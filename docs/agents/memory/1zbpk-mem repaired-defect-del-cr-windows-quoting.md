# Repaired defect DEL-CR-WINDOWS-QUOTING

Owner: Engineering
Status: superseded
Last verified: 2026-09-29

Memory ID: `1zbpk-mem repaired-defect-del-cr-windows-quoting`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 526079
Source event: `finding:1zc7n:DEL-CR-WINDOWS-QUOTING`
Validation: rewrite
Validated by: agent
Action delta: When a test asserts on a process_info.cmdline rendering, compute the expected substring with subprocess.list2cmdline on nt and a space join elsewhere; never hard-code the POSIX form.
Validation rationale: DEL-CR-WINDOWS-QUOTING: two tests required unquoted '--root /tmp/a b' and would fail on native Windows, where process_info._render uses list2cmdline. The generated candidate's summary restated the disposition only and its targets were not repo-relative.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zbe6-mem command-line-test-expectations-must-be-platform-rendered`

## Summary

Real defect fixed in wave 1zc7n: Repair resolves the finding: expectations are platform-aware and spaced-argument coverage is kept

## Evidence

- `DEL-CR-WINDOWS-QUOTING`
- `ev-del-cr-windows-quoting-3`
- `1zc7n`

## Targets

- `tests/test_process_info.py`
- `tests/test_indexer.py`
