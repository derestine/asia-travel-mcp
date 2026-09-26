"""Viator Partner API client.

Get a key at https://partners.viator.com (partner signup), then set VIATOR_API_KEY.
Docs: https://docs.viator.com/partner-api/technical/

Endpoints used (Partner API v2):
  POST /products/search
  GET  /products/{product-code}
  POST /availability/schedules/{product-code}
  POST /bookings/hold
  POST /bookings/book
  GET  /bookings/{booking-reference}
  POST /bookings/{booking-reference}/cancel
"""
from __future__ import annotations

import httpx

from .base import (
    ActivityDetails,
    ActivityProvider,
    ActivitySummary,
    AvailabilitySlot,
    ProviderBooking,
    ProviderError,
    ProviderHold,
)

BASE_URL = "https://api.viator.com/partner"
_API_VERSION = "application/json;version=2.0"


class ViatorProvider(ActivityProvider):
    name = "viator"

    def __init__(self, api_key: str):
        if not api_key:
            raise ProviderError("VIATOR_API_KEY is required for the Viator provider")
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"exp-api-key": api_key, "Accept": _API_VERSION,
                     "Content-Type": "application/json"},
            timeout=30.0,
        )

    async def _post(self, path: str, body: dict) -> dict:
        r = await self._client.post(path, json=body)
        if r.status_code >= 400:
            raise ProviderError(f"Viator {path} failed ({r.status_code}): {r.text[:300]}")
        return r.json()

    async def _get(self, path: str) -> dict:
        r = await self._client.get(path)
        if r.status_code >= 400:
            raise ProviderError(f"Viator {path} failed ({r.status_code}): {r.text[:300]}")
        return r.json()

    @staticmethod
    def _summary(p: dict) -> ActivitySummary:
        pricing = p.get("pricing") or {}
        return ActivitySummary(
            product_code=p.get("productCode", ""),
            title=p.get("title", ""),
            destination=(p.get("destinations") or [{}])[0].get("destinationName", ""),
            rating=p.get("rating"),
            review_count=p.get("reviewCount"),
            price_from=(pricing.get("summary") or {}).get("fromPrice"),
            currency=(pricing.get("currency") or "USD"),
            duration=(p.get("duration") or {}).get("description"),
            image_url=((p.get("images") or [{}])[0].get("variants") or [{}])[0].get("url"),
            categories=[c.get("name", "") for c in p.get("productCategories") or []],
        )

    async def search(self, destination, date=None, travelers=2, category=None,
                     max_price=None, limit=10):
        body: dict = {
            "filtering": {"destination": destination},
            "pagination": {"start": 1, "count": limit},
            "sorting": {"sort": "REVIEW_AVG_RATING", "order": "DESCENDING"},
            "currency": "USD",
        }
        if date:
            body["filtering"]["dateRange"] = {"from": date, "to": date}
        data = await self._post("/products/search", body)
        out = [self._summary(p) for p in data.get("products", [])]
        if category:
            out = [a for a in out if category.lower() in [c.lower() for c in a.categories]]
        if max_price is not None:
            out = [a for a in out if a.price_from is not None and a.price_from <= max_price]
        return out

    async def get_details(self, product_code: str) -> ActivityDetails:
        p = await self._get(f"/products/{product_code}")
        s = self._summary(p)
        return ActivityDetails(
            **s.__dict__,
            description=p.get("description", ""),
            highlights=[h.get("title", "") for h in p.get("highlights") or []],
            cancellation_policy=(p.get("cancellationPolicy") or {}).get("description"),
        )

    async def check_availability(self, product_code, date, travelers=2):
        data = await self._post(f"/availability/schedules/{product_code}", {
            "dateRange": {"from": date, "to": date},
            "currency": "USD",
        })
        slots: list[AvailabilitySlot] = []
        for bookable in data.get("bookableItems", []):
            for season in bookable.get("seasons", []):
                for pricing in season.get("pricings", []):
                    total = (pricing.get("totalPrice") or {}).get("price")
                    slots.append(AvailabilitySlot(
                        date=date, available=total is not None,
                        price_total=(total.get("value") if total else None),
                        currency=(total.get("currency") if total else "USD"),
                        option_code=bookable.get("productOptionCode"),
                    ))
        return slots or [AvailabilitySlot(date=date, available=False)]

    async def create_hold(self, product_code, date, travelers, contact) -> ProviderHold:
        data = await self._post("/bookings/hold", {
            "productCode": product_code,
            "travelDate": date,
            "currency": "USD",
            "bookingQuestions": [],
        })
        hold = data.get("hold") or {}
        total = ((data.get("totalPrice") or {}).get("price") or {}).get("value", 0.0)
        return ProviderHold(provider_ref=hold.get("holdReference", ""),
                            total=float(total), currency="USD", raw=data)

    async def confirm_hold(self, provider_hold_ref: str, contact: dict) -> ProviderBooking:
        data = await self._post("/bookings/book", {
            "holdReference": provider_hold_ref,
            "currency": "USD",
            "bookingQuestions": [],
            "communication": {"email": contact.get("email"),
                               "phone": contact.get("phone", "")},
        })
        booking = data.get("booking") or {}
        return ProviderBooking(provider_ref=booking.get("bookingReference", ""),
                               status=booking.get("status", "CONFIRMED"), raw=data)

    async def get_booking(self, provider_booking_ref: str) -> ProviderBooking:
        data = await self._get(f"/bookings/{provider_booking_ref}")
        booking = data.get("booking") or {}
        return ProviderBooking(provider_ref=provider_booking_ref,
                               status=booking.get("status", "UNKNOWN"), raw=data)

    async def cancel_booking(self, provider_booking_ref: str, reason=None) -> ProviderBooking:
        data = await self._post(f"/bookings/{provider_booking_ref}/cancel",
                                {"reason": reason or "Customer request"})
        booking = data.get("booking") or {}
        return ProviderBooking(provider_ref=provider_booking_ref,
                               status=booking.get("status", "CANCELLED"), raw=data)
