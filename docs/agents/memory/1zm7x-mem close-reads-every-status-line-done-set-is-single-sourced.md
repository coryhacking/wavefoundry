# Close reads every status line; done set is single-sourced

Owner: Engineering
Status: active
Last verified: 2026-10-03

Memory ID: `1zm7x-mem close-reads-every-status-line-done-set-is-single-sourced`
Kind: `decision`
Confidence: 0.8
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 214355
Source event: `decision-log:1zlu0-bug close-wave-treats-unfinished-statuses-as-open:034b9c932b5e1fed`
Validation: promote
Validated by: agent
Action delta: When reading change status for a gate, read every attributed status line and fail closed; take the done set from wave_lint_lib.constants, never a local list.
Validation rationale: 1zls7 delivery review found the first close-status implementation read the lint parser's last status line, so a later duplicate, fenced or indented done line hid an open status; the fix reads the union. The single done-set source and the union reading are the durable rules.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

DONE_CHANGE_STATUSES (terminal statuses plus implemented) and is_done in wave_lint_lib/constants.py are the only done set; close and the lint dependency rule read it. A gate reading change status must consider every status line attributed to a record (WorkRecord.status_values), treat an unreadable or missing status as open, and catch status lines the lint parser does not attribute (Item Status inside a change record, column-0 ids outside the lint shape). Last-line-wins reading was a fail-open regression.

## Evidence

- `1zlu0-bug close-wave-treats-unfinished-statuses-as-open`
- `DEL-1ZLS7-CLOSE-STATUS-LAST-WINS`
- `1zls7`

## Targets

- `wave_lint_lib/constants.py`
- `wave_lint_lib/wave_validators.py`
- `wf_server/server_impl.py`
