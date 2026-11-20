# Qualify renamed distributions for v1.45.0

Change ID: `23uxi-bug renamed-profile-release-qualification`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23ve4 repair-renamed-profile-qualification

## Rationale

Release qualification at 6f505ee9 recorded 26 failures and errors in 11 test files under the second profile. The default and declared profiles passed. A manifest symlink also caused the lifecycle drift report to abort under the second profile.

## Product Intent

Distribution maintainers can rely on the release checks to exercise their effective prompt names, skill registry and lifecycle diagnostics while preserving existing project registrations and repository containment.

## Requirements

1. Resolve names using the active checkout and distinguish existing registrations from defaults for an empty checkout. Keep explicit overrides and reject invalid registrations under the same documented rules across profiles.
2. Preserve containment on manifest reads and the drift report's established handling of unavailable baseline data. Check every failure from the second-profile report against the contract before deciding whether the implementation, qualification setup or test expectation needs repair.
3. Exercise the same behavioral assertions under default, renamed and declared configurations. Preserve negative controls, required source fixtures and the release gates.

## Scope

The affected lifecycle, vocabulary, rendering and qualification paths and their tests. Packaging policy, downstream source edits and unrelated feature changes are outside this repair.

## Acceptance Criteria

- [x] AC-1: A renamed checkout with a manifest linked outside the repository returns the established drift outcome without reading the external file. A valid manifest still supports drift detection.
- [x] AC-2: Tests through normal lookup and render paths distinguish project-retained names from fresh defaults, follow manifest edits, exercise collisions and invalid input, and report lifecycle status using the active vocabulary.
- [x] AC-3: Account for all 26 baseline failures. Full default, second and declared qualification and required report comparisons pass on the release candidate without new skips, exceptions or reduced coverage to evade a failure.

## Tasks

- [x] Classify the failing assertions and reproduce product defects and incorrect fixture assumptions.
- [x] Repair affected readers and test arrangements, then replay focused positive and negative controls.
- [x] Run full release qualification and compare the results.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Repair | Implementer | Readiness | Group by root cause |
| Verify | QA | Repair | Exercise public paths and compare profiles |

## Serialization Points

- `.wavefoundry/framework/scripts/`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

Review the testing architecture if qualification behavior changes. Existing distribution and containment contracts govern the repair.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserve repository containment and report availability |
| AC-2 | required | Verify downstream behavior |
| AC-3 | required | Qualify the release |

## Progress Log

At 6f505ee9 the second-profile run reported 19 failed assertions and seven errors across 11 files. The fixes address these groups:

| Baseline failures and errors | Repair and evidence |
| --- | --- |
| 1 lifecycle baseline report | Read one contained manifest for the comparison. A refused target produces no external read and the report still identifies independent local drift. |
| 3 synthetic skill registry cases | Inject invalid or future skills at the registry used by the public renderers. Ordinary collision cases use each checkout’s real registry. |
| 12 source-carrier checks across language guidance, readiness, rendering and reconciliation | Resolve the existing checkout’s registered names before reading its prompts and generated roles. Preserve required source fixtures and negative controls. |
| 2 MCP tool index checks | Compare the registered first sentence against the documented summary in the active vocabulary. Changing a substantive phrase still fails. |
| 2 migration and install checks | Check the existing prompt’s registered path after rendering. Keep the missing-link and missing-file controls. |
| 5 lifecycle status and lookup cases | Verify the configured document names, refusal and unchanged state. Exercise lookup on the same cache before and after editing a manifest. |
| 1 vocabulary validation case | The shipped profile rejects the incomplete planning override. Custom vocabulary supplies the inherited shortcut. |


The final default and declared runs each passed 13,080 tests. The renamed run passed 13,058. All three covered 251 files. Both qualification comparisons passed with the baseline skips preserved. An earlier concurrent run exceeded a timing budget. The standalone default run passed on the same candidate.

## Decision Log

Use the existing three-profile qualification. A waiver would leave the confirmed drift-report regression in the release.

## Risks

A test could repeat the implementation's mistake. Use independent expected values for legacy registrations, fresh defaults and malformed inputs.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
