# Context-Efficiency Flush Defers Its Transfer Instead Of Poisoning The Store

Change ID: `20b38-bug context-efficiency-flush-permission-poisons-store`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-10
Wave: 20b3b upgrade-resilience

## Rationale

**Brief.** Goal: a transient failure during the context-efficiency `flush` (for example a Windows sharing violation or `PermissionError` while another process holds the lease file or the SQLite store) must not durably block `wf_upgrade` and `wf_reload_mcp`. Consumer: an operator whose telemetry store is briefly locked. Constraints: telemetry is advisory, must never lose accounting silently, and the existing gap semantics (a durable record when accounting is genuinely lost) stay. Windows, macOS, Linux and WSL2 share the same logic. Success: a retryable error during `flush` leaves the rows in place, writes no gap marker, reports a non-poisoned deferred result, and the transfer is retried on the next flush; the marker is written only for failures that genuinely lose accounting.

**Precondition.** Do not Prepare or Implement this change until wave `20b3a upgrade-failure-surfacing` is implemented, fully delivery-reviewed and PAUSED under the operator-approved sequence. Re-derive every cited line anchor against the post-`20b3a` tree; line numbers in this document are advisory and symbols are the anchors. Re-Prepare these amended plans against that source before activation; all framework code edits require the root Stage Gate and applicable framework-edit authorization. Closure is not required or authorized.

Field report: a `.wavefoundry/logs/context-efficiency.gap` marker blocked `wf_upgrade` twice (`context_efficiency_projection_failed`, "positive projection suppressed by durable accounting gap"). The second time it appeared after `wf_prepare_wave` reported `{"persistence": "failed", "error": "PermissionError: [Errno 13] Permission denied"}` and later calls showed `"persistence": "poisoned"`.

**Verified at HEAD.**

- All marker writes go through `_write_gap_sentinel` (`context_efficiency.py:1098`, first writer wins). `_commit_event` (1501) writes it only when the commit failed and the spool (`_spool_event`, 1769) also failed, after a 10 second busy retry (`_with_busy_retry`, `_is_busy_error` at 1036).
- `flush` (`FlushResult`-returning method at 2213) is a different operation. It performs only a general-to-wave TRANSFER: the lease check (`_ensure_lease`, 1989, which reaches `_try_lock_lease`, 534, a file open and lock) and then the local `_transfer_once` (2237) doing SQL updates of rows already stored. It has no new event to record, so there is nothing to spool: `_spool_event` serializes one new event (producer, focus, tool, event kind, metric, event id).
- `_ensure_lease` is called outside `_with_busy_retry` (about line 2236), which retries only accepted `sqlite3.OperationalError`. The real carrier open in `RuntimeFileLock.acquire` (`runtime_lock.py:453-467`) wraps `PermissionError` or another `OSError` in `RuntimeLockError` with the original cause; `_try_lock_lease` (`context_efficiency.py:534-548`) swallows that wrapper for both create modes. An actual `_open_lock_carrier` permission-failure probe confirmed `(None, False)` for both. Injecting a raw exception at `_try_lock_lease` alone does not prove this real seam.
- `_ensure_lease` (1989-1999) sets `self._lease_attempted = True` before `_try_lock_lease`. A swallowed carrier failure leaves no owned handle and false reclaimability, but later calls skip acquisition. A propagated demanded own-lease failure must reset the attempted flag before retrying.
- Any `Exception` in `flush` writes the marker immediately (about 2336-2337) and the result becomes `"poisoned"` (2338-2341), with no retry classification and no deferral. `touched.add(target)` precedes `conn.commit()`, and an exception after the commit (in `finally`, `conn.close()` or `_unlock_lease`) would today be classed as a failure although the rows moved.
- `FlushResult` (282) carries transfer outcome. Actual consumers are `wf_server/context_efficiency_handlers._flush_context_efficiency` and `context_efficiency.workflow_proxy_after_flush`, delegated by `wf_server/server_impl._record_lifecycle_boundary`. The former maps any unsuccessful flush to a failed projection today; the latter treats non-poisoned failures as fatal. `_poisoned_or_fatal_telemetry_failure` (the earlier cited `server_impl.py:18294` region) concerns new-event commit failure, not this transfer, and stays unchanged.
- `_commit_event` has no retryable classification either: it spools on ANY `Exception`. The only sqlite-specific test is `_is_busy_error` (1036). There is no shared constant to reuse.
- sqlite normally reports a locked database as `OperationalError`. Carrier permission failures are wrapped and currently swallowed, so the reported raw `PermissionError` cannot be attributed to that seam from this source trace. Other flush file/store operations remain candidates. The historical Windows exception and exact call site remain unisolated; actual wrapped carrier failures are a separately verified coverage gap, not a native incident reproduction.
- A zero-byte marker cannot be produced by our writer (it always emits a JSON record through a temp file and `os.link`, or an exclusive-create fallback, 1121-1146); it most likely came from an external touch or a crash in the no-hardlink fallback `_write_exclusive` (1089). `read_gap_reason` (1152) returns `{}` for a zero-byte file, so `_gap_diagnostic` (1167) says "(reason not recorded)".
- A clear command already exists (`wf clear-accounting-gap`) and its text is in the diagnostic (1179-1182); surfacing it in the top-level upgrade and reload errors belongs to change `20b34-enh upgrade-cli-resume-and-gap-clear-guidance`, not here.
- `docs/architecture/data-and-control-flow.md` item 9 (about line 157) states that a failed general-row transfer "durably writes `.wavefoundry/logs/context-efficiency.gap`". This change deliberately contradicts that for retryable errors, so the doc update is certain, not conditional.

## Requirements

1. The failure semantic for `flush` is "transfer deferred": when the transfer fails with a retryable condition (permission denied, sharing violation, busy or locked lease or store), it retries within the existing busy budget and then returns a non-poisoned, deferred result without writing the gap marker. The rows remain in the general bucket and the next `flush` retries the transfer. Nothing is spooled, because a transfer has no event to spool.
2. The retry location is decided: `_with_busy_retry` is widened with an optional parameter carrying the retryable classification, defaulting to the current `_is_busy_error` test, so `_commit_event` (which calls it with the default) is unchanged. `flush` passes the new classification and uses the widened retry around both `_ensure_lease` and `_transfer_once`, which closes the gap that the lease call sits outside the retry today. The retry loop wraps the lock acquisition rather than sitting inside it: the whole flush has one fixed absolute busy deadline, not a fresh budget per lease/SQL attempt; each attempt takes and releases `self._lock` (the lock `record_retrieval`, `focus` and `set_focus` also take), and the loop never sleeps while holding it, so a locked-lease storm cannot stall every telemetry caller for the busy budget.
3. A retryable own/live-lease failure resets `_lease_attempted` and reaches the flush retry classifier. Use a flush-only opt-in at `_ensure_lease`/`_try_lock_lease`: demanded own `create=True` acquisition recognizes and propagates `RuntimeLockBusy` and the specific retryable permission/sharing cause or errno of the existing `RuntimeLockError` wrapper, with bounded cause inspection. `_ensure_lease` is also called before new-event commits by `record_retrieval` and `record_workflow`; their default non-throwing acquisition and commit/spool path must remain unchanged. A prior unsuccessful default acquisition must not prevent a later demanded flush attempt. Preserve prior non-retryable runtime-lock handling and `create=False` best-effort orphan skipping. Do not change general `runtime_lock.py` behavior or poison a skipped orphan probe.
4. The deferred shape is `FlushResult(success=False, persistence="deferred", touched_waves=frozenset())`. `_flush_context_efficiency` and `workflow_proxy_after_flush` treat it as non-fatal pending transfer, preserving the general rows for retry. `server_impl._record_lifecycle_boundary` delegates this handling; alter that caller only if needed after the predecessor rebase. Do not change `_poisoned_or_fatal_telemetry_failure` or real new-event commit/spool failures. Public `wf_upgrade`/`wf_reload_mcp` report pending accounting without a gap block, never imply that deferred rows have been projected.
5. A failure that genuinely loses accounting keeps writing the marker and reports `"poisoned"`. A single transaction rules out partial loss for the transfer, so the poisoning cases are the non-retryable exceptions and any state where the transfer's atomicity cannot be shown. An exception raised AFTER `conn.commit()` (in `finally`, `conn.close()` or `_unlock_lease`) is never reported as deferred: the rows have moved, so the result reports success with `touched_waves` returned, and the cleanup error is logged. Because `touched.add(target)` precedes `conn.commit()` in `_transfer_once`, a raising `commit()` cannot be told apart from a post-commit cleanup error by `touched` alone, so `_transfer_once` exposes a committed signal (a return value or a nonlocal flag); `flush` reports success with `touched_waves` only when the signal is true, and clears `touched` on any pre-commit failure. Cleanup continues releasing remaining orphan leases even if connection close raises; a committed transfer is never retried.
6. The set of exceptions treated as retryable is a new named constant plus a classifier, introduced by this change and applied to `flush`: `PermissionError`, its specific retryable `RuntimeLockError` carrier wrapper, busy or locked conditions, and `OSError` whose `winerror` is 32 or 33, read as `getattr(exc, "winerror", None) in (32, 33)` so an `OSError` without the attribute is classified by its other properties and does not raise. It is not described as shared with `_commit_event`: two classification paths exist deliberately (`_commit_event` and `_is_busy_error` versus `flush`), recorded in the Decision Log with a follow-up pointer to unify them.
7. A zero-byte or unparseable marker is reported distinguishably: `read_gap_reason` returns a named value for each (for example `{"reason": "empty_marker"}` and `{"reason": "unreadable_marker"}`, defined as module constants), distinct from `{}`, from `None` and from a JSON marker's value, and `_gap_diagnostic` says the marker is empty or unreadable, how it can arise (external creation or interrupted write), still points at `wf clear-accounting-gap`, and does not claim a recorded reason.
8. A deferred transfer is neither lost nor double counted: after the retry succeeds, the general rows are claimed exactly once.
9. Update `docs/architecture/data-and-control-flow.md` item 9 and the public persistence/result contract in `docs/specs/mcp-tool-surface.md` to name `deferred`, pending rows and non-fatal lifecycle behavior; non-retryable transfer failures still poison. Update `docs/references/context-efficiency.md` if its flush contract needs the same correction. This behavioral spec requires docs-contract review.
10. Behavior is the same on Windows, macOS, Linux and WSL2. The Windows-specific exception types are named in the classification, and tests build them by instance (see AC-6) so they run on every platform; the logic does not depend on platform checks beyond the exception classification.

## Scope

**Problem statement:** `flush` poisons the store on any exception, including a transient Windows lock, and the resulting durable marker blocks upgrade and reload until the operator finds and runs the clear command.

**In scope:**

- The `flush` deferred-transfer semantic, the new retryable classification and the widened retry.
- The lease attempt reset and the lease open and lock site.
- The `FlushResult` deferred shape and the callers that must treat it as non-fatal.
- The zero-byte and unparseable marker diagnostic.
- The mandatory architecture and public persistence/result spec updates, with docs-contract review.
- Tests, including injected `PermissionError` and instance-built `OSError` with `winerror`.

**Out of scope:**

- Surfacing the clear command in `wf_upgrade` and `wf_reload_mcp` top-level errors (change `20b34`).
- An MCP tool for clearing the gap.
- Making upgrade ignore the marker (a policy decision for the operator: whether telemetry may block lifecycle operations at all).
- Locating the process that held the file in the field incident.
- Changing `_commit_event` spool behavior or adopting the new classification there.

## Acceptance Criteria

- [x] AC-1: Inject `PermissionError` separately at the actual `runtime_lock._open_lock_carrier` seam (retaining its real `RuntimeLockError` wrapping) and in the SQL transfer. In both cases no gap marker is written, the result is `FlushResult(success=False, persistence="deferred", touched_waves=frozenset())`, and before/after row snapshots show the general rows unchanged.
- [x] AC-2: After the injected error clears, the next `flush` completes the transfer and each row is claimed exactly once (no loss, no double count). A variant injects an exception after `conn.commit()` and asserts exactly-once, a success result that still returns `touched_waves`, and no marker. A second variant makes `conn.commit()` itself raise and asserts the deferred result with an empty `touched_waves`, no marker, and unchanged rows (the committed signal is false).
- [x] AC-3: A non-retryable exception in `flush` still writes the marker and reports `"poisoned"`.
- [x] AC-4: A retryable error that persists past the busy budget returns the deferred result and writes no marker; a fake clock/sleep proves the one fixed absolute budget spans lease and SQL retries without resetting, and the test never waits out the real budget. `_commit_event` behavior is unchanged (asserted with its default retry); actual `record_retrieval` and `record_workflow` controls with a wrapped carrier failure still reach their unchanged commit/spool path rather than raising before it.
- [x] AC-5: A zero-byte marker (seeded with `gap_path(root).write_bytes(b"")`) yields the named empty-marker value from `read_gap_reason`, distinct from `{}`, `None` and a JSON marker's value; an unparseable-JSON marker yields the named unreadable value; the diagnostic names the marker empty or unreadable and still includes the clear command text; a JSON marker keeps its current diagnostic.
- [x] AC-6: The retryable-exception constant and classifier are the single place the `flush` classification is defined, asserted by a test that changes the constant once and observes `flush` follow it. `OSError` values are built by instance, for example `e = PermissionError(13, "x"); e.winerror = 32` (the `OSError(..., winerror=...)` keyword raises `TypeError` on POSIX and `OSError(32, ...)` becomes `BrokenPipeError`), and are classified retryable on every platform; an `OSError` with no `winerror` attribute is handled without raising.
- [x] AC-7: The Progress Log records which exception and call site the Windows incident most plausibly involved, or states that it could not be reproduced off Windows.
- [x] AC-8: An own-lease open/lock failure followed by success resets `_lease_attempted`, retries and holds the lease. Own `create=True` busy/permission failures, including actual wrapped carrier permission and instance-built sharing violations, reach the fixed-budget retry; orphan `create=False` probes skip the same unavailable carriers without poisoning or forcing acquisition. A non-retryable runtime-lock control preserves its prior behavior.
- [x] AC-9: A deferred result produces a healthy pending projection in actual `_flush_context_efficiency` and `workflow_proxy_after_flush` consumers; `wf_upgrade`/`wf_reload_mcp` do not block. A control fixture proves genuinely failed new-event commit/spool accounting remains fatal/poisoned through the unchanged instrumentation helper.
- [x] AC-10: `docs/architecture/data-and-control-flow.md` item 9 cites the retryable constant and the deferred outcome and no longer states that a failed general-row transfer durably writes the marker unconditionally (a doc-truth assertion over the edited text).
- [x] AC-11: While a `flush` is retrying a retryable error, a concurrent `record_retrieval` call completes without waiting for the busy budget (the retry never sleeps while holding `self._lock`), verified with the sleep patched to block until the concurrent call returns.
- [x] AC-12: The public `docs/specs/mcp-tool-surface.md` result contract includes `deferred` and pending/non-fatal transfer semantics consistent with actual lifecycle responses; docs-contract review checks this behavior and required enum/result examples.

## Tasks

- [x] Reproduce actual wrapped carrier permission/sharing failures through `runtime_lock._open_lock_carrier` and a separate SQL transfer error; identify the real producer and consumer without claiming native Windows reproduction.
- [x] Introduce the retryable-exception constant and classifier; widen `_with_busy_retry` with the optional classification parameter (default unchanged).
- [x] Add flush-only demanded own-lease classification/reset, preserving default retrieval/workflow acquisition and non-retryable handling; test a prior failed default attempt followed by a demanded retry, plus unchanged `create=False` orphan probing.
- [x] Implement the deferred result and its callers' handling, and keep poisoning for non-retryable failures; handle post-commit exceptions per Requirement 5. Compute one retry deadline for the entire flush, acquire/release the telemetry lock per attempt, and ensure close failure does not prevent remaining orphan unlocks; never retry a committed transfer.
- [x] Make `read_gap_reason` return the named values for an empty and an unparseable marker and improve `_gap_diagnostic`.
- [x] Add tests beside `tests/test_context_efficiency.py:513` and `:1834-1841` (and the server tests at `tests/test_server_context_efficiency.py:281-285`), building `OSError` values by instance.
- [x] Update `docs/architecture/data-and-control-flow.md` item 9 and `docs/specs/mcp-tool-surface.md` persistence/result semantics; update `docs/references/context-efficiency.md` where needed. Obtain docs-contract review for AC-12.
- [x] Add a `CHANGELOG.md` bullet (root-level file).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| classification and call-site investigation | implementer | none | feeds AC-7; includes the lease site |
| widened retry, lease reset and deferred result | implementer | investigation | one module, plus the callers |
| diagnostic and tests | implementer | deferred result | includes the retry-once and post-commit tests |
| architecture doc and CHANGELOG | implementer | deferred result | item 9 update is mandatory |


## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency.py`, `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_context_efficiency.py`, `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `docs/architecture/data-and-control-flow.md`, `docs/specs/mcp-tool-surface.md`

`CHANGELOG.md` also changes (root-level file, so not a declared target). `server_impl.py` is also edited by the upgrade-failure-surfacing wave and by `20b37`; that wave is implemented, delivery-reviewed and paused first, and only a required delegating boundary hunk may change here; the instrumentation failure helper stays unchanged. The primary caller edits belong in `context_efficiency_handlers` and `workflow_proxy_after_flush`.

## Affected Architecture Docs

Update (mandatory): `docs/architecture/data-and-control-flow.md` item 9 (about line 157), which currently says a failed general-row transfer durably writes `.wavefoundry/logs/context-efficiency.gap`, contradicts the new behavior for retryable errors. It must name the retryable-exception constant, the deferred (non-poisoned) result, the rows left in the general bucket, and that non-retryable failures still poison (AC-10). No dedicated context-efficiency architecture doc exists under `docs/architecture/`; `docs/references/context-efficiency.md` is the signal contract and is updated only if it describes poisoning on flush. The public persistence/result contract in `docs/specs/mcp-tool-surface.md` also gains deferred/pending semantics. The change keeps the existing gap and event-spool contracts.

## AC Priority


| AC    | Priority     | Rationale |
| ----- | ------------ | --------- |
| AC-1  | required     | The core defect. |
| AC-2  | required     | The deferred transfer must not lose or double count. |
| AC-3  | required     | Do not weaken real poisoning. |
| AC-4  | required     | The budget and the no-marker guarantee together. |
| AC-5  | important    | Misleading diagnostic cost the operator time. |
| AC-6  | important    | One classification point, testable on every platform. |
| AC-7  | nice-to-have | Resolves an inference. |
| AC-8  | required     | Without the reset the lease site never retries. |
| AC-9  | required     | A deferred flush must not block upgrade or reload. |
| AC-10 | important    | The architecture doc currently states the opposite. |
| AC-11 | required     | The retry must not stall telemetry callers behind the lock. |
| AC-12 | required | Public behavioral spec must match the new result. |


## Progress Log

Qualification repair verified — 2026-10-10: the absent pending-metadata fallback is integrated with two real durable-projection/gap controls. The actual pre-edit accumulator also retained a real general row without inventing a pending claim and refused a real accounting gap in scratch. The unchanged memory suite passes 234 tests in scratch, and all eight boundary tests pass in the integrated 80-test run. Removing the getter fallback fails the named legacy-projection assertion. Real gap barriers, current deferred visibility, handler digests and the original memory test remain unchanged; AC-12 still awaits independent docs-contract review.

Readback, qualification repair — 2026-10-10: a restored pre-reload telemetry object may not expose the new optional pending-transfer metadata. Read it with an absent-value fallback, then always run the existing durable projection/gap checks. For example, a legacy object now projects its real durable wave rows instead of raising AttributeError; an actual accounting gap still refuses public upgrade. The unchanged 234-test memory suite and eight boundary controls pass in scratch; deleting the fallback fails a named control. Only the projection getter and two tests in the existing server-telemetry module change; no healthy forcing, speculative flush, digest refresh or weakened gap contract.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-10 | Planned from upgrade field feedback; write paths verified read-only; Windows exception type and zero-byte marker origin are inferred. | file:line citations in Rationale |
| 2026-10-10 | Readiness repair: `flush` is a transfer, not an event write, so the spool fallback is replaced by a deferred transfer; the shared-with-`_commit_event` claim is dropped. | red-team readiness review |
| 2026-10-10 | Confirming-round repair: lease-attempt reset, widened retry location, fixed `FlushResult` deferred shape, post-commit exception rule, instance-built `OSError` fixtures and the mandatory architecture doc update added. Product Intent: waived (bug fix, no product scope). | confirming readiness reviews of all six lanes |
| 2026-10-10 | Plan amended to target actual transfer consumers, preserve real event-commit failure, distinguish demanded own leases from orphan probes, and update the public deferred contract. Windows historical cause remains an inference. | `_flush_context_efficiency`, `workflow_proxy_after_flush`, `_record_lifecycle_boundary`, `_try_lock_lease`; public MCP spec |

| 2026-10-10 | Readback: previously a transient transfer permission/busy failure durably poisoned accounting and blocked lifecycle tools; now demanded own-lease plus SQL transfer share one absolute busy deadline, with the telemetry lock released before every sleep. Exhaustion reports deferred/pending with unchanged general rows; retry claims each row once. Explicit commit success distinguishes post-commit cleanup failure, which remains successful and releases remaining orphans. Real event commit/spool loss and non-retryable transfer failures remain fatal/poisoned. Empty/unreadable markers gain honest named diagnostics. | AC-1 through AC-12; context_efficiency, context_efficiency_handlers, only necessary delegating public reload response hunk in server.py, focused existing context/server tests and public/reference docs. The public reload owner drops successful projection data today; its response hunk is coordinator-authorized to report pending accounting. Native Windows incident origin remains unproved. |
| 2026-10-10 | Thought: make lease retry an explicit flush-only opt-in and preserve the default event write policy before adapting atomic transfer outcomes and consumers. | Live MCP producer/carrier/consumer reads; existing readiness consumed by coordinator. |
| 2026-10-10 | Observe: `FLUSH_RETRYABLE_EXCEPTIONS` / `_is_retryable_flush_error` classify only transfer retries. Actual own-lease carrier permission and instance-built WinError 32/33 pass through real `RuntimeLockError` wrapping; busy own leases defer too. Default retrieval and workflow carrier failures still reach durable event commits; unavailable orphan probes and non-retryable runtime-lock behavior retain their prior handling. | `DeferredTransferTests`: real carrier seam, producer/event/source rows, demanded retry/reset, workflow default control, constant mutation, and no-attribute OSError control. The historical Windows incident could not be reproduced off Windows; a carrier sharing/permission failure is plausible, but its precise file, holder and exception remain unproved. |
| 2026-10-10 | Observe: one absolute deadline encloses own-lease and SQL attempts, with the telemetry lock held only during each attempt. Retry exhaustion leaves durable general rows unchanged, returns deferred with empty touched waves and no spool/gap, and the next plain flush retries the remembered destination exactly once. A real non-retryable transfer still poisons. | Fixed fake-clock budget test; blocked sleep allows concurrent retrieval to commit; SQL permission row snapshots; existing non-transient poison control. |
| 2026-10-10 | Observe: only successful `conn.commit()` establishes the committed signal. Raising commit with an active transaction rolls back and defers; uncertain commit outcome or failed rollback poisons. Post-commit close/unlock failures remain successful with touched waves, log cleanup failure, release remaining orphan leases, and never repeat the committed transfer. | Commit/close proxy over real SQLite plus two actual orphan leases; unknown-atomicity controls. Empty/unreadable markers return named values, retain clear-command guidance, and never invent a recorded cause. |
| 2026-10-10 | Observe: actual `_flush_context_efficiency` / workflow proxy report healthy pending transfer, and registered public upgrade and fresh-process reload report `data.context_efficiency_projection.pending_general_transfer` without claiming general rows were projected. Real new-event commit plus spool failure remains poisoned, and an existing gap still blocks pending projection. | `DeferredTransferBoundaryTests`; public reload executed only in its isolated test process. Minimal response hunks in `server_impl.py` and `server.py`; only the changed registered `wf_upgrade` digest was refreshed, preserving captured_at and every other handler digest. |
| 2026-10-10 | Landing controls: nine deleted/loosened transfer guards each caused its named assertion to FAIL and were restored before final tests: flush classification, demanded lease, failed-attempt reset, committed signal, unknown-commit poison, deferred consumer, unchanged event retry default, release-lock-before-sleep, and release-all-orphans. | Temporary mutant runner output; no weakened assertions, census exclusions or test skips. Three additional download mutants (live Xet opt-out, worker-scope restoration, wall-clock timeout guard) also failed their named tests and were restored. Full qualification and independent docs-contract approval remain coordinator work; AC-12 is not claimed here. |
| 2026-10-10 | Verify: frozen source passed the isolated context-efficiency module (98 tests, 2.860s), server context-efficiency module (112 tests, 7.283s), and registry / tree-kill census / lifecycle structure modules (75 tests, 52.745s). Full MCP docs validation passed with no errors or warnings. | Canonical tool-venv Python, -B, no bytecode cache, HF/Transformers offline; zero skips in these runs. The server module emitted a database ResourceWarning while still passing; no native Windows or full-suite qualification claim. AC-1 through AC-11 and seven implementation tasks tracked through typed MCP; AC-12 and its combined docs-contract-review task remain pending for the coordinator's independent review lane. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-10 | Divergent pre-plan. Approach A: classify retryable errors in `flush` and defer the transfer without a marker. Approach B: stop upgrade and reload from blocking on a gap marker. Approach C: add an MCP tool to clear the gap. Approach D (rejected during readiness): give `flush` the spool fallback of `_commit_event`. Selected A. | A removes the cause of re-poisoning while keeping the marker meaningful; the rows are already stored and the transfer is atomic, so deferral loses nothing. D is unsatisfiable: a transfer has no event to spool. B discards a deliberate integrity guard and is a policy decision for the operator; C treats the symptom. | B and C remain possible follow-ups; B in particular needs an operator decision on whether telemetry may block lifecycle operations at all. |
| 2026-10-10 | Widen `_with_busy_retry` with an optional classification parameter (default unchanged) rather than adding a second retry loop, and keep two classification paths deliberately. | `_commit_event` also uses `_with_busy_retry`, so a default-preserving parameter keeps its behavior; `flush` needs to retry `_ensure_lease` and `_transfer_once`, which sit outside the current retry. The `_commit_event`/`_is_busy_error` path and the `flush` path therefore classify differently on purpose. Follow-up pointer: unify the two classifications once the field behavior is confirmed. | A second retry loop in `flush` (duplicates the budget logic); adopting the constant in `_commit_event` now (changes spool behavior, out of scope). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Treating too many errors as retryable hides real corruption. | Explicit exception list; AC-3 keeps non-retryable poisoning. |
| A permanently locked store defers forever and rows never reach the wave. | The deferred result is visible to callers; the existing projection reports pending state; noted for implementation to confirm. |
| The lease flag is never reset and the retry never reaches the lease site. | Requirement 3 and AC-8. |
| An exception after commit is reported as deferred and the touched waves are lost. | Requirement 5 and the AC-2 variant. |
| `winerror` is absent on POSIX and a test cannot construct the Windows error. | Instance-built fixtures and `getattr` classification (AC-6). |
| The Windows root cause is something other than `flush`. | AC-7 records the finding; the fix is still correct for the verified `flush` path. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
