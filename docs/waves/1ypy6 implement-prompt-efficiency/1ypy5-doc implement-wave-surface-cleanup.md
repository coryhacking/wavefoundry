# Implement Wave Surface Cleanup

Change ID: `1ypy5-doc implement-wave-surface-cleanup`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-21
Wave: `1ypy6 implement-prompt-efficiency`

## Rationale

Wavefoundry's rendered `docs/prompts/implement-wave.prompt.md` is a 1,902-token digest of seed 180 (utf8 bytes divided by 4) that restates the ReAct loop, the readiness handoff, builder-lane allocation, the MCP-first measurement sentence and the checkbox rule twice, duplicates what `wf_implement_wave` already returns in-band, and is missing the two sections the packaged template has and it does not: `## Completion` with exit criteria and the sentence that implementation does not authorize commit, release or closure, and the `repair_start`-before-mutation step. It carries four stale references: two renamed role names (`ui-ux-engineer`, `senior-data-engineer`), the profile key spelled `code_pattern`, and "council verdict" as the readiness authority where the typed `wave-council-readiness` approval governs declared waves.

Readiness narrowed the cuts. Three passages the first draft called restatements are carrier content that tests distribute to this surface and the packaged template and must stay: the host-neutral orchestration paragraph (`HostNeutralOrchestrationCarrierTests` requires exactly one paragraph naming seed 180 with three clauses), the readback paragraph (`BriefingLoopCarrierTests` pins ten clauses on both files), and the memory briefing sentence (seed 100 requires it on this surface and `test_memory_records.py` pins it). The two one-line pointers for the landing rule and external blockers are pinned literals in `test_docs_lint.py` and stay as they are. The realistic target is about 1,200 tokens, measured in the inventory and not pinned, because the review-policy owned region grows per wave. The claim this change makes is modest: a shorter entry prompt removes duplication and lowers entry cost; it does not by itself lower the total reading cost once an agent follows the pointers. The inventory includes a short walkthrough of a single-change implement pass with and without MCP attached, counting what is read at each step before the first edit, so the broader claim rests on a measurement rather than on the prompt's size.

Readiness also moved three LOCAL items here from the seed change. The "Operating Memory (migrated from the retired role journal, 2026-07-22)" blocks in six role docs are project prose written by the seed 210 migration, not renderer output; `docs/agents/memory-archive.md` is a machine-regenerated register that would destroy them, so they move to a new history document. The old "immediately preceding" wording lives on five local surfaces. And `docs/agents/code-reviewer.md` and `qa-reviewer.md` lack the "Tool posture" lead seed 050 asks reviewer role docs to front-load.

Separately, the packaged template `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md` lags the seed 100 rule it exists to satisfy (memory briefing, delegation rule, builder-lane allocation, docs-gate guidance). The template is missing-only, so the block reaches new installs; existing targets receive the same clauses through seed 160's carrier clause, which triggers on the sibling's seed 180 and 209 edits, and through seed 160's repo-local prompt reconciliation when seed 100 changes; neither path reads the template.

## Requirements

1. Wavefoundry's public surface (LOCAL, outside the one owned region `wavefoundry:review-policy`): keep the host-neutral paragraph, the readback paragraph, the memory briefing sentence, the landing-rule and external-blocker pointer lines, the single-OPEN pre-condition cut to one sentence, and the `## Framework Script Changes` local section with its docs-gate item reworded to apply at every completion boundary. Replace the ReAct list, the readiness-handoff restatement, the builder-lane paragraph, the MCP-first measurement sentence and the duplicate checkbox lines with a `## Execution` list of one-sentence items pointing at their seed sections (orientation with the code tools and the `retrieval_posture` directive; one readback per change; admitted scope only, marking each AC and task in the completing pass with `wf_mark_ac` and `wf_mark_task`; focused tests per change and the canonical suite before delivery review; `repair_start` before mutating and distinct fresh reverification; external-blocker escalation; builder-lane allocation and subagent delegation as one-line pointers to seed 180, because seed 100 requires the surface to carry both and seed 160 verifies the builder-lane reference at upgrade), and add `## Completion` carrying the template's exit criteria and the commit, release and closure prohibition. No `RETIRED_LIFECYCLE_TOKENS` string is introduced. The agent body `docs/prompts/agents/implement-wave.prompt.md` loses its duplicate checkbox line and old pre-condition wording.
2. Stale references (LOCAL): `frontend-developer` and `data-engineer` replace the two renamed lanes (with the note that `data-engineer` renders only when seed 050's database evidence exists); `code_patterns`; the readiness authority sentence names the typed `wave-council-readiness` approval on the current receipt; the old "immediately preceding" wording is replaced on `docs/prompts/agents/implement-wave.prompt.md`, `docs/prompts/implement-feature.prompt.md`, `docs/prompts/prepare-wave.prompt.md` (outside its owned region), `docs/agents/wave-coordinator.md` and `docs/contributing/discovery-delivery-workflow.md` with the current-typed-approval wording the sibling seed change adopts.
3. Packaged template (GENERIC, new installs): one host-conditional block under a heading such as `## When the Wavefoundry MCP is attached` carrying the memory briefing (`memory_brief(context='pre_implementation', targets=[...])` before the first edit), `wf_validate_docs` at the completion boundary, and the rule that delegated code work goes through a role-typed agent or carries the MCP-first directive; grouped so a host without MCP skips one block. The readback clauses the carrier test pins stay. The template's `## Completion` stays. Nothing names a Wavefoundry artifact or assumes Python.
4. Role-journal archive (LOCAL): the six "Operating Memory (migrated from the retired role journal, 2026-07-22)" blocks (`wave-coordinator.md`, `implementer.md`, `planner.md`, `guru.md` outside its owned regions, `personas/wave-coordinator.md`, `personas/framework-operator.md`) move verbatim into a new `docs/agents/history/operating-memory-2026-07-22.md` with one section per source role; the residue census in `test_events_only_residue_census.py` gains the heading in a TEST-LOCAL token tuple scanned over `docs/agents` recursively, with a count-bounded allowance for the history document; the production `RETIRED_LIFECYCLE_TOKENS` tuple (shipped to every target's lint and upgrade reconciler) is not touched. The history document carries the `Role:` and `Category:` metadata the docs gate requires of every file under `docs/agents`.
5. Reviewer role docs (LOCAL): `docs/agents/code-reviewer.md` and `qa-reviewer.md` gain the short "Tool posture" lead seed 050 specifies, placed outside owned regions.
6. Tests: `test_docs_lint.py` (`test_prompt_surfaces_and_role_docs_are_reconciled`, the two pointer literals: kept, so no edit), `test_render_agent_surfaces.py` (`BriefingLoopCarrierTests`, `HostNeutralOrchestrationCarrierTests`: kept content, so no edit), `test_memory_records.py` (`test_implement_prompt_requires_the_briefing`: kept), `test_events_only_residue_census.py` (gains the test-local heading token and the history-path allowance). The prompt-surface manifest carries no content digest and is unchanged. After the edits, `wf render-surfaces` produces no diff in the owned region and no diff to the hand-edited prose; the docs gate is clean.

## Scope

**Problem statement:** the local surface is longer than it needs to be, lacks its own exit criteria and carries stale names; six role docs carry retired journal payload on the per-wave read path; the packaged template lacks the block the seed rule requires.

**In scope:** `docs/prompts/implement-wave.prompt.md` and its agent body outside owned markers; the five local surfaces with the old pre-condition wording; the six role docs and the new history document; the two reviewer role docs; the packaged template; the residue census test; CHANGELOG bullet.

**Out of scope:** seeds (sibling enhancement); tools (sibling bug); any other lifecycle prompt beyond the named sentences; `memory-archive.md` (machine-regenerated, never hand-edited).

## Acceptance Criteria

- [x] AC-1: The rendered surface carries `## Execution` and `## Completion`, the named restatements are gone, the four carrier passages and two pointer literals remain, and the measured size is recorded in the inventory (target about 1,200 tokens, not pinned).
- [x] AC-2: No stale reference remains on the surface or the five named local surfaces; every tool, role, key and path named resolves against the tree, allowing the conditional role wrappers.
- [x] AC-3: The packaged template carries the host-conditional block and `## Completion`, keeps the pinned readback clauses, names no Wavefoundry artifact, and reads correctly for a target without MCP.
- [x] AC-4: The six role-journal blocks live verbatim in the history document and in no live role doc; the residue census pins the heading with a test-local token and the history-path allowance, and `RETIRED_LIFECYCLE_TOKENS` is unchanged.
- [x] AC-5: The two reviewer role docs carry the Tool posture lead; owned regions are unchanged after re-render; docs gate clean; manifest content unchanged (gardener timestamp only); the named tests pass without edits except the census.

## Tasks

- [x] Inventory: every sentence on the surface classified as keep, cut, move-to-pointer or reword, with its seed owner and pinning test; the six journal blocks and their byte counts; the with-and-without-MCP read walkthrough; the authored reconciliation of Wavefoundry's own surfaces for the sibling's new seed sentences, per its propagation table.
- [x] Rewrite the surface and the agent body; fix the stale references on the five local surfaces.
- [x] Move the journal blocks to the history document; add the census token; add the Tool posture leads.
- [x] Add the template block; re-render; docs gate; CHANGELOG bullet; required delivery review (docs-contract lane reads every diff).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| surface-inventory | technical-writer | — | Sentence classification before any edit. |
| surface-rewrite | technical-writer | surface-inventory | Local surfaces, role docs, history document, packaged template. |
| independent-review | required reviewers | surface-rewrite | Docs-contract lane required. |

## Serialization Points

- `docs/prompts/implement-wave.prompt.md`
- `docs/prompts/agents/implement-wave.prompt.md`
- `docs/prompts/implement-feature.prompt.md`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/agents/wave-coordinator.md`
- `docs/agents/implementer.md`
- `docs/agents/planner.md`
- `docs/agents/guru.md`
- `docs/agents/personas/`
- `docs/agents/history/`
- `docs/agents/code-reviewer.md`
- `docs/agents/qa-reviewer.md`
- `docs/contributing/discovery-delivery-workflow.md`
- `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_events_only_residue_census.py`

## Affected Architecture Docs

N/A: prompt and role-doc prose only; no boundary, flow or verification architecture changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The entry-cost and duplication reduction is the change; total read cost is measured by the walkthrough, not claimed. |
| AC-2 | required | Stale names misdirect lane allocation; stale gate wording contradicts the tools. |
| AC-3 | important | Reaches new installs only. |
| AC-4 | important | Per-wave read cost; content preserved. |
| AC-5 | required | Owned regions and pinned carriers must survive a hand edit. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Planned from the independent Implement wave prompt review; sizes measured as utf8 bytes divided by 4; template diff and stale names verified against the tree. | Coordinator reads of the surface, the template and `docs/repo-profile.json`. |
| 2026-09-21 | Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): three "restatements" are pinned carrier content and stay (host-neutral paragraph, readback clauses, memory briefing); the two pointer literals are pinned; there is no context-efficiency carrier on this file; the size is measured not pinned; the role-journal archive, the five old-wording surfaces and the Tool posture leads moved here from the seed change; seed 160's carrier clause reaches existing targets through the sibling's seed 180 and 209 edits, not the template. | Readiness review in this wave directory. |
| 2026-09-22 | Operator contract review: the efficiency claim is stated modestly (entry cost and duplication, not total read cost) and backed by a with-and-without-MCP read walkthrough in the inventory; this change owns the authored reconciliation of Wavefoundry's own surfaces for the sibling's new seed sentences. | Operator review message. |

| 2026-09-22 | Observe: implemented the scoped local cleanup; preserved host/readback/memory and landing/blocker carriers; moved six trailing journal blocks byte-for-byte. Initial lint corrected archive Role/Category metadata. The operator-facing readback described these edits before they ran; this written progress entry is recorded after the edit, not claimed as prior evidence. | seed-surface-inventory.md; focused test output. |

| 2026-09-22 | Delivery complete: all required lanes approved, 9,522-test full suite green/current, docs lint clean, retrieval after receipt passes against before with no violations or invalidation. Wave remains open pending operator close. | delivery-review.md; events.jsonl; before/after retrieval receipts. |
| 2026-09-22 | Independent objective evaluation found three residual stale strings inside this change's scope (`code_pattern` on the implement-feature surface and its agent body; the wave-coordinator role doc's council-verdict output line) and a manifest gardener-timestamp change; all three strings corrected, AC-5 wording clarified. | Coordinator edits; docs gate rerun. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Pointers to seed sections instead of restated text, except pinned carrier passages. | Seed 020 forbids restating the exploration order downstream; the tool carries the posture directive in-band; the carrier tests own what they pin. | Keep the digest; twice the read cost for no consumed output. |
| 2026-09-21 | New history document, not `memory-archive.md`. | The archive register is regenerated from typed records on every archive or upgrade and would drop the prose. | Typed memory records; disproportionate for historical prose. |
| 2026-09-21 | Template block is host-conditional under one heading. | A host without MCP skips one block. | Inline conditionals. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A cut sentence was load-bearing for a host without seed access. | Every cut is classified against its seed owner and pinning test in the inventory; nothing is cut that has no seed owner. |
| Re-render rewrites the owned region differently. | AC-5 requires a no-diff re-render. |
| `guru.md` edit touches a renderer-owned region. | The move stays outside the marker regions; the re-render check covers it. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
