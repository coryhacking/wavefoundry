# Default-Enable Wave Council In Project Skeleton

Change ID: `1p33f-enh default-enable-wave-council-in-project-skeleton`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-03
Wave: `1p337 config-key-back-compat-hotfix` (admitted as the third change — operator-directed admission alongside the back-compat fix and docs migration, packaged for 1.4.0)

## Rationale

The framework's project skeleton currently treats `wave_review` (formerly `wave_council_policy`) as opt-in: install seed prose mentions it under "when the framework-standard council model is enabled" framing, and the docs-lint base fixture omits it entirely. A new project that installs Wavefoundry gets a working install with **no Wave Council surface at all** unless the operator hand-adds the block — even though every other reviewer lane (`red-team`, `architecture-reviewer`, `qa-reviewer`, `security-reviewer`) is code-level always-available.

Red-team is the precedent: it is hard-wired as the Phase 1 council primer seat in `_select_council_seats()` and is always-on whenever council runs. Wave Council itself should ship the same way at the framework default — **available by default, not enforced.** The distinction is load-bearing: `enabled: true` makes the surface present and operator-discoverable; `required_for_all_waves: true` is the enforcement knob the operator opts into when they decide council should gate every wave.

This change ships the default `wave_review: { enabled: true }` block in the project skeleton so new installs and upgrades pick it up automatically. Each project's operator keeps full control over `required_for_all_waves`, which remains opt-in.

## Requirements

1. **Project skeleton emits `wave_review` block at install/upgrade.** The install seed names `wave_review` as a required top-level workflow-config section (alongside `wave_implement`, `agent_memory`, etc.). New projects pick up `wave_review: { enabled: true }` automatically; existing projects pick it up on upgrade.
2. **Default block enables the surface but does not enforce.** The skeleton emits `enabled: true` only (or with `required_for_all_waves: false` explicit if needed for schema clarity). Operators who want enforcement set `required_for_all_waves: true` themselves.
3. **docs-lint required-keys validator names `wave_review` as required.** The `WORKFLOW_REQUIRED_KEYS` alias-tuple gains a `("wave_review", "wave_council_policy")` entry — so projects that already migrated keys pass, projects still on legacy keys pass, and projects with neither key fail with a discoverable error.
4. **Active operator-facing docs reflect "default-on, opt-in enforcement"** rather than the current "when enabled" framing. Update the highest-traffic prose: `010-install-wavefoundry.prompt.md`, `docs/contributing/feature-wave-lifecycle-overview.md`, `docs/contributing/review-and-evals.md`, `docs/references/project-overview.md`. Sites that already reference `wave_review.enabled` as a truthy gate don't need wording changes — the gate semantics are unchanged.
5. **Self-host `docs/workflow-config.json` keeps `required_for_all_waves: true`.** This repo's own posture (enforcement on) is intentional and unrelated to the new default. The change is about what *other projects* get by default, not what this project does.
6. **No runtime/behavior change for projects that already have a `wave_review` block.** The reader logic shipped in `1p336` is the runtime contract; this change is skeleton + validator only. A project with an existing `wave_review.enabled: true` block sees no behavior change.
7. **Tests cover the new validator behavior.** Add cases proving: (a) project with `wave_review` block passes required-keys check; (b) project with legacy `wave_council_policy` block passes; (c) project with neither key fails with an error naming both acceptable keys.

## Scope

**Problem statement:** The framework's project skeleton ships without the Wave Council surface enabled, requiring operators to hand-add the config block. New installs silently lack the council surface — discoverability is poor and the framework's own default contradicts its recommended posture.

**In scope:**

- `010-install-wavefoundry.prompt.md` — add `wave_review` to the required-top-level-sections list; soften "when enabled" framing to "default-on, enforcement opt-in"
- `.wavefoundry/framework/scripts/tests/fixtures/docs_lint/base/docs/workflow-config.json` — add `wave_review: { enabled: true }` block
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py` `WORKFLOW_REQUIRED_KEYS` — add `("wave_review", "wave_council_policy")` alias-tuple entry
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py` — add coverage for the three new validator scenarios
- `docs/contributing/feature-wave-lifecycle-overview.md`, `docs/contributing/review-and-evals.md`, `docs/references/project-overview.md` — soften prose where it implies opt-in
- `CHANGELOG.md` — combined 1.4.0 entry covers this change

**Out of scope:**

- Forcing `required_for_all_waves: true` by default. The operator was explicit: enabling, not enforcing.
- Archetype Council enablement. Stays operator-invoked per `1p31i` design.
- Runtime reader changes — `1p336` carries the back-compat behavior and is unchanged.
- Migration of any seed prose other than the install seed. Other seeds reference `wave_review` correctly already.
- Historical wave records. No-retrofit principle applies.

## Acceptance Criteria

- [x] AC-1: `WORKFLOW_REQUIRED_KEYS` in `wave_lint_lib/constants.py` gains a `("wave_review", "wave_council_policy")` alias-tuple entry positioned after the `("wave_implement", "wave_execution")` entry.
- [x] AC-2: `docs_lint/base/docs/workflow-config.json` fixture gains a top-level `wave_review: { "enabled": true }` block — exactly that shape, no `required_for_all_waves` key.
- [x] AC-3: `test_docs_lint.py` adds a test verifying a workflow-config with `wave_review` block passes the required-keys validator (the existing fixture exercise covers this; explicit assertion makes the contract observable).
- [x] AC-4: `test_docs_lint.py` adds a test verifying a workflow-config with legacy `wave_council_policy` block (and no `wave_review`) passes the required-keys validator — proves alias-tuple back-compat for the new key.
- [x] AC-5: `test_docs_lint.py` adds a test verifying a workflow-config missing both `wave_review` and `wave_council_policy` fails with an error naming both acceptable keys.
- [x] AC-6: `010-install-wavefoundry.prompt.md` line 142 (required-sections list) adds `wave_review` to the named top-level sections.
- [x] AC-7: `010-install-wavefoundry.prompt.md` line 363 (verification check) adds `wave_review` to the verified top-level sections.
- [x] AC-8: `010-install-wavefoundry.prompt.md` line 181 (output description) softens the conditional "when the framework-standard council model is enabled" framing to default-on/opt-in-enforcement framing.
- [x] AC-9: `010-install-wavefoundry.prompt.md` line 246 (output description for the optional Wave Council policy block) is updated to reflect default-on shape — emit `enabled: true` as default; `required_for_all_waves` and other knobs remain operator-set.
- [x] AC-10: `docs/contributing/feature-wave-lifecycle-overview.md` Wave Council prose softens "When `wave_review.enabled` is true" to reflect default-on framing (e.g., "Wave Council ships enabled by default; `required_for_all_waves: true` is the operator opt-in for enforcement").
- [x] AC-11: `docs/contributing/review-and-evals.md` Wave Council prose softens the conditional framing similarly.
- [x] AC-12: `docs/references/project-overview.md` Wave Council prose softens the conditional framing similarly.
- [x] AC-13: Full framework test suite passes (regression discipline).
- [x] AC-14: Self-host `docs/workflow-config.json` is **not** modified — its `required_for_all_waves: true` setting stays as-is.
- [x] AC-15: CHANGELOG 1.4.0 entry adds a bullet describing the new framework default.
- [x] AC-16: `wave_audit` returns `ready=true` after all edits land.

## Tasks

- [x] Open `seed_edit_allowed` gate (covers `010-install-wavefoundry.prompt.md` edit)
- [x] Open `framework_edit_allowed` gate (covers `wave_lint_lib/constants.py`, fixture, test, and docs edits)
- [x] Add `("wave_review", "wave_council_policy")` entry to `WORKFLOW_REQUIRED_KEYS`
- [x] Add `wave_review: { "enabled": true }` block to the docs-lint base fixture
- [x] Add the three new validator-coverage tests to `test_docs_lint.py`
- [x] Edit `010-install-wavefoundry.prompt.md` lines 142, 181, 246, 363 per AC-6/7/8/9
- [x] Edit `docs/contributing/feature-wave-lifecycle-overview.md`, `docs/contributing/review-and-evals.md`, `docs/references/project-overview.md` per AC-10/11/12
- [x] Run framework test suite — verify no regressions
- [x] Run `wave_audit` — verify ready=true post-edits
- [x] Close both gates
- [x] Update CHANGELOG 1.4.0 entry
- [x] Mark change `implemented`

## Affected Architecture Docs

`N/A` — this change ships a framework default in the install skeleton plus a docs-lint validator entry. No architectural boundary, data flow, or testing-architecture impact. The runtime contract was established in `1p336`; this change only changes what new projects get by default.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (`WORKFLOW_REQUIRED_KEYS` alias-tuple entry) | required | Core enforcement of the new default; without it, the validator doesn't see the new key. |
| AC-2 (fixture has `wave_review` block) | required | Validator test coverage relies on the fixture; the fixture is also the canonical example. |
| AC-3 (test: `wave_review` passes) | required | Regression coverage for the new-key path. |
| AC-4 (test: legacy `wave_council_policy` passes) | required | Back-compat regression coverage; alias-tuple behavior must hold for the new entry. |
| AC-5 (test: missing both fails) | required | Negative-path coverage; verifies the error message names both acceptable keys per AC-1 contract. |
| AC-6 (install seed line 142) | required | Install-time skeleton emission; this is the load-bearing line for the new default. |
| AC-7 (install seed line 363) | required | Install verification check; without this, the install passes silently when the new key is missing. |
| AC-8 (install seed line 181) | required | Operator-facing output description must reflect the new default. |
| AC-9 (install seed line 246) | required | Operator-facing output description for the council block; must reflect default-on shape. |
| AC-10 (`feature-wave-lifecycle-overview.md` prose) | required | High-traffic operator surface; prose should not contradict the new default. |
| AC-11 (`review-and-evals.md` prose) | required | High-traffic operator surface; same rationale. |
| AC-12 (`project-overview.md` prose) | required | High-traffic operator surface; same rationale. |
| AC-13 (framework test suite passes) | required | Regression discipline. |
| AC-14 (self-host config unchanged) | required | Hard scope bound — this change is about new-project default, not changing this repo's posture. |
| AC-15 (CHANGELOG entry) | required | Release notes discoverability. |
| AC-16 (`wave_audit` ready=true) | required | Standard post-implementation verification gate. |

All ACs are required; the scope is bounded and every surface is load-bearing for the new default.

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Default `enabled: true` only — do not set `required_for_all_waves: true` in the skeleton | Operator was explicit: "we're not enforcing a review. Just enabling." Mirrors the red-team precedent: surface available by default, enforcement opt-in. | (a) Default both `enabled: true` and `required_for_all_waves: true` — rejected; would force council on every wave for every new project. (b) Leave skeleton without the block — rejected; reverts the change. |
| 2026-06-03 | Admit to `1p337` rather than create a new wave for 1.3.34 | Operator directed admission ("admit"). Bundling means consumers upgrading to 1.4.0 get coherent new-default behavior with the back-compat fix and docs migration in one release. | (a) New wave shipping as 1.3.34 — rejected per operator; (b) Defer indefinitely — rejected; the framework default is the load-bearing fix for discoverability. |
| 2026-06-03 | Use the alias-tuple data structure (shipped in `1p336`) to express the new required-keys entry | Composes with the existing pattern — no validator logic change, just one more entry. | Special-case the rename in validator code — rejected; defeats the alias-tuple generalization shipped in `1p336`. |
| 2026-06-03 | Do not modify the self-host `docs/workflow-config.json` | This repo's `required_for_all_waves: true` is an intentional posture and unrelated to the new default. Changing it would be scope-creep and would also remove a useful enforcement signal during framework development. | Set this repo to default-shape too — rejected; conflates new-project default with framework self-host posture. |

## Risks

| Risk | Mitigation |
|---|---|
| Validator entry changes break an existing project's config check (e.g., a project has the block but with an unexpected shape) | The validator only checks for key presence, not block shape. Existing projects with either `wave_review` or `wave_council_policy` block pass; only projects with neither fail. Tests AC-3/AC-4/AC-5 cover all three paths. |
| Install seed prose drift if the four edit sites (lines 142, 181, 246, 363) end up phrasing the new default inconsistently | Edit each site with explicit reference to the same "default-on, enforcement opt-in" phrasing. Review the seed diff before commit. |
| Existing projects on legacy `wave_council_policy` who upgrade and see no behavior change might wonder if the upgrade actually shipped anything | The 1p336 deprecation note (legacy-key read → stderr) is the discoverability signal for the rename. The new default applies only to new installs and upgrades that regenerate the skeleton; legacy-key projects stay on legacy until they regenerate. |
| New-project install discovers that `required_for_all_waves` is absent and defaults to false runtime-side, when the operator expected enforcement | The runtime contract is unchanged: `_read_wave_council_policy()` returns the block as-is and consumers gate on `policy.get('required_for_all_waves', False)`. Operators who want enforcement set the flag explicitly. This is the same behavior as today. |
| The skeleton emits `wave_review` but a downstream agent reads the legacy `wave_council_policy` key without back-compat | All readers added in `1p336` honor the new key with legacy fallback; readers added in this change use the new key only. No new legacy-key-direct readers introduced. |

## Related Work

- **`1p336` (back-compat fix)** — shipped the runtime reader's new-key precedence with legacy fallback. This change builds on that contract by making the new key the framework default.
- **`1p33b` (active-doc migration)** — migrated active operational docs to the new canonical names. This change continues the migration by making the new key the **install-time** default.
- **`1p2q3` (original seed-prose rename)** — initiated the `wave_council_policy` → `wave_review` rename. This change is the final step of that transition: the framework's own default now uses the new name.
- **`1p31i` (Archetype Council seed)** — the operator-invoked Archetype Council is intentionally NOT default-enabled; this change is explicitly about Wave Council only.

## Session Handoff

Admitted to `1p337` post-reopen alongside `1p336` (back-compat) and `1p33b` (active-doc migration). Sequenced last in the wave: requires the alias-tuple data structure from `1p336` and benefits from the active-doc migration in `1p33b`.
