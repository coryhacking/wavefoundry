# Kind and tool censuses must include rendered skills and server messages

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bvy-mem kind-and-tool-censuses-must-include-rendered-skills-and-serv`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 68521
Supersedes: `1zlgh-mem kind-and-tool-censuses-must-include-skills-and-hand-edited-p`
Checked at: 2026-11-26T06:32:44Z
Check note: Retiring a kind or tool name affects rendered skills and served registration. A code-only census misses those consumers. Reviewed .wavefoundry/framework/scripts/wf_server/server_impl.py:1113.
Check flags: none

## Summary

When retiring or renaming a change kind or an MCP tool, census the skill bodies in render_agent_surfaces.SKILL_REGISTRY (.wavefoundry/framework/scripts/render_agent_surfaces.py, rendered into .claude, .codex and .agents skills) and the kind lists in server error messages such as change_doc_response, not only seed-rendered prompts. Why: wave 1zli8 retired feat and missed the shipped plan skill body and change_doc_response's invalid_arguments message (DEL-1ZLI8-FEAT-GUIDANCE-RESIDUE); tests/test_retired_change_kinds.py SkillGuidanceTests pins only the plan skill, so other skills and messages are unguarded.

## Evidence

- `DEL-1ZLI8-FEAT-GUIDANCE-RESIDUE`
- `1zli8`
- `test_retired_change_kinds.SkillGuidanceTests.test_the_plan_change_skill_lists_no_retired_scaffold`

## Targets

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_retired_change_kinds.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
