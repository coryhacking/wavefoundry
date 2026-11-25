# Migrate spec-tool permissions during upgrade

Spec ID: `24ax3-enh migrate-spec-tool-permissions-during-upgrade`
Spec Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: 24buu memory-revalidation-upgrade-delivery

## Rationale

Wave `248o5` (change `248o6`) renamed the five stock tools `wf_new_change`, `wf_get_change`, `wf_add_change`, `wf_remove_change` and `wf_close_change` to `wf_*_spec`. To keep each operation's permissions, the server withholds a new name while host policy it can read names the old one without an equivalent rule (`spec_tool_permissions.assess`). On an installation whose live `.wavefoundry/install-log.md` lacks `Initial MCP vocabulary: spec-tools-v1`, the server also withholds every new name until the operator records a per-tool review with `upgrade_wavefoundry.py spec-permissions --tool <name> --confirm-effective-host-rules` (`_review_held`). Upgrade reports the holds (`spec_tool_permission_holds` in the summary, `Withheld renamed tool:` lines) but resolves none of them.

Replayed on this repository on 2026-11-24: after the 248o5 code loaded, all five spec tools were withheld, two by exact-name allow rules in `.claude/settings.local.json` and all five by the missing review. The 24buu upgrade rehearsal (`.wavefoundry/work/24buu/upgrade-rehearsal.md`, items 2, 3 and 8) found the same on a 1.51.0 installation, plus a framework-managed `wf_get_change` allow rule left in `.claude/settings.json`. Every installation that predates 248o5 meets this lockout after upgrading to 1.52.0. The operator asked that "wf upgrade just does this so it's standard part of the upgrade" (2026-11-24).

## Product Intent

**Beneficiaries:** operators who upgrade an existing installation to 1.52.0, and the agents that plan, admit and close specs there.

**Before:** after upgrading, the spec tools are missing until the operator edits the host settings, runs five review commands and restarts the host.

**After:** upgrade copies each exact old-name permission rule in the repository's own host settings to the new name, with the same category and constraint, re-renders the managed rules, and records an upgrade verification for each tool that no readable policy layer still restricts. After the usual post-upgrade restart the spec tools are available with the same allow, ask and deny behavior as before. A tool that a user-level or enterprise layer denies or asks for under its old name stays withheld, and the summary names the file and the exact rule to add there; upgrade changes nothing outside the repository.

**Teammates:** a teammate who pulls the upgraded repository gets the same result from `wf setup`, which runs the same steps on their machine. After a pull, setup readiness (`index_health` `setup_readiness`, `wf setup --check`) reports withheld spec tools with `wf setup` as the remedy, so the agent's existing post-pull check finds it (operator direction, 2026-11-24: "don't we suggest that wf setup run after git update").

**What a target sees on the installing hop:** the summary lines this code prints and the withheld-tool remedies. Seed 160's revised guidance reaches a target's upgrade prompt only on its next upgrade.

**Boundaries:** upgrade and setup write only host settings inside the checkout, and reads user-level and enterprise settings without writing them (operator decision, 2026-11-24). It never widens a grant: it copies existing rules, adds none, and never serves a tool that a readable layer restricts under its old name without the same restriction on the new name. A file it cannot parse is left byte-identical and its tool stays withheld with today's remedy.

AC-1, AC-2, AC-4 and AC-5 establish the intent: an upgraded legacy fixture exposes the spec tools with deny and ask preserved and no operator command, and a tool restricted outside the repository is never served unrestricted.

## Requirements

1. **Where it runs.** The migration, verification and managed-rule render run whenever `render_platform_surfaces.py` runs with `--include-permissions`, in this order: migrate repository rules, write verification receipts, render managed rules. The 1.51.0 upgrade orchestrator launches that child with exactly `--repo-root <root> --include-permissions --manifest <path>` from the freshly extracted code, before the docs gate and the index, so no new flag is needed on the installing hop. `wf setup` launches the same child (`setup_wavefoundry._run_render_platform_surfaces`) and therefore runs the same steps; that is the teammate path. The permissions-only backstop (`--include-permissions --permissions-only`, in `--update-index` and `phase_cleanup`) runs the same steps idempotently, and the migration runs whether or not the Claude platform render is selected.
2. **Repository rule migration.** For each stock route in `mcp_tool_extensions.stock_spec_routes()`:
   1. `.claude/settings.json` and `.claude/settings.local.json`: in each of `permissions.allow`, `ask` and `deny`, a rule whose tool pattern is exactly `mcp__wavefoundry__<old>`, with or without a `(constraint)`, gets `mcp__wavefoundry__<new>` with the identical constraint in the same list, unless that rule is already present. The old rule is kept. Framework-managed entries in `.claude/settings.json` stay owned by the permissions render (requirement 6).
   2. `.codex/config.toml`: for the Wavefoundry server entry, an old name in `enabled_tools` or `disabled_tools` gets the new name in the same list, and a `tools.<old>` table is copied to `tools.<new>` when `tools.<new>` is absent. The edit inserts text without re-serializing, so comments survive.
   3. A pattern rule that matches the old name but not the new name (for example `mcp__wavefoundry__wf_*_change`) is not rewritten; the route stays held with today's remedy.
3. **Constraint equivalence.** `spec_tool_permissions.assess` treats an old rule with a constraint as satisfied when the same list holds the new name with the identical constraint. Today any constrained old rule holds the new name.
4. **Separated holds.** `assess` reports repository-rule holds, outside-layer holds (requirement 5) and the review hold separately, so callers can tell why a route is held. Existing callers that want one combined result keep it.
5. **Outside layers, read-only.** Upgrade and setup read, never write, the user-level Claude settings (`$CLAUDE_CONFIG_DIR/settings.json`, else `<home>/.claude/settings.json`), the Codex user config (`$CODEX_HOME/config.toml`, else `<home>/.codex/config.toml`), and the Claude enterprise managed-settings file at its documented path for the platform (macOS `/Library/Application Support/ClaudeCode/managed-settings.json`, Linux and WSL2 `/etc/claude-code/managed-settings.json`, Windows `C:\ProgramData\ClaudeCode\managed-settings.json`), when present. `<home>` is `HOME`, else `USERPROFILE`, else `Path.home()`. All of these paths resolve through one function, which also honors `WAVEFOUNDRY_MANAGED_SETTINGS_PATH` as an override of the enterprise path, so a test and the subprocess render child can be isolated from the real machine. Each layer is read with the semantics the repository reader already applies:
   1. Claude files use the `_claude` matcher, so a pattern rule that matches the old name but not the new one, in `deny` or `ask`, holds the route.
   2. The Codex file uses the `_codex` rules, so an old name in `disabled_tools`, or a `tools.<old>` table without an equal `tools.<new>`, holds the route.
   3. A file is read following symlinks, read-only. A file that exists but cannot be read or parsed (including a byte-order mark the parser rejects) holds every route whose old name appears in its text, as `assess` already does for Cursor settings.
   A `deny` or `ask` restriction on an old name without the same rule on the new name holds that route, and the summary prints one line naming the resolved file path, the category and the exact new rule to add. An `allow` rule on an old name holds nothing and gets the same one-line recommendation.
6. **Managed rules.** After the migration, the same child renders the framework-managed allow rules, so `.claude/settings.json` holds the new names in the same upgrade.
7. **Upgrade verification.** For each route with no repository or outside-layer hold after the migration, upgrade writes a receipt at the existing per-tool path and scope (workstation, user, absolute checkout) whose body states that upgrade verified the repository and readable user-level and enterprise layers. `_review_held` accepts that body and the existing operator body. A route with any other hold gets no receipt. A valid existing receipt, operator or upgrade, is left unchanged. The receipt body lists the files it read. The summary lists migrated rules, verified tools, remaining holds and the resolved outside-layer paths.
8. **Write fidelity.** Each repository file is rewritten only when a rule is added: atomically, keeping key order, indentation and line endings, through the framework's contained-write helpers. A repository file that fails to parse, is a symlink or resolves outside the checkout is not written, and its routes stay held with the existing remedy. After the Codex text insertion, the file is parsed again with `tomllib` and must differ from the original only by the added names and tables; otherwise the original bytes are kept and the routes stay held.
9. **Idempotence.** A second run, including the backstop in the same upgrade, changes no byte and rewrites no receipt.
10. **Guidance.** Seed 160's section "MCP tool names for change specs" (anchor `#mcp-tool-names-for-change-specs`, linked from the CHANGELOG) is revised in place, keeping its heading and anchor, and the same text is applied to `docs/prompts/upgrade-wavefoundry.prompt.md` outside its renderer-owned regions. It says that upgrade and `wf setup` migrate repository rules and record the verification, that outside-layer recommendations are applied by the operator, and that the `spec-permissions` command remains the remedy when a hold remains (a pattern rule, a malformed file, Cursor settings, or policy the upgrade cannot read, such as MDM profiles, the Windows registry, server-managed settings or host launch flags). The sentence telling the agent to run `spec-permissions` for each reviewed tool on every existing installation is removed.
11. **Platform behavior.** The enterprise path is resolved per platform (macOS, Linux and WSL2, Windows); home and environment overrides use `Path.home()` and `os.environ`; writes use the atomic replace the framework already uses on Windows. On WSL2 the user-level files are the Linux home's.

## Scope

**Problem statement:** upgrading an existing installation withholds the renamed spec tools until the operator performs manual permission steps.

**In scope:**

- The migration, constraint equivalence, separated holds, outside-layer reads and recommendations, managed-rule render, upgrade verification receipt, summary lines and tests.
- Seed 160 and its self-hosted prompt copy.
- A `CHANGELOG.md` `[Unreleased]` entry that also names the remaining manual cases.

**Out of scope:**

- Writing any file outside the checkout.
- Cursor `.cursor/settings.json`: no framework writer exists for it, so a matching token still holds the tool with today's remedy.
- Removing the old-name rules, which name no served tool.
- The other specs in this wave (`24but-enh deliver-memory-revalidation-through-upgrade`, `24bn7-bug release-zip-entry-missing-contained-files`, `24bn8-enh replace-unedited-lifecycle-prompts-during-upgrade`, `24bn9-enh cli-upgrade-runs-cleanup`).

## Acceptance Criteria

- [x] AC-1: On a legacy-install fixture (no `spec-tools-v1` line) whose `.claude/settings.local.json` allows `mcp__wavefoundry__wf_add_change` and `mcp__wavefoundry__wf_get_change`, whose `.claude/settings.json` has `mcp__wavefoundry__wf_remove_change` in `deny` and `mcp__wavefoundry__wf_close_change(mode=dry_run)` in `ask`, and whose `.codex/config.toml` (with a comment line) lists `wf_new_change` in `disabled_tools`, running the Phase 1 permissions render child adds `wf_add_spec` and `wf_get_spec` to the local allow list, `wf_remove_spec` to `deny`, `wf_close_spec(mode=dry_run)` to `ask` and `wf_new_spec` to `disabled_tools`, keeps the comment, and leaves `spec_permission_holds(root)` empty with five upgrade-verification receipts. Known bad: today's code adds nothing and holds all five.
- [x] AC-2: On the AC-1 fixture after migration, for each new name the rules in each layer match its old name's rules category for category and constraint for constraint (a table comparison over allow, ask and deny), and no new name appears in a list its old name was not in.
- [x] AC-3: A malformed `.claude/settings.local.json` holding an old name is left byte-identical, its routes stay held with the existing remedy, and no receipt is written for them; the other files still migrate.
- [x] AC-4: With `HOME`, `USERPROFILE`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME` and `WAVEFOUNDRY_MANAGED_SETTINGS_PATH` all pointed at temporary folders, each of these outside-layer cases holds the named route, writes no receipt for it, prints a recommendation naming the resolved file, and leaves the outside files byte-identical, while the other routes are verified: (1) a user-level Claude `deny` on `mcp__wavefoundry__wf_close_change`; (2) a user-level Claude `deny` pattern `mcp__wavefoundry__wf_*_change` (holds all five); (3) a Codex user config with `wf_remove_change` in `disabled_tools`; (4) a user-level Claude file that is a symlink to a file denying `wf_close_change` (followed); (5) a user-level Claude file holding `wf_get_change` that fails to parse (holds `wf_get_spec`); (6) an enterprise managed-settings fixture with `ask` on `wf_add_change`. No test reads the real home or system paths. Known bad: serving the new name because the outside restriction never matched it, or because the file was skipped.
- [x] AC-5: A pattern rule `mcp__wavefoundry__wf_*_change` in `deny` leaves every route it matches held with no receipt, and the file unchanged.
- [x] AC-6: An end-to-end upgrade test on a legacy fixture, through the existing upgrade test harness, finishes with the cleanup summary's `spec_tool_permission_holds` empty, no `Withheld renamed tool:` line, and `.claude/settings.json`'s managed allow list naming `wf_get_spec` and not `wf_get_change` with no self-healing flag. Known bad: today's code prints five such lines and keeps the old managed rule.
- [x] AC-7: Running the child twice leaves every repository file and receipt byte-identical after the first run.
- [x] AC-8: Seed 160's "MCP tool names for change specs" section and the self-hosted copy state requirement 10, keep the heading and anchor, and no longer contain the per-tool `spec-permissions` instruction for every existing installation; a text test pins both the new text and the absence of the old sentence (known bad: today's section). `CHANGELOG.md` has an `[Unreleased]` entry naming this wave and change, the remaining manual cases, the teammate `wf setup` path, and that outside layers are read, not changed.
- [x] AC-9: A repository `.claude/settings.local.json` that is a symlink, and one that resolves outside the checkout, holding an old-name allow rule, are not written; their routes stay held with the existing remedy and no receipt is written for them.
- [x] AC-10: Driving `render_platform_surfaces.py` as a subprocess with exactly the 1.51.0 orchestrator argv (`--repo-root <root> --include-permissions --manifest <path>`) on the AC-1 fixture, with the isolation of AC-4, produces the AC-1 result; driving it through `setup_wavefoundry._run_render_platform_surfaces` on a fresh clone of the migrated fixture with no receipts writes the receipts for that clone's workstation scope.
- [x] AC-11: After a pull, setup readiness (`setup_readiness` as reported by `index_health` and `wf setup --check --json`) reports a reason for withheld spec tools whose recommended action is `wf setup`, and reports nothing for them once `wf setup` has run.
- [x] AC-12: A `.codex/config.toml` with a comment and a `[mcp_servers.wavefoundry.tools.wf_get_change]` table gains an equal `wf_get_spec` table and keeps the comment; the re-parsed file differs from the original only by that table.

## Tasks

- [x] `spec_tool_permissions.py`: separated holds, constraint equivalence, the repository migration, the outside-layer reader, the upgrade-verification body and a receipt writer shared with `acknowledge`.
- [x] `render_platform_surfaces.py`: run migration, managed render and verification in the `--include-permissions` path; summary data.
- [x] `upgrade_wavefoundry.py`: surface the migrated, verified and held lines in the summary; keep the backstop idempotent.
- [x] `setup_readiness.py`: report withheld spec tools with `wf setup` as the recommended action.
- [x] Tests in `tests/test_spec_tool_permissions.py` for AC-1 to AC-5 and AC-7 with temporary roots, home and environment; an end-to-end case in `tests/test_upgrade_wavefoundry.py` for AC-6.
- [x] Seed 160 (under `seed_edit_allowed`) and the self-hosted prompt copy; text pin; changelog.
- [x] Per-file `--profile second` on touched tests; full default suite with `--no-cache` last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| permissions-core | implementer | — | Requirements 2 to 5, 7 to 9 |
| render-wiring | implementer | permissions-core | Requirements 1 and 6, AC-6 |
| guidance | implementer | — | Requirement 10, AC-8 |

## Serialization Points

- `.wavefoundry/framework/scripts/spec_tool_permissions.py`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/setup_readiness.py`, `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_spec_tool_permissions.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/architecture/data-and-control-flow.md`, `docs/architecture/threat-model.md`
- The root `CHANGELOG.md` entry.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md`: the upgrade and setup permission flow gains the repository rule migration, the outside-layer read and the upgrade verification receipt.
- `docs/architecture/threat-model.md`: upgrade and setup now read user-level and enterprise settings outside the checkout (read-only) and write verification receipts that make the server serve renamed tools.

Security review is requested because the change writes host permission files and records verification receipts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The migration itself, including deny and ask. |
| AC-2 | required | No grant is widened inside the repository. |
| AC-3 | required | A bad file is never rewritten. |
| AC-4 | required | Outside restrictions are honored and never written. |
| AC-5 | required | Pattern rules cannot be bypassed. |
| AC-6 | required | The operator-visible outcome. |
| AC-7 | required | Both runs in one upgrade are safe. |
| AC-8 | required | Guidance and release notes. |
| AC-9 | required | Symlinked or outside repository files are never written. |
| AC-10 | required | The installing hop and the teammate path both run it. |
| AC-11 | required | Teammates are pointed at the remedy. |
| AC-12 | required | Codex tables migrate without losing comments. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned for wave `24buu`; managed-rule render added from the upgrade rehearsal (item 3). | `.wavefoundry/work/24buu/upgrade-rehearsal.md` |
| 2026-11-24 | Revised before readiness approval from the red-team primer: outside-layer deny and ask now hold the route (F1), holds are separated (F2), the receipt has an upgrade body, the work runs in the Phase 1 render child (F5), pattern-rule and redirected-config cases added, ACs reworded (F10, F13, F14). | `.wavefoundry/work/24buu/readiness/red-team.md` |
| 2026-11-24 | Bounded readiness repair (cycle 1) for SEC-1, QA-4, QA-5, AR-2, AR-3, DC-1 and DC-4: outside layers use the repository reader's semantics, follow symlinks and hold on unparseable files; paths resolve through one isolatable function; `wf setup` runs the same steps (operator direction) and setup readiness points teammates at it; the verbatim 1.51.0 argv, symlink refusal and Codex table copy are tested; the seed section is revised in place; architecture docs named. | `.wavefoundry/work/24buu/readiness/repair-1.md` |
| 2026-11-24 | Readback: the `--include-permissions` render child (upgrade Phase 1, its permissions-only backstop, `wf setup`) migrates exact old-name rules in `.claude/settings.json`, `.claude/settings.local.json` and `.codex/config.toml`, then writes upgrade-verification receipts for routes no repository or readable outside layer holds, then renders managed rules; outside layers are read only; setup readiness reports what setup would still change. ACs 1 to 12. Scope: no write outside the checkout, no Cursor writer, old rules kept. Expected files: `spec_tool_permissions.py`, `render_platform_surfaces.py`, `upgrade_wavefoundry.py`, `setup_readiness.py`, the two named test files, seed 160 and its copy, CHANGELOG, the two architecture docs. | `memory_brief(pre_implementation)`: no `needs_reverification` advisory |
| 2026-11-24 | Implemented. `spec_tool_permissions.py`: `assess_layers` (repository, outside and review holds separately; `assess` keeps the combined result), constraint equivalence (the same rule with its constraint must name the new tool), `outside_layer_paths` (one function; `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `HOME`/`USERPROFILE`/`Path.home()`, `WAVEFOUNDRY_MANAGED_SETTINGS_PATH`), `_read_outside` (non-blocking open, follows links, refuses special files and files over 4 MiB), `migrate_repository` (JSON keeps key order, detected indentation and line endings; Codex text insertion re-parsed with `tomllib` and kept only when it equals the original plus the additions), `record_verification` (upgrade body lists each checked file and whether the managed-settings override was set; a valid operator or upgrade receipt is left unchanged), `setup_pending`, shared `_write_receipt`. Render child: `migrate_spec_tool_permissions` runs before `render_codex_mcp_config` and `render_claude_permissions`, outside the Claude-platform gate, in both the full and `--permissions-only` paths, fail-safe; prints migrated, verified, withheld, recommendation and outside-layer lines. Upgrade summary adds recommendations and outside layers. `setup_readiness`: reason `spec_tools_withheld` with the setup action; the three policy inputs join the assessment signature (lstat, so a link cannot make readiness indeterminate). | `.wavefoundry/work/24buu/impl/24ax3/` |
| 2026-11-24 | Deviations: (1) Windows enterprise path reads both `C:\ProgramData\ClaudeCode\managed-settings.json` (spec) and `C:\Program Files\ClaudeCode\managed-settings.json` (current Claude Code), read-only. (2) Equivalence accepts the exact new rule beside a pattern rule (`wanted in rules`), so the recommended rule actually lifts the hold; the migration still never rewrites a pattern (AC-5). (3) Test isolation: `run_tests.py` sets `CLAUDE_CONFIG_DIR`, `CODEX_HOME` and `WAVEFOUNDRY_MANAGED_SETTINGS_PATH` to a never-created path for every worker, and the touched tests set all five variables to temporary folders; readiness fixtures (`tests/setup_ready_fixture.py`, `tests/test_setup_readiness.py` setUp) now carry a fresh-install log; `tests/fixtures/line-ending-census.json` reclassifies the receipt writer and the migration write. (4) An unquoted zsh argument list turned one focused run into a full default run (13596 tests, OK); later edits supersede that receipt. Gapfill: shell `sed`/`grep` for long-file line ranges and Python edit scripts for multi-site replacements. | `.wavefoundry/work/24buu/impl/24ax3/affected-1.txt` |
| 2026-11-24 | Landing mutants (scratch copy, `mutants.txt`): outside allow holds (killed by `test_outside_allow_only_recommends...`); special-file check removed (`test_outside_special_file...`); read size cap removed (`test_outside_file_over_the_size_cap...`); Codex `disabled_tools` only recommends, unparseable token hold removed, receipts written despite holds (`test_ac4...`); receipt line check removed and override line dropped (`test_outside_allow_only_recommends...`); managed allow copied, migration removed from the full path, migration moved after the managed render (`SpecToolPermissionUpgradeTests`); Codex re-parse skipped (`test_codex_insertion...`); backstop skips migration (`test_permissions_only_backstop...`); readiness reason removed (`SpecToolReadinessTests`); signature inputs removed (`test_policy_inputs_are_in_the_assessment_signature`); old constraint semantics (`test_constraint_equivalence...`); Program Files path dropped (`test_outside_paths_resolve...`); valid receipt rewritten (`test_existing_operator_receipt...`); runner isolation removed (`test_runner_isolates_host_policy_locations`, in-repo run then restored). All killed. Default and `--profile second` per file: `test_spec_tool_permissions.py` (29), `test_setup_readiness.py` (59), `test_line_ending_census.py` (16), `test_upgrade_wavefoundry.py` (768) all OK. | `.wavefoundry/work/24buu/impl/24ax3/final-*.txt`, `mutants.txt`, `m18.txt` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Upgrade migrates permissions and records the verification. | Operator: "we need to fix this so wf upgrade just does this so it's standard part of the upgrade". | Keep the manual review: declined by the operator. |
| 2026-11-24 | Write only repository settings; read user-level settings and recommend. | Operator: "let's just update the local repository, we could read and recommend user level settings, but don't change them". | Ignore user-level files; write user-level files. |
| 2026-11-24 | `wf setup` runs the same migration and verification, and setup readiness reports withheld spec tools with `wf setup` as the remedy. | Operator: "don't we suggest that wf setup run after git update" (2026-11-24), on how teammates' machines get the tools. | Check at server start; one command per machine; a committed marker. |
| 2026-11-24 | An outside-layer deny or ask on an old name holds the new name; an outside allow only recommends. | Planner default after red-team F1: serving a tool the user denied under its old name widens a grant, which the Boundaries forbid; holding it keeps "don't change them" and still recommends the fix. | Recommend only (the earlier planner reading): widens a denied tool. |
| 2026-11-24 | Selected: copy exact-name rules in the Phase 1 permissions render child, then write an upgrade-verification receipt per unheld route. Efficacy: replaying this repository and the rehearsal, the child adds the missing rules, re-renders the managed rule and verifies all five tools before the docs gate, on the CLI and MCP paths alike. It controls the outcome. It cannot see host launch flags or unreadable policy, which the guidance names. `assess` already finds the rules and `acknowledge` already writes the receipt. Measured after release by whether upgraded projects report `Withheld renamed tool:` lines. | Planner default. | Run in cleanup: on the 1.51.0 CLI path cleanup is a manual step and runs after the docs gate. Drop the receipt requirement: loses the outside-layer check. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Policy the upgrade cannot read (host launch flags, a managed policy at a nonstandard path) restricts an old name. | The receipt body says what upgrade verified; guidance names the `spec-permissions` command for that case. |
| Rewriting a host settings file loses formatting. | JSON keeps order and indentation; the Codex edit inserts text and is tested on a commented file. |
| Two sessions upgrade the same checkout. | The upgrade already holds its lock; the child runs inside it. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
