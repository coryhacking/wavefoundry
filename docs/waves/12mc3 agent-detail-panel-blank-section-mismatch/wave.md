# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-14

wave-id: `12mc3 agent-detail-panel-blank-section-mismatch`
Title: Agent Detail Panel Blank Section Mismatch

## Changes


Change ID: `12mc3-bug agent-bootstrap-seed-missing-canonical-heading-names`
Change Status: `complete`
Previous Change Status: `planned`

Change ID: `12mc6-enh agent-dialog-full-doc-markdown-render`
Change Status: `complete`
Previous Change Status: `planned`

Change ID: `12mcr-bug persona-scope-section-wave-anchor-antipattern`
Change Status: `complete`
Previous Change Status: `planned`

Change ID: `12mh2-enh wave-reopen-supports-paused-waves`
Change Status: `complete`
Previous Change Status: `planned`

Change ID: `12mh7-enh jupyter-notebook-chunking`
Change Status: `complete`
Previous Change Status: `planned`

Change ID: `12mha-enh semantic-search-reranker`
Change Status: `complete`
Previous Change Status: `planned`

Change ID: `12mhv-enh server-startup-model-download`
Change Status: `complete`
Previous Change Status: `planned`

## Objective

Replace the brittle `_DETAIL_SECTIONS` allowlist with full-doc markdown rendering in the agent dialog, eliminating cross-project heading drift permanently. Companion seed updates codify canonical heading names and authoring best practices. Extended scope adds Jupyter notebook chunking, combined cross-index semantic search with cross-encoder reranking, and server-startup background model download.

Completed At: 2026-05-14

## Wave Summary

Seven changes across two implementation phases. **Phase 1 (complete):** (1) full-doc markdown rendering in agent dialog with `renderMarkdownish` extended to handle `##`, `**bold**`, `` `code` ``; (2) seed-050/seed-006 canonical heading and authoring updates; (3) persona lint relaxation removing `## Scope` + wave-id anchor requirement; (4) `wave_reopen` extended to accept paused waves. **Phase 2 (complete):** (5) Jupyter notebook chunking — cell-typed chunks from `.ipynb` files; (6) combined docs+code retrieval with cross-encoder reranker (`BAAI/bge-reranker-base`), RRF fallback, `top_n` default raised to 7; (7) server-startup background model download for all three models with `HF_HUB_OFFLINE` opt-out and dead-field cleanup via code-reviewer lane.

## Journal Watchpoints

- **Watchpoint:** seed edits (seed-050, seed-006, seed-120, seed-005) require `seed_edit_allowed` gate — open before editing, close immediately after.
- **Watchpoint:** `framework_edit_allowed` gate required for all Phase 2 files: `chunker.py`, `indexer.py`, `server.py`, `setup_index.py`, `test_chunker.py`, `test_server_tools.py`, and Phase 1 files `dashboard_lib.py`, `dashboard.js`, `constants.py`, `wave_validators.py`.
- **Sequencing (Phase 1):** implement the dashboard render change (12mc6-enh) before the seed updates (12mc3-bug). Persona lint fix (12mcr-bug) is independent.
- **Sequencing (Phase 2):** `12mha-enh` must land before `12mhv-enh` (startup download depends on `_get_reranker()` and `RERANKER_MODEL`). `12mh7-enh` is independent of both.

## Review Evidence

- wave-council-readiness: approved (2026-05-14 — Phase 1 core approach approved; 2026-05-14 Phase 2 readiness review complete for 12mh7, 12mha, 12mhv — 3 blocking findings resolved: raw cell type scoped, search_combined default wording fixed, HF_HUB_OFFLINE suppression added)
- wave-council-delivery: approved (2026-05-14 — Phase 1 complete: all 4 changes done; 1172 tests pass; docs-lint clean; 2026-05-14 Phase 2 delivery approved: all 3 changes complete; 1213 tests pass; all ACs verified; dead fields _docs_embedder/_code_embedder removed by code-reviewer lane)
- operator-signoff: approved (2026-05-14 — operator confirmed closure)

## Dependencies

- No external wave dependencies.
