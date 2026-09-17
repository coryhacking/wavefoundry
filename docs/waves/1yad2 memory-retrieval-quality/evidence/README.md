# Memory retrieval evidence

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Final decision and measured benefit

Adopt memory-scoped equal-weight RRF followed by CPU summary relevance checks on at most five candidates. The calling agent still judges relevance, applicability and direct support; returned records carry `support_verified=false`. Ordinary code/docs search, memory briefing and unsolicited advisory ordering are outside this change.

The final comparison used the actual old and new public paths, the same completed SQLite snapshot, 24 independently authored cases (16 answerable, eight no-match), and 100 warm calls per variant.

| Measure | Before | After |
| --- | ---: | ---: |
| Queries with expected useful memories | 12/16 | 15/16 |
| Queries with independently judged direct support | 11/16 | 15/16 |
| Nonempty no-match responses | 0/8 | 0/8 |
| Direct-support precision across returned records | 68.75% | 71.43% |
| Warm p95 | 614.0 ms | 192.2 ms |

No previously useful query lost all useful support. Six adjacent, non-answering records remain. Results are a small local memory evaluation, not proof for arbitrary repositories. Native execution was macOS ARM64/Python 3.13.5 on CPU; no Windows/Linux performance claim. Canonical verification passed 9,126 tests across 95 files with 12 disclosed skips.

## What to read and retain

| Artifact | Why it remains |
| --- | --- |
| [Production qualification](summary5-production-qualification.md) | Final behavior, quality, timing, environment and limits. |
| [Final verification](summary5-final-verification.md) | Canonical test receipt, input hash and delivery status. |
| [Final delivery review](summary5-final-delivery-review.md), [final QA](summary5-final-qa.md) | Independent review, mutation controls and repaired boundary verification. |
| [Integration preflight](summary5-integration-preflight.md) | Frozen protocol and explicit post-observation acceptance revision. |
| `summary5-production-qualification.json.gz` | Exact final results/timings, baseline source, reviewed hashes and executed repair probes. |
| `summary5-integration-preflight.json.gz` | Frozen queries/parameters, original candidate lists, blind identity mapping and relevance judgments. |
| `qualification-inputs.json.gz` | Byte-identical corpus and original query fixture, plus the helper imported by final benchmark scripts. |
| `qualification-models.json`, `qualification-parameters.json` | Model/runtime hashes and original frozen comparison settings. Final summary5 settings are in the preflight bundle. |
| `summary5-delivery-qa.json.gz` | Reproducer and mutations for the stale-source defect, needed to explain the repair. |
| Remaining review/decision reports and small control results | Evidence cited by the immutable review ledger and the evolution of the decision. |
| [Retention manifest](retention-manifest.json) | Hashes and disposition of removed files, plus retained bundle hashes. |

The review ledger (`../events.jsonl`), wave record, acceptance criteria, reviewer reports, final measurements and blind judgments are retained. Earlier reports describe what was known at their date; statements that production was unchanged or adoption refused are historical, superseded by final production qualification. The ledger is not rewritten to erase that history.

## Lessons from the retired experiments

- Nearest-neighbour ranking and per-query score normalization do not establish that an answer exists. Ungated RRF and score fusion returned results for all eight negatives in the original qualification.
- Weighted RRF and lexical injection offered no compelling qualified advantage over equal-weight RRF. Score fusion's small exploratory gain did not resolve abstention.
- Qualifying title/action/summary text could reject useful evidence; summary-only representation improved the measured balance without lowering the -4 raw-logit cutoff. The score is not a probability or proof of support.
- Checking five summaries retained the measured usefulness of checking twenty while reducing latency. Agent-side evidence review remained the caller's responsibility; no extra host-agent service was added.
- The initial no-new-empty gate rejected an empty response replacing an irrelevant baseline hit. The operator explicitly revised acceptance to prevent loss of useful support instead. [The preflight](summary5-integration-preflight.md) records this after-observation decision; it is not a retroactive claim that the original gate passed.
- Final review found and repaired stale source/vector matching and incomplete cached-model recovery guidance. Those findings and independent reverification remain in the ledger.

Earlier exploratory dumps, development/old holdout outputs, follow-up experiment dumps and redundant logs were deleted by operator direction on 2026-09-17. Their aggregate outcomes and caveats remain in [original qualification](qualification-report.md) and [follow-up](relevance-followup.md). Do not claim their raw results are still independently replayable. Those observed datasets are development material for any future tuning, not fresh holdouts.

## Audit and reproduction

Each retained gzip bundle is JSON; its `files` entries contain original text and SHA-256 hashes. Audit the final metrics from the final result files and the blind packet/map/verdicts without loading models. The production bundle and preflight bundle are unchanged by cleanup. The input bundle preserves the original corpus/query bytes and the `wf_relevance_probe.py` dependency formerly kept only in the removed follow-up bundle.

For an execution rerun, use a disposable checkout with the reviewed source/model versions. Extract the two fixture files from `qualification-inputs.json.gz` into that checkout's wave `evidence/` directory, and extract the helper and final benchmark scripts into a scratch script directory. `../qualification_eval.py` remains the historical evaluation harness. The scripts contain machine-specific repository and `/private/tmp` paths and an old `HEAD` lookup: adapt paths and use the retained baseline function/recorded baseline commit, never today's HEAD as the old baseline. Reconstruct a complete index from the matching source corpus; its snapshot hash is recorded, but the large SQLite snapshot is not retained here. The harness must refuse corpus drift or incomplete epochs. Exact historical timings cannot be regenerated from hashes alone.

The archived scripts are inert audit text, not portable maintained executables. Restoring inputs is an explicit reproduction step; the removed standalone fixtures are not a live runtime dependency. Frozen corpus, queries and judgments include project-owned memory text: keep them local and out of aggregate-only public MCP evaluation responses.
