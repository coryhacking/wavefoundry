# Logging a Repair Lapses the Approvals of Everything the Repair Did Not Touch

Change ID: `1ugk9-bug progress-log-appends-lapse-unrelated-approvals`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-05
Wave: `1uhcb review-cycle-churn`

## Rationale

`policy_input_digest` (`review_policy.py:424-451`) hashes each change doc through
`canonical_review_policy_body`, which normalizes **only** the gardener date line
(`gardener_metadata.py:48-55`). Every other byte is digested, including the Progress Log.

`AGENTS.md` **Change Doc Tracking (Real-Time)** requires a repairer to record what they did. So the
required act of logging a repair changes the body bytes, which changes the digest, which supersedes
the receipt. Two consequences follow, and the exact blast radius is stated below because an earlier
draft of this Rationale overclaimed it and a prepare lane then underclaimed it in the other
direction.

**What lapses, measured.** Receipt binding is phase-scoped. `policy_receipt_id` is legal only on a
readiness-phase approval (`review_evidence.py:3139-3145`), and the currency check only compares
receipt ids when `approval_record_phase` returns `readiness` (`review_evidence.py:1311-1319`;
`approval_record_phase` at `:1026-1036` returns the EXPLICIT `approval_phase` when present, falling
back to key-based inference only for legacy records). Executed against wave 1ugk8's real ledger, its
18 approval records split cleanly:

- **10 readiness-phase approvals, every one `policy_receipt_id`-bound and therefore lapsing on any
  supersession**: the council readiness approval plus all six prepare lanes (code-reviewer,
  qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, qa).
- **8 delivery-phase approvals, none receipt-bound, all surviving**: the six delivery lanes, the
  delivery council, and operator-signoff.

So a Progress Log append lapses the readiness ROSTER, not one approval and not everything: seven
signoff keys in 1ugk8 once prepare-phase lane review had completed. It never touches a delivery
approval, a finding head, or a repair record.

**And staleness blocks, independently of what lapsed.** `review_policy_receipt_stale` is in
`_guided_review_authority_blocker`'s `blocking_codes` (`server_impl.py:14358-14375`), so while the
receipt is stale the guided signoff-recording actions are gated until a re-Prepare mints a fresh
receipt, which is itself what lapses the readiness roster.

Observed in wave 1ugk8 (2026-08-04): the receipt was minted five times
(`ba64de5452e1` → `19a3002bb808` → `22acce406d73` → `0f1fbbd64e01`, plus the readiness re-record)
and readiness was re-recorded under context ids `-r2` through `-r5`. Two of those cycles were driven
by findings that were entirely editorial: a doc quantifier and a set of line citations that had
drifted by ten lines. Note what the `all eight signoffs read pending` observation after
implementation did NOT show: those were pending because the delivery cycle had not yet been
recorded, not because a supersession had cleared them. Do not cite that symptom as evidence of
lapsing.

The cost is therefore per-repair rather than superlinear in the original sense, but it is not one
approval: each editorial nit costs a re-Prepare plus a re-record of the whole readiness roster, and
gates guided signoff recording until it is done. Wave 1uhcb, this change's own wave, paid five
readiness re-records before implementation even began.

This is scoped deliberately narrowly. It changes **no** review coverage: the same lanes run, the
same findings block, the same repair-independence audit applies. It only stops re-litigating
approvals that nothing invalidated.

**This extends an established remedy rather than inventing one.** The gardener-date normalization
that `canonical_review_policy_body` performs today exists because wave 1tz6l's
`1tz6k-bug review-policy-receipt-metadata-stability` found that a metadata verification date was
staling receipts and forcing exactly this kind of needless re-Prepare. That change fixed one
non-substantive carrier. The Progress Log is the second, and it is worse, because unlike a date
stamp it is written by the very act the review loop demands. Follow that change's shape.

## Requirements

1. **Progress-Log content is excluded from the review-policy digest. Exactly ONE section is
   excluded, and this is it.** `canonical_review_policy_body` replaces the body of the
   `## Progress Log` section with a stable sentinel before hashing, exactly as it already does for
   the gardener date. Appending, editing, or reordering Progress Log rows must produce an unchanged
   `policy_input_digest`, so a recorded approval survives the logging of a repair it is unrelated to.
2. **`## Session Handoff` is deliberately NOT excluded.** An earlier draft excluded it as a second
   fixed-pointer section; an independent review recommended narrowing to the Progress Log only and
   that is adopted. Three reasons, the third measured: it is not the observed source of
   repair-tracking churn, which is the Progress Log append that `AGENTS.md` mandates; no validator
   anywhere in `wave_lint_lib` references the section, so nothing keeps
   it a pointer; and the corpus already deviates, carrying about 710 `## Session Handoff` headings
   against about 678 canonical pointer sentences, so roughly thirty change docs hold something else
   there today (counts are match counts, so treat the gap as approximate but real). Excluding an
   unenforced section whose invariant is already broken would buy nothing and hide whatever those
   docs contain. The Progress Log earns its exception because it is the MANDATED repair-tracking
   surface and it gains an explicit rule (Requirement 2b); the handoff pointer earns nothing and is
   not the source of the loop. One exception, not two.
   Note what the corpus evidence does and does not prove, because an earlier draft of this
   requirement overreached: the gap proves the pointer invariant is BROKEN, and it does not prove
   nobody edits the section. If anything it suggests the opposite. The supportable claim is the
   narrower one stated above, that Session Handoff is not the observed churn source.
2a. **The exclusion is HASH-ONLY; no reader changes.** The section stays in the file verbatim.
   This matters because the Progress Log does have a programmatic consumer:
   `_retrieval_posture_gap` (`server_impl.py:15941`) reads the change doc and clears its advisory on
   finding the substring `Gapfill:` (`:15934`). That reader is unaffected, and a test must prove it
   still clears after the change so nobody later reads "excluded from the digest" as "removed from
   the doc".
   **Reader census corrected.** An earlier draft of this requirement, and a Progress Log row below,
   claimed the council census found no OTHER production reader of Progress Log content. That is
   false, and there are two more: `server_impl.py:16327` calls
   `_section_body(ct, "## Progress Log")` and feeds the parsed rows into the wave-close change
   summary, and `dashboard_lib.py:1075` calls `_parse_progress_log` on the section that
   `_extract_section(text, "Progress Log")` returns. Both read the FILE, not the canonicalized digest
   body, so the hash-only conclusion and the no-regression conclusion both still hold unchanged: this
   is a correction to the census claim, not a newly discovered regression. Stated so a later reader
   who finds either call site does not conclude the change shipped on a false premise.
2b. **The Progress Log NARRATES; it must not AMEND.** Requirement 1's safety rests on the Progress
   Log carrying no reviewable claim, and as written that was an assumption rather than a rule. The
   council disproved it as a description of current practice: this repo routinely ANNOUNCES scope
   changes in Progress Log rows. Real examples, none adversarial:
   `12as6-enh:275-276` (an expansion adding resume semantics and a new status vocabulary, then a
   second row announcing a **hard-break envelope change**), `12sp5-enh:105` (lint-only expanded to
   full automated Council review), `1p92t-bug:346` (a Level-3 finding expanding scope mid-flight),
   `1u8jc-enh:121` (scope narrowed), and `1uhfx-bug:89,91` (both extensions in the wave released
   today). So the seed passage in Requirement 6 must also state the rule that makes the exclusion
   safe: a scope, requirement, or AC change is recorded in the **digested** section that owns it, and
   the Progress Log row points at that edit rather than substituting for it. Without this rule the
   change opens a real hole; with it, the hole is closed by the same convention that already governs
   how these docs are written.
3. **Every other section stays digested, byte for byte.** Rationale, Requirements, Scope,
   Acceptance Criteria, Tasks, Agent Execution Graph, Serialization Points, Affected Architecture
   Docs, AC Priority, Decision Log, Risks, and Session Handoff must all keep their current
   lapse-on-edit behavior. A plan change still lapses approvals; that property is the point of the
   receipt and is not being weakened.
4. **Section detection is anchored, not heuristic.** Match the canonical `## Progress Log` heading at
   the start of a line and end the region at the next `## ` heading or end of file. A fenced code
   block containing a lookalike heading must not be treated as a section boundary. **A real fence
   toggle is required, and the precedent this requirement originally cited is the wrong one:**
   `gardener_metadata.py:20-26` is frontmatter-boundary logic, safe from fenced lookalikes only
   because it never enters the body, so it offers a body-section scanner zero reusable protection.
   Mirror `commit_provenance._without_fenced_code` (`commit_provenance.py:81-94`) instead, the tree's
   one correct fence tracker, toggling only when the marker matches the currently open fence so a
   `~~~` inside a ``` block does not close it. Do NOT reuse
   `wave_lint_lib/wave_validators.py:126` `_extract_sections`, which is fence-blind. Keep the heading
   pattern a module constant rather than a public parameter: a per-section helper keeps a future
   second exclusion cheap, and that is not a licence to add one without its own evidence.
5. **An absent, duplicated, or malformed section degrades to today's behavior.** Zero matches or
   ambiguous multiple matches return the body unchanged and still digested, mirroring
   `normalize_gardener_date`'s `len(matches) != 1` guard. A doc missing a Progress Log must not
   error.
6. **A narrow editorial stop condition and the narrate-not-amend rule are stated in the review
   seeds.** After the first delivery review cycle, an editorial-only finding (wording that is true
   but imprecise, drifted citations, formatting) is repaired inline within the current cycle and
   recorded in the Progress Log; it does not by itself open another repair cycle. Every finding that
   needs verification, a boundary repair, or escalation retains its existing action-matrix route —
   including missing test coverage, behavior, security, architecture, scope, requirements, and
   acceptance criteria. Name the escape hatch explicitly: an editorial finding that makes a shipped
   claim FALSE is a correctness defect, not an editorial one. The same passage carries Requirement
   2b's rule, because the two are one idea: the Progress Log becomes safe to exclude from the digest
   precisely because it narrates rather than amends.
   **The seed is `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`, in the Finding
   classification block at `:66-70`.** Named here because a prepare lane established there is no
   seed that generates the `Review wave` prompt body, so the obvious-looking carrier is not a seed at
   all. That block is the canonical authority for whether a finding opens a new cycle (`:66` already
   reads "after an exceptional named checkpoint or the delivery review, before deciding which loop
   level to activate"), it sits directly under the Finding escalation table at `:55-64` whose last row
   is already an exit-loop case, and `:41-45` is the only place in the seeds that defines what
   Progress Log entry types are for, so narrate-not-amend reads in context there as a further
   entry-type constraint. Requires `seed_edit_allowed`.
   **Propagation to EXISTING repos, corrected.** An earlier draft of this requirement claimed that
   upgrades never touch an existing project review prompt, so the rule would reach fresh installs
   only. That is FALSE and must not be restated. The whole-file lifecycle template
   (`install/lifecycle-prompts/review-wave.prompt.md:24`) is indeed missing-only per `seed-100` item
   14, but the review-policy **reconciler** owns targeted exact-string replacements inside existing
   project prompts: `review_policy_reconcile.py:67-81` keys on
   `docs/prompts/review-wave.prompt.md` and already rewrites the neighbouring passage at `:73-75`
   ("Blocking findings return the wave to implementation (Level 2 loop)" becomes the recorded-repair-
   cycle language). Related renderer carriers: `render_agent_surfaces.py:1164` and
   `review_policy.py:233`.
   So the behavioral rule lands in seed-180, and **if it must surface in existing project prompts it
   lands as a reconciler replacement pair**, which is the mechanism that actually reaches them.
   Decide that explicitly rather than assuming either direction. Three cautions if the reconciler
   carrier is used: memory `1u2ju-mem` marks `review_policy_reconcile.py` FRAGILE (two separate
   repairs in wave 1tz6l) and requires rerunning `ReviewPolicyReconcilerTests`; a replacement
   pair matches an exact string, so it silently no-ops against a repo whose prompt has drifted; and
   the reconciler cannot carry a new pair on its OWN installing upgrade, because
   `upgrade_wavefoundry.py:4548-4554` builds the replacement plan pre-extraction and `:4700-4711`
   applies that frozen plan, with no fresh-code backstop. The rule therefore reaches an existing
   repo's project prompt on the NEXT upgrade, which makes the reconciler a seed-160 class (b)
   carrier and must be disclosed as such (Requirement 9).
7. **`REVIEW_POLICY_EVALUATOR_VERSION` bumps from 2 to 3.** Decided at plan time, not left open;
   rationale in the Decision Log. The bump is a labeling requirement, not the mechanism: the digest
   changes for every wave whether or not the constant moves, because
   `canonical_review_policy_body`'s output feeds `policy_input_digest` (`review_policy.py:434-451`).
   Nothing in the tree branches on `evaluator_version` (its only production uses are that hash input
   and the stamp at `server_impl.py:6893`), so without the bump two different digest algorithms both
   stamp `evaluator_version: 2` and the permanent `events.jsonl` record cannot say whether a digest
   moved because a plan was edited or because canonicalization changed.
   Three carriers move together:
   - `review_policy.py:25` — the constant.
   - `test_review_policy.py:343` `test_evaluator_version_two_is_the_shipped_transition_boundary` —
     a deliberate tripwire asserting the constant equals 2. It must be consciously updated, not
     deleted, and it keeps pinning the current shipped boundary.
   - `test_server_tools.py:27913` `test_public_prepare_converges_once_from_evaluator_v1_to_v2` — this
     test BREAKS on the bump and is not merely a template. It patches the constant to 1, prepares,
     unpatches, and asserts `receipts()[-1]["evaluator_version"] == 2` at `:27947`; once the constant
     is 3 that assertion fails. So it must be retargeted, pinning the old boundary explicitly by
     patching both `review_policy` and `self.srv` to 2 the way `:27924-27928` patches to 1, and a
     v2-to-v3 case added in the same shape (patch to old, prepare, assert a receipt at old, unpatch,
     prepare, assert exactly ONE new receipt at new, prepare a third time, assert it settles), per
     memory `1ty9f-mem`. TWO test pins move on this bump, not one.
8. **Prepare-owned plan CONTENT is populated before the council runs, not after it.** Caught live on
   this wave: filling the AC Priority table at Prepare superseded the receipt and lapsed the
   readiness approval that had just been recorded, because AC Priority is genuinely
   requirement-bearing and correctly stays digested. So the lifecycle currently mandates an edit at
   exactly the moment it invalidates the approval it just collected. This is a fourth instance of
   the same churn and the ONLY one of the four that Requirement 1 cannot fix, because the remedy is
   ordering rather than canonicalization.
   Applies to both surfaces the operator named:
   - **AC Priority** — one row per AC with its priority and rationale, filled when the ACs are
     written.
   - **Tasks** — the task list ENUMERATED completely at plan time, so implementation checks boxes
     rather than adding rows.
   Three carriers, all verified present:
   - `server_impl.py:16745` — the scaffold generator emits the placeholder `(Populated at Prepare
     wave.)`, which is the instruction telling every future author to fill it late. Change the
     emitted text to direct a plan-time fill.
   - `docs/plans/plan-template.md:60` — the same placeholder in the template doc. **This file is
     project-local and does NOT ship in the pack** (nothing in `build_pack.py` references it; it is
     seeded by `seeds/040:30` at install). Editing it corrects Wavefoundry's own copy only.
     **DECIDED (operator, 2026-08-05): add the `seeds/160` migration bullet**, following the
     established pattern already used three times for plan-template migrations
     (`seeds/160:194-195`, `:367-369`, `:474-475`), plus the matching verification-checklist line, so
     existing target repos actually receive the corrected instruction. The operator kept
     Requirement 8 in this wave after a reviewer recommended splitting it, so it lands complete
     rather than Wavefoundry-local.
   - `seeds/040-docs-structure-bootstrap.prompt.md:36` — the install-time template seeder, which
     specifies the `## AC Priority` section without saying when it is filled. It does not carry the
     placeholder string, so the plan's census claim stands, but if a freshly installed repo should
     scaffold a plan-time-fill template then this needs the same one-clause addition. Decide and
     record; silence here is how the corrected instruction fails to reach new repos.
   - `.wavefoundry/framework/seeds/170-plan-feature.prompt.md:80` — the seed that owns AC and Task
     authoring. It currently says nothing about WHEN the priority table is filled; it gains the
     ordering rule.
   Census result, run rather than assumed: no seed contains the string `Populated at Prepare`, so
   the scaffold and the template are the only instruction carriers. Existing change docs keep their
   text and are not regenerated; only newly scaffolded docs get the corrected placeholder. The
   `ac_priority_unpopulated` check at Prepare stays exactly as it is, as the backstop for an author
   who skips the plan-time fill.
   **Boundary, stated so it is not conflated:** this covers ENUMERATION and CONTENT only. Checkbox
   STATE (`[ ]` to `[x]` to `[~]`) still changes during implementation, cannot be pre-populated, and
   remains the deferred follow-up named in Out of scope, where `[~]`'s required inline rationale is
   what makes it a harder problem than a simple exclusion.
9. **The one-time re-Prepare is disclosed, not absorbed.** Any wave that is readied or open in a
   target repo when this lands goes stale once at its next `wf_prepare_wave` and its READINESS-phase
   approvals lapse once; delivery approvals, finding heads, and repair records are untouched. State
   this in the CHANGELOG bullet, which requires **creating** a new `## [1.15.4] - unreleased`
   section: `CHANGELOG.md:9` is the released `## [1.15.3] - 2026-08-04`, and `build_pack.py --version`
   hard-fails without a matching section, so an append to the released section is the wrong move.
   Name BOTH recovery paths, not just the heavier one: `gardener_metadata` sits in server_impl's
   reload-purge set (`server_impl.py:30-43`) and this change adds no new tool, so `wf_reload_mcp`
   suffices as well as a full host restart. Add the mid-review case so its first field report is
   recognized rather than escalated: on a wave already open for review, the stale receipt gates
   guided signoff recording until the re-Prepare, and recorded findings and delivery approvals are
   unaffected. Add the mechanism behind "closed waves are untouched" rather than asserting it:
   receipt-chain validation re-derives ids from the fields stored ON the record
   (`review_evidence.py:3863-3899` via `receipt_semantic_fields`, `review_policy.py:488-502`), never
   from change-doc bytes, so every historical receipt in every sealed archive continues to validate
   after both the canonicalization change and the bump. Two boundaries to state correctly
   rather than conflate: closed waves are untouched, because their receipts are history and sealed
   archives are never retroactively invalidated; and this is NOT the config-migration path, so
   wave 1uf69's no-op guard (which stops a no-op `enabled`/`delivery_mode` migration from marking
   readied waves) does not apply. The churn arrives through ordinary digest staleness in the
   server, so it takes effect after the post-upgrade host restart. Do not add a compatibility shim
   that accepts either canonicalization: it would permanently encode two algorithms to avoid a
   single one-time re-Prepare.
   **Seed-160 class split, corrected.** A prepare-phase release lane classified every component as
   class (c) and concluded there is **no class (b) component**. That is wrong for one carrier and the
   claim must not be restated: the digest exclusion, the evaluator constant, and the scaffold text
   are class (c) (server-resident, effective after `wf_reload_mcp` or a host restart), the seed edits
   are effective as soon as the pack extracts, but the **review-policy reconciler pair is class (b)**.
   Its replacement plan is built pre-extraction (`upgrade_wavefoundry.py:4548-4554`) and the frozen
   plan is what applies (`:4700-4711`), so the installing upgrade makes no edit to
   `docs/prompts/review-wave.prompt.md` and the sentence arrives on the NEXT upgrade; a third pass is
   idempotent. The CHANGELOG bullet carries that per-bullet transition disclosure including the
   sentence that stops the false field report, namely that the one-run lag is the frozen-plan
   preflight working as designed rather than the reconciler failing. No pack-hook bridge is added:
   the behavioral rule itself is live immediately in the seeds, so the lag costs an existing repo's
   project-prompt copy one upgrade and nothing else.

## Scope

**Problem statement:** the review-policy receipt digests repair-tracking prose, so the mandatory act
of recording a repair lapses approvals that the repair could not have invalidated, making each
trivial finding cost a full re-record of the signoff roster. The target is FALSE invalidation only.
Legitimate re-review, where the plan or the implementation actually changed, is preserved unchanged:
the 1uhfy ledger's six readiness approvals were mostly earned by three real scope expansions, and
this change would not have suppressed a single one of them.

**In scope:**

- `canonical_review_policy_body` in `.wavefoundry/framework/scripts/gardener_metadata.py`, plus its
  section-region helper. ONE section excluded: `## Progress Log`.
- Tests in `test_review_policy.py`, which is the unambiguous home: no `test_gardener_metadata.py`
  exists and that module already owns every gardener-metadata assertion (`import gardener_metadata`
  at `:23`). Digest stability and sensitivity go beside
  `test_policy_digest_ignores_only_one_canonical_gardener_date` (`:816-830`), reusing its local
  `digest(body)` closure so AC-1's "real append" clause is satisfied through the actual
  `policy_input_digest`; the degrade quadrants go beside
  `test_policy_and_drift_consumers_share_the_same_narrow_boundary` (`:832-860`). Do not create a new
  module for four tests.
- One stop-condition passage in the review seed that owns delivery-review cycles.
- The Prepare-owned-content ordering rule (Requirement 8): the scaffold placeholder in
  `server_impl.py`, the same placeholder in `docs/plans/plan-template.md`, and the ordering rule in
  `seeds/170-plan-feature.prompt.md`.
- `REVIEW_POLICY_EVALUATOR_VERSION` in `review_policy.py`, its boundary pin in
  `test_review_policy.py`, and a v2-to-v3 convergence test in `test_server_tools.py`.
- `CHANGELOG.md`, including the one-time re-Prepare disclosure.

**Out of scope, deliberately:**

- **Which lanes get required.** `select_required_review_lanes` (`review_policy.py:391-421`) scores
  risk triggers by substring-matching change-doc **prose**, with no diff or magnitude input, so a
  thorough plan draws more lanes than a sloppy one. In wave 1ugk8 the release lane was required by
  `risk trigger: upgrade_wavefoundry.py, build_pack.py` when the change never touched
  `build_pack.py`; the plan only discussed it. That is a real defect and the natural follow-up, but
  it **reduces review coverage**, so it deserves its own change and its own careful pass. This
  change is coverage-neutral; do the coverage-neutral one first.

  THIS change's own admission reproduced the defect twice, which is the specimen set the follow-up
  should be built against. Its roster came back `code-reviewer, qa-reviewer, release-reviewer`, and:
  (a) the release lane fired on `risk trigger: upgrade_wavefoundry.py, build_pack.py` because the
  paragraph you are reading QUOTES those filenames as evidence; the change touches neither. (b) The
  code lane's reasons include `risk trigger: ... .js ...` although nothing here involves JavaScript,
  because `.js` is a substring of `events.jsonl`, which this plan names repeatedly as the review
  authority. So the trigger corpus penalizes citing evidence, and one of its tokens cannot
  distinguish a JavaScript file from a JSONL ledger. Both were left uncorrected here on purpose:
  gaming the evaluator by deleting load-bearing evidence from a plan would be the wrong fix, and the
  right fix belongs to the follow-up.
- **AC and task checkbox STATE**, as distinct from the enumeration Requirement 8 now covers.
  Flipping `[ ]` to `[x]` also changes the digest and also lapses
  approvals, on the same faulty grounds. It is a larger question because a `[~]` marker carries a
  required inline rationale that IS substantive and must stay digested, so normalizing checkbox
  state is not the same shape of fix. Named here so it is a known follow-up rather than a gap.
- Any change to finding classes, the evidence schema, cycle caps, or the repair-independence audit.
- Any change to what blocks close.

## Acceptance Criteria

- [x] AC-1: Appending a Progress Log row to an admitted change doc leaves `policy_input_digest`
  and the derived receipt id unchanged, proven by computing the digest before and after a real
  append rather than by asserting on the canonicalizer alone.
- [x] AC-2: Editing Rationale, Requirements, Scope, an AC's text, Tasks, Serialization Points, a
  Decision Log row, or a Risks row each still changes the digest. One case per surface, so a
  future over-broad exclusion fails loudly.
- [x] AC-3: A `## Progress Log` heading inside a fenced code block does not open or close a
  region, and a doc with no Progress Log, or with two, is returned unchanged and still digested.
- [x] AC-3a: Editing the `## Session Handoff` section still changes the digest, pinning that the
  narrowing to one exclusion actually held and that a future refactor cannot quietly re-add it.
- [x] AC-4: A recorded **readiness-phase** approval survives a Progress-Log-only repair end to end
  through the public path: record readiness approvals, append a Progress Log row, then
  `wf_prepare_wave` appends NO new receipt and `wf_review_wave` reports those approvals still
  current rather than `review_policy_receipt_stale`. It must name readiness specifically and assert
  the no-new-receipt condition: delivery-phase approvals are not receipt-bound today, so a test
  written against a delivery lane passes green on the unmodified tree and proves nothing, which is
  the vacuity mode memory `1ty9f-mem` records.
- [x] AC-5: The seed states the stop condition including the escape hatch AND the narrate-not-amend
  rule from Requirement 2b, while preserving the existing action-matrix route for every
  non-editorial finding, and docs-lint passes.
- [x] AC-5a: A test asserts the DIVERGENCE, namely that the canonicalized digest body carries the
  sentinel while the on-disk file still contains `Gapfill:`, so hash-exclusion and file-presence hold
  simultaneously. The existing `test_retrieval_posture_gap_cleared_by_gapfill_and_by_retrieval`
  (`test_server_context_efficiency.py:1919`) is cited as a non-regression control, NOT as new
  coverage: `_wave_has_gapfill_note` (`server_impl.py:15931-15938`) reads whole files, so it is
  already green and cannot fail from a hash-only change. Memory `1u8m9-mem`'s summary is corrected
  per the Affected Architecture Docs census.
- [x] AC-6: `REVIEW_POLICY_EVALUATOR_VERSION` is 3, its boundary pin in `test_review_policy.py` is
  updated rather than deleted and still asserts the current shipped boundary, and a v2-to-v3
  public-prepare test proves exactly one new receipt is appended on the first prepare after the
  bump and that a third prepare settles.
- [x] AC-7: The CHANGELOG bullet discloses the one-time re-Prepare for readied and open waves,
  states that closed waves are untouched, and does not claim the effect is immediate (it lands
  after the post-upgrade host restart). Docs-lint passes and the full framework suite passes.

- [x] AC-8: The scaffold generator and `plan-template.md` no longer instruct a Prepare-time fill of
  the AC Priority table, `seeds/170-plan-feature.prompt.md` states that AC Priority is populated and
  Tasks are fully enumerated before the prepare council runs, and the `ac_priority_unpopulated`
  backstop still fires on a doc that skipped it (proven by test, since a placeholder change that
  silently disabled the backstop would trade one churn source for a missing gate).
## Tasks

- [x] Red-first: digest-stability and digest-sensitivity tests, plus the fenced-lookalike and
  ambiguous-section guards
- [x] Extend `canonical_review_policy_body` with the ONE section exclusion, adding a
  `normalize_progress_log(text, *, replacement)` helper between `normalize_gardener_date` (ends
  `:45`) and `canonical_review_policy_body` (`:48`), keyword-only to match the existing style, with
  the `len(matches) != 1` degrade guard transferred, plus both new names in `__all__`. Do NOT extend
  the doc-drift consumer: `index_state_store.py:3374-3375` deliberately shares only the DATE
  boundary. Rename or comment `test_policy_and_drift_consumers_share_the_same_narrow_boundary`
  (`test_review_policy.py:832`), whose name encodes an invariant this change narrows
- [x] Public-path test for AC-4
- [x] Bump the evaluator constant to 3; update its boundary pin; add the v2-to-v3 convergence test
- [x] Seed passage: stop condition plus the narrate-not-amend rule
- [x] Review-repair: narrow the stop condition to editorial-only findings and pin that the shipped
  review-prompt replacement converges byte-stably. Test execution is intentionally deferred at the
  operator's direction; static review and docs-lint remain recorded below.
- [x] Requirement 8 ordering: correct the scaffold placeholder and the template, add the ordering
  rule to seed-170, add the `seeds/160` plan-template migration bullet plus its verification-checklist
  line, add the one-clause addition to `seeds/040:36`, and pin that the `ac_priority_unpopulated`
  backstop still fires
- [x] Prove the `Gapfill:` advisory reader still clears; correct memory `1u8m9-mem`'s summary
- [x] Full suite, docs-lint, CHANGELOG bullet with the re-Prepare disclosure

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          | Single-file behavior change plus tests and one seed passage; seed edit needs `seed_edit_allowed` |


## Serialization Points

- `.wavefoundry/framework/scripts/gardener_metadata.py`; `test_review_policy.py`; the review seed
  (gated); `CHANGELOG.md`

## Affected Architecture Docs

Census RUN at Prepare (2026-08-05), not deferred. One carrier found, and it is not a doc:

- `docs/agents/memory/1u8m9-mem fold-census-findings-into-plan-text-before-minting-the-revie.md`
  states "the review-policy receipt digests the change-doc bytes" and that "amendments after the
  mint supersede the receipt and lapse all recorded approvals". Its **rule stays correct** and this
  change does not weaken it: a substantive amendment must still be folded before the mint. Its
  **stated reason becomes imprecise**, because after delivery the receipt digests every byte except
  the progress-tracking sections. Update the record's summary; do not retire it.

The census scope lesson, which the plan originally missed: **memory records are living, retrievable
surfaces that agents act on**, so a census that sweeps only seeds, specs, architecture, and
contributing docs is incomplete. Include `docs/agents/memory/`.

No architecture or spec surface asserts that any change-doc edit supersedes the receipt, so nothing
under `docs/architecture/` or `docs/specs/` requires correction. Closed-wave archives keep their
text.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The digest-stability property IS the fix; without it nothing changes |
| AC-2 | required | The only thing that catches an over-broad exclusion. Without it the receipt is silently weakened, which is worse than the bug being fixed |
| AC-3 | required | A misfiring region detector would corrupt the digest for any doc that merely mentions a heading, and the ambiguous case must degrade rather than error |
| AC-3a | required | Pins the one-exclusion boundary the independent review asked for; without it a later refactor can widen the exception silently, which is the failure mode that made the second exclusion a bad trade in the first place |
| AC-4 | required | Proves the fix through the public path an operator actually uses; AC-1 alone can pass while the lifecycle still reports staleness |
| AC-5 | required | Without the narrate-not-amend half the council's substantive finding is unaddressed and the exclusion opens a real hole |
| AC-5a | required | The Progress Log has a live production reader; a hash-only change that broke it would be a regression in an unrelated sensor |
| AC-6 | required | An unpinned evaluator transition is the exact defect memory `1ty9f-mem` records from the last bump |
| AC-7 | important | The re-Prepare is real but one-time and self-correcting, so an undisclosed one costs a false field report rather than a broken repo |
| AC-8 | required | This is the one churn source of the four that Requirement 1 cannot fix, and it fires on every wave that reaches Prepare; leaving it would mean the wave ships having demonstrated a defect it declined to close |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-05 | Follow-up repair for the delivery review: the stop condition no longer restricts new cycles to "correctness or contract" defects. It now leaves only editorial-only findings inline, while every finding needing verification, a boundary repair, or escalation keeps its existing action-matrix route. This preserves the pre-existing Level-2 missing-test-coverage and Level-3 architecture routes. Added a focused reconciler fixture for the exact 1.15.3 shipped review-prompt sentence and a byte-stable second pass. | Static source/diff review; targeted new test inspected but **not executed** per the operator's instruction not to run tests. |
| 2026-08-05 | Delivery-review repair, six findings, by a repairer who did not implement the change. **The one code defect made the whole exclusion a silent no-op on Windows:** `_PROGRESS_LOG_HEADING_RE` ended `[ \t]*$`, which cannot match `## Progress Log\r`, and `normalize_progress_log` splits on `"\n"`, so on a CRLF checkout under `core.autocrlf` the match count was 0, the `len(matches) != 1` guard returned the body unchanged, and nothing was excluded. Fixed to `\s*$`, matching the CRLF-tolerant sibling `_GARDENER_DATE_LINE_RE` two lines above (the RED output proves the asymmetry: the gardener date sentinel HAD applied to the same CRLF fixture while the Progress Log body was still fully present). Two half-pinned Requirement-4 boundaries closed with mutation-verified cases: marker-matched fence toggling (the delivered fence cases carried no real `## Progress Log` AFTER the fenced construct, so they proved only that a guard existed) and the region ending at `## ` rather than at any `#` heading. Three doc-honesty repairs: seed-180's stop condition claimed editorial repairs never need a re-Prepare, which is FALSE because a drifted citation in `## Rationale` or formatting in `## Requirements` lands in a digested section and still supersedes the receipt, so the seed now keys the re-Prepare on WHERE the repair lands rather than on how the finding was classified; the CHANGELOG claimed existing repos receive the seed rule through the reconciler on upgrade, which is false for the INSTALLING upgrade because the replacement plan is built pre-extraction and deliberately frozen, so that bullet now carries a per-bullet class-(b) transition disclosure including the sentence that stops the false field report, and Requirements 6 and 9 record the corrected class split; and Requirement 2a's census claim of no other production reader is corrected, naming `server_impl.py:16327` and `dashboard_lib.py:1075`. Both read the file rather than the digest body, so the hash-only and no-regression conclusions are unchanged and there is no new defect. The identical census claim also appears in this wave's recorded prepare-council verdict in `wave.md` and in the release lane's `events.jsonl` record; both are append-only history and are corrected HERE rather than rewritten. No change to `review_policy_reconcile.py` was needed: its replacement text never carried the false re-Prepare clause. | RED then GREEN on the CRLF case: `AssertionError: '<progress-log narration excluded from the review-policy digest>' not found in '...## Progress Log\r\n...'` before the regex fix, OK after. Mutants re-run on byte-copies outside the repo: fence toggle not marker-matched (`fence = "" if fence == marker else marker`) SURVIVED all five delivered progress-log tests and is KILLED by `test_marker_matched_fence_toggling_keeps_the_real_section_excluded`; region end at any `#` SURVIVED all five and is KILLED by `test_the_progress_log_region_ends_only_at_a_level_two_heading`; the unconditional-close variant (`fence = "" if fence else marker`) is killed by both the pre-existing `tilde-inside-backticks` case and the new one. Repo verified byte-identical to a pre-mutation copy with `cmp` afterward. Suite 6830 tests across 62 files OK (6828 plus 2 new test methods; the CRLF case is a `subTest` inside the existing AC-1 test, so it adds coverage without adding a count); `test_server_tools` 1578 OK; `ReviewPolicyReconcilerTests` 13 OK; `wf docs-lint: ok` |
| 2026-08-05 | LIVE FIELD PROOF of this change in the running server. Reloaded via `wf_reload_mcp` (`impl_matches_disk: true`, 83 tools re-registered, `evaluator_version` now reports 3), then appended THIS row and re-ran `wf_prepare_wave(mode='dry_run')` to check whether the receipt moved. The result is recorded in the row below, written after the second call. | `wf_reload_mcp` response; two consecutive `wf_prepare_wave` dry runs across a Progress-Log-only append |
| 2026-08-05 | Implemented red-first, every requirement landed at the insertion points the plan named. `normalize_progress_log(text, *, replacement)` added to `gardener_metadata.py` between `normalize_gardener_date` and `canonical_review_policy_body`, keyword-only, `len(matches) != 1` degrade guard transferred, heading kept as a module constant, and fence tracking mirroring `commit_provenance._without_fenced_code` so a `~~~` inside a backtick fence does not close it; wired in as the second normalization in `canonical_review_policy_body`; `PROGRESS_LOG_SENTINEL` and `normalize_progress_log` added to `__all__`. The doc-drift consumer was deliberately left on the DATE boundary alone and the test whose name encoded the old shared-boundary invariant was renamed with the reason stated in its docstring. `REVIEW_POLICY_EVALUATOR_VERSION` moved 2 to 3 with BOTH pins moved: the boundary tripwire updated rather than deleted, and the v1-to-v2 convergence test retargeted by patching to 2 in its second phase so the retired boundary stays pinned, plus a new v2-to-v3 case in the same shape. Requirement 6 landed in `seeds/180` under Finding classification and reaches existing repos through a reconciler replacement pair keyed on the shipped sentence, with the v1.14 pair's replacement text updated so a repo at either baseline converges on the same current text and a second pass is a no-op. Requirement 8 landed in the scaffold, the plan template, `seeds/170`, `seeds/040`, and `seeds/160` (migration bullet in both migration lists plus the verification-checklist line); the `ac_priority_unpopulated` check was not touched and a test pins that it still fires. | Suite 6828 tests across 62 files OK (baseline 6820 plus 8 new tests); `wf docs-lint: ok`; RED before the fix: AC-1's four variants failed on digest inequality, AC-3 and AC-5a errored on the absent helper, AC-4 failed `3 != 2 : a Progress-Log-only append must mint no new receipt`, AC-6's pin failed `2 != 3`; five mutants applied to byte-copies outside the repo and all killed, (i) no exclusion by 8 assertions incl. AC-4, (ii) a second Session Handoff exclusion by `surface='session-handoff'`, (iii) no fence guard by `fenced-lookalike-only`, `tilde-inside-backticks`, and the in-region fence test, (iv) reverted constant by the boundary pin and the v2-to-v3 test, (v) unconditional exclusion by `case='duplicated'`; repo verified byte-identical to a pre-mutation copy with `cmp` afterward |
| 2026-08-05 | Gapfill: MCP `code_read` and `code_keyword` covered every production module this change touches, but `.wavefoundry/framework/scripts/tests/` and `.wavefoundry/framework/seeds/` sit outside the structural navigation layer, so locating the enclosing test class, the reconciler fixture semantics (`_root` seeds only `replacements[0][0]`, and `plan_reconciliation` computes its match list against the ORIGINAL text so replacement pairs cannot chain), and the seed insertion points needed read-only Bash greps announced as gapfills. Worth adding before the next wave that picks a test home: `code_keyword` does reach the tests tree, but class-level navigation does not, so "which class owns this test" is currently a grep. | Bash greps over `tests/test_review_policy.py`, `tests/test_server_tools.py`, `.wavefoundry/framework/seeds/160`, `/170`, `/180`, and `/040`, plus `git show v1.14.0:docs/prompts/review-wave.prompt.md` to confirm which reconciler baseline the byte-stability test exercises |
| 2026-08-05 | Independent reviewer confirmed the phase-scoped receipt-binding correction, the two-evaluator-pin finding, the `commit_provenance` fence precedent, and the plan-template locality, then caught a FALSE claim this plan had just introduced while folding the lane findings: that no seed or renderer updates an existing project Review-wave prompt. Verified and the reviewer is right. The whole-file lifecycle template is missing-only, but `review_policy_reconcile.py:67-81` owns exact-string replacements inside `docs/prompts/review-wave.prompt.md` in EXISTING repos and already rewrites the adjacent passage at `:73-75`. Requirement 6 is corrected: the behavioral rule lands in seed-180, and surfacing it in existing prompts is a reconciler replacement pair, with two cautions recorded (memory `1u2ju-mem` marks that file fragile and requires `ReviewPolicyReconcilerTests`; a replacement pair silently no-ops against a drifted prompt). Third claim of mine falsified by an independent pass in this wave, which is the argument for the review discipline rather than against it. | Reviewer report 2026-08-05; `code_read` of `review_policy_reconcile.py:55-95` showing the `docs/prompts/review-wave.prompt.md` key and its replacement pairs |
| 2026-08-05 | Five prepare-phase lanes run: release, code, qa-reviewer, docs-contract WITHHELD, architecture APPROVED. Seven findings folded, three of them blocking, and the largest is a correction to this plan's own central claim IN BOTH DIRECTIONS. The plan said a supersession lapses every recorded approval; the code lane said it lapses exactly one, `wave-council-readiness`. Executed against 1ugk8's real ledger, neither is right: its 18 approval records split into 10 readiness-phase approvals that ALL carry `policy_receipt_id` and therefore all lapse (council plus all six prepare lanes), and 8 delivery-phase approvals that carry none and all survive. The lane's own probe showed lanes surviving only because by then each lane's CURRENT approval was its delivery-phase one. Rationale, AC-4, and the superlinearity claim are corrected to the measured split, and the misleading "all eight pending" citation is retired with a note not to reuse it. Also folded: the Requirement 6 seed is NAMED (`seeds/180:66-70`) after the lane established that no seed generates the Review-wave prompt body and the obvious carrier is a missing-only lifecycle template reaching fresh installs only; `test_server_tools.py:27913` BREAKS on the evaluator bump rather than merely serving as a template, so two pins move; AC-5a was vacuously satisfiable by an already-green whole-file reader and now asserts the hash-versus-file divergence; the fence precedent this plan cited was frontmatter logic offering a body scanner no protection, replaced with `commit_provenance.py:81-94`; the test home is unambiguous (`test_review_policy.py`, no `test_gardener_metadata.py` exists); `plan-template.md` does not ship so its correction is Wavefoundry-local unless a seed-160 migration bullet is added; a digested Risks row cited Requirement 8 for what is Requirement 9; the CHANGELOG has no open section so one must be created; and `wf_reload_mcp` suffices rather than only a full host restart. | Lane reports 2026-08-05; my own confirmation probe over `docs/waves/1ugk8 .../events.jsonl` printing per-record `approval_phase` and receipt binding; `review_evidence.py:1026-1036`, `:1311-1319`, `:3139-3145` |
| 2026-08-05 | Independent review (not the author, not the council) endorsed the core fix and recommended two adjustments, BOTH adopted: narrow to the Progress Log only, and restate the objective as removing false invalidation rather than stopping the review loop. Verified the review's load-bearing claim rather than accepting it, and found stronger evidence than it offered: `wave_lint_lib` contains zero references to Session Handoff, and the corpus already deviates from the pointer invariant in roughly thirty docs. The review also contributed an analysis this plan had not used: 1uhfy's six readiness approvals were mostly LEGITIMATE, earned by three genuine scope expansions, which independently confirms both that the fix is correctly scoped and that Requirement 2b's narrate-not-amend rule is load-bearing, since those same expansions were announced in Progress Log rows. | Reviewer report 2026-08-05; `code_keyword` over `wave_lint_lib/**/*.py` returned 0 matches for Session Handoff; heading-vs-pointer counts 710 against 678 over `docs/waves/**/*.md` |
| 2026-08-05 | Requirement 8 added at operator direction after the churn was caught LIVE on this wave: filling the Prepare-owned AC Priority table superseded receipt `review-policy-511e88f79af303be4214` and lapsed the readiness approval recorded moments earlier, forcing a re-record under `review-policy-38a14e8048c301efdfd3`. Operator asked for the same treatment for ACs and Tasks. Resolved by ordering rather than exclusion, because both surfaces are requirement-bearing and must stay digested. Carriers verified: the scaffold placeholder at `server_impl.py:16745` and `docs/plans/plan-template.md:60` are the only two instruction carriers (census: no seed contains the string), and `seeds/170-plan-feature.prompt.md:80` owns AC and Task authoring but currently states nothing about when the priority table is filled. Checkbox STATE is explicitly left in Out of scope as a distinct and harder problem. | Live supersession observed in this wave's own ledger: `supersedes_receipt_id: review-policy-511e88f79af303be4214`; carriers located by `code_keyword` over the seeds and the scaffold |
| 2026-08-05 | Prepare-phase council PASS after in-phase repair, ONE pass, both seats run by the coordinator with read-only MCP retrieval (the Agent tool was unavailable on a classifier outage; for a change this size a single code-grounded pass is proportionate and matches the stop condition this change proposes). Two substantive findings, both folded before the receipt mint. RED-TEAM disproved the safety argument as written: Progress Logs are the sanctioned place where this repo ANNOUNCES scope changes, with six real examples including a hard-break envelope change, so the exclusion opened a real hole; closed by promoting narrate-not-amend from an assumption to a stated seed rule (Requirements 2b and 6) and reframing the Risks row away from the adversarial smuggling case it had wrongly assumed. Red-team also found the Progress Log DOES have a production reader and the plan had not said the exclusion is hash-only (Requirement 2a). DOCS-CONTRACT ran the census the plan had deferred and found one carrier, a memory record rather than a doc, plus the scope lesson that censuses must include `docs/agents/memory/`. It also surfaced the direct precedent: the gardener-date normalization exists because wave 1tz6l fixed this same class of false staleness, so this change extends an established remedy. Clean on the remaining items: nothing branches on `evaluator_version` and no architecture or spec surface asserts that any change-doc edit supersedes the receipt. **This row's third clean item, "no other production reader of Progress Log content", is FALSE and is corrected in Requirement 2a: `server_impl.py:16327` and `dashboard_lib.py:1075` both read the section. Both read the file rather than the digest body, so the hash-only and no-regression conclusions stand; the census claim did not.** | Council census 2026-08-05: `code_keyword` over `docs/waves/**` returned 18 scope-change Progress Log rows; `server_impl.py:15934` `if "Gapfill:" in doc.read_text(...)`; `1u8m9-mem` summary text; `1tz6k-bug review-policy-receipt-metadata-stability` |
| 2026-08-05 | Evaluator-version question SETTLED at plan time rather than deferred to implementation. Verified by reading every use of `REVIEW_POLICY_EVALUATOR_VERSION` that nothing in the tree branches on it: its only production uses are the `policy_input_digest` hash payload (`review_policy.py:434`) and the receipt stamp (`server_impl.py:6893`), with int validation at `:575`. That means the bump is a labeling decision, not the mechanism forcing the re-Prepare, which corrected the original Requirement 7's framing. Decision recorded, the three carriers named, and the one-time re-Prepare moved from an assumption to a disclosed Requirement 9. | `review_policy.py:25`, `:434`, `:553`, `:575`; `server_impl.py:6893`; existing tripwire `test_review_policy.py:343` and convergence template `test_server_tools.py:27913` |
| 2026-08-05 | Filed after the operator flagged that wave 1ugk8's review loop kept reopening. Root cause located by reading the digest path rather than by inference: `canonical_review_policy_body` normalizes only the gardener date, so the Progress Log append that `AGENTS.md` requires of every repairer is itself what lapses the unrelated approvals. Scoped to the coverage-neutral half; the lane-selection defect is recorded in Out of scope as the follow-up. | `review_policy.py:424-451`, `gardener_metadata.py:48-55`; wave 1ugk8 minted five receipts and re-recorded readiness through context id `-r5`, with two cycles driven by purely editorial findings |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-05 | Exclude progress-tracking sections from the digest rather than adding a finding-severity class or a cycle cap | The receipt exists to attest that the reviewed PLAN has not changed. Progress-tracking prose is a record of what happened and states no reviewable claim, so digesting it produces false staleness. Fixing the input is smaller and more honest than adding machinery to tolerate a wrong input | (1) Introduce an editorial finding class that does not re-open a cycle (rejected for now: touches the evidence schema, and the loop would still re-record on any Progress Log append). (2) Cap review cycles at N (rejected: caps the symptom, and a real defect found in cycle 3 must still be able to block). (3) Let repairers skip the Progress Log (rejected: destroys the audit trail to dodge a digest bug). (4) Re-record approvals faster or in bulk (rejected: automates the busywork instead of removing it) |
| 2026-08-05 | Keep lane selection out of this change | Narrowing the trigger corpus reduces which reviews run, which is a genuine risk-posture change; this exclusion changes no coverage at all. Shipping the coverage-neutral fix first keeps the two decisions separately reviewable and separately revertible | Bundle both (rejected: mixes a coverage-neutral fix with a coverage-reducing one in a single approval, and the operator asked for baby steps) |
| 2026-08-05 | Narrow to ONE excluded section, dropping the `## Session Handoff` exclusion | Independent review recommended it and the evidence is stronger than the review had: no validator in `wave_lint_lib` references the section, and the corpus already carries about 710 `## Session Handoff` headings against about 678 canonical pointer sentences, so roughly thirty docs hold something other than the pointer today. An exclusion whose safety rests on an invariant that is both unenforced and already violated buys nothing and could hide real content. The Progress Log earns its exception on different grounds: it is the MANDATED repair-tracking surface, it is the actual source of the loop, and it gains an explicit narrate-not-amend rule | (1) Keep both exclusions (rejected: a second exception with no measured benefit and a weaker safety case, and the reviewer is right that each exception is a thing every future reader must reason about). (2) Keep the exclusion and add a docs-lint rule enforcing the pointer (rejected: builds new enforcement machinery to justify an exclusion nobody needs, and the thirty deviating docs would have to be reconciled first) |
| 2026-08-05 | Restate the objective as removing FALSE invalidation rather than stopping the review loop | Also from the independent review, and correct: legitimate re-review still happens whenever the plan or implementation genuinely changes, and the 1uhfy ledger is the proof, where most of six readiness approvals were earned by three real scope expansions. The original wording invites a future reader to over-extend this change into suppressing review it was never meant to touch | Leave the wording (rejected: the imprecision is exactly the kind that licenses scope creep later) |
| 2026-08-05 | Fix the AC-Priority and Tasks churn by ORDERING (populate before the council) rather than by excluding those sections from the digest | Both are requirement-bearing: AC Priority sets which criteria are required, and the task list is what the plan commits to doing. Excluding them would weaken the receipt in exactly the way AC-2 exists to prevent. Nothing forces the fill to happen after the council, so the churn is a scheduling artifact of the scaffold's own placeholder text, and correcting the instruction costs nothing | (1) Exclude AC Priority and Tasks from the digest like the Progress Log (rejected: they carry reviewable claims, so this would trade a churn bug for a real hole). (2) Leave it and accept one supersession per wave (rejected: it fires on every wave that reaches Prepare, and this wave demonstrated it live). (3) Suppress the `ac_priority_unpopulated` check (rejected: removes a gate instead of fixing an ordering problem) |
| 2026-08-05 | Bump `REVIEW_POLICY_EVALUATOR_VERSION` from 2 to 3 | The field's only job is to identify the algorithm that produced a receipt, and the input canonicalization is part of that algorithm. Verified that nothing branches on the value: its only production uses are the `policy_input_digest` hash payload and the receipt stamp, so the bump costs nothing operationally (the digest moves either way) while omitting it leaves the permanent `events.jsonl` history unable to distinguish a plan edit from a canonicalization change. Hygiene argument, stated as such | (1) Do not bump (rejected: two digest algorithms would both stamp v2, silently degrading an audit trail this project goes to considerable lengths to keep trustworthy). (2) Bump `REVIEW_POLICY_SCHEMA_VERSION` instead (rejected: schema_version describes the receipt record's SHAPE, which is unchanged; canonicalization is derivation logic and therefore evaluator territory). (3) Grandfather receipts matching either canonicalization (rejected: permanently encodes two algorithms to avoid one one-time re-Prepare, against the standing simplicity constraint) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The exclusion is drawn too wide and a substantive edit stops lapsing approvals | AC-2 pins one digest-sensitivity case per requirement-bearing surface, so an over-broad region fails loudly rather than silently weakening the receipt |
| A scope or requirement change is announced ONLY in a Progress Log row, so after the exclusion it no longer lapses approvals | This is the council's substantive finding and it is NOT the adversarial smuggling case; it is current sanctioned practice, with six real examples in Requirement 2b including a hard-break envelope change. Mitigated by making narrate-not-amend an explicit stated rule in the same seed passage as the stop condition (Requirements 2b and 6), so the convention that makes the exclusion safe is written down instead of assumed. Residual after that: an agent who violates the stated rule, which is the same exposure as an agent who never updates Scope at all today |
| The exclusion is misread as removing the section from the doc | Requirement 2a states it is hash-only and requires a test proving the `Gapfill:` advisory reader still clears |
| The one-exclusion boundary widens later, since the section helper makes a second exclusion cheap to add | AC-3a pins that editing Session Handoff still moves the digest, and Requirement 4 states plainly that a cheap mechanism is not a licence to add an exclusion without its own evidence |
| Section detection misfires on a doc whose prose contains a heading lookalike | Requirement 4 anchors on line-start headings and Requirement 5 degrades to today's behavior on ambiguity, mirroring the existing `len(matches) != 1` guard |
| The one-time re-Prepare is read as a defect in the field, since the fix's own installing upgrade imposes exactly the approval re-recording it exists to prevent | Requirement 9 makes it a disclosed CHANGELOG item with its boundaries stated (closed waves untouched, and `wf_reload_mcp` or a host restart to take effect), and Requirement 7's convergence test proves it happens ONCE rather than repeating |
| An operator who has already run `wf_reload_mcp` is told to "restart" and reports the fix as not working | Requirement 9 names both recovery paths. `gardener_metadata` is in server_impl's reload-purge set (`server_impl.py:30-43`) and this change adds no new tool, so a reload genuinely suffices; claiming only a full restart is what would generate the false report |
| The evaluator bump is mistaken for the mechanism that forces the re-Prepare, so a later reader reverts the bump expecting the churn to stop | Requirement 7 states plainly that the digest moves either way and that nothing branches on the value; the Decision Log records the bump as a labeling choice with its own rationale |
| This change is itself over-reviewed, which would be self-refuting | One review pass. Requirement 6's stop condition applies to this wave as soon as it is written |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
