# Envision: guide consequential strategic decisions

Change ID: `224ut-enh envision-guided-decisions`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-31
Wave: `224uu envision-guided-decisions`

## Rationale

The operator supplied Tensorwell feedback from Envision 1.39.0+q0f4: concrete alternatives and advisory review improved the document, but the author listed consequential unresolved choices instead of helping the operator decide. This is one operator/run report, not comparative proof. Current core sections Establish the brief and Explore, then recommend allow nonblocking uncertainties and preserve operator choices but do not explicitly facilitate a conversation after alternatives become intelligible. The operator requests the proposed addition with consequence-based triggers, focused questions and a distinction between explicit strategic acceptance and mere document acceptance. During implementation, the operator also required one clear unified vision statement/paragraph expressing the project’s ultimate meaning; some field outputs did not make that statement clear. The existing summary-first sentence is insufficiently explicit about this standalone artifact.

## Product Intent

Operators can use Envision to understand and select, combine or deliberately defer consequential directions before dependent drafting/review treats them as settled. The vision reflects their actual answer, without reopening settled strategy or imposing an interview on a draft-only request. This advances Wavefoundry's adopted intent to turn human purpose into challengeable direction; it does not decide Wavefoundry's own open entry strategy. AC-2/3 observe bounded conversational behavior; AC-1 proves guidance delivery. A reader should also be able to explain the project’s purpose, intended future and beneficiary value from its unified opening paragraph alone (AC-4). Human comprehension and later Plan change carry-through remain field observations, not claims established by a scripted probe.

## Requirements

1. After developing concrete alternatives, guide choices that materially affect beneficiaries, product responsibility, destination, roadmap order or operating commitments. Distinguish them from engineering details or research uncertainties that can remain open. Reuse prior answers and preserve explicitly chosen destinations.
2. Walk through consequential decisions one at a time in dependency order. Explain why a decision matters now, credible options through future experiences, effects on outcomes/responsibility/path/obligations, a provisional recommendation and uncertainty, and reversibility. Invite choosing, combining, deferring or seeking evidence; reflect the actual answer and resulting consequences before the next dependent step. No fixed question count or standalone decision artifact.
3. Pause only dependent recommendation/review work when the unanswered choice would materially redirect it; continue useful independent evidence work. An explicit exploratory-draft-first or no-interview request is respected: keep contingent choices visible rather than inventing agreement. Research-dependent deferrals name a useful next test. Do not treat silence or review consensus as an answer.
4. Explicit acceptance of a recommended direction can select strategy; receiving a document or approving its wording alone does not. Selection alone grants neither adoption nor implementation authority; honor separately explicit instructions under existing rules. No approval ritual, automatic Review plan/Evaluate decision, new reviewer role or broader interview mandate.
5. Existing product-strategy/challenge review checks whether consequential choices were explained and operator answers accurately reflected, rather than just listed. Delivery returns newly surfaced material choices to a focused conversation, respecting no-interview requests and existing revision/review coverage and bounded-repair rules. No automatic second repair loop or implicit implementation follows.
6. Update canonical core and existing review/delivery companions plus exact local counterparts, architecture explanation and changelog. Preserve the company-context addition and all existing research/revision/adoption/phase-loading contracts. Keep the core concise, targeting replacement/consolidation where possible; record word counts and why any growth matters.
7. Lead the vision’s substantive content with one clear unified vision statement, normally a concise standalone paragraph stating enduring purpose, the future the project exists to make possible and why it matters to those it serves. The roadmap and supporting argument follow; a slogan, feature list or blend of incompatible alternatives is insufficient. Preserve an explicitly chosen direction. For an authorized exploratory draft, clearly label one coherent recommended statement provisional rather than implying selection; if no coherent statement is possible, use the guided-choice step within the requested interview scope. Review the opening for meaning and fidelity, not word count or a mandatory template.

## Scope

**In scope:** seed179; envision review/delivery companions; corresponding local prompts; architecture Envision section; changelog; wave records and handoff. Coordinator writes; independent reviewers and probe workers have read-only source access.

**Out of scope:** actual vision outputs; Tensorwell integration diagnostics/runtime changes; company-context evidence from closed224us; new commands/skills/companions or renderer/seed100/160 changes; target upgrades, package rebuild/version stamp, commit/push/release and wave closure. The existing tested q0f4 archive stays unchanged. This follow-up changes guidance source for the next build.

## Acceptance Criteria

- [x] AC-1: Core and review/delivery phase guidance implement R1–R7 with canonical/local parity and no new protocol/file surface. Existing company context, authority, phased loading and bounded-review rules survive; count words and explain growth. Explicit selection is distinguished from document wording approval and from adoption/implementation.
- [x] AC-2: One staged synthetic interaction shows a fresh author explain consequential alternatives and ask one focused question before settling a contingent direction; after a frozen scripted operator reply chooses a combination and defers another choice, the author reflects that answer and adjusts the recommendation/dependencies without inventing the deferred decision. An independent reader can reconstruct the chosen outcome and tradeoff, and rejects frozen bad responses that select on silence or ignore the answer. This is simulated interaction evidence, not observed human comprehension or comparative superiority.
- [x] AC-3: In the same bounded probe batch, fresh author outputs for an already-chosen destination and an explicit no-interview exploratory draft honor those instructions. No rote strategic reopening, mandatory questionnaire, assumed adoption or dependent review commitment appears; unresolved research gets a useful next test. Reader rejects a frozen bad response forcing an interview or reopening the settled direction. Existing family upgrade mappings still cover changed sources, and authored docs/scoped checks pass without failures attributable to this change.
- [x] AC-4: Two short opening excerpts under the final guidance (selected direction and no-interview provisional direction) each supply one unified statement before roadmap detail. A fresh reader given only each opening can reconstruct purpose, intended future and beneficiary value, then confirms fidelity against the supplied brief; it rejects frozen generic-slogan/feature-list controls. No implied strategic selection or new interview appears in the provisional case. Scope is opening clarity in these cases, not universal full-vision compliance.

## Tasks

- [x] Freeze probe packets, staged reply, reader questions/anchors and bad controls before seed edits.
- [x] Implement and mirror concise guidance; update architecture/changelog and contract checks.
- [x] Execute one bounded conversational batch and independent evaluation; retain unique evidence and limits.
- [x] Freeze and run the operator-added opening-statement check against the final guidance, with an independent reader.
- [x] Run canonical framework checks, required delivery reviews and final docs validation; hand off source changes.

## Agent Execution Graph

| Workstream | Owner | Depends On | Boundary |
| --- | --- | --- | --- |
| Guidance and records | Coordinator | Readiness | Only write owner |
| Interaction probe | Fresh author, then independent reader | Frozen inputs and revised guidance | Scripted operator, no real strategy selection |
| Delivery | Required reviewers | Evidence and canonical tests | No artifact rebuild or target changes |

## Serialization Points

Freeze evaluation inputs before source edits. Supply author only the relevant scenario/prompt, never scoring anchors or bad controls. Supply the scripted reply only after the initial question is persisted. Separate the two standalone branch scenarios from the interactive transcript; use fresh branch contexts so choices do not bleed across cases. Reader reconstructs before seeing anchors/controls. Root serializes source and ledger writes. Finish material records before canonical suite; no repository input mutations during that run.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/179-envision-project.prompt.md`
- `.wavefoundry/framework/seeds/envision/review.prompt.md`
- `.wavefoundry/framework/seeds/envision/delivery.prompt.md`
- `docs/prompts/envision-project.prompt.md`
- `docs/prompts/agents/envision/review.prompt.md`
- `docs/prompts/agents/envision/delivery.prompt.md`
- `docs/architecture/data-and-control-flow.md`

Root CHANGELOG.md also changes. No source scripts, tests, manifests, skill registry or catalog changes are intended.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` Envision flow for the alternatives-to-decision transition, conditional pause, operator-answer propagation and bounded delivery handling. No runtime boundary changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Correct delivered guidance and preserved contracts |
| AC-2 | required | Main claim needs interaction evidence, not document headings |
| AC-3 | required | Deferral/autonomy boundaries must remain useful |
| AC-4 | required | The vision must communicate its ultimate meaning in one usable opening |

## Evaluation Budget

One interactive author context, two short fresh branch contexts (already-chosen and no-interview), and one independent reader; brief excerpts rather than complete visions or another advisory ensemble. Freeze prompts/reply/questions/anchors/controls before edits. The interactive author's first question is preserved before the scripted reply; absence of a reply is tested by its initial waiting posture, not a fabricated elapsed-time experiment. No model identity diversity or real operator understanding is claimed. One batch per declared scope: return evidence/options to the operator if a required outcome remains unproven, rather than automatically repeating. Required implementation reviews remain independent. Retain exact unique inputs and outputs in one compact evidence file; routine reviewer notes stay disposable. Observe actual operator comprehension and Plan change continuity at the next natural use without redirecting that work.

The operator’s added unified-statement requirement authorizes one additional bounded check, not a retry of the original interaction. Preserve the original candidate, packets and results unchanged. Before the statement edit, freeze a filtered packet using the existing chosen/no-interview briefs, neutral opening-reader questions, fidelity anchors and two bad controls. One fresh author produces two opening excerpts using final guidance; one fresh reader reconstructs from openings alone before receiving briefs/anchors/controls. No full vision or new advisory ensemble. Original interaction evidence remains scoped to its candidate; final delivery reviewers check the added opening rule for compatibility with that behavior rather than claim it was exercised in the first batch.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-31 | Operator requested the proposed guided-decision change. Closed224us with explicit authorization before this follow-up activates. No new seed edit yet. | Tensorwell report supplied in conversation; current core/review/delivery inspected through MCP |
| 2026-10-31 | Frozen scripted interaction, chosen/draft-only cases, reader questions/anchors and three bad controls before any source edit. Filtered author packets exclude reply and scoring. | `.wavefoundry/work/224uu/fixture.json` SHA-256 `bb3865b3daa67b93ec965f50c046fb152b4c91924f521670dda01d8fb384e7dc`; core 1,656 / family 3,575 words baseline |
| 2026-10-31 | Readback / Thought: add the alternatives-to-decision conversation to core and existing review/delivery reminders. Before: list a material choice as uncertainty and finish the draft. After: explain options, ask a focused question and change the contingent recommendation from the actual answer; draft-only/chosen paths remain direct. AC-1/2/3; source-only follow-up, no package/vision/runtime changes. | Readied receipt `review-policy-0b75b437df860a67a112`; source-before.json retained |
| 2026-10-31 | Observe: all5canonical/local bodies match; protected sources, actual visions and q0f4 archive unchanged; docs validate. Core 1,656→1,821 (+165), family 3,575→3,815 (+240). Growth supplies the missing interactive decision step, conditional pause and answer/authority distinction, with existing phase reminders; no new file or review protocol. Thought: run the frozen interaction and two fresh branch contexts, keeping scripted reply/scoring hidden. | `.wavefoundry/work/224uu/contract-check.json`; three fresh author contexts |
| 2026-10-31 | Operator added the explicit unified vision statement during implementation. Amended R7/AC-4 and bounded evaluation scope before dependent source edits; preserve original frozen interaction evidence and obtain refreshed readiness. | Current operator instruction; core Write the vision and roadmap inspected |
| 2026-10-31 | Original interaction batch passed staged independent reading and all3bad controls; later opening enhancement is not covered by that result. Froze the additional two-opening check before the next source edit; reopened AC-1/implementation task for R7. | reader-verdict.json SHA-256 `7e99a9662fe573da0137defa1a45f6a496e0de9eeb0b1b5b381c5c69130ca034`; statement-fixture.json in disposable work |
| 2026-10-31 | Readback / Thought: refreshed readiness authorizes R7. Replace the loose summary-first opening with one explicit unified paragraph of project meaning; preserve selected/provisional status and roadmap afterward. Existing review/delivery checks inspect opening alone. Now execute the separately frozen two-opening test, preserving original interaction evidence. | Current receipt `review-policy-66c066998b3a32f32d20`; statement fixture SHA-256 `e0c6c8bb58bd0d561ee2dcba9a3694e6014114ac52c1d8dc704f03711c82a08a` |
| 2026-10-31 | Final core 1,897 words (+241 from baseline); family 3,929 (+354). Added unified project meaning, accurate provisional status and opening-only review checks. Canonical/local parity and protected-file checks pass. Two fresh-author openings passed staged independent reconstruction/fidelity; both slogan and feature-list controls rejected. First-paragraph cut rule was saved after generation but before coordinator inspection; no content-based selection. Original conversation test remains scoped to its earlier retained candidate. | `evaluation-evidence.json`; opening verdict SHA-256 `f9efa9030a7d53aebe585cc796c614bed7f20ab7e131b2e6e30595019632c12b` |
| 2026-10-31 | Canonical suite passed 12,291 tests across 214 files with 12 reported skips (552.279s); current receipt independently checked by QA. Fresh QA, architecture and docs-contract delivery reviews approved without findings; QA confirmed bounded Intent outcome. All required ACs verified; no field efficacy or final-candidate conversation rerun claimed. | `evaluation-evidence.json`; `delivery-evidence.json`; receipt `e16ce391848e53be93a7ef273df398da4684b8c66db93e7195acbb4169d38dba` |
| 2026-10-31 | Subsequent explicit operator request built local 1.39.0+q0fz after all implementation reviews. Reused exact default qualification; fresh second/declared profiles and exact skip comparisons passed. Archive bytes, changelog, nested manifests and uv 0.12.22 verified. Packaging is a follow-on operation, not a change to reviewed requirements or authority. | `packaging-evidence.json`; no public release, target upgrade, commit or closure |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-31 | Conditional facilitated choice after alternatives, with existing phase reminders | Makes decisions intelligible before asking, while keeping independent work moving | Upfront strategy questionnaire asks too early; delivery-only list repeats the reported gap; a new decision workflow adds ceremony |
| 2026-10-31 | Scripted multi-turn probe plus explicit boundary cases | Can observe answer propagation and waiting posture without pretending to measure actual human understanding | Static vision-only reader misses interaction; broad real-project trial needs unavailable operator/project time |

## Risks

| Risk | Mitigation |
| --- | --- |
| Every uncertainty becomes a gate | Consequence-based trigger; details/research can defer; independent work continues |
| Recommendation or review consensus substitutes for a choice | Provisional recommendation, explicit answer reflection and silence control |
| Endless interview/review loop | Reuse settled choices; no-interview branch; existing one-repair boundary |
| Prompt growth dilutes strategy | Short core step, existing review/delivery owners, word-count accounting |

## Session Handoff

See `docs/agents/session-handoff.md`. Implement this source follow-up; old package and unrelated visions stay unchanged.
