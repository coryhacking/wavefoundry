# Complete setup with machine-local inference and no embedding work

Change ID: `22l9j-bug setup-machine-local-fallback-and-no-work`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-05
Wave: 22l9k setup-machine-local-fallback

## Rationale

An operator updating the Wavefoundry source checkout on another macOS ARM64 machine from 1.36 to 1.39 has no Tensorwell installation. Its full-precision index is current, but ordinary setup refuses with “Local fallback compatibility unverified” before reaching the incremental build; the setup stamp stays stale. A temporary-root control reproduces the current source: real published SQLite data, canonical all-content dry-run up_to_date=true, setup return 2 before build, no model preparation, published state unchanged. Native provider leaves were controlled; no affected-machine native qualification or release bisect ran. Git history attributes the added refusal to 6bfe8638, which includes wave 21kbd.

Source verification: setup_index._check_setup_precision assesses a predicted mismatch and then probe-dependent uncertainty; main calls it before model preparation/build_index. setup_wavefoundry.main writes its assessment stamp only after successful complete core setup. index_handlers._index_is_up_to_date explicitly declines content=all, whose build route invokes setup_index.py. inference_profile's shipped tensorwell mode is automatic optional discovery, not a per-machine installation requirement. provider_policy accepts the coreml override, but no override should be needed for compatible automatic local operation.

## Product Intent

A developer can update this same Wavefoundry checkout on machines with or without Tensorwell and complete ordinary setup using compatible locally available execution. A genuinely current incremental index needs no embedding preparation and setup can refresh its stamp after normal completion. Machines remain free to select different compatible execution without modifying tracked provider declarations. AC-1 through AC-4 establish these controlled paths; actual affected-host native execution remains a field verification limit. This supports the adopted vision's dependable existing delivery foundation without changing its destination or roadmap.

## Requirements

1. On ordinary incremental setup, establish whether all requested semantic work is current from the canonical indexer planning logic with matching scope/options and identities. Health summaries or a raw zero changed-file count alone are insufficient. Skip embedding model preparation and the unverified-fallback refusal only for a proven current plan; still run normal indexer validation/maintenance and the rest of setup. Full/rechunk, missing/incompatible storage, model/chunker/walker changes, changed/new files and requested detached layers must not acquire false no-work authority. Uncertain planning follows the normal guarded path.
2. Automatic optional Tensorwell discovery must remain machine-local. With Tensorwell absent/unselected, compatible local execution can proceed through the existing bounded provider selection/preparation path without a tracked configuration edit, environment override or Tensorwell installation. Availability alone is not proof of successful native execution: preserve bounded isolated probes, accurate fallback diagnostics and rechecking after provider decisions before incompatible preparation/publication. Explicit extension policy remains strict; failure of an already selected service operation must not silently retry locally.
3. Preserve the all-layer known precision-mismatch guards and explicit rebuild authority. No implicit full/int8 conversion, model/provider substitution incompatible with the retained index, destructive recovery, forged setup stamp, native-probe bypass or service installation/startup is introduced. An incompatible local decision must refuse safely with actionable local/rebuild guidance; Tensorwell is one optional compatible execution source, not a universal prerequisite. Recheck changed selection and source/plan currency at the existing execution boundaries; a no-work observation does not authorize later incompatible embedding.
4. Complete core setup refreshes the stamp through its existing owner only after successful setup/index validation. A refused or failed build does not claim readiness or refresh the stamp; partial/background setup keeps its existing stamp semantics. MCP all-content updates use the corrected setup route without a separate readiness bypass.
5. Preserve dependency-only, graph-only, prewarm-only, explicit provider, fresh setup, legacy provenance, local and extension behavior except for the stated correction. Explain the automatic optional-service/no-work contract and honest native-platform limits in the embedding architecture and changelog. No seed, generated prompt, provider declaration, dependency pin or release/version edits.

## Scope

In scope: setup_index.py; its provider-preflight tests; setup_wavefoundry tests for the existing stamp owner; existing handler tests if needed to verify the all-content route; embedding-model architecture; changelog; wave and handoff bookkeeping. A small reusable planning helper may be added inside setup_index.py using the existing indexer, without creating an independent planner or changing indexer precision semantics.

Out of scope: indexer.py/provider_policy.py/accel_embedder.py/inference_provider.py/tensorwell_client.py behavior changes, provider declarations, new configuration/storage schemas, actual Tensorwell installation, native model downloads, background-index redesign, general setup refactoring, native Windows/Linux qualification and a release. If canonical no-work proof requires changing these protected owners, amend this scope and re-Prepare before editing them.

## Acceptance Criteria

- [x] AC-1: Ordinary setup over a genuinely current full-precision index with automatic CoreML availability and no service completes without native embedding preparation; its real setup completion route refreshes the stamp. No-work proof uses canonical planning rather than only stale-path reporting. The unchanged candidate must reproduce the reported refusal.
- [x] AC-2: With new/changed embedding work and no Tensorwell, a compatible automatic local decision proceeds without tracked/provider overrides; an incompatible local decision still refuses without changing the prior published snapshot or claiming setup completion. Test both initial selection and a selection/provider change after assessment.
- [x] AC-3: Full/rechunk, scope-specific/detached work, identity/version changes, failed/uncertain planning and source changes after a no-work observation cannot falsely bypass work or authorize incompatible embedding. Existing explicit-local/extension, fresh/legacy, graph/dependency/prewarm-only and selected-service failure contracts retain meaningful controls.
- [x] AC-4: Failed or refused core setup leaves its stamp unchanged; partial/background completion does not create a full-core stamp. The all-content MCP path reaches the corrected setup route. Documentation states machine-local optional discovery, no-work behavior, retained compatibility guarantees and measured platform limits.

## Tasks

- [x] Implement canonical no-work preparation gating and compatible automatic local fallback with preserved precision checks.
- [x] Add production-entry regression and negative controls for setup, selection changes, stamp publication and the all-content route.
- [x] Update the embedding architecture and changelog, validate affected docs and run the canonical suite after material edits settle.
- [x] Obtain fresh required delivery reviews; reconcile evidence, limits and handoff without another automatic evaluation batch.

## Serialization Points

Coordinator owns protected source writes; all readiness/review workers are read-only. No overlapping write owners. Use current host capabilities for the bounded implementation; model-family agreement is not native qualification. Preserve unrelated work and actual visions. Source-first investigation uses MCP reads; synthetic probes use temporary roots only.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_provider_preflight.py`
- `.wavefoundry/framework/scripts/tests/test_setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `docs/architecture/embedding-model.md`

CHANGELOG.md is also an intended root-level documentation edit; it is not a new packaging/version change. Requested review lanes: code, QA, architecture and docs-contract.

## Affected Architecture Docs

Update docs/architecture/embedding-model.md, Optional Tensorwell execution, replacing the current blanket uncertainty-refusal description with the corrected no-work and machine-local fallback contract. No new architecture mechanism or interface is intended.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reproduces and fixes the observed setup loop. |
| AC-2 | required | Makes absence of an optional service a normal compatible-machine case while retaining protection. |
| AC-3 | required | Prevents a no-work optimization from authorizing stale or incompatible execution. |
| AC-4 | required | Makes readiness truthful and verifies the shared MCP/setup continuation. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Use canonical no-work planning to gate preparation and keep automatic local execution through existing probe/precision boundaries. | The fixture demonstrates a current plan refused before build. Skipping unnecessary preparation removes that failure; allowing the existing local path resolves the optional-service prerequisite while post-decision guards retain compatibility. No agent-adherence or native-host result is claimed from controlled tests. | No-work-only patch leaves changed-work local use broken. Force local policy or coreml override creates machine-specific setup burden and does not fix dynamic selection. Delete all precision guards permits incompatible vectors. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-05 | Verified current source and isolated reproduction before planning. All-content dry-run current; setup returns 2 before build; published state unchanged. | /private/tmp/wf-setup-no-work-repro.json; SetupProviderPreflightTests with real temporary SQLite snapshot and controlled provider/model leaves. |
| 2026-11-05 | Readback: use the existing indexer dry-run with matching content/options solely to omit unnecessary native preparation; retain the real build and stamp owner. Replace blanket uncertainty refusal with the existing guarded machine-local path, preserving repeated actual precision checks. Required readiness lanes and targeted council approve on the current receipt. | Review contexts setup_readiness_red, setup_readiness_codearch, setup_readiness_qadocs and setup_readiness_chair. |
| 2026-11-05 | Implemented one canonical preparation-only assessment and removed the blanket optional-service uncertainty refusal. Known precision checks, bounded probes and real build/stamp ownership remain. | setup_index.py diff; protected indexer/provider/accelerator/declaration bytes equal baseline bc9cfc8e. |
| 2026-11-05 | Focused canonical runner passes 280 tests / 3 files / 0 skips (setup 204, preflight 18, stamp owner 58). Direct inference controls 11 pass; strengthened all-content response → setup → real indexer control passes. Native/model leaves controlled; subprocess transport is simulated for the MCP case. | /private/tmp/wf-22l9k-focused-runner.log; wf-22l9k-inference.log; wf-22l9k-mcp.log. |
| 2026-11-05 | Three bounded in-memory mutants are rejected by their outcome assertions: omit no-work exemption, omit post-probe precision callback, or omit normal build. Each yields one assertion failure with zero errors; originals pass. | test_current_plan_skips_preparation_but_reaches_real_build; test_provider_probe_rejection_rechecks_precision_before_native_accel; /private/tmp/wf-22l9k-mutants.json. |
| 2026-11-05 | Direct shell setup tests initially used an incomplete interpreter/sandbox, producing dependency and permission failures. Unchanged tests pass through the canonical configured runner with host permissions; no dependency/version edits were made. Advisory integration review found no concrete defect; retained readiness context is not delivery approval. | setup_readiness_codearch effect check; canonical focused execution above. |
| 2026-11-05 | First full run exercised 12,328 tests; only the CLI documentation census failed because this wave copied maintained Markdown into disposable work under .md names. Verified all six copies against clean baseline bc9cfc8e and renamed them to .snapshot with bytes preserved. No product/source/test edit was needed. Fresh-empty canonical plan also returns up_to_date=false. | /private/tmp/wf-22l9k-canonical.log; refused run 553d00ae495a4a3aa6ed7c6907bd6582; owned baseline cleanup. |
| 2026-11-05 | Final frozen full suite passes 12,328 tests / 217 files / 12 intended skips in 568.366 seconds, with current green framework receipt. CLI census also passes all 54 controls after the scratch-name correction. All six reviewed source/doc blobs and protected-owner checksums remain exact. | /private/tmp/wf-22l9k-canonical-final.log; receipt inputs aa8ddc700c3ff56a07430b9a8545c2f1cd5f74b90e62dabecd1db95afaf6f38c. |
| 2026-11-05 | Fresh independent code, architecture, QA and docs-contract approve; targeted delivery council passes unanimously, intent_fit establishes, no findings. Reviewers independently replayed real entry and behavioral guard-mutant cases. All ACs/tasks complete; source gates closed. No affected-machine native qualification, closure or commit performed. | Typed delivery approvals and actual review roster in wave.md/events.jsonl. |
| 2026-11-05 | Preserved a new 51-byte ORT session-format artifact in owned ignored scratch after stable-identity/shape checks. It was absent from the initial tree and appeared during test activity; the exact producing invocation is not attributed. No native model execution is inferred from this import artifact. Memory proposal returned no eligible durable record. | venv_bootstrap.py telemetry note; .wavefoundry/work/22l9k/scratch/ort-session.snapshot. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Source changes between planning and execution | Continue normal indexer execution/validation; test source/selection change controls, never return setup success solely from a preliminary plan. |
| Optional-service absence hides a real precision change | Preserve known mismatch checks, bounded local probe decision and all-layer final protection; test publication/stamp retention. |
| Host-specific findings are overstated | Controlled CoreML availability is simulation; record no affected-machine native, Windows or Linux qualification. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
