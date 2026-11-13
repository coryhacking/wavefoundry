# Permit Direct Retrieval And Trim Dated Instructions

Change ID: `237eg-enh permit-direct-retrieval-and-trim-dated-instructions`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-12
Wave: `237ef instruction-file-audit-follow-ups`

## Rationale

A `/doctor prompt-audit` of the Claude Code instruction files (2026-11-12, target model Claude Opus 5.5) found guidance that current models follow too literally, plus stale wording. The operator objected to the retrieval-intent backstop in particular: it tells an agent to **stop** before any `code_*` call made for a user question and to route to Guru instead. An agent should be able to call `code_search` whenever it wants; the useful question is whether the question needs the Guru workflow. The same text ships to every project through seeds 050 and 211, so a local edit alone would leave every other project with the forbidding rule.

The audit's other findings in scope here:
1. Implementation principle 1, "ask before writing a single line", is an absolute that makes agents ask questions the request, code or docs already answer.
2. The `wf-upgrade` skill tells operators to hand-edit and delete `.wavefoundry/guard-overrides.json`, while the root instructions use `wf_open_gate` and `wf_close_gate`.
3. The `wf-upgrade` skill and the Guru subagent still name journals, which are retired in favour of memory records.
4. `AGENTS.md` carries a sentence about a past migration (stale-cleaned files that no longer exist) and wave or change IDs on 4 lines (three rule headings and the skills paragraph). Seed 050 carries more in prompt text that ships to every project; Requirement 6 states the rule that derives the set, so no count is load-bearing. The IDs were added as pointers to the wave that introduced each rule; a reading agent cannot act on them, and the history already lives in git and `docs/waves/`.

The audit's `CLAUDE.md` finding (two conflicting startup lists) was fixed outside this wave as an instruction-file edit: `CLAUDE.md` now holds only its two renderer-generated regions. That edit and its companion `AGENTS.md` gate paragraph are uncommitted working-tree changes; this change does not depend on them.

Audit finding coverage:

| Audit finding | Disposition |
| --- | --- |
| H1: `CLAUDE.md` and `AGENTS.md` startup lists conflict | Fixed before this wave (`CLAUDE.md` reduced to generated regions; its gate rule moved into `AGENTS.md`) |
| M1: retrieval backstop forbids direct `code_*` calls | Requirements 1, 2 and 7; AC-1, AC-4 |
| M2: "ask before writing a single line" | Requirements 3 and 7; AC-2, AC-4 |
| M3: stale-cleaned-files sentence in `AGENTS.md` | Requirement 6; AC-5 |
| M4: wave IDs in `AGENTS.md` (extended to seed 050 by operator direction) | Requirement 6; AC-5 |
| F1: `AGENTS.md` tool list shadows the registered tools | Change `237eh-enh tool-spec-as-the-enforced-tool-inventory` in this wave: the spec becomes the complete, enforced tool reference and `AGENTS.md` points to it |
| F2: `wf-upgrade` skill hand-edits the gate file | Requirement 4; AC-3 |
| F3: retired journal wording in the Guru subagent and `wf-upgrade` skill | Requirement 5; AC-3 |

## Product Intent

Agents in every Wavefoundry project may call `code_*` retrieval tools directly. Instead of being told to stop, they are asked to decide whether a question needs the Guru workflow. They ask the operator only when the request, code and docs leave intent unclear. Operators get a `wf-upgrade` checklist that uses the gate tools. Before: the shipped text forbids direct retrieval for user questions and demands a question before any edit. After: the same files permit direct retrieval, keep the Guru workflow for mechanism-level questions, and keep the other three principles unchanged. Existing projects receive the change on upgrade without losing their own additions. Boundary: guidance only; no lint, gate, hook or tool behavior changes. AC-1 together with AC-4 tests whether the intent is established in shipped and upgraded text. Whether agents actually stop over-routing is a field observation this change cannot prove.

## Requirements

1. **One consistent routing rule.** A routing surface is any shipped text whose job is to decide when an agent uses Guru. Rewrite every sentence, example or description on a routing surface that routes a code-location question or a targeted lookup to Guru, or that tells an agent not to retrieve directly. The routing surfaces verified in today's tree (a census, not a substitute for the rule) are:
   1. seed 050's auto-Guru section and `AGENTS.md` § Codebase and documentation questions (auto-Guru): the pre-flight question ("If yes, route to Guru", including "where is X" in its list of phrasings), the "understanding, locating, or explaining" sentence, the "Where is the rate limiter defined?" example row and the "Retrieval-intent backstop" paragraph;
   2. seed 211's and `docs/agents/guru.md`'s routing paragraphs: the auto-routing sentence ("Any agent answering code or documentation questions must follow…"), the pre-flight question ("that's a Guru question"), the anchoring examples ("…are all Guru questions", including the rate-limiter example) and the backstop;
   3. the host routing surfaces: the Cursor rule `CURSOR_AUTO_GURU_MDC` ("Guru work when the user is asking to understand, locate, or explain"), the Guru subagent `description` in `CLAUDE_GURU_AGENT` ("where to find implementation"), the `wf-guru` skill description in the skill registry ("locating behavior"), and seed 050's templates for all three (the Cursor rule, the subagent description and the skill description).

   Each rewritten text yields:
   1. an agent may call the `code_*` tools directly at any time;
   2. the pre-flight question asks whether answering needs an investigation of how code or documentation works (a how-or-why question about a mechanism, usually across files); if so, the agent uses the Guru workflow (retrieval loop and Pass 3 validation), and otherwise a direct lookup answers it;
   3. locating a definition or reading one value is a direct lookup in both example sets, with Guru used when the answer needs the surrounding mechanism;
   4. the backstop becomes a reminder of that same question. The **stop** instruction, the all-caps "IS", "instead of doing the retrieval yourself" and "do not perform the retrieval directly" go, and the "This applies to delegated work too" clause stays unchanged.

   `AGENTS.md` keeps its local `code_lexical` entry in the backstop's tool list. Sentences that only describe the Guru workflow itself (classification, including Guru's own "navigational" class, retrieval loop, citations) are not routing surfaces. Keep the existing pin in `test_render_agent_surfaces.py` intact: the "tell me about the way authentication works" example stays in seed 050, seed 211 and `AGENTS.md`, and `AGENTS.md` keeps the "Route to Guru?" column and the "anchoring" heading near it. Re-render every file produced from the changed renderer constants (`.cursor/rules/auto-guru.mdc`, `.claude/agents/guru.md` and every `wf-guru` skill copy).
2. **Guru's own statement (seed 211 and `docs/agents/guru.md`).** Within Requirement 1's set, Guru's voice says: other agents may retrieve directly, and questions that need the retrieval loop and Pass 3 validation are Guru's to answer.
3. **Implementation principle 1 (seed 050 task 16 and `AGENTS.md`).** Rename principle 1 to **Ask when intent is unclear** and reword it to: when the request, code and docs leave intent, architecture or requirements unclear, ask before building on a guess; state any assumption the agent proceeds on. Principles 2 to 4 stay word for word. Seed 160's Implementation Principles check names the new label.
4. **`wf-upgrade` skill gate steps (`render_agent_surfaces.py`, `WF_UPGRADE_SKILL_BODY`).** Replace the steps that create, edit and delete `.wavefoundry/guard-overrides.json` by hand with `wf_open_gate` / `wf_close_gate` for `framework_edit_allowed` and `seed_edit_allowed`, with the `wf gate open|close` CLI fallback. Keep the operator-approval step and the protected surfaces it lists. Update the existing pin in `test_render_platform_surfaces.py` that asserts the rendered skill contains `.wavefoundry/guard-overrides.json`, keeping its other assertions.
5. **Retired journal wording.** In `WF_UPGRADE_SKILL_BODY`, replace "Preserve journals, personas, wave archives, and historical records" with wording that names memory records and keeps personas, wave archives and historical records. In the Guru subagent body that produces `.claude/agents/guru.md`, replace "journal writes" with memory-record writes, matching `docs/agents/guru.md`'s "Guru journal (a typed memory record)". Re-render every surface produced from these constants.
6. **`AGENTS.md` and seed 050 cleanups.** Remove the `AGENTS.md` sentence "The old flat `.claude/skills/upgrade-wave.md` and pre-namespace `.codex/skills/auto-guru/` are stale-cleaned on render." Remove every wave or change ID reference (a lifecycle ID cited as the origin of a rule, such as "wave `1p6lp`" or "changes `1zyv1`, `206fi`") from `AGENTS.md` and from seed 050's prompt text, rewording the surrounding phrase so it still reads as the current rule. An ID that is a machine contract, a marker string or a literal a renderer or lint matches stays; the implementer names any such exception in the Progress Log.
7. **Upgrade delivery (seed 160).** Seed 160's agent-procedure step 4, "Backfill tier 1 in `AGENTS.md`", already reconciles the auto-Guru section "when `050` changed in the pack", but it does not say how to treat local text and does not cover the Implementation Principles. Extend that step:
   1. when seed 050 changed, merge its changed routing text (Requirement 1's set) and principle 1 into the existing `AGENTS.md`;
   2. replace text inherited from the earlier seed, preserve project additions such as extra tool names or project-specific examples, and present ambiguous or conflicting local text to the operator.

   The existing rule that regenerates `docs/agents/guru.md` when seed 211 changed covers that file. Update this repository's rendered `docs/prompts/upgrade-wavefoundry.prompt.md` and add a changelog entry.

## Scope

**Problem statement:** Shipped instruction text forbids direct retrieval, demands a question before any edit, and carries stale gate and journal instructions.

**In scope:**

- Seeds 050, 160 and 211
- Text of `render_agent_surfaces.py` constants `WF_UPGRADE_SKILL_BODY`, `CLAUDE_GURU_AGENT` (description and body), `CURSOR_AUTO_GURU_MDC` and the `wf-guru` skill registry description, plus their rendered outputs
- This repository's `AGENTS.md`, `docs/agents/guru.md` and `docs/prompts/upgrade-wavefoundry.prompt.md`
- Focused tests over the seed text and the rendered skill and subagent, and the changelog

**Out of scope:**

- The `AGENTS.md` tool list: handled by change `237eh-enh tool-spec-as-the-enforced-tool-inventory`
- Wave IDs in seeds other than 050, and every closed wave record
- Seed 210 (Migrate journals) and the memory system
- Any lint, gate, hook, renderer logic or tool behavior change; only the text of the named constants changes
- `CLAUDE.md`, already reduced to its generated regions

## Acceptance Criteria

- [x] AC-1: Every routing surface in Requirement 1 states or implies that direct `code_*` calls are permitted and frames Guru as the answer to a question about how code or docs work. None routes a code-location question or a targeted lookup to Guru: the rate-limiter example is a direct lookup in both example sets; the pre-flight question no longer sends every code-or-doc read to Guru; and the Cursor rule, subagent description and skill description, rendered and in seed 050's templates, no longer name locating or "where to find" as Guru work. None contains "**stop**", "IS Guru's job", "instead of doing the retrieval yourself" or "do not perform the retrieval directly", and the delegated-work clause is unchanged. A test over the four carriers, seed 050's templates and the renderer's output fails on today's text for each surface.
- [x] AC-2: Seed 050 and `AGENTS.md` no longer contain "before writing a single line". Principle 1 asks when the request, code and docs leave intent unclear and requires stating assumptions; principles 2 to 4 are unchanged; seed 160's principles check names the new label. A test fails on the current text.
- [x] AC-3: The rendered `wf-upgrade` skill names `wf_open_gate` and `wf_close_gate` with the `wf gate open|close` fallback, keeps the approval step and both gate names, and no longer tells the operator to create, edit or delete `.wavefoundry/guard-overrides.json` by hand. The skill and the rendered Guru subagent no longer name journals. A test over the renderer output fails on the current constants, and every rendered copy in this repository is refreshed.
- [x] AC-4: Seed 160's step 4 instructs merging changed seed 050 routing text and principle 1 into an existing `AGENTS.md`, replacing inherited text while preserving project additions and presenting conflicts to the operator. A test bounded to that step (from "Backfill tier 1" to the next numbered step) asserts each obligation; the existing "merge-safe" wording alone does not satisfy it, and the test fails on the current seed 160 text. The rendered upgrade prompt's corresponding step is updated to match.
- [x] AC-5: `AGENTS.md` no longer contains the stale-cleaned sentence. A test finds no wave or change ID reference in `AGENTS.md` or seed 050's prompt text other than the exceptions named in the Progress Log, and fails on the current text of both. Its pattern catches bare, backticked, parenthesized and slash-joined IDs (such as wave 1p45l and 1p7pm/1p88t) and does not flag digit-only tokens. The changelog describes the change. The documents this change edits validate, and the change's own tests pass.

## Tasks

- [x] Open `seed_edit_allowed`; edit seeds 050, 211 and 160 (Requirements 1, 2, 3 and 7); close the gate.
- [x] Open `framework_edit_allowed`; edit the named renderer constants (Requirements 1, 4 and 5), update the `test_render_platform_surfaces.py` pin, add the focused tests; close the gate.
- [x] Edit `AGENTS.md`, `docs/agents/guru.md` and the rendered upgrade prompt by the seed-first workflow (Requirements 1, 2, 3, 6 and 7).
- [x] Run `wf render-surfaces` and confirm the rendered skill and subagent copies changed as expected.
- [x] Add the changelog entry; run the focused tests, the second profile on them, and full docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seeds-and-renderer | implementer | — | Serial owner of seeds 050, 160, 211 and the two renderer constants |
| local-carriers | implementer | seeds-and-renderer | `AGENTS.md`, `docs/agents/guru.md`, rendered prompts and skills |


## Serialization Points

- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `.wavefoundry/framework/seeds/211-guru.prompt.md`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/`
- `docs/agents/guru.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, `.claude/agents/guru.md`
- `.claude/skills/wf-upgrade/SKILL.md`, `.codex/skills/wf-upgrade/SKILL.md`, `.agents/skills/wf-upgrade/SKILL.md`
- `.claude/skills/wf-guru/SKILL.md`, `.codex/skills/wf-guru/SKILL.md`, `.agents/skills/wf-guru/SKILL.md`, `.cursor/rules/auto-guru.mdc`
- The root `AGENTS.md` and `CHANGELOG.md` are also edited.

## Affected Architecture Docs

N/A: the change edits instruction prose in seeds, two renderer text constants and their rendered copies. No module boundary, data or control flow, or verification seam changes. Behavior is identical on Windows, macOS, Linux and WSL2: only text changes, and rendering keeps its existing newline handling.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The operator's direct request: direct retrieval is permitted |
| AC-2 | required  | Same over-literal pattern, shipped verbatim to every project |
| AC-3 | required  | Operator checklist contradicts the gate tools |
| AC-4 | required  | Without it, existing projects keep the old text |
| AC-5 | important | Archival text in every session's instructions, here and in seed 050's shipped text |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-12 | Planned from the `/doctor prompt-audit` findings and the operator's direction on the retrieval rule | Audit report in session; line references verified against the tree |
| 2026-11-12 | Repaired before lane review from the red-team primer: B1 (pre-flight question and example sets), seed 160 step 4, the `test_render_platform_surfaces.py` pin, the three rendered skill copies, principle 1's new label, and rule-derived ID set | `.wavefoundry/work/237ef/primer.md` |
| 2026-11-12 | Bounded readiness repair of ROUTING-RDY-1 (code and QA): host routing surfaces added under a rule-derived set; AC-1, AC-4 and AC-5 test oracles tightened from lane notes; existing `test_render_agent_surfaces.py` anchor pin kept | `.wavefoundry/work/237ef/code.md`, `qa.md`, `docs.md` |
| 2026-11-12 | Readied on receipt `review-policy-be68036212b7fb0653d6`: code, QA and docs-contract approvals current; ROUTING-RDY-1 terminal; `council-readiness` intent fit `establishes`. Implementation notes from the lanes and council, non-blocking: (1) seed 050's subagent and skill description templates are already neutral, so record them as absence checks that pass today rather than checks that must fail; (2) apply Requirement 1's rule to the Cursor rule frontmatter ("Auto-route code and documentation questions to Guru"), `WF_GURU_SKILL_BODY` ("the default path for code/doc questions") and seed 050's "delegates code/doc questions", or record why each stays; (3) scope the AC-1 subagent check to its `description:` line, since the body's "locating and understanding code" retrieval bullet describes the workflow; (4) make AC-1 assert the "where is X" outcome explicitly; (5) the rendered upgrade prompt's matching step is "Tier 1 — `AGENTS.md`"; cover it in the AC-4 test; (6) seed 050 has its own stale-cleaned sentence near line 280, outside Requirement 6 unless it is also archival | `.wavefoundry/work/237ef/council.md`, `code-reverify.md`, `qa-reverify.md`, `docs-focused.md` |
| 2026-11-12 | Re-readied with change `237eh` on receipt `review-policy-3644fe6b6c58a9425d1e`; the earlier notes still apply. Added notes, non-blocking: (1) seed 160 step 4 does not carry the ID removals into existing targets' `AGENTS.md`, which the Objective does not claim; (2) `AGENTS.md` carries uncommitted edits and change `237eh` also edits it, so build on the working tree and serialize the two changes' `AGENTS.md` edits | `.wavefoundry/work/237ef/council-final.md` |
| 2026-11-12 | Readback: rewrite every routing surface (seed 050 auto-Guru section and templates, seed 211, `AGENTS.md`, `docs/agents/guru.md`, `CURSOR_AUTO_GURU_MDC`, the `CLAUDE_GURU_AGENT` description, the `wf-guru` skill description) so direct `code_*` calls are permitted and Guru answers how-or-why mechanism questions (AC-1); rename principle 1 to "Ask when intent is unclear" in seed 050, `AGENTS.md` and seed 160's check (AC-2); switch `WF_UPGRADE_SKILL_BODY` to the gate tools and replace journal wording there and in the Guru subagent (AC-3); extend seed 160 step 4 with the merge rule and update the rendered upgrade prompt (AC-4); drop the stale-cleaned sentence and every origin wave or change ID from `AGENTS.md` and seed 050 (AC-5). Example: "Where is the rate limiter defined?" goes from "Yes, route to Guru" to a direct lookup, and the backstop's "**stop**" becomes a reminder to ask whether the question needs Guru. Serves Product Intent by removing the forbidding rule at its source in the seeds, so every project gets it on upgrade. Boundary: text only; no renderer logic, lint, gate or hook change. Files: the three seeds, `render_agent_surfaces.py` constants, `AGENTS.md`, `docs/agents/guru.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, rendered skill, subagent and Cursor copies, focused tests and `CHANGELOG.md` | Plan Requirements 1 to 7 |
| 2026-11-12 | Implemented. Seeds 050, 211 and 160 edited under `seed_edit_allowed` (closed after); renderer constants `CURSOR_AUTO_GURU_MDC` (including its frontmatter description), the `CLAUDE_GURU_AGENT` description and body, the `wf-guru` registry description, `WF_GURU_SKILL_BODY` ("default path for questions about how code or docs work") and `WF_UPGRADE_SKILL_BODY` edited; seed 050's "delegates code/doc questions" line reworded; `AGENTS.md`, `docs/agents/guru.md` and the rendered upgrade prompt's Tier 1 step updated; `wf render-surfaces` refreshed `.cursor/rules/auto-guru.mdc`, `.claude/agents/guru.md` and the three `wf-guru` and three `wf-upgrade` skill copies, all with parseable frontmatter. Lifecycle-ID exceptions: none (no renderer, lint or test matches any removed ID as a literal; the remaining citations are code comments and docstrings outside this scope). Kept: seed 050's "stale-cleaned by the render pass" sentence for `.codex/skills/auto-guru/`, which describes current renderer behavior (`STALE_SKILL_PATHS`), not a past migration; the subagent body's "locating and understanding code" retrieval bullet, which describes the workflow, not routing. Tests: new `test_render_agent_surfaces.py::RoutingGuidanceTextTests` (9 tests: AC-1 carriers, rate-limiter rows, host surfaces, Guru's statement; AC-2 principle 1; AC-3 skill and subagent; AC-4 seed 160 step 4 and the rendered step; AC-5 ID pattern and census); `test_render_platform_surfaces.py` pin now asserts the gate tools and the absence of `.wavefoundry/guard-overrides.json`. Controls: on a `git archive HEAD` scratch copy, 28 subtests fail across the 8 surface tests (every surface fails on today's text; seed 050's already-neutral subagent and skill templates fail on the positive direct-lookup check); mutants on a scratch copy of the edited tree, restoring only the Cursor rule's "understand, locate, or explain" and shortening the `AGENTS.md` delegated clause, each fail exactly one subtest. Profiles: declared and second pass for `test_render_agent_surfaces.py` and `test_render_platform_surfaces.py`; the first default run passed every test but was flagged for repository changes made during the run, so it is rerun once the tree is quiet. Gapfill: shell for the scratch-copy controls, the ID census and test runs, which MCP tools cannot execute | `RoutingGuidanceTextTests`; scratch copies under the session scratchpad |
| 2026-11-12 | Correction: the implementation row above said re-rendering refreshed `.claude/agents/guru.md`; it refreshed only the body, because `_merge_claude_agent` keeps an existing file's frontmatter, so the description still routed "where to find implementation" to Guru (delivery finding SUBAGENT-DEL-1, found by code, docs-contract and the council red-team). Delivery repair cycle: `.claude/agents/guru.md` description set to the renderer's; seed 160 step 6 and the rendered upgrade prompt tell the upgrading agent to edit that `description:` line; seed 160 step 4 and the rendered Tier 1 step now name the whole changed auto-Guru section (MERGELIST-DEL-1); seed 160's `wf-upgrade` skill check describes the gate-tool flow (UPGRADECHECK-DEL-1); the CHANGELOG entry no longer overclaims and gains a 237eh bullet (CHANGELOG-DEL-1). New guards and their landing mutants (scratch copy): rendered subagent description assertion (`test_rendered_subagent_description_matches_the_renderer` plus a host-surface entry) fails when the old description is restored; the step 4 needles fail on the old three-element list; the seed 160 skill assertion fails on the old guard-overrides wording | Repair mutant run in the session scratchpad `237ef-repair-mut` |
| 2026-11-12 | Reverification: docs-contract resolved SUBAGENT-DEL-1, UPGRADECHECK-DEL-1 and CHANGELOG-DEL-1 and approved delivery; QA resolved MERGELIST-DEL-1 (an M5 replay of the named elements reproduces the delivered `AGENTS.md` section byte for byte) and approved delivery; code confirmed SUBAGENT-DEL-1. Second repair cycle for the code reviewer's SUBAGENT-DEL-2 (seed 050's subagent template description differed from the renderer constant, so seed 160 step 6's "current template text" was ambiguous): seed 050's template now carries the constant's description, and `test_rendered_subagent_description_matches_the_renderer` asserts the two match apart from the profile-renamed lifecycle-command list. Landing: restoring the old template line on a scratch copy fails that test | `.wavefoundry/work/237ef/docs-reverify-delivery.md`, `qa-reverify-delivery.md`, `code-reverify-delivery.md`; scratchpad `237ef-c5-mut` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-12 | One change covering seeds, the two renderer constants, local carriers and upgrade delivery | Every finding is instruction text with the same delivery path; one change keeps review proportionate. Mechanism efficacy: replaying the motivating case, the reworded text no longer tells an agent to stop before a `code_search` call, and the seed 160 rule carries it into existing projects. The change only advises agents; it controls nothing. Tests prove delivery, not changed behavior; success after release is fewer trivial lookups routed to Guru, which is not measured | Two changes (seed guidance, local cleanup): extra admission and review for text sharing one path. Local edits only, drift recorded: every other project keeps the forbidding rule |
| 2026-11-12 | Remove all wave and change ID references from `AGENTS.md` and seed 050, not only the three headings | Operator direction. A reading agent cannot act on an ID; the history lives in git and `docs/waves/`. Covering seed 050 matches the standing preference that shipped seed text not cite internal artifacts. Other seeds stay out of scope to keep the change small | Headings only, leaving the skills paragraph's five IDs and seed 050's eight |
| 2026-11-12 | Hand the `AGENTS.md` tool list to change `237eh` (operator direction) | Investigation showed the list is the only complete, enforced inventory and the spec it should defer to is missing 18 tools, so the correct fix is a separate change that completes and enforces the spec first | Keep the list as working redundancy (the first plan's decision) |
| 2026-11-12 | Extend seed 160's agent-procedure step 4 instead of adding a separate rule (readiness primer repair) | The primer showed step 4, "Backfill tier 1 in `AGENTS.md`", already reconciles the auto-Guru section when seed 050 changed; it lacks the preserve-additions rule and the Implementation Principles. Extending the owning step avoids two rules for one section | A separate seed 160 rule (the plan's first draft, based on the incorrect premise that only the 1.5.0 migration entry reconciled this section) |
| 2026-11-12 | Define routing surfaces by rule and include the host routing surfaces (ROUTING-RDY-1 repair) | Code and QA lanes showed the Cursor always-on rule, the Guru subagent description, the `wf-guru` skill description and seed 050's templates for them still route location lookups to Guru; on Cursor and Claude Code these decide routing before any carrier is read. Lifting the two-constant limit is text-only and keeps the change guidance-only | Keep the host surfaces with a Decision Log reason (rejected: it contradicts the operator's direction on exactly the hosts that auto-route) |
| 2026-11-12 | Cover the pre-flight question and both example sets, not only the backstop (readiness primer B1) | The pre-flight question ("If yes, route to Guru") and the "Where is the rate limiter defined? → Yes" examples would still route the motivating trivial lookup to Guru, so softening the backstop alone leaves contradictory rules and does not meet the operator's direction | Soften only the backstop paragraph |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| An upgrade merge overwrites a project's own retrieval or principle wording | The new rule preserves project additions and presents conflicts to the operator |
| Softened wording lets agents skip Guru on questions that need it | The text keeps the Guru workflow for mechanism-level questions and keeps the delegated-work clause |
| A test or golden pins the old renderer constant text | Search the tests for the old strings before editing; update any pin with the change |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
