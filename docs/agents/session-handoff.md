# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Current Session

**Active wave:** *(none)*
**Status:** idle. Wave 1y6hg closed after all five ACs, required delivery reviews and docs checks passed. Fresh framework receipt: 9,104 tests across 95 files, 12 skips; two-worker run passed the unchanged timing check. No commit or push performed.

**Paused wave:** `1y4j8 portable-windows-path-test` retains its three-line test-only fix and prior reviews. BackgroundRefreshActiveTests passed all13 on macOS3.13.5; exact-method controls passed on3.11/3.13, restored-old failure on3.11 and constant-result mutants rejected. No nativeWindows claim. Preserve these unrelated pending edits.

**Last closed wave:** `1y6hg python-runtime-deprecation-advisory` — Python 3.11/3.12 remain allowed with once-only command/MCP startup advice, nonblocking health data and interpreter-transition guidance.

Retrospective validated as memory `1y5tz-mem validate-setup-readiness-against-canonical-producers`: test observers with actual producer output and share parser grammar. No wave AC/task deferrals.

## Release

Official 1.24.0+ppq7 published on 2026-09-13; tag v1.24.0 and framework/model asset hashes verified. Source commit 3433fb03; release stamp f8e4732e. Host-neutral orchestration is subsequent source work, not a new packaged release.

## Open questions / Deferred decisions

- Graph-expansion/reranking quality comparison (evaluation AC-4) remains intentionally deferred; current retrieval ordering unchanged.
- Native Windows/Linux/Intel execution remains release follow-through.
- Investigate MCP's initial `graph_rebuilt=false` notice on an all-content full rebuild.
- The CoreML reranker probe fell back to CPU after `output_features has no value for logits`; no reranker fix included.
- Any other unfinished povc receipt must retain its original archive; qualified revision-2 repair: `/Users/coryhacking/.wavefoundry/dist/povc-storage-rebuild-repair-v2.zip`.
- Follow-ups recorded by the 1xtnr council, not in scope: bind the two `graph-index-system.md` builder-version mirrors to `docs_constants_validators._claims()`; a kind-aware `symbol_lookup` once `reads` binds get their own table; route `_scan_all_call_sites_in_file` through `_resolve_repo_path`.
