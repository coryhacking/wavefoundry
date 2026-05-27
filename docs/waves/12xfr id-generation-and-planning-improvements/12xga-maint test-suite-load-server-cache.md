# Test Suite: `load_server()` Per-Class Cache via `setUpClass`

Change ID: `12xga-maint test-suite-load-server-cache`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: 12xfr id-generation-and-planning-improvements

## Rationale

`test_server_tools.py` runs ~1665 tests in ~130s when framework files change, because `load_server()` is called in `setUp` across ~98 test classes — one full `exec_module` reimport of `server.py` + `server_impl.py` per test method. Moving to `setUpClass` for classes whose tests are safe (using only context-managed patches, not raw attribute assignments) reduces the number of module loads from ~1665 to ~98, targeting a runtime near 60s.

## Requirements

1. Audit all test classes in `test_server_tools.py` that call `self.srv = load_server()` in `setUp` to classify them as **safe** (use only context-managed `patch.object(...)` calls, no raw `self.srv.attr = value` mutations) or **unsafe** (raw attribute mutations that would leak between tests within the class).
2. For each **safe** class: replace `setUp` with a `@classmethod setUpClass` (`cls.srv = load_server()`) and add `self.srv = self.__class__.srv` (or `self.srv = type(self).srv`) in a lightweight `setUp` that does not call `load_server()`.
3. For each **unsafe** class: leave `setUp` as-is and add a comment marking the class as requiring per-method isolation.
4. Classes that call `load_server()` for module-reload testing (asserting version state, testing the thin-runner split) must keep per-method isolation; any shared state from a previous test would invalidate the test premise.
5. The full test suite must pass with 0 failures after the conversion.
6. Target wall-clock runtime ≤ 60s on CI hardware (from ~130s baseline).

## Scope

**Problem statement:** The full test suite takes ~130s on framework changes because `load_server()` (a full `exec_module` reimport) is called once per test method, not once per test class.

**In scope:**

- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — audit + convert safe classes to `setUpClass`

**Out of scope:**

- Other test files (they do not call `load_server()`)
- Changes to `load_server()` itself (no API change needed)
- Introducing a `WAVEFOUNDRY_SKIP_SLOW_TESTS` flag (separate scope)
- Parallelizing the test suite

## Acceptance Criteria

- [x] AC-1: Every test class in `test_server_tools.py` that uses `load_server()` is classified in an audit table (safe / unsafe / reload-sensitive) with rationale.

  | Class | Classification | Rationale |
  |---|---|---|
  | 89 classes (see code) | safe | Context-managed patches only; no raw `self.srv.attr =` mutations |
  | `ReadChunkerVersionTests` | unsafe | Mutates `self.srv._chunker_version_cache` directly in a helper called from test methods |
  | `RerankerTests` | unsafe | Mutates `self.srv.DEFINITION_BOOST_RULES` directly (try/finally restore, but raw mutation pattern) |
  | `WaveMcpReloadTests` | reload-sensitive | Calls both `load_server()` and `load_thin_runner()` in setUp; tests module-reload behavior |
  | `SemanticEmbeddingRegressionTests` | already setUpClass | Previously converted; left unchanged |
  | `TestLanceDBIndex` | already setUpClass | Previously converted; left unchanged |
- [x] AC-2: All **safe** classes use `setUpClass` + a thin `setUp` that does not call `load_server()`.
- [x] AC-3: All **unsafe** and **reload-sensitive** classes retain per-method `load_server()` calls and are annotated with a comment explaining why.
- [x] AC-4: `python3 .wavefoundry/framework/scripts/run_tests.py --no-cache` passes with 0 failures.
- [ ] AC-5: Wall-clock runtime drops from the ~130s baseline to ≤ 60s on the developer machine. (Gate: audit must show ≥ 70% of classes are safe before the 60s target is considered realistic; if fewer, revise the target before converting.) **Target not met: measured 112s (18s / 14% improvement). Remaining time is test-body overhead — tmpdir I/O, file writes, subprocess calls — not module loads. Further gains require a different approach (e.g., parallelisation or skipping slow embedding tests by default).**

## Tasks

- [x] Audit: grep `setUp` for `load_server()`, then inspect each class for raw `self.srv.attr =` attribute mutations (not mere `self.srv =` rebinds, which are safe) and reload-sensitive patterns; record safe/unsafe/reload-sensitive count
- [x] Build audit classification table (safe / unsafe / reload-sensitive)
- [x] Convert safe classes: `setUp` → `setUpClass` + thin `setUp`
- [x] Annotate unsafe and reload-sensitive classes with inline comment
- [x] Run `python3 run_tests.py --no-cache` and record timing — 112s / 1665 tests / 0 failures
- [x] Verify AC-5 (timing target) — **not met**: 112s vs ≤60s target; improvement is real (18s) but bottleneck is test-body I/O, not module loads

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Audit | implementer | — | Read-only; produces classification table |
| Conversion | implementer | Audit | Edit safe classes; no gate required (test file only) |
| Validation | implementer | Conversion | Full suite + timing measurement |

## Serialization Points

- Complete the audit before any conversion — classifying incorrectly produces silent state-leakage bugs that are hard to diagnose after the fact.

## Affected Architecture Docs

N/A — confined to the test file; no boundary, flow, or verification architecture impact.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Audit is prerequisite for safe conversion |
| AC-2 | required | Core behavior change |
| AC-3 | required | Documents isolation invariants for future maintainers |
| AC-4 | required | No regressions |
| AC-5 | important | Timing target is the goal; "important" because hardware variation may prevent exactly 60s |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-26 | `setUpClass` per class, not a module-level singleton | Per-class isolation is a hard boundary — no cross-class state leakage is possible even if one test mutates module globals; singleton cache risks silent cross-class corruption | Module-level singleton with `fresh=True` opt-in — rejected: any test that forgets `fresh=True` corrupts later tests; silent failure mode |
| 2026-05-26 | Audit first, convert second | Classifying all 98 classes before touching any reduces the chance of mis-categorization | Opportunistic conversion — rejected: a single missed raw-assignment leaks state, causing failures in the wrong test method |
| 2026-05-26 | Annotate unsafe classes, not a skip list | Inline comments survive refactors better than an external list; future contributors see the reason at the call site | External skip list or config — rejected: decoupled, rots silently |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-26 | Change doc created | Operator direction; baseline measured at 132s / 1665 tests |
| 2026-05-26 | Implementation complete | 89 safe classes converted, 3 annotated; suite 112s / 1665 / 0 failures |

## Risks

| Risk | Mitigation |
| --- | --- |
| A class classified as "safe" has a raw attribute mutation missed by grep | Two-pass audit: grep for `self.srv.` assignments without surrounding `with patch`, then manual spot-check of the highest-test-count classes. Distinguish `self.srv.attr = value` (unsafe — mutates shared object) from `self.srv = ...` inside a test method (safe — rebinds instance attribute only). |
| After conversion, a new test added to a `setUpClass` class uses raw assignment without being noticed | Add a comment at the class level noting the isolation contract so future contributors recognize the constraint |
| `setUpClass` error propagation is worse than `setUp` | If `load_server()` raises in `setUpClass`, every test in the class is marked as an error (not just one). Mitigation: verify `load_server()` is resource-free and confirm it does not raise under normal conditions before committing to full conversion. |
| 60s target not met if fewer than 70% of classes are safe | Record safe/unsafe/reload-sensitive count during audit; revise the target before converting if the safe fraction is too low. |
| 60s target not met if the embedding regression tests dominate | Embedding tests already skip gracefully when model is not cached; if cached, they are a fixed cost (~10–20s) independent of this change |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
