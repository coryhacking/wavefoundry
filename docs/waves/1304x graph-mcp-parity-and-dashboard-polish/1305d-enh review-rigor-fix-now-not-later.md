# Review Rigor: Fix-Now-Not-Later as Standing Practice

Change ID: `1305d-enh review-rigor-fix-now-not-later`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 1304x graph-mcp-parity-and-dashboard-polish

## Rationale

Wave `1304x` close-review surfaced four issues — A1 (a real bug in `code_graph_path`), missing per-tool refresh tests, an unaddressed AC-6 (diagnostic vocabulary), and an unaddressed AC-9 (architecture doc). The council moderator's synthesis defaulted to filing two of these as follow-on plans and accepting two as "honest AC partials." After operator pushback ("We're letting too many things go through review without recommending fixes"), all four were addressed in the same session — including the code-review observations that I'd flagged but not fixed (the `holder` dict trick, missing `Callable` type hint, broad `except Exception`).

The pattern is the standing problem: review seats find real issues, then the moderator (or the implementer) defers them to "follow-on plans" or "AC partials." Each deferred item is small. Across many waves, the cumulative effect is technical debt and inconsistent quality. The fix is to change the *default* behavior at the review seats themselves: when a review finds an issue that's small enough to fix in-session, the recommendation should be **fix it now**, not "file as follow-on." Follow-on planning is reserved for issues that genuinely exceed the wave's scope or require new design.

This change adds the "fix-now-not-later" principle to the review-related seed prompts so that future code-reviewer, architecture-reviewer, performance-reviewer, security-reviewer, and council-moderator runs apply this default automatically.

Source: operator request during wave `1304x` close-review, 2026-05-30.

## Requirements

1. The `code-reviewer` seed (`.wavefoundry/framework/seeds/221-code-reviewer.prompt.md`) must include guidance that small findings (type hints, naming, narrow vs broad exceptions, dead code, obvious refactors, missing tests for a structural transform that was extracted) should be recommended as **in-session fixes** rather than deferred to follow-on plans. The seed must define the threshold: any finding that can be fixed in fewer than ~20 lines of code without changing the change's contract should be fixed in the same session.
2. The `architecture-reviewer` seed must include similar guidance for architectural findings: helper boundary cleanups, signature consolidation, redundant indirection, missing type hints on public-ish helpers — fix in-session unless the fix would change a contract or require a new decision.
3. The `performance-reviewer` and `security-reviewer` seeds must include the same principle. Performance concerns that involve measurable but small overhead in already-touched code (extra hash lookups, unnecessary copies, missing short-circuits) should be fixed; large redesigns or architectural changes are still deferred. Security concerns that involve narrowing an exception scope, validating an input that's already in hand, or logging a side-effect should be fixed; new threat-model work is deferred.
4. The `council-review` seed (`.wavefoundry/framework/seeds/230-council-review.prompt.md`) must update the moderator's synthesis guidance: the default verdict format should distinguish "PASS WITH IN-SESSION FIXES" (apply now, then close) from "PASS WITH FOLLOW-ON" (file the plan, close, address later). The moderator must explicitly justify why each follow-on isn't fixable in-session, rather than the current default of filing.
5. The `guru` seed (`.wavefoundry/framework/seeds/211-guru.prompt.md`) should include a parallel principle when guru produces review-adjacent commentary: don't recommend deferral by default; recommend in-session fixes for small, contained issues.
6. The change must not alter review seats' independence — each seat still produces its own findings; the principle applies to *how findings are routed* after they're recorded, not to *which findings get recorded*.
7. The seed updates must be additive — existing review guidance is preserved.

## Scope

**Problem statement:** Review seats produce findings, and the default routing is to file them as follow-on plans or accept as AC partials. Each individual deferral is small; cumulative technical debt is significant. The seed prompts don't currently bias toward in-session fixes for small issues.

**In scope:**

- `.wavefoundry/framework/seeds/221-code-reviewer.prompt.md` — add a "Fix-Now Threshold" section
- `.wavefoundry/framework/seeds/214-architecture-reviewer.prompt.md` — add the same section adapted for architectural concerns
- `.wavefoundry/framework/seeds/212-performance-reviewer.prompt.md` — add the principle scoped to perf
- `.wavefoundry/framework/seeds/213-security-reviewer.prompt.md` — add the principle scoped to security
- `.wavefoundry/framework/seeds/230-council-review.prompt.md` — update the moderator synthesis guidance to require explicit justification for each follow-on
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — add a parallel principle to the guru's review-adjacent commentary
- Memory promotion — save the principle to user memory so it persists across sessions

**Out of scope:**

- Changing the qa-reviewer or docs-contract-reviewer seeds — these seats already focus on coverage gaps and contract issues, not deferral patterns
- Adding new review seats
- Changing the wave lifecycle (Prepare, Implement, Close) flow
- Changing how AC priority is recorded — that surface is for scope, not for fix-now-vs-defer
- Changing review-evidence diagnostic emission in `server_impl.py` — the seed updates are operator-facing prompt guidance, not server contract

## Acceptance Criteria

- [x] AC-1: The five review seeds (`code-reviewer`, `architecture-reviewer`, `performance-reviewer`, `security-reviewer`, `council-review`) each contain a `## Fix-Now Threshold` (or `## Moderator Synthesis: Fix-Now-or-Justify`) section articulating the ~20-LOC-and-no-contract-change threshold with concrete examples per lane.
- [x] AC-2: The council-review seed's Moderator Synthesis section requires every follow-on recommendation to carry a one-line justification and explicitly names the unacceptable justifications ("small but worth doing later", "honest AC partial") that should be routed back to the lane for in-session fix.
- [x] AC-3: The guru seed has a parallel principle added to its Tool Selection Quick Rules.
- [x] AC-4: User memory entry `feedback_fix_now_not_later.md` saved and indexed in `MEMORY.md`.
- [x] AC-5: All five framework-seed edits done under `seed_edit_allowed`; guru seed edit done in the same gate window.
- [x] AC-6: `docs-lint` passes — seed edits are markdown additions only, no metadata schema changes.

## Tasks

- [ ] Open `seed_edit_allowed` gate
- [ ] Update `221-code-reviewer.prompt.md` with the Fix-Now Threshold section
- [ ] Update `214-architecture-reviewer.prompt.md` with the same principle adapted for architectural findings
- [ ] Update `212-performance-reviewer.prompt.md` with the perf-scoped version
- [ ] Update `213-security-reviewer.prompt.md` with the security-scoped version
- [ ] Update `230-council-review.prompt.md` moderator synthesis guidance
- [ ] Update `211-guru.prompt.md` with parallel principle for review-adjacent commentary
- [ ] Close gate
- [ ] Save user-memory entry documenting the principle
- [ ] Run `docs-lint`; confirm clean
- [ ] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The five review seeds are where the principle takes effect |
| AC-2 | required | The moderator synthesis is the choke point where follow-ons get filed; explicit justification stops the silent-defer pattern |
| AC-3 | important | Guru's review-adjacent commentary is high-frequency; same principle applies |
| AC-4 | important | Memory entry survives across sessions so the principle persists |
| AC-5 | required | Gate hygiene |
| AC-6 | required | Lint hygiene |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Encode the principle as seed prompt guidance, not as a lifecycle gate | Lifecycle gates already exist for scope (stage gate, AC priority); the issue is operator-facing review behavior, which is shaped by the review seat seeds | Add a lifecycle gate that blocks close when any review finding is filed as follow-on (rejected — too strict; some follow-ons genuinely exceed scope) |
| 2026-05-30 | ~20 LOC threshold for "in-session" | Empirical estimate: most of the wave `1304x` close-review findings were under 20 LOC each. A precise threshold gives reviewers a defensible default | Time-based threshold ("under 10 min") — rejected because reviewers don't time themselves; LOC is observable. No threshold ("use judgment") — rejected because that's the current default and it produces the deferral problem |
| 2026-05-30 | Update guru seed too | Guru produces frequent review-adjacent commentary in code-question flows; the principle should apply there too | Limit to formal review seats — rejected because guru's commentary often anchors the agent's mental model of "is this issue worth fixing" |

## Risks

| Risk | Mitigation |
|---|---|
| Reviewers fix too many things in-session and waves become unboundedly long | The ~20-LOC threshold caps the fix size per-finding; council moderator can still defer larger ones with justification |
| Operator overrides aren't honored if a finding gets fixed in-session without their input | Operator-driven scope changes still take precedence; the principle is the *default*, not a forced behavior |
| Seed bloat as principles accumulate | The section is short (≤10 lines per seed); existing guidance is preserved |

## Related Work

- This change directly addresses the close-review-of-wave-`1304x` pattern where four findings were initially routed to follow-on plans before operator pushback redirected to in-session fixes.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
