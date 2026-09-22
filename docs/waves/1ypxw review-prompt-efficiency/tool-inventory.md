# Review Tool Inventory

Owner: Engineering
Status: active
Last verified: 2026-09-22

Read-only inventory completed after wave 1ypy6 and before this wave's source edits. MCP `code_outline`, `code_keyword`, and targeted `code_read` verified these anchors; no lifecycle event or test execution was part of the inventory. Prior uncommitted work is preserved by the coordinator's pre-wave snapshots under `/tmp/1ypxw-before`.

## Implementation anchors

- `review_policy.py`: `policy_input_digest` computes sorted per-change entries but discards them. `receipt_semantic_fields` selects identity-bearing fields, `build_policy_receipt` copies additional fields, and `validate_policy_receipt` has a closed optional set. A metadata-only field can preserve evaluator version 7 and receipt identities by retaining the existing digest payload and serialization byte-for-byte.
- `lifecycle_gate_support.py`: `_prepare_policy_state` constructs receipt inputs; `receipt_supersession_attribution` currently reports aggregate differences only. Attribution after publication must identify the predecessor rather than compare the current receipt with itself.
- `server_impl.py`: `wf_prepare_wave_response` publishes before activation/readiness gates. Append the successful supersession advisory there so readiness-missing errors retain it, and remove metadata only from the response receipt copy. `_publish_prepare_policy_state` currently does not mutate its supplied state.
- `review_evidence.py`: `review_authority_projection` binds only readiness approvals to receipts. Delivery wording must preserve optional contributor attribution. `wf_review_event_response` shares `stale_warnings` across its dry-run and create returns; this is the advisory insertion point without changing record validity or identity.
- `render_agent_surfaces.py`: the coordinator owns the executable-review-evidence carrier block and its pinned renderer/setup/upgrade tests. The implementation worker owns the four tool docstrings and the core receipt/status/event tests.

## Clarifications surfaced

The precise every-path-token rule conflicts with the prose example suppressing a warning for a bare durable test identifier beside a temporary path. The operator confirmed the precise path-token rule: a durable repository path suppresses the warning; a bare test ID beside only temporary paths does not.

The instruction to repeat the advisory while any historical readiness approval names an old receipt would persist forever in append-only history. The operator selected latest readiness approvals per signoff. The plan is amended and focused readiness verification against receipt `review-policy-d33fe310355179ea758d` precedes the changed predicate.

## Verification plan

Use canonical declared-wave fixtures and typed producers for document edits, normalized edits, genesis receipts, supersession, and delivery currency. Pin legacy receipt compatibility and unchanged aggregate digest bytes; exercise optional metadata validation. Run focused tool/policy/evidence tests and the unchanged lifecycle goldens. No full suite is owned by this inventory worker.

## Before receipt and source preservation

`docs/reports/retrieval-quality-1ypxw-before.json`: verdict baseline; generation 1944 stayed complete under attempt `7bf30ea9846b4476a8bea27c4c18f8cc`; no invalidation or operator-review reasons; production end digest verified. File SHA-256 `bc649b675aca1a965e7292428f9f1b784acde5915895fed9a2b2614ea1a1f5c4`. The before image includes uncommitted completed 1ypy6 changes; HEAD alone is not this wave's baseline. Command: `python3 -B 'docs/waves/1ymzq handler-module-split-three/evidence/eval-quiet-window.py' --out docs/reports/retrieval-quality-1ypxw-before.json`. The ordinary all-content incremental refresh preceded the run; no full rebuild.

Renderer source shortened the carrier block and preserved review-policy/focused-repair obligation pointers after the real fresh-role fixture detected their omission. Renderer/platform suites: 237 tests pass. `evidence/carrier-mutants.py` kills restoration of the duplicate actionability paragraph and removal of the event tool name. Intermediate carrier sync passed lint; all 18 changed snapshotted docs carriers differ only within the owned protocol region. Final post-seed render is still required.


## Implemented verification

AC-1 through AC-3 and their implementation tasks are complete. The operator clarified that a bare test ID does not suppress an ephemeral-path warning and that repeated supersession advice follows each signoff's latest readiness approval. Both choices were incorporated after the coordinator restored readiness on receipt `review-policy-d33fe310355179ea758d`.

The focused command below passed **407 tests** in 28.256 seconds:

```bash
PYTHONPATH=.wavefoundry/framework/scripts/tests python3 -B -m unittest test_server_tools_lifecycle.WaveCouncilPolicyTests test_review_policy test_review_evidence test_review_operator_integration test_phase_gates test_events_only_residue_census test_lifecycle_golden test_declared_wave_fixtures
```

The canonical producer tests cover readiness current before rotation; changed-document attribution; normalized edits with byte-identical ledgers; genesis silence; legacy receipts without metadata; ready/create success and readiness-missing envelopes; delivery currency and no new delivery approval action; partial readiness refresh, full clearance with retained history, and delivery-only history; ephemeral approval and finding previews/writes. The approval cases include the requested five cases plus the clarified bare-test-ID-plus-temp case. Root boundaries, Windows case/separator spelling, and historical readiness wording are covered. Both lifecycle goldens remain unchanged. The strict advisory emit-site census is in `test_server_tools_lifecycle.py`, and names the two supersession sites and the event advisory explicitly.

Four in-memory known-bad controls each caused the intended assertion failure, without modifying repository source: removing scratchpad classification; removing document attribution; consulting all historical readiness approvals instead of the latest per signoff; and adding `policy_inputs` to receipt identity. These are detection evidence for the changed behavior, not an independent review. During test development, an initially unapproved receipt fixture and an incorrect `record_id` lookup were corrected to explicit typed approvals and `evidence_record_id`; the final passing run includes those corrections.

## Production delta relative to pre-wave snapshot

AST comparison against `/tmp/1ypxw-before/.wavefoundry/framework/scripts/` found precisely these function deltas (nested changes also change their containing function's AST):

| Module | Added functions | Changed functions |
| --- | --- | --- |
| `review_policy.py` | `policy_input_snapshot` | `policy_input_digest`, `validate_policy_receipt` |
| `review_evidence.py` | `artifact_path_tokens`, `ephemeral_artifact_tokens`, `stale_readiness_receipt_ids` | `review_authority_projection` |
| `lifecycle_gate_support.py` | none | `receipt_supersession_attribution`, `_prepare_policy_state` |
| `server_impl.py` | none | `wf_review_event_response` and nested `transact`; `wf_prepare_wave_response`; `wf_review_wave_response`; `register_mcp_surface` through nested `wf_review_wave` and `wf_review_event` docstrings |

Module-level changes are the `os`/`tempfile` imports and exported ephemeral-root constant plus captured environment roots in `review_evidence.py`, the imported snapshot helper in `lifecycle_gate_support.py`, and three imported evidence helpers in `server_impl.py`. No retrieval implementation was modified. The digest's canonical JSON payload and serialization remain identical, and evaluator version stays 7: metadata is excluded from `receipt_semantic_fields`, so no convergence-pin version bump or historical ledger rewrite is appropriate.

Full framework validation, final docs validation, after-retrieval evaluation, and independent delivery review remain coordinator-owned. No commit or wave close was performed.

## Coordinator integration checks

On 2026-09-22, all 13 `test_tool_surface_golden.py` tests passed through unittest discovery. The public tool fixture and both lifecycle fixture JSON files are byte-identical to `/tmp/1ypxw-before`; their SHA-256 values are respectively `2d8dad0a2e4230e856e8b65c2624d78d444e0531780d00ef694d1bf8147f7e4c`, `7fc0cd4da50b95a0058b7a7a727ebcf2b70651a369f2d3d2827658c4ec874ec1` and `e72420b56a9fa57ba039dc88ab42672dd50024c8678c3b363d191653c45a9f42`. This checks public registration compatibility; the full framework suite remains pending.


## Supplementary consumer checks

The full lifecycle module ran 552 tests and found one existing current-delivery wording expectation in `WaveLifecycleMutationTests.test_typed_review_approval_updates_machine_and_human_state`; its expected string was updated for AC-2. A subsequent dashboard-module run (216 tests, one skipped) found the analogous current-delivery expectation in `DashboardSnapshotTests.test_dashboard_approval_state_comes_from_validated_external_records`. That expectation was updated as well. Both exact corrected consumer tests pass together. Pending and readiness wording remains unchanged.

The broad dashboard run also encountered native-process limitations: six CLI-daemon identity subtests could not enumerate command-line PIDs (`dashboard_cmdline_pids` returned `None`), and `test_mcp_start_confirms_serving_own_child` reported that the child exited before serving. These paths were not modified. The coordinator will run canonical validation with native execution; this local dashboard run is not reported as green. No extra dashboard implementation edit was made.

MCP `wf_validate_docs` passed with no errors or warnings after tool implementation and tracking updates. Canonical full-suite and final documentation validation remain coordinator-owned after all wave surfaces finish.
