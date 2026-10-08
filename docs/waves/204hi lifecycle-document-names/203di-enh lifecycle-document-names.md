# Give lifecycle documents change-neutral names

Change ID: `203di-enh lifecycle-document-names`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-08
Wave: 204hi lifecycle-document-names

## Rationale

Waveforge's distribution work exposed remaining feature-named lifecycle documents after the public prompts became change-named. Rename the three agreed documents without losing customized downstream content or silently dropping lifecycle review-policy validation.

## Requirements

1. Rename seed `001-feature-wave-framework-overview.md` to `001-framework-lifecycle-overview.md`, retaining its numeric identity; rename contributing `feature-workflow.md` to `delivery-workflow.md` and `feature-wave-lifecycle-overview.md` to `lifecycle-overview.md`.
2. Update current source instructions, titles, live references, policy registrations and test consumers. Derive the reference census from the three old basenames over tracked live files; retain historical closed waves, ledgers, changelog entries and benchmark evidence, and explicit migration inputs.
3. Upgrade existing project documents before policy rendering uses the new paths. Preserve bytes and permission bits at the move boundary, leave customized prose intact, preflight all document pairs, refuse collisions and unsafe paths without overwriting either side, and make successful reruns no-ops.
4. Report links to moved documents for reconciliation rather than rewriting arbitrary project prose or historical evidence. Document the upgrade's rename, conflict recovery and retained-content behavior.
5. Keep lifecycle direct-document validation and managed baseline reconciliation effective at the new path. Establish through tests whether the path change affects policy receipts; require and disclose re-Prepare if actual policy inputs change, without changing digest canonicalization or historical receipts.

## Scope

**Problem statement:** Feature-named lifecycle documentation obscures the generic change model and requires coordinated downstream migration because one document carries review-policy obligations.

**In scope:** The three named files; their live references and titles; contained renderer migration and ordering; policy carrier registration; focused migration, upgrade and policy tests; self-hosted documentation reconciliation; Waveforge handoff.

**Out of scope:** Renaming arbitrary feature concepts, changing lifecycle vocabulary profiles or authority, merging the existing change-workflow guide, rewriting archives or benchmark evidence, memory migration, release-pack publication, wave closure, and committing or pushing this new work without a subsequent instruction.

## Acceptance Criteria

- [x] AC-1: The three new canonical paths exist, the three old paths are absent in the current source tree, and a rule-derived live-reference census contains no obsolete references except documented compatibility inputs and historical evidence.
- [x] AC-2: Existing customized project documents migrate with exact bytes and permission bits at the move boundary; reruns make no additional moves; absent legacy documents remain absent unless an existing documented seeding path creates their new names.
- [x] AC-3: Both-present conflicts and unsafe source/destination paths are refused before any document pair is moved; existing source, destination and outside files retain their bytes. Diagnostics identify recovery without silently overwriting content.
- [x] AC-4: Real surface rendering and installing-upgrade coverage prove migration precedes policy reconciliation, new-path lifecycle policy obligations remain enforced, customized text outside managed regions survives, and receipt/re-Prepare implications are tested and documented.
- [x] AC-5: Fresh seeding instructions, upgrade guidance and a Waveforge handoff consistently identify the new names, preservation boundary, conflict recovery and reference-reconciliation obligations; historical evidence remains unchanged.

## Tasks

- [x] Complete independent readiness review and record current typed approvals.
- [x] Rename canonical and local documents and reconcile live references and policy registrations.
- [x] Add the contained project-document migration and regression coverage.
- [x] Verify migration boundaries, installing upgrade, policy coverage and vocabulary portability with meaningful negative controls.
- [x] Run the full framework suite with all repository writes frozen, then validate docs and complete independent delivery review and handoff.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness | Independent council and required reviewers | Plan | Primer first, isolated seats, current receipt approvals |
| Implementation | Coordinator implementer | Readiness | Serialized source, seed and local document edits |
| Verification | Coordinator and independent QA | Implementation | Temporary fixtures; no repository writes during canonical suite |
| Delivery review | Independent reviewers | Verification | Review the actual diff and executed evidence |

## Serialization Points

- `.wavefoundry/framework/seeds/`
- `.wavefoundry/framework/README.md`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/contributing/`
- `docs/references/`
- `docs/prompts/upgrade-wavefoundry.prompt.md`

Only the coordinator edits implementation files. Canonical seed edits require the seed gate in addition to the framework gate. Generated surfaces follow their canonical source. Tests and review probes are serialized when they share state; the full suite runs on a frozen repository.

## Affected Architecture Docs

N/A for architecture hubs: reuse the existing contained migration and policy-carrier ownership boundaries without changing protocol or evaluation semantics. The affected lifecycle and delivery guides themselves describe the renamed operating surface; upgrade guidance records the added migration step and ordering.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Completes the agreed naming cleanup without rewriting evidence |
| AC-2 | required | Downstream customizations must survive upgrade |
| AC-3 | required | Project-file migration must not overwrite conflicting or outside data |
| AC-4 | required | A pathname rename cannot drop policy authority or break installing upgrades |
| AC-5 | required | Waveforge needs a usable, accurate integration contract |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-08 | Preexisting changes committed and pushed before starting this wave; clean main at 49b701bb. Plan grounded in existing council-role migration and policy carrier registry. | Git status; renderer migration helpers; review_policy.py registry |

| 2026-10-08 | Readback: implement AC-1–5 by renaming the three documents and live references, migrating two project docs through contained exclusive writes before policy rendering, and retaining current policy authority. Example: a customized old lifecycle guide moves byte-for-byte to lifecycle-overview.md, then only its managed policy region may reconcile. Historical evidence is report-only. Memory advisories rechecked against current contained reads/writes, real baseline producers and fresh upgrade subprocess; use exact-byte, public-path and negative-control tests. | Typed readiness complete; framework and seed gates open. |

| 2026-10-08 | AC-1–5 implementation evidence: three new paths and complete tracked live-name census; only migration inputs/guidance and historical evidence retain old names. Eight focused tests pass, fresh installing-upgrade test passes including disabled-migration control; deleted all-pair preflight causes named second-pair conflict test failure. Current policy snapshot matches pre-edit snapshot (b9135e812e24adabe1642d208693e020076eba285f27eb53d38637892fe5520a). Surface sync and full docs lint pass. No framework source changes during independent delivery review. | test_lifecycle_document_names.py; LifecycleDocumentInstallingUpgradeTests; /tmp/wf-lifecycle-prior-digest.json; /tmp/wf-204hi-review-tree.json. |

| 2026-10-08 | Independent code/docs/security reviews found no production defect. Code killed preflight/nonexclusive/mode mutants; security killed an unsafe following-read mutant through the renderer. QA-204HI-001 found a missing manifest in the new profile fixture. Recorded repair_start before adding explicit readable manifest and profile-derived Prepare marker assertion; default and prompt-names eight-test owners now pass with no skips. Upgrade owner under prompt-names passes 682 tests, two existing skips. Independent QA reverification and full suite pending. | Typed finding/repair cycle 1; repaired tree eae5f5c78ea9c53222e3292aed00365ef22d42385bd71b79d752d1764aa29352; /tmp/wf-lifecycle-profile-repaired.log. |

| 2026-10-08 | QA-204HI-001 independently cleared. Second-profile run exposed QA-204HI-002: history fixture hardcoded docs/waves and relative depth. Recorded cycle-2 repair_start; derive history root from record_paths.WAVES_ROOT and relative old link from actual parent, retaining exact history bytes assertion. Only test fixture changed; production remains frozen. | Final source fingerprint 359a3bd1808f8236105880804096fdf690d46e337dd12344d8d0a4cb845786aa; independent QA reverification pending. |

| 2026-10-08 | QA-204HI-002 independently cleared; default, second and prompt-names each pass all eight tests with zero skips. Hardcoded-root mutant fails intended history-link assertion; exact-byte history oracle retained. All source fingerprints stable. Freeze all repository writers, including MCP telemetry/review ledger, for canonical suite. | Typed cycle-2 reverification and convergence checkpoint; 359a3bd1 final source. |

| 2026-10-08 | Sandboxed canonical run executed 11,894 tests across 174 files, 20 existing skips, 421.808s; five owners failed because sandbox denied localhost bind, ps, tool-venv scratch file and pip cache access. New lifecycle, renderer, upgrade and policy owners passed. No fresh receipt written. Rerun unchanged tree with host permissions; freeze all repository writes again. | /tmp/wf-204hi-canonical.log; failures dashboard_server/process_info/setup_index/startup_install/verify_vendored_scripts, explicit Operation not permitted diagnostics. |

| 2026-10-08 | Host-permission canonical run passed: 11,894 tests across 174 files, 20 existing skips, 412.596s. All sandbox-denied owners pass, no repository-change guard failure; final reviewed source fingerprint unchanged. Fresh green receipt written. | /tmp/wf-204hi-canonical-host.log; receipt 660d1a46ca27f86aab3f159a26b3685cbf28484ade8a820791e10e29e09f2c15, 2026-10-08T20:32:39.636317+00:00. |

| 2026-10-08 | All five ACs and tasks complete. Independent code, docs-contract, security and QA delivery approvals current; both fixture findings terminal. QA recomputed receipt hash and source fingerprint. Documentation validation and diff checks pass. Implementation complete; operator closure and new-work commit/push remain pending. | Typed ledger and green canonical receipt. |

| 2026-10-08 | Review memory drafted one generic fragile-file candidate; rewrote it to the two verified profile-fixture boundaries with the correct target path. Retrieval advisory reports zero implementation-stage calls despite MCP-first investigation/reviewer reads; source exploration was largely completed before activation. Gapfill: shell used for executed probes, mechanical edits and Git verification; MCP remained available and was used for code grounding. | Typed memory validation; no production or test changes after green receipt. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-08 | Use explicit document rename pairs with existing contained publication primitives and early renderer ordering. | Bounded compatibility path preserves local prose and existing ownership. | A source-only rename strands downstream files and policy validation; compatibility stubs duplicate authorities; merging into change-workflow mixes separate guides and increases content risk. |
| 2026-10-08 | Preserve historical evidence and report downstream moved links. | Migration owns paths, not arbitrary authored text. | Global replacement could alter historical receipts and customized prose. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Policy renderer creates a destination before migration | Run migration before policy reconciliation and verify public rendering/upgrade ordering |
| Existing destination or linked parent causes data loss | All-pair preflight plus contained exclusive publication; adversarial fixtures |
| Downstream file content still contains old names | Report links and document explicit reconciliation; do not claim arbitrary prose is rewritten |
| New-path registration changes readiness unexpectedly | Verify receipt inputs and disclose actual re-Prepare requirements |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
