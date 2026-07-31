# Single-Pass Review Lifecycle

Change ID: `1tr85-enh single-pass-review-lifecycle`
Change Status: `completed`
Owner: Engineering
Status: completed
Last verified: 2026-07-31
Wave: `1tsyx review-lifecycle-simplification`

## Rationale

The lifecycle reviews the same claim twice before implementation: a readiness council runs at Prepare,
and a separate pre-implementation review gate runs again before the first edit. Implementation then
invokes reviewer lanes whose conclusions the post-implementation review supersedes. Removing that
duplicated pass is the whole of this change.

An independent readiness council examined a much broader cutover and found the wider cost case did not
survive contact with the code: no seed mandates a full-suite run at any lifecycle boundary, the
per-cycle convergence checkpoint is appended by the tool at zero authoring cost, and the retrieval
posture entry is an advisory that never blocks. What is genuinely duplicated agent effort is narrow
and specific, so this change is scoped to exactly that, plus the defects that removing a gate would
otherwise expose.

That second part is not optional. Before this change, the required-lane gate was already vacuous:
measured, 151 of 181 wave records resolve to an empty required-lane roster. The cause is not a single
heading mismatch. The shipped wave template emits no participants section at all (113 records), and a
further 38 carry a `## Participants` heading and still resolve empty because the body is prose bullets
rather than the expected `Required review lanes:` bullet or role-table row. All five non-closed waves
in this repository resolve empty, including this one. The activation gate reads a
hand-authored prose verdict line rather than typed
evidence, which the code says out loud. A stale readiness approval causes the close gate to stop
requiring readiness instead of blocking. And the repairer/reverifier independence audit returns
"clean" rather than "unknown" when its anchor record is missing. Each of these is currently masked by
the duplicated review pass. Removing the pass without closing them would trade ceremony for a real
loss of enforcement, which is the opposite of the intent.

The broader restructuring (review-policy mode, council de-gating, a shared delivery evaluator, the
repair-loop rewrite, test cadence, and the install/upgrade cutover) is deferred to a follow-on change
recorded at `docs/plans/1tsbu-enh review-policy-and-delivery-evaluator.md`, which carries the full
readiness-council findings as its input.

## Requirements

1. **One pre-implementation review, owned by Prepare.** Remove the separate
   `pre-implementation-review:` marker, its chronology audit, and its second-approval concept.
   Prepare keeps a mandatory fresh independent critique of the proposed work before the first
   implementation edit; that critique is the only pre-code review. Carriers include
   `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, which today instructs the
   upgrade agent to BACKFILL the retired gate into every target repository and then lists it as a
   post-upgrade success criterion. Seed 160 phrases it as prose ("Pre-Implementation Review Gate"),
   never as the token `pre-implementation-review`, so any census must match both forms.
2. **Activation consumes typed readiness evidence.** On a wave declaring
   `review-evidence-source: events.jsonl`, `wf_implement_wave` must refuse to open the wave unless a
   current typed readiness approval exists. Today Gate 1 is a structural prose check over the
   `## Review Checkpoints` verdict line and does not read typed evidence at all, so a hand-authored
   line opens a declared planned wave. This remains true when `wave_review.enabled` is false: an
   empty policy-derived council-key list is not evidence that Prepare ran, so the stable typed
   `wave-council-readiness` key remains mandatory until `1tsbu` migrates policy and projection
   together. Legacy prose waves keep their current behavior unchanged.
3. **Retire the prose `prepare-council` verdict as a machine gate.** On declared waves the typed
   record is the authority. Two docs-lint validators in `wave_lint_lib/wave_validators.py` read the
   prose line, and they are NOT equivalent: `check_prepare_council_verdict` hard-errors only at status
   `implementing`, warns at `active`, and skips `planned` and `closed` entirely;
   `check_prepare_council_roster_evidence` emits warnings only and is documented as a consistency
   backstop, not a structural gate. Reconcile them so a declared wave with typed readiness evidence
   and no prose verdict passes at every status, while legacy waves keep byte-exact current behavior.
   Do NOT promote the roster-evidence warnings to errors: that would be a new hard failure for every
   `active` or `implementing` wave with an unevidenced seat, which is an enforcement increase this
   change does not authorize.
4. **Implementation does not run routine inferential review.** Remove the implementation-time
   reviewer-lane loop (seed 180's Level 2 "implement, invoke reviewer lane, critic, fix, re-invoke"
   default) whose result the post-implementation review supersedes. Implementation keeps focused
   computational checks and may request an exceptional named checkpoint at a high-risk boundary.
   Level 2 is the MIDDLE rung of the correction ladder, and the escalation table routes logic errors,
   missing behavior, and missing test coverage to it, so its removal must name the replacement
   in-phase route rather than collapsing the ladder to "fix it yourself" or "stop the wave". Write
   that route into the seed; `seeds/001` carries the same ladder and must agree.
5. **Remove the dead review-policy flag and correct the carriers that misdescribe it.**
   `required_for_all_waves` is parsed at `server_impl.py:2481` and read by nothing; configured
   council workflow and delivery enforcement key on `wave_review.enabled`, while Requirement 2's
   durable declared-wave readiness boundary remains unconditional until the enabled-aware projection
   migration. Remove the flag, including from
   `.wavefoundry/framework/seeds/007-review-system-overview.md`, which ships it inside the config
   block target projects are told to write. Correct `docs/references/project-overview.md`,
   `docs/contributing/feature-wave-lifecycle-overview.md`, and
   `docs/contributing/review-and-evals.md`, which all describe an operator opt-in the code has never
   implemented. This change does not alter what `enabled: true` enforces.

   **Deliberately NOT fixed here:** `review_evidence.py` assigns both council keys unconditionally
   before the `enabled` check, so a project that turned council off still gets council rows demanded
   in its projection. That is a real defect, but it is the single key-derivation path shared by
   lifecycle writes, lint, AND upgrade, and docs-lint hard-errors on a stale projection for every
   non-closed wave. Changing it without a re-projection step would break the docs gate of every
   downstream repository holding an open or planned wave, and this repository would never see it
   because it runs `enabled: true`. The fix travels with the re-projection work already owned by
   `docs/plans/1tsbu-enh review-policy-and-delivery-evaluator.md`.
6. **Make the independence audit total as defense in depth.** Today
   `_resolving_repair_start_context` returns `None` when no anchor matches and the audit then reports
   that malformed persisted shape as clean. The public append boundary already rejects an
   anchorless reverification, so this did not make such a chain appendable through
   `wf_review_event`. The audit must still reject the shape so imported or historical state, and
   future producer regressions, cannot evade the independent close-time check. Both comparison
   points stay live and must be named explicitly: the append-time guard
   (`reverification_context_not_fresh`, `reverification_actor_not_distinct`) is the primary control,
   and the close-gate audit (`review_evidence_independence_invalid`) is the backstop for chains
   written by older code. The join key is `(finding_id, cycle)`, not `finding_id` alone; the cycle
   half is load-bearing.
7. **Close the two enforcement holes the gate removal would otherwise widen.**
   (a) The required-lane gate must stop being SILENTLY vacuous. Note the precise goal: this change
   does not make every wave carry required lanes, because that would be an enforcement increase (see
   the decision below). It makes the emptiness VISIBLE and the gate correct whenever a roster does
   exist. Concretely: a declared wave whose roster resolves empty produces an explicit,
   NON-BLOCKING advisory at review and close rather than silently bypassing the gate; a wave whose
   roster is populated has its lanes enforced; and the template emits the section in a discoverable,
   deterministically-resolving shape so an operator can populate it deliberately.

   The advisory is non-blocking by design. Measured, ALL five non-closed waves in this repository
   currently resolve to an empty roster, including this one. A blocking advisory would freeze this
   repository's ability to review or close its own in-flight waves at the moment it needs to close
   this wave, and would impose the same freeze on every target repository. Visibility is the
   deliverable here; making rosters mandatory is a separate decision for the follow-on change.

   **The template roster ships EMPTY of required lanes.** The template emits the section in a shape
   both extractors resolve deterministically, containing no required lanes by default. This is
   deliberate: because this repository declares no `required_review_lanes` in workflow config, the
   wave record is the sole lane source, so a template that shipped a populated roster would make every
   newly created wave in every target repository unclosable until those lane approvals existed. That
   is an enforcement INCREASE, and this wave's mandate is to stop gates from being silently skipped,
   not to add new mandatory lanes. Lane enforcement stays opt-in exactly as it is today; what changes
   is that an empty roster is now reported instead of silently bypassing the gate.

   Note that TWO independent copies of the roster parser exist, in `server_impl.py` and
   `review_evidence.py`. An executed comparison of their EFFECTIVE outputs over all 181 current wave
   records found 181/181 agreement: although `server_impl.py` deduplicates in its local helper,
   `review_evidence.py` reaches the same order-preserving deduplicated result through
   `review_status_signoff_keys`. The duplication is therefore a future-drift risk, not a current
   three-record behavior defect. This wave keeps the two copies but pins parity over the real corpus
   and an adversarial duplicate/order fixture, in addition to checking the real producer record.
   (b) At close, a STALE readiness approval currently causes the
   readiness key to be dropped from the required set instead of blocking
   (`transition_policy: applies-from-next-prepare`, shipped by default). A stale approval must
   block; it must never relax a requirement.
8. **Preserve hard invariants.** Retain a fresh independent critical plan review before code,
   readiness before implementation, independent post-implementation review, independent
   affected-lane reverification after a material repair, operator-owned close, atomic cross-process
   event publication, non-Git support, and readability of closed historical ledgers. Closed ledgers
   containing `repair_start` and `convergence_checkpoint` records remain valid to READ; this change
   retires no run kind and adds no compatibility layer.

## Scope

**Problem statement:** The pre-implementation claim is established twice, once by the readiness
council and again by a separate pre-implementation gate, and implementation re-invokes reviewer
lanes whose conclusions are superseded. The duplication also masks four enforcement defects, so the
duplicated pass cannot be removed safely without fixing them.

**In scope:**

- The pre-implementation review gate and marker across seeds, install prompts, rendered prompts, and
  the upgrade contract in seed 160.
- Activation-time readiness derivation in `wf_implement_wave`.
- The `prepare-council` prose verdict as a machine gate, and the two docs-lint validators enforcing it.
- The prose verdict's seat-roster alignment check becomes legacy-only with the rest of that gate;
  declared waves do not gain a typed seat-alignment successor in this change. That design question is
  deferred explicitly to `1tsbu`.
- The implementation-time reviewer-lane loop in seed 180 and its rendered carriers.
- Removal of `required_for_all_waves` and correction of the carriers describing it, including seed 007.
- Independence-audit totality at both the append and close comparison points.
- The silently vacuous required-lane gate (non-blocking empty-roster advisory, enforcement when a
  roster exists, plus a template that emits a resolvable but lane-empty roster section) and the
  stale-readiness close relaxation.

**Out of scope (deferred to `docs/plans/1tsbu-enh review-policy-and-delivery-evaluator.md`):**

- The `risk_based | universal` review-policy mode and risk-to-depth selection.
- De-gating the Wave Council or making it operator-invoked.
- The shared read-only delivery evaluator for Review and Close.
- Restructuring the repair loop, cycle records, or convergence checkpoints.
- Removing narration or the retrieval-posture advisory.
- Test-cadence changes and memory-timing changes.
- The install/upgrade config cutover and the dashboard lifecycle narrative.
- Mechanical reconciliation of retired review-lifecycle sections already installed in downstream
  repositories. This wave removes the backfill instruction and keeps new/current carriers clean;
  the versioned replacement mechanism is owned by `1tsbu`.
- Making the review-status projection respect `wave_review.enabled`, including the downstream
  re-projection needed to migrate open and planned waves safely.
- Weakening any surviving review control, or letting implementers self-approve repairs.

## Acceptance Criteria

Every AC below states a POSITIVE failure obligation. A criterion satisfied only by deleting the
behavior it describes is not satisfied. Each red-first fixture must be shown failing against
pre-change code before it is made to pass.

- [x] AC-1: On a wave declaring `review-evidence-source: events.jsonl`, `wf_implement_wave` FAILS to
  open the wave when no current typed readiness approval exists, including when a well-formed
  hand-authored `prepare-council` verdict line is present and when `wave_review.enabled` is false.
  Red-first: the fixture must fail against
  current code, where the forged line opens the wave. A legacy prose wave still opens exactly as it
  does today, pinned byte-exact.
- [x] AC-2: A declared wave with typed readiness evidence and NO prose `prepare-council` verdict line
  passes docs-lint at status `implementing`, where `check_prepare_council_verdict` hard-errors today.
  The red-first fixture MUST be written at `implementing`; at `planned` and `active` the validator
  skips or warns, so a fixture written there is green on pre-change code and proves nothing. The
  legacy direction pins that a legacy prose wave missing its verdict line still hard-errors at
  `implementing` with the current message. `check_prepare_council_roster_evidence` keeps emitting
  warnings and is pinned as warnings, not promoted.
- [x] AC-3: An executable carrier census, extending
  `.wavefoundry/framework/scripts/tests/test_events_only_residue_census.py` with a load-bearing
  allowlist, finds no live pre-implementation-review gate in any shipped surface. The census matches
  the prose forms ("Pre-Implementation Review Gate", "pre-implementation review gate") as well as the
  token, including the "Pre-Implementation Gate Reconciliation" phrasing, and it covers
  `.wavefoundry/framework/seeds/`, `.wavefoundry/framework/install/`, `docs/prompts/`, `README.md`,
  and rendered platform surfaces. Every allowlist entry carries a written justification and the census
  FAILS when an entry's file or token no longer matches, so an allowance cannot quietly cover a
  surviving carrier. Red-first: reintroducing the phrase into seed 160 turns the census red, and a
  second mutation outside `seeds/` proves the scope is not seeds-only. Seed 160's backfill instruction
  and its post-upgrade verification entry are both removed.
- [x] AC-4: Seed 180 no longer makes reviewer-lane invocation the implementation-time default and its
  rendered carriers agree, covered by the AC-3 census. Positively, and not delegated to another AC:
  (a) the surviving post-implementation delivery gate still BLOCKS, proved by a REGRESSION PIN, not a
  red-first fixture: a wave with no `initial_delivery` review run fails both review and close. That
  gate already blocks today, so the pin is green on arrival and its job is to fail if this wave
  damages it. Do not manufacture a red by weakening a working gate. And (b) seed 180's correction ladder
  retains a NAMED in-phase route for a finding that is neither implementer-internal nor a
  stop-the-wave escalation. Level 2 is currently the middle rung of that ladder and the escalation
  table routes logic errors, missing behavior, and missing test coverage to it; deleting the rung
  without naming its replacement collapses the ladder to "fix it yourself" or "stop the wave". The
  replacement route is written into the seed, not left implicit, and `seeds/001` carries the same
  ladder and must agree.
- [x] AC-5: `required_for_all_waves` is absent from every shipped surface including seed 007's config
  block; the three named docs describe actual behavior (council enforcement keys on
  `wave_review.enabled` alone). The projection's unconditional council keys are explicitly OUT of
  scope per Requirement 5, so no projection behavior changes here and no re-projection is needed; a
  regression pin asserts the review-status projection is byte-identical before and after this change
  for both `enabled: true` and `enabled: false`, which is what proves the deferral is real rather
  than accidental. `docs/workflow-config.json` keeps its own `required_for_all_waves: true` only if
  the flag still parses; since the flag is removed, this repository's config drops it too, and the
  audit records that as a deliberate self-host change rather than leaving it as unexplained residue.
- [x] AC-6: A reverification whose independence anchor cannot be resolved is REJECTED. Red-first
  fixtures cover: (a) anchor absent, at the append guard and at the close backstop, and (d) a
  cycle-mismatched anchor, proving the `(finding_id, cycle)` join is enforced. Existing regressions
  from wave `1to7k` continue to pin (b) same actor as the repairer and (c) same context as the
  repairer; they are green-on-arrival controls, not new red-first evidence for this wave. A green suite
  that no longer exercises these paths does not satisfy this AC. Totality must not hard-block
  legitimate work: a fixture generated by the canonical
  repair producer, not hand-authored, proves the normal repair path always writes a resolvable anchor,
  so rejection fires only on genuinely anchorless chains.
- [x] AC-7: At close, a STALE readiness approval BLOCKS. Red-first: the fixture fails against current
  code, where staleness causes the readiness key to be dropped from the required set. Absent and
  current approvals keep their present behavior, pinned. The absent case is a DELIBERATE carve-out,
  not an oversight: a wave that never re-entered Prepare is not retroactively required to hold a
  readiness signoff, and the change doc states that rather than leaving it unexplained. This requires
  distinguishing present-but-stale from absent, which the current boolean currency check does not
  expose; the probe that makes that distinction is part of this AC and must exercise the real
  `ReviewAuthority.signoff_recorded` method rather than a test-local replacement.
- [x] AC-8: A declared wave whose required-lane roster resolves EMPTY produces an explicit
  NON-BLOCKING advisory at both review and close; the gate is never silently skipped. Red-first
  against current code, where an empty roster bypasses the block with no signal at all. The advisory
  must not block: a fixture proves a declared wave with an empty roster still reviews and closes,
  which is what keeps this repository and every target repository able to close their in-flight
  waves. Additionally: (a) a wave whose roster IS populated has its lanes enforced, so a required
  lane without a current approval BLOCKS review and close, proved by a REGRESSION PIN that is green
  on arrival because both gates already enforce populated rosters today. Do not manufacture a red by
  weakening the current gate;
  (b) a wave generated by the real `wf_create_wave` producer, not a hand-written fixture, resolves
  DETERMINISTICALLY through both extractor copies and both agree on that record. Per the Decision Log
  the producer's roster carries no required lanes, so the expected resolution is empty-and-advised;
  the obligation is that the two copies agree and the outcome is deterministic, not that the roster
  is populated. A second green-on-arrival regression compares both effective extractor outputs over
  the real wave corpus and an adversarial duplicate/order fixture; it pins the reproduced 181/181
  parity and fails if either copy drifts.
- [x] AC-9: Every closed historical ledger in `docs/waves/` still passes docs-lint unchanged,
  executed against the real corpus (41 ledgers, of which 25 contain `repair_start` and 15 contain
  `convergence_checkpoint`). No run kind is retired and no read/write compatibility layer is added.
- [x] AC-10: Focused lifecycle/lint/evidence suites and the canonical full suite pass; docs-lint and
  generated-surface drift checks are clean; and no Wavefoundry-internal wave, ADR, or change ID is
  introduced into `.wavefoundry/framework/seeds/`.

## Tasks

- [x] Write the executable carrier census first (AC-3), matching prose and token forms, so every
  later removal is measured rather than asserted.
- [x] Convert `wf_implement_wave` Gate 1 to a typed readiness read on declared waves, preserving
  legacy prose behavior byte-exact.
- [x] Reconcile the two `prepare-council` docs-lint validators for declared versus legacy waves.
- [x] Remove the pre-implementation gate from seeds, install prompts, rendered prompts, and seed 160's
  backfill instruction plus its verification checklist entry.
- [x] Remove seed 180's implementation-time reviewer-lane loop and regenerate its carriers.
- [x] Remove `required_for_all_waves` including from seed 007 and correct the three misdescribing docs;
  leave the council-key projection byte-identical for both `enabled` states as required by AC-5.
- [x] Make the independence audit total at both comparison points; pin the `(finding_id, cycle)` join.
- [x] Emit a non-blocking empty-roster advisory on a declared wave instead of silently skipping the
  gate, enforce lanes when a roster exists, and make the wave template emit a roster section both
  extractors resolve deterministically, carrying NO required lanes by default.
- [x] Pin effective roster-extractor parity over the current corpus and an adversarial duplicate/order
  fixture; do not treat the disproven three-record divergence as an implementation defect.
- [x] Add the AC-5 regression pin proving the review-status projection is byte-identical before and
  after, so the deferred projection fix is provably deferred rather than accidentally included.
- [x] Make a stale readiness approval block at close instead of relaxing the requirement.
- [x] Run the census, the closed-ledger corpus check, focused suites, the full canonical suite, docs
  lint, and the drift check.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| census-first | qa-reviewer | — | The executable carrier census lands before any removal so each deletion is measured. |
| gates-and-evidence | implementer | census-first | Activation typed read, prepare-council validators, independence totality, stale-readiness, roster heading. Single owner for `server_impl.py` and `review_evidence.py`. |
| carriers | docs-contract-reviewer | census-first, gates-and-evidence | Seeds are canonical; regenerate rather than patching generated copies. Seed 160 and seed 007 are the load-bearing ones. |
| verification | qa-reviewer | gates-and-evidence, carriers | Red-first proof for every AC, closed-ledger corpus check, full suite. |

## Serialization Points

- The carrier census lands before removals.
- `.wavefoundry/framework/scripts/server_impl.py`, `.wavefoundry/framework/scripts/review_evidence.py`,
  and `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py` are shared chokepoints and
  require single-owner edits. `wave_validators.py` is enforcement, not a carrier, and belongs to the
  gates workstream.
- `.wavefoundry/framework/install/lifecycle-prompts/` ships five templates distinct from the seeds and
  must be swept alongside them.
- Evidence and gate changes land before carrier regeneration.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — activation and evidence transitions.
- `docs/architecture/current-state.md` — public lifecycle flow.
- `docs/contributing/review-and-evals.md` and `docs/contributing/feature-wave-lifecycle-overview.md`
  — operator-facing review semantics and the corrected policy description.
- `docs/references/project-overview.md` — corrected policy description.
- `docs/specs/mcp-tool-surface.md` — `wf_implement_wave` activation contract.
- `README.md` — the worked transcript ends with "Pre-implementation review gate next".

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Activation must not open on forgeable prose once the duplicate pass is gone. |
| AC-2 | required | The retired prose gate must not hard-fail declared waves, nor silently stop gating legacy ones. |
| AC-3 | required | The upgrade contract actively reinstalls the retired gate; a census is the only control that catches it. |
| AC-4 | required | The duplicated implementation-time review is the wave's core removal. |
| AC-5 | required | A dead flag plus three misdescribing docs ship to every target repository. |
| AC-6 | required | The append boundary already rejects anchorless reverifications; a total independent audit is defense in depth against malformed persisted state and future producer regressions. |
| AC-7 | required | A stale approval relaxing a close requirement is a live bypass. |
| AC-8 | required | The lane gate is measurably vacuous today; removing another gate without this is a net loss. |
| AC-9 | required | Closed ledgers must stay readable; this is the wave's main regression risk to existing repos. |
| AC-10 | required | Proves the whole change end to end, including the shipped-seed hygiene rule. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-28 | Cycle 4 scope correction supersedes the two prose-migration attempts below. The original contract required seed 160's retired-gate backfill and success criterion to be removed; it did not require an agent-interpreted migration of every previously installed target prompt. The carrier matrix and its narrower duplicated validation were therefore withdrawn. The repository-wide executable census remains the current-tree control, with the previously vacuous backticked `prepare-council` literal corrected and additional rich-carrier phrases pinned individually. Complete downstream replacement and its production validation move to `1tsbu` as one shared mechanism. | Focused residue-census module passed 20/20. Four independently planted historical semantic routes each fail alone, including the `ready_for_council_review` sentence, exact backticked `prepare-council` sentence, rich Implement parallel-lane clause, and Council structured-verdict MUST clause. Seed 160 and the rendered upgrade prompt carry no downstream-reconciliation claim or duplicate residue list. Fresh docs-contract reverification remains required. |
| 2026-07-28 | Delivery repair cycle 4 was widened across the full bounded historical carrier family after the first repair proved too literal. Seed 160 now names the install-baseline and rich-rendered shapes for Implement, Review, agent Review, Council Review, Prepare, and Upgrade; it replaces known framework-owned baseline sections with current equivalents while preserving project-authored text. The recursive census now normalizes case and whitespace, matches the retired semantic clauses as well as headings/tokens, and permits the upgrade prompt's migration vocabulary only inside one named section at exact counts. The larger idempotent lifecycle-section reconciler is explicitly deferred to `1tsbu`; this wave supplies the complete prose migration bridge required for its own upgrade contract. | Focused residue-census module passed 20/20. A historical target fixture fails on all five populated carrier files before reconciliation and passes after replacement; the live upgrade prompt proves all retired literals are confined to its single count-bounded self-reference section. Fresh docs-contract reverification remains required. |
| 2026-07-28 | Delivery repair cycle 4 opened before mutation for `upgrade-removal-names-wrong-heading-and-validates-clean`. The migration now covers both historical Implement-wave section spellings, removes the stale Prepare-wave paragraph, and validates the full `docs/prompts/` carrier class by case-insensitive residue tokens rather than treating deletion of one heading as proof. The regression separates removal-line anchors from validation-section anchors so moving a token to the wrong instruction cannot satisfy it. | `repair_start` recorded as `ev-upgrade-removal-names-wrong-heading-and-validate-2`; complete residue-census module passed 18/18. Fresh docs-contract reverification remains required. |
| 2026-07-28 | Delivery repair cycle 3 follow-up closed the two uncleared QA objections and the verifier's three mechanical notes. Legacy malformed prose now positively asserts `prepare_council_verdict_invalid` through both Prepare-create and Implement; AC-7 now builds three real typed waves through canonical wave/event producers and reports each state inside its own `subTest`; the redundant current-signoff disjunct is removed. Requirement 6 and the AC-6 rationale now describe the total audit honestly as defense in depth because the public append boundary already rejected anchorless reverifications. Seed 160 now names both retired headings literally and checks their post-upgrade absence; the residue census permits only those two count-bounded removal/validation references. | Focused affected set passed 37/37 (`WaveCouncilPolicyTests`, `LegacyProseGateParityTests`, and `test_events_only_residue_census`). Replacing `ReviewAuthority.signoff_recorded` with the old current-only behavior makes the canonical-producer AC-7 test fail on the stale quadrant. Fresh QA reverification remains required before either chain clears. |
| 2026-07-28 | Delivery repair cycle 3 accepted all eight second-review findings. Added real-authority AC-7 coverage, positive legacy Prepare/Implement pins, and the missing Review-side `initial_delivery` pin; corrected AC-6 polarity claims. Reverted the isolated readiness-rerun doctrine rewrite, reconciled three live reviewer-loop prompts, added upgrade removal guidance for previously installed gate sections, corrected AGENTS.md, and documented declared-wave seat alignment as an intentional legacy-only boundary whose typed successor is deferred to `1tsbu`. | Focused lifecycle/census checks passed (19/19 and 18/18). A direct unguarded `test_server_tools` run triggered the known native CoreML/ONNX abort surface; the crash report located the fault in Apple Espresso/CoreML, and the same module then passed 1,471/1,471 (one expected skip) with the canonical runner's CPU/disabled-reranker guards. Independent mutation/reverification remains required for the blocking lanes. |
| 2026-07-28 | Delivery repair cycle 2 closed the four independently reproduced blockers: declared Prepare no longer consumes prose; council-disabled declared activation remains fail-closed on the stable typed readiness key; docs-lint resolves declarations through the canonical parser; and every live shipped carrier now assigns routine inferential work to the distinct Review phase. The first full run correctly exposed stale prose-authority fixtures; those became typed-ledger producers and malformed prose became an inertness control. Fresh architecture reverification then found the packaged `.wavefoundry/README.md` outside the census; it was reconciled, added to scope, and mutation-proven before final verification. | Direct regressions 116/116 and affected lifecycle set 143/143; final canonical suite 6,393/6,393 across 59 files in 324.556s; fresh red-team, architecture, and code-reviewer counterexample matrices all PASS; docs-lint clean with the pre-existing roster-evidence warning; `git diff --check` clean. |
| 2026-07-28 | Thought: implementation begins census-first after fresh code-reviewer reverification and a superseding readiness-council approval. The carrier-census test file and the lifecycle/evidence/lint fixture files are disjoint, so those red-first lanes may proceed in parallel; production changes remain serialized behind their demonstrated failures. | `ev-approval-wave-council-readiness-2`; `wf_implement_wave(mode='create')`; pre-implementation `memory_brief` over the named target files. |
| 2026-07-28 | Observe: implementation is complete. Declared activation now consumes typed readiness authority; legacy prose behavior remains pinned; empty rosters advise without blocking; populated rosters, stale readiness, and independence anchors fail closed as specified. The retired gate and dead policy flag are absent from every shipped carrier. | Red-first fixtures captured for AC-1/2/8; 162 focused tests passed; carrier census 16/16; platform sync wrote no files; canonical suite 6,391/6,391 across 59 files in 325.139s; docs-lint clean with one pre-existing warning. |
| 2026-07-28 | Independent post-readiness plan review found four blocking contract defects and opened cycle-1 repairs before mutation. Reconciled the projection scope so the `enabled`-respecting change remains wholly deferred to `1tsbu`; relabeled populated-roster enforcement as a green regression pin because current review and close already block; corrected the roster-parser claim after an executed 181-record comparison found zero effective-output differences; and aligned the wave record with the deferred matrix/test-cadence scope and the intentionally optional roster. | Findings `projection-scope-contradicts-deferral`, `populated-roster-enforcement-mislabeled-red-first`, `roster-extractor-divergence-claim-is-false`, and `wave-record-pulls-deferred-policy-back-into-execution`; two focused existing gate tests passed; executed dual-extractor census: 181 records, 0 differences. |
| 2026-07-27 | Planned from the pre-1.15 lifecycle/code/process audit and operator direction to preserve strong review while eliminating repeated review of the same claim. | Audit prompt and findings. |
| 2026-07-28 | Red-team seat returned CHANGES REQUESTED and found a self-contradiction the prior repair introduced: the C1 decision (template roster ships lane-empty) landed in Requirement 7(a) and the Decision Log but never propagated into AC-8(b), which still demanded the producer emit a NON-EMPTY roster. No implementation could satisfy both, and the cheapest resolution would have been to populate the template and reintroduce exactly the enforcement increase C1 was raised to prevent. Repaired by stating the honest deliverable: the gate stops being SILENTLY vacuous rather than stops being vacuous. An empty roster now yields an explicit NON-BLOCKING advisory, because all five non-closed waves here resolve empty and a blocking advisory would freeze this repository's ability to close this very wave; a populated roster is enforced; and the producer obligation is determinism plus extractor agreement, not a populated roster. Three further blocking repairs: the `enabled`-respecting projection fix is DEFERRED to `1tsbu` because it is the shared key-derivation path and changing it without re-projection would break the docs gate of every downstream repo holding an open wave, invisibly to this repo which runs `enabled: true`; Requirement 3 and AC-2 misdescribed the two validators (one hard-errors only at `implementing`, the other only warns), so AC-2's red-first is now pinned at `implementing` where the hard error actually lives and the roster-evidence warnings are explicitly not promoted; and the 37/1 record split is corrected to 38/0 after this wave's own heading rename. The red-team also confirmed no activation bootstrap deadlock, that independence totality does not retro-break the corpus (214 reverification rows, 0 anchorless across 41 ledgers), and that delivery repairs cannot stale readiness so this wave cannot block its own close. | Red-team seat report; executed roster and ledger probes over 181 records and 41 ledgers; `wave_validators.py:1799-1815`, `:1909-1911`; `review_evidence.py:1101-1107`, `:1149-1159`, `:891-892` |
| 2026-07-28 | Second reverification returned READY subject to two conditions, both now settled in this doc. C1: the wave template's roster content was an unmade design decision that, combined with AC-8's blocking obligation, would have shipped an enforcement INCREASE to every target repository; decided as a lane-empty roster and recorded in the Decision Log. C2: AC-4(a) was mislabeled red-first when the delivery gate already blocks today, which invited weakening a working gate to manufacture a red; relabeled as a regression pin. The seat also reported a 3-of-181 effective roster-extractor divergence; that measurement was later disproven and is explicitly superseded by the newer repair entry above, whose final-output comparison found 181/181 parity. Other corrections from the seat remain valid: the disproven heading-mismatch framing survived on the Scope, Tasks, and Risks surfaces an implementer works from; Requirement 4 did not match AC-4(b)'s named-route obligation; and this wave's own record used a heading that made it a live instance of the defect it fixes, now `## Participants`. The reverifier withdrew its own cycle-mismatch objection on re-analysis, confirming AC-6(d) is a valid red-first once the audit becomes total. All ten ACs re-audited as non-deletion-satisfiable. | Reverification seat report; original extractor comparison superseded by the 181/181 effective-output census recorded above. |
| 2026-07-28 | Reverification of the re-scope returned NOT READY and was repaired in-phase. The coordinator's synthesis had over-generalized one seat's observation about THIS wave's own record into a repository-wide cause: the claim that the lane roster resolves empty because the extractor wants `## Participants` while the template writes `## Coordinator and Participants` is FALSE. Measured: the template emits no participants section at all (113 of the 151), 37 records carry `## Participants` and still resolve empty, and `## Coordinator and Participants` occurs in exactly one file in the repository, this wave's own record. Requirement 7(a) and AC-8 were re-anchored on the empty-roster report and on a roster generated by the real `wf_create_wave` producer, since the original fixture would have gone green against that single self-authored record while the gate stayed vacuous for 150 others. Also repaired: AC-4 had no positive obligation of its own and delegated to AC-8; AC-5 lacked its enabled-true counter-pin; AC-3's census scope excluded `README.md`, which the same document names as a carrier, and imposed no allowlist justification; AC-6 gained a producer-generated proof that totality does not hard-block legitimate repairs; AC-7 now states the absent-approval carve-out explicitly. Requirement 7(a) also now names the two divergent roster-extractor copies. Fourteen of fifteen checkable claims in the re-scoped plan were independently confirmed true. | Reverification seat report; executed roster census over 181 records; `server_impl.py:6381`, `:6492-6515`; `review_evidence.py:1113` |
| 2026-07-28 | Re-scoped from a sixteen-requirement cutover to this focused change at operator direction, after an independent five-seat readiness council returned unanimous CHANGES REQUESTED. The council refuted part of the original cost case against code: no seed mandates a full-suite run at any lifecycle boundary, the convergence checkpoint is auto-appended by the tool at zero authoring cost, and the retrieval-posture entry never blocks. It also found that the original AC set could not distinguish simplification from relaxation, since prohibition-shaped ACs are satisfied by deleting the asserted behavior. Every AC here is therefore a positive failure obligation with a red-first proof. Four enforcement defects the duplicated pass was masking are folded in as required scope: forgeable activation, a vacuous lane roster (151 of 181 records resolve empty because the extractor wants `## Participants` and the template writes `## Coordinator and Participants`), a stale-readiness close relaxation, and a fail-open independence audit. Deferred scope recorded as a separate plan. | Readiness council seat reports; `server_impl.py:2481`, `:2506`, `:13800-13834`, `:2531-2536`; `review_evidence.py:1149`, `:1753-1755`; `seeds/160-upgrade-wavefoundry.prompt.md:204-207`, `:460`; `seeds/007-review-system-overview.md:142-148` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-28 | Supersede the attempted prose migration bridge: `1tsyx` removes seed 160's backfill/verification claims and does not promise to rewrite already-installed downstream carriers; `1tsbu` owns one production reconciler whose vocabulary and scope are shared with its tests. | Five repair rounds exposed the same structural mismatch: existing lifecycle files are skipped mechanically, prose must guess multiple historical shapes, and a hand-maintained validation list drifts from the executable census. Requirement 1 and AC-3 require removal of the backfill instruction and success criterion, not a new migration system. | Continue enumerating prose variants — rejected by repeated counterexamples. Import test-only census code into upgrade — rejected because productizing its scope/vocabulary is the deferred mechanism, not a focused repair. Leave the contradictory matrix in place — rejected as a known false contract. |
| 2026-07-28 | Complete `1tsyx` with a carrier-by-carrier prose migration matrix and exact-section/count validation; put a mechanical, idempotent lifecycle-section reconciler in `1tsbu`. | The six escaped carriers and the two Prepare shapes are direct completion gaps in this wave's own upgrade promise, so deferring them would ship a known-broken migration. A general reconciler changes the upgrade architecture and needs ambiguity handling, versioning, preservation rules, and byte-stability criteria beyond this repair. | Defer every gap to `1tsbu` — rejected because current upgrades would remain incomplete. Build the reconciler inside `1tsyx` — rejected as a materially larger mechanism during a delivery repair. Keep adding literal deletion instructions — rejected because the historical carrier fixture proves the defect is a semantic family, not one heading. |
| 2026-07-28 | Keep the upgrade-heading precision repair in `1tsyx` under exact count-bounded census allowances, covering both historical installation shapes and spelling-robust residue validation. | This wave introduced both the removal instruction and the census that prevented it from naming installed headings precisely. Fixing that self-created ambiguity is completion of the current upgrade contract; `1tsbu` owns typed policy/projection migration and is not the natural boundary. | Defer to `1tsbu` — rejected as unrelated scope and because it would knowingly land a broken current-wave migration instruction. Relax the tokens globally — rejected; only seed 160's bounded removal and recursive-validation references are allowed. |
| 2026-07-27 | Keep `events.jsonl` as the sole machine authority and Git as optional audit history. | The events-only cutover already removed redundant receipts; Git cannot be required in supported non-Git projects. | Replace events with Git — rejected. Add another sidecar — rejected. |
| 2026-07-28 | Re-scope to the pre-implementation duplication plus the defects it masks; defer policy mode, council de-gating, the shared evaluator, and the upgrade cutover. | The independent council showed the broad cost case rested partly on repetition that does not exist in the framework, while the genuinely duplicated agent effort is narrow. A smaller change with positive ACs is more likely to land without a net enforcement loss. | One sixteen-requirement cutover — rejected after the council; the AC set could not tell simplification from relaxation. Two admitted changes in one wave — rejected, both would close together and the split created no safer intermediate state. |
| 2026-07-28 | Fold the four masked enforcement defects into this change rather than deferring them. | Removing a review pass while leaving the gates it shadowed vacuous or bypassable converts a simplification into a relaxation. These fixes are what make the removal safe. | Defer them to the follow-on change — rejected; the removal would ship first and the exposure window would be the entire release. |
| 2026-07-28 | The empty-roster signal is a NON-BLOCKING advisory, and the deliverable is that the lane gate stops being SILENTLY vacuous rather than stops being vacuous. | All five non-closed waves in this repository resolve to an empty roster, including this one. A blocking signal would freeze this repository's ability to review or close its own in-flight waves at the moment it needs to close this wave, and would impose the same freeze on every target repository. Visibility is achievable now; mandatory rosters are a separate decision. | Blocking advisory — rejected, it freezes in-flight waves everywhere. Leave the skip silent — rejected, that is the defect. Populate the template roster so the gate has something to enforce — rejected as the same enforcement increase under another name. |
| 2026-07-28 | Defer the `enabled`-respecting review-status projection fix to `1tsbu`. | It is the single key-derivation path shared by lifecycle writes, lint, and upgrade; docs-lint hard-errors on a stale projection for every non-closed wave, so changing it without a re-projection step breaks the docs gate of every downstream repo holding an open wave. This repository runs `enabled: true` and would never see the breakage. The re-projection work is already owned by that plan. | Fix it here with a re-projection step — rejected, that pulls the upgrade cutover back into this wave. Fix it here without re-projection — rejected as a silent downstream break. |
| 2026-07-28 | The wave template's roster section ships EMPTY of required lanes. | This repository declares no `required_review_lanes` in workflow config, so the wave record is the sole lane source. A populated template roster combined with AC-8's blocking obligation would make every newly created wave in every target repository unclosable until those approvals existed. That is an enforcement increase, and this wave's mandate is to stop gates being silently skipped, not to add mandatory lanes. | Ship a populated default roster — rejected as a surprise enforcement increase. Leave the template emitting nothing and rely only on the report — rejected; the section should be discoverable so operators can populate it deliberately. |
| 2026-07-28 | Preserve every retired run kind as READ-valid; retire nothing in the ledger grammar. | 41 closed ledgers carry `repair_start` and `convergence_checkpoint`; docs-lint validates them corpus-wide with no closed-wave exemption. | Retire the run kinds with a read/write asymmetry — rejected as the compatibility layer the wave watchpoint forbids. |
| 2026-07-28 | Treat the duplicate roster parsers as a pinned maintenance risk, not a live output defect. | The final projection path deduplicates through `review_status_signoff_keys`; an executed comparison found identical ordered lane outputs on all 181 current wave records. | Canonicalize immediately — rejected as unnecessary structural churn in this simplification wave. Keep the disproven 3-record claim — rejected by execution. Ignore the duplication — rejected because a parity regression is cheap and protects the gate/projection boundary. |
| 2026-07-28 | Keep declared readiness fail-closed on the stable typed `wave-council-readiness` key when council policy is disabled. | The enabled-aware projection migration is explicitly deferred to `1tsbu`, and the current projection already carries the readiness key unconditionally. Treating an empty policy-derived key list as readiness proof would violate the mandatory pre-code critique and relax activation before that migration exists. | Let disabled policy bypass readiness — rejected as the executed finding. Add a new readiness key in this wave — rejected as a larger ledger/projection migration already owned by `1tsbu`. Block disabled projects with no recovery path — rejected. |
| 2026-07-28 | Make the prose council seat-alignment gate legacy-only alongside the prose verdict; defer any typed successor to `1tsbu`. | Declared waves use typed approval authority and treat the prose checkpoint as narrative, so a machine check derived from that prose cannot remain authoritative. Reintroducing it would contradict Requirement 3; silently removing it was still a documentation defect. | Reintroduce the prose gate for declared waves — rejected. Invent a typed seat-evidence schema here — rejected as review-policy scope owned by `1tsbu`. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Removing a review pass produces a net enforcement loss rather than a simplification. | Changed behavior carries a positive failure obligation and a red-first proof; already-working gates carry green-on-arrival regression pins. The four masked defects are required scope, not follow-ups. |
| The upgrade contract reinstalls the retired gate into target repositories. | Seed 160's backfill instruction and verification entry are removed, and AC-3's census matches the prose phrasing seed 160 actually uses. |
| A token census misses carriers that describe the gate in prose. | The census matches both prose forms and the token, plus the "Pre-Implementation Gate Reconciliation" phrasing, across seeds, install templates, rendered prompts, `README.md`, and platform surfaces. Every allowlist entry carries a written justification and the census fails when an entry stops matching, and a second mutation outside `seeds/` proves the scope. |
| Fixing the vacuous lane gate ships an unplanned enforcement INCREASE, making every new wave in every target repo unclosable until lane approvals exist. | The template roster ships with no required lanes; lane enforcement stays opt-in exactly as today. Only the silent skip is fixed, and the change is recorded as an explicit decision rather than an implementation detail. |
| Closed ledgers stop validating after the change. | AC-9 executes the real 41-ledger corpus; no run kind is retired. |
| Tests pinning real invariants are deleted as retired ceremony. | No test is deleted unless it first FAILS against the new code; a test that still passes unchanged is pinning a surviving invariant. `test_review_evidence.py` is a non-sweep file requiring per-test justification. |
| Declared-wave changes break legacy prose waves. | Every gate change pins legacy behavior byte-exact in the same fixture pair. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state. Wave `1to78` closed and landed as
commit `3f59e379`, so the shared lifecycle and evidence files are unheld.
