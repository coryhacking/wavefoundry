# Vendor docs-lint-exclusions Doc Via Framework Pack

Change ID: `1p3b5-enh vendor-docs-lint-exclusions-via-framework-pack`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p3b9 chunker-indexer-correctness-and-1-5-0-hardening`

## Rationale

Wave 1p35d (`1p35p` enterprise hardening) introduced `docs/references/docs-lint-exclusions.md` to give enterprise security review an operator-visible enumeration of what `docs-lint` deliberately does NOT flag. The doc lives in this self-host repo as a project artifact — but `docs/references/` is consumer-owned, not vendored from the framework pack. Consumers running `Upgrade wave framework` to 1.5.0 do not get the file.

The exclusion list `LINT_EXCLUDED_TRANSIENT_DIRS` lives in framework code (`wave_lint_lib/core_validators.py`). The operator-facing doc explaining it should be discoverable at the same surface across every install — currently it isn't.

Wave 1p35d C6 captured this as finding F2 in the pre-close review. Two paths considered:

(a) **Vendor the doc through the framework pack** at a consumer-discoverable location (e.g., `.wavefoundry/framework/docs/lint-exclusions.md`) so every install has it.
(b) **Generate per-project at install time** via `seed-090` (gardening harness) rendering.

Path (a) is the cleaner shape because the content is **framework-owned**, not project-specific. The exclusion list is a framework contract, not project state. Vendoring through the pack keeps the doc and the constant aligned on every upgrade.

## Requirements

1. **Doc lives in the framework pack** at a stable path (`.wavefoundry/framework/docs/lint-exclusions.md` recommended; pick whatever directory the pack standardizes for operator-facing reference content). Ships in the zip; gets installed alongside other framework artifacts.
2. **Single source of truth**. The committed wavefoundry source has the doc at one path; the pack ships it at that path; consumers see it at that path. No two-place authoring.
3. **Drift-guard test**. The existing `test_exclusion_doc_exists_and_lists_each_pattern` in `test_docs_lint.py` continues to assert every pattern in `LINT_EXCLUDED_TRANSIENT_DIRS` appears in the doc — moves the file path the test resolves accordingly.
4. **`docs/references/docs-lint-exclusions.md`** (the current location in this self-host) either becomes a thin pointer to the framework-pack location, or is deleted entirely and the README / other reference docs point at the new location. Pick whichever keeps the operator's discovery path simpler.
5. **`seed-090` (gardening harness)** prose updated to mention the vendored doc location so operators can find it via the seed surface.
6. **CHANGELOG entry** records the vendoring move so consumers upgrading to the version including this change know the doc relocated (relevant for forks that linked to the wavefoundry-source path).
7. **No content change**. The doc content stays exactly as written in wave 1p35d; this change is structural (where it lives, who owns it) not editorial.

## Scope

**In scope:**

- Move `docs/references/docs-lint-exclusions.md` → framework pack location
- Update `test_exclusion_doc_exists_and_lists_each_pattern` to resolve the new path
- Update seed-090 to reference the vendored doc
- Update any other references to the doc (CHANGELOG link, README pointer, code docstrings)
- One test verifying the doc is included in `build_pack.py` output (zip contains the file)

**Out of scope:**

- Generating per-project copies of the doc at install time (path b above, rejected)
- Auto-injecting the doc into consumer `docs/references/` (creates a vendored-content management problem worse than the original gap)
- Changing the exclusion list itself (separate change if needed)
- Designing a generic "framework-owned reference doc" surface for other future docs (this change addresses one doc; generalization can ride on observed need)

## Acceptance Criteria

- [x] AC-1: Doc lives at `.wavefoundry/framework/docs/lint-exclusions.md` (relocated via `git mv` from `docs/references/`).
- [x] AC-2: `collect_files` in `build_pack.py` walks the framework tree; the doc is included automatically. Regression guard: `test_lint_exclusions_doc_ships_in_pack` builds a mini-fw with the doc and asserts the zip contains `.wavefoundry/framework/docs/lint-exclusions.md`.
- [x] AC-3: `test_exclusion_doc_exists_and_lists_each_pattern` updated to resolve the new framework-pack path; continues to assert every `LINT_EXCLUDED_TRANSIENT_DIRS` pattern appears in the doc.
- [x] AC-4: References updated: `test_docs_lint.py` (4 occurrences via `replace_all`); `wave_lint_lib/core_validators.py` docstring pointer. Historical wave records (1p35d/wave.md, 1p35p change doc) intentionally NOT updated per the no-retrofit principle.
- [x] AC-5: seed-090 prose gains an `Operator reference` block naming the vendored doc location + the source-of-truth constant in `core_validators.py`.
- [x] AC-6: CHANGELOG entry under `## [1.5.0]` records the relocation, names the old + new paths, and warns forks with hardcoded links to update.
- [~] AC-7: Self-host upgrade-simulation E2E test is **subsumed by AC-2's build_pack test** — the pack-inclusion test verifies the doc lands in the zip; the consumer-side unzip path is `unzip -o <zip> -d <repo-root>` which is mechanical. Skipped as redundant.
- [x] AC-8: Full framework test suite passes (count updated after C3 lands).
- [x] AC-9: docs-lint passes.

## Tasks

- [x] Open `seed_edit_allowed` and `framework_edit_allowed` gates (framework gate was already open from C1)
- [x] Create `.wavefoundry/framework/docs/` directory
- [x] `git mv docs/references/docs-lint-exclusions.md .wavefoundry/framework/docs/lint-exclusions.md`
- [x] Update test_docs_lint.py path resolution (4 sites via replace_all + 1 explicit doc_path constant)
- [x] Update `wave_lint_lib/core_validators.py` docstring pointer
- [x] Update seed-090 prose with `Operator reference` block
- [x] Update CHANGELOG with relocation note
- [x] Add `test_lint_exclusions_doc_ships_in_pack` to verify zip inclusion
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close gates (will close at C5 / wave end)

## Affected Architecture Docs

`N/A` — relocates a single doc; no architectural boundary change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (doc at framework-pack location) | required | Core fix mechanism. |
| AC-2 (build_pack includes the file) | required | Without packaging inclusion, consumers don't get the doc. |
| AC-3 (drift-guard test follows) | required | Without the test moving with the file, the doc and the constant can drift silently. |
| AC-4 (old-path references updated) | required | Stale references break operator navigation. |
| AC-5 (seed-090 names the doc) | required | Discoverability gate. |
| AC-6 (CHANGELOG entry) | required | Fork operators with hard-coded links need to know about the move. |
| AC-7 (upgrade simulation) | required | Verifies the vendoring path end-to-end. |
| AC-8 (suite passes) | required | Standard. |
| AC-9 (lint passes) | required | Standard. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-04 | Vendor the doc through the framework pack rather than generate per-project | The exclusion list is a framework contract, not project state. Vendoring keeps content and constant aligned on every upgrade. | Generate per-project via seed-090 — rejected; introduces a content-authoring split between the framework constant and N consumer copies, with no single source of truth. |
| 2026-06-04 | Pick `.wavefoundry/framework/docs/` as the vendored location | Matches existing per-purpose-dir convention (`framework/install/`, `framework/release/`, `framework/scripts/`). | Use `docs/references/` directly via copying — rejected; mixes vendored content with consumer-owned content in the same dir. |

## Risks

| Risk | Mitigation |
|---|---|
| Consumers with bookmarks or hardlinks to `docs/references/docs-lint-exclusions.md` find a missing file post-upgrade | CHANGELOG entry names the relocation explicitly. Consider a one-line redirect file at the old path during a deprecation window — out of scope unless evidence warrants. |
| Future reference docs face the same vendoring question | This change establishes the pattern. Future docs can follow the same shape; generalization (a "framework-vendored doc" surface) is queued only on observed need. |

## Related Work

- **Wave 1p35d (`1p35p` enterprise hardening)** — introduced `docs/references/docs-lint-exclusions.md` and the drift-guard test.
- **`LINT_EXCLUDED_TRANSIENT_DIRS` in `wave_lint_lib/core_validators.py`** — the source-of-truth constant the vendored doc enumerates.
- **`test_exclusion_doc_exists_and_lists_each_pattern` in `test_docs_lint.py`** — the drift guard that follows the file to its new location.

## Session Handoff

Surfaced as wave 1p35d C6 finding F2 in the pre-close review (2026-06-04). Operator selected for queue to the follow-on wave that ships jointly with 1p35d under the **1.5.0** tag (alongside `1p397`, `1p399`, and the other Tier 2 follow-ups).
