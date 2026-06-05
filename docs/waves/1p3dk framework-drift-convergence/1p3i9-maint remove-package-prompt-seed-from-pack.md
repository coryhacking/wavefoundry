# Remove package-wavefoundry seed from consumer pack

Change ID: `1p3i9-maint remove-package-prompt-seed-from-pack`
Change Status: `implemented`
Owner: framework-maintainer
Status: implemented
Last verified: 2026-06-05
Wave: 1p3dk framework-drift-convergence

## Rationale

Seed-240 (`240-package-wavefoundry.prompt.md`) describes the `Package Wavefoundry` operator entry point — but only the wavefoundry repo itself packages; consumer projects run `Upgrade wave framework` instead. Shipping the seed to every consumer is category-error dead weight: the seed's own body said "Run this from the Wavefoundry repository root." Wave `1p3dk`'s drift-convergence theme is "no dual-valid states and no unenforced claims"; this is the seed-equivalent — no seeds shipped to consumers for workflows consumers cannot run.

The cleaner fix is not an exclusion list in `build_pack.py` (which would treat a category error as configuration) but to remove the file from the seeds directory entirely. The seeds dir becomes definitionally "what ships to consumers." The wavefoundry-internal operator entry lives at `docs/prompts/package-wavefoundry.prompt.md` in the wavefoundry source tree — already a clean hand-authored 85-line file with no marker regions — and stays as the canonical source of truth.

## Requirements

1. `.wavefoundry/framework/seeds/240-package-wavefoundry.prompt.md` is deleted from the wavefoundry repo.
2. `docs/prompts/package-wavefoundry.prompt.md` carries the Keep-a-Changelog rewrite of step 4 (ported from seed-240's 1p3i6-era rewrite) so the operator-facing entry reflects the post-1p3i6 CHANGELOG flow.
3. `.wavefoundry/framework/README.md` is updated — the two seed-by-filename references (packaging paragraph + seed file listing) are corrected or removed.
4. Consumer projects auto-prune the seed via MANIFEST-prune on next `wave_upgrade` (no explicit migration step required — old MANIFEST listed the seed; new MANIFEST will not; `prune_framework.py` deletes the now-absent path).
5. No orphan `docs/prompts/package-wavefoundry.prompt.md` cleanup is required in consumer trees because consumers never produced one (their renderer never had reason to — packaging is wavefoundry-internal).
6. Cross-references from other seeds (040, 100, 150, 160) continue to work — they reference the rendered path `docs/prompts/package-wavefoundry.prompt.md` (which exists in the wavefoundry repo only) guarded by "when present" conditions that already handle the consumer absence case.

## Scope

**Problem statement:** A wavefoundry-internal operator prompt lives in the framework seeds directory, ships in every consumer pack, and renders into consumer trees as dead weight describing a workflow consumers cannot run.

**In scope:**

- Port Keep-a-Changelog rewrite from seed-240 step 4 → `docs/prompts/package-wavefoundry.prompt.md`
- Delete `.wavefoundry/framework/seeds/240-package-wavefoundry.prompt.md` from the wavefoundry repo
- Update `.wavefoundry/framework/README.md` (2 seed-by-filename references)
- CHANGELOG bullet documenting the removal and the conceptual reframing of "what counts as a seed"

**Out of scope:**

- Adding a generic exclusion-list mechanism in `build_pack.py` (rejected — treats category error as configuration; no second wavefoundry-internal seed exists today)
- Auto-cleanup of orphan rendered `docs/prompts/package-wavefoundry.prompt.md` in consumer trees (no consumer is known to have one — packaging is wavefoundry-internal and consumer renderers never produced it)
- Refactoring the other cross-references (seeds 040 / 100 / 150 / 160) — their "when present" guards already handle the absence cleanly

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/framework/seeds/240-package-wavefoundry.prompt.md` does not exist in the wavefoundry repo working tree.
- [x] AC-2: `docs/prompts/package-wavefoundry.prompt.md` step 4 references root `CHANGELOG.md` (Keep-a-Changelog format), not `.wavefoundry/CHANGELOG.md` and not the narrative-prose diagnostic.
- [x] AC-3: `docs/prompts/package-wavefoundry.prompt.md` Options section does not list `--skip-changelog-diagnostic`.
- [x] AC-4: `.wavefoundry/framework/README.md` does not list `240-package-wavefoundry.prompt.md` in the seeds inventory; the packaging paragraph references `docs/prompts/package-wavefoundry.prompt.md` (wavefoundry-internal) instead of the seed.
- [x] AC-5: Repo-wide grep for `240-package` and `seed-240` returns zero hits in live surfaces (verified — only references remaining are in historical journals / wave docs / CHANGELOG entries, which are intentionally preserved as supersession breadcrumbs).
- [x] AC-6: `docs-lint` returns clean (`exit 0`, no errors).
- [x] AC-7: A pack built from the current repo does not contain `.wavefoundry/framework/seeds/240-package-wavefoundry.prompt.md`. (Verified against `wavefoundry-1.5.0.p3ib.zip`: `unzip -l ... | grep 240-package` returns zero hits.)

## Tasks

- [x] Edit `docs/prompts/package-wavefoundry.prompt.md` step 4 — Keep-a-Changelog framing, root canonical, drop diagnostic reference.
- [x] Edit `docs/prompts/package-wavefoundry.prompt.md` Options — remove `--skip-changelog-diagnostic` row.
- [x] `git rm .wavefoundry/framework/seeds/240-package-wavefoundry.prompt.md`.
- [x] Edit `.wavefoundry/framework/README.md` packaging paragraph — replace seed-240 reference with `docs/prompts/package-wavefoundry.prompt.md` (wavefoundry-internal).
- [x] Edit `.wavefoundry/framework/README.md` seeds inventory — remove the `240-package-wavefoundry.prompt.md` line.
- [x] Run docs-lint and resolve any drift.
- [x] Add CHANGELOG bullet under `[1.5.0]`.
- [x] Repo-wide grep audit confirms zero remaining references in live (non-historical) surfaces.

## Agent Execution Graph


| Workstream                | Owner               | Depends On | Notes |
| ------------------------- | ------------------- | ---------- | ----- |
| Port content              | framework-maintainer | —          | Step 4 + Options edits to docs/prompts/. |
| Delete seed               | framework-maintainer | Port content | Avoid deletion before the operator-facing prompt is up-to-date. |
| Update framework/README   | framework-maintainer | Delete seed | Reference updates to reflect the new home. |
| Verification              | framework-maintainer | All above  | grep audit + docs-lint. |


## Serialization Points

- `docs/prompts/package-wavefoundry.prompt.md` is touched by two Edit operations — serialize the edits within that file.
- The seed deletion must follow the docs/prompts content port so the operator-facing surface is current before the seed disappears (no transient window where both files are stale or absent).

## Affected Architecture Docs

N/A — change is confined to seed-and-prompt surface (no domain map / layering / cross-cutting impact).

## AC Priority


| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | The deletion IS the change. |
| AC-2 | required      | Operator-facing CHANGELOG guidance must be Keep-a-Changelog per 1p3i6. |
| AC-3 | required      | Stale flag reference would mislead operators. |
| AC-4 | required      | Framework README is the single inventory; stale entry leaks the deletion intent. |
| AC-5 | required      | Live references must not point at a deleted seed. Historical references in journals/waves/CHANGELOG stay. |
| AC-6 | required      | docs-lint must stay clean. |
| AC-7 | required      | The pack contract — the seed is genuinely gone from consumer surfaces. |


## Progress Log


| Date       | Update                                                                  | Evidence |
| ---------- | ----------------------------------------------------------------------- | -------- |
| 2026-06-05 | Change admitted into wave 1p3dk; port + delete + README updates landed. | seed-240 deleted via `git rm`; framework/README.md updated; docs/prompts/ step 4 rewritten. |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-05 | Delete the seed entirely; do not maintain an exclusion list in `build_pack.py`. | Exclusion list treats a category error as configuration. Deletion fixes the category — "seeds" become definitionally "what ships to consumers." | (a) Add `WAVEFOUNDRY_INTERNAL_SEEDS` exclusion constant (rejected — over-design for n=1 case); (b) Move seed to a new `.wavefoundry/internal/` directory (rejected — operator entry is already at `docs/prompts/package-wavefoundry.prompt.md`; new dir adds layering with no payoff). |
| 2026-06-05 | Keep `docs/prompts/package-wavefoundry.prompt.md` as the canonical hand-authored operator entry in the wavefoundry repo. | Already exists, no marker regions, 85 lines covering everything needed. Operator already invokes via this path. | (a) Move to `docs/contributing/package-wavefoundry.md` (rejected — operators don't expect contributing-doc location for a workflow they run; muscle memory is `docs/prompts/`). |
| 2026-06-05 | Skip orphan-cleanup for consumer `docs/prompts/package-wavefoundry.prompt.md`. | No consumer is known to have one — packaging is wavefoundry-internal and consumer renderers never produced it. Audit-and-skip per "audit means audit" rule. | (a) Add post-extract cleanup step (rejected — speculative cleanup for a hypothetical orphan). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A consumer who somehow has `docs/prompts/package-wavefoundry.prompt.md` rendered (e.g., from a fork) sees an orphan file describing a workflow they cannot run. | Document the situation in the CHANGELOG bullet so the operator can manually delete if encountered. No auto-cleanup. |
| The MANIFEST-prune step misses the seed (e.g., consumer's old manifest lacks the seed entry). | Both old and new manifests are validated under `prune_framework.py`'s standard flow — same hot-path as every other seed pruned in prior waves. No special-casing needed. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
