# Constrain reconciliation Git query execution

Change ID: `20nno-bug bounded-literal-git-queries`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-14
Wave: `20nnk distribution-status-fixtures`

## Rationale

reconcile_scan._git_run currently invokes Git with the inherited environment and repository configuration, while _git_ignored sends repository names directly to check-ignore. These boundaries should implement metadata queries with literal names while preserving intentional ignore behavior and truthful incomplete results.

## Requirements

1. Run the scanner's Git query family through one bounded helper with inherited GIT_* routing/config variables removed and command-executing Git features reachable by those queries disabled, including core.fsmonitor.
2. Treat every supplied repository path literally, including punctuation, leading colon syntax and unusual whitespace, preserving NUL framing and exact result membership.
3. Preserve supported repository/worktree discovery and intended ignore sources. Inventory configuration read by the two queries; document any intentional trust/ignore-policy boundary rather than silently discarding all ignore configuration.
4. Keep existing time, input/output size, process-tree cleanup and fail-closed incomplete/error status; never convert Git failures into a clean scan or uncontrolled fallback.
5. Test only disposable repositories with harmless local markers; no real user configuration changes or disclosure of paths/content.

## Scope

reconcile_scan Git helper/query callers, bounded scratch tests and scanner trust documentation. No global Git environment rewrite, user Git configuration change or new upgrade phase.

## Acceptance Criteria

- [x] AC-1: Scratch query controls show that configuration-driven helper execution and inherited repository/config redirection cannot change the intended query target.
- [x] AC-2: Literal unusual filenames receive the same ignore answer as an independent literal-path oracle and do not omit eligible files or fail solely due to pathspec interpretation.
- [x] AC-3: Normal ignore rules, required host surfaces and linked worktree discovery preserve expected scanner scope.
- [x] AC-4: Timeout, invalid output, unavailable Git and size-limit controls still produce truthful incomplete/error outcomes and bounded owned-process cleanup.

## Tasks

- [x] Inventory query-specific Git command/config reachability and choose minimal suppression preserving ignore semantics.
- [x] Implement sanitized environment and literal-path handling in the shared bounded helper.
- [x] Add disposable-repository regression controls and document query trust/compatibility limits.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | Readiness approval | Sole source write owner |
| Independent review | Required specialist lanes | Reviewable implementation | Read-only; report findings to coordinator |

## Serialization Points

Only the implementer edits the declared targets after readiness. Reviewers are read-only; the coordinator owns lifecycle records. Shared runner, server, policy, seed and prompt changes serialize with adjacent waves. Seed/default/prompt changes require existing edit guards and renderer ownership; do not hand-edit generated regions.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/architecture/cross-cutting-concerns.md`

## Affected Architecture Docs

docs/architecture/cross-cutting-concerns.md and the upgrade seed's scanner trust section: constrained Git query execution.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-2 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-3 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-4 | required | Establishes the scoped behavior or preserves its boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Planned from current source inspection; implementation and qualification pending. | Requirements and declared review targets above. |

| 2026-10-14 | Readback: Restrict reconciliation Git queries to a sanitized Git environment, disabled fsmonitor and literal pathspecs. Before, repository config or magic-shaped names can alter query execution/membership; after, literal target paths preserve normal ignore/worktree behavior under existing deadlines, output caps and fail-closed handling. | reconcile_scan.py, existing scanner tests, seed 160 and admitted threat-model docs; no target Git configuration writes. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Select query-local environment sanitization, explicit command-feature suppression and literal path semantics. | Make scanner Git queries literal, bounded and independent of inherited command-routing settings. | Ignore Git entirely: loses required project exclusions and repeats generated scanning. Require trusted configuration only in documentation: retains avoidable behavior in metadata queries. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Contract regression or scope expansion | Over-sanitizing can change intended ignore rules or linked-worktree discovery. Use behavior comparisons for supported layouts and document configuration choices. |

## Session Handoff

Planned only. Prepare/readiness must pass before code edits. Keep durable decisions and final command/results in wave.md; compact execution detail stays in ignored cache or temporary storage. No new permanent evidence folder. See docs/agents/session-handoff.md for sequencing.
