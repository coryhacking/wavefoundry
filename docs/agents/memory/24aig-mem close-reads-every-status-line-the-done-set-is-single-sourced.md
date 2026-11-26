# Close reads every status line; the done set is single-sourced

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24aig-mem close-reads-every-status-line-the-done-set-is-single-sourced`
Kind: `decision`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 214355
Supersedes: `1zm7x-mem close-reads-every-status-line-done-set-is-single-sourced`
Checked at: 2026-11-26T06:32:43Z
Check note: Lifecycle status can appear on multiple lines; compare all owned values using the shared done-set instead of reading only the first. Reviewed .wavefoundry/framework/scripts/wf_server/server_impl.py:14982.
Check flags: none

## Summary

When a gate reads change status, read every status line attributed to the record (WorkRecord.status_values in .wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py), treat a missing or unreadable status as open, and take the done set from DONE_CHANGE_STATUSES / is_done in wave_lint_lib/constants.py, never a local list. Why: 1zls7 delivery review found the first close-status implementation read only the lint parser's last status line, so a later duplicate, fenced or indented done line hid an open status (DEL-1ZLS7-CLOSE-STATUS-LAST-WINS); status lines the lint parser does not attribute (Item Status inside a change record, column-0 ids) must be caught too.

## Evidence

- `1zlu0-bug close-wave-treats-unfinished-statuses-as-open`
- `DEL-1ZLS7-CLOSE-STATUS-LAST-WINS`
- `1zls7`

## Targets

- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
