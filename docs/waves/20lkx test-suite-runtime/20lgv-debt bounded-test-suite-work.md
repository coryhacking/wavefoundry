# Bounded Test Suite Work

Change ID: `20lgv-debt bounded-test-suite-work`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-14
Wave: `20lkx test-suite-runtime`

## Rationale

The operator requests lower qualification time without weaker coverage. The latest canonical run passed 12,504 tests across 187 files in 763.799 seconds with six workers. Docs-lint took 448.8 worker-seconds and the 17-test prefix-collapse module took 267.0. Discovery found 330 distinct docs-lint test methods executed 1,226 times through inherited runnable base classes, and scanner tests that traverse the growing live checkout or a large historical artifact. The change removes redundant work and uses bounded ordinary fixtures, preserving an explicit whole-checkout audit. Host contention makes these observational timings unsuitable for a promised speedup; deterministic work reduction and transparent before/after measurements are the acceptance basis.

## Requirements

1. Separate reusable docs-lint fixture helpers from runnable TestCase classes. Every distinct existing docs-lint test method and its assertions remains discoverable once with equivalent fixture behavior. Remove only inherited duplicate executions whose subclasses do not change the inherited test or its fixture semantics; preserve any intentional variant found during implementation.
2. Ordinary prefix-collapse tests use finite scratch inputs independent of checkout history for eligible-file accounting and dense-input cost reporting. Exercise the real file walker and scanner, with explicit expected eligible, scanned and guard-skipped paths and reasons; a silent omission or unknown skip reason must fail. Preserve the existing frozen language-equivalence, positive/negative detection and ledger-write controls.
3. Retain the existing whole-checkout coverage and historical slow-artifact checks behind an explicit audit invocation in the same test module, outside normal unittest discovery. Do not introduce ordinary skipped tests, alter production scan scope, rules, caps or guards, or remove the audit's no-repository-write boundary. Document the invocation and distinguish optional diagnostic audit results from canonical qualification.
4. Record a pre/post discovery census and fixture workload counts, focused test outcomes and canonical elapsed/per-file timings. Preserve interpreter isolation, bytecode refusal, receipt integrity, normal worker settings and scheduling. Keep performance claims bounded by observed machine load; do not promise a return to the older 135.9-second median.

## Scope

**In scope:** test helper inheritance, bounded scanner fixtures, explicit diagnostic audit selection, testing architecture documentation and measured qualification.

**Out of scope:** production lint/scanner changes, broad CLI-to-in-process conversion, runner scheduling or cache changes, higher worker limits, receipt/review gates, model/backend work, machine/service tuning, unrelated test modules, release packaging or commits.

## Acceptance Criteria

- [x] AC-1: Standard discovery retains every distinct existing docs-lint test body and equivalent helper behavior while removing only proven inherited duplicates; before/after method identity and fixture checks explain every count change.
- [x] AC-2: Default scanner accounting and dense-input tests consume a fixed scratch corpus rather than live checkout/history; known-bad missing-work and reporting controls fail the relevant assertions while current production scanner behavior passes.
- [x] AC-3: An explicit audit command still runs the real-checkout accounting and historical-artifact checks with no repository writes; default discovery excludes these audit-only checks without adding skips. A bounded scratch-root control exercises audit dispatch and write containment.
- [x] AC-4: Changed tests and documentation pass their checks, and evidence reports reduced redundant execution and bounded input work alongside honest before/after timing and remaining limitations. No failure elsewhere is attributable to this change.

## Tasks

- [x] Capture the method/fixture baseline and isolate bounded scanner inputs and audit entry point.
- [x] Extract helper-only test bases and preserve all unique docs-lint assertions.
- [x] Bound ordinary scanner fixtures and retain the explicit read-only checkout audit.
- [x] Update testing docs, independently review coverage preservation and run final qualification.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Plan and integration | coordinator | — | Source edits only after readiness |
| Readiness | independent council and required lanes | plan | Source-grounded, bounded review |
| Implementation | coordinator as implementer | readiness | Serial writes to two test files and testing docs |
| Delivery | independent council and required lanes | implementation | Method census, bounded controls, final results |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_secrets_prefix_collapse.py`
- `docs/architecture/testing-architecture.md`

Temporary census, timings and reviewer reports stay outside the repository. No production code, runner, seeds or config writes.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: unique-test helper convention, default bounded scanner fixtures and explicit read-only diagnostic audit command.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Remove redundant execution without losing assertions |
| AC-2 | required | Stable ordinary-suite work and meaningful scanner coverage |
| AC-3 | required | Preserve intentional whole-checkout investigation and containment |
| AC-4 | required | Demonstrate work reduction and avoid overstated timing claims |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Discovery: MCP targeted source reads and AST census show 330 distinct docs-lint methods, 1,226 discovered executions and 896 inherited repeats; eight subclasses do not override base fixture/test methods. Prefix-collapse ordinary tests scan the live checkout and historical census. | `test_docs_lint.py`; `test_secrets_prefix_collapse.py`; preceding canonical run 12,504/187/12 skips, 763.799 seconds |
| 2026-10-13 | Gapfill: AST and unittest discovery counts are executed mechanical probes; prose-only authoring uses known filesystem paths. MCP code reads validate the affected source, without an indexed-freshness claim. | Current source and temporary census |

| 2026-10-13 | Readiness passed; implementer readback: preserve all 330 distinct docs-lint methods and fixture semantics, replace two unbounded default scanner probes with finite real-scanner fixtures, retain explicit contained checkout audit, then independently review and qualify. No runner or production changes. | Typed readiness approvals; receipt review-policy-88ff696f600452dbbd7c |

| 2026-10-14 | Implementation: helper-only bases preserve all 330 method ASTs and all baseline helper resolutions; default discovery drops 896 inherited repetitions. Scanner uses exactly eight eligible paths, four existing guard reasons and three findings; quiet no-keyword processing is observed independently of cost rows. Dense fixture is 32 lines / 3,968 bytes. | Before/after census and four known-bad controls: missing eligibility, unprocessed quiet file, unknown reason and absent cost row each fail the owning assertion |
| 2026-10-14 | Explicit two-check checkout audit retained in a function-local suite. Bounded dispatch passes both checks without skips or changed scratch files. Initial dispatch assertion matched the word skipped in a test name; corrected it to check the unittest skip summary. | CheckoutAuditDispatchTests; ordinary discovery adds only this bounded control |

| 2026-10-14 | Qualification cycle 1: 11,609 tests / 187 files / 12 skips in 625.671 seconds; one failing profile-literal census. QA reproduced the new hard-coded audit fixture path. Initial focused repair attempted declared layout roots; the adjacent stale-allowlist control correctly rejected changing the intentionally fixed historical repository input. Final repair shares the original historical path between the audit and its scratch fixture, retaining the existing repository-input-prose exception without additions. Other 186 files passed, including docs-lint 50.3 seconds and prefix-collapse 15.9 seconds. | Finding 20lkx-profile-literal-census; final green receipt pending |

| 2026-10-14 | Focused repair is green: all eight profile-census tests and 18 prefix tests pass, no skips, in 15.398 seconds. The intentionally historical path remains fixed and shared; there is no new allowlist or default-profile exclusion. Fresh code/QA reverification and final canonical run are in progress. | ProfileLiteralCensusTests, CheckoutAuditDispatchTests, existing repository-input-prose exception |

| 2026-10-14 | Final canonical qualification green: 11,609 tests / 187 files / 12 existing skips, 627.384 seconds wall and 2,907.103 worker-seconds. Before: 12,504 / 187 / 12, 763.799 wall and 3,701.111 worker-seconds. Count delta is exactly 896 inherited repeats removed plus one audit-dispatch control. Docs-lint 448.8 to 52.444 seconds; prefix-collapse 267.0 to 16.038; no controlled causal speedup claim under varying host load. | Fresh green receipt input hash b240480388326e02c42685eb78d282f68a335f98d052027b6326a2a6f655bae4; run_tests.py default six workers |
| 2026-10-14 | Fresh focused code/QA independently cleared the fixture finding: original historical path and existing exception retained, exact census and stale-entry controls pass, bounded audit has zero skips/writes under default and nondefault declared roots. Reintroduced literal, inappropriate historical relocation and removed write containment are detected. | Typed cycle-1 reverification; ProfileLiteralCensusTests and CheckoutAuditDispatchTests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-13 | Remove proven duplicates and bound ordinary scanner work; retain explicit real-checkout audit. | Smallest change that eliminates measured avoidable work while retaining distinct tests, real scanner execution and diagnostic capability. | More workers or changed scheduling does not remove work and can worsen contention; broad in-process CLI conversion changes isolation and coverage across many cases, so defer until profiling justifies it. |
| 2026-10-13 | Use the just-completed canonical run as baseline and compare deterministic work counts plus subsequent focused/full results. | Avoid another expensive unchanged full run; disclose load differences instead of attributing all elapsed-time change to code. | Repeated full benchmarks on this contended host add delay without controlling the main confounder. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Inheritance hides intentional fixture variants | Compare method bodies, helper resolution and subclass overrides before removing executions |
| Smaller scanner corpus loses real boundary coverage | Explicit eligible/scanned/skipped cases and independent bad-result controls; retain real-checkout audit |
| Audit accidentally writes the project ledgers | Preserve no-write recorders and exercise containment in scratch |
| Apparent speedup is host noise | Report deterministic counts and work bounds separately from elapsed time |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
