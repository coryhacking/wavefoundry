# Handler Module Split Three Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Phase: readiness. Context: `handler-split-three-readiness-20260921`. This reviews the five plans, not delivered behavior; nothing is implemented.

## Council

Seats ran in separate fresh contexts against the admitted change docs, the wave record and the `1y0h2` and `1ymzk` precedents: `red-team` (fixed) and `docs-contract-reviewer` (rotating, bound to the receipt), with `architecture-reviewer` also run. The code-reviewer, qa-reviewer, security-reviewer and release-reviewer readiness lanes ran in the same round, fresh and independent. Every seat verified plan claims against the tree with AST walks, greps and live reads rather than the plans' prose.

Strongest challenge (red-team and security together): the first-draft containment primitive matched about eighty functions on its predicate, not the ten the plan named, and the sites do not share one predicate or one failure contract; adopting a plain check outright would have weakened seven of them. The index plan, second in the first draft, edits `retrieval_eval.py` and moves the evaluator's identity, which made the whole wave's receipt pair incomparable.

Strongest alternative (architecture): split the wave into three (containment alone; the four handler moves; index last as its own wave) so each carries one receipt pair. The operator chose one wave, reordered: containment, context efficiency, thin wrappers, upgrade, then index last, with a three-receipt sequence whose comparable pair closes before the index change.

## Findings and repair

Blocking in the first round, all repaired in one rewrite pass:

- Containment: the primitive became a flagged one (`strict`, `refuse_symlink_components`) with three adoption classes, per-site predicate and failure-contract preservation, an explicit allowlist, a thirteen-case test plan and a census test; moved first in the wave so its `indexer.py` edit sits inside the receipt window.
- Context efficiency: the interlock fixture in `test_index_source_guard.py` patches `_read_ce_projection_config` on the server and starts the real monitor, so the moved projector must read that name through `server_impl` at call time or the `1yj14` tests time out; four moved-to-moved and source-text sites named; monitor owner corrected to `ImplHandler`; census corrected to seventeen definitions.
- Thin wrappers: `wf_audit_response` is decorated at definition time by a factory in the monolith and cannot move under the recipe; `_run_post_write_lint` is patched by the shared hermeticity fixture and stays with its only caller; the secrets close gate, the introspection trio and the next-action table stay; about fifty-seven dashboard patch sites listed; the gate tools need a tool-to-response map.
- Upgrade: the extension hook runs from the new archive against the installed tree at `pre_extract`, so a name-level fallback would abort every upgrade from an older install; the phase-to-process mapping was backwards (only cleanup runs in the fresh process); the purpose sentence overstated load reduction; `test_upgrade_extensions.py` does not exist.
- Index: moved last because it alone moves evaluator identity; forty-odd moved-to-moved sites listed; `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` becomes a call-time read because the shared `load_server()` fixture assigns it on the server; the `test_docs_lint.py` baseline pin named.
- Wave record: dependencies on `1ymzk` and on `1yljp`'s after-receipt declared; the three-receipt sequence written; the objective no longer claims the runner avoids loading the server.

## Focused verification

Three fresh verifiers checked the rewritten packet against the tree (one per pair of docs: wrappers and upgrade; index and the wave record; containment and context efficiency under the security and docs-contract seats). None found a blocking defect in the settled design; each found plan-text errors that would have misdirected the implementer, all folded before this record was written:

- Wrappers: the "no `server_impl` import at any scope" wording contradicted the recipe (function-level import per call) and is now "no module-top import"; the thirteen-name dashboard census included the two child-PID helpers, so the child-PID trio (set, register, reap) is placed with index and the dashboard module holds eleven; the `DOCS_LINT_*` constants and `_regenerate_codebase_map_safe` stay in the root because no docs mover reads them; only two `run_garden` patches are moved-to-moved and the roughly sixty around lifecycle stayers must not be repointed; `_read_guard_overrides` and `_EDIT_GOVERNANCE_GATE_MAP` are reached by `codenav_handlers`; `DASHBOARD_START_WAIT_SECONDS` has a second read in a nested default argument; `wf_sync_surfaces_response` reaches the lint attacher.
- Upgrade: `_read_framework_pack_version` is called at import time for `SERVER_IMPL_VERSION` and `_setup_notice_key` belongs to `ImplHandler`, so fourteen definitions move, not sixteen; `UPGRADE_SUMMARY_TERMINAL_KEYS` is a twelfth moving object with two call-time reads; the legacy-name fallback tests must set `sys.modules["dashboard_handlers"]` to `None` because the real module is importable in the test process.
- Index: the `_REASON_*` names are a five-way tuple unpack of `_LEXICAL_FALLBACK_REASONS`, read per call; the staying monitor policy reaches two movers; the caller breakdown was off by one bucket; patch sites are enumerated as calls, not blocks, and the `_background_refresh_active` patches around movers were missing; `_graph_refresh_then_recheck` is reached only by attribute from other handler modules.
- Containment and context efficiency: `indexer._is_relative_to` raises on resolve errors today at all seven sites, two of which are inclusive, so the `None`-to-`False` direction is recorded per site; `resolve_path_under_root` moves to the sub-clause class to keep its two diagnostic codes distinct; the census is thirty helpers with eighteen allowlisted, not twenty-two and thirteen; `_STATUS_PATTERN` has seven bare users, not seventeen; `data-and-control-flow.md` names the renderer helper (contract unchanged); the standing-baseline anchors are a table row and a bold paragraph, not headings.
- Wave record: both `1ymzk-before` and `1yljp-before` receipts are invalid (`index_not_ready`) and `1yljp` is implementing, so R0 waits for `1yljp` to close and a complete index; the fallback baseline is `1y0bf-final`.

Cross-wave note surfaced to the operator, not repaired here: `1ymzj` in wave `1ymzk` repoints the two standing-baseline references without naming the `post-1wybs` literal pin in `test_docs_lint.py`; implementing it as written breaks that pin.

Known-bad detection in this round: every blocking item above was detected by a seat or lane reading the tree, not the plan; the readiness rule of one full review, one bounded repair and one focused verification was followed, and the focused round's findings were all plan-text corrections rather than build-changing defects, so approvals were recorded without a further round. Verdict: approved; no readiness blockers remain.

Requested lane settings: host default model and effort for all seats and lanes. Observed runtime identity: unknown.

Limits: no implementation; no test module was executed in this round (the plans name the modules and the delivery lanes run them); reachability closures are name-based and do not follow `_load_script` string dispatch, which the committed inventories grep for; patch-site counts are regex counts that the inventories must re-derive as calls.

## Current-tree delta check (2026-09-21, before implementation)

The prior approval is withheld by `READY-DELTA-RECEIPT-IDENTITY`. The supported `docs_search_response` live fallback reaches `WaveIndex.search_docs_lexical`, `_live_docs_chunks`, then `indexer._is_relative_to`. Adopting the planned primitive therefore requires its evaluator membership at the first change; that edits the evaluator identity and invalidates the promised R0/R1 comparison. No implementation source has changed. Operator decision is pending on staging the real unused primitive/tests/evaluator membership before a new-baseline R0, with all caller adoption after R0; index extraction remains the final R2 identity boundary.

Provenance correction: the initial finding's structured source lanes incorrectly include architecture and QA. Only the fresh red-team worker performed that independent inspection; its observation narrative correctly says so. The coordinator also inspected the call chain. A typed same-cycle correction was rejected because an existing finding requires the repair/reverification path, so no historical JSONL was rewritten and no corroborating lanes or approvals are invented. Treat architecture/QA attribution on that historical row as erroneous; actual focused verification must establish its own provenance.

Established dependency corrections for the pending packet: 1ymzk is closed and its after receipt passes; 1yljp is closed with the operator's scoped benchmark waiver, so it has no required after receipt to await. The existing signed 1ymzk after receipt is the historical reference.

## Security delta: resolution errors and the removal veto

Finding: `READY-DELTA-CONTAINMENT-ERROR`. Actual reviewer lane: `security-reviewer` only. Context: `split3-security-readiness-delta-20260921`. This supersedes the earlier no-blockers conclusion for this specific planned behavior. The current source remains unchanged: `indexer._is_relative_to` catches only `ValueError`; `_validate_prepared_removals` uses it inclusively in its explicit-request branch before constructing the removal veto. MCP reads rechecked these exact bodies before recording.

The planned mapping of resolve `OSError`/`RuntimeError` to `False` changes more than a harmless file drop. On explicit requested files, `_validate_prepared_removals` drops the unresolvable candidate from `current`; the later removal veto then misses it, and this branch collects no unreadable-directory evidence. Preserve the current raising contract. The smallest proposed repair is to leave `indexer._is_relative_to` unchanged and explicitly allowlist it; operator decision is pending. No plan repair or approval is recorded by this reviewer.

The following exact bounded probe was executed from the repository root with `python3 -B`. It compiles the two current function bodies without importing the production module, supplies identity policy filters, and injects a transient resolution failure. The second helper simulates only the proposed error mapping; the new primitive does not exist yet. This is a faithful local removal-veto boundary check, not a registered public indexing call, an actual filesystem-error reproduction, or evidence that stored rows were deleted. No files or index state are changed by the probe.

```python
import ast
from pathlib import Path
from unittest.mock import patch
source = Path('.wavefoundry/framework/scripts/indexer.py').read_text()
tree = ast.parse(source)
names = {'_is_relative_to', '_validate_prepared_removals'}
ns = {'Path': Path, 'SourceChanged': type('SourceChanged', (Exception,), {})}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), '<source-extracted-indexer-functions>', 'exec'), ns)
for name in ('_filter_canonical_wave_event_ledgers', '_filter_memory_archive_bodies', '_filter_legacy_memory_pointers', '_filter_secret_scan_findings', '_filter_project_index_excludes', '_filter_code_files'):
    ns[name] = lambda paths, *args, **kwargs: paths
ns['_graph_layer_for_index_dir'] = lambda _: 'project'
ns['_project_meta_include_prefixes'] = lambda *args: ()
ns['_effective_project_include_prefixes'] = lambda *args: ()
ns['_shadowed_by_unreadable'] = lambda *args: False
kwargs = dict(root=Path('/repo'), index_dir=Path('/repo/.wavefoundry/index'), removed_meta={'a.md'}, removed_by_layer={'docs': {'a.md'}}, requested_files=[Path('/repo/a.md')], respect_ignore=True, include_prefixes=(), project_include_prefixes=(), include_tests=False, include_generated=False)
old = ns['_is_relative_to']
def proposed_bool(path, parent):
    try:
        return old(path, parent)
    except (OSError, RuntimeError, ValueError):
        return False
with patch.object(Path, 'resolve', side_effect=OSError('injected transient resolution error')), patch.object(Path, 'is_file', return_value=True):
    for label, helper in [('current', old), ('proposed error mapping simulation', proposed_bool)]:
        ns['_is_relative_to'] = helper
        try:
            ns['_validate_prepared_removals'](**kwargs)
            print(label + ': returns normally (removal veto absent)')
        except Exception as exc:
            print(label + ': ' + type(exc).__name__ + ': ' + str(exc))
```

Expected: resolution uncertainty aborts the destructive-membership check. Observed output:

```text
current: OSError: injected transient resolution error
proposed error mapping simulation: returns normally (removal veto absent)
```

The known-bad detection is the deliberately simulated exception-to-False variant, which the comparison distinguishes from the current raising guard. Readiness integrity attestations apply to that named boundary and current-tree plan review only. Observed model/runtime identity: unknown. No independent corroboration by other lanes is claimed.


## Operator disposition — containment error repair

On 2026-09-21 the operator approved preserving `indexer._is_relative_to` unchanged and explicitly allowlisting it. Repair cycle 1 was recorded before plan mutation. The containment plan now names two outright adoptions, nine sub-clause adoptions and nineteen allowlisted helpers. Its AC-2 explicitly protects the indexer helper and callers. No framework code changed. The earlier indexer retrieval route no longer establishes primitive membership; derive membership from remaining adopters before bootstrap and verify independently. Fresh focused reverification is still outstanding; retained reviewers are not fresh contexts.


## Fresh focused architecture verification — 2026-09-21

Reviewer responsibility: architecture-reviewer. Fresh independent context: `split3_fresh_repair_review`; requested model/effort inherited host defaults, observed runtime identity unknown. Reviewed after commit `4a8b8951`, with plans frozen. This is new evidence, not retroactive architecture or QA participation in the original receipt finding. The historical source-lane attribution remains erroneous; no QA approval is claimed.

The staged sequence is internally coherent: unused primitive and justified evaluator registration/tests precede new-baseline R0; all eleven adoptions through upgrade precede comparable R1; index extraction creates the separately disclosed R2 identity boundary. The unchanged indexer helper cannot justify primitive registration. Current `git diff -- .wavefoundry/framework/scripts/indexer.py` was empty.

An independently executed `python3 -B` replay of the exact source-extracted indexer probe above produced `current: OSError: injected transient resolution error` and `known-bad mapping: returns normally (removal veto absent)`. This verifies the reason for preserving the helper and distinguishes the rejected mapping. It is a bounded function-boundary probe with mocked resolution/filter inputs, not a public indexing invocation or evidence of actual deletion.

Remaining-adopter reachability has a conditional route that must not be erased by the indexer exclusion: `code_ask_response` → `WaveIndex.search_combined` → `_graph_signal_candidates` (`server_impl.py:2145-2146`) → `graph_query.get_query_index` → `_ensure_graph_builder_current` → dynamic loading of `indexer.py` and `build_index(content="graph", full=True)` (`graph_query.py:301-321`) → build finalization (`indexer.py:5791`) → `index_state_store.finalize_build_epoch` → `memory_backfill.authorize_index_finalize` or `restage_index_finalize` → `inventory_closed_waves` → `_wave_status` → `memory_backfill._contained_source_file`. The latter is one of the eleven remaining adopters. Finalization reads `WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID` and optionally `WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT` (`index_state_store.py:3322-3328, 3346-3370, 3393-3426`); authorization and restaging census the waves (`memory_backfill.py:744,838`), and `_wave_status` checks the containment helper (`memory_backfill.py:176-178`). This is a supported conditional call route requiring stale graph and backfill publication context, not evidence that the ordinary benchmark fixtures exercise it. No stale-graph rebuild, migration, or publication was executed.

Evaluator roots are exactly the four direct response calls (`retrieval_eval.py:1558-1567`), without ImplHandler telemetry wrappers. Its initial complete-state/vector-corpus checks (`retrieval_eval.py:1523-1555`) do not themselves prove the conditional graph route unreachable; a build may subsequently invalidate the measurement through generation drift. Membership therefore has a supported-path justification through the remaining memory-backfill adopter if the plan retains supported-path closure as its criterion; record that conditional scope explicitly before bootstrap. Do not claim universal absence of remaining-adopter reachability, or ordinary-fixture execution of this branch.

Method and limits: MCP `code_ask`, `code_outline`, exact-token searches and targeted current source reads preceded a conservative AST name-unified call closure. That probe visited 1,537 symbols and deliberately over-approximated attribute calls; its `session.run` → `memory_eval.run` memory-record paths are false name collisions and were discarded after reading `accel_embedder.py:633`. The memory-backfill route above was then resolved against actual module-qualified/dynamic-load code. The other directly inspected adopters belong to map, lifecycle, memory mutation, renderer/reconciliation, TechDocs and workflow-instruction accounting; this is not an exhaustive proof against arbitrary dynamic dispatch.

Disposition: the indexer preservation repair is verified and the staged identity boundaries are coherent. No overall readiness approval is issued by this section: the security lane is independently checking a remaining root-resolution failure-contract issue, and the coordinator must reconcile typed chains and required-lane approvals against the current receipt. No implementation source was edited and no full suite or benchmark was run by this reviewer.
