# background-build.pid can hold the wf CLI pid, not a builder

Owner: Engineering
Status: active
Last verified: 2026-09-29

Memory ID: `1zb26-mem background-build-pid-can-hold-the-wf-cli-pid-not-a-builder`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 164401
Source event: `finding:1za2y:DEL-F1`
Validation: promote
Validated by: agent
Action delta: Before narrowing any pid liveness check on background-build.pid, check who stamps the file: wf setup and wf update-indexes stamp the wf_cli.py process pid.
Validation rationale: DEL-F1 was a regression found only in delivery: the new builder-only predicate called a live wf setup completed because setup_index.main runs in-process in wf_cli.py and pre-stamps its own pid. Tests had been rewritten to a setup_index.py-shaped process, fitting the predicate instead of the system.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

setup_index.main pre-stamps background-build.pid with os.getpid(); under wf setup / wf update-indexes that is the wf_cli.py process, often with no --root. A liveness check that accepts only indexer.py/setup_index.py command lines reports a live setup as completed. Status uses _pid_is_live_index_build(unbound_ok=True) with _is_setup_entry_cmdline; lock reclaim keeps its narrower markers. Test with real processes of every stamping shape.

## Evidence

- `DEL-F1`
- `ev-del-f1-3`
- `1za2y`

## Targets

- `.wavefoundry/framework/scripts/wf_server/index_handlers.py`
- `.wavefoundry/framework/scripts/setup_index.py`
