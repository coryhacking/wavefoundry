# Downstream Validation — 1.7.1 test pack (`wavefoundry-1.7.1.p67a.zip`)

Owner: Engineering
Status: active
Last verified: 2026-06-17

## Purpose

Validate the `1.7.1` test pack on a real consumer repo before committing/releasing. The pack bundles two unreleased waves since v1.7.0:

- **`1p66c` codebase-map-round4** — per-area `AGENTS.md` ancestor-walk resolution + code-graph edge-extraction **determinism** (`GRAPH_BUILDER_VERSION` 31→32, consumers re-extract the graph on upgrade).
- **`1p66q` code-ask-retrieval-quality** — `code_ask` confidence calibration + abstention, doc/code retrieval balance, graph-signal-into-citations + enumeration handling, and reranker batch-size tuning (batch 40).

Recommended consumer: the TS/Nx repo that produced the original `code_ask` quality assessment (re-run the same 12 probes), plus a quick smoke on a JVM and a Swift repo.

## ⚠️ Keep the validation report OUT of the indexed tree

Write your validation report (and any scratch notes) **outside the consumer's indexed tree**, or in an ignored path (e.g. a `.aiignore`/`wavefoundry-ignore` location, or a sibling directory). A report committed into the repo **quotes the test queries verbatim** — so on a re-run the documented off-topic probes match the *report itself* (it ranks high → abstention is defeated → false `medium`/`high`), and the report shows up as a `code_ask` citation on unrelated questions. If you suspect contamination, delete the report from the tree and run an incremental docs reindex, then re-probe. (teton 1.7.1 run hit exactly this — a re-run of the documented off-topic queries matched the report at 0.927 until the artifacts were removed.)

## Prerequisites

- The test pack: `~/.wavefoundry/dist/wavefoundry-1.7.1.p67a.zip` (built on the maintainer machine; copy it to the consumer host).
- A consumer repo already on Wavefoundry ≥ 1.7.0 with a built index.
- The wavefoundry MCP server attached in the consumer's agent (or run `code_ask` via the consumer's CLI).

## Step 1 — Install the pack

1. Copy `wavefoundry-1.7.1.p67a.zip` to the consumer repo root. **Do not unzip it** — the agent unpacks it as the first step.
2. In the consumer's agent, run the shortcut: **Upgrade wave framework**.
3. Expect the upgrade to:
   - extract the pack and advance the framework,
   - run **one graph re-extraction** (the `GRAPH_BUILDER_VERSION` 31→32 bump) — minutes, not a full semantic rebuild; the Lance semantic index is unaffected,
   - reload the MCP server.
4. After upgrade, **reconnect / restart the MCP server** in the agent so it runs the new code (new tools/resources and the new `code_ask`/reranker code need a fresh connection).

**Pass:** upgrade completes, `wave_index_health` reports the graph present at builder version `32`, no errors.

## Step 2 — Reranker is active and on the right batch (`1p66v`)

1. Run any `code_ask` question. Inspect the response:
   - `reranked: true` — the cross-encoder ran.
   - `rerank_ms` is high on the **first** call (one-time CoreML/ONNX compile of the new batch-40 static graph), then small (~100ms on Apple Silicon GPU, more on CPU) on subsequent calls.
2. If `reranked: false`, the response now carries a loud `gaps` entry **"reranker unavailable — ranking is vector-only and degraded …"**. That is the deployment signal: the cross-encoder isn't building on that host (check `WAVEFOUNDRY_EMBED_PROVIDER`, the reranker model cache, and the host's ONNX provider). **Report this if seen** — it is the most likely root cause of the original "confidently wrong" field reports.

**Pass:** `reranked: true` on a healthy host; if `false`, the loud gap is present and names the cause.

## Step 3 — Confidence + abstention (`1p66r`)

Run these probes and check the new fields:

| Probe | Expected |
| --- | --- |
| A clear, well-covered question (a known symbol / "how does X work") | `confidence: high` or `medium`; `gaps` has no "no confident match"; citations are not `weak`. |
| A deliberately off-topic / zero-signal question (e.g. "which sourdough bread recipes are supported") | `confidence: low`; a `gaps` entry **"no confident match — all retrieval scores below the relevance floor …"**; every citation flagged **`weak: true`**; citations still returned (not empty). |
| Re-run the original C2 (cross-file) and E2 (false-negative) probes from the assessment | They should now **abstain** (`confidence: low` + "no confident match" + `weak`) instead of returning confident off-topic citations. |

**Pass:** the off-topic and former confidently-wrong probes now abstain with `weak` citations + the gap; the well-covered probe is unaffected. **`confidence: high` must never appear when `reranked: false`** (capped at `medium`).

## Step 4 — Doc/code retrieval balance (`1p66s`)

1. Ask a "where is X implemented" / "how does X work" question where BOTH a spec/ADR/architecture doc and the implementing source exist.
2. Expect the implementing **code** citation to appear and not be outranked by the prose; the response carries `demotion_count > 0` / `partition_applied: true` for these intents.

**Pass:** code surfaces for code questions; a genuinely doc-answerable question (a spec-defined contract) still surfaces the doc (demotion is a down-weight, not exclusion).

## Step 5 — Cross-file + enumeration recall (`1p66t`)

| Probe | Expected |
| --- | --- |
| A cross-file behavioral chain (caller → mid → implementing across files) | The load-bearing files appear in `citations`, some flagged **`from_graph: true`** (the graph rescue now reaches citations, not only `graph_related`). |
| An enumeration ("which handlers are registered", "list all providers", "what events are subscribed") | A `gaps` entry **"enumeration query — citations are a ranked sample and may be INCOMPLETE …"**; more of the set surfaces than before. For the exhaustive list, the gap routes you to `code_keyword` / `code_references`. |

**Pass:** cross-file chains surface `from_graph` citations; enumerations flag incompleteness rather than implying a complete list.

## Step 6 — Graph determinism + AGENTS.md resolution (`1p66c`)

1. **Determinism:** run `wave_index_build(content='graph', mode='rebuild')` twice on identical source. Compare the `input_fingerprint` in the graph payload/state across the two runs.
   - **Pass:** identical `input_fingerprint` and identical edge count both runs (the round-3 churn — e.g. 75068 vs 74890 — should be gone).
2. **Per-area context:** author (or confirm) an `AGENTS.md` at a project root (e.g. `libs/ui/AGENTS.md`) whose areas are deep subdirectories. Read `wavefoundry://area/<area_id>` for one of those deep areas and check the codebase map's `Area context:` link.
   - **Pass:** the deep area resolves to the ancestor (project-root) `AGENTS.md`; an area with no ancestor `AGENTS.md` returns a graceful not-found.

## What to report back

For each consumer, capture:

- Upgrade outcome + graph builder version + any errors.
- `reranked` value on a sample `code_ask` (and the loud-fallback gap text if `false`).
- The 12-probe re-run scorecard vs the original assessment — specifically whether the previously confidently-wrong probes now abstain.
- The two-rebuild `input_fingerprint` comparison (match / differ + edge counts).
- Reranker first-call vs warm `rerank_ms` (sanity on the batch-40 latency).
- Any regression: a previously-correct answer that now abstains or loses its code citation (over-correction), or a fabricated/mismatched citation (fidelity — must never happen).

## Known limitations (expected, not bugs)

- **No-reranker host:** if the cross-encoder can't build on the host, ranking is vector-only and confidence is capped at `medium` with the loud gap — by design. Fix the reranker setup; don't treat the capped ranking as authoritative.
- **Enumeration completeness:** `code_ask` widens but does not guarantee an exhaustive set — the incompleteness gap intentionally routes exhaustive enumeration to the exact tools.
- **Graph-into-citations** was validated by its building blocks + this downstream pass (the in-suite harness is graph-only); confirm the `from_graph` citations look right on a real cross-file chain and report anything off.
- **`1p66s` no-reranker cross-source balance** is not guaranteed on a no-reranker host (incomparable cosine scales); that host is already flagged degraded by the loud gap.

## References

- Waves: `docs/waves/1p66c codebase-map-round4/`, `docs/waves/1p66q code-ask-retrieval-quality/`.
- `code_ask` contract: `docs/specs/mcp-tool-surface.md` (confidence / abstention / `weak` / degraded-fallback / graph-into-citations / enumeration).
- Agent uncertainty protocol: `docs/agents/guru.md`.
