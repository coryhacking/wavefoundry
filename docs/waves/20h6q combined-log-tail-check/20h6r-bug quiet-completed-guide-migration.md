# Quiet completed project-owned guide migrations

Change ID: `20h6r-bug quiet-completed-guide-migration`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-12
Wave: 20h6q combined-log-tail-check

## Rationale

A successful lifecycle-guide rename leaves delivery-workflow.md as project-owned prose. Each later render diagnoses its unregistered destination as an unconfirmed migration even when no legacy links exist. The operator needs a quiet completed migration without surrendering ownership of the guide or adding persistent dismissal state. The released 1.29.0+pw75 renderer reproduced the notice on the second and third scratch renders; the first moved the guide and its bytes remained unchanged.

## Requirements

1. Suppress the unconditional new-only confirmation notice for lifecycle destinations that are not registered renderer-owned managed surfaces. Derive that set from the existing migration and carrier registries, rather than adding a special case for one filename.
2. Preserve the existing restriction on new-only link-repair authority: an unmanaged destination alone must not authorize automatic rewrites. Initial old-source migrations and supported managed-region confirmation retain their behavior.
3. Preserve conflict, containment, byte/mode preservation and bounded document-reading checks. Do not add an unconditional document scan merely to suppress the notice.
4. Keep diagnostics for actual conflicts, refused reads and unsupported links encountered by authorized migration work. The generic notice must not claim legacy links were observed when none were inspected or found.

## Scope

**In scope:** Lifecycle confirmation/reporting in render_agent_surfaces.py, repeated-render and upgrade-preview regressions, a concise upgrade-guidance clarification and implementation changelog entry.

**Out of scope:** Registering delivery-workflow.md as framework-managed; adding managed regions, migration receipts or dismissal files; widening rewrite authority; unrelated render changes.

## Acceptance Criteria

- [x] AC-1: A real scratch render moves the legacy project-owned guide, and subsequent renders with no legacy links emit no unconfirmed-target notice while preserving its bytes and mode.
- [x] AC-2: A new-only unmanaged target grants no rewrite authority; managed-region, old-source, absent-guide and conflicting-path controls retain their distinct outcomes.
- [x] AC-3: Preview and apply agree on the relevant notices; affected tests pass, edited documentation validates, and no new unconditional scan or persistent artifact is introduced.

## Tasks

- [x] T-1: Prepare the admitted plan and inspect existing confirmation, preview and repeated-render tests.
- [x] T-2: Adjust diagnostic emission without altering migration authorization or project ownership.
- [x] T-3: Exercise registered render and preview paths with quiet-repeat and preserved-refusal controls; obtain independent code and QA review.
- [x] T-4: Update upgrade guidance and changelog; retain the concise result and limitations in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Scoped repair | implementer | readiness | One writer |
| Verification | code-reviewer, qa-reviewer | implementation | Review authority preservation as well as quiet output |

## Serialization Points

Planning only; readiness precedes source or seed edits. The implementer owns the named repair and tests; reviewers are read-only. Seed 160 owns guidance, with its rendered local prompt synchronized. The policy registry is a read-only reference; its membership is protected from this change.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_document_names.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`

## Affected Architecture Docs

N/A: diagnostic correction preserves migration ownership and control flow. Clarify the existing lifecycle-document section of the upgrade seed and rendered prompt; no new architecture mechanism.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Completed migrations must stop producing the false notice |
| AC-2 | required | Quiet output cannot confer rewrite authority |
| AC-3 | required | Preserve bounded preview/apply behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Implementation/disposition and independent delivery reviews completed. Original planning handoff below is historical; current completion and local-pack limitations are recorded in wave.md and the session handoff. | Matching green framework qualification and typed review ledger |
| 2026-10-12 | Landing control: an in-memory mutant that admits unmanaged new-only destinations into confirmed pairs fails both preview and apply through the test's no-traversal trap. The real incoming bounded migration-preview fixture also passes; independent delivery assessment remains pending. | BoundedDocumentRepairTests.test_unmarked_delivery_target_never_authorizes_repair; BoundedMigrationPreviewTests |
| 2026-10-12 | Renderer repair passes all 24 lifecycle-document tests. Before the fix, new real-repeat renders 2/3 and unmanaged preview/apply controls failed the false notice assertion. Afterward they pass while preserving bytes/modes, no-rewrite/no-scan and existing managed/conflict/refusal controls. Seed160 and rendered guidance now describe existing bounded repairs accurately. Incoming upgrade-preview integration and independent delivery assessment remain pending. | Named canonical tests; temporary focused outputs; broken-finalization mutation |
| 2026-10-12 | Readback: AC-1–3 retain project ownership and existing migration authority. Remove only the unconditional unmanaged new-only notice in render_agent_surfaces.py; exercise repeated real render, no-rewrite/no-scan and preview controls in test_lifecycle_document_names.py. Before: a completed project guide warns every render. After: it is quiet, while an unrelated legacy link remains untouched without migration authority. Clarify seed 160 and its rendered prompt; preserve bytes, modes, conflicts and registered-region diagnostics. | Admitted plan; current-source boundary inspection; current typed readiness |
| 2026-10-12 | Live source and scratch execution confirm the released defect. First render moved two guides; renders two and three warned only for delivery-workflow.md despite no links. No repository source changed. | render_agent_surfaces._confirmed_lifecycle_document_pairs and render_agent_surfaces; test_lifecycle_document_names.LifecycleDocumentMoveTests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-12 | Suppress the unsupported new-only diagnostic while retaining no-rewrite authority | Small correction to a false diagnostic; no additional state or upgrade work | Register the project guide as managed: changes ownership and policy. Record one-shot migration/dismissal state: adds durable machinery for a cosmetic notice. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Warning suppression accidentally permits new-only rewrites | Separate diagnostic emission from confirmed pair selection and test an unrelated new-only destination |
| Tests assert only no writes and miss stderr | Check actual repeated render output, not only the migration result's written list |

## Session Handoff

Planned only. See docs/agents/session-handoff.md; no permanent evidence folder is needed.
