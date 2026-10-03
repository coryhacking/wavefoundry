# Checklist item readers must change together

Owner: Engineering
Status: active
Last verified: 2026-10-03

Memory ID: `1zm01-mem checklist-item-readers-must-change-together`
Kind: `fragile_file`
Confidence: 0.8
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 214355
Source event: `decision-log:1zltr-bug close-gate-checklist-open-items:9d11affffb5273ec`
Validation: promote
Validated by: agent
Action delta: Before changing how change-doc checklist items are parsed, update every reader together, not just the close gate.
Validation rationale: Wave 1zls7 readiness found that the mark tools, the gardener checkbox normaliser and the dashboard parsers read checklist items separately from the close gate; changing only the gate would let items block close that the mark tools could not mark. The durable rule is the reader census, not the amendment list.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Change-doc checklist items are read by the close gate (lifecycle_gate_support), wf_mark_ac/wf_mark_task (_mark_change_item_response), gardener_metadata.normalize_checkbox_tracking and the dashboard_lib checklist parsers. Route new parsing rules through change_doc_checklist (checklist_items, section_text, fenced_line_flags) and census every reader, or an item can block close that the mark tools cannot mark.

## Evidence

- `1zltr-bug close-gate-checklist-open-items`
- `1zls7`

## Targets

- `change_doc_checklist.py`
- `lifecycle_gate_support.py`
- `gardener_metadata.py`
- `dashboard_lib.py`
