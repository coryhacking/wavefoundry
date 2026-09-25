# Readiness Review: 1yzj9 sensor-advisory-decisions

Owner: Engineering
Status: active
Last verified: 2026-09-24

## Round 1 (full review)

Receipt `review-policy-5b58c38ff28988a1ed02`. Red-team seat (isolated) approved with six non-blocking notes. A combined context ran docs-contract (rotating seat), architecture, code and QA: architecture, code and QA approved; docs-contract blocked on DOCS-READY-1, because seed 170 and `plan-feature.prompt.md` say the release checklist lists every advisory sensor, which becomes false once decided sensors leave the checklist, and the prompt mirror was not a named target.

## Repair (one bounded pass)

The change doc Requirements through Tasks were rewritten: the clause reworded in seed 170 and mirrored in `plan-feature.prompt.md`; the `constants.py` comment and sensor docstring added; validation placed beside the polarity check with a non-empty-string rule; the exact decided suffix specified; both entries recorded under `1yzj9` with a Decision Log row for `inert_record_layout_config` and one superseding the `1wujs` flip condition; test census widened to `AdvisoryFirstRulePinTests` (lifecycle-test strings are synthetic and need no edit); AC-1 reworded to an in-scope wave with a CLI suffix assertion; the field-data script now prints every Rationale figure, the hit list and the seeded sample.

## Round 2 (focused verification)

Pending: docs-contract confirmation of DOCS-READY-1.
