# Testing Architecture

Owner: Engineering
Status: active
Last verified: 2026-07-15

## Test Tiers

| Tier | Scope | Location | Runner |
|------|-------|----------|--------|
| Framework script unit tests | `docs_lint.py`, `build_pack.py` behavior | `.wavefoundry/framework/scripts/tests/` | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| Dashboard reader/server unit tests | `dashboard_lib.py`, `dashboard_server.py` snapshot and HTTP-handler contract | `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| Fixture-based integration | Docs-lint against fixture repos | `.wavefoundry/framework/scripts/tests/fixtures/` | Same runner |
| Semantic embedding regression | Real fastembed path, model name/dim/determinism/ranking anchors — **skipped** when fastembed is not installed or model not cached | `SemanticEmbeddingRegressionTests` in `test_server_tools.py` | Same runner |
| Differential equivalence harnesses (wave 1rsh9) | Optimized path vs authoritative path over identical inputs — the registry-backed incremental skip vs the Lance-read delta plan (`RegistryDifferentialTests`), and the secret-scan cache path vs a no-cache full scan through a six-mutation git fixture matrix with the REAL scanner (`DifferentialEquivalenceTests`). Any divergence fails; these are the adoption gates for skip-class optimizations | `test_fts_lexical_layer.py`, `test_secret_scan_cache.py` | Same runner |
| Build-epoch fault injection (wave 1sed7) | The SQLite-only state contract: epoch state-machine/CAS unit tests (`BuildEpochTests`), structured no-fallback failure injection at every mandatory boundary + a fresh-process kill between fence and finalize (`EpochOrderingAndFaultTests`), legacy meta.json convergence-by-reconstruction (`LegacyConvergenceTests`), and the reader seqlock at the MCP tool boundary — mid-search epoch mutation discards results (`EpochSeqlockConcurrencyTests`) | `test_index_state_store.py`, `test_indexer.py`, `test_server_tools.py` | Same runner |
| Review-protocol propagation and state (waves 1skt1/1slep) | Typed carrier-registry census plus public-path integration through fresh setup, packaged install, real full-upgrade extraction, direct `wf render-surfaces`, and self-host reconciliation. Fixtures pin compact authoring, direct canonical `events.jsonl` parsing, required judgment refusal, lane-scoped approval chronology, generated-Markdown non-authority, empty-run provenance, serialized append/replay/fault recovery, bounded prefix proof, public MCP registration/schema, missing-carrier creation, Guru-absent execution, idempotency, malformed-ledger fail-closed behavior, initial-delivery close gating, and exact semantic-index exclusion. Setup/upgrade/package tests place byte sentinels in historical target waves and prove those paths install source/carriers without scanning or mutating wave history; subsequent public creation is external-ledger-only | `test_review_evidence.py`, `test_render_agent_surfaces.py`, `test_server_tools.py`, `test_indexer.py`, build-pack/setup/upgrade/render integration tests | Same runner |
| Manual docs gate | MCP **`wave_validate`** succeeds, **or** `wf docs-lint` passes | MCP / repo root | `wave_validate` / `wf docs-lint` |
| Manual gardener | MCP **`wave_garden`**, **or** `wf docs-gardener` | MCP / repo root | `wave_garden` / `wf docs-gardener` |

### Semantic Embedding Regression Tier

These tests exercise the real `fastembed` embedding path — no mocks. They pin four properties as regression anchors so that a future model upgrade fails loudly rather than silently:

- **Model name** — `DOCS_MODEL == "BAAI/bge-small-en-v1.5"`
- **Dimension** — output vector length == 384
- **Determinism** — same text always produces the same vector
- **Ranking order** — a semantically close query ranks its best match above an unrelated chunk

When a model upgrade is intentional, update the two constants at the top of `SemanticEmbeddingRegressionTests` and follow the checklist in `docs/architecture/embedding-model.md`.

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
2. Docs gate: **agents** — MCP **`wave_validate`** succeeds (use **`wave_garden`** first when metadata needs refresh); **CI / no MCP** — `wf docs-lint` passes on the Wavefoundry repo itself

## Framework Script Hygiene

Run tests without writing bytecode: `python3 -B .wavefoundry/framework/scripts/run_tests.py`. If caches were written, clean them:

```bash
find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
```

## Minimum Verification Bar for Cross-Module Changes

Any change touching `.wavefoundry/framework/scripts/wave_lint_lib/` or `docs_lint.py`:
- All existing fixture tests must pass
- Docs gate: **`wave_validate`** (MCP) or **`wf docs-lint`** (CLI) on the Wavefoundry repo

Any change to `docs/prompts/prompt-surface-manifest.json` or `.wavefoundry/framework/VERSION`:
- **`wave_validate`** or **`wf docs-lint`** must pass (manifest `framework_revision` validation)
