# Intent-Based Auto-Guru Routing With Examples and Retrieval Backstop

Change ID: `1p3hf-enh intent-based-auto-guru-routing`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-05
Wave: `1p3dk framework-drift-convergence`

## Rationale

Field observation (2026-06-05): a user asked *"tell me about the way authentication works"* — a textbook codebase-investigation question that should have routed to Guru automatically. It did not. The lead agent answered directly without consulting Guru, missing the routing trigger entirely.

Investigation of `seed-050` (lines 128-141, the markdown block that gets seeded into `AGENTS.md`) shows the trigger prose is already framed as intent-based, not pattern-matching:

> *"When a message is primarily about **understanding, locating, or explaining** source code or project docs ... adopt the Guru workflow."*

So the rule is right; it's just easy for the lead agent to skip the classification step on any given message. The intent check is abstract; the lead agent has many other things competing for its attention; the routing miss happens silently.

The fix shape is **make the trigger harder to skip**, in three complementary ways:

1. **Pre-flight question** — convert the abstract intent check into a literal question the agent asks itself before responding: *"Does answering this require reading code to understand what's there?"* A yes-or-no pre-flight is harder to skip than an attribute classification.
2. **Positive/negative examples table** — surface forms vary infinitely; the boundary is finite and demonstrable. An examples table with both routes-to-Guru and does-not-route cases (including the *exact* failure-mode example from this report) anchors the rule in recognizable cases. Future agents reading `AGENTS.md` see "tell me about the way X works" → Guru explicitly.
3. **Retrieval-intent backstop** — if the agent is about to call `code_search` / `code_keyword` / `code_read` / `code_definition` / any retrieval tool in service of a user question, that retrieval IS the agent of a Guru call. The tool reach-for becomes the late-detect signal. If the pre-flight missed, the retrieval-reach catches it.

This is a seed-prose-only change (no code, no schema, no MCP tool change). The seeded `AGENTS.md` template grows by ~30 lines; `seed-211` (Guru role doc) gains a mirror "When agents should route to me" section for symmetry; `render_agent_surfaces.py` flows the changes through automatically to tier-2 marker blocks on `CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, etc.

Out of scope: keyword-trigger lists, hardcoded phrase patterns, regex-based intent classifiers in code. The diagnosis is that lead-agent attention is the scarce resource; better prose with stronger anchors is the fix, not more rules to mechanically match.

## Requirements

1. **Pre-flight question added to seed-050's auto-Guru section.** Insert a literal pre-response check: *"Before responding to any user message, ask yourself: does answering this require reading code or documentation to understand what's there? If yes, route to Guru."* Positioned at the top of the routing block so it's the first thing the lead agent reads.
2. **Positive/negative examples table added.** A markdown table with at minimum 8 example user questions covering: explicit how/where/what questions (positive), the failure-mode example "tell me about the way authentication works" (positive — explicitly named), descriptive phrasings ("walk me through", "I want to understand"), code-location questions ("where is X defined"), and operational questions that should NOT route (rename, delete, change config).
3. **Retrieval-intent backstop rule added.** A literal rule in seed-050's auto-Guru section: *"If you find yourself about to call `code_search`, `code_keyword`, `code_read`, `code_definition`, `code_outline`, `code_callhierarchy`, `code_references`, or `code_pattern` in service of a user question — stop. That retrieval is Guru's job. Route to Guru instead of doing the retrieval yourself."*
4. **The exact failure-mode example must be present.** *"tell me about the way authentication works"* appears verbatim in the examples table as a positive case, labeled with the reason ("semantic intent = how does it work; surface form doesn't match keyword patterns").
5. **seed-211 (Guru role doc) gains a mirror "When agents should route to me" section.** Symmetric to seed-050's table — same examples, same reasons, but framed from Guru's perspective ("these are the questions I should receive"). Two surfaces reinforcing the same boundary from different sides.
6. **render_agent_surfaces.py flows the changes.** After seed edits land, running `render_platform_surfaces.py` (which calls `render_agent_surfaces.py`) propagates the updated template into tier-2 marker blocks on `CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `WARP.md`, `.github/copilot-instructions.md`. Tier-3 native surfaces (`.cursor/rules/auto-guru.mdc`, `.claude/agents/guru.md`, `.codex/skills/auto-guru/SKILL.md`) also pick up the new content.
7. **Test guards the failure-mode example.** A test in `test_render_platform_surfaces.py` (or `test_dashboard_server.py` if it tests rendered AGENTS.md content) asserts that the literal string `tell me about the way authentication works` is present in the rendered AGENTS.md / tier-2 marker blocks. This is a regression guard so future renders or seed edits don't accidentally drop the explicit failure-mode anchor.
8. **No keyword-trigger list.** The change intentionally does NOT add a list of trigger phrases ("how does", "where is", "what does", etc.). The fix is intent-based plus example-anchored plus retrieval-backstop. Adding a keyword list would re-introduce the whack-a-mole pattern this change is removing.
9. **CHANGELOG bullet describes the routing-strength improvements.**

## Scope

**Problem statement:** Auto-Guru routing relies on the lead agent applying an abstract intent check ("is this about understanding code?") to every user message. The check is easy to skip; the routing miss happens silently. A real user question "tell me about the way authentication works" failed to route this session despite being a textbook Guru question.

**In scope:**

- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md` — auto-Guru section gets pre-flight question, examples table (with the failure-mode example), retrieval-intent backstop rule
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — mirror "When agents should route to me" section
- `.wavefoundry/framework/scripts/render_agent_surfaces.py` — verify the new template content flows through to tier-2 / tier-3 generated surfaces; minor template updates if any
- This self-host's `AGENTS.md` — re-rendered after seed edits land; sees the new content
- This self-host's tier-2 marker blocks (`CLAUDE.md`, `.cursor/rules/project-context.mdc`, etc.) — re-rendered
- Test in `test_render_platform_surfaces.py` (or equivalent) guarding the failure-mode example
- CHANGELOG bullet

**Out of scope:**

- Adding a keyword-trigger list (explicitly rejected — whack-a-mole pattern)
- Code-level intent classification (a Python regex / NLP classifier in `server_impl.py`) — the routing decision is the lead agent's, not the MCP server's
- Changes to other agent role docs (architecture-reviewer, code-reviewer, etc.) — they have their own routing surfaces; out of scope for this change
- Changes to the user-facing documentation that explains the shortcut phrase **Guru** — operators can still explicitly invoke; this change only affects auto-routing when they don't

## Acceptance Criteria

- [x] AC-1: `seed-050` auto-Guru section opens with a literal pre-flight question: *"Before responding to any user message, ask yourself: does answering this require reading code or documentation to understand what's there? If yes, route to Guru."*
- [x] AC-2: `seed-050` auto-Guru section includes a positive/negative examples table with at least 8 rows. At least 5 are "route to Guru" cases; at least 3 are "do not route" operational cases.
- [x] AC-3: The exact string `tell me about the way authentication works` appears in the examples table, marked as a positive case with the reason "semantic intent = how does it work; surface form doesn't match keyword patterns" (or equivalent prose).
- [x] AC-4: `seed-050` auto-Guru section includes the retrieval-intent backstop rule naming at minimum the tools: `code_search`, `code_keyword`, `code_read`, `code_definition`, `code_outline`, `code_callhierarchy`, `code_references`, `code_pattern`.
- [x] AC-5: `seed-211` (Guru role doc) gains a "When agents should route to me" or equivalent section with the same examples table (or a reference to seed-050's table).
- [x] AC-6: After running `render_platform_surfaces.py`, the rendered `AGENTS.md` in this self-host contains all three additions: pre-flight question, examples table including the failure-mode example, retrieval-intent backstop rule.
- [x] AC-7: After running `render_platform_surfaces.py`, the tier-2 marker block in `CLAUDE.md` between `<!-- waveframework:auto-guru begin -->` and `<!-- end -->` contains either the full new template or a compact reference to it (whichever `render_agent_surfaces.py` was already designed to do — preserve the existing tier-1/tier-2 split).
- [x] AC-8: A test in `test_render_platform_surfaces.py` (or equivalent test file that covers rendered AGENTS.md content) asserts the literal string `tell me about the way authentication works` is present in the rendered output. The test fails if a future render or seed edit drops the failure-mode anchor.
- [x] AC-9: No keyword-trigger list (literal enumeration of phrases like "how does", "where is", "what does") is added. Verified by inspection of the change diff.
- [x] AC-10: CHANGELOG bullet under `## [1.5.0]` describes the routing improvements.
- [x] AC-11: Full framework test suite passes (additional ~1-3 tests).
- [x] AC-12: docs-lint clean.

## Tasks

- [x] Open `seed_edit_allowed` gate
- [x] Edit `seed-050` auto-Guru section: add pre-flight question, examples table, retrieval backstop rule
- [x] Edit `seed-211` Guru role doc: add mirror "When agents should route to me" section
- [x] Verify `render_agent_surfaces.py` template content reflects the new seed-050 prose; update if the renderer has hardcoded template content separately
- [x] Run `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` to propagate to tier-2 / tier-3 surfaces in this self-host
- [x] Add the regression test guarding the failure-mode example
- [x] Update CHANGELOG bullet
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close `seed_edit_allowed` gate

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seed-050-edit | implementer | — | Pre-flight question + examples table + retrieval backstop |
| seed-211-mirror | implementer | seed-050-edit | Symmetric section in Guru role doc |
| renderer-audit | implementer | seed-050-edit | Verify `render_agent_surfaces.py` flows the new content; minor updates if needed |
| self-host-render | implementer | renderer-audit | Run render_platform_surfaces.py to propagate locally |
| test | qa-reviewer | self-host-render | Failure-mode-example regression guard |
| docs | docs-contract-reviewer | seed-050-edit | CHANGELOG bullet |

## Serialization Points

- All edits are seed-prose + rendered-doc-content. Single seed_edit_allowed gate covers them. No cross-cutting file conflicts.
- Sequence: seed-050 → seed-211 → renderer audit → self-host render → test → CHANGELOG.

## Affected Architecture Docs

`N/A` — pure seed-prose and rendered-output change; no architectural boundary or data-flow change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Pre-flight question is the load-bearing "harder to skip" mechanism. |
| AC-2 | required | Examples table is the boundary-anchoring mechanism. |
| AC-3 | required | The exact failure-mode example is the most important single anchor in the table. |
| AC-4 | required | Retrieval-intent backstop catches misses the pre-flight skipped. |
| AC-5 | required | Symmetry across seed-050 and seed-211; reinforces the same boundary from both sides. |
| AC-6 | required | Rendered AGENTS.md is the lead-agent-facing surface; must reflect the change. |
| AC-7 | required | Tier-2 marker blocks must inherit the new template content. |
| AC-8 | required | Regression guard against future renders dropping the anchor. |
| AC-9 | required | Architectural discipline — no keyword-trigger list. |
| AC-10 | required | CHANGELOG. |
| AC-11 | required | Suite must pass. |
| AC-12 | required | docs-lint must pass. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-05 | Change scaffolded after field observation: user asked "tell me about the way authentication works" and routing missed. | This doc |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-05 | Intent-based pre-flight + examples + retrieval backstop, NOT a keyword-trigger list | Surface forms vary infinitely; pattern-matching is whack-a-mole. The current seed prose is already intent-based; the failure mode was skip-the-classification, not wrong-pattern. Fix is to make the check harder to skip (pre-flight question, anchored examples, late-detect backstop). | Add a keyword-trigger list ("how does X work", "where is X", "what does X do", ...) — rejected explicitly; re-introduces the whack-a-mole pattern that just demonstrably failed. |
| 2026-06-05 | The exact failure-mode example *"tell me about the way authentication works"* appears verbatim in the examples table | Future agents reading AGENTS.md see the exact case that demonstrably missed. The anchor is concrete and recognizable. AC-3 and AC-8 (regression test) protect this specific anchor. | Use a paraphrase — rejected; loses the anchor's specificity. Add many close paraphrases — rejected; bloats the table without proportional value. |
| 2026-06-05 | Mirror the examples table in seed-211 (Guru role doc) rather than only seed-050 | Two surfaces reinforce the same boundary from different sides. The lead agent reads AGENTS.md (rendered from seed-050) before answering a question; an agent invoked AS Guru reads guru.md (rendered from seed-211) when handling the question. Same boundary, two angles. | Only edit seed-050 — rejected; misses the symmetric reinforcement. Use a shared file with cross-references — rejected; adds an indirection layer for marginal benefit. |
| 2026-06-05 | Regression test guards the literal string `tell me about the way authentication works` in rendered AGENTS.md | The specific anchor must survive future renders and seed edits. A literal-string assertion is brittle but appropriate: this is the one anchor whose accidental removal would re-introduce the failure mode. | Test only the structural presence of an examples table — rejected; allows future edits to silently drop the load-bearing failure-mode case. |
| 2026-06-05 | No code-level intent classifier in server_impl.py | The routing decision belongs to the lead agent (the LLM), not the MCP server. The MCP server's tools (code_ask, docs_search) ARE the routing target, not the router. Adding routing logic to the server would muddle the layering. | Add a server-side classifier — rejected; wrong layer. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The lead agent still skips the pre-flight question (the same failure mode this change targets) | Three layers of defense: (1) pre-flight as the FIRST thing in the section so it's read first; (2) examples table with the exact failure-mode example so the agent recognizes the case visually; (3) retrieval-intent backstop catches misses the pre-flight skipped. Triple-layer reduces miss rate substantially even if no single layer is bulletproof. |
| Adding length to the auto-Guru section makes AGENTS.md longer and risks competing with other tier-1 content | The current section is ~10 lines; this change adds ~30 lines (pre-flight + table + backstop). AGENTS.md target length is ≤ 320 lines per seed-050 hygiene rule; the auto-Guru section grows but stays within budget. If length becomes an issue, the examples table could move to a linked supplementary doc; defer that decision until field observation shows length impact. |
| The examples table becomes a hidden enumeration that agents pattern-match against (re-introducing the very behavior we're avoiding) | The table is labeled explicitly as anchoring examples for an intent rule, not as the rule itself. The pre-flight question and retrieval backstop both reference intent and behavior, not the table. If field observation shows agents pattern-matching the table, the framing in seed-050 can be tightened. |
| Re-render of tier-2 marker blocks could pick up the new content in unexpected ways across hosts (CLAUDE.md vs Cursor vs Junie) | `render_agent_surfaces.py` already handles tier-1/tier-2 split via marker regions. AC-7 explicitly preserves the existing split (full template or compact reference, whichever the renderer was designed to do). No host-specific divergence is introduced. |
| Future seed edits drop the failure-mode example anchor accidentally | AC-8 regression test asserts the literal string is present. Any edit that removes it fails the test. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state. Change doc scaffolded 2026-06-05 in response to operator observation that a user question *"tell me about the way authentication works"* failed to auto-route to Guru. Operator directed scope as option B (admit as new change in wave `1p3dk`).
