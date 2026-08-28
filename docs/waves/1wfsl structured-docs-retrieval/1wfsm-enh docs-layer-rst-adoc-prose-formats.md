# Docs-Layer Support for reStructuredText and AsciiDoc

Change ID: `1wfsm-enh docs-layer-rst-adoc-prose-formats`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-27
Wave: `1wfsl structured-docs-retrieval`

## Rationale

The docs retrieval surface today INCLUDES markdown section chunks
(`chunker.MARKDOWN_EXTENSIONS`), plain-text files (`TEXT_EXTENSIONS`) and
extensionless documentation names (`DOCS_EXTENSIONLESS_NAMES`) routed to
`chunk_plain_text` as doc-kind chunks, doc chunks extracted from code docstrings and
comments (the 1sek8 dual-output union), and HTML/XML element text and notebook
markdown cells (the enumeration is deliberately non-exhaustive; kind-based routing
is the authority). What it does
NOT contain is reStructuredText or AsciiDoc: those files are admitted by the walk's
text sniff but no chunker emits doc-kind chunks for them and the code-corpus filter
drops them, so they produce zero retrieval rows. A target repository whose
documentation lives in Sphinx rst or AsciiDoc, which describes a large share of the
Python and JVM ecosystems, therefore gets no `docs_search` coverage over its actual
documentation, and Guru falls back to file reads.
These are pure prose formats that embed as well as markdown; the gap is format parsing,
not retrieval design. The markdown path's measured lever applies directly: section
breadcrumbs prepended to embedded chunk text produced a ten-point natural-language
retrieval improvement (the 1p4w9 note in the `CHUNKER_VERSION` history), and both rst and
adoc carry extractable heading structure (rst underline-adornment titles; adoc `=` prefix
titles). This is the highest-value coverage gap surveyed for wave `1wfsl` because it
concerns the primary documentation of entire target ecosystems rather than auxiliary spec
files.

## Requirements

1. The docs layer MUST chunk `.rst` and `.adoc` (plus `.asciidoc`) files wherever it
   chunks markdown today: the same corpus roots, the same doc kinds and tags, the same
   downstream `docs_search` and `code_ask` visibility, while existing markdown
   chunking remains byte-identical. No new configuration is required for the default
   docs roots; the include-prefix mechanics are unchanged.
2. Heading structure MUST drive section chunking with breadcrumb prefixes on embedded
   text, mirroring the markdown path: rst section titles recognized by
   underline-adornment (and overline where present), adoc titles by `=` run prefixes.
   Parsing is a bounded framework-internal implementation with no new third-party
   dependency; imperfect recognition degrades to larger plain-prose chunks, never to
   file exclusion.
3. Directive and macro noise MUST be bounded: rst directive bodies that are code or
   non-prose (`.. code-block::`, `.. image::`, tables of options) and adoc listing/source
   blocks chunk as code-kind or are size-bounded so they do not dominate prose ranking;
   inline roles and attribute references pass through as text.
4. The mechanism is chunker-owned, and the plan text names it precisely (readiness
   council correction: there is NO "docs-corpus extension set" in the indexer to
   extend). The change adds rst/adoc section chunkers emitting doc-kind chunks, which
   the existing kind-based layer routing (`_is_docs_kind`) then carries into the docs
   layer; `.rst`/`.adoc`/`.asciidoc` join `_KNOWN_TEXT_EXTENSIONS` so the sniff is
   skipped. `CHUNKER_VERSION` is bumped with the chunk-set-shape rationale (that bump
   drives the consumer re-chunk); `WALKER_VERSION` is bumped only under its
   filter-logic-change clause for the known-text registration, with the rationale
   naming that clause.
5. Adoption is measurement-checked, not assumed: a bounded golden query set over real rst
   and adoc corpora (drawn from real-world documentation trees, harness metric definitions per
   sibling `1wfr8-enh`) MUST record recall at 5 and mean reciprocal rank on matched
   markdown/rst/adoc query pairs, demonstrating quality comparable to the markdown
   path on equivalent content, with any gap recorded and dispositioned. This gate validates quality; coverage
   itself ships regardless because zero-coverage is strictly worse than plain-prose
   chunking.
6. Boundaries unchanged: machine-authority and secret-scan exclusions, the
   markdown-carrier guidance for non-prose data, and the code layer's extension set are
   untouched. `.txt` and extensionless documentation files keep their EXISTING
   plain-text doc-chunk path, unchanged by this change (readiness council correction;
   see the Decision Log row).

## Scope

**Problem statement:** entire documentation trees in rst and adoc are invisible to
semantic and lexical docs retrieval across target repositories.

**In scope:**

- `.wavefoundry/framework/scripts/chunker.py` (rst and adoc section chunkers, extension
  registration, `CHUNKER_VERSION` bump)
- `.wavefoundry/framework/scripts/indexer.py` (known-text extension registration and
  the walker-version bump under its filter-logic clause; layer routing itself is
  unchanged)
- `.wavefoundry/framework/scripts/tests/test_chunker.py` and
  `.wavefoundry/framework/scripts/tests/test_indexer.py` (section recognition, breadcrumb,
  directive-noise bounding, corpus-membership regressions with real-format fixtures)
- golden rst/adoc query fixtures and the recorded measurement
- `docs/architecture/search-architecture.md` and the testing-architecture tier row
- shipped guidance touch-up where the docs-layer format contract is stated (coordinate
  with sibling change `1wdvr-doc` so the final wording reflects the extended set)

**Out of scope:**

- `.txt`, Org-mode, MediaWiki, or any further prose format (future curated additions)
- third-party parser dependencies (docutils, asciidoctor)
- Sphinx cross-reference resolution, adoc include-file expansion, or any semantic link
  following
- code-layer or structured-format changes (sibling `1wfr8-enh`; parked plan
  `1wfso-enh`)

## Acceptance Criteria

- [x] AC-1: Real-world rst and adoc fixture files chunk into section units with correct
  breadcrumb prefixes; underline-adornment and `=`-prefix heading recognition are each
  covered by positive and negative tests (prose lines that merely resemble adornment do
  not split sections).
- [x] AC-2: Directive and listing noise is bounded by tests: a code-block-heavy rst file
  and a listing-heavy adoc file produce prose chunks whose embedded text is not dominated
  by non-prose bodies.
- [x] AC-3: Corpus-membership tests prove `.rst`/`.adoc`/`.asciidoc` files under docs
  roots produce doc-kind chunks that enter the docs layer and surface through
  `docs_search`, and the `WALKER_VERSION` (filter-logic clause) and `CHUNKER_VERSION`
  bumps carry their documented rationale lines.
- [x] AC-4: The recorded matched-pair golden-set measurement (recall at 5 and mean
  reciprocal rank per the `1wfr8-enh` harness definitions) exists as wave evidence,
  and the AC is discharged by that recording PLUS a disposition for any gap versus
  markdown; a missing measurement or an undispositioned gap blocks it.
- [x] AC-5: Existing markdown chunking is byte-identical (differential test), the full
  suite and docs gate pass, and the affected architecture docs are updated.

## Tasks

- [x] Collect real-world rst and adoc fixture corpora and author the golden query set.
- [x] Implement rst and adoc section chunkers with breadcrumbs and noise bounding; bump
  `CHUNKER_VERSION`.
- [x] Register `.rst`/`.adoc`/`.asciidoc` in `_KNOWN_TEXT_EXTENSIONS` (indexer.py) and
  bump `WALKER_VERSION` under its filter-logic clause.
- [x] Add section-recognition, noise-bounding, corpus-membership, and markdown
  differential regressions.
- [x] Record the golden-set measurement and its disposition.
- [x] Update architecture docs and coordinate the shipped-guidance wording with
  `1wdvr-doc`.
- [x] Run the canonical suite, docs gate, and hygiene checks.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixtures and golden set | performance-reviewer | none | Real-world corpora; freeze before measurement. |
| Chunkers and corpus wiring | implementer | Fixtures and golden set | Serialize chunker.py and indexer.py edits with sibling changes through one lane. |
| Regressions and differential proof | qa-reviewer | Chunkers and corpus wiring | Markdown byte-identity is the leak guard. |
| Measurement and docs | performance-reviewer, docs-contract-reviewer | Regressions and differential proof | Coordinate wording with `1wdvr-doc`. |


## Serialization Points

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `docs/architecture/search-architecture.md`
- Chunker and indexer edits serialize with sibling wave changes touching the same files;
  land the `1wdvr-doc` guidance wording after this change's extension set is settled or
  amend it in the same cycle.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`: docs-layer format set and the rst/adoc
  section-parsing contract.
- `docs/architecture/chunking-and-indexing-pipeline.md`: its chunking overview,
  doc-kind table, and markdown-chunking section state the docs-format set and must
  reflect the extension (readiness lane finding).
- `docs/architecture/testing-architecture.md`: chunker tier row gains the new-format and
  differential coverage.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Heading recognition is the whole lever; false splits corrupt every downstream chunk. |
| AC-2 | required | Directive noise domination would make coverage worse than absence for ranking. |
| AC-3 | required | Corpus membership and version-bump conventions are the consumer contract. |
| AC-4 | required | Quality parity must be observed, not assumed; shortfalls need recorded dispositions. |
| AC-5 | required | Markdown byte-identity, suite, and docs gates are standing requirements. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-27 | Planned from the wave 1wfsl survey: `MARKDOWN_EXTENSIONS` limits the docs layer to markdown; no rst/adoc handling exists anywhere in chunker or indexer (grep census); the breadcrumb lever has the measured 1p4w9 precedent; `.ipynb` already has a dedicated chunker path so notebooks are excluded from this gap. | chunker/indexer grep census in the wave planning session. |
| 2026-08-27 | Readiness lane correction: the row above's "`MARKDOWN_EXTENSIONS` limits the docs layer to markdown" phrasing was imprecise (plain-text, extensionless, docstring, HTML/XML element-text, and notebook-cell doc chunks are also in the docs surface); the Rationale carries the corrected non-exhaustive contract. | docs-contract readiness lane finding 3c. |
| 2026-08-27 | IMPLEMENTED under `framework_edit_allowed` (serialized lane): `chunk_rst`/`chunk_adoc` doc-kind section chunkers in chunker.py with breadcrumb labels, docutils-faithful title rules (column-0, blank-line-preceded, underline >= title length; overline form), adoc `=`-run titles outside delimited blocks; code directives and `[source]`/`----`/`....` blocks extract as code-kind; media/table directives drop; admonitions stay prose; unknown structure degrades to prose. `RST_EXTENSIONS`/`ADOC_EXTENSIONS` + dispatch after the markdown branch; `CHUNKER_VERSION` 32 to 33 with the chunk-set-shape rationale. indexer.py: `.rst`/`.adoc`/`.asciidoc` joined `_KNOWN_TEXT_EXTENSIONS`; `WALKER_VERSION` 12 to 13 under the filter-logic clause. Regressions: `RstChunkerTests`, `AdocChunkerTests`, `ProseFormatNoiseBoundingTests`, `MarkdownDifferentialTests` (byte-identity against a snapshot generated from the ACTUAL pre-change git-HEAD chunker over committed sources), and the corpus-membership walk test in test_indexer.py; test_chunker.py 452 tests and test_indexer.py 305 tests green. Architecture docs updated (search-architecture, chunking-and-indexing-pipeline overview/doc-kind-table/new section, testing-architecture tier row). | chunker.py/indexer.py/test diffs; focused runs `test_chunker.py — 452 ok`, `test_indexer.py — 305 ok`; `markdown_differential_expected.json` (HEAD chunker v32). |
| 2026-08-27 | MEASUREMENT recorded (harness per `1wfr8-enh` definitions; committed matched-trio corpus `prose/`, 16 queries x 3 formats; docs-layer mirror: doc-kind chunks only). BEFORE (git-HEAD chunker v32): md recall@5 0.875 / MRR 0.794; rst 0.0 / 0.0; adoc 0.0 / 0.0 — the true zero-coverage baseline. AFTER (chunker v33): rst 0.875 / 0.549 (recall MATCHES markdown); adoc 0.75 / 0.45; md 0.875 / 0.429. Dispositions: (1) queries p14/p15 miss in ALL three formats (rank 0 everywhere) — format-neutral query difficulty, not a format gap; (2) adoc's two format-specific misses (p08, p10) rank exactly 6, beaten by their own md/rst twins — cross-format twin competition in the tripled matched corpus, not an adoc parsing failure (the adoc chunks contain the answers); (3) the md MRR shift 0.794 to 0.429 is a corpus-composition artifact of the same twin competition (markdown chunks are byte-identical per the differential test; the competitive set tripled) — in a real repository documentation exists in one format. Quality comparable to markdown on matched pairs: demonstrated. | `evidence/retrieval_eval_prose_before.json`, `evidence/retrieval_eval_prose_after.json`; per-query tables therein. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-27 | Framework-internal section parsers for rst and adoc with breadcrumbed chunks; coverage ships, quality is measurement-checked. | The formats are pure prose with extractable heading structure, zero coverage is strictly worse than plain-prose chunking, and the breadcrumb lever has a measured precedent; no new dependency keeps the no-network and dependency-light contracts intact. | Index-time conversion to markdown via docutils/asciidoctor was rejected as new third-party dependencies with heavyweight failure modes; treating the files as plain text without headings was rejected as discarding the one measured lever; leaving the gap and documenting a manual-conversion workaround was rejected as pushing framework work onto every operator. |
| 2026-08-27 | `.txt` and extensionless documentation files keep their EXISTING plain-text doc-chunk path unchanged (readiness council correction: the original row wrongly described the status quo as excluding them). | They are already in the docs retrieval surface via `chunk_plain_text`; this change neither improves nor removes that path, and adding heading heuristics for plain text has no structure to exploit. | Removing `.txt` from the docs surface was rejected as an unrelated regression; adding structure heuristics for it was rejected as having no stable oracle. |


## Risks


| Risk | Mitigation |
| --- | --- |
| Adornment-style false positives split prose incorrectly. | Negative tests from real corpora; degrade to larger plain-prose chunks rather than aggressive splitting. |
| Walk-version bump re-walks every consumer index. | Documented convention; unchanged files re-embed nothing (content-hash reuse). |
| Directive-heavy Sphinx trees still rank noisily. | AC-2 bounding plus the AC-4 measurement gate with recorded disposition. |
| Wording drift against sibling `1wdvr-doc` guidance. | Explicit coordination task and wave watchpoint. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
