# Context Efficiency Turn-End and Quiet-Period Projection

Change ID: `1tsjh-enh context-efficiency-turn-end-projection`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-27
Wave: `1tskc context-efficiency-projection-freshness`

## Rationale

Context Efficiency events are already written through to the host-local SQLite authority, but the
portable `wave.md` checkpoint is normally refreshed only at lifecycle, MCP reload, and upgrade
boundaries. During a long implementation or review period, the durable numbers can therefore be
current while the project-visible wave record remains stale for many turns.

Refresh the projection opportunistically after a turn and after a bounded period without new
telemetry. The new triggers are visibility improvements only: they must not change attribution,
credits, debits, phase semantics, close sealing, or the existing hard publication barriers.

## Requirements

1. Preserve `.wavefoundry/logs/context-efficiency.sqlite` as the immediate write-through authority.
   Automatic projection changes only when durable totals become visible in `wave.md`; it does not
   alter any Context Efficiency calculation, source-credit deduplication, attribution, or phase rule.
2. Provide one canonical, root-bound pending-projection operation used by lifecycle/reload/upgrade,
   the turn-end adapter, and the background safety net. It must reuse the project-global publication
   lock, re-read SQLite and `wave.md` after acquiring the lock, atomically replace only the owned
   checkpoint region, and retain the generation compare-and-set behavior.
3. The automatic operation is accounting-neutral. It must not record a tool-cost event, increment a
   Context Efficiency generation because of its own response, change process focus, transfer a
   general bucket, advance a stage, or expose a metered public-tool feedback loop.
4. On hosts with a verified native turn-end event, use that event as the primary prompt projection
   opportunity. The initial rendered integration is Claude Code's existing main-session `Stop` path;
   do not invent hook files or contracts for hosts without verified native support.
5. The turn-end adapter is fail-safe and non-blocking. Lock contention, missing state, corrupt state,
   or projection failure must leave the durable generation pending for retry, exit successfully, and
   never delay or reject completion of the host turn. Keep projection separate from the existing
   session-capture hook's capture-only responsibility, even when both use the same host event.
6. Add an in-process background safety net that works independently of native hook availability and
   independently of the indexing monitor's enabled state. It observes pending `(wave_id, generation)`
   values and attempts projection only after the same generation has remained unchanged for the full
   quiet period. It is a daemon/scheduler owned by the MCP process, not an installed user-home daemon
   or another platform-specific artifact.
7. Default the quiet period to **120 seconds without a generation change**. Expose
   `context_efficiency.projection.quiet_period_seconds` in project workflow configuration, clamp
   values below 90 seconds to 90, and allow values through 600 seconds so operators may choose a
   several-minute delay. Polling must be cheap and must not rewrite `wave.md` on every poll.
8. If a new event advances the generation before publication, restart the quiet-period observation.
   If it advances while a projection is in flight, the older projection must not mark the newer
   generation published; the newer generation remains pending for the next opportunity.
9. Multiple MCP processes, overlapping turn-end adapters, and lifecycle writers may attempt the same
   projection. They must converge on the latest durable generation without losing telemetry or
   project-authored `wave.md` prose. A process that finds no pending generation, loses the race, or
   renders byte-identical output performs no file replacement.
10. Preserve existing lifecycle, review-boundary, close, reload, and upgrade publication behavior as
    hard barriers. Automatic failures are retryable and must not weaken close sealing, compaction,
    reload refusal, upgrade refusal, or accounting-gap failure semantics.
11. Ship the background behavior first-class on native Windows, WSL2, macOS, and Linux. Any hook
    launcher changes use the committed, platform-neutral launcher strategy and existing root-owner
    contract; no generated artifact may contain render-host-specific absolute paths.
12. Document the new projection cadence, configuration, supported hook coverage, failure semantics,
    and the distinction between durable accounting and the portable Markdown checkpoint.

## Scope

**Problem statement:** Durable Context Efficiency accounting can remain absent from or stale in
`wave.md` until the next lifecycle boundary, which makes the visible record lag during long-running
implementation and review work.

**In scope:**

- A handler-independent canonical pending-projection entry point shared by synchronous and automatic
  callers.
- A Claude Code turn-end adapter using the existing verified `Stop` event without changing the
  session-capture responsibility.
- A cross-host MCP-process quiet-period safety net with a 120-second default and generation-based
  trailing-edge behavior.
- Workflow configuration parsing and documentation for the bounded quiet-period setting.
- Concurrency, generation-race, failure, performance, portability, and no-op regression coverage.
- Reconciliation of Context Efficiency reference/spec/architecture documentation and platform
  mapping where the new trigger coverage is described.

**Out of scope:**

- Changing Context Efficiency formulas, token estimation, source credit, debit, neutral-repeat,
  attribution, phase, or paired-evaluation policy.
- Replacing SQLite with `wave.md` as the live authority.
- Removing or relaxing lifecycle, close, reload, or upgrade projection barriers.
- Inventing native end-turn contracts for Cursor, Copilot, Windsurf, Junie, Codex, Air, Warp, or
  Antigravity where Wavefoundry has not verified one.
- A user-home service, always-running external daemon, network service, or untracked installation
  state.
- Automatically committing projected changes.

## Acceptance Criteria

- [ ] AC-1: An eligible measured event is durable immediately, marks its wave generation pending,
  and produces exactly the same stage and total calculations before and after automatic projection.
- [ ] AC-2: On the verified Claude turn-end path, one pending generation is projected through the
  canonical operation; a busy publication lock or injected projection failure returns promptly,
  exits successfully, and leaves the generation pending.
- [ ] AC-3: With no native turn-end signal, a pending generation is not projected before 120 seconds
  of unchanged observation by default, is projected on the first eligible poll afterward, and has its
  quiet clock restarted whenever the generation changes.
- [ ] AC-4: Configuration tests prove the 120-second default, the 90-second lower clamp, acceptance
  through 600 seconds, and graceful fallback on missing or invalid configuration.
- [ ] AC-5: A race that commits a newer event during projection cannot publish that newer generation
  under the older snapshot; the next automatic or hard-boundary attempt publishes it.
- [ ] AC-6: Two independent MCP processes and an overlapping lifecycle writer converge without lost
  events, duplicate credit, corrupted markers, or lost project-authored prose.
- [ ] AC-7: The automatic projection path creates no telemetry event, credit, debit, focus mutation,
  phase mutation, general-bucket transfer, or self-perpetuating pending generation.
- [ ] AC-8: When no generation is pending or the rendered checkpoint is byte-identical, `wave.md`
  contents and modification time remain unchanged.
- [ ] AC-9: Existing create/prepare/implement/review/pause/reopen/close, reload, and upgrade projection
  tests remain behaviorally unchanged, including failure barriers, close sealing, and compaction.
- [ ] AC-10: The background safety net executes through platform-neutral code on native Windows,
  WSL2, macOS, and Linux; committed hook/config artifacts contain no render-host absolute path and
  unsupported hosts receive no invented native hook surface.
- [ ] AC-11: The quiet-period path remains cheap while idle and under repeated generation changes;
  performance coverage uses contention-tolerant bounds and proves that polling does not write the
  checkpoint or scan the documentation corpus.
- [ ] AC-12: Context Efficiency reference, MCP surface specification, data/control-flow architecture,
  workflow-config reference, and platform hook coverage all describe the shipped trigger hierarchy
  and recovery behavior consistently.

## Tasks

- [ ] Extract or introduce the canonical root-bound pending-projection operation and route existing
  lifecycle/reload/upgrade callers through it without changing their public envelopes.
- [ ] Add generation-observation state and the 120-second trailing-edge background scheduler with
  bounded configuration parsing and clean handler shutdown.
- [ ] Add a dedicated, fail-safe Claude `Stop` adapter for Context Efficiency projection and preserve
  the existing session-capture hook's separate responsibility.
- [ ] Ensure the automatic path is excluded from first-party tool-cost accounting and cannot create a
  projection feedback loop.
- [ ] Add no-op, generation-reset, in-flight-race, lock-contention, multi-process, focus-neutrality,
  closed-wave, and hard-barrier regression tests.
- [ ] Add platform/config rendering tests for native Windows, WSL2/POSIX, macOS, and Linux-compatible
  committed surfaces, including no absolute render-host paths.
- [ ] Add contention-tolerant performance coverage for idle polling and warm projection.
- [ ] Update the Context Efficiency reference, MCP tool-surface specification, workflow-config
  reference, platform mapping, and data/control-flow architecture documentation.
- [ ] Re-render only the canonical platform surfaces affected by the verified Claude hook change and
  validate that operator-authored configuration remains preserved.
- [ ] Run targeted tests, the full framework suite, docs lint, and live post-reload probes for both
  turn-end and quiet-period projection before delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Projection contract and configuration | implementer | — | Own the canonical projector, generation observation, and config boundary. |
| Background safety net | implementer | Projection contract and configuration | Keep it independent of index-monitor enablement and host hooks. |
| Claude turn-end adapter | implementer | Projection contract and configuration | Dedicated fail-safe adapter; no unsupported-host surfaces. |
| Verification | qa-reviewer | All implementation workstreams | Exercise races, no-op behavior, failure recovery, portability, and performance. |
| Contract reconciliation | docs-contract-reviewer | Projection contract and configuration | Reconcile spec, reference, architecture, config, and platform claims. |

## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency.py` and the canonical projection owner — one
  authority for generation, snapshot, publication, and accounting-neutral automatic projection.
- `.wavefoundry/framework/scripts/server_impl.py` — lifecycle barriers, handler monitor lifecycle,
  configuration, and cost-exemption wiring must be reconciled as one control-flow change.
- `.wavefoundry/framework/scripts/render_platform_surfaces.py` and rendered Claude hook/config files —
  canonical-source-first edits followed by bounded re-rendering; never hand-edit generated surfaces.
- `project_state_publication_lock` remains the sole cross-process `wave.md` writer serialization
  boundary; do not introduce a parallel lock or invert lock order.
- Context Efficiency tests share timing and SQLite fixtures; concurrency and performance probes must
  run with isolated roots and contention-aware budgets.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — add automatic projection triggers to the Context
  Efficiency capture/projection path.
- `docs/references/context-efficiency.md` — document live authority, turn-end primary path,
  quiet-period safety net, configuration, and unchanged hard barriers.
- `docs/specs/mcp-tool-surface.md` — update durable accounting/projection and failure contracts.
- `docs/agents/platform-mapping.md` — distinguish verified Claude turn-end coverage from the
  cross-host background safety net and unsupported native-hook surfaces.
- The workflow-configuration reference/schema that owns `context_efficiency.projection` — document
  defaults, bounds, and invalid-value fallback.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required / important / nice-to-have / not-this-scope | |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-27 | Planned as a dedicated wave with a 120-second default unchanged-generation quiet period. | Operator direction and current Context Efficiency projection review. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-27 | Use a verified turn-end trigger plus a generation-stable quiet-period safety net, while retaining all hard lifecycle barriers. | Prompt projection on capable hosts and portable recovery elsewhere provide fresher visibility without making either asynchronous mechanism responsible for durability. | Hook-only was rejected because Wavefoundry has no verified turn-end contract on several supported hosts; timer-only was rejected because it would unnecessarily delay projection where a semantic turn boundary exists. |
| 2026-07-27 | Default to 120 seconds with a 90-second lower bound and configurable values through 600 seconds. | This matches the operator's preference for 90–120 seconds or a few minutes and avoids reacting to normal pauses inside an active turn. | A 20–45 second delay was rejected as too eager; a fixed periodic writer was rejected because it would create tracked-file churn during active work. |
| 2026-07-27 | Make automatic projection accounting-neutral and internal rather than a normally metered MCP call. | A metered projection response could create another debit and pending generation after publishing, producing a feedback loop. | A public metered flush tool was rejected; lifecycle-only projection is the current behavior but leaves long-running wave records stale. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Multiple servers or hooks race to publish the same generation. | Re-read under the shared project publication lock, recheck pending generation, atomically replace the marker, and retain compare-and-set publication. |
| A timer writes during active agent work and creates noisy tracked-file churn. | Require a stable generation for the full quiet period, reset on every generation change, and avoid byte-identical writes. |
| Turn-end lock contention delays or breaks host completion. | Use a non-blocking/bounded attempt, always exit successfully, and leave durable state pending for the safety net or hard barrier. |
| The projection operation records its own debit indefinitely. | Keep it outside normal cost instrumentation or explicitly exempt it; pin zero telemetry mutation in regression tests. |
| Background behavior silently depends on indexing configuration or host support. | Give it its own configuration/lifecycle and verify operation with indexing disabled and without native hook surfaces. |
| A newer event lands between snapshot and publication. | Preserve generation compare-and-set semantics and prove the newer generation remains pending. |
| Platform render introduces machine-specific paths or unsupported hook claims. | Reuse the committed owner-bound launcher contract, scan generated artifacts, and emit only the verified Claude adapter. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
