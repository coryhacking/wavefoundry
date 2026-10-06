# A Distribution Cannot Declare Its Own Skills

Change ID: `1zv89-enh declared-extension-skills`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zv8c waveforge-seams-and-lock-links

## Rationale

Downstream request (Waveforge R3): tools have a declaration seam in `mcp_tool_extensions.py`, but skills do not. `render_agent_surfaces.SKILL_REGISTRY` is a literal tuple and `render_skills` renders only that tuple, so a distribution that ships its own prompt docs cannot give them a `SKILL.md` on any skill host without editing the framework's renderer, which conflicts on every merge.

## Requirements

1. `mcp_tool_extensions.py` gains `EXTENSION_SKILLS: Mapping[str, Mapping[str, object]] = {}` (shipped empty, a plain literal). Each key is a skill name; each value has exactly `title`, `description`, `prompt_doc` and `summary` (a list or tuple of strings). It is added to the test support's `SHIPPED_DECLARATION` (and the full-set assertion in `test_profile_support`). It is a renderer-only declaration: it is NOT part of `declared()`, `declaration_problems` or `validate_declaration`, so a bad skill entry can never stop the MCP server, the tool roster or the allowlist render.
2. `mcp_tool_extensions.skill_declaration_problems(skills=None)` (stdlib-only; reads `EXTENSION_SKILLS` at call time when no argument) returns one message per problem, naming the skill and key:
   - the value is a dict with exactly the four keys;
   - the name matches `^[a-z0-9]+(?:-[a-z0-9]+)*$`, is at most 64 characters, does not start with `wf-` (every framework skill name does, so this also prevents a collision with `SKILL_REGISTRY`), does not contain `claude` or `anthropic`, and its rendered path is not one of `render_agent_surfaces.STALE_SKILL_PATHS` (checked by the renderer, which owns that list);
   - `title` and `description` are non-empty, single-line (no CR, LF, tab, other C0/C1 control, U+0085, U+2028 or U+2029), without surrounding spaces; `description` is at most 1024 characters; neither contains `: ` or ` #`, ends with `:`, starts with a YAML indicator character (`-?:,[]{}#&*!|>'"%@` or a backtick), or is a YAML special scalar (`true`, `false`, `yes`, `no`, `on`, `off`, `null`, `~`, case-insensitive) or a number;
   - `prompt_doc` is a repo-relative POSIX path under `docs/prompts/` ending in `.prompt.md`, with no `..`, backslash, drive, colon or absolute form;
   - `summary` is a list or tuple of 1 to 8 strings, each following the `title` rules except the YAML-scalar rules.
3. The renderer reads the declaration at call time (`getattr(mcp_tool_extensions, "EXTENSION_SKILLS", {})`, never a `from`-import, so the test base declaration and the upgrade old-code window see the current module). Validation runs in `_skill_output_destinations`, which `preflight_agent_surface_paths` calls before the first write of any render (including `render_platform_surfaces`), so an invalid declaration refuses the whole render with every problem named and nothing written. `render_skills` re-checks before its own writes.
4. Every reader of the registry in `render_agent_surfaces.py` (`_skill_output_destinations`, `render_skills`, and the other loops over `SKILL_REGISTRY`) iterates the framework registry followed by the declared skills. A declared skill renders through `_thin_pointer_body(title, prompt_doc, summary, label="skill")` (the framework's skills keep "Wavefoundry skill"), gated on its `prompt_doc` existing, through the same symlink and host-root checks. The framework registry's name policy is unchanged. Declared skill folders are distribution-owned: `is_framework_maintenance_surface` stays limited to `*/skills/wf-*`.
5. `wf_server_info` lists the declared skill names under `extensions.skills`, with `skill_problems` when `skill_declaration_problems()` is non-empty (reported, never fatal).
6. `docs/specs/mcp-tool-surface.md`, `docs/architecture/current-state.md`, `docs/architecture/layering-rules.md` (the new import edge) and the module docstring describe the constant, each stating that `EXTENSION_SKILLS` is read only by the renderer and is never fatal to the server. CHANGELOG gets one Added bullet under `## [1.29.0]`.

## Scope

**Problem statement:** a distribution cannot add skills without editing the framework renderer.

**In scope:**

- The declaration, its validation, the renderer and destination list, the server info listing, docs, CHANGELOG, tests.

**Out of scope:**

- Removing the rendered file of a skill a distribution stops declaring (a stale `SKILL.md` stays until removed by hand; recorded as a follow-up).
- Skill bodies other than the thin pointer.
- Protecting an operator-authored skill folder that a distribution later declares by the same name (the distribution chooses its names).

## Acceptance Criteria

- [x] AC-1: With one valid declared skill (summary given as a list, as a profile asset would) and its prompt doc present, `render_skills` writes its `SKILL.md` to every active skill host with the thin-pointer body labelled "skill" and the declared frontmatter, and a re-render changes nothing; with the prompt doc absent it writes nothing for that skill.
- [x] AC-2: Each validation rule in Requirement 2 has a test whose invalid value is reported by `skill_declaration_problems`; a full `render_agent_surfaces` run (and `render_platform_surfaces` main) with an invalid declaration refuses with every problem named and leaves every rendered file byte-identical; a `wf-` name and a stale-path name are refused.
- [x] AC-3: The stock declaration renders exactly the current framework skills (existing render tests unchanged); an invalid skill declaration does not stop the server (`declared()` false for a skills-only declaration) and `wf_server_info` lists declared names and any `skill_problems`.
- [x] AC-4: Docs (including the `layering-rules.md` edge and the `current-state.md` entry) and the CHANGELOG bullet describe the constant; the change's own tests pass and no failure elsewhere is attributable to this change.

## Tasks

- [x] Declaration constant, `skill_declaration_problems`, test-support `SHIPPED_DECLARATION` and profile assertion
- [x] Renderer: call-time read, preflight validation, registry loops, thin-pointer label
- [x] `wf_server_info` listing
- [x] Docs and CHANGELOG
- [x] Tests

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| skills-seam | implementer | — | |


## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/record_layout_support.py`, `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`, `docs/specs/mcp-tool-surface.md`, `docs/architecture/current-state.md`, `docs/architecture/layering-rules.md`

## Affected Architecture Docs

`docs/architecture/layering-rules.md`: record the new flat-sibling import edge `render_agent_surfaces` -> `mcp_tool_extensions` (direction and reason) beside the existing `mcp_tool_roster` -> `mcp_tool_extensions` row. `docs/architecture/current-state.md`: add the skills constant to the extension declaration, stating it is renderer-only and never fatal to the server.

## Platform Behavior

Rendering writes the same `SKILL.md` bytes on Windows, macOS, Linux and WSL2; the existing symlink and host-root checks apply unchanged. `prompt_doc` is POSIX-form on every platform (a backslash is refused).

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the seam itself |
| AC-2 | required | an invalid declaration must never reach a host |
| AC-3 | required | stock surface unchanged |
| AC-4 | required | docs and release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Implemented: `EXTENSION_SKILLS` (plain literal) and `skill_declaration_problems` in `mcp_tool_extensions` (stdlib-only; also refuses a `prompt_doc` with a backtick, control character, or empty or `.` segment, and YAML numbers including base-60 and `.inf`/`.nan`); renderer `declared_skill_problems` (adds the retired-path check) and `declared_skills`, validated in `_skill_output_destinations` so `preflight_agent_surface_paths` refuses before any write, re-checked in `render_skills`; `_thin_pointer_body(label=...)` keeps framework skills byte-identical; `wf_server_info` lists `skills` and `skill_problems`; test support `SHIPPED_DECLARATION`, profile `_VALIDATE_DRIVER` and the refusal-driver reset updated; spec, `layering-rules.md` row, `current-state.md` sentence and CHANGELOG Added bullet | scratch impl89: 643 OK across 10 files (new `test_declared_extension_skills.py`, 24 tests) |
| 2026-10-05 | Mutation probes killed (35) across renderer, name, text, `prompt_doc`, entry-shape, summary and server-side rules; four first-round survivors (backslash, colon, absolute, string summary) were caught only by a neighbouring rule, so the tests now assert each rule's own message | scratch impl89 |
| 2026-10-05 | Architecture review folded in: the new `render_agent_surfaces` -> `mcp_tool_extensions` edge is recorded in `layering-rules.md` (A1); docs state the constant is renderer-only (A4) | architecture review |
| 2026-10-05 | Readiness review folded in: validation moves to the render preflight so nothing is written on a bad declaration (B1); renderer-only declaration kept out of `declared()` (N1); `wf-` prefix covers framework-name collisions (N2); stale-path names refused (N3); fuller YAML and name rules (N4); list or tuple summaries (N5); call-time read (N6); profile assertion (N7); neutral thin-pointer label (N8) | readiness review |
| 2026-10-05 | Planned from Waveforge R3 | `render_agent_surfaces.SKILL_REGISTRY`, `render_skills` read |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | Renderer-only declaration, outside `declared()` | a bad skill entry must not stop the MCP server or the allowlist render | validating with the tool declarations |
| 2026-10-05 | Declared skills reuse the thin-pointer body and must not use the `wf-` prefix | keeps the workflow in the prompt doc and the `wf-` family framework-owned | free-form bodies; allowing `wf-` names |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A declared value breaks the YAML frontmatter | plain-scalar character rules in validation |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
