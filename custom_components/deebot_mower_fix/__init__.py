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
# All GOAT mower device classes affected by the clean_V2 bug.
# These are the 4 canonical hardware files plus every symlinked alias.
# ---------------------------------------------------------------------------
_GOAT_CLASSES: tuple[str, ...] = (
    # 5xu9h3.py family (GOAT G1 / O1000 LiDAR Pro and variants)
    "5xu9h3", "0jbd6s", "2ap5uq", "2i0fns", "6n9pcz", "77atlz",
    "9bts2s", "aadham", "ao7fpq", "bfvvk", "qhq6i0", "s69g6z", "wwswjm",
    # 300lc5.py family
    "300lc5", "6cibhb",
    # 51rcxt.py family
    "51rcxt", "2px96q",
    # xmp9ds.py
    "xmp9ds",
)


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
        Clean = clean_mod.Clean

        class CleanMower(Clean):  # type: ignore[misc,valid-type]
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

    CleanMower = clean_mod.CleanMower
    GetCleanInfo = getattr(clean_mod, "GetCleanInfo", None)

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

        try:
            mod = importlib.import_module(f"deebot_client.hardware.{class_}")
        except ModuleNotFoundError:
            _LOGGER.debug("No hardware module for class %s; skipping", class_)
            continue

        changed = False

        # Replace CleanV2 → CleanMower in the module's global namespace so
        # get_device_info() produces the correct CapabilityCleanAction.
        if getattr(mod, "CleanV2", None) is not None:
            mod.CleanV2 = CleanMower  # type: ignore[attr-defined]
            changed = True

        # Replace GetCleanInfoV2 → GetCleanInfo so state polling uses the
        # correct topic.
        if getattr(mod, "GetCleanInfoV2", None) is not None and GetCleanInfo:
            mod.GetCleanInfoV2 = GetCleanInfo  # type: ignore[attr-defined]
            changed = True

        if changed:
            # Evict any stale cached entry and rebuild with the patched module
            devices_cache.pop(class_, None)
            devices_cache[class_] = mod.get_device_info()
            patched += 1
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
