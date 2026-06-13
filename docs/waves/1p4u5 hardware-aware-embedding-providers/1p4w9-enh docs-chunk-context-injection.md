# Docs-chunk section-breadcrumb context injection

Change ID: `1p4w9-enh docs-chunk-context-injection`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-11
Wave: `1p4u5 hardware-aware-embedding-providers`

## Rationale

Docs-chunk embeddings omitted heading/topic context. The chunker emitted most docs chunks
with `text` = the raw body and the `section` breadcrumb (`stem > qname` / `H1 > heading` /
bare `## heading`) only in metadata. A documentation chunk body frequently does not restate its
heading, so a natural-language query matching the heading topic could not reach the chunk by
cosine similarity.

An empirical A/B on **2026-06-11** measured this: full 22,306-chunk corpus, the repo's own
32-query `benchmarks/retrieval_eval.json`, top-3 cosine, the live bge-small model. Prepending the
`section` breadcrumb to each chunk's embedded text moved **docs top-3 retrieval 60.0% → 70.0%
(+10pp)** with no overall regression. The same injection **regresses CODE** (0/8 deep-rank code
queries rescued, several worse) because code bodies already contain the symbol name on the
`def`/`func` line — so the injection is **docs-kind only**. See
[[project_code_retrieval_quality_levers]] for the diagnostic (a four-model A/B and a code-embedder
review confirmed the embedder is not the lever for code retrieval; chunking/context is).

This is implemented as a **chunking change** (not an embedding-model change): the breadcrumb is
folded into the docs chunk `text` itself, so the chunk's `chunk_hash` changes and the existing
`CHUNKER_VERSION` re-chunk path re-embeds the changed docs chunks while reusing unchanged code
vectors by content hash — no model-version trigger or new metadata field. Related broader idea:
`12pn3-enh chunk-context-enrichment` (this is the narrow, validated docs slice).

## Requirements

1. Docs-kind chunks (`doc`, `doc-summary`, `seed`, `prompt`) prepend their non-empty `section`
   breadcrumb to `text`, idempotently (skip when `text` already opens with the breadcrumb, e.g.
   markdown H1-breadcrumb chunks and docstring chunks that build `text` from the breadcrumb).
2. Code-kind chunks are unchanged (the injection regresses code retrieval).
3. The injection runs before the universal oversized-chunk guard so no chunk exceeds
   `MAX_CHUNK_CHARS`.
4. `CHUNKER_VERSION` is bumped so existing indexes re-chunk; docs chunks (changed `text`/hash)
   re-embed and code chunks (unchanged) reuse vectors by content hash.

## Scope

**Problem statement:** Docs-chunk embeddings omitted the section/heading context held in metadata,
capping NL-to-docs retrieval; a validated fix exists but must be docs-gated.

**In scope:**

- `chunker.py`: a `_inject_docs_breadcrumb` post-pass in `chunk_file`, applied before
  `split_large_chunks`.
- `CHUNKER_VERSION` bump (29 → 30).

**Out of scope:**

- Code chunks (injection regresses code retrieval — body-only retained). [[project_code_retrieval_quality_levers]]
- Embedding-model swap, reranker, or hybrid-lexical changes (separate, larger levers).
- Indexer embed-step changes / a new embed-input metadata version (the chunker approach makes the
  existing `chunk_hash` + `CHUNKER_VERSION` machinery handle re-embed — see Decision Log).

## Acceptance Criteria

- [x] AC-1: Docs-kind chunks prepend the section breadcrumb to `text` when section is non-empty.
  Verified by `DocsBreadcrumbInjectionTests.test_doc_chunk_gets_section_breadcrumb` /
  `test_seed_and_prompt_chunks_also_injected` / `test_chunk_file_injects_for_no_h1_markdown_doc`.
- [x] AC-2: Code-kind chunks are unchanged. Verified by `test_code_chunk_unchanged`.
- [x] AC-3: Injection is idempotent (no double-prefix) and a no-op for empty/None section.
  Verified by `test_idempotent_when_text_already_starts_with_breadcrumb` /
  `test_empty_or_none_section_no_change`.
- [x] AC-4: No chunk exceeds `MAX_CHUNK_CHARS` (injection precedes the guard). Verified by the
  existing `UniversalOversizedChunkGuardTests` (green after the reorder).
- [x] AC-5: `CHUNKER_VERSION` bumped to `30`; the re-chunk path re-embeds changed docs chunks and
  reuses code vectors by content hash (`_chunk_hash` includes `text`/`section`). Verified by
  `test_chunker_version_bumped_to_30` + the existing chunker-version re-chunk tests in
  `test_indexer.py`.
- [x] AC-6: Full framework suite green (`run_tests.py` — 3145 tests).

## Tasks

- [x] Add `_inject_docs_breadcrumb` + apply it in `chunk_file` before `split_large_chunks`.
- [x] Bump `CHUNKER_VERSION` 29 → 30 with a history note.
- [x] Add `DocsBreadcrumbInjectionTests` (6 tests) and update the version-assertion test.
- [x] Run the full suite.
- [~] Re-validate the docs delta against `retrieval_eval.json` after a real re-index (intentionally
  deferred to a rebuild — the +10pp was measured pre-merge with the identical section-prepend
  transform; a live re-index re-confirms it but is operator-owned and not a close blocker).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| chunker injection | implementer | — | `_inject_docs_breadcrumb` in `chunk_file` |
| version bump | implementer | chunker injection | `CHUNKER_VERSION` 29 → 30 |
| tests | qa-reviewer | chunker injection | `DocsBreadcrumbInjectionTests` |

## Serialization Points

- `chunk_file` finalization order (`_inject_docs_breadcrumb` must precede `split_large_chunks`).
- `CHUNKER_VERSION` (shared re-chunk trigger for both layers).

## Affected Architecture Docs

`docs/architecture/embedding-model.md` — note that docs chunks embed the section breadcrumb +
body. No layering/flow/boundary change; no new ADR (narrow, single-module chunker change with an
empirical basis). [Deferred to wave close docs pass.]

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The core behavior. |
| AC-2 | required | Guards the validated code-regression boundary. |
| AC-3 | required | Prevents double-prefix / no-op correctness. |
| AC-4 | required | Embedder token-cap contract. |
| AC-5 | required | Without the bump, upgraded indexes keep stale docs vectors. |
| AC-6 | required | No suite regressions. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | Validated the docs gain. | A/B on full 22,306-chunk corpus + `retrieval_eval.json`, bge-small: section-prepend docs top-3 60.0% → 70.0% (+10pp); code 41.2% unchanged (0/8 deep-rank rescued, some worse) → docs-gated. |
| 2026-06-11 | IMPLEMENTED as a chunking change. `_inject_docs_breadcrumb` in `chunk_file` (before `split_large_chunks`); `CHUNKER_VERSION` 29 → 30; 6 new tests + version test updated. Full suite **3145 green**. | `chunker.py` `_inject_docs_breadcrumb` / `chunk_file` / `CHUNKER_VERSION`; `tests/test_chunker.py` `DocsBreadcrumbInjectionTests`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-11 | Implement as a CHUNKER change (breadcrumb in chunk `text` + `CHUNKER_VERSION` bump), not an indexer embed-step change. | The chunk `text`/`chunk_hash` changing makes the existing re-chunk + content-hash reuse path re-embed docs and reuse code automatically — no model-version trigger or new meta field, and the stored/displayed chunk text stays consistent with what was embedded. | Indexer embed-input gating + a new `embed_input_versions` meta trigger (rejected: more core-rebuild-logic blast radius; vectors would diverge from stored text). |
| 2026-06-11 | Gate injection to docs-kind chunks only. | Measured regression on code (redundant symbol name; deep-rank queries worsened). | Inject for all chunks (rejected: hurts code). |
| 2026-06-11 | Inject before `split_large_chunks`. | The prefix can push a chunk over `MAX_CHUNK_CHARS`; running the guard after re-caps. | Inject after split (rejected: violated the oversized-chunk guard — 3 tests). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Split docs chunks: only part-1 carries the breadcrumb (injected pre-split). | Acceptable — most docs chunks are under the cap and unsplit; part-1 holds the highest-signal opening. |
| Token-budget pressure from longer docs inputs. | Breadcrumbs are short; the guard caps total length; the front-loaded breadcrumb survives any tail truncation. |
| Overlap with `12pn3-enh chunk-context-enrichment`. | Referenced; this is the narrow validated docs slice — reconcile at that plan's admission. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
