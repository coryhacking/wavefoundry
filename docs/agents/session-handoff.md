# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-07-11

## Current State

**Two waves ready for the 1.12 release:**

1. **Wave `1rsh9 sqlite-index-substrate` — CLOSED, committed as `a62d612a`** (4 changes: state store, FTS5 hybrid lexical, secret-scan cache, Tantivy retirement; details in the wave record and memory).
2. **Wave `1sbfi external-supertype-visibility` — IMPLEMENTED, delivery-reviewed, CLOSE-READY (awaiting operator close), UNCOMMITTED.** Operator-directed pre-1.12 work. `1sbfh`: the field-reported blind spot (class implements an external interface → invisible, unlike `calls`) is closed at the query/server layer — the census proved extraction already emitted the edges. Shipped: external-supertype name resolution (project-shadowed; distinct-id grouping, never merged), `code_impact` external seeds labeled with implementor blast radius + `external_candidates` ambiguity breakdown, `supertypes` sections with always-on external counts on `code_impact`/`code_callhierarchy` (include_external gate, calls parity). **No `GRAPH_BUILDER_VERSION` bump** — field graphs light up on upgrade without re-extraction. 14 new tests; suite 4,832 OK; `wave_validate` clean; `wave_close` dry-run PASSES; seeds 211/180 + tool docstrings + graph-index-system/mcp-tool-surface/feedback docs updated.

**Companion finding:** the other planned pre-1.12 item (corp-TLS cluster) was verified ALREADY SHIPPED (uv scrub 1.9.7 via 1p8tg; launcher CA coverage 1.10.0 via 1p939; host-agent CA vars in the ladder) — memory corrected, no work needed.

## Next Steps

1. **Operator decision: close wave `1sbfi`** (dry-run passes) and commit it.
2. **Release 1.12.0** — bundles waves `1rsh9` + `1sbfi` (CHANGELOG section at release time; commit-style bullets, no build numbers/wave IDs; `build_pack.py --release` needs a clean tree + the `## [X]` section; gh account `coryhacking`). Post-upgrade note for field repos: `wave_mcp_reload` for running servers; the graph tools' new signals work against existing graphs immediately.
3. Wave `1ro44` (agent memory + churn decay) remains READIED and unblocked — natural next wave after the release.

## Follow-ups recorded (not blocking)

- Retire the `1rycf` close-time bloat gate once field data confirms (Tantivy leak source removed by 1rsh9/1sauc).
- Stale-content Lance drift detection via a freshness-store cross-check.
- Tier 2 rule-delta secret scanning (spike: partially viable).
- `meta.json` reader migration; graph build-path auto-maintenance (deferred per 1rq4h AC-7).
- Extraction-side: qualification-via-import-facts for unqualified external supertype declarations (census note in `1sbfh` — would let two unqualified same-name externals separate; extraction modeling, needs its own change).

## Session Notes

- The pre-edit hook fails when the shell cwd is inside `.wavefoundry/framework/scripts/` — `cd` back to repo root before Edit calls.

## Current Session

**Active wave:** *(none)*
