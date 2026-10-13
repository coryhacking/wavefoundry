# Reassess the deferred warm-estimator timing check

Change ID: `20h8h-task reassess-warm-estimator-budget`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-12
Wave: 20h6q combined-log-tail-check

## Rationale

Release 1.29.0 explicitly deferred a second-profile warm-estimator assertion while independent reviews were running concurrently. The recorded 50-source p95 was 47.612 ms against a 37.217 ms effective budget (25 ms nominal, contention factor 1.489). That observation does not establish a product performance regression or prove host contention caused it. Track a bounded later reassessment so the exception does not disappear from the work list.

## Requirements

1. Wait until unrelated concurrent review/test activity is no longer materially confounding the measurement. Do not launch timing investigation during the operator's current deferment or stop other sessions to create quiet conditions.
2. Reproduce the named test under the same second vocabulary/layout profile using the existing fixture and runner mechanisms. Record source identity, applied profile, effective threshold, observed p95, sample counts and relevant execution conditions without retaining raw transcripts indefinitely.
3. Bound reassessment to one baseline and one corroborating targeted run. If failures persist or conditions remain unsuitable, record that result and a scoped next decision; do not loop until green, rerun the entire suite just for timing, or relax assertions to make them pass.
4. This task produces an evidence-based disposition, not a production or budget change. Any demonstrated repair requires an explicit plan amendment and readiness before code edits. Preserve the original failed release report and exception.

## Scope

**In scope:** Deferred targeted measurement and concise diagnosis of ContextEfficiencyServerIntegrationTests.test_repeated_warm_estimator_and_projection_budgets; a durable disposition in wave.md.

**Out of scope:** Code or threshold edits, automatic retries, host tuning, machine-wide process control, full qualification solely for performance diagnosis, and claims of universal performance from two runs.

## Acceptance Criteria

- [x] AC-1: The reassessment records either valid targeted second-profile measurements with their source/conditions or an explicit inability to obtain interpretable measurements; it does not infer causation from the release-time failure alone.
- [x] AC-2: The final disposition distinguishes an observed pass, a reproducible scoped failure and inconclusive evidence, with a concrete next action where needed; original failed qualification remains intact.
- [x] AC-3: No production/test thresholds or unrelated machine workloads are changed; concise results remain in wave.md and temporary measurement artifacts are removed after relevant facts are retained.

## Tasks

- [x] T-1: At execution time, establish suitable conditions and choose the existing targeted second-profile invocation; otherwise keep the task deferred with its reason.
- [x] T-2: Run the bounded baseline and corroboration, or record why measurements remain uninterpretable.
- [x] T-3: Obtain a focused QA assessment of the evidence and record the disposition and any separate repair scope; clean temporary artifacts.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Bounded reassessment | implementer | readiness and suitable conditions | Read-only source; temporary measurement outputs |
| Evidence assessment | qa-reviewer | measurement or explicit deferral | No invented performance conclusion |

## Serialization Points

Plan only now. Schedule after concurrent review activity subsides; do not overlap with this wave's verification. The implementer may write temporary outputs and the wave summary only; source files below are read-only references. Reviewers inspect the evidence without automatically repeating measurements.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `.wavefoundry/framework/scripts/run_tests.py`

## Affected Architecture Docs

N/A: a one-time diagnostic task with no behavioral change. A later repair must identify its own affected contracts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Measurements must be interpretable and honestly bounded |
| AC-2 | required | Preserve an explicit disposition without erasing the release exception |
| AC-3 | required | Avoid unnecessary retries, source changes and retained artifacts |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Implementation/disposition and independent delivery reviews completed. Original planning handoff below is historical; current completion and local-pack limitations are recorded in wave.md and the session handoff. | Matching green framework qualification and typed review ledger |
| 2026-10-12 | Readback: AC-1–3 allow an explicit inability/inconclusive disposition. Operator confirmed concurrent reviews; perform no timing measurements or source/threshold edits. Preserve the original failed release result, record later bounded reassessment as next action, and obtain focused QA assessment. | Admitted plan; current-source boundary inspection; current typed readiness |
| 2026-10-12 | Added to the follow-up wave at operator request. No timing work performed; release-time results remain inconclusive under concurrent reviews. | Release 1.29.0 qualification exception; named test and recorded threshold/p95 |
| 2026-10-12 | Operator explicitly kept timing deferred because other reviews are running. Interpretable measurements are unavailable in this effort; no timing probe, threshold edit or workload interference was performed. Next action: the existing bounded targeted second-profile reassessment after suitable conditions are confirmed. Focused QA assessment remains pending. | Operator reply; Requirements 1–4 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-12 | Bounded targeted reassessment later, without assuming a fix | Retains the deferred issue while respecting the operator's no-timing-investigation constraint | Raise the budget now: unsupported and may hide a regression. Repeat whole profiles under concurrent load: costly and still inconclusive. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A quiet-looking host still has hidden contention | Record limitations and preserve an inconclusive outcome when warranted |
| Repeated measurements become a pass-seeking loop | Fixed two-run budget and explicit next decision |

## Session Handoff

Planned only; this task does not authorize immediate timing tests or source edits.
