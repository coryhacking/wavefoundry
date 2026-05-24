# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-21

wave-id: `12sg7 implementation-governance-upgrades`
Title: Implementation Governance Upgrades

## Changes

Change ID: `12sf9-enh senior-builder-roles`
Previous Change Status: `planned`
Change Status: `complete`

Change ID: `12sfb-enh mcp-code-navigation-defaults`
Previous Change Status: `planned`
Change Status: `complete`

Change ID: `12sfj-enh ac-task-linked-tracking`
Previous Change Status: `planned`
Change Status: `complete`

Change ID: `12sg4-enh pre-implementation-review-gate`
Previous Change Status: `planned`
Change Status: `complete`

Change ID: `12s5r-enh dashboard-dialog-wider-ac-id-column`
Previous Change Status: `planned`
Change Status: `complete`

Change ID: `12sh5-enh formal-red-team-role`
Previous Change Status: `planned`
Change Status: `complete`

## Objective

Upgrade Wavefoundry’s implementation governance model so waves start with stronger implementation-role routing, MCP-first code navigation defaults, live AC/task progress tracking, a formal pre-implementation review gate, and the dashboard changes needed to support that workflow clearly.

## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| planner | planning | all admitted changes — implementation workflow, role routing, and dashboard/governance contracts |
| wave-coordinator | coordination | all admitted changes — admission, serialization, readiness, and later implementation/review routing |
| implementer | implement | all admitted changes — framework seeds, lifecycle scripts, dashboard/parser/lint behavior, and Wavefoundry-local docs updates |
| architecture-reviewer | review | `12sf9`, `12sfb`, `12sg4`, `12sh5` — builder-lane routing, challenger-role boundaries, MCP gate-family contract, and pre-implementation lifecycle control flow |
| code-reviewer | review | `12sf9`, `12sfj`, `12sg4`, `12s5r` — framework scripts, dashboard/parser/lint behavior, lifecycle mutation paths, and dashboard rendering changes |
| qa-reviewer | review | all admitted changes — AC/task tracking semantics, dashboard visibility, and readiness/implementation workflow regression coverage |
| docs-contract-reviewer | review | `12sf9`, `12sfb`, `12sfj`, `12sg4`, `12sh5` — seeded role docs, prompt surfaces, and operator-facing workflow contracts |
| security-reviewer | review | `12sf9`, `12sg4`, `12sh5` — gate-policy enforcement, protected-surface posture, lifecycle cleanup semantics, and challenger-lane boundary with security review |
| council-moderator | council | full admitted set — Wave Council readiness and delivery synthesis |
| reality-checker | council | full admitted set — ceremony, operator burden, and practicality challenge lane |
| red-team | council | full admitted set — misuse, policy-bypass, and stale-state challenge lane |

## Dependencies

- No external wave dependency identified.
- Must preserve compatibility with the current wave lifecycle contract, especially `Prepare wave`, `Implement wave`, `Review wave`, and Wave Council readiness/delivery behavior.
- Implementation order for this wave is canonical-seed-first: update the framework seed prompts and shared seed-side contracts first so the behavior is relevant to all seeded projects, then review the resulting seed contract, then update Wavefoundry-local specs, generated surfaces, and local operating docs to match.
- Dashboard/parser/lint behavior must stay aligned with the forward document contract chosen for AC/task tracking.
- `12s5r-enh dashboard-dialog-wider-ac-id-column` is a narrow dashboard presentation slice but now depends on the same dashboard/parser contract decisions as the AC/task tracking change.
- `12sh5-enh formal-red-team-role` depends on the same specialist taxonomy, council wording, and routing surfaces already touched by `12sf9` and `12sg4`.

## Current Assumptions

- These six changes belong in one wave because they all govern how implementation is prepared, routed, tracked, and reviewed.
- The dashboard dialog-width change belongs in this same wave because it affects the dashboard surface that will also change for AC/task progress visibility.
- The admitted work should stay serialized around the lifecycle contract surfaces (`050`, `100`, `170`, `180`, gate tools, dashboard/parser/lint) even though the wave is now active.
- Seed prompts are the primary implementation target for this wave; Wavefoundry-local specs and generated/local operating surfaces should only be refreshed after the canonical seed contract for each change is implemented and reviewed.
- `12sh5` broadens the specialist and council contract and therefore must stay aligned with `12sf9`, `12sg4`, and any Wave Council wording updates.
- The simplest acceptable AC/task tracking model is checkbox ACs plus review-evidence enforcement, not a second independent tracking table.
- The pre-implementation review gate should remain distinct from ordinary readiness, even if it is ultimately implemented as the first formal phase inside `Implement wave`.

## Outputs Produced Or Expected

- Six admitted change docs under this wave folder
- An active wave container for implementation-governance improvements
- Seed and prompt-surface updates spanning builder-role routing, MCP-first navigation, AC/task tracking, and pre-implementation review policy
- Dashboard, parser, validator, and dashboard presentation updates where the admitted changes require them

## Review Checkpoints

- Admission recorded 2026-05-21: `12sf9`, `12sfb`, `12sfj`, `12sg4`, and `12s5r` admitted to `12sg7 implementation-governance-upgrades`.
- Admission recorded 2026-05-21: `12sh5-enh formal-red-team-role` admitted after the initial ready pass so the framework can formalize `red-team` as a distinct multi-mode specialist and council participant.
- Product-owner: N/A — these changes affect framework workflow, governance, prompt surfaces, and dashboard/tooling behavior rather than target-product semantics.
- **Prepare wave — readiness verdict (2026-05-21): READY**
  - No other wave is currently `active`, so `12sg7` can be promoted without violating the single-active-wave rule.
  - All five admitted change docs are present under the wave folder, structurally complete, and already contain `## AC Priority`.
  - Required review lanes for the admitted scope are `architecture-reviewer`, `code-reviewer`, `qa-reviewer`, `docs-contract-reviewer`, and `security-reviewer`; Wave Council readiness also adds `council-moderator`, `reality-checker`, and `red-team`, with `docs-contract-reviewer` serving as the rotating domain seat because the wave is seed/prompt/contract heavy.
  - Product-owner acknowledgment remains N/A because the wave changes framework workflow and tooling behavior rather than target-product semantics.
  - Next lifecycle step is `Implement wave`.
- **Prepare wave — readiness verdict (2026-05-21, rerun after `12sh5` admission): READY**
  - All six admitted change docs are present under the wave folder, structurally complete, and contain `## AC Priority`.
  - `12sh5` broadens the specialist/council contract but stays within the existing governance and prompt-surface scope of this wave; no new product-owner requirement is introduced.
  - Required review lanes remain `architecture-reviewer`, `code-reviewer`, `qa-reviewer`, `docs-contract-reviewer`, and `security-reviewer`; the `12sh5` scope specifically expands architecture/docs-contract/security review coverage because it defines challenger-role boundaries and council participation semantics.
  - Wave Council readiness remains satisfied with fixed seats `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, and `red-team`, plus rotating domain seat `docs-contract-reviewer`.
  - Next lifecycle step is `Implement wave`.
- **Delivery review — verdict (2026-05-21): PASS**
  - All five required specialist lanes reviewed: `architecture-reviewer`, `code-reviewer`, `qa-reviewer`, `docs-contract-reviewer`, `security-reviewer`.
  - Wave Council delivery pass completed. Fixed seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, `red-team`. Rotating domain seat: `docs-contract-reviewer`.
  - All required-priority ACs across all six changes have supporting code/test/review evidence. 1501 tests pass, docs-lint clean.
  - Pre-implementation gate (12sg4): self-referential exception — this wave introduced the gate and therefore could not have run it before implementation. Reflect: future waves with a large seed surface area should explicitly list core implementation-failure modes (silent wording drift across prompts, parser/lint divergence) in the pre-mortem step.
  - seed-020 (12sfb): assessed as "no change needed"; progress log covers overview seeds 001/010/150/160 but does not name `020` explicitly. Advisory only — ACs satisfied without that change.
  - Advisory (red-team `failure-pressure-test`): pre-implementation gate is protocol-only; a lint check for verdict presence is recommended in a follow-on wave.
  - Next lifecycle step is `Close wave`.

## Review Evidence

- wave-council-readiness: **READY** 2026-05-21 — synthesized by `council-moderator` after fixed-seat review (`architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, `red-team`) plus rotating domain seat `docs-contract-reviewer`; verdict: the admitted scope is implementation-ready, but implementation should preserve one-write-owner serialization around lifecycle seeds, gate tooling, and dashboard/parser surfaces.
- operator-signoff: product-owner N/A; wave activation requested by operator via `Prepare wave` on 2026-05-21.
- architecture-reviewer: approved 2026-05-21 — scope 12sf9, 12sfb, 12sg4, 12sh5. Gate family rename (`wave_gate_open`/`close`/`status`) is correctly layered in server_impl.py with `_READONLY_TOOL` on `wave_gate_status` and mutating annotations on open/close; `design_system_edit_allowed` added to `_VALID_GATES`; governance policy delegated to `workflow-config.json`. Pre-implementation gate implemented as first phase of Implement wave per decision log; protocol-only enforcement is the intended design. red-team role contract leads with mission/invariants before modes; boundaries vs. reality-checker/security-reviewer/senior-engineering-challenger are explicit. Advisory: seed-020 assessment for 12sfb not explicitly recorded in progress log; advisory only, AC-set is satisfied without that change.
- code-reviewer: approved 2026-05-21 — scope 12sf9, 12sfj, 12sg4, 12s5r. Gate tools confirmed in server_impl.py (lines 9410, 9430, 9446) with correct read-only annotation on `wave_gate_status`. `_check_checkbox_ac_syntax` validator confirmed (wave_validators.py:194–206, wired at line 717); two new lint tests pass. Dashboard review badge (`metric-dialog-review-badge`) confirmed in AcsDialog; pending-waves newest-first sort confirmed in WavesCard (line 655) and WavesDialog (line 844); `.agent-dialog { width: min(1000px, 92vw) }` and `.metric-dialog-ac-id { white-space: nowrap }` confirmed in dashboard.css. 12sg4 is doc/prompt-only; no code change needed. 1501 tests pass.
- qa-reviewer: **PASS** 2026-05-21 — scope all six changes. All required-priority ACs are [x] with supporting code/test/review evidence: seeds 222–225 auto-discovered and tests pass (1501); gate tools confirmed; lint validator confirmed; dashboard evidence confirmed. 12sfb unchecked tasks (seed-020, overview seeds) explicitly qualified "if needed" and progress log confirms assessment completed with no changes required; ACs AC-1 through AC-8 are satisfied without those changes. The pre-implementation gate (12sg4) could not have been run for this wave since it was introduced by this wave — self-referential expected exception; Reflect note added to 12sg4 progress log. AC priority tables reconciled: all required rows have code/test evidence or recorded rationale.
- docs-contract-reviewer: approved 2026-05-21 — scope 12sf9, 12sfb, 12sfj, 12sg4, 12sh5. Seeds 222–225 contain no project-specific content; harness extension placeholders correctly present. MCP-first wording is consistent across seed-180, seed-100, seed-050, and seed-211. Truth-hierarchy language is consistent across review-wave.prompt.md, qa-reviewer.md, and code-reviewer.md. Pre-implementation gate wording is consistent across seed-180, seed-100, seed-001, seed-215, and local prompt surfaces. seed-050 wave_council_policy note for red-team is generic (references config key, not project-specific roster). Docs-lint clean.
- security-reviewer: approved 2026-05-21 — scope 12sf9, 12sg4, 12sh5. Gate name validation uses `_VALID_GATES` frozenset; no user-controlled values interpolated into file paths or commands. `wave_gate_status` correctly annotated `_READONLY_TOOL`; open/close tools are not marked readonly (correct). `design_system_edit_allowed` gate is inert when governance is `"evolvable"` — correct by policy, not a security gap. Pre-implementation gate (12sg4) is protocol-only; no new trust boundary. red-team role explicitly routes credible security findings to `security-reviewer` rather than issuing security verdicts. No new injection surfaces introduced.
- wave-council-delivery: approved 2026-05-21 — synthesized by `council-moderator` after fixed-seat review (`architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, `red-team`) plus rotating domain seat `docs-contract-reviewer`. All specialist lanes pass. Two advisory findings carried forward, neither blocking: (1) red-team `failure-pressure-test` on 12sg4: the pre-implementation gate is protocol-only; a follow-on lint check for verdict presence is recommended in a future wave. (2) seed-020 assessment for 12sfb advisory; ACs satisfied without that change. reality-checker: no false confidence detected — critical ACs have code/test evidence, not just checked boxes. Delivery verdict: the admitted scope is fully implemented, all required ACs are evidenced, and the framework now has a coherent implementation-governance contract.

## Journal Refs

- `docs/agents/session-handoff.md`

## Journal Watchpoints

- **Watchpoint:** These changes touch core workflow surfaces (`170`, `180`, `100`, `050`, review docs, and potentially `215`); wording drift across prompts is the main risk.
- **Watchpoint:** The dashboard/parser/lint contract for checkbox ACs must remain consistent; do not let one surface adopt a different forward model.
- **Watchpoint:** `12s5r` remains confined to dashboard presentation files; do not let that narrow UI slice silently widen into unrelated server-side dashboard work.
- **Watchpoint:** The new pre-implementation gate must be clearly distinguished from `Prepare wave` so the workflow gains signal rather than ceremony.
- **Watchpoint:** Specialist builder-role additions must complement `implementer` rather than creating overlapping or contradictory routing.
- **Watchpoint:** `12sh5` must separate `red-team` cleanly from `reality-checker`, `security-reviewer`, and `senior-engineering-challenger`; otherwise the framework will encode overlapping challenger lanes.
- **Watchpoint:** Do not satisfy these changes only in Wavefoundry-local docs. Seed prompts and canonical seed-side contracts are the source of truth for this wave; local specs and rendered/local surfaces are a follow-on reconciliation step.

## Completion Criteria

- All six admitted changes reach `complete` or are explicitly deferred with rationale
- The framework has a coherent implementation-governance contract across planning, readiness, implementation, review, and closure
- Dashboard/parser/lint behavior matches the final AC/task tracking contract
- Wave Council and coordinator surfaces consistently describe any new pre-implementation review behavior

## Handoff Or Next-Wave Notes

- Next lifecycle step is `Implement wave` for `12sg7 implementation-governance-upgrades`.
- During implementation, complete the canonical seed-prompt changes first, then review that shared contract, then reconcile Wavefoundry-local specs and rendered/local surfaces.
- Keep the work serialized around shared lifecycle seeds, gate-tool surfaces, and dashboard/parser/lint files to avoid contract drift during implementation.

Completed At: 2026-05-21

## Wave Summary

*(Populated at closure.)*
