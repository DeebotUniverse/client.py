"""Countries util."""

from __future__ import annotations

_MAP_COUNTRY: dict[str, str] = {"GB": "UK"}


def get_ecovacs_country(alpha_2_country: str) -> str:
    """Get the country used by ecovacs from a ISO 3166 alpha2 country."""
    return _MAP_COUNTRY.get(alpha_2_country, alpha_2_country)
