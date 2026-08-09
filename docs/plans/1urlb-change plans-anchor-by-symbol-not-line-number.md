# Plans And Reviews Anchor By Symbol, Not By Line Number

Change ID: `1urlb-change plans-anchor-by-symbol-not-line-number`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-08
Wave: 1uprb review-authority-mutation-on-failure

## Rationale

Line-number citations in change docs and review evidence go stale, and the repository already knows it. The practice exists but only as scattered per-wave watchpoints, so it is applied when someone remembers and skipped when they do not.

Wave `1sufo` states it plainly:

> Anchor by symbol (`wave_memory_search_response`), not line number: a concurrent session is editing `server_impl.py`, so the semantic re-sort has drifted (was ~8002-8004, now ~8008-8010) and will keep moving.

`1tmb1` and `1p9pe` carry the same instruction as their own watchpoints. Three waves independently rediscovered the rule, which is the signature of a convention that belongs in a seed rather than in a wave record.

**Measured cost, this session.** In wave `1ur6p` six cited line anchors went stale and had to be re-anchored **twice** — once when implementation shifted the files, and again when a later fold shifted them further. Independent review spent findings on it both times. In wave `1uprb` a council seat filed citation drift as a finding when a cited range named `:15619-15631` while the statement it referenced closed at `:15629`. Both waves declared files under concurrent edit by sibling waves, and both cited into them by line anyway.

**Why the fix is now cheap.** A symbol anchor is not merely more durable, it is *resolvable*: `code_definition(symbol)` and `code_read` return the current text, so a reader with MCP always gets today's version. A line anchor cannot be resolved that way; it can only be checked, and checking is what keeps costing review cycles. The retrieval tools that make symbol anchors resolvable already ship, which is what makes this a documentation change rather than a tooling one.

**Boundary.** This is about durable citations in **authored artifacts** — change docs, wave records, review evidence. It is explicitly NOT about retrieval tools *returning* line numbers: `code_callhierarchy`, `code_references` and `code_ask` should keep reporting exact lines, because that is how a reader navigates to a symbol in the first place. Seed 211 fuses both concerns in one place, so the boundary is drawn **within** it rather than around it: its `code_ask` response-field list and its external-sources block are tool-side and stay; its `## Citation Format` opening and Assumption Discipline bullet are author-side and are reconciled. An earlier revision of this paragraph said the whole citation-format section "stays as it is", which would have made this change contradict its own AC-2.

## Requirements

1. **Authored artifacts anchor by symbol.** Change docs, wave records, and review evidence cite a resolvable anchor — a function, class, constant, test name, or a distinguishing expression — rather than a bare `file:line`. State the rule where authors and reviewers will meet it.

2. **The rule is conditional, not absolute, and says so.** A line number is acceptable when no symbol contains the site (a module-level constant block, a data file, a specific line in a generated artifact, **or prose in a hand-authored markdown document**) or when the citation is deliberately historical, such as a Progress Log row recording what was verified at a point in time. Blanket prohibition would push authors into worse citations, for example naming a whole 30,000-line file.

3. **Historical rows are exempt and stay exempt.** Line numbers already written into `## Progress Log` and `## Decision Log` rows are records of what was verified when, and rewriting them falsifies the history. The rule applies to live claims, not to the log of how they were reached.

4. **The rule names its own reason.** An author must be able to tell when it matters: the anchor is resolvable with `code_definition` / `code_read`, and line anchors drift hardest exactly when the target file is under concurrent edit, which is when reviewers are most likely to be reading it.

5. **No mechanical enforcement ships in this change.** A docs-lint rule that flags `file:line` in a change doc would need to distinguish live claims from historical rows and from legitimately line-anchored sites, which Requirements 2 and 3 make a judgment call. Guidance first; measure whether it holds before considering a gate.

## Scope

**Problem statement:** A durable-citation practice that three waves independently rediscovered exists nowhere an author is required to read, so plans keep citing line numbers into files under concurrent edit and reviewers keep spending findings on drift.

**In scope:**

- Seed `170-plan-feature.prompt.md`: the authoring rule for change docs.
- Seed `180-implement-feature.prompt.md` and `211-guru.prompt.md`: the citation rule for review evidence and findings, without disturbing their existing retrieval-tool guidance.
- `.wavefoundry/framework/seeds/237-council-review.prompt.md`, resolved rather than left undetermined. Its sentence "cited `file:line` sites and symbols must resolve" is a verification instruction that already names symbols, so it does not contradict the new rule and needs **no edit**. Recorded as an explicit decision so the scope item is not left dangling at prepare.
- Rendered prompt surfaces regenerated from the edited seeds.

**Out of scope:**

- Any docs-lint rule or mechanical gate (Requirement 5).
- Retrofitting existing change docs. Live claims in an OPEN wave may be re-anchored opportunistically; closed waves are history.
- Changing what retrieval tools return.

## Acceptance Criteria

- [ ] AC-1: The rule appears in `170-plan-feature.prompt.md` in the section an author reads while writing a change doc, and states the resolvable-anchor reason rather than only the prohibition.
- [ ] AC-2: The rule reaches the **author-side** citation sites in seed 211 and leaves the **tool-side** ones untouched. Pinned by exact label rather than paraphrase, because a paraphrase is what produced the original defect:
  **Unchanged:** the literal "Citation fields in `code_ask` response" list, and the "Citation format for external sources:" block. Retrieval tools must keep returning exact lines.
  **Reconciled, directionally:** the `## Citation Format` opening and the Assumption Discipline "Code-validated" bullet gain the symbol anchor as the **primary** form while **keeping** `path:start-end` as the locating aid. Deleting the notation would strand the tool-side field list immediately below, which depends on it.
  **Both forms, with its reason stated in the seed:** the "Cite results as `path:line_number`" line under `## When MCP is Not Available`. That section exists because MCP is down, so `code_definition` and `code_read` are unavailable by construction and Requirement 4's justification does not hold there; a grep-only reader needs the line to re-find the site. Both anchors ship together there and only there.
- [ ] AC-3: The conditional carve-outs from Requirements 2 and 3 are stated in the seed text, not left implicit. An author must be able to read the seed and know that a module-level constant may be line-cited and that a Progress Log row is not to be rewritten.
- [ ] AC-4: Rendered prompt surfaces regenerate cleanly from the edited seeds, and `docs/prompts/prompt-surface-manifest.json` reflects it.
- [ ] AC-5: This wave's own change docs carry zero **un-annotated** line-number citations in live claims, verified by count, and every remaining line citation names which Requirement 2 carve-out applies. An absolute zero is the wrong pin: prose in a hand-authored markdown doc has no containing symbol, which Requirement 2's carve-out list must therefore name explicitly alongside the module-level constant case.
- [ ] AC-6: The full framework suite and docs-lint pass.

## Tasks

- [ ] Draft the rule text once, with the carve-outs, and reuse it rather than paraphrasing per seed.
- [ ] Edit `170-plan-feature.prompt.md` under the `seed_edit_allowed` gate.
- [ ] Edit the review-side seeds under the same gate, leaving retrieval guidance untouched.
- [ ] Regenerate rendered prompt surfaces.
- [ ] Count live-claim line citations across this wave's change docs and record zero.
- [ ] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| rule-text | implementer | — | One canonical wording, including carve-outs |
| seed-edits | implementer | rule-text | Requires `seed_edit_allowed`; do not disturb retrieval guidance |
| surface-render | implementer | seed-edits | Regenerate and verify the manifest |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `.wavefoundry/framework/seeds/211-guru.prompt.md`
- `docs/prompts/prompt-surface-manifest.json`

## Affected Architecture Docs

`N/A` with rationale: this changes authoring guidance in seed prompts and their rendered surfaces. It moves no boundary, no data flow, and no test topology.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | If the rule is not where an author writes, it stays a per-wave watchpoint, which is the current failure. |
| AC-2 | required | A reviewer applying a different standard than the author reproduces the drift from the other side; the negative half stops the edit bleeding into retrieval guidance. |
| AC-3 | required | Without the carve-outs the rule is wrong often enough to be ignored, which is worse than absent. |
| AC-4 | important | Rendered surfaces are what most hosts actually read. |
| AC-5 | important | Self-application. A wave that writes this rule and violates it teaches the opposite. |
| AC-6 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
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
| The seed edit bleeds into retrieval-tool guidance | AC-2 pins seed 211's `code_ask` citation-format section as unchanged; the tools should keep returning exact lines |
| Guidance alone does not change behavior | Accepted for this change, and stated as such in Requirement 5: measure adherence over the next few waves before considering a gate |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
