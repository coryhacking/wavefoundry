# Checklist item readers must change together

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249i9-mem checklist-item-readers-must-change-together`
Kind: `fragile_file`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 214355
Supersedes: `1zm01-mem checklist-item-readers-must-change-together`

## Summary

When changing how change-doc checklist items are parsed, route the rule through .wavefoundry/framework/scripts/change_doc_checklist.py (checklist_items, section_text, fenced_line_flags) and update every reader together: the close gate in lifecycle_gate_support.py, wf_mark_ac/wf_mark_task via _mark_change_item_response in wf_server/server_impl.py, gardener_metadata.normalize_checkbox_tracking and the dashboard_lib.py parsers. Why: wave 1zls7 readiness found changing only the close gate would let an item block close that the mark tools could not mark.

## Evidence

- `1zltr-bug close-gate-checklist-open-items`
- `1zls7`

## Targets

- `.wavefoundry/framework/scripts/change_doc_checklist.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/gardener_metadata.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
