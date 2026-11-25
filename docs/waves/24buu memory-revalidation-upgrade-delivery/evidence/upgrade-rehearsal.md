# Upgrade rehearsal: 1.51.0 to 1.52.0 candidate

Owner: Engineering
Status: active
Last verified: 2026-11-24

Date: 2026-11-24. Evidence for wave `24buu` planning. Logs live in the session scratchpad `rehearsal/` folder (`build.log`, `install151.log`, `upgrade-zipapp-attempt.log`, `upgrade-attempt1-docsgate.log`, `upgrade.log`, `cleanup.log`, `setupcheck.json`, `dryrun.log`).

## Setup

- **Candidate pack.** `wavefoundry-1.52.0.q5sn.zip` was built from `git archive HEAD` (`cbc69fb8`) in a scratch copy. `build_pack.py` refuses a tree without a `## [1.52.0]` CHANGELOG section, so the copy got a stub section and `--skip-docs-gate`. The main repository was not modified.
- **Target.** A scratch git repository with a two-file Python app. 1.51.0 was installed from `~/.wavefoundry/dist/wavefoundry-1.51.0.q5hc.zip` with Phase 1 setup (`setup_wavefoundry.py --confirm-hosts-stopped --model-bundle wavefoundry-models-3.zip`), which exited 0 with no network.
- **Phase 2 was skipped.** Seed agent work (seeds 030 to 178) was not run. The required docs were stubbed and `wf render-surfaces` was run so that 1.51.0 docs lint passed. No `AGENTS.md` exists.
- **Operator state.**
  - One active memory record (`03k2h-mem`) and one wave (`03k5d demo-wave`) were created with 1.51.0 code.
  - `.claude/settings.local.json` allows `wf_add_change` and `wf_get_change`.
  - `.claude/settings.json` denies `wf_remove_change`.
- **Upgrade.** `wf upgrade --root . --pack <candidate> --yes --confirm-hosts-stopped`, then `wf upgrade --cleanup`.

## Interventions and incorrect end states

1. **The release zipapp entry fails before doing anything.** `python3 wavefoundry-1.52.0.q5sn.zip --root <target> --confirm-hosts-stopped` raises `ModuleNotFoundError: No module named 'contained_files'` from `embedded_model_bundle.retain` (zip line 94, `import contained_files`). The zipapp ships only `__main__.py`, `upgrade_bridge_bootstrap.py`, `subprocess_util.py` and `embedded_model_bundle.py`. The 1.51.0 zipapp has the identical code, so the bug predates this release. Seed 160 (line 49) tells protocol-1 targets to use this entry. The `wf upgrade --pack` path works. Kind: mechanical (pack builder). Removed by 24but or 24ax3: **no**.
2. **All five spec tools are withheld after upgrade.** The summary has five `spec_tool_permission_holds` entries, and cleanup prints five `Withheld renamed tool:` lines. Three come from exact-name rules: the deny on `wf_remove_change` in `settings.json`, and allows on `wf_get_change` and `wf_add_change` in `settings.local.json`. Two come from the missing review (`wf_new_spec`, `wf_close_spec`). `spec_permission_holds(root)` returns all five. Kind: mechanical. Removed: **yes, by 24ax3** (AC-1 and AC-5 cover exactly this shape).
3. **The managed allow rule keeps the old name.** `.claude/settings.json` `permissions.allow` still holds `mcp__wavefoundry__wf_get_change` and no spec name. The summary lists it under `renderer_provenance_flags` as "SELF-HEALING", but it heals only after the hold clears. Kind: mechanical. Removed: **yes, by 24ax3**, indirectly, because the next permissions render runs once holds clear. 24ax3 should confirm that the backstop render in the same upgrade picks this up after migration, not only on the next upgrade.
4. **Unedited lifecycle prompts are reported but not replaced.** `lifecycle_baseline_drift` reports `upstream_changed_local_matches_previous` with `action: "overwrite: Replace the unedited local copy with the incoming template."` for `docs/prompts/implement-wave`, `memory-review`, `close-wave`, `close-spec` and `explain`. The runner preserves all five ("report only; project copies preserved").
   - After upgrade, `docs/prompts/memory-review.prompt.md` and `close-wave.prompt.md` contain 0 `check_note` mentions. The incoming baseline has 5.
   - Kind: agent-guidance. Removed: **partly, by 24but**. Its requirement 3 asks the agent to merge the keep rule, but only into memory-review and close-wave, and as an agent edit. Because each local copy is byte-identical to the previous template, the runner could overwrite it safely with no agent step. That would also fix items 5 and 6.
5. **Unedited prompts still name the retired tools.** The reconciliation lists 10 candidates naming retired tools (`wf_close_change`, `wf_get_change`) in the same unedited prompts: `close-spec.prompt.md` ×6, `close-wave` ×1, `implement-wave` ×1, `explain` ×2 (`v2-ambiguous`). Agents following these prompts call tools that no longer exist. Kind: agent-guidance. Removed: **no**. An automatic overwrite of unedited copies (item 4) would remove all of them.
6. **`plan-template.md` is falsely reported as locally edited.** `docs/plans/plan-template.md` is reported `upstream_changed_local_differs_from_previous` with "merge: ... by hand". The only difference from the 1.51.0 template is the materialized `Last verified: 2026-11-24` against `{{generated_at}}`. The drift classifier does not normalize the placeholder, so every project gets a hand-merge instruction. Kind: mechanical (classifier). Removed: **no**.
7. **A manual cleanup continuation remains.** Phases 0 to 4 end with "Proceed with agent editing pass, then run: upgrade-wavefoundry --cleanup". The cleanup then lists five agent editing-pass steps: drift detection, behavior contract gaps, scan findings, docs gate re-run and an optional `--update-index`. This is by design on the CLI path. MCP `wf_upgrade` runs the phases itself. Kind: agent-guidance. Removed: no, and none is expected.
8. **The skills name withheld tools.** The rendered `wf-close-spec` skill tells agents to call `wf_close_spec`, which is withheld (item 2). Until the holds clear, skills and prompts disagree with the served tool list. Removed: **yes, by 24ax3** (through item 2).
9. **Two notes on the main repository.**
   - Building a pack from the live tree is refused without a release CHANGELOG section. That is expected and release-only, not an upgrade intervention.
   - A stray `.wavefoundry/framework/scripts/__pycache__/` exists in the main repository, timestamped 18:43, holding `contained_files`, `mcp_tool_extensions`, `setup_commands` and `spec_tool_permissions` .pyc files. It predates this rehearsal (build at 18:57) and matches the parent session's ad hoc `python3 -` import of `spec_tool_permissions`, which ran without `PYTHONPYCACHEPREFIX`. Left in place per the hygiene rule (report, do not clean).

## Worked with no intervention

- Phase 1 install of 1.51.0, fully offline with the cached model bundle.
- `wf upgrade --pack` phases 0 to 4:
  - pre-flight, seed diff report, extraction and surface render;
  - prune (0), secrets policy (materialized `docs/scan-rules.toml`), lifecycle policy (idempotent) and the sidecar cleanup;
  - the docs gate (passed once the target was lint-clean beforehand);
  - the index update with the cached models (docs and code layers complete) and the graph rebuild.
- `wf upgrade --cleanup` exited 0.
- After upgrade:
  - `wf setup --check --json` reports `ready` with no reasons.
  - `server.py --dry-run` passes.
  - `wf docs-lint` passes.
  - `memory_brief(context="review")` loads the 1.51.0 record with `revalidation_reasons: []`.
  - The 1.51.0 wave and the memory record are intact.
  - New surfaces were added: the `wf-contract` skills, `author-behavior-contract.prompt.md` and `codebase-map.md`.

## Not exercised

- Seed 160 agent steps beyond reading the summary, the MCP `wf_upgrade` path, Windows, user-level settings, and a project with edited lifecycle prompts.
- A project whose Phase 2 was real (`AGENTS.md`, personas).
