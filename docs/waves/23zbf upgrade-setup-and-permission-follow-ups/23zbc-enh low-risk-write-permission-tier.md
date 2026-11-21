# Low-risk write permission tier for the rendered host allowlist

Change ID: `23zbc-enh low-risk-write-permission-tier`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 23zbf upgrade-setup-and-permission-follow-ups

## Rationale

A downstream team on a renaming distribution reported (field feedback on v1.46.0, item 9) that the rendered Claude Code settings allow only read-tier tools. Every checkbox mark, gardening run, index build and new plan record prompts. The only framework-owned relief is `wavefoundryAllowWriteTools`, which allows the whole write tier, so closes, gates, upgrades and cleanup stop prompting too. Teams that want fewer prompts therefore give up the host prompt on exactly the actions an operator most wants to see.

The operator accepted the evaluator's verdict on 2026-11-21: add an operator-set key that allows a named, framework-judged subset of the write tier, default off.

The same passage of seed 050 states a falsehood as a contract: "there is no per-tool opt-in". Hand-authored per-tool allow rules already survive every render (executed, see Progress Log). The seed is corrected here because the new key is documented in the same bullet.

## Product Intent

A team using Claude Code can set one committed key and stop being prompted for routine, bounded lifecycle bookkeeping (marking checkboxes, gardening, index builds, new plan records, the memory retrieval diagnostic) while every close, gate, upgrade, cleanup, review-evidence write and configured-command run still prompts. Before: all write tools prompt, or none do. After: a middle setting exists, the framework owns the judgment about which tools are in it, and the rules follow a distribution's tool renames. A repository that sets no key renders exactly what it renders today.

The first operator outcome is the rendered allowlist (AC-1 to AC-3, AC-5). Its mark tools depend on the writer protections in 23xlm. The seed correction (AC-8) ships with it because both edit one bullet. Whether prompts fall enough in practice is observable only after release: ask the reporting team in the next feedback round whether the set's tools stopped prompting and whether closes and gates still prompt.

## Requirements

1. **Named subset, no new tier value.** `mcp_tool_roster.py` defines `LOW_RISK_WRITE_TOOLS`, a frozenset of core tool names. `TIER_READ` and `TIER_WRITE` stay the only tier values and no `TOOL_TIERS` entry changes, so the pre-edit read exemption, the upgrade-in-progress guard and extension tier validation are untouched. The members are exactly these 16 core write-tier tools:
   1. `wf_mark_ac`, `wf_mark_task`
   2. `wf_garden_docs`
   3. `index_build`, `index_optimize`
   4. `wf_new_bug`, `wf_new_change`, `wf_new_documentation`, `wf_new_enhancement`, `wf_new_feature`, `wf_new_maintenance`, `wf_new_operations`, `wf_new_refactor`, `wf_new_task`, `wf_new_tech_debt`
   5. `wf_memory_eval`
2. **Admission rule.** The constant is the governing enumeration. A tool may be added later only when reading its handler in its writing mode shows all of the following, and the same change updates the pinned-membership test, the seed 050 list and the tool-surface list:
   1. its writes are confined to the derived index, a generated reference or module-index section, a bounded edit to an existing tracked record, or one new file that never replaces an existing one;
   2. every tracked write shows in `git diff` or `git status` and is undone by a Git restore or a file delete;
   3. it cannot change a lifecycle status, record review evidence, open or close an edit gate, remove retained work, run configured commands, start a service, or reload or upgrade the framework;
   4. it cannot write a host permission file or cause a permissions render.
3. **Served-name resolution.** One roster function returns the low-risk names a host can actually call, derived from `all_tool_tiers()` and the extension declaration, in this order:
   1. each member that the declaration does not replace contributes its own name;
   2. each member that the declaration replaces contributes its `alias_for_core` name, because the core behavior is served there, and the replaced core name drops out, because a distribution handler is served there;
   3. each declared alias whose canonical name is a member that is not replaced contributes the alias name, including an alias with fixed parameters;
   4. the result keeps only names present in `all_tool_tiers()` with the write tier, so a hidden canonical name is never returned;
   5. a new extension tool is never returned, and an alias of a tool outside the set is never returned.
   A member a distribution overrides through `EXTENSION_OVERRIDES` keeps its membership, consistent with an override keeping the core name and tier (Operator decision 2026-11-21: an overridden member keeps its membership). An invalid declaration raises through `all_tool_tiers()` before any name is returned, as it does for the existing rule functions.
4. **Rule derivation.** `allow_rules` and `tools_for_tiers` accept a second selector that adds the resolved low-risk names to the read tier. Calls without it return what they return today. When the write tier is selected the low-risk selector adds nothing, because the set is a subset of the write tier.
5. **Operator key.** The renderer reads a second operator-authored top-level key in `.claude/settings.json`, `wavefoundryAllowLowRiskWriteTools`, beside `wavefoundryAllowWriteTools`. The renderer only reads it and never writes it. It counts as set only when its JSON value is the boolean `true`, the same strict test the existing key uses. It lives outside the provenance key, outside workflow config and outside every rendered block. Absent or not `true` is the default and renders the read tier only.
6. **Render behavior.** `render_claude_permissions` selects the read tier, plus the low-risk names when the low-risk key is set, plus the whole write tier when the write key is set. The existing merge contract applies unchanged to the selected rules: emitted rules are claimed under `wavefoundryManagedAllow`; a claimed rule that is no longer selected is pruned; a selected rule that is present but unclaimed is operator-authored and is never claimed or removed. Clearing the low-risk key prunes the low-risk rules the renderer claimed on the next render unless the write key still selects them.
7. **Upgrade reporting.** The upgrade's count of already-present unmanaged rules (`_permissions_unmanaged_present` in `upgrade_wavefoundry.py`) selects rules exactly as the renderer does, from one shared selection so the two cannot diverge. The existing consent line already names every rule the render adds or removes, so low-risk rules appear there with no further change.
8. **Upgrade path for an existing install.** Nothing changes on upgrade for a repository that sets no key. To adopt the tier the operator adds `"wavefoundryAllowLowRiskWriteTools": true` to the committed `.claude/settings.json`; the next upgrade or `wf setup` renders and claims the rules and the consent line names them. An older framework ignores the key (executed), so setting it before upgrading is harmless. No migration, no new render entry point, and `wf_sync_surfaces` still never renders permissions.
9. **Seed 050 correction.** The permission-allowlist contract in seed 050 no longer says the mutating tier is all or nothing or that there is no per-tool opt-in. It states three levels: read tier by default; the low-risk key, with the member list and what stays prompting; the write key, with the existing warning. It states that a hand-authored per-tool allow rule is a supported per-tool opt-in that survives every render but gets no rename self-heal. The removal levers bullet names the low-risk key as the lever for a low-risk rule.
10. **Seed 160.** The upgrade checklist line that describes the rendered allow rules names both keys. The paragraph on who can trigger the render says an agent-triggered upgrade renders the read tier plus only what the operator's keys select, and that no low-risk tool can trigger a render.
11. **Project docs.** `docs/specs/mcp-tool-surface.md` documents the key, carries one enumerated list of the low-risk set, states the threat note below in the permission section, and rewords the "bounded to the read tier" sentence the same way as requirement 10. `docs/agents/platform-mapping.md` (the allowlist row and the render-boundary paragraph) and `docs/prompts/upgrade-wavefoundry.prompt.md` (the render paragraph) say the same. The renderer docstring and the roster module docstring describe the three levels.
12. **Platforms and hosts.** The change is a JSON merge with no platform-specific code path, so Windows, macOS, Linux and WSL2 behave identically; the settings file keeps its existing serialization. Only Claude Code has a rendered allowlist. Cursor, Codex, Copilot, Windsurf, Junie, Air, Warp and Antigravity receive nothing from this change; the docs say so.

## Scope

**Problem statement:** The rendered allowlist offers read-only or everything. Teams need a framework-owned middle level that follows tool renames, and seed 050 wrongly denies that per-tool rules work.

**In scope:**

- `LOW_RISK_WRITE_TOOLS`, its served-name resolution and the rule selector in `mcp_tool_roster.py`.
- The second key and selection in `render_platform_surfaces.py`; the matching selection in `upgrade_wavefoundry.py`.
- Seeds 050 and 160; the tool-surface spec; `docs/agents/platform-mapping.md`; `docs/prompts/upgrade-wavefoundry.prompt.md`.
- Tests for membership, resolution, rendering, pruning, upgrade reporting, the two handler properties the judgment rests on, and list equality between the constant, seed 050 and the spec.
- An Unreleased CHANGELOG bullet.

**Out of scope (each a recorded DECLINE):**

- A third tier value. DECLINE: the tier also drives the pre-edit read exemption (`render_platform_surfaces.py:1127`), the upgrade-in-progress guard (`wf_server/server_impl.py:21637`, `22575`) and extension validation (`mcp_tool_extensions.py:382`, `606`); a permission-only concern does not justify threading a value through them.
- `wf_pause_wave`, `wf_set_handoff`. DECLINE: both overwrite `docs/agents/session-handoff.md`, where operator waivers may be recorded, and each runs about once a session.
- `wf_scan_secrets`. DECLINE: it persists findings and a clean cache that gates read.
- `wf_review_wave`. DECLINE: its handler was not judged here and it is in the write tier; it keeps prompting.
- `memory_add`, `memory_propose`, `memory_validate`. DECLINE: durable, repository-visible records that steer later agents.
- `wf_run_sensors`, `wf_review_event`, `wf_context_efficiency_eval`, every lifecycle transition, both gates, `wf_upgrade`, `wf_cleanup_work`, `wf_sync_surfaces`, `wf_reload_mcp`, `wf_techdocs_baseline`, bulk memory tools and the four dashboard tools. DECLINE: command execution, evidence authority, operator checkpoints, surface or runtime rewrites, or process control.
- Reclassifying `wf_memory_eval` to the read tier. DECLINE: it would change the default allowlist and the pre-edit exemption, and the accepted verdict keeps the default unchanged (Operator decision 2026-11-21: `wf_memory_eval` stays in the write tier and joins the set).
- A way for a distribution to declare its own extension tools low-risk. DECLINE: the framework owns this risk judgment; a distribution or operator can hand-author rules, which survive every render.
- A free-form per-tool list key. DECLINE: it moves the risk judgment to each team; hand-authored rules already give that.
- Rendered allowlists for other hosts. DECLINE: no such renderer exists, and this change adds none.
- A low-risk field in the tool-surface golden or a Tool Index column. DECLINE: the pinned-membership test and the list-equality test are the oracles.
- Rewriting the existing write-tier enumeration in seed 050. DECLINE: unrelated to this change.

## Threat Note

Ship the 23xlm writer checks before granting the tier its two mark tools. These bounds describe the combined delivery. This change widens an allowlist only when an operator sets a key in a host-guarded file. With the key set, an agent can do the following without a host prompt:

| Tool | What it can write unprompted | Bound |
| --- | --- | --- |
| `wf_mark_ac`, `wf_mark_task` | Mark one checkbox complete or deferred in an editable spec of an open wave. A deferral may also write a visible rationale. | Both tools preserve archived history, terminal waves and individually completed specs in an open wave. Closing one spec leaves editable siblings open. The permission grants no close authority. The supplied task label must match exactly or name a unique prefix. Marking can switch a completed item to deferred and the reverse. Required AC deferrals need an explicit reason. A non-required AC or task may be deferred without one. The shared writer rejects multiline and markup-breaking reasons. |
| `wf_garden_docs` | Refreshes verification dates on changed docs and framework-owned manifest keys, and creates a missing handoff. | Takes no caller content. Rewriting a dated doc with malformed UTF-8 can replace invalid bytes. Gardening can start a background document-index refresh. |
| `index_build`, `index_optimize` | Maintain derived index state. A map build writes `docs/references/codebase-map.md` and updates the generated module block in `docs/repo-index.md` when its markers exist. | Map generation uses its own codebase-map lock. Builds consume CPU, disk and time. On a model-cache miss the embedding path may download a framework-selected public model. The model download does not send repository content. |
| Ten `wf_new_*` tools | One new plan file per call from the template, named by a minted id and a slug limited to lowercase letters, digits and dashes | Never replaces an existing file; `wf_new_feature` only refuses; a plan grants nothing until admitted and readied |
| `wf_memory_eval` | Nothing | Returns aggregate metrics only |

**Worst case.** An agent can mark work complete without doing it, or defer a criterion and alter its rationale without a host prompt. These actions change what the close checklist reports. An affected delivery approval that predates a new or changed deferral must be recorded again. Review evidence, closing, operator signoff, gate changes, configuration writes and command execution still require their existing authority. Repeated plan creation and index rebuilds can consume disk and compute. The tier does not grant arbitrary filesystem or network access.

**Why the risk is acceptable.**

1. Every tracked effect is visible in `git diff` or `git status` and is reversible there. The index is derived and rebuildable.
2. The checkpoints that turn a false mark into a false delivery still prompt: review evidence (`wf_review_event`), close (`wf_close_wave`, `wf_close_change`) and the gates. Close also needs current delivery approvals and the operator signoff, which a checkbox does not supply.
3. The tier cannot widen itself. No member writes the settings file or reaches a permissions render; `wf_upgrade` and `wf_sync_surfaces` are excluded, so the existing argument that an agent-triggered upgrade cannot allowlist the tool that triggered it still holds.
4. Default off, operator-authored, and narrower than the key teams set today. An operator can already hand-write any of these rules; the change adds no capability, only a maintained list.
5. The host rule is per tool, not per argument, so each member is judged on its writing mode.

**Residuals accepted.** Protection of the key is a host guarantee plus prompt policy, exactly as for the existing key. The no-overwrite property of the scaffolder rests on a unique minted id plus an existence check, not an exclusive create. A distribution override of a member is trusted to stay compatible.

## Acceptance Criteria

AC-1, AC-3 and AC-5 together test the intent: the middle level renders, stays narrow, and names tools the host actually serves.

- [x] AC-1: A test renders permissions into a settings file whose only key is `wavefoundryAllowLowRiskWriteTools: true` and asserts that `permissions.allow` holds exactly the read-tier rules plus the 16 low-risk rules, that `wavefoundryManagedAllow` equals that list, and that the rules for `wf_close_wave`, `wf_close_change`, `wf_open_gate`, `wf_close_gate`, `wf_upgrade`, `wf_cleanup_work`, `wf_review_event` and `wf_run_sensors` are absent. An implementation that ignores the key fails the first assertion; one that renders the whole write tier fails the last.
- [x] AC-2: The default is unchanged. A test asserts that a settings file with the key absent, `false`, the string `"true"` or the number `1` renders the read tier only, that the existing `ClaudePermissionsRenderTests` pass without edits to their assertions, and that an install-created settings file contains no low-risk key. An implementation that defaults on or coerces truthy values fails.
- [x] AC-3: A test exercises the key combinations and pruning:
  1. with both keys `true` the allowlist equals the whole-write-tier render;
  2. clearing the write key while the low-risk key stays `true` leaves exactly the read tier plus the low-risk rules;
  3. clearing the low-risk key prunes every low-risk rule the renderer claimed;
  4. a low-risk-named rule the operator hand-authored before any render stays in `permissions.allow`, stays out of `wavefoundryManagedAllow`, and survives clearing the key.
  An implementation that never prunes fails sub-point 3; one that claims operator rules fails sub-point 4.
- [x] AC-4: A test pins the membership of `LOW_RISK_WRITE_TOOLS`:
  1. it equals the 16 names in requirement 1;
  2. every member is a `TOOL_TIERS` key with the write tier;
  3. it shares no member with a separately stated never-list holding at least `wf_upgrade`, `wf_sync_surfaces`, `wf_reload_mcp`, `wf_open_gate`, `wf_close_gate`, `wf_close_wave`, `wf_close_change`, `wf_cleanup_work`, `wf_run_sensors` and `wf_review_event`;
  4. `TOOL_TIERS` values are still only `read` and `write`, and `wf_memory_eval` is still `write`.
  Adding a tool to the constant alone fails sub-point 1.
- [x] AC-5: A test applies a validated declaration that aliases one member and hides its canonical name, gives a second member an alias with fixed parameters, replaces a third member, declares one new write-tier extension tool, and aliases a tool outside the set. It asserts that the low-risk rules include the two aliases and the replacement's `alias_for_core` name; exclude the hidden canonical name, the replaced core name, the extension tool and the out-of-set alias; and name only tools present in `all_tool_tiers()`. It also asserts that an invalid declaration raises and yields no rules. An implementation that prefixes the constant's names directly fails: it emits a rule for the hidden name and the replaced handler and omits the aliases (executed against a prototype, see Progress Log).
- [x] AC-6: A test of the upgrade's permissions delta asserts that, for a settings file holding hand-authored low-risk rules, `unmanaged_present` counts them when the low-risk key is `true` and does not count them when it is absent. An implementation that leaves the upgrade's selection on the write key alone fails the first assertion.
- [x] AC-7: Tests pin the handler properties the membership judgment rests on, citing an existing test in the Progress Log where one already proves the property:
  1. for each mintable kind, a scaffolder call whose minted id names an existing plan file leaves that file byte-identical and reports `already_exists`;
  2. `wf_memory_eval` leaves the repository tree byte-identical on a run where the curated pass is available, not only on the unavailable path.
  3. Through the served mark tools, a valid mark writes one admitted spec. An unlisted spec, unsupported state and an ambiguous task prefix leave both target and neighboring specs unchanged. Link to 23xlm's passing tests for terminal waves, a completed member and its editable sibling in the same open wave, required deferral reasons and visible status-note boundaries before granting the tier.
  A scaffolder that writes before checking fails sub-point 1; an eval that persists a report fails sub-point 2.
- [x] AC-8: Seed 050 is corrected. A test extracts the tool names in seed 050's low-risk list and in the tool-surface spec's low-risk list and asserts each equals `LOW_RISK_WRITE_TOOLS`. A keyword search of `.wavefoundry/framework/seeds/` for "no per-tool opt-in" returns nothing, seed 050's permission contract no longer calls the mutating tier all or nothing, and the seed states that a hand-authored per-tool rule survives every render without rename self-heal. A seed that documents the key but keeps the false sentence fails the search; a list that omits a member fails the test.
- [x] AC-9: Every live passage that describes the allowlist levels or the agent-triggered render boundary agrees with requirements 9 to 12. The governing set is every file outside closed wave records, dated CHANGELOG history and memory records that names `wavefoundryAllowWriteTools` or says an agent-triggered render is bounded to the read tier: seed 050, seed 160, `docs/specs/mcp-tool-surface.md`, `docs/agents/platform-mapping.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, the renderer docstring and the roster docstring. Each names the low-risk key, and none still says the render is bounded to the read tier without the operator-key qualifier. The spec carries the threat note and the statement that only Claude Code has a rendered allowlist. The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `framework_edit_allowed` with `wf_open_gate` before the first script or test edit.
- [x] `mcp_tool_roster.py`: add `LOW_RISK_WRITE_TOOLS`, the served-name resolution function and the low-risk selector on `tools_for_tiers` and `allow_rules`; update the module docstring.
- [x] `render_platform_surfaces.py`: add the key constant beside `PERMISSIONS_WRITE_TIER_KEY`, read it in `render_claude_permissions`, expose one selection used by the renderer and the upgrade, and update the docstring's levels and render-boundary text.
- [x] `upgrade_wavefoundry.py`: make `_permissions_unmanaged_present` use the shared selection.
- [x] Tests in `test_render_platform_surfaces.py`: AC-1, AC-2, AC-3, AC-4.
- [x] Tests in `test_extension_tool_modules.py`: AC-5, with the declaration applied through the existing declaration test support.
- [x] Upgrade delta test for AC-6 beside the existing permissions delta tests; extend the install test that asserts the write key is absent to cover the low-risk key.
- [x] Handler property tests for AC-7, or cite existing ones in the Progress Log.
- [x] Close `framework_edit_allowed` with `wf_close_gate` when the script and test edits are done.
- [x] Open `seed_edit_allowed` with `wf_open_gate`; edit seed 050 (the permission-allowlist contract bullets, including the removal levers) and seed 160 (the allow-rules checklist line and the render paragraph); close `seed_edit_allowed` with `wf_close_gate` immediately after.
- [x] `docs/specs/mcp-tool-surface.md`: the key, the enumerated low-risk list, the threat note, the reworded render-boundary sentence, and the hosts statement.
- [x] `docs/agents/platform-mapping.md` and `docs/prompts/upgrade-wavefoundry.prompt.md`: mirror the seed wording by hand; rendering does not propagate seed prose.
- [x] List-equality test for AC-8 (seed 050 list and spec list against the constant), added under `framework_edit_allowed`.
- [x] Add an Unreleased `CHANGELOG.md` bullet that tells operators how to opt in, what stays prompting and that the default is unchanged, ending "Wave 23zbf / 23zbc.".
- [x] Run the touched test files with `run_tests.py --file`, then the same files with `--profile declared`, then the full `python3 .wavefoundry/framework/scripts/run_tests.py` last.
- [x] Run `wf_validate_docs` and fix failures in the documents this change edits.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| roster-and-renderer | implementer | none | Requirements 1 to 7 and AC-1 to AC-7; sequence the `upgrade_wavefoundry.py` edit with the sibling specs in this wave that touch that file |
| seeds | implementer | roster-and-renderer | Requirements 9 and 10 under `seed_edit_allowed`; the member list is copied from the constant |
| docs-and-changelog | implementer | seeds | Requirements 11 and 12, AC-8 list test, AC-9, CHANGELOG |
| security-review | security-reviewer | roster-and-renderer | Read-only lane; reviews the membership, the resolution rule and the threat note |


## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_roster.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/agents/platform-mapping.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`

The root-level changelog is also edited; it is named here in prose because a root-level file cannot be declared as a target.

## Affected Architecture Docs

N/A. The change adds a named subset and a second key inside the existing roster-to-renderer path. No module boundary, data or control path, or test seam moves, and no tier value is added. The permission contract and its threat statement live in `docs/specs/mcp-tool-surface.md` and seed 050, which this change updates. `docs/architecture/threat-model.md` does not cover the host allowlist today and gains nothing.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Proves the intent: the middle level renders and stays narrow. |
| AC-2 | required | The accepted verdict requires an unchanged default. |
| AC-3 | required | Clearing the key must remove what it added and never touch operator rules. |
| AC-4 | required | Security: the set cannot widen silently. |
| AC-5 | required | The reporter is a renaming distribution; rules must name served tools and never a replaced handler. |
| AC-6 | important | Keeps the upgrade's unmanaged count truthful when the key is set. |
| AC-7 | required | The membership judgment rests on these two handler properties. |
| AC-8 | required | Corrects a false contract in a shipped seed and keeps the lists equal. |
| AC-9 | important | The carriers must agree, and change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-21 | Readback: add the operator-selected Claude Code permission group after the mark writer protections pass. Default settings select reads. An explicit JSON true adds only the 16 reviewed tools or their served core aliases. Tools that close work or grant permissions still request approval. | AC-1 through AC-9 cover the roster, settings merge, upgrade report, handler contracts, tests and instructions. |
| 2026-11-21 | The stock and renamed permission checks passed, including invalid declarations, both keys together, removal of managed rules, preservation of manual rules and upgrade counts. A forced collision on every mintable kind preserved the existing plan. The available memory evaluation left its scratch repository byte-identical. | ClaudePermissionsRenderTests, LowRiskDeclaredToolsTests, PermissionsRenderConsentTests, AutoLintAtMcpGatesTests and MemoryEvalTests. The 23xlm writer tests passed before the new permission group was enabled. |
| 2026-11-21 | Planned. Retrieval note: the semantic index reported `index_not_ready`, so files were read directly and searched with exhaustive text search. | `seed_get` returned `index_not_ready` |
| 2026-11-21 | Executed: roster census. 93 core tools, 44 read, 49 write; the 16 proposed names are all write tier; 33 write-tier tools keep prompting. | `.wavefoundry/work/23zbf/planning/23zbc/probe_roster.py` |
| 2026-11-21 | Executed: resolution prototype under a declaration with an alias plus hidden canonical, a pinned alias, a replacement and an out-of-set alias. The rule returns the aliases and `alias_for_core`, drops the hidden and replaced names, and every name is served. The known-bad direct-prefix form emits `wf_mark_ac` (not served) and the replaced `wf_garden_docs`, and omits three served names. | `probe_roster.py` output |
| 2026-11-21 | Executed: a hand-authored `mcp__wavefoundry__wf_mark_ac` rule survives two renders unclaimed, and no other write rule renders. The proposed key is inert under today's renderer (file bytes unchanged). | `.wavefoundry/work/23zbf/planning/23zbc/probe_handlers.py` |
| 2026-11-21 | Executed: each of the nine mintable kinds creates exactly one new file and changes no existing file; `feat` refuses and writes nothing; a forced id collision returns `created: false` with `already_exists` and leaves the tree byte-identical (status `ok`, not an error); slugs with `/`, `..`, uppercase, a space or empty are refused with nothing written. All ten wrappers call one shared path (read). | `probe_handlers.py` output; `wf_server/server_impl.py:9442-9617`, `26044-26197` |
| 2026-11-21 | Executed on the unavailable path only: `wf_memory_eval` leaves an empty-corpus tree unchanged. Inferred from reading for the available path: `run_curated` and its ranking helpers contain no write call and the tool is registered read-only. AC-7 sub-point 2 closes this gap. | `memory_eval.py:869-992`; `wf_server/memory_handlers.py:2286` |
| 2026-11-21 | Inferred from reading, not executed: the marker handler writes only the mark and an optional one-line note and accepts only `x` or `~` (`server_impl.py:7909-8185`); the gardener writes date stamps, framework-owned manifest keys and a missing handoff stub (`docs_gardener.py:337-520`); `index_build(content='map')` regenerates the tracked codebase map, so the evaluator's "gitignored index only" is corrected; the gardener date line is masked from the review-policy digest (`gardener_metadata.py:13-23`). | file reads |
| 2026-11-21 | Inferred from a text census, not a call-graph proof: only `setup_wavefoundry.py:110` and `upgrade_wavefoundry.py:2249`, `2361` pass the permissions switch, and no handler module of a set member names the renderer, setup or upgrade scripts as something it runs. | exhaustive text search for the switch and script names |
| 2026-11-21 | Inferred: when the key is set before the installing upgrade, that upgrade's fresh-code backstop renders the rules. This follows the existing seed 160 description of the backstops and was not executed. | seed 160 line 410 |
| 2026-11-21 | Census of live carriers of `wavefoundryAllowWriteTools` (exhaustive text search over `.py`, `.md`, `.json`, `.toml`, excluding closed wave records, CHANGELOG history and one memory record): seed 050, seed 160, the tool-surface spec, `platform-mapping.md`, `upgrade-wavefoundry.prompt.md`, the renderer, the upgrade script, the roster docstring and tests. No parked plan overlaps (evaluator's check, not repeated). | text search |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-21 | Selected: a named subset of the write tier plus a second operator key. | It leaves every tier consumer untouched, keeps the default, and lets the framework own the risk judgment and the rename handling. | Third tier value: must be threaded through the pre-edit exemption, the upgrade guard, extension validation, the tool golden and the Tool Index for a permission-only concern. Zero code (seed fix plus a hand-paste list): no rename self-heal and wrong names for a renaming distribution, which is the reporter's case. Free-form per-tool list key: moves the risk judgment to each team, and non-obvious cases such as `wf_run_sensors` are easy to get wrong. |
| 2026-11-21 | Mechanism efficacy. Replay: the reporter sets the key, the next render adds rules under its served names, and marks, gardening, index builds and new records stop prompting while closes, gates, upgrades and cleanup still prompt; the rename case was replayed in the prototype. The mechanism controls the rendered rules and the host enforces them; it is opt-in, so seed 050 and the CHANGELOG bullet are what make an operator act. It misses frequent tools left out on purpose (`wf_review_wave`, `wf_pause_wave`), so relief is partial. Hand-authored rules give one team most of the value but no self-heal. Measured after release by asking the reporter whether set tools stopped prompting and closes still prompt, and by the absence of reports of a rule naming an unserved tool. | Required by Plan spec for a new mechanism. | n/a |
| 2026-11-21 | Tool set: the evaluator's 16 unchanged. Two of its reasons are corrected: `wf_garden_docs` also reconciles manifest keys and creates a missing handoff stub; `index_build` can regenerate the tracked codebase map. Neither takes caller content or replaces operator content, so both stay in. | Each handler was read; the scaffolder and renderer claims were executed. | Dropping `wf_new_feature` (it only refuses): kept, so the redirect to `wf_new_enhancement` arrives without a prompt. |
| 2026-11-21 | The operator chose to keep the opt-in tier and ship all three mark-integrity checks under 23xlm first. | Its writer had allowed edits under a live root after closure, missing required rationales and structurally unsafe note text. The revised Threat Note names the remaining effects and the separate dependency. | A documentation-only repair and dropping the tools were declined. |
| 2026-11-21 | Operator decision 2026-11-21: `wf_memory_eval` stays in the write tier and joins the set. | It persists nothing, but moving it to read changes the default allowlist and the pre-edit exemption, which the verdict rules out. | Reclassify to read: declined by the operator. |
| 2026-11-21 | A replaced member drops out and its `alias_for_core` joins. Operator decision 2026-11-21: an overridden member keeps its membership. | A replacement serves an incompatible distribution handler under the core name; an override keeps the core name and tier by contract. | Drop overridden members too: declined by the operator. |
| 2026-11-21 | Key name `wavefoundryAllowLowRiskWriteTools`, strict boolean `true`. | Mirrors the existing key and its test. | A list-valued key: declined above. |
| 2026-11-21 | No operator questions remain open. The two questions raised at planning (membership of an overridden member; the tier of `wf_memory_eval`) are settled by the operator decisions recorded in the two rows above, as relayed by the wave coordinator. | Both change what renders, so each needed an operator answer. | n/a |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The set widens later without review. | AC-4 pins membership and a never-list; AC-8 ties the seed and spec lists to the constant; requirement 2 states the admission rule. |
| A rule names a tool the distribution does not serve, or allows a replaced handler. | Requirement 3 and AC-5, with the known-bad form executed. |
| An agent marks work complete that was not done. | Accepted and stated in the threat note; review evidence, signoff and close still prompt. |
| A later handler change makes a member unsafe (for example a scaffolder that overwrites). | AC-7 pins the handler properties; the admission rule applies to changes as well as additions. |
| Prose carriers drift from the constant. | One enforced list in the seed and one in the spec; other passages name the key and point at them. |
| `upgrade_wavefoundry.py` is edited by sibling specs in this wave. | The edit is one function; sequence it per the execution graph. |
| Operators read "low-risk" as "no risk". | The seed and spec state the worst case in plain words beside the key. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
