# Fragile: server.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-31

Memory ID: `1u2yv-mem fragile-server-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `repeated-repairs:1u2b0:server.py`
Validation: rewrite
Validated by: agent
Action delta: Before adding any call between old.close() and the _set_handler restore in perform_mcp_reload, make the callee catch Exception (not one named type) and return a degradation string instead of raising; rerun RunnerIdentityTests, RunnerIdentitySetterCompatibilityTests and WaveMcpReloadTests together.
Validation rationale: The draft says "2 repairs, treat as fragile, run the full suite", which records nothing. Both repairs are the SAME defect at two exception breadths, and the mechanism is a structural window in the file. Verified in the current tree at .wavefoundry/framework/scripts/server.py:73-121: the first repair added _record_runner_identity to wrap the previously unguarded set_server_runner_version(..., runner_files=...) call, whose kwarg raised TypeError against an older impl (fatal at build_server, and at the reload site it escaped after old.close() and before the _set_handler restore, which guards only build_handler); the second repair widened that helper's first try from TypeError-only to except Exception with a TypeError branch for the single-argument retry, because ValueError/OSError/AttributeError still escaped. The docstring at :76-92 now states the never-raises guarantee and names the closed-handler consequence, and both callers are present at :343 and :478. Evidence chain followed in the 1u2b0 ledger (both findings terminal with executed reverification).
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1u498-mem server-py-fragility-is-the-close-to-restore-window-in-perfor`
## Summary

server.py required 2 separate repairs during wave 1u2b0; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `runner-setter-kwarg-crashes-torn-tree`
- `runner-identity-helper-guards-only-typeerror`
- `1u2b0`

## Targets

- `server.py`
