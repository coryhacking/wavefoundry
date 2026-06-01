# Rename to CHANGELOG.md, Relocate to Project Level, Cumulative Per-Version Sections

Change ID: `131at-enh changelog-cumulative-project-level`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: TBD

## Rationale

`RELEASE_NOTES.md` currently lives at `.wavefoundry/framework/RELEASE_NOTES.md`, inside the framework drop. The framework directory is overwritten wholesale on every upgrade — meaning the file is replaced with the new version's content each time. In principle this is fine (the wavefoundry source repo accumulates history, downstream consumers always get the latest snapshot), but it makes the file conceptually a framework-internal artifact rather than what it actually is: **project-level operator-facing release history**.

Three changes to the model:

1. **Rename** to `CHANGELOG.md`. Stronger filename convention — GitHub renders `CHANGELOG.md` specially alongside README, and readers looking for release history check there first. `RELEASE_NOTES.md` is real but noticeably less discoverable. The naming switch costs nothing (one-time rename) and improves operator findability.

2. **Relocate.** Move the file from `.wavefoundry/framework/RELEASE_NOTES.md` to `.wavefoundry/CHANGELOG.md` — alongside the project-level `bin/`, `git-hooks/`, and `README.md`. Signals to operators (and to the framework's own upgrade lifecycle) that release history is a project-level concern, not a framework-internal one. Combined with the rename, the destination path is also more clearly a project-level artifact.

3. **Cumulative per-version sections.** One section per release version (`## MAJOR.MINOR.PATCH — YYYY-MM-DD`). Same-version repackages don't append delta-style build entries — they **rewrite that version's section** as cohesive narrative prose covering the most important points across all builds of that version. **The structural unit is the version, not the build.** Build numbers do not appear in the file at all — they live in git history, the `VERSION` file, and the dist zip filename. The changelog describes what the version delivers.

**Important: not Keep-a-Changelog format.** The community `CHANGELOG.md` convention often follows keepachangelog.com's structured `Added / Changed / Deprecated / Removed / Fixed / Security` sections. **Wavefoundry deliberately departs from that structure** — sections are cohesive narrative prose per version, focused on operator impact, not delta categories. seed-240 must be explicit about this departure so the packaging agent doesn't pattern-match to Keep-a-Changelog when seeing the filename.

Today's seed-240 already says "edit the existing entry in place" for same-semver repackages. The strengthened requirement: that in-place edit must produce **operator-readable cohesive prose**, not a chronological log of "build XXX added Y, build YYY added Z." The agent doing the packaging is responsible for the narrative quality.

## Approach

### Relocation

- Physical move: `.wavefoundry/framework/RELEASE_NOTES.md` → `.wavefoundry/CHANGELOG.md` in the wavefoundry source repo.
- Zip layout: `build_pack.py` ships the file at `.wavefoundry/CHANGELOG.md` directly. **Breaks the "every zip entry begins with `.wavefoundry/framework/`" invariant** — accepted, documented in seed-240 and in build_pack.py comments.
- Upgrade lifecycle: on `wave_upgrade` / `wave-upgrade`, the consumer's `.wavefoundry/CHANGELOG.md` is replaced with the zip's copy (the wavefoundry repo's accumulated history). The wavefoundry repo is the single source of truth; downstream consumers receive a current snapshot, never edit it locally.
- Old-path cleanup: when consumers upgrade from a pre-relocation pack, `.wavefoundry/framework/RELEASE_NOTES.md` must be pruned. MANIFEST-based prune (`prune_framework.py --old-manifest`) handles this automatically as long as the new MANIFEST does not list the old path AND the new MANIFEST entry includes the new path. Verify during implementation.

### Cumulative per-version section semantics

Each version section is **one cohesive prose block**, not a chronological diff log. Quality criteria:

- **Operator impact, not implementation chronology.** A section describes what the version *delivers* to the operator (capabilities, fixes, breaking changes, required actions), not when each piece landed.
- **Reads as a unified narrative.** A reader scanning the section sees a coherent story for the release. No "build XXX added X. Build YYY added Y." Build numbers do not appear in the file.
- **Required-action callouts are explicit.** Cache invalidation (e.g., `GRAPH_BUILDER_VERSION` bumps), MCP server restart needs, and breaking changes get their own sub-section or callout — operators reading the section must be able to skim and find "do I need to do anything?" without parsing prose.
- **Wave reference at the end.** "Full per-change docs: wave `<wave-id>`." One line, traceability into the wavefoundry repo.

### Same-version repackage flow

1. Build script reads the existing `.wavefoundry/CHANGELOG.md`.
2. Detect whether the version being packaged already has a section (by header match on `## MAJOR.MINOR.PATCH`).
3. If yes: **the packaging agent rewrites the section**. The build script cannot generate cohesive prose; this is human/agent judgment. seed-240 is the instruction set for the agent.
4. If no: insert a new section at the top of the file (newest first). Same prose quality criteria.

The build script's role is mechanical: enforce the format (header pattern, date stamp), reject sections that look like delta logs (heuristic: count of "build " occurrences in a section; flag if structurally chronological). Final prose quality is the agent's responsibility — seed-240 spells out the criteria.

### Build-number absence

Build numbers do not appear in `CHANGELOG.md` at all — not as sub-sections, not as footers, not inline. They live in git history (`git log` shows the `VERSION` file bump per build), in the `VERSION` file itself, and in the dist zip filename (`wavefoundry-1.2.1.319y.zip`). A customer reporting an issue on `1.2.1+319y` ties their report to the `1.2.1` section via the major.minor.patch prefix; the build number tells the framework owner *which packaging iteration* of `1.2.1`, but the changelog describes what `1.2.1` as a whole delivers to operators.

## Requirements

1. `.wavefoundry/framework/RELEASE_NOTES.md` no longer exists; `.wavefoundry/CHANGELOG.md` is the canonical location.
2. `build_pack.py` ships the file at `.wavefoundry/CHANGELOG.md` in the zip (one path outside `.wavefoundry/framework/`).
3. `build_pack.py` reads the existing file before packaging; if the version being packaged has no section, the build proceeds normally; if a section exists, the build proceeds without error (the agent has already updated it per seed-240) but emits a diagnostic if the section looks chronological (heuristic: more than 2 "build " occurrences inside the section body).
4. `prune_framework.py` removes the old `.wavefoundry/framework/RELEASE_NOTES.md` on upgrade from a pre-relocation pack.
5. Consumer upgrade flow places the file at `.wavefoundry/CHANGELOG.md` and overwrites any existing content (single source of truth).
6. seed-240 is rewritten to describe the new flow: relocation, cumulative per-version section semantics, same-version rewrite criteria, prose quality bar.
7. The wavefoundry repo's own `.wavefoundry/CHANGELOG.md` is migrated: existing per-version content from `.wavefoundry/framework/RELEASE_NOTES.md` is moved to the new path, with each version's section already rewritten to cohesive prose (one-time migration pass, performed as part of this change).
8. Documentation referencing the old path is updated (`AGENTS.md`, `CLAUDE.md`, per-project rendered prompts, `docs/references/dashboard-install-upgrade.md` if applicable).

## Scope

**Problem statement:** Release notes live inside the framework drop, treated as a framework-internal artifact. Same-version repackaging encourages append-style delta logs rather than cohesive per-version narratives. Operators reading release notes see chronology, not impact.

**In scope:**

- `.wavefoundry/CHANGELOG.md` — new canonical location, with one-time migration of existing content.
- `.wavefoundry/framework/scripts/build_pack.py` — zip layout update, format-validation diagnostic.
- `.wavefoundry/framework/scripts/prune_framework.py` — old-path removal on upgrade.
- `.wavefoundry/bin/wave-upgrade` and any related upgrade CLI — verify the new path is created/overwritten correctly.
- `.wavefoundry/framework/seeds/240-package-wavefoundry.prompt.md` — rewritten for new flow.
- `docs/prompts/package-wavefoundry.prompt.md` — re-rendered from updated seed.
- `AGENTS.md`, `CLAUDE.md`, per-project doc references — path updates.
- Wave `wave_upgrade` MCP tool seed (if it documents the old path) — path update.

**Out of scope:**

- Per-consumer customization (downstream projects can't edit the file persistently — it gets overwritten on upgrade). If a use case emerges for project-local notes alongside framework history, that's a separate change.
- Automated prose generation (LLM-driven section rewriting from change-doc deltas). Quality is human/agent judgment; spec stays at "the packaging agent writes the prose per seed-240 criteria."
- Migrating to a structured format (YAML / JSON release manifests). `CHANGELOG.md` stays human-readable markdown.
- Versioning history of the `CHANGELOG.md` file itself across upgrades. Single source of truth = wavefoundry repo's git history.
- Adopting the Keep-a-Changelog spec (`Added / Changed / Deprecated / Removed / Fixed / Security` per-version subsections). Deliberately rejected — cohesive narrative prose per version is the intended structure.
- Conditional inclusion in the zip (e.g., skip if unchanged). Always ship.

## Acceptance Criteria

**Relocation:**

- [ ] AC-1: `.wavefoundry/CHANGELOG.md` exists at the new path with the migrated content.
- [ ] AC-2: `.wavefoundry/framework/RELEASE_NOTES.md` does not exist post-migration.
- [ ] AC-3: `build_pack.py` produces a zip containing `.wavefoundry/CHANGELOG.md` at the new path.
- [ ] AC-4: `build_pack.py` does NOT include `.wavefoundry/framework/RELEASE_NOTES.md` (verified via `unzip -l`).
- [ ] AC-5: `prune_framework.py` removes the old path on upgrade when the old MANIFEST listed it.

**Cumulative semantics:**

- [ ] AC-6: Migrated content has one section per release version. No per-build subsections, no build-number footers, no inline build-number references — build numbers do not appear in the file.
- [ ] AC-7: Each migrated section reads as cohesive narrative prose (operator-readable, impact-focused, not a chronology). Manual review at implementation time.
- [ ] AC-8: Each section has a required-action callout when applicable (cache invalidation, MCP server restart, breaking changes).
- [ ] AC-9: Each section ends with a one-line wave reference (`Full per-change docs: wave <wave-id>`).
- [ ] AC-10: `build_pack.py` emits a diagnostic when a same-version section looks chronological (heuristic: >2 "build " occurrences inside the section body, OR any `+XXXX` build-number reference).

**Build / upgrade flow:**

- [ ] AC-11: `build_pack.py` detects a same-version repackage (existing `## MAJOR.MINOR.PATCH` section) and proceeds without modifying the agent-written prose; only stamps/validates.
- [ ] AC-12: Consumer upgrade flow places the file at `.wavefoundry/CHANGELOG.md` and overwrites the consumer's prior content.
- [ ] AC-13: Upgrading from a pre-relocation pack (old MANIFEST has `.wavefoundry/framework/RELEASE_NOTES.md`) prunes the old path AND creates the new path in one upgrade pass.

**seed-240 update:**

- [ ] AC-14: seed-240 documents the new path.
- [ ] AC-15: seed-240 documents cumulative per-version section semantics with prose quality criteria.
- [ ] AC-16: seed-240 includes a same-version-rewrite checklist for the packaging agent (operator-impact framing, narrative cohesion, no chronological structure, required-action callouts, traceability footer).
- [ ] AC-17: seed-240 documents the zip-layout invariant break (one entry outside `.wavefoundry/framework/`) and the rationale.
- [ ] AC-18: `docs/prompts/package-wavefoundry.prompt.md` re-rendered from updated seed-240.

**Cross-doc consistency:**

- [ ] AC-19: References to the old path in `AGENTS.md`, `CLAUDE.md`, and any other surface are updated.
- [ ] AC-20: `docs-lint` passes via post-edit hook.

## Tasks

- [ ] Phase 0 — audit code/doc references to `.wavefoundry/framework/RELEASE_NOTES.md`; record paths in Decision Log
- [ ] Phase 0 — verify MANIFEST-based pruning handles relocation cleanly (or design the migration step)
- [ ] Open `seed_edit_allowed` gate
- [ ] Rewrite seed-240 with new path, cumulative semantics, prose criteria, zip-layout invariant note
- [ ] Re-render `docs/prompts/package-wavefoundry.prompt.md` from updated seed-240
- [ ] Close `seed_edit_allowed` gate
- [ ] Open `framework_edit_allowed` gate
- [ ] Migrate existing `.wavefoundry/framework/RELEASE_NOTES.md` content to `.wavefoundry/CHANGELOG.md` with cohesive per-version sections (one-time)
- [ ] Delete old path
- [ ] Update `build_pack.py` zip layout (include new path; exclude old path)
- [ ] Add `build_pack.py` chronological-section diagnostic
- [ ] Update `prune_framework.py` to handle the relocation (if not already covered by MANIFEST diff)
- [ ] Update upgrade CLI scripts to place file at new path
- [ ] Update `AGENTS.md`, `CLAUDE.md`, and any other doc references
- [ ] Close `framework_edit_allowed` gate
- [ ] Repackage; verify zip layout, verify diagnostic doesn't fire on the migrated content
- [ ] Test upgrade flow against a consumer project (manual or scripted): old path pruned, new path created
- [ ] Mark change `implemented`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| phase-0-audit | Engineering | — | Sequential; outputs feed every other workstream |
| seed-240-rewrite | Engineering | phase-0-audit | Pure seed/docs |
| content-migration | Engineering | seed-240-rewrite | Apply the new criteria to existing content |
| build-pack-update | Engineering | phase-0-audit | Code edits to build_pack.py |
| prune-upgrade-update | Engineering | phase-0-audit | Code edits to prune_framework.py + upgrade CLI |
| cross-doc-updates | Engineering | phase-0-audit | AGENTS.md, CLAUDE.md, etc. |
| field-verify | Engineering | All above | End-to-end test against a consumer project |

## Serialization Points

- `.wavefoundry/CHANGELOG.md` itself — migration writes it; subsequent edits must not race with the build script's format-validation pass.
- `build_pack.py` — single file holding the zip layout + diagnostic logic; coordinate edits.
- seed-240 — both prose criteria and same-version checklist live here; one edit pass.

## Affected Architecture Docs

- N/A — this change renames a file, moves it, and updates the packaging workflow. No architectural boundary or data flow change. `docs/references/dashboard-install-upgrade.md` may need a path-update if it references the old `RELEASE_NOTES.md` filename.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Relocation foundation |
| AC-2 | required | Old path absent — no dual-location confusion |
| AC-3 | required | Zip ships correct path |
| AC-4 | required | Zip excludes old path |
| AC-5 | required | Upgrade prunes old path |
| AC-6 | required | Cumulative structure |
| AC-7 | required | Prose quality bar |
| AC-8 | required | Operator-actionable callouts |
| AC-9 | required | Wave reference for traceability |
| AC-10 | important | Diagnostic guardrail against drift back to chronological log or build-number references |
| AC-11 | required | Build-script behavior on same-version repackage |
| AC-12 | required | Consumer upgrade path |
| AC-13 | required | Migration: old → new in one upgrade pass |
| AC-14 | required | seed-240 path |
| AC-15 | required | seed-240 prose criteria |
| AC-16 | required | seed-240 same-version checklist |
| AC-17 | required | seed-240 zip invariant note |
| AC-18 | required | Per-project prompt regenerated |
| AC-19 | required | Cross-doc consistency |
| AC-20 | required | Lint gate |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Relocate to `.wavefoundry/CHANGELOG.md` | Release notes are project-level operator-facing history, not framework-internal artifact | Keep at `.wavefoundry/framework/` (rejected — current location implies framework-internal lifecycle); ship to both paths (rejected — dual sources of truth) |
| 2026-06-01 | Single source of truth = wavefoundry repo's `.wavefoundry/CHANGELOG.md`; consumer copy is overwritten on upgrade | Consumers don't edit release notes; they read them. Overwrite is the simplest correct behavior | Per-consumer cumulative log (rejected — out of scope per user direction; would require append-merge logic in upgrade flow) |
| 2026-06-01 | Same-version repackage = rewrite section, not append | User-specified: "If we package multiple times with the same version number then rework the wording to include the new enhancements so don't just prepend. It should be relevant and meaningful prose of the most important points." | Append per-build subsections (rejected — produces chronological log, not narrative) |
| 2026-06-01 | Prose quality is agent/human responsibility; build script enforces format only | LLM-driven section rewriting from change-doc deltas is out of scope; quality bar comes from seed-240 criteria | Automate prose generation (out of scope) |
| 2026-06-01 | Build script emits diagnostic for chronological-looking sections (heuristic: >2 "build " in body) | Cheap guardrail against drift back to delta-log style; not enforcement, just a signal | Strict enforcement (rejected — too rigid, would block legitimate cases mentioning build numbers in prose); no diagnostic (rejected — drift would go unnoticed) |
| 2026-06-01 | Break the "every zip entry under `.wavefoundry/framework/`" invariant | Relocation requires one entry outside framework/; the invariant break is intentional and documented | Keep file in framework/, move at upgrade time (rejected — adds upgrade complexity for a one-file relocation; the zip-layout break is the simpler change) |
| 2026-06-01 | Rename to `CHANGELOG.md` | Stronger filename convention; GitHub renders it specially; readers look there first | Keep `RELEASE_NOTES.md` (rejected — less discoverable); `HISTORY.md` (rejected — uncommon) |
| 2026-06-01 | Deliberately depart from Keep-a-Changelog spec | The spec's `Added / Changed / Deprecated / Removed / Fixed / Security` structure is delta-log style; we want cohesive narrative prose per version focused on operator impact | Adopt Keep-a-Changelog (rejected — wrong shape for the operator-impact narrative goal) |
| 2026-06-01 | Build numbers do not appear in `CHANGELOG.md` at all | Build numbers are packaging-iteration metadata, not release-content metadata; the changelog describes what the *version* brought to operators. Build-number traceability lives in git history, the `VERSION` file, and the dist zip filename | Per-build subsections (rejected — chronological log); one-line traceability footer per version (rejected — still treats builds as changelog-relevant when they aren't) |
| TBD (Phase 0) | MANIFEST migration mechanism | (verified during Phase 0 audit) | Manual prune step; automated MANIFEST diff |

## Risks

| Risk | Mitigation |
|---|---|
| Existing consumer projects have edits to `.wavefoundry/framework/RELEASE_NOTES.md` that get lost on rename+relocation | Document in the migration release section: "changelog is now a wavefoundry-managed file at a new path; project-local edits will not survive upgrade." Realistically, no consumer should be editing release notes — they're operator-readable history, not configuration |
| Consumers (or external tooling) referencing the old `RELEASE_NOTES.md` filename break on rename | Cross-doc update sweep; the migration version's section in the new `CHANGELOG.md` calls out the rename explicitly so operators reading it understand the new location |
| MANIFEST-based prune doesn't handle relocation cleanly (old MANIFEST lists `.wavefoundry/framework/RELEASE_NOTES.md`, new MANIFEST lists `.wavefoundry/CHANGELOG.md` — but the prune logic only prunes paths that were in the old MANIFEST and absent from the new one. The new path was never in either old MANIFEST. So the prune should work correctly, but verify) | Phase 0 audit; add an explicit test in build_pack.py / prune_framework.py if needed |
| Consumer upgrade flow doesn't create the new path's parent directory (`.wavefoundry/` exists, but upgrade flow may not create files there) | Upgrade flow already writes to `.wavefoundry/` (creates `index/`, `logs/`, etc.) — verify during Phase 0 |
| Same-version rewrite quality is inconsistent across operators | seed-240 explicit checklist; chronological-section diagnostic catches the most common drift |
| Operators using the relocated file as a substitute for changelog tooling expect things the file isn't (machine-readable manifest, per-change deltas) | seed-240 explicitly states "operator-readable markdown, not a machine-readable manifest" |
| Downstream consumers reading the file via tooling (CI scrapers, dashboard surfaces) break on path change | Cross-doc update sweep + a one-line migration note in the relocated file pointing readers to the new path |

## Related Work

- Adjacent to `131ar` (sync MCP tool descriptions with shipped capabilities) — both touch seed-240. Sequencing: land `131at` first (the relocation + workflow change), then `131ar` (the description sync), so the docs-sync change can reference the new location in its release-notes update.
- Companion to wave 13129's seed-240 hardening (which originally enforced the same-version-edit-in-place rule). This change strengthens that rule from "edit" to "rewrite as cohesive prose."
- No dependency on `1319s` (construction-call edges). Independent lifecycle.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
