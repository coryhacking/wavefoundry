# render_agent_surfaces techdocs family: normalize every write-loop failure and re-census the caller carriers

Owner: Engineering
Status: active
Last verified: 2026-08-18

Memory ID: `1vqqy-mem render-agent-surfaces-techdocs-family-normalize-every-write-`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-08-18
Updated: 2026-08-18
Source exploration cost: 3814599
Source event: `repeated-repairs:1vj4e:render_agent_surfaces.py`
Validation: promote
Validated by: agent
Action delta: Before editing render_agent_surfaces.py's techdocs baseline family, normalize every new post-preflight failure into TechdocsWriteFailed inside the write loop and reconcile the caught exception tuple against the sibling helpers' own except clauses (techdocs_member_is_generated already caught UnicodeDecodeError when the loop did not), and carry any change to render_techdocs_baseline's caller set into the module docstring, the wave-1vj4e block comment, the docs/references/install-assets.md consumers cell, and the guard test's name, none of which a green suite checks.
Validation rationale: Auto-derived attribution is false: memory_supply keys targets off literal '<name>.py' tokens in the head evidence record's artifact_or_test_id and public_path, so it counted DEL-1 (whose repair edited docs/index.md and project-overview.md and names render_agent_surfaces.py only as the source of AST line numbers) and missed DEL-2 and DEL-5, whose repair records cite the module in symbol form (render_agent_surfaces.TechdocsWriteFailed, render_agent_surfaces write loop) and so carry no '.py' token; the real repair set is DEL-2, DEL-3 and DEL-5, three repairs not two. Verified in the delivered tree: the write loop catches (RuntimeError, OSError, UnicodeDecodeError) and raises TechdocsWriteFailed, the docstring says 'exactly two callers', the wave-1vj4e block comment names both entries, and the install-assets.md consumers cell reads 'via wf techdocs-baseline or the wf_techdocs_baseline MCP tool'. The generic 'rerun the full suite' delta is worthless here because the suite was green through all three misses.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1vj4e repaired render_agent_surfaces.py three times, all inside the Backstage/TechDocs baseline family. DEL-2 added TechdocsWriteFailed and techdocs_member_states so a post-preflight write failure carries the members already written instead of reporting an empty tree. DEL-5 then found UnicodeDecodeError, a ValueError rather than an OSError, still escaping the same write loop as a raw traceback with no envelope and no cache invalidation, even though the module's own sibling techdocs_member_is_generated had caught (OSError, UnicodeDecodeError) all along. DEL-3 found the module docstring, the wave-1vj4e block comment, and the docs/references/install-assets.md consumers cell all still claiming the CLI was the only caller of render_techdocs_baseline after the wf_techdocs_baseline MCP tool was added in-wave, with the guard test still named test_only_the_thin_entry_calls_the_command_function while its body already asserted two entries. The full suite was green through all three misses, so rerunning it is not the control. Two controls are: every post-preflight failure normalizes into TechdocsWriteFailed inside the write loop, with the caught tuple reconciled against the sibling helpers' own except clauses; and any change to render_techdocs_baseline's caller set is carried into all four prose carriers, because the static caller-allowlist test guards the code boundary and says nothing about the prose that describes it.

## Evidence

- `DEL-2`
- `DEL-3`
- `DEL-5`
- `ev-del-2-3`
- `ev-del-3-3`
- `ev-del-5-3`
- `1vj4e`

## Targets

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `docs/references/install-assets.md`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
