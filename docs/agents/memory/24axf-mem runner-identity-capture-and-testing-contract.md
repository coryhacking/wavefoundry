# Runner identity capture and testing contract

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24axf-mem runner-identity-capture-and-testing-contract`
Kind: `decision`
Confidence: 0.75
Created: 2026-11-25
Updated: 2026-11-26
Supersedes: `1uamr-mem runner-identity-capture-and-testing-contract`
Checked at: 2026-11-26T06:32:44Z
Check note: The runner identity and test-loader path still differ. Verify the actual running module before testing reload behavior. Reviewed .wavefoundry/framework/scripts/server.py:324.
Check flags: none

## Summary

When changing runner identity hashing or testing launch-captured runner state, keep the hash in one implementation, compute_runner_identity in .wavefoundry/framework/scripts/wf_server/server_impl.py. server.py captures the runner version and file set once at launch through a getattr fallback that tolerates an older impl, and wf_server_info recomputes the same paths at query time, so a second hash would let the two drift. Test launch-captured state by calling compute_runner_identity over temporary copies of the runner files and mutating them (RunnerIdentityTests in tests/test_server_tools.py); reserve fresh-process probes for tool-registration changes.

## Evidence

- `RunnerIdentityTests.test_identity_changes_when_either_runner_file_changes`
- `RunnerIdentityTests.test_stale_runner_detected_after_disk_change`
- `RunnerIdentityTests.test_runner_file_set_covers_server_and_venv_bootstrap`

## Targets

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
