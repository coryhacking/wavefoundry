# Keep unresolved security evidence visible through closure

Change ID: `230k6-bug security-factor-closure-integrity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-10
Wave: 230k8 security-and-distribution-follow-ups

## Rationale

Waveforge reports that unknown security impact or containment can become terminal and disappear from closure review, and that change closure skips its unsettled-security check when the ledger is unreadable. Source inspection supports both paths: `review_evidence.security_factor_unsettled` checks only reachability and authority delta; `derive_disposition` can then fall through to `dont_do_later`. This is conditional, because earlier actionability rules can still yield `do_now`. `wf_close_change_response` checks pending candidates only when `read_review_event_ledger` returns no errors. `review_evidence` also restricts initial synthesis to new findings and repair cycles to actionable rows. These are source-supported inferences, not a reproduced served-tool failure. Expected behavior is visible unresolved security evidence and refusal of typed closure when review authority cannot be established.

## Product Intent

Operators and downstream distributions can distinguish a settled security decision from missing evidence. AC-1 through AC-4 establish this without treating every unknown correctness detail as a security blocker. This supports [the adopted vision](../../../VISION.md), Horizon 1's dependable delivery on the existing foundation; it does not redirect the roadmap or add an acceptance program.

## Requirements

1. A real security candidate (validation_status=real and authority_domain other than none) with unverified attacker_reachability, authority_delta, observable_impact or containment must not silently become dont_do_later. Preserve earlier do_now precedence, existing unknown-reachability/authority handling and the proven-unreachable exception (unsupported_reachability with supported_reachability=false). Invalid/conforming findings and correctness-only unknowns retain their existing treatment.
2. Review, change close and wave close must consistently expose pending security_unsettled findings and retain the existing operator decision route. Missing evidence is not proof of an exploitable defect and must not be described as one.
3. For typed containers, change close must obtain review authority through the validated reader used by Review and wave close (resolve_review_authority), refusing missing, malformed, truncated or semantically invalid required ledgers with review_ledger_unreadable and distinct missing/invalid explanations. No document, dependent-change state or ledger may be written on refusal. Legacy containers retain their established compatibility behavior.
4. Provide a served, append-only reconsideration route for an existing terminal real security finding when fresh evidence resolves or changes a security gate factor. Retain finding identity and prior history; apply current validation, disposition and review-coverage rules. Do not reopen arbitrary terminal correctness findings, rewrite historical events or manufacture approval. Record the selected protocol action and its authority checks before implementing this new transition.
5. Test closure through the served tool or an explicit served-close fixture seam that downstream distributions can override. Scope the security surface census to canonical framework carriers; project-owned docs checks must use the source-repository fixture boundary. Keep required canonical-source coverage.
6. Update security disposition/closure contracts, release notes and directly affected guidance to explain the additional unknown factors, unreadable-authority refusal and reconsideration route. Do not rewrite closed wave records or their ledgers.

## Scope

In scope: review_evidence.py, lifecycle_gates.py, review authority helpers, wf_server/server_impl.py and relevant served tool registration, security disposition and lifecycle tests/fixtures, canonical security guidance and its self-hosted mirrors, CHANGELOG.md and affected specs. The authoritative carrier set is the set of maintained instructions describing security_unsettled, discovered from source references during implementation; record the census before changing those instructions.

Out of scope: new security scoring, automatic risk acceptance, actor authentication, broad lifecycle redesign, changes to historical approvals, or treating the field report as vulnerability proof.

## Acceptance Criteria

- [x] AC-1: An executable disposition matrix covers each of the four unknown security factors separately and in combinations. The motivating impact/containment cases remain visible instead of terminal; do_now precedence, proven-unreachable, invalid/conforming and correctness-only controls retain intended outcomes.
- [x] AC-2: Served Review, change close and wave close agree on pending security candidates. On typed fixtures with missing, malformed, truncated and semantically invalid ledgers, closure refuses and before/after bytes show no mutations; valid settled and legacy controls behave as specified.
- [x] AC-3: An existing terminal security finding can receive fresh evidence through the served writer and produce a validated new head under the same identity with history intact. Invalid transition, missing evidence and unrelated terminal-finding controls are refused; resulting closure behavior follows the new head.
- [x] AC-4: The served-close test exercises an overridden distribution handler, and the security census runs with canonical carrier checks while permitting distribution-owned document wording. A missing required canonical carrier still fails.
- [x] AC-5: Changed contracts and release notes match implemented behavior, all tests this change adds or changes pass, its documents validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Reproduce the conditional disposition and served-close ledger failures; record expected versus observed outcomes.
- [x] Specify and test the security-only terminal reconsideration transition before source edits to that protocol.
- [x] Implement shared authority handling and factor coverage; update served fixtures and carrier census.
- [x] Update canonical guidance, local mirrors and contracts; run scoped negative controls and required delivery reviews.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Reproduce and implement | Implementer | Readiness | Source edits only after admission and Prepare. |
| Verify delivery | Required reviewers | Implementation | Independently check served behavior and negative controls. |

## Serialization Points

One implementer owns shared source edits. Coordinate CHANGELOG.md with concurrent work. Do not modify unrelated writing-guide work.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/wf_server/`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`
- `docs/contributing/review-and-evals.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/agents/`

## Affected Architecture Docs

Update docs/architecture/data-and-control-flow.md for review-authority and reconsideration flow; docs/architecture/testing-architecture.md for the served-close fixture seam. Update docs/contributing/review-and-evals.md and docs/specs/mcp-tool-surface.md as behavioral contracts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped repair and compatibility contract. |
| AC-2 | required | Establishes the scoped repair and compatibility contract. |
| AC-3 | required | Establishes the scoped repair and compatibility contract. |
| AC-4 | required | Establishes the scoped repair and compatibility contract. |
| AC-5 | required | Establishes the scoped repair and compatibility contract. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-10 | Authored from Waveforge v1.41.0 follow-up and current source inspection; not admitted or readied. | Report targets tag efc286b6 / commit d7ab7aad. Execution status: unverified; reproduce before implementation. Indexed retrieval refused index_runtime_stale, so targeted source reads supplied grounding. |
| 2026-11-10 | Readback: a real finding with a non-none `authority_domain` whose `observable_impact` or `containment` is `unverified` will derive `security_unsettled` (today: `dont_do_later`); unknown reachability or authority delta keep their domain-independent rule, as do `do_now` precedence, the shown-unreachable exception and correctness-only unknowns (AC-1). Change close will read review authority through `resolve_review_authority` and refuse a typed container whose ledger is missing or invalid with `review_ledger_unreadable`, writing nothing; legacy containers are unchanged (AC-2). Scope boundary: no new scoring, no ledger migration, closed records untouched. Expected files: `review_evidence.py`, `lifecycle_gates.py`, `wf_server/server_impl.py`, the security disposition tests and fixture support, seeds 007/209/237/239 and their mirrors, `docs/contributing/review-and-evals.md`, `docs/specs/mcp-tool-surface.md`, the two architecture docs, `CHANGELOG.md`. This serves Product Intent by keeping missing evidence distinguishable from a settled decision. | Served probe (scratch test over `wf_review_event_response`): a terminal `dont_do_later` head with unknown impact stays terminal; restarting it with its own judgment is refused as non-actionable. |
| 2026-11-10 | Reconsideration protocol selected before any protocol edit (requirement 4). Action: `event="finding"`, `run_kind="repair_start"` on the current terminal head, in the cycle the next repair start would use, with a judgment that marks the security gate factor in question `unverified` and so derives `security_unsettled`. Eligibility: the predecessor is the current head, is terminal (`not_required`, `completed` or `operator_waived`) and is a real finding; a `not_issue` predecessor is refused. Identity and history: same `finding_id`, the new head supersedes the predecessor, nothing is rewritten. Coverage: the new head is `pending` and holds `operator-signoff` withheld; it settles only through the unchanged fresh, independent reverification (which may still not add previously cleared lanes) or the operator close. A fresh judgment that is action-required takes the ordinary repair path with its own blocking and recheck lanes. Waiver: an `operator_waived` predecessor stays in the ledger as attributed history; the new head carries no waiver and Review and Close name the superseded waiver, so the operator decides again. Closed containers: the served writer refuses the reconsideration. Not reopened: a terminal correctness finding restarted with a judgment that derives no pending disposition. | Served probe: `repair_start` on a terminal head is already accepted when the new judgment derives `security_unsettled` or `do_now`, and refused when it derives a terminal disposition; a reverification with no repair start is refused. |
| 2026-11-10 | Reproduced before the fix. Expected: a real finding with `authority_domain: confidentiality` and `observable_impact: unverified` stays visible. Observed: the served writer recorded `dont_do_later` / `not_required`, and the existing `DerivationTests` case named `correctness` asserted that outcome. Change close: `wf_close_change_response` ran its unsettled check only inside `if not ledger_errors`, so a missing or invalid ledger skipped it. | `test_security_unsettled_disposition.py` before the edit: 31 passed, and after the rule change the `correctness` subtest failed with `('security_unsettled', 'pending') != ('dont_do_later', 'not_required')`. |
| 2026-11-10 | Carrier census taken before any instruction edit: every maintained file naming `security_unsettled`, excluding wave records and caches. Wording that states the factor rule: seeds 007, 209 (unknown-factor paragraph and gate step 3), 211, 237, 239; `docs/contributing/review-and-evals.md`; `docs/specs/mcp-tool-surface.md`; the `wf_review_event` docstring; `lifecycle_gates.py`; `review_evidence.py`; `CHANGELOG.md`. Named only as a disposition, unchanged: seeds 212, 215, 217, 221, 225, 236; `install/lifecycle-prompts/review-wave.prompt.md`; `docs/agents/qa-reviewer.md`; `docs/agents/specialists/council-chair.md`. | `grep -rIl security_unsettled` over the tree; the self-hosted mirrors under `docs/agents/` carry no factor wording, so none needed an edit. |
| 2026-11-10 | Implemented. `unsettled_security_factors` adds impact and containment for a non-`none` domain; `wf_close_change` reads `resolve_review_authority` and shares `security_candidate_diagnostics` with Review and Close; the builder refuses a reconsideration of a `not_issue` finding; the served writer refuses a repair start on a closed record (`wave_closed`); `security_candidate_state` names unverified factors and a superseded waiver. Tests: factor matrix over all 15 combinations with four controls each; closure parity; four corrupt ledgers in both modes with whole-tree byte comparison; a legacy control; reconsideration from a pre-repair terminal head; five refusal controls; a reconsidered operator waiver; the served-close seam with an overriding handler; the scoped census. The handler digest pin moved only for `wf_review_event` and `wf_close_change`. | `run_tests.py --file test_security_unsettled_disposition.py`: 49 tests OK. `--file test_close_change.py --file test_change_id_path_guard.py --file test_lifecycle_golden.py --file test_review_evidence.py --file test_extension_tool_modules.py`: OK. |
| 2026-11-10 | Landing rule: each guard deleted or loosened in a scratch copy of the tree, baseline green, mutant killed. Factor tuple emptied: `DerivationTests.test_the_factor_matrix_covers_each_factor_alone_and_in_combination`. Domain qualifier removed: `test_correctness_unknowns_and_settled_factors_derive_as_before`. Ledger refusal disabled, and the missing/invalid distinction forced: `ClosureAuthorityTests.test_an_unreadable_typed_ledger_refuses_the_close_and_writes_nothing`. Shared candidates emptied: `test_review_change_close_and_wave_close_name_the_same_pending_candidate`. Real-predecessor guard removed: `ReconsiderationTests.test_unrelated_terminal_findings_are_not_reopened`. Closed refusal disabled: `test_a_closed_record_takes_no_reconsideration`. Superseded waiver dropped: `test_a_reconsidered_operator_waiver_stays_in_the_ledger_and_is_decided_again`. | Scratch tree under the session scratchpad; 8 of 8 mutants killed. |
| 2026-11-10 | Gapfill: region reads for editing used the host file reader after MCP `code_read`, `code_keyword` and `memory_brief` oriented the work, because the loaded MCP server reported `loaded_code_stale` and its read responses carried advisories several times the size of the source range. Exact-text sweeps for the carrier census used shell `grep` over non-indexed paths. | MCP calls recorded in the context-efficiency ledger for the implement stage. |
| 2026-11-10 | Delivery review. Five lanes ran in fresh, independent contexts: code, QA, architecture, security and docs-contract all approved. One finding, `CODE-DEL-1` (low, introduced here): the `review_ledger_unreadable` message blamed the ledger when only the record's review projection was invalid, and the unsettled diagnostic used a singular verb for two factors. Repaired in cycle 1 and reverified by a fresh code-reviewer context; `test_a_broken_projection_is_refused_without_blaming_a_valid_ledger` and `test_two_unverified_factors_are_named_in_the_plural` each fail on the old wording. Accepted notes, not repaired: a record without the `review-evidence-source` declaration that still holds a ledger is no longer scanned by change close, which now matches Review and wave close and is reported by docs-lint as an orphaned ledger; the closed-record refusal covers `repair_start` only, and other event kinds can still append to a closed ledger, which predates this wave; a `completed` terminal predecessor has no reconsideration test. | Ledger: approvals for all five lanes; `CODE-DEL-1` head `do_now` / `completed`. Full suite after the repair: 12,709 tests across 238 files, 12 skips, OK. `run_tests.py --profile second` and `--profile declared` over the ten changed test files: 1,232 and 1,235 tests OK. `wf_validate_docs`: ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-10 | Extend the existing disposition and authority mechanisms, with a narrowly scoped append-only reconsideration route | This directly prevents silent terminal handling and unreadable-authority closure; success is served refusal/visibility and later evidence-based settlement, not an advisory count | Advisory-only listing can be ignored and does not repair closure; allowing arbitrary terminal re-synthesis broadens authority beyond this defect |

## Risks

| Risk | Mitigation |
| --- | --- |
| Overblocking nonsecurity or proven-unreachable findings | Use explicit negative controls and preserve legacy semantics. |
| Historical security heads remain terminal after classification repair | Exercise reconsideration from a pre-repair terminal head; do not migrate ledgers silently. |
| New transition bypasses review authority | Validate evidence, identity and review coverage through the served writer; request architecture and security review. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
