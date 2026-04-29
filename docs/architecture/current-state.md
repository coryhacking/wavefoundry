# Architecture — Current State

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Runtime Topology

**Development-time topology (current state):**

```
Developer/agent
  │
  ├── python3 .wavefoundry/framework/scripts/lifecycle_id.py  →  docs/workflow-config.json (read)
  ├── python3 .wavefoundry/framework/scripts/docs_lint.py      →  docs/ tree (read)
  ├── python3 .wavefoundry/framework/scripts/docs_gardener.py  →  docs/ tree (read/write metadata)
  ├── python3 .wavefoundry/framework/scripts/build_pack.py     →  .wavefoundry/framework/VERSION (write), wavefoundry-framework-*.zip (write)
  └── python3 .wavefoundry/framework/scripts/render_platform_surfaces.py  →  .claude/, .cursor/, .github/hooks/ (write)
```

**Planned runtime topology (future MCP server, not yet implemented):**

```
MCP client (Claude Code, Cursor, Copilot, etc.)
  │
  └── stdio or socket
        └── wavefoundry MCP server (src/wavefoundry/server.py)
              ├── wave.* tools    →  target repository docs/ (read; mutation tools future)
              ├── code.search     →  target repository files (read)
              └── code.read       →  target repository files (read)
```

## Current Risk Areas

| Risk | Details | Mitigation |
|------|---------|-----------|
| Framework dir accidentally deleted | `.wavefoundry/framework/` is tracked in git; restore with `git checkout HEAD -- .wavefoundry/framework` | Covered by normal git recovery |
| No CI/CD | No automated test runs on push | Framework tests run manually: `python3 .wavefoundry/framework/scripts/run_tests.py` |
| MCP server not yet designed | Transport, allowed-roots config format, tool contracts all TBD | Keep read-only tools first; defer mutation tools |

## Verification Sources

This doc was verified from direct inspection of: `.wavefoundry/framework/scripts/`, `.wavefoundry/framework/seeds/`, `.venv/pyvenv.cfg`, repository root file listing, `docs/repo-index.md`.
