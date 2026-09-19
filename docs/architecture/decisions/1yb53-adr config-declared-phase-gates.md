# 1yb53-adr — Config-declared phase gates

Owner: Engineering
Status: accepted
Last verified: 2026-09-18

## Context

Projects need additional prepare or close checks without forking lifecycle handlers. Automatically importing repository policy modules would execute project code when an agent host loads the server.

## Decision

Accept optional typed `phase_gates` configuration naming existing sensors for prepare and close. Validate the same schema in docs lint and lifecycle preparation. Execute required list-form commands only during mutating phases; read-only previews list `would_run` and do not execute commands. Keep review-lane selection in its existing configuration.

Use named gate functions in static phase tuples, with a data-only context and support readers. A shared bounded subprocess runner preserves captured output and reports failures and elapsed time. Include configured policy and referenced sensors in the readiness digest only when the phase-gate block is nonempty.

## Consequences

Projects gain reviewed, visible checks without importing custom policy Python. Provenance identifies every reached configured gate. Default projects keep their existing policy digests and tool parameter schemas.

Mutating lifecycle calls execute configured project commands with the host environment and repository working directory: prepare `ready`/`create` whenever it reaches its readiness stage, and close `create` only when no blocking diagnostic has accumulated by the time its sensor gate runs. This is deliberate authority, not sandboxing. Commands must be trusted and fast; failures and timeouts block. Dry-run success cannot prove a sensor will pass. Prepare may publish a policy receipt before a required sensor fails, but that receipt is not an approval. Legacy compatibility paths that never reach readiness report no executed gates.

The two mutating phases carry different preconditions, and the difference is narrower than it was. Editing an approved sensor's command rotates the review-policy digest, which makes the recorded readiness approval no longer current, so `council_signoff_gate` emits a blocking `missing_wave_council_signoff` and prepare takes its blocking early return before the readiness gate tuple, where the sensor would execute. Close now gates on the same cause through a different mechanism: a conjunct on its sensor gate's own predicate, evaluated over the diagnostics accumulated before that gate, so a close that is far from closable reports its declared sensors as `would_run` rather than executing them. The mechanisms are not identical and neither is a sandbox: prepare's barrier sits before its readiness tuple, so a blocking diagnostic raised inside that tuple does not withhold its sensor, and close's bound is what the gate stage can see, so two later checks can still fail a close whose sensors already ran. `phase_gates` therefore still carries a trust requirement, and it is unqualified on a legacy prose wave or a wave with no current policy receipt: there the evidence path is inert, nothing binds the command bytes at either phase, and a declared sensor executes on any close that is otherwise clean. Treat the key as executable content under review, not as configuration that is inert until a wave is ready.

> **Amended 2026-09-18 by wave `1yd97 phase-gate-follow-ups` (`1yd98-enh`).** The operator chose to give close the precondition this record described it as lacking. The Decision is unchanged; the Consequences section is corrected in place. Superseded wording, preserved verbatim.
>
> Second paragraph opening sentence: "Mutating lifecycle calls now execute configured project commands with the host environment and repository working directory."
>
> Third paragraph, in full: "The two mutating phases carry different preconditions, and the difference is deliberate. Prepare's readiness stage runs only under typed authority or a present and valid council verdict, so the digest binding over declared sensors means an unreviewed edit to a sensor command lapses the approvals and the command does not execute. Close carries no equivalent precondition: its blocking predicate is evaluated after every gate has run, so `wf_close_wave` in `create` (or its `apply` alias) executes the declared close sensors even on a wave that is far from closable, including one whose approvals are absent or whose review evidence is invalid. That ordering is what lets an operator see sensor results beside the other blockers in a single pass rather than one gate at a time. The cost is that the digest binding is a real control on prepare only. `phase_gates` therefore carries the same trust requirement as a commit hook: anything a project declares there runs on the close path on every `create` or `apply` attempt that reaches the gate stage, so treat the key as executable content under review, not as configuration that is inert until a wave is ready."

## Alternatives Considered

| Alternative | Reason rejected |
| --- | --- |
| Discover repository Python policy modules | Executes repository code implicitly during server loading |
| Configure an imported policy-module path | Adds containment and import complexity while retaining code-execution exposure |
| Add `required_lanes` to phase gates | Duplicates existing lane policy without owning lane selection |
| Execute sensors during dry-run | Breaks the read-only contract |

## References

- [Configuration contract](../cross-cutting-concerns.md#configured-phase-gates)
- [Wave 1y0h0](../../waves/1y0h0%20typed-phase-gates/wave.md)
- [Wave 1yd97](../../waves/1yd97%20phase-gate-follow-ups/wave.md) — amends the Consequences section
