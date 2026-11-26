# Old-runner upgrade hooks reload their whole import closure in place

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24c7b-mem old-runner-upgrade-hooks-reload-their-whole-import-closure-i`
Kind: `decision`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 358042
Supersedes: `1zf7r-mem old-runner-upgrade-hooks-reload-their-whole-import-closure-i`
Checked at: 2026-11-26T06:32:45Z
Check note: The old runner can retain imported dependencies. Reloading just the top-level hook leaves leaf modules at the old version. Reviewed .wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py:1119.
Check flags: none

## Summary

When an upgrade hook crashes on an attribute the old runner's cached module lacks, reload the hook's framework import closure leaf-first in place in .wavefoundry/framework/scripts/upgrade_extensions.py (_MEMORY_BOOTSTRAP_MODULES, with stateful modules in _MEMORY_BOOTSTRAP_EXCLUDED and a reason) instead of adding getattr tolerance in the consumer. Why: a 1.27 runner executes the new pack's upgrade_extensions.py with its own stale sys.modules, so RecordRoots.archive crashed post_docs_gate; a subprocess does not help because the runner re-imports the same modules after the hook, and getattr tolerance fixes one field and misses the class. tests/test_upgrade_wavefoundry.py test_every_framework_import_of_the_bootstrap_modules_is_reloaded_or_excluded keeps the closure complete.

## Evidence

- `1zesi-bug memory-hook-stale-modules`
- `1zeyo`
- `test_upgrade_wavefoundry.test_every_framework_import_of_the_bootstrap_modules_is_reloaded_or_excluded`

## Targets

- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/memory_backfill.py`
- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
