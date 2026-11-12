# Explain statistics coverage and health

Change ID: `231kf-enh explain-statistics-coverage-and-health`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-11
Wave: 231kh explainable-project-statistics

## Rationale

Tensorwell's 1.42.0+q2u7 field report found useful totals without enough context to act: omitted benchmark files, invisible incomplete scans, candidates absent from the prose, unexplained lifecycle completion and a large context-saving estimate. These are reported downstream observations, not independently reproduced Tensorwell results. This change addresses feedback items 5–9; source roles, inline tests and directory views belong to companion change 231kg.

Current source reads establish `_files` reports a cap and aggregate unreadable/binary counts but no size-skip paths; `_secrets` reads only findings; `_lifecycle` aggregates all assigned checklists without per-wave rows; `_token_savings` aggregates healthy published checkpoints but discards each contributing row. An executed `_memories` control with active/candidate/rejected records returns all three statuses, so candidate omission is not established as a collector defect. Tensorwell's upgrade count may instead include proposals not yet written as records. `scan_secrets.update_secrets_scan` writes the latest scan type/time/completion, replacing the preceding state; `scanner_completion` explicitly does not prove a whole-tree scan ran.

## Product Intent

An operator should be able to distinguish counted work from omitted files, current outstanding scanner failures from a historical scan, active memories from candidates, and recorded accounting from measured savings in one read-only report. AC-1 through AC-5 jointly establish that outcome on deterministic fixtures; human comprehension and Tensorwell's live state remain field-validation questions. This supports the adopted vision's Horizon 2, a living understanding with provenance and uncertainty visible, without claiming a horizon exit or altering the vision.

## Requirements

1. **File coverage.** Code/TODO sections must return skip counts by reason and up to 10 sorted repository-relative example paths per reason, plus omitted counts. Distinguish intentional index-policy exclusions, binary candidates, size-cap exclusions and unreadable eligible files/directories. Extend the existing walker with optional observation collection where needed rather than walking the repository again or changing indexing eligibility. Do not follow newly introduced links or expose file content. Report pruned lifecycle evidence directories as intentional policy exclusions, including their observed directory count and bounded examples under configured record roots; do not count their unvisited descendant files or lines. State which exclusions are observable without enumerating pruned trees; do not claim an exhaustive list below those trees. Existing unavailable/incomplete behavior for unreadable eligible scope stays intact. The actual `indexing.max_file_bytes` limit and scope remain visible.
2. **Recorded scan health.** The secrets section must read existing scanner state and outstanding skip evidence without running a scan, pruning history, writing files or opening a writable store. Report latest recorded scan scope/time/completion separately from the last recorded full scan's time/completion, and from current outstanding incomplete counts by reason and intentional exclusions by reason. Include bounded relative paths from coverage records only, never finding matches, finding paths, credentials, hashes, identities or arbitrary error detail. Report the count of configured project allowlist path entries, clearly not the number of matching files. Label scan history as local to this machine: its gitignored state is not shared project history and may be absent on a fresh clone. Missing or malformed sources produce unknown/unavailable fields with fixed reasons, not zero or clean assertions.
3. **Preserve full-scan history at its owner.** Extend the existing scanner publication path with a small backward-compatible last-run/last-full summary so subsequent incremental or no-work operations do not erase full-scan identity. Cover the actual full/incremental producer paths used by the indexer, docs validation and the explicit scan tool; use one shared summary publisher. A full attempt with incomplete coverage must be recorded as incomplete, never substituted with an older successful full scan. A per-edit docs lint updates latest scan only when secret scanning actually executes; record it as incremental with the requested changed-file scope, without replacing last full scan. A no-work or read-only assessment does not update either scan timestamp or claim a scan ran. Existing state without full-run evidence is unknown; no backfill from findings mtime, no forced migration scan and no finding-ledger schema change. Include scan/rules identity and recorded-scope qualification; a later rules change or file change must not be presented as a current-tree clean guarantee. Publication failure retains prior observations and their original timestamp, never stamps fresh health, and yields an explicit unavailable/incomplete publication diagnostic under existing scanner failure policy. Stats exposes retained observations as historical; when no durable failure marker exists it cannot claim to know an unrecorded attempt.
4. **Memories.** Render every returned `by_status` count, including candidates awaiting validation, rejected and archived records, and retain active-kind breakdown. Reuse `load_memory_records` and the existing schema. Make candidate-record counts explicit; do not mix unwritten proposals, backfill worklists or pending archive transitions into that count. If malformed records prevent a trustworthy count, disclose that limit rather than manufacturing a reconciliation with an upgrade total. Validate the collector/presenter boundary before changing loading behavior.
5. **Lifecycle.** Return the actual lifecycle completion rule used by shared Progress (closed-container contribution and terminal member statuses) with profile-aware names. Keep literal criteria/task completion distinct. Add one row per active/implementing/paused container with ID, status, done/deferred/open/total criteria and tasks, and missing/unreadable coverage. Derive membership from admitted identity, use the shared checklist collector and configured record roots, and never infer done checkboxes from status. Return all selected rows in stable ID order; the skill may summarize with an explicit omitted count. No dashboard calculation change or new gate.
6. **Context accounting.** Expose existing source/workflow/artifact credit, recorded request/response debit, net estimate and paired-evaluation count beside the total. Label request/response values as recorded accounting estimates, not total model consumption, reasoning tokens or billing. Keep the default payload and presentation aggregate-only for contributing per-wave detail: retain aggregate credits, debits, estimates, stage totals, coverage counts, paired-evaluation count and existing excluded-record diagnostics. Add `include_wave_details=false` to the shared collector/MCP call and `--include-wave-details` to the CLI. Only an explicit opt-in returns per-wave healthy checkpoint rows and excluded/missing/pending status with the same aggregation policy as today; healthy rows reconcile exactly to aggregate and stages. With token_savings unrequested, the option must not cause checkpoint reads. The skill requests these rows only for a per-wave question, not to build its default summary. At zero paired evaluations, the formatter and skill must place “No paired evaluations recorded” beside the estimate. Do not change checkpoint formulas, invent paired evidence, or read live telemetry as a substitute for published checkpoints.
7. **Delivery and cost.** Keep existing JSON fields and meanings; new fields are additive. MCP and CLI share one payload; requested sections remain lazy, and code/TODO share one file pass. Update the `wf-stats` registry guidance and rendered skills to display new qualifiers and bounded examples without recounting. Preserve optional index costs and read-only boundaries. Configuration, parser or source failure in one section must not hide other sections. Default and renamed-profile fixtures must cover labels and configured roots. No network, models, subprocess, scan, build, memory mutation or lifecycle mutation from stats.

## Scope

**In scope:** `project_stats.py`, optional walker diagnostics in `indexer.py`; scanner observation producers/readers (`scan_secrets.py`, `run_secrets_scan.py`, `scanner_skips.py`, `wave_lint_lib/secrets_validators.py`); shared lifecycle collector only for reusable explanation/coverage; skill registry/rendered skills; MCP/CLI descriptions, statistics spec, focused tests and changelog. The scan summary is observational and does not change rule evaluation, exclusions or gate decisions.

**Out of scope:** new scanner rules, automatic rescans/setup, changing acceptance, new memory lifecycle states, provider billing integration, new dashboard panels, broad telemetry redesign, source-role classification, automatic project configuration, implementation of downstream Tensorwell changes. Protect unrelated build stamps, all Envision guidance and other lifecycle prompts.

## Acceptance Criteria

- [x] AC-1: A real walker fixture with an eligible small file, an oversized file, a binary candidate, an ignored/pruned subtree, lifecycle evidence directories under default/renamed roots, and denied file/directory produces exact observed reason counts, bounded paths and omitted counts through MCP/CLI; eligible unreadability stays incomplete. The original implementation cannot satisfy the size-path and reason breakdown assertions. Excluded evidence-directory counts describe directories only, with no traversal or invented descendant counts. Existing index eligibility and unrelated stats sections are unchanged.
- [x] AC-2: Real scanner publication/readback controls cover full complete, full incomplete, later per-edit incremental secret scanning, no-work lint, rule change, fresh-clone absence and missing/malformed history and publication failure through the relevant producer paths. Stats preserves last-full scope separately from latest run, reports outstanding failures and allowlist-entry counts, never treats unknown as clean, and performs no scan or write. Per-edit incremental scanning updates latest scan only, no-work lint updates neither timestamp, and output labels the observations machine-local. Secret-shaped fixture content and finding paths are absent from the returned health metadata.
- [x] AC-3: A record fixture containing active, candidate, rejected and archived memories is represented in the public payload and both presentation routes with exact counts; archive bodies count once. An unwritten proposal does not count as a candidate record. A missing candidate in presentation fails the oracle even if the payload is right.
- [x] AC-4: Active and paused containers under default and renamed roots report exact checklist rows and coverage, with actual status-completion rules; terminal member statuses do not mark unchecked criteria done. Historical short member metadata cannot duplicate or misassign membership. Missing and unreadable admitted docs remain visible.
- [x] AC-5: Known healthy, unhealthy, missing and pending checkpoint fixtures reconcile opted-in per-wave, per-stage and total credit/debit/estimate fields. Default MCP/CLI reports omit contributing per-wave rows, and explicit detail requests produce equivalent rows on both routes. A fixture with hundreds of healthy checkpoints verifies that default output does not grow by a row per checkpoint; existing excluded-record diagnostics remain compatible. The detail option performs no checkpoint work when token_savings is unrequested. Zero paired evidence is prominently labelled in CLI and skill guidance; the output does not claim measured savings or total token consumption. Existing aggregation is unchanged.
- [x] AC-6: Public MCP/CLI tests show additive compatibility, selected-section laziness, unchanged read-only behavior and failure isolation; new documents validate. The original formatter/collector fails at least one decisive assertion for each new behavior. Native Windows execution is reported only if actually exercised.

## Tasks

- [x] Ground skip and scan producer ownership; implement bounded observation/readback with tests.
- [x] Add lifecycle/per-wave accounting and memory-status presentation using existing collectors.
- [x] Update MCP/CLI contracts, skill registry/rendered skills, spec and architecture notes.
- [x] Run focused default/renamed-profile controls, relevant full qualification, required reviews and record limits.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Statistics and scan observations | implementer | — | Own shared report and producer changes serially |
| Verification | independent reviewers | implementation | Required lanes inspect actual public boundaries |

## Serialization Points

- `.wavefoundry/framework/scripts/project_stats.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/scanner_skips.py`, `.wavefoundry/framework/scripts/scan_secrets.py`, `.wavefoundry/framework/scripts/run_secrets_scan.py`, `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wf_cli.py`, `.wavefoundry/framework/scripts/tests/`, `docs/specs/mcp-tool-surface.md`

Finish this change's shared payload contracts before 231kg edits the same files. Reviewers are read-only; only the implementer writes source. Generated skills render from their registry; no new backing prompt or public command.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` for scanner observation ownership and statistics reads, `docs/architecture/performance-budget.md` for bounded reporting, and `docs/references/dashboard-adapter-model.md` for shared lifecycle explanations.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Names missing evidence rather than presenting incomplete counts as exhaustive |
| AC-2 | required | Separates historical scan, present failures and unknown coverage |
| AC-3 | required | Makes validation work visible without mixing populations |
| AC-4 | required | Shows where open work resides with shared semantics |
| AC-5 | required | Makes the estimate inspectable without overstating evidence |
| AC-6 | required | Preserves public compatibility and read-only isolation |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-11 | Observe: implementation and independent delivery review complete; all ACs/tasks satisfied. Final reviewed-tree canonical suite passes 12,814 tests across 248 files, 12 reported skips, 863.764 seconds. | Current successful framework receipt; six required lane approvals and council establishes. One CLI path-display finding repaired and reverified. No native Windows/live downstream/human comprehension claim. |
| 2026-11-11 | Observe: all integration corrections verified before requalification. Scanner identity reads and pre-scan capture share the retained indexer scanner runtime; reload guard unchanged. Profile census passes. 47 combined history/reload/census/audit tests plus unavailable-runtime control pass. Source frozen again. | `test_lifecycle_gates_structure`, `test_profile_literal_census`, `test_stats_scan_observations`, `CheckoutAuditDispatchTests`; no standalone scanner import bypass or weakened read-only assertion. Full canonical rerun next. |
| 2026-11-11 | Observe: audit containment repair passes all 33 prefix-collapse/history tests. Only test/audit helper files changed: new history writes serialize into scratch under the existing no-repository-writes context; original whole-checkout byte assertion stays unchanged. Actual publish=False leaves no files. | `CheckoutAuditDispatchTests` and `test_stats_scan_observations`; mutants omitting history redirection and deleting publish=False guard both fail. Product scanner behavior unchanged by this repair; full qualification rerun pending. |
| 2026-11-11 | Observe: reopened AC-2/AC-6 while canonical integration failures are repaired. Production publish=False already prevents history writes; the explicit checkout-audit helper runs real serialization with writers redirected and omitted the new writer. Extend its containment seam and retain unchanged whole-tree byte comparison. | `CheckoutAuditDispatchTests`; current producer diagnosis, not a waiver or test deletion. |
| 2026-11-11 | Observe: 8 new producer tests, 109 scanner/walker regressions, 171 validator tests and 31 report/public stats tests pass. Real caller controls cover explicit full scan, indexer incremental and executed per-edit docs lint; no-work/read-only timestamps stay unchanged. Atomic failure preserves old history. AC-1–5 complete; full qualification and delivery review remain. | `test_stats_scan_observations` and `test_stats_explainability`; `test_stats_surfaces` MCP/CLI parity. Mutants removing the ten-example cap and last-full retention are rejected by `test_real_walk_observes_bounded_exclusions_without_entering_evidence` and `test_full_then_incremental_then_no_work_preserves_distinct_times`. No native Windows or field result claimed. |
| 2026-11-11 | Observe: shared report contracts implemented; existing 24 stats tests and six new explainability tests pass. Producer APIs stable with seven new walker/history tests and 12 existing completion tests passing; remaining focused regression/mutants continue. Begin dependent 231kg after common payload contracts settle, while producer-only tests finish. | Real checkpoint/detail parity, 350-record default, active/paused literal marks, memory populations, malformed findings retaining history; scanner full/incremental/no-work/failure and bounded walker controls. No future delivery approval claimed. |
| 2026-11-11 | Readback: make omitted files, historical scan observations, candidate memories, active/paused checklist work and estimated context accounting explainable without scans or writes from stats. For example, an incremental scan will preserve a separately dated last-full observation; default token reports remain aggregates until detail is requested. Scanner/walker producers and shared stats/API consumers are disjoint implementation lanes; 231kg follows integration. | AC-1–6; project_stats, indexer walker, scanner owners, MCP/CLI, registry, docs and focused tests. No eligibility, gate, billing or dashboard formula change. |
| 2026-11-11 | Updated requirements and ACs following operator-approved plan review; no implementation. | Policy exclusions, explicit token-detail option, per-edit scan/no-work controls and machine-local history. Focused readiness refresh pending. |
| 2026-11-11 | Planning only. Direct MCP source reads confirm collector ownership. Executed mocked memory-record control returned active=1, candidate=1, rejected=1; no evidence yet that the loader caused Tensorwell's presentation gap. | `project_stats._memories`, `memory_records.load_memory_records`; scanner state and skip readers |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-11 | Operator accepted policy-excluded evidence, opt-in per-wave token detail and execution-only per-edit scan observations. | Avoid widening the walk, oversized default reports and false scan timestamps. History is explicitly machine-local. Requirements and ACs are amended; prior readiness needs focused refresh. | Counting pruned files, returning all token rows by default, or counting no-work lint as a scan. |
| 2026-11-11 | Extend existing collectors and producer-owned observations, then format them. | Replay: omitted benchmark files become named coverage exclusions; incomplete scanner work stays visible; record statuses and per-wave accounting explain totals. This advises operators, not a new gate. ACs test exact counts and unknown states; the next field run checks whether operators can locate unresolved work. | Presentation-only cannot recover missing skip/full-run history. A new audit/scanning command would add cost and mutate state during a report. |
| 2026-11-11 | Keep candidate records separate from unpersisted proposals and accounting separate from billing. | Those are different populations and measurements; summing them would make the report less truthful. | Inventing reconciliation or calling estimates actual consumption hides uncertainty. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Latest incremental observation masquerades as full/current coverage | Separate latest/last-full/current-outstanding fields; legacy unknown and rules identity controls |
| Diagnostic paths leak secret finding content | Only contained coverage paths and fixed reason codes; no finding paths, matches or arbitrary error text |
| Extra report detail becomes expensive or overwhelming | Reuse collected data, section laziness and bounded path examples; skill summarizes long rows explicitly |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
