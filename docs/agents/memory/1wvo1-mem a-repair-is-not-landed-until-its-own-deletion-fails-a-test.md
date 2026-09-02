# A repair is not landed until its own deletion fails a test

Owner: Engineering
Status: active
Last verified: 2026-09-01

Memory ID: `1wvo1-mem a-repair-is-not-landed-until-its-own-deletion-fails-a-test`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-09-01
Updated: 2026-09-01

## Summary

After writing any guard, delete it and run the suite. If nothing fails, the guard is not landed — write the discriminating fixture before moving on. Wave 1wur7 needed FOUR repair rounds because this was skipped each time, and every round was reopened by an independent lane rather than by the implementer. The recurring shape: a mechanism ships with a fixture that would survive its removal. Concrete instances, all confirmed by executing the mutant: removing the straight-apostrophe branch from `_AC_CODE_SPAN_RE` was undetectable by 1058 tests; the runner pattern's two lookaheads were pinned only in conjunction, so either could be deleted alone; `tests/` in `_AC_REPO_REFERENT` stayed dead-then-unpinned because the pin written to cover it matched through the widened scope gap and never reached the referent; the close gate's call site in `wf_close_wave_response` could be replaced with a hardcoded value with all 516 lifecycle tests green, because every existing close test used a temp root with no runner and took the not_applicable path. Two second-order lessons. First, a pin that passes is not a pin that discriminates: construct the input where ONLY the mechanism under test can change the outcome, then verify the mutant fails. Second, prose is a mechanism too — `testing-architecture.md` asserted a FOUR-effect inventory while the code it described said FIVE, because no test guarded the sentence.

## Evidence

- `1wur7 evaluator-identity-and-ac-locality`
- `QA-DEL-1`
- `QA-DEL-2`
- `DOCS-DEL-2`
- `test_possessive_apostrophes_do_not_form_a_swallowing_span`
- `test_the_side_effect_inventory_is_stated_consistently`
- `test_a_change_whose_subject_is_the_runner_is_not_flagged`
- `test_close_response_carries_the_receipt_and_blocks_on_a_stale_one`

## Targets

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
