# The upgrade dry run does not show which retired models the real run will delete

Spec ID: `24e91-bug retired-model-cleanup-dry-run-shows-nothing`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-26
Wave: 24eth waveforge-1p53-follow-ups

## Rationale

This changes a stated promise in `docs/architecture/contracts/mcp-tool-surface.md` (the retired-model cleanup fields paragraph).

Waveforge reported, on v1.53.0, that running an upgrade test against a scratch copy removed retired models from the real shared cache. Their sandbox blocked the first attempt; they then approved it deliberately.

What the tree does today:

- `_retired_cleanup_targets()` in `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` always targets `~/.wavefoundry/cache`, plus the `FASTEMBED_CACHE_PATH` and `WAVEFOUNDRY_ONNX_SRC_CACHE` overrides, whichever repository is being upgraded. The model cache is shared by every repository on the workstation, so cleanup is correctly workstation-wide. (inferred: read.)
- The CLI dry run (`wf upgrade --dry-run`, which runs the installed `upgrade_wavefoundry.py --dry-run`) builds its summary with `_retired_model_cleanup_result("dry_run")`: status `dry_run` and four empty lists. The contract states exactly that: "Dry-run reports status `dry_run` and four empty lists." So a dry run says nothing about what the real run will delete. (inferred: read.)
- Seed `160` already has a "Wavefoundry 1.16 retired-model cleanup" section that says dry-run deletes nothing and that removal applies to the user-global cache shared by every repository. It does not say that a rehearsal against a scratch copy deletes for real, or how to see what will go. Wavefoundry's own rendered `docs/prompts/upgrade-wavefoundry.prompt.md` has no such section, and no copy exists under `.wavefoundry/framework/install/lifecycle-prompts/`. (inferred: read and search.)
- The public MCP `wf_upgrade` tool has no dry run; the upgrade prompt says preview is CLI-only. (inferred: read of the served signature and the prompt.)
- A component that is a symlink is removed by the real run (only the link goes, the target stays); only a symlinked cache root, a reparse-point ancestor, a non-directory or an unverified custom component is reported `unowned`. (executed by the red-team readiness seat on a scratch cache.)

The dry run is produced by the installed runner, so the preview reaches operators only on an upgrade from a release that contains it. Waveforge's next upgrade from 1.53 will not show it; the release notes and Waveforge handoff supply the warning before that hop.

## Product Intent

An operator or agent who runs `wf upgrade --dry-run`, including a rehearsal against a scratch copy, learns before the real run which retired model components it will delete and that they live in the shared workstation cache. Before: the dry run reports four empty lists. After: it also lists the planned components, path-free, and the upgrade prompt says a rehearsal deletes them for every repository. AC-1 and AC-5 test this. What the real run removes, and when, does not change. Before the first upgrade from 1.53, operators can read the release notes and Waveforge handoff. The installed 1.53 runner cannot list components. Later upgrades using the updated runner can preview them.

## Requirements

1. The CLI dry-run summary gains one additive list field, `retired_model_cleanup_planned`, holding the path-free target ids (`<cache-kind>:<scope>:<component-key>`, matching `_RETIRED_MODEL_CLEANUP_ITEM_RE`) the real run would report in `retired_model_cleanup_removed`.
2. A component is listed when the read-only form of the removal's own pre-checks (flat-key check, ancestor reparse check, cache-root checks, custom-component ownership via `_legacy_custom_component_owned`) would let the real run remove it. A symlinked default-scope component is listed, as the real run removes the link; a symlinked custom-scope component is not, as `_legacy_custom_component_owned` refuses it and the real run reports it `unowned`. A component the real run would report `absent` or `unowned` is not listed. The preview never deletes, unlinks, renames or creates anything.
3. When `_cleanup_version_eligible(to_version)` is false, the list is empty and the dry-run log says cleanup will not run for this target version. Otherwise the log says the active-model authority and index epoch are checked at apply, after the reindex, so the list names what is eligible for removal if those checks pass. The list comes from the installed runner's allowlist; the log says so.
4. The dry run keeps status `dry_run` and the four existing lists empty. The summary schema version and every real-run field are unchanged. `_retired_model_cleanup_from_mapping` and every dry-run projection of the cleanup fields carry the new field; real-run projections and lock defaults are unchanged.
5. Seed `160`'s "Wavefoundry 1.16 retired-model cleanup" section adds that a rehearsal against a scratch copy still deletes from the shared workstation cache, and that `wf upgrade --dry-run` lists the planned components in `retired_model_cleanup_planned`. Wavefoundry's rendered `docs/prompts/upgrade-wavefoundry.prompt.md` is not changed: it has no retired-model section, and adding one is outside this change.
   Include a warning in the release notes and a Waveforge handoff draft available before apply. State that rehearsal cleanup affects the shared workstation cache and that the installed 1.53 runner cannot preview the component list.
6. The contract paragraph in `docs/architecture/contracts/mcp-tool-surface.md` that states "Dry-run reports status `dry_run` and four empty lists" names the new dry-run field and its rule, and keeps the five terminal fields' key-parity statement for real runs. The same sentence in `docs/contributing/build-and-verification.md` ("Dry-run reports `dry_run` with four empty lists") gains the same addition.
7. Windows, macOS, Linux and WSL2: the preview uses the same lstat and reparse-point checks as the removal on each platform, so it lists exactly what that platform's real run would remove; a Windows junction component is treated as the real run treats it there.

## Scope

**Problem statement:** a workstation-wide deletion has no preview.

**In scope:**

- A read-only planned-removal helper in `upgrade_wavefoundry.py` and the dry-run summary field.
- Tests in `test_upgrade_wavefoundry.py`.
- The seed `160` section, the contract paragraph and the matching sentence in `docs/contributing/build-and-verification.md`.

**Out of scope:**

- A dry run on the public MCP `wf_upgrade` tool.
- Changing the cleanup targets, the allowlist, or making cleanup per repository.
- Adding a retired-model section to Wavefoundry's rendered upgrade prompt.
- Adding an opt-out flag for the real run.

## Acceptance Criteria

- [x] AC-1: With a temporary home cache holding two allowlisted retired components and one non-allowlisted directory, the CLI dry-run summary's `retired_model_cleanup_planned` lists exactly the two target ids and the other directory is untouched; with the preview removed, the test fails. Oracle: unit test driving the dry-run summary.
- [x] AC-2: After the dry run every planned component and every symlink target still exists byte-identically. A symlinked default-scope component is listed as planned; a symlinked custom-scope component and a symlinked cache root are not listed, matching the real run's `unowned`. Oracle: before/after tree comparison plus a call to the real removal on a copy, asserting the preview agrees with it.
- [x] AC-3: The dry-run summary keeps status `dry_run`, the four existing lists empty and the schema version unchanged, and the new field survives `_retired_model_cleanup_from_mapping`.
- [x] AC-4: With an ineligible target version, the list is empty and the log says cleanup will not run.
- [x] AC-5: The release notes and Waveforge handoff draft each warn before apply about the shared cache and the 1.53 preview limitation. The seed `160` section states the rehearsal behaviour and names `retired_model_cleanup_planned`, the contract paragraph and the build-and-verification sentence name the new dry-run field, and the change's own suites and every test it adds pass; the documents this change edits validate.

## Tasks

- [x] Factor the removal's pre-checks into a read-only helper and add the planned list to the dry-run summary.
- [x] Carry the field through `_retired_model_cleanup_from_mapping` and every dry-run projection found by a census of the five cleanup keys.
- [x] Tests for AC-1 to AC-4.
- [x] Seed `160` section edit under `seed_edit_allowed`; contract paragraph edit.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| preview | implementer | — | read-only helper and summary field |
| tests | implementer | preview | AC-1 to AC-4 |
| docs | implementer | preview | AC-5, seed and contract |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/architecture/contracts/mcp-tool-surface.md`
- `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

`docs/architecture/contracts/mcp-tool-surface.md`: the retired-model cleanup fields paragraph (Requirement 6). No phase, ownership or flow change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The preview is the fix. |
| AC-2 | required | The preview must agree with the real run and delete nothing. |
| AC-3 | required | Existing consumers of the dry-run summary must not change. |
| AC-4 | important | The preview must not claim a removal that will not happen. |
| AC-5 | required | Release notes and the handoff cover the first hop; the contract must state the field. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-26 | The installed CLI now uses the removal's read-only checks to list eligible shared-cache components before apply. A directory and a default-scope symlink appeared in preview and were removed from disposable copies. The external sentinel survived both the native and forced no-follow removal paths. Invalid custom markers (null, array, or an empty file path) remained untouched and did not interrupt preview. | Three CLI regressions, MCP summary projection and the complete dry-run and cleanup test classes: 43 tests, one platform-specific skip on macOS. The full upgrade module and MCP projection ran 779 tests with two skips, and the containment suite passed 23 tests. Full docs lint passed. The release notes and the operator's unsent [Waveforge handoff](waveforge-handoff.md) cover the first hop from 1.53. |
| 2026-11-26 | Readback: the installed CLI will list eligible retired cache IDs before apply using the same ownership checks as removal. Two untouched caches in a scratch checkout become visible in the plan, while real cleanup still checks authority and the index epoch. AC-1 to AC-5 cover parity, field shape, version scope and the first-hop warning in both operator-facing documents. | Upgrade driver, cleanup projection, upgrade tests, seed 160, contract, build guidance, release notes and Waveforge handoff. |
| 2026-11-26 | Planned from the Waveforge v1.53.0 report, finding 3. | Reads cited in Rationale. |
| 2026-11-26 | Implementation note from the readiness council (nonblocking): native Windows removes through `_remove_retired_component_no_follow`, so the shared read-only pre-check helper must cover that path too, and AC-2's preview-versus-removal comparison should run against whichever removal path the host uses (a Windows run of the test, or a test that drives the no-follow path directly). | council-readiness approval, strongest-challenge. |
| 2026-11-26 | Red-team reverification notes applied: custom-scope symlink stated as not planned; `docs/contributing/build-and-verification.md` sentence added to Requirement 6. | Red-team reverification report. |
| 2026-11-26 | Readiness repair for RDY-1: narrowed to the CLI dry run, symlinked components listed as the real run removes them, first-hop and installed-runner limits stated, eligibility verdict limited to version, seed section amended instead of two copies, contract paragraph added. | Red-team and docs-contract readiness reports. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-26 | Add a read-only planned-removal list to the CLI dry run, and amend the seed's existing cleanup section; keep cleanup workstation-wide. Planner default; the operator asked for a single wave covering the DO items. | Replaying the Waveforge case: the seed sentence reaches their next hop through the incoming pack; from the following release on, the dry run names the components before the sandbox refusal. It advises rather than controls; the rehearsal instructions the operator follows show the list. The allowlist and the removal's own pre-checks supply all of it. It cannot know whether apply-time authority checks will pass, so it says so. Measured by the next rehearsal report. | (B) Seed sentence only: a rehearser running a dry run still sees four empty lists. (C) Scope cleanup to the upgrade target: the cache is shared by design, so per-repository cleanup would leave retired models forever. (D) Require a confirmation flag for cleanup: changes the real run for every operator to fix a preview gap. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The preview's pre-checks drift from the removal's. | One shared helper used by both; AC-2 compares the preview with the real removal. |
| A dry-run projection the census misses drops the field. | Census of every copy of the five cleanup keys during implementation; AC-3. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
