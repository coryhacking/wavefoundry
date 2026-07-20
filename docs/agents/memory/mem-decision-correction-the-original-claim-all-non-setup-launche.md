# Decision: **Correction:** the original claim "all non-setup launchers…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-correction-the-original-claim-all-non-setup-launche`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p92t-bug ca-bundle-non-setup-launchers:d7876e49a647e4de`
Validation: reject
Validated by: agent
Action delta: None; use the consolidated model-download path census memory rather than preserving an intermediate correction.
Validation rationale: This correction was itself incomplete because constructor calls through aliases were outside its literal search hypothesis.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p939): **Correction:** the original claim "all non-setup launchers funnel through `accel_embedder`" was false. Expand the fix to also cover `server_impl.py::_ensure_model_cached()`'s embedding branch — an independent raw `TextEmbedding(...)` call site discovered via pre-implementation MCP exploration (`code_keyword` for `TextEmbedding(`), before any code edit.. Rationale: The earlier scope was based on tracing only `accel_embedder`'s own call graph; it never checked for sibling raw download call sites elsewhere in the codebase. `_ensure_model_cached`'s failure shape (online HF metadata round-trip) matches the field report's traceback more closely than the `accel_embedder` paths, making it plausibly the literal repro site..

## Evidence

- `1p92t-bug ca-bundle-non-setup-launchers`
- `1p939`

## Targets

- `server_impl.py`
