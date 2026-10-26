# AC-6 follow-up: gap-free control run

Owner: implementer
Status: active
Last verified: 2026-10-25

Written by the coordinator before the control plan exists, on operator direction ("independently written, gap-free control plan, run once, to test the over-flagging question").

Question: does the qa-reviewer's intent-coverage duty over-flag, that is, raise an intent-coverage finding on a plan whose ACs genuinely cover its Product Intent?

Procedure:

1. A separate agent authors a small, well-bounded control plan (`plan-d-*.txt`) in neutral wording, with ACs intended to cover every stated part of its Product Intent. The author is not told the plan is a control or that a reviewer will be tested.
2. A second, independent agent vets the plan adversarially for intent coverage only and reports any part of the Product Intent no AC tests. The author may revise once from the vetting notes. This prepares the fixture; it is not a reviewer retry. The plan then freezes.
3. One fresh qa-reviewer, briefed only with `docs/agents/qa-reviewer.md` and the same neutral brief used for plans A to C, reviews the frozen plan once.
4. If the qa-reviewer raises any intent-coverage finding, a fresh, independent council seat adjudicates each one against the plan text: genuine gap (the fixture was not gap-free) or over-flag.

An intent-coverage finding is a stated part of the Product Intent that the reviewer says no AC tests. Other findings (testability, negative paths, wording) are not intent-coverage findings and do not count.

Outcomes, fixed in advance:

- Pass: the qa-reviewer raises no intent-coverage finding on the frozen plan.
- Over-flag shown: the qa-reviewer raises one or more intent-coverage findings and the adjudicator rules at least one an over-flag.
- Inconclusive: every intent-coverage finding raised is ruled a genuine gap. The fixture was not gap-free; no further run.

There is one run. Whatever the outcome, it is recorded in `ac6-results.md` and the finding 21KK5-DEL-AC6 is re-triaged on that evidence.
