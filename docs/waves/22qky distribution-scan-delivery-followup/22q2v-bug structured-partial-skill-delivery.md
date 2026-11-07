# Report partial skill delivery to structured callers

Change ID: `22q2v-bug structured-partial-skill-delivery`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: 22qky distribution-scan-delivery-followup

## Rationale

Waveforge reports that a declared skill collision is visible in console output but absent from the renderer manifest, sync diagnostics and upgrade summary. The current implementation preserves unrelated rendering correctly; its structured callers cannot distinguish complete delivery from a successful render that withheld a skill. A temporary-root execution of the platform renderer with one retired-name collision and one independent declaration returned zero, rendered the independent skill, and produced a manifest containing only `written`.

## Product Intent

Distribution operators and MCP agents can identify withheld skills and the action needed to restore them without parsing logs, while continuing to receive unrelated skills. This supports the adopted vision's dependable execution and continuity foundations without changing the destination or introducing a new approval gate. AC-1 through AC-3 establish the observable reporting outcome; AC-4 protects existing delivery and vocabulary boundaries.

## Requirements

1. Preserve collision-local refusal: a declared name colliding with an effective core or retired name remains withheld and its existing output preserved; unrelated declarations and core skills still render. Declaration-schema or unsafe-path failures retain their existing failure behavior. Noncolliding downstream `wf-*` skills remain supported.
2. Successful render manifests and structured sync results explicitly report `partial_skill_delivery`, with structured `skill_collision` diagnostics naming each collided declaration, its reason and the rename/rerender remedy. The noncollision result reports false and an empty collision list. Partial delivery remains a successful render operation with an advisory, not a global render failure.
3. Carry the same facts into the upgrade's machine-readable summary and MCP diagnostics, including its separate cleanup/resume process. Bound collections using the existing response limits with explicit counts when details are omitted. Preserve the partial flag even when details or console output are truncated. Do not infer completeness from an absent legacy field: retain compatible old-child handling and distinguish unavailable reporting where needed.
4. A subsequent successful render after a declaration is renamed clears the current partial state. Store upgrade state only in the owning upgrade's existing lifecycle state; do not let one repository, failed attempt or previous invocation contaminate another result. Human output remains useful, but machine consumers do not depend on parsing its wording.
5. Describe the partial-result contract in the affected MCP and platform documentation. Do not change skill naming policy, permission rendering authority, lifecycle approvals, install adoption or automatic retry behavior.

## Scope

**In scope:** `render_agent_surfaces.py` result construction; `render_platform_surfaces.py` manifest output; `wf_server/docs_handlers.py` sync functions; `upgrade_wavefoundry.py` surface-render result persistence and summary emission; `wf_server/upgrade_handlers.py` summary/diagnostic propagation; focused tests; MCP/platform documentation and a concise changelog entry.

**Out of scope:** registry renames, downstream source edits, server registration behavior, collisions in MCP tools, generalized partial-render policy for unrelated warnings, scanner upgrade preflight, setup readiness changes, commits, releases and wave closure.

## Acceptance Criteria

- [x] AC-1: A public platform-render invocation with a real declared-name collision and a noncolliding `wf-*` declaration returns a manifest with partial delivery and the exact collision, preserves the collided path and renders the noncolliding skill. The current manifest containing only `written` fails this criterion.
- [x] AC-2: The sync MCP path exposes an advisory `skill_collision` and partial delivery from the manifest even when console output is empty or truncated; a noncollision run reports complete skill delivery. Existing permission-render restrictions remain intact.
- [x] AC-3: Surface rendering followed by the upgrade's summary/cleanup boundary carries the collision into the summary sentinel and bounded MCP response, with an advisory and retained partial flag. Renaming the declaration and rerunning clears the current result; a different root and a legacy summary do not falsely inherit it.
- [x] AC-4: Focused tests cover effective renamed-profile core names, case-insensitive or retired-name collision behavior, noncolliding shared prefixes, unchanged schema-error refusal and idempotent rerendering. Changed documentation agrees with the tested success-versus-partial contract. Tests added or changed for this change pass, and no failure elsewhere is attributable to it.

## Tasks

- [x] T-1: Propagate typed collision results through renderer manifests and sync responses.
- [x] T-2: Persist this upgrade's collision state and expose it through summary and MCP adapters, including reset and bounded output.
- [x] T-3: Add public-path regression and known-bad controls; update the affected contract documentation and changelog through the coordinator.
- [x] T-4: Record focused evidence, obtain independent required review and resolve material findings.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Collision propagation | implementer | Prepare wave | Existing result owner supplies facts; adapters serialize them. |
| Integration and docs | coordinator | Collision propagation | Serialize shared upgrade and docs-handler edits with scanner work. |
| Verification | required reviewers | Implementation | Fresh independent contexts; no reviewer source writes. |

## Serialization Points

The coordinator owns shared documentation and changelog integration. `upgrade_wavefoundry.py` and `wf_server/docs_handlers.py` also carry scanner work in this wave; serialize edits to those files or explicitly isolate functions and reread the combined diff before testing. Preserve unrelated pre-existing VERSION, README, docs index, overview and prompt-manifest edits.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/wf_server/docs_handlers.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_declared_extension_skills.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/agents/platform-mapping.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` for the renderer-manifest and persisted-upgrade-summary reporting path. Update `docs/specs/mcp-tool-surface.md` and `docs/agents/platform-mapping.md` for caller-visible partial skill delivery. No ownership or permission boundary changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the truthful producer contract and preserves useful delivery. |
| AC-2 | required | Fixes the motivating agent-facing sync gap. |
| AC-3 | required | Fixes the motivating upgrade gap across process boundaries. |
| AC-4 | required | Protects distribution customization and the existing name-local failure boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-06 | Readback: preserve successful unrelated rendering while propagating exact collision facts through manifests, sync and upgrade summaries, including cleanup and retry. A collision currently yields only prose; afterward the same successful operation carries partial_skill_delivery and an advisory. No registry, permission or adoption behavior changes. | AC-1–AC-4; renderer, sync and upgrade adapters/tests; shared documentation remains coordinator-owned. |
| 2026-11-06 | Planning only. MCP source reads verified result metadata exists but the platform manifest and sync adapter discard it; the upgrade phase only logs stderr diagnostics. Temporary-root render returned exit 0, manifest fields `written` only, and a rendered unrelated skill. The existing log-propagation test passed, showing its assertions do not cover structured consumers. | `SkillRenderResult`; `render_platform_surfaces.main`; `run_sync_surfaces`; `phase_surface_rendering`; `InvalidDeclarationRefusesRenderTests.test_partial_render_diagnostic_reaches_sync_and_upgrade_consumers` (1 test, 1.207s). Indexed retrieval reported stale; cited current source was read directly with MCP. |
| 2026-11-06 | Implemented structured manifests, sync advisory and upgrade checkpoint/summary propagation. Real child rendering with console output erased still exposes the collision; renamed declarations clear it and failed rerenders reset stale observations. Bounded MCP test retains the flag for 2,000 collision records and reports omitted counts. Legacy/malformed manifests remain unknown. | `InvalidDeclarationRefusesRenderTests` 7/7 pass (2.874s); declared-skill file previously 67 tests/1 existing skip (15.027s); `WaveUpgradeMcpToolTests` 71/71 pass (11.851s); cleanup-focused upgrade tests 77 tests/1 existing skip (12.050s). Initial cleanup test invocation lacked scripts import path; corrected invocation uses PYTHONPATH. |
| 2026-11-06 | Known-bad control removed partial_skill_delivery from the actual child manifest; the public sync assertion failed as expected. No source mutation or test skip was used. | In-memory `_run_main` wrapper applied to `test_partial_render_diagnostic_reaches_sync_and_upgrade_consumers`; exactly one assertion failure, no execution errors. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-06 | Extend the existing result and summary contracts additively; retain successful partial rendering. | Existing collision detection already controls withheld names. Explicit fields let callers distinguish operation success from delivery completeness, and public-path tests can reject log-only behavior. False positives are bounded by the actual collision result rather than prose parsing. Post-release success is an operator-visible collision advisory with unrelated skills still delivered. | A nonzero exit for a collision would recreate global disruption and mislabel useful completed writes. More console wording would retain the current machine-consumer gap. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A separate cleanup process or output bounder loses the advisory. | Exercise the persisted summary and bounded MCP paths; keep the terminal partial flag outside truncatable detail. |
| Stale state reports a repaired collision indefinitely. | Scope persistence to the owning upgrade and test collision-to-clean transitions and separate roots. |
| A typed manifest change breaks old child processes. | Add fields compatibly and distinguish missing legacy reporting from observed false. |
| Existing global shared objects leak diagnostics between renders. | Derive per-run results and test successive different declarations. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
