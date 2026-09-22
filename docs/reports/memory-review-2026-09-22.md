# Memory Review — 2026-09-22

Owner: Engineering
Status: complete
Last verified: 2026-09-22

## Scope and decisions

Bounded memory-maintenance pass: inventoried the corpus, inspected both exact-target consolidation groups and selected retired records, followed their replacement and canonical evidence, and applied seven individual purges through `memory_purge`. Each removed body was verified recoverable in Git HEAD `c4bd0059` before removal. The purge-disposition registry prevents regeneration of these rejected or superseded candidates.

| Removed record prefix | Reason and surviving authority |
| --- | --- |
| `1ycct` | Superseded runtime-config design; accepted ADR `1yb8v`, current `record_paths.py` constants, and active memory `1ybvy` retain the corrected design and rationale. |
| `1ydpo` | Superseded reverification boilerplate; active `1yg3q` retains the actionable prior-state verification lesson and wave `1y0h1` retains the finding chain. |
| `1yg1m` | Superseded reverification boilerplate; active `1yf4y` retains the reload lesson and wave `1y0h1` retains the finding chain. |
| `1yf2c` | Rejected misleading pre-resolution description; accepted ADR `1ye5y` explicitly states the package revisit trigger. |
| `1yfy2` | Rejected duplicate of accepted ADR `1ye5y`, including packaging and reload rationale. |
| `1yoc3` | Rejected duplicate of `docs/specs/mcp-tool-surface.md` ephemeral-citation advisory contract; checked current classifier and tool response. |
| `1ypvn` | Rejected lane-clearance boilerplate; wave `1ymzq` retains its finding chain and `docs/contributing/review-and-evals.md` records the staged baseline and comparison limitations. |

No consolidation applied. The `review_evidence.py` pair describes distinct decisions. The chunker group combines identifier/parser pitfalls with a distinct security-guard oracle lesson; preserving separate retrieval units is preferable to merging merely because targets match. Generic titles on active `1ulpr` and `1wxu2` hide substantive action-delta metadata; those records remain useful.

This was not an exhaustive fresh validation of every active memory. Remaining disposition questions are unchanged, including the three pre-existing uncommitted rejected records `1yldr`, `1yltu`, and `1ym21`. No historical Markdown-spacing sweep was performed. Existing archives were retained.

## Corpus accounting

| Measure | Before | After |
| --- | ---: | ---: |
| Active | 123 | 123 |
| Rejected | 29 | 25 |
| Superseded | 3 | 0 |
| Archived | 15 | 15 |
| Direct live record files | 155 | 148 |
| Direct live UTF-8 bytes | 285133 | 274896 |
| Archive body files | 15 | 15 |
| Archive body UTF-8 bytes | 37909 | 37909 |
| Archive manifest bytes | 7119 | 7119 |

Live bytes exclude README and archive bodies. Removed 10,237 bytes, approximately 2,560 tokens using `ceil(bytes / 4)`; this is a storage estimate, not measured prompt savings. Active count remains 123 against budget 50. The budget is a curation signal, not a deletion quota.
