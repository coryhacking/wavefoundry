# Operator approvals stop asserting checks nobody ran

Change ID: `21qbb-bug operator-approval-forced-integrity-claims`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-27
Wave: 21sld operator-approval-honest-attestation

## Rationale

Every `operator-signoff` approval in the typed review ledger currently claims `test_ran_without_unintended_skip`, `public_path_reached`, `boundary_values_realistic`, `assertions_non_vacuous` and `known_bad_detected` are all `true`, although the operator ran no check of their own. The tool leaves no honest alternative:

- `review_evidence.build_compact_review_event` validates every approval through `_validated_integrity_checks(..., executed=True)`, which refuses any `false` value ("executed approval event cannot carry integrity_checks.<field>=false").
- The record validator (the `execution_status == "executed"` integrity check in `review_evidence.py`) refuses false booleans on any executed record.
- Seed 209 ("The five `integrity_checks` booleans attest to the evidence the recording actor actually produced … If any boolean cannot be honestly affirmed, do not approve") therefore makes an honest operator sign-off impossible, while close requires one.

Observed on 2026-10-27: the operator approvals for waves `21s7b`, `21fgr`, `21rft` and `21fgy` all carry five `true` checks with a free-text note saying "operator performed no separate probe". The typed ledger is the sole review authority (`1to78`/`1tomw`), so it now contains claims that never happened.

## Product Intent

An operator who signs off a wave records what they actually did — an approval of the reviewed scope — and the ledger no longer contains test-evidence claims attributed to them that they never made. Specialist and council approvals keep their full integrity attestation unchanged. Historical ledgers stay valid and readable. Boundary: only the `operator-signoff` approval shape changes; close-gate authority, lane requirements and every other record type are untouched.

## Requirements

1. `integrity_checks` become optional on an `operator-signoff` approval event. When omitted, they default as in requirement 2. When supplied, they keep the exact shape but may honestly carry `false`, the same rule as a non-executed finding. Existing callers that supply all-`true` checks keep working, and an operator who really ran checks can still say so.
2. When the caller omits checks, the stored operator approval record carries the five integrity booleans as `false` and `known_bad_detection_method` as a fixed text stating that operator attestation runs no check. Operator approvals also get their own default `expected` and `counterexample_or_failure_condition` text, describing an operator approval of the reviewed scope. Today's defaults say "the approving actor independently verifies the current affected scope" and "…not independently grounded", and seed 209 says operator approval is not mislabeled as independent review. It keeps `execution_status: "executed"`, `phase: "delivery"` and `required_for_approval: true`, so the existing close gate and approval-currency logic (`approval_record_phase` consumers, the closure check requiring executed delivery approval evidence) accept it unchanged.
3. The record validator accepts `false` integrity booleans on an executed record only when it is an `operator-signoff` approval by actor `operator`. Every other executed record keeps the all-`true` rule.
4. Existing operator approval records with all-`true` booleans remain valid, current and closable. No ledger is rewritten.
5. The guided review action for `approval:operator-signoff` no longer lists `integrity_checks` in `required_caller_inputs`. This extends the existing operator filter in the approval-action builder, which already strips `fresh_context`/`independent`; the `REVIEW_ACTION_CALLER_INPUTS` tuple and the response-level schema stay unchanged.
6. The written contract matches. Seed 209's integrity paragraph narrows its "If any boolean cannot be honestly affirmed, do not approve" sentence *in place* to specialist and council approvals and states the operator rule. The `wf_review_event` docstring's "executed claim also requires the exact caller-supplied `integrity_checks`" sentence and `docs/specs/mcp-tool-surface.md`'s "Executed approvals and findings require the exact caller-authored `integrity_checks` object" are corrected the same way.

## Scope

**Problem statement:** the approval schema forces the operator to assert test evidence they did not produce.

**In scope:**

- `review_evidence.py`: operator branch in `build_compact_review_event` approval handling, the record-validator exemption, and the per-action caller inputs for the operator approval action.
- `wf_server` `wf_review_event` docstring sentence (refresh the handler-digest pin if the docstring is part of it).
- Seed 209 integrity paragraph, narrowed in place (`seed_edit_allowed` gate). Seed 209 has no rendered `docs/` copy.
- `docs/specs/mcp-tool-surface.md` integrity sentence.
- Tests in the existing review-evidence test files.

**Out of scope:**

- Specialist, council, finding, reverification and repair-start integrity rules.
- Rewriting historical ledgers or their projections.
- Recording findings from another lane's code read: the tool already accepts a non-executed finding with honest `false` checks via `execution_status`; the 2026-10-27 friction was caller misuse, not a tool defect.

## Acceptance Criteria

- [x] AC-1: `wf_review_event(event="approval", signoff_key="operator-signoff", actor="operator", ...)` with no `integrity_checks` succeeds, and the stored record has all five booleans `false` and the fixed operator method text, and its `expected` and `counterexample_or_failure_condition` fields contain no "independent" claim. With explicit checks containing `false` values it also succeeds and stores them verbatim, and all-`true` checks still succeed. On the current tree the first two calls are refused ("requires an exact integrity_checks object" / "cannot carry integrity_checks.<field>=false").
- [x] AC-2: A wave whose only operator approval is the new shape passes `wf_close_wave` dry-run approval checks exactly as an otherwise identical wave with an old all-`true` operator approval does; a test asserts both cases.
- [x] AC-3: The record validator still rejects an executed specialist approval, council approval, and executed finding that carries any `false` integrity boolean. It also rejects `false` booleans on an executed record whose actor is not `operator` (an approval) or whose claim is not `approval:operator-signoff` (an executed operator-actor finding — 18 such records exist in committed ledgers). Removing either half of the operator predicate fails a test.
- [x] AC-4: Every committed `events.jsonl` under `docs/waves/` still validates (an existing-ledger census test, or the existing full docs validation, passes), and a recorded old-shape operator approval fixture remains current.
- [x] AC-5: The `approval:operator-signoff` review action's `required_caller_inputs` omits `integrity_checks`; specialist and council approval actions still include it, and `REVIEW_ACTION_CALLER_INPUTS` is unchanged.
- [x] AC-6: Seed 209, the `wf_review_event` docstring and `docs/specs/mcp-tool-surface.md` no longer state that every executed approval must affirm all integrity checks (a text assertion on each). The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] T-1: Add the operator branch to approval handling in `build_compact_review_event` and the stored-record defaults.
- [x] T-2: Narrow the record-validator integrity rule with an operator-approval predicate (actor `operator` AND claim `approval:operator-signoff`).
- [x] T-3: Operator filter for the approval action's caller inputs; operator default `expected`/failure text; docstring, seed 209 (in place) and tool-surface spec sentences.
- [x] T-4: Tests for AC-1..AC-5 with known-bad mutants of each predicate half; run the canonical suite last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | readiness | Single writer |
| Verification | code-reviewer, qa-reviewer, docs-contract-reviewer | implementation | Independent; mutants of the operator predicate |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`

## Affected Architecture Docs

N/A: the review-evidence authority, its record types and the close gate keep their structure; one approval shape gains an honest default. Seed 209 carries the contract text.

## Platform Behavior

Pure Python record validation and markdown; no filesystem, process or path behavior changes. Identical on Windows, macOS, Linux and WSL2.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the intent: operator approvals carry no test claims |
| AC-2 | required | Close must not regress |
| AC-3 | required | The exemption must not widen to evidence that does carry checks |
| AC-4 | required | Historical ledgers stay valid |
| AC-5 | important | Guided actions must not prompt for the claims |
| AC-6 | required | Change-local verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-27 | Leftovers fixed after delivery review, at the operator's request ("fix the leftovers"), under `framework_edit_allowed`, now closed. (1) The executed-integrity error text now reads "(for a specialist or council approval: do not approve; ...)", because an operator approval can no longer trigger it. The two `1uf64` tests that pin the full message were updated. (2) The earlier decision to leave `normalize_review_event_request` unchanged is reversed. The retry fingerprint now uses the same operator defaults the builder stores: `expected`, failure text, and the honest-false `integrity_checks` when omitted. So an omitted field and the same field spelled out fingerprint alike. The defaults are shared constants `OPERATOR_APPROVAL_EXPECTED_DEFAULT` and `OPERATOR_APPROVAL_FAILURE_DEFAULT`, with the predicate `is_operator_approval_request`. The cost is accepted: a retry of an operator approval recorded before this change no longer replays. Retries happen only on the open wave, and no open wave carries an operator approval. New test `test_retry_fingerprint_treats_an_omitted_operator_default_as_spelled_out` uses fixed literal expectations. The frozen-ledger fingerprint pin moved again, because only the operator row's `request_digest` changed. Full suite: 12,266 tests, 12 existing skips, OK, fresh receipt. | run_tests --no-cache (green) |
| 2026-10-27 | Canonical qualification. The first full run failed two files, both from this change. `test_declared_wave_fixtures` flagged the new test's literal wave-declaration text as unclassified; a `component-fixture` comment fixed it. `test_server_tools_lifecycle.test_frozen_single_lane_stale_approval_operator_equivalence` pins its starting ledger fingerprint, which moved because its operator approval now stores the operator default `expected` and failure text; a probe confirmed those are the only differing fields, with supplied checks stored unchanged. The pin was refreshed with a comment. Both edits were made under `framework_edit_allowed`, now closed. The rerun passed 12,265 tests across 213 files, 12 existing skips, 541.473s, with a fresh green receipt. Note: AC-3's figure of 18 committed operator-actor executed findings is the red-team's count; the QA readiness reviewer counted 9 with a different grep. The test builds its own operator-actor finding, so the count is not load-bearing. | scratchpad canonical-21sld.log (red), canonical-21sld-2.log (green) |
| 2026-10-27 | Implemented under `framework_edit_allowed`, with seed 209 under `seed_edit_allowed`; both gates are closed. `review_evidence.py`: `OPERATOR_APPROVAL_INTEGRITY_DEFAULT` and `is_operator_approval_record` (actor `operator` AND `claim_id == approval:operator-signoff`). The approval branch of `build_compact_review_event` takes optional checks for operator sign-off, validated with `executed=False`, and gives operator approvals their own `expected` and failure text. The `_validate_evidence_shape` executed-integrity rule exempts only `is_operator_approval_record`. The approval-action operator filter also strips `integrity_checks`, and `REVIEW_ACTION_CALLER_INPUTS` is unchanged. `normalize_review_event_request` defaults are deliberately unchanged: they only feed the replay digest, so an identical retry of an existing operator approval still replays. Docs: `wf_review_event` docstring (two sentences) with only that handler's digest refreshed, `docs/specs/mcp-tool-surface.md`, and seed 209 narrowed in place plus field-table and approval-evidence clauses. Tests: `OperatorApprovalHonestAttestationTests` (7) build the delivery run and approvals through `build_identified_review_event`. Mutants: dropping the actor half, dropping the claim half, `executed=True` in the builder, the old expected text, the reverted action filter, removing the validator exemption and the reverted seed sentence each fail. Owning files `test_review_evidence`, `test_lifecycle_gates`, `test_council_signoff_keys`, `test_mcp_tool_registry`, `test_intent_fit_approvals` and `test_server_package` ran 344 tests, OK. AC-4: full docs validation passes via MCP and as a fresh-process `wf docs-lint`, which validates every committed ledger, including about 670 old-shape operator approvals. The spec text is under `docs/`, not the packaged framework, so the AC-6 text assertions cover the seed and docstring and the spec is left to docs review. | scratchpad/m21sld mutants; run_tests --file x6; wf docs-lint |
| 2026-10-27 | Readiness repair after the red-team primer. The primer found two gaps: operator records kept default text claiming independent verification, and the seed 209 "do not approve" sentence, the docstring and `mcp-tool-surface.md` contract text would become false. Both are now in R2/R6, AC-1/AC-6 and scope. AC-5 now targets the existing operator filter in the approval-action builder. AC-3 names the operator-actor finding known-bad. The primer census found no reader of the integrity booleans or `execution_status` outside `review_evidence.py` (dashboard follows the validator), and 670 committed operator approvals, all old shape. | red-team primer; `review_evidence` approval-action builder operator filter; seed 209 integrity paragraph |
| 2026-10-27 | Planned. Code read: `_validated_integrity_checks` (executed approvals must affirm every boolean), approval branch of `build_compact_review_event` (always `executed=True`), the record-validator executed-integrity rule and `required approval evidence must be executed in delivery`, the closure check requiring executed delivery approval evidence, the approval-currency map keyed on `execution_status == "executed"`, `REVIEW_ACTION_CALLER_INPUTS["approval"]`. Seed 209 integrity paragraph. Observed forced-true operator records in waves 21s7b, 21fgr, 21rft, 21fgy. | `code_keyword`/`code_read`; events.jsonl of those waves |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-27 | Keep `execution_status: "executed"` for operator approvals and store honest `false` checks under a narrow operator predicate. | The close gate, approval currency and the required-approval record rule all key on `executed`. Keeping it means no gate logic changes, and old records stay valid. Replaying the motivating case: a 21rft-shaped close with the new record passes, and the ledger no longer claims operator tests. Success after release: new operator records carry `false` checks, and the readout shows no forced claims. | (a) A new `execution_status: "attested"`: honest, but touches three gate sites plus every reader, so more surface for the same outcome. (b) Drop the integrity fields from operator records: breaks the record schema's required-field set for all readers. (c) Leave the schema and rely on the free-text note: the authority keeps false claims. (d) Refuse caller-supplied checks on operator approvals: breaks existing callers and fixtures, and blocks an operator who really ran checks. (e) Red-team alternative, `execution_status: "not_applicable"` for operator approvals: honest and needs no new term. It changes three close-gate sites (required-approval rule, approval-currency map, closure check) plus projection wording. The chosen design changes one validator rule and leaves the gate untouched, at the cost of `executed` covering the operator's act of approval. |

## Risks

| Risk | Mitigation |
| --- | --- |
| The exemption widens to non-operator records | Predicate requires both actor `operator` and claim `approval:operator-signoff`; AC-3 mutants of each half |
| Readers elsewhere treat `false` integrity on an executed record as invalid | Census of every reader of the five fields at implementation (`code_keyword`, limit 0); AC-4 validates all committed ledgers |
| Handler docstring edit breaks the handler-digest pin | Refresh the pin as the existing test instructs |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
