# The Harnessability Audit Reports the Best Debt Score When Its Scan Fails

Change ID: `1zilz-bug audit-debt-score-scan-failure`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-30
Wave: 1zim2 local-surface-hardening

## Rationale

From a downstream report (verified 2026-09-30): `_audit_harnessability` in `wf_server/server_impl.py` runs `git grep -c -E 'TODO|FIXME|HACK|XXX'` through `_mcp_subprocess_run` and never reads the return code. In a directory that is not a git repository, or one git refuses (dubious ownership, exit 128), stdout is empty, the count is 0 and `debt_score` becomes `"high"`, the best score, so `wf_audit` overstates the target. A missing git already raises into the existing `except` and reports `"unknown"`.

## Requirements

1. **Fail closed.** Return code 0 counts matches as today; return code 1 (no matches) is a count of 0 and `"high"`; any other code gives `debt_score` `"unknown"` with evidence naming the exit code and the first line of stderr. The existing exception path names the exception in its evidence. No additional subprocess call is added (a test pins exactly one in this function).
2. **Overall score.** The existing rule already excludes `unknown` dimensions from the average; that stays.
3. **Platforms.** Windows, macOS, Linux and WSL2 behave the same.
4. **Transition.** CHANGELOG under `### Fixed` in `## [Unreleased]`.

## Scope

**Problem statement:** a failed debt scan is reported as the best possible score.

**In scope:**

- `_audit_harnessability` debt block; tests; CHANGELOG.

**Out of scope:**

- Other audit dimensions.

## Acceptance Criteria

- [x] AC-1: in a temporary non-git directory (with `GIT_CEILING_DIRECTORIES` set so no parent repository is found) the audit reports `debt_score` `"unknown"` with the exit code in its evidence; a git repository with tracked files and no markers reports `"high"`; one with tracked markers reports by count as today.
- [x] AC-2: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Read the return code; name the exception in the fallback evidence.
- [x] Tests (real temporary directories).
- [x] CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Audit fix | implementer | readiness | |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`

## Affected Architecture Docs

N/A.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect |
| AC-2 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Implemented. The debt block reads `result.returncode`: 0 and 1 count as before (1 gives 0 and "high"); any other code gives "unknown" with `git grep exited <code> (<first stderr line>)`; the exception fallback names the exception type. Still exactly one `_mcp_subprocess_run` call. CHANGELOG `### Fixed` | `test_server_tools.HarnessabilityDebtScanFailureTests` (4 tests, real temp dirs, `GIT_*` scrubbed, `GIT_CEILING_DIRECTORIES` set, `git add` for tracked markers). Mutation: returncode check disabled, non-git test fails. Focused: server_tools 375 OK, tree_kill_routing 32 OK (one-call pin) |
| 2026-10-01 | Implementation note from readiness: the audit tests also scrub `GIT_DIR` | Readiness review |
| 2026-09-30 | Readiness round 1: approved; notes folded in: no extra subprocess (one call pinned by `test_tree_kill_routing`), exception named in evidence, `GIT_CEILING_DIRECTORIES` and tracked marker files in tests | Prepare council and lane review |
| 2026-09-30 | Planned from a downstream report, verified: the debt block computes the count from stdout only and never checks `returncode` | Code read |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Unknown rather than an error | The audit reports, it does not fail | Raise |

## Risks

| Risk | Mitigation |
| --- | --- |
| A git that prints warnings with exit 0 | Only the exit code decides |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
