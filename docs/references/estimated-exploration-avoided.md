# Estimated exploration avoided

Owner: Engineering
Status: active
Last verified: 2026-07-18

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

When a memory advisory is actually surfaced in a matching context (today: via
`wave_memory_brief`), each surfaced record that carries a measured
`Source exploration cost:` contributes:

```
credit_per_record = source_exploration_cost x attribution_factor
attribution_factor = ATTRIBUTION_BASE x match_confidence
```

- `source_exploration_cost` is the MEASURED consumed-token cost of the wave that
  produced the record (its `request_debit + response_debit` from that wave's
  `## Context Efficiency` telemetry), stamped on the record when it is proposed.
  It is a measured number, never a hardcoded constant, so the estimate cannot
  inflate with corpus size.
- `ATTRIBUTION_BASE` is bounded WELL below 1.0: `0.5` for a surfaced advisory,
  `0.75` for an explicitly-cited one. A merely-surfaced advisory is discounted
  harder than a cited one because surface is not proof of use.
- `match_confidence` is in `(0, 1]`: `1.0` for a record that matched a requested
  target, `0.25` for one that surfaced without a direct match.

The per-wave estimate is the sum of these credits over the advisory-surface
events during that wave's work, accumulated in a disposable sidecar
(`.wavefoundry/index/exploration-avoided.json`, gitignored, rebuildable).

## Invariants

- **Grounded, never a constant.** The unit is the record's measured source cost.
- **Event-triggered.** Credit accrues only on an actual advisory-surface event,
  never because records exist, so it cannot grow with corpus size.
- **Bounded.** The attribution factor is fixed, documented, and well below 1.0.
- **Separate, never summed.** It lives in its own sidecar and surfaces under its
  own label (`estimated_exploration_avoided` on `wave_current` / `wave_audit`).
  It is NEVER added to the measured `## Context Efficiency` token total.
- **Surfaced vs cited, recorded distinctly.** `surfaced_events` and
  `cited_events` are tracked separately; surface is discounted for the gap.
- **Telemetry-only.** It never affects retrieval, ranking, gating, or the
  advisory surface itself. A credit failure is swallowed and changes nothing.

## The mandatory caveat

Every surfacing of the number carries this caveat:

> estimated: a surfaced (or cited) advisory does not prove a re-exploration was
> avoided; this is grounded in the measured cost of the original exploration,
> scaled by a bounded semantic-match attribution, and is NEVER summed into the
> measured Context Efficiency token total.

## Measurement-grade alternative (out of scope)

A rigorous with-brief / without-brief paired evaluation (running the same task
twice and comparing provider token counts) would measure the avoidance directly.
It is heavy and rarely runnable per wave, so it is out of scope here; this
grounded estimate is the always-available approximation, and the paired
evaluation remains the only measurement-grade path.
