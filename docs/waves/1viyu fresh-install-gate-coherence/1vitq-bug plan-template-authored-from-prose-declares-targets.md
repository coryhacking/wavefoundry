# The install authors `docs/plans/plan-template.md` from seed-040 prose, so every fresh install ships a scaffold that declares review targets

Change ID: `1vitq-bug plan-template-authored-from-prose-declares-targets`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-17
Wave: 1viyu fresh-install-gate-coherence

## Rationale

The 2026-08-17 fresh-install field report lists `docs/plans/plan-template.md` failing docs-lint "out of the box" because its example review-target paths are not fenced. The reporter attributes it to framework-shipped content; that is inaccurate in a way that matters for the fix. No `plan-template.md` ships in the pack. seed-040 task 11 (`040-docs-structure-bootstrap.prompt.md` line 30) tells the installing agent to **author** the template, and its Serialization Points bullet (line 39) hands the agent the declaration example inline: `` - `src/app/handler.py`, `docs/specs/` ``. Nothing in seed-040 says an example written into a scaffold must be fenced. seed-160 (upgrade) does say it, at line 199 ("Any example you write into the template must not itself declare a target: put it inside a fenced block") with a verify step at line 482; the install seed never received the same rule. So the agent transcribes the example as a live bullet, `check_scaffold_declares_nothing` (`core_validators.py` line 29) fires exactly as its docstring predicts ("Prose is not a gate"), and the operator reads a framework false positive.

The framework already holds a correct template. `server_impl._default_template()` (the fallback `new_change` uses when `docs/plans/plan-template.md` is absent) carries the same section set with the examples fenced, and this repository's own `docs/plans/plan-template.md` passes the check. The defect is that the install path is the one place that authors from prose instead of copying a known-good artifact, the same "copy verbatim, do not author a thin version" pattern seed-012 already uses for `install-log-format.md` and `scan-findings-format.md`.

## Requirements

1. **One shipped template.** Move the plan template out of `_default_template()` into `.wavefoundry/framework/install/plan-template.md` (packaged like the other `install/` templates); `_default_template()` reads that file so `new_change`'s fallback and the materialized copy are the same bytes. Resolution is root-then-module per FILE (target root's `.wavefoundry/framework/install/plan-template.md` first, then the file packaged beside the module), the same idea as `render_agent_surfaces.reconcile_lifecycle_prompt_baselines` but at file granularity, because that helper falls back only when the whole `install/lifecycle-prompts/` directory is absent and a scratch fixture with an `install/` dir but no `plan-template.md` would otherwise raise; scratch-root test fixtures whose `.wavefoundry/framework/` is empty still resolve; a genuinely missing file raises a clear error. `_default_template()` is called with no arguments today (`new_change`, and the tests `test_falls_back_to_default_template` and the `_default_template()` call in `test_server_tools.py`), so it gains an optional `root=None` parameter (module-only resolution when `None`) and `new_change` passes `root`; the existing call sites keep working. Keep the current `_default_template()` section set and fenced examples; align headings with seed-040 task 11's list (including `## Agent Execution Graph`, which the in-code fallback lacks and the self-hosted template has). The shipped file's `Last verified:` is a `{{generated_at}}`-style placeholder that every writer stamps with today's date (`new_change` already rewrites `Last verified:`; the materializer in Requirement 2 stamps on write), because `check_metadata` requires a `YYYY-MM-DD` value on every `docs/**/*.md`.
2. **Code materializes, seeds verify.** `docs/plans/plan-template.md` joins the missing-only baseline set that `render_agent_surfaces` materializes at setup and on every upgrade (a sibling of `LIFECYCLE_PROMPT_BASELINES` for scaffolds, per-file root-then-module template resolution, same never-overwrite rule, `Last verified:` stamped on write, and the destination enumerated in `preflight_agent_surface_paths` so the containment preflight covers it). `docs/references/install-assets.md` gains rows for the two new `install/` assets (`plan-template.md`, and `1vim5`'s `workflow-config.defaults.json`, recorded there by whichever change lands second). Fresh installs therefore carry the template after Phase 1, before seed-040 runs. seed-040 task 11 becomes: verify `docs/plans/plan-template.md` is present (Phase 1 materialized it); if absent, copy the shipped file verbatim and stamp the date; never author it from the section list, which stays as the contract the file must satisfy; tailor only project-specific wording. Add the fence rule from seed-160 line 199 as the backstop for any later hand edit, and a one-line "verify it declares nothing" instruction (the docs gate enforces it).
3. **Upgrade backfill, absent-only, by the same code.** The materializer in Requirement 2 already runs on upgrade, so seed-160's plan-template guidance (line 199) is reworded to say the render materializes a missing template and the agent's job is the merge-safe repair of an existing one; seed-160 line 198, which today instructs editing `_default_template()`'s inline string, is updated to name the shipped file; seed-160 lines 371 to 374 and 479 to 482 and seed-100 step 14 ("six lifecycle baselines from `install/lifecycle-prompts/`") are re-read for coherence with the new scaffold baseline and adjusted only where they would contradict it. No overwrite of an existing template.
4. **Executable falsification.** Tests prove: (a) the shipped template passes `check_scaffold_declares_nothing` (`serialization_point_paths` returns no targets) and contains every section heading seed-040 task 11 names (a mutation that unfences one example, or drops a heading, must fail); (b) `new_change` in a scratch repo with no `docs/plans/plan-template.md` and an empty `.wavefoundry/framework/` scaffolds a doc whose bytes derive from the shipped file via module resolution (the previous inline string is gone), and the existing `test_falls_back_to_default_template` still passes; (c) the pack-content test lists `install/plan-template.md`; (d) full docs-lint on a scratch repo whose only `docs/plans/` content is the materialized template reports no `plan-template.md` errors (including `check_metadata`, so the date stamp is exercised); (e) the render materializes `docs/plans/plan-template.md` when absent and leaves an existing file byte-identical (mirror of the lifecycle-baseline tests in `test_render_agent_surfaces.py`).

## Scope

**Problem statement:** The install seed makes the agent author the change-doc scaffold from an inline example with no fence rule, so every fresh install produces a template that the docs gate correctly rejects; the framework already ships a passing template in code but not as a copyable file.

**In scope:**

- The shipped `install/plan-template.md`, `_default_template()` reading it, the scaffold-baseline materialization in `render_agent_surfaces.py`, seed-040 task 11 and seed-160 lines 198/199 wording, pack test, tests.

**Out of scope:**

- Changing `check_scaffold_declares_nothing` or `serialization_point_paths` (both correct).
- Rewriting this repository's own `docs/plans/plan-template.md` beyond any drift the shared template exposes (it already passes; a diff is recorded, not applied blindly).
- The plan-template's content contract itself (section semantics stay as seed-040 and seed-170 define them).

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/framework/install/plan-template.md` ships in the pack, passes `check_scaffold_declares_nothing`, and contains every section seed-040 task 11 names; the test derives the heading list from a single constant shared with nothing hand-copied in the test body.
- [x] AC-2: `_default_template()` returns the shipped file's content with root-then-module resolution; `new_change` in a repo without a project template scaffolds from it (test b); the inline template string no longer exists in `server_impl.py`.
- [x] AC-3: `render_agent_surfaces` materializes `docs/plans/plan-template.md` missing-only with the date stamped (test e); seed-040 task 11 says verify-present / copy-verbatim-when-absent plus the fence rule and verify line; seed-160 lines 198/199 name the shipped file and the render; docs-lint clean; suite green.
- [x] AC-4: A scratch repo whose `docs/plans/` holds only the materialized template passes full docs-lint with no `plan-template.md` finding, `check_metadata` included (test d).

## Tasks

- [x] Extract `_default_template()`'s string to `install/plan-template.md`; add `## Agent Execution Graph` and reconcile headings against seed-040 task 11 and the self-hosted template; `Last verified:` becomes a stamped placeholder; make `_default_template()` read the file with root-then-module resolution.
- [x] `render_agent_surfaces.py`: scaffold-baseline materialization (`docs/plans/plan-template.md` from `install/plan-template.md`, missing-only, date stamped) alongside `reconcile_lifecycle_prompt_baselines`; test (e).
- [x] `build_pack.py` pack-content test: assert `install/plan-template.md` is packaged.
- [x] Seeds under `seed_edit_allowed`: seed-040 task 11 (verify-present, copy-verbatim-when-absent, fence rule, verify line); seed-160 lines 198/199 (shipped file + render materializes).
- [x] Tests (a) through (d) in `test_docs_lint.py` / `test_server_tools.py` / `test_build_pack.py`; full suite; `wf_validate_docs`.
- [x] Diff the shipped template against this repository's `docs/plans/plan-template.md`; record any intentional divergence in the wave record.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| template   | implementer | none       | Goal: shipped file + `_default_template()` reads it (root-then-module) + tests (a)(b)(c) |
| render     | implementer | template   | Goal: missing-only materialization at setup/upgrade with date stamp + test (e) |
| seeds      | implementer | template   | Goal: seed-040 task 11 and seed-160 line 199 repointed |
| prove      | implementer | template   | Goal: scratch-repo lint (d), suite, template diff recorded |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `docs/references/install-assets.md`

**Framework maintenance note.** Seed edits (040, 160) require `seed_edit_allowed`; script edits require `framework_edit_allowed`. Read-only lanes: `wave_lint_lib/core_validators.py`, `review_policy.py` (`SCAFFOLD_DOCS`, `serialization_point_paths`) are consumed, not edited.

## Affected Architecture Docs

`N/A`: no boundary, flow, or verification-seam change; the plan-template contract remains where seed-040/seed-170 define it.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The shipped, tested artifact is the fix; the mutation-sensitive test keeps it fixed. |
| AC-2 | required  | One source of truth; two templates would drift the way the in-code fallback already has (missing AEG). |
| AC-3 | required  | Without the seed change the install keeps authoring from prose and the shipped file is never used. |
| AC-4 | important | End-to-end proof on the reported failure mode; the unit tests already cover the mechanism. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-17 | Delivery review (release + docs-contract lanes APPROVE-with-editorial; code/qa lanes' CODE-DEL-1 repair touched the sibling lifecycle materializer): `reconcile_lifecycle_prompt_baselines` now stamps `{{generated_at}}` exactly as `reconcile_scaffold_baselines` does, so both baseline families materialize lint-clean; the shipped lifecycle baselines carry the metadata block. Recorded here because this change owns the scaffold-baseline pattern the repair extended; ownership of the lifecycle templates themselves is recorded in `1vitr`. | `render_agent_surfaces.reconcile_lifecycle_prompt_baselines`; `test_render_agent_surfaces` (76 OK pre-repair; re-run at reverification) |
| 2026-08-17 | Readiness amendment from the docs-contract seat (DC-9, DC-10, DC-13): per-file resolution (the lifecycle helper's fallback is directory-level); `_default_template(root=None)` signature stated with its existing call sites; `preflight_agent_surface_paths` enumeration; `install-assets.md` rows; seed-160 lines 371 to 374 / 479 to 482 and seed-100 step 14 named for coherence. | `render_agent_surfaces.py` `template_root.is_dir()` fallback; `preflight_agent_surface_paths`; `test_falls_back_to_default_template` |
| 2026-08-17 | Readiness amendment from the red-team primer (RT-3, RT-4, RT-5, RT-6): adopted code materialization via the lifecycle-baseline pattern, root-then-module resolution for the shipped file, date stamping for `check_metadata`, seed-160 line 198 added to scope, test (e) added. | `render_agent_surfaces.reconcile_lifecycle_prompt_baselines`; `test_falls_back_to_default_template`; `check_metadata` / `METADATA_PATTERNS` |
| 2026-08-17 | Planned from the 2026-08-17 fresh-install field report. Verified: no `plan-template.md` under `.wavefoundry/framework/` (`code_list_files`); seed-040 task 11 line 30 says "Seed", line 39 gives the inline example, zero "fence" mentions in seed-040 vs seed-160 lines 199/482; `check_scaffold_declares_nothing` docstring predicts this exact failure; `_default_template()` in `server_impl.py` (fallback of `new_change`, line 8585) is fenced but lacks `## Agent Execution Graph`; the reporter's example path `apps/backend/qa-api/app/main.py` appears nowhere in the framework (agent-authored). | `seeds/040` 30/39, `seeds/160` 199/482, `core_validators.py` 29, `server_impl.py` 8585 and `_default_template` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-17 | Ship the template as a file, make `_default_template()` read it (root-then-module), and have `render_agent_surfaces` materialize `docs/plans/plan-template.md` missing-only at setup and upgrade, with seed-040 reduced to verify/copy-when-absent plus the fence rule as backstop. | Readiness amendment (red-team primer RT-3, RT-4, RT-5): the pack already materializes missing-only baselines by code (`reconcile_lifecycle_prompt_baselines`), and agent-copy prose is the failure class 1vim5 diagnoses; one artifact serves the MCP fallback, setup, upgrade, and the seed; the validator stays untouched. Cost accepted: `docs/plans/` exists after Phase 1, before seed-040 builds `docs/`, so the shipped file must lint on its own (date stamped on write). | Copy-verbatim by seed prose only, no code materializer (rejected at readiness: an install step an agent can skip; the lifecycle baselines already show the code path is cheap and proven); add the fence rule to seed-040 only (rejected as sole fix: the validator docstring records that identical prose in seed-160 was received, followed, and still shipped a declaring template); have `new_change` ignore the project template and always use the in-code string (rejected: operators refine their template, and the install would still author a failing file); loosen `check_scaffold_declares_nothing` for fresh installs (rejected: every plan created from a declaring scaffold silently loses lanes, which is the harm the check exists to prevent). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The shipped template diverges from this repository's refined `docs/plans/plan-template.md` and the wrong one becomes canonical. | Record the diff at implement; the shipped file is the fresh-install baseline, the self-hosted file stays operator-refined; both must pass the same test. |
| `_default_template()` file read fails at runtime (moved pack, missing file, scratch root with an empty `.wavefoundry/framework/`). | Root-then-module resolution (the packaged file sits beside the module); the pack-content test guarantees presence; test (b) runs against an empty scratch framework dir; a missing file raises a clear error rather than silently scaffolding an empty doc. |
| A materialized template with a placeholder date fails `check_metadata`. | Every writer stamps `Last verified:`; test (d) runs full lint on the materialized file. |
| Upgrade overwrites an operator template. | Requirement 3 is create-when-absent only; test the present-file path leaves bytes unchanged. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
