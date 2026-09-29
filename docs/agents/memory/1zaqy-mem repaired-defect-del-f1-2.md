# Repaired defect DEL-F1

Owner: Engineering
Status: superseded
Last verified: 2026-09-28

Memory ID: `1zaqy-mem repaired-defect-del-f1-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 222676
Source event: `finding:1z8ou:DEL-F1`
Validation: rewrite
Validated by: agent
Action delta: When a source-text census recognises a regex construct (an anchor, a group), make it reject escaped and character-class look-alikes, and give each guard its own planted control that fails when only that guard is removed.
Validation rationale: DEL-F1 (ev-del-f1-3): the label-reader census matched a literal caret, so an escaped \^ or a [^ class counted as an anchor; the first class fixture was flagged regardless of the guard, which only a per-guard mutant revealed. Generated candidate carried no action.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zb8n-mem source-text-censuses-must-reject-escaped-and-class-look-alik`

## Summary

Real defect fixed in wave 1z8ou: Resolved.

## Evidence

- `DEL-F1`
- `ev-del-f1-3`
- `1z8ou`

## Targets

- `tests/test_label_reader_census.py`
