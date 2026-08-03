# Doc-Drift Classifier Fails Closed on Deletion Frames and Reports Stale State as Clean

Change ID: `1u8o0-bug doc-drift-classifier-fails-every-build-silently`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-03
Wave: `1u8o2 downstream-field-report-fixes`

## Rationale

Reported by Solaris (roughly a dozen consecutive builds across four pack versions, both build
modes) and previously observed in-house. Every affected build logs:

    build_index: doc drift update skipped — gardener classifier failed (git error/timeout/malformed
    output); prior drift state preserved, will retry next build.

**Prepare-cycle grounding corrected the filed premise (2026-08-01, two independent executed
probes).** The classifier is NOT unconditionally broken on the affected environment class: the
real `update_drift_from_build` executed end to end against this repo (macOS, Apple Silicon,
Python 3.13) succeeded in 1.0s ("1474 docs, 125 drift-flagged, 116 waves attributed"), and
`_gardener_only_pairs` returned 34 pairs on the production-shaped corpus. The failure is
CONDITIONAL on history shape, and the red-team seat reproduced a deterministic trigger
synthetically:

**A commit that deletes a living doc fails the frame parser closed** at
`index_state_store.py:3400`: the deletion frame `+++ /dev/null` sets `cur_file=None`
(`:3386-3387`), its content lines then read as content outside a well-formed hunk, and the whole
classifier returns `(False, set())`. Because the git log runs with `--no-renames` (`:3329`),
renames also emit deletion frames. One delete (or rename) of a living doc therefore poisons EVERY
build until the commit ages out of the `FRESHNESS_GIT_LOG_MAX_COMMITS` window, then silently
self-clears: deterministic, platform-independent, and matching the field signature exactly
("fails on every build, across pack versions, both build modes"). Whether the Solaris failure is
this trigger or another of the many collapsed causes is unknowable from the field log, which is
defect two.

Three defects, restated on the grounded evidence:

1. **A reproduced fail-closed trigger:** living-doc deletion (and rename) frames break the parser,
   freezing drift state for the lifetime of the commit window.
2. **The error is undiagnosable:** the log line already splits the STAGE (`which` distinguishes
   "history walk" from "gardener classifier" at `:3895`), but the parenthetical
   "(git error/timeout/malformed output)" is static text, and inside `_gardener_only_pairs` there
   are on the order of fifteen distinct fail-closed return sites (subprocess error, timeout,
   malformed sentinel, truncated frame, deletion frame, blob-fetch failure, frame-validator
   rejections at `:3334-3419`) all collapsing to `(False, set())`. Neither the operator nor a
   triaging agent can tell which fired.
3. **The downstream surface lies by omission:** `wf_audit` builds `doc_drift` from the worklist
   (`server_impl.py:9952-9956`) with no staleness or failure surface, so a frozen state reads as
   an evaluated-clean zero. This is the intent-versus-outcome reporting pattern this project has
   fixed twice (1u44n summary fields, 1u5vl delegation); the drift surface has the same disease.

## Requirements

1. **Fix the reproduced trigger:** deletion (and rename-as-deletion) frames are handled instead of
   failing the whole classification closed: either parsed correctly (a deleted living doc is a
   legitimate drift signal) or skipped per-file with the rest of the classification proceeding.
   Red-first: the synthetic delete-a-living-doc repro (probe-proven red today) becomes the pinned
   regression test. Trigger-persistence precision (code lane, verified): the production pathspec is
   built from the CURRENT living corpus (`indexer.py:4867`), so the deletion frame recurs only
   while the deleted path is still living, that is delete-then-recreate (or a rename whose old
   name is reused); a plain delete-and-gone self-clears on the next build. The regression fixture
   MUST encode delete-then-recreate (or keep the path in the passed corpus), or the productionized
   test goes vacuously green while the parser defect persists; that persistence condition is also
   exactly what matches the dozen-consecutive-builds field signature.
2. **Per-return-site failure reasons, not a three-way disjunction.** Each fail-closed return in
   `_collect_git_history` and `_gardener_only_pairs` carries a reason code threaded to the log
   line, which names stage plus reason plus a bounded sample where parse-shaped (the existing
   `which` stage split is kept). The class-level injection tests of AC-2 drive one representative
   of each class: subprocess error, timeout, malformed output, and the deletion-frame class,
   because a three-cause test would pass while still hiding the reproduced trigger.
3. **Staleness is surfaced from the FIRST failure, with age; a threshold only escalates.** The
   store already persists drift meta (`META_DRIFT_UPDATED_AT`); the failure state records
   consecutive-failure count, last reason, and last successful evaluation time. The reproduced
   trigger is deterministic for weeks then self-clears, so a threshold-gated surface would hide
   truth exactly when it matters; age-since-last-success appears immediately.
4. **The `wf_audit` contract is extended additively, and the spec update is REQUIRED.**
   `docs/specs/mcp-tool-surface.md:944` declares `doc_drift` `{available, flagged_count, entries}`
   the stable consumer contract; the new evaluation state (for example an `evaluation` object with
   status, `stale_since`, `consecutive_failures`, `last_reason`) is added without changing any
   existing key's meaning, the relationship to the existing `available` field is resolved and
   documented (available-true-but-stale is a real state), and the spec's "Drift never blocks
   `ready`" guarantee (`:947`) is preserved and restated with the new state. A consumer must be
   able to distinguish evaluated-clean from not-evaluated from the response shape alone.
5. **Re-points named.** `test_doc_drift.py`'s detector-failure stubs pin the exact `(ok, payload)`
   contract this change alters: `:701-702` (`test_detector_failure_preserves_prior_drift`) and the
   sibling `drift_detect_failed` assertions at `:881`, `:988`, `:1163`, plus the healthy-path
   negative at `:1181`. Each is re-pointed to the new failure contract, not deleted. The shape
   pins at `test_doc_drift.py:413` and `test_server_tools.py:30703` stay green (additive fields
   only).

## Scope

**Problem statement:** a reproduced history-shape trigger fails the drift classifier closed for
the lifetime of a commit window, the collapsed error reporting hides which of ~15 causes fired,
and the audit surface presents the frozen state as evaluated-clean.

**In scope:** the frame parser's deletion/rename handling in `index_state_store.py`
(`_gardener_only_pairs`, `_collect_git_history`), the per-return-site reason taxonomy and log
line, the staleness state in store meta, the additive `wf_audit` `doc_drift` extension in
`server_impl.py`, the Required spec update, regression tests and the named re-points.

**Out of scope:** the drift classification algorithm's semantics beyond deletion/rename handling;
`index_health` mirroring (optional, decide at implementation and record).

## Acceptance Criteria

- [x] AC-1: The reproduced trigger is fixed red-first: the synthetic living-doc-deletion (and
  rename) repro fails against current code and passes post-fix, with the classification
  completing for the remaining corpus. If the Solaris field cause later proves distinct, the AC-2
  taxonomy is the shipped instrument that captures it; that residual is recorded, not silently
  absorbed.
- [x] AC-2: One representative injection per failure class (subprocess error, timeout, malformed
  output, deletion frame) produces a distinct stage-plus-reason log line; the static three-way
  parenthetical is gone.
- [x] AC-3: From the FIRST failed evaluation, the store records and `wf_audit` reports the
  evaluation state (status, age since last success, consecutive count, last reason); a healthy
  build reports evaluated-clean; the two are distinguishable from response fields alone, asserted
  on fields, never prose.
- [x] AC-4: The spec's `doc_drift` section is updated in the same change: additive shape, the
  `available` relationship documented, "drift never blocks ready" restated and preserved
  (verified by test: the new state never gates readiness).
- [x] AC-5: The five named `test_doc_drift.py` re-points land as re-points; the two shape pins
  stay green; full framework suite passes.

## Tasks

- [x] Encode the red-first deletion-frame repro as a regression test (probe fixture exists)
- [x] Fix deletion/rename frame handling in the parser
- [x] Thread per-return-site reason codes to the log line; remove the static parenthetical
- [x] Add the evaluation state to store meta and the additive `wf_audit` extension
- [x] Update `docs/specs/mcp-tool-surface.md` (Required): shape, `available` relationship,
      drift-never-blocks-ready restated
- [x] Re-point the five named detector-failure stubs; verify the two shape pins stay green
- [x] Injection tests per failure class; staleness-surface tests; full suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          | Serialize with 1u8nz (shared `index_state_store.py`) and 1u8o1 (shared `server_impl.py` audit shape) |


## Serialization Points

- `index_state_store.py` is shared with 1u8nz; `server_impl.py`'s `wf_audit` response assembly is
  shared with 1u8o1; land the audit-shape edits of 1u8o0 and 1u8o1 against the spec in one pass.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md` (`wf_audit` `doc_drift`, a declared stable consumer contract).
  REQUIRED, additive-only.
- CHANGELOG `### Fixed` bullet at the release that ships it.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reproduced trigger is the defect; red-first with the delete-then-recreate condition is its proof |
| AC-2 | required | The collapsed message is why the field cause was undiagnosable; per-class reasons are the shipped instrument |
| AC-3 | required | The frozen-clean-zero misreport is the misreporting-class defect this wave exists to end |
| AC-4 | required | doc_drift is a declared stable consumer contract; shipping a shape change without the spec makes the spec the next lying surface |
| AC-5 | required | The named re-points and shape pins are what keep the taxonomy change from landing vacuously |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-01 | Filed after repeated in-house observation plus the formal Solaris report, on the premise that the classifier never succeeds on the affected environments. | Field report 2026-08-01; session-handoff open-items history |
| 2026-08-01 | Prepare cycle corrected the premise by execution: the real classifier SUCCEEDS on this repo and environment (update_drift_from_build end to end, 1.0s, 125 flagged), and the red-team seat reproduced a deterministic fail-closed trigger synthetically (living-doc deletion frame at index_state_store.py:3400; renames included via --no-renames; poisons every build until the commit ages out of the log window, then self-clears). Plan rewritten: fix the reproduced trigger red-first, per-return-site reason taxonomy (~15 collapse sites, not three), staleness surfaced from first failure with age, the wf_audit spec update promoted to Required additive-only with the available-field relationship and the drift-never-blocks-ready guarantee preserved, and the five test_doc_drift re-points named. | Probe artifacts probe_gardener/probe_c/c2/c3 plus the synthetic delrepo, scratchpad 2026-08-01; index_state_store.py:3329/:3386-3387/:3400/:3895 |
| 2026-08-01 | Red-first landed: `DeletionFrameClassificationTests` (delete-then-recreate fixture per requirement 1, rename variant, end-to-end update) FAILED 3 of 3 against pre-fix code, then the deletion-frame handling in `_gardener_only_pairs` (an `f_deletion` frame flag: `+++ /dev/null` content lines validate structurally and are never gardener-only candidates) turned all three green. Per-return-site reasons landed as a falsy `_DriftWalkFailure` carrier in the ok slot (every existing truthiness check and 2-tuple unpack keeps working); every fail-closed return in `_collect_git_history` and `_gardener_only_pairs` names itself with a bounded sample; the skip log line now prints stage plus reason plus the consecutive-failure count and the static parenthetical is gone. | tests/test_doc_drift.py `DeletionFrameClassificationTests`; index_state_store.py `_DriftWalkFailure`, `_collect_git_history`, `_gardener_only_pairs` |
| 2026-08-01 | Staleness and audit surface landed: `_record_drift_failure`/`_record_drift_success` persist consecutive count, stage, reason, first-failure time, and last-success time in store meta (failure recorded on the drift_detect branch, the git-probe-failed branch, and the exception path; success resets); `drift_evaluation_state` is the read side; `wf_audit`'s `doc_drift` gains the additive `evaluation` object plus a `doc_drift_evaluation_stale` advisory diagnostic. Taxonomy tests (`DriftFailureTaxonomyTests`: one injection per class incl. the deletion-frame class completing with no skip line; staleness from first failure with age, escalation, reset) and the audit-side field tests (`DriftWorklistAuditSurfaceTests`, incl. the never-blocks-ready pin) all green; the five named re-points landed as re-points asserting the new stage/reason fields; test_doc_drift 100 tests OK; spec updated additively (doc_drift shape, available relationship, drift-never-blocks-ready restated); docs-lint clean. | tests/test_doc_drift.py, tests/test_server_tools.py `DriftWorklistAuditSurfaceTests`; server_impl.py wf_audit assembly; docs/specs/mcp-tool-surface.md |
| 2026-08-01 | AC-5 closed: full framework suite green (6720 tests across 61 files, OK) including test_doc_drift and the test_server_tools shape pins; seam reruns green (760 + 2377 tests OK). AC-1 residual stands as recorded: if the Solaris field cause proves distinct from the reproduced deletion-frame trigger, the shipped per-class reason taxonomy is the capture instrument. Change implemented. | run_tests.py output 2026-08-01 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-01 | Fix the reproduced deletion-frame trigger rather than hunting the unconfirmed field cause first | The trigger is probe-proven, deterministic, and matches the field signature (every build, all packs, both modes, eventual silent self-clear); the taxonomy ships alongside as the instrument for any distinct field cause | Diagnose-the-field-environment-first as originally filed (rejected: the classifier succeeds on the same environment class locally, so environment hunting has no reproduction to chase; the field log's collapsed message is precisely what the taxonomy fixes) |
| 2026-08-01 | Staleness surfaces from the first failure with age; thresholds only escalate | The reproduced trigger is deterministic for the commit-window lifetime and then self-clears; a threshold-gated surface hides the truth exactly during the poisoned window | Consecutive-failure threshold as the display gate (rejected: delays truth; kept only as an escalation marker) |
| 2026-08-01 | Reason threading uses a falsy `_DriftWalkFailure` object in the ok slot, keeping the `(ok, payload)` 2-tuple arity | The suite holds roughly twenty 2-tuple unpack sites and truthiness assertions across test_doc_drift and test_indexer; a 3-tuple return would have broken far more than the five named re-points, while every assertion on `ok` is truthiness-based (verified by grep: no identity assertions), so a falsy carrier preserves the entire existing contract and legacy stubs returning a bare `False` degrade to reason "unspecified" | Return a 3-tuple `(ok, payload, reason)` (rejected: breaks every unpack site, ballooning the named re-point set); a module-global last-failure register (rejected: process-global mutable state, the relocation hazard recorded in memory) |
| 2026-08-01 | `index_health` does NOT mirror the drift evaluation state in this change | `wf_audit` is the declared audit/consumer surface for `doc_drift` and the plan marks index_health mirroring optional; mirroring would duplicate a consumer contract with no named consumer today, and the staleness signal already reaches every audit reader through the additive `evaluation` object plus the advisory diagnostic | Mirror into index_health now (rejected: contract duplication without a consumer; can be added additively later if a consumer appears) |
| 2026-08-01 | The git-probe-failed skip records a failed evaluation; the confirmed non-git skip and the fingerprint-match skip do not | A probe failure means the evaluation could not run and the served rows are aging (the same frozen-state hazard as a classifier failure); a confirmed non-git repo has no evaluation to run (nothing is frozen), and a fingerprint match means the prior successful evaluation is still current | Count only classifier failures (rejected: a permanently failing git probe would freeze state invisibly, the exact disease this change removes) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The Solaris field cause is a different collapse site than the reproduced trigger | AC-1 records the residual explicitly; AC-2's per-class taxonomy is the shipped capture instrument; the staleness surface makes any future silent freeze visible |
| The additive audit extension drifts from the spec's stable-contract declaration | AC-4 makes the spec update Required in the same change, additive-only, with the never-blocks-ready guarantee test-pinned |
| Re-pointed stubs keep passing against a tolerated legacy failure shape | Requirement 5 names each stub; AC-5 requires them re-pointed to the new contract, and the injection tests drive the real seams |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
