# The seven lint-required `workflow-config.json` sections have no install owner since the 1p35d install split

Change ID: `1vim5-bug workflow-config-required-sections-have-no-install-owner`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-17
Wave: 1viyu fresh-install-gate-coherence

## Rationale

A fresh target-repo install (field report 2026-08-17) ended Phase 2 with 144 docs-lint errors; the single largest cluster was `docs/workflow-config.json: missing `<key>` section` for all seven `WORKFLOW_REQUIRED_KEYS` (`wave_implement`, `wave_review`, `agent_memory`, `project_persona_generation`, `prompt_generation`, `factor_review_policy`, `persona_review_policy`; `wave_lint_lib/constants.py` line 53), plus two knock-on review-policy obligation errors from a hand-authored `wave_review` block. The installing agent had to reverse-engineer the expected shape from `core_validators.py`, `review_policy.py`, and the framework README's "Suggested Workflow Config Anchors" aside.

The gap is a regression, not an omission that was always there. Before wave 1p35d (1.5.0) the seed-010 install body carried the requirement explicitly (at `11b3af4e^`, seed-010 line 142: "Workflow config must include top-level sections `wave_implement`, `wave_review` (default `enabled: true`) ... `factor_review_policy`, and `persona_review_policy`"). 1p35d split install into seeds 011/012 and that step was dropped: neither seed mentions `agent_memory` or `project_persona_generation`, and no script writes a default. What remains is worse than silence: `wf setup` Step 0 (`setup_wavefoundry._provision_lifecycle_policy_if_absent`, calling `upgrade_wavefoundry.materialize_lifecycle_policy`) creates `docs/workflow-config.json` holding only `lifecycle_id_policy`, so `check_workflow_config` (`core_validators.py` line 283) fails immediately on the first Phase 2 audit and stays failed until someone hand-authors seven sections. seed-040 line 64 still says the fields "will be added during the `010` workflow-config seeding step", a step that no longer exists; the README anchor list (`README.md` line 171) omits `wave_review`, which lint requires, and still describes `agent_memory` in journal terms.

Prose already lost this requirement once. The fix is a shipped default that code applies at the same Phase 1 step that already creates the file, so lint never sees a config it must fail.

## Requirements

1. **Ship the defaults as data.** Add `.wavefoundry/framework/install/workflow-config.defaults.json` carrying every `WORKFLOW_REQUIRED_KEYS` section with framework-default values (`prompt_generation.seed_framework_source` = `.wavefoundry/framework`; `factor_review_policy.applicable_factors` empty so seed-050's profile-seeding rule still runs; no project-specific keys; the canonical key spelling from `WORKFLOW_REQUIRED_KEYS`, never seed-160 line 516's `wf_implement_wave`, which is prose drift this change corrects to `wave_implement`). The `wave_review` section is not a second authority: its value must equal `review_policy.migrate_wave_review_policy(None)` (today `{"enabled": true, "delivery_mode": "targeted"}` via `FRESH_INSTALL_DELIVERY_MODE`), which is what every upgrade already provisions; a value-equality test pins the file to the function. Values are validated by the tests in Requirement 4, not by prose. The file is resolved root-then-module (target root's `.wavefoundry/framework/install/` first, then the directory packaged beside the module), the same rule `render_agent_surfaces.reconcile_lifecycle_prompt_baselines` uses, so scratch-root fixtures with an empty `.wavefoundry/framework/` still resolve.
2. **Apply the defaults at setup Step 0, key-wise and absent-only.** Extend the existing Step 0 provisioning in `setup_wavefoundry.py` so that, after `lifecycle_id_policy` is materialized, every top-level key present in the defaults file and absent from `docs/workflow-config.json` is added; existing keys are never modified or reordered, and a corrupt file still fails loudly with no write (same contract as `materialize_lifecycle_policy`). Print one `workflow config: provisioned N default section(s)` / `already complete` line so the operator log shows the outcome. Provide the same behavior behind `wf upgrade --materialize-lifecycle-policy`'s recovery path only if it falls out of sharing the helper; do not widen upgrade otherwise.
3. **Repoint the seeds and the log.** `seed-040` line 64 concerns `design_review_triggers` and `require_design_review_for_ui_surface_changes`, which are project-evidence keys and stay out of the defaults; the rewrite therefore says: the file exists after Phase 1 (setup Step 0 provisions `lifecycle_id_policy` and the seven required sections), so add these two design keys directly to `docs/workflow-config.json` in this task, and the retired "`010` workflow-config seeding step" sentence is removed; `seed-011` Step 0 and the install-log template row 1.2 name the default sections alongside `lifecycle_id_policy` in the verify text; the README "Suggested Workflow Config Anchors" list gains `wave_review` and loses journal wording (the `agent_memory` anchors at lines 190 to 197, including "journal root path" at line 192, describe typed memory records instead); `seed-160` line 516 spells the key `wave_implement` and lists `wave_review` among the sections the docs gate expects (it omits it today). `seed-012` gains no new step (the file is complete before Phase 2 begins), but its step for seed-100 (template row 2.9) states explicitly that `wf render-surfaces` must run after the prompt surface exists: an explicit `wave_review.delivery_mode` makes `check_review_policy_carriers` require the `wavefoundry:review-policy-upgrade` region in `docs/prompts/upgrade-wavefoundry.prompt.md` once that file exists, and `render_agent_surfaces` (`reconcile_upgrade_policy_surface`) is what writes it; before the file exists the carrier check skips it, so the fresh Phase 1 window is clean.
4. **Executable falsification.** Tests prove: (a) a scratch repo containing only `.wavefoundry/framework/` and an empty `docs/` after Step 0 has a `docs/workflow-config.json` that passes `check_workflow_config` and `normalize_wave_review_policy` with zero errors; (b) a pre-existing config with an operator-set `wave_review` and no `agent_memory` gains only `agent_memory` and the operator value is byte-identical after; (c) a corrupt JSON file produces the loud error and no write; (d) the defaults file's top-level keys are exactly a superset of `WORKFLOW_REQUIRED_KEYS` (the mutation that removes one key from the defaults must fail this test); (e) `build_pack` packages the defaults file (pack-content test); (f) `defaults["wave_review"] == migrate_wave_review_policy(None)` (value equality, so the file cannot drift from the fresh-install authority); (g) on the fresh scratch repo of test (a), after the Phase 1 render, `check_review_policy_carriers` reports zero errors (the upgrade prompt is absent, so the explicit `delivery_mode` imposes nothing yet), and once a `docs/prompts/upgrade-wavefoundry.prompt.md` is materialized and the render re-run, still zero (the region is upserted).

5. **Pin the framework README carrier.** A semantic-anchor test over `.wavefoundry/framework/README.md`'s Suggested Workflow Config Anchors requires `wave_review`, typed-memory wording, and absence of the retired `journal root path` phrase; restoring any one of the stale tokens fails the test. This is the executable owner for the README rewrite already required by Requirement 3.

## Scope

**Problem statement:** Lint requires seven `workflow-config.json` sections that nothing in the install writes, so every fresh install fails its own docs gate at the first Phase 2 audit and an agent hand-authors policy from validator source.

**In scope:**

- The shipped defaults file, the setup Step 0 provisioning, seed-011 / seed-040 / install-log template / README wording, tests.

**Out of scope:**

- Changing which keys `WORKFLOW_REQUIRED_KEYS` requires or their validation.
- Backfilling existing target repos through upgrade (an installed repo already passes lint, so it already carries the sections; seed-160 line 516 states the retention rule, and only its key spelling is corrected here).
- The two knock-on review-policy obligation errors from the field report beyond the note in Requirement 3: they arise when `wf render-surfaces` is not re-run after seed-100 creates the upgrade prompt; seed-100 steps 13/14 already require that render, and this change only makes seed-012's step say it.
- Project-specific keys (`enabled_agent_roles`, `indexing`, `dashboard`, drift entries): seeds 030/050/140 own them.
- The `wf_audit_install` gate behavior (change `1vitr`).

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/framework/install/workflow-config.defaults.json` ships in the pack, its top-level keys cover every entry of `WORKFLOW_REQUIRED_KEYS` (asserted from the constant, not a hand-written list), and its `wave_review` value equals `migrate_wave_review_policy(None)` (test f).
- [x] AC-2: `wf setup` Step 0 on a fresh repo yields a `docs/workflow-config.json` that passes `check_workflow_config` and `normalize_wave_review_policy` with zero errors, full docs-lint on that repo reports no `docs/workflow-config.json` errors, and `check_review_policy_carriers` reports zero errors before and after the upgrade prompt exists with the render re-run (test g).
- [x] AC-3: Provisioning is key-wise and absent-only: an operator-set section is byte-identical after Step 0, and a corrupt file fails loudly with no write (tests b and c).
- [x] AC-4: seed-040 line 64, seed-011 Step 0, install-log template row 1.2, and README anchors (lines 171 to 197) name the setup provisioning and no longer reference the retired `010` step or journals; seed-160 line 516 spells `wave_implement`; seed-012's seed-100 step names the post-surface `wf render-surfaces` run; docs-lint clean; framework suite green.
- [x] AC-5: A mutation-sensitive semantic-anchor test pins `wave_review`, typed-memory wording, and removal of `journal root path` in the framework README anchors.

## Tasks

- [x] Author `install/workflow-config.defaults.json`: keys and shapes from the docs-lint fixture `tests/fixtures/docs_lint/base/docs/workflow-config.json` and the self-hosted sections, values framework-generic only. Explicitly exclude the self-hosted values that are project policy or retired vocabulary: `agent_memory.sensitivity` ("...in_journals" wording), `project_persona_generation.evidence_sources` (project paths), `persona_review_policy.active_personas`, `factor_review_policy.partial_factors` / `not_applicable_factors` (project assessments), and any `wave_review` key beyond `migrate_wave_review_policy(None)`; `agent_memory` describes typed memory records, not journals.
- [x] `setup_wavefoundry.py`: `_provision_workflow_defaults_if_absent(root)` (per-file root-then-module defaults resolution: check the target root's file, then the file packaged beside the module, not the directory, so a scratch fixture with an `install/` dir but no defaults file still resolves; key-wise absent-only merge, corrupt-file refusal, one summary line), invoked from Step 0 after lifecycle provisioning; share the read-parse-refuse helper with `materialize_lifecycle_policy` if that is a pure extraction.
- [x] `build_pack.py`: confirm the `install/` directory scan packages the new file (add to the pack-content test).
- [x] Seeds under `seed_edit_allowed`: seed-040 line 64 (design keys added directly; retired-step sentence removed); seed-011 Step 0 + row 1.2 wording; seed-012 seed-100 step (render after surface); seed-160 line 516 key spelling + `wave_review`; `install/install-log.template.md` row 1.2; `README.md` anchors 171 to 197. Note-only, project doc: `docs/agents/personas/wave-coordinator.md` line 56 carries the same `wf_implement_wave` key drift; fix in passing if touched, otherwise leave for the docs sweep.
- [x] Tests (a) through (g) in `test_setup_wavefoundry.py` / `test_build_pack.py` / `test_review_policy.py`; run the full suite; `wf_validate_docs`.
- [x] Framework README contract test: assert the three Requirement 5 anchors and demonstrate failure when each is reverted independently.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| defaults   | implementer | none       | Goal: shipped defaults file + coverage test (d) + pack test (e) |
| provision  | implementer | defaults   | Goal: Step 0 merge helper + tests (a)(b)(c) |
| prose      | implementer | defaults   | Goal: seed-040/011/012/160 lines, template row 1.2, README anchors repointed |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/install/install-log.template.md`
- `.wavefoundry/framework/seeds/011-install-wavefoundry-phase-1.prompt.md`
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md`
- `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/README.md`
- `.wavefoundry/framework/scripts/tests/test_setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`

**Framework maintenance note.** Seed edits (011, 012, 040, 160) require `seed_edit_allowed`; seed-012 and seed-160 are shared with `1vitr`/`1viyt` and `1vitq` respectively (line-level ownership recorded in the wave Watchpoints); script edits require `framework_edit_allowed`. Protected surfaces not touched: `WORKFLOW_REQUIRED_KEYS`, `check_workflow_config`, `materialize_lifecycle_policy` semantics, upgrade Phase 2c.

## Affected Architecture Docs

`N/A` for `docs/architecture/*`: no module boundary or data path changes; the install flow's own contract docs (`docs/prompts/install-wavefoundry.prompt.md` renders from seed-010/011 and is refreshed by the surface render) are covered by the prose workstream.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Data shipped in the pack is what makes the fix survive future seed rewrites; the constant-driven test is what stops the next silent key drift. |
| AC-2 | required  | The reported failure mode, executed on a fresh scratch repo. |
| AC-3 | required  | Absent-only merge is the safety property for every existing repo that re-runs setup. |
| AC-4 | important | Prose coherence; lint-checked, but not the mechanism. |
| AC-5 | important | The public framework README carrier is easy to drift and cheap to hold with the existing semantic-reference test style. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-17 | Delivery review editorial repair (REL-DEL-2 / CODE-DEL-4, release + code lanes): `_provision_workflow_defaults_if_absent` now writes through `upgrade_wavefoundry._atomic_write_json` (same-directory temp + `os.replace`, `ensure_ascii=False`) and reports a write-time OSError as an `ERROR:` line, so a merge no longer rewrites non-ASCII operator values as `\\uXXXX` escapes and is crash-safe; the no-write path (config already complete) was already byte-identical. Note-only findings kept as-is: no test pins `_workflow_defaults_path` target-first resolution (probe-verified); README line 192 handled. | `setup_wavefoundry._provision_workflow_defaults_if_absent`; `test_setup_wavefoundry.LifecyclePolicyStepZeroTests` re-run at reverification |
| 2026-08-17 | Thought: every required public carrier needs an executable owner. Observe: `RT-FINAL-006` found the framework README rewrite was scope-owned but not test-owned; Requirement 5/AC-5 now pin its required anchors with focused mutations. | Typed readiness finding/repair; framework README Suggested Workflow Config Anchors |
| 2026-08-17 | Readiness amendment from the docs-contract seat (DC-6, DC-7, DC-8, DC-9): seed-040 line 64 rewrite stated precisely (design keys are added directly, not by Step 0); seed-160 line 516 also gains `wave_review`; the self-hosted values that must NOT be copied into the defaults are named; per-file (not directory) root-then-module resolution. | seed-040 line 64 quoted; `docs/workflow-config.json` (this repo) values; `reconcile_lifecycle_prompt_baselines` directory-level fallback at `template_root.is_dir()` |
| 2026-08-17 | Readiness amendment from the red-team primer (RT-3, RT-10, RT-11, RT-12, RT-14): root-then-module defaults resolution; `wave_review` value pinned to `migrate_wave_review_policy(None)` (test f); the explicit-`delivery_mode` carrier consequence stated with the render as the remedy and test (g); seed-160 line 516 spelling; README line 192 taken over from 1viyt. | `review_policy.migrate_wave_review_policy` / `FRESH_INSTALL_DELIVERY_MODE`; `check_review_policy_carriers` upgrade-carrier branch (skips when the prompt is absent); `render_agent_surfaces` calls `reconcile_upgrade_policy_surface` |
| 2026-08-17 | Planned from the 2026-08-17 fresh-install field report. Verified: no seed 030 to 140 mentions `agent_memory` / `project_persona_generation` (`code_keyword` over `.wavefoundry/framework/**`); no script writes a default (`code_pattern` for `"prompt_generation"` / `"factor_review_policy"` outside tests); setup Step 0 provisions only `lifecycle_id_policy` (`setup_wavefoundry.py` line 136); the pre-1p35d seed-010 body required the sections (`git show 11b3af4e^:.../010-*.md` line 142); seed-040 line 64 dangling `010` reference; README anchors line 171 omit `wave_review`. | `wave_lint_lib/constants.py` 53, `core_validators.py` 283, `setup_wavefoundry.py` 136, `README.md` 171, `seeds/040` 64, git `11b3af4e` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-17 | Ship the seven sections as a data file and apply them from setup Step 0, key-wise absent-only; `wave_review` pinned by test to `migrate_wave_review_policy(None)`. | Runs before lint ever reads the file, is idempotent for existing repos, cannot be lost by a seed rewrite the way the seed-010 prose was, and (readiness amendment, red-team RT-10/RT-11) keeps one authority for the fresh `wave_review` value while the file stays inspectable. | Restore the requirement as seed-012 prose (rejected: prose is what got lost in 1p35d, and agents still reverse-engineer shapes from validators); relax `check_workflow_config` until the prompt surface exists (rejected: hides the gap, and `wave_review` is read live by the server, `server_impl.py` 2699); write the defaults from `materialize_lifecycle_policy` itself (rejected: couples the ID-policy contract, which must never be re-provisioned, to a merge that may legitimately re-run). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A default value (for example `wave_review.delivery_mode`) changes behavior for repos that re-run setup and lacked the key. | Absent-only merge, plus the setup summary line names every provisioned section; a repo that passed lint already carries all seven keys, so the merge is a no-op there (test b). |
| Explicit `delivery_mode` makes the upgrade-prompt carrier region mandatory at row 2.9 (the field report's two obligation errors). | Before the prompt exists the carrier check skips it; `wf render-surfaces` upserts the region (`reconcile_upgrade_policy_surface`), seed-100 already requires that render, and seed-012's step now says it; test (g) proves both states. `1vitr` classifies this message as blocking (not an absence), which is correct: the fix is to run the render. |
| Defaults drift from `WORKFLOW_REQUIRED_KEYS` on a future key addition. | Test (d) is derived from the constant, so adding a key without a default fails the suite. |
| Provisioning runs against a non-root cwd. | Reuse the existing `.wavefoundry/framework/` anchor guard from Step 0. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
