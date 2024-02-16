"""Command constants module."""
from __future__ import annotations

CHARGE_STATE_IS_CHARGING = 1
# 30007 -> Already charging
CHARGE_STATE_FAIL_CHARGING = {"30007"}
# 3 -> Bot in stuck state, example dust bin out
# 5 -> Busy with another command
CHARGE_STATE_FAIL_ERROR = {"3", "5"}

CLEAN_DEFAULT_CLEANINGS = 1

MAP_TRACE_POINT_COUNT = 200
