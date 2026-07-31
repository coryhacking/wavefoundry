# Guided One-Command Protocol-Bridge Upgrade Handoff

Change ID: `1txh7-enh protocol-bridge-upgrade-handoff`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-07-30
Wave: `1tz6l release-upgrade-hardening`

## Rationale

The protocol-1 to protocol-2 upgrade boundary correctly refuses to let the attached 1.14 runner
extract a 1.15 feature pack or replace itself in-process. The current operator experience obscures
that designed boundary: the incoming extension emits structured `bridge_release_required` data, but
`wf_upgrade` reduces the subprocess result to generic `upgrade_failed`; the agent then inspects raw
output and bridge source, discovers several adjacent release assets, stops the dashboard, asks the
operator to disconnect MCP, runs a bridge command, and finally runs a second hash-pinned feature
command. The upgrade is safe but feels broken and requires framework archaeology at the point of
highest operator uncertainty.

Keep explicit host quiescence and the no-self-replacement rule. Make the unavoidable interaction
simple: the normal MCP call returns one bounded handoff, the operator stops or disconnects
Wavefoundry MCP, the agent runs the self-contained package through its ordinary non-MCP shell, and
the operator fully restarts every attached host after completion. The operator must not have to
copy or type a terminal command, but the framework also must not introduce a detached supervisor
merely to move an already-capable agent shell outside the process being replaced.

## Requirements

1. Preserve the protocol boundary: a protocol-1 runner never extracts a protocol-2 feature pack,
   the running MCP process never replaces its own framework tree, and no tool kills an agent host or
   silently asserts host quiescence.
2. Have the distribution builder emit exactly one public package named
   `wavefoundry-<version>.zip`. The normal extractable feature pack also carries a standard-library
   Python entry point, the existing bridge bootstrap, selection metadata, bridge archive, and exact
   feature payload. The embedded selection continues to SHA-256-bind both payload archives and
   identify their supported source and destination protocols. No sibling special-purpose upgrade
   package or public bridge-composition files may remain in `dist/`.
3. After explicit `--confirm-hosts-stopped`, the bundle must acquire the existing lifecycle,
   publication, and dashboard locks; validate installed source and embedded hashes; atomically install
   the bridge with rollback; and immediately execute the existing hash-pinned feature-upgrade argv.
   The operator must not copy or run a second command for the normal path.
4. Return one bounded structured result covering both hops: source and target versions/protocols,
   bridge install state, feature-upgrade exit/state, rollback path, upgrade log, `restart_required`,
   and one exact recovery action when the feature phase pauses or fails. Preserve the normal retained
   upgrade checkpoint rather than inventing a parallel recovery state.
5. Improve the incoming protocol-2 feature extension's protocol-1 refusal payload so even the already
   shipped 1.14 wrapper's raw output contains an immediately usable handoff: `bridge_release_required`,
   why in-process continuation is impossible, the expected bundle path, bundle presence, an exact
   path-safe command when present, the explicit host-stop requirement, and restart/retry guidance.
6. Teach the current `wf_upgrade` wrapper to parse the known structured refusal and promote it into
   typed response data and a dedicated diagnostic instead of returning only generic
   `upgrade_failed`. Unknown subprocess failures keep the existing generic behavior.
7. Update the upgrade prompt to stop at this boundary without source inspection or speculative shell
   recovery. It should stop the dashboard through MCP when possible, tell the operator exactly which
   agent/MCP hosts must be stopped, have the agent execute the exact returned argv through its
   ordinary non-MCP shell without asking the operator to copy or type it, and resume verification
   after every attached host restarts.
8. Keep the bundle platform-neutral and repository-independent: native Windows, WSL2, macOS, and
   Linux use the same committed Python entry point, with path quoting tested for spaces, backslashes,
   Unicode, and POSIX paths. The structured argv list is the execution authority; any displayed
   command is a rendering of that argv for the detected host and must not be parsed back into
   authority. Do not embed build-host absolute paths.
9. Preserve local-only operation and explicit artifact acquisition. This change does not add network
   downloads to the MCP server; release documentation and refusal guidance must identify the single
   Wavefoundry package used for normal and protocol-bridge upgrades. Legacy internal
   bridge components may still be built to compose and verify the bundle, but must not be presented
   as alternative operator steps in the normal handoff.
10. Keep lifecycle-carrier reconciliation fail-closed for project-authored prose that is not an exact
    registered baseline, but return the complete bounded recovery worklist in the first failure:
    every matched retired token, its line, and one explicit edit-and-retry action. A user must not
    discover one retired token per upgrade attempt.
11. Make review-policy adoption convergent for realistic pre-1.15 repositories. The renderer must
    add or refresh framework-owned marker regions carrying every newly required policy obligation in
    each existing registered carrier, while preserving all project-authored bytes outside those
    regions and never creating an absent conditional document. Validation-only direct-document rows
    remain validation authorities; separate renderer rows own only the portable baseline regions.
12. Make lifecycle-ID memory migration repair every durable `memory_backfill_sources.memory_id`
    reference to a renamed record, including rewritten or superseded candidates whose legacy slug
    changes under the canonical `slugify` normalization. Retry after an interrupted rename must
    derive the same mapping from current on-disk records and must not leave a permanently missing
    historical candidate.
13. Make docs-gate recovery compose with the historical-memory gate. A successful
    `resume_after_gate` must clear only the docs failure marker, establish or refresh the canonical
    memory backfill run, and persist a phase accepted by `resume_after_memory`; pending validation
    must return the existing action-required result and recovery instruction rather than suggesting
    index publication prematurely.
14. Make the receipt-owned index publication handshake model the complete multi-pass Phase 4 build.
    A later graph-maintenance pass at the same successful generation must not invalidate the staging
    receipt solely because it owns a different child attempt ID. A different generation, incomplete
    epoch, corrupt receipt, or mismatched inventory must still fail closed.
15. Keep the post-upgrade retired-surface reconciliation scan focused on live target-repository
    carriers. Framework-owned `framework.rollback-*` recovery trees created by the protocol bridge
    are inactive history and must not surface as stale live guidance; similarly named project files
    and directories remain in scope.
16. Make the supported protocol-bridge handoff agent-driven without a detached supervisor. The
    incoming refusal must return the exact standalone argv and an ordered contract: stop the
    dashboard and every Wavefoundry MCP server for the repository, run that argv through the agent
    host's ordinary non-MCP shell, keep the session otherwise idle during cutover, then fully restart
    every attached host before lifecycle mutation resumes. The operator may perform the host/MCP
    stop and restart, but must not have to copy, synthesize, or type the terminal command.
17. Represent a historical-memory pause honestly. Exit 4 with
    `state=awaiting_memory_validation` must not persist `failed_phase=docs_gate`, print docs-failure
    recovery, or require `resume_after_gate` after the docs gate has passed. `resume_after_memory`
    must remain directly callable from the retained memory phase. If canonical inventory
    synchronization proves the validation worklist is empty, the upgrade must automatically advance
    through memory publication rather than pausing for a no-op backfill invocation.
18. Bound every MCP-visible upgrade response emitted by the current 1.15-or-later wrapper, including
    both human output and structured summary collections. Large seed diffs, carrier bodies, and
    repeated subprocess output belong in the upgrade log or a named bounded artifact; the response
    carries summaries, named total/returned/remaining counts, paths, and exact recovery argv.
    Truncation must be explicit and must never remove the terminal state, diagnostic, or recovery
    action. An already-running protocol-1 wrapper cannot be retroactively capped by an incoming pack;
    document that compatibility boundary honestly and provide an agent-shell fallback for a host
    overflow so the operator still never has to copy or type a terminal command.
19. Make review-policy reconciliation actionable without guessing at project prose. For a known
    carrier whose exact baseline no longer matches, return the registered replacement text or a
    deterministic patch preview alongside every token/line match. Also scan all live, nonhistorical
    Markdown for retired lifecycle instructions and report matches outside registered carriers,
    excluding closed wave history and generated rollback/upgrade assets. Only exact framework-owned
    or registered-baseline sections may be rewritten automatically; ambiguous project prose remains
    fail-closed.
20. Derive dashboard quiescence from the canonical lifetime lock and process metadata rather than an
    obsolete status file. A refusal must identify the Wavefoundry service, PID when available, and
    exact stop action; the plan and error output may not simultaneously report the dashboard as
    stopped while its lock is held.
21. Keep upgrade-created recovery assets out of project work and reconciliation noise.
    `.wavefoundry/framework.rollback-*` and `.wavefoundry/upgrade-assets/` must be covered by the
    managed ignore contract; retained rollback remains available until successful cleanup or explicit
    operator removal. Reconciliation findings from host-local permission files such as
    `.claude/settings.local.json` must be classified under `host_permission_flags`, not mixed with
    agent-editable project reconciliation.

## Scope

**Problem statement:** A deliberately safe protocol bridge currently surfaces as a generic failure
and requires manual inspection, multi-asset coordination, and a two-command handoff.

**In scope:**

- An executable bridge/feature entry point inside the normal builder-produced Wavefoundry package.
- Agent-shell execution of both verified hops after explicit quiescence, without user-entered
  terminal commands or a detached supervisor.
- Structured `bridge_release_required` propagation and exact recovery guidance.
- Honest, composable docs/memory phase state and zero-work automatic advancement.
- Bounded MCP output, actionable lifecycle reconciliation, dashboard-owner diagnostics, and
  upgrade-artifact/host-permission classification.
- Upgrade prompt, release asset, platform, integrity, rollback, and recovery tests.

**Out of scope:**

- Allowing an MCP server to overwrite its own running framework.
- Automatically killing, disconnecting, or restarting agent hosts.
- A background supervisor, timer, or host hook that continues the protocol bridge after the
  invoking interaction ends.
- Inferring or forging `--confirm-hosts-stopped`; the standalone runner must still verify its locks.
- Adding network access or automatic GitHub downloads to target repositories.
- General redesign of protocol-2 upgrades that do not require a bridge.

## Acceptance Criteria

- [x] AC-1: A tagged protocol-1 fixture receiving the protocol-2 feature still refuses before any
  target-repository mutation and reports `bridge_release_required`.
- [x] AC-2: The refusal returned through the old-runner-compatible output names the one package and,
  when it is present, one path-safe command plus the exact stop/restart sequence; no source inspection
  or command synthesis is required.
- [x] AC-3: Running that one command without `--confirm-hosts-stopped` or while any serialization lock
  is held refuses before extraction; the tool never kills a process or supplies the confirmation.
- [x] AC-4: With confirmed quiescence, the bundle verifies both embedded hashes, installs protocol 2,
  executes the exact selected feature archive once, and reaches the same terminal or retained recovery
  state as the existing two-command flow.
- [x] AC-5: Corrupt bundle metadata, either corrupt nested archive, source-version mismatch, path
  escape, protocol mismatch, or failed bridge verification leaves the original framework intact.
- [x] AC-6: A failure after the framework swap restores or retains the documented rollback and emits
  one exact recovery action; a feature-phase docs or memory pause uses the existing upgrade checkpoint.
- [x] AC-7: The current `wf_upgrade` MCP envelope promotes a recognized bridge refusal into typed data
  and a dedicated diagnostic while preserving generic handling for unrecognized failures.
- [x] AC-8: Builder and release tests prove the single package contains the exact bridge and feature
  bytes identified by selection metadata and is the only release asset.
- [x] AC-9: Native Windows, WSL2, macOS, and Linux path fixtures produce executable commands without
  render-host absolute paths or shell-specific quoting assumptions; structured argv remains the
  canonical executable form in every result.
- [x] AC-10: The canonical upgrade prompt describes the one-action/one-command/restart flow and no
  longer directs agents into bridge-source archaeology.
- [x] AC-11: One ambiguous lifecycle carrier containing multiple retired phrases fails before every
  write and reports all matching token/line pairs plus the exact edit-and-retry recovery in one
  diagnostic; removing the listed project prose lets the same upgrade proceed.
- [x] AC-12: A realistic pre-1.15 fixture whose existing direct documents lack the new review-policy
  vocabulary passes production review-policy validation after surface rendering. The render is
  byte-stable on retry, preserves project prose byte-for-byte outside owned markers, and does not
  create absent conditional documents.
- [x] AC-13: A same-version successor upgrade matching the external rewritten/superseded case — a
  maximum-length legacy `mem-` id whose suffix normalizes by removing a trailing dash — automatically
  rewrites its durable `memory_backfill_sources.memory_id` to the sole verified on-disk lifecycle ID
  through the canonical inventory synchronization path. A second pass is clean, the candidate is not
  reported as missing, and absent or ambiguous matches remain actionable rather than being guessed or
  dropped.
- [x] AC-14: Starting from a retained `failed_phase=docs_gate` checkpoint whose prior phase is
  `review_sidecar_cleanup_complete`, the public `resume_after_gate` path succeeds and leaves
  `resume_after_memory` usable. If that resume still finds pending memory work, it returns the existing
  action-required result while restoring `current_phase=awaiting_memory_validation`, so the documented
  `memory_backfill` and `memory_validate` recovery tools remain callable. Existing refusal controls
  still prevent memory publication while the docs marker remains failed.
- [x] AC-15: A public `resume_after_memory` fixture runs the real docs/code/graph Phase 4 sequence in
  which graph maintenance completes the same generation under a later attempt ID. Publication accepts
  that completed generation and marks the memory run indexed. Controls prove that a stale generation,
  incomplete build epoch, corrupt receipt, and mismatched inventory digest still refuse publication.
- [x] AC-16: The shipped reconciliation scan excludes retired references beneath an actual
  `.wavefoundry/framework.rollback-*` bridge backup while still finding them in a similarly named
  `.wavefoundry/framework.rollback-notes.md` file and a project-owned
  `docs/framework.rollback-*/` directory.
- [x] AC-17: The real incoming `post_preflight` refusal returns bounded structured argv and the
  stop-MCP → agent-shell-run → full-host-restart sequence. A host automation fixture can execute the
  returned argv without parsing a display command; no detached process is queued, no host is killed,
  and the bundle still refuses while a required lock is held. Every bridge carrier must name the
  restart of every attached host, not only the invoking host.
- [x] AC-18: A real docs-success/memory-pause run records no docs failure, gives
  `resume_after_memory` as the direct recovery, and an empty canonical validation worklist advances
  automatically to index publication. A nonempty worklist still pauses with its exact retained run
  and cannot publish early.
- [x] AC-19: The public current-wrapper MCP envelope for a worst-case seed-diff/refusal fixture stays
  below the named byte/character cap while preserving state, diagnostic, counts, log path, and
  recovery argv; both raw output and repo-sized structured-summary collections are bounded, and the
  same fixture proves omitted detail is present in the named log or bounded artifact. A tagged
  protocol-1 control proves and documents the unretrofit-able old-wrapper boundary plus the
  no-operator-command agent-shell fallback.
- [x] AC-20: Preflight reports all retired-token matches across registered carriers and all other
  live Markdown. Known carriers include their canonical replacement or patch preview; ambiguous
  prose is never auto-rewritten; `docs/waves/` history and generated framework/index/rollback/
  upgrade-assets paths remain excluded without excluding live project guidance elsewhere under
  `.wavefoundry/`.
- [x] AC-21: A held canonical dashboard lock makes both plan and refusal report the dashboard as
  running and identify its PID/service plus the exact stop action. The stopped control remains clean
  on native Windows, WSL2/Linux, and macOS.
- [x] AC-22: Managed ignore rendering covers rollback and upgrade-assets paths, live reconciliation
  excludes them, and stale exact-name rules in a host-local permission file surface only under
  `host_permission_flags`; similarly named project-owned paths remain visible.

## Tasks

- [x] Add the self-contained upgrade entry point to the normal package in `build_pack.py` and keep
  release orchestration to that one asset.
- [x] Reuse the canonical bootstrap/install functions inside the bundle; do not fork bridge logic.
- [x] Add explicit combined-hop execution and structured terminal/recovery output.
- [x] Enrich the incoming `bridge_release_required` payload for the shipped protocol-1 hook surface.
- [x] Parse and promote the refusal in `wf_upgrade_response`.
- [x] Update seed 160, rendered upgrade guidance, package/release references, and architecture flow.
- [x] Add protocol-floor, no-mutation, integrity, rollback, retained-recovery, and cross-platform path
  tests using the real builder artifacts.
- [x] Execute a tagged 1.14.0 → candidate 1.15.0 end-to-end upgrade rehearsal from the documented
  operator flow before release.
- [x] Return a complete bounded retired-token recovery worklist from lifecycle-carrier preflight.
- [x] Register and render framework-owned review-policy baseline regions for all existing carrier
  classes, then prove adoption through the production validator on a realistic pre-1.15 fixture.
- [x] Reconcile uniquely resolvable legacy memory IDs inside the canonical transactional inventory
  synchronization path, including same-version successor upgrades, and pin no-match, ambiguity, and
  idempotent retry behavior.
- [x] Keep `resume_after_memory` in the callable historical-memory recovery phase whenever pending
  work remains, and pin the complete docs-gate-to-memory-gate recovery sequence through the public
  CLI entry point.
- [x] Bind the staging receipt to the completed multi-pass generation rather than an intermediate
  child attempt, and pin the exact external graph-restamp sequence plus all fail-closed controls.
- [x] Exclude generated protocol-bridge rollback directories from the live reconciliation scan while
  retaining positive coverage for similarly named project paths.
- [x] Replace the rejected supervisor wording with the agent-shell handoff in seed 160, rendered
  prompts, MCP diagnostics, and upgrade architecture.
- [x] Separate memory action-required state from docs failure state and auto-advance empty worklists.
- [x] Cap MCP-visible upgrade output and structured summaries and move omitted detail to the existing
  log/bounded artifact, with an honest protocol-1 compatibility fallback.
- [x] Surface known lifecycle replacements and widen report-only retired-token coverage to live docs.
- [x] Make dashboard plan/refusal output consume canonical lock/process ownership.
- [x] Render ignore coverage for upgrade artifacts and route host-local permission drift separately.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Bundle format and builder | implementer | — | One asset, canonical nested bytes and hashes. |
| Bridge/feature orchestration | implementer | Bundle format | Preserve locks, rollback, and retained state. |
| MCP refusal promotion | implementer | Refusal contract | Additive typed response for current runners. |
| Operator guidance | docs-contract-reviewer | Refusal contract | One stop action, one command, one restart. |
| Cross-version rehearsal | qa-reviewer | All implementation work | Exercise tagged 1.14.0, not a hand-built stand-in. |

## Serialization Points

- `build_pack.py` must define the artifact bytes before the bootstrap and release tests consume them.
- The incoming extension payload, current MCP parser, and seed 160 are one contract and must change
  together.
- Combined-hop execution must reuse the existing upgrade checkpoint and lock ordering.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — replace the two-command bridge handoff with the
  self-contained combined-hop flow while retaining quiescence and rollback boundaries.
- `docs/specs/mcp-tool-surface.md` — define the structured `bridge_release_required` response.
- `docs/contributing/build-and-verification.md` — document the single-package release and rehearsal.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserves the safety boundary. |
| AC-2 | required | Defines the operator-facing usability outcome. |
| AC-3 | required | Prevents automation from weakening quiescence. |
| AC-4 | required | Proves the one-command path actually completes both hops. |
| AC-5 | required | Integrity and no-mutation failure behavior are release-critical. |
| AC-6 | required | Recovery must converge without a second authority. |
| AC-7 | required | MCP must expose the designed boundary rather than generic failure. |
| AC-8 | required | The release asset must be reproducible and internally bound. |
| AC-9 | required | All supported platforms are first-class. |
| AC-10 | important | Agents need a stable, non-archaeological recovery recipe. |
| AC-11 | required | A fail-closed preflight must still provide complete recovery rather than an edit/retry loop. |
| AC-12 | required | A supported pre-1.15 repository must not deadlock at a newly activated policy gate after rendering. |
| AC-13 | required | Historical-memory migration must not strand durable candidate references after a filename rename. |
| AC-14 | required | The documented recovery phases must compose; clearing one gate cannot make the next recovery verb unreachable. |
| AC-15 | required | Publication must accept the completed multi-pass generation without weakening the exact receipt CAS. |
| AC-16 | required | A successful bridge upgrade must not report its own inactive rollback tree as live project drift. |
| AC-17 | required | The normal path should require host stop/restart, not a user-entered terminal command or a supervisor. |
| AC-18 | required | A memory pause must not masquerade as a docs failure or require a no-op recovery cycle. |
| AC-19 | required | Oversized MCP output can hide the only actionable state from the invoking host. |
| AC-20 | required | Reconciliation must cover live guidance while preserving project-authored authority. |
| AC-21 | required | Quiescence guidance is unsafe when service state and lock state contradict each other. |
| AC-22 | important | Upgrade-owned artifacts and host-local permissions must not pollute the project worklist. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-30 | Reproduced the protocol-floor refusal in an external 1.14.0 project and stopped before mutation. | Attached transcript: `bridge_release_required`; `wf_reload_mcp` could not cross the installed protocol boundary; dashboard stopped cleanly. |
| 2026-07-30 | Traced the friction to response and packaging seams rather than the bridge safety design. | Incoming hook emits structured paths; MCP wrapper returns generic `upgrade_failed`; bootstrap installs the bridge and returns a second command instead of executing it. |
| 2026-07-30 | Built the executable package entry point, typed refusal promotion, retained hash-bound feature path, and bounded combined-hop result. | `test_upgrade_protocol.py`: 16/16; `WaveUpgradeMcpToolTests`: 28/28; release orchestration tests green. |
| 2026-07-30 | Rehearsed the documented command against an isolated checkout of local tag `v1.14.0`. | Bridge installed protocol 2; feature runner reached its real docs gate; existing checkpoint retained `failed_phase=docs_gate`; result supplied exact `--resume-after-gate` argv, rollback path, log, and restart requirement. |
| 2026-07-30 | Completed canonical verification. | Full framework suite 6,509/6,509 across 61 files; docs-lint clean; both edit gates closed. |
| 2026-07-30 | Repaired all delivery-review findings with executed cross-platform controls. | Build IDs are bounded before staging; POSIX and Windows payload paths are both contained; Windows handoff converts `pythonw` to the console interpreter; busy lock probes preserve owner bytes; spawn failures and primary success return total recovery; release `main()` wiring is load-bearing. Original adversarial probes now reject before mutation; full suite 6,518/6,518 across 61 files. |
| 2026-07-30 | Closed the final independent-review gaps in staging and operator carriers. | Feature retention now uses an exclusively created regular staging file and verifies the final contained archive; a full-install regression preserves an external sentinel despite a pre-existing old predictable staging link. The public Windows refusal payload pins the console interpreter at the call site. Release, upgrade, architecture, persona, README, package, and changelog carriers now agree on the single package and first-class native Windows flow. Full suite 6,520/6,520. |
| 2026-07-30 | Corrected the release shape to the product's one-package contract and rebuilt locally. | `build_pack.main` now leaves exactly `dist/wavefoundry-1.15.0.pfps.zip`; the same archive is directly extractable and executes its protocol bridge. Focused packaging/protocol tests 128/128, public MCP handoff parser test green, canonical suite 6,520/6,520, docs-lint clean, and `python3 dist/wavefoundry-1.15.0.pfps.zip --help` succeeds. |
| 2026-07-30 | An external 1.14.0 project exercised the new package and exposed two adoption gaps after the bridge succeeded. | Lifecycle preflight revealed two retired phrases across separate edit/retry attempts; surface rendering then activated review-policy validation without supplying 11 required obligations across seven existing documents. The retained checkpoint and rollback remained correct. |
| 2026-07-30 | Repaired both external adoption gaps without weakening ownership or validation. | Ambiguous lifecycle preflight now returns every canonical token and line in one atomic failure. Separate renderer companion rows add portable marker-owned policy baselines to existing direct docs; a real `v1.14.0` fixture passes the production validator after one render and is byte-stable on retry. Focused upgrade/renderer/policy verification passed 444/444; canonical suite 6,524/6,524; docs-lint clean. |
| 2026-07-30 | A continued external upgrade exposed a historical-memory recovery deadlock after the docs gate cleared. | A rewritten candidate retained a pre-normalization `memory_backfill_sources.memory_id`, and `resume_after_gate` left `current_phase=review_sidecar_cleanup_complete`, which both memory recovery and publication reject. |
| 2026-07-30 | Repaired the memory-ID retry and composed docs-gate recovery with the canonical memory checkpoint. | Red-first external-shape regressions now pass: memory records 179/179, upgrade 361/361, MCP upgrade wrapper 28/28. Canonical suite 6,526/6,526 across 61 files and docs-lint clean. Public seed, rendered prompt, architecture, spec, and MCP next-step guidance all route a recovered docs gate through `resume_after_memory`. |
| 2026-07-30 | Built the corrected single 1.15.0 distribution for external retry. | `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pfqg.zip`; SHA-256 `d97fa0ff02d27fed1505697f15677df48d8ba80e205febf5b11f22c1bb454dd5`; direct zipapp `--help` succeeds. Superseded `pfq6` moved to `/private/tmp`, leaving one 1.15.0 package in dist. |
| 2026-07-30 | The external `pfqg` retry refuted both recovery-completion claims and reopened AC-13/AC-14. | The version-gated broad rename migration did not run on the same-version successor, leaving one stale rewritten/superseded source row pending. `resume_after_memory` then returned action-required from `memory_resume_preflight` without restoring the publication-control phase, so the documented memory tools could not clear it. |
| 2026-07-30 | Moved stale memory-ID repair into every transactional inventory synchronization and made pending resume restore the recovery phase. | Red-first tests reproduced both external failures. Unique normalized mappings repair automatically and idempotently; missing mappings remain in the worklist; ambiguous or internally inconsistent mappings roll back and fail loud. Public `resume_after_memory` now restores `awaiting_memory_validation` on both pending and reconciliation-error paths. Focused verification: memory records 179/179, memory backfill 44/44, upgrade 364/364. Canonical suite 6,532/6,532 across 61 files. |
| 2026-07-30 | Built the automatic-recovery candidate directly into the canonical local distribution directory. | `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pfqq.zip`; SHA-256 `b39a93589adb32161fe14e2597ea74537dfe8d24372f559e5280e18305996f47`; direct zipapp `--help` succeeds. Superseded `pfqg` moved to `/private/tmp`, leaving exactly one 1.15.0 package in `~/.wavefoundry/dist`. |
| 2026-07-30 | The external `pfqq` retry proved the stale-memory repair, then exposed a deterministic final receipt mismatch. | `memory_id_references_repaired=1`, pending reached zero, and the index built healthy across 1,929 files. Three `resume_after_memory` attempts then failed because the staging receipt named the docs/code child attempt while graph idle-maintenance re-stamped the same completed generation under a later attempt ID. The generation matched; attempt identity alone blocked publication. |
| 2026-07-30 | Repaired the multi-pass receipt handshake without weakening exact-attempt publication. | The first child freezes generation and inventory authority; the final graph child atomically transfers that same frozen publication to its own attempt and rewrites the receipt; the parent retains the exact attempt-ID CAS. The external sequence was red before repair and green afterward. Wrong generation, wrong attempt, wrong run, corrupt/expanded receipt shape, non-building epoch, and changed inventory all refuse. Focused verification: index-state store 37/37, memory backfill 46/46, upgrade 365/365. Canonical suite 6,536/6,536 across 61 files. Two earlier saturated runs each had one unrelated flake (25.275 ms versus 25 ms CE p95; a live background-refresh registry entry); both exact tests passed alone and the quiet canonical rerun was fully green. |
| 2026-07-30 | Built the receipt-handshake repair for the next external retry. | `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pfsd.zip`; SHA-256 `84b39918dd2793d977579b24df98479ce0a7299c8782abec9f5f9143ae1f1769`; direct zipapp `--help` succeeds. Superseded `pfqq` moved to `/private/tmp`, leaving exactly one 1.15.0 package in the scanned dist directory. |
| 2026-07-30 | The external pfsd retry completed the full protocol bridge, memory publication, graph maintenance, cleanup, reload, and incremental index convergence. | Teton reached `1.15.0+pfsd` with the upgrade lock removed, 83 tools reloaded, `impl_matches_disk=true`, memory pending zero, receipt-owned publication successful, and the post-cleanup incremental index current. The same run exposed one bounded reconciliation false positive: the live scan descended into the retained `framework.rollback-bridge-pfps-p2` recovery tree. |
| 2026-07-30 | Removed inactive protocol-bridge rollback trees from the live reconciliation corpus without a broad name exclusion. | The canonical scanner excludes only paths whose first two components are `.wavefoundry/framework.rollback-*`; a same-prefix file and project-owned directory remain scanned. The pre-fix field-shaped probe returned the rollback carrier; focused regression and near-miss controls pass after repair. Canonical suite 6,536/6,536 across 61 files; docs-lint clean. |
| 2026-07-30 | A full agent-driven Solaris upgrade completed but required six standalone invocations and three diagnostic recoveries. | The field run exposed a docs-success memory pause mislabeled as `failed_phase=docs_gate`, a zero-item memory gate, a 347,970-character MCP response, dashboard-state contradiction, live retired guidance outside the carrier census, host-permission misrouting, and unignored upgrade assets. |
| 2026-07-30 | Replaced the unimplemented detached-supervisor proposal with the simpler operator-stop/agent-shell/restart contract and reopened implementation scope around the field-proven gaps. | The successful run proves no supervisor is needed: the agent already owns a non-MCP shell. The only irreducible interaction is full host restart across the tool-schema boundary; all intermediate machine-resolvable phases are now required to converge automatically. |
| 2026-07-30 | Implemented the Solaris field repairs across upgrade state, MCP output, reconciliation, service ownership, and managed artifacts. | A successful docs gate now clears its failure marker before memory work; one canonical bounded memory batch auto-advances only when the run-wide pending state is empty; MCP output is capped with count/log metadata; known carriers receive unified replacement previews while other live Markdown is report-only; the lifetime lock is authoritative and refusal guidance names the service/PID/stop action; rollback and upgrade-assets paths are rendered and excluded without hiding project-owned lookalikes. |
| 2026-07-30 | Completed focused and canonical verification. | Directly affected upgrade, memory, review-policy, protocol, rendering, and reconciliation modules passed 466/466. The canonical isolated runner passed 6,542/6,542 tests across 61 files and docs-lint is clean. One non-authoritative combined in-process unittest invocation reached CoreML and exited by signal 139 without an assertion summary; the canonical per-file runner subsequently passed the same `test_server_tools.py` surface at 1,519/1,519. |
| 2026-07-30 | Fresh amended-plan council review rejected three claims and one implementation boundary before approval. | Red-team reproduced a 1,047,683-character final envelope through an unbounded 10,000-row structured summary despite the 60K prose cap. Docs-contract review proved an incoming pack cannot retrofit the already-running 1.14 wrapper, `.wavefoundry/README.md` was hidden by an overbroad exclusion, and bridge carriers said singular host despite the every-attached-host requirement. AC-17/19/20 and their tasks reopened. |
| 2026-07-30 | Repaired and independently re-falsified every amended-plan council finding. | The current-wrapper contract is honest about the unretrofit-able protocol-1 boundary and assigns overflow fallback to the agent shell. Public response probes for dual 10,000-row collections, 180K scalar/nested summary values, and oversized bridge prose/unknown fields returned 85,173, 61,635, and 73,497 characters respectively under the 100K cap while preserving terminal diagnostics, exact recovery argv, and log path. `.wavefoundry/README.md` and a same-prefix notes file remain visible while generated framework/index/rollback/assets trees stay excluded. Every bridge and rename-boundary carrier says restart every attached host; mutation probes caught all three regressions; the rendered upgrade-policy marker is byte-identical to its canonical block. |
| 2026-07-30 | Completed canonical verification on the final repaired tree. | The isolated framework runner passed 6,545/6,545 tests across 61 files, including 1,522/1,522 server-tool tests; docs-lint is clean and diff whitespace validation passes. |
| 2026-07-30 | Repaired and independently re-falsified the final delivery-review escape paths before signoff. | The upgrade response now budgets scalar values, scalar omission metadata, collection keys/metadata, diagnostics, and bridge argv by serialized size where escaping matters, with a fixed-shape final fallback; adversarial public envelopes remained below 100K while terminal state and valid exact argv survived. `build_pack.main` fingerprints every top-level `wavefoundry-*` artifact, rejects stale or newly emitted special/composition siblings, preserves older canonical release zips, and cleans bridge artifacts even when validation fails. All four executable recovery branches and public carriers assign shell execution to the agent and require restart of every attached host. Independent code, architecture, QA, docs-contract, and release reverification passed; the final canonical suite passed 6,564/6,564 across 61 files. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-30 | Preserve explicit quiescence and no self-replacement. | Those are real integrity and concurrency boundaries, not incidental friction. | Hot-swapping the live MCP runner and automatically killing hosts were rejected. |
| 2026-07-30 | Make the one normal Wavefoundry zip both extractable and directly executable for the verified two-hop upgrade. | It removes the special upgrade package, multi-asset coordination, and the second copied command while preserving the existing hashes, locks, and rollback. | A sibling upgrade zipapp would create a second public package; documentation-only guidance leaves the failure-shaped UX intact. |
| 2026-07-30 | Corrected the package contract after an executed local build exposed two public outputs. | The product has one Wavefoundry distribution package; bridge pieces are internal payloads, not a second release surface. | Publishing a feature zip beside a special upgrade `.pyz` was rejected by the operator. |
| 2026-07-30 | Treat portable review-policy vocabulary as framework-owned marker content, separate from file-wide direct-document validation. | Older projects cannot be expected to invent new 1.15 policy language, while the marker boundary preserves project ownership and makes retries deterministic. | Weakening the validator or hand-editing each target project would hide drift and make adoption repository-specific. |
| 2026-07-30 | Keep ambiguous project lifecycle prose manual, but enumerate the full canonical match set in one preflight failure. | The framework must not guess how to rewrite custom prose, yet repeated single-token discovery is unnecessary friction. | Broad fuzzy replacement would mutate project-authored meaning without authority. |
| 2026-07-30 | Use the agent host's ordinary shell after MCP quiescence instead of adding a detached supervisor. | The external Solaris run proved the agent can execute the self-contained package and recovery argv directly; a supervisor adds lifecycle, process-census, status, and cross-platform machinery without removing the mandatory final host restart. | Detached supervisor and user-entered terminal command were rejected. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A convenience bundle becomes a second upgrade implementation. | Package and invoke the existing bootstrap and feature runner; keep one selection and lock/checkpoint authority. |
| Combined execution obscures partial success. | Emit separate bridge and feature states plus the existing retained checkpoint and rollback path. |
| The old 1.14 MCP wrapper cannot gain the new parser. | Put the exact command and operator action in the incoming feature hook's structured raw output; the current parser improvement covers future callers. |
| Cross-platform command rendering breaks on spaces or Windows paths. | Prefer argv execution inside the zipapp and test rendered human commands across native path forms. |
| Automatic continuation skips genuine memory judgment. | Auto-advance only after canonical synchronization proves the worklist is empty; retain the existing fail-closed pause for any actionable item. |
| A broad live-doc scan rewrites project history or authored prose. | Exclude closed wave history and upgrade assets; report outside registered carriers and mutate only exact owned/baseline sections. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
