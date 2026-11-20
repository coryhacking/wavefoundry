# Match the test boundary to the failure

Change ID: `23tcu-enh match-test-boundary-to-failure`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23tcw test-boundaries-and-technology-evidence

## Product Intent

A builder starts with the bug a user could observe and chooses the simplest test that would fail if that bug remained. QA uses the same question to decide whether the test supports the claim. For any language, ordinary inputs can establish a decision rule. For listener recovery, the decisive observation is a successful request through the same listener after the injected failure. AC-2 checks whether both roles make that distinction in a worked example.

## Rationale

Tensorwell wave `0evgw` reports two passing listener controls. Its recovery test injects a fault just after accept on five real loopback connections, then requires HTTP 200 from fresh readiness and liveness requests on the same server. A loop could count all five failures and still drop every subsequent request. The second test exercises shutdown during repeated failures, a separate claim. The source is `accept_failures_are_survived_and_reported_on_transition` and the following shutdown test in `crates/tensorwell-daemon/src/service/tests.rs`. Wavefoundry inspected the source and downstream record; it did not rerun those tests.

## Requirements

1. Carry Tensorwell's proposed question into the existing cross-language builder and QA guidance:

   > What bug would this test catch, and which parts of the real system must run to expose it?

   Test a decision with ordinary values when they expose the bug. For I/O, timing or resource lifetime, exercise the relevant production path and inject the difficult condition at the narrowest practical point.

2. Illustrate the question with listener recovery. Inject an accept-path failure, then send a real request through the listener and check its response. A retry counter answers a different question about retry or reporting behavior. Preserve the existing evidence rules for the claimed path and independent expected results.
3. Keep the source attribution in this proposal. Use a self-contained example in shipped guidance so a downstream team can apply it without access to Tensorwell.

## Scope

Extend existing test-design and review prose. Seed 209 owns shared evidence guidance; the builder execution instructions and seed 239 QA guidance carry it to their readers. Check local builder and QA entry points and their canonical owners before editing. No language-specific mocking policy, new review lane, tool, or mandatory artifact.

## Acceptance Criteria

- [x] AC-1: A builder and a QA reviewer following their ordinary instructions each encounter the question and can locate the recovery example.
- [x] AC-2: In a short exercise, the builder uses ordinary inputs for a pure retry decision and exercises a real listener for recovery. Given a listener that counts every retry but drops every subsequent connection, QA rejects the counter as proof of recovery. QA identifies the failing assertion: a fresh request to that same server must receive the expected response.

## Tasks

- [x] Trace both role entry points and update the shared guidance and necessary carriers.
- [x] Exercise both claims, reconcile local instructions, and validate documentation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Test guidance | Documentation writer | Readiness | One writer for shared and role-specific instructions |
| Behavioral check | QA reviewer | Draft | Compare decision and recovery examples |

## Serialization Points

- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`, `.wavefoundry/framework/seeds/239-qa-reviewer.prompt.md`, `.wavefoundry/framework/seeds/180-implement-spec.prompt.md`, `docs/agents/implementer.md`, `docs/agents/qa-reviewer.md`

## Affected Architecture Docs

Existing evidence and role contracts apply.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Both roles need the instruction where they work. |
| AC-2 | required | Checks whether the question changes the choice of evidence. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-19 | Recorded Tensorwell's proposal and verified the example against its local source. | Listener test at line 2490; post-failure requests at lines 2511–2512. |
| 2026-11-19 | Readback: choose evidence for the decision in scope. | Exercise ordinary role instructions against the case observations before sharing the scoring criteria. |
| 2026-11-19 | Builder passed five retry-budget cases and received pong from a fresh connection after five injected post-accept failures. The defective listener counted five and returned an empty response. QA independently identified the failing fresh-request assertion. | Fresh role readers used the normal role entry points before seeing the scoring criteria. Full docs lint passed. |
| 2026-11-19 | Corrected the two seed instructions after the partial-install audit exposed links that broke when copied into a project. | Independent reviewer rendered a downstream fixture twice, resolved six paths and exact headings, and rejected the obsolete relative link and twelve altered paths or titles. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-19 | Propose a question in the existing builder and QA guidance. | It connects the failure to the necessary real components and observable result. | A Rust-only rule would miss the same design choice in other languages. Requiring full-system tests for pure decisions would add unrelated dependencies. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A reviewer interprets “real system” as requiring every dependency. | Show how the real listener and a controlled failure can coexist with a fake backend. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
