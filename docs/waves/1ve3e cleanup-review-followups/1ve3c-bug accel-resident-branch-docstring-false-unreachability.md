# accel_embedder docstring falsely claims the resident branch is unreachable

Change ID: `1ve3c-bug accel-resident-branch-docstring-false-unreachability`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-15
Wave: 1ve3e cleanup-review-followups

## Rationale

The `_resolve_model_files` docstring (`accel_embedder.py`, the paragraph beginning "Since wave 1v0r0 registered arctic") claims the resident-graph branch "is unreachable for the current model set and only runs for an unregistered model." That claim is false: `_resolve_clean_onnx` returns `None` not only for unregistered models but whenever the clean-export fetch **fails** (offline cold cache, CA-trust failure), and its own degradation message says "falling back to the resident model path." The resident branch is therefore the live degradation path for both shipped models, and the tests prove it (`test_resolve_downloads_resident_model_on_cold_cache`, `test_resolve_none_when_resident_unavailable_after_fetch`, plus the comment at the offline fixture: "Offline + not cached → clean source unavailable → caller falls back to the resident path").

The false claim has already caused real damage twice: it entered the 2026-08-11 comment-fix waiver note as a "dead-for-shipped-models" finding, and the 2026-08-15 codebase cleanup review repeated it as a `remove` recommendation that the operator approved before plan-time verification falsified it against the code. A docstring that mislabels a live degradation path as dead code is a standing invitation to delete working fallback behavior.

## Requirements

1. **Correct the docstring.** Rewrite the reachability paragraph in `_resolve_model_files` to state both real routes into the resident branch: (a) models with no `CLEAN_ONNX_SOURCES` entry, and (b) registered models whose clean-export fetch fails (offline cold cache, CA failure), per the `_resolve_clean_onnx` fallback. Retain the still-true note that the fastembed cache is independently load-bearing for `indexer._get_embedder`.
2. **No behavior change.** Code, tests, and shipped behavior are untouched; the existing fallback tests are the executed evidence the corrected claim cites.

## Scope

**Problem statement:** A docstring mislabels a live offline/CA degradation path as unreachable dead code, and has twice propagated into removal recommendations.

**In scope:** the one docstring paragraph in `accel_embedder.py`.

**Out of scope:**

- Any change to `_resolve_model_files`, `_ensure_fastembed_model_cached`, or `_resolve_clean_onnx` behavior.
- The 2026-08-11 waiver note in `docs/agents/session-handoff.md` (historical record; the current-session handoff carries the correction instead).
- Test changes (existing coverage already proves the fallback path).

## Acceptance Criteria

- [x] AC-1: the docstring names both routes into the resident branch (unregistered model; failed clean fetch for a registered model) and cites the fallback semantics of `_resolve_clean_onnx`; the word "unreachable" no longer appears in it.
- [x] AC-2: zero behavior change: no executable line of `accel_embedder.py` is modified; `test_accel_embedder` passes unchanged; full suite green; docs-lint clean.

## Tasks

- [x] Rewrite the reachability paragraph of the `_resolve_model_files` docstring.
- [x] Run `test_accel_embedder` + full suite; docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| docstring  | implementer | —          | Goal: the corrected paragraph, comment-only diff, suite green |


## Serialization Points

- `.wavefoundry/framework/scripts/accel_embedder.py`

## Affected Architecture Docs

`N/A`: a comment-only accuracy fix inside one module; no boundary, flow, or verification change.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The false claim is the defect; both routes must be named so no future sweep re-derives "dead". |
| AC-2 | required | Comment-only is the safety property. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-15 | Planned from the codebase cleanup review's F1, which the plan-time census FALSIFIED: the sweep (and the 2026-08-11 waiver note it corroborated) called the resident branch dead for shipped models, but `_resolve_clean_onnx` degrades to `None` on fetch failure and the fallback tests execute the branch for registered models. The removal recommendation is withdrawn; the docstring's false unreachability claim is the actual defect. | `accel_embedder.py` `_resolve_clean_onnx` except-path message ("falling back to the resident model path"); `test_resolve_downloads_resident_model_on_cold_cache`, `test_resolve_none_when_resident_unavailable_after_fetch` |
| 2026-08-15 | Implemented. Reachability paragraph rewritten to name both routes (unregistered model; failed clean fetch for a registered model), citing `_resolve_clean_onnx`'s degradation semantics rather than the current model roster; the word "unreachable" no longer appears; the diff is comment-only (7 insertions / 3 deletions, all inside the docstring; executable-line diff of `_resolve_model_files` pre/post is empty). Full suite 7241 tests across 62 files OK (`suite-1ve3e.log`). One observation surfaced and correctly attributed: `test_reranker_fp16_matches_fp32_when_available` FAILS when run directly on this CoreML machine (one of three queries drifts 0.0670 against the 0.05 bound) but is SKIPPED under `run_tests.py`, which pins `WAVEFOUNDRY_EMBED_PROVIDER=cpu` for hardware-independence (wave 1p52p), so "71 tests ok" in every suite run this week means skipped, not passed. The failure reproduces identically against HEAD's untouched file in a scratch tree and depends on no line this change touches: it is a pre-existing, operator-machine-only FP16 export precision observation, orthogonal to this wave, and is handed to the retrospective as a follow-up candidate rather than buried. | `git diff --stat accel_embedder.py`; scratchpad `t1ve3e.log`, `headtree` control run; `suite-1ve3a.log` (11:03 pass) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-15 | Withdraw the cleanup review's `remove` verdict; fix the docstring instead and keep the branch. | The branch is the live offline/CA degradation path for shipped models, proven by executed tests; removing it would regress GPU-path robustness exactly where prewarm is skipped. | Remove the branch as approved (rejected: premise falsified by the code); leave the docstring as-is (rejected: it has propagated into removal recommendations twice). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The rewritten paragraph drifts from the code again on the next model-set change. | The paragraph cites the `_resolve_clean_onnx` fallback semantics rather than enumerating the current model set, so it stays true regardless of which models are registered. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
