# Accept unordered ownership inputs and predict fresh-repository lint fallback

Change ID: `20d8z-bug distribution-test-and-lint-seams`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-10-11
Wave: 20d92 distribution-test-and-lint-seams

## Rationale

Keep distribution ownership validation order-independent while preserving explicit inventory authority, and make changed-doc lint timeout prediction match real CLI triggers in a fresh repository. Scratch controls show unique unordered paths are refused by `framework_text_ownership.load_inventory`, and default Git status collapses a new docs directory while `--untracked-files=all` names its trigger file.

## Product Intent

Framework maintainers and distributions should receive deterministic ownership loads and appropriate lint bounds for real changed files. Governing context: `docs/contributing/build-and-verification.md` and `docs/specs/mcp-tool-surface.md`. The optional bytecode census seam is deliberately excluded pending demonstrated need and a bounded reviewed design.

Design Intent: N/A — no UI surface changes.

## Requirements

1. `framework_text_ownership.load_inventory` accepts unique valid relative paths in any input order and returns their deterministic sorted tuple. Continue rejecting duplicates and invalid paths; sorting must not silently deduplicate invalid input or enlarge the shipped ownership set.
2. `wf_server.server_impl._predict_incremental_full_fallback` invokes Git status with `--untracked-files=all` so nested untracked trigger files are visible, including in a no-commit repository. Preserve tracked/rename parsing and existing Git-failure behavior; compare prediction with the actual CLI changed-set/full-fallback trigger path.
3. Update focused distribution and post-write lint regressions rather than broadening scan ownership or making the ordinary test suite discover arbitrary checkout files.
4. No declarable bytecode exemption is admitted in this change. A later proposal would require demonstrated need, explicit bounded relative names/reasons limited to distribution-owned modules, refusal of upstream shipped-inventory exemptions, and unchanged upstream entry/library checks; no blanket bypass is authorized.

## Scope

In scope: the source symbols named in Requirements and Discovery evidence, their tests listed below, directly necessary contained-helper edits, and the named architecture/build guidance.

Out of scope: new receipt gates, general frameworks, release packaging, index rebuilds, unrelated host hooks/prompts, history rewriting, commits and wave closure. Optional bytecode exemptions are not admitted.

## Acceptance Criteria

- [x] AC-1: Unique valid inventories in distinct input orders load to the same sorted tuple; duplicate, escaping, absolute and non-string invalid controls still refuse without changing the shipped ownership set. The existing loader fails the unordered-positive case.
- [x] AC-2: In an actual fresh no-commit Git repository, nested untracked fallback-trigger files cause prediction to match the actual CLI full-fallback decision; unrelated untracked files predict false. The default-status implementation fails the trigger-positive control.
- [x] AC-3: Tracked edits, supported rename parsing and unavailable/failed Git retain their existing outcomes and timeout selection; focused post-write lint tests verify the complete prediction-to-bound path.
- [x] AC-4: This change's focused suites and added tests pass, its authored/edited docs validate, and no failure elsewhere is attributable to this change; its source edit does not alter retrieval results or bypass ownership/bytecode checks.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Order-independent ownership. |
| AC-2 | required | Actual trigger parity. |
| AC-3 | required | Compatibility. |
| AC-4 | required | Scoped verification. |

## Tasks

- [x] Split unordered-positive from duplicate/invalid ownership tests; implement validation then deterministic sorting.
- [x] Add a fresh no-commit real-Git trigger fixture and CLI/prediction parity assertion; add --untracked-files=all.
- [x] Run focused distribution and advisory-lint/post-write suites, preserve existing ownership controls and review timeout selection.
- [x] Update test seam documentation and verify retrieval-module identity obligations before touching server_impl.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Reproduction and minimal repair | implementer | Readiness and activation | Python stdlib, contained I/O, regression controls; one write owner. |
| Documentation reconciliation | implementer | Repair behavior stable | Named docs only; no new report/evidence folder. |
| Independent delivery review | code-reviewer, qa-reviewer, architecture-reviewer | Current implementation | Read-only; Council synthesizes; coordinator owns state. |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/framework_text_ownership.py`
- `.wavefoundry/framework/scripts/tests/test_distribution_seams.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_advisory_lint_reuse.py`
- `docs/architecture/testing-architecture.md`
- `docs/contributing/build-and-verification.md`

The implementer exclusively owns listed source/test/doc edits during activation; review lanes remain read-only. Protected: canonical seeds, generated agent/platform surfaces, root AGENTS.md, workflow/repo-profile config, qualification/test receipts, shipped ownership fixture, Git and history. No protected-surface edit is planned; directly necessary helper or fixture changes require coordinator scope check. Other waves touching shared modules must finish/pause before activation; never edit another wave's artifacts.

## Affected architecture docs

- `docs/architecture/testing-architecture.md`: reconcile only this change's boundary or verification contract.

No new ADR or architecture restructuring is planned.

## Knowledge Transfer Plan

Record focused regression names, fix-absent outcomes and material limits in this change's Progress Log and wave.md. Preserve custom-prose/newline and real-producer fixture cautions from project memory; a guard is complete only when its absence is detected. Keep scratch captures outside the repository; no permanent evidence folder.

## Persona Review Plan

Use the material specialist lanes declared by wave.md; framework-operator concerns are incorporated into their refusal/retry review rather than a separate blanket persona pass. Product-owner and additional persona/factor lanes are requested only when Prepare policy derives them or a material scope finding justifies them. Existing policy-derived lanes and Council authority remain binding.

## Wave Readiness Plan

Coordinator performs docs validation, independent required specialist lanes and Council readiness, then final ready-only Prepare. Implementation requires clean typed readiness and later single-OPEN activation. Operator authorized preparation/review/implementation; this planner owns docs only. Existing open wave remains open until its coordinator pauses it.

## Watchpoints

Use generic fixtures and source anchors only. Report changed assumptions before implementation. Partial failure and skipped safety refusals stay visible. Reuse current matching evidence; never mint receipts manually or copy raw transcripts into docs.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-11 | Planning discovery completed; implementation pending. | executed: unique unordered scratch inventory raised ValueError; real no-commit Git status returned a directory while --untracked-files=all returned the nested trigger. source-inspected: `load_inventory`, `test_inventory_rejects_duplicate_unsorted_or_escaping_paths`, `_predict_incremental_full_fallback`, `wave_lint_lib.secrets_validators._get_changed_files`. Full predictor/CLI parity is an implementation oracle, not yet established. Bytecode `census_problems` and `PINNED_SOURCE_ENTRIES` were read; no justified additional exempt module was identified. |
| 2026-10-11 | Activated after the preceding five waves were delivered and paused. Coordinator readback: validate uniqueness and relative names before deterministic sorting; expose every untracked trigger to the existing predictor without changing failure behavior or lint bounds. | Existing typed readiness consumed. Production server edits are held until the actual private-checkout retrieval baseline completes; then one writer owns the seven listed paths. No exemption, closure, commit or new pack is admitted. |
| 2026-10-11 | Inventory sorting and the explicit Git expansion flag are implemented; seven listed source/test/guidance paths frozen. | Actual pre-change retrieval baseline passed 35 fixtures in an isolated current checkout before edits. Thirteen focused tests passed with no skips; real no-commit Git reaches collector, CLI scope and timeout dispatch. Faithful no-sort, no-duplicate-guard and no-Git-flag controls fail the intended assertions. Three-file focused qualification and after-change retrieval remain pending. |
| 2026-10-11 | Compatibility and complete lint dispatch verified; candidate source remains frozen and framework gate is closed. | All 446 tests across distribution, advisory-lint and server-tool workers passed with zero skips. The focused runner exited 1 only because coordinator checkbox bookkeeping changed the watched wave doc; this diagnostic supplies no green receipt. The upcoming quiet isolated canonical run supplies whole-suite authority. No source assertions, timeout budgets or shipped inventories were weakened. |
| 2026-10-11 | Actual before/after retrieval identity obligation satisfied on the frozen server candidate. | Offline actual private-checkout CLI pair: 35 fixtures, before baseline exit 0 and after pass exit 0, stable generations 3333/3334, same fixture/evaluator identities, only the server production member changed, zero comparison violations, invalidation or operator-review reasons. Ordinary private index updates ran immediately before each foreground evaluator, with no monitor or concurrent tree mutation. This measured pair is not universal retrieval or performance qualification. |
| 2026-10-11 | Independent code and QA discovered an attributable no-Git test eligibility regression; AC-3 is reopened and AC-4 remains unmet. | Insertion displaced the original skip decorator onto the new Git class. Actual before/current absence controls show intended old-class skip becoming FileNotFoundError during setup. Typed initial-delivery finding and repair-start cycle 1 were recorded before the sole owner edits. Original-candidate qualification was deliberately terminated, exit 143, and supplies no receipt authority. |
| 2026-10-11 | Bounded decorator repair complete and source refrozen; independent cycle-1 reverification pending. | Sole owner moved only the old class guard, preserving all test bodies and the other six paths byte-for-byte. Actual public loader: repaired Git-present nine tests pass with no skips; repaired Git-absent nine intentional skips and zero errors, preserving both reasons. A private copy removing only the restored guard reproduces setup FileNotFoundError. Production identity and completed retrieval pair remain unchanged; fresh matching canonical qualification is required. |
| 2026-10-11 | The real decorator finding is independently completed; both required repair lanes are cleared by typed cycle-1 reverification. | Fresh code and QA each publicly discover both whole classes with Git truly absent: nine intended skips, zero errors. Git-present nine/ten selected tests execute with no skips. Each private current-source guard-removal mutant reproduces six old-class Git-not-found setup errors. All seven identities match the final freeze; six paths and all bodies remain unchanged. Architecture reconciled the exact guard-only delta without repeating its prior controls. Current whole qualification and final full docs remain approval prerequisites. |
| 2026-10-11 | All four ACs and tasks completed; matching quiet canonical qualification passed on the repaired freeze. | 12,326 tests / 185 files / 803.946 seconds, exit 0, 12 aggregate skips. Genuine receipt `de3fcc02a3cc50de0c800a3f5adae0369045a0b79baa505c3b0401426c283754`, run `2026-10-11T11:10:43.395511+00:00`, transferred byte-identically after root/snapshot/source equality. No aggregate skip-identity claim; new focused tests execute without skips, and no-Git class skips are explicitly intentional. Completed retrieval pair and all three independent review conditions remain satisfied pending final current docs validation and typed approval publication. |
| 2026-10-11 | Delivery complete; all required code, QA and architecture approvals committed after final current full docs passed with zero errors and warnings. | Guided tool continuation contains only operator signoff. The real finding is completed with no unresolved lane, waiver or deferral; all four AC and four tasks are checked. Coordinator will pause under existing authorization; no closure, commit, push or new build is authorized by this implementation request. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-11 | Request only material specialist review lanes. | Wave record names scope-specific lanes; preserve policy-derived requirements and Council. | Reject blanket independent specialties/personas absent a material boundary or policy trigger because they add overhead without a demonstrated quality benefit. |
| 2026-10-11 | Required divergent pre-plan completed. | Select validation-then-sort and explicit Git untracked expansion: both are small fixes to observed seams. Reject editing every input inventory into order because it preserves an unnecessary input constraint. Reject broad distribution exemptions or a replacement lint predictor because no safe exemption need was established and the current predictor only needs the explicit Git flag. | Alternatives critiqued in selection rationale. |
| 2026-10-11 | Execute authorized follow-up within named scope. | Operator authorized preparation, review and implementation; coordinator serializes waves and pauses completed work. | No close, commit or push; unchanged authorized execution packet needs no new permission hold. |

## Risks

The server implementation is shared and may be a production-retrieval identity member even for a lint-only edit; inspect retrieval identity and satisfy applicable receipt policy before editing. Preserve the explicit shipped inventory and upstream bytecode controls; do not turn sorting into deduplication.

## Session Handoff

Planned; no code edited and no AC/task complete. Coordinator owns Prepare/Council and future activation. Read this file and wave.md for durable scope/evidence. Global handoff is coordinator-owned.

Review routing note: requested lanes are scope-specific; Prepare's actual policy-derived requirements and current Council gate remain authoritative. Product-owner and other unrequested specialties are not independently mandatory absent policy selection or a justified material finding.
