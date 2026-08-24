# Review-plan migration and skill cleanup need exact-line and lexical-symlink controls

Owner: Engineering
Status: active
Last verified: 2026-08-22

Memory ID: `1vyvq-mem review-plan-migration-and-skill-cleanup-need-exact-line-and-`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-08-22
Updated: 2026-08-22
Source exploration cost: 3716673
Source event: `repeated-repairs:1w047:render_agent_surfaces.py`
Validation: promote
Validated by: agent
Action delta: When changing render_agent_surfaces prompt migration or skill cleanup, test exact whole-line recognition with prefixed/suffixed project-owned variants and preflight every lexical skill-root component for symlinks before any delete or generated write.
Validation rationale: Wave 1w047 produced two independent delivery defects in this file: substring replacement rewrote customized project prose, and resolved-path containment followed declared-root/same-root symlinks into unrelated content. Final controls cover 14 embedded-line variants, five symlink polarities, normal idempotence, and the fresh upgrade subprocess. This supplements the existing renderer-baseline memory with migration and deletion-containment safeguards.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

In render_agent_surfaces.py, treat project-owned prompt migration and stale skill cleanup as a single high-risk mutation boundary: accept only exact whole legacy lines while preserving other bytes/line endings, and reject symlinks in every lexical component from each declared skill root through stale and output paths before any mutation.

## Evidence

- `QA-DEL-1`
- `CODE-DEL-1`
- `ReviewPlanPromptMigrationTests`
- `SkillRegistryTests.test_retired_plan_skill_cleanup_is_contained_to_each_declared_host_root`

## Targets

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
