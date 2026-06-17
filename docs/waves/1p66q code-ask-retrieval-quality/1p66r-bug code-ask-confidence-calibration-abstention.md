# code_ask reports high confidence and emits citations on zero-signal retrieval

Change ID: `1p66r-bug code-ask-confidence-calibration-abstention`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-17
Wave: `1p66q code-ask-retrieval-quality`

## Rationale

A ground-truthed quality assessment (12 probes graded against grep/Read/git, not the index) found `code_ask`'s **most dangerous** failure mode: it returns confidently-wrong answers rather than abstaining. On a cross-file query with top retrieval scores ~0.001 it emitted off-topic navigation citations; on a false-negative ("does hook X exist?") it `confidence=high` denied a real hook by leaning on a stale doc. Citation *fidelity* is otherwise excellent (zero fabrications across 12 probes) — the problem is calibration + the absence of abstention, which turns "I don't know" into "confidently wrong."

Two concrete code facts (verified) cause this:

1. **No-reranker confidence is count-based and score-blind.** `_heuristic_confidence` (`server_impl.py:15088`) returns `"high"` whenever `n >= 2` citations exist when `reranked=False` (`return "high" if n >= 2 else "medium"`). The per-index floor (below) guarantees ≥2 citations on any non-empty index, so **every** answer reports `high` when the reranker did not run — regardless of relevance. (Whether the consumer's reranker is even active is itself unknown — see `1p66u`; this bug is exactly why the `reranked` field matters.)
2. **The per-index floor manufactures citations from noise.** `_agent_candidate_select` guarantees each source ≥`AGENT_PER_INDEX_FLOOR_K = 3` slots (`server_impl.py:157`), so a zero-signal query still emits ~6 citations even when every cross-encoder score is ~0.001. There is **no abstention path**: the only `gaps` "no indexed evidence" entry (`server_impl.py:15320`) fires solely when citations are *empty* (an empty index), never on poor relevance. When the reranker *did* run, the 0.1 floor (`CONF_AGENT_RERANK_LOW`) correctly yields `confidence=low`, but citations are still emitted unmarked, so a consumer treats them as load-bearing.

The fix is the single highest-value change for trust: make confidence relevance-aware in both paths and add a real abstention signal, **without** sacrificing the zero-fabrication citation fidelity.

## Requirements

> **Single-path clarification (operator Q):** `code_ask` has ONE ranking path — rerank-first agent selection (`rerank_mode` always `"agent"`; the old `local`/`rrf_fallback` modes were removed in 1p52p). `reranked=False` is not a mode; `_agent_rerank` (`server_impl.py:925`) returns `False` ONLY when the cross-encoder is unavailable (`WAVEFOUNDRY_DISABLE_RERANKER`, or the model can't build/load, or `rerank()` raises). A healthy install always reranks. So the no-reranker branch is a *degraded fallback*, and the consumer's confidently-wrong cases most likely mean their reranker wasn't running — which must be made loud (Requirement 6), not silently handled.

1. **No-reranker confidence is not blindly high.** When `reranked=False`, confidence must not be `"high"` purely because `n >= 2`. Cap it at `"medium"` so the count-based floor can never report `high` on an unranked result set. (No absolute cosine floor here — see Requirement 2.)
2. **Relevance-gated abstention (reranked path only).** When the cross-encoder ran and even the best candidate score is below the relevance floor (`CONF_AGENT_RERANK_LOW = 0.1`; the ~0.001 zero-signal case), `code_ask` adds an explicit `gaps` "no confident match" entry and the citations are marked weak (Requirement 3); `_heuristic_confidence` already returns `low` in this band. **No analogous absolute floor in the no-reranker path** — its per-citation scores are mixed-model cosine (arctic-doc vs bge-code) on incomparable scales (prepare-council condition 1), so the no-reranker signal is the confidence cap (Req 1) + the loud-fallback gap (Req 6), not a miscalibrated absolute threshold.
3. **Floor-filler citations are marked, not silently load-bearing.** The per-index anti-starvation floor (3 docs + 3 code) must not present below-floor candidates as confident citations. Either suppress sub-floor floor-fillers when stronger candidates exist, or flag them (a per-citation `weak: true` / `below_floor: true`) so a consumer/agent does not treat them as answer-bearing. The anti-starvation intent (don't return empty when *something* plausibly relevant exists) is preserved.
4. **Citation fidelity preserved.** No change weakens the existing guarantee that every emitted citation points at a real `file:line` whose text matches — the zero-fabrication property is the crown jewel and a regression here is unacceptable.
5. Generic, language-agnostic; the `gaps`/confidence contract documented in `docs/specs/mcp-tool-surface.md` (`code_ask` response fields) and `docs/agents/guru.md` (uncertainty protocol — how an agent should treat `confidence=low` + abstention `gaps`). Tests cover: no-reranker not-high, sub-floor abstention, weak-citation marking, loud reranker-unavailable gap, and a positive case still `high`.
6. **Loud degraded fallback.** When `reranked=False` (the reranker did not run), `code_ask` surfaces an explicit `gaps` entry stating ranking is vector-only/degraded and naming the cause (disabled / model-unbuildable), so a silently-degraded install is visible (a healthy install always reranks). This is the missing diagnostic behind the field "confidently wrong" cases — the consumer was likely on the silent fallback.

## Scope

**Problem statement:** `code_ask` cannot say "I don't know." It manufactures confident-looking citations from zero-signal retrieval and reports `high` confidence on unranked results, producing confidently-wrong answers — the worst RAG failure mode.

**In scope:**

- `_heuristic_confidence` (`server_impl.py:15088`) — relevance-aware in both reranked and no-reranker paths.
- The candidate-selection / response assembly (`_agent_candidate_select` ~`server_impl.py:1186`; `code_ask` response ~`server_impl.py:15197`) — a score floor that drives abstention `gaps` + weak-citation marking.
- `gaps` population on low-relevance (not only empty index).
- Docs: `mcp-tool-surface.md` `code_ask` fields, `guru.md` uncertainty protocol.
- Tests in `test_server_tools.py`.

**Out of scope:**

- Improving *recall* (Tier 3, `1p66t`) or the doc/code mix (Tier 2, `1p66s`) — this change only makes the tool honest about what it did/didn't find.
- Reranker provider/availability (`1p66u`) — though this bug is *why* reranker presence matters; the two are complementary.
- Any change to how citations are extracted/verified (fidelity untouched).

## Acceptance Criteria

- [x] AC-1: With the reranker unavailable (`reranked=False`), a query does **not** report `confidence=high` — it is capped at `medium` (never count-based `high`). (`test_confidence_no_reranker_capped_at_medium`, `test_confidence_no_reranker_keyword_path_capped_medium`.)
- [x] AC-2: A zero-signal query under the reranker (top score below `CONF_AGENT_RERANK_LOW`) returns `confidence=low` AND a `gaps` "no confident match" entry, AND its citations are marked `weak`. (`test_reranked_zero_signal_abstains_and_marks_weak`.)
- [x] AC-3: The per-index floor still prevents an empty result when plausibly-relevant candidates exist (anti-starvation preserved) — abstention is a *signal*, not silence. (Same test asserts citations still returned.)
- [x] AC-4: Citation fidelity unchanged — emitted citations still resolve to real `file:line` with matching text; existing `code_ask` citation tests pass unchanged (full suite 3299 green). `test_reranked_strong_match_no_abstention` guards no over-correction.
- [x] AC-5: When `reranked=False`, a loud `gaps` entry names the degraded vector-only fallback + cause. (`test_no_reranker_emits_loud_degraded_gap`.)
- [x] AC-6: `mcp-tool-surface.md` (`code_ask` confidence/gaps/`weak`-citation/degraded-fallback contract) and `guru.md` (uncertainty protocol) updated; full suite + docs-lint clean.

## Tasks

- [x] Make `_heuristic_confidence` relevance-aware: no-reranker path capped at `medium` (never count-based `high`); keep the reranked `CONF_AGENT_RERANK_HIGH/LOW` bands.
- [x] Reranked-path abstention: on sub-floor top score add a `gaps` "no confident match" entry; mark sub-floor citations `weak`.
- [x] Loud degraded-fallback `gaps` entry when `reranked=False` (cause named).
- [x] Tests: no-reranker-not-high, sub-floor abstention + weak marking, anti-starvation preserved, loud reranker-unavailable gap, positive-case no-over-correction; reconciled the 3 stale count-based-`high` tests.
- [x] Docs: `mcp-tool-surface.md` + `guru.md`; docs-lint + full suite (3299 green).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| confidence + abstention | Engineering | — | single-module (`server_impl.py`) |
| docs + tests | Engineering | confidence + abstention | mcp-tool-surface + guru + test_server_tools |


## Serialization Points

- `server_impl.py` `code_ask` path is shared with `1p66s`/`1p66t` — sequence to avoid overlapping edits (this change first; it is the safety floor the others build on).

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (`code_ask` response contract) and `docs/agents/guru.md` (uncertainty protocol). No layering/boundary change — single-module behavior + contract doc.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Kills the count-based `high` on unranked results. |
| AC-2 | required | The abstention path — the core fix. |
| AC-3 | required | Anti-starvation must not regress. |
| AC-4 | required | Citation fidelity is non-negotiable. |
| AC-5 | important | Contract + agent-protocol docs. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | Planned from the code_ask quality assessment (confidently-wrong on C2/E2/A2) + grounded root cause. | `_heuristic_confidence` `server_impl.py:15088`; `AGENT_PER_INDEX_FLOOR_K` `:157`; `CONF_AGENT_RERANK_HIGH/LOW` `:220-221`; gaps `:15320` |
| 2026-06-17 | **teton downstream validation found + fixed (in-session):** a capitalized leading interrogative / conversational lead-in ("Which"/"Where"/"Tell"/"Explain"/…) was extracted by `_extract_question_symbol`'s capitalized fallback as a "symbol", and symbol-first injection then keyword-boosted off-topic citations above the relevance floor — DEFEATING abstention for the capitalized phrasing (the lowercase form, not matched by the ≥4-char capitalized fallback, abstained correctly). Fix: `_QUESTION_NONSYMBOLS` stopword set + the bare-word fallbacks iterate (`re.findall`) and skip these, so a capitalized question abstains like its lowercase form while a real symbol later in the question is still found. Explicit symbols (backtick/qualified/@/CONSTANT) are never filtered. `test_extract_question_symbol_skips_interrogatives`; full suite 3309 green. | teton 1.7.1.p67a downstream report, finding #1; `_extract_question_symbol`/`_QUESTION_NONSYMBOLS` `server_impl.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Add an abstention *signal* (confidence=low + gaps + weak-marking), not hard silence. | Anti-starvation floor has value (a weak lead beats nothing) IF it is honestly labeled; silence loses a sometimes-useful navigation hint. | Hard-suppress all sub-floor citations (rejected — loses the navigation value + over-corrects); leave as-is (rejected — the dangerous failure). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-abstaining: marking real-but-modest matches as weak. | Anchor the floor on the existing `CONF_AGENT_RERANK_LOW = 0.1` band (already tuned); positive-case AC guards against over-correction. |
| Confidence change breaks consumers parsing the field. | Field values stay within the existing `{low, medium, high}` enum; only the *mapping* tightens. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
