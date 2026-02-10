"""Abstract base class for ingest sources."""
from __future__ import annotations

from abc import ABC, abstractmethod

from order_automation.models.order import Order, RawOrder


class IngestSource(ABC):
    """Base class every ingest source must implement."""

    @abstractmethod
    def poll(self) -> list[RawOrder]:
        """Check the source for new data and return raw payloads."""

    @abstractmethod
    def parse(self, raw: RawOrder) -> list[Order]:
        """Convert a raw payload into one or more canonical orders."""
