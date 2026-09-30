# In-place module reloads keep exception class identity

Owner: Engineering
Status: active
Last verified: 2026-09-30

Memory ID: `1zcis-mem in-place-module-reloads-keep-exception-class-identity`
Kind: `decision`
Confidence: 0.8
Created: 2026-09-30
Updated: 2026-09-30
Source exploration cost: 479414
Source event: `decision-log:1zesi-bug memory-hook-stale-modules:33dd1328d300b38c`
Validation: promote
Validated by: agent
Action delta: Any in-place importlib.reload of a framework module must keep its exception classes' identity (rebind them to the pre-reload objects), or by-name importers stop catching what the reloaded code raises.
Validation rationale: Drafted from a Progress Log row that was misfiled in the Decision Log (since moved). The lesson is real and verified: upgrade_extensions._reload_in_place rebinds surviving exception classes; test_names_imported_from_the_old_record_paths_still_catch_what_it_raises fails without it. The draft's wording was a log entry, not an actionable record.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

importlib.reload updates a module's namespace in place, so a function another module imported by name (wave_lint_lib/helpers.py: from record_paths import RecordLayoutInvalid, load_record_roots) looks up the NEW exception class when it raises, while the holder's except still names the OLD one and misses it. The plausible counter-argument that the old function and old class stay together is wrong. upgrade_extensions._reload_in_place snapshots the module's own exception classes and rebinds each that survives the reload to its original object; safe only while those class definitions are unchanged across versions (RecordLayoutInvalid and AmbiguousWaveId are AST-identical in v1.27.0 and HEAD). Non-exception classes matter only if something does isinstance on them.

## Evidence

- `1zesi-bug memory-hook-stale-modules`
- `1zeyo`
- `DEL-1ZEYO-R2`

## Targets

- `upgrade_extensions.py`
- `record_paths.py`
- `wave_lint_lib/helpers.py`
