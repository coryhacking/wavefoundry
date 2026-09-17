# Honor Configured Record Roots Through One Shared Path Resolver

Change ID: `1y042-enh record-roots-config-and-resolver`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-14
Wave: `1y0gz record-layout-roots`

## Rationale

**Brief.** Goal: let a target repository relocate its wave and plan roots through committed configuration, with the default reproducing today's `docs/waves` and `docs/plans` layout exactly. Audience: integrators such as Waveforge whose document tree differs from the default, and framework maintainers who currently maintain the same two literals in about twenty files. Approach: one import-light resolver module, a typed config block, and a census test that forbids new literal joins. Constraints: config-driven, no repository code loaded by the server; fail-closed on an invalid root; byte-identical default behavior. Success: a repository with `record_layout` pointing elsewhere passes every lifecycle tool, docs-lint, and indexing without a single patched framework file.

Verification against the current tree found the layout hardcoded in 41 places in `server_impl.py` (for example `list_waves` at line 3678, `_resolve_wave_md_matches` at 7182, `_resolve_change_doc_matches` at 7343, `create_wave` at 8896) and in about 60 more across 19 other scripts, led by `wave_lint_lib/wave_validators.py` (18) and `wave_lint_lib/constants.py` (7). There is no shared helper analogous to `repo_root.py` or `index_paths.py`. `docs/workflow-config.json` already declares `wave_implement.wave_root`, but nothing reads it, and a comment at `docs_gardener.py:172-174` claiming the linter consumes it is stale. The RFC in `docs/reports/wavefoundry-modularity-rfc.md` proposes a `PathResolver` protocol bound by auto-discovered modules; this change takes the config-driven route instead, consistent with the project's recorded stance that adapters are config-driven rather than plugin-driven.

Re-verified 2026-09-17 against four intervening commits (`1y3og setup-local-reconciliation`, `1y0h*` orchestration guidance, `1y4j8 portable-windows-path-test`, `1y6hg python-runtime-deprecation-advisory`): `docs/workflow-config.json` and both `wave_lint_lib` files are byte-identical across all four (`git diff` empty on each). Current line numbers after one localized insertion earlier in the file: `list_waves` 3684, `_resolve_change_doc_matches` 7345, `_resolve_unique_change_doc` 7451, `create_wave` 8891, the repo-cache wave fingerprint 3806. No requirement below changes; only navigation anchors moved. `setup_readiness.py`, the new module from `1y3og`, reads only `('indexing', 'setup', 'platforms', 'embedding', 'providers')` from workflow-config and writes nothing — no collision with the `record_layout` key this change adds.

Directly validated 2026-09-17 against Waveforge's real fork (`docs/reports/waveforge-fork-audit.md`): their `set_root: "docs/features/"` config key and their own `_resolve_wave_doc_matches`/`_plan_wave_doc_path`/`_move_wave_doc` functions confirm they already built a bespoke path-resolution layer for exactly this need — this change's premise is not hypothetical. Separately confirmed: `chunker.py` and `graph_indexer.py`'s "wave" references are almost entirely internal development-provenance comments, not document-model coupling, so once this change and `1y043` remove the remaining path-level coupling, the indexing pipeline built on top should merge cleanly for Waveforge with no further work on this side.

## Requirements

1. A new module `.wavefoundry/framework/scripts/record_paths.py` with only stdlib imports exposes `load_record_roots(root) -> RecordRoots`, where `RecordRoots` carries the repo-relative and absolute paths for the waves root and the plans root, plus `validate_record_layout(root) -> list[diagnostic]`.
2. Configuration lives in a new top-level `record_layout` object in `docs/workflow-config.json` with exactly two optional string keys, `waves_root` and `plans_root`. Absent keys default to `docs/waves` and `docs/plans`. When `record_layout` is absent and the legacy `wave_implement.wave_root` is present, that value is honored for the waves root and docs-lint reports an informational migration hint naming the new key.
3. Validation is fail-closed. A root is invalid when it is absolute, contains `..`, resolves outside the repository root, passes through a symlink that leaves the repository, equals the other root, or nests inside the other root. An invalid layout is a docs-lint error (`record_layout_invalid`), and every MCP tool that constructs a record path returns that same diagnostic and performs no read or write. Nothing silently falls back to the defaults.
4. Every `docs/waves` or `docs/plans` path construction in `server_impl.py` routes through the resolver, including the six lifecycle handlers' shared helpers, the repo-cache fingerprint (line 3806 as of 2026-09-17; re-verify at implementation time), and the literal substring check near it.
5. Every path construction in `wave_lint_lib` (constants, wave validators, core validators, link validators) routes through the resolver, so docs-lint validates the configured roots rather than the defaults.
6. The remaining scripts that hardcode the layout route through the resolver: `docs_gardener.py`, `render_agent_surfaces.py`, `render_platform_surfaces.py`, `indexer.py`, `memory_backfill.py`, `techdocs_audit_lib.py`, `lifecycle_id.py`, `review_policy.py`, `review_evidence.py`, `commit_provenance.py`, `gardener_metadata.py`, `upgrade_wavefoundry.py`, `reconcile_scan.py`, `install_log_lib.py`, `context_efficiency.py`.
7. A census test asserts that no non-test module under `.wavefoundry/framework/scripts/` outside `record_paths.py` constructs a path from the literals `docs/waves` or `docs/plans`. Literals inside user-facing message strings are permitted only through an explicit allowlist in the test that names file and purpose.
8. The default configuration produces paths byte-identical to today: the existing lifecycle, lint, indexing, and rendering test corpora pass unchanged. This change adds its own small schema-pin test covering the eight lifecycle tools it touches (`wf_create_wave`, `wf_add_change`, `wf_remove_change`, `wf_list_waves`, `wf_list_plans`, `wf_get_change`, `wf_current_wave`, `wf_prepare_wave`), so `1y0gz` does not depend on `1y0do tool-surface-snapshot` landing first; when the full golden fixture exists it must also show no change, but that is `1y0do`'s own gate, not a precondition here.
9. The stale comment in `docs_gardener.py` is corrected, and `record_paths` is added to the module purge list at the top of `server_impl.py` so `wf_reload_mcp` picks up changes to it.
10. Documentation: the workflow-config key reference gains the `record_layout` block with its validation rules, and `docs/references/project-overview.md` notes that the roots are configurable.

## Scope

**Problem statement:** The record layout is a hardcoded literal repeated across the framework, so any target repository with a different tree must patch framework files and re-patch on every upgrade.

**In scope:**

- The resolver module, the config block, validation, and the legacy-key fallback.
- Routing all listed scripts through the resolver.
- The census test and the layout-fixture tests.
- Documentation of the new key.

**Out of scope:**

- Nested discovery of wave records at arbitrary depth (`1y043-enh nested-record-lookup`).
- Installer and bootstrap seeds creating non-default roots; a target sets `record_layout` after install and moves its records.
- Rendered prose in `AGENTS.md`, seeds, and prompt docs that mentions `docs/waves` as the conventional location.
- Dashboard configuration beyond what `dashboard_lib.py` already reads from workflow-config.

## Acceptance Criteria

- [ ] AC-1: With no `record_layout` block, every path the resolver returns equals the corresponding literal path used today, and the existing lifecycle, lint, indexing, and rendering suites pass without modification.
- [ ] AC-2: In a fixture repository with `record_layout` set to `project/records/waves` and `project/records/plans`, `wf_create_wave`, `wf_add_change`, `wf_remove_change`, `wf_list_waves`, `wf_list_plans`, `wf_get_change`, `wf_current_wave`, and `wf_prepare_wave` dry-run operate on the configured roots, and docs-lint passes on that fixture.
- [ ] AC-3: Each invalid-root class (absolute, `..`, escape via resolution, escaping symlink, equal roots, nested roots) produces the `record_layout_invalid` diagnostic from docs-lint and from `wf_create_wave`, and no file is created.
- [ ] AC-4: With only the legacy `wave_implement.wave_root` set to a non-default value, the waves root honors it and docs-lint emits the migration hint.
- [ ] AC-5: The census test passes on the completed tree and fails when a literal `docs/waves` join is reintroduced in a non-allowlisted module.
- [ ] AC-6: The eight touched lifecycle tools' schemas are unchanged by this change's own pin test (and, once `1y0do` exists, the full golden fixture too), and `wf_reload_mcp` picks up a modified `record_paths.py` in the reload test.
- [ ] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Write `record_paths.py` with `RecordRoots`, `load_record_roots`, `validate_record_layout`, and unit tests for every validation class.
- [ ] Add `record_layout` handling to the workflow-config validation path in docs-lint, including the legacy-key hint.
- [ ] Route `server_impl.py` sites through the resolver, batch by area: lifecycle helpers, listing and lookup helpers, cache fingerprint, remaining sites.
- [ ] Route `wave_lint_lib` through the resolver and re-run the lint corpus.
- [ ] Route the fifteen remaining scripts through the resolver.
- [ ] Write the census test with its allowlist.
- [ ] Build the relocated-roots fixture repository and the AC-2 lifecycle tests.
- [ ] Add `record_paths` to the `server_impl.py` purge list and extend the reload test.
- [ ] Correct the `docs_gardener.py` comment.
- [ ] Update the workflow-config reference and `docs/references/project-overview.md`.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| resolver       | implementer | —            | module, validation, unit tests, lint hook |
| server-routing | implementer | resolver     | 41 sites in batches, golden unchanged after each |
| lint-routing   | implementer | resolver     | wave_lint_lib, runs in parallel with server-routing |
| script-routing | implementer | resolver     | fifteen remaining scripts |
| census-fixture | qa          | server-routing, lint-routing, script-routing | census test, relocated fixture, AC-2 and AC-3 |
| docs           | implementer | resolver     | key reference, overview, comment fix |


## Serialization Points

- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/`
- `.wavefoundry/framework/scripts/docs_lint.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/project-overview.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/layering-rules.md` gain the resolver as the single owner of record-root resolution, alongside `repo_root.py` and `index_paths.py`. `docs/architecture/data-and-control-flow.md` notes that lifecycle tools and docs-lint read the same configured roots. A short decision record under `docs/architecture/decisions/` records the config-driven choice over an auto-discovered resolver protocol.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Default behavior must be byte-identical |
| AC-2 | required  | This is the integrator outcome the change exists for |
| AC-3 | required  | Fail-closed containment is the security posture of the change |
| AC-4 | important | Existing configs must not regress silently |
| AC-5 | required  | Prevents the literal creeping back in later waves |
| AC-6 | required  | Public surface unchanged; reload freshness for a purged module |
| AC-7 | required  | Standard change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-14 | Change planned and admitted to `1y0gz record-layout-roots` | this document |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-14 | Config-driven roots in `workflow-config.json`, resolved by one stdlib module | Waveforge already commits that file; no repository code is imported by the server; matches the recorded config-over-plugin stance and the `index_paths.py` pattern | (a) RFC `PathResolver` protocol with auto-discovered modules: most flexible, but the server would execute repository-supplied Python at startup in every host that auto-starts MCP. (b) Environment variable overrides: zero-config for the operator, but invisible to reviewers and not shared across a team |
| 2026-09-14 | Fail-closed on invalid layout, no default fallback | A silent fallback would write records to the wrong tree while the operator believes the config is honored | Warn-and-fallback: friendlier, but creates split-brain record trees that lint then flags after the fact |
| 2026-09-14 | New `record_layout` block rather than extending `wave_implement.wave_root` | `wave_implement` is about implementation policy; the roots are layout; keeping the legacy key as a fallback avoids breaking existing configs | Reuse `wave_implement.wave_root` and add `plans_root` beside it: fewer keys, wrong home |
| 2026-09-14 | Route all nineteen files in this change rather than server plus lint only | A partial routing leaves docs-lint and indexing disagreeing with the server about where records live; the census test only has teeth when it covers everything | Two changes: smaller PRs, but an intermediate state where relocating roots half-works |
| 2026-09-17 | Own schema-pin test for the eight lifecycle tools rather than a hard dependency on `1y0do`'s full fixture | Archetype Council (Sun Tzu, 2026-09-17) found this change's own success criterion transitively blocked on a prerequisite wave whose primary audience is the two maintainer-only refactor waves, not this one — an unforced coupling for the wave Waveforge actually needs first | Keep the hard dependency: fewer moving parts, but delays the Waveforge-blocking change behind unrelated maintainer-facing work if `1y0do` slips |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Mechanical routing of about a hundred sites introduces one wrong root | Batches land behind the existing corpus plus the golden snapshot; the relocated fixture exercises both roots through every lifecycle tool |
| A literal is legitimately needed in a user-facing message and the census blocks it | The allowlist is explicit and reviewed; the message can also be built from the resolver |
| Waveforge's real layout needs nesting the roots cannot express | Nesting is the companion change in this wave; this change only relocates roots |
| Seeds and rendered docs keep saying `docs/waves` | Accepted for this change; the conventional location remains the default, and a seed follow-up can add one sentence about `record_layout` under the seed gate |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
