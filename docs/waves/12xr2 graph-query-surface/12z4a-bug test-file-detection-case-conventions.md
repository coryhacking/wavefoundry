# Fixed-community classifiers miss case-variant dirs and non-Python conventions

Change ID: `12z4a-bug test-file-detection-case-conventions`
Change Status: `complete`
Owner: framework-maintainer
Status: complete
Last verified: 2026-05-31
Wave: `12xr2 graph-query-surface`

## Rationale

Graph community clustering pre-assigns auxiliary files into fixed communities (**Tests**,
**Benchmarks**, **Scripts**, **Generated**, **CI/CD**, **Configuration**) via path-based
classifiers in `graph_cluster.py`. When a classifier misses files, they are clustered with
production code instead of being isolated. That distorts community boundaries, labels, and
the usefulness of the community overview — especially for non-Python projects and repos that
use title-case directory names (common on macOS/Xcode/SwiftPM layouts).

**Trigger:** Observed in a Swift/SwiftPM/Xcode project on framework **1.1.0+2z2x** (and
likely earlier): files under `Tests/` with `*Tests.swift` naming were not classified as tests.

**Broader review:** The same structural defects apply to **all six** path classifiers — not
only tests. Detection must work **across language technologies** (Python, Go, Rust, Java/Kotlin,
C#, Swift, JavaScript/TypeScript, C/C++, etc.) using path conventions common to each ecosystem,
not Python-only filename rules. This change applies a **shared** case-insensitive directory
helper across all classifiers and a **language-neutral filename policy** for tests/benchmarks.

## Requirements

1. **Multi-language test detection:** Classify test files correctly for Python, Go, Rust,
   Java/Kotlin, C#, Swift, JavaScript/TypeScript, and C/C++ using a combination of
   case-insensitive directory segments and extension-agnostic filename heuristics (see
   reference table below). Must not regress existing Python behavior.
2. **Tests — directories:** Case-insensitive match for `test`, `tests`, `__tests__`, `spec`,
   `specs`, and other agreed cross-ecosystem test directory names.
3. **Tests — filenames:** Extension-agnostic rules covering:
   - Python-style: `test_*`, `*_test.*` (not only `*_test.py`)
   - Go-style: `*_test.go` (generalize to `*_test.<ext>`)
   - PascalCase ecosystems (Java/Kotlin/C#/Swift): `*Tests`, `*Test`, `Test*` stems
   - JS/TS: `*.test.*`, `*.spec.*` in filename
4. **Shared directory matching:** All classifiers that match path **segments** use one
   case-insensitive helper (`part.casefold()` against a normalized set).
5. **Benchmarks:** Same directory fix plus multi-language filename stems (`*Benchmark*`,
   `bench_*`, `*_bench.*`, Go `*_bench_test.go` pattern where applicable).
6. **Scripts / Generated / Configuration / CI/CD:** Case-insensitive directory matching;
   preserve exact-case rules where the ecosystem requires it (`Dockerfile`, dot-prefixed CI
   dirs).
7. After fix, graph index rebuild reclassifies mis-bucketed files.
8. Deterministic behavior with per-language regression tests in `test_graph_cluster.py`.

## Scope

**Problem statement:** Fixed-community classifiers use case-sensitive directory membership
and (for tests/benchmarks) Python-only filename heuristics. Title-case or non-Python
conventions silently land in production Leiden communities.

**Affected code:** `.wavefoundry/framework/scripts/graph_cluster.py` — all `_is_*_source_file`
helpers (~L131–195) and their `_*_DIR_NAMES` constants (~L24–46).

### Cross-classifier audit (1.1.0+2z2x)

All classifiers split paths and use `part in _SOME_SET` (case-sensitive) unless noted.

| Classifier | Dir names (constant) | Filename heuristics | Same defects? | Example misses |
| ---------- | -------------------- | ------------------- | ------------- | -------------- |
| `_is_test_source_file` | `test`, `tests`, `__tests__` | `test_*`, `*_test.py` only | **Yes — confirmed** | `Tests/HueAuthorizationTests.swift` |
| `_is_bench_source_file` | `benchmark`, `benchmarks` | `bench_*`, `*_bench.py` only | **Yes** | `Benchmarks/FooBenchmarks.swift` |
| `_is_scripts_source_file` | `scripts`, `bin`, `tools` (shallow); `cli`, `tasks`, `cmd`, `hack` (any depth) | none | **Yes (dirs)** | `Scripts/seed.py`, `Bin/wave-gate` |
| `_is_generated_source_file` | `generated`, `__generated__`, `gen`, `migrations`, `stubs` | suffix list (`.pb.go`, etc.) | **Yes (dirs)** | `Generated/models.swift`, `Migrations/0001.sql` |
| `_is_cicd_source_file` | `.github`, `.gitlab`, `ci`, … | exact `Dockerfile`, `docker-compose.*` | **Partial** | `CI/workflow.yml` (dir); `Dockerfile` must stay exact |
| `_is_config_source_file` | `config`, `conf`, `settings`, `configuration` | exact known filenames + `*.config.js` | **Yes (dirs)** | `Config/settings.swift`; filenames mostly lowercase by convention |

**Documentation community** (`kind` `doc`/`seed`) is kind-based, not path-based — out of scope
for this bug.

### Tests — root cause (confirmed)

1. **Case-sensitive directory match**

   ```python
   return any(part in _TEST_DIR_NAMES for part in parts[:-1])
   ```

   `"Tests"` does not match `{"test", "tests", "__tests__"}`.

2. **Python-only filename patterns**

   ```python
   if filename.startswith("test_") or filename.endswith("_test.py"):
   ```

   Misses Swift `*Tests.swift`, Java `FooTest.java`, Go `foo_test.go`, C# `FooTests.cs`, etc.

### Language technology reference — test detection targets

Directory placement catches most integration-test layouts; filename rules catch unit-test
files outside those dirs. Implementers should use **stem/suffix checks that do not hardcode
`.py`**.

| Ecosystem | Typical test directories | Typical test filename patterns | Example path (must → Tests) |
| --------- | ------------------------ | ------------------------------ | --------------------------- |
| **Python** | `tests/`, `test/` | `test_*.py`, `*_test.py` | `tests/test_indexer.py` ✓ today |
| **Go** | (often same package dir) | `*_test.go` | `pkg/handler_test.go` |
| **Rust** | `tests/` (integration) | under `tests/`; `*_test.rs` optional | `tests/integration_test.rs` |
| **Java / Kotlin** | `src/test/java`, `src/test/kotlin`, `test/` | `*Test.java`, `*Tests.java`, `Test*.java` | `src/test/java/com/app/FooTest.java` |
| **C# / .NET** | `Tests/`, `test/` | `*Tests.cs`, `*Test.cs` | `MyApp.Tests/FooTests.cs` |
| **Swift** | `Tests/` (SPM/Xcode) | `*Tests.swift`, `*Test.swift` | `SolarisShared/Tests/HueBridgeTLSTests.swift` |
| **JavaScript / TS** | `__tests__/`, `tests/`, `spec/`, `specs/` | `*.test.js`, `*.spec.ts`, `*.test.tsx` | `src/__tests__/auth.test.ts` |
| **C / C++** | `test/`, `tests/` | `test_*.cpp`, `*_test.cpp`, `*Test.cpp` | `tests/test_parser.cpp` |

**Proposed unified filename rules (extension-agnostic where noted):**

| Rule | Matches |
| ---- | ------- |
| Path segment in test dir set (case-insensitive) | All rows above when file lives under a test directory |
| `filename.startswith("test_")` | Python, some C/C++ |
| `filename` matches `*_test.<ext>` | Go, Rust, Python generalization |
| `stem.endswith("Tests")` or `stem.endswith("Test")` | Swift, Java, Kotlin, C# |
| `stem.startswith("Test")` | JUnit 3–style Java, some Kotlin |
| `".test." in filename` or `".spec." in filename` | JS/TS/Vitest/Jest |

**Benchmark parity (same case/dir fixes + filename extension):**

| Ecosystem | Patterns |
| --------- | -------- |
| Python | `bench_*`, `*_bench.py` → generalize `*_bench.*` |
| Go | `*_bench_test.go`, `benchmark/` dir |
| Java (JMH) | `*Benchmark.java` |
| Rust | `benches/` dir |
| PascalCase | `*Benchmark*.swift/cs/java` stems |

**Observed Swift examples (confirmed miss today):**

| Path | Detected today? |
| ---- | --------------- |
| `SolarisMonitor/Tests/HueAuthorizationTests.swift` | No |
| `SolarisShared/Tests/ConfigurationFileValidationTests.swift` | No |
| `SolarisShared/Tests/HueBridgeTLSTests.swift` | No |
| `SolarisShared/Tests/RoutineStatusContractsTests.swift` | No |
| `SolarisShared/Tests/HueBridgeProperciesFileTests.swift` | No |
| `SolarisShared/Tests/JSONWithCommentsTests.swift` | No |

**Additional cross-language examples (must detect after fix):**

| Path | Language |
| ---- | -------- |
| `src/test/java/com/example/UserServiceTest.java` | Java |
| `MyApp.Tests/Controllers/HomeControllerTests.cs` | C# |
| `internal/api/handler_test.go` | Go |
| `tests/integration_test.rs` | Rust |
| `src/components/Button.test.tsx` | TypeScript |
| `src/__tests__/auth.spec.js` | JavaScript |

**Impact:** Misclassified auxiliary files pollute production communities; fixed buckets
(**Tests**, etc.) may be empty or incomplete.

**In scope:**

- Shared `_path_has_dir_segment(parts, names)` with case-insensitive matching.
- **Multi-language test filename policy** — implement unified rules from reference table;
  remove `.py`-only suffix checks (`*_test.py` → `*_test.*`; add `.test.`/`.spec.` infix,
  PascalCase stems, etc.).
- Parity fixes for benchmark/scripts/generated/config directory matching — same change.
- CI/CD: case-insensitive **directory** match for `ci`/`CI`; keep exact-case filename rules
  for `Dockerfile` and dot-prefixed tool dirs.
- Unit tests: **at least one positive example per language row** in the reference table (can
  be table-driven in `test_graph_cluster.py`).
- Bump `CLUSTER_BUILDER_VERSION`.

**Out of scope:**

- Parsing project manifests (`Package.swift`, `pom.xml`) for test-target membership.
- New fixed-community categories or Leiden algorithm changes.
- Case-folding **filenames** where the ecosystem is case-sensitive (`Dockerfile` ≠
  `dockerfile` on Linux containers).

## Acceptance Criteria

### Tests — multi-language

- [x] AC-1: Swift — `_is_test_source_file("SolarisMonitor/Tests/HueAuthorizationTests.swift")` → `True`.
- [x] AC-2: Python — `_is_test_source_file("scripts/tests/test_chunker.py")` → `True` (regression).
- [x] AC-3: Go — `_is_test_source_file("internal/api/handler_test.go")` → `True`.
- [x] AC-4: Java — `_is_test_source_file("src/test/java/com/example/UserServiceTest.java")` → `True`.
- [x] AC-5: C# — `_is_test_source_file("MyApp.Tests/Controllers/HomeControllerTests.cs")` → `True`.
- [x] AC-6: Rust — `_is_test_source_file("tests/integration_test.rs")` → `True`.
- [x] AC-7: TypeScript — `_is_test_source_file("src/components/Button.test.tsx")` → `True`.
- [x] AC-8: JavaScript — `_is_test_source_file("src/__tests__/auth.spec.js")` → `True`.
- [x] AC-9: Negative — `_is_test_source_file("src/indexer.py")` → `False`.
- [x] AC-10: Case variants — `Tests/`, `TEST/`, `__TESTS__/`, `Spec/` directories match.
- [x] AC-11: Ambiguous PascalCase stems (e.g. production file named `Contest.swift` outside
  test dirs) documented or guarded; false-positive rate acceptable per decision log.

### Cross-classifier parity

- [x] AC-12: `_is_bench_source_file("Benchmarks/embed_bench.swift")` or Go
  `foo_bench_test.go` returns `True`; Python `benchmarks/` paths unchanged.
- [x] AC-13: `_is_scripts_source_file("Scripts/seed.py")` and `Bin/update-indexes` → `True`;
  deep `pkg/framework/scripts/` still excluded.
- [x] AC-14: `_is_generated_source_file("Generated/models.swift")` → `True`; `_pb2.py` suffix
  unchanged.
- [x] AC-15: `_is_config_source_file("Config/settings.swift")` → `True`; `pyproject.toml` /
  `tsconfig.json` unchanged.
- [x] AC-16: `_is_cicd_source_file("CI/workflow.yml")` → `True`; `Dockerfile` exact match
  preserved.

### Verification

- [x] AC-17: `test_graph_cluster.py` includes a table-driven or explicit case per language
  in the reference table; full framework test suite passes.
- [ ] AC-18: After graph rebuild, observed Swift test paths and spot-checked Java/Go/C# paths
  land in the **Tests** fixed community.

## Tasks

- [x] Add shared helper `_path_has_dir_segment(parts, names)` using `part.casefold()`.
- [x] Refactor all six `_is_*_source_file` functions to use the helper for directory checks.
- [x] Implement `_is_test_source_file` filename policy per reference table:
  - [x] Generalize `*_test.py` → `*_test.<any-ext>`
  - [x] Add PascalCase stem rules (`Tests`, `Test`, `Test*` prefix)
  - [x] Add JS/TS `.test.` / `.spec.` infix detection
  - [x] Extend `_TEST_DIR_NAMES` with `spec`, `specs`, `__tests__` (already partially covered)
- [x] Implement `_is_bench_source_file` multi-language parity (`*_bench.*`, `*_bench_test.go`,
  `*Benchmark*` stems).
- [x] **Scripts / Generated / Config / CI/CD:** case-insensitive dirs; document exact-case
  exceptions.
- [x] Add **table-driven** regression tests: one path per language row + title-case dir cases
  for each classifier touched.
- [x] Bump `CLUSTER_BUILDER_VERSION`.
- [x] Rebuild graph index on affected repositories after merge.

## Agent Execution Graph


| Workstream           | Owner               | Depends On        | Notes                                        |
| -------------------- | ------------------- | ----------------- | -------------------------------------------- |
| shared-dir-helper    | framework-maintainer | —                 | One helper, all classifiers                  |
| multi-lang-test-rules | framework-maintainer | shared-dir-helper | Unified filename policy, not Python-only   |
| bench-lang-rules     | framework-maintainer | shared-dir-helper | Go/Java/Rust/PascalCase benchmark patterns   |
| parity-dirs          | framework-maintainer | shared-dir-helper | Scripts/Generated/Config/CI/CD               |
| regression-tests     | framework-maintainer | all above         | Table-driven per-language cases              |
| rebuild-verify       | qa-reviewer         | all above         | Swift + spot-check Java/Go/C#                |


## Serialization Points

- Introduce the shared directory helper first; all classifier edits depend on it.

## Affected Architecture Docs

`N/A` unless Prepare wave adds a one-line note in indexing/graph docs describing fixed-community
path classifiers and case-insensitive directory matching.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Confirmed Swift miss — primary trigger |
| AC-2 | required | Python regression guard |
| AC-3 | required | Go convention |
| AC-4 | required | Java convention |
| AC-5 | required | C# convention |
| AC-6 | required | Rust convention |
| AC-7 | required | JS/TS convention |
| AC-8 | required | Negative control |
| AC-9 | required | Case-insensitive dirs |
| AC-10 | important | False-positive guard for ambiguous stems |
| AC-11 | important | Cross-classifier bench parity |
| AC-12 | important | Scripts title-case dirs |
| AC-13 | important | Generated title-case dirs |
| AC-14 | important | Config title-case dirs |
| AC-15 | important | CI/CD title-case dirs |
| AC-16 | required | Test coverage per language |
| AC-17 | required | Full suite pass |
| AC-18 | important | Post-rebuild verification on real repo |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-05-29 | Bug reported from Swift/Xcode project; test files misclassified. | `graph_cluster.py` L131–138 |
| 2026-05-29 | Scope expanded: audit shows same case-sensitive dir pattern in all six `_is_*_source_file` classifiers; parity fix bundled into same change. | `graph_cluster.py` L24–195 |
| 2026-05-29 | Implemented shared `_path_has_dir_segment`, multi-language test/bench rules, cross-classifier case-insensitive dirs; `CLUSTER_BUILDER_VERSION=8`. | `graph_cluster.py`, `test_graph_cluster.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-29 | Bundle non-test classifier dir fixes in same change (not follow-up) | Same root cause, shared helper, minimal extra diff | Test-only fix first, parity in separate bug |
| 2026-05-29 | Extension-agnostic filename rules over per-language branches | One policy table; graph indexer already walks many languages; avoids N× duplicated `_is_test_*_file` helpers | Separate detector per language; manifest parsing |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| PascalCase `*Test`/`*Tests` false-positive on production names (`Contest.swift`, `LatestReportTestData.swift`) | Prefer directory context; require `Tests` plural suffix where ambiguous; negative tests per language |
| `spec/` matches non-test specification docs | Document JS/TS/Ruby convention; negative test for `docs/spec/` |
| Go `testdata/` or fixtures dirs misclassified | Do not add `testdata` to test dir set unless confirmed; fixtures often non-test helper data |
| `.test.` infix matches non-test filenames rarely (`contest.test.json`) | Accept low rate or require known extensions (`.js`, `.ts`, `.tsx`, `.jsx`, `.mjs`, `.cjs`) |
| Case-folding dot dirs (`.GitHub`) | Only fold segment names in configured sets; leave dot-prefixed CI dirs as configured lowercase literals |
| Title-case `Scripts/` at depth 3+ misclassified | Preserve existing shallow-depth rule for scripts/bin/tools |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
