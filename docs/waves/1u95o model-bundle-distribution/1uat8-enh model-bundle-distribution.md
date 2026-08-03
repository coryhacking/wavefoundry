# Direct-Distribution Model Bundle

Change ID: `1uat8-enh model-bundle-distribution`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-03
Wave: `1u95o model-bundle-distribution`

## Rationale

Wavefoundry's normal framework ZIP deliberately ships source only and obtains
embedding and reranking artifacts from their upstream model sources on first
use. That is an unnecessary deployment dependency for air-gapped and tightly
controlled enterprise environments. Operators need a second, directly
distributable model companion that can populate the required model caches only
when the validated artifacts are absent, while retaining the small standard
framework package for every other installation.

The current validated model set is directly redistributable under Apache-2.0
or MIT terms. "Latest" must mean the latest *supported, redistributable,
compatible candidate at a recorded evaluation date*, not an unpinned download
at package-build or target-install time. Newer general-purpose model families
that require a different runtime, embedding dimension, or index migration are
not silently substituted into this packaging change.

## Requirements

1. Keep the existing standard `wavefoundry-<version>.<build>.zip` source-only
   package and its upgrade-selection behavior unchanged.
2. Produce a separately named, directly distributable model-set asset that is
   not eligible as a framework-upgrade ZIP. Its own version, compatibility
   fingerprint, allowlist, and provenance are the binding contract; it must not
   be republished merely because a framework build changed.
3. Package only a declared, pinned model set: the FastEmbed embedding assets
   and the clean ONNX reranker assets required by the released runtime. Include
   provenance, upstream revision, file/tree hashes, license texts, attribution,
   and an explicit redistribution decision for every component.
4. Give the declared model set an explicit version and compatibility identity.
   When a matching companion contains a newer compatible declared set,
   setup/install/upgrade must validate and atomically replace an older verified
   local set; an equal or newer compatible local set must be left unchanged.
   The path must work without network access.
5. During an upgrade from the standard feature package, compare the installed
   verified model-set identity with the model policy pinned in that package. If
   the package declares a newer compatible set, use the normal upstream
   download/materialization path when network access is available; when it is
   not, preserve the working local set and report the matching model companion
   as the deterministic recovery path. Do not query an unpinned upstream
   "latest" model during target upgrade.
6. Bind the embedding portions of the declared model set to semantic-index
   provenance. Any changed embedding identity, revision, bytes, dimension, or
   prefix behavior must invalidate and fully rebuild only its affected semantic
   layer before that layer is reported current; a reranker-only update must be
   versioned and surfaced as a retrieval-behavior change without claiming an
   embedding rebuild occurred.
7. Reject unsafe archives, manifest/version/hash mismatches, undeclared files,
   unsafe paths or links, and incomplete materializations without leaving a
   partially published model cache.
8. Preserve the normal upstream-download fallback when no valid companion is
   supplied, including the current cache-location and host-acceleration
   behavior.
9. Before selecting the pinned set, evaluate the current FastEmbed-supported,
   commercially redistributable embedding and reranking candidates against the
   existing models for retrieval quality, reranking quality, runtime support,
   package footprint, and reindex impact. Record the date, tool/runtime
   version, candidates, licenses, evidence, and decision. Treat an actual
   model/runtime/index migration as a separately admitted follow-up change.
10. Release tooling must publish the normal framework ZIP on every framework
   release and the model-set asset only when the model set changes, with
   documentation that distinguishes their installation and offline-use paths.

## Scope

**Problem statement:** Enterprise users cannot reliably allow model downloads
from production hosts, while shipping a single large framework ZIP would make
ordinary updates heavier and could make the current feature-pack selector
ambiguous.

**In scope:**

- An independently versioned standard-pack/model-set artifact design and manifest schema.
- Deterministic artifact construction from a narrow allowlist of pinned files,
  including notices and provenance.
- Safe, idempotent offline model materialization into the runtime's expected
  FastEmbed and clean-ONNX source caches.
- Version comparison and controlled replacement for an older declared model
  set, whether its source is the companion or the standard package's normal
  upstream-download path.
- Package, install, setup, upgrade, release, documentation, and fixture-based
  verification changes needed to deliver the two assets.
- A documented, reproducible current-model selection evaluation.

**Out of scope:**

- Replacing the current embedding or reranking model merely because a newer
  upstream model exists.
- Bundling compiled CoreML/static-shape artifacts, arbitrary user caches,
  symlinked cache internals, executable model code, or undeclared downloads.
- Changing semantic index structure or silently rebuilding every target index;
  the narrowly required metadata extension for declared model-set compatibility
  and affected-layer invalidation remains in scope.
- Publishing the deferred official 1.15.0 release before this wave is reviewed
  and implemented.

## Acceptance Criteria

- [x] AC-1: A standard feature ZIP and a separately named paired model
  companion can be built reproducibly; only the standard ZIP is eligible for
  automatic framework-upgrade discovery.
- [x] AC-2: Every bundled component has a machine-readable pinned provenance
  record, tree/file hashes, upstream revision, included license text and
  attribution, and an approved direct-redistribution decision.
- [x] AC-3: A no-network fixture installation with the matching companion
  materializes the required embedding and reranker sources exactly once and
  reports their verified readiness.
- [x] AC-4: Re-running setup/install/upgrade with a verified model set makes
  no cache changes, while a newer compatible declared set upgrades an older
  one exactly once; a failed validation or extraction leaves no partial
  published set.
- [x] AC-5: A standard-package upgrade detects a newer pinned compatible model
  set, retains the verified working set, and reports the exact matching
  companion action. It does not replace a verified cache from an unpinned
  upstream download, whether or not network access is available.
- [x] AC-6: Tests reject traversal, links, undeclared content, package/model
  version mismatch, hash mismatch, and incompatible companion artifacts.
- [x] AC-7: An embedding-set update invalidates and fully re-embeds exactly the
  affected semantic layer before it reports current; reranker-only updates are
  visible in retrieval provenance without falsely rebuilding semantic vectors.
- [x] AC-8: The current upstream-download path still succeeds when the
  companion is absent, and host-specific compiled caches are neither packaged
  nor overwritten.
- [x] AC-9: The model-selection record evaluates the latest supported,
  commercially redistributable candidates at its stated date and explicitly
  retains the current models or opens a separately admitted migration change.
- [x] AC-10: Release tooling and operator documentation publish and explain both
  assets, their offline installation behavior, cache verification, and failure
  recovery.
- [x] AC-11: Model assets are named and selected by independent model-set
  version. A framework-only release does not rebuild or publish model bytes;
  a release that changes the declared set publishes the corresponding asset and
  upgrade finds that exact asset across its standard distribution directories.

## Tasks

- [x] Define the companion name, manifest contract, binding/version rules,
  cache-target layout, and model allowlist/provenance format.
- [x] Define compatible model-set version ordering, standard-package upgrade
  detection, offline recovery reporting, and the atomic replacement contract.
- [x] Add model-set provenance to index compatibility checks and tests so an
  embedding artifact update cannot leave mixed-generation vectors in a current
  index.
- [x] Capture reproducible candidate and license evidence; run the selection
  evaluation and record its disposition before artifact generation.
- [x] Extend pack construction and release publication to build and attach the
  companion without weakening the existing standard-pack invariant.
- [x] Implement safe, atomic model-bundle validation and idempotent
  materialization in the install/setup/upgrade paths.
- [x] Add focused fixture tests for construction, legal/provenance gates,
  offline installation, idempotence, and all rejection/rollback paths.
- [x] Update package, installation, upgrade, reliability, and release
  documentation; run required framework and documentation validation.
- [x] Decouple model-asset naming, manifest validation, release publication,
  and upgrade selection from framework build identity; add focused coverage for
  standard distribution-directory discovery.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Artifact contract and provenance | framework-engineer | — | Lock design before package or installer edits. |
| Model selection evaluation | retrieval-evaluator | artifact contract | May retain current models; migration is out of scope. |
| Pack and release tooling | framework-engineer | artifact contract | Standard package remains sole automatic upgrade input. |
| Offline materializer | framework-engineer | artifact contract | Must be atomic and cache-layout aware. |
| Fixtures and verification | test-engineer | pack and materializer | Synthetic fixtures only; no large models in repository tests. |
| Documentation | docs-contract-reviewer | implementation evidence | Describe both assets and recovery. |

## Serialization Points

- Approve the artifact/manifest contract and model-selection disposition before
  modifying shared packaging, setup, upgrade, or release code.
- Build both assets only after all implementation and review repairs are
  complete; do not publish a stale pre-review package.
- Any proposed model or index-runtime migration must stop this change and enter
  a separate plan/wave admission path.

## Affected Architecture Docs

- `docs/ARCHITECTURE.md` — package and offline deployment boundary.
- `docs/architecture/current-state.md` — model acquisition/materialization
  behavior and cache ownership.
- `docs/architecture/cross-cutting-concerns.md` — supply-chain provenance,
  archive safety, and third-party notices.
- `docs/architecture/testing-architecture.md` — offline fixture and rollback
  verification.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserves unambiguous upgrade behavior. |
| AC-2 | required | Direct redistribution needs auditable provenance. |
| AC-3 | required | Offline materialization is the primary outcome. |
| AC-4 | required | Prevents cache corruption and wasted extraction. |
| AC-5 | required | Standard upgrades must surface and apply pinned model updates. |
| AC-6 | required | Archive intake is a trust boundary. |
| AC-7 | required | Prevents mixed-generation semantic vectors. |
| AC-8 | required | Retains the current lightweight path. |
| AC-9 | required | Meets the pinned latest-compatible evaluation requirement. |
| AC-10 | important | Operators need a usable release path. |
| AC-11 | required | Prevents needless large-asset publication and makes model updates independently deployable. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-03 | Planned paired model companion after direct-distribution and compatibility preflight. | Current model licenses are Apache-2.0/MIT; current FastEmbed support excludes a drop-in BGE-M3 migration. |
| 2026-08-03 | Added versioned model-set upgrade behavior for companion and standard-package upgrades. | Standard upgrades compare a release-pinned policy rather than making an unpinned upstream latest-model query. |
| 2026-08-03 | Added semantic-index provenance and targeted re-embedding requirement for model-set updates. | Existing index metadata compares embedding model names, not model artifact revisions; a same-name replacement otherwise risks mixed-generation vectors. |
| 2026-08-03 | Implemented the paired model-bundle builder/materializer, standard setup/upgrade handoff, release asset support, model fingerprinting, and synthetic fixture coverage. | `model_bundle.py`; `test_model_bundle.py`; focused tests pass. Gapfill: MCP retrieval was unavailable in this host, so targeted native reads were used for the package, setup, upgrade, accelerator, and index-state seams. |
| 2026-08-03 | Delivery review repaired cache-marker verification, model-set no-downgrade behavior, feature-SHA binding, release-asset census, and the durable upgrade-pause handoff. | `test_model_bundle.py`; targeted `test_build_pack.py`, `test_indexer.py`, and `test_upgrade_wavefoundry.py` cases pass; docs-lint passes. The aggregate runner became idle after worker completion and was stopped without a final verdict, so delivery approvals remain pending. |
| 2026-08-03 | Delivery review repaired the remaining partial-publication risk: model materialization now stages the complete set and rolls back already-published components if any later rename fails. | `test_failed_publish_restores_existing_cache` injects a failure after the first cache directory publishes; all original markers are restored. |
| 2026-08-03 | Final review made pre-marker caches visible during standard-package upgrades instead of silently treating them as current. | `test_standard_package_surfaces_unmanaged_model_cache`; full framework suite passes (6,787 tests). |
| 2026-08-03 | Operator selected the safe AC-5 policy: standard packages detect model-set drift but only the matching hash-bound companion can replace a verified cache. | Avoids turning a normal upgrade into an unpinned upstream model replacement. |
| 2026-08-03 | Implementation completed; all ACs and tasks are evidence-backed. | Full framework suite: 6,787 tests across 62 files; docs-lint and paired-artifact build pass. |
| 2026-08-03 | Reconciled the model-selection upgrade rule with the operator-selected safe policy. | Standard upgrades detect drift and retain the verified cache; only the matching companion can replace it. |
| 2026-08-03 | Decoupled the model-set asset from framework build identity. | `wavefoundry-models-<model-set>.zip` is built only with `--with-models`; target packs declare the exact set and setup discovers it across standard distribution directories, including the first upgrade from an older runner. Full framework suite passes: 6,790 tests across 62 files. |
| 2026-08-03 | Built the real local 1.15.0 artifacts after compatibility verification. | `~/.wavefoundry/dist/wavefoundry-1.15.0.pgmf.zip` and `~/.wavefoundry/dist/wavefoundry-models-1.zip`; both declare model set `1` and fingerprint `wf-model-set-1-20260803`. Legacy feature-bound model assets no longer block the independent-set build. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-03 | Use a paired, non-selectable model companion rather than two interchangeable framework packs. | Preserves the one canonical framework-upgrade input and keeps ordinary updates small. | One fat feature ZIP; two independently selectable feature ZIPs. |
| 2026-08-03 | Pin model artifacts and evaluate latest compatible candidates; do not dynamically download or silently upgrade models. | Reproducibility, license auditability, cache/index compatibility, and predictable enterprise deployment. | Latest-at-build download; BGE-M3 runtime migration in this scope. |
| 2026-08-03 | Allow controlled upgrades to a newer compatible *pinned* model set. | Delivers model updates without a live, nondeterministic latest-model lookup or unsafe cache replacement. | Never upgrade local models; query upstream latest on every target upgrade. |
| 2026-08-03 | Version model assets independently from framework releases. | Avoids republishing large model bytes for framework-only changes while preserving exact target-policy selection and validation. | Keep the model asset hash-bound to every framework build. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Bundled cache layout differs across FastEmbed or acceleration paths. | Package a canonical declared source tree, materialize it through a tested adapter, and exclude compiled caches. |
| A model license or revision cannot be verified for redistribution. | Fail the provenance gate and omit that component; retain ordinary upstream-download behavior. |
| Large assets create accidental release/upgrade ambiguity. | Keep the model companion outside the normal pack matcher and bind it through an explicit manifest. |
| A standard-only upgrade cannot reach its model provider. | Retain the verified working set, report that the released model policy is newer, and name the matching companion as offline recovery. |
| An updated embedding artifact is stored under the same public model name. | Persist and compare a declared embedding compatibility fingerprint, then fully rebuild only the affected layer before publication. |
| Candidate evaluation identifies a model requiring index/runtime migration. | Record the finding and open a separate change instead of expanding this packaging wave. |

## Session Handoff

The official 1.15.0 release remains intentionally deferred. This change is
planning-only until it is admitted, prepared, reviewed, and explicitly opened
for implementation.
