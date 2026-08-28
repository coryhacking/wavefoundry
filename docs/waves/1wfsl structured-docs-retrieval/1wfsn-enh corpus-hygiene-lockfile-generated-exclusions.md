# Corpus Hygiene: Consolidate Exclusion Mechanisms and Close the Stragglers

Change ID: `1wfsn-enh corpus-hygiene-lockfile-generated-exclusions`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-27
Wave: `1wfsl structured-docs-retrieval`

## Rationale

The original premise of this change ("no name-based lockfile exclusion exists; lockfiles
are chunked today") was FALSIFIED by the readiness council against the tree, and this
document is re-planned on the corrected baseline. Multiple exclusion mechanisms already
exist and already catch most lockfiles (the count below is what this planning pass
found; Requirement 1's executed census is the authority and consolidation covers
EVERY mechanism it finds, explicitly including `_GENERATED_EXCLUDE_EXTENSIONS` at
indexer.py line 608, applied in the walk at line 876, which this doc's first
correction itself missed): `HARDCODED_EXCLUDE_FILENAMES` (indexer.py
constant, line 600) name-excludes `package-lock.json`, `yarn.lock`, and
`pnpm-lock.yaml` in `walk_repo`; `BINARY_EXTENSIONS` (constant, line 576) contains
`.lock` (line 594), walk-excluding `Cargo.lock`, `poetry.lock`, `uv.lock`,
`Pipfile.lock`, `composer.lock`, `Gemfile.lock`, and `flake.lock`; and
`_filter_code_files`'s `SOURCE_CODE_EXTENSIONS` gate (line 1252) drops `go.sum`,
`gradle.lockfile`, and `*.map` from every retrieval corpus even though they walk.
`bun.lockb` is binary-sniffed out.

What remains true and worth fixing: the mechanisms are SEVERAL unrelated constants with no
shared documentation, so this session's censuses missed mechanisms twice (two in the
original planning census, a third in its first correction), an implementer
extending one cannot see the others, and a small set of machine-generated files IS still
indexed today, roughly `npm-shrinkwrap.json`, `packages.lock.json`, `*.min.js`, and
`*.min.css`. The honest change is consolidation plus stragglers: one documented
exclusion story, the genuinely indexed noise closed, measured on corpora that exist
locally.

## Requirements

1. A corrected per-name census MUST be recorded first as implementation evidence: for
   every candidate machine-generated name, its current classification (walk-excluded by
   name, walk-excluded by extension or sniff, walked-but-corpus-filtered, or actually
   indexed), produced by executing the real walk and corpus filters, not by grep.
2. EVERY exclusion mechanism the executed census finds MUST be consolidated behind one
   documented story (at minimum the name layer including its fourth entry
   `prompt-surface-manifest.json`, the `.lock` binary-extension entry, the
   generated-extension set, and the corpus filter): a
   single named module-level structure (or clearly cross-referenced constants) in
   `indexer.py` stating what is excluded, by which mechanism, and why, so a future
   editor sees the whole exclusion surface in one place, with cross-references to the
   adjacent exclusion classes the census does not consolidate (the machine-authority
   path predicates, the dot-directory rule, and the directory/prefix constants) so the
   documentation cannot recreate the fragmentation one layer out. Behavior for names
   already excluded MUST NOT change.
3. The stragglers that the census confirms are indexed today MUST be excluded by exact
   name or bounded pattern: at minimum `npm-shrinkwrap.json` and `packages.lock.json`
   by name, `*.min.js` and `*.min.css` by pattern, applied uniformly across the
   semantic, lexical, and graph walks.
4. Secret scanning MUST NOT be narrowed in any form: the standalone scanner's
   all-tracked-files candidate semantics are a preserved contract, covered by a
   regression.
5. The re-include escape hatch is SCOPED to the name-based exclusion layer only (the
   consolidated name/pattern set including the pre-existing
   `HARDCODED_EXCLUDE_FILENAMES` entries): an `indexing` workflow-config field, default
   empty, restores a named file to the walk by subtracting it at the filename check
   only. It does NOT override the binary-extension or content-sniff mechanisms, and it
   can NEVER resurrect the machine-authority path exclusions (per-wave `events.jsonl`,
   memory-archive bodies), which the walk applies before the name layer; both
   boundaries are documented with the field. The secret-scan FINDINGS ledger
   (`docs/scan-findings.json`) is NOT among those walk-level path exclusions today
   (qa re-verification finding: only the `.wavefoundry/index/` scan-cache sidecar is
   prefix-excluded), so it joins Requirement 1's census candidates; if the census
   shows any corpus configuration can reach it, it MUST be excluded at the
   machine-authority path layer, outside the hatch's reach.
6. The version constants MUST be bumped per their documented conventions for the filter
   logic change, and the effect MUST be measured on corpora that exist locally: recorded
   before/after corpus statistics (file count, chunk count, index size) on this
   repository plus committed fixture corpora containing real-world straggler samples.
   Operator-side validation on the operator's local Java, Swift, and JS/TS consumer
   projects after a local pack build is a disclosed, NON-gating follow-up recorded when
   its evidence arrives (the established operator-side validation pattern).

## Scope

**Problem statement:** the exclusion surface is fragmented across several undocumented
mechanisms (which caused two false planning censuses in this very wave; the executed
census is the authoritative count), and a small class of machine-generated files still
reaches the corpus.

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py` (consolidated exclusion documentation,
  straggler names/patterns, re-include config read, version bump)
- `docs/workflow-config.json` schema documentation for the re-include field (default
  empty)
- `.wavefoundry/framework/scripts/tests/test_indexer.py` (census-executable regressions,
  straggler exclusion, re-include scoping, layer uniformity, secret-scan-unchanged)
- committed straggler fixture corpora and the before/after measurements
- `docs/architecture/search-architecture.md` walk-contract note; coordination with
  `1wdvr-doc` guidance wording

**Out of scope:**

- changing the classification of any already-excluded name
- narrowing secret scanning
- vendored-directory heuristics beyond gitignore
- content-based generated-file detection; size or entropy heuristics

## Acceptance Criteria

- [x] AC-1: The executed per-name census exists as evidence, and regressions pin the
  classification of every listed name at Requirement 1's mechanism-class granularity
  (name / extension-or-sniff / corpus-filter; Requirement 2 may restructure the
  constants): already-excluded names stay excluded by their mechanism class, and each straggler is excluded by the new name/pattern layer,
  uniformly across semantic, lexical, and graph walks, while sibling legitimate files
  (`package.json`, un-minified sources) remain included.
- [x] AC-2: The re-include field restores a name-layer-excluded file and is proven NOT
  to override binary-extension, sniff, or machine-authority path exclusions (a
  regression attempts to re-include a canonical `events.jsonl` path and fails); it is
  default empty; the version bump carries its rationale.
- [x] AC-3: A regression proves the standalone secret-scan candidate set is unchanged.
- [x] AC-4: Recorded before/after corpus statistics exist for this repository and the
  committed fixture corpora; the operator-side consumer-project validation is recorded
  as a disclosed non-gating follow-up in the wave record.
- [x] AC-5: The consolidated exclusion documentation exists in `indexer.py` and
  `search-architecture.md`, the full suite and docs gate pass, and hygiene checks are
  clean.

## Tasks

- [x] Execute the per-name census through the real walk and corpus filters; record it.
- [x] Consolidate the exclusion documentation and add the straggler names/patterns with
  the version bump.
- [x] Implement the scoped re-include config read.
- [x] Add the AC-1/AC-2/AC-3 regressions and straggler fixtures.
- [x] Record before/after statistics on this repository and the fixtures.
- [x] Update `search-architecture.md`; coordinate wording with `1wdvr-doc`.
- [x] Run the canonical suite, docs gate, and hygiene checks.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Executed census and before statistics | performance-reviewer | none | Through the real walk, not grep; the false-census lesson is the reason. |
| Consolidation and stragglers | implementer | Executed census and before statistics | Serialize indexer.py edits with sibling wave changes through one lane. |
| Regressions incl. secret-scan and re-include scoping | qa-reviewer | Consolidation and stragglers | AC-2's non-override proof is load-bearing. |
| After statistics and docs | performance-reviewer, docs-contract-reviewer | Regressions incl. secret-scan and re-include scoping | Operator-side validation recorded as non-gating follow-up. |


## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `docs/architecture/search-architecture.md`
- Indexer edits serialize with sibling wave changes touching the same file; the executed
  census precedes the first filter edit.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`: the walk contract gains the consolidated
  exclusion story and the scoped re-include field.
- `docs/architecture/testing-architecture.md`: indexer tier row gains the census-backed
  exclusion and secret-scan-unchanged coverage.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The executed census is the correction of this change's own planning defect; classification pins prevent regression in either direction. |
| AC-2 | required | An escape hatch that silently overrode binary or sniff exclusions would be a correctness and security hazard. |
| AC-3 | required | Silently narrowing secret scanning would be a security regression. |
| AC-4 | required | Hygiene claims ship with measured local evidence; the consumer-project tier is disclosed, not gating. |
| AC-5 | required | The consolidation documentation is the durable fix for the fragmentation that caused the false census. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-27 | Original plan authored on a FALSE census ("no name-based exclusion exists"); the readiness council's red-team seat falsified it against the tree (`HARDCODED_EXCLUDE_FILENAMES` line 600; `.lock` in `BINARY_EXTENSIONS` line 594; `_filter_code_files` gate line 1252) and the change was re-planned in place as consolidation-plus-stragglers before readiness was recorded. The planning grep's exclusion pipeline (`grep -v` chains) hid the disproving lines; Requirement 1 makes the census executable through the real walk for exactly that reason. | Red-team primer F1 with verified anchors; re-planned document (this revision). |
| 2026-08-27 | Independent fresh-context qa re-verification confirmed the mechanism-count un-pin repair (VERIFIED-REPAIRED, zero anchor drift on every cited indexer.py line) and surfaced one new advisory: the secret-scan findings ledger `docs/scan-findings.json` (`SCAN_FINDINGS_PATH`, wave_lint_lib/constants.py) is not walk-path-excluded today; only the `.wavefoundry/index/` scan-cache sidecar is prefix-excluded. Requirement 5's machine-authority parenthetical was corrected and the ledger added to the census candidates with a conditional path-layer exclusion; sibling `1wdvr-doc` Requirement 2's caution was aligned so the guidance never overpromises. | QA re-verification report 2026-08-27; indexer.py `HARDCODED_EXCLUDE_PATHS`/`HARDCODED_EXCLUDE_PREFIXES` and predicates at lines 826-849. |
| 2026-08-27 | IMPLEMENTED under `framework_edit_allowed`: consolidation banner ("CORPUS EXCLUSION STORY") above the constants in `indexer.py` with the eight walk layers in application order and cross-references to the unconsolidated adjacent classes; stragglers closed (`npm-shrinkwrap.json`/`packages.lock.json` joined `HARDCODED_EXCLUDE_FILENAMES`; new `HARDCODED_EXCLUDE_FILENAME_SUFFIXES` = `.min.js`/`.min.css` at the same name layer); `docs/scan-findings.json` excluded via the new machine-authority predicate `_is_secret_scan_findings_path` (path imported from `wave_lint_lib.constants.SCAN_FINDINGS_PATH`, one definition), applied in `walk_repo` BEFORE the name layer AND on the `files=` incremental seam; re-include hatch `indexing.walk_reinclude_filenames` (exact filenames only, path-shaped entries rejected) subtracts at the name layer alone; `WALKER_VERSION` 11 to 12 with the rationale line. Post-landing fixture census re-executed: every straggler excluded with correct mechanism attribution, all pre-existing classifications unchanged, siblings still indexed. Regressions: `CorpusExclusionCensusTests` (7 tests) incl. census pins, hatch scoping incl. the `yarn.lock` double-coverage no-op, `events.jsonl`/scan-findings resurrection attempts failing, seam boundary, walker bump, and secret-scanner candidate non-narrowing over a real git fixture; full `test_indexer.py` 304 tests green. `search-architecture.md`, `chunking-and-indexing-pipeline.md`, and the testing-architecture tier row updated. | indexer.py/test_indexer.py diffs; `evidence/census_results_after.json`; focused run `test_indexer.py — 304 tests ok`. |
| 2026-08-27 | Requirement 1 EXECUTED census recorded (real `walk_repo` + `_filter_code_files` on a constructed fixture tree, `WALKER_VERSION` 11, no grep). Classifications: name layer excludes package-lock.json, yarn.lock, pnpm-lock.yaml, prompt-surface-manifest.json; the `.lock` binary-extension entry excludes Cargo/poetry/uv/Pipfile/composer/Gemfile/flake locks; content sniff excludes bun.lockb; generated extensions exclude .snap/.excalidraw; the corpus filter drops go.sum, gradle.lockfile, *.map; INDEXED-class stragglers confirmed: npm-shrinkwrap.json, packages.lock.json, *.min.js, *.min.css, AND docs/scan-findings.json (the qa-advisory candidate: it walks in this real repository and passes the code-corpus filter, so a corpus configuration can reach it; the conditional Requirement 5 path-layer exclusion is therefore REQUIRED). Legitimate siblings (package.json, app.js, styles.css) confirmed included. Repository before-stats: 1,904 walked files, 180 code-corpus files, index 212,314,625 bytes. | `evidence/census_exclusions.py`, `evidence/census_results.json`. |
| 2026-08-27 | DELIVERY REPAIR (finding QA-DEL-1, qa delivery lane): the committed BEFORE census artifact had been clobbered by a script re-run (the script wrote a fixed sibling filename). Repaired: the script now defaults to a non-committed output name (`--out` required to write committed artifacts), and `census_results.json` was REGENERATED by executing the fixture census against the extracted git-HEAD indexer module (walker 11) — matching the qa lane's independent reproduction row for row (all five stragglers INDEXED, incl. docs/scan-findings.json) — with the before repo-stats carried from the surviving corpus_stats_1wfsn.json record under an explicit provenance note. | QA-DEL-1 ledger records; regenerated `evidence/census_results.json` (provenance field); `evidence/census_exclusions.py` `--out` parameter. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-27 | Re-plan as consolidation-plus-stragglers on the corrected baseline; keep every existing exclusion's behavior. | The council falsified the original premise; the durable defect is mechanism fragmentation, and the real gap is four straggler classes. | Proceeding with the original 15-name list was rejected as legislating already-true behavior on a false rationale; withdrawing the change entirely was rejected because the fragmentation caused a real planning failure this session and the stragglers are genuinely indexed. |
| 2026-08-27 | Scope the re-include escape hatch to the name-based layer only. | Overriding `BINARY_EXTENSIONS` or the content sniff would re-admit genuinely binary content classes on a per-name whim and complicate three mechanisms at once. | A hatch overriding all mechanisms was rejected as a correctness hazard the original plan had not even identified. |
| 2026-08-27 | Measurement is two-tier: local fixtures plus this repository gate closure; the operator's local Java/Swift/JS-TS consumer projects validate post-build, disclosed and non-gating. | The p4ea oracle repositories are external distributions, not local paths (recorded precedent: 1p9qa AC-6), but the operator confirmed the projects are locally available to them after a local build; the established operator-side validation pattern fits exactly. | Gating closure on external-project evidence was rejected as an unexecutable required AC. |


## Risks


| Risk | Mitigation |
| --- | --- |
| Consolidation accidentally changes an existing exclusion's behavior. | AC-1 pins every listed name's classification in both directions. |
| The re-include hatch is assumed to cover binary/sniff exclusions. | AC-2 proves the non-override; the config field documentation states the boundary. |
| The measured local reduction is small on the corrected baseline. | Honest outcome: the consolidation documentation and straggler closure stand on their own; the statistics are recorded either way. |
| Version bump re-walks consumer indexes. | Documented convention; content-hash reuse bounds cost. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
