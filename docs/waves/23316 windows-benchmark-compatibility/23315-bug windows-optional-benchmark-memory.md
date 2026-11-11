# Keep the embedding benchmark usable without Unix memory APIs

Change ID: `23315-bug windows-optional-benchmark-memory`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-10
Wave: 23316 windows-benchmark-compatibility

## Rationale

The standalone embedding benchmark imports Unix-only `resource` unconditionally at module load. On native Windows the import is unavailable, so even its CLI cannot start. A bounded probe of that actual import statement with resource unavailable produced ModuleNotFoundError; native Windows execution has not run. Current source also rounds, subtracts, compares and formats peak RSS as a mandatory float. Making only the import conditional would therefore move the failure into reporting rather than fix it.

The production contained-file writer already checks fchmod availability and selects a path-based fallback without directory-descriptor support. A manual control successfully created, replaced and retained an unchanged file with fchmod absent. Preserve that behavior with a maintained test; no file-writer product change is requested.

## Product Intent

A Windows operator can start the embedding benchmark and obtain its available timing and retrieval results without a Unix-only memory API. Missing memory evidence is explicit, never zero or a passing memory criterion. AC-1 and AC-2 establish that behavior with offline controlled workloads; AC-3 preserves the existing older-Windows file-writing path. This supports the adopted [vision](../../../VISION.md), Horizon 1's dependable delivery, without changing the roadmap or claiming native Windows qualification.

## Requirements

1. Make resource optional in benchmarks/embed_bench.py. When it is absent, CLI help and benchmark execution must not fail because of that absence. Preserve unrelated import errors rather than broadly swallowing them.
2. When resource is absent, report peak_rss_mb and rss_delta_mb as JSON null, add an explicit explanation that the resource-based peak RSS measurement is unavailable, and print an unavailable marker in progress and summary output. Keep field names and numeric values on supported hosts. Do not substitute current RSS, a different memory metric, zero or a fabricated value.
3. When either baseline or candidate peak RSS is unavailable, report vs_baseline.memory_ok as null with an explanation, rather than passing/failing or evaluating arithmetic on null. Keep timing, throughput, retrieval and other decision criteria operating. Preserve existing supported-host units and comparison semantics.
4. Add a regression test that removes fchmod capability and forces the existing path-based Windows branch, then verifies creation, replacement and unchanged-file behavior through write_contained_bytes. Use an isolated module OS proxy or equivalent restoration-safe fixture; do not mutate process-wide os irreversibly. No production contained_files change is in scope.
5. Keep all tests offline with synthetic embeddings and temporary output roots. No model download, live model execution, repository index build or external install is required. Describe the unavailable memory fields and comparison in benchmark guidance and release notes; simulated capability tests do not qualify all Windows behavior.

## Scope

In scope: .wavefoundry/framework/scripts/benchmarks/embed_bench.py; a focused benchmark compatibility test module under scripts/tests; tests/test_contained_files.py; existing benchmark documentation if present or the benchmark's own help/docstring; CHANGELOG.md.

Out of scope: production embedding/backend changes, alternate memory-measurement dependencies, full Windows CI, work-area/snapshot support, broad platform cleanup, source changes to contained_files.py, packaging/version changes, commit, push or closure.

## Acceptance Criteria

- [x] AC-1: With resource genuinely unavailable to the imported benchmark, its ordinary help path succeeds and a controlled full benchmark/report path completes with timing and retrieval results. JSON and terminal output explicitly represent unavailable peak/delta memory without type errors or false numeric values. Restoring the unconditional import fails the control.
- [x] AC-2: A baseline/candidate controlled run with missing memory yields memory_ok=null and its reason; numeric supported-host cases retain peak RSS conversion, delta and memory comparison results. Tests exercise progress, report and summary consumers rather than only the helper.
- [x] AC-3: A maintained regression test removes fchmod capability while exercising the existing path fallback and proves create, replacement and no-op behavior. A test-local known-bad variant that calls missing fchmod is detected; production file-writing code stays unchanged.
- [x] AC-4: Changed benchmark guidance describes the fields and evidence limits, changed tests pass, touched docs validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Reproduce the missing-module failure and inspect every peak-RSS consumer.
- [x] Implement optional measurement and truthful report/console handling.
- [x] Add offline end-to-end benchmark controls and missing-fchmod regression with known-bad checks.
- [x] Update guidance and changelog; run focused checks, canonical suite and required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | Implementer | Readiness | One small benchmark change and tests. |
| Verification | Independent reviewers | Implementation | Bounded offline controls; no actual models. |

## Serialization Points

Coordinator owns lifecycle records. One implementer owns the benchmark, tests and release note. Reviewers do not edit source. Preserve unrelated concurrent work.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/benchmarks/embed_bench.py`
- `.wavefoundry/framework/scripts/tests/test_embed_bench_compatibility.py`
- `.wavefoundry/framework/scripts/tests/test_contained_files.py`

## Affected Architecture Docs

N/A: existing standalone benchmark receives optional measurement reporting; no production architecture, module ownership or workflow boundary changes. Document the report contract in the benchmark docstring/help and existing benchmark documentation if present.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Makes benchmark execution usable when the module is absent. |
| AC-2 | required | Prevents false evidence and preserves existing numeric behavior. |
| AC-3 | required | Protects the verified older-Windows writing fallback. |
| AC-4 | required | Keeps delivered behavior and guidance consistent. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-10 | Final canonical suite passed: 12,747 tests across 240 files, 12 skips, 700.189 seconds. Full docs validation and diff whitespace check passed. AC-4 complete. | .wavefoundry/work/23316/full-suite-qualified.log; successful canonical test receipt. Native Windows and live model performance remain unqualified. |
| 2026-11-10 | Initial full-suite attempt stopped as sandbox-limited, not qualification. Local socket bind and process enumeration each refused with PermissionError errno 1. Verified runner PID/cwd/wave-log ownership before terminating it and its own descendants; canonical suite restarted with local permissions. | full-suite.log (incomplete), full-suite-qualified.log (current). No source changes between attempts. |
| 2026-11-10 | Implemented optional RSS, null comparisons/reasons and console handling; AC-1–3 pass. Focused runner: 51 tests, one existing skip. | test_embed_bench_compatibility (5), test_contained_files (46). Original unconditional import, fabricated zero and unconditional missing fchmod variants each rejected; .wavefoundry/work/23316/negative-controls.txt. First focused run exposed a help-line-wrap assertion, corrected without changing product behavior. |
| 2026-11-10 | Readback: implement optional resource-based RSS; preserve numeric units, mark unavailable measurements and comparisons null with reasons, and test complete report rows plus absent-fchmod writes. AC-1–4; benchmark, focused tests and changelog only. | Readiness passed; no production file-writer changes or live models. |
| 2026-11-10 | Planned from source inspection and prior simulated capability probes; native Windows remains unverified. | embed_bench._peak_rss_mb, measure_full_rebuild and main; contained_files.write_contained_bytes. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-10 | Optional resource measurement with nulls and explicit explanations. | Removes the startup failure without inventing a memory result; full report controls expose missed consumers. | Reject Windows entirely: loses usable timing/quality work. Add another memory backend: expands dependencies and risks changing metric meaning. |
| 2026-11-10 | Preserve file writer and add capability regression only. | The simulated missing-fchmod path already works; a production rewrite has no demonstrated benefit. | Replace guarded POSIX calls globally: unnecessary and risks weakening working behavior. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A later consumer still assumes a float. | Exercise report creation, baseline comparison and terminal summary with unavailable memory. |
| Tests accidentally keep the host's resource or fchmod. | Block the import and remove the attribute explicitly; known-bad controls prove detection. |
| Simulated Windows results overstate support. | State macOS execution and simulated capabilities separately from native qualification. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
