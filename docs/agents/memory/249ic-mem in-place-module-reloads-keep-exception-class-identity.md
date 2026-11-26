# In-place module reloads keep exception class identity

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249ic-mem in-place-module-reloads-keep-exception-class-identity`
Kind: `decision`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 479414
Supersedes: `1zcis-mem in-place-module-reloads-keep-exception-class-identity`
Checked at: 2026-11-26T06:32:42Z
Check note: The upgrade reload helper updates a module in place. Exception identity can outlive a reload and must be tested accordingly. Reviewed .wavefoundry/framework/scripts/upgrade_extensions.py:1796.
Check flags: none

## Summary

When upgrade code reloads a framework module in place (upgrade_extensions._reload_in_place) or changes an exception class that such a module defines, keep the rebinding of surviving exception classes to their original objects. Change those class definitions only together with the rebinding. importlib.reload updates the namespace in place, so a function another module imported by name (wave_lint_lib/helpers.py: from record_paths import RecordLayoutInvalid, load_record_roots) raises the new class while the importer's except clause still names the old one and misses it. The counter-argument that the old function and the old class stay together is wrong. The rebinding is safe only while those class definitions are unchanged across versions (RecordLayoutInvalid and AmbiguousWaveId match v1.27.0). It runs in a finally so a partial reload does not split the classes. Non-exception classes matter only where something calls isinstance on them (1zesi, DEL-1ZEYO-R2).

## Evidence

- `1zesi-bug memory-hook-stale-modules`
- `1zeyo`
- `DEL-1ZEYO-R2`

## Targets

- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/helpers.py`
