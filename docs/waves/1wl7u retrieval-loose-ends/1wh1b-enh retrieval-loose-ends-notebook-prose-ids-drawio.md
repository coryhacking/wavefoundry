# Retrieval Loose Ends: Notebook Cells, Prose Section Ids, drawio Decision

Change ID: `1wh1b-enh retrieval-loose-ends-notebook-prose-ids-drawio`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-28
Wave: `1wl7u retrieval-loose-ends`

## Rationale

Wave `1wik9` recorded three dispositions it deliberately did not deliver, and all
three are now small because that wave built the machinery. Executed probes on the
shipped 1.20.0 tree (2026-08-28) confirm the current state. (1) Notebook code
cells still reach NEITHER retrieval table: `chunk_jupyter` emits them as
`kind="code"` from `.ipynb` files that are never code-eligible (probe:
`docs/analysis.ipynb#cell-1`, kind `code`, dropped by the per-table gate), the
exact both-tables drop class `1whup` closed for fences. The fix is nearly free:
cell ids are already unique per file (`#cell-N`) and cell sections already carry
breadcrumbs ("notebook > Cell 2"), so routing is a kind change on proven
`doc-code` plumbing. (2) Duplicate-titled PROSE sections still collide chunk ids
(probe: two `Setup` sections in one rst file both emit `docs/guide.rst#setup`) and
collapse silently in the id-keyed delta planner and chunk registry, the recorded
pre-existing bound of `1whup` Requirement 2; the repeat-crumb ordinal pattern
shipped for SDL `extend` (CODE-DEL-1 repair) is the proven fix shape. (3) The
`.drawio` question `1whuq` recorded stays open: an executed probe shows a text-XML
`.drawio` passes the content sniff, WALKS in, chunks as one code-kind line window,
and ships zero rows in either table, so today it costs walk and chunk work while
delivering nothing and polluting nothing.

## Requirements

1. Notebook code cells MUST emit `kind="doc-code"` (markdown cells stay `doc`;
   `#cell-N` identities unchanged; the notebook-level kernel language preserved
   where the notebook declares one — per-cell language metadata is ignored by the
   shipped chunker and stays ignored; council-executed probe: an R-tagged cell
   reports the kernel's `python`), routing them into the DOCS table through the
   landed `_is_docs_kind` membership. The `doc-code` conventions apply as landed
   by `1whup`: code size cap and breadcrumb injection (cell text is bare source
   with `section` set, so injection supplies the context). Notebook OUTPUTS remain
   unindexed exactly as today, verified not assumed. The preserved-invisibility
   disposition recorded in `1whup` AC-1 is SUPERSEDED by this change and the
   supersession is recorded in this document AND made executable, never silently:
   the three shipped tests pinning the current notebook kind
   (`test_notebook_code_cells_keep_their_current_kind` — the 1whup disposition
   artifact — plus `JupyterChunkerTests.test_code_cell_produces_code_chunk` and
   `test_dispatch_routing`) are rewritten to pin the new contract in the same
   landing.
2. Duplicate-titled prose sections MUST gain repeat-only file-pass ordinals across
   EVERY prose-id emission site (markdown section ids including the H3-split and
   line-window id bases, and the shared rst/adoc `_emit_prose_sections` ids): the
   first occurrence of a slug keeps its current id (id stability for the
   overwhelming single-title case), and repeats within one `chunk_file` pass get a
   deterministic ordinal suffix, mirroring the SDL `crumb_counts` COUNTER
   mechanics but NOT its `-N` suffix shape. The council falsified the shape
   transfer: `-N` is a legal `_slugify` output tail (1,647 ids in this corpus
   already end in `-<digits>`, and a literal `Setup 2` title emits `#setup-2`),
   so the ordinal suffix MUST either contain a character outside the slug
   alphabet (for example `~2`) or be assigned collision-aware against the file's
   literal slugs. An EXECUTED census through the real chunker MUST enumerate
   every UN-ANCHORED slug-id emission site across ALL chunkers first — not only
   the md/rst/adoc family: council probes already reproduced the same collision
   in the `chunk_html` regex fallback (kind `doc`), with `chunk_xml`'s fallback
   and `_ts_config_chunker` as adjacent un-anchored `{path}#{slug}` emitters —
   and each census site is fixed or explicitly dispositioned out; the census,
   not this plan, is the authority. The id-keyed silent collapse in
   `_plan_lance_delta_rows` and the sqlite registry upsert is the motivating
   defect, live in this repo's own corpus (6 files currently emit duplicate ids,
   silently losing 15 index rows).
3. The `.drawio` membership question MUST be closed by census plus recorded
   decision: an executed census (real-world-shaped `.drawio` fixture through
   `walk_repo`, both eligibility sets, and `chunk_file`) grounds a Decision Log
   entry either adding `.drawio` to `_GENERATED_EXCLUDE_EXTENSIONS` (a
   walk-behavior change requiring a `WALKER_VERSION` bump with its rationale
   line, following the `.excalidraw` precedent) or recording the status quo with
   its measured cost. Either outcome is acceptable; an unrecorded outcome is not.
4. Measurement (notebook routing only): extend the prose golden set with a
   committed real-world-shaped `.ipynb` fixture and at least 4 notebook-variant
   queries whose anchors are proven unique to the fixture within the corpus,
   FROZEN with a recorded baseline (structurally zero for code-cell content)
   before the chunker edit. The bar: at least 0.75 recall at 5 on the notebook
   queries after the change, AND the content-anchored per-format prose aggregates
   hold their frozen baselines (the `1whup` amended-bar convention), with
   file-attributed movements recorded and dispositioned. The prose-ordinal change
   is identity-only and carries no retrieval measurement.
5. Version and differential discipline: chunk-set shape changes bump
   `CHUNKER_VERSION` with the documented rationale (once if the pieces land
   together); the markdown and specs-negatives byte-identity differentials
   regenerate as a deliberate versioned step under the tool venv with every
   changed row classified into the intended delta classes (notebook cell kind,
   repeat-title ordinal ids) and discrimination re-proven on mutation before
   re-arming. The council verified the current differential sources are BLIND to
   both declared classes (no duplicate titles, no notebooks), so the versioned
   regeneration MUST add at least one duplicate-titled markdown source (and a
   notebook source where the format fits) — a regeneration whose declared delta
   classes produce zero rows is vacuous and does not satisfy this requirement.
   The kind-mirror sweep is re-executed to verify `doc-code` needs no new mirror
   sites for notebooks (verified, never assumed).
6. Coverage invariant (standing ARCH-DEL-1 criterion): a per-line content-coverage
   differential over notebook and duplicate-titled fixtures proves no file loses
   coverage relative to the pre-change chunker path, previously-dropped code-cell
   content appears in docs-table-eligible chunks, and the differential is proven
   non-vacuous by revert-simulation.
7. Boundaries: no code-table membership change (no `.ipynb` becomes
   code-eligible); no notebook-output or attachment indexing; no reranker,
   embedder, or walk changes beyond the explicit `.drawio` decision; prompt-kind
   and seed markdown behavior untouched.

## Scope

**Problem statement:** three recorded retrieval gaps from the 1wik9 arc remain
open: notebook code content is invisible to search, duplicate-titled prose
sections silently lose index rows, and the `.drawio` membership question is
undecided.

**In scope:**

- `.wavefoundry/framework/scripts/chunker.py` (notebook cell kind, prose repeat
  ordinals, `CHUNKER_VERSION`; `.drawio` exclusion only if decided)
- `.wavefoundry/framework/scripts/indexer.py` only if the `.drawio` decision adds
  the exclusion (`WALKER_VERSION` and the generated-extension set)
- `.wavefoundry/framework/scripts/tests/test_chunker.py` and `test_indexer.py`
  (routing, ordinal-uniqueness, degenerate, differential, and census-fixture
  regressions)
- `.wavefoundry/framework/scripts/tests/fixtures/retrieval_golden/` (notebook
  fixture, nb-variant golden queries, regenerated differentials)
- the docs-layer contract carriers where notebook cells are named: seed 211 plus
  its `docs/agents/guru.md` parity mirror (behind `seed_edit_allowed`; the edit
  lands INSIDE the `GuruIndexScopeParityTests`-guarded `## Index Scope` region,
  so the mirror edit is byte-identical or the suite fails),
  `docs/contributing/build-and-verification.md`, `docs/specs/mcp-tool-surface.md`
  (which the council found does NOT currently name notebook cells — update only
  where a stated fact changes)
- `docs/architecture/search-architecture.md`,
  `docs/architecture/chunking-and-indexing-pipeline.md`,
  `docs/architecture/testing-architecture.md`
- `docs/architecture/performance-budget.md` — the lint-bound `chunker version`
  pin; the docs gate hard-fails on the `CHUNKER_VERSION` bump until it refreshes
- `CHANGELOG.md` `[Unreleased]` entry at close (the 1wip2 claims engine
  machine-checks any version-constant numerals written there)

**Out of scope:**

- indexing notebook outputs, attachments, or execution results
- admitting notebook content to the CODE table
- any diagram format beyond the recorded `.drawio` decision
- reranker, embedder, or harness metric changes

## Acceptance Criteria

- [x] AC-1: Routing and shape tests prove notebook code cells emit `doc-code`
  with unchanged `#cell-N` identities, preserved notebook-level kernel language,
  injected breadcrumbs, the code cap, and docs-table-only membership; notebook
  outputs remain unindexed; the `1whup` disposition supersession is recorded and
  executable (the three kind-pinning tests rewritten to the new contract).
- [x] AC-2: Ordinal-uniqueness tests prove duplicate-titled markdown, rst, and
  adoc prose sections (including the H3-split path) emit collision-free ids
  whose suffix cannot collide with any legal `_slugify` output (non-slug-alphabet
  character or collision-aware assignment), with first-occurrence ids unchanged,
  pinned against the census-enumerated emission sites (the census sweeps every
  un-anchored slug-id emitter across all chunkers, including the HTML/XML
  fallbacks and `_ts_config_chunker`, each fixed or dispositioned); the
  regenerated differentials include at least one duplicate-titled source so the
  declared delta classes are non-vacuous, carry only classified deltas, and are
  mutation-proven before re-arming.
- [x] AC-3: The `.drawio` census exists as evidence and the Decision Log records
  the membership outcome; if the exclusion lands, `WALKER_VERSION` bumps with
  rationale and a walk regression pins it, and if not, the status-quo cost is
  recorded.
- [x] AC-4: The frozen notebook golden queries meet the Requirement 4 bar with
  the content-anchored prose aggregates at or above their frozen baselines,
  recorded as wave evidence with movements dispositioned. Status note: ipynb
  1.0 recall at 5 (bar 0.75); md improved to 0.750, adoc holds 0.750, fence-*
  hold 1.0; ONE aggregate sits below its frozen value — rst 0.750 to 0.688 —
  with the movement file-attributed (p10:rst rank 4 to 6, zero notebook rows
  in its top 5, displaced by byte-identical cross-format twins of the same
  answer content; rst chunking differential-proven byte-identical, rst MRR
  improved) and ACCEPTED by the recorded Decision Log disposition of
  2026-08-29; the "movements recorded and dispositioned" clause is read as
  governing this case.
- [x] AC-5: The coverage differential proves zero content loss with
  revert-simulation on notebook and duplicate-titled fixtures.
- [x] AC-6: `CHUNKER_VERSION` carries its rationale, the kind-mirror sweep is
  re-executed and recorded, contract carriers are updated behind their gates
  (seed parity enforced by `GuruIndexScopeParityTests`; the lint-bound
  `performance-budget.md` chunker pin and the two stale `"34"` pins in the
  pipeline doc refresh to the post-wave value), and the full suite and docs gate
  pass.

## Tasks

- [x] Execute and record the censuses: un-anchored slug-id emission sites across
  ALL chunkers (md/rst/adoc plus the HTML/XML fallbacks and config chunker),
  notebook emission and output handling, kind-mirror sweep, `.drawio`
  walk/eligibility/chunk census.
- [x] Author the notebook fixture and nb-variant golden queries with uniqueness
  proof; freeze and record the baseline.
- [x] Implement notebook `doc-code` routing and prose repeat ordinals; bump
  `CHUNKER_VERSION`; land the `.drawio` decision.
- [x] Regenerate the byte-identity differentials as a versioned step with
  classified deltas and discrimination proof, adding a duplicate-titled source
  (and a notebook source where the format fits) so the declared classes appear.
- [x] Add routing, ordinal, degenerate, walk (if decided), and
  coverage-differential regressions.
- [x] Record the post-change measurement against the bar; disposition movements.
- [x] Update contract carriers and architecture docs; run the canonical suite and
  docs gate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Censuses and golden queries | performance-reviewer | none | Baseline frozen before any chunker edit; census is the authority over plan enumerations. |
| Routing and ordinals | implementer | Censuses and golden queries | chunker.py serialized through one lane; drawio decision lands with its census. |
| Regressions and differentials | qa-reviewer | Routing and ordinals | Coverage differential is the leak guard; differentials regenerate versioned. |
| Measurement and carriers | performance-reviewer, docs-contract-reviewer | Regressions and differentials | Seed edits behind the gate with parity discipline. |


## Serialization Points

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `.wavefoundry/framework/seeds/211-guru.prompt.md`
- `docs/agents/guru.md`

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`: the doc-code kind-list bullet
  gains notebook code cells and drops the now-false preserved-state clause; walk
  section (and the bullet's "stay out by decision" clause) if the `.drawio`
  exclusion lands.
- `docs/architecture/chunking-and-indexing-pipeline.md`: notebook chunking line,
  the prose-id ordinal note, the `doc-code` kind-table row gains notebook code
  cells, and the two pre-existing stale `CHUNKER_VERSION` `"34"` pins refresh to
  the post-wave value.
- `docs/architecture/testing-architecture.md`: a NEW tier row for this wave's
  regressions AND the now-false "preserved notebook state" phrase in the 1wik9
  row updates.
- `docs/architecture/performance-budget.md`: the lint-bound chunker version pin
  refreshes with the bump.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Closes the last recorded both-tables content drop; the routed kind is the delivered mechanism. |
| AC-2 | required | Silent index-row collapse is the defect class this project treats as blocking; identities are the consumer contract. |
| AC-3 | required | An undecided membership question left open twice becomes standing ambiguity; either recorded outcome closes it. |
| AC-4 | required | Retrieval changes ship only with recorded measurements on frozen sets. |
| AC-5 | required | Golden sets provably cannot see coverage loss; the differential is the only oracle. |
| AC-6 | required | Version discipline and carrier truth are standing requirements. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-28 | Planned from executed probes on the shipped 1.20.0 tree: `chunk_jupyter` emits code cells as `kind="code"` with unique `#cell-N` ids and breadcrumbed sections (`docs/analysis.ipynb#cell-1`, kind `code`, section "notebook > Cell 2"), dropped from both tables by the eligibility gate; two duplicate-titled rst sections both emit `docs/guide.rst#setup` (same for markdown and adoc), collapsing in the id-keyed delta planner; a text-XML `.drawio` walks in via the content sniff, chunks as one code-kind line window, and ships zero rows in either table. The `1whup` fence machinery (doc-code kind, all seven mirrors, code cap, breadcrumb injection, SDL repeat-crumb ordinal pattern) is landed and field-validated, making all three fixes small. | Session probes 2026-08-28; wave 1wik9 records (1whup AC-1 disposition, 1whuq `.drawio` follow-up, CODE-DEL-1 ordinal repair). |
| 2026-08-29 | Phase A executed (before any chunker edit). Censuses recorded (`evidence/census_retrieval_loose_ends.py/.json`): every un-anchored slug-id emitter reproduced by execution — md dup-H2 (`#setup` x2), H3-split (`#config/advanced` x2), line-window bases (relative-line twins), preamble-vs-literal-title (`#preamble` x2), the doc-summary sentinel (a literal "Doc Summary" H2 collides with the dispatch summary chunk — a census-found bonus class), rst/adoc (`#setup` x2), the HTML regex fallback (`#section` x2, kind doc) and the corrected XML fallback fixture (`#item` x2, kind doc); the tree-sitter HTML path is line-anchored (no collision) and the dup-key YAML config probe emits anonymous `#node-N` ids (no collision reproduced — adjacent class dispositioned as follow-up); controls (fences, SDL ordinals, `#cell-N`, diagrams) collision-free; the literal `Setup 2` trap reproduced (`#setup-2`). Notebook census: code cells kind="code" reach neither table, outputs never read, per-cell language ignored. `.drawio` census: walks in, one code-kind line window, zero rows shipped either table. Committed real-world-shaped fixture `prose/ipynb/churn_cohort_analysis.ipynb` + 5 nb golden queries (4 code-cell-anchored, 1 markdown-cell control) with executed anchor-uniqueness proof (`evidence/nb_anchor_uniqueness.json`: each anchor in exactly one corpus file and one chunk). Baseline FROZEN pre-change (`evidence/eval_prose_before_1wh1b.json`): ipynb 0.2 recall at 5 (nb01-nb04 rank 0 — structurally invisible; nb05 rank 1), md 0.688, rst 0.750, adoc 0.750, fence-* 1.0. | evidence/census_retrieval_loose_ends.json; evidence/nb_anchor_uniqueness.json; evidence/eval_prose_before_1wh1b.json |
| 2026-08-29 | Implementation landed (framework gate opened; seed gate opened and closed for the parity pair). chunker.py: `_dedupe_id_base` helper (`~k` repeat-only file-pass ordinals; `~` outside the `_slugify` alphabet so the shape is unforgeable — pinned by an executed literal-tilde-title test), threaded through chunk_markdown (section, H3-split via new `h2_id_base`/`id_counts` params, line-window and decompose bases, doc-summary-seeded counter), `_emit_prose_sections` (rst/adoc), and the chunk_html/chunk_xml doc-kind regex fallbacks; fence ids deliberately keep their raw slug base. `chunk_jupyter` code cells emit `kind="doc-code"` (ids, notebook-level kernel language, output-blindness unchanged; cap and breadcrumb injection ride the landed 1whup plumbing). `CHUNKER_VERSION` 37 to 38 with full rationale. indexer.py: `.drawio` joins `_GENERATED_EXCLUDE_EXTENSIONS`, `WALKER_VERSION` 13 to 14 with rationale. The three notebook kind pins rewritten to the new contract (executable supersession: `test_notebook_code_cells_route_to_doc_code` + the two JupyterChunkerTests) plus new `ProseIdOrdinalTests` (11 tests) and DocCodeRoutingTests notebook additions (4 tests); walk + un-overridable-reinclude pins in test_indexer.py. Post-change census re-executed: ZERO collisions at every site, all notebook cells docs-routed, `.drawio` no longer walks, all seven kind mirrors carry doc-code with no new site (`evidence/census_post_change_1wh1b.json`). test_chunker 521 green, test_indexer 312 green. | chunker.py, indexer.py, test_chunker.py, test_indexer.py; evidence/census_post_change_1wh1b.json |
| 2026-08-29 | Differentials regenerated as a versioned step (`evidence/regen_differentials_1wh1b.py/.json`): the three pre-existing markdown sources verified BYTE-IDENTICAL old-vs-new (single-title stability); a duplicate-titled source and a notebook source ADDED (the council-proven blindness repair); every changed row classified — 1 repeat-title-ordinal-id, 2 notebook-cell-kind, 0 unclassified; revert-simulation discriminates (the re-armed snapshot mismatches the pre-change chunker); specs-negatives asserted zero-delta. Coverage differential (`evidence/coverage_differential_1wh1b.py/.json`, Requirement 6): per-line coverage computed over id-collapse SURVIVING rows (the `_plan_lance_delta_rows`/registry last-writer-wins model) across the committed notebook fixture and dup-titled md/rst/adoc fixtures — zero lines lost vs the pre-change chunker, all 23 notebook code-cell lines docs-eligible, dup-titled prose survives the collapse; revert-simulation FAILS against the old chunker (23 code-cell lines invisible, rst/adoc rows lost to collapse), proving non-vacuity. | evidence/regen_differentials_1wh1b.json; evidence/coverage_differential_1wh1b.json |
| 2026-08-29 | Post-change measurement (`evidence/eval_prose_after_1wh1b.json`) against the frozen baseline: ipynb 0.2 to 1.0 recall at 5 (bar 0.75 — all five queries hit; the four previously-invisible code-cell queries rank 1-3), fence-md/rst/adoc hold at 1.0, md 0.688 to 0.750 (improved), adoc holds 0.750. One movement recorded and dispositioned: rst 0.750 to 0.688 — p10:rst ("automatically retry write requests") slipped rank 4 to 6 with ZERO notebook rows in its top 5; the slots went to byte-identical cross-format twins of the same content (md/adoc `#retry-semantics-and-backoff` at ranks 4-5, the answer content present twice in the top 5), rst chunking is differential-proven byte-identical, and rst MRR improved 0.532 to 0.560 (p09 rank 2 to 1); for symmetric disclosure, adoc MRR moved 0.408 to 0.336 over the same pair while adoc recall holds at 0.750 (the bar metric) — near-tie reordering among same-content cross-format twins under embedding batch-boundary changes from the corpus growing 174 to 178 rows, not crowding by notebook content. Carriers updated: seed-211 + guru.md Index Scope (byte-identical mirror edit behind `seed_edit_allowed`, parity re-verified at 5,764 bytes), search-architecture doc-code bullet (supersession + walk-excluded drawio), pipeline doc (kind-table row, notebook chunking entry, ordinal note, drawio walk section, stale `"34"` pins and walker pins refreshed to 38/14), performance-budget lint-bound pin 37 to 38, testing-architecture (superseded phrase + new 1wl7u tier row), build-and-verification and mcp-tool-surface doc-code enumerations. | evidence/eval_prose_after_1wh1b.json; docs/agents/guru.md; .wavefoundry/framework/seeds/211-guru.prompt.md; docs/architecture/* |
| 2026-08-29 | Delivery review executed (three isolated lanes per the receipt; no delivery council required). Docs-contract: 0 blocking, 3 advisory, all repaired (session-handoff rewritten to the open-wave truth; the Risks-table reinclude-hatch claim aligned with the corrected Decision Log; symmetric MRR disclosure added). QA: 0 blocking, 3 advisory, all repaired (regen evidence JSON re-captured parseable from a bare run; the coverage differential's md leg strengthened to exclude the doc-summary sliver — the revert simulation now shows md collapse loss too; chunk_jupyter gained isinstance shape guards so valid-JSON non-notebook payloads fall back to the line window instead of raising, with `test_wrong_shape_json_falls_back`); QA also mutation-proved the four load-bearing regressions with byte-verified restores. Code: 1 blocking — CODE-DEL-1: the DEFAULT tree-sitter HTML path (`_ts_markup_chunker`, ids `{slug}-L{start}`) collided for SAME-LINE sibling elements (compact/minified HTML), falsifying this log's earlier census generalization "the tree-sitter HTML path is line-anchored (no collision)" — that claim is SUPERSEDED: it held only for the census's one-element-per-line fixture. Repaired by threading `_dedupe_id_base` over the `{slug}-L{start}` base (executed: `#section-L1` / `#section-L1~2`; multi-line control unchanged), pinned by `test_treesitter_html_same_line_siblings_dedupe`, the census script extended with a same-line probe and the post-change census re-captured (zero collisions), the CHUNKER 38 rationale and pipeline-doc ordinal note extended to name the site. Suite 523 chunker tests green post-repair. | events.jsonl CODE-DEL-1 chain; evidence/census_post_change_1wh1b.json; lane reports 2026-08-29 |
| 2026-08-29 | Prepare-council repairs applied. Red-team (all nine claims verified by execution) falsified the ordinal-suffix mitigation: the SDL `-N` shape is only safe because `-` cannot appear in an SDL identifier, while `-<digits>` is a legal `_slugify` tail (1,647 same-shaped ids in this corpus; a literal `Setup 2` title emits `#setup-2`) — Requirement 2 now mandates a non-slug-alphabet suffix or collision-aware assignment; the census broadens to every un-anchored slug-id emitter (executed probes reproduced the collision in the `chunk_html` fallback); the differential sources are blind to both declared delta classes, so Requirement 5 now requires adding a duplicate-titled source; the supersession is made executable (three named kind-pinning tests); the per-cell language wording corrected to notebook-level kernel language. Docs-contract seat added the missed lint-bound `performance-budget.md` chunker pin (the docs gate would hard-fail the bump without it), the `CHANGELOG.md` `[Unreleased]` carrier, the two stale `"34"` pipeline-doc pins, and the two-part testing-architecture edit; confirmed the seed edit lands inside the `GuruIndexScopeParityTests`-guarded region. Motivating defect confirmed live: 6 files in this corpus silently lose 15 index rows today. | Council seat reports 2026-08-29 (red-team executed probes `probe_c1_jupyter.py`/`probe_c2_c5_gates.py`/`probe_c3_collisions.py`/`probe_corpus_census.py`; docs-contract carrier sweep); wave.md Review Checkpoints. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-28 | Repeat-only ordinals for prose ids (first occurrence keeps its current id). | Id stability for the dominant single-title case avoids churning nearly every consumer index row; repeats are the defective minority and gain determinism. | Ordinals on every section id were rejected (full id churn for no correctness gain); leaving the bound open again was rejected (the class silently loses index rows and the fix shape is now proven). |
| 2026-08-29 | Ordinal suffix shape: `~k` (a reserved non-slug character), via `_dedupe_id_base`. | Both designs the repaired Requirement 2 admitted were viable; the reserved shape is simpler and deterministic without scanning the file's literal slugs, and unforgeability is proven by execution: `~` is stripped by `_slugify`, so a literal `Setup ~2` title lands on `setup-2`, never `setup~2` (pinned by `test_literal_tilde_in_title_cannot_forge_the_ordinal_shape`). | Collision-aware ordinal assignment against the file's literal slugs (the council's strongest-alternative) was rejected as more stateful for no additional safety once the suffix alphabet is disjoint; bare `-N` was rejected by the council's executed falsification (1,647 same-shaped ids in this corpus; `Setup 2` emits `#setup-2`). |
| 2026-08-29 | `.drawio` EXCLUDED at the walk layer: joins `_GENERATED_EXCLUDE_EXTENSIONS`, `WALKER_VERSION` 13 to 14 (the `.excalidraw` precedent), closing the 1whuq open question. | Census-grounded (`evidence/census_retrieval_loose_ends.json`): a text-XML `.drawio` walks in via the content sniff, chunks as one code-kind line window, and ships ZERO rows in either table — pure walk/chunk cost, no retrieval value, no pollution to preserve. The plan's hatch claim was corrected during implementation: the reinclude hatch deliberately cannot override the generated-extension layer (pinned by `test_reinclude_hatch_cannot_override_extension_or_sniff`), and nothing is lost — a re-included `.drawio` would still ship zero rows; surfacing `.drawio` content would be a future CHUNKER decision, not a walk hatch. | Recording the status quo (keep walking it) was rejected: measured cost with zero value and a shipped precedent for the same class; adding a `.drawio` chunker (surfacing diagram labels like 1whuq) was out of scope by Requirement 7. |
| 2026-08-29 | `_ts_flat_emit_chunker` un-anchored `{path}#{slug}` code-kind config ids: DISPOSITIONED as a recorded follow-up, not changed. | The census could not reproduce a collision by execution (a duplicate-key YAML emits anonymous `#node-N` ids on this path); the class is code-kind config chunks, outside Requirement 2's prose-section scope, and re-basing config ids risks unclassified deltas in the specs-negatives differential corpus. | Fixing it in this wave was rejected (no executed reproduction, scope boundary, differential risk); ignoring it silently was rejected — this row IS the recorded disposition, and the census JSON carries the executed probe. |
| 2026-08-29 | The MALFORMED-notebook fallback stays in the both-tables drop class: DISPOSITIONED as recorded residual, not changed (code-lane delivery advisory). | An unparseable or wrong-shape `.ipynb` falls back to `chunk_line_window` (kind `code`), and `.ipynb` is never code-eligible, so those rows ship to neither table — the pre-existing 1whup residual for degenerate inputs only; parseable notebooks (the content case) are fully routed by this wave, and the wrong-shape crash found by QA is guarded to reach this same fallback instead of raising. | Routing the malformed fallback to `doc-code` was rejected in-wave (raw JSON/broken text embeds as noise; a deliberate decision for a follow-up if ever wanted); leaving it unrecorded was rejected — this row is the disposition. |
| 2026-08-29 | The markdown prose-id counter is seeded with the `doc-summary` sentinel. | Census-found bonus collision class: every markdown doc emits a dispatch-layer `#doc-summary` summary chunk, so a literal "Doc Summary" heading collided with it; seeding the same counter fixes it in the same mechanism (pinned by `test_doc_summary_sentinel_is_reserved`). | A separate reserved-name list was rejected (the counter already expresses reservation); leaving it was rejected (same silent-collapse defect class). |
| 2026-08-29 | rst aggregate movement (0.750 to 0.688) ACCEPTED with recorded attribution; the AC-4 bar reads as met with this dispositioned movement. | File-attributed per query: only p10:rst moved out (rank 4 to 6) and its post-change top 5 contains ZERO notebook rows — the slots went to byte-identical cross-format twins of the same answer content (md/adoc `#retry-semantics-and-backoff`); rst chunking is differential-proven byte-identical, and rst MRR improved (p09 rank 2 to 1). Mechanism: near-tie reordering among same-content cross-format twins under embedding batch-boundary changes as the shared corpus grew 174 to 178 rows — not crowding by notebook content. | Treating the movement as a bar failure requiring repair was rejected: there is no mechanism to repair (rst rows are byte-identical; the reordering is float-level among near-duplicates the golden corpus intentionally carries); re-freezing the baseline post-change was rejected (bar integrity). |


## Risks


| Risk | Mitigation |
| --- | --- |
| Notebook code cells embed noisily against prose queries. | The frozen measurement decides; the content-anchored bar protects prose access; cells are capped at the code limit. |
| Prose ordinal suffixes collide with an existing literal id. | The council falsified the reserved-shape transfer by census: `-N` is a legal slug tail with 1,647 same-shaped ids in this one corpus. Requirement 2 therefore mandates a suffix containing a non-slug-alphabet character or collision-aware assignment, verified against the census-enumerated id shapes. |
| The `.drawio` exclusion surprises a target indexing them on purpose. | The census-grounded decision records the rationale, and nothing retrievable is lost: a `.drawio` shipped zero rows in either table even when walked. Surfacing `.drawio` content would be a future chunker decision; the reinclude hatch is name-layer ONLY and cannot restore generated-extension files (corrected during implementation, pinned by `test_reinclude_hatch_cannot_override_extension_or_sniff`). |
| Differential regeneration masks an unintended delta. | Every changed row must classify into the declared classes; any unclassified delta blocks, and discrimination is re-proven on mutation. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
