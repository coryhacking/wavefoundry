# Bounded document checks and migration compatibility

Change ID: `20k55-bug bounded-document-checks-and-migration-compatibility`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-13
Wave: `20k56 bounded-document-checks-and-migration-compatibility`

## Rationale

Make documentation validation and upgrade preview safe and predictable for project-owned files while supporting explicitly declared legacy prompt vocabulary. Ordinary markdown currently bypasses the bounded record-document reader; new-only role targets can abort a document-move preview when they cannot be inspected; and the standalone review-plan classifier has no additive declaration point for an exact legacy contract. The intended consumers are local lint, render and upgrade operations. Success means bounded reads, useful per-path refusal reporting, unaffected eligible work continuing where the existing migration contract permits it, and exact declared migrations without importing installed framework state.

## Requirements

1. Apply a contained, no-link, nonblocking regular-file read capped at the existing 8 MiB document budget to ordinary markdown selected by the docs-lint metadata/link scans and the root agent entry files. Derive this set from `markdown_scan_roots`, `iter_markdown_docs`, `iter_linkable_docs` and `_ENTRY_FILES`; preserve configured record roots and archive exclusions. The strict policy refuses every lexical parent component and final entry that is a symlink or reparse point, including linked scan roots; use no-follow descriptor traversal where supported and documented checked fallback limits elsewhere. Preserve successful decoding/newline behavior and the existing record-document refusal contract.
2. Both full and incremental lint must report refused inputs once per repository-relative entry with a bounded cause class, without target paths or target content. Refusal remains a non-clean lint result; skipping an unreadable input is not successful validation. A replaced file must not reuse cached target content. Reuse the central containment machinery with an explicit strict read policy; existing callers that intentionally allow contained internal links keep their default behavior.
3. A new-only council role document or native wrapper that cannot be safely read or decoded is preserved, reported and excluded from confirmed migration pairs. The standalone role migration and combined role/lifecycle migration propagate those diagnostics consistently in preview and apply. Unrelated valid pairs still plan normally. Existing old-source conflicts, unreadable move sources and publication failures keep their preflight/refusal behavior; a skipped target never grants link-rewrite authority. Existing identity mismatch handling is not relaxed merely to obtain a clean result.
4. Add `EXTRA_REVIEW_PLAN_LEGACY_CONTRACT_PROFILES` beside the shipped profiles in the standard-library-only checker, empty as shipped. A distribution may edit that source constant in its incoming pack. Each declaration uses the existing named profile and exact labelled old-line/replacement-lines shape. Validate the declaration and combine it with the shipped profiles for classification. Preserve the exactly-one-match rule, one occurrence per required old line, newline preservation and project-prose preservation. Invalid, empty, conflicting or ambiguous declarations and unrecognized custom text fail closed with actionable bounded diagnostics.
5. Installed preflight, incoming privately loaded preflight and render consume the same declared classifier semantics. Do not import project modules, installed extension modules, or runtime configuration to obtain the declaration. Defaults remain available and unchanged.
6. Keep permanent outcomes in this change and the wave record plus canonical tests and required typed evidence. No new readiness sidecars, evidence folders, upgrade scan passes or unconditional whole-tree migration scans.

## Scope

**Problem statement:** Equivalent document inputs currently receive inconsistent read and migration treatment depending on whether they are lifecycle records, ordinary docs, or already-moved role targets.

**In scope:** `contained_files.py` if needed for an explicit no-link read option; `wave_lint_lib/helpers.py`, its direct metadata/link/refusal consumers and full/incremental CLI reporting; new-only role-pair observation and diagnostic propagation in `render_agent_surfaces.py`; exact profile declarations in `review_plan_prompt_check.py`; focused tests and the existing architecture and distribution-seam documentation.

**Out of scope:** Changing markdown link semantics, making all repository readers strict, rewriting unreadable files, weakening move preflight or docs gates, adding runtime profile discovery, new approval or identity mechanisms, full runtime reload, packaging, closure and publication. No claims of native Windows execution without qualification.

Intended code/test files are declared below. Implementer owns writes; reviewers inspect and exercise isolated fixtures without editing source or review ledgers. Framework seeds, generated root agent guides and hook configuration are protected from direct editing in this wave: no semantic change to them is planned. If implementation reveals a necessary new owner or behavioral surface, update this plan and obtain focused readiness review before editing it.

## Acceptance Criteria

- [x] AC-1: Full and incremental docs-lint paths do not read linked, nonregular, oversized or replaced ordinary markdown/entry targets; they emit deterministic entry-only refusal diagnostics and retain a non-clean result. Bounded fixture observations distinguish safe refusal from a hang, target-content disclosure or false clean scan, while ordinary valid docs and existing record behavior remain unchanged.
- [x] AC-2: Public role-only and combined document-move previews report and preserve an unreadable, linked, nonregular, oversized or invalid-UTF-8 new-only role/wrapper, omit its pair from repair authority and still plan unrelated valid work. Preview writes nothing; apply obeys the same skip/refusal decisions. Existing conflicts and invalid old sources remain refused before moves.
- [x] AC-3: An explicitly declared exact legacy profile migrates through classifier, render and installed/incoming preflight paths while the two shipped profiles remain accepted. Undeclared wording, malformed profiles, duplicates and ambiguous matches are refused without changing either prompt. The privately loaded checker remains standard-library-only.
- [x] AC-4: The change's focused tests pass and cover successful behavior plus meaningful refusal/ambiguity controls; authored documentation states the actual read policy, extension shape, migration limits and platform qualification. No failure elsewhere is attributable to this change.

## Tasks

- [x] Add the central strict read mode and route the generic docs metadata/link inventory and agent entry reads through it; preserve record compatibility and cache/refusal semantics.
- [x] Make new-only role observations return bounded diagnostics through both migration entry points without licensing skipped targets.
- [x] Add and validate the explicit exact-profile declaration in the standalone checker; exercise incoming private-load and renderer consumers.
- [x] Add focused ordinary-doc/entry read, public migration and declared-profile regressions; run their affected suites and inspect negative controls.
- [x] Update the architecture/seam contract and changelog, then complete required readiness/delivery evidence and pause for operator closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness and scope | wave-coordinator, independent council | — | Plan and exact owned boundaries reviewed before code edits |
| Contained doc reads | implementer | Readiness and scope | One owner for helper, reporting and direct consumers |
| Migration and declared contracts | implementer | Readiness and scope | Serialize shared renderer/checker/upgrade-test edits |
| Verification and delivery | independent reviewers | Implementation | Code, QA, architecture, security and docs-contract remits; required automatic lanes retained |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/contained_files.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/helpers.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/core_validators.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/link_validators.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/review_plan_prompt_check.py`
- `.wavefoundry/framework/scripts/tests/test_contained_files.py`
- `.wavefoundry/framework/scripts/tests/test_qualification_report.py`
- `.wavefoundry/framework/scripts/tests/test_workflow_include_prefixes.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_distribution_seams.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `docs/architecture/cross-cutting-concerns.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/specs/mcp-tool-surface.md`

Coordinate edits to `test_upgrade_wavefoundry.py` with any simultaneous test-portability repair; do not replace another wave's changes. Qualification runs after all admitted implementation batches are stable. Root `CHANGELOG.md` receives only a generic behavior summary.

Keep the existing qualification-report wrong-parent and workflow-config replacement controls compatible with the new containment keywords. Their test wrappers must accept and forward those keywords while retaining both fault injections and all refusal/state-preservation assertions. No production-reader change is part of this integration repair.

## Affected Architecture Docs

- `docs/architecture/cross-cutting-concerns.md`: distinguish the strict docs reader from default contained-link semantics and retain runtime-lock/platform limitations.
- `docs/architecture/data-and-control-flow.md`: role-pair preview diagnostics and privately loaded exact-profile declaration.
- `docs/specs/mcp-tool-surface.md`: document the additive source declaration beside existing distribution seams and the unchanged docs gate contract.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The lint gate must not inspect refused target content or claim it was checked |
| AC-2 | required | A harmless preserved new-only input must not prevent unrelated valid preview work |
| AC-3 | required | Declaration support must remain exact, shared and independently loadable |
| AC-4 | required | The owned behavior and its limits must be verifiable and documented |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
| 2026-10-13 | After focused readiness currency and recorded repair start, both qualification-report and workflow-config mock wrappers now accept and forward containment keywords. Both original refusal tests pass with their injections/assertions unchanged. Production readers unchanged; fresh QA reverification and final qualification pending. | Canonical targeted controls; recorded cycle-1 repair; no release/closure claim |
| 2026-10-13 | Implemented strict cached ordinary-document reads, non-clean refusal reporting, new-only role/wrapper skip diagnostics, and exact source-declared legacy profiles. Final affected modules: 1,483 tests pass with one intended skip; 46 upgrade-boundary tests pass. Known-bad strict-link, new-only abort and ignored-declaration controls fail as intended. Full docs validation passes. Final combined qualification and independent delivery remain pending. | StrictCachedReadTests; StrictOrdinaryDocumentTests; NewOnlyRoleRefusalTests; DeclaredLegacyReviewPlanTests; native Windows unrun |
| 2026-10-13 | Readied and opened after independent council approval. Readback: strict 8 MiB ordinary-doc/entry and carrier reads keep refusals non-clean; new-only role failures preserve inputs without granting link authority; standalone profiles remain exact and source-declared. Implementer owns bounded source/test changes; coordinator owns prose and final combined qualification. | Current typed readiness; AC-1..AC-4; live MCP reads and memory briefing |
| 2026-10-13 | Planned from live source inspection; no implementation edits or approval claims. | Generic docs read dispatch, role-pair confirmation callers and standalone classifier inspected |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-13 | Reuse central descriptor reads with an explicit no-link policy; report refused docs as non-clean. | Bounds I/O while preserving existing contained-link consumers and truthful lint results. | A preliminary `lstat` plus ordinary read retains a replacement window; applying strict semantics globally changes unrelated contracts. |
| 2026-10-13 | Skip and report only unconfirmable new-only role targets, preserving old-source preflight. | A destination grants no repair authority until confirmed, and unrelated preview work remains useful. | Aborting every preview repeats an avoidable robustness failure; accepting the name alone grants unsupported link rewrite authority. |
| 2026-10-13 | Empty source-level extra profile constant in the standalone checker. | One explicit distribution seam works in private incoming loads without runtime dependencies. | Importing a distribution module couples preflight to the installed tree; fuzzy wording or substring matching can authorize destructive migration of customized content. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Refusal collection differs between full and incremental scans | Exercise both public CLI paths; preserve deterministic single-path reporting and existing record messages |
| Existing containment follows internal links intentionally | Add an explicit strict policy with default behavior unchanged; use descriptor/identity checks, not check-then-read |
| Skipping a target accidentally grants a link-repair pair | Assert pair omission and unchanged links alongside reported diagnostics |
| New declaration weakens exact migration recognition | Validate the finite tuple shape and uniqueness; retain exactly-one recognized profile and preserve originals on refusal |
| Standalone preflight imports installed project state | Keep all declaration data in the privately loadable checker and retain restricted-import tests |
| Extra close/upgrade overhead | Reuse existing reports, scans and typed ledgers; no new persistent evidence or repeated broad qualification |

## Session Handoff

Ready for independent plan/readiness review after admission. No code edits have been made. Wave closure, commits and packaging require their own operator direction.
