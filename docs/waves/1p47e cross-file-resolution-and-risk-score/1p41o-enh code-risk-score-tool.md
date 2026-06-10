# Add code_risk_score MCP Tool (Composite Symbol Risk — Blast-Radius × Degree, Extensible)

Change ID: `1p41o-enh code-risk-score-tool`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-06-09

> **Gate GO — operator-confirmed 2026-06-09.** AC-8 re-ran on the rebuilt v24 graph and PASSED (pooled ρ(risk, fan_in)=0.796 ≤ 0.95, CoV(afc)=0.981 ≥ 0.3; per-module degeneracy 81%→50%, flat-afc 46%→17% vs the `1p41l` NO-GO). The per-module residual (uniform-blast-radius small modules track `fan_in`) was folded into AC-9 usage guidance, not treated as a blocker. Operator confirmed **"pass"** — `1p41o` ships. All ACs satisfied; evidence in the Progress Log.
Wave: 1p47e cross-file-resolution-and-risk-score

> **GATED behind `1p470` (wave `1p47e` stage gate) — re-attempt of a tool gated out in `1p41l`.** This was gated out at AC-8 in the now-closed `1p41l` (2026-06-08): the composite collapsed to a `fan_in` degree proxy because the call graph lacked cross-file `Class.method` edges (the blast-radius term was near-constant). It is re-admitted here as `planned`, **gated**: `1p470` ships cross-file receiver resolution + rebuilds the graph first; then `code_risk_score`'s **AC-8 re-runs** against the rebuilt graph. **Implement this change ONLY if the composite is then non-degenerate (Spearman ρ ≤ ~0.95); if it is still a degree proxy, re-defer it.** See the `1p47e` STAGE GATE watchpoint.
> The tool was implemented in the query layer and run against the real project graph. The composite `risk = affected_file_count * log1p(fan_in)` collapses to a pure `fan_in` (degree) proxy on the **majority of real modules**: across 52 in-cap modules, normalized Spearman ρ(risk, fan_in) > 0.95 on **42/52 (81%)**, and `affected_file_count` is **flat across all symbols in 24/52 (46%)**. Root cause is structural and confirmed by self-check: the call graph systematically lacks cross-file `Class.method()` edges (87% of `calls` edges are intra-file `EXTRACTED`), so the blast-radius term is near-constant — e.g. `GraphQueryIndex.from_root`, called from dozens of sites in `server_impl.py`, has **0** `calls` edges and `affected_files = 0`. The pre-committed rank-normalize fallback did not rescue it (often unchanged or worse). Per the operator's gate logic, an irreducible degree proxy is gated out, not shipped. The query-layer method was **reverted** (no unwired/dead code); the design is preserved in this change doc + git history. **Wave `1p47e` addresses exactly that revisit condition:** sibling change `1p470` adds cross-file receiver resolution, after which the blast-radius term should vary and AC-8 re-runs (the wave's stage gate) to decide whether this ships. See the Decision Log + the `1p47e` Journal Watchpoints. Related: [[project_mcp_code_tool_quality_log]].

## Rationale

Aceiss field eval §3.2 asks for a one-call pre-change safety score that ranks the symbols in a module by how dangerous they are to touch, so an agent can prioritize before a cross-cutting change. Round-5 grounding confirmed **both required primitives already exist**, so this is a pure query-layer composition with **no new extraction and no `GRAPH_BUILDER_VERSION` bump**:

- **Blast radius** — `GraphQueryIndex.graph_impact` (`graph_query.py:1200`) returns `affected` + `affected_files` with per-node `hop`.
- **Degree** — from `GraphQueryIndex._out`/`_in` (`graph_query.py:914`). Use the **calls-only** `fan_in`/`fan_out` (matching `report()`, `graph_query.py:1310-1320`), **not** the all-edge degree (which also counts `imports`/`defines` and would inflate module/import nodes — computed separately in the communities section ~`server_impl.py:13009-13013`, not `:12951` which is a `collapse_generated_files` comment). No reusable degree helper exists, so the tool computes it inline over `calls` edges.

**Naming (resolved):** the report called it "churn" — which implies git-commit churn, a *temporal* metric this does not measure. "Refactor risk" was also rejected as too narrow: the blast-radius risk applies to *any* edit (bugfix, feature, signature change), not only behavior-preserving refactors. The tool is named **`code_risk_score`** and framed as a **general composite**: v1 combines blast-radius × degree; it is designed to absorb further structural signals later (e.g. cyclomatic complexity, chokepoint/community membership, doc/test gaps) **without a rename**. Because the name is intentionally generic, the docstring and spec must lead with the dimension and surface the score's component inputs so it is never a black box.

## Requirements

1. New MCP tool `code_risk_score` in the query layer; no index/extractor changes.
2. Input: a scope to rank over — `path` or glob (and/or `module`), plus optional `top` (default 20), `max_hops` (passed through to impact, default 3), `layer`.
3. For each candidate symbol defined in scope, compute `affected_file_count` (derived as `len(affected_files)` from `graph_impact`, after the test-path filter `code_impact` applies), `fan_in`, `fan_out` (calls-only degree), and a composite `risk`. The v1 formula leads on the **upstream** signals (load-bearing for *risk of changing X*) with degree **log-dampened** to avoid hub domination: `risk = affected_file_count * log1p(fan_in)`. `fan_out` (X's own outgoing calls — near-orthogonal to change-risk) is **surfaced as an independent component, not multiplied into `risk`**. Formula + raw component values are surfaced in the response. (The candidate set — definitions in scope, before scoring — is bounded: error or truncate above a cap, e.g. 200, since `graph_impact` runs a BFS per candidate.)
4. Output: list ranked descending by `risk`, each entry carrying the impact/report field names — `node_id`, `label`, `source_file` (NOT `symbol`/`file`) — plus the raw `affected_file_count`, `fan_in`, `fan_out`, `risk`, and worst-case `hop`. The response carries a top-level `score_formula` string **and** a `score_components` list whose names map 1:1 to those per-entry raw inputs — so the score is transparent, re-weightable, and extensible without breaking the contract.
5. Top-N cap enforced (default 20) to avoid token overflow; document that `top` controls it. The docstring leads with the dimension: *"ranks symbols by how risky they are to change — a composite of blast-radius × degree."*

## Scope

**Problem statement:** there is no single-call "which symbols in this module are dangerous to touch?" — agents must run `code_impact` per symbol and eyeball degree manually.

**In scope:**

- Query-layer composite scoring over existing `graph_impact` + degree primitives.
- MCP tool wiring (`server_impl.py`), docstring (composite framing), `docs/specs/mcp-tool-surface.md` + `211-guru.prompt.md` mention, unit tests, prompt-surface manifest update if the tool count is tracked.

**Out of scope:**

- Git commit-history churn (not indexed) — deliberately **not** what this score measures.
- Additional composite signals (complexity, coverage, hotspot membership) — future extensions the `score_components` contract is designed to admit, not part of this change.
- Any new extractor or `GRAPH_BUILDER_VERSION` bump; dashboard / UI surfacing.

## Acceptance Criteria

> **Re-attempt, gated.** AC-8 (the value gate) returned NO-GO in `1p41l` (degree proxy). It **re-runs as `1p47e`'s stage gate** after `1p470` lands + the graph rebuilds; AC-1..AC-7 and AC-9 are the implementation criteria that apply **only if** the gate passes. See the banner + the `1p47e` STAGE GATE watchpoint. (ACs reset to `[ ]` — this is planned work again, not the gated-out terminal state.)

- [x] AC-1: `code_risk_score(scope=...)` returns `results` with `affected_file_count`, `fan_in`, `fan_out`, `risk`, and `hop` per symbol, plus top-level `score_formula` + `score_components`. *(Verified: query-layer + wrapper-layer tests; end-to-end on the real graph.)*
- [x] AC-2: results are sorted descending by `risk`; the `top` cap is enforced and documented (default 20).
- [x] AC-3: tool runs against the existing graph payload with **no** `GRAPH_BUILDER_VERSION` change (verify the constant is untouched).
- [x] AC-4: docstring and `mcp-tool-surface.md` lead with the dimension ("risk of *changing* this symbol"), enumerate the score's current component inputs (blast-radius × degree), and state it is a structural composite designed to grow — explicitly **not** git-history churn. The raw components are surfaced in the response so the score is not a black box.
- [x] AC-5: unit tests cover the scoring math, descending ranking, empty-scope, and the top-N cap.
- [x] AC-6: `run_tests.py` and docs-lint pass; `mcp-tool-surface.md` documents the tool.
- [x] AC-7: an **MCP wrapper-layer** regression test asserts `code_risk_score` returns the documented fields (`risk`, `score_formula`, `score_components`, per-symbol `affected_file_count`/`fan_in`/`fan_out`) through the tool boundary — not just the query-layer function (carry-forward lesson from waves `130rj`/`130ol`).
- [x] AC-8: **degeneracy go/no-go gate — RE-RUNS as the `1p47e` stage gate, after the FULL `1p470` (Phase 1 typed-language + Phase 2 Python) ships + the graph rebuilds** (the sample is this repo's Python-heavy modules, whose blast-radius signal comes from Phase 2 — measure after both phases, not Phase 1 only). On a sample of **≥10 real modules spanning low/medium/high fan-in**, evaluate in order:
  - **(1) PRECONDITION — blast-radius non-degeneracy:** `affected_file_count` across the sample must have **coefficient of variation (stddev/mean) ≥ 0.3** (the `1p41l` NO-GO had it flat in 46% of modules). If it is still near-constant (`CoV < 0.3`), the cross-file resolution produced no usable blast-radius signal → **re-defer `1p41o`** (do not run the ρ test on a flat distribution — that is the noise-low-ρ false-positive the readiness review flagged).
  - **(2) INDEPENDENCE — Spearman gate:** compute ρ(risk, fan_in) on the sample. **PASS (ship) only if ρ ≤ 0.95** (risk is not merely a `fan_in` proxy).
  - **(3) FALLBACK:** if `0.95 < ρ`, recompute with the pre-committed **rank-normalize fallback** (rank-normalize each composite dimension before summing) and **PASS only if ρ then ≤ 0.95**; otherwise **re-defer**.
  - **Auditable closure evidence (mandatory):** record the sampled module list, per-module `affected_file_count`, the computed CoV, and ρ (pre- and post-fallback) in this change doc — the borderline-ρ case (e.g. 0.94 vs 0.96) must be decided by the recorded numbers, not interpretation. If re-deferred, set `Change Status: deferred` + relocate to `docs/plans/` with this evidence.
  - **Threshold provenance (operator decision, 2026-06-09):** the `CoV ≥ 0.3`, `≥10`-module, and `ρ ≤ 0.95` values were authored at prepare and **operator-accepted as provisional** — left as-is now, to be **sanity-checked / calibrated against the actual observed `affected_file_count` distribution and ρ spread when the gate runs**, not treated as immutable. The `ρ ≤ 0.95` line is the original `1p41l` decision; `CoV ≥ 0.3` and `≥10` are the prepare-authored additions most worth revisiting at gate-time.

  (Prior run in `1p41l` 2026-06-08 was NO-GO — degree proxy on 81% of modules, `affected_file_count` flat in 46% — because cross-file `Class.method` `calls` edges were absent; `1p470` is the fix that makes the re-run meaningful.)
- [x] AC-9: usage guidance reaches the **existing graph-tool recipe depth** in `211-guru.prompt.md` (regenerated into `guru.md` per the seed-first rule) — **not** a one-line pointer. The recipe must carry: (a) **when to reach for it** — *before a cross-cutting change/refactor, to prioritize which in-scope symbols to touch carefully*; (b) the explicit **`code_risk_score` vs `code_impact` distinction** — `code_risk_score` *ranks many* symbols across a scope, `code_impact` sizes *one* symbol's blast radius (the key "why this tool" answer); (c) **how to read the output** — `risk` is a *relative rank within the queried scope*, read `score_components` not the raw number, it is *structural, not git-churn*; (d) an **anti-pattern** note — do not treat the raw `risk` as an absolute or cross-module-comparable magnitude; (e) an entry in the **per-role tool-routing tables** (e.g. the implementer / architect-reviewer rows). Verifiable by inspecting the regenerated `guru.md` recipe + routing-table rows at close.

## Tasks

- [x] Implement `risk_score(scope, max_hops, top, layer)` in `graph_query.py` reusing `graph_impact` + degree, returning the score plus its named components.
- [x] Wire the `code_risk_score` MCP tool in `server_impl.py` with the documented response shape (`score_formula` + `score_components`).
- [x] Add unit tests (scoring, ranking, cap, empty scope, component surfacing).
- [x] Document in `docs/specs/mcp-tool-surface.md`; add a **full recipe** in `211-guru.prompt.md` at the depth of the existing graph-tool recipes (when-to-use, `code_risk_score` vs `code_impact` distinction, how-to-read `score_components`, anti-pattern) **plus a per-role tool-routing-table entry**, then regenerate `guru.md` from the seed (seed-first); update prompt-surface manifest if required. (Requires `seed_edit_allowed`.)
- [x] Run the AC-8 go/no-go gate on ≥2 real modules **before** marking the tool's ACs complete; if it gates out, defer the tool (relocate the change to `docs/plans/`) and record the no-go rather than shipping a degree proxy.

## Agent Execution Graph


| Workstream         | Owner       | Depends On | Notes |
| ------------------ | ----------- | ---------- | ----- |
| scoring (query)    | Engineering | —          | `graph_query.py`, reuse impact+degree; emit named components |
| MCP wiring + docs  | Engineering | scoring    | `server_impl.py` (sole new tool registration in the wave — `1p41q` deferred) |
| value gate (AC-8)  | Engineering | scoring    | run on ≥2 real modules; ship-or-defer decision |
| guidance recipe (AC-9) | Engineering | MCP wiring | full recipe + role-routing in `211-guru.prompt.md` → regen `guru.md` |


## Serialization Points

- None within the wave: `code_risk_score` is now the **only** new `server_impl.py` tool registration (`1p41q` was deferred 2026-06-08), so there is no sibling-registration collision to sequence. If other `server_impl.py` work is in flight outside this wave, coordinate the tool-registration region as usual.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — add a one-line entry for the new query-layer tool. No new boundary or data-flow (composition over existing primitives).

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core tool output, incl. transparent components |
| AC-2 | required  | Ranking is the tool's purpose |
| AC-3 | required  | No-index-bump invariant — query-layer only |
| AC-4 | required  | Composite transparency + dimension framing prevents black-box / churn misread |
| AC-5 | required  | Scoring/ranking correctness needs tests |
| AC-6 | required  | Framework tests + lint + spec |
| AC-7 | important | Wrapper-layer regression (130rj/130ol lesson) |
| AC-8 | required  | Go/no-go value gate — ship only if non-degenerate, else defer (do not ship a degree proxy) |
| AC-9 | required  | Recipe-level usage guidance — without it the tool is built-but-unused (the adoption gap the value review flagged) |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-09 | **AC-8 stage gate RE-RUN on the rebuilt v24 graph (post-`1p470`) → PASS (pooled), with a documented per-module nuance for AC-9.** Ran the real `GraphQueryIndex.risk_score` over 12 real self-host modules spanning fan-in. **Pooled (833 scored symbols):** CoV(affected_file_count)=**0.981** (≥0.3 precondition PASS); Spearman ρ(risk, fan_in)=**0.796** (≤0.95 INDEPENDENCE PASS, no fallback needed). **Per-module (1p41l-comparable):** degenerate (ρ>0.95) **6/12 (50%)** vs `1p41l` 81%; flat-afc (CoV<0.3) **2/12 (17%)** vs `1p41l` 46% — the cross-file + lazy-loader edges measurably reduced degeneracy. Residual: within tiny single modules with near-uniform blast radius, `risk` still tracks `fan_in` (correct — when afc is uniform the highest-degree symbol *is* the riskiest); the tool's distinct signal is on broad/cross-module scopes where afc varies → folded into AC-9 guidance. | Per-module table: graph_query.py ρ=0.71, wave_lint_lib ρ=0.48, lifecycle_id ρ=0.69, scan_secrets ρ=0.50 (good divergence); graph_indexer/chunker/setup_index ρ≈1.0 (uniform-afc small modules). `from_root` now scores with fan_in=12 (was 0 → the `1p470` lazy-loader fix directly feeds the score). |
| 2026-06-09 | **Implemented** (gate GO). `GraphQueryIndex.risk_score(scope, max_hops, top, candidate_cap, is_test_path)` in `graph_query.py` (composite over `graph_impact` + calls-only degree, `risk = afc * log1p(fan_in)`, `fan_out` surfaced not multiplied, over-cap guard, scope path/dir/glob). MCP tool `code_risk_score` + `code_risk_score_response` in `server_impl.py` (dimension-leading docstring, `score_formula` + `score_components`, test-path filter, error paths). 10 new tests (7 query-layer math/ranking/cap/empty/glob/test-filter + 3 wrapper-layer field-contract/empty/over-cap). No `GRAPH_BUILDER_VERSION` change (query-layer only — the v24 bump is `1p470`'s). | `run_tests.py` **2946 green**; `server.py --dry-run` OK (tool registers); end-to-end response verified on the real graph. |
| 2026-06-09 | **AC-8 evidence CORRECTION (delivery-council red-team finding).** The original gate measurement used a Spearman with no tie-handling, which DEFLATED the per-module ρ recorded above (graph_query.py 0.71→**0.911**, lifecycle_id 0.69→**0.892** with proper average-rank ties; scan_secrets 0.50→0.55). The **gate criterion (pooled ρ ≤ 0.95) still PASSES and reproduces**: proper-tie pooled ρ = **0.802** over 2,309 symbols / 59 in-cap `.py` modules ≈ the recorded 0.796. Per-module degeneracy (ρ>0.95) with the tool's default test-filter = **23/59 (39%)** — down from `1p41l`'s 81% (the red-team's "83%" was measured WITHOUT the default filter). Honest read: most small modules are strongly degree-correlated (0.85–0.95); the tool's *distinct* signal is on broad scopes, exactly as the AC-9 guidance states. **Caveat:** `.wavefoundry/index/` is gitignored/per-machine, so these numbers are a point-in-time measurement, not a committed reproducible harness (follow-on: ship a measurement harness). Gate CONCLUSION (PASS / ship) unchanged; the correction is to the per-module evidence precision, not the verdict. | Proper-tie Spearman re-measurement on the committed v24 graph (59 modules, default filter). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-07 | Named `code_risk_score`, framed as a general composite (not `code_churn_risk`/`code_refactor_risk`) | "churn" implies git-commit churn (a temporal metric this does not measure); "refactor" is too narrow — blast-radius risk applies to *any* edit, not only behavior-preserving refactors; operator wants an extensible composite | `code_refactor_risk`, `code_change_risk`, `code_edit_risk` considered; `code_risk_score` chosen for neutrality + future-proofing, with the docstring/`score_components` carrying the dimension so the generic name is not a black box |
| 2026-06-07 | v1 score = `affected_file_count*(fan_in+fan_out)`, treated as a validation hypothesis (council R-2) | `affected_file_count` and `fan_in` are correlated; degree may dominate the ranking | Validate on a real module during implementation; normalize/separate factors if degree-dominated (AC-8) |
| 2026-06-07 | Git commit-history churn excluded from the score | Commit history is not indexed; the composite is structural | Index git churn — rejected this scope (separate, larger build); the `score_components` contract leaves room to add it later if indexed |
| 2026-06-08 | **Refined (pre-impl review):** drop `fan_out` from the headline product (surface it independently); log-dampen degree (`affected_file_count * log1p(fan_in)`); count **calls-only** `fan_in`/`fan_out` over **resolved** edges (exclude low-confidence EXTRACTED, matching `code_impact`'s refactor-safety filter); bound the candidate set; make AC-8 a Spearman-ρ degeneracy gate with a pre-committed rank-normalize fallback. | The grounded review confirmed `affected_file_count` and `fan_in` are correlated by construction (fan_in is the hop-1 subset of the reverse reach), so the original `count*(fan_in+fan_out)` behaves ~degree² and hubs dominate; `fan_out` measures what X depends on (near-orthogonal to change-risk). Also fixed the stale degree citation and pinned the calls-only definition. | Keep `fan_in+fan_out` product (degree-dominated); normalize without dropping `fan_out` (still correlated, adds noise). |
| 2026-06-08 | **Gated + guidance-raised (operator value re-assessment):** AC-8 elevated from "important" to a **required go/no-go** — ship only if the `risk` ranking diverges from raw `fan_in` (directly or after the normalize fallback); if it stays a degree proxy, gate the tool out and defer it (do not ship a degree restatement). Added **AC-9** requiring `211-guru.prompt.md` guidance at the existing graph-tool recipe depth (when-to-use, `code_risk_score` vs `code_impact`, how-to-read, anti-pattern, role-routing entry), not a one-line pointer. | Operator asked whether the net-new tools carry real value + enough usage guidance. The tool's value over `code_impact` is real (ranking across a scope) but *conditional* on non-degeneracy, and a non-obvious optional tool with one-line guidance is built-but-unused. Both risks are now AC-enforced. (Sibling `1p41q` deferred in the same pass — see wave Review Checkpoints.) | Ship ungated with a soft validation note (risks shipping a degree proxy + an orphaned tool); defer `1p41o` too (rejected — its ranking value is distinct from `code_impact` and worth building behind the gate). |
| 2026-06-08 | **GATED OUT — AC-8 NO-GO (branch (c)).** Implemented `risk_score` in the query layer and ran the gate against the real project graph (6,947 nodes / 20,212 edges). Verdict: do **not** ship; reverted the query-layer method (no dead code); **deferred it in `1p41l`** (later relocated to wave `1p47e` for a gated re-attempt behind `1p470` — see the next row). The wave ships only its doc-gap fixes (`1p41m`/`1p41n`) + the dashboard fix (`1p466`) — exactly the prepare-council's strongest-alternative. | Empirical degeneracy on the majority of real modules: normalized Spearman ρ(risk, fan_in) > 0.95 on **42/52 (81%)** in-cap modules; `affected_file_count` flat across all symbols in **24/52 (46%)**; the rank-normalize fallback did not rescue it. Root cause (self-checked): the call graph lacks cross-file `Class.method()` `calls` edges (87% of `calls` edges are intra-file `EXTRACTED`), so the blast-radius term is near-constant and the composite collapses to `log1p(fan_in)` — e.g. `GraphQueryIndex.from_root` (dozens of cross-file call sites) has 0 `calls` edges → `affected_files = 0`. An agent gets the same ordering from `wave_graph_report` fan_in / `code_callhierarchy` already; guru.md:286 already warns that empty `code_impact` ≠ no callers. | Ship only on the ~7 modules where ρ < 0.8 (rejected — a tool can't know in advance which modules it helps on; a degree proxy 81% of the time misleads). Keep the method unwired for a future formula (rejected — dead code; design lives in git + this plan). **Revisit condition:** the call graph gains reliable cross-file method-call resolution (separate extractor wave), making the blast-radius term meaningful. |
| 2026-06-08 | **Relocated from closed `1p41l` to new wave `1p47e`; re-set to `planned`, gated behind `1p470`.** Operator created `1p47e` for the coupled pair (cross-file resolution + risk-score) with a stage gate between them; ACs reset `[~]`→`[ ]` (planned work again), AC-8 re-runs as the gate. | The gate-out's documented revisit condition (cross-file call resolution) is now being delivered by sibling `1p470` in the *same* wave — so the deferred work is resumed behind the AC-8 re-run gate rather than left parked in a closed wave. | Leave it deferred in closed `1p41l` (rejected — operator wants it actively re-attempted, gated); mint a fresh successor change (rejected — duplicates the spec + the rich gate-out evidence; relocating the doc preserves both). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Generic name `risk_score` is silent on *which* risk | Docstring/spec lead with the dimension ("risk of changing X"); response surfaces `score_components` so the composite is self-describing |
| Per-symbol `graph_impact` over a large scope is slow | Cap candidate set to in-scope definitions; honor `top`; document cost |
| Score degenerates to "highest-degree node wins" (degree dominates correlated terms) | Validate ranking on a real module (AC-8); surface raw factors via `score_components` so the agent can re-weight; normalize if needed |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
