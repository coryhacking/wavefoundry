# Decision: Readiness amendments: Requirement 1 now defines `DONE_CHANG…

Owner: Engineering
Status: superseded
Last verified: 2026-10-03

Memory ID: `1zms2-mem decision-readiness-amendments-requirement-1-now-defines-done`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 214355
Source event: `decision-log:1zlu0-bug close-wave-treats-unfinished-statuses-as-open:034b9c932b5e1fed`
Validation: rewrite
Validated by: agent
Action delta: When reading change status for a gate, read every attributed status line and fail closed; take the done set from wave_lint_lib.constants, never a local list.
Validation rationale: 1zls7 delivery review found the first close-status implementation read the lint parser's last status line, so a later duplicate, fenced or indented done line hid an open status; the fix reads the union. The single done-set source and the union reading are the durable rules.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zm7x-mem close-reads-every-status-line-done-set-is-single-sourced`

## Summary

Decision (wave 1zls7): Readiness amendments: Requirement 1 now defines `DONE_CHANGE_STATUSES = frozenset(TERMINAL_CHANGE_STATUSES) \| {"implemented"}` and one done predicate beside the lint constants, read by close and the lint dependency rule; close iterates `wave_validators._parse_work_records` (ids, statuses, anchor types, whitespace-stripped, fixing indented records, red-team R4) instead of `_CHANGE_STATUS_PATTERN`; AC-3 patches the done set and pins the `implemented`-only difference; AC-5 also forbids `_CHANGE_STATUS_PATTERN`; Requirement 7 brings the two lifecycle golden fixtures, the declared-delta entry and `test_docs_lint.py` into scope with the new dependency message; `wave_validators.py` added to review targets; pending-decision residue removed; dashboard `DONE_STATUSES` and `wfds.js` named in the follow-up; red-team R8 (wave.md versus change-doc status drift) recorded as a follow-up. Rationale: Readiness review: Requirements 1 and 6 and AC-3 and AC-5 contradicted each other, and pinned text outside the named files would have failed.

## Evidence

- `1zlu0-bug close-wave-treats-unfinished-statuses-as-open`
- `1zls7`

## Targets

- `test_docs_lint.py`
- `wave_validators.py`
- `wfds.js`
