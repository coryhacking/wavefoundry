# Independent delivery QA review — 1ypxw

Owner: Engineering
Status: active
Last verified: 2026-09-22

Verdict: APPROVE final implementation and test coverage after C-1 and C-2 repairs. The whole-suite receipt is green and independently confirmed current. Retrieval after-measurement and final docs gate remain coordinator integration checks; this approval does not claim their results or authorize closure.

Context: `/root/ypxw_delivery_qa`, fresh for delivery, independent of implementation and readiness. This is one QA lane, not several votes. Scope: three admitted changes; reviewed against `/tmp/1ypxw-before`, which retains the preceding wave's uncommitted work, not Git HEAD. All 44 paths in `evidence/delivery-tree.json` matched at entry and exit. No production or lifecycle state edits.

## Execution and fixture fidelity

MCP `code_outline`, `code_keyword` and `code_read` located and read the changed fixtures and predicate/authority owners. An initial unsupported `path` keyword on `code_keyword` was rejected; retried with its supported `glob` argument. Shell was used for executable probes, snapshot comparison and this report.

Independently executed 13 tests with zero skips: seven new `WaveCouncilPolicyTests` methods (ephemeral approval preview/write, ephemeral finding preview/write, delivery-only history, prepare attribution/delivery currency, success/legacy fallback, latest approval per lane, genesis), `LockAndPublicationPolicyTests.test_policy_inputs_metadata_preserves_receipt_identity_and_history`, and all five lifecycle golden tests. All passed in 8.205 seconds.

Independently executed 31 tests with zero skips: `HostNeutralOrchestrationCarrierTests`, `ReviewProtocolCarrierRegistryTests`, `ReviewCycleChurnControlPinTests`, and `EphemeralArtifactTokensTests`. All passed in 0.486 seconds.

Reproduce from repository root with `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest` followed by the class/method names above. The seven lifecycle method names are the methods at test_server_tools_lifecycle.py:9157–9353; source navigation established those exact test bodies rather than relying on their labels.

The fixture creates the change, admits it, prepares it and records approvals through production functions. Its declared-wave helper carries explicit docs-gate stubs, so these tests claim lifecycle/advisory behavior, not docs-validator behavior. Deliberate requirements and progress-log edits are test inputs. The assertions observe public response status and ledger bytes, receipt IDs, retained approval IDs, per-lane partial reapproval, complete reapproval and delivery actions. They do not short-circuit on an earlier refusal. The legacy metadata case intercepts the receipt producer only to omit the new optional field, then returns through canonical recording/Prepare. The finding case verifies the actual stored finding in authority records.

## Known-bad controls

All mutations were confined to the reviewer process or disposable render targets. No repository source was rewritten. Execute `python3 -B 'docs/waves/1ypxw review-prompt-efficiency/evidence/delivery-qa-mutants.py'` for the five independent runtime mutations.

| Mutation | Target assertion | Result |
| --- | --- | --- |
| Suppress temporary-path predicate for approval | Public preview reports advisory for `/tmp/probe.log` | Killed: assertion failure, no error/skip |
| Suppress predicate for finding | Public finding preview carries advisory | Killed: assertion failure, no error/skip |
| Inspect every historical readiness approval | Advisory clears after all lanes reapprove | Killed: assertion failure, no error/skip |
| Inspect one latest approval globally | Advisory remains after council reapproves while QA is stale | Killed: assertion failure, no error/skip |
| Remove scratchpad classification | Non-temp-root `project/scratchpad/probe.log` still warns | Killed: assertion failure, no error/skip |
| Fresh template says readiness instead of delivery | AC-derived contract applied to actual renderer output | Killed by executed template test |
| Fresh template permits retained-context approval | Same public renderer contract | Killed by executed template test |
| Fresh template closes the wave | Same public renderer contract | Killed by executed template test |
| Restore owned actionability paragraph | Carrier contract | Killed by independently rerun `evidence/carrier-mutants.py` |
| Remove named event tool | Carrier contract | Killed by independently rerun `evidence/carrier-mutants.py` |

No survivors; no full-file mutant reruns were needed. The template and carrier mutations were authored by implementers but execution and test-body inspection here were independent. Prompt presence is not evidence of future reviewer adherence.

## Independent reference and compatibility

Reference: the admitted requirements and explicit operator decisions, plus pre-wave implementation for compatibility. Falsifiers are loss of old receipt identity, unexpected normalized-edit rotation, premature/never-ending warning, altered delivery currency, advisory refusal, and template authority expansion.

Directly imported the pre-wave policy module and compared its `policy_input_digest` against current `policy_input_snapshot()[0]` for disabled/default, universal, and targeted configurations, with admitted requirement bodies and a progress-log section. All three matched. An initial dynamic-import harness omitted registration in `sys.modules` and failed before executing the comparison; corrected the harness and obtained all three passes. This was a harness error, not product evidence.

AST comparison confirms `receipt_semantic_fields`, `derive_receipt_id`, `_approval_rows` and `signoff_current` are unchanged from the pre-wave snapshot. Both lifecycle golden JSON fixtures, the tool-surface golden and prompt-surface manifest are byte-identical to that snapshot.

## AC reconciliation

| Change | ACs | Evidence and remaining boundary |
| --- | --- | --- |
| 1yoy2 | 1–2 | Producer-built rotation/legacy/genesis/normalized controls, per-lane partial/all-clear mutations, unchanged receipt semantics and delivery-current/no-action assertions |
| 1yoy2 | 3 | Finding and approval preview/write, durable-path and zero-path negative controls, bare test ID positive control, scratchpad and Windows case/separator unit boundary, three advisory mutants |
| 1yoy2 | 4 | Carrier registry/cross-pins and two killed owned-block controls |
| 1yoy2 | 5 | Goldens verified unchanged; full suite and docs gate remain coordinator integration checks |
| 1ypxu | 1–5 | Independently read requirements; seed and orchestration pins execute, preserve packet/integration anchors, assert mutation pointers/budget and phase/provenance wording; source review supports scoped edits |
| 1ypxu | 6 | Propagation is explicitly documented by the inventory; rendering tests prove rendered carriers only, not human reconciliation on an arbitrary future target; final suite/docs/gate status remain coordinator checks |
| 1ypxv | 1–4 | Local prompt/role pins; actual fresh template render with three known-bad cases and repeat-render byte equality |
| 1ypxv | 5 | Manifest byte comparison and frozen-source hashes verified; tests cover owned carrier parity; final docs gate and final integration receipt remain coordinator checks |

## Integrity and limits

`fresh_context: true`; `independent: true`.

- `test_ran_without_unintended_skip: true`
- `public_path_reached: true` — response functions are the production lifecycle surface; renderer invoked on disposable target repositories.
- `boundary_values_realistic: true` — reachable canonical setup and real append-only histories; temporary paths are deliberately lexical inputs.
- `assertions_non_vacuous: true` — explicit expected responses/ledger state plus killed mutations.
- `known_bad_detected: true`
- `known_bad_detection_method: focused-mutation` — five independently injected runtime controls and five independently rerun renderer/template controls, all killed on the named assertions.

Budget: eight-minute bounded QA pass. Did not rerun the whole framework suite, native Windows execution, runtime model retrieval evaluation, every malformed metadata shape, or every possible path spelling. Those are not claimed. The advisory is deliberately lexical and does not prove that a cited non-temporary path exists or belongs to the repository. Common-mode risk: the producer-built integration fixtures exercise shared production setup; their expected results derive from the plan/operator contract and mutations, while digest compatibility additionally uses the pre-wave implementation.

Coordinator update after the bounded checks: the code lane reports two handler-digest fixture mismatches caused by the intentionally changed wrapper docstrings, and a native test interpreter missing `mcp`. These were not reproduced by this QA pass. The handler repair and its independent verification remain pending; do not record this report as an unconditional delivery approval. The three golden comparisons above remain valid and distinct from that handler-digest fixture.

## Final integration assessment after repairs

The earlier pending statements above describe the initial review boundary. C-1 and C-2 now have separate fresh independent repair reverification reports (`C1-reverification.md`, `C2-reverification.md`), which this QA lane read. I independently compared both repaired test files with the pre-wave snapshot: six-condition expectation plus conditional heading pins; one obsolete ALLOWLIST exemption removed; historical SITES retained with a retirement comment. Scanner predicates/exclusions/polarity controls are unchanged. I reran both complete modules: eight tests passed in 0.262 seconds with zero skips. The handler fixture changes only its description/provenance and the two intended wrapper entries (`wf_review_event`, `wf_review_wave`); the other entries are unchanged. I reran `test_mcp_tool_registry.HandlerDigestTests` using `/Users/coryhacking/.wavefoundry/venv/bin/python`: two passed in 0.389 seconds, including its one-word known-bad control. No repair source was authored by this reviewer.

Final fingerprint: all 48 paths in `evidence/delivery-tree-final.json` matched. Independently imported `run_tests` and recomputed `_hash_inputs()`: `c7ad178ba2f8223f4ca113aa9970edfabba9cac9e2cb0f1bcd25d834afb8792e`, equal to the cache receipt with `result: ok`, `test_count: 9533`, and `ran_at: 2026-09-22T19:21:00.785063+00:00`. Read `/tmp/1ypxw-full-suite-final.log`: 9,533 tests across 121 files, 322.799 seconds, OK; 12 suite skips reported. Those are the suite's recorded skips, not hidden failures; my 44 original and 10 final targeted checks had no skips. I verified the receipt/log rather than claiming to have launched that full run myself.

Final QA integrity remains: `test_ran_without_unintended_skip: true`, `public_path_reached: true`, `boundary_values_realistic: true`, `assertions_non_vacuous: true`, `known_bad_detected: true`; method `focused-mutation` (the independently executed controls in this report, plus final handler-digest known-bad execution). `fresh_context: true`, `independent: true`, context `/root/ypxw_delivery_qa`: this context has only performed delivery review and finding follow-up, not readiness, implementation or repair.

Final limitation: after-retrieval benchmark is still pending in the coordinator's quiet window. This QA approval is for source/test scope and the current full-suite receipt; it must not be cited as a completed retrieval comparison or a causal quality claim. No additional source writes are needed or authorized by this report.
