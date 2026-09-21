# Readiness protocol behavioral scenarios

Owner: Engineering
Status: active
Last verified: 2026-09-20

## Method

Independent evaluator `/root/readiness_behavior_scenarios` received the authored seed 215, seed 209 and Wave Council role, plus the five packets below. It authored no implementation, inspected no tests or AC expected answers, and made no lifecycle mutations. Expected outcomes below were compared with its returned decisions. This is an observed instruction-following exercise, separate from instruction-presence tests and runtime verification.

## Packets and observations

| Case | Input packet | Expected decision | Observed decision and scope | Mismatch |
| --- | --- | --- | --- | --- |
| Wording preference | Accepted path-plus-available-inode design explicitly accepts replacement-volume inode reuse ambiguity for a scoped reboot fix. Only objection changes “inode when available” to “available inode”; no behavioral difference. | Untyped note; no reopening accepted design. | No blocker. Carry wording as an implementation note without requiring plan publication or another review. Obtain normal current approvals if absent. | None |
| Successful repair | Full review identified source drift. One repair adds a byte-hash guard. Packet contains finding, diff and affected atomicity/reader fail-closed contracts; retained guard checks pass. All required lanes and council reviewed effects and approved the current receipt. | Complete finding resolution and proceed without unrelated sweep. | Ready under stipulated facts after source/blocking lanes terminalize the original finding if needed. Verify original reproduction, adjacent controls and replacement defects; no second automatic repair or full council merely because a guard was added. | None |
| Regression against unchanged contract | Same repair moves sidecar deletion outside its transaction. Unchanged affected contract requires deletion atomic with publication. Focused rollback probe demonstrates inconsistent sidecar after the one repair. | New defect remains blocking; escalate rather than automatically repair again. | Not ready. The unchanged atomicity contract is within affected scope. Record the replacement blocker, preserve lane authority and escalate for operator choice of another bounded pass or replanning. | None |
| Original blocker survives | Required AC has no observable oracle. One repair changes prose but still gives no pass/fail oracle. Focused verification confirms defect; no further pass authorized. | Retain blocker and escalate without another automatic repair. | Not ready. Retain original finding, specify the missing oracle and escalate; do not manufacture approval or defer essential verification to delivery. | None |
| Receipt rotation | All four lanes and council approved R1. Prepare publishes repaired packet as R2; focused probes pass. Only code reviewer has recorded R2 approval. | QA, architecture, docs-contract and council must review effects and record current approvals; no unrelated sweep. | Not implementable. Those four approvals must bind R2; code's current approval need not repeat. Complete any outstanding finding replay/terminalization, confirm no blockers and current receipt coverage, then activate. | None |

## Limitations

Five finite synthetic cases shared one fresh independent context; these are not five independent reviewers or model replications. Fictional probe results and receipt states were stipulated inputs, not executed product tests. The evidence supports the reported decisions for these packets, not universal convergence, runtime correctness, or a guarantee of approval. The evaluator reported no blocking ambiguity in the authored instructions.
