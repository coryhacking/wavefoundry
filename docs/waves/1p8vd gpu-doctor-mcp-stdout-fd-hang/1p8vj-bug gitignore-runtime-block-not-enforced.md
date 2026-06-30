# Programmatic .gitignore reconcile — enforce the Wavefoundry runtime ignore block on install + upgrade

Change ID: `1p8vj-bug gitignore-runtime-block-not-enforced`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-29
Wave: `1p8vd gpu-doctor-mcp-stdout-fd-hang` (requires `framework_edit_allowed` + `seed_edit_allowed` at implementation)

## Rationale

A self-hosted target repo (the operator's Windows-test repo) was found missing the `.gitignore` entries for the local semantic index (`.wavefoundry/index/`) and logs (`.wavefoundry/logs/`), so per-machine binary/log artifacts could be committed. Root cause (mapped, cited):

The canonical Wavefoundry ignore block lives **only as prose** in seed-050 (lines ~262–291), and there is **no programmatic writer** — neither `render_platform_surfaces.py`, `setup_wavefoundry.py`, nor `upgrade_wavefoundry.py` ever writes `.gitignore`. Install relies on the LLM agent executing seed-050's "add this block when missing" step; upgrade relies on the agent executing seed-160 line 167 ("verify… add when missing"). Both are agent-prose-only with no enforcement. A repo that wasn't a git repo at install time (no `.gitignore` to edit) never got the block, and **upgrade never self-heals** it. Confirmed by the field: the operator upgraded the affected repo several times and it was never flagged.

By contrast, `render_platform_surfaces.py` already manages `.aiignore` programmatically and idempotently via `render_aiignore()` (read → replace managed block → write) and runs on every install, `wf render-surfaces`, and upgrade Phase 1. The fix is to give `.gitignore` the same treatment so the runtime block is **enforced and self-healing**, not agent-dependent.

## Requirements

1. **Programmatic `.gitignore` reconcile.** Add `render_gitignore_block(repo_root)` to `render_platform_surfaces.py`, mirroring `render_aiignore()`: ensure the canonical Wavefoundry runtime ignore block is present in `<repo>/.gitignore` — create the file if missing, insert the block if absent, and on re-run replace only the framework-managed region (sentinel-delimited) so the operation is idempotent and **preserves all user/other entries**.
2. **Canonical entry list.** The managed block must contain the seed-050 runtime entries: `.wavefoundry/index/`, `.wavefoundry/framework/index/`, `.wavefoundry/logs/`, `.wavefoundry/**/*.lock`, `.wavefoundry/dashboard-server.json`, `.wavefoundry/upgrade-in-progress.json`, `.wavefoundry/guard-overrides.json`, and the `/wavefoundry-*.zip` pack-drop rule.
3. **Wire into the renderer entry point.** Call `render_gitignore_block(repo_root)` from `render_platform_surfaces.main()` so it runs on every `wf setup`, `wf render-surfaces`, `wf upgrade` (Phase 1), and `wave_upgrade()` — making existing repos self-heal on their next upgrade.
4. **Reconcile the seed prose to the programmatic owner.** Update seed-050 (the `.gitignore` block instruction) and seed-160 (the line-167 verify step) so they reference `render_gitignore_block` as the authoritative writer (the agent verifies it ran / no longer hand-maintains the block), keeping seed = source of truth.
5. **No clobber, no behavior change beyond the block.** Existing user `.gitignore` content is preserved verbatim; nothing outside the managed region is touched; no change when the block is already present and current.

## Scope

**Problem statement:** the Wavefoundry `.gitignore` runtime block is agent-prose-only with no programmatic writer, so it silently fails to appear (especially when the repo wasn't git at install) and upgrade never self-heals it.

**In scope:**

- `render_platform_surfaces.py`: `render_gitignore_block()` + wiring into `main()`.
- `seed-050` / `seed-160`: prose reconcile to the programmatic owner.
- `test_render_platform_surfaces.py`: create/append/idempotent/preserve coverage.

**Out of scope:**

- Removing already-committed index/log files from a repo's history (operator action; out of framework scope).
- The `.aiignore` mechanism (unchanged; this mirrors it).
- Broadening the canonical ignore list beyond the seed-050 entries.

## Acceptance Criteria

- [x] AC-1: `render_gitignore_block` creates `.gitignore` with the managed Wavefoundry runtime block when the file does not exist. (`test_creates_gitignore_with_block_when_missing`)
- [x] AC-2: when `.gitignore` exists without the block, the block is appended; a second run is idempotent (no duplicate block/entries). (`test_appends_block_and_is_idempotent`)
- [x] AC-3: pre-existing user entries are preserved verbatim; only the framework-managed region is (re)written. (`test_preserves_user_entries`; loose copies of managed *patterns* are also folded into the block — `test_folds_loose_managed_entries_without_duplicating`)
- [x] AC-4: the managed block contains every seed-050 runtime entry. (`test_creates_gitignore_with_block_when_missing` asserts all 8 canonical entries)
- [x] AC-5: `render_platform_surfaces.main()` calls `render_gitignore_block`, so it runs on install, `render-surfaces`, and upgrade Phase 1. (`render_platform_surfaces.py:1471`; `test_main_wires_gitignore_render`)
- [x] AC-6: seed-050 and seed-160 reference the programmatic render as the authoritative writer. (seed-050 runtime-files bullet + seed-160 line-167 step name `render_gitignore_block` / `wf render-surfaces`)
- [x] AC-7: the full framework suite + docs-lint stay green. (suite 3702 ok; docs-lint ok)

## Tasks

- [x] Read `render_aiignore()` and mirror its managed-block pattern for `.gitignore`.
- [x] Add `render_gitignore_block(repo_root)` with the canonical entry list + sentinel-delimited managed region (under `framework_edit_allowed`).
- [x] Wire it into `render_platform_surfaces.main()`.
- [x] Reconcile seed-050 + seed-160 prose to the programmatic owner (under `seed_edit_allowed`).
- [x] Add `test_render_platform_surfaces.py` cases for AC-1..5. (5 cases in `RenderGitignoreBlockTests`)
- [x] Run the framework suite + docs-lint; confirm green. (suite 3702 ok; docs-lint ok)
- [x] Dogfood: ran `render_gitignore_block` on this repo — folded our loose canonical entries into the managed block (3 stale legacy comment headers hand-removed; see Risks).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| `render_gitignore_block` + wiring | implementer | — | `framework_edit_allowed`; mirror `render_aiignore` |
| seed-050/160 prose reconcile | implementer | render block | `seed_edit_allowed`; point prose at the writer |
| tests + suite/docs-lint | qa-reviewer | both | AC-1..5 + green |

## Serialization Points

- `render_platform_surfaces.py` is the single code surface; the seed edits are independent prose. Open `framework_edit_allowed` for the renderer + `seed_edit_allowed` for the seeds in the same pass.

## Affected Architecture Docs

`N/A` — adds an idempotent file-reconcile to the existing renderer alongside `.aiignore`; no boundary/flow/verification-architecture change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Fresh installs (incl. non-git-at-install) get the block. |
| AC-2 | required | Self-healing on upgrade without duplication. |
| AC-3 | required | Must never clobber operator `.gitignore` content. |
| AC-4 | required | The block must actually cover index/logs/etc. |
| AC-5 | required | Enforcement only works if it's wired into the renderer. |
| AC-6 | important | Seed stays source of truth (no prose/impl drift). |
| AC-7 | required | Suite + docs-lint green. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-29 | Drafted from a field report (Windows-test repo missing index/log `.gitignore` entries across multiple upgrades). Root cause: `.gitignore` block is agent-prose-only (seed-050/160) with no programmatic writer; `render_aiignore` is the established idempotent-writer pattern to mirror. Added to wave `1p8vd` per operator direction. | seed-050:262–291; seed-160:167; `render_platform_surfaces.render_aiignore` (~:1263); field memory `field-feedback-gpu-doctor-mcp-hang` (sibling Windows-test findings). |
| 2026-06-29 | Implemented. Added `render_gitignore_block` (sentinel-delimited managed block; folds loose canonical entries; preserves operator content) + wired into `main()` (unconditional, runs every render/setup/upgrade); reconciled seed-050 + seed-160 prose to name it the authoritative writer. Dogfooded on this repo. | `render_platform_surfaces.py` + seed-050/160 diffs; 5 `RenderGitignoreBlockTests`; suite 3702 ok; docs-lint ok; `git check-ignore` confirms the managed block ignores index/logs/state. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-29 | Programmatic writer in the renderer (runs on install + upgrade), not a reconcile-scan suggestion. | The agent-prose backfill already failed silently across multiple upgrades; a writer self-heals without depending on the agent. `reconcile_scan` is report-only and would reproduce the same "never acted on" failure. | Add `.gitignore` to `reconcile_scan` (report-only — rejected); leave as seed prose (status quo — rejected). |
| 2026-06-29 | Sentinel-delimited managed block (mirror `render_aiignore`). | Idempotent re-write of only the framework region; preserves operator entries. | Append-once with no markers (can't update the list later without duplication). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The managed-block rewrite clobbers operator-added ignore rules. | Mirror `render_aiignore`'s read/replace-only-managed-region pattern; AC-3 asserts user entries preserved. |
| **(impl finding, dogfood)** On a repo with a *prior hand-seeded* block whose **comment wording differs** from the canonical block, the fold strips the matching pattern lines + current-wording comments but can leave OLD-wording comment headers as cosmetic orphans (observed on this self-hosted repo, seeded years ago — 3 stale headers hand-removed). | The actual target class (repos *missing* the block, e.g. the Windows-test repo) gets a clean append with no orphans. Folding dedupes the functional ignore *rules* (the load-bearing part); stale comment text is cosmetic and operator-removable. Not worth the parsing complexity of matching every historical comment wording. |
| Block markers churn existing repos' `.gitignore` on first upgrade (a diff). | One-time, expected reconcile; the block is stable thereafter (idempotent — AC-2). |
| Seed prose and the renderer drift again. | AC-6 reconciles seed-050/160 to name the programmatic owner so the contract is single-sourced. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
