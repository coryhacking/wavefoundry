# Diagram Label Retrieval: drawio and excalidraw

Change ID: `1wl7v-enh drawio-excalidraw-label-retrieval`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-29
Wave: `1wl7w diagram-label-retrieval`

## Rationale

Operators document architecture in draw.io and Excalidraw, and those files carry the
same retrieval value the `1whuq` diagram formats shipped for: node, edge, and frame
labels are architecture prose. Today both extensions sit in
`_GENERATED_EXCLUDE_EXTENSIONS` (`.excalidraw` since the generated-files wave;
`.drawio` since wave `1wl7u`, whose census showed a walked file chunked as one
code-kind line window and shipped ZERO rows in either table). The `1wl7u` Decision
Log explicitly left surfacing the content as a future chunker decision; the operator
has now made that decision: their repositories hold real `.drawio` files.

Executed probes on the current tree (2026-08-29) ground the design. The canonical
draw.io compressed save (URL-encode, then raw deflate, then base64 inside the
`<diagram>` element) inflates with pure stdlib (`base64` + `zlib` at wbits -15 +
`urllib.parse.unquote`), and label extraction (diagram page `name` attributes plus
`mxCell` `value` attributes) returns identical results for the compressed and plain
forms; values can carry HTML markup (`<b>Billing queue</b>`), so tags and entities
must be stripped. The real Excalidraw schema yields text-element strings plus frame
`name`s by plain JSON traversal. Both formats pass the null-byte text sniff. Neither
raw serialization is readable prose (mxGraph geometry XML; Excalidraw coordinate
JSON), so unlike `1whuq` the chunk text must be the EXTRACTED labels, never the raw
source.

## Requirements

1. `.drawio` files MUST chunk into docs-routed `kind="doc-code"` label units: one
   chunk per `<diagram>` page, text = a breadcrumb line followed by the page's
   extracted labels in document order. Label sources are `mxCell` `value`
   attributes AND the `label` attributes of `object`/`UserObject` wrapper
   elements (the council's executed strongest challenge: draw.io's Edit Data
   feature serializes labeled cells as `<object label="X"><mxCell/></object>`,
   which value-only extraction parses cleanly and silently drops); a
   wrapper-bearing fixture makes the coverage oracle see the class. HTML
   handling is TWO decode layers: the XML attribute decode, then tag stripping
   plus `html.unescape`. The breadcrumb is the page `name` unless it matches the
   auto-generated `Page-N` pattern, in which case the file stem is used (a
   "Page-1" breadcrumb is noise, not retrieval value); `Chunk.language` is
   pinned to `drawio`. Ids ride the shipped `_dedupe_id_base` mechanism on the
   `diagram` base, so a single-page file emits `{path}#diagram` (the `1whuq`
   shape) and later pages emit `#diagram~2`, `#diagram~3`; oversized label sets
   split through the universal guard and the multi-part ids compose with the
   `~k` base (pinned by assertion). Compressed page bodies inflate via the
   stdlib chain behind an explicit per-page inflated-bytes cap at a concrete
   seam: a module constant applied through `zlib.decompressobj(...)
   .decompress(raw, cap)` whose eof/unconsumed-tail check detects over-cap
   inflation and returns nothing (the on-disk `MAX_INDEX_FILE_BYTES_DEFAULT` walk cap is
   useless against inflation; the council's executed 64 KB bomb inflates past
   10 MB). Raw source, geometry, and style strings are NEVER indexed.
2. `.excalidraw` files MUST chunk into docs-routed `doc-code` label units: one
   chunk per file, text = a file-stem breadcrumb line followed by text-element
   strings (`originalText` preferred, `text` fallback) and frame `name`s in
   document order; id `{path}#diagram`; `Chunk.language` pinned to `excalidraw`.
   Elements carrying `isDeleted: true` (text and frames alike) and
   empty/whitespace-only strings are SKIPPED, specified and pinned (the
   council's executed probe showed naive traversal leaks deleted ghost labels
   into the index). Element geometry, style properties, and the `files` blob
   (embedded images) are NEVER indexed.
3. Degenerate inputs MUST degrade to ZERO chunks, never to raw-source indexing:
   malformed XML/JSON, a failed or over-cap inflate, and a parse yielding no labels
   each emit nothing (net-identical to today's exclusion for that file). This is a
   deliberate departure from the `1whuq` stem-breadcrumbed-raw-text degrade,
   because these serializations are machine noise; the departure is recorded, not
   silent.
4. Walk re-admission MUST be an executable supersession: both extensions leave
   `_GENERATED_EXCLUDE_EXTENSIONS`, `WALKER_VERSION` bumps with a rationale naming
   the superseded exclusions (the `1wl7u` `.drawio` decision and the original
   `.excalidraw` exclusion), and every test pinning the exclusions flips to pin
   the re-admission in the same landing — on the indexer side
   `test_excludes_snap_and_excalidraw`, `test_excludes_drawio_as_generated`, the
   `GENERATED_EXT_LAYER` census rows, and the reinclude-hatch pins, AND on the
   chunker side the two pins the council census added:
   `test_excluded_formats_do_not_dispatch_to_diagram_chunker` (which asserts
   these exact extensions never produce `#diagram` ids — narrowed to the
   still-excluded `.d2`/`.dsl`) and `test_extensions_registered_chunker_only`
   (the extension-set and dispatch-disjointness census the new registration must
   join). The red-team census added three further supersession sites: the
   exact-version chunker ratchet test and its history docstring (gains the new
   transition line), the chunker's diagram-extension rationale comment stating
   the two formats "are excluded by decision" (becomes false), and the WALKER
   13-to-14 rationale prose whose "future CHUNKER decision" sentence the new
   rationale must name as superseded. After both flips the `GENERATED_EXT_LAYER`
   census fixture keeps `.snap` as its remaining member, so the layer pins stay
   non-vacuous. Registration is chunker-extension-gated; neither extension joins
   `_KNOWN_TEXT_EXTENSIONS` (the content sniff stays, per the `1whuq` precedent)
   or any code-eligibility set.
5. Measurement: extend the diagrams golden set with committed real-world-shaped
   fixtures — a compressed multi-page `.drawio` built by the canonical
   compression algorithm and carrying an `object label` wrapper, a plain-XML
   `.drawio`, and an `.excalidraw` with bound container text, a frame, and an
   `isDeleted` ghost — plus at least 4 queries per format whose anchors are
   proven unique within the corpus, FROZEN with a recorded structurally-zero
   baseline before the chunker edit. The bar: at least 0.75 recall at 5 per new
   format after the change, AND the existing mermaid/plantuml/dot diagram
   queries hold their 1.0 baseline, with any movement file-attributed and
   dispositioned. Readout: the diagrams eval branch computes ONE aggregate
   (council-verified; the specs branch's per-format id-prefix grouping was never
   mirrored), so this wave adds that grouping to the diagrams branch, id-prefix
   keyed exactly like the specs branch, metrics themselves unchanged — the
   narrow harness exception to the boundary, admitted here explicitly.
6. Version and differential discipline: `CHUNKER_VERSION` bumps with the
   documented rationale; the markdown and specs-negatives differentials are
   asserted zero-delta (no shared formats); the kind-mirror sweep is re-executed
   to verify `doc-code` needs no new mirror site (verified, never assumed); and a
   label-coverage differential proves every authored label in the fixtures
   appears in a docs-table-eligible chunk, non-vacuous by revert-simulation.
   Per-line coverage deliberately does not apply: not indexing geometry lines is
   the design, and the recorded coverage oracle is label-level. Claims-engine
   sequencing (council finding): the standing `[Unreleased]` bullet claims
   `CHUNKER_VERSION` 38 and `WALKER_VERSION` 14, and the docs gate machine-checks
   those numerals against the live constants on every full run, so the numeral
   refresh MUST land in the same working state as the version bumps — never
   deferred to the final carrier pass — or every intermediate docs-gate run
   fails.
7. Boundaries: no embedded-image or OCR extraction; no dual-extension handling
   for `.drawio.png`/`.drawio.svg` or `.excalidraw.png`/`.excalidraw.svg`
   exports (those are `.png`/`.svg` files and stay on their existing paths —
   recorded non-goal); no Miro support (boards are cloud-resident with no open
   on-disk format; committed API-export JSON would already walk as plain JSON
   today — recorded non-goal); no change to the on-disk
   `MAX_INDEX_FILE_BYTES_DEFAULT` walk cap, with the consequence DISCLOSED: an
   `.excalidraw` whose embedded-image `files` blob pushes it past the cap stays
   walk-invisible with no degrade signal (recorded limitation, not silent); no
   reranker, embedder, or metric changes beyond the Requirement 5 grouping
   readout; prompt-kind and seed markdown behavior untouched.

## Scope

**Problem statement:** draw.io and Excalidraw diagrams in operator repositories are
invisible to retrieval; their labels are architecture prose the docs index should
serve, exactly as it now serves Mermaid/PlantUML/DOT.

**In scope:**

- `.wavefoundry/framework/scripts/chunker.py` (drawio/excalidraw label chunkers,
  dispatch registration, `CHUNKER_VERSION`)
- `.wavefoundry/framework/scripts/indexer.py` (generated-set removal,
  `WALKER_VERSION`)
- `.wavefoundry/framework/scripts/tests/test_chunker.py` and `test_indexer.py`
  (extraction shape, compression, degenerate, walk-supersession, and coverage
  regressions)
- `.wavefoundry/framework/scripts/tests/fixtures/retrieval_golden/diagrams/`
  (drawio/excalidraw fixtures, golden queries, frozen baseline)
- docs-layer contract carriers: seed
  `.wavefoundry/framework/seeds/211-guru.prompt.md` plus its `docs/agents/guru.md`
  parity mirror (behind `seed_edit_allowed`; the walk-excluded sentence in the
  `GuruIndexScopeParityTests`-guarded `## Index Scope` region becomes false and
  the mirror edit is byte-identical), `docs/contributing/build-and-verification.md`
- `docs/architecture/search-architecture.md`,
  `docs/architecture/chunking-and-indexing-pipeline.md`,
  `docs/architecture/testing-architecture.md`
- `docs/architecture/performance-budget.md` (lint-bound chunker pin) and
  `CHANGELOG.md` `[Unreleased]` (the `1wl7u` `.drawio`-exclusion bullet is still
  unreleased and is AMENDED to the net story rather than left contradicting this
  wave; the claims engine machine-checks the numerals)

**Out of scope:**

- Embedded images, OCR, `.drawio.png`/`.drawio.svg` dual extensions
- Miro or any cloud-resident board service
- The legacy `.rtb` format
- Indexing raw diagram serializations (geometry, styles, coordinates)
- Reranker, embedder, or harness metric changes

## Acceptance Criteria

- [x] AC-1: Extraction tests prove compressed and plain `.drawio` pages emit
  identical docs-routed `doc-code` label units — including `object`/`UserObject`
  wrapper `label` attributes and the two-layer HTML decode — with page-name
  breadcrumbs (file stem when the name matches the `Page-N` auto pattern),
  pinned `language` values, `#diagram`/`#diagram~k` ids whose oversized
  multi-part splits compose with the `~k` base, and `.excalidraw` files emit one
  labels-plus-frames unit; raw serialization content (geometry, styles,
  coordinates) appears in no chunk text.
- [x] AC-2: The decompression cap is pinned by a hostile over-cap fixture
  (on-disk small, inflating past the cap) that degrades to zero chunks through
  the bounded `decompressobj` seam; every degenerate class (malformed XML/JSON,
  failed inflate, label-free parse) emits zero chunks, never raw-source windows;
  and `isDeleted` elements and empty strings are pinned as skipped.
- [x] AC-3: Both extensions walk again with the exclusion pins flipped to
  re-admission pins in the same landing, `WALKER_VERSION` carries the
  supersession rationale, and neither extension joins `_KNOWN_TEXT_EXTENSIONS`
  or any code-eligibility set.
- [x] AC-4: The frozen per-format golden queries meet the Requirement 5 bar with
  the existing diagram queries holding 1.0, readable per format off the
  committed result JSON via the id-prefix grouping added to the diagrams eval
  branch, recorded as wave evidence with movements dispositioned.
- [x] AC-5: The label-coverage differential proves every authored fixture label
  is docs-table-eligible, non-vacuous by revert-simulation; the markdown and
  specs-negatives differentials are asserted zero-delta.
- [x] AC-6: `CHUNKER_VERSION` carries its rationale, the kind-mirror sweep is
  re-executed and recorded, contract carriers are updated behind their gates
  (seed parity byte-identical; the lint-bound performance-budget pin and the
  `[Unreleased]` amendment land with matching numerals), and the full suite and
  docs gate pass.

## Tasks

- [x] Author the real-world-shaped fixtures (canonical compressed multi-page
  drawio carrying an `object label` wrapper, plain drawio, excalidraw with bound
  text, a frame, and an `isDeleted` ghost) and golden queries with uniqueness
  proof; add the diagrams-branch per-format grouping; freeze and record the
  structurally-zero baseline.
- [x] Implement the drawio and excalidraw label chunkers (stdlib inflate chain
  with the decompression cap, HTML stripping, `_dedupe_id_base` page ids) and
  dispatch registration; bump `CHUNKER_VERSION`.
- [x] Re-admit both extensions at the walk layer; bump `WALKER_VERSION` with the
  supersession rationale; flip the exclusion pins to re-admission pins; refresh
  the `[Unreleased]` version numerals in the SAME landing as the bumps (the
  claims engine checks them on every docs-gate run).
- [x] Add extraction, compression-cap, degenerate, walk-supersession, and
  label-coverage regressions; assert the markdown and specs-negatives
  differentials zero-delta.
- [x] Run the post-change measurement against the bar; disposition movements.
- [x] Update contract carriers (seed-211 + guru.md behind the gate, architecture
  docs, performance-budget pin, `[Unreleased]` amendment); run the canonical
  suite and docs gate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixtures and golden queries | performance-reviewer | none | Baseline frozen before any chunker edit; fixtures built by the canonical producers' algorithms, never hand-shaped approximations. |
| Chunkers and walk re-admission | implementer | Fixtures and golden queries | chunker.py serialized through one lane; the walk supersession lands with the chunkers, never separately. |
| Regressions and differentials | qa-reviewer | Chunkers and walk re-admission | The decompression-cap hostile fixture is the security-relevant pin. |
| Measurement and carriers | performance-reviewer, docs-contract-reviewer | Regressions and differentials | Seed edits behind the gate with byte-parity discipline. |


## Serialization Points

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/seeds/211-guru.prompt.md`
- `docs/agents/guru.md`

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`: the doc-code kind bullet's diagram
  clause gains the two extraction formats and drops the walk-excluded framing
  (the `.d2`/`.dsl` "stay out by decision" clause remains true and survives).
- `docs/architecture/chunking-and-indexing-pipeline.md`: the diagram section
  gains the extraction family (labels, compression chain, cap, degrade-to-zero);
  the doc-code kind-table row gains the new formats; the walker and chunker pins
  refresh.
- `docs/architecture/testing-architecture.md`: a NEW tier row for this wave's
  regressions AND the existing 1wl7u row's now-falsified `.drawio` exclusion
  clause reworded to superseded framing (the 1wl7u-rewrote-the-1whup-row
  precedent).
- `docs/architecture/performance-budget.md`: the lint-bound chunker pin.
- `docs/specs/mcp-tool-surface.md`: the `docs_search` doc-code enumeration gains
  the extraction formats (completeness, not falsity; the non-exhaustive hedge
  lives elsewhere in the file).

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The extraction shape is the delivered feature; identical compressed/plain output is the format-fidelity core. |
| AC-2 | required | The decompression cap is a security boundary; degrade-to-zero is the recorded design departure from 1whuq. |
| AC-3 | required | Silent supersession of shipped exclusion decisions is the drift class this project treats as blocking. |
| AC-4 | required | Retrieval changes ship only with recorded measurements on frozen sets. |
| AC-5 | required | Golden sets alone cannot see label loss; the differential is the oracle. |
| AC-6 | required | Version discipline and carrier truth are standing requirements. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-29 | Phase A executed (before any chunker edit). Fixtures built through the CANONICAL producer algorithms (`evidence/build_fixtures_1wl7v.py`): a compressed multi-page drawio (URL-encode, raw deflate, base64 per page) carrying an `object label` wrapper and an HTML-tagged value, a plain-XML drawio with the auto `Page-1` name, and a real-schema excalidraw with bound container text, a frame, an `isDeleted` ghost sentinel, and an empty-string element. Nine golden queries added (5 drawio, 4 excalidraw) with prefix-grouped ids; the diagrams eval branch gained the per-format id-prefix grouping (mirroring the shipped specs branch; the one admitted harness change) BEFORE the freeze. Baseline FROZEN (`evidence/eval_diagrams_before_1wl7v.json`): core d01-d09 hold 1.0/1.0 with the new fixtures in the corpus; drawio 0.0 and excalidraw 0.0 (structurally zero). Raw-text anchor scan recorded (`evidence/nb_anchor_uniqueness_raw.json`; compressed drawio anchors are raw-invisible by design, proven at chunk level below). | evidence/build_fixtures_1wl7v.py; evidence/eval_diagrams_before_1wl7v.json |
| 2026-08-29 | Implementation landed in ONE claims-safe landing (framework gate; seed gate opened and closed for the parity pair). chunker.py: `DRAWIO_EXTENSIONS`/`EXCALIDRAW_EXTENSIONS`/`DRAWIO_MAX_INFLATED_BYTES`, `_drawio_clean_label` (two-layer HTML decode with a tag-shaped-only strip so a literal `a < b` survives), `_drawio_page_model` (nested-element plain form; the compressed form through the bounded `decompressobj(raw, cap)` seam with the eof/unconsumed-tail over-cap check), `chunk_drawio` (per-page units, wrapper labels, auto `Page-N` stem fallback, `_dedupe_id_base` page ids) and `chunk_excalidraw` (originalText preference, isDeleted and empty skipping, files blob never read), dispatch branches after the 1whuq family; `CHUNKER_VERSION` 39 with rationale; the 1whuq extension-comment supersession. indexer.py: both extensions leave `_GENERATED_EXCLUDE_EXTENSIONS` (`.snap` remains), `WALKER_VERSION` 15 naming both superseded rationales. SAME landing: `[Unreleased]` amended to the net story with the 39/15 numerals, performance-budget pin, pipeline pins (claims check verified green). Executed smoke: wrapper label and HTML-stripped value extracted, `#diagram`/`#diagram~2`, auto-name stem fallback, ghost skipped, bomb/malformed/label-free/wrong-shape all zero chunks, both files walk and route to docs. | chunker.py; indexer.py; CHANGELOG.md [Unreleased]; claims check [] |
| 2026-08-29 | Pins flipped and regressions landed: `test_excludes_snap_keeps_generated_layer_non_vacuous` + `test_readmits_drawio_and_excalidraw_with_extraction` replace the two exclusion pins (WALKER >= 15), `GENERATED_EXT_LAYER` keeps `.snap`, the reinclude pin drops the drawio row, `test_extensions_registered_chunker_only` gains the extraction sets in the disjointness census, `test_excluded_formats_do_not_dispatch_to_diagram_chunker` narrows to `.d2`/`.dsl`, the version ratchet moves to 39 with the history line. New `DrawioChunkerTests` (10) and `ExcalidrawChunkerTests` (5): form equivalence, wrapper labels, two-layer decode, multi-page ids, auto-name fallback, the under-disk-cap deflate bomb, degenerate zero classes, docs membership/language/cap, oversized-split composition, injection idempotence, committed-fixture pins incl. the ghost. test_chunker 538 green, test_indexer 312 green. Label-coverage differential (`evidence/label_coverage_1wl7v.py/.json`): every authored label docs-eligible, ghost never leaks, compressed/plain identical by executed re-inflation, all 9 chunk-level anchors unique, revert-simulation FAILS against the pre-change chunker (4 violations) proving non-vacuity. | test_chunker.py; test_indexer.py; evidence/label_coverage_1wl7v.json |
| 2026-08-29 | Carriers updated: seed-211 + guru.md Index Scope (byte-identical mirror edit behind `seed_edit_allowed`; twins byte-identical: 5,931 bytes by the parity oracle's heading-inclusive extraction (5,916 excluding the heading line), 18 parity tests green) now teach the extracted-label contract; search-architecture doc-code bullet (supersession of both walk exclusions, per-page/per-board units, bomb cap); pipeline doc (diagram-section extraction family, kind-table row, 39/15 pins); build-and-verification and mcp-tool-surface enumerations; testing-architecture (1wl7u row supersession clause + new 1wl7w tier row). | docs/agents/guru.md; .wavefoundry/framework/seeds/211-guru.prompt.md; docs/architecture/*; docs/specs/mcp-tool-surface.md |
| 2026-08-29 | Post-change measurement (`evidence/eval_diagrams_after_1wl7v.json`) against the frozen baseline: drawio 0.0 to 1.0 recall at 5 and excalidraw 0.0 to 1.0 (bar 0.75 per format — every one of the nine new queries ranks its diagram FIRST, including the object-wrapper query drawio-q03), and the existing mermaid/plantuml/dot core holds exactly 1.0/1.0. Zero movements to disposition. Full framework suite green: 7,685 tests (was 7,670 pre-wave); docs gate green with the amended `[Unreleased]` numerals machine-verified. | evidence/eval_diagrams_after_1wl7v.json; evidence/full_suite_1wl7v.log (7,685 OK) |
| 2026-08-29 | Kind-mirror sweep re-executed and recorded (`evidence/kind_mirror_sweep_1wl7v.json`): both new chunkers emit the landed `doc-code` kind and every kind-keyed mirror carries it (`_is_docs_kind`, the eval harness `_DOCS_KINDS`, `DOCS_SEARCH_KINDS`, `_doc_matches_kind`, `_DOCS_BREADCRUMB_KINDS`) — no new mirror site needed, verified not assumed. Note recorded: the census's two source-string tuple probes (`code_ask` partition literals) count zero because those literals changed shape in an earlier wave; the kind-keyed mirrors and the shipped doc-code kind-filter regressions are the live verification, and the stale probe expression is noted for the next census author. | evidence/kind_mirror_sweep_1wl7v.json |
| 2026-08-29 | Delivery review executed: three lanes plus the REQUIRED delivery council (red-team fixed seat; the isolated docs-contract lane report as the rotating-seat evidence). Docs-contract 0 blocking / 4 advisory, all repaired (session-handoff truth, dual-convention parity byte figure, durable suite-log evidence copy, `MAX_INDEX_FILE_BYTES_DEFAULT` name). Code 0 blocking / 2 advisory (wrapped-base64 page drop; fictional line anchors on synthesized oversized units). Council red-team seat APPROVE with the whole-repo 2,025-file sweep crash-free and collision-free for the new formats, the WALKER 14-to-15 rebuild seam verified by symbol and execution, and two advisories: the small-corpus recall lenience (the honest signal is MRR 1.0, rank 1 on all 18 queries over content-anchored corpus-unique anchors with diverse top-5 competitors) and the PRE-EXISTING `_ts_flat_emit_chunker` id-collapse class now QUANTIFIED at 151 colliding ids / 565 dedupe losses in css/js/toml — the recorded 1wh1b follow-up, untouched by this wave, magnitude carried into its record. QA 1 BLOCKING (QA-DEL-1) / 3 advisory; mutants a/b/d killed with sha-verified restores; the eval independently re-verified exactly; fixtures byte-identical to the canonical builder output. | lane and council reports 2026-08-29; events.jsonl QA-DEL-1 chain |
| 2026-08-29 | QA-DEL-1 repaired in one landing with the advisories. The blocking oracle gap: the delivered bomb's truncated inflate failed XML parse, so the ParseError fallback redundantly enforced zero-chunks and a mutant deleting the eof/unconsumed-tail cap guard survived 538+312 tests. Repair: `test_escape_aligned_overcap_page_is_refused` encodes QA's non-equivalence witness (the quoted model padded to a 3-byte `%0A` boundary then past the cap, so the truncated-at-cap prefix is VALID XML and only the guard can refuse it) — executed mutant-kill proof: the guard-removed mutant indexes the sentinel while the tree refuses it. Same landing: whitespace-stripped strict base64 decode with `test_wrapped_base64_body_still_extracts` (MIME 76-column reflow now extracts identically); split-part line METADATA clamped to the parent file span for the synthesized drawio/excalidraw kinds only (ids keep raw window numbers for uniqueness; existing corpus shapes byte-identical) with `test_synthesized_split_line_metadata_stays_within_the_file`; the two QA degenerate pins (`test_whitespace_only_page_body_emits_nothing`, `test_typeless_and_malformed_elements_are_skipped`); and the label-coverage revert gate tightened to require BOTH formats failing (`formats_failing: [drawio, excalidraw]`, regenerated evidence). QA-3 (the coverage script's HEAD-dependence) is dispositioned as correctly-disclosed point-in-time evidence: a post-commit re-run self-fails by construction and must not be read as a regression. test_chunker 543 green. | test_chunker.py; chunker.py; evidence/label_coverage_1wl7v.json (per-format gate) |
| 2026-08-29 | Prepare-council repairs applied (both seats PASS-WITH-REPAIRS; the first red-team attempt was killed by a host sleep and retried clean). Red-team verified all eight claim families by execution and found: `object`/`UserObject` wrapper labels silently dropped by value-only extraction (Requirement 1 now names them and the fixture carries one); `isDeleted` ghost labels and empty strings leak through naive traversal (Requirement 2 now pins skipping); the on-disk walk cap is useless against inflation (an executed 64 KB bomb inflates past 10 MB; Requirement 1 now names the bounded `decompressobj` seam); the diagrams eval branch has no per-format readout (Requirement 5 admits the narrow id-prefix grouping); three more supersession pin sites (version ratchet test, chunker rationale comment, walker rationale prose) join the Requirement 4 census; auto `Page-N` breadcrumbs fall back to the stem; language values pinned; export dual-extensions symmetrized; over-cap boards disclosed as walk-invisible. Docs-contract found the claims-engine red window (the `[Unreleased]` numeral refresh MUST ride the version-bump landing or every intermediate docs gate fails — Requirement 6 and the walk task now state it), the two chunker-side pins missing from the census, the 1wl7u testing-architecture row needing superseded framing, the pipeline kind-table row, and the mcp-tool-surface completeness edit; parity twins verified byte-identical with the falsified walk-excluded sentence located inside the guarded region. | Council seat reports 2026-08-29; wave.md Review Checkpoints |
| 2026-08-29 | Planned from executed probes on the current tree (operator instruction: "let's do a wave for these formats"; operator confirms real `.drawio` files in their repositories). Probe results: the canonical compressed draw.io body inflates via stdlib (`base64` + `zlib` wbits -15 + `unquote`) and label extraction returns identical results for compressed and plain forms including HTML-tagged values; the real Excalidraw schema yields text strings and frame names by JSON traversal; both extensions currently sit in `_GENERATED_EXCLUDE_EXTENSIONS`, in no other membership set, and would line-window as zero-row kind="code" if walked. Miro raised and dispositioned as a non-goal (cloud-resident, no open on-disk format). | Session probes 2026-08-29; 1wl7u Decision Log (`.drawio` exclusion with extraction left as a future chunker decision); 1whuq records (diagram unit shape, sniff-precedent) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-29 | Chunk text is the EXTRACTED labels, never the raw serialization; degenerate inputs emit zero chunks. | mxGraph XML and Excalidraw JSON are machine noise that would embed badly and pollute prose ranking; a degenerate file emitting nothing is net-identical to today's exclusion, so nothing regresses. | The 1whuq raw-source degrade was rejected for these formats (raw source is unreadable geometry, unlike Mermaid/PlantUML text); indexing raw source behind the code cap was rejected (noise with no anchor value). |
| 2026-08-29 | Per-page `.drawio` ids ride `_dedupe_id_base` on the `diagram` base (`#diagram`, `#diagram~2`). | Single-page files keep exact 1whuq id parity; multi-page files get deterministic collision-free ids through the mechanism wave 1wl7u just shipped and mutation-proved, rather than a new ordinal scheme. | A page-index suffix (`#diagram-p2`) was rejected (a second ordinal grammar for no gain); one chunk per file concatenating pages was rejected (page names are breadcrumb value and long boards would hit the cap as one blob). |
| 2026-08-29 | Miro is a recorded non-goal. | Boards are cloud-resident behind a REST API; Wavefoundry is local-only by principle, and there is no open on-disk format to target. Committed API-export JSON already walks as plain JSON today. | Building an API importer was rejected (violates the no-network principle for indexing); waiting for a committed-export corpus with a stable schema is the revisit condition. |


## Risks


| Risk | Mitigation |
| --- | --- |
| A hostile `.drawio` carries a decompression bomb. | The inflate chain enforces a bounded inflated-bytes cap and degrades to zero chunks past it; a hostile fixture pins the cap (AC-2). |
| Extracted labels embed noisily against existing diagram or prose queries. | The frozen measurement decides: the existing mermaid/plantuml/dot queries must hold 1.0, and per-set-disjoint corpora keep prose aggregates untouched. |
| Real-world drawio variants diverge from the fixtures (mxlibrary, incomplete saves). | Detection is extension-plus-parse: anything the bounded parser cannot read degrades to zero chunks; fixtures are built by the canonical producers' algorithms, and the operator's real files are the first field validation. |
| The walk re-admission surprises a target that relied on the exclusion. | The reinclude story is one-directional and stated in the notes: files return only WITH extraction value, raw source stays unindexed either way, and `WALKER_VERSION` forces the deliberate re-walk. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
