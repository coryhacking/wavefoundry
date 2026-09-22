# Delivery architecture and docs-contract review

Owner: Engineering
Status: active
Last verified: 2026-09-22

## Verdict and provenance

Final verdict: APPROVE for architecture and docs-contract, with correlated roles disclosed below. The integration failure is resolved and the current green full-suite receipt was independently checked. Required after-change retrieval evidence remains pending; the coordinator will withhold recording these approvals until that evidence is available.

Phase: delivery. Context: `/root/ypxw_delivery_arch_docs`. This context was newly started for delivery and did not implement or perform readiness review. Architecture and docs-contract roles share this context: their judgments are correlated, not two independent passes. Only this report was written; no source, ledger, close or commit operation was performed.

## Boundary and contract findings

The implementation fits the objective without introducing a new authority layer. Optional receipt metadata remains outside receipt identity; policy input serialization is unchanged, and lifecycle support still consumes the evidence facade rather than importing the orchestrator. The advisory is computed from existing lane authority, not a new persistence store. Temporary path classification is lexical and advisory; it neither proves existence nor rejects an otherwise valid record. Architecture/data-flow and tool-surface spec text describe these limits.

The canonical evidence protocol owns the detailed actionability and mutation obligations. Renderer carriers retain a direct protocol pointer, explicit delivery entry and event authoring tools, mutation-authority limits and all three independence codes. Seed 180 retains integration rereading, worker-versus-wave completion, tree fingerprint and moved-tree refresh obligations while collapsing duplicated evidence lists. The controlled-comparison sentence from the preceding wave remains intact; the new QA condition is sixth, so condition 5 keeps its known-bad meaning.

Fresh-install review guidance now carries delivery provenance, receipt-selected council, QA/AC checks, truth hierarchy and operator-owned exit boundaries. Existing customized prompts still require authored reconciliation; rendering is not represented as wholesale seed-to-prose propagation. The inventory's seed-160 propagation mechanism and distinction between direct canonical reading, authored upgrades and renderer-owned regions are coherent. Named project examples remain in local reviewer docs while generic seeds retain their rules without stale module names.

The local public scope-gap check is conditional on an AC Priority table, whereas seed 100 and the fresh template retain a bounded unconditional scope-gap check. This is the admitted local narrowing, not an implementation deviation. The typed-approval sentence in the local Required Before Close paragraph should be read with the explicit legacy-prose compatibility sentences in the same prompt; this is a minor clarity limit, not a new gate behavior.

## Frozen tree and inspection

All 45 paths in `evidence/delivery-tree.json` matched their SHA-256 fingerprints before and after this review. Comparison baseline was `/tmp/1ypxw-before`, which includes preceding-wave uncommitted work. Reviewed the three admitted change requirements and ACs; the six seed diffs; packaged template; renderer producer diff; unique authored prompt/role changes; architecture, spec and changelog updates; and generated evidence-block changes. `docs/contributing/review-and-evals.md` lacked a pre-wave snapshot, so its Git diff was inspected separately and contains only the shared owned-block change. MCP `code_outline` and targeted `code_read` were used for source definitions; shell diffing was used for bounded comparison and documentation inspection.

Sources consulted include `docs/architecture/layering-rules.md`, `docs/architecture/domain-map.md`, the two role contracts, and the seed/surface inventory. Verified policy snapshot serialization, optional metadata validation, attribution fallback, phase-specific review response and pure ephemeral-token classifier against source. This is not a replacement for the code/QA lane's complete state-machine review.

Independent census reproduced the inventory's remaining naming-hit line numbers for seeds 100, 180, 209, 212, 214, 221 and 239. Edited seeds 214/221 contain none of `_TS_SYMBOL_LANG_MAP`, `accel_embedder` or `server.py`. Remaining product-name references are pre-existing tool posture or generic framework instructions. The prompt manifest is byte-identical to the pre-wave snapshot. Public review prompt bytes changed 10221→9127; agent body 5968→4780. These measurements support lower entry size only, not total read cost or reviewer performance.

## Executed verification

From repository root, with bytecode disabled:

```sh
PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest test_render_agent_surfaces.HostNeutralOrchestrationCarrierTests.test_fresh_review_template_contract_and_known_bad_controls test_render_agent_surfaces.HostNeutralOrchestrationCarrierTests.test_public_fresh_render_delivers_every_lifecycle_phase test_render_agent_surfaces.ReviewProtocolCarrierRegistryTests.test_carrier_blocks_carry_chain_aware_independence_contract test_render_agent_surfaces.ReviewProtocolCarrierRegistryTests.test_reconciles_before_guru_guard_preserves_extensions_and_is_idempotent test_render_agent_surfaces.HostNeutralOrchestrationCarrierTests.test_customized_prompts_require_authored_merge_then_converge -v
PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest test_docs_lint.ReviewCycleChurnControlPinTests test_lifecycle_gates_structure -q
```

Observed: first command 5 tests passed in 0.268 seconds; second command 15 tests passed in 13.818 seconds. No skips. Duplicate-resource warnings appeared during scratch reload tests, which still passed. The fresh-template fixture invokes `render_agent_surfaces` against copied package templates, verifies generated prompt content before the owned block, and proves second-render byte stability. Its known-bad variants change the actual template used by that renderer, not a hand-written output fixture.

| Mechanism | Known-bad mutation | Oracle and observed result |
| --- | --- | --- |
| Delivery phase propagation | Template says readiness instead of delivery | Real-render contract assertion rejects mutant |
| Fresh-context approval provenance | Retained context records approval | Real-render contract assertion rejects mutant |
| Operator-owned close | Review claims it closes the wave | Real-render contract assertion rejects mutant |

All three controls executed and were caught within `test_fresh_review_template_contract_and_known_bad_controls`. These controls prove carrier delivery and oracle sensitivity, not agent obedience. The remaining selected tests exercise required lifecycle baselines, shared independence code pins, preservation/idempotence, authored customized-prompt reconciliation, seed/local sentence pins and import/reload boundaries.

## Integrity and limits

For the executed scoped evidence, all five integrity checks are true: `test_ran_without_unintended_skip`, `public_path_reached` (real renderer), `boundary_values_realistic` (fresh/customized package targets), `assertions_non_vacuous` (independent literal obligations and byte preservation), and `known_bad_detected`. `known_bad_detection_method`: focused-mutation, three real-template variants listed above.

Not run here: the full framework suite, retrieval benchmark, every lifecycle event permutation, or a live downstream upgrade. Those remain coordinator/code/QA evidence. The bounded review found no need for a new architecture decision. The final integration check below resolves the previously outstanding full-suite condition. Required after-change retrieval evidence remains explicitly outside this approval claim.

## Final integration recheck

The final 48-path `delivery-tree-final.json` matches disk with zero mismatches. None of the original 45 reviewed paths changed. Three additions contain only test-contract repair: two handler source hashes and their explanatory fixture description; the QA pin now accepts the planned conditional sixth check while preserving the first five; the stale renderer census allowance is removed while its historical SITES row remains. These repairs introduce no new runtime or prompt contract.

Independently recomputed `run_tests._hash_inputs()` and obtained `c7ad178ba2f8223f4ca113aa9970edfabba9cac9e2cb0f1bcd25d834afb8792e`, exactly the cache receipt's hash. Receipt result is `ok`, test count 9533, timestamp `2026-09-22T19:21:00.785063+00:00`. Read the final suite log: 9533 tests across 121 files, 12 intentional skips, 322.799 seconds, OK. This verifies the coordinator's receipt, not a claim I independently reran the entire suite.

Independently reran `test_fixture_fidelity_guidance`, `test_record_layout_census` and `test_mcp_tool_registry` using `run_tests._test_runner_python()` with `-B -m unittest ... -q`: 35 tests passed in 3.340 seconds, zero skips. An initial direct-system-interpreter invocation failed only the registry subprocess reload test because that subprocess lacked `mcp`; rerunning with the canonical runner's selected tool-venv interpreter passed. This environment mismatch was not suppressed or counted as a source defect.

Final scoped integrity declaration for both correlated roles:

```json
{
  "test_ran_without_unintended_skip": true,
  "public_path_reached": true,
  "boundary_values_realistic": true,
  "assertions_non_vacuous": true,
  "known_bad_detected": true,
  "known_bad_detection_method": "focused-mutation: three real-render template reversals (phase, retained-context approval, closing authority) were rejected; canonical-interpreter integration recheck passed all 35 selected tests"
}
```

Fresh independent delivery context remains `/root/ypxw_delivery_arch_docs`; architecture and docs-contract share it. The after-change retrieval benchmark is still pending and is not claimed as verified. No further writes will be made during the coordinator's quiet benchmark window.
