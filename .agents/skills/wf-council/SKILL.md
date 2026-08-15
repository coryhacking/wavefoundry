---
name: wf-council
description: Convene an on-demand review on one artifact, choosing among the role-based Wave Council, the stance-based Archetype Council, and standalone Red-team review. Not the open wave's required lanes (Review wave) and not a change-doc stress test (Interrogate this plan).
---

# Convene a review council (Wavefoundry skill)

This skill is a router: pick the review form that fits the artifact, then read and follow that form's prompt doc. The full chooser table lives in `docs/prompts/archetype-council.prompt.md`.

- Code, architecture, or trust-boundary artifact: **Council review**, `docs/prompts/council-review.prompt.md`.
- Prose, naming, AC formulation, or decision narrative: **Archetype review**, `docs/prompts/archetype-council.prompt.md`.
- One sharp adversarial challenge on a single artifact: **Red-team review**, `docs/prompts/red-team-review.prompt.md`.
- These on-demand reviews record no lifecycle signoffs and satisfy no gate; when a prompt directs recording against a wave, use the `wf_review_event` MCP tool.
- Boundary: the open wave's REQUIRED review lanes run under Review wave (`wf_review_wave`), and a change doc heading for admission gets Interrogate this plan; this router is for on-demand reviews outside both.
