# Declared Skill Ownership, Orphan Removal and Prompt Templates; Declared-Profile Golden Covers Modules, Hidden Tools, Replacements and Skills

Change ID: `1zxnu-enh declared-skill-ownership-and-profile-goldens`
Change Status: `implemented`
Owner: framework-operator
Status: planned
Last verified: 2026-10-06
Wave: 1zyb3 distribution-extensibility

## Rationale

Wave 1zv8c gave a distribution its own skills through `mcp_tool_extensions.EXTENSION_SKILLS`. The renderer cannot tell a SKILL.md it wrote from one an operator wrote, so it has three gaps, all confirmed at HEAD `06c02e63` (paths under `.wavefoundry/framework/scripts/`):

- **No ownership marker.** `render_agent_surfaces.skill_document` (line 760) emits only `name` and `description` frontmatter and the body; nothing marks the file as renderer-owned.
- **Unconditional overwrite.** `render_skills` (line 862) writes every eligible skill through `write_text` (line 1469). It refuses only symlinked paths and treats only `STALE_SKILL_PATHS` (line 449) specially, so a hand-written `.claude/skills/<declared-name>/SKILL.md` is silently replaced.
- **No orphan removal.** When a distribution stops declaring a skill, its rendered folder stays forever. The unreleased 1.29.0 CHANGELOG entry says so: "A skill the distribution stops declaring keeps its rendered `SKILL.md` until removed by hand."

A fourth gap is the prompt doc. A declared skill renders only where its `prompt_doc` exists (`declared_skills`, line 794, sets `requires_doc`). The declaration has no way to ship that doc, so a distribution has to seed `docs/prompts/<name>.prompt.md` some other way. `mcp_tool_extensions.SKILL_KEYS` (line 691) is exactly `("title", "description", "prompt_doc", "summary")`, and `skill_declaration_problems` (line 775) rejects any other key.

Part 3(e) of the same report covers the per-profile tool-surface golden from wave 1zyc3. Today `tests/fixtures/profiles/declared.json` declares only `EXTENSION_TOOL_ALIASES` and `EXTENSION_TOOL_PARAMETERS`. So `tests/fixtures/tool-surface-golden/declared.json` never pins a tool served from an `EXTENSION_MODULES` module with its own schema, a hidden tool, a replacement of a core name, or a declared skill. A regression in any of those declaration paths does not show up as a golden diff.

Code-grounded facts this plan relies on:

- `_load_extension_module` (`wf_server/server_impl.py` line 20372) loads a declared module only from a `.py` file listed directly in the real `SCRIPTS_DIR`. For that reason `tests/test_extension_tool_modules.py` runs every extension-module case in a scratch copy of the scripts tree, in a subprocess (its module docstring says so). `ProfileToolSurfaceGoldenTests._boot` (`tests/test_tool_surface_golden.py`) boots in-process under `base_declaration`, so it cannot load a module.
- `record_layout_support.apply_profile` edits only the constants named in an asset. `_profile_errors` accepts only `modules` and `active` keys. Neither one places a module file into the copied tree, and `run_tests.py --profile declared` uses `apply_profile`.
- `serialize_surface` records each served tool's tier, `inputSchema` and annotations, and nothing else. Skills are never served by the MCP server (`EXTENSION_SKILLS` is renderer-only; `wf_server_info` lists only names, `_declared_skills_for_response` at server_impl line 18496), so the golden cannot represent them.

## Requirements

1. **Ownership marker.** Every SKILL.md rendered for a declared skill carries a fixed marker as the first body line, right after the closing `---` of the frontmatter and its blank line: `<!-- wavefoundry:declared-skill -->`. The frontmatter is unchanged (`name` and `description` only), so no host has to accept an unknown frontmatter key, and an HTML comment is inert in every host's markdown. Framework (`wf-`) skills from `SKILL_REGISTRY` stay unmarked and keep their current overwrite behavior. Marker detection checks that exact line as the first non-blank line after the frontmatter block, ignoring a trailing `\r`; it needs no YAML parser.
2. **Refuse and report an unmarked overwrite.** Before any write, the render checks each declared skill's target on each active host. If an existing SKILL.md there lacks the marker, the render does not overwrite it: the file stays byte-identical and that skill is skipped on that host. Everything else still renders, and the render prints one stderr `NOTICE` per refused path. Each notice names the repository-relative path and the remedy: rename the declared skill, or remove or rename the hand-written folder. `wf_sync_surfaces` already includes stderr in its `output`.
   - **Legacy adoption.** An unmarked file counts as owned, and is rewritten with the marker, when its bytes equal what the 1zv8c renderer produced for the same declared skill (the current `skill_document` output). The comparison ignores CRLF versus LF. This serves trees built from current (unreleased) main, where 1zv8c rendered declared skills without a marker; no released version ships `EXTENSION_SKILLS`, but distributions build from main.
3. **Orphan removal.** The pass runs only when the host skills root itself is not a link; a linked root raises before any write, as today. On each active host it lists the immediate children of the host skills directory and, for each child, decides before touching anything:
   - **Links are skipped, never followed.** A child whose `lstat` shows a symlink, or (Windows) a junction or other reparse point, or whose `resolve()` differs from its lexical path, is skipped silently. Its marker is never read through the link. The same `resolve()` equals lexical-path check applies to the child's `SKILL.md` before it is read or unlinked.
   - **Candidate.** A child is an orphan candidate when its name does not start with `wf-`, its name casefolded matches no currently declared name, and its `SKILL.md` is a regular file (by `lstat`) that carries the marker.
   - **Extra entries.** Before any unlink, the candidate folder is listed. If it holds anything other than `SKILL.md`, the folder is left entirely untouched (the marked `SKILL.md` included) and reported in a stderr `NOTICE` naming the folder.
   - **Removal.** Otherwise the `SKILL.md` is unlinked and the folder removed with `rmdir`, never a recursive delete. The removed paths are returned among the changed paths, like `STALE_SKILL_PATHS` removals.

   Orphans are computed and checked before the first write. A declared skill that is merely gated off (its prompt doc is absent) is still declared, so its folder is not an orphan.
4. **Optional `prompt_doc_template`.** A declared skill may name `prompt_doc_template`, the only optional key.
   - **Value.** A POSIX path relative to the framework `install/` directory, ending in `.prompt.md`. It has no empty, `.` or `..` segment, no backslash, no `:`, no leading `/`, no control character and no backtick.
   - **Validation.** `skill_declaration_problems` checks the value. A missing required key is still reported, and any key outside the required four plus this one is still unknown.
   - **When it applies.** At render time, if the skill's `prompt_doc` does not exist, the renderer creates it from the template. It resolves the template the way `_resolve_install_asset` does (the target's `.wavefoundry/framework/install/` first, then the packaged copy) and stamps `{{generated_at}}` with today's date, as `reconcile_lifecycle_prompt_baselines` does. It writes through the same contained-path writer and never overwrites an existing doc.
   - **Order.** Creation runs before the skill gate, so the skill renders in the same pass. The destination is included in `preflight_agent_surface_paths`.
   - **Missing template.** If the template cannot be found when the doc is absent, the render raises naming the template path.
5. **Profile asset carries module files.** A profile asset may name `module_files`, `{module_name: path relative to tests/fixtures/profiles/}`. Each named module must appear in that asset's `EXTENSION_MODULES` or `EXTENSION_HELPER_MODULES`. `_profile_errors` validates the shape and that each source exists under the profiles directory. `apply_profile` copies each source into the copied scripts directory as `<module_name>.py` through `replace_file_in`, and still never touches the canonical tree.
6. **Extended `declared` asset.** `tests/fixtures/profiles/declared.json` keeps its two aliases and adds:
   - one extension module (source under `tests/fixtures/profiles/`) serving one new tool with its own non-trivial input schema, with its prefix and tier declared;
   - one hidden canonical tool, served only through a plain alias;
   - one replacement of a core name, with `alias_for_core`;
   - one declared skill whose `prompt_doc_template` is an already-shipped install template, `lifecycle-prompts/review-plan.prompt.md`, so no fixture-only template ships in the pack.

   The implementer picks the hidden and replaced core names so that the `--profile declared` run does not regress (AC-11), and records the choice in the Decision Log.
7. **Golden boot for module-declaring assets.** `ProfileToolSurfaceGoldenTests` boots an asset that declares `EXTENSION_MODULES` or `EXTENSION_HELPER_MODULES` in a scratch copy made with `copy_scripts_tree` and `apply_profile`, in a subprocess. `serialize_surface`, `strip_prose_descriptions`, `_canonical_schema` and `_stub_handler` move out of `test_tool_surface_golden.py` into a dependency-free tests support module, `tests/tool_surface_support.py` (stdlib only), which `copy_scripts_tree` adds to its copied support list. The subprocess imports that one definition and emits the serialized surface as JSON. The subprocess call uses a generous timeout (at least 300 seconds), so a loaded machine does not fail the boot. Module-free assets keep the in-process boot. `WF_UPDATE_TOOL_SURFACE_GOLDEN=1` regeneration and the per-tool diff work the same for both boots.
8. **Skills outside the golden.** The golden format represents served tools only, so skills are pinned by a separate test. Under the `declared` asset's declaration, rendering a temporary repository produces the marked SKILL.md and the template-created prompt doc. The golden test's docstring states that skills are not part of the golden. The existing assertion `set(tools) - set(shipped) == {"wf_alias_help", "wf_alias_read_raw"}` (`test_tool_surface_golden.py` line 556) is updated to the new asset's added names (the two aliases, the module tool and the `alias_for_core` name), and a second assertion pins `set(shipped) - set(tools)` to the hidden canonical name, which the shipped golden has and the declared one lacks.
9. Under the shipped empty declaration nothing changes. The framework skills render byte-identically, the shipped golden is unchanged, and no file outside a declared skill folder or its prompt doc is written or removed.

## Scope

**Problem statement:** The renderer overwrites hand-written skills that share a declared name, never removes skills a distribution stops declaring, and cannot ship a declared skill's prompt doc. The declared-profile golden also does not cover module tools, hidden tools, replacements or skills.

**In scope:**

- `render_agent_surfaces.py`: marker in `skill_document` for declared skills only, marker detection, legacy adoption, refuse-and-report, orphan removal, template creation, and the preflight addition.
- `mcp_tool_extensions.py`: the optional `prompt_doc_template` key, its validation, and the `EXTENSION_SKILLS` comment.
- Test support (`record_layout_support.py`: `module_files` in `_profile_errors` and `apply_profile`), the `declared` asset, a fixture module, the golden test's subprocess boot, and the regenerated `tool-surface-golden/declared.json`.
- Tests in `test_declared_extension_skills.py`, `test_render_agent_surfaces.py` (if a framework-skill byte check needs it), `test_tool_surface_golden.py` and `test_profile_support.py`.
- Docs: `docs/specs/mcp-tool-surface.md` (Declared skills section and the `EXTENSION_SKILLS` table row), `docs/architecture/current-state.md` (the `EXTENSION_SKILLS` sentence), `docs/architecture/testing-architecture.md` (Declared-alias run paragraph), and the unreleased 1.29.0 CHANGELOG bullet (its "keeps its rendered SKILL.md until removed by hand" sentence).

**Out of scope:**

- Marking or orphan-removing framework `wf-` skills (the framework owns that namespace, and `STALE_SKILL_PATHS` already retires them).
- Renaming `SKILL_REGISTRY` entries or touching the shipped tool-surface golden (wave E, `1zxnw`/`1zxnx`, lands after this wave).
- Any server or `@mcp.tool` handler change. `wf_server_info` already reports `skill_problems` from `skill_declaration_problems`, so the new key's problems surface with no handler edit.
- Representing skills inside the tool-surface golden format.

Census (predicate: every place that writes or removes a SKILL.md). Command: `grep -n "write_text(target\|stale.unlink\|parent.rmdir" .wavefoundry/framework/scripts/render_agent_surfaces.py`. Result at HEAD: lines 949 and 956 (the stale removal) and line 996 (the write); `render_skills` is the only writer. Callers: `grep -rn "render_skills(" .wavefoundry/framework/scripts | grep -v /tests/` returns only `render_agent_surfaces.py:2838`.

## Acceptance Criteria

- [x] AC-1: A rendered declared skill's SKILL.md has frontmatter holding exactly `name` and `description`, and its first body line is `<!-- wavefoundry:declared-skill -->`. A file with that line elsewhere in the body (not first) does not count as marked. A rendered `wf-` skill's bytes are unchanged from HEAD (byte comparison against `skill_document` output for every `SKILL_REGISTRY` entry).
- [x] AC-2: With an unmarked, hand-written `SKILL.md` at a declared skill's path, a render: leaves that file byte-identical; writes every other skill and surface; prints a `NOTICE` naming the repository-relative path and the remedy; leaves that path out of the changed paths.
- [x] AC-3: An unmarked SKILL.md whose bytes (LF or CRLF) equal the pre-marker rendering of the same declared skill is rewritten with the marker. One that differs by one byte is refused as in AC-2.
- [x] AC-4: After a declared skill is removed from `EXTENSION_SKILLS`, a render removes its marked SKILL.md and empty folder on every active host and returns those paths. In the same run each of these is left untouched (bytes and entries) and the render completes: a marked folder whose name casefolds to a still-declared name; an unmarked folder; a `wf-` folder; a marked folder holding an extra entry, which is also reported in a `NOTICE`; a child folder that is a symlink (POSIX) or a junction (Windows) to a marked folder elsewhere: skipped without reading through it, so the link target is untouched.

  A host skills root that is itself a link still raises before any write.
- [x] AC-5: A declared but gated-off skill (prompt doc absent, no template) keeps its existing marked folder.
- [x] AC-6: `skill_declaration_problems` accepts an entry with a valid `prompt_doc_template`. It reports one named problem each for: absolute path, `..` segment, backslash, `:`, wrong suffix, non-string value, and an unknown extra key.
- [x] AC-7: With `prompt_doc_template` set and the prompt doc absent, a render creates the doc from the template with `{{generated_at}}` stamped and renders the skill in the same pass. With the doc present, the doc is byte-identical after the render. With the template missing and the doc absent, the render raises naming the template path before any write.
- [x] AC-8: Under the shipped empty declaration, a render of a fixture repository produces the same bytes as HEAD for every skill path, and the shipped `fixtures/tool-surface-golden.json` is unchanged.
- [x] AC-9: The committed `tool-surface-golden/declared.json`, read on its own, shows: the module tool with its declared tier and its own schema properties; the hidden canonical name absent, with its alias present; the replaced core name with the module's schema; `alias_for_core` with the core schema and tier.

  A test asserts each of these.
- [x] AC-10: The drift test detects, and names per tool and key, three mutations made through the declaration or the fixture module: a changed module tool schema, a hidden tool un-hidden, and a replacement dropped.
- [x] AC-11: `run_tests.py --profile declared` reports no failing file that passes in a baseline `--profile declared` run of the pre-change tree. Both per-file results are recorded in the Progress Log.
- [x] AC-12: Under the `declared` asset's skill declaration, a render of a temporary repository produces the marked SKILL.md on each active host and the template-created prompt doc. `apply_profile` places the fixture module in the copied scripts directory and refuses a `module_files` entry whose module is not declared or whose source is missing.

## Tasks

- [x] Open `framework_edit_allowed`; close it right after the script and test edits.
- [x] `mcp_tool_extensions.py`: add `SKILL_OPTIONAL_KEYS = ("prompt_doc_template",)`, validate it in `skill_declaration_problems`, and update the `EXTENSION_SKILLS` comment.
- [x] `render_agent_surfaces.py`:
  - [x] add the declared-skill body marker line to `skill_document` (declared skills only), a marker reader, and the legacy-bytes adoption check;
  - [x] add the refuse-and-report path, the orphan pass (computed and containment-checked with the existing preflight, before the first write) and template creation before the skill gate;
  - [x] add the template destinations to `preflight_agent_surface_paths`.
- [x] Tests for AC-1 to AC-8 in `test_declared_extension_skills.py`.
- [x] `record_layout_support.py`: `module_files` support in `_profile_errors` and `apply_profile`, with tests in `test_profile_support.py`. Update that file's existing assertion about the `declared` asset's contents.
- [x] Move the serializer helpers into `tests/tool_surface_support.py` and add it to `copy_scripts_tree`'s support list. Add the fixture module and extend `declared.json`. Add the subprocess boot to `test_tool_surface_golden.py`. Regenerate only the declared golden with `WF_UPDATE_TOOL_SURFACE_GOLDEN=1` and confirm the shipped golden did not change.
- [x] Tests for AC-9, AC-10 and AC-12. Run the baseline and post-change `--profile declared` runs for AC-11.
- [x] Docs: `mcp-tool-surface.md`, `current-state.md`, `testing-architecture.md`, and the CHANGELOG 1.29.0 bullet.
- [x] Run `wf_validate_docs`, then the full suite last (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 skill ownership (R2) | implementer | - | `mcp_tool_extensions.py`, `render_agent_surfaces.py`, `test_declared_extension_skills.py` |
| ws-2 profile module files and golden (3e) | implementer | ws-1 | Needs ws-1's marker and template key for the asset's skill and AC-12 |
| ws-3 docs and CHANGELOG | implementer | ws-1, ws-2 | Spec, architecture and CHANGELOG text |

## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`, `.wavefoundry/framework/scripts/tests/test_tool_surface_golden.py`, `.wavefoundry/framework/scripts/tests/test_profile_support.py`, `.wavefoundry/framework/scripts/tests/test_declared_extension_skills.py`, `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/tool_surface_support.py`
- `.wavefoundry/framework/scripts/tests/fixtures/profiles/`, `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden/declared.json`
- `docs/specs/mcp-tool-surface.md`, `docs/architecture/current-state.md`, `docs/architecture/testing-architecture.md`
- Root-level file edited (not a path token): CHANGELOG.md.

No `@mcp.tool` handler source changes, so `tests/fixtures/register-surface-handler-digests.json` is not touched. If an implementation edit does reach `wf_server/server_impl.py`, that fixture is regenerated in the same change. Only the declared profile golden changes; the shipped `tool-surface-golden.json` must stay byte-identical. New framework Python carries no record-vocabulary literal (no record filename or heading text); the marker and paths above are not record vocabulary.

## Affected Architecture Docs

`docs/architecture/current-state.md` (the wave 1zv8c `EXTENSION_SKILLS` sentence gains ownership, orphan removal and template creation) and `docs/architecture/testing-architecture.md` (the Declared-alias run gains module files and the subprocess golden boot). `docs/architecture/layering-rules.md`: no new import edge; the existing `render_agent_surfaces.py` to `mcp_tool_extensions.py` row stays accurate. `docs/ARCHITECTURE.md` and the other child docs: N/A.

## Platform Behavior

- **Line endings.** SKILL.md and prompt docs are written with `newline=""` (LF bytes on every host, as `write_text` does today). Marker detection and legacy adoption both ignore `\r`, so a checkout with `core.autocrlf=true` on Windows still counts as marked or adoptable.
- **Case-insensitive filesystems.** On macOS APFS (default), Windows NTFS and WSL2 `/mnt/c` DrvFs, two spellings can name the same folder. Declared names are lower-case only, and the orphan pass compares casefolded names, so a marked folder that differs from a declared name only in case is never removed. On case-sensitive Linux ext4, that rule keeps such a folder too (conservative).
- **Removal.** Removal is `unlink` plus `rmdir`, never a recursive delete. A file held open by an editor on Windows makes `unlink` fail. The render then raises naming the path, as the stale-path removal does today, and the operator closes the file and reruns.
- **Symlinks and junctions.** A linked host skills root is refused on every platform through the existing `_skill_path_has_symlink_component` and resolved-root checks. Inside the root, the orphan pass skips a linked child: `lstat` catches a POSIX or Windows symlink, and requiring `resolve()` to equal the lexical path catches a Windows junction (which `Path.is_symlink()` does not report) and a WSL2 DrvFs reparse point, before any read or unlink.
- **Test boot.** The subprocess boot uses `sys.executable` and the copied tree on every platform. `copy_scripts_tree` already removes read-only entries portably.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The marker is the basis of ownership; framework skills must not move. |
| AC-2 | required | The core protection the report asked for. |
| AC-3 | required | Without adoption, every skill rendered from unreleased main would be refused on first render. |
| AC-4 | required | Orphan removal, with the safety cases that keep it from deleting operator work. |
| AC-5 | important | Matches today's gating behavior; avoids churn when a prompt doc is briefly absent. |
| AC-6 | required | A declaration problem must be named before any write. |
| AC-7 | required | The template key's whole contract, including missing-only. |
| AC-8 | required | The shipped surface is unchanged. |
| AC-9 | required | The point of Part 3(e). |
| AC-10 | important | Proves the golden catches regressions on the new paths. |
| AC-11 | important | Keeps the distribution-shaped suite run usable. |
| AC-12 | important | Covers skills where the golden cannot. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-06 | Planned from the verified Waveforge report items R2 and Part 3(e); claims checked against HEAD `06c02e63`. | Census commands in Scope; line numbers cited in Rationale. |
| 2026-10-06 | ws-1: `mcp_tool_extensions.SKILL_OPTIONAL_KEYS` and `_skill_template_problems`; `render_agent_surfaces` gains `DECLARED_SKILL_MARKER`, `has_declared_skill_marker`, legacy adoption (`_legacy_declared_skill_document`, CRLF-insensitive bytes), `_refused_declared_skill_paths` (skip and stderr `NOTICE`), `_declared_skill_orphans` (unlink plus rmdir), `_declared_prompt_doc_creations` (target-first template resolution, `O_EXCL` contained write, before the skill gate) and the preflight destinations. All refusals and orphans are decided before the first write. | `test_declared_extension_skills.py` 42 tests OK (16 new across `DeclaredSkillMarkerTests`, `DeclaredSkillOwnershipTests`, `DeclaredSkillOrphanTests`, `PromptDocTemplateTests`, `StockDeclarationSkillBytesTests`). |
| 2026-10-06 | Platform behavior of the orphan pass: a child is skipped when `lstat` reports a symlink (POSIX and Windows), when `st_file_attributes` carries `FILE_ATTRIBUTE_REPARSE_POINT` (Windows junctions and other reparse points, which `is_symlink()` misses), when `resolve()` differs from the lexical path (also catches WSL2 DrvFs reparse points), or when it is not a directory by `lstat`; the child's `SKILL.md` gets the same checks plus regular-file-by-`lstat`. Names compare casefolded on every filesystem (macOS APFS, Windows NTFS, WSL2 `/mnt/c` and case-sensitive Linux ext4 alike), so a case-variant folder is kept. Removal is `unlink` then `rmdir`; on Windows a file held open makes either fail, and the render raises naming the path. The test creates a junction through `_winapi.CreateJunction` when Windows refuses an unprivileged symlink; verified here on macOS only. | `test_removed_declaration_removes_only_the_owned_folder`, `test_linked_host_skills_root_still_raises_before_any_write`. |
| 2026-10-06 | ws-2: `record_layout_support` validates and copies `module_files` (`_module_file_errors`, `apply_profile(profiles_dir=...)`, copied only when the declaration module is edited) and copies `tests/tool_surface_support.py`, which now holds `serialize_surface`, `strip_prose_descriptions`, `_canonical_schema`, `_stub_handler` and `FIXTURE_SCHEMA`. `declared.json` adds module `dist_tools` (fixture `tests/fixtures/profiles/dist_tools.py`, tool `dist_inventory`, tier read, prefix `dist_`), hides `wf_gpu_doctor` behind the new plain alias `wf_alias_gpu_doctor`, replaces `wf_open_dashboard` (`alias_for_core` `dist_open_dashboard_core`) and declares skill `dist-review` with template `lifecycle-prompts/review-plan.prompt.md`. Names chosen because no test calls `wf_gpu_doctor` or `wf_open_dashboard` through the served registry (grep of quoted names in `tests/test_*.py`). The golden test boots module-declaring assets through `copy_scripts_tree` plus `apply_profile` in a subprocess (timeout 300 s); drift cases now take a `schema_patch` and module-source overrides. Only `tool-surface-golden/declared.json` was regenerated (`WF_UPDATE_TOOL_SURFACE_GOLDEN=1`, in scratch, copied back); `git diff --quiet` on the shipped `tool-surface-golden.json` is clean. Also updated asset-copying helpers in `test_profile_support.py` and `test_declaration_support.py` to copy the module source, and the in-process declared check in `test_declaration_support.py` to leave out the module parts (only a copied tree has the module file). | `test_tool_surface_golden.py` 25 OK, `test_profile_support.py` 73 OK, `test_declaration_support.py` 9 OK, `test_mcp_tool_registry.py` 27 OK, `test_render_agent_surfaces.py` 146 OK, `test_extension_tool_modules.py` 222 OK. |
| 2026-10-06 | Deviation for review: Requirement 8's parenthetical lists four added names, but Requirement 6's hidden tool needs a plain unpinned alias and the only existing plain alias targets `wf_help`, which many tests reference; hiding `wf_gpu_doctor` adds a fifth name, `wf_alias_gpu_doctor`, so the added-names assertion has five. The Decision Log row for the name choice (Requirement 6) is left to the coordinator because Decision Log edits rotate the review receipt. | `test_declared_golden_carries_aliases_tiers_and_mapped_parameters`. |
| 2026-10-06 | Risk census rerun, predicate a test file calling a render function (`grep -l 'render_agent_surfaces(\\|render_skills(\\|ras\\.render\\|render_agent_surfaces\\.render' tests/test_*.py`): 9 files, 3 with `base_declaration`. No stock-surface test needed `apply_base_declaration`: the post-change `--profile declared` run below shows no render-list regression. | AC-11 run below. |
| 2026-10-06 | Mutation probes (scratch copy, each restored): marker matched anywhere, legacy adoption removed, refusal removed, all three link checks off with `os.stat`, extra-entry check off, case-sensitive name compare, `wf-` skip removed, template overwrite of an existing doc, preflight template destination dropped (with and without render containment), fixture module schema changed, undeclared `module_files` allowed: every probe fails at least one named test. A single link layer off is not detected, because the three link checks overlap (defense in depth). | Probe scripts `probes.py`, `probes_link.py`, `probe_pf.py` in the implementer scratch. |
| 2026-10-06 | AC-11: baseline `run_tests.py --profile declared` on a scratch copy of the pre-change tree: 0 of 165 files failed (11,499 tests). Post-change run: 0 of 165 files failed (11,521 tests). An intermediate post-change run failed only `test_profile_support.py` (a copied tree under the profile already holds `dist_tools.py`; the test now removes it first), fixed before the final run. Full scratch suite `run_tests.py --no-cache`: OK, 11,521 tests across 165 files. `wf_validate_docs` passes. | Logs `baseline_profile.log`, `post_profile2.log`, `full.log` in the implementer scratch. |
| 2026-10-06 | Delivery repair DEL-1 (blocking): `JournalDeclarationProblemTests.test_shipped_declaration_is_valid_and_not_declared` asserted `declared()` is False against the ambient module, which is True by design under `--profile declared`; its assertions now run inside `declaration_support.base_declaration()`. | `test_upgrade_wavefoundry.py` passes under both profiles (runs below). |
| 2026-10-06 | Delivery repair DEL-4a/b/c: `_declared_prompt_doc_creations` treats the prompt doc as present when `os.path.lexists` holds, so a dangling link is never written through; orphan removal keeps `unlink` raising but a failed `rmdir` after it now prints a `NOTICE` naming the repository-relative folder and the exception class and does not raise. New tests: `test_dangling_link_at_the_prompt_doc_is_present_and_never_written_through`, `test_orphan_folder_gaining_an_entry_after_the_decision_survives` (seam adds `.DS_Store` after the orphan decision; folder and entry survive), `test_template_creation_never_overwrites_a_doc_that_appears_after_the_check` (pins `O_EXCL`). Spec: an orphan folder with any extra entry, OS metadata such as `.DS_Store` included, is kept and reported; CHANGELOG bullet notes the link case. | `test_declared_extension_skills.py` 45 OK. Mutation probes, each restored: `lexists` back to `is_file`, `rmdir` swapped for `rmtree`, `rmdir` failure re-raised, `exclusive=False`: each fails its named test. |
| 2026-10-06 | AC-11 evidence after the delivery repairs. Full suites on a fresh scratch copy after all repairs: shipped `run_tests.py --no-cache` OK, 11,547 tests across 165 files, 0 failing files; `run_tests.py --profile declared` 0 of 165 files failed (11,547 tests). | Logs `sD3_shipped.log`, `sD3_declared.log` in the implementer scratch. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-06 | Refusing an unmarked overwrite skips that one skill on that host and reports it; the rest of the render proceeds. | "Refuse and report overwrite" targets the overwrite. Failing the whole render (and with it an upgrade's render phase) over one name collision is out of proportion, and the file is preserved either way. | Raise before any write, as an invalid declaration does (open question for the operator). |
| 2026-10-06 | The marker is a fixed HTML-comment body line, `<!-- wavefoundry:declared-skill -->`, first after the frontmatter; only declared skills carry it (coordinator decision). | Every host tolerates an HTML comment in the body, so ownership does not depend on any host accepting an unknown frontmatter key. `wf-` skills are framework-owned and already retired through `STALE_SKILL_PATHS`. | A `metadata` frontmatter entry (relies on host frontmatter tolerance); a top-level custom key (may be rejected by a strict host). |
| 2026-10-06 | Legacy adoption by exact pre-marker bytes (kept by coordinator decision). | No released version ships `EXTENSION_SKILLS`, but distributions build from current main, whose 1zv8c renderer wrote unmarked skills; exact bytes prove zero operator edits, so marking loses nothing. | Treat every unmarked file as foreign (refuses every skill rendered from unreleased main). |
| 2026-10-06 | The `declared` asset's skill uses the shipped `lifecycle-prompts/review-plan.prompt.md` as its `prompt_doc_template` (coordinator decision). | Nothing fixture-only ships in the pack, and the template already exists in every install. | A fixture template under `install/` (would ship in every pack). |
| 2026-10-06 | The orphan pass skips linked children instead of raising, and leaves a marked folder with extra entries entirely untouched (coordinator decisions). | A link inside the root may point at operator content elsewhere; skipping never reads or deletes through it. Checking for extra entries before the unlink avoids a half-removed folder. | Raise on a linked child (blocks every render over an unrelated link); unlink `SKILL.md` and keep the folder (leaves a half-removed folder). |
| 2026-10-06 | Templates live under the framework `install/` directory and are resolved target first, then packaged. | Same resolution as the lifecycle baselines, and the pack already ships `install/`. | A repository-relative path anywhere (wider write source; harder to contain). |
| 2026-10-06 | A module-declaring profile asset boots its golden in a scratch copy, in a subprocess. | `_load_extension_module` loads only from the real scripts directory, and the suite's repository-state guard forbids writing there. | Patch `SCRIPTS_DIR` in process (bypasses the loader's own checks, so the golden would not reflect a real distribution). |
| 2026-10-06 | Fixture names for the declared profile: module tool `dist_inventory`; `wf_open_dashboard` replaced by the module and kept reachable as `dist_open_dashboard_core`; `wf_gpu_doctor` hidden behind a new plain alias `wf_alias_gpu_doctor` (five added names, not four). | The hidden tool needs a plain, unpinned alias, and the only existing plain alias targets `wf_help`, which many tests call; the chosen core names are not called by name in tests. | Hide `wf_help` (breaks many tests); add a pinned alias (does not exercise the plain-alias path). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| An operator copies the marker line into a hand-written skill, which the renderer then treats as owned. | Accepted: copying the marker is an explicit claim of renderer ownership. A file is marked only when the line is the first body line, so quoting it elsewhere does not mark the file. |
| Adding a hidden tool and a replacement to the ambient declaration breaks tests in the `--profile declared` run that call those names directly. | AC-11 compares against a baseline run. The implementer picks names that tests do not call through the served registry, and records the choice. |
| Under `--profile declared` the ambient `EXTENSION_SKILLS` (with its template) makes every render in a test also create the template prompt doc and the marked skill, so tests asserting exact written lists or file trees change. Census, predicate a test file calling a render function (`grep -l 'render_agent_surfaces(\\|render_skills(\\|ras\\.render\\|render_agent_surfaces\\.render' tests/test_*.py`): 8 files, 2 of which use `base_declaration` (`test_declared_extension_skills.py`, `test_server_tools.py`); a broader predicate (any mention of a render module) gives 36 files, 4 with `base_declaration`. The readiness review counted about 21 and 7 with its own predicate; the implementer reruns the census and records the predicate used. | Tests whose subject is the stock rendered surface get `apply_base_declaration` (they are stock-surface tests by the existing convention), each listed in the Progress Log; AC-11 confirms no file regresses against the baseline run. |
| A distribution's own active asset layers over `declared`, and its `EXTENSION_MODULES` replaces the framework asset's tuple. | The layering rule is unchanged and documented in `testing-architecture.md`. Note the module-file interaction there. |
| Shared file `render_agent_surfaces.py` with wave C (`1zxnt`, history-path constant at line 296) and wave E (`1zxnw`/`1zxnx`, `SKILL_REGISTRY` names, lands after this wave). | Different regions. C lands first and this change rebases on it. E rebases on this change, and its renames go through `STALE_SKILL_PATHS`, which the orphan pass never touches (`wf-` folders are skipped). |
| Shared goldens with wave E. | This change regenerates only `tool-surface-golden/declared.json`. E regenerates after this change lands. |
| Shared files `mcp_tool_extensions.py`, `tests/record_layout_support.py` and `docs/specs/mcp-tool-surface.md` with `1zxnv-enh journal-migration-extension-points` in the same wave (it adds two journal declarations there). | Edit order inside wave D for shared files: this change first, then `1zxnv`, then `1zxny`. Rerun the declaration key-set pin in `test_profile_support.py` after `1zxnv`. |
| The orphan pass deletes a folder an operator still wanted. | Only marked files are removed (a hand-written file has no marker), only for undeclared names, only from a folder holding nothing else, never through a link, and never recursively. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
