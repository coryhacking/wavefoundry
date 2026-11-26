# Probe-then-unlink of a lock carrier lets two holders coexist

Owner: Engineering
Status: archived
Last verified: 2026-09-29

Memory ID: `1zbln-mem probe-then-unlink-of-a-lock-carrier-lets-two-holders-coexist`
Superseded by: `24bx9-mem never-unlink-a-lock-carrier-after-only-probing-it`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-09-29
Updated: 2026-11-25
Archived: 2026-11-25
Archive reason: Superseded by 24bx9-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1zbln-mem probe-then-unlink-of-a-lock-carrier-lets-two-holders-coexist.md`

## Summary

A lock file that is also the lock identity (dashboard carrier, index build lock) must never be deleted by a process that only probed it: between the probe and the unlink another process can acquire it, and the next process then locks a fresh inode, giving two live holders. Clear stale metadata by acquiring the same lock (same offset, non-blocking), rewriting in place while held, then releasing; held or unknown lock state keeps the file and reports unverified. Test with a real contender and with the unlink restored as a mutant.

## Evidence

- `DEL-DASHBOARD-CARRIER-RACE`
- `ev-del-dashboard-carrier-race-3`
- `ev-del-dashboard-carrier-race-4`
- `1zc7n`
- `DEL-F3`
- `1za2y`

## Targets

- `.wavefoundry/framework/scripts/wf_server/dashboard_handlers.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/tests/test_process_info_callers.py`
