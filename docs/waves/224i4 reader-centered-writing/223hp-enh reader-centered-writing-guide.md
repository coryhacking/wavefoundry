# Reader-centered writing guidance for documents and instructions

Change ID: `223hp-enh reader-centered-writing-guide`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-31
Wave: 224i4 reader-centered-writing

## Rationale

The operator requested a shared writing guide after discussing ISO 24495-1:2023 and ASD-STE100. Wavefoundry communicates through specifications, architecture, plans, waves, reviews and handoffs. Those documents need to help their readers understand behavior, make decisions and continue work. Correct headings and short sentences alone do not establish that outcome.

The existing technical-writer seed already prioritizes accuracy, audience clarity, findability and terminology consistency (seed 233, lines 12–36). This change connects that intent to a reusable guide and concrete reader tasks across authoring workflows. It does not claim those workflows universally fail today. The earlier Envision feedback concerns particular runs; it is motivation, not evidence of general writing quality or comparative benefit.

## Product Intent

Operators, maintainers and agents should be able to find and accurately explain a document’s purpose, obligations, important choices and next action without reconstructing them from procedural history. The change delivers a common writing reference and tests faithful reader understanding on bounded examples. AC-2 and AC-3 assess that intent; shipping references alone does not prove it. It supports the adopted vision’s system understanding and continuity outcomes (Horizon 2), while preserving the authority and evidence needed for trustworthy acceptance. It neither changes that vision nor promises its long-term result.

## Requirements

1. **Common guide.** Provide one concise, packaged writing guide using ISO 24495-1’s relevant, findable, understandable and usable principles as the main framework. Explain the reader’s task before prescribing style. Use original explanatory prose and primary-source references; describe it as guidance informed by the standards, not certified or fully verified compliance. Do not bundle licensed standards or impose the full STE dictionary.
2. **Precise language.** Adapt selected STE practices for instructions and requirements: consistent terms, explicit actor/action/conditions, clear references, direct verbs and one coherent instruction per step. Preserve technical vocabulary when it is needed; define it for the audience rather than replace it inaccurately. Preserve normative force, exceptions, evidence status, risk, authorization and numerical constraints. Do not impose universal word/sentence limits, ban passive voice mechanically, or treat shorter prose as inherently better.
3. **Artifact purpose.** Give compact guidance for vision; specification; architecture; decision record; change plan; wave/status record; review finding; and handoff/release note. Vision starts with unified meaning; specifications expose observable obligations; architecture explains responsibilities, flows and failure modes; decisions show choice and consequence; plans connect problem to outcome and verification; waves show current objective/status/blockers/next action; findings explain failure and evidence; handoffs expose result and continuation. Scale detail to stakes and reader knowledge. Preserve existing machine-required headings, metadata, evidence schemas and audit history.
4. **Use at the point of work.** Add short references in the shared run contract and relevant existing author/reviewer guidance, with artifact-specific purpose only where needed. Ordinary replies and progress reports should lead with the answer, result or next action. Do not load the whole guide on every tool call, add a public command/skill or repeat it in every prompt. Honor explicit user format and project writing conventions; expose consequential conflicts instead of silently replacing them.
5. **Distribution.** Install and upgrade must deliver the canonical guide and working references for both new and existing projects. Existing local style guidance and operator edits survive; reconcile changed pointers through established merge-safe ownership rules. A guide-only update must reach a target without needing unrelated prompt changes. No automatic rewrite of historical documents, waves, approvals or visions. Determine actual delivery seams through source inspection and executable checks before claiming support.
6. **Review by task.** Existing applicable reviewers test whether the intended reader can recover the needed meaning and action. Distinguish factual or contractual errors from editorial preferences. Use existing lane authority and stop rules; add no council, required lane, approval gate, compliance score or blocking prose linter. Automated checks in this wave cover delivery/contract mechanics, not purported comprehension.
7. **Evidence and rollout.** Apply to newly authored or substantially revised material, and documents naturally touched later. Compare bounded current-guidance/candidate examples before claiming improvement. Retain all attempts and failed controls. If both versions succeed, report preventive guidance, not demonstrated superiority. Synthetic readers are not human validation. Capture later operator feedback during ordinary work without creating a recurring survey or redirecting that work.

## Scope

**In scope:** one canonical guide at `.wavefoundry/framework/docs/writing-guide.md`; six seed integrations and four project-local counterparts below; delivery/contract checks and the bounded reader evaluation; architecture flow and changelog updates. The guide owns artifact-specific purposes; callers carry short references, not copied writing policies.

| Canonical owner | Exact project-local counterpart | Change and invocation route |
| --- | --- | --- |
| `.wavefoundry/framework/seeds/020-run-contract.prompt.md` | Shared contract is consumed directly; no parallel local copy | Add the concise ordinary-response rule and load the guide when authoring or materially revising prose; preserve semantic and machine contracts |
| `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md` | `AGENTS.md` | Seed one short shared writing reference and local-policy precedence; existing host entry files continue to point to AGENTS |
| `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` | `docs/prompts/index.md` | Carry the short writing reference in existing Operating Rules; this entry route reaches planning, decisions, vision, implementation/status and handoff without separate policy copies per prompt |
| `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` | `docs/prompts/upgrade-wavefoundry.prompt.md` | Specify the same-run, agent-assisted merge of these references and the technical-writer clause, preserving local content and checking actual destinations on retries |
| `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` | Existing reviewer carriers already reference this canonical seed; no carrier edit planned | Put the reader-task review direction inside the canonical Executable Review Evidence Protocol that the existing managed carrier explicitly loads; retain existing reviewer authority and no new lane/gate |
| `.wavefoundry/framework/seeds/233-technical-writer.prompt.md` | `docs/agents/specialists/technical-writer.md` | Correct the short-over-complete priority to reader purpose and accurate sufficient detail; point to the common guide |

Additional owning paths are `.wavefoundry/framework/scripts/tests/test_writing_guide_delivery.py`, `docs/architecture/data-and-control-flow.md`, and root CHANGELOG.md. Test fixtures may live inside that test module or temporary directories; bounded author/reader evidence belongs in the existing change/wave records, with temporary working artifacts disclosed. No runtime script change is planned. The earlier seed list was a maximum discovery inventory: seeds040/170/176/178/179/180/190/227/230 and the Envision companions need no edit because they inherit the shared entry/run-contract route and retain their own artifact contracts. No separate reviewer-role copy is needed because the existing managed review block directs reviewers to seed209. Do not claim renderer propagation of arbitrary seed prose.

**Delivery route and proof boundary:** `build_pack.collect_files` includes regular framework docs under the archive's `.wavefoundry/framework/` prefix; `upgrade_wavefoundry._extract_feature_members` delivers those members independently of changed-seed detection. Therefore a guide-only payload revision can update the same canonical path without a prompt revision. Fresh project references are authored through seeds050/100/233. Existing references and the customized upgrade prompt are reconciled by an agent following seed160, outside renderer-owned regions; setup/rendering alone does not merge them. Reconcile only uniquely identifiable canonical clauses or unambiguous additions, preserve local writing policy/metadata, and stop the affected merge on a conflict. On retries inspect the actual guide and reference destinations even if the prior diff is empty; current content makes no further edit. Guidance is locally readable and does not require fetching linked standards at run time.

Before claiming AC-4, execute production collection/extraction on temporary fresh and customized targets, including a second payload changing only the guide. Separately execute and record the actual seed-driven fresh authoring and existing-target agent merge, then verify each selected reference resolves and can load the guide, customized text and historical artifacts remain unchanged, and a repeat reconciliation is stable. Exercise missing-guide and stale-reference negative controls. Mechanical tests establish bytes, reachability and preservation; the recorded agent-assisted reconciliation establishes the authored-pointer path. A fake automatic prose migration or package-membership-only test is insufficient. This is bounded component/reconciliation evidence, not an unexecuted full downstream install, network/model setup or release-archive qualification claim.

**Protected:** root vision/research/review and Relay documents; historical wave/change records and ledgers; unrelated product/code behavior; model/dependency pins; public command/skill registry; review-policy requirements; current 224uu Envision semantics and its package qualification. No bulk cleanup, new lint engine, new company discovery, Floorplan integration, mandatory compliance certification or package build in this wave.

## Acceptance Criteria

- [x] AC-1: The common guide and actual invocation routes cover R1–R4 and R6 without duplicated policies, compulsory extra reviews or altered machine contracts. Review verifies precise instructions and evidence/authority survive simplification, including a legitimate technical example that needs substantial detail. Report the common guide length and added always-read text, explaining material growth. Authored/edited documents validate; no failure elsewhere is attributable to this change.
- [x] AC-2: On a frozen technical fixture containing a requirement and architecture/decision explanation, candidate-guided authoring lets an independent reader identify the actor, triggering conditions, required outcome, exception, responsibility boundary and consequential tradeoff. The reader rejects a fluent but semantically wrong simplification. Current-guidance output uses the same brief; comparison reports actual outcomes without assuming candidate superiority.
- [x] AC-3: On a frozen planning/status/continuation fixture and a short vision opening, the reader finds and explains the intended outcome, present status, unresolved decision and next authorized action, and reconstructs the vision’s meaning. It rejects a concise generic statement and an attractive status summary that invents completion or authority. A justified long technical passage is not rejected merely for length. Evidence distinguishes agent evaluation from human comprehension and later field usefulness.
- [x] AC-4: Executed delivery checks establish that a fresh target and an existing customized target can obtain the guide and relevant references without overwriting local writing policy or historical artifacts. A guide-only revision is delivered. Checks exercise the actual producer/reconciliation path and reject missing-guide or stale-reference controls; package membership alone is insufficient. Tests added/changed by this work pass.

## Tasks

- [x] Finalize the smallest owning surface inventory and delivery route before readiness. Evidence: exact Scope mapping; targeted MCP reads of build_pack.collect_files, upgrade_wavefoundry._extract_feature_members, render_agent_surfaces.REVIEW_PROTOCOL_CARRIER_BLOCK and seeds020/040/050/100/160/233. Delivery execution remains a later task, not a planning-pass claim.
- [x] Freeze representative briefs, reader tasks, meaning-preservation oracle, current-guidance baseline and bad controls before guidance changes.
- [x] Author the shared guide and concise integration references; update local mirrors, architecture flow and changelog.
- [x] Verify fresh/existing/customized delivery and guide-only updates through the declared production collection/extraction and actual agent-assisted authoring/reconciliation paths; check pointer loading, preservation, stable repeat and negative controls without network/model work.
- [x] Run the bounded author/reader batch, retain observed outcomes and limits, and repair only within the declared batch boundary.
- [x] Run required framework checks, independent delivery lanes and final docs validation; hand off results.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Surface inventory and brief | coordinator | operator request | Read-only source discovery; planning writes only |
| Guide and references | technical-writer / implementer | admitted, readied and activated wave | One write owner for shared sources |
| Delivery verification | implementer / QA | settled delivery mapping | Real producer path and preservation controls |
| Bounded evaluation | independent author and reader contexts | frozen briefs and candidate | Separate reader reconstruction from scoring; no pretend human sample |
| Required reviews | receipt-selected reviewers | stable final source/evidence | Read-only; coordinator records actual judgments |

## Serialization Points

Do not implement while 224uu owns the open slot. Its package is a separate authorized operation and must finish against its reviewed source. Planning this wave does not reopen 224uu or insert the guide into that package. Exact material scope must be settled before Prepare.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/docs/writing-guide.md`
- `.wavefoundry/framework/seeds/020-run-contract.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/seeds/233-technical-writer.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_writing_guide_delivery.py`
- `docs/prompts/index.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/agents/specialists/technical-writer.md`
- `docs/architecture/data-and-control-flow.md`

Root AGENTS.md and CHANGELOG.md are also intended edits. This exact list replaces the earlier maximum discovery inventory. Implementation owns guide/seeds/mirrors/tests; independent reviewers never edit them. Preserve operator contributions and stop on conflicting ownership. Existing review managed regions and other host surfaces need no hand edit; any necessary generated side effect must be inspected and attributed before keeping it. A runtime delivery defect would require an explicit scope amendment before editing its script, not an implicit expansion of this prose change. The later operator-requested Envision-loop evaluation is separate work after this wave, outside this scope.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: where authoring loads the shared guidance, who owns local policy and how install/upgrade deliver it. No new runtime architecture is intended; revise this scope if inspection shows runtime work is necessary.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Guidance must be coherent, precise and usable at the authoring surface |
| AC-2 | required | Technical meaning must survive improved prose |
| AC-3 | required | Communication must support decisions and continuation, not only look simpler |
| AC-4 | required | Benefits must reach existing and new target projects |

## Evaluation Budget

One predeclared batch using two small composite fixtures, not full project visions: technical obligations/architecture and plan/status/handoff/vision excerpts. Use matched baseline/candidate authors and a fresh reader; freeze the questions, expected meaning and stopping conditions before source edits. Reader first reconstructs meaning from neutrally labelled outputs, then sees scoring criteria and bad controls. Reuse outputs across ACs; do not spawn a reviewer for every artifact type. Exact mechanics belong to implementation, within this bounded coverage.

Report every attempt and whether observed differences support improvement. If a required outcome remains unproven or a repair fails its focused check, return evidence/options to the operator before another batch. No automatic sequence of broadened trials. Later naturally occurring user feedback is useful follow-up, not a condition invented after delivery.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-31 | Implementation complete: all required delivery lanes approved and QA independently confirmed bounded intent. Final docs validation passed. Retained oversized evidence strings were represented as lossless line arrays so scanner lines remain bounded; every original artifact SHA-256 still matches. Wave stays open; no package, commit/push or closure performed. | Current typed approvals in events.jsonl; delivery-evidence.json; evaluation-evidence.json; session handoff |
| 2026-10-31 | Operator authorized one fresh focused reader check on unchanged candidate texts. Reconstruction was frozen before scoring; all 32 predefined atoms recovered and all 4 controls correct. Initial misses retained; offline-operation omission outside oracle noted. AC-2/3 bounded reading evidence established without claiming superiority or human validation. Full suite rerun passes 12,296 tests / 215 files / 12 skips in 547.411s. | evaluation-evidence.json retains authorization, exact packet, reconstruction and scores; delivery-evidence.json records both suite attempts and current receipt/report |
| 2026-10-31 | Initial full suite failed the profile-literal census on two default wave paths in the new test. Replaced them with configured record_paths/vocabulary_profile values; no production guide change. Both affected files pass (13 tests), and a separate alternate-directory/filename preservation control passes. Full suite rerun required; failed execution retained. | delivery-evidence.json verification_attempts; refused-fc8b64063e704b11907688a3e582bb39.json; /private/tmp/224i4-default.log |
| 2026-10-31 | Initial matched batch complete. Baseline technical 17/17; candidate technical 15/17; candidate planning 13/15; baseline planning 13/15. All omissions are partial reader misses, with meaning present in authored text. Three bad controls rejected and detailed positive accepted. AC-2/3 complete reconstruction remains unproven; no comparative improvement shown. Returned evidence/options to operator before another batch; no source repair proposed. | evaluation-evidence.json retains every original input/output, frozen reconstruction and scoring; separate-turn reconstruction hash 443bf740f760…; operator question pending |
| 2026-10-31 | AC-1/4 execution complete: five mechanical tests pass; separate agent authored fresh references and reconciled customized carriers from shipped seeds, preserving local policy/metadata/commands and historical/vision bytes. Both current-content retries were no-ops. Coordinator rechecked reference chains and protected bytes. Component qualification only; no complete target install, network/model setup or native Windows run. | delivery-evidence.json retains actual diffs, source/output/retry hashes and limits; test_writing_guide_delivery.py rejects missing-guide and stale-reference controls |
| 2026-10-31 | Implemented guide and references. Guide 980 words; ten seed/mirror surfaces net +673, including +141 shared startup/run-contract words. Other additions are conditional install/upgrade/review guidance. Architecture +160 and changelog +58. Five focused delivery tests pass; full docs validation and diff check pass. No comparative reader result yet. | Frozen guide cd9904b56148…; implementation-counts.json; test_writing_guide_delivery.py (5 tests); actual agent reconciliation running separately |
| 2026-10-31 | Readback: add one reader-centered guide and short seed/local entry references; preserve technical meaning, local policy, machine contracts and lifecycle authority. For example, simplify instructions without converting permission into obligation or dropping an exception. AC-1 checks guidance/routes; AC-2/3 use the frozen matched reader batch; AC-4 separately checks production extraction and actual agent-assisted reconciliation. Exact fourteen paths remain as admitted; no Envision-loop implementation, package, vision rewrite or runtime change. | Readiness receipt review-policy-6aaaa5c03809538b6ef2; activated via wf_implement_wave; pre-implementation memory briefing checked; implementation-baseline.json captures existing content |
| 2026-10-31 | Operator agreed to ISO-led plain-language guidance with selected STE practices and requested a new wave. Planning only; package source remains unchanged. | Current conversation; official ISO overview and public standard preview; official ASD-STE overview |
| 2026-10-31 | Inspected technical-writer priorities, run-contract boundaries, docs/bootstrap ownership and adopted vision opening/path. Existing guidance supports clarity; exact common-reference delivery route is still to be verified. | Seeds020/040/100/233; project-overview canonical designation; VISION.md opening/path |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-31 | One shared guide plus concise references and reader tasks | Replays the motivating problem by asking whether readers can recover meaning and action; existing author/reviewer workflow supplies the point of use | Full STE compliance would require dictionary/rule verification and constrain broad strategic prose; duplicating style rules per prompt increases drift and attention cost; a blocking style linter could reward short but wrong text |
| 2026-10-31 | Advisory language principles with semantic preservation and existing review authority | Guidance influences behavior but cannot guarantee comprehension; examples and reader tasks test selected outcomes. It can miss domain misunderstandings or be ignored; generic scorekeeping is not a substitute | No universal readability score, fixed length cap, or extra council. Clear existing outputs may already pass; then report preventive guidance |
| 2026-10-31 | Stage this as a separate planned wave | Artifact-wide delivery and evaluation is materially broader than 224uu’s Envision change | Expanding the implemented Envision wave would invalidate its settled scope and interfere with requested packaging |

## Risks

| Risk | Mitigation |
| --- | --- |
| Simplification deletes a condition, exception or authority boundary | Explicit semantic oracle and wrong-but-fluent controls |
| More instructions make agents less attentive | One source, point-of-use pointers, report added always-read burden and justify growth |
| Style becomes compliance theatre | Reader tasks and honest scope; no certification claim or scoring gate |
| Local policies are overwritten or existing targets miss the guide | Real customized-target and guide-only delivery checks |
| Generic guidance suppresses technical precision or justified detail | Audience-aware terms and long-but-useful positive control |
| Evaluation expands indefinitely | Predeclared batch; return unresolved outcomes to operator |

## References

- [ISO 24495-1:2023 official overview](https://www.iso.org/standard/78907.html)
- [Public ISO 24495-1 preview](https://cdn.standards.iteh.ai/samples/78907/d194fac21d6a45f38bfcfec9657f7498/ISO-24495-1-2023.pdf)
- [ASD-STE100 official overview](https://www.asd-ste100.org/about.html)

These sources support the principles; the full standards have not been audited for compliance in this planning pass. The guide must not claim that they have.

## Session Handoff

See `docs/agents/session-handoff.md`. This is an admitted planning artifact, not readiness or implementation authority. Finish the exact surface/delivery inventory, then Prepare and review before source edits.
