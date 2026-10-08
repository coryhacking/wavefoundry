# Decision: Default the preview's new `zip_path` parameter to `None` an…

Owner: Engineering
Status: rejected
Last verified: 2026-10-07

Memory ID: `203vj-mem decision-default-the-preview-s-new-zip-path-parameter-to-non`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 184122
Source event: `decision-log:200v2-maint upgrade-and-render-edge-test-gaps:4eda22bcec64e70b`
Validation: reject
Validated by: agent
Action delta: No durable action: a test-signature compatibility detail recorded in the change doc.
Validation rationale: The default-None parameter only keeps two test callers working; nothing a future agent would act on differently.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Decision (wave 200xy): Default the preview's new `zip_path` parameter to `None` and rewrite the preview half of the `test_history_paths.py` structural test.. Rationale: One-argument callers in two test files keep working, and the structural test then pins the new behavior (incoming-module load) instead of the target-path import it replaces..

## Evidence

- `200v2-maint upgrade-and-render-edge-test-gaps`
- `200xy`

## Targets

- `test_history_paths.py`
