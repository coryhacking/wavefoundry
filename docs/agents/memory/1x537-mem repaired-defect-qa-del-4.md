# Repaired defect QA-DEL-4

Owner: Engineering
Status: superseded
Last verified: 2026-09-04

Memory ID: `1x537-mem repaired-defect-qa-del-4`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 458752
Source event: `finding:1wpih:QA-DEL-4`
Validation: rewrite
Validated by: agent
Action delta: Before marking an acceptance criterion met, open every artifact its requirement names by path and confirm the file exists; and when a change adds a new standing report or corpus family, add its glob to `.aiignore` in the same edit, because `.json` is an indexed source extension and an unignored measurement becomes its own search answer.
Validation rationale: Verified against the evidence chain and the current tree. Requirement 9 of `1wpie` names `docs/reports/graph-quality-baseline.json` and `docs/reports/graph-quality-post.json` by path; neither existed, and `graph_quality_eval.py` had no report builder, no writer, and no report flag -- only a corpus-summary command line. AC-9 nonetheless read as met because its other half, the injected-forbidden-edge and deleted-expected-edge mutation controls, was genuinely delivered and passing. That is the reusable shape: a criterion with two clauses can look satisfied on the strength of one. The second lesson came out of the repair itself. Writing the two reports put them straight into the graph, because `.aiignore` listed every other standing report family (`retrieval-quality-*`, `lexical-ranking-*`, `ann-reference-*`) and not this one; `test_the_canonically_ignored_standing_artifacts_are_absent` caught it. The ignore line alone was not treated as the fix -- `write_report` now refuses an unignored in-repository destination with `self_contaminating_artifact`, and deleting that guard fails two named tests. The generated summary quoted the reverification's disposition line rather than either lesson, so the record is rewritten.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1x40o-mem a-two-clause-acceptance-criterion-can-read-as-met-on-one-cla`
## Summary

Real defect fixed in wave 1wpih: Reverified by a different lane than the one that raised it, with the guard proved by deletion rather than by a passing assertion.

## Evidence

- `QA-DEL-4`
- `ev-qa-del-4-3`
- `1wpih`

## Targets

- `graph_quality_eval.py`
