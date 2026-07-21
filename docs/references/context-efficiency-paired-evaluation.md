# Context Efficiency Paired Evaluation Protocol

Owner: Engineering
Status: active
Last verified: 2026-07-20

The measured Context Efficiency ledger counts only deterministic quantities:
files demonstrably read or written, request and response sizes, workflow
prompts served. What it deliberately never counts is the counterfactual —
"what would the agent have spent without the tool." That quantity is real but
unmeasurable from a single run, so it is admitted through exactly one channel:
a quality-gated paired evaluation whose scored residual
(`matched_pair_residual`) joins the wave snapshot. This document is the
protocol for producing one.

## The flow

1. **Register** the evaluation scope:
   `wf_context_efficiency_eval(wave_id=..., phase_id=..., mode='register',
   applicability={...})`. Applicability pins the eight identity keys (wave,
   phase, stage, task-spec digest, repository snapshot digest, model id and
   version, tool-configuration digest) so a result can never silently apply to
   a different context than it was measured in.
2. **Scaffold** the artifact:
   `wf_context_efficiency_eval(wave_id=..., phase_id=..., mode='scaffold',
   report_path='docs/waves/<wave>/pairs.json')`. The skeleton's shape is
   derived from the scorer's own canonical constants — applicability prefilled
   from the registered scope, the minimum number of pair entries, every arm
   field present. Placeholder values are deliberately invalid: an unfilled
   scaffold is rejected by the scorer, so a scaffold can never accidentally
   qualify.
3. **Run the pairs.** Each pair is one matched task executed twice:
   - **baseline arm**: the task performed without the Wavefoundry MCP surface
     (retrieval by manual reading, state inspection by shell, records authored
     by hand);
   - **assisted arm**: the same task with the full tool surface.
   Both arms record `input_tokens`, `output_tokens`, and `tool_calls` from
   provider-reported usage (`usage_source: "provider_reported"` is the only
   accepted value — never self-estimated numbers), plus whether the task
   `completed`.
4. **Score quality blind.** Each arm's output is scored 0–4 on correctness,
   completeness, evidence, and maintainability by a judge who does not know
   which arm produced it (`quality_scored_blind: true` is asserted per arm). A
   pair only qualifies when the assisted arm's quality is at least the
   baseline's on every dimension and both arms completed — savings bought by
   worse output never count.
5. **Fill and attach**: put the measured numbers into the scaffold, set a
   unique `evaluation_id` and `pair_id`s, record each assisted run's
   `assisted_direct_net` (the ledger's measured direct net for that run, so
   the residual never double-counts what the ledger already claims), then
   `wf_context_efficiency_eval(mode='attach', report_path=...)`. The scorer
   validates the artifact, requires at least 5 qualifying pairs, and takes the
   MINIMUM residual across qualifying pairs — the most conservative
   generalization the data supports.

## What the residual means

For each qualifying pair, `residual = max(0, (baseline total tokens − assisted
total tokens) − assisted_direct_net)`: the token advantage of the assisted arm
beyond what the measured ledger already credits. The attached
`matched_pair_residual` is the minimum such residual over qualifying pairs.
It appears as a separate component in the wave's Context Efficiency snapshot
and is the ONLY sanctioned counterfactual contribution to
`estimated_tokens_saved`.

## Boundaries

- Running the baseline arm is operator or harness work. The framework
  validates, scores, and attaches; it does not execute agents.
- A scaffold whose placeholders are unedited never attaches (the scorer
  rejects it); partial fills fail closed.
- Replacing an attached evaluation uses `mode='replace'` with
  `supersedes_evaluation_id` set; `mode='revoke'` withdraws the residual.
- The quality gate is not tunable per wave: 5 qualifying pairs, blind scoring,
  and provider-reported usage are floors, not defaults.

See `docs/references/context-efficiency.md` for the measured ledger this
protocol complements.
