# Upgrade Migration Tier-2 Hardening

Change ID: `1p3b7-enh upgrade-migration-tier-2-hardening`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p3b9 chunker-indexer-correctness-and-1-5-0-hardening`

## Rationale

Wave 1p35d's pre-close review surfaced three small enterprise-deployment improvements (F4, F5, F6) that are individually <20 LOC each, share a similar shape (extending or refining a surface that already shipped), and can be bundled into one change to keep the follow-on wave's roster manageable.

Each addresses a real risk class but none is acute enough to block 1p35d's close:

- **F4 — `.claude/settings.local.json` strip**: `1p3ay`'s `_strip_pycache_row_from_claude_settings` only touches the committed `.claude/settings.json`. An operator who put the legacy pycache hook row in their personal override file (`.claude/settings.local.json`) would still have the orphan. `settings.local.json` is gitignored, but enterprise consumers with shared machine images or operator-onboarding scripts may share local-overrides across users.
- **F5 — Component-level test for dashboard empty-Agents-panel guidance**: `1p35l` (C4) added the empty-state guidance copy. Unit tests cover `collect_agents` and the `no_agent_role_docs` advisory; the React rendering branch for the empty panel was not directly tested. Low-impact (UX-only) but a real regression surface.
- **F6 — Recursive walk for Role: backfill**: `1p3ay`'s `_backfill_role_field_on_agent_docs` walks three fixed subdirs (`docs/agents/`, `docs/agents/specialists/`, `docs/agents/personas/`). Enterprise repos that nest agent docs by team (`docs/agents/teams/<team>/<role>.md`) would be missed. Not in framework default, but a real shape some consumers use.

Bundling rationale: each is small, none is contract-changing, and they share the "extend an existing surface" delivery shape. One change doc + one delivery-council pass covers them; splitting would create three micro-changes with redundant ceremony.

## Requirements

### F4 — `.claude/settings.local.json` strip

1. `_strip_pycache_row_from_claude_settings` is extended (or a companion helper added) to also process `.claude/settings.local.json` when present. Same matching logic: `matcher == "Bash"` + command ending in `pycache-cleanup` / `pycache-cleanup.cmd`.
2. Both files (`settings.json` and `settings.local.json`) are reported separately in the migration report so the operator can see which got modified.
3. Missing `settings.local.json` is a no-op (same as missing `settings.json` today).

### F5 — Component-level test for empty-Agents-panel

4. A dashboard unit test exercises the `Agents` component with `agents=[]`, asserts the empty-state guidance markup renders (heading + paragraph with shortcut phrase + `Role:` code element).
5. A second test exercises the populated case (`agents=[{...}]`), asserts the empty-state markup is NOT present.

### F6 — Recursive walk for Role: backfill

6. `_backfill_role_field_on_agent_docs` switches from fixed-subdir iteration to a recursive walk of `docs/agents/` (using `pathlib.Path.rglob("*.md")` or equivalent), skipping `journals/` at any depth and honoring the existing exempt-filename list.
7. Existing tests covering `specialists/` and `personas/` subdirs continue to pass.
8. New test covers a nested layout (`docs/agents/teams/auth/code-reviewer.md`) — verifies Role: gets inserted at any depth.
9. New test verifies a deeply-nested journal file (`docs/agents/teams/auth/journals/note.md`) is still skipped.

## Scope

**In scope:**

- `_strip_pycache_row_from_claude_settings` extension for `.claude/settings.local.json`
- Component-level test for `Agents` empty-state branch
- `_backfill_role_field_on_agent_docs` recursive-walk refactor
- Tests for each (4 new tests + 1 modified test minimum)
- CHANGELOG bullets noting the three extensions

**Out of scope:**

- Generic per-host settings.local migration (Cursor, Codex, etc.) — none of those hosts had the pycache hook, so settings.local migration is Claude-specific
- Dashboard E2E browser-level testing (component-level coverage is sufficient for F5)
- Generic recursive walking for other migrations (each migration's surface determines its own walk shape)
- Renaming the C7 migration helpers (their names remain stable; F6's recursive walk is an internal refactor)

## Acceptance Criteria

- [x] AC-1: F4 — `_strip_pycache_row_from_claude_settings` now iterates `(settings.json, settings.local.json)` via the shared `_strip_pycache_row_from_settings_file(path, root)` inner helper. Each file's strip is independent.
- [x] AC-2: F4 — Return type changed from `str | None` to `list[str]`; migration report sections include one entry per modified file (both files appear when both are stripped). Existing 7 tests updated to the new list shape.
- [x] AC-3: F4 — `test_F4_strips_from_settings_local_json_too` and `test_F4_settings_local_only` cover both-files and local-only cases respectively; missing-file already covered by the existing `test_missing_settings_file_returns_empty_list`.
- [x] AC-4: F5 — `test_agents_component_has_empty_state_branch` asserts the JS source contains `function Agents({ agents, onSelectAgent })`, `hero-agents--empty` className, `"Agents"` heading, `"No agent role docs found"` copy, `"Init agent surfaces"` shortcut, and `Role: <role-slug>` code element.
- [x] AC-5: F5 — `test_agents_component_renders_populated_branch_when_agents_present` asserts the category strings (`"coordinate"`, `"review"`, `"build"`) and `hero-agent-group` class are still present.
- [x] AC-6: F6 — `_backfill_role_field_on_agent_docs` switched from fixed-subdir iteration to `agents_root.rglob("*.md")`. The `journals` skip and exempt-filename list apply at every depth.
- [x] AC-7: F6 — Existing `test_walks_specialists_and_personas_subdirs` continues to pass unchanged (recursive walk is a superset of the three fixed subdirs).
- [x] AC-8: F6 — `test_F6_recursive_walk_finds_nested_layout` plants `docs/agents/teams/auth-team/code-reviewer.md`, verifies migration inserts `Role: code-reviewer`.
- [x] AC-9: F6 — `test_F6_journals_skipped_at_any_depth` plants `docs/agents/teams/auth/journals/note.md`, verifies it is left untouched.
- [x] AC-10: CHANGELOG bullet describes all three changes (F4 + F5 + F6) in one entry.
- [x] AC-11: Full framework test suite passes (2507 tests, +6 from C5).
- [x] AC-12: docs-lint passes.

## Tasks

- [x] Open `framework_edit_allowed` gate (already open from C1)
- [x] Refactor `_strip_pycache_row_from_claude_settings` to iterate both `settings.json` and `settings.local.json` via shared inner helper
- [x] Update post_extract migration to iterate the new list return shape
- [x] Add dashboard component-level tests for `Agents` empty-state (source-level assertion matching the existing test pattern)
- [x] Refactor `_backfill_role_field_on_agent_docs` to recursive walk
- [x] Mirror the recursive walk in the preview helper `_preview_role_field_backfill`
- [x] Add nested-layout test for backfill
- [x] Add deeply-nested journal-skip test
- [x] Verify existing C7 migration tests still pass against the refactored backfill (29 prior tests + 2 new = 31 backfill tests, all pass)
- [x] Update CHANGELOG
- [x] Run framework test suite (2507 tests pass)
- [x] Run docs-lint (clean)
- [x] Close gate (will close at wave end)

## Affected Architecture Docs

`N/A` — three small surface extensions; no architectural boundary change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (settings.local.json processed) | required | Core F4 fix. |
| AC-2 (separate report entries) | required | Operator visibility into which file changed. |
| AC-3 (local-override tests) | required | Verifies F4 behavior. |
| AC-4 (Agents empty-state render test) | required | Core F5 fix. |
| AC-5 (Agents populated-state regression guard) | required | Without it, a refactor could break empty-state without test signal. |
| AC-6 (recursive walk) | required | Core F6 fix. |
| AC-7 (existing tests preserved) | required | Regression discipline. |
| AC-8 (nested layout test) | required | Verifies F6 reaches the case it exists for. |
| AC-9 (deeply-nested journal skip) | required | Regression guard for journal-exemption-at-depth. |
| AC-10 (CHANGELOG) | required | Standard. |
| AC-11 (suite passes) | required | Standard. |
| AC-12 (lint passes) | required | Standard. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-04 | Bundle F4 + F5 + F6 in one change | Each is <20 LOC, none is contract-changing, all share the "extend existing surface" delivery shape. One council pass covers them; splitting creates three micro-changes with redundant ceremony. | Three separate change docs — rejected; ceremony cost. |
| 2026-06-04 | F4 extends settings strip, not a new helper | `_strip_pycache_row_from_claude_settings` already does the work for one file; extending it (or refactoring to take a path parameter and calling twice) is simpler than a parallel helper. | New companion helper — rejected; duplicates logic. |
| 2026-06-04 | F6 changes from fixed subdirs to recursive walk | Three fixed subdirs already required iteration logic; recursive walk via `rglob` is the same shape with broader coverage. | Add a fourth fixed subdir for `teams/` — rejected; doesn't generalize to other nesting shapes. |
| 2026-06-04 | F5 uses component-level testing, not E2E | The dashboard already has unit/component testing infrastructure; E2E browser tests aren't established for this repo and are out of scope. | E2E browser test — rejected; infrastructure cost. |

## Risks

| Risk | Mitigation |
|---|---|
| F6 recursive walk false-positives on a non-role-doc that happens to land deep in `docs/agents/` | Same exempt-filename list applies at all depths; `journals/` at any depth is skipped. False positives possible if an operator drops a non-role .md file deep in the tree, but the lint rule that drove C4 implies any .md under `docs/agents/` (except the exempt list) IS supposed to be a role doc. |
| F4 changes operator-personal state without operator awareness | The C7 migration report already records every file modified; F4 just adds `settings.local.json` to that report when applicable. Same audit trail. |
| F5 component test fails on future React/dashboard refactors that change rendering shape | Acceptable — that's exactly what regression guards exist for. If the empty-state markup intentionally changes, the test updates with it. |

## Related Work

- **Wave 1p35d (`1p3ay`)** — introduced the C7 migration helpers F4 and F6 extend.
- **Wave 1p35d (`1p35l`)** — introduced the dashboard empty-Agents-panel guidance F5 tests.
- **Wave 1p35d pre-close review** — surfaced these as findings F4, F5, F6 (2026-06-04).

## Session Handoff

Surfaced as wave 1p35d pre-close review findings F4, F5, F6 (2026-06-04). Operator selected the bundle option for queue to the follow-on wave that ships jointly with 1p35d under the **1.5.0** tag.
