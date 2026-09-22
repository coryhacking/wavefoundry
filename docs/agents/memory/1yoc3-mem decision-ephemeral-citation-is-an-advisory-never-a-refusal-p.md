# Decision: Ephemeral citation is an advisory, never a refusal; predica…

Owner: Engineering
Status: rejected
Last verified: 2026-09-22

Memory ID: `1yoc3-mem decision-ephemeral-citation-is-an-advisory-never-a-refusal-p`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-22
Updated: 2026-09-22
Source exploration cost: 805735
Source event: `decision-log:1yoy2-bug review-ledger-tool-gaps:6a841426947632d9`
Validation: reject
Validated by: agent
Action delta: No additional durable action: consult the canonical review-event contract, which already requires advisory-only handling of temporary citations.
Validation rationale: Followed the 1yoy2 Decision Log and Requirement 3 and verified current review_evidence.ephemeral_artifact_tokens and server_impl.wf_review_event_response. The target is accurate, but docs/specs/mcp-tool-surface.md:826 already states the same advisory-only rule and lexical boundaries; retaining a separate memory would duplicate the authoritative contract without adding a future-action delta.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1ypxw): Ephemeral citation is an advisory, never a refusal; predicate in `review_evidence.py`, diagnostic in the tool.. Rationale: A refusal would block a lane over citation style; the validator's error channel refuses writes..

## Evidence

- `1yoy2-bug review-ledger-tool-gaps`
- `1ypxw`

## Targets

- `review_evidence.py`
