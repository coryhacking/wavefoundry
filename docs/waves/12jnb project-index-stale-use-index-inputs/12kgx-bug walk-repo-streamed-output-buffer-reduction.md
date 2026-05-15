# Walk Repo Streamed Output Buffer Reduction

Change ID: `12kgx-bug walk-repo-streamed-output-buffer-reduction`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

`walk_repo()` already prunes excluded directories before descending, but it still buffers every enumerated path in a temporary `all_entries` list before applying the per-file filters. On very large repositories, that keeps unnecessary paths in memory and delays the final sort/filter pass. The walker should stream accepted files directly into the result list and only retain indexable paths.

## Requirements

1. `walk_repo()` should apply the existing per-file filters while traversing, instead of buffering every enumerated path first.
2. The optimization should keep deterministic output ordering for the returned file list.
3. The returned indexable file set should remain unchanged for the same repo inputs.
4. The pruning behavior from the previous change should remain intact.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`

**Out of scope:**

- Changing index file formats
- Changing stale detection policy
- Changing dashboard rendering or wave lifecycle behavior

## Acceptance Criteria

- `walk_repo()` no longer materializes a temporary list of every candidate path before filtering.
- The returned indexable file set matches the previous implementation for representative repos.
- Excluded trees are still pruned before descent, and the remaining per-file checks stay as a safety net.
- The returned ordering remains deterministic.

## Tasks

- Stream candidate files through the existing per-file filters during traversal
- Preserve deterministic ordering without buffering excluded paths
- Add regression coverage for output parity and exclusion handling

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Avoid buffering every enumerated path before filtering |
| AC-2 | required | Preserve indexable output parity |
| AC-3 | required | Preserve pruning and safety-net behavior |
| AC-4 | required | Keep output ordering deterministic |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Traversal order drifts across platforms | Sort the surviving results before returning |
| Streaming changes subtle filter behavior | Keep the existing per-file filter logic intact and cover the same representative cases |
