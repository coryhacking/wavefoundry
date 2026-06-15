# Nested-type constant retrieval miss (code_ask / code_constants)

Change ID: `1p5k0-bug nested-type-constant-retrieval`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-14
Wave: `1p5dk 1-6-release-hardening`

## Rationale

Surfaced by downstream **solaris** (Swift, 699 files): `code_ask("What is the value of RoutineConfig.maxRetries and where is it used?")` returned the usage sites but **not** the declaration `static let maxRetries = 3` — the declaration was absent from citations and `definition_boosted` never fired. The constant is nested: `static let maxRetries` inside `struct RoutineConfig` inside `class AutomationController`.

Empirical bisection (vary one factor): the decisive contrast is **bare-leaf vs dotted-qualifier**, NOT the "value" decoy or reader-intent. Three distinct issues, severity-ranked:

1. **PRIMARY — symbol-first injection was gated to `question_type == "explanatory"`.** Value/where-is questions classify **navigational**, so they got no injection and depended on raw vector top-K; a dotted-phrase embedding ranks usage chunks above the one-line declaration, so it never entered the candidate pool and `_definition_match_boost` had nothing to lift. (The boost itself works — `_extract_question_symbol` leaf-falls-back and the leaf branch matches `{max,retries}`, confirmed by passing bare-leaf rows.)
2. **SECONDARY — chunk-lane nested-type flattening.** `_walk_class_members` recursed into a nested type with the *unchanged* outer class name, so `struct RoutineConfig`'s member was attributed to `AutomationController` (not `AutomationController.RoutineConfig`). Consequences: `code_constants(["RoutineConfig.maxRetries"])` couldn't resolve, the qualified-token boost branch couldn't match the natural qualifier, same-named members of two nested types collided, and the chunk lane diverged from the (correct) graph lane. Paired matcher gap: `code_constants_response` matched only the bare leaf OR the full qualified name — never an intermediate dotted suffix.
3. **NOISE (cosmetic) — graph-seed extractor picks generic English words.** `_GRAPH_SEED_STOPWORDS` omitted `value`, so "what is the value of X" seeded graph traversal on `value` and spent second-hop expansion on unrelated readers. Doesn't change citations; visible in `graph_related`.

NOT the cause (verified — left alone): `DEFINITION_MATCH_BOOST` (1.3×) is not too weak — it lands the declaration at #1 whenever the symbol is a candidate; bumping it would risk the 1p4hj AC-10 calibration for no gain.

(Patches were authored + unit-verified downstream and applied to this tree before tracking; this change doc records them retroactively. The in-tree `1p5xx` placeholder ID was replaced with `1p5k0`.)

## Requirements

1. Symbol-first injection fires for **navigational** value/where-is questions too (not explanatory-only), so a query-named declaration enters the candidate pool regardless of vector top-K. The wide-window + two-hop gates stay explanatory-only.
2. The chunk lane attributes nested-type members to the **qualified** owner (`Outer.Inner.x`) and emits a nested-type `__decl__` chunk — aligning with the graph lane. `CHUNKER_VERSION` bumps (chunk-set shape change → forced re-chunk/re-embed).
3. `code_constants` resolves the bare leaf, the full qualified name, AND every intermediate dotted suffix (`Outer.Inner.x` → `{x, Inner.x, Outer.Inner.x}`) — without over-matching a bogus prefix.
4. `_GRAPH_SEED_STOPWORDS` excludes generic decoy nouns (`value`/`flag`/`option`/…) so the graph seed isn't hijacked — WITHOUT adding them to `_QUERY_STOPWORDS` (they stay content terms for `DEFAULT_TIMEOUT`-style definition matching).
5. **No regression** to the 1p4hj AC-10 recall + dilution eval from widening injection onto navigational queries.

## Scope

**In scope:** `server_impl.py` (injection gate; `code_constants` dotted-suffix matcher; graph-seed stoplist), `chunker.py` (nested-type qualified descent + `CHUNKER_VERSION` 30→31), regression tests, CHANGELOG.

**Out of scope:** `DEFINITION_MATCH_BOOST` weight; the graph lane (already nests correctly — no `GRAPH_BUILDER_VERSION` bump); the wide-window / two-hop explanatory-only gates.

## Acceptance Criteria

- [x] AC-1: the AC-10 recall + dilution eval (`run_recall_eval.py`) passes after the injection widening — **11/11, exit 0** (5 constant ≤5, 6 symbol all #1, incl. navigational-classified queries; no dilution regression). This is the gate for the PRIMARY change.
- [x] AC-2: nested-type members get qualified qnames in the chunk lane and `code_constants` resolves the intermediate dotted suffix; asserted by tests (chunker nested-qname + `code_constants` dotted-suffix incl. a negative no-over-match case). `CHUNKER_VERSION` bumped 30→31; full suite + docs-lint green.

## Tasks

- [x] Patch 1: widen symbol-first injection gate to `("explanatory", "navigational")`.
- [x] Patch 2a/2b: nested-type qualified descent in `_walk_class_members`; dotted-suffix matching in `code_constants_response`; `CHUNKER_VERSION` 30→31.
- [x] Patch 3: add decoy nouns to `_GRAPH_SEED_STOPWORDS` (graph-seed scope only).
- [x] Replace the `1p5xx` placeholder ID (chunker.py ×2, server_impl.py ×1) with `1p5k0`.
- [x] Regression tests + the AC-10 eval gate; v31 index rebuild.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- Shares `server_impl.py`/`chunker.py` only within this change.

## Affected Architecture Docs

`N/A` — retrieval-ranking + chunker-qname fix; no boundary/contract change. The graph lane (the contract surface) is unchanged.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The injection widening touches the AC-10-calibrated retrieval path — the no-regression eval is the gate. |
| AC-2 | required  | The nested-qname + dotted-suffix fix is the actual user-facing miss; the version bump must ship with it. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-14 | Patches (authored + unit-verified downstream on solaris) applied to this tree: injection gate widened to navigational (server_impl.py:1586), nested-type qualified descent (chunker.py:_walk_class_members), `code_constants` dotted-suffix matcher, graph-seed stoplist, `CHUNKER_VERSION` 30→31. Replaced `1p5xx` placeholder with `1p5k0`. | `server_impl.py`, `chunker.py` |
| 2026-06-14 | **Gate PASS:** rebuilt the index to v31 (13,917 doc / 10,184 code chunks) and ran `run_recall_eval.py` → **11/11, exit 0** — navigational symbol queries still rank #1 (no dilution from the injection widening), constants retrievable. Added regression tests; full suite green. | `run_recall_eval.py`, `test_chunker.py`, `test_server_tools.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-14 | Fix PRIMARY at the injection gate (widen to navigational), not the boost weight | The boost already lands declarations at #1 when they're candidates; the real miss is navigational queries getting no injection so the declaration never becomes a candidate. Bumping `DEFINITION_MATCH_BOOST` risks the AC-10 calibration for no gain. | Bump `DEFINITION_MATCH_BOOST` (rejected — wrong lever + regression risk); graph `reads`-hop (rejected — treats a symptom; the seed was the decoy, not a graph-hop gap) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Injecting declarations on navigational queries regresses recall | Gated by the AC-10 eval — ran post-patch, 11/11 pass, navigational queries still #1 |
| Nested-qname change collides with existing chunk ids | `CHUNKER_VERSION` 30→31 forces a clean re-chunk; negative test guards `code_constants` over-match |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
