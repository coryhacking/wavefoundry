# Envision: focused feedback before final verification

Change ID: `226i1-enh envision-focused-feedback-loops`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-31
Wave: 228dy envision-focused-feedback

## Rationale

Envision should help people establish a compelling product destination and a credible long-horizon path, with feedback arriving while it can still change the argument. The operator requested a few useful loops during Envision, then authorized this plan.

Tensorwell and Solaris reports describe authors polishing a familiar or assumed direction before fully understanding the operator's intended future. Later conversations changed beneficiaries, priorities or product boundaries; source checks changed roadmap assumptions. These are operator-supplied reports and author self-assessments, not independently reproduced comparisons. Several reported gaps have since received guidance.

Current seed 179 already requires concrete alternatives, guided consequential decisions, a unified opening paragraph, capability validation and backward planning. Its review companion requires one initial pass, one bounded repair and affected-reviewer verification. The proposed delta is an early statement discussion, explicit targeted return paths, and a staged reader reconstruction before that repair boundary. More iterations, reviewers or words are not success measures.

## Product Intent

Help an operator and author reach a vision whose purpose, ambitious destination and beneficiary value are clear, whose useful stages survive consequential feedback, and whose next advance a reader can understand without the author's explanation. The observable outcome is earlier correction of mistaken direction or meaning, carried through the roadmap without restarting everything. AC-2 through AC-4 test that intent and its limits.

This supports the adopted [vision's Horizon 3](../../../VISION.md#horizon-3--executable-intent-and-sustained-missions): exposing consequential human decisions while handling routine work. It is an authoring improvement, not delivery of a mission runtime or acceptance of the vision's still-proposed entry change. Preserve the product destination, technical and nontechnical roadmap, single-document default and operator-owned adoption.

## Requirements

1. **Target the affected reasoning.** Organize three feedback opportunities—destination, roadmap and understanding—inside existing phases. Each identifies its input, consequential mismatch, affected revision and stopping condition. Return only when there is a concrete correction, new evidence or unresolved consequential choice. Do not require three full workflow executions, a fixed iteration count or repeated self-critique without a new basis.
2. **Discuss the destination early.** After fair exploration when needed, draft the unified paragraph before polishing the long document: enduring purpose, intended future, beneficiary value and selected/provisional status. Use it in the existing guided conversation; reflect the actual answer in the paragraph and dependent roadmap. Reuse settled choices without another approval. Honor draft-first/no-interview requests and defer evidence-dependent choices with a useful test. Silence is not selection. Do not reopen ambition by rote or blend incompatible futures to avoid a decision.
3. **Repair the path from evidence.** Work backward from the destination; inspect capability classifications, unresolved breakthroughs, dependencies and useful intermediate outcomes. Resolve consequential conflicts through targeted checks or explicit uncertainty. Propagate new evidence into affected prerequisites, sequence or immediate advances while preserving unaffected work. Technical and nontechnical dependencies count. A changed destination, beneficiary, responsibility or commitment returns to the operator; missing proof alone does not justify shrinking ambition.
4. **Check understanding before repair.** When independent review is selected and available, stage the check within one selected product-strategy or domain/workflow review in a fresh context. First provide the opening alone and request its meaning; then provide the roadmap overview and request the next advance, its connection to the destination and main uncertainty. Retain these answers before supplying the full brief, explanations or judging criteria for ordinary role review. Do not coach reconstruction. Preserve applicable role protocols; add no fifth reviewer or council. If agreed scope excludes an appropriate independent reader or capability is unavailable, disclose the omission and any author self-check without inventing independence or expanding scope.
5. **Share one repair boundary.** Collect understanding findings with the other initial role findings before the existing bounded author repair. Affected reviewers verify that identified revision, including passages changed to repair meaning. Do not grant each feedback opportunity its own review/repair allowance. Early drafting and operator conversation precede this boundary; after verification, report remaining substantive findings rather than automatically repairing again. Later operator-authorized revisions require accurate new coverage. Stop when the mismatch is resolved, feedback adds no material information, or progress needs an operator decision, unavailable evidence or expanded scope. Consolidate related corrections rather than creating a loop for each sentence.
6. **Preserve economical delivery and authority.** Report material feedback, resulting change and remaining uncertainty in the existing response and compact status as applicable; retain consequential rationale in the vision. Add no default sibling, transcript or tracker. Review agreement and comprehension do not select strategy, adopt a vision or authorize implementation. Preserve phased loading, proportional scope, source fidelity and local policy. Replace overlap where possible; target net-neutral prompt-family length, record core/family counts and justify growth. Introduce no hard prompt or vision word ceiling.

## Scope

**Intended edits:**

- `.wavefoundry/framework/seeds/179-envision-project.prompt.md` and `docs/prompts/envision-project.prompt.md`: early statement discussion, targeted roadmap feedback and phase routing.
- `.wavefoundry/framework/seeds/envision/review.prompt.md` and `docs/prompts/agents/envision/review.prompt.md`: staged understanding and the shared repair boundary.
- `.wavefoundry/framework/seeds/envision/delivery.prompt.md` and `docs/prompts/agents/envision/delivery.prompt.md`: feedback/coverage reporting and consistent stop wording.
- `docs/architecture/data-and-control-flow.md`, `CHANGELOG.md`, and change-owned evaluation records and focused delivery checks. Reuse existing Envision fixtures where applicable; add no prose linter or wording-only tests.

**Protected:** research/revision companions; seeds 100/160/170; public catalog, registry and rendered skills; runtime code, dependencies, version/package metadata; actual visions and evidence siblings; other waves and unrelated operator edits. Return with any necessary scope expansion before editing those surfaces.

Seed 160's changed-Envision-family rule at lines 495–509 explicitly covers core and companion-only deltas, local customization and conflicts. Its text was inspected; actual delivery of this change still needs the reconciliation check. No new delivery mechanism is proposed.

**Ownership:** one implementer writes canonical/local pairs serially. Evaluation authors/readers use isolated fixtures. Required wave reviewers read candidate/evidence; they do not edit sources or actual visions. Lifecycle reviews remain separate from Envision's advisory roles.

## Acceptance Criteria

- [x] AC-1: Canonical and local instructions consistently define early destination discussion, targeted roadmap feedback and staged understanding before one shared repair, with authority and stop rules preserved. Report word counts and justified growth. Generic “iterate until good” wording, duplicated procedural owners or an extra automatic repair fails inspection.
- [x] AC-2: A bounded synthetic authoring trace shows an actual supplied operator correction changing the early statement and dependent roadmap before full-draft review. A consequential capability/dependency correction changes the path without silently shrinking the chosen destination or rebuilding a verified capability. A semantic evaluator checks consequences against the frozen brief/evidence; merely asking questions or listing the answer as unresolved fails.
- [x] AC-3: A fresh selected reader records uncoached reconstructions before explanatory context and judging criteria. The opening conveys purpose/future/value; the overview connects the next advance and main uncertainty. A concrete meaning defect is repaired within the shared pass and checked on the identified revision. Reader verdicts count only if relevant misleading controls are rejected. Coached or materially false reconstructions fail; this is agent evidence, not proof of human comprehension.
- [x] AC-4: Focused branches preserve an already-chosen destination, honor explicit no-interview/deferral, disclose unavailable independent coverage and stop on a substantive finding first raised after verification. Evidence shows faithful progress or pending work without redundant strategic approval, inferred consent, invented review or automatic extra repair.
- [x] AC-5: Changed-family reconciliation carries the new instructions into an existing target, preserves compatible local additions, surfaces conflicting policy and leaves actual vision/evidence files unchanged. Companion-only change and repeat reconciliation retain one procedural owner. The change's own checks pass, edited documents validate, and no failure elsewhere is attributable to this change.

## Evaluation approach and stop

Run cheap contract/parity and delivery checks before authoring trials. Freeze the brief, operator replies, consequential evidence, expected semantic consequences, reader questions and judging criteria before candidate authoring. Design exact controls during implementation. Use a fictional project unrelated to either field report. One sequential authoring case can cover AC-2/AC-3; short isolated branches cover AC-4 without additional full visions. Retain reader answers before revealing expected meaning. Separate authorship from judging and disclose shared host/model/framing limits.

Declare the finite batch and its stopping point before execution, including allowed repair and verification. It must include a specific misunderstanding that allows observing repair; a clean draft alone cannot establish that behavior. Retain all attempted outcomes and sufficient exact input/output/revision evidence, not routine transcripts. If a required outcome remains unproven or a repair fails its recheck, return evidence and options to the operator before another batch. Do not add trials until one passes.

This establishes selected candidate behaviors, not superiority to existing guidance or causation by a particular loop. No comparative claim is planned; such a claim would require a prospectively matched baseline. During the next naturally authorized field run, observe whether discussion corrected mistaken direction earlier, whether evidence propagated into the roadmap, whether readers understood it and whether extra exchanges helped. Do not start field runs or redirect later planning automatically.

## Tasks

- [x] Freeze current surface bytes, evaluation inputs and finite batch; record existing dirty-tree boundaries.
- [x] Implement minimal core/review/delivery changes and local counterparts under an admitted, readied wave; update architecture/changelog.
- [x] Complete contract/parity and reconciliation checks before authoring trials.
- [x] Run the declared authoring, staged-reading and boundary branches; retain every outcome and honor the stop.
- [x] Record AC evidence and limitations; complete required delivery reviews, document validation and framework checks under repository policy.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Freeze evaluation | Evaluator | Readiness | Inputs/oracle independent of candidate outputs |
| Author instructions | Implementer | Frozen inputs | Serial canonical/local edits |
| Delivery checks | QA | Candidate instructions | Before authoring trials |
| Authoring and staged reading | Isolated author and reader | Delivery checks | Reconstruction before judging context |
| Delivery assessment | Required wave reviewers | Evidence | Exact candidate and disclosed limits |

## Serialization Points

One writer owns each canonical/local pair. Initial findings precede the shared repair; verification follows that revision. Preserve unrelated checkout work.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/179-envision-project.prompt.md`
- `.wavefoundry/framework/seeds/envision/review.prompt.md`
- `.wavefoundry/framework/seeds/envision/delivery.prompt.md`
- `docs/prompts/envision-project.prompt.md`
- `docs/prompts/agents/envision/review.prompt.md`
- `docs/prompts/agents/envision/delivery.prompt.md`
- `docs/architecture/data-and-control-flow.md`

The root changelog is also in scope. At admission request QA, architecture and docs-contract coverage for interaction ordering, evidence quality and preservation, alongside path-selected lanes. This plan creates no approvals.

## Affected Architecture Docs

Update [data and control flow](../../architecture/data-and-control-flow.md) because author/operator/reviewer transitions change. Runtime architecture, product responsibilities and lifecycle authority remain unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Coherent instructions without duplicated loops |
| AC-2 | required | Feedback changes dependent reasoning |
| AC-3 | required | Meaning is reconstructed and repaired before verification |
| AC-4 | required | Useful iteration respects choices and stops honestly |
| AC-5 | required | Existing targets receive the change without losing policy/artifacts |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-31 | Final quiet qualification passed: 12,296 tests / 215 files / 12 existing skips in 538.163s. Green receipt matches current framework hash 990095ca0c86131faeaedfb6e3058015f31a0a16801597626386917bf6a74f81. Both earlier refused attempts remain evidence; no source repair or test waiver. | Run 79ec669704a244418492370f238f8e97; .wavefoundry/cache/qualification/228dy-default.json; delivery-review-evidence.json. |
| 2026-10-31 | Correct-environment run passed all 12,296 tests / 215 files / 12 skips, but the runner refused its receipt because the coordinator recorded delivery approvals and changed the wave summary during execution. Reconciliation correctly refuses authority-file changes. A final quiet run is required; no test failure is waived. | Refused run 8b80e1a7c0db435d80b75453ac634cd0; guard names events.jsonl and wave.md; framework hash unchanged. |
| 2026-10-31 | Final semantic evaluator confirms AC-2–4 within the frozen synthetic scope. Independent architecture, docs-contract and targeted delivery council found no candidate defects; council intent fit establishes. QA awaits final framework qualification. | evaluation-evidence.json includes final-assessment.json; typed delivery approvals and retained reviewer reports. |
| 2026-10-31 | First full suite failed six files under PATH Python without psutil and sandbox restrictions on process inspection and loopback sockets. Focused diagnosis passed all 11 process-info checks using the existing tool venv with approved host access. Full qualification rerun uses that environment; no source repair, dependency installation or test suppression. | Initial report refused-6d00686c840f4864af7fc7f4969bdc34.json; original and qualified logs under /private/tmp/228dy-framework-tests*.log. |
| 2026-10-31 | Staged reader reconstructed opening and overview before anchors, rejected M/T and accepted K. Controlled authority defect PS-01 was repaired once and contextually verified on exact revision A3-D1-R1, with no remaining findings. Natural author draft preserved; no second blind reading or natural defect claimed. | Repaired SHA-256 8e1673f779da9da51266dd84c8231bc6d352bbcb736cadc8de34daab7bcd81cc; final independent semantic assessment pending. |
| 2026-10-31 | AC-2 and AC-4 semantic checks passed. Operator answer committed a provisionally favored destination and sharpened authority/path; no reversal demonstrated. Evidence moved reconciliation from unverified to working, rather than correcting an asserted missing feature. Four separately spawned branch contexts honored selected/no-interview/unavailable/post-verification boundaries. | eval/results/main-assessment.json, branch-assessment.json and context-record.json; fictional stipulated facts, same host/model-family limits. |
| 2026-10-31 | AC-5 delivery checks passed before authoring: actual transport helpers, semantic merge, companion-only update, explicit conflict and repeat no-op. 260 source entries matched; five bad controls rejected. Initial checker-only date assumption failed and was corrected against retained metadata. | work/228dy/delivery records; unique proof retained at delivery. No full installer/native-Windows claim. |
| 2026-10-31 | Candidate core/local parity and contract inspection passed; full docs validation clean. Core 1,897→1,905 words; family 3,929→4,013 (+84) buys explicit staged input, honest missing coverage and shared repair accounting. Repeated prose replaced; no runtime enforcement or behavior claim from this check. | Frozen eval manifest 148b8285c19383b47d0cecc54c2003b15c4ff2a53e671f2247577382ae1d53da; work/228dy baseline, GO-candidate and contract-check. |
| 2026-10-31 | Readback: implement early statement discussion, evidence-driven roadmap returns and an uncoached selected-reader stage before the single shared repair. For example, an operator choosing community access instead of commercial sales changes the statement and dependent path before polishing; it does not authorize adoption. AC-1–5 cover the three canonical/local pairs, delivery and honest stopping. | Readiness passed on review-policy-0938e94e97cf51e25b56; 228dy activated, 224i4 paused. |
| 2026-10-31 | Authored plan only after operator requested the suggested enhancement. | Core/review/delivery, seed 160 family rule, architecture flow and writing guide inspected; field reports attributed. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-31 | Select focused feedback within existing phases. | Makes the early statement actionable and places reconstruction before repair without full reruns. | Unchanged guidance costs least but leaves sequencing implicit. Repeated complete cycles multiply effort and invite agreement without new evidence. |
| 2026-10-31 | Reuse a selected reviewer with staged input. | Existing coverage can supply a fresh reconstruction before contextual role review. | A mandatory fifth reader adds cost; author-only rereading cannot establish independent understanding. |
| 2026-10-31 | Test specific behaviors, not superiority. | Current guidance already supports much of the goal; field reports do not isolate the proposed mechanism. | Add a matched comparison only if an authorized later scope needs that claim. |

**Mechanism efficacy:** replaying Tensorwell's account suggests an early paragraph could expose “personal computer” as an unchosen destination; replaying Solaris suggests targeted capability feedback could repair the path without restarting strategy. These effects are inferred, not executed outcomes. Guidance advises the author; actual operator answers, source evidence and reader reconstructions provide external feedback. It can still be ignored, mistake a legitimate modest ambition for failure, or cause unnecessary exchanges. Existing guided decisions provide much of the mechanism. Honoring settled/no-interview paths, requiring consequential feedback and sharing one repair boundary limits added burden. AC-2 through AC-4 test these distinctions; later field observations assess usefulness.

## Risks

| Risk | Mitigation |
| --- | --- |
| Prompt growth weakens adherence | Replace overlap; keep procedural detail in companions; report counts/reasons |
| Feedback becomes approval ceremony or shrinks ambition | Reuse choices and return strategic changes to the operator |
| Reconstruction is coached or treated as strategy validation | Retain first answers; distinguish understanding from endorsement or demand |
| Three opportunities multiply review rounds | Shared repair/verification boundary; no automatic post-verification restart |
| Synthetic success is overstated | All attempts, controls and limits retained; no human/field/superiority claim |
| Delivery checks imply platform qualification | Host-neutral instructions; report actual test host and no native Windows claim without execution |

## References and evidence limits

- [Envision core](../../prompts/envision-project.prompt.md), [review](../../prompts/agents/envision/review.prompt.md) and [delivery](../../prompts/agents/envision/delivery.prompt.md): inspected on 2026-10-31. Instructions establish prescribed behavior, not execution fidelity.
- [Writing guide](../../../.wavefoundry/framework/docs/writing-guide.md): reader-task reconstruction within existing reviews, preserving meaning and authority.
- Tensorwell and Solaris reports supplied in this conversation: motivating field observations without independent reproduction or comparative proof.
- [Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents), [Self-Refine](https://arxiv.org/abs/2303.17651) and [Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798): previously consulted primary sources supporting investigation of bounded feedback with clear criteria and external evidence. Their task-specific findings do not establish efficacy for Wavefoundry visions or current models.

## Session Handoff

Admitted to 228dy under the operator’s prepare/review/implement request; readiness is pending. Pause completed-but-open 224i4 before activation. No actual vision revision, package, commit or closure is authorized. See [session handoff](../../agents/session-handoff.md) for current repository work.
