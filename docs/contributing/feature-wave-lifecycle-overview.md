# Feature Wave Lifecycle Overview

Owner: Engineering
Status: active
Last verified: 2026-06-03

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
  → implementer executes; reviewer lanes participate during execution
  → blocking findings return wave to implementation (Level 2 loop)
  → scope or plan invalidation triggers re-Prepare (Level 3 loop)

Review wave
  → code-reviewer, qa-reviewer, architecture-reviewer (as required by change type)
  → when enabled, run Wave Council delivery pass and record `wave-council-delivery`
  → AC scope gap check; AC priority reconciliation against shipped behavior

Close wave / Finalize feature
  → mark all changes complete or deferred with rationale
  → distill journals; promote durable lessons to project-context-memory.md
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

The framework ships `wave_review.enabled: true` by default (formerly `wave_council_policy`) so the Wave Council surface is available out of the box. Enforcement on every wave is operator opt-in via `required_for_all_waves: true`. When enforcement is on, every wave also requires:

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

Generate with: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>`

Kind options: `wave`, `feat`, `bug`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`.

See `docs/workflow-config.json` `lifecycle_id_policy` for epoch details.
