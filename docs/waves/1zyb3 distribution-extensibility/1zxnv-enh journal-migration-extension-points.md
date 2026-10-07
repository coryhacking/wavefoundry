# Journal Migration Extension Points: Declared Pristine Templates and a Pre-Migration Hook

Change ID: `1zxnv-enh journal-migration-extension-points`
Change Status: `implemented`
Owner: framework-operator
Status: planned
Last verified: 2026-10-06
Wave: 1zyb3 distribution-extensibility

## Rationale

The upgrade's journal migration has a single deletion oracle and no extension point. At HEAD `06c02e63` (paths under `.wavefoundry/framework/scripts/`):

- `upgrade_extensions.migrate_journals` (line 1475) deletes a journal only when, after CRLF normalization, it equals `_pristine_journal_template(wave_id, title, date)` (line 1233, compared at line 1571). That function is Wavefoundry's own retired scaffold.
  - A distribution that generated a different journal scaffold cannot get its pristine journals deleted. Every one is "left" for the manual **Migrate journals** prompt.
- `_migrate_journals` (line 1613) is called from one place, `pre_docs_gate` (line 1902). It runs only when `_from_version_predates(from_version, "1.15.0")`.
- `upgrade_wavefoundry._run_hook` (line 1158) runs the extension-module hook first and the convention script (`.wavefoundry/hooks/pre-docs-gate`) second.
  - So a distribution's own pre-docs-gate hook runs after the migration, too late to prepare the journal folder.
- The `_migrate_journals` docstring calls it "The post-extract caller", but its only caller is `pre_docs_gate`.

Census (predicate: call sites of the oracle and of the applying caller). Command: `grep -n "_pristine_journal_template(\|_migrate_journals(" .wavefoundry/framework/scripts/upgrade_extensions.py`. Result: definitions at 1233 and 1613, calls at 1571 and 1902. `grep -rn` over the rest of the scripts tree (tests excluded) finds no other reference.

Wave C's shared history-path constant (`1zxnt`, `history_paths.py`, value `("journals", "snapshots")`) answers "is this path under a history directory" for skip predicates. The migration reads one fixed legacy location (`_JOURNALS_REL`, `docs/agents/journals`), not an exclusion, so this change does not consume that constant. It must not add a new quoted `"journals"` literal outside `_JOURNALS_REL` and its migration code, because wave C's AC-3 census allows only those.

## Requirements

1. **One declaration surface.** Two renderer-style declarations join the distribution-edited `mcp_tool_extensions.py` (coordinator decision; no new declaration module). Both ship empty.
   - `EXTENSION_JOURNAL_TEMPLATES: tuple[str, ...] = ()`: extra pristine journal scaffold texts. Each may use the placeholders `{{wave_id}}`, `{{title}}` and `{{date}}`.
   - `EXTENSION_JOURNAL_PRE_MIGRATION_HOOK: str = ""`: `"module:function"`, where `module` is a flat module already declared in `EXTENSION_HELPER_MODULES` and `function` is a callable defined there. The upgrade calls it as `function(root)` with the repository root `Path`.

   Following the `EXTENSION_SKILLS` precedent, both stay outside `declared()`, `declaration_problems` and `validate_declaration`, so they never change the served tool surface and never stop the MCP server. A new `journal_declaration_problems()` in the same module returns one named message per problem (empty means valid). `wf_server_info` is not changed.
2. **Validation rules** (`journal_declaration_problems`):
   - `EXTENSION_JOURNAL_TEMPLATES` is a tuple (or list) of strings; each is non-empty, at most 65,536 characters and has no `\r`;
   - the only `{{...}}` tokens are the three placeholders;
   - at least one non-blank line holds no placeholder;
   - two placeholders never touch without literal text between them;
   - the hook is `""` or exactly one `:` joining a module name and a function name; the module name passes the existing `_module_name_problems` rules and is listed in `EXTENSION_HELPER_MODULES`; the function name is an identifier. Whether the function exists and takes one positional argument is checked when the hook is loaded (Requirement 3), since the validator is stdlib-only and imports nothing.
3. **Loading.** Everything in this requirement happens inside the existing `_from_version_predates(from_version, "1.15.0")` gate, so an upgrade that does not run the migration never loads or validates the journal declaration. Inside the gate, `pre_docs_gate` loads `mcp_tool_extensions.py` by file path from the extracted tree, under a private module name, so a stale copy in `sys.modules` never answers.
   - **Missing file:** an extracted tree with no `mcp_tool_extensions.py` reads as the empty declaration, and the migration runs as at HEAD.
   - **Missing constants:** a module that predates these constants (`getattr` default) reads as the empty declaration.
   - **Import failure:** a module that raises on import is refused like an invalid declaration, with one path-free problem naming the module and the exception type only (never the exception text).
   - **Invalid declaration:** inside the gate, `pre_docs_gate` raises before touching any journal, with a message listing every problem. This refuses the upgrade at that phase, consistent with how an invalid tool or skill declaration refuses its own consumer; the operator fixes the declaration and reruns.
   - **Hook loading:** the helper module is loaded by file path from the extracted scripts directory, only from a `.py` file listed directly in that directory (the `_load_extension_module` rule). A missing file, a missing attribute, a non-callable, or a signature that cannot bind one positional argument is an invalid declaration (refused as above).
4. **Template matching.** `migrate_journals` (preview and apply alike) deletes a journal when, after CRLF normalization, it equals the built-in scaffold (checked first, unchanged) or fully matches any declared template.
   - A declared template matches when its literal text is equal and each placeholder captures one line fragment. `{{date}}` captures `\d{4}-\d{2}-\d{2}`; `{{wave_id}}` and `{{title}}` capture one or more non-newline characters.
   - Every occurrence of one placeholder must capture the same text.
   - Matching is a single full match over a compiled pattern with no nested quantifiers.
   - A matched journal is reported under `deleted`, as the built-in oracle's are. `migrate_journals` takes the templates through a keyword argument whose default is the loaded declaration, so a preview caller sees the same oracle.
5. **Pre-migration hook.** Inside the existing version gate, `pre_docs_gate` calls the declared hook once, immediately before `_migrate_journals`.
   - If the hook raises, the migration is skipped for this upgrade and journals stay untouched. One path-free warning names the hook (`module:function`) and the exception type only, never the exception text, and says a later upgrade or the Migrate journals prompt finishes the work. The upgrade continues.
   - The hook is not called when the gate skips the migration (from-version at or after 1.15.0). The public preview (`migrate_journals(root, apply=False)`) never calls it.
6. **Docstring.** The `_migrate_journals` docstring names its real caller, `pre_docs_gate`, before the docs gate.
7. **Unchanged default.** Under the shipped empty declaration, behavior and output are byte-identical to today.

## Scope

**Problem statement:** A distribution cannot teach the journal migration its own pristine scaffolds or prepare the journal folder before the migration runs.

**In scope:**

- `mcp_tool_extensions.py`: the two constants, their comments, and `journal_declaration_problems`.
- `upgrade_extensions.py`: load by path, hook loading, template matching in `migrate_journals`, the hook call and refusal in `pre_docs_gate`, the warning, and the docstring fix.
- `tests/record_layout_support.py`: the two keys in `SHIPPED_DECLARATION` (the key-set pin in `test_profile_support.py` requires every `EXTENSION_*` constant there), and `journal_declaration_problems()` added to `_VALIDATE_DRIVER` beside `skill_declaration_problems()` (guarded by `hasattr` the same way), so an invalid journal declaration in a profile asset is refused when the asset is applied.
- Tests in `test_upgrade_wavefoundry.py`, beside `JournalMigrationProfileTests`, and validator tests beside the existing declaration tests.
- `docs/specs/mcp-tool-surface.md` (two rows in the declaration table and a short "Declared journal migration" paragraph next to **Declared skills**), seed `210-migrate-journals.prompt.md` (one sentence beside its preview sentence), CHANGELOG.

**Out of scope:**

- Containment, `dir_fd` and message hardening of the migration's file operations (wave B, `1zxns`).
- The history-path constant and archive-aware journal tests (wave C, `1zxnt`).
- Changing the 1.15.0 version gate, the built-in oracle, or the relocation rules.
- A general distribution hook framework for other upgrade phases.

## Acceptance Criteria

- [x] AC-1: A journal that equals a declared template, with its own values substituted, is deleted by `pre_docs_gate` on a pre-1.15.0 upgrade and listed under `deleted` by `migrate_journals(root, apply=False)`. Its CRLF form is deleted too. A copy differing by one character, and a copy whose two `{{wave_id}}` occurrences differ, are left and listed under `left`.
- [x] AC-2: Each validation rule in Requirement 2, each hook-loading failure in Requirement 3, and an extracted `mcp_tool_extensions.py` that raises on import has a case that triggers it. On a pre-1.15.0 upgrade, `journal_declaration_problems()` (or the load) names the problem, path-free for the import failure, and `pre_docs_gate` raises listing it with `docs/agents/journals/` byte-identical. On a 1.15.0-or-later upgrade the same invalid declaration is not loaded or validated and `pre_docs_gate` completes. The profile validator `record_layout_support._VALIDATE_DRIVER` reports the same problems for a profile asset that declares them.
- [x] AC-3: Hook ordering is proven by effect: a hook that writes a pristine built-in scaffold into the journal folder has that file deleted by the same `pre_docs_gate` call. The hook is called exactly once, with the repository root.
- [x] AC-4: The hook is not called when the from-version is 1.15.0 or later, or by `migrate_journals(root, apply=False)`.
- [x] AC-5: A hook that raises with an exception whose text contains an absolute path leaves the journal folder byte-identical. `pre_docs_gate` returns normally, and the warning names the hook and the exception type and contains no part of the exception text.
- [x] AC-6: With the shipped declaration, `journal_declaration_problems()` returns `[]`, `declared()` stays False, and the existing journal-migration tests pass unchanged. The key-set pin in `test_profile_support.py` passes with both new keys frozen empty.
- [x] AC-7: With an extracted `mcp_tool_extensions.py` that lacks both constants, and with no extracted `mcp_tool_extensions.py` at all, `pre_docs_gate` migrates exactly as at HEAD.
- [x] AC-8: The `_migrate_journals` docstring names `pre_docs_gate`. `grep -n "post-extract caller" .wavefoundry/framework/scripts/upgrade_extensions.py` returns nothing.
- [x] AC-9: Wave C's AC-3 census command, rerun after this change, lists no new `"journals"` hit.

## Tasks

- [x] Open `framework_edit_allowed` for the scripts and close it after; open `seed_edit_allowed` for the seed 210 sentence and close it right after.
- [x] `mcp_tool_extensions.py`: the two constants and `journal_declaration_problems`.
- [x] `upgrade_extensions.py`:
  - [x] add the by-path declaration loader, the helper-module hook loader, template compilation and matching;
  - [x] add the `templates` keyword on `migrate_journals`, and the refusal, hook call and path-free warning in `pre_docs_gate`;
  - [x] fix the docstring.
- [x] `record_layout_support.py`: freeze both keys in `SHIPPED_DECLARATION` and add `journal_declaration_problems()` to `_VALIDATE_DRIVER`.
- [x] Tests for AC-1 to AC-9. Use a temporary scripts copy for declaration variants; never edit the canonical module from a test.
- [x] Update `mcp-tool-surface.md`, the seed 210 sentence and the CHANGELOG entry.
- [x] Run `wf_validate_docs`, then the full suite last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 declaration and migration | implementer | waves B and C landed | `mcp_tool_extensions.py`, `upgrade_extensions.py`, `record_layout_support.py`, tests |
| ws-2 docs | implementer | ws-1 | spec, seed 210, layering rules, CHANGELOG |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/record_layout_support.py`, `.wavefoundry/framework/scripts/tests/test_profile_support.py`
- `.wavefoundry/framework/seeds/210-migrate-journals.prompt.md`
- `docs/specs/mcp-tool-surface.md`, `docs/architecture/layering-rules.md`
- Root-level file edited (not a path token): CHANGELOG.md.

No `@mcp.tool` handler and no tool schema changes: the new constants are outside `declared()` and the served surface, so neither the handler digest fixture nor any tool-surface golden is touched. The new framework Python holds no record-vocabulary literal: the placeholders are `{{wave_id}}`, `{{title}}` and `{{date}}`, and the record filename never appears.

## Affected Architecture Docs

`docs/architecture/layering-rules.md`: one row stating that `upgrade_extensions` loads `mcp_tool_extensions` and the declared hook's helper module by file path from the extracted tree (never through `sys.modules`), and that `mcp_tool_extensions` still imports no framework module. `docs/ARCHITECTURE.md` and the other child docs: N/A, since the migration's place in the upgrade flow is unchanged.

## Platform Behavior

- Template comparison normalizes CRLF to LF before matching, as the built-in oracle does, so a Windows checkout with `core.autocrlf=true` matches on Windows, macOS, Linux and WSL2 alike.
- Templates may not contain `\r`, so the declaration itself is newline-neutral.
- Loading by file path (`importlib.util.spec_from_file_location`) behaves the same on every platform. The path is built with `pathlib` from the repository root.
- Deletion uses the migration's existing removal routine as wave B leaves it: directory-handle based on POSIX, path based on native Windows. This change adds no file operation of its own.
- The hook receives a `pathlib.Path`. What the hook does on each platform is the distribution's responsibility, stated in the constant's comment.
- The helper-module listing check compares the exact file name from `os.listdir`, so a mis-cased module name is refused on case-insensitive volumes (macOS APFS default, Windows NTFS, WSL2 `/mnt/c`) as on Linux, matching `_load_extension_module`.
- The hook warning carries only the hook name and exception type, so no absolute path (POSIX or a Windows drive path) reaches the upgrade log.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The declared oracle is the main request. |
| AC-2 | required | A bad declaration is refused before any journal is touched. |
| AC-3 | required | "Before the migration" is the hook's whole contract. |
| AC-4 | required | The hook runs only on an applying migration. |
| AC-5 | required | A hook failure must leave journals untouched. |
| AC-6 | required | The shipped behavior is unchanged. |
| AC-7 | important | Covers the old-pack and partial-tree window. |
| AC-8 | nice-to-have | The docstring accuracy fix. |
| AC-9 | important | Keeps wave C's single-definition census true. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-06 | Planned from the verified Waveforge report item R4; claims checked against HEAD `06c02e63`. | Census command in Rationale. |
| 2026-10-06 | Implemented. `mcp_tool_extensions`: `EXTENSION_JOURNAL_TEMPLATES`, `EXTENSION_JOURNAL_PRE_MIGRATION_HOOK`, `journal_declaration_problems(templates, hook, helper_modules)` (reads the module constants when an argument is None). `upgrade_extensions`: `JournalDeclarationError`, `_load_journal_declaration` (by-path load under a private name; missing file or constants read as empty; import failure names the class only), `_load_journal_hook` (exact listed `.py`, resolved parent check, signature bind), `_compile_journal_template` (escaped literals, named group then backreference per placeholder), `migrate_journals(..., templates=)` (default loads the declaration without the hook), `_run_journal_pre_migration_hook`, and the gate wiring in `pre_docs_gate`; `_migrate_journals` docstring names `pre_docs_gate`. `record_layout_support`: both keys frozen, `journal_declaration_problems()` in `_VALIDATE_DRIVER`. Docs: spec rows and paragraph, layering row, seed 210 sentence, CHANGELOG Added bullet. | `JournalDeclarationProblemTests` (3), `JournalDeclarationMigrationTests` (10, the Windows junction case skips off Windows), `ApplyProfileTests.test_an_invalid_journal_declaration_is_refused`; `test_upgrade_wavefoundry.py` 653 ok, `test_profile_support.py` 74 ok. AC-8 grep empty. AC-9 census non-test hits unchanged (`_JOURNALS_REL` and the two checkpoint stage-name lines). |
| 2026-10-06 | Deviations: the hook warning carries the exception class name only, not `lifecycle_lock.path_free_exception_text`, because Requirement 5 and AC-5 forbid any exception text. `test_extension_tool_modules.py` (outside Serialization Points) gains the two keys in its refusal-driver reset dict, which `DeclarationConstantCensusTests` requires for every `EXTENSION_*` constant. No tool-surface golden changed. Gapfill: shell reads used for retrieval. | Mutation probes in scratch: validator returning `[]`, warning with exception text, template matching dropped, backreference dropped, hook moved after the migration, helper listing check dropped: all killed. |
| 2026-10-06 | Delivery repair DEL-2: free-text placeholders `{{wave_id}}` and `{{title}}` now capture 1 to 512 characters (`_JOURNAL_PLACEHOLDER_MAX`; real wave ids and titles are far shorter), and `migrate_journals` skips the pattern for a journal longer than `_journal_template_max_length(template)`, so two placeholders on one long line cannot backtrack quadratically. Tests: `test_free_text_placeholders_use_bounded_quantifiers` (structural, plus a 200,000-character pathological line under a generous ceiling), `test_journal_longer_than_the_template_bound_is_never_pattern_matched` (spy pattern). | Probes: unbounded `+` restored, length cap removed: both fail. |
| 2026-10-06 | Delivery repair DEL-3: `_load_journal_hook` also requires `resolved.name == file_name`, mirroring the server loader's stem check, so a same-directory link to a sibling script is refused. Test `test_helper_link_to_a_sibling_script_is_refused` (skips where symlinks are unavailable). | Probe: name check removed: test fails. |
| 2026-10-06 | Delivery repair DEL-4d: inside the 1.15.0 gate `pre_docs_gate` now loads and validates the journal declaration (hook load included) before `_migrate_memory_naming`, and always passes the loaded templates to `_migrate_journals`, so the declaration module executes once. `test_pre_docs_gate_version_gates_journal_migration` now expects `_migrate_journals(root, ())` because the gate always passes the (here empty) loaded templates. New tests: `test_invalid_declaration_leaves_the_memory_naming_migration_unapplied`, `test_declaration_module_is_executed_once_per_gate`. Spec paragraph updated (bound, sibling-link refusal, refusal before any pre-1.15.0 migration); CHANGELOG bullet updated. Gapfill: shell reads used for retrieval. | `test_upgrade_wavefoundry.py` 658 OK. Probes: memory naming moved before the load, templates not passed: both fail. |
| 2026-10-06 | Full suites on a fresh scratch copy after all repairs: shipped `run_tests.py --no-cache` OK, 11,547 tests across 165 files, 0 failing files; `run_tests.py --profile declared` 0 of 165 files failed (11,547 tests). | Logs `sD3_shipped.log`, `sD3_declared.log` in the implementer scratch. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-06 | The two declarations live in `mcp_tool_extensions.py`, and the hook is `"module:function"` in a declared helper module (coordinator decision). | One declaration surface for distributions, reusing the existing helper-module and module-name rules. Kept outside `declared()` like `EXTENSION_SKILLS`, so the server and tool surface are unaffected. | A new declaration module; constants in `upgrade_extensions.py`; a convention script (runs after the migration). |
| 2026-10-06 | An invalid declaration refuses the upgrade at `pre_docs_gate` with its problems; a hook that raises skips the migration with a path-free warning and the upgrade continues (coordinator decision). | Consistent with how every other declaration is validated; a hook failure leaves journals in place, which is always safe because a rerun or the Migrate journals prompt finishes the work. | Skip-and-warn for both (hides a broken declaration); abort on hook failure (blocks an upgrade over a journal cleanup). |
| 2026-10-06 | Not consuming wave C's history-path constant. | That constant answers a skip predicate; the migration reads one fixed legacy location. | Derive `_JOURNALS_REL` from it (mixes two meanings). |
| 2026-10-06 | The hook-failure warning carries the hook name and exception class only, and the preview never loads or runs the hook's helper module. | Requirement 5 forbids any part of the exception text, and the shared path-free helper can keep some of it; a preview must not execute distribution code. | Use the path-free exception text (may keep message fragments); run the hook in preview (executes code on a dry run). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A too-general declared template deletes journals with operator content. | The validation rules require a placeholder-free non-blank line and forbid adjacent placeholders. Each placeholder is confined to one line, so content on a new line cannot match. The constant's comment states that a template is the distribution's assertion of zero content, as `EXTENSION_ARTIFACT_PATH_FIELDS` is for artifacts. |
| An old runner loads `upgrade_extensions` from the new zip while the extracted `mcp_tool_extensions.py` predates the constants (partial extraction). | Missing constants read as the empty declaration (AC-7). |
| Declaring a helper module only for the hook also makes the MCP server load and hash it (helper modules are loaded at server start). | Documented in the constant's comment: the hook's helper must import cleanly in the server process, and its `register`, if any, is never called. |
| Shared file `upgrade_extensions.py` with:<br>- wave A (`1zx02`, lock cut-over);<br>- wave B (`1zxns`, containment and `dir_fd` in the journal code);<br>- wave C (`1zxnt`, history-path sites at lines 2220 and 2445).<br>Shared file `test_upgrade_wavefoundry.py` with wave C (`JournalMigrationProfileTests` archive-aware records). | A, B and C land before this wave under the fixed A to E wave sequence. This change edits `migrate_journals` as B leaves it, and rebases on C's `test_upgrade_wavefoundry.py` edits (the `JournalMigrationProfileTests` archive-aware records): C lands first, fixed order. |
| Shared files `mcp_tool_extensions.py`, `tests/record_layout_support.py` and `docs/specs/mcp-tool-surface.md` with `1zxnu-enh declared-skill-ownership-and-profile-goldens` in the same wave. | Edit order inside wave D for shared files: `1zxnu` first, then this change, then `1zxny`. Rerun the declaration key-set pin after this change. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
