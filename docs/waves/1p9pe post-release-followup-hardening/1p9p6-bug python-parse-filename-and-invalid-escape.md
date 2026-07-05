# Fix invalid-escape SyntaxWarning at source and make indexer AST-parse warnings name the real file

Change ID: `1p9p6-bug python-parse-filename-and-invalid-escape`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-04
Wave: `1p9pe post-release-followup-hardening`

## Rationale

A full index rebuild emitted, mid-build, two identical lines with no actionable source:

```
<unknown>:293: SyntaxWarning: invalid escape sequence '\`'
```

Two distinct defects combine to produce this:

1. **A real invalid escape sequence in framework source.** `.wavefoundry/framework/scripts/tests/test_wf_cli.py:293` contains, inside a normal (non-raw) triple-quoted docstring, the fragment ``(``\`docs_lint.py\```)``. `\`` is not a recognized Python escape, so Python 3.12+ raises a `SyntaxWarning` (and a future Python will make it a hard `SyntaxError`) when the file is compiled/parsed. A tree-wide sweep of every tracked `.py` file under `-W error::SyntaxWarning` confirms this is the **only** file with a genuine invalid-escape warning — the other `\`` occurrences in the tree (`gen_codebase_map.py`, `wave_lint_lib/secrets_validators.py`, `wave_lint_lib/helpers.py`, `wave_lint_lib/wave_validators.py`) all sit inside raw strings or regex literals and are benign.

2. **The indexer parses Python with no `filename=`, so the warning is undiagnosable.** The indexing pipeline calls `ast.parse(source)` without the optional `filename=` argument, which defaults to `"<unknown>"`. That is why the warning reads `<unknown>:293` instead of naming the file. The warning surfaces in the build log because `_run_indexer` merges the child's stderr into the watched stdout pipe (`stderr=subprocess.STDOUT`); it appears more than once because the source is parsed by more than one indexing pass/worker (code chunking plus the parallel graph-extraction workers), and each `<unknown>`-filenamed parse registers independently. Note that `server_impl.py` already passes `filename=str(p)` at several of its own `ast.parse` sites — the indexing-path sites simply never adopted that pattern, so any invalid escape in a target repo's Python (not just our own) is reported today as an untraceable `<unknown>:N`.

Fixing (1) removes the current noise and the latent forward-compat `SyntaxError`; fixing (2) means the next such warning — in this repo or any indexed target repo — names the offending file and line so it can be found without a manual grep. A regression guard makes the invalid-escape class non-recurring.

## Requirements

1. The invalid escape sequence at `.wavefoundry/framework/scripts/tests/test_wf_cli.py:293` must be eliminated so the file compiles with zero `SyntaxWarning` under `python -W error::SyntaxWarning`, while the docstring's rendered intent (illustrating that a bare prose mention of `` `docs_lint.py` `` is allowed) is preserved.
2. The Python `ast.parse` calls on the **indexing path** must pass `filename=` naming the file being parsed, so a `SyntaxWarning`/`SyntaxError` from indexed Python (this repo or a target repo) names the real path and line instead of `<unknown>`. The three current indexing-path sites are `chunker.py:497` (`chunk_python`, `path` in scope), `chunker.py:5179` (`_extract_python_module_docstring`, no path in scope — thread one in), and `graph_indexer.py` `_extract_python_artifact` (~:6518 post-1p9q3; the file is under active edit by a sibling wave — anchor by symbol, `rel_path` in scope).
3. Passing `filename=` must not change any chunking, symbol-extraction, or graph-extraction output — it is a diagnostic-only argument. The existing `except SyntaxError:` fallbacks at each site must remain unchanged in behavior (a genuinely unparseable file still degrades gracefully; it does not start raising).
4. A regression guard must fail if any tracked, non-vendored `.py` file (re)introduces an invalid-escape `SyntaxWarning`, so this defect class cannot silently return.
5. No behavioral change to `wf_cli` itself: the edit to `test_wf_cli.py` is confined to the offending docstring; the test's assertions and the coverage contract it documents are untouched.

## Scope

**Problem statement:** A framework test file carries a genuine invalid-escape `SyntaxWarning` (latent future `SyntaxError`), and the indexer's `ast.parse` calls omit `filename=`, so the warning surfaces during builds as an untraceable `<unknown>:293` with no path.

**In scope:**

- Fix the invalid escape at `tests/test_wf_cli.py:293` (raw-string the docstring, or otherwise make `` `docs_lint.py` `` render without an invalid escape).
- Add `filename=` to the three indexing-path `ast.parse` sites (`chunker.py:497`, `chunker.py:5179`, `graph_indexer.py` `_extract_python_artifact` ~:6518), threading an optional `filename`/path parameter into `_extract_python_module_docstring` (and its caller at `chunker.py:5225`) where no path is currently in scope, defaulting to `"<unknown>"` to preserve call compatibility.
- A regression test (in the framework test suite) that sweeps tracked non-vendored `.py` files and asserts none emits an invalid-escape `SyntaxWarning`.

**Out of scope:**

- The benign `\`` occurrences inside raw strings / regex literals elsewhere in the tree — the sweep confirms they emit no warning; do not churn them.
- The `server_impl.py` `ast.parse` sites that already pass `filename=` (`:11889`, `:11923`, `:14320`) and the non-indexing `server_impl.py` sites that don't (`:10259`, `:11204`, `:11424`, `:13555`) — those are code-navigation/outline tools, not the build-time indexing path that produced the observed log noise; leave them to a separate change if desired.
- Any change to how `_run_indexer` merges child stderr, or to warning capture/filtering at the subprocess boundary — the fix is to name the file, not to mute or reroute the stream.
- Broader adoption of `-W error::SyntaxWarning` as a suite-wide flag.

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/framework/scripts/tests/test_wf_cli.py` compiles with **zero** `SyntaxWarning` under `python -W error::SyntaxWarning -c "import ast; ast.parse(open(path).read())"`; the docstring still communicates that a bare prose mention of a script name is allowed. Verified by the AC-4 sweep passing and by reading the docstring. *(Evidence: docstring raw-stringed (`r"""`), one-token change; `-W error::SyntaxWarning` parse clean; sweep test passes.)*
- [x] AC-2: `chunker.chunk_python`, `chunker._extract_python_module_docstring`, and `graph_indexer._extract_python_artifact` each call `ast.parse(..., filename=<real path>)`; a unit test parsing a source string containing an invalid escape through one of these paths asserts the emitted `SyntaxWarning`'s `filename` is the supplied path, not `"<unknown>"`. **Effectiveness clause (corrective pass, applied 2026-07-04):** additionally, an integration-shaped check runs a real index build over a fixture tree containing an invalid-escape Python source and asserts the logged warning names the fixture path — the causal multi-pass story in the Rationale is explicitly not load-bearing; this check is. *(Evidence: all three sites pass `filename=`; `tests/test_python_parse_diagnostics.py` — unit tests cover all three paths; `IndexBuildWarningNamesFixturePathTests` runs a real graph index build over a fixture tree in a fresh subprocess and asserts stderr logs `src/bad_escape.py:…: SyntaxWarning` with no `<unknown>`. Rebuild-level proof: full graph rebuild on this repo post-fix logs zero `SyntaxWarning`/`<unknown>` lines.)*
- [x] AC-3: Chunk / symbol / graph output for a representative Python source is byte-for-byte unchanged by the `filename=` addition (the existing chunker/graph tests stay green), and a source that raises `SyntaxError` still degrades via the existing fallback (returns line-window chunks / empty artifact) rather than propagating. *(Evidence: full suite green — `test_chunker.py`, `test_graph_indexer.py` (376 tests), `test_indexer.py` (206 tests) unchanged and passing; `SyntaxErrorFallbackTests` pins the line-window / `None` fallbacks.)*
- [x] AC-4: A regression test sweeps every tracked, non-vendored `.py` file and fails if any emits an invalid-escape `SyntaxWarning`; it passes on the fixed tree and fails when the `test_wf_cli.py:293` fix is reverted. *(Evidence: `InvalidEscapeSweepTests` sweeps 117 tracked `.py` files via `git ls-files`; negative case verified — with HEAD's `test_wf_cli.py` temporarily restored the sweep FAILED naming `test_wf_cli.py:293: invalid escape sequence '\`'`, then passed again with the fix.)*
- [x] AC-5: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` (docs-lint) is clean. *(Evidence: 4457 tests across 43 files OK in 162s; `wave_validate` clean — see Progress Log.)*

## Tasks

- [x] Fix `tests/test_wf_cli.py:293` — make the offending docstring a raw string (`r"""`) or escape the backticks so `` `docs_lint.py` `` renders with no invalid escape; confirm the surrounding assertions are untouched. *(Raw-stringed the class docstring — one token; assertions untouched.)*
- [x] Add `filename=path` to `ast.parse` in `chunker.chunk_python` (`chunker.py:497`).
- [x] Add an optional `filename` parameter to `_extract_python_module_docstring` (`chunker.py:5179`), default `"<unknown>"`, pass it through from the caller at `chunker.py:5225`, and forward it into `ast.parse`.
- [x] Add `filename=rel_path` to `ast.parse` in `graph_indexer._extract_python_artifact` (anchored by symbol; landed at `graph_indexer.py:7402`).
- [x] Add a unit test asserting an invalid-escape source parsed through an indexing-path helper reports the supplied filename in the `SyntaxWarning`. *(`tests/test_python_parse_diagnostics.py::ParseFilenameInWarningTests` — all three paths, plus the subprocess integration build check.)*
- [x] Add the tree-wide invalid-escape sweep regression test to the framework suite. *(`InvalidEscapeSweepTests`; revert-negative case verified.)*
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`; fix any failures; clean any `__pycache__`. *(4457 tests / 43 files OK; `wave_validate` clean; `__pycache__` cleaned.)*

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-escape-fix | implementer | — | Fix `tests/test_wf_cli.py:293`; independent single-file edit. |
| ws2-parse-filename | implementer | — | Add `filename=` to the three indexing-path `ast.parse` sites (`chunker.py` ×2 + `graph_indexer.py`); `_extract_python_module_docstring` gains an optional param. |
| ws3-tests | implementer | ws1-escape-fix, ws2-parse-filename | Filename-in-warning unit test + tree-wide invalid-escape sweep; run suite + `wave_validate`. |


## Serialization Points

- `chunker.py` is edited by ws2 at two disjoint functions (`chunk_python`, `_extract_python_module_docstring` + its caller) — single owner, no concurrent edit.
- ws3's sweep test is the oracle for AC-1/AC-4 and must run after ws1 lands so the tree is clean.

## Affected Architecture Docs

N/A — the change adds a diagnostic-only `ast.parse` argument at three existing indexing sites, fixes one docstring, and adds tests. It introduces no module boundary, no data/control-flow change, and no change to what the chunker/graph produce (AC-3 pins output invariance). No `docs/ARCHITECTURE.md` or `docs/architecture/*` update is warranted.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The invalid escape is a real latent `SyntaxError` and the source of the observed noise; fixing it is the core defect fix. |
| AC-2 | required | Naming the file is the diagnosability fix the operator asked for; without it the next warning is untraceable again. |
| AC-3 | required | Output-invariance is the non-regression guarantee — `filename=` must be diagnostic-only, and the `SyntaxError` fallbacks must not change. |
| AC-4 | important | Regression guard prevents the invalid-escape class from silently returning; the fix works without it but recurs unguarded. |
| AC-5 | required | Suite + docs-lint green is the standing merge gate for framework code. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-04 | Implemented. (1) `test_wf_cli.py:277` class docstring raw-stringed (`r"""`) — parses clean under `-W error::SyntaxWarning`. (2) `filename=` added at all three indexing-path sites: `chunker.py` `chunk_python` (`filename=path`), `_extract_python_module_docstring` (new optional `filename="<unknown>"` param, forwarded from `_chunk_code_summary` as `filename=path`), `graph_indexer.py` `_extract_python_artifact` (`filename=rel_path`, landed at :7402). (3) New `tests/test_python_parse_diagnostics.py` (8 tests): filename-in-warning unit tests for all three paths, `SyntaxError` fallback pins, subprocess integration check (real `update_graph_index` build over a fixture tree with an invalid-escape source → stderr logs `src/bad_escape.py:2: SyntaxWarning`, no `<unknown>`, graph artifact written), and the tracked-`.py` sweep (117 files; revert-negative verified: with HEAD's `test_wf_cli.py` restored the sweep fails naming `test_wf_cli.py:293`). (4) **Live before/after:** BEFORE — parsing HEAD's `test_wf_cli.py` the pre-fix way reproduces exactly `<unknown>:293: SyntaxWarning: invalid escape sequence '\`'` (and today's freshness rebuild logged the same); AFTER — fresh full graph rebuild (`indexer.py --root . --content graph --full`, venv python) completed with **zero** `SyntaxWarning`/`<unknown>` lines (log `/tmp/1p9p6-graph-rebuild.log`; finished: 11360 nodes / 32546 edges). Full suite 4457 tests OK; `wave_validate` clean. No `GRAPH_BUILDER_VERSION` bump — no artifact-shape change. | `chunker.py:497,5177-5183,5225`; `graph_indexer.py:7400-7402`; `tests/test_wf_cli.py:277`; `tests/test_python_parse_diagnostics.py`; rebuild log; suite output. |
| 2026-07-04 | Freshness re-verification before implementation (waves 1p9q3/1roqn landed on the cited files): defect still reproduces — TODAY's full graph rebuild again logged `<unknown>:293` and the `-W error::SyntaxWarning` repro confirms `test_wf_cli.py:293`; chunker anchors exact; `_extract_python_artifact` moved :5667→~:6518 (anchors updated to symbol form — the file is under live edit by wave 1p9qh); `indexer.py:1013/1175` exclusion citations still exact. Corrective-note items applied in place: the Rationale's multi-pass causal story is NOT load-bearing (which pass emits the live warning remains unsettled — the fix does not depend on it), and AC-2 gains the rebuild-level effectiveness clause the corrective pass required. | Freshness lane 2026-07-04; live rebuild log; `-W error::SyntaxWarning` repro. |
| 2026-07-03 | Scoped from a live full index rebuild that logged `<unknown>:293: SyntaxWarning: invalid escape sequence '\`'` (×2) mid-build. Root-caused to (1) an invalid escape in `tests/test_wf_cli.py:293` and (2) indexing-path `ast.parse` calls omitting `filename=`. Tree-wide `-W error::SyntaxWarning` sweep confirms `test_wf_cli.py` is the ONLY file with a genuine invalid-escape warning; verified the three indexing-path parse sites and that `server_impl.py` already uses the `filename=str(p)` pattern at some of its own sites. | Build log `project-index-build.log`; `chunker.py:497,5179,5225`; `graph_indexer.py` `_extract_python_artifact`; `server_impl.py:11904,11938,14341` (post-1p9q3); tree sweep output. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Fix the escape at the source AND add `filename=` to the indexing-path parses AND add a sweep guard (approach A). | Fixes the actual defect, closes the diagnosability gap the operator flagged, and makes the escape class non-regressable. The `filename=` change is tiny and each site has a path readily available (or a trivial optional param). | (B) Fix only `test_wf_cli.py:293` — rejected: the next invalid escape reappears as an untraceable `<unknown>:N`, leaving the diagnosability gap. (C) Suppress `SyntaxWarning` at the indexer boundary + fix source — rejected: mutes legitimately useful signal (a target repo's real escape bugs, and our own); the goal is to surface, not silence. |
| 2026-07-03 | Scope `filename=` to the indexing-path sites only, not every `ast.parse` in the tree. | Those three sites produced the observed build-log noise and parse target-repo code at scale; the `server_impl.py` navigation/outline sites are a separate, non-build concern and some already pass `filename=`. | Sweep all `ast.parse` sites in one change — rejected as scope creep beyond the reported symptom. |
| 2026-07-03 | Prefer raw-stringing the `test_wf_cli.py` docstring over deleting the backtick example. | Preserves the docstring's illustrative intent (a bare prose mention of a script name is allowed) with a one-token change. | Rewrite the example without backticks — unnecessary; the backticks are the point of the example. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `filename=` inadvertently changes parse behavior or a downstream consumer keys off the `<unknown>` filename. | `filename=` is a documented diagnostic-only argument to `ast.parse`; AC-3 pins byte-for-byte output invariance and the existing `SyntaxError` fallbacks; no consumer reads the parse filename. |
| Raw-stringing the docstring alters an assertion that reads the docstring text. | The docstring is descriptive prose, not asserted-against; AC-5 (full suite) and AC-1 (read the docstring) confirm intent preserved and no test regressed. |
| The sweep test is slow or flaky (parsing every tracked `.py`). | Parse is compile-only (no import/exec), bounded to tracked non-vendored files; it mirrors the one-shot sweep already run by hand in seconds. |
| A future genuinely-invalid target-repo file now surfaces a real path in logs and looks alarming. | That is the intended improvement — a named path is strictly better than `<unknown>`; the `except SyntaxError:` fallback still degrades gracefully, so indexing is unaffected. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
