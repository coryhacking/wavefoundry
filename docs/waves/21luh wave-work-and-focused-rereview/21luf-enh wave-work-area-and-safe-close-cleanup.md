# Wave work area and safe close cleanup

Change ID: `21luf-enh wave-work-area-and-safe-close-cleanup`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-25
Wave: `21luh wave-work-and-focused-rereview`

## Rationale

Give agents one predictable disposable workspace for a wave and operators bounded cleanup after closure. The operator selected the gitignored path `.wavefoundry/work/<wave-id>/`, without a waves subdirectory. Existing wave records and unique evidence must remain durable.

## Product Intent

Cooperating agents can find temporary wave work, and successful closure removes disposable output without deleting another wave's work or the evidence needed to substantiate delivery. AC-1 through AC-4 jointly establish that outcome. The workspace is not a sandbox, durable archive or migration destination for historical files.

## Requirements

1. Use `.wavefoundry/work/<wave-id>/`; the key is the resolved unique lifecycle prefix (for example `21luh`), not arbitrary caller text or the mutable descriptive slug. Establish ownership bound to the configured repository and resolved wave. Never silently adopt unrelated pre-existing directories. Worktrees have separate repository-local areas.
2. Successful mutating Create/Prepare/Implement/Reopen operations establish the directory lazily as needed, including for existing waves. Current-wave, Prepare, Implement and Review responses expose its path and availability. Read-only calls and dry-runs do not create it. Missing/unwritable work areas yield a bounded notice, not new lifecycle authority or a readiness gate. No new public tool is required.
3. Add `.wavefoundry/work/` to the canonical managed Git ignore surface and reconcile installs/upgrades and this repository, preserving unrelated rules. Never untrack files automatically. Use applicable runtime-path exclusions to keep scratch out of indexing, distribution packaging and repository-source/qualification observation. Scratch writes must not masquerade as source edits; genuine source changes remain detected.
4. This is general-purpose disposable work: optional `receipts/`, `reviews/`, `tests/` and `scratch/` subdirectories, created only as needed. Coordinator briefs identify the shared path. Existing host permissions still apply; no arbitrary execution, tool grant, or automatic migration of /tmp or existing evidence.
5. Retain through planned, ready, active and paused states. Only after successful operator-authorized whole-wave closure, attempt cleanup of that owned directory. Dry-run, blocked/failed close and single-change close preserve it. Cleanup failure reports remaining work without undoing closure; an authorized repeated close may retry. Reopening creates a fresh owned generation, protected from stale cleanup. No sweeper, age expiry, automatic process killing or new gate.
6. Creation and cleanup reject traversal, symlink/junction escape, ownership mismatch and identity substitution. Verify parent/directory identity at the destructive boundary and coordinate with lifecycle publication so stale cleanup cannot delete a reopened generation. Never follow links to delete their targets. On unsupported safe-deletion paths, preserve files with an explicit notice. An absent directory is a successful cleanup no-op.
7. Before close, preserve unique long-term proof in maintained locations and record final results/limits in wave records. New durable approvals must not depend solely on disposable paths; preserve unique proof before finalizing evidence. Do not rewrite immutable ledger references or delete historical wave artifacts. Receipt snapshots are optional aids whose later absence is honest and expected.
8. Update canonical lifecycle/review-artifact guidance and applicable local/install/upgrade carriers. The existing prohibition on automatic deletion changes only for this newly designated owned workspace; ordinary wave-folder evidence retains its current protections.

## Scope

In scope: owned work-area lifecycle/discovery, managed ignores and runtime exclusions, contained post-close cleanup and prospective evidence guidance.

Out of scope: historical temp/evidence cleanup, retention configuration, archival service, approval changes, test-receipt acceptance (21lue), automatic commits or builds.

Source-inspected premises: close transition/retry handling is in `wf_server/server_impl.py::wf_close_wave_response`; managed ignores are in `render_platform_surfaces.py::_GITIGNORE_BLOCK`. These are not executed proof of the proposed mechanism. An executed read-only `git check-ignore -v --no-index .wavefoundry/work/21j63/probe.txt` probe found no matching rule. The current seed 190/209 automatic-cleanup prohibition is explicitly narrowed by Requirement 8, not silently bypassed.

## Acceptance Criteria

- [x] AC-1: Supported lifecycle responses give two agents the same owned path for one wave and different paths for distinct waves; reads create nothing, and pause/reopen follow the declared lifetime.
- [x] AC-2: Successful whole-wave close removes owned scratch while preserving records, other waves and external files. Dry-run, failed close and single-change close retain it; stale cleanup cannot delete a reopened generation.
- [x] AC-3: Traversal, link substitution, wrong ownership and partial-I/O cases cannot delete outside the owned area. Failure is advisory after closure; missing directories and authorized retries are idempotent, with host limitations stated.
- [x] AC-4: Installed/upgraded fixtures Git-ignore scratch and exclude it from packaging/indexing and source qualification observation, while genuine framework/source edits remain detectable.
- [x] AC-5: Canonical and supported guidance consistently describes the path, preservation duties and cleanup timing; a worked example retains unique final proof outside scratch and remains understandable after cleanup.

## Tasks

- [x] Ground directory identity, concurrent reopen and supported-host deletion in existing contained-I/O helpers.
- [x] Implement the shared work-area helper and lifecycle discovery/creation/cleanup.
- [x] Reconcile the actual runtime-path consumers and managed Git ignore.
- [x] Update canonical seeds/templates before reconciling supported local/install/upgrade guidance.
- [x] Independently verify bounded lifecycle, isolation and deletion cases, including controls that reject an unsafe implementation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Directory/lifecycle integration | implementer | readiness | Own helper and shared server edits |
| Exclusions and guidance | implementer | directory contract | Serialize renderer/seed changes |
| Verification | code/QA/security/docs reviewers | frozen implementation | Read-only; coordinator records evidence |

## Serialization Points

- `.wavefoundry/framework/scripts/wave_work.py`
- `.wavefoundry/framework/scripts/contained_files.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/machine_authority.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-change.prompt.md`
- `.wavefoundry/framework/seeds/190-close-wave.prompt.md`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/`
- `docs/prompts/`
- `docs/contributing/build-and-verification.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/threat-model.md`
- `docs/architecture/domain-map.md`

Root .gitignore is an intended renderer output. Derive guidance edits from instructions governing workspace creation/use/close, not every prompt indiscriminately. Protect unrelated instructions, host permissions, closed records and generated authority regions. Implementer/coordinator owns writes; reviewers are read-only. Additional source owners discovered at readiness require a scope amendment before editing.

## Affected Architecture Docs

Update data-and-control-flow for workspace lifetime, threat-model for ownership/deletion, domain-map for the narrow disposable work/snapshot write allowance, and the MCP surface contract for discovery and cleanup observations. The domain-map exception does not broaden approval authority or document ownership. Seed 050 and the renderer must retain canonical managed-ignore block parity.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Shared discoverability |
| AC-2 | required | Correct cleanup lifetime |
| AC-3 | required | Destructive-operation containment |
| AC-4 | required | Scratch stays local and outside product inputs |
| AC-5 | required | Agents understand disposability and durable evidence |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-25 | Independent delivery verification completed; required lanes and Council support the admitted mechanisms. Final canonical qualification passed 12,195 tests across 211 files, 12 skips, 592.190s; no reviewed source changed during the run. | Maintained helper/lifecycle/publication/review controls and typed delivery evidence; receipt inputs_hash db4065ce546931c670d6378ed45f79af78c256fe64aec17cfda145e214335a87; see wave Review Checkpoints for limits |
| 2026-10-25 | Before test-only promotion: independent security found no production defect, but the isolated parent-anchor guard survived the maintained tests. Its regular-parent substitution control preserves moved proof on production and loses it under the guard mutant. Promote that exact bounded control to the maintained helper tests before final qualification; all delivery readers have finished on the frozen implementation. | Independent security fixture and proposed test_regular_parent_substitution_before_unlink_preserves_moved_work; no implementation behavior change |
| 2026-10-25 | Implemented helper and public lifecycle integration; 18 helper and 10 registered-path tests pass. Five helper and three lifecycle mutants detected; excludes source/package/index scratch; 11 carrier controls plus reconcile/source-guard modules pass. Independent delivery review still pending. | Reproducible tests: test_wave_work, test_wave_work_lifecycle, managed-ignore/reconcile/source-guard fixtures; results in task scratch |
| 2026-10-25 | Source-owner amendment: the maintained FRAMEWORK_SCRIPT_MODULE_NAMES census in mcp_tool_extensions.py must reserve the new wave_work module against extension-name collision. Add that source target before editing it; no behavior or approval-contract change. | Current module census and its parity-test contract |
| 2026-10-25 | Readback: agents currently scatter temporary work; add one gitignored owned path exposed by lifecycle responses, retain on pause, clean only after successful whole-wave close. Example: two agents discover work/21luh; closing 21luh removes only its owned scratch, preserving durable evidence and other waves. AC-1–5; helper/server, ignore/exclusion sources, canonical guidance and supported carriers only. | Current readiness receipt and scoped plan |
| 2026-10-25 | Planned from operator direction. No source edits or readiness claimed. | Conversation; source reads; Git ignore probe |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-25 | Managed local work area with plain files and lazy subdirectories | Shared discovery and a bounded cleanup target | Ad hoc OS temp retains discovery ambiguity; committed scratch adds permanent volume |
| 2026-10-25 | Cleanup after committed closure, best effort | Removes disposable work without making maintenance another gate | Pre-close deletion risks losing work on refusal; expiry can destroy paused work |
| 2026-10-25 | Mechanism controls location/lifetime; guidance controls evidence promotion | Replays scattered-work case through one path and contained deletion; measure observed use and cleanup outcomes on later waves | Cannot guarantee agent adoption or classify arbitrary content as durable; no automatic evidence classifier |

## Risks

| Risk | Mitigation |
| --- | --- |
| Durable claim depends on deleted scratch | Preserve unique proof before final approval; no retrospective migration |
| Races with reopened wave or path replacement | Ownership generation, contained identity checks and serialized lifecycle boundary |
| Windows handles or filesystem features prevent safe deletion | Preserve with notice; qualify actual supported behavior |
| Scope expands into evidence deletion | Only designated owned scratch is eligible |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
