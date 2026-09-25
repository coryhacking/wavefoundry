# Readiness Review: 1yzj9 sensor-advisory-decisions

Owner: Engineering
Status: active
Last verified: 2026-09-25

## Round 1 (full review)

Receipt `review-policy-5b58c38ff28988a1ed02`. Red-team seat (isolated) approved with six non-blocking notes. A combined context ran docs-contract (rotating seat), architecture, code and QA: architecture, code and QA approved; docs-contract blocked on DOCS-READY-1, because seed 170 and `plan-feature.prompt.md` say the release checklist lists every advisory sensor, which becomes false once decided sensors leave the checklist, and the prompt mirror was not a named target.

## Repair (one bounded pass)

The change doc Requirements through Tasks were rewritten: the clause reworded in seed 170 and mirrored in `plan-feature.prompt.md`; the `constants.py` comment and sensor docstring added; validation placed beside the polarity check with a non-empty-string rule; the exact decided suffix specified; both entries recorded under `1yzj9` with a Decision Log row for `inert_record_layout_config` and one superseding the `1wujs` flip condition; test census widened to `AdvisoryFirstRulePinTests` (lifecycle-test strings are synthetic and need no edit); AC-1 reworded to an in-scope wave with a CLI suffix assertion; the field-data script now prints every Rationale figure, the hit list and the seeded sample.

## Round 2 (focused verification)

Completed in the typed ledger at receipt `review-policy-fa39d1cf2c158974fbc0`: docs-contract confirmed DOCS-READY-1 resolved; code, QA, architecture and the readiness council approved. The council recorded red-team (fixed, isolated) and docs-contract (rotating), with the remaining specialist reviews recorded separately. This paragraph reconciles the previously stale narrative; it is not a new approval.

## Prepare and focused check, 2026-09-25

`wf_review_wave(phase='prepare')` confirmed all four required specialist approvals current. `wf_prepare_wave(mode='ready')` succeeded with lint and gardening passed, the same receipt, and no activation. Existing typed approvals remain the readiness authority; no implementation work was performed.

The coordinator checked the current registry, routing branches and public CLI test fixture. An isolated red-team follow-up found no implementation-design blocker and recommended carrying two wording qualifications into implementation:

- Describe the field data as an observed decline in final-document findings after introduction, not proof that guidance and warnings caused the decline. The sample cannot observe intermediate revisions or separate their effects.
- Scope the close-receipt reassurance to the Wavefoundry incident. The framework receipt covers framework inputs and is not applicable where the runner is absent; it is not a general consumer-repository test guarantee.

Strongest challenge: a standing advisory decision is not a guarantee about future heuristic quality. Strongest alternative: keep the small registry field and conservative evidence wording; no additional validator mechanism is warranted. The existing Risks section already permits reconsideration in a later wave. A whitespace-only decision value should be treated as empty when implementing the non-empty-string contract.

This follow-up reviewed the plan and current source, without executing the unimplemented tests or claiming delivery approval. The two wording qualifications are implementation notes, not a new review gate.
