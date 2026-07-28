# Single-Pass Review Lifecycle

Change ID: `1tr85-enh single-pass-review-lifecycle`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-27
Wave: `1tsyx review-lifecycle-simplification`

## Rationale

Wavefoundry's review controls have become strong enough to catch real defects, but the
lifecycle now asks several surfaces to establish substantially the same claim: readiness
councils and a separate pre-implementation review, implementation-time inferential review,
specialist lanes plus council seats, repeated prose and typed evidence, full-suite runs at
several nearby boundaries, repair-start ceremony, per-cycle convergence records, and another
delivery/close evaluation over much of the same state. Recent waves show that this repetition
adds latency and makes ownership harder to understand without providing an independent new
oracle each time.

The intended rule is:

> Each lifecycle claim is independently reviewed once. Repeat review only when later work
> invalidates that claim, and re-review only the affected scope and lanes.

This change simplifies orchestration without weakening the protections that have produced
high-quality results. Readiness remains mandatory before code, one independent delivery review
remains mandatory after implementation, material repairs still require independent
reverification, and credible security, concurrency, corruption, migration, destructive, and
external-input risks still receive adversarial depth. The change removes duplicate ceremonies,
not independent judgment.

## Requirements

1. **One canonical lifecycle.** Define and enforce one lifecycle matrix:
   `Plan -> Prepare -> Implement -> Review -> focused repair/reverification when needed ->
   operator review -> Close`. The matrix owns which claims are established at each stage,
   who may establish them, which evidence is required, and what invalidates them. Other seeds,
   prompts, role docs, tool docstrings, and contributor docs point to or render from that
   contract rather than restating divergent variants.
2. **Prepare owns a strong critical pre-implementation review.** Fold the pre-implementation
   review into Prepare, but preserve it as a mandatory, fresh, independent critique of the
   proposed work before the first implementation edit. The selected readiness lanes must test the
   plan's assumptions, alternatives, scope boundaries, AC completeness, failure modes, affected
   consumers, install/upgrade impact, concurrency and recovery behavior, verification strategy,
   and credible threat paths; findings may block readiness and must be repaired and rechecked
   before Prepare passes. Remove only the separate `pre-implementation-review:` marker,
   chronology audit, and second approval concept. Re-Prepare is required only when admitted
   scope, required AC semantics, trust boundaries, architecture/ownership, or another named
   load-bearing readiness assumption materially changes before implementation.
3. **Implementation is builder-owned.** Implementation runs focused computational checks and
   may request an exceptional named checkpoint at a high-risk boundary, but it does not run
   routine inferential review or manufacture delivery approval. Remove automated/repeated
   reviewer invocations whose result will be superseded by the post-implementation review.
4. **One independent delivery review.** Review begins after implementation and the first full
   canonical suite. It runs one risk-selected set of independent lanes. Those lane results are
   authoritative; a compact coordinator-generated summary reports their current state without
   conducting another review or requiring a council verdict.
5. **Review depth has real cost differences; Council is operator-invoked.** Use one unambiguous
   review policy (`risk_based | universal`) and make risk-based the shipped default. Under
   `risk_based`: lightweight review selects one or two relevant lanes; standard review requires
   code/QA plus risk-selected lanes; full review selects the broad adversarial lane set only for
   evidenced high-risk boundaries. The Wave Council is not automatically invoked and is not a
   lifecycle gate; it remains available when the operator explicitly requests broader synthesis,
   alternative generation, or help resolving conflicting lane conclusions. Conflicting required
   lanes remain blocking until the operator resolves them or invokes the Council. Remove the
   ambiguous `enabled`/`required_for_all_waves` behavior and any parsed-but-ignored setting.
6. **Threat-grounded adversarial depth.** Full security/adversarial review is triggered by a
   credible actor/capability/reachability/impact path such as lower-trust or external input,
   credentials/authentication, concurrency, corruption or interruption, migration/upgrade,
   destructive operations, or writes outside the project's ownership. Trusted local
   operator-owned, Git-auditable state is a correctness/integrity concern unless a concrete
   threat path is evidenced. Missing threat-model documentation does not suppress a directly
   evidenced external threat.
7. **One evidence authority, compact projection.** Keep `events.jsonl` as the sole machine
   authority, `wave.md` as a generated current-state projection plus one concise review summary,
   and Git as optional historical audit/reconstruction. Do not add sidecars,
   receipts, hashes, or a Git requirement. Remove hand-authored `prepare-council` evidence and
   repeated per-seat prose as separate machine gates.
8. **Minimal honest evidence records.** Approval records contain only facts actually supplied
   or mechanically known. They must not synthesize integrity booleans such as
   `known_bad_detected=true` when the approval input did not establish them. Review/finding
   authoring retains the smallest set of load-bearing semantic judgments; bookkeeping,
   supersession, and projection fields remain generated.
9. **Focused repair loop.** Replace the mandatory
   `finding -> pre-mutation repair_start -> reverification -> global cycle/convergence ceremony`
   with `finding -> repair -> independent affected-lane reverification -> approval`. Review and
   repair may iterate as often as needed in the same review phase. Only affected approvals become
   stale. A broader lane review is required only when the repair changes a named full-review
   boundary; an automated Council rerun is never required. Repeated boundary drift may trigger a
   convergence checkpoint, but cycle 2 alone does not.
10. **Evidence-rich, narration-light execution.** Remove mandatory
    Thought/Action/Observe/Reflect/Gapfill narration and the retrieval-posture prose gate. Keep
    concise decisions, deviations, blockers, scope changes, test evidence, and lifecycle
    milestones. MCP-first retrieval remains guidance; context-efficiency telemetry is useful
    review input but never an approval gate.
11. **Bounded test cadence.** During implementation, run focused tests and sensors. Run the full
    canonical suite once before initial delivery review. After a finding, run its exact
    reproduction/known-bad control and affected focused suites; run one final full suite after all
    material findings are terminal. Require an extra mid-cycle full suite only when a repair is
    cross-cutting or changes a load-bearing integration boundary.
12. **Single delivery evaluator.** Review and Close use one shared, read-only delivery-state
    evaluator. Close adds only close-specific checks (operator approval, terminal AC/tasks,
    pending memory, archive/landing mechanics) and does not independently reconstruct or rerun the
    delivery review.
13. **Memory once, after terminal findings.** Propose and validate durable memory after delivery
    findings are terminal. Close checks that no candidate remains pending; it does not repeat
    memory analysis already completed by Review.
14. **Remove stale and dead lifecycle branches.** Remove the retired journal-distillation closure
    language and either delete `rerun_prepare_before_closure` or replace it with the named
    boundary-delta re-Prepare rule. Census public prompts, seeds, generated carriers, tool
    docstrings, validators, dashboards, and tests so no old path remains authoritative.
15. **Clean install and upgrade.** Fresh installs render only the simplified lifecycle. Upgrade
    maps `required_for_all_waves=true` to `universal` and every other old Council configuration to
    `risk_based`, removes both retired booleans, makes Council operator-invoked, regenerates
    carriers, and leaves closed historical ledgers readable as inert history without retaining the
    old mutation workflow. Non-Git projects receive the same behavior.
16. **Preserve hard invariants.** The implementation must retain a fresh independent critical
    plan review before code, readiness before implementation, independent post-implementation
    review, independent affected-lane reverification after a material repair, exact known-bad and
    adjacent controls where applicable, operator-owned close, atomic cross-process event
    publication, non-Git support, and a full-suite release boundary.

## Scope

**Problem statement:** The same review claims are established and encoded repeatedly across
Prepare, Implement, Review, repair cycles, and Close. The duplication increases elapsed time,
tool use, evidence volume, and contradictory guidance while making it less clear which approval
is authoritative.

**In scope:**

- The canonical lifecycle/review contract and all generic seed/prompt/role carriers.
- Review policy configuration and its install/upgrade normalization.
- Prepare, implement, review, repair/reverification, memory, and close orchestration.
- Review-evidence construction, validation, current-state projection, and approval staleness.
- Risk/depth selection and credible-threat grounding.
- Shared delivery-gate evaluation and test cadence.
- Dashboard/help/spec/reference text needed to explain the simplified state.
- Removal of obsolete code, fields, branches, tests, and documentation made unreachable by the
  cutover.

**Out of scope:**

- Weakening independent pre-implementation or delivery review, or letting implementers
  self-approve repairs.
- Replacing `events.jsonl` with Git or requiring source control.
- New evidence sidecars, receipts, adoption files, or proof hashes.
- A universal full council after every repair.
- Open-ended fuzzing or unbounded adversarial probes.
- Reclassifying concrete external, credential, concurrency, corruption, migration, destructive,
  or cross-ownership risks as harmless to reduce review cost.
- Rewriting closed historical wave ledgers.
- Test-runner performance work already owned by wave `1tmtx`.

## Acceptance Criteria

- [ ] AC-1: A single executable lifecycle matrix is the canonical source for stage claims,
  invalidation triggers, authorized actors, review depth, required evidence, and test cadence;
  all rendered/public carriers are consistent with it and no second conflicting contract remains.
  The matrix states explicitly whether an approval recorded in one phase may satisfy a later
  phase's gate. Approval currency is per signoff key and phase-free today, so a readiness-phase
  approval already satisfies a delivery gate; the matrix must either affirm that as intended or
  scope currency by phase, and the answer is load-bearing for AC-7.
- [ ] AC-2: Prepare cannot pass until a fresh independent critical reviewer has challenged the
  proposed design, alternatives, assumptions, scope/ACs, failure/recovery paths, affected
  consumers, install/upgrade behavior, verification strategy, and applicable threats; findings
  block readiness. No separate pre-implementation marker or chronology gate exists, unchanged
  plans proceed without a second review, and every named material boundary delta requires
  focused re-Prepare. Activation consumes typed readiness evidence: on a wave declaring
  `review-evidence-source: events.jsonl`, `wf_implement_wave` Gate 1 must not open the wave on a
  hand-authored structural prose verdict line, and a fixture proves a forged line cannot open it.
- [ ] AC-3: The implementation path runs no routine inferential reviewer; one independent
  post-implementation review satisfies both selected specialist lanes and council seats, with
  exceptional checkpoints limited to an explicitly named high-risk boundary.
- [ ] AC-4: `risk_based | universal` is the only automatic review policy. Executed fixtures prove
  materially different lightweight, standard, and full lane rosters, prove credible high-risk
  examples cannot be downgraded to lightweight, prove no Wave Council runs automatically, and
  prove an explicit operator request can invoke it without replacing or waiving required lanes.
- [ ] AC-5: Upgrade fixtures cover all old boolean combinations, remove the retired keys, preserve
  local repository config not owned by the migration, render the simplified surfaces on fresh
  install and upgrade, and work in a non-Git target.
- [ ] AC-6: A typed evidence fixture proves approval events never fabricate unsupplied test or
  integrity facts; malformed or insufficient approvals fail closed with an actionable diagnostic.
- [ ] AC-7: Repair fixtures prove one finding can be repaired and independently reverified in the
  same review phase, only affected lanes stale, repeated findings can loop without forced global
  cycles, and a named load-bearing boundary change still triggers the required broader review.
  A fixture also pins the AC-1 phase-currency answer, so whichever way it is decided the behavior
  is executed rather than implied.
- [ ] AC-8: Review and Close return the same delivery-gate diagnostics from one shared evaluator;
  Close adds only its enumerated close-specific checks and does not rerun review work.
- [ ] AC-9: Test orchestration fixtures prove the focused/full-suite cadence, including exact
  known-bad and adjacent controls after repairs and the cross-cutting-repair exception.
- [ ] AC-10: `events.jsonl` remains the sole machine authority, publication remains atomic under
  concurrent writers, wave.md contains only the compact current projection/synthesis, and no new
  state sidecar or Git dependency is introduced.
- [ ] AC-11: Repository-wide contract and dead-code censuses find no authoritative
  `pre-implementation-review`, mandatory `repair_start`, unconditional cycle-2 convergence,
  mandatory Gapfill narration, stale journal-distillation closure step, ignored
  `required_for_all_waves`, or duplicate delivery-gate implementation outside explicitly
  documented closed historical records.
- [ ] AC-12: Focused lifecycle/install/upgrade/render tests and the canonical full suite pass; docs
  lint and generated-surface drift checks are clean; a worked lightweight wave demonstrates the
  intended shorter path without loss of independent delivery review.

## Tasks

- [ ] Write the canonical lifecycle matrix and threat/risk-to-depth decision table first.
- [ ] Replace review-policy booleans with the single mode and implement one-way install/upgrade
  normalization.
- [ ] Reconcile Prepare around one strong independent critical plan review and remove only the
  duplicate pre-implementation marker/gate.
- [ ] Remove routine implementation-time inferential review; make selected specialist lanes
  authoritative and retain Council as an operator-invoked surface only.
- [ ] Simplify evidence construction, approval facts, repair/reverification transitions, and
  per-lane invalidation while retaining atomic publication and honest archive reads.
- [ ] Extract the shared read-only delivery evaluator and route Review/Close through it.
- [ ] Reconcile test cadence, memory timing, retrieval guidance, and closure mechanics.
- [ ] Regenerate every shipped carrier and update architecture/spec/contributor/dashboard docs.
- [ ] Add install, upgrade, non-Git, concurrency, known-bad, risk-depth, and end-to-end lifecycle
  fixtures; delete tests that only pin retired ceremony.
- [ ] Run residue/dead-code/contract-owner censuses, focused tests, the canonical full suite, docs
  lint, and generated-surface drift checks.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| lifecycle-contract | architecture-reviewer | — | Own the matrix, invalidation triggers, and depth policy before code changes. |
| orchestration-and-evidence | implementer | lifecycle-contract | Prepare/Implement/Review/Close and `events.jsonl` state machine move together. |
| install-and-upgrade | implementer | lifecycle-contract | One-way config cutover; no runtime fallback path. |
| carriers-and-docs | docs-contract-reviewer | lifecycle-contract | Seeds are canonical; regenerate, do not patch generated copies as authority. |
| verification | qa-reviewer | orchestration-and-evidence, install-and-upgrade, carriers-and-docs | Risk matrix, known-bads, concurrency, install/upgrade, end-to-end path. |

## Serialization Points

- The lifecycle matrix and policy-mode mapping must be accepted before implementation branches
  edit consumers.
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`,
  `.wavefoundry/framework/scripts/review_evidence.py`, and
  `.wavefoundry/framework/scripts/server_impl.py` are shared chokepoints and require single-owner
  edits or explicit handoff.
- Review-evidence grammar and tool response changes land before prompt/carrier regeneration and
  end-to-end fixtures.
- Install/upgrade normalization lands before the rendered-surface parity sweep.
- The active `1to78` wave must close or explicitly hand off its overlapping files before this wave
  opens; planning/readiness may proceed without disturbing it.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — lifecycle and evidence transitions.
- `docs/architecture/testing-architecture.md` — focused/full test cadence and known-bad policy.
- `docs/architecture/threat-model.md` — credible-threat trigger and local-trust boundary.
- `docs/architecture/current-state.md` — public lifecycle flow and review policy mode.
- `docs/contributing/review-and-evals.md` and lifecycle overview/workflow docs — operator-facing
  review semantics.
- `docs/specs/mcp-tool-surface.md` — lifecycle tool envelopes and diagnostics.
- An ADR is required if Prepare/Review/Close ownership or the review-policy mode is judged a stable
  architectural decision rather than an implementation detail during readiness.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents prompt/code/validator contradiction. |
| AC-2 | required | Removes the duplicate readiness claim. |
| AC-3 | required | Establishes the one independent delivery review. |
| AC-4 | required | Makes review depth and policy configuration effective. |
| AC-5 | required | Framework-wide behavior must install and upgrade cleanly. |
| AC-6 | required | Approval evidence must remain honest. |
| AC-7 | required | Repair loops must converge without weakening independence. |
| AC-8 | required | Review/Close must not duplicate delivery evaluation. |
| AC-9 | important | Reduces test latency while retaining evidence. |
| AC-10 | required | Preserves the events-only authority and concurrency guarantees. |
| AC-11 | required | Prevents the retired workflow from surviving in another carrier. |
| AC-12 | required | Proves the simplified lifecycle works end to end. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-27 | Planned from the pre-1.15 lifecycle/code/process audit and operator direction to preserve strong review while eliminating repeated review of the same claim. | Audit prompt and findings; recent wave telemetry and evidence-ledger histories cited in the Rationale and Decision Log. |
| 2026-07-27 | Folded two wave-`1to78` delivery-council follow-ups into this plan's ACs at operator direction, as naming rather than new scope: the typed Gate 1 activation read (AC-2, censused by AC-11's `pre-implementation-review` sweep) and the phase-currency question for lane approvals (AC-1, pinned by an AC-7 fixture). Both were already inside Requirement 1/2/7 in substance but unnamed, so no census or fixture anchored them. A third follow-up (Participants lane-roster scaffold plus empty-roster lint advisory) was deliberately NOT folded in: Requirement 5 makes lane selection risk-derived, which may delete the hand-authored roster entirely, so building a scaffold for it now would be work against a surface this wave may remove. | 1to78 delivery-council findings ledger; 1to78 wave record AC scope gap check |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-27 | Select a coordinated single-pass lifecycle cutover across contract, orchestration, evidence, and carriers. | The duplication is enforced across all four layers; changing only one leaves contradictions or dead ceremony. | Prompts-only simplification — rejected because validators/tools would still enforce the old path. Remove review gates broadly — rejected because it weakens independent quality control. Keep the current model and improve wording — rejected because it does not remove repeated work. |
| 2026-07-27 | Keep `events.jsonl` as the sole machine authority and Git as optional audit history. | The recent events-only cutover already removed redundant receipts; Git cannot be required in supported non-Git projects. | Replace events with Git — rejected. Add another summary/receipt sidecar — rejected. |
| 2026-07-27 | Make lane selection risk-based by default, retain universal lane selection, and make Wave Council operator-invoked rather than automatic. | Required lanes already own findings and cannot be waived by Council; automatic Council repeats their work. Council remains valuable for an operator-requested multi-perspective synthesis or conflict resolution. | Keep automatic Council with fewer seats — rejected because it preserves the duplicate review layer. Remove Council entirely — rejected because explicit operator use remains valuable. Disable review — rejected because critical readiness and independent delivery review are hard invariants. |
| 2026-07-27 | Keep one strong critical pre-implementation review inside Prepare. | Simplification must validate and critique the proposed approach before code rather than shifting all independent judgment until after implementation. | Checklist-only Prepare — rejected as too weak. Separate Prepare plus pre-implementation review approvals — rejected as duplicate claims. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Simplification weakens pre-implementation challenge or high-risk review. | Require a fresh independent critical plan review in Prepare; pin its challenge dimensions and the credible-risk trigger table with downgrade-resistant fixtures. |
| Multiple carriers drift during the cutover. | Establish one canonical matrix, regenerate surfaces, and run a repository-wide residue/ownership census. |
| Approval or repair state becomes permissive. | Use red-first known-bad fixtures for fabricated approval facts, stale-lane behavior, self-reverification, and changed-boundary reruns. |
| Upgrade leaves targets on mixed old/new semantics. | One-way config/surface migration with no fallback; installation and upgrade end-to-end fixtures include non-Git targets. |
| Historical ledgers force a second compatibility system. | Treat closed records as inert readable history; do not preserve the retired mutation workflow for active waves. |
| The simplification wave becomes another open-ended review saga. | Freeze scope to the requirements above; adjacent ideas are classified through the actionability matrix and do not expand the wave without an operator-approved contract change. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state. Wave `1to78` CLOSED on 2026-07-27,
so its serialization hold on the shared lifecycle/evidence files is released and no wave currently
owns them. Its follow-up FU4 (content-driven wave-folder role in `review_evidence.py`) landed
separately under an operator waiver; read the file for current shape.
