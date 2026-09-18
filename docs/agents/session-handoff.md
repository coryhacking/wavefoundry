# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Current Session

**Active wave:** *(none)*
**Status:** idle. Wave 1yab2 closed with all four delivery lanes approved, all ACs/tasks complete and no deferrals. The full unchanged suite passed 9152 tests with 17 skips at two-worker concurrency; the receipt matches the framework tree. Docs checks passed. Release 1.25.0 is operator-authorized; local qualification is recorded below.

**Delivered:** binary/runtime files no longer inflate source credits; new output says Estimated context avoided and explains the whole-file baseline. Valid text credits, costs, deduplication and archived checkpoint readability are preserved. No history-correction machinery. Memory checkpoint produced zero candidates; lessons remain in the accounting reference. Framework and seed gates are closed.

Memory maintenance: 86 retired generated drafts purged with source-event dispositions retained; two related packaging memories consolidated. Active 118/50 budget, no candidates; 15 history-bearing archives retained. Live text 360,902→227,069 bytes. Fresh-process index health ready/integrity OK and diagnostic evaluation available; attached MCP remains stale and requires host restart. Details: `docs/reports/memory-review-2026-09-17.md`.

Waves 1y6hg and 1y4j8 are closed. The Python advisory wave was committed/pushed as 52158da1; the test-only wave remains uncommitted.

**Last closed wave:** `1yab2 context-accounting-valid-source-baselines` — eligible-text accounting and qualified estimates, with exact legacy readability. Prior identity and memory work is also complete.

Retrospective validated as memory `1y5tz-mem validate-setup-readiness-against-canonical-producers`: test observers with actual producer output and share parser grammar. No wave AC/task deferrals.

**Wave 1y9sv:** closed with all eight ACs and all tasks complete, no deferrals. Refreshed receipt `review-policy-8d546f327a21e8eaa6c7`; all required approvals recorded. Memory checkpoint produced no new candidates. Accounting audit and independent review report retained under the wave evidence directory.

**Waveforge modularity plan, transferred 2026-09-16 from the planning package built against base commit `6a74faed` (uncommitted):** five planned waves and three reports under `docs/reports/` (modularity RFC, implementation kickoff, Waveforge fork audit). Wave `1y0h3 team-upgrade-reconciliation` was withdrawn by operator decision on 2026-09-16 and not extracted: `1y0dl` conflicted with closed wave `1y3og` (no reconcile flag; `wf setup` is the post-pull path), `1y0dn` was delivered by `1y3og` (core indexing proceeds with memory validation pending), `1y0dm` was overtaken (the refusal already names `wf setup`), and `1y0h4` was superseded by `6a74fae`. The package's reference guide `team-framework-upgrade-and-index-reconciliation.md` was not extracted because it contradicts `1y3og` AC-6. Operator also resolved the `1y0h1` registry design on 2026-09-16 (FastMCP tool-table introspection, no 90-site conversion); that change doc was rewritten and the wave re-readied.

| Wave | Changes | State |
| --- | --- | --- |
| `1y0do tool-surface-snapshot` | `1xzsl` | CLOSED 2026-09-17; golden fixture landed (90 tools); uncommitted |
| `1y0gz record-layout-roots` | `1y042`, `1y043` | readied 2026-09-17; no longer hard-depends on `1y0do` |
| `1y0h0 typed-phase-gates` | `1y044`, `1y0bd` | readied 2026-09-17 |
| `1y0h1 tool-registry-dispatch` | `1y0be` | re-readied 2026-09-16 after the registry decision; `1y0do` dependency satisfied |
| `1y0h2 handler-module-split` | `1y0bf` | readied 2026-09-17; requires `1y0h1` closed |

Remaining implementation order: `1y0gz`, `1y0h0`, `1y0h1`, `1y0h2`. The OPEN slot is free.

## Release

Release target `1.25.0` approved 2026-09-17. Two local projects reported successful upgrades to the test package, clean docs/reconciliation checks and completed prompt editing passes. The follow-up clarifies that Python guidance applies only to Wavefoundry tooling, not the host application language. The official path builds the feature archive and verified model set 3 through `build_pack.py --with-models --release`.

Local test build `1.25.0+pqmt` created 2026-09-17 at `~/.wavefoundry/dist/wavefoundry-1.25.0.pqmt.zip` (7,486,022 bytes). SHA-256: `09defc0419ff5b8c176084161090b1ed27673a6b1aff0ad28c058a2521b70f2a`. Docs gate passed; 9152-test receipt current. Outer archive and inner upgrade payload verified, including exact changelog, version and source bytes. VERSION and prompt manifest match. Feature-only local build; no models bundled, tag, commit or publication. Advisory sensor `ac_asserts_repository_state` (1wur7) remains advisory.

Official 1.24.0+ppq7 published on 2026-09-13; tag v1.24.0 and framework/model asset hashes verified. Source commit 3433fb03; release stamp f8e4732e. Host-neutral orchestration is subsequent source work, not a new packaged release.

## Open questions / Deferred decisions

- Not yet scoped: give the `terminology` workflow-config key real consumers beyond the dashboard (rendered docs and messages). Premise correction recorded in `docs/reports/waveforge-fork-audit.md`: the key is read by `dashboard_lib.py` today, and Waveforge's values are keyed by Waveforge tier names (their `wave` is Wavefoundry's `change`), so a change must fix whose vocabulary the keys use before it can claim zero-edit merges.
- Graph-expansion/reranking quality comparison (evaluation AC-4) remains intentionally deferred; current retrieval ordering unchanged.
- Native Windows/Linux/Intel execution remains release follow-through.
- Investigate MCP's initial `graph_rebuilt=false` notice on an all-content full rebuild.
- The CoreML reranker probe fell back to CPU after `output_features has no value for logits`; no reranker fix included.
- Any other unfinished povc receipt must retain its original archive; qualified revision-2 repair: `/Users/coryhacking/.wavefoundry/dist/povc-storage-rebuild-repair-v2.zip`.
- Follow-ups recorded by the 1xtnr council, not in scope: bind the two `graph-index-system.md` builder-version mirrors to `docs_constants_validators._claims()`; a kind-aware `symbol_lookup` once `reads` binds get their own table; route `_scan_all_call_sites_in_file` through `_resolve_repo_path`.
