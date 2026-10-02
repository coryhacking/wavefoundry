# Kind and tool censuses must include skills and hand-edited prompts

Owner: Engineering
Status: active
Last verified: 2026-10-02

Memory ID: `1zlgh-mem kind-and-tool-censuses-must-include-skills-and-hand-edited-p`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-10-02
Updated: 2026-10-02
Source exploration cost: 68521
Source event: `finding:1zli8:DEL-1ZLI8-FEAT-GUIDANCE-RESIDUE`
Validation: promote
Validated by: agent
Action delta: When retiring or renaming a change kind or tool, census the skill registry in render_agent_surfaces.py and both Plan feature prompts, which are not rendered from seed 170 and need direct edits.
Validation rationale: The finding showed the shipped wf-plan-feature skill and change_doc_response's error message still offered the retired kind after the planned census; the generated summary carries no actionable content.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1zli8: retiring the feat kind missed the shipped wf-plan-feature skill body in render_agent_surfaces.SKILL_REGISTRY (rendered into .claude, .codex and .agents skills) and the kind list in change_doc_response's invalid_arguments message. The Plan feature prompts under docs/prompts are not rendered from seed 170 and need direct edits. SkillGuidanceTests now pins the skill's scaffold list.

## Evidence

- `DEL-1ZLI8-FEAT-GUIDANCE-RESIDUE`
- `1zli8`

## Targets

- `render_agent_surfaces.py`
- `tests/test_retired_change_kinds.py`
