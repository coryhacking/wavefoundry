# Reconciliation fence consumers must share strict closing semantics

Owner: Engineering
Status: active
Last verified: 2026-11-26

Memory ID: `1w0ob-mem reconciliation-fence-consumers-must-share-strict-closing-sem`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-08-23
Updated: 2026-11-26
Source exploration cost: 982767
Source event: `finding:1w3br:CODE-DEL-FENCE-CLOSE-CONTEXT-001`
Validation: promote
Validated by: agent
Action delta: When changing reconciliation Markdown fence handling, update both heading-context and archive-span consumers and test backtick/tilde pseudo-closers with trailing text plus valid whitespace-only closers.
Validation rationale: The generated summary was truncated and mixed durable parser guidance with review-ledger mechanics. The underlying lesson is durable and verified in current reconcile_scan.py: both _finding_context and _archive_row_spans share the same close predicate, and the delivery mutant proved that omitting the whitespace-tail check can retarget persistent v2 heading identity.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Checked at: 2026-11-26T06:32:40Z
Check note: Heading context contributes to persisted finding keys. Fixture coverage must keep both fence consumers synchronized. Reviewed .wavefoundry/framework/scripts/reconcile_scan.py:1529.
Check flags: target_churn

## Summary

In reconcile_scan.py, a fenced-code closer must use the opener character, meet or exceed its length, and contain only trailing whitespace. Keep _finding_context and _archive_row_spans synchronized. Regression coverage must include backtick and tilde fence-like lines with trailing non-whitespace (remain content), valid whitespace-only closers, ignored fenced headings, and archive-row parity; otherwise fenced examples can retarget the heading context embedded in persistent v2 disposition keys.

## Evidence

- `CODE-DEL-FENCE-CLOSE-CONTEXT-001`
- `ev-code-del-fence-close-context-001-3`
- `1w3br`

## Targets

- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `symbol:_finding_context`
- `symbol:_archive_row_spans`
