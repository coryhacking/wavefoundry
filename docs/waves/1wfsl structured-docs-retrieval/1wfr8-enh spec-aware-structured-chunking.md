# Spec-Aware Chunking for OpenAPI and JSON Schema

Change ID: `1wfr8-enh spec-aware-structured-chunking`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-27
Wave: `1wfsl structured-docs-retrieval`

## Rationale

YAML and JSON files in the code corpus are chunked today by tree-sitter flat emission
over mapping pairs (`chunk_yaml_treesitter`, the registered `tree_sitter_json` grammar):
syntax-aware, domain-blind. For documentation-bearing spec formats that is a measurable
retrieval handicap: an OpenAPI operation's `summary`/`description` prose lands in chunks
separated from the method and path that give it meaning, and a JSON Schema property's
`description` loses its property-path context, so natural-language queries over specs
rank poorly relative to the prose the files actually contain. The chunker's own history
shows the lever works when applied to prose-bearing structure: prepending section
breadcrumbs to docs chunks measured a ten-point NL-retrieval improvement (the 1p4w9 note
on `CHUNKER_VERSION`). This change applies the same idea to exactly two curated formats,
behind a measured adoption gate, because no field demand has been observed yet and the
project's retrieval history (RRF, reranker split, adaptive freshness) is explicit that
plausible retrieval changes ship only on measured wins.

## Requirements

1. Detection MUST be content-based within files already in the corpus: a YAML/JSON file
   whose root carries `openapi:` or `swagger:` is an OpenAPI spec. A file is a JSON
   Schema only when its root `$schema` VALUE is a json-schema.org dialect identifier, or
   its root is schema-shaped (a `$defs`/`definitions` object, or root `type` plus
   `properties`). A bare root `$schema` key pointing anywhere else (schemastore config
   references in `renovate.json`, `.eslintrc.json`, tsconfig-style files) MUST NOT
   qualify; that config class is a named negative in AC-1. No new extensions, no new
   walk inclusions, no include-prefix changes; a spec outside the configured prefixes
   stays outside (operator guidance for that is sibling change `1wdvr-doc`).
2. For detected OpenAPI specs, chunk units MUST be operation-level: one chunk per
   method-plus-path carrying its `summary`, `description`, parameter and response
   descriptions, with a breadcrumb prefix on the embedded text (for example
   `paths./users/{id}.get:`) mirroring the docs-breadcrumb pattern. For detected JSON
   Schemas, units MUST be definition- or property-group-level with the property-path
   breadcrumb. Deterministic chunk identities follow the existing owner-path
   conventions.
3. Files NOT detected as either format MUST chunk byte-identically to today's flat
   emission, proven by a differential test over a non-spec YAML/JSON corpus (kubernetes
   manifests, CI configs, arbitrary JSON fixtures).
4. Adoption is measurement-gated with a COMMITTED harness owned by this change: before
   the first chunker edit, a spec-specific golden set of at least 20 natural-language
   queries with labeled expected chunks over real committed spec fixtures MUST exist in
   the repository (under the chunker test fixtures; the parked `1sear-enh` suite in wave
   `1seaw` remains the broader follow-up and is cross-referenced, not depended on), with
   the metric definitions fixed as recall at 5 and mean reciprocal rank. The numeric
   pass bar for shipping default-on is: mean recall at 5 improves by at least five
   points AND mean reciprocal rank does not regress; any individual query that regresses
   is enumerated with a recorded disposition. Anything short of the bar lands
   config-gated off with the measurement recorded; the default decision is reversible
   only by a later measured re-run. Neither outcome reopens the design. Operator-side
   validation on the operator's local consumer projects after a pack build is a
   disclosed, non-gating follow-up.
5. `CHUNKER_VERSION` MUST be bumped with the standard chunk-set-shape-change rationale
   line (consumer code indexes re-chunk; embeddings reuse by content hash), and the
   oversized-chunk bounding plus `indexing.max_treesitter_parse_bytes` behavior MUST
   apply to spec chunks unchanged.
6. Boundaries unchanged: the docs layer's format set is untouched by THIS change (its
   accurate prose-surface contract is stated in sibling `1wdvr-doc`, and sibling
   `1wfsm-enh` extends it separately); excluded machine-authority and secret-scan
   artifacts stay excluded; CSV is explicitly out of scope in any form; no generic
   extract-all-string-values heuristic for arbitrary YAML/JSON.

## Scope

**Problem statement:** spec files are findable but rank poorly because their prose is
chunked without its structural context; the framework has a proven breadcrumb lever it
has never applied to structured formats.

**In scope:**

- `.wavefoundry/framework/scripts/chunker.py` (detection, the two spec chunkers,
  registration, `CHUNKER_VERSION` bump)
- `.wavefoundry/framework/scripts/tests/test_chunker.py` (detection, chunk-shape,
  differential, and identity tests plus fixtures)
- the golden spec query set and its fixtures (location per the `1sear-enh` harness if
  landed, else under the chunker test fixtures)
- `docs/architecture/search-architecture.md` and the relevant
  `docs/architecture/testing-architecture.md` tier row
- reproducible before/after retrieval measurements as wave evidence

**Out of scope:**

- CSV in any form (does not embed usefully; the markdown-carrier pattern is the answer)
- generic prose-field extraction for arbitrary YAML/JSON
- new walk extensions, include-prefix defaults, or docs-layer format changes
- AsyncAPI, Protobuf options, Terraform docs, or any third format (future changes may
  add formats through the same curated gate)
- reranker, embedder, or fusion changes

## Acceptance Criteria

- [x] AC-1: Detection unit tests cover OpenAPI 3.x in YAML and JSON, Swagger 2.x, and
  JSON Schema positives (dialect-URI and schema-shaped roots), plus negatives that MUST
  remain on the flat-emission path: kubernetes manifests, CI configs, arbitrary JSON,
  the `$schema`-carrying non-schema config class (`renovate.json`,
  `.eslintrc.json`, tsconfig-style files), and one named non-schema JSON whose root
  happens to carry `type` and `properties` (the schema-shaped-branch adversarial
  negative).
- [x] AC-2: Chunk-shape tests prove operation-level and definition-level units carry
  their breadcrumb plus description prose with deterministic identities, a boundary
  test proves oversized-chunk bounding and `indexing.max_treesitter_parse_bytes`
  apply to spec chunks unchanged, and `CHUNKER_VERSION` is bumped with the documented
  rationale line.
- [x] AC-3: A differential test proves non-spec YAML/JSON corpora chunk byte-identically
  to the pre-change chunker.
- [x] AC-4: The golden set (at least 20 labeled queries) is committed BEFORE the first
  chunker edit, the recorded measurement (before/after recall at 5 and mean reciprocal
  rank) exists as wave evidence, and the shipped default matches the Requirement 4
  numeric bar with the decision and any per-query regressions dispositioned in this
  doc.
- [x] AC-5: Existing chunker regressions stay green, the affected architecture docs are
  updated, and docs lint passes.

## Tasks

- [x] Build the spec fixture corpus (real-world OpenAPI and JSON Schema files plus
  non-spec negatives) and the golden query set with labeled expected chunks.
- [x] Record the pre-change baseline measurement over the golden set.
- [x] Implement content-based detection and the two spec chunkers with breadcrumbed
  units and deterministic identities; bump `CHUNKER_VERSION`.
- [x] Add detection, chunk-shape, identity, and differential regressions.
- [x] Record the post-change measurement; decide default-on versus config-gated off from
  the measured outcome and record the decision.
- [x] Update `search-architecture.md` and the testing-architecture tier row.
- [x] Run the canonical suite, docs gate, and diff/hygiene checks.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixtures, golden set, baseline measurement | performance-reviewer | none | Baseline recorded before any chunker edit. |
| Detection and spec chunkers | implementer | Fixtures, golden set, baseline measurement | Serialize all chunker.py edits through one lane. |
| Regressions and differential proof | qa-reviewer | Detection and spec chunkers | Differential corpus must include the negatives from AC-1. |
| Post-change measurement and default decision | performance-reviewer | Regressions and differential proof | The measured outcome decides the default; record either way. |
| Docs and closure gates | docs-contract-reviewer | Post-change measurement and default decision | Architecture rows plus docs gate. |


## Serialization Points

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `docs/architecture/search-architecture.md`
- The golden set is FROZEN at the baseline measurement, before the first chunker edit
  (matching the wave watchpoint); any post-baseline change to the set forces a baseline
  re-run so the before/after delta spans an identical set. Complete the differential
  proof before the default decision.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`: the chunking tier description gains the
  curated spec-format path and its detection contract.
- `docs/architecture/testing-architecture.md`: the chunker tier row gains the
  differential and golden-set coverage.
- `docs/ARCHITECTURE.md` needs no new child doc; this extends the existing chunking seam.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Detection false positives silently rewrite chunking for ordinary config files. |
| AC-2 | required | The breadcrumbed unit is the whole enhancement; the version bump is the consumer contract. |
| AC-3 | required | Non-spec corpora must be provably untouched or the change leaks beyond its curation. |
| AC-4 | required | The project ships retrieval changes only on measured wins; the gate is the point. |
| AC-5 | required | Suite, docs, and hygiene gates are standing closure requirements. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-27 | Planned from a verified census: YAML/JSON chunk via tree-sitter flat mapping-pair emission (`chunk_yaml_treesitter`, `tree_sitter_json` at chunker.py lines 106-108, 5635); the docs-breadcrumb precedent measured a ten-point NL win (1p4w9 note in the `CHUNKER_VERSION` history); `SOURCE_CODE_EXTENSIONS` already includes the spec extensions, so coverage is not the gap. Related parked work: golden-query retrieval suite `1sear-enh` (wave `1seaw`, planned) is the preferred harness shape for AC-4. | chunker.py census; `code_constants` read; wf_list_plans. |
| 2026-08-27 | GOLDEN SET COMMITTED BEFORE ANY CHUNKER EDIT (watchpoint honored): 24 labeled natural-language queries over a committed 14-file spec fixture corpus (`tests/fixtures/retrieval_golden/specs/` + `golden_queries_specs.json`), authored replicas of well-known public API shapes; harness `run_retrieval_eval.py` runs the REAL pipeline stages (chunker.chunk_file, the indexer's embedder with documents bare / queries prefixed via query_embedding_prefix, cosine ranking; code-layer kind mirror). BASELINE recorded on the frozen set with flat emission (chunker v33): recall at 5 0.8333, MRR 0.8194; three petstore queries beyond rank 20 entirely. | `evidence/retrieval_eval_specs_before.json`; fixture self-check in the authoring lane report. |
| 2026-08-27 | IMPLEMENTED under `framework_edit_allowed` (serialized lane): content-based detection + spec chunkers in chunker.py — OpenAPI YAML via a bounded indentation extractor (no YAML dependency; column-0 `openapi:`/`swagger:` root key), OpenAPI/JSON-Schema JSON via stdlib json with the dialect-URI and value-shape-guarded schema-shaped branches; operation/definition/property units with breadcrumbs BAKED into kind="code" text; `indexing.max_treesitter_parse_bytes` applies to the spec path unchanged; per-project gate `indexing.spec_aware_chunking` published by the indexer as `WAVEFOUNDRY_SPEC_CHUNKING`; `CHUNKER_VERSION` 33 to 34. Regressions: `SpecChunkingTests` (9 tests) over the committed corpus incl. the named negatives, deterministic-identity re-chunk, parse-cap boundary, config gate, and the non-spec byte-identity differential against a pre-change (git-HEAD v32) snapshot regenerated under the canonical tree-sitter environment after an environment-sensitive first cut; test_chunker.py 461 tests green. | chunker.py/indexer.py/test diffs; focused run `test_chunker.py — 461 ok`. |
| 2026-08-27 | POST-CHANGE MEASUREMENT + DEFAULT DECISION: recall at 5 0.8333 to 1.0000 (+16.7 points; every query hits, including the three previously beyond rank 20), MRR 0.8194 to 0.9479; ZERO individual per-query rank regressions (5 improved). The Requirement 4 numeric bar (recall +5 points AND MRR non-regression) is MET decisively: the shipped default is DEFAULT-ON (`SPEC_CHUNKING_DEFAULT_ON = True`), reversible per project via `indexing.spec_aware_chunking`. The parked `1wfso-enh` admission-gate condition (a measured default decision) is now satisfied with a default-on outcome; admission remains a separate operator decision. | `evidence/retrieval_eval_specs_after.json`; per-query rank comparison therein. |
| 2026-08-27 | DELIVERY REPAIR (finding ARCH-DEL-1, architecture delivery lane, blocking): detected OpenAPI specs silently dropped non-curated sections (servers, securitySchemes, webhooks, non-schemas components subsections) from both corpora — content flat emission previously served, invisible to the golden set. Repaired with per-subsection `components.<key>:` chunks and a `spec:` residue chunk in BOTH the JSON and YAML chunkers (the JSON Schema chunker's own residue pattern); regression `test_non_curated_sections_keep_coverage` pins petstore securitySchemes/servers, payments servers, and swagger securityDefinitions coverage. ARCH-DEL-2 folded in: JSON spec chunk end-lines capped at the source's real length. Measurement RE-RUN over the frozen golden set post-repair: recall@5 1.0, MRR 0.9479, zero per-query regressions (corpus 103 to 107 chunks) — the bar and the DEFAULT-ON decision stand unchanged. test_chunker.py 462 tests green. | ARCH-DEL-1/ARCH-DEL-2 ledger records; `evidence/retrieval_eval_specs_after.json` (label after-1wfr8-spec-chunking-with-residue-coverage); focused run `test_chunker.py — 462 ok`. |
| 2026-08-27 | DELIVERY REPAIR CYCLE 2 (independent reverification found the ARCH-DEL-1 repair INCOMPLETE with two executed residuals): (1) path-ITEM-level keys (parameters, summary, description, servers — siblings of the HTTP methods inside the curated `paths` root) still vanished in both YAML and JSON branches; repaired with per-path `paths.<path>:` item chunks in both. (2) the ARCH-DEL-2 line cap never reached `_chunk_json_schema`; `max_line` now passes at all its call sites. Regressions `test_path_item_level_content_keeps_coverage` (pins the petstore path-level parameters drop the reverifier found, plus a JSON path-item case) and `test_minified_schema_lines_capped_at_source_length`; test_chunker.py 464 green. Measurement RE-RUN over the frozen set: recall@5 1.0, MRR 0.9479, zero regressions (108 chunks) — bar and DEFAULT-ON unchanged. The census script's no-out default now prints to stdout only (writes require explicit --out). | Reverification report 2026-08-27; `evidence/retrieval_eval_specs_after.json` (label after-1wfr8-spec-chunking-full-coverage); focused run `test_chunker.py — 464 ok`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-27 | Curated domain chunkers for exactly OpenAPI and JSON Schema, content-detected, measurement-gated. | Prose provably exists in these formats with a structural context that flat emission discards, and the breadcrumb lever has a measured precedent; curation bounds false-positive risk and the gate matches the project's measured-adoption history. | A generic extract-all-string-values heuristic over arbitrary YAML/JSON was rejected as noise that degrades ranking; index-time synthesis of markdown carrier files was rejected as generated-artifact machinery with ownership and staleness costs; extending the docs layer to structured formats was rejected as a boundary change the machine-authority principle argues against. |
| 2026-08-27 | CSV stays excluded everywhere. | Value tables produce no usable embedding under any treatment; a hand-written markdown carrier describing the dataset is strictly better retrieval content. | Header-only FTS over CSVs was considered and rejected as cost without a query class that needs it. |


## Risks


| Risk | Mitigation |
| --- | --- |
| The measurement shows no win. | The bounded outcome is config-gated off with the measurement recorded; the design does not reopen, matching prior evaluated-and-rejected retrieval work. |
| Detection false positives rewrite chunking for ordinary configs. | Content-based root-key detection plus the AC-1 negative corpus and the AC-3 differential proof. |
| The chunker version bump re-chunks every consumer index. | Standard convention: embeddings reuse by content hash, the bump rationale documents the cost, and the change rides a normal release. |
| Very large specs hit the tree-sitter parse-size cap. | The existing `indexing.max_treesitter_parse_bytes` behavior applies unchanged and is covered by a boundary test. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
