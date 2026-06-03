# Unify Review Surfaces As Specialists

Change ID: `1p33i-enh unify-review-surfaces-as-specialists`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-03
Wave: `1p337 config-key-back-compat-hotfix` (admitted as the fourth change — operator-directed admission alongside the back-compat fix, docs migration, and default-enable changes; packaged for 1.4.0)

## Rationale

Today's review-surface taxonomy is asymmetric. Red team is a specialist (`docs/agents/specialists/red-team.md`) — an agent role that can be invoked. Wave Council is coordinated by `council-moderator` at `docs/agents/council-moderator.md` (top-level, not a specialist). Archetype Council has no role doc at all — operators only discover the surface via seed-236 and the shortcut phrase.

That asymmetry is a discoverability and naming bug. An operator browsing `docs/agents/specialists/` sees red-team as an available reviewer but no Wave Council or Archetype Council peer. The names are also inconsistent: `red-team.md` is named after the surface; `council-moderator.md` is named after the moderator function (and which council?). The two councils ARE peers of red-team in the review-system mental model — they should look like peers in the filesystem.

This change unifies the three review surfaces as specialists, named after the council/role rather than the moderator function:

- `docs/agents/specialists/red-team.md` — already in place; no move
- `docs/agents/specialists/wave-council.md` — moved + renamed from `docs/agents/council-moderator.md`
- `docs/agents/specialists/archetype-council.md` — new role doc, parallel structure to `wave-council.md`, linking to seed-236 as the canonical protocol

The role-string identity `council-moderator` is renamed to `wave-council` throughout active surfaces (seeds, code, docs, tests) so the operator-visible name and the runtime seat-name match. Historical wave records are kept verbatim per the no-retrofit principle — they describe what happened under the `council-moderator` role-name at the time and remain accurate to that moment.

## Requirements

1. **Wave Council role doc relocates to specialists/ and renames to `wave-council`.** `docs/agents/council-moderator.md` moves to `docs/agents/specialists/wave-council.md`; frontmatter `Role:` changes from `council-moderator` to `wave-council`; doc title and self-references change accordingly.
2. **Archetype Council role doc created at `docs/agents/specialists/archetype-council.md`.** Mirrors the structure of `wave-council.md`. Identifies the operator-invoked protocol, the five canonical stance-based seats (Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman) plus the documented swap-ins (Hemingway, Munger), links to seed-236 as canonical protocol definition, and notes operator-invoked (not default-required) posture.
3. **Seed file renames.** `215-council-moderator.prompt.md` renames to `215-wave-council.prompt.md`. Internal `Role: council-moderator` frontmatter and content references update to `wave-council`. Seed file ordering numbers preserved.
4. **All active doc references rename from `council-moderator` to `wave-council`.** ~25 active references across `docs/agents/`, `docs/contributing/`, `docs/references/`, and `docs/prompts/` flip to the new role-name. Cross-doc links update where they refer to file paths.
5. **All code role-string references rename.** Every literal `"council-moderator"` (or `'council-moderator'`) in `server_impl.py`, `dashboard_lib.py`, and `wave_lint_lib/wave_validators.py` flips to `"wave-council"`. Seat selection in `_select_council_seats()` and review-evidence parsing produce the new role-name in JSON output.
6. **All test fixtures and assertions update accordingly.** Tests in `test_server_tools.py`, `test_docs_lint.py`, `test_build_pack.py`, and `test_dashboard_server.py` that match the literal role-string flip to the new name.
7. **`docs/workflow-config.json` references update.** If `council-moderator` appears in any `active_personas`, required-lane list, or other policy block, it flips to `wave-council`.
8. **Historical wave records under `docs/waves/<closed-wave-ids>/` are NOT modified.** The no-retrofit principle from `1p32k` Req-9 applies. Those records describe contemporaneous role names and remain factually accurate to their wave's runtime.
9. **The in-flight `1p337/wave.md` and `1p33b` change-doc council-verdict records are NOT rewritten.** Those verdicts were recorded under the `council-moderator` role-name and stand as recorded. New verdicts (this change's delivery council) use the new `wave-council` role-name forward.
10. **`docs/prompts/index.md` and `AGENTS.md` shortcut tables remain unchanged unless they explicitly name the role.** The shortcut phrases for Wave Council readiness and delivery do not embed the role-name; they invoke the protocol. Any shortcut entries that mention `council-moderator` flip to `wave-council`.
11. **No behavior change for any review pass.** Renaming is identity-only. The Wave Council protocol, fixed seats, rotating-seat policy, Phase 1 primer mechanics, and verdict shape remain bit-for-bit identical. Operator-facing council output uses the new role-name but the synthesis logic is unchanged.
12. **No new archetype-council protocol behavior.** This change adds the role *doc* for Archetype Council to make it discoverable; the protocol itself remains as specified in seed-236, operator-invoked, with no default-enable.

## Scope

**Problem statement:** Three review surfaces (red-team, Wave Council, Archetype Council) have inconsistent representation in `docs/agents/`: one is a specialist named after its role, one is a top-level "moderator" role doc, and one has no role doc at all. The taxonomy gap is a discoverability bug and a naming inconsistency. Operators browsing the agents directory cannot see all three review surfaces as peers; the runtime role-string (`council-moderator`) does not match the operator-facing concept (Wave Council).

**In scope:**

- File moves: `docs/agents/council-moderator.md` → `docs/agents/specialists/wave-council.md`; new file `docs/agents/specialists/archetype-council.md`
- Seed file rename: `215-council-moderator.prompt.md` → `215-wave-council.prompt.md`
- Role-string rename across all active surfaces (~25 docs, ~13 seeds, code, tests, workflow-config)
- Verification: full test suite + `wave_validate` + manual `wave_review` smoke check

**Out of scope:**

- Historical wave records under closed waves (no-retrofit principle)
- The in-flight 1p337/1p33b council-verdict records (recorded under prior role-name; stand as recorded)
- Renaming any council-protocol seed file beyond 215 (007-review-system-overview, 230-council-review, 236-archetype-council keep their filenames — they describe the protocol, not the agent role)
- Adding any new behavior to the Archetype Council protocol — seed-236 is unchanged; only the role doc is added
- Changing how shortcut phrases invoke the protocols — invocation surface is unchanged

## Acceptance Criteria

- [x] AC-1: `docs/agents/council-moderator.md` is removed; `docs/agents/specialists/wave-council.md` exists with the relocated content and `Role: wave-council` frontmatter.
- [x] AC-2: `docs/agents/specialists/archetype-council.md` is created with parallel structure to `wave-council.md`, naming the five canonical seats + documented swap-ins, linking to seed-236, and noting operator-invoked (not default-required) posture.
- [x] AC-3: `.wavefoundry/framework/seeds/215-council-moderator.prompt.md` is renamed to `215-wave-council.prompt.md`; internal `Role:` frontmatter and content references flip from `council-moderator` to `wave-council`.
- [x] AC-4: All occurrences of the literal string `council-moderator` in **active** docs under `docs/agents/`, `docs/contributing/`, `docs/references/`, `docs/prompts/` flip to `wave-council` (where the reference is to the role/agent — file-path references update to the new path).
- [x] AC-5: All occurrences of the literal `"council-moderator"` (and `'council-moderator'`) in `.wavefoundry/framework/scripts/server_impl.py`, `dashboard_lib.py`, `wave_lint_lib/wave_validators.py` flip to `"wave-council"` / `'wave-council'`.
- [x] AC-6: All occurrences in `.wavefoundry/framework/scripts/tests/test_server_tools.py`, `test_docs_lint.py`, `test_build_pack.py`, `test_dashboard_server.py` flip to the new role-name; tests pass.
- [x] AC-7: All occurrences in **active** framework seeds (001, 007, 010, 050, 100, 150, 160, 190, 211, 214, 225, 230, 236) flip from `council-moderator` to `wave-council`. Seed-215 is the renamed file from AC-3; all other seeds are content-only edits.
- [x] AC-8: `docs/workflow-config.json` references to `council-moderator` (if any) flip to `wave-council`.
- [x] AC-9: Historical wave records under closed waves are NOT modified. Verified by grep showing only the new role-name in `git diff` under active paths and the legacy role-name preserved under closed-wave paths.
- [x] AC-10: The in-flight `docs/waves/1p337 .../wave.md` and `docs/waves/1p337 .../1p33b ...md` council-verdict text is NOT rewritten. Verified by inspection of `git diff` for these two paths.
- [x] AC-11: `wave_review(phase='prepare')` and `wave_review(phase='delivery')` runs against a synthetic test fixture produce verdict JSON with `wave-council` as the moderator role-name (not `council-moderator`). Verified by test.
- [x] AC-12: Full framework test suite passes after all edits (regression discipline).
- [x] AC-13: `wave_validate` returns passed=true after all edits.
- [x] AC-14: `wave_audit` returns ready=true after all edits (modulo the pre-existing unassociated-commits and harness-coverage diagnostics that predate this wave).
- [x] AC-15: CHANGELOG 1.4.0 entry adds a bullet describing the review-surface unification.
- [x] AC-16: No reference to `council-moderator` remains in any active surface after the change (grep verification). Historical wave docs are the only surviving references.

## Tasks

- [x] Open `seed_edit_allowed` gate (covers seed-215 rename and content edits across active seeds)
- [x] Open `framework_edit_allowed` gate (covers all framework script and test edits)
- [x] Move `docs/agents/council-moderator.md` → `docs/agents/specialists/wave-council.md`; update title, `Role:` frontmatter, and self-references
- [x] Create `docs/agents/specialists/archetype-council.md` with the parallel structure
- [x] Rename `215-council-moderator.prompt.md` → `215-wave-council.prompt.md`; update internal role references
- [x] Flip all `council-moderator` → `wave-council` references in active docs (AC-4 scope)
- [x] Flip all `"council-moderator"` → `"wave-council"` in code (server_impl, dashboard_lib, wave_validators)
- [x] Flip all test-string occurrences (4 test files)
- [x] Flip all active-seed references (12 content-only edits + 1 renamed)
- [x] Flip `docs/workflow-config.json` references if any
- [x] Verify no `council-moderator` reference remains in active paths via grep
- [x] Verify historical wave records unchanged via `git diff --stat docs/waves/`
- [x] Run framework test suite; fix any miss
- [x] Run `wave_validate`
- [x] Run `wave_audit` and confirm ready=true
- [x] Close both gates
- [x] Update CHANGELOG with 1p33i bullet
- [x] Mark change `implemented`

## Affected Architecture Docs

`N/A` — this change is a taxonomy/naming refactor across documentation and identifier strings. No new boundaries, no new flows, no new components. The Wave Council protocol's place in the architecture is unchanged; only its role-name identifier and file location change. Architecture-reviewer is not required.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (council-moderator.md → specialists/wave-council.md) | required | Core file move; load-bearing for the taxonomy unification. |
| AC-2 (archetype-council.md created) | required | The new specialist parallel to wave-council; load-bearing for discoverability. |
| AC-3 (seed-215 rename + content) | required | Seed-level identity is what downstream installs see; must match the role doc. |
| AC-4 (active doc references flip) | required | Without this, the docs contradict the new role-name. |
| AC-5 (code role-string flip) | required | Runtime mismatch with operator-facing name if not done together. |
| AC-6 (test references flip) | required | Test suite fails on assertion mismatch otherwise. |
| AC-7 (active seed references flip) | required | Seed-level identity propagation across the entire seed surface. |
| AC-8 (workflow-config flip) | required | Active config surface must use the new role-name. |
| AC-9 (no historical wave records modified) | required | Hard scope bound per no-retrofit principle. |
| AC-10 (in-flight 1p337 verdicts unchanged) | required | Recorded verdicts under prior role-name stand as recorded — explicit decision per operator direction. |
| AC-11 (runtime verdict JSON shows new role-name) | required | End-to-end verification that the rename actually flows through to the operator-visible output. |
| AC-12 (test suite passes) | required | Regression discipline. |
| AC-13 (wave_validate passes) | required | Lint gate. |
| AC-14 (wave_audit ready=true) | required | Aggregate post-implementation gate. |
| AC-15 (CHANGELOG bullet) | required | Release-notes discoverability. |
| AC-16 (no council-moderator in active surfaces) | required | Hard verification gate; without this, the rename is partial and risks runtime mismatches. |

All ACs required; the rename has to be atomic across runtime + docs to avoid mismatch states.

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Move all three review surfaces (red-team, wave-council, archetype-council) under `docs/agents/specialists/` | Operator direction: "They should all be specialist agents." Resolves the taxonomy asymmetry — red-team was already a specialist; the two councils should be peers. | Keep council-moderator at top-level — rejected; perpetuates the asymmetry. |
| 2026-06-03 | Name files after the council/surface, not the moderator function (`wave-council.md`, not `wave-council-moderator.md`) | Matches `red-team.md` pattern (named after the role, not the function). Operator direction. | Use `wave-council-moderator.md` — rejected; emphasizes the moderator function over the council surface. |
| 2026-06-03 | Keep historical wave records unchanged | No-retrofit principle from `1p32k` Req-9. Records describe what happened at the time. | Rewrite history to use new role-name — rejected; loses audit-trail value. |
| 2026-06-03 | Keep the in-flight 1p337 council-verdict records under the prior `council-moderator` name | Those verdicts were issued under the prior role identity; rewriting would falsify the record. Forward verdicts (this change's delivery council) use the new name. | Rewrite the in-flight verdicts — rejected; verdict records are immutable signed events, not free-floating prose. |
| 2026-06-03 | Admit to `1p337` as the fourth change rather than create a new wave | Operator-directed admission. The three previous late-admits established a pattern of grouping the rename-transition + discoverability cleanup in one release. | Defer to 1.3.34 — rejected per operator. |
| 2026-06-03 | Rename only seed-215 (the moderator role seed); leave 230-council-review, 236-archetype-council, 007-review-system-overview filenames intact | Those seeds describe the *protocol*, not the *agent role*. The seed-225 (red-team) / seed-215 (wave-council) pattern: the role-named seed is what gets renamed; the protocol-named seeds stay. | Rename all council-related seeds — rejected; conflates protocol identity with role identity. |

## Risks

| Risk | Mitigation |
|---|---|
| Partial rename leaves runtime mismatch (e.g., role-string in code expects `council-moderator` but seed says `wave-council`) | AC-5 + AC-6 + AC-11: every literal in code and tests flips together; AC-11 end-to-end test verifies operator-visible output uses the new name. AC-16 grep-verifies no active-surface reference remains. |
| Test failures from string assertions on role-name | Tests flipped in AC-6 alongside the code flip; both land together. Full suite run before declaring done. |
| Cross-doc broken links (file moves change paths in linked references) | The role doc move from `docs/agents/council-moderator.md` to `docs/agents/specialists/wave-council.md` invalidates any explicit path link. Grep for both `council-moderator.md` and `docs/agents/council-moderator` to catch path-style references. |
| Operator confusion if old role-name appears in error messages or audit output after this change | AC-11 verifies new name flows through runtime. Anything not caught by tests goes into a small "verify manually" smoke list: `wave_review(phase='prepare')` + `wave_review(phase='delivery')` against a synthetic fixture. |
| Historical-record references to the old name in active docs (e.g., a contributing doc says "see council-moderator review on wave 12g27") create the illusion that those records should be rewritten | AC-9 is the hard rule; historical references in active docs that point at closed-wave records keep the old name because that's the name on the record. Distinguish "reference to the role" (renames) from "reference to a historical signature" (does not rename). Edits use the rule: if it points at the agent role going forward, rename; if it points at a recorded verdict from before this change, keep. |
| Existing operators reading the framework via search/MCP `docs_search` get hits on the old name for the council-moderator role | The index will refresh on next `wave_index_build`. Old-name hits in historical wave records remain — that's correct behavior; the new-name hits dominate active surfaces. |

## Related Work

- **`1p336` (back-compat fix)** — Established the pattern of reader-side back-compat for seed-prose renames; that pattern does not apply here because role-string identity is operator-facing and is the same on both sides of the rename.
- **`1p33b` (active-doc migration)** — Same no-retrofit boundary applies here.
- **`1p33f` (default-enable Wave Council)** — This change finishes the Wave Council surfacing work started in 1p33f: 1p33f made the surface available by default; this change makes the surface named consistently and discoverable as a specialist.
- **`1p32k` Req-9 (no-retrofit principle)** — Direct precedent for the historical-record preservation rule.
- **`1p31i` (Archetype Council)** — Created the protocol; this change creates the role doc that makes it discoverable in `docs/agents/specialists/`.
- **`12g27` (original Wave Council protocol)** — Closed wave where `council-moderator` was first established; remains under the old name per AC-9.

## Session Handoff

Admitted to `1p337` post-reopen as the fourth change. Sequenced last in the wave: depends on the active-doc surface from 1p33b being current, benefits from the default-enable from 1p33f to make the new role doc immediately reachable in every new install.
