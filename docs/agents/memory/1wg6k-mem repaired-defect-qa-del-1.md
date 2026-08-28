# Repaired defect QA-DEL-1

Owner: Engineering
Status: superseded
Last verified: 2026-08-27

Memory ID: `1wg6k-mem repaired-defect-qa-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-27
Updated: 2026-08-27
Source exploration cost: 390416
Source event: `finding:1wfsl:QA-DEL-1`
Validation: rewrite
Validated by: agent
Action delta: Evidence-generating scripts must default their output to stdout or a non-committed filename; committed evidence artifacts are written only via an explicit --out, so re-runs (including reviewers' own reproductions) can never clobber before-evidence.
Validation rationale: The generated summary restated the discharge line rather than the reusable lesson. The verified chain: the census script wrote a fixed sibling filename, so a reproduction run silently overwrote the committed walker-11 before-artifact with post-change output, making the cited evidence contradict its citation; the qa delivery lane detected it by diffing against an independent git-HEAD reproduction, and the repair (stdout-only default plus explicit --out, artifact regenerated from the HEAD module with a provenance field) was independently reverified with SHA-256 non-mutation proof. Current target verified: census_exclusions.py now carries the --out contract and the regenerated artifact carries walker_version 11 with provenance.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1wiaj-mem evidence-scripts-must-not-default-write-committed-artifact-n`
## Summary

Real defect fixed in wave 1wfsl: Repair verified by independent execution; the finding's do_now disposition is discharged.

## Evidence

- `QA-DEL-1`
- `ev-qa-del-1-3`
- `1wfsl`

## Targets

- `census_exclusions.py`
- `evidence/census_exclusions.py`
