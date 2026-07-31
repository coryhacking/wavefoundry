# Review Policy and Delivery Evaluator

Change ID: `1tsbu-enh review-policy-and-delivery-evaluator`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-07-29
Wave: `1tuoc review-policy-and-delivery-evaluator`

## Rationale

This is the deferred half of the review-lifecycle simplification. Change
`1tr85-enh single-pass-review-lifecycle` removes the duplicated pre-implementation review pass and
closes the enforcement defects that pass was masking. What remains is the larger structural work:
making review depth an explicit policy, deciding whether the Wave Council is a lifecycle gate,
sharing one delivery-state evaluator between Review and Close, and migrating existing projects onto
whatever is decided.

The split exists because an independent five-seat readiness council returned unanimous
CHANGES REQUESTED on the combined sixteen-requirement version. Two conclusions drove the split.
First, the wider cost case did not survive contact with the code, so the combined wave was carrying
requirements justified by repetition that does not exist. Second, and more seriously, an AC set built
from prohibitions ("no routine reviewer runs", "no Council runs automatically", "Review and Close
return the same diagnostics") is satisfied by deleting the behavior it asserts about, which is
exactly what a simplification wave does. That work needs its own review boundary and its own
positively-stated acceptance criteria.

The deferred questions are resolved below. The selected design preserves the one pre-code Council
critique, introduces an explicit risk-selected delivery policy, persists the selected delivery roster
in the wave record, and makes Review and Close consume one evaluator with a named close-only delta.
The post-`1tsyx` corpus is not yet large enough to justify changing the safe install default, so fresh
and upgraded enabled projects remain `universal`; `targeted` is available as an explicit opt-in until
the adoption measurement gate is met.

## Requirements

1. **Review policy and vocabulary.** Keep `wave_review.enabled` as readiness enablement and add the
   canonical `wave_review.delivery_mode` with values `disabled | targeted | universal`. The valid
   truth table is exact: `enabled=false` requires `delivery_mode=disabled` and requires neither
   Council phase; `enabled=true, delivery_mode=targeted` requires readiness Council and risk-selected
   delivery Council; `enabled=true, delivery_mode=universal` requires Council at both phases. Every
   other combination is invalid and fail-closed. The existing Council primer depth tiers
   (`lightweight | standard | full`) remain a separate adversarial-question axis. Fresh installs use
   `enabled=true, delivery_mode=universal`; upgrades map legacy `false` to `false/disabled` and legacy
   `true` to `true/universal`, preserving enforcement.
2. **Council as a phase-specific gate.** When review is not disabled, Wave Council remains the single
   readiness gate and therefore the pre-code failure-first critique. At delivery, `universal` always
   requires `wave-council-delivery`; `targeted` requires it only when the delivered boundary or a
   repair head carries an existing full-council trigger; `disabled` requires neither Council key.
   Specialist lanes remain non-waivable in every mode.
3. **Risk-selected roster and provenance.** `## Participants` separates operator input from generated
   authority: `Requested review lanes:` is optional project/operator input and
   `Required review lanes:` is Prepare-owned output. Prepare derives delivery lanes from the documented
   triggers already used by Wavefoundry (code, QA, architecture, docs-contract, release,
   performance, security), persists the exact ordered result in the wave's `## Participants`
   `Required review lanes:` field, and returns the mode, reasons, and delivery-Council decision in the
   typed response. That persisted field is the wave-specific roster authority consumed by Review,
   Close, projection, and lint. A canonical `policy_input_digest` binds the registered policy
   evaluator/schema version, normalized `wave_review`
   object, project `required_review_lanes`, applicable `review_policies`, admitted change IDs/kinds and
   change-doc bytes, and `Requested review lanes:`. Generated `Required review lanes:` is a receipt
   result, never a source input. Review and Close recompute the
   digest and block with an actionable re-Prepare diagnostic on change; they also retain the current
   project `required_review_lanes` as a monotonic downstream floor, so a newly added project lane can
   never be dropped by an older receipt. Ambiguous or stale persisted policy blocks rather than
   silently re-deriving a different wave-specific roster.
4. **Typed readiness/council alignment and receipt ABI.** The Prepare response and a versioned typed
   policy receipt stored in `events.jsonl` identify the selected primer depth and seat roster, policy
   mode, persisted delivery lanes, delivery-Council decision, evaluator/schema version, and
   `policy_input_digest`. The ledger ABI is the `review_policy_receipt` record type with exactly:
   `record_type`, `receipt_id`, `schema_version`, `evaluator_version`, `policy_input_digest`,
   `delivery_mode`, `primer_depth`, ordered `council_seats`, ordered `requested_lanes`, ordered
   `required_lanes`, `delivery_council_required`, and optional `supersedes_receipt_id`. Prepare first
   compares the proposed normalized semantic state with the current receipt: an identical current
   state is idempotent and appends nothing. Every changed state appends a new receipt whose mandatory
   `supersedes_receipt_id` is the current receipt, and derives `receipt_id` from both the normalized
   semantic fields and that parent ID (the genesis receipt uses an explicit genesis parent token).
   Thus A -> B -> A produces three distinct IDs and can never resurrect the first A receipt or its
   approval. The latest valid append-order receipt is current. Prepare alone mints receipts. The readiness
   approval builder server-derives `policy_receipt_id` from that current receipt and rejects every
   caller-supplied receipt field; an approval is current only while its bound receipt remains current.
   Therefore Prepare R1, approval A1, changed Prepare R2 makes A1 ineligible even if every other
   approval field is unchanged. Publication order is fixed under the publication transaction:
   compute and preflight everything; write the Prepare-owned Participants roster; append the receipt
   and rebuild its projection; then clear the re-Prepare marker last. Any interrupted intermediate
   shape fails closed, publishes no current approval, and retry derives the state and converges without
   duplicating the receipt. `wf_implement_wave` rejects a readiness approval whose bound receipt does
   not match the current persisted wave roster/policy. Legacy prose waves retain their existing
   compatibility path.
5. **Shared delivery evaluator.** Review and Close differ deliberately today, and the differences are
   not incidental: Close requires both council keys while Review requires one; Close alone applies the
   `transition_policy` branch; Close builds its roster as an unordered set while Review preserves order
   with `operator` first; Close alone runs the independence audit under `closure=True`, the secrets
   gate, memory validation, and the silent-unchecked-AC gate. "Same diagnostics from one evaluator"
   therefore uses one evaluator that returns a shared delivery-state result plus a named
   `closure_only` result. Review consumes the shared result; Close consumes both. The closure-only
   diagnostic-code set is the registered constant
   `CLOSURE_ONLY_DIAGNOSTIC_CODES = (docs_gardener_failed, open_changes_remaining,
   missing_signoff_evidence, review_evidence_independence_invalid,
   memory_validation_candidates_missing, memory_validation_required,
   memory_validation_check_failed, secrets_gate_unresolved, silent_unchecked_items_at_close,
   gates_forced_closed, review_projection_failed)`. Transport errors (`invalid_arguments`,
   `wave_not_found`) remain outside the evaluator. The constant is pinned against executed branches by
   exact list equality and one mutation per branch so the independence audit, secrets gate, memory
   validation, unchecked-AC gate, transition policy, and operator close authority cannot disappear
   during extraction. The shared blocking registry is exactly
   `SHARED_DELIVERY_DIAGNOSTIC_CODES = (review_evidence_invalid,
   missing_executable_approval_evidence, docs_lint_error, missing_operator_signoff,
   missing_required_lane, missing_wave_council_signoff, review_policy_receipt_stale,
   review_policy_reprepare_required)`. Tests use independent test-local literal tuples grounded in
   this requirement—not the production registries—as their expected oracle. Every shared and
   closure-only branch gets an executed mutation, plus distinct mutations for shared operator
   authority and transition-policy key selection.
6. **Honest evidence integrity.** Replace the single `integrity_confirmed` expansion with this exact
   caller-supplied object: `integrity_checks = {test_ran_without_unintended_skip: bool,
   public_path_reached: bool, boundary_values_realistic: bool, assertions_non_vacuous: bool,
   known_bad_detected: bool, known_bad_detection_method: non-empty string}`. The method lives inside
   the object; no additional integrity keys are accepted. The builder copies those facts; it does not
   mint success values. For an executed approval or finding every boolean must be true; a missing,
   false, extra, or empty-method field rejects before append.
   Approval and finding events use the same contract. Missing/partial checks fail before append.
   Existing canonical ledgers remain valid and immutable.
7. **Approval phase currency.** Leave the existing evidence `phase` field unchanged for schema and
   immutable-ledger compatibility. New approval events require a distinct versioned
   `approval_phase: readiness | delivery`. Readiness keys and Prepare-lane approvals are current only
   in readiness; delivery keys, specialist delivery approvals, and operator signoff are current only
   in delivery. The tool rejects known key/phase contradictions before append, and Review/Close query
   the intended approval phase explicitly. Existing approvals without `approval_phase` remain valid:
   `wave-council-readiness` is interpreted as readiness, while every other historical approval retains
   delivery interpretation. Existing non-closed waves that need phase-specific specialist readiness
   approvals are marked for re-Prepare by Requirement 8; closed ledgers are never rewritten.
   `approval_phase`, the complete `integrity_checks` object, and its detection method participate in
   normalized request content and operation identity; an otherwise-identical retry that changes one
   of them conflicts and appends zero rows.
8. **Upgrade and in-flight records, INCLUDING the deferred projection fix.** `review_evidence.py`
   assigns both council keys unconditionally before the `enabled` check, so a project that turned
   council off still gets council rows demanded in its projection. That fix was deliberately deferred
   out of `1tr85` and belongs here, because it is the single key-derivation path shared by lifecycle
   writes, lint, and upgrade, and it must travel with a re-projection step.
   Upgrade and every lifecycle mutation reuse the existing `lifecycle-mutation.lock` domain through
   one shared production helper, including its canonical path, byte offset, and platform locking
   style; no upgrade-only lock is introduced. When both locks are needed the exact order is lifecycle
   mutation lock first, publication lock second. The shared helper exposes a strict acquisition mode:
   Upgrade and every registered lifecycle writer use it and return an actionable failure without
   entering the critical section when the lock path, backend, or acquisition fails; the historical
   yield-unlocked fallback is prohibited on these authority-bearing paths. The JSON sentinel is durable recovery state only,
   never mutual exclusion. Upgrade acquires the strict lifecycle lock and then the existing
   project-global publication lock before preflight and holds both continuously within each
   process-bounded mutating transaction, releasing them in reverse order. The only permitted
   inter-transaction boundary is the existing `awaiting_memory_validation` return: before releasing
   either lock Upgrade writes and fsyncs a durable checkpoint that blocks every unrelated publisher
   and names only `memory_backfill` and `memory_validate` as authorized recovery writers. Those writers
   use the normal publication lock individually. Resume reacquires lifecycle then publication, verifies
   the checkpoint and validated-memory receipt, repeats the complete read-only preflight, and only then
   continues. No other phase may release publication ownership before its transaction reaches a
   terminal state.

   A typed production publication-writer registry enumerates every outside publisher and its
   contention policy. Context-efficiency projection, ordinary memory writes, review-event publication,
   docs gardening, synchronous and background index publication, and any later registered publisher
   fail fast during Upgrade with actionable `upgrade_in_progress`; no writer inherits the helper's
   current indefinite `blocking=True` behavior. The two named memory-recovery writers are enabled only
   at the durable pause and otherwise follow their ordinary policy. Upgrade holds the lifecycle lock
   across each preflight and mutation transaction. Mutating
   lifecycle calls fail closed while it is held, while read-only Review returns an actionable
   `upgrade_in_progress` diagnostic rather than reading a mixed state. Before the first project-state
   mutation Upgrade completes a read-only preflight over config, every lifecycle carrier path and
   shape, every non-closed wave, and every intended projection. Framework-pack extraction may already
   have occurred, but a preflight or incoming-migration load failure leaves project config, carriers,
   waves, and ledgers byte-identical and retryable. After clean preflight the order is fixed:
   migrate/validate config → reconcile recognized lifecycle sections → mark
   every non-closed declared wave `review-policy-reprepare-required` and rebuild its review projection
   → run docs lint → publish the operator summary. The next successful `wf_prepare_wave` deterministically
   persists the roster and policy receipt and clears the marker; Implement, Review, and Close block on
   the marker with that recovery. A durable failed-phase checkpoint remains after every post-mutation
   interruption, and Prepare, Implement, Review, Close, publication, and cleanup fail closed until
   retry reaches a terminal consistent state. While the failed phase is retained, Prepare appends no
   policy receipt and mutates neither roster nor re-Prepare marker. Each file mutation is atomic under
   the OS lock; an ambiguous carrier
   discovered by preflight leaves the complete mutation set unapplied and is reported, and retry
   converges from repository state. Closed wave
   Markdown and ledgers remain byte-identical. Changing the required signoff key set changes the rendered
   review-status projection, and docs-lint fails any non-closed wave whose projection is stale. Every
   target repository with an open or planned wave will fail its docs gate immediately after upgrade
   unless upgrade re-projects those records. Also: a project running `wave_review.enabled: false` has
   zero council enforcement today, so a single mandatory policy mode is an enforcement INCREASE for
   them. Both directions need operator-visible upgrade notes.
9. **Test cadence and narration.** Remains out of scope as low value: the council measured that no seed mandates
   a full-suite run at any boundary, `run_tests.py` has a content-hash skip cache so an unchanged
   rerun costs about zero, the convergence checkpoint is auto-appended by the tool, and the Gapfill
   and retrieval-posture entries never block. Any cadence work here is net-new specification, not
   de-duplication, and should be justified as such.
10. **One review-policy carrier registry.** A typed production
    `REVIEW_POLICY_CARRIER_REGISTRY` is the complete authority mapping each canonical source and
    section identity to its rendered destination and owner (`renderer`, `lifecycle_reconciler`, or
    `direct_docs`). It covers Prepare, Review, Close, and Upgrade prompts; project overview,
    contributing, reference, and tool-surface/specification docs; agent-role carriers; and the
    dashboard lifecycle narrative. Rendering, target reconciliation, validation, and the AC-9 census
    all consume this registry rather than maintaining parallel file or token lists. Owner labels carry
    permissions, not just taxonomy: `renderer` may replace only its current marker-bounded owned
    regions; `lifecycle_reconciler` may replace only an exact registered legacy marker or byte-known
    baseline section with its registered successor; `direct_docs` is validation-only and never a
    target-repository writer. Ambiguous, unregistered, or project-authored surrounding text is
    immutable. These permissions and the narrow known-baseline exception are reconciled in
    `docs/architecture/domain-map.md` and, where the executable layering invariant belongs,
    `docs/architecture/layering-rules.md`. Upgrade guidance
    in the registered family states the legacy policy mapping, the non-closed-wave re-Prepare marker,
    retained failed-phase recovery and retry, operations blocked while incomplete, ambiguity
    reporting, and closed-wave immutability. The same registry family carries the complete
    protocol-bridge operator contract: interpretation of `upgrade_protocol_version` and
    `minimum_runner_protocol`; the structured `upgrade_protocol_invalid` and
    `bridge_release_required` results; how to obtain and run the canonical builder-emitted bridge
    bootstrap and artifacts; the requirement to stop attached project hosts and record confirmation;
    the bridge's framework-only, project-surface-read-only boundary; the exact feature-pack second-hop
    command; and protocol-2 refusal of missing, malformed, import-failing, or mismatched mandatory
    code. Each registered carrier declares which obligations it renders, reconciles, or validates. A
    mutation for each carrier-owner class and bridge obligation proves that deleting a registry member,
    omitting a protocol recovery step, or restoring the universal-delivery narrative cannot pass
    silently.
11. **Target-repo retirement channel.** `reconcile_scan.py` handles only retired bin wrappers and
    renamed tools. There is no channel to tell a target repository that lifecycle vocabulary was
    retired, so a downstream repo's hand-authored `AGENTS.md`, prompts, and CI notes keep instructing
    agents to do retired things with no signal. Replace the prose-only cleanup model with an
    idempotent, versioned lifecycle-section reconciler: recognize exact framework-owned legacy
    sections or markers, replace known baseline sections with their current baseline equivalents,
    preserve project-authored surrounding text, report ambiguous shapes instead of guessing, and
    prove a second run is byte-stable. The reconciler and its validation must consume one
    production-owned vocabulary and carrier-scope definition; tests import that contract rather
    than maintaining a second literal list or narrower directory walk. Every destination, ancestor,
    temporary sibling, and final target is proven contained under the configured root; symlinked
    targets or ancestors are refused operationally, while native-Windows reparse/junction metadata is
    rejected by injected/static path-contract fixtures without claiming live NTFS execution; inspected
    carrier identity and marker shape are revalidated immediately before replacement. Wave `1tsyx` removes the
    retired backfill and keeps current shipped carriers clean but deliberately does not promise to
    rewrite already-installed downstream prompts; this requirement owns that migration.
12. **Bounded repair-class census and stop rule.** A confirmed finding must not be repaired only at
    the literal reproduction site when the same root cause has obvious sibling forms. Before editing,
    the repair pass must name the defect class and inspect the bounded family that shares its producer,
    consumer, authority boundary, compatibility family, platform family, or lifecycle branch. Confirmed
    siblings may be fixed in the same repair only when they share the root cause, remain inside the
    admitted scope, are materially relevant, and have a bounded low-risk repair. Reverification must
    replay the original reproduction, exercise at least one sibling or alternate producer shape when
    one exists (otherwise record a complete zero-sibling census), include a negative control, and show
    that the regression would fail if the defect class returned rather than merely pinning the reported
    literal. This is not authorization for a general review pass or architectural expansion. Pre-existing,
    speculative, cosmetic, low-value, different-root-cause, or differently scoped observations must be
    dispositioned explicitly as `maybe_later` or `dont_do_later`; the evaluator must allow either outcome
    without forcing a new wave.
13. **Measured adoption gate.** Before implementation, replay the corrected post-`1tsyx` review path
    over the eligible corpus and publish the inputs, classification reasons, Council-decision delta,
    required specialist-lane delta, limitations, and corpus fingerprint in
    `review-policy-adoption-baseline.md`. Changing the fresh-install default from `universal` to
    `targeted` requires at least a 20% reduction in delivery-Council invocations and a 15% reduction in
    required specialist-lane approvals with zero omitted project-required or risk-triggered lanes.
    The current one-wave post-fix corpus produces 0%/0%, so it does not meet the gate; this wave keeps
    the fresh-install default `universal` and ships `targeted` as explicit opt-in. A future change may
    change the default only after a larger qualifying replay or an explicit operator decision that
    records why a smaller benefit is acceptable.
14. **Versioned two-hop upgrade protocol.** The canonical ABI is
    `UPGRADE_PROTOCOL_VERSION = 2`. Every real pack carries `upgrade_protocol_version` and
    `minimum_runner_protocol` in its builder-stamped release metadata and retained upgrade state; the
    runner records its own protocol before loading incoming code. The mappings are exact: tagged
    supported-floor and protocol-1 runners are `legacy_optional_extension`; the immediately previous
    compatible runner and this release are protocol 2. Unknown, missing, malformed, decreasing, or
    unsupported values fail closed with a structured `upgrade_protocol_invalid` result. A feature pack
    whose minimum exceeds the installed runner produces `bridge_release_required` before extraction,
    with the required bridge version and exact retry command.

    Direct protocol-1-to-feature-pack mutation is not claimed. Instead the real distribution builder
    emits a standalone cross-platform Python bridge bootstrap adjacent to separately identified bridge
    and feature archives, plus stamped metadata containing their exact paths and hashes. The bootstrap
    receives the repository root and both artifacts explicitly. It does not route the bridge through
    the unmodified old runner's normal pipeline: that pipeline has ambient semver discovery and
    continues after extraction through rendering, revision stamping, pruning, policy materialization,
    docs gardening, and index writers. The bootstrap validates the supported-floor identity, both
    artifact hashes, host quiescence, and root containment; acquires the same lifecycle-then-publication
    lock domain through a builder-shipped stdlib implementation; stages a complete framework-only
    bridge tree; atomically swaps only `.wavefoundry/framework/` with rollback state; and verifies the
    installed protocol before releasing. It neither extracts nor invokes any project-surface member.
    After the bridge installs protocol 2, the new runner's explicit
    `--pack <feature-archive>` path performs the second hop, so the feature is selected exactly once and
    a bridge-selection loop is impossible.

    The bridge is identified by `bridge_build_id` and protocol metadata; it is not a product release
    and does not change or restamp project prompt-surface `framework_revision`. Project state remains
    byte-identical because the bridge archive contains no project-surface members. Its complete
    framework-only manifest includes the full runnable framework tree plus strict lifecycle/publication
    locking, protocol metadata, fail-closed loader support, and rollback metadata; it is not a minimal
    manifest that could cause the old prune phase to retire installed framework files. The feature
    pack's official incoming `pre_extract` extension executes on the unmodified supported-floor runner
    before any write and returns `bridge_release_required`; the bootstrap, not that runner, installs
    protocol 2. The operator then retries the
    feature pack under protocol 2, which acquires the strict lifecycle lock before preflight and
    mutation. An old attached host is not allowed across the bridge boundary: the bridge command is a
    maintenance operation that requires all project agent hosts stopped, records that operator
    confirmation, and its integration fixture starts the old host, performs the documented shutdown,
    then proves Prepare/review-event/Close are unavailable throughout the bridge. If host quiescence
    cannot be established, the bridge refuses before extraction. The feature archive alone carries
    the new product `VERSION` and matching prompt-surface `framework_revision`. The compatibility guarantee applies
    only to an artifact emitted by the canonical builder and verified against its stamped manifest;
    protocol-1's optional loader cannot make a falsifiable safety promise for an arbitrary malformed
    or tampered zip. Protocol-2 runners do reject missing, syntax-broken, import-failing, or mismatched
    mandatory protocol/backstop code before extraction.
15. **Platform boundary.** Operational upgrade/reconciliation fixtures cover macOS, Linux, and WSL2
    as the supported Windows execution environment, plus non-Git target repositories. Native Windows
    drive, separator, case, containment, and normalization forms receive parser/static contract
    coverage, but this wave does not claim native NTFS execution, reparse-point, or junction behavior
    without a native Windows runner. Committed framework artifacts remain platform-neutral.

## Scope

**Problem statement:** Review depth, council gating, delivery-gate evaluation, and their migration
remain unspecified after the focused change lands. Several of the original answers were shown unsound
by review and need re-deciding rather than re-implementing.

**In scope:**

- Review-policy mode, depth selection, and its phase scope.
- Council gating decision and roster provenance.
- Shared delivery evaluator with an enumerated, pinned close-only diagnostic set.
- Approval-record honesty and phase currency.
- Install/upgrade migration including in-flight wave re-projection.
- Registry-owned dashboard/lifecycle narration and a target-repo retirement channel.
- Supported-floor old-runner/new-pack compatibility and shared lifecycle-lock ordering.
- A builder-produced protocol bridge for legacy optional-extension runners, including host quiescence
  and zero project-surface mutation.
- A measured adoption gate for any future change from universal to targeted-by-default.
- Repair evaluation that searches a bounded same-root-cause family, proves class-level coverage, and
  stops with an explicit `do_now`, `maybe_later`, or `dont_do_later` disposition.

**Out of scope:**

- Anything delivered by `1tr85-enh single-pass-review-lifecycle`.
- Weakening any surviving review control.
- Test-runner performance, owned by wave `1tmtx`.

## Acceptance Criteria

- [x] AC-1: A fresh-install fixture selects `universal`, an upgraded enabled fixture preserves
  `universal`, an upgraded disabled fixture preserves `disabled`, and each mode produces the exact
  readiness/delivery Council requirements specified in Requirements 1–2. An exhaustive matrix rejects
  `false/targeted`, `false/universal`, `true/disabled`, missing `delivery_mode`, unknown modes, and
  non-boolean `enabled` without weakening Council or specialist enforcement; a mutation that aliases
  the policy to the primer-depth vocabulary also fails. Public-path targeted fixtures are exact:
  no delivered-boundary or repair-head trigger requires readiness Council and omits delivery Council;
  a delivered-boundary trigger requires delivery Council; and a repair-head-only trigger also requires
  delivery Council. Always-true, always-false, and delivered-boundary-only decision mutations fail.
- [x] AC-2: Prepare derives and persists one ordered delivery roster with reasons, and Review, Close,
  projection, and lint all consume that persisted authority. Fixtures prove code/QA/architecture/
  docs-contract/release/performance/security triggers, project-required lane folding, byte-stable
  re-Prepare, and fail-closed handling of an ambiguous or stale receipt. After Prepare, adding a new
  project-required lane must block as stale and must never let Review or Close omit that lane.
- [x] AC-3: A declared wave's server-derived typed readiness receipt binds the primer depth, Council
  seats, policy mode, requested-lane inputs, resulting ordered delivery roster, delivery-Council
  decision, policy evaluator/schema version, and digest. Implement rejects a current approval after
  any bound field is changed; `wf_review_event` rejects caller-authored receipt fields. A legacy prose
  wave remains byte-for-byte compatible, and byte-stable re-Prepare never hashes generated roster
  output as source input. The ledger validates the exact `review_policy_receipt` ABI and currentness
  rule. An executed R1/A1/R2 sequence proves A1 becomes ineligible, callers cannot supply
  `policy_receipt_id`, and interruption probes after roster write, receipt append, projection rebuild,
  and marker clear each fail closed and converge on retry without duplicate receipts. An A -> B -> A
  fixture proves R3 is distinct from R1, supersedes R2, and cannot make A1 eligible; a mutation that
  removes the parent receipt from identity fails.
- [x] AC-4: The shared delivery evaluator produces Review's complete blocking diagnostic set, and
  Close produces that same shared set plus the exact registered closure-only set. Mutating away each
  shared or closure-only branch fails independently against test-local literal tuples that do not
  import production registries, while Review never runs a close-only mutation. Separate executed
  mutations remove operator authority from both consumers and remove transition-policy key selection;
  both must fail.
- [x] AC-5: `wf_review_event` rejects approval and finding events whose exact caller-supplied
  `integrity_checks` object is missing, partial, false, extra, or has an empty detection method for an
  executed claim; every boolean is also tested with non-boolean values and the method with non-string
  values; empty and whitespace-only detection methods are distinct rejecting fixtures. A successful
  record contains exactly the supplied checks and method. Existing ledger fixtures
  remain valid without rewriting.
- [x] AC-6: New `approval_phase` readiness and delivery approvals are phase-scoped through the registered public tool;
  wrong key/phase combinations append zero rows, readiness approvals cannot satisfy delivery, and
  delivery approvals cannot satisfy Prepare. A corpus test validates all historical approvals,
  including the existing readiness-key records whose evidence `phase` remains `delivery`; no sealed
  ledger bytes change.
- [x] AC-7: Upgrade fixes disabled-policy projection, marks and re-projects every non-closed declared
  wave for required re-Prepare after policy/key migration, leaves closed Markdown and ledgers
  byte-identical, and reports the preserved/new policy to the operator. Implement, Review, and Close
  block on the marker; successful Prepare creates the roster/receipt, clears it, and makes the stale
  pre-upgrade projection lint-clean. In a disabled fixture with persisted `code-reviewer` and
  `qa-reviewer` lanes, the exact positive row set is `code-reviewer`, `qa-reviewer`, and
  `operator-signoff`; no Council rows appear. Empty-projection and restored-unconditional-Council
  mutations both fail. A concurrent-upgrade fixture proves OS-lock exclusion. Interruption checkpoints
  after config, each carrier, marker, and projection write retain durable failed state and converge on
  retry without copying/deleting or duplicating sections. At one post-mutation interruption checkpoint,
  a public `wf_prepare_wave` call proves zero receipt append, zero roster mutation, and zero marker
  clearing; it succeeds only after terminal upgrade retry.
- [x] AC-8: The versioned lifecycle-section reconciler replaces every recognized framework-owned
  legacy section with the current baseline, preserves surrounding project prose, refuses ambiguous or
  malformed shapes with an actionable report, and is byte-stable on a second run. Reconciler,
  validation, and tests import one production vocabulary and carrier-scope contract. One fixture proves
  an ambiguous/malformed carrier among otherwise recognized carriers leaves the entire intended
  mutation set byte-identical with an actionable report and byte-stable retry. A distinct clean-preflight
  interruption fixture contains one reconciled carrier plus remaining recognized legacy carriers and
  no ambiguity; retry neither duplicates, deletes, nor skips work. Outside-root sentinel, parent
  symlink, target symlink, nested/malformed markers, and swap-before-replace probes all fail closed
  operationally; native-Windows junction/reparse forms are injected/static metadata-contract probes
  only, consistent with AC-11.
- [x] AC-9: The exact typed `REVIEW_POLICY_CARRIER_REGISTRY` covers every owner class and carrier family
  in Requirement 10. Rendering, target reconciliation, production validation, and the test census all
  consume it. Dashboard and canonical lifecycle carriers describe Prepare as the single readiness
  critique and delivery review according to `disabled | targeted | universal`; deleting one member
  from each `renderer`, `lifecycle_reconciler`, and `direct_docs` class or restoring the prior
  universal-only narrative makes the appropriate executed mutation fail. Permission fixtures prove
  renderer writes are marker-bounded, lifecycle reconciliation writes only exact registered legacy
  markers or byte-known baselines, direct-docs entries never write target files, and surrounding prose
  is immutable; each cross-owner write mutation fails.
- [x] AC-10: A confirmed repair performs the bounded
  same-root-cause census from Requirement 12, exercises a sibling shape or records a complete
  zero-sibling result, includes a negative control, and rejects a mutation that restores the defect
  class. It must also prove that an unrelated or disproportionate observation can terminate as
  `maybe_later` or `dont_do_later` without becoming a blocking finding or mandatory follow-up wave.
- [x] AC-11: The canonical framework suite and docs gate pass. Operational upgrade fixtures cover
  WSL2 `/mnt/<drive>` paths, macOS `/Users` paths, Linux paths, and non-Git targets; native Windows
  drive/separator/case/containment/normalization forms are parser/static contract fixtures only. No
  test or documentation claims native NTFS reparse/junction execution without a native runner, and no
  platform-specific artifact is committed.
- [x] AC-12: Upgrade and lifecycle mutations import one shared helper for the exact existing
  `lifecycle-mutation.lock` path, byte offset, and platform implementation. Interleavings prove the
  lock order `lifecycle -> publication`, reverse-order release, and continuous ownership of both locks
  within each process-bounded transaction; read-only Review returns `upgrade_in_progress`. A real
  pause/resume interleaving proves that `awaiting_memory_validation` fsyncs its restrictive checkpoint
  before release, permits only `memory_backfill`/`memory_validate`, and requires lock reacquisition plus
  complete preflight before resume.
  An independent finite writer census is exactly equal to the production lifecycle-mutation registry
  plus review-event publication: create, add, remove, Prepare, pause, reopen, Implement, Review writes,
  Close, handoff, gate operations, and any later registered member. A representative real
  cross-process contention probe exercises the shared mechanism. An exact production
  publication-writer registry covers context-efficiency, ordinary and recovery memory writers,
  review-event publication, docs gardening, synchronous/background index publication, and later
  registered members. Every non-recovery entry fails fast with structured `upgrade_in_progress` during
  Upgrade under an executable bounded deadline; no entry may inherit indefinite blocking. Removing a
  registry member, its bounded policy, or the paused-state authorization check fails.

  Upgrade's synchronous index child performs computation and writes a verified staging receipt but
  never reacquires publication ownership; the lock-owning parent validates the receipt and finalizes
  authoritative index state. Detached code indexing launches only after both locks are released and a
  durable pending marker exists. A bounded real Upgrade → setup/indexer → parent-finalization probe,
  including the memory-backfill receipt path, proves no parent/child deadlock; removing the
  staging/finalization seam fails. Releasing publication ownership at any non-pause point fails.
  Lock path creation, backend import/use, acquisition, and
  publication-after-lifecycle failures all produce zero project writes. A lock-order reversal,
  upgrade-only lock, or yield-unlocked mutation fails. The JSON sentinel remains recovery state, not serialization.
- [x] AC-13: `review-policy-adoption-baseline.md` is reproducible from the fingerprinted eligible
  corpus and reports Council and specialist-lane deltas plus limitations. The measured 0%/0% result
  keeps the install default universal. A fixture cannot switch the default to targeted unless the
  20% Council, 15% lane, and zero-omission gate all pass or an explicit operator decision is recorded.
- [x] AC-14: The bridge bootstrap, bridge archive, stamped selection metadata, and feature archive all
  come from the canonical `build_pack.py` path, not synthetic fixtures. Bridge assertions cover its
  distinct `bridge_build_id`, protocol metadata, complete framework-only MANIFEST, absence of every
  project-surface member, rollback metadata, and absence of a new prompt-surface revision. Feature assertions cover its
  archive name, product `VERSION`, matching prompt-surface `framework_revision`, and MANIFEST membership
  for the runner, strict lock helper, protocol metadata, extension, renderer/backstop, and migration
  surfaces. A real colocated-artifact fixture first proves the unmodified tagged supported-floor runner
  refuses the feature before extraction, then invokes the standalone bootstrap directly and proves no
  old-runner render, stamp, prune, policy, garden, or index phase executes. It verifies only the complete
  framework tree is atomically swapped with rollback available, then proves protocol 2 selects the
  exact feature path once through `--pack` without looping. The old runner refuses a directly supplied
  feature pack before extraction with `bridge_release_required`; the builder-produced bridge runs only
  after the old project host is demonstrably shut down, changes no project-state bytes, installs
  protocol 2, and makes Prepare/review-event/Close unavailable throughout. The retry consumes the
  feature pack under protocol 2 and succeeds under the strict lifecycle and publication locks. Exact
  fixtures cover floor, immediately previous, and current protocol mappings; unknown/missing/malformed/
  decreasing versions; structured retry fields; standalone bootstrap containment and rollback; and
  project-surface byte equality across populated fixtures. Protocol-2 missing, syntax-broken,
  import-failing, and mismatched mandatory code fails
  before extraction. Mutations that bypass the real builder, invoke the old runner for bridge install,
  use a minimal/pruning manifest, confuse bridge identity with product `VERSION`, write a project
  surface, skip host quiescence or rollback verification, release either lock early, or omit the retry
  fail.
- [x] AC-15: The registry-backed upgrade guidance states legacy mapping, re-Prepare marking, failed
  phase and retry, blocked operations, ambiguity reporting, closed immutability, protocol-field
  interpretation, both structured protocol errors, bridge acquisition and invocation, host shutdown
  confirmation, the framework-only/read-only bridge boundary, the exact feature second hop, and
  protocol-2 malformed-code refusal. One mutation per carrier family and per bridge obligation proves
  that rendering, reconciliation, validation, and census cannot silently omit any obligation. A
  mandatory architecture decision records review-policy authority, receipt binding, shared-evaluator
  ownership, strict lifecycle/publication lock order, carrier-owner permissions, reconciliation, and
  the protocol-2 bridge; it is indexed in `docs/architecture/decisions/README.md` and linked from
  `docs/ARCHITECTURE.md`.

## Tasks

- [x] Re-measure council-gate load-bearingness after `1tr85` fixes the roster extraction; the eligible
  one-wave corpus is recorded in `review-policy-adoption-baseline.md` and does not justify changing
  the safe install default.
- [x] Implement and document the delivery-policy parser, upgrade mapping, roster derivation, and
  persisted policy receipt.
- [x] Extract the shared delivery evaluator and register its closure-only diagnostic set.
- [x] Make review evidence integrity and approval phase caller-authored and phase-scoped.
- [x] Implement non-closed wave re-projection and the versioned lifecycle-section reconciler.
- [x] Reconcile dashboard, canonical seeds/prompts, reference docs, and MCP tool descriptions.
- [x] Add red-first policy/evaluator/evidence/upgrade/reconciler tests and mutation controls.
- [x] Specify the bounded repair-class census, class-level reverification evidence, and the
  `do_now | maybe_later | dont_do_later` decision boundary in the review/evaluator contract.
- [x] Add the strict lifecycle-lock helper, publication-writer registry and fail-fast policies,
  checkpointed memory pause/resume, parent-owned index finalization, and platform-boundary fixtures
  required by AC-11 through AC-15.
- [x] Add protocol-v2 pack metadata, a real-builder standalone framework-only bridge bootstrap and
  artifact fixture, strict legacy-host quiescence, rollback, and the exact two-hop supported-floor path.
- [x] Author and index the mandatory architecture decision covering policy authority, receipt and
  evaluator ownership, lock order, carrier permissions, reconciliation, and the bridge protocol.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| decisions | architecture-reviewer | — | Resolve the open questions before implementation branches. |
| policy-and-evaluator | implementer | decisions | Depth policy, gating, shared evaluator. |
| migration | implementer | decisions | Config migration plus in-flight wave re-projection. |
| verification | qa-reviewer | policy-and-evaluator, migration | Red-first proofs, upgrade fixtures, non-Git target. |

## Serialization Points

- The open-question decisions land before implementation.
- The adoption baseline lands before any default-policy implementation; its failed materiality gate
  keeps the implementation default universal.
- `server_impl.py`, `review_evidence.py`, and `wave_lint_lib/wave_validators.py` are shared chokepoints.
- Lifecycle mutation locking is acquired before publication locking everywhere; Upgrade holds both
  continuously within each process-bounded transaction, permits only the checkpointed memory-validation
  pause, releases in reverse order, and permits no inverse order or indefinite outside-publisher wait.
- This change must not open until `1tr85-enh single-pass-review-lifecycle` closes.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md`, `docs/architecture/current-state.md`,
  `docs/architecture/testing-architecture.md`, `docs/architecture/domain-map.md`,
  `docs/architecture/layering-rules.md`, `docs/contributing/review-and-evals.md`,
  `docs/specs/mcp-tool-surface.md`, `docs/architecture/decisions/README.md`, and
  `docs/ARCHITECTURE.md`. A new mandatory ADR records the complete authority and protocol decision
  named in AC-15; implementation is incomplete until it is indexed and linked.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Defines the compatible policy transition and keeps primer depth distinct from delivery policy. |
| AC-2 | required | Establishes one persisted roster authority for every downstream consumer. |
| AC-3 | required | Prevents a stale approval from authorizing a changed review boundary. |
| AC-4 | required | Makes evaluator sharing a simplification without dropping close-only controls. |
| AC-5 | required | Stops the evidence builder from fabricating integrity claims. |
| AC-6 | required | Makes approval currency phase-honest. |
| AC-7 | required | Prevents upgrade from breaking in-flight waves or disabled projects. |
| AC-8 | required | Replaces repeatedly drifting prose migration with one idempotent mechanism. |
| AC-9 | required | Keeps operator-facing lifecycle narration aligned with executable policy. |
| AC-10 | required | Prevents literal-only repairs without turning every nearby observation into another review cycle or mandatory wave. |
| AC-11 | required | Establishes cross-platform and repository-boundary delivery confidence. |
| AC-12 | required | Serializes Upgrade with every lifecycle and publication mutation in one lock domain. |
| AC-13 | required | Prevents an unmeasured cost hypothesis from weakening the fresh-install default. |
| AC-14 | required | Proves incoming migration logic is usable by the runner that actually performs upgrade. |
| AC-15 | required | Makes the complete operator contract one registry-backed, mutation-proven family. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-29 | **Observe:** Closed the independently reproduced implementation gaps across the supported-floor upgrade, publication barrier, policy receipt, Prepare ordering, and real-carrier reconciliation. Protocol-1 now refuses before extraction; protocol-2 validates mandatory incoming code and freezes the consumed pack; releases carry all bridge artifacts; the bridge preserves product `VERSION`, verifies and consumes one staged archive, enforces repository/quiescence boundaries, and returns a path-safe hash-bound second hop. Upgrade policy planning occurs before project mutation and applies before carrier rendering. Direct/background index, lifecycle, CE, and corrupt-checkpoint paths fail closed. Prepare lints before publishing policy state, receipt IDs are recomputed, malformed receipts diagnose, and targeted Council decisions consume the persisted receipt authority. **Reflect:** Real v1.14 carrier reconciliation and retry are byte-stable, and production lint now consumes the same carrier registry. The operator-declined `docs/waves` parent-symlink case remains deliberately unimplemented; `.wavefoundry` symlink escape remains blocked. | Canonical suite 6,433/6,433 across 61 files; docs-lint clean with the existing reality-checker roster warning; focused upgrade 360/360, docs-lint 611/611, build-pack 103/103, review-policy 17/17, lifecycle-lock 17/17, protocol 7/7; executed v1.14 six-carrier reconciliation changed all six and produced an empty second retry. |
| 2026-07-29 | **Thought:** Repair the independently reproduced defects by bounded root-cause families: bridge selection/consumption, upgrade serialization/publication, receipt authority, and carrier reconciliation. **Gapfill:** Wavefoundry MCP retrieval tools are not attached in this Codex session, so the repair uses the codebase map followed by targeted `rg`/bounded reads. The operator explicitly declined the `docs/waves` parent-symlink finding as outside the realistic threat model; no code or AC claim will be added for it. | Three independent review lanes plus executed adversarial probes; operator direction on the symlink finding. |
| 2026-07-28 | Implemented the policy, receipt, evaluator, evidence, reconciliation, upgrade-transaction, publication-guard, index-finalization, and protocol-bridge workstreams. Corrected the final carrier census so every `direct_docs` member names a real validation-only path, including the dashboard review-policy narrative. The implementation tasks are complete; required AC checkboxes remain open for the independent delivery review rather than treating a green suite as proof of each exhaustive mutation/interleaving clause. | Exact-tree canonical suite: 6,419/6,419 across 61 files; docs-lint clean with one pre-existing reality-checker evidence warning; both edit gates closed; adoption fingerprints remain byte-identical. |
| 2026-07-28 | Closed the final readiness boundary: the builder owns a standalone framework-only bridge bootstrap and deterministic two-hop selection; Upgrade uses process-bounded dual-lock transactions with a checkpointed memory pause and parent-owned index finalization; outside publishers fail fast; the bridge recovery contract is registry-backed; and the architecture decision is mandatory and indexed. | Cycle-5 code, docs-contract, and performance reviews reproduced old-runner post-extract writers, bridge/product identity conflict, the multi-turn memory gate, parent/child index deadlock, indefinite publisher blocking, incomplete operator guidance, and a nonbinding ADR obligation. |
| 2026-07-28 | Completed the post-`1tsyx` adoption baseline. The one eligible high-risk wave requires Council under both universal and targeted policy and has no specialist-lane reduction, so the fresh-install default remains universal while targeted ships as opt-in. | `review-policy-adoption-baseline.md`; fingerprinted `1tsyx` wave, ledger, and change doc. |
| 2026-07-28 | Bound policy approvals to an exact append-only receipt ABI; reused the lifecycle lock domain with lifecycle-before-publication ordering; added one carrier registry, old-runner/new-pack compatibility, and an honest native-Windows boundary. | Final readiness seats: code-reviewer, docs-contract-reviewer, and reality-checker. |
| 2026-07-28 | Replaced the unexecutable legacy-runner renderer bridge with protocol-v2 metadata and a real-builder two-hop bridge pack; made lifecycle locking strict and census-complete; defined carrier-owner write permissions. | Final QA, release, and architecture seats reproduced the old-runner write window, optional-loader limitation, incomplete writer census, permissive lock failure, and domain-boundary ambiguity. |
| 2026-07-28 | Made the downstream-retirement ownership explicit after `1tsyx` withdrew its repeatedly drifting prose migration: this plan now owns complete replacement of already-installed carriers and requires production validation and tests to consume one vocabulary/scope contract. | Fifth repair review demonstrated an instruction/control contradiction, a vacuous spelling token, file-scoped allowance leakage, and a shipped validation narrower than the test census. |
| 2026-07-28 | Initially expanded the target-repo retirement channel into an idempotent, versioned lifecycle-section reconciler while leaving a prose bridge in `1tsyx`; the later entry above supersedes the bridge portion after further review showed it was itself another drifting source of truth. | Fifth-round `1tsyx` docs-contract review reproduced six escaped historical carriers and two incompatible Prepare prompt shapes; subsequent scope correction removed the prose bridge and left this plan as the sole downstream-migration owner. |
| 2026-07-28 | Added a bounded repair-class census and explicit stop/disposition rule: repair adjacent variants only when they share the root cause and admitted scope; require class-level reverification; allow low-value or unrelated observations to end as `maybe_later` or `dont_do_later`. | Operator direction after the multi-cycle `1tsyx` delivery review exposed both literal-only repairs and unnecessary pressure to pursue every observation. |
| 2026-07-28 | Created as the deferred half of the review-lifecycle simplification, carrying the readiness council's findings as durable input so the analysis is not repeated. Not ready to admit: several original answers were shown unsound and need re-deciding. | Readiness council seat reports for wave `1tsyx`; `server_impl.py:2506`, `:2530-2537`, `:14298`; `review_evidence.py:1149`, `:1423-1438`, `:1950`, `:1960-1965`, `:2502-2524`; `seeds/215-wave-council.prompt.md:30-36` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-28 | Make `build_pack.py` emit a standalone framework-only bridge bootstrap and two separately identified archives; bypass the old runner's post-extract pipeline for bridge installation, then select the feature by explicit protocol-2 pack path. | The supported-floor runner has ambient archive selection and continues into project-writing render/prune/policy/garden/index phases, so it cannot safely install a minimal bridge pack. | Depend on archive semver order or old-runner hooks — rejected as nondeterministic and mutation-prone. Ask the operator to hand-copy framework files — rejected as unverified and non-atomic. |
| 2026-07-28 | Hold lifecycle and publication locks continuously within each Upgrade transaction; use one fsynced, recovery-writer-only memory-validation pause; finalize child-computed index state in the lock-owning parent; fail outside publishers fast. | A process cannot hold an OS lock across the existing multi-turn memory return, and a parent holding publication while waiting on a publishing child deadlocks. The checkpointed pause and parent finalization preserve exclusion without impossible lock lifetime or slow-machine hangs. | Hold locks across operator turns — impossible. Let the child reacquire the parent-held lock — deadlocks. Release after preflight without a restrictive checkpoint — permits mixed state. |
| 2026-07-28 | Record the authority split and two-hop protocol in one mandatory, indexed ADR. | Review policy, receipts, evaluator ownership, lock order, carrier permissions, reconciliation, and bridge semantics form one durable architectural boundary that cannot remain an optional documentation note. | Treat the existing architecture-doc list as sufficient — rejected because it does not preserve the decision and rejected alternatives as one indexed authority record. |
| 2026-07-28 | Use `disabled | targeted | universal` for delivery policy; keep readiness Council whenever review is enabled, keep primer depth separate, and retain universal as the install default until the measured adoption gate passes. | It creates a safe risk-selected path without converting a one-wave, 0%-reduction sample into a weaker default. | Make targeted the fresh default immediately — rejected by the pre-implementation measurement. Remove Council as a gate entirely — rejected because it is the only effective gate on most historical waves. |
| 2026-07-28 | Persist the derived delivery roster in `## Participants` and bind it into a typed readiness receipt. | Review and Close already parse Participants; persisting once is simpler and auditable, while the receipt detects stale approvals after edits. | Re-derive independently at each boundary — rejected as drift-prone. Add a second roster sidecar — rejected as unnecessary authority. |
| 2026-07-28 | Share a delivery evaluator through a common result plus a registered closure-only delta. | It removes duplicated evaluation while preserving deliberate Close-only controls and gives tests an exact mutation target. | Force Review and Close to be identical — rejected because Close owns secrets, memory, unchecked-AC, operator, and transition checks. Leave separate functions — rejected because the shared blocking state continues to drift. |
| 2026-07-28 | Require caller-authored integrity checks and explicit approval phase for new events while validating historical records unchanged. | The current builder claims facts it cannot know and labels every approval delivery; explicit inputs make the ledger honest without rewriting sealed history. | Keep the single confirmation boolean — rejected as non-falsifiable expansion. Rewrite historical ledgers — rejected by append-only compatibility. |
| 2026-07-28 | Replace prose-directed downstream cleanup with a versioned, marker/known-baseline lifecycle reconciler that refuses ambiguity. | Five `1tsyx` review rounds demonstrated that prose and duplicated vocabularies cannot reliably migrate heterogeneous target repositories. | Continue adding prose literals — rejected as the repeated root cause. Replace whole files — rejected because project-authored surrounding text must survive. |
| 2026-07-28 | Use a builder-produced protocol-v2 bridge artifact and standalone bootstrap instead of attempting a one-pass floor-to-feature upgrade. | The tagged floor runner cannot make missing or broken incoming extensions fatal and its post-extract path writes project state. A two-hop bootstrap stops a valid feature pack before extraction, installs strict protocol support without entering that pipeline, and then retries under protocol 2. | Renderer-only backstop — rejected because post-extract writes first. Treat the optional extension as mandatory — rejected because the old runner cannot enforce it. Claim arbitrary malformed legacy packs are safe — rejected as unfalsifiable. |
| 2026-07-28 | Require a bounded same-root-cause census during repair, paired with an explicit stop/disposition rule. | A literal-only repair invites another cycle for an adjacent variant, while an unbounded "look for related issues" instruction invites scope creep. The bounded family plus `maybe_later`/`dont_do_later` outcomes addresses both failure modes. | Repair only the reported reproduction — rejected as too narrow. Re-review the whole area after every finding — rejected as unbounded. Automatically create follow-up waves for every observation — rejected as low-value churn. |
| 2026-07-28 | Defer this scope out of wave `1tsyx` rather than carrying one sixteen-requirement cutover. | The combined AC set could not distinguish simplification from relaxation, and part of the cost case was refuted against code. This half needs its own review boundary and its own positive ACs. | Keep one cutover — rejected after unanimous CHANGES REQUESTED. |

## Risks

| Risk | Mitigation |
| --- | --- |
| The old runner mutates project surfaces or prunes framework files while installing the bridge. | Bypass its post-extract pipeline: the builder-emitted bootstrap verifies hashes and quiescence, atomically swaps a complete framework-only tree with rollback, then passes the exact feature path to protocol 2. |
| A non-lifecycle publisher exposes mixed project state or waits indefinitely during Upgrade. | Use process-bounded dual-lock transactions, a restrictive fsynced memory pause, parent-owned finalization, and registry-enforced fail-fast `upgrade_in_progress` responses with bounded contention tests. |
| The deferred analysis is lost and re-derived expensively. | The council's findings are recorded here with file and line evidence rather than as a pointer to a closed wave. |
| Decisions are made from pre-fix measurements. | Requirement 13 and `review-policy-adoption-baseline.md` bind default adoption to the corrected post-`1tsyx` corpus and retain universal when the materiality gate is not met. |
| Prohibition-shaped ACs reappear. | Stated as an explicit constraint in the Acceptance Criteria section. |
| A sibling search becomes an open-ended second review or expands repair scope silently. | Restrict the census to the named defect class and bounded family; require materiality, admitted scope, and low repair risk for `do_now`; disposition everything else without blocking. |
| The protocol bridge becomes a second feature release or permits mixed-version writes. | Build it from the canonical pack path with byte-identical project surfaces, read-only hooks, verified host quiescence, explicit protocol metadata, and a required second-hop retry under the strict lifecycle lock. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
