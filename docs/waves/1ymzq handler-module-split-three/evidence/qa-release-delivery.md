# Independent QA and release review — 1ymzq

Owner: Engineering
Status: active
Last verified: 2026-09-22

Reviewer context: `/root/split3_qa_delivery`, fresh independent of implementation. QA and release are two correlated perspectives of one worker, not two independent reviewers. No repository source or documentation edits performed. Initial packet SHA256 `2a027a2cda7ae16a2c3433eeaa31408c5d97684f7874cbfc5d3687163e63d51f`; renewed packet `/private/tmp/1ymzq-delivery-fingerprint-v2.json`, SHA256 `7d69750f1514d43c92f20b5b68749688b2776ccb5862b5bacd4c66d249808577`. Twelve-minute bounded sweep; targeted tests per mutant, whole-file only for survivor.

## Verdict and readiness

QA: implementation evidence satisfactory on frozen code, final delivery approval WITHHELD solely pending required R2 and its final pointer reconciliation (index AC-5). Release: approve code's packaging/reload/old-install compatibility boundaries; this is not a published-package certification. No new implementation blocker found.

Readiness judgment: APPROVE the current plan clarifications for receipt `review-policy-94b63f24a5c63152fa15`. The actual classified sets, documented call-time seams, named optimize mock-owner repoints, pure already-resolved containment boundary and R0/R1/R2 sequence describe existing implemented behavior; no additional behavior is requested by those clarifications. R2 is explicitly a new baseline, not comparative evidence across the membership change. Required R2 completion remains a delivery condition, not a reason to invent another implementation change.

Initial `tree_moved_under_review`: six docs paths changed after v1. Coordinator disclosed Prepare gardening; renewed v2 matches every packet path. Reread all six current documents and checked load-bearing handler ownership, containment, reload and baseline claims against implementation. Old git hash-object blobs were not stored, so a mechanical metadata-only v1/v2 delta cannot be reconstructed; that claim is coordinator provenance, not independently proven. Code/tests never changed. Current reread supersedes v1 docs evidence.

## Independent references and executed evidence

References: independently read all five change requirements and ACs; registered tool golden fixture; actual pre-extract old-install contract; Path exception and resolution-count contracts; source-guard lock exclusion invariant. MCP `code_ask` followed by `code_outline`/`code_read` for implementation validation. Shell AST/source inspection supplemented MCP for exact test selection and executable fault injection; source-generated inventories were not accepted as sole proof.

Canonical focused command: `python3 -B .wavefoundry/framework/scripts/run_tests.py --file test_handler_modules.py --file test_path_containment.py --file test_index_handler_identity.py --file test_tool_surface_golden.py --file test_index_source_guard.py --file test_lifecycle_gates_structure.py --file test_upgrade_wavefoundry.py`.

Observed: 598 tests / seven isolated files passed in 30.093s, one intended native-Windows junction cleanup skip. This diagnostic run leaves the full-suite receipt untouched. Reload/containment/identity/golden/source-guard tests had zero skips. Upgrade's one platform skip is not evidence for native Windows qualification.

Full receipt independently parsed and hash recomputed twice with canonical `_hash_inputs`: `23beca55d485bce9f4ed5e7097dac6df7e9bbbc6b374f8e6334c8380daae317e`, result ok, test_count 9508, 121 timing entries; `_cache_hit(current_hash)` true. Did not rerun the entire suite. The receipt proves current framework inputs, not all repository documentation.

## AC coverage

| Change | Required AC evidence |
|---|---|
| CE 1ymzl AC1–3 | Full roster AST and same-object re-export assertions; golden registration; generated manifest; scratch reload invokes registered wf_context_efficiency_eval with required arguments. |
| CE AC4–5 | Unchanged source-guard suite exercises real monitor, build-first and writer-first contention, unknown acquisition and retry, publication contention release; current full receipt covers other named existing suites. |
| Thin wrappers 1ymzn AC1–3 | Full three-module partitions, retained root ownership, object identities, golden public signatures; transport-free docs sync/secrets calls assert subprocess reached and output parsed; each registered reload executes modified scratch response. |
| Thin wrappers AC4–5 | Mock-owner repoints preserve expectations, retained root seams stay patched; current full receipt covers dashboard/lifecycle suites. Wrapper exclusion from measured closure supported by inventory and ownership boundaries. |
| Upgrade 1ymzo AC1–3 | Classified identities, golden surface, manifest and registered reload. |
| Upgrade AC4–6 | 531 upgrade tests pass; real extension helper is exercised under injected unavailable module and both installed modern/legacy stop shapes, asserting actual selected call. Reload census and memory source pin retained. Current full receipt covers remaining named suites. |
| Index 1ymzm AC1–4,6 | Complete owner/identity roster, golden surface, reload plus unchanged lifecycle structure/source guard tests; current full receipt covers named index suites. |
| Index AC5 | Module identity mutation test passes and catches omission. Baseline pointers explicitly pending. Final R2 absent at this review: UNVERIFIED until follow-up. |
| Containment 1ymzp AC1–5 | 23 tests exercise real filesystem symlinks/missing tails plus pure Windows paths, exact wrapper resolution-call counts/error classes and causes, retained per-site clauses, independent thirty-site census, stale allowlist and polarity controls; identity and scratch reload. Current full receipt covers adopter suites. |

No silent intentionally-unmet AC was accepted. Remaining final-review task checkboxes are honest pending state. Inventories and extracted counts were checked by structural tests; AST parity alone was not treated as behavioral evidence.

## Mutation table

All mutations are scratch copies or process-local mocks; repository source unchanged. Reproducer `/private/tmp/1ymzq-qa-probe.py`; results `/private/tmp/1ymzq-qa-mutations.json`.

| Mechanism | Focused known-bad mutation | Observed detector |
|---|---|---|
| CE reload | Remove CE handler purge membership | Scratch production reload fails `fresh is not old`; baseline reaches registered tool. |
| Index reload | Remove index handler purge membership | Same exact stale identity assertion fails. |
| Docs reload | Remove docs handler purge membership | Same stale identity assertion fails. |
| Dashboard reload | Remove dashboard handler purge membership | Same stale identity assertion fails. |
| Edit gate reload | Remove edit gate handler purge membership | Same stale identity assertion fails. |
| Upgrade reload | Remove upgrade handler purge membership | Same stale identity assertion fails. |
| Retrieval identity | Remove index_handlers.py from production membership | Independent copied-file test fails explicit membership assertion. |
| Pure containment | Re-resolve root/candidate in pure helper | Filesystem-forbidden oracle fails `AssertionError: resolve`. |
| Packaging | Drop index_handlers.py from collect_files output | Generated manifest membership assertion fails. Also actual production-tree collect_files includes all six new handlers and path_containment. |
| Old-install upgrade | Replace ImportError catch by ValueError | Both modern and legacy absent-module tests error at actual stop helper; baseline passes. |
| CE source-guard interlock | Replace guard acquisition with nullcontext | Targeted unknown-acquisition test SURVIVED (publication lock shares underlying RuntimeFileLock fault); expanded only survivor to seven-test file, producing three failures. Strongest: writer-first test reports `builder read while automatic write was held`; monitor busy-state and map defer also fail. `/private/tmp/1ymzq-ce-mutant.txt`. |

The targeted survivor is not a new bug or evidence that exclusion is untested: the adjacent explicit concurrency oracle catches it. Unknown-acquisition alone must not be cited as proof of source-guard acquisition. No surviving mutation remains after the prescribed expansion.

## Receipt audit

R0 raw report verdict baseline, no invalidation/operator review reasons, stable complete generation1892/attempt66c73ce6eefb4b6c8a2f3de33aec3936. Actual file SHA256 `78f48fb12f8a9e42d409b4e8e59a8c5e26e1c12d1f7a3e4eb2964d224615441e` exactly equals R1's baseline_file_sha256. R1 verdict pass, stable complete generation1899/attempt473a8756f6a64e309f543f1cbc6c2aca; 27 compared fixture/tool keys, zero violations. Both evaluator hashes `2db63339b76ad3d655bb3c311eb039a2429ca7880940f7dfd442ad4c8a49fd03`, fixture digests `b4b00b893e2e72e6a60062851592fba3a4d52ff0f2e0003aa0064ef4a29b0d57`. Retained unsuccessful attempts are correctly excluded as proof. R1 is cross-generation, so corpus effects remain a disclosed limitation; it does not compare final index extraction.

## Evidence integrity and limits

`fresh_context=true`; `independent=true` relative to implementation; `same_worker_qa_release=true`; `checks_executed=true`; `zero_unintended_skips=true`; `production_path_reached=true` for reload/extension/CE/wrapper boundaries; `fixture_state_reachable=true`; `assertions_nonvacuous=true`; `known_bad_detected=true`; `current_v2_fingerprint_matches=true`; `framework_receipt_current=true`; `R0_R1_verified=true`; `R2_verified=false`; `final_qa_approval=false`.

No external package publish/build, installed end-user upgrade, native Windows process qualification, or exhaustive filesystem races run. Release VERSION stamping logic unchanged and no VERSION diff; generated manifest and actual collect_files cover module distribution. Mocked subprocess boundaries verify selection and interpretation, not subprocess internals. Registered reload proves actual dispatch but uses a deliberate scratch sentinel response. Full receipt relies on canonical prior suite rather than this worker rerunning 9508 tests. R2 and rotating docs-contract perspective await coordinator follow-up.
