# Wave Template Validation Conformance

Owner: Engineering
Status: complete
Last verified: 2026-05-25
Verification method: validator review against `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`

## Change ID

Change ID: `1p0r6-maint wave-template-validation-conformance`

Wave: `12wsj framework-cleanup`

## Rationale

The repository’s checked-in change and wave artifact templates are partially behind the live wave-validation contract. The validator currently requires checkbox Acceptance Criteria, a structured `## AC Priority` table, an H1 title for admitted change docs, and specific wave-record sections, but the canonical template surfaces do not describe all of that cleanly. Leaving the templates stale increases the chance that new wave artifacts will fail validation or require repair after admission.

## Product Intent

Keep the repository’s template surfaces aligned with the actual wave-validation contract so newly created change docs and wave artifacts conform on first use rather than relying on later upgrade or lint repair.

## Design Intent

Design Intent: N/A — no UI surface changes.

## Requirements

1. Review all wave-related template surfaces that influence creation of change docs or wave artifacts.
2. Update the checked-in change-doc template so it reflects the current validation contract for admitted change docs.
3. Update the wave artifact contract doc so it reflects the current validation contract for active and baseline wave records.
4. Update every checked-in planning/template surface that restates the change-doc scaffold so it matches the live template requirements.

## Decision Refs

Decision refs:

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`

## Scope

Problem statement:

- The repository’s checked-in wave/change templates no longer fully match the live validator contract.

**In scope:**

- `docs/plans/plan-template.md`
- `docs/waves/README.md`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`
- `docs/prompts/plan-feature.prompt.md`
- `docs/prompts/add-change-to-wave.prompt.md`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/prompts/agents/prepare-wave.prompt.md`
- `docs/prompts/review-wave.prompt.md`
- `docs/prompts/agents/review-wave.prompt.md`
- `docs/contributing/feature-workflow.md`
- `docs/references/project-overview.md`
- `.wavefoundry/framework/scripts/server_impl.py`

**Out of scope:**

- Repo-local active wave records other than any minimal coordination updates needed for this admission
- Product source files
- Broad seed-prompt cleanup outside the template contract

## Acceptance Criteria

- [x] AC-1: `docs/plans/plan-template.md` reflects the current admitted-change validation contract, including checkbox AC syntax and an `## AC Priority` table scaffold.
- [x] AC-2: `docs/waves/README.md` describes the current required wave-record anchors and sections used by the validator for active and baseline waves.
- [x] AC-3: The checked-in planning and admission prompt surfaces that restate the scaffold use the same checkbox-AC, AC-priority, and ID-format contract as the template.
- [x] AC-4: `docs-lint` passes after the template updates.

## AC Priority

| AC | Priority | Description | Rationale |
| --- | --- | --- | --- |
| AC-1 | required | `docs/plans/plan-template.md` matches the live admitted-change validation contract | This is the primary scaffold used for new change docs |
| AC-2 | required | `docs/waves/README.md` documents the current wave-record validation contract | The wave artifact contract must match actual validator expectations |
| AC-3 | required | The checked-in planning and admission prompt surfaces match the same template contract as the checked-in template | Future planning and admission flows should not reintroduce stale scaffold guidance |
| AC-4 | required | `docs-lint` passes after the updates | Validation is the acceptance proof for the conformance work |

All ACs are Required.

## Tasks

- [x] Audit the validator-required sections and syntax for admitted change docs and wave records.
- [x] Update `docs/plans/plan-template.md`.
- [x] Update `docs/waves/README.md`.
- [x] Update the seeded and checked-in planning/admission docs that restate the scaffold contract.
- [x] Run `docs-lint` and `git diff --check`.

## Agent Execution Graph

| Workstream | Primary Agent | Scope | Depends On | Can Run In Parallel With | Deliverable |
| --- | --- | --- | --- | --- | --- |
| Validator audit | docs-contract-reviewer | extract current wave-validation requirements from validator code | none | none | required-contract checklist |
| Template updates | implementer | align change and wave template surfaces with validator contract | validator audit | seed alignment | updated template docs |
| Seed alignment | workflow-engineer | align planning seed contract with updated templates | validator audit | template updates | updated planning seed |
| Verification | qa-reviewer | docs gate and diff hygiene | template updates | none | clean validation pass |

## Serialization Points

- Finalize the validator-derived contract before editing any template file.
- Update the checked-in template and the planning seed in the same effort so they do not diverge again.

## Affected Architecture Docs

N/A — this work changes docs/workflow templates only.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-25 | Admitted template-conformance work into wave `12wsj framework-cleanup` | Validator review and operator request |
| 2026-05-25 | Partial progress landed: `docs/plans/plan-template.md` and some planning surfaces reflect the current validator contract, and docs-lint passes. `docs/waves/README.md` and the full prompt/seed/template surface set still need reconciliation. | `docs/plans/plan-template.md`, `docs/prompts/plan-feature.prompt.md`, `python3 .wavefoundry/framework/scripts/docs_lint.py` |
| 2026-05-25 | Completed the remaining template-contract reconciliation: refreshed `docs/waves/README.md`, aligned the bootstrap/planning seed wording, and updated the local workflow overview surfaces to the live validator and admission contract. | `docs/waves/README.md`, `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`, `docs/contributing/feature-workflow.md`, `docs/references/project-overview.md`, `python3 .wavefoundry/framework/scripts/docs_lint.py`, `git diff --check` |

## Decision Log

| Date | Decision | Reason | Alternatives Rejected |
| --- | --- | --- | --- |
| 2026-05-25 | Keep the scope focused on template and planning surfaces that directly define or restate the wave/change scaffold contract | This fixes validator drift at the source without broadening into unrelated prompt cleanup | Editing only one template file and leaving contradictory scaffold instructions elsewhere |

## Session Handoff

- If unfinished, resume with the validator-derived checklist first, then patch the three in-scope surfaces together.

## Risks And Mitigations

- Risk: updating the checked-in template without the planning seed could reintroduce scaffold drift.
- Mitigation: update both surfaces in the same change.
- Risk: overfitting templates to repo-local examples rather than the actual validator.
- Mitigation: derive requirements directly from `wave_validators.py` and `constants.py`.

## Completion Notes

- This change is for template conformance only.
- The checked-in template and planning/admission surfaces now match the current validator contract for checkbox ACs/tasks, AC priority, and wave-record anchors.
