# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-21

wave-id: `12sq2 enterprise-role-seeds-and-lint`
Title: Enterprise Role Seeds And Lint

## Changes

Change ID: `12smw-enh enterprise-specialist-seeds`
Change Status: `implemented`

Change ID: `12sp5-enh pre-implementation-gate-lint-check`
Change Status: `implemented`

Change ID: `12sq4-enh wave-close-summary-generation`
Change Status: `implemented`

Change ID: `12sqb-enh wave-implement-mcp-tool`
Change Status: `implemented`

## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| implementer | implement | all admitted changes |
| architecture-reviewer | review | `12sp5`, `12sqb` — Wave Council prepare-phase review contract, `wave_implement` lifecycle control flow |
| code-reviewer | review | `12sp5`, `12sq4`, `12sqb` — server_impl.py changes, verdict recording, status transition, next_tools fix |
| qa-reviewer | review | all admitted changes — AC coverage, test evidence, regression safety |
| docs-contract-reviewer | review | `12smw` — seed authoring, role rename, seed 160 upgrade reference |
| security-reviewer | review | `12sp5`, `12sqb` — council gate enforcement, lifecycle state transition, misuse surface |
| council-moderator | council | full admitted set — Wave Council delivery synthesis |
| reality-checker | council | full admitted set — ceremony and practicality challenge |
| red-team | council | full admitted set — misuse, gate bypass, and stale-state challenge |

## Objective

Extend Wavefoundry with seed prompts for enterprise-relevant specialist roles, rename the `ui-ux-engineer` build role to `frontend-developer`, enhance the `software-engineer` seed with project stack detection, introduce two new enterprise specialists (`enterprise-workflow-engineer`, `enterprise-integration-engineer`), establish a dual-phase review lifecycle (prepare-phase plan review + implementation-phase delivery review) with automated Wave Council review at prepare time and a `wave_implement` gate tool enforcing review completion before implementation begins, and auto-generate a narrative wave summary at `wave_close` time.

## Journal Watchpoints

- **Watchpoint:** `12smw` — `ui-ux-engineer` rename touches seed 223, seed 050, and several other seeds; serialize all seed edits under a single `seed_edit_allowed` gate open/close pass and validate cross-seed references before closing the gate.
- **Watchpoint:** `12smw` — `-developer` was already present in `_BUILD_SUFFIXES` in both `dashboard_lib.py` and `wave_lint_lib/wave_validators.py`; no code change needed. This task is complete.
- **Watchpoint:** `12sp5`, `12sq4`, and `12sqb` all modify `server_impl.py`; implement sequentially under `framework_edit_allowed` gate — do not open the gate for more than one at a time. Implement `12sp5` first (Council verdict format), then `12sqb` (phase parameter + wave_implement, which depends on `12sp5` verdict format), then `12sq4` (wave_close summary).
- **Watchpoint:** `## Prepare Review Evidence` section format must be agreed as part of `12sp5` implementation before `12sqb` touches `wave_review` — both depend on the same section structure for prepare-phase lane signoffs.
- **Watchpoint:** `12sq4` — summary write must precede the status checkpoint write in `wave_close`; a write-order regression would silently drop the summary from closed wave records.

Completed At: 2026-05-22

## Wave Summary

Wave `12sq2` (Enterprise Role Seeds And Lint) delivered 4 changes: Enterprise Specialist Seeds, Post-Prepare Wave Council Review, Wave Close Summary Generation, and Wave Implement MCP Tool. Notable adjustments during implementation: Enterprise Specialist Seeds: workflow-architect removed; consolidated into workflow-engineer; Post-Prepare Wave Council Review: Scope expanded from lint-only to full automated Wave Council review at prepare time; Post-Prepare Wave Council Review: Renamed from pre-implementation to prepare-phase.

**Changes delivered:**

- **Enterprise Specialist Seeds** (`12smw-enh enterprise-specialist-seeds`) — 8 ACs completed. Key decisions: Exclude apple-platform-engineer, mobile-app-builder, terminal-integration-specialist from this batch; Consolidate workflow-architect and enterprise-workflow-engineer into single workflow-engineer
- **Post-Prepare Wave Council Review** (`12sp5-enh pre-implementation-gate-lint-check`) — 7 ACs completed. Key decisions: Warn rather than hard-error for waves predating this feature; Red-team is a fixed seat; rotating seat is heuristic-selected from wave content
- **Wave Close Summary Generation** (`12sq4-enh wave-close-summary-generation`) — 5 ACs completed. Key decisions: Structured field extraction only — no LLM inference; Two-part format: short paragraph + per-change detail
- **Wave Implement MCP Tool** (`12sqb-enh wave-implement-mcp-tool`) — 11 ACs completed. Key decisions: Implement after 12sp5 — depends on Council verdict format; Transition to `implementing` status on create
## Review Evidence

- wave-council-readiness: approved 2026-05-21 — Wave Council readiness confirmed. Four changes admitted: enterprise specialist seeds (12smw), prepare-phase Wave Council review (12sp5), wave-close summary generation (12sq4), wave_implement MCP tool + dual-phase review (12sqb). Scope is coherent. No product-owner requirement (framework-only changes). Required review lanes: architecture-reviewer, code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer. Rotating domain seat: docs-contract-reviewer (seed/prompt-heavy batch). Wave is ready for implementation.
- wave-council-delivery: approved 2026-05-21 — All four changes shipped with full AC coverage and 1571 passing tests. 12smw delivered seed prompts for 11 enterprise specialists, two new role docs (workflow-engineer, enterprise-integration-engineer), role renames (frontend-developer, data-engineer), and stack-detection on the software-engineer seed. 12sp5 made the prepare-phase Wave Council review structural and blocking with rotating seat heuristic and lint enforcement. 12sqb introduced wave_implement as a formal gate tool with dual-phase review (prepare + implementation), implementing status audit across all tools, and wave_review phase parameter. 12sq4 added deterministic wave close summary generation from structured change doc fields. No blocking findings from any reviewer. Red-team: no gate bypass path; Prepare Review Evidence section separation eliminated substring collision risk. Reality-checker: implementing status audit thorough; summary generation appropriately scoped. PASS.
- operator-signoff: approved 2026-05-21

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-21: CONDITIONAL PASS** (red-team fixed seat; architecture-reviewer rotating seat)
  - **Blocking resolved:** Namespace collision risk — `-pre` suffix on lane keys would cause substring match against implementation signoff detection. Fixed: `wave_review(phase="prepare")` writes to a dedicated `## Prepare Review Evidence` section; implementation signoffs remain in `## Review Evidence`. No collision possible. AC-1 in `12sqb` updated to enforce this.
  - **Advisory:** `12smw` has 5 sub-deliverables; explicit sub-task checkpoints recommended during implementation.
  - **Advisory:** Rotating seat heuristic must be documented explicitly in `12sp5` — not left to implementer discretion. Added to AC-2 and tasks.
  - **Advisory:** Override mechanism for council findings should be clarified in `12sp5` (what "resolved" means and whether operator can disagree). Noted for implementer consideration.
  - **Advisory:** `implementing` status audit required before implementation of `12sqb`. Added as AC-8 and task.
  - All blocking issues resolved in change docs. Implementation may proceed.

## Dependencies

- No external wave dependencies.
- `12sp5` and `12sq4` both touch framework scripts; serialize their implementation to avoid conflicts on shared files.
