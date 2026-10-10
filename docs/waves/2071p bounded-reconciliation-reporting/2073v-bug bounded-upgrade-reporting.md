# Give upgrade reporting one bounded failure-aware path

Change ID: `2073v-bug bounded-upgrade-reporting`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-09
Wave: 2071p bounded-reconciliation-reporting

## Rationale

When delegated summary fails or times out, _emit_primary_summary_via_delegate_or_fallback invokes an in-process fallback that scans again without a deadline. The finite upstream boundary probe confirms that re-entry; _run_reconciliation_scan converts an injected exception to three empty channels. Cleanup reporting also invokes this scanner synchronously after publication and before verified-pack deletion. Thus optional reporting can obscure completed installation or block final cleanup. The exact downstream 300-second trigger remains unisolated.

The operator requested Plan, Prepare and Review only. No implementation, activation, closure, commit, push or package build is authorized by this request.

## Requirements

1. Use one monotonic reporting-work budget of 30 seconds across child startup, scanning and recovery inside the new producer/current reporting path; propagate remaining time rather than allocating fresh stage budgets. Preserve the pinned delegated parent timeout constant (300 seconds) and old argv contract. The producer's own budget ends work inside that compatible envelope; a current parent may enforce a shorter remaining work budget through an optional, backward-compatible input without changing the pinned default. Isolate potentially blocking scanning in an owned child with run_with_tree_kill (or the existing equivalent) so a stalled read/parser cannot defeat that enforced deadline. Inject a smaller budget for tests.

2. On delegate timeout/error/protocol failure, emit one bounded fallback from already observed parent facts and any valid already-returned scan result; do not invoke another scanner or unrelated expensive renderer/diagnostic pass. The new child independently honors a bounded budget when called by an older parent that cannot pass remaining time. A bounded timeout is not a guarantee the whole upgrade fits an external MCP deadline.

3. Keep installation/adoption/index-publication outcome separate from reconciliation reporting state. Successful work with incomplete, timed-out or failed reconciliation remains successful with an explicit reporting warning; errors must not become a clean empty finding set. Complete and partial findings keep their established three channels and provenance.

4. Preserve old-parent/new-child sentinel recognition, accepted schemas and exactly-one-summary behavior. Keep the existing compact degraded marker and parent-derived fact preservation; carry incomplete/error details in protocol-compatible fields or an additive shape only after cross-version tests prove acceptance. Do not invent a new required schema or parent expectation. Keep the producer import stdlib-only under an older runner's tool venv, and use flat compact fields that survive the old server's bounded summary parser.

5. Cleanup's optional summary must consume the same bounded reporting path. Attempt owned temporary and verified-pack cleanup regardless of report success, without deleting unverified/operator-owned packs or losing recovery state. A reporting failure must neither fabricate adoption/index success nor roll back verified successful publication.

6. Retain bounded diagnostic metadata (last input path/stage, elapsed time/counts and failure class) without source contents. Exercise resume, memory/index authorization and old-code seams around the modified path; do not alter publication, consent or lock ownership.

## Scope

**Problem statement:** Give upgrade reporting one bounded failure-aware path to repair the confirmed behavior described above.

**In scope:**

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/reconcile_scan.py (shared result contract only)`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `docs/architecture/data-and-control-flow.md`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/decisions/1u49j-adr fresh-code-summary-producer-contract.md`

**Out of scope:** Promise of total upgrade runtime below MCP limits, changing installation/publication success rules, new summary protocol, downstream execution, causal-file attribution, and implementation during this request.

## Acceptance Criteria

- [x] AC-1: Success, scan error, delegate error, malformed payload and timeout each return within one injected end-to-end reporting bound, emit exactly one compatible primary summary and perform no second scan after delegate failure. Oracle: real stub children plus actual emitters and call-count controls.
- [x] AC-2: Failed/partial/timeout scans are explicitly incomplete while successful installation and index facts remain accurate; valid complete scan findings retain their channels. Oracle: current and old-parent/new-child summary fixtures, sentinel parsers and contradictory parent/child fact controls.
- [x] AC-3: Cleanup cannot be indefinitely blocked by reporting and still attempts eligible owned-resource cleanup, preserving recovery and verified publication state. Oracle: actual cleanup/report boundary fixtures with stalled reporting and owned/unowned pack controls.
- [x] AC-4: Existing summary degradation, schema-divergence, resume, memory/index authorization and phase-transition contracts remain valid. Oracle: existing seam clusters plus controls restoring the unbounded fallback or exception-to-empty behavior.

## Tasks

- [x] Add served-path or scanner regression coverage reproducing the confirmed defects with realistic adjacent controls.
- [x] Implement only the admitted requirements and preserve the stated compatibility boundaries.
- [x] Run affected tests and selected known-bad controls; record actual AC evidence as each completes.
- [x] Complete independent delivery review and applicable framework qualification before proposing closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Repair | implementer | Current typed readiness and implementation authorization | Single writer for shared modules |
| Verification | required reviewer lanes | Frozen implementation | Fresh independent contexts |
| Integration | wave-coordinator | Verified repair | Reconcile scope, ACs and full qualification |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/reconcile_scan.py (shared result contract only)`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `docs/architecture/data-and-control-flow.md`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/decisions/1u49j-adr fresh-code-summary-producer-contract.md`

## Affected Architecture Docs

docs/architecture/data-and-control-flow.md; docs/contributing/build-and-verification.md (operator reporting/qualification only). The accepted fresh-code summary ADR pins producer argv/schema/sentinel and the outer 300-second timeout.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Success, scan error, delegate error, malformed payload and timeout each return within one injected end-to-end reporting bound, emit exactly one compatible primary summary and perform no second scan after delegate failure |
| AC-2 | required | Failed/partial/timeout scans are explicitly incomplete while successful installation and index facts remain accurate; valid complete scan findings retain their channels |
| AC-3 | required | Cleanup cannot be indefinitely blocked by reporting and still attempts eligible owned-resource cleanup, preserving recovery and verified publication state |
| AC-4 | required | Existing summary degradation, schema-divergence, resume, memory/index authorization and phase-transition contracts remain valid |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Implemented and all tasks complete. Final quiet host-capable canonical12057tests/178files/13skips green in669.258s, fresh matching framework receipt. All seven delivery lanes current; both cycle1 findings independently terminal. | wave.md final qualification; framework/test-cache.json resultok/inputs_hash |
| 2026-10-09 | All seven required delivery lanes approved; cycle1 performance/false-description repairs independently cleared. Fresh QA125/no skips/3mutants; code55, performance6plus7controls, docs8controls. Eight ACs checked; final canonical suite remains root-owned pending. | Typed events and wave.md compact final synthesis; canonical regression test IDs |
| 2026-10-09 | AC1–4 proved by fresh bounded scanner/reporting/compatibility/cleanup tests and selected independent initial lanes. Cycle1 deterministic persistence/context controls and broader reporting/process tests67green; root paired performance exact findings unchanged and two documentary diagnostics green. All eight ACs checked; final review and canonical qualification still pending. | BoundedReconciliationTests; BoundedUpgradeReportingTests; DelegatedSummaryContractTests; DelegatedSummaryDegradationTests; wave.md delivery synthesis |
| 2026-10-09 | Readback: implement AC1–4 in upgrade_wavefoundry.py/test_upgrade_wavefoundry.py after the shared scanner result boundary. Enforce one30s reporting-work budget with remaining time and owned-child termination; keep300s pinned default/old argv/schema/sentinel/std lib imports. Before: failed delegate rescans synchronously and scan errors look empty; after: one bounded facts-only warning preserves actual installation/publication facts and owned cleanup. No whole-upgrade deadline promise or old-parent fallback repair. | Current operator instruction implement this wave; successful wf_implement_wave create; baseline-source-packet.json |
| 2026-10-09 | Implementation frozen; framework edit gate closed. Scanner/reporting/cleanup source is implemented, including verified pack identity proof. Focused 158, authorization/resume 34 and adjacent 79 tests green; five semantic guard mutants killed. Canonical full qualification and seven independent delivery lanes running; no closure/Git/package authorization. | evidence/implementation/frozen-source-packet.json; wf2071p-focused.log; wf2071p-memory-seams.log; wf2071p-adjacent.log; wf2071p-mutants.log |
| 2026-10-09 | Builder checkpoint: pre-fix scanner forbidden-descent/structured-limit and reporting fallback-reentry/exception-to-empty regressions failed; initial scanner pass69 tests, one rollback-near-miss corrected pending rerun. Structured scanner and owned report child implemented but not frozen/qualified. | Independent worker checkpoint; exact durable test results follow at freeze |
| 2026-10-09 | Plan only. Current defect mechanisms exercised by the finite upstream scratch probe; no repaired behavior claimed. Downstream cost measurements are attributed, with upstream identity verification only for the named profile. | Wave baseline captures; updated Tensorwell diagnostic report |
| 2026-10-09 | Optional Review plan resolves contract branches from source and accepted summary ADR: stored provenance, nullable unproven snippets, compatible singular fields; bounded scope/work and reporting state; preserve producer protocol. No unresolved operator choice or implementation authorization inferred. | Requirements and Decision Log |

- 2026-10-09 — Integration readback: register the new owned reporting worker in the existing timed-process census (`tests/test_tree_kill_routing.py`, one ROUTED row). This required qualification change verifies AC-1 process-tree timeout routing and does not alter production behavior or expand technical scope. Baseline archived before edit.

- 2026-10-09 — Cycle1 repair readback: all seven initial delivery lanes collected; PERF-2071P-01 and the deduplicated two false docstrings recorded, then repair_start recorded before mutation. Root changes only durable progress persistence to file/stage boundaries or100ms intervals, preserves cooperative checkpoints, skips context when no findings, corrects two descriptions and adds deterministic persistence/context controls. Initial quiet sandbox qualification completed178files but failed local socket/process/home-cache fixtures; final qualification uses required host capabilities with no waiver.

## Decision Log

| Date | Decision | Reason and alternatives |
| --- | --- | --- |
| 2026-10-09 | Divergent pre-plan choice | Selected one owned bounded reporting path and a facts-only recovery summary. Rejected merely shrinking the delegated timeout: fallback still scans without bounds. Rejected treating report failure as installation failure or redesigning the whole upgrade protocol: contradicts observed successful publication and expands scope. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A small historical reproducer misses a related supported input | Use the derived contract classes and adjacent controls in ACs, not only the reported line/path |
| Bounds or missing evidence appear as successful absence | Preserve explicit unknown/incomplete states and make negative controls non-vacuous |
| A compatibility repair widens into unrelated redesign | Keep scope explicit; return material contradictions to planning |

## Session Handoff

Implemented in this closed wave; final qualification, review outcomes, retained evidence and limits are recorded in wave.md.
