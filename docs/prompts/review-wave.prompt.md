# Review Wave

Owner: Engineering
Status: active
Last verified: 2026-10-26

Shortcut: **`Review wave`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-change.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose reviewer models and effort for the actual review risks. Read the existing scope, fingerprint, commands/results, findings and next action; independently verify the current tree. A host change does not itself establish independence. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

In existing readiness and delivery reviews, ask whether meeting Requirements and ACs would establish Product Intent and the wave Objective, and whether added complexity, runtime cost or operator burden undermines that outcome. At delivery, distinguish evidenced outcomes from intended benefits; checked implementation steps alone prove neither benefit nor approval. Use the existing lanes and gates.

Run all required review lanes against the admitted changes. Review is not optional when required lanes were confirmed at readiness. Review wave is the delivery phase, started with `wf_review_wave(wave_id, phase='implementation')`; readiness review already ran at Prepare.

## Steps

All review, repair, and reverification investigation follows the run contract's Retrieval Rules (`.wavefoundry/framework/seeds/020-run-contract.prompt.md`): MCP retrieval tools first, for every lane and briefed subagent; executed probes remain shell work.

1. Read the wave record and each admitted change doc; confirm which review lanes were required at readiness.
2. On every delivery review, the coordinator first drafts one `Intent outcome:` paragraph, prefixed `YYYY-MM-DD: `, in the existing exact `## Review Checkpoints` section (never a second such section): achieved, partial or not established, citing the delivery evidence, the plan's measure of success when one exists, and material limitations. Assign the independent check to `qa-reviewer` when it is in the current required delivery roster; otherwise assign one reviewer already in that roster. If the roster is empty, record `No independent delivery-lane intent check ran` in `## Review Checkpoints`; do not add a lane or claim an independent check occurred. The assigned reviewer independently confirms or corrects whether the delivered work achieves each admitted change's Product Intent and the wave Objective, citing delivery evidence and material limitations, whether or not delivery Council is required. A correction showing unachieved intent is a typed finding under seed 209; a wording-only correction is editorial. The coordinator incorporates corrections before close.
3. Run each required lane:
  - `code-reviewer` — correctness, pattern compliance, branch completeness, re-entrant safety for mutable state
  - `qa-reviewer` — AC coverage, multi-step verification for stateful behavior
  - `architecture-reviewer` — boundary and layering impact
  - Other lanes as required per `docs/contributing/review-and-evals.md`
  - Brief every lane with the seed-209 packet fields `tree_fingerprint` (`git hash-object` over the reviewed paths), `time_budget`, and `sweep_rule` (targeted tests per mutant, whole-file runs only for survivors), and require a mutation table in each report (wave `1wuju`).
  - **Frozen tree per round:** no edit lands under the reviewed paths while a lane runs; collect every lane's findings, repair once, re-snapshot once, and re-brief with a new fingerprint. A lane that finds the fingerprint changed records `tree_moved_under_review` (seed 209). Neither `frozen_boundary` nor `policy_input_digest` freezes code; a repair landed while a lane is still running invalidates that lane's evidence for the paths it touched. Each lane reports at its `time_budget` with what is in hand and lists what was not run.
4. When the current receipt-derived `required_council_signoffs` lists `council-delivery`, run the Wave Council delivery pass in two phases: first, the `council-chair` declares a **primer depth tier** (`lightweight` / `standard` / `full`) based on trust boundaries touched, files in scope, and change type; (1) `red-team` runs the adversarial primer (`council-adversarial-primer` mode) first at the declared depth — strongest challenge, best alternative, `primer_questions`, and an `efficacy_replay` of each change's motivating case through its mechanism; (2) fixed seats each receive the standard briefing plus the primer and must address it, including the `efficacy_replay`, before producing findings; rotating fifth seat finds the strongest unconsidered alternative; `council-chair` synthesizes all outputs; record `council-delivery` (on declared waves as a typed approval event via `wf_review_event`, which projects into `## Review Evidence`; only legacy prose waves record the signoff line directly) and summarize the reasoning in `## Review Checkpoints`. The checkpoint must include the seat roster, the rotating fifth seat, any material disagreements, and how they were resolved or why they remain unresolved. Delivery review verifies the current typed readiness authority on declared waves; it does not treat a prose `prepare-council` checkpoint as machine evidence. Legacy waves retain their prose compatibility contract. The council-chair's `intent_fit` judges the same draft using the assigned reviewer's assessment when available (seed 215); the coordinator revises a corrected draft before close. The typed `council-delivery` approval records the confirmed verdict as `evidence.intent_fit` (`establishes`, `partially` or `does_not`); a `does_not` verdict does not block, and Review and Close show it to the operator before sign-off.
5. **AC scope gap check:** when the change doc carries an `## AC Priority` table, after confirming required ACs are met, surface important/nice-to-have items not in admitted scope; confirm not-this-scope deferrals.
6. **AC priority reconciliation:** when the change doc carries an `## AC Priority` table, reconcile it against delivered behavior; update if scope shifted; `qa-reviewer` must attest every required row has verification evidence or a recorded deferral. **`[~]` AC verification:** for every AC marked `[~]` (intentionally not met), `qa-reviewer` confirms the inline status note is present and legitimate (names when / who / why). A silent `[~]` with no recorded rationale is a finding — surface it as a review-pass blocker under seed 170's "AC and task checkbox states — the `[~]` marker" convention.
7. Record findings and approvals through `wf_review_event`; the wave record `## Review Checkpoints` keeps the narrative summary. Legacy prose waves retain their recording contract.
8. Blocking findings open a recorded repair cycle. The implementer repairs the affected boundary and each blocking lane independently reverifies it before delivery approval is restored. After the first delivery cycle, an editorial-only finding (wording that is true but imprecise, drifted citations, formatting) is repaired inline in the current cycle and recorded in the Progress Log; it does not by itself open another repair cycle. Every finding that needs verification, a boundary repair, or escalation retains its existing action-matrix route. An editorial finding that makes a shipped claim FALSE is a correctness defect. A scope, requirement, or AC change is recorded in the section that owns it, and the Progress Log row points at that edit rather than substituting for it.

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

All required lanes must have current typed delivery approvals before **Close wave** can proceed, with the narrative summary in `## Review Checkpoints`. When the current receipt-derived `required_council_signoffs` lists `council-delivery`, that approval must also be current (a typed approval event on declared waves, projected into `## Review Evidence`; a prose line counts only on legacy waves).

Review wave does not close the wave, mark completion or commit changes; those actions remain operator-owned.

## Memory Capture During Review

Follow `docs/prompts/memory-review.prompt.md` for evidence-derived candidate curation after current finding heads are reconciled.
Conversational lessons may use `memory_add(status='candidate', ...)` under that workflow's evidence and privacy rules.

<!-- wave:executable-review-evidence begin — generated by render_agent_surfaces.py; preserve project-authored content outside this region -->
## Executable review evidence

Follow the canonical **Executable Review Evidence Protocol** in
`.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` for material
approval claims, blocking findings, review policy and focused repair.
Exercise the public or registered
path when one exists; keep state/interleaving probes within the protocol's
finite risk-selected budget; record expected versus observed evidence and
honest limitations; and never broaden task authority to run destructive,
external, credential-bearing, or cost-bearing probes.

Start delivery review with `wf_review_wave(phase='implementation')` and
record findings and approvals through `wf_review_event`; never hand-edit
`events.jsonl`. Reviewers supply the load-bearing judgment facts to the
coordinator; a role without lifecycle mutation authority returns those
facts to its coordinator instead of writing wave state.

The tools enforce `reverification_context_not_fresh`,
`reverification_actor_not_distinct`, and `review_evidence_independence_invalid`
for decidable independence contradictions as protocol policy, not caller
authentication.
<!-- wave:executable-review-evidence end -->

<!-- wavefoundry:review-policy:begin -->
## Review-policy delivery

Review Wave consumes the shared delivery evaluator selected by the current
review-policy receipt. After a repair, search the same root cause and adjacent
repair class before focused reverification; broaden review only when a
load-bearing boundary changed.

Check authoring routes: test observations, repair progress, evidence locations
and continuation notes belong in the canonical `## Progress Log` or existing
session handoff; weighed plan choices and material decisions stay in
`## Decision Log`. A change to scope, requirements, acceptance, task meaning,
priority, review targets or authority must amend its owning digested section
before or with narration. The log may link or summarize that edit, never
substitute for it; material edits require the existing re-Prepare and affected
readiness approval steps. Legitimate material decision receipt rotation is
intentional.

For example, "Reran tests on Windows; repair passed" is Progress Log narration.
Changing who may approve a release artifact amends Requirements and any owning
review targets or authority section, with a weighed design choice in Decision
Log when needed. Review the owning amendment and its affected approvals.
Guidance and existing review enforce this discipline; they do not automatically
discover semantic amendments hidden only in narration. Use the canonical heading;
unsupported or ambiguous Progress Log headings may remain digested.
<!-- wavefoundry:review-policy:end -->

## Focused readiness re-review

For stale readiness, use the guided review actions and seed 209’s **Focused readiness re-review**. Compare cumulatively from each lane’s last approved receipt, with its prior approval/evidence, changed sections and a verified normalized before/after delta when available; provide the full amended plans and affected dependency context, and ask whether the change alters the verdict. Newly required lanes perform normal initial review. Exact raw receipt snapshots under `.wavefoundry/work/<wave-id>/receipts/` are optional aids, never approval authority. Missing legacy metadata, missing/corrupt/cleaned snapshots, stale inputs, incompatible normalization or truncated output must be explicit; obtain full text or fall back to normal full review. Reads create no snapshots. Receipt identity, required lanes, approval invalidation and deferral rules are unchanged; no approval transfers or measured effort savings are implied.

## Disposable wave work

Use the lifecycle-reported `.wavefoundry/work/<wave-id>/`, keyed by the resolved unique prefix, for shared temporary work; include the path and availability notices in coordinator briefs. Follow seed 180’s **Disposable wave work** and seed 209’s **Review Artifact Discipline**. Reads and dry-runs create nothing; unavailable work is advisory and existing host permissions apply. Receipt copies and review notes are disposable aids; preserve unique proof before final evidence and keep durable approval authority in its existing records.
