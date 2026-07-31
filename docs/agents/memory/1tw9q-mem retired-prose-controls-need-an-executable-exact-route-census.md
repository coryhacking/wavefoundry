# Retired prose controls need an executable exact-route census

Owner: Engineering
Status: active
Last verified: 2026-07-28

Memory ID: `1tw9q-mem retired-prose-controls-need-an-executable-exact-route-census`
Kind: `failed_attempt`
Confidence: 0.96
Created: 2026-07-28
Updated: 2026-07-28
Source exploration cost: 3418720
Source event: `finding:1tsyx:upgrade-removal-names-wrong-heading-and-validates-clean`
Validation: promote
Validated by: agent
Action delta: When retiring a prose-carried lifecycle control, enumerate each historical semantic route in an executable census and prove every route fails independently, including inside any allowed file.
Validation rationale: The generated candidate captures a durable failure mode, but its basename-only target and finding-title wording are too narrow. The verified lesson is the exact-route census and allowance-evasion proof used by the final repair.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Removing one heading or phrase is not evidence that a prose-carried control is gone. Maintain the exact historical route vocabulary in an executable census, plant each route separately to prove detection, and repeat the probe in allowed files so allowances cannot hide residue. Keep broader downstream reconciliation in one separately owned mechanism instead of duplicating migration vocabularies.

## Evidence

- `finding:1tsyx:upgrade-removal-names-wrong-heading-and-validates-clean`
- `ev-upgrade-removal-names-wrong-heading-and-validate-3`
- `test_events_only_residue_census.py::test_each_new_historical_semantic_route_is_detected_individually`

## Targets

- `.wavefoundry/framework/scripts/tests/test_events_only_residue_census.py`
