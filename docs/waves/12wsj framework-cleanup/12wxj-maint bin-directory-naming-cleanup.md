# Bin Directory Naming Cleanup

Change ID: `12wxj-maint bin-directory-naming-cleanup`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-25
Wave: `12wsj framework-cleanup`

## Rationale

Two naming inconsistencies exist in `.wavefoundry/bin/`:

1. `wave_dashboard` uses underscores while every other bin script uses dashes — this is a drift from the established convention and creates inconsistency in documentation, seeds, and contributor setup instructions.
2. `register-codex-mcp` was the manual bootstrap step for registering the wavefoundry MCP server in `~/.codex/config.toml`. Since `12ww2-ops` moved that registration to a committed project-local `.codex/config.toml`, the script has no remaining function and should be removed along with its references.

## Requirements

1. `.wavefoundry/bin/wave-dashboard` replaces `.wavefoundry/bin/wave_dashboard`; the old filename is removed.
2. All references to `wave_dashboard` in seeds, scripts, docs, AGENTS.md, and tests are updated to `wave-dashboard`.
3. `.wavefoundry/bin/register-codex-mcp` is removed.
4. All references to `register-codex-mcp` in seeds, scripts, docs, AGENTS.md, and tests are removed or replaced with a note pointing to the project-local `.codex/config.toml`.
5. The seed changes are made with the `seed_edit_allowed` gate open and closed immediately after.

## Scope

**Problem statement:** `wave_dashboard` uses underscore naming instead of the dash convention used by all other bin scripts; `register-codex-mcp` is a now-obsolete bootstrap script superseded by the project-local MCP config.

**In scope:**

- Rename `.wavefoundry/bin/wave_dashboard` → `.wavefoundry/bin/wave-dashboard`
- Update all `wave_dashboard` references: seeds (5), scripts (2), tests (3), docs (~15 files), `AGENTS.md`, `.claude/settings.local.json`
- Remove `.wavefoundry/bin/register-codex-mcp`
- Remove or replace all `register-codex-mcp` references: seeds (2), scripts (2), tests (1), docs (~8 files), `AGENTS.md`, `.codex/skills/auto-guru/SKILL.md`, `README.md`

**Out of scope:**

- Changes to `dashboard_server.py` or MCP server implementation
- Any rename of the `wave_dashboard` MCP tools exposed by `server_impl.py` (those are API surface, not bin scripts)

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/bin/wave-dashboard` exists and is executable; `.wavefoundry/bin/wave_dashboard` is deleted
- [x] AC-2: `grep -r "wave_dashboard" .wavefoundry/ docs/ AGENTS.md .claude/` returns only stale-cleanup list and assertFalse tests — both correct
- [x] AC-3: `.wavefoundry/bin/register-codex-mcp` is deleted
- [x] AC-4: `grep -r "register-codex-mcp" .wavefoundry/ docs/ AGENTS.md .codex/ README.md` returns only stale-cleanup list and assertFalse tests — both correct
- [x] AC-5: `python3 .wavefoundry/framework/scripts/run_tests.py` — 1620 tests, 0 failures (2026-05-25)
- [x] AC-6: `docs-lint` passes after all edits

## Tasks

- [x] Open `seed_edit_allowed` gate
- [x] Rename `wave_dashboard` → `wave-dashboard` in seeds 010, 152, 160
- [x] Remove `register-codex-mcp` references from seeds 050, 160; replaced with `.codex/config.toml` note
- [x] Close `seed_edit_allowed` gate immediately after seed edits
- [x] Update `AGENTS.md` — rename and removal
- [x] Update `README.md` — remove `register-codex-mcp`
- [x] Update `docs/references/dashboard-install-upgrade.md`
- [x] Update `docs/prompts/` — start dashboard; install, upgrade
- [x] Update `docs/agents/platform-mapping.md`
- [x] Update `.codex/skills/auto-guru/SKILL.md`
- [x] Update `render_platform_surfaces.py` and `render_agent_surfaces.py`
- [x] Update test file `test_render_platform_surfaces.py`
- [x] Rename bin file `wave_dashboard` → `wave-dashboard`; delete `register-codex-mcp`
- [x] Run full test suite — verify AC-5
- [x] Run docs-lint — verify AC-6

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| Seed edits | implementer | gate open | Open + close gate as a unit |
| Docs and surface edits | implementer | — | Can run in parallel with non-seed work |
| Script and test edits | implementer | — | |
| Bin file rename and deletion | implementer | all edits complete | Rename last to avoid broken references during edit pass |
| Validation | implementer | bin rename + deletion | Full suite + docs-lint |

## Serialization Points

- Open `seed_edit_allowed` gate before touching any seed; close immediately after — do not leave gate open across the full edit pass.
- Rename/delete the bin file last — keep the old name valid while references are being updated so any partial run stays coherent.

## Affected Architecture Docs

N/A — naming and dead-code cleanup only; no boundary, flow, or verification architecture impact.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core rename deliverable |
| AC-2 | required | Confirms no stale `wave_dashboard` references remain |
| AC-3 | required | Removes obsolete script |
| AC-4 | required | Confirms no stale `register-codex-mcp` references remain |
| AC-5 | required | No regressions from mechanical rename |
| AC-6 | required | Docs contract stays clean |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-25 | Change doc created | |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-25 | Combine both items in one change | Same area, same kind of work (bin hygiene); single test pass covers both | Two separate changes (more overhead, no benefit) |
| 2026-05-25 | Exclude closed wave history docs from AC-2/4 grep | Historical wave docs record what was implemented; renaming them is churn with no benefit | Update all files (unnecessary) |

## Risks

| Risk | Mitigation |
|---|---|
| `wave_dashboard` MCP tool names in `server_impl.py` share the prefix — grep catches them accidentally | AC-2 grep is scoped to bin scripts, seeds, docs, and AGENTS.md — not server_impl.py tool names |
| Seed gate left open across edit pass | Serialization point: close gate immediately after seed edits complete |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
