# An Unsettled Security Candidate Stays Open Until Settled

Change ID: `22ubf-enh unsettled-security-candidate-stays-open`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-08
Wave: 22upa security-candidates-and-uv-advisory

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

A real security finding whose attacker reachability or authority delta is still unknown cannot close silently, whatever rejection basis the reviewer picks. It holds `operator-signoff` withheld, and the status row names it with its promotion trigger, until evidence settles it or the operator closes it by name in an attributed record. Correctness-side `unverified` handling and every other disposition are unchanged, and no closed wave is re-judged.

## Requirements

1. **A fifth disposition, `security_unsettled`, triggered by facts.**
   - It joins `DISPOSITIONS`. `derive_disposition` returns it for a `real` record that is not action-required when `attacker_reachability == "unverified"` or `authority_delta == "unverified"`, whatever its `rejection_basis`.
   - One exception: `rejection_basis: unsupported_reachability` with `supported_reachability: false` is a finding shown unreachable, and stays `dont_do_later`.
   - `authority_domain` alone does not trigger it.
   - `do_now` keeps precedence. Every other record derives exactly as today.
2. **Record shape.**
   - A `security_unsettled` synthesis carries a non-`none` `rejection_basis`. `promotion_trigger` follows the existing rule: required for `insufficient_evidence`, `unsupported_reachability` and `disproportionate_repair`, refused otherwise.
   - It is never blocking for lanes (`derive_blocking` false). `review_depth` is `focused`. It never creates follow-on debt.
   - Its `repair_execution_state` is always `pending` while it derives `security_unsettled`, whatever the run kind. The synthesis builder's `repair_execution_state` expression gains this case, so a reverification that still derives it cannot write `completed`.
3. **It holds `operator-signoff` open, and only that.**
   - While a current head is `security_unsettled` and `pending`, `review_status_rows` marks `operator-signoff` `withheld`.
   - The `why` lists each such `finding_id` and its `promotion_trigger`.
   - The `next_action` says "operator decision required: settle by fresh evidence, or the operator closes it". It never presents the operator close as an agent action.
   - Lane approvals and their freshness are unaffected.
   - `wf_close_wave` and `wf_close_change` therefore refuse while one is open, with diagnostic `unsettled_security_candidate` naming each one.
4. **Settling by evidence.**
   - A `security_unsettled` head accepts `repair_start` (cycle n+1), the same as `do_now` and `maybe_later` heads do today.
   - A fresh, independent `reverification` by a lane then writes the settled judgment:
     - If it derives `do_now`, it is written `pending` and follows the normal repair chain.
     - If it derives `not_issue` or `dont_do_later`, it is written `not_required` and is terminal, as today.
     - If it still derives `security_unsettled`, it stays `pending` under requirement 2.
   - These predicates gain `security_unsettled` as a non-terminal disposition: `repair_start` admission, the repair-cycle aggregate check, the projection `terminal` flag, and the close-time repair checks. Lane clearing for it uses the existing reverification rule.
5. **Settling by the operator: an attributed close.**
   - `wf_review_event(event="finding", run_kind="reverification", actor="operator", ...)` with a `waiver` object (`waiver_id`, `waiver_scope`, `waiver_reason`, `waiver_risk`) is accepted for a `security_unsettled` head at cycle n+1, without a preceding `repair_start`. It is refused for any other actor, any other head disposition, or a missing waiver field.
   - The close writes its own `executable_evidence` record (`claim_kind: finding`). That record carries the same operator identity resolution as an `operator-signoff` approval: the resolved operator handle, the local account, and an optional `attested_by`. Its `integrity_checks` are null (not applicable).
   - It then writes a superseding head with the same judgment: `repair_execution_state: operator_waived`, `decision_authority: operator`, the waiver fields, the original `promotion_trigger`, and an `evidence_record_id` that links to that operator evidence record.
   - The validator refuses an `operator_waived` `security_unsettled` head whose linked evidence record's `verification_context.actor` is not `operator`. A hand-edited head without the operator evidence fails lint.
   - Close lists each waived candidate as an advisory `security_candidate_waived`, with the waiver reason and the operator identity.
   - The `wf_review_event` description and seed 209 say an agent records this close only on the operator's explicit instruction in the current request, the same rule as Wave Close.
6. **Closed waves are not re-derived.**
   - Full docs-lint validates every wave's `events.jsonl`, through the `validate_external_review_evidence` call in `wave_lint_lib/wave_validators.py`.
   - For a wave whose record `Status` is `closed`, the validator stops recomputing derived fields (`disposition`, `blocking`, `review_depth`, and the per-disposition repair-state rules). Schema, identity, digests, chain linkage and the projection checks still run. A closed wave's recorded dispositions, old or new, stay valid as written.
   - In a wave still open across the upgrade, a pre-change `dont_do_later` head that would now derive `security_unsettled` is accepted as written. Review and close report it as a non-blocking advisory `security_candidate_predates_rule`, with its trigger. A new synthesis for that finding uses the new rule.
   - About ten internal callers use `derive_disposition`. The implementer lists them and states how each treats the fifth disposition.
7. **Visibility without breaking existing records.**
   - `review_evidence_summary` counts `security_unsettled`.
   - `review_evidence_summary_line` appends `, security_unsettled N` only when N is non-zero, so every existing four-count "Machine review state" line re-renders byte for byte. Both byte-for-byte consumers then stay current: docs-lint's projection compare and the dashboard (`dashboard_lib`).
   - `wf_review_wave` and the close dry-run report each open candidate as `unsettled_security_candidate`.
8. **Surfaces.** Every surface that states the dispositions or the terminal rule names the fifth. The `docs/agents` copies are hand-maintained; render-surfaces does not propagate seed prose there, so they are edited directly. The surfaces are:
   - seed 209:
     - the unknown-factor paragraph ("treats the resulting `dont_do_later` as terminal ...");
     - the derivation ladder ("Every other real proposition");
     - the `disposition =` enumeration;
     - the terminal rule.
   - seeds 007, 211, 212, 215, 217, 221, 225, 236, 237 and 239, and `install/lifecycle-prompts/review-wave.prompt.md`;
   - `docs/contributing/review-and-evals.md`;
   - both terminal-rule statements in `docs/specs/mcp-tool-surface.md`;
   - `docs/agents/qa-reviewer.md` and `docs/agents/specialists/council-chair.md`;
   - the `wf_review_event` docstring and guided schema, with `tests/fixtures/register-surface-handler-digests.json` and `tests/fixtures/lifecycle-gate-golden.json` refreshed for those two changes only.

## Scope

**Problem statement:** a security finding with an unknown factor is terminal, so a wave can close with it unsettled and unnamed, and choosing a different rejection basis has the same effect.

**In scope:**

- `review_evidence.py`:
  - derivation;
  - the builder;
  - the validator, including the closed-wave rule;
  - the chain and terminal predicates;
  - the projection and summary;
  - the guided schema.
- The close and review diagnostics in `wf_server/`, and the `wf_review_event` operator close.
- The surfaces in requirement 8.
- Tests, golden fixtures and handler digests that change with them.

**Out of scope:**

- Correctness-side `unverified` handling: `observable_impact` or `containment` unverified does not trigger the new disposition.
- Lane blocking and approval freshness.
- Operator waivers for other dispositions.
- A new event kind or run kind.

## Platform Behavior

Ledger, validation and projection logic only, with no filesystem or process change. Behaviour is identical on Windows, macOS, Linux and WSL2.

## Acceptance Criteria

- [x] AC-1: Each of these real findings, recorded through the served `wf_review_event`, derives `security_unsettled` with `repair_execution_state: pending`:
  1. `attacker_reachability: "unverified"` with each of `insufficient_evidence`, `categorical` and `disproportionate_repair`;
  1. `authority_delta: "unverified"` with `insufficient_evidence`.

  On the current code each derives `dont_do_later` with `not_required`.
- [x] AC-2: A wave fixture with every required signoff approved, `operator-signoff` included, and a current receipt is closable on the current code. After appending one `security_unsettled` head:
  1. the `operator-signoff` row is `withheld`, and its `why` names the finding id and trigger;
  1. its `next_action` offers no agent-executable call;
  1. every lane row is unchanged;
  1. `wf_close_wave(mode="dry_run")` reports `unsettled_security_candidate` and is not closable.
- [x] AC-3: From AC-2's state, each settling path makes the wave closable, and full docs-lint passes after each:
  1. (a) `repair_start`, then a fresh, independent lane reverification that derives `not_issue`;
  1. (b) the same with `dont_do_later` on settled factors;
  1. (c) one that derives `do_now`, followed by its normal repair completion;
  1. (d) the operator close.

  The following are refused:
  1. a non-fresh lane reverification;
  1. an operator close by a non-operator actor, without a waiver field, or on a non-`security_unsettled` head.

  A reverification that still derives `security_unsettled` stays `pending`, and the row stays withheld. After (d):
  1. the operator evidence record carries the resolved operator identity;
  1. the head keeps its `promotion_trigger`;
  1. close reports `security_candidate_waived`.

  A hand-written `operator_waived` head without operator evidence fails validation.
- [x] AC-4: These cases are unchanged:
  1. a correctness finding (both security factors known, `observable_impact: "unverified"`, `insufficient_evidence`) still derives `dont_do_later`;
  1. `unsupported_reachability` with `supported_reachability: false` and `attacker_reachability: "unverified"` still derives `dont_do_later`;
  1. `authority_domain: "integrity"` with both security factors known still derives `dont_do_later`.
- [x] AC-5: Compatibility.
  1. Full docs-lint over every existing wave record in this repository passes unchanged, and each four-count summary line re-renders byte for byte.
  1. A closed-wave fixture holding a waived head and a superseded `security_unsettled` record validates.
  1. In an open wave, a pre-change security `dont_do_later` head validates with exactly one `security_candidate_predates_rule` advisory.
- [x] AC-6: A census test lists every file outside `docs/waves/` and `tests/` that names three or more of the four existing dispositions. It requires each one to also name `security_unsettled`, and it covers every requirement-8 surface. The `wf_review_event` description, guided schema and seed 209 state the operator close's explicit-instruction rule.

## Tasks

- [x] Derivation, builder, validator (including the closed-wave rule), chain and terminal predicates, projection and summary in `review_evidence.py`.
- [x] The operator close and the close and review diagnostics in `wf_server/`.
- [x] Requirement-8 surfaces; refresh the handler digest and lifecycle golden.
- [x] Tests for AC-1 to AC-6.
- [x] CHANGELOG `[Unreleased]` bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ledger | implementer | none | review_evidence.py and its tests |
| surfaces | implementer | ledger | server, seeds, specs, docs/agents, fixtures |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, `.wavefoundry/framework/seeds/`, `.wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md`, `docs/specs/mcp-tool-surface.md`, `docs/contributing/review-and-evals.md`, `docs/agents/qa-reviewer.md`, `docs/agents/specialists/council-chair.md`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: `docs/architecture/` does not describe the dispositions. The ledger contract lives in seed 209 and `docs/specs/mcp-tool-surface.md`, both updated here.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The new state, triggered by facts |
| AC-2 | required | Holding signoff open is the requested outcome |
| AC-3 | required | It must be settleable, including manually by the operator |
| AC-4 | required | Correctness handling and settled findings must not change |
| AC-5 | required | Existing and closed ledgers must keep validating |
| AC-6 | required | Every surface must describe it |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-08 | Planned from Waveforge item 1; operator chose option 3 (a non-terminal disposition). | operator answer |
| 2026-11-08 | Operator: an item must be closable manually so `insufficient_evidence` cannot keep it open permanently. Found that no tool writes `operator_waived`; requirement 4 and AC-3 now add an operator close on `wf_review_event`. | operator request; `review_evidence.py` synthesis builder |
| 2026-11-08 | Readiness round 1 repair (findings 22upa-docs-surface-census-incomplete, -arch-closed-wave-rule-breaks-new-records, -arch-summary-line-projection-equality, -qa-settle-paths-unwritable, -qa-reverify-marks-unsettled-completed, -qa-ac2-closable-claim-vacuous, -cr-summary-line-drift, -cr-closed-wave-rederive, -sec-rejection-basis-evasion, -sec-operator-close-unattributed). Operator chose: trigger by facts; stop re-deriving closed waves; attested operator close on explicit instruction. Requirements, scope, ACs and decisions rewritten. | repair_start records, context 22upa-impl-repair-1 |
| 2026-11-08 | Readiness cycle 1 continued: binding amendments, which take precedence over the sections above where they differ. (1) 22upa-docs-surface-census-incomplete: AC-6's census covers only the framework and contract surfaces (`.wavefoundry/framework/`, `docs/specs/`, `docs/contributing/`, `docs/agents/`, `docs/prompts/`); dated reports under `docs/reports/` and root review artifacts such as `VISION-review.md` are history and out of scope, so they are not edited. (2) 22upa-cr-closed-wave-rederive: requirement 6's skip is a `closed` parameter on `validate_review_evidence_records`, passed by both `wave_lint_lib/wave_validators.py` and `dashboard_lib._review_evidence_dashboard_state`; in closed mode the validator's repair-chain checks read each record's stored disposition instead of calling `derive_disposition`. AC-5 gains a known-bad fixture: a closed wave holding an old-rule `dont_do_later` head with `attacker_reachability: "unverified"` passes full lint and the dashboard state, and fails validation when the closed flag is not passed. Open-wave acceptance of pre-change `dont_do_later` covers superseded records as well as heads. `--upgrade-uv` handling note for 22ube is in that doc. (3) 22upa-qa-settle-paths-unwritable: requirement 5's operator close is recorded in the head's open repair cycle when one exists (after a `repair_start` or a still-unsettled reverification) and counts as terminal progress for that cycle in `_repair_cycle_progress`; when the head has no open cycle it is recorded in the wave's next cycle, never a lower one. AC-3 gains the case: a still-unsettled reverification in cycle k, then the operator close in cycle k, then another finding's `repair_start` in cycle k+1, with full docs-lint passing. Implementer notes from reviewers: `review_status_rows` must check the stored `security_unsettled` plus `pending` state; the new branch in `derive_disposition` sits before `maybe_later`. | reverification records, contexts 22upa-reverify-* |
| 2026-11-08 | Implemented. `review_evidence.py`: `security_unsettled` joins `DISPOSITIONS`; `derive_disposition` branch after `do_now`, before `maybe_later`; builder writes it `pending`, writes a reverification that settles a `security_unsettled` head as `do_now` `pending`, and requires `fresh_context`/`independent` for any lane reverification of one; `_build_operator_close` (waiver in `evidence.waiver`, no judgment, head's open cycle or `_guided_repair_cycle`); validator `closed` parameter on `validate_review_evidence_records` and `validate_external_review_evidence` (stored disposition, no derived-field recompute), open-wave acceptance of pre-rule `dont_do_later` on heads and superseded rows, operator-close link check; `_repair_cycle_progress` and the close-time independence audit treat the operator close as terminal progress or skip it with no open cycle; `security_candidate_state` feeds the `operator-signoff` withhold (stored state only) and the guided schema gains `waiver`. `lifecycle_gates`: `unsettled_security_candidate` (blocking, added to the shared registry), advisories `security_candidate_waived` and `security_candidate_predates_rule`. `wf_close_change` reads the ledger and refuses on stored `security_unsettled` + `pending`. docs-lint and `dashboard_lib` pass `closed`. Surfaces: seeds 007, 209, 211-217, 221, 225, 236, 237, 239, the install review-wave prompt, both `docs/agents` copies, review-and-evals, mcp-tool-surface; handler digest (wf_review_event only) and lifecycle golden (`waiver` entry, declared in test_lifecycle_golden) refreshed. Caller census, `derive_disposition`: `derive_blocking` (fifth is never `do_now`, so false); `derive_review_depth` (focused); `predates_security_rule` and `_validation_disposition` (the new rules); `review_authority_projection` finding facts (non-terminal while `pending`, terminal once `operator_waived`; the withhold reads stored state); builder repair-state expression and its two `synthesis["disposition"]` assignments; the `_repair_cycle_progress` and relationship/closure checks now go through `_validation_disposition`. `validate_review_evidence_records` without `closed`: `lifecycle_gate_support._prepare_policy_state` and server_impl Prepare publication (planned, readied or open waves only), server_impl `wf_review_event` append (a write; passing `closed` would skip derivation on newly appended rows, so it is not passed; a closed wave whose stored rows would re-derive differently fails closed with `review_evidence_invalid`), `run_tests._ledger_rows` (only ledgers changed during a run; a failure keeps the strict guard). None of 503 repository wave ledgers holds a row that re-derives differently. Deviations: (1) the amendment's closed-wave known-bad (old-rule `dont_do_later` fails without the closed flag) cannot fail, because requirement 6's open-wave acceptance accepts that same record; the known-bad used is an old-rule `maybe_later` with unknown attacker reachability, which fails without the flag and passes lint and the dashboard with it (mutating either caller's flag in a scratch copy fails the test). (2) `wf_close_change` findings are wave-scoped, so it refuses for any open candidate in the wave. (3) Six seeds and qa-reviewer saying `four-way` / `exact four dispositions` were corrected to five. Gapfill: shell grep and Python reads for retrieval in large files. Known-bad: the new test file run against HEAD's review_evidence, lifecycle_gates, server_impl, wave_validators and dashboard_lib in a scratch framework copy fails AC-1 (`dont_do_later`/`not_required`), AC-2 (row `approved`, no diagnostic), AC-3 (each path refused or not closable), AC-5 (no `closed`, no advisory, four-count only); AC-4 passes on both (regression guard); AC-6 census listed 15 surfaces missing before the edits. | `tests/test_security_unsettled_disposition.py` 30 OK; test_review_evidence, test_lifecycle_golden, test_mcp_tool_registry, test_close_change, test_render_agent_surfaces, test_credible_threat_unknown_factor, test_profile_literal_census OK; broad related set (77 files) green except `test_tree_kill_routing` (setup_index `_install_pinned_uv` / `_uv_version`, change 22ube, not this change); `wf_validate_docs` passes |
| 2026-11-08 | Delivery repair cycle 2, finding `22upa-del-prerule-maybe-later-stranded` (architecture-reviewer and code-reviewer): the rule before 22ubf derived a record that now derives `security_unsettled` as either `maybe_later` or `dont_do_later`, but only a pre-rule `dont_do_later` was accepted, so an open wave holding an old `maybe_later` with unverified attacker reachability failed every later write and close; and the server read paths (`wf_review_event` list, wave resource, status projection) validated closed waves without `closed`. Binding amendment to requirement 6 and AC-5: the open-wave acceptance covers a pre-rule `maybe_later` as well (`PRE_SECURITY_RULE_DISPOSITIONS`), the `security_candidate_predates_rule` advisory names the recorded disposition, and the three read paths pass `closed=True` for a closed record through `_validate_review_evidence_as_recorded` (record read via `_read_wave_record_text`; falls back to the old call when a loaded `review_evidence` lacks the parameter). The write path (`wf_review_event` append) stays strict, as before. The closed-flag known-bad is now a stored disposition the current rules no longer derive for any reason (`maybe_later` with `optional_value` none), since a pre-rule `maybe_later` is accepted in open waves too. QA gap closed: the `--upgrade-uv` test asserts the install runs under the held install lock. Seed 209, mcp-tool-surface and the CHANGELOG bullet updated. | test_security_unsettled_disposition 32 OK (new: open-wave pre-rule `maybe_later` keeps writing with the advisory; closed-flag known-bad including the list and helper paths; reload-window fallback); scratch mutants: exemption limited to `dont_do_later` fails the open-wave test only, helper ignoring `closed` fails the closed-flag test only; test_server_tools_lifecycle 666 OK (record-read seam census), test_setup_uv_advisory, test_review_evidence, test_lifecycle_golden, test_mcp_tool_registry, test_close_change, test_render_agent_surfaces OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-08 | Non-terminal disposition `security_unsettled` | Operator's choice of Waveforge option 3 | Advisory list only (option 1); operator acknowledgement event (option 2) |
| 2026-11-08 | Withhold `operator-signoff` only, not lane approvals | The operator decides; the seed keeps it out of lane blocking and freshness | Withhold the source lanes too |
| 2026-11-08 | Trigger by facts (`attacker_reachability` or `authority_delta` unverified), whatever the basis; drop the bare `authority_domain` trigger | Readiness findings: the basis label could route around it, and domain alone held settled findings open. Operator's choice | Keep `insufficient_evidence` as trigger and refuse `dont_do_later` with a security factor unverified |
| 2026-11-08 | Stop re-deriving dispositions for closed waves; structural and integrity checks stay | Operator: closed history should not be re-judged; also fixes new records failing after close | Record-keyed acceptance of the old shape; a `disposition_rules` version field |
| 2026-11-08 | Operator close writes its own attributed evidence, required by the validator; agents record it only on explicit current-request instruction; the status row never offers it as an agent action | Readiness findings: a self-declared actor with no evidence was a rubber stamp. Operator's choice | Fold the waiver into `operator-signoff` |
| 2026-11-08 | Fifth summary count only when non-zero | Keeps every existing record projection-current byte for byte | Canonicalize four-count lines as five-count |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A fifth disposition breaks consumers that assume four | Requirement 6 caller census; AC-6 surface census; AC-5 full lint |
| A hand-edited ledger closes a candidate | Requirement 5: the validator requires linked operator evidence |
| Operators waive by reflex | The waiver needs a reason and risk, and is attributed and reported at close |
| Skipping derivation in closed waves hides tampering there | Schema, identity, digest and chain checks still run; closed waves are already sealed history |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
