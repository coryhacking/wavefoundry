# Upgrade Dry-Run Preview Of Migration Effect

Change ID: `1p3b6-enh upgrade-dry-run-preview-of-migration-effect`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-04
Wave: TBD (slated for the follow-on wave admitting `1p397` + `1p399`; joint 1.5.0 release)

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

- [ ] AC-1: `UpgradeContext` exposes a `dry_run` boolean attribute populated from the upgrade orchestrator's `--dry-run` flag.
- [ ] AC-2: `_preview_role_field_backfill(root)` returns the list of paths that would be modified, with the slug that would be inserted into each, performing zero filesystem mutations.
- [ ] AC-3: `_preview_pycache_launcher_deletion(root)` returns the list of launcher files that would be deleted, performing zero filesystem mutations.
- [ ] AC-4: `_preview_settings_pycache_strip(root)` returns a description of the row that would be stripped (or None when no row matches), performing zero filesystem mutations.
- [ ] AC-5: `post_extract(ctx)` checks `ctx.dry_run` and calls the preview variants when True; writes the preview-log to `.wavefoundry/logs/upgrade-migration-1.5.0.preview.log`; prints a concise stderr summary.
- [ ] AC-6: Dry-run preview-log filename is distinct from the real-run filename so a preview doesn't shadow a subsequent real run's report.
- [ ] AC-7: Tests verify each preview helper's correctness against fixture state.
- [ ] AC-8: Test verifies `post_extract` in dry-run mode performs zero mutations on every fixture (file state byte-identical pre-and-post).
- [ ] AC-9: Test verifies the dry-run preview-log is written and contains the expected migration sections + action records.
- [ ] AC-10: seed-160 prose updated: the existing `### 1.5.0 upgrade — auto-migration` subsection gains a paragraph naming the `--dry-run` preview path and where the preview-log lands.
- [ ] AC-11: CHANGELOG entry under 1.5.0.
- [ ] AC-12: Full framework test suite passes.
- [ ] AC-13: docs-lint passes.

## Tasks

- [ ] Open `seed_edit_allowed` and `framework_edit_allowed` gates
- [ ] Add `dry_run` to `UpgradeContext` (or equivalent)
- [ ] Wire the orchestrator `--dry-run` flag through to extension hooks
- [ ] Implement `_preview_role_field_backfill`
- [ ] Implement `_preview_pycache_launcher_deletion`
- [ ] Implement `_preview_settings_pycache_strip`
- [ ] Add dry-run branch to `post_extract`
- [ ] Write preview-log to `.wavefoundry/logs/upgrade-migration-1.5.0.preview.log`
- [ ] Add tests
- [ ] Update seed-160 prose
- [ ] Update CHANGELOG
- [ ] Run framework test suite
- [ ] Run docs-lint
- [ ] Close gates

## Affected Architecture Docs

`N/A` — extends an existing extension surface; no architectural boundary change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (UpgradeContext.dry_run) | required | Signaling mechanism the migration hooks consult. |
| AC-2, AC-3, AC-4 (per-migration preview helpers) | required | Each migration must have a preview path; without it the gap stays for that migration's surface. |
| AC-5 (post_extract dry-run branch) | required | Wiring that activates the preview pipeline. |
| AC-6 (distinct preview-log filename) | required | Preventing a preview from shadowing a real-run report is the operator-trust invariant. |
| AC-7 (preview helper tests) | required | Verifies the preview output matches what a real run would do. |
| AC-8 (zero-mutations test) | required | Load-bearing invariant: dry-run never writes. |
| AC-9 (preview-log content test) | required | Ensures operator-visible output is actually populated. |
| AC-10 (seed-160 prose) | required | Discoverability. |
| AC-11 (CHANGELOG) | required | Standard. |
| AC-12, AC-13 | required | Standard hygiene. |

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
