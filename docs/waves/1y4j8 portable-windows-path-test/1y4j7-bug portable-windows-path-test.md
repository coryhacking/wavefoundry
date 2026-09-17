# Portable Windows path comparison test

Change ID: `1y4j7-bug portable-windows-path-test`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-16
Wave: 1y4j8 portable-windows-path-test

## Rationale

The Windows quoted-indexer-root test constructs concrete Path objects while globally mocking os.name to nt. On macOS Python 3.11 this raises NotImplementedError before comparison, so use pure Windows path values to exercise the Windows string-comparison branch without requiring a Windows filesystem. The unchanged named test passes on macOS Python 3.13.5; the report's universal/non-version-dependent claim is therefore not supported. Preserve the positive and negative assertions and production behavior.

## Requirements

1. Import PureWindowsPath and replace only the two Windows root operands in BackgroundRefreshActiveTests.test_windows_quoted_indexer_root_is_compared_case_insensitively.
2. Keep quoted command parsing, case-insensitive matching and different-root rejection covered without platform-specific concrete filesystem paths.

## Scope

In scope: one test-file import and two operand replacements; focused verification and accurate interpreter/platform evidence.
Out of scope: production code, dependency changes, runner redesign, skips, compatibility claims for unexecuted native platforms, commit and closure.

## Acceptance Criteria

- [x] AC-1: The quoted Windows test uses PureWindowsPath for both root operands and retains matching-root true / other-root false assertions.
- [x] AC-2: The corrected test exercises the real comparison function without concrete WindowsPath construction; the original operands reproduce the Python 3.11 failure and corrected operands pass under Python 3.11 and 3.13 on macOS.

## Tasks

- [x] Apply the bounded import and operand substitutions after readiness.
- [x] Run focused before/after controls and available test class; record fixture/runtime limitations.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness and verification | independent code/QA reviewer | — | Lightweight red-team critique before review; no production changes |
| Test fixture repair | coordinator | readiness | Three-line source delta |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`

## Affected Architecture Docs

N/A: test data representation only; no production, test-runner or architecture boundary change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the platform-dependent fixture construction without weakening assertions |
| AC-2 | required | Demonstrates failure detection and retained comparison behavior on available interpreters |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-16 | Named unmodified test passes Python 3.13.5 on macOS; direct Path construction under mocked nt fails Python 3.11. Full 3.11 fixture is blocked by shared tool-venv interpreter mismatch, so isolate exact test method and production function if needed without claiming full fixture coverage. | Local interpreter probes and named unittest |

Closure update2026-09-16: operator subsequently authorized closing this wave, superseding the original planning-only scope/handoff wording. The unchanged test fix was included in the green9104-test full suite, with current matching framework receipt. Required reviews and all AC/tasks are complete.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-16 | Use PureWindowsPath | Explicit Windows lexical semantics, no filesystem support requirement | Preconstruct Path before patch leaves host-native semantics implicit; skip on non-Windows loses useful cross-platform coverage |

## Risks

| Risk | Mitigation |
| --- | --- |
| Mistake a patched platform flag for native Windows qualification | Record macOS Python versions and isolated fixture limits; native Windows remains unexecuted |

## Session Handoff

See docs/agents/session-handoff.md. Test-only implementation complete; wave remains open, with no commit or closure requested.

Implementation: exactly one import and two operands changed after successful Prepare. Full BackgroundRefreshActiveTests class passed on macOS Python3.13.5: 13 tests, no skips. Git diff whitespace clean; no production changes. Framework edit gate closed. Gapfill: coordinator used the operator-provided exact test location for a mechanical patch; independent reviews used MCP reads of the test and production consumer.

Final executed regression matrix (independent reviewer, exact test method and actual production function extracted from final tree; fixture setup/server loading omitted):

| Interpreter on macOS | Corrected operands | Restored original operands | Always-true / always-false comparison |
| --- | --- | --- | --- |
| Python 3.11.13 | pass | NotImplementedError | both AssertionError |
| Python 3.13.5 | pass | pass | both AssertionError |

No skips; os.name restored after each cell. Native Windows and full Python3.11 fixture remain unexecuted. Full Python3.13 class passed all13 tests. Full framework suite not rerun for this narrow test-only edit; existing receipt is stale and must be refreshed before closure.
