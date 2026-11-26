# Decision: The `server_impl.py` demotion site adopts the shared consta…

Owner: Engineering
Status: archived
Last verified: 2026-10-07

Memory ID: `1zz0q-mem decision-the-server-impl-py-demotion-site-adopts-the-shared-`
Superseded by: `24an6-mem retrieval-demotion-shares-only-the-history-components`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-11-25
Source exploration cost: 97308
Source event: `decision-log:1zxnt-maint correctness-and-test-hygiene-round:c6848bf011bfc53d`
Validation: promote
Validated by: agent
Action delta: The retrieval demotion shares only journals/snapshots with history_paths, applies them to document results only, and keeps its own reports and name tests.
Validation rationale: server_impl._doc_demotion_weight uses is_history_path for non-code kinds and keeps reports/feedback/journal name tests, verified in delivery review.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Archived: 2026-11-25
Archive reason: Superseded by 24an6-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1zz0q-mem decision-the-server-impl-py-demotion-site-adopts-the-shared-.md`

## Summary

Decision (wave 1zyb2): The `server_impl.py` demotion site adopts the shared constant for `journals` and `snapshots` but keeps `reports` and the name tests.. Rationale: It is a ranking heuristic with different members; only the shared members should be shared..

## Evidence

- `1zxnt-maint correctness-and-test-hygiene-round`
- `1zyb2`

## Targets

- `server_impl.py`
