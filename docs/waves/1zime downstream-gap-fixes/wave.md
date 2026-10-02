# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zime downstream-gap-fixes`
Title: Downstream Gap Fixes

## Objective

Close the gaps a downstream fork reported as still open at `5004296a`. A denied file stat, an inherited `PROJECT_ROOT`, a native provider-probe crash or a hung `taskkill` no longer aborts or misdirects setup, upgrade, indexing or dashboard control. Lifecycle responses recommend the real next step when readiness is incomplete and point declared waves at the typed council record. A parameter-mapped alias echoes its own parameter names in response `data` and can carry its own description. The close-time checkbox gate no longer passes an open item written with a non-dash marker, under a missing, renamed or duplicated section heading, or citing an exempt AC later in its text.

## Changes

Change ID: `1zimk-bug setup-and-server-robustness-gaps`
Change Status: `implemented`

Change ID: `1ziml-enh lifecycle-hint-gaps`
Change Status: `implemented`

Change ID: `1zimm-bug alias-parameter-names-in-response-data`
Change Status: `implemented`

Change ID: `1zimq-bug close-gate-checkbox-bypasses`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-01

## Wave Summary

Wave `1zime` (Downstream Gap Fixes) delivered 4 changes: Setup and Server Robustness Gaps: Denied Stat, Inherited Root, Probe Crash, Unbounded Taskkill, Lifecycle Hints Name the Pending Readiness Lanes, the Unwritten Objective and the Right Verdict Record, Parameter-Mapped Aliases Rename Their Parameter Names in Response Data and May Declare Their Own Description, and The Close Checkbox Gate Reads Every Checklist Item, Requires Both Sections and Takes the AC Id From the Start. Notable adjustments during implementation: Setup and Server Robustness Gaps: Denied Stat, Inherited Root, Probe Crash, Unbounded Taskkill: Delivery-review repair (implementer B, `server_impl`): `index_health` no longer reports a file the build kept while its stat is denied as removed or stale. `McpRepoCache._layer_current_state` passes both unreadable sets to `walk_repo` and `_layer_health` leaves those paths (and paths under unreadable directories) out of the comparison; a genuinely removed file is still reported. Test `LayerHealthFileMetaTests.test_unreadable_paths_are_neither_removed_nor_stale`; mutants K1 and K2 killed; Setup and Server Robustness Gaps: Denied Stat, Inherited Root, Probe Crash, Unbounded Taskkill: Delivery-review repair round. (1) `walk_repo` now runs every path- and name-based filter (hard-coded excludes, dot directories, name layer, extension layers, ignore files) before the entry stat, through the new `_walk_entry_is_regular_file`; only the content sniff and the size cap follow it, so a gitignored denied entry (a `server.pem` symlink into a protected directory) is never stat'ed, reported or allowed to block `preflight_rebuild_sources` or a storage rebuild. The ignore check moved above the content sniff, which changes no result because both only exclude. The optional "denied entry with no stored rows is absent for a storage rebuild" alternative was NOT taken: filter order alone removes the reported false block, and the strict census stays fail-closed for any non-ignored denied entry. (2) Added the probe-child venv-activation assertion and the `0xC0000000` crash-code boundary test. Scratch mutations: stat-before-filters, removed child activation and `>=` to `>` each fail a named test; Setup and Server Robustness Gaps: Denied Stat, Inherited Root, Probe Crash, Unbounded Taskkill: Implemented all four fixes test-first. (a) `walk_repo` classifies each entry with `os.stat`; absence errnos and winerrors 21/123/1921 stay silent, any other `OSError` goes to the new `unreadable_files` set and one stderr line; the build, `preflight_rebuild_sources` and `_validate_prepared_removals` pass the union to the existing `unreadable_dirs` consumers. (b) `phase_docs_gate` and the rendered hooks' `run_command` pin `PROJECT_ROOT` to the checked root; surfaces re-rendered. (c) `_probe_embedding_provider` spawns `_measure_embedding_provider` in a child through `_run_install_step` (600 s, stdin closed, `faulthandler`, `WF_PROBE_RESULT ` last line) and maps signal, crash code, exit, parse and timeout outcomes to a rejected candidate. (d) dashboard `taskkill` bounded at 10 s; two census entries added. Each new test failed on the unfixed code (AC-1 `PermissionError`, AC-2 rows lost to `PermissionError` in the build, AC-3 other repository restamped and gate passed, AC-4 the caller died with -11, AC-6 no timeout and `TimeoutExpired` raised).

**Changes delivered:**

- **Setup and Server Robustness Gaps: Denied Stat, Inherited Root, Probe Crash, Unbounded Taskkill** (`1zimk-bug setup-and-server-robustness-gaps`) — 7 ACs completed. Key decisions: Treat (a) as a walker defect for any denied file stat, with `.env` as the reported instance; Interpret "stops the server" as "stops the server's walk consumers" (assumption)
- **Lifecycle Hints Name the Pending Readiness Lanes, the Unwritten Objective and the Right Verdict Record** (`1ziml-enh lifecycle-hint-gaps`) — 8 ACs completed. Key decisions: Read "pending lanes at readiness" as the wrong top-level hint plus unnamed pending lanes when readiness is incomplete; Read "objective-review reminder" as an advisory for the unwritten scaffold Objective at Prepare (ASSUMPTION)
- **Parameter-Mapped Aliases Rename Their Parameter Names in Response Data and May Declare Their Own Description** (`1zimm-bug alias-parameter-names-in-response-data`) — 8 ACs completed. Key decisions: This change supersedes the `data` clause of 1zim0's Requirement 3 (data stays canonical); Rename only top-level `data` keys that are renamed parameters of the called alias
- **The Close Checkbox Gate Reads Every Checklist Item, Requires Both Sections and Takes the AC Id From the Start** (`1zimq-bug close-gate-checkbox-bypasses`) — Require both headings at close; allow an empty `## Tasks` section; Treat a misspelled, suffixed or demoted heading as missing rather than detecting near-misses
## Watchpoints

- Watchpoint: waves `1zimd` (`setup_index.py` and its tests) and `1zimf` (`server_impl.py`, `mcp_tool_extensions.py` from `1zimo`, `wave_lint_lib/wave_validators.py` from `1zimp`, `test_extension_tool_modules.py`, the MCP tool surface spec) touch the same files; whichever lands second rebases.
- Watchpoint: `1zimq` and `1ziml` both touch `lifecycle_gate_support.py`; `1zimq` must not change any existing closed doc's outcome (census: 0 non-dash items, 0 late-cited AC ids), and Prepare's per-change section gate refuses non-dash checklist items on the planned wave, since per-change lint runs only once a wave is implementing.
- Watchpoint: `1ziml` changes hint fields only. Regenerate the lifecycle golden explicitly and review its diff against that change's AC-7 before delivery review. Confirm first that the council brief text is not a receipt-digest input.
- Watchpoint: intended required lanes are code-reviewer, qa-reviewer and security-reviewer. Prepare publishes the roster from the declared Serialization Points, and security-reviewer is requested by judgment. Security review covers `1zimk` (b), where the docs gate ran against and wrote into an inherited root, and `1zimm`, where alias responses rename keys but never values.
- Follow-up: confirm with the reporter that "objective-review reminder" meant the unwritten scaffold Objective at Prepare, not a delivery-time check against the Objective.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the hint helper as first written would skip a docs-lint error that has no recovery_usage and recommend the review step on a wave whose docs fail, and single-blocker fixtures would not catch it; resolved by taking the hint from the first blocking diagnostic and a two-blocker AC-1 fixture; strongest-alternative: put denied file paths into the existing unreadable set rather than threading a new parameter, adopted in Requirement 2 as the union passed to the existing guards)
- Prepare council seat evidence (2026-10-01): one independent Opus reviewer ran both seats and the code, qa, docs-contract, release and security lanes against HEAD 232c5a24 with read-only probes: all four 1zimk gaps reproduce or hold by reading (a PermissionError from is_file on Python 3.13.5; phase_docs_gate and the hook spawn without a pinned root; the probe runs in-process; taskkill has no timeout); the council brief is not a receipt input; no core consumer reads alias data. It blocked on the hint ordering, the unmeetable golden AC, the errno classification, the incomplete unreadable-guard list and undeclared probe tests; its edits were applied verbatim, plus its advisories on the AC-3 fixture and the probe spawn resolver.
- Prepare council seat evidence for the additions (2026-10-01): one independent Opus reviewer reviewed `1zimq` (new) and the `1zimm` description extension against the code with scratch probes: all four close-gate bypasses plus a fenced-heading residual reproduce; census re-derived (1,033 docs; 0 non-dash items, 0 late-cited AC ids). It blocked on Prepare never running per-change lint for a planned wave, the parser missing from the reload purge set, and 31 heading-less close fixtures; its edits and three bookkeeping edits were applied verbatim and re-verified (all lanes APPROVE).

- **Delivery Wave Council [delivery-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a denied entry was classified before every filter, so an ignored denied file blocked a storage rebuild with no opt-out; fixed by running path, name and ignore filters before the stat; strongest-alternative: also treat a denied entry with no stored rows as absent for a rebuild, not taken because filter order removes the false block and the strict census stays fail-closed)
- Delivery seat evidence (2026-10-01): one independent Opus reviewer reproduced every gap against HEAD in scratch copies (real mode-000 `.env`, real SIGSEGV and timeout in the probe child, inherited PROJECT_ROOT against a second git repo, all four close-gate bypasses in LF and CRLF), compared the lifecycle golden by diagnostic code (no status, code or advisory change), re-ran a 1,033-document census against HEAD, and ran 23 mutants. Its seven maybe-later findings (filter order, index_health staleness, near-miss headings, closed-doc note, five test gaps, delivery-phase hint, pure-call usage) were repaired by the two implementers and re-verified in a fresh scratch copy (all resolved; implementer full suite 10517 OK).

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 30 | 141,408 |
| implement | 11 | 988,625 |
| review | 24 | 656,004 |
| **Total** | **65** | **1,786,037** |

<!-- wave:context-efficiency-state {"generation":65,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":11,"content_source_credit":992480,"derived_artifact_credit":0,"direct_net":988625,"estimated_tokens_saved":988625,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":192,"response_debit":3663,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":30,"content_source_credit":191378,"derived_artifact_credit":5365,"direct_net":141408,"estimated_tokens_saved":141408,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6382,"response_debit":58166,"source_credit_count":44,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":24,"content_source_credit":726859,"derived_artifact_credit":2008,"direct_net":656004,"estimated_tokens_saved":656004,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2892,"response_debit":72287,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":65,"content_source_credit":1910717,"derived_artifact_credit":7373,"direct_net":1786037,"estimated_tokens_saved":1786037,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9466,"response_debit":134116,"source_credit_count":81,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11529},"wave_id":"1zime downstream-gap-fixes"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
