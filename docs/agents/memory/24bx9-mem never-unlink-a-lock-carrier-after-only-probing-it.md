# Never unlink a lock carrier after only probing it

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bx9-mem never-unlink-a-lock-carrier-after-only-probing-it`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1zbln-mem probe-then-unlink-of-a-lock-carrier-lets-two-holders-coexist`

## Summary

When code clears stale metadata from a file that is also a lock's identity (the dashboard metadata carrier in dashboard_lib.py, the index-build.lock), do not probe the lock and then delete the file. Between the probe and the unlink another process can take the lock, and the next process then locks a fresh inode, so two live holders exist (DEL-DASHBOARD-CARRIER-RACE, wave 1zc7n). Instead, take the same lock non-blocking at the same offset, rewrite the metadata in place while you hold it, then release it. When the lock is held or its state is unknown, keep the file and report the state as unverified. Test with a real contender process and with the unlink restored as a mutant, as test_a_dashboard_cannot_lock_the_carrier_while_stop_clears_it does.

## Evidence

- `DEL-DASHBOARD-CARRIER-RACE`
- `ev-del-dashboard-carrier-race-3`
- `ev-del-dashboard-carrier-race-4`
- `1zc7n`
- `DEL-F3`
- `1za2y`
- `test_process_info_callers.test_a_dashboard_cannot_lock_the_carrier_while_stop_clears_it`

## Targets

- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/wf_server/dashboard_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_process_info_callers.py`
