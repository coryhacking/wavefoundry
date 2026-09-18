# Repaired defect lint-corpus-docs-only

Owner: Engineering
Status: rejected
Last verified: 2026-09-17

Memory ID: `1ydkj-mem repaired-defect-lint-corpus-docs-only`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-17
Updated: 2026-09-17
Source exploration cost: 578663
Source event: `finding:1y0gz:lint-corpus-docs-only`
Validation: reject
Validated by: agent
Action delta: No durable action from this record: its targets are reviewer scratch probes outside the repository; the lesson (corpus walkers union record roots outside docs/) is recorded in docs/architecture/layering-rules.md, the 1y042 change doc, and the pinning tests
Validation rationale: The generated record targets reverify-integrator/probe_c2.py and run_mutants_c2.py, which are session scratchpad artifacts not present in the tree, so it cannot be promoted or rewritten in place. The repair itself lives in wave_lint_lib/helpers.markdown_scan_roots and docs_gardener.markdown_scan_roots with RecordLayoutLintTests and RecordLayoutGardenerTests pinning it; the layering-rules "Shared path resolution" section states the rule.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1y0gz: Repaired; nothing further

## Evidence

- `lint-corpus-docs-only`
- `ev-lint-corpus-docs-only-3`
- `1y0gz`

## Targets

- `reverify-integrator/probe_c2.py`
- `run_mutants_c2.py`
- `docs_lint.py`
- `docs_gardener.py`
