# Quality Score

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Current Quality Posture

**Overall:** Early-stage framework tooling with solid validation infrastructure. No production code yet.

| Dimension | Score | Notes |
|-----------|-------|-------|
| Test coverage | Medium | Unit tests for docs_lint and build_pack; no CI; manual execution |
| Documentation | High | Comprehensive seed prompts; self-hosted Wave Framework surface installed |
| Correctness | High | Framework scripts are well-defined; docs_lint enforces correctness gates |
| Maintainability | High | Clean separation: seeds / scripts / docs |
| Security | High | Local-only; no secrets; guard mechanism for seed protection |

## Quality Risks

| Risk | Severity | Notes |
|------|---------|-------|
| No CI/CD | Medium | Tests not automatically run on every change; human must run manually |
| Insufficient implementation history for pattern catalog | Low | `code_patterns` has `insufficient_history`; revisit when MCP src/ added |
| MCP tool contracts not yet specified | Medium | `docs/specs/mcp-tool-surface.md` missing; see `docs/missing-docs.md` |

## Review-Sensitive Surfaces

- `framework/seeds/` — any seed edit may affect all target repositories; requires architecture + docs-contract review
- `docs_lint.py` validation logic — correctness failures silently pass bad docs; requires code + QA review
- `build_pack.py` VERSION stamping — incorrect stamp corrupts version guard; requires code + release review
- Future MCP tool contracts — breaking changes affect all clients; require architecture + docs-contract review

## Quality Improvement Plan

1. Add CI/CD (GitHub Actions) after first delivery wave
2. Add `pyproject.toml` with test infrastructure declaration
3. Populate `code_patterns` once MCP implementation sources exist
4. Spec MCP tool surface in `docs/specs/mcp-tool-surface.md`
