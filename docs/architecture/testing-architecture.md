# Testing Architecture

Owner: Engineering
Status: active
Last verified: 2026-07-20

## Test Tiers

| Tier | Scope | Location | Runner |
|------|-------|----------|--------|
| Framework script unit tests | `docs_lint.py`, `build_pack.py` behavior | `.wavefoundry/framework/scripts/tests/` | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| Dashboard reader/server unit tests | `dashboard_lib.py`, `dashboard_server.py` snapshot and HTTP-handler contract | `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| Historical memory backfill | no-Git inventory, SQLite claim/replay, candidate-only writes, agent-validation gate, deferred publication | `.wavefoundry/framework/scripts/tests/test_memory_backfill.py`; setup/upgrade integration suites | canonical runner |
| Review current-state projection | per-signoff derivation, causal withholding/reapproval, narrative preservation, malformed markers, bounded output | `test_review_evidence.py`; `test_server_tools.py`; upgrade suite | canonical runner |
| Dashboard Markdown presentation | executed shared-renderer DOM behavior, hidden comments, soft wraps/lists, exact shared-caller census, fixed-width overflow geometry, and execution from canonical plus extracted install/upgrade assets | `test_dashboard_server.py`; `test_build_pack.py`; upgrade suites; checked-in 1440×900 and 390×844 browser regression | canonical runner + `WAVEFOUNDRY_BROWSER_TESTS=1` browser tier |
| Fixture-based integration | Docs-lint against fixture repos | `.wavefoundry/framework/scripts/tests/fixtures/` | Same runner |
| Semantic embedding regression | Real fastembed path, model name/dim/determinism/ranking anchors — **skipped** when fastembed is not installed or model not cached | `SemanticEmbeddingRegressionTests` in `test_server_tools.py` | Same runner |
| Differential equivalence harnesses (wave 1rsh9) | Optimized path vs authoritative path over identical inputs — the registry-backed incremental skip vs the Lance-read delta plan (`RegistryDifferentialTests`), and the secret-scan cache path vs a no-cache full scan through a six-mutation git fixture matrix with the REAL scanner (`DifferentialEquivalenceTests`). Any divergence fails; these are the adoption gates for skip-class optimizations | `test_fts_lexical_layer.py`, `test_secret_scan_cache.py` | Same runner |
| Independent-reference review contract (waves 1shv4/1sq4a) | Contract and distribution tests pin the bounded independent-reference rule, code/QA carrier wording, proof ceiling, and install/upgrade propagation. They prove the rule is delivered and internally coherent—not that an agent adhered to it during a review | `test_render_agent_surfaces.py`, `test_setup_wavefoundry.py`, `test_upgrade_wavefoundry.py`, existing `test_review_evidence.py` independence checks | Same runner |
| Build-epoch fault injection (wave 1sed7) | The SQLite-only state contract: epoch state-machine/CAS unit tests (`BuildEpochTests`), structured no-fallback failure injection at every mandatory boundary + a fresh-process kill between fence and finalize (`EpochOrderingAndFaultTests`), legacy meta.json convergence-by-reconstruction (`LegacyConvergenceTests`), and the reader seqlock at the MCP tool boundary — mid-search epoch mutation discards results (`EpochSeqlockConcurrencyTests`) | `test_index_state_store.py`, `test_indexer.py`, `test_server_tools.py` | Same runner |
| Review-protocol propagation and state (waves 1skt1/1slep/1stwj) | Typed carrier-registry census plus public-path integration through fresh setup, packaged install, real full-upgrade extraction, direct `wf render-surfaces`, and self-host reconciliation. Fixtures pin compact authoring, direct canonical `events.jsonl` parsing, required judgment refusal, lane-scoped approval chronology, generated-Markdown non-authority, empty-run provenance, serialized append/replay/fault recovery, bounded prefix proof, public MCP registration/schema, missing-carrier creation, Guru-absent execution, idempotency, malformed-ledger fail-closed behavior, initial-delivery close gating, multi-finding repair cycles, progressive multi-lane reverification, legacy batch-run compatibility, aggregate convergence timing, and exact semantic-index exclusion. Setup/upgrade/package tests place byte sentinels in historical target waves and prove those paths install source/carriers without scanning or mutating wave history; subsequent public creation is external-ledger-only | `test_review_evidence.py`, `test_render_agent_surfaces.py`, `test_server_tools.py`, `test_indexer.py`, build-pack/setup/upgrade/render integration tests | Same runner |
| Context-efficiency telemetry (wave 1stwj) | Closed-ledger arithmetic for 18 retrieval and five lifecycle tools; exact structural-path census; phase/source/version and event uniqueness across real processes; general attribution; store-identity-loss freeze; accounting-gap poisoning; paired-evaluation quality gate/attachment; lifecycle/reload/upgrade projection; install/package/upgrade non-mutation | `test_context_efficiency.py`, `test_server_context_efficiency.py`, `test_server_tools.py`, render/setup/package/upgrade integration tests | Same runner |
| Memory supply and exploration-estimate integrity (waves 1stwm/1sxj7) | Real compact review-event repair chains, admitted-change Decision Logs, escaped pipes, implementation-only anchors, Unicode/evidence identity, concurrent add/propose idempotency, SQLite event replay and origin budgets, exact-match passive/explicit surfaces, current source-cost authority, lazy schema extension, and lifecycle/reload/upgrade projection | `test_memory_records.py`, `test_context_efficiency.py` | Same runner |
| Commit provenance integrity (waves 1sufq/1sxj7) | Canonical local commit identity, anchored landing grammar, explicit metadata authority, mixed blame coverage, conflict propagation, file-relevance labeling, exact public input union, and read-only/traversal controls | `test_commit_provenance.py`, `test_server_context_efficiency.py` | Same runner |
| Memory-retrieval eval (wave 1sufo) | Hermetic golden set over a synthetic memory corpus scoring the shipped `memory_search`/`brief` paths: recall@k / MRR plus explicit pass/fail on the five policy invariants (exact-target, paraphrase-does-not-demote-trust, no-index, decay, supersession), and a recorded baseline vs lexical-only/semantic-only that a future ranking/fusion change must beat. Measurement-only; builds its own corpus, never depends on the live one. See `docs/references/memory-retrieval-eval.md`. Sibling of the code/docs golden-query recall eval | `tests/eval/run_memory_eval.py` (runner + `memory_golden.json`), `test_memory_eval.py` | Same runner |
| Manual docs gate | MCP **`wf_validate_docs`** succeeds, **or** `wf docs-lint` passes | MCP / repo root | `wf_validate_docs` / `wf docs-lint` |
| Manual gardener | MCP **`wf_garden_docs`**, **or** `wf docs-gardener` | MCP / repo root | `wf_garden_docs` / `wf docs-gardener` |

### Semantic Embedding Regression Tier

These tests exercise the real `fastembed` embedding path — no mocks. They pin four properties as regression anchors so that a future model upgrade fails loudly rather than silently:

- **Model name** — `DOCS_MODEL == "BAAI/bge-small-en-v1.5"`
- **Dimension** — output vector length == 384
- **Determinism** — same text always produces the same vector
- **Ranking order** — a semantically close query ranks its best match above an unrelated chunk

When a model upgrade is intentional, update the two constants at the top of `SemanticEmbeddingRegressionTests` and follow the checklist in `docs/architecture/embedding-model.md`.

### Independent-Reference Review Evidence

Independent-reference verification is a review-evidence technique for any implementation change, not a new test tier or a replacement for independent approval. Within seed 209's finite probe budget, code review identifies a credible reference that does not share the implementation's assumptions and the exact promised property; QA names the assertion that would falsify each load-bearing correctness, complexity, compatibility, or parity claim. For deterministic mechanisms a fixed seed or durable fixture makes generative probes reproducible, invalid inputs are rejected before comparison, and incidental representation differences stay outside the assertion.

The worked pattern is a fallback parser compared with a grammar-backed parser over valid generated declarations, asserting only initializer ownership identity. Named fixtures retain diagnosed edge cases; the differential comparison diversifies the reference used to explore the valid surface. Because both parsers can still share a misunderstanding, specification-derived or metamorphic assertions cover plausible common-mode failures. Implementer-produced results remain `independent: false`; carrier and rendering tests prove distribution only.

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
- Fresh setup and full upgrade fixtures begin without any of the five lifecycle
  prompts, exercise the public renderer, and prove packaged missing-only
  templates materialize all five while leaving historical wave/event bytes and
  existing project prompt prose unchanged.
- Direct SQL checks assert that query text, responses, prompts, source paths,
  secrets, and conversations are absent.
- Fresh setup, packaged install, public render, and full upgrade fixtures deliver
  the implementation, five prompt baselines, and managed `.wavefoundry/logs/`
  ignore without eager sidecar creation. Historical `wave.md` and `events.jsonl`
  byte sentinels remain unchanged until a later mutating lifecycle boundary.

Performance claims use repeated, warm, paired samples against an uninstrumented
control, never one-shot wall-clock assertions. Contention, source-count, and
projection samples report distributions; correctness does not depend on a
machine-specific one-shot timing threshold.

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
