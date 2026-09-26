"""Provider factory."""
from __future__ import annotations

from ..config import get_provider_name, get_viator_api_key
from .base import ActivityProvider, ProviderError
from .mock import MockProvider
from .viator import ViatorProvider


def get_provider() -> ActivityProvider:
    name = get_provider_name()
    if name == "viator":
        key = get_viator_api_key()
        if not key:
            raise ProviderError("TRAVEL_PROVIDER=viator requires VIATOR_API_KEY")
        return ViatorProvider(key)
    if name == "mock":
        return MockProvider()
    raise ProviderError(f"Unknown TRAVEL_PROVIDER: {name} (use 'mock' or 'viator')")
