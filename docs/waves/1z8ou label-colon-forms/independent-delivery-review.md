# Independent delivery review

Owner: Engineering
Status: active
Last verified: 2026-09-28

## Verdict

Approve. No blocking findings. Separate code/architecture and QA reviews agree that the objective is met. Neither reviewer implemented this change. Reviewer contexts were reused from review of an unrelated wave; this report does not claim newly spawned contexts or replace existing typed approvals. Operator signoff remains operator-owned.

## Evidence

- Coordinator canonical focused run: 53 tests across vocabulary profile, second profile, label-reader census and vocabulary census; all passed, no skips. Each reviewer separately ran the first three suites (48 tests) successfully.
- Full-suite receipt independently recomputed against the framework: current and green, 9,917 tests. This review did not rerun the full suite.
- The validator accepts the requested `Wave`, `Wave ID`, `Wave Status` profile, including archive validation, and suffix pairs. It rejects casefolded duplicates and fixed-label collisions. Heading rules are unchanged.
- The fixture's back-reference differs from its folder fallback; admission repairs a placeholder; removal changes the actual admitted IDs; explicit expected values establish member ID and status behavior.
- Direct execution of the removal pattern with member label `ID` matches a canonical block but refuses `Wave ID:` and prose-prefixed blocks.
- Independent scratch controls reverting all six anchors are caught by the census, which identifies the four wave-validator sites and the removal/template-fill sites. Reverting the prefix rule, duplicate casefolding and fixed-label casefolding is caught. Unanchoring the status reader produces wrong member statuses and fails; matching a bare back-reference returns `planned` rather than the set ID and fails.
- The second-profile driver alone does not kill every anchoring revert. Its Progress Log accurately states that the census provides those particular controls.

## Nonblocking limitation

Both reviewers and the coordinator reproduced a lexical-census limitation at `test_label_reader_census.py:48`: a planted `re.search(rf"\^{_vocab.ID_KEY_RE}:", text)` is accepted even though its caret is literal rather than a start anchor. No current shipped reader uses this form. Document this heuristic limit or add an escaped-caret negative control in a follow-up; it does not invalidate the current six fixes.

## Stable fingerprints

Relevant Git blob hashes were unchanged across review:

| File under framework scripts | Hash |
| --- | --- |
| vocabulary_profile.py | 0f88c64176957688472acb00711dd18995efbe4a |
| wave_lint_lib/wave_validators.py | aef9b4c7b20d81df5fc5a58542b416489fea45bb |
| wf_server/server_impl.py | 266055f7815bd6a5bcbcc51c5d19944dd36a958f |
| tests/test_label_reader_census.py | 705c090aab6f47bb2144bed0a4a067e2d35d3658 |
| tests/test_vocabulary_second_profile.py | 84264bcb5010c05624f74d90e8868d78f1ab0cfa |

All mutations were in memory or temporary copies. No production implementation edits, commits, closure, or operator approval were performed.
