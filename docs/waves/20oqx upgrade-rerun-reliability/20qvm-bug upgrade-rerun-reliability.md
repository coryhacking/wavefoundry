# Make upgrade reruns terminal and content-stable

Change ID: `20qvm-bug upgrade-rerun-reliability`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-15
Wave: `20oqx upgrade-rerun-reliability`

## Rationale

A repeated ordinary invocation for the installed full build should refuse before adoption work, without claiming that the installation is healthy or terminal. Repair repeated adoption, misleading success results, generated timestamp churn and incomplete retired-storage cleanup without weakening index compatibility or recovery ownership.

## Requirements

1. Inspect retained recovery state before same-build detection. An ordinary invocation selecting the installed full VERSION/build refuses before creating a checkpoint, rendering, model work or indexing; it reports the already-installed build and supported repair commands, not terminal health. A matching semantic version with a different full build may proceed. Same-full-VERSION content disagreement is an identity collision, also refused. Compare canonical framework identity where available, not the outer lean/combined model wrapper; no new terminal receipt or completion inference is introduced.
2. Explicit --update-index and --rebuild-index repair requests bypass ordinary same-build refusal. --rebuild-storage keeps its independent applicability checks: pending legacy conversion may rebuild; absent legacy storage or an already-complete receipt refuses with guidance. Failures and required operator action must not be reported as completed success. Preserve documented phased runner and old-parent/new-child compatibility and the existing distinction between ordinary index-repair/unlock policy and fatal guarded recovery.
3. Verify later-day byte stability through the registered renderer and upgrade/docs-gate paths. Preserve existing missing-only carrier behavior; change a timestamp writer only if a bounded fixture reproduces churn there. Same-build refusal must prevent a repeat docs gate from re-stamping the target. Do not globally ignore metadata in memory fingerprints; real content changes remain visible to historical-memory validation.
4. Before a new legacy storage rebuild, capture the retired graph directory and allowlisted regular-file identities in the existing storage receipt, without a new file or tree snapshot. After verified publication and positively established old-host release, remove only those entries with no-follow, deletion-time identity checks. Unknown/new entries, replacements, nested directories, links/reparse points and uncertain hosts preserve the whole graph directory and recoverable cleanup state. Older receipts without graph identity evidence preserve and report the directory; already-complete receipts stay no-ops. Resume must reuse captured ownership, never adopt new entries by name.
5. Document storage-rebuild applicability with and without legacy storage, same-build refusal, explicit index repair and retained recovery commands using the actual public entry-point behavior.

## Scope

In scope: the requirements above, registered entry-point regressions, canonical guidance and necessary generated surfaces.
Out of scope: unrelated refactoring, timing investigation, production-target mutation, external publication and release execution.

## Acceptance Criteria

- [x] AC-1: Registered CLI and MCP tests show ordinary same-full-build reruns refuse nonzero/non-success without adoption writes, rendering/indexing or a new checkpoint; same-build content collision also refuses, different full builds proceed, and explicit index repair reaches its intended path.
- [x] AC-2: Pending recovery is handled before rerun detection; injected index failure and action-required results cannot be mistaken for completed adoption by CLI or MCP, while supported phase completion remains compatible.
- [x] AC-3: A later-day render with unchanged content preserves bytes; ordinary same-build retry does not run the docs gate or create memory work. A bounded upgrade/docs-gate fixture identifies any remaining timestamp-only churn before a writer is changed; substantive content changes still trigger expected memory work.
- [x] AC-4: A newly captured receipt removes allowlisted retired graph artifacts after verified rebuild and host exit; changed identities, unknown/new/nested/link entries, live or uncertain hosts and unverified publication preserve the directory and retry state. Missing graph evidence and already-complete historical receipts remain conservative; corrected refusal retries use the original captured identities.
- [x] AC-5: Upgrade instructions describe no-legacy storage-rebuild refusal, explicit index repair, ordinary same-build refusal and phase/recovery outcomes accurately.

## Tasks

- [x] Reproduce terminal, pending, later-day and explicit rebuild paths through public entry points.
- [x] Implement conservative same-build refusal and truthful outcomes without bypassing precision checks.
- [x] Prove later-day carrier stability, fix only reproduced timestamp churn, and extend verified cleanup ownership in the existing receipt.
- [x] Add targeted regressions and update upgrade seed and rendered guidance.
- [x] Complete readiness before code edits and required delivery review; retain durable results in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation and guidance | Implementer | Readiness | Single write owner; serialize shared files |
| Verification and review | QA and required reviewers | Implementation | Read-only review; coordinator records evidence |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/docs_gardener.py` (only if the registered-path fixture identifies it as the timestamp owner)
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`
- `docs/architecture/data-and-control-flow.md`

Write ownership: implementer owns admitted behavior and its derived callers/tests. Canonical seed edits precede regeneration; do not hand-patch generated surfaces. Reviewers are read-only. Protect publication guards, recovery checkpoints, unrelated user hooks/docs, secrets and existing evidence; no historical ledger rewrites. Confirm exact seed/config edits during Prepare before opening gates.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` and applicable canonical setup, extension, lifecycle or release guidance.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core observable contract |
| AC-2 | required | Core observable contract |
| AC-3 | required | Core observable contract |
| AC-4 | required | Core observable contract |
| AC-5 | required | Core observable contract |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Readback: refuse ordinary same-full-build adoption before rendering/indexing (previously it repeated adoption); retained recovery and explicit repair keep precedence. Make publication failures non-success, prove unchanged-date stability, and capture retired graph ownership in the existing receipt before safe cleanup. AC-1–AC-5; upgrade/storage scripts, focused tests, seed 160 and architecture guidance only. No new receipt files, snapshots, timing work or closure. | Approved plan and current public entry points |

| 2026-10-15 | Implemented same-full-build refusal, validated retained-continuation precedence, explicit storage applicability and observed publication outcomes. Incoming old-parent hook captures its actual index return and restores the original function; unknown/failed outcomes cannot seal memory. Equality always refuses, so identical and colliding same-label archives receive the same refusal, with no outer-archive hash used as admission authority. Preflight has no shared installed/pack canonical source digest; it does not claim their bytes match or define a new digest merely to distinguish refusal wording. | CLI/MCP rerun tests; real process resume suite |
| 2026-10-15 | Added receipt-bound graph ownership for both legacy and schema-kind receipts. Complete classification precedes deletion; descriptor identity checks refuse replacements. Concurrent changes after the first unlink can leave partial progress; retry reuses captured identities. Platforms without descriptor-safe deletion retain graph and cleanup state; no native Windows execution claimed. | Storage cleanup and ownership tests |
| 2026-10-15 | Next-day registered rendering is byte-stable. Upgrade docs-gate fixture executes the real gardener: unchanged docs remain stable, substantive changed docs keep their change and receive the date. No renderer/gardener writer change or memory fingerprint exclusion was needed. | DateStabilityTests |
| 2026-10-15 | Focused verification: 17 new rerun/ownership/date tests and three affected storage tests passed together (20 tests, 4.25s); storage file 127 passed before final narrowly tested additions; upgrade file 773 had one None-return success fixture, repaired and targeted rerun green; 25 targeted main/guidance cases passed. Three seam files ran 92 cases; only four retained-continuation cases exposed equality ordering, repaired and all five real process-resume cases passed (36.4s). Full docs validation and diff check passed. Canonical aggregate suite and independent delivery review remain coordinator work. | Temporary logs outside repository; named regression tests in scripts/tests |
| 2026-10-15 | Guard mutation pins all detected: remove equal-build refusal → same_build_cli test; remove validated-recovery exception → validated_retained_continuation test; remove rebuild applicability → absent_legacy_rebuild test; remove graph directory identity → replaced_empty_directory test; remove persisted file identity → missing_evidence_and_replacement test; remove deletion-time identity → deletion_time_swap test; allow unknown index outcome → parent_exception test; remove nonzero publication result → failed_primary_index_publication test. Mutants executed in memory only and restored; no source snapshot or permanent evidence folder. | test_upgrade_rerun_reliability and UpgradeManifestRecoveryTests; eight detected mutants |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Choose conservative refusal of ordinary same-full-build adoption, with retained recovery precedence and explicit index repair. | Installed identity does not prove terminal health; refusal avoids new completion receipts and repeated adoption work. | Successful no-op needs durable terminal proof; always rerun repeats migrations; refusing every equal semantic version blocks newer builds. |

## Public Outcome Matrix

| State | CLI / MCP result | Recovery and mutation rule |
| --- | --- | --- |
| Retained recovery, including malformed or unreadable ownership | Existing continuation or explicit refusal wins before identity comparison | Preserve checkpoint and original pack binding; no new adoption |
| Ordinary same full build, including identity collision | Nonzero / non-success preflight refusal | No adoption work or completion claim; direct operator to supported index repair or owning continuation |
| Different full build | Existing adoption path | Preserve validation, precision and publication gates |
| Explicit index update/rebuild | Existing observed result | Equality refusal does not swallow repair |
| Storage rebuild without applicable pending legacy conversion | Explicit applicability refusal | Preserve storage; recommend appropriate index repair |
| Successful primary phase | Existing zero phase-success result | Clearly phase complete with cleanup still pending; not terminal adoption |
| Index publication failure | Nonzero / failed publication | Preserve existing ordinary repair/unlock policy separately from fatal guards; never report phases complete |
| Memory/host action required | Existing typed action-required exit and MCP result | Retain owning continuation |
| Successful cleanup | Existing zero terminal result | Only report observed obligations; a previous index failure is never recast as successful publication |

## Open Decisions

No unresolved operator scope decision. Prepare must verify exact API/schema compatibility and source-derived affected paths.

## Risks

| Risk | Mitigation |
| --- | --- |
| Version-only equality can hide changed artifacts; compare actual supported identity and test retained-state precedence. | Use public-path positive and negative controls; preserve contracts outside scope. |
| Review overhead | Keep durable conclusions in wave.md and temporary probes outside tracked evidence folders; reuse valid qualification. |
