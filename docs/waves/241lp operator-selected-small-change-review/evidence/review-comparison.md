# Small-change review comparison

Owner: Engineering
Status: complete
Last verified: 2026-11-22

One independent code reviewer and an ordinary panel of one code reviewer and one QA reviewer examined the same four Python examples. Each reviewer recorded findings before reading the others. All three ran before-and-after probes. The small lane and ordinary panel identified the same three material problems. The sample establishes agreement on these inputs. It cannot establish how often a specialist catches an additional problem in production.

| Input and required outcome | Observed result | Review outcome |
| --- | --- | --- |
| Preserve the first duration for each name, including zero. | On repeated measurements of zero followed by a positive value, the truthiness check overwrote the zero. | Both arms asked for repair. |
| Extract UTC-day grouping into a helper. | Both versions gave the same UTC dates across midnight for offset timestamps. | Both arms approved. |
| Keep the latest N samples, including an empty window at N=0. | The replacement slice retained every item at zero. The earlier loop cleared the list. | Both arms asked for repair. |
| Historical compatibility control from 210eb. Exclude a note from a setup stamp. | A checkout with a note in its old stamp reported a mismatch on unchanged input. Rewriting the stamp allowed later note edits. | Both arms identified the existing-user defect. The small-lane reviewer escalated its external effect. |

**Reviewer effort.** The small reviewer recorded 14 elapsed seconds. The ordinary code reviewer recorded 13 seconds and the QA reviewer 27 seconds, totaling 40 reviewer-seconds across two people or contexts. These intervals cover examination of the examples and the probes. They exclude scheduling, orchestration, lifecycle operations and test qualification. The reviewers did not measure queue time or full-suite duration for either comparison arm.

**Limits.** The three internal cases used synthetic snippets. The compatibility control modeled the published concern using deterministic configuration equality. These examples exercised reviewer judgment independently of the lifecycle tool tests. They used one model family. End-to-end time saved on live changes remains unknown.
