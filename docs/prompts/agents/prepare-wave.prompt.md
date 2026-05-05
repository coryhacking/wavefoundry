# Agent Body — Prepare Wave

Owner: Engineering
Status: active
Last verified: 2026-05-04

## Context

You are running **Prepare wave** on Wavefoundry. This is the stage gate for implementation.

## Steps

1. Validate that all admitted change docs already live in `docs/waves/<wave-id>/`; repair any staged-only doc by moving it there, and stop on duplicate staged + wave copies.
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

## CIA Orientation

During scope assessment (step 2), use the CIA to answer "what does X currently do?" and "which files are affected?" without launching full file reads:

```
code_search(topic, kind="code-summary", limit=5)   # which modules are in scope?
code_dependencies(path)                             # what does the target file import/export?
code_ask("what are the entry points for X?")        # cross-cutting questions
```

This speeds up the Affected Architecture Docs check and helps select accurate review lanes. If MCP is not available, use `grep -n "^import\|^from" <path>` for dependencies and `grep -r "keyword" .` for module discovery.

## Product-Owner Acknowledgment

Wavefoundry has no external product owner. Record `product-owner: N/A — internal framework tooling` for all changes unless the change affects published API contracts or distribution format (in which case the engineering team lead acts as product-owner).
