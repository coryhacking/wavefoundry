# `wf_reload_mcp` cannot observe or report the tool-list notification it schedules, because a sync in-loop tool returns before the task runs

Change ID: `1vt2p-bug reload-tool-list-notification-fire-and-forget`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-20
Wave: 1vt2q mcp-reload-notification-delivery

## Rationale

`wf_reload_mcp` exists so an operator can pick up implementation changes without restarting the
host. When the tool set changes it schedules `notifications/tools/list_changed` and then reports
success it never observed.

**The original diagnosis in this plan was wrong and is recorded here so it is not re-derived.**
The first draft named a garbage-collection hazard: `loop.create_task(...)` discards its return
value, and CPython documents that the loop keeps only weak references to tasks. The readiness
council falsified that by execution on this stack (CPython 3.13.5, `mcp` 1.28.1, `anyio` 4.14.2),
with a positive control to prove the method could detect the hazard if present:

- **Control**, a task awaiting a future nothing else references: collected, `Task was destroyed
  but it is pending!`, alive-after-gc `False`.
- **Subject**, the real `BaseSession.send_notification` over a real memory object stream built as
  `mcp/server/stdio.py` builds it, scheduled by a sync function inside the loop exactly as FastMCP
  invokes a sync tool: alive after five `gc.collect()` before its first step, alive after five
  more while parked inside the send, and **delivered** in both the reader-parked and no-reader
  cases.

The chain is structural rather than lucky: `create_task` places a strong `Handle` holding
`task.__step` into `loop._ready` before returning, and every suspension point in this coroutine
parks on a future reachable from the live write stream. The task is never in an unreferenced
suspension. **There is no collection hazard to repair.**

What remains is real and is the actual defect. FastMCP calls a sync tool function directly inside
the running loop (`func_metadata.py`: `if fn_is_async: return await fn(...)` else `return
fn(...)`), so `wf_reload_mcp` **returns before the scheduled task takes its first step**. It
therefore cannot know whether the notification was sent, and it reports
`tool_list_changed_notification_sent: true` at schedule time regardless. A failure inside the send
becomes an unretrieved-task warning on a stderr nobody reads, while the response claims success.
The `completed` value the docstring advertises is unreachable in production, because it requires
`asyncio.get_running_loop()` to raise.

## Requirements

1. **Keep the scheduled send where awaiting is impossible; await where it is possible.** The
   readiness council's falsification changed what `loop.create_task(...)` means here. It is not a
   hazard to be removed: it is a mechanism **proven on the wire to deliver**, under a positive
   control, that merely cannot be reported on by the sync function that schedules it. So
   `perform_mcp_reload()` gains a keyword, `notify`:

   - `notify="schedule"` (the default, and what the `wf_upgrade` caller uses): unchanged
     behaviour, still `create_task`, reported as **`scheduled`** rather than `sent`. That value is
     now backed by executed evidence rather than a guess.
   - `notify="defer"`: send nothing and return the decision for a caller that can await it.
     The exact private handoff key is `tool_list_changed_notification_required: bool`. It is
     present only on the defer return, is popped by `wf_reload_mcp` before any public response,
     and must never escape through `wf_reload_mcp` or `wf_upgrade.data.mcp_reload`.

   **The return SHAPE is named, not left open.** `perform_mcp_reload()` keeps returning its
   existing payload MAPPING on both values, with the defer decision carried as an ordinary key
   inside it, never as a tuple and never as a callable. A tuple return would make the upgrade
   caller's `reload_resp.get("status")` raise, and that call site's bare `except Exception`
   converts the raise into a silent `mcp_reload_skipped` diagnostic: the wire would still carry
   the notification because `create_task` already fired, so AC-1 would pass and the mocked test
   would pass while `data.mcp_reload` and the whole escalation diagnostic vanished from the
   upgrade response. A callable would ride into a serialized envelope on any path that forgot
   to pop it.

   `server_impl.py` is declared as a review target because the upgrade caller lives there; it is
   **declared for review, not for edit**. Requirement 6's class-(c) conclusion depends on the
   behavioural bytes staying inside `server.py`, and weakens the moment that file is edited.

2. **`wf_reload_mcp` becomes an `async def` tool, calls with `notify="defer"`, and awaits the
   send**, reporting a genuine `completed` or a `failed` naming the exception type. FastMCP already
   dispatches async tool functions (`func_metadata.py`, `if fn_is_async: return await fn(...)`).
   It would be the first async tool in this surface, and the council verified the conversion is
   mechanically free: the argument model keeps `_wf_exact_args`, `_ensure_no_extra_args` still
   rejects unknown keys, `convert_result` is unchanged, the tool survives re-registration, and an
   awaited send over a zero-buffer stream does not deadlock.

   **This ordering is the correction.** The previous draft made the tool async and had the sync
   function merely return a decision, which deleted delivery from the `wf_upgrade` caller: proven
   on the wire, pristine `['notifications/tools/list_changed']` versus plan-design `[]`. That
   caller is sync (`server_impl.py` `wf_upgrade`), calls `perform_mcp_reload()` directly, and has
   no async wrapper to act on any decision. An upgrade is THE tool-set-changing event and is the
   surface the originating field report came from, so making it go quiet would have been a worse
   defect than the dishonest reporting this change exists to fix.

3. **Delete the `asyncio.run()` fallback, and NAME the outcome that replaces it.** With the
   branch gone, `asyncio.get_running_loop()` raises into the outer `except Exception` and the
   response emits `failed` with "could not reach the active session" when no send was even
   attempted and the session was perfectly reachable. That is a field asserting more than was
   observed, which is Requirement 4's prohibition in the opposite polarity, and it is what two
   of the six affected tests would silently receive. The no-loop condition gets its own
   explicit helper outcome value, **`no_running_loop`**, with diagnostic code
   `tool_list_changed_notification_no_running_loop`, so AC-5's branch enumeration has something
   to enumerate against. This value is defensive output from `perform_mcp_reload(notify="schedule")`;
   neither production caller is expected to reach it, and it is not a documented
   `wf_reload_mcp` result.
   The removal itself stands: it is not merely unreachable, and reaching it would drive
   an anyio stream bound to the server's loop from a brand-new loop, which is unsafe. Its removal
   is a deliverable, not a side effect.

4. **No response field may claim more than was observed, and both callers keep delivering.**
   The awaited path reports `completed` or `failed` with the exception type. The scheduled path
   reports `scheduled`, which is what it is. The schedule-time `tool_list_changed_notification_
   sent: true` goes, along with `queued`. Client ADOPTION stays unknowable server-side and the
   response must keep saying so. **The `wf_upgrade` response must keep carrying its escalation
   diagnostic** (fresh turn, reconnect, restart); losing it would remove the operator's only
   pointer at the ladder on the exact path where the tool set changed.

   **The state domain is closed and caller-specific.** Internally,
   `tool_list_changed_notification_dispatch` is one of `not_needed`, `deferred`,
   `scheduled`, `no_running_loop`, `completed`, or `failed`. The private `deferred`
   state and `tool_list_changed_notification_required` key exist only between
   `perform_mcp_reload(notify="defer")` and `wf_reload_mcp` and are removed before response
   serialization. The direct `wf_reload_mcp` response can expose only `not_needed`,
   `completed`, or `failed`; `wf_upgrade.data.mcp_reload` can expose only `not_needed`,
   `scheduled`, or `failed`. `completed` is impossible on the sync upgrade path, while
   `scheduled` is impossible on the async direct-tool path. `no_running_loop` is defensive
   private-helper output outside both public caller domains.

5. **Correct the documentation, and note that the spec entry is an ADDITION.**
   `docs/specs/mcp-tool-surface.md` contains zero occurrences of `tool_list_changed_notification`
   and has no `wf_reload_mcp` entry at all; only the `server.py` docstring describes these values.
   The first draft asserted the spec "currently describes the `completed` value", which is false.

6. **Disclose the transition as seed-160 class (c), a FULL HOST RESTART.** The BEHAVIOURAL
   bytes are in `server.py`, which with `venv_bootstrap.py` is the un-reloadable runner set
   captured at process launch and never reloaded in-process, so no `wf_reload_mcp` ever loads this
   fix. (The previous draft said "every byte this change touches is in `server.py`", which is
   false: **AC-7** edits the spec and **AC-1 through AC-6** edit tests. That correction is itself a
   correction: an earlier version of this parenthetical said AC-6 edits the spec, so the sentence
   whose only job is to record a falsified supporting claim carried one of its own. The class-(c)
   conclusion survives
   the correction; the sentence supporting it did not.) The honest instruction is therefore not
   "the next reload" but "restart every attached host"; reload signals this itself through
   `runner_stale`.

## Scope

**Problem statement:** `wf_reload_mcp` schedules `notifications/tools/list_changed` from a sync
function running inside the server's event loop, returns before the task can run, and reports
success it never observed.

**In scope:**

- Making the tool `async def` and awaiting the send; keeping `perform_mcp_reload()` sync for the
  `wf_upgrade` caller.
- Removing the `asyncio.run()` fallback.
- The reported fields, the `wf_reload_mcp` docstring, and a new `wf_reload_mcp` entry in
  `docs/specs/mcp-tool-surface.md`.
- Recording the answered `tools_reregistered` question (see Decision Log) so it is not
  re-investigated.

**Out of scope:**

- The garbage-collection hypothesis. Falsified by execution with a control; see Rationale. No
  reference-retention work is to be done, and an implementer who finds themselves adding one has
  drifted.
- Client adoption. No server change forces a host to re-fetch `tools/list`; the escalation ladder
  (reload, fresh turn, reconnect, restart) is correct and stays.
- The rest of the reload payload (`runner_stale`, `impl_matches_disk`, the identity fields). They
  verify correct and are untouched.

## Acceptance Criteria

- [x] AC-1: **The `wf_upgrade` caller still DELIVERS.** A reload driven through
  `perform_mcp_reload()` with the default `notify="schedule"`, from a sync function inside a
  running loop (the upgrade caller's production condition), puts
  `notifications/tools/list_changed` **on the wire** of a real session over real streams. Asserted
  on wire traffic, not on a return value and not against a mock: the existing
  `test_cleanup_apply_invokes_mcp_reload` mocks `perform_mcp_reload`, which is why the previous
  draft's regression would have shipped green. This AC is listed first because it is the one the
  previous design silently broke.
- [x] AC-1b: **The `wf_upgrade` RESPONSE keeps its escalation diagnostic, with
  `perform_mcp_reload` UNMOCKED.** After a reload that changes the tool set, the upgrade response
  still carries `data.mcp_reload` and the tool-list diagnostic naming the fresh-turn, reconnect and
  restart ladder. The only existing test of that merge patches `perform_mcp_reload` with a literal
  dict, so it passes for any real return shape, including one that makes the caller's
  `.get("status")` raise into a bare `except Exception` and silently drop the whole block. AC-1
  pins the wire; this pins the response. Both are needed, because the wire can carry the
  notification while the operator-facing diagnostic disappears.
- [x] AC-2: With `notify="defer"` and the tool async, the send is **awaited** and the response
  carries `completed`. The test asserts delivery happened BEFORE the tool returned, which is the
  property the sync form cannot have and which therefore fails on the unfixed code.
- [x] AC-3: An exception inside `send_tool_list_changed()` yields `failed` with the exception type
  in the response, and no field claims delivery. Satisfiable only because AC-2 made the outcome
  observable.
- [x] AC-4: The census names **exactly two** production call sites (`server.py` and
  `server_impl.py`'s upgrade path), each exercised under **its own production condition**: the
  upgrade caller inside a running loop, not the no-loop condition the previous draft tested it
  under. A census finding fewer than two fails; so does one that tests the second caller off-loop.
- [x] AC-5: No emittable combination of response fields asserts more than was observed, verified
  by enumerating every branch rather than sampling. The internal dispatch domain is exactly
  `not_needed | deferred | scheduled | no_running_loop | completed | failed`; the private
  `tool_list_changed_notification_required` key and `deferred` state never escape a public
  response. The direct tool exposes only `not_needed | completed | failed`; the upgrade response
  exposes only `not_needed | scheduled | failed`; `no_running_loop` is tested only as
  defensive private-helper output. `queued` and the
  schedule-time `sent: true` are gone; `scheduled` means a `create_task` whose delivery has a
  positive control on this stack.
- [x] AC-6: The `asyncio.run()` fallback is removed, **and the six existing tests that assert on
  the fields this change alters are rewritten or deleted**, named individually and split into the
  two groups they actually fall into, because only THREE of them fail. Measured against a patched
  copy the design-caused delta is exactly three failures
  (`test_reload_reports_queued_notification_on_active_event_loop`,
  `test_perform_mcp_reload_detects_description_change_and_sends_notification`,
  `test_reload_reports_completed_notification_when_send_finishes`). The other **three go GREEN
  while encoding the retired contract**, which is the more dangerous half:
  `..._reports_no_description_change_on_unchanged_reload` becomes VACUOUS, since its
  `assertFalse(result["data"].get(...))` passes because the key was deleted and would pass equally
  if the notification had fired; `..._notifies_when_new_tool_is_registered` accepts either the sent
  or the failed diagnostic code and so absorbs the new off-loop outcome silently; and
  `test_cleanup_apply_invokes_mcp_reload` keeps a mock payload production can no longer emit, which
  is the unfaithful-fixture shape this plan already names as what let the previous near-miss
  through. This criterion is the ONLY guard on those three. The previous draft
  claimed the branch "cannot be exercised"; that is false, since
  `test_reload_reports_completed_notification_when_send_finishes` is green today and reaches it.
  It is unreachable in PRODUCTION, not unreachable, and the test churn is a deliverable rather
  than a surprise.
- [x] AC-7: The docstring and a NEW `docs/specs/mcp-tool-surface.md` entry describe the values
  each caller can actually receive: `wf_reload_mcp` owns
  `not_needed | completed | failed`; `wf_upgrade.data.mcp_reload` owns
  `not_needed | scheduled | failed`. The spec also names `no_running_loop` as defensive
  private-helper output outside both public caller domains, and names
  `tool_list_changed_notification_required` and `deferred` as private helper-only handoff
  state that must not serialize, and
  **records the RETIRED values** (`queued`, the `tool_list_changed_notification_sent` field, and the
  `tool_list_changed_notification_queued` diagnostic code) so an operator reading an older
  transcript can map them. State honestly that `scheduled` buys little over the `queued` it
  replaces, since both mean handed to the loop and unobserved: the honesty gain on that path comes
  from deleting the `sent: true` field, not from the rename. No documented value may be unreachable
  in production.
- [x] AC-8: **End to end on the real seam.** After a full host restart, add a tool, reload, and
  observe what the host does. **Disposition declared in advance:** the repair owns the server
  SENDING the notification, which AC-1 and AC-2 pin; it does not own client adoption, which the
  Scope section excludes and which no server change can force. **"Verifiably sends" names evidence
  AC-2 cannot produce:** the `notifications/tools/list_changed` frame observed on the host's actual
  stdio transport or in the host's MCP log. NOT the `completed` field, which this change introduces
  and which would close the only criterion meant to escape self-reporting on the change's own
  self-report. **Absence of that frame FAILS this criterion.** With the frame present, a host that
  still does not refresh is a host fact and the next rung of the escalation ladder,
  **not** a failed repair. Recording this before the run is the point: without it, a non-adopting
  host reads as failure, which is the same false-report shape this change exists to remove.
- [x] AC-8b: **The one delivery path this repair CREATES is dispositioned, not left unnamed.**
  Awaiting binds delivery to the lifetime of the request task, which fire-and-forget did not:
  cancelling the `wf_reload_mcp` request mid-send drops the notification permanently, after the
  tool set has already been re-registered, so the host is never told. Measured under identical
  cancellation, awaited gives no notification while scheduled still delivers. Probability is low
  and the escalation ladder covers the operator. **Accepted gap:** cancellation aborts the awaited
  send and no retry is scheduled. Retrying could duplicate a frame when cancellation races a
  partially completed send, while the cancelled request has no response channel on which to report
  the later outcome. A polarity test must pin that awaited cancellation drops the send while the
  unchanged scheduled upgrade control still delivers. This accepted gap is recorded in Risks; no
  silent fallback or duplicate-capable retry may be added in this wave.
- [x] AC-9: The transition disclosure names seed-160 class (c) and a full host restart, and states
  the sentence that stops an operator reporting the fix as failed after a reload that could never
  have loaded it.

## Tasks

- [x] Enumerate both `perform_mcp_reload()` call sites and pin the upgrade caller's CURRENT wire
  behaviour first, so the regression the previous design introduced cannot recur unnoticed.
- [x] Add the `notify` keyword; keep `schedule` as the default so the upgrade path is unchanged by
  omission rather than by intent.
- [x] Convert `wf_reload_mcp` to `async def`, call with `notify="defer"`, await the send.
- [x] Remove the `asyncio.run()` fallback and rework the reported fields.
- [x] Rewrite or delete the six affected tests in `test_server_tools.py`, naming each.
- [x] Add the AC-8b cancellation polarity test: cancelled awaited direct-tool send is dropped
  without retry, while the scheduled upgrade-path control still delivers.
- [x] Update the docstring; add the `wf_reload_mcp` entry to `docs/specs/mcp-tool-surface.md`.
- [x] Record the class-(c) transition disclosure.
- [x] Restart the host, then run AC-8 with its pre-declared disposition.

## Agent Execution Graph


| Workstream | Role | Depends on | Notes |
| ---------- | ---- | ---------- | ----- |
| ws-1 call-site census | implementer | — | Enumerate both `perform_mcp_reload()` callers and pin the sync/async boundary before any edit. Gates every other workstream. |
| ws-2 async conversion | implementer | ws-1 | `async def` tool, awaited send, `asyncio.run()` fallback removed, reported fields reworked. |
| ws-3 tests | implementer | ws-2 | AC-1, AC-1b, AC-2 through AC-6. The before-return assertion in **AC-2** is the one that must fail on unfixed code; **AC-1 is a regression guard and must PASS on unfixed code**, since today's `create_task` already delivers. Building AC-1 to fail would invert its purpose. AC-6's six-test split is owned here. |
| ws-4 documentation | implementer | ws-2 | Docstring, the new spec entry, and the class-(c) transition disclosure. |
| ws-5 end-to-end | operator | ws-2, ws-4 | **AC-8** and AC-8b. Requires a full host restart first, so it cannot run in the session that lands the fix. |


## Serialization Points

Declared review targets:

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`

The test target is `test_server_tools.py`, not `test_server_startup_guards.py` as an earlier
draft declared: the latter is 108 lines of venv fail-fast guards with zero reload content, while
all seventeen `tool_list_changed_notification` references and all six affected tests live in
`test_server_tools.py`. A declared target that resolves to an unrelated file is the same defect as
declaring none, in a quieter form.

Declared here because the review policy reads declared targets from THIS section only. The first
draft declared them in prose under Affected Architecture Docs, which declares nothing: the policy
then recruited lanes through its undeclared-targets whole-document fallback, matching this
document's own prose rather than a target list.

**Serialization:** ws-2 edits `server.py` while `1vry5` edits `techdocs_audit_lib.py`. Disjoint
files, no shared surface, so the two waves may proceed concurrently. Only one wave may be OPEN at
a time regardless.

## Affected Architecture Docs

N/A. MCP reload IS described under `docs/architecture/` (`data-and-control-flow.md`,
`testing-architecture.md`, `domain-map.md`), so the first draft's claim that a keyword census
returned nothing was true only for the three terms it searched and is corrected here. What those
documents describe is the reload's PLACE in the flow, not the tool-list notification mechanism or
the reported fields, and this change alters neither a layer boundary, an ownership rule, nor a
documented flow. If the async conversion turns out to change how the reload sits in that flow,
this section and the declared targets must be amended before that edit.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The previous design deleted this delivery and no criterion caught it. It is graded first and required because a silent regression on the upgrade path is worse than the dishonest reporting this change repairs. |
| AC-1b | required | AC-1 pins the WIRE; this pins the RESPONSE. The wire can carry the notification while the operator-facing escalation diagnostic silently disappears, and the only existing test of that merge is mocked, so it passes for any real return shape. |
| AC-2 | required | Awaiting the send is the repair for the tool's half; the before-return assertion is what makes it falsifiable against the sync form. |
| AC-3 | required | A swallowed exception is how the defect stays invisible. Observability is half the fix. |
| AC-4 | required | The census is where the previous draft went wrong twice: it missed the second caller's importance, then tested it under a condition it never has in production. |
| AC-5 | required | The defect IS a false success report; any surviving over-claiming field reproduces it elsewhere. |
| AC-6 | required | Raised from important: three of the six tests go GREEN while asserting the retired contract, one of them vacuously, so this criterion is the ONLY guard on them. A test that passes for the wrong reason is worse than one that fails. |
| AC-7 | required | The docstring is the operator's contract for a diagnostic used during upgrades and currently advertises a value production cannot produce. |
| AC-8 | required | Every other criterion is closable with unit tests and doc edits. Without this an intermittent host-facing defect can be declared fixed without ever being demonstrated. Its disposition is declared in advance so a non-adopting host is not misread as a failed repair. |
| AC-8b | important | The cancellation path is a delivery loss this repair CREATES rather than inherits, and its probability is low with the escalation ladder covering the operator. It is graded important rather than required because an explicit accepted-gap row satisfies it; what is not acceptable is leaving it unnamed. |
| AC-9 | important | The disclosure changes no behaviour and the repair is correct without it; its absence costs one run of operator confusion, not a wrong result. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-19 | Re-cut after the readiness council FAILED the first draft. The original root cause (a garbage-collection hazard on the scheduled task) was **falsified by execution with a positive control**, and the two ACs built on it were mutually unsatisfiable. Re-cut around the council's recommended design: make the tool `async def` and await the send. Also split out of `1vry5` into this wave, because batching an asyncio notification repair with a TechDocs matcher change produced a wave record describing only one of them and lane selection driven by one change's declared paths and the other's fallback. | Council seats `red-team` and `docs-contract-reviewer`, both FAIL; control task collected while the real send-path task survived ten `gc.collect()` calls and delivered in both reader-parked and no-reader cases. |
| 2026-08-20 | Readiness cycle 1 repaired three packet defects before code: added the required architecture lane; closed and partitioned the exact internal/public notification state domain; and chose the explicit accepted-gap cancellation disposition with a polarity-test task. | `PREP-NOTIFICATION-STATE-DOMAIN-001`, `PREP-ARCHITECTURE-LANE-002`, `PREP-CANCELLATION-DISPOSITION-003`; docs lint clean before repair. |
| 2026-08-20 | Implementation opened on receipt `review-policy-725ac3e256402e4c1581`. Ordered sequence: (1) pin the exact two-caller census and unchanged `server_impl.py` boundary; (2) split helper scheduling from the direct tool's awaited send; (3) migrate the six legacy assertions and add upgrade-wire, exhaustive-state, failure, private-escape, and cancellation-polarity controls; (4) align the public spec and class-(c) restart disclosure; (5) run focused, full-suite, docs, and restarted-host verification. | Readiness council and all four required lanes approved; `wf_implement_wave(mode="create")` succeeded; `framework_edit_allowed` opened. Gapfill: shell region reads were used only for exact bulk test inventory and diff-aware mechanical editing in the already-located `WaveMcpReloadTests` block; semantic navigation and lifecycle context came from the prepared packet and MCP workflow. |
| 2026-08-20 | AC-8 passed on a freshly started stdio server process using a temporary framework copy. The live client initialized, the temporary `server_impl.py` gained one probe tool after startup, `wf_reload_mcp` reloaded it, and the client observed the protocol notification before refetching the new tool successfully. | Actual stdio result: `ToolListChangedNotification`; direct dispatch `completed`; `wf_1vt2q_notification_probe` absent before reload and present after `tools/list`; process exit 0. The temporary copy emitted the expected roster-drift warning for the deliberately injected probe and was automatically removed. |
| 2026-08-20 | Implementation validation completed. The first full-suite pass exposed one structural test oracle that counted only synchronous decorated tools; broadening that AST census to include `AsyncFunctionDef` preserved its two-way registration check for the first async tool. | Focused reload/upgrade matrix: 21 tests OK. Restarted-host AC-8 probe: PASS. Final framework suite: 7,459 tests across 64 files, all OK. `git diff --check`: clean. |
| 2026-08-20 | Delivery cycle 2 repaired two carrier defects: the public spec now distinguishes the retired `tool_list_changed_notification_sent` boolean field from the retained same-named success diagnostic, and canonical seed 160 now publishes the same direct/upgrade state domains and private-state boundary as the implementation. | `ARCH-DEL-RETIRED-VOCAB-SCOPE-001` and `DOCS-DEL-SEED160-RELOAD-CONTRACT-002` terminal after fresh architecture/docs-contract reverification; 147 focused reload, packaging, and shipped-reference tests OK; docs lint clean; wording mutants killed. |


## Decision Log


| Decision | Alternatives considered | Rationale |
| -------- | ----------------------- | --------- |
| Make `wf_reload_mcp` `async def` and await the send. | (a) Retain a reference to the scheduled task and add a done-callback. (b) Leave the dispatch alone and only soften the reported fields. | (a) repairs a hazard that measurement says does not exist here, and still cannot put the outcome in the response, because a sync tool returns before the task steps. (b) leaves an operator-facing diagnostic that can only ever say "unconfirmed". Awaiting removes the task **on the reload tool's path only** and is the only option under which AC-2 and AC-3 are simultaneously satisfiable. It does NOT remove `create_task` generally: `notify="schedule"` keeps it for the `wf_upgrade` caller by construction, which is the whole point of AC-1. An earlier version of this row said "removes the task entirely", which describes the falsified design and is the exact sentence an implementer could act on to reintroduce the regression. |
| Keep `perform_mcp_reload()` synchronous. | Convert it too. | It has a second caller on the `wf_upgrade` path which is itself a sync in-loop tool. Converting it would widen this change into the upgrade runner for no benefit. |
| Record the `tools_reregistered` 88-versus-90 question as ANSWERED rather than carrying it into implementation. | Carry it as an investigation task. | The council derived it: `tools_reregistered` counts `post_reload & (pre_reload - _RELOAD_SURVIVOR_TOOLS)`, so 88 = a 90-tool post-reload roster, minus the one survivor (`wf_reload_mcp`), minus the one NEWLY ADDED tool, which by definition cannot appear in the pre-reload set. Both gaps are by construction and the count can never be zero on a reload that adds a tool. Nothing is unexplained; at most the docstring wording deserves a note. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| **The stated root cause was already wrong once.** The first draft named a garbage-collection hazard that execution disproved, and two required ACs were built on it. | The falsification and its positive control are recorded in the Rationale and the hypothesis is named OUT OF SCOPE, so it is neither re-derived nor quietly reintroduced. An implementer adding reference-retention code has drifted from this plan. |
| This would be the first `async def` tool in the surface, so FastMCP's sync-tool argument normalization and `_ensure_no_extra_args` path may not apply unchanged. | **Requirement 2** makes that examination explicit rather than assumed, and ws-1 gates every other workstream on the call-site census. If the async path proves incompatible, the finding lands before any dispatch edit. |
| Repairing a reload diagnostic could break the `wf_upgrade` reload path, which is a strictly more important surface. | **AC-4** requires both call sites named in the test, each under its own production condition, and fails a census that finds fewer than two. `perform_mcp_reload()` deliberately stays synchronous. |
| The repair cannot demonstrate itself on the run that installs it: `server.py` is un-reloadable runner code, so no `wf_reload_mcp` ever loads it. | Requirement 6 and **AC-9** make the class-(c) full-restart disclosure a deliverable. **AC-8** is explicitly ordered after a restart. Without this an operator reloads, sees the old behaviour, and reports the fix as failed, which is the same false-report failure this change exists to remove. |
| **AC-8** is the only criterion that touches the real seam and it needs an operator and a restart, so it is the one most likely to be skipped. | It is graded required and assigned to an operator workstream (ws-5) with an explicit dependency, rather than left as a task, and its evidence is now a transport-observed frame rather than the change's own response field. Every other AC is closable without it, which is precisely why it cannot be optional. |
| Cancelling the async `wf_reload_mcp` request while its awaited send is blocked drops that notification. | **Accepted gap for this wave.** Do not retry: cancellation may race a partially transmitted frame, so a fallback send could duplicate it, and the cancelled request cannot report the later outcome. The existing reconnect/restart ladder bounds operator impact. AC-8b's polarity test pins the accepted behavior against the scheduled upgrade-path control. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
