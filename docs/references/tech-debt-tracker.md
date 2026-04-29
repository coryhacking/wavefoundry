# Tech Debt Tracker

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Active Debt Items

| ID | Item | Severity | Effort | Notes |
|----|------|---------|--------|-------|
| DEBT-01 | No CI/CD pipeline | Medium | Medium | Tests run manually; risk of undetected regressions |
| DEBT-02 | No `pyproject.toml` | Low | Low | Needed for MCP package; factor 02 (dependencies) becomes applicable |
| DEBT-03 | No import linter | Low | Low | Layering rules enforced only by code review; no automated check |
| DEBT-04 | `docs/specs/mcp-tool-surface.md` missing | Medium | Large | MCP tool contracts not formally specified; needed before MCP server work begins |
| DEBT-05 | `code_patterns` not cataloged | Low | Low | Insufficient history now; revisit when MCP src/ has ≥3 source files |

## Retired Items

*(None yet)*
