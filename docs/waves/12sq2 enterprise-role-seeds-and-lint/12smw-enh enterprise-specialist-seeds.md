# Enterprise Specialist Seeds

Change ID: `12smw-enh enterprise-specialist-seeds`
Change Status: `implemented`
Owner: software-engineer
Status: implemented
Last verified: 2026-05-21
Wave: 12sq2 enterprise-role-seeds-and-lint

## Rationale

The project has 18 specialist agent docs that were manually authored and have no seed prompts backing them. Other projects that adopt Wavefoundry cannot benefit from these roles because the framework has no mechanism to generate them. Additionally, two role gaps exist for common enterprise stacks (BPM workflow engines, event-driven integration) that no existing specialist covers.

A separate design decision applies to `software-engineer`: rather than maintaining language-specific engineer roles (`java-backend-engineer`, `dotnet-engineer`, etc.) as separate specialists, the `software-engineer` seed should detect the project's primary tech stack and generate a focused, stack-tailored doc. The seed is instructional and comprehensive; the generated agent is specific (e.g. "Senior Java Software Engineer" in a Java project, "Senior Python Software Engineer" in a Python project). This eliminates role proliferation while preserving depth.

## Requirements

1. Seed prompts must exist for all 11 enterprise-relevant existing specialists so they can be generated in new projects via the agent bootstrap surface.
2. Two new specialist docs must be authored: `enterprise-workflow-engineer` and `enterprise-integration-engineer`.
3. Seed prompts must exist for the two new specialists.
4. The `software-engineer` seed (222) must be enhanced to detect project tech stack (languages, frameworks, build tools) and tailor the generated doc's title, operating identity, responsibilities, and harness extensions accordingly.
5. All new and updated specialist docs must pass `docs-lint` (correct `Category: specialist`, valid metadata, no stale role references).
6. Seed prompts must follow the established seed format (frontmatter: Lane, seed number in 220s–230s range, output path, category).
7. The `workflow-architect` specialist doc must be updated to clarify its dev-workflow scope is distinct from enterprise BPM (to avoid confusion with the new `enterprise-workflow-engineer`).

## Scope

**Problem statement:** Enterprise projects using Wavefoundry cannot generate specialist roles from seeds, two enterprise role gaps exist, and the `software-engineer` seed produces a generic doc rather than a stack-specific one.

**In scope:**

- Enhanced `software-engineer` seed (222): stack detection, tailored title + identity + responsibilities + harness (Python, Java, C#/.NET, TypeScript/Node as primary variants)
- Rename build role `ui-ux-engineer` → `frontend-developer`: rename `docs/agents/ui-ux-engineer.md`, seed `223-ui-ux-engineer.prompt.md`, update Lane/title in seed, update all references in seeds (050, 100, 160, 170, 180)
- Rename build role `senior-data-engineer` → `data-engineer`: rename seed `224-senior-data-engineer.prompt.md`, update Lane/title in seed, update all references in seeds (050, 100, 160, 170, 180) and `implementer.md`, `specialists/README.md`
- Add `-developer` to `_BUILD_SUFFIXES` in `wave_validators.py` so `frontend-developer` auto-classifies as `Category: build` (already present — no code change needed)
- Seed prompts for 7 existing enterprise specialists: `backend-architect`, `software-architect`, `database-optimizer`, `security-engineer`, `ai-engineer`, `api-tester`, `technical-writer`
- New specialist doc + seed for: `workflow-engineer` (combined BPM architect + implementer: Camunda, Temporal, Flowable, jBPM; BPMN modeling, approval chains, failure recovery), `enterprise-integration-engineer` (Kafka, RabbitMQ, Azure Service Bus, IBM MQ)
- Removed `workflow-architect` doc (CI/CD scope moved to `devops-automator`; BPM scope consolidated into `workflow-engineer`)
- Minor scope clarification update to `workflow-architect` doc
- Seed numbering assigned from available slots in the 220s–230s range

**Out of scope:**

- Seeds for non-enterprise specialists (`apple-platform-engineer`, `mobile-app-builder`, `terminal-integration-specialist`)
- Seeds for `devops-automator`, `sre`, `accessibility-auditor` (deferred)
- Retiring existing `java-backend-engineer` and `frontend-developer` specialist docs (deferred — may be kept as manually maintained project-specific docs)
- Changes to existing seed-backed specialists (guru, red-team, senior-engineering-challenger, environment-auditor, operating-surface-gardener, reality-checker)
- Changes to `_COORDINATE_STEMS` in wave_validators.py

## Acceptance Criteria

- [x] AC-1: `software-engineer` seed (222) detects project tech stack and produces a tailored title, identity, and harness; verified by generating in a Python and Java context
- [x] AC-2: `ui-ux-engineer` build role renamed to `frontend-developer`; seed 223 updated; all seed references updated; `docs-lint` passes
- [x] AC-2b: `senior-data-engineer` build role renamed to `data-engineer`; seed 224 updated; all seed references updated; `docs-lint` passes
- [x] AC-3: Seeds exist for all 7 enterprise-relevant existing specialists and pass lint
- [x] AC-4: `workflow-engineer.md` exists in `docs/agents/specialists/` with `Category: specialist` and has a corresponding seed (234); scope covers BPM architecture + implementation (Camunda, Temporal, Flowable, jBPM)
- [x] AC-5: `enterprise-integration-engineer.md` exists in `docs/agents/specialists/` with `Category: specialist` and has a corresponding seed; scope covers messaging/event streaming (Kafka, RabbitMQ, Azure Service Bus, IBM MQ)
- [x] AC-6: `workflow-architect.md` updated to clarify it owns dev-workflow/CI-CD, not BPM
- [x] AC-7: `wave_validate` and `docs-lint` pass clean with no new errors

## Tasks

- [x] Audit existing specialist docs to extract consistent structure for seed template
- [x] Rename `docs/agents/ui-ux-engineer.md` → `docs/agents/frontend-developer.md`; update Role, title, Category
- [x] Rename seed `223-ui-ux-engineer.prompt.md` → `223-frontend-developer.prompt.md`; update Lane and title
- [x] Update `ui-ux-engineer` references in seeds 050, 100, 160, 170, 180 and `implementer.md`, `specialists/README.md`
- [x] Confirm `-developer` already in `_BUILD_SUFFIXES` in both `dashboard_lib.py` and `wave_lint_lib/wave_validators.py` (no code change needed)
- [x] Rename seed `224-senior-data-engineer.prompt.md` → `224-data-engineer.prompt.md`; update Lane and title
- [x] Update `senior-data-engineer` references in seeds 050, 100, 160, 170, 180 and `implementer.md`, `specialists/README.md`
- [x] Enhance `software-engineer` seed (222) with stack detection logic (Python, Java, C#/.NET, TypeScript variants)
- [x] Author seed prompts for 7 existing enterprise specialists: `backend-architect`, `software-architect`, `database-optimizer`, `security-engineer`, `ai-engineer`, `api-tester`, `technical-writer`
- [x] Author `docs/agents/specialists/enterprise-workflow-engineer.md`
- [x] Author seed `enterprise-workflow-engineer.prompt.md`
- [x] Author `docs/agents/specialists/enterprise-integration-engineer.md`
- [x] Author seed `enterprise-integration-engineer.prompt.md`
- [x] Update `workflow-architect.md` scope clarification
- [x] Run `wave_validate` and `docs-lint`; fix any failures

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Audit + seed template design | software-engineer | — | Extract common structure from existing docs |
| Rename ui-ux-engineer → frontend-developer | software-engineer | — | File, seed, references, _BUILD_SUFFIXES |
| Enhance software-engineer seed (222) | software-engineer | Audit | Stack detection: Python, Java, C#/.NET, TypeScript |
| Seeds for 7 existing specialists | software-engineer | Audit | backend-architect, software-architect, database-optimizer, security-engineer, ai-engineer, api-tester, technical-writer |
| New specialist docs (2) | software-engineer | Audit | enterprise-workflow-engineer, enterprise-integration-engineer |
| Seeds for 2 new specialists | software-engineer | New docs | |
| workflow-architect clarification | software-engineer | — | Minor edit, no dependency |
| Lint + validate pass | qa-reviewer | All above | |

## Serialization Points

- Seed number assignment (220s–230s range): agree on slot allocation before authoring to avoid conflicts with existing seeds

## Affected Architecture Docs

N/A — changes are confined to specialist agent docs and seed prompts. No boundary, flow, or verification architecture impact.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core design goal — stack-tailored software-engineer |
| AC-2 | required | Role rename — frontend-developer is clearer in enterprise contexts |
| AC-2b | required | Role rename — data-engineer naming is consistent with other builder specialist names |
| AC-3 | required | Core deliverable for existing specialists |
| AC-4 | required | Workflow engines explicitly requested |
| AC-5 | required | Enterprise integration is ubiquitous in Java/.NET shops |
| AC-6 | important | Prevents role confusion at adoption time |
| AC-7 | required | Gate for merge |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-21 | Change created | Assessment: 11 enterprise-fit existing specialists, 2 new specialists, enhanced software-engineer seed |
| 2026-05-21 | ui-ux-engineer → frontend-developer rename complete | Agent doc, seed 223, seeds 050/100/160/170/180, implementer.md, specialists/README.md all updated; _BUILD_SUFFIXES already had -developer |
| 2026-05-21 | senior-data-engineer → data-engineer rename complete | Seed 224 renamed, seeds 050/100/160/170/180, implementer.md, specialists/README.md all updated |
| 2026-05-21 | Seeds 226-229, 231-233 authored for 7 existing enterprise specialists | backend-architect, software-architect, database-optimizer, security-engineer, ai-engineer, api-tester, technical-writer |
| 2026-05-21 | New specialist docs + seeds 234-235 authored | workflow-engineer.md (combined BPM arch+impl), enterprise-integration-engineer.md; seeds 234-workflow-engineer, 235-enterprise-integration-engineer |
| 2026-05-21 | workflow-architect removed; consolidated into workflow-engineer | In enterprise context, workflow-architect means BPM not CI/CD; CI/CD scope moved to devops-automator |
| 2026-05-21 | specialists/README.md updated | Enterprise archetype section, seed references, devops-automator replaces workflow-architect in universal specialists |
| 2026-05-21 | software-engineer seed (222) enhanced with stack detection | Generation-time tailoring instructions + Python/Java/C#/.NET/TypeScript skill variant blocks; project doc updated to "Senior Python Software Engineer" |
| 2026-05-21 | docs-lint: ok | All new docs and seeds pass lint |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-21 | Exclude apple-platform-engineer, mobile-app-builder, terminal-integration-specialist from this batch | Not part of stated enterprise stack | Could seed all 18; deferred to future wave |
| 2026-05-21 | Consolidate workflow-architect and enterprise-workflow-engineer into single workflow-engineer | In enterprise software, "workflow" means BPM not CI/CD; combined architect+implementer into one role; CI/CD moves to devops-automator | Keep both roles |
| 2026-05-21 | Enhance software-engineer seed with stack detection rather than creating java-backend-engineer and dotnet-engineer seeds | One role with tailored output reduces proliferation; seed is instructional, generated doc is specific | Separate language-specific specialist seeds |
| 2026-05-21 | Rename ui-ux-engineer → frontend-developer; merge frontend-developer specialist into the build role | "Frontend Developer" is the standard enterprise title; "UI/UX Engineer" implies design research scope that is typically a separate discipline in enterprise orgs | Keep ui-ux-engineer name |
| 2026-05-21 | Rename senior-data-engineer → data-engineer | All agents are experienced by definition; "senior" in the name is redundant and inconsistent with software-engineer and frontend-developer naming | Keep senior prefix |

## Risks

| Risk | Mitigation |
| --- | --- |
| Seed number collisions in 220s range | Audit existing seed numbers before authoring; allocate slots explicitly |
| Specialist doc scope creep (e.g. frontend-developer covering too many frameworks) | Keep existing docs as-is; seed reflects current scope |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
