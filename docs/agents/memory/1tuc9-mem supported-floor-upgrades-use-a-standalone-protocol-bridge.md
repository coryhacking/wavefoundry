# Supported-floor upgrades use a standalone protocol bridge

Owner: Engineering
Status: active
Last verified: 2026-07-29

Memory ID: `1tuc9-mem supported-floor-upgrades-use-a-standalone-protocol-bridge`
Kind: `decision`
Confidence: 0.9
Created: 2026-07-29
Updated: 2026-07-29
Source exploration cost: 2258580
Source event: `decision-log:1tsbu-enh review-policy-and-delivery-evaluator:f7cedeb51666068e`
Validation: promote
Validated by: agent
Action delta: When changing supported-floor upgrade behavior, preserve the builder-produced bridge pack, standalone bootstrap, and explicit protocol-2 feature selection; do not route the bridge through the legacy runner's post-extract pipeline.
Validation rationale: The decision log and current implementation agree, but the generated candidate truncated its title, duplicated punctuation, and named only a basename. Rewriting preserves the durable architectural choice with precise current targets.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

For supported-floor upgrades, the pack builder emits a framework-only bridge archive, a standalone bootstrap, and explicit protocol-2 selection metadata. The bootstrap installs the bridge without entering the legacy runner's project-writing post-extract pipeline, then hands off to the verified feature archive.

## Evidence

- `docs/waves/1tuoc review-policy-and-delivery-evaluator/1tsbu-enh review-policy-and-delivery-evaluator.md`
- `wave 1tuoc final implementation and independent delivery review`

## Targets

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
- `.wavefoundry/framework/scripts/upgrade_protocol.py`
