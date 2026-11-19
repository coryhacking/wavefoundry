---
name: wf-plan-spec
description: Plan a change of any kind (feature, bug fix, enhancement, refactor, documentation, tech debt, task, maintenance, operations) and produce a consolidated spec ready for wave admission. The Plan spec workflow.
---

# Plan a change (Wavefoundry skill)

This skill is a thin pointer: the workflow lives in `docs/prompts/plan-spec.prompt.md`. Read that document and follow it; do not improvise the steps from this summary.

- The workflow selects the scaffold among the `wf_new_<kind>` MCP creation tools (bug, enhancement, refactor, documentation, tech debt, task, maintenance, operations, change) by change kind, then admits the doc with `wf_add_change`.
- Gate reminder: planning writes docs only; no repository code edits until the stage gate (spec, wave admission, recorded readiness) is satisfied.
