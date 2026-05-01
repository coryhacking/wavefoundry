# Performance Budget

Owner: Engineering
Status: active
Last verified: 2026-04-30

## Current Performance Expectations

| Operation | Expected Duration | Notes |
|-----------|-----------------|-------|
| `.wavefoundry/bin/docs-lint` on this repo | < 5 seconds | Validates docs/ tree; should be fast |
| `.wavefoundry/bin/docs-gardener` on this repo | < 5 seconds | Metadata refresh; local file I/O |
| `lifecycle_id.py` | < 1 second | Pure computation + config read |
| `build_pack.py` | < 30 seconds | Zip creation; depends on framework/ tree size |
| `render_platform_surfaces.py` | < 5 seconds | File generation; small number of hook files |
| Framework script test suite | < 30 seconds | Unit tests on fixture files |

## Performance Hotspots

None currently; all operations are local file I/O with small data volumes.

## Future: MCP Server

| Operation | Target | Notes |
|-----------|--------|-------|
| `code.search` exact search | < 2 seconds for repos ≤ 100k files | TBD based on index implementation |
| `wave.current` | < 1 second | Read a few docs/ files |
| `wave.validate` | < 5 seconds | Validate docs/ tree |

The local SQLite index (future) should make exact search faster than full-tree scanning. Index build time is a one-time cost; keep it under 60 seconds for typical target repos.
