# Command-line test expectations must be platform-rendered

Owner: Engineering
Status: active
Last verified: 2026-09-29

Memory ID: `1zbe6-mem command-line-test-expectations-must-be-platform-rendered`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 526079
Source event: `finding:1zc7n:DEL-CR-WINDOWS-QUOTING`
Validation: promote
Validated by: agent
Action delta: When a test asserts on a process_info.cmdline rendering, compute the expected substring with subprocess.list2cmdline on nt and a space join elsewhere; never hard-code the POSIX form.
Validation rationale: DEL-CR-WINDOWS-QUOTING: two tests required unquoted '--root /tmp/a b' and would fail on native Windows, where process_info._render uses list2cmdline. The generated candidate's summary restated the disposition only and its targets were not repo-relative.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

process_info.cmdline renders argv with subprocess.list2cmdline on Windows (spaced arguments quoted) and a space join on POSIX. Tests that assert on the rendered line must build the expected substring the same way per platform; a hard-coded POSIX substring passes on macOS/Linux and fails on native Windows, which has no CI here. Keep a spaced argument in the fixture so quoting stays exercised.

## Evidence

- `DEL-CR-WINDOWS-QUOTING`
- `ev-del-cr-windows-quoting-3`
- `1zc7n`

## Targets

- `.wavefoundry/framework/scripts/process_info.py`
- `.wavefoundry/framework/scripts/tests/test_process_info.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
