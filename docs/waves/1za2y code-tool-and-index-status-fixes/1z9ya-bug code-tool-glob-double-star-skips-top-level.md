# Code Tool Globs Match `**/` Across Zero Directories

Change ID: `1z9ya-bug code-tool-glob-double-star-skips-top-level`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-29
Wave: 1za2y code-tool-and-index-status-fixes

## Rationale

`code_keyword(query, glob=".wavefoundry/framework/scripts/**/*.py")` found nothing for a symbol defined in `scripts/record_paths.py`, so a census built on that glob silently missed every module directly in `scripts/`. The glob filter is copied inline five times in `wf_server/codenav_handlers.py` (the `code_list_files`, `code_keyword` (two sites), `code_constants` and `code_pattern` handlers) as `fnmatch.fnmatch(relpath, glob) or fnmatch.fnmatch(p.name, glob)`. In `fnmatch`, `*` also matches `/`, so `**` behaves like `*`, and `A/**/*.py` needs a literal `/` on each side: at least one subdirectory. `**/*.py` also misses files at the repository root. The tool docstrings show `**/` examples (for example `"**/server.py"`) that a root-level file does not match.

## Requirements

1. One shared glob matcher replaces the inline copies. The set of call sites is every glob filter over navigation file paths in `codenav_handlers.py` (derive it from the `fnmatch` uses there), not a hand-listed subset.
2. A `**/` segment matches zero or more directories: `A/**/*.py` matches `A/x.py` and `A/b/x.py`; `**/*.py` matches a root-level file.
3. Every path a glob matches today still matches: `*` still crosses `/`, a pattern still also matches against the file name, and matching keeps its current case sensitivity per platform (case-insensitive on Windows, as `fnmatch` does today).
4. The glob semantics are stated once in `docs/specs/mcp-tool-surface.md`, and the tool docstrings' glob examples match them.
5. Matching cost stays linear in the pattern: the matcher does not expand one variant per `**/` segment or build a regular expression with nested repetition.

## Scope

**Problem statement:** `**/` requires at least one directory, so globs silently skip top-level files.

**In scope:**

- The shared matcher and its use at every navigation glob site in `codenav_handlers.py`.
- Tool docstrings and the spec's glob description.

**Out of scope:**

- Changing `*` to stop at `/`, or adding brace expansion (`{py,md}`): both would change or add semantics, not fix `**/`. Brace globs stay unsupported and the spec says so.
- The navigation walker (change `1z9u7`).

## Acceptance Criteria

- [x] AC-1: `code_keyword`, `code_constants`, `code_list_files` and `code_pattern` with `glob="A/**/*.py"` include a file directly in `A/` as well as files in its subdirectories, and `**/*.py` includes a root-level `.py` file.
- [x] AC-2: a table of existing glob forms (`*.py`, `dir/*.py`, `*beta*`, a full relative path, `src/**`, a trailing `/**`, and `**` inside a path segment) matches the same paths before and after the change.
- [x] AC-3: the spec states the glob semantics (including that `*` crosses `/`, that the file name is also tried, and that braces are unsupported) and every tool docstring glob example is consistent with them.
- [x] AC-4: the change's own suites and every test it adds pass, and the documents it edits validate.

## Tasks

- [x] Add the shared matcher and replace every inline glob filter in `codenav_handlers.py` with it.
- [x] Tests: `**/` with zero and more directories, a root-level file, and the unchanged-forms table, through each tool named in AC-1.
- [x] Docstrings in `wf_server/server_impl.py` and the spec's glob description.
- [x] CHANGELOG Fixed entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Matcher, call sites, docs | implementer | readiness | |
| Review | code, QA, docs-contract reviewers | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/codenav_handlers.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/specs/mcp-tool-surface.md`

Root release note: CHANGELOG.md.

## Affected Architecture Docs

N/A: the tool contract lives in `docs/specs/mcp-tool-surface.md`, which this change updates; no module boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The observed defect |
| AC-2 | required | No regression for existing globs |
| AC-3 | important | Agents choose globs from the docs |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-29 | Delivery repair round 1 (QA-4, DOC-4, code note on `[!]]`): `**/` is a marker only as a whole segment (glob start or after `/`), so `a**/b.py` no longer matches `ab.py`; class parsing follows fnmatch (a `]` right after `[` or `[!` is a member). New cases: `a**/b.py`, `src/a**/b.py`, `**/[t]op.py`, `**/[!]]*.py`, `**/a*c.py`. Scratch mutants: marker anywhere fails 2 subtests; the old class parse fails 1 | `test_navigation_glob` OK |
| 2026-09-29 | Full suite run: the first run failed `test_mcp_tool_registry.HandlerDigestTests` (the handler-digest fixture pins tool docstrings; exactly `code_constants`, `code_keyword`, `code_list_files`, `code_pattern` and `index_build_status` moved, all edited on purpose by 1z9ya and 1z9yb, and only those entries were refreshed) and `test_server_package.RetiredFlatNameCensusTests` (new tests used `from wf_server import <evicted module>`, which reads a stale module after a reload; changed to `import wf_server.<name> as <name>`). Rerun green | `run_tests.py --no-cache`: 10031 tests across 143 files OK |
| 2026-09-29 | Implemented. `_glob_matches` keeps the old `fnmatch(relpath) or fnmatch(name)` result and adds a state-set matcher only when the glob contains `**/` (`*` any run from the current positions, `**/` also skips to after any `/`, other tokens through `fnmatchcase`; lowercased on Windows); all five inline filters in `codenav_handlers.py` call it; tool docstrings and the spec state the rule. A first regex translation backtracked on 40 `**/` segments and hung the run; the state-set matcher replaced it and `test_many_double_star_segments_stay_fast` pins the cost. Scratch mutant: a plain `fnmatch` filter fails the zero-directory and root-file cases. Gapfill: the filter sites were found with grep because `code_keyword` with `**/*.py` skips top-level files, the defect this change fixes | `tests/test_navigation_glob.py` 5 OK |
| 2026-09-29 | Readiness review folded in: more unchanged forms in AC-2, Windows case rule stated, linear matching cost. | readiness review |
| 2026-09-29 | Planned. Semantics probed with a scratch script: `**` equals `*` under `fnmatch`; `A/**/*.py` needs a subdirectory; `**/*.py` misses a root file; `*.py` and `dir/*.py` match recursively; braces unsupported. | investigation of `codenav_handlers.py` glob filters |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-29 | One shared matcher where `**/` also matches zero directories, keeping every current match | Fixes the defect without changing any glob that works today | Gitignore-style globbing where `*` stops at `/` (breaks `dir/*.py` matching recursively, which callers rely on); fixing only `code_keyword` (leaves four identical copies to drift) |

## Risks

| Risk | Mitigation |
| --- | --- |
| A new matcher changes an existing match | The unchanged-forms table in AC-2 |
| A glob site is missed | Derive sites from the `fnmatch` uses in `codenav_handlers.py` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
