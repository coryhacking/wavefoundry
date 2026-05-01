# Prepare Wave

Owner: Engineering
Status: active
Last verified: 2026-04-30

Shortcut: **`Prepare wave`** | Alias: **`Ready wave`**

## Purpose

Confirm wave readiness before implementation begins. The stage gate: implementation must not start until **Prepare wave** passes cleanly as the immediately preceding lifecycle step.

## Steps

1. Validate that every admitted change doc already lives in `docs/waves/<wave-id>/`. If an admitted doc is still staged in `docs/plans/`, repair the placement by moving it into the wave folder; if duplicate staged and wave copies exist, stop and resolve the conflict explicitly.
2. Confirm each change doc is complete: Rationale, Requirements, Scope, Acceptance Criteria, Affected architecture docs.
3. Select required review lanes for each admitted change (see `docs/contributing/agent-team-workflow.md`).
4. Confirm `qa-reviewer` is included for any bug fix (`review_policies.require_qa_reviewer_for_bug_fixes: true`).
5. **AC priority check:** categorize each admitted change's ACs as required / important / nice-to-have / not-this-scope; record in `## AC priority` on the change doc; interrogate required and important ACs until each classification is explicitly justified.
6. Record product-owner acknowledgment for product-impacting waves (feature changes shifting product behavior/UX/acceptance).
7. Update wave record status to `Status: active`.

## Readiness Verdict

Record a readiness verdict in the wave record `## Review checkpoints` (e.g., `Prepare wave — readiness verdict`). The wave is ready when:
- All admitted change docs are complete and wave-owned
- Any admitted-doc placement drift was repaired or explicitly resolved
- All required review lanes are confirmed
- AC priority is recorded on each change doc
- Product-owner acknowledgment is recorded (when applicable)

## Wavefoundry-Specific Review Lane Selection

| Change Type | Required Lanes |
|-------------|--------------|
| Framework seed edit | architecture-reviewer, docs-contract-reviewer |
| Framework script change | code-reviewer, qa-reviewer |
| MCP tool contract | architecture-reviewer, docs-contract-reviewer |
| Packaging / build | code-reviewer, release-reviewer |
| Bug fix (any) | qa-reviewer (required by policy) |
