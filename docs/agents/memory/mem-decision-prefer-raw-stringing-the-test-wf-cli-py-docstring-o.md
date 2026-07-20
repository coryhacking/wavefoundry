# Decision: Prefer raw-stringing the `test_wf_cli.py` docstring over de…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-prefer-raw-stringing-the-test-wf-cli-py-docstring-o`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9p6-bug python-parse-filename-and-invalid-escape:207aa97f7c37d8b5`
Validation: reject
Validated by: agent
Action delta: None; choose the smallest source correction when a current invalid escape is found.
Validation rationale: The one-token docstring repair is too specific to affect future behavior beyond the active parser-diagnostics memory.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p9pe): Prefer raw-stringing the `test_wf_cli.py` docstring over deleting the backtick example.. Rationale: Preserves the docstring's illustrative intent (a bare prose mention of a script name is allowed) with a one-token change..

## Evidence

- `1p9p6-bug python-parse-filename-and-invalid-escape`
- `1p9pe`

## Targets

- `test_wf_cli.py`
