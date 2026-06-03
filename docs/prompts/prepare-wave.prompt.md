# Prepare Wave

Owner: Engineering
Status: active
Last verified: 2026-06-03

Shortcut: **`Prepare wave`** | Alias: **`Ready wave`**

## Purpose

Confirm wave readiness before implementation begins. The stage gate: implementation must not start until **Prepare wave** passes cleanly as the immediately preceding lifecycle step.

## Steps

1. Validate that every admitted change doc already lives in `docs/waves/<wave-id>/`. If an admitted doc is still staged in `docs/plans/`, repair the placement by moving it into the wave folder; if duplicate staged and wave copies exist, stop and resolve the conflict explicitly.
2. Confirm each change doc is complete: Rationale, Requirements, Scope, Acceptance Criteria, Affected architecture docs.
3. Select required review lanes for each admitted change (see `docs/contributing/agent-team-workflow.md`).
4. Confirm `qa-reviewer` is included for any bug fix (`review_policies.require_qa_reviewer_for_bug_fixes: true`).
5. When `wave_review.enabled` is true, run the Wave Council readiness pass in two phases: first, the `wave-council` declares a **primer depth tier** (`lightweight` / `standard` / `full`) based on trust boundaries touched, files in scope, and change type — this sets how many stances and `primer_questions` Phase 1 produces; (1) `red-team` runs the adversarial primer (`council-adversarial-primer` mode) first in isolation at the declared depth — strongest challenge, best alternative, and `primer_questions`; (2) fixed seats each receive the standard briefing plus the primer output and must address `strongest_challenge` and `primer_questions` before producing their own findings; a rotating fifth seat finds the strongest alternative path the wave did not take; `wave-council` synthesizes all outputs; record `wave-council-readiness` in `## Review Evidence` and the narrative verdict in `## Review checkpoints`. The recorded verdict must be a structured `prepare-council` line with `moderator`, `primer-depth`, `seats`, `rotating-seat`, `strongest-challenge`, and `strongest-alternative` fields. **`wave_prepare` signals this step with `status: "ready_for_council_review"` — run the review immediately when you see that status, then call `wave_prepare(mode='create')` again to complete prepare.**
6. **AC priority check:** categorize each admitted change's ACs as required / important / nice-to-have / not-this-scope; record in `## AC priority` on the change doc; interrogate required and important ACs until each classification is explicitly justified. ACs admitted with the `[~]` marker (intentionally not met from the outset) are unusual but accepted — they must already carry an inline status note explaining the deferral, and the `## AC priority` row must still record their priority. See `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` *"AC and task checkbox states — the `[~]` marker"* for the canonical convention. Note the close-time hard gate: silent `[ ]` items block `wave_close`, so prepare-time AC tracking habits matter.
7. Record product-owner acknowledgment for product-impacting waves (feature changes shifting product behavior/UX/acceptance).
8. Update wave record status to `Status: active`.

## Readiness Verdict

Record a readiness verdict in the wave record `## Review checkpoints` (e.g., `Prepare wave — readiness verdict`). The wave is ready when:
- All admitted change docs are complete and wave-owned
- Any admitted-doc placement drift was repaired or explicitly resolved
- All required review lanes are confirmed
- `wave-council-readiness` is recorded when `wave_review.enabled`
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

When Wave Council is enabled, `red-team` always runs first as the adversarial primer (Phase 1) before any other seat. The fixed Phase 2 seats are `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, and `reality-checker` — each receives the red-team primer and must engage with it. The fifth seat rotates from the admitted wave evidence: prefer `docs-contract-reviewer` for seed/prompt/contract work, `performance-reviewer` for indexing/search/hot-path work, `release-reviewer` for packaging/distribution work, or an applicable persona when operator-facing acceptance is central.

**Do not assign** legacy factor lanes (`factor-12`, `factor-13`) — these have no governing prompt body and their review obligations are covered by the lanes above.
