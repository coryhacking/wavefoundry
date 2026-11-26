# Offline vendored-script checks live in the shipped vendored_integrity module

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bue-mem offline-vendored-script-checks-live-in-the-shipped-vendored-`
Kind: `decision`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 97308
Supersedes: `2016a-mem decision-coordinator-move-parse-readme-and-offline-problems-`
Checked at: 2026-11-26T06:32:44Z
Check note: Offline vendored integrity runs from packaged sources. Keep parsing and checks in shipped code with its install requirements. Reviewed .wavefoundry/framework/scripts/vendored_integrity.py:5.
Check flags: none

## Summary

When adding or changing an offline check of vendored scripts, put it in the shipped .wavefoundry/framework/scripts/vendored_integrity.py (parse_readme, offline_problems); the network verifier verify_vendored_scripts.py stays source-repo only and imports it. Why: decision of wave 1zyb2; the requester is a distribution, so reporting unavailable everywhere would defeat the finding, and wf_audit uses the shipped module uncached because hashing the vendored files costs milliseconds.

## Evidence

- `1zxnt-maint correctness-and-test-hygiene-round`
- `1zyb2`

## Targets

- `.wavefoundry/framework/scripts/vendored_integrity.py`
- `.wavefoundry/framework/scripts/verify_vendored_scripts.py`
