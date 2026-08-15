# Decision: Gate on backing-doc presence (`requires_doc`), not on repo…

Owner: Engineering
Status: superseded
Last verified: 2026-08-15

Memory ID: `1vdbk-mem decision-gate-on-backing-doc-presence-requires-doc-not-on-re`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-15
Updated: 2026-08-15
Source exploration cost: 42695
Source event: `decision-log:1vbpl-enh wf-package-skill-doc-gated:5e931ebbefbdcba8`
Validation: rewrite
Validated by: agent
Action delta: A future conditional skill (or any repo-scoped rendered surface) gates on the presence of its backing capability doc via Skill.requires_doc, never on a repo-identity signal; the gate path must equal the doc the surface points at.
Validation rationale: The drafted decision is durable and correct but its auto-derived target is wrong: build_pack.py appears only in the rationale prose (as the reason repo-identity detection is impossible, since scripts ship to every target); the shipped mechanism is Skill.requires_doc in render_agent_surfaces.py with two gate consumers (render_skills, _skill_output_destinations) and the gate-equals-pointer test. Verified against the current tree: the field, both consumers, and test_doc_gate_polarity_both_directions plus test_doc_gated_entries_declare_their_backing_doc_as_gate all exist and executed (t1ve3a.log, suite 7241/62 OK).
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1vc5w-mem repo-conditional-skills-gate-on-backing-doc-presence-never-r`
## Summary

Decision (wave 1ve3a): Gate on backing-doc presence (`requires_doc`), not on repo identity.. Rationale: The packaging prompt exists only where packaging applies (seed 100 public-only contract); the gate follows the capability and needs no new repo-detection mechanism..

## Evidence

- `1vbpl-enh wf-package-skill-doc-gated`
- `1ve3a`

## Targets

- `build_pack.py`
