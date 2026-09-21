# Task-Fit Model And Effort Defaults

Change ID: `1yb52-enh task-fit-model-effort-defaults`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-21

## Rationale

**Brief.** Make the existing per-task model/effort policy effective for coordinators and reviewers across supported hosts. Remove framework-imposed model pins from generated Claude wrappers, preserve operator choices, and require a brief task-fit decision before delegation using controls actually available. Success is neutral generated defaults plus actionable guidance, not a claimed improvement in model quality or cost. At planning time the OPEN slot was held by `1y0gz record-layout-roots` (since closed); activation still requires a separate `Implement wave`.

Seed 180 already calls for task-fit selection throughout Prepare to Close (commit `2f29f95a`, lines 159-166). Seed 050's Guru example (line 241) and `render_agent_surfaces.CLAUDE_GURU_AGENT` (line 406) nevertheless specify `model: sonnet`; the five local Claude wrappers carry that pin at line 5. `render_agent_surfaces.render_agent_surfaces` currently writes the Guru template unconditionally through its nested `_tier3_write` (which calls `write_text`, a full-file overwrite), so changing only the rendered file is insufficient and preserving operator model/effort settings needs an explicit merge rule. Factor wrappers are seed-authored (seed 050 task 5); no Python path writes them, and seed 050 specifies no model for them, so removing their pin needs only the agent editing pass plus a literal control on seed text. The only other Python path that touches `.claude/agents/` is the review-protocol reconciler, which replaces or appends its marker region and never edits frontmatter; a valid frontmatter merge therefore survives that pass. Malformed-file preservation is a whole-render contract: the initial and closing reconciler can append or refresh body regions, so they must honor the same skip as the template writer.

Claude Code's documented model selection (verified 2026-09-21) supports per-invocation selection, definition frontmatter (`model`, `effort`, `model: inherit`) and an environment-level subagent default; frontmatter outranks that environment default, which is why an explicit `inherit` can bypass an operator's configured default and omission cannot. Omitted settings do not prove which model ran. Provider/version/organization controls may change effective selection. Keep those details in the host adapter guidance, not in the host-neutral policy.

## Requirements

1. Fresh framework-generated Claude wrappers SHALL omit `model` and `effort` frontmatter by default. Seed 050, the Guru renderer and factor-wrapper guidance SHALL agree. Do not substitute a fixed premium model, a role-based tier map, or `model: inherit` as a universal policy; omission respects the host's resolution rules and operator defaults.
2. Rendering and upgrade reconciliation SHALL preserve existing explicit operator model/effort choices, including `inherit`, Sonnet and unknown future valid values, without normalizing them to framework choices. No value alone proves origin, and no in-tree provenance signal exists for the renderer to read, so the renderer SHALL never remove an existing `model`/`effort` key from an existing wrapper; the only retirement path is the upgrade editing pass in seed 160, which retires a pin only when provenance (for example git history) or explicit scoped operator direction establishes it is framework-owned, and otherwise retains it with a note naming the concrete edit (delete the `model:` line). Do not invent a new provenance database, startup warning or approval gate. On malformed or ambiguous frontmatter (missing closing delimiter, duplicate `model:`/`effort:` lines, non-scalar value) follow the module's one existing fail-safe: leave the file byte-for-byte unchanged, print the existing `render_agent_surfaces: WARNING` stderr line, exclude the path from the returned written list, and keep exit status zero so one bad operator file does not fail a whole setup or upgrade render. Apply that fail-safe across the entire render operation, including reconciliation before and after the template writer; no writer may modify a skipped malformed Claude wrapper. Reuse the existing warning-and-skip principle, without prescribing the Codex TOML merger implementation. The upgrade summary warning channel is not extended; the documented stderr invisibility is accepted. Scope template merging to the Claude Guru path and malformed-wrapper protection to the Claude wrapper family; do not change the Cursor rule that shares `_tier3_write`. Preserve unrelated frontmatter and read-only tool boundaries.
3. Seed 180's canonical host-neutral guidance SHALL require the coordinator to consider capability, effort, complexity, uncertainty, consequences and expected verified work before delegation. Delegation-time selection is the primary mechanism: choose from the models and effort controls actually exposed by the current host for this assignment, honoring operator constraints. Do not require provider/model names or capability rankings to be baked into instructions or rewritten when availability changes. Use a per-invocation selection when the host supports it; otherwise use available defaults and state the limitation. Inheritance is a fallback, not proof of a task-fit decision. Reassess at task boundaries; no fixed premium-for-review or cheap-for-implementation rule.
4. Use the existing work-allocation or review narrative for one concise model/effort rationale per materially distinct assignment; routine similar tasks may share one rationale. Distinguish requested settings from observed runtime identity. If the host does not expose actual model/effort, record unknown rather than claiming verification. Do not add telemetry storage, mandatory model enumerations, model-ranking tables, benchmark requirements or release gates. Independent review requirements remain unchanged.
5. Upgrade guidance SHALL reconcile generated defaults and existing user customization, covering both Guru and factor wrappers; repeated render/upgrade SHALL be idempotent. Seed 160's existing **Host-neutral orchestration reconciliation** section already covers same-pass reconciliation, preserved customization, conflict presentation, idempotent repeat merge and the no-model-registry rule; the edit is limited to the genuine gaps: one table row for `.claude/agents/guru.md` and `.claude/agents/factor-*.md` frontmatter (preserve explicit values, retain ambiguous pins with a note, never add a framework pin), the stale-running-agent caveat, and the do-not-mutate list below. A stale running agent may retain old definitions: guidance SHALL state when a fresh host/agent is necessary rather than promising immediate changes to running workers. Do not mutate user-global host configuration, environment variables, permissions, tool allowlists, active agents or another wave's files as a migration shortcut.
6. Tests SHALL cover fresh generation, deliberate existing model/effort overrides (including a deliberate Sonnet value, which is also the ambiguous-legacy case and needs no separate fixture), `inherit`, unknown values, unrelated keys, malformed frontmatter (missing closing delimiter and duplicate keys, defined in the module's existing regex terms; no YAML parser is added), repeat rendering and the actual surface-render entry path (`render_platform_surfaces.main`, the route used by `wf render-surfaces`, setup, upgrade phase 1 and `wf_sync_surfaces`). Exercise malformed wrappers with absent or stale protocol regions so a reconciliation write cannot hide behind a current marker block; cover the whole render call even when Guru is unavailable. The existing manifest re-render test already asserts an empty second render on a Guru-enabled tree; add pre-seeded override and malformed cases on that same route, and a byte-equality assertion across two `render_agent_surfaces` calls. Verify canonical seed guidance and generated defaults agree with a literal assertion that seed 050's Claude Guru block has no `model:`/`effort:` line. Failure controls follow the repo's in-test self-mutant convention with a non-vacuity guard: one mutant reinserts `model: sonnet` into `CLAUDE_GURU_AGENT`, a second restores the unconditional `write_text` overwrite; the reintroduced-default control is scoped to renderer templates and seed 050, because a docs-lint test fixture legitimately writes `model: sonnet` into a synthetic factor wrapper. No live paid model calls are needed; renderer tests establish configuration behavior, not effective host execution.

## Scope

**In scope:** neutral generated defaults, narrow preservation logic, seed 050/180/160 guidance, existing local policy pointers and wrappers where ownership is proven, and focused tests.

**Intended edits:** `.wavefoundry/framework/scripts/render_agent_surfaces.py` (template line, narrow Claude frontmatter preservation and whole-render malformed-wrapper skip); `tests/test_render_agent_surfaces.py` and `tests/test_render_platform_surfaces.py` (no existing test asserts the Sonnet bytes, so nothing is deleted); `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md` (drop the `model:` line from the Claude Guru example); `180-implement-feature.prompt.md` (additive only: append to the **Choose for the task** bullet the per-invocation-selection-is-primary, inheritance-is-not-a-decision and no-baked-in-provider-names clauses, and add the requested/observed/unknown distinction; the existing clauses stay verbatim because `POLICY_CLAUSES` in the renderer tests pins them); `160-upgrade-wavefoundry.prompt.md` (the gaps named in Requirement 5; `UPGRADE_CLAUSES` in the tests must stay verbatim); `docs/prompts/implement-feature.prompt.md` (retain the shared implementation-wave pointer; detailed selection guidance stays in seed 180); `docs/prompts/upgrade-wavefoundry.prompt.md` (extend the existing reconciliation block, and correct the line that lists `.claude/agents/guru.md` as a generated file so it reads generated-but-preserved); `docs/agents/platform-mapping.md` and `docs/contributing/agent-team-workflow.md` (keep the pinned owner filename and last sentence); the five `.claude/agents/*.md` wrappers, whose pins are framework-owned by git history (`07e9dd17`, `df94140d`); a CHANGELOG Unreleased bullet. Only the Claude wrapper family carries a model pin at HEAD; no Cursor, Codex, Antigravity, Junie, Warp or Copilot surface is affected. Add no new host-specific configuration machinery. Inventory any additional generator before editing it; a material scope expansion requires re-Prepare.

**Protected surfaces:** operator-authored wrappers and model/effort preferences, unrelated frontmatter, permissions/tool allowlists, user-global configuration, the open wave and its implementation. Readiness reviewers are read-only except their own evidence report; implementer owns the named changes after separate activation.

**Out of scope:** model benchmarks, choosing a permanent vendor/model, changing provider quotas or permissions, new routing service, workflow gates, retrospective execution audit, proving which model ran in the reported Claude session, modifying currently running workers, and implementing while another wave owns the OPEN slot.

## Acceptance Criteria

- [x] AC-1: Fresh Guru and seed-guided factor wrapper defaults contain no framework-imposed model/effort pin; regression controls detect a reintroduced fixed model default.
- [x] AC-2: Render and upgrade tests preserve explicit model/effort choices and unrelated frontmatter; an existing pin is never removed by the renderer; malformed input leaves the file byte-for-byte unchanged throughout the complete render call (including both reconciliation passes), with the existing stderr warning, exit zero and no entry in the written list.
- [x] AC-3: Repeated surface rendering is byte-stable after the closing reconcile pass within one `render_agent_surfaces` call and across a second call, for both a fresh wrapper and a pre-seeded wrapper; the actual render route exercises the preservation behavior, and its tests detect an overwrite mutation.
- [x] AC-4: Canonical guidance and local pointers require task-fit consideration with truthful requested/observed/unknown distinctions, using existing narratives and no new ledger, gate or role-tier mapping.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Re-read the renderer seams named in Rationale at activation and confirm the readiness inventory still holds (wrapper ownership and the writer census are recorded facts, not open questions).
- [x] Remove generated defaults and implement the smallest safe preservation rule on the actual writer path.
- [x] Align seed 050, seed 180, upgrade guidance and local policy pointers; preserve explicit choices during local surface reconciliation.
- [x] Add focused fresh/render/upgrade/idempotence and negative-control tests, including deliberate Sonnet and malformed frontmatter.
- [x] Run scoped checks and documentation validation, then required delivery review; refresh the framework suite receipt before closure.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the demonstrated contradiction. |
| AC-2 | required | Operator choices must survive automation. |
| AC-3 | required | Rendering or upgrading must not restore the defect. |
| AC-4 | required | Neutral defaults alone do not cause task-fit selection. |
| AC-5 | required | Change-local correctness and documentation validation. |

## Affected Architecture Docs

`docs/agents/platform-mapping.md` describes the host-adapter boundary; `docs/contributing/agent-team-workflow.md` carries the existing delegation policy pointer. No storage, MCP input contract or runtime architecture changes. Keep policy canonical in seed 180 rather than copying it into every role.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| ownership-and-render | implementer | separate activation | One owner for shared renderer/test edits. |
| policy-and-surfaces | implementer | ownership-and-render | Bounded policy alignment and reconciliation. |
| independent-review | required reviewers | implementation | Fresh contexts; report actual capabilities honestly. |

## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`

## Decision Log

| Date | Decision | Rationale / alternatives |
| --- | --- | --- |
| 2026-09-17 | Omit generated defaults; select per assignment when controls permit | Selected: respects operator/host resolution without a framework model hierarchy. Universal inheritance can bypass host defaults and remains unexamined allocation; role presets hardcode the same error in a different form. |
| 2026-09-17 | Preserve ambiguous legacy pins | A Sonnet value may be either an old template default or an intentional operator choice. Value matching cannot distinguish them; defer ambiguous reconciliation to the existing editing pass, not a new ownership system. In this repository provenance is established: the Guru pin arrived with the renderer template in `07e9dd17` and the four factor pins in `df94140d` via a seed-050 pass copying that example, so all five may be retired here; the ambiguity rule applies to target repositories where history is unavailable. |
| 2026-09-17 | Plan, prepare and review only | Operator explicitly reserved the OPEN slot for another agent at planning time. `1y0gz` closed in `8545c4f9`; the constraint is lifted, and activation still re-reads the renderer seams per Risks. |
| 2026-09-21 | Malformed frontmatter: leave unchanged, warn on stderr, exit zero | The module has exactly one fail-safe convention (`_upsert_review_protocol_region` returning None, reconciler warns and skips). Write-and-report would contradict it; raising would fail a whole setup or upgrade render for one bad operator file. Extending the upgrade summary warning channel was rejected as new machinery for this change. |

| 2026-09-21 | Whole-render malformed-wrapper preservation; outcome-based fail-safe | Operator accepted the demonstrated reconciler counterexample. Guard every participating Claude writer, not only the template write; retain a small conservative implementation without importing the Codex TOML merger design. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-17 | Operator confirmed delegation-time selection as primary, adapting to available providers/models without repeatedly rewriting instructions. | Requirement 3; no static provider matrix or role defaults. |
| 2026-09-21 | Readiness lanes code-reviewer, qa-reviewer and docs-contract-reviewer ran in fresh independent contexts; all three approved with nonblocking refinements, folded into Rationale, Requirements 2, 5 and 6, Scope, AC-2, AC-3, Tasks and the Decision Log. Claude Code frontmatter claims verified against the current docs. | Context `model-policy-readiness-20260921`; lane reports summarized in `events.jsonl`. Requested lane settings: host default model and effort for all three lanes, chosen because plan review against code needs judgment and the lanes are bounded; observed runtime identity unknown. |

| 2026-09-21 | Thought: bounded readiness repair clarifies malformed-wrapper preservation over initial reconciliation, template write and closing reconciliation; removes implementation-shape prescription. No model registry, parser dependency or new gate. Publish repaired packet then focused lane/council verification | MODEL-READY-1; disposable real reconciler reproduced changed=True/reported_written=True |

| 2026-09-21 | Readback: fresh wrappers will omit fixed model/effort; deliberate Sonnet/high and unrelated frontmatter survive rendering, while malformed wrappers stay unchanged through all passes. Thought: implement renderer/tests in one worker; coordinator updates seeds/local pointers and verifies upgrade loading. Retire only the five locally provenance-proven pins. Independent delivery review follows integration | AC-1 through AC-5; readiness receipt review-policy-4926d35aeaa2d77e3233; historical commits 07e9dd17 and df94140d verified |

| 2026-09-21 | Observe: seed 050 now omits generated pins; seed 180 adds delegation-time selection and requested/observed/unknown notes; seed 160/local upgrade guidance covers preservation, proven ownership, fresh agents and protected settings. Five provenance-proven local pins removed with tool allowlists untouched. Upgrade source places extraction before phase_surface_rendering, whose fresh subprocess loaded replaced disk code in a disposable probe; no installing-run old-writer window on that normal path | evidence/upgrade-render-probe.py; upgrade_wavefoundry.main / phase_surface_rendering; seed gate closed |

| 2026-09-21 | Observe: all 236 renderer tests pass; controls kill fixed-default injection, unconditional overwrite, and whole-render validation bypass. Existing frontmatter including tool lists and CRLF survives. Local render produces no additional changes. Source frozen for fresh independent delivery review; full suite pending | GuruWrapperModelPolicyTests; ManifestChannelTests; evidence/delivery-fingerprint.json |

| 2026-09-21 | Independent delivery checks passed renderer behavior; QA found a policy paragraph accidentally inserted inside an earlier seed-050 cross-reference. Relocated unchanged paragraph beside the standalone wrapper contract and restored Task 5. Final fingerprint published for focused independent readback; first full suite green (9,452 tests), fresh receipt pending corrected tree | delivery-code-docs.md; delivery-qa.md; evidence/delivery-fingerprint.json |

| 2026-09-21 | Observe: final suite passed 9,452 tests (12 skips) across 117 files in 311.586s; current green receipt independently hash-verified after editorial correction. Full docs validation passed; code/docs approvals recorded and QA final receipt independently verified and delivery approval recorded. Memory proposal produced zero candidates | delivery-evidence.md; test-cache.json inputs_hash bccb13c717c88225f91743b96af31951603588d51d9fe9ab5790a8947837a4e0 |

| 2026-09-21 | Readback / Thought: MODEL-BOM-1 reproduces silent BOM+CRLF header loss through the complete renderer. Preserve the BOM in the existing header slice while recognizing its opening delimiter; add valid and malformed full-render rows, prove they fail before repair, and independently reverify. Reconcile editorial prompt twins by relying on their common canonical pointer; record allowlist preservation limitation in upgrade editing guidance | Required AC-2 reopened; repair cycle 2 recorded before source edits |

| 2026-09-21 | Observe: two existing full-render tests now include BOM+CRLF valid and malformed rows; before repair they failed five assertions, after the one-line delimiter fix all 236 renderer tests pass. Gapfill: targeted documentation edits remove repeated policy from implement-feature so its pointer matches implement-wave, explain tool-allowlist preservation and explicit upgrade reconciliation, remove doubled whitespace and refresh four touched Last verified dates | /tmp/1ycrj-bom-red.log; /tmp/1ycrj-bom-focused.log; MODEL-BOM-1; evidence/delivery-fingerprint.json |

| 2026-09-21 | Observe: MODEL-BOM-1 resolved by independent code and QA reverification; old-check mutants fail both valid and malformed oracles. Code/docs/QA delivery and focused readiness approvals restored; re-Prepare succeeded. All 9,452 full-suite tests pass (12 skips), current receipt independently verified, docs lint clean. Change complete; no closure or commit | bom-code-docs-review.md; bom-qa-review.md; bom-readiness-delta.md; delivery-evidence.md |

## Risks

| Risk | Mitigation |
| --- | --- |
| Neutral defaults inherit an expensive or unsuitable model | Explicit task-fit consideration; no promise that omission itself optimizes cost. |
| Renderer strips a deliberate preference | Preservation and malformed-input controls on the actual write path. |
| Host does not offer per-task effort/model controls | Honest fallback and unknown effective identity; no unsupported commands. |
| Concurrent wave changes renderer seams | Re-read implementation targets before activation; re-Prepare if assumptions or policy inputs moved. Since planning the renderer changed only in scaffold-path resolution (`8545c4f9`), not the Guru writer. |
| The upgrade that installs this change runs the old writer once | Upgrade phase 1 renders as a subprocess; if it executes the pre-change renderer, operator model/effort edits made before that upgrade are clobbered once. Implementer confirms which renderer that subprocess runs and states the window in seed 160 if it exists. |

## References

- [Claude Code subagent configuration](https://code.claude.com/docs/en/sub-agents#choose-a-model): consulted 2026-09-17, re-verified 2026-09-21 (`model` aliases and `inherit`, `effort` levels, per-invocation override outranks frontmatter, frontmatter outranks the environment default); host behavior is version-dependent.
- `render_agent_surfaces.CLAUDE_GURU_AGENT` and `render_agent_surfaces` nested `_tier3_write`.
- Seed 180, Host-neutral orchestration; seed 050, Claude Guru and factor-wrapper examples.
