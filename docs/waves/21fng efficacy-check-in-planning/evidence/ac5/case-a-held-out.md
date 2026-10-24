Owner: Engineering
Status: active
Last verified: 2026-10-23

# Derive the Intent Outcome Assessment Automatically at Wave Close

Operators currently write the `Intent outcome:` paragraph in a wave's Review Checkpoints by hand, stating whether the intended benefit was achieved, partial or not established. This is repetitive, and at close the operator is usually restating what the change documents already record. Each change document already lists its acceptance criteria with `[x]`, `[~]` and `[ ]` checkboxes, and every AC must be settled before close. Propose that `wf_close_wave` derive the assessment from those checkboxes and write the `Intent outcome:` line itself. When every AC across the admitted changes is `[x]` the line reads achieved; when some are `[~]` it reads partial; when ACs are unmet or absent it reads not established. The generated line would cite the change ids and the checked ACs as its evidence references and flow into the Wave Summary through the existing close-summary composer. Operators could still override the generated line, but the default requires no authoring, which shortens close and makes every closed wave carry a uniform, consistently worded assessment.

Source: the Decision Log row "Preserve explicit outcome assessment; never infer it from task completion" in `docs/waves/2124l explicit-intent-through-lifecycle/2124m-enh explicit-intent-through-lifecycle.md` (its rejected-alternative column, "Synthesize success from checked ACs"), plus that change's Product Intent and Requirement 4 for context. Deliberately left out: the rationale column and the rejection reason, and any critique of the idea.
