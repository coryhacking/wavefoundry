# Review Wave

Owner: Engineering
Status: active
Last verified: {{generated_at}}

Shortcut: **`Review wave`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose reviewer models and effort for the actual review risks. Read the existing scope, fingerprint, commands/results, findings and next action; independently verify the current tree. A host change does not itself establish independence. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

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
- Run delivery Council when the current receipt-derived `required_council_signoffs`
  lists `wave-council-delivery`. The council declares primer depth, runs
  the isolated red-team primer first, briefs fixed seats with it, and synthesizes
  their findings. Record the seat roster, rotating fifth seat when present,
  disagreements and their disposition in the narrative review checkpoint.
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
