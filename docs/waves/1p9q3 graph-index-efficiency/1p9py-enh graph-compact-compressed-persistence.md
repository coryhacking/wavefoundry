# Graph index: compact, gzip-compressed persistence for graph artifacts

Change ID: `1p9py-enh graph-compact-compressed-persistence`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-04
Wave: `1p9q3 graph-index-efficiency`

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

- [x] AC-1: After a full graph rebuild on the self-hosted repo, all three graph artifacts are gzip-compressed compact JSON, and the combined size of `project-graph.json` + `project-graph-state.json` + `project-graph-clusters.json` is reduced by at least 10× versus the pre-change baseline (baseline: 35.4 MB combined). Measured numbers recorded in the Progress Log. *(Met 2026-07-03: combined 36,014,585 B → 2,054,390 B = 17.5×; all three files carry the gzip magic bytes.)*
- [x] AC-2: A legacy (pre-change, plain pretty-printed) artifact set loads successfully through every reader path — `read_graph_payload`, `_load_state`, cluster read — with no rebuild required just to read; the next build rewrites compressed. Unit-tested with fixture files in both formats. *(`GraphArtifactPersistenceTests` dual-format tests; pre-existing plain-JSON fixture tests — `_seed_stale_graph`, dashboard `/api/graph` — now exercise the fallback on every run.)*
- [x] AC-3: Logical round-trip equivalence — decoding a legacy artifact and re-encoding through the new writer yields an identical payload object (same nodes, edges, counts, fingerprint inputs). Unit-tested. *(`test_legacy_roundtrip_yields_identical_payload`.)*
- [x] AC-4: A truncated/corrupted gzip artifact degrades exactly as a corrupted JSON file does today (reader returns the caller-supplied default; version-staleness path then triggers re-extraction) — no crash, no half-parsed state. Unit-tested. *(`test_truncated_gzip_returns_default`, `test_corrupted_gzip_body_returns_default`, `test_corrupted_plain_json_returns_default`.)*
- [x] AC-5: Consumer audit recorded — every call site that reads a graph artifact path is enumerated (grep for the filename constants and direct path literals) and either routed through a sniffing reader or justified; no remaining direct `json.loads` of a graph artifact file. *(Audit table in Progress Log 2026-07-03; two direct readers found and migrated: `graph_query.py` version check, `server_impl.py` `_graph_health_summary`.)*
- [x] AC-6: `GRAPH_BUILDER_VERSION` bumped; the stale-version query path (`_ensure_graph_builder_current`, `graph_query.py:122-275`) rebuilds a pre-change index on first query and subsequent queries hit the compressed artifacts. Covered by an integration-shaped test. *(35 → 36; `test_auto_rebuild_fires_when_builder_version_stale` seeds a true plain-JSON pre-change artifact set, asserts the rebuild rewrites both artifacts gzip and the follow-up query is diagnostic-free.)*
- [x] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. *(4287 tests across 41 files OK on the wavefoundry venv python; `__pycache__` cleaned.)*
- [x] AC-8: Atomic writes — every graph artifact write is temp-file + `os.replace` in the artifact's own directory; a reader polling the path during a slow simulated write never observes a partial file (fault-injection or interleaving test), and no in-place `write_text` of a graph artifact remains (grep gate on the writer paths). *(`test_reader_never_observes_partial_file_during_slow_writes` (chunked+slowed temp-file writes with a polling reader), `test_failed_write_preserves_existing_artifact_and_cleans_temp` (fault injection), `test_no_in_place_write_text_in_artifact_writers` (source-level gate on both `_write_json` implementations).)*

## Tasks

- [x] Introduce gzip-aware write/read helpers alongside `_write_json`/`_read_json` in `graph_indexer.py` (compact separators, `sort_keys=True`, gzip level documented; magic-byte sniff on read; same-directory temp + `os.replace` atomic write); route payload/state writers through them. *(Implemented in-place in `_read_json`/`_write_json` (the only graph-artifact I/O helpers) + public `read_json_artifact` alias; `GRAPH_GZIP_LEVEL = 6` documented.)*
- [x] Route `graph_cluster.py` writer/reader through the same helpers (import or mirror — follow existing cross-module conventions). *(Mirrored, matching the module's existing helper-mirroring convention.)*
- [x] Audit consumers: grep `GRAPH_FILENAMES`/`GRAPH_STATE_FILENAMES`/`CLUSTER_FILENAMES` and literal `project-graph` path references across `scripts/`, dashboard code, and tests; migrate direct readers; record the audit list in the Progress Log. *(133-match exhaustive enumeration; audit table in Progress Log.)*
- [x] Bump `GRAPH_BUILDER_VERSION` with a changelog entry in the version-history comment. *(35 → 36.)*
- [x] Tests: dual-format read, round-trip equivalence, corrupted-gzip default, version-bump rebuild path. *(14 new tests in `GraphArtifactPersistenceTests` + strengthened `test_auto_rebuild_fires_when_builder_version_stale`.)*
- [x] Measure and record before/after artifact sizes and one incremental-build wall time on the self-hosted repo. *(Progress Log 2026-07-03.)*
- [x] Run `run_tests.py` + `wave_validate`; clean `__pycache__`. *(4287 OK; clean.)*

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
| 2026-07-04 | Delivery-review scope note: AC-1's 17.5× was measured at this change's own boundary (all three artifacts gzip JSON). After the sibling incremental-merge change replaced the gzip state JSON (1.4 MB) with the SQLite store (3.5 MB incl. the merge-state sidecar), the wave's END-STATE combined footprint is **8.6×** vs the 36.0 MB baseline — still order-of-magnitude, recorded here so the headline is not quoted stale. Independently re-measured by the performance review lane. Also: reader-copy parity gate added (`test_all_sniffing_reader_copies_handle_gzip_magic` — the gzip sniff is mirrored in four modules; a format change that drifts a reader now fails tests). Release-note callout recorded in the wave watchpoints: stale pre-upgrade server sessions cannot read gzip artifacts and must reconnect/`wave_mcp_reload` after upgrading. | Performance lane measurement table 2026-07-04; red-team primer F2/F3. |
| 2026-07-03 | Scoped from the graph-index efficiency evaluation. Baseline measured on the self-hosted repo: payload 11,701,810 B, state 22,661,853 B, clusters 1,100,292 B; gzip -9 on payload = 536,711 B (21.8×); cold `json.load` ~30 ms / ~47 MB resident. Writer confirmed `indent=2, sort_keys=True`, no compression. | `graph_indexer.py:973-975`; `.wavefoundry/index/graph/*` measurements 2026-07-03. |
| 2026-07-03 | **Implemented.** `graph_indexer.py` `_read_json`/`_write_json` rewritten (gzip sniff + legacy fallback; compact separators + `sort_keys` + gzip level 6 (`GRAPH_GZIP_LEVEL`, `mtime=0` for byte-stable output) + same-dir temp + `os.replace`); public `read_json_artifact` alias exported. `graph_cluster.py` mirrors both helpers + exports `read_json_artifact` (module's existing mirroring convention). `GRAPH_BUILDER_VERSION` 35 → 36 with changelog entry (single bump covers the wave's sibling shape changes per the serialization point). | `graph_indexer.py` (imports, v36, `GRAPH_GZIP_LEVEL`, `_read_json`, `_write_json`); `graph_cluster.py` (imports, helpers). |
| 2026-07-03 | **Consumer audit (AC-5)** — exhaustive `code_keyword` enumeration of `GRAPH_FILENAMES`/`GRAPH_STATE_FILENAMES`/`CLUSTER_FILENAMES` + literal `project-graph` (133 matches, limit=0). Production call sites: `graph_indexer.py` `_load_state`/`read_graph_payload`/finalize writers → new helpers (in place); `graph_cluster.py` `_read_existing_clusters`/`read_cluster_payload`/`update_graph_clusters` reader+writer → mirrored helpers; `dashboard_lib.py` `_read_json` (feeds `read_graph_payload`/`read_graph_cluster_payload`) → gzip-sniffing (catches `EOFError`/`zlib.error` too); `gen_codebase_map.py` `_read_json` (graph+cluster) → gzip-sniffing; **`graph_query.py:164` direct `json.loads(state_path.read_text())` in `_ensure_graph_builder_current` → MIGRATED** to `indexer.read_json_artifact` (would have crashed on gzip: `UnicodeDecodeError` was uncaught); **`server_impl.py:3304` direct `json.loads` in `_graph_health_summary` → MIGRATED** to `graph_cluster.read_json_artifact` (would have silently nulled node/edge counts). Justified no-change sites: `dashboard_server.py:230` (mtime stat watch only, no read), `server_impl.py:18918` (default path string in a not-found message, no read), all `graph_path.stat()` size/mtime sites. Test readers of production-written artifacts migrated: `test_graph_indexer.py:481`, `test_indexer.py:1604`, `test_server_tools.py` `_force_stale_state` + rebuild assertion. Test writers of plain-JSON fixtures left as-is deliberately — they exercise the legacy fallback. Zero remaining direct `json.loads(path.read_text())` of a graph artifact. | `code_keyword` audit 2026-07-03; migrated diffs in the files above. |
| 2026-07-03 | **Measurements (AC-1).** Pre-rebuild (v35 plain): payload 11,882,897 B, state 23,013,634 B, clusters 1,118,054 B = 36,014,585 B combined. Post full rebuild (v36 gzip compact): payload 548,760 B (21.7×), state 1,396,324 B (16.5×), clusters 109,305 B (10.2×) = 2,054,390 B combined = **17.5× reduction** (≥10× target met; vs the scoping baseline 35,463,955 B = 17.3×). All three artifacts start with `0x1f 0x8b`. Full graph rebuild: 14.2 s in-build (10,955 nodes / 31,435 edges, 1,277 files). Incremental one-file build: **1.5 s** in-build (2.8 s wall incl. interpreter); no-op incremental short-circuits (~1.1 s wall). Query sanity on compressed artifacts: `load_graph` present=True, builder 36, no rebuild diagnostic; clusters present, 46 communities. | `ls -l .wavefoundry/index/graph/` + timed builds 2026-07-03. |
| 2026-07-03 | **Tests + verification.** 14 new tests in `test_graph_indexer.py::GraphArtifactPersistenceTests` (write format/determinism, temp-file hygiene, dual-format read, public alias, round-trip, 4 corruption/missing cases, fault-injection atomic write, interleaving polling-reader, `write_text` grep gate, cluster parity) + builder-version test updated to 36 + AC-6 integration test strengthened (legacy plain artifact set → rebuild → gzip + clean follow-up query). Full suite: **4287 tests across 41 files OK** (wavefoundry venv python). Architecture doc `docs/architecture/graph-index-system.md` format wording updated (Overview, Disk Artifacts, Cluster Artifacts); `docs/specs/mcp-tool-surface.md` audited — no graph-artifact-format wording present, no change needed. Note: `mkstemp` gives artifacts 0600 perms (was umask 0644) — acceptable for single-user gitignored machine artifacts. | `run_tests.py` output 2026-07-03; doc diffs. |


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
