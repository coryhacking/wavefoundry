# A two-clause acceptance criterion can read as met on one clause

Owner: Engineering
Status: active
Last verified: 2026-09-04

Memory ID: `1x40o-mem a-two-clause-acceptance-criterion-can-read-as-met-on-one-cla`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 458752
Source event: `finding:1wpih:QA-DEL-4`
Validation: promote
Validated by: agent
Action delta: Before marking an acceptance criterion met, open every artifact its requirement names by path and confirm the file exists; and when a change adds a new standing report or corpus family, add its glob to `.aiignore` in the same edit, because `.json` is an indexed source extension and an unignored measurement becomes its own search answer.
Validation rationale: Verified against the evidence chain and the current tree. Requirement 9 of `1wpie` names `docs/reports/graph-quality-baseline.json` and `docs/reports/graph-quality-post.json` by path; neither existed, and `graph_quality_eval.py` had no report builder, no writer, and no report flag -- only a corpus-summary command line. AC-9 nonetheless read as met because its other half, the injected-forbidden-edge and deleted-expected-edge mutation controls, was genuinely delivered and passing. That is the reusable shape: a criterion with two clauses can look satisfied on the strength of one. The second lesson came out of the repair itself. Writing the two reports put them straight into the graph, because `.aiignore` listed every other standing report family (`retrieval-quality-*`, `lexical-ranking-*`, `ann-reference-*`) and not this one; `test_the_canonically_ignored_standing_artifacts_are_absent` caught it. The ignore line alone was not treated as the fix -- `write_report` now refuses an unignored in-repository destination with `self_contaminating_artifact`, and deleting that guard fails two named tests. The generated summary quoted the reverification's disposition line rather than either lesson, so the record is rewritten.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

QA-DEL-4 (wave 1wpih): AC-9 was marked met while the two report artifacts its Requirement 9 names by path did not exist and `graph_quality_eval.py` had no code path that could write them. It looked satisfied because its other clause, the injected-edge mutation controls, was delivered and passing. Open every artifact a requirement names by path before marking the criterion. The repair produced a second lesson: writing the reports put them into the graph, because `.aiignore` listed every other standing report family and not this one, and `.json` is an indexed source extension. Add the glob in the same edit that creates the family, and back it with a writer that refuses an unignored in-repository destination (`self_contaminating_artifact`) rather than trusting the ignore line to be remembered.

## Evidence

- `QA-DEL-4`
- `ev-qa-del-4-3`
- `1wpih`
- `test_graph_quality_eval.ShippedReportPairTests`
- `test_graph_quality_eval.ReportSelfContaminationTests`
- `test_graph_quality_eval.LiveGraphEvidenceControlTests.test_the_canonically_ignored_standing_artifacts_are_absent`

## Targets

- `.wavefoundry/framework/scripts/graph_quality_eval.py`
- `.wavefoundry/framework/scripts/tests/test_graph_quality_eval.py`
- `.aiignore`
