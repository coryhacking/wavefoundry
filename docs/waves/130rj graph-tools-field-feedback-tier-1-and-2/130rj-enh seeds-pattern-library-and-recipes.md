# Seeds — Question-Type Pattern Library + Reviewer Recipes + AOP/Latency Footguns

Change ID: `130rj-enh seeds-pattern-library-and-recipes`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Both Solaris and Aceiss field reports converge on a single observation: the seeds describe each graph tool in isolation but never teach the chains that answer agent question types. The big wins from the tools come from sequencing 2–4 calls that triangulate — different orderings answer different question shapes. Solaris's bug investigation used `code_callhierarchy → code_impact → code_keyword` to enumerate every change site in 500ms; agents who don't know that chain re-invent it every session.

Same gap on the reviewer side. Code-reviewer / architecture-reviewer / security-reviewer prompts currently teach what to look for, not how to use the graph to inform the fix-now-vs-follow-on decision. Solaris proposed: code-reviewer counts incoming + community span; architecture-reviewer escalates on cross-community findings; security-reviewer sizes production attack surface via `include_tests=false`.

Plus two specific footguns surfaced repeatedly:

- **AOP/advice empty-incoming on Java** (Aceiss §2.3, §4.2): when a method has `@Advice.OnMethodEnter` / `@Around` / `@Before` / `@After`, `code_callhierarchy` returns empty incoming and `code_references` *also* returns nothing useful — the callers are wired at weave time by ByteBuddy/AspectJ, not Java code. The current seed-180/211 fallback rule ("if `code_callhierarchy` empty for Java, use `code_references`") is actively misleading for advice methods.
- **`code_ask` latency** (Aceiss §2.6, §4.6): Aceiss measured 31,770ms of 33,712ms (94%) in the cross-encoder reranker for a navigational question that `code_definition` + `code_callhierarchy` answered in <200ms. Seeds don't tell agents when to skip `code_ask`.

## Requirements

1. Seeds 180/211 carry a **question-type pattern library** with the seven patterns from Solaris's report, each as a 4–6-line tool chain plus a one-sentence "when to use" framing.
2. Seeds 180/211 carry an **anti-patterns** section listing the seven agent-facing footguns from Solaris §7 v2 plus the Aceiss-surfaced `code_ask` latency footgun. Footgun count is 7 (not 8) because the v2 report withdrew the `external_*_count` anti-pattern from the agent-facing list and reclassified it as a framework-maintainer signal — that lands in seed-160 instead (requirement 7 below).
3. Seeds 180/211 carry the **AOP/advice exception** to the "fall back to `code_references`" rule (Aceiss §4.2): for Java methods annotated with `@Advice.OnMethodEnter`/`@Advice.OnMethodExit`/`@Around`/`@Before`/`@After`/`@AfterReturning`/`@AfterThrowing`, the correct fallback is `code_keyword(<advice_class_name>)` scoped to instrumentation/aspect files — the registration is the caller.
4. Seeds 213 (security-reviewer), 214 (architecture-reviewer), 221 (code-reviewer) carry **reviewer-side graph recipes** that inform fix-now-vs-follow-on per `1305d`: code-reviewer uses `code_callhierarchy.incoming` count + community uniformity; architecture-reviewer uses `code_impact` cross-community span; security-reviewer uses `code_impact(include_tests=false)` to size production attack surface.
5. The seed text describes patterns at a "shape" level (which tool, what argument, what to look for) rather than at the API level (parameter names, response field names) — the seeds reference existing per-tool documentation rather than duplicating it.
6. The seed updates use AST-precise language about tool semantics: `code_callhierarchy.incoming` is per-caller-function not per-call-site; `code_graph_path` traverses `defines` edges; `code_callhierarchy.outgoing` mixes function calls with init/constructor calls; etc. These match the existing tool docstrings.
7. **Seed-160 (upgrade-wavefoundry) carries a framework-maintainer note** that `external_outgoing_count` / `external_incoming_count` deltas between framework versions are a regression signal for extractor fixes (Solaris's 47 → 3 drop after 30qh diagnosed the Swift fix landing). This is a maintainer-side QA signal, not an agent prompt — moved here from the agent-facing seeds per Solaris v2.
8. **`docs/workflow-config.json` schema gains a `code_navigation_hints` field** carrying `guard_tokens` and `early_exit_tokens` lists (matches the existing `code_review_triggers`/`architecture_triggers`/`security_triggers` schema pattern). The seed-180/211 edge-case pattern references this config field rather than hardcoding tokens, so project conventions tune without seed rerenders. The config field is opt-in: empty/absent → patterns describe the general shape with no concrete tokens.
9. **Render-platform-surfaces gains a `code_navigation_hints` passthrough** so the field reaches downstream agent contexts. (Investigate scope at implementation time — may be no-op if the config is already consumed directly by tools.)

## Scope

**In scope:**

- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` — add Pattern Library section (after the existing MCP-first exploration list) + add Anti-Patterns to existing tool notes + add AOP advice exception to the fallback rule + add `code_ask` latency note.
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — same additions, plus the Question-Type Recipes block in the Tool Selection Quick Rules section. Edge-case pattern (Pattern 5) references `workflow-config.json.code_navigation_hints.guard_tokens` rather than hardcoded language tokens.
- `.wavefoundry/framework/seeds/213-security-reviewer.prompt.md` — reviewer-side graph recipe for sizing production attack surface.
- `.wavefoundry/framework/seeds/214-architecture-reviewer.prompt.md` — reviewer-side graph recipe for cross-community escalation.
- `.wavefoundry/framework/seeds/221-code-reviewer.prompt.md` — reviewer-side graph recipe for the fix-now-threshold decision.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` — one-line maintainer note that `external_*_count` deltas across pack versions are a regression signal for extractor fixes (Solaris v2 reclassification).
- This repo's `docs/workflow-config.json` schema (or its template if `seed_edit_allowed`/framework-side touch is needed) — declare the `code_navigation_hints` field shape with example tokens.

**Out of scope:**

- A new dedicated `docs/agents/code-graph-patterns.md` document (Solaris suggested it but the seeds themselves are the right vector for in-session pattern discoverability; a separate doc adds an extra hop).
- Adding new tool surfaces (`code_advice_sites` etc. are Tier 3 follow-up waves).
- Enforcing or validating `code_navigation_hints` field shape via docs-lint (out of scope here; the schema declaration is documentation-only).

## Acceptance Criteria

- [x] AC-1: Seed 180 carries a "Investigation patterns (when to chain tools)" subsection with at least 4 named patterns (bug investigation; refactor; analogue-first; impact analysis with `include_tests=true/false` diff).
- [x] AC-2: Seed 211 carries a "Question-type recipes" subsection with at least 5 named recipes mapped to question shapes (`"If I change X, what breaks?"`, `"What edge cases does X handle?"`, `"Where do we handle X?"`, `"Is module A coupled to module B?"`, `"Where does this advice/AOP method actually get called?"`).
- [x] AC-3: Both seeds 180 and 211 carry the AOP advice exception (Java methods with `@Advice.OnMethodEnter`/`@Advice.OnMethodExit`/`@Around`/`@Before`/`@After` annotations: do NOT fall back to `code_references`; search for `TypeInstrumentation.transform()` / `@Aspect` registration).
- [x] AC-4: Both seeds 180 and 211 carry the `code_ask` latency footgun (skip for navigational questions; check `rerank_ms` field; switch to direct tools when >5000ms).
- [x] AC-5: Both seeds 180 and 211 carry an Anti-Patterns section documenting the seven agent-facing footguns (callhierarchy.outgoing mixes constructors, callhierarchy.incoming is per-caller-function, graph_path traverses defines, callgraph depth>1 on chokepoints, code_impact path= Python/JS/Go/Rust only, empty graph signals extractor incompleteness, code_keyword without glob is noisy) plus the `code_ask` reranker-latency footgun. `external_*_count` is NOT in the agent-facing anti-patterns list (moved to seed-160 per AC-11).
- [x] AC-6: Seed 221 (code-reviewer) carries a "Reviewer-side graph queries" subsection with the code-reviewer recipe (count `code_callhierarchy.incoming`; if small AND same-community AND <20 LOC change, fix-now per `1305d`).
- [x] AC-7: Seed 214 (architecture-reviewer) carries the architecture-reviewer recipe (read `community:` across `code_impact` results; findings spanning multiple communities are cross-cutting → surface to council).
- [x] AC-8: Seed 213 (security-reviewer) carries the security-reviewer recipe (`code_impact(include_tests=false)` to size production attack surface; `code_callhierarchy.incoming` on each affected node for trust-boundary crossings).
- [x] AC-9: `docs-lint` passes after the seed edits.
- [x] AC-10: No existing seed instructions removed or altered beyond the explicit AC additions.
- [x] AC-11: Seed-160 (upgrade-wavefoundry) carries a one-line framework-maintainer note: `external_outgoing_count` / `external_incoming_count` deltas across pack versions are a regression signal for extractor fixes; a sudden drop after a graph-extractor upgrade is diagnostic of the fix landing (Solaris v2 reclassification). The note is scoped to maintainer-side QA, not agent in-session decision-making.
- [x] AC-12: `docs/workflow-config.json` (this repo's config) gains a `code_navigation_hints` field with `guard_tokens` and `early_exit_tokens` lists. The example values document the field shape; project owners tune to local convention. Seed 211 references this field rather than hardcoding language-specific tokens.

## Tasks

- [x] Open `seed_edit_allowed` gate
- [x] Update seed-180 with the four required additions (patterns, anti-patterns, AOP, code_ask)
- [x] Update seed-211 with the five required additions (recipes, anti-patterns, AOP, code_ask, patterns reference) — pattern 5 (edge case) references `workflow-config.json.code_navigation_hints.guard_tokens`
- [x] Update seeds 213/214/221 with reviewer-side graph recipes
- [x] Update seed-160 with the one-line maintainer note about `external_*_count` deltas as extractor-regression signal
- [x] Update this repo's `docs/workflow-config.json` with the `code_navigation_hints` field shape (example values; project owners tune)
- [x] Run docs-lint
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The pattern library headline value (seed-180 side) — both reports converged on this |
| AC-2 | required | The pattern library headline value (seed-211 side) — recipes mapped to question shapes |
| AC-3 | required | AOP exception fix to the existing misleading fallback rule |
| AC-4 | required | `code_ask` latency footgun avoidance |
| AC-5 | required | Anti-patterns concentrate the actionable footguns into one section |
| AC-6 | required | Code-reviewer recipe — incoming count + community uniformity as fix-now signal |
| AC-7 | required | Architecture-reviewer recipe — cross-community span as escalation signal |
| AC-8 | required | Security-reviewer recipe — production attack-surface sizing via `include_tests=false` |
| AC-9 | required | Standard hygiene (docs-lint) |
| AC-10 | required | Standard hygiene (no existing instructions removed) |
| AC-11 | required | Seed-160 maintainer note (external_*_count as extractor-regression signal, not agent prompt — Solaris v2 reclassification) |
| AC-12 | required | workflow-config.json `code_navigation_hints` field shape — project-tunable token lists matching existing trigger-list schema pattern |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Land patterns in existing seeds (180/211/213/214/221), not a new `code-graph-patterns.md` | In-session discoverability is highest when patterns live next to the existing tool docs the agent already reads; a separate doc adds an extra hop and operators may not navigate to it | New dedicated `docs/agents/code-graph-patterns.md` (rejected — Solaris's "stays compact" framing is appealing but in practice the seed is what agents read; out-of-band docs get skipped) |
| 2026-05-31 | Describe patterns at the "shape" level (tool name + arg semantics) rather than at the API level | Tool API details already live in the per-tool docstrings; duplicating creates a future maintenance footgun when tools evolve | Inline full API specs (rejected — duplication; tool docstrings are the source of truth) |
| 2026-05-31 | Treat AOP fallback exception as a seed correction, not a tool change in this change | The behavior fix (Aceiss §2.3 — return `caller_pattern: "advice"` from `code_callhierarchy`) is change `130rj-enh aop-advice-empty-incoming-detection`. The seed correction is independent and ships even if the tool change misses scope | Combine both into one change (rejected — different change vectors: one is doc edit under seed_edit_allowed, the other is server_impl + tree-sitter under framework_edit_allowed) |
| 2026-05-31 | Reviewer recipes use existing `1305d` fix-now-not-later doctrine as the anchor | Already canonical via feedback memory; reviewers know it; binding graph queries to that decision tightens the existing workflow without inventing a new framing | New "graph-aware review" framing (rejected — over-engineering; the existing doctrine just needs the new signals) |

## Risks

| Risk | Mitigation |
|---|---|
| Seeds grow too long and become harder to read; pattern library could bloat | Each pattern is 4–6 lines max; anti-patterns are bullet-list one-liners; reviewer recipes are 2–3 lines each. Total additions ~80–100 lines distributed across 5 seeds |
| AOP advice exception is Java-specific and might confuse agents working on non-Java projects | Phrased as "if Java AND advice annotation present, ..."; rule is opt-in by pattern match. Non-Java projects ignore it because the precondition is false |
| `code_ask` latency note could be read as "always skip code_ask"; correct framing is "skip for navigational, use for synthesis" | Explicit "when to use vs when NOT to use" framing; cite the `rerank_ms` measurement so agents have an objective threshold |
| Reviewer recipes could conflict with existing reviewer guidance | Add as a NEW subsection ("Reviewer-side graph queries") clearly scoped to the fix-now-threshold decision; doesn't override any existing checklist |

## Related Work

- Wave 130et / 130ol / 130qf shipped the graph extractor foundation. This change closes the loop on operator-facing usage guidance.
- Companion to `130rj-enh graph-tool-shape-consistency` (tool-side correctness for community label/ID, pagination, hop attribution), `130rj-enh code-ask-fast-mode` (the API-side latency fix the seeds reference), `130rj-enh aop-advice-empty-incoming-detection` (the API-side AOP detection the seeds reference), `130rj-enh generated-code-classifier-and-filters` (the generated-code filter mentioned in anti-patterns).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
