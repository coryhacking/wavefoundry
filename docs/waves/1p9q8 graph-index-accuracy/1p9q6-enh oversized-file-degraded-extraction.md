# Graph accuracy: degraded line-scan extraction for files over the tree-sitter parse cap, instead of total omission

Change ID: `1p9q6-enh oversized-file-degraded-extraction`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-06
Wave: TBD

> **CONVENTION REVERSAL (reality-checker freshness lane, 2026-07-05): this change no longer DEFINES the "line-scan degradation convention" — it must MIRROR one that already landed.** 1p9q6 never shipped, but wave **1p9qe** (SQL ERROR-region DDL recovery) landed a bounded, comment/string-masked, line-anchored degraded-extraction tier FIRST, establishing the framework's canonical shape: a provenance marker (`_SQL_RECOVERY_MARKER = "sql_recovery"`, `graph_indexer.py:7332`; every recovered object carries `extraction: "sql_recovery"`), per-file count properties on the module node (`sql_error_regions`/`sql_recovered_definitions`/`sql_unrecovered_regions`), a bounded masked scan (`_sql_recover_error_region:7468`, `_sql_recovery_mask_noncode:7380`), and a verbose build-log line (`_sql_recovery_log_line:7562`). 1p9q6's oversized-file tier is still genuinely UNBUILT (no `line_scan` marker exists — verified live 2026-07-05), so the change is still valid; but its Requirement 4 marker/counts/logging must be re-worded to ALIGN with the 1p9qe precedent (a parallel `extraction: "line_scan"` marker + analogous per-file counts + a shared log-line style), not to introduce a novel convention. See the 2026-07-05 Progress Log row.

## Rationale

Files larger than `WAVEFOUNDRY_MAX_TS_PARSE_BYTES` (default 2 MB, `MAX_TREESITTER_PARSE_BYTES_DEFAULT`, `graph_indexer.py:2287`; the guard shipped in the 1p5c4/v30 bump) skip AST graph extraction **entirely**: no module node beyond the file's presence, no defines, no imports, no calls. A 2.1 MB generated-but-referenced file (large API clients, generated bindings, vendored single-file libraries) becomes a hole in the graph — everything that imports it dangles to `external::`, its symbols are unfindable by `code_definition`-adjacent graph paths, and `code_impact` silently understates blast radius through it. The 5 MB walk cap (`MAX_INDEX_FILE_BYTES_DEFAULT`, `indexer.py:685`) at least logs a skip; the 2 MB AST cap silently degrades graph accuracy while the file still counts in the corpus.

Total omission is the wrong degradation shape. A bounded, AST-free line scan can recover the highest-value, lowest-risk facts — import statements and top-level definition names — at `EXTRACTED` confidence, keeping oversized files *connected* (imports in/out, defines) without pretending to call-graph fidelity. This mirrors the framework's now-canonical honest-degradation tier — the 1p9qe SQL ERROR-region recovery scan (marker + per-file counts + bounded masked scan + verbose log; `graph_indexer.py:7332,7380,7468,7562`) — and the older label-propagation fallback for Leiden: reduced fidelity, loudly labeled, never silent absence.

## Requirements

1. **Line-scan fallback tier.** Files over the AST cap (but under the walk cap) get a bounded line-oriented scan extracting: (a) import/include/use statements per language family (reusing per-language import-pattern knowledge where practical — anchored line-start patterns, not general regex over the whole content), and (b) top-level definition names (`def`/`class`/`function`/`fn`/`type`/`impl`-style line-anchored declarations). Emitted as normal module/definition nodes and `imports`/`defines` edges at `EXTRACTED` confidence.
2. **No call edges.** The fallback never emits `calls`/`reads`/`extends` edges — those require structure the scan cannot faithfully see. Definitions from fallback files participate as **targets** for other files' resolution only through the existing unique-candidate rule (a fallback-extracted twin can therefore correctly force refusal — that is a feature: presence knowledge preventing a wrong bind).
3. **Bounded cost.** The scan is single-pass, line-anchored, with a hard line-length guard and a scan-byte ceiling (own constant, env-overridable) so pathological minified one-liners cannot blow up build time; over the ceiling → today's behavior (skip, but now logged). Encoding robustness (council finding, prepare review 2026-07-03): the scan handles the decode shapes big generated files actually exhibit — UTF-8 BOM stripped, decode-errors fall back per the walker's existing encoding policy, a missing final newline still yields the last line; undecodable content degrades to logged skip, never a crash.
4. **Honest labeling — MIRROR the landed 1p9qe convention (reality-checker 2026-07-05).** Fallback-extracted module nodes carry a marker (`extraction: "line_scan"` node property, the direct parallel to 1p9qe's `extraction: "sql_recovery"` at `graph_indexer.py:7332`) so consumers and reviewers can distinguish them; per-file count properties on the module node follow the `sql_error_regions`/`sql_recovered_definitions`/`sql_unrecovered_regions` shape (e.g. `line_scan_defines`/`line_scan_imports`/`line_scan_skipped`); the build log line counts fallback files in the style of `_sql_recovery_log_line` (`graph_indexer.py:7562`); the skip (only past the scan ceiling) is logged, not silent. Reuse the 1p9qe marker/count/log conventions rather than inventing new ones.
5. **Cap semantics unchanged.** The 2 MB AST cap and 5 MB walk cap values/overrides are untouched; this change only replaces empty extraction with degraded extraction between them.
6. **Calibration gate.** Fixture: a >2 MB source file with known imports/definitions (synthesized in-test) — assert recovered imports/defines and node marker; before/after graph connectivity for a corpus containing it (dangling `external::` count drops). Precision guard: the line scan must not invent definitions inside strings/comments in the fixture's adversarial sections.
7. **Version bump + adversarial review.** `GRAPH_BUILDER_VERSION` bumped; included in the wave's adversarial faithfulness review (the scan is a detection surface; silent narrowing/over-extraction both matter).

## Scope

**Problem statement:** Files between the 2 MB AST cap and the 5 MB walk cap silently contribute nothing to the graph, creating dangling edges and understated impact through exactly the large generated/vendored files that other code heavily imports.

**In scope:**

- The line-scan fallback tier (imports + top-level defines, `EXTRACTED` confidence, no call edges), its cost bounds, node marker, and logging.
- Adversarial precision fixtures (strings/comments/minified-line cases); connectivity calibration.
- Version bump.

**Out of scope:**

- Changing either cap's default or the walk-cap behavior.
- Chunked/partial tree-sitter parsing of oversized files (revisit only on field evidence; parse-cap exists because tree-sitter cost/robustness degrades there).
- Semantic (embedding) indexing of oversized files — separate pipeline with its own size policy.
- Any call-graph recovery from fallback files.

## Acceptance Criteria

- [x] AC-1: A fixture file over the AST cap yields a module node with `extraction: "line_scan"`, its import edges, and its top-level definition nodes/defines edges — and no `calls`/`reads` edges. Unit-tested across at least Python-style, C-style, and Go/Rust-style declaration syntaxes. Evidence: `test_line_scan_exact_set_and_count_properties` (exact node+edge set on a Go fixture; `assertFalse` on any calls/reads) + `test_line_scan_multi_syntax_declaration_families` (Python/C/Rust/Go scanner-level).
- [x] AC-1b: The per-file line-scan count node properties MIRROR the 1p9qe recovery convention shape — a test asserts `line_scan_defines`/`line_scan_imports`/`line_scan_skipped` (parallel to `sql_recovered_definitions`/`sql_error_regions`/`sql_unrecovered_regions`) exist on the module node with the CORRECT values for a fixture (not merely that the aggregate build-log count is emitted). Convention-mirror pinned by name. Evidence: `test_line_scan_exact_set_and_count_properties` asserts all three by name (defines=2, imports=1, skipped=0).
- [x] AC-2: Referrers of an oversized file's symbols resolve against its fallback-extracted definitions under the unique-candidate rule, and a fallback-extracted twin forces refusal of an otherwise-unique bind. Unit-tested both directions (the presence-prevents-wrong-bind case is the faithfulness core). Evidence: `test_line_scan_referrer_resolution_and_twin_refusal` — direction 1 (unique line-scan candidate → `calls` resolves to `big/widget.go::Widget` at RECEIVER_RESOLVED); direction 2 (twin added → bind refuses to `external::Widget`; line-scan def is one of the two candidates).
- [x] AC-3: Adversarial precision — declaration-looking text inside string literals, comments, and a minified single-line segment does not produce definition nodes; scan-ceiling overflow degrades to logged skip. Unit-tested. Evidence: `test_line_scan_adversarial_precision_and_ceiling` — ghost declarations in `//`/`/* */`/string/over-length line mint nothing; whole-file ceiling → `ceiling_skipped`/`line_scan_ceiling_skipped`, no nodes, no marker.
- [x] AC-4: Cost bound — the scan of a maximum-size fixture completes within the single-pass bound (instrumented; measurement recorded), and the build log reports fallback-file count and any past-ceiling skips. Evidence: `test_line_scan_cost_bound_and_build_log` — 20,000-def fixture scanned in ~230 ms (< 3 s bound; measurement printed); verbose build asserts the "N file(s) over the AST parse cap" summary + per-file line.
- [x] AC-5: Connectivity calibration — on a fixture corpus with an oversized hub file, dangling `external::` references to its symbols drop versus baseline; counts recorded in the Progress Log. Evidence: `test_line_scan_connectivity_calibration` — dangling `external::Widget` baseline=1 → treatment=0, resolved-to-hub=1 (recorded 2026-07-05 Progress Log row).
- [x] AC-6: `GRAPH_BUILDER_VERSION` bumped; adversarial review lane covers the scan's over/under-extraction modes; findings dispositioned. — **[integration 2026-07-05]** the bump portion is DONE: coordinated `39→40` landed (the `extraction: "line_scan"` nodes + `line_scan_defines`/`line_scan_imports`/`line_scan_skipped` properties are named in the changelog head). — **[delivery review 2026-07-06]** the adversarial review lane over the scan's over/under-extraction modes RAN (PASS: invents nothing from strings/comments/docstrings/minified lines, emits zero calls/reads, ceiling overflow degrades to a logged skip, twin-refusal correct — all verified live). Findings dispositioned. AC complete.
- [x] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. Evidence: full suite green (see Progress Log); `wave_validate` clean; `__pycache__` cleaned post-run.

## Tasks

- [x] Implement the line-scan extractor (per-language-family line-anchored import + top-level definition patterns; line-length guard; scan-byte ceiling; `extraction` marker; logging). `graph_indexer.py`: `_line_scan_extract`, `_line_scan_mask` (comment-only vs full-mask modes), `_line_scan_comment_profile`, `_line_scan_log_line`, constants `_LINE_SCAN_MARKER`/`_LINE_SCAN_MAX_BYTES_DEFAULT`/`_LINE_SCAN_MAX_LINE_CHARS`.
- [x] Wire it into the size-gate path between the two caps; ensure fallback definitions flow into the cross-file candidate sets. `_over_ts_parse_cap` helper + the `_extract_code_artifact` over-cap branch → `_extract_line_scan_artifact` (before the unbounded JS/TS regex fallback); definitions populate `defined_symbols`/`simple_names` and the node map (`_build_candidate_indexes` picks them up automatically).
- [x] Fixtures + tests per AC-1..AC-5 (multi-syntax, adversarial strings/comments/minified, twin-refusal, connectivity, cost). 7 new tests in `test_graph_indexer.py` (+ encoding-robustness).
- [x] Bump `GRAPH_BUILDER_VERSION` with changelog entry; run `run_tests.py` + `wave_validate`; clean `__pycache__`. — **[integration 2026-07-05]** coordinated `39→40` landed (single bump across all four `1p9q8` changes per Journal Watchpoint); the changelog head names the line-scan nodes/properties. `run_tests.py`/`wave_validate`/`__pycache__` clean.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-line-scan | implementer | — | The scanner: patterns, bounds, marker, logging. |
| ws2-gate-wiring | implementer | ws1-line-scan | Size-gate path integration; candidate-set participation. |
| ws3-tests-calibration | implementer | ws2-gate-wiring | Multi-syntax + adversarial + twin-refusal + connectivity fixtures; cost measurement. |
| ws4-adversarial-review | reviewer | ws3-tests-calibration | Red-team: what does the scan invent, and what does it still silently miss? |


## Serialization Points

- Shares `graph_indexer.py` size-gate region; disjoint from `1p9q4`/`1p9q5`'s resolution code but coordinate the single wave-level `GRAPH_BUILDER_VERSION` bump.
- The twin-refusal behavior (AC-2) intersects `1p9q5`'s scope tiers — a fallback-extracted definition must count in those candidate sets too; add one cross-change fixture at integration.

## Affected Architecture Docs

Update the indexing size-policy documentation wherever the 2 MB cap's "skips AST extraction" behavior is described (v29 changelog context; `docs/specs/mcp-tool-surface.md` index notes if present): behavior becomes "degrades to line-scan extraction (imports + top-level definitions, labeled) up to the scan ceiling." No boundary/flow impact.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The fallback tier existing and being labeled is the change. |
| AC-1b | important | The per-file count-property convention-mirror (parallel to 1p9qe) must be pinned by name, not just the aggregate log count. |
| AC-2 | required | Candidate-set participation (including refusal-forcing) is where accuracy is won or silently lost. |
| AC-3 | required | Inventing definitions from strings/comments would pollute candidate sets repo-wide — worse than the current hole. |
| AC-4 | required | An unbounded scan on pathological files would regress the build path this tier exists to protect. |
| AC-5 | important | Connectivity delta demonstrates the value; a weak delta prompts re-scoping, not blocking. |
| AC-6 | required | Standing version-bump and adversarial-review rules for detection surfaces. |
| AC-7 | required | Suite + docs-lint green is the standing merge gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the graph-index accuracy evaluation. Confirmed: >2 MB files skip AST extraction entirely (v29 changelog; `MAX_TREESITTER_PARSE_BYTES_DEFAULT`, `graph_indexer.py:1797-1799`; propagated via `WAVEFOUNDRY_MAX_TS_PARSE_BYTES`, `indexer.py:2892`); 5 MB walk cap logs skips (`indexer.py:685,689-709,844-859`) but the AST cap is silent; degradation precedent = Leiden→label-prop fallback (`graph_cluster.py:335-343`). | `graph_indexer.py:1797-1799`; `indexer.py:685,844-859,2892`; evaluation 2026-07-03. |
| 2026-07-05 | **Implemented (implementer lane).** Added the bounded line-scan degraded-extraction tier to `graph_indexer.py`, mirroring the 1p9qe recovery convention at the marker/counts/log layer (scanner itself is new: whole-file, AST-free, comment/string-masked, line-anchored). Wiring: `_over_ts_parse_cap` + `_extract_code_artifact` over-cap branch → `_extract_line_scan_artifact` (precedes the unbounded JS/TS regex fallback). Recovers imports + top-level defs at EXTRACTED, marks `extraction: "line_scan"` on module + def nodes, emits NO calls/reads. Per-file props `line_scan_defines`/`line_scan_imports`/`line_scan_skipped` (+ `line_scan_ceiling_skipped`) on the module node + a `_line_scan_log_line` build-log line. Exact-set flip verified. **Calibration (AC-5): dangling `external::Widget` baseline=1 → treatment=0; resolved-to-hub=1.** Cost (AC-4): 20,000-def scan ~230 ms single-pass (< 3 s bound). 7 new tests; full suite 4618 tests OK (`test_graph_indexer.py` 461). **Version bump DEFERRED** to wave integration (coordinated single 39→40). | `graph_indexer.py` (`_over_ts_parse_cap`, `_line_scan_extract`, `_line_scan_mask`, `_extract_line_scan_artifact`, `_extract_code_artifact` wiring, build-log loop); `tests/test_graph_indexer.py` (7 tests); full suite green 2026-07-05. |
| 2026-07-05 | **Freshness reconciliation (reality-checker lane). Verdict: NEEDS-RE-SCOPE (convention reversal — mechanism still valid).** Tier still UNBUILT (no `line_scan` marker exists — verified live), so the core change holds. But the "line-scan degradation convention" this doc claimed to DEFINE was landed FIRST by wave 1p9qe (SQL ERROR-region recovery): provenance marker `_SQL_RECOVERY_MARKER="sql_recovery"` (`graph_indexer.py:7332`), per-file count props (`sql_error_regions`/`sql_recovered_definitions`/`sql_unrecovered_regions`), bounded masked scan (`_sql_recover_error_region:7468`, `_sql_recovery_mask_noncode:7380`), verbose log (`_sql_recovery_log_line:7562`). Requirement 4 re-worded to MIRROR that convention (marker + counts + log style), not define it. STALE-ANCHOR fixes: `graph_indexer.py:1799`→`:2287`; 5 MB walk cap = `MAX_INDEX_FILE_BYTES_DEFAULT`, `indexer.py:685` (2 MB AST cap `MAX_TREESITTER_PARSE_BYTES_DEFAULT` at `indexer.py:686`). Coordinated version bump target now **39→40**. | live verify 2026-07-05: `graph_indexer.py:2287,7332,7380,7468,7562`; `indexer.py:685-686`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Bounded line-anchored scan for imports + top-level definitions only, no call edges (approach A). | Recovers the facts that reconnect the graph (who imports it, what it defines) with a cost and precision profile a line scan can actually guarantee; refuses the facts (calls) it cannot see faithfully — honest degradation over silent absence, matching the Leiden-fallback precedent. | (B) Chunked tree-sitter parse (split file, parse windows) — weakness: window boundaries corrupt scope/structure; wrong-structure ASTs risk *wrong* edges, worse than missing ones. (C) Raise the cap — weakness: the cap exists for parse cost/robustness; raising trades a hole for a stall and remains a cliff, just farther out. (D) Leave as-is, log the skip — weakness: fixes silence but not the graph hole; kept as the past-scan-ceiling behavior. |
| 2026-07-03 | Fallback definitions participate fully in cross-file candidate sets. | Presence knowledge is the point: it both enables correct binds to oversized-file symbols and correctly *blocks* wrong unique-candidate binds that only looked unique because the twin was invisible. | Quarantine fallback nodes from resolution — rejected: preserves today's wrong-bind exposure exactly where the file is a heavily-imported hub. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Line scan invents definitions from strings/comments/minified content, polluting candidate sets. | Line-anchored patterns + line-length guard + adversarial fixtures (AC-3); adversarial review targets invention modes; `EXTRACTED` confidence keeps downstream weighting conservative. |
| Per-language pattern table drifts from real declaration syntax (misses or false positives per language). | Start with the language families the extractor already profiles (`_TS_PROFILES` list) using their known keyword anchors; multi-syntax tests per family (AC-1); unmatched languages simply yield module+imports only. |
| New fallback twins flip previously-bound unique candidates to refusal, dropping some existing binds. | Correct behavior (the bind was only unique through blindness) — called out for the adversarial review and visible in the calibration counts, so the delta is examined rather than assumed regression. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
