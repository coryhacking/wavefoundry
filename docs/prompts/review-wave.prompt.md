# Review Wave

Owner: Engineering
Status: active
Last verified: 2026-07-31

Shortcut: **`Review wave`**

## Purpose

Run all required review lanes against the admitted changes. Review is not optional when required lanes were confirmed at readiness.

## Steps

All review, repair, and reverification investigation follows the run contract's Retrieval Rules (`.wavefoundry/framework/seeds/020-run-contract.prompt.md`): MCP retrieval tools first, for every lane and briefed subagent; executed probes remain shell work.

1. Read the wave record and each admitted change doc; confirm which review lanes were required at readiness.
2. Run each required lane:
  - `code-reviewer` — correctness, pattern compliance, branch completeness, re-entrant safety for mutable state
  - `qa-reviewer` — AC coverage, multi-step verification for stateful behavior
  - `architecture-reviewer` — boundary and layering impact
  - Other lanes as required per `docs/contributing/review-and-evals.md`
3. When `wave_review.enabled` is true, run the Wave Council delivery pass in two phases: first, the `wave-council` declares a **primer depth tier** (`lightweight` / `standard` / `full`) based on trust boundaries touched, files in scope, and change type; (1) `red-team` runs the adversarial primer (`council-adversarial-primer` mode) first at the declared depth — strongest challenge, best alternative, `primer_questions`; (2) fixed seats each receive the standard briefing plus the primer and must address it before producing findings; rotating fifth seat finds the strongest unconsidered alternative; `wave-council` synthesizes all outputs; record `wave-council-delivery` (on declared waves as a typed approval event via `wf_review_event`, which projects into `## Review Evidence`; only legacy prose waves record the signoff line directly) and summarize the reasoning in `## Review checkpoints`. The checkpoint must include the seat roster, the rotating fifth seat, any material disagreements, and how they were resolved or why they remain unresolved. Delivery review verifies the current typed readiness authority on declared waves; it does not treat a prose `prepare-council` checkpoint as machine evidence. Legacy waves retain their prose compatibility contract.
4. **AC scope gap check:** after confirming required ACs are met, surface important/nice-to-have items not in admitted scope; confirm not-this-scope deferrals.
5. **AC priority reconciliation:** reconcile the `## AC priority` table against delivered behavior; update if scope shifted; `qa-reviewer` must attest every required row has verification evidence or a recorded deferral. **`[~]` AC verification:** for every AC marked `[~]` (intentionally not met), `qa-reviewer` confirms the inline status note is present and legitimate (names when / who / why). A silent `[~]` with no recorded rationale is a finding — surface it as a review-pass blocker. See `170-plan-feature.prompt.md` "AC and task checkbox states — the `[~]` marker" for the canonical convention.
6. Record all findings in the wave record `## Review checkpoints`.
7. Blocking findings open a recorded repair cycle; the implementer repairs the affected boundary and each blocking lane independently reverifies it before delivery approval is restored.

## Code Review Specifics (Wavefoundry)

- Framework script changes: verify test coverage in `.wavefoundry/framework/scripts/tests/`
- Seed prompt changes: verify no project-specific guidance was added to generic seeds
- Manifest changes: verify `framework_revision` matches `.wavefoundry/framework/VERSION`

## AC and Task Verification Truth Hierarchy

The change document is the coordination layer, not the authority layer. The source of truth is:

1. Code and tests — actual delivered behavior
2. Review evidence — verification that the behavior exists and is correct
3. Documentation — shared understanding and continuity

Reviewers must not treat checked ACs or tasks as proof of completion. For every required AC, confirm that supporting code, tests, or documented verification exists. If an AC is marked `[x]` but lacks supporting evidence, treat it as incomplete or unverified and record a finding. If an AC or task was intentionally left unchecked, confirm a rationale is recorded in the Progress Log or Review Checkpoints — a silent unchecked item is a gap, not a deferral.

## Required Before Close

All required lanes from readiness must be reconciled in `## Review checkpoints` before **Close wave** can proceed. When Wave Council is enabled, `wave-council-delivery` must also be recorded (a typed approval event on declared waves, projected into `## Review Evidence`; a prose line counts only on legacy waves).

## Memory Capture During Review

Run `memory_propose(wave_id, mode='create')` after the current finding heads
are reconciled. For each evidence-derived candidate, a focused agent must follow
the evidence and current target, state the future action delta, check durability,
canonical overlap, target accuracy, duplicates/contradictions, and confidence,
then call `memory_validate` with promote, retain, reject, or rewrite. This is
bounded memory curation, not another review council; zero-memory waves are valid.
Manually authored conversational lessons may still use
`memory_add(status='candidate', ...)`. Never store raw transcripts, secrets,
or personal facts.

If review concludes that a reconciled `stale`, `superseded`, or `rejected`
record should leave the active corpus, archive it only with an explicit reason.
Require current evidence before confirming archival of a decision, operator
preference, or fragile-file record; age alone is not sufficient.

<!-- wave:executable-review-evidence begin — generated by render_agent_surfaces.py; preserve project-authored content outside this region -->
## Executable review evidence

Follow the canonical **Executable Review Evidence Protocol** in
`.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` for material
approval claims and blocking findings. Exercise the public or registered
path when one exists; keep state/interleaving probes within the protocol's
finite risk-selected budget; record expected versus observed evidence and
honest limitations; and never broaden task authority to run destructive,
external, credential-bearing, or cost-bearing probes.

Do not hand-author canonical JSONL when the lifecycle coordinator exposes
the typed review-evidence authoring surface. Reviewers supply the
load-bearing judgment facts to that coordinator; the authoring surface
derives only bookkeeping, appends the fixed sibling
`docs/waves/<wave>/events.jsonl` authority, and rebuilds the compact
Markdown current-state projection in `wave.md`. A role without lifecycle
mutation authority returns those facts to its coordinator instead of
writing wave state.

Under the current review policy, after validation apply the ordered
four-way actionability gate:
`do_now`, `maybe_later`, `dont_do_later`, or `not_issue`. Complete bounded
`do_now`/`maybe_later` work before closure, create no backlog for rejected
states, and use focused repair replay unless a load-bearing boundary change
objectively requires a full council.

Repair/reverification independence is enforced chain-aware at the typed
authoring surface: a reverification sharing its `repair_start`'s context
while declaring `fresh_context=true` is rejected as a contradiction
(`reverification_context_not_fresh`), and a same-actor reverification is
rejected as protocol policy (`reverification_actor_not_distinct`); both
append nothing. The close gate audits open and reopened waves' current
chains (`review_evidence_independence_invalid`); closed archives are never
retroactively invalidated. Actor equality is protocol policy, not caller
authentication — the truth of `fresh_context`, `independent`, and actor
identity itself remains a declaration the validator cannot verify.
<!-- wave:executable-review-evidence end -->

<!-- wavefoundry:review-policy:begin -->
## Review-policy delivery

Review Wave consumes the shared delivery evaluator selected by the current
review-policy receipt. After a repair, search the same root cause and adjacent
repair class before focused reverification; broaden review only when a
load-bearing boundary changed.
<!-- wavefoundry:review-policy:end -->
