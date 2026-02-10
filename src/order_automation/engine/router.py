"""Rule-based order routing.

Reads declarative rules from a YAML file and returns the set of destination
names an order should be submitted to.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from order_automation.models.order import Order


def _resolve_field(order: Order, dotted: str) -> Any:
    """Resolve a dot-notation field path (e.g. ``ship_to.state``) on *order*."""
    obj: Any = order
    for part in dotted.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj


def _coerce(value: Any, reference: Any) -> Any:
    """Coerce *reference* (from YAML) to the same type as *value*."""
    if isinstance(value, Decimal):
        return Decimal(str(reference))
    if isinstance(value, int) and not isinstance(reference, int):
        return int(reference)
    if isinstance(value, float):
        return float(reference)
    return reference


def _evaluate_condition(order: Order, condition: Any) -> bool:
    """Return *True* if the order satisfies *condition*."""
    if condition == "always":
        return True

    if not isinstance(condition, dict):
        return False

    field = condition.get("field", "")
    operator = condition.get("operator", "==")
    expected = condition.get("value")

    actual = _resolve_field(order, field)
    if actual is None:
        return False

    if operator == "in":
        return actual in expected  # type: ignore[operator]

    expected = _coerce(actual, expected)

    ops = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
    }
    fn = ops.get(operator)
    if fn is None:
        return False
    return fn(actual, expected)


class OrderRouter:
    """Evaluates routing rules and returns matching destination names."""

    def __init__(self, rules_path: str | Path | None = None) -> None:
        self.rules: list[dict] = []
        if rules_path is not None:
            self.load(rules_path)

    def load(self, path: str | Path) -> None:
        """Load rules from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        self.rules = data.get("rules", [])

    def route(self, order: Order) -> list[str]:
        """Return the list of destinations the *order* should go to."""
        destinations: list[str] = []
        for rule in self.rules:
            condition = rule.get("condition", "always")
            if _evaluate_condition(order, condition):
                dest = rule.get("destination", "")
                if dest and dest not in destinations:
                    destinations.append(dest)
        return destinations
