"""Registry and factory for FX rate providers."""

from __future__ import annotations

import os
from typing import Callable, Dict, Iterable, List

from .base import BaseRateProvider, ProviderError

ProviderFactory = Callable[[], BaseRateProvider]

_PROVIDER_FACTORIES: Dict[str, ProviderFactory] = {}


def _default_factories() -> Iterable[tuple[str, ProviderFactory]]:
    from flask import current_app

    from .exchangerate_provider import ExchangeRateHostProvider
    from .frankfurter_provider import FrankfurterProvider
    from .mock import MockRateProvider

    factories: list[tuple[str, ProviderFactory]] = [
        (MockRateProvider.name, MockRateProvider),
    ]

    def exchangerate_factory() -> ExchangeRateHostProvider:
        config = current_app.config
        return ExchangeRateHostProvider.from_config(config)

    def frankfurter_factory() -> FrankfurterProvider:
        config = current_app.config
        return FrankfurterProvider.from_config(config)

    factories.append((ExchangeRateHostProvider.name, exchangerate_factory))
    factories.append((FrankfurterProvider.name, frankfurter_factory))

    return factories


def register_provider(name: str, factory: ProviderFactory) -> None:
    """Register a provider factory under the given name."""

    if not name:
        raise ValueError("Provider name cannot be empty.")
    normalized = name.lower()
    _PROVIDER_FACTORIES[normalized] = factory


def unregister_provider(name: str) -> None:
    """Remove a provider factory; primarily for testing."""

    _PROVIDER_FACTORIES.pop(name.lower(), None)


def list_providers() -> List[str]:
    """Return the list of registered provider identifiers."""

    return sorted(_PROVIDER_FACTORIES.keys())


def _resolve_name(name: str | None = None) -> str:
    return (name or os.getenv("FX_RATE_PROVIDER") or "mock").lower()


def get_provider(name: str | None = None) -> BaseRateProvider:
    """Instantiate a provider using the supplied or configured name."""

    provider_name = _resolve_name(name)
    try:
        factory = _PROVIDER_FACTORIES[provider_name]
    except KeyError as exc:
        available = ", ".join(list_providers()) or "none registered"
        raise ProviderError(
            f"Unknown provider '{provider_name}'. Available providers: {available}"
        ) from exc
    return factory()


def init_provider(app) -> BaseRateProvider:
    """Attach the configured provider to the Flask app."""

    provider_name = app.config.get("FX_RATE_PROVIDER")
    provider = get_provider(provider_name)
    app.extensions["rate_provider"] = provider
    return provider


def reset_registry(default_factories: Iterable[tuple[str, ProviderFactory]] | None = None) -> None:
    """Reset provider registry; useful for tests."""

    _PROVIDER_FACTORIES.clear()

    factories = default_factories or _default_factories()
    for name, factory in factories:
        register_provider(name, factory)


reset_registry()

