# Evidence scripts must not default-write committed artifact names

Owner: Engineering
Status: active
Last verified: 2026-08-27

Memory ID: `1wiaj-mem evidence-scripts-must-not-default-write-committed-artifact-n`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-27
Updated: 2026-08-27
Source exploration cost: 390416
Source event: `finding:1wfsl:QA-DEL-1`
Validation: promote
Validated by: agent
Action delta: Evidence-generating scripts must default their output to stdout or a non-committed filename; committed evidence artifacts are written only via an explicit --out, so re-runs (including reviewers' own reproductions) can never clobber before-evidence.
Validation rationale: The generated summary restated the discharge line rather than the reusable lesson. The verified chain: the census script wrote a fixed sibling filename, so a reproduction run silently overwrote the committed walker-11 before-artifact with post-change output, making the cited evidence contradict its citation; the qa delivery lane detected it by diffing against an independent git-HEAD reproduction, and the repair (stdout-only default plus explicit --out, artifact regenerated from the HEAD module with a provenance field) was independently reverified with SHA-256 non-mutation proof. Current target verified: census_exclusions.py now carries the --out contract and the regenerated artifact carries walker_version 11 with provenance.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1wfsl (QA-DEL-1): the executed-census evidence script wrote its results to a fixed committed filename by default, so a later reproduction run (the qa delivery lane's own) silently clobbered the walker-11 BEFORE artifact with post-change output — the cited evidence then contradicted its Progress Log citation, in a wave whose watchpoint was falsified censuses. Detection required diffing against an independent git-HEAD-module reproduction. Repair: default output to stdout only (file writes require explicit --out) and regenerate the before-artifact by executing against the extracted HEAD module with a provenance field disclosing the clobber and the carried repo-stats. Rule: before/after evidence pairs are append-only — any script that can regenerate one side must be incapable of overwriting committed evidence without an explicit, deliberate flag.

## Evidence

- `QA-DEL-1`
- `ev-qa-del-1-3`
- `1wfsl`
- `evidence/census_results.json provenance field`

## Targets

- `docs/waves/1wfsl structured-docs-retrieval/evidence/census_exclusions.py`
