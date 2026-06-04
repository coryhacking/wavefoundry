# Upgrade Migration For 1.5.0 Breaking Changes

Change ID: `1p3ay-feat upgrade-migration-for-1-5-0-breaking-changes`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p35d install-flow-two-phase-with-log-and-audit`

## Rationale

Wave 1p35d introduces three changes that break in-place on existing consumer installs running `Upgrade wave framework` from 1.4.x:

1. **`docs-lint` now enforces `Role:` on every `docs/agents/*.md` file** (C4 / `1p35l`). Consumers with custom agent docs added after their last install will hit lint failures on the first post-upgrade docs gate run.
2. **`.claude/hooks/pycache-cleanup*` launcher files become orphans** (C5 / `1p35n`). The framework no longer renders them, but the files remain in consumer repos and the `.claude/settings.json` hook row still points at them — Claude Code will invoke a deleted launcher on every Bash tool call and silently fail.
3. **`.claude/settings.json` `PostToolUse` Bash → `pycache-cleanup` row is no longer in the rendered spec.** `render_platform_surfaces.py` merges rather than overwrites settings.json, so the stale row persists until removed.

Without an active migration, consumers running `Upgrade wave framework` to 1.5.0 will land in a broken intermediate state. The remedy today is "operator manually edits settings.json and deletes the launcher files" — exactly the kind of post-upgrade manual cleanup the framework's upgrade machinery exists to prevent.

**`upgrade_extensions.py` is the canonical surface for this.** It ships in the upgrade zip, runs at named phase boundaries during the upgrade flow (`post_extract`, `post_surface_rendering`, etc.), receives an `UpgradeContext` with `from_version`, and is designed for version-gated migration hooks. Currently a no-op reference implementation; wave `12r1y` introduced the framework precisely for this case.

## Requirements

1. **Migration runs automatically during `Upgrade wave framework`** when the `from_version` predates 1.5.0. No operator action required; no separate command. The agent invokes upgrade as usual; the migration fires at the `post_extract` phase boundary.
2. **Three migrations land:**
   - **Role: backfill** — for every `docs/agents/<file>.md` file (and `docs/agents/specialists/<file>.md`, `docs/agents/personas/<file>.md`) missing a `Role:` line, insert `Role: <filename-slug>` immediately after the `Status:` line (or after `Owner:` if `Status:` is absent). Exclusions match the existing docs-lint exemption list: `README.md`, `session-handoff.md`, `platform-mapping.md`, and any file under `docs/agents/journals/`.
   - **Pycache launcher cleanup** — delete `.claude/hooks/pycache-cleanup`, `.claude/hooks/pycache-cleanup.py`, `.claude/hooks/pycache-cleanup.cmd` if any exist. Idempotent — re-running the upgrade is safe.
   - **Settings.json pycache row removal** — parse `.claude/settings.json`, locate any `PostToolUse` hook block whose `matcher` is exactly `"Bash"` AND whose nested `hooks[0].command` ends with `pycache-cleanup` (with or without `.cmd` / `cmd.exe /c` prefix), remove that block. Preserve all other hook rows including any operator-added custom hooks.
3. **Version gate.** Each migration runs only when `_from_version_predates(ctx.from_version, "1.5.0")` returns `True`. Repeat upgrades from 1.5.0+ skip the migrations entirely (no work, no log entries).
4. **Operator-visible migration report.** Every run that performs at least one fix writes a consolidated report to `.wavefoundry/logs/upgrade-migration-1.5.0.log`. Format: one section per migration, listing files modified. Idempotent re-run with no changes writes nothing.
5. **Defensive isolation.** A failure in one migration must not abort the others. Wrap each migration call in a try/except; on exception, record the migration name + traceback in the report and continue.
6. **Idempotency tests.** Each migration must be exercised by running it twice: first run performs work, second run is a no-op (no file modifications, no report-section appending).
7. **Version-gate tests.** A migration run with `from_version = "1.5.0"` or `"1.5.1"` performs zero work.
8. **No new dependencies.** Migration logic uses stdlib only (`json`, `pathlib`, `re`). No new modules added to the pack.
9. **seed-160 prose update.** A new subsection in seed-160 names the three migrations explicitly so the upgrade-driving agent knows what to expect and what to verify post-upgrade. Format follows existing seed-160 conventions.
10. **CHANGELOG entry.** A bullet under `## [1.5.0]` `### Changed` (or a new `### Migrations` section, whichever reads cleaner) names the auto-migration behavior.

## Scope

**In scope:**

- New module-level migration helpers in `upgrade_extensions.py` (`_from_version_predates`, `_backfill_role_field_on_agent_docs`, `_delete_pycache_hook_launchers`, `_strip_pycache_row_from_claude_settings`, `_write_migration_report`)
- New `post_extract(ctx)` hook wiring the version-gated migration calls
- Tests for each migration covering happy-path, idempotent re-run, missing-inputs, and version-gate
- seed-160 subsection documenting the auto-migration behavior
- CHANGELOG bullet under 1.5.0

**Out of scope:**

- Forward-only migrations beyond 1.5.0 (this change establishes the pattern; future migrations follow the same shape)
- Migration of host configs beyond Claude Code (`.cursor/`, `.windsurf/`, `.github/hooks/`, etc.) — the pycache hook was Claude-Code-specific; no other host had it
- Validation that re-rendering `render_platform_surfaces.py` after the migration produces a consistent state (`post_surface_rendering` already covers this contract)
- Rollback mechanism — the migration is forward-only; `git` is the rollback path if needed
- Migration for non-upgrade paths (a consumer running `Install wave framework` after wave 1p35d gets a fresh install with the new spec; no migration needed)

## Acceptance Criteria

- [x] AC-1: `post_extract(ctx)` is defined in `upgrade_extensions.py` and gated on `_from_version_predates(ctx.from_version, "1.5.0")`.
- [x] AC-2: `_from_version_predates` correctly recognizes pre-1.5.0 versions as TRUE and 1.5.0+ versions as FALSE. `FromVersionPredatesTests` covers `"1.0.0"`, `"1.3.32"`, `"1.4.0"`, `"1.4.1"`, `"1.4.1+p347"`, `"0.9.0"` → True; `"1.5.0"`, `"1.5.0+x"`, `"1.5.1"`, `"1.6.0"`, `"2.0.0"`, `"10.0.0"` → False.
- [x] AC-3: Unknown / unparseable `from_version` (None, empty, date-style `"2026-05-19a"`, garbage, `"v1.5.0"`) all return TRUE (safe default — re-run idempotent).
- [x] AC-4: `_backfill_role_field_on_agent_docs` walks agents/ + specialists/ + personas/, inserts `Role: <slug>` after `Status:` (fallback `Owner:`).
- [x] AC-5: `_ROLE_LINE_RE.search` short-circuits when `Role:` already present.
- [x] AC-6: Exemption list (`README.md`, `session-handoff.md`, `platform-mapping.md`) + journals/ directory skipped.
- [x] AC-7: `_delete_pycache_hook_launchers` removes the three variants. Idempotent (test_idempotent_when_no_launchers_present).
- [x] AC-8: `_strip_pycache_row_from_claude_settings` matches `matcher: "Bash"` + command suffix `pycache-cleanup` / `pycache-cleanup.cmd`; preserves all other rows (test_preserves_operator_custom_bash_hook).
- [x] AC-9: No-op when pycache row absent — returns None, file content unchanged (`test_noop_when_no_pycache_row`).
- [x] AC-10: Report written when ≥1 migration performed work (`test_report_lists_all_three_migration_sections`).
- [x] AC-11: Report NOT written when no work performed (`test_no_report_written_when_no_work_done`).
- [x] AC-12: Exception isolation: a migration raising is captured in the report with name + traceback; other migrations still run (`test_exception_in_one_migration_isolated`).
- [x] AC-13: Idempotent re-run: each migration's `test_idempotent_second_run_is_noop` + the orchestration-level `test_idempotent_full_pipeline`.
- [x] AC-14: `test_version_gate_skips_when_from_at_cutoff` — `from_version = "1.5.0"` → zero work, no report.
- [x] AC-15: seed-160 gains `### 1.5.0 upgrade — auto-migration` subsection.
- [x] AC-16: CHANGELOG 1.5.0 bullet added.
- [x] AC-17: Full framework test suite passes (2459 tests, +29 from C7).
- [x] AC-18: docs-lint passes.

## Tasks

- [x] Open `seed_edit_allowed` and `framework_edit_allowed` gates
- [x] Implement `_from_version_predates` helper
- [x] Implement `_backfill_role_field_on_agent_docs`
- [x] Implement `_delete_pycache_hook_launchers`
- [x] Implement `_strip_pycache_row_from_claude_settings`
- [x] Implement `_write_migration_report`
- [x] Wire `post_extract(ctx)` with version gate + try/except isolation + report write
- [x] Add tests covering each migration (29 new tests across 5 classes)
- [x] Add version-gate tests
- [x] Add exception-isolation test
- [x] Add seed-160 `### 1.5.0 upgrade — auto-migration` subsection
- [x] Update CHANGELOG 1.5.0 with auto-migration bullet
- [x] Run framework test suite (2459 tests pass)
- [x] Run docs-lint (clean)
- [x] Close gates

## Affected Architecture Docs

`N/A` — extends an existing extension point (`upgrade_extensions.py`); no architectural boundary or new component introduced.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (post_extract defined + version-gated) | required | The activation mechanism. |
| AC-2 (version-gate recognizes pre-1.5.0 vs 1.5.0+) | required | Wrong comparison either skips migrations on broken installs or re-runs them on already-migrated ones. |
| AC-3 (unknown / unparseable from_version → safe default) | required | Date-style `from_version` from older packs must still trigger migration; idempotent re-run is the safety net. |
| AC-4 (Role: backfill walks the right tree + inserts correctly) | required | The most-impactful migration; protects every customer with custom agent docs. |
| AC-5 (Role: already-present is left alone) | required | Idempotency precondition; without it, repeated upgrades append duplicate lines. |
| AC-6 (exemption list honored) | required | Misclassifying `README.md` / `session-handoff.md` / `platform-mapping.md` / `journals/` as role docs would corrupt their headers. |
| AC-7 (launcher cleanup) | required | Dead files create operator confusion at minimum. |
| AC-8 (settings.json strip removes the right row) | required | The active failure mode: stale hook calls deleted launcher. |
| AC-9 (settings.json no-op when row absent) | required | Avoid spurious file rewrites for downstream watch loops. |
| AC-10 (report written when work performed) | required | Operator audit trail. Without the report, post-upgrade verification is grep-and-pray. |
| AC-11 (report NOT written when no work performed) | required | Avoid log noise on already-migrated repeated upgrades. |
| AC-12 (exception isolation) | required | A partial migration is worse than a noisy one — operators need to know what fired. |
| AC-13 (idempotent re-run) | required | Operators re-run upgrades for many reasons; re-runs must not double-fix or corrupt state. |
| AC-14 (version-gate skip on 1.5.0+) | required | Wasted work + log noise on every subsequent upgrade. |
| AC-15 (seed-160 prose) | required | Discoverability for the upgrade-driving agent. |
| AC-16 (CHANGELOG) | required | Discoverability for operators reading release notes. |
| AC-17 (full framework test suite passes) | required | Standard hygiene. |
| AC-18 (docs-lint passes) | required | Standard hygiene. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-04 | Implement migration in `upgrade_extensions.py` (`post_extract` hook) | The framework already has a version-gated extension surface (wave `12r1y`) for exactly this case. Using it preserves the established upgrade-phase contract. | Add migration to `upgrade_wavefoundry.py` directly — rejected; the extension module exists to prevent migration logic from coupling to the upgrade orchestrator core. |
| 2026-06-04 | Auto-fix rather than warn-and-stop | Consumers running `Upgrade wave framework` expect a single-step upgrade. Stopping at every missing `Role:` would create a tedious back-and-forth. The auto-fix is correct (Role = filename slug) and the migration report makes it auditable. | Warn and require explicit operator approval per file — rejected; the operator already authorized the upgrade. |
| 2026-06-04 | Treat unknown / unparseable `from_version` as pre-1.5.0 | Idempotent migrations are safe to re-run; treating unknown as "old" means we never silently skip migration on a state that actually needs it. | Treat unknown as "skip" — rejected; would leave consumers with date-style `from_version` (`2026-05-10a`) unmigrated. |
| 2026-06-04 | Each migration wrapped in try/except, isolated failure | Partial state is worse than full state — an operator who hit a Python error mid-migration would have to guess what ran. Isolated failures + a report telling them precisely what fired and what raised is the auditable shape. | Bail on first exception — rejected; one bug in one migration would block the rest. |
| 2026-06-04 | Migration report at `.wavefoundry/logs/upgrade-migration-1.5.0.log` | Mirrors the existing `.wavefoundry/logs/` convention (build, upgrade, dashboard logs all live there). Version in the filename so future migrations don't overwrite. | Append to a generic upgrade log — rejected; conflates per-version migration records with continuous upgrade activity. |
| 2026-06-04 | Migration runs only via `Upgrade wave framework`, not on fresh installs | Fresh installs already get the new spec; running the migration on them would be wasted work. The upgrade extension framework fires only on upgrades by design. | Run on every framework activation — rejected; pointless work. |

## Risks

| Risk | Mitigation |
|---|---|
| Auto-injected `Role:` doesn't match the operator's intent for a file that wasn't really meant to be a role doc | The migration runs only on files under `docs/agents/` excluding the exemption list. If a non-role doc ended up there, the file's existence already implied it was a role doc per the docs-lint rule; the migration just makes the agent doc visible. The report names every file modified so the operator can audit and revert any unwanted insertions. |
| Settings.json strip misidentifies a hook row that legitimately ends with `pycache-cleanup` (e.g., an operator-customized hook with the same name) | Match is anchored on `matcher: "Bash"` AND `command` *ending* in `pycache-cleanup` or `pycache-cleanup.cmd`. The exact-string-match shape minimizes risk. If an operator named their own hook `pycache-cleanup`, removal is appropriate behavior — the framework recommends not reusing retired hook names. |
| Migration runs on a partially-corrupted upgrade state and produces inconsistent results | The `post_extract` phase runs after the new framework zip has fully extracted to disk. The migration sees the new spec in place. Idempotent design means a second upgrade run produces the same end state regardless of where the first run halted. |
| Operator-customized `.claude/settings.json` ordering is disrupted by the strip rewrite | Settings.json is JSON; round-trip via `json.load` + `json.dump` preserves keys but may normalize whitespace. Use `indent=2` to match the existing rendered output style. If operator-customized formatting was significant, the operator can re-format post-upgrade. |
| Future migrations layer onto this one and create version-gate confusion | The pattern is: one `post_extract` hook block per version cutoff, each independently gated. The pattern is documented in this change doc + seed-160. |
| Vendored consumers on older Claude Code never upgrade | The migration only fires during `Upgrade wave framework`. Consumers who don't upgrade stay on 1.4.x with no behavior change. The migration is forward-only; no rollback concern. |

## Related Work

- **Wave `12r1y` (`upgrade_extensions.py` introduction)** — defined the extension hook surface this change uses.
- **C2 (`1p35h` / `wave_install_audit`)** — new MCP tool; reload covered by seed-160 step 3 (no migration needed).
- **C4 (`1p35l` / Role: enforcement)** — the breaking change Migration #1 addresses.
- **C5 (`1p35n` / pycache hook retirement)** — the breaking change Migrations #2 and #3 address.
- **seed-160** — operator-facing upgrade prompt that gains an auto-migration subsection.
- **Self-host Role: drift fix during C4** — the 22 specialist + persona docs in this self-host that were missing `Role:` were fixed via an ad-hoc Python script. The migration codifies that same logic so consumer repos with the same drift class get fixed automatically.

## Session Handoff

Admitted to wave 1p35d as C7. Sequenced after C6's enterprise hardening (no dependency on C1–C6 implementation; the migration logic depends on the breaking-change contracts being final, which they are at C5 / C6 close). Delivery-council pass required before close.
