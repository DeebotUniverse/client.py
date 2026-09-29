# GOAT O500 follow-up: 29 September 2026

Lawna2 can mow when Mike presses Continue in the Ecovacs app, but the latest Home Assistant Start attempt still left her showing an error. The deployed update corrects a separate charging-status bug and adds diagnostic logs; it has not fixed this control failure. A local reproduction now shows that a charging report can hide a paused job from the client's Start/Resume decision. That is a concrete weakness in the code, but the retained live logs contain neither the failed command nor its response, so its role in this incident remains unproven. The next step is one supervised test with logging verified beforehand, after the current mow has finished and Mike agrees to the test. Any subsequent fix must preserve genuine faults and distinguish a current unfinished job from stale history. PR 1847 remains draft.

Mike previously relayed Grok Bot's deployment report: `3132dfb` is live, file
hashes passed after restarting HA Core, and HA then showed stable docking with
a rising battery level. No mower controls were issued in that test. This is
deployment and recovery evidence, not a validated control cycle or proof that
the code change caused recovery; the restart happened at the same time.

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
  and that she was subsequently manually docked and charging. The later
  deployment report below records HA's observed recovery.
- HA itself was reachable during investigation and returned HTTP 401 from its
  API. No authenticated HA session was available here. Live package hashes,
  automation traces, device error codes and MQTT/API logs were not inspected.

## Reported deployment and recovery: 29 September

The following observations were supplied by Grok Bot through Mike. They were
not independently read from HA or a raw protocol capture in this investigation.

| Period (BST) | Reported observation |
| --- | --- |
| Approximately 14:38 | HA briefly alternated between docked and error, then settled on error. |
| Approximately 14:50–15:01, before deployment | Lawna2 was online and charging; battery rose from 4% to 20%, while HA continued to show error. No start command was sent. |
| Deployment | Complete ten-file overlay from `3132dfbdecae632deb7d997bbad10b094f91d494`; original native extension retained, package still `deebot-client==18.5.1`, header still `0.0.50`. A rollback backup was taken and post-restart hashes passed. |
| Approximately 15:03–15:05, after deployment and restart | HA showed stable docked activity and battery rose from 20% to 22%. No mower commands were issued. |

Availability recovered **before** deployment. Activity recovered **after** both
deployment and restart, so these observations cannot separate a code effect
from new initial readings, cleared process state, or a changed device report.
The charging-query correction changes certain false DOCKED reports to ERROR;
it does not itself clear an old ERROR. Charging alongside HA error also does
not distinguish an active device fault from a cached or repeated alert without
the actual error code and incoming messages.

Keep the live runtime pinned to `3132dfb` while gathering the next evidence.
This record adds documentation only and requires no new overlay installation.
The subsequent HA Start attempt failed as reported below. A complete successful
control cycle on this revision and the next morning's ordered command/events
remain unverified. PR 1847 stays draft; raw Start/Resume response traces have
not been supplied for this report.

## Reported HA Start versus app Continue: approximately 15:51–15:54 BST

Grok Bot's next report, relayed by Mike, describes this sequence on `3132dfb`:

| Time (BST) | Reported observation |
| --- | --- |
| Approximately 15:51 | HA Start from docked at roughly 35% battery returned HTTP 200, followed by persistent HA error and no successful mowing. |
| Approximately 15:52 | Mike pressed Continue in the app. HA briefly showed docked at 14:52:00 UTC, then mowing at 14:52:16 UTC. Physical mowing was reported; battery still showed 35%. |
| 15:54 report | HA remained mowing. Area 400.96 m² and duration 312.75 minutes retained the earlier stale pattern. |

Grok Bot subsequently supplied a more precise history/logbook extraction:

| Time (BST) | Reported HA history/logbook entry |
| --- | --- |
| 15:45:00 | Docked at the beginning of the examined period. |
| 15:51:23 | Error, associated with the `lawn_mower.start_mowing` service call. |
| 15:52:00.884 | Brief mowing state. |
| 15:52:00.942 | Docked, approximately 58 ms after the preceding state. |
| 15:52:16 | Sustained mowing, attributed by Mike to app Continue. |
| 15:52:22 | Area changed from 400.0 to 400.96 m². |

Battery was reported around 32–35% during the transition and later falling
while physically mowing. The area was therefore not completely frozen, but
its retained magnitude still does not establish coverage for this run or an
unfinished job. The brief activity alternation shows state updates; without
their raw sources it does not establish physical docking, a specific event
ordering race, or which command succeeded. The current mow was left running.

The retained Core Docker logs contained **no lines for the examined
15:50–15:53 BST window**, and no `Mower clean request` or `Mower clean result`
lines anywhere in the retained output. They also lacked the request/response
and clean/charging/error payloads for the window. Grok Bot reported mostly
WARNING-level client output after the approximately 15:03 BST Core restart.
This is consistent with DEBUG output not being captured, but the log-level
configuration for that minute was not established. Log silence does not prove
START, RESUME, an absent overlay, an absent device response or fault clearance.
HA documents that levels set through
[`logger.set_level`](https://www.home-assistant.io/actions/logger.set_level/)
reset at restart unless configured persistently. Earlier DEBUG output therefore
does not establish that DEBUG remained enabled after the overlay restart.

No app Continue request was captured that day. A historical incoming
`trigger: continue` report from 28 September is not the missing 29 September
outbound request. The failed action cannot be reconstructed from these logs;
a new bounded capture is required. Do not keep asking for the missing lines.

The app comparison leaves different actions or task parameters as a plausible
explanation. The missing logs do not favour START over RESUME. This is not a
captured comparison in which only `act` changed:
the app's complete request, any extra commands, the HA command response and the
device's task reports are missing. The app button's label does not establish
the exact wire payload. The earlier physical obstruction remains a separate,
real observation; neither this comparison nor charging proves fault clearance.

### Reproduced action-selection weakness

At the runtime in `3132dfb`, the following synthetic inputs were replayed through
the actual clean/charging handlers and command code, using a mock transport.
They are test inputs, not claimed Lawna2 telemetry:

- Paused task: `{"state":"clean","cleanState":{"motionState":"pause","content":{"type":"auto"}}}`.
- Charging: `{"isCharging":1}`.
- No active task for the parser: `{"state":"idle"}`.

| Handler input order | Cached activity | Requested action | Actual clean body |
| --- | --- | --- | --- |
| Paused task, then charging | DOCKED | START | `{"act":"start","content":{"type":"auto"}}` |
| Charging, then paused task | PAUSED | START | `{"act":"resume","content":{"type":"auto"}}` |
| Paused task, then charging | DOCKED | RESUME | `{"act":"start","content":{"type":"auto"}}` |
| Idle, then charging | DOCKED | START | `{"act":"start","content":{"type":"auto"}}` |

An independent code review reproduced the ordering effect and the explicit
RESUME rewrite. When charging lands last and leaves DOCKED, aggregate activity
cannot distinguish the paused-job case from the idle case. With the reverse
order, PAUSED remains visible, as the table shows. This does not establish which
task report Lawna2 actually sent before the failed Start.

### Conditional patch outline, pending the raw task reports

Choose the implementation scope after the capture. These are design concerns
if task selection is implicated, not a commitment to a new task-state system.
The trace may justify a smaller change or identify a different cause.

1. **Retain mower task evidence separately from activity.** In
   `deebot_client/messages/json/clean_info.py`, the parser currently reduces
   clean/task reports to `StateEvent` at lines 32–64. Add mower-specific task
   evidence, with a small event/value definition under `deebot_client/events/`
   if appropriate, using only fields verified in the O500 capture. Retain task
   state and any required mode/identity independently of charging. Do not use
   area, duration or an old aggregate PAUSED event as a pending-job flag.
2. **Select the mower action from current task evidence.** In
   `deebot_client/commands/json/clean.py`, `CleanMower._execute` at lines 106–127
   delegates to the generic conversions at lines 37–48. Give the mower its own
   selection step: verified resumable task selects RESUME; verified no-task
   state selects START. Bypass the generic rewrite after selection, and
   preserve an explicitly requested mower RESUME. Keep vacuum selection intact.
   Whether an O500 idle report establishes no pending job must be checked from
   the capture rather than assumed from the current parser.
3. **Refresh and expire evidence deliberately.** For unknown/stale task context,
   await a specific `getCleanInfo` response before relying on it. The existing
   `event_bus.request_refresh` schedules work and is not a completion barrier.
   A failed or unrecognised reply must remain unknown, not become proof that
   there is no job. Define invalidation for restart/reconnect, completion,
   cancellation and task-changing commands; prevent an older query reply from
   replacing newer task evidence. Verify how reports identify a resumable
   return-to-charge job rather than assuming every paused history qualifies.
4. **Preserve genuine faults and command format.** Do not clear errors merely
   to make a start appear successful, force HA to mowing, or retry every rejected
   start as resume. Keep `clean`, `content.type` and header `0.0.50`; only change
   task/mode parameters where captured evidence requires it. An active area
   job must not silently be resumed as an auto job.
5. **Add regression coverage before implementation.** Extend
   `tests/commands/json/test_clean.py`, `tests/messages/json/test_mower_state.py`
   and, if a new event is used, event tests. Cover both report orders, fresh idle,
   explicit RESUME, paused-to-idle/completed/cancelled transitions, unknown task
   context after restart/reconnect, delayed or failed queries, genuine alerts,
   and unchanged vacuum behaviour. Then run the non-Docker suite and overlay
   import/hash checks before supplying a new SHA for dogfood.

These are proposed changes, not an implemented fix. A HA Core change is not
required to correct this client's action selection: its existing Start service
already delegates that choice to the client. Separately, surfacing client
command failures through the HA service would make HTTP 200 less misleading.

### Immediate evidence handoff and next dogfood

The attempted historical capture for **15:50–15:53 BST (14:50–14:53 UTC)**
returned no command evidence, as recorded above. Keep `3132dfb` installed and
do not interrupt the current mow. At the next test agreed with Mike:

1. Record the actual pre-test app state, any Continue option, HA state, battery
   and any fault. A docked HA state alone does not establish a pending job.
2. Set both `deebot_client` and `homeassistant.components.ecovacs` to `debug`
   using HA's [`logger.set_level` action](https://www.home-assistant.io/actions/logger.set_level/).
   Verify that fresh DEBUG messages actually appear before issuing any control.
   If they do not, resolve logging first. Retain the previous levels for restoration.
   Keep that proof line in the same saved Core stream used for the test, and
   do not restart HA between checking logging and issuing Start.
3. Save the complete bounded Core log window, starting before the pre-command
   task/status reports and continuing through the response and following state
   reports. A live filtered view is useful, but **do not save only lines matching
   Start/Resume**: API replies, faults and task reports may lack those words.
   Require fresh clean and charging reports before proceeding. If needed, use
   `homeassistant.update_entity` for `lawn_mower.lawna2`: the
   [HA 2026.9.2 entity implementation](https://github.com/home-assistant/core/blob/2026.9.2/homeassistant/components/ecovacs/entity.py)
   requests the subscribed events' refreshes. Wait for their actual replies;
   service completion is not a response barrier. Record HA activity before and
   after this refresh, which itself can change the cached action-selection state.
   Do not send an extra mowing command to obtain a snapshot.
4. From docked with app evidence of a pending job, issue one HA Start and record
   UTC/BST times. If it fails, retain the evidence and stop repeating commands.
   Any subsequent app Continue comparison must be supervised and separately
   timestamped, with physical/app observations alongside the logs.
   If the app shows no pending job, label it a fresh-job test rather than a
   reproduction of the reported docked/Continue case. Save the broader
   pause/resume/dock test until this first command trace has been assessed.
5. Restore the earlier logging levels after the bounded test and redact credentials
   and identifiers before sharing the trace.

The captured evidence should include:

- The exact `Mower clean request: action=..., cached_state=...` and
  `Mower clean result: sent_action=..., handling=...` lines.
- The failed HA `clean` request body and outer/inner API response, followed by
  `getCleanInfo`, `onCleanInfo`, `onScheduleTaskInfo`, `getChargeState`,
  `onChargeInfo`, `getError` and `onError` messages, including the most recent
  clean/task report **before** Start.
- The successful app Continue's complete command body and any adjacent commands
  **if captured**. HA logs should not be assumed to contain outbound app requests.
  If unavailable, say so; the HA response and task reports are still useful.

The relevant existing client log prefixes are `Calling api`,
`Success calling api` and `Try to handle message`. The two new `Mower clean`
lines do not include the full body or response. Preserve command fields while
redacting account/device identifiers: the existing sanitisation filter does
not scrub preformatted strings, including the API request summary.

On the synthetic docked case the current code logs a request with
`action=start, cached_state=DOCKED` and a result with `sent_action=start`.
The live handling result is unknown; do not substitute an expected SUCCESS or
ERROR for the actual line. `handling=SUCCESS` is still not evidence of mowing:
compare the inner response with following activity/error reports and physical
movement. If the actual failed request already sent `resume`, revisit the
action-selection hypothesis before changing code.

No new runtime files have changed in this documentation update, so **do not
re-overlay merely for this report**. Preserve the live run and collect existing
logs first. Once a reviewed, tested task-selection candidate exists, provide
its exact SHA and complete file manifest, including any new event module;
back up, apply the complete manifest, retain native `rs`/`.so`, restart, and
verify hashes against that SHA. Do not assume the current ten-file list will
cover a future new module. Keep package `18.5.1` and header `0.0.50` unchanged.

Then, in supervised daylight with adequate charge and genuine faults addressed:

1. From docked with a **verified pending job**, issue one HA Start; verify the
   selected resume body, accepted response and actual mowing.
2. After a verified completed/ended job, test HA Start from docked; verify a
   fresh start and actual mowing. Do not end the current run just to obtain logs.
3. Check pause, Start-to-resume and Dock, then check charging and activity again
   after several minutes. Include a restart with a pending job to test recovery
   of task evidence without relying on in-memory history.
4. Preserve the next morning's first command and ordered state/error reports.
   Keep PR 1847 draft until the exact proposed runtime tip passes the relevant
   live tests; record any documentation-only difference from that tested SHA.

### Independent review of the evidence and next step

At Mike's request, Grok 4.7 Extra High reviewed the local code, tests and this
documentation through Cursor CLI in read-only Ask mode. The first attempt
failed with a connection-stalled error; the retry completed successfully.
The reviewer confirmed the action-selection weakness, distinguished it from
the unproven cause of the live failure, and recommended keeping `3132dfb`
deployed until a bounded capture exists. Its documentation and capture
clarifications have been checked against the source and incorporated above.
This review did not add live telemetry or validate a new runtime fix.

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
state-recovery behaviour. The local repository investigation issued no live
mower commands; the live HA/app commands above were reported by Mike and Grok Bot.

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
  Docker/MQTT integration test was run. Live deployment and recovery are now
  reported above; a control cycle on the candidate remains pending.

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
