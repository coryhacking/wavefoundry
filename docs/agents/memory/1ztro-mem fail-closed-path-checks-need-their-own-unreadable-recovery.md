# Fail-closed path checks need their own unreadable recovery

Owner: Engineering
Status: active
Last verified: 2026-10-04

Memory ID: `1ztro-mem fail-closed-path-checks-need-their-own-unreadable-recovery`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 282431
Source event: `finding:1zrak:DEL-R1`
Validation: promote
Validated by: agent
Action delta: When a 3.14 fail-open fix makes an uninspectable path read as present, give it its own diagnostic and recovery instead of reusing the 'present' branch's message.
Validation rationale: DEL-R1: after converting the upgrade-lock check to the errno rule, an unreadable or looping upgrade-in-progress.json fell into the 'present' branch and setup told the operator to finish an upgrade that may not exist. Fixed with upgrade_lock_unreadable_cause/_message; the generic summary carried no lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Converting a pathlib predicate to the errno rule (absent only on ENOENT/ENOTDIR) makes an uninspectable path refuse. Reusing the 'present' branch's message then misleads: an unreadable upgrade-in-progress.json told setup to finish an upgrade that may not exist. Give the unreadable case a distinct path-free cause and recovery (upgrade_lib.upgrade_lock_unreadable_cause/_message).

## Evidence

- `DEL-R1`
- `ev-del-r1-3`
- `1zrak`

## Targets

- `.wavefoundry/framework/scripts/upgrade_lib.py`
- `.wavefoundry/framework/scripts/setup_reconciliation.py`
