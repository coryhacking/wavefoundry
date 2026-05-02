# Prepare Wave

Owner: Engineering
Status: active
Last verified: 2026-05-01

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

## Single-Active-Wave Rule

Only one wave may be `active` at a time. `wave_prepare` enforces this: when another wave is already `active`, it returns an `another_wave_active` error diagnostic with `wave_pause` as the recovery tool. To context-switch between waves:

1. `wave_pause(wave_id='<current-active>', mode='create')` — transitions the current active wave from `active` to `paused` and records a session-handoff entry.
2. `wave_prepare(wave_id='<target>', mode='create')` — promotes the target wave to `active`. Works for `planned → active` (normal prepare) and `paused → active` (resume).

**Resume semantics:** a paused wave is resumed by re-running `wave_prepare` on it. The single-active-wave guard still applies — resume is blocked if any other wave is currently `active`.

The `wave_current` tool returns `data.waves[]` with all non-closed waves: active first (0 or 1), then planned, then paused. Each entry's `next_action` tells you what to do: `implement_wave` (active), `prepare_wave` (planned), or `resume_wave` (paused). The `resume_wave` label is a hint; the underlying transition is still `wave_prepare` on the paused wave.

## Wavefoundry-Specific Review Lane Selection

| Change Type | Required Lanes |
|-------------|--------------|
| Framework seed edit | architecture-reviewer, docs-contract-reviewer |
| Framework script change | code-reviewer, qa-reviewer |
| MCP tool contract | architecture-reviewer, docs-contract-reviewer |
| Packaging / build | code-reviewer, release-reviewer |
| Bug fix (any) | qa-reviewer (required by policy) |
