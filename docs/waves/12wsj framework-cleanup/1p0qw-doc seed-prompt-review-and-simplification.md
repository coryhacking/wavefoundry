# Seed Prompt Review And Simplification

Owner: Engineering
Status: complete
Last verified: 2026-05-25
Verification method: manual seed-prompt review across `.wavefoundry/framework/seeds/`

## Title

Seed Prompt Review And Simplification

## Change ID / Filename

Change ID: `1p0qw-doc seed-prompt-review-and-simplification`

Wave: `12wsj framework-cleanup`

## Rationale

The Wavefoundry seed corpus has grown enough that some prompts now restate the same contracts in multiple places, and a few lifecycle and memory rules have drifted into contradiction. That raises maintenance cost, increases the chance of upgrade/init drift, and can make agents less efficient by forcing them through redundant or conflicting instructions. This review captures simplification opportunities that preserve or improve output quality rather than merely shortening prompts.

## Product Intent

Keep the shared Wavefoundry prompt layer accurate, internally consistent, and easier to maintain so seeded repositories produce higher-confidence agent behavior with less prompt drift, less unnecessary operator friction, and clearer lifecycle routing.

## Design Intent

Design Intent: N/A — no UI surface changes.

## Requirements

- Identify contradictions, inefficiencies, and simplification opportunities in the current seed corpus.
- Prefer recommendations that reduce maintenance burden or execution friction without weakening guardrails or output quality.
- Preserve the framework's current quality bar for lifecycle discipline, review rigor, docs gating, and evidence-based behavior.
- Record concrete file-level evidence for each finding so follow-on implementation can be scoped precisely.

## Decision Refs

Decision refs:

- N/A — review findings only

## Scope

- Problem statement: the seed prompt corpus contains duplicated contracts, inconsistent lifecycle wording, and uneven platform/operator guidance that can degrade maintainability and agent efficiency.
- In-scope changes: review and document issues across `.wavefoundry/framework/seeds/`, especially lifecycle prompts, overview docs, and specialist-role seeds; apply the operator-approved high-priority contract fixes that came directly out of this review when they are narrow and already decisioned.
- Out-of-scope changes: broad seed simplification beyond the approved high-priority fixes, changing product code, or opportunistic cleanup not grounded in the recorded findings.

## Acceptance Criteria

- [x] AC-1: A documented review exists with concrete issues tied to specific seed files and lines.
- [x] AC-2: Each issue includes a recommendation that preserves or improves output quality rather than only shrinking prompt text.
- [x] AC-3: The review distinguishes true contradictions from maintainability or efficiency opportunities.

## Tasks

- [x] Reconcile the documented findings with framework maintainers.
- [x] Decide which findings become immediate seed edits versus deferred cleanup.
- [x] Implement approved prompt changes and re-run docs validation.

## AC Priority

| AC | Priority | Description | Rationale |
| --- | --- | --- | --- |
| AC-1 | required | A documented review exists with concrete issues tied to specific seed files and lines | The review must be evidence-backed so cleanup work is grounded in actual contract drift rather than preference |
| AC-2 | required | Each issue includes a recommendation that preserves or improves output quality rather than only shrinking prompt text | The cleanup goal is better maintainability and efficiency without weakening agent output quality |
| AC-3 | required | The review distinguishes true contradictions from maintainability or efficiency opportunities | Follow-on implementation depends on separating blocking contract conflicts from optional cleanup |

All ACs are Required. There are no Important, Nice-to-have, or Not-this-scope items for this review-only change.

## Review Findings

1. `High` — Journal-memory policy is internally contradictory.
Evidence:
`004-wave-memory-overview.md:19,29` says durable memory should capture positive validated approaches as well as corrections.
`006-agent-journal-system-overview.md:39,59,74` allows immediate capture when a durable signal appears and explicitly treats closure as a distillation point, not the only write time.
`020-run-contract.prompt.md:89-91` narrows journaling to failures, rework, or hard-to-find issues and explicitly says not to journal issues fully fixed in the same session.
Recommendation:
Make `020` match the broader operating-memory contract: journal when the signal is durable and non-obvious, whether it is a correction or a validated pattern. Keep the anti-activity-log rule, but remove the failure-only framing.

2. `High` — Change-document relocation timing conflicts across lifecycle seeds.
Evidence:
`001-feature-wave-framework-overview.md:27,37,71,114,197` says admitted change docs move into `docs/waves/<wave-id>/` during `Add change to wave`.
`170-plan-feature.prompt.md:76` says `Prepare wave` is the primary relocation stage.
`180-implement-feature.prompt.md:162,188` says `Prepare wave` must physically move the files and `Implement wave` should only repair drift defensively.
`200-wave-reconciliation.prompt.md:110` assumes the `Prepare wave` model.
Recommendation:
Pick one canonical relocation stage and remove the other story everywhere. The cleaner model is the newer one: `Add change to wave` admits and repairs metadata, `Prepare wave` performs the canonical file relocation before implementation.

3. `High` — `Implement wave` authorization is stricter than `AGENTS.md` and creates unnecessary stop points.
Evidence:
`AGENTS.md:105,111` says explicit authorization in the current request such as `Implement wave` or `Implement feature` is sufficient for product implementation, subject to the normal guards and any recorded hold.
`180-implement-feature.prompt.md:157,208` says agents must stop after `Prepare wave`, present the plan, and wait for another explicit approval, and must not treat `Implement wave` itself as approval.
Recommendation:
Align `180` with `AGENTS.md`. Keep the requirement to surface the implementation plan and risks, but require a second approval only when the repo entry contract or active handoff explicitly imposes a hold, not as a universal extra checkpoint.

4. `Medium` — Canonical public command naming has drifted across overview and lifecycle seeds.
Evidence:
`002-wave-framework-seeding-overview.md:87-105` says durable docs should normalize onto `Init wave framework` / `Upgrade wave framework` and treat install phrases as aliases.
`008-framework-map.md:40-41` and `009-framework-maintenance-contract.md:34,47` still foreground `Install Wavefoundry` / `Upgrade Wavefoundry`.
`010-install-wavefoundry.prompt.md:1-3` uses `Install Wavefoundry` as the primary label.
`160-upgrade-wavefoundry.prompt.md:3` uses `Upgrade wave framework` plus `Install wave framework` as primaries.
Recommendation:
Choose one canonical public phrase family and demote the others to aliases in a single shared rule. The least ambiguous current model is `Init wave framework` and `Upgrade wave framework`, with install/context variants accepted but not foregrounded.

5. `Medium` — The init and upgrade umbrella prompts duplicate too much subordinate contract detail, which increases drift risk.
Evidence:
`010-install-wavefoundry.prompt.md:139-146` explicitly says artifact detail lives in step prompts, but the prompt still carries a long embedded artifact and handoff contract immediately below.
`160-upgrade-wavefoundry.prompt.md:68-155` and `160-upgrade-wavefoundry.prompt.md:331-432` inline a very large reconciliation matrix that overlaps `seed-150`, `seed-050`, `seed-040`, `seed-100`, and related seeds.
Recommendation:
Refactor `010` and `160` into orchestration prompts plus a smaller invariant checklist. Keep the routing, ordering, and stop conditions in the umbrella prompts, and move most file-class specifics into referenced step prompts or a generated checklist source of truth.

6. `Medium` — Platform support guidance is uneven across lifecycle prompts.
Evidence:
`160-upgrade-wavefoundry.prompt.md:41` explicitly says Windows operators should use WSL2 rather than native `cmd.exe` or PowerShell.
`010-install-wavefoundry.prompt.md`, `240-package-wavefoundry.prompt.md`, and `250-migrate-existing-wave-project.prompt.md` contain bash-oriented examples and lifecycle steps but no corresponding platform support note.
Recommendation:
State the supported-platform rule once in a shared contract seed such as `020` or `002`, then add short cross-references in `010`, `160`, `240`, and `250` so init, package, migrate, and upgrade all present the same operator expectation.

7. `Medium` — Specialist-role seeds `226-235` repeat the same harness skeleton almost verbatim.
Evidence:
`226-backend-architect.prompt.md`, `227-software-architect.prompt.md`, `228-database-optimizer.prompt.md`, `229-security-engineer.prompt.md`, `231-ai-engineer.prompt.md`, `232-api-tester.prompt.md`, `233-technical-writer.prompt.md`, `234-workflow-engineer.prompt.md`, and `235-enterprise-integration-engineer.prompt.md` all use the same section structure: `Operating Identity`, `Responsibilities`, `Default Stance`, `Focus Areas`, `Do Not`, `Output Shape`, `Assumption Tracking`, `Salience Triggers`, `Memory Responsibilities`.
Recommendation:
Keep the role-specific substance, but generate these from a shared specialist template or extract the repeated harness contract into a single referenced seed. That reduces maintenance drift while preserving the current output quality and lane specificity.

8. `Medium` — Init’s docs-gate contract is inconsistent about what counts as CLI completion.
Evidence:
`010-install-wavefoundry.prompt.md:140` says hosts without MCP only need `.wavefoundry/bin/docs-lint` exit 0 for init completeness.
`010-install-wavefoundry.prompt.md:177` later says CLI fallback verification is `.wavefoundry/bin/docs-gardener` and `.wavefoundry/bin/docs-lint`.
`002-wave-framework-seeding-overview.md:50,198`, `040-docs-structure-bootstrap.prompt.md:235`, `090-doc-gardening-harness.prompt.md:13`, and `160-upgrade-wavefoundry.prompt.md:155,217,238,271` all use the fuller `docs-gardener && docs-lint` CLI contract.
Recommendation:
Unify the CLI docs-gate rule everywhere. If `docs-gardener` is required before `docs-lint`, say so consistently in init completion criteria rather than only in later verification notes.

9. `Medium` — The init MCP/index handoff is underspecified relative to the framework’s own MCP-availability contract.
Evidence:
`010-install-wavefoundry.prompt.md:146` makes “restart MCP and run `wave_index_build`” a required final handoff step.
`211-guru.prompt.md:433-435` and `050-agent-entry-surface-bootstrap.prompt.md:443` say MCP is not active at init time and is registered separately via `Enable Wavefoundry MCP`.
`010` does not clearly describe when MCP is already expected to exist, whether init must also seed the registration path, or what the no-MCP handoff is when registration has not been run yet.
Recommendation:
Make the init handoff explicit: either seed/register MCP as part of init or split the handoff into “if MCP is already registered, restart and reindex” versus “otherwise run the MCP enable path first, then reindex.”

10. `Medium` — Init and upgrade do not enforce the plan-template scaffold with the same specificity.
Evidence:
`170-plan-feature.prompt.md:63` requires checkbox syntax for Acceptance Criteria and live checkbox tracking for Tasks.
`160-upgrade-wavefoundry.prompt.md:118-120,300-301,399-400` explicitly upgrades `docs/plans/plan-template.md` and scaffold generators to checkbox syntax.
`010-install-wavefoundry.prompt.md:32,183,359` requires the consolidated change-document format after init but does not explicitly require the same checkbox AC/Task scaffold.
Recommendation:
Make init and upgrade seed the same plan-template contract explicitly. New installs should not depend on later upgrade reconciliation to receive the checkbox AC/Task standard.

11. `Low` — Some seed cross-references use stale task numbers, which adds avoidable maintenance confusion.
Evidence:
`010-install-wavefoundry.prompt.md:139` points to `seed-040` build-and-verification work as “task 16”.
`040-docs-structure-bootstrap.prompt.md:231-253` shows the relevant `Wave framework pack upgrade verification` work is task 17.
`160-upgrade-wavefoundry.prompt.md:155` points to task 17, while `160-upgrade-wavefoundry.prompt.md:432` points back to task 16 for the same concept.
Recommendation:
Normalize task-number references or avoid brittle task-number references where a stable heading or section title would be clearer.

## Agent Execution Graph

| Workstream | Primary Agent | Scope | Depends On | Can Run In Parallel With | Deliverable |
| --- | --- | --- | --- | --- | --- |
| Seed review | docs-contract-reviewer | review the shared seed corpus for contradictions and simplification opportunities | none | none | issue list with evidence |
| Follow-on implementation | implementer / workflow-engineer | edit seeds after maintainer approval | seed review | reviewer lanes | updated seed corpus |
| Validation | docs-contract-reviewer / qa-reviewer | verify docs contract and prompt-surface alignment after edits | follow-on implementation | none | clean docs gate and reconciled findings |

## Serialization Points

- Choose the canonical lifecycle relocation model before editing lifecycle prompts.
- Choose the canonical public command names before editing overview and shortcut docs.
- Reconcile the journal-memory contract before touching journal, closure, or upgrade prompts.
- Run docs validation after any approved seed edits.

## Affected Architecture Docs

N/A — this review concerns framework prompts and docs workflow behavior, not product/module architecture boundaries.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-25 | Reviewed the seed corpus for contradictions, drift, and simplification opportunities; documented findings in this change doc. | `.wavefoundry/framework/seeds/` |
| 2026-05-25 | Applied the approved high-priority contract fixes from the review: journal-memory contract alignment, Add-change relocation ownership, Implement-wave approval alignment, and canonical init/upgrade naming cleanup; docs gate passed. | `.wavefoundry/framework/seeds/020-run-contract.prompt.md`, `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`, `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`, `.wavefoundry/framework/seeds/002-wave-framework-seeding-overview.md`, `.wavefoundry/framework/seeds/008-framework-map.md`, `.wavefoundry/framework/seeds/009-framework-maintenance-contract.md`, `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `python3 .wavefoundry/framework/scripts/docs_lint.py` |

## Decision Log

| Date | Decision | Reason | Alternatives Rejected |
| --- | --- | --- | --- |
| 2026-05-25 | Record findings before editing the seed corpus | The review surfaced multiple cross-seed contradictions that should be prioritized before mechanical cleanup | Editing individual prompts immediately without a consolidated issue list |
| 2026-05-25 | Journal-memory contract should remember anything that improves outcomes, not only failures | Operator clarified that durable memory should optimize for future outcomes rather than failure-only recall | Keeping the narrower failure/rework-only framing from `seed-020` |
| 2026-05-25 | Admitted change docs move during `Add change to wave`; `Prepare wave` validates and repairs any drift | Operator clarified the intended lifecycle ownership for change-doc relocation | Making `Prepare wave` the sole canonical relocation stage |
| 2026-05-25 | `Implement wave` requires operator confirmation to move into implementation, but not a second confirmation unless review materially changed the plan | Operator clarified the intended approval model | Requiring a universal second approval checkpoint before every implementation start |

## Operator Direction

- Journal memory should preserve anything that will improve future outcomes, including validated positive patterns, not only failures or rework.
- Change documents should move into the wave folder during `Add change to wave`; `Prepare wave` should validate that state and move any stragglers.
- Operator confirmation is required to move into implementation. A second implementation confirmation is only needed when review materially changes the plan or execution packet.

## Session Handoff

- If implementation is deferred, refresh `docs/agents/session-handoff.md` with the prioritized finding list and the chosen canonical direction for relocation, journal policy, and command naming.

## Risks And Mitigations

- Risk: simplification work could accidentally weaken lifecycle or review guardrails.
- Mitigation: only simplify duplicated wording after a single authoritative contract source is chosen and referenced.
- Risk: fixing one seed in isolation could deepen cross-seed drift.
- Mitigation: implement changes by contract cluster rather than file-by-file opportunism.

## Completion Notes

- The review findings remain the source document for broader simplification follow-up.
- The operator-approved high-priority contract fixes were applied in this wave; lower-priority findings remain available for later cleanup waves.
