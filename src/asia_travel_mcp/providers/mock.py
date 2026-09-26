"""Mock provider: realistic Asia activities dataset for demos, tests and development.

Swap to the real Viator provider with TRAVEL_PROVIDER=viator + VIATOR_API_KEY.
"""
from __future__ import annotations

import hashlib
from datetime import date as date_cls

from .base import (
    ActivityDetails,
    ActivityProvider,
    ActivitySummary,
    AvailabilitySlot,
    ProviderBooking,
    ProviderError,
    ProviderHold,
)

_CATALOG: list[dict] = [
    {
        "product_code": "TYO-TEAMLAB-01",
        "title": "teamLab Planets TOKYO Digital Art Museum Ticket",
        "destination": "Tokyo",
        "rating": 4.8, "review_count": 12413, "price_from": 24.0,
        "duration": "2-3 hours",
        "categories": ["Attractions", "Art & Culture"],
        "description": "Immerse yourself in massive interactive digital artworks across water and garden areas at teamLab Planets.",
        "highlights": ["Walk through water", "Floating flower garden", "Athletics Forest"],
        "cancellation_policy": "Free cancellation up to 24 hours before the visit.",
    },
    {
        "product_code": "TYO-FUJI-02",
        "title": "Mt Fuji, Hakone & Lake Ashi Day Trip from Tokyo",
        "destination": "Tokyo",
        "rating": 4.6, "review_count": 8932, "price_from": 89.0,
        "duration": "10 hours",
        "categories": ["Day Trips", "Nature"],
        "description": "See Mt Fuji's 5th Station, cruise Lake Ashi and ride the Hakone Ropeway with an English-speaking guide.",
        "highlights": ["Mt Fuji 5th Station", "Lake Ashi cruise", "Hakone Ropeway"],
        "cancellation_policy": "Free cancellation up to 48 hours before departure.",
    },
    {
        "product_code": "BKK-CRUISE-01",
        "title": "Chao Phraya River Dinner Cruise with Live Music",
        "destination": "Bangkok",
        "rating": 4.5, "review_count": 6210, "price_from": 38.0,
        "duration": "2 hours",
        "categories": ["Cruises", "Food & Drink"],
        "description": "Buffet dinner aboard a luxury cruise past Wat Arun and the Grand Palace, with live music.",
        "highlights": ["International buffet", "Iconic riverside landmarks", "Live band"],
        "cancellation_policy": "Free cancellation up to 24 hours before departure.",
    },
    {
        "product_code": "BKK-PALACE-02",
        "title": "Grand Palace & Wat Pho Guided Tour",
        "destination": "Bangkok",
        "rating": 4.7, "review_count": 4102, "price_from": 29.0,
        "duration": "4 hours",
        "categories": ["Tours", "History"],
        "description": "Guided morning tour of the Grand Palace, Emerald Buddha and the Reclining Buddha at Wat Pho.",
        "highlights": ["Skip-the-line entry", "Expert local guide", "Small group"],
        "cancellation_policy": "Free cancellation up to 24 hours before the tour.",
    },
    {
        "product_code": "DPS-ULUWATU-01",
        "title": "Uluwatu Temple Sunset & Kecak Fire Dance",
        "destination": "Bali",
        "rating": 4.7, "review_count": 5580, "price_from": 18.0,
        "duration": "5 hours",
        "categories": ["Culture", "Sunset"],
        "description": "Clifftop temple at sunset followed by the dramatic Kecak fire dance performance.",
        "highlights": ["Sunset over the Indian Ocean", "Kecak chant performance", "Hotel transfers"],
        "cancellation_policy": "Free cancellation up to 24 hours before the tour.",
    },
    {
        "product_code": "DPS-PENIDA-02",
        "title": "Nusa Penida Island Day Trip with Snorkeling",
        "destination": "Bali",
        "rating": 4.6, "review_count": 7304, "price_from": 65.0,
        "duration": "9 hours",
        "categories": ["Day Trips", "Snorkeling"],
        "description": "Fast-boat to Nusa Penida: Kelingking Beach viewpoint, Angel's Billabong and snorkeling with manta rays (seasonal).",
        "highlights": ["Kelingking viewpoint", "Snorkeling gear included", "Beachside lunch"],
        "cancellation_policy": "Free cancellation up to 48 hours before departure.",
    },
    {
        "product_code": "TPE-JIUFEN-01",
        "title": "Jiufen Night Tour & Shifen Waterfall from Taipei",
        "destination": "Taipei",
        "rating": 4.8, "review_count": 3941, "price_from": 32.0,
        "duration": "6 hours",
        "categories": ["Tours", "Nightlife"],
        "description": "Lantern-lit Jiufen old street, sky-lantern release in Shifen and the Golden Waterfall.",
        "highlights": ["Jiufen teahouse street", "Sky lantern experience", "Shifen Waterfall"],
        "cancellation_policy": "Free cancellation up to 24 hours before the tour.",
    },
    {
        "product_code": "SIN-GARDENS-01",
        "title": "Gardens by the Bay: Flower Dome + Cloud Forest",
        "destination": "Singapore",
        "rating": 4.8, "review_count": 15230, "price_from": 28.0,
        "duration": "3-4 hours",
        "categories": ["Attractions", "Nature"],
        "description": "Twin cooled conservatories plus the Supertree Grove at Singapore's iconic garden.",
        "highlights": ["Flower Dome", "Cloud Forest waterfall", "Supertree Grove"],
        "cancellation_policy": "Free cancellation up to 24 hours before the visit.",
    },
]


def _lookup(product_code: str) -> dict:
    for item in _CATALOG:
        if item["product_code"] == product_code:
            return item
    raise ProviderError(f"Unknown product code: {product_code}")


def _slot_available(product_code: str, day: str) -> bool:
    # Deterministic pseudo-availability so demos are stable.
    h = int(hashlib.sha256(f"{product_code}:{day}".encode()).hexdigest(), 16)
    return h % 10 != 0  # ~90% of dates available


class MockProvider(ActivityProvider):
    name = "mock"

    async def search(self, destination, date=None, travelers=2, category=None,
                     max_price=None, limit=10) -> list[ActivitySummary]:
        dest = destination.strip().lower()
        out: list[ActivitySummary] = []
        for item in _CATALOG:
            if dest not in item["destination"].lower() and dest not in item["title"].lower():
                continue
            if category and category.lower() not in [c.lower() for c in item["categories"]]:
                continue
            if max_price is not None and item["price_from"] > max_price:
                continue
            out.append(ActivitySummary(
                product_code=item["product_code"], title=item["title"],
                destination=item["destination"], rating=item["rating"],
                review_count=item["review_count"], price_from=item["price_from"],
                duration=item["duration"], categories=item["categories"],
            ))
            if len(out) >= limit:
                break
        return out

    async def get_details(self, product_code: str) -> ActivityDetails:
        item = _lookup(product_code)
        return ActivityDetails(
            product_code=item["product_code"], title=item["title"],
            destination=item["destination"], rating=item["rating"],
            review_count=item["review_count"], price_from=item["price_from"],
            duration=item["duration"], categories=item["categories"],
            description=item["description"], highlights=item["highlights"],
            cancellation_policy=item["cancellation_policy"],
        )

    async def check_availability(self, product_code: str, date: str, travelers: int = 2):
        item = _lookup(product_code)
        try:
            date_cls.fromisoformat(date)
        except ValueError:
            raise ProviderError(f"Invalid date (use YYYY-MM-DD): {date}")
        available = _slot_available(product_code, date)
        total = round(item["price_from"] * travelers, 2) if available else None
        return [AvailabilitySlot(date=date, available=available, price_total=total,
                                 option_code="STD" if available else None)]

    async def create_hold(self, product_code, date, travelers, contact) -> ProviderHold:
        item = _lookup(product_code)
        if not _slot_available(product_code, date):
            raise ProviderError(f"{product_code} is not available on {date}")
        total = round(item["price_from"] * travelers, 2)
        ref = "MOCK-HOLD-" + hashlib.sha256(
            f"{product_code}{date}{travelers}{contact.get('email')}".encode()
        ).hexdigest()[:10].upper()
        return ProviderHold(provider_ref=ref, total=total, currency="USD",
                            raw={"product_code": product_code})

    async def confirm_hold(self, provider_hold_ref: str, contact: dict) -> ProviderBooking:
        ref = "MOCK-" + hashlib.sha256(provider_hold_ref.encode()).hexdigest()[:10].upper()
        return ProviderBooking(provider_ref=ref, status="CONFIRMED",
                               raw={"hold_ref": provider_hold_ref})

    async def get_booking(self, provider_booking_ref: str) -> ProviderBooking:
        return ProviderBooking(provider_ref=provider_booking_ref, status="CONFIRMED", raw={})

    async def cancel_booking(self, provider_booking_ref: str, reason=None) -> ProviderBooking:
        return ProviderBooking(provider_ref=provider_booking_ref, status="CANCELLED",
                               raw={"reason": reason})
