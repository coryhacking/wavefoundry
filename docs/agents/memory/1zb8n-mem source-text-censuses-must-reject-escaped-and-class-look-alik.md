# Source-text censuses must reject escaped and class look-alikes, one control per guard

Owner: Engineering
Status: active
Last verified: 2026-09-28

Memory ID: `1zb8n-mem source-text-censuses-must-reject-escaped-and-class-look-alik`
Kind: `fragile_file`
Confidence: 0.8
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 222676
Source event: `finding:1z8ou:DEL-F1`
Validation: promote
Validated by: agent
Action delta: When a source-text census recognises a regex construct (an anchor, a group), make it reject escaped and character-class look-alikes, and give each guard its own planted control that fails when only that guard is removed.
Validation rationale: DEL-F1 (ev-del-f1-3): the label-reader census matched a literal caret, so an escaped \^ or a [^ class counted as an anchor; the first class fixture was flagged regardless of the guard, which only a per-guard mutant revealed. Generated candidate carried no action.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

tests/test_label_reader_census.py recognises anchored readers by matching source text. A literal caret match accepted an escaped \^ and a [^ character class; the fix is a lookbehind for backslash and [. A planted fixture can pass for the wrong reason (a class not reaching the colon was flagged by a different rule), so verify each guard with a mutant that removes only that guard.

## Evidence

- `DEL-F1`
- `ev-del-f1-3`
- `1z8ou`

## Targets

- `.wavefoundry/framework/scripts/tests/test_label_reader_census.py`
