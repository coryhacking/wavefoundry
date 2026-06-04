# Chunker Oversized-Chunk Guard For All Text Surfaces

Change ID: `1p397-bug chunker-mega-chunk-fallback-for-unstructured-prompts`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-04
Wave: TBD (recommended: a follow-on wave after 1p35d closes; co-admit with `1p399`)

## Rationale

Investigation during wave 1p35d (C3 / `1p35j`) surfaced that ~half the framework seed catalog was unreachable via `seed_get`. C3's disk-fallback addressed the symptom; this change addresses one of two root causes.

**The defect, originally framed (markdown only):** `chunker.chunk_markdown()` (`.wavefoundry/framework/scripts/chunker.py:662`) splits markdown documents at their primary heading level (H2 when any `## ` exist; H3 as fallback; defaults to H2 when neither is present). When a `.prompt.md` file has **only an H1 title and no H2 sections** — typical of "Intent + numbered Tasks" prompt files like `040-docs-structure-bootstrap.prompt.md`, `060-domain-boundaries.prompt.md`, `070-quality-and-debt.prompt.md`, `080-mechanical-enforcement.prompt.md`, `090-doc-gardening-harness.prompt.md`, `110-wave-memory-bootstrap.prompt.md`, `120-project-persona-synthesis.prompt.md`, `130-agent-journal-bootstrap.prompt.md`, `140-reindex-ongoing.prompt.md`, `152-start-dashboard.prompt.md`, `153-stop-dashboard.prompt.md`, `154-restart-dashboard.prompt.md`, and `250-migrate-existing-wave-project.prompt.md` — the entire file body becomes a single preamble chunk. Seed-040 is 31K chars / ~7700 tokens; BGE-small's 512-token cap silently truncates input, so the resulting vector encodes only the first ~2K chars.

**The defect, broader framing (this scope):** A dispatcher-level audit of `chunk_file` (`chunker.py:4159`) shows **only `kind="code"` chunks are size-capped**. `split_large_code_chunks` (`chunker.py:478`) explicitly skips non-code chunks (`if chunk.kind != "code" or len(chunk.text) <= max_chars: result.append(chunk); continue`). Every other dispatch path — markdown (doc/seed/prompt), plain text, YAML, JSON, TOML, HTML, XML — can emit chunks of unbounded size, and the embedder will silently truncate any chunk past its 512-token input cap.

The H1-only markdown prompt is the observed acute case (because seed files are heavily H1-only and 30K+ chars), but the same defect applies anywhere a text-bearing file produces a long structural region without an internal split boundary: a 200-line YAML config under a single key, a JSON blob with one giant `description` field, a plain-text doc with one long paragraph. None of these would be re-split today.

Net effect: any indexed text file whose structural chunker emits an oversized non-code chunk becomes weakly-searchable or unsearchable at the semantic surface, regardless of whether it appears in `file_meta`.

## Requirements

1. **Universal oversized-chunk guard at the dispatcher level.** Introduce `split_large_chunks(chunks, max_chars=MAX_CHUNK_CHARS)` (or generalize `split_large_code_chunks` by removing its `kind != "code"` early-skip). Apply it in `chunk_file` (`chunker.py:4159`) to **every dispatch path**, not just the code paths. After this pass, no chunk emitted by `chunk_file` exceeds `MAX_CHUNK_CHARS`.
2. **`MAX_CHUNK_CHARS` default = 4000.** Matches the existing `MAX_CODE_CHUNK_CHARS` value. Code chunks already use this threshold; reusing it keeps behavior continuous for code and applies a parallel ceiling to other kinds.
3. **Structural-unit awareness for markdown (keep-whole-if-it-fits).** `chunk_markdown()` treats lists (numbered and bullet, including nested items under the same top-level item) and pipe tables as **structural units**. Default behavior: the unit is kept as a single chunk. Only when a unit exceeds `MAX_CHUNK_CHARS` does it decompose:
   - **Lists** decompose one **top-level item** at a time (including any nested children/sublists/code blocks under that item). If a single top-level item still exceeds `MAX_CHUNK_CHARS`, the universal guard hard-wraps it.
   - **Tables** decompose one **row** at a time, with the header row prepended to each emitted chunk to preserve column context. If a single row + header still exceeds `MAX_CHUNK_CHARS`, the universal guard hard-wraps it.
   - **Prose / paragraph content** between structural units decomposes at paragraph boundaries (blank-line separated) when oversized.
4. **Markdown semantic split fallback order.** When an H1-only or otherwise oversized markdown body needs splitting, `chunk_markdown()` walks the body's top-level blocks in document order, emitting one chunk per block until the running chunk size would exceed `MAX_CHUNK_CHARS`, at which point it flushes. Structural units (lists, tables) participate as single blocks unless they themselves exceed the cap, in which case Requirement 3's decomposition applies. The universal guard handles anything that remains over-cap as a last resort.
5. **Markdown structural-awareness scope gate.** The keep-whole / per-item / per-row decomposition applies whenever a markdown body contains the affected structures and `chunk_markdown()` is on a path that would otherwise emit oversized chunks. The `kind_override` gate controls only one narrower decision: whether to *eagerly* re-split H1-only bodies even when individual top-level blocks would fit. For `kind_override` ∈ seed/prompt with H1-only body, eagerly split. For generic project-layer docs, decompose only when an emitted chunk would actually exceed `MAX_CHUNK_CHARS`. This preserves project-layer doc index chunk shape while still correcting the oversized-chunk case for both surfaces.
6. **Section label derivation for derived chunks.**
   - **List decomposition**: emitted chunks use the first 80 chars of the top-level list-item text as `section`.
   - **Table decomposition**: emitted chunks use `<original-section> · row N–M` (e.g., `Decision Log · row 3–4`) as `section`. The header row is prepended to each chunk and does not count toward row numbering.
   - **Paragraph decomposition**: emitted chunks use the first 80 chars of the first paragraph in the chunk as `section`.
   - **Universal hard-wrap guard** (last resort, when no structural decomposition can bring a chunk under the cap): derived chunks keep the parent `section` and append `(part N/M)`.
7. **Plain text, YAML, JSON, TOML, HTML, XML are covered by the universal guard.** No per-chunker semantic fallback is required for these in this change — hard-wrap at `MAX_CHUNK_CHARS` is acceptable for correctness (it guarantees the embedder sees the content) even if the chunk shape is not semantically clean. Better-than-hard-wrap fallbacks for these types can land in later changes if observed quality issues surface.
8. **Coverage assertion.** The generative test introduced in `1p35j` (`test_every_numbered_seed_reachable`) is extended to assert that **no indexed seed produces a chunk exceeding `MAX_CHUNK_CHARS`**. This is the load-bearing regression guard; it catches any future chunker that bypasses the universal pass.
9. **`CHUNKER_VERSION` bumps in the same change.** Because the universal guard + structural-unit awareness changes the shape of emitted chunks (list/table per-item vs. per-row decomposition, `(part N/M)` hard-wrap suffix, structural-unit-as-single-chunk preference), `chunker.py:CHUNKER_VERSION` must increment in the same commit. `indexer.py:1880-1897` auto-escalates to a full rebuild on chunker-version mismatch (`old_chunker_versions["docs"] != current_chunker_version`), so consumers running `Upgrade wave framework` to the version including this fix get the new chunk shape applied to their entire corpus automatically — no manual `wave_index_build(mode='rebuild')` step required. **Missing this bump is the load-bearing-correctness failure mode**: without it, consumer indexes keep their old-shape chunks, the universal guard never gets to re-process them, and the bug stays latent on every consumer until something else triggers a rebuild. Same shape as the established `GRAPH_BUILDER_VERSION` rule for graph-extractor changes.
10. **No additional re-embedding required at fix time beyond the chunker bump.** Once `CHUNKER_VERSION` increments, existing indexed files re-chunk automatically on the next incremental update via the auto-escalation path above. The companion `1p399` (indexer drift detection) provides the proper repair path for already-built indexes that have other forms of drift.

## Scope

**Problem statement:** Every non-code chunk in the chunker pipeline can exceed the embedder's input cap, silently truncating the embedded representation. H1-only markdown prompts are the observed acute case; the underlying defect spans all non-code chunk kinds.

**In scope:**

- Universal oversized-chunk guard applied in `chunk_file` to every dispatch path
- `chunk_markdown()` structural-unit awareness: lists (numbered + bullet) and pipe tables kept whole when they fit, decomposed per-item / per-row when they don't
- `chunk_markdown()` H1-only oversized-body splitting that walks top-level blocks (treating structural units as single blocks) and flushes at `MAX_CHUNK_CHARS`
- Per-item / per-row section label derivation; `(part N/M)` for hard-wrap splits
- Header-row preservation when tables decompose per-row
- Extension to `test_every_numbered_seed_reachable` for max-chars assertion
- Coverage of plain text, YAML, JSON, TOML, HTML, XML by the universal guard (hard-wrap only)
- Tests for the markdown structural-unit paths (whole list, per-item list, whole table, per-row table) and the universal hard-wrap path

**Out of scope:**

- Repairing existing indexes that already have the drift (covered by `1p399`)
- Semantic-aware fallbacks for non-markdown text types beyond hard-wrap (e.g., YAML key boundaries, JSON property boundaries) — defer until evidence of retrieval-quality issues
- Improving the seed-040, seed-060, etc. content to add H2 sectioning (cosmetic; not load-bearing)
- Replacing BGE-small with a longer-context embedder (model-swap is out of band)
- Changes to chunking of binary or unsupported file types

## Acceptance Criteria

- [ ] AC-1: `chunk_file` applies `split_large_chunks` (or the generalized `split_large_code_chunks`) to the result of every dispatch branch, not only the code branches.
- [ ] AC-2: After `chunk_file` returns, no chunk exceeds `MAX_CHUNK_CHARS` (default 4000), regardless of original chunker, file type, or chunk kind.
- [ ] AC-3: `chunk_markdown()` treats lists (numbered + bullet) and pipe tables as structural units: a list/table that fits under `MAX_CHUNK_CHARS` emerges as a **single chunk**, not as one chunk per item or per row.
- [ ] AC-4: When a list exceeds `MAX_CHUNK_CHARS`, it decomposes one top-level item at a time (including any nested children/sublists/code blocks under that item). Items are grouped greedily into chunks up to the cap.
- [ ] AC-5: When a table exceeds `MAX_CHUNK_CHARS`, it decomposes one row at a time. Each emitted chunk has the header row prepended so column context is preserved.
- [ ] AC-6: When `chunk_markdown()` splits an H1-only or otherwise oversized body, it walks top-level blocks in document order, treats lists and tables as single blocks until they themselves exceed the cap, and flushes a chunk whenever the running size would exceed `MAX_CHUNK_CHARS`.
- [ ] AC-7: Section-label derivation: list-decomposed chunks use the first 80 chars of the top-level list item; table-decomposed chunks use `<original-section> · row N–M`; paragraph-decomposed chunks use the first 80 chars of the first paragraph; universal-guard hard-wrap derivatives use `<parent-section> (part N/M)`.
- [ ] AC-8: Chunker behavior on H2-rich markdown files (e.g., seed-050) is unchanged — same chunk count, same section labels, same line ranges (regression guard).
- [ ] AC-9: Generic doc markdown (no `kind_override` indicating prompt content) is NOT eagerly re-split — structural-unit decomposition fires only when a unit actually exceeds `MAX_CHUNK_CHARS`. Project-layer doc index chunk shape is preserved for fitting content.
- [ ] AC-10: Test fixture: seed-040-style "Intent + Tasks" input (long numbered list, no H2) decomposes per-top-level-item with 10+ resulting chunks, each ≤ `MAX_CHUNK_CHARS`.
- [ ] AC-11: Test fixture: a small numbered list (~500 chars) emerges as a **single chunk**, not split per item. Regression guard for the keep-whole-if-it-fits property.
- [ ] AC-12: Test fixture: a small pipe table (~500 chars) emerges as a **single chunk**, not split per row.
- [ ] AC-13: Test fixture: a 6K-char pipe table with a header row decomposes per-row, header prepended to every derived chunk, each chunk ≤ `MAX_CHUNK_CHARS`.
- [ ] AC-14: Test fixture: a 10K-char plain-text input emerges as multiple chunks each ≤ `MAX_CHUNK_CHARS`.
- [ ] AC-15: Test fixture: a long YAML file with one large top-level key emerges as multiple chunks each ≤ `MAX_CHUNK_CHARS` (hard-wrap is fine).
- [ ] AC-16: `test_every_numbered_seed_reachable` (from `1p35j`) gains an assertion: no seed produces a chunk exceeding `MAX_CHUNK_CHARS`. Load-bearing generative guard.
- [ ] AC-17: `chunker.CHUNKER_VERSION` is bumped in the same change. Load-bearing for correctness: without the bump, `indexer.py:1880-1897` auto-escalation never fires and consumer indexes keep their old-shape chunks; the fix stays latent on every consumer until something else triggers a rebuild. Test asserts the constant changed value (regression guard against future refactors that touch chunk shape without bumping).
- [ ] AC-18: Full framework test suite passes after changes (regression discipline).
- [ ] AC-19: docs-lint passes.

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Introduce `MAX_CHUNK_CHARS` constant (= `MAX_CODE_CHUNK_CHARS` value) and `split_large_chunks(chunks, max_chars)` helper
- [ ] Either generalize `split_large_code_chunks` (drop the `kind != "code"` early-skip) and rename, or add a thin wrapper — pick the smaller diff
- [ ] Wire the universal guard into `chunk_file` so every dispatch path runs through it before return
- [ ] Add a top-level-block walker to `chunk_markdown()` that recognizes lists (numbered + bullet) and pipe tables as structural units, treats each as a single block when sizing chunks
- [ ] Implement list decomposition: when a list exceeds `MAX_CHUNK_CHARS`, emit per-top-level-item chunks (grouped greedily up to the cap, with nested children kept with their parent item)
- [ ] Implement table decomposition: when a table exceeds `MAX_CHUNK_CHARS`, emit per-row chunks (grouped greedily) with the header row prepended to each emitted chunk
- [ ] Implement paragraph decomposition for oversized prose blocks (blank-line separated)
- [ ] Implement section-label derivation across all decomposition paths (list item / `· row N–M` / paragraph hint / `(part N/M)` for hard-wrap)
- [ ] Add markdown fixture test: small list kept whole (regression for keep-whole-if-it-fits)
- [ ] Add markdown fixture test: small table kept whole
- [ ] Add markdown fixture test: large list decomposes per-top-level-item (seed-040-style)
- [ ] Add markdown fixture test: large table decomposes per-row with header preserved on each emitted chunk
- [ ] Add plain-text oversized-chunk fixture test (universal guard)
- [ ] Add YAML oversized-chunk fixture test (universal guard)
- [ ] Add regression test for H2-rich markdown (chunk count + sections preserved)
- [ ] Add regression test for non-prompt H1-only markdown where individual blocks fit (no eager re-split; structural decomposition fires only above the cap)
- [ ] Extend `test_every_numbered_seed_reachable` with max-chars assertion
- [ ] Bump `chunker.CHUNKER_VERSION` (currently `"22"` at the time of this plan; bump to `"23"` or whatever is next when the change actually lands)
- [ ] Add test asserting `CHUNKER_VERSION` increased relative to the pre-change baseline (covers AC-17 — regression guard against future refactors that change chunk shape without bumping)
- [ ] Run framework test suite
- [ ] Run docs-lint
- [ ] Close gate

## Affected Architecture Docs

`N/A` — internal chunker logic change; no architectural boundary or contract surface modified.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (universal guard wired into dispatcher) | required | Core fix mechanism; without it, only code chunks are protected. |
| AC-2 (no chunk > MAX_CHUNK_CHARS) | required | The observable correctness property. Anything beyond this is shape. |
| AC-3 (lists / tables are structural units, kept whole when they fit) | required | Without this, retrieval quality regresses for small lists/tables that are most useful as a single semantic unit. |
| AC-4 (list decomposes per top-level item when oversized) | required | Per-item decomposition produces the cleanest semantic chunks for "Intent + Tasks" prompt content. |
| AC-5 (table decomposes per row with header preserved) | required | Without header preservation, decomposed table rows lose column context and become low-quality retrieval hits. |
| AC-6 (top-level-block walker flushes at cap) | required | The walker is the load-bearing structural traversal; without it, lists/tables interact incorrectly with surrounding prose. |
| AC-7 (section label derivation across paths) | required | Without coherent sections, `seed_get` substring matching on sections fails or returns confusing labels. |
| AC-8 (H2-rich behavior preserved) | required | Regression guard — must not change behavior on the ~70% of seeds that do have H2 sections. |
| AC-9 (non-prompt H1-only fitting content unchanged) | required | Regression guard for project-layer doc index. Decomposition fires only when actually over the cap. |
| AC-10 (large list per-item fixture) | required | Verifies the per-item decomposition path produces ≥10 chunks under cap on representative input. |
| AC-11 (small list kept whole) | required | Regression guard for the keep-whole-if-it-fits property — without this, the property is unverified. |
| AC-12 (small table kept whole) | required | Same as AC-11 for tables. |
| AC-13 (large table per-row + header preserved) | required | Verifies per-row decomposition path and header preservation. |
| AC-14 (plain-text oversized fixture) | required | Verifies the universal guard fires beyond markdown — without this, the scope expansion is unverified. |
| AC-15 (YAML oversized fixture) | required | Same as AC-14 for tree-sitter dispatch paths. |
| AC-16 (generative max-chars assertion) | required | The load-bearing future-proof guard. Catches any future chunker that bypasses the universal pass. |
| AC-17 (CHUNKER_VERSION bump) | required | Without it, consumer indexes keep the old chunk shape and the fix stays latent. Auto-escalation in `indexer.py` is gated on this constant. |
| AC-18 (suite passes) | required | Standard. |
| AC-19 (lint passes) | required | Standard. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-04 | Apply the size guard at the dispatcher level, not inside each individual chunker | One choke point covers every current and future chunker; each chunker need not remember to enforce the cap. | Per-chunker enforcement — rejected; relies on every future chunker remembering the convention. |
| 2026-06-04 | Reuse `MAX_CODE_CHUNK_CHARS` value (4000) as `MAX_CHUNK_CHARS` for all kinds | Continuous behavior for code (no regression); a parallel ceiling for other kinds; established value with operational history. | Pick a lower bound (e.g., 2000) closer to BGE-small's actual cap — rejected; would re-split many existing code chunks and shift retrieval shape for the whole index. |
| 2026-06-04 | Lists and tables are structural units: kept whole when they fit, decomposed per-item / per-row when they don't | A small list or table is most useful as a single semantic unit; over-eager decomposition produces low-quality retrieval hits for cohesive small structures. Decomposition only when the unit actually exceeds the cap preserves retrieval quality for the common case and corrects only the problematic case. | Always decompose lists per-item and tables per-row regardless of size — rejected; would degrade retrieval quality for small cohesive structures. Or never decompose — rejected; doesn't fix the bug. |
| 2026-06-04 | Table per-row decomposition prepends the header row to every emitted chunk | Decomposed rows without column context lose most of their semantic value — a row like `\| 2026-06-04 \| Decision text \| Reason \| Alts \|` means nothing without the header. | Drop the header — rejected; decomposed rows become low-quality. Emit a separate header chunk — rejected; the consumer can't reliably join header chunks to row chunks at retrieval time. |
| 2026-06-04 | Markdown structural decomposition fires whenever a unit exceeds the cap, regardless of `kind_override` | The bug (oversized chunks → truncated embeddings) affects all surfaces, not only seed/prompt. The `kind_override` gate controls only the narrower question of *eagerly* re-splitting H1-only bodies even when individual blocks would fit. | Gate all structural decomposition on `kind_override` — rejected; project-layer docs with a 30K-char table would still emit a truncated single chunk, leaving the bug unresolved on that surface. |
| 2026-06-04 | Plain text / YAML / JSON / TOML / HTML / XML use hard-wrap only (no semantic fallback in this change) | Hard-wrap is sufficient for the correctness property (no truncated embeddings). Semantic-aware fallbacks for these types are a quality improvement that should ride evidence, not speculation. | Build YAML key-boundary and JSON property-boundary fallbacks now — deferred; no observed retrieval-quality issues yet on those types, and the universal guard ensures correctness regardless. |
| 2026-06-04 | Hard-wrap section label uses `(part N/M)` suffix | Operators reading retrieval results need to distinguish hard-wrap derivatives from semantically-split or original chunks. | Drop section on hard-wrap derivatives — rejected; substring matching on sections would degrade. |
| 2026-06-04 | Coverage assertion in `test_every_numbered_seed_reachable` is "no chunk > MAX_CHUNK_CHARS" | The single load-bearing invariant. A future chunker that emits a 30K chunk would fail this test regardless of which dispatch path produced it. | Per-chunker chunk-count assertions — rejected; brittle to future content edits that legitimately change shape. |

## Risks

| Risk | Mitigation |
|---|---|
| Hard-wrap on tree-sitter-produced YAML/JSON/TOML chunks degrades retrieval quality on those file types | Acceptable for correctness baseline; semantic-aware fallbacks for those types can land in follow-on changes once evidence justifies the investment. The current behavior (silent embedder truncation) is worse than hard-wrap. |
| Doubling up: code chunks already pass through `split_large_code_chunks` inside individual code branches AND would pass through the universal guard | Either (a) remove the inner per-branch call (preferred — single choke point) or (b) make the universal guard idempotent (no-op on already-compliant chunks). Either is safe. |
| Markdown list/table boundary detection misfires on edge-case formatting (e.g., a code block that contains pipe characters that look like a table) | Detection uses canonical markdown patterns (list item starts at line column; table rows require `\|` at line start AND a separator row beneath the header). False positives at worst produce more or fewer structural units than expected; correctness (no chunk over cap) is preserved by the universal guard regardless. |
| Per-row table decomposition with header prepended inflates total embedded text proportional to row count × header size | Acceptable: header rows are typically <200 chars; tables that decompose are by definition >4000 chars, so header inflation is <5% per emitted chunk. Trade-off favors semantic recoverability of decomposed rows. |
| Existing indexes don't pick up the fix until files are re-edited (mtime change) | Companion change `1p399` adds drift detection that forces re-chunk when `file_meta` and Lance disagree, regardless of mtime. |
| New chunker tests slow down the suite | Each chunker test is unit-level (microseconds). No measurable impact. |
| Operators see new `(part N/M)` section labels in retrieval results and assume they indicate degraded chunk quality | Document the label in the chunker's docstring + a short note in the index health surface so it reads as routine. |

## Related Work

- **`1p35d` (1p35j)** — added the disk-fallback to `get_seed` that worked around this bug at the consumer side. The fallback remains useful as defense-in-depth even after this fix lands.
- **`1p399` (companion bug)** — fixes the indexer drift problem where `file_meta` and Lance get out of sync. Together these two changes close the "half the seed catalog unreachable" defect at root cause: `1p397` prevents NEW drift from this source, `1p399` repairs EXISTING drift.
- **Seed retrospective (downstream consumer)** — original report flagged `seed_get` / `docs_search` half-coverage as the highest-impact item.
- **`chunker.py:478` `split_large_code_chunks`** — the existing code-only guard that this change generalizes.
- **`chunker.py:4159` `chunk_file`** — the dispatcher that gains the universal guard wiring.

## Session Handoff

Not yet admitted to a wave. Recommended path: admit alongside `1p399` into a new wave that closes before the **1.5.0** release tag — both waves (`1p35d` and this follow-on) ship together as 1.5.0. The two changes are orthogonal but together fix the same broader defect ("half the seed catalog unreachable"); shipping them under the same version tag means consumers absorb the chunker fix in the same upgrade as the install-flow restructure.

**Scope-expansion notes (2026-06-04):**

1. The original framing was markdown-prompt-specific. Operator question during 1p35d C3 review surfaced that the underlying defect (dispatcher-level — only code chunks are size-capped) is broader than the markdown observation. This plan now covers the universal dispatcher-level guard and treats the markdown structural-unit handling as the preferred boundary selector layered on top of it.
2. Second operator refinement: lists and tables should be treated as structural units — kept whole when they fit, decomposed per-item / per-row only when they don't. Replaces the original "always split at numbered-list boundaries" framing. The keep-whole-if-it-fits property is now a load-bearing AC (AC-11, AC-12) so future changes can't regress it.
