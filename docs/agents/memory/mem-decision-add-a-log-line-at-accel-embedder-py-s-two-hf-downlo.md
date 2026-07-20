# Decision: Add a log line at `accel_embedder.py`'s two `_hf_download_c…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-add-a-log-line-at-accel-embedder-py-s-two-hf-downlo`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p92t-bug ca-bundle-non-setup-launchers:fc3a321c00264acc`
Validation: reject
Validated by: agent
Action delta: None; the consolidated model-download memory already requires diagnostics to survive best-effort degradation.
Validation rationale: This is a narrower consequence of the consolidated lesson and would create a duplicate advisory.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p939): Add a log line at `accel_embedder.py`'s two `_hf_download_cached_first()` callers (`_resolve_clean_onnx`, `_resolve_reranker_cpu_files`) rather than changing their "never raises" contract.. Rationale: Both delivery-phase findings (red-team primer first-principles stance; architecture-reviewer seat) confirmed `raise_with_ca_bundle_diagnostic`'s exception was being silently discarded by these two callers' blanket `except Exception: return None`, making AC-4's diagnostic operator-invisible at those call sites. Logging before degrading preserves the existing, separately-correct best-effort/graceful-degradation contract (these functions must never raise) while still surfacing the diagnostic text..

## Evidence

- `1p92t-bug ca-bundle-non-setup-launchers`
- `1p939`

## Targets

- `accel_embedder.py`
