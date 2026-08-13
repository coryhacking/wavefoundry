# Feature Wave Lifecycle Overview

Owner: Engineering
Status: active
Last verified: 2026-08-12

Adapted from `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md` for Wavefoundry's specific reviewer roles, personas, and artifact paths.

## Overview

The Wave Framework lifecycle is the delivery model for non-trivial work in Wavefoundry. A **wave** is the coordination unit: it admits one or more **changes** (consolidated change docs), enforces reviewer lanes, and closes with a documented record of what was done, what was deferred, and what was learned.

## Typical Delivery Sequence

```
Plan feature
  → author change doc at docs/plans/<change-id>.md

Create wave
  → create docs/waves/<wave-id>/wave.md
  → wave-coordinator manages admission and execution

Add change to wave
  → admit change into wave; relocate doc to docs/waves/<wave-id>/

Prepare wave (stage gate — required before implementation)
  → confirm readiness: admitted docs are wave-owned, doc complete, review lanes selected, AC priority recorded
  → when enabled, run Wave Council readiness pass and record `wave-council-readiness`
  → required reviewers confirmed; product-owner acknowledgment if product-impacting

Implement wave / Implement feature
  → implementer executes and verifies computationally
  → Review wave runs required inferential lanes
  → blocking findings return wave to implementation through the delivery repair loop
  → scope or plan invalidation triggers re-Prepare (Level 3 loop)

Review wave
  → code-reviewer, qa-reviewer, architecture-reviewer (as required by change type)
  → when enabled, run Wave Council delivery pass and record `wave-council-delivery`
  → AC scope gap check; AC priority reconciliation against shipped behavior

Close wave / Finalize feature
  → mark all changes complete or deferred with rationale
  → validate memory candidates; promote durable lessons to project-context-memory.md
  → clear or refresh docs/agents/session-handoff.md
  → docs-contract review if docs/specs/*.md changed (or record N/A with rationale)
```

## Wavefoundry-Specific Reviewer Roles

| Change Type | Required Reviewers |
|-------------|------------------|
| Framework seed edit | architecture-reviewer, docs-contract-reviewer |
| Framework script change | code-reviewer, qa-reviewer |
| MCP tool contract change | architecture-reviewer, docs-contract-reviewer |
| Packaging / build change | code-reviewer, release-reviewer |
| Self-hosted docs change | docs-contract-reviewer (if behavioral specs changed) |

## Persona Agents

- **framework-operator** — invoked during spec authoring, MCP tool design review, and acceptance of install/upgrade behavior changes
- **wave-coordinator** — invoked during spec authoring for wave lifecycle behavior changes

## Wave Council

The framework ships `wave_review.enabled: true` and `delivery_mode: targeted` by default. Enabled review requires readiness Council; targeted delivery escalates to full Council only for upgrade/release, permission/trust-boundary, cross-platform, and other shared boundary triggers. The explicit `universal | targeted | disabled` mode remains available:

- `wave-council-readiness` before implementation
- `wave-council-delivery` before closure

The `wave-council` owns council synthesis. The `wave-coordinator` still owns lifecycle state and gates.

## Factor-Review Agents (applicable)

- `factor-03-config` — configuration reading and defaults
- `factor-05-build-release-run` — packaging and VERSION stamping
- `factor-12-admin-processes` — CLI tool contracts
- `factor-13-api-first` — MCP tool surface contracts

## Pause / Handoff

Use **Pause wave** to park session state in `docs/agents/session-handoff.md` and commit it when context must be preserved. The handoff artifact is the primary working-memory snapshot for resuming a wave in a new session.

## Lifecycle IDs

Generate with the MCP `wave_new_<kind>` / `wf_create_wave` tools (preferred — they dedupe against on-disk IDs). CLI fallback when MCP is unavailable: `wf lifecycle-id --kind <kind> --slug <slug>`

Kind options: `wave`, `feat`, `bug`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`.

See `docs/workflow-config.json` `lifecycle_id_policy` for epoch details.

<!-- wavefoundry:review-policy:begin -->
## Review-policy lifecycle baseline

The review policy records phase-scoped approval_phase evidence separately for
readiness and delivery.
<!-- wavefoundry:review-policy:end -->
