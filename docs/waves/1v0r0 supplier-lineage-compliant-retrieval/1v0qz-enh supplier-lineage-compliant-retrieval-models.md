# Supplier-Lineage-Compliant Retrieval Model Swap

Change ID: `1v0qz-enh supplier-lineage-compliant-retrieval-models`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-11
Wave: `1v0r0 supplier-lineage-compliant-retrieval`

## Rationale

Supplier origin is now a product requirement. Wavefoundry's active code
embedder, `BAAI/bge-small-en-v1.5`, does not satisfy it. The direct correction
is to replace that model with `Snowflake/snowflake-arctic-embed-s` while
leaving the already accepted document embedder and reranker in place.

A 28-query comparison over 6,895 current code chunks found a small, consistent
quality advantage for Arctic S over Arctic XS before and after the production
L6 reranker. Arctic S is slower to index, but its measured FP16 GPU time stayed
well inside the accepted 2.0x relative ceiling. The swap advances the packaged
offline model set from v1 to v2 for Wavefoundry `1.16.0`; supplier
origin remains a manual, evidence-backed decision whenever that model set is
changed.

## Requirements

1. The production model set SHALL be:
   `Snowflake/snowflake-arctic-embed-xs` for documents,
   `Snowflake/snowflake-arctic-embed-s` for code, and the existing
   `cross-encoder/ms-marco-MiniLM-L-6-v2` logical reranker resolved through its
   existing pinned `Xenova/ms-marco-MiniLM-L-6-v2` artifact export. Embedding
   dimensions SHALL remain 384.
2. The generated model-set verification manifest SHALL retain its operational
   artifact schema and identify the exact repositories, revisions, hashes,
   licenses, and attributions for the v2 bundle. The model-selection decision
   record SHALL separately identify the supplier and artifact publisher, manual
   supplier-origin decision, verification date, reviewer, and evidence URLs.
   Supplier-origin eligibility SHALL be reviewed manually whenever a model is
   swapped; this wave SHALL NOT add runtime jurisdiction validation or mix
   hand-authored decision fields into the generated bundle identity.
3. Arctic S SHALL use Snowflake's query-only retrieval instruction and no
   stored-chunk prefix. Its cache alias and clean ONNX mappings SHALL resolve
   Snowflake-published FP16 and INT8 artifacts without falling back to BAAI.
4. Both embedders SHALL run FP16 on supported GPU providers and INT8 on CPU
   with effective model-forward batch 32. The independent outer indexing chunk
   batch MAY remain unchanged.
5. The reranker SHALL remain unchanged: the current L6 logical model, pinned
   Xenova FP16/INT8 artifacts, FP16 GPU / INT8 CPU selection, and independent
   batch 40. Its runtime success log SHALL report
   `RERANK_STATIC_BATCH`, not the embedding `STATIC_BATCH`. L2 SHALL NOT replace
   it in this change.
6. Advancing the shared model-set fingerprint from v1 to v2 SHALL force one
   complete atomic rebuild of both semantic layers before publication. This
   intentionally preserves the existing shared-fingerprint architecture and
   guarantees that BAAI and Arctic S vectors cannot mix. Subsequent unchanged-v2
   updates SHALL retain existing incremental behavior. After a target release
   `>=1.16.0` has verified or attested model set v2 (or later) and successfully
   published the complete v2 semantic epoch, upgrade SHALL remove the retired
   BAAI-derived BGE Small, BGE Base, and BGE Reranker artifacts from
   Wavefoundry-managed caches. Cleanup SHALL use an exact, path-contained
   allowlist covering their FastEmbed/Qdrant, clean-ONNX/Xenova, static-ONNX,
   and compiled-CoreML directories; it SHALL never delete a cache root,
   Snowflake or L6 artifacts, unrelated Hugging Face content, or an unmarked
   component under an operator-supplied custom cache root. The cleanup SHALL be
   idempotent, report removed and skipped targets, never follow a symlink to its
   referent, and leave the upgrade explicitly incomplete with actionable
   recovery if a required owned target cannot be removed. An exact component
   symlink MAY be unlinked as a node or rejected actionably, but its referent
   SHALL remain untouched. No cleanup SHALL run before successful v2
   verification and semantic publication, during dry-run, or after a failed
   publication. On an installing upgrade, removal SHALL execute only in the
   freshly loaded `--cleanup` process after the new framework code is active and
   before dashboard restart or upgrade-lock removal. That process SHALL verify
   a durable, current, complete all-layer semantic publication receipt/token
   bound to the v2 model fingerprint; it SHALL NOT trust only a subprocess
   success Boolean or the lock's `index_rebuilt_at` timestamp. If a later build
   has opened an incomplete semantic epoch, cleanup SHALL refuse to run. The v2
   transition SHALL NOT race cleanup with the redundant detached Phase 4c pass:
   it SHALL either suppress that pass when the foreground all-layer receipt
   already proves convergence or await it and revalidate its final receipt.
   Any removal failure SHALL set a cleanup-specific failed phase, return
   nonzero, retain the upgrade lock, and preserve exact
   removed/absent/unowned/failed reporting for recovery.
7. The framework model-set version SHALL advance from `1` to `2`, producing the
   release asset `wavefoundry-models-2.zip`. Its bundle and verification
   manifests SHALL contain the pinned Arctic XS, Arctic S, and L6 artifacts and
   metadata. New setup and upgrade flows SHALL select model set v2; an installed
   v1 set SHALL upgrade safely, and BAAI SHALL no longer be active, default,
   bundled, or setup-required in release `1.16.0`. Release and release-dry-run
   modes SHALL reject an invocation without `--with-models`; non-release local
   feature-pack builds MAY remain model-optional. Before offline cache
   publication, materialization SHALL require semantic JSON equality between
   the incoming embedded verification manifest and the installed canonical
   verification manifest; a self-consistently rehashed/revisioned substitute
   bundle SHALL fail without modifying the verified cache.
   Cleanup eligibility SHALL compare the installed pack's `to_version` against
   `1.16.0` using semantic-version precedence, ignoring build metadata; boundary
   tests SHALL cover `1.15.9`, `1.16.0`, `1.16.0+build`, and `1.16.1`.
   Unknown or malformed `to_version` values SHALL fail closed without cleanup.
8. The dedicated input
   `.wavefoundry/framework/scripts/benchmarks/model_swap_code_queries.json` and
   a backward-compatible extension of the existing `embed_bench.py` evaluator
   SHALL reproduce the 28-query Arctic XS-versus-S comparison with stable
   accepted answers, pinned model provenance, candidate ranks, production L6
   reranking, and deterministic quality metrics.
   The controlled release run SHALL write
   `model_swap_v2_result.json`, including hardware/provider facts and the
   same-machine FP16 GPU timing ratio. Normal CI SHALL recompute and validate
   the committed result's ranks, metrics, provenance, ratio arithmetic, and
   thresholds without rerunning model inference or portable wall-clock timing.
   The existing 32-query `retrieval_eval.json` fixture SHALL remain unchanged.
9. Model-selection, embedding architecture, performance, setup, and release
   documentation SHALL state the exact model, precision, and batch contracts.
   Historical records that accurately describe prior BAAI use SHALL remain
   unchanged.
10. Existing accelerator, indexer, model-bundle, setup, upgrade, package, and
    benchmark test helpers SHALL be updated or parameterized for Arctic S/model
    set v2 wherever they already cover the behavior. The implementation SHALL
    not create a parallel test suite solely because the model ID changed; new
    fixtures are limited to behavior the current suite does not express.

## Scope

**Problem statement:** The active code embedding model has a supplier origin
that no longer meets the product requirement.

**In scope:**

- Swap the code embedder from BAAI BGE Small to Snowflake Arctic S.
- Keep Arctic XS for documents and MiniLM L6 for reranking.
- Set both embedding forward paths to FP16 GPU / INT8 CPU at batch 32.
- Add Arctic S prefix, alias, artifact, bundle, and verification-manifest data.
- Record the manually reviewed supplier origin for the v2 model set.
- Update model packaging, setup, and upgrade behavior for
  `wavefoundry-models-2.zip` in framework release `1.16.0`.
- Remove retired BAAI-derived BGE Small, BGE Base, and BGE Reranker artifacts
  from exact Wavefoundry-owned cache targets only after v2 verification and
  complete semantic publication.
- Force a safe one-time full semantic re-index and add focused resolution, fallback, quality,
  performance, CPU, GPU, bundle, and offline-setup tests.
- Update the directly affected documentation.

**Out of scope:**

- Automated jurisdiction validation, a generalized supplier policy engine, or
  an online evidence verifier.
- Redesigning model acquisition, caching, background downloads, or query-time
  network behavior.
- Replacing L6 with L2, migrating its Xenova artifacts, or changing reranker
  batch 40.
- Deleting whole cache roots, unrelated/shared Hugging Face content, unmarked
  custom-cache components, or rewriting historical records.
- Multilingual retrieval, hosted inference, remote indexing, or changing vector
  dimensions.
- The broad retrieval-intent golden-query framework planned by `1seaw`; this
  wave commits only the focused model-swap fixture.

### Retired cache cleanup allowlist

Cleanup is restricted to the following relative component directories beneath
their named cache root. Public-name and runtime-alias FastEmbed entries are both
listed because either can exist from prior releases; no prefix, wildcard, model
family, or cache-root deletion is permitted.

| Cache root | Exact relative component directories |
| --- | --- |
| FastEmbed | `models--BAAI--bge-small-en-v1.5`; `models--qdrant--bge-small-en-v1.5-onnx-q`; `models--BAAI--bge-base-en-v1.5`; `models--qdrant--bge-base-en-v1.5-onnx-q`; `models--BAAI--bge-reranker-base` |
| clean ONNX source | `models--Xenova--bge-small-en-v1.5`; `models--Xenova--bge-reranker-base` |
| static ONNX | `BAAI__bge-small-en-v1.5`; `BAAI__bge-base-en-v1.5`; `BAAI__bge-reranker-base` |
| compiled Core ML | `BAAI__bge-small-en-v1.5`; `BAAI__bge-base-en-v1.5`; `BAAI__bge-reranker-base` |

Default Wavefoundry cache roots own those exact components. Under an
operator-supplied FastEmbed or clean-ONNX root, a component is owned only when
its existing Wavefoundry model-bundle attestation marker names that exact
component and the marker's recorded file inventory and hashes verify against
the component at cleanup time. Marker presence alone is not ownership: missing,
malformed, stale, or file-mismatched markers leave the component untouched and
report it as unowned. A missing component is an idempotent skip; an existing
owned component that cannot be removed is a cleanup failure.

## Acceptance Criteria

- [ ] AC-1: Runtime constants select Arctic XS for documents, Arctic S for code,
  and the existing L6/Xenova reranker contract; embedding outputs remain 384
  dimensional and Arctic S uses the Snowflake query-only prefix.
- [ ] AC-2: The generated model-set verification manifest contains the exact v2
  artifact/revision/hash/license/attribution facts for Arctic XS, Arctic S, and
  L6/Xenova. The separate model-selection record contains the manual
  supplier-origin decision, reviewer, date, and evidence URLs; bundle generation
  still reproduces the canonical manifest exactly, and no runtime jurisdiction
  validator is introduced.
- [ ] AC-3: Arctic S resolves Snowflake-published FP16 on supported GPU providers
  and INT8 on CPU, with cache alias and clean-ONNX tests proving that BAAI is not
  selected as a fallback.
- [ ] AC-4: Arctic XS and Arctic S use effective embedding batch 32 on GPU and
  CPU. Tests verify provider, precision, actual forward width, output dimension,
  and parity tolerance; the outer chunk batch is tested as an independent knob.
- [ ] AC-5: L6 remains on its current logical ID, pinned Xenova FP16/INT8
  revision and hashes, provider mapping, and batch 40. Tests fail if L2 replaces
  it or the reranker batch is coupled to embedding batch 32. The existing
  successful-reranker server test asserts the public success log reports
  `static 40x512` when embedding batch is 32.
- [ ] AC-6: The v1-to-v2 shared fingerprint change forces one complete atomic
  rebuild of both docs and code layers before publication and cannot expose
  mixed-model vectors. Once v2 is published, unchanged-v2 updates retain the
  existing incremental behavior. Upgrade cleanup cannot run before the verified
  v2 model set and complete v2 semantic epoch are both durable. The freshly
  loaded cleanup process reopens and verifies the durable all-layer
  receipt/token and exact v2 fingerprint; the upgrade lock timestamp or a bare
  child-process result is not sufficient authority.
- [ ] AC-7: `MODEL_SET_VERSION` is `2`, the compatibility fingerprint is a new
  v2 identity, and `wavefoundry-models-2.zip` builds and validates with only the
  pinned Arctic XS, Arctic S, and L6 artifacts. New setup and upgrade select v2,
  an installed v1 set upgrades safely, offline materialization remains
  network-inert, and BAAI is absent from v2 active/default/setup/bundle records.
  Release and release-dry-run without `--with-models` fail before publication;
  a successful release receipt asserts both the exact feature archive and
  the `1.16.0` feature archive plus `wavefoundry-models-2.zip`, while
  non-release local builds remain optional.
  Offline materialization also rejects a bundle whose embedded verification
  manifest differs semantically from the installed canonical manifest—even
  when substituted payload bytes, revision refs, and embedded hashes are
  internally consistent—and leaves the verified cache unchanged.
- [ ] AC-8: On an upgrade to `1.16.0` or later, after verified/attested model set
  v2 and complete semantic publication, cleanup removes the exact retired
  BAAI-derived BGE Small, BGE Base, and BGE Reranker directories from
  Wavefoundry's FastEmbed, clean-ONNX, static-ONNX, and compiled-CoreML caches.
  Tests prove path containment, exact allowlisting, idempotent reruns,
  removed/skipped reporting, and no deletion of Snowflake, L6, unrelated cache
  entries, cache roots, or unmarked components beneath custom cache overrides.
  A symlink mutant proves cleanup never traverses an allowlisted component or
  custom-root symlink into an external referent: the referent remains intact,
  while the component link is either unlinked without following it or rejected
  actionably. Custom-root tests prove marker presence is insufficient; missing,
  malformed, stale, and file-mismatched attestations classify the component as
  unowned and preserve it. Immediately before mutation, cleanup re-lstats the
  root and component, revalidates containment and any ownership attestation,
  and uses a no-follow deletion path; a check/use substitution mutant that
  replaces the component with an external symlink preserves the referent and
  fails or safely unlinks only the link node.
  Dry-run, failed verification/publication, and pre-publication paths delete
  nothing; a required owned-target removal failure keeps upgrade completion
  explicit and actionable. On the first transition to new framework code,
  cleanup runs in the freshly loaded `--cleanup` process before dashboard
  restart and upgrade-lock removal. Tests mutation-kill reliance on only a
  subprocess success Boolean or `index_rebuilt_at`: cleanup requires a current
  durable receipt/token for the complete docs-and-code v2 semantic epoch and
  refuses if a later detached build has opened an incomplete epoch. Failure
  returns nonzero, records a cleanup-specific failed phase, retains the upgrade
  lock, and preserves exact removed/absent/unowned/failed status. Eligibility
  uses semantic precedence of pack `to_version` with build metadata ignored,
  with tests for `1.15.9`, `1.16.0`, `1.16.0+build`, `1.16.1`, and
  unknown/malformed fail-closed inputs. The transition either suppresses the
  redundant detached Phase 4c pass when foreground convergence is authoritative
  or awaits it and validates its final receipt before cleanup.
  With only an unmanaged stale BAAI cache available, active resolution obtains
  Arctic S through the existing acquisition behavior or fails explicitly—never
  by fallback.
- [ ] AC-9: `model_swap_code_queries.json` contains exactly 28 code queries and
  accepted answers; a backward-compatible `embed_bench.py` mode runs pinned
  candidate retrieval plus production L6 and writes `model_swap_v2_result.json`
  with per-query raw and reranked ranks, provenance, and controlled timing.
  Arctic S is no worse than
  Arctic XS at aggregate top-3, top-10, and MRR before reranking and top-5,
  top-10, and MRR after L6, loses no required answer from top 40, and its
  recorded same-machine FP16 GPU time is within 2.0x XS. A focused CI test
  recomputes those metrics and ratio from the committed result and detects
  threshold/provenance/rank mutations without running model inference. The
  existing 32-query `retrieval_eval.json` remains byte-identical.
- [ ] AC-10: Existing test helpers and fixtures are updated/parameterized for
  Arctic S and model set v2 wherever they already own the behavior; the existing
  32-query benchmark remains compatible and byte-identical. Directly affected
  model-selection, architecture, performance,
  setup, upgrade, decision, release, framework-version, and changelog surfaces
  agree on framework `1.16.0` and model set v2; the changelog contains the exact
  `1.16.0` release heading required by packaging, focused tests and package
  build verification pass, docs lint is clean, and the full framework suite
  passes.

## Tasks

- [ ] Replace the code model constant with Arctic S and add its query-prefix,
  cache-alias, FP16, and INT8 mappings.
- [ ] Change the embedding static forward batch from 64 to 32 while preserving
  the CPU batch 32 and reranker batch 40 contracts; correct the existing
  reranker success log to use `RERANK_STATIC_BATCH` and extend its current test.
- [ ] Update the model-set manifest, compatibility fingerprint, bundle inputs,
  licenses, revisions, hashes, and manually reviewed supplier-origin record.
- [ ] Advance `MODEL_SET_VERSION` to `2` and update setup, upgrade, package,
  version, and release tests/surfaces for `wavefoundry-models-2.zip`; require
  `--with-models` in release/release-dry-run mode and assert both release assets.
- [ ] Add a stdlib-only, exact-path retired-model cleanup to the post-publication
  upgrade path for target releases `>=1.16.0`. Derive only the fixed BAAI BGE
  Small/Base/Reranker FastEmbed/Qdrant, clean-ONNX/Xenova, static-ONNX, and
  compiled-CoreML targets; require Wavefoundry ownership markers for custom
  cache roots and re-verify their recorded file inventory and hashes; validate
  containment without following symlinks before deletion; and report removed,
  absent, unowned, and failed targets. Re-lstat and revalidate immediately at
  the mutation boundary; never follow a component or cache-root symlink to its
  referent. Invoke cleanup from the freshly loaded `--cleanup` process, before
  dashboard restart and upgrade-lock removal, only after reopening a current
  durable all-layer v2 publication receipt/token. Do not authorize it from only
  a subprocess Boolean or `index_rebuilt_at`; refuse when a later semantic epoch
  is incomplete. Suppress the redundant detached Phase 4c pass when foreground
  convergence is authoritative, or await it and validate its final receipt.
  On failure, set a cleanup-specific failed phase, return nonzero, retain the
  lock, and persist the exact result projection. Gate on pack
  `to_version >= 1.16.0` by semantic precedence with build metadata ignored;
  unknown or malformed versions fail closed.
- [ ] Bind offline materialization to the installed canonical verification
  manifest and extend the existing bundle tamper test with a self-consistent
  payload/revision/ref/hash substitution that must fail before publication.
- [ ] Verify BAAI is absent from active/default/bundled/setup-required paths,
  retired Wavefoundry-owned cache targets are removed only after successful v2
  convergence, unrelated/user-managed caches remain intact, and historical
  records remain accurate.
- [ ] Add shared-fingerprint full-rebuild, atomic publication, no-mixed-vector,
  and subsequent unchanged-v2 incremental-update tests.
- [ ] Add `model_swap_code_queries.json` and `model_swap_v2_result.json`; extend
  `embed_bench.py` backward-compatibly for the controlled release evaluation and
  focused deterministic CI result validation while preserving the existing
  `retrieval_eval.json` input and behavior.
- [ ] Update existing accelerator, indexer, model-bundle, setup, upgrade,
  package, and benchmark tests in place; add a new fixture/test only where an
  existing owner cannot express the required behavior.
- [ ] Update directly affected documentation and run focused/full verification.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Model swap and manifest | implementer | — | Constants, mappings, batch, supplier record, bundle inputs. |
| Rebuild and fallback safety | implementer | Model swap and manifest | Shared fingerprint, atomic full publication, then fresh-process exact retired-model cleanup before restart/lock removal. |
| Retrieval and runtime verification | qa-reviewer | Rebuild and fallback safety | CPU/GPU, quality, timing, mutation, and offline tests. |
| Documentation | implementer | Model swap and manifest | Record the exact delivered model contract. |
| Independent delivery review | qa-reviewer | Retrieval and runtime verification, Documentation | Verify required ACs and supplier evidence. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/model_bundle.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/VERSION`
- `.wavefoundry/framework/model-set-verification-manifest.json`
- `.wavefoundry/framework/scripts/benchmarks/model_swap_code_queries.json`
- `.wavefoundry/framework/scripts/benchmarks/embed_bench.py`
- `.wavefoundry/framework/scripts/benchmarks/model_swap_v2_result.json`
- `.wavefoundry/framework/scripts/tests/`
- `README.md`
- `docs/references/model-selection.md`
- `docs/architecture/embedding-model.md`
- `docs/architecture/performance-budget.md`
- `docs/architecture/decisions/1p92d-adr embedding-precision-policy.md`
- `CHANGELOG.md`

Model constants, artifact mappings, the compatibility fingerprint, and the
verification manifest SHALL change together before bundle or retrieval evidence
is accepted.

## Affected Architecture Docs

- `docs/architecture/embedding-model.md` — update the code model, precision,
  batch, prefix, artifact, and re-index facts.
- `docs/architecture/performance-budget.md` — distinguish embedding batch 32
  from reranker batch 40 and record the accepted Arctic S indexing cost.
- `docs/architecture/decisions/1p92d-adr embedding-precision-policy.md` — append
  the Arctic S and embedding-batch decision evidence without rewriting history.
- `docs/architecture/current-state.md` — update only if it names the superseded
  code model or embedding batch.

`docs/ARCHITECTURE.md` needs no change because component ownership and top-level
boundaries do not change.

## AC Priority


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The exact model set is the operator-approved outcome. |
| AC-2 | required | The manual supplier decision and exact artifact provenance must be durable. |
| AC-3 | required | The new model must resolve correctly without a BAAI fallback. |
| AC-4 | required | FP16 GPU / INT8 CPU batch 32 is part of the approved deployment contract. |
| AC-5 | required | The accepted L6 reranker must remain unchanged. |
| AC-6 | required | The existing shared fingerprint must migrate atomically without mixed vectors. |
| AC-7 | required | The new release must package and upgrade to the approved v2 model set. |
| AC-8 | required | The operator-required 1.16 cleanup must remove only retired Wavefoundry-owned BAAI artifacts after safe convergence. |
| AC-9 | required | Quality and practical indexing cost justify S instead of XS for code. |
| AC-10 | important | Durable docs and full regression evidence keep the release coherent. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Created and admitted the planned supplier-lineage model-swap wave without taking the OPEN slot. | Wave `1v0r0`; change `1v0qz-enh`. |
| 2026-08-10 | Confirmed XS documents, S code, embedding FP16 GPU / INT8 CPU batch 32, and retained L6 FP16 GPU / INT8 CPU batch 40. | Operator confirmation and current runtime inspection. |
| 2026-08-10 | Compared Arctic XS and S on 28 queries over 6,895 code chunks with production L6 reranking. | Raw S top-3 89.29%, top-10 96.43%, MRR 0.8822 versus XS 85.71%, 92.86%, 0.8718. Reranked S top-5 89.29%, top-10 96.43%, MRR 0.8560 versus XS 85.71%, 96.43%, 0.8376. FP16 MPS batch-32 time: S 21.485s, XS 13.185s. AC-9 requires the durable committed fixture. |
| 2026-08-10 | The initial council exposed provenance, acquisition-path, validation, and fixture ambiguities; the operator then challenged the wave's complexity. | Red-team context `1v0r0-redteam-20260810-supplier-lineage-01`; docs-contract context `1v0r0-docs-contract-20260810-final-03`; plan narrowed to the direct model swap and manual supplier record. |
| 2026-08-10 | Removed automated jurisdiction validation and added model bundle v2 to the release scope. | Operator direction: supplier origin is reviewed manually at model-swap time; the new release must ship `wavefoundry-models-2.zip`. |
| 2026-08-11 | Simplified the v2 migration after the narrowed red-team review. | Context `1v0r0-redteam-20260811-modelswap-02`: accept one full semantic rebuild under the existing shared fingerprint, keep manual supplier evidence outside the generated manifest schema, and treat the measured timing ratio as controlled release evidence. |
| 2026-08-11 | Defined a dedicated deterministic 28-query input/result without replacing the existing mixed benchmark or evaluator. | QA context `1v0r0-qa-20260811-modelswap-final-05` plus operator direction to reuse tests: extend `embed_bench.py` backward-compatibly, add the dedicated input/result, and keep existing `retrieval_eval.json` byte-identical. |
| 2026-08-11 | Made the v2 model companion mandatory for release-mode packaging. | Release context `CTX-1v0r0-release-final-20260811-A7C4`: release/release-dry-run must reject missing `--with-models` and the release receipt must assert both the feature archive and `wavefoundry-models-2.zip`; local non-release builds stay optional. |
| 2026-08-11 | Added the bounded batch-log and canonical-bundle-binding repairs exposed by final lane review. | Code context `1v0r0-code-recheck-20260811-modelswap-final-06`: log `RERANK_STATIC_BATCH` and extend the existing success test. Security context `1v0r0-security-20260811-modelswap-final-06`: compare the incoming embedded verification manifest to the installed canonical authority before offline publication and mutation-test a self-consistently remanifested substitute. |
| 2026-08-11 | Locked the framework release version to `1.16.0`. | Operator approval; feature-archive name, VERSION stamp, release receipt, and changelog heading are now deterministic. |
| 2026-08-11 | Added bounded removal of retired BAAI-derived caches during upgrades to `1.16.0` or later. | Operator direction; cleanup is post-verification/post-publication, exact-path and ownership-gated, idempotent, auditable, and cannot delete unrelated or shared cache content. This load-bearing revision requires a fresh readiness receipt and affected-lane review. |
| 2026-08-11 | Bound cleanup to the freshly loaded upgrade process and durable all-layer publication authority. | Fresh QA, security, and release review required no-follow symlink handling, file-verified custom-root ownership, mutation-boundary revalidation, semantic `to_version` gating, a current v2 all-layer receipt/token, and lock-retaining nonzero failure before dashboard restart or lock removal. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | Replace BAAI with Arctic S for code and retain Arctic XS for documents. | S had a small consistent code-quality advantage; XS remains the proven document choice. | XS for both: faster but weaker on code. Granite: CPU cost was not viable. Keep BAAI: fails supplier origin. |
| 2026-08-10 | Retain the current L6 logical model and Xenova artifacts on CPU and GPU. | L6 already meets the accepted supplier requirement and the L2 test lost quality. | L2: faster but lower quality. Official-artifact migration: unrelated risk. |
| 2026-08-10 | Use embedding batch 32 on CPU and GPU; keep reranker batch 40. | Embedding batch 32 is the approved cross-device setting; reranking has a separately tested optimum. | Keep GPU embedding batch 64 or couple reranking to 32: contrary to the measured contracts. |
| 2026-08-10 | Record supplier lineage as a manual model-swap decision, not runtime jurisdiction validation. | Supplier selection is infrequent and reviewed with each swap; runtime legal-policy machinery is disproportionate. | Automated jurisdiction engine: unnecessary complexity. Omit provenance: loses the reason for the swap. |
| 2026-08-10 | Publish the changed packaged model set as v2 with framework `1.16.0`. | The code model, bundle contents, hashes, compatibility fingerprint, VERSION stamp, and changelog key change together and must not masquerade as v1. | Overwrite v1: breaks immutable model-set identity. Delay packaging: leaves offline installs on BAAI. |
| 2026-08-11 | Use the existing shared model-set fingerprint and perform a one-time full semantic rebuild for v2. | This is safer and simpler than adding per-layer fingerprint semantics solely to avoid rebuilding unchanged docs. | Per-layer fingerprints: broader architecture change. Code-only rebuild under the shared fingerprint: contradicts current behavior. |
| 2026-08-11 | Keep manual supplier evidence in the model-selection decision record, separate from the generated verification manifest. | The manifest is deterministically generated from cached artifacts and compared exactly during bundle creation. | Add hand-authored fields only to canonical JSON: breaks bundle equality. Expand the generator schema: unnecessary for manual review. |
| 2026-08-11 | Reuse and extend the existing benchmark/test owners for the model swap. | Most behavior already has accelerator, indexer, bundle, setup, upgrade, package, and benchmark fixtures; model-ID changes should update those expectations rather than fork coverage. | Parallel replacement suite: duplicate ownership and drift. Replace `retrieval_eval.json`: loses existing coverage. |
| 2026-08-11 | Require the model companion in release and release-dry-run modes. | Manual recovery expects the companion on the same release, and a feature-only release would leave offline users on model set v1. | Keep `--with-models` optional for releases: permits an incomplete v2 release. Require it for every local build: unnecessary. |
| 2026-08-11 | Bind offline bundle consumption to the installed canonical verification manifest. | Self-consistent embedded hashes prove internal consistency, not that the bytes are the reviewed v2 artifacts. | Trust the incoming manifest alone: permits re-manifested substitutions. Add signature infrastructure: broader than the existing canonical-manifest trust model. |
| 2026-08-11 | Remove retired BAAI-derived artifacts from Wavefoundry-owned caches after successful v2 convergence while preserving historical records. | Supplier-lineage cleanup should remove obsolete local weights, but only after the replacement model set and semantic epoch are durable. | Preserve every old cache: leaves retired BAAI weights behind. Delete before publication or purge whole/shared caches: unsafe and unnecessary. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A future model swap overlooks supplier origin. | Keep supplier decision, reviewer, date, and evidence in the model-selection and verification records and require the same manual review in future model-swap plans. |
| A new release still selects model bundle v1. | Version the model set and fingerprint as v2 and test setup, upgrade, package contents, recovery guidance, and v1-to-v2 transition. |
| A self-consistently re-manifested bundle substitutes unreviewed model bytes. | Require incoming/canonical manifest equality before materialization and mutation-test changed payload, revision/ref, and hashes together. |
| Arctic S artifact mappings differ from XS. | Pin and test Snowflake's exact FP16/INT8 paths, revisions, hashes, tokenizer, and prefix. |
| A stale BAAI cache wins resolution. | Test both models present and BAAI-only cache states; active resolution must select/acquire S or fail explicitly. |
| Cleanup deletes user-managed or still-needed model data. | Use fixed retired-model IDs and exact directory names, validate containment under Wavefoundry roots without following symlinks, require a file-verified Wavefoundry ownership marker beneath custom roots, and mutation-test sibling/cache-root, forged-marker, stale-marker, and external-symlink targets. |
| Cleanup removes the recovery path before v2 is usable. | In the freshly loaded cleanup process, reopen a current all-layer v2 receipt/token and run before restart/lock removal; do not trust only `index_rebuilt_at` or subprocess success, refuse a later incomplete epoch, and retain the lock with a cleanup-specific failed phase on failure. |
| The v2 swap leaves mixed vectors. | Use the existing shared fingerprint to force a complete atomic docs+code rebuild before v2 publication. |
| Arctic S indexing is too slow on developer hardware. | Use batch 32, test CPU/GPU paths, and enforce the same-machine 2.0x relative ceiling. |
| The focused query set overfits the current repository. | Commit query intent and accepted-answer rationale; leave the broader golden suite to `1seaw`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
