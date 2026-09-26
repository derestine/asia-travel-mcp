"""MCP server: Asia travel discovery, booking and management for AI agents.

Tools:
  search_activities / get_activity_details / check_availability
  create_booking_hold / confirm_booking / get_booking / cancel_booking

Payment flow: create_booking_hold reserves inventory and returns a payment_url.
The traveler pays there (plug in Stripe Payment Links via PAYMENT_LINK_BASE);
confirm_booking is then called (by your payment webhook in production) to
convert the hold into a confirmed booking.
"""
from __future__ import annotations

from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import config
from .providers import get_provider
from .providers.base import ProviderError
from .store import BookingStore

mcp = FastMCP("asia-travel")
_provider = None
_store = None


def _get_provider():
    global _provider
    if _provider is None:
        _provider = get_provider()
    return _provider


def _get_store() -> BookingStore:
    global _store
    if _store is None:
        _store = BookingStore(config.get_db_path())
    return _store


def _payment_url(hold_id: str, total: float, currency: str) -> str:
    base = config.get_payment_link_base()
    if base:
        return f"{base.rstrip('/')}/{hold_id}"
    # Dev stub: replace with a real hosted checkout (Stripe Payment Links, Paddle).
    return f"https://pay.example.com/checkout/{hold_id}?amount={total}&currency={currency}"


@mcp.tool()
async def search_activities(
    destination: str,
    date: str | None = None,
    travelers: int = 2,
    category: str | None = None,
    max_price_usd: float | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search bookable tours & activities in an Asian destination.

    destination: city/place, e.g. 'Tokyo', 'Bali', 'Bangkok'.
    date: preferred date YYYY-MM-DD (optional, improves relevance).
    """
    try:
        results = await _get_provider().search(
            destination, date=date, travelers=travelers,
            category=category, max_price=max_price_usd, limit=limit)
    except ProviderError as e:
        return [{"error": str(e)}]
    return [r.__dict__ for r in results]


@mcp.tool()
async def get_activity_details(product_code: str) -> dict:
    """Full details for one activity: description, highlights, cancellation policy."""
    try:
        return (await _get_provider().get_details(product_code)).__dict__
    except ProviderError as e:
        return {"error": str(e)}


@mcp.tool()
async def check_availability(product_code: str, date: str, travelers: int = 2) -> list[dict]:
    """Check live availability & total price for a product on a date (YYYY-MM-DD)."""
    try:
        slots = await _get_provider().check_availability(product_code, date, travelers)
    except ProviderError as e:
        return [{"error": str(e)}]
    return [s.__dict__ for s in slots]


@mcp.tool()
async def create_booking_hold(
    product_code: str,
    date: str,
    travelers: int,
    contact_name: str,
    contact_email: str,
    contact_phone: str | None = None,
) -> dict:
    """Reserve inventory and get a payment link. The booking is NOT confirmed
    until the traveler pays and confirm_booking is called."""
    provider = _get_provider()
    try:
        details = await provider.get_details(product_code)
        hold = await provider.create_hold(
            product_code, date, travelers,
            {"name": contact_name, "email": contact_email, "phone": contact_phone})
    except ProviderError as e:
        return {"error": str(e)}
    store = _get_store()
    # payment_url needs the hold id, so create the row first with a temp URL then patch
    row = store.create_hold(
        product_code=product_code, title=details.title, date=date, travelers=travelers,
        total=hold.total, currency=hold.currency, contact_name=contact_name,
        contact_email=contact_email, provider=provider.name,
        provider_hold_ref=hold.provider_ref, payment_url="",
        ttl_minutes=config.get_hold_ttl_minutes())
    url = _payment_url(row["id"], hold.total, hold.currency)
    store._db.execute("UPDATE holds SET payment_url=? WHERE id=?", (url, row["id"]))
    store._db.commit()
    row["payment_url"] = url
    return {
        "hold_id": row["id"],
        "product": details.title,
        "date": date,
        "travelers": travelers,
        "total": hold.total,
        "currency": hold.currency,
        "payment_url": url,
        "expires_at": row["expires_at"],
        "next_step": "Share payment_url with the traveler. After payment, call confirm_booking.",
    }


@mcp.tool()
async def confirm_booking(hold_id: str) -> dict:
    """Confirm a paid hold into a booking. In production call this from your
    payment webhook after successful payment."""
    store = _get_store()
    hold = store.get_hold(hold_id)
    if not hold:
        return {"error": f"Unknown hold: {hold_id}"}
    if hold["status"] != "awaiting_payment":
        return {"error": f"Hold {hold_id} is already {hold['status']}"}
    if datetime.fromisoformat(hold["expires_at"]) < datetime.now(timezone.utc):
        return {"error": f"Hold {hold_id} expired at {hold['expires_at']}"}
    provider = _get_provider()
    try:
        pb = await provider.confirm_hold(
            hold["provider_hold_ref"],
            {"name": hold["contact_name"], "email": hold["contact_email"]})
    except ProviderError as e:
        return {"error": str(e)}
    booking = store.create_booking(hold, pb.provider_ref)
    store.mark_hold_confirmed(hold_id)
    return {
        "booking_ref": booking["ref"],
        "status": booking["status"],
        "product": booking["title"],
        "date": booking["date"],
        "travelers": booking["travelers"],
        "total": booking["total"],
        "currency": booking["currency"],
        "provider_ref": pb.provider_ref,
    }


@mcp.tool()
async def get_booking(booking_ref: str) -> dict:
    """Look up a booking by its reference (ATB-XXXXXXXX)."""
    booking = _get_store().get_booking(booking_ref)
    if not booking:
        return {"error": f"Unknown booking: {booking_ref}"}
    return booking


@mcp.tool()
async def cancel_booking(booking_ref: str, reason: str | None = None) -> dict:
    """Cancel a booking upstream and mark it cancelled locally."""
    store = _get_store()
    booking = store.get_booking(booking_ref)
    if not booking:
        return {"error": f"Unknown booking: {booking_ref}"}
    if booking["status"] == "CANCELLED":
        return {"booking_ref": booking_ref, "status": "CANCELLED",
                "note": "Already cancelled"}
    try:
        await _get_provider().cancel_booking(booking["provider_booking_ref"], reason)
    except ProviderError as e:
        return {"error": str(e)}
    store.mark_booking_cancelled(booking_ref)
    return {"booking_ref": booking_ref, "status": "CANCELLED"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
