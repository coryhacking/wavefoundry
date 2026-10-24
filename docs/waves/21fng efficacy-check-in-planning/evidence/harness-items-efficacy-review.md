# Harness Items Efficacy Review

Owner: Engineering
Status: active
Last verified: 2026-10-23

Record of the 2026-10-23 review that motivated change `21fnf`. Source article: Ahmed Besbes, "Harness Engineering: Make Your Coding Agent Better Without Changing the Model" (The Tech Buffet #31, 2026-10-10). Seven candidate harness improvements were proposed, then each was tested against its own goal with six questions: replay the motivating case through the mechanism; leverage (control or advice); evidence of need; precision and noise; a cheaper path; how success will be measured.

| # | Proposal | Efficacy finding | Decision |
| --- | --- | --- | --- |
| 1 | Repeated-failure loop detection (failure fingerprints) | Advisory only (Wavefoundry does not own the agent loop); real loops are often not byte-identical; no data on frequency | Build as advisory data gathering |
| 2 | Scope-drift sensor (diff vs declared review targets) | Motivating case `test_memory_backfill.py` sits inside the declared `.wavefoundry/framework/scripts/tests/` directory target, so the sensor would not flag it; generated files make every diff noisy | Hold until a replay over closed waves shows useful precision |
| 3 | Compact failure digests | Runner already prints failing files; marginal alone | Merge into item 1 |
| 4 | Richer session-start brief | Staleness occurred after compaction, not at session start; needs the compact trigger and a size cap | Build |
| 5 | Claims-vs-evidence check | Matching behaviour claims in prose to a diff has low precision; reviewers and the test receipt already catch overstated progress | Drop |
| 6 | Harness evaluation task set | Model variance needs many runs; costly; closed-wave ledgers already hold outcome data | Replace with ledger metrics |
| 7 | Sandboxing guidance | Low cost; corrects false assumptions about gates | Build (documentation) |

Four of the seven proposals changed (dropped, held, replaced or merged) after the six questions were applied.
