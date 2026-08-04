# A No-Op Review-Policy Migration Still Marks Every Readied Wave for Re-Prepare on Every Upgrade

Change ID: `1uf69-bug noop-policy-migration-invalidates-readied-waves`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-04
Wave: `1uf65 integrity-checks-guidance`

## Rationale

Target-repo field report (2026-08-04, observed on two consecutive upgrades, the second a
no-seed build successor pgt9 to pgto): Phase 0c marked the same readied wave for re-Prepare on
both runs, even when nothing a reviewer would care about moved. Recovery is cheap each time
(the typed wave-council-readiness approval survives, so `wf_prepare_wave(mode='ready')`
re-readies without a re-review), but the consequence generalizes: any project holding readied
waves re-prepares all of them on every pack adoption, forever.

Mechanism verified in this tree: `plan_review_policy_upgrade`
(`review_policy_upgrade.py:53-115`) sweeps every non-closed declared wave unconditionally
(:78-110) and stamps the re-prepare marker on each (`set_reprepare_marker(text, True)`, :92);
`apply_review_policy_upgrade` then writes every marked wave (:140-148). The asymmetry sits in
the same file: the CONFIG write is already conditional (:130, `if plan.config_after !=
plan.config_before`), but the wave marking has no corresponding no-op guard. When the policy
migration changes nothing (config byte-identical, zero carrier edits), the marking is pure
churn: it invalidates prepare state that the policy did not affect.

## Requirements

1. **A no-op migration marks nothing:** when the migrated config is byte-identical to the
   existing config AND the carrier reconciliation plans zero edits, the wave sweep neither
   stamps the re-prepare marker nor rewrites any wave.md. The upgrade result reports
   `waves_marked_for_reprepare: []` honestly on such runs. The guard suppresses ONLY the
   marking and wave writes: the plan-phase validation walk (unreadable waves and ledger errors
   failing preflight at :82-90/:111-112) runs unchanged, because both resume paths
   (`upgrade_wavefoundry.py:4060`, :4381) call `plan_review_policy_upgrade` purely for that
   validation (council-verified).
2. **A real policy delta keeps today's behavior:** any config change or carrier edit marks
   every non-closed declared wave exactly as now, pinned red-first (drive a config-delta run
   and assert the marker lands).
3. **Red-first on the reported shape:** a test drives the migration twice against an unchanged
   config with a readied declared wave; the second run must leave the wave byte-identical
   (marker absent, no rewrite). It fails on the current tree.
4. **Boundary decision RECORDED at Prepare (2026-08-04): skip marking, wave writes, AND the
   reprojection on a true no-op** (the pass's purpose is wholly derivative of the policy delta;
   the incidental crash/hand-edit projection repair it provided runs pre-extraction old code
   and is maintained at every event append anyway). Two residuals are ACCEPTED and recorded:
   (a) the pre-policy-wave seam at `server_impl.py:6965-6968` (a declared wave with no receipt
   and no marker imported into an already-migrated project is no longer caught by upgrade;
   recomputation at each lifecycle gate covers receipt-bearing waves but NOT this state, which
   `server_impl.py:6962-6968` short-circuits, so detection there is voluntary: re-ready any
   imported wave folder with `wf_prepare_wave(mode='ready')`), and (b) the old-code-window carrier-replay asymmetry (a pack whose only
   review-policy change is block prose replays via the post-extraction surface render outside
   `plan.carriers`, so such packs mark nothing under the guard; block prose is agent guidance,
   not wave review semantics).
5. **Doc carriers gain the no-op qualifier** (council census): the canonical sentence in
   `review_policy.py:97-121` (`UPGRADE_POLICY_BLOCK`, framework gate), then re-render the
   `wavefoundry:review-policy-upgrade` marker region (never hand-edit
   `docs/prompts/upgrade-wavefoundry.prompt.md:255`); seeds 160:518, 100:72, and 209:197
   (seed gate; seed-209 is 1uf64's delivered file, do not regress its integrity-check text);
   `docs/architecture/data-and-control-flow.md:266-268`. The 1tsbu ADR stays as history; the
   docs-lint fixture stays frozen (docs-lint never content-compares the block).

## Scope

**Problem statement:** the review-policy migration's wave sweep lacks the no-op guard its own
config write already has, so every upgrade invalidates every readied wave regardless of
whether the policy moved.

**In scope:** `review_policy_upgrade.py` (`plan_review_policy_upgrade` /
`apply_review_policy_upgrade`) and its tests (`test_review_policy.py`,
`test_upgrade_protocol.py` as applicable); the Requirement 5 doc carriers
(`review_policy.py` baseline block under the framework gate; seeds 160/100/209 under the seed
gate; the rendered upgrade prompt via re-render; `data-and-control-flow.md`).

**Out of scope:** the marker semantics and `wf_prepare_wave` recovery flow (correct);
`migrate_wave_review_policy` itself; carrier reconciliation logic; the plan-phase validation
walk (preserved by Requirement 1).

## Acceptance Criteria

- [x] AC-1: A no-op migration (byte-identical config, zero carrier edits) leaves every wave
  byte-identical and reports an empty marked list (red-first).
- [x] AC-2: A genuine policy delta still marks every non-closed declared wave (pinned; BOTH
  halves of the guard are pinned since the delivery-review repair: the config-delta path by
  `test_legacy_policy_mapping_marks_open_waves_and_preserves_closed_bytes` and the carrier-only
  path by `test_carrier_only_delta_still_marks_readied_waves`, which fails against a
  carrier-half-dropped mutant).
- [x] AC-3: The recorded boundary decision is implemented as written (validation walk
  preserved; marking, writes, and reprojection all skipped on a true no-op); the two accepted
  residuals are recorded in the Decision Log; full framework suite passes.
- [x] AC-4: Every Requirement 5 doc carrier carries the no-op qualifier; the rendered prompt is
  regenerated, not hand-edited; seed-209's 1uf64 content is unregressed; docs-lint passes.

## Tasks

- [x] Red-first: double-run no-op migration test with a readied declared wave
- [x] Add the no-op guard (marking/writes/reprojection only; validation walk untouched)
- [x] Delta-run pin; carrier doc edits under their gates + prompt re-render; suite; CHANGELOG
  bullet (current unreleased section)

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          |       |


## Serialization Points

- `review_policy_upgrade.py`, `review_policy.py`, `test_review_policy.py`; seeds 160/100/209
  (209 shared with delivered 1uf64: do not regress); the rendered upgrade prompt (re-render
  only)

## Affected Architecture Docs

Candidates at Prepare: CHANGELOG; the upgrade prompt's "Every non-closed declared wave is
marked for re-Prepare" sentence (`review_policy.py:103` baseline and its rendered carriers)
gains the no-op qualifier.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The no-op guard is the fix; without it every pack invalidates every readied wave forever |
| AC-2 | required | A genuine policy delta must keep marking or real policy changes ship un-re-prepared |
| AC-3 | required | The validation walk carries the resume preflights; skipping it would weaken upgrade recovery |
| AC-4 | required | Doc carriers stating the unconditional contract become false the moment the guard lands |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-04 | Filed from a target-repo field report (same readied wave marked on two consecutive upgrades, the second a no-seed build successor); mechanism verified code-grounded: unconditional wave sweep at review_policy_upgrade.py:78-110/:140-148 versus the conditional config write at :130. | Field report 2026-08-04; code_read this session |
| 2026-08-04 | Readiness council ran (red-team + docs-contract, code-grounded, MCP-first with disclosed Gapfill sweeps for index-excluded carriers). Red-team confirmed every mechanism cite, proved the guard inputs stable across build successors (both are fixed-point), found no test that fights the guard, censused all four marker consumers, and named two residuals now accepted in Requirement 4; it also established the validation-walk constraint (resume preflights depend on the plan phase). Docs-contract found three uncensused seed carriers plus an architecture doc; all folded into Requirements 4-5, Scope, ACs, and Serialization Points before the receipt mint. | Council seat reports 2026-08-04 |
| 2026-08-04 | Red-first proven on the reported shape: the double-run test (`test_noop_policy_migration_leaves_readied_waves_untouched`) fails pre-fix with `AssertionError: Lists differ: ['docs/waves/open-wave/wave.md'] != []` (guard temporarily neutralized to reproduce the pre-fix tree; 7 tests in `ReviewPolicyUpgradeTests`, 1 failure). | RED run 2026-08-04 (`tests.test_review_policy.ReviewPolicyUpgradeTests`, FAILED failures=1) |
| 2026-08-04 | Guard added in `plan_review_policy_upgrade` (`review_policy_upgrade.py:74-82`, `:96-97`): `policy_unchanged = config_after == config_before and not carriers`, then a single `continue` placed AFTER the unreadable-wave and ledger-error branches so the validation walk still reads and validates every wave while the marker, reprojection, and `WaveMigration` append are skipped. `apply_review_policy_upgrade` needs no change: an empty `plan.waves` yields `waves_marked_for_reprepare: []` and no wave write. | `review_policy_upgrade.py` this session; GREEN run `tests.test_review_policy` 35 tests OK |
| 2026-08-04 | Three tests added plus the AC-2 delta pin strengthened: no-op double-run (bytes + empty marked list + `plan.waves == ()`), unreadable-wave preflight still fails on a no-op run, ledger-error preflight still fails on a no-op run; `test_legacy_policy_mapping_marks_open_waves_and_preserves_closed_bytes` now asserts `waves_marked_for_reprepare == ['docs/waves/open-wave/wave.md']` explicitly. | `tests/test_review_policy.py`; 35 tests OK |
| 2026-08-04 | Requirement 5 carriers updated with the no-op qualifier: `review_policy.py` `UPGRADE_POLICY_BLOCK` (canonical baseline), seeds 160/100/209 (209 edited on the re-Prepare sentence only; its 1uf64 integrity-check text and phase rule untouched), `docs/architecture/data-and-control-flow.md`. `docs/prompts/upgrade-wavefoundry.prompt.md` regenerated via `render_agent_surfaces.py` (renderer reported that one path written); the ADR and the docs-lint fixture left frozen. | Renderer output 2026-08-04; `git diff --stat` shows the prompt's only change inside the marker region |
| 2026-08-04 | CHANGELOG bullet added under `## [1.15.2] - unreleased` / `### Fixed`; verification: `test_review_policy` + `test_upgrade_protocol` + `test_render_agent_surfaces` + `test_docs_lint` (1019 tests OK), `CouncilSeedVerificationContractTests` (9 OK) and `test_server_tools` for the 1uf64 pins, then the full framework suite. | Test runs 2026-08-04 (see Decision Log) |
| 2026-08-04 | Delivery-review repair 1 (release lane P2): the CHANGELOG bullet now discloses the transition run in the same register as the sibling 1uf67 bullet: the installing upgrade still marks each readied wave once (the sweep is planned and applied from the pre-extraction module at `upgrade_wavefoundry.py:4547`/`:4550`/`:4707`, extraction at `:4643`), the freshly rendered `docs/prompts/upgrade-wavefoundry.prompt.md` will already state the new rule during that same run (Phase 1 renders on new code) so the prose looks wrong for exactly one run, recovery is `wf_prepare_wave(mode='ready')` with the typed `wave-council-readiness` approval surviving, and a closing sentence tells operators not to report that one run as this fix failing. | `CHANGELOG.md` `## [1.15.2] - unreleased` / `### Fixed`, 1uf69 bullet |
| 2026-08-04 | Delivery-review repair 2 (qa fix-now): AC-2's pin claim is now genuinely satisfied. New test `test_carrier_only_delta_still_marks_readied_waves` pins the CARRIER half of `policy_unchanged`: it migrates once, re-readies the wave (`set_reprepare_marker(text, False)`), then plants one registered legacy section (`docs/prompts/implement-wave.prompt.md`, the "Required review lanes from readiness must participate during execution." replacement) so the config stays byte-identical while reconciliation plans an edit. Asserts `plan.config_after == plan.config_before`, `len(plan.carriers) >= 1`, `waves_marked_for_reprepare == ['docs/waves/open-wave/wave.md']`, and that the wave bytes changed. Non-vacuity proven against a scratch byte-copy of `review_policy_upgrade.py` with the carrier half dropped (`policy_unchanged = config_after == config_before`): the new test FAILS there (`AssertionError: Lists differ: [] != ['docs/waves/open-wave/wave.md']`) while the pre-existing no-op test still passes, so the new test is the only pin on that half. Repo file byte-verified unchanged (`shasum -a 256 -c`, OK). | `tests/test_review_policy.py`; mutant run 2026-08-04 (1 failure); `tests.test_review_policy` 36 tests OK |
| 2026-08-04 | Delivery-review repair 3 (architecture + qa P3): the over-claiming residual rationale corrected in both Decision Log rows and in the Requirement 4 parenthetical that carried the same sentence. Recomputation is the surviving mechanism for receipt-BEARING waves only; `server_impl.py:6962-6968` returns early exactly when the receipt is None and no marker is present, so residual (a)'s population has no automatic invalidation and no diagnostic and detection is voluntary. Operational note added: re-ready any wave folder imported from outside the project with `wf_prepare_wave(mode='ready')`. | `code_read server_impl.py:6945-6979` this session; this change doc's Requirement 4 and Decision Log |
| 2026-08-04 | Delivery-review repair 4 (qa nit): the ledger-error preflight test's regex tightened from `"preflight failed"` to `"review-policy upgrade preflight failed"`, so it can no longer pass on `plan_reconciliation`'s `"lifecycle carrier preflight failed"`. | `tests/test_review_policy.py` `test_noop_migration_still_fails_preflight_on_a_ledger_error` |
| 2026-08-04 | Gapfill: shell retrieval used for the index-excluded framework test tree (`tests/test_review_policy.py` symbol listing) and for the cross-carrier sentence census (`grep -rn "non-closed declared wave"`), because `code_keyword` returned only the two indexed hits and never the seed/test carriers. | This session's Bash calls |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-04 | Guard keys on the migration's own outputs (config byte delta plus carrier edit count); skip marking, writes, and reprojection on a true no-op; keep the validation walk | The inputs are exactly what defines whether the policy moved, both are fixed-point across build successors, and the walk is the resume preflight validator | Policy-version watermark in the lock or config (rejected: more machinery, still needs the byte comparison); skip the whole plan phase on no-op (rejected: breaks resume preflight validation) |
| 2026-08-04 | Accept two residuals: the pre-policy-wave seam (server_impl.py:6965) and the block-prose replay asymmetry | For receipt-BEARING waves, receipt/evaluator recomputation at each lifecycle gate is the surviving invalidation mechanism. It is NOT for the narrow population residual (a) names: `server_impl.py:6962-6968` returns early exactly when the receipt is None and no marker is present, so a declared wave imported from outside the project gets no automatic invalidation and no diagnostic, and detection is voluntary. Operational note: run `wf_prepare_wave(mode='ready')` on any wave folder imported from outside the project. Block prose is agent guidance, not wave review semantics | Extend the guard to detect imported pre-policy waves or block-prose deltas (rejected: machinery for cases the receipt path already covers on receipt-bearing waves) |
| 2026-08-04 | Implemented as one local `continue` inside the existing wave walk, guarded by `policy_unchanged = config_after == config_before and not carriers`, placed after the unreadable-wave and ledger-error branches | Keeps the recorded boundary exactly: the validation walk still reads, decodes, and ledger-checks every wave (both resume preflights preserved), while marker/reprojection/wave writes are skipped; `apply_review_policy_upgrade` then reports an empty marked list with no code change of its own | Early return before the walk (rejected: kills the resume preflight validation); a `skip_waves` plan flag or new dataclass field (rejected: new schema for a condition the existing outputs already express) |
| 2026-08-04 | Residuals re-affirmed at implementation: the two accepted residuals stand unchanged, and no additional detection was added for them | The guard is exactly the recorded scope; recomputation covers receipt-bearing waves, the no-receipt-and-no-marker seam has no automatic invalidation or diagnostic (voluntary re-ready is the recovery), and block prose remains agent guidance rather than wave review semantics | Add an imported-pre-policy-wave probe or a block-prose delta check (rejected in-plan and again here as machinery the receipt path already covers on receipt-bearing waves) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Skipping the sweep hides a wave whose recorded policy genuinely lags | The no-op guard keys on the migration's own outputs (config delta plus carrier edits), the same inputs that define whether the policy moved; AC-2 pins the delta path |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
