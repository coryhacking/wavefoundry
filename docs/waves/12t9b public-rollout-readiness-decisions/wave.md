# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-23

wave-id: `12t9b public-rollout-readiness-decisions`
Title: Public Rollout Readiness Decisions

## Objective

Define the rollout contract for three foundation areas that currently remain implicit or inconsistent: release versioning, platform support, and Python runtime/dependency management. The outcome of this wave is a set of implementation-ready changes that let Wavefoundry tighten its public operator contract before wider adoption.

## Changes

Change ID: `12t9a-change migrate-release-versioning-to-semver`
Change Status: `implemented`

Change ID: `12t9a-change define-cross-platform-support-policy`
Change Status: `implemented`

Change ID: `12t9a-change standardize-python-tool-environment`
Change Status: `implemented`

Change ID: `12t9f-change enforce-checkbox-task-scaffolds-for-change-docs`
Change Status: `implemented`

## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| planner | plan | all admitted changes |
| wave-coordinator | coordinate | full wave lifecycle routing and readiness gate |
| qa-reviewer | review | all admitted changes — AC coverage, checklist fidelity, migration clarity |
| release-reviewer | review | `12t9a`, `12t9f` — versioning contract, packaging/update compatibility, scaffold contract changes |
| architecture-reviewer | review | `12t9a`, `12t9a-change standardize-python-tool-environment` — release/runtime boundary changes and rollout contract coherence |
| docs-contract-reviewer | review | `12t9a-change define-cross-platform-support-policy`, `12t9f` — operator-facing prompt/docs contract and planning scaffold contract |
| council-moderator | council | full admitted set — Wave Council readiness synthesis |
| reality-checker | council | full admitted set — challenge rollout assumptions and enforcement gaps |
| security-reviewer | council | full admitted set — environment/bootstrap and platform-policy trust-boundary challenge |

Completed At: 2026-05-22

## Wave Summary

Wave `12t9b` (Public Rollout Readiness Decisions) established the rollout contract for four foundation areas and delivered the low-risk Track A implementation directly. The higher-blast-radius Track B runtime work was intentionally split into the follow-on implementation wave `12tms python-env-and-semver-implementation`, which carried the semver and Python-environment code changes to completion.

**Changes delivered:**

- **Migrate Release Versioning To Semver** (`12t9a-change migrate-release-versioning-to-semver`) — rollout contract decided in `12t9b`; implementation completed intentionally in follow-on wave `12tms python-env-and-semver-implementation`.
- **Define Cross-Platform Support Policy** (`12t9a-change define-cross-platform-support-policy`) — 4 ACs completed directly in `12t9b`; macOS/Linux native and Windows-via-WSL2 operator policy published in local docs/prompts.
- **Standardize Python Tool Environment** (`12t9a-change standardize-python-tool-environment`) — rollout contract decided in `12t9b`; implementation completed intentionally in follow-on wave `12tms python-env-and-semver-implementation`.
- **Enforce Checkbox Task Scaffolds For Change Docs** (`12t9f-change enforce-checkbox-task-scaffolds-for-change-docs`) — 5 ACs completed directly in `12t9b`; local scaffold, prompt, lint, and tests aligned to checkbox-task syntax.
## Journal Watchpoints

- **Watchpoint:** The active wave `12sq2 enterprise-role-seeds-and-lint` remains separate; keep this wave `planned` until that work is reviewed and wave capacity is available.
- **Watchpoint:** The semver and Python-environment changes both affect upgrade and operator documentation; review those surfaces together before implementation starts.
- **Watchpoint:** Resolve the Windows support policy before promising native Windows compatibility in install, upgrade, or registration surfaces.
- **Watchpoint:** Task-checkbox enforcement touches both the Wavefoundry local planning template and the framework contract; avoid fixing only one layer and leaving self-hosting drift behind.

## Review Evidence

- wave-council-readiness: approved 2026-05-22 — Four planning changes admitted: semver migration, platform support policy, Python tool-environment strategy, and checkbox-task scaffold enforcement. Scope is coherent: all four establish outward-facing rollout contracts before implementation. Required reviewer lanes: qa-reviewer for all changes; release-reviewer for versioning and scaffold-contract changes; architecture-reviewer for version/runtime contract changes; docs-contract-reviewer for platform-policy and scaffold-contract language. Product-owner: N/A — framework/operator process changes, not product feature delivery. Wave is ready for implementation planning and subsequent execution when capacity allows.
- red-team-readiness: mode=`council-seat` strongest_challenge=`The current wave bundles four outward-facing contract changes that all converge on install/upgrade/operator experience; implementing them as one undifferentiated pass risks partial consistency where docs, templates, runtime bootstrap, and upgrade behavior diverge mid-wave.` best_alternative=`Sequence the wave as two explicit implementation tracks: Track A establishes contracts and low-risk enforcement (`12t9f` checkbox-task contract, `12t9a-change define-cross-platform-support-policy` support stance), then Track B applies higher-blast-radius runtime/release mechanics (`12t9a-change standardize-python-tool-environment`, `12t9a-change migrate-release-versioning-to-semver`) after the operator contract is stable.` consequence_of_current_path=`A single broad execution pass can produce a misleadingly 'mostly updated' release where one surface promises behavior another surface cannot yet honor.` recommendation=`Keep the wave intact, but implement in staged tracks with an explicit checkpoint between contract-definition changes and runtime/release changes.` evidence_basis=`All four admitted changes directly touch public operator contracts, and three of them explicitly name upgrade/docs/bootstrap surfaces as in scope. The wave watchpoints already note shared upgrade/doc surfaces and self-hosting drift risk.` confidence=`high`
- wave-council-delivery: approved 2026-05-22 — `12t9b` delivered its contracted scope as a decision-and-contract wave: Track A shipped code directly (checkbox enforcement, platform policy), while Track B intentionally concluded with binding decisions that were carried into follow-on implementation wave `12tms python-env-and-semver-implementation`. Council flag: `packaging` library must be an explicit implementation dependency in the follow-on wave (not an afterthought), and architecture docs must reflect the decided contracts before this wave closes. Starting version `1.0.0` vs `0.1.0` should be operator-confirmed before the semver implementation wave opens.
- operator-signoff: approved 2026-05-22

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-22: PASS** (red-team fixed seat; docs-contract-reviewer rotating seat)
  - The admitted scope is coherent: all four changes tighten external rollout contracts before implementation.
  - Red-team challenge: avoid partial fixes that correct Wavefoundry-local drift while leaving framework defaults or enforcement inconsistent downstream.
  - Docs-contract-reviewer challenge: operator-facing prompts, templates, and upgrade surfaces must reflect one canonical contract for versioning, platform support, Python environment setup, and task checkbox semantics.
  - No blocking contradictions found between the admitted changes; proceed with the wave as the planning/execution container for these rollout-readiness decisions.
- **Red-team readiness review — 2026-05-22: advisory alternatives recorded**
  - Evidence: all four admitted changes alter outward-facing rollout contracts, and three explicitly include docs, upgrade, bootstrap, or scaffold surfaces that operators experience together.
  - Inference: the main delivery risk is not that any single change is wrong, but that the implementation order allows one contract surface to move ahead of the others.
  - Best alternative implementation idea: execute in two tracks. Track A: `12t9f` checkbox-task scaffold enforcement plus `12t9a-change define-cross-platform-support-policy` to stabilize prompt/template/operator language first. Track B: `12t9a-change standardize-python-tool-environment` plus `12t9a-change migrate-release-versioning-to-semver`, with a checkpoint after Track A to confirm the operator contract before touching runtime/bootstrap and release ordering.
  - Secondary alternative: split semver migration into a compatibility-first phase (version parser + manifest semantics + mixed-version upgrade handling) and a packaging-surface phase (artifact naming + docs + release workflow) if the release-path blast radius proves larger than expected during implementation.
  - Recommendation: keep the current wave, but implement with explicit stage boundaries rather than parallelizing all four changes.
- **Wave Council delivery [wave-council-delivery] — 2026-05-22: PASS**
  - Track A shipped code with test coverage; Track B intentionally stopped at binding planning decisions with full audit evidence.
  - Reality-checker flag: `packaging` library (required for semver version comparison) is not yet a declared dependency — the implementation wave must add it to `pyproject.toml` in the same pass as updating `check_version.py`.
  - Red-team second pass: semver starting version (`1.0.0` vs `0.1.0`) should be operator-confirmed before the implementation wave opens; planning decisions should be reflected in architecture docs now.
  - Council bounds: decisions hold through first public release; revisit Python environment decision if `WAVEFOUNDRY_TOOL_VENV` proves incompatible with WSL2 constraints before `1.0.0` ships.
  - Historical note: the subsequent implementation landed in follow-on wave `12tms python-env-and-semver-implementation`; this closure record remains correct because `12t9b` was intentionally used to lock the contract and stage the later runtime work.
- **Prepare wave — readiness verdict [prepare-readiness] — 2026-05-22: PASS**
  - All four admitted change docs are wave-owned under `docs/waves/12t9b public-rollout-readiness-decisions/`.
  - Required sections are present on all change docs; task checklists now use checkbox syntax consistently across this wave.
  - AC priority has been recorded on each admitted change.
  - Wave Council readiness signoff recorded in `## Review Evidence`.
  - Product-owner acknowledgment is not required for this wave because the admitted work defines framework/operator contracts rather than shipping end-user product behavior.

## Dependencies

- No external wave dependencies.

## Serialization Points

- **Track A must complete before Track B starts.** Track A stabilizes operator-facing contract surfaces: `12t9f-change enforce-checkbox-task-scaffolds-for-change-docs` and `12t9a-change define-cross-platform-support-policy`.
- **Checkpoint after Track A:** confirm prompt/template/operator language is internally consistent before touching runtime bootstrap, dependency installation, release version semantics, or upgrade ordering.
- **Track B is serialized after the checkpoint.** Track B carries the higher-blast-radius mechanics: `12t9a-change standardize-python-tool-environment` and `12t9a-change migrate-release-versioning-to-semver`.
- **Semver fallback split:** if versioning blast radius proves larger than expected, execute `12t9a-change migrate-release-versioning-to-semver` in two internal phases: compatibility/parser/manifest handling first, packaging/artifact naming/docs second.

## Execution Plan

1. Implement Track A:
   - `12t9f-change enforce-checkbox-task-scaffolds-for-change-docs`
   - `12t9a-change define-cross-platform-support-policy`
2. Run a coordinator checkpoint:
   - verify operator-facing prompts, templates, and upgrade/install wording agree
   - verify the task-checkbox contract is consistent between local Wavefoundry surfaces and framework defaults
   - confirm no new language promises native Windows behavior beyond the chosen support stance
3. Implement Track B:
   - `12t9a-change standardize-python-tool-environment`
   - `12t9a-change migrate-release-versioning-to-semver`
4. If Track B uncovers larger-than-expected semver migration risk, split semver execution into:
   - parser/manifest/mixed-version compatibility
   - packaging/artifact naming/docs/release workflow

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-22 | Adopted red-team recommendation to stage implementation in two tracks with a coordinator checkpoint between contract-surface work and runtime/release mechanics. | `red-team-readiness` review evidence and `Red-team readiness review` checkpoint in this wave record. |
| 2026-05-22 | Completed Track A and reached the coordinator checkpoint. Checkbox-task syntax is now enforced for wave-owned change docs, and the public platform policy now states macOS/Linux native support with Windows via WSL2. | `docs/plans/plan-template.md`, `docs/prompts/plan-feature.prompt.md`, `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, `.wavefoundry/framework/scripts/tests/test_docs_lint.py`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `README.md`, `docs/prompts/install-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/architecture/current-state.md`; verification: `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_docs_lint.py'`, `python3 .wavefoundry/framework/scripts/docs_lint.py`. |
| 2026-05-22 | Completed the Track B coordinator checkpoint as an intentional handoff boundary. Semver and Python environment decisions were finalized here, then implemented in follow-on wave `12tms python-env-and-semver-implementation` rather than directly inside `12t9b`. | `12t9a-change migrate-release-versioning-to-semver.md`, `12t9a-change standardize-python-tool-environment.md`, and follow-on wave `docs/waves/12tms python-env-and-semver-implementation/`. |
| 2026-05-23 | Clarified the historical record after follow-on implementation landed: `12t9b` closed intentionally as a contract-setting wave with direct Track A delivery and delegated Track B execution. | `docs/waves/12t9b public-rollout-readiness-decisions/wave.md`, `docs/waves/12tms python-env-and-semver-implementation/`. |
