"""Runtime configuration from environment variables."""
from __future__ import annotations

import os


def get_provider_name() -> str:
    return os.environ.get("TRAVEL_PROVIDER", "mock").lower()


def get_viator_api_key() -> str | None:
    return os.environ.get("VIATOR_API_KEY")


def get_db_path() -> str:
    return os.environ.get("TRAVEL_DB_PATH", "data/bookings.db")


def get_payment_link_base() -> str | None:
    """Base URL for hosted payment links. Replace with your Stripe Payment
    Link / Paddle checkout base URL in production."""
    return os.environ.get("PAYMENT_LINK_BASE")


def get_hold_ttl_minutes() -> int:
    return int(os.environ.get("HOLD_TTL_MINUTES", "30"))
