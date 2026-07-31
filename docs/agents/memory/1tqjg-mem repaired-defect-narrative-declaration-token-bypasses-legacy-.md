# Repaired defect narrative-declaration-token-bypasses-legacy-prepare-lint

Owner: Engineering
Status: superseded
Last verified: 2026-07-28

Memory ID: `1tqjg-mem repaired-defect-narrative-declaration-token-bypasses-legacy-`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-28
Updated: 2026-07-28
Source exploration cost: 2613230
Source event: `finding:1tsyx:narrative-declaration-token-bypasses-legacy-prepare-lint`
Validation: rewrite
Validated by: agent
Action delta: Whenever declaration text selects an authority or compatibility branch, call the canonical header parser and require an error-free exact value; test narrative, malformed, absent, and valid-header quadrants.
Validation rationale: The generated candidate correctly identifies a durable authority-parsing defect but misattributes it to docs_lint.py. The bypass was introduced in wave_validators.py and depends on review_evidence.py's canonical parser; the rewrite records that reusable boundary and the executed four-quadrant control.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1trpb-mem parse-authority-declarations-never-infer-them-from-raw-subst`
## Summary

Real defect fixed in wave 1tsyx: The raw-substring authority bypass is closed and legacy output remains byte-stable.

## Evidence

- `narrative-declaration-token-bypasses-legacy-prepare-lint`
- `ev-narrative-declaration-token-bypasses-legacy-prep-3`
- `1tsyx`

## Targets

- `docs_lint.py`
