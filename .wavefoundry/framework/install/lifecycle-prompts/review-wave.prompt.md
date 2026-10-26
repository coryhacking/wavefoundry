# Review Wave

Owner: Engineering
Status: active
Last verified: {{generated_at}}

Shortcut: **`Review wave`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-change.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose reviewer models and effort for the actual review risks. Read the existing scope, fingerprint, commands/results, findings and next action; independently verify the current tree. A host change does not itself establish independence. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

In existing readiness and delivery reviews, ask whether meeting Requirements and ACs would establish Product Intent and the wave Objective, and whether added complexity, runtime cost or operator burden undermines that outcome. At delivery, distinguish evidenced outcomes from intended benefits; checked implementation steps alone prove neither benefit nor approval. Use the existing lanes and gates.

Evaluate the implemented wave against its acceptance criteria, public
contracts, failure modes, and current repository state.

Review wave is the delivery phase; readiness review already ran at Prepare.
Start with `wf_review_wave(wave_id, phase='implementation')` when available.
Every required-lane approval comes from a reviewer context started for delivery
review. A context retained from readiness, inventory, a non-delivery checkpoint
pass or repair may return findings and evidence but records no approval.
Without the typed tool, return judgment facts to the coordinator and never
hand-edit the ledger. Legacy prose waves retain their recording contract.
Brief each lane using seed 209's **Briefing Packet**, including
`tree_fingerprint`, `time_budget` and `sweep_rule`.

## Review method

1. Review the actual diff and current tree, not the implementation summary.
   All review, repair, and reverification investigation follows the run
   contract's Retrieval Rules (`seed-020`): MCP retrieval tools first, for
   every lane and briefed subagent; executed probes remain shell work.
2. Reproduce material claims through public or registered paths where safe.
3. Use an independent reference for changed behavior and state the common-mode
   limitations of that reference.
4. Classify every finding through the canonical action matrix: `do_now`,
   `maybe_later`, `dont_do_later`, or `not_issue`.
5. Record executable evidence and finding synthesis through the typed evidence
   tool when available.
6. A newly discovered finding may be recorded, started, repaired, and
   reverified in the same open repair cycle. Do not stop merely because an
   earlier review pass already ran. After the first delivery cycle, an
   editorial-only finding (wording that is true but imprecise, drifted
   citations, formatting) is repaired inline in the current cycle and recorded
   in the Progress Log; it does not by itself open another repair cycle. Every
   finding that needs verification, a boundary repair, or escalation retains
   its existing action-matrix route. An editorial finding that makes a shipped
   claim FALSE is a correctness defect. A scope, requirement, or AC change is
   recorded in the section that owns it, and the Progress Log row points at
   that edit rather than substituting for it.
7. Re-run only affected lanes for bounded repairs unless a load-bearing
   boundary objectively requires a full council.
8. After current finding heads are reconciled, run
   `memory_propose(wave_id, mode='create')`. For each evidence-derived
   candidate, follow the evidence and current target, state the future action
   delta, check canonical overlap and confidence, then record `promote`,
   `retain`, `reject`, or `rewrite` with `memory_validate`. This is a
   focused curation pass, not another council; zero-memory waves are valid.

## Required review and acceptance checks

- `code-reviewer` is not optional when required by readiness or project policy,
  or when the change touches non-trivial product logic. Include branch-complete
  and re-entrant checks for affected per-key mutable state. QA verifies state
  across repeated calls or routine steps, or records deferral and residual risk.
- On every delivery review, the coordinator first drafts one `Intent outcome:`
  paragraph, prefixed `YYYY-MM-DD: `, in the existing exact `## Review Checkpoints`
  section (never a second such section): achieved, partial or not established, citing
  the delivery evidence, the plan's measure of success when one exists, and material
  limitations. Assign the independent check to `qa-reviewer` when it is in the current
  required delivery roster; otherwise assign one reviewer already in that roster. If the
  roster is empty, record `No independent delivery-lane intent check ran` in `## Review
  Checkpoints`; do not add a lane or claim an independent check occurred. The assigned
  reviewer independently confirms or corrects whether the delivered work achieves each
  admitted change's Product Intent and the wave Objective, citing delivery evidence and
  material limitations, whether or not delivery Council is required. A correction
  showing unachieved intent is a typed finding under seed 209; a wording-only correction
  is editorial. The coordinator incorporates corrections before close.
- Run delivery Council when the current receipt-derived `required_council_signoffs`
  lists `council-delivery`. The council declares primer depth, runs
  the isolated red-team primer first, briefs fixed seats with it, and synthesizes
  their findings. Record the seat roster, rotating fifth seat when present,
  disagreements and their disposition in the narrative review checkpoint.
  The council-chair's `intent_fit` judges the same draft using the assigned reviewer's assessment when available
  (seed 215); the coordinator revises a corrected draft
  before close. The typed `council-delivery` approval records the confirmed
  verdict as `evidence.intent_fit` (`establishes`, `partially` or
  `does_not`); a `does_not` verdict does not block, and Review and Close show
  it to the operator before sign-off.
- Perform one bounded AC scope gap check: confirm required ACs are met, surface
  valuable important/nice-to-have items outside admitted scope for operator
  disposition, and confirm not-this-scope deferrals.
- When an admitted change carries an AC priority table, reconcile it against
  delivered behavior. `qa-reviewer` attests every required row has verification
  evidence or a recorded deferral; record that reconciliation before closure.
- Verify every `[~]` AC has a legitimate inline note naming when, who and why;
  a silent marker is a blocking review finding under seed 170's checkbox rules.

## AC and Task Verification Truth Hierarchy

The change document coordinates work; it does not prove completion. Prefer:

1. Code and tests: actual delivered behavior.
2. Review evidence: verification that the behavior exists and is correct.
3. Documentation: shared understanding and continuity.

For every required AC, verify supporting code, tests or documented verification.
A checked AC or task without evidence is incomplete or unverified and needs a
finding. An intentionally unmet item needs a recorded rationale; silence is not
an accepted deferral.

## Project review specifics

## Approval

Approval requires current, lane-authorized evidence after every repair that
affects that lane. Implementer-authored verification can prove behavior but is
not independent delivery approval. Keep operator signoff pending until the
operator explicitly supplies it.

Review wave ends when every required lane and any receipt-required council
approval is current in `wf_review_wave`. It does not close the wave, mark
completion or commit changes.

## Focused readiness re-review

For stale readiness, use the guided review actions and seed 209’s **Focused readiness re-review**. Compare cumulatively from each lane’s last approved receipt, with its prior approval/evidence, changed sections and a verified normalized before/after delta when available; provide the full amended plans and affected dependency context, and ask whether the change alters the verdict. Newly required lanes perform normal initial review. Exact raw receipt snapshots under `.wavefoundry/work/<wave-id>/receipts/` are optional aids, never approval authority. Missing legacy metadata, missing/corrupt/cleaned snapshots, stale inputs, incompatible normalization or truncated output must be explicit; obtain full text or fall back to normal full review. Reads create no snapshots. Receipt identity, required lanes, approval invalidation and deferral rules are unchanged; no approval transfers or measured effort savings are implied.

## Disposable wave work

Use the lifecycle-reported `.wavefoundry/work/<wave-id>/`, keyed by the resolved unique prefix, for shared temporary work; include the path and availability notices in coordinator briefs. Follow seed 180’s **Disposable wave work** and seed 209’s **Review Artifact Discipline**. Reads and dry-runs create nothing; unavailable work is advisory and existing host permissions apply. Receipt copies and review notes are disposable aids; preserve unique proof before final evidence and keep durable approval authority in its existing records.
