# Plans And Reviews Anchor By Symbol, Not By Line Number

Change ID: `1urlb-change plans-anchor-by-symbol-not-line-number`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-09
Wave: 1usqm citation-durability-and-receipt-integrity

## Rationale

Line-number citations in change docs and review evidence go stale, and the repository already knows it. The practice exists but only as scattered per-wave watchpoints, so it is applied when someone remembers and skipped when they do not.

Wave `1sufo` states it plainly:

> Anchor by symbol (`wave_memory_search_response`), not line number: a concurrent session is editing `server_impl.py`, so the semantic re-sort has drifted (was ~8002-8004, now ~8008-8010) and will keep moving.

`1tmb1` and `1p9pe` carry the same instruction as their own watchpoints. Three waves independently rediscovered the rule, which is the signature of a convention that belongs in a seed rather than in a wave record.

**Measured cost, this session.** In change `1ur6p` (wave `1ur6o`) six cited line anchors went stale and had to be re-anchored **twice** — once when implementation shifted the files, and again when a later fold shifted them further. Independent review spent findings on it both times; both re-anchoring rows are in that change's Progress Log. A second anecdote, about a `1uprb` seat filing a cited range of `:15619-15631` against a statement closing at `:15629` (quoted ranges, not anchors — the citation is the subject of the sentence), is **recorded here as unverified**: it is not findable in that wave's change doc, `wave.md`, or `events.jsonl`, and appears to have lived only in a seat report that was never persisted. It is kept, marked, rather than deleted or asserted, because a plan about citation durability must not itself carry an unbacked citation. Both waves declared files under concurrent edit by sibling waves, and both cited into them by line anyway.

**Why the fix is now cheap.** A symbol anchor is not merely more durable, it is *resolvable*: `code_definition(symbol)` and `code_read` return the current text, so a reader with MCP always gets today's version. A line anchor cannot be resolved that way; it can only be checked, and checking is what keeps costing review cycles. The retrieval tools that make symbol anchors resolvable already ship, which is what makes this a documentation change rather than a tooling one.

**Boundary.** This is about durable citations in **authored artifacts** — change docs, wave records, review evidence. It is explicitly NOT about retrieval tools *returning* line numbers: `code_callhierarchy`, `code_references` and `code_ask` should keep reporting exact lines, because that is how a reader navigates to a symbol in the first place. Seed 211 fuses both concerns in one place, so the boundary is drawn **within** it rather than around it: its `code_ask` response-field list and its external-sources block are tool-side and stay; its `## Citation Format` opening and Assumption Discipline bullet are author-side and are reconciled. An earlier revision of this paragraph said the whole citation-format section "stays as it is", which would have made this change contradict its own AC-2.

## Requirements

1. **The authored surfaces delivered by this change anchor by symbol.** Change docs, wave records, and **agent answers or durable notes that cite code** cite a resolvable anchor — a function, class, constant, test name, or a distinguishing expression — rather than a bare `file:line`. State the rule where authors and reviewers will meet it. The third category is named because AC-2 reconciles seed 211's `## Citation Format` opening and its Assumption Discipline bullet, both of which govern **Guru answers** (including its writes to `docs/agents/memory/`, `docs/architecture/` and `docs/specs/` under the seed's Write Permissions table). **Review-evidence citation authoring remains a desired domain but is not a delivered requirement of this change:** its only carriers are seed 209 plus the council/lane seeds, and Scope records that work as an explicit follow-up. An earlier revision named review evidence here while simultaneously deferring every surface that could implement it, leaving a normative requirement no AC could prove; delivery review narrowed the requirement rather than pretending the deferral satisfied it.

2. **The rule is conditional, not absolute, and says so.** A line number is acceptable when no symbol contains the site (a module-level constant block, a data file, a specific line in a generated artifact, **or prose in a hand-authored markdown document**) or when the citation is deliberately historical, such as a Progress Log row recording what was verified at a point in time. Blanket prohibition would push authors into worse citations, for example naming a whole 30,000-line file. **A line citation taken under a carve-out names the carve-out inline**, so a reviewer can tell a deliberate line anchor from a lapsed one. Without this sentence the annotation obligation exists only in AC-5, which binds this wave alone: a seed could list the carve-outs, never ask anyone to annotate, and the practice would die with this change.

3. **Historical rows are exempt and stay exempt.** Line numbers already written into `## Progress Log` and `## Decision Log` rows are records of what was verified when, and rewriting them falsifies the history. The rule applies to live claims, not to the log of how they were reached.

4. **The rule names its own reason.** An author must be able to tell when it matters: the anchor is resolvable with `code_definition` / `code_read`, and line anchors drift hardest exactly when the target file is under concurrent edit, which is when reviewers are most likely to be reading it.

5. **No mechanical enforcement ships in this change.** A docs-lint rule that flags `file:line` in a change doc would need to distinguish live claims from historical rows and from legitimately line-anchored sites, which Requirements 2 and 3 make a judgment call. Guidance first; measure whether it holds before considering a gate.

## Scope

**Problem statement:** A durable-citation practice that three waves independently rediscovered exists nowhere an author is required to read, so plans keep citing line numbers into files under concurrent edit and reviewers keep spending findings on drift.

**In scope:**

- Seed `170-plan-feature.prompt.md`: the authoring rule for change docs.
- Seeds `180-implement-feature.prompt.md` and `211-guru.prompt.md`: the citation rule for **implementation-time and Q&A citations**, without disturbing their existing retrieval-tool guidance. An earlier revision claimed these two carry "the citation rule for review evidence and findings"; they do not. A census across all 68 seeds places the `wf_review_event` evidence-field contract (the only seed containing `artifact_or_test_id`) in `209-agent-harness-core.prompt.md`, and council-seat finding authoring in `237-council-review.prompt.md`. Seed 211's `## Citation Format` governs Guru **answers**, not review evidence.
- `.wavefoundry/framework/scripts/render_agent_surfaces.py` and its rendered `.claude/agents/guru.md` consumer: the Claude native wrapper carried a contradictory bare-`file:line` instruction, so the durable fix belongs in the renderer source and the generated carrier is verified with it.
- `.wavefoundry/framework/seeds/237-council-review.prompt.md`, resolved rather than left undetermined. Its sentence "cited `file:line` sites and symbols must resolve" is a verification instruction that already names symbols, so it does not contradict the new rule and needs **no edit**. Recorded as an explicit decision so the scope item is not left dangling at prepare.
- Rendered prompt surfaces regenerated from the edited seeds.

**Out of scope:**

- Any docs-lint rule or mechanical gate (Requirement 5).
- **Review-evidence citation authoring**, which lives in `209-agent-harness-core.prompt.md` and the lane seeds rather than in any seed this change edits. Named as a follow-up rather than silently absorbed, because Requirement 1 lists review evidence as an in-domain artifact and this change gives that third no landing site. The follow-up must also revisit `237-council-review.prompt.md`: the no-edit decision below is correct on non-contradiction grounds, but 237 is where a council seat is told what to do and its only citation sentence currently normalizes `file:line`, so "does not contradict" is weaker than Requirement 1's "state the rule where authors and reviewers will meet it".
- Retrofitting existing change docs. Live claims in an OPEN wave may be re-anchored opportunistically; closed waves are history.
- Changing what retrieval tools return.

## Acceptance Criteria

- [x] AC-1: The rule appears in `170-plan-feature.prompt.md` as a new `### Citations in change docs anchor by symbol` subsection placed immediately before the existing `### AC and task checkbox states — the [~] marker` subsection, and states the resolvable-anchor reason rather than only the prohibition. **The insertion point is named because that seed has none to find:** a census for `citation|cite|cited|file:line|line number` across its 205 lines returns **zero** matches, and it carries exactly three headings, so an earlier revision's "the section an author reads while writing a change doc" named nothing that exists.
- [x] AC-2: The rule reaches the **author-side** citation sites in seed 211 and leaves the **tool-side** ones untouched. Pinned by exact label rather than paraphrase, because a paraphrase is what produced the original defect:
  **Unchanged:** the literal "Citation fields in `code_ask` response" list, **because retrieval tools must keep returning exact lines**; and the "Citation format for external sources:" block, **because an external URL has no containing symbol and the anchor question does not arise**. The two justifications are stated separately because they differ: the external-sources block under `## External Lookup` defines an *authored* format (`Source: https://… (retrieved …)`) that no retrieval tool emits, so an earlier revision's shared "tool-side" rationale was false for it even though the disposition was right.
  **Reconciled, directionally:** the `## Citation Format` opening and the Assumption Discipline "Code-validated" bullet gain the symbol anchor as the **primary** form while **keeping** `path:start-end` as the locating aid. Deleting the notation would strand the tool-side field list immediately below, which depends on it.
  **Both forms, with its reason stated in the seed:** the "Cite results as `path:line_number`" line under `## When MCP is Not Available`. That section exists because MCP is down, so `code_definition` and `code_read` are unavailable by construction and Requirement 4's justification does not hold there; a grep-only reader needs the line to re-find the site. Both anchors ship together there and only there.
- [x] AC-3: The conditional carve-outs from Requirements 2 and 3 are stated in the seed text, not left implicit. The seed text enumerates **all five** Requirement 2 carve-outs (module-level constant block, data file, generated artifact, prose in a hand-authored markdown document, deliberately historical citation) and **both** Requirement 3 sections (`## Progress Log`, `## Decision Log`), verified by reading the rendered seed. An earlier revision pinned only two of the seven, so a seed naming the module-level constant and the Progress Log while omitting data files, generated artifacts and the Decision Log would have passed.
- [x] AC-2b: The rule reaches `180-implement-feature.prompt.md` at a **named insertion point** — adjacent to the existing delivery-review Stop-condition bullet, which already names "a drifted line citation in `## Rationale`" as an editorial finding class — stated for the citations an implementer and reviewer write into `## Progress Log` evidence and into findings. The seed's existing MCP retrieval-tool guidance (the numbered `code_*` tool list) is **byte-unchanged**, verified by diff. Without this AC, seed 180 is in Scope, in a Task and in the Agent Execution Graph but pinned by nothing, so an implementation that never opens it passes every AC green.
- [x] AC-4: **The consumer surfaces of the edited seeds carry the rule.** `docs/agents/guru.md` is updated to match seed 211 at all five pinned sites — it is materialized from the seed by an agent at Init/Upgrade, **not** by a renderer, so it does not follow automatically. The Claude native wrapper is repaired at its owning `CLAUDE_GURU_AGENT` template in `.wavefoundry/framework/scripts/render_agent_surfaces.py`, and the rendered `.claude/agents/guru.md` carries the symbol-first rule with the line range retained beside it. `docs/prompts/plan-feature.prompt.md` and `docs/prompts/implement-feature.prompt.md` are checked and updated only if they restate citation guidance. `wf render-surfaces` runs and reports no drift. `docs/prompts/prompt-surface-manifest.json` is **not** expected to change: no field in it derives from seed body text, so an earlier revision's manifest clause was vacuously satisfiable by `last_gardened_at` alone.
- [x] AC-5: This wave's own change docs carry zero **un-annotated** line-number citations in live claims, verified by count, and every remaining line citation names which Requirement 2 carve-out applies. An absolute zero is the wrong pin: prose in a hand-authored markdown doc has no containing symbol, which Requirement 2's carve-out list must therefore name explicitly alongside the module-level constant case.
- [x] AC-6: The full framework suite and docs-lint pass.

## Tasks

- [x] Draft the rule text once, with the carve-outs, and reuse it rather than paraphrasing per seed.
- [x] Edit `170-plan-feature.prompt.md` under the `seed_edit_allowed` gate.
- [x] Edit the review-side seeds under the same gate, leaving retrieval guidance untouched.
- [x] Update `docs/agents/guru.md` to match seed 211 at all five pinned sites; it does not regenerate from the seed.
- [x] Repair the Claude native wrapper at `CLAUDE_GURU_AGENT` in `render_agent_surfaces.py` and re-render `.claude/agents/guru.md`.
- [x] Run `wf render-surfaces`, and check `docs/prompts/plan-feature.prompt.md` and `docs/prompts/implement-feature.prompt.md` for restated citation guidance.
- [x] Count live-claim line citations across this wave's change docs and record the count, with each remaining one naming its carve-out.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| rule-text | implementer | — | One canonical wording, including carve-outs |
| seed-edits | implementer | rule-text | Requires `seed_edit_allowed`; do not disturb retrieval guidance |
| consumer-surfaces | implementer | seed-edits | Hand-update `docs/agents/guru.md` at the five pinned sites; repair `CLAUDE_GURU_AGENT` in `render_agent_surfaces.py`; verify the rendered `.claude/agents/guru.md` carrier |
| surface-render | implementer | consumer-surfaces | Run `wf render-surfaces`; check the two rendered prompt surfaces. The manifest is not expected to move |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `.wavefoundry/framework/seeds/211-guru.prompt.md`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.claude/agents/guru.md`
- `docs/agents/guru.md`
- `docs/prompts/plan-feature.prompt.md`
- `docs/prompts/implement-feature.prompt.md`

**The rendered consumer surfaces are declared because they do not follow automatically.** Seed 211 declares `**Output path:** docs/agents/guru.md`, but `render_platform_surfaces.py` runs the agent-surface pass only **when `docs/agents/guru.md` already exists** — the file is a precondition, not an output — and `render_agent_surfaces.py` writes only `.claude/agents/guru.md`, `.cursor/rules/auto-guru.mdc`, the Codex skill and the root bridge. `docs/prompts/*.prompt.md` bodies are agent-reconciled at Init/Upgrade per seeds 040 and 160, not mechanically regenerated. All five strings AC-2 pins in seed 211 also live in `docs/agents/guru.md`, located **by the strings themselves rather than by line**. An earlier revision recorded line anchors here (471, 544, 587, 596, 691) under the hand-authored-markdown carve-out; two of them drifted before this wave closed, because this change's own edits to that file moved the strings. That is this change's thesis demonstrated against itself, and it is recorded rather than quietly repaired: the durable anchors are the strings, quoted verbatim in AC-2. Editing the seeds alone would therefore leave this repository's own Guru role doc, and every host surface derived from it, teaching the rule this change exists to replace.

`docs/prompts/prompt-surface-manifest.json` was declared in an earlier revision and is **removed**: none of its fields (`public_prompt_surface`, `generated_artifacts`, `framework_revision`, …) derives from seed body text, so it cannot reflect this change. The only field that would move is `last_gardened_at`, which any docs edit bumps, making the old AC-4 clause vacuously satisfiable.

## Affected Architecture Docs

`N/A` with rationale: this changes authoring guidance in seed prompts and their rendered surfaces. It moves no boundary, no data flow, and no test topology.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | If the rule is not where an author writes, it stays a per-wave watchpoint, which is the current failure. |
| AC-2 | required | A reviewer applying a different standard than the author reproduces the drift from the other side; the negative half stops the edit bleeding into retrieval guidance. |
| AC-2b | required | Seed 180 is in Scope, a Task and the AEG but was pinned by no AC, so an implementation that never opened it passed everything green. |
| AC-3 | required | Without the carve-outs the rule is wrong often enough to be ignored, which is worse than absent. |
| AC-4 | required | Rendered surfaces are what most hosts actually read, and `docs/agents/guru.md` does not regenerate from its seed. Raised from important: without it the change ships with its own consumer surface teaching the rule it replaces. |
| AC-5 | important | Self-application. A wave that writes this rule and violates it teaches the opposite. |
| AC-6 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-09 | Full-depth delivery primer and QA converged on a contract contradiction: Requirement 1 required review-evidence citation authoring while Scope deferred seed 209 and the council/lane carriers, and no AC could prove that category. Narrowed Requirement 1 to the actually delivered change-doc, wave-record and Guru answer/durable-note surfaces; retained review evidence as the explicit named follow-up | red-team delivery primer; QA AC reconciliation; Scope out-of-scope carrier census |
| 2026-08-09 | Independent docs-contract delivery review found that the Claude wrapper repair was recorded only in the Progress Log, leaving its renderer source and generated carrier outside the owning Scope, AC, Task, execution graph and Serialization Points. Folded both delivered surfaces into those sections; no implementation changed | canonical `serialization_point_paths` target census versus `git diff --name-only`; renderer `CLAUDE_GURU_AGENT` and `.claude/agents/guru.md` |
| 2026-08-08 | IMPLEMENTED. Seed 170 gained `### Citations in change docs anchor by symbol` immediately before the `[~]` marker subsection, with all five carve-outs in a table plus both historical sections. Seed 180 gained the cite-by-symbol bullet adjacent to the Stop-condition bullet; its retrieval-tool guidance verified byte-identical by md5 across the edit (795c05fb4ddea3ff603f2bfc02be62f8 before and after). Seed 211 reconciled at the two author-side sites and given both-forms treatment under `## When MCP is Not Available`; both pinned tool-side sites confirmed untouched by diff | md5 before/after; `git diff` filtered on the two unchanged labels returned nothing |
| 2026-08-08 | Consumer surfaces closed: `docs/agents/guru.md` hand-updated at the same three edit sites, since the renderer treats it as a precondition rather than an output. `wf render-surfaces` run clean. **An earlier version of this row claimed both derived wrappers needed no change; that was FALSE for `.claude/agents/guru.md` and both the docs-contract and architecture delivery lanes caught it.** Its step 4 read "Return a complete answer with file:line citations" — contradicting step 1 of the same list, which points at the doc this change just rewrote — and it is renderer-owned, so it ships to every target repo. Repaired at source in `render_agent_surfaces.py` under the framework gate and re-rendered. `.cursor/rules/auto-guru.mdc` and the Codex skill were verified clean. Neither rendered prompt surface restates citation guidance, so AC-4's conditional update correctly did not fire for them. `prompt-surface-manifest.json` did not move, exactly as the plan predicted | `git status` after render: only the three seeds, guru.md, and the regenerated codebase map |
| 2026-08-08 | AC-5 self-application caught a defect in its own verification before it could pass falsely. The first count returned zero, but the detector only matched `file.md:NNN` and missed the `line 476-477` prose form; a second detector then false-flagged one citation as annotated because "regenerated" contains the substring "generated". With a strict carve-out-phrase detector the true count is three live line citations, one of which was genuinely un-annotated. Both were annotated with the named carve-out, final count zero un-annotated | strict detector; 3 live citations, 0 un-annotated |
| 2026-08-08 | BOTH SEATS P1, convergent: AC-4 asserted a rendering mechanism this repository does not have. Seed 211 declares `Output path: docs/agents/guru.md`, but `render_platform_surfaces.py` runs the agent-surface pass only WHEN that file already exists, so it is a precondition rather than an output, and `render_agent_surfaces.py` writes only the Cursor rule, Claude subagent, Codex skill and root bridge. All five strings AC-2 pins live in `docs/agents/guru.md` at lines 471, 544, 587, 596 and 691. Editing the seeds alone would have shipped a change about durable citations whose own 88KB consumer surface still taught the rule it replaces. AC-4 rewritten; `docs/agents/guru.md` and the two rendered prompt surfaces declared | verified: seed `Output path:` line; renderer gating; five string hits in guru.md |
| 2026-08-08 | BOTH SEATS P1, convergent: seed `180-implement-feature.prompt.md` sat in Scope, in a Task and in the Agent Execution Graph while no AC pinned it, so an implementation that never opened it passed every AC green. This is the same defect class the sibling `1upba` names at its own AC-1. Added AC-2b with a named insertion point (the delivery-review Stop-condition bullet, the seed's only citation-adjacent site) and a byte-unchanged diff requirement on its retrieval-tool guidance | both seats, independently |
| 2026-08-08 | Insertion points named for both seeds after a census showed AC-1 pointed at nothing: `170-plan-feature.prompt.md` contains ZERO matches for citation-related terms across 205 lines and carries exactly three headings, so "the section an author reads while writing a change doc" did not exist. AC-1 now names the subsection and its placement | executed census over seed 170 |
| 2026-08-08 | Four scope and pinning corrections folded: AC-3 pinned two of the seven carve-outs Requirements 2 and 3 define, so a seed omitting data files, generated artifacts and the Decision Log would have passed; the annotation obligation existed only in AC-5 and so bound this wave rather than future authors, now stated in Requirement 2; Requirement 1's artifact domain did not contain the Guru-answer surface AC-2 actually edits; and the Scope claim that seeds 180 and 211 carry "the citation rule for review evidence" is false, since a 68-seed census places that contract in `209-agent-harness-core.prompt.md`. Review-evidence authoring is now an explicit out-of-scope follow-up rather than an unlanded third of Requirement 1 | docs-contract seat, with red-team concurring on the 209 placement |
| 2026-08-08 | Two accuracy repairs to this plan's own evidence, both recorded rather than quietly applied: `1ur6p` is a CHANGE inside wave `1ur6o`, not a wave; and the `1uprb` anecdote about a `:15619-15631` citation is not findable in that wave's change doc, `wave.md` or `events.jsonl`, so it is now marked unverified rather than asserted. A plan about citation durability carrying an unbacked citation is the failure it exists to prevent | red-team search across the `1uprb` wave folder |
| 2026-08-08 | `docs/prompts/prompt-surface-manifest.json` REMOVED from Serialization Points and from AC-4: no field in it derives from seed body text, so the only field that would move is `last_gardened_at`, which any docs edit bumps, making the old clause vacuously satisfiable. Seed 160 also records the file as renderer-managed and excluded from the reconcile scan | docs-contract seat, field-by-field read |
| 2026-08-08 | Raised by the operator after noticing line-number citations in `1upba`'s plan. Searched for an existing rule before assuming one: none found in the seeds. What exists is the same instruction independently recorded as a watchpoint in three separate waves, each time triggered by the target file being under concurrent edit | `1sufo`, `1tmb1`, `1p9pe` wave records |
| 2026-08-08 | `1upba`'s 33 line-number citations re-anchored to symbols before this change was authored, as the worked example. All four declared files were confirmed modified in the working tree by sibling waves, so the concurrent-edit trigger from the prior waves applied exactly | count verified: zero un-annotated line citations remain. Two live claims cite a prose paragraph in `data-and-control-flow.md` by line, which is the Requirement 2 carve-out and is now annotated as such in `1upba` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-08 | Guidance in seeds, no docs-lint rule | Requirements 2 and 3 make this a judgment call: a lint rule would have to separate live claims from historical Progress Log rows and from legitimately line-anchored sites, and a rule that fires on correct citations trains authors to ignore it, which this repository has already measured once when declining a placeholder heuristic | Ship a docs-lint gate now (rejected: unmeasured false-positive rate on a judgment boundary); leave it as per-wave watchpoints (rejected: that is the status quo that failed three times) |
| 2026-08-08 | Do not retrofit closed waves | Line numbers in closed-wave records are history, and rewriting them falsifies what was verified when | Bulk re-anchor the corpus (rejected: destroys the record and touches hundreds of closed documents for no live benefit) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The rule is read as absolute and authors cite whole files | Requirement 2 and AC-3 require the carve-outs to be stated in the seed text, with the module-level-constant case named explicitly |
| The seed edit bleeds into retrieval-tool guidance | AC-2 pins seed 211's **tool-side** sites as unchanged by exact label — the "Citation fields in `code_ask` response" list and the "Citation format for external sources:" block; the tools should keep returning exact lines. It does not pin the whole citation-format section, whose opening is author-side and is reconciled |
| Guidance alone does not change behavior | Accepted for this change, and stated as such in Requirement 5: measure adherence over the next few waves before considering a gate |
| The seeds this change edits are themselves under concurrent edit | `170-plan-feature.prompt.md` carries uncommitted working-tree modifications right now, and seed 180 was edited by the shipped sibling `1urlc`. That is this change's own central justification applied to itself, and the sibling `1upba` names the same hazard for its `.py` files while this one did not. The implementer confirms each insertion point is unmodified by a sibling before editing, and re-reads rather than trusting a line offset recorded earlier in the session |
| The seed edits land but the surfaces hosts actually read keep the old rule | AC-4 declares `docs/agents/guru.md` and the two rendered prompt surfaces as explicit deliverables, because seed 211's `Output path:` is not honored by any renderer — `render_platform_surfaces.py` treats `guru.md` as a precondition for the agent-surface pass, not as an output |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
