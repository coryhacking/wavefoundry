# Memory maintenance — 2026-09-17

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Disposition

Operator requested memory review after closing wave `1yad2 memory-retrieval-quality`. No pending candidates existed. Reviewed the three exact same-kind/target consolidation groups; combined only the two release-packaging review findings. The review-authority decisions and chunker failure lessons address different mechanisms and remain separate. The active budget is a curation signal, not a deletion quota.

Replacement: `1y7ig-mem verify-package-contents-through-the-real-release-and-injecti`. It preserves both real-release artifact cardinality and real injected-build retired-member checks, confirmed in current `test_build_pack.py` at the `build_pack.main()` call and `InstallTemplateInjectionTests.test_install_log_template_ships_in_framework_tree`. Both source bodies remain archived because they carry the replacement's detailed evidence trail.

Removed 54 rejected and 32 superseded live generated drafts individually through the guarded public purge handler. These were non-actionable completion recaps, incorrect scratch/fixture targets, duplicate lessons, or drafts already replaced by active records. Reviewed their disposition rationales, replacement summaries and retained source wave evidence; checked protected kinds against current replacement knowledge, target existence and relevant contracts. All 86 source-event hashes are preserved in `.wavefoundry/memory-purge-dispositions.json`, preventing regeneration. Original wave decision logs and typed review ledgers remain. No active knowledge was deleted to reach the cap.

The attached MCP's consolidation write refused `memory_state_unwritable` without changing records. A fresh process using the same unmodified public handler and normal publication/memory fences succeeded. No lock or database state was manually overridden. Live/history MCP searches verified the replacement and archives afterward.

## Before and after

| Measure | Before | After |
| --- | ---: | ---: |
| Active | 119 | 118 |
| Candidate | 0 | 0 |
| Rejected live bodies | 54 | 0 |
| Superseded live bodies | 32 | 0 |
| Stale live bodies | 0 | 0 |
| Active budget | 50 | 50 |
| Lint-valid live-body UTF-8 bytes | 360,902 | 227,069 |
| Archive body files | 13 | 15 |
| Archive body UTF-8 bytes | 33,572 | 37,909 |
| Archive register UTF-8 bytes | 6,158 | 7,119 |

Estimated removed live-context tokens: **33,459**, calculated as `ceil((360902 - 227069) / 4)`. This is a text-size estimate, not measured prompt savings. Archive and register bytes are reported separately. Existing thirteen archives retain specific historical mechanisms; no archive was deleted. No candidate judgment remains pending. The corpus remains 68 active records over budget; further reductions would require meaningful cross-topic curation rather than merging unlike memories.

## Verification

All live and archive bodies parsed successfully. Normal and historical MCP memory searches passed. Source-event disposition hashes verified 86/86. Docs validation passed. The attached MCP writer and health reader refused `index_runtime_stale`; `wf update-indexes --docs-only` separately refused the configured background-layer combination before indexing. The current documented `indexer.py --root . --content docs` entrypoint then completed successfully in a fresh process with normal guards. Fresh public build status confirmed lock not held, a clean ended_at, complete epoch generation 1543 and interrupted=false.

Fresh public health reported ready, semantic_ready=true, schema 8 and integrity=ok; docs 29,384 and code 12,528 rows each matched registry/canonical/raw counts with zero missing/orphan vectors, and both FTS digests were OK. The same fresh public `wf_memory_eval_response` completed with available=true, no diagnostics and 12 sampled records. Its legacy-policy baseline and semantic-only Recall/MRR were 1.0; the separate diagnostic policy-ordered-RRF candidate and lexical-only were Recall 0.25/MRR 0.3621. That diagnostic candidate is not the delivered summary5 production design. `qualifying=false` and `independent_full_corpus_holdout_required` remain explicit: self-summary metrics do not authorize adoption or replace the wave's frozen independent qualification.

The attached MCP host still needs a full restart; implementation reload did not replace its captured writer. The closed wave's frozen evaluation remains historical evidence for that exact corpus, not a new measurement of this curated corpus. Final report/handoff edits receive a final docs gate and incremental refresh; reported counts above describe the completed maintenance snapshot.
