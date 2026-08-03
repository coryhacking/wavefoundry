# server.py fragility is the close-to-restore window in perform_mcp_reload

Owner: Engineering
Status: archived
Last verified: 2026-07-31

Memory ID: `1u498-mem server-py-fragility-is-the-close-to-restore-window-in-perfor`
Superseded by: `1u8q2-mem server-tools-test-playbook`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-07-31
Updated: 2026-08-02
Source exploration cost: 777948
Source event: `repeated-repairs:1u2b0:server.py`
Validation: promote
Validated by: agent
Action delta: Before adding any call between old.close() and the _set_handler restore in perform_mcp_reload, make the callee catch Exception (not one named type) and return a degradation string instead of raising; rerun RunnerIdentityTests, RunnerIdentitySetterCompatibilityTests and WaveMcpReloadTests together.
Validation rationale: The draft says "2 repairs, treat as fragile, run the full suite", which records nothing. Both repairs are the SAME defect at two exception breadths, and the mechanism is a structural window in the file. Verified in the current tree at .wavefoundry/framework/scripts/server.py:73-121: the first repair added _record_runner_identity to wrap the previously unguarded set_server_runner_version(..., runner_files=...) call, whose kwarg raised TypeError against an older impl (fatal at build_server, and at the reload site it escaped after old.close() and before the _set_handler restore, which guards only build_handler); the second repair widened that helper's first try from TypeError-only to except Exception with a TypeError branch for the single-argument retry, because ValueError/OSError/AttributeError still escaped. The docstring at :76-92 now states the never-raises guarantee and names the closed-handler consequence, and both callers are present at :343 and :478. Evidence chain followed in the 1u2b0 ledger (both findings terminal with executed reverification).
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

Archived: 2026-08-02
Archive reason: Superseded by a verified consolidated file playbook after retention review.
Archive path: `docs/agents/memory/archive/1u498-mem server-py-fragility-is-the-close-to-restore-window-in-perfor.md`
## Summary

Both server.py repairs in wave 1u2b0 are one defect caught at two exception breadths, and the reusable fact is the window they live in: perform_mcp_reload closes the old handler BEFORE the new one is installed, and its restore path guards only build_handler. Anything called between those two points that raises leaves a CLOSED handler installed in a live process, which no test of the happy path can see. Repair 1: server.py called set_server_runner_version(version, runner_files=...) unguarded from both build_server and perform_mcp_reload; a torn mid-upgrade tree pairs the new runner with an older impl whose one-argument signature raises TypeError on the keyword, killing the build outright at one site and stranding a closed handler at the other. Repair 2: the guard the first repair added caught only TypeError, so ValueError from a validating impl, OSError from one that persists, or AttributeError from a partially initialised module still escaped and falsified the helper's own "NEVER raises" docstring. Rule for this file: a helper called in that window catches Exception and returns a degradation string; the second call-shape retry is a branch, not the whole guard. The torn-tree pairing (new runner, older impl) is the concrete reachability, via downgrade-then-wf_reload_mcp and via the mid-extraction upgrade window.

## Evidence

- `runner-setter-kwarg-crashes-torn-tree`
- `runner-identity-helper-guards-only-typeerror`
- `1u2b0`
- `.wavefoundry/framework/scripts/server.py:73-121 (_record_runner_identity)`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py:9051 RunnerIdentityTests, :9237 RunnerIdentitySetterCompatibilityTests, :9434 WaveMcpReloadTests`

## Targets

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
