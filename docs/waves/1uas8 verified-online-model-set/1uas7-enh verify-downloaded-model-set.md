# Verify Downloaded Model Set

Change ID: `1uas7-enh verify-downloaded-model-set`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-03
Wave: `1uas8 verified-online-model-set`

## Rationale

Normal Hugging Face acquisition can produce the same model bytes as the
offline companion, but it has no release-pinned marker and is therefore
reported as unmanaged. The standard feature package should carry enough
verification metadata to attest an exact downloaded cache without bundling
the model bytes.

## Requirements

1. The standard feature package carries a release-pinned, model-set verification
   manifest containing the declared version, compatibility fingerprint,
   approved components, revisions, file hashes, provenance, and license
   metadata, but no model bytes.
2. After normal online model warm completes, setup validates the local cache
   against that manifest. Only a complete match receives the same
   `.wavefoundry-model-bundle.json` v1 marker written by offline bundle
   materialization.
3. A missing, incomplete, altered, mixed, or incompatible cache remains
   unmanaged (or its existing non-current state); setup must never mint a
   release marker from model name or revision alone.
4. The existing offline `wavefoundry-models-<set>.zip` validation,
   materialization, atomic rollback, no-downgrade, and feature-package
   selection behavior remain unchanged.
5. The 1.15.1 package/release documentation explains that verified online and
   offline acquisition converge on the same model-set identity.

## Scope

**Problem statement:** An online-downloaded cache cannot currently be
recognized as the release-pinned model set, despite potentially matching it
byte-for-byte.

**In scope:**

- Generate and package the small model-set verification manifest with every
  feature package that declares a model set.
- Validate and adopt a fully matching online-warmed cache without copying model
  bytes or changing cache locations.
- Add hermetic positive and negative tests for manifest packaging, adoption,
  mismatch refusal, and unchanged offline behavior.
- Update README, changelog, package/upgrade guidance, and the relevant
  architecture/testing contracts for 1.15.1.

**Out of scope:**

- Model downloads, remote release lookup, credentials, or a new downloader.
- Bundling model bytes in the standard feature ZIP.
- Relaxing any existing hash, revision, provenance, license, cache-publication,
  or model-set selection validation.
- Treating a matching model name or revision as sufficient proof.

## Acceptance Criteria

- [x] AC-1: A standard feature package contains a compact verification manifest
  for its declared model set and contains no model payload.
- [x] AC-2: A normal online-warmed cache whose full files and revisions match
  the manifest is marked v1 and `local_model_set_status()` reports `current`.
- [x] AC-3: Missing, extra, altered, wrong-revision, or partial caches do not
  receive the marker and remain non-current.
- [x] AC-4: The offline companion materialization behavior and the normal
  online warm/download behavior remain unchanged.
- [~] AC-5: 1.15.1 operator documentation explains identity convergence and
  remains consistent with the actual validation boundary. *(Intentionally deferred: release documentation and changelog belong to the separate 1.15.1 release-preparation step; this wave delivers and verifies the runtime/package contract without publishing a release.)*

## Tasks

- [x] Define a generated, source-controlled model-set verification manifest and
  include it in the standard feature package.
- [x] Add cache verification/adoption after the successful normal model warm,
  preserving the offline materialization path.
- [x] Add hermetic positive and negative tests, including a no-marker-on-
  mismatch control.
- [~] Update release and architecture/test documentation, then run docs lint,
  focused tests, and the canonical suite. *(Intentionally deferred: 1.15.1 release documentation and final archive build run after this implementation wave; focused model-bundle, package, setup-order, compile, and docs-lint checks passed.)*

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Manifest and cache attestation | framework-engineer | — | Preserve model-bundle verifier as the authority. |
| Packaging and regression tests | framework-engineer | Manifest and cache attestation | Test both standard and companion packages. |
| Release documentation | docs-contract-reviewer | Verified behavior | State the equivalence boundary precisely. |


## Serialization Points

- Define the manifest schema once, then reuse it for offline bundle validation
  and online-cache attestation so the two paths cannot drift.

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` and
`docs/architecture/testing-architecture.md` — the model identity and
verification boundary changes for both acquisition paths.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Standard packages must have the attestation data without model bytes. |
| AC-2 | required | This is the requested online/offline identity convergence. |
| AC-3 | required | A false v1 marker would undermine release-pinned verification. |
| AC-4 | required | Existing acquisition and offline safety contracts cannot regress. |
| AC-5 | important | Operators need an accurate 1.15.1 explanation. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-03 | Planned from the operator request to recognize a verified Hugging Face cache as the same release-pinned model set as the matching offline companion. | Existing `model_bundle` hashes/revisions and materialization marker are the authority. |
| 2026-08-03 | Implemented canonical manifest packaging and post-warm online cache attestation. | The standard feature ZIP carries the checked-in manifest without model payload; full file/revision verification writes v1 markers only after complete validation. |
| 2026-08-03 | Gapfill: semantic code retrieval was unavailable while the index was not ready, so targeted shell reads were used to inspect the package and model-bundle seams. | `code_ask` returned `index_not_ready`; the fallback reads were bounded to `build_pack.py`, `model_bundle.py`, `setup_index.py`, and their tests. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-03 | Carry verification metadata in the standard package, not model bytes. | It enables safe local cache attestation while retaining the small package and the optional offline companion. | Add a marker after download without validation; rejected because identity would be unverifiable. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Manifest and cache file maps could drift between online and offline paths. | One shared schema and mutation-focused mismatch tests. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
