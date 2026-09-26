"""Provider interface: every inventory source (Viator, Klook, mock, ...) implements this."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ActivitySummary:
    product_code: str
    title: str
    destination: str
    rating: float | None = None
    review_count: int | None = None
    price_from: float | None = None
    currency: str = "USD"
    duration: str | None = None
    image_url: str | None = None
    categories: list[str] = field(default_factory=list)


@dataclass
class ActivityDetails(ActivitySummary):
    description: str = ""
    highlights: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    meeting_point: str | None = None
    cancellation_policy: str | None = None


@dataclass
class AvailabilitySlot:
    date: str
    available: bool
    price_total: float | None = None
    currency: str = "USD"
    option_code: str | None = None


@dataclass
class ProviderHold:
    provider_ref: str
    total: float
    currency: str
    raw: dict = field(default_factory=dict)


@dataclass
class ProviderBooking:
    provider_ref: str
    status: str  # CONFIRMED | CANCELLED | PENDING
    raw: dict = field(default_factory=dict)


class ProviderError(Exception):
    """Raised when the upstream supplier API fails."""


class ActivityProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def search(
        self,
        destination: str,
        date: str | None = None,
        travelers: int = 2,
        category: str | None = None,
        max_price: float | None = None,
        limit: int = 10,
    ) -> list[ActivitySummary]: ...

    @abstractmethod
    async def get_details(self, product_code: str) -> ActivityDetails: ...

    @abstractmethod
    async def check_availability(
        self, product_code: str, date: str, travelers: int = 2
    ) -> list[AvailabilitySlot]: ...

    @abstractmethod
    async def create_hold(
        self, product_code: str, date: str, travelers: int, contact: dict
    ) -> ProviderHold:
        """Reserve inventory upstream; payment is collected separately."""

    @abstractmethod
    async def confirm_hold(self, provider_hold_ref: str, contact: dict) -> ProviderBooking:
        """Convert a paid hold into a confirmed booking upstream."""

    @abstractmethod
    async def get_booking(self, provider_booking_ref: str) -> ProviderBooking: ...

    @abstractmethod
    async def cancel_booking(self, provider_booking_ref: str, reason: str | None = None) -> ProviderBooking: ...
