# When a review handoff benefits from a graph

Owner: Engineering
Status: active
Last verified: 2026-11-21

Keep the existing guided review actions. Two independent coordinators reached the same correct decisions at five historical checkpoints. A dependency graph made one relationship easy to see: a single edit needed three independent checks. The baseline reader also identified all three. The graph met the safety criteria but did not meet the spec's threshold for a live orchestration trial. [Pilot spec and example diagram](<../plans/23z5n-task pilot-review-handoff-graph.md#example-handoff-from-23zbg>)

## What the coordinators decided

Each row uses the ledger up to and including the indicated line. The action count comes from the shipped review-action reader. Both coordinators reached the decision shown.

| Wave and line | Guided actions | Decision |
| --- | ---: | --- |
| 23zbg, 14 | 8 | Make one edit to the seed 070 marker requirement. Keep the docs-contract, code and QA findings separate so each reviewer verifies the edit. Repair the trusted ruling's scope and provenance separately and return it to security. |
| 23xo7, 16 | 2 | Repair the helper census for QA and the dashboard mock census for architecture. Run those focused checks before spending a full-suite run on qualification. |
| 23xo7, 42 | 2 | The earlier repairs have cleared. Check whether material edits have settled and whether the suite receipt matches the current tree. The packet supplies no matching receipt. QA and operator signoff actions remain. |
| 23xo7, 45 | 1 | A new refresh-order finding reopens QA work. Repair it and return it to QA. Preserve the other lanes' evidence within the scope they reviewed. |
| 23xo7, 64 | 1 | QA has finished. Operator signoff remains. Check the receipt against the final tree before closure. |

The historical first full run in 23xo7 took 831 seconds and found five failures. The repaired run took 754 seconds and passed 13,193 tests. Both readers chose focused checks first. This replay did not run the suite or measure time saved. [23xo7 spec](<../waves/23xo7 awaiting-closure/23xo6-enh pause-reviewed-deliveries-for-closure.md>) · [Recorded suite measurements](workflow-efficiency-2026-11-21.md)

## Where a diagram helps

Two more readers answered the same two questions. One saw a rendered Mermaid diagram. The other saw a table of the same eight dependencies. Both answered correctly.

| Work already complete | What each reader concluded |
| --- | --- |
| The marker is fixed and QA has verified it. The ruling still needs clarification. | Docs-contract and code can check now. Security waits for the ruling. Reassessment waits for all four checks. |
| Both repairs are complete. Docs-contract, code and security have verified. | QA remains. After QA verifies, the coordinator can reassess readiness. |

The diagram reader could follow all eight arrows. The table reader pointed out that four rows saying “Reassess readiness” left the requirement for **all four** checks implicit. A table can say that in one sentence. The graph is useful when a reader needs to see where work branches or rejoins. Put it in the spec that owns those dependencies, or in the wave record when they cross specs. A linear sequence needs only a list. The review ledger continues to track which checks have actually run.

The exact Mermaid block in the spec rendered locally with seven labeled nodes and eight edges. GitHub supports this fenced format. Wavefoundry v1.47.0's dashboard Markdown renderer displays the block as source. The sentence above the diagram explains the dependencies for readers there. [Example in the spec](<../plans/23z5n-task pilot-review-handoff-graph.md#example-handoff-from-23zbg>) · [Dashboard renderer](../../.wavefoundry/framework/dashboard/ds/wfds.js) · [GitHub diagram support](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)

## How to repeat the replay

1. Use v1.47.0, commit `23a98b65`. Slice each ledger at the line numbers above before projecting its state. Use readiness for 23zbg and delivery for 23xo7. [23zbg ledger](<../waves/23zbg review-and-planning-guidance/events.jsonl>) · [23xo7 ledger](<../waves/23xo7 awaiting-closure/events.jsonl>)
2. Take required lanes from the last policy receipt in each slice. Include council readiness for readiness, and operator signoff plus any required delivery council for delivery. Pass the slice and signoffs to `_guided_review_actions` with the corresponding approval phase and run kind (`readiness` or `initial_delivery`). Keep all returned actions, lane observations and the explicit notice that current source and receipt identity are unknown. None of these five projections truncated its actions. [Review-action implementation](../../.wavefoundry/framework/scripts/wf_server/server_impl.py)
3. Give one reader that baseline. Give a second independent reader the same packet plus the dependencies, the outstanding actions and what would invalidate qualification. Build repair groups from blocking, unfinished `current_synthesis_heads`. An analyst grouped the three seed 070 findings after reading them. Both arms received the underlying observations. Reviewers retained their individual finding IDs. [Review evidence reader](../../.wavefoundry/framework/scripts/review_evidence.py)
4. Score each reader on repair choice, verification ownership and qualification. A candidate advances only if it corrects a baseline decision while preserving every required check. For the separate visual comparison, give fresh readers the same two questions above and vary only the presentation.

This was a desk trial on two selected waves. The coordinators used the same model family and received the five cutoffs in order in one packet each, so later checkpoints were visible. Preparing the graph required an analyst to identify a shared cause and check the links to each reviewer. The trial did not reconstruct historical working trees, measure reader speed or compare live engineering teams. A future proposal to automate scheduling needs evidence of a missed decision or repeated work that the additional machinery actually prevents.
