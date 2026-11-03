"""SAP field mapping and order type classification.

Maps internal order fields to SAP VA-01 transaction fields.
Supports ZL01 (stock orders) and ZL02 (drop ship orders).
"""
from __future__ import annotations

from typing import Any

from order_automation.models.order import Order


# SAP Order Types
SAP_ORDER_TYPES = {
    "ZL01": "Stock Order",
    "ZL02": "Drop Ship Order",
}

# Ship-to locations that indicate stock/warehouse orders
WAREHOUSE_KEYWORDS = {"warehouse", "dc", "distribution", "fulfillment", "depot", "hub"}

# SAP Plant codes by state/region
SAP_PLANT_CODES = {
    "CA": "1000",
    "NY": "2000",
    "TX": "3000",
    "FL": "4000",
    "IL": "5000",
    "WA": "6000",
    "OR": "6000",
    "NV": "1000",
    "AZ": "1000",
    "CO": "3000",
    "MA": "2000",
    "GA": "4000",
    "PA": "2000",
    "OH": "5000",
}

# SAP Sales Organization mapping
SAP_SALES_ORG = {
    "US": "1000",
    "CA": "2000",
}

# Material group mapping for lighting products
SAP_MATERIAL_GROUPS = {
    "LED-": "LEDLAMP",
    "FIX-": "FIXTUR",
    "CTL-": "CONTRL",
    "WIRE-": "CABLNG",
    "CONN-": "CONNCT",
    "EMG-": "EMRGCY",
    "BATT-": "BATTER",
}


def classify_order_type(order: Order) -> str:
    """Determine SAP order type (ZL01 stock vs ZL02 drop ship).

    Rules:
    - If ship-to address contains warehouse-related keywords → ZL01 (stock)
    - If ship-to is a customer's end location → ZL02 (drop ship)
    - Default to ZL01 if unclear
    """
    ship_to_name = (order.ship_to.name or "").lower()
    ship_to_line1 = (order.ship_to.line1 or "").lower()
    combined = f"{ship_to_name} {ship_to_line1}"

    for keyword in WAREHOUSE_KEYWORDS:
        if keyword in combined:
            return "ZL01"

    # If customer name appears in ship-to, likely a direct shipment
    customer_lower = (order.customer_name or "").lower()
    if customer_lower and customer_lower not in ship_to_name:
        return "ZL02"  # Different destination → drop ship

    return "ZL01"  # Default to stock


def get_material_group(sku: str) -> str:
    """Map a SKU prefix to its SAP material group."""
    for prefix, group in SAP_MATERIAL_GROUPS.items():
        if sku.upper().startswith(prefix):
            return group
    return "MISC"


def map_to_sap(order: Order) -> dict[str, Any]:
    """Map an internal order to SAP VA-01 fields.

    Returns a dict with SAP-compatible field names and values.
    """
    order_type = classify_order_type(order)
    state = order.ship_to.state.upper() if order.ship_to.state else "CA"
    country = order.ship_to.country.upper() if order.ship_to.country else "US"

    sap_data: dict[str, Any] = {
        # Header
        "order_type": order_type,
        "order_type_desc": SAP_ORDER_TYPES.get(order_type, "Unknown"),
        "sales_org": SAP_SALES_ORG.get(country, "1000"),
        "distribution_channel": "10",  # Wholesale
        "division": "00",  # Cross-division
        "plant": SAP_PLANT_CODES.get(state, "1000"),

        # Customer
        "sold_to_party": order.customer_id,
        "ship_to_party": order.customer_id,
        "customer_po": order.po_number,
        "po_date": str(order.order_date),

        # Delivery
        "requested_delivery_date": str(order.requested_ship_date or order.order_date),
        "shipping_point": SAP_PLANT_CODES.get(state, "1000"),
        "incoterms": "FOB" if order_type == "ZL02" else "EXW",
        "delivery_priority": "02",  # Normal

        # Ship-to
        "ship_to_name": order.ship_to.name,
        "ship_to_street": order.ship_to.line1,
        "ship_to_city": order.ship_to.city,
        "ship_to_region": order.ship_to.state,
        "ship_to_postal": order.ship_to.postal_code,
        "ship_to_country": order.ship_to.country,

        # Line items
        "items": [],
    }

    for idx, item in enumerate(order.line_items):
        sap_item = {
            "item_number": (idx + 1) * 10,  # SAP convention: 10, 20, 30...
            "material": item.sku,
            "material_group": get_material_group(item.sku),
            "quantity": item.quantity,
            "uom": item.uom,
            "net_price": float(item.unit_price),
            "plant": sap_data["plant"],
            "storage_location": "0001",
        }
        sap_data["items"].append(sap_item)

    return sap_data
