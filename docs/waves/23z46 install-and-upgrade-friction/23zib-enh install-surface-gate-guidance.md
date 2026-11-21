# Install surface gate guidance, independent CLAUDE.md bridge and manifest example

Change ID: `23zib-enh install-surface-gate-guidance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-20
Wave: 23z46

## Rationale

Field feedback on 1.46.0 (item 7 in `.wavefoundry/work/23z45/field-feedback-v1.46.0.md`) reported three install-surface defects. Each was checked against the tree on 2026-11-20 and all three premises hold:

1. **The install gives no gate guidance, and the hook message points at the file instead of the tool.** Phase 1 setup renders the pre-edit hooks. Phase 2 then asks the agent to write `AGENTS.md` (row 2.5) and `docs/prompts/` (row 2.9), which the hook guards. The install log template and seeds 010, 011 and 012 never mention an edit gate. The block message says the edit "requires `.wavefoundry/guard-overrides.json` with `framework_edit_allowed.enabled: true`", which invites the agent to edit that file itself. It names neither `wf_open_gate` nor the operator.
2. **The root `CLAUDE.md` bridge is rendered only when Guru is.** `render_agent_surfaces` returns early when `docs/agents/guru.md` is absent, and the bridge call sits after that return. A repository without the Guru role doc keeps a `CLAUDE.md` that does not import `AGENTS.md`.
3. **Seed 100 gives a `schema_version` example the framework does not write.** The seed says the string `"1.0"`. The only framework writer of that key writes the integer `1`.

## Product Intent

An operator installing Wavefoundry, and the agent doing the install, benefit. Before: the agent meets a blocked edit partway through Phase 2 with a message that names a file to edit, the operator is never asked, Claude may not load `AGENTS.md` in a repository without Guru, and the manifest the agent authors disagrees with the one the framework writes. After: the install log tells the agent when to ask the operator to open the framework edit gate and when to confirm it is closed, every host's block message names the tool and says the decision is the operator's, the bridge appears whenever `CLAUDE.md` exists, and the seed's example equals the written value.

Boundary: this change adds guidance and corrects two renderers. It does not change which paths are guarded, how a gate is opened, or who may open one. AC-1 to AC-3 establish the gate guidance outcome, AC-4 the bridge and AC-5 the manifest example. Whether agents then ask instead of editing the override file cannot be proven by renderer tests. Observe it in the next fresh-install field report: the install transcript should show the agent asking before the first guarded edit and no agent write to `.wavefoundry/guard-overrides.json`.

## Requirements

1. Every rendered hook that blocks or warns on a closed edit gate emits a message that names the gate, names `wf_open_gate(gate="<gate>")` and the CLI fallback `wf gate open <gate>`, and states that opening the gate is the operator's decision, so the agent asks first. The set of hooks is derived by rule: every hook source in `render_platform_surfaces.py` that calls `guard_enabled`. Today that is five message sites across Claude, Copilot, Cursor and Windsurf (see Decision Log).
2. The message no longer instructs the reader to set `enabled: true` in `.wavefoundry/guard-overrides.json`.
3. All hosts take the gate wording from one definition in the renderer, so the hosts cannot drift apart.
4. Each host keeps its current exit code and output stream, and the Claude and Copilot messages keep the `BLOCKED:` prefix.
5. The message is ASCII only, so a native Windows console with a legacy code page prints it intact.
6. The install log template carries an open row before the first Phase 2 row whose step edits a guarded surface, and a close row after the last such row. The open row is an `(instruction)` row telling the agent to ask the operator to open `framework_edit_allowed`. The close row is a `(verify)` row whose expectation is that `wf_gate_status` reports the install's gates closed.
7. Seed 012 carries one section per new row. The open-row section states: ask the operator and wait; never edit `.wavefoundry/guard-overrides.json` directly; never route around the hook with shell writes; ask only when an enabled host's hook guards a path that Phase 2 writes under `framework_edit_allowed` (`AGENTS.md`, `docs/prompts/`), and otherwise mark the row `[~]`; name the hosts whose hooks do so, a set derived from the renderer (today Claude, Copilot and Cursor; Windsurf's hook guards seeds only, which Phase 2 never writes, so a Windsurf-only install marks the row `[~]`); if the operator declines, stop and report. It also states that a session stopping before the close row closes the gate and asks again on resume.
8. `install-log-format.md` describes the two rows, and the row-number census in the tests matches the template.
9. `render_agent_surfaces` patches the root `CLAUDE.md` bridge whether or not `docs/agents/guru.md` exists. It still does nothing when `CLAUDE.md` is absent, and the auto-Guru marker block stays Guru-gated.
10. Seed 100's `schema_version` example states the value `docs_gardener.default_manifest_payload` writes, and says an existing value is preserved rather than rewritten.
11. Seed 050 describes the gate as opened by the operator through `wf_open_gate`, and no longer describes the bridge as part of the Guru surfaces.

## Scope

**Problem statement:** The install surface leaves the agent to discover the edit gate by being blocked, the block message suggests self-authorizing, the `CLAUDE.md` bridge depends on an unrelated role doc, and one seed example contradicts the code.

**In scope:**

- Gate message text in `.wavefoundry/framework/scripts/render_platform_surfaces.py`, with one shared definition.
- Two rows in `.wavefoundry/framework/install/install-log.template.md`, their sections in seed 012, and the format reference.
- Moving the bridge call in `.wavefoundry/framework/scripts/render_agent_surfaces.py` ahead of the Guru early return.
- The `schema_version` sentence in seed 100 and the gate and bridge sentences in seed 050.
- Tests for each, and regeneration of this repository's rendered hooks and reference copy.

**Out of scope:**

- Changing the guarded path set, the gate storage file, or `wf_open_gate` behaviour.
- Adding a pre-edit hook to hosts that have none (Codex, Junie, Warp, Antigravity). They get the guidance through seed 012 and `AGENTS.md`.
- Adding a framework-gate hook to Windsurf, which today guards seeds only.
- Changing the value the gardener writes, or rewriting `schema_version` in existing manifests.
- Upgrade-time gate guidance (seed 160). The corrected hook message reaches upgrades on its own; upgrade friction is planned in `23zia`.
- Creating `CLAUDE.md` where none exists.
- Adding the rows to live install logs of installs already in progress. The live log is never overwritten.

**Protected surfaces and lanes (framework maintenance plan):**

- Seeds 012, 050 and 100 are edited under `seed_edit_allowed`. All other framework files are edited under `framework_edit_allowed`. Both gates are opened only on the operator's instruction and closed when the edits finish.
- Generated surfaces are never hand-edited: `.claude/hooks/`, `.cursor/hooks/`, `.github/hooks/`, `.windsurf/hooks/` and `docs/references/install-log-format.md` are regenerated from the renderer and the shipped template.
- One write-owning lane (implementer) holds every file below; the three sub-items touch disjoint functions but share test files. Review lanes are read-only.
- This repository's own `CLAUDE.md` already carries the bridge and its own manifest carries `"1.0"`; neither is expected to change.

**Platform behaviour:** Hooks are Python and run on macOS, Linux, WSL2 and native Windows through the same rendered source, so the message change is identical on all four. The message is ASCII (Requirement 5). The message names the CLI fallback as `wf gate open <gate>`; on native Windows that command is reached as `.\.wavefoundry\bin\wf.cmd gate open <gate>`, which seed 012 states in full because a one-line hook message should not carry two launcher forms. The bridge write uses the existing platform-newline writer, so an operator's CRLF `CLAUDE.md` keeps its line endings (inferred from `_write_repo_text_platform_newlines`; covered by AC-4). The seed and template edits are prose and platform-neutral.

## Acceptance Criteria

AC-1 to AC-3 together test the gate guidance intent, AC-4 the bridge and AC-5 the manifest example.

- [x] AC-1: A test renders each host's gate hook, runs the rendered body against a guarded path with the gate closed, and finds in the output the gate name, `wf_open_gate`, `wf gate open` and a statement that the operator decides. It finds no `enabled: true`. The hosts covered are derived from the renderer by the rule in Requirement 1, so a new gate hook without the wording fails the test. Fails today: executed 2026-11-20, the Claude hook prints the `guard-overrides.json` wording for `AGENTS.md`, `docs/prompts/index.md` and a seed.
- [x] AC-2: The same rendered-body test shows each host's exit code and stream unchanged, the `BLOCKED:` prefix kept for Claude and Copilot, an edit to an unguarded path still passing, an edit with the gate open still passing, and the message encodable as ASCII.
- [x] AC-3: The install log template parses with an open row before the first guarded-surface row and a close row after the last, each with a matching seed 012 section, and the row-number census test passes with both rows listed. The open-row section contains the ask-the-operator instruction and the prohibition on editing the override file. Fails today: the template has no such rows and the census set excludes them.
- [x] AC-4: With a root `CLAUDE.md` and no `docs/agents/guru.md`, `render_agent_surfaces` writes the bridge block, reports `CLAUDE.md` as written, adds no auto-Guru marker block and is idempotent on a second run. With no `CLAUDE.md` it creates none. A CRLF `CLAUDE.md` keeps CRLF. The existing Guru-present bridge tests still pass. Fails today: executed 2026-11-20 against a scratch target, the bridge was absent and nothing was reported written.
- [x] AC-5: A test reads seed 100 and finds that its `schema_version` example equals the JSON form of `docs_gardener.default_manifest_payload()["schema_version"]`. Fails today: the seed says `"1.0"` and the payload value is `1`.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; this repository's rendered hooks equal a fresh render; and no failure elsewhere is attributable to this change.
- [x] AC-7: A test runs each hooked host's rendered pre-edit hooks, gates closed, against the Phase 2 guarded paths (`AGENTS.md` and a file under `docs/prompts/`) and derives the set of hosts that block or warn. Windsurf is not in that set. The hosts that seed 012's open-row section names as needing the gate equal the derived set, and the section tells a Windsurf-only install to mark the row `[~]`. Fails with the fix absent: guidance keyed on "any pre-edit hook" names no such host set, or includes Windsurf, and would stop a Windsurf-only install for a gate nothing there enforces.

## Tasks

- [x] Before rewording, list every byte-exact oracle on the current hook messages and bridge placement: tests, rendered hooks, seeds, `docs/` and local prompts (`grep` for `guard-overrides.json` near `enabled`, `after an approved file-level plan`, `before intentional seed edits`).
- [x] Define the gate message once in `render_platform_surfaces.py` and use it at every `guard_enabled` site.
- [x] Add the rendered-body tests for AC-1 and AC-2 in `test_render_platform_surfaces.py`.
- [x] Add the two rows to `install-log.template.md`; choose decimal-extension numbers that keep existing row numbers stable (suggested `2.1.5` and `2.13.7`).
- [x] Add the two sections to seed 012 and update `install-log-format.md`; update the census set and add the content assertions in `test_install_log_lib.py`.
- [x] Key the open-row condition in seed 012 on hooks that guard a Phase 2 path under `framework_edit_allowed`, name those hosts, and add the AC-7 test that derives the host set by running the rendered hooks, including the Windsurf-only case.
- [x] Move `patch_root_bridge` ahead of the `guru_available` early return in `render_agent_surfaces.py` and include its result in the returned list; add the AC-4 tests.
- [x] Correct seed 100's `schema_version` sentence and add the AC-5 test.
- [x] Update seed 050's gate and bridge sentences.
- [x] Update the guard-overrides line in `docs/architecture/cross-cutting-concerns.md`.
- [x] Regenerate this repository's hooks with `wf_sync_surfaces(mode='run')` and refresh `docs/references/install-log-format.md` from the shipped template.
- [x] Run the focused suites, then a second run under the declared release profile for the render tests, then full docs validation.
- [x] Add the Unreleased changelog entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| oracle-census | implementer | none | Read-only; lists pinned strings before any rewording |
| hook-message | implementer | oracle-census | Renderer, rendered-body tests, seed 050 gate sentence |
| install-rows | implementer | hook-message | Template, seed 012, format reference, census test; wording must match the hook message |
| claude-bridge | implementer | none | Renderer move, tests, seed 050 bridge sentence |
| manifest-example | implementer | none | Seed 100 sentence and test |
| regenerate-and-verify | implementer | hook-message, install-rows, claude-bridge, manifest-example | Sync surfaces, reference copy, suites, docs validation |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/install/install-log.template.md`
- `.wavefoundry/framework/install/install-log-format.md`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_install_log_lib.py`
- `.wavefoundry/framework/scripts/tests/test_per_area_agents_context.py`
- `.wavefoundry/framework/scripts/tests/test_docs_gardener.py`
- `.claude/hooks/pre-edit.py`
- `.cursor/hooks/seed-warn.py`
- `.cursor/hooks/framework-plan-warn.py`
- `.github/hooks/pre-tool-use.py`
- `.windsurf/hooks/seed-protect.py`
- `docs/references/install-log-format.md`
- `docs/architecture/cross-cutting-concerns.md`

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md`: the guard-overrides line says the file is "consumed by Claude Code pre-edit hook". Update it to say the operator opens a gate through `wf_open_gate` and that every hooked host reads the file. No boundary, flow or verification seam changes, so the other architecture docs are N/A.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect: the message must name the tool and the operator on every hooked host |
| AC-2 | required | Guards against weakening the gate while rewording it |
| AC-3 | required | The install log is where the agent learns to ask before it is blocked |
| AC-4 | required | The bridge is how Claude loads `AGENTS.md`; it must not depend on Guru |
| AC-5 | important | A wrong example, harmless to lint today, but it makes the agent author a value the framework would not |
| AC-6 | required | Change-local verification and regenerated surfaces |
| AC-7 | required | An install must not stop for a gate that no enabled hook enforces on Phase 2 paths |

## Progress Log

2026-11-21: The implementer reproduced a successful render without Guru that left an existing CLAUDE.md without its import. The five committed hook files reproduce the old wording, and the Claude pre-edit test pins its opening. The renderer supplies the hook bodies. Installers need the operator's gate decision before the first guarded edit and must close the gate on interruption. Verification will run each affected host hook on the two Phase 2 paths, render the bridge twice in a CRLF file, and compare the manifest example with the gardener's value.

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-21 | Verified the five generated hooks, install-log rows and existing Claude bridge. | All 244 focused tests passed on this checkout and under the declared profile. Full docs validation passed. |
| 2026-11-20 | Spec authored; all three premises verified against the tree, two by execution | Decision Log rows below |
| 2026-11-20 | Operator decision recorded: open row plus close row confirmed; row numbers, Windsurf scope and reader note unchanged | Decision Log, last row |
| 2026-11-20 | Plan review finding (advisory, relayed by the coordinator) applied: the open row is asked only when an enabled hook guards a Phase 2 path under `framework_edit_allowed`; Requirement 7 narrowed, AC-7 and a task added for the Windsurf-only case | `render_windsurf_hooks` registers only `seed-protect`, and the rendered `.windsurf/hooks/seed-protect.py` line 444 checks `is_seed_prompt` alone |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-20 | Premise (a) confirmed, hook message. Status: executed. | Ran the rendered `.claude/hooks/pre-edit.py` with the gate closed: `AGENTS.md` and `docs/prompts/index.md` exit 2 with "require `.wavefoundry/guard-overrides.json` with `framework_edit_allowed.enabled: true`"; a seed exits 2 with the seed variant; `CLAUDE.md` exits 0. Sources: `render_platform_surfaces.py` lines 1201 to 1209 (Claude and Copilot share `gate_file_path`), 1318 to 1319 and 1336 to 1338 (Cursor), 1668 to 1670 (Windsurf, seed only). None names `wf_open_gate`. | None; the premise holds |
| 2026-11-20 | Premise (a) confirmed, install log. Status: verified by reading; the interpretation of "row" is inferred. | `install-log.template.md` has no gate row, and seeds 010, 011 and 012 contain no mention of an edit gate, `wf_open_gate` or the override file. The guarded set (`render_platform_surfaces.py` lines 556 to 588) includes `AGENTS.md` and `docs/prompts/`, which rows 2.5 and 2.9 write. The feedback says "a guard-override and gate row" without naming its content; an open row and a close row is the reading adopted. | A single row; rejected because a gate left open after install removes the protection for all later work |
| 2026-11-20 | Premise (b) confirmed. Status: executed. | `render_agent_surfaces.py` returns at lines 5593 to 5594 when `docs/agents/guru.md` is absent; `patch_root_bridge` is called at line 5648. Ran `render_agent_surfaces` on two scratch targets holding a `CLAUDE.md`: without `guru.md` no bridge and nothing written; with it, bridge present and `CLAUDE.md` reported. | None; the premise holds |
| 2026-11-20 | Premise (c) confirmed, with one correction to its wording. Status: executed. | Seed 100 line 53 says `"1.0"`. The manifest writer is `docs_gardener.py`, not the surface renderer: `default_manifest_payload` line 361 and `ensure_manifest` line 438 use integer `1`. Ran `ensure_manifest` on an empty scratch root: the file was created with `schema_version` `1`. | None; the premise holds |
| 2026-11-20 | Fix the seed example, not the writer. | Docs lint checks only that the key is present (`core_validators.py` lines 688 to 690), and no reader of the value was found in the scripts that open the manifest (inferred: the census covered `dashboard_lib`, `check_version`, `build_pack`, `reconcile_scan`, `render_agent_surfaces`, `upgrade_wavefoundry` and `docs_gardener`, not out-of-tree readers). Existing manifests carry either form, and `setdefault` preserves them. | Change the writer to `"1.0"`: touches code and fixtures for a value nothing reads. Add a lint type check: a new mechanism that would fail existing installs |
| 2026-11-20 | Selected approach for (a): one shared message definition plus two install rows. | Efficacy: replaying the field case, the agent reaches the open row before row 2.5 and asks; if it skips the row, the block message now gives the same instruction at the moment of the block. The hook controls the edit; the wording and the row only advise, and what makes the agent act is that the named tool is the shortest path and is permission-gated on hosts that prompt for write tools. It cannot stop an agent that edits the override file through a shell, which the seed text forbids and which stays a known limit. Success is measured in the next fresh-install report. | Reword the message only: the agent still learns by being blocked mid-step. Have setup open the gate for the whole install automatically: removes the operator's decision, which is the point of the feedback. Exempt install from the hook: weakens the guard and needs a new install-state mechanism |
| 2026-11-20 | Selected approach for (b): move the bridge call ahead of the Guru early return. | Smallest change; the bridge already no-ops without `CLAUDE.md`. The top-of-function preflight runs before the new call site (inferred to cover `CLAUDE.md`; the implementer confirms). | Move the bridge into the platform renderer's Claude entrypoints: a larger ownership move across two renderers for no added benefit. Document the dependency: leaves the defect |
| 2026-11-20 | The close row is a `(verify)` row, not an `(instruction)` row. | A closed gate is observable through `wf_gate_status`, and the row applies on every host whether or not the open row was `[~]`. | An instruction row: nothing to check it against |
| 2026-11-20 | Operator decision, relayed by the coordinator from the main session: "a guard-override and gate row" means one open row plus one close row. This supersedes the "inferred" status in the install-log row above. The suggested row numbers (`2.1.5`, `2.13.7`), the Windsurf framework-gate hook staying out of scope and the `schema_version` reader note stand as written. | The operator accepted the coordinator's recommendation. | A single row, rejected above |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A byte-exact test or doc pins the old message | First task is the oracle census; `test_render_platform_surfaces.py` line 2163 pins the `BLOCKED: Seed prompt edit requires` prefix, which Requirement 4 keeps |
| Rendered hook templates drift from the tested source | AC-1 and AC-2 execute the rendered bodies, and AC-6 compares this repository's hooks with a fresh render |
| New rows break install-log parsing or the audit's next-step logic | Decimal-extension numbers are already legal (`2.13.5`); the template and parser parity tests and the one-to-one census run against the real template. No script refers to a row by literal number (inferred from a search for `2.14` and `2.15` in the scripts) |
| The gate is left open after an interrupted install | Seed 012 tells a stopping session to close it; the close row verifies it; the limit is an abandoned session, which is unchanged from today |
| The operator is asked on a host with no hook, or with a hook that guards no Phase 2 path (Windsurf) | The open row is marked `[~]` there (AC-7); the close row still verifies closed state |
| The bridge now writes into a `CLAUDE.md` the operator did not expect to change | It writes only the marked block, only into an existing file, and already did so for every Guru-enabled repository; the sync result reports the file |
| Seed prose does not reach local prompt copies | The census task checks `docs/prompts/` for restated wording; none was found for the `schema_version` example on 2026-11-20 |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
