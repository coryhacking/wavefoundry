# Upgrade Dry-Run Preview Of Migration Effect

Change ID: `1p3b6-enh upgrade-dry-run-preview-of-migration-effect`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p3b9 chunker-indexer-correctness-and-1-5-0-hardening`

## Rationale

Wave 1p35d (`1p3ay` upgrade migration) introduced `post_extract` hooks in `upgrade_extensions.py` that run three migrations automatically on every consumer upgrade from < 1.5.0:

1. `Role:` backfill on `docs/agents/*.md`
2. `.claude/hooks/pycache-cleanup*` launcher deletion
3. `.claude/settings.json` pycache-row strip

The migrations modify operator-owned files. They are idempotent + isolated + report-backed, but **risk-averse enterprise deployments need a preview** — what would this migration touch, before it commits.

The upgrade orchestrator already has a `--dry-run` flag (per seed-160). Today `--dry-run` surfaces the extension module source and the upgrade phase list, but does NOT simulate what the `post_extract` migrations would do. This gap was identified as wave 1p35d C7 finding F3 (also recorded as advisory C7-DC-1 in the C7 delivery-council verdict).

The fix: each migration helper gains a `_preview` variant that returns the list of planned actions without performing them; `post_extract` calls the preview variants instead of the action variants when `ctx.yes` indicates dry-run mode (or via a new `ctx.dry_run` attribute, whichever is cleaner). The preview output goes to stderr + the upgrade log so operators see exactly what would change.

## Requirements

1. **`UpgradeContext` gains a `dry_run` attribute** (or repurposes an existing one) that the migration hooks consult. Dry-run mode is propagated from the upgrade orchestrator's `--dry-run` flag.
2. **Each migration helper gains a `_preview` companion** that takes the same inputs, returns the planned action list, but performs zero filesystem mutations:
   - `_preview_role_field_backfill(root) -> list[str]` — names files that WOULD have `Role:` inserted, with the slug that WOULD be inserted
   - `_preview_pycache_launcher_deletion(root) -> list[str]` — names launcher files that WOULD be deleted
   - `_preview_settings_pycache_strip(root) -> dict | None` — describes the row that WOULD be stripped (matcher + command), without rewriting the JSON
3. **`post_extract(ctx)` consults `ctx.dry_run`**. When True: call the `_preview` variants, write the preview report to `.wavefoundry/logs/upgrade-migration-1.5.0.preview.log` (distinct filename so a preview run doesn't shadow a later real run's report), AND print a concise summary to stderr.
4. **Preview output structure** mirrors the existing migration-report shape (per-migration section with action records) so operators reading both side-by-side can correlate.
5. **No new dependencies**. Stdlib only.
6. **Tests** cover each preview helper (matches the action variant's coverage shape) + the orchestration `post_extract` dry-run branch (verifies zero mutations + preview-log written).

## Scope

**In scope:**

- `UpgradeContext.dry_run` field (or equivalent signaling mechanism)
- Three `_preview` helpers paralleling the three action helpers
- `post_extract` dry-run branch
- Preview-log writer (separate filename)
- Tests

**Out of scope:**

- Interactive operator confirmation per migration (`--dry-run` is sufficient for the gap; per-migration confirm adds operator friction without addressing the documented concern)
- Preview UI in the dashboard (server-side preview-log is the contract; dashboard can render it later)
- Rolling back a partial real-run via the preview data (forward-only; `git` is the rollback path)
- Preview for hypothetical future migrations beyond the three in `1p3ay` (this change establishes the pattern; future migrations add their own preview variants)

## Acceptance Criteria

- [x] AC-1: `UpgradeContext.dry_run: bool = False` attribute added; `phase_dry_run` constructs a preview context with `dry_run=True` and invokes `post_extract` on the loaded extension module before any side effects occur.
- [x] AC-2: `_preview_role_field_backfill(root)` walks the same dirs as the action helper, identifies files missing `Role:` AND with a `Status:`/`Owner:` anchor, returns `["<path>: would insert `Role: <slug>`", ...]`. Zero mutations. Verified via `RoleBackfillPreviewTests`.
- [x] AC-3: `_preview_pycache_launcher_deletion(root)` returns `["would delete <path>", ...]` for each existing `.claude/hooks/pycache-cleanup*` launcher. Zero mutations. Verified via `PycacheLauncherDeletionPreviewTests`.
- [x] AC-4: `_preview_settings_pycache_strip(root)` returns a dict `{"file", "matcher", "command", "note"}` describing the row that would be stripped, or None when no row matches. JSON not rewritten. Verified via `SettingsPycacheStripPreviewTests`.
- [x] AC-5: `post_extract(ctx)` checks `getattr(ctx, "dry_run", False)`; when True it calls the preview helpers, writes `.wavefoundry/logs/upgrade-migration-1.5.0.preview.log`, and prints `upgrade-migration preview: N planned action(s); see <path> for details (no files modified)` to stderr.
- [x] AC-6: Preview-log filename is `upgrade-migration-1.5.0.preview.log` — distinct from the real-run `upgrade-migration-1.5.0.log`. Verified via `test_dry_run_uses_distinct_filename_from_real_run`.
- [x] AC-7: 12 unit tests across `RoleBackfillPreviewTests` (4 cases), `PycacheLauncherDeletionPreviewTests` (2 cases), `SettingsPycacheStripPreviewTests` (3 cases).
- [x] AC-8: `test_dry_run_zero_mutations` plants a role-missing agent doc + a pycache launcher, runs `post_extract` with `dry_run=True`, asserts both files are byte-identical post-call.
- [x] AC-9: `test_dry_run_writes_preview_log_when_actions_planned` asserts the preview log is written, contains the `PREVIEW` marker, and names the planned files; also asserts the real-run log is NOT written in the same call.
- [x] AC-10: seed-160 `### 1.5.0 upgrade — auto-migration` subsection gains a `Migration preview (operator-side, --dry-run)` paragraph describing the preview path, the preview-log location, and the distinct-filename invariant.
- [x] AC-11: CHANGELOG entry under `## [1.5.0]`.
- [x] AC-12: Full framework test suite passes (2501 tests, +14 from C4).
- [x] AC-13: docs-lint passes.

## Tasks

- [x] Open `seed_edit_allowed` and `framework_edit_allowed` gates (both already open from earlier in the wave)
- [x] Add `dry_run` to `UpgradeContext` (with `getattr` fallback for older callers)
- [x] Wire the orchestrator `--dry-run` flag through: `phase_dry_run` loads the extension module from the new pack and calls `post_extract(preview_ctx)` with `dry_run=True`
- [x] Implement `_preview_role_field_backfill`
- [x] Implement `_preview_pycache_launcher_deletion`
- [x] Implement `_preview_settings_pycache_strip`
- [x] Add `_write_migration_preview_report` (distinct filename)
- [x] Add dry-run branch to `post_extract`
- [x] Add tests (14 net new)
- [x] Update seed-160 prose
- [x] Update CHANGELOG
- [x] Run framework test suite (2501 tests pass)
- [x] Run docs-lint (clean)
- [x] Close gates (will close at C5 / wave end)

## Affected Architecture Docs

`N/A` — extends an existing extension surface; no architectural boundary change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (UpgradeContext.dry_run) | required | Signaling mechanism the migration hooks consult. |
| AC-2 (Role: backfill preview helper) | required | Without it, the Role: backfill migration has no preview path. |
| AC-3 (pycache launcher deletion preview helper) | required | Without it, the launcher cleanup migration has no preview path. |
| AC-4 (settings.json pycache strip preview helper) | required | Without it, the settings.json strip migration has no preview path. |
| AC-5 (post_extract dry-run branch) | required | Wiring that activates the preview pipeline. |
| AC-6 (distinct preview-log filename) | required | Preventing a preview from shadowing a real-run report is the operator-trust invariant. |
| AC-7 (preview helper tests) | required | Verifies the preview output matches what a real run would do. |
| AC-8 (zero-mutations test) | required | Load-bearing invariant: dry-run never writes. |
| AC-9 (preview-log content test) | required | Ensures operator-visible output is actually populated. |
| AC-10 (seed-160 prose) | required | Discoverability. |
| AC-11 (CHANGELOG) | required | Standard. |
| AC-12 (suite passes) | required | Standard. |
| AC-13 (lint passes) | required | Standard. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-04 | Add a `dry_run` attribute to `UpgradeContext` rather than a separate hook | The hook is already named `post_extract`; splitting it into `post_extract` + `post_extract_dry_run` doubles the maintenance surface. A single hook that checks `ctx.dry_run` is simpler. | Separate hooks per mode — rejected; doubles surface. |
| 2026-06-04 | Preview-log filename distinct from real-run filename | A subsequent real run after a dry-run would overwrite the preview-log with real results — preserving the preview separately means operators can audit both. | Single filename, overwrite-OK — rejected; loses the audit trail. |
| 2026-06-04 | Preview output mirrors real-run report structure | Operators reading both side-by-side can correlate planned vs actual; lower cognitive cost than two distinct shapes. | Custom preview format — rejected; no benefit, more to learn. |
| 2026-06-04 | No interactive confirm | `--dry-run` is sufficient for the documented preview need; interactive confirm adds operator friction and assumes the operator wants to abort mid-migration, which is not the documented use case. | Per-migration interactive confirm — deferred; revisit if evidence warrants. |

## Risks

| Risk | Mitigation |
|---|---|
| Preview helper drifts from the action helper (returns paths that the real run wouldn't actually modify, or vice-versa) | Both helpers share the same walk logic — extract a common `_collect_*_targets(root)` helper that both use, with the action helper performing mutations and the preview helper only reporting. Tests assert the two enumerations agree. |
| Operator runs the real upgrade after reviewing a preview, expecting identical behavior, but state changed between runs | Document the limitation clearly: preview is a snapshot at the time of dry-run; real-run-time state may differ if files changed between runs. Standard `--dry-run` semantic. |
| Preview report grows large on monorepos with many agent docs | Acceptable — the operator asked for the preview; size scales with the migration's actual footprint. Cap at first N entries per migration with `... +K more` tail if needed. |

## Related Work

- **Wave 1p35d (`1p3ay` upgrade migration)** — introduced the migration helpers this change adds previews to.
- **`upgrade_extensions.py`** — extension surface for both.
- **seed-160 `### 1.5.0 upgrade — auto-migration` subsection** — operator-facing prose this change extends.
- **C7 delivery-council advisory C7-DC-1** — surfaced this gap as a follow-up.

## Session Handoff

Surfaced as wave 1p35d C7 advisory C7-DC-1 and C6 review finding F3. Operator selected for queue to the follow-on wave that ships jointly with 1p35d under the **1.5.0** tag.
