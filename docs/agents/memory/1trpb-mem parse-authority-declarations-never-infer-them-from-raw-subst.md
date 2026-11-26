# Parse authority declarations; never infer them from raw substrings

Owner: Engineering
Status: active
Last verified: 2026-11-26

Memory ID: `1trpb-mem parse-authority-declarations-never-infer-them-from-raw-subst`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-07-28
Updated: 2026-11-26
Source exploration cost: 2613230
Source event: `finding:1tsyx:narrative-declaration-token-bypasses-legacy-prepare-lint`
Validation: promote
Validated by: agent
Action delta: Whenever declaration text selects an authority or compatibility branch, call the canonical header parser and require an error-free exact value; test narrative, malformed, absent, and valid-header quadrants.
Validation rationale: The generated candidate correctly identifies a durable authority-parsing defect but misattributes it to docs_lint.py. The bypass was introduced in wave_validators.py and depends on review_evidence.py's canonical parser; the rewrite records that reusable boundary and the executed four-quadrant control.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Checked at: 2026-11-26T06:32:39Z
Check note: The lifecycle gate distinguishes declared review authority from incidental text. Keep the parser boundary during future changes. Reviewed .wavefoundry/framework/scripts/review_evidence.py:3838.
Check flags: target_churn

## Summary

Wave 1tsyx introduced a legacy-gate bypass by checking whether `review-evidence-source: events.jsonl` appeared anywhere in wave.md. A narrative mention therefore selected typed behavior without a declaration. The repair routes the decision through parse_review_evidence_source and accepts only the exact value with no parser errors; absent, narrative, malformed, and valid-header public-path fixtures pin both directions.

## Evidence

- `narrative-declaration-token-bypasses-legacy-prepare-lint`
- `ev-narrative-declaration-token-bypasses-legacy-prep-3`
- `1tsyx`

## Targets

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
