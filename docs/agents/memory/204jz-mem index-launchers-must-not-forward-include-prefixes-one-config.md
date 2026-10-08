# Index launchers must not forward include prefixes; one config reader decides eligibility

Owner: Engineering
Status: active
Last verified: 2026-10-07

Memory ID: `204jz-mem index-launchers-must-not-forward-include-prefixes-one-config`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 161410
Source event: `decision-log:2038p-bug setup-leaks-framework-tests-into-docs-index:ecbb2ceeeb0db0f8`
Validation: promote
Validated by: agent
Action delta: Never forward --project-include-prefix from setup or any launcher; every index build reads docs/workflow-config.json itself through workflow_include_prefixes.py, and a launcher that forwards an override makes docs eligibility differ between builds, which causes a re-embed and reap loop.
Validation rationale: Wave 204jj found wf setup forwarding merged docs and code prefixes, which widened docs eligibility to framework test files; incremental builds then reaped those rows and the next setup re-embedded about 250 files. The fix removes the forward and puts one stdlib-only reader in workflow_include_prefixes.py (so setup gains no indexer import side effects); verified live on this repo with zero test rows and zero drift across setup, incremental, setup.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Docs and code index eligibility must be identical on every launch path (setup, hooks, quiet-period monitor, rebuild). Wave 204jj removed setup's --project-include-prefix forward, which had made framework test files docs-eligible only under setup and caused a setup re-embed / incremental reap loop. All builds now read docs/workflow-config.json through the stdlib-only workflow_include_prefixes.py; indexer._workflow_project_include_prefixes delegates to it. The --project-include-prefix flag remains for manual and test use only and overrides every layer.

## Evidence

- `204jj`
- `2038p-bug setup-leaks-framework-tests-into-docs-index`
- `SetupLaunchedCorpusParityTests`

## Targets

- `.wavefoundry/framework/scripts/workflow_include_prefixes.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
