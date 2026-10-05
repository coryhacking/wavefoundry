# Repaired defect DEL-R1

Owner: Engineering
Status: superseded
Last verified: 2026-10-04

Memory ID: `1zthv-mem repaired-defect-del-r1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 282431
Source event: `finding:1zrak:DEL-R1`
Validation: rewrite
Validated by: agent
Action delta: When a 3.14 fail-open fix makes an uninspectable path read as present, give it its own diagnostic and recovery instead of reusing the 'present' branch's message.
Validation rationale: DEL-R1: after converting the upgrade-lock check to the errno rule, an unreadable or looping upgrade-in-progress.json fell into the 'present' branch and setup told the operator to finish an upgrade that may not exist. Fixed with upgrade_lock_unreadable_cause/_message; the generic summary carried no lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1ztro-mem fail-closed-path-checks-need-their-own-unreadable-recovery`

## Summary

Real defect fixed in wave 1zrak: resolved

## Evidence

- `DEL-R1`
- `ev-del-r1-3`
- `1zrak`

## Targets

- `tests/test_pathlib_predicate_guards.py`
