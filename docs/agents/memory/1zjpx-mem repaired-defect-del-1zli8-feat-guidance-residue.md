# Repaired defect DEL-1ZLI8-FEAT-GUIDANCE-RESIDUE

Owner: Engineering
Status: superseded
Last verified: 2026-10-02

Memory ID: `1zjpx-mem repaired-defect-del-1zli8-feat-guidance-residue`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-02
Updated: 2026-10-02
Source exploration cost: 68521
Source event: `finding:1zli8:DEL-1ZLI8-FEAT-GUIDANCE-RESIDUE`
Validation: rewrite
Validated by: agent
Action delta: When retiring or renaming a change kind or tool, census the skill registry in render_agent_surfaces.py and both Plan feature prompts, which are not rendered from seed 170 and need direct edits.
Validation rationale: The finding showed the shipped wf-plan-feature skill and change_doc_response's error message still offered the retired kind after the planned census; the generated summary carries no actionable content.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1zlgh-mem kind-and-tool-censuses-must-include-skills-and-hand-edited-p`

## Summary

Real defect fixed in wave 1zli8: Repair verified.

## Evidence

- `DEL-1ZLI8-FEAT-GUIDANCE-RESIDUE`
- `ev-del-1zli8-feat-guidance-residue-3`
- `1zli8`

## Targets

- `tests/test_retired_change_kinds.py`
