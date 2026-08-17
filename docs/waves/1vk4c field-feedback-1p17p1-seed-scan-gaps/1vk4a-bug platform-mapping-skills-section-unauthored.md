# Seed-100 Points at a platform-mapping Skills Section No Seed Authors

Change ID: `1vk4a-bug platform-mapping-skills-section-unauthored`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-08-16
Wave: 1vk4c field-feedback-1p17p1-seed-scan-gaps

## Rationale

Wave `1p6lp` (skills, 1.17.0) added a public-surface requirement to seed-100 (`100-project-prompt-surface-bootstrap`, item "index.md — Skills usage note"): every target repository's `docs/prompts/index.md` must carry a Usage Notes bullet about the `wf-` skill family and "point at `docs/agents/platform-mapping.md` § Skills for rendering and gating detail". Nothing authors that section. `platform-mapping.md` is project-owned prose whose content is specified by seed-050 (`050-agent-entry-surface-bootstrap`, "`docs/agents/platform-mapping.md` — Availability Matrix"), and that section says nothing about skills; no renderer touches the file (`code_keyword` over `.wavefoundry/framework/scripts/*.py`: the only `platform-mapping.md` hits are role-doc exemption lists). In this repository the section exists because it was hand-written during `1p6lp`; every consumer either ships a dangling pointer or relies on the upgrading agent inferring the section. The first field upgrade to 1.17.1 (2026-08-16, a local project) hit exactly that: the agent had to invent the section from the rendered skill directories.

## Requirements

1. Seed-050's `platform-mapping.md` guidance specifies a **Skills** subsection (any heading level, heading text beginning with `Skills`, placed after the availability matrix), written the same way as the matrix (a record of on-disk fact, written after the `render_agent_surfaces` pass of seed-050 task 20 has produced the skill directories) and present whenever a skill host ROOT exists (`.claude/`, `.codex/`, or `.agents/`, the same activation predicate seed-100 and `render_skills` use): the active host skill directories, the skills actually rendered in this repository (listed from disk at write time, never copied from the seed, and re-verified against disk on every upgrade by the seed-160 checklist bullet), and the gating rules: skills render on `wf setup` and **Upgrade Wavefoundry**; a `requires_doc`-gated skill renders only where its backing doc exists (`wf-guru` on `docs/agents/guru.md`; `wf-package` and `wf-code-cleanup` on their prompt docs); skill rendering is independent of `enabled_agent_roles`, which gates agent-role wrappers, not skills; bodies are thin pointers to the backing `docs/prompts/*.prompt.md`.
2. Seed-160's post-upgrade checklist (the block that already checks `platform-mapping.md` for auto-Guru routing and hook coverage) checks, on every upgrade, that `platform-mapping.md` carries the Skills subsection whenever a skill host root exists and that its listed set matches the rendered directories on disk, so consumers converge on the next upgrade and registry growth cannot leave the section stale.
3. Seed-100's pointer and the section name agree: seed-100 says "§ Skills"; seed-050 names the subsection so that phrase resolves (a heading whose text begins with `Skills`).
4. The self-hosted rendered surface `docs/prompts/upgrade-wavefoundry.prompt.md` does not carry seed-160's post-upgrade checklist (verified at readiness: its only platform-mapping mention is the "Verify paths listed in `docs/agents/platform-mapping.md` § Auto-Guru routing" item in its agent-surfaces checklist); add one sibling item there ("Verify `platform-mapping.md` § Skills lists the rendered skill set when a skill host root exists") so the project-local surface agrees with the seed. This repository's `docs/agents/platform-mapping.md` already satisfies requirement 1 (its `### Skills (wf- namespace, registry-rendered)` subsection) and is only touched if the heading form must change.
5. No renderer or code change: the section stays agent-authored prose like the rest of `platform-mapping.md`. Seed edits go through the `seed_edit_allowed` gate.

## Scope

**Problem statement:** the framework tells consumers to point at a documentation section that no seed tells anyone to write.

**In scope:**

- Seed-050 Skills subsection specification (content, write timing, fact-not-intent rule).
- Seed-160 checklist bullet.
- Self-hosted `docs/prompts/upgrade-wavefoundry.prompt.md` mirror.
- docs-lint and the full framework suite (seed-content censuses).

**Out of scope:**

- Rendering the section from a registry (a marker region in `platform-mapping.md`). Skills are already listed by the renderer's registry; a rendered region would be the durable convergence path but is a renderer change with marker-ownership tests, disproportionate for a paragraph of prose. Revisit if the hand-authored section drifts across consumers.
- Changing seed-100's wording beyond the pointer agreement in requirement 3.
- A docs-lint rule that validates the pointer.

## Acceptance Criteria

- [x] AC-1: Seed-050's platform-mapping guidance contains a Skills subsection specification covering the activation predicate (host root exists), active host skill directories, the on-disk rendered set (list from disk, not from the seed), and the three gating rules (setup/upgrade render; `requires_doc` doc-gating naming `wf-guru`, `wf-package`, `wf-code-cleanup`; independence from `enabled_agent_roles`), written after the `render_agent_surfaces` pass has produced the skill directories.
- [x] AC-2: Seed-160's post-upgrade checklist contains a bullet requiring the Skills subsection when a skill host root exists and re-verifying its listed set against disk, and `docs/prompts/upgrade-wavefoundry.prompt.md` gains the sibling verify item next to its Auto-Guru routing item.
- [x] AC-3: Seed-100's "§ Skills" pointer resolves against the subsection seed-050 specifies (any heading level, text beginning with `Skills`, after the matrix); the three seeds use one name and one activation predicate (host root exists).
- [x] AC-4: docs-lint clean; the full framework suite passes (seed-content censuses and residue tests included).
- [x] AC-5: This repository's `docs/agents/platform-mapping.md` satisfies AC-1's specification as written (verified against disk: 14 skill directories in each of `.claude/skills/`, `.codex/skills/`, `.agents/skills/`: 12 universal plus `wf-package` and `wf-code-cleanup`, present here because their backing prompts exist), with no edit or only a heading-form edit.

## Tasks

- [x] Open `seed_edit_allowed`; add the Skills subsection specification to seed-050's platform-mapping section; close the gate.
- [x] Add the seed-160 checklist bullet (same gate window); add the sibling verify item in `docs/prompts/upgrade-wavefoundry.prompt.md` (project-local surface, hand-edited).
- [x] Confirm seed-100's pointer text matches the specified heading; adjust wording only if the names differ.
- [x] Verify this repository's `platform-mapping.md` § Skills against the specification and the rendered directories.
- [x] docs-lint; full suite; record results.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Seed edits (050, 160) | implementer | — | Under `seed_edit_allowed`; prose only. |
| Self-hosted mirror + local verification | implementer | Seed edits | `docs/prompts/upgrade-wavefoundry.prompt.md`; this repo's `platform-mapping.md`. |
| Verification | qa-reviewer | All | docs-lint + full suite; three-seed name agreement. |

## Serialization Points

- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/agents/platform-mapping.md`

## Affected Architecture Docs

N/A: prose specification in three seeds and one rendered prompt surface; no boundary, flow, or verification-architecture impact.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The missing specification is the defect. |
| AC-2 | required | Without the checklist bullet, existing consumers never converge. |
| AC-3 | important | Name agreement is what makes the pointer resolve. |
| AC-4 | required | Seed edits ship to every consumer; the suite carries seed censuses. |
| AC-5 | important | Self-hosting proof that the specification matches a real rendered set. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-16 | Planned from the first 1.17.1 field upgrade (local project): the upgrading agent found seed-100's new requirement, found both doc surfaces absent, and authored them by inference. Verified against the tree: seed-100 line "index.md — Skills usage note" carries the pointer; seed-050's platform-mapping section has no skills content; no script writes `platform-mapping.md`; this repo's section exists at `### Skills (wf- namespace, registry-rendered)` and was hand-written in `1p6lp`. | `code_keyword` census; seed-050 "Availability Matrix" section; operator field report 2026-08-16 |
| 2026-08-16 | Readiness council corrections: activation predicate pinned to host ROOT exists (as seed-100 and `render_skills`); heading contract pinned (any level, text begins with `Skills`, after the matrix); doc-gated set names `wf-guru` too (`render_agent_surfaces.py` `requires_doc` at the guru, package, and cleanup entries); AC-5 count corrected to 14 per host incl. `.agents/skills/`; the rendered upgrade prompt does not carry seed-160's checklist, so requirement 4 now adds one sibling verify item instead of a mirror; seed-160's bullet re-verifies the listed set against disk on every upgrade so registry growth cannot strand the prose. | council seat returns 2026-08-16; `ls .claude/skills .codex/skills .agents/skills` |
| 2026-08-16 | Implemented under `seed_edit_allowed`: seed-050's platform-mapping section gained the "Skills subsection (wave 1vk4c)" specification (activation predicate = host root exists; host skill directories; rendered set listed from disk, never from a seed; gating rules incl. `wf-guru`/`wf-package`/`wf-code-cleanup` doc-gating and independence from `enabled_agent_roles`; written after the task-20 render pass; re-verified on upgrade); seed-160's post-upgrade checklist gained the Skills bullet next to the auto-Guru routing bullet (add or refresh from disk when missing or stale, never from the seed's example list); the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` gained the sibling verify item next to its Auto-Guru routing item; seed-100's "§ Skills" pointer needed no change (this repo's `### Skills (...)` heading resolves under the any-level, begins-with-`Skills` contract). AC-5: this repo's section listed 14 skill directories per host and the doc-gated set correctly, but lacked two of the specified gating rules (render on setup/upgrade; independence from `enabled_agent_roles`), so one sentence was added rather than the planned no-edit; noted here as the deviation. docs-lint ok. | seeds 050/160 diff; `docs/prompts/upgrade-wavefoundry.prompt.md`; `docs/agents/platform-mapping.md` § Skills; `ls .claude/skills .codex/skills .agents/skills` (14 each) |
| 2026-08-16 | Full framework suite after implementation: 7267 tests across 63 files OK (`suite-1vk4c.log`, AC-4 evidence). Delivery review: docs-contract lane verified every seed-050 statement against `render_agent_surfaces.py` (SKILL_HOSTS root `is_dir` activation; the three `requires_doc` entries; `render_skills` inside the pass task 20 runs; no `enabled_agent_roles` dependency); its low finding on the placement clause (this repo keeps the section under auto-Guru routing, not after the role tables) repaired by relaxing seed-050 to anywhere after the header block; `platform-mapping.md` restamped 2026-08-16. | docs-contract lane return; seed-050 diff |
| 2026-08-16 | Post-repair full framework suite (after the delivery hardening): 7267 tests across 63 files OK (`suite-1vk4c-2.log`); reverifier and delivery council APPROVE. | `suite-1vk4c-2.log`; reverify-1vk4c return |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-16 | Keep the section agent-authored and specify it in seed-050 (plus a seed-160 checklist bullet) rather than rendering it. | Matches how the rest of `platform-mapping.md` is produced (fact recorded after render); a paragraph of prose does not justify a new renderer-owned marker region with ownership tests; the seed-diff editing pass on upgrade already converges consumers when seed-050 changes. | Rendered marker region (deferred: durable but disproportionate now); drop the pointer from seed-100 (rejected: loses the one consumer-facing place that explains skill gating, and this repo's `AGENTS.md` already links it). |

## Risks

| Risk | Mitigation |
| --- | --- |
| Agents copy the seed's skill list instead of listing from disk, so doc-gated skills get claimed where absent. | The specification says list from disk and names the doc-gated pair as the example of what NOT to claim universally, mirroring seed-100. |
| Seed edits trip a seed-content census or residue test. | Full suite before review. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
