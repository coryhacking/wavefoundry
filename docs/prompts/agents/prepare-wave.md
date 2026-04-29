# Agent Body — Prepare Wave

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Context

You are running **Prepare wave** on Wavefoundry. This is the stage gate for implementation.

## Steps

1. Move all admitted change docs from `docs/plans/` into `docs/waves/<wave-id>/`.
2. Verify each change doc has: Rationale, Requirements, Scope, Acceptance Criteria, Affected architecture docs.
3. Select review lanes (see `docs/contributing/agent-team-workflow.md`).
4. Confirm `qa-reviewer` for any bug fix.
5. Record `## AC priority` on each change doc.
6. Record readiness verdict in wave record `## Review checkpoints`.
7. Update wave record `Status: active`.

## Review Lane Matrix for Wavefoundry

| Change Type | Required Lanes |
|-------------|--------------|
| Framework seed edit | architecture-reviewer, docs-contract-reviewer |
| Framework script | code-reviewer, qa-reviewer |
| MCP tool contract | architecture-reviewer, docs-contract-reviewer |
| Packaging / build | code-reviewer, release-reviewer |
| Bug fix | qa-reviewer (required by policy) |

## Product-Owner Acknowledgment

Wavefoundry has no external product owner. Record `product-owner: N/A — internal framework tooling` for all changes unless the change affects published API contracts or distribution format (in which case the engineering team lead acts as product-owner).
