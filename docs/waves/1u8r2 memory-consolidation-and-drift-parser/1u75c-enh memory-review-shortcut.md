# Review Memories Shortcut

Change ID: `1u75c-enh memory-review-shortcut`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-02
Wave: `1u8r2 memory-consolidation-and-drift-parser`

## Rationale

Memory maintenance currently has tools and policy but no public lifecycle-style shortcut. An operator can ask for a "memory review" and receive a read-only report even when the intended outcome is reviewed consolidation, archival, and purge. Add one explicit, deployable command whose contract says that it reviews and applies justified memory lifecycle decisions, while retaining the existing protections against age-only cleanup and unsafe retirement of protected kinds.

## Requirements

1. Add the canonical public shortcut **`Review memories`**, with **`Memory review`** as an alias, backed by a framework seed and a rendered project prompt.
2. Define the command as an apply-oriented maintenance pass using the existing public sequence. Inventory with `memory_brief` plus history reads. For evidence-derived candidates that carry `Source event:` and `Validation: pending`, use `memory_validate(memory_id=..., verdict=..., action_delta=..., rationale=..., evidence_verified=..., current_target_verified=..., canonical_overlap=..., rewrite_kind/title/summary/evidence/targets/confidence=... when verdict="rewrite")`; never route a hand-authored or already-finalized candidate to `memory_validate`—give an ordinary reviewed candidate `memory_reconcile(status="active"|"rejected")` disposition when justified, otherwise leave it unchanged and report it unresolved. Run `memory_consolidate(mode="dry_run")`, then apply at most one returned `groups[]` entry with `memory_consolidate(mode="create", memory_ids=<exactly one groups[].memory_ids>, title=..., summary=..., reviewed=true, eligibility_confirmed=<true only after current protected-kind review>)`; never pass or auto-apply `retired_cleanup_ids`. Consolidation create already supersedes and archives every selected source: do not re-archive those IDs; after verifying the replacement, retain each source archive only if history-worthy and otherwise purge it individually. For other pre-existing retired records, archive each history-worthy record individually with `memory_reconcile(status="archived", retain_for_history=true, archive_reason=...)` and purge each unimportant record individually with `memory_purge(reviewed=true)`; supply `eligibility_confirmed=true` only after current review for protected kinds. Finish deterministically with `memory_search` default/history verification, `wf_validate_docs()`, and `index_build(content="docs", mode="update")`. When the update starts a build, poll `index_build_status(layer="project")` until `lock.held=false`, `lock.ended_at` confirms clean completion, and either `state="finished"` or `state="idle"` with `epoch.status="complete"` and `epoch.interrupted=false` before calling `index_health()` and `wf_memory_eval()`; when the update reports `up_to_date=true`, proceed without polling. Stop and report rather than evaluating against stale data when the build is interrupted, fails, or does not reach one of those clean terminal forms. Then report before/after evidence. When the operator explicitly requests read-only review, take a separate branch limited to `memory_brief`, `memory_search`/history reads, `memory_consolidate(mode="dry_run")`, and `wf_memory_eval`; it must call no `memory_validate`, consolidation create, `memory_reconcile`, `memory_purge`, docs mutation, or index mutation operation.
3. Preserve the current safety boundaries: never consolidate unrelated records to satisfy the active-memory budget, never retire on age alone, require current evidence for protected kinds, and leave unresolved judgment calls unchanged and reported.
4. Keep the output compact but measurable: status counts, active count versus budget, disposition counts, archive size, live-corpus bytes and estimated tokens removed, unresolved items, and memory-eval results when available. Define live-corpus bytes as the UTF-8 sizes of lint-valid record bodies directly under `docs/agents/memory/` (excluding `README.md` and `archive/`); estimate removed tokens as `ceil(max(before_bytes - after_bytes, 0) / 4)` and label it an estimate. Define archive size as archive-body file count plus total UTF-8 bytes under `docs/agents/memory/archive/`, with `docs/agents/memory-archive.md` bytes reported separately. Do not record model names.
5. Make the shortcut available to fresh and existing projects through seed-050 `AGENTS.md` registration, seed-100 install-time prompt generation, seed-160 every-upgrade reconciliation, the canonical framework command map, and the project-local shortcut/index/manifest surfaces. The fresh-renderer upgrade-policy marker must instruct exact merge-safe reconciliation of `AGENTS.md`, `docs/prompts/index.md`, and `docs/prompts/prompt-surface-manifest.json` (canonical shortcut only in the manifest), so an existing project receives discovery as well as the prompt file. After upgrade, surface `Review memories` when `memory_brief` reports that curation is required or returns consolidation candidates; the upgrade itself must never auto-curate or purge memory.

## Scope

**Problem statement:** The memory lifecycle is implemented but not exposed as one unambiguous operator workflow, so review requests can stop at recommendations and leave the corpus unmaintained.

**In scope:**

- Canonical framework seed `.wavefoundry/framework/seeds/240-memory-review.prompt.md` and packaged missing-only template `.wavefoundry/framework/install/lifecycle-prompts/memory-review.prompt.md`.
- Deterministic missing-prompt deployment through `.wavefoundry/framework/scripts/render_agent_surfaces.py`; existing project prompt prose remains untouched.
- Fresh-install and every-upgrade propagation in seeds `050-agent-entry-surface-bootstrap.prompt.md`, `100-project-prompt-surface-bootstrap.prompt.md`, and `160-upgrade-wavefoundry.prompt.md`.
- Post-upgrade conditional recommendation in `.wavefoundry/framework/scripts/review_policy.py`'s lifecycle-reconciler-owned `UPGRADE_POLICY_BLOCK` and its rendered `docs/prompts/upgrade-wavefoundry.prompt.md` carrier. Add a targeted, idempotent fresh-renderer backstop through `.wavefoundry/framework/scripts/review_policy_reconcile.py` and `render_agent_surfaces.py`: the old in-process upgrade reconciler may first apply its old block, then the extracted new renderer must call a targeted helper that replaces only that same marker region during the installing upgrade while preserving all prose outside it. Do not broaden renderer ownership to the lifecycle reconciler's other carriers. Add this destination to `preflight_agent_surface_paths` before any renderer write.
- Canonical/public discovery surfaces: `.wavefoundry/framework/README.md`, `AGENTS.md`, `docs/prompts/memory-review.prompt.md`, `docs/prompts/index.md`, and `docs/prompts/prompt-surface-manifest.json`.
- `CHANGELOG.md` registration.
- Contract and deployment probes in `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`, `test_setup_wavefoundry.py`, `test_upgrade_wavefoundry.py`, `test_review_policy.py`, and `test_build_pack.py`, plus docs validation and package inclusion.

**Out of scope:**

- New memory storage or ranking behavior.
- A new MCP orchestration tool; the prompt composes existing `memory_*`, validation, evaluation, and index operations.
- Automatic scheduled cleanup.
- Model-name telemetry.
- Retiring useful active memories solely to force the active count below the budget.

## Acceptance Criteria

- [x] AC-1: `Review memories` is discoverable in the canonical framework command map and all three project-local public surfaces: `AGENTS.md`, `docs/prompts/index.md`, and `docs/prompts/prompt-surface-manifest.json`; alias `Memory review` is present in the prompt, `AGENTS.md`, and prompt index, while the manifest keeps only the canonical shortcut.
- [x] AC-2: The rendered prompt explicitly states that invocation authorizes reviewed eligible memory mutations, including permanent purge, unless the operator requests a read-only review. A prompt-contract test extracts the read-only procedure and proves it contains only invocation forms for `memory_brief`, `memory_search`/history reads, `memory_consolidate(mode="dry_run")`, and `wf_memory_eval`, with no mutating invocation forms. Setup/upgrade renderer tests separately snapshot `docs/agents/memory/**` and `docs/agents/memory-archive.md` and prove those bytes are unchanged.
- [x] AC-3: The prompt specifies the runnable `memory_brief`/history inventory → evidence-derived pending candidate `memory_validate(...)` or ordinary reviewed candidate `memory_reconcile(status="active"|"rejected")` → `memory_consolidate(mode="dry_run")` then at most one exact `groups[].memory_ids` reviewed create → verify the replacement → keep or purge each auto-archived consolidation source without re-archiving it → individually archive or purge other pre-existing retired records → default/history `memory_search` verification → `wf_validate_docs()` → `index_build(content="docs", mode="update")` → clean-completion polling through `index_build_status(layer="project")` when a build starts (or the explicit `up_to_date=true` exception) → `index_health()` → `wf_memory_eval()` → report sequence. It stops on failed, interrupted, or non-clean index completion rather than evaluating stale state. It explicitly forbids routing hand-authored/finalized candidates to `memory_validate` or applying `retired_cleanup_ids`, carries `eligibility_confirmed=true` on consolidation create/archive/purge only after current review for protected kinds, and preserves age-only, replacement-first, and active-budget safeguards. Known-bad prompt fixtures missing one required validation argument, routing a hand-authored candidate to `memory_validate`, or omitting the index-build terminal-state gate must fail the contract probe.
- [x] AC-4: The prompt reports before/after status and disposition counts, active budget, archive-body count/bytes plus separate register bytes, live-corpus bytes and estimated tokens removed using the defined UTF-8-byte formula, unresolved judgments, and memory evaluation when available; it does not record model names.
- [x] AC-5: Fresh setup and every upgrade deterministically materialize a missing `docs/prompts/memory-review.prompt.md` from the packaged template through the existing missing-only renderer, while an existing prompt remains byte-identical; seed guidance reconciles the shortcut triplet without replacing supported project-grown additions. On the installing upgrade, a transition probe proves the old in-process reconciler may write its old upgrade-policy block and the extracted new renderer then updates only that same marker to recommend `Review memories` and require merge-safe reconciliation of the `AGENTS.md`/index/manifest discovery triplet, preserving outside-marker prose. The upgrade-prompt destination participates in the renderer's all-paths-before-first-write preflight; a symlink-escape probe proves refusal occurs before any sibling surface changes. Upgrade never auto-curates or purges.
- [x] AC-6: Framework docs validation passes; tests/probes prove missing prompt/shortcut backfill instructions exist for install and upgrade, the upgrade-policy marker transition preserves project prose outside its region, conditional post-upgrade guidance names `Review memories`, upgrade never invokes a memory mutation, and a local framework package includes both `seeds/240-memory-review.prompt.md` and `install/lifecycle-prompts/memory-review.prompt.md`.

## Tasks

- [x] Add the canonical memory-review seed and rendered project prompt.
- [x] Register seed-050 `AGENTS.md`, seed-100 install-time, and seed-160 every-upgrade propagation.
- [x] Register canonical and project-local shortcut surfaces and changelog entry.
- [x] Add/run targeted prompt-contract, static, and reconciliation probes for the exact candidate-routing rules and final validation/index-build-status/eval sequence (including `up_to_date=true`, clean completion, and failed/interrupted stop branches), required memory tool flags, protected-group consolidation confirmation, `groups[].memory_ids`-only consolidation and `retired_cleanup_ids` exclusion, read-only zero mutation with before/after corpus-byte snapshot, install/upgrade presence, old-reconciler → extracted-new-renderer same-run transition, outside-marker preservation, preflight symlink refusal before sibling mutation, conditional recommendation, and no automatic memory mutation; run docs validation.
- [x] Build or inspect a local package and verify both the new seed and deployable missing-only prompt template are included.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| prompt contract | implementer | — | Canonical seed and rendered prompt share one behavior contract. |
| propagation | implementer | prompt contract | Install, upgrade, command-map, and project-local registrations. |
| verification | qa-reviewer | propagation | Docs lint, targeted tests, and package inclusion. |

## Serialization Points

- The canonical seed must be complete before its install/upgrade propagation wording and rendered project prompt are finalized.
- `docs/prompts/index.md`, `docs/prompts/prompt-surface-manifest.json`, and `AGENTS.md` must remain triplet-consistent.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — record Phase 0c old in-process lifecycle reconciliation followed by the Phase 1 extracted-new-renderer targeted marker backstop, including marker-only ownership and preflight ordering.
- `docs/architecture/testing-architecture.md` — update the packaged baseline count and verification contract for the sixth missing-only prompt, old→new same-run transition, outside-marker preservation, preflight refusal, read-only/no-upgrade-mutation controls, and package contents.
- `docs/architecture/layering-rules.md` — record the invariant that the lifecycle reconciler remains primary owner and the fresh renderer may replay only the shared `UPGRADE_POLICY_BLOCK` marker as a bounded transition backstop after preflighting the destination.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The command is unusable if operators and agents cannot discover it consistently. |
| AC-2 | required | Apply-versus-report ambiguity is the defect this change resolves. |
| AC-3 | required | The command must preserve the memory lifecycle's existing safety contract. |
| AC-4 | important | Quantified results make cleanup auditable without adding narrative recordkeeping. |
| AC-5 | required | The capability must reach fresh and upgraded consumer projects. |
| AC-6 | required | Distribution and docs validity are release requirements. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-02 | Change authored from operator-approved shortcut and instructions; implementation not started. | Operator direction; existing memory archive, purge, consolidation, and budget contracts. |
| 2026-08-02 | Implemented the apply-oriented shortcut, missing-only install/upgrade deployment, same-upgrade marker backstop, discovery triplet, package registration, and safety/transition probes. | Full framework suite: 6,736 tests across 61 files, all passing; `wf_validate_docs`: clean. |
| 2026-08-02 | Built and inspected the corrected local 1.15.0 package in the canonical distribution directory. | `~/.wavefoundry/dist/wavefoundry-1.15.0.pggr.zip` (`1.15.0+pggr`); both memory-review prompt artifacts, final retention-safety repairs, and the upgrade/MCP reload repair verified in-archive; full suite 6,741/6,741 passed. |
| 2026-08-02 | Field-ran `Review memories` and aligned clean index completion with the live status API. | Clean completion observed as `state=idle`, `epoch.status=complete`, `epoch.interrupted=false`, `lock.held=false`, with `lock.ended_at` populated; prompt and contract probe accept this and the transient `finished` form. |
| 2026-08-02 | Rebuilt the final deployable package after the retention and upgrade review repairs. | `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pghf.zip`; both packaged memory-review prompt artifacts match source byte-for-byte; canonical suite 6,758/6,758 passed. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-02 | Canonical phrase is `Review memories`; `Memory review` is an alias. | Natural operator phrasing and consistent with the public review vocabulary. | `Curate memories` was accurate but less likely to be requested naturally. |
| 2026-08-02 | Invocation is apply-oriented and explicitly authorizes eligible purge. | Avoids repeating the read-only interpretation that prompted this change while keeping tool-enforced eligibility checks. | Recommend-only review rejected; separate apply shortcut rejected as unnecessary complexity. |
| 2026-08-02 | Compose existing tools through prompt instructions. | The lifecycle mechanics already exist; a new runtime orchestrator would overengineer the change. | New `wf_review_memories` MCP tool deferred unless field use proves prompt orchestration insufficient. |
| 2026-08-02 | Upgrade installs and conditionally recommends the command but never runs it automatically. | A destructive curation pass must remain operator-initiated; the existing post-upgrade memory brief provides the bounded trigger. The existing lifecycle reconciler remains primary, with a targeted extracted-new-renderer backstop so the recommendation lands on the installing upgrade instead of one upgrade late. | Automatic upgrade cleanup rejected as an authority expansion; next-upgrade-only propagation rejected as an old-code-window defect. |
| 2026-08-02 | Deploy the rendered prompt through the existing missing-only baseline renderer. | Fresh setup and every upgrade already invoke this path; registering one packaged template gives deterministic deployment while preserving an existing project-authored prompt byte-for-byte. | Seed guidance alone rejected because direct setup/upgrade would not materialize the file; a new renderer rejected as duplicate machinery. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A review-sounding command unexpectedly deletes records. | State apply authority at the top, restrict purge to reviewed eligible retired records, preserve protected-kind confirmation, and honor an explicit read-only request. |
| Agents chase the budget by deleting useful memory. | State that the cap is a curation signal, not a quota, and prohibit unrelated consolidation or useful-record retirement solely to reach it. |
| New projects receive the seed but not the public shortcut. | Register seed-050 `AGENTS.md`, seed-100 fresh generation, seed-160 every-upgrade reconciliation, framework README, and the local shortcut triplet; verify package inclusion. |
| The same-run backstop widens renderer write authority or writes before containment failure. | Keep the lifecycle reconciler primary, expose one targeted marker helper, include the exact destination in all-paths-before-first-write preflight, and pin a symlink-escape no-sibling-mutation probe. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
