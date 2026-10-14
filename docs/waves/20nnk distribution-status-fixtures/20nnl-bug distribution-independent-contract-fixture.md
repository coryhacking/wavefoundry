# Make the declared contract fixture independent of shipped wording

Change ID: `20nnl-bug distribution-independent-contract-fixture`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-14
Wave: `20nnk distribution-status-fixtures`

## Rationale

DeclaredLegacyReviewPlanTests builds its pack by replacing one exact empty declaration line. Source inspection confirms the fixture silently depends on the shipped declaration's formatting and value. The fixture should install its own known contract without editing the live checker.

## Requirements

1. Construct the fixture's declaration deterministically without requiring the empty default assignment text; the example must take effect in the copied incoming module before its relevant entry path executes.
2. Isolate checker, renderer and incoming-hook expectations from live distribution declarations while preserving all three actual execution paths.
3. Preserve malformed, duplicate, ambiguous and customized-contract refusal coverage, and leave repository source and original pack inputs unchanged outside the fixture.
4. Use neutral example vocabulary; no default-only skip, live declaration reset or distribution-specific exemption.

## Scope

DeclaredLegacyReviewPlanTests and directly shared fixture helpers/tests only. No production migration relaxation or declaration API change.

## Acceptance Criteria

- [x] AC-1: The registered fixture succeeds with both empty and nonempty preexisting declarations and does not depend on the literal default assignment or its formatting.
- [x] AC-2: Installed checker, renderer and incoming hook consume the same fixture-owned declaration and preserve expected project prose/line endings.
- [x] AC-3: Malformed or ambiguous contracts still refuse, and controlled runs leave live source and original declarations unchanged.

## Tasks

- [x] Replace literal-dependent fixture setup with an explicit fixture-owned override effective at incoming execution.
- [x] Add nonempty/reformatted-source controls and replay installed/renderer/incoming paths.
- [x] Record the regression result and fixture boundaries in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | Readiness approval | Sole source write owner |
| Independent review | Required specialist lanes | Reviewable implementation | Read-only; report findings to coordinator |

## Serialization Points

Only the implementer edits the declared targets after readiness. Reviewers are read-only; the coordinator owns lifecycle records. Shared runner, server, policy, seed and prompt changes serialize with adjacent waves. Seed/default/prompt changes require existing edit guards and renderer ownership; do not hand-edit generated regions.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`

## Affected Architecture Docs

N/A: test-fixture repair only; production extension and migration contracts remain unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-2 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-3 | required | Establishes the scoped behavior or preserves its boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Planned from current source inspection; implementation and qualification pending. | Requirements and declared review targets above. |

| 2026-10-14 | Readback: Replace exact-empty-line fixture substitution with fixture-owned example declaration independent of live declaration formatting/content. Before, a nonempty distribution declaration silently defeats substitution; after, checker, renderer and incoming hook receive the intended isolated example while malformed and ambiguous controls remain. | AC-1 through AC-3; tests/test_upgrade_wavefoundry.py only, no production behavior change. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Select a fixture-owned assignment placed before module execution reaches any entry-point invocation, with live declarations patched explicitly in test scope. | Keep the incoming-pack legacy-contract test valid when a distribution already declares custom profiles. | Match the shipped literal more loosely: still depends on formatting. Change production defaults or skip declared distributions: hides the fixture defect. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Contract regression or scope expansion | Appending after a main invocation can be too late. Validate execution order in both imported incoming hooks and any direct script fixture path. |

## Session Handoff

Planned only. Prepare/readiness must pass before code edits. Keep durable decisions and final command/results in wave.md; compact execution detail stays in ignored cache or temporary storage. No new permanent evidence folder. See docs/agents/session-handoff.md for sequencing.
