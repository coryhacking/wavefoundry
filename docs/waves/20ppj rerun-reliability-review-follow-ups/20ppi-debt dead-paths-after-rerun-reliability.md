# Preserve recovery and compatibility paths after rerun reliability

Change ID: `20ppi-debt dead-paths-after-rerun-reliability`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20ppj rerun-reliability-review-follow-ups`

## Rationale

Readiness source controls corrected the original dead-path premise. `check_version.read_installed_version` falls back to VERSION when the manifest revision is absent; ordinary same-build preflight therefore already refuses that case. A stale manifest revision takes precedence, and validated retained recovery bypasses the ordinary refusal. The extract-phase `_tree_already_at` guard remains reachable and protects those paths from destructive re-extraction.

`lane_has_signoff_in_evidence` deliberately accepts an ignored `authorization` keyword for compatibility, and `test_review_evidence` already passes it. This change now pins these boundaries with focused regression coverage and accurate guidance instead of deleting reachable safeguards or changing a public helper's call shape.

## Requirements

1. Preserve the ordinary same-full-build preflight refusal and the extraction guard for validated retained recovery and stale-manifest/target-VERSION cases. Missing manifest revision continues to fall back to VERSION through the existing reader; no second policy or new receipt is introduced.
2. Enumerate and test ordinary preflight, missing-revision fallback, stale-manifest precedence and retained docs-gate retry. Keep `_tree_already_at` wherever these proven paths need it; a tree already at target must never be destructively re-extracted.
3. Retain the explicit `authorization` compatibility keyword and document its ignored meaning. Verify None, False and True preserve identical explicit-state authority and never enable free-prose approval. Do not introduce `**_ignored` or accept arbitrary unknown keyword arguments.
4. Limit runtime edits to a demonstrated discrepancy with these preserved contracts; otherwise deliver regression coverage and documentation only. Windows, macOS, Linux and WSL2 semantics remain unchanged; local fixtures do not establish native platform qualification.

## Scope

**Problem statement:** apparent dead paths are reachable recovery and compatibility safeguards; protect them against an unsafe cleanup.

**In scope:**

- Regression coverage and accurate guidance for the extract-phase `_tree_already_at` branch and the preflight same-build decision in `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- The `authorization` parameter of `lane_has_signoff_in_evidence` in `.wavefoundry/framework/scripts/review_evidence.py`
- Tests referencing either

**Out of scope:**

- Changing the same-build refusal policy that `20qvm` established
- Any change to signoff parsing rules

## Acceptance Criteria

- [x] AC-1: Ordinary same-build refusal, missing manifest revision falling back to VERSION, stale manifest precedence and validated retained-recovery bypass are exercised through actual source with exact outcomes.
- [x] AC-2: A retained docs-gate retry and stale-manifest/target-VERSION path preserve an existing tree byte-for-byte through extraction; `_tree_already_at` remains where required by these reachable paths.
- [x] AC-3: Explicit `authorization=None`, False and True preserve the same approved/pending/free-prose results; the named keyword remains accepted and arbitrary unknown keywords remain rejected.
- [x] AC-4: The change's own suites and every test it adds pass; authored or edited documents validate; no failure elsewhere is attributable to this change.

## Tasks

- [x] Record the proven ordinary and retained preflight-to-extraction reachability in the Decision Log.
- [x] Add or retain focused missing/stale-manifest and retained docs-gate retry regressions without removing the extraction guard.
- [x] Pin explicit ignored-keyword compatibility and accurate docstring guidance; no parser or arbitrary-keyword policy change.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Upgrade branch | Implementer | Readiness | Single write owner |
| Review-evidence parameter | Implementer | Readiness | Same owner; independent file |
| Delivery review | QA and required reviewers | Both | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A. Preserves existing recovery and compatibility semantics; no boundary, flow or verification seam changes. The upgrade seed's same-build wording from `20qvm` already describes the surviving policy.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserve actual preflight decisions |
| AC-2 | required | Must not lose the `1p44r` guarantee |
| AC-3 | important | Existing caller compatibility |
| AC-4 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from the code review of `43621e07` | Review finding 9 |
| 2026-10-15 | Clarification of the keyword decision: the `authorization` keyword is retained because `lane_has_signoff_in_evidence` is a public helper whose external callers may pass it. The existing test passing it is evidence of use, not the reason for keeping it. | Cross-wave plan review; no requirement or AC changed |

| 2026-10-15 | Readback: preserve extraction guard and explicit ignored authorization keyword; add actual preflight/extraction and helper compatibility regressions. AC-1/2/3; focused tests only unless discrepancy found. No parser-policy change. | Admitted plan and current-source MCP reads |

| 2026-10-15 | Focused controls passed: root follow-ups, rerun, retained docs-gate retry, scope and container-status controls: 44 tests / 0 skips. In-memory mutants restored the unbound import, repeated discovery and missing extraction guard; each targeted test detected its defect. Final combined qualification remains pending. | test_rerun_followups; test_upgrade_rerun_reliability; ResumeAfterGateTests; OpenContainerScopeTests; ContainerStatusContractTests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | One debt change for both leftovers | Both are cleanup from the same commit and are small | Two changes (rejected: overhead) |
| 2026-10-15 | Readiness correction: retain the reachable extraction guard and explicit ignored keyword | Actual source proves retained recovery and stale-manifest paths; an existing test passes the keyword | Unconditional deletion rejected as a regression; broad ignored kwargs rejected as unnecessary API expansion |

## Risks

| Risk | Mitigation |
| --- | --- |
| The extract-phase branch protected a retry path preflight does not see | Task 1 enumerates reachability before deletion; AC-2 keeps the idempotence test |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

## Readiness correction

PPJ-R2 narrows the original cleanup proposal to compatibility and recovery regression coverage. The original deletion premise was falsified by actual-source controls; no implementation started.
