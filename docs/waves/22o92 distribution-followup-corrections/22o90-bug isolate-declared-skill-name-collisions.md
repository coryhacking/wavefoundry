# Isolate a colliding skill name without stopping unrelated rendering

Change ID: `22o90-bug isolate-declared-skill-name-collisions`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-05
Wave: 22o92 distribution-followup-corrections

## Rationale

Waveforge confirmed its thirteen proposed wf-prefixed names validate, but asked about a later core release introducing a conflicting name. The operator explicitly chose collision-local refusal: fail the conflicting name, not the whole skill render. A current actual render_skills probe with wf-plan-change and wf-synthetic-independent raises before rendering the unrelated declaration. The validators report the right full name; the all-or-nothing render policy is what changes.

## Product Intent

A downstream upgrade should keep unrelated skills usable while making a specific name conflict visible and preserving files at that name. AC-1 to AC-3 establish partial delivery, containment and truthful reporting. This extends Horizon 1 portability without adding a skill override/alias system or changing the adopted vision.

## Requirements

1. Classify complete-name collisions separately from malformed declarations, invalid core registry entries and unsafe destinations. For the specific core/retired/effective-name collision class, refuse the conflicting declaration/name and continue eligible unrelated core and downstream skills. Keep declared_skill_problems useful as a complete diagnostic surface. Do not implement collision handling by parsing human error strings or swallowing every RuntimeError.
2. Preserve every existing file at a colliding rendered name across all active hosts, including template creation, core writes, retirement and declared-skill cleanup. Do not overwrite an existing downstream skill with a newly introduced core skill. Skip the affected name where necessary and report both blocked declaration and any blocked core output. Unrelated names proceed; shared symlink/path-safety or malformed-schema failures retain their existing nonmutating refusal.
3. Produce bounded explicit diagnostics listing each refused full name, its conflict and the downstream rename remedy. Report partial rendering rather than all-skills success or a global render failure. Preserve existing callers/return types where practical and carry diagnostics through the existing render/sync/upgrade reporting channels; inspect each actual caller before selecting the compatible mechanism. Do not silently turn an advisory into permission to omit an entire setup or upgrade phase.
4. Apply the same partition to every skill/template/policy entry point, including render_skills and render_agent_surfaces. Preserve thin-pointer bodies, doc gates, operator-only policies, marker ownership, unmarked file protection and contained cleanup. A normal noncolliding wf-prefixed declaration remains supported; downstream owns renaming and any desired compatibility alias.
5. Test a future core-name introduction against an already rendered downstream skill, plus configured core names, retired names and case/destination collisions. A second valid declaration and an unrelated core skill must still update. Repeat rendering remains deterministic; after a downstream rename resolves the conflict, normal rendering resumes with existing ownership rules.
6. Document collision-local behavior and partial-result semantics. In the existing release guidance, ask maintainers to list newly introduced core skill names in the tagged release notes so downstream owners can check their names before upgrade. This change adds no new core skill names, migration engine or mandatory pre-check gate. An upgrade pre-check can reuse the same diagnostic information if the existing path can report it without a second validator.

## Scope

In scope: typed collision classification, eligible-name partitioning, preservation across all skill write/cleanup paths, compatible partial diagnostics, existing caller integration, tests and concise release guidance.

Out of scope: tolerating unsafe paths or arbitrary invalid declarations, overwriting core/declaration collisions, automatic downstream renames, a new override/alias mechanism, a new approval gate, new core skills or release publication.

## Acceptance Criteria

- [x] AC-1: Actual render_skills and render_agent_surfaces runs with one colliding and one valid declaration update eligible unrelated core and downstream skills on all active hosts. The colliding name is reported and remains byte-for-byte unchanged; restoring the current all-or-nothing path fails this outcome.
- [x] AC-2: An installed downstream skill survives a newly introduced/configured core collision and cleanup passes without overwrite or deletion. Retired/case variants are isolated; malformed schemas and unsafe linked destinations still refuse before mutation. Unmarked files and ordinary marker-owned cleanup retain their contracts.
- [x] AC-3: Actual render/sync/upgrade consumer reports distinguish partial success, full success and fatal refusal without claiming every skill rendered. Diagnostics name the exact conflict and remedy. Removing the collision through a downstream-owned rename restores normal rendering; documentation and release guidance match the observed behavior.

## Tasks

- [x] Freeze the current mixed-declaration render failure and enumerate actual skill/policy/template callers.
- [x] Implement collision-local partitioning and protected-name writes/cleanup with compatible partial diagnostics.
- [x] Update affected contracts, tests and release guidance; independently verify both public render paths, negative controls and required delivery reviews.

## Agent Execution Graph

One implementation owner handles the renderer and its callers. Independent code, QA, architecture, security and docs-contract reviewers verify partial results and non-overwrite boundaries. Serialize render_agent_surfaces.py and CHANGELOG.md with sibling profile work.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_declared_extension_skills.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/contributing/build-and-verification.md`
- `docs/references/release-flow.md`
- `docs/specs/mcp-tool-surface.md`

The current keyword census finds declared_skill_problems itself and its direct production caller in render_agent_surfaces.py, plus tests. _all_skills and _declared_prompt_doc_creations have additional internal consumers; implementation must trace their actual public callers before mutation. Extra source files require a named plan amendment before readiness. CHANGELOG.md records behavior; seeds, core names, existing downstream files, old wave records and :memory:.ses are protected. No source gate is open.

## Affected Architecture Docs

Update the MCP/render contract for partial outcomes and ownership preservation, plus maintainer release guidance for listing new core names. No new skill registry owner is introduced.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | A name conflict must not prevent unrelated skill delivery. |
| AC-2 | required | Partial rendering must not weaken ownership or filesystem safety. |
| AC-3 | required | Operators and upgrades must see what was actually delivered. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Refuse only the colliding name while preserving it and rendering unrelated eligible skills. | Explicit operator decision. The mixed-declaration public renderer currently raises and renders none. Name-local partitioning controls delivery; a visible partial result tells the downstream owner what to rename. Success includes unchanged colliding bytes and updated unrelated skills, not only a validator message. | Global refusal is safe but blocks unrelated updates; automatic rename/overwrite changes downstream ownership; a pre-check alone warns without fixing the later all-or-nothing render. |

## Risks

Filtering only the final write loop can still fail earlier during template/policy enumeration or delete the conflicted skill during cleanup. Shared unsafe host roots remain fatal. Existing list-returning callers need truthful compatible partial diagnostics. Do not relabel the same context as independent review or claim a field upgrade from synthetic rendering.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-06 | Implementation and all required technical delivery reviews complete; no deferred AC or task. | Final canonical run passes 12,400 tests across 218 files in 575.668 seconds, with 12 expected skips and green input hash 2e773a18ef0cde23bd5bf478dcb01125cbf9eab7c5f16df94c63a0640231553a. All seven lane approvals and Council PASS establish intent. Operator closure signoff remains pending; the requested pause permits scanner-wave implementation next. |
| 2026-11-05 | Implemented the collision partition and protected writes/cleanup. Focused suite passes 67 tests; both public renderers preserve conflicting names and deliver unrelated skills. Actual CLI output is carried through sync and upgrade, and the reconciliation registry remains usable. Three controlled mutants are rejected: whole-render abort, colliding cleanup/policy writes, and core overwrite. | `.wavefoundry/framework/scripts/tests/test_declared_extension_skills.py`; temporary logs `/private/tmp/22o90-tests.log` and `/private/tmp/22o90-mutants.log`. Controlled temporary repositories, not a field upgrade; full-suite and independent delivery review remain coordinator work. |
| 2026-11-05 | Readback: classify full-name collisions separately, preserve all colliding name bytes across rendering and cleanup, render unrelated eligible skills and report a partial result. Malformed declarations and unsafe shared paths still refuse. | AC-1–3; before a core collision aborts every skill, after only its name is withheld. Scope is renderer/declaration and existing caller reporting; no rename, new skill or permission bypass. |
| 2026-11-05 | Readiness implementation note: reconcile_scan._mandatory_paths also consumes _all_skills. Exercise that existing consumer under AC-3 during integration; this observation adds no source-write permission or changed requirement. | Supplemental performance/release review; shared-skill partition must reach actual callers. |
| 2026-11-05 | Planning only; operator selected collision-local failure. Actual temporary render with wf-plan-change plus wf-synthetic-independent raises the core conflict and produces no unrelated skill. | Public render_skills; original helper diagnostic is correct. Source unchanged; no downstream rename, wave admission or readiness performed. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
