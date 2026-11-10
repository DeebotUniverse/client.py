"""Native map id validation (Y1 Pro)."""

from __future__ import annotations


def valid_mid(value: object) -> str | None:
    """Return trimmed map id or None for missing/transient ids.

    Only str and int (never bool) ids are accepted; float, collections,
    empty strings and the transient id 0 are rejected.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, int):
        text = str(value)
    else:
        return None
    if not text or text == "0":
        return None
    return text
