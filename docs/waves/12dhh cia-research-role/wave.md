# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-05

wave-id: `12dhh cia-research-role`
Title: CIA Research and Documentation Role

## Objective

Expand the CIA's research and documentation role, and add doc orientation guidance for the CIA.

## Changes

Change ID: `12dhh-enh cia-research-role`
Change Status: `implemented`

Change ID: `12dhh-enh cia-role-doc-orientation`
Change Status: `implemented`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| docs-contract-reviewer | review | 12dhh — CIA prompt behavioral changes, journal creation, write-carve-out accuracy, anti-assumption rule completeness |
| qa-reviewer | review | 12dhh — AC coverage, seed-211 fidelity |
| docs-contract-reviewer | review | 12dhh-enh cia-role-doc-orientation — CIA orientation section content accuracy and role-specificity |
| qa-reviewer | review | 12dhh-enh cia-role-doc-orientation — AC coverage, existing content preservation |

Completed At: 2026-05-05

## Wave Summary

Expands the Code Insight Agent from a pure retrieval tool to a research-and-document role. The CIA may now ask the operator clarifying questions, must validate every claim in code or explicitly flag it as pattern-inferred, maintains its own journal for durable discoveries, and is permitted to write to `docs/architecture/` and `docs/specs/` when it makes findings worth preserving. Wave/code write-paths remain prohibited.

## Review Signoff Evidence

### 12dhh-enh cia-role-doc-orientation

- docs-contract-reviewer: approved — all 5 CIA Orientation sections present at correct positions; each section carries role-specific tool selections meaningfully differentiated across planner, prepare, single-change implementer, wave-coordinator, and reviewer roles; MCP fallback instructions present in every section; all pre-existing content preserved unchanged.
- qa-reviewer: approved — all 7 ACs pass: CIA Orientation sections verified in all 5 role docs at correct insertion points; tools are role-specific and workflow-anchored; MCP fallback present in each section with grep commands and cite-as-path:line_number instruction in review-wave; all pre-existing sections verbatim-intact across all 5 files.

### 12dhh-enh cia-research-role

- qa-reviewer: approved — all 11 ACs verified: Purpose reframed with senior-engineer framing and 5 numbered activities, Assumption Discipline (3 tiers + judgment-based confidence model), Operator Q&A (3 trigger conditions + exhaust-index guard), Edge Case Detection (8 categories + named output section), External Lookup (framework/spec/library scope + citation format), Discovery Documentation (timing: after answering; all 3 write surfaces named), Write Permissions table accurate (journal + docs/architecture/ + docs/specs/), AC-7b completeness-by-default stated in Purpose, seed-211 byte-identical to source, CIA journal created with all required sections, seed-050 journal bootstrap present at line 296, 902 tests pass.
- docs-contract-reviewer: approved — seed-211 byte-identical to source prompt (diff empty); Write Permissions table lists exactly 3 permitted paths with all other paths explicitly prohibited; Assumption Discipline tiers non-overlapping (code-validated/pattern-inferred/unresolvable); confidence model judgment-based not count-based; Operator Q&A gates on index exhaustion with one-question-at-a-time constraint; External Lookup citation format includes URL and retrieval date; seed-050 CIA journal bootstrap rule at line 296 is contract-complete (names all 8 journal sections, ties content to CIA operating identity from seed-211); CIA journal follows role journal pattern with Index Gaps extension; Discovery Documentation timing unambiguous (after answering).

## Journal Watchpoints

- **Watch: gate hygiene** — `12dhh-enh cia-research-role` requires `seed_edit_allowed`; `12dhh-enh cia-role-doc-orientation` requires `framework_edit_allowed`. Do not run both guard windows concurrently; restore each gate immediately after its change completes.
- **Watch: role doc edits do not block seed edits** — the two changes share no files. `12dhh-enh cia-role-doc-orientation` edits `docs/prompts/agents/` role docs only; `12dhh-enh cia-research-role` edits seeds and the CIA source prompt. Either can run first with no ordering constraint.
- **Follow-up: after closure, verify new project installs include CIA orientation** — the seed-050 change in `12dhh-enh cia-research-role` seeds CIA orientation into new role docs at install time. Confirm at next install smoke-test that the CIA orientation sections match the role-doc patterns introduced in `12dhh-enh cia-role-doc-orientation`.

## Dependencies

- Depends on: wave `12d4b codebase-qa` (closed) — CIA foundation
