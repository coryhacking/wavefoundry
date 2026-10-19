# Operator-owned Claude skills run only when the operator invokes them

Change ID: `2136l-enh claude-operator-owned-skills-manual-only`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: 2136r agent-guidance-best-practices

## Rationale

The Claude Code best-practices guide recommends `disable-model-invocation: true` on skills "for workflows with side effects that you want to trigger manually". With that key, Claude Code does not offer the skill to the model; only the operator's `/name` runs it.

Four Wavefoundry skills wrap operator-owned steps:
- `wf-close-wave` and `wf-close-change`: close is operator-owned (seed 020:22).
- `wf-package`: builds a distribution.
- `wf-upgrade`: rewrites the framework install.

Today every skill renders the same two-key frontmatter (`render_agent_surfaces.skill_document`, `render_agent_surfaces.py:872-878`), so Claude may load these four on its own judgement.

This is a modest gain, and the limit is stated here:
- The skills are thin pointers to `docs/prompts/*.prompt.md`.
- An agent can still read the prompt and call `wf_close_wave` directly.
- The operator-owned close rule therefore stays a prose rule.

What the change does buy:
- Claude no longer picks these workflows up from an adjacent phrase.
- The four descriptions leave the model's always-loaded skill list.

## Requirements

1. The `Skill` registry entry (`render_agent_surfaces.py:557-574`) gains a field that marks a skill operator-invoked only.
2. The field is set on the registry entries that render as `wf-close-wave`, `wf-close-change`, `wf-package` and `wf-upgrade`. It is a field on the entry, not a match on the rendered name, so a renamed vocabulary profile keeps the flag on its close skills.
3. For the Claude skill host (`.claude/skills/`) only, a marked skill's frontmatter carries `disable-model-invocation: true` after `name` and `description`.
4. Codex (`.codex/skills/`) and `.agents/skills/` frontmatter is unchanged. Nothing establishes how those hosts treat an unknown key.
5. Unmarked skills render byte-identically on every host.
6. `skill_document` (`render_agent_surfaces.py:872-878`) gains a host argument, used by the write loop (about 1503-1513). The declared-skill consumers are unaffected, because they never see framework skills: the ownership compare runs only for `skill.declared` (about 1059), and `has_declared_skill_marker` scans to the closing `---` regardless of key count. The Codex `wf-guru` graft is on an unchanged host. The test helper `_head_document` (`test_declared_extension_skills.py:422-424`) becomes host-aware.
7. A render over an existing `.claude/skills/<name>/SKILL.md` rewrites it to the new bytes, as framework skills already are (plain byte-compare overwrite, about 1542).
8. Behaviour is the same on Windows, macOS, Linux and WSL2. The change is renderer string output, and it uses the existing write path and its platform newline handling.

## Scope

**Problem statement:** Claude can invoke operator-owned workflow skills on its own judgement.

**In scope:**

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`: registry field, host-aware frontmatter, consumers.
- The tests that pin skill bytes:
  - `test_declared_extension_skills.py`: `_head_document`, `test_framework_skills_keep_their_head_bytes`, `StockDeclarationSkillBytesTests`, `DeclaredSkillRenderTests.test_valid_declared_skill_renders_to_every_active_host`;
  - `test_render_agent_surfaces.py`: `SkillRegistryTests`, the self-hosted byte test;
  - `test_vocabulary_prompt_names.py` snapshots, where affected.
- A new test for the Claude-only key and the unchanged Codex and `.agents` bytes.
- The re-rendered `.claude/skills/` for the four skills in this repo.
- The text that describes skill rendering, each gaining one clause naming the manual-only set: the AGENTS.md skills paragraph, seed 050's skills text, and `docs/agents/platform-mapping.md` § Skills (line 47 says "frontmatter `name`/`description`"; seed 050:563-569 requires it to state rendering as on-disk fact), plus the README skills paragraph if it repeats the two-key statement.

**Out of scope:**

- Mechanical enforcement of operator-owned close in `wf_close_wave`.
- Other hosts' manual-invocation equivalents.
- Declared extension skills: their two-key contract stays.

## Acceptance Criteria

- [x] AC-1: A render emits `disable-model-invocation: true` in `.claude/skills/<name>/SKILL.md` for exactly the marked skills, and the test asserts, under the default vocabulary profile, that the marked set equals the literal four names independently of the registry field, so removing a flag cannot make expected and actual both shrink. On a target without `docs/prompts/package-wavefoundry.prompt.md`, `wf-package` is not rendered and the expected set is the other three.
- [x] AC-2: The same render leaves every `.codex/skills/` and `.agents/skills/` document, and every unmarked `.claude/skills/` document, byte-identical to the pre-change render.
- [x] AC-3: Re-rendering over a pre-change `.claude/skills/wf-close-wave/SKILL.md` updates it to the new bytes, and a second render writes nothing.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the registry field and set it on the four skills.
- [x] Make frontmatter host-aware for the Claude host, and update the byte-exact consumers.
- [x] Update the pinned-byte tests, and add the AC-1 to AC-3 tests.
- [x] Re-render this repo's surfaces, and update the AGENTS.md, seed 050, platform-mapping and README skills text.
- [x] Dogfood once after re-render: in a fresh session, "close the wave" with `wf_close_wave(mode="dry_run")` still routes through the `AGENTS.md` shortcut to `close-wave.prompt.md`. Record the result in the Progress Log.
- [x] Run the touched test files, then the whole suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| renderer | implementer | none | Requirements 1 to 7 |

## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_declared_extension_skills.py`, `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`, `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`, `.claude/skills/`

## Affected Architecture Docs

N/A: one renderer output field, with no boundary or flow change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The change itself. |
| AC-2 | required | Other hosts and skills must not move. |
| AC-3 | required | Existing installs must take the update cleanly. |
| AC-4 | required | Skill bytes are heavily pinned. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Planned. Frontmatter is shared and two-key (`skill_document`, 872-878). The host is known only in the write loop (about 1506-1513). `_head_document` pins every framework skill's bytes. | Guru investigation |
| 2026-10-18 | Readiness red-team: the flag lives on the registry entry, not a name match, and AC-1's literal-name check is scoped to the default vocabulary profile. | 2136r readiness red-team primer |
| 2026-10-18 | Readiness code review: `test_valid_declared_skill_renders_to_every_active_host` added to the pinned-byte list. | 2136r readiness review |
| 2026-10-18 | Implemented under `framework_edit_allowed`: `Skill.operator_only` set on the close-wave, close-change, upgrade and package registry entries; `skill_document(skill, skills_dir)` adds `disable-model-invocation: true` only for `.claude/skills`. `_head_document` is host-aware with a literal four-name oracle; new `ManualOnlyClaudeSkillTests` cover AC-1 (with and without the package prompt) and AC-3. Re-render wrote exactly the four Claude skill files. AGENTS.md skills paragraph, seed 050 and `platform-mapping.md` gained the clause; README does not repeat the two-key statement, so it is unchanged. Dogfood: a fresh `claude -p` session in this repo (Read only) routed "close the wave" through the AGENTS.md shortcut to `docs/prompts/close-wave.prompt.md`, chose `wf_close_wave(mode="dry_run")` first, and listed none of the four skills as invocable. QA scratch mutants (flag dropped from one entry; key on every host) both failed the named tests. | scratchpad dogfood-2136l.out; test_declared_extension_skills 60 OK; delivery code and qa reviews |
| 2026-10-18 | Whole suite `--no-cache` after settled inputs: 11907 tests OK, fresh green receipt. Two earlier runs had no test failures but tripped the repository-change guard on concurrent edits (CHANGELOG, gardener stamps, and another session writing wave 2124l). | scratchpad suite-2136r-3.txt |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | -------- |
| 2026-10-18 | Emit the key only for the Claude host. | It is a Claude Code key; Codex and `.agents` behaviour for unknown keys is unverified. | All hosts; risks breaking a strict frontmatter parser. |
| 2026-10-18 | Mark four skills. | These are the ones with operator-owned side effects. | Also `wf-implement-wave` and `wf-prepare-wave`; those are routine agent steps the operator expects Claude to drive. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The operator says "close the wave" and Claude can no longer load the skill. | The `AGENTS.md` shortcut table routes to `docs/prompts/close-wave.prompt.md` directly. The skill was only a pointer to it. |
| Claude Code blocks a model attempt to invoke the skill and tells it not to reproduce the steps another way, which might deter the prompt-doc route. | The description is no longer in context, so the model routes by the `AGENTS.md` shortcut; the dogfood task checks this. Inferred from the Claude Code skills docs, not yet tested. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
