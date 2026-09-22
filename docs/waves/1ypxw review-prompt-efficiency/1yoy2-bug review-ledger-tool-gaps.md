# Review Ledger Tool Gaps

Change ID: `1yoy2-bug review-ledger-tool-gaps`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-22
Wave: `1ypxw review-prompt-efficiency`

## Rationale

Two independent reviews (2026-09-21) of the **Review wave** prompt surface and of the implementation review step measured four waves' ledgers and found that the cost of delivery review sits in approvals, not findings: 44 of 73 approvals were re-approvals, 22 of them re-approving scope the lanes themselves called unchanged, and 29 of 112 evidence rows cited temporary paths. Three of the levers are tooling, GENERIC, and reach every target on upgrade.

1. Receipt rotation names no document. When a change-doc edit rotates the review-policy receipt, the tools already say more than the first draft of this plan claimed: `receipt_supersession_attribution` in `lifecycle_gate_support.py` names the old and new receipt ids, the differing semantic fields and the digested change-id list, and it is emitted as `review_policy_receipt_superseded` on the `wf_mark_ac` deferral path and as the pre-publication advisory `review_policy_receipt_stale` on a prepare dry run. What it cannot say, and states in every message, is which document changed: `policy_input_digest` in `review_policy.py` computes a per-change `sha256(canonical_review_policy_body(body))` into a local payload and stores only the aggregate hash, and `validate_policy_receipt` enforces a closed field set. On `ready` and `create` the rotation is silent except for the lapsed-approvals advisory. Lanes re-approve scope they cannot tell moved (wave `1ymzk`: twelve of twenty-eight approvals were rotation refreshes described as scope-neutral). Naming the document needs one optional receipt field; naming the section needs the previous canonical body, which nothing persists, so section-level attribution is not claimed.
2. Delivery approvals are re-recorded on rotation although nothing lapses them. `review_authority_projection` sets `receipt_binding_applies` only for readiness approvals, a delivery approval cannot even carry `policy_receipt_id`, and `_guided_review_actions` derives approval actions from that projection, so a rotation never mints a delivery approval action; the same wave still re-recorded architecture, code and qa delivery approvals under a new receipt because the review-status projection uses one "Why" string for both phases and gives no signal that delivery rows are not receipt-bound.
3. Ephemeral evidence is accepted silently. `artifact_or_test_id` is documented as a durable identifier, is required by the finding and approval evidence field sets, and is only shape-checked as a non-empty string; a quarter of the evidence rows across four waves cite `/tmp`, `/private/tmp` or a session scratchpad, which a later reviewer cannot open.
4. The owned executable-review-evidence block (`REVIEW_PROTOCOL_CARRIER_BLOCK` in `render_agent_surfaces.py`, written into the nineteen `REVIEW_PROTOCOL_CARRIER_REGISTRY` rows plus any native wrapper present on disk, per `review_protocol_carriers`) names no tool: it says "the typed review-evidence authoring surface" where an agent needs `wf_review_wave(phase='implementation')` and `wf_review_event`, and its third and fourth paragraphs restate seed 209's actionability gate and independence diagnostics that the tools return in `caller_input_schema` and as rejection codes.

## Requirements

1. Receipt-delta attribution, document level. The review-policy receipt record gains one OPTIONAL, non-semantic field, `policy_inputs`, holding the per-change entries `policy_input_digest` already computes (`change_id`, `kind`, `sha256`) and the project-policy digest; `build_policy_receipt` writes it, `validate_policy_receipt` adds it to its optional set, and it is NOT added to `receipt_semantic_fields`, so `derive_receipt_id`, the chain checks and every existing ledger stay byte-compatible and no evaluator-version bump is needed (state this explicitly against the convergence-pin rule). `_prepare_policy_state` computes the per-change digests once instead of discarding them. `receipt_supersession_attribution` is extended: when the superseded receipt carries `policy_inputs`, its message names the change docs whose digest differs; when it does not (every pre-upgrade receipt), it keeps today's sentence that the document is not attributable from persisted data. The attributable message ends with the clause "which section changed is not attributable from persisted data", so the two existing pins on that literal in `test_server_tools_lifecycle.py` (the `wf_mark_ac` deferral message and the prepare dry-run `review_policy_receipt_stale` payload) keep holding even though their fixtures, readied through `make_declared_wave`, will mint receipts that carry `policy_inputs` and take the attributable path. The existing code `review_policy_receipt_superseded` is reused, not duplicated. Emit sites: `wf_prepare_wave` in `ready` and `create` attaches it as an advisory on the success envelope and on the readiness-missing envelope (the branch that returns `error` with `missing_wave_council_signoff`, where an advisory changes nothing because `has_blocking_diagnostics` ignores advisories), gated on `policy_state["receipt_append_required"]` captured BEFORE `_publish_prepare_policy_state` runs AND on the published receipt carrying `supersedes_receipt_id` (a fresh wave's first Prepare appends a genesis receipt with nothing superseded and emits no advisory, matching the existing dry-run site's early return when no current receipt exists); `wf_review_wave(phase='prepare')` repeats it while any lane's latest readiness approval in the ledger carries a `policy_receipt_id` other than the current receipt's, derived from the ledger without the new field; superseded approvals remain history and do not prolong the advisory after every lane reapproves. The message states that readiness approvals against the old receipt are no longer current, that a lane whose remit excludes every changed document may re-record by reference to its prior evidence, and that a lane whose remit includes a changed document must review it before approving. The prepare envelope's `review_policy.receipt` projection strips `policy_inputs`, so the lifecycle golden captures no new unconditional field.
2. Delivery approvals are not receipt-bound, and the surfaces say so. Inside `review_authority_projection`'s status-row derivation in `review_evidence.py` (not in `review_status_rows` or any caller, and never in `server_impl.py`, whose residue guard forbids `review_status_rows(` there), the "Why" string branches on `receipt_binding_applies`: a current delivery approval reads "current executed approval, not receipt-bound, follows every affected repair"; readiness rows keep today's wording. The `wf_review_wave` and `wf_review_event` response-function docstrings and their registered tool wrapper docstrings each gain one sentence: a receipt rotation lapses readiness approvals only; delivery approvals stay current, and `review_policy_receipt_stale` blocks the implementation-phase review until re-Prepare without touching them. A test pins that a rotation after a delivery approval neither lapses it nor offers a delivery approval action (the plan expects this already holds).
3. Ephemeral-artifact advisory. A pure predicate `ephemeral_artifact_tokens(artifact_or_test_id)` in `review_evidence.py` returns the path-like tokens that lie under an ephemeral root; the root list is an exported constant: `/tmp`, `/private/tmp`, `/var/tmp`, `/var/folders`, `tempfile.gettempdir()` both raw and real-path resolved, `%TEMP%` and `%TMP%` values case-insensitively with either separator, and any path whose segments include `scratchpad`. A path-like token is a whitespace-, comma- or semicolon-delimited token, trailing punctuation stripped, that contains a path separator or starts with `/`, `~` or a drive letter. `wf_review_event_response` assembles `artifact_or_test_id_ephemeral` as `_diagnostic(..., advisory=True)` and appends it to the `stale_warnings` list on both the dry-run and the create branches when the field has at least one path-like token and every path-like token is ephemeral; zero path-like tokens is not flagged; a row citing one durable repository path alongside a temp path is not flagged; a bare test identifier alongside only temporary paths does not suppress the advisory; finding and approval records alike. The record is still written.
4. Owned-block producer text. `REVIEW_PROTOCOL_CARRIER_BLOCK` replaces its "typed review-evidence authoring surface" sentence with the two tool names and the phase argument, the instruction never to edit `events.jsonl` by hand, and the role-without-mutation-authority rule; drops its third paragraph (the four-way actionability gate; seed 209 owns it); and reduces its fourth paragraph to ONE sentence that names `reverification_context_not_fresh`, `reverification_actor_not_distinct` and `review_evidence_independence_invalid` and says the tool rejects those decidable contradictions as protocol policy, not caller authentication (the literal `not caller` is pinned), so the cross-pin between the block and the validator constants (`test_carrier_blocks_carry_chain_aware_independence_contract`, wave `1tmb2` AC-8) and the fresh-tree pins in `test_setup_wavefoundry.py` and `test_upgrade_wavefoundry.py` keep holding. The four `assertIn("four-way actionability gate")` pins (`test_render_agent_surfaces.py`, `test_render_platform_surfaces.py`, `test_setup_wavefoundry.py`, `test_upgrade_wavefoundry.py`) are updated to the new pointer sentence. `wf render-surfaces` re-renders every carrier (the parity check in `check_review_protocol_carrier_parity` fails the docs gate otherwise); the re-render is marker-region only. The Decision Log records the `1tmb2` AC-8 amendment: the codes still propagate to every carrier, in one sentence.
5. Tests. Receipt delta, through canonical producers in `test_server_tools_lifecycle.py` (`make_declared_wave`, `wf_prepare_wave_response`, `wf_review_event_response`): readiness approvals current, then one change doc edited in a digested section (attribution names it) and one in a normalized section (no supersession), a superseded receipt lacking `policy_inputs` (message degrades to today's sentence), and a genesis Prepare on a fresh wave (no advisory); the two `not attributable from persisted data` pins unchanged. After reapproval of every lane, the repeated prepare-review advisory clears while the old approval rows remain in the ledger. Delivery binding, same module: a delivery approval, then a rotation; `signoff_current(approval_phase='delivery')` true, the "Why" string reads not receipt-bound (new pin), no delivery action offered; the existing pins on "no current executed approval" and the dashboard payload (`test_dashboard_server.py`, `test_review_operator_integration.py`, `dashboard_lib.py` consumer) stay green because pending and readiness rows keep their wording. Ephemeral: rows for temp-only, temp plus durable, durable only, zero path tokens, and a scratchpad path NOT under a temp root, through the canonical writer; only the first and last are flagged; a mutant dropping the scratchpad rule fails on the last. Owned block: the carrier registry test, the constant cross-pin and the four pointer pins pass; a mutant reintroducing the third paragraph fails the new content pin. Golden fixtures: `fixtures/lifecycle-gate-golden.json` and `fixtures/lifecycle-gate-pre-configured-golden.json` (checked by `test_only_declared_observability_additions_since_extraction_golden`) stay unchanged because the receipt projection strips the new field and every fixture scenario holds one receipt; `tool-surface-golden.json` carries no descriptions, so the docstring edits do not move it. The declared-fixture census (`test_declared_wave_fixtures.py`) sees only producer-backed fixtures.
6. Follow-ups recorded, not done: section-level attribution (needs per-section digests), a typed shape for `tree_moved_under_review`, and a scope-neutral currency re-approval mode.

## Scope

**Problem statement:** receipt rotation cannot name the document that moved, delivery approvals are re-recorded without cause, temp-path evidence is accepted silently, and the owned reviewer block names no tool while duplicating the seed.

**In scope:** one optional non-semantic receipt field and its validator entry; `_prepare_policy_state`, `receipt_supersession_attribution`, `wf_prepare_wave_response`, `wf_review_wave_response`, `wf_review_event_response`; the status-row wording in `review_evidence.py`; the ephemeral predicate; the owned-block producer and its re-render; tests; CHANGELOG bullet; the architecture and spec sentences.

**Out of scope:** receipt identity, `receipt_semantic_fields`, the digest inputs, rotation rules, the readiness rule and the approval schema (unchanged); the independence audit (wave `1ypy6`); seeds (sibling enhancement); prompt prose (sibling documentation change); section-level attribution; a typed `tree_moved_under_review` shape; a currency re-approval mode.

## Acceptance Criteria

- [x] AC-1: A superseding receipt (never a genesis receipt) is reported on `wf_prepare_wave` (ready, create, and the readiness-missing envelope) and on `wf_review_wave(phase='prepare')` with the old and new ids and the changed change docs when the superseded receipt carries `policy_inputs`, degrading to today's not-attributable sentence otherwise; a normalized-section edit produces no supersession; receipt ids and every existing ledger are byte-compatible.
- [x] AC-2: The status row for a current delivery approval reads not receipt-bound, readiness and pending rows keep their wording, all four docstrings state the rule, and a rotation neither lapses a delivery approval nor offers a delivery approval action.
- [x] AC-3: `wf_review_event` attaches `artifact_or_test_id_ephemeral` on both branches only when every path-like token is ephemeral; the five-row fixture and the scratchpad mutant behave as specified; the record is written.
- [x] AC-4: The owned block names `wf_review_wave(phase='implementation')` and `wf_review_event`, keeps the three code names in one sentence, carries no actionability-gate paragraph, and is re-rendered into every carrier with the named pins updated.
- [x] AC-5: Framework suite green; both lifecycle goldens and the tool-surface golden unchanged; docs gate clean.

## Tasks

- [x] Inventory: the receipt publication path, `receipt_supersession_attribution` and its message pins, `receipt_binding_applies`, the `artifact_or_test_id` sites, every carrier and every test that pins the block.
- [x] Add `policy_inputs`, extend the attribution helper, emit on the three surfaces, strip it from the prepare projection.
- [x] Branch the status-row wording, add the docstring sentences and the delivery-binding pin.
- [x] Implement the ephemeral predicate and advisory.
- [x] Rewrite the owned block, re-render, update the pins.
- [x] CHANGELOG bullet; architecture and spec sentences; framework suite; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| tool-inventory | implementer | — | Committed before edits. |
| tool-fixes | implementer | tool-inventory | One owner for `server_impl.py`, `review_evidence.py`, `review_policy.py`, `lifecycle_gate_support.py`, `render_agent_surfaces.py`. |
| independent-review | required reviewers | tool-fixes | Fresh contexts; the fixture families are the known-bads. |

## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_gates.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_golden.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_review_operator_integration.py`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/testing-architecture.md`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` ("Review history and current state"): one sentence that delivery approvals are not receipt-bound and that a superseding receipt names the changed documents when its predecessor carries `policy_inputs`. `docs/architecture/testing-architecture.md` (review-evidence fixture row): one clause for the receipt-delta, delivery-binding and ephemeral fixture families. `docs/specs/mcp-tool-surface.md`: the two advisory codes beside `review_policy_receipt_stale`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The re-approval cost has no document-level explanation today. |
| AC-2 | required | Prevents needless delivery re-approvals the validator never asked for. |
| AC-3 | important | Advisory only; protects the durability of evidence. |
| AC-4 | important | Every reviewer carrier gains the tool names and loses a duplicated passage. |
| AC-5 | required | Change-local correctness. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-22 | Owned-block source and four pointer pins updated. Fresh-install test caught missing review-policy/focused-repair obligation anchors; kept these as a canonical seed pointer without restoring duplicated policy. 237 renderer/platform tests pass. Both restore-actionability and remove-tool controls killed by the carrier-contract test. Actual surface render pending seed edit window. | `evidence/carrier-mutants.py`; test_render_agent_surfaces + test_render_platform_surfaces. |
| 2026-09-22 | Readback: AC1–5 add non-semantic document attribution to receipts, explain delivery currency, warn on temporary-only evidence, and shorten the owned carrier block. A changed change doc will be named instead of merely listing every admitted change; receipt identity and approval authority stay unchanged. Owned scripts: review_policy, review_evidence, lifecycle_gate_support, server_impl, render_agent_surfaces and named tests. Pending operator clarification for ephemeral mixed identifiers and historical-versus-current readiness warnings; dependent edits held. | Current-tree inventory; baseline retrieval-quality-1ypxw-before.json. |
| 2026-09-22 | Allocation: core tooling delegated to implementer; coordinator owns renderer and integration. Inherited model/effort selected for coupled lifecycle correctness; observed runtime identity unknown. Gapfill: bulk source/pin census and mechanical multi-file text edits use shell after MCP owner/region discovery. No commit requested; prewave snapshots captured in /tmp/1ypxw-before rather than committing inventory. | MCP navigation and baseline snapshot. |
| 2026-09-22 | Planned from the Review wave and implementation-review prompt reviews. | Coordinator reads. |
| 2026-09-22 | Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): per-document attribution is not derivable from persisted data (one aggregate digest, closed receipt schema) and `review_policy_receipt_superseded` with `receipt_supersession_attribution` already exists with message pins; adopted the optional non-semantic `policy_inputs` field with the prepare-envelope projection stripped so the goldens stay unchanged; section-level attribution dropped; the status-row wording keyed on `receipt_binding_applies` inside the projection; the ephemeral predicate given a token grammar, a root list and a layering; the owned block keeps the three code names in one sentence so the `1tmb2` cross-pin and fresh-tree pins hold; the registry symbol corrected to `REVIEW_PROTOCOL_CARRIER_REGISTRY` plus native wrappers; seven test modules and the spec added to serialization points. | Readiness review in this wave directory. |
| 2026-09-22 | Tool AC-1 through AC-3 implemented after clarified readiness restoration: receipt metadata/attribution, latest-per-signoff repeat advice, delivery wording, and ephemeral advisory. 407 focused tests green; four targeted mutants detected; lifecycle goldens unchanged. | `tool-inventory.md`, implemented verification and pre-wave production delta. |
| 2026-09-22 | Supplementary lifecycle/dashboard consumers exposed two current-delivery wording pins; updated expected text, and both focused consumers pass. Broad dashboard checks retained known native-process limitations; full suite remains coordinator-owned. | `tool-inventory.md`, supplementary consumer checks; `test_server_tools_lifecycle.py`, `test_dashboard_server.py`. |

| 2026-09-22 | Reflect/repair C-1: full-suite exact-source handler census found the two intended tool-description changes. Updated only `wf_review_wave` and `wf_review_event` hashes in `register-surface-handler-digests.json`, with provenance; retained the hash algorithm, one-word docstring negative control, other 87 hashes and all three promised tool/lifecycle goldens. Both handler digest tests pass; independent reverification and full-suite rerun pending. | `evidence/delivery-code-review.md`; AC-2. |

| 2026-09-22 | Observe: implementation and delivery review complete; all ACs/tasks checked, C-1/C-2 terminal, four current delivery lane approvals, green current 9,533-test receipt and stable passing before/after retrieval comparison. Both edit gates closed. Wave remains open for operator closure; no commit performed. | `delivery-review.md` and typed review ledger. |
| 2026-09-22 | Correction from the independent objective evaluation: Requirement 4 places `check_review_protocol_carrier_parity` in the renderer; it lives in `wave_lint_lib/core_validators.py` and is invoked by the docs gate. The requirement text is left as written to keep the readiness receipt stable; this row is the correction of record. The docstring wording "do not lapse solely from rotation" was left unchanged: it states the same rule the status row pins, and rewording the two wrapper docstrings would rotate the handler-digest fixture, the framework test receipt and the retrieval receipt pair. | Independent evaluation report (session scratchpad); `wave_lint_lib/core_validators.py`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-22 | Operator clarification: only each lane's latest readiness approval prolongs the receipt advisory; only a durable repository path suppresses a temporary-only path warning. | Append-only history must not make warnings permanent; bare test names do not satisfy the specified path-token rule. | Historical-row warning forever; guessed test-ID recognition; rejected by operator. |
| 2026-09-22 | Optional non-semantic `policy_inputs` on the receipt; projection stripped from the prepare envelope. | Exact document attribution with receipt identity, ledgers and goldens unchanged. | Reuse the existing not-attributable message only (cheap, but AC-1 unmet); section digests (needs old bodies). |
| 2026-09-22 | Ephemeral citation is an advisory, never a refusal; predicate in `review_evidence.py`, diagnostic in the tool. | A refusal would block a lane over citation style; the validator's error channel refuses writes. | Refuse on create; rejected. |
| 2026-09-22 | Owned block keeps the three code names in one sentence (`1tmb2` AC-8 amended, not reversed). | The cross-pin between block and validator constants guards renames on both sides. | Drop the paragraph entirely and delete the pin; loses the rename guard. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A pre-upgrade receipt lacks `policy_inputs` and the first rotation after upgrade cannot name the document. | The degrade path keeps today's sentence; the second rotation is exact. |
| The receipt projection strip is missed and a golden reddens. | Requirement 5 names both fixtures and the observability-additions test. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
