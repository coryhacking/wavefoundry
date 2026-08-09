# Upgrade-time code can only depend on what the pack ships

Owner: Engineering
Status: active
Last verified: 2026-08-07

Memory ID: `1umf9-mem upgrade-time-code-can-only-depend-on-what-the-pack-ships`
Kind: `decision`
Confidence: 0.9
Created: 2026-08-07
Updated: 2026-08-07
Source exploration cost: 51887
Source event: `decision-log:1ulr2-bug upgrade-preflight-blocks-on-state-it-owns:78de10052171b26d`
Validation: promote
Validated by: agent
Action delta: Before designing a fix that runs during upgrade in a target repo, check whether the module it would depend on actually ships there.
Validation rationale: The drafted candidate records one wave's specific rejection and would not change behavior on a future design. The durable lesson is the check that produced it: an upgrade-time component runs inside the target repository, so it can only import what the pack ships, and `build_pack.py` does not ship. Readiness caught this only because the plan's hardest requirement was tested rather than read. Verified against the current tree: `build_pack.py` is absent from the 1.15.4 zip while `review_policy.py`, `review_policy_reconcile.py`, and `upgrade_wavefoundry.py` are present in both the feature pack and the nested bridge.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

A component that executes during `wf upgrade` runs inside the TARGET repository, so it may only import modules the distribution zip actually contains. Verify membership against the built pack before designing any dependency: `build_pack.py` is a build tool and is NOT shipped, so no runtime validator may derive behavior from it, and a design that does inverts the layering as well as being impossible. The same listing answers the related question of WHICH code executes on a given upgrade path, which decides whether a fix is class-a or class-b: the nested bridge carries `review_policy.py`, `review_policy_reconcile.py`, and `upgrade_wavefoundry.py`, and the bridge installs its framework before running the feature hop, so a protocol-1 crossing executes NEW code and the fix applies on that same run. An ordinary protocol-2 upgrade runs its review-policy preflight before any extraction, using the framework already installed, so there the fix takes effect only from the next upgrade. Do not assert either classification from the usual path; read the argv and the zip.

## Evidence

- `1ulr2-bug upgrade-preflight-blocks-on-state-it-owns`
- `1uoq0`

## Targets

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/review_policy_reconcile.py`
- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
