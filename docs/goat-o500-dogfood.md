# GOAT O500: Home Assistant deployment and live checks

Home Assistant could show that a mowing command had succeeded even when the GOAT O500 did nothing, and it could keep showing an old error after the mower recovered. The integration was using an unsupported command for reading the mower's activity and was missing some of the mower's status messages. This update uses the O500's supported commands, reads its actual activity after accepted controls and cleared faults, and handles the missing status messages. Mike confirmed start, pause, resume and docking on Lawna2 in daylight on 28 September 2026 using the nine-file overlay from `f2d53716f20d9bdcf1c0fa6fc1bc7ab15bc51d14`. The live evidence and its limits are recorded below.

This is a patch for supervised dogfood, not an upstream or PyPI release. The
upstream contribution is draft
[PR 1847](https://github.com/DeebotUniverse/client.py/pull/1847).

**29 September follow-up:** Mike subsequently reported a morning error and an
offline mower, then confirmed Lawna2 was physically stuck and had been manually
docked and was charging. See the [follow-up investigation](goat-o500-follow-up-2026-09-29.md)
for the evidence, a small charging-state reporting fix, and the next retest.
The historical nine-file overlay and successful run below remain the baseline.
Grok Bot subsequently reported deploying the ten-file `3132dfb` candidate with
verified hashes: HA showed stable docked activity and rising battery after the
restart. No mower commands were tested on that revision. Keep the upstream PR
draft; neither this recovery nor the earlier control cycle establishes
unattended reliability.

## Confirmed daylight dogfood: 28 September 2026

Mike reported the following supervised run on the Isle of Man at approximately
16:17-16:25 BST, after Home Assistant recovered from a house power cut.

- Device: Ecovacs GOAT O500 Panorama, hardware class `300lc5`, Lawna2
  (`lawn_mower.lawna2`).
- Runtime: HA Core with the installed package still reporting
  `deebot-client==18.5.1`; the complete nine-file Python overlay listed below
  came from [`f2d53716f20d9bdcf1c0fa6fc1bc7ab15bc51d14`](https://github.com/MikeWGitHub/client.py/commit/f2d53716f20d9bdcf1c0fa6fc1bc7ab15bc51d14).
  The existing native `deebot_client.rs` extension was retained.
- JSON header version remained `0.0.50` throughout this run.

| HA action | Reported live result |
| --- | --- |
| `lawn_mower.start_mowing` | HTTP 200, then HA showed `mowing`; the Ecovacs app confirmed the mower was off dock and cutting, not merely beeping. |
| Pause | HA and the app agreed that the mower was paused. |
| Resume via `lawn_mower.start_mowing` | Mowing resumed, with app confirmation. |
| Dock | Activity changed to `returning`, then `docked`, at about 67% battery. |

An HA HTTP 200 alone is insufficient evidence of success. This run adds
reported activity transitions and app confirmation of actual mowing. It
confirms the start/pause/resume/dock path in this local overlay setup; it does
not claim a captured raw protocol response for each action, a separate stop or
spot-area test, or fault-clear/scheduled-message validation.

Night tests are excluded from the success evidence: Ecovacs refused operation
with insufficient light / weak GPS reports. This daylight result validates
`0.0.50` in the tested setup; no `0.0.22` override was needed.

The house source of truth remains
[`MikeWGitHub/client.py` on `cursor/goat-o500-clean-commands-e8d8`](https://github.com/MikeWGitHub/client.py/tree/cursor/goat-o500-clean-commands-e8d8),
with the live overlay pinned to the tested commit above. Recording these
results does not change the live HA overlay, switch its installation source,
or merge either PR. Upstream
[PR 1847](https://github.com/DeebotUniverse/client.py/pull/1847) and
[fork PR 1](https://github.com/MikeWGitHub/client.py/pull/1) must contain the
tested commit or a strict successor containing only review polish before
being marked ready for review.

## What is included

- `300lc5` selects `CleanMower`/`CleanAreaMower`: the `clean` command with nested
  `content.type`. Other hardware definitions keep their existing clean commands.
- O500 activity refresh uses `getChargeState` and `getCleanInfo`, not
  `getCleanInfo_V2`.
- Accepted mower clean commands request a fresh activity read. Accepted charge
  commands also request it for mower devices.
- `onCleanInfo` has an explicit handler shared with `GetCleanInfo`. Existing
  legacy aliases and vacuum decoding continue working.
- Mower `onScheduleTaskInfo` updates activity. Mower `onChargeInfo` handles
  returning and alerts; an idle charge message requests a state read rather than
  assuming the robot is physically docked.
- Clearing a mower error while activity is still ERROR requests real activity
  once per error episode, including when the cached error code was already zero.
  Repeated error-free reports do not create a polling loop. Active errors and
  `trigger: alert` still report ERROR.
- These recovery reads queue one follow-up when a state poll is already running,
  so a stale in-flight response cannot consume the post-control refresh.
  Other refresh callers keep their existing behavior.

## Deploy a pinned commit

Use the exact full commit SHA supplied with the handoff, from
`MikeWGitHub/client.py`, branch `cursor/goat-o500-clean-commands-e8d8`.
Do not select the moving branch tip or a similarly named upstream release.

The existing installation was reported as HA Core 2026.9.2 with
`deebot-client==18.5.1` and a local overlay. Discover the actual server runtime
and overlay before deploying: a Python shell in an add-on is not necessarily
the Python environment used by HA Core.

1. Record the installed HA/Python/client versions, active overlay location,
   current source hashes and rollback copy. Preserve any unrelated local fixes.
2. Fetch the fork at the pinned SHA. For the existing 18.5.1 overlay, update the
   complete set of runtime files below together, including the two new modules.
   These existing source files were checked against the 18.5.1 wheel at the
   upstream base. If the server has a different package or additional patches,
   compare the files before applying this overlay.
3. Keep the server's native `deebot_client.rs` extension. No Rust changes or
   macOS binaries are part of this patch. Do not blindly `pip install` this
   development branch: its package version is 0.0.0 and HA pins its dependency.
4. Use the server's established persistent overlay mechanism, then restart HA
   Core so all imports and cached capabilities are rebuilt. Verify persistence
   after that restart. A partial module reload is insufficient.
5. Run the local checks below in the actual HA Python environment. Compare the
   imported files' SHA-256 hashes against the same files from the pinned commit.
   Record the deployment SHA outside the upstream package version metadata.

All runtime files needed relative to the package parent:

```text
deebot_client/commands/json/__init__.py
deebot_client/commands/json/charge.py
deebot_client/commands/json/clean.py
deebot_client/commands/json/error.py
deebot_client/event_bus.py
deebot_client/hardware/300lc5.py
deebot_client/messages/json/__init__.py
deebot_client/messages/json/charge_info.py
deebot_client/messages/json/clean_info.py
```

The new modules are required: copying only `300lc5.py` and `clean.py` can break
imports or leave the state-recovery fix incomplete.

## Read-only runtime check

This snippet imports local code and constructs commands. It does not log in,
send a device command or contact the mower.

```python
import asyncio
import hashlib
import importlib.metadata
from pathlib import Path

import deebot_client
from deebot_client.commands.json import COMMANDS, CleanMower
from deebot_client.commands.json.clean import CleanAreaMower, GetCleanInfo
from deebot_client.hardware import get_static_device_info
from deebot_client.messages import get_message
from deebot_client.models import CleanAction

async def check():
    info = await get_static_device_info("300lc5")
    assert info is not None
    caps = info.capabilities
    assert caps.clean.action.command is CleanMower
    assert caps.clean.action.area is CleanAreaMower
    assert [c.NAME for c in caps.state.get] == ["getChargeState", "getCleanInfo"]
    assert type(caps.state.get[1]) is GetCleanInfo
    for name in ("onCleanInfo", "onScheduleTaskInfo", "onChargeInfo"):
        handler = get_message(name, info)
        assert handler is not None
        print(name, handler.__module__, handler.__name__)
    for action in CleanAction:
        command = caps.clean.action.command(action)
        print(action.value, command.NAME, command._get_payload())
    print("global clean lookup:", COMMANDS["clean"].__name__)
    print("installed distribution:", importlib.metadata.version("deebot-client"))
    root = Path(deebot_client.__file__).parent
    print("imported package:", root)
    for rel in (
        "commands/json/__init__.py", "commands/json/charge.py",
        "commands/json/clean.py", "commands/json/error.py", "event_bus.py",
        "hardware/300lc5.py",
        "messages/json/__init__.py", "messages/json/charge_info.py",
        "messages/json/clean_info.py",
    ):
        path = root / rel
        print(rel, hashlib.sha256(path.read_bytes()).hexdigest())

asyncio.run(check())
```

The expected header version in this revision is still `0.0.50`. Changing it
silently would invalidate the comparison below.

## Repeatable live acceptance checks for Lawna2

Deploying and checking imports is separate from operating the mower. Coordinate
the physical command sequence with Mike. Record timestamps and compare the HA
entity, Ecovacs app and observed device response, one command at a time.

1. Refresh `lawn_mower.lawna2` with `homeassistant.update_entity`. Confirm outgoing
   `getChargeState` and `getCleanInfo` in logs, their raw responses, and the
   resulting StateEvent. Refresh the actual battery/current-area/duration
   entities separately; discover their entity IDs instead of guessing them.
2. For an Auto run, check start, pause, start-as-resume, and dock. HA has no
   separate standard mower stop/end service. For each command save the actual
   `cmdName`, header and body, outer `ret`/`errno`, inner response code/message,
   and following activity events. HTTP 200 from HA alone is not a pass.
3. An accepted start needs both an inner command response `code: 0` and a
   subsequent working activity/device response. A charge ACK can immediately
   say RETURNING, but docking needs the charge-state confirmation.
4. If an existing fault is cleared through the app, verify that code zero leads
   to a fresh activity query and the real state. Do not induce a blade fault to
   perform this check. This patch does not dismiss faults or bypass them.
5. If a normal scheduled run occurs, inspect `onScheduleTaskInfo`; inspect
   `onChargeInfo` on return/completion. The initial handler fixtures come from
   another GOAT model, so retain O500 payloads for confirmation.

Capture DEBUG output for `deebot_client` and the Ecovacs integration only for
the test window. Redact account tokens, identifiers and network details before
sharing. Report the ordered command/event sequence, not just the final entity
snapshot, then restore the previous log levels.

## Optional follow-ups and evidence limits

The daylight run above succeeded with header `0.0.50`. It does not establish
compatibility for every firmware or transport. A mower-only `0.0.22`
comparison is an optional later experiment if a reproducible rejection such
as 20003 occurs; document the `0.0.50` result first. Do not change the shared
vacuum header or rewrite all header fields at once.

Ghost area/duration values and sticky error latching remain optional follow-ups,
not blockers for the confirmed start/pause/resume/dock result. No fault-clear
test is claimed for this run. After a Core update or rebuild, the established
overlay may need to be re-applied and its imports/hashes rechecked; this note
does not authorize changing the live installation.

An ACK followed by stale activity needs event/readback investigation instead.
An old battery timestamp alone does not establish whether updates stopped,
since identical values are suppressed. Area/duration and battery freshness are
not proven fixed by this patch; compare actual received values and units.

Separate HA pause/resume requests still default to Auto, so continuation of
app-started area jobs is not claimed as validated. HA's service methods still
do not surface every client rejection as a failed service call; improving that
error contract is a separate client/HA change.

If imports or basic entity updates regress, restore the saved overlay files,
remove the new modules if they were previously absent, restart HA Core and
verify the previous revision. Report the SHA and failing check before retrying.

The confirmed daylight results are now recorded. Keep PR 1847 draft pending
review preparation, including verification that its tip is the tested commit
or a strict successor containing only review polish. This guide adds evidence;
it does not change runtime code or the installation source.
