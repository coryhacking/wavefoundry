# Qualify reviewer context isolation on native hosts

Spec ID: `24c3r-enh qualify-native-reviewer-context-isolation`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-25
Wave: 24c3o review-comprehension-isolation-and-contract-drift

## Rationale

A request for fresh context describes how a reviewer should run. It gives maintainers little evidence about what a particular host and dispatch mode actually pass to that reviewer.

## Product Intent

Maintainers can tell which tested Claude Code and Codex configurations expose parent-only context and which qualifications remain unknown.

## Requirements

1. Use a disposable synthetic project on each available native host. Record host, version, platform, dispatch mode and date. Keep normal project instructions visible. Generate a harmless unique parent-only marker absent from child inputs and an independently observable marker in an assigned artifact.
2. Ask the reviewer to read the artifact and report any parent marker it actually received, without disclosing the expected values. Compare the results outside the reviewer. Repeat with deliberate marker disclosure as a detection control. Record project-instruction visibility separately.
3. Distinguish observed disclosure, no disclosure observed under the tested conditions, inconclusive controls and unsupported or unavailable dispatch. Preserve existing per-review independence attestations. Rerun on integration changes, outside normal wave gates.

## Scope

Distinguish observed disclosure, no disclosure observed under the tested conditions, inconclusive controls and unsupported or unavailable dispatch. Preserve existing per-review independence attestations. Rerun on integration changes, outside normal wave gates.

## Acceptance Criteria

- [x] AC-1: On each named host, retain dispatch inputs, observations and the control result, or record precisely which capability could not run. Missing artifact evidence or a missed deliberately supplied marker cannot qualify a configuration.
- [x] AC-2: A reviewer that starts successfully but cannot read its assignment yields an inconclusive result. A marker seen only in the deliberate disclosure run does not taint the clean run.
- [x] AC-3: The probe uses only synthetic inputs and reports its limits. One successful run establishes no guarantee for other versions, dispatch modes or hidden context.

## Tasks

- [x] Document one repeatable manual dispatch procedure using a tiny synthetic project. Use a harmless project instruction with an observable response to check instruction visibility during the same dispatch.
- [x] For each of Claude Code and Codex, use one available native configuration. Run the ordinary dispatch and deliberate disclosure control, or record why the host is unavailable. Record the version, mode and observations in one results table.

## Agent Execution Graph

1. Implementer updates the named guidance or qualification procedure.
2. The assigned reviewer checks the observations against the acceptance criteria during normal delivery review.

## Serialization Points

- `.wavefoundry/framework/seeds/180-implement-spec.prompt.md`
- `docs/contributing/review-and-evals.md`
- `docs/agents/platform-mapping.md`

## Affected Architecture Docs

Review docs/agents/platform-mapping.md and docs/contributing/review-and-evals.md for qualification evidence.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the stated outcome or its scope boundary. |
| AC-2 | required | Establishes the stated outcome or its scope boundary. |
| AC-3 | required | Establishes the stated outcome or its scope boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-25 | Planned for wave admission. | Requirements and acceptance criteria above. |
| 2026-11-25 | Implemented the paired procedure and ran ordinary and control dispatches on both native CLI hosts. Both ordinary responses reported NONE. Both controls detected the supplied receipt and both artifact checks passed for each host. | [Tested versions, dispatch arguments, exact briefs, expected and observed receipts, instruction visibility and limits](../../contributing/review-and-evals.md#reviewer-context-qualification). Seed 180 defines how to classify a missed control, unreadable artifact or unavailable dispatch. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-25 | Qualify host configurations outside lifecycle review. | A request for fresh context describes how a reviewer should run. It gives maintainers little evidence about what a particular host and dispatch mode actually pass to that reviewer. | A self-attested fresh flag cannot detect leakage. A probe on every wave adds cost and still samples only one configuration. |

## Risks

A reviewer can overlook visible text. Deliberate disclosure tests detection and missing evidence yields an inconclusive result.

## Session Handoff

See the wave record for coordination.
