# Decision: Home the census pin in `test_events_only_residue_census.py`…

Owner: Engineering
Status: superseded
Last verified: 2026-08-04

Memory ID: `1uga6-mem decision-home-the-census-pin-in-test-events-only-residue-cen`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-04
Updated: 2026-08-04
Source exploration cost: 421254
Source event: `decision-log:1ug7o-bug seed-160-misstates-legacy-delivery-mode-mapping:9109a2ac5c03567d`
Validation: rewrite
Validated by: agent
Action delta: When adding a durable repo-tree census pin, put it in test_events_only_residue_census.py and key it on the false CLAIM shape, not on a bare token that is also a live legal value; do not add an allowance table when the expected count is zero everywhere.
Validation rationale: The drafted candidate is right about the home and the claim-keying but carries a detail the delivery itself removed: it prescribes "a claim-keyed allowance table", and the delivery review found that table provably inert, because any entry that would exempt an occurrence immediately fails the sibling corpus-total test. The table, its lookup branch, and its validator test were deleted in the delivery repair, so a promoted record naming the allowance table would send the next author to build scaffolding this wave just removed. Verified against the current tree: _census_files has no root parameter and includes docs/references/ while excluding docs/architecture/decisions/; _scan_delivery_mode_claim has no allowance branch; the corpus-total test and the claim scan are both present and the module is green at 24 tests. Also verified the claim-keying premise by measurement, 64 legitimate occurrences of `universal` across 28 in-scope files, of which the fail-closed default in server_impl.py is the only one a looser pattern would catch.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1ug1d-mem repo-tree-census-pins-home-in-the-census-module-key-on-the-c`
## Summary

Decision (wave 1ugk8): Home the census pin in `test_events_only_residue_census.py` with a claim-keyed allowance table, not in `test_review_policy.py` with a token sweep. Rationale: The census module already owns the exact scope and archive-immunity this needs and already has the allowance-table idiom; `test_review_policy.py` reads module constants and would acquire a whole-repo filesystem dependency. Claim-keying is forced by `universal` being a live legal enum with roughly twenty legitimate occurrences.

## Evidence

- `1ug7o-bug seed-160-misstates-legacy-delivery-mode-mapping`
- `1ugk8`

## Targets

- `test_events_only_residue_census.py`
- `test_review_policy.py`
