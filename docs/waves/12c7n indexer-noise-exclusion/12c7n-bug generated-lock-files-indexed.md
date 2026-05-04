# Generated and Lock Files Indexed

Change ID: `12c7n-bug generated-lock-files-indexed`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-03
Wave: `12c7n indexer-noise-exclusion`

## Rationale

Machine-generated files — dependency lock files, test snapshots, and generated JSON blobs — are being indexed as semantic code. On a real project, Vitest CDK snapshot files generated 2,970 chunks (17%), `.excalidraw` diagram files generated 259 chunks (1.5%), and `tsconfig.spec.json` files repeated across ~50 library packages produce near-identical chunks each time. Unlike binary files, these are valid text and pass the null-byte sniff — they require explicit exclusion by extension or filename pattern. `.excalidraw` files are JSON-format diagram data with no code semantics. Repeated boilerplate configs (`tsconfig.spec.json`) bloat the index with duplicate content.

## Requirements

1. The following file patterns must be excluded from `walk_repo()` output: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` (dependency lock files).
2. Files matching `*.snap` must be excluded (Vitest/Jest snapshot files).
3. Files matching `*.excalidraw` must be excluded (JSON diagram files with no code semantics).
4. The exclusion must be pattern-based (filename or extension), applied in `walk_repo()` before files are yielded.
5. `package.json` must not be excluded — it contains meaningful dependency, script, and project metadata.
6. Other `.json` files must not be blanket-excluded — only the specific generated patterns listed above.
7. A test must assert that `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `*.snap`, and `*.excalidraw` are excluded, and that `package.json` is not excluded.

## Scope

**Problem statement:** Lock files and test snapshots are valid text files that pass binary detection but are semantically useless for code search. They contribute hundreds to thousands of noise chunks per project.

**In scope:**

- `indexer.py` `walk_repo()`: add `HARDCODED_EXCLUDE_FILENAMES` (exact filename matches) and `HARDCODED_EXCLUDE_EXTENSIONS` (extension matches) for the patterns above
- Tests: exclusion of lock files, snapshots, excalidraw; non-exclusion of `package.json`

**Out of scope:**

- Excluding all generated files generically — only the high-signal, low-value patterns identified above
- Postman collection exclusion — these are `.json` files; blanket-excluding `*.postman_collection.json` is fragile; users can `.aiignore` these
- Binary file exclusion — separate change `12c7n-bug binary-files-indexed-as-text`

## Acceptance Criteria

- AC-1: `package-lock.json` is not yielded by `walk_repo()`.
- AC-2: `yarn.lock` is not yielded by `walk_repo()`.
- AC-3: `pnpm-lock.yaml` is not yielded by `walk_repo()`.
- AC-4: Files matching `*.snap` are not yielded by `walk_repo()`.
- AC-5: Files matching `*.excalidraw` are not yielded by `walk_repo()`.
- AC-6: `package.json` is yielded by `walk_repo()` (not excluded).
- AC-7: Other `.json` files are yielded normally.
- AC-8: Tests assert AC-1 through AC-7.
- AC-9: All pre-existing framework tests continue to pass.

## Tasks

- [ ] Add `HARDCODED_EXCLUDE_FILENAMES` frozenset to `indexer.py` (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`)
- [ ] Add `.snap` and `.excalidraw` to the extension exclusion set in `walk_repo()`
- [ ] Apply both checks in `walk_repo()` before yielding files
- [ ] Add tests to `test_indexer.py` covering lock file, snapshot, and excalidraw exclusion

## Agent Execution Graph

| Workstream   | Owner       | Depends On | Notes                                     |
| ------------ | ----------- | ---------- | ----------------------------------------- |
| indexer-excl | Engineering | —          | Filename + extension exclusion in `walk_repo()` |
| tests        | Engineering | indexer-excl | Exclusion + non-exclusion test cases    |

## Serialization Points

- `walk_repo()` in `indexer.py` is the single-author surface; can run in parallel with `12c7n-bug binary-files-indexed-as-text` if care is taken not to conflict on the same lines.

## Affected Architecture Docs

N/A — implementation confined to `walk_repo()` exclusion logic. No boundary or data-flow impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Lock file exclusion — highest noise contributor |
| AC-2 | required | Lock file exclusion |
| AC-3 | required | Lock file exclusion |
| AC-4 | required | Snapshot exclusion |
| AC-5 | required | Excalidraw diagram exclusion |
| AC-6 | required | Must not over-exclude — package.json is signal |
| AC-7 | required | Must not over-exclude JSON broadly |
| AC-8 | required | Test coverage for the fix |
| AC-9 | required | Non-regression gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Other generated JSON files not on the list continue to be indexed | Users can .aiignore specific paths; blanket JSON exclusion would be worse |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
