# fragile-run-garden-output-contract

Owner: Engineering
Status: archived
Last verified: 2026-07-22

Memory ID: `1tboh-mem fragile-run-garden-output-contract`
Superseded by: `1u8q1-mem server-impl-file-playbook`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-07-22
Updated: 2026-08-02
Source event: `repeated-repairs:1tbvp:run_tests.py`
Validation: promote
Validated by: agent
Action delta: Before touching run_garden or the gardener's stdout, re-read both sides of the output contract and run the canonical-producer integration and over-cap tests; verify envelope claims with a live post-reload MCP probe.
Validation rationale: The drafted candidate misattributed the fragile target to run_tests.py, which appears only as the verification command in both findings' evidence; both repairs (the 'wrote'-grep contract break and the bounded-output parse) landed in server_impl.py run_garden. The fragile-area signal is real: the gardener-envelope contract broke twice in one wave, each time invisible to hand-written fixtures.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

Archived: 2026-08-02
Archive reason: Superseded by a verified consolidated file playbook after retention review.
Archive path: `docs/agents/memory/archive/1tboh-mem fragile-run-garden-output-contract.md`
## Summary

run_garden in server_impl.py needed two repairs in wave 1tbvp: its 'wrote'-grep silently broke when the gardener's stdout wording changed (dropping the index-refresh trigger), and its exact-prefix replacement then parsed the BOUNDED 200k output, under-counting large runs with a corrupted final path. The gardener-stdout-to-envelope contract is fragile: parse the complete result.stdout with the exact `docs-gardener: updated <path>` prefix, keep the bound for the human-facing output field only, and verify any change with the canonical-producer integration tests, the over-cap regression, and a live post-reload wf_garden_docs probe.

## Evidence

- `run-garden-stdout-contract-break`
- `run-garden-parses-bounded-output`
- `1tbvp`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/docs_gardener.py`
