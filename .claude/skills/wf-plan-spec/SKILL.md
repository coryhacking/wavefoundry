---
name: wf-plan-spec
description: Plan a change of any kind (feature, bug fix, enhancement, refactor, documentation, tech debt, task, maintenance, operations) and produce a consolidated spec ready for wave admission. The Plan spec workflow.
---

# Plan a change (Wavefoundry skill)

This skill is a thin pointer: the workflow lives in `docs/prompts/plan-spec.prompt.md`. Read that document and follow it; do not improvise the steps from this summary.

- Select a kind-specific scaffold such as `wf_new_bug` or `wf_new_enhancement`, or use `wf_new_spec(slug=...)` for the generic scaffold (stored kind `change`). Pass the returned `data.spec_id` to retrieve the spec with `wf_get_spec(spec_id=...)` and admit it with `wf_add_spec(wave_id=..., spec_id=..., mode='create')`.
- Gate reminder: planning writes docs only; no repository code edits until the stage gate (spec, wave admission, recorded readiness) is satisfied.
