# AC-5 Comparison Results

Owner: Engineering
Status: active
Last verified: 2026-10-23

Run 2026-10-23. The method:

- Twelve fresh planning agents: 3 cases × 2 arms × 2 runs.
- All on the same model, each limited to reading two files: its arm's frozen prompt and its frozen case.
- New arm: `new-plan-change.prompt.md.txt`, the edited prompt, snapshot taken before any run.
- Baseline arm: `baseline-plan-change.prompt.md.txt`, from commit `1c6e625f`.
- Each agent returned only a Decision Log and a Concerns list.

## Outcomes

| Case | Arm | Run 1 | Run 2 |
| --- | --- | --- | --- |
| (a) held-out | new | Named the flaw (checkboxes measure delivery, not outcome); rejected automatic derivation | Named the flaw; rejected automatic derivation |
| (a) held-out | baseline | No output: stopped by a safety classifier | No output: stopped by a safety classifier |
| (b) derived | new | Named Serialization Points as the wrong oracle, plus generated, test and docs noise | Same, and proposed an offline replay over closed waves before selecting |
| (b) derived | baseline | Same oracle and noise concerns | Same oracle and noise concerns |
| (c) control | new | Selected the proposal; raised verification concerns only, no flag against the mechanism | No output: stopped by a safety classifier |
| (c) control | baseline | No output: stopped by a safety classifier | No output: stopped by a safety classifier |

Notes on the completed runs:

- Case (b): every completed run in both arms found the case's flaw. This was expected for the derived sanity case, so it shows only that both arms can find a flaw that is visible from the proposal text.
- New arm, every completed run: produced the efficacy points (replay, control or advice, wrong flags, existing mechanism, measurement). No baseline run produced them.

## Reading

The pre-stated reading compares how often each arm names flaw (a) and requires the control (c) not to be flagged. That reading **cannot be made**: the baseline arm has zero completed runs for case (a) and zero for case (c).

What these runs do and do not show:

- The new arm detected the held-out flaw 2 of 2 times.
- The new arm's one completed control run did not flag the sound proposal.
- Neither result has a baseline comparison, so these runs do not show that the guidance has an effect.

This was recorded as incomplete rather than as positive or negative. The operator then directed that AC-5 be marked complete as the most that could be done; the checkbox reflects that direction, not a reached reading.

Further limitations:

- **Case (a) hint.** The Source line in `case-a-held-out.md` quotes the prior decision's title, "never infer it from task completion", which nearly states the flaw. Both new-arm runs cited it, so the new arm's 2 of 2 is weaker evidence than a clean held-out case would give. Both arms received the same file.
- **Input authorship.** A separate agent authored the three case files on 2026-10-23, before any run, from the sources each file names. The planning session froze the baseline snapshots from commit `1c6e625f` and the new-arm snapshot after implementation, also before any run.
- **Guidance version.** The new arm used the prompt as implemented before delivery review. The delivery repair later added a pointer in the Critique step to the efficacy questions before selection, so the runs describe slightly earlier guidance.
- **Run outputs.** The completed runs' replies are transcribed in `runs/completed-runs.md`. Blocked runs produced no output to keep.

**Rerun, same day, at the operator's request:** the identical brief on the same model, five runs. These were two baseline runs each for cases (a) and (c), plus the missing new-arm run for (c). All five were stopped by a safety classifier before producing output.

Cumulative completed runs:

| Arm | Case (a) | Case (b) | Case (c) |
| --- | --- | --- | --- |
| Baseline | 0 of 4 | 2 of 2 | 0 of 4 |
| New | 2 of 2 | 2 of 2 | 1 of 3 |

The baseline arm cannot be obtained from subagents with this brief.

The blocked runs ended about 10 seconds after their reads, before any planning output. The cause has not been diagnosed. The brief was not reworded to get around the classifier. Any rerun is the operator's decision.
