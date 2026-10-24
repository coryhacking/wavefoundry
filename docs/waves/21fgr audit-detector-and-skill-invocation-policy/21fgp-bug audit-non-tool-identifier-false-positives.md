# Suppress confirmed non-tool audit false positives

Change ID: `21fgp-bug audit-non-tool-identifier-false-positives`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-22
Wave: 21fgr audit-detector-and-skill-invocation-policy

## Rationale

Audit A8 reports fourteen stale-tool findings from the legitimate identifiers code_patterns (profile key), wf_server (Python package) and wave_record_ambiguous (error code). The scanner already has an explicit NON_TOOL_IDENTIFIERS set.

## Product Intent

Operators receive actionable stale-tool findings without being told to remove valid configuration, package paths or error names. AC-1 and AC-2 demonstrate this through the served audit response.

## Requirements

1. Add only the three confirmed non-tool identifiers to the existing exclusion mechanism. Keep scan scope, classifications, counts and response limits unchanged.
2. Preserve detection of unknown callable tool references and existing migration-name exceptions. Test through wf_audit_response rather than the exclusion set alone.

## Scope

In scope: audit identifier exclusions and regression tests. Out of scope: generic Markdown parsing, scanning new directories, user configuration, tool renames or suppressing whole prefixes.

## Acceptance Criteria

- [x] AC-1: A fixture containing realistic profile, module-path and error-code passages emits no stale_tool_reference for the three identifiers; the unchanged implementation fails this check.
- [x] AC-2: The same public audit fixture still reports a deliberately nonexistent callable tool name, with correct project/pack classification and totals; removing detection makes the assertion fail.
- [x] AC-3: Focused audit regressions and the canonical framework suite pass, with independent delivery review and full docs validation.

## Tasks

- [x] T-1: Add producer-shaped audit regression fixtures and confirm the prior behavior fails.
- [x] T-2: Extend the existing non-tool identifier exclusions.
- [x] T-3: Run focused tests, independent review, framework suite and docs validation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | readiness | Single writer |
| Verification | independent reviewer lanes | implementation | Frozen source; public-path and known-bad checks |

## Serialization Points

Coordinator owns records; implementer owns the following files only. Generated surfaces must come from their owning renderer.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

## Affected Architecture Docs

N/A: a bounded exclusion correction within the existing scanner changes no architectural boundary or response schema.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the bounded correction and preservation contract |
| AC-2 | required | Establishes the bounded correction and preservation contract |
| AC-3 | required | Establishes the bounded correction and preservation contract |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-22 | Planned from current audit and inspected owning source; no implementation edits. | Audit findings and declared source paths |

| 2026-10-22 | Readback: extend only the existing exact non-tool exclusions for code_patterns, wf_server and wave_record_ambiguous; public audit fixtures must still detect a fake callable and preserve classification/counts (AC-1/2). Source/test paths are the declared scanner and server-tool tests. Memory advisories reviewed; no lifecycle or response-schema edit. | Example: valid package path currently flags stale; afterward it clears while wf_totally_retired_tool still flags |

| 2026-10-22 | Public wf_audit_response regression initially failed (8 findings versus expected 2). After exact three exclusions, all four HarnessCoherencePackTextTests pass. Four in-memory mutants detected by test_public_audit_distinguishes_non_tool_identifiers_from_stale_calls: removing each exclusion yields 4 versus 2; hiding the fake callable yields 0 versus 2. Actual scanner and response path exercised; unrelated lint/index readiness legs isolated in fixture. The focused runner refused before executing tests because concurrent Prepare publication held the observation lock beyond its bounded window; this is no test-failure result. Final canonical suite/review will run after source/publication freeze. | /private/tmp/wf-audit-remediation/a8-before.log, a8-focused.log and a8_mutants.py |

| 2026-10-22 | Final canonical run completed red: 12,072 tests across206files,12skips,1056.567s. All five original failing files now pass. Two other files fail: registered reload ownership reports second writer; TechDocs escaping-symlink fixture lacks unsafe_survivor_targets. Fresh independent QA/code/security/docs reviews found no new admitted-scope blocker; repaired findings are terminal, but delivery approvals and qualification ACs remain pending the required green suite. No test waiver, threshold change or unchanged retry. | /private/tmp/wf-audit-remediation/canonical-final.log; final-code-architecture-review.md; final-security-review.md; fresh-qa-docs reports; final-source-preservation.json |

| 2026-10-23 | Qualification completed after the operator-requested retry: canonical suite passes12,072tests across206files with12existing skips in648.998s; a fresh green receipt is recorded. Both formerly failing files pass. Reviewed implementation fingerprints unchanged. All specialist delivery approvals are current, all required ACs/tasks met, changes implemented. Operator signoff and closure remain pending; no commit or close performed. No new memory candidate warranted: bounded lessons remain in canonical tests/guidance and existing records. | .wavefoundry/framework/scripts/run_tests.py; /private/tmp/wf-audit-remediation/canonical-requested-requalification.log; typed delivery approvals and post-requalification-source-check.json |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-22 | Use the existing explicit exclusion set | Smallest bounded correction | Broad parser or host abstraction redesign is outside scope |

## Risks

| Risk | Mitigation |
| --- | --- |
| Overbroad suppression could hide genuine stale tools | Public-path regressions and independent review |

## Session Handoff

Prepare before source edits. Implement, review and pause; no commit or closure authorized.
