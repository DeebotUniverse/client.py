# GOAT O500: Home Assistant deployment and live checks

Home Assistant could show that a mowing command had succeeded even when the GOAT O500 did nothing, and it could keep showing an old error after the mower recovered. The integration was using an unsupported command for reading the mower's activity and was missing some of the mower's status messages. This update uses the O500's supported commands, reads its actual activity after accepted controls and cleared faults, and handles the missing status messages. Automated tests pass; the final check is to install this revision on the Home Assistant server and confirm that Lawna2 responds and reports its state correctly.

This is a patch for supervised dogfood, not an upstream or PyPI release. The
upstream contribution is draft
[PR 1847](https://github.com/DeebotUniverse/client.py/pull/1847).

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

## Live acceptance checks for Lawna2

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

## What remains conditional

Header version is not resolved by the existing evidence. The original O500 iOS
capture uses `0.0.50`, while later O500 reports associate `0.0.22` with successful
controls. If the unchanged request returns 20003, report that response first;
an otherwise identical mower-only version comparison is the next experiment.
Do not change the shared vacuum header or rewrite all header fields at once.

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

Keep PR 1847 draft until the live results are recorded. The handoff is ready for
deployment testing; automated tests alone do not establish physical mower
control.
