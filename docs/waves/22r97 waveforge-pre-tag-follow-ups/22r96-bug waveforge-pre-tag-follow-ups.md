# Waveforge pre-tag follow-ups

Change ID: `22r96-bug waveforge-pre-tag-follow-ups`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-06

## Rationale

Waveforge verified `2b6b985a` under their profile and cleared the next tag. They also reported four small gaps, each confirmed against the current tree:

1. **Recurring incompletes have no lasting remedy.** When the engine stops a file at `MAX_MATCHES` (20,000), it raises `WorkLimit("match_limit")`. `secrets_validators._scan_upstream_raw` (the `if not result["complete"]` branch) records only `detection_or_filter_work_incomplete`, so `scanner_skips.fixed_limit_remedy` gives "retry" advice. The match cap is deterministic for the same content, so a retry cannot clear it. A worker timeout is recorded with detail `worker_timeout`, also with "retry" guidance. Because an incomplete row blocks docs-lint and wave close, such a file blocks a target until someone works out an allowlist entry by hand.
2. **A malformed project rule file reads as an infrastructure failure.** A TOML parse error in `docs/scan-rules.toml` ends in the catch-all handlers of `scanner_upgrade._inspect_root` (`incoming_validator_unavailable`) and `inspect_project_rules` (`validation_unavailable`). The operator cannot tell a broken rule file from a broken validator.
3. **Two bare `wf setup` remedies remain.** `sqlite_storage_migration.py` builds a bare `"wf setup"` command for `storage_migration_required` (the `command = "wf_upgrade" if … else "wf setup"` site), which `index_build` and graph reads reach. `wf_server/memory_handlers.py` has the `memory_query_fallback` text "run wf setup if provisioning is needed".
4. **`wf setup` does not surface a skill collision.** `setup_wavefoundry._run_render_platform_surfaces` runs the renderer without `--manifest` and checks only its exit code. After a collision, setup exits 0 having printed only the renderer's stderr line. The `wf render-surfaces` CLI behaves the same way.

## Product Intent

Operators of downstream distributions get an accurate, actionable outcome in each case: a lasting remedy for a deterministic scan limit, a rule-file parse error named as such, repository-selected setup remedies everywhere, and a visible notice when setup or a render withholds a skill. Scanner completion policy, the readiness policy and the exit codes are unchanged.

## Requirements

1. When a scan stops on a deterministic work limit, `secrets_validators._scan_upstream_raw` records a fixed detail string chosen by exact membership in a closed token set, never copying worker text. The tokens are the engine's `WorkLimit` diagnostics `match_limit`, `result_limit` and `component_set_limit`, and the worker error `worker_response_too_large`. When several diagnostics are present, a fixed precedence picks one detail. `scanner_skips` gives each a token-specific remedy, worded as a work limit rather than an input limit:
   - `match_limit` (raw matches before filtering): the shared remedy, which is to convert or split the file, or, after confirming it holds no secrets, add the anchored `[allowlist] paths` entry.
   - `result_limit` and `worker_response_too_large` (filter-surviving candidate findings that could not all be returned, so none are shown): the file holds unreviewed candidate secrets. Lead with splitting the file and rescanning the parts so the findings appear; allow a path entry only after those findings are reviewed.
   - `component_set_limit` (findings are reported but the scan is incomplete): the reported findings stand, and a path entry would also suppress them. Resolve the findings, or narrow the rule, first; allow a path entry only after confirming they are false positives.

   A worker timeout (`worker_timeout`) gets its own per-row guidance: retry first. If it recurs on unchanged content during the scan, the shared remedy applies after confirming no secrets. A timeout during the path-exclusion check (`_upstream_path_excluded`) gets retry guidance only, because a path entry is evaluated by that same check. `incomplete_guidance` does not count timeouts as fixed limits. Other residual reasons, such as filter errors, keep their current text.
2. A project `docs/scan-rules.toml` that is not valid TOML yields the issue code `project_rules_parse_error`, emitted as a fixed literal. Only `WorkerError("invalid_configuration")` from the project-rules `_load_toml` call counts; size limits, decode errors and other worker errors keep their existing outcome. The classification happens only in the child `scanner_upgrade._inspect_root`, around the project-rules `_load_toml` call and not the framework one; the parent `inspect_project_rules` passes it through and does not parse. No parser text, file content or rule value appears in the output.
3. Three bare remedies use the repository-selected `setup_recovery` form, with argv and shell where the response carries structured recovery: the setup-owned `storage_migration_required` remedy in `sqlite_storage_migration.py`, including the graph-read recovery in `graph_snapshot._read_failure` for setup-owned migrations (upgrade-owned migrations keep `wf_upgrade_status`); the `memory_query_fallback` recovery text in `wf_server/memory_handlers.py`, whose `recovery_usage` becomes the command alone, with the explanation kept in the message; and `publication_control._checkpoint_recovery_tail`. Deliberately bare strings stay unchanged: `LEGACY_RECOVERY_GUIDANCE`, the "resume the recorded wf setup continuation" texts, and guidance with no root in scope (`runtime_advisory`).
4. After rendering completes successfully, `render_platform_surfaces.main` prints one summary line to stderr, with the fixed prefix `render_platform_surfaces: PARTIAL SKILL DELIVERY - `, listing every withheld skill name (from the `skill_collisions` records, never from stderr text) and the remedy, when the render reports partial skill delivery and `--manifest` is absent. The existing per-collision `render_agent_surfaces: PARTIAL -` lines are unchanged. `wf setup` (which runs the renderer without `--manifest`) and the `wf render-surfaces` CLI therefore show it once, while manifest callers (upgrade, `wf_sync_surfaces`) add no line. Exit codes are unchanged.

## Scope

**In scope:** the four items above, their tests and the changelog.

**Out of scope:** adding collision state to `wf setup --check --json`; changing which reasons count as intentional exclusions; exit-code changes; scanner rule content.

## Acceptance Criteria

- [x] AC-1: A real file driven through the live worker past `MAX_MATCHES` (for example, more than 20,000 matches of a synthetic fixture rule) is recorded with the match-limit detail and the shared remedy, and becomes complete once an anchored `[allowlist] paths` entry is added. On the current code it gets `detection_or_filter_work_incomplete` with "retry" only. The token-to-detail mapping is exact for all four tokens, including one multi-token case under the fixed precedence. Each token's remedy text is asserted exactly, including the split-first caution for `result_limit` and `worker_response_too_large` and the resolve-findings-first caution for `component_set_limit`, and none is worded as an input limit. A scan-time worker-timeout row (a mock is allowed for the timeout case only) carries the recurring-timeout guidance with its retry step, a path-check timeout carries retry only, and neither is counted as a fixed limit. A filter-error residual keeps its current text.
- [x] AC-2: A syntactically invalid project `docs/scan-rules.toml` yields `project_rules_parse_error` from both `_inspect_root` and `inspect_project_rules`, and the output contains no parser message or file content. On the current code both yield `incoming_validator_unavailable`. Negative controls: a project-parse worker failure other than `invalid_configuration` (for example a mocked `worker_timeout`) and an invalid framework `scan-rules.toml` still yield `incoming_validator_unavailable`.
- [x] AC-3: For structured carriers (the graph-read diagnostic for a setup-owned migration, and `memory_query_fallback`), `recovery_usage`, `recovery_argv` and `recovery_shell` equal `setup_recovery(root)` exactly. For prose carriers (the `MigrationRequired` text and `_checkpoint_recovery_tail`), the text contains `setup_recovery(root)["recovery_usage"]` for a root whose launcher differs from the bare form, and no longer contains "run wf setup" or "rerun ordinary wf setup". Upgrade-owned migrations still give `wf_upgrade_status`. On the current code all of them are bare.
- [x] AC-4: With two real declared-skill collisions, setup's render output and the `wf render-surfaces` CLI each contain exactly one line with the prefix `render_platform_surfaces: PARTIAL SKILL DELIVERY - ` naming both withheld skills, and still exit 0. A `--manifest` render (as upgrade and `wf_sync_surfaces` run it) contains zero such lines. On the current code zero such lines are printed.
- [x] AC-5: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Carry the engine's match-limit diagnostic into the skip detail, and extend the remedy projection (with recurring-timeout guidance).
- [x] Classify project rule TOML parse errors in both inspection entry points.
- [x] Route both bare setup remedies through `setup_recovery`.
- [x] Add the partial-delivery summary line to setup and the render CLI.
- [x] Add regression tests with known-bad controls; update the changelog.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| followups  | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/scanner_skips.py`, `.wavefoundry/framework/scripts/scanner_upgrade.py`, `.wavefoundry/framework/scripts/sqlite_storage_migration.py`, `.wavefoundry/framework/scripts/graph_snapshot.py`, `.wavefoundry/framework/scripts/publication_control.py`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: these are reporting changes within existing owners, with no boundary or flow change. Update `docs/specs/mcp-tool-surface.md` if it lists the affected issue codes or remedy text.

## Platform Behavior

The remedies use the existing `setup_recovery` POSIX and Windows command shapes. The parse-error classification and summary line are platform-neutral. Worker timeouts depend on load on every platform, which is why the timeout guidance keeps retry as the first step.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | A deterministic limit otherwise blocks a target with an unclearable "retry". |
| AC-2 | important | Lets the operator find and fix a broken rule file. |
| AC-3 | required  | Completes the selected-root remedy contract from 22q2u. |
| AC-4 | important | Makes a withheld skill visible to setup users. |
| AC-5 | required  | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-07 | Delivery repair cycle 1 (QA `22r97-qa-del-response-cap-mapping-untested`, by the coordinator): `test_response_cap_from_the_scan_path_records_its_exact_detail_and_remedy` raises the worker's closed `WorkerError("worker_response_too_large")` for the `scan` operation through the real `_scan_upstream_raw` except branch, then asserts the row, `RESULT_REMEDY` and the work-limit summary. Mock justification: a live response-cap fixture needs about 10,000 surviving findings (about 22 s per run). Also pinned `unsupported` status for `project_rules_parse_error` (code-review advisory). | QA mutant M2a (`worker_response_too_large` recorded as `worker_failure`) now fails the new test in a scratch copy; `test_scanner_work_limits` 7 OK, `test_scanner_upgrade` 10 OK |
| 2026-11-07 | Operator-requested wording change for downstream projects, after delivery review: the shipped implement-wave lifecycle prompt now says "disposable work area" instead of "disposable wave work area" (template `install/lifecycle-prompts/implement-wave.prompt.md`, the authored local copy `docs/prompts/implement-wave.prompt.md`, and the phrase pinned in `test_compact_review_artifacts.py`). Prose only. The `.gitignore` block header and seed 180's **Disposable wave work** heading are left unchanged, because the header string identifies existing blocks in downstream projects. | `test_compact_review_artifacts` 4 OK; `wf_sync_surfaces` wrote nothing; full docs lint OK |
| 2026-11-06 | Planned from Waveforge's 2b6b985a follow-up; all four claims confirmed against the tree. The operator chose one small wave before the tag. | Waveforge follow-up 2026-11-06; source checks of `secrets_validators._scan_upstream_raw`, `betterleaks_engine` `WorkLimit("match_limit")`, `scanner_upgrade` catch-alls, `sqlite_storage_migration` and `memory_handlers` remedies, `setup_wavefoundry._run_render_platform_surfaces` |
| 2026-11-07 | Requirement 1 delivered. `scanner_skips.work_limit_detail` maps engine diagnostics by exact membership. Fixed precedence: `result_limit`, then `match_limit`, then `component_set_limit`, because a raised limit returns no findings and outranks the composite-set limit. The worker-error branch already records the closed `WorkerError.code`, so `worker_response_too_large` arrives as a fixed detail. `fixed_limit_remedy` gives token-specific work-limit remedies, a scan-time `worker_timeout` its retry-first guidance, and the new `path_check_worker_timeout` detail retry only. `incomplete_guidance` counts input and work limits separately and treats timeouts as retry candidates. Filter errors keep `detection_or_filter_work_incomplete` and its retry text. | `tests/test_scanner_work_limits.py` (6 tests OK): the live worker with 20,001 synthetic matches records `match_limit`, its exact remedy on two scans, then completes after the anchored entry; exact multi-token mapping; exact remedies for all four tokens; live filter-error residual; mocked timeouts; mixed summary. `test_scanner_input_limits.py` timeout pin updated (13 OK). The response cap was not driven live, because 10,000 surviving findings took 22 s in a probe; its detail comes from the closed worker code set. |
| 2026-11-07 | Requirement 2 delivered. The child `_inspect_root` catches `WorkerError` with code `invalid_configuration` from the project `_load_toml` call only and returns `unsupported` with the literal `project_rules_parse_error`. The parent passes it through without parsing. | `test_scanner_upgrade.py` `ProjectRulesParseErrorTests` (2 tests; file 10 OK): both entry points give the code with no parser or file text; negative controls `worker_timeout`, `worker_input_too_large`, `configuration_size_limit`, `UnicodeDecodeError` and a broken framework TOML (in the child and through an incoming pack) keep `incoming_validator_unavailable`. |
| 2026-11-07 | Requirement 3 delivered. `require_ready` uses `setup_recovery(root)` for setup-owned migrations through the new shared predicate `migration_owned_by_setup` (no receipt, or `entry_path == "setup"`). `graph_snapshot._read_failure` reuses that predicate on the real receipt and carries `recovery_usage`, `recovery_argv` and `recovery_shell`; upgrade-owned migrations and an unreadable receipt keep `wf_upgrade_status`. `memory_query_fallback` sets `recovery_usage` to the command alone, adds argv and shell beside the `_diagnostic` payload, and keeps the explanation in the message. `_checkpoint_recovery_tail` names the selected command. `LEGACY_RECOVERY_GUIDANCE`, the recorded-continuation text and `runtime_advisory` are unchanged. | `test_setup_reconciliation.py` (48 OK; the dispatch test now asserts the exact command and graph diagnostic, and a new tail test); `test_graph_snapshot_readers.py` (51 OK, old mapping updated); `test_memory_records.py` (234 OK, exact structured equality). |
| 2026-11-07 | Requirement 4 delivered. Without `--manifest`, `render_platform_surfaces.main` prints one `PARTIAL_SKILL_DELIVERY_PREFIX` line after a successful render, naming the withheld skills from the `skill_collisions` records and giving the remedy. Per-collision lines and exit codes are unchanged. | `test_declared_extension_skills.py::test_partial_skill_delivery_summary_is_one_line_without_manifest` (file 69 OK): with two collisions, exactly one line in the CLI and in setup's `_run_render_platform_surfaces` argv run through the real renderer, both names present, exit 0; zero lines with `--manifest` and with no collision. |
| 2026-11-07 | Known-bad results on HEAD (scratch `git archive HEAD` copy with the new tests). AC-1: live match test FAIL (`detection_or_filter_work_incomplete`), mapping ERROR (no `work_limit_detail`), remedies FAIL (None), timeout ERROR (no remedy), mixed summary FAIL; the filter-error control passes, as intended. AC-2: parse test FAIL (`incoming_validator_unavailable`); negative controls pass, as intended. AC-3: dispatch FAIL (bare `run wf setup`), tail FAIL (`rerun ordinary wf setup`), graph readers FAIL (`wf_upgrade_status`), memory FAIL (prose `recovery_usage`). AC-4: FAIL (0 summary lines). Mutants, all killed: both `_load_toml` calls classified; any `WorkerError` classified; summary printed with `--manifest`; precedence reordered; timeouts counted as fixed limits; graph read always setup-owned. | Scratch `impl-22r96/head` and `impl-22r96/mutate.py` |
| 2026-11-07 | Related suites green: `test_sqlite_storage_migration` 133, `test_tensorwell_integration` 31, `test_tree_kill_routing` 33, `test_upgrade_recovery_guidance` 7, `test_mcp_tool_registry` 27, `test_betterleaks_engine` 30, `test_distribution_seams` 48, `test_render_platform_surfaces` 169, `test_secrets_validators` 171, `test_scan_secrets` 28, `test_scan_completion` 12, `test_scanner_skips` 12, `test_scanner_worker_config` 7, `test_old_parent_publication` 9, `test_mcp_scan_completion` 1, `test_scanner_fixture_hygiene` 1. No `__pycache__` under `.wavefoundry/framework/`. Changelog Unreleased Fixed bullet added. `docs/specs/mcp-tool-surface.md` names neither the codes nor the remedy text, so it is unchanged. Gapfill: source reads used Bash `sed`/`grep` alongside the loaded MCP tools, for speed on known paths. | `run_tests.py --file` focused runs, 2026-11-07 |
| 2026-11-07 | Platforms. The remedy routes use `setup_recovery`, which formats POSIX (`shlex.join`) on macOS, Linux and WSL2 and PowerShell (`& '...\wf.cmd'`) on native Windows. Tests compare against `setup_recovery(root)` on the running host, so they do not depend on the platform. The scanner remedies, parse-error code and summary line are fixed ASCII text and behave the same on every platform. The timeout tests are mocked. The live match-limit test uses the cross-platform worker. Native Windows was not executed here, which matches the existing qualification. | Code inspection |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-06 | The match cap gets the full fixed-limit remedy; a worker timeout gets the remedy only as recurring-timeout guidance, with retry first. | The match cap is deterministic for the same content. A timeout can depend on load, and allowlisting it on the first occurrence could exclude a file that would scan on a quieter run. Efficacy: Waveforge's motivating cases (always hits `MAX_MATCHES`, always times out) both get a lasting fix. | The full remedy for both (over-excludes on transient load); no remedy for timeouts (leaves Waveforge's case unclearable). |
| 2026-11-07 | Bounded readiness repair after the first full round: token-specific remedies (security S1); `worker_response_too_large` added as a deterministic work limit (QA `22r97-qa-response-cap-intent-gap`); a fixed summary-line prefix (code C1); structured versus prose AC-3 oracles, with the memory `recovery_usage` reduced to the command (QA `22r97-qa-ac3-oracle`); AC-2 negative controls (QA `22r97-qa-ac2-overbroad-control`); path-check timeouts get retry only. | Readiness lane notes in `.wavefoundry/work/22r97/readiness/` | Defer the response cap |
| 2026-11-07 | Readiness repairs F1-F6 from the red-team primer, before any approval: all three deterministic `WorkLimit` tokens; parse-error classification in the child only; third bare remedy and the graph-read migration recovery added, with exact-equality ACs; a live-worker match-cap fixture; the summary line printed only by the renderer without `--manifest`. | Red-team primer `.wavefoundry/work/22r97/readiness/primer.json` | Scope the work-limit remedy to the match cap only |
| 2026-11-06 | One summary line, not a new exit code or a `--check --json` field. | Waveforge asked for exactly this; exit codes stay compatible. | A distinct exit code; extending the setup check JSON. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| PowerShell recovery quoting does not escape curly quotes in a checkout path (pre-existing, display-only; security note) | Out of scope; track as a follow-up. |
| The timeout guidance encourages allowlisting files that hold secrets | The text requires confirming the file holds no secrets, and the entry is anchored to one path. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
