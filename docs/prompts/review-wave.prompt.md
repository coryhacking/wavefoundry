# Review Wave

Owner: Engineering
Status: active
Last verified: 2026-07-20

Shortcut: **`Review wave`**

## Purpose

Run all required review lanes against the admitted changes. Review is not optional when required lanes were confirmed at readiness.

## Steps

1. Read the wave record and each admitted change doc; confirm which review lanes were required at readiness.
2. Run each required lane:
  - `code-reviewer` — correctness, pattern compliance, branch completeness, re-entrant safety for mutable state
  - `qa-reviewer` — AC coverage, multi-step verification for stateful behavior
  - `architecture-reviewer` — boundary and layering impact
  - Other lanes as required per `docs/contributing/review-and-evals.md`
3. When `wave_review.enabled` is true, run the Wave Council delivery pass in two phases: first, the `wave-council` declares a **primer depth tier** (`lightweight` / `standard` / `full`) based on trust boundaries touched, files in scope, and change type; (1) `red-team` runs the adversarial primer (`council-adversarial-primer` mode) first at the declared depth — strongest challenge, best alternative, `primer_questions`; (2) fixed seats each receive the standard briefing plus the primer and must address it before producing findings; rotating fifth seat finds the strongest unconsidered alternative; `wave-council` synthesizes all outputs; record `wave-council-delivery` in `## Review Evidence` and summarize the reasoning in `## Review checkpoints`. The checkpoint must include the seat roster, the rotating fifth seat, any material disagreements, and how they were resolved or why they remain unresolved. When implementation passes through the prepare gate, the review must also be able to verify that the prior prepare-council verdict was structured and machine-readable, not just a freeform marker.
4. **AC scope gap check:** after confirming required ACs are met, surface important/nice-to-have items not in admitted scope; confirm not-this-scope deferrals.
5. **AC priority reconciliation:** reconcile the `## AC priority` table against delivered behavior; update if scope shifted; `qa-reviewer` must attest every required row has verification evidence or a recorded deferral. **`[~]` AC verification:** for every AC marked `[~]` (intentionally not met), `qa-reviewer` confirms the inline status note is present and legitimate (names when / who / why). A silent `[~]` with no recorded rationale is a finding — surface it as a review-pass blocker. See `170-plan-feature.prompt.md` "AC and task checkbox states — the `[~]` marker" for the canonical convention.
6. Record all findings in the wave record `## Review checkpoints`.
7. Blocking findings return the wave to implementation (Level 2 loop).

## Code Review Specifics (Wavefoundry)

- Framework script changes: verify test coverage in `.wavefoundry/framework/scripts/tests/`
- Seed prompt changes: verify no project-specific guidance was added to generic seeds
- Manifest changes: verify `framework_revision` matches `.wavefoundry/framework/VERSION`

## Pre-Implementation Gate Reconciliation

During review, confirm that a `pre-implementation-review: passed` verdict was recorded before the first code edit (in `## Review Checkpoints`). If the gate was skipped or recorded as `blocked` and implementation proceeded anyway, surface it as a finding. When implementation revealed that the pre-mortem missed important risks or information gaps, record a `Reflect:` entry in Progress Log noting what should be added to the pre-implementation checklist before the next similar wave.

## AC and Task Verification Truth Hierarchy

The change document is the coordination layer, not the authority layer. The source of truth is:

1. Code and tests — actual delivered behavior
2. Review evidence — verification that the behavior exists and is correct
3. Documentation — shared understanding and continuity

Reviewers must not treat checked ACs or tasks as proof of completion. For every required AC, confirm that supporting code, tests, or documented verification exists. If an AC is marked `[x]` but lacks supporting evidence, treat it as incomplete or unverified and record a finding. If an AC or task was intentionally left unchecked, confirm a rationale is recorded in the Progress Log or Review Checkpoints — a silent unchecked item is a gap, not a deferral.

## Required Before Close

All required lanes from readiness must be reconciled in `## Review checkpoints` before **Close wave** can proceed. When Wave Council is enabled, `wave-council-delivery` must also be present in `## Review Evidence`.

## Memory Capture During Review

Run `wave_memory_propose(wave_id, mode='create')` after the current finding heads
are reconciled. For each evidence-derived candidate, a focused agent must follow
the evidence and current target, state the future action delta, check durability,
canonical overlap, target accuracy, duplicates/contradictions, and confidence,
then call `wave_memory_validate` with promote, retain, reject, or rewrite. This is
bounded memory curation, not another review council; zero-memory waves are valid.
Manually authored conversational lessons may still use
`wave_memory_add(status='candidate', ...)`. Never store raw transcripts, secrets,
or personal facts.

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

After validation, apply the ordered four-way actionability gate:
`do_now`, `maybe_later`, `dont_do_later`, or `not_issue`. Complete bounded
`do_now`/`maybe_later` work before closure, create no backlog for rejected
states, and use focused repair replay unless a load-bearing boundary change
objectively requires a full council.
<!-- wave:executable-review-evidence end -->
