# Declare distribution lifecycle compatibility seams

Change ID: `20qvo-enh distribution-lifecycle-seams`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20qvn distribution-lifecycle-compatibility`

## Rationale

Distributions need bounded policy extension points for activation scope, safe upgrade-time previews and legacy hook ownership without forking core lifecycle logic.

## Requirements

1. Keep repository-wide single-open scope as the default; support a declared canonical parent-folder scope for nested container layouts. Apply the same scope to every activation path derived from the shared activation guard.
2. Resolve scope within canonical contained record paths. Same-scope concurrent activation stays excluded; do not partition or weaken the repository publication lock.
3. Allow explicitly declared distribution preview tools to execute during unfinished upgrades under a no-publication context. Overrides must receive the context; framework publication APIs must refuse writes in that context. Declared extension Python remains trusted code, not sandboxed against direct filesystem or external side effects.
4. Allow declared exact legacy hook command forms/ownership markers to be pruned during render, including supported absolute extensionless forms. Preserve unrelated user commands and make repeated renders stable.

## Scope

In scope: the requirements above, registered entry-point regressions, canonical guidance and necessary generated surfaces.
Out of scope: unrelated refactoring, timing investigation, production-target mutation, external publication and release execution.

## Acceptance Criteria

- [x] AC-1: Default and nested-scope tests prove same-parent exclusion, different-parent admission and consistent prepare/reopen/implementation activation behavior.
- [x] AC-2: Concurrency and invalid-scope tests preserve publication serialization and refuse escaped/ambiguous scope.
- [x] AC-3: Registered override previews work during pending upgrades without writes; undeclared tools and attempted publication remain refused.
- [x] AC-4: Render fixtures replace declared legacy hooks once, preserve unrelated entries and remain byte-stable on rerender.

## Tasks

- [x] Inventory all activation and preview dispatch paths and existing profile declarations.
- [x] Implement the smallest shared scope and explicit preview contracts.
- [x] Add exact ownership declarations to the existing hook-render contract.
- [x] Exercise registered dispatch and render fixtures; update extension and migration guidance.
- [x] Complete readiness before code edits and required delivery review; retain durable results in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation and guidance | Implementer | Readiness | Single write owner; serialize shared files |
| Verification and review | QA and required reviewers | Implementation | Read-only review; coordinator records evidence |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/publication_control.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`
- `docs/architecture/data-and-control-flow.md`

Write ownership: implementer owns admitted behavior and its derived callers/tests. Canonical seed edits precede regeneration; do not hand-patch generated surfaces. Reviewers are read-only. Protect publication guards, recovery checkpoints, unrelated user hooks/docs, secrets and existing evidence; no historical ledger rewrites. Confirm exact seed/config edits during Prepare before opening gates.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` and applicable canonical setup, extension, lifecycle or release guidance.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core observable contract |
| AC-2 | required | Core observable contract |
| AC-3 | required | Core observable contract |
| AC-4 | required | Core observable contract |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned only; implementation and approvals pending | This plan and wave record |
| 2026-10-15 | Readback: implement repository-default and opt-in canonical parent activation scope across all three callers; multiple open waves require explicit selection. Declared Prepare/close dry-run overrides inherit a publication-refusing context with loaded provenance checks. Exact event/whole-command legacy declarations preserve foreign hooks. Before: another parent blocks activation and overrides cannot preview; after: declared parent scope admits it and declared current overrides preview without writes. AC-1–4; record_paths, server_impl, publication_control, extension declarations, renderer, focused tests and canonical lifecycle guidance. | Admitted requirements and current source inventory |

| 2026-10-15 | Implemented shared scope/preview/hook seams and reconciled canonical guidance. Parent scope uses contained discovered records; all three activation callers retain global publication/lifecycle locking. Implicit census: current-wave helper, audit, resource, dashboard and generated capture now report ambiguity; telemetry already requires a unique open wave and safely keeps general attribution without selecting a record. Seed050 owns exact hook render guidance; seed160 remains unchanged by coordinator direction. Generated session-capture bundle regenerated; existing review carrier points to canonical seed209, so no duplicate generated review prose was needed. | Source and focused fixtures |
| 2026-10-15 | Initial record/distribution/core-preview99 passed. Registered extension preview2 and final target10 passed. Parent scope/registered concurrency/implicit consumer/capture/renderer6 passed. Compatibility473 had one declaration-reset fixture failure, repaired; census/tool-surface28 passed. Four qvo mutants detected scope-filter deletion, first-open selection, broad hook ownership and provenance bypass; three more detected missing nested requirement, canonical-target validation and preview declaration validation. Named tests and finite scripts: /private/tmp/20qvn-mutants.py and /private/tmp/20qvn-validation-mutants.py. No live services, model operations or external target execution. | Focused validation; no whole-suite claim |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Choose declarative narrow seams implemented by shared core policy. | Coherent contract with focused regression coverage | Distribution overrides for whole handlers: duplicate safety logic. Relax all guards globally: removes intentional serialization and ownership checks. |

## Open Decisions

No unresolved operator scope decision. Prepare must verify exact API/schema compatibility and source-derived affected paths.

## Risks

| Risk | Mitigation |
| --- | --- |
| Preview extensions may try to publish; enforce read-only behavior at the publication boundary, not only by convention. | Use public-path positive and negative controls; preserve contracts outside scope. |
| Review overhead | Keep durable conclusions in wave.md and temporary probes outside tracked evidence folders; reuse valid qualification. |

## Source-derived implementation contract

- Add an import-light `OPEN_CONTAINER_SCOPE` declaration beside `record_paths.NESTED`, default `repository`, optional `parent`. `parent` requires the nested layout; the scope is the immediate canonical parent of the wave directory (not the record file). Direct children share the waves root. Reuse contained layout validation; reject unknown values and noncanonical targets rather than silently widening or narrowing scope.
- Apply that policy in the existing `_find_other_active_wave` guard used by prepare activation, implement and reopen. Keep the repository publication and lifecycle locks unchanged. When more than one wave is open, implicit current-wave selection must report ambiguity and request an explicit ID; never select a different parent's first record as a write target. Single-open and planned fallback behavior remain compatible.
- Add a narrow `EXTENSION_UPGRADE_PREVIEW_TOOLS` declaration in `mcp_tool_extensions.py` for declared overrides of canonical Prepare and close only. Preserve their supported dry-run modes, checkpoint compatibility and current-code tests; reject undeclared names, incompatible replacements and malformed declarations. Aliases resolve through the canonical wrapped handler. Delegation through existing `core_handler` inherits the same read-only context without duplicate accounting.
- Preview eligibility must verify declared module/helper source digests and declaration identity against the loaded provenance as well as the existing core/launcher identity. A marker on a callable alone is insufficient. Expose preview status through the extension staging surface so an override can branch explicitly. Framework mutation/publication entry points remain fail-closed, and previews do not write locks, receipts, focus, telemetry or docs. Trusted extension code remains responsible for avoiding direct I/O; this seam is not a Python sandbox.
- Use renderer-only `EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS`, empty by default, in the existing declaration module. Entries describe exact event and command text, optionally with a single supported repository-root placeholder for old absolute launchers. Validate before writing; expand only that placeholder and compare the complete command. Do not grant ownership through substring, basename, regex, arbitrary shell parsing or evaluating commands. Preserve other commands in a mixed entry and preserve unrelated metadata. Current canonical hook recognition remains covered by its existing fixtures.
- Focused tests belong in `test_record_paths.py`, `test_distribution_seams.py`, `test_server_tools_lifecycle.py`, `test_extension_tool_modules.py` and `test_render_platform_surfaces.py`, with lock/concurrency controls using the existing lifecycle harness. Update the extension declarations and lifecycle guidance; no new plugin framework or subprocess execution is required.

Source inspection: `record_paths.py` defines merge-time layout constants; `server_impl._find_other_active_wave` has three activation callers and `_current_wave_from` currently selects the first open record. `_wrap_upgrade_publication_guard` excludes replacements and only accepts a core marker; `_upgrade_preview_code_current` currently checks core setup and launcher identities. `render_claude_settings` preserves mixed hook entries but recognizes current commands by marker text. These are implementation anchors, not executed review approvals.
