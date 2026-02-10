"""Abstract base class for output adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod

from order_automation.models.order import Order, SubmissionResult


class OutputAdapter(ABC):
    """Base class every output adapter must implement."""

    @abstractmethod
    def submit(self, order: Order) -> SubmissionResult:
        """Submit *order* to the destination and return the result."""
