# wf-package skill, gated to repositories that carry the packaging surface

Change ID: `1vbpl-enh wf-package-skill-doc-gated`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-15
Wave: 1ve3a package-skill

## Rationale

Operator direction (2026-08-15): add a `wf-package` skill for the **Package Wavefoundry** maintainer command, but it must exist only in this repository, because packaging applies only to the framework source project.

Wave `1p6lp` deferred maintainer skills because the registry lacked repo-conditional gating. The registry now carries exactly the right mechanism in miniature: `wf-guru` gates on the presence of `docs/agents/guru.md`. Generalizing that boolean (`requires_guru`) into a doc-presence gate (`requires_doc`) yields a `wf-package` that renders only where its backing prompt exists. The premise is grounded in the canonical seeds: seed `100-project-prompt-surface-bootstrap.prompt.md` marks the packaging prompt "**public-only, when present**" ("when `docs/prompts/package-wavefoundry.prompt.md` is seeded"), and the install `lifecycle-prompts/` set does not include it, so target repos never carry the doc. The gate therefore follows the packaging *capability* rather than hardcoding a repo identity, which also does the right thing in the exotic case of a repo that deliberately seeds a packaging surface.

## Requirements

1. **Generalize the registry gate.** Replace `Skill.requires_guru: bool` with `Skill.requires_doc: "str | None" = None` in `render_agent_surfaces.py`. `wf-guru` becomes `requires_doc="docs/agents/guru.md"` with byte-identical emission behavior. `render_skills` and `_skill_output_destinations` gate on the doc's presence; both must stay in exact agreement (the preflight consults the latter).
2. **Register `wf-package`.** New entry gated on `requires_doc="docs/prompts/package-wavefoundry.prompt.md"`:
   - **Description** (single-line, YAML-safe, no `": "`): scoped to building the Wavefoundry framework distribution pack; names Package Wavefoundry; states it is available only where the packaging prompt doc exists (normally the framework source repository).
   - **Thin-pointer body** to `docs/prompts/package-wavefoundry.prompt.md` with three reminders: `build_pack.py` hard-fails without a matching `## [version]` CHANGELOG section, so changelog-first and prefer `--release`; publishing a release is operator-owned and never proceeds without explicit operator instruction in the current session; the ordered verification commands live in `docs/contributing/build-and-verification.md`. No duplicated prompt content.
3. **Catalog rows.** `docs/agents/platform-mapping.md` skills table gains the `wf-package` row with its gate; the AGENTS.md skills paragraph names it with the "framework source repo only" qualifier.
4. **Tests.** Gate polarity in both directions on a temp repo (packaging doc present emits `wf-package`; absent emits nothing, matching target-repo reality); `wf-guru` gating regression unchanged; existing registry invariants (name policy, pairwise-distinct descriptions, YAML-safe descriptions, pointer-target resolution) automatically cover the new entry. Full suite green; docs-lint clean.

## Scope

**Problem statement:** Packaging deserves the same discoverable skill treatment as the lifecycle commands, but it must never render into target repos, and the registry's only conditional gate is guru-specific.

**In scope:**

- The `requires_doc` generalization (Requirement 1).
- The `wf-package` registry entry + body (Requirement 2).
- Catalog rows + tests (Requirements 3 and 4).

**Out of scope:**

- `wf-cleanup-review` and `wf-config-review` (evaluated 2026-08-15 as worthwhile, not yet operator-chosen; a later change can add them as plain ungated entries).
- Any change to `build_pack.py` or the packaging/release flow itself.
- A release-orchestration skill beyond the pointer (release knowledge stays in the prompt doc and memory records).
- Re-opening any `1p6lp` decision (namespace, hosts, thin-pointer contract all carry over unchanged).

## Acceptance Criteria

- [x] AC-1: `Skill.requires_doc` replaces `requires_guru`; `wf-guru` emission behavior is unchanged and still gated on `docs/agents/guru.md`; `render_skills` and `_skill_output_destinations` use the same gate.
- [x] AC-2: `wf-package` is a registry entry gated on `docs/prompts/package-wavefoundry.prompt.md`; it renders on this repository's skill hosts and a test proves a repo without the doc emits no `wf-package` anywhere.
- [x] AC-3: the body is a thin pointer carrying the changelog-first, operator-owned-release, and verification-checklist reminders without restating the prompt's content.
- [x] AC-4: `platform-mapping.md` skills table + AGENTS.md skills paragraph list `wf-package` with its gate.
- [x] AC-5: gate-polarity tests in both directions; full suite green; docs-lint clean.

## Tasks

- [x] Generalize `Skill.requires_doc` + gate checks in `render_agent_surfaces.py`; migrate the `wf-guru` entry.
- [x] Add the `wf-package` entry (description + thin-pointer body).
- [x] Catalog rows (platform-mapping + AGENTS.md).
- [x] Tests (gate polarity both directions; invariants); re-render this repo; full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| registry   | implementer | —          | Goal: `requires_doc` generalization + `wf-package` entry, gates in exact agreement between emitter and preflight |
| surface    | implementer | registry   | Goal: catalogs, re-render, tests, suite + lint green |


## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `docs/agents/platform-mapping.md`
- `AGENTS.md`

## Affected Architecture Docs

`N/A`: extends the wave-`1p6lp` skill registry with one gated entry and a field generalization; no boundary, flow, or verification architecture changes beyond the catalog rows named above.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The gate generalization must not change wf-guru behavior. |
| AC-2 | required  | "This repository only" is the operator's constraint; the negative direction is the property that matters. |
| AC-3 | required  | Thin-pointer contract plus the release-safety reminders. |
| AC-4 | important | Catalog/discoverability. |
| AC-5 | required  | The negative-direction test is the proof the constraint holds in target repos. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-15 | Planned per operator direction ("add wf-package, but it should only exist in this repository"). Gate premise verified code-grounded: seed 100 marks the packaging prompt public-only/when-present, and `install/lifecycle-prompts/` omits it, so target repos never carry `docs/prompts/package-wavefoundry.prompt.md`. | Seed `100-project-prompt-surface-bootstrap.prompt.md:93`; `ls .wavefoundry/framework/install/lifecycle-prompts/` 2026-08-15 |
| 2026-08-15 | Interrogated (batch) before implementation. Six branches walked, all self-answered from the tree: the `requires_doc` gate test is `.is_file()`, matching `guru_available`'s existing check exactly, so wf-guru byte-identity follows from using the same predicate; the emitter/preflight agreement obligation is already pinned in Requirement 1; description wording is implementation freedom bounded by the standing YAML-safety and distinctness tests; standard host-dir gating needs no wf-package nuance; the body's release reminders point only at repo-canonical surfaces (the prompt doc and `build-and-verification.md`), never at session memory; a packaging-doc-present/`build_pack.py`-missing repo cannot meaningfully occur since scripts ship in every pack. Zero open operator questions. | `render_agent_surfaces.py` `guru_available` (`.is_file()` on `docs/agents/guru.md`); `SkillRegistryTests` standing invariants |
| 2026-08-15 | Implemented. `Skill.requires_doc` replaces `requires_guru` (wf-guru entry uses the `GURU_ROLE_REL` constant so the gate shares its single source with `guru_available`); both gate consumers updated identically; `wf-package` registered with the three-reminder thin-pointer body. New tests: `test_doc_gate_polarity_both_directions` (present emits on all hosts, absent emits nowhere while ungated skills still emit) and `test_doc_gated_entries_declare_their_backing_doc_as_gate` (the gate path must equal the doc the body points at, so the skill can never render where its pointer dangles). Re-render: 14 skills on all three hosts here; second render writes an empty manifest. Focused tests 168 OK. | `render_agent_surfaces.py` `Skill`/`SKILL_REGISTRY`/`render_skills`/`_skill_output_destinations`; scratchpad `t1ve3a.log`, `render3.json` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-15 | Gate on backing-doc presence (`requires_doc`), not on repo identity. | The packaging prompt exists only where packaging applies (seed 100 public-only contract); the gate follows the capability and needs no new repo-detection mechanism. | Hardcode a framework-source-repo check (rejected: invents a repo-identity signal the framework does not have; `build_pack.py` ships to every target so script presence cannot distinguish); leave wf-package out (rejected: operator direction). |
| 2026-08-15 | Generalize `requires_guru` to `requires_doc` rather than adding a second boolean. | One mechanism, two users (`wf-guru`, `wf-package`); a parallel boolean per gated skill would not scale and the guru gate is already a doc-presence check in disguise. | `requires_guru` + `requires_package` booleans (rejected: same check duplicated). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Gate generalization silently changes `wf-guru` emission. | AC-1 pins byte-identical behavior; existing guru-gating regression runs unchanged. |
| A target repo seeds a packaging prompt doc and unexpectedly gains `wf-package`. | By design: the skill follows the capability. The description states the scoping so an operator seeing it in such a repo understands why. |
| Description drifts into YAML-unsafe text. | The `": "`/newline registry test from `1p6lw` covers every entry automatically. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
