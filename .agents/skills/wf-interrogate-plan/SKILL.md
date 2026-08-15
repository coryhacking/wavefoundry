---
name: wf-interrogate-plan
description: Stress-test a change doc before wave admission by walking every unresolved decision branch one question at a time. The Interrogate this plan workflow.
---

# Interrogate a plan (Wavefoundry skill)

This skill is a thin pointer: the workflow lives in `docs/prompts/interrogate-plan.prompt.md`. Read that document and follow it; do not improvise the steps from this summary.

- Load the change doc with the `wf_get_change` MCP tool; the interrogation itself is prompt-driven.
- Self-answer from project resources first; surface only the questions that genuinely need operator judgment.
