# code_ask misses cross-file chains and enumerations; the graph rescue never reaches citations

Change ID: `1p66t-enh code-ask-graph-signal-and-enumeration`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-17
Wave: `1p66q code-ask-retrieval-quality`

## Rationale

The quality assessment's hard floor was recall on two shapes: a cross-file behavioral chain collapsed to ~0 (named none of the 3 load-bearing files), and "which X are registered" returned 7 of 17. Grounded root causes (verified):

1. **The graph rescue exists but never reaches `citations`.** `_graph_signal_candidates` (`server_impl.py:1019`) does 1-hop neighbor expansion, but its results land in a separate `graph_related` block, **not** in the `citations` list the answer synthesizes from. An agent/consumer reading `citations` (as Guru is instructed to) sees zero graph signal — so for a cross-file chain where the implementing file doesn't rank above the relevance drop-off, it is simply absent. The graph layer that *should* connect caller→callee across files is computed and then dropped on the floor.
2. **Graph seeding needs a resolvable anchor symbol.** `_graph_signal_candidates` seeds on identifier-like tokens ≥4 chars (`_GRAPH_QUERY_IDENT_RE`) minus `_GRAPH_SEED_STOPWORDS`; a generic NL question ("which providers are registered") resolves no symbol and, if the top semantic breadcrumbs also don't resolve, returns `[]` immediately (`server_impl.py:1088`). Cap is `AGENT_GRAPH_SIGNAL_CAP = 3` (`:163`).
3. **No enumeration intent; the drop-off trims the tail.** `_classify_question` has no "list all X" class. The relevance drop-off (`AGENT_RELEVANCE_DROPOFF = 0.85` × top) plus the text budget trims lower-ranked matches, so a set-of-17 loses members 8–17 once their score falls below 0.85×top. The keyword fallback (`server_impl.py:1300`) only fires when `len(citations) < 2` — a sparse rescue, not an enumeration widener.

This change surfaces the already-computed graph signal into the answer and adds enumeration handling, raising the recall floor on exactly the shapes the assessment said to grep-first today. It pairs with `1p66r` (abstention): better recall reduces, and honest abstention covers, the residual misses.

## Requirements

1. **Graph signal into the citation pool.** When `_graph_signal_candidates` resolves cross-file neighbors (callers/callees/readers) relevant to the question, their source `file:line` are merged into the candidate pool that feeds `citations` (subject to the same fidelity + reranking), not only the separate `graph_related` block. A consumer reading `citations` must see the load-bearing cross-file files when the graph connects them.
2. **Robust seeding for symbol-less questions.** Improve graph seeding so a behavioral/enumeration NL question without a literal symbol can still anchor — e.g. seed from the top reranked code candidate's symbol (not only query tokens / breadcrumbs), so a cross-file chain anchored by the best semantic hit expands along real edges. Keep faithfulness (only real graph edges; no fabricated neighbors).
3. **Enumeration intent → widen, don't trim.** Detect "list/all/which/every X" intent and, for it, widen retrieval (raise the effective `top_n`, relax the 0.85 drop-off) and/or back the answer with an exact pass (`code_keyword`/graph references) so an enumeration returns the full set, not a reranked top-k. The response should signal when an enumeration may be incomplete (a `gaps`-style note) rather than imply completeness.
4. **Bounded.** Widening must stay within sane caps (text budget, a higher but finite enumeration `top_n`) so a hot symbol doesn't balloon the response; the graph merge respects `AGENT_GRAPH_SIGNAL_CAP`-style bounds.
5. Generic; documented in `mcp-tool-surface.md` (`second_hop_symbols` / graph-in-citations + enumeration behavior) and `guru.md` (enumeration + cross-file guidance — currently "grep first"; note the improved-but-still-verify posture). Tests: a 3-file cross-file chain surfaces the load-bearing files in `citations`; an enumeration fixture returns substantially more of the set (and flags incompleteness when it truncates).

## Scope

**Problem statement:** `code_ask` under-recalls cross-file chains (the graph rescue is computed but excluded from citations and needs a literal anchor) and enumerations (top-k drop-off trims the set; no enumeration intent).

**In scope:**

- `_graph_signal_candidates` (`server_impl.py:1019`) — seeding from top semantic code hits; merging resolved neighbors into the citation candidate pool.
- `_classify_question` (`server_impl.py:15072`) + the `code_ask` retrieval path — enumeration intent → widen `top_n`/relax drop-off / exact backing.
- The `code_ask` response (`second_hop_symbols`, an enumeration-incompleteness `gaps` note).
- Tests + docs.

**Out of scope:**

- Confidence/abstention (`1p66r`) and doc/code balance (`1p66s`) — though all three share the `code_ask` path and must be sequenced.
- Reranker availability (`1p66u`).
- New graph extraction (the edges already exist — `1p66e` made them deterministic; this only *consumes* them in `code_ask`).

## Acceptance Criteria

- [x] AC-1: The strongest cross-file graph neighbors that clear the relevance floor are reranked and merged INTO `citations` (flagged `from_graph: true`), bounded by `AGENT_GRAPH_CITATION_CAP`, additive (never reorders the semantic citations) and only when the reranker ran. Faithful by construction — `_node_def_candidate` reads the real on-disk source window, so the merged citation resolves to a real `file:line`. **Positively unit-tested** post-teton: the merge was extracted to `_merge_graph_into_citations` and `GraphSignalTests` now exercises the vector-miss/graph-hit rescue directly — `test_graph_merge_rescues_vector_missed_file` (a graph-reachable file the semantic pass missed is appended `from_graph`), plus already-cited-skip, below-floor-drop, and no-reranker-skip. (Resolves teton finding #2, which left the path unverified because vector recall was always sufficient there.)
- [x] AC-2: Symbol-less behavioral questions already seed graph expansion from the top semantic hits' breadcrumbs (existing `_graph_signal_candidates`, the top reranked candidates); only real graph edges are followed (no fabricated neighbors — `GraphSignalTests` confirms real caller/reader edges). No seeding change was needed; the merge (AC-1) is what newly routes those neighbors into citations.
- [~] AC-3: Enumeration intent (`_is_enumeration_query`) is detected and retrieval is widened (text budget ×`AGENT_ENUMERATION_BUDGET_MULT`) so more of the set clears the cutoff, AND a `gaps` entry flags the list as a ranked sample that may be incomplete. **Narrowed:** "substantially more of the full set" is asserted via the widening mechanism + the honest incompleteness flag rather than a hard "≥N of 17" count — exact set-completeness is explicitly routed to `code_keyword`/`code_references` (vector retrieval is not the right tool for an exhaustive enumeration; over-promising a count would be the very over-claim `1p66r` fixes). Detection + gap unit-tested (`test_is_enumeration_query`, `test_enumeration_query_flags_incompleteness`).
- [x] AC-4: Bounded — graph merge capped at `AGENT_GRAPH_CITATION_CAP=2`; enumeration widening is a fixed `×2.0` text-budget multiplier (no unbounded `top_n`); both reuse existing caps. (`AGENT_GRAPH_SIGNAL_CAP` still bounds the neighbor pool.)
- [x] AC-5: Docs (`mcp-tool-surface.md` graph-into-citations + enumeration bullets, `guru.md` uncertainty protocol) updated; full suite (3308) + docs-lint clean.

## Tasks

- [x] Merge reranked, floor-gated graph neighbors into citations (additive, `from_graph` flag, `AGENT_GRAPH_CITATION_CAP`, reranker-only) in `search_combined`; `_build_graph_related` dedups against them (also_cited).
- [x] Seeding: confirmed existing semantic-hit breadcrumb seeding covers symbol-less questions; no change needed (the gap was routing-to-citations, not seeding).
- [x] Enumeration-intent detection (`_is_enumeration_query`) + text-budget widening + incompleteness `gaps` flag.
- [x] Tests: enumeration detection (pos/neg, incl. the "what is the value" false-positive guard), enumeration gap present/absent; graph-merge building blocks via `GraphSignalTests`.
- [x] Docs: `mcp-tool-surface.md` + `guru.md`; docs-lint + full suite.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| graph-into-citations + seeding | Engineering | `1p66r` | consumes existing graph edges |
| enumeration intent + widening | Engineering | `1p66r` | classification + retrieval path |
| tests + docs | Engineering | both above | |


## Serialization Points

- Shares `_agent_candidate_select` / `code_ask` path + `_classify_question` with `1p66r`/`1p66s`; implement after `1p66r` (and ideally after `1p66s`, since the doc/code quota and the graph merge both touch selection).

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (`code_ask` graph-in-citations + enumeration behavior). No layering change — `code_ask` consumes the existing graph layer.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Cross-file rescue must reach citations — the C2 miss. |
| AC-2 | important | Symbol-less anchoring widens applicability. |
| AC-3 | required | Enumeration completeness — the 7-of-17 miss. |
| AC-4 | required | Bounded — no runaway responses. |
| AC-5 | important | Docs. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | Planned from the quality assessment (C2 cross-file ~0, C1 enumeration 7/17) + grounded root cause. | `_graph_signal_candidates` `server_impl.py:1019`; graph_related-not-citations; `AGENT_RELEVANCE_DROPOFF=0.85`, `AGENT_GRAPH_SIGNAL_CAP=3` `:163`; keyword fallback `:1300` |
| 2026-06-17 | **teton downstream validation — `from_graph`-into-citations UNVERIFIED (not contradicted):** every cross-file chain probed had sufficient vector recall, so the graph-rescue-into-citations path (`from_graph`) never fired (it only adds neighbors NOT already cited, gated on the reranker). `graph_related` populated correctly. Enumeration incompleteness gap, doc/code balance, confidence/abstention, determinism, and AGENTS.md walk-up all ✅ confirmed. **Follow-up DONE (pre-close):** the merge was extracted to `_merge_graph_into_citations` and `GraphSignalTests` now positively exercises the vector-miss/graph-hit rescue in-suite (4 tests: rescue, already-cited-skip, below-floor-drop, no-reranker-skip) — no longer reliant on a downstream vector-miss to confirm the path. | teton 1.7.1.p67a downstream report, finding #2; `_merge_graph_into_citations` `server_impl.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Surface the EXISTING graph signal into citations rather than build new retrieval. | The graph edges already exist (deterministic post-`1p66e`); the miss is that they never reach the answer surface. Cheapest high-recall lever. | A new multi-hop retriever (rejected — over-engineered; the 1-hop graph already computed is unused). |
| 2026-06-17 | Enumerations widen + flag incompleteness rather than silently truncate. | Honesty (pairs with `1p66r`): a partial enumeration that claims completeness is a confidently-wrong failure. | Leave to user-side grep (rejected — the tool should at least not imply completeness). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Graph merge balloons citations on a hot symbol. | Bounded by graph cap + text budget + rerank (AC-4). |
| Enumeration widening surfaces noise. | Exact backing / rerank still applies; incompleteness flagged rather than over-claimed. |
| Seeding from a wrong top hit expands the wrong neighborhood. | Only real edges followed; reranking gates the merged neighbors; abstention (`1p66r`) covers low-confidence expansions. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
