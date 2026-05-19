# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-19

wave-id: `12pn3 search-retrieval-quality`
Title: Search Retrieval Quality

## Objective

Improve semantic search retrieval quality across docs and code by upgrading the code embedding model, adding hybrid FTS+dense retrieval, enriching chunk context at embed time, and upgrading the reranker. Includes an evaluation path for a smaller docs model (nomic-embed-text-v1.5-Q) that requires instruction-prefix infrastructure.

## Changes

Change ID: `12pn3-enh code-embedding-model-jina-v2`
Change Status: `deferred`

Change ID: `12pn3-enh hybrid-fts-retrieval`
Change Status: `implemented`

Change ID: `12pn3-enh chunk-context-enrichment`
Change Status: `deferred`

Change ID: `12pn3-enh reranker-upgrade`
Change Status: `implemented`

Change ID: `12pn3-enh nomic-embed-docs-model-evaluation`
Change Status: `deferred`

Change ID: `12pnm-enh dashboard-doc-viewer`
Change Status: `implemented`

Change ID: `12pr7-enh streaming-embed-write`
Change Status: `implemented`

Change ID: `12q5v-enh code-ask-explanatory-doc-demotion`
Change Status: `implemented`

Change ID: `12q63-enh code-ask-symbol-first-injection`
Change Status: `implemented`

Change ID: `12q8t-enh cia-spec-top-citation-hardening`
Change Status: `implemented`

Change ID: `12qf3-enh tree-sitter-swift-objc-and-regex-replacements`
Change Status: `implemented`

Completed At: 2026-05-18

## Wave Summary

Delivered retrieval and agent-hardening work across eight implemented changes: hybrid FTS+dense fusion with RRF on every query (`12pn3-enh hybrid-fts-retrieval`), reranker upgrade (`12pn3-enh reranker-upgrade`), streaming embed writes (`12pr7-enh`), `code_ask` explanatory demotion and symbol-first two-hop injection (`12q5v`, `12q63`), Guru rename plus `validation_required` / dynamic `next_tools` (`12q8t`), dashboard doc viewer (`12pnm`), and broad tree-sitter chunking for Swift/ObjC plus config/markup languages (`12qf3`, `CHUNKER_VERSION` `"21"`). Three changes remain **deferred** with recorded rationale: jina code embeddings, embed-time context prefixes, and nomic docs evaluation — `indexer.py` still uses `BAAI/bge-small-en-v1.5` for both tables at delivery review time.

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required for all code changes in this wave — open before editing `.wavefoundry/framework/scripts/` and close immediately after.
- **Watchpoint:** Changes 1, 3, and 5 each require a full `--full` index rebuild after landing — coordinate sequence to avoid redundant rebuilds. Preferred order: 3 (context enrichment) → 1 (jina-code) → 5 (nomic) if all three land in the same session.
- **Blocking:** Changes 1 and 5 both modify `DOCS_MODEL`/`CODE_MODEL` constants in `indexer.py` — do not implement concurrently; serialize and rebase before the second constant is set.
- **Watchpoint:** Hybrid FTS (change 2) requires LanceDB Tantivy support — verify `lancedb` version at implementation time; wrap FTS index creation in try/except with graceful dense-only degradation.
- **Watchpoint:** `12qf3` bumps `CHUNKER_VERSION` — requires full index rebuild after implementation; coordinate with other rebuild-triggering changes in this wave to avoid redundant full builds.

## Review Checkpoints

### Delivery review scope (2026-05-19)

Reviewed all **implemented** changes (8/11). Deferred changes (`12pn3-enh code-embedding-model-jina-v2`, `12pn3-enh chunk-context-enrichment`, `12pn3-enh nomic-embed-docs-model-evaluation`) were not re-litigated; each change doc records deferral rationale and does not block delivery signoff for shipped work.

**Verification:** `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_chunker.py' -p 'test_server_tools.py' -p 'test_indexer.py'` — **63 tests OK**. Full suite: **1357 run, 1 environmental error** (`test_dashboard_server.IndexBuilderTests.test_single_build_gate_sets_pending_flag` — temp index dir cleanup race; not attributed to wave code). `wave_validate` — docs-lint OK.

### Specialist lanes

| Lane | Verdict | Summary |
|------|---------|---------|
| `code-reviewer` | **approved** | Framework changes follow existing indexer/server/chunker patterns. Tree-sitter additions use shared `_ts_generic_structured_chunker` / `_ts_flat_emit_chunker` / `_ts_dispatch` with regex fallbacks. `code_ask` hardening is covered by `test_server_tools` (validation_required, next_tools, partition). No project-specific guidance added to generic seeds beyond intentional Guru/auto-Guru surfaces. |
| `qa-reviewer` | **approved** | Required ACs for implemented change docs have test or documented verification in Progress Log. `12qf3` AC-1–AC-14 addressed in implementation; operators must run **full reindex** after `CHUNKER_VERSION` 21 (AC-8) — recorded as post-deploy operator step, not automated in CI. Deferred changes have explicit `deferred` status and decision log entries. |
| `architecture-reviewer` | **approved** | Boundaries preserved: chunking in `chunker.py`, embed/index in `indexer.py`, retrieval in `server.py`, UI in dashboard. `docs/architecture/chunking-and-indexing-pipeline.md` updated to match `CHUNKER_VERSION` 21 and tree-sitter coverage. Wave summary was stale (corrected in this review). |
| `performance-reviewer` | **approved (advisory)** | Hybrid FTS adds index build cost and per-query FTS path but avoids full-scan lexical fallback when index present. `12qf3` adds optional grammar wheels and per-file tree walks — acceptable with fallbacks; cold `setup_index.py` install surface grows. Recommend monitoring first full reindex duration on large repos. |
| `security-reviewer` | **approved** | No new network calls or trust-boundary expansion. Tree-sitter parses local repo content only (same trust model as regex chunkers). `.tfvars`/`.env` still use `chunk_secrets_file` (redacted values). MCP `code_ask` reads citation paths under configured root; `validation_required` increases agent follow-through, not operator privilege. |
| `docs-contract-reviewer` | **approved** | Architecture pipeline doc aligned with implementation. Embedding table in arch doc notes current `bge-small` in `indexer.py` vs deferred jina/nomic changes — intentional drift called out. |

### Wave Council — delivery (2026-05-19)

**Seat roster (fixed):** `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, `red-team`  
**Rotating seat:** `performance-reviewer` (indexing, search hot path, chunker expansion)

| Seat | Delivery finding |
|------|------------------|
| `architecture-reviewer` | Shipped retrieval stack is coherent: chunk → embed → Lance (dense+FTS) → RRF → rerank → `code_ask` partition. Deferred embedding changes should not block closing delivered retrieval features. |
| `security-reviewer` | No blocking issues. Optional grammars do not execute untrusted code. |
| `qa-reviewer` | Test coverage adequate for shipped paths; operator full reindex required after chunker 21. |
| `reality-checker` | **Assumption:** operators run full reindex after deploy — **unverified** until operator confirms. **Assumption:** all grammar wheels installed in production venv — **partial** (optional at runtime). Deferred jina/nomic means original wave objective is only partially met — **accepted** via explicit deferrals. |
| `red-team` | **No ship-stopper.** Risks to track: (1) machines without new grammars get weaker chunks than dev with full install — mitigated by regex fallback but retrieval quality varies by environment; (2) `CHUNKER_VERSION` 21 without reindex leaves stale chunk boundaries in index — **operator action required**; (3) wave.md change-status drift was misleading for review — **fixed in this pass**; (4) Guru `validation_required` reduces spec-only answers but does not guarantee agents call `code_outline` — behavioral, not enforceable in server alone. |
| `performance-reviewer` | Acceptable; first reindex after grammar expansion may be slow. |

**Material disagreements:** None blocking. `reality-checker`/`red-team` stressed environment-dependent chunk quality vs `qa-reviewer` “approved with operator reindex” — **resolved:** document reindex and `setup_index.py` grammar install in closure checklist; council does not require jina/nomic for delivery approval.

**Council moderator synthesis:** Delivery of the eight implemented changes is **approved** for merge/operator use. Wave is **not ready to close** until: deferred changes remain explicitly deferred (done), `operator-signoff` recorded when operator intends close, and operator confirms full reindex post-`CHUNKER_VERSION` 21 (or records waiver in handoff).

### Close readiness (operator)

- [ ] Run full index rebuild after deploying chunker 21 / retrieval changes
- [ ] Confirm `setup_index.py` installed new tree-sitter grammar wheels in the MCP Python environment
- [ ] Record `operator-signoff: approved` in the Review Evidence section when ready to **Close wave**
- [ ] Decide follow-up wave for deferred: jina code model, context prefixes, nomic eval

## Review Evidence

- operator-signoff: approved 2026-05-18
- wave-council-readiness: approved — retrieval quality improvements are well-scoped, each change is independently deployable, risk mitigations documented in change docs. 2026-05-17.
- wave-council-delivery: approved 2026-05-19 (eight implemented changes; seats architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, red-team; rotating performance-reviewer; no blockers; operator full reindex required before close)
- code-reviewer: approved 2026-05-19
- qa-reviewer: approved 2026-05-19
- architecture-reviewer: approved 2026-05-19
- performance-reviewer: approved 2026-05-19 (advisory)
- security-reviewer: approved 2026-05-19
- docs-contract-reviewer: approved 2026-05-19

## Dependencies

- No external wave dependencies.
