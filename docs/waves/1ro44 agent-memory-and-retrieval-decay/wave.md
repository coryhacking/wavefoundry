# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-04

wave-id: `1ro44 agent-memory-and-retrieval-decay`
Title: Agent Memory And Retrieval Decay

## Objective

Ship the Wave Memory layer (typed, evidence-backed, graph-attached memory records surfaced at action time) on top of the graph platform landed in waves 1p9q3/1p9qh, together with churn-aware temporal decay for retrieval: index-time freshness/churn metadata, doc-code drift detection, and kind-aware memory-confidence decay. When this wave closes, agents receive prior-learning advisories before risky actions and can distinguish current documentation from drifted documentation in every retrieval response.

## Changes

Change ID: `1p8gy-enh graph-backed-agent-memory`
Change Status: `planned`

Change ID: `1ro43-enh churn-aware-retrieval-decay`
Change Status: `planned`

## Wave Summary

Two complementary changes: `1p8gy` adds the memory record schema, `wave_memory_*` MCP tools, graph-node attachment through the incremental-merge path, and lifecycle capture at pause/review/close; `1ro43` adds temporal metadata (git churn, doc-code drift anchored to content changes/verification stamps, wave-attributed historical decay for `docs/waves/` records) to the semantic index with annotation-first surfacing and an evidence-gated drift partition. `1ro43`'s per-path freshness primitive is the seam `1p8gy` consumes for kind-aware memory decay. Follow-on plans staged for a future wave: `1rolq-enh verify-docs-agentic-review` (agentic disposal loop) and `1rppn-enh wave-change-manifests-close-advisory` (deterministic close-time manifests + close advisories).

## Journal Watchpoints

- Watchpoint (cross-change seam): the `1ro43` freshness primitive signature blocks `1p8gy` kind-aware decay (AC-13) — sequence the `1ro43` churn-metadata workstream first or pin the interface early.
- Watchpoint (graph write path): graph writes from memory records must reuse the 1p9q3 incremental-merge SQLite store and invalidate the graph query cache correctly; a parallel write path is a defect. `GRAPH_BUILDER_VERSION` bump required with the new node/edge shapes.
- Watchpoint (ranking safety): the drift partition never reorders on raw age, is evidence-gated behind the census (`1ro43` AC-8), and ships with a kill switch; flipping the demotion default is blocked until census findings are recorded.
- Watchpoint (content safety): memory forbidden-content lint (no secrets/transcripts/personal facts) lands with the schema, not deferred until after the first records exist.
- Watchpoint (historical class boundary): `docs/waves/` chunks are annotation-only (landing-commit anchor, waves-behind) — never drift-flagged, never worklisted, never routed to verify/amend; any ranking treatment for the class is deferred pending census evidence.
- Watchpoint (verification semantics): gardener `Last verified` stamps are mechanical file-touch records and never count as verification events; drift anchors only to doc content changes or commit-SHA verification stamps, and `docs_gardener` is blocked from touching those stamps. The stamp-writing agentic review loop is deferred to `1rolq-enh verify-docs-agentic-review` (docs/plans, future wave after this one lands); this wave must leave the worklist/stamp contracts documented and stable for it.

## Participants

- code-reviewer — framework-script changes across `server_impl.py`, `indexer.py`, `graph_indexer.py`, `docs_lint.py`
- qa-reviewer — AC priority tables present on both changes; census/evidence gates verified
- architecture-reviewer — new MCP tool contracts (`wave_memory_*`), graph schema extension, index/retrieval boundary changes
- docs-contract-reviewer — lifecycle seed/prompt updates (pause/review/close/Guru), worklist/stamp consumer contracts
- performance-reviewer — churn extraction in the build path, advisory surfacing on hot read tools, graph-cache interplay
- security-reviewer — memory forbidden-content rules and lint, evidence-ref scoping

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: kind-aware decay was directionally wrong for `fragile_file` — churn on a fragile file is ambiguous evidence, meaning refactored-away or actively unstable, so silent confidence attenuation would hide the warning exactly when the file is being churned — resolved by amendment to 1p8gy Req 13: churn sets a needs-reverification flag, never drops the advisory below briefing inclusion, and only reconciliation retires the record; strongest-alternative: split 1p8gy into a schema+tools wave followed by a surfacing wave — rejected because the action-time surfacing is the value thesis of the change and the schema alone ships nothing an agent experiences, while the real coupling risk, the 1ro43 freshness-primitive seam, is already serialized inside the wave)
- Council seat notes: red-team also pressed advisory latency/response bloat on hot read tools (resolved by amendment to 1p8gy Req 6: named caps, warm graph-cache path, graceful absence) and the cross-wave storage seam with 1rsh9 (accepted as recorded: either landing order works, one store file, seam mirrored in both wave records). architecture-reviewer: single write path through the 1p9q3 incremental-merge store is correct, require graceful absence at every surfacing point — folded into the Req 6 amendment. security-reviewer: forbidden-content lint must land with the schema (already a wave watchpoint); memory records are repo-visible and reviewable, local-git-only churn — pass. qa-reviewer: require synthetic git fixtures rather than live-repo assumptions for churn/derivation tests, and per-kind fixtures for all eight memory kinds — accepted as implementation-test guidance. reality-checker: gardener mechanical stamping, status-only close drift, landing-commit convention (including the five-wave bundle commit), and chunk_hash reuse all verified against source this session; the "wave docs are the bulk of the docs index" claim is directional, not measured — accepted as directional. docs-contract-reviewer (rotating): the close-time distillation checkpoint in 1p8gy Req 7 is a deliberate new close-step and must stay cheap (propose candidates, quick promote/reject/defer decisions) — accepted with the burden note recorded; 1ro43 Req 11 consumer contracts must be published on the drift-summary surface, not only in the change doc. seat_agreement: unanimous; no challenge round required; amendments applied in-session before readiness was recorded.
- AC priority: confirmed at prepare for both changes as proposed in each doc (1p8gy AC-1..10 required, AC-11 required, AC-12/13 important; 1ro43 AC-1..6, 8..11, 13, 14 required, AC-7/12 important). Product-owner acknowledgment: wave scope and both changes were operator-directed in-session during planning on 2026-07-04.

## Review Evidence

- wave-council-readiness: approved 2026-07-04 — prepare council synthesis verdict READY after amendments (fragile_file needs-reverification semantics; advisory caps and graceful absence); seats unanimous; full synthesis in Review Checkpoints
- operator-signoff: pending operator confirmation at closure

## Dependencies

- No external wave dependencies.
