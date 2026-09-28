# Repaired defect cold-site-preload-breaks-nested-ordering

Owner: Engineering
Status: superseded
Last verified: 2026-09-28

Memory ID: `1z907-mem repaired-defect-cold-site-preload-breaks-nested-ordering`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 56010
Source event: `finding:1z8tx:cold-site-preload-breaks-nested-ordering`
Validation: rewrite
Validated by: agent
Action delta: Before fixing a test-order leak, probe _script_cache and sys.modules identity across load_server calls and run a pairwise single-process sweep of all layout-patching files, rather than reasoning from what load_server appears to reset.
Validation rationale: The first repair assumed load_server empties _script_cache; an identity probe showed it does not, and the preload broke nested then cold_sites. The drafted summary ('Resolved.') carried no lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1z6oc-mem load-server-shares-server-impl-test-order-leaks-need-a-pairw`

## Summary

Real defect fixed in wave 1z8tx: Resolved.

## Evidence

- `cold-site-preload-breaks-nested-ordering`
- `ev-cold-site-preload-breaks-nested-ordering-3`
- `1z8tx`

## Targets

- `tests/test_record_layout_cold_sites.py`
