# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-31
review-evidence-source: events.jsonl

wave-id: `1tskc context-efficiency-projection-freshness`
Title: Context Efficiency Projection Freshness
review-policy-reprepare-required: false
## Objective

Keep the portable Context Efficiency checkpoint current during long implementation and review work
without changing the durable accounting model, and restore reliable MCP-owned index convergence.
Add verified turn-end projection where supported, a cross-host 120-second unchanged-generation
safety net, and zombie-/PID-reuse-safe index monitor recovery while retaining every lifecycle hard
barrier and existing index single-flight authority.

## Changes

Change ID: `1tsjh-enh context-efficiency-turn-end-projection`
Change Status: `implemented`

Change ID: `1txzt-bug mcp-index-monitor-stale-child-recovery`
Change Status: `implemented`

Completed At: 2026-07-30

## Wave Summary

Wave `1tskc` (Context Efficiency Projection Freshness) delivered two changes: Context Efficiency Turn-End and Quiet-Period Projection and MCP Index Monitor Stale-Child Recovery. Notable adjustments during implementation: MCP Index Monitor Stale-Child Recovery: Repaired stale-child ordering and durable PID classification, added the authoritative whole-index lock probe, and exposed bounded process-local monitor status.

**Changes delivered:**

- **Context Efficiency Turn-End and Quiet-Period Projection** (`1tsjh-enh context-efficiency-turn-end-projection`) — 12 ACs completed. Key decisions: Use a verified turn-end trigger plus a generation-stable quiet-period safety net, while retaining all hard lifecycle barriers.; Default to 120 seconds with a 90-second lower bound and configurable values through 600 seconds.
- **MCP Index Monitor Stale-Child Recovery** (`1txzt-bug mcp-index-monitor-stale-child-recovery`) — 9 ACs completed. Key decisions: Keep this as a separate bug change in 1tskc instead of widening the Context Efficiency change.; Add monitor status to existing index health/status instead of creating a new public tool.
## Watchpoints

- The automatic projector must never meter itself or create a new pending generation.
- Turn-end handling is non-blocking and fail-safe; lock contention leaves durable work pending.
- The quiet clock resets on every generation change and defaults to 120 seconds, with a 90-second
  lower bound and configuration through 600 seconds.
- Do not invent native hook surfaces for hosts without a verified end-turn contract.
- Preserve the shared publication lock, atomic marker replacement, generation compare-and-set,
  project-authored prose, close sealing/compaction, and reload/upgrade refusal behavior.
- Reconcile completed index children before active-state suppression; a real live builder must still
  exclude every duplicate spawn.
- Both MCP-owned background paths expose bounded configured/alive and last-outcome state through
existing diagnostic surfaces; neither creates telemetry or tracked-file polling churn.

## Implementation Evidence

- The Context Efficiency path now has one root-bound projector shared by hard boundaries, the
  dedicated Claude Stop adapter, and a generation-stable MCP safety net. Automatic projection is
  fail-fast, accounting/focus neutral, no-op stable, and continues past retryable per-wave failures.
- The index monitor reaps owned POSIX children before classification, rejects recycled PIDs through
  the canonical indexer classifier plus exact target-root binding, checks the authoritative build
  lock, survives reload with an empty registry, and launches `content=all` so docs and code converge
  together.
- Final independent review reproduced five boundary defects and verified their repairs: owner-root
  loss outside the Claude cwd, blocking same-process automatic publication, a close/seal TOCTOU,
  same-executable cross-repository PID reuse, and destructive replacement of operator Claude hooks.
  The repaired tree passed independent code, QA, architecture, and docs-contract review.
- Targeted changed-area tests, platform rendering, packaging, and docs lint pass. The canonical
  6,492-test run has one independently reproducible pre-existing actor-policy expectation in
  `RepairIndependenceBoundaryTests`; delivery review must classify that disclosed unrelated failure
  rather than treating the changed-area suite as green by assertion.

## Participants

- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer
- Builder lane: implementer
- Readiness council: red-team, docs-contract-reviewer (rotating)
- Delivery council: policy-selected universal council after implementation evidence exists

## Prepare Review Evidence

- **Red-team — 2026-07-29: PASS.** Strongest challenge: adding another daemon could repeat the
  index monitor's silent-failure class or accidentally meter its own projection. Resolution: require
  bounded monitor status and a projection-only primitive that excludes process flush, attribution,
  focus, stage, seal, and compaction side effects.
- **Docs-contract-reviewer — 2026-07-29: PASS.** The two changes remain separately specified while
  sharing explicit `ImplHandler` serialization. Platform and existing diagnostic-surface claims are
  bounded; unsupported native hook contracts remain out of scope.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-29: PASS** (moderator: wave-council;
  primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat:
  docs-contract-reviewer; strongest-challenge: prevent a second opaque or self-metering background
  loop; strongest-alternative: lifecycle-only projection was simpler but rejected because it leaves
  long implementation and review work visibly stale)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 28 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 94 | 1,882,217 |
| implement | 56 | 2,460,239 |
| review | 41 | 43,835 |
| **Total** | **191** | **4,386,291** |

<!-- wave:context-efficiency-state {"generation":135,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":56,"content_source_credit":2546012,"derived_artifact_credit":1746,"direct_net":2460239,"estimated_tokens_saved":2460239,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1448,"response_debit":87432,"source_credit_count":37,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1361},"plan":{"calls":94,"content_source_credit":2139727,"derived_artifact_credit":987,"direct_net":1882217,"estimated_tokens_saved":1882217,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6820,"response_debit":259132,"source_credit_count":106,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7455},"review":{"calls":41,"content_source_credit":90856,"derived_artifact_credit":1272,"direct_net":43835,"estimated_tokens_saved":43835,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2156,"response_debit":47483,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":191,"content_source_credit":4776595,"derived_artifact_credit":4005,"direct_net":4386291,"estimated_tokens_saved":4386291,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10424,"response_debit":394047,"source_credit_count":165,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10162},"wave_id":"1tskc context-efficiency-projection-freshness"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 3 | 4591412 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":4591412,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
