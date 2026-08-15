# Cleanup review mislabeled a live degradation path as dead code; verify fallback reachability before recommending removal

Owner: Engineering
Status: active
Last verified: 2026-08-15

Memory ID: `1vcgo-mem cleanup-review-mislabeled-a-live-degradation-path-as-dead-co`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-15
Updated: 2026-08-15

## Summary

The 2026-08-15 codebase cleanup review recommended removing accel_embedder's resident-graph branch (_ensure_fastembed_model_cached + the branch in _resolve_model_files) as dead-for-shipped-models, corroborating a docstring that said the branch was unreachable; the operator approved removal. Plan-time verification falsified it: _resolve_clean_onnx returns None on any FAILED clean fetch (offline cold cache, CA failure) and logs "falling back to the resident model path", so the branch is the live degradation route for registered models, and the offline-fallback tests execute it. Next action: before recommending removal of any fallback/degradation branch, trace every producer of the sentinel that routes into it (here, every None return of the preferred path), not only the registry lookup, and cross-check the module's own tests for fixtures that exercise the branch; a zero-reference or "registered" argument never proves a fallback dead. Fixed by correcting the docstring (wave 1ve3e), keeping the branch.

## Evidence

- `1ve3c-bug accel-resident-branch-docstring-false-unreachability`
- `1ve3e`
- `symbol:_resolve_clean_onnx`
- `symbol:_resolve_model_files`
- `test_resolve_downloads_resident_model_on_cold_cache`
- `test_resolve_none_when_resident_unavailable_after_fetch`

## Targets

- `.wavefoundry/framework/scripts/accel_embedder.py`
- `docs/prompts/codebase-cleanup-review.prompt.md`
