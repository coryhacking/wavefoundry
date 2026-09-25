# Decision: Warn about any present retired flat file; do not refuse and…

Owner: Engineering
Status: superseded
Last verified: 2026-09-25

Memory ID: `1ywy1-mem decision-warn-about-any-present-retired-flat-file-do-not-ref`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-25
Updated: 2026-09-25
Source exploration cost: 200863
Source event: `decision-log:1yxwn-ref retire-optional-flat-server-aliases:c71700083e8e765d`
Validation: rewrite
Validated by: agent
Action delta: For a retired framework file an upgrade may leave behind, rely on the MANIFEST-diff prune alone and report leftovers (upgrade post_pruning report, wf_server_info diagnostic, stderr); never add an unproven-ownership deletion path and never refuse startup over it.
Validation rationale: Operator decision recorded in the 1yxwn-ref Decision Log and ADR 1yx4m amendment; implemented as server_impl.retired_flat_leftovers (wf_server_info diagnostic retired_flat_module_leftover, stderr in register_mcp_surface) and upgrade_extensions.post_pruning (report only). The generated target prune_framework.py is the cited hazard, not where the decision lives, so targets are rewritten. Verified by the old-runner matrix (proven prune deletes 10, unproven keeps and warns).
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1yz02-mem decision-leftover-retired-framework-files-are-warned-about-n`

## Summary

Decision (wave 1yxyw): Warn about any present retired flat file; do not refuse and do not delete it outside the MANIFEST prune (operator decision, superseding the refusal chosen at readiness). Rationale: The ten files are framework-owned and unedited, so the ordinary MANIFEST-diff prune is the right deletion authority. Every install that holds them (first shipped in v1.26.0) has a MANIFEST, so a leftover means only a missed or unproven prune; a warning to delete it is enough. Deleting without ownership evidence repeats the removed legacy-fallback hazard (`prune_framework.py`).

## Evidence

- `1yxwn-ref retire-optional-flat-server-aliases`
- `1yxyw`

## Targets

- `prune_framework.py`
