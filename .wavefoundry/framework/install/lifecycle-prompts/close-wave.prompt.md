# Close Wave

Owner: Engineering
Status: active
Last verified: {{generated_at}}

Shortcut: **`Close wave`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-change.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort for reconciliation and unresolved judgments by task fit. Efficient routine checks do not waive review evidence or explicit operator closure authority. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

Close a delivered wave after implementation, review, documentation, and
handoff state are fully reconciled. Close wave is the only wave close, whatever
the change count.

## Closure checks

All closure-time code and docs investigation follows the run contract's
Retrieval Rules (`seed-020`): MCP retrieval tools first, for every lane and
briefed subagent.

1. Every change is `implemented`, `complete`, or `deferred` with rationale, and
   every AC and task is completed or intentionally deferred with rationale.
   **Close change** (`wf_close_change`) is optional; use it to mark a single
   change `complete` and activate its dependents inside the open wave.
2. Required review lanes and configured council signoffs are current.
3. Change status, wave status, completion date, and chronology agree.
4. Architecture, specifications, public prompts, and release notes reflect the
   delivered behavior.
5. Journals, durable memory candidates, and the session handoff are reconciled.
   Run `memory_propose(wave_id, mode='create')`, then use
   `memory_validate` on every evidence-derived candidate. The validating
   agent follows the linked evidence and current target, states the future
   action delta, checks canonical overlap and confidence, and records
   `promote`, `retain`, `reject`, or `rewrite`. A wave may correctly produce
   zero memories; a missing or pending eligible candidate blocks close.
6. The canonical test suite, docs gate, and relevant packaging checks pass.
7. The context-efficiency checkpoint has been projected from durable telemetry
   when telemetry is available.
8. Run `wf_close_wave(mode='dry_run')` before requesting operator approval.

Before closure, explicitly author one concise `Intent outcome:` paragraph in the existing exact `## Review Checkpoints` section: state achieved, partial or not established, cite evidence, and retain material limitations. When the plan states a measure of success, cite it and say whether it can be read yet. It may cover changes sharing an outcome. The close-summary composer carries the last such paragraph or list item (optionally dated `YYYY-MM-DD: `) into Wave Summary, preserving its text and qualification; do not infer achievement from titles or checked ACs. Legacy records without this assessment remain closable under existing gates and retain their existing summary behavior; this adds no schema or blocking gate.

## Operator authority

Only an explicit operator instruction authorizes `wf_close_wave(mode='create')`
or equivalent apply mode. Passing dry-run, finishing implementation, or asking
for review does not imply closure approval. Commit, tag, push, and release
authority remain separately operator-owned.
