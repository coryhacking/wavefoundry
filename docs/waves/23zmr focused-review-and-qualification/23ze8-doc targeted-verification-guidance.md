# Target verification at the reported failure

Change ID: `23ze8-doc targeted-verification-guidance`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-21
Wave: 23zmr focused-review-and-qualification

## Rationale

A full suite can expose a small contract failure that a focused test would catch earlier. Several lanes can also describe one underlying failure, and a comparison where both runs pass can be mistaken for evidence of improvement.

## Product Intent

Builders and reviewers identify an affected contract early, repair a shared failure once with each lane's observation intact, and tell whether a before-and-after comparison demonstrates the intended change. The guidance supports these decisions without changing release qualification.

## Requirements

1. Run available fast checks for the affected contract before the full suite. For lifecycle changes, illustrate how to select a relevant census, contract fixture or targeted test. Keep every required suite, review and release profile.
2. Before recording findings, group observations only when they share the underlying failure, corrective action and expected outcome. Preserve every contributing lane and its individual observations. Keep distinct failures and existing typed findings independently traceable and preserve required lane verification.
3. Before a comparison, identify the motivating case and the observable outcome that distinguishes the old and proposed behavior. When both runs meet the same check, record preservation alone. State what evidence would distinguish improvement if it remains unproven.

## Scope

Update seed 209's existing review and qualification guidance and add a short pointer in Wavefoundry's review guide. Existing tools, ledger schemas, required approvals, full-suite coverage and release gates retain their current behavior. No timers or new reports.

## Acceptance Criteria

- [x] AC-1: For a representative lifecycle defect, a builder selects the affected fast contract check, predicts the specific failure, observes it on the known-bad case and a pass on the valid control, then identifies the required full qualification. Existing recorded positive and negative results can supply this evidence.
- [x] AC-2: A reviewer replaying reports from two lanes records one finding when failure, repair and outcome match, retains both observations and lanes, and keeps a report requiring a different repair or outcome separate.
- [x] AC-3: A reviewer states the expected distinguishing observation before running a comparison, identifies two equal passes as preservation, and identifies the missing evidence for any improvement claim.

Together these criteria establish the decisions the guidance supports. They do not measure elapsed-time savings across projects.

## Tasks

- [x] Revise seed 209 and link the local review guide to its instructions.
- [x] Replay the three decisions against the old and revised instructions and run required validation. For AC-1, exercise the registered lifecycle carrier census with an omitted installed Prepare prompt and the intact registry.

## Agent Execution Graph

| Workstream | Owner | Depends on |
| --- | --- | --- |
| Guidance and local pointer | Technical writer | Readiness |
| Scenario verification | QA and docs contract reviewers | Guidance |

## Serialization Points

- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `docs/contributing/review-and-evals.md`

## Affected Architecture Docs

N/A. Editorial instructions use existing lifecycle mechanisms and evidence contracts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Checks run early and retain qualification. |
| AC-2 | required | Grouping preserves each independent observation. |
| AC-3 | required | Evidence supports only the outcome actually observed. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-21 | Planned a bounded guidance change. | Requirements and scenario-based acceptance criteria above. |
| 2026-11-21 | Readback: seed 209 will tell builders to exercise the affected contract before full qualification, and tell reviewers when to group reports and what equal passing runs prove. The local review guide will point to that guidance. | AC-1–3. An omitted Prepare carrier should fail the fast registry check while its valid control passes. Required reviews and full-suite coverage remain in force. |
| 2026-11-21 | Delivery QA and docs contract reviewers verified the three replay scenarios; council confirmed the intent outcome. No workflow state or release gates changed. | Registry carrier census accepted intact inputs, rejected only the omitted Prepare prompt, then passed on restoration. The guide’s three links resolved; a deliberately broken comparison fragment failed exactly once. The full docs check and 22 targeted tests passed. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-21 | Extend the existing review guidance. | Every case is a reviewer or builder decision. | A new gate would increase overhead. A repository-only note would miss installed projects. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Consolidation could hide disagreement. | Preserve each observed case and contributor, and keep distinct findings separate. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
