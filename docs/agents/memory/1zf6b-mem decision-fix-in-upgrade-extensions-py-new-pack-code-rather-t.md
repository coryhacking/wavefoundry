# Decision: Fix in `upgrade_extensions.py` (new-pack code) rather than…

Owner: Engineering
Status: superseded
Last verified: 2026-09-30

Memory ID: `1zf6b-mem decision-fix-in-upgrade-extensions-py-new-pack-code-rather-t`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-30
Updated: 2026-09-30
Source exploration cost: 358042
Source event: `decision-log:1zesi-bug memory-hook-stale-modules:43fd40f0317f7cdc`
Validation: rewrite
Validated by: agent
Action delta: When an upgrade hook crashes on an attribute the old runner's cached module lacks, reload the hook's whole framework import closure in place (leaf-first) in upgrade_extensions.py instead of adding getattr tolerance in the consumer.
Validation rationale: Verified against the 1zesi Decision Log and current upgrade_extensions.py: _MEMORY_BOOTSTRAP_MODULES is reloaded leaf-first by _installed_memory_backfill, stateful modules are listed in _MEMORY_BOOTSTRAP_EXCLUDED with reasons, and an AST test derives the closure from framework_files. The draft's wording omitted the mechanism and the in-place (not subprocess) constraint the readiness review forced.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zf7r-mem old-runner-upgrade-hooks-reload-their-whole-import-closure-i`

## Summary

Decision (wave 1zeyo): Fix in `upgrade_extensions.py` (new-pack code) rather than tolerate a missing `archive` attribute in `memory_backfill`. Rationale: Removes the whole class (any new field or function in a dependency), and runs on the installing upgrade.

## Evidence

- `1zesi-bug memory-hook-stale-modules`
- `1zeyo`

## Targets

- `upgrade_extensions.py`
