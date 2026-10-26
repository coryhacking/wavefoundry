# Diagnose setup provider access before incompatible local warmup

Change ID: `21kbc-enh setup-provider-preflight-before-local-warmup`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-25
Wave: 21kbd setup-provider-preflight

## Rationale

On 2026-10-25, the operator authorized normal setup after an MCP restart. The restricted invocation of `./.wavefoundry/bin/wf setup --root /Users/coryhacking/Developer/wavefoundry` prepared local models, failed its CoreML probe, warmed a CPU INT8 embedder, and only then refused an implicit full-to-INT8 conversion for both existing index layers. Exit 2; the published index was preserved. The same command with host access selected the qualified service, skipped local embedding provider preparation, found the index current, and completed successfully with zero accepted embedding inputs. The subsequent MCP assessment reported setup ready and current code.

These are executed observations from this session, not a proposed reproduction. Host restrictions are the leading explanation for failed service selection, but the first invocation did not report its exact Tensorwell selection reason; a particular permission or transport error is unverified. Successful selection with no changed inputs does not prove new service inference executed.

Current-source inspection: `setup_index._resident_setup_embedder` requests an adapter without retaining its diagnostic; `prewarm_models` proceeds locally on no adapter; `setup_index.main` prepares models and probes providers before invoking the index build. `indexer._implicit_precision_changes` and `_implicit_precision_refusal` already reject recognized precision changes. `_predicted_precision_class` is an availability-based prediction, not a successful native execution probe. Moving a comparison earlier must not misrepresent that distinction.

## Product Intent

Operators refreshing an existing index get an actionable explanation when the setup process cannot use the intended Tensorwell provider, without paying for an incompatible local model warmup or risking the published index. A qualified reachable service avoids local preparation; supported local setups and explicitly requested rebuilds remain available. AC-1 and AC-2 together test this outcome, while AC-3 through AC-5 protect legitimate alternatives and truthful diagnosis.

## Requirements

1. Retain and surface the actual provider-selection result for each required setup workload when it determines local preparation or refusal. Distinguish unsupported model, policy/precision exclusion, unavailable or incompatible service, and unknown failure using the existing selector's vocabulary. Do not infer that Tensorwell is stopped merely because this process cannot select it. Do not expose credentials, authorization headers or raw private discovery data.
2. When qualified service selection covers the requested workloads at the required precision, skip their local weight warmup, ONNX/CoreML compilation and INT8 preparation. Preserve per-workload behavior for mixed coverage and explicit provider controls; service selection is not evidence of executed inference.
3. Before local model warmup or compilation, compare the proposed fallback with recognized persisted index precision for the requested update, using the existing compatibility rules. An ordinary update that would require an implicit precision conversion must stop before that preparation, retain the published index, and report recorded/requested precision plus the relevant selection reason. Keep the indexer's later check authoritative so selection changes or direct indexer callers cannot bypass protection.
4. Limit conservative uncertainty refusal to implicit local fallback in the default Tensorwell mode: for an existing explicitly recorded full-precision index, when no qualified service was selected and full precision depends solely on an available provider that requires a native model probe while its CPU fallback is INT8, stop before that model preparation. Report recorded full and unverified fallback compatibility (possible full/INT8), not a measured GPU failure. Explicit local/extension policy, fresh setup, unrecognized legacy provenance and an explicit full rebuild retain their existing paths and later guards; selecting local is an explicit preparation choice, not proof of native success. Use existing provider probe requirements and precision owners, without a new provider mode, persisted decision authority or model registry.
5. Preserve supported fresh setup, existing compatible local indexes, explicitly selected local/extension policy, per-model mixed coverage and the existing explicit full-rebuild route. A full rebuild may intentionally change precision under existing rules; ordinary setup must not silently upgrade itself to a rebuild. Missing or legacy provenance retains its existing recovery semantics and must not be guessed to mean full precision.
6. Recommend recovery appropriate to the observed reason: restore service visibility/compatibility or explicit compatible provider configuration first; describe deliberate rebuild only as a separate operator choice. Never automatically elevate permissions, start/reconfigure Tensorwell, disable the service, convert the index, or retry the whole setup indefinitely. Explain process-local reachability and the early-refusal behavior in maintained setup/provider documentation.


## Readiness design

One read-only assessment before semantic model preparation uses the existing selector diagnostic, provider mode/probe requirements and recognized stored precision. It considers the workloads the invocation will prepare, including requested background semantic layers; it does not silently narrow the final indexer guard, which currently checks both persisted layers. A recognized known mismatch refuses early; the bounded implicit-fallback uncertainty rule in Requirement 4 also refuses before native preparation. Missing/bare/unknown provenance remains unknown, never defaulted to full. Dependency-only, graph-only and migration prewarm-only behavior remains outside this existing-index update check.

Selection diagnostics belong to the exact decision they describe. If selection is repeated later, a different result must be assessed and reported before it authorizes local work; do not use a previous qualified-service result to bypass preparation checks after the service disappears. Keep a decision local to the operation, not a new persisted cache. Retain the later authoritative indexer check for provider changes and direct callers. Diagnostics must be bounded symbolic reasons; unknown exception text is not a safe public diagnostic.

## Scope

In scope: setup provider-selection diagnostics; early existing-index compatibility assessment before local preparation; reuse of the indexer's precision rules; focused setup/provider/compatibility tests and operator documentation.

Out of scope: a global ban on local inference; new required-service configuration; Tensorwell installation or transport redesign; automatic host escalation; changes to precision definitions, model pins or rebuild authority; query/reranker recovery outside setup; changes to closed wave 21k15; release or packaging.

## Acceptance Criteria

- [x] AC-1: Through the public setup path, a controlled reproduction of unavailable service selection plus an existing full-precision index and incompatible INT8 fallback refuses before local model warmup/compilation. A call-order or sentinel oracle proves the avoided work; output names the selection reason and compatibility problem, and published index content remains unchanged. A late-only refusal cannot satisfy this criterion.
- [x] AC-2: The otherwise-equivalent qualified-service control succeeds without local preparation for covered workloads; mixed coverage prepares only eligible uncovered workloads. Selection-only/no-work results do not claim executed service inference.
- [x] AC-3: Adjacent controls preserve fresh local setup, an existing compatible local index and deliberately requested rebuild behavior. Legacy/unknown provenance and explicit provider controls follow their stated policy without invented compatibility or automatic conversion.
- [x] AC-4: Distinct controlled selection failures retain distinct bounded diagnostics and useful next actions. An unverified cause is labeled unknown rather than reported as service shutdown or a proven sandbox fault; output contains no credentials or raw sensitive discovery payload.
- [x] AC-5: A provider change after early assessment and a direct indexer invocation still encounter the existing compatibility guard before incompatible publication. The change's maintained tests and documentation agree on prediction versus execution, refusal timing and operator-controlled recovery.

## Tasks

- [x] During readiness, reproduce the public-path call order in disposable fixtures; settle early assessment without native model preparation, including unknown provenance and mixed coverage.
- [x] Retain provider-selection diagnostics and add the early compatibility decision using existing setup/indexer owners; preserve the later publication guard.
- [x] Add focused public-path paired controls and independently verify each AC, including actual unwanted-preparation sentinels and unsafe guard variants.
- [x] Update provider/setup guidance, complete required delivery review and run canonical qualification once after sources settle.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| setup-provider-preflight | implementer | readiness | One writer for coupled setup/indexer/provider seams |
| independent-verification | qa-reviewer | implementation | Verify avoided preparation and preserved adjacent behavior |
| documentation | coordinator | settled behavior | Explain observed reasons and recovery without universal availability claims |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/inference_provider.py`, `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/embedding-model.md`, `docs/contributing/build-and-verification.md`

The provider facade/client are review targets; change them only if existing diagnostic support is insufficient. No seeds, generated host configurations or model/dependency manifests are intended write targets. Prepare derives required lanes; request architecture and security in addition to code, QA and docs-contract because provider selection, index preservation and diagnostic privacy cross boundaries.

## Affected Architecture Docs

`docs/architecture/embedding-model.md`: setup selection, precision assessment and fallback timing. `docs/contributing/build-and-verification.md`: actionable setup refusal and host-access troubleshooting. Keep implementation details out of user recovery messages unless they determine the next action.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevent the motivating wasted preparation while preserving index data |
| AC-2 | required | Use available service and avoid unnecessary local execution |
| AC-3 | required | Preserve legitimate local and explicit rebuild workflows |
| AC-4 | required | Make recovery actionable without inventing the cause or leaking data |
| AC-5 | required | Early diagnosis cannot weaken final compatibility enforcement |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-25 | Independent code/QA verified the repair and detected the original fault with old-behavior mutants; all five delivery lanes approve and QA confirms the controlled intent outcome. One final canonical run passed 12,228 tests across 213 files, 12 existing skips, in 739.352s. All six reviewed file hashes unchanged. All ACs/tasks complete; framework gate closed. No repeat qualification for recordkeeping. | Terminal QA-21KBD-001 cycle 1; typed delivery approvals; test receipt inputs_hash 10811c0fb166aac47670bf1f18ce7571c1f15595cdb91081fe80f2f1979128cd; canonical-final.log in owned wave work |
| 2026-10-25 | After recorded repair_start cycle 1, replaced both whole-module-cache fixture patches with restoration of owned keys only. Fresh discovery now runs all eight controls successfully without NumPy preload. Old cleanup loses a lazy import; repaired cleanup preserves it and restores owned bindings. Production and both guidance files unchanged; frozen again for independent code/QA reverification and docs-contract review. | QA-21KBD-001; new test SHA-256 cb025d86d88bb1153ce38329288bb26f1d60bc9d97e638931a6a03cba49e4968; fresh eight-test run 4.391s |
| 2026-10-25 | Independent delivery found QA-21KBD-001 before repair: whole-module-cache restoration removes lazily imported NumPy, leaving one pass and seven setup errors in a fresh worker. The earlier ordered green run masked this fixture defect. Code and QA withhold delivery approval; production remains frozen. Repair only the five owned module bindings, preserving unrelated imports; no NumPy preload workaround. | Typed finding QA-21KBD-001; independent code/QA reproductions and implementer fresh-worker reproduction |
| 2026-10-25 | Implementation frozen for delivery: setup selection diagnostics and repeated early checks share recognized precision reader with unchanged late guard; no facade/client edits. Eight new public-path controls pass, plus 23 adjacent setup/scheduling and two extension controls; existing 14 precision controls passed. Final ordered extension/new-fixture run 10/10 in 5.305s. Two guard-removal variants expose actual unwanted preparation. Combined-run module identity issue corrected in the test fixture only. Canonical qualification and independent delivery pending. | SetupProviderPreflightTests; SetupIndexTests and SetupLayerSchedulingTests; ExplicitPrecisionRebuildTests; ProviderTests; delivery source hashes |
| 2026-10-25 | Readback before first code edit: current restricted/service-unselected update prepares local models then refuses full-to-INT8. Deliver setup refusal before that preparation with exact bounded selection reason, plus qualified-service/no-local-work control; preserve explicit local, extension, fresh, legacy and deliberate rebuild behavior and the later all-layer guard. AC-1–5. One writer owns setup/indexer and focused tests; coordinator owns two docs. Readiness passed on review-policy-3c52e00c270245cdc240. | Five independent specialist approvals and council-readiness; current public-main ordering and precision/selector controls |
| 2026-10-25 | Planned from two actual setup invocations: restricted process exit 2 after INT8 preparation and precision refusal; host-access retry exit 0 using qualified service with zero accepted embedding inputs. Later setup assessment ready. Exact first-run service rejection remains unverified. No implementation edits or new setup/test rerun for planning. | Session setup outputs at 22:23:59 and 22:24:24–27 UTC; source owners named in Rationale |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-25 | Bound uncertainty refusal to implicit Tensorwell fallback with recognized full provenance and a probe-dependent GPU whose CPU route is INT8 | Availability alone cannot prove native success. Explicit local/extension policy remains an operator-selected preparation path with the existing late guard; fresh, legacy and full-rebuild routes are preserved. | Refusing every unproven local GPU would regress explicit local workflows. Trusting availability alone misses the motivating CoreML-to-INT8 failure. |
| 2026-10-25 | Select bounded early compatibility assessment plus selection diagnostics | Replaying the incident should stop before incompatible local preparation and explain why service selection failed. This controls wasted preparation; diagnostics advise the operator, who chooses recovery. Existing precision rules and selector diagnostics supply the starting point. Effectiveness remains prospective until paired AC-1/AC-2 execution. | Diagnostics only leaves late refusal and wasted work. Globally prohibit local fallback changes fresh/local behavior and adds policy beyond the incident. |
| 2026-10-25 | Keep final compatibility enforcement and avoid new provider authority | Early availability can become stale or remain uncertain; a later guard protects publication. Unknown/legacy metadata must not be mislabeled. The early assessment can conservatively refuse a recoverable environment; mitigate with explicit uncertainty and a concrete retry/configuration remedy, not silent conversion. | Trust the early result as publication authority risks a changed provider. Duplicate precision definitions risks drift. |
| 2026-10-25 | Measure avoided model preparation and diagnostic usefulness, not an assumed timing gain | Tests prove zero incompatible preparation and matched compatible behavior. On the next real affected setup, record the reported cause, whether its recommended recovery worked and whether local preparation was avoided; no additional telemetry subsystem. | A successful setup alone does not prove absence of unnecessary work; invented saved-time estimates do not establish operator benefit. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Availability prediction says full but native preparation later fails | Readiness settles uncertainty before preparation; retain later indexer guard and avoid claims of measured compatibility |
| Service availability differs between MCP and a child process | Report the actual setup-process selection reason; do not substitute cached MCP availability |
| Overbroad early refusal breaks fresh/local or legacy setup | Matched adjacent controls and existing policy/provenance semantics |
| Repeated selection creates contradictory diagnostics | Bind reported reason to the decision being described; report a subsequent selection change explicitly |

## Session Handoff

Planning only. Admitted to 21kbd; not readied or implemented. Next is Prepare wave and independent review of the bounded early-assessment seam. Preserve all earlier uncommitted work; 21k15 remains closed.
