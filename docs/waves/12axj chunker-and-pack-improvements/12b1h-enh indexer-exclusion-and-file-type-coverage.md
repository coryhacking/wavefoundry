# Indexer Exclusion and File-Type Coverage

Change ID: `12b1h-enh indexer-exclusion-and-file-type-coverage`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-01
Wave: `12axj chunker-and-pack-improvements`

## Rationale

The indexer's `HARDCODED_EXCLUDE_DIRS` is a manually-maintained list of known tool dirs (`.git`, `.hg`, etc.) that grows stale as new tools appear (`.idea`, `.vscode`, `.claude`, `.cursor`, `.codex`, `.fleet`, etc.). A blanket rule — exclude all dirs whose names start with `.` except `.wavefoundry` — is future-proof and eliminates the whack-a-mole list.

Additionally, `.txt` files and extensionless files like `README`, `LICENSE`, `CHANGELOG` are never indexed despite containing useful documentation. And a few common code formats (`.xml`, `.graphql`, `.proto`, `.sql`) are missing from `SOURCE_CODE_EXTENSIONS`. `.env` files risk indexing secrets and should be explicitly excluded.

## Requirements

1. All directories whose names begin with `.` must be excluded from the walk, except `.wavefoundry` (and its subdirectories).
2. The existing explicit dot-dir entries in `HARDCODED_EXCLUDE_DIRS` (`.git`, `.hg`, `.svn`, `.next`, `.nuxt`) may be retained for clarity but the blanket rule is the enforcement mechanism.
3. `.txt` files must be walked and treated as documentation (docs index, not code index).
4. Extensionless files named `README`, `LICENSE`, `CHANGELOG`, `CONTRIBUTING`, `NOTICE` must be walked and treated as documentation.
5. `.xml`, `.graphql`, `.gql`, `.proto`, `.sql` must be added to `SOURCE_CODE_EXTENSIONS` for code indexing.
6. `.env` and `.env.*` patterns must be excluded from the walk entirely (secrets risk).
7. All existing tests must continue to pass; new tests must cover the blanket dot-dir rule, `.txt` inclusion, extensionless README inclusion, and `.env` exclusion.

## Scope

**Problem statement:** The indexer misses useful doc files (`.txt`, `README`) and some code formats, and requires manual maintenance to exclude new tool dot-dirs.

**In scope:**

- `indexer.py`: blanket dot-dir exclusion in `walk_repo`; add `.txt`, extensionless allowlist to walker; add `.xml`, `.graphql`, `.gql`, `.proto`, `.sql` to `SOURCE_CODE_EXTENSIONS`; add `.env` pattern to exclusion
- `chunker.py`: ensure `.txt` files are handled (plain-text passthrough → doc chunk); extensionless allowlist files treated as markdown
- `test_indexer.py`: tests for dot-dir blanket rule, `.txt` inclusion, extensionless README inclusion, `.env` exclusion
- `test_chunker.py`: tests for `.txt` passthrough and extensionless README chunking

**Out of scope:**

- `.github/workflows` special-casing (covered by blanket dot-dir rule; users can override via `.aiignore`)
- Directory-level `.aiignore` scoping
- Language-specific chunking for XML/GraphQL/Proto/SQL (plain passthrough for now)

## Acceptance Criteria

- AC-1: A directory named `.idea` at any depth is excluded from the walk
- AC-2: A directory named `.vscode` at any depth is excluded from the walk
- AC-3: `.wavefoundry/` and its children are still walked
- AC-4: A file named `README` (no extension) at repo root is included in the walk and produces a doc chunk
- AC-5: A `.txt` file is included in the walk and produces a doc chunk
- AC-6: A `.env` file is excluded from the walk
- AC-7: `.graphql`, `.proto`, `.sql` files appear in `SOURCE_CODE_EXTENSIONS`
- AC-8: All existing tests pass

## Tasks

- [ ] Update `walk_repo` in `indexer.py`: replace the per-name dot-dir check with a blanket `name.startswith(".")` guard that allowlists `.wavefoundry`
- [ ] Add `.env` exclusion to `walk_repo` (filename pattern match before extension check)
- [ ] Add `.txt` to `SOURCE_CODE_EXTENSIONS` as a docs-eligible extension (or handle via separate docs extension set)
- [ ] Add extensionless filename allowlist (`README`, `LICENSE`, `CHANGELOG`, `CONTRIBUTING`, `NOTICE`) to walker so they are not skipped by binary-extension check
- [ ] Add `.xml`, `.graphql`, `.gql`, `.proto`, `.sql` to `SOURCE_CODE_EXTENSIONS`
- [ ] Ensure `chunker.py` `chunk_file` handles `.txt` (plain text → single doc chunk) and extensionless allowlist files (treat as markdown)
- [ ] Add tests to `test_indexer.py`: dot-dir blanket exclusion, `.wavefoundry` still included, `.txt` included, `README` included, `.env` excluded
- [ ] Add tests to `test_chunker.py`: `.txt` produces doc chunk, `README` produces doc chunk

## Agent Execution Graph

| Workstream       | Owner       | Depends On | Notes |
| ---------------- | ----------- | ---------- | ----- |
| indexer-walker   | implementer | —          | `indexer.py` walk changes + tests |
| chunker-passthru | implementer | —          | `chunker.py` `.txt`/README handling + tests |

## Serialization Points

- `indexer.py` and `chunker.py` are independent; both workstreams can run in parallel.

## Affected Architecture Docs

N/A — confined to `indexer.py` walk filter and `chunker.py` dispatch; no boundary/flow/interface change visible to callers.

## AC Priority

| AC   | Priority    | Rationale |
| ---- | ----------- | --------- |
| AC-1 | required    | Core goal: blanket dot-dir exclusion |
| AC-2 | required    | Core goal: blanket dot-dir exclusion |
| AC-3 | required    | `.wavefoundry` must remain indexed |
| AC-4 | required    | README files are primary project docs |
| AC-5 | important   | `.txt` changelogs and notes are useful |
| AC-6 | required    | Secrets risk |
| AC-7 | nice-to-have | Fills coverage gaps; no correctness risk |
| AC-8 | required    | No regressions |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-01 | Implemented blanket dot-dir exclusion, `.env` exclusion, extensionless allowlist, `.txt` routing, new extensions; 668 tests pass | `indexer.py`, `chunker.py`, `test_indexer.py`, `test_chunker.py` |
| 2026-05-01 | Round-1 review fixes: `_DOT_DIR_ALLOWLIST_PREFIX` trailing slash bug; stale comment; coupling notes; section prepend in `chunk_plain_text`; nested dot-dir test; AC-7 assertion | all four review lanes approved |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-01 | Blanket `.`-prefix dir exclusion with `.wavefoundry` allowlist | Eliminates whack-a-mole tool-dir list; `.wavefoundry` is the only first-party dot-dir we own | Per-name blocklist (grows stale); per-name allowlist (more restrictive than needed) |
| 2026-05-01 | Exclude `.env` at walker level, not in `BINARY_EXTENSIONS` | Secrets should never reach the chunker; binary-ext check is for format, not sensitivity | Add to `.aiignore` template (user-opt-in, weaker guarantee) |
| 2026-05-01 | Treat `.txt` and extensionless allowlist files as docs, not code | These are plain-text documentation; adding them to `SOURCE_CODE_EXTENSIONS` would cause them to appear in the code semantic index where they don't belong | Add to SOURCE_CODE_EXTENSIONS (wrong index) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Blanket dot-dir rule excludes a dot-dir someone legitimately wants indexed | `.aiignore` negation patterns or `--no-ignore-files` flag already available; document in walker comments |
| `.env.example` (not a secret) is excluded alongside `.env` | Acceptable trade-off; `.env.example` can be re-included via `.aiignore` negation if needed |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
