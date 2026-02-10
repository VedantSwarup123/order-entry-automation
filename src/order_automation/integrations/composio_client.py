"""Composio integration wrapper.

All external service calls (Gmail, Outlook, Google Sheets, Slack) go through
this module.  If the composio SDK is not installed or not configured, every
call silently returns plausible mock data so the system works with zero
external credentials.
"""
from __future__ import annotations

import structlog

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Availability detection
# ---------------------------------------------------------------------------
try:
    from composio import ComposioToolSet  # type: ignore[import-untyped]

    COMPOSIO_AVAILABLE = True
except ImportError:
    COMPOSIO_AVAILABLE = False
    ComposioToolSet = None  # type: ignore[assignment,misc]

_toolset: ComposioToolSet | None = None


def get_toolset() -> ComposioToolSet | None:
    """Return a shared ``ComposioToolSet`` instance, or *None* if unavailable."""
    global _toolset
    if not COMPOSIO_AVAILABLE:
        return None
    if _toolset is None:
        try:
            _toolset = ComposioToolSet()
        except Exception:
            log.warning("composio_toolset_init_failed")
            return None
    return _toolset


def is_connected() -> bool:
    """Return *True* when Composio is importable and a toolset can be created."""
    return get_toolset() is not None


# ---------------------------------------------------------------------------
# Mock responses
# ---------------------------------------------------------------------------

def _mock_response(action: str, params: dict) -> dict:
    """Return a plausible empty/success response for *action*."""
    action_upper = action.upper()
    if "FETCH" in action_upper or "GET" in action_upper or "READ" in action_upper:
        # Read-type actions → empty list / empty data
        if "EMAIL" in action_upper or "MAIL" in action_upper:
            return {"emails": [], "messages": []}
        if "SHEET" in action_upper or "SPREADSHEET" in action_upper:
            return {"values": [], "rows": [], "data": []}
        return {"data": []}
    # Write / send / append actions → success
    return {"success": True, "status": "ok", "mock": True}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_action(action_name: str, params: dict | None = None) -> dict:
    """Execute a Composio action.

    If Composio is unavailable or the call fails, a mock response is returned
    so the rest of the system never crashes due to missing credentials.
    """
    params = params or {}

    ts = get_toolset()
    if ts is None:
        log.info("composio_mock", action=action_name)
        return _mock_response(action_name, params)

    try:
        result = ts.execute_action(action_name, params)
        return result if isinstance(result, dict) else {"result": result}
    except Exception as exc:
        log.warning("composio_action_failed", action=action_name, error=str(exc))
        return _mock_response(action_name, params)
