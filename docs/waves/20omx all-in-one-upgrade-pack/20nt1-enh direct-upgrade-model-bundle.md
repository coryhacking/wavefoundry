# Directly upgradeable package with embedded models

Change ID: `20nt1-enh direct-upgrade-model-bundle`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-14
Wave: 20omx all-in-one-upgrade-pack

## Rationale

Operators need a single downloadable upgrade ZIP carrying the framework and its exact model set, alongside the existing lean package and standalone model asset. The operator explicitly chose a combined ZIP directly usable for upgrades, rather than a transport wrapper requiring two ZIPs to be unpacked first. Preserve existing model validation, compatible cache reuse and ordinary lean upgrades.

## Requirements

1. Add --with-embedded-models (implying --with-models) as an explicit build option to emit an additional directly upgradeable archive containing the same framework version/build and a byte-exact copy of the verified standalone model-set ZIP. Preserve existing bare build and --with-models behavior; do not replace the lean or standalone artifacts. The requested combined mode builds models from the warmed cache and does not download them.
2. Use wavefoundry-<semver>.<build>.with-models.zip as the combined filename and teach every framework-package discovery/selection entry point that accepts release assets about that variant. Derive the affected set from consumers of the package filename grammar and release-asset selection, including executable bridge and MCP/CLI paths. Standalone model archives never become upgrade candidates. Preserve existing semver/mtime/build ordering between distinct builds; collapse equal-version/build variants deterministically with lean preferred when both are present, independent of directory enumeration. An explicit pack path is honored.
3. Upgrade the combined archive directly, with no preliminary operator extraction. Keep embedded model bytes outside the installed framework source tree. Resolve the exact declared model set from the verified selected archive; reject malformed, mismatched, duplicate, linked, unsafe or oversized payloads before cache publication. Reuse existing component/hash/license validation and atomic cache publication rather than adding a parallel model installer.
4. Reuse an already verified matching model cache only after exact component-map/revision/hash comparison with the selected canonical manifest without materializing the embedded model ZIP or loading models merely to inspect it. When needed, stream the embedded bundle into an owned bounded staging location and feed canonical setup. Document an exact optional manual extraction path for offline recovery without requiring extraction for ordinary upgrade.
5. Preserve dry-run no-publication semantics, retained-run identity, resume availability and owned cleanup. A paused run must retain access to its verified embedded source after transient files disappear; cleanup removes only owned staging once recovery no longer needs it. Do not silently fall back to downloads after an invalid embedded bundle.
6. Combined output must preserve the executable protocol bridge and normal extraction contracts. Qualify the existing 1.31.0 runner boundary explicitly: if its discovery cannot recognize the new variant, document and test the executable/explicit entry route. Do not claim that changing incoming code changes an already-running older parent. Normal install instructions must identify the correct archive and avoid unpacking model bytes into project docs/source.
7. Release tooling publishes both package choices plus the standalone model asset when the new option is selected, with one version/build identity and clear asset descriptions. Preserve existing default releases, dry-run behavior, error recovery and independently versioned model sets. No modification of the already-published v1.31.0 assets is included.

## Concrete design

Embed one exact companion member under payload/models/ with bounded metadata naming model-set identity, size and SHA-256. Keep the model bytes only once in the final combined archive; the nested feature/bridge assembly must not duplicate them. Reuse the existing --model-bundle argument for combined sources where possible. The selected combined source is retained with existing verified-pack ownership until upgrade completion; model extraction is staged only when the exact canonical cache is unavailable. Existing 1.31.0 discovery is not claimed to understand the new filename: its supported combined entry is executing the archive, which must hand the retained combined source to the fresh runner. The existing executable currently refuses protocol-2 targets, so implement a distinct protocol-2 entry that verifies and retains the exact selected combined archive, stages the incoming runner outside installed framework source, and invokes that fresh runner with explicit root, pack and expected hash. Use existing quiescence/retained-checkpoint/ownership controls; release parent locks before the child acquires its transaction. On launch failure, recovery must re-enter a retained artifact, never reference deleted staging. Keep the protocol-1 bridge-install branch unchanged. Readiness reviews this new entry mechanism before implementation. Limits derive from the release-pinned model manifest and explicit archive budgets; reject invalid declared bundles instead of treating them as absent.

## Scope

In scope: optional combined build, naming/discovery, embedded model handoff, retention/cleanup, executable bridge compatibility, targeted tests and packaging/install/upgrade guidance. Out of scope: model changes, provider routing, dependency bundling, network download redesign, new model cache format, timing investigation, republishing v1.31.0 or automatic model loading.

## Acceptance Criteria

- [x] AC-1: A requested build produces the unchanged lean format and a distinct combined upgrade ZIP with identical framework content/version and the exact validated companion bytes; ordinary builds retain their existing outputs.
- [x] AC-2: Public upgrade selection handles lean-only, combined-only and coexisting equal-build variants deterministically; existing ordering between distinct builds is preserved and standalone model files are excluded. Explicit selection is preserved.
- [x] AC-3: The combined ZIP upgrades a scratch target without manually unpacking it, using embedded models when needed; a matching verified cache avoids embedded extraction. Invalid embedded inputs preserve the existing cache and return an actionable refusal.
- [x] AC-4: Dry run, interruption/resume and cleanup preserve verified artifact identity and availability without target publication in preview, unbounded reads or unowned deletion.
- [x] AC-5: Registered CLI/MCP and executable bridge paths have documented, tested compatibility boundaries, including an existing 1.31.0 runner; no unsupported old-parent transparency claim remains.
- [x] AC-6: Release dry run lists the intended assets and matching build identity; packaging, install and upgrade docs explain both choices and optional model extraction. The change's own tests and edited docs validate.

## Tasks

- [x] Finalize filename/flag, equal-build preference, embedded path and owned retention design through readiness review.
- [x] Implement additive archive composition and release asset handling with shared model verification.
- [x] Integrate selection and embedded-bundle handoff across derived public consumers and bridge routes.
- [x] Verify offline/matching-cache, invalid input, dry-run and interruption/resume boundaries with bounded fixtures.
- [x] Update canonical guidance and rendered local packaging surfaces; perform independent delivery review and normal qualification reuse.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Artifact and consumer contract | implementer | readiness | One owner for naming, bridge, setup handoff and tests avoids conflicting archive contracts. |
| Delivery verification | code/QA/security/architecture/release reviewers | implementation | Independent review of shared archive and publication boundaries. |

## Serialization Points

One implementer owns code edits. Reviewers are read-only; coordinator owns the wave record. Canonical seeds are edited before regenerated guidance. Existing review-policy carriers and provider implementation are protected from unrelated changes.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_bundle.py`
- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/model_bundle.py`
- `.wavefoundry/framework/scripts/embedded_model_bundle.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/setup_requirements.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/install/`
- `docs/prompts/package-wavefoundry.prompt.md`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/cross-cutting-concerns.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/testing-architecture.md`

Root README.md and CHANGELOG.md also receive operator-facing descriptions. Readiness must narrow any additional derived consumers before code edits; these directory targets are review floors, not permission for unrelated changes.

## Affected Architecture Docs

Update cross-cutting concerns for the embedded companion boundary, data/control flow for verified staging and resume, and testing architecture for dual-variant qualification. Update build-and-verification and package prompt; canonical upgrade/install guidance owns consumer instructions.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Requested packaging choice and backward compatibility. |
| AC-2 | required | Avoid wrong automatic upgrade selection. |
| AC-3 | required | Direct upgrade and existing model integrity boundary. |
| AC-4 | required | Safe preview and recoverable offline upgrade. |
| AC-5 | required | Existing runner and protocol compatibility cannot be assumed. |
| AC-6 | required | Discoverable release choices and verifiable public behavior. |

## Progress Log

- 2026-10-15: Operator clarified that the same combined ZIP must be directly installable as well as directly upgradeable. Verified the existing Requirement 6 / AC-5–6 normal-install contract: selective extraction of framework paths and install-wavefoundry.md into a fresh temporary target, with no payload or runner members installed, followed by the installed setup_index.main using --model-bundle on that same combined ZIP. Empty isolated caches published all three canonical components; a second call published zero and canonical-cache verification passed. No separate model archive extraction was required. Probe stopped after model provisioning, before dependency installation, indexing or agent onboarding; this is not a complete fresh-project onboarding claim. No shipped code or instructions changed, so the current full-suite receipt remains applicable.

- 2026-10-15: Final no-edit canonical qualification PASSED: 11,684 tests across 187 files, 12 skips, 726.438 seconds, exit 0; current green receipt and default qualification report written. Full documentation validation passed without warnings before this run; final record validation follows. No extra profile or packaging/release claim. Implementation, required ACs and six delivery reviews are complete; wave remains open pending operator closure.

- 2026-10-15: All 11,684 tests across 187 files passed (12 skips, 780.158 seconds), but runner qualification failed the concurrent-edit guard because the coordinator closed framework_edit_allowed and updated wave.md while the suite ran. No green receipt is claimed. All six independent delivery approvals are recorded; both gates and review records are now settled before the required no-edit rerun. This coordination failure did not alter reviewed source, invalidate reviewer fingerprints or require repeating readiness.
- 2026-10-15: Corrected installed protocol-2 integration fixture passed preview with no changed/added files. Real apply reached storage_restart_required with the same existing archive in embedded_source_proof, zip_path, index guard and action continuation; one retained ZIP only. The original release archive and operator cache were not changed.

- 2026-10-15: D1 repair independently reverified by code/architecture (one context), QA/docs/release (one context), and security (separate context). Final protocol file: 44 tests passed; focused repair set: 74 passed. Cleanup-disabled controls reproduce the orphan, while the repaired public path removes it; failures/replacements and adopted checkpoint ownership remain protected. New real-main regression records lean source ownership without treating it as a model bundle. The original tag-export integration fixture lacked packaging-generated UPGRADE-PROTOCOL.json and therefore proved protocol-1 bridge compatibility, not an installed protocol-2 target; a follow-up uses the marker from the official 1.31.0+pwp1 archive.

- 2026-10-15: Independent delivery reviewers reproduced one shared AC-4 cleanup finding: the executable wrapper retains its owned archive after a successful child leaves no checkpoint; lean protocol-2 lacks the combined proof handoff too. Recorded D1-owned-archive-cleanup for focused repair and independent code/architecture/QA/security reverification. The in-progress qualification was stopped before source repair; it is not green evidence.
- 2026-10-15: Completed canonical qualification ran 11,681 tests across 187 files with three failures: new-helper declaration census, lifecycle-lock opener census, and the setup fixture still mocking materialize_bundle instead of materialize_source. Corrected the two inventories and fixture under the admitted targets; all three focused controls passed. No product behavior was weakened to satisfy them.

- 2026-10-15: Implementer focused checks passed: build/package 121, model bundle 29, protocol/envelope 41, hygiene/distribution 60, fresh historical bootstrap 22 and final cleanup checks 2. Guard-removal controls failed by assertion with zero errors/skips: canonical-cache-map guard → test_combined_exact_companion_and_cold_then_current_cache; embedded SHA guard → test_combined_hash_corruption_preserves_empty_cache; actual stream-byte cap → test_embedded_envelope_rejects_unsafe_duplicate_and_actual_overflow; preserve-existing-proof guard → test_combined_envelope_retention_refuses_links_and_preserves_replacements. Final code and tests frozen before canonical qualification. An early qualification attempt was stopped when a final cleanup test landed after launch; it is not qualification evidence. No result from the implementer's concurrently edited broad upgrade-test attempt is reused.
- 2026-10-15: Integration apply exposed a retained-source mismatch: the restart continuation referenced the wrapper's archive after the child retained its own copy and the wrapper removed the first. The implementation now propagates the child-owned path into selected-pack identity; a rebuilt actual-tagged fixture confirmed checkpoint, guard and action paths agree and exist. After original download ZIP deletion, the exact continuation progressed to rendering/docs validation. Resume also prompted a same-owned-source reuse correction to avoid repeated large copies. Final tests must pin both controls before delivery approval.
- 2026-10-15: Real model-set-3 companion exercised in isolated fastembed/ONNX cache roots: first combined-source materialization published all three canonical components; the second published zero with an extraction trap, and canonical-cache comparison passed. No model inference, downloads or changes to the operator's model cache occurred.
- 2026-10-15: Coordinator integration preview used a scratch tree exported from the actual v1.31.0 tag and a producer-built incoming combined ZIP carrying the real model-set-3 companion. Executing the ZIP with --dry-run from outside the target exited 0, reached incoming migration preview/docs-gate PASSED, and identified 1.31.0+pwp1 to 1.32.0+aaaa. Complete target file-hash inventories were identical with no added files. This proves preview compatibility only, not apply/resume or live model inference; scratch script/report remain under /private/tmp/20omx-tagged-* pending final boundary verification. Full docs validation passed without warnings.
- 2026-10-14: Shared transport helper added as an explicit review target; focused architecture/code, QA/docs/release, security and chair delta reviews approved the stdlib-only factoring under the current receipt. An initial helper draft arrived before the pause reached the implementer; further edits stopped until re-Prepare passed. This is a recorded sequencing correction, not a retrospective claim that the draft was already qualified. Coordinator owns prose/seed updates, implementer owns code/tests. Canonical seed-160 combined-package guidance was copied into its local prompt counterpart; no managed policy block was hand-edited. Gapfill: bulk documentation updates use exact text edits after live MCP reads.
- 2026-10-14 Readback: Implement AC-1–6 as an optional directly upgradeable combined ZIP alongside the existing lean and standalone assets. Before, offline operators must supply a separate model ZIP; after, the selected combined archive supplies the exact companion only when the canonical cache needs it. Preserve existing model identities, legacy bridge behavior and cross-build ordering. Work is confined to the named packaging, upgrade, model, setup, test and documentation surfaces; no release publication, provider changes or timing investigation.
- 2026-10-14: Operator selected a combined ZIP directly usable for upgrades. MCP discovery located build_upgrade_bundle and release extra_assets; live reads confirmed _matching_model_bundle searches only separate files and _find_latest_release_zip filters filenames before version/mtime ranking. Indexed retrieval reported stale data; implementation anchors were verified through live code_read. Planning only; no implementation or readiness approval claimed.

## Decision Log

The concrete option/name and equal-build lean preference preserve existing default behavior. Keep legacy ordering across different builds rather than bundling a broad selection-policy rewrite into this feature. Add an exact canonical-cache check because marker self-attestation alone cannot prove the release-pinned set matches.

| Decision | Reason | Alternatives |
| --- | --- | --- |
| Additional directly upgradeable archive with embedded verified companion | Operator explicitly chose direct upgrade; reuse the current model ZIP and validation path. | Transport wrapper containing two ZIPs is simpler but requires preliminary extraction and was not selected. |
| Preserve lean package and standalone companion | Existing operators and recovery workflows retain their options. | Replacing the lean artifact imposes model download size on every upgrade. |
| Reuse verified companion bytes rather than flattening model files into framework | Keeps model identity/license checks and avoids permanent model payload in installed source. | Flattened files blur installed-source and model-cache ownership and duplicate extraction/validation behavior. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Older runner ignores variant filename or embedded payload | Verify actual old-parent routes and provide an executable entry path before claiming compatibility. |
| Duplicate variant changes automatic selection | One grammar and deterministic ranking, tested across relevant consumers. |
| Large nested payload increases memory/disk or breaks resume | Stream with bounds, reuse valid cache, retain verified owned source until completion. |
| Archive tampering or cache replacement | Existing pinned manifest, hash and atomic publication checks remain mandatory. |

## Session Handoff

Implementation and required delivery reviews are complete, with final canonical qualification green. Wave remains open; closure, commit, push and release have not been performed. See docs/agents/session-handoff.md for session context.
