# Bound reconciliation traversal, reads and matching

Change ID: `2073u-bug bounded-reconciliation-scan`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-09
Wave: 2071p bounded-reconciliation-reporting

## Rationale

The scanner currently traverses excluded trees with root.rglob, reads and retains entire eligible files and repeatedly matches whole text. Tensorwell's metadata census found about 1.34 GB of eligible .local data. Upstream scratch scope confirms .local and target are eligible while .claude/settings.json remains intentionally live. The current prompt-path pattern shows approximately fourfold time growth when anchor-free 'a/' input doubles. These are confirmed mechanisms; the exact file causing Tensorwell's complete timeout remains unknown. Tensorwell's follow-up identifies a 31,681,348-byte ONNX profile (SHA-256 13f74e12464ba615c3072d342c2fc5ee1f2cfe3a9011c08724b4a1242abe1e0a) taking 10.480564 seconds with zero findings. The instrumented normal-scope sample exhausted 120 seconds after 737 files; the aggregate control filtering root .local/target completed 186 files in 8.414389 seconds. Instrumentation and corpus differences prevent a directly comparable speedup claim; these support cumulative generated-file cost, not attribution of the historical active file.

The operator requested Plan, Prepare and Review only. No implementation, activation, closure, commit, push or package build is authorized by this request.

## Requirements

1. Prune established excluded directory components before descent, including repository-root generated .local and Rust target trees. Preserve current component-aware near-miss behavior, configured lifecycle/history exclusions, and intentionally live host permission/config surfaces. Do not adopt blanket Git-ignore/hidden-directory filtering or apply the extension-based file predicate to directory descent.

2. Use contained_files for bounded, contained regular-file reads; do not follow links or open special files. Introduce named internal defaults for entry, file and byte limits and a cooperative monotonic scan deadline: 100,000 visited entries, 10,000 eligible files, 16 MiB per file, 128 MiB total read, 100,000 candidates, 10,000 findings, and 30 seconds. The first exhausted bound ends or skips work with explicit incompleteness; limits may be injected in tests without adding an operator configuration surface.

3. Use literal-anchor candidate extraction and bounded token parsing for prompt references instead of restart-at-every-character matching. Bound every other user-content pattern pass by the admitted file/candidate/work limits. Contextualize each file's findings before discarding its text; do not retain the whole corpus. Preserve valid relative references, punctuation, correct .prompt.md exclusion, twin-file guards and existing Markdown fence/disposition semantics.

4. Offer a structured bounded scan result carrying the three existing finding channels, complete/incomplete/error state, reasons, visited/eligible/read counts and bytes. Keep existing public list/tuple API shapes through compatible wrappers; wrappers must never disguise partial/error execution as a clean empty scan. Reporting consumers in the companion change consume the structured result.

5. Record bounded progress at file/pattern boundaries (relative path, stage, elapsed time and counts only), including the last attempted input for timeout diagnosis. Never retain file contents or secrets in progress output. Excluded generated/history material is intentional scope; a cap, read refusal or error in eligible scope is explicit incompleteness.

## Scope

**Problem statement:** Bound reconciliation traversal, reads and matching to repair the confirmed behavior described above.

**In scope:**

- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/performance-budget.md`

**Out of scope:** Identifying the full downstream causal file, scanning all Tensorwell data, Git-ignore semantics, indexer tuning, general regex-engine replacement, configuration-schema expansion, and implementation during this request.

## Acceptance Criteria

- [x] AC-1: Excluded components are never descended into, while intentional host surfaces, current docs and similarly named legitimate directories are inspected. Oracle: instrumented scratch traversal with forbidden-descent and required-live controls. Include root-only generated exclusions and live nested/near-miss directory controls; record the named Tensorwell profile as an optional, hash-verified external cost reproducer rather than checking its content into fixtures.
- [x] AC-2: File/total-byte, entry/file-count and elapsed-work bounds prevent unbounded corpus retention or processing and report all eligible-scope omissions truthfully. Oracle: injected small limits, huge/junk files, refused links/special files and a multi-file fixture; no full Tensorwell scan is required.
- [x] AC-3: Anchor-free and candidate-dense adversarial prompt text completes within the bounded workload and valid reference/disposition/fence/channel semantics remain intact. Oracle: controlled scaling and exact fixture findings; timing alone cannot establish semantic correctness.
- [x] AC-4: Legacy consumer shapes remain compatible, while partial/error work cannot be reported as complete with zero findings. Oracle: actual legacy wrappers and structured-result consumers with complete, incomplete and failure controls.

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

- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/performance-budget.md`

## Affected Architecture Docs

docs/architecture/data-and-control-flow.md; docs/architecture/performance-budget.md. Verify applicable sections during implementation rather than altering unrelated contracts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Excluded components are never descended into, while intentional host surfaces, current docs and similarly named legitimate directories are inspected |
| AC-2 | required | File/total-byte, entry/file-count and elapsed-work bounds prevent unbounded corpus retention or processing and report all eligible-scope omissions truthfully |
| AC-3 | required | Anchor-free and candidate-dense adversarial prompt text completes within the bounded workload and valid reference/disposition/fence/channel semantics remain intact |
| AC-4 | required | Legacy consumer shapes remain compatible, while partial/error work cannot be reported as complete with zero findings |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Implemented and all tasks complete. Final quiet host-capable canonical12057tests/178files/13skips green in669.258s, fresh matching framework receipt. All seven delivery lanes current; both cycle1 findings independently terminal. | wave.md final qualification; framework/test-cache.json resultok/inputs_hash |
| 2026-10-09 | All seven required delivery lanes approved; cycle1 performance/false-description repairs independently cleared. Fresh QA125/no skips/3mutants; code55, performance6plus7controls, docs8controls. Eight ACs checked; final canonical suite remains root-owned pending. | Typed events and wave.md compact final synthesis; canonical regression test IDs |
| 2026-10-09 | AC1–4 proved by fresh bounded scanner/reporting/compatibility/cleanup tests and selected independent initial lanes. Cycle1 deterministic persistence/context controls and broader reporting/process tests67green; root paired performance exact findings unchanged and two documentary diagnostics green. All eight ACs checked; final review and canonical qualification still pending. | BoundedReconciliationTests; BoundedUpgradeReportingTests; DelegatedSummaryContractTests; DelegatedSummaryDegradationTests; wave.md delivery synthesis |
| 2026-10-09 | Readback: implement AC1–4 in reconcile_scan.py/test_reconcile_scan.py: prune root .local/target and existing excluded components before descent; retain nested/near-miss and ignored host files. Bound contained regular no-follow reads, all work/results and per-file retention; preserve three channels/fences/dispositions and truthful legacy shapes. Before: a generated31MB profile is read and matching can grow quadratically; after: that root tree is never visited and eligible omissions report incomplete. No Gitignore integration, artifact deletion or external scan. | Current operator instruction implement this wave; successful wf_implement_wave create; baseline-source-packet.json |
| 2026-10-09 | Implementation frozen; framework edit gate closed. Scanner/reporting/cleanup source is implemented, including verified pack identity proof. Focused 158, authorization/resume 34 and adjacent 79 tests green; five semantic guard mutants killed. Canonical full qualification and seven independent delivery lanes running; no closure/Git/package authorization. | evidence/implementation/frozen-source-packet.json; wf2071p-focused.log; wf2071p-memory-seams.log; wf2071p-adjacent.log; wf2071p-mutants.log |
| 2026-10-09 | Builder checkpoint: pre-fix scanner forbidden-descent/structured-limit and reporting fallback-reentry/exception-to-empty regressions failed; initial scanner pass69 tests, one rollback-near-miss corrected pending rerun. Structured scanner and owned report child implemented but not frozen/qualified. | Independent worker checkpoint; exact durable test results follow at freeze |
| 2026-10-09 | Plan only. Current defect mechanisms exercised by the finite upstream scratch probe; no repaired behavior claimed. Downstream cost measurements are attributed, with upstream identity verification only for the named profile. | Wave baseline captures; updated Tensorwell diagnostic report |
| 2026-10-09 | Optional Review plan resolves contract branches from source and accepted summary ADR: stored provenance, nullable unproven snippets, compatible singular fields; bounded scope/work and reporting state; preserve producer protocol. No unresolved operator choice or implementation authorization inferred. | Requirements and Decision Log |

- 2026-10-09 — Cycle1 repair readback: all seven initial delivery lanes collected; PERF-2071P-01 and the deduplicated two false docstrings recorded, then repair_start recorded before mutation. Root changes only durable progress persistence to file/stage boundaries or100ms intervals, preserves cooperative checkpoints, skips context when no findings, corrects two descriptions and adds deterministic persistence/context controls. Initial quiet sandbox qualification completed178files but failed local socket/process/home-cache fixtures; final qualification uses required host capabilities with no waiver.

## Decision Log

| Date | Decision | Reason and alternatives |
| --- | --- | --- |
| 2026-10-09 | Divergent pre-plan choice | Selected pruned traversal, finite work/read bounds, per-file retention and an explicit result state. Rejected only excluding .local/target plus an anchor precheck: leaves other oversized inputs and reporting failures unbounded. Rejected a Git-tracked-only semantic scanner: hides legitimate host surfaces and changes reconciliation's contract. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A small historical reproducer misses a related supported input | Use the derived contract classes and adjacent controls in ACs, not only the reported line/path |
| Bounds or missing evidence appear as successful absence | Preserve explicit unknown/incomplete states and make negative controls non-vacuous |
| A compatibility repair widens into unrelated redesign | Keep scope explicit; return material contradictions to planning |

## Session Handoff

Implemented in this closed wave; final qualification, review outcomes, retained evidence and limits are recorded in wave.md.
