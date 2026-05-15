# Walk Repo Node Modules Pruning

Change ID: `12kgw-bug walk-repo-node-modules-pruning`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

`walk_repo()` currently walks every path with `Path.rglob("*")` and only filters after enumeration. On repositories with large `node_modules` trees, that forces Python to stat a huge number of files that will be discarded later. The dashboard and index startup should prune excluded directories before descending so large dependency trees do not delay startup.

## Requirements

1. `walk_repo()` should prune excluded directories before descending into them.
2. The pruning should preserve the existing per-file filter logic as a safety net.
3. The file set returned by `walk_repo()` should remain the same for indexable files.
4. The optimization should not change ignore semantics for files that would otherwise be included.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`

**Out of scope:**

- Changing index file formats
- Changing stale detection policy
- Changing dashboard rendering or wave lifecycle behavior

## Acceptance Criteria

- `walk_repo()` uses directory pruning so excluded trees like `node_modules`, `.git`, and `dist` are skipped before file enumeration.
- The returned indexable file set matches the previous implementation for the same repo inputs.
- Existing filters remain in place as a safety net and continue to exclude the same files.
- Large trees no longer impose avoidable stat costs during startup walks.

## Tasks

- Replace `Path.rglob("*")` enumeration with a pruned `os.walk()` traversal
- Keep the existing per-file ignore checks unchanged
- Add regression coverage for pruning large excluded trees and preserving file outputs

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Startup should skip excluded directories before descending |
| AC-2 | required | The optimization must preserve indexable file outputs |
| AC-3 | required | Existing ignore behavior must remain a safety net |
| AC-4 | required | This fix targets large-tree startup latency |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Pruning accidentally skips indexable files | Keep the existing per-file filter loop and test against representative repos |
| Directory normalization differs between platforms | Normalize directory comparisons through the existing path handling helpers |
| Regression changes traversal order in a way that affects outputs | Sort the collected paths before applying the unchanged filter logic |
