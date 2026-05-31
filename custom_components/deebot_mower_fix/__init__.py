"""deebot_mower_fix – Home Assistant custom component.

Patches the installed ``deebot_client`` library so GOAT lawnmower devices
use the correct MQTT topic (``clean``, not ``clean_V2``) for all clean
commands.  Without this patch the mower logs:

    No response received for command "clean_V2"

and never starts, pauses, or stops.

Installation
------------
1. Copy the ``custom_components/deebot_mower_fix/`` directory into your HA
   ``config/custom_components/`` folder.
2. Add ``deebot_mower_fix:`` to ``configuration.yaml``.
3. Restart Home Assistant.

The patch is applied once at startup and is safe to leave in place even
after ``deebot_client`` is updated — if the installed version already
contains ``CleanMower`` the component logs a message and does nothing.

References
----------
- https://github.com/DeebotUniverse/client.py/issues/1467
- https://github.com/DeebotUniverse/client.py/issues/852
- https://github.com/home-assistant/core/issues/170261
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)
DOMAIN = "deebot_mower_fix"

# ---------------------------------------------------------------------------
# GOAT mower device classes grouped by required payload format.
#
# V1-flat family (5xu9h3 / O1000 LiDAR Pro and variants):
#   Firmware accepts the legacy clean topic AND the legacy flat payload:
#   START  → {"act": "start", "type": "auto"}
#   PAUSE  → {"act": "pause"}
#   STOP   → {"act": "stop"}
#   RESUME → {"act": "resume"}
#
# V2-content family (xmp9ds A1600 RTK, 300lc5, 51rcxt):
#   Firmware accepts the legacy clean topic with a V2 nested payload:
#   START  → {"act": "start",  "content": {"type": "auto"}}
#   PAUSE  → {"act": "pause",  "content": {"type": "auto"}}
#   STOP   → {"act": "stop",   "content": {"type": "auto"}}
#   RESUME → {"act": "resume", "content": {"type": "auto"}}
# ---------------------------------------------------------------------------

# Uses flat V1 payload (no nested content object)
_GOAT_V1_CLASSES: tuple[str, ...] = (
    "5xu9h3", "0jbd6s", "2ap5uq", "2i0fns", "6n9pcz", "77atlz",
    "9bts2s", "aadham", "ao7fpq", "bfvvk", "qhq6i0", "s69g6z", "wwswjm",
)

# Uses V2 nested content payload (confirmed by MQTT traces in issue #852)
_GOAT_V2_CLASSES: tuple[str, ...] = (
    "xmp9ds",
    "300lc5", "6cibhb",
    "51rcxt", "2px96q",
)

_GOAT_CLASSES: tuple[str, ...] = _GOAT_V1_CLASSES + _GOAT_V2_CLASSES


# ---------------------------------------------------------------------------
# Core patch logic (synchronous – called via executor)
# ---------------------------------------------------------------------------

def _apply_patch() -> None:
    """Inject CleanMower and patch all known GOAT hardware modules."""

    # ── Step 1: ensure CleanMower exists in the installed deebot_client ─────
    try:
        clean_mod = importlib.import_module("deebot_client.commands.json.clean")
    except ImportError:
        _LOGGER.error("deebot_client is not installed; patch cannot be applied")
        return

    if hasattr(clean_mod, "CleanMower"):
        _LOGGER.info(
            "deebot_mower_fix: CleanMower already present in installed "
            "deebot_client — no injection needed"
        )
    else:
        # Older install: define CleanMower as a Clean subclass with V2 args
        _LOGGER.warning(
            "deebot_mower_fix: CleanMower missing from installed deebot_client; "
            "injecting compatibility class"
        )
        _base_clean = clean_mod.Clean

        class CleanMower(_base_clean):  # type: ignore[misc,valid-type]
            """Clean command for mower devices (legacy topic, V2 content payload)."""

            _v2_args: ClassVar[bool] = True

        clean_mod.CleanMower = CleanMower  # type: ignore[attr-defined]

        # Also expose from the json commands package if present
        try:
            json_pkg = importlib.import_module("deebot_client.commands.json")
            if not hasattr(json_pkg, "CleanMower"):
                json_pkg.CleanMower = CleanMower  # type: ignore[attr-defined]
        except ImportError:
            pass

    # CleanMower uses V2 nested payload: {"act": "start", "content": {"type": "auto"}}
    # CleanMowerFlat uses V1 flat payload: {"act": "start", "type": "auto"} (no content wrapper)
    # The O1000 LiDAR Pro (5xu9h3 family) rejects the nested format with code 20003.
    _clean_mower_v2 = clean_mod.CleanMower
    _base_clean_for_flat = clean_mod.Clean

    class _CleanMowerFlat(_base_clean_for_flat):  # type: ignore[misc,valid-type]
        """Clean command with V1 flat payload for older GOAT firmware.

        Sends {"act": "start", "type": "auto"} instead of the nested
        {"act": "start", "content": {"type": "auto"}} that causes error 20003
        on 5xu9h3-family firmware.
        """

        _v2_args: ClassVar[bool] = False

    get_clean_info = getattr(clean_mod, "GetCleanInfo", None)

    # ── Step 2: patch each hardware module and warm the device cache ─────────
    try:
        hw_mod = importlib.import_module("deebot_client.hardware")
    except ImportError:
        _LOGGER.error("deebot_client.hardware not found; skipping hardware patch")
        return

    devices_cache: dict[str, Any] = hw_mod._DEVICES  # type: ignore[attr-defined]  # noqa: SLF001
    not_found_cache: set[str] = hw_mod._NOT_FOUND  # type: ignore[attr-defined]  # noqa: SLF001

    patched = 0
    already_fixed = 0
    for class_ in _GOAT_CLASSES:
        not_found_cache.discard(class_)

        # Choose the right CleanMower variant for this hardware family:
        # V1-flat families (5xu9h3/O1000 etc.) use the flat payload to avoid
        # firmware error 20003 "unknow type" caused by the nested content object.
        clean_cmd = _CleanMowerFlat if class_ in _GOAT_V1_CLASSES else _clean_mower_v2

        try:
            mod = importlib.import_module(f"deebot_client.hardware.{class_}")
        except ModuleNotFoundError:
            _LOGGER.debug("No hardware module for class %s; skipping", class_)
            continue

        changed = False

        # Replace CleanV2 → appropriate CleanMower variant so get_device_info()
        # produces the correct CapabilityCleanAction.
        if getattr(mod, "CleanV2", None) is not None:
            mod.CleanV2 = clean_cmd  # type: ignore[attr-defined]
            changed = True

        # Replace GetCleanInfoV2 → GetCleanInfo so state polling uses the
        # correct topic.
        if getattr(mod, "GetCleanInfoV2", None) is not None and get_clean_info:
            mod.GetCleanInfoV2 = get_clean_info  # type: ignore[attr-defined]
            changed = True

        if changed:
            # Evict any stale cached entry and rebuild with the patched module
            devices_cache.pop(class_, None)
            devices_cache[class_] = mod.get_device_info()
            patched += 1
            _LOGGER.debug(
                "deebot_mower_fix: patched %s with %s payload",
                class_,
                "flat-V1" if class_ in _GOAT_V1_CLASSES else "nested-V2",
            )
        else:
            already_fixed += 1

    _LOGGER.info(
        "deebot_mower_fix: done — %d class(es) patched, %d already correct",
        patched,
        already_fixed,
    )


# ---------------------------------------------------------------------------
# Home Assistant entry points
# ---------------------------------------------------------------------------

async def async_setup(hass: Any, config: Any) -> bool:
    """Set up the deebot_mower_fix component and apply the patch."""
    _LOGGER.info("deebot_mower_fix: starting up, applying CleanMower patch …")
    await hass.async_add_executor_job(_apply_patch)
    return True
