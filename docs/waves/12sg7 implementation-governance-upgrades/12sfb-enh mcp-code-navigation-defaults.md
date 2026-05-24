# MCP-First Code Navigation Defaults For Implementation

Change ID: `12sfb-enh mcp-code-navigation-defaults`
Change Status: `complete`
Owner: wave-coordinator
Status: complete
Last verified: 2026-05-21
Wave: `12sg7 implementation-governance-upgrades`

## Rationale

Wavefoundry already ships strong MCP code-navigation capabilities: `code_ask`, `code_search`, `code_definition`, `code_references`, `code_keyword`, `code_outline`, and `code_dependencies`. It also already contains partial guidance to use them:

- `docs/agents/guru.md` defines the retrieval loop in detail.
- `seed-050` already tells generated role docs to orient with MCP tools before broad file reads.
- `docs/prompts/agents/implement-wave.prompt.md` already includes a pre-edit orientation pass.

Even so, agents still default to `grep`, broad file reads, and ad-hoc shell exploration during implementation. The problem is not absence of capability; it is that the framework does not yet make MCP-first exploration a sufficiently hard execution default at the exact moment implementation begins.

Current gap shape:

1. The public implementation contract does not explicitly say that code navigation tools are the **default** exploration path and that shell/file scans are **fallback only**.
2. The generated `implementer` guidance mentions useful tools, but not as a hard tool hierarchy with explicit escalation/fallback conditions.
3. The wave coordinator surfaces tell agents to produce a plan before edits, but do not clearly require that the plan be grounded in MCP-based code ownership, definition, and call-site evidence.
4. There is no durable framework-level guidance on reducing tool-friction when hosts support eager MCP loading or pre-registration.

This change makes the framework operationally clear: when MCP is attached, agents should reach for Wavefoundry code navigation first, and only fall back to `grep`, `rg`, or broad reads when MCP results are unavailable, stale, or insufficient for the specific question.

## Requirements

1. The framework must define an explicit **MCP-first code exploration order** for implementation work:
   - `code_ask` for cross-cutting “what does this do?” questions
   - `code_search` for conceptual/module discovery
   - `code_definition` for declarations and owning symbols
   - `code_references` for call sites and impact radius
   - `code_keyword` for exact token/string matches
   - `code_outline` before broad `code_read` on large files
   - shell search (`rg`, `grep`) and broad file reads only as fallback
2. The implementation surfaces must explicitly state that, when MCP is available, agents must not begin exploration by defaulting to shell search or full-file reads for questions that the code-navigation tools are designed to answer.
3. The framework must define clear fallback conditions for using shell/file exploration instead:
   - MCP not attached
   - relevant MCP tool unavailable in the host session
   - index freshness or index health makes MCP results unreliable
   - MCP results are genuinely insufficient after a reasonable pass
4. The public and agent-body `Implement wave` / `Implement feature` contracts must require the pre-edit implementation plan to be grounded in MCP evidence about:
   - which file owns the behavior
   - whether the target symbol already exists
   - which call sites or references will be affected
   - what neighboring patterns already exist in the repo
5. The generated `implementer.md` role doc must name a strict exploration hierarchy and must state plainly that `grep`/`rg`/manual file scanning are fallback tools, not first-choice exploration when MCP is available.
6. The generated `planner.md` and `wave-coordinator.md` guidance must reinforce the same MCP-first expectation for planning and lane selection, so the habit is reinforced before implementation starts.
7. The Guru surfaces must distinguish between:
   - code/doc Q&A retrieval, and
   - implementation-time code navigation obligations,
   so implementers do not treat Guru as “for questions only” while still defaulting to shell search during coding.
8. The framework should add host-agnostic guidance that repositories should pre-register or eagerly expose Wavefoundry MCP tools when the host supports it, to reduce schema-loading friction that makes shell tools the easier default.
9. The framework should require implementers to record a `Gapfill:` or equivalent note when MCP exploration was unavailable or insufficient and forced a fallback, so repeated tool-friction becomes visible to maintainers.
10. The new guidance must preserve existing Guru validation discipline: MCP-first navigation does not authorize answering from `code_ask` alone; targeted validation reads are still required before synthesis or code changes.

## Scope

**Problem statement:** Agents know shell search and file reads are always available, so they often use those by habit instead of the framework’s higher-signal MCP code-navigation tools.

**In scope:**

- Seed updates that make MCP-first exploration explicit in planning and implementation contracts
- Role-doc generation updates for `implementer`, `planner`, and `wave-coordinator`
- Guru/auto-Guru clarifications where needed
- Operator-facing guidance on fallback conditions and eager MCP registration when supported

**Out of scope:**

- Changing MCP server retrieval algorithms or ranking behavior
- Host-specific product work beyond documentation/generation guidance
- Enforcing tool use through runtime hard-blocks in every host
- Rewriting all existing role docs by hand outside the generated framework surfaces

## Acceptance Criteria

- [x] AC-1: `seed-180` and related implementation surfaces explicitly state that MCP code-navigation tools are the default pre-edit exploration path when available.
- [x] AC-2: `seed-050` generates `implementer.md`, `planner.md`, and `wave-coordinator.md` with a clear tool-use hierarchy and explicit shell-search fallback wording.
- [x] AC-3: `seed-100` ensures repo-local `implement-wave` / `implement-feature` prompt docs carry the MCP-first exploration rule in their execution guidance.
- [x] AC-4: The framework documents the allowed fallback conditions for `rg`/`grep`/broad file reads instead of leaving fallback judgment implicit.
- [x] AC-5: The implementation planning contract requires evidence of symbol ownership, references, and in-repo pattern discovery before first edit.
- [x] AC-6: Guru or related routing docs clearly explain that implementation-time navigation should still use MCP tools even when the agent is not in a dedicated “Guru” Q&A interaction.
- [x] AC-7: The framework includes guidance to reduce host/tool friction by pre-registering or eagerly exposing MCP tools when the host supports it.
- [x] AC-8: The change does not weaken the existing requirement to validate with targeted reads before making claims or edits.

## Tasks

- [x] Update `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` to make MCP-first code navigation an explicit pre-edit implementation requirement, with shell search as fallback only.
- [x] Update `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` so generated `implement-wave` / `implement-feature` prompt docs repeat the same rule in public execution guidance.
- [x] Update `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md` so generated canonical role docs for `implementer`, `planner`, and `wave-coordinator` include a strict MCP tool hierarchy and fallback conditions.
- [ ] Update `.wavefoundry/framework/seeds/020-run-contract.prompt.md` if needed to add a general “prefer structured repository tools over shell exploration when available” rule for implementation and investigation work.
- [x] Update `.wavefoundry/framework/seeds/211-guru.prompt.md` — added implementation-time navigation vs. Guru Q&A clarification in Usage by Other Agents section.
- [ ] Update supporting overview or refresh surfaces as needed, likely including:
  - `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`
  - `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md`
  - `.wavefoundry/framework/seeds/150-refresh-wavefoundry.prompt.md`
  - `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- [x] Update Wavefoundry self-hosted docs/generated surfaces — `docs/agents/implementer.md` (added Codebase Orientation MCP Tools section), `docs/prompts/implement-wave.prompt.md` (added MCP-first exploration guardrail).
- [x] Add explicit note on recording MCP fallback friction in journals or progress logs when it changes implementation behavior.
- [x] Run framework verification and docs validation after implementation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seed-core | implementer | Prepare wave | `180`, `100`, `050`, optional `020`/`211`; `seed_edit_allowed` gate required |
| overview-sync | implementer | seed-core | `001`, `010`, `150`, `160` alignment |
| wf-self-host-surfaces | implementer | seed-core | Refresh local generated/canonical docs |
| verify | qa-reviewer | all | Framework tests + docs validation |

## Serialization Points

- `seed-180`, `seed-100`, and `seed-050` should be reviewed together because they define one implementation contract.
- Any Guru wording change should be reviewed after the implementation-contract wording is stable, to avoid contradictory overlap.
- Self-hosted doc refresh should happen after the seed text is finalized.

## Affected Architecture Docs

N/A — this is an execution-contract and prompt-surface change, not a runtime architecture change.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The main behavior change is at implementation start |
| AC-2 | required | Role docs are where the habit is reinforced |
| AC-3 | required | Public prompt docs must carry the same rule |
| AC-4 | required | Fallback must be principled, not vague |
| AC-5 | required | Planning evidence is how this changes behavior materially |
| AC-6 | important | Prevents “Guru is only for Q&A” misreading |
| AC-7 | important | Reduces recurrence caused by host friction |
| AC-8 | required | Must preserve validation rigor |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-21 | Change doc created after reviewing existing guidance in `seed-050`, `seed-180`, `seed-211`, `docs/agents/implementer.md`, and `docs/prompts/agents/implement-wave.prompt.md`. | Operator request + repo inspection |
| 2026-05-21 | Prepare wave completed; change marked ready for implementation in `12sg7`. | `docs/waves/12sg7 implementation-governance-upgrades/wave.md` |
| 2026-05-21 | Seed-core workstream complete: added explicit MCP-first code exploration section to `seed-180` (ordered hierarchy, four fallback conditions, Gapfill obligation, validation-rigor preservation note); strengthened `implementer.md`, `planner.md`, and `wave-coordinator.md` MCP orientation sections in `seed-050` with explicit fallback wording; updated `implement-feature + implement-wave` and `implement-wave` per-prompt rules in `seed-100` to carry the MCP-first code navigation requirement. Docs-lint passes. | `seed-180`, `seed-050`, `seed-100` edits; `wave_validate` clean |
| 2026-05-21 | Overview + self-hosted workstream complete: added implementation-time navigation vs. Guru Q&A clarification to `seed-211`; added AC-7 host-friction / pre-registration note to `seed-050`; added Codebase Orientation (MCP Tools) section to `docs/agents/implementer.md`; added MCP-first code exploration guardrail to `docs/prompts/implement-wave.prompt.md`. Overview seeds (001, 010, 150, 160) assessed — do not describe code exploration model explicitly and carry no contradictory language; no update required. Docs-lint passes. | `seed-211`, `seed-050`, `docs/agents/implementer.md`, `docs/prompts/implement-wave.prompt.md`; `wave_validate` clean |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-21 | Treat this as an enforcement-and-defaults problem, not a missing-capability problem | Existing guidance already mentions MCP tools, but not strongly enough at implementation time | Re-document all MCP tools from scratch |
| 2026-05-21 | Put the strongest rule in `seed-180` / `seed-100` rather than Guru alone | The implementation shortcut is the highest-leverage insertion point | Keep the rule only in Guru and role docs |
| 2026-05-21 | Preserve shell search as fallback rather than banning it outright | There are legitimate no-MCP or degraded-index cases | Absolute prohibition on `rg`/`grep` first |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Guidance duplicates Guru and creates conflicting wording | Keep Guru focused on retrieval mechanics; keep `180`/`100` focused on implementation obligations |
| Agents still skip MCP tools out of habit | Make the rule procedural at the plan-before-edit checkpoint and in generated role docs |
| Hosts differ in how easily MCP schemas are exposed | Use host-agnostic wording: eager loading when supported, fallback when not |
| Overly rigid wording slows down trivial edits | Scope the requirement to exploration questions that MCP tools are designed to answer, not every single edit regardless of context |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
