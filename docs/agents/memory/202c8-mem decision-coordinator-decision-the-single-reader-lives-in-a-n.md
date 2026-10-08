# Decision: Coordinator decision: the single reader lives in a new stdl…

Owner: Engineering
Status: superseded
Last verified: 2026-10-07

Memory ID: `202c8-mem decision-coordinator-decision-the-single-reader-lives-in-a-n`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 161410
Source event: `decision-log:2038p-bug setup-leaks-framework-tests-into-docs-index:ecbb2ceeeb0db0f8`
Validation: rewrite
Validated by: agent
Action delta: Never forward --project-include-prefix from setup or any launcher; every index build reads docs/workflow-config.json itself through workflow_include_prefixes.py, and a launcher that forwards an override makes docs eligibility differ between builds, which causes a re-embed and reap loop.
Validation rationale: Wave 204jj found wf setup forwarding merged docs and code prefixes, which widened docs eligibility to framework test files; incremental builds then reaped those rows and the next setup re-embedded about 250 files. The fix removes the forward and puts one stdlib-only reader in workflow_include_prefixes.py (so setup gains no indexer import side effects); verified live on this repo with zero test rows and zero drift across setup, incremental, setup.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `204jz-mem index-launchers-must-not-forward-include-prefixes-one-config`

## Summary

Decision (wave 204jj): Coordinator decision: the single reader lives in a new stdlib-only module `workflow_include_prefixes.py`, not in `indexer`.. Rationale: A module-level `import indexer` would run `activate_tool_venv()` and `register_loaded_source()` at setup import time, before `ensure_deps`; a stdlib module keeps the reader free of those side effects for both consumers..

## Evidence

- `2038p-bug setup-leaks-framework-tests-into-docs-index`
- `204jj`

## Targets

- `workflow_include_prefixes.py`
