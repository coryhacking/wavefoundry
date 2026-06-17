# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-17

wave-id: `1p65k codebase-map-round3`
Title: Codebase Map Round3

## Objective

Round-3 codebase-map polish from teton field feedback on `1.7.0+p65a` (rounds 1–2 confirmed landed). `1p65l` (generator, deterministic): strip vendored/generated files from area key-files (#1), name config areas from their config files not doc prose (#3-name), qualify opaque structural/version leaf names + coalesce sibling versions (#5), collapse same-package type-only communities (#4). `1p65m` (clustering, `CLUSTER_BUILDER_VERSION`): make clustering REPRODUCIBLE (#4 — identical input → identical communities/labels/count; the headline item, root of the intermittent #3 config label + typings-count variance, likely a label-propagation fallback) AND split cross-directory grab-bag communities joined only by weak/util edges (#2 — the source of the leak `1p65l #1` mitigates downstream). When this wave closes, the map's areas are cohesive, reproducible across rebuilds, and their key-files/hubs/names carry real signal.

## Changes

Change ID: `1p65l-enh map-generator-polish-round3`
Change Status: `implemented`

Change ID: `1p65m-enh graph-clustering-cohesion`
Change Status: `implemented`

Change ID: `1p661-enh per-area-agents-authoring`
Change Status: `implemented`

Change ID: `1p662-enh per-area-agents-mcp-resource`
Change Status: `implemented`

Completed At: 2026-06-17

## Wave Summary

Wave `1p65k codebase-map-round3` (Codebase Map Round3) delivered 4 changes: Codebase map generator polish (round 3): vendored key-files, config/structural names, typings collapse, Graph clustering cohesion: split cross-directory grab-bag communities, Per-area AGENTS.md: author content for major areas (the codebase-map ROI lever), and Per-area AGENTS.md MCP resource (convenience read layer over the files). Notable adjustments during implementation: Graph clustering cohesion: split cross-directory grab-bag communities: Implemented: (det) seed igraph's global RNG (`igraph.set_random_number_generator(random.Random(0))`) before partitioning so the unseeded fallback is also reproducible; kept `seed=0`. (cohesion) `_split_cross_directory_grabbags` — conservative (≥`GRABBAG_MIN_DIRS`=4 distinct module-dirs, none ≥`GRABBAG_DOMINANT_SHARE`=0.5) anti-over-split per-module-dir split, deterministic. `CLUSTER_BUILDER_VERSION` 9→10. 4 new tests (grab-bag splits, cohesive doesn't, fixed-graph reproducible, version); full suite 3281 green. **Residual:** if teton STILL sees identical-input churn after upgrading, the cause is upstream INPUT-GRAPH determinism (incremental reindex producing different graphs) — out of `graph_cluster`'s scope; a separate graph-build-determinism follow-up. The grab-bag split thresholds are conservative and teton-validation may tune them.

**Changes delivered:**

- **Codebase map generator polish (round 3): vendored key-files, config/structural names, typings collapse** (`1p65l-enh map-generator-polish-round3`) — 4 ACs completed. Key decisions: --------; Bundle the four generator-local fixes into one change; clustering cohesion (#2) is a separate change (`1p65m`).
- **Graph clustering cohesion: split cross-directory grab-bag communities** (`1p65m-enh graph-clustering-cohesion`) — 3 ACs completed. Key decisions: --------; Investigation-first before tuning; separate change from the generator polish.
- **Per-area AGENTS.md: author content for major areas (the codebase-map ROI lever)** (`1p661-enh per-area-agents-authoring`) — 3 ACs completed. Key decisions: --------; Reverse `1p5xc`'s "framework never auto-authors per-area AGENTS.md" — agent drafts grounded content for MAJOR areas during inventory; humans refine.
- **Per-area AGENTS.md MCP resource (convenience read layer over the files)** (`1p662-enh per-area-agents-mcp-resource`) — 3 ACs completed. Key decisions: --------; Resource COMPLEMENTS the on-disk file (reads it); does not replace it or synthesize content.
## Journal Watchpoints

- Sequencing: implement `1p65l` first (deterministic generator wins, independently shippable, includes the highest-leverage #1 key-files filter), then `1p65m` (fuzzier clustering cohesion that needs an investigation phase before tuning).
- `1p65l` is generator-only (no version bump); `1p65m` bumps `CLUSTER_BUILDER_VERSION` (community shape change). Both require `framework_edit_allowed`.
- Faithfulness gates before close: `1p65l` must never exclude a real product file from key-files (explicit-signal/tag detection only); `1p65m` must not over-split a cohesive module (anti-over-split fixture) and must preserve `seed=0` determinism.
- Follow-up: validate against the teton TS consumer as the real-world oracle (vendored key-file leak gone; `spinner-animation` grab-bag resolves; `v1`/`v2` qualified) + the multilang pack; teton should regenerate its map (the round-3 report was partly against a stale, pre-`1p64u` map).
- Blocking: only one wave may be OPEN at a time — `1p61u` closed 2026-06-17 so the slot is free; ready/open `1p65k` via prepare → implement.
- Scope (operator-directed, post-prepare): `1p661` (per-area `AGENTS.md` authoring — seed-030/050/160, reverses `1p5xc`'s "never auto-author" to agent-drafts-grounded-for-major-areas/human-refines) + `1p662` (per-area `AGENTS.md` MCP resource, a read layer over the files) admitted 2026-06-17 after the downstream ROI verdict (map is cold-start orientation for MCP agents; the lever is human-authored per-area context, empty today — memory `project-codebase-map-roi`). Broadens the wave from map-generator polish to per-area context population. Prepare-council covered `1p65l`/`1p65m`; the delivery-council must cover all four. `1p661` is seed-prose/policy (`seed_edit_allowed`); `1p662` is `server_impl` + docs (`framework_edit_allowed`). The file stays source-of-truth + indexed; the resource complements, never replaces.

## Review Evidence

- wave-council-readiness: approved (READY) — prepare-council passed 2026-06-17 (seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer) over `1p65l` (generator polish, no version bump) + `1p65m` (clustering cohesion + determinism, `CLUSTER_BUILDER_VERSION`). `1p65l` assumptions verified (key_files/key_symbols/hub have no vendored filter — confirmed in code). `1p65m`'s primary goal (determinism, round-3 #4) rests on an unconfirmed root cause — must distinguish same-graph→different-clusters (clustering nondeterminism: label-prop fallback / seed) from input-graph churn (upstream graph build) on a byte-fixed graph before tuning. Strongest-alternative (generator canonical re-sort instead of fixing clustering) rejected — community membership varies (221 vs 100 areas), not just ordering. Faithfulness gates: `1p65l` explicit-signal-only (never excludes product) + graceful fallback when an area is fully vendored/generated; `1p65m` anti-over-split + determinism preservation. Conditions carried into implement (non-blocking): (1) `1p65m` investigation distinguishes clustering-nondeterminism vs input-graph churn on a fixed graph — if the latter, extend to graph-build determinism; (2) confirm the label-prop-fallback hypothesis for the 100 outlier, make the fallback deterministic/surfaced; (3) `1p65l` key_files/hub fall back gracefully for all-vendored areas; (4) `1p65m`'s determinism test uses a fixed input graph (clustering the same graph twice → identical). Sequencing `1p65l` → `1p65m`; `1p65l` independently shippable.
- wave-council-delivery: approved (PASS) — delivery-council 2026-06-17 over all 4 changes (seats: reality-checker, red-team, qa-reviewer, security-reviewer, architecture-reviewer, docs-contract-reviewer). #1/#3/#5/#4-typings teton-validated on p65w; #2 generator cohesion + `1p661` authoring + `1p662` resource tested here, await teton confirm. Faithfulness gates pass: `1p65l` never excludes product (explicit signals + fallback); `1p65m` anti-over-split + determinism-given-fixed-graph verified + split is no-op-worst-case; `1p662` reads the on-disk file, never synthesizes, fail-safe; `1p661` never overwrites. Substantive finding (flagged, NOT fixed — deliberate per the map-ROI feedback): `1p65m`'s pre-merge grab-bag split is best-effort (small fragments may be re-merged by `_merge_small`); it is upside-or-neutral, and the load-bearing #2 fix is the deterministic generator-side cohesion filter in `1p65l`. Watchpoint: review teton's first agent-authored per-area `AGENTS.md` for boilerplate padding (`1p661` guardrails are prose). #4 real-world determinism churn honestly DEFERRED (environment-specific, not reproducible here; instrument-first when taken up). Full suite 3284 green; docs-lint clean; only `1p65m` bumps `CLUSTER_BUILDER_VERSION` (9→10).
- operator-signoff: approved — operator directed close of 1p65k on 2026-06-17 (delivery-council PASS): round-3 generator polish (#1/#3/#5/#4-typings teton-validated, #2 cohesion filter), clustering reproducibility + best-effort split, and the per-area `AGENTS.md` authoring instructions + `wavefoundry://area/` resource. #4 real-world determinism churn deferred to a future instrument-first change; teton to validate `p664` downstream.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-17: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer; rotating-seat: security-reviewer; strongest-challenge: `1p65m`'s determinism root cause is unconfirmed — must distinguish same-graph→different-clusters (label-prop fallback / seed) from input-graph churn (upstream graph build) on a byte-fixed graph before tuning, else the fix is in the wrong layer; strongest-alternative: generator canonical re-sort instead of fixing clustering — rejected because community membership varies (221 vs 100 areas), not just ordering; conditions carried into implement (non-blocking): (1) `1p65m` investigation distinguishes clustering-nondeterminism vs input-graph churn on a fixed graph (extend to graph-build determinism if the latter); (2) confirm label-prop-fallback = the 100 outlier + make the fallback deterministic/surfaced; (3) `1p65l` key_files/hub graceful fallback for all-vendored areas; (4) `1p65m` determinism test on a fixed input graph; sequencing `1p65l` → `1p65m`, `1p65l` independently shippable; faithfulness: `1p65l` explicit-signal-only never excludes product, `1p65m` anti-over-split + determinism preservation)

- **Delivery-phase Wave Council [delivery-council] — 2026-06-17: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, security-reviewer, architecture-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; scope: all 4 changes incl. the operator-directed `1p661`/`1p662` per-area-context additions; substantive-finding: `1p65m` pre-merge grab-bag split is best-effort (may be re-merged by `_merge_small`; upside-or-neutral) — the load-bearing #2 fix is `1p65l`'s generator-side cohesion filter; flagged-not-fixed deliberately per the map-ROI feedback, teton validates; watchpoint: teton's first agent-authored `AGENTS.md` for boilerplate; #4 real-world churn deferred (environment-specific, instrument-first); faithfulness verified: never-excludes-product / never-synthesizes / never-overwrites / anti-over-split; full suite 3284 green, docs-lint clean)

## Dependencies

- No external wave dependencies.
