# SQL Extension Alias Detection

Change ID: `12jv9-enh sql-extension-alias-detection`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

SQL support currently keys off `.sql`, but many repos use other common SQL-oriented suffixes for dialect-specific scripts. Broadening the extension detection keeps structural chunking, indexing, and symbol navigation available across more projects without changing the SQL parser behavior itself.

## Requirements

1. Common SQL script aliases should route through the same SQL chunking / indexing path as `.sql`.
2. The alias list should be broad enough to help heterogeneous repos, but still finite and explicit.
3. Existing `.sql` behavior must remain unchanged.
4. Tests should cover the new aliases in indexer, chunker, and server routing surfaces.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

**Out of scope:**

- Changing the SQL parser or chunking strategy
- Altering the broader language category model

## Acceptance Criteria

- SQL aliases map to the canonical `sql` language everywhere chunking and navigation care about file extensions.
- The existing `.sql` path still works.
- Tests confirm at least one alias routes through the SQL chunker and indexing maps.

## Tasks

- Add a finite set of common SQL aliases to the extension maps
- Update tests to assert alias routing

## AC Priority

| AC | Priority | Rationale |
| -- | -- | -- |
| AC-1 | required | Alias routing is the actual capability change |
| AC-2 | required | Existing SQL support must not regress |
| AC-3 | required | Regression coverage keeps the alias list honest |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Over-broad aliases pull in non-SQL files | Keep the alias list explicit and conservative |
| Aliases drift across indexer/chunker/server maps | Add tests that exercise all routing surfaces |
