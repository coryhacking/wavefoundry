---
name: wf-close-spec
description: Close one admitted change inside the open wave, marking it complete and activating its dependents; never closes the wave (Close wave is the only wave close). The Close spec workflow.
disable-model-invocation: true
---

# Close a change (Wavefoundry skill)

This skill is a thin pointer: the workflow lives in `docs/prompts/close-spec.prompt.md`. Read that document and follow it; do not improvise the steps from this summary.

- To check readiness with `wf_close_spec(wave_id=..., spec_id=..., mode='dry_run')`, run `dry_run` (the default) freely.
- Gate reminder: closure is operator-owned. Call `mode="create"` only when the operator explicitly instructs closing that change in the current request; closure is never inferred from adjacent actions such as "run the review" or "fix the tests".
- The tool permits closure from `ready` and does not verify review evidence; required review must still be completed before closure.
- Run it after Review wave has cleared the change: a completed change cannot be reopened, and the tool records no review evidence.
- Close wave (`wf-close-wave`) remains the only wave close, whatever the change count.
