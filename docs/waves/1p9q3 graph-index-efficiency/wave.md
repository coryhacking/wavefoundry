# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-03

wave-id: `1p9q3 graph-index-efficiency`
Title: Graph Index Efficiency

## Objective

Cut the graph index's storage, per-build write volume, and per-query latency by roughly an order of magnitude, and make per-edit build cost proportional to the change instead of the repository. When this wave closes, graph artifacts are compact and compressed, the MCP server caches the constructed graph between tool calls, betweenness centrality works on graphs past 10k nodes (the self-hosted repo already exceeds the current cap), and incremental builds do O(delta) merge work with a provably full-rebuild-equivalent result.

## Changes

Change ID: `1p9py-enh graph-compact-compressed-persistence`
Change Status: `planned`

Change ID: `1p9pz-enh graph-query-payload-cache`
Change Status: `planned`

Change ID: `1p9q1-enh graph-buildtime-betweenness`
Change Status: `planned`

Change ID: `1p9q2-enh graph-incremental-merge-state-store`
Change Status: `planned`

## Wave Summary

Tier 1 + Tier 2 of the graph-index efficiency evaluation (2026-07-03): `1p9py` compact/gzip artifact persistence, `1p9pz` server-process query cache, `1p9q1` build-time betweenness with size tiers, `1p9q2` incremental merge with symbol-scoped invalidation plus a per-file state store. Grounded in measurements on the self-hosted index (34 MB artifacts, 21.8× gzip ratio, full re-merge and full JSON parse per build/query).

## Journal Watchpoints

- Sequencing: land `1p9py` (I/O helpers) before `1p9q2` (state store writes through them); `1p9pz`'s cache must stay format-agnostic (keys on file stats, not content).
- Coordinate a single final `GRAPH_BUILDER_VERSION` bump across `1p9py`/`1p9q1`/`1p9q2` at integration; `1p9q1` may also bump `cluster_builder_version`.
- `1p9q2` requires an adversarial faithfulness review lane at wave review (security-control-faithfulness rule for resolution/binding changes) — differential-green alone is not sufficient.
- Follow-up watchpoint: `1p9pz` includes the AGENTS.md graph-layer/networkx docs correction rider — if the paragraph is seed-rendered, the `seed_edit_allowed` gate applies; verify ownership before editing.
- Blocking: `finalize()` analysis-pass seam is shared between `1p9q1` and `1p9q2` — settle the fingerprint-gated-skip interface before both lanes touch it.

## Participants

- code-reviewer — all four changes touch `.wavefoundry/framework/scripts/*.py`
- qa-reviewer — all change docs carry AC priority tables
- architecture-reviewer — MCP tool response shape changes (`wave_graph_report` betweenness section) and indexing module seams
- performance-reviewer — chunker/indexer hot paths (artifact I/O, per-query cache, build-time analysis pass, incremental merge)
- docs-contract-reviewer — rotating council seat (the `1p9pz` AGENTS.md/seed docs-accuracy rider)
- red-team, reality-checker — council seats (prepare phase); adversarial faithfulness lane re-runs at implementation review for `1p9q2`

## Review Checkpoints

- Prepare wave — readiness verdict (2026-07-03): READY. Council ran at standard primer depth. Red-team's strongest challenge — in-place artifact writes (`_write_json` uses direct `write_text`) combined with `1p9pz`'s stat-keyed cache could pin a torn cross-process read — was accepted and resolved by amendment: `1p9py` gained Requirement 8 + AC-8 (atomic temp + `os.replace` writes) and `1p9pz` Requirement 2 now names that as a precondition. Architecture seat's ambiguity finding (what "persistent merged maps" means under spawn-per-build processes) resolved by amendment to `1p9q2` Requirement 1: the payload artifact is the persistent map, plus an incrementally-maintained name-to-candidates lookup. Strongest alternative (skip gzipping the monolithic state file in `1p9py` since `1p9q2` replaces it) recorded and declined — the helpers are generic and the application is trivial, and `1p9py` must stand alone if `1p9q2` slips. Remaining seats found the AC set testable and the sequencing sound; performance seat confirmed gzip cost is noise against build wall time and flagged the exact-tier betweenness threshold as measurement-owned (already in `1p9q1` Requirement 2). AC priorities recorded on all four change docs. Product-owner acknowledgment: not applicable (framework-internal efficiency work; no product behavior shift).
- Docs-contract seat (rotating): the `1p9pz` AGENTS.md graph-layer/networkx correction must flow through the owning seed if the paragraph is seed-rendered (`seed_edit_allowed` gate) — already required by `1p9pz` Requirement 7 and AC-7; the capability-wording updates in `docs/specs/mcp-tool-surface.md` are audit-and-update per the "audit means audit" rule. No contract regressions found in the planned tool response changes (`wave_graph_report` gains method metadata; no field removals).
- **Prepare-phase Wave Council [prepare-council] — 2026-07-03: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: stat-keyed query cache over non-atomic in-place artifact writes can pin a torn cross-process read — resolved by amendment, 1p9py Requirement 8/AC-8 atomic temp-plus-replace writes with 1p9pz naming it a precondition; strongest-alternative: defer monolithic-state gzip to 1p9q2's store rework — declined, helpers are generic and 1p9py must stand alone if 1p9q2 slips)

## Review Evidence

- wave-council-readiness: approved 2026-07-03 — prepare council synthesis verdict READY after amendments (1p9py atomic writes, 1p9pz cache precondition, 1p9q2 persistence-model clarification); no unresolved blocking findings
- operator-signoff: pending operator confirmation at closure

## Dependencies

- No external wave dependencies.
