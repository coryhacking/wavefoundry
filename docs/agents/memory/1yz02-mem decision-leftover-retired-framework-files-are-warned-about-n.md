# Decision: leftover retired framework files are warned about, never deleted outside the MANIFEST prune

Owner: Engineering
Status: active
Last verified: 2026-09-25

Memory ID: `1yz02-mem decision-leftover-retired-framework-files-are-warned-about-n`
Kind: `decision`
Confidence: 0.9
Created: 2026-09-25
Updated: 2026-09-25
Source exploration cost: 200863
Source event: `decision-log:1yxwn-ref retire-optional-flat-server-aliases:c71700083e8e765d`
Validation: promote
Validated by: agent
Action delta: For a retired framework file an upgrade may leave behind, rely on the MANIFEST-diff prune alone and report leftovers (upgrade post_pruning report, wf_server_info diagnostic, stderr); never add an unproven-ownership deletion path and never refuse startup over it.
Validation rationale: Operator decision recorded in the 1yxwn-ref Decision Log and ADR 1yx4m amendment; implemented as server_impl.retired_flat_leftovers (wf_server_info diagnostic retired_flat_module_leftover, stderr in register_mcp_surface) and upgrade_extensions.post_pruning (report only). The generated target prune_framework.py is the cited hazard, not where the decision lives, so targets are rewritten. Verified by the old-runner matrix (proven prune deletes 10, unproven keeps and warns).
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Decision (wave 1yxyw, operator): the ten retired flat server aliases are deleted only by the upgrade's MANIFEST-diff prune, the deletion authority for framework-owned files. A file that remains means the prune did not run or was unproven (no saved old MANIFEST); it is reported by upgrade_extensions.post_pruning (report only, never raises, never deletes), by the wf_server_info diagnostic retired_flat_module_leftover and on stderr, and the server still starts. An unproven-ownership deletion path would repeat the legacy-fallback source loss removed from prune_framework.py. A leftover persists until deleted by hand, and meanwhile a stale flat import binds to it.

## Evidence

- `1yxwn-ref retire-optional-flat-server-aliases`
- `1yxyw`
- `1yx4m-adr`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
