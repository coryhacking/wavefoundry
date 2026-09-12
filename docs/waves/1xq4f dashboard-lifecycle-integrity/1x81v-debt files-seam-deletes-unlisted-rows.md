# Preserve Unlisted Content During Targeted Index Builds

Change ID: `1x81v-debt files-seam-deletes-unlisted-rows`
Change Status: `review`
Owner: Engineering
Status: active
Last verified: 2026-09-11
Wave: 1xq4f dashboard-lifecycle-integrity

## Rationale

An explicit `build_index(files=[...])` bypasses the repository walk but currently treats the selected files as the entire corpus. `_detect_changes` subtracts their paths from every prior path and the eligibility reap removes unlisted rows. The defect was reproduced during `1x6ti` and the current SQLite implementation retains the same derivation. The operator selected this repair for `1xq4f` alongside shared-store lifetime fixes. Preserve the useful programmatic seam, without adding a CLI or MCP parameter.

## Requirements

1. A non-null `files=` selection is a partial update, never an authoritative repository census. Unlisted canonical chunks, vectors, FTS, graph/extraction state, bookkeeping and layer hashes remain intact.
2. Listed existing files are processed normally; an explicitly listed missing file may retire only its own indexed state. An empty selection is a no-op with respect to corpus membership. Out-of-root paths remain rejected/ignored according to the existing boundary.
3. A targeted request must not publish global model/chunker/walker, graph builder/schema or corpus-policy currency that it has not established. When an index-wide rebuild is necessary, refuse the partial request before schema reset/initialization or other mutation, with actionable guidance to run a complete walk. `full=True` with an explicit selection is likewise refused rather than replacing the corpus.
4. The normal filesystem-walk path retains its existing deletion, exclusion, unreadable-subtree preservation and publication behavior. Pending storage rebuild still requires a complete walk.

## Scope

**In scope:** targeted selection, removal and eligibility derivation in the coordinated indexer; preservation across all shared-store participants; focused real-SQLite tests and the documented programmatic contract. A bounded graph producer adjustment is allowed only if needed to merge selected paths while retaining prior extraction state.

**Out of scope:** exposing `files=` through CLI/MCP, changing complete-walk reap policy, partial storage migration, new model or schema changes, or fixing unrelated build behavior.

## Acceptance Criteria

- [x] AC-1: Seed two source files and both semantic layers plus graph state, change one and run `files=[one]`; the other file's canonical text, vectors, FTS, graph/extraction records, bookkeeping and layer hashes remain unchanged. The selected file becomes current, and removing the selection-preservation mechanism makes a named test fail.
- [x] AC-2: The following ordinary walk does not regenerate or re-embed unlisted unchanged content. Test an explicitly selected deletion and an empty selection: only the named deletion is retired and empty selection removes nothing. Normal complete-walk deletion still works.
- [x] AC-3: Explicit selection plus full rebuild, incompatible index constants/model, graph builder/schema, or a pending storage rebuild refuses before destructive publication, retains the prior corpus and gives complete-walk recovery guidance. The permissive known-bad variant fails named assertions.

## Tasks

- [x] Preserve unselected corpus and auxiliary state while deriving changes/removals from explicit selection.
- [x] Pin selected deletion, empty selection and subsequent ordinary-walk behavior using real SQLite and bounded fake embeddings.
- [x] Refuse partial requests that would claim index-wide rebuild currency; preserve existing complete-walk and migration gates.
- [x] Record named known-bad controls and run affected tests.
- [x] Update the targeted-build caveat in `docs/architecture/data-and-control-flow.md` and describe the user benefit in the changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| T1 targeted preservation | implementer | compatibility C1 | Same indexer writer; serialize with lifetime repair. |
| T2 tests and docs | implementer | T1 | Real shared-store census and follow-up walk. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`, `docs/architecture/data-and-control-flow.md`

Use the same owner as compatibility C1 for shared indexer/graph files and tests. Serialize shared architecture documentation with C4 and dashboard L3.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: replace the destructive `files=` caveat with the partial-update contract and complete-walk refusal conditions.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevent unrelated retrieval content from disappearing. |
| AC-2 | required | Preserve deletion semantics and avoid needless regeneration. |
| AC-3 | required | Partial work cannot establish whole-index compatibility. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-04 | Original defect filed from `1x6ti` readiness council RED-PREP-5. | Historical scratch probe `prep_redteam/probe_b2_files_seam.py`. |
| 2026-09-11 | Operator approved admission with preservation rather than parameter removal; plan updated for unified SQLite. | Current `_build_index_locked` selection branch and `_detect_changes` still derive removals from unlisted paths. |
| 2026-09-11 | Readback: files=None stays a full census; files=[] preserves membership; a nonempty selection updates/retires only selected paths and retains unlisted state even when absent on disk. Refuse global currency/full rebuild before mutation. Thought: T1/T2 share C1 indexer owner; test all participants and follow-up walk. | Current readiness receipt and typed lane approvals; implementation now authorized. |
| 2026-09-11 | Storage/targeted implementation complete: final eight contract tests and exact-definition consumer pass; six named production mutants fail. A schema-refusal defect found in the broader run is repaired and passes focused verification; canonical full validation is pending. | `implementation-evidence.json`: storage_and_targeted, frozen source hashes. |

| 2026-09-11 | Implementation complete and ready for delivery review: canonical suite green, 8,898 tests across 86 files, 12 skips; receipt recomputed against the final source. Docs gate and whitespace check pass. | `implementation-evidence.json`: canonical_validation. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-11 | Keep `files=` as a partial update; preserve unlisted content. | Matches programmatic targeted-update intent and avoids destructive surprise. | Removing the parameter would break existing test/evaluation callers and eliminate useful targeted indexing. Treating the selection as the whole corpus retains the defect. |
| 2026-09-11 | Refuse selection plus whole-index rebuild requirements. | A subset cannot establish global currency or rebuild a migration. | Silent promotion to a full walk surprises callers about cost and scope. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A semantic-only preservation fix still removes graph or auxiliary rows. | Test every participant and trace all membership consumers. |
| Partial work incorrectly stamps global version or configuration currency. | Explicit refusal and prior-state assertions. |
| Broad preservation prevents legitimate deletions. | Test explicitly listed missing paths and an ordinary full walk. |

## Plan Review

2026-09-11: Selection preservation includes graph current-path membership and finalize known-minus-current retirement, idle reap/orphan reconciliation, and layer eligibility. Currency refusal must precede `ensure_current` and include graph builder/schema as well as semantic identity. These are implementation consequences of the admitted preservation requirement, not new user-facing scope.

## Session Handoff

Admitted with operator authorization; re-Prepare the three-change wave before implementation. No new public tool parameter is proposed.
