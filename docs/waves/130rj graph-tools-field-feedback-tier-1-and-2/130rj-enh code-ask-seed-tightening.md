# `code_ask` — Tighten Seed Guidance Instead of Adding API Surface for a Misuse Case

Change ID: `130rj-enh code-ask-seed-tightening`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

The change was originally scoped (Aceiss v1 §2.6) to add a `fast_mode: bool` parameter to `code_ask` that would skip the cross-encoder reranker, giving callers a way to reduce latency on navigational questions. After review (Aceiss clarification 2026-05-31, this conversation): **fast_mode is the wrong fix**.

The evaluation finding wasn't "the reranker is too slow for navigational questions" — it was "`code_ask` is the wrong tool for navigational questions." For "where is X defined?" or "what calls X?", `code_definition` + `code_callhierarchy` return exact line numbers and call sites; `code_ask` returns synthesized prose that's *both slower and less precise*. The reranker latency is a symptom, not the root cause.

Adding `fast_mode` would:
1. Make a misuse pattern slightly cheaper (still slower than direct tools, still less precise),
2. Add API surface that agents and seeds need to learn,
3. Imply a "try `code_ask` first, bail if `rerank_ms > threshold`" pattern — which is exactly what burns the 30-second reranker pass unnecessarily.

Correct fix: don't start with `code_ask` for navigational questions. Period. The seeds already point in that direction; this change tightens the wording to remove the trailing hedge.

The companion observation Aceiss made — surfacing the timing breakdown so future evaluation reports can be written easily — is already covered: `code_ask`'s response carries `vector_ms` and `rerank_ms` at the top level (server_impl.py:11121-11122). No additional surface needed.

## Requirements

1. **Do NOT add a `fast_mode` parameter to `code_ask`.** Skip the planned API surface entirely.
2. **Tighten seed-180 and seed-211** to remove the "check `rerank_ms` and switch when high" hedge. The rule becomes: "Skip `code_ask` for navigational questions when the symbol or file is known. Use `code_definition` + `code_callhierarchy` instead — they are faster and more precise. Use `code_ask` only when synthesis across unknown files and layers is required."
3. **Confirm `rerank_ms` and `vector_ms` remain in the response** (already shipped; document in the seed as diagnostic-only, not as a runtime routing signal).
4. **No code changes.** This is a seed-text correction plus a confirmation of an already-present response field.

## Scope

**In scope:**

- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` — revise the `code_ask` latency footgun text to remove the "check rerank_ms and switch" hedge; the rule is "don't start with `code_ask` for navigational questions."
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — same revision on the `code_ask` "skip for navigational" guidance line.

**Out of scope:**

- Adding `fast_mode` or any `question_type` hint parameter to `code_ask` (rejected per the clarification above).
- Removing `rerank_ms` / `vector_ms` from the response (kept as diagnostic surface for evaluation reports).
- Any change to `code_ask`'s retrieval pipeline.

## Acceptance Criteria

- [x] AC-1: Seed-180 `code_ask` latency footgun text no longer contains the "check `rerank_ms` and switch" hedge. The rule reads as a directive against starting with `code_ask` for navigational questions, not as a fallback path.
- [x] AC-2: Seed-211 `code_ask` guidance line carries the same tightening.
- [x] AC-3: No code changes to `code_ask_response`. `rerank_ms` and `vector_ms` continue to appear in the response (verified by reading the existing tests / current implementation; no new tests required for unchanged behavior).
- [x] AC-4: `docs-lint` passes after the seed edits.

## Tasks

- [x] Open `seed_edit_allowed` gate
- [x] Revise seed-180 `code_ask` latency text per AC-1
- [x] Revise seed-211 `code_ask` guidance per AC-2
- [x] Run docs-lint
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The seed-180 correction that removes the misleading try-then-switch hedge |
| AC-2 | required | The seed-211 parallel correction |
| AC-3 | required | Confirms the existing diagnostic surface is sufficient — no API change needed |
| AC-4 | required | Standard hygiene |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Drop `fast_mode` API surface | Aceiss clarification: the latency is a signal, not the root problem. Adding `fast_mode` makes a misuse case slightly cheaper while preserving the misuse pattern. Correct fix is the seed guidance change | Ship `fast_mode` as originally scoped (rejected — adds API surface for the wrong reason; agents/seeds need to learn yet another parameter for a misuse case) |
| 2026-05-31 | Tighten seed language to remove "check rerank_ms" hedge | The hedge implies "try `code_ask` first; bail if slow" — exactly the pattern that burns the reranker cost. The right rule is "don't start with `code_ask` for navigational questions" | Keep the hedge as a safety net (rejected — implies a try-first pattern that defeats the point) |
| 2026-05-31 | Keep `rerank_ms` / `vector_ms` in the response | Useful for evaluation reports (Aceiss's measurement of 31,770 ms reranker vs 200 ms direct tools was possible because the timing was exposed). Document as diagnostic surface in the seed, not as a runtime routing signal | Drop the timing fields (rejected — they're useful for evaluation and don't cost anything at runtime) |
| 2026-05-31 | Change-doc reflects the revised scope rather than being withdrawn from the wave | Keeping the change doc preserves the audit trail of why the original `fast_mode` proposal was reconsidered. Withdrawing would lose the decision context | Withdraw the change from the wave and roll the seed edit into Change 1's doc (rejected — loses decision history) |

## Risks

| Risk | Mitigation |
|---|---|
| Agents already trained on the hedge pattern continue to start with `code_ask` and check `rerank_ms` | The seed revision is the only authoritative source; agents reading it forward get the directive form. Existing in-flight sessions either complete with the old wording or refresh on next read |
| The decision to drop `fast_mode` may need to be reconsidered if a different evaluation surfaces a legitimate use case for skipping the reranker on synthesis questions | The change doc captures the reasoning; revisiting is possible. The current evidence is unambiguous (navigational misuse, not synthesis-with-fast-mode-needed) |

## Related Work

- Companion to `130rj-enh seeds-pattern-library-and-recipes` (Change 1; already implemented). That change introduced the original "check `rerank_ms` and switch" hedge based on Aceiss v1 §2.6 / §4.6. This change tightens the wording per the Aceiss clarification.
- Same wave: `130rj-enh graph-tool-shape-consistency` (implemented), `130rj-enh generated-code-classifier-and-filters`, `130rj-enh aop-advice-empty-incoming-detection`, `130r7-bug java-method-reference-call-sites`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
