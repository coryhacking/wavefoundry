# Repo-tree census pins: home in the census module, key on the claim

Owner: Engineering
Status: active
Last verified: 2026-08-04

Memory ID: `1ug1d-mem repo-tree-census-pins-home-in-the-census-module-key-on-the-c`
Kind: `decision`
Confidence: 0.8
Created: 2026-08-04
Updated: 2026-08-04
Source exploration cost: 421254
Source event: `decision-log:1ug7o-bug seed-160-misstates-legacy-delivery-mode-mapping:9109a2ac5c03567d`
Validation: promote
Validated by: agent
Action delta: When adding a durable repo-tree census pin, put it in test_events_only_residue_census.py and key it on the false CLAIM shape, not on a bare token that is also a live legal value; do not add an allowance table when the expected count is zero everywhere.
Validation rationale: The drafted candidate is right about the home and the claim-keying but carries a detail the delivery itself removed: it prescribes "a claim-keyed allowance table", and the delivery review found that table provably inert, because any entry that would exempt an occurrence immediately fails the sibling corpus-total test. The table, its lookup branch, and its validator test were deleted in the delivery repair, so a promoted record naming the allowance table would send the next author to build scaffolding this wave just removed. Verified against the current tree: _census_files has no root parameter and includes docs/references/ while excluding docs/architecture/decisions/; _scan_delivery_mode_claim has no allowance branch; the corpus-total test and the claim scan are both present and the module is green at 24 tests. Also verified the claim-keying premise by measurement, 64 legitimate occurrences of `universal` across 28 in-scope files, of which the fail-closed default in server_impl.py is the only one a looser pattern would catch.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

A durable pin that a false doc claim has not reappeared belongs in test_events_only_residue_census.py, whose _census_files() already builds the shipped-surface scope and excludes docs/waves and docs/plans by construction, so wave archives cannot defeat it. Do not home it in a module that only reads constants; that acquires a whole-repo filesystem dependency and has no scope scaffolding. Key the pin on the false CLAIM shape (for example `delivery_mode=universal`), never on a bare token that is also a live legal value: `universal` has 64 legitimate occurrences across 28 in-scope files as an enum member and as ordinary English, so a token sweep is red on contact, then loosened, then rotted. Add no allowance table when the expected count is zero in every in-scope file: a zero-count allowance exempts nothing, and a sibling test asserting the corpus total is zero is strictly stronger and makes any exempting entry fail immediately. Extend the scope only where a real carrier lives (docs/references/ had to be added) and keep docs/architecture/decisions/ excluded when an ADR deliberately preserves the original claim under an amendment note.

## Evidence

- `1ug7o-bug seed-160-misstates-legacy-delivery-mode-mapping`
- `1ugk8`

## Targets

- `.wavefoundry/framework/scripts/tests/test_events_only_residue_census.py`
