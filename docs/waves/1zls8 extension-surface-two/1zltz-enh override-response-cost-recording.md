# Cost Recording for What Overrides of Self-Recording Tools Add

Change ID: `1zltz-enh override-response-cost-recording`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-02
Wave: 1zls8 extension-surface-two

## Rationale

An override (`EXTENSION_OVERRIDES`) is served under the core name and gets the core name's wrappers, cost recording included. The cost wrapper `_wrap_first_party_tool_costs` skips every name in `_COST_EXEMPT_TOOLS` unless it is a replacement (`extractor_free`). Those exempt names (`wf_create_wave`, `wf_prepare_wave`, `wf_implement_wave`, `wf_review_wave`, `wf_close_wave`, `wf_reload_mcp`, and the retrieval tools `code_*` and `docs_search`) record their own cost inside the core callable: the lifecycle tools through `_lifecycle_context_result`, which measures the response through `_record_workflow_context`, and the retrieval tools through `_record_retrieval_context`. An override that delegates through `mcp.core_handler(name)` receives that core callable, so the core records the core response. Anything the override adds after `core_handler` returns is recorded nowhere: the outer wrapper skips the exempt name and the core measurement has already happened. The spec's sentence that delegating "records cost once, through the override's own name-keyed wrappers" is therefore true for non-exempt names only.

The downstream distribution (Waveforge) asked, at low priority, for a post-response hook inside the core recording sequence, and noted that a check that must run under the same hold as the core call has to nest the lock around `core_handler`. On the second point the code shows otherwise: overrides are installed into the served table before the `MIDDLEWARE` chain runs, and the chain is keyed on the served name, so an override of a lifecycle-locked name (create, prepare, implement and close are in `_LIFECYCLE_MUTATION_LOCK_TOOLS`) runs its whole body, before and after `core_handler`, inside the lifecycle lock and behind the upgrade publication guard. This plan pins that with a test and fixes only the recording gap, with the smallest mechanism that does not double count.

## Requirements

1. **Measured core handler.** `core_handler(name)` on the staging surface returns a thin wrapper around the core callable instead of the bare callable. The wrapper calls the core callable with the same arguments, returns its result unchanged (same object) and propagates any exception unchanged. When a measurement scope is active (Requirement 2) and `name` is in `_COST_EXEMPT_TOOLS` (a core that records its own cost), it adds the core result's response size to that scope; the core handler of a non-exempt name never adds to a scope, because that core recorded nothing and its response is part of what the override returns. The size is `context_efficiency.estimate_tokens_utf8(json.dumps(result, sort_keys=True, default=str))` for a dict or list result, else 0, the same estimator the cost wrapper uses. With no active scope it only calls through. The wrapper captures the `ContextVar` object when it is built, not by a module-global lookup at call time: an in-place `wf_reload_mcp` re-executes `server_impl` in the same module dict and rebinds the global, and the wrapper and the delta recorder of one install must share one variable. `core_handler` must be called on the thread or task that runs the override: a `ContextVar` is not inherited by a thread-pool worker, so a core call made in an executor thread is not subtracted and its size counts as the override's addition. The spec states this.
2. **Delta recording for overrides of exempt names.** A new module-level set `_EXTENSION_OVERRIDE_DELTAS: set[str]` holds the installed override targets that are in `_COST_EXEMPT_TOOLS`. `_install_extension_tools` clears it at install start beside `_EXTENSION_REPLACED_CORE.clear()` and fills it after a valid install, and the `except BaseException` that strips the surface to runner tools in `register_mcp_surface` clears it beside the other extension sets. The cost pass gains a main-pass keyword `override_deltas: Collection[str]` (beside `extractor_free` and `artifact_extractors`), set by `_cost_pass_kwargs` from that set and absent for the stock declaration. For those names only, the cost wrapper wraps the served callable with a delta recorder: it opens a measurement scope (a `contextvars.ContextVar` holding a per-call accumulator, reset in a `finally`), calls the override, and then records at most one `record_tool_cost` event for the name with `derived_artifact_tokens=0` and no extractors:
   - when the scope saw at least one core call: only when `delta = final_tokens - core_tokens` is greater than 0, one event with `request_tokens=0` (the core recorded the request) and `response_tokens = delta`, where `final_tokens` is the override's final response measured by the same estimator and `core_tokens` is the sum the scope accumulated; a delta of zero or less records nothing;
   - when the scope saw no core call (the override answered itself): one event with the request and the full response, exactly as the wrapper records a non-exempt tool, because nothing else recorded either; this is the single event for the call.
   The event id is a fresh `uuid4`, as for debit-only events today.
   **Call count.** The context-efficiency stage totals count calls as `COUNT(*)` over `telemetry_event` for the wave and stage (`context_efficiency.py`, the stage query that also sums request and response tokens), so a delegating override that adds fields counts as two events in the **Tool calls** column (the core's event and the delta event); one that adds nothing counts as the core's event only, and one that never delegates counts once. Marking delta events and excluding them from the count was considered and not chosen (Decision Log). The spec states this.
3. **Unchanged paths.** Non-exempt names, replacements (`extractor_free`), core names without an override, aliases (copies of the wrapped canonical tool, so they inherit the delta recorder of an overridden exempt name) and the core-behaviour chain are unchanged. `_COST_EXEMPT_TOOLS` is not edited, and a core call's own recording inside the core callable is unchanged.
4. **Observational only.** The delta recorder follows the existing wrapper rules: it stays silent while the publication checkpoint reports a reason, any recording failure is swallowed, and the override's result is returned unchanged in every case.
5. **Nesting.** A core handler called inside another override's scope adds only to the innermost active scope; a scope is per call and per thread or task, because it is a `ContextVar` reset on exit.
6. **Lock and guard coverage pinned.** A test pins that an override of a lifecycle-locked exempt name (for example `wf_close_wave` or `wf_prepare_wave`) runs code after `core_handler` returns while the lifecycle lock is still held (the process-hold registry from wave `1zimc` shows the hold), and that the publication guard refuses the override, before its body runs, while the upgrade checkpoint is active.
7. **Docs.** `docs/specs/mcp-tool-surface.md` **Overrides**: the `core_handler` sentence states that for a name that records its own cost the core records the core response and the server records only what the override adds after the core call (or the whole call when the override never delegates), and that an override of a lifecycle-locked name already runs entirely under the lock and the publication guard, so it never takes the lock itself; the spec also states the **Tool calls** count rule of Requirement 2 and the calling-thread rule of Requirement 1. The extension-modules row of `docs/architecture/threat-model.md`, which says an override "receives the unwrapped core handler", is updated: the override receives a thin measuring wrapper around the unwrapped core handler, which returns the core result unchanged and carries no lock, guard or cost wrapper, so the override's own name-keyed wrappers still apply once. One `### Changed` entry in `## [Unreleased]`.
8. **Platforms.** Windows, macOS, Linux and WSL2 behave the same: `ContextVar`, JSON sizing and the existing telemetry store; no file, process or path behaviour is added.
9. **Transition.** With no override of an exempt name the served callables, wrapper chain and recorded events are unchanged.

## Scope

**Problem statement:** for an override of a tool that records its own cost, what the override adds after delegating to the core handler is never recorded.

**In scope:**

- The measured `core_handler` wrapper, the `ContextVar` scope, `_EXTENSION_OVERRIDE_DELTAS`, the `override_deltas` cost keyword and `_cost_pass_kwargs` in `wf_server/server_impl.py`.
- Tests in `tests/test_extension_tool_modules.py` with fixture overrides of an exempt lifecycle tool and an exempt retrieval tool.
- The **Overrides** paragraph of the spec, the current-state wrapper sentence, the threat-model extension-modules row and the CHANGELOG entry.

**Out of scope:**

- A post-response hook inside the core recording or publication sequence (Decision Log).
- Extractor credit (artifact, focus, state source) for override additions.
- Changing what any core callable records, or editing `_COST_EXEMPT_TOOLS`.

## Acceptance Criteria

- [x] AC-1: through `call_tool`, an override of an exempt lifecycle tool that delegates through `core_handler` and adds a field records exactly one extra cost event for the core name with `request_tokens == 0` and `response_tokens` equal to the size of the final response minus the size of the core response; an override that delegates and adds nothing records no extra event; the core's own recording is unchanged. Without the change no extra event is recorded.
- [x] AC-2: an override of an exempt retrieval tool (`code_*` or `docs_search`) that delegates and adds a field records the same delta event, and an override that answers without calling `core_handler` records the request and full response.
- [x] AC-3: the result returned by `core_handler`'s wrapper is the same object the core returned, an exception from the core propagates unchanged, calling the wrapper with no active scope records nothing, and the core handler of a non-exempt name called inside an exempt override's scope adds nothing to that scope.
- [x] AC-4: an override of a non-exempt name, a replacement, and every name with no override record exactly the events they record today (compared against the recorded events before the change); the stock declaration produces no `override_deltas` keyword.
- [x] AC-5: while the upgrade publication checkpoint is active the delta recorder writes nothing and the override's result is unchanged; a failing telemetry write leaves the result unchanged.
- [x] AC-6: an override of a lifecycle-locked exempt name observes its own hold in the process-hold registry after `core_handler` returns and before it returns, and a second process finds the lifecycle lock held during that window.
- [x] AC-7: the spec, the threat-model row and the CHANGELOG entry describe the recording rule, the call-count rule, the calling-thread rule, the measuring wrapper and the lock coverage of overrides.
- [x] AC-8: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-9: for one delegating override call of an exempt lifecycle tool, the wave's stage `calls` count in the context-efficiency totals rises by exactly the count a direct core call adds when the override adds nothing, and by that count plus one when it adds a field.
- [x] AC-10: while the upgrade publication checkpoint is active, the publication guard refuses a call to an override of a lifecycle-locked exempt name before the override's body runs (a fixture side effect at the top of the body never happens), and no delta event is recorded.

## Tasks

- [x] Add the `ContextVar` scope and the measured wrapper returned by `core_handler`.
- [x] Add `_EXTENSION_OVERRIDE_DELTAS` (cleared at install start and in the `register_mcp_surface` failure handler), and `override_deltas` to `_wrap_first_party_tool_costs` and `_cost_pass_kwargs`, with the delta recorder for those names.
- [x] Fixture overrides of an exempt lifecycle tool and an exempt retrieval tool; tests for AC-1 to AC-6, AC-9 and AC-10, including a real second-process lock probe for AC-6.
- [x] Record, in the Progress Log, each name-keyed set an overridden exempt name passes through and its disposition (cost exemption, lock, guard, extractors), as change `1zimo-enh extension-lifecycle-tools-and-artifact-credit` did.
- [x] Spec paragraph, current-state sentence, threat-model row and CHANGELOG entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Measured core handler and delta recorder | implementer | readiness, `1zlty-enh extension-response-key-renames` delivered | `server_impl` staging surface and cost wrapper |
| Docs | implementer | delta recorder | spec, current-state and CHANGELOG |
| Review | code-reviewer, qa-reviewer, architecture-reviewer | implementation | |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/current-state.md`
- `docs/architecture/threat-model.md`

The CHANGELOG entry is a root-level file and is listed here as prose only.

## Affected Architecture Docs

`docs/architecture/current-state.md` (tool registry and wrapper chain paragraph): one sentence that the main cost pass also takes the overridden exempt names, recording only what the override adds. `docs/architecture/threat-model.md` (extension-modules row): an override delegating through `core_handler` now receives a measuring wrapper around the unwrapped core handler rather than the bare handler. No boundary or flow change otherwise.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The recording gap for lifecycle overrides is the point of the change |
| AC-2 | required | Retrieval overrides have the same gap, and a non-delegating override must still be recorded |
| AC-3 | required | Delegation must stay transparent to the override |
| AC-4 | required | No double counting and no change for anything else |
| AC-5 | required | Accounting must stay observational |
| AC-6 | important | Pins the lock coverage the downstream request assumed was missing |
| AC-7 | required | Distributions need the rule documented |
| AC-8 | required | Standard verification |
| AC-9 | required | The delta event must not inflate the call count beyond the documented rule |
| AC-10 | required | Requirement 6's guard half must be executed, not inferred |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-03 | Delivery-review repair (N5, docs only). The spec's **Overrides** paragraph now states that for a lifecycle core that publishes the context-efficiency checkpoint (create, prepare, review and a mutating close), the checkpoint is published inside the core call, before the override's delta event is written, so the delta lands in the next checkpoint, or outside the wave once a sealing close has cleared focus. No code change. Full suite in a fresh scratch copy (`run_tests.py --no-cache`): 10,813 tests OK | `docs/specs/mcp-tool-surface.md` |
| 2026-10-03 | Implemented. `core_handler` returns `_measured_core_handler`, which captures `_OVERRIDE_COST_SCOPE` at build time and adds only a `_COST_EXEMPT_TOOLS` core result's size to the active scope; `_EXTENSION_OVERRIDE_DELTAS` is cleared at install start and in the `register_mcp_surface` failure handler and filled with installed exempt override targets; `_cost_pass_kwargs` passes `override_deltas`, and `_wrap_first_party_tool_costs` wraps those names with `_override_delta_recorder` (positive delta only, request and full response when no self-recording core was called, silent during the checkpoint, failures swallowed). Name-keyed sets an overridden exempt name passes through: `_COST_EXEMPT_TOOLS` keeps the full cost wrapper off and now routes to the delta recorder; `_LIFECYCLE_MUTATION_LOCK_TOOLS` (create, prepare, implement, close) and the publication writer registry (those four plus review) apply by served name, so the override runs locked and guarded; `_ARTIFACT_EXTRACTORS`, `_COST_FOCUS_EXTRACTORS` and `_STATE_SOURCE_EXTRACTORS` hold no exempt name and the delta recorder runs no extractor; `_CONTEXT_RETRIEVAL_TOOLS` and `_LIFECYCLE_CONTEXT_STAGES` act only inside the core callable's own recording, unchanged; `wf_reload_mcp` is exempt but a runner tool, never overridable. Deviation: `test_overrides_inherit_exactly_the_core_wrappers` now expects the `wf_create_wave` override's markers to be `cost` plus the stock markers, because the ACME fixture overrides that exempt name and now gets the delta recorder. Observed: a delegating `wf_close_wave` override adding a field recorded one event of 104 tokens with no request; the review-stage calls count rose by 1 for a direct core call and an override adding nothing, and by 2 for one adding a field; the second process found the lock `busy` after `core_handler` returned. Failing-first on the unfixed tree: `OverrideCostRecordingTests` setup, two `MeasuredCoreHandlerTests` and the markers test errored. Mutations all killed: bare handler returned, non-exempt core added to the scope, zero delta recorded, checkpoint silence off, `override_deltas` never passed, set not cleared on a late registration failure. Not pinned by a test: build-time capture of the `ContextVar` (it differs from a call-time lookup only for a reload during a call). Suites: as recorded for 1zltx | `test_extension_tool_modules.py` (`OverrideCostRecordingTests`, `MeasuredCoreHandlerTests`, `ExtensionServingTests`, `StockSurfaceTests` stock driver) |
| 2026-10-02 | Planned from the downstream request. Verified in the tree: `core_handler` returns `getattr(core_table[name], "fn")`, the core callable captured before argument normalization and `MIDDLEWARE`; `_wrap_first_party_tool_costs` skips names in `_COST_EXEMPT_TOOLS` unless in `extractor_free`, which `_cost_pass_kwargs` fills only with replacements; the exempt lifecycle tools record through `_lifecycle_context_result` and `_record_workflow_context`, the retrieval tools through `_record_retrieval_context`; overrides are installed by `_install_extension_tools` before `apply_middleware` runs `MIDDLEWARE` (cost, lock, guard, setup), keyed on the served name. The lock coverage of the post-core part of an override is inferred from that order, not yet executed; AC-6 executes it | `wf_server/server_impl.py` (`_extension_staging_surface`, `_wrap_first_party_tool_costs`, `_COST_EXEMPT_TOOLS`, `_cost_pass_kwargs`, `_lifecycle_context_result`, `_record_workflow_context`, `MIDDLEWARE`, `register_mcp_surface` install order) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-02 | Record the override's added size as a delta, measured by a scope that `core_handler`'s wrapper feeds | Fixes the gap with no change to any core callable or to `_COST_EXEMPT_TOOLS`, never double counts the core response, and keeps the existing observational wrapper contract | A declared post-response hook called inside the core recording and publication scope: it would have to be threaded through `_lifecycle_context_result` and every retrieval recorder, run under the core flush and the lock, be restricted to adding fields and convert failures to advisories; much more surface for a low-priority request. Recorded as the follow-up if a distribution needs its additions inside the published context-efficiency checkpoint |
| 2026-10-02 | Treat overrides of exempt names like replacements (`extractor_free`) was rejected | That records the request and the whole response again, double counting what the core already recorded | Put override targets of exempt names into `extractor_free` |
| 2026-10-02 | Readiness amendments: the delta event is recorded only when the delta is greater than 0 (a non-delegating override records its request and full response as the single event; a zero delta records nothing), and a delegating override that adds fields counts as two events in **Tool calls**, pinned by AC-9; only exempt cores add to the scope; the `ContextVar` is captured at wrapper build time; `core_handler` must be called on the calling thread; `_EXTENSION_OVERRIDE_DELTAS` is named and cleared at install start and on install failure; AC-10 executes the guard half of Requirement 6; the threat-model row is updated | Readiness review findings B1, N7 and N8. `context_efficiency.py` counts stage calls as `COUNT(*)` over `telemetry_event`, so a zero-delta event per call doubled **Tool calls** for every delegating override. Counting two events only when the override really added response bytes needs no telemetry schema or query change; marking delta events would need a new `telemetry_event` column and a filter in every consumer that counts events, for a low-priority accounting gap | Mark delta events and exclude them from the calls count; or keep recording a zero delta so every call shows in the ledger |
| 2026-10-02 | No lock nesting helper | Overrides already run entirely under the core name's lifecycle lock and publication guard because `MIDDLEWARE` wraps the served name after install; AC-6 pins it | Expose the lock so an override can nest it around `core_handler`, which `1zimn-enh extension-public-helpers` decided against |

## Risks

| Risk | Mitigation |
| --- | --- |
| The delta is an estimate: the core may measure its response before adding telemetry fields such as `workflow_instruction_proxy`, so those fields may count as override additions | The spec calls the figure an estimate of what the override added; a delta at or below zero records no event, so no negative debit is written; tests assert the documented formula, not a byte-exact ledger |
| A `ContextVar` scope leaks across calls | Reset in `finally`; AC-3 and a nesting test check the no-scope and nested cases |
| An override delegates to a different overridden name's core handler | All core results inside the scope are summed, so the delta stays what this call added beyond every core result |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
