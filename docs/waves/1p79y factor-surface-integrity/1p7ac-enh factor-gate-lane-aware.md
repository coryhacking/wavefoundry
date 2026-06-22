# Factor gate keys off the operational lane set (factor_review_policy.applicable_factors)

Change ID: `1p7ac-enh factor-gate-lane-aware`
Change Status: `implemented`
Owner: Engineering
Status: planned
Wave: `1p79y factor-surface-integrity`
Last verified: 2026-06-22

## Rationale

`1p79x`'s `check_factor_surface` gate keys the canonical-doc requirement off `docs/repo-profile.json` `factor_review` *status* (each `applicable` factor → canonical doc required). Three independent observations show that is the **wrong source surface**:

- **solaris (Swift consumer):** the operator-approved-retired the factor-review lane (emptied `workflow-config.json` `factor_review_policy.applicable_factors`, deleted the agent files) but kept truthful `applicable` assessments in `repo-profile.json`. The gate false-blocked the upgrade, forcing the operator to either regenerate unwanted docs (contradicting the retirement) or falsify applicability (relabel `applicable`→`partial`).
- **RDS/CDK consumer:** `repo-profile.json` marks **10** factors applicable, but `workflow-config.json` activates only **7** lanes. The gate forced generating **10** canonical docs (3 more than active lanes); expanding the lane set to 10 is an operator policy decision the agent correctly declined — leaving a 7-vs-10 drift.
- **wavefoundry itself:** `repo-profile.json` marks `07` (Port binding) `applicable`, but `workflow-config.json` `factor_review_policy.applicable_factors` is `["03","05","12","13"]` (07 is in `partial_factors`). `1p79x` therefore over-required `docs/agents/factor-07-port-binding.md`.

**Root cause:** the canonical factor docs are the review-**lane** artifacts. The requirement must key off the **operational active-lane set** — `workflow-config.json` `factor_review_policy.applicable_factors` — not the broader `repo-profile.json` applicability **assessment**. The operational set already expresses lane-retirement (empty) and partial/assessment-only factors (not listed). `repo-profile` answers "is this factor relevant?"; `workflow-config` answers "do we run a lane for it?" — and only the latter implies a canonical doc.

## Requirements

1. **Re-key the gate to the operational lane set.** In `wave_lint_lib/wave_validators.py` `check_factor_surface`, require the canonical `docs/agents/factor-<nn>-<name>.md` (with `Role: factor-<nn>-<name>` + `Category: factor`) for each factor listed in `docs/workflow-config.json` `factor_review_policy.applicable_factors` — NOT for each `applicable` factor in `repo-profile.json`. An absent/empty `applicable_factors` (retired lane) requires **no** canonical docs. Factors that are partial / assessment-only (not in `applicable_factors`) require no canonical doc.
2. **Preserve wrapper checks.** Keep the orphan-wrapper (a `.claude/agents/factor-*.md` with no matching canonical) and missing-frontmatter checks on any wrappers that exist, regardless of the lane set.
3. **Drift WARNING (non-blocking).** When `repo-profile.json` `factor_review` marks a factor `applicable` but it is NOT in `workflow-config.json` `applicable_factors`, emit a docs-lint **WARNING** (not an ERROR): the factor is assessed-relevant but has no active review lane. This surfaces the assessment-vs-operational gap (the solaris 6-factor and RDS 10-vs-7 drift, and wavefoundry's own 07) for operator reconciliation, **without** forcing doc over-generation or blocking the gate. Preserves the feedback's "no silent drift" intent.
4. **Reconcile wavefoundry's own drift (self-host).** `repo-profile.json` `07` = `applicable` vs `workflow-config.json` `07` = partial. Make the two surfaces agree on factor-07's true status (port binding is a real active concern via the dashboard server). Either promote 07 to an active lane (add to `applicable_factors`, keep `factor-07-port-binding.md` + add its wrapper if lanes render wrappers here) or align `repo-profile` to `partial` (factor-07 doc becomes optional documentation). Keep `docs/agents/factor-07-port-binding.md` consistent with the chosen status; the self-host must be docs-lint clean with no false ERROR and no residual drift WARNING.
5. **Seeds.** `seed-050` / `seed-160` describe the gate keying off `factor_review_policy.applicable_factors`, the retired-lane case (empty set → no docs required), and the assessment(`repo-profile`)-vs-operational(`workflow-config`) relationship; `seed-238` treats a retired or narrower lane set as a legitimate operator choice (not drift to "retire/relocate"); reconcile any `1p79x` seed text that implied `repo-profile` `factor_review` drives the gate.
6. **Tests.** lane-active (factor in `applicable_factors`, no canonical) → ERROR; retired (empty/absent `applicable_factors`) with `repo-profile` factors still `applicable` → PASS (solaris case); assessment-only (factor `applicable` in `repo-profile` but not in `applicable_factors`) → WARNING, not ERROR (RDS 10-vs-7 case); self-host (`applicable_factors` `03/05/12/13` with their docs) → PASS; orphan-wrapper + missing-frontmatter still enforced. Bytecode-free.
7. **Hygiene.** Edits under `framework_edit_allowed` (validator/tests) + `seed_edit_allowed` (seeds); the factor-07 reconciliation is `docs/`/config. No external-project names introduced. **No VERSION bump** (lands in the held 1.8.0 before release).

## Scope

**Problem statement:** The `1p79x` factor gate requires canonical docs based on the `repo-profile.json` applicability *assessment* rather than the `workflow-config.json` operational *active-lane set*, so it false-blocks retired-lane repos (solaris) and over-requires docs where the assessment exceeds the active lanes (RDS 10-vs-7, wavefoundry's own 07).

**In scope:** re-key `check_factor_surface` to `factor_review_policy.applicable_factors`; the non-blocking assessment-vs-lane drift WARNING; wavefoundry's own 07 reconciliation; the dependent test + seed updates.

**Out of scope:** changing any consumer's policy (which factors get lanes is the operator's call — this only fixes which surface the gate reads); the design-system surface; expanding wavefoundry's own lane set beyond an honest 07 reconciliation.

**Depends on:** `1p79x` (this refines the gate it added). Same wave (`1p79y`), pre-release.

## Acceptance Criteria

- [x] AC-1: `check_factor_surface` keys the canonical-doc requirement off `workflow-config.json` `factor_review_policy.applicable_factors` (operational lane set), not `repo-profile.json` `factor_review` status.
- [x] AC-2: a retired lane (empty/absent `applicable_factors`) requires no canonical docs even when `repo-profile` marks factors `applicable` — solaris-shaped input passes without falsifying `repo-profile`. (Test: `test_factor_surface_retired_lane_repo_profile_applicable_passes`.)
- [x] AC-3: lane-active behavior preserved — a factor in `applicable_factors` with no canonical doc → ERROR (the Java-consumer path still fires). (Test: `test_factor_surface_lane_active_missing_canonical_fails`.)
- [x] AC-4: an assessment-only factor (`applicable` in `repo-profile`, not in `applicable_factors`) → docs-lint **WARNING**, not ERROR — RDS 10-vs-7-shaped input is visible but unblocked. (Test: `test_factor_surface_assessment_only_factor_warns_not_errors` asserts returncode 0 + WARNING.)
- [x] AC-5: orphan-wrapper + missing-frontmatter checks still apply to any existing `.claude/agents/factor-*.md` wrappers regardless of the lane set. (Tests: `test_factor_surface_orphan_wrapper_fails_regardless_of_lane_set` (empty lane set), `test_factor_surface_wrapper_missing_frontmatter_fails`.)
- [x] AC-6: wavefoundry's own `07` `repo-profile`/`workflow-config` drift reconciled — `repo-profile` `07` aligned to `partial` (matches operational config; `07` is in `partial_factors`), `docs/agents/factor-07-port-binding.md` removed (over-generated by `1p79x`'s wrong keying), and its `platform-mapping.md` row removed; self-host docs-lint clean (exit 0, no ERROR, no residual drift WARNING). Active lanes now exactly `03/05/12/13` with their canonical docs.
- [x] AC-7: `seed-050`/`seed-160`/`seed-238` describe the lane-set keying, retired-lane case, and assessment-vs-operational relationship; no seed text still implies `repo-profile` drives the gate.
- [x] AC-8: tests cover lane-active→ERROR, retired→PASS, assessment-only→WARNING, self-host→PASS, orphan/frontmatter still enforced; bytecode-free; docs-lint clean. Full suite 3394 green (was 3388).
- [x] AC-9: gated edits (`framework_edit_allowed` validator/cli/tests, `seed_edit_allowed` seeds, all closed); no external-project names introduced (`aceiss|teton|solaris` grep = 0 over changed files); no VERSION bump.

## Tasks

- [x] Open gates per scope (`framework_edit_allowed` validator/tests; `seed_edit_allowed` seeds); close after each.
- [x] Re-key `check_factor_surface` to `factor_review_policy.applicable_factors`; add the assessment-vs-lane drift WARNING.
- [x] Update tests for lane-active/retired/assessment-only/self-host + preserved orphan/frontmatter cases.
- [x] Reconcile wavefoundry's `07` across `repo-profile.json` + `workflow-config.json`; keep/remove `factor-07-port-binding.md` consistently; confirm self-host docs-lint clean. (Aligned `repo-profile` 07 → `partial`; removed the factor-07 canonical doc + platform-mapping row.)
- [x] Update `seed-050`/`seed-160`/`seed-238` for the lane-set keying + retired case + assessment-vs-operational relationship.
- [x] Run framework tests bytecode-free; docs-lint clean; grep external-names = 0; close gates.

## Agent Execution Graph


| Workstream      | Owner       | Depends On  | Notes                                                              |
| --------------- | ----------- | ----------- | ----------------------------------------------------------------- |
| validator-rekey | implementer | —           | key off `applicable_factors`; add non-blocking drift WARNING      |
| tests           | implementer | validator-rekey | lane-active/retired/assessment-only/self-host + orphan/frontmatter |
| self-host-07    | implementer | validator-rekey | reconcile 07 across repo-profile + workflow-config; factor-07 doc |
| seed-updates    | implementer | validator-rekey | seed-050/160/238 lane-set keying + retired + relationship         |
| review          | reviewer    | all above   | framework-code + docs-contract lanes; re-run delivery council     |


## Serialization Points

- The re-keyed validator is the contract the seeds + tests describe — land it first.
- This refines `1p79x` (same wave); the `wave-council-delivery` signoff covering `1p79x` must be re-run to also cover `1p7ac` before close.

## Affected Architecture Docs

- **N/A** — confined to the validator + seeds + config reconciliation; no module-boundary/data-flow change. (If `docs/architecture/` documents the factor-gate contract, add a one-line note; confirm at Prepare.)

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Keying off the operational lane set is the fix; corrects the wrong-surface root cause. |
| AC-2 | required  | Retired-lane repos (solaris) must stop being false-blocked without falsifying assessments. |
| AC-3 | required  | The genuine "active lane missing its canonical" finding (Java consumer) must still fire. |
| AC-4 | required  | The assessment-vs-lane drift (RDS 10-vs-7) must be visible but non-blocking — no forced over-generation. |
| AC-5 | required  | Orphan/malformed wrappers remain real defects regardless of lane set. |
| AC-6 | required  | Self-host must be clean + internally consistent (the 07 drift this surfaced in our own config). |
| AC-7 | important | Seeds are the downstream contract; they must describe the corrected keying. |
| AC-8 | required  | Behavior change must be test-locked across all four cases, bytecode-free. |
| AC-9 | required  | Gated framework edits; vendor-neutrality and no-release-yet preserved. |


## Progress Log


| Date       | Update                                                                 | Evidence                          |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| 2026-06-22 | Plan created from two independent `1.8.0+p7a6` downstream reports (solaris retired-lane false-block; RDS 10-vs-7 forced over-generation) plus wavefoundry's own `07` drift. Root cause: `1p79x` keyed the gate off `repo-profile.json` `factor_review` (assessment) instead of `workflow-config.json` `factor_review_policy.applicable_factors` (operational lanes). Fix folded into the held 1.8.0 before release. | solaris + RDS field reports; `wave_validators.py check_factor_surface`; wavefoundry `workflow-config.json` `applicable_factors` `["03","05","12","13"]` vs `repo-profile` `07` applicable |
| 2026-06-22 | Implemented. **Re-keyed `check_factor_surface`** to require the canonical `docs/agents/factor-<nn>-<name>.md` (with `Role:`/`Category: factor`) for each factor in `docs/workflow-config.json` `factor_review_policy.applicable_factors` (read the actual policy shape: `applicable_factors`/`partial_factors`/`not_applicable_factors`), NOT for each `applicable` factor in `repo-profile.json`; absent/empty `applicable_factors` requires no canonical docs. **Non-blocking WARNING mechanism:** changed `check_factor_surface` to return `(failures, warnings)` (the same tuple contract `check_prepare_council_verdict`/`check_design_*` already use); the assessment-vs-lane drift signal (a `repo-profile` `applicable` factor not in `applicable_factors`) is appended to `warnings`, and `cli.py` routes it via `warnings.extend(...)` — warnings print as `WARNING:` and do NOT flip the returncode (only `failures` flip it to 1). **Preserved:** the lane-active ERROR (factor in `applicable_factors` with no/malformed canonical), the orphan-wrapper ERROR, and the missing-frontmatter ERROR (both wrapper checks run regardless of the lane set). **Self-host 07 reconciliation:** aligned `repo-profile.json` `factor_review["07"]` `applicable`→`partial` (matches operational config — `07` is in `partial_factors`, the dashboard port-binding is an optional local surface), removed `docs/agents/factor-07-port-binding.md` (over-generated by `1p79x`'s wrong keying, no longer gate-required), and removed its `docs/agents/platform-mapping.md` row — wavefoundry's factor surface now exactly matches its active lanes `03/05/12/13` and docs-lint is clean with **no residual drift WARNING**. **Tests:** replaced the `1p79x` repo-profile-keyed cases with lane-active→ERROR, retired-lane(+repo-profile applicable)→PASS, assessment-only→WARNING-not-ERROR (asserts returncode 0), self-host `03/05/12/13`→PASS (no drift warning), orphan-wrapper-under-empty-lane→ERROR, missing-frontmatter→ERROR; added `_set_applicable_factors` fixture helper. **Seeds:** `seed-050` task 5, `seed-160` (backfill + audit checklist + diff-summary lines), `seed-238` (governed-pair section) re-keyed to `applicable_factors`, the retired/narrower-lane-is-legitimate case, and the assessment-vs-operational relationship; removed `1p79x` text implying `repo-profile` drives the gate. Full suite **3394** green bytecode-free (was 3388, +6); self-host `docs-lint: ok` (exit 0, zero warnings/errors); `aceiss\|teton\|solaris` grep over changed files = 0; no VERSION bump; gates opened/closed per scope, all closed. | `wave_validators.py` `check_factor_surface`, `cli.py`, `tests/test_docs_lint.py`, `seeds/050`, `seeds/160`, `seeds/238`, `docs/repo-profile.json`, removed `docs/agents/factor-07-port-binding.md` + its `platform-mapping.md` row |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-22 | **Divergent pre-plan — selected: re-key the gate to `workflow-config.json factor_review_policy.applicable_factors`** | The canonical docs ARE the review-lane artifacts, so the requirement must follow the operational active-lane set, which already encodes retirement (empty) and partial (not listed). Fixes solaris, RDS, and wavefoundry's own 07 in one move with no new config surface. | (B) Add an explicit `factor_review_policy.retired` flag while keeping `repo-profile` keying — rejected: doesn't fix the partial / 10-vs-7 over-require, and adds redundant config. (C) Keep `repo-profile` keying + tell operators to downgrade applicability — rejected: forces falsifying the assessment, the exact failure two consumers hit. |
| 2026-06-22 | Surface assessment-vs-lane drift as a non-blocking WARNING (not ERROR) | The feedback wanted drift visible, not silent — but an applicable factor without an active lane is a policy gap for the operator to reconcile, not a build-blocking defect. | Hard ERROR on any assessment-vs-lane drift — rejected: re-creates the over-block (RDS would still be forced to expand lanes or downgrade). Silent (no signal) — rejected: loses visibility. |
| 2026-06-22 | `repo-profile` = applicability assessment; `workflow-config.applicable_factors` = operational lane set; canonical docs follow the lane set | Establishes the single source of truth for the gate and the meaning of each surface, so future drift is interpreted consistently. | Treat the two as interchangeable (status quo) — the source of the bug. |


## Risks


| Risk                                                                 | Mitigation                                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Re-keying hides a genuinely-drifted repo whose `applicable_factors` is stale/empty but should have lanes | The non-blocking drift WARNING surfaces every `repo-profile`-applicable factor that lacks an active lane, so the gap stays visible for operator reconciliation. |
| wavefoundry's own `07` reconciliation direction is a judgment call | Decide by actual applicability (the dashboard genuinely binds ports); make `repo-profile` + `workflow-config` agree and the self-host clean either way. |
| The 3 consumers already generated docs under the old gate (Java 7, RDS 10, solaris relabel) | Harmless under the re-key: the gate now requires docs only for `applicable_factors` (a subset of what they generated); extra docs stay valid and the drift WARNING guides reconciliation. No retroactive breakage. |
| `factor_review_policy` shape varies / `applicable_factors` absent | Treat absent/empty as "no active lanes" (no canonical required); the WARNING still flags `repo-profile`-applicable factors so absence isn't silently permissive. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
