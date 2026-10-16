# GOAT O500 error recovery: 30 September 2026

Home Assistant could keep showing an old mower error even after the mower reported that the fault had cleared. The client tried to read the mower's activity once, but if that read failed during a connection problem it would ignore every later clear report. This update lets a later clear report try again, with at least 30 seconds between attempts while the same error activity remains cached. It still uses the mower's actual status and preserves genuine fault reports. Automated tests reproduce the original failure and verify recovery after a prolonged outage. The separate case where HA Start fails but app Continue works still needs a live command trace; this update does not claim to solve it. Upstream PR 1847 remains draft.

## Scope and evidence

- Source: `MikeWGitHub/client.py`, branch
  `cursor/goat-o500-clean-commands-e8d8`. Install the exact full commit SHA from
  the accompanying handoff, rather than a moving branch tip.
- Previous live runtime, as reported by Grok Bot through Mike:
  `3132dfbdecae632deb7d997bbad10b094f91d494`.
- Only one runtime file changes from that overlay:
  `deebot_client/commands/json/error.py`. Keep the complete ten-file overlay
  together when installing or reapplying it after a Core update.
- `clean` payloads, Start/Resume selection, header `0.0.50`, package metadata
  `deebot-client==18.5.1` and the native extension are unchanged.
- The local reproduction uses the real O500 commands, response handlers and
  event bus with a simulated transport failure. It is not live device telemetry
  and does not establish that this defect caused the 29 September incident.

## Behaviour

When `getError` or `onError` reports code zero (including an empty code list),
and a subscribed mower's cached activity is ERROR, the client requests
`getChargeState` and `getCleanInfo` immediately. If those reads fail or leave
activity at ERROR, another clear report at least 30 seconds later can request
them again. Reports inside the interval are suppressed. There is no background
timer or fixed attempt limit; retries require new incoming clear reports.

A new non-zero fault resets recovery eligibility and continues reporting ERROR.
A new ERROR episode after an activity change is eligible immediately. A report
received before anyone subscribes to activity does not consume a recovery
attempt. Vacuum behaviour is unchanged. No command dismisses a fault, and no
clear report invents a healthy activity state.

The interval applies to an unchanged ERROR episode, rather than all activity
reads. If competing clean/charging responses repeatedly move activity out of
ERROR and back, each new episode can request an immediate read. Capture any
such sequence in the supervised trace; it is a possible rate limitation, not
an established cause of the reported live failure.

DEBUG logging adds:

```text
Mower error-clear activity refresh: retry=False, cached_state=ERROR
Mower error-clear activity refresh: retry=True, cached_state=ERROR
```

The first line records a new recovery episode; the second records a later
attempt in the same episode. Neither line establishes successful recovery:
check the following query responses and activity events. Existing control logs
still record `Mower clean request: action=..., cached_state=...` and
`Mower clean result: sent_action=..., handling=...`.

## Automated verification

- Both new regression tests failed against the previous implementation:
  the second recovery attempt sent no queries, and a clear report before
  subscription prevented subsequent recovery.
- The real-command regression exercises four failed query pairs, suppresses
  rapid duplicate reports, then recovers to CLEANING from a successful query
  pair on the fifth eligible report. Further clear reports while healthy do
  not query activity.
- Existing tests cover active faults, new fault episodes, vacuum isolation,
  clean/charge responses and refresh requests during an in-flight poll.
- Full available non-Docker suite: 885 passed, 11 deselected, four snapshots
  passed. The existing generator-parametrisation deprecation warning remains.
- Mypy and Ruff checks pass. Docker/live MQTT and live HA/device tests are not
  claimed by these results.
- A cold import of the complete overlay onto the installed 18.5.1 package
  retained its native extension and verified O500 commands, message handlers
  and header `0.0.50`.
- Cursor CLI Grok 4.7 xHigh independently reviewed the source and found no
  blocking code issue, recommending a supervised docked deployment. Its
  read-only session could not execute shell tests. Its stale deployment-note
  finding was corrected; the commit must still be pinned before installation.

## Handoff to Grok Bot

Install only when the mower is safely docked or Mike has finished the current
run. Keep the authenticated HA work with Grok Bot.

1. Record the live SHA, actual HA Core/Python/package versions, imported file
   paths and hashes. Back up the current complete overlay for rollback.
2. Fetch the exact SHA supplied with this handoff from the fork. Apply these
   ten files together to the existing persistent overlay in HA Core's actual
   Python environment:

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

3. Preserve the native `rs`/`.so`, header `0.0.50` and installed distribution
   metadata. Do not install the development branch as a new pip release.
   Restart HA Core using the established overlay procedure.
4. Check imported source hashes against the pinned commit, including
   `commands/json/error.py` and `commands/json/charge_state.py`. Use the
   [read-only runtime check](goat-o500-dogfood.md#read-only-runtime-check)
   in HA Core's environment. Verify the O500 selects `CleanMower`, plain
   `getCleanInfo`, and the expected message handlers.
5. Enable `deebot_client` DEBUG logging **after** the restart. Verify that a
   read-only activity refresh emits query/response logs before operating the
   mower. A silent log is not evidence of a particular command or response.
6. Record deployment SHA, post-restart hashes, entity availability and the
   state/battery readings. Installation alone is not a successful control test.

Do not deliberately cause a blade fault or a connection outage on the mower.
If a genuine fault is cleared normally in the app, save the ordered error-clear,
recovery-query and activity messages. If the first query fails naturally,
check that a later clear report after 30 seconds requests another query pair.
No retry is expected solely because 30 seconds elapsed without a new report.

## Supervised control retest

When Mike is ready, capture a single HA Start from docked with an app-confirmed
unfinished job. Save the pre-control `getCleanInfo`/`getChargeState` responses,
requested action, cached activity, actual outgoing `clean` body, outer
`ret`/`errno`, inner code/message and following clean/charging/error events.
Record UTC/BST times and compare HA, app and physical response.

If it succeeds, check pause, HA Start as resume, then dock. Test a fresh job
separately from an unfinished job. HTTP 200 from HA alone is not a pass. If
HA Start fails again, save the trace before any app intervention; coordinate
recovery with Mike and record app Continue separately. Redact credentials and
device/account identifiers before sharing.

Ghost area/duration values do not prove that a current unfinished job exists.
Do not change Start/Resume selection or the protocol header based on those
figures. The future trace must establish which action was actually sent and
whether it was rejected or accepted before any further control fix.

Restore the previous complete overlay and restart Core if imports, availability
or ordinary controls regress. Recheck its hashes and record the failure.
Keep PR 1847 draft until the exact runtime revision has successful live tests.
