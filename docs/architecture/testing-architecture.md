# Testing Architecture

Owner: Engineering
Status: active
Last verified: 2026-09-04

## Test Tiers

| Tier | Scope | Location | Runner |
|------|-------|----------|--------|
| Framework script unit tests | `docs_lint.py`, `build_pack.py` behavior | `.wavefoundry/framework/scripts/tests/` | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| Dashboard reader/server unit tests | `dashboard_lib.py`, `dashboard_server.py` snapshot and HTTP-handler contract | `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| Historical memory backfill | no-Git inventory, SQLite claim/replay, candidate-only writes, agent-validation gate, deferred publication | `.wavefoundry/framework/scripts/tests/test_memory_backfill.py`; setup/upgrade integration suites | canonical runner |
| Review current-state projection | per-signoff derivation, causal withholding/reapproval, narrative preservation, malformed markers, bounded output | `test_review_evidence.py`; `test_server_tools_lifecycle.py`; upgrade suite | canonical runner |
| Dashboard Markdown presentation | executed shared-renderer DOM behavior, hidden comments, soft wraps/lists, exact shared-caller census, fixed-width overflow geometry, and execution from canonical plus extracted install/upgrade assets | `test_dashboard_server.py`; `test_build_pack.py`; upgrade suites; checked-in 1440×900 and 390×844 browser regression | canonical runner + `WAVEFOUNDRY_BROWSER_TESTS=1` browser tier |
| Fixture-based integration | Docs-lint against fixture repos | `.wavefoundry/framework/scripts/tests/fixtures/` | Same runner |
| Semantic embedding regression | Real fastembed path, model name/dim/determinism/ranking anchors — **skipped** when fastembed is not installed or model not cached | `SemanticEmbeddingRegressionTests` in `test_server_tools_retrieval.py` | Same runner |
| Model-set identity | Synthetic warmed-cache fixtures verify independent model-set selection and matching online-cache attestation, manual-recovery wording (exact asset, standard locations, and no-replacement guarantee), component/file hashes, traversal/link rejection, idempotence, corruption repair, mismatch refusal, and no-downgrade behavior without downloading model bytes | `test_model_bundle.py`, `test_setup_index.py`, `test_build_pack.py` | Same runner |
| Differential equivalence harnesses (wave 1rsh9) | Optimized path vs authoritative path over identical inputs — the registry-backed incremental skip vs the Lance-read delta plan (`RegistryDifferentialTests`), and the secret-scan cache path vs a no-cache full scan through a six-mutation git fixture matrix with the REAL scanner (`DifferentialEquivalenceTests`). Any divergence fails; these are the adoption gates for skip-class optimizations | `test_fts_lexical_layer.py`, `test_secret_scan_cache.py` | Same runner |
| TechDocs external publication oracle (wave 1vry5) | Version-pinned MkDocs/pathspec publication differential, escaped-separator classification table, and finite before/after matcher-cost corpus. This is a permanent source-repository harness, not a runtime dependency or ordinary unit test | `.wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py`; wave-scoped retained JSON artifact | Disposable scratch venv with `mkdocs==1.6.1` and `pathspec==1.1.1`; exact command in the harness docstring |
| Independent-reference review contract (waves 1shv4/1sq4a) | Contract and distribution tests pin the bounded independent-reference rule, code/QA carrier wording, proof ceiling, and install/upgrade propagation. They prove the rule is delivered and internally coherent—not that an agent adhered to it during a review | `test_render_agent_surfaces.py`, `test_setup_wavefoundry.py`, `test_upgrade_wavefoundry.py`, existing `test_review_evidence.py` independence checks | Same runner |
| Build-epoch fault injection (wave 1sed7) | The SQLite-only state contract: epoch state-machine/CAS unit tests (`BuildEpochTests`), structured no-fallback failure injection at every mandatory boundary + a fresh-process kill between fence and finalize (`EpochOrderingAndFaultTests`), legacy meta.json convergence-by-reconstruction (`LegacyConvergenceTests`), and the reader seqlock at the MCP tool boundary — mid-search epoch mutation discards results (`EpochSeqlockConcurrencyTests`) | `test_index_state_store.py`, `test_indexer.py`, `test_server_tools_lifecycle.py` | Same runner |
| Review-protocol propagation and state (waves 1skt1/1slep/1stwj/1tomw/1to78) | Typed carrier-registry census plus public-path integration through fresh setup, packaged install, real full-upgrade extraction, direct `wf render-surfaces`, and self-host reconciliation. Fixtures pin compact authoring, direct canonical `events.jsonl` parsing (the sole machine authority; no receipt or hash sidecar), required judgment refusal, lane-scoped approval chronology, generated-Markdown non-authority, empty-run provenance, serialized append/replay/fault recovery, public MCP registration/schema, missing-carrier creation, Guru-absent execution, idempotency, malformed-ledger fail-closed behavior, initial-delivery close gating, multi-finding repair cycles, progressive multi-lane reverification, legacy batch-run compatibility, aggregate convergence timing, and fixed-role semantic-index exclusion. The crash matrix at the ledger's atomic-replace seam is two-tier: exception-injection cuts at the named boundaries remain as fast equivalents, and true-termination cuts kill a spawned child process (venv python) via `os._exit` at each named boundary (before the ledger replace; after the replace, before projection), with the parent asserting the surviving on-disk state, canonical parseability, and exact-replay convergence; a shipped torn-write known-bad control proves those oracles can fail. A rollback-boundary negative control restores a complete older but internally valid ledger and proves local structural validation accepts it (the documented boundary; Git/backups are the optional history authority) while corruption, partial writes, invalid relationships, and declared-missing authority remain rejected. A role-aware live-surface deletion census fails when shipped code, current seeds/carriers, install/upgrade/package assets, or current architecture/spec docs retain the removed adoption sidecar names, adoption-only symbols, deleted inline-ledger machinery, or prose-evidence helpers outside their bounded roles (the authority facade module is the one legitimate home for the prose helpers); the census is test-inclusive, covering `.wavefoundry/framework/scripts/tests/` with per-file allowances for named negative-assertion and probe sites, every allowance load-bearing (an allowance whose file is gone or no longer carries the token fails the census); archived closed-wave records are excluded. Setup/upgrade/package tests place byte sentinels in historical target waves and prove those paths install source/carriers without scanning or mutating wave history; subsequent public creation is external-ledger-only | `test_review_evidence.py`, `test_events_only_residue_census.py`, `test_render_agent_surfaces.py`, `test_server_tools_lifecycle.py`, `test_indexer.py`, build-pack/setup/upgrade/render integration tests | Same runner |
| Context-efficiency telemetry (wave 1stwj) | Closed-ledger arithmetic for 18 retrieval and five lifecycle tools; exact structural-path census; phase/source/version and event uniqueness across real processes; general attribution; store-identity-loss freeze; accounting-gap poisoning; paired-evaluation quality gate/attachment; lifecycle/reload/upgrade projection; install/package/upgrade non-mutation | `test_context_efficiency.py`, `test_server_context_efficiency.py`, the `test_server_tools*` shards, render/setup/package/upgrade integration tests | Same runner |
| Memory supply and exploration-estimate integrity (waves 1stwm/1sxj7) | Real compact review-event repair chains, admitted-change Decision Logs, escaped pipes, implementation-only anchors, Unicode/evidence identity, concurrent add/propose idempotency, SQLite event replay and origin budgets, exact-match passive/explicit surfaces, current source-cost authority, lazy schema extension, and lifecycle/reload/upgrade projection | `test_memory_records.py`, `test_context_efficiency.py` | Same runner |
| Commit provenance integrity (waves 1sufq/1sxj7) | Canonical local commit identity, anchored landing grammar, explicit metadata authority, mixed blame coverage, conflict propagation, file-relevance labeling, exact public input union, and read-only/traversal controls | `test_commit_provenance.py`, `test_server_context_efficiency.py` | Same runner |
| Memory-retrieval eval (waves 1sufo / 1tbt5) | Hermetic golden set over a synthetic memory corpus scoring the shipped search path and an evaluation-only BM25+semantic RRF candidate: recall@k / MRR, 11 policy/archive/adaptive-freshness invariants, deterministic single-stream controls, and an explicit adoption decision. An optional bounded live pass freezes its sample before scoring and emits aggregate metrics, kind/status counts, and a fingerprint only. The registered 1,000-record lexical budget guards its single-pass cost. See `docs/references/memory-retrieval-eval.md`. | `memory_eval.py` (shipped engine), `tests/eval/memory_golden.json` (test-only fixture), `test_memory_eval.py`, `tests/perf_budget_policy.py` | Same engine; the live pass is the `wf_memory_eval` MCP tool (CLI fallback `--curated-root <repo>`) |
| Memory archival lifecycle and curation (waves 1t8la/1u7uy/1u8r2) | Rename-only body migration, indexed compact-register schema with index-excluded bodies, setup/upgrade retirement of legacy pointer copies plus hard index exclusion and lint refusal, protected-kind eligibility, destructive purge metadata/refusals, purge staging with register-failure rollback and interruption/retry convergence, repo-visible hash-only purged-source suppression across index reset/setup/upgrade, cross-process serialization, consolidation rollback, forbidden-content refusal, bounded detailed consolidation previews, default/history retrieval isolation, semantic/graph explicit-file corpus boundaries, and fixed active-budget signals | `test_memory_records.py`, the `test_server_tools*` shards, `test_indexer.py`, `test_graph_indexer.py`, `test_setup_wavefoundry.py`, `test_upgrade_wavefoundry.py`, `test_docs_lint.py` | Same runner |
| Corpus exclusion census and hygiene (wave 1wfsl, 1wfsn) | Executed-census classification pins at mechanism-class granularity (name / extension-or-sniff / corpus-filter / machine-authority path) over a constructed fixture through the REAL `walk_repo` + `_filter_code_files` (never grep — the wave's false grep censuses are the reason), straggler exclusion (`npm-shrinkwrap.json`, `packages.lock.json`, `*.min.js`, `*.min.css`), re-include hatch scoping (name layer only; extension/sniff/machine-authority non-override incl. a canonical `events.jsonl` and `docs/scan-findings.json` resurrection attempt), the `files=` seam scan-findings boundary, the walker-version bump, and secret-scanner candidate non-narrowing over a real git fixture | `test_indexer.py` (`CorpusExclusionCensusTests`) | Same runner |
| Prose-format section chunking (wave 1wfsl, 1wfsm) | rst underline/overline adornment and adoc `=`-run section recognition with positive and adversarial-negative fixtures (mid-paragraph separator rows, literal-block adornment, `=`-lines inside listing blocks), breadcrumb + doc-kind emission, code-directive/listing extraction as code-kind, noise bounding on code-heavy fixtures, corpus-membership + `_KNOWN_TEXT_EXTENSIONS` + version-bump pins, and the markdown byte-identity differential against a pre-change-chunker snapshot fixture | `test_chunker.py` (`RstChunkerTests`, `AdocChunkerTests`, `ProseFormatNoiseBoundingTests`, `MarkdownDifferentialTests`), `test_indexer.py` (`CorpusExclusionCensusTests.test_rst_adoc_walk_and_docs_layer_membership`) | Same runner |
| Spec-format family (wave 1wik9, 1wfso) | per-format detection positives (AsyncAPI 2.x YAML and 3.x JSON incl. the detection-order pin against schema-shaped roots; SDL with and without descriptions; proto2 and proto3), unit shapes with symbol-path breadcrumbs and deterministic identities, detached-comment and option non-units, gate-off and degenerate byte-identical line-window fallbacks, other-extension lookalike negatives in the extended negatives snapshot (mutation-proven), the AC-4 grammar-independence pin (parsers consult no tree-sitter loader), per-format golden subsets with the specs harness per-format grouping, and per-format content-coverage differentials with revert-simulation | `test_chunker.py` (`SpecFamilyTests`, `SpecChunkingTests`), `tests/fixtures/retrieval_golden/specs/` | Same runner |
| Guidance-surface drift guards (wave 1wip2, 1wgwn) | seed-211/guru.md Index Scope byte-parity with heading-uniqueness pins (mutation-proven on a one-byte scratch divergence; cross-referenced with the pre-existing Citation-block oracle in test_server_tools_lifecycle), and the CHANGELOG version-constant claims engine in both homes: docs-gate Unreleased-only scoping (dated-top-section no-op pinned — the post-release deadlock case), seeded-stale catch, historical-quoted-phrasing immunity, and the packaging-gate refusal reproducing the pm1l escape | `test_shipped_reference_docs.py` (`GuruIndexScopeParityTests`), `test_docs_constants_lint.py` (`ChangelogConstantsTests`), `test_build_pack.py` (stale-claim refusal) | Same runner |
| Retrieval loose ends (wave 1wl7u, 1wh1b) | notebook doc-code routing (docs-table eligibility, breadcrumb injection, code cap, output invisibility, oversized-cell split, the rewritten kind pins that supersede the 1whup preserved-invisibility disposition), repeat-only prose-id ordinals (`ProseIdOrdinalTests`: md/rst/adoc duplicates, H3-split composed bases, line-window bases, preamble and doc-summary sentinel reservations, the `Setup 2` legal-slug trap, tilde unforgeability, fence-base stability, single-title bare-id stability), the `.drawio` generated-walk exclusion (the 1wl7w/1wl7v label-extraction supersession later re-admitted both tool-diagram extensions; the reinclude pin survives on `.snap`), the regenerated markdown differential with a duplicate-titled and a notebook source (classified deltas, revert-simulation discrimination), and the per-line coverage differential over id-collapse surviving rows | `test_chunker.py` (`ProseIdOrdinalTests`, `DocCodeRoutingTests`, `JupyterChunkerTests`, `MarkdownDifferentialTests`), `test_indexer.py` (walk + reinclude pins), `tests/fixtures/retrieval_golden/prose/ipynb/` | Same runner |
| Diagram label extraction (wave 1wl7w, 1wl7v) | drawio extraction shape (compressed/plain form equivalence by executed re-inflation, object/UserObject wrapper labels, two-layer HTML decode, auto `Page-N` stem fallback, multi-page `#diagram`/`#diagram~k` ids with oversized-split composition, the bounded per-page inflate cap pinned by an under-disk-cap deflate bomb, degenerate zero-chunk classes, docs membership/language/cap pins, injection idempotence, committed-fixture wrapper extraction), excalidraw extraction (originalText preference, isDeleted ghost and empty-string skipping, files-blob blindness, degenerate classes, committed-fixture ghost pin), the walk re-admission supersession pins (both extensions out of the generated set, WALKER 15, `.snap`-anchored layer non-vacuity, hatch pin), the extraction extension-set disjointness census, and the authored-label coverage differential with revert-simulation and chunk-level anchor uniqueness | `test_chunker.py` (`DrawioChunkerTests`, `ExcalidrawChunkerTests`), `test_indexer.py` (re-admission pins), `tests/fixtures/retrieval_golden/diagrams/` | Same runner |
| Diagram-file chunking (wave 1wik9, 1whuq) | per-family fixture shape and breadcrumb tests (mermaid frontmatter title, plantuml title directive, DOT graph identifier incl. quoted names, stem fallback), degenerate inputs (empty, oversized via the universal guard), chunker-only registration pins (extension-set disjointness in the chunker; never `_KNOWN_TEXT_EXTENSIONS`, `SOURCE_CODE_EXTENSIONS`, `BINARY_EXTENSIONS`, or the generated set in the indexer), docs-split membership in and out of docs roots, the binary-impostor OLE `.dot` sniff exclusion, and the frozen 9-query `diagrams` golden set with its executed eligibility census | `test_chunker.py` (`DiagramChunkerTests`), `test_indexer.py` (`DiagramCorpusMembershipTests`), `tests/fixtures/retrieval_golden/diagrams/` | Same runner |
| Doc-code routing and kind filtering (wave 1wik9, 1whup) | doc-code emission from all three doc-family emitters with file-pass-scoped ordinal identities (duplicate-titled-section collision pins), per-emitter breadcrumb truth (baked markdown, injected rst/adoc, bare preamble), code-cap selection, prompt fence-inline exemption, notebook doc-code routing (the 1wl7u/1wh1b executable supersession of the preserved state), per-emission-site content-coverage invariant, docs-table routing via `_is_docs_kind`, and the server-side kind-filter enforcement including a real-Lance semantic-path raw-SQL filter regression and the `code_ask` partition-tuple complementarity pin; the regenerated markdown differential snapshot with the specs-negatives zero-delta assertion; the extended prose golden set with unique-anchor fence queries and the content-anchored recall supplement | `test_chunker.py` (`DocCodeRoutingTests`, `MarkdownDifferentialTests`), `test_indexer.py` (`DocCodeTableRoutingTests`), `test_server_tools_retrieval.py` (`DocCodeKindFilterTests`), `tests/fixtures/retrieval_golden/` | Same runner |
| Spec-aware chunking detection and differential (wave 1wfsl, 1wfr8) | Detection positives (OpenAPI 3.x YAML+JSON, Swagger 2.x, JSON Schema dialect-URI and schema-shaped roots) and negatives (kubernetes/CI/compose configs, schemastore `$schema` configs, arbitrary JSON, and the adversarial schema-shaped data file) over the COMMITTED spec fixture corpus; operation/definition chunk shapes with baked breadcrumbs and deterministic identities; kind="code" layer-boundary pin; the `indexing.max_treesitter_parse_bytes` cap boundary on the spec path; the config gate (`WAVEFOUNDRY_SPEC_CHUNKING`); the non-spec byte-identity differential against a pre-change-chunker snapshot; and the golden-set measurement harness (`run_retrieval_eval.py`) whose before/after results are wave evidence | `test_chunker.py` (`SpecChunkingTests`), `tests/fixtures/retrieval_golden/` | Same runner |
| Standing production retrieval evaluation (wave 1seaw, 1sear) | Generation-frozen, cached/offline evaluation of the current public `code_ask`, `code_search`, `docs_search`, and `code_lexical` response paths over a versioned calibration/holdout corpus. Reports Recall@k, nDCG@k, agentic MRR@10, abstention, warm p95, cold start, and serialized-envelope size, and binds each report to the production-module identity digest, run timestamps, and the resolved declaration spans behind symbol anchors (declaration-span intersection, never a same-file mention); it is intentionally outside the hermetic default test run because it requires a published index and cached models. | `.wavefoundry/framework/scripts/retrieval_eval.py`; `docs/evals/retrieval-quality-golden.json`; standing baseline `docs/reports/retrieval-quality-post-1wybs.json` (a single run recorded at the `1wybs` delivery review, verdict `fail` under the drift disposition recorded in that wave's record; the reference only until the next evaluator edit, after which the next ranking wave records its own before-receipt; earlier receipts either bind a superseded evaluator identity and are incomparable, or, for the `1wuju` before-receipt, bind superseded production bytes and are no longer the reference) | `python3 -B .wavefoundry/framework/scripts/retrieval_eval.py --root . --fixtures docs/evals/retrieval-quality-golden.json --out docs/reports/retrieval-quality-<change-id>.json --baseline docs/reports/retrieval-quality-post-1wybs.json` |
| Manual docs gate | MCP **`wf_validate_docs`** succeeds, **or** `wf docs-lint` passes | MCP / repo root | `wf_validate_docs` / `wf docs-lint` |
| Manual gardener | MCP **`wf_garden_docs`**, **or** `wf docs-gardener` | MCP / repo root | `wf_garden_docs` / `wf docs-gardener` |

### Canonical Runner, Measured Scheduling, and the Server-Tools Shard Family (wave 1tmtx)

The canonical runner (`python3 .wavefoundry/framework/scripts/run_tests.py`)
runs each `tests/test_*.py` file in its own subprocess, capped at six
concurrent workers, in alphabetical name order. Alphabetical is the MEASURED
schedule: a counterbalanced comparison (A-T-T-A) against a timing-guided
longest-first candidate, run on a byte-identical digest-bound timing manifest
and unchanged runner source, selected alphabetical (means 130.5 s vs 136.8 s;
evidence under `docs/waves/1tmtx test-suite-performance/evidence/`). The
benchmark-only interface `--schedule-control bootstrap|alphabetical|timing
--timings-file <path>` reproduces that comparison and never touches the
production last-green cache.

Every run prints per-file elapsed seconds, a bounded top-10 slowest-file
summary, aggregate worker service time, and the aggregate skip count; a
successful complete run persists an advisory `durations_s` map beside the
last-green cache entry. Timing data never authorizes a skip or a pass, and
neither the cache file nor the timing manifest is a public compatibility API.
`--file <basename>` (repeatable) is the focused diagnostic mode for repair
loops: the same lock/subprocess/timeout/artifact-guard path, no cache or
timing access, output labeled as focused. Focused runs are never delivery
evidence — one full canonical isolated run remains the delivery authority.

The former 37k-line `test_server_tools.py` monolith is a three-shard family
plus a non-discovered support module: `test_server_tools.py` (server
core/infra; hosts the framework-wide subprocess isolation guard and the
reader-census test), `test_server_tools_retrieval.py` (retrieval, graph, and
index tools), `test_server_tools_lifecycle.py` (wave lifecycle, review, and
governance tools), and `server_tools_support.py` (shared fixtures and the
subprocess-scan seams; no `TestCase`, no `test_*` names, no module-level
mutable server state). The split preserved the exact frozen
`(class, test_method)` identity set and per-class AST fingerprints (mechanical
proof in the wave's `verify_shards.py` evidence).

### Semantic Embedding Regression Tier

These tests exercise the real `fastembed` embedding path — no mocks. They pin four properties as regression anchors so that a future model upgrade fails loudly rather than silently:

- **Model name** — independent `DOCS_MODEL` and `CODE_MODEL` selectors both equal `Snowflake/snowflake-arctic-embed-s`
- **Dimension** — output vector length == 384
- **Determinism** — same text always produces the same vector
- **Ranking order** — a semantically close query ranks its best match above an unrelated chunk

When a model upgrade is intentional, update the two `_EXPECTED_*` constants beside `SemanticEmbeddingRegressionTests` in `test_server_tools_retrieval.py` and follow the checklist in `docs/architecture/embedding-model.md`.

### Independent-Reference Review Evidence

Independent-reference verification is a review-evidence technique for any implementation change, not a new test tier or a replacement for independent approval. Within seed 209's finite probe budget, code review identifies a credible reference that does not share the implementation's assumptions and the exact promised property; QA names the assertion that would falsify each load-bearing correctness, complexity, compatibility, or parity claim. For deterministic mechanisms a fixed seed or durable fixture makes generative probes reproducible, invalid inputs are rejected before comparison, and incidental representation differences stay outside the assertion.

The worked pattern is a fallback parser compared with a grammar-backed parser over valid generated declarations, asserting only initializer ownership identity. Named fixtures retain diagnosed edge cases; the differential comparison diversifies the reference used to explore the valid surface. Because both parsers can still share a misunderstanding, specification-derived or metamorphic assertions cover plausible common-mode failures. Implementer-produced results remain `independent: false`; carrier and rendering tests prove distribution only.

### TechDocs External Oracle Tier

The TechDocs matcher has a permanent differential harness under
`.wavefoundry/framework/scripts/tests/oracle/`. It provisions no dependencies
itself: the operator creates a disposable virtual environment and installs the
exact MkDocs and pathspec versions named in the harness docstring. The harness
prints the observed versions, compares the audit's computed Markdown survivor
set with `mkdocs.structure.files.get_files`, regenerates the escaped-separator
classification table, and writes the wave-scoped finite cost-corpus artifact.

The canonical framework runner discovers only top-level `tests/test_*.py`, so
this tier does not introduce skips or optional imports into the dependency-free
unit suite. Packaging excludes `scripts/tests`, so the oracle is source-repo
verification rather than shipped runtime surface. Its cost result is explicitly
the slowest observation in the named finite corpus; the public worker deadline,
not this sample, remains the aggregate availability bound.

### Dashboard Browser Geometry Tier

The canonical per-file runner always discovers the fixed-viewport dashboard
regression, but skips its Chrome-dependent execution unless
`WAVEFOUNDRY_BROWSER_TESTS=1` is set and both Node and Chrome are available.
The opt-in tier executes the checked-in `wfds.js` renderer with the real
dashboard stylesheet, loads the result into exact-size 1440×900 and 390×844
iframes, and queries browser DOM geometry. It asserts page, dialog, and body
`scrollWidth <= clientWidth`, non-vacuous prose/inline/table coverage, zero
ordinary-prose or inline-code overflow, hidden ownership comments, and
table-local horizontal scrolling. This is a portable capability-gated browser
tier; retained screenshots are supporting evidence, not the executable gate.

### Context-Efficiency Telemetry Verification

The telemetry suite treats efficiency reporting as a closed accounting contract:

- An exact public-tool census pins the `context_avoided` field on all 18 eligible
  retrieval/navigation tools, including `code_keyword`, `code_pattern`, and
  `code_constants`, and excludes path-list-only tools.
- Independent helpers compute `ceil(UTF-8 bytes / 4)` for request, complete
  response, prompt, and source size. Fixtures pin the closed equation rather
  than trusting per-call display fields.
- Baseline-classification tests grow and shrink an indexed file after a build,
  mutate it between capture and comparison, remove it after capturing indexed
  metadata, and exercise paths with no size-bearing proof. Stable matches classify
  as verified; current or captured sizes classify as estimated; no-baseline sources
  are omitted. Telemetry never performs a whole-file rescue read/hash.
- An exact graph-field census proves structural credit is derived only from each
  tool's documented public path fields. Content and structural returns of the
  same source version share one phase credit.
- Real child interpreters contend on SQLite and prove global event replay
  protection plus `(wave, phase, source, version)` uniqueness. New phases and
  changed versions re-credit deliberately.
- Lifecycle fixtures prove every reached handler retains request/response debits,
  while only a newly completed milestone receives the mapped prompt credit.
  General events are producer-scoped. Barrier tests keep two live lease owners
  isolated while two lifecycle writers race to claim one abandoned producer;
  exactly one wins. Missing/ambiguous leases fail safe, and mocked
  native-Windows plus exercised POSIX branches pin the sentinel lock contract.
- Controlled concurrent writers modify lifecycle/evidence/operator prose while a
  telemetry projection runs; a dedicated interleaving includes the mutating docs
  gardener. The shared project-global lock must preserve every unrelated byte,
  replace only the marker-owned block, and leave a failed projection pending.
  Reload and upgrade barriers refuse to proceed while pending projection fails.
- Checkpoint known-bad fixtures cover duplicate/unmatched markers, malformed JSON,
  wrong schemas, invalid state shapes, duplicate state comments, and altered
  rendered tables through the same strict validator used by runtime parsing and
  docs lint.
- Sealed-close fixtures use the publication generation as a cutoff, inject
  failure between CAS and compaction, and prove retry through the pending-wave
  census. Before/after snapshots are byte-identical, payload rows disappear,
  replay tombstones reject old event IDs, stale process focus redirects to
  general, and reopen creates a new phase above the compact floor.
- Fault injection proves a failed event transaction writes durable gap poison and
  suppresses positive totals, including exceptions raised before the ordinary
  commit call; failure to persist both event and poison returns
  `telemetry_persistence_failed`.
- This is the first shipped telemetry schema, so no versioned pre-release
  compatibility fixture or legacy-evidence table exists. Replacing the current
  store freezes active history as `credit_history_unavailable`; closed
  validator-valid state can restore only its sealed compact floor.
- Paired-evaluation fixtures require pre-registration, exact applicability,
  at least five completed quality-equivalent pairs, conservative minimum
  residual, authoritative phase-ledger direct-net equality, idempotent replay,
  explicit replacement, and revocation.
- Fresh setup and full upgrade fixtures begin without any of the six lifecycle
  prompts, exercise the public renderer, and prove packaged missing-only
  templates materialize all six, including `memory-review`, while leaving historical wave/event bytes and
  existing project prompt prose unchanged.
- Upgrade transition fixtures run an old in-process policy block followed by the
  freshly extracted renderer, then prove that only the shared upgrade-policy marker
  changes, outside prose is byte-preserved, the destination was preflighted before
  sibling writes, and memory curation/purge was never invoked.
- Direct SQL checks assert that query text, responses, prompts, source paths,
  secrets, and conversations are absent.
- Fresh setup, packaged install, public render, and full upgrade fixtures deliver
  the implementation, six prompt baselines, and managed `.wavefoundry/logs/`
  ignore without eager sidecar creation. Historical `wave.md` and `events.jsonl`
  byte sentinels remain unchanged until a later mutating lifecycle boundary.

Performance claims use repeated, warm, paired samples against an uninstrumented
control, never one-shot wall-clock assertions. Contention, source-count, and
projection samples report distributions; correctness does not depend on a
machine-specific one-shot timing threshold.

## Performance-Test Budget Policy (wave 1seax / 1t3zv)

The framework suite runs up to six parallel workers; sustained back-to-back
runs saturate the machine, and tight wall-clock budgets then flake on
scheduler contention even when the guarded operation is healthy (recorded:
an isolated 120 ms result failing a 200 ms budget; an isolated 240 ms result
failing a 3 s budget at 3.2 s contended). Every wall-clock budget in the
suite follows the policy in
`.wavefoundry/framework/scripts/tests/perf_budget_policy.py`:

- a NEW timing budget must record an isolated reference measurement (and a
  contended one when available) and set the threshold with measured
  contention headroom — at least ~3x the worst observed contended time,
  while staying an order of magnitude under a genuine regression;
- budget assertions go through `assert_within_budget`, whose failure message
  reports the observed timing, the threshold, and the isolated reference
  (the triage signal separating contention from regression);
- prefer RELATIVE bounds (a ratio of two timings from the same run — see the
  chunker's `2.6x` bound) where the invariant allows: they are
  contention-immune by construction;
- never globally serialize the suite, and never inflate a budget without the
  measured basis (a deliberately injected meaningful slowdown must still
  fail — pinned by `test_perf_budget_policy.py`).

## Close-Time Verification: the framework test receipt (wave 1wur7)

The wave close gate gained one verification step. `wf_close_wave` reads the
existing `.wavefoundry/framework/test-cache.json` receipt written by
`run_tests.py` and requires `result == "ok"` with an `inputs_hash` matching the
current framework tree; a missing, red, stale, or unreadable receipt is reported as
`framework_test_receipt_not_proven`. The gate REUSES `run_tests.py`'s own
`_hash_inputs` so the gate and the writer cannot drift, and it runs no suite and
spawns no subprocess. The runner is loaded from the target root's own copy, and
because a server may be launched against a different `--root` the borrow is
contained: the runner path must resolve inside the target root, all FIVE of the
runner's import side effects are undone (`sys.dont_write_bytecode`, the
dashboard-suppression variable, its `sys.path` insert, the tool-venv activation
that prepends `site-packages`, and every module the borrow registers in
`sys.modules`), and any failure to load or to call it
— `SystemExit` from the venv guard included — degrades to `unreadable` rather
than raising out of the tool call.

`state` is one of `not_applicable`, `proven`, `missing`, `not_ok`, `stale`, and
`unreadable`. The receipt's hash covers `.wavefoundry/framework/` only, so only
receipt STALENESS is framework-scoped; because the receipt is written only on a
whole-suite pass, a failure triggered by content under `docs/` prevents a NEW
receipt from being written; when the framework tree also changed the standing
receipt is stale and close is blocked, while in a documentation-only wave a
current green receipt persists and close is not blocked despite a red suite. A green receipt attests the framework code, not the tree:
the check is neither a whole-repository guarantee nor a whole-repository
exemption. Run the suite last before close — any edit under
`.wavefoundry/framework/` invalidates the receipt. Where the
runner is absent — every repository that consumes the packaged framework, since
`build_pack.py` excludes the runner, `scripts/tests`, and the receipt — the check
is a documented no-op.

This is the machine-visible half of moving whole-suite assertions out of per-change
acceptance criteria; the feedforward half is seed `170-plan-feature.prompt.md`
*"Acceptance criteria assert what the change controls"* and the sensor half is the
`docs-lint` AC-shape validator.

## Standing Gate Identity and Reproducibility Contract (wave 1wur7)

**Production identity now binds the cluster carrier (wave `1wpaj`).**
`graph_cluster.py` joined the production retrieval modules and
`CLUSTER_BUILDER_VERSION` joined the production version constants, so a cluster
artifact change moves the production digest. This is recorded as **provenance
honesty, not as a detector**: across the tool set the evaluator actually
measures, the cluster artifact reaches query time only through memory-advisory
ranking, so binding it does not give the gate a new way to catch a citation
regression. The graph tools do read the artifact by other paths, which is why
the claim is scoped to the measured set rather than stated generally.

**Eleven tuning variables are identity, recorded as values (wave `1wpaj`).**
The four `WAVEFOUNDRY_GRAPH_BETWEENNESS_*` knobs,
`WAVEFOUNDRY_MAX_TS_PARSE_BYTES`, `WAVEFOUNDRY_MAX_LINE_SCAN_BYTES`, the four
`WAVEFOUNDRY_GRAPH_PARALLEL_*` knobs, and `WAVEFOUNDRY_SPEC_CHUNKING` change
centrality method, artifact shape, extraction breadth, rebuild duration, or
which chunks a spec file produces — all while moving no module hash, so a
receipt taken under different values would otherwise compare as identical. They
are recorded as resolved VALUES in their own compared key and are deliberately
**not** retrieval toggles: that set records presence rather than value, and
treats any set name as an active quality toggle requiring operator review — and
the indexer MANAGES two of the eleven in the process environment on every build,
assigning the spec-chunking one when a workflow override is present and popping it
otherwise, so either branch is what the frozen snapshot captures, which would make a run's own required verdict unreachable. The
values are frozen at evaluator import so an in-process assignment cannot move
the snapshot mid-run. `WAVEFOUNDRY_SPEC_CHUNKING` was missing from the first
delivery of this set and was added at delivery review: without it, two runs
built under different spec-chunking settings compare as identical and any
resulting quality difference is attributed to the code under test.

**Per-fixture regressions cannot hide behind an aggregate (wave `1wpaj`).** The
comparison now walks every `(fixture_id, tool)` key across both reports,
requires identical key sets and exactly one row per key, and compares every
gate metric under the evaluator's own key mapping, since two of the five gate
names do not exist on a case row. Null semantics are explicit: a baseline value
against a current null fails, a current value against a baseline null is
reported without failing, and null against null is a skip. Without the mapping
the two affected metrics would read null on both sides and silently disable
themselves, which is the masking channel this oracle exists to close.

**Report I/O is confined and never overwrites (wave `1wpaj`).** A baseline or
output path must be a regular direct child of `docs/reports/` whose basename
begins with `retrieval-quality-`; the prefix is part of the rule rather than a
convention, because the repository's ignore rule keys on it and a report written
outside it enters the retrieval corpus and contaminates the next run's own
measurement. Outside-root paths, symlinked components, hard-link and path
aliases, and non-regular files are rejected, the three confining ancestors are
checked explicitly since the no-follow open flag covers only the final
component, and the baseline is opened once without following symlinks and hashed
from that handle before parsing. Writes land in a same-directory temporary that
satisfies the same prefix rule, publish by atomic link, unlink the temporary in
a `finally`, and verify a single link afterwards. The three closed-`1seaw`
receipts are protected inputs and can never be destinations.

**Identity is compared per comparison kind.** The repository root (path, device,
inode), the index directory, and the state-store path bind every kind; the state
store file's own device and inode bind only a `same_generation_pair`, where "one
frozen physical store" is what makes a jitter measurement mean anything. Binding
the inode across generations refused the exact case `cross_generation` exists to
cover, a controlled rebuild. `SAME_GENERATION_INDEX_IDENTITY_KEYS` is the single
source of truth and a test pins it equal to what `_index_identity` emits, so a
field added later cannot go silently uncompared.

**Reproducibility is measured on the stable statistics.** A pair whose warm
sample FLOOR or MEDIAN moved past `PAIR_JITTER_THRESHOLD` was measured under
external load, is marked `pair_contended`; a later comparison that inherits its jitter
reports `inherited_contended_baseline` per tool with the recovery rather than
refusing, since latency is advisory for every kind. A baseline that is a single
run (no pair-derived `jitter_ratio`) is accepted at the 25% floor with
`jitter_source: single_run_floor` and `contention_judged: false` (wave `1wuju`);
no within-run estimator is computed, because the recorded fixture refuted every
candidate. The p95 shift
is recorded but excluded from the band, because the band is `max(25%, 3 x jitter)`
applied to the p95 and including it would both widen a quiet pair's band on tail
noise and make the latency clause unreachable.

An evaluator-only edit records no close-time baseline (wave `1wybq`): an edit
that moves `evaluator_identity` without moving `production_identity` leaves the
standing receipt incomparable, and the next wave that changes production
retrieval bytes records a before-receipt with the current evaluator and an
after-receipt, compared as `cross_generation` in this repository because the
production modules are indexed and the preflight refuses a stale index; a
cross-generation comparison attributes corpus drift to the change under the
zero-tolerance regression rule, so a `fail` is read together with the
production diff between the two receipts' identity blocks. Full
contract: `docs/contributing/review-and-evals.md`.

**Latency is advisory for every comparison kind** (operator decision at the
wave `1wur7` close): the clause is computed and recorded for
`same_generation_pair`, `production_change_same_generation`, and
`cross_generation` alike, each with a reason, and routes to
`operator_review_required`; none is a hard violation and none is dropped. The
retrieval-quality floors and the response-size ceiling remain hard.

## Landing Rule for Guards (wave 1wuju)

A guard, validator member, carve-out, or tuning constant is landed only when a
named test fails with it deleted or loosened; a pin that passes for an unrelated
reason is not a pin. The implementer records the mutant and the failing test in
the change document's Progress Log before requesting review, and each delivery
lane reports a mutation table (mechanism, mutation, failing test or NOT CAUGHT)
as the prose projection of its `known_bad_detection_method: focused-mutation`
evidence. Review rounds run against a frozen tree: the briefing packet carries a
`tree_fingerprint`, a `time_budget`, and a `sweep_rule`; repairs are batched once
per round and the tree is re-snapshotted once. A census is re-derived whenever
its predicate moves and is quoted only with the predicate that produced it; a
figure carried forward from an earlier predicate is a stale claim, not evidence.
Seeds 180, 190, 209, 214, 221, and 239 carry the rules.

## Graph Fidelity Corpus and Declared Gaps (wave 1wpie)

`graph_quality_eval.py` scores the fixed corpus at
`docs/evals/graph-quality-golden.json` through a frozen relation-to-public-tool
matrix. Two rules keep it honest.

**Every scored relation needs both sides.** A relation with no expected edge, or
no forbidden opportunity, scores vacuously: precision or recall is undefined and
the relation proves nothing. `load_corpus` refuses such a corpus outright.

**False positives and recall gaps are graded differently.** A false positive is
an edge that is simply not true, so the gate is zero, always. A recall gap is a
measured limitation of the extractor, so it is DECLARED rather than hidden.
Each entry in `known_gaps` names an expected edge the graph does not currently
produce, the evidence that isolated it, and a stable id. The suite asserts the
declared set equals the actual miss set **exactly**, in both directions: a new
miss fails because it is undeclared, and a repaired miss also fails, so an
improvement cannot land while the corpus still describes it as broken. A gap
that does not correspond to an expected edge is rejected at load, because a gap
for an edge nobody expects is a claim about nothing.

**A report says what produced it.** `--report <path> --label baseline|post`
writes an identity-bound report: corpus digest, evaluator source, the extraction
and query sources actually loaded, graph and cluster builder/schema versions, the
graph input fingerprint, repository provenance, environment and clustering
backend, and a digest over the report's own content. Evaluator identity and
production identity are recorded SEPARATELY, because the normal comparison is one
instrument reading two productions; a single combined digest would hide exactly
the difference being measured. `production_identity.source_root` records where
the measured production was loaded from, so a baseline taken from a predecessor
checkout is not misread as the working repository. `verify_report_pair` reports a
delta as attributable only when the corpus and the instrument both held still.
The two report paths join `.aiignore` like every other standing report family, so
a measurement never becomes its own search answer.

**Controls live where the walker indexes them.** The Evidence/Data positive and
negative controls sit under the owning wave's `evidence/` directory, not beside
the other eval fixtures. A re-derived census of the persisted graph found
`docs/evals/` and `docs/reports/` contribute zero nodes each while wave evidence
trees contribute 2,758; a control filed with the fixtures would never be indexed
and every assertion about it would pass vacuously. Each classification assertion
is therefore preceded by a presence assertion, so an unindexed or relocated
control FAILS instead of passing silently.

## Engine Rewrites Are Judged Differentially (wave 1x4ol)

The secrets ruleset is Gitleaks schema, written for Go's RE2, and it runs on
Python's `re`. RE2 guarantees linear time; `re` backtracks. A pattern that is
safe upstream can be quadratic here. Eleven of 280 rules open with two nested
bounded lazy spans over the same class, which a backtracking engine explores at
roughly 2,600 split points per start position; a further 120 open with a single
lazy span that the collapse does not reach. Wave `1x4ol`
collapses that shape to a single span at load, in the RE2-to-Python shim, never
in the ruleset data.

**A rewrite is judged by identical match sets, not by its own output.** The
equivalence claim is that the rewritten pattern accepts exactly the language of
the original. That is asserted three ways, all against inputs frozen BEFORE the
engine edit existed: a seeded random corpus reproduced from its recorded seed, a
hand-authored true-positive and known-negative fixture validated against the
unmodified engine, and every match the unmodified engine recorded over the real
repository, replayed at the same span with the same captured groups. A single
divergence fails the change. A fixture written after the rewrite proves nothing
about what stopped matching, which is why the freeze precedes the edit in the
execution graph.

**The rewrite is surgical.** It matches one exact literal shape and leaves every
other pattern byte-identical, asserted by round-tripping the whole ruleset. A
broader rewriter would be a new engine responsibility and needs its own review.

**No coverage lever is used.** The operator declined a time bound. The scanner
scans every file it scanned before; the set is asserted identical over the real
repository, and no new skip reason exists.

## Docs-lint Sensor Polarity (wave 1wuju)

Docs-lint sensors carry a registered polarity (`wave_lint_lib/constants.py`
`SENSOR_POLARITY_REGISTRY`). An `advisory` sensor's findings travel the same
validator run as failures but reach the `WARNING:` channel with the sensor named,
so `docs_lint.py` exits 0 and `run_validate` returns `passed: true` with
`warnings`; every lifecycle gate, the install audit included, renders them as
`docs_lint_warning` diagnostics with `advisory: true`. A new sensor ships advisory and flips to `blocking` only in
a recorded change with field data; the AC-locality sensor is the first
registrant. Unregistered validators keep their blocking polarity.

## Evaluator Reported Statistics (wave 1wur7)

The standing retrieval gate's per-tool `performance` block now records
`warm_floor_ms` and `warm_median_ms` beside `warm_p95_ms`, plus
`p95_is_maximum`, `small_sample_estimate`, and `minimum_warm_samples`. A
`same_generation_pair` additionally records `jitter_components`
(floor/median/p95), `pair_jitter_threshold`, and `pair_contended`; a comparison
whose baseline is a single run records `jitter_source: single_run_floor`,
`pair_contended: null`, and `contention_judged: false` instead. Pair jitter is
the larger of the floor and median shifts; the p95 shift is recorded but kept out
of the band, because the band is `max(25%, 3 x jitter)` applied to the p95 and
feeding the p95 shift back in would make the latency clause unreachable. Full
contract: `docs/contributing/review-and-evals.md`.

## Test File Locations

| Test File | What It Tests |
|-----------|--------------|
| `.wavefoundry/framework/scripts/tests/test_docs_gardener.py` | docs_gardener behavior |
| `.wavefoundry/framework/scripts/tests/test_build_pack.py` | build_pack.py behavior |
| `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` | dashboard snapshot readers, port selection, and HTTP handler responses |
| `.wavefoundry/framework/scripts/tests/fixtures/docs_lint/base/` | Fixture target repo for docs_lint tests |

## Doubles Policy

- No mocking of file I/O; tests use fixture directories as real file trees.
- Tests do not connect to external services; all operations are local file reads/writes.

## CI / CD

No automated CI pipeline currently. All tests run manually.

Minimum verification bar for any framework script change:
1. `python3 .wavefoundry/framework/scripts/run_tests.py` passes (no bytecode: use `-B` flag or the run_tests.py wrapper)
2. Docs gate: **agents** — MCP **`wf_validate_docs`** succeeds (use **`wf_garden_docs`** first when metadata needs refresh); **CI / no MCP** — `wf docs-lint` passes on the Wavefoundry repo itself

## Framework Script Hygiene

Run tests without writing bytecode: `python3 -B .wavefoundry/framework/scripts/run_tests.py`. If caches were written, clean them:

```bash
find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
```

## Minimum Verification Bar for Cross-Module Changes

Any change touching `.wavefoundry/framework/scripts/wave_lint_lib/` or `docs_lint.py`:
- All existing fixture tests must pass
- Docs gate: **`wf_validate_docs`** (MCP) or **`wf docs-lint`** (CLI) on the Wavefoundry repo

Any change to `docs/prompts/prompt-surface-manifest.json` or `.wavefoundry/framework/VERSION`:
- **`wf_validate_docs`** or **`wf docs-lint`** must pass (manifest `framework_revision` validation)

Agent-memory supply or validation changes additionally require:

- record parser/lint parity for source-event and validation metadata;
- executable promote/retain/reject/rewrite paths, including serialized rewrite
  and explicit partial-failure recovery;
- re-proposal after rejection/supersession proving the source is not regenerated;
- close-time missing/pending validation diagnostics and a zero-memory control;
- install and upgrade carrier checks; and
- a bounded real-wave backfill report whose activated records are individually
  checked against evidence and the current target.
