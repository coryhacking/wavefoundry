# Pretool dispatch and legacy signoff

Change ID: `20k0d-bug pretool-dispatch-and-legacy-signoff`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-13
Wave: `20k0e pretool-dispatch-and-legacy-signoff`

## Rationale

Make the rendered pre-edit registration reach the hook's existing tool classifier, and make legacy reviewer prose require approval language outside the lane identifier. The consumer is an operator using generated hooks or legacy wave records. Preserve existing gate decisions and typed review authority; introduce no new review steps or evidence stores.

## Requirements

1. Render the owned Claude PreToolUse pre-edit entry without a tool-name matcher, allowing the hook's existing classification and supported explicit path fields to decide. Keep PostToolUse edit matching selective and preserve unrelated project hook entries. Re-rendering replaces the old owned registration without duplicates.
2. Known non-edit tools retain their exemption; known edits retain required-path checks; unfamiliar names retain compatibility reporting and supported-path checks. Do not claim inspection of shell commands, arbitrary patch text, unknown schemas or universal write enforcement.
3. In legacy reviewer prose, a matching lane identifier cannot itself supply a signoff token. Explicit state-line precedence, whole-lane matching, canonical positive states, operator/council restrictions and typed-ledger evaluation remain unchanged.
4. Update canonical hook guidance and regenerate only affected owned surfaces. Add registered configuration-to-hook and legacy-parser regressions with positive and negative controls.

## Scope

In scope: renderer registration/merge, hook contract documentation, legacy prose token matching and focused regression tests. Out of scope: authenticated approvals, changing typed review gates, parsing arbitrary tools, additional lifecycle reviews, performance threshold changes, release or commit.

## Acceptance Criteria

- [x] AC-1: A freshly rendered and an upgraded owned pre-edit registration select an unfamiliar tool; executing its generated hook with a supported protected path enforces the existing gate. Known edit/non-edit controls and unrelated settings survive; a second render is stable.
- [x] AC-2: Post-edit registration remains selective, and unfamiliar tools without supported paths retain the documented compatibility outcome without triggering docs work through the post-edit hook.
- [x] AC-3: Legacy pending prose whose lane contains a signoff token is rejected, while explicit positive state and genuine approval prose outside the lane remain accepted. Exact pending state, token-boundary and authorization-lane controls remain negative.
- [x] AC-4: Authored guidance accurately states registration coverage and its limits; focused tests and changed documents validate, with regression controls detecting removal of each repaired boundary.

## Tasks

- [x] Repair pre-edit registration and update owned-entry reconciliation controls.
- [x] Repair lane-excluded prose matching and add parser controls.
- [x] Update canonical guidance and affected rendered surfaces; document limitations.
- [x] Run focused verification, known-bad controls and independent delivery review; record concise evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness | council-chair and independent seats | complete plan | Critique observable outcomes and host coverage |
| Implementation | implementer | recorded readiness | One write owner for renderer/parser and docs |
| Delivery | independent required reviewers | frozen implementation | Verify registered route, regressions and limits |

## Serialization Points

Only this wave owns the relevant renderer and legacy parser edits while active. Later worker-publication changes in review_evidence.py serialize after this wave pauses. Read-only reviewers do not edit source. Coordinator owns lifecycle records and affected regenerated surfaces.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/agents/platform-mapping.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/cross-cutting-concerns.md`
- `.claude/settings.json`

Root CHANGELOG.md and renderer-owned local guidance are updated only for this behavioral delta; no blanket render or host reconfiguration.

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md`: clarify host hook dispatch versus path classification. `docs/specs/mcp-tool-surface.md` and platform mapping: align relevant existing hook claims. No identity or typed-authority architecture changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The host must actually dispatch to the existing gate |
| AC-2 | required | Broader pre-event coverage must not broaden post-edit work |
| AC-3 | required | A role identifier must not be its own approval |
| AC-4 | required | Verify behavior and prevent stronger claims than the implementation |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
| 2026-10-13 | Corrected both stale threat-model pre-hook claims after recorded repair start. Fresh independent docs verification passed generated registration and an MCP-named protected-path denial; original unsupported-schema, selective-post and live-host limits retained. Final qualification and remaining delivery authority pending. | Canonical targeted controls; recorded cycle-1 repair; no release/closure claim |
| 2026-10-13 | Implemented hook registration, lane masking and matching guidance. Focused suite: 168 tests passed in 59.103s; full docs lint passed. Restoring the finite pre-matcher makes the registered dispatch regression fail; removing lane masking makes nine negative subtests fail. Final combined qualification and independent delivery review pending. | test_render_platform_surfaces; test_server_tools_lifecycle.SignoffLatestStateTests and TypedExclusiveGateDerivationTests; wf_validate_docs |
| 2026-10-13 | Readback: remove only pre-edit matcher; gate supported unfamiliar paths through generated settings/launcher, keep post selective, and mask whole-lane prose identifiers with whitespace. Existing state/typed authority and project settings remain. | AC-1..AC-4; current typed readiness |
| 2026-10-13 | Planned from live source; no implementation edits. Pre-edit and post-edit currently share CLAUDE_EDIT_MATCHER. A bounded local parser probe accepted pending prose for a token-bearing lane and rejected exact pending state. | render_platform_surfaces.CLAUDE_HOOKS; review_evidence.lane_has_signoff_in_evidence |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-13 | Omit only the pre-edit matcher and reuse existing classification. | Covers unfamiliar names without a second classifier. Official hook reference permits omitted matcher for all event occurrences. | Expanding a finite allowlist misses future names; documenting the unreachable branch leaves coverage absent. |
| 2026-10-13 | Exclude matched lane text from legacy prose token search. | Fixes the false positive while preserving genuine compatibility evidence. | Delete all prose compatibility: unnecessary migration impact; accept any lane mention: no positive evidence. |

Official registration contract: [Claude Code hook matchers](https://code.claude.com/docs/en/hooks#matcher-patterns). No live host execution is implied by generated-hook fixtures.

## Risks

| Risk | Mitigation |
| --- | --- |
| All-tool pre-event invocation increases hook invocations | Preserve fast non-edit behavior and do not widen post-edit work; no field timing claims |
| Old registration remains beside new registration | Exercise upgrade merge and idempotence with project hooks |
| Legacy compatibility becomes over-strict | Positive prose and exact-state controls alongside token-bearing negative cases |

## Session Handoff

Coordinator continues through implementation and independent review, then pauses for operator closure.
