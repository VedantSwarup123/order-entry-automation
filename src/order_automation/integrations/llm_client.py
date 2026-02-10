"""LLM-powered order extraction using Claude API.

Extracts structured order data from unstructured email/fax text.
Falls back to regex if the API is unavailable.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog

log = structlog.get_logger()

# Try to import anthropic; gracefully degrade if missing.
try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None  # type: ignore[assignment]


EXTRACTION_PROMPT = """You are an order extraction assistant for Ledvance, a lighting products distributor.
Extract structured order data from the following text. Return ONLY valid JSON with this schema:

{
  "customer_id": "string",
  "customer_name": "string",
  "po_number": "string",
  "order_date": "YYYY-MM-DD",
  "ship_to": {
    "name": "string",
    "line1": "string",
    "city": "string",
    "state": "string (2-letter)",
    "postal_code": "string",
    "country": "US"
  },
  "line_items": [
    {"sku": "string", "description": "string", "quantity": int, "unit_price": float, "uom": "EA"}
  ],
  "notes": "string",
  "confidence": 0.0-1.0,
  "anomalies": ["list of any unusual findings"]
}

Rules:
- Extract ALL line items found in the text
- If a field is not found, use empty string "" for strings, 0 for numbers
- Set confidence based on how complete and clear the data is (1.0 = perfect, 0.5 = partial, 0.0 = unusable)
- Flag anomalies: unusual quantities (>1000), missing required fields, suspicious pricing, duplicate items
- Common Ledvance SKUs start with LED-, FIX-, CTL-, WIRE-, CONN-, EMG-, BATT-
- Recognize common distributor names: Sonepar, Rexel, WESCO, Graybar, CED, City Electric

TEXT TO EXTRACT:
"""

ANOMALY_PROMPT = """Analyze this order for anomalies and potential issues:

Order: {order_json}

Check for:
1. Unusually large quantities (>500 units for single items)
2. Unit prices that seem wrong (e.g., $0.01 or >$10,000)
3. Missing critical fields (customer, PO, ship-to address)
4. Duplicate line items
5. Inconsistent data (e.g., PO format doesn't match customer)

Return JSON: {{"anomalies": ["list of issues"], "risk_level": "low|medium|high", "confidence": 0.0-1.0}}
"""


def extract_order_from_text(text: str, source: str = "email") -> dict[str, Any]:
    """Extract order data from unstructured text using Claude API.

    Falls back to regex extraction if the API is unavailable or fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key or not ANTHROPIC_AVAILABLE:
        log.info("llm_extraction_fallback", reason="no_api_key" if not api_key else "no_sdk")
        result = _regex_fallback(text)
        result["extraction_method"] = "regex"
        return result

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[
                {"role": "user", "content": EXTRACTION_PROMPT + text}
            ],
        )

        content = response.content[0].text
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1)

        result = json.loads(content)
        result["extraction_method"] = "llm"
        result.setdefault("confidence", 0.8)
        result.setdefault("anomalies", [])

        # Run basic anomaly checks on top of LLM output
        basic_anomalies = _basic_anomaly_check(result)
        result["anomalies"] = list(set(result.get("anomalies", []) + basic_anomalies))

        log.info(
            "llm_extraction_success",
            source=source,
            confidence=result.get("confidence"),
            items=len(result.get("line_items", [])),
        )
        return result

    except Exception as exc:
        log.warning("llm_extraction_failed", error=str(exc), source=source)
        result = _regex_fallback(text)
        result["extraction_method"] = "regex_fallback"
        return result


def detect_anomalies(order_data: dict[str, Any]) -> dict[str, Any]:
    """Run anomaly detection on extracted order data.

    Uses Claude API if available, otherwise falls back to basic checks.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    basic = {
        "anomalies": _basic_anomaly_check(order_data),
        "risk_level": "low",
        "confidence": 0.6,
    }

    if not api_key or not ANTHROPIC_AVAILABLE:
        if basic["anomalies"]:
            basic["risk_level"] = "medium" if len(basic["anomalies"]) <= 2 else "high"
        return basic

    try:
        client = anthropic.Anthropic(api_key=api_key)
        order_json = json.dumps(order_data, default=str)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": ANOMALY_PROMPT.format(order_json=order_json)}
            ],
        )

        content = response.content[0].text
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1)

        result = json.loads(content)
        # Merge basic checks with LLM checks
        all_anomalies = list(set(result.get("anomalies", []) + basic["anomalies"]))
        result["anomalies"] = all_anomalies
        return result

    except Exception as exc:
        log.warning("llm_anomaly_detection_failed", error=str(exc))
        if basic["anomalies"]:
            basic["risk_level"] = "medium" if len(basic["anomalies"]) <= 2 else "high"
        return basic


def _basic_anomaly_check(data: dict[str, Any]) -> list[str]:
    """Run basic rule-based anomaly checks."""
    anomalies: list[str] = []

    # Missing required fields
    if not data.get("customer_id"):
        anomalies.append("Missing customer_id")
    if not data.get("po_number"):
        anomalies.append("Missing PO number")

    ship_to = data.get("ship_to", {})
    if isinstance(ship_to, dict):
        if not ship_to.get("line1") and not ship_to.get("city"):
            anomalies.append("Missing ship-to address")

    # Line item checks
    items = data.get("line_items", [])
    if not items:
        anomalies.append("No line items found")

    skus_seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        sku = item.get("sku", "")
        qty = item.get("quantity", 0)
        price = float(item.get("unit_price", 0))

        if qty > 1000:
            anomalies.append(f"Unusually large quantity: {sku} x {qty}")
        if price > 5000:
            anomalies.append(f"Unusually high price: {sku} @ ${price}")
        if price == 0 and sku != "REVIEW":
            anomalies.append(f"Zero price: {sku}")
        if sku in skus_seen:
            anomalies.append(f"Duplicate SKU: {sku}")
        skus_seen.add(sku)

    return anomalies


# Key-value patterns: customer_id: CUST-123
_KV_PATTERN = re.compile(r"^\s*([\w_]+)\s*:\s*(.+)$", re.MULTILINE)

# Tabular line-item pattern: SKU  QTY  PRICE
_LINE_PATTERN = re.compile(
    r"^\s*(\S+)\s+(\d+)\s+\$?([\d,.]+)\s*$", re.MULTILINE
)


def _regex_fallback(text: str) -> dict[str, Any]:
    """Extract order data using regex patterns when LLM is unavailable."""
    kv: dict[str, str] = {}
    for m in _KV_PATTERN.finditer(text):
        kv[m.group(1).lower()] = m.group(2).strip()

    items: list[dict[str, Any]] = []
    for m in _LINE_PATTERN.finditer(text):
        try:
            items.append({
                "sku": m.group(1),
                "description": "",
                "quantity": int(m.group(2)),
                "unit_price": float(Decimal(m.group(3).replace(",", ""))),
                "uom": "EA",
            })
        except (InvalidOperation, ValueError):
            continue

    confidence = 0.3  # base regex confidence
    if kv.get("customer_id"):
        confidence += 0.15
    if kv.get("po_number"):
        confidence += 0.15
    if items:
        confidence += 0.2

    result: dict[str, Any] = {
        "customer_id": kv.get("customer_id", ""),
        "customer_name": kv.get("customer_name", ""),
        "po_number": kv.get("po_number", ""),
        "order_date": kv.get("order_date", str(date.today())),
        "ship_to": {
            "name": kv.get("ship_to_name", ""),
            "line1": kv.get("ship_to_address", kv.get("address", "")),
            "city": kv.get("ship_to_city", kv.get("city", "")),
            "state": kv.get("ship_to_state", kv.get("state", "")),
            "postal_code": kv.get("ship_to_zip", kv.get("zip", "")),
            "country": "US",
        },
        "line_items": items,
        "notes": kv.get("notes", ""),
        "confidence": round(min(confidence, 1.0), 2),
        "anomalies": [],
    }

    result["anomalies"] = _basic_anomaly_check(result)
    return result
