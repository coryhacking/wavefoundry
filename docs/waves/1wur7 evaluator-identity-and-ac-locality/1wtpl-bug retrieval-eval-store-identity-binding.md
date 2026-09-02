# Retrieval Evaluator Binds the Store File Inode Instead of the Store Identity

Change ID: `1wtpl-bug retrieval-eval-store-identity-binding`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-31
Wave: 1wur7 evaluator-identity-and-ac-locality

## Rationale

`retrieval_eval._index_identity` records the sqlite state-store file's device and inode inside `index_identity`, and `_validate_baseline_compatibility` requires the whole mapping to be equal for every comparison kind. A controlled rebuild that recreates the store file (a compatibility bump, a store reset, or the corrupt-open recovery that wave `1wpif` repaired) therefore makes the evaluator refuse its own `cross_generation` kind, the kind that exists precisely for controlled rebuilds. Wave `1wpif` hit this on its first cross-generation comparison: every other binding matched (corpus digest, evaluator identity, models, providers, environment, toggles) and the comparison had to be reproduced at the data level (`.wavefoundry/framework/scripts/benchmarks/compare_retrieval_receipts.py`, disclosed as computed rather than signed). Store identity should be the repository and index path plus a stable store identifier, with the file inode bound only where it means something (a same-generation pair on one physical store).

## Requirements

1. `index_identity` SHALL bind the repository root (path and inode), the index directory, and the store path for every comparison kind, and SHALL NOT bind the state-store file device/inode for `cross_generation` comparisons.
2. A same-generation pair SHALL still require one physical store, identified by the state-store file device and inode, so jitter is measured on one frozen store. The store-instance-identifier alternative is REJECTED (readiness CODE-RDY-6): no such identifier exists, minting one edits `index_state_store.py`, a member of `PRODUCTION_RETRIEVAL_MODULES`, which would perturb `production_identity` and contradict this wave's "no product path" scope; a `meta`-row identifier would also travel with a file copy and admit a copied store that the inode correctly refuses.
3. Any change to the evaluator's identity rules SHALL be documented in `docs/contributing/review-and-evals.md` and SHALL re-baseline deliberately: the change is landed, indexed, and a fresh same-generation pair recorded before it gates anything. `review-and-evals.md` currently claims "a `cross_generation` comparison covers a controlled rebuild", which the code cannot sign today; that sentence SHALL become true or be corrected.
4. The data-level comparison tool SHALL remain available and clearly labelled as computed, for the case a signed receipt is structurally unavailable. The tool (`benchmarks/compare_retrieval_receipts.py`) is currently an UNTRACKED artifact of paused wave `1wpif` (readiness CODE-RDY-9), so this requirement is satisfied either by `1wpif` committing it or by this wave adopting it; the implementer SHALL state which, and SHALL NOT leave a requirement whose subject is absent from the repository.
5. The identity rule SHALL be evaluated per comparison kind, which requires `_validated_epoch` to run BEFORE the `index_identity` comparison in `_validate_baseline_compatibility` (readiness CODE-RDY-7). The reordering changes which `invalid_baseline` message a doubly-incompatible report returns first; that reordering is intended and SHALL be pinned rather than discovered.

## Scope

**Problem statement:** the evaluator's store-identity binding is stricter than its own comparison model, so the controlled-rebuild comparison it promises cannot be signed.

**In scope:**

- `retrieval_eval._index_identity` and `_validate_baseline_compatibility`; the receipt schema fields they emit; tests in `tests/test_retrieval_eval.py`; the review-and-evals contract prose.

**Out of scope:**

- Any change to metrics, floors, thresholds, or the frozen corpus; the ANN certification work owned by `1wpih` (`1wsc8`), which should absorb or sequence after this change.

## Acceptance Criteria

- [x] AC-1: A cross-generation pair differing ONLY in the state-store file device/inode compares as `cross_generation` and is not refused, asserted at fixture level through the evaluator test module's report builder using the identity shape recorded in wave `1wpif` (inode 634552732 to 635682939, every other binding equal). Fixture level is the correct vehicle, not a re-run: landing this change alters `retrieval_eval.py`'s bytes and therefore `evaluator_identity`, so the `1wpif` receipts are refused for a different reason before the identity rule is ever reached (readiness CODE-RDY-5, QA-RDY-4). The recorded inode values are the fixture's provenance, not a machine-specific contract.
- [x] AC-2: A SAME-generation pair whose state-store device/inode differ is still refused, where "different physical store" means differing file identity per Requirement 2. This is a no-regression assertion, not new coverage: `test_incompatible_store_attempt_or_runtime_invalidates_baseline` already pins `state_store_inode=99` at generation 8 on both sides, and it must stay green, which is the built-in known-bad proving the loosening is not over-broad.
- [x] AC-3: `review-and-evals.md` states the identity rule and no longer claims a capability the code lacks; the evaluator test module covers AC-1 and AC-2 plus the Requirement 5 reordering; a fresh same-generation pair is recorded with the changed evaluator before it gates a ranking change.

## Tasks

- [x] Split `index_identity` comparison into cross-generation bindings (repository root/inode, index directory, store path) and same-generation bindings (those plus store device/inode); do NOT mint a store-instance identifier (Requirement 2).
- [x] Reorder `_validate_baseline_compatibility` so `_validated_epoch` runs before the identity comparison, and pin the resulting refusal ordering.
- [x] Update the evaluator tests: add the cross-generation inode-only fixture; confirm the existing same-generation `state_store_inode=99` refusal stays green.
- [x] Resolve the untracked comparison tool (adopt into this wave or sequence behind `1wpif`'s commit) and state which in the Decision Log.
- [x] Update `docs/contributing/review-and-evals.md` including the over-promising cross-generation sentence; re-baseline.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes                                   |
| -------------- | ----------- | ------------ | --------------------------------------- |
| Evaluator      | implementer | —            | identity rules, tests                   |
| Docs, baseline | implementer | Evaluator    | contract prose, fresh same-generation pair |


## Serialization Points

- `.wavefoundry/framework/scripts/retrieval_eval.py`, `.wavefoundry/framework/scripts/tests/test_retrieval_eval.py`, `docs/contributing/review-and-evals.md`

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md` (the standing gate's identity contract)

## AC Priority


| AC   | Priority  | Rationale                                                        |
| ---- | --------- | ---------------------------------------------------------------- |
| AC-1 | required  | The cross-generation comparison is the gate's controlled-rebuild promise. |
| AC-2 | required  | Jitter must stay measured on one physical store.                 |
| AC-3 | important | Contract prose and a deliberate re-baseline prevent silent drift. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-01 | Delivery review round 1: the identity split verified clean in every lane. The code lane confirmed by execution that `SAME_GENERATION_INDEX_IDENTITY_KEYS` is exactly the seven keys `_index_identity` emits and that cross-generation still binds repository root/device/inode, index directory and store path, so two unrelated indexes remain uncomparable; the architecture lane independently confirmed the loosening CANNOT unblock paused wave `1wpif`, because this wave's own edits changed `evaluator_identity`, a stronger barrier than the one relaxed, and the new full-distribution fields are required as well. No repair was needed for this change. | Lane reports in the wave record; `test_retrieval_eval.py::IndexIdentityBindingTests` (5 tests). |
| 2026-08-31 | Fresh same-generation pair recorded with the changed evaluator on generation 53 (one attempt id `c23c02bb`), verdict `pass`, no operator-review reasons, no tool contended. Recorded through a temp-and-promote runner per the wave's evidence-hygiene watchpoint: both runs wrote to a temp directory and were promoted only after both succeeded on one frozen generation with matching evaluator and production identity. Two earlier attempts were correctly REFUSED and published nothing when a background index refresh started mid-run (`index_not_ready`), which is the guard working. The pair also demonstrates the estimator repair on live evidence: `code_search` shows 22.90% p95 jitter against a 1.69% floor and 0.17% median, so the delivered rule records a 0.25 band where the p95-only estimator would have recorded 0.6871 -- a 2.75x looser standing band that every later cross-generation comparison would have inherited. `docs_search` sits at its permanent nine samples, labelled `p95_is_maximum: true` and NOT escalated. | `docs/reports/retrieval-quality-post-1wur7-run1.json` (baseline arm) and `docs/reports/retrieval-quality-post-1wur7.json` (comparison arm); `comparison_kind: same_generation_pair`, `verdict: pass`. |
| 2026-08-31 | Implemented. `_compare_index_identity` compares `CROSS_GENERATION_INDEX_IDENTITY_KEYS` (repository root/device/inode, index directory, store path) on every kind and adds `state_store_device`/`state_store_inode` only for a same-generation pair; `_validated_epoch` and the generation-ordering checks moved ahead of the identity comparison, and the resulting refusal ordering is pinned. `IndexIdentityBindingTests` covers the inode-only cross-generation pair (the recorded 634552732 -> 635682939 shape), the five bindings that still refuse across generations, the same-generation device/inode known-bad, and the reordering. | `.wavefoundry/framework/scripts/retrieval_eval.py` `_compare_index_identity`, `_validate_baseline_compatibility`; `tests/test_retrieval_eval.py::IndexIdentityBindingTests` (4 tests, 54 in the module, green). |
| 2026-08-31 | Drafted from wave `1wpif` delivery evidence: the evaluator refused the cross-generation comparison against the `1sear` standing pair because the store file inode differed while every other binding matched; the comparison was reproduced at the data level and disclosed. | `docs/reports/retrieval-quality-post-1wpif-vs-1sear-computed.json`; `1wpif` wave record, "Delivery evidence recorded" checkpoint. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-31 | ADOPT the data-level comparison tool into this wave (Requirement 4). `benchmarks/compare_retrieval_receipts.py` stays where wave `1wpif` wrote it and is declared by this wave, so the requirement's subject is present in the repository rather than dependent on a paused wave's commit. Its docstring is updated: the blocker it was written for is repaired here, so it now documents the residual case (a comparison across two `evaluator_identity` values, which the compatibility rule binds unconditionally and by design). | `1wpif` is paused and its close is blocked on a foreign wave's uncommitted change document, so sequencing behind its commit would hand this requirement's satisfiability to a third party. The tool is small, self-contained, imports nothing from `retrieval_eval`, and labels its output `computed`; nothing about adopting it changes `1wpif`'s own record. | **Sequence behind `1wpif`'s commit:** cleaner ownership, but blocked in practice. **Delete it now that `1wtpl` lands:** loses the residual cross-evaluator-identity case, which this change cannot remove. |
| 2026-08-31 | Select the inode-split implementation and reject the store-instance-identifier alternative (readiness CODE-RDY-6). | No such identifier exists; minting one edits `index_state_store.py`, a `PRODUCTION_RETRIEVAL_MODULES` member, which would perturb `production_identity` and contradict this wave's own "no product path" scope. A `meta`-row identifier would also travel with a file copy, admitting a copied store that the inode correctly refuses. | **Store-instance id in `meta`:** the only precedent (`context_efficiency._store_instance_id`), but it changes production identity and weakens AC-2's refusal. **Bind nothing:** loses the same-generation single-store guarantee that makes jitter meaningful. |
| 2026-08-31 | Verify AC-1 at fixture level rather than by re-running the receipts it names (readiness CODE-RDY-5, QA-RDY-4). | Landing this change alters `retrieval_eval.py`'s bytes and therefore `evaluator_identity`, which the compatibility rule binds unconditionally, so the `1wpif` pair is refused for a different reason before the identity rule is reached. The recorded inode values remain the fixture's provenance. | **Live signed receipt against the standing pair:** structurally impossible after this change. **Full live demonstration:** needs a store-recreating rebuild; available as a separate AC if wanted. |
| 2026-08-31 | Fix the identity rule in its own change rather than inside `1wpif`. | Changing the evaluator changes its digest, which the compatibility rule also binds, so the `1sear` pair could not be compared either way; the fix needs its own deliberate re-baseline. | **Patch inside 1wpif:** would have loosened a gate mid-delivery to sign the wave's own receipt. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Loosening identity lets two unrelated indexes be compared | Keep repository root/inode, index directory, and store path bound for every kind; only the file inode moves to the same-generation rule. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
