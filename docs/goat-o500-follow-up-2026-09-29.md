# GOAT O500 follow-up: 29 September 2026

Lawna2's controls worked in the supervised daylight test, but the next morning Home Assistant showed an error and the mower later went offline. Mike subsequently found her physically stuck, then manually docked her and confirmed charging. That makes a real device problem a credible explanation; it does not prove when she became stuck or which command moved her. This candidate corrects a separate, reproducible bug that could label certain charging-query failures as “docked”, and adds logs showing whether a start request becomes resume. It preserves the working command format. The morning command failure and later loss of contact have not been reconstructed from raw logs, and this is not a confirmed fix for either.

## Revision and evidence

- Proven daylight control revision: `f2d53716f20d9bdcf1c0fa6fc1bc7ab15bc51d14`,
  deployed as the original nine-file overlay onto `deebot-client==18.5.1`.
- Fork tip at the start of this investigation:
  `19375cc9c724a1d4ebcb574535859ff667cec45b`. Its sole change since `f2d5371`
  was the daylight-test documentation. **There was no runtime drift.**
- Mike's report: the 29 September sunrise automation ran at approximately
  07:46 BST with its rain gate allowing the run. HA changed from “paused” to
  “error”; mower and battery later became unavailable at 12:27:12 UTC
  (13:27 BST). These are reported HA observations, not a raw device trace.
- Mike then confirmed the app also showed offline, that the mower was stuck,
  and that she was subsequently manually docked and charging. HA's recovery
  after docking still needs checking.
- HA itself was reachable during investigation and returned HTTP 401 from its
  API. No authenticated HA session was available here. Live package hashes,
  automation traces, device error codes and MQTT/API logs were not inspected.

## What the code establishes

### “Paused” does not establish that a resume command was sent

[HA Core 2026.9.2](https://github.com/home-assistant/core/blob/2026.9.2/homeassistant/components/ecovacs/lawn_mower.py)
maps both client `IDLE` and `PAUSED` to HA `paused`. It calls `CleanAction.START`
for `start_mowing`. In `commands/json/clean.py`, only cached client `PAUSED`
converts START to RESUME; IDLE, ERROR and DOCKED send START.

The cache can be stale. State refresh runs `getChargeState` and `getCleanInfo`
concurrently. A synthetic replay confirms that `isCharging: 1` followed by a
clean `motionState: pause` leaves PAUSED; the reverse order leaves DOCKED.
The existing event-bus guard preserves DOCKED against IDLE, but not PAUSED.
These are reproducible ordering properties, not evidence that Lawna2 sent those
messages overnight. Changing that precedence or forcing every start to START
could break a real paused job; capture both replies and their order first.

### Error and unavailable are different paths

- `GetError`/`onError` with a non-zero last code, and clean/charge/schedule
  messages with `trigger: alert`, can produce client ERROR. A failed `clean`
  command alone does not emit that activity. A physical obstruction is now a
  plausible real fault, so clearing the cached error on every start would hide
  relevant information. The client does not implement app fault dismissal.
- The `f2d5371` recovery already requests activity after a received error-free
  report while cached activity is ERROR. It does not guarantee the device sent
  a clearance message or that the refresh succeeded while offline.
- Device availability is separate. Outer `errno: 4200` marks it unavailable;
  the availability worker also marks it unavailable when its battery probe
  cannot successfully reach/handle the device. It retries after its 60-second
  interval when recent successful traffic has not suppressed the probe.
- A normal MQTT transport loss is retried every five seconds. Authentication
  failures and unexpected exceptions can terminate that MQTT worker; the
  logs distinguish these from a transport reconnect. REST availability polling
  is separate. App offline corroborates loss of app/device contact and does
  not establish an HA-only reconnect defect, battery exhaustion, or a specific
  cloud/network cause. No reconnect rewrite is justified by this evidence.
- Automation `current: 0` means its HA action sequence finished. HA still
  ignores the client's failed-command result, so HTTP 200 and a completed
  automation are not evidence of accepted mowing.

### Confirmed bug and minimal candidate

`GetChargeState._handle_body` already decodes string failure codes `"3"` and
`"5"` as ERROR, but then unconditionally emitted DOCKED. The candidate emits
the decoded `status` instead. String `"30007"` still means already charging
and emits DOCKED; a successful `isCharging: 1` reading is unchanged. This
shared JSON-handler correction applies to vacuums as well as mowers. It does
not add new numeric-code mappings or change their existing interpretation.

`CleanMower._execute` now logs the requested action and cached client state,
then the actual sent action and handling result. For example, the synthetic
PAUSED case produces:

```text
Mower clean request: action=start, cached_state=PAUSED
Mower clean result: sent_action=resume, handling=SUCCESS
```

These logs contain no account credentials or device identifiers. Existing API
DEBUG logs remain necessary for the raw payload and response. The candidate
does not alter clean bodies, the START/RESUME conversion, header `0.0.50`,
fault dismissal, availability policy or the successful nine-file overlay's
state-recovery behaviour. No live mower commands were sent in this investigation.

## Automated verification

- The new charge-state tests failed on the original code: string `"3"`/`"5"`
  emitted DOCKED for both mower and vacuum fixtures. They pass with the one-line
  correction; already-charging behaviour is preserved.
- The diagnostic tests verify actual sent payloads for cached PAUSED, IDLE and
  ERROR, with accepted and rejected responses. They do not simulate real telemetry.
- Full non-Docker suite: **883 passed**, 11 Docker tests deselected, four snapshots
  passed; one existing pytest parametrisation deprecation warning. The first
  sandboxed run could not open the local authentication test server (28 fixture
  errors); the permitted localhost rerun passed all 883 tests.
- Mypy passed 367 source/test files; changed Python files passed Ruff lint and
  formatting checks. Independent review found no further actionable issues.
- A cold-import check passed using the published 18.5.1 wheel plus exactly the
  ten Python files below and its existing native extension. No Rust build or
  Docker/MQTT integration test was run. Live candidate validation is pending.

## Fork-only candidate deployment

Keep `MikeWGitHub/client.py`, branch `cursor/goat-o500-clean-commands-e8d8`, as
the installation source. Use the exact candidate SHA supplied with the handoff.
Keep upstream PR 1847 draft; the existing PR description is not being promoted
as proof of this new runtime revision. Both PRs share this fork branch, so a
push advances their diff automatically even while review notes remain unchanged.

Once she is online and charging, record HA/Python/client versions and preserve
the current overlay and any existing logs. First verify recovery on the deployed
baseline where practical; otherwise installation and a restart may obscure
which action restored contact. Installing this candidate is a separate test.

The candidate requires **ten** Python files relative to a stock 18.5.1 package:

```text
deebot_client/commands/json/__init__.py
deebot_client/commands/json/charge.py
deebot_client/commands/json/charge_state.py
deebot_client/commands/json/clean.py
deebot_client/commands/json/error.py
deebot_client/event_bus.py
deebot_client/hardware/300lc5.py
deebot_client/messages/json/__init__.py
deebot_client/messages/json/charge_info.py
deebot_client/messages/json/clean_info.py
```

Relative to a verified `f2d5371` overlay, only `commands/json/charge_state.py`
and `commands/json/clean.py` change. Apply the pinned complete set through the
established persistent overlay mechanism; retain the server's native `rs`/`.so`
and installed package version. Restart HA Core, then run the baseline guide's
read-only import check, adding `commands/json/charge_state.py` to its hash list.
Compare all ten hashes against the pinned revision in the actual Core runtime.
Re-check after any Core rebuild/update. Roll back to the saved files if needed;
this candidate adds no new modules beyond the original nine-file overlay.

## Short live retest and capture

1. Confirm physical charging, app online, then HA mower/battery available.
   Allow roughly two availability-check intervals. If only HA stays unavailable,
   save logs first, refresh the mower and battery entities, and check Ecovacs
   authentication/MQTT errors. A targeted integration reload is a later recovery
   step; preserve evidence before doing it. Do not start while the app is offline.
2. If the app still reports a fault, address it and dismiss it there when
   appropriate. Confirm the actual error code/clearance and fresh charging/clean
   state. Do not induce a fault or clear HA's activity manually to fake recovery.
3. In a supervised clear area, issue one HA Start. Compare the new cached-state
   and sent-action logs, inner command response, following activity, app status
   and physical movement. HTTP 200 is not sufficient.
4. Pause, use Start to resume, then Dock. Confirm physical return and charging.
   Check again after several minutes and before the next morning run: does HA
   remain docked, and if not, which incoming message changed it?
5. If any step fails, stop repeating commands and save the ordered trace:
   requested service/context, `cmdName`, header/body and actual `act`, outer
   `ret`/`errno`, inner code/message, `getChargeState`, `getCleanInfo`,
   `onCleanInfo`, `onChargeInfo`, `onScheduleTaskInfo`, `getError`/`onError`,
   `onBattery`/`getBattery`, and MQTT/authentication/reconnect errors. Record
   UTC/BST timestamps, automation trace, runtime hashes and app/device observations.

Enable `deebot_client` and `homeassistant.components.ecovacs` DEBUG logging for
the bounded test window and restore the previous levels afterwards. Redact
tokens, credentials, account/device identifiers and network details before
sharing logs publicly. Keep the original ordered log privately for diagnosis.

The old area/duration readings are not proof of movement or completed coverage.
Statistics and unit/freshness checks remain separate. The successful daylight
test used header `0.0.50`; there is no new evidence to justify `0.0.22` now.
