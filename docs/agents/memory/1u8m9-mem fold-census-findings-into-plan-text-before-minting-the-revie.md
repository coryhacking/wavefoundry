# Fold census findings into plan text before minting the review-policy receipt

Owner: Engineering
Status: active
Last verified: 2026-08-06

Memory ID: `1u8m9-mem fold-census-findings-into-plan-text-before-minting-the-revie`
Kind: `decision`
Confidence: 0.9
Created: 2026-08-02
Updated: 2026-08-05
Source exploration cost: 326846
Source event: `decision-log:1u8o4-ref rename-summary-schema-to-schema-version:094374b7875512eb`
Validation: promote
Validated by: agent
Action delta: Before minting a review-policy receipt on a contract-surface change, fold every council/lane census finding into the plan text first; the receipt must be minted against the amended bytes or the recorded approvals lapse.
Validation rationale: The generated draft is wave-narrative (it names the specific gaps verbatim) and its auto-derived target test_server_tools.py is incidental. The durable mechanism underneath is real and recurred twice in this wave alone: plan amendments after receipt mint stale the receipt and void approvals, so the census-fold must precede the mint. Rewritten to state the reusable ordering rule with the correct target (the review-policy receipt seam).
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1u8o5: readiness-council and lane reviews surfaced plan-text gaps (missed doc surfaces, test-design pins). Because the review-policy receipt digests the change-doc bytes, every such finding must be folded into the plan BEFORE wf_prepare_wave mints the receipt; a substantive amendment after the mint supersedes the receipt and lapses the READINESS-phase approvals bound to it, forcing a re-record cycle. The rule is unchanged; two boundaries make it precise (corrected 2026-08-05, wave 1uhcb). What lapses is the readiness roster, the council readiness approval plus every prepare lane, because `policy_receipt_id` is legal only on a readiness-phase approval; delivery-phase approvals, finding heads, and repair records carry no receipt binding and survive. And the digest is every byte except two deliberately excluded non-substantive carriers: the gardener-owned `Last verified:` date line (wave 1tz6k) and the `## Progress Log` body (wave 1ugk9), so recording a repair no longer lapses anything. Every requirement-bearing section stays digested, including Scope, Requirements, Acceptance Criteria, AC Priority, and Tasks, so folding a census finding still requires the fold to precede the mint. The wave paid this cost twice (receipts e1dd99 and 7b4074 each superseded after in-phase amendments) before the delivery receipt was minted against final bytes.

## Evidence

- `1u8o5`
- `1u8o4-ref rename-summary-schema-to-schema-version`
- `receipt chain e1dd992d -> 7b40746c -> 0853e670`

## Targets

- `.wavefoundry/framework/scripts/review_policy.py`
