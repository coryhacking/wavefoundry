# The Legal Judgment Shape Is Discoverable Only by Reading the Deriver

Change ID: `1ug68-enh guided-review-action-carries-its-schema`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-05
Wave: `1ui1d review-loop-friction`

## Rationale

`wf_review_wave` is documented as the sole guided inspection entry point: it returns bounded
`review_actions`, each separating state-derived `state_args` from `required_caller_inputs`. The design
intent is that a caller supplies judgment and evidence while the server supplies everything derivable.

Two defects break that contract in practice, both observed live while recording wave 1uhcb's delivery
ledger.

**1. A guided action's `state_args` are only writable in combination with a judgment the action never
names, and nothing on the surface says so.** The recommended reverification action returns
`blocking_required_lanes: ["qa-reviewer"]`. That value is legal, but ONLY when the caller's judgment
independently derives `blocking=true`. Supplying a softened judgment — the natural move when
recording that a defect is now repaired — makes the same `state_args` unwritable, and the resulting
message, `finding_synthesis: non-blocking synthesis cannot retain blocking_required_lanes`, names the
field rather than the coupling.

The mechanism, read from the tree rather than inferred:

- `blocking` is DERIVED, never declared (`derive_blocking`, `review_evidence.py:913`): it requires
  `disposition == do_now` plus the blocking predicate.
- `review_evidence.py:3376` rejects any synthesis carrying `blocking_required_lanes` while `blocking`
  derives false.
- Therefore a reverification must repeat the finding's ORIGINAL judgment. `blocking` describes the
  defect's nature; `blocking_required_lanes` tracks which lanes have not yet cleared it. "Still
  blocking, one lane left" is the correct and expected intermediate state, and
  `repair_execution_state` is auto-derived to `completed` for reverification runs regardless.

**This was originally filed as a contract violation between the guided action and the validator, and
that framing was REFUTED.** Root-caused on 2026-08-05 while finishing 1uhcb's ledger: the two never
disagreed. Passing the guided `state_args` verbatim together with the finding's original judgment
succeeds, demonstrated five times in a row across two findings and five lanes. The refuted framing is
recorded here rather than deleted so it is not retried, and because the correction relocates the
defect: this is a **discoverability** gap, not a broken contract. Nothing is wrong with either side;
what is missing is any surface that tells a caller the two fields are coupled.

**2. The judgment schema is not discoverable from the tool surface.** A `finding` event requires
roughly twenty typed judgment fields. Their allowed values are frozensets in the module
(`VALIDATION_STATUSES`, `SCOPE_RELATIONS`, `CONTRACT_RELEVANCES`, `TRISTATE`, `AUTHORITY_DOMAINS`,
`AUTHORITY_DELTAS`, `OBSERVABLE_IMPACTS`, `CONTAINMENTS`, `FIX_RISKS`, `OPTIONAL_VALUES`,
`REPAIR_SAFETIES`, `BENEFIT_VS_FIX_RISKS`, `REJECTION_BASES`, `REPAIR_EXECUTION_STATES`) and are
returned by no tool.

Some later validator checks are sequential, but that is not the first fix. They depend on a valid
prior head, actor, and phase, so broad error aggregation would change a safety-sensitive protocol
contract before the caller can even see the schema it needs. This change resolves the observed
discoverability failure first; any remaining multi-retry evidence is a separate follow-up.

**Why this matters beyond ergonomics.** The framework's own instructions tell agents to record typed
review evidence, and the operator's framing is that recordkeeping confirms the work rather than being
the work. A recordkeeping surface that costs a session of schema archaeology inverts that: agents
either burn budget rediscovering the shape or fall back to prose where an enum belongs. In 1uhcb the
cost was seven failed calls and a session that ended with the ledger unfinished; a later session
root-caused the coupling in one read of `derive_blocking` and completed all eleven records without a
single rejected write. The whole delta was knowing one undocumented rule. The fix is derivation and
self-description, not documentation.

## Requirements

1. **The guided action carries the judgment its own `state_args` require.** Neither side of the
   original "disagreement" is wrong, so nothing is reconciled and no behavior changes here. A
   reverification action returning non-empty `blocking_required_lanes` includes the current finding's
   copyable `judgment_template` and a machine-readable constraint that the submitted judgment must
   still derive `blocking=true`. This directly tells the caller to preserve the defect's original
   judgment while independently verifying the repair; it does not serialize or duplicate
   `derive_blocking` as prose.
   **Do NOT "fix" either side.** An earlier draft of this requirement instructed the implementer to
   decide which side was wrong; that instruction rested on the refuted premise above and would invite
   a behavior change where none is warranted. Loosening `review_evidence.py:3376` would let a
   non-blocking synthesis retain blocking lanes, which is precisely the integrity property that keeps
   a repaired-but-uncleared finding visible.
2. **Reproduce the real failure, not the refuted one.** The fixture is a caller that supplies a
   guided reverification action's `state_args` verbatim together with a *softened* judgment (the
   natural "it is fixed now" move). That must fail today with the field-named message, and must fail
   after the change too — but with a message that names the coupling and points to the action's
   `judgment_template`.
   **Vacuity trap, stated because the earlier draft walked into it:** a test that passes the guided
   `state_args` with the finding's ORIGINAL judgment is GREEN on the current tree. It cannot be the
   RED-first case, and asserting it as one would ship a test that never fails. Pin it instead as the
   positive control proving the flow already works.
3. **The guided action carries its nested input schema, emitted ONCE per response rather than per
   action.** `required_caller_inputs` names top-level objects such as `judgment`, `evidence`, and
   `integrity_checks`; enum domains therefore belong in a nested schema for the judgment fields, not
   on those top-level names. Each judgment field reports its allowed values or scalar kind, and
   integrity booleans and tristates are labelled as such, so a caller never reads module frozensets
   to construct a legal payload.
   **Response-size constraint, and it is load-bearing rather than stylistic.** Guided actions are
   emitted per finding and per lane under `REVIEW_ACTION_CAP = 50` (`review_evidence.py:303`), so a
   schema duplicated onto every action multiplies a roughly fourteen-field enum registry by the
   action count. That is precisely the aggregate-envelope failure memory `1u1xb-mem` records from
   wave 1tz6l: per-field truncation does not bound an MCP envelope, because many small fields exceed
   the cap together. Emit the schema once at the response level and have actions reference it by
   name; a per-action copy is a defect, not an implementation detail. Budget the serialized size of
   the added block and keep the existing whole-envelope postcondition intact.
4. **No weakening of what the fields MEAN.** This change is about self-description, not derivation of
   new behavior. It
   must not relax any enum, make a load-bearing judgment field optional, or let a caller omit an
   integrity check. Pin that the same invalid records are still rejected.

## Scope

**Problem statement:** a guided action's `state_args` are writable only in combination with a
judgment the surface never names, and the judgment schema itself is discoverable only by reading
module frozensets and the `derive_blocking` predicate, so recording typed review evidence costs a
session of schema archaeology and sometimes does not complete.

**In scope:** the `review_actions` projection and its `state_args` / `required_caller_inputs` split;
the current-head judgment template and blocking constraint on a reverification action; nested
judgment-schema and integrity-kind reporting; the targeted coupling diagnostic; the tool docstrings
and MCP tool-surface spec; `CHANGELOG.md`.

**Out of scope:** what the judgment fields mean or which are required (Requirement 4 forbids
weakening); **any change to `derive_blocking` or to the `review_evidence.py:3376` retention rule**,
both of which are correct as they stand and are described, not modified, by this change; the review
lifecycle itself; a broad derived-field audit; aggregation of later sequential validation errors;
digest behaviour (see `1ug66-enh`); lane selection (see `1ug67-bug`).

## Acceptance Criteria

- [x] AC-1: Two paired cases over the same guided reverification action, using wave 1uhcb's ledger
  shape as the fixture. (a) POSITIVE CONTROL, green on the current tree and still green after: the
  action's own `state_args` plus the finding's original judgment write successfully. (b) RED-first:
  the same `state_args` with a softened judgment fails today naming only the field, and after the
  change fails with a message naming the `blocking` coupling and its `judgment_template`. The action
  itself carries the original judgment and blocking constraint. AC-1 is met only if (a) is asserted
  to be green BEFORE the change, which is what stops (b) being written as a test that could never
  have failed.
- [x] AC-2: A response containing any action with a `judgment` caller input carries a nested schema
  for each judgment field: enum allowed values or scalar kind, with booleans and tristates labelled.
  Pinned per input kind. The schema appears exactly ONCE per response regardless of action count,
  pinned by a fixture with several judgment-bearing actions asserting a single occurrence; and a
  response at the `REVIEW_ACTION_CAP` boundary stays within the whole-envelope size postcondition.
- [x] AC-3: The template and schema are derived from the same current finding and enum registries the
  validator uses, pinned by changing the source head or a registry value and proving the action
  changes with it rather than returning stale prose.
- [x] AC-4: No relaxation. Every record the current validator rejects is still rejected, pinned per
  rejection class, including a reasonless deferral, a missing integrity check, and prose supplied
  where an enum belongs.
- [x] AC-5: The retention rule is unweakened: a synthesis whose judgment derives `blocking=false`
  still cannot carry `blocking_required_lanes`, pinned directly so no ergonomics change can quietly
  relax the property that keeps a repaired-but-uncleared finding visible.
- [x] AC-6: Mutation-checked. At minimum: enum domains dropped from the projection; a current-head
  template is replaced with stale hardcoded data; the blocking constraint is removed; the coupling
  diagnostic no longer points to the template; and the schema is moved from response level to
  per-action, which must be killed by AC-2's single-occurrence and envelope-size cases. Each mutant
  is killed by a named test.
- [x] AC-7: Full framework suite and docs-lint pass.

## Tasks

- [x] Positive control (AC-1a) asserted green BEFORE any change, then the RED-first softened-judgment
  case (AC-1b), both on 1uhcb's ledger shape
- [x] Current-head judgment template and blocking constraint carried on the action
- [x] Nested judgment-schema and integrity-kind reporting
- [x] Targeted coupling diagnostic and non-relaxation pins (AC-4, AC-5); mutation check; full suite; docs-lint; CHANGELOG bullet

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| disclose   | implementer | —          | Current-head template and blocking constraint; no behavior change |
| schema     | implementer | disclose   | Nested domains, scalar kinds, and targeted diagnostic |


## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`; `.wavefoundry/framework/scripts/server_impl.py`; `.wavefoundry/framework/scripts/tests/test_review_evidence.py`; `.wavefoundry/framework/scripts/tests/test_server_tools.py`; `docs/specs/mcp-tool-surface.md`; `CHANGELOG.md`

## Affected Architecture Docs

Census at Prepare against the then-current tree. Candidates: the MCP tool-surface spec's review-event
and review-wave sections, the review-system overview seed, any seed instructing agents to record typed
review evidence, and `docs/agents/memory/` records about the review ledger. If a surface documents the
caller-supplies-judgment contract, Requirement 4 changes which fields that means. Treat `N/A` as a
finding until the sweep is run.

## AC Priority

Populated at plan time, before the prepare council runs, per the ordering rule wave 1uhcb shipped
(`seeds/170-plan-feature.prompt.md`; `docs/plans/plan-template.md`).


| AC   | Priority       | Rationale |
| ---- | -------------- | --------- |
| AC-1 | required       | The paired positive-control-plus-red case is what stops this change repeating the vacuity mistake the refuted draft would have shipped |
| AC-2 | required       | Enum-domain reporting is the change's primary deliverable; without it the discoverability gap is untouched |
| AC-3 | required       | The response must derive its template and schema from the live source of truth rather than returning a second, drift-prone schema |
| AC-4 | required       | Non-relaxation is the integrity boundary for an ergonomics change |
| AC-5 | required       | The retention rule is the property the refuted framing would have destroyed; it must be pinned directly rather than implied by AC-4 |
| AC-6 | required       | Mutation checks are what make the other ACs non-vacuous, and this repo has twice shipped surviving mutants |
| AC-7 | required       | Suite and docs gate are the standing release condition |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-05 | Filed from a live failure rather than a hypothesis: while recording wave 1uhcb's delivery ledger, the guided reverification action returned `blocking_required_lanes` that the finding-synthesis validator then refused under both dispositions tried, and the surrounding schema archaeology cost seven failed calls. That wave's ledger is still incomplete as a result, which is the strongest available argument for this change. | Wave 1uhcb: guided `review_actions` payload versus the `finding_synthesis` rejection; seven failed `wf_review_event` calls recorded in that session's handoff |
| 2026-08-05 | **Premise REFUTED and the plan re-authored before admission.** A later session root-caused the failure by reading the deriver: the guided action and the validator never disagreed. `blocking` is derived (`derive_blocking`, `review_evidence.py:913`), `review_evidence.py:3376` forbids retaining `blocking_required_lanes` only when it derives false, and the failed attempts had softened the judgment. Passing the guided `state_args` with the finding's ORIGINAL judgment succeeds. Consequences folded in: the title and defect 1 are rewritten from contract-violation to discoverability; Requirement 1 no longer instructs anyone to "fix whichever side is wrong" and explicitly forbids touching either; Requirement 2's RED-first fixture is re-pointed at the softened-judgment case with the vacuity trap named, because the originally-specified fixture is green on arrival; AC-1 becomes a paired positive-control-plus-red case; AC-8 pins the retention rule against relaxation; and the error-aggregation requirement now names the real mechanism. Requirements 3 and 4 were unaffected and carry the change's value. | 1uhcb ledger completed 2026-08-05: five reverifications and six approvals, eleven records, zero rejected writes, using the guided `state_args` verbatim; `review_evidence.py:913`, `:3376`, `:2619`, `:2831-2838` |
| 2026-08-05 | **Delivery review: AC-1 was marked complete with no test at all, and the message half of Requirement 2 was unimplemented.** Requirement 3 is genuinely delivered and verified in a live response: `caller_input_schema` is emitted ONCE at response level with `input_schema_ref` on each action, and `judgment_template` plus `blocking_constraint` are populated on reverification actions from the current head. But no paired positive-control/RED case existed; the only new coverage touching the feature was a field-name roster assertion. Added `test_guided_reverification_template_writes_while_softening_is_refused` over a two-lane fixture, which is the shape wave 1uhcb actually had. Two things surfaced while writing it. First, with a SINGLE blocking lane the reverification empties the list, so the retention rule cannot fire and a softened judgment legitimately terminalizes the finding — the coupling is only reachable while a lane remains outstanding, and the fixture was corrected to two lanes. Second, the refusal is enforced by `validate_review_evidence_records`, NOT by `build_compact_review_event`, so a test stopping at the producer sees the softened judgment succeed and proves nothing; the test now builds and then validates. The refusal message was also extended to name the DERIVED coupling and point at `judgment_template`, which Requirement 2 required and the delivery had not done. | Mutants killed: reverting the message to field-only, and dropping `judgment_template`/`blocking_constraint` from the projection, each fail the new test |
| 2026-08-05 | Prepare-council performance-seat finding, folded into Requirement 3, AC-2 and AC-6: AC-2 originally required every judgment-bearing action to carry the nested schema. Guided actions are emitted per finding and per lane under `REVIEW_ACTION_CAP = 50`, so that duplicates a roughly fourteen-field enum registry by the action count — the exact aggregate-envelope failure memory `1u1xb-mem` records from wave 1tz6l, where per-field truncation failed to bound an MCP envelope because many small fields exceeded the cap together. The schema is now emitted once per response with actions referencing it, pinned by a single-occurrence fixture and an at-cap envelope-size case, with the per-action variant mutation-killed. This edit stales the receipt minted moments earlier and lapses the readiness approval recorded against it, which is a live instance of exactly the churn `1ug66-enh` and `1ug67-bug` exist to reduce; re-minted and re-recorded rather than skipped. | `review_evidence.py:303` action cap, `:1401-1425` per-finding per-lane action emission; memory `1u1xb-mem` |
| 2026-08-05 | Prepare-review finding, repaired: the AC list was non-contiguous and disagreed with the AC Priority table's ordering (list ran AC-1..AC-5, AC-8, AC-7 with no AC-6; the table ran AC-1..AC-5, AC-7, AC-8). That is not cosmetic here, because `_check_tilde_required_ac_has_inline_note` resolves priority by AC id and falls back to POSITIONAL mapping, so divergent ordering is a latent mis-mapping of which ACs carry the required-priority `[~]` rule. Renumbered contiguously AC-1..AC-7 with both surfaces aligned; the retention-rule AC is now AC-5 and the mutation AC is AC-6. The earlier row above refers to that AC as "AC-8", which was correct when written; history is left intact and the mapping is recorded here. | `wave_lint_lib/wave_validators.py:334-336` positional fallback; parsed AC ids from both sections before and after |
| 2026-08-05 | Review narrowed the implementation to the observed discoverability failure. A guided action now needs a current-head judgment template, a blocking constraint, and a nested schema for the `judgment` object; its top-level caller inputs are not themselves enum fields. The broad derived-field audit and multi-error aggregation are deferred because they change protocol behavior beyond the proven failure. | Review of `REVIEW_ACTION_CALLER_INPUTS` and guided-action projection: `review_evidence.py:326-335`, `:1406-1519` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-05 | Fix with a self-describing action, not a separate documented schema | A guided action carries the current-head template and enum registry values, so the caller does not reconstruct the payload and a second prose schema cannot drift | Document the enums in the tool docstring (rejected: duplicates the source of truth and drifts); leave it and rely on agents reading the module (rejected: measured at seven failed calls and an unfinished ledger) |
| 2026-08-05 | Requirement 4 forbids relaxing any field | The judgment fields exist to stop vacuous or unsupported findings being recorded; an ergonomics change that quietly made them optional would trade a real integrity property for convenience | Simplify the schema by dropping fields (rejected: that is a separate decision about what review evidence must assert, and not this change's business) |
| 2026-08-05 | Carry the current judgment template and a blocking constraint; change neither `derive_blocking` nor the retention rule | Both are correct. The template is more useful than paraphrasing a predicate: it tells the caller exactly which existing judgment to preserve while the constraint explains why the lanes remain | Loosen `review_evidence.py:3376` to accept the lanes regardless of derived blocking (rejected: erases the visibility property); serialize `derive_blocking` as prose (rejected: a copyable current template is smaller and less drift-prone) |
| 2026-08-05 | Defer derived-field auditing and broad error aggregation | The observed failure is schema discovery. Moving fields or changing sequential validation broadens behavior and protocol compatibility without evidence that it is necessary | Include both now (rejected: over-scopes a focused ergonomics repair) |
| 2026-08-05 | Keep the refuted framing visible in this document rather than deleting it | A future reader who hits the same message will re-derive the same wrong conclusion; recording the refutation and its evidence is what stops the second occurrence. This mirrors how 1ug66 records its rejected wholesale-exclusion approach | Delete the refuted text (rejected: loses the correction); leave it uncorrected (rejected: it would drive an unbuildable Requirement 1 and 2 into implementation) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| An ergonomics change quietly weakens evidence integrity | AC-4 pins per rejection class that every currently-invalid record is still rejected, and Requirement 4 states the prohibition explicitly |
| An implementer reads the refuted framing kept in the Rationale and "fixes" a side anyway, relaxing the retention rule | Requirement 1 forbids changing either side in bold and states why; Scope's Out-of-scope names `derive_blocking` and `review_evidence.py:3376` explicitly; AC-5 pins the retention rule directly and AC-6 mutation-kills its removal |
| The RED-first case is written as the originally-specified fixture and is green on arrival, shipping a test that can never fail | Requirement 2 names the vacuity trap explicitly and AC-1 requires the positive control to be asserted green BEFORE the change, so the pair is falsifiable by construction |
| A template or schema drifts from its source | AC-3 changes a head and registry value under test and requires the action to change with both |
| The nested schema is emitted per action and the response envelope exceeds the host cap at high action counts | Requirement 3 mandates one response-level emission with actions referencing it; AC-2 pins single-occurrence and an at-cap envelope-size case; AC-6 mutation-kills the per-action variant. Grounded in memory `1u1xb-mem` and `REVIEW_ACTION_CAP = 50` rather than in a size guess |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
