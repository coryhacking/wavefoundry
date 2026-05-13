# MCP And Upgrade Guidance Clarity

Change ID: `12jnk-doc upgrade-and-mcp-guidance-clarity`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The MCP tool surface has become richer, especially around code navigation, search orientation, and upgrade recovery. The operator-facing docs need a clearer "which tool do I use when?" story, and the framework upgrade prompt needs to make the post-upgrade expectations explicit so framework updates are applied, restarted, and reindexed in the correct order.

## Requirements

1. Operator-facing MCP docs must clearly distinguish semantic discovery, exact lookup, and symbol navigation.
2. Canonical seed prompts must carry the same guidance so regenerated surfaces do not drift back.
3. The upgrade prompt must explain the practical framework-update flow clearly, including restart and index update expectations after an upgrade.
4. Rendered docs and canonical seeds must stay aligned.
5. Verification must pass.

## Scope

**In scope:**

- `AGENTS.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/prompts/agents/code-insight-agent.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/211-code-insight-agent.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`

**Out of scope:**

- MCP server behavior changes
- Upgrade script or packaging logic changes

## Acceptance Criteria

- AC-1: MCP docs include a clear chooser for `code_search`, `code_definition`, `code_references`, `code_keyword_search`, and `code_read`.
- AC-2: The CIA seed and related bootstrap guidance mirror the same tool-selection guidance.
- AC-3: The upgrade prompt clearly explains how framework updates are applied and what operators must restart or rebuild afterward.
- AC-4: Rendered docs and canonical seeds are aligned.
- AC-5: Verification passes.

## Tasks

- Add or refine tool-selection guidance in rendered docs
- Update canonical seed prompts to match
- Clarify upgrade flow in rendered prompt and canonical upgrade seed
- Run docs lint

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Operators and agents need a clear tool chooser |
| AC-2 | required | Seed/rendered parity must hold across regenerations |
| AC-3 | required | Upgrade behavior needs a clear operator mental model |
| AC-4 | required | Drift between seed and rendered docs would regress quickly |
| AC-5 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-12 | Change doc created for MCP tool-selection clarity and framework upgrade prompt clarity. | `AGENTS.md`; `docs/specs/mcp-tool-surface.md`; `docs/prompts/upgrade-wavefoundry.prompt.md`; `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` |
| 2026-05-12 | Clarified MCP tool-selection guidance in rendered docs and canonical seeds, and rewrote the upgrade guidance so the framework-update flow explicitly covers zip adoption, reconciliation, MCP restart, and index update vs rebuild expectations. | `AGENTS.md`; `docs/specs/mcp-tool-surface.md`; `docs/prompts/agents/code-insight-agent.prompt.md`; `docs/prompts/upgrade-wavefoundry.prompt.md`; `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`; `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`; `.wavefoundry/framework/seeds/211-code-insight-agent.prompt.md`; `./.wavefoundry/bin/docs-lint` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
