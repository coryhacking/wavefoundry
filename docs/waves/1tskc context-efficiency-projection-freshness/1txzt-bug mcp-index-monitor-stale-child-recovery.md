# MCP Index Monitor Stale-Child Recovery

Change ID: `1txzt-bug mcp-index-monitor-stale-child-recovery`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-29
Wave: `1tskc context-efficiency-projection-freshness`

## Rationale

The MCP server owns an in-process index-staleness monitor intended to recover missed post-edit hooks
and edits made by hosts without a verified turn-end hook. In a live Wavefoundry session the project
index remained stale by 88 paths for more than a day even though the monitor was enabled, its stale
predicate returned true, the repository had exceeded the five-minute quiet period, and no build lock
was held.

The monitor was blocked by its own completed child. `background-refresh.json` recorded PID 5892,
which was a POSIX `<defunct>` process. `_background_refresh_active` treated `os.kill(pid, 0)` success
as proof of a live refresh, so `_maybe_refresh_if_stale` returned before reaching the launcher that
would reap the child. The same state-file check can misclassify a recycled PID belonging to an
unrelated process. The indexer's canonical build-lock path already handles both zombie and recycled
PID cases; the MCP refresh path does not.

## Requirements

1. A finished MCP-launched index child must never prevent a later quiet-period refresh. Reconcile or
   reap completed children before any state-file PID can classify a refresh as active.
2. Background-refresh liveness must reject POSIX zombies and recycled PIDs that do not belong to an
   active Wavefoundry index build. Reuse the existing canonical index-process/lock classification
   where practical rather than maintaining another weaker PID interpretation.
3. Preserve single-flight behavior: an actually live index build or authoritative held build lock
   prevents a duplicate spawn across MCP threads and processes.
4. Preserve the existing quiet-period contract: the monitor polls cheaply, defers to a fresh
   `reindex-pending` marker and a recently completed build, and starts one detached project refresh
   after the configured quiet period when inputs remain stale.
5. Preserve fail-safe, platform-first behavior on native Windows, WSL2, macOS, and Linux. POSIX child
   reaping must remain non-blocking; Windows must not acquire a POSIX zombie dependency or create a
   console window.
6. Make the monitor diagnosable through the existing index health/status surface. Report whether it
   is configured and alive plus its last check time, stale decision, trigger outcome, and bounded
   reason without turning polling into telemetry or persistent tracked-file churn.
7. MCP reload and handler shutdown must not strand child state that can suppress refresh after a new
   handler starts. Recovery must derive safely from durable process/build state when the in-memory
   child registry is empty.
8. Keep explicit `index_build`, setup/upgrade indexing, post-edit/turn-end hook indexing, graph build,
   and index freshness calculations behaviorally unchanged.

## Scope

**Problem statement:** The MCP quiet-period index monitor can permanently classify a completed child
or recycled PID as an active refresh, leaving a stale semantic index without an observable reason.

**In scope:**

- Reordering or consolidating refresh-active reconciliation so completed children cannot short-circuit
  their own reaper.
- Zombie- and recycled-PID-safe background-refresh state classification.
- Handler reload/shutdown recovery for persisted background-refresh state.
- Existing index health/status observability for monitor configuration, liveness, last decision, and
  last trigger.
- Regression coverage for live-build single-flight, completed children, PID reuse, reload, and all
  first-class operating-system families.

**Out of scope:**

- Changing index contents, chunking, embedding, ranking, graph extraction, or freshness definitions.
- Changing the five-minute default quiet period or the post-edit hook debounce policy.
- Adding a user-home daemon, filesystem watcher service, or platform-specific untracked state.
- Combining Context Efficiency projection state with index-generation or index-build state.
- Automatically committing index-derived or projected files.

## Acceptance Criteria

- [x] AC-1: Given stale inputs, an expired quiet period, and a completed MCP child that remains as a
  POSIX zombie, one monitor poll reaps/reconciles that child and starts exactly one refresh.
- [x] AC-2: A persisted background-refresh record whose PID now belongs to an unrelated process is
  not classified as a live index build and cannot suppress the next eligible refresh.
- [x] AC-3: A genuinely live index builder or held authoritative build lock prevents every competing
  MCP process/thread from launching a duplicate build.
- [x] AC-4: A server-side reload with stale background-refresh state and an empty in-memory child
  registry still converges to a refresh when the repository is stale and quiet.
- [x] AC-5: Native Windows follows the detached/windowless process path without POSIX process probes;
  WSL2, macOS, and Linux use non-blocking zombie-safe reconciliation.
- [x] AC-6: Index health/status reports monitor enabled/alive state and a bounded last-check record
  containing the stale result, trigger result, and reason; unavailable state is explicit rather than
  inferred as healthy.
- [x] AC-7: Existing fresh-marker, recent-build, publication-block, absent-index, corrupt-state, and
  active-build paths remain fail-safe and do not spawn.
- [x] AC-8: An integration regression exercises the real ordering between stale detection, child
  reconciliation, active-state evaluation, and refresh launch; it fails against the pre-change
  control flow and does not mock `_background_refresh_active` into the expected result.
- [x] AC-9: Explicit builds, setup/upgrade builds, hooks, graph extraction, and search/index-health
  envelopes remain behaviorally compatible apart from the additive monitor-status fields.

## Tasks

- [x] Establish one authoritative background-refresh liveness/reconciliation path using the existing
  indexer process-state and build-lock primitives where safe.
- [x] Remove the monitor's ordering path that returns on stale child state before reaping or otherwise
  make reconciliation precede every active-state decision.
- [x] Record bounded in-memory monitor observations without metering, tracked-file writes, or corpus
  scans beyond the existing stale predicate.
- [x] Add monitor status to the existing index health/status response and document each field.
- [x] Add non-vacuous regressions for zombie child recovery, unrelated recycled PID, reload with an
  empty registry, real live-build exclusion, Windows behavior, and state-probe failure.
- [x] Reconcile architecture/reference documentation that describes MCP-owned index freshness and
  background behavior.
- [x] Run targeted tests, the full framework suite, docs lint, and a live post-reload quiet-period
  probe before delivery review.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Liveness and reconciliation contract | implementer | — | Unify the ordering and process-state boundary first. |
| Monitor observability | implementer | Liveness and reconciliation contract | Keep state bounded and accounting-neutral. |
| Regression and live verification | qa-reviewer | Both implementation workstreams | Prove pre-fix failure and post-fix convergence. |
| Contract reconciliation | docs-contract-reviewer | Monitor observability | Update only docs that claim freshness behavior. |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` — child lifecycle, monitor loop, and status fields
  share one control-flow boundary.
- `.wavefoundry/framework/scripts/indexer.py` and process-state helpers — reuse must not introduce an
  import cycle or split the build-lock authority.
- Index monitor and Context Efficiency projection scheduler work in wave 1tskc both touch
  `ImplHandler`; reconcile handler startup, reload, shutdown, and additive status state together.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — correct the MCP monitor's child-lifecycle and
  convergence flow.
- `docs/specs/mcp-tool-surface.md` — document additive index monitor status and recovery semantics.
- `docs/contributing/build-and-verification.md` — distinguish hook-triggered refresh from the MCP
  quiet-period safety net and its observable recovery state.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Reproduces and closes the observed completed-child deadlock. |
| AC-2 | required | PID reuse is the durable-state variant of the same suppression defect. |
| AC-3 | required | Single-flight preservation prevents corruption and duplicate native work. |
| AC-4 | required | MCP reload currently loses the in-memory child registry and must still recover. |
| AC-5 | required | Every supported operating-system family must retain safe child semantics. |
| AC-6 | required | Operator-visible monitor state is required to diagnose future convergence failures. |
| AC-7 | required | Existing quiet and publication guards must remain fail-safe. |
| AC-8 | required | The prior tests separated reaping and monitor flow; an integrated oracle is essential. |
| AC-9 | required | Existing index entry points and envelopes must remain compatible. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-29 | Planned from a live MCP failure analysis and admitted to wave 1tskc. | Index stale by 88 paths; PID 5892 verified `<defunct>`; stale=true and active=true reproduced through the shipped predicates. |
| 2026-07-29 | Readiness review assigned every AC as required. | Each AC protects either the reproduced defect, build single-flight authority, supported platforms, or release compatibility. |
| 2026-07-29 | Repaired stale-child ordering and durable PID classification, added the authoritative whole-index lock probe, and exposed bounded process-local monitor status. | Zombie, recycled PID, reload-empty-registry, classifier-failure, live-child, held-lock, Windows no-waitpid, observer, lifecycle, and public `index_health` regressions pass. |
| 2026-07-29 | Live post-reload probe crossed the formerly blocked path and launched PID 11565; review then caught that the shared launcher relied on `indexer.py`'s docs-only default. The launcher now passes `--content all` explicitly. | Live lock transitioned held→clean finish; deterministic all-layer update reported 1,623 files, 21,499 doc chunks, and 6,388 code chunks. Preferred-interpreter regression pins the final `--content all` arguments. |
| 2026-07-29 | Canonical suite executed after implementation. | 6,492 tests across 61 files: the changed-area monitor fixture was corrected and passes; one unrelated, independently reproducible stale actor-policy expectation remains in `RepairIndependenceBoundaryTests`. All other 6,491 tests passed; docs lint clean. |
| 2026-07-29 | Independent review found that executable-class validation alone still accepted a recycled PID running Wavefoundry's indexer for another repository. The durable PID check now also binds the readable command line's exact `--root` to the state-file owner. | Different-root indexer is rejected, same-root control remains active, and quoted/case-varied native-Windows roots compare correctly; the full background-active class passes 16/16. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-29 | Keep this as a separate bug change in 1tskc instead of widening the Context Efficiency change. | Both changes touch handler-owned background convergence, but their authorities, triggers, and acceptance evidence are distinct. | A separate later wave delays a confirmed shipping defect; folding it into 1tsjh obscures the CE accounting boundary. |
| 2026-07-29 | Add monitor status to existing index health/status instead of creating a new public tool. | Operators already inspect these surfaces when an index appears stale, and additive state avoids tool-surface expansion. | Logs or a new diagnostic tool would make routine recovery harder to discover. |
| 2026-07-29 | Launch automatic project refresh with explicit `--content all`. | `indexer.py` defaults to docs-only; a bare launch can report activity while code embeddings remain stale, which matches the operator's broader field symptom. | Preserve the bare command was rejected because workflow include-prefix parsing does not change the CLI content default. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A liveness repair permits duplicate index builds. | Preserve the authoritative OS/build-lock single-flight check and test a genuinely live builder across competing callers. |
| Reusing indexer helpers creates an import cycle or Windows subprocess regression. | Keep the authority in a dependency-safe module or use a narrow shared helper; exercise native-Windows branches with the windowless runner. |
| Monitor observations become another durable state file or telemetry feedback loop. | Keep bounded status in handler memory and expose it read-only; no tracked writes or Context Efficiency events. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
