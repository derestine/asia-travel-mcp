"""End-to-end test of the agent booking flow against the mock provider."""
from __future__ import annotations

import os
import tempfile

import pytest

os.environ["TRAVEL_PROVIDER"] = "mock"
os.environ["TRAVEL_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from asia_travel_mcp import server  # noqa: E402


@pytest.mark.asyncio
async def test_full_booking_flow():
    results = await server.search_activities(destination="Tokyo", travelers=2)
    assert not any("error" in r for r in results), results
    assert len(results) >= 1
    code = results[0]["product_code"]

    details = await server.get_activity_details(product_code=code)
    assert details["product_code"] == code
    assert details["cancellation_policy"]

    slots = await server.check_availability(
        product_code=code, date="2026-12-15", travelers=2)
    assert slots and slots[0]["available"], slots

    hold = await server.create_booking_hold(
        product_code=code, date="2026-12-15", travelers=2,
        contact_name="Test Traveler", contact_email="test@example.com")
    assert "hold_id" in hold, hold
    assert hold["payment_url"].startswith("http")
    assert hold["total"] > 0

    booking = await server.confirm_booking(hold_id=hold["hold_id"])
    assert booking["status"] == "CONFIRMED", booking
    assert booking["booking_ref"].startswith("ATB-")

    fetched = await server.get_booking(booking_ref=booking["booking_ref"])
    assert fetched["ref"] == booking["booking_ref"]

    cancelled = await server.cancel_booking(
        booking_ref=booking["booking_ref"], reason="test")
    assert cancelled["status"] == "CANCELLED"

    fetched2 = await server.get_booking(booking_ref=booking["booking_ref"])
    assert fetched2["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_search_no_results_and_bad_product():
    results = await server.search_activities(destination="Atlantis")
    assert results == []
    bad = await server.get_activity_details(product_code="NOPE-01")
    assert "error" in bad
