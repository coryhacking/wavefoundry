# Capture implementation decisions for the next engineer

Change ID: `241lq-doc capture-implementation-rationale-for-walkthroughs`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-22
Wave: 241lr implementation-rationale-handoff

## Rationale

A diff shows which approach shipped. By delivery review, the engineer who chose it may have moved on. Explain already asks why the team chose the approach, what proved it worked and what remains open. Implement provides a place to record those answers but gives little direction about when they matter.

## Product Intent

A maintainer taking over one spec can explain a consequential choice, find the evidence for it and act on the remaining work without asking the original implementer. A routine fix still needs only its ordinary completion entry. AC-1 and AC-3 verify the published instructions. Assess their effect on real work after several waves.

## Requirements

1. During single-spec and wave implementation, ask what the next engineer needs that the diff and tests cannot reliably tell them. Record that information in the affected spec when the choice or discovery occurs. In the Decision Log, name the constraint, the actual alternative considered when one exists, and the consequence of the choice. Apply this to algorithms, dependencies, architecture, performance or security when relevant.
2. In the Progress Log, record an issue that changed the work, how the team addressed it, and what observation demonstrated the result. For a remaining compromise or TODO, record the next action, owner or revisit condition when known. Link existing evidence once. Changes to requirements or acceptance still follow the existing amendment process.
3. On request, Explain may walk through an in-progress spec. Distinguish verified behavior, planned work and unknowns. Keep the existing optional Review offer. Routine fixes need no extra entry or walkthrough.

## Scope

The implementer updates canonical Implement and Explain guidance and reconciles the self-hosted prompts. QA and docs reviewers inspect the delivered instructions and the retrospective trigger. Preserve existing record headings, MCP contracts, approvals and closure behavior. The guidance applies by default wherever the framework delivers Implement and Explain. This change adds no artifact, gate, automated writer or required invocation.

## Acceptance Criteria

- [x] AC-1: Both implementation entry points give the same recording guidance. An in-progress Explain walkthrough distinguishes executed checks from planned checks.
- [x] AC-2: Publish a retrospective instruction with a concrete trigger. After the first five completed waves using the guidance, a maintainer samples their specs, including routine fixes when available. Report which choices have a traceable reason, what evidence distinguishes verified work from open checks, and where notes duplicate the diff or leave a handoff unclear. Cite examples and recommend keeping or adjusting the guidance. Report limited evidence when a case is absent. This later analysis does not gate adoption, delivery or closure.
- [x] AC-3: Inspect the delivered instructions for a routine fix. They permit the ordinary completion entry and preserve the optional walkthrough. No exercise or paired trial is required to ship.

## Tasks

- [x] Update the canonical guidance and reconcile the corresponding project prompts.
- [x] Check the rendered single-spec, wave and Explain instructions, validate docs and record where maintainers will find the retrospective trigger.

## Agent Execution Graph

The implementer updates the standard instructions. Independent review checks the published guidance and the retrospective trigger.

## Serialization Points

- `.wavefoundry/framework/seeds/180-implement-spec.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/explain.prompt.md`
- `docs/prompts/implement-spec.prompt.md`, `docs/prompts/implement-wave.prompt.md`, `docs/prompts/explain.prompt.md`

## Affected Architecture Docs

N/A. The guidance uses existing records, tools and review authority.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Both implementation paths serve maintainers. |
| AC-2 | required | Assign a later assessment using completed work. |
| AC-3 | required | Routine work stays proportionate. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-22 | Initially proposed a pilot. The operator subsequently chose immediate adoption and a retrospective after several waves. | Current Implement and Explain prompts. |
| 2026-11-22 | Implemented. Seed 180 owns the guidance under the `Rationale for the next engineer:` label, placed after **Readback before editing**, and the trigger under **Retrospective on rationale records**: five waves closed after the project installs the release carrying this guidance. Implement spec and Implement wave (install template and self-hosted copy) carry the same pointer paragraph; Explain (install template and self-hosted copy) adds the in-progress walkthrough paragraph under **Choose the delivery**. The renderer does not carry this prose, so the `docs/prompts/` copies were hand-merged. No existing sentence changed. `BriefingLoopCarrierTests.test_each_carrier_independently_satisfies_contract_and_matches` first failed because the readback block in each carrier ran on into the new paragraph and the carriers then differed; the new guidance now opens with the plain label line `Rationale for the next engineer:`, which ends that block in seed 180 and Implement spec, and the test passes. The existing Review offer, record headings and approvals are untouched. | Focused `run_tests.py --file` runs green: test_compact_review_artifacts, test_docs_lint, test_language_guidance, test_reconcile_scan, test_render_platform_surfaces, test_shipped_reference_docs, test_vocabulary_prompt_names, test_work_area_wording, test_lifecycle_baseline_drift, test_review_policy, test_server_tools_lifecycle, test_render_agent_surfaces (after the label fix); `wf_validate_docs` passed. |
| 2026-11-22 | Gapfill: retrieval used shell `grep`/`sed` on the four prompt files and the test directory instead of `code_keyword`/`code_read`, because the edit targets were already known by path and the pin check needed an exhaustive literal grep across tests. | Implementer session. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-22 | Capture material facts in the existing spec and explain them on demand. | Planner default based on the operator's goal of retaining rationale during implementation. | A walkthrough after every spec repeats routine evidence. Waiting until Review loses the rationale when the implementer moves on. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A checklist encourages invented alternatives or unsupported claims. | Omit empty categories and identify unmeasured effects. Use examples from actual waves and identify sampling limits. |

## Session Handoff

Admitted to wave 241lr for readiness review. The operator directed standard adoption and later analysis. Five completed waves is the planning default for “several”.
