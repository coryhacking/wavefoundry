# Operator Guidance: Making Structured-Format Directories Searchable

Change ID: `1wdvr-doc index-include-prefixes-operator-guidance`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-27
Wave: `1wfsl structured-docs-retrieval`

## Rationale

The framework's code index already covers structured formats: `SOURCE_CODE_EXTENSIONS`
(`indexer.py`) includes `.yaml`, `.yml`, `.toml`, `.json`, `.jsonc`, `.xml`, `.graphql`,
`.proto`, SQL dialects, and Terraform, and `indexing.project_include_prefixes.code` in
`docs/workflow-config.json` is a per-project list. CORRECTED at implementation (third
falsified planning claim this wave, proven by executing the real filters): the code corpus
spans the WHOLE repository by default — everything outside `.wavefoundry/`, the corpus
exclusions, and ignore files — so ordinary spec directories are already fully retrievable
(semantic, BM25, `code_ask`) with no configuration, and `project_include_prefixes.code` is
the opt-back-in past the `.wavefoundry/` blanket (self-hosting), not a general root
selector. The discoverability gap is real in a corrected form: no shipped surface tells
operators that specs are searchable by default, what to check when they are not
(ignore files first), or how the `.wavefoundry/`-nested opt-in works. The only
place the lever is documented is the self-hosting aside in seed 211 (Guru), which frames
it as a Wavefoundry-repository special case. Meanwhile the docs layer deliberately serves prose (markdown
sections, plain-text and extensionless doc chunks, code docstring doc chunks, and
other doc-kind sources, non-exhaustively, per the readiness corrections) while
machine-authority files route through
typed tools, and nothing explains that contract or its consequence to a target
operator whose "docs" are partly structured files. The result across target repositories is silent
zero retrieval over spec content with no discoverable remedy.

## Requirements

1. Shipped operator guidance MUST state, in framework-generic wording, the ACCURATE
   docs-retrieval contract (readiness council correction of the earlier "markdown only"
   phrasing): the docs layer serves prose, INCLUDING markdown section chunks,
   plain-text and extensionless documentation files, doc chunks extracted from code
   docstrings and comments, and HTML/XML element text and notebook markdown cells
   (non-exhaustive; chunk-kind routing is the authority), while
   machine-authority data files are served through typed
   tools and markdown carriers, never search; the code layer indexes the
   `SOURCE_CODE_EXTENSIONS` formats, including YAML/JSON/TOML, across the whole
   repository by default (implementation correction: `project_include_prefixes.code`
   is the `.wavefoundry/` blanket opt-back-in, not a root selector), so the guidance
   states the default-coverage truth plus the missing-spec checklist — ignore files
   first, the prefix opt-in for `.wavefoundry/`-nested content, then rebuild with
   `wf update-indexes` (or the MCP `index_build`) and verify with a `code_search`
   query. The wording reflects the final docs-format set delivered
   by sibling `1wfsm-enh` (this guidance lands last per the wave watchpoint).
2. The guidance MUST carry the boundary cautions: never widen prefixes to pull in
   secret-bearing or machine-authority artifacts (per-wave `events.jsonl` ledgers and
   memory-archive bodies are path-excluded by design and stay excluded; the
   secret-scan findings ledger's exclusion is delivered by sibling `1wfsn-enh`'s
   census-driven machine-authority coverage, and this guidance's final wording
   states what that census lands, never more); prefer curated
   directories over repo-root widening; CSV is not indexed under any configuration, and
   the markdown-carrier pattern (a prose page describing the dataset or artifact) is the
   supported alternative for content that does not embed usefully.
3. The canonical carrier is the seed layer so every target receives it: extend the seed
   211 corpus-boundary section from its self-hosting-only aside into the general target
   recipe, and reconcile the operator-facing indexing guidance surfaces that seed 150's
   indexing-contract clause already names, so `wf refresh` parity propagates the wording.
   The self-hosted twins in this repository (`docs/specs/mcp-tool-surface.md` semantic
   index notes and `docs/contributing/build-and-verification.md` Semantic Index section)
   MUST match the seed contract.
4. Seed wording MUST stay framework-generic: no Wavefoundry-repository-specific paths or
   project names beyond the existing self-hosting example, per the seeds-carry-no-
   internal-artifact-refs rule.
5. This change is documentation-only: no indexer, chunker, walk-version, or
   workflow-config default changes; no auto-detection behavior.

## Scope

**Problem statement:** the include-prefixes lever that makes structured-format
directories retrievable exists and works, but no shipped surface teaches it to target
operators, and the docs-layer prose contract is undocumented outside code
comments.

**In scope:**

- `.wavefoundry/framework/seeds/211-guru.prompt.md` (corpus-boundary section extension)
- the operator-facing indexing guidance surfaces named by seed 150's indexing-contract
  reconciliation clause (exact list confirmed at implementation via that clause)
- `docs/specs/mcp-tool-surface.md` and `docs/contributing/build-and-verification.md`
  (self-hosted twins of the seed guidance)
- `AGENTS.md` MCP/indexing notes in this repository if the twin reconciliation touches
  them

**Out of scope:**

- any indexer, chunker, or configuration-default change
- auto-detection or setup-time hinting of spec directories (recorded alternative)
- CSV indexing in any form
- the spec-aware chunking enhancement (sibling change `1wfr8-enh`)

## Acceptance Criteria

- [x] AC-1: An operator following only the shipped guidance can make a non-default
  structured-format directory searchable: the recipe names the exact config key, the
  rebuild command, and a verification step, and a walkthrough against a sample repository
  fixture (spec file in a non-default directory, prefix added, rebuild, `code_search`
  hit) is recorded as evidence.
- [x] AC-2: The guidance states the accurate prose-surface docs-layer contract (per the
  corrected Requirement 1 wording, including the `1wfsm` format set) with its
  rationale, the machine-authority and secret-scan exclusions, and the CSV and
  markdown-carrier position, in both the seed and the self-hosted twins.
- [x] AC-3: Seed wording is framework-generic, the self-hosted twins match the seed
  contract, and docs lint plus the shipped-reference parity checks pass.

## Tasks

- [x] Construct the operator-facing indexing-guidance surface list by census (readiness
  council correction: seed 150's indexing-contract clause names the surface class
  generically, not an enumeration); the census MUST include at minimum
  `docs/agents/guru.md` (the seed-211 parity carrier), `docs/specs/mcp-tool-surface.md`
  including its docs-search description line, `docs/contributing/build-and-verification.md`,
  and `docs/architecture/chunking-and-indexing-pipeline.md` (a live docs-format
  contract carrier found by the readiness lane); record the constructed list in this
  doc before editing.
- [x] Extend seed 211's corpus-boundary section with the general target recipe and
  cautions (gate: `seed_edit_allowed`).
- [x] Reconcile the self-hosted twins (`docs/specs/mcp-tool-surface.md`,
  `docs/contributing/build-and-verification.md`) to the seed contract.
- [x] Execute the AC-1 fixture walkthrough and record the evidence.
- [x] Run full docs validation and the shipped-reference parity tests.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Surface census and seed wording | docs-contract-reviewer | none | Seed edits behind the seed gate; framework-generic wording only. |
| Self-hosted twin reconciliation | implementer | Surface census and seed wording | Marker-fence hazard: place prose outside renderer-owned regions. |
| Walkthrough evidence and validation | qa-reviewer | Self-hosted twin reconciliation | AC-1 fixture walkthrough plus docs gate. |


## Serialization Points

- `.wavefoundry/framework/seeds/211-guru.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/build-and-verification.md`
- Open `seed_edit_allowed` before the seed edit and close it immediately after; complete
  the seed wording before reconciling twins so the twins copy a settled contract.

## Affected Architecture Docs

- N/A beyond the named guidance surfaces: this change documents existing behavior and
  crosses no module boundary, data path, or verification seam. `docs/architecture/`
  content is unchanged.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The change exists to make the lever teachable; an unexecutable recipe is the failure mode. |
| AC-2 | required | The contract and cautions prevent operators widening into secret-bearing or authority paths. |
| AC-3 | required | Seed genericity and twin parity are shipped-surface correctness gates. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-27 | Planned from a verified census: `SOURCE_CODE_EXTENSIONS` includes YAML/JSON/TOML (indexer.py line 456); seed 211 documents the include-prefixes opt-in as a self-hosting aside only; seed 150 already carries an indexing-contract reconciliation clause to propagate operator wording; the docs chunker is markdown-only (`chunker.MARKDOWN_EXTENSIONS`). | grep census across seeds, install assets, and docs surfaces; `code_constants` read of `SOURCE_CODE_EXTENSIONS`. |
| 2026-08-27 | Readiness-council correction: the planning census's "docs chunker is markdown-only" claim was IMPRECISE; the docs retrieval surface also carries plain-text/extensionless doc chunks (`chunk_plain_text`) and code docstring doc chunks (the 1sek8 dual-output union). Requirement 1's contract wording and the Rationale were corrected before readiness was recorded. | Red-team primer F2 and docs-contract seat verification with chunker/indexer anchors. |
| 2026-08-27 | CENSUS-CONSTRUCTED surface list (recorded before editing, per Task 1): SHIPPED seed layer — `seeds/211-guru.prompt.md` Index Scope corpus-boundary section (the canonical carrier to extend), `seeds/160-upgrade-wavefoundry.prompt.md` line ~225 (upgrade preservation mention of `indexing.project_include_prefixes`; verified compatible, no edit), `seeds/150-refresh-wavefoundry.prompt.md` indexing-contract reconciliation clause (the propagation mechanism, not a content carrier). SELF-HOSTED twins — `docs/agents/guru.md` Index Scope (byte-parity carrier of seed 211; no renderer fences in that region), `docs/specs/mcp-tool-surface.md` (semantic-index rebuild note ~line 1167 and the docs-search description line ~1418), `docs/contributing/build-and-verification.md` (extra project index roots, ~line 129), `docs/architecture/chunking-and-indexing-pipeline.md` (include-prefix architecture prose at lines ~67 and ~197-198 plus the config example ~789-797; this row ORIGINALLY recorded the config example as already updated by siblings 1wfsn/1wfsm, which the delivery lane DISPROVED by byte-identity diff against HEAD — a false census disposition, finding DOCS-DEL-1; the Configuration Reference section was rewritten to opt-back-in semantics under that finding's repair), `docs/architecture/data-and-control-flow.md` line ~90 (one-sentence exclusion mention; verified compatible), `docs/architecture/decisions/1p4xx-adr` (historical ADR, not edited), `AGENTS.md` (MCP/indexing notes; originally dispositioned as carrying no include-prefix recipe — a second census miss: its graph-index parenthetical DID misdescribe include-prefixes as a scope restriction and was corrected under DOCS-DEL-1). Census method: repo-wide token sweep for `project_include_prefixes` plus the readiness-lane docs-layer-contract pins, excluding wave records and plans. | grep census output in session; readiness-lane pins (guru.md:626, mcp-tool-surface.md:1418, chunking-and-indexing-pipeline.md). |
| 2026-08-27 | IMPLEMENTATION FALSIFICATION (the wave's third, caught by the executable walkthrough): the plan's recipe premise — that `indexing.project_include_prefixes.code` selects the code roots and a directory outside them needs adding — was DISPROVEN by executing the real filters (`_filter_project_index_excludes` excludes only `.wavefoundry/`-prefixed paths, with the prefixes list as the opt-back-in; `_effective_project_include_prefixes` confirms). An ordinary `api-contracts/` spec directory is in the code corpus with NO configuration. The Rationale and Requirement 1 were corrected in place (marked), and the shipped guidance was rewritten to the accurate contract: default whole-repo coverage, a missing-spec checklist (ignore files first), and the prefix opt-in scoped to `.wavefoundry/`-nested (self-hosting) content. | `evidence/walkthrough_include_prefixes.py` (the failing pre-correction assertion falsified the premise); indexer.py `_filter_project_index_excludes` / `PROJECT_INDEX_EXCLUDE_PREFIXES`. |
| 2026-08-27 | IMPLEMENTED (landing last per the wave watchpoint, after all sibling outcomes settled): seed 211 Index Scope extended under `seed_edit_allowed` (opened and closed around each edit) with the corrected framework-generic guidance — default coverage, missing-spec checklist, `.wavefoundry/`-nested opt-in recipe, spec-aware chunking note reflecting 1wfr8's measured DEFAULT-ON, the accurate non-exhaustive docs-layer prose contract reflecting 1wfsm's landed rst/adoc set, machine-authority exclusions reflecting 1wfsn's landed scan-findings predicate, CSV/markdown-carrier position, and the `walk_reinclude_filenames` name-layer-only boundary. Byte-parity mirror applied to `docs/agents/guru.md`; twins reconciled (`docs/contributing/build-and-verification.md` extra-roots section; `docs/specs/mcp-tool-surface.md` docs-search description line + index_build include-prefixes note). AC-1 walkthrough EXECUTED with the real build + embedder + Lance vector search: Part A default-coverage hit (ordinary directory, no config), Part B blanket-excluded spec opted in via the prefix, rebuilt, top hit rank 1 on the 1wfr8-breadcrumbed operation chunk. | seed/guru/twin diffs; `evidence/walkthrough_include_prefixes_result.json` (verdict GUIDANCE VERIFIED). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-27 | Documentation-only: teach the existing include-prefixes lever through the seed layer and self-hosted twins. | The capability exists and works; discoverability is the whole gap, and a docs change ships to every target through refresh parity with zero behavior risk. | A setup-time hint that detects spec-like files outside prefixes was rejected as code scope with heuristic false positives (plausible follow-up if field demand appears); auto-including detected spec directories by default was rejected as surprise corpus growth that violates the explicit-configuration principle. |


## Risks


| Risk | Mitigation |
| --- | --- |
| Seed edits propagate to every target and can regress unrelated wording. | Bound the edit to the corpus-boundary section, run behind the seed gate, and verify with the shipped-reference parity tests. |
| Prose placed inside renderer-owned marker fences is destroyed on the next render. | Place all twin edits outside fenced regions and diff the fences after the docs gate. |
| Operators over-widen prefixes after reading the recipe. | AC-2's cautions are a required part of the same guidance block, not a separate page. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
