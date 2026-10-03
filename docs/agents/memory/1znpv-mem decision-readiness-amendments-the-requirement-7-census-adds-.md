# Decision: Readiness amendments: the Requirement 7 census adds readers…

Owner: Engineering
Status: superseded
Last verified: 2026-10-03

Memory ID: `1znpv-mem decision-readiness-amendments-the-requirement-7-census-adds-`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 214355
Source event: `decision-log:1zltr-bug close-gate-checklist-open-items:9d11affffb5273ec`
Validation: rewrite
Validated by: agent
Action delta: Before changing how change-doc checklist items are parsed, update every reader together, not just the close gate.
Validation rationale: Wave 1zls7 readiness found that the mark tools, the gardener checkbox normaliser and the dashboard parsers read checklist items separately from the close gate; changing only the gate would let items block close that the mark tools could not mark. The durable rule is the reader census, not the amendment list.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zm01-mem checklist-item-readers-must-change-together`

## Summary

Decision (wave 1zls7): Readiness amendments: the Requirement 7 census adds readers outside `change_doc_checklist` importers (`_mark_change_item_response`, `gardener_metadata.normalize_checkbox_tracking`, the `dashboard_lib.py` checklist parsers); `wf_mark_ac` and `wf_mark_task` read through the shared parser (Requirement 7a, the shared parser chosen over having lint and Prepare report blockquoted items) so every item that blocks close can be marked; near-miss heading detection normalises case, whitespace and up to three spaces of ATX indent (red-team R5, Requirement 4a); a line without the fence's blockquote prefix ends the fence (R7); the fence helper is exposed for `1zltv`; AC-7 added. Red-team R6: multi-character marks such as `[  ]` or `[ x]` stay non-items by intent (plain text, as today), not open items. Rationale: Readiness review: the mark tools could not mark items the close gate now blocks on, and heading and fence edge cases could still hide items.

## Evidence

- `1zltr-bug close-gate-checklist-open-items`
- `1zls7`

## Targets

- `dashboard_lib.py`
