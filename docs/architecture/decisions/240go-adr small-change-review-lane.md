# 240go-adr — Plan an operator-selected small-change review lane

Owner: Engineering
Status: accepted
Last verified: 2026-11-21

## Context

The framework already reduces delivery review for some changes. In the 30 most recent closed waves with typed review records in the sample, 14 used targeted delivery without a council. Only two had a single required readiness specialist, and both required documentation review. These counts establish how often those rules applied in this repository. They do not establish how much time a new lane saves.

Small edits still carry meaningful review work. In 210e9, QA caught a regression fixture that needed to be Git-tracked. In 210eb, the code reviewer approved a compatibility promise on a two-line filter. The council corrected it: previously written setup stamps still needed setup or upgrade. That shows what the second review contributed on this occasion. The dashboard repair in 2423b changed a public snapshot contract and would take ordinary review even though the visible defect was a repeated card.

## Decision

Plan a permanent, operator-selected lane for eligible small internal changes, with one independent code reviewer at readiness and delivery. Asked whether to keep the current rules and measure first or pursue the permanent lane, the operator chose **“Plan the permanent small-change lane”**. The follow-up spec owns implementation. The current release continues to enforce its existing gates.

## Consequences

An eligible change would need fewer reviews before delivery. The operator still chooses the scope, signs off on delivery and directs closure. The test receipt remains a close requirement. A brief description alone cannot establish eligibility. An undeclared file, a public behavior change or a need for another specialist sends the work through ordinary review.

Implementation must join the selection to the review-policy receipt. Prepare and Close both check the readiness signoff, and activation requires current readiness authority. Modifying only lane selection would leave the council signoff in force. A receipt must identify the reviews that actually ran.

## Alternatives Considered

| Alternative | Tradeoff |
| --- | --- |
| Continue with targeted delivery, focused re-review and named waivers (C). | Lowest implementation cost. A waiver still requires an individual policy exception and gives operators no standard path for repeated small fixes. |
| Reduce the readiness roster only (B). | Preserves delivery specialists. Under the one-required-specialist rule, two of the 30 sampled waves could have qualified. Revisit if delivery review catches material issues that escape the small lane. |
| Measure three changes before planning a policy (C with a comparison). | Would provide better timing data, but the operator prefers to plan the permanent path now. Measure actual results during qualification and early use. |

## Revisit conditions

Compare elapsed readiness time, reviewer effort, escalation frequency and material findings from the first eligible uses. Have an independent ordinary review examine the same inputs in a few early cases. Compare findings after both sides have recorded them. Track queue and full-suite time separately. Reconsider the eligibility boundary if small internal fixes rarely qualify, if reviewers routinely escalate, or if an omitted specialist would have caught a material defect. The follow-up proposes a three-file limit and one spec per wave for initial qualification. Those are design parameters for review.

## References

- [Decision spec 2136q](../../waves/241lp%20operator-selected-small-change-review/2136q-change%20small-change-lane.md)
- [Implementation spec 240t6](../../waves/241lp%20operator-selected-small-change-review/240t6-enh%20operator-selected-small-change-lane.md)
- [Feedback on the setup filter](../../waves/210eb%20setup-readiness-config-notes/events.jsonl)
- [Fixture and compatibility review](../../waves/210e9%20python-3-11-test-compatibility/events.jsonl)
