# Shared Path Containment Primitive

Change ID: `1ymzp-ref shared-path-containment-primitive`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-21
Wave: `1ymzq handler-module-split-three`

## Rationale

Path containment, the check that a candidate path resolves inside a root and does not escape through `..`, an absolute path or a symlink, has no single owner. The readiness census (three independent AST scans) found thirty dedicated containment helpers across the scripts, not the ten the first draft grepped by name (the focused verification re-derived the count: nine copies, one adoption, twenty more; the AC-3 census test is the final figure). Nine are hand-rolled copies with `_contained` or `_is_relative_to` in the name: `indexer._is_relative_to`, `context_efficiency._contained_prompt`, `memory_backfill._contained_source_file`, `memory_supply._contained_source_file`, `memory_records._contained_record_path`, `_contained_memory_subdir_path` and `_contained_purge_staging_path`, `render_agent_surfaces._contained_review_carrier_path`, `server_impl._contained_wave_review_paths`; `techdocs_audit_lib._contained` already delegates to the renderer helper and is an adoption, not a copy. Twenty more the grep missed: `server_impl.resolve_path_under_root` (the allowed-roots validation `docs/SECURITY.md` and the threat model describe), `server_impl._resolve_repo_path` (the code-navigation root boundary, patched by `test_handler_modules`), `review_policy.contained_relative_path` (public, refuses any symlink component), `retrieval_eval._path_under_root` and `confined_report_path`, `context_efficiency.contained_stat_signature`, `docs_gardener._under_a_scan_root`, `dashboard_server._asset_path`, `memory_records.canonical_memory_root` and `_purge_disposition_path`, `memory_backfill._canonical_waves_dir`, `setup_readiness._safe`, `record_paths._resolved_inside` (which deliberately uses `os.path.realpath` because the docs-lint hot loop pins that), `lifecycle_gates._framework_test_receipt_status`, `upgrade_extensions._guard_owned_path` (an lstat walk refusing links and Windows reparse points, no resolve at all), `upgrade_wavefoundry._retired_sidecar_path_error`, `review_evidence._review_authority_path_error`, `wave_lint_lib/helpers._is_under` (lexical, no resolve), `techdocs_audit_lib._inside`, `repair_ppol_memory_staging.safe`.

The security lane's per-site table shows the sites do not agree on one predicate. Two are containment-shaped and can adopt only behind their existing resolution/error boundaries: `render_agent_surfaces._contained_review_carrier_path` (non-strict candidate resolution supports missing write targets, returns the resolved path, writer opens it with `O_NOFOLLOW`) and `techdocs_audit_lib._contained` (a repoint). `indexer._is_relative_to` remains unchanged and explicitly allowlisted: it catches only `ValueError`, and resolution `OSError` or `RuntimeError` must continue to abort. Its five exclusion and two inclusion sites have different polarity; converting a resolution error to `False` lets `_validate_prepared_removals` lose its explicit-request removal veto. The rest enforce stronger or different predicates that a plain check must not weaken: existence (`resolve(strict=True)`) and regular-file checks in `_contained_prompt` and both `_contained_source_file` helpers; lstat-level refusal of any symlink, even one resolving inside, in both `_contained_source_file` helpers and `review_policy.contained_relative_path`; exact-parent equality against a canonical location in the `memory_records` trio; a five-invariant layout check (canonical waves root, depth window, file-symlink equality) in `_contained_wave_review_paths`; envelope diagnostics in `resolve_path_under_root`. Failure contracts today span `False`, `None`, `ValueError`, `RuntimeError`, `OSError`, `FileNotFoundError` and a `(None, diagnostic)` tuple. Two of the named sites have no escape test at all (`_contained_prompt`, `memory_supply._contained_source_file`).

So the change is narrower and more honest than the first draft: one stdlib containment owner with a resolving entry point and a pure already-resolved comparison entry point, wrapped adoption at the two containment-shaped sites, adoption of only the redundant sub-clause at the stronger sites with every other clause kept verbatim, an explicit allowlist with reasons for what stays hand-rolled, and a census predicate that isolates single-purpose helpers rather than every function that happens to call `resolve()`.

This change runs first in the wave so every production adoption sits inside the wave's receipt window, after a narrowly staged unused-module/evaluator bootstrap, and because it touches eight modules the handler moves do not edit.

## Requirements

1. A new stdlib-only module `.wavefoundry/framework/scripts/path_containment.py` exports `contained_path(root, candidate, *, strict=False, refuse_symlink_components=False) -> Path | None`. Semantics: both root and candidate are resolved; with `strict=False` the existing prefix is followed physically and a non-existent tail is collapsed lexically, so write targets are judged by where they would land; with `strict=True` the candidate must exist; with `refuse_symlink_components=True` any symlink in the candidate's components below the root is refused even if it resolves inside (lstat walk); the root itself is accepted as contained; the RESOLVED path is returned so write sites open it, never the original spelling; case-variant spellings are refused, not normalized (the docs record that case aliases are handled elsewhere by `os.path.samefile`); the exception set caught and mapped to `None` is `(OSError, RuntimeError, ValueError)`, which covers the 3.11 and 3.12 symlink-loop `RuntimeError`; a strict exception is not part of the primitive, because the raising sites keep four different exception types and their own wrappers. The docstring states all of this and the merge-time expectation that forks add no second implementation. The same module exports `contained_resolved_path(root, candidate) -> Path | None`: a pure native-path comparison of already-resolved paths, returning candidate when contained (including equality) and None otherwise. It performs no resolve, stat, lstat, normalization, or other filesystem operation. Callers must supply already-resolved absolute native paths without unresolved `..`; callers own resolution and symlink policy. `contained_path` delegates its final comparison to this helper so there is one comparison implementation; existing wrappers use the pure helper after their original filesystem operations.
2. Adoption by class, each site's predicate and failure contract preserved and recorded in the inventory before the edit: (a) wrapped adoption, `render_agent_surfaces._contained_review_carrier_path` and `techdocs_audit_lib._contained`. Preserve the renderer's uncaught `repo_root.resolve()` before its candidate-resolution try, `candidate.resolve(strict=False)`, candidate `OSError` translation with its existing diagnostic/cause, and escaping-path diagnostic. Its root `OSError` must still propagate; candidate `RuntimeError` must still propagate unchanged. The primitive replaces only the containment decision after those existing resolution boundaries; do not route an initial root or candidate resolution through the primitive's catch-all. TechDocs may repoint only with equivalent initial root/candidate resolution and its existing `RuntimeError`-to-`None` boundary preserved: root `OSError` propagates while renderer-style refusal remains `None`. If delegating to the renderer remains necessary to preserve those contracts exactly, keep that delegation and classify TechDocs as indirect adoption in the inventory/census rather than weakening its contract. No conversion to `strict=True`; missing write targets remain supported. Use the pure already-resolved helper: no extra filesystem operation may follow the existing resolution boundaries. Differential tests assert the exact original resolution calls and detect a mutant that re-resolves; unchanged source-text alone is insufficient; (b) sub-clause only, `server_impl.resolve_path_under_root` (keeps its own resolve `try` so the `path_resolution_failed` and `path_outside_allowed_roots` diagnostics stay distinct; only the `relative_to` clause is replaced), the `memory_records` trio, `_contained_wave_review_paths`, both `_contained_source_file` helpers, `_contained_prompt`, `review_policy.contained_relative_path` (which keeps its existing symlink-component walk and returns the unresolved path), where the pure helper replaces only the containment comparison and every canonical-location, exact-parent, existence, regular-file and symlink clause stays verbatim, pinned by a source-text test per site; (c) explicitly allowlisted with reasons: `indexer._is_relative_to` (preserve its raising contract and all seven call sites unchanged; resolution uncertainty must abort prepared-removal validation), `record_paths._resolved_inside` (hot-loop constraint forbids `Path.resolve`), `upgrade_extensions._guard_owned_path` (no resolve by design), `wave_lint_lib/helpers._is_under` (lexical by design), and the remaining fifteen, each with a one-line reason and a follow-up marker (nineteen allowlisted in all; the census test reports the true number).
3. Tests, in `tests/test_path_containment.py`: thirteen cases, parent escape through a non-existent tail, absolute escape and absolute inside, directory-symlink escape with a non-existent final component, file-symlink escape, dangling symlink to an outside target refused and to an inside target accepted, root equals candidate, relative inside, root that is itself a symlink accepted on both sides, symlink loop under root pinned per interpreter branch, leave-and-re-enter symlink accepted by the primitive and refused with the flag, case-only difference refused, injected `PureWindowsPath` pairs (drive-letter mismatch refused, case-only accepted, same UNC share accepted, different share refused, `\\?\` prefix refused as a documented false reject; not `os.path.normcase`, which is the identity on POSIX), and a `strict=True` non-existent candidate refused. Each adopted site's existing tests pass unchanged; `_contained_prompt` and `memory_supply._contained_source_file` gain the escape tests they lack; each sub-clause site gains a source-text pin on its retained clauses. Renderer and TechDocs gain differential fault-injection tests for root `OSError`, root/candidate `RuntimeError`, candidate `OSError`, escape refusal, and missing inside write targets. Assert exception class, preserved diagnostic/cause where applicable, or `None` at the actual wrapper boundary; a mutant swallowing root `OSError` must fail. A second-resolution fault must not change wrapper success; pure-helper tests forbid filesystem operations and cover native POSIX/Windows comparison semantics.
4. Census: a test asserts that every single-purpose containment helper under `.wavefoundry/framework/scripts/` either calls the primitive or is in the allowlist with a reason. Predicate (AST): a function whose body calls `.resolve(` or `os.path.realpath(`, then `relative_to`, `is_relative_to`, or an equality on a resolved value, whose return is a bare constant or a raise, with at most twenty-five statements and calls restricted to path, string and the named layout helpers; recorded as an approximation. Polarity mutants plant a `Path.resolve` form and a `realpath` form in a temp tree and assert both are reported; a stale-allowlist check fails when an allowlisted helper no longer exists or has adopted.
5. Evaluator: preserving `indexer._is_relative_to` removes the proposed adoption on the previously identified `WaveIndex._live_docs_chunks` route. Do not use that unchanged route as evidence that `path_containment.py` belongs in `PRODUCTION_RETRIEVAL_MODULES`. Before the bootstrap, derive membership from the remaining eleven planned adoptions and the measured tools' supported call closure; record the resolved symbols and an independent review of that derivation. If another measured route reaches the primitive, register it before R0 under the operator-approved staged sequence and pin membership/identity with a test; otherwise record the exclusion and make no speculative evaluator registration. Only the real unused primitive, its focused tests and justified evaluator membership/identity test may precede R0; prove no production caller adoption or import yet. R0 is a new baseline, not a comparison to the old reference. All production adoption follows R0; R1 uses that same evaluator identity. The purge list gains the module only if `server_impl.py` imports it at module top; a per-call reach needs no entry and the inventory says which.
6. Documentation: `docs/architecture/cross-cutting-concerns.md` (Shared Utilities) gains one line naming the primitive as the containment owner; `docs/architecture/layering-rules.md` (Shared path resolution) adds it as a fourth stdlib-only owner and repoints the `wf techdocs-audit` row's "shared helper"; `docs/SECURITY.md` and `docs/architecture/threat-model.md` carry allowed-roots claims only and need no edit.

## Scope

**Problem statement:** a security primitive is implemented thirty ways with seven failure conventions, and a plain containment check is weaker than half of them.

**In scope:** the module with a two-flag resolving entry point and a pure already-resolved comparison; wrapped adoption at two sites; sub-clause adoption at nine sites with retained clauses pinned; the allowlist with reasons; the thirteen-case test module; the two missing escape tests; the census and its mutants; the evaluator derivation; the two architecture doc lines; a CHANGELOG bullet.

**Out of scope:** the kickoff's `foundation/` package move; changing any site's predicate or failure behavior; adopting at the allowlisted sites; a raising variant of the primitive; storage-identity comparisons.

## Acceptance Criteria

- [x] AC-1: `path_containment.contained_path` exists with both flags and the thirteen cases passing, including symlinks created on disk and the interpreter-pinned loop case.
- [x] AC-2: The two wrapped sites and nine sub-clause sites adopt the primitive (TechDocs may delegate through the renderer as explicitly inventoried), each preserving its recorded predicate and failure contract; the retained clauses are pinned by source text; `indexer._is_relative_to` and its callers remain unchanged and its allowlist entry records the exception-preserving removal-veto contract; each site's existing tests pass unchanged and the two missing escape tests exist.
- [x] AC-3: The census passes with the recorded allowlist, its stale-entry check passes, and both polarity mutants are reported.
- [x] AC-4: The evaluator derivation for `path_containment.py` is recorded and, if it joins, pinned by a test.
- [x] AC-5: The change's own suites and every test it adds pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Commit the inventory: all thirty sites with predicate, failure contract, callers (including `wave_lint_lib/core_validators.py`'s reach into the renderer helper and the direct test references), class (a, b or c) and reason.
- [x] Create the module and its thirteen-case test file.
- [x] Adopt at the two wrapped sites, then the nine sub-clause sites, one module at a time, adding the source-text pins and the two missing escape tests.
- [x] Add the census, allowlist, stale check and polarity mutants; record the evaluator derivation; architecture doc lines; CHANGELOG bullet; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| containment-inventory | implementer | clean readiness | Classify before the unused-module bootstrap; no caller adoption until R0. |
| primitive-and-adoption | implementer | inventory, unused-module bootstrap and R0 | One module at a time after R0; bootstrap is the explicit pre-R0 exception. |
| independent-review | required reviewers | primitive-and-adoption | Security-reviewer lane reads the per-site table. |

## Serialization Points

- `.wavefoundry/framework/scripts/path_containment.py`
- `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/memory_backfill.py`
- `.wavefoundry/framework/scripts/memory_supply.py`
- `.wavefoundry/framework/scripts/memory_records.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/test_path_containment.py`
- `docs/architecture/cross-cutting-concerns.md`
- `docs/architecture/layering-rules.md`

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` (Shared Utilities) and `docs/architecture/layering-rules.md` (Shared path resolution and the `wf techdocs-audit` row). `docs/architecture/data-and-control-flow.md` names the renderer helper and its unchanged `RuntimeError` contract, so it needs no edit; `docs/SECURITY.md` and `docs/architecture/threat-model.md` name none of the helpers and need no edit.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The primitive is the change. |
| AC-2 | required | Adoption without weakening any site is the safety property. |
| AC-3 | required | Without the census the next copy appears unnoticed. |
| AC-4 | required | Production retrieval identity must be derived. |
| AC-5 | required | Change-local correctness. |

## Progress Log

Final delivery checkpoint (2026-09-22): all required lanes and Council approved unchanged reviewed source; R2 baseline independently verified including index AC-5. Full 9,508-test receipt current. Evidence: `evidence/qa-final.md`, `evidence/council-final.md`, `retrieval-evidence.md`. Earlier pending checkpoints are historical and resolved.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Implemented pure comparison and eleven adoptions (TechDocs indirect), preserving original filesystem operations and diagnostics; module-top server import plus purge membership. Census tracks thirty sites, nineteen exemptions and two explicit non-containment scanner false positives. Required delivery review remains pending. | `test_path_containment`: 23 tests; six existing adopter modules: 643 tests; nested layout: 18 tests; server path boundary: 2 tests, all passed. Real modified-scratch reload passed. In-memory re-resolution mutant caused 4 expected errors; root-OSError swallowing caused 2 expected failures. Initial broad invocation named nonexistent `test_memory_supply`; corrected invocation passed all 643 actual tests (supply coverage lives in memory records/backfill). `git diff --check` clean; `indexer.py` diff empty. |
| 2026-09-21 | Reflect / Thought: the wrapper-preservation contract forbids extra filesystem calls, not merely changed first-call handling. Operator approved a pure already-resolved comparison in the same owner; obtain scoped readiness review before adoption. | /private/tmp/1ymzq_extra_resolution_probe.py reproduces original success versus extra-resolution refusal. |
| 2026-09-21 | Observe: R0 completed as a valid new baseline, no invalidation reasons; source freeze ended after evaluator exit. CPU reranker fallback followed isolated CoreML probe failure; no embedding rebuild. | docs/reports/retrieval-quality-1ymzq-before.json; run 9660e98184a322494510fd6d22254e28228679d523fe8baede8f1f30beec2d6c. |
| 2026-09-21 | Observe: unused bootstrap complete; 15 containment/identity tests and 148 evaluator tests pass, no skips. No production imports in AST scan; removing membership makes identity test fail. Inventory is a durable reviewed artifact, not a Git commit. Coordinator read primitive/test/diff and confirmed caller boundaries untouched. | containment-inventory.md; test_path_containment.py; test_retrieval_eval.py. Primitive SHA256 38956bd0796c5982a26a48235e7b814ddcddcf2b6e81a8ca6fe360f61e3ebc0c; evaluator 2db63339b76ad3d655bb3c311eb039a2429ca7880940f7dfd442ad4c8a49fd03. |
| 2026-09-21 | Readback / Thought: stage only the unused stdlib primitive, its focused tests and justified evaluator membership before R0. Preserve all eleven caller boundaries, including untouched indexer; adopt callers only after R0. Files: path_containment.py, test_path_containment.py, retrieval_eval.py and focused identity test. | Current readied receipt; remaining memory-backfill supported retrieval route documented by architecture. |
| 2026-09-21 | Gapfill: targeted shell symbol search supplemented MCP navigation for locating the existing production-identity test; implementation will use local AST operations for mechanical inventories and moves after MCP source orientation. | MCP code_read/code_outline and subsequent code_keyword resolved test_handler_modules.test_codenav_edit_moves_production_identity. |
| 2026-09-21 | Planned from the kickoff's foundation slice; the first draft counted ten helpers by name. | grep of `def _contained`, `_is_relative_to`. |
| 2026-09-21 | Readiness round: security, red-team, code, QA and architecture reviews found thirty sites, showed the first predicate matched about eighty functions, and produced the per-site predicate and failure table; the plan was rewritten to a flagged primitive, three adoption classes, an explicit allowlist and a thirteen-case test plan, and moved to first in the wave for the receipt window. | Readiness review in this wave directory; context `handler-split-three-readiness-20260921`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Operator approved the shared pure comparison entry point after an extra-resolution fault changed successful wrapper behavior. | Keep existing filesystem operations and failure boundaries; resolving API delegates the same comparison. R0 already contains the module in evaluator membership, so this implementation edit preserves evaluator identity for R1. | Re-resolving wrappers; rejected. Defer consolidation; not selected. |
| 2026-09-21 | Operator approved staging unused primitive/tests/evaluator membership before new-baseline R0; caller adoption follows R0. | The original proposed indexer adoption changed evaluator identity before the promised comparable pair; after excluding that adoption, remaining-call reachability must be re-derived before registration. | Separate containment wave; not selected. |
| 2026-09-21 | Operator approved preserving and explicitly allowlisting `indexer._is_relative_to`. | Exception-to-False conversion loses the prepared-removal veto on resolution uncertainty; preserve existing failure behavior. | Primitive adoption with exception swallowing; rejected. |
| 2026-09-21 | Operator approved a bounded root-resolution contract repair and focused verification. | Preserve renderer and TechDocs root `OSError`, candidate-resolution error boundaries, and non-strict missing write-target acceptance; no relaxation of AC-2. | Catch-all adoption; rejected by independently executed differential probe. |
| 2026-09-21 | Primitive without the package move. | The move is churn for a fork; the primitive is a real consolidation. | Full foundation package as the kickoff wrote it. |
| 2026-09-21 | Two flags, no raising variant. | Sites need existence and strict-symlink semantics today; raising sites keep four exception types. | One flag-free signature (first draft); would weaken eight sites. |
| 2026-09-21 | Three adoption classes with an explicit allowlist. | Half the sites cannot adopt outright without changing what they enforce. | Adopt everywhere; rejected as a behavior change. |
| 2026-09-21 | First in the wave. | All eleven caller adoptions must sit inside the receipt window; the indexer helper is protected from change. | Parallel or last; leaves a production-module edit outside the pair. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A sub-clause adoption silently drops a retained clause. | Source-text pin per site on the retained clauses; a mutant that removes one clause fails the pin. |
| Windows behavior is unprovable here. | Injected pure-path pairs; recorded limitation. |
| The census predicate is an approximation. | Stated as such; allowlist carries reasons; polarity mutants in two forms. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

Computational verification: full framework suite passed 9,508 tests across 121 files (12 skips). Required independent delivery review is still pending.
