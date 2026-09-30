# Old-runner upgrade hooks reload their whole import closure in place

Owner: Engineering
Status: active
Last verified: 2026-09-30

Memory ID: `1zf7r-mem old-runner-upgrade-hooks-reload-their-whole-import-closure-i`
Kind: `decision`
Confidence: 0.8
Created: 2026-09-30
Updated: 2026-09-30
Source exploration cost: 358042
Source event: `decision-log:1zesi-bug memory-hook-stale-modules:43fd40f0317f7cdc`
Validation: promote
Validated by: agent
Action delta: When an upgrade hook crashes on an attribute the old runner's cached module lacks, reload the hook's whole framework import closure in place (leaf-first) in upgrade_extensions.py instead of adding getattr tolerance in the consumer.
Validation rationale: Verified against the 1zesi Decision Log and current upgrade_extensions.py: _MEMORY_BOOTSTRAP_MODULES is reloaded leaf-first by _installed_memory_backfill, stateful modules are listed in _MEMORY_BOOTSTRAP_EXCLUDED with reasons, and an AST test derives the closure from framework_files. The draft's wording omitted the mechanism and the in-place (not subprocess) constraint the readiness review forced.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

A 1.27 upgrade runner executes the NEW pack's upgrade_extensions.py but keeps its own stale sys.modules, so a hook importing a new module against an old cached dependency crashes (RecordRoots.archive in post_docs_gate). Fix in upgrade_extensions.py: reload the hook's framework import closure leaf-first IN PLACE (the runner re-imports the same modules after the hook, so a subprocess does not help), exclude stateful modules (index_state_store, lifecycle_id) with a recorded reason that their used API is unchanged, and keep an AST test that every framework import in the closure is reloaded or excluded. Do not patch the consumer with getattr tolerance: it fixes one field and misses the class.

## Evidence

- `1zesi-bug memory-hook-stale-modules`
- `1zeyo`

## Targets

- `upgrade_extensions.py`
- `memory_backfill.py`
- `record_paths.py`
