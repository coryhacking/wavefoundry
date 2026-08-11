# Rollback-Failure Detail Embeds Absolute Paths That Defeat The Leak Helper

Change ID: `1v0ly-bug rollback-failure-detail-embeds-absolute-paths`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-10
Wave: 1uzwh artifact-read-fail-closed

## Rationale

`1uu9z` closed the absolute-path leak class by routing read-failure messages through `_read_error_detail`, which renders `strerror` for `OSError` because `OSError.__str__` embeds the path. One producer defeats the helper by construction: `_replace_artifacts_transactionally` raises a **synthetic single-arg** `OSError(detail)` whose `detail` joins `rollback_errors` entries of the form `f"{path}: {rollback_exc}"` — absolute paths, twice over (the entry's own path plus the embedded exception's). A single-arg `OSError` has `strerror is None`, so the helper falls through to verbatim and the publish handler at the `review_policy_receipt_stale` site renders the paths.

Readiness-council correction (2026-08-10): the leak is not double-fault-only. The detail head, `f"receipt publication failed: {exc}"`, embeds the original `OSError.__str__` (which carries the absolute path) on **every** publication failure, including the common case where rollback succeeds and `rollback_errors` is empty. The double-fault merely adds more paths; the head leaks alone.

Found by the delivery code lane at `1uwpf` reverification, dispositioned there as out of scope (a write/rollback double-fault, not a document read). The lane also named the fix: **at the raise site**, not in the helper — the helper's verbatim fall-through is correct for genuinely message-only exceptions, and special-casing it would hide information for exception shapes that carry none of their own.

## Requirements

1. **The whole `detail` renders path-free, head included.** The raise site composes both the head (the original exception rendered via `_read_error_detail`, not `str`) and the `rollback_errors` entries from `_repo_rel(...)`-rendered paths and cause text, with no embedded absolute path. For a path outside the repository root, where `_repo_rel`'s fallback still raises `ValueError`, the composition renders the final path component only: diagnosability keeps the artifact name, never the absolute prefix.
2. **The double-fault remains fully diagnosable.** The entry still names which artifact failed to roll back and why; only the path form changes.
3. **`_read_error_detail` is untouched.** The helper's contract stands as `1uu9z` shipped it.

## Scope

**Problem statement:** one synthetic-exception producer re-leaks the paths the leak helper exists to strip, on every failed publish; worst on the double-fault path where the rollback errors join in.

**In scope:** the `raise OSError(detail)` composition in `_replace_artifacts_transactionally` (`server_impl.py`); a red-first test.

**Out of scope:** `_read_error_detail` itself; any change to when the transaction raises; the TOCTOU reachability of the publish handler (recorded in `1uu9z`).

## Acceptance Criteria

- [x] AC-1: A forced rollback double-fault produces a `detail` containing repo-relative paths and no absolute path, reproduced **red-first** with the raise site exercised directly (the publish-handler reachability is TOCTOU-only and stays untested, per the `1uu9z` disposition pattern).
- [x] AC-2: A single-fault publication failure (rollback succeeds, `rollback_errors` empty) produces a `detail` with no absolute path, reproduced **red-first**: today the head embeds the original `OSError.__str__`. The common path gets its own regression test, not incidental coverage from the double-fault fixture.
- [x] AC-3: The detail still names the artifact and the cause, in both fault shapes.
- [x] AC-4: `_read_error_detail`'s contract is pinned behaviorally, not source-textually (the `1upba` lesson: a source-literal pin also pins syntax and its equality half tautologizes): subTests assert strerror rendering for a real `OSError` and verbatim fall-through for a synthetic single-arg one, unchanged before and after.
- [x] AC-5: The full framework suite and docs-lint pass.

## Tasks

- [x] Red-first tests at the raise site: the double-fault and the single-fault head leak.
- [x] Compose `detail` path-free (head and entries); run the suite and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | Direct raise-site exercise |
| fix | implementer | red-test | Raise-site composition only |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

## Affected Architecture Docs

`N/A` with rationale: message composition only; no boundary, flow, or gate change.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect on the double-fault path. |
| AC-2 | required | The defect on the common path; previously unpinned, found at readiness review. |
| AC-3 | required | Sanitizing must not lobotomize the one record of a publication failure. |
| AC-4 | important | The helper's contract was just verified by six lanes; this change must not drift it. |
| AC-5 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Planned from wave `1uwpf`'s carried-forward findings (delivery code lane). Premise verified before authoring: the raise site joins `rollback_errors` into a single-arg `OSError`, whose `strerror` is `None` | source read at the raise site, 2026-08-10 |
| 2026-08-10 | Readiness council (red-team and docs-contract seats): scope extended to the detail head, which leaks the original exception's absolute path on every single-fault publication failure (AC-2 added, previously unpinned); the `_repo_rel` risk mitigation was wrong (its fallback still raises out-of-repo) and Requirement 1 now specifies the out-of-repo form; the helper pin moved from source-literal to behavioral per the `1upba` lesson | red-team seat report (executed raise-site and helper reads), 2026-08-10 |
| 2026-08-11 | Thought: implement at the raise site per the plan with the readiness lanes' two traps folded in: `root` threaded into `_replace_artifacts_transactionally` (single production caller, `_publish_prepare_policy_state`, has it in scope), and the failing artifact's path/purpose captured BEFORE the rollback loop rebinds the `path` loop variable. Out-of-repo rendering via a new `_artifact_display_path` helper (repo-relative, basename fallback where `_repo_rel` raises) | readiness lane reports, 2026-08-11 |
| 2026-08-11 | Implemented. Red executed on the clean HEAD extract: the single-fault head leaked the absolute path verbatim (`receipt publication failed: [Errno 13] Permission denied: '/var/folders/.../artifact-a.txt'`), matching the qa readiness probe's observation of both fault shapes. New composition names the failing artifact (display path plus purpose) with the cause via `_read_error_detail`, rollback entries render display-path plus cause, and the out-of-repo case keeps the final component only. Four tests: single-fault path-free (AC-2), double-fault path-free with both artifacts named (AC-1, AC-3), out-of-repo final-component (Requirement 1), and the behavioral helper pin (AC-4: strerror subTest with the absolute path asserted absent, synthetic verbatim subTest with `strerror is None` asserted). BulkWaveGetChangeTests 30/30 green | executed HEAD-extract red probe; test runs, 2026-08-11 |
| 2026-08-11 | Delivery-council repair (red-team finding 1, fix-now sized): the leak class survived through one adjacent producer/consumer pair the raise-site fix never touched. Consumer: the `review_receipt_refresh_failed` handler in `_mark_change_item_response` rendered the caught exception raw; now routed through `_read_error_detail`. Producer: `review_evidence.py`'s ledger-read OSError branch embedded the absolute path in its message (a disclosed one-line adjacent-scope repair in 1uzwi's file, made path-free in that function's own missing-file idiom: `path.name` plus strerror). Red-first via the seat's executed attack shape (chmod-000 events.jsonl at a declared-wave deferral): the new `test_refresh_failure_diagnostic_is_path_free` observed the absolute path shipping pre-fix and passes post-fix; MarkAcReceiptRefreshTests 4/4, test_review_evidence 152/152, dashboard 189 OK. Carried forward, not repaired here: the staging `read_bytes` comprehensions before the transaction try (pre-existing raw propagation, correctly outside this plan's raise-site scope, and census-invisible to the `.read_text`-keyed residue detector); `resolve_review_authority`'s unreadable-to-legacy fail-open in review_evidence.py; the close race window folding a vanished doc into `change_doc_unreadable` | red-team seat attack reproduction; repaired test runs, 2026-08-11 |
| 2026-08-11 | Reverification (red-team seat, independent): repair verified effective by re-executing the original attack (diagnostic path-free, artifact and cause named); one minor residual found and fixed in-session: the regression test half-pinned the repair (the chmod scenario is satisfied by the producer fix alone, so a consumer-revert mutant survived, and the docstring mis-attributed the producer). The test now pins both halves as subTests (producer: chmod ledger; consumer: a real path-carrying OSError raised directly from the publication step), with the consumer-revert mutant re-executed red on a scratch copy and the live tree green 4/4 | seat reverification report; executed consumer-mutant red run, 2026-08-11 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | Fix at the raise site, not the helper | The verbatim fall-through is correct for message-only exceptions; the defect is a producer embedding paths in a message | Special-case single-arg OSError in the helper (rejected: hides information for shapes that carry none of their own) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Repo-relative rendering fails for a path outside the repo | `_repo_rel`'s fallback does NOT cover this case (it retries `resolve(strict=False)` and still raises `ValueError` out-of-repo; the earlier mitigation text was wrong, corrected at readiness review). Requirement 1 specifies the out-of-repo form (final path component only), and the red-first temp-dir case exercises exactly that branch |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
