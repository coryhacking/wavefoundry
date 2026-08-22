# A wave predating typed review evidence is skipped by the validator that would flag it

> **WITHDRAWN 2026-08-21 by prepare-council BLOCK (wave `1vwyc`). The premise is falsified. Do not
> retry this change without first identifying the code path that actually refused the field target's
> wave.**
>
> The skip this plan calls a defect is a deliberate, documented legacy-protocol selector, replicated
> across five surfaces:
>
> - `server_impl._wave_uses_external_review_evidence` computes the identical three-term expression
>   under the docstring: "True for the new contract; unmarked pre-protocol waves remain prose-only
>   legacy."
> - `_review_evidence_diagnostics` and `_approval_evidence_diagnostics` short-circuit on that
>   predicate and return zero errors for an undeclared wave. The lifecycle does not refuse it.
> - `review_evidence.resolve_review_authority` returns `typed=False` on the same condition; the prose
>   path is a live supported branch.
> - `wave_validators._check_prepare_council_verdict` already validates undeclared non-terminal waves
>   by routing them to the legacy prose gate, erroring for `implementing` and warning for `active`.
>   The gate is not silent about these waves; it applies the other gate.
> - `check_orphan_wave_ledgers` already fails on the genuinely dangerous half-migrated state.
>
> Three shipped surfaces promise operators this compatibility: CHANGELOG `## [1.15.0]` ("Legacy waves
> without the declaration keep the prose mechanism unchanged"), CHANGELOG `## [1.15.4]` ("Legacy
> prose-only waves keep their existing structured `prepare-council` authority and validation
> unchanged"), and the `review_policy_reconcile` policy block ("Legacy prose waves retain the
> structured checkpoint compatibility gate").
>
> So `validate_external_review_evidence` returning `ok=False` on an undeclared record is a
> typed-protocol validator asserting its own precondition against a record that is not on the typed
> protocol. It is not a hidden answer the gate failed to ask for. This change would put the docs gate
> in disagreement with the lifecycle on a protocol question and fire against a supported
> configuration.
>
> **A second, independent blocker.** `check_wave_docs` returns a flat failure list with no warnings
> channel, so the proposed finding would be a hard gate failure, not an advisory. It would fire on
> `1seaw` here, turning a green gate red, while Requirement 4 and AC-6 forbid modifying the record
> that would fix it. The shipped precedent is severity-graded: `_check_prepare_council_verdict`
> returns `(errors, warnings)` and errors only for `implementing`.
>
> **What remains true and unexplained:** a target repository did hit an unexpected refusal mid-wave
> after crossing the 1.14.0 boundary, and diagnosis was expensive. That report stands. The refusing
> code path was never identified, and this plan guessed at it. Identify it first.
>
> Also recorded: the executed verification in this plan is accurate (the guard evaluates False, the
> validator returns `ok=False`, the blast radius is 139 closed / 1 planned / 0 active of 236). The
> measurements were never the problem. The inference from them was.


Change ID: `1vwye-bug prose-era-wave-evidence-silently-unvalidated`
Change Status: `withdrawn`
Owner: Engineering
Status: planned
Last verified: 2026-08-21
Wave: TBD

## Rationale

The review-evidence validator runs only on wave records that already declare
`review-evidence-source: events.jsonl`. A wave authored before that header existed declares nothing,
so the check is skipped and the docs gate stays silent about a wave whose review evidence the
lifecycle tools will refuse.

Verified in `wave_lint_lib/wave_validators.py`, at the `is_wave_record` branch:

```
source, _source_errors = parse_review_evidence_source(text)
inline_marker = re.search(r"(?mi)^review-evidence-protocol\s*:", text) is not None
if source is not None or _source_errors or inline_marker:
    review_evidence = validate_external_review_evidence(path)
```

Executed against a prose-era fixture (a wave with `## Review Evidence` prose, no header, no sibling
`events.jsonl`): `source=None`, `_source_errors=()`, `inline_marker=False`, so the guard is False and
validation never runs. Calling `validate_external_review_evidence` on that same fixture directly
returns `ok=False` with `wave header must declare 'review-evidence-source: events.jsonl'`. The check
knows the answer; the gate never asks the question.

Confirmed end to end: placing that fixture in this repository and running `wf docs-lint` produces
three unrelated findings (watchpoint wording, a missing change file, a missing `prepare-council`
verdict) and **nothing** about the missing header or the unvalidatable evidence.

**Field evidence.** A target repository upgraded across the 1.14.0 boundary holding an active
prose-era wave. Its first signal was a lifecycle refusal while trying to advance the wave, not the
upgrade. The durable artifacts corroborate the shape: that wave's `events.jsonl` is dated the 1.14.0
release date and holds a single `approval:wave-council-readiness` record whose evidence fields cite a
prose approval authored 18 days earlier. The repair was cheap and evidence-layer only; it did not
invalidate work or force a review to be re-run. **The expensive part was diagnosis**, hitting an
unexpected gate failure mid-wave and working out what the pack now wanted.

That is precisely what this gate exists to prevent, and it is the part the current skip defeats.

### Two other fixes were considered and rejected on evidence

**Surfacing CHANGELOG sections at upgrade time was falsified.** The pack ships
`.wavefoundry/CHANGELOG.md` into every target and no upgrade module reads it, which looked like the
fix. It is not. The `## [1.14.0]` entry covers the change in a subordinate clause inside an *Added*
bullet about a rendering feature: "so approval currency and open blocks are readable at a glance
while `events.jsonl` remains the only authority." The word "remains" asserts continuity, so to a
target holding a prose-era wave it reads as *nothing to do here*. Surfacing it would have been a
no-op, and worse than silence, because it is a false negative. The same release's tool-rename bullet
warns correctly, which shows the variable is entry authoring rather than mechanism presence.
Extraction may still be worth doing later, but it does not fix this and must not be sold as if it did.

**Improving the refusal message improves the wrong half.** The refusal is what makes the repair
cheap, and the repair was already cheap. `review_policy_reconcile` already produces a good actionable
refusal elsewhere (naming the signoff key, the tool, the authority model, and the next call). Better
text arrives only after the operator has hit the gate mid-wave, which is the expensive moment this
change moves earlier.

## Requirements

1. A **non-terminal** wave record that does not declare `review-evidence-source` must produce a
   finding, rather than skipping validation.
2. The finding must be actionable without archaeology: name the missing header, state that
   `events.jsonl` is the sole review authority, and name the tool that records a typed approval.
3. **Closed waves must stay silent.** 139 of this repository's 236 wave records are closed and lack
   the header; they are historical archives and firing on them would be noise that trains operators
   to ignore the channel.
4. Do not modify any existing wave record. This change makes a gate report; migrating a wave is the
   operator's action, taken with the report in hand.

## Scope

**Problem statement:** the review-evidence validator is gated on a header that prose-era waves do not
have, so the waves most likely to need migrating are the only ones never checked.

**In scope:**

- The skip condition in `wave_validators.py`'s `is_wave_record` branch.
- Terminal-status scoping so closed archives stay silent.
- The finding text.
- Tests for the prose-era case, the closed-archive case, and the already-migrated case.

**Out of scope:**

- Migrating any wave, here or downstream.
- CHANGELOG extraction at upgrade time. Falsified for this defect; if wanted, it is its own change.
- Refusal-message wording in the lifecycle tools. Different half of the problem.
- Any general migration-registry mechanism. This defect needs none: the validator already knows the
  answer and is simply not being asked.

## Acceptance Criteria

- [ ] AC-1: A non-terminal wave record with `## Review Evidence` prose, no `review-evidence-source`
      header, and no sibling `events.jsonl` produces a finding naming the missing header.
- [ ] AC-2: A wave record with `Status: closed` in the same condition produces no finding. Proven
      against real archives, not only a fixture.
- [ ] AC-3: Running the full docs gate over this repository produces exactly one new finding, for
      `1seaw retrieval-intent-golden-queries` (status `planned`, header absent), and no finding for
      any of the 139 closed archives.
- [ ] AC-4: A wave that already declares the header is unaffected, with byte-identical lint output
      before and after.
- [ ] AC-5: The finding text names the header, the authority model, and `wf_review_event`, verified
      by asserting on the message rather than on the finding count.
- [ ] AC-6: No file under `docs/waves/` is modified by the change or by running the gate.

## Tasks

- [ ] Extend the skip condition so a non-terminal wave record without the header is validated.
- [ ] Scope the new finding to non-terminal statuses, reusing the existing `Status: closed` test
      already used by the projection check rather than introducing a second status predicate.
- [ ] Write the finding text per AC-5.
- [ ] Tests: prose-era non-terminal, closed archive, already-migrated, and the repository-wide count.
- [ ] Run the full gate before and after and diff the findings.

## Agent Execution Graph


| Workstream    | Owner       | Depends On | Notes |
| ------------- | ----------- | ---------- | ----- |
| skip-condition | implementer | :          | One condition plus terminal-status scoping; reuse the existing closed-status predicate. |
| finding-text  | implementer | skip-condition | Must be actionable without archaeology; asserted on directly. |
| verification  | qa          | finding-text | Repository-wide before/after diff across all 236 wave records. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_wave_lint.py`

## Affected Architecture Docs

`N/A`. This change removes a skip in an existing validator and scopes an existing finding class by a
status predicate already used elsewhere in the same function. No boundary, ownership, flow, or
verification-architecture change; no new mechanism.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The defect itself. |
| AC-2 | required  | 139 closed archives would otherwise fire, which is worse than the silence being fixed. |
| AC-3 | required  | The only AC that measures real blast radius rather than fixture behavior. |
| AC-4 | required  | Guards against changing behavior for the waves that are already correct. |
| AC-5 | important | Diagnosis cost is the harm being addressed; a finding that says only "invalid" recreates it. |
| AC-6 | required  | A lint change must never mutate the records it inspects. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-21 | Verified by execution before planning. | Guard evaluates False on a prose-era fixture (`source=None`, no errors, no inline marker) while `validate_external_review_evidence` on the same file returns `ok=False`. Full `wf docs-lint` on the fixture reports three unrelated findings and nothing about review evidence. |
| 2026-08-21 | Blast radius measured across all 236 wave records. | 139 closed and 1 planned (`1seaw`) lack the header; 0 active. Terminal scoping is required, and the expected new-finding count in this repo is exactly 1. |
| 2026-08-21 | Two alternative fixes rejected on evidence. | The 1.14.0 CHANGELOG entry buries the change in an Added-rendering bullet using the word "remains", so upgrade-time extraction would have been a no-op. Better refusal text improves the repair, which field evidence shows was already cheap. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------- | ------------ |
| 2026-08-21 | Fix the skip rather than add a preflight migration scan. | The validator already computes the correct answer and is simply not called. A preflight scan would need a per-release registry of what state becomes invalid, which is a new mechanism with the same authoring dependency that made the CHANGELOG route fail. | Preflight target-state scan (rejected: new mechanism, same authoring dependency); CHANGELOG extraction (rejected: falsified against the motivating release). |
| 2026-08-21 | Report at the docs gate rather than at upgrade specifically. | The upgrade already runs the docs gate, so fixing the gate surfaces this at upgrade time for free, and also surfaces it for a wave that drifted without an upgrade. | Upgrade-only reporting (rejected: narrower, and duplicates a gate the upgrade already runs). |
| 2026-08-21 | Closed waves stay silent. | 139 of 236 records are closed prose-era archives. Firing on history would drown the one live finding and train operators to skip the channel. | Fire on all (rejected: 139 to 1 noise ratio); migrate archives (rejected: rewrites history to satisfy a linter). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The new finding fires on historical archives and becomes noise. | AC-2 and AC-3 pin the behavior against the real 139 closed records, not a fixture. |
| A second status predicate drifts from the existing closed-status test in the same function. | The task requires reusing the predicate the projection check already applies rather than writing a new one. |
| A downstream target has many non-terminal prose-era waves and sees a burst of findings on upgrade. | The finding is per-record and actionable, and the repair is evidence-layer only. Field evidence shows one such wave took a single transcribed approval. Worth stating in the release note so a burst is expected rather than alarming. |
| The finding text ages into inaccuracy if the authority model changes again. | AC-5 asserts on the message, so a future authority change fails the test rather than silently shipping stale guidance. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
