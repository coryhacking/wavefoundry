# Repo-conditional skills gate on backing-doc presence, never repo identity

Owner: Engineering
Status: active
Last verified: 2026-08-15

Memory ID: `1vc5w-mem repo-conditional-skills-gate-on-backing-doc-presence-never-r`
Kind: `decision`
Confidence: 0.9
Created: 2026-08-15
Updated: 2026-08-15
Source exploration cost: 42695
Source event: `decision-log:1vbpl-enh wf-package-skill-doc-gated:5e931ebbefbdcba8`
Validation: promote
Validated by: agent
Action delta: A future conditional skill (or any repo-scoped rendered surface) gates on the presence of its backing capability doc via Skill.requires_doc, never on a repo-identity signal; the gate path must equal the doc the surface points at.
Validation rationale: The drafted decision is durable and correct but its auto-derived target is wrong: build_pack.py appears only in the rationale prose (as the reason repo-identity detection is impossible, since scripts ship to every target); the shipped mechanism is Skill.requires_doc in render_agent_surfaces.py with two gate consumers (render_skills, _skill_output_destinations) and the gate-equals-pointer test. Verified against the current tree: the field, both consumers, and test_doc_gate_polarity_both_directions plus test_doc_gated_entries_declare_their_backing_doc_as_gate all exist and executed (t1ve3a.log, suite 7241/62 OK).
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1ve3a: Skill.requires_doc (render_agent_surfaces.py) generalizes the wf-guru gate so a skill emits only where its backing capability doc exists. Chosen over a framework-source-repo identity check because the framework has no such signal (build_pack.py ships to every target, so script presence cannot distinguish repos) and the capability doc is the honest scoping: wf-package gates on the packaging prompt (seed 100 public-only/when-present), wf-code-cleanup on the cleanup prompt. The gate path must equal the doc the skill body points at, pinned by test_doc_gated_entries_declare_their_backing_doc_as_gate, so a gated skill can never render where its pointer dangles; test_doc_gate_polarity_both_directions proves both directions.

## Evidence

- `1vbpl-enh wf-package-skill-doc-gated`
- `1ve3a`
- `test_doc_gate_polarity_both_directions`
- `test_doc_gated_entries_declare_their_backing_doc_as_gate`

## Targets

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
