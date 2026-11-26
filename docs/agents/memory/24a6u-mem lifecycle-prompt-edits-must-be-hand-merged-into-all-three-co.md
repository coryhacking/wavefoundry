# Lifecycle prompt edits must be hand-merged into all three copies

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24a6u-mem lifecycle-prompt-edits-must-be-hand-merged-into-all-three-co`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-11-25
Updated: 2026-11-26
Action delta: Applies when a plan or change edits lifecycle prompt text: list all three copies in the plan and merge the same edit into each, then assert the text in each copy, instead of editing the seed and re-rendering.
Validation rationale: Readiness of wave 24bik caught a plan that edited only seed 240 and re-rendered; MemoryReviewPromptTests shows rendering preserves an existing prompt, and MemoryAdmissionGuidanceTests.CARRIERS lists the three copies.
Checked at: 2026-11-26T06:32:43Z
Check note: Lifecycle baseline rendering distinguishes installed prose from authored copies. Review all three carriers after a prompt change. Reviewed .wavefoundry/framework/scripts/render_agent_surfaces.py:5174.
Check flags: none

## Summary

When changing the text of a lifecycle prompt such as Review memories, edit the seed, the install template under .wavefoundry/framework/install/lifecycle-prompts/ and the self-hosted docs/prompts copy by hand. Rendering only writes a missing prompt, so editing the seed and re-rendering leaves the template that ships to target repositories and the existing docs/prompts copy unchanged.

## Evidence

- `24bik-r-q1-template-copy-omitted`
- `24bik`
- `test_render_agent_surfaces.MemoryReviewPromptTests.test_missing_only_baseline_materializes_and_preserves_existing_prompt`

## Targets

- `.wavefoundry/framework/install/lifecycle-prompts/memory-review.prompt.md`
- `.wavefoundry/framework/seeds/240-memory-review.prompt.md`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
