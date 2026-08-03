# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-08-03

## Current State (2026-08-03, idle)

- **Last closed wave:** `1ua8t memory-checkpoint-reporting` — normal historical-memory checkpoints now report as action-required rather than as `index_update` failures, including across the legacy-parent installing-upgrade boundary.
- **No wave is OPEN.** The remaining planned waves are not activated; inspect the wave catalog before selecting follow-up work.
- **Release follow-up:** `wavefoundry-1.15.0.pgl2.zip` predates the final `runner_stale: null` clarification. Rebuild and re-verify a package before publication.

## Open questions / Deferred decisions

- Should the next package carry only the runner-freshness clarification or be grouped with another release-ready change?
- The close transaction did not automatically finalize admitted change statuses; this wave was corrected during closure. Consider a separate lifecycle-tool fix if that behavior recurs.

## Historical session notes (superseded)

### Current State (2026-07-31, end of session)

- **Wave 1tz6l release-upgrade-hardening: CLOSED + COMMITTED `3870201b`.**
- **Wave 1u2b0 host-surface-hardening: CLOSED, NOT committed.** Two changes (1u2ay runner-staleness
  identity, 1u2az renderer-owned permission allowlist). Fourteen findings across two delivery
  review cycles, all repaired with mutation checks and reverified by every blocking lane; seven
  approvals recorded; suite green at 6645. Field-validated on two target repos: the extraction
  filter withheld 6 runner members with a clean root, and the permissions block rendered 42
  read-tier rules with the knob correctly unset.
- **Pack `1.15.0+pg1a` built** at `~/.wavefoundry/dist/wavefoundry-1.15.0.pg1a.zip` (only 1.15.0
  pack in dist). CHANGELOG gained an `### Upgrading to 1.15.0` section.
- **Wave 1u44n upgrade-publication-integrity: READIED, NOT implemented. The plan is REFUTED and
  needs re-authoring before any code is written.**

## 1u44n: what happened and what the re-authoring must fix

Change `1u44m-bug` was filed from twice-reproduced field feedback (Phase 4 index publication fails
while the lock reads `awaiting_memory_validation`; the summary reports `index_update` success
anyway). The prepare council corrected the causal story once; the code-reviewer prepare lane then
REFUTED the corrected plan with an executable probe and recorded nothing. QA and release approved
(`ev-approval-qa-reviewer`, `ev-approval-release-reviewer`); code-reviewer did not.

**The refutation (code lane, probe-verified):** `begin_build_epoch` refuses on **checkpoint
presence**, not on the phase value. Probe: phase `awaiting_memory_validation` raises, phase
`index_update` ALSO raises, no checkpoint succeeds, staged-child receipt succeeds. So the planned
fix (advance the lock's `current_phase`) changes only the refusal text. Only removing the
checkpoint (what `cleanup` does, explaining the field recovery) or owner/staged-child status
unblocks publication. Corollary: Phase 4 publication is refused on EVERY upgrade whose index build
has real work, not only memory-gate runs.

**Corrections the rewrite must fold in:**

1. Re-point AC-1 at authorized-publisher status (owner or staged receipt) at the
   `begin_build_epoch` boundary, NOT at the phase value. Bring `index_state_store.begin_build_epoch`
   and the staged-receipt mechanism explicitly in scope. Red-first test: `begin_build_epoch` from a
   non-owner pid with a checkpoint present.
2. If the phase is advanced at all, add `index_update` to the `resume_after_memory` allow-list at
   `upgrade_wavefoundry.py:3481` in the same change, or the fix strands the only working recovery
   (the same deadlock shape 1tz6l already repaired once).
3. Extend the false-success sweep beyond `:4287-4291` to the `--update-index` writer at `:3675` and
   the `--rebuild-index` writer at `:3698`, and to BOTH swallowed-child-exit sites (`:2059` and
   `:2179`, plus `:2190` for the graph child).
4. Fix the plan's file misattribution: Serialization Points says `server_impl.py`, but
   `_build_upgrade_summary`, `_emit_primary_phase_summary`, `_cl_rebuilt` and
   `_docs_gate_summary_line` all live in `upgrade_wavefoundry.py` (`:2670`, `:2763`, `:3719`,
   `:2486`). `server_impl.py` only parses the sentinel.
5. Scope the `publication_control.py` non-goal to the guard PREDICATE, and name where the enriched
   refusal message is composed instead. Two refusal surfaces will otherwise diverge: the MCP
   `index_build` caller and the in-upgrade `setup_index.py` child raise.
6. Test-fixture vacuity traps: `begin_build_epoch` exempts a same-process caller, so a naive
   fixture goes green while appearing to cover the field scenario. Prior art that defeats it:
   explicit `"pid": -1` (`test_review_policy.py:625`) plus clearing
   `WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT`. Also `_build_upgrade_summary(ran_index_rebuild=False)`
   proves nothing; tests must drive both emit sites end to end.
7. Second existing literal to re-point (not delete): `test_upgrade_wavefoundry.py:4556-4560`
   asserts "running in background" and pins the exact hardcoded behavior AC-2 removes. The named
   `test_server_tools.py:24610` is the first. Preserve `ran_index_rebuild`'s name and arity: about
   twenty call sites depend on them.
8. Add a changelog task: a bullet in the existing `## [1.15.0] - unreleased` → `### Fixed` (1.15.0
   was never released; `+pfxp` and `+pg1a` are prerelease builds of it), PLUS a sentence in
   `### Upgrading to 1.15.0` noting that a target already on pfxp/pg1a will still hit the defect on
   the transition run under the old parent runner, since a version-keyed bullet cannot express a
   boundary inside one version.
9. Check whether `resume_after_gate` (`:3857-3885`) is a second instance of the same retained-phase
   defect: it selects `index_complete` only when state is `indexed` and otherwise leaves
   `awaiting_memory_validation`, then routes to `resume_after_memory` even on the `ready_for_index`
   branch. Four sibling checkpoint writers sit outside the current audit surface
   (`upgrade_wavefoundry.py:3446`, `:3537`; `upgrade_extensions.py:658`, `:711`).

**The best remedy found, worth adopting (release lane):** no `--cleanup` backstop is needed here
because `phase_cleanup` removes the lock unconditionally and `awaiting_memory_validation` is not a
retained-refusal phase, so an installed-but-not-yet-effective fix leaves targets recoverable. But
better: `upgrade_extensions` is loaded from inside the NEW pack while the parent runner is still old
code, `pre_index_update` already reads the checkpoint and run id, and the old parent already calls
`_run_hook("pre_index_update")` at `:4274` immediately before Phase 4. Acting there would make the
fix effective **on the installing upgrade itself**, closing the old-code window for once.

Both reported field variants are explained by one mechanism (rerun at `indexed` short-circuits at
`memory_backfill.py:686`; fresh zero-work run lands `ready_for_index`), so the disproved
auto-continue theory is not needed for either.

## Other open items

- `docs/plans/`: nothing pending. Deferred from 1u2b0 and still unfiled: the legacy
  `render_claude_settings` corrupt-file rebuild that destroys operator `deny` rules and the write
  tier knob, agent-reachable via `wf_sync_surfaces`. Pre-existing, a permission widening, worth its
  own change doc.
- Doc-drift gardener classifier fails on every index build across multiple targets (0 flagged,
  prior state preserved). Reported repeatedly, never filed.
- `memory_propose` drafts records with bare-basename targets; two of three decision drafts in 1u2b0
  pointed at a file that did not contain the thing they described. Generator-seam defect.
- Pre-release: the permission surface has never been exercised by a fresh `wf setup` against a
  scratch target (upgrades have exercised it; install has not).

## 1u44n status after the rewrite (2026-07-31, end of session)

The plan WAS re-authored per the nine corrections and the code-reviewer lane re-reviewed the
rewrite and PASSED (nine-assertion probe, including the assertion that refuted the prior version).
The plan now carries seven requirements and eight ACs, adopts the `pre_index_update` bridge as an
ADDITIVE requirement, and records two probe-found mechanics the implementer must
design against: the receipt write at `index_state_store.py:2323` is skipped without a backfill run
id, so naive reuse of `phase_index_update_parent_owned` raises; and a parent-set env grant is
inherited by the detached background code child.

**OPERATOR CORRECTION (2026-07-31): there is always a zip file for upgrades.** The rewrite justified
keeping the in-runner fix standalone by citing `_load_extension_module` returning None when
`zip_path is None`. Those branches exist in code (the staged-tree direct-merge path), but that path
does not occur in practice, so it must not shape the design. Consequences for the implementer:
the `pre_index_update` bridge is available on every real upgrade, which makes it the PRIMARY
delivery mechanism for already-upgraded targets rather than a fallback; the in-runner fix is still
required, but for the right reason (it is the actual correctness repair, and every later upgrade
runs new code anyway), not as insurance against a zip-less run. Do not add defensive scope for the
no-zip case beyond what already exists. Worth a separate question later: whether the zip-less
branches are dead code that should be retired.

**Review-integrity gap RESOLVED (2026-07-31, later in session): all four lanes genuinely
re-reviewed the rewritten plan in fresh contexts and wave 1u44n is now OPEN (implementing).**

- The operator zip correction was folded into the change doc itself (requirement 3, Old-code window
  note, Decision Log alternative (b)) before any lane reviewed.
- Four parallel lane re-reviews of the rewrite: code PASS (10/10 probe assertions re-executed,
  47/47 line claims exact, `ran_index_rebuild` count exactly 31); qa PASS with 3 P2 repairs (hook
  fail-safety must live INSIDE the hook body since `_run_hook` is fail-fatal, preserving the
  intentional `ACTION_REQUIRED_EXIT` pause branches at `upgrade_extensions.py:695-707` with the
  pause test `test_upgrade_wavefoundry.py:6347-6351` named must-stay-green; third pinned test
  `test_index_rebuilt_at_recorded` `:967-972` added to the re-point list because it would SILENTLY
  KEEP PASSING; AC-3 observable specified as post-hook `begin_build_epoch` admission of a non-owner
  child via a zip-loaded module); docs PASS with 1 P2 repair (wave.md still carried the refuted
  lock-advance causal story in its summary and watchpoints; re-synced, superseded council
  checkpoint retained as labeled history); release FAIL then CONFIRM-PASS with 2 P2 repairs (a
  THIRD index-publication refusal surface at `upgrade_wavefoundry.py:3595-3622` emits a false
  "validation is pending" message at zero pending on the standalone recovery path, fires BEFORE the
  `:3643` bridge hook, outside `publication_checkpoint_reason`; and the detached-child publisher
  grant needed an AC-level executed no-grant assertion, with the presence-bound primitive at
  `index_state_store.py:2272-2274` named).
- All repairs folded into the plan; every lane then re-adjudicated the FINAL bytes and returned
  CONFIRM-PASS.
- Ledger: approvals for all four lanes plus `wave-council-readiness` recorded keyed to receipt
  `review-policy-ab7c318c1599c2515c2b` (minted against the final bytes; supersedes
  `a06d8d9bda25a886a380`). Lesson learned this session: mint the receipt AFTER the last doc edit,
  THEN record approvals; a first code-reviewer record got staled by the repair-pass edits and was
  re-recorded under the fresh receipt with the supersession noted in its evidence.
- `wf_prepare_wave(mode='ready')` passed (council verdict valid), `wf_implement_wave(mode='create')`
  transitioned the wave to implementing.

## 1u44n DELIVERED and delivery-reviewed (2026-08-01)

- Implementation complete: value-bound publisher grant (`publisher_grant` token in the checkpoint
  matched against `WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN`) at all three Phase 4 paths, detached-child
  token strip, `pre_index_update` bridge (self-contained, transition-safe back to v1.4.0 runners),
  refusal composed once in `_checkpoint_recovery_tail` with the standalone gate consistent, outcome-
  derived `index_update` with de-swallowed child exits and standalone exit 1 (server relabel so it
  is not misread as docs-gate), no phase advance, requirement 6 audit recorded, three pinned tests
  re-pointed. Full suite 6671 across 61 files OK, coordinator-executed independently.
- Delivery review: four fresh-context lanes ALL PASS with executed verification, zero P1/P2;
  six mutation checks across two lanes, zero survivors; eleven P3 notes recorded in the lane
  approvals (follow-up candidates: end-to-end parent-owned staged-publication coverage; the
  cleanup-branch structural pin). Ledger: `ev-approval-{code,qa,docs-contract,release}-reviewer-*`
  and `ev-approval-wave-council-delivery` under receipt `review-policy-daf643a89a49bac36e9d`.
- Wave 1u44n status: implementing, all ACs/tasks checked, ONLY `operator-signoff` outstanding.
  Close is operator-owned; not requested yet. Nothing committed since `3870201b`.

## Field validation (2026-08-01): pg1a → pg5l upgrade on a target repo

- Pack `1.15.0+pg5l` built (fix symbols verified inside the zip). Operator upgraded a target from
  pg1a: **Phase 4a published cleanly on the installing upgrade with the OLD parent driving**; the
  1u44n bridge closed the old-code window in the field. No debris (allowlist held), permissions
  unchanged (42 managed), graph fingerprint reused.
- Reconciliation mystery RESOLVED and RETRACTED: pg1a's empty `[]` channel was the pfxp-era
  orchestrator building a summary against pg1a's rewritten scan API; pg5l run reported 34/34 with
  direct-scan cross-check [34, 0, 0]. Not a standing regression.
- Third confirmed instance of the old-code-window pattern (pfxp debris, pg1a runner_stale null,
  pg1a reconciliation []). Generalizable remedy filed as
  `docs/plans/1u44o-enh post-extract-summary-subprocess-backstop.md`: run summary building and
  post-extract reporting in a subprocess on freshly extracted code (the pg1a permissions backstop
  pattern, field-proven first time), with the two-remedy design note (hook bridge for behavior,
  fresh-code subprocess for reporting).

## 1u44n CLOSED; 1u5vl filed, six-lane-reviewed, and READIED (2026-08-01)

- **1u44n CLOSED** on explicit operator direction after field validation (pg1a to pg5l upgrade
  published cleanly under the old parent via the bridge). Operator-signoff and close recorded;
  three memory candidates adjudicated (one rewritten to the delivered three-disjunct mechanism).
- **Operator directed 1u44o ship in 1.15.0.** Wave `1u5vl upgrade-reporting-window-closure`
  created, 1u44o admitted, and taken through a six-reviewer prepare cycle (red-team seat + five
  policy lanes incl. architecture-reviewer). The cycle rewrote the plan substantially: honest
  class split (sentinel-carried vs server-resident; runner_stale is OUT of reach, restart-only),
  a pinned permanent entry-point contract (standalone flag, versioned sentinel envelope,
  unrecognized-token-degrades, contract test as the standing guard for fielded runners),
  primary-emit-only delegation (cleanup emit already runs fresh-process new code),
  parent-only-facts carrier (skipped_scan_locations), mutual-exclusion of delegated and fallback
  emits, AC-1 schema-divergent vacuity guard, parser-side end-to-end coverage with marker
  bounder-survivability, and two refuted plan absolutes rewritten (a pre-emit hook seam EXISTS,
  rejected on fail-fatality; the old parser is passthrough, field-proven). All six reviewers
  CONFIRM on final bytes; approvals under receipt `review-policy-219dcc04148fe24a231d`;
  **1u5vl is READIED, not open.**

## 1u5vl DELIVERED and delivery-reviewed (2026-08-01, later)

- Commit precondition satisfied: waves 1u2b0 + 1u44n committed as `15723021` (operator-authorized).
- 1u5vl implemented on top: `--emit-summary` delegation contract (schema token 1, timeout constant
  300s, marker `summary_source_degraded` terminal-key registered), primary-emit-only, mutual
  exclusion, lock-carried `skipped_scan_locations`, permanent `DelegatedSummaryContractTests`, all
  doc surfaces incl. gated seed edit + ADR `1u49j-adr`. Implement-stage MCP retrieval healthy (no
  posture gap this time).
- Delivery review: five fresh-context lanes ALL PASS with executed verification. Findings, all
  repaired (coordinator) + reverified (originating lane): shared P2 disclosure falsehood (the
  transition run is UNMARKED; pre-mechanism runners have no marker code) fixed in CHANGELOG + ADR;
  qa P2 surviving mutant D2 closed by a new nonempty `skipped_scan_locations` round-trip test
  through the REAL child; code P3 pair folded as hardening (publisher-token pop for the summary
  child; 40-char clamp on the unrecognized-token repr). Nine mutation checks total, zero final
  survivors. Coordinator-executed final suite: 6691 across 61 files, OK.
- Ledger: five lane approvals + `ev-approval-wave-council-delivery` under receipt
  `review-policy-3429fda3782aa165656f`. ONLY `operator-signoff` outstanding; close is
  operator-owned. Readiness-signoff re-affirmation under the final receipt will be needed at close
  (same supersession pattern as 1u44n).

**Operator-directed waiver (2026-08-01):** one-line formatting change outside wave scope, per
explicit operator instruction ("one more small change I'd like you to just make"): the
exploration-avoided projection table in `exploration_avoided.py` now renders its four numeric
cells with comma separators (matching the Context Efficiency table convention). Covered by the
full `test_memory_records` module (179 OK). Rides the next commit alongside the 1u5vl delivery.

**Field validation (2026-08-01): pg5l to pg8h on a target repo.** Transition run behaved exactly
as disclosed: unmarked old-schema summary (pre-delegation parent), no false report filed (the
seed-160 sentence pre-empted it), reconciliation 34 with direct scan_repo_channels cross-check
[34, 0, 0], runner_stale correctly false with unchanged runner files, root clean, lock cleared.
Standing verification hook (operator-recorded; updated by wave 1u8o5 after the envelope key
renamed to `summary_schema_version`): the NEXT upgrade initiated by a pg8h/pg9m-era runner takes
exactly one MARKED degraded run (`summary_source_degraded: unrecognized_schema_token_None`, no
schema key on the fallback summary); the upgrade after that must carry
`summary_schema_version: 1` unmarked, and that run is the renamed contract's field proof.
**First half OBSERVED in the field (2026-08-02, pg9m to pgf6 on a target repo):** the pg9m
parent delegated to the fresh pgf6 child, did not recognize the renamed key, and degraded with
exactly `summary_source_degraded: unrecognized_schema_token_None`; the fallback was the parent's
own correct summary (reconciliation 34, independent scan_repo_channels cross-check [34, 0, 0]);
no false bug report filed. Remaining: the next upgrade on that repo must report
`summary_schema_version: 1` unmarked.

## Solaris field report 2 (2026-08-02): drift diff-parser tab bug, FILED as 1u91n

Solaris's pgf6 upgrade root-caused a new framework defect, verified against this tree and
filed as `docs/plans/1u91n-bug drift-diff-parser-drops-tab-terminated-paths.md` (unwaved):
`_gardener_only_pairs` keeps git's TAB terminator on `+++` filenames containing spaces
(`index_state_store.py:3545/:3553`), so the blob spec fails at :3614 and doc-drift evaluation
is dead on every repo following the framework's own space-containing naming convention,
including this one. The 1u8o0 staleness diagnostic is what made the field diagnosis possible
(the reporter confirmed both 1u8o2-era improvements: honest exit 4 with retained lock, and
cause-naming drift failures). Same report also confirmed the 1u44n/1u44o fixes working
(clean pause before Phase 4, documented recovery succeeded, clean publication).

## Solaris downstream defect report triaged (2026-08-01)

Five items. Item 1 (Phase 4 deadlock + false success) is the already-fixed 1u44m defect, exercised
on pre-fix packs (report covers through pg1a; fixes shipped in pg5l and pg8h); their root-cause
hypothesis (stale phase value) is the refuted lock-advance theory, and the probe-verified account
(refusal on checkpoint presence; grant disjuncts) plus the recovery they found are already
documented. Four NEW/unfiled items now have change docs in `docs/plans/`:

- `1u725-bug aiignore-render-accumulates-blank-lines` (mechanism verified against tree; +2 blank
  lines per render, field repo reached 189)
- `1u8nz-bug index-removal-missed-when-path-leaves-scope-before-disk` (index-ignore-delete
  ordering strands chunks/graph nodes; phantom map areas)
- `1u8o0-bug doc-drift-classifier-fails-every-build-silently` (finally filed after repeated
  in-house observation; taxonomy split + staleness surface + root-cause fix)
- `1u8o1-bug coherence-scan-flags-pack-owned-migration-text` (checker-side fix; seed-160
  wave_open_gate hits are migration instructions that must keep the retired name; includes the
  transition-debris identification doc gap)

CHANGELOG Upgrading item 5 gained the reporter's permission-posture sentence (docs-only edit).
Positive field confirmations recorded: extraction allowlist held (pg1a), seed-160 transition
caveat accurately predicted the final spill, permissions provenance clean (42/42/0).

## 1u5vl CLOSED + COMMITTED 1b646e8e; wave 1u8o2 OPEN and implementing (2026-08-01)

- 1u5vl closed on explicit operator direction (signoff + readiness re-affirmation recorded);
  committed as `1b646e8e` with the release-prep edits and the four filed plans.
- Wave `1u8o2 downstream-field-report-fixes` (four Solaris bugs) went through a five-reviewer
  prepare cycle that REFUTED both reporter root causes by independent executed reproduction:
  1u8nz rewritten to orphaned graph/sidecar store rows (Lance already self-heals; all deletion
  orderings heal; pack-lineage discrepancy is now a requirement); 1u8o0 rewritten to the
  reproduced living-doc deletion-frame trigger (delete-then-recreate persistence condition pinned
  into the fixture; classifier succeeds locally otherwise). Also: 1u8o1's wf_cli fix is
  checker-side REQUIRED (seed rewrite proven vacuous; twelfth mirror finding), seed-160 debris
  guidance is extend-in-place (premise was stale), 1u725 gained anti-vacuity assertions. All five
  reviewers CONFIRM on final bytes; five signoffs under receipt `review-policy-ece50807cc434b4322df`;
  READIED then OPENED; implementer running all four changes in serialization order
  (1u725, 1u8nz, 1u8o0, 1u8o1; index_state_store shared by 1u8nz+1u8o0; server_impl wf_audit
  shape shared by 1u8o0+1u8o1, landed against the spec in one pass).
- Close-time follow-ups recorded by lanes: the shipped eligibility reap's mass-removal hazard
  (disclosed, out of 1u8nz scope) needs its own entry; operator-signoff placeholder line; fresh
  unreleased CHANGELOG section contingency if 1.15.0 ships before this wave.

## 1u8o2 DELIVERED, delivery-reviewed, repairs reverified (2026-08-01, late)

- All four changes implemented and delivery-reviewed: four lanes PASS with executed verification,
  then a seven-item repair pass (two qa P2 test gaps from probing mutants: the untested build-path
  reap seam, now pinned; the vacuous never-blocks-ready pin, de-vacuated; five accuracy P3s incl.
  the secrets-cache breaker-starvation record and the walk-parity doc clause), every repair
  reverified by its originating lane with mutant kills re-established from scratch. Twelve
  mutation checks total, zero final survivors.
- Coordinator-executed final suite: 6721 across 61 files, OK. Tracking verified (all boxes,
  statuses synced, gates closed). Ledger: four lane approvals + `ev-approval-wave-council-delivery`
  under receipt `review-policy-03e6ca8f46d892ce20a4`. ONLY `operator-signoff` outstanding; close
  is operator-owned. Readiness re-affirmation under the final receipt will be needed at close
  (standard supersession pattern).
- Durable follow-up filed: `docs/plans/1u8o3-debt eligibility-reap-mass-removal-hazard.md`
  (symbol-anchored) so the disclosed shipped-reap hazard survives close.

**Field validation (2026-08-01, late): pg8h to pg9m on a target repo.** The delegation's first
live proof: the schema token at value 1 (observed under the pre-rename key spelling; wave 1u8o5
has since renamed the key to `summary_schema_version`, so the next pg8h/pg9m-initiated upgrade
takes one marked degraded run and the run after reports `summary_schema_version: 1` unmarked, per
the standing hook above), no `summary_source_degraded`, on the upgrade that shipped its own
seed change; the class-(a) reporting lag is empirically closed (transition run pg5l-to-pg8h had
correctly shown absent, per the disclosure). runner_stale false, impl_matches_disk true,
reconciliation 34 with independent cross-check [34, 0, 0], root clean, permissions unchanged.

## Next Steps
1. Operator: signoff + close for 1u8o2.
2. Release commit (operator-authorized), dating the `## [1.15.0] - unreleased` heading.
3. `build_pack.py --release` under gh account `coryhacking` (branch main, no v1.15 tag), then
   `gh release create` as `coryhacking`. pg8h predates wave 1u8o2; the release build is the ship
   artifact.

## Current Session

**Active wave:** *(none)*
