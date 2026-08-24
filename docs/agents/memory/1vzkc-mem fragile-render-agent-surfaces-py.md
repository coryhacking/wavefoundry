# Fragile: render_agent_surfaces.py

Owner: Engineering
Status: superseded
Last verified: 2026-08-22

Memory ID: `1vzkc-mem fragile-render-agent-surfaces-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-08-22
Updated: 2026-08-22
Source exploration cost: 3716673
Source event: `repeated-repairs:1w047:render_agent_surfaces.py`
Validation: rewrite
Validated by: agent
Action delta: When changing render_agent_surfaces prompt migration or skill cleanup, test exact whole-line recognition with prefixed/suffixed project-owned variants and preflight every lexical skill-root component for symlinks before any delete or generated write.
Validation rationale: Wave 1w047 produced two independent delivery defects in this file: substring replacement rewrote customized project prose, and resolved-path containment followed declared-root/same-root symlinks into unrelated content. Final controls cover 14 embedded-line variants, five symlink polarities, normal idempotence, and the fresh upgrade subprocess. This supplements the existing renderer-baseline memory with migration and deletion-containment safeguards.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1vyvq-mem review-plan-migration-and-skill-cleanup-need-exact-line-and-`
## Summary

render_agent_surfaces.py required 2 separate repairs during wave 1w047; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `PREP-MIGRATED-PROMPT-SEMANTICS-005`
- `CODE-DEL-1`
- `1w047`

## Targets

- `render_agent_surfaces.py`
