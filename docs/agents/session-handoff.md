# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-07-04

## Current State (2026-07-04 — 1roqn CLOSED + committed; no wave open)

**Wave `1roqn lance-drift-eligibility` CLOSED 2026-07-04 (operator-approved: "close and commit")** — delivery review PASS unanimous, all ACs met. No wave currently open; readied waves `1p9q8`/`1p9qh`/`1p9qi` await `Implement wave`.

The drift fix is live-proven: the previously permanent loop (`repairing 1 drifted file(s)` + ~1 s merge + ~1.35 MB per hook fire) now takes `merge[zero-change]` with 0 bytes; suite 4,358 OK (12 new tests); eligibility gated per-build on `files_for_content` with the graph-mode write-capability skip; reaper firewall intact. Key close-time watchpoint: `docs/workflow-config.json` is a LIVE per-kind-residual instance shielded only by 20 all-mode-setup rows in code.lance — any code-layer table recreation re-triggers the loop via the residual (named trigger + follow-up instrument recorded in wave.md watchpoints).

Suggested commit subject: `Land wave 1roqn: gate lance drift detection on chunk eligibility`.

Earlier this session: **`1p9q3 graph-index-efficiency` CLOSED + committed (`38c52ccd`)**; `1roqn` planning committed (`5f214be5`).

### Delivered (headline numbers, all independently reproduced by the performance lane)

- `1p9py`: compact/gzip/atomic graph artifacts — 17.5× at its own boundary, **8.6× wave end-state** (payload 0.56 + SQLite store 3.5 + clusters 0.11 MB vs 36.0 MB); `GRAPH_BUILDER_VERSION` 36.
- `1p9pz`: stat-validated in-process query cache — warm graph-tool calls 42.8 ms → 0.04 ms (~1,000×); 17 sites migrated; docs rider fixed stale layer/union/networkx claims.
- `1p9q1`: build-time tiered betweenness — 10k query cap retired; exact tier 14-62 ms at 11k nodes; `CLUSTER_BUILDER_VERSION` 11.
- `1p9q2`: incremental merge + symbol-scoped invalidation + SQLite state store — zero-change builds 0 bytes/0.3 s; rows + re-resolution O(delta); bytes O(graph) via the merge_state sidecar (honestly re-scoped + instrumented).

### Review outcome (2026-07-03/04)

Five delivery lanes (code, qa, architecture, performance, **adversarial faithfulness**) + red-team primer + four fixed council seats + rotating docs-contract seat. **Synthesis PASS, seats unanimous.** The adversarial lane found a REAL equivalence bug (merged-epoch symbol-delta collapse → `reads` edges in untouched files escaping re-resolution; missing + dangling edges) — **fixed in-session** (per-side delta + `DepthSwapDeltaKeyTests`; reproducer green; AC-9 discharged faithful-with-residuals). Also fixed in-session: blob-aware sidecar counters + `sidecar:` log segment; two un-invalidated cache-refresh paths; never-pin-stale-builder cache guard (+ once-per-process stderr note); WAL pragma result check; reader-copy parity gate; dead-code removal; honest claims re-scope; stale seed-211/guru.md cap wording; architecture-doc updates.

Gates: full suite **4,346 tests / 42 files OK** post-fix; docs-lint clean; `wave_review` green (`wave-council-delivery` recorded); `wave_close` dry-run clean; both edit gates closed; no `__pycache__`.

### Approved sequence in flight (operator: "close 1p9q3 and continue", 2026-07-04)

Close DONE → commit → open `1roqn` → implement `1rmaf-bug` → review → operator close decision for `1roqn`.

### Follow-up candidates recorded in wave watchpoints (not admitted)

- ~~URGENT: Lance drift-repair loop~~ — now planned + council-READIED as wave `1roqn lance-drift-eligibility` (`1rmaf-bug`); implementation next in this session.
- Full-merge kill-switch env for the incremental machinery (rotating-seat rider; cheap field insurance).
- Row-sharded fragment store — gated on real large-corpus measurement.
- Doc-impact add-direction miss (proven pre-existing); seed-gardening pass for pre-existing internal wave refs in seeds 211/214.
- **At ship time**: release notes must carry the "reconnect / `wave_mcp_reload` after upgrading" callout (stale sessions can't read gzip artifacts).

## Other Session Work

Wave `1p9qm subagent-mcp-retrieval-posture` closed + committed earlier (`6fb035da`); planning waves committed (`5f5e5db8`). Readied waves awaiting their turn after `1p9q3` closes: `1p9q8 graph-index-accuracy`, `1p9qh java-csharp-enterprise-accuracy`, `1p9qi sql-graph-accuracy` (suggested order: 1p9qh → 1p9qi; 1p9q8 anywhere). Pre-existing planned: `1p9pe post-release-followup-hardening`, `1p6lp cross-host-skills`. From 1p9qm: registry-derived wrapper-allowlist pin + docs-lint factor-wrapper `tools:` check remain follow-up candidates.

**⚠ Standing until `1p9p7 renderer-overwrite-safety` (wave `1p9pe`) lands:** every `render_agent_surfaces` run rewrites `.codex/config.toml` and deletes the operator's `wave_close approval_mode` block — restore after ANY re-render.

## Coordination Watchpoints

- `docs/specs/mcp-tool-surface.md`: waves `1p9qh`/`1p9qi` also want vocabulary edits — one integration owner.
- Solaris reporter re-runs their transcript count after upgrading (1p9qm field verification).
- MCP server old-code window: the running server executes pre-edit graph modules until reconnect/`wave_mcp_reload` — measurements via fresh venv subprocesses, not `wave_index_build`.
- Operator decision recorded 2026-07-04: keep SQLite for the state store; do NOT move the graph payload into SQLite (assessed and declined — it would break the stat-validated cache design for no measured benefit; revisit only with large-repo parse-dominance evidence).

## Current Session

**Active wave:** *(none)*
