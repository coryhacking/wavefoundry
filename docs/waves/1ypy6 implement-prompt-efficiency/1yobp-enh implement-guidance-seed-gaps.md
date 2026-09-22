# Implement Guidance Seed Gaps

Change ID: `1yobp-enh implement-guidance-seed-gaps`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-21
Wave: `1ypy6 implement-prompt-efficiency`

## Rationale

An independent review of the **Implement wave** prompt surface and of the implementation review step (2026-09-21) traced the failures the last two handler-split waves paid for to one-sentence gaps in the seeds every target receives, and found seed sentences that contradict the lifecycle the tools enforce. Every item here is GENERIC: it reaches existing targets only through a seed re-render on upgrade, so it belongs in seeds, not in the packaged template or in Wavefoundry's own prompt. The readiness round removed two items the first draft placed here by mistake: the retired-journal blocks in the role docs are project-authored prose that no seed or renderer emits (they came from the seed 210 migration an agent performed in this repository), and the repository profile key `code_patterns` has no producer in code (it is agent-authored per seed 030). Their local halves moved to the sibling documentation change; their generic halves stay here as seed sentences.

The gaps. Seed 180's Refactor / API change investigation pattern walks callers by call hierarchy and impact, which finds code that calls a symbol and misses code that names its owner as a string: patch targets, path literals, source-text censuses, import allowlists. Both handler-split waves found those only at full-suite time. Seed 209's Code-Grounded Verification says a census is re-derived when its predicate moves, and freezes the reviewed tree by digest, but says nothing about a measurement whose substrate is not code: the second wave's before and after retrieval receipts were taken across an index reap and read as a code effect until an independent red-team pass compared the corpora. Seed 209 also splits the statement of who writes the ledger across three places, names `recommended_fix` as a required finding field without saying it is a hypothesis, and enumerates the enforced independence codes in a sentence that the sibling bug change makes incomplete.

The contradictions. Seed 180 task 5, seed 100's implement rule and seed 050's stage-gate and implementation-guard items require Prepare to be "the immediately preceding" lifecycle action, which the READY versus OPEN model (wave `1p45l`) and the typed readiness authority replaced: the gate is a current `wave-council-readiness` approval on the current receipt, and any number of readied waves may wait. Seed 180 states the real-time checkbox rule three times (the core execution model paragraph and the two participant bullets); repetition is the salience failure, not the cure. Seed 030 names the profile key `code_pattern` at four sites while this repository's profile and every prose reader carry `code_patterns` (wave `1p2q3` renamed it in seeds to match the MCP tool name; the profile key and the tool are different things).

## Requirements

1. Seed 180, Investigation patterns, the Refactor / API change bullet gains one sentence: when the change moves or renames a definition, also search tests and fixtures for the old owner named as a string (mock or patch targets, path literals, source-text censuses, import allowlists) with the exact-token tool over the test and fixture globs, because those references are not in the call graph and fail only at full-suite time; every hit is classified in the plan before the first move as an update or as intentionally retained with the reason (a fixture that must keep naming the old owner is a retained hit, not an edit). The sentence names no project artifact.
2. Seed 209, Code-Grounded Verification, gains one sentence inserted AFTER the pinned stale-claim sentence (which is byte-pinned by `test_docs_lint.py` and its `testing-architecture.md` twin and is not edited): a before/after measurement pair attributes its delta to the change only when the two runs differ in nothing but the change: each side records the identity of every substrate the measurement depends on (build, index or dataset generation, fixture corpus, environment), each run is stable within itself (the same identity at its start and end), and any substrate that differs between the sides for a reason other than the change is named and the conclusion qualified accordingly. A substrate that the change itself necessarily alters (indexed source changing the index generation) is the intended difference, not a disqualifier; differing identities alone do not prove the delta came from the substrate, they only remove the right to attribute it to the code without qualification. No wave id is added.
3. Seed 209, Typed authoring and human view, gains one sentence replacing the three partial statements of the writing hand (the coordinator-records sentence in Review Artifact Discipline, the reviewer-supplies sentence in Typed authoring, and the numbered lane-clearing steps whose verbs "records" and "submits" become "supplies" with their step semantics kept): the coordinator is the writing hand for every typed event; `verification_context.actor` names the lane whose judgment the event records, and its `context_id`, `fresh_context` and `independent` describe that lane's context, never the coordinator's or the implementer's; the implementer supplies exactly one kind of context, the `repair_start` for a finding it is about to repair. Seed 209's Finding Record Schema `recommended_fix` row gains the clause that it is a hypothesis the repairer re-derives against the tree, and adopting it verbatim is a claim. Seed 209's sentence enumerating enforced independence codes gains `review_context_retained` with its one-line meaning (a fresh-declared reverification or approval from a context that authored any `repair_start`), owned here because the sibling bug change adds the code.
4. Seed 180 task 5, seed 100's `implement-feature + implement-wave` rule, and seed 050's stage-gate item and implementation-guard item are reworded so the pre-condition is "a current typed readiness approval on the current review-policy receipt" rather than a Prepare pass as the immediately preceding action; seed 100's rule keeps its routing back to Plan feature, Create wave, Add change to wave or Prepare wave when the approval is missing or stale, and the replacement wording preserves the two supported non-typed cases: legacy waves whose readiness authority is the prose council verdict, and repositories with wave review disabled, where a clean Prepare pass remains the gate. The five local surfaces carrying the old wording are owned by the sibling `1ypy5`.
5. Seed 180 keeps the real-time checkbox rule in the two participant bullets and drops the core-execution-model copy; seed 100 carries no copy and is not edited for this item; seed 050's AGENTS.md "Change doc tracking" item is a section contract and stays. Seed 180 also gains one sentence, anchored at task 12 of its task list (seed 180 carries no docs-gate wording today): at an explicit validation or handoff boundary, verify the full docs gate with the typed validation tool when the MCP server is attached, CLI fallback otherwise (seed 100 already says this on the rendered rule; seed 180 must carry it so seed 160's carrier clause reaches existing targets).
6. Seed 030 reads `code_patterns` at all four sites, and seed 160 gains one note (placed in step 14 or after the briefing-loop carrier block, never inside it, because that block is byte-pinned against `docs/prompts/upgrade-wavefoundry.prompt.md` by `BriefingLoopCarrierTests`): upgrades accept either spelling in an existing profile and never rename an operator-authored key (seed 030's preservation rule). A static test pins seed 030's key against `docs/repo-profile.json`; there is no producer to pin.
7. Seed 210 step 3 is reworded so folded journal content goes into a history document, not the live role doc; seed 160's operating-memory reconciliation bullet (outside the byte-pinned briefing-loop block) tells targets that an existing migrated block is moved to a history document, archived not deleted. The local move in this repository is owned by `1ypy5`.
8. Seed 110, which already owns the wave-record `Depends On:` grammar, gains the sentence that the line is what `wf_implement_wave` reads for intra-wave order (seed 170 carries no dependency grammar and is not edited, so the grammar stays in one place; the scaffold bullet is owned by `1ypy4`). Seed 160 notes the host-conditional MCP block the packaged implement template now carries, in a new bullet after the briefing-loop carrier block, not inside it.
9. Propagation is explicit, not assumed: `wf render-surfaces` regenerates only renderer-owned regions and baselines, it does not copy new seed prose into existing prompts, and some rendered guidance comes from renderer constants rather than seeds. The inventory therefore carries a propagation table with one row per new or changed sentence: its seed anchor, every destination that should carry it, and the actual mechanism for each (read directly from the seed by agents; a renderer constant in `render_agent_surfaces.py` or `review_policy.py` that this change edits, named; seed 160's authored reconciliation at upgrade for existing targets; or Wavefoundry's own surfaces, whose authored reconciliation is owned by `1ypy5`). A destination with no mechanism is recorded as not propagated rather than claimed. Every seed edit is made with the `seed_edit_allowed` gate open and closed immediately after; `wf render-surfaces` is run once and the diff of every regenerated file is limited to the renderer-owned regions this change names. Pinned tests to respect: `test_docs_lint.py` (the stale-claim sentence, `assertIn`, insertion after it is safe), the seed byte pins in `test_upgrade_wavefoundry.py` and `test_setup_wavefoundry.py` (pass as long as the same seed ships), `test_render_agent_surfaces.py` (seed 160 carrier-clause literals: adding a sentence outside the pinned blocks is safe, rewording the seed list or the briefing-loop block is not). Seed 160 also reconciles repo-local prompts when seed 100 changes, so the seed 100 rewording reaches existing targets by that path too.

## Scope

**Problem statement:** two GENERIC failure classes are uncovered by the seeds, several seed sentences contradict the enforced lifecycle, and the seeds do not describe the ledger's writing hand, the dependency line, or the new independence code.

**In scope:** seeds 180, 209, 100, 050, 030, 110, 210 and 160 as itemized; regenerated surfaces; the static profile-key pin; CHANGELOG bullet.

**Out of scope:** any change to the review-policy digest, the readiness rule, the ReAct loop or the retrieval posture directive; the packaged lifecycle templates and every local surface (sibling documentation change); the tools (sibling bug change); any renderer change (none is needed).

## Acceptance Criteria

- [x] AC-1: Seeds 180 and 209 carry the new sentences (Requirements 1 to 3), generic and naming no project artifact; the propagation table maps every sentence to its destinations and mechanisms; each renderer-constant destination is edited in this change or recorded as not propagated; Wavefoundry's own surfaces are reconciled by `1ypy5`.
- [x] AC-2: Seeds 180, 100 and 050 no longer require Prepare as the immediately preceding action; a grep census over the seeds records zero remaining occurrences, and the local surfaces are handed to `1ypy5`.
- [x] AC-3: The real-time checkbox rule appears in seed 180's two participant bullets only; the docs-gate sentence is present in seed 180.
- [x] AC-4: Seed 030 reads `code_patterns` at all four sites, seed 160 carries the either-spelling note, and the static pin passes.
- [x] AC-5: Seeds 210 and 160 carry the history-document wording; seeds 110 and 160 carry the dependency-line and template-block notes; every seed 160 addition sits outside the byte-pinned briefing-loop block.
- [x] AC-6: The framework suite and docs gate pass; the gate `seed_edit_allowed` is closed at the end of the change.

## Tasks

- [x] Inventory: for each edited sentence, the seed anchor (heading and neighboring sentence), every rendered surface it reaches, and every pinned test.
- [x] Open the seed gate; make the seed edits; close the gate.
- [x] Build the propagation table; record renderer-constant destinations as not propagated (renderer code remains out of scope); run `wf render-surfaces` once; add the static profile-key pin; verify the pinned tests.
- [x] CHANGELOG bullet; framework suite; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| seed-inventory | implementer | — | Anchors, reached surfaces and pinned tests before any edit. |
| seed-edits | implementer | seed-inventory | Gate open only for the edit window. |
| independent-review | required reviewers | seed-edits | Docs-contract lane reads every regenerated diff for genericity. |

## Serialization Points

- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/030-inventory-and-map.prompt.md`
- `.wavefoundry/framework/seeds/110-wave-memory-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/210-migrate-journals.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`

## Affected Architecture Docs

N/A: seed prose changes; no module boundary, flow or verification architecture changes. Regenerated surfaces under `docs/` follow from the seeds.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The gaps are the motivating defects. |
| AC-2 | required | Seed text contradicts the enforced gate. |
| AC-3 | important | Salience repair; behavior unchanged. |
| AC-4 | important | Key-name drift between a seed and its consumers. |
| AC-5 | important | Keeps seeds truthful for the sibling changes. |
| AC-6 | required | Change-local correctness and gate hygiene. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Planned from the independent Implement wave prompt review; anchors verified against the seeds and `review_evidence.py`. | Coordinator reads. |
| 2026-09-21 | Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): the retired-journal block is project prose in six role docs, not renderer output, and `memory-archive.md` is machine-regenerated, so the local move went to `1ypy5` and only the seed 210 and 160 wording stays here; `code_patterns` has no producer, so the pin is static; "immediately preceding" also lives in seed 050 and five local surfaces; seed 100 carries no checkbox copy; added the seed 209 writing-hand, `recommended_fix` and code-enumeration sentences, the seed 180 docs-gate sentence, and the seed 110 and 160 notes the sibling changes rely on. | Readiness review in this wave directory. |
| 2026-09-22 | Operator contract review: the measurement sentence now distinguishes the intended change from uncontrolled differences, requires within-run stability and qualifies rather than forbids conclusions when other substrates changed; string-reference census hits are classified update or intentionally retained; the readiness rewording preserves legacy prose-verdict and review-disabled behavior; propagation is a per-sentence table of destination and mechanism, with authored reconciliation of Wavefoundry's surfaces handed to `1ypy5` and renderer constants named or recorded as not propagated. | Operator review message. |

| 2026-09-22 | Observe: implemented canonical guidance and static profile-key check; moved new upgrade notes below the pinned carrier boundary after the carrier test detected inclusion. Seed gate closed. 132 renderer tests now pass. | seed-surface-inventory.md; focused test output. |

| 2026-09-22 | Delivery complete: all required lanes approved, 9,522-test full suite green/current, docs lint clean, retrieval after receipt passes against before with no violations or invalidation. Wave remains open pending operator close. | delivery-review.md; events.jsonl; before/after retrieval receipts. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | One sentence per gap, in the seed section that already owns the pattern. | Both failures generalize to any stack with mocks, snapshot paths or shared measurement substrates; seeds reach existing targets. | Add the text to the packaged template; reaches new installs only. |
| 2026-09-21 | Docs-gate sentence goes in seed 180, not the seed 160 trigger list. | Seed 160's carrier clause triggers on seed 180 changes; adding seed 100 to the trigger list would also change a pinned literal and the rendered upgrade prompt. | Add seed 100 to the trigger list. |
| 2026-09-21 | `code_patterns` is the profile key; seed 030 changes. | The profile and every reader use it; the `1p2q3` rename conflated the key with the MCP tool name. | Rename the profile key in every target; forbidden by the preservation rule. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A regenerated surface changes beyond the intended sentences. | Every regenerated diff is reviewed line by line by the docs-contract lane. |
| A seed sentence smuggles a Wavefoundry artifact into every target. | The docs-contract lane greps each new sentence for wave ids, wave-folder paths, test names and receipt paths. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
