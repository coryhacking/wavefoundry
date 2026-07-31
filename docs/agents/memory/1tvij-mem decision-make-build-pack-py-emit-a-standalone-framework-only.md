# Decision: Make `build_pack.py` emit a standalone framework-only bridg…

Owner: Engineering
Status: superseded
Last verified: 2026-07-29

Memory ID: `1tvij-mem decision-make-build-pack-py-emit-a-standalone-framework-only`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-29
Updated: 2026-07-29
Source exploration cost: 2258580
Source event: `decision-log:1tsbu-enh review-policy-and-delivery-evaluator:f7cedeb51666068e`
Validation: rewrite
Validated by: agent
Action delta: When changing supported-floor upgrade behavior, preserve the builder-produced bridge pack, standalone bootstrap, and explicit protocol-2 feature selection; do not route the bridge through the legacy runner's post-extract pipeline.
Validation rationale: The decision log and current implementation agree, but the generated candidate truncated its title, duplicated punctuation, and named only a basename. Rewriting preserves the durable architectural choice with precise current targets.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1tuc9-mem supported-floor-upgrades-use-a-standalone-protocol-bridge`
## Summary

Decision (wave 1tuoc): Make `build_pack.py` emit a standalone framework-only bridge bootstrap and two separately identified archives; bypass the old runner's post-extract pipeline for bridge installation, then select the feature by explicit protocol-2 pack path.. Rationale: The supported-floor runner has ambient archive selection and continues into project-writing render/prune/policy/garden/index phases, so it cannot safely install a minimal bridge pack..

## Evidence

- `1tsbu-enh review-policy-and-delivery-evaluator`
- `1tuoc`

## Targets

- `build_pack.py`
