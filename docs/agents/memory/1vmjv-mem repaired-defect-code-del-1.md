# Repaired defect CODE-DEL-1

Owner: Engineering
Status: superseded
Last verified: 2026-08-17

Memory ID: `1vmjv-mem repaired-defect-code-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `finding:1viyu:CODE-DEL-1`
Validation: rewrite
Validated by: agent
Action delta: Any test that claims a "Phase-1-complete" or "fresh install" tree must build it through the real producers (setup Step 0 provisioners + render_agent_surfaces) and judge it with the real validator; any new renderer-materialized docs/** baseline must carry Owner/Status/Last verified with a stamped date, and every baseline family must go through the same {{generated_at}} stamp.
Validation rationale: Two independent delivery lanes built faithful trees and found 21 blocking metadata errors from renderer-materialized files (five lifecycle prompt baselines and the two pointer-form carriers), which the delivered AC-1 test could not see because its fixture was a bare framework dir with an empty docs/. Repair verified on the current tree: templates carry the block with {{generated_at}}, reconcile_lifecycle_prompt_baselines stamps it (mirroring reconcile_scaffold_baselines), _initial_review_carrier_text emits metadata, and _build_phase_one_complete_tree in WaveInstallAuditTests runs the real validator; three metadata mutants kill it. The draft's target (render_platform_surfaces.py) is the entry, not the seam; the seam is render_agent_surfaces baselines plus the templates and the fixture. Root cause predates the wave (one baseline family stamped, the other not), which is the reusable warning.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1vn0v-mem renderer-materialized-docs-baselines-must-lint-on-their-own-`
## Summary

Real defect fixed in wave 1viyu: REPAIRED: required AC-1 proven by a faithful real-validator test that is mutation-sensitive, and confirmed through the production render entry.

## Evidence

- `CODE-DEL-1`
- `ev-code-del-1-4`
- `1viyu`

## Targets

- `render_platform_surfaces.py`
