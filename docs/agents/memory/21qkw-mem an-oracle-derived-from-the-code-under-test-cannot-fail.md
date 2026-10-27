# An oracle derived from the code under test cannot fail

Owner: Engineering
Status: active
Last verified: 2026-10-27

Memory ID: `21qkw-mem an-oracle-derived-from-the-code-under-test-cannot-fail`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-10-27
Updated: 2026-10-27

## Summary

When a test's expected value is read from the same table or function the code uses (e.g. expected label = LABELS[code] || fallback), a broken table still passes: a blanked label fell back to the generic text on both sides. Assert fixed literal expectations written in the test, then confirm with a mutant that blanks or swaps one entry.

## Evidence

- `21rft`
- `21rf7-bug dashboard-refusal-follow-ups`
- `QA-DEL-1`
- `test_dashboard_server.DashboardStaleRuntimeReportingTests.test_refused_index_renders_one_explanation_on_every_surface`

## Targets

- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
