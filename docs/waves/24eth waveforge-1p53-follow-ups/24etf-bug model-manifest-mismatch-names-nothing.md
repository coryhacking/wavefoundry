# The model companion build error does not name the mismatched component or file

Spec ID: `24etf-bug model-manifest-mismatch-names-nothing`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-26
Wave: 24eth waveforge-1p53-follow-ups

## Rationale

Waveforge reported, on v1.53.0, that building the model companion from a local cache failed on one missing file (the reranker's `onnx/model.onnx`) with only "warmed model cache does not match the canonical verification manifest". They had to diagnose which file was wrong before repairing the cache from a verified companion.

`model_bundle.build_bundle` (`.wavefoundry/framework/scripts/model_bundle.py:280`) builds a manifest from the cache with `_manifest_from_cache` and compares it with the checked-in canonical manifest as two whole dictionaries (line 289). On any difference it raises that one message (line 290). Both manifests are in hand at that point, so the difference can be named at no extra cost. It is the only site of the message, called from `build_pack.py:1819` when packaging with models. (executed: search and read.)

## Product Intent

A maintainer or distribution building a model companion from a warmed cache learns from the error which component and which file differ, and how, so the next step is a targeted repair rather than a diagnosis. Before: one generic sentence. After: the same sentence followed by a bounded list such as `reranker-clean-onnx: models/.../onnx/model.onnx missing from the cache`. AC-1 tests this. The build still refuses exactly the caches it refuses today.

## Requirements

1. When the built and canonical manifests differ, the error keeps today's first sentence and adds each difference, grouped by component id, naming the manifest-relative file path (the `models/<target>/<directory>/<relative>` form already in the manifest) and the kind of difference: missing from the cache, not in the canonical manifest, or content digest differs. A difference in component metadata (for example the revision) or in a top-level field names that field. When the manifests differ but no file, field or component difference is found (for example only the order of entries), the error says the manifests differ only in order.
2. The list is bounded: at most 20 differences are named, followed by the count of the rest. The message names no absolute path and no digest value.
3. Equal manifests build exactly as today. Every cache that is refused today is still refused, and none that builds today is refused.
4. Behaviour is identical on Windows, macOS, Linux and WSL2: manifest paths are already POSIX-form.

## Scope

**Problem statement:** a manifest mismatch is reported without saying what differs.

**In scope:**

- A difference summary in `model_bundle.py` used by `build_bundle`.
- Tests in `test_model_bundle.py`.

**Out of scope:**

- Repairing the cache automatically.
- Other model verification messages (`materialize_source`, attestation).

## Acceptance Criteria

- [x] AC-1: Deleting one reranker file from a test cache makes `build_bundle` raise an error naming that component id, that file's manifest path and "missing from the cache"; with the summary removed, the test fails. Oracle: `assertRaisesRegex` in `test_model_bundle.py`.
- [x] AC-2: A changed file is named as "content digest differs", an extra file as "not in the canonical manifest", and a changed revision names the field. The existing drift test still passes.
- [x] AC-3: Reordering two file entries in the canonical manifest fixture yields the order-only message. With 25 files removed, exactly 20 are named followed by "and 5 more", and the message holds no absolute cache path and no digest.
- [x] AC-4: The change's own suites and every test it adds pass.

## Tasks

- [x] Add a bounded manifest-difference summary and use it in `build_bundle`.
- [x] Tests for AC-1 to AC-3.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| summary | implementer | — | AC-1 to AC-4 |

## Serialization Points

- `.wavefoundry/framework/scripts/model_bundle.py`
- `.wavefoundry/framework/scripts/tests/test_model_bundle.py`

## Affected Architecture Docs

N/A: an error message inside one packaging function; no boundary or flow change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Naming the reported case is the fix. |
| AC-2 | required | Every difference kind is named correctly. |
| AC-3 | important | Bounded and free of local paths. |
| AC-4 | required | Change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-26 | Planned from the Waveforge v1.53.0 report, finding 4. | Reads cited in Rationale. |
| 2026-11-26 | Readiness notes applied: real component id `reranker-clean-onnx` in the example, wording aligned with AC-1, order-only fallback added. | Red-team readiness report N7. |
| 2026-11-26 | Readback: keep the existing cache equality check in model_bundle.py, then describe mismatches from the two in-memory manifests. A missing reranker weight will identify the component and manifest-relative path. Tests in test_model_bundle.py cover the diagnostic kinds, ordering and output cap. | AC-1 through AC-4. |
| 2026-11-26 | The builder retains the original manifest equality check and describes differences only after refusing a build. The missing reranker test and the three new mismatch controls failed against the old generic message. All 37 model bundle tests passed after the repair. | test_model_bundle.py covers missing and extra files, changed digest, revision and top-level fields, list order, and exactly 20 of 25 differences. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-26 | Name the differences in the existing error, bounded. Planner default; the operator asked for a single wave covering the DO items. | Replaying the Waveforge case: the error would have named the reranker's `onnx/model.onnx` as missing, removing the diagnosis step. No new mechanism; both manifests already exist at the raise. | (B) Log the full diff to a file and point at it: an extra artifact for a message that fits in a few lines. (C) Repair the cache automatically from a companion: hides a corrupted cache and needs a verified source the build may not have. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A structural difference (a missing component entry) has no file to name. | Requirement 1 names the component or field instead; AC-2 covers metadata. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
