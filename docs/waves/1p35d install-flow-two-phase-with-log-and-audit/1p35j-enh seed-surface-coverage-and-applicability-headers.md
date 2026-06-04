# Seed Surface Coverage And Applicability Headers

Change ID: `1p35j-enh seed-surface-coverage-and-applicability-headers`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-03
Wave: `1p35d install-flow-two-phase-with-log-and-audit`

## Rationale

The downstream agent reported that `seed_get` and `docs_search` failed to locate roughly half the seed catalog — seeds 216, 222–224, 226–229, 232 were unreachable via MCP and had to be read directly from disk. They flagged this as the **highest-impact** item in their feedback. The framework's own [[seed-first doc workflow]] memory establishes that seeds are the source of truth and consumers should be able to retrieve them by number or name; an MCP catalog that covers only half is structurally broken.

Adjacent gaps from the same retrospective:

- Specialist seeds (especially 231, 234, 235) lack an `Applicable when:` line at the top; the evaluating agent has to read the full body to determine non-applicability. A one-line header at the top of every specialist seed lets the agent skip in 10 seconds instead of 2 minutes.
- Seeds 175 (interrogate-plan) and 176 (evaluate-decision) lack `docs/prompts/*.prompt.md` public-prompt entries in installs; shortcut phrases for these don't resolve.
- Seed-210 (journal distillation) has no public-prompt shortcut at all; the maintenance verb is invisible without manually invoking it.
- Seeds 180 and 211 reference a `code_navigation_hints` MCP tool that doesn't exist in the live surface. Ghost references confuse agents and trigger the wave_audit coherence finding.
- Seed-050 (agent entry bootstrap) doesn't reference the authoritative per-role seeds (214, 215, 216, 221–225, 236). Agents writing role docs from seed-050's generic template produce shallower content than the authoritative seeds would. **Includes seed-236 (archetype-council)**: a downstream consumer's install produced a thin "text-only review" archetype-council role doc, missing the broader-scope framing that lives in seed-236 (general-purpose lenses for plans, design docs, code, prose, decision narratives, naming, AC formulation).

These are all seed-surface issues — content, coverage, and reachability. Bundled here as a single change because they share the same surface and a single delivery-council pass can cover them.

## Requirements

1. **Seed catalog coverage in `seed_get` and `docs_search`.** All seeds under `.wavefoundry/framework/seeds/*.prompt.md` are reachable via `seed_get(<number>)` and discoverable via `docs_search(query, layer="framework")`. No silent absence.
2. **Diagnostic when `seed_get` is called with an absent number.** Returns the closest matches (Levenshtein or numeric proximity) so the agent can recover.
3. **`Applicable when:` line at the top of every specialist seed** under 220–239 plus any other specialist range. Format: a single line, immediately after the title, e.g., `**Applicable when:** project uses LLMs, RAG pipelines, or prompt engineering` (seed-231) or `**Applicable when:** project has automation, CI/CD, or workflow orchestration` (seed-234).
4. **Public prompts for seeds 175 and 176.** `docs/prompts/interrogate-plan.prompt.md` and `docs/prompts/evaluate-decision.prompt.md` (or the equivalent paths after a project's prompt-surface bootstrap runs) get generated from their seeds during the standard prompt-surface bootstrap (seed-100). Shortcut phrases resolve correctly.
5. **Public-prompt shortcut for seed-210 (journal distillation).** Added to the framework default prompt surface as `Distill journals` (or operator-chosen verb). Maintenance verb becomes discoverable.
6. **Resolve ghost `code_navigation_hints` references in seeds 180 and 211.** Decide: (a) the tool was renamed → update references to the current name; (b) the tool was planned but never landed → remove references; (c) it should exist → add it. Investigation drives the decision; the wave doc captures it.
7. **Seed-050 references authoritative per-role seeds.** Adds an explicit "for richer role content, see the per-role authoritative seeds:" pointer list — 214 (architecture-reviewer), 215 (wave-council), 216 (reality-checker), 221 (code-reviewer), 222 (software-engineer), 223 (frontend-developer), 224 (data-engineer), 225 (red-team), **236 (archetype-council)**. Agents generating role docs from seed-050 know to pull from these. Seed-050 must explicitly instruct: "for the three councils (red-team, wave-council, archetype-council), read seeds 225/215/236 IN FULL and preserve their protocol details, seat composition, swap-ins, and broader-scope framing — do not generate a thin generic template."
8. **Tests verify that `seed_get(<number>)` returns content for every numbered seed file in `.wavefoundry/framework/seeds/`.** Single test pattern: enumerate, attempt retrieval, assert non-empty. Catches future seed additions that bypass the catalog.
9. **CHANGELOG entry describes the seed-surface improvements** as part of the 1.5.0 entry.

## Scope

**In scope:**

- Diagnose root cause of `seed_get` / `docs_search` half-coverage (likely an index-build gap or a name-pattern mismatch); fix
- Add `Applicable when:` headers to all specialist seeds (220–239 range + any other specialist seeds)
- Generate public prompts for seeds 175 and 176 in seed-100's output set
- Add public-prompt shortcut for seed-210
- Investigate ghost `code_navigation_hints` and apply the chosen resolution
- Update seed-050 with authoritative-seed pointers
- Coverage test for `seed_get`

**Out of scope:**

- Rewriting the underlying seeds 175, 176, 210 themselves (they exist; only their public-prompt exposure is missing)
- Per-project seed customization (`Applicable when:` is universal framework-level metadata)
- New seed authoring (we're surfacing existing seeds, not adding new ones)
- Dashboard changes to surface seed coverage (separate concern)

## Acceptance Criteria

- [x] AC-1: Root cause for `seed_get` / `docs_search` half-coverage is identified and documented inline in the Decision Log.
- [x] AC-2: `seed_get(<number>)` returns content for every seed file in `.wavefoundry/framework/seeds/*.prompt.md`. Verified by a generative test.
- [x] AC-3: `seed_get` on a non-existent number returns a clear error including closest-match suggestions.
- [x] AC-4: Every specialist seed (220–239 range) has an `Applicable when:` line immediately after the title, single line, bolded label.
- [x] AC-5: Specialist seeds outside 220–239 (if any) also gain the same header.
- [x] AC-6: Seed-100 (project-prompt-surface-bootstrap) instructs the agent to generate `docs/prompts/interrogate-plan.prompt.md` and `docs/prompts/evaluate-decision.prompt.md` from seeds 175 and 176.
- [x] AC-7: Seed-100 instructs the agent to add a `Distill journals` shortcut entry for seed-210.
- [x] AC-8: AGENTS.md shortcuts table in the framework default surface includes `Distill journals` pointing at seed-210.
- [~] AC-9: Ghost `code_navigation_hints` references in seeds 180 and 211. **Not applicable — false-positive coherence finding.** Investigation confirmed `code_navigation_hints` is NOT a tool — it's a `docs/workflow-config.json` config schema block, referenced correctly in seeds 180/211 as a parameter value: `code_keyword(queries=<project.code_navigation_hints.guard_tokens>, glob="<file>")`. The wave_audit coherence-finding diagnostic misclassified the parameter as a tool name. No change to seeds 180/211 needed; the recipes work correctly when the workflow-config block exists (and degrade gracefully when it doesn't, per seed-211's documented contract).
- [x] AC-10: Seed-050 includes an explicit "Per-role authoritative seeds" pointer block listing 214, 215, 216, 221, 222, 223, 224, 225, 236; AND a bolded instruction that for the three councils (red-team, wave-council, archetype-council) the agent MUST read seeds 225, 215, 236 in full rather than generating thin generic templates.
- [x] AC-11: CHANGELOG 1.5.0 entry includes a bullet describing the seed-surface improvements (coverage, applicability headers, ghost-tool resolution, seed-050 references).
- [x] AC-12: docs-lint passes.
- [x] AC-13: Full framework test suite passes.

## Tasks

- [x] Open `seed_edit_allowed` and `framework_edit_allowed` gates
- [x] Diagnose `seed_get` coverage gap (read indexer + seed loader paths; identify which seeds are excluded and why)
- [x] Implement the fix (likely an index-build inclusion change or a name-pattern resolver)
- [x] Add closest-match diagnostic to `seed_get`
- [x] Audit specialist seeds (220–239) for missing `Applicable when:` headers; add to each
- [x] Verify no other specialist seeds outside 220–239 are missing the header
- [x] Update seed-100 to generate seed-175, 176, and 210 public-prompt surfaces
- [x] Add `Distill journals` to the AGENTS.md framework default surface
- [x] Investigate `code_navigation_hints` references; document resolution and apply
- [x] Update seed-050 with authoritative-seed pointer block
- [x] Add generative test for `seed_get` coverage
- [x] Update CHANGELOG 1.5.0 entry
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close gates

## Affected Architecture Docs

`N/A` — content and coverage improvements to existing surfaces. No boundary or component changes.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (root cause documented) | required | Without root cause, fix is speculative. |
| AC-2 (coverage test passes) | required | The downstream agent's #1 highest-impact item. Hard regression gate. |
| AC-3 (closest-match diagnostic) | required | Agent recovery path when seed numbers are mis-remembered or refactored. |
| AC-4 (Applicable when on 220–239) | required | The 2-min-vs-10-sec evaluation cost matters at install time. |
| AC-5 (Applicable when outside 220–239) | required | Coverage. |
| AC-6 (seed-175, 176 public prompts) | required | Shortcut phrases don't resolve without these. |
| AC-7 (seed-100 generates seed-210 shortcut) | required | Maintenance verb needs an install-time creation step. |
| AC-8 (AGENTS.md surface includes `Distill journals`) | required | Shortcut not in the surface table = not invocable. |
| AC-9 (ghost tool resolved) | not-this-scope | Investigation showed `code_navigation_hints` is a real workflow-config schema, not a ghost tool — the original coherence finding was a parameter-vs-tool-name misclassification. |
| AC-10 (seed-050 references including 236; council read-in-full instruction) | required | Shallow generic role docs vs richer authoritative content; downstream archetype-council role doc was thinner than seed-236. |
| AC-11 (CHANGELOG) | required | Discoverability for consumers upgrading. |
| AC-12 (docs-lint passes) | required | Standard hygiene. |
| AC-13 (framework test suite passes) | required | Regression discipline. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Bundle 6 seed-surface improvements as one change | All touch the same surface (seeds + prompt catalog); a single delivery-council pass covers them coherently; splitting would produce 6 micro-changes with redundant ceremony. | 6 separate changes — rejected; ceremony cost without delivery benefit. |
| 2026-06-03 | Investigate `code_navigation_hints` rather than guess the resolution | The right fix depends on what the references intended. Resolution captured at implementation in Decision Log. | Pick a resolution up-front — rejected; risks shipping the wrong fix. |
| 2026-06-03 | Generative test for seed coverage (enumerate-and-assert) | Catches future seed additions that bypass the catalog without having to hand-list every seed in tests. | Hand-listed test fixture — rejected; future seeds get missed silently. |

## Risks

| Risk | Mitigation |
|---|---|
| Root cause of seed coverage gap is in the BGE embedding step (some seeds don't get indexed by the embedder) | Coverage test catches this regardless of root cause. Investigation surfaces whether it's index-build, name-pattern, or embedder filtering. |
| Adding `Applicable when:` to specialist seeds breaks downstream agents that expect the old structure | Header is additive; existing structure unchanged. Risk is low. |
| `code_navigation_hints` was a tool we genuinely need but never landed; resolution = "remove" might be wrong | Investigation specifically checks: was there design discussion, was it referenced in roadmap docs, what behavior does the seed assume. If genuinely missing functionality, the change escalates a follow-on wave. |
| Seed-050 authoritative-seed pointers drift if a new role seed is added | Drift is mechanically catchable by docs-lint (could check that every authoritative role seed appears in seed-050's pointer block); deferred to a follow-on. |

## Related Work

- **`1p35f` (install log + entry doc)** — install log rows reference seeds. If `seed_get` coverage is broken, the agent following the log can't retrieve seeds. This change is a prerequisite for the install log working end-to-end.
- **Seed-100 (project-prompt-surface-bootstrap)** — emits public prompt files per seed; updates needed for seeds 175, 176, 210.
- **Seed-050 (agent-entry-bootstrap)** — generates role docs; updated with authoritative-seed pointers in this change.

## Session Handoff

Admitted to `1p35d` as a parallel-with-C4 content change. Sequenced after `1p35f` and `1p35h` (install log + audit tool) because the install log will reference seeds that this change makes reliably retrievable.
