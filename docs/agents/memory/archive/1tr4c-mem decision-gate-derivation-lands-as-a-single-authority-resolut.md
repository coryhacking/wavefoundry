# Decision: Gate derivation lands as a single authority-resolution faca…

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1tr4c-mem decision-gate-derivation-lands-as-a-single-authority-resolut`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-27
Updated: 2026-11-25
Source exploration cost: 1158805
Source event: `decision-log:1to77-enh preship-events-authority-hardening:102e55efc290ffa8`
Validation: promote
Validated by: agent
Action delta: When adding any new gate read of review-evidence content (signoff presence, currency, severity), consume resolve_review_authority in review_evidence.py rather than parsing wave.md prose; the residue census forbids the prose-evidence tokens outside that facade, so a direct read fails the census.
Validation rationale: The decision is real and load-bearing: the facade exists at review_evidence.py with six converted gate surfaces in server_impl.py, the census forbidden-token backstop is a live executed control, and the delivery council independently confirmed the topology cycle-free. The action delta governs every future gate change, which is exactly the durable class the corpus wants; the spec documents the contract but the memory carries the do-this-next rule.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Checked at: 2026-11-25T16:09:19Z
Check note: Item 7 review: encoded elsewhere. Implemented and enforced: resolve_review_authority (.wavefoundry/framework/scripts/review_evidence.py:3789) is the single facade, documented in docs/architecture/contracts/mcp-tool-surface.md:2133, and tests/test_events_only_residue_census.py::EventsOnlyResidueCensusTests::test_prose_evidence_reads_stay_inside_the_facade asserts no prose evidence read exists outs.
Check flags: target_churn, target_not_canonical
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, encoded in Implemented and enforced: resolve_review_authority (.wavefoundry/framework/scripts/review_evidence.py:3789) is the single facade, documented in docs/architecture/contracts/mcp-tool-surface.md:2133, and tests/test_events_only_residue_census.py::EventsOn.
Archive path: `docs/agents/memory/archive/1tr4c-mem decision-gate-derivation-lands-as-a-single-authority-resolut.md`

## Summary

Decision (wave 1to78): Gate derivation lands as a single authority-resolution facade in `review_evidence.py`, not five point patches.. Rationale: The defect class being fixed is second-derivation drift across scattered call sites; one seam makes inertness provable at one place, lets the residue census forbid prose reads outside the facade (so future gates cannot silently regress), and documents one contract in the spec instead of five behaviors. Proposed independently by the red-team primer and the rotating docs-contract seat..

## Evidence

- `1to77-enh preship-events-authority-hardening`
- `1to78`

## Targets

- `review_evidence.py`
