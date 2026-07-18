# Estimated exploration-avoided — a separate, grounded wave-metric category

Change ID: `1svuk-enh estimated-exploration-avoided-category`
Change Status: `planned`
Owner: framework
Status: planned
Last verified: 2026-07-17

Wave: `1stwm memory-supply`

## Rationale

Wave 1stwj measures per-call retrieval token savings honestly (returned bytes vs whole-file bytes of cited sources). It deliberately excludes the memory layer's biggest real value: a `wave_memory_brief` advisory that prevents a 20-100k-token re-exploration. Both council seats agreed that value cannot be folded into the measured number as a per-call token (it is a counterfactual), and that doing so would rebuild agentmemory's inflatable gauge. But the operator's direction is right that it should not be invisible either — the red-team's sharpest point was that leaving it out lets the measured retrieval number be misread as total system value while the biggest saving contributes zero.

This change adds a SEPARATE, explicitly-labeled ESTIMATE category — "estimated exploration avoided" — that is honest because it is grounded in a MEASURED quantity: the real cost of the exploration that actually happened once and got captured as a memory record (its `source_exploration_cost`, stamped by `1stwk`). It is credited only on a real avoidance event (an advisory surfaced in a matching context), weighted by semantic-match confidence, bounded, and never summed into the measured `## Context Efficiency` total.

## Requirements

1. **Grounded unit, never a constant.** The credit unit is the record's `source_exploration_cost` (the measured cost of the wave/repair-cycle that produced it, stamped at record creation by `1stwk`). No hardcoded per-record constant, no unbounded baseline — this is the structural difference from agentmemory's `count × magic-number` gauge.
2. **Event-triggered, never accrues by existence.** Credit is added only when a memory advisory is actually surfaced in a matching context (via `wave_memory_brief` or the passive advisories attached to `code_read`/`wave_prepare`/etc.), not because records exist. So it cannot inflate with corpus size.
3. **Semantic-match-weighted, bounded attribution.** `estimated_exploration_avoided += source_exploration_cost × attribution_factor`, where `attribution_factor` is bounded well below 1.0 and scaled by the semantic-match confidence between the live context and the record (a strong match to a `failed_attempt` you are about to repeat is a stronger avoidance signal than a weak one). The formula is fixed and documented in the reference doc so it is inspectable, not a black box.
4. **A separate, labeled category — never summed into the measured total.** It is surfaced as its own line/block, distinct from the measured `## Context Efficiency` retrieval savings, and labeled with the explicit causal caveat: *"estimated: a surfaced+cited advisory does not prove a re-exploration was avoided; grounded in the measured cost of the original exploration, scaled by a bounded semantic-match attribution."* It is never added to the measured token number and never presented as billing-exact.
5. **Honest uptake signal.** The trigger is "advisory surfaced in a semantically-matching context." Because surface is not proof of use, the attribution is discounted for that gap; an optional stronger signal (an explicit cite/act marker when a reviewer or agent references the advisory) may raise the attribution when present. The distinction between surfaced and cited is recorded, not blurred.
6. **Telemetry only.** Like 1stwj, this never affects retrieval, ranking, gating, or the advisory surface itself. Disposable, rebuildable, non-authoritative.

## Scope

**Problem statement:** the memory layer's largest real saving (avoided re-exploration) is unmeasurable per call and currently invisible; it needs an honest, grounded, separate estimate so it is neither faked into the measured number nor lost.

**In scope (edited under `framework_edit_allowed`):**
- `.wavefoundry/framework/scripts/server_impl.py` — on advisory surface (brief + passive advisories), compute the semantic-match-weighted credit from the record's `source_exploration_cost`; accumulate per wave/stage in the telemetry sidecar (reusing the 1stwj store); surface a separate labeled "estimated exploration avoided" line on `wave_current`/`wave_audit` and a distinct block in `wave.md` (not inside `## Context Efficiency`).
- Reuse: the `source_exploration_cost` on records (`1stwk`), the advisory surface + `search_docs` semantic-match confidence, and the 1stwj telemetry store/labeling discipline.
- Docs — reference doc for the formula + the causal caveat; a note that it is an estimate, separate from measured savings.
- Tests — grounded-unit (uses measured source cost, not a constant), event-triggered-only (no accrual without a surface event), bounded attribution, separate-category (never summed into the measured total), caveat-labeling, telemetry-only invariance.

**Out of scope:**
- **Folding it into the measured `## Context Efficiency` total** — it is always a separate labeled estimate.
- **Any per-wave token-savings target/AC** — this is an emergent estimate, not a target (Goodhart).
- **Claiming causation** — the caveat labeling is mandatory; it is an estimate of potential avoidance, not proof.
- **The matched paired-evaluation harness** (with/without-brief provider-token runs) — a heavier, more rigorous path; out of scope here, and noted as the only measurement-grade alternative.

## Acceptance Criteria

- [ ] AC-1: The credit unit is the record's measured `source_exploration_cost` (from `1stwk`), never a hardcoded constant, and the baseline is bounded (a single record's real origin cost), so it cannot inflate with corpus size. (required)
- [ ] AC-2: Credit is added only on an actual advisory-surface event in a matching context; with no surface event, nothing accrues (test). (required)
- [ ] AC-3: `attribution_factor` is bounded well below 1.0, scaled by semantic-match confidence, and the formula is fixed + documented. (required)
- [ ] AC-4: The value is surfaced as a SEPARATE, explicitly-labeled estimate (its own line/block), never summed into the measured `## Context Efficiency` total, and carries the causal caveat. (required)
- [ ] AC-5: Surfaced-vs-cited is recorded distinctly; the attribution honestly reflects that surface is not proof of use. (required)
- [ ] AC-6: Telemetry-only invariance — retrieval, ranking, gating, and the advisory surface are byte-identical with this credit path on vs off (test). (required)
- [ ] AC-7: Full framework suite green; docs-lint clean. (required)

## Tasks

- [ ] On advisory surface, compute semantic-match-weighted credit from the record's `source_exploration_cost`; accumulate per wave/stage in the 1stwj sidecar.
- [ ] Surface a separate labeled "estimated exploration avoided" line on `wave_current`/`wave_audit` + a distinct `wave.md` block (not inside `## Context Efficiency`).
- [ ] Reference doc: formula + causal caveat + estimate-vs-measured distinction.
- [ ] Tests: grounded unit, event-triggered, bounded attribution, separate-category, caveat, telemetry-only invariance.
- [ ] Full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| credit | framework | — | on-surface, source-cost × bounded semantic attribution |
| surface | framework | credit | separate labeled category; wave.md block + wave_current/audit |
| verify | framework | surface | tests incl. telemetry-only invariance; docs |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` — edited under `framework_edit_allowed`. Depends on `1stwk`'s `source_exploration_cost` stamping and the 1stwj telemetry store.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` note (the separate estimate line); a reference doc for the formula. No boundary change — an additive, telemetry-only estimate category on top of the existing memory + telemetry surfaces.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Grounded in measured source cost — the anti-inflation guarantee |
| AC-2 | required | Event-triggered — cannot accrue by corpus size |
| AC-3 | required | Bounded, documented, inspectable attribution |
| AC-4 | required | Separate labeled estimate, never summed into measured tokens |
| AC-5 | required | Surface ≠ use honesty |
| AC-6 | required | Telemetry-only; never perturbs behavior |
| AC-7 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-17 | Change doc authored on operator direction, reconciling both council seats | Operator: "estimate exploration savings as a category"; red-team: keep separate + labeled; 1stwj Out-of-scope excludes re-exploration from measured tokens |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-17 | Ground the estimate in measured `source_exploration_cost` | The structural difference from agentmemory's `count × constant`; a real measured unit | Hardcoded per-record constant (rejected — the inflatable gauge) |
| 2026-07-17 | Separate labeled category, never summed into measured tokens | Answers the red-team's "inverts value picture" without faking a measurement | Fold into `## Context Efficiency` (rejected — dishonest, inflates the measured total) |
| 2026-07-17 | Event-triggered on surface, discounted for surface≠use | Cannot accrue by existence; honest about the causal gap | Credit on record existence (rejected — inflates with corpus) |
| 2026-07-17 | Paired-evaluation harness out of scope | Measurement-grade but heavy and rarely runnable per wave | Require paired eval (rejected — impractical per wave) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Read as a measured/billing number | Mandatory caveat labeling; separate from the measured block; never summed |
| Attribution factor gamed or too generous | Bounded well below 1.0, semantic-weighted, fixed + documented formula |
| Surface credited as proven use | Surfaced-vs-cited recorded distinctly; attribution discounted for the gap |
| Perturbs the advisory surface | AC-6 telemetry-only invariance test |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
