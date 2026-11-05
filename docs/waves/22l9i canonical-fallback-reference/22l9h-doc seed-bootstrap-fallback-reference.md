# Reference canonical shell retrieval fallback rules

Change ID: `22l9h-doc seed-bootstrap-fallback-reference`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-05
Wave: 22l9i canonical-fallback-reference

## Rationale

Seed 100's implement-wave bootstrap instruction says “four allowed fallback conditions,” while seed 180 and seed 020 define three retrieval-fallback reasons. The reported mismatch is verified in the current source.

## Product Intent

Agents generating implementation prompts should follow the canonical fallback rules without a contradictory count. AC-1 establishes the corrected instruction; this prose correction does not claim measured agent adherence or change the allowed reasons. It supports the adopted vision's dependable project guidance without changing its direction or horizons.

## Requirements

1. Replace “the same four allowed fallback conditions” in seed 100 with a count-free reference to the allowed fallback conditions in seed 180.
2. Preserve the surrounding MCP-first, delegation and implementation instructions and the canonical rules in seeds 020 and 180.

## Scope

In scope: one phrase in `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`; progress and feedback bookkeeping.

Out of scope: retrieval policy changes, runtime code, rendered prompt rewrites, release/build changes and unrelated feedback. No local prompt repeats the reported phrase (to be checked before implementation).

## Acceptance Criteria

- [x] AC-1: Seed 100's implement-wave instruction references the allowed fallback conditions in seed 180 without a separate numerical count, and its remaining text is unchanged.
- [x] AC-2: Seeds 020 and 180 remain byte-identical to their pre-change contents; no generated prompt or runtime code is changed.

## Tasks

- [x] Correct the phrase and mark the recorded feedback resolved.
- [x] Verify the exact diff and protected files, validate docs and obtain required delivery review.

## Serialization Points

One coordinator owns writes; reviewers are read-only. Protect all other framework files and actual visions. Existing handoff feedback may be updated to reflect completion.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`

## Affected Architecture Docs

N/A: the correction references the existing policy owner and changes no boundary or flow.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the reported contradiction without another duplicated count. |
| AC-2 | required | Bounds this correction to the stale bootstrap phrase. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Reference canonical conditions without a count. | Removes this mismatch and avoids maintaining a second count; source comparison verifies delivery, not agent compliance. | Change four to three: accurate now but retains duplicate state. Leave unchanged: preserves contradiction. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-05 | Planned the operator-requested phrase correction. | Current seed 100 line 107 versus seed 180 line 129 and seed 020 lines 86–90. |
| 2026-11-05 | Readback: replace only the stale count with the canonical reference; preserve seeds 020/180 and all remaining bootstrap text. Readiness and required lanes approve on current receipt. | Review contexts fallback_readiness_red, fallback_readiness_docsqa and fallback_readiness_chair. |
| 2026-11-05 | Implemented exact phrase-only correction. Canonical citation retained; reverse replacement recovers the original seed bytes; seeds 020/180 match protected baselines. Both required ACs and task 1 complete. Full docs validation and diff check pass. Canonical suite running. | Current source versus pre-change byte snapshot; no generated prompt/runtime edits. |
| 2026-11-05 | All 12,314 tests passed, but runner refused the receipt because the coordinator updated the standalone handoff during execution. No test failure or source change occurred. Rerun with repository writes frozen; recovery acceptance requires an additional explicit operator instruction and is not used. | /private/tmp/wf-22l9i-tests.log; refused run 76829a710b73444da55c8017c2181aa4. |
| 2026-11-05 | Frozen-tree canonical suite passes 12,314 tests across 217 files, with 12 intended skips, in 616.761 seconds; valid green receipt written. Fresh QA and docs-contract independently confirm exact change and reject stale-count/citation-removal controls. | /private/tmp/wf-22l9i-tests-frozen.log; contexts fallback_delivery_qa and fallback_delivery_docs. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
