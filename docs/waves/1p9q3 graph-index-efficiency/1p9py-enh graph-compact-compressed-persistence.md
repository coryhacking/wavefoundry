# Graph index: compact, gzip-compressed persistence for graph artifacts

Change ID: `1p9py-enh graph-compact-compressed-persistence`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

All three graph artifacts are written as pretty-printed JSON — `_write_json` (`graph_indexer.py:973-975`) uses `json.dumps(payload, indent=2, sort_keys=True)` with no compression. On the self-hosted repo (453 files, 10,776 nodes, 30,899 edges) that is 34 MB on disk: `project-graph.json` 11.7 MB, `project-graph-state.json` 22.6 MB, `project-graph-clusters.json` 1.1 MB. Measured `gzip -9` on the payload compresses **21.8×** (11.7 MB → 0.51 MB) — the bytes are dominated by indentation whitespace and repeated JSON keys/relation strings, not information.

This matters twice per edit, not once: the post-edit hook triggers a graph refresh on every reindex (`_build_graph_artifacts` runs unconditionally from `_build_index_locked`, `indexer.py:2756-2828`), and `finalize()` rewrites **all** artifacts in full on every build (`graph_indexer.py:7404-7541`). So every edit-triggered build currently rewrites ~34 MB of pretty-printed JSON. On a large target repo (5k files, ~100k+ nodes) linear extrapolation puts that at hundreds of MB per hook fire. Compact + compressed persistence cuts disk footprint and per-build write volume by roughly an order of magnitude with no change to graph content, and it is the prerequisite baseline for the Tier-2 incremental-merge work (`1p9q2-enh graph-incremental-merge-state-store`).

Cold-load cost today is ~30 ms / ~47 MB resident for the 11.7 MB payload; gzip decode adds negligible CPU at these sizes and shrinks I/O, so read-side latency stays flat or improves.

## Requirements

1. **Compact JSON encoding.** All graph artifact writers drop `indent=2` and use compact separators (`(",", ":")`), retaining `sort_keys=True` (the `input_fingerprint` determinism check at `graph_indexer.py:8172-8182` depends on stable output).
2. **Gzip compression on write.** The graph payload (`project-graph.json`) and the per-file state (`project-graph-state.json`) are written gzip-compressed. The clusters artifact (`project-graph-clusters.json`, written at `graph_cluster.py:936`) follows the same path for uniformity. Compression level chosen for write-speed balance (gzip level 6 default; document the choice).
3. **Transparent, sniffing readers.** All graph artifact readers (`_read_json` `graph_indexer.py:947-951`, `read_graph_payload` `graph_indexer.py:8832-8856`, `_load_state` `graph_indexer.py:5552-5569`, `read_cluster_payload` in `graph_cluster.py`) detect the gzip magic bytes (`0x1f 0x8b`) and transparently read **both** compressed and legacy plain-JSON files. A pre-upgrade index must load without error; the next build rewrites it compressed.
4. **Stable file naming.** On-disk filenames stay as-is (`GRAPH_FILENAMES` / `GRAPH_STATE_FILENAMES` / `CLUSTER_FILENAMES` unchanged); the content is sniffed, not the extension. Rationale in Decision Log.
5. **Version bump.** `GRAPH_BUILDER_VERSION` (`graph_indexer.py:35`, currently `"35"`) is bumped in the same change so downstream caches and the version-staleness path treat the transition as a rebuild boundary (standing rule: any change that alters artifact shape bumps the version).
6. **Consumer audit.** Audit every reader of the three artifact paths outside the three modules (dashboard, `gen_codebase_map.py`, tests, any `wf` CLI path) and route them through the sniffing readers; no consumer may `json.loads(path.read_text())` a graph artifact directly after this change.
7. **No behavioral change to graph content.** Node/edge/cluster content, counts, and `input_fingerprint` semantics are byte-for-byte equivalent modulo serialization; a decode → re-encode round-trip of a pre-change artifact yields an identical logical payload.
8. **Atomic writes.** All graph artifact writes go through same-directory temp file + `os.replace`. Today `_write_json` writes in place (`path.write_text`), so a concurrently-reading process (the MCP server reads while builds run in hook-spawned separate processes) can observe a torn file. This becomes acute with `1p9pz`: a stat-keyed cache could pin a torn read, since a torn read taken just after the in-place write finishes carries the file's final stats. (Council finding, prepare review 2026-07-03.)

## Scope

**Problem statement:** Graph artifacts are pretty-printed uncompressed JSON, making the on-disk index ~20× larger than necessary and turning every edit-triggered incremental build into a ~34 MB (repo-proportional) rewrite.

**In scope:**

- Compact separators + gzip in the shared graph artifact writer(s); sniffing readers for all three artifacts.
- Consumer audit and migration of any direct-read call sites to the sniffing readers.
- `GRAPH_BUILDER_VERSION` bump.
- Before/after size and build-time measurements recorded in the Progress Log (self-hosted repo as the fixture).
- Tests: round-trip equivalence, legacy plain-JSON readability, gzip-artifact readability, corrupted/truncated-gzip fallback behavior (matches existing `_read_json` default-on-error contract).

**Out of scope:**

- Any change to graph *content*, extraction, or merge behavior (that is `1p9q2`).
- Restructuring the state file's internal shape (per-file blob store — `1p9q2`).
- Query-side caching (`1p9pz`).
- Compressing non-graph index artifacts (`meta.json`, lance tables — lance has its own format).

## Acceptance Criteria

- [ ] AC-1: After a full graph rebuild on the self-hosted repo, all three graph artifacts are gzip-compressed compact JSON, and the combined size of `project-graph.json` + `project-graph-state.json` + `project-graph-clusters.json` is reduced by at least 10× versus the pre-change baseline (baseline: 35.4 MB combined). Measured numbers recorded in the Progress Log.
- [ ] AC-2: A legacy (pre-change, plain pretty-printed) artifact set loads successfully through every reader path — `read_graph_payload`, `_load_state`, cluster read — with no rebuild required just to read; the next build rewrites compressed. Unit-tested with fixture files in both formats.
- [ ] AC-3: Logical round-trip equivalence — decoding a legacy artifact and re-encoding through the new writer yields an identical payload object (same nodes, edges, counts, fingerprint inputs). Unit-tested.
- [ ] AC-4: A truncated/corrupted gzip artifact degrades exactly as a corrupted JSON file does today (reader returns the caller-supplied default; version-staleness path then triggers re-extraction) — no crash, no half-parsed state. Unit-tested.
- [ ] AC-5: Consumer audit recorded — every call site that reads a graph artifact path is enumerated (grep for the filename constants and direct path literals) and either routed through a sniffing reader or justified; no remaining direct `json.loads` of a graph artifact file.
- [ ] AC-6: `GRAPH_BUILDER_VERSION` bumped; the stale-version query path (`_ensure_graph_builder_current`, `graph_query.py:122-275`) rebuilds a pre-change index on first query and subsequent queries hit the compressed artifacts. Covered by an integration-shaped test.
- [ ] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.
- [ ] AC-8: Atomic writes — every graph artifact write is temp-file + `os.replace` in the artifact's own directory; a reader polling the path during a slow simulated write never observes a partial file (fault-injection or interleaving test), and no in-place `write_text` of a graph artifact remains (grep gate on the writer paths).

## Tasks

- [ ] Introduce gzip-aware write/read helpers alongside `_write_json`/`_read_json` in `graph_indexer.py` (compact separators, `sort_keys=True`, gzip level documented; magic-byte sniff on read; same-directory temp + `os.replace` atomic write); route payload/state writers through them.
- [ ] Route `graph_cluster.py` writer/reader through the same helpers (import or mirror — follow existing cross-module conventions).
- [ ] Audit consumers: grep `GRAPH_FILENAMES`/`GRAPH_STATE_FILENAMES`/`CLUSTER_FILENAMES` and literal `project-graph` path references across `scripts/`, dashboard code, and tests; migrate direct readers; record the audit list in the Progress Log.
- [ ] Bump `GRAPH_BUILDER_VERSION` with a changelog entry in the version-history comment.
- [ ] Tests: dual-format read, round-trip equivalence, corrupted-gzip default, version-bump rebuild path.
- [ ] Measure and record before/after artifact sizes and one incremental-build wall time on the self-hosted repo.
- [ ] Run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-io-helpers | implementer | — | Gzip-aware compact write/read helpers in `graph_indexer.py`; payload + state writers/readers routed through them; version bump. |
| ws2-clusters-and-consumers | implementer | ws1-io-helpers | Cluster artifact on the same path; consumer audit + migration of direct readers. |
| ws3-tests-and-measurement | implementer | ws1-io-helpers, ws2-clusters-and-consumers | Dual-format/round-trip/corruption/version tests; before/after size + build-time measurements. |


## Serialization Points

- The helper signatures in `graph_indexer.py` (ws1) must land before ws2 migrates consumers to them.
- `GRAPH_BUILDER_VERSION` is also bumped by `1p9q1` and `1p9q2` if implemented in the same wave — coordinate to a single final bump at wave integration (one bump covering all three artifact-shape changes is correct; three separate bumps are harmless but noisy).

## Affected Architecture Docs

Audit `docs/specs/mcp-tool-surface.md` (graph index build/status wording) and any architecture doc that states the graph artifact format; update format descriptions from "JSON" to "gzip-compressed compact JSON with legacy plain-JSON read fallback" where the format is documented. Confined otherwise to the indexing module — no boundary or control-flow change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The size reduction is the point of the change; 10× is conservative versus the measured 21.8× gzip ratio. |
| AC-2 | required | Silent inability to read a pre-upgrade index would force spurious full rebuilds on every target repo at upgrade. |
| AC-3 | required | Guarantees the change is serialization-only — no graph-content drift. |
| AC-4 | required | Corruption handling must not regress the existing default-on-error contract. |
| AC-5 | required | A missed direct reader crashes on gzip bytes — the audit is the guard. |
| AC-6 | required | Standing rule: artifact-shape changes bump the builder version so caches rebuild. |
| AC-7 | required | Suite + docs-lint green is the standing merge gate for framework code. |
| AC-8 | required | Council finding: in-place writes + the `1p9pz` stat-keyed cache can pin a torn read; atomicity is the precondition for safe caching. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the graph-index efficiency evaluation. Baseline measured on the self-hosted repo: payload 11,701,810 B, state 22,661,853 B, clusters 1,100,292 B; gzip -9 on payload = 536,711 B (21.8×); cold `json.load` ~30 ms / ~47 MB resident. Writer confirmed `indent=2, sort_keys=True`, no compression. | `graph_indexer.py:973-975`; `.wavefoundry/index/graph/*` measurements 2026-07-03. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Gzip + compact JSON behind sniffing readers (approach A). | ~20× measured reduction with stdlib-only machinery, transparent back-compat, and no change to payload semantics; smallest step that removes the write-amplification bytes before the Tier-2 merge rework. | (B) Compact JSON only, no gzip — weakness: leaves ~10-15× on the table; repeated keys/strings dominate and only compression removes them. (C) Binary/columnar re-encoding (interned string tables, struct-of-arrays, or msgpack) — weakness: a real format change touching every producer/consumer and the fingerprint contract for a marginal win over gzip at current scales; revisit only if profiling after this change shows parse time (not I/O) dominating on large repos. |
| 2026-07-03 | Keep existing filenames; sniff content magic bytes rather than renaming to `.json.gz`. | Filename constants are referenced across modules, tests, and potentially target-repo tooling; content sniffing gives dual-format reads for free and avoids a rename migration. The `.json`-named-but-gzipped tradeoff is acceptable for gitignored machine artifacts. | Rename to `.json.gz` with legacy fallback + cleanup — more honest naming but adds a two-filename resolution path and a cleanup step for every consumer; rejected as churn without benefit for non-human-facing artifacts. |
| 2026-07-03 | Clusters artifact compressed too, despite being only 1.1 MB. | Uniformity: one writer/reader contract for all graph artifacts; avoids a "which files are compressed" special case in every consumer and in `1p9q2`. | Leave clusters plain for human inspectability — rejected: inspectability is one `zcat` away, and mixed formats are a standing trap. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A consumer outside the audited set reads the artifact directly and breaks on gzip bytes. | AC-5 tree-wide audit keyed on the filename constants and path literals; the sniffing reader is exported for any external-ish consumer; corrupted-read contract (AC-4) means a missed reader fails loud in tests, not silently. |
| Compressed writes slow the hot post-edit build path. | Gzip level 6 on ~1-2 MB of compact JSON is single-digit milliseconds; AC-1 measurement includes build wall time to confirm no regression; level is a named constant if tuning is needed. |
| `sort_keys` + separators change perturbs `input_fingerprint` determinism checks. | Fingerprint is computed over node/edge sets (`graph_indexer.py:8172-8182`), not serialized bytes; AC-3 round-trip test guards it explicitly. |
| Version bump forces a one-time synchronous rebuild inside the first query on upgraded repos (`_ensure_graph_builder_current` inline rebuild). | Known, existing behavior for every builder-version bump; upgrade pipeline already rebuilds indexes (`reconcile_scan` runs on every upgrade), so the query-path rebuild is the fallback, not the common case. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
