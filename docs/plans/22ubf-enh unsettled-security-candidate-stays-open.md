# An Unsettled Security Candidate Stays Open Until Settled

Change ID: `22ubf-enh unsettled-security-candidate-stays-open`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-08
Wave: TBD

## Rationale

Waveforge's review of v1.40.0 (field feedback, 2026-11-08, item 1). Seed 209's rule "An unknown factor is not an absent factor" keeps a security candidate whose factor cannot be confirmed or ruled out. The candidate is recorded:

- as `real`;
- with the factor `unverified`;
- with `rejection_basis: insufficient_evidence`;
- with a `promotion_trigger`.

`review_evidence.derive_disposition` then derives `dont_do_later`, which is terminal:

- the validator requires `repair_execution_state: not_required` for it (`review_evidence.py`, the `disposition in {"not_issue", "dont_do_later"}` check);
- the projection marks it `terminal`;
- `review_evidence_summary` only counts it.

So a wave can close with a security candidate nobody settled, and neither review nor close names it. For a security finding, "unknown" quietly becomes "accepted". The operator chose Waveforge's option 3: a distinct, non-terminal disposition that keeps a status row open until the candidate is settled.

## Product Intent

A security candidate recorded under the unknown-factor rule holds `operator-signoff` withheld, and names itself with its promotion trigger in the status row, until a later synthesis settles it or the operator waives it by name. The outcome is that a wave can no longer close with an unsettled security candidate unseen. Correctness-side `unverified` handling and every other disposition are unchanged.

## Requirements

1. **A fifth disposition, `security_unsettled`,** joins `DISPOSITIONS`.
   - `derive_disposition` returns it for a `real` record that is not action-required and has `rejection_basis: insufficient_evidence`, when at least one security factor is unknown or in play:
     - `attacker_reachability == "unverified"`,
     - `authority_delta == "unverified"`, or
     - `authority_domain` other than `"none"`.
   - Every other record derives exactly as today. `do_now` keeps precedence.
2. **Record shape.**
   - A `security_unsettled` synthesis requires `rejection_basis: insufficient_evidence` and a `promotion_trigger`. Both rules exist today.
   - It is written with `repair_execution_state: pending`, `blocking: false` and `review_depth: focused`.
   - It is not terminal. It never creates follow-on debt.
3. **It holds `operator-signoff` open.** While a current head is `security_unsettled` and pending, the `operator-signoff` status row is `withheld`.
   - The row's `why` names each such finding id and its `promotion_trigger`.
   - The row's `next_action` names both ways to settle it.
   - Lane approvals and their freshness are unaffected. Seed 209 keeps "it does not drive security severity, blocking" for lanes.
   - `wf_close_wave` and `wf_close_change` therefore refuse until the candidate is settled. The diagnostic `unsettled_security_candidate` lists each one.
4. **Settling it uses existing paths only.**
   - A later `finding` synthesis for the same `finding_id` supersedes the head. If the factor is confirmed, it derives `do_now` and follows the normal repair. If it is ruled out, it derives `not_issue` or `dont_do_later` on its settled factors.
   - Alternatively, an operator waiver: `repair_execution_state: operator_waived` with `decision_authority: operator` and the existing waiver fields.
   - A settling synthesis written by a lane obeys the existing terminal-reverification rule (`fresh_context` and `independent` true).
5. **Visibility.**
   - `review_evidence_summary` and `review_evidence_summary_line` count `security_unsettled`.
   - `wf_review_wave` and the close dry-run report each one as an `unsettled_security_candidate` diagnostic with its trigger.
   - The summary-line pattern (`review_evidence.py`, the `current` group) accepts the old four-count line and the new five-count line, so existing wave records still parse.
6. **Compatibility.** A ledger written before this change validates unchanged.
   - A pre-change `dont_do_later` record that would now derive `security_unsettled` is accepted as written in a closed wave.
   - In an open wave it is reported once with a diagnostic naming it, and is re-derived only when a new synthesis is written.
   - The exact mechanism is settled at readiness. This repository's only `insufficient_evidence` record (`21KK5-DEL-AC6`) is a non-security record that still derives `dont_do_later`.
7. **Surfaces.**
   - The `wf_review_event` description and guided schema list the disposition and how to settle it.
   - Seed 209's unknown-factor paragraph replaces "treats the resulting `dont_do_later` as terminal, so it does not hold a gate or status row open" with the new rule.
   - The seeds and prompts that enumerate the four dispositions name the fifth: 007, 211, 212, 215, 217, 221, 225, 236, 237, 239, and `install/lifecycle-prompts/review-wave.prompt.md`.
   - Also updated: `docs/specs/mcp-tool-surface.md` and the rendered local copies (`docs/agents/qa-reviewer.md`, `docs/agents/specialists/council-chair.md`), through the render path.

## Scope

**Problem statement:** an unconfirmed security candidate is terminal, so a wave can close with it unsettled and unnamed.

**In scope:**

- `review_evidence.py`: derivation, validation, projection, summary, guided schema.
- The close and review diagnostics in `wf_server/`.
- The seed and spec text listed in requirement 7.
- Tests, golden fixtures and handler digests that change with them.

**Out of scope:**

- Correctness-side `unverified` handling.
- `unsupported_reachability` and `disproportionate_repair`, which stay `dont_do_later`.
- Any change to lane blocking or approval freshness.
- A new event kind or an operator-acknowledge event. The existing operator waiver is the acknowledgement.

## Platform Behavior

Ledger and projection logic only, with no filesystem or process change. Behaviour is identical on Windows, macOS, Linux and WSL2.

## Acceptance Criteria

- [ ] AC-1: A `real` finding with `rejection_basis: insufficient_evidence` and `attacker_reachability: "unverified"`, recorded through the served `wf_review_event`, derives `security_unsettled` with `repair_execution_state: pending`. On the current code it derives `dont_do_later` with `not_required`.
- [ ] AC-2: With such a head current, every other signoff is approved, and the receipt is current:
  - the `operator-signoff` row is `withheld`, and its `why` names the finding id and trigger;
  - `wf_close_wave(mode="dry_run")` reports `unsettled_security_candidate` and is not closable.

  On the current code the same ledger is closable.
- [ ] AC-3: Each settling path makes the same wave closable:
  - a fresh, independent reverification that derives `do_now` with its repair completed;
  - one that derives `not_issue`;
  - an `operator_waived` head with the waiver fields.

  A non-fresh settling synthesis is refused.
- [ ] AC-4: The derivation is unchanged for a correctness record: `authority_domain: none`, both security factors known, and `insufficient_evidence` still derives `dont_do_later`. It is also unchanged for `unsupported_reachability` and `disproportionate_repair` with a security factor unknown.
- [ ] AC-5: A ledger fixture written before this change, containing a security `dont_do_later` with `insufficient_evidence`, validates under requirement 6. The four-count summary line still parses.
- [ ] AC-6: The `wf_review_event` description, guided schema, seed 209 and the tool-surface spec name `security_unsettled` and both ways to settle it. A test holds them to `DISPOSITIONS`.

## Tasks

- [ ] Derivation, validation, projection and summary in `review_evidence.py`.
- [ ] Close and review diagnostics.
- [ ] Seed, prompt and spec text; render the local copies.
- [ ] Tests for AC-1 to AC-6; refresh golden fixtures and handler digests.
- [ ] CHANGELOG `[Unreleased]` bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ledger | implementer | none | review_evidence.py and its tests |
| surfaces | implementer | ledger | server diagnostics, seeds, spec, renders |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/seeds/`, `.wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md`, `docs/specs/mcp-tool-surface.md`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: the review ledger contract lives in seed 209 and `docs/specs/mcp-tool-surface.md`, both updated here; no component boundary or data flow changes.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The new disposition is the change |
| AC-2 | required | Holding the row open is the requested outcome |
| AC-3 | required | It must be settleable without new machinery |
| AC-4 | required | Correctness handling must not change |
| AC-5 | required | Existing ledgers must keep validating |
| AC-6 | required | Reviewers must be able to record it |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-08 | Planned from Waveforge item 1; operator chose option 3 (a non-terminal disposition). | operator answer |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-08 | Non-terminal disposition `security_unsettled` | Operator's choice of Waveforge option 3 | Advisory list only (option 1); operator acknowledgement event (option 2) |
| 2026-11-08 | Withhold `operator-signoff` only, not lane approvals | The operator decides whether to close with it open; the seed keeps it out of lane blocking and freshness | Withhold the source lanes too |
| 2026-11-08 | Settle by re-synthesis or the existing operator waiver | No new event kind | A dedicated acknowledge event |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A fifth disposition breaks consumers that assume four | Census every `dont_do_later` consumer at readiness; AC-5 and AC-6 |
| Downstream ledgers hold records that would re-derive | Requirement 6 compatibility rule, AC-5 |
| Reviewers over-use `insufficient_evidence` to defer security work | It now holds signoff open, which removes the incentive |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
