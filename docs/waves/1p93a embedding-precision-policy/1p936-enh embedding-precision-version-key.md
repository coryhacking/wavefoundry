# Fold embedding precision class into `model_versions` (re-embed guard)

Change ID: `1p936-enh embedding-precision-version-key`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-30
Wave: `1p93a embedding-precision-policy`

## Rationale

Once change `1p935` lets a layer be embedded at **INT8** (CPU-bound) or **full precision** (FP16/FP32, GPU/CPU-resident), the index must record *which* so that (a) moving a layer across precision **classes** forces a re-embed, and (b) the query embedder picks the precision matching the stored index. Today `model_versions` keys on the **model name only** (`indexer.py:2435`/`2445` compare `old_model_versions.get("docs") != DOCS_MODEL`), which is correct for FP16↔FP32 (cos 1.0, interchangeable — `1p517` AC-8) but **invisible to INT8**: an INT8 index silently queried by full-precision vectors (or vice versa) would degrade without ever forcing a rebuild.

Crucially the key tracks the precision **class**, not the exact format: **FP16 and FP32 collapse to `full`** (they're cos 1.0 — a GPU machine's FP16 index and its FP32-resident CPU queries must *not* look like a precision change), and only **INT8** is a distinct class. This preserves the `1p517` interchangeability invariant for full-precision provider swaps while catching the one transition that actually shifts vectors.

## Requirements

1. **Write the precision class** into each layer's `model_versions` value at the write site (`indexer.py:3000-3004`): e.g. `new_model_versions["docs"] = f"{DOCS_MODEL}@{precision_class}"` where `precision_class ∈ {"full", "int8"}` (FP16/FP32 → `full`; INT8 → `int8`).
2. **Match the scheme at the compare sites** (`indexer.py:2435`/`2445`) so a precision-class change sets `model_changed` and forces a full re-embed of that layer; a same-class change (FP16↔FP32 provider swap) does not.
3. **Determine the active precision class** from the resolved embedder (the `make_embedder` result / dispatch in `1p935`) before embedding starts, so the comparison and write use the run's actual precision.
4. **Query embedder selects precision from the index's recorded value.** `server_impl`'s query path reads `model_versions` (precision class) and constructs the matching embedder (INT8 vs full) — so query↔index precision agree even if the host machine's classification differs from when the index was built.

## Scope

**Problem statement:** `model_versions` can't distinguish an INT8 index from a full-precision one, so a precision-class change neither forces a re-embed nor steers the query embedder.

**In scope:**

- `indexer.py`: precision-class suffix at the `model_versions` compare (`:2435`/`:2445`) and write (`:3002`/`:3004`) sites; derive the active class from the dispatch.
- `server_impl.py`: query embedder reads the recorded precision class to pick its embedder.
- `tests/test_indexer.py`: re-embed-on-class-change and no-re-embed-on-same-class (FP16↔FP32) coverage.

**Out of scope:**

- The INT8-CPU embedder itself (`1p935`).
- Migration of existing indexes — a pre-this-change index has a bare `model_name` value; treat a missing `@class` suffix as `full` (no spurious rebuild for existing full-precision indexes).

## Acceptance Criteria

- [x] AC-1: switching a layer's precision class (`full` ↔ `int8`) forces a **full re-embed** of that layer on the next build. Evidence: `indexer.py` compare site (`_precision_class_from_version(old) != _predicted_precision_class(...)` → `model_changed`); `test_precision_class_change_forces_reembed` (`PrecisionClassVersionTests`).
- [x] AC-2: a same-class provider/format swap (FP16 GPU ↔ FP32 CPU-resident, both `full`) does **not** force a re-embed — the `1p517` interchangeability invariant is preserved. Evidence: FP16/FP32 collapse to `full` in `_predicted_precision_class`; `test_same_precision_class_no_reembed`.
- [x] AC-3: the recorded `model_versions["docs"]`/`["code"]` value carries the precision class (visible in `meta.json`); a legacy bare-name value is treated as `full`. Evidence: write site records `f"{MODEL}@{class}"`; `_precision_class_from_version` maps a bare name → `full`; `test_precision_class_from_version_*`, `test_legacy_bare_name_index_not_rebuilt_when_full`.
- [x] AC-4: the query embedder's precision is derived from the index's recorded class (INT8 index → INT8 query embedder). Evidence: `server_impl._get_embedder` reads `model_versions`; `test_get_embedder_uses_int8_when_index_recorded_int8`, `..._uses_fastembed_when_index_recorded_full`, `..._int8_build_failure_falls_back_to_fastembed` (`test_server_tools.py`).
- [x] AC-5: full framework suite + docs-lint green; tests cover AC-1/AC-2. Evidence: 3,755 tests OK; docs-lint clean.

## Tasks

- [x] Add the precision-class suffix scheme + a helper (`framework_edit_allowed`). Done: `indexer._precision_class_from_version` (parse) + `_predicted_precision_class` (the single predictor both compare and write use). **Design note (implementation):** the write site records the PREDICTED class, not a resolved-embedder class — both sides call `_predicted_precision_class`, so they are consistent by construction (a resolved-embedder-vs-prediction split caused a perpetual-rebuild bug in the first cut; fixed).
- [x] Apply it at the `model_versions` compare + write sites; treat missing suffix as `full`. Done: `indexer.py:build_index` compare (`:2507`/`:2517` region) + write (`new_model_versions` region).
- [x] Wire the query embedder (`server_impl`) to read the recorded class and select its precision. Done: `server_impl.WaveIndex._get_embedder`.
- [x] Add re-embed/no-re-embed tests; run suite + docs-lint. Done: `PrecisionClassVersionTests` (8) + query-side tests (3); 3,755 tests OK.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| precision-class version scheme | implementer | — | `indexer.py` compare + write sites |
| query-side precision selection | implementer | version scheme | `server_impl.py` reads `model_versions` |
| tests | qa-reviewer | both | re-embed-on-change / no-re-embed-same-class |

## Serialization Points

- `model_versions` value format — the compare and write sites must use the identical scheme; a mismatch forces perpetual rebuilds.
- Depends on `1p935` (no INT8 enters the stored path without it); this change is the guard that makes `1p935` safe.

## Affected Architecture Docs

`docs/architecture/embedding-model.md` — note the precision-class component of `model_versions` and the full↔int8 re-embed rule. ADR `1p92d` already records the decision.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Without it, a precision change silently mixes vectors. |
| AC-2 | required | Must not break the full-precision interchangeability invariant. |
| AC-3 | required | The recorded class is what the guard + query path read. |
| AC-4 | required | Query must match index precision. |
| AC-5 | required | No regressions. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-30 | Drafted from ADR `1p92d` + the `model_versions` write/compare map. | `1p92d-adr`; `indexer.py:2435/2445/3000-3004`. |
| 2026-06-30 | Implemented; caught + fixed a perpetual-rebuild divergence during test bring-up (see Decision Log). AC-1..5 met. | `indexer.py`, `server_impl.py` diffs; `PrecisionClassVersionTests` (8) + 3 query-side tests; 3,755 tests OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-30 | Track precision **class** (`full` vs `int8`), collapsing FP16/FP32 into `full`. | FP16↔FP32 are cos 1.0 (interchangeable); only INT8 shifts vectors. Avoids spurious re-embeds on provider swaps. | Track exact format (fp16/fp32/int8) — rejected: would force needless rebuilds when a GPU FP16 index is queried by FP32-resident CPU. |
| 2026-06-30 | Missing `@class` suffix = `full`. | Existing indexes are full-precision; avoids a spurious rebuild on upgrade. | Force a rebuild on first run post-change (rejected — unnecessary churn). |
| 2026-06-30 | **Both the compare AND the write site derive the class from `_predicted_precision_class` (provider availability), NOT from the resolved embedder instance.** | The first cut used a resolved-embedder class at the write site and a prediction at the compare site; whenever resolution fell back (offline, cache-miss, a mock in tests, or a non-offloading GPU) the two disagreed → every incremental build saw a class mismatch it had just written → **perpetual re-embed**. A single predictor makes the two sites consistent by construction; `make_embedder` is aligned to resolve exactly what the predictor reports, so the recorded class stays truthful about the stored vectors. | Resolve the embedder at the compare site to get the true class (rejected — regresses the 1p5d6/1p938 lazy-load: forces a ~40s CoreML compile on every no-op incremental pass). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Scheme mismatch between compare and write → perpetual rebuilds. | Single shared formatter; AC-2 asserts no-op on same-class. |
| Legacy index spuriously rebuilds on upgrade. | Treat missing suffix as `full` (AC-3). |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
