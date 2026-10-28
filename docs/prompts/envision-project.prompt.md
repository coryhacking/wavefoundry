# Envision Project

Owner: Engineering
Status: active
Last verified: 2026-10-28

**Applicable when:** any project. Establish or revise its enduring vision and technical horizons. This is an authoring workflow, not implementation planning or autonomous execution.

**Shortcut:** `Envision project` · **Skill:** `wf-envision`

Turn an intended future into a grounded vision and a credible progression of capabilities. The vision establishes purpose; horizons explain how technical foundations enable it; later changes and waves deliver bounded increments.

## Scope and output

Default output is `VISION.md` at the repository root, titled `<Project>: Vision and Technical Horizons`. Honor an existing canonical location or an explicitly requested filename. Preserve valid existing content and operator edits. A discussion, prompt-writing request or explicit read-only review does not authorize writing a vision or review file: return the requested advice in the conversation instead.

Invoking this authoring workflow includes architecture review, a red-team challenge and Archetype Council on a new or substantially revised vision. The operator may narrow or omit reviews; state the scope actually performed. Minor edits use affected reviews proportionately rather than automatically rerunning every seat. These are advisory artifact reviews, not lifecycle gates. This workflow creates no wave, implementation backlog, deployment, commit or publication, and grants no implementation or approval authority.

## 1. Establish the brief

Reuse the conversation, existing vision and project context. Establish the beneficiary, ultimate outcome, ambition, planning horizon, constraints and deliverable. Ask only for missing decisions that materially change the vision; do not repeat an answered interview. State reversible assumptions and preserve unresolved strategic choices as open questions.

A twelve-month horizon and unlimited resources are optional brief parameters, not defaults. Do not impose autonomous agents, cloud services, a business model or a fixed number of horizons on unrelated projects. Use only the target project's brief; do not import a personal skill's founding narrative or another project's ambitions.

## 2. Ground the starting point

Follow the target repository's instructions and investigation workflow. Where Wavefoundry retrieval is configured for that target, use Guru and indexed retrieval, then validate load-bearing claims against current source. Confirm a delegated worker's actual tool access. If target-scoped MCP retrieval is unavailable, use targeted local inspection and disclose the evidence gap; an index attached to a different repository is not evidence for this target.

Inspect the existing vision, project orientation, architecture, operating constraints and implementation relevant to the direction. Use focused safe checks where an executable claim matters. Distinguish verified capabilities, partial foundations, new engineering and unresolved research. Historical plans, passing record validation and confident prose do not prove shipped behavior. Do not run unrelated suites, setup or environment changes merely to author the vision.

Identify tensions between the destination and today's architecture or product boundary. Explain the transition and future decision needed; neither silently change the current contract nor treat it as an eternal limit on ambition.

## 3. Draft the vision and horizons

Write a coherent argument connecting the beneficiary's future experience to technical foundations and measurable outcomes. Adapt headings and depth to the project; the following is a content contract rather than a rigid template.

- **Purpose and lived experience:** enduring purpose, beneficiary, consequential outcome and a concrete end-to-end scenario. Explain what people do, what the system does, where human judgment remains and what is received. Separate durable principles from current rules the vision proposes to revisit.
- **Starting point:** concise repository citations for relevant current capabilities, their verification limits and the distance to the destination. Label proposals and research explicitly. If source and documentation conflict, state the consequence for the roadmap.
- **Technical horizons:** choose meaningful capability thresholds, not arbitrary calendar quarters or team boundaries. For each, state the unlocked experience, technical foundations (components, contracts, state ownership, interfaces and instrumentation), prerequisites, an end-to-end demonstration, measurable exit criteria and independent judge, failure conditions, uncertainties and useful intermediate value if later horizons never arrive. An unchanged baseline must fail the new capability demonstration. Explain how each foundation enables what follows.
- **Architecture and evolution:** show components and data flow when a compact diagram helps; distinguish existing from proposed components. Name sources of truth, trust boundaries, execution locations and integration contracts. Keep unresolved design choices visible rather than accidentally committing to them.
- **Sequencing and investment:** dependencies, opportunities for parallel work, critical path and research bets. Dates express aspirations; exit evidence establishes completion. If resources are unlimited, explain what more experiments or specialists buy and which bottlenecks remain. Avoid inventing a year's worth of tickets.
- **Evaluation:** measure beneficiary outcomes, reliability, total cost and maintenance burden. Define baselines, representative cases, independent assessment and observation windows as appropriate. Count failures, abandonment, human rescues and delayed regressions; distinguish targets from measured results. For agentic systems, also assess evidence quality and separation of evaluator from evaluated system. Activity counts are not success measures.
- **Hard questions and next investment:** assumptions most likely to invalidate the vision, the cheapest meaningful experiments to resolve them, a compelling ultimate demonstration and the next bounded investigation or change to consider.

## 4. Review one identified draft

The author coordinates review but does not impersonate independent reviewers. Give each worker the same identified draft (path and revision or content fingerprint), brief, evidence sources, write boundaries and relevant unresolved questions. Reviewer work is read-only against source and the vision. Parallel independent reads are useful; serialize revisions so reviewers know which draft they judged.

Use the target's canonical role and prompt documents. The installed seeds provide a fallback when a project omits a local role or command; this does not require enabling a role, changing configuration or installing anything:

| Review | Canonical instructions | Focus on the vision |
| --- | --- | --- |
| Architecture | `docs/agents/architecture-reviewer.md` (or the project's actual architecture-reviewer role); fallback `.wavefoundry/framework/seeds/214-architecture-reviewer.prompt.md` | Current-state accuracy, foundations, dependency order, ownership, interfaces, trust boundaries and feasible transition. Flag assumptions and decisions, while preserving the requested ambition. |
| Red-team | `docs/prompts/red-team-review.prompt.md` and `docs/agents/specialists/red-team.md`; fallback seeds `177-red-team-review.prompt.md` and `225-red-team.prompt.md` | Strongest failure modes, unsupported bets, simpler or stronger alternative, and what would disprove the promised outcome. Select a standalone lens appropriate to this vision and preserve the canonical output shape. |
| Archetype Council | `docs/prompts/archetype-council.prompt.md`, full protocol `.wavefoundry/framework/seeds/236-archetype-council.prompt.md`, and `docs/agents/specialists/council-chair.md` (fallback seed `215-council-chair.prompt.md`) | Strategic positioning, reader readiness, testable claims, durability and simplicity across horizons. The chair declares seats/swaps, runs isolated axes and synthesizes the actual outputs under the canonical protocol. |

Architecture and standalone red-team may run independently on the draft. Then the council-chair conducts Archetype Council; its optional primer may reuse the actual red-team output for this same draft. Follow seed 236's axis-before-reading, isolated seats, synthesis, red-team closing reconciliation and falsification check. Do not clone its schemas or substitute one author's five paragraphs for five independent seats. Report context sharing and actual coverage honestly.

**Artifact-only boundary:** instructions about delivery-wave records in generic role documents apply when performing that lifecycle. Here, do not call Prepare, Review wave or review-approval tools, create wave records or write `council-readiness`/`council-delivery` approvals. A vision review does not replace required specialist or Wave Council approval for later implementation. Credible security issues go to the appropriate specialist; red-team does not issue security signoffs.

**Capability limit:** if independent workers, required instructions or a review capability are unavailable, continue useful authorized drafting or advice. Label any author self-check as such, identify the missing review and leave that outcome pending. Never claim it passed, silently relabel the author as a reviewer, or reconfigure the host to make it available. If a review is explicitly omitted by the operator, record that scope without pretending it ran. A draft with pending review remains usable but is not described as independently reviewed in those areas.

## 5. Reconcile, validate and deliver

Collect the initial findings before editing. Apply the canonical review dispositions and explain material decisions; correct factual errors, broken sequencing and unsupported claims. Preserve genuine research uncertainty and operator-owned strategic choices as open questions instead of inventing resolution. Incorporate accepted improvements into the vision, not merely an appended verdict.

Use one initial review pass, one bounded author repair pass and one focused verification by affected reviewers. At that boundary, report remaining actionable findings and decisions rather than starting an automatic review loop or claiming convergence. A material change of direction may need a new brief and review scope; obtain that decision before proceeding with dependent work.

Keep a compact review section in the vision (or the project's existing linked review location): draft identity, reviews/axes actually run, verdicts, material finding dispositions, incorporated changes, unresolved decisions and unavailable/omitted coverage. Keep routine seat transcripts temporary; retain the evidence needed to understand material conclusions. For read-only requests, this record stays in the response and no file changes occur.

Check citations, links, prerequisite order and the horizon content contract. Run applicable documentation validation: with target-scoped Wavefoundry MCP use `wf_validate_docs`; without it use the project's supported docs check (Wavefoundry CLI: POSIX `./.wavefoundry/bin/wf docs-lint`, native Windows `.\.wavefoundry\bin\wf.cmd docs-lint`). Fix introduced defects and report unrelated failures without widening scope. Passing docs lint proves document consistency, not that the future capabilities exist.

Return the document path or requested read-only advice, central direction, horizon sequence, actual review outcome and material open decisions. Recommend the next bounded investment without automatically creating plans or starting work.
