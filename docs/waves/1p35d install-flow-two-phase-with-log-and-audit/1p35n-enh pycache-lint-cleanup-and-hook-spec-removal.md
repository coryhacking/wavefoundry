# Pycache Lint Cleanup And Hook Spec Removal

Change ID: `1p35n-enh pycache-lint-cleanup-and-hook-spec-removal`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p35d install-flow-two-phase-with-log-and-audit`

## Rationale

The consumer hit a recurring `docs-lint` blocker: `__pycache__` should not be checked in: .wavefoundry/framework/scripts/__pycache__`. The MCP server runs Python modules, which creates `.pyc` bytecode under that path; `.gitignore` excludes it, but `docs-lint` flags the directory's presence on disk anyway. The result: every `wave_audit` after an MCP server run fails until the agent cleans up the directory.

Seed-080 originally specified three hooks (pre-edit, post-edit, **pycache-cleanup-on-Bash**); only two are wired in the rendered `settings.json`. The third was a symptom-patch for this exact recurring lint blocker.

**Operator decision: don't ship the third hook; fix the underlying lint behavior instead.**

The cleaner architecture is:

- `docs-lint` excludes `__pycache__` directories (they're transient bytecode that matches `.gitignore` and should not be flagged as "checked in").
- Seed-080 spec drops the pycache-cleanup hook entirely — two hooks, not three.
- `render_platform_surfaces.py` stops emitting the third hook in any host wrapper.

Net effect: smaller surface area (one fewer hook to maintain across host platforms), eliminates the recurring lint blocker, and removes a hook that was treating a symptom rather than addressing the root cause.

## Requirements

1. **`docs-lint` excludes `__pycache__` directories** wherever they appear in the lint scan. The check that emits the "should not be checked in" error skips `__pycache__` (matching `.gitignore` behavior).
2. **`__pycache__` exclusion is named explicitly in `wave_lint_lib`** so it's discoverable and testable. Single source of truth (constant or function) rather than a regex buried inline.
3. **Seed-080 spec drops the pycache-cleanup hook.** Spec reads "two hooks: pre-edit, post-edit" (or whatever the canonical name is) — no third hook mentioned. Any prose describing the third hook is removed.
4. **`render_platform_surfaces.py` does not emit the pycache-cleanup hook** in `.claude/settings.json`, `.cursor/hooks.json`, or any other host config it renders.
5. **Existing host configs in this self-host repo that have the third hook wired are updated** (rendered fresh). Other consumers re-render on next `Refresh wave framework`.
6. **Tests verify**:
   - docs-lint passes on a fixture repo that has `__pycache__` directories present
   - docs-lint still fails on other "should not be checked in" patterns (the exclusion is targeted, not blanket-permissive)
   - render_platform_surfaces output does not include the pycache hook in any rendered config
7. **CHANGELOG 1.5.0 entry includes a bullet for the removal and the lint behavior change.**

## Scope

**In scope:**

- docs-lint `__pycache__` exclusion
- Seed-080 spec edits
- `render_platform_surfaces.py` hook-emission changes
- Updated host configs in this self-host
- Tests for both lint behavior and renderer output

**Out of scope:**

- Broader gitignore-respecting lint behavior beyond `__pycache__` (could be a follow-on; the targeted `__pycache__` exclusion solves the actual recurring blocker)
- Removing other hook surfaces (pre-edit, post-edit remain unchanged)
- Documenting why the hook was originally added (the rationale is captured in the wave's Decision Log; we don't need an in-seed retrospective)

## Acceptance Criteria

- [x] AC-1: docs-lint does NOT flag `__pycache__` directories under `.wavefoundry/framework/scripts/` (or anywhere else) as "checked in".
- [x] AC-2: docs-lint still flags other genuinely-checked-in artifacts that should not be — exclusion is targeted to `__pycache__`, not blanket.
- [x] AC-3: Seed-080 prose specifies two hooks (pre-edit, post-edit); no mention of pycache-cleanup. (seed-080 defers hook contracts to seed-050; seed-050 updated to the two-hook spec, including the matrix row, JSON config, and entrypoint list.)
- [x] AC-4: `render_platform_surfaces.py` does not emit the pycache hook in `.claude/settings.json`.
- [x] AC-5: `render_platform_surfaces.py` does not emit the pycache hook in any other host config (cursor, codex, junie, etc.).
- [x] AC-6: This self-host's `.claude/settings.json` is re-rendered and no longer contains the pycache hook.
- [x] AC-7: Test verifies docs-lint passes with `__pycache__` directories present.
- [x] AC-8: Test verifies docs-lint still fails on other "checked in" patterns.
- [x] AC-9: Test verifies render output across all host platforms excludes the pycache hook helper.
- [x] AC-10: CHANGELOG 1.5.0 entry includes the removal + lint-behavior bullet.
- [x] AC-11: docs-lint passes after all edits (including against this self-host).
- [x] AC-12: Full framework test suite passes.

## Tasks

- [x] Open `seed_edit_allowed` and `framework_edit_allowed` gates
- [x] Locate the `__pycache__` "checked in" lint rule; add the exclusion
- [x] Update seed-080 spec to two-hook formulation (deferred to seed-050; seed-080 already routes hook contracts there)
- [x] Update `render_platform_surfaces.py` to stop emitting the third hook
- [x] Re-render this self-host's `.claude/settings.json`
- [x] Add lint-exclusion tests
- [x] Add renderer-output tests
- [x] Update CHANGELOG
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close gates

## Affected Architecture Docs

`N/A` — removes a hook spec and fixes a lint rule; no architectural surface change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (pycache excluded from lint) | required | Eliminates the recurring blocker. |
| AC-2 (exclusion is targeted) | required | Without this, the fix becomes a permissive bypass that hides real "checked in" issues. |
| AC-3 (seed-080 two-hook spec) | required | Spec and impl must agree. |
| AC-4 (renderer drops hook in .claude/settings.json) | required | Claude renderer must match the two-hook spec. |
| AC-5 (renderer drops hook in all other host configs) | required | Same coverage across cursor, codex, junie, etc. |
| AC-6 (self-host config refreshed) | required | Dogfood — we don't ship a self-host with the legacy hook. |
| AC-7 (test: lint passes with pycache present) | required | Verifies the targeted exclusion works. |
| AC-8 (test: lint still fails on other checked-in patterns) | required | Verifies the exclusion is targeted, not blanket. |
| AC-9 (test: renderer output excludes the hook) | required | Verifies the renderer change holds across host wrappers. |
| AC-10 (CHANGELOG) | required | Discoverability — operators upgrading need to know the hook is gone. |
| AC-11 (docs-lint passes against this self-host) | required | Dogfood; the self-host runs the new exclusion. |
| AC-12 (framework test suite passes) | required | Regression discipline. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Remove the pycache hook entirely; fix the lint exclusion instead | Operator-directed: "I don't know that I really care about the pycache hook right now. Should we just remove it as a framework hook?" + "docs-lint excluding pycache is a great addition." The hook treated a symptom; the exclusion fixes the root. | Wire the hook (original C5 plan) — rejected per operator; symptom-patch with more surface area. |
| 2026-06-03 | Scope the exclusion narrowly to `__pycache__` rather than broad gitignore-respecting | Targeted fix solves the observed recurring blocker without the design work of generalizing to all gitignored patterns. Generalization can be a follow-on if other patterns hit the same issue. | Broad gitignore-respecting lint — rejected; broader change for unclear additional benefit. |

## Risks

| Risk | Mitigation |
|---|---|
| Some other transient artifact pattern hits the same "checked in" rule | If it does, the targeted exclusion approach extends incrementally. The narrow fix is reversible if pattern emerges; the broad-respect-gitignore approach is harder to walk back. |
| Existing consumer installs have the third hook wired and won't auto-remove on upgrade | Re-running `Refresh wave framework` after upgrading regenerates host configs without the hook. Document this in the CHANGELOG bullet. |
| Test fixture that exercises `__pycache__` creates real bytecode on the test runner | Tests use synthetic mkdir; no actual Python execution. Isolated. |

## Related Work

- **Seed-080 (host-config rendering)** — the canonical specification surface for the hook contract. Edited here.
- **`render_platform_surfaces.py`** — the implementation surface. Edited here.
- **`.gitignore`** — already excludes `__pycache__`; the lint behavior is now consistent with that.

## Session Handoff

Admitted to `1p35d` as an independent cleanup change. Can implement in parallel with C3, C4. Sequenced earlier rather than later so the install flow can be tested against a lint-clean state.
