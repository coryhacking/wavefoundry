# Readiness convergence delivery evidence

Owner: Engineering
Status: active
Last verified: 2026-09-20

## Scope and independent references

Implementation follows Requirements 1–8 in the admitted change. Protocol evidence and runtime evidence are separate: instruction pins test retention, the five observed decisions in `behavioral-scenarios.md` test the bounded brief, and canonical-producer fixtures exercise public Prepare/Implement response behavior. No result claims universal convergence.

The review packet's source fingerprint is `fdf5349386e3c17ef146c683ceef7f1d86338496511794c2c94871d17bababf9`. Reproduce it by forming a dictionary from these eleven sorted repo-relative paths to their `git hash-object <path>` output, serializing with Python `json.dumps(mapping, sort_keys=True)`, then hashing that UTF-8 string with SHA-256: `server_impl.py` under `.wavefoundry/framework/scripts/`; seeds `007-review-system-overview.md`, `100-project-prompt-surface-bootstrap.prompt.md`, `170-plan-feature.prompt.md`, `209-agent-harness-core.prompt.md`, `215-wave-council.prompt.md` under `.wavefoundry/framework/seeds/`; and `docs/agents/specialists/wave-council.md`, `docs/contributing/review-and-evals.md`, `docs/prompts/plan-feature.prompt.md`, `docs/prompts/prepare-wave.prompt.md`, `docs/specs/mcp-tool-surface.md`. Test files were outside this first packet while their author finished compatibility expectations; final verification includes them.

## Computational checks and negative controls

The test implementer executed 57 focused tests covering new behavior, ledger/projection controls and tool/lifecycle goldens. Only intentionally added Prepare response fields/advisories changed the lifecycle response golden. Removing precisely those additions from the regenerated response snapshot reproduced the prior snapshot; public signature fixtures and the pre-configured-gates historical snapshot were not edited. Existing lifecycle tests also exposed two exact diagnostic-list expectations; those are compatibility expectations for the intentional new advisory, not altered gate outcomes.

Essential protocol pins exercise 77 deleted-clause controls across seven protocol surfaces, two plan-shape surfaces and two finding-bar surfaces. These establish instruction retention only.

| Runtime mutation executed in isolation | Named failing test in `test_readiness_convergence.py` | Outcome |
| --- | --- | --- |
| Threshold 5 becomes 6 | `test_receipt_counts_zero_one_five_six_are_from_canonical_ledger` | Detected |
| Remove first `initial_delivery` cutoff | `test_receipts_after_first_initial_delivery_do_not_count` | Detected |
| Force observed count to zero | `test_count_observes_receipt_published_by_this_prepare` | Detected |
| Ignore project-only lanes | `test_lane_advice_matches_activation_union_and_current_receipt` | Detected after strengthening the fixture to retain a genuinely project-only lane |
| Treat stale approvals as current | `test_lane_advice_matches_activation_union_and_current_receipt` | Detected |
| Remove `advisory: true` | `test_receipt_counts_zero_one_five_six_are_from_canonical_ledger` | Detected |
| Omit count on lock refusal | `test_outer_lock_refusals_keep_null_count_and_original_error` | Detected |

The project-only-lane mutant initially survived because policy publication had copied that lane into the wave roster. Correcting the fixture removed the shared assumption; the runtime did not change to accommodate the test.

## Independent delivery review

Architecture and docs-contract both approve, from one fresh independent context (`1yfzu-arch-doc-independent-20260920`), with no blocking findings. The reviewer recomputed all eleven source hashes and executed temporary-root public Prepare/Implement probes: threshold 5/6, seven total receipts with six before delivery, unchanged underlying refusal and ledger bytes, missing/current/rotated approvals, and missing-ledger null. Threshold, cutoff and empty-roster mutants were detected. Fourteen additional instruction deletion controls were detected. These document controls prove presence, not adherence; the five observed behavioral decisions remain separate evidence.

Their runtime fixtures used existing canonical producers with lint/garden/background refresh stubbed. No transport, concurrency or full-suite claim is made by those lanes. Typed approval records preserve that scope and the shared-context limitation.

Code reviewer also approves the final fifteen-file packet, in the same fresh non-author context as architecture/docs-contract (not a separate independent vote). Three targeted outer-refusal tests passed; a removed lock-refusal field was detected in addition to the prior threshold/cutoff/roster controls. The protocol implementer supplied an additional runtime-only cross-check with six killed mutants; that cross-check is implementation evidence and does not approve its author's protocol.

The final packet fingerprint is `0e1f46340385f5c1a4bcb46f53fc61997295b92e953500418f8972235e798067`. Its recipe is the same sorted path-to-Git-blob mapping and JSON/SHA-256 recipe above, adding `.wavefoundry/framework/scripts/tests/test_readiness_convergence.py`, `test_server_tools_lifecycle.py`, `test_lifecycle_golden.py` and `fixtures/lifecycle-gate-golden.json` under that tests directory.

## Validation status

Full suite passed: **9,428 tests across 115 files**, 12 existing skips, 284.292 seconds. The runner's receipt reports `result: ok`; `inputs_hash` is `98f8dcb5c09d5a217fd62957c745b18f6485a760e2cef034eb6ccf89d3360440`, independently recomputed by importing `run_tests` with the scripts directory on `PYTHONPATH` and calling `run_tests._hash_inputs()`. Command: `/Users/coryhacking/.wavefoundry/venv/bin/python -B .wavefoundry/framework/scripts/run_tests.py`; captured output `/tmp/1yfzu-full-suite.log`.

Full `wf_validate_docs` passed with zero errors and warnings. Both edit gates are closed. Independent QA approves all ACs: 19 selected tests with no skips; eight injected runtime defects detected; live signature/digest controls and registered Prepare success/error metamorphic checks passed. The last mutation triggered an exact missing `advisory` key error rather than an assertion failure; it was not a setup error or survivor. QA recomputed all fifteen packet hashes and the final fingerprint. Registered probes stubbed model/index initialization and docs validation; response-size telemetry was explicitly normalized because added advisory text changes its size. The 12 full-suite skips were not independently reclassified by QA. All four required delivery approvals are recorded; code, architecture and docs-contract share one non-author context, with QA in a second independent context. `memory_propose(mode="create")` returned zero candidates (`no_material_evidence`); no memory was promoted. The operator subsequently authorized closure and commit; the wave is closed with typed operator approval.
