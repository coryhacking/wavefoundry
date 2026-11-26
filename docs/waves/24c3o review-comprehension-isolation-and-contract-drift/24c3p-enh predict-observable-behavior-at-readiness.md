# Predict observable behavior during readiness review

Spec ID: `24c3p-enh predict-observable-behavior-at-readiness`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-25
Wave: 24c3o review-comprehension-isolation-and-contract-drift

## Rationale

Two reviewers can approve the same words while expecting different results. The upgrade summary repair in 24buu illustrates the cost of discovering that difference at delivery.

## Product Intent

An implementer learns before building when an assigned reviewer reads a material promise differently from the author.

## Requirements

1. Use an already assigned independent reviewer, preferably QA where assigned. Give them the spec and its cited contracts before separate author commentary, examples of the desired answer or peer verdicts. Keep governance and the spec’s own rationale available. If the council primer or seat packet can disclose the answer, collect the assigned reviewer’s unedited prediction in a first exchange before sharing the primer. Then give that reviewer the ordinary primer and packet to finish review. Use an already assigned independent seat when QA is absent.
2. For one representative case, record the input, observable result, and an observation that would disprove the prediction. Compare with intended behavior after committing the prediction. Use the existing finding path if two plausible readings change delivery.
3. Keep the exercise in ordinary readiness evidence. Reuse existing evidence when it already answers the question. Preserve the small-change policy and existing approval rules.

## Scope

Keep the exercise in ordinary readiness evidence. Reuse existing evidence when it already answers the question. Preserve the small-change policy and existing approval rules.

## Acceptance Criteria

- [x] AC-1: On the upgrade-summary fixture, a reviewer predicts which primary and cleanup information the operator sees and what the machine consumes. A missing primary-only detail can falsify the prediction even when one terminal sentinel appears.
- [x] AC-2: On an ambiguous variant, retain the original prediction and show which ambiguity needs a decision. On a precise variant, the reviewer can approve using the same evidence without raising a finding.
- [x] AC-3: Rendered readiness guidance works with or without an assigned QA seat. No new role, approval, or schema field is required.

## Tasks

- [x] Update the readiness brief and reconcile the local prompt.
- [x] Use one short upgrade-summary walkthrough. An assigned reviewer records the prediction before clarification, then checks it against the clarified wording. Include an answer-revealing primer and retain the order of the two exchanges. Inspect the rendered prompt for the fallback when QA is absent.

## Agent Execution Graph

1. Implementer updates the named guidance or qualification procedure.
2. The assigned reviewer checks the observations against the acceptance criteria during normal delivery review.

## Serialization Points

- `.wavefoundry/framework/seeds/215-council-chair.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md`
- `docs/prompts/prepare-wave.prompt.md`

## Affected Architecture Docs

N/A. This change extends an existing workflow within its current authority.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the stated outcome or its scope boundary. |
| AC-2 | required | Establishes the stated outcome or its scope boundary. |
| AC-3 | required | Establishes the stated outcome or its scope boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-25 | Planned for wave admission. | Requirements and acceptance criteria above. |

The first exchange supplied only this synthetic spec: “During an automatic cleanup upgrade, show a summary after each stage. Machine consumers count one terminal completion sentinel.” The independent reviewer received a primary scan warning and successful cleanup as inputs. Its unedited response follows.

> I predict the primary stage shows one summary reporting both the scan warning and the successful cleanup. The stage summary does not emit a completion sentinel. I would expect one sentinel when the upgrade ends.
>
> A primary-stage summary that reports successful cleanup but omits the scan warning would disprove my prediction about what the user sees.
>
> The spec requires a summary after each stage, but leaves its contents open. It also leaves unclear whether the sentinel is visible to users or only to machine consumers.

The second exchange supplied the intended stage boundaries and the single terminal sentinel. The same reviewer identified its mistaken placement of the cleanup result and correctly predicted the two separate summaries. The Prepare routes prefer QA when assigned and otherwise use an assigned independent reviewer.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-25 | Use an assigned reviewer. | Two reviewers can approve the same words while expecting different results. The upgrade summary repair in 24buu illustrates the cost of discovering that difference at delivery. | A new comprehension lane adds staffing. Delivery-only review discovers the mismatch after implementation. |

## Risks

Reviewers may recite the desired answer. Separate prediction from comparison and retain their order.

## Session Handoff

See the wave record for coordination.
