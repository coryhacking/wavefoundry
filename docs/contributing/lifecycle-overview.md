# Lifecycle Overview

Owner: Engineering
Status: active
Last verified: 2026-11-22

Adapted from `.wavefoundry/framework/seeds/001-framework-lifecycle-overview.md` for Wavefoundry's specific reviewer roles, personas, and artifact paths.

## Overview

The Wave Framework lifecycle is the delivery model for every repository-code change in Wavefoundry, regardless of apparent simplicity. A **wave** is the coordination unit: it admits one or more **changes** (consolidated specs), enforces reviewer lanes, and closes with a documented record of what was done, what was deferred, and what was learned.

## Typical Delivery Sequence

The lifecycle has five stages. The facts for each stage (what you do, what runs automatically, councils and reviewers, gates and what comes next) are owned by the **Lifecycle At A Glance** table in `.wavefoundry/framework/seeds/001-framework-lifecycle-overview.md`; this section adapts it to Wavefoundry's paths.

1. **Plan spec**: write one spec at `docs/plans/<change-id>.md` with the outcome, acceptance criteria and tasks (mint the id with `wf_new_<kind>`). Optional: **Review plan**.
2. **Prepare wave**: **Create wave** writes `docs/waves/<wave-id>/wave.md`; **Add spec to wave** admits the spec and moves it into the wave folder; **Prepare wave** validates docs, records the review-policy receipt and runs the readiness lanes. In ordinary review the readiness Wave Council then records `council-readiness`; an operator-selected small change uses an independent code reviewer instead. Implementation refuses until the required readiness approval is recorded. Readying does not take the OPEN slot.
3. **Implement wave**: activate the wave (by default one wave is OPEN at a time) and build every admitted spec, marking tasks and ACs as they complete. Framework and seed edits need the `framework_edit_allowed` and `seed_edit_allowed` gates open.
4. **Review wave**: run the required delivery lanes. The delivery Wave Council records `council-delivery` only when the current receipt selects it (`delivery_mode: targeted` escalates on boundary triggers). Blocking findings return to implementation through the repair loop.
5. **Close wave**: the operator signs off and tells the agent to close. Optional **Close spec** (`wf_close_change`) first closes one reviewed change. **Pause wave** parks work; a reviewed paused wave shows **Awaiting closure**. In this framework source repository, close also checks the framework test receipt. The operator commits the result.

## Wavefoundry-Specific Reviewer Roles

| Change Type | Required Reviewers |
|-------------|------------------|
| Framework seed edit | architecture-reviewer, docs-contract-reviewer |
| Framework script change | code-reviewer, qa-reviewer |
| MCP tool contract change | architecture-reviewer, docs-contract-reviewer |
| Packaging / build change | code-reviewer, release-reviewer |
| Self-hosted docs change | docs-contract-reviewer (if behavior contracts changed) |

## Persona Agents

- **framework-operator** — invoked during behavior-contract authoring, MCP tool design review, and acceptance of install/upgrade behavior changes
- **wave-coordinator** — invoked during behavior-contract authoring for wave lifecycle behavior changes

## Wave Council

The framework ships `wave_review.enabled: true` and `delivery_mode: targeted` by default. Enabled review requires readiness Council; targeted delivery escalates to full Council only for upgrade/release, permission/trust-boundary, cross-platform, and other shared boundary triggers. The explicit `universal | targeted | disabled` mode remains available:

- `council-readiness` before implementation
- `council-delivery` before closure, only when the current receipt selects it

The `council-chair` owns council synthesis. The `wave-coordinator` still owns lifecycle state and gates.

## Factor-Review Agents (applicable)

- `factor-03-config` — configuration reading and defaults
- `factor-05-build-release-run` — packaging and VERSION stamping
- `factor-12-admin-processes` — CLI tool contracts
- `factor-13-api-first` — MCP tool surface contracts

## Pause / Handoff

Use **Pause wave** to park session state in `docs/agents/session-handoff.md`; the operator commits it when context must be preserved. The handoff artifact is the primary working-memory snapshot for resuming a wave in a new session.

## Lifecycle IDs

Generate with the MCP `wf_new_<kind>` / `wf_create_wave` tools (preferred — they dedupe against on-disk IDs). CLI fallback when MCP is unavailable: `wf lifecycle-id --kind <kind> --slug <slug>`

Kind options: `wave`, `bug`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`. The `feat` kind is retired for new changes (`--kind feat` exits 2 and names `enh`) and stays valid for existing ids.

See `docs/workflow-config.json` `lifecycle_id_policy` for epoch details.

<!-- wavefoundry:review-policy:begin -->
## Review-policy lifecycle baseline

The review policy records phase-scoped approval_phase evidence separately for
readiness and delivery.
<!-- wavefoundry:review-policy:end -->
