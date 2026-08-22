# Fragile: render_agent_surfaces.py

Owner: Engineering
Status: superseded
Last verified: 2026-08-18

Memory ID: `1vq30-mem fragile-render-agent-surfaces-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-08-18
Updated: 2026-08-18
Source exploration cost: 3814599
Source event: `repeated-repairs:1vj4e:render_agent_surfaces.py`
Validation: rewrite
Validated by: agent
Action delta: Before editing render_agent_surfaces.py's techdocs baseline family, normalize every new post-preflight failure into TechdocsWriteFailed inside the write loop and reconcile the caught exception tuple against the sibling helpers' own except clauses (techdocs_member_is_generated already caught UnicodeDecodeError when the loop did not), and carry any change to render_techdocs_baseline's caller set into the module docstring, the wave-1vj4e block comment, the docs/references/install-assets.md consumers cell, and the guard test's name, none of which a green suite checks.
Validation rationale: Auto-derived attribution is false: memory_supply keys targets off literal '<name>.py' tokens in the head evidence record's artifact_or_test_id and public_path, so it counted DEL-1 (whose repair edited docs/index.md and project-overview.md and names render_agent_surfaces.py only as the source of AST line numbers) and missed DEL-2 and DEL-5, whose repair records cite the module in symbol form (render_agent_surfaces.TechdocsWriteFailed, render_agent_surfaces write loop) and so carry no '.py' token; the real repair set is DEL-2, DEL-3 and DEL-5, three repairs not two. Verified in the delivered tree: the write loop catches (RuntimeError, OSError, UnicodeDecodeError) and raises TechdocsWriteFailed, the docstring says 'exactly two callers', the wave-1vj4e block comment names both entries, and the install-assets.md consumers cell reads 'via wf techdocs-baseline or the wf_techdocs_baseline MCP tool'. The generic 'rerun the full suite' delta is worthless here because the suite was green through all three misses.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1vqqy-mem render-agent-surfaces-techdocs-family-normalize-every-write-`
## Summary

render_agent_surfaces.py required 2 separate repairs during wave 1vj4e; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `DEL-1`
- `DEL-3`
- `1vj4e`

## Targets

- `render_agent_surfaces.py`
