# Renderer-materialized docs baselines must lint on their own; fresh-tree fixtures must use the real producers

Owner: Engineering
Status: active
Last verified: 2026-08-17

Memory ID: `1vn0v-mem renderer-materialized-docs-baselines-must-lint-on-their-own-`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `finding:1viyu:CODE-DEL-1`
Validation: promote
Validated by: agent
Action delta: Any test that claims a "Phase-1-complete" or "fresh install" tree must build it through the real producers (setup Step 0 provisioners + render_agent_surfaces) and judge it with the real validator; any new renderer-materialized docs/** baseline must carry Owner/Status/Last verified with a stamped date, and every baseline family must go through the same {{generated_at}} stamp.
Validation rationale: Two independent delivery lanes built faithful trees and found 21 blocking metadata errors from renderer-materialized files (five lifecycle prompt baselines and the two pointer-form carriers), which the delivered AC-1 test could not see because its fixture was a bare framework dir with an empty docs/. Repair verified on the current tree: templates carry the block with {{generated_at}}, reconcile_lifecycle_prompt_baselines stamps it (mirroring reconcile_scaffold_baselines), _initial_review_carrier_text emits metadata, and _build_phase_one_complete_tree in WaveInstallAuditTests runs the real validator; three metadata mutants kill it. The draft's target (render_platform_surfaces.py) is the entry, not the seam; the seam is render_agent_surfaces baselines plus the templates and the fixture. Root cause predates the wave (one baseline family stamped, the other not), which is the reusable warning.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

CODE-DEL-1 (wave 1viyu): five of six shipped install/lifecycle-prompts baselines and the two pointer-form review carriers materialized by render_agent_surfaces carried no Owner/Status/Last verified metadata, so on a genuinely Phase-1-complete tree the real docs-lint emitted 21 blocking errors and wf_audit_install could never return next_step; the delivered AC-1 test used an emptier fixture (bare .wavefoundry/framework/, empty docs/, no Step 0, no render) and stayed green. Repair: metadata blocks with a {{generated_at}} placeholder stamped in reconcile_lifecycle_prompt_baselines exactly as reconcile_scaffold_baselines does, metadata in _initial_review_carrier_text, and the fixture rebuilt as _build_phase_one_complete_tree (copy shipped seeds/ + install/, run both Step 0 provisioners and render_agent_surfaces, real run_validate); mutants dropping a template Owner line, the pointer metadata, or the stamp all fail it. Rules: (1) a fixture that claims a real lifecycle state must be produced by the real code path, not hand-assembled; (2) every docs/** file the renderer materializes must satisfy check_metadata on first lint, with the date stamped on write; (3) baseline families share one stamp/write path (three root-then-module resolvers and two stamp loops still exist, recorded as RTD-2 debt).

## Evidence

- `CODE-DEL-1`
- `ev-code-del-1-3`
- `ev-code-del-1-4`
- `test_server_tools.WaveInstallAuditTests.test_real_validator_phase_one_complete_repo_reaches_phase_two_seed`
- `1vitr-bug audit-install-lint-gate-blocks-fresh-phase-2-entry`

## Targets

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
