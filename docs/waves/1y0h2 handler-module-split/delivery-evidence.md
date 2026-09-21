# Handler split delivery evidence

Owner: Engineering
Status: active
Last verified: 2026-09-20

## Reviewed boundary

Wave `1y0h2`, change `1y0bf-ref`. Baseline commit `aadab429`.
Frozen aggregate fingerprint: `deb126f99a76186ff1cfa8e9e59c802291c97741a73b4fb65ffd16c1bb80fd9e`.

The 77 moved definitions match the baseline AST after normalizing only function-local server_impl imports and qualifications. All 19 registration closures and the golden tool fixture remain unchanged. The evaluator gains only codenav production identity membership and the single moved lexical symbol anchor.

## Executed checks

- Graph-stage retrieval corpus: 1,312 tests; sole failure was a source-location assertion, repointed and passed.
- Combined extraction corpus plus registry: 1,337 tests; sole remaining source-location assertion repointed without changing its expected count.
- Final focused check: 37 tests passed, covering the repaired assertion, registry and all nine new handler guards.
- Independent architecture/QA context: 36 handler/registry tests passed, no skips, 13.790 seconds. The definition-equivalence proof is attributed to the code lane below.
- Independent code lane: nine handler tests plus five graph/digest tests passed with no skips. All 19 real response calls matched the pre-move source on an identical temporary source/SQLite graph fixture; only timing/accounting envelope fields were excluded.
- Full docs validation passed without errors or warnings.

## Independent mutation controls

| Mutation | Oracle | Result |
| --- | --- | --- |
| Unrestricted walker | Ignored-file response assertions | Killed |
| Missing retained-walker qualification | Successful listing assertion | Killed |
| Captured walker | Invocation-time patch assertion | Killed |
| Missing codenav production membership | Changed-file identity digest | Killed |
| Missing graph purge membership | Scratch native reload and registered callable | Killed |
| Undefined global or retained attribute | Name-resolution guard | Killed |
| Missing evaluator aliases | Real-server attribute census | Killed |
| Stale symbol or content anchor path | Corpus anchor resolver | Killed |

No mutations touched live production files. Scratch packaging and reload tests used copied framework trees. Empty-index smoke calls supplement the standing indexed graph tests; they do not claim full graph branch coverage.

## Runtime observation

The operator supplied a CoreML native crash report for PID 58427. The graph-stage log identifies that exact PID as an isolated reranker probe exiting with signal 11. Its parent reported CPU fallback and completed the test run. This is not evidence that CoreML acceleration works on the host. No acceleration source or configuration changed in this wave.

## Initial delivery receipts (superseded by pre-close refresh)

Full framework suite passed: **9,418 tests / 114 files / 12 skips**, 282.315 seconds. Receipt input hash: `a21bdbafd26e3b9c84fc447799a65194c87cd3ad1c9411433e46375b32fc58a4`.

The first full-suite pass exposed two source-owner censuses outside the initially named retrieval corpus. Repair cycle 3 included both handler files in the constructor/fresh-parse checks and exact advisory-diagnostic census without changing their expected sets. Independent reverification passed three focused tests and killed six mutations, including count-preserving advisory relocation. Code approval was restored; architecture approval remained current. Repaired freeze: `bfbf8898cc09153a6b80bbd59ebbc875ab0baabef37054be4f1c47e5283808ad`.

The standing evaluation ran once and returned **baseline**, with no invalidation or operator-review reasons. Report: `docs/reports/retrieval-quality-1y0bf-post-move.json`. Generation 1762 and its completed attempt token remained unchanged; production digest was verified again at exit. Before execution, the index contained 125 codenav chunks and 102 graph-handler chunks, with both file hashes matching disk. Warm p95: code_ask 3896.36 ms, code_lexical 41.72 ms, code_search 616.69 ms, docs_search 522.41 ms. Largest envelope: 25,065 bytes. No before/after metric deltas are claimed: the admitted plan deliberately restarts the comparison chain. See `verification-summary.json` for hashes and exact receipt fields.

The initial sandbox build used CPU INT8 after CoreML initialization failed. Its first attempt rejected a concurrent test edit and restored the previous completed snapshot; a stable retry completed. The existing host MCP monitor subsequently rebuilt with its full-precision CoreML provider. Evaluation ran in that host environment against the completed generation, with the CPU cross-encoder fallback after an isolated CoreML reranker probe failed. No provider settings or acceleration code were changed.

Memory curation rejected six generated candidates as duplicate or incorrectly targeted; the final proposal pass produced zero new candidates. Accepted decisions remain in the architecture documents and admitted change.

Final QA approval independently recomputed the framework input hash, report SHA-256, report run ID and current production digest; all matched. All fourteen repaired-freeze file hashes remained unchanged. Code, QA and architecture delivery approvals are current. Architecture and QA share one independent reviewer context; neither reviewer authored implementation or tests. The full-suite and standing evaluation artifacts were verified rather than rerun by QA.

## Reproducing review fingerprints

The original and cycle-3 fingerprints describe historical review snapshots, not the final cleanup tree. Their complete ordered path-to-Git-blob-hash maps are preserved in `delivery-freeze.json` and `delivery-repair-freeze.json`; `delivery-final-freeze.json` describes the cleanup tree. Each aggregate is SHA-256 over Python `json.dumps(mapping, sort_keys=True)` with default separators, UTF-8 encoded, excluding the `tree_fingerprint` field. Each per-file value is the Git blob SHA-1 (header `blob <byte-length>\0` followed by the raw bytes), not a raw-file SHA-1. Run from the repository root:

```python
import hashlib, json
from pathlib import Path
base = Path("docs/waves/1y0h2 handler-module-split")
for name in ("delivery-freeze.json", "delivery-repair-freeze.json", "delivery-pre-garden-freeze.json", "delivery-final-freeze.json"):
    mapping = json.loads((base / name).read_text())
    expected = mapping.pop("tree_fingerprint")
    actual = hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()
    assert actual == expected, name
    print(name, actual)
    if name == "delivery-final-freeze.json":
        for path, blob in mapping.items():
            data = Path(path).read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() == blob, path
```

Historical maps reproduce the aggregate fingerprints; they do not reconstruct old bytes or claim that the subsequently edited files still have their historical hashes. The final map additionally checks the present files. The definition-equivalence claim comes from the code lane's executed AST comparison; a QA lane using regression results is not counted as an additional AST proof.

## Pre-close follow-up

The operator authorized removal of composition-root aliases for standard-library/typing names, a real outside-root containment fixture, and accurate/reproducible evidence. Both handler modules already imported Any, Optional and Path directly; the cleanup uses those names. Behavior-dependent helper lookups remain late-bound. The strengthened fixture creates `outside.py` alongside a nested repository and checks both rejection and absence of its sentinel; patching the resolver to allow escape makes that same oracle fail. Nine focused handler tests pass. Independent code review passed eleven handler/digest tests, the live registered golden surface, all77 normalized AST comparisons and all19 runtime differential calls. Independent QA reran the containment/structure checks and reproduced the disclosure under bypass. Both reviewers reproduced all three manifest digests and validated all14 final current hashes. Final aggregate: `509c3c4b7af4cd64279a40ffc38f9db8cc2f2509d6e89ceb405285e30a4def43`.

The cleanup changes production identity, so a fresh indexed evaluation will supersede the initial delivery baseline. This is an operator-authorized refresh after the original single planned run, not a before/after performance comparison.

## Final pre-close receipts

The refreshed suite passed **9,418 tests / 114 files / 12 skips** in 302.669 seconds. Current framework receipt hash: `6a48b57b85bf739f554d86fa6bf95fa792b9d5b3199cd887be30610733925a9d`. The final report is `docs/reports/retrieval-quality-1y0bf-final.json`, SHA-256 `6ffd36fb70188e591f3520dc4bdcc3c0b60f3d120fdb93db5d8896e83df4c211`, verdict **baseline**, no invalidation or operator-review reasons. Completed generation1772 and attempt `52cc939f6bbe40c3b747ac7450c3d03d` remained unchanged. Production digest `958c641b8e8c9c14b604eee1dbca8bd4b16ee830e8bbaee2cdf1380a325dda51` was verified again at exit. Both source hashes matched indexed files before execution (124 codenav chunks,102 graph chunks). `verification-summary.json` holds exact fields; `verification-summary-initial.json` preserves the previous receipt.

An initial preflight attempt refused a stale generated wave record and ran no measurements. A subsequent unprotected attempt could not produce a valid report because a background refresh moved the index and the requested destination already held the preflight failure. Neither is used as baseline evidence. The successful final attempt used a fresh report path and held the normal indexer build-lock context in the parent while running the unchanged evaluator in a child process. This prevented concurrent refreshes; all evaluator preflight, generation and production-identity checks remained active. No repository code or configuration was changed for measurement coordination.

Memory close checkpoint returned zero new candidates and six persisted rejected dispositions. Retrospective lessons are recorded in the wave closure reconciliation and existing architecture documentation.

Close-time gardening updated only three Last verified dates: domain-map September15→20, search-architecture September17→20, registry ADR September19→20. Substituting the historical dates exactly reproduces the previous blob hashes; no prose or production code changed. The pre-garden final manifest is preserved as `delivery-pre-garden-freeze.json`; `delivery-final-freeze.json` now records current gardened bytes, aggregate `2e67176fef75db44764cab545b54530afe46136b66f41118b5f3f593d751b3d2`. All historical verification statements refer to the snapshot then reviewed; final current-file verification uses the gardened manifest.
