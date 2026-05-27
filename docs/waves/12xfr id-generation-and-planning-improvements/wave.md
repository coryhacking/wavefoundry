# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-27

wave-id: `12xfr id-generation-and-planning-improvements`
Title: Id Generation And Planning Improvements

## Objective

Improve two framework weak points discovered during `12wsj`: (1) lifecycle ID generation can produce duplicate prefixes when two IDs are created in the same 2-minute window; (2) the `Plan feature` step has no divergent ideation phase, so framing errors and missed alternatives are only caught at red-team/council review after the plan has anchored.

## Changes

Change ID: `12xfc-enh divergent-pre-plan-ideation`
Change Status: `complete`

Change ID: `12xfq-enh lifecycle-id-base36-collision-avoidance`
Change Status: `complete`

Change ID: `12xga-maint test-suite-load-server-cache`
Change Status: `complete`

Change ID: `0rlcw-doc search-retrieval-heuristics-canonicalization`
Change Status: `complete`

Change ID: `0rld3-bug test-runner-single-run-guard`
Change Status: `complete`

Change ID: `0rlec-bug indexer-cross-process-lock`
Change Status: `complete`

Change ID: `0rle6-bug reranker-cache-local-path`
Change Status: `complete`

Change ID: `0rlgv-feat update-indexes-bin-wrapper`
Change Status: `complete`

Change ID: `0rlg4-bug friendly-message-for-index-build-lock-busy`
Change Status: `complete`

Change ID: `0rlga-bug venv-aware-mcp-server-status-message`
Change Status: `complete`

Change ID: `0rlgd-bug clean-index-update-completion-message`
Change Status: `complete`

Change ID: `0rlgn-bug manual-index-refresh-no-upgrade-runner`
Change Status: `complete`

Change ID: `0rlgw-bug dashboard-index-lock-busy-skip`
Change Status: `complete`

## Wave Summary

Two enhancements: `12xfc` adds a required diverge/critique/select pass to `Plan feature` (seed-170 and its rendered local surface) so alternative approaches are evaluated before a plan is drafted. `12xfq` replaces the Crockford base32 alphabet with base36, encodes the 5th prefix character as elapsed minutes since epoch `% 36` for per-minute resolution, and adds borrow-from-future collision avoidance via filesystem scan. A supporting maintenance fix adds a single-run guard to `run_tests.py` so overlapping invocations do not multiply the subprocess fan-out.

## Journal Watchpoints

- **Blocking (`12xfq`):** Open `framework_edit_allowed` gate before editing `lifecycle_id.py`; close immediately after. Test updates do not require the gate.
- **Blocking (`12xfc`):** Open `seed_edit_allowed` gate before editing `seed-170`; close immediately after the seed edit before touching the rendered prompt surface.
- **Watchpoint (`12xfq`):** Existing IDs in `docs/plans/` and `docs/waves/` use Crockford base32 characters — base36 is a superset, so all existing IDs remain scannable without migration.
- **Serialization (`12xfq`):** Implement `decode_base36` before the borrow-from-future scan; the increment loop depends on it.

## Review Evidence

- wave-council-readiness: approved 2026-05-26 — Two independent enhancements with tight scope and testable ACs. `12xfc` is seed+docs only (seed gate required); `12xfq` is framework script + tests (framework gate required). No dependency between them; can implement in parallel. Required lanes: code-reviewer (`12xfq` algorithm and tests), docs-contract-reviewer (`12xfc` seed language), qa-reviewer (AC verification across both). No blocking contradictions. Wave is ready for implementation.
- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-26: PASS** (red-team fixed seat; docs-contract-reviewer rotating seat)
  - Strongest challenge: `12xfq` touches every test in `test_lifecycle_id.py`; incomplete test update would leave the gate failing with no clear signal.
  - Best alternative considered: keep Crockford base32 and use `% 32` to avoid alphabet change — rejected: base36 allows `% 36` to fit exactly with no wasted symbols.
  - Council verdict: scope is tight, ACs are testable, gate requirements are explicit in watchpoints. Both changes are independent and can implement in parallel. No blocking contradictions.

## Dependencies

- No external wave dependencies.
