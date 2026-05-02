# Markdown Chunker Heading Hierarchy

Change ID: `12avx-enh markdown-chunker-heading-hierarchy`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-02
Wave: `12axj chunker-and-pack-improvements`

## Rationale

The current markdown chunker splits at `##` boundaries and discards the document-level context (`#` title, preamble) from each section chunk. A search result for "Extraction Philosophy" carries no signal that it belongs to "Design System Architecture" — the embedding for that chunk has no outer heading context. Additionally, oversized `##` sections (those with multiple `###` sub-headings and hundreds of lines of body) collapse into a single chunk, which swamps the embedding and reduces retrieval precision.

Two targeted fixes: (1) inject the H1 title as prefix context into every `##` section chunk so embeddings carry the full heading path; (2) threshold-gate `###` sub-section splitting so oversized sections are broken at semantically clean boundaries before falling back to the existing line-window splitter.

The context injection approach (fix 1) is directly validated by Anthropic's published "Contextual Retrieval" technique (2024), which demonstrated measurable retrieval precision improvements by prepending a short context description to each chunk before embedding. Injecting `{H1} > {## heading}` into chunk `text` is that technique applied to heading hierarchy.

## Requirements

1. Every `##` section chunk — both prose (`kind="doc"`) and extracted fenced code (`kind="code"`) — must include the document's H1 title as a context prefix in `text` (format: `{H1} > {## heading}\n\n{body}`). When no H1 is present, emit body unchanged.
2. The `section` field on `Chunk` must carry the full breadcrumb string (`"{H1} > {## heading}"`) rather than only the bare `##` heading. When no H1 is present, `section` is unchanged from today.
3. A `##` section whose body exceeds a configurable character threshold must be re-split at `###` sub-heading boundaries. Each resulting sub-chunk's `text` is prefixed `{H1} > {## heading} > {### heading}\n\n{sub-body}` and its `section` carries the full three-level breadcrumb. Both prose and fenced code sub-chunks receive the same breadcrumb.
4. The threshold must be a named module-level constant (`H3_SPLIT_THRESHOLD_CHARS`, default 2000) so it is tunable without hunting for a magic number.
5. When a `##` section exceeds the threshold but contains no `###` sub-headings, fall through to `chunk_line_window` — but still inject the breadcrumb into each fallback chunk's `text` prefix and `section` field, since the context is known at call time.
6. Fenced code blocks extracted from a `###` sub-section must carry the three-level breadcrumb in `section` and the same prefix in `text`.
7. Preamble content (before the first `##`) is unaffected by breadcrumb injection — it has no parent `##` heading to inherit.
8. Seed files (`kind="seed"`) must receive the same breadcrumb treatment as doc files.
9. **Chunk ID convention.** Sub-section chunk IDs must follow a stable, forward-compatible scheme so the indexer can align old and new chunks without ambiguity:
   - `##` section prose: `{path}#{h2-slug}` (unchanged from today)
   - `##` section fenced code: `{path}#{h2-slug}:code` (unchanged from today)
   - `###` sub-section prose: `{path}#{h2-slug}/{h3-slug}`
   - `###` sub-section fenced code: `{path}#{h2-slug}/{h3-slug}:code`
   - Line-window fallback within a section: `{path}#{h2-slug}:L{start}-L{end}`
   - The `/` separator between heading levels is chosen because it mirrors URL fragment hierarchy, is unused in the existing ID scheme, and leaves `::` and `:` unambiguous for future code chunk IDs.
10. **Index rebuild signal.** Add a `chunker_version` string constant to `chunker.py` (e.g. `CHUNKER_VERSION = "2"`, incremented on any change that alters chunk boundaries or content). The indexer's `meta.json` already tracks `model_versions` and forces a full rebuild when they change; add `chunker_version` to that same meta dict under the key `"chunker_version"` so a changed constant triggers an automatic full rebuild without manual intervention.
11. All existing `chunk_markdown` tests must remain green; new tests must cover breadcrumb injection on both prose and code chunks, `###` splitting, threshold boundary (at/just-above/just-below), no-H1 fallback, line-window breadcrumb injection, and new chunk ID shapes.

## Scope

**Problem statement:** Markdown chunks lack outer heading context, reducing embedding quality for sections whose meaning depends on document identity. Oversized sections without sub-heading splits produce low-precision embeddings.

**In scope:**

- `chunker.py` — H1 capture, breadcrumb injection into `section` and `text`, threshold-gated `###` splitting, line-window fallback for oversized sections without `###`
- `tests/test_chunker.py` — new test cases for all new behaviors; update any existing assertions that legitimately change

**Out of scope:**

- `####` and deeper headings — treated as prose body within a `###` sub-section; not split on
- Paragraph-boundary or list-boundary splitting for sections without `###` sub-headings that exceed the threshold — falls to existing line-window; follow-on if needed
- Changing `kind` values, chunk ID format, or `Chunk` dataclass fields beyond `section` and `text`
- Re-indexing or embedding pipeline changes — chunker output is consumed by the indexer unchanged

## Acceptance Criteria

- AC-1: A `##` section prose chunk for a file with an H1 has `text` starting with `{H1} > {## heading}\n\n` and `section == "{H1} > {## heading}"`.
- AC-2: A fenced code chunk extracted from a `##` section also has the breadcrumb prefix in `text` and breadcrumb in `section`.
- AC-3: A file with no H1 produces chunks identical to today's output.
- AC-4: A `##` section whose stripped body character count exceeds `H3_SPLIT_THRESHOLD_CHARS` and contains at least one `###` heading produces multiple chunks, one per `###` sub-section.
- AC-5: Each `###` sub-chunk has `section == "{H1} > {## heading} > {### heading}"` and `text` prefixed accordingly.
- AC-6: A `##` section at exactly `H3_SPLIT_THRESHOLD_CHARS` characters is not split (threshold is exclusive).
- AC-7: A `##` section above threshold with no `###` sub-headings falls through to line-window chunks; each fallback chunk has breadcrumb in `section` and `text` prefix.
- AC-8: Fenced code blocks inside a `###` sub-section carry the three-level breadcrumb in both `section` and `text`.
- AC-9: Preamble chunks are unaffected by breadcrumb injection.
- AC-10: Seed files receive the same breadcrumb treatment as doc files.
- AC-11: `###` sub-section prose chunk ID is `{path}#{h2-slug}/{h3-slug}`; fenced code chunk ID is `{path}#{h2-slug}/{h3-slug}:code`; line-window fallback ID is `{path}#{h2-slug}:L{start}-L{end}`.
- AC-12: `chunker.py` exports `CHUNKER_VERSION`; indexer `meta.json` stores it and forces a full rebuild when it changes.
- AC-13: All pre-existing `test_chunker.py` tests pass; any whose expected `section`, `text`, or `id` values change are updated with an explanatory comment.
- AC-14: New tests cover all cases in Req 11.

## Tasks

- [ ] Add `CHUNKER_VERSION = "2"` and `H3_SPLIT_THRESHOLD_CHARS = 2000` constants to `chunker.py`
- [ ] In `chunk_markdown`: capture the H1 title from the first line matching `^#\s+` (not `##`+); store as `doc_title`
- [ ] Inject breadcrumb into each section's `section` field and `text` prefix (both prose and fenced code chunks) when `doc_title` is present
- [ ] After building section body, check `len(body.strip()) > H3_SPLIT_THRESHOLD_CHARS and "###" in body`; if true, delegate to new `_split_h3_sections` helper
- [ ] Implement `_split_h3_sections(body, start_line, h2_title, doc_title, path, default_kind)`: split on `###` boundaries; prefix each sub-chunk text with three-level breadcrumb; extract fenced code blocks per sub-section (reuse `_FENCED_CODE_PATTERN`); emit `section` as three-level breadcrumb; use `{path}#{h2-slug}/{h3-slug}` ID scheme
- [ ] For oversized sections without `###`: call `chunk_line_window` on the prose body, then inject breadcrumb into each returned chunk's `section` and `text` prefix; use `{path}#{h2-slug}:L{start}-L{end}` IDs
- [ ] Update `indexer.py`: read `CHUNKER_VERSION` from chunker module; store in `meta.json` under `"chunker_version"`; trigger full rebuild when it differs from stored value (same pattern as `model_versions`)
- [ ] Update `test_chunker.py`: audit all existing `chunk_markdown` assertions for `section`, `text`, `id`; update stale values with comments; add AC-14 cases
- [ ] Run full test suite locally to confirm green

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| `chunker.py` changes | implementer | — | H1 capture → breadcrumb injection → `_split_h3_sections` helper |
| `test_chunker.py` updates | implementer | chunker.py | Update stale assertions; add new cases |
| Verification | implementer | both | `run_tests.py`; spot-check a real docs index build |

## Serialization Points

- `chunker.py`, `indexer.py`, and `test_chunker.py` are the only files touched; no other cross-file coordination needed.
- `CHUNKER_VERSION` constant must be incremented in `chunker.py` before the indexer task is written, so the indexer task can read the correct value.
- `framework_edit_allowed` guard must be open for all edits to framework scripts.

## Affected Architecture Docs

`docs/architecture/search-architecture.md` — update chunking strategy section to note H1 breadcrumb injection, threshold-gated `###` splitting, new chunk ID hierarchy scheme, and `CHUNKER_VERSION` rebuild signal. Check at implementation time; update if the doc covers chunker behavior.

Otherwise N/A — confined to `chunker.py`, `indexer.py`, and their tests; no module boundaries or control-flow topology changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core deliverable — breadcrumb in prose chunk text is the primary embedding quality improvement |
| AC-2 | required | Fenced code chunks need breadcrumb too; omitting them would be inconsistent |
| AC-3 | required | No-H1 fallback ensures no regression for files without a title |
| AC-4 | required | H3 splitting is the second core deliverable; oversized sections must break |
| AC-5 | required | Sub-chunk breadcrumb is required for H3 split to deliver retrieval value |
| AC-6 | required | Threshold boundary correctness — at-threshold must not split |
| AC-7 | required | Line-window fallback with breadcrumb handles sections without H3 but above threshold |
| AC-8 | required | Fenced code in H3 sub-sections must carry full breadcrumb |
| AC-9 | required | Preamble chunks must be unaffected — regression guard |
| AC-10 | nice-to-have | Seed files are secondary corpus; breadcrumb is valuable but lower priority than doc files |
| AC-11 | required | New ID scheme must be stable and consistent for indexer alignment |
| AC-12 | required | CHUNKER_VERSION rebuild signal is required for correct incremental indexing |
| AC-13 | required | Existing tests must pass; stale assertions must be updated |
| AC-14 | required | New tests are the verification gate for all new behaviors |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-01 | Change created | — |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-01 | Character count as threshold signal, not paragraph/complexity count | Embedding quality degrades with size regardless of content type; character count captures this directly; complexity only affects split-point selection, not trigger | Paragraph count (rejected: short dense paragraphs accumulate slowly; misleading signal); content-type heuristics (rejected: premature complexity, follow-on if needed) |
| 2026-05-01 | Threshold gates `###` splitting only; no new paragraph/list splitter for no-`###` sections | Line-window fallback already handles oversized sections without `###`; paragraph splitting is a follow-on if needed | Paragraph-boundary split (deferred) |
| 2026-05-01 | H1 injected as text prefix and `section` breadcrumb; no new `Chunk` fields | Keeps `Chunk` dataclass stable; breadcrumb in `section` is discoverable by existing consumers; text prefix directly improves embedding context | New `breadcrumb` field on `Chunk` (rejected: schema change with no immediate consumer benefit) |
| 2026-05-01 | Default threshold 2000 chars | ~30–40 lines of dense prose; keeps short-to-medium sections as single chunks while splitting large multi-subsection blocks; tunable via named constant | Lower (1000): splits too aggressively; Higher (3000+): misses moderately oversized sections |
| 2026-05-01 | Breadcrumb injected into doc chunk `text` as well as code chunk `text` | Doc chunks are the primary embedding target for prose search; omitting the breadcrumb from doc chunk text would leave the most-retrieved chunk type without document context. Validated by Anthropic's Contextual Retrieval (2024): context must appear in `text` to influence the embedding vector — metadata fields alone have no embedding effect. | Doc chunk text unchanged, breadcrumb only in `section` (rejected: `section` is metadata; embedding model sees `text`) |
| 2026-05-01 | Breadcrumb injected into line-window fallback chunks | Line-window chunks are produced when context is known (a `##` section exceeded threshold); discarding that context in the fallback is an unnecessary loss. Consistent with Contextual Retrieval principle: inject all available context. | Fallback chunks left with `section=None` (rejected: wastes known context) |
| 2026-05-01 | `###` IDs use `/` separator: `{path}#{h2-slug}/{h3-slug}` | `/` for sub-path traversal follows JSON Pointer (RFC 6901), which uses `/` as the path separator within a document. The `#` anchor prefix follows URI fragment syntax (RFC 3986). Together they give a scheme with clear prior art in two web standards. Leaves `::`, `:`, and `.` unambiguous for code IDs. | `.` (rejected: collides with Python qualified names); `>` (rejected: URL-unsafe) |
| 2026-05-01 | `CHUNKER_VERSION` in `chunker.py`; indexer reads it into `meta.json` | Follows database migration versioning pattern (Alembic, Flyway, Liquibase): a monotonically incrementing version forces full reprocess when transformation logic changes. Indexer already uses this pattern for `model_versions`; extending it to `chunker_version` is consistent and requires no new mechanism. | Manual full rebuild instruction only (rejected: relies on operator remembering to run `--full`; stale index is a silent correctness bug) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Existing tests assert exact `section`, `text`, or `id` values that change with breadcrumb injection or new ID scheme | AC-13 requires explicit audit of all `chunk_markdown` assertions; stale expected values must be updated with comments |
| Threshold default too aggressive or too conservative for real doc shapes | Constant is named and module-level; easy to adjust after observing index quality on real corpus |
| H1 capture misidentifies metadata lines as the title | H1 detection targets only `^#\s+` (single `#`, space, non-empty); `Owner:`, `Status:` lines don't match; safe |
| `CHUNKER_VERSION` increment forgotten when chunker logic changes in future | Convention documented in decision log; incrementing is the only required step; no tooling needed |
| Existing built indexes become stale after deployment | `CHUNKER_VERSION` change triggers automatic full rebuild on next `build_index` call; no manual intervention needed |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
