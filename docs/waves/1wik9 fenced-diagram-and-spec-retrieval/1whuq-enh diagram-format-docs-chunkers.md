# Docs-Layer Chunkers for Standalone Diagram Files

Change ID: `1whuq-enh diagram-format-docs-chunkers`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-27
Wave: `1wik9 fenced-diagram-and-spec-retrieval`

## Rationale

Standalone hand-authored diagram files produce zero retrieval rows today, verified by
executed probe at the wave `1wfsl` close-out: `.mmd`, `.mermaid`, `.puml`,
`.plantuml`, `.dot`, and `.gv` appear in NO extension set (`SOURCE_CODE_EXTENSIONS`,
`_KNOWN_TEXT_EXTENSIONS`, `BINARY_EXTENSIONS`, `_GENERATED_EXCLUDE_EXTENSIONS` all
report false), so they walk in through the content sniff, fall to the unknown-type
line-window fallback as code-kind chunks, and the code-corpus extension gate then
drops them from every table. This is the same zero-coverage class reStructuredText
and AsciiDoc were in before `1wfsm-enh` closed it.

The content is worth retrieving: Mermaid, PlantUML, and Graphviz DOT are
hand-authored text whose node, edge, and subgraph labels are natural-language
architecture statements ("Auth Service validates Token Store"). Architecture
questions are a primary Guru query class, and a repository whose architecture lives
in diagram files gets no docs coverage over it. Tool-generated diagram formats are a
different class and are not adopted: `.excalidraw` is walk-excluded via
`_GENERATED_EXCLUDE_EXTENSIONS`, while `.drawio` (tool-generated XML) is in no
extension set today and is merely invisible by the corpus gate; this change adopts
neither, and whether `.drawio` should join the generated-exclusion set is a recorded
follow-up question, not assumed.

## Requirements

1. The docs layer MUST chunk the curated hand-authored diagram formats: Mermaid
   (`.mmd`, `.mermaid`), PlantUML (`.puml`, `.plantuml`), and Graphviz DOT (`.dot`,
   `.gv`). Each file emits docs-routed chunks (kind per the sibling `1whup-enh`
   decision: `doc-code` when that change lands first, else `doc` with a recorded
   follow-up to converge) carrying a breadcrumb line (diagram title where the format
   declares one, else the file stem) followed by the raw diagram source. Label
   extraction beyond breadcrumb-plus-source is NOT in scope unless the measurement
   demands it; the raw source already contains every label.
2. Registration is CHUNKER-ONLY (readiness code-lane correction of the planned
   `1wfsm` transfer): the six extensions MUST NOT join `_KNOWN_TEXT_EXTENSIONS`,
   because that registration is a content-sniff BYPASS, and `.dot` has a binary
   namesake (legacy Word templates: OLE compound files full of null bytes that the
   sniff excludes today and that would otherwise walk in as mojibake docs rows).
   Hand-authored text diagram files already pass the sniff, so walk membership is
   unchanged and NO `WALKER_VERSION` bump applies; the chunker dispatch registration
   (extension constants plus the dispatch branch) is what delivers the chunks, and
   the chunk-set change bumps `CHUNKER_VERSION` with its rationale line. A
   binary-impostor `.dot` fixture (null-byte header) is pinned in the
   degenerate-input tests as walk-excluded.
3. An EXECUTED census MUST record docs-table eligibility for diagram files in and
   out of docs roots. The council's executed probe already established the polarity:
   default docs eligibility is WHOLE-REPO outside the `.wavefoundry/` blanket (the
   docs include-prefixes are only the framework-fold entries and only re-include
   inside the blanket), so `docs/diagrams/x.mmd` and `src/x.mmd` are BOTH
   docs-eligible once they emit docs-routed chunks. The census re-executes and pins
   that result, and the shipped guidance states it plus the one real boundary
   (`.wavefoundry/`-nested diagram files need the include-prefix opt-in).
4. Oversized and degenerate inputs degrade, never exclude: files over the chunk caps
   split through the universal guard; unparseable or title-less files chunk as
   breadcrumbless source text. Detection is by extension only (no content sniffing of
   ambiguous extensions), and `.drawio`, `.excalidraw`, `.d2`, and Structurizr `.dsl`
   are explicitly out with the rationale recorded (tool-generated XML, already
   excluded, small ecosystem share, and an ambiguous extension respectively).
5. Coverage invariant (the `1wfsl` ARCH-DEL-1 lesson): no currently-retrievable file
   may lose coverage. Today's baseline for these extensions is zero rows, so the
   invariant reduces to a differential proving files with OTHER extensions chunk
   byte-identically to the pre-change chunker.
6. Adoption is measurement-checked with the wave `1wfsl` harness and its fixed
   metrics: a committed golden subset of at least 9 label-targeted queries (3 per
   format family) over real-world-shaped diagram fixtures, frozen at baseline, with
   each anchor proven unique to its expected file. The set mechanism is named
   explicitly (qa readiness lane): a new `diagrams` set in the harness (its own
   corpus directory and query file, a minimal `--set` addition scoped here), so the
   existing prose and specs corpora stay per-set disjoint and their frozen queries
   cannot regress from these fixtures; the existing prose golden aggregates are
   re-run once post-landing and MUST stay at or above their frozen baselines.
   Coverage itself ships regardless because zero-coverage is strictly worse than
   plain-text chunking (the `1wfsm` precedent); the recorded measurement validates
   quality and any gap is dispositioned.

## Scope

**Problem statement:** hand-authored architecture diagrams in standalone files are
invisible to semantic and lexical docs retrieval across target repositories.

**In scope:**

- `.wavefoundry/framework/scripts/chunker.py` (diagram dispatch, breadcrumb
  extraction, extension constants, `CHUNKER_VERSION` bump)
- `.wavefoundry/framework/scripts/tests/test_chunker.py` and `test_indexer.py`
  (per-format chunk shape, breadcrumb, corpus membership, eligibility-boundary,
  binary-impostor `.dot` sniff-exclusion, and differential regressions with
  real-format fixtures; no indexer source change ships: registration is
  chunker-only per Requirement 2)
- diagram fixture corpora, the golden query subset, and the minimal `diagrams`
  set addition to the harness under
  `.wavefoundry/framework/scripts/tests/fixtures/retrieval_golden/`
- `docs/architecture/search-architecture.md`, the pipeline doc's format tables, the
  testing-architecture tier row, and ALL FOUR docs-layer contract sentence carriers
  (seed 211 plus its guru.md byte-parity mirror behind `seed_edit_allowed`,
  `docs/contributing/build-and-verification.md`, and the `docs_search` rows of
  `docs/specs/mcp-tool-surface.md`): the non-exhaustive format list gains the
  diagram families

**Out of scope:**

- `.drawio`, `.excalidraw`, `.d2`, Structurizr `.dsl`, and any further diagram format
  (future candidates through the same curated gate)
- label extraction, layout parsing, or diagram semantics beyond
  breadcrumb-plus-source
- embedded diagram fences inside markdown (sibling change `1whup-enh` owns that
  routing)
- third-party diagram parser dependencies

## Acceptance Criteria

- [x] AC-1: Real-format fixture files for all three families chunk into docs-routed
  units with correct breadcrumbs (declared title where present, file stem otherwise),
  with deterministic identities, covered by positive and degenerate-input tests.
- [x] AC-2: Corpus-membership tests prove the six extensions produce docs-table rows
  under docs roots AND out of them (the executed eligibility census pins the
  whole-repo polarity and the `.wavefoundry/` boundary), a binary-impostor `.dot`
  stays walk-excluded by the sniff, and the `CHUNKER_VERSION` bump carries its
  rationale line (no walker bump: walk behavior is unchanged).
- [x] AC-3: A differential test proves files with other extensions chunk
  byte-identically to the pre-change chunker, and the explicitly-out formats remain
  untouched.
- [x] AC-4: The frozen label-targeted golden measurement exists as wave evidence with
  any quality gap versus prose dispositioned.
- [x] AC-5: The affected architecture, pipeline, and docs-layer-contract carriers are
  updated and the full suite and docs gate pass.

## Tasks

- [x] Build real-world-shaped diagram fixture corpora and the golden query subset;
  freeze and record the baseline.
- [x] Execute and record the eligibility census for in-root and out-of-root diagram
  files.
- [x] Implement the diagram dispatch and breadcrumb extraction with the chunker
  extension constants; bump `CHUNKER_VERSION`.
- [x] Add shape, membership, boundary, degenerate-input, and differential
  regressions.
- [x] Record the post-change measurement; disposition any gaps.
- [x] Update the architecture and contract carriers; run the canonical suite and
  docs gate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixtures, golden subset, eligibility census | performance-reviewer | none | Baseline and census recorded before any chunker edit. |
| Diagram dispatch and registration | implementer | Fixtures, golden subset, eligibility census | Serialize chunker.py edits with sibling wave changes through one lane (no indexer source change per Requirement 2); kind decision coordinates with `1whup-enh`. |
| Regressions and differential | qa-reviewer | Diagram dispatch and registration | The other-extension differential is the leak guard. |
| Measurement and docs | performance-reviewer, docs-contract-reviewer | Regressions and differential | Contract-sentence updates coordinate with the seed parity rule. |


## Serialization Points

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `docs/architecture/search-architecture.md`
- The golden subset is FROZEN at baseline; sibling `1whup-enh` lands its kind decision
  before this change's emission kind is finalized, or this change emits `doc` with a
  recorded convergence follow-up.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`: the docs-layer format set gains the
  diagram families.
- `docs/architecture/chunking-and-indexing-pipeline.md`: chunking overview and
  doc-kind table.
- `docs/architecture/testing-architecture.md`: tier row for the diagram coverage.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The breadcrumbed unit is the enhancement; degenerate inputs must degrade, never exclude. |
| AC-2 | required | Corpus membership and the eligibility boundary are the honest-coverage claims; version bumps are the consumer contract. |
| AC-3 | required | Extension-gated dispatch must be provably leak-free for every other file. |
| AC-4 | required | The project ships retrieval changes only with recorded measurements on frozen sets. |
| AC-5 | required | Contract carriers and closure gates are standing requirements. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-27 | Planned from executed probes at the wave 1wfsl close-out: all six extensions absent from every extension set (probe over `SOURCE_CODE_EXTENSIONS`, `_KNOWN_TEXT_EXTENSIONS`, `BINARY_EXTENSIONS`, `_GENERATED_EXCLUDE_EXTENSIONS`); a standalone `.mmd` chunks as a code-kind line window and is corpus-filtered to zero rows. This repository holds no diagram files (no local demand datum); the operator-side consumer-project validation pass is the demand survey for target repositories. | Session probe output (extension-set membership + chunk_file smoke on a `.mmd` source). |
| 2026-08-27 | Prepare-council repairs applied before readiness: Requirement 3's eligibility polarity corrected by the red-team seat's executed probe (default docs eligibility is whole-repo outside the `.wavefoundry/` blanket; both in-root and out-of-root diagram files are docs-eligible once doc-kind chunks exist), the matching risk row reworded; the `.drawio` current-state wording corrected (invisible by gate, not walk-excluded) with its generated-set membership recorded as a follow-up question; the contract-carrier list extended to all four docs-layer twins; harness path corrected to its resolvable form. | Red-team and docs-contract council seat reports 2026-08-27. |
| 2026-08-27 | Readiness-lane repairs applied before readiness recording: the code lane falsified the planned `_KNOWN_TEXT_EXTENSIONS` transfer (registration bypasses the content sniff, and `.dot` has a binary Word-template namesake the sniff excludes today), so Requirement 2 became chunker-only with no walker bump and a pinned binary-impostor fixture; the qa lane's set mechanism is now explicit (a scoped `diagrams` harness set with per-set-disjoint corpora) with the existing prose aggregates protected by a hard at-or-above-baseline re-run and anchors proven unique. | Code, qa, architecture, and docs-contract readiness lane reports 2026-08-27. |
| 2026-08-27 | Implemented. Fixtures and baseline first: six real-world-shaped diagram fixtures (three families) under a per-set-disjoint `diagrams/` corpus, nine label-targeted queries (three per family) with EXECUTED anchor-uniqueness proof, a minimal `--set diagrams` harness addition (docs-kind mirror, DOCS model, structural-zero path for the empty pre-change corpus), baseline FROZEN at 0.0/0.0 with chunk_count 0. Eligibility census executed through walk_repo plus the real `_filter_project_index_excludes` docs-eligibility call: in-root and out-of-root diagram files BOTH docs-eligible, `.wavefoundry/`-nested excluded without opt-in, the binary-impostor OLE `.dot` walk-excluded by the sniff; adjacent fact recorded: a diagram inside an excluded directory NAME (build, dist, target, out) never walks. Implementation: `chunk_diagram` (one doc-code unit per file, title-or-stem breadcrumb: mermaid frontmatter or title line, plantuml title directive, DOT graph identifier incl. quoted names), `DIAGRAM_EXTENSIONS` chunker-only registration, dispatch branch after adoc, CHUNKER_VERSION 35 to 36 with rationale (NO walker bump). Emission kind is `doc-code` per the landed sibling 1whup decision (no convergence follow-up needed). | `evidence/census_diagram_eligibility.json`; `evidence/eval_diagrams_before_1whuq.json`. |
| 2026-08-27 | Regressions and measurement: 11 DiagramChunkerTests (per-family shape and breadcrumbs, stem fallback, quoted DOT names, empty and oversized degradation, extension-set disjointness, excluded-format non-dispatch, version pin) plus 3 DiagramCorpusMembershipTests (never in `_KNOWN_TEXT_EXTENSIONS`/`SOURCE_CODE_EXTENSIONS`/`BINARY_EXTENSIONS`/generated set; docs-split membership in and out of docs roots; binary-impostor walk exclusion). AC-3 differential: the v35-pinned markdown and specs-negatives byte-identity snapshots still pass unchanged under v36, proving other-extension output untouched. Measurement: diagrams set 0.0 to 1.0 recall at 5 and 1.0 MRR (all nine queries rank their diagram first; no gaps to disposition); post-landing prose re-run byte-identical to the 1whup after-run (per-set-disjoint corpora, content-anchored bar unchanged at 0.875). Carriers: all four docs-layer contract twins (seed 211 + guru.md parity verified by direct byte-diff — the 16-test reference-doc module guards other pairs, per the DOCS-DEL-1 follow-up — build-and-verification, tool-surface) plus search-architecture, pipeline (new chunk_diagram section), testing-architecture tier row, performance-budget constant. Full suite 7,619 green; docs gate ok. | `evidence/eval_diagrams_after_1whuq.json`; `evidence/eval_prose_after_1whuq.json`; scratchpad suite_1whuq2.log (exit 0). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-27 | Curate three hand-authored families (Mermaid, PlantUML, DOT) with breadcrumb-plus-source chunks; exclude tool-generated and ambiguous formats. | Hand-authored diagram text carries prose labels the raw source already exposes to embedding; curation bounds false-positive and dependency surface, matching the 1wfr8/1wfso selection principle. | Label-extraction parsing per format was deferred as cost without measured need (the source contains the labels); `.drawio` inclusion was rejected as tool-generated XML in the `.excalidraw` class; `.d2`/Structurizr were deferred for share and extension ambiguity; a generic any-extension diagram sniff was rejected as detection surface without a query class. |


## Risks


| Risk | Mitigation |
| --- | --- |
| Diagram syntax tokens outweigh labels and embed noisily. | The measured golden subset decides; label extraction is the recorded escalation path if breadcrumb-plus-source underperforms. |
| The `.wavefoundry/`-nested boundary or a config-restricted docs set leaves some diagram files invisible. | Requirement 3's executed eligibility census pins the default whole-repo polarity and the real boundary; the guidance states both. |
| Kind decision drifts from the sibling change. | The serialization point orders the decision or records the convergence follow-up explicitly. |
| `.dot` files that are not Graphviz. | Extension-gated dispatch degrades to breadcrumbless text chunks, never excludes; the differential covers other extensions. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
