# Prepare Wave

Owner: Engineering
Status: active
Last verified: 2026-05-23

Shortcut: **`Prepare wave`** | Alias: **`Ready wave`**

## Purpose

Confirm wave readiness before implementation begins. The stage gate: implementation must not start until **Prepare wave** passes cleanly as the immediately preceding lifecycle step.

## Steps

1. Validate that every admitted change doc already lives in `docs/waves/<wave-id>/`. If an admitted doc is still staged in `docs/plans/`, repair the placement by moving it into the wave folder; if duplicate staged and wave copies exist, stop and resolve the conflict explicitly.
2. Confirm each change doc is complete: Rationale, Requirements, Scope, Acceptance Criteria, Affected architecture docs.
3. Select required review lanes for each admitted change (see `docs/contributing/agent-team-workflow.md`).
4. Confirm `qa-reviewer` is included for any bug fix (`review_policies.require_qa_reviewer_for_bug_fixes: true`).
5. When `wave_council_policy.enabled` is true, run the Wave Council readiness pass: fixed seats plus one rotating domain seat review the admitted change set in isolation; `council-moderator` synthesizes the result; record `wave-council-readiness` in `## Review Evidence` and the narrative verdict in `## Review checkpoints`. **`wave_prepare` signals this step with `status: "ready_for_council_review"` — run the review immediately when you see that status, then call `wave_prepare(mode='create')` again to complete prepare.**
6. **AC priority check:** categorize each admitted change's ACs as required / important / nice-to-have / not-this-scope; record in `## AC priority` on the change doc; interrogate required and important ACs until each classification is explicitly justified.
7. Record product-owner acknowledgment for product-impacting waves (feature changes shifting product behavior/UX/acceptance).
8. Update wave record status to `Status: active`.

## Readiness Verdict

Record a readiness verdict in the wave record `## Review checkpoints` (e.g., `Prepare wave — readiness verdict`). The wave is ready when:
- All admitted change docs are complete and wave-owned
- Any admitted-doc placement drift was repaired or explicitly resolved
- All required review lanes are confirmed
- `wave-council-readiness` is recorded when `wave_council_policy.enabled`
- AC priority is recorded on each change doc
- Product-owner acknowledgment is recorded (when applicable)

A clean readiness verdict confirms the wave is **admissible**. It does not replace the **pre-implementation review gate**, which is the mandatory first phase of `Implement wave`. The lifecycle sequence is: `Prepare wave` (readiness) → **pre-implementation review gate** (first phase of `Implement wave`) → first code edit.

## Single-Active-Wave Rule

Only one wave may be `active` at a time. `wave_prepare` enforces this: when another wave is already `active`, it returns an `another_wave_active` error diagnostic with `wave_pause` as the recovery tool. To context-switch between waves:

1. `wave_pause(wave_id='<current-active>', mode='create')` — transitions the current active wave from `active` to `paused` and records a session-handoff entry.
2. `wave_prepare(wave_id='<target>', mode='create')` — promotes the target wave to `active`. Works for `planned → active` (normal prepare) and `paused → active` (resume).

**Resume semantics:** a paused wave is resumed by re-running `wave_prepare` on it. The single-active-wave guard still applies — resume is blocked if any other wave is currently `active`.

The `wave_current` tool returns `data.waves[]` with all non-closed waves: active first (0 or 1), then planned, then paused. Each entry's `next_action` tells you what to do: `implement_wave` (active), `prepare_wave` (planned), or `resume_wave` (paused). The `resume_wave` label is a hint; the underlying transition is still `wave_prepare` on the paused wave.

## Wavefoundry-Specific Review Lane Selection

Assign lanes at Prepare time and record them in the wave record `## Participants` section. Two tiers:

**Tier 1 — assign whenever the change type matches (most waves will have all three):**

| Trigger | Lane |
|---------|------|
| Any change to `.wavefoundry/framework/scripts/*.py` | `code-reviewer` |
| Any change doc with an AC priority table | `qa-reviewer` |
| MCP tool contract, index routing, or module boundary change | `architecture-reviewer` |

**Tier 2 — assign only when specifically applicable:**

| Trigger | Lane |
|---------|------|
| Seed edit that defines a behavioral contract agents rely on | `docs-contract-reviewer` |
| Packaging, build, or VERSION change | `release-reviewer` |
| New or modified chunker/indexer hot paths, per-file loops, or regex scan patterns | `performance-reviewer` |
| New file-access tools, path argument from MCP caller, `re.compile` with user input, or write-path constraint on a read-only tool | `security-reviewer` |

**Policy:** `qa-reviewer` is always required for bug fixes (`review_policies.require_qa_reviewer_for_bug_fixes: true`).

When Wave Council is enabled, the default fixed seats are `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, and `reality-checker`. The fifth seat rotates from the admitted wave evidence: prefer `docs-contract-reviewer` for seed/prompt/contract work, `performance-reviewer` for indexing/search/hot-path work, `release-reviewer` for packaging/distribution work, or an applicable persona when operator-facing acceptance is central.

**Do not assign** legacy factor lanes (`factor-12`, `factor-13`) — these have no governing prompt body and their review obligations are covered by the lanes above.
