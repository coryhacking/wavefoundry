# Decision: Post-approval review (DEL-1ZEYO-R2): the in-place reload br…

Owner: Engineering
Status: superseded
Last verified: 2026-09-30

Memory ID: `1zeow-mem decision-post-approval-review-del-1zeyo-r2-the-in-place-relo`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-30
Updated: 2026-09-30
Source exploration cost: 479414
Source event: `decision-log:1zesi-bug memory-hook-stale-modules:33dd1328d300b38c`
Validation: rewrite
Validated by: agent
Action delta: Any in-place importlib.reload of a framework module must keep its exception classes' identity (rebind them to the pre-reload objects), or by-name importers stop catching what the reloaded code raises.
Validation rationale: Drafted from a Progress Log row that was misfiled in the Decision Log (since moved). The lesson is real and verified: upgrade_extensions._reload_in_place rebinds surviving exception classes; test_names_imported_from_the_old_record_paths_still_catch_what_it_raises fails without it. The draft's wording was a log entry, not an actionable record.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1zcis-mem in-place-module-reloads-keep-exception-class-identity`

## Summary

Decision (wave 1zeyo): Post-approval review (DEL-1ZEYO-R2): the in-place reload broke exception class identity. `importlib.reload` updates the module namespace, so an old function imported by name (`wave_lint_lib/helpers.py`: `from record_paths import RecordLayoutInvalid, load_record_roots`) raised the NEW `RecordLayoutInvalid` that the holder's `except` did not name. The red-team refutation (old function and old class stay together) was wrong. Fix: `_reload_in_place` rebinds every exception class that survives the reload to its original object (the classes in the reload set are byte-identical to v1.27.0); used by `_installed_memory_backfill` and `_refresh_record_layout_modules`. Test: a from-imported `load_record_roots` still raises the from-imported class after `post_docs_gate`. Mutant (no rebind) caught. Rationale: 153 focused tests OK.

## Evidence

- `1zesi-bug memory-hook-stale-modules`
- `1zeyo`

## Targets

- `wave_lint_lib/helpers.py`
