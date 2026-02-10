"""Order normalisation logic.

Cleans up addresses, SKUs, UOMs and customer names so that orders from
different sources look uniform before validation and routing.
"""
from __future__ import annotations

import re

from order_automation.models.order import Address, Order

# Full US state-name → abbreviation mapping
_STATE_ABBREVS: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}

_COUNTRY_ALIASES: dict[str, str] = {
    "usa": "US", "united states": "US", "united states of america": "US",
    "u.s.": "US", "u.s.a.": "US", "america": "US",
    "canada": "CA", "can": "CA",
    "mexico": "MX", "mex": "MX",
}

_UOM_ALIASES: dict[str, str] = {
    "each": "EA", "ea": "EA", "pc": "EA", "pcs": "EA", "piece": "EA",
    "case": "CS", "cs": "CS", "cse": "CS",
    "box": "BX", "bx": "BX",
    "pallet": "PL", "pl": "PL", "plt": "PL",
    "dozen": "DZ", "dz": "DZ",
    "pound": "LB", "lb": "LB", "lbs": "LB",
    "kilogram": "KG", "kg": "KG", "kgs": "KG",
}


def _normalize_state(state: str) -> str:
    """Convert full state name to two-letter abbreviation."""
    lowered = state.strip().lower()
    return _STATE_ABBREVS.get(lowered, state.strip().upper())


def _normalize_country(country: str) -> str:
    """Normalise country name to ISO-like code."""
    lowered = country.strip().lower()
    return _COUNTRY_ALIASES.get(lowered, country.strip().upper())


def _normalize_postal_code(code: str) -> str:
    """Strip non-digit chars except hyphens."""
    return re.sub(r"[^\d\-]", "", code)


def _normalize_uom(uom: str) -> str:
    """Standardise unit-of-measure codes."""
    return _UOM_ALIASES.get(uom.strip().lower(), uom.strip().upper())


def _normalize_address(addr: Address) -> Address:
    """Return a copy of *addr* with normalised fields."""
    return addr.model_copy(update={
        "state": _normalize_state(addr.state),
        "country": _normalize_country(addr.country),
        "postal_code": _normalize_postal_code(addr.postal_code),
    })


class OrderNormalizer:
    """Applies cleaning / normalisation rules to an :class:`Order`."""

    def normalize(self, order: Order) -> Order:
        """Return a normalised copy of *order*."""
        updates: dict = {}

        # Customer name → title case
        if order.customer_name:
            updates["customer_name"] = order.customer_name.strip().title()

        # Addresses
        updates["ship_to"] = _normalize_address(order.ship_to)
        if order.bill_to is not None:
            updates["bill_to"] = _normalize_address(order.bill_to)

        # Line items: SKU uppercase+trim, UOM standardisation
        new_items = []
        for item in order.line_items:
            new_items.append(item.model_copy(update={
                "sku": item.sku.strip().upper(),
                "uom": _normalize_uom(item.uom),
            }))
        updates["line_items"] = new_items

        return order.model_copy(update=updates)
