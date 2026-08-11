# Supplier-Lineage-Compliant Retrieval Model Swap

Change ID: `1v0qz-enh supplier-lineage-compliant-retrieval-models`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-11
Wave: `1v0r0 supplier-lineage-compliant-retrieval`

## Rationale

Supplier origin is now a product requirement. Wavefoundry's active code
embedder, `BAAI/bge-small-en-v1.5`, does not satisfy it. The direct correction
is to use `Snowflake/snowflake-arctic-embed-s` as the single embedding model
for both documents and code while leaving the accepted reranker in place.

A 28-query comparison over 6,895 current code chunks found a small, consistent
quality advantage for Arctic S over Arctic XS before and after the production
L6 reranker. A separate 100-query document comparison over 23,410 current
document chunks found no statistically distinguishable quality loss from S:
after production L6 reranking, XS/S were 61%/60% at top 3, tied at 67% top 5,
80% top 10, and 83% top 20, with MRR 0.5185/0.5178; every paired 95% interval
included zero. Arctic S is slower to index, but its measured FP16 GPU time
stayed inside the accepted 2.0x relative ceiling. One shared model also lets
the existing model-name-keyed caches reuse one in-memory embedder for both
layers instead of retaining separate XS and S instances. The swap advances the
packaged offline model set from v1 to v2 for Wavefoundry `1.16.0`; supplier
origin remains a manual, evidence-backed decision whenever that model set is
changed.

## Requirements

1. The production model set SHALL use
   `Snowflake/snowflake-arctic-embed-s` as the single embedding model for both
   documents and code, plus the existing
   `cross-encoder/ms-marco-MiniLM-L-6-v2` logical reranker resolved through its
   existing pinned `Xenova/ms-marco-MiniLM-L-6-v2` artifact export. Embedding
   dimensions SHALL remain 384. Document and code model selection SHALL remain
   separate configuration points so a future reviewed model swap can diverge
   them without restoring a split-model implementation. For v2, both
   configuration points SHALL independently name Arctic S.
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
4. The shared embedder SHALL run FP16 on supported GPU providers and INT8 on
   CPU with effective model-forward batch 32. Existing per-model caches SHALL
   reuse one model instance when both layers request Arctic S; equality of the
   two configured model IDs SHALL enable reuse, but SHALL NOT collapse their
   two configuration authorities into one constant. When both layers
   participate in one build with equal model IDs, the build SHALL choose one
   execution class before either embedder is loaded: bulk/full if either layer
   requires it, otherwise the existing small-run CPU class. It SHALL load once
   and assign that instance to both layers. Divergent model IDs retain
   independent execution-class resolution. The independent outer indexing
   chunk batch MAY remain unchanged.
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
   idempotent, report the exact cleanup result contract below, never follow a symlink to its
   referent, and leave the upgrade explicitly incomplete with actionable
   recovery if a required owned target cannot be removed. An exact component
   symlink MAY be unlinked as a node or rejected actionably, but its referent
   SHALL remain untouched. No cleanup SHALL run before successful v2
   verification and semantic publication, during dry-run, or after a failed
   publication. On an installing upgrade, removal SHALL execute only in the
   freshly loaded `--cleanup` process after the new framework code is active and
   before dashboard restart or upgrade-lock removal. That process SHALL verify
   the sole durable semantic authority in `index-state.sqlite`: read one stable
   token, a bounded `build_state` plus `build_layer_meta` summary, then the token
   again; both token reads SHALL be identical, the epoch SHALL be complete with
   docs and code present. Both composite model-version values SHALL identify the
   exact active docs/code models and approved precision classes declared by the
   installed canonical model set, and each fingerprint suffix SHALL equal that
   set's exact active shared identity. For v2 both identities are Arctic S; a
   later model set uses its own canonical active identities. It SHALL NOT
   create a second receipt file or trust only
   a subprocess success Boolean, an upgrade-lock copy, or the lock's
   `index_rebuilt_at` timestamp. If a later build has opened an incomplete
   semantic epoch, cleanup SHALL refuse to run. The v2
   transition SHALL NOT race cleanup with the redundant detached Phase 4c pass:
   the foreground update SHALL produce the complete all-layer v2 receipt and
   SHALL suppress Phase 4c for that transition.
   Any removal failure SHALL set failed phase `retired_model_cleanup`, return
   nonzero, retain the upgrade lock, and preserve exact
   removed/absent/unowned/failed reporting for recovery.
   Cleanup SHALL also fail closed if the currently installed canonical model
   manifest declares any allowlisted retired component active; a model-set
   version of v2 or later alone is not deletion authority.
7. The framework model-set version SHALL advance from `1` to `2`, producing the
   release asset `wavefoundry-models-2.zip`. Its bundle and verification
   manifests SHALL contain only the pinned Arctic S embedding and L6 reranker
   artifacts and metadata. Arctic XS SHALL no longer be active, default,
   bundled, or setup-required, but its existing non-BAAI cache is not part of
   the operator-requested retired-supplier cleanup. New setup and upgrade flows
   SHALL select model set v2; an installed
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
   Retired BAAI and Arctic XS runtime/default/acquisition/setup/package mappings
   SHALL be removed rather than left unreachable. The residue census SHALL use
   this closed classification: production/default/acquisition/setup/package and
   current-behavior test expectations use Arctic S only; exact v1-to-v2
   migration input fixtures MAY contain BAAI and Arctic XS but SHALL never
   expect them in v2 output; cleanup MAY contain only the exact BAAI allowlist
   identifiers; model-comparison evidence MAY contain Arctic XS and S; frozen
   comparison-input fixtures, authored at comparison time, MAY name the
   then-current retired identifier in query or accepted-answer text, are bound
   by hash to the committed comparison result, and are never re-authored;
   accurate historical documents and decision rows remain unchanged. Every
   other BAAI or Arctic XS occurrence SHALL fail the census.
8. The dedicated inputs
   `.wavefoundry/framework/scripts/benchmarks/model_swap_code_queries.json` and
   `.wavefoundry/framework/scripts/benchmarks/model_swap_docs_queries.json`,
   plus a backward-compatible extension of the existing `embed_bench.py`
   evaluator, SHALL reproduce the 28-query code and 100-query document Arctic
   XS-versus-S comparisons with stable accepted answers, pinned model
   provenance, candidate ranks, production L6 reranking, and deterministic
   quality metrics.
   The controlled release run SHALL write
   `model_swap_v2_result.json`, including hardware/provider facts and the
   same-machine FP16 GPU timing ratio. Normal CI SHALL recompute and validate
   the committed result's ranks, metrics, provenance, ratio arithmetic, and
   thresholds without rerunning model inference or portable wall-clock timing.
   The existing 32-query `retrieval_eval.json` fixture SHALL remain unchanged.
9. Model-selection, embedding architecture, performance, setup, and release
   documentation SHALL state the exact model, precision, and batch contracts.
   The public Package Wavefoundry prompt SHALL state that release and release
   dry-run require the matching model companion, while non-release local builds
   remain model-optional.
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

- Use Snowflake Arctic S as the single document-and-code embedder, replacing
  BAAI BGE Small for code and Arctic XS as the active document default.
- Preserve independently configurable document and code model selectors, with
  both selectors set to Arctic S in model set v2 and one cached instance reused
  because their configured IDs match.
- Keep MiniLM L6 for reranking.
- Set the shared embedding forward path to FP16 GPU / INT8 CPU at batch 32 and
  verify both layers reuse the model-name-keyed instance.
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
- Removing the reranker or redesigning `code_ask` relevance calibration,
  weak-match abstention, confidence bands, or candidate-selection semantics;
  the broader `1seaw` golden-query evaluation is the appropriate proof surface
  for that architectural change.
- Deleting whole cache roots, unrelated/shared Hugging Face content, unmarked
  custom-cache components, or rewriting historical records.
- Collapsing document and code selection into a single configuration authority;
  future divergence remains possible only through another reviewed model swap.
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

Cleanup always evaluates the fixed default Wavefoundry FastEmbed and clean-ONNX
roots because prior producer/runtime paths may have populated them. When the
corresponding cache override names a distinct root, cleanup evaluates that root
as an additional custom target; an override never substitutes for inspecting
the default runtime root. Default Wavefoundry cache roots own the exact
allowlisted components. Under a custom root, the existing v1 marker need not
carry a component identifier: ownership is bound by the marker's location at an
exact allowlisted component path beneath that root plus successful verification
of its immutable retired-v1 model-set version/fingerprint and exact recorded
legacy inventory domain and hashes at cleanup time. That domain is exactly the
marker-recorded `refs/` and `snapshots/` entries. The marker itself and only
`blobs/` objects transitively referenced by those recorded snapshots may exist
outside the marker map; unreferenced blobs and every other unrecorded file make
the component unowned.
Marker presence alone is not ownership: missing, malformed, stale,
wrong-version, wrong-fingerprint, extra-file, or file-mismatched markers leave
the component untouched and report it as unowned. A missing component is an
idempotent skip; an existing owned component that cannot be removed is a cleanup
failure.

### Public cleanup result contract

The upgrade response, retained upgrade-lock state, and `wf_upgrade_status`
summary use the same flat bounded fields; they SHALL NOT wrap this result in a
nested object:

- `retired_model_cleanup_status`: one of `not_applicable`, `dry_run`,
  `complete`, or `failed`.
- `retired_model_cleanup_removed`: stable target IDs successfully removed.
- `retired_model_cleanup_absent`: stable target IDs already absent.
- `retired_model_cleanup_unowned`: stable target IDs preserved because ownership
  proof failed.
- `retired_model_cleanup_failed`: entries formatted
  `<target-id>|remove_failed` for owned targets whose removal failed.

A target ID is `<cache-kind>:<scope>:<component-key>`, where `cache-kind` is
`fastembed`, `clean-onnx`, `static-onnx`, or `coreml`; `scope` is `default` or
`custom`; and `component-key` is the exact relative allowlist entry with no
absolute path. Lists are deterministic, deduplicated, lexically sorted, and
bounded by the finite allowlist. Dry-run returns `dry_run` with all four lists
empty; `not_applicable` also carries four empty lists. `remove_failed` is the
only allowed public reason code. Raw exception text, errno text, and filesystem
paths SHALL NOT enter any of the five public fields. Successful applicable
cleanup returns `complete` with an empty failed list. Failure returns `failed`,
preserves every partial result list in the
retained lock, sets `failed_phase=retired_model_cleanup`, and emits diagnostic
code `retired_model_cleanup_failed` with recovery
`wf_upgrade(phase="cleanup")`. That call retries only this failed phase after
revalidating all authorities and remaining targets; unrelated failed phases
retain their existing recovery behavior. `wf_upgrade_status` exposes these same
five fields until successful retry clears the failure and removes the lock.
All five keys are protected terminal fields in `_bounded_upgrade_summary` and
whole-response bounding: they bypass or receive reserved capacity ahead of
generic collection fields, remain present with exact key parity even when
`reconciliation`, host-permission, or other collections saturate their shared
budget, and are never replaced by a nested object. The public
`wf_upgrade(mode="dry_run")` / `upgrade_wavefoundry.py --dry-run` path emits its
upgrade summary sentinel with `retired_model_cleanup_status=dry_run` and all
four lists empty.

## Acceptance Criteria

- [x] AC-1: Separate document and code runtime configuration constants each
  select Arctic S, without aliasing one constant to the other, plus the existing
  L6/Xenova reranker contract; embedding outputs remain 384 dimensional and
  both layers use the Snowflake query-only prefix. A focused fixture can set the
  two selectors to different IDs without changing production defaults.
- [x] AC-2: The generated model-set verification manifest contains the exact v2
  artifact/revision/hash/license/attribution facts for Arctic S and L6/Xenova,
  with no active/bundled Arctic XS component. The separate model-selection
  record contains the manual
  supplier-origin decision, reviewer, date, and evidence URLs; bundle generation
  still reproduces the canonical manifest exactly, and no runtime jurisdiction
  validator is introduced.
- [x] AC-3: Arctic S resolves Snowflake-published FP16 on supported GPU providers
  and INT8 on CPU, with cache alias and clean-ONNX tests proving that BAAI is not
  selected as a fallback.
- [x] AC-4: The shared Arctic S embedder uses effective embedding batch 32 on
  GPU and CPU. Tests verify provider, precision, actual forward width, output
  dimension, and parity tolerance; the outer chunk batch remains an independent
  knob. Server and indexer cache tests prove identical document/code model names
  resolve to one in-process embedder instance rather than two. A mixed-boundary
  fixture with one layer below and one layer at the incremental-GPU threshold
  proves a single preselected bulk execution class, one constructor call, and
  object identity across both layers. When both are below the threshold they
  share the existing small-run CPU class. A divergent-selector fixture resolves
  independent instances through the same generic model-name-keyed path.
- [x] AC-5: L6 remains on its current logical ID, pinned Xenova FP16/INT8
  revision and hashes, provider mapping, and batch 40. Tests fail if L2 replaces
  it or the reranker batch is coupled to embedding batch 32. The existing
  successful-reranker server test asserts the public success log reports
  `static 40x512` when embedding batch is 32.
- [x] AC-6: The v1-to-v2 shared fingerprint change forces one complete atomic
  rebuild of both docs and code layers before publication and cannot expose
  mixed-model vectors. Once v2 is published, unchanged-v2 updates retain the
  existing incremental behavior. Upgrade cleanup cannot run before the verified
  v2 model set and complete v2 semantic epoch are both durable. The freshly
  loaded cleanup process reopens and verifies the durable all-layer
  receipt/token and exact v2 fingerprint; the upgrade lock timestamp or a bare
  child-process result is not sufficient authority.
- [x] AC-7: `MODEL_SET_VERSION` is `2`, the compatibility fingerprint is a new
  v2 identity, and `wavefoundry-models-2.zip` builds and validates with only the
  pinned Arctic S and L6 artifacts. New setup and upgrade select v2, an
  installed v1 set upgrades safely, offline materialization remains
  network-inert, and BAAI plus Arctic XS are absent from v2
  active/default/setup/bundle records.
  Release and release-dry-run without `--with-models` fail before publication;
  a successful release receipt asserts both the exact feature archive and
  the `1.16.0` feature archive plus `wavefoundry-models-2.zip`, while
  non-release local builds remain optional.
  Offline materialization also rejects a bundle whose embedded verification
  manifest differs semantically from the installed canonical manifest—even
  when substituted payload bytes, revision refs, and embedded hashes are
  internally consistent—and leaves the verified cache unchanged.
  A source/data census proves retired BAAI and Arctic XS mappings are not merely
  unreachable: no obsolete runtime, default, acquisition, setup, packaging, or
  current-behavior test expectation remains. Exact v1 migration inputs may
  contain both legacy identities but never as expected v2 output; cleanup may
  contain only exact BAAI allowlist identifiers; comparison evidence may contain
  XS/S; and accurate history remains unchanged. Every other occurrence fails.
- [x] AC-8: On an upgrade to `1.16.0` or later, after verified/attested model set
  v2 and complete semantic publication, cleanup removes the exact retired
  BAAI-derived BGE Small, BGE Base, and BGE Reranker directories from
  Wavefoundry's FastEmbed, clean-ONNX, static-ONNX, and compiled-CoreML caches.
  Tests prove path containment, exact allowlisting, idempotent reruns,
  the exact flat status/removed/absent/unowned/failed reporting contract, and no
  deletion of Snowflake, L6, unrelated cache
  entries, cache roots, or unmarked components beneath custom cache overrides.
  A symlink mutant proves cleanup never traverses an allowlisted component or
  custom-root symlink into an external referent: the referent remains intact,
  while the component link is either unlinked without following it or rejected
  actionably. Custom-root tests prove marker presence is insufficient; missing,
  malformed, stale, wrong-version, wrong-fingerprint, file-mismatched,
  unreferenced-blob, and other extra-file attestations classify the component as
  unowned and preserve it. Valid legacy online-cache fixtures prove recorded
  refs/snapshots plus only their transitively referenced blobs remain eligible.
  Immediately before mutation, cleanup re-lstats the
  root and component, revalidates containment and any ownership attestation,
  and uses a no-follow deletion path; a check/use substitution mutant that
  replaces the component with an external symlink preserves the referent and
  fails or safely unlinks only the link node.
  Dry-run, failed verification/publication, and pre-publication paths delete
  nothing; a required owned-target removal failure keeps upgrade completion
  explicit and actionable. On the first transition to new framework code,
  cleanup runs in the freshly loaded `--cleanup` process before dashboard
  restart and upgrade-lock removal. Tests mutation-kill reliance on only a
  subprocess success Boolean or `index_rebuilt_at`: cleanup reads the sole
  `index-state.sqlite` authority through `index_state_store`, requiring an
  identical complete token before and after a bounded summary whose content
  contains docs and code; its composite values identify the canonical active
  docs/code models at approved precision and both carry that model set's exact
  shared fingerprint suffix. For v2 both layers identify Arctic S. An
  upgrade-lock copy is audit-only. Cleanup refuses if a later
  detached build has opened an incomplete epoch. Failure
  returns nonzero, records a cleanup-specific failed phase, retains the upgrade
  lock, and preserves exact removed/absent/unowned/failed status. Eligibility
  uses semantic precedence of pack `to_version` with build metadata ignored,
  with tests for `1.15.9`, `1.16.0`, `1.16.0+build`, `1.16.1`, and
  unknown/malformed fail-closed inputs. The cleanup-eligible transition requires
  a synchronous foreground all-layer v2 receipt and suppresses the redundant
  detached Phase 4c pass. Cleanup also refuses if the installed canonical model
  manifest declares any allowlisted component active. A later-model-set fixture
  proves cleanup uses that set's canonical active identities rather than
  hard-coding the v2 fingerprint. A saturated-summary mutant fills existing
  reconciliation, permission, and envelope collections; all five cleanup keys
  and exact values still survive summary and whole-envelope bounding. The
  public upgrade dry-run path exposes the dry-run status and four empty lists.
  With only an unmanaged stale BAAI cache available, active resolution obtains
  Arctic S through the existing acquisition behavior or fails explicitly—never
  by fallback.
- [x] AC-9: `model_swap_code_queries.json` contains exactly 28 code queries and
  `model_swap_docs_queries.json` contains exactly 100 document queries, each
  with stable accepted answers. A backward-compatible `embed_bench.py` mode
  runs pinned candidate retrieval plus production L6 and writes
  `model_swap_v2_result.json` with per-query raw and reranked ranks, provenance,
  category metrics, and controlled timing. On code, Arctic S is no worse than
  Arctic XS at aggregate top-3, top-10, and MRR before reranking and top-5,
  top-10, and MRR after L6, and loses no required answer from top 40. On
  documents, the paired S-minus-XS 95% confidence interval includes zero at
  reranked top-3, top-5, top-10, top-20, top-40, and MRR; the point estimate is
  no worse than 2 percentage points at each hit-rate cutoff and no worse than
  0.02 MRR. S's recorded same-machine FP16 GPU indexing time for each corpus is
  within 2.0x XS. A focused CI test recomputes metrics, paired intervals, and
  ratios from the committed result and detects threshold/provenance/rank
  mutations without running model inference. The existing 32-query
  `retrieval_eval.json` remains byte-identical.
- [x] AC-10: Existing test helpers and fixtures are updated/parameterized for
  Arctic S and model set v2 wherever they already own the behavior; the existing
  32-query benchmark remains compatible and byte-identical. Directly affected
  model-selection, architecture, performance,
  setup, upgrade, decision, release, framework-version, and changelog surfaces
  agree on framework `1.16.0` and model set v2; the changelog contains the exact
  `1.16.0` release heading required by packaging, focused tests and package
  build verification pass, docs lint is clean, and the full framework suite
  passes.

## Tasks

- [x] Keep separate document and code model constants and set each to Arctic S;
  add its query-prefix, cache-alias, FP16, and INT8 mappings; verify equal-ID
  server/indexer caches reuse one instance across both layers; choose one
  build-level execution class before loading equal-ID layer embedders, including
  mixed small/bulk and both-small fixtures; and add a divergent-selector fixture
  proving future separation uses the same generic model-name-keyed path.
- [x] Change the embedding static forward batch from 64 to 32 while preserving
  the CPU batch 32 and reranker batch 40 contracts; correct the existing
  reranker success log to use `RERANK_STATIC_BATCH` and extend its current test.
- [x] Update the model-set manifest, compatibility fingerprint, bundle inputs,
  licenses, revisions, hashes, and manually reviewed supplier-origin record.
- [x] Advance `MODEL_SET_VERSION` to `2` and update setup, upgrade, package,
  version, and release tests/surfaces for `wavefoundry-models-2.zip`; require
  `--with-models` in release/release-dry-run mode and assert both release assets.
- [x] Add a stdlib-only, exact-path retired-model cleanup to the post-publication
  upgrade path for target releases `>=1.16.0`. Derive only the fixed BAAI BGE
  Small/Base/Reranker FastEmbed/Qdrant, clean-ONNX/Xenova, static-ONNX, and
  compiled-CoreML targets; require Wavefoundry ownership markers for custom
  cache roots and re-verify their recorded file inventory and hashes; validate
  containment without following symlinks before deletion; and report removed,
  absent, unowned, and failed targets. Re-lstat and revalidate immediately at
  the mutation boundary; never follow a component or cache-root symlink to its
  referent. Invoke cleanup from the freshly loaded `--cleanup` process, before
  dashboard restart and upgrade-lock removal, only after reopening a current
  `index-state.sqlite` all-layer v2 publication authority through
  `index_state_store`: identical complete token around a bounded docs-and-code
  summary, with both composite values identifying the installed canonical
  model set's active docs/code models at approved precision and carrying its
  exact shared fingerprint suffix (Arctic S for both layers in v2).
  Treat any upgrade-lock copy as audit-only. Do not authorize cleanup from only
  a subprocess Boolean or `index_rebuilt_at`; refuse when a later semantic epoch
  is incomplete. Require a synchronous foreground all-layer v2 receipt and
  suppress the redundant detached Phase 4c pass for this transition.
  On failure, set `failed_phase=retired_model_cleanup`, return nonzero, retain the
  lock, and persist the exact result projection. A later `--cleanup` retry SHALL
  recognize only this cleanup-specific failed phase, revalidate every authority
  and remaining target, resume idempotently, and clear the failure only after
  full success; other failed phases retain their existing recovery paths. Gate
  on pack
  `to_version >= 1.16.0` by semantic precedence with build metadata ignored;
  unknown or malformed versions fail closed. Require the immutable retired-v1
  version/fingerprint and exact legacy refs/snapshots inventory for a
  custom-root marker; allow only transitively referenced blobs outside that map,
  and
  refuse cleanup when the current canonical model manifest declares an
  allowlisted component active. Test a later model set against its own canonical
  identities so cleanup is not permanently hard-coded to v2. Reserve or bypass
  generic summary/envelope collection budgets for all five cleanup keys and add
  saturated competing-collection plus upgrade dry-run sentinel tests.
- [x] Bind offline materialization to the installed canonical verification
  manifest and extend the existing bundle tamper test with a self-consistent
  payload/revision/ref/hash substitution that must fail before publication.
- [x] Remove obsolete BAAI and Arctic XS runtime/default/acquisition/setup/package
  mappings rather than preserving dead compatibility branches. Apply the closed
  residue matrix: Arctic S-only current behavior and tests; legacy BAAI/XS only
  as exact v1 migration inputs; BAAI only in the exact cleanup allowlist; XS/S
  only in comparison evidence; accurate history unchanged; every other legacy
  occurrence fails. Verify retired Wavefoundry-owned cache targets are removed
  only after successful v2 convergence and unrelated or user-managed caches
  remain intact.
- [x] Add shared-fingerprint full-rebuild, atomic publication, no-mixed-vector,
  and subsequent unchanged-v2 incremental-update tests.
- [x] Add `model_swap_code_queries.json`, `model_swap_docs_queries.json`, and
  `model_swap_v2_result.json`; extend `embed_bench.py` backward-compatibly for
  the controlled release evaluation and focused deterministic CI result
  validation while preserving the existing `retrieval_eval.json` input and
  behavior.
- [x] Update existing accelerator, indexer, model-bundle, setup, upgrade,
  package, and benchmark tests in place; add a new fixture/test only where an
  existing owner cannot express the required behavior.
- [x] Update directly affected documentation and run focused/full verification.
  Update the public Package Wavefoundry Run, Output, and Options sections so
  release/release-dry-run require the matching v2 model asset without changing
  model-optional non-release local builds.

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
- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/model_bundle.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/VERSION`
- `.wavefoundry/framework/model-set-verification-manifest.json`
- `.wavefoundry/framework/scripts/benchmarks/model_swap_code_queries.json`
- `.wavefoundry/framework/scripts/benchmarks/model_swap_docs_queries.json`
- `.wavefoundry/framework/scripts/benchmarks/embed_bench.py`
- `.wavefoundry/framework/scripts/benchmarks/model_swap_v2_result.json`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/package-wavefoundry.prompt.md`
- `.wavefoundry/README.md`
- `README.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/contributing/build-and-verification.md`
- `docs/references/release-flow.md`
- `docs/references/wavefoundry-overview.md`
- `docs/references/model-selection.md`
- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/embedding-model.md`
- `docs/architecture/performance-budget.md`
- `docs/architecture/testing-architecture.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/chunking-and-indexing-pipeline.md`
- `docs/architecture/layering-rules.md`
- `docs/architecture/decisions/1p92d-adr embedding-precision-policy.md`
- `docs/specs/mcp-tool-surface.md`
- `CHANGELOG.md`

Model constants, artifact mappings, the compatibility fingerprint, and the
verification manifest SHALL change together before bundle or retrieval evidence
is accepted.

## Affected Architecture Docs

- `.wavefoundry/README.md` and `docs/references/wavefoundry-overview.md` — update
  current setup/model examples while retaining explicitly historical v1 facts.
- `docs/architecture/current-state.md` and
  `docs/architecture/data-and-control-flow.md` — update the current retrieval
  identities, model-set version, and upgrade cleanup boundary.
- `docs/architecture/embedding-model.md` — update the shared docs/code model,
  precision, batch, prefix, cache reuse, artifact, and re-index facts.
- `docs/architecture/search-architecture.md` and
  `docs/architecture/chunking-and-indexing-pipeline.md` — update current model,
  fingerprint, and indexing-flow facts.
- `docs/architecture/performance-budget.md` — distinguish embedding batch 32
  from reranker batch 40 and record the accepted Arctic S indexing cost.
- `docs/architecture/testing-architecture.md` — update current model fixtures,
  model-set-v2 verification, and cleanup safety coverage.
- `docs/architecture/layering-rules.md` — record the one-way
  `index_state_store` authority-to-upgrade-cleanup boundary without adding a
  second receipt authority.
- `docs/specs/mcp-tool-surface.md` — document the cleanup-specific failure and
  exact removed/absent/unowned/failed upgrade result projection.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` and
  `docs/prompts/upgrade-wavefoundry.prompt.md` — keep canonical and rendered
  cleanup recovery instructions synchronized.
- `docs/prompts/package-wavefoundry.prompt.md` — update the public Run, Output,
  and Options contract so release/release-dry-run require the matching model
  companion while non-release local builds remain model-optional.
- `docs/contributing/build-and-verification.md` and
  `docs/references/release-flow.md` — update current `1.16.0` companion-package
  and upgrade-recovery guidance without rewriting historical release facts.
- `docs/architecture/decisions/1p92d-adr embedding-precision-policy.md` — append
  the Arctic S and embedding-batch decision evidence without rewriting history.

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
| AC-9 | required | Expanded code and document evidence justifies one S embedder without a material quality loss. |
| AC-10 | important | Durable docs and full regression evidence keep the release coherent. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Created and admitted the planned supplier-lineage model-swap wave without taking the OPEN slot. | Wave `1v0r0`; change `1v0qz-enh`. |
| 2026-08-10 | Confirmed XS documents, S code, embedding FP16 GPU / INT8 CPU batch 32, and retained L6 FP16 GPU / INT8 CPU batch 40. | Operator confirmation and current runtime inspection. |
| 2026-08-10 | Compared Arctic XS and S on 28 queries over 6,895 code chunks with production L6 reranking. | Raw S top-3 89.29%, top-10 96.43%, MRR 0.8822 versus XS 85.71%, 92.86%, 0.8718. Reranked S top-5 89.29%, top-10 96.43%, MRR 0.8560 versus XS 85.71%, 96.43%, 0.8376. FP16 MPS batch-32 time: S 21.485s, XS 13.185s. AC-9 requires the durable committed fixture. |
| 2026-08-11 | Expanded the document bake-off and selected Arctic S as the single embedder for both semantic layers. | 100 queries over 23,410 document chunks, FP16 MPS batch 32 plus production L6 CoreML: reranked XS/S top-3 61%/60%, top-5 67%/67%, top-10 80%/80%, top-20 83%/83%, top-40 88%/87%, MRR 0.5185/0.5178; every paired 95% interval included zero. Raw S led at top-3, top-5, top-10, and MRR. S encoded at 350.51 chunks/s versus XS 581.73 and remained inside the 2.0x ceiling. Temporary fixture/result SHA-256: `63359684afa4ba0cd91aa5c51f109176223cedd1dd4485bf838e7e0bd7a411e5` / `83816d74603120503a85cd443dc04fdfe3e08ef091b074566e80be97fafe4cf4`; AC-9 requires their durable committed equivalents. |
| 2026-08-10 | The initial council exposed provenance, acquisition-path, validation, and fixture ambiguities; the operator then challenged the wave's complexity. | Red-team context `1v0r0-redteam-20260810-supplier-lineage-01`; docs-contract context `1v0r0-docs-contract-20260810-final-03`; plan narrowed to the direct model swap and manual supplier record. |
| 2026-08-10 | Removed automated jurisdiction validation and added model bundle v2 to the release scope. | Operator direction: supplier origin is reviewed manually at model-swap time; the new release must ship `wavefoundry-models-2.zip`. |
| 2026-08-11 | Simplified the v2 migration after the narrowed red-team review. | Context `1v0r0-redteam-20260811-modelswap-02`: accept one full semantic rebuild under the existing shared fingerprint, keep manual supplier evidence outside the generated manifest schema, and treat the measured timing ratio as controlled release evidence. |
| 2026-08-11 | Defined a dedicated deterministic 28-query input/result without replacing the existing mixed benchmark or evaluator. | QA context `1v0r0-qa-20260811-modelswap-final-05` plus operator direction to reuse tests: extend `embed_bench.py` backward-compatibly, add the dedicated input/result, and keep existing `retrieval_eval.json` byte-identical. |
| 2026-08-11 | Made the v2 model companion mandatory for release-mode packaging. | Release context `CTX-1v0r0-release-final-20260811-A7C4`: release/release-dry-run must reject missing `--with-models` and the release receipt must assert both the feature archive and `wavefoundry-models-2.zip`; local non-release builds stay optional. |
| 2026-08-11 | Added the bounded batch-log and canonical-bundle-binding repairs exposed by final lane review. | Code context `1v0r0-code-recheck-20260811-modelswap-final-06`: log `RERANK_STATIC_BATCH` and extend the existing success test. Security context `1v0r0-security-20260811-modelswap-final-06`: compare the incoming embedded verification manifest to the installed canonical authority before offline publication and mutation-test a self-consistently remanifested substitute. |
| 2026-08-11 | Locked the framework release version to `1.16.0`. | Operator approval; feature-archive name, VERSION stamp, release receipt, and changelog heading are now deterministic. |
| 2026-08-11 | Added bounded removal of retired BAAI-derived caches during upgrades to `1.16.0` or later. | Operator direction; cleanup is post-verification/post-publication, exact-path and ownership-gated, idempotent, auditable, and cannot delete unrelated or shared cache content. This load-bearing revision requires a fresh readiness receipt and affected-lane review. |
| 2026-08-11 | Bound cleanup to the freshly loaded upgrade process and durable all-layer publication authority. | Fresh QA, security, and release review required no-follow symlink handling, file-verified custom-root ownership, mutation-boundary revalidation, semantic `to_version` gating, a current v2 all-layer receipt/token, and lock-retaining nonzero failure before dashboard restart or lock removal. |
| 2026-08-11 | Repaired cleanup authority, retry, cache-root, and living-doc boundaries. | Fresh code, architecture, and red-team review selected synchronous all-layer v2 publication with Phase 4c suppression; bound authority solely to a stable `index-state.sqlite` epoch; made cleanup-specific failures idempotently retryable; bound custom ownership to an exact retired-v1 marker location, fingerprint, and inventory; added default-plus-distinct-override cache census and current-manifest reactivation refusal; and enumerated every living current-state surface found by census. |
| 2026-08-11 | Defined the public cleanup result and recovery contract. | Fresh docs-contract review named `retired_model_cleanup`, five flat bounded response/lock/status fields, stable path-free target IDs and reason codes, deterministic ordering, exact retry diagnostic/recovery, and the canonical/rendered upgrade plus release-guidance owners. |
| 2026-08-11 | Preserved separate document/code configuration without retaining a split-model implementation. | Operator direction: both v2 selectors independently name Arctic S and share the model-name-keyed instance when equal; obsolete BAAI/XS runtime, acquisition, setup, and packaging branches are removed, with only cleanup/comparison/test/history references retained for their stated purposes. |
| 2026-08-11 | Repaired the single-instance and legacy-residue boundaries exposed by fresh Council seats. | Red-team context `1v0r0-redteam-fresh-20260811-single-s-cacheclass-01`: equal-ID layers now choose one build-level execution class, including the mixed small/bulk threshold. Docs-contract context `1v0r0-docs-contract-fresh-20260811-1b03c65efcb372f5c2cb-01`: one closed residue matrix distinguishes current tests, exact v1 migration inputs, cleanup identifiers, comparison evidence, and history; `index_state_store.py` is an explicit review target. |
| 2026-08-11 | Added the missing public package-command owner. | Code readiness context `1v0r0-code-readiness-single-s-final-20260811-0b21e0fb623445858305-04` found `docs/prompts/package-wavefoundry.prompt.md` still describes the release model companion as optional; it is now an explicit review target and must distinguish mandatory release modes from model-optional local builds. |
| 2026-08-11 | Thought: implement in dependency order—runtime/model identity first, equal-ID orchestration second, bundle/release/setup third, fresh-process cleanup fourth, benchmark evidence fifth, then living docs and full verification. | Current receipt `review-policy-915d860b9f84196061d1` is approved across Council and every required readiness lane; `wf_implement_wave` transitioned the wave to implementing. |
| 2026-08-11 | Implemented the single-Arctic-S v2 retrieval model set, safe 1.16 upgrade cleanup, release pairing, deterministic benchmark evidence, and current documentation; all ACs and tasks are complete and the change is ready for independent delivery review. | Initial implementation evidence: 7,147/7,147 tests across 62 files; docs-lint clean; deterministic benchmark validator `ok: true` for 28 code and 100 document queries; actual v2 companion and 1.16.0 feature packs verified under `/private/tmp/wf-v2-pack-verify/`. The attached native CoreML/Espresso crash remained open for delivery review and production-path containment. |
| 2026-08-11 | Folded independent delivery findings, contained the native CoreML failures, and simplified the dashboard model label. | Final canonical suite: 7,157/7,157 tests across 62 files in 296.665s; docs-lint and `git diff --check` clean; benchmark validator `ok: true`. Isolated production children reproduced `SIGSEGV` for Arctic S and L6 while the parent survived, cached both CoreML paths as unsafe, and selected CPU/fallback without constructing a parent CoreML session. Cleanup now uses strict ASCII SemVer and file-descriptor-anchored deletion; mixed model-set epochs, public cleanup leakage, release-pairing, and stale batch-contract defects are regression-covered. The dashboard displays the model ID only through the first `@` and retains full provenance on hover. Rebuilt feature archive `/private/tmp/wf-v2-pack-verify/wavefoundry-1.16.0.pieo.zip` (`22a85666…`) is byte-identical to all 80 shipped repaired files; the v2 companion (`4ba7f0c1…`) retains identical canonical manifest content and all 15 payload hashes. Delivery PASS contexts: code/architecture `delivery-1v0r0-postpass-20260811-54ce7d30`; security/release/docs `1v0r0-delivery-security-release-docs-final-20260811-05`; QA `1v0r0-delivery-qa-20260811T200421Z-c7c7ee9-9b37a9dd`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | Replace BAAI with Arctic S for code and retain Arctic XS for documents. | S had a small consistent code-quality advantage; XS remains the proven document choice. | XS for both: faster but weaker on code. Granite: CPU cost was not viable. Keep BAAI: fails supplier origin. |
| 2026-08-10 | Retain the current L6 logical model and Xenova artifacts on CPU and GPU. | L6 already meets the accepted supplier requirement and the L2 test lost quality. | L2: faster but lower quality. Official-artifact migration: unrelated risk. |
| 2026-08-11 | Supersede the XS-docs/S-code split with Arctic S for both layers. | The expanded 100-query document test found no statistically distinguishable reranked loss, raw S was stronger at the practical top-3/5/10 cutoffs, and existing model-name-keyed caches can reuse one S instance across both layers. | Retain XS for docs: slightly faster indexing but keeps a second resident/downloaded embedding model without measured quality benefit. Use XS for both: weaker on the 28-query code set. |
| 2026-08-11 | Retain L6 in this model-swap wave even though the focused raw S results did not need it for ranking accuracy. | L6 currently owns `code_ask`'s unified relevance scale, weak-match abstention, cross-source drop-off, and high-confidence calibration. Removing it is a public retrieval-contract redesign that needs the broader `1seaw` golden-query proof, not an incidental extension of the supplier model swap. | Remove L6 now: lower memory and latency, but silently degrades/confounds confidence and candidate-selection semantics without adequate cross-intent evidence. |
| 2026-08-10 | Use embedding batch 32 on CPU and GPU; keep reranker batch 40. | Embedding batch 32 is the approved cross-device setting; reranking has a separately tested optimum. | Keep GPU embedding batch 64 or couple reranking to 32: contrary to the measured contracts. |
| 2026-08-10 | Record supplier lineage as a manual model-swap decision, not runtime jurisdiction validation. | Supplier selection is infrequent and reviewed with each swap; runtime legal-policy machinery is disproportionate. | Automated jurisdiction engine: unnecessary complexity. Omit provenance: loses the reason for the swap. |
| 2026-08-10 | Publish the changed packaged model set as v2 with framework `1.16.0`. | The code model, bundle contents, hashes, compatibility fingerprint, VERSION stamp, and changelog key change together and must not masquerade as v1. | Overwrite v1: breaks immutable model-set identity. Delay packaging: leaves offline installs on BAAI. |
| 2026-08-11 | Use the existing shared model-set fingerprint and perform a one-time full semantic rebuild for v2. | This is safer and simpler than adding per-layer fingerprint semantics solely to avoid rebuilding unchanged docs. | Per-layer fingerprints: broader architecture change. Code-only rebuild under the shared fingerprint: contradicts current behavior. |
| 2026-08-11 | Keep manual supplier evidence in the model-selection decision record, separate from the generated verification manifest. | The manifest is deterministically generated from cached artifacts and compared exactly during bundle creation. | Add hand-authored fields only to canonical JSON: breaks bundle equality. Expand the generator schema: unnecessary for manual review. |
| 2026-08-11 | Reuse and extend the existing benchmark/test owners for the model swap. | Most behavior already has accelerator, indexer, bundle, setup, upgrade, package, and benchmark fixtures; model-ID changes should update those expectations rather than fork coverage. | Parallel replacement suite: duplicate ownership and drift. Replace `retrieval_eval.json`: loses existing coverage. |
| 2026-08-11 | Require the model companion in release and release-dry-run modes. | Manual recovery expects the companion on the same release, and a feature-only release would leave offline users on model set v1. | Keep `--with-models` optional for releases: permits an incomplete v2 release. Require it for every local build: unnecessary. |
| 2026-08-11 | Bind offline bundle consumption to the installed canonical verification manifest. | Self-consistent embedded hashes prove internal consistency, not that the bytes are the reviewed v2 artifacts. | Trust the incoming manifest alone: permits re-manifested substitutions. Add signature infrastructure: broader than the existing canonical-manifest trust model. |
| 2026-08-11 | Remove retired BAAI-derived artifacts from Wavefoundry-owned caches after successful v2 convergence while preserving historical records. | Supplier-lineage cleanup should remove obsolete local weights, but only after the replacement model set and semantic epoch are durable. | Preserve every old cache: leaves retired BAAI weights behind. Delete before publication or purge whole/shared caches: unsafe and unnecessary. |
| 2026-08-11 | Keep document and code model selectors independent while assigning Arctic S to both. | This keeps future reviewed divergence straightforward without paying the runtime, package, or maintenance cost of two active model implementations today. | Collapse to one selector: makes a future split invasive. Keep obsolete split-model mappings: leaves dead code and ambiguous fallbacks. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A future model swap overlooks supplier origin. | Keep supplier decision, reviewer, date, and evidence in the model-selection and verification records and require the same manual review in future model-swap plans. |
| A new release still selects model bundle v1. | Version the model set and fingerprint as v2 and test setup, upgrade, package contents, recovery guidance, and v1-to-v2 transition. |
| A self-consistently re-manifested bundle substitutes unreviewed model bytes. | Require incoming/canonical manifest equality before materialization and mutation-test changed payload, revision/ref, and hashes together. |
| Arctic S artifact mappings must serve both semantic layers. | Pin and test Snowflake's exact FP16/INT8 paths, revisions, hashes, tokenizer, prefix, and one-instance cache reuse for both docs and code. |
| Simplification accidentally removes the ability to configure different models later. | Retain two explicit selectors, keep provider/cache resolution keyed generically by model ID, and test both equal-ID reuse and divergent-ID resolution. |
| Equal model IDs still allocate two instances when docs/code cross the small-run/bulk threshold. | Preselect one build-level execution class: bulk/full if either participating layer requires it, otherwise small-run CPU; load once and share, while divergent IDs remain independent. |
| Retired mappings survive as unreachable dead code and later become an accidental fallback. | Census active source and canonical data; permit legacy IDs only in exact cleanup, focused comparison/migration tests, and accurate historical records. |
| A stale BAAI cache wins resolution. | Test S-plus-BAAI and BAAI-only cache states; active resolution must select/acquire S or fail explicitly. |
| Cleanup deletes user-managed or still-needed model data. | Use fixed retired-model IDs and exact directory names, validate containment under Wavefoundry roots without following symlinks, require an immutable-v1-fingerprint marker with exact legacy refs/snapshots inventory and only transitively referenced blobs beneath custom roots, refuse any component active in the current canonical manifest, and mutation-test sibling/cache-root, forged-marker, stale-marker, unreferenced-blob/extra-file, future-reactivation, and external-symlink targets. |
| Cleanup removes the recovery path before v2 is usable. | In the freshly loaded cleanup process, reopen a current all-layer v2 receipt/token and run before restart/lock removal; do not trust only `index_rebuilt_at` or subprocess success, refuse a later incomplete epoch, and retain the lock with a cleanup-specific failed phase on failure. |
| The v2 swap leaves mixed vectors. | Use the existing shared fingerprint to force a complete atomic docs+code rebuild before v2 publication. |
| Arctic S indexing is too slow on developer hardware. | Use batch 32, test CPU/GPU paths, and enforce the same-machine 2.0x relative ceiling. |
| The focused query set overfits the current repository. | Commit query intent and accepted-answer rationale; leave the broader golden suite to `1seaw`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
