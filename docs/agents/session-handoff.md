# Session Handoff

Owner: Engineering
Status: in_progress
Last verified: 2026-06-23

## Active wave: `1p7de graph-edge-trust` (OPEN) — IMPLEMENTED + downstream-validated; UNCOMMITTED per operator "commit when everything is done"
- **`1p7df`** transitive confidence — COMMITTED (c76721f).
- **`1p7dg`** confidence promotion — 3 surfaces; per-language lift cleared on Python (90.4%→31.9%), Java javaagent (26.9%→20.6%), Swift solaris (52.7%→33.4%); faithfulness real-data-confirmed. (Python same-file committed d6c786e; rest uncommitted.)
- **`1p7dh`** string-literal binding — `reads_config` (Python/JSON + Java/Spring file config via tree-sitter-yaml + @Value/getProperty) + AOP `instruments` (24 classes/36 targets, zero noise). v35 downstream re-validated stable.
- **GRAPH_BUILDER_VERSION 32→35.** Full suite **3427 OK** bytecode-free; gates closed; docs-lint clean.

## Upgrade flow improved (operator-directed, this session)
The upgrade's final index phase now updates BOTH semantic AND **graph** indexes, version-aware (incremental, or auto-escalates to a rebuild on a builder bump) — `phase_index_update` runs `setup_index.py --graph-only`, `phase_index_rebuild` runs `--graph-only --full`. Symmetric with semantic; a `GRAPH_BUILDER_VERSION` bump now materializes DURING the upgrade (not lazy-first-query, which remains a safety net). 2 tests; docs updated to the symmetric framing (seed 160 + `upgrade-wavefoundry.prompt.md` + `CHANGELOG [1.8.1]`; stale "moving to 1.6.0 bumps both" examples replaced). NOTE: takes effect for upgrades run BY a pack that contains it (p7jg+) — the old-code-window caveat.

## Local build (v35): `~/.wavefoundry/dist/wavefoundry-1.8.1.p7jg.zip` (VERSION+manifest 1.8.1+p7jg). Carries the v35 extractor + improved upgrade flow. Supersedes earlier p7j* zips (removed).

## Uncommitted (commit when everything done): 1p7dg cross-file + same-file widening; 1p7dh config (Python+Java) + AOP instruments + namedOneOf; upgrade-flow graph step (upgrade_wavefoundry.py + 2 tests); GRAPH_BUILDER_VERSION 35 + version-pin test; VERSION + manifest (1.8.1+p7jg); upgrade-path docs (seed 160 + prompt + CHANGELOG [1.8.1]); change-doc/wave/handoff updates; experiments/ scripts.
## Committed this session (on main): 1688bbc standardization · c76721f 1p7df + reranker fix · d6c786e 1p7dg reframe + Python same-file + AC-1 spike.

## Drafted parallel (planned, not activated): `1p7ir index-build-robustness` (1.8.0 OOM+TLS, 4 changes).
## Done earlier: 1.8.0 RELEASED. ## Planned, not started: `1p6lp cross-host-skills`.
## Memory this session: project_field_feedback_1p8_oom_tls, project_literal_edge_target_locality.

## Current Session

**Active wave:** *(none)*
