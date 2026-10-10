# Rust graph code and QA repair reverification

Owner: Engineering
Status: active
Last verified: 2026-10-08

Fresh independent context: `206og-fresh-code-qa-reverification-1`; acting lanes code-reviewer and qa-reviewer. This reviewer did not implement the repair, retained no implementation context, and independently formed its verdict from the current contract, source and executed probes. Current capable model was selected for correctness verification; actual runtime model and effort identity are unknown. Six-minute initial evidence budget; targeted tests per mutant, whole-file expansion only for survivors. No mutant survived. No frozen source edits were made.

**Verdict: code and QA delivery approved.** Typed cycle-1 lane reverifications were previewed and recorded separately for code and QA for `rust-let-initializer-shadow` and `rust-qualified-impl-call`. After the performance lane independently cleared its finding, code delivery approval was previewed and recorded. The final quiet canonical suite is green. This reviewer independently read the final unchanged Requirements/design/AC packet, refreshed code and QA readiness approvals for receipt `review-policy-94cbcc94f64098765959`, and then previewed and recorded final QA delivery approval. No operator approval, closure, commit or push is supplied.

## Independent reference and production path

The reference is Rust lexical binding visibility and explicit module/type/trait identity, independently read against change 206of's Requirements, Readiness Design Contract and required ACs. Both original four-line counterexamples were freshly accepted by `rustc --crate-type lib --emit metadata` with exit 0. They build scratch repositories through `_RepoDriver`, canonical extraction and SQLite publication, `begin_build_epoch`/`finalize_build_epoch`, and consume real `code_callgraph_response` results. Assertions identify exact targets using original UTF-8 source offsets; they are not edge-count proxies.

- `python3 -B /tmp/wf-206og-independent-code-qa.py`: exit 0. Initializer occurrence `[118,125)` targets `types.rs::P.hit`; following `[127,134)` targets `types.rs::R.hit`, both `RECEIVER_RESOLVED`.
- `python3 -B /tmp/wf-206og-qualified-probe.py`: exit 0. Calls `[167,178)` and `[180,191)` target `types.rs::a.<P as T>.hit` and `types.rs::b.<P as T>.hit`, respectively, both `RECEIVER_RESOLVED`.
- `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_graph_call_integrity.py -v`: 50 tests pass, zero failures/errors/skips, 5.981s.
- `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_graph_rust_provenance.py -v`: nine tests pass, zero failures/errors/skips, 2.026s.

MCP-first source examination confirms let visibility uses declaration end, lexical scope/name positions are sorted and searched with binary search, and explicit scoped receivers use the same normalized alias representation as candidate indexing. Unique-candidate checks and unknown shadows remain intact. The adjacent initializer-loop test preserves the outer array type during the initializer; explicit-module ambiguity controls remain unresolved. Declaration lookup complexity is independently reviewed in the performance lane; these code/QA results do not substitute for its measured verdict.

## Required AC coverage

| Required AC | Independently executed evidence |
| --- | --- |
| AC-1 | Public publication test asserts original macro and UTF-8 spans, unrelated same-name receivers and neighboring callers; integrity macro/same-line tests pass. |
| AC-2 | Repeated occurrences, missing-provenance omission, incremental replacement versus fresh graph and response immutability all pass through public storage/query fixtures. Repeat-loss mutant is detected by exact occurrence assertions. |
| AC-3 | Distinct same-trait types, two traits on one type, cross-file candidates, explicit module receivers, generic refusal and ambiguous aliases pass. Original module counterexample now retains both genuine project targets. |
| AC-4 | Typed local/associated-array loops, lexical unknown shadow, later/sibling declarations and own-initializer controls pass. Original valid initializer counterexample independently observes previous-binding P then new-binding R. |
| AC-5 | Unknown/known witnesses remain separate; unknown receiver and same-/cross-file collect controls, established language controls and unsupported generic cases pass. Exact identity and span oracles are separate from relationship counts. |
| AC-6 | Previous-builder per-file cache retirement, fresh/incremental parity, failed-rebuild refusal, pinned generations, occurrence-only edit and non-Rust confidence/topology preservation pass. Final quiet canonical run passes 11,915 tests across 175 files. |

All six rows are required. There are no intentionally unmet `[~]` rows, optional priority omissions or new scope deferrals in the admitted contract. Checked tasks are not evidence; the outstanding documentation/review task remains coordinator-owned until all delivery lanes qualify.

## Mutation and integrity table

| Runtime mutation, scratch process only | Targeted independent oracle | Observed |
| --- | --- | --- |
| Premature binding visibility: `_RustLexicalFacts.visible_at` returns declaration start | Original public initializer fixture requires exact initializer target P.hit | Exit 1, `AssertionError`; no setup error or skip; killed. |
| Raw module receiver: scoped a/b receivers restored to external qualified names | Original public qualified fixture requires exact a/b trait-qualified project target set | Exit 1, `AssertionError`; no setup error or skip; killed. |
| Discard repeated sites after `_merge_call_evidence` | `test_exact_receiver_spans_survive_extraction_storage_and_public_projection` requires complete exact source occurrences | One assertion failure, zero errors/skips; killed. |

All five integrity facts are affirmed for the executed focused evidence: tests actually ran without unintended skips, real public paths were reached, compiler-accepted boundary inputs were realistic, assertions are non-vacuous, and focused restored-bad mutations were detected. Scratch mutation scripts patch production functions in memory; repository bytes remain unchanged. The compiler is an independent validity reference, not a graph implementation oracle; target/span expectations derive from source syntax and the explicit consumer contract.

## Frozen tree and limits

All 13 `git hash-object` values match `/tmp/wf-206og-repair-frozen.json` and the durable `evidence/repair-1-tree.json` boundary on initial and final focused-review readback. The report and typed event projection are outside that frozen source boundary.

No live Tensorwell checkout, native-platform qualification, general Rust type checker, arbitrary macro expansion or exhaustive recall claim is made. The first repaired-tree canonical run completed 11,915 tests across 175 files in 388.716s with 29 skips and one failure in `test_docs_constants_lint.py`: its early `test_live_repo_is_clean` observed the malformed Wave header in the architecture delivery report. The coordinator corrected that metadata. The runner also detected authorized concurrent report/event/wave edits, so that run supplied no fresh green receipt.

The final quiet canonical run, `/tmp/wf-206og-canonical-final.log`, completes 11,915 tests across 175 files in 417.943s with `OK` and 29 reported skips. No baseline-guard failure appears in that run. This reviewer independently read the final log and verified the fresh `test-cache.json` receipt has `result=ok`, test count 11,915, and input hash `c89058fb3175e15d7ac1ce5daf8daedbcfb53c362c0320115d674e10a64b726a`, equal to `_hash_inputs()` for the current framework tree. All 13 frozen hashes still match. The 59 focused AC tests have zero skips; full-suite platform/optional skips are disclosed and do not replace their boundary evidence. Final guided review reports clean docs lint. The changed handoff digest was reconciled by re-Prepare and current-packet readiness review, enabling the final typed QA approval; post-approval guidance lists operator signoff only.
