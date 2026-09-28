# Edit Hook Gates Bypassed by Absolute Paths

Change ID: `1z823-bug edit-hook-gates-bypassed-by-absolute-paths`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-27
Wave: 1z822 hook-lock-and-setup-safety

## Rationale

The rendered edit hooks decide what an edit touches by comparing the host-supplied path with repo-relative prefixes. In `render_platform_surfaces.py` the shared hook helpers `is_seed_prompt`, `is_framework_maintenance_surface`, `maybe_docs_lint` and `should_reindex` apply `str.startswith(".wavefoundry/framework/…")`, `startswith("docs/")` and similar to the raw path that `detect_file_path` returns. Claude Code always sends an absolute path, so on that host the seed gate and the framework-maintenance gate never block, the post-edit docs-lint never runs, and the reindex mark is decided on a path that never matches. It was observed in this repository: `server_impl.py` and `server.py` were edited on 2026-09-26 with `framework_edit_allowed` closed and nothing blocked. A relative path with `..` or `./`, a symlink, or a case variant on a case-insensitive filesystem slips past the same checks on every host.

Two related defects surface once the path is fixed. The Claude post-edit hook returns on a docs-lint failure before it marks the reindex (and the Copilot and Cursor post-edit hooks likewise skip their reindex trigger), so an edit that fails lint is never indexed. The Claude launcher built by `launcher_command` exits with `sys.exit('<message>')` (status 1) when `CLAUDE_PROJECT_DIR` is missing, and an exception while loading the hook body also exits 1; for a PreToolUse hook status 1 is a non-blocking warning, so a broken launch lets every edit through. Found by an external review of `v1.27.0` (RFC section 7, B1, B2, B3), verified against the code on 2026-09-27.

## Requirements

1. **One path classifier for every hook.** The hook helpers gain one function that turns a host-supplied path into a repo-relative POSIX path, or reports that the path is outside the repository. It anchors a relative path at `REPO_ROOT`, expands `~`, resolves symlinks and `..` (`resolve(strict=False)` already tolerates missing parents; on a resolution error such as a symlink loop it falls back to lexical normalization of the absolute path), and computes containment against the resolved `REPO_ROOT`. On a case-insensitive filesystem (detected at `REPO_ROOT`), both the containment test and the prefix comparison are case-folded, so a variant spelling of any component, including the repository root's own components, is still inside. `is_seed_prompt`, `is_framework_maintenance_surface`, `maybe_docs_lint`, `should_reindex` and every other helper that classifies an edit path by prefix use it. A path outside the repository is not a guarded surface and does not mark a reindex.
2. **Reindex on every exit after an edit.** Every post-edit hook that reindexes today (Claude post-edit, Copilot post-tool-use, Cursor after-file-edit) marks or triggers the reindex on every exit path after the edit, including a docs-lint failure and Cursor's warning gates, and still returns each result exactly as today. The Windsurf docs-lint hook has no reindex today and is unchanged.
3. **Pre-edit hooks fail closed.** Every rendered launcher for a hook that runs before an edit and blocks it by exiting 2 (Claude PreToolUse, Copilot pre-tool-use, Windsurf seed-protect) exits 2 when its project-root variable is missing (where it uses one) or the hook body raises an ordinary exception while loading, and prints the reason to stderr. The launcher catches `Exception` only, so the body's own `SystemExit` passes through unchanged; the command stays one host-neutral line with no shell expansion. Launchers for every other hook keep exit 1, because exit 2 on a Stop hook would stop the session from ending. Which launchers fail closed follows from the hook's role: for Claude it is derived from the declared event in `CLAUDE_HOOKS`; the Copilot and Windsurf pre-edit render sites, which have no event registry, pass an explicit fail-closed flag to `launcher_command`. The command avoids `$` and embedded double quotes so the same text works under PowerShell. A missing `python3` still yields the shell's own non-blocking status; that is a known limit.
4. Existing targets receive the fixed hooks through the normal render on **Upgrade Wavefoundry**; nothing else changes in a target.

## Scope

**Problem statement:** the edit gates and post-edit lint are silently inactive on Claude Code and bypassable on every host.

**In scope:**

- the shared hook helpers and every rendered pre-edit and post-edit hook body that uses them;
- the Claude launcher's exit status by event;
- tests in `test_render_platform_surfaces.py` and the rendered surfaces in this repository.

**Out of scope:**

- hosts' own permission systems;
- what the gates protect (the prefix lists are unchanged; Windsurf's hook remains seed-only);
- MCP-side edit tools, shell edits and hard links, which do not go through host edit hooks: the gates are guard rails against accidental edits, not an adversarial boundary;
- payload fields the detector does not read today (Claude `notebook_path`; Copilot's argument encoding is unverified and unchanged).

## Acceptance Criteria

- [x] AC-1: a rendered Claude pre-edit hook, run with an absolute path, a `./` or `..` path, a symlink into the repository, and (on a case-insensitive filesystem) a case variant of an inner component and of a repository-root component, each naming a seed prompt or a framework-maintenance file, exits 2 while the matching gate is closed and exits 0 once it is open; a path outside the repository exits 0 and marks no reindex.
- [x] AC-2: a rendered post-edit hook given an absolute `docs/` path runs docs-lint, and when that lint fails the reindex is still marked (Claude) or triggered (Copilot, Cursor) and the failure is still reported; Cursor's warning gates also reach the reindex.
- [x] AC-3: each rendered pre-edit launcher (Claude PreToolUse, Copilot pre-tool-use, Windsurf seed-protect) exits 2 when its hook body raises on load, and the Claude one also when `CLAUDE_PROJECT_DIR` is unset; the Claude Stop and SessionStart launchers still exit 1 in the same conditions, and a body's own `SystemExit(0)` still exits 0.
- [x] AC-4: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] Add the path classifier to the hook helpers and route every prefix check through it.
- [x] Reorder the post-edit hooks so the reindex precedes a lint-failure return.
- [x] Add a fail-closed mode to `launcher_command`; select it from the PreToolUse event in `render_claude_settings` and explicitly at the Copilot pre-tool-use and Windsurf seed-protect render sites.
- [x] Tests for AC-1 to AC-3; re-render this repository's hook surfaces; CHANGELOG `[Unreleased]` Fixed bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Hooks | implementer | readiness | Single write owner; MCP code tools for reads |
| Review | combined reviewer | Hooks | One combined reviewer |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`, `.claude/hooks/`, `.claude/settings.json`, `.cursor/hooks/`, `.github/hooks/`, `.windsurf/hooks/`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `CHANGELOG.md` (shared by all three changes in this wave)

## Affected Architecture Docs

`N/A`: the hooks' contract (which surfaces are gated) is unchanged; this fixes how a path is matched against it.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The gates are currently inactive on Claude Code |
| AC-2 | required | Fixing AC-1 activates the lint path that skips the reindex |
| AC-3 | required | A broken launch must not open the gates |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Delivery review (one combined reviewer): red-team and docs-contract approve; code and QA blocked on B1, which is in 1z824's routing. Notes applied here: N1, seed `050-agent-entry-surface-bootstrap` now describes the Copilot and Windsurf pre-edit launchers as fail-closed (shape, not exact text) and drops a false claim that Windsurf `seed-protect` carries a framework plan gate; N3, case-insensitivity is probed on the lettered `.wavefoundry` child so a letterless root is still detected. N5 (git-bash `/c/...` paths are treated as outside) recorded as a known limit; Claude Code sends native paths | delivery review |
| 2026-09-27 | Implemented: `repo_relative` in the hook helpers (anchors at `REPO_ROOT`, resolves, lexical fallback on a resolution error, case-folded containment and prefixes on a case-insensitive filesystem) now feeds `is_seed_prompt`, `is_framework_maintenance_surface`, `maybe_docs_lint` and `should_reindex` (the census found exactly these four prefix checks). Claude and Copilot post-edit mark or trigger the reindex before a lint failure returns; Cursor after-file-edit collects the gate verdict and reindexes before printing it. `launcher_command(fail_closed=True)` installs `sys.excepthook` exiting 2 and exits 2 on a missing root; selected from the PreToolUse event for Claude and explicitly at the Copilot pre-tool-use and Windsurf seed-protect render sites. Rendered hooks in this repository re-rendered. `RenderedEditHookPathTests` runs the real hook bodies and launchers in a temp repository; scratch mutants (raw prefix, unfolded containment, lint-before-mark, no fail-closed, outside-path reindex) each fail a test | `test_render_platform_surfaces`, scratch-tree mutants |
| 2026-09-27 | Readiness round 1 (one combined reviewer): blocked on F2, a case variant in the repository-root component still escapes a containment test that folds case only for the prefix (probed: `resolve()` keeps the variant casing and `relative_to` raises). Amended: containment is case-folded too and AC-1 names a root-component variant. Notes folded in: the reindex rule is every exit after an edit (Cursor warning gates, Windsurf has none), fail-closed covers every pre-edit launcher and catches `Exception` only, outside paths mark no reindex, resolution-failure wording, and the guard-rail threat model | readiness review |
| 2026-09-27 | Planned from RFC section 7 (B1, B2, B3). Verified with the MCP code tools: `is_seed_prompt` and `is_framework_maintenance_surface` use raw `startswith`; `claude_pre_edit_source` passes `detect_file_path` output unchanged; `claude_post_edit_source` returns on lint failure before `mark_reindex_pending_for`; `launcher_command` exits via `sys.exit(message)`. B1 observed live in this repository on 2026-09-26 | `code_read`, `code_keyword` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | One classifier in the shared helpers, used by every prefix check | Every host shares the helpers, so one fix covers all of them and a test can drive every check through one seam | Normalize in each hook body (repeats the logic per host); prefix-match absolute forms too (misses symlinks, `..` and case) |
| 2026-09-27 | Implement fail-closed with `sys.excepthook` rather than a `try` statement | A one-line `python3 -c` cannot hold `try`/`except`; the hook never sees `SystemExit`, so a body's own exit status passes through. It also sees `KeyboardInterrupt`, so an interrupted pre-edit hook blocks instead of warning, which errs toward closed; Requirement 3's "catches `Exception` only" is met for `SystemExit`, the case it exists to protect | `exec` of a multi-line string (fragile quoting under PowerShell) |
| 2026-09-27 | Fail closed only for PreToolUse, derived from the declared event | Exit 2 blocks the edit, which is the point; on Stop it would prevent the session from ending | Fail closed for every hook (breaks Stop); keep exit 1 (current bypass) |
| 2026-09-27 | Fall back to lexical normalization when resolution fails | A new file's parent may not exist yet, and a failed resolution must not make a guarded path look unguarded | Treat unresolvable paths as unguarded (fails open) |

## Risks

| Risk | Mitigation |
| --- | --- |
| The gates start blocking edits that were silently allowed | That is the intended fix; the gate messages already name how to open them |
| Case folding on a case-sensitive filesystem over-matches | Fold only when the filesystem at `REPO_ROOT` is case-insensitive |
| Rendered hook drift between this repo and targets | Re-render here; targets get it on upgrade |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
