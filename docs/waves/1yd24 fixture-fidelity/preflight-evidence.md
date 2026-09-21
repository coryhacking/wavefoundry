# Fixture-fidelity preflight

Owner: Engineering
Status: active
Last verified: 2026-09-20

## Census baseline

The pre-implementation Python literal census found 51 declaration occurrences across ten test files: four positive integration candidates, eighteen component inputs, eleven negative/corruption controls, five historical compatibility inputs, eight assertions/read checks and five removal/tamper operands. The classification is a review inventory, not a claim that all occurrences write a wave. There are 72 actual canonical creator calls across seven files.

Positive integration candidates: `test_dashboard_server._make_wave`, `test_memory_records.MemoryProposeTests._wave`, `test_docs_lint.PrepareCouncilVerdictLintTests._declare_with_typed_readiness`, and `test_server_tools_lifecycle.ReviewPhaseAliasTests.setUp`. The implementation census must also inspect supporting helpers such as `WaveCouncilPolicyTests._prepared_wave_with_change` that mix canonical creation with manual admission. Immutable historical/parser/golden files remain inputs under test.

## Producer feasibility

Disposable-root probe sequence using `server_tools_support.load_server()` and `_make_repo`: install a valid targeted policy block; patch `run_validate`, `run_garden`, `_run_post_write_lint`, and background refresh only within the probe; call `wf_create_wave_response(create)`; `_change_create_response(create)`; `wf_add_change_response(create)`; initial `wf_prepare_wave_response(ready)`; `wf_review_event_response(run, readiness)`; `wf_review_event_response(approval, wave-council-readiness)`; final Prepare ready. This sequence reaches a non-error final response. The initial Prepare publishes a receipt while reporting missing council approval. A receipt-free empty wave cannot approve. Omitting the readiness run can still pass standalone evidence validation, but final Prepare reports `review_evidence_invalid` for the missing readiness Review Run Record. The durable helper tests will encode these cases, so evidence does not depend on temporary probe files surviving.

## Propagation boundary

`render_agent_surfaces._carrier_protocol_block` emits static common guidance referencing seed 209. `_initial_review_carrier_text` reads seed 239 when creating a missing QA role, while existing project-owned role prose is preserved. Verification must distinguish shipped canonical seed/pointer coverage from automatic replacement of existing project prose. No such replacement currently occurs.
