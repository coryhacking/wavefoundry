# Actionable readiness handoff

Change ID: `22l5x-enh actionable-readiness-handoff`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-05
Wave: 22l5y actionable-readiness-handoff

## Rationale

An operator reported repeated full readiness panels and hard-to-use blocker handoffs. The installed version, round logs and causal root cause are unavailable, so the report is not proof of a framework defect or six mechanically observed rounds. Current code already classifies nonblocking notes and required blockers; current guidance already bounds repair and requires focused verification. The missing practical improvement is a compact response exposing those existing facts and the next safe choices, rather than another generic missing-approval hint.

## Product Intent

Coordinators and operators can see which readiness findings actually block, what evidence and lanes remain, and how to make the next bounded decision without repeating an unrelated panel. Required specialist authority, security obligations and current-receipt approvals remain intact. AC1–3 test this bounded handoff; AC4 checks lifecycle instructions. No general reduction in review cost or enforcement of a review-round limit is claimed.

## Requirements

1. Add a compact, read-only readiness decision packet to the existing guided readiness response/continuation path, derived from the same authority projection used for actions. Expose only bounded allowlisted current finding IDs, canonical disposition/blocking/terminal/repair facts, unresolved lane IDs and enum-valued judgment reasons already present in that projection. Copy no full evidence, document excerpts or arbitrary prose into this summary. Distinguish findings from missing approvals and invalid/unavailable authority. Bound rows and report totals/truncation; never imply omitted findings are cleared. Link to the existing focused_rereview information and canonical inspection tools. Do not add a second classifier, severity scale, ledger, gate or approval source.
2. Make the packet's safe operator choices explicit: authorize another named bounded repair/verification, amend scope and re-Prepare, request missing evidence or pause dependent work, or use an applicable explicit operator waiver through the existing protocol with its required rationale/residual-risk fields. No choice silently waives required specialist authority or accepts sensitive-data risk. Normal unfinished readiness is not an operator stop. State that the coordinator must apply the existing one-repair/one-focused-verification stop using actual review history; no stop, round count or elapsed-cost conclusion is inferred from receipt publications. The existing high-publication advisory remains advisory and can point to this packet/tool.
3. Update the canonical bounded-readiness handoff and focused briefing to make this packet usable: present remaining blocking findings separately from advisory notes, the precise unresolved obligation, evidence/uncertainty and affected lanes, and decision options before another automatic review begins. Finding source/blocking lanes replay the finding; other approving lanes check only cumulative delta effects plus necessary unchanged context, and new lanes review their remit once. Preserve every current-receipt reapproval requirement. Use existing focused_rereview data rather than copying full panels by default. Larger approval-currency/carry-forward optimization is deferred.
4. For migrations, reuse relevant working-source evidence with an explicit destination-risk delta: changed data, identity/permissions, persistence, exposure, trust/operating boundaries, and whether old evidence remains applicable. A documentation-only label is no security exemption. Missing decisive security evidence stays a blocker under existing semantics. Keep one bounded guidance walkthrough with discriminating controls; no agent-trial matrix or automatic extra batch.
5. Correct the broken Builder-lane allocation references in the canonical install implementation template and local Implement wave prompt to seed180's actual Wave orchestration contract / Allocation section. Clarify that Implement consumes current readiness authority rather than automatically calling Prepare; stale/missing authority follows the existing remedy. Clarify seed190's final newly applicable-lanes evaluation is not a blanket rerun of unchanged readiness Council: changed policy/roster still requires existing re-Prepare/current approval rules. Preserve valid aliases and handoff behavior.

## Scope

In scope: the guided readiness response helper in server_impl.py and focused existing tests; only the operator question string in review_evidence.focused_rereview and its relevant test expectations; canonical seeds209/215/100 and the affected install prepare/implement/close lifecycle template clauses, matching local prepare/implement/close and council/reviewer instruction surfaces actually owning those clauses; seed190 only its final-lane clarification; architecture/data-and-control-flow and changelog. Derive exact mirrored spans from canonical owners; do not bulk-render all platform files.

Out of scope: policy digest/currency redesign, automatic carry-forward, a new severity system or waiver path, mechanical review-round budget, changing the existing receipt-publication threshold, security/PHI exemptions, installed Teton changes, unrelated source/vision/package changes, commit/close/build/release. Preserve all previous wave history and current local1.39.0+q1ch work.

## Acceptance Criteria

- [x] AC-1: Registered readiness review and successful typed-write continuations expose the bounded canonical decision packet, including ordinary missing-approval state versus actual blocking findings and disclosed unavailable/truncated data. Delivery responses remain compatible. The old response without the packet fails the check; no-op/mutant controls must fail.
- [x] AC-2: Public-path controls distinguish an advisory editorial note from a required-AC security blocker, preserve existing classifications/approval gates, and keep publication-count telemetry from claiming or enforcing a round stop. Operator choices and existing focused-rereview navigation are visible without another classifier or bypass.
- [x] AC-3: One bounded coordinator walkthrough uses the packet and updated guidance to return unresolved post-verification obligations and concrete options to the operator, replays only affected findings/delta effects, and compares source evidence against a consequential migration destination delta. It rejects another automatic full-panel sweep and a documentation-only security exemption. This is a synthetic case, not proof of field time savings.
- [x] AC-4: Canonical/local instruction spans agree, both broken allocation references resolve to the actual source section, final new-lane evaluation and Implement's authority consumption are accurate, and valid existing aliases/handoff behavior remain unchanged. No Teton installation or actual vision is modified.

## Tasks

- [x] Implement the compact response packet and focused public-path regression controls.
- [x] Update canonical/local bounded-review, migration and lifecycle handoff guidance and architecture/changelog.
- [x] Execute the one bounded walkthrough and negative controls; retain unique evidence.
- [x] Complete required framework/docs validation and independent delivery review; update progress and handoff.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Response implementation | implementer | readiness | Reuse existing authority projection; no policy changes |
| Guidance/integration | coordinator | readiness | One writer for coupled canonical/local clauses |
| Independent review | selected reviewers | frozen packet | Same actual threads may perform explicit phase refreshes; no invented samples |

## Serialization Points

Readiness precedes any source edit. Freeze material code/guidance and unique evidence before the final suite; do not mutate sources during review. Coordinator serializes ledger writes.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_readiness_convergence.py`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/seeds/215-council-chair.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/190-close-wave.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/close-wave.prompt.md`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/prompts/implement-wave.prompt.md`
- `docs/prompts/close-wave.prompt.md`
- `docs/agents/specialists/council-chair.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

Update data-and-control-flow.md for the advisory response packet, existing-authority source and focused handoff. No change to policy/current-approval authority.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Makes the existing review facts actionable in the served response. |
| AC-2 | required | Preserves blocking authority and honest telemetry. |
| AC-3 | required | Tests the intended focused operator decision with realistic security limits. |
| AC-4 | required | Corrects the deferred lifecycle references and semantic ambiguity. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-05 | Complete: all four ACs and tasks are met. Code, QA, architecture, docs-contract and security independently approve the frozen delivery; no findings or delivery Council remain. Wave stays open for operator direction. | Current receipt review-policy-a79b6a81e3d0347642c3; typed events.jsonl. Canonical suite passed 12,314 tests across 217 files, with 12 intended skips, in 571.576s; inputs b59b0e60776d2eee5b6968bab74d002b2c70112d5843c5d03a3b96c28ed3f304. Full docs validation and diff check passed. |
| 2026-11-05 | Observe: focused readiness refresh passed before the question-only review_evidence edit; all five lanes and the selected red-team/docs-contract readiness Council approved the amended scope. Delivery reviewers independently confirmed public-path controls and safe handoff limits. | Four delivery reviewers retained prior readiness context only; docs-contract used a fresh actual thread. No implementation/repair context or additional independent-sample claim. Independent missing-packet, byte-cap, evidence-leak and broken-reference controls rejected the corresponding defects. |
| 2026-11-05 | Observe: implementation source frozen; 14readiness/223review-evidence/661lifecycle tests pass(2lifecycle skips). Registered read/postwrite continuity, unchanged activation, one coordinator handoff and reference checks pass. | delivery-evidence.json; 3process-local mutants detected;16materialpaths frozen. Initial allocation probe assumed Markdown headings; actual plain contract label/bold Allocation clause verified, no product correction. Fresh delivery/fullsuite pending. |
| 2026-11-05 | Observe: derived fresh-install prepare/close templates own the same clauses and are updated narrowly with their local mirrors; no platform-wide render. Canonical209/215/100 guidance, allocation and final-lane/current-authority instructions are updated. New focused_rereview question owner stays paused pending its readiness refresh. | Existing-owner derivation from install/lifecycle-prompts prepare/close; root approved bounded coupled clauses. All snapshots use .snapshot. |
| 2026-11-05 | Scope discovery: amend owningScope/ReviewTargets for one focused_rereview question and its tests, plus prepare/close template mirrors; refresh affected readiness before editing that new owner. Independent already-readied server/guidance work may continue. | Proposed question: Does the cumulative change since your last approval alter your verdict? Use the full amended plans and dependency context as needed to assess that delta; do not repeat an unrelated whole-document sweep. |
| 2026-11-05 | Readback: expose a compact readiness packet from existing projection facts, distinguish blockers/notes/pending approvals without policy changes, and make focused operator/migration/lifecycle handoffs usable. Runtime implementer owns server/tests; coordinator owns coupled guidance. | AC1–4; all5readiness lanes and standardred-team/docs-contract Council pass onf3268f70eeaa7ce39393. Prepare ready and Implement passed; paired edit gates open. No source edits before readiness. |
| 2026-11-05 | Planning: current classifiers and registered readiness path executed under temporary roots; no source edits. | Optional editorial classified maybe_later/nonblocking; required security AC do_now/blocking. wf_review_wave has focused_rereview but no decision packet. Current snapshot/receipt behavior retained. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Include the focused_rereview operator question and exact install-template mirrors. | Its existing instruction to review full amended plans could be read as another whole-document sweep, contradicting the intended delta-effect check. Change only that question to use full context as needed; no approval currency changes. Prepare/close template clauses are actual fresh-install owners of the same guidance. | A server override would duplicate ownership; leaving the old question risks contradictory instructions. |
| 2026-11-05 | Select compact response visibility plus focused guidance and reference corrections. | Existing projection already supplies dispositions, blockers and lane facts; exposing it makes the stop/choice handoff usable without a policy redesign. Readiness guidance controls behavior normatively; public packet controls observable visibility only. Success is discriminating served controls plus one synthetic handoff; field adherence/cost remains unproven. | Guidance-only repeats instructions already ignored; automatic round enforcement/carry-forward redesign changes authority and is larger than the requested simple improvement. |
| 2026-11-05 | Defer approval-currency/carry-forward optimization. | Required approvals remain current under existing policy; cumulative delta checks can be made usable now without risky approval transfers. | Receipt-count stop would confuse publications with rounds and falsely claim budget enforcement. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A compact packet hides required findings. | Canonical facts only; bounded output declares omissions and retains full-inspection route. |
| Options imply authority or security waiver. | Explicit existing-protocol requirements; no automatic selection, new waiver or classifier. |
| Migration evidence reuse overlooks a changed exposure. | Destination delta and security-negative control; documentation-only is no exemption. |
| An unverified field incident is presented as reproduced root cause. | Preserve source/version/log limits; test the narrower observed mechanism. |

## Session Handoff

See docs/agents/session-handoff.md for current session state.
