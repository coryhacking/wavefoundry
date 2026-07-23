# Fragile: run_tests.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-22

Memory ID: `1tage-mem fragile-run-tests-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-22
Updated: 2026-07-22
Source exploration cost: 102216
Source event: `repeated-repairs:1tbvp:run_tests.py`
Validation: rewrite
Validated by: agent
Action delta: Before touching run_garden or the gardener's stdout, re-read both sides of the output contract and run the canonical-producer integration and over-cap tests; verify envelope claims with a live post-reload MCP probe.
Validation rationale: The drafted candidate misattributed the fragile target to run_tests.py, which appears only as the verification command in both findings' evidence; both repairs (the 'wrote'-grep contract break and the bounded-output parse) landed in server_impl.py run_garden. The fragile-area signal is real: the gardener-envelope contract broke twice in one wave, each time invisible to hand-written fixtures.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tboh-mem fragile-run-garden-output-contract`
## Summary

run_tests.py required 2 separate repairs during wave 1tbvp; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `run-garden-stdout-contract-break`
- `run-garden-parses-bounded-output`
- `1tbvp`

## Targets

- `run_tests.py`
