# Estimated exploration avoided

Owner: Engineering
Status: active
Last verified: 2026-07-20

## What this is (and is not)

Wavefoundry measures retrieval token savings honestly in the per-wave
`## Context Efficiency` block: for each content-bearing retrieval call it counts
the whole-file bytes of the cited sources minus the request and response bytes,
per-phase-deduped and zero-clamped. That measured number deliberately EXCLUDES
the memory layer's largest real value: a surfaced memory advisory that prevents a
costly re-exploration (a 20k-to-100k-token re-derivation of something already
learned). That value is a counterfactual, and folding it into the measured
number as if it were a per-call token would rebuild an inflatable gauge.

"Estimated exploration avoided" is a SEPARATE, explicitly-labeled ESTIMATE that
keeps that value visible without faking a measurement. It is honest because it is
grounded in a MEASURED quantity and is credited only on a real event.

## The formula

When a memory advisory is actually surfaced in an exact matching context (via
`wave_memory_brief` or a passive code/lifecycle advisory), each surfaced record
that carries a measured
`Source exploration cost:` contributes:

```
credit_per_record = source_exploration_cost x attribution_factor
attribution_factor = ATTRIBUTION_BASE x exact_match
```

- `source_exploration_cost` is the MEASURED consumed-token cost of the wave that
  produced the record (its current SQLite `request_debit + response_debit`,
  falling back to the closed wave projection only when no live row exists),
  stamped on the record when it is proposed.
  It is a measured number, never a hardcoded constant, so the estimate cannot
  inflate with corpus size.
- `ATTRIBUTION_BASE` is bounded WELL below 1.0: `0.5` for a surfaced advisory,
  `0.75` for an explicitly-cited one. A merely-surfaced advisory is discounted
  harder than a cited one because surface is not proof of use.
- `exact_match` is `1.0` only when the record matched the requested file,
  symbol, community, wave, or change identifier. An unmatched advisory earns
  zero until a real semantic confidence model exists.

The per-wave estimate is the sum of the bounded credits in the existing
`.wavefoundry/logs/context-efficiency.sqlite` authority. Events are keyed by
receiving wave, stage, phase, source origin, memory ID, normalized target
context, and surfaced/cited state. Repeating the same event in a phase is
idempotent. All records produced by the same source wave share one receiving-
phase budget: record multiplication cannot exceed `50%` of that source wave's
measured cost for surfaces (`75%` when cited evidence exists). A new receiving
phase may earn new credit because it represents a new review/repair context.

## Invariants

- **Grounded, never a constant.** The unit is the record's measured source cost.
- **Event-triggered.** Credit accrues only on an actual advisory-surface event,
  never because records exist, so it cannot grow with corpus size.
- **Bounded and deduplicated.** The attribution factor is fixed and well below
  1.0; a source-origin budget and phase/context event key prevent repeated
  advisories or record multiplication from inflating it.
- **Separate, never summed.** It shares SQLite durability with Context
  Efficiency but uses a distinct table and projection block. It surfaces under
  its own label (`estimated_exploration_avoided` on `wave_current` /
  `wave_audit`, plus `## Estimated Exploration Avoided` in `wave.md`) and is
  NEVER added to the measured `## Context Efficiency` token total.
- **Surfaced vs cited, recorded distinctly.** `surfaced_events` and
  `cited_events` are tracked separately; surface is discounted for the gap.
- **Telemetry-only.** It never affects retrieval, ranking, gating, or the
  advisory surface itself. A credit failure is swallowed and changes nothing.

## The mandatory caveat

Every surfacing of the number carries this caveat:

> estimated: a surfaced (or cited) advisory does not prove a re-exploration was
> avoided; this is grounded in the measured cost of the original exploration,
> scaled by a bounded exact-match attribution, and is NEVER summed into the
> measured Context Efficiency token total.

## Measurement-grade alternative (out of scope)

A rigorous with-brief / without-brief paired evaluation (running the same task
twice and comparing provider token counts) would measure the avoidance directly.
It is heavy and rarely runnable per wave, so it is out of scope here; this
grounded estimate is the always-available approximation, and the paired
evaluation remains the only measurement-grade path.
