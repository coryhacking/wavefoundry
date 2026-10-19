# Faster document term matching in graph builds

Change ID: `212o7-enh doc-term-matcher-token-lookup`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-19
Wave: `2134o graph-doc-rescan-speed`

## Rationale

Wave 212ym's live rebuild showed the `doc rescans` phase of `GraphIndexSession.finalize` taking 5 minutes 10 seconds for 489 changed docs, while every other finalize phase took under 7 seconds. A profile of the real project-layer artifacts (2026-10-19) puts 99% of that time in one call in `GraphIndexSession._extract_doc_artifact`: `complex_pattern.finditer(code_ctx)`.

`GraphIndexSession._compile_doc_matcher` builds `complex_pattern` as a single `\b(?:t1|t2|...)\b` IGNORECASE alternation over every non-identifier term. In this repository that is 102,169 terms, a 6.45-million-character pattern, and 79,930 of the terms are JSON and config key paths from wave evidence files and fixtures. Python's `re` tries the alternatives one at a time at each position, so the scan runs at about 1,500 characters of code text per second: `docs/specs/mcp-tool-surface.md` takes 31 seconds, `README.md` 23, `CHANGELOG.md` 22.

A prototype that splits code text into tokens and looks each candidate span up in a dict ran the 12 largest docs in 0.022 seconds instead of 137. It found 251 of the regex's 257 matches with nothing extra. The 6 misses were terms that start with a non-word character (for example `/reports`), which a token split never yields.

## Product Intent

An operator or agent running a full or large graph build (`index_build(content='graph')`, `wf setup`, an upgrade) waits seconds rather than minutes for the document rescan phase, and gets the identical graph. Boundaries: the graph's nodes and edges do not change, no dependency is added, and incremental builds that touch few documents keep their current cost. AC-1 and AC-3 test whether the intent was met.

## Requirements

1. The complex-term scan in `GraphIndexSession._extract_doc_artifact` returns exactly the matches the current regex returns, in the same order: the leftmost, longest, non-overlapping case-insensitive matches of the complex terms, each with a word boundary (`\b`, as Python `re` defines it for `str` patterns) on both sides.
2. The scan no longer runs one regex alternation over all complex terms. It finds candidates by dictionary lookup over spans of the code text. Terms the lookup cannot reach (for example terms that begin or end with a non-word character) are matched by a fallback that preserves requirement 1 for them.
3. `GraphIndexSession._compile_doc_matcher` builds whatever lookup structure the scan needs once per finalize, as it builds the regex today, and keeps returning the `complex_lower` mapping its callers read. Its compile time on this repository is no worse than today's 5.2 seconds.
4. The `doc rescans` phase logs a progress line under the wave 212ym rule: in verbose mode, `build_index: graph finalize progress (<layer> layer): <done>/<total> docs` every `_GRAPH_PROGRESS_INTERVAL` docs and once at the end of the changed-doc loop.
5. Graph output is unchanged, so `GRAPH_BUILDER_VERSION` stays as it is. If the equivalence check of AC-2 finds any difference that cannot be removed, the version is bumped in this change and the difference is recorded in the Progress Log.

## Scope

**Problem statement:** Document term matching costs time proportional to code-text length times the number of complex terms, which makes the document rescan phase dominate graph builds.

**In scope:**

- `GraphIndexSession._compile_doc_matcher` and the complex-term scan in `GraphIndexSession._extract_doc_artifact` in `graph_indexer.py`.
- The doc-rescan progress counter (requirement 4).
- Tests in `test_graph_indexer.py`.
- One CHANGELOG bullet.

**Out of scope:**

- Changing which terms are eligible (for example dropping JSON key paths), which changes the graph.
- The simple-identifier path, caching across builds, and parallel document scanning.
- New dependencies (for example an Aho-Corasick package).

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2. The change is pure Python string and dict work inside the indexer process, with no file, path or process handling.

## Acceptance Criteria

- [x] AC-1: For a fixture of documents and a term set covering overlapping terms, a term that is a prefix of another, mixed case, terms starting or ending with a non-word character, non-ASCII word characters, and terms adjacent to punctuation, the new scan returns the same match sequence as the current regex, which the test keeps as its reference oracle. A mutant that drops the fallback or prefers a shorter match fails the test.
- [x] AC-2: A differential check over this repository's real documents and real term set (run during implementation; the script and its summary are recorded in the Progress Log) finds the new and old scans' match sequences identical for every document.
- [x] AC-3: A forced verbose full graph rebuild of this repository records, in the Progress Log, the `doc rescans` phase duration before (5:10 on 2026-10-19) and after this change, and shows the doc progress lines. This is the intent check; it records a measurement and sets no threshold.
- [x] AC-4: In verbose mode the changed-doc loop prints the requirement 4 progress lines at the interval and at the end; non-verbose builds print none. Oracle: captured stdout with the interval patched small.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Capture the old scan as a reference function in the tests.
- [x] Implement the lookup-based scan and its fallback; update `_compile_doc_matcher`.
- [x] Add the doc-rescan progress counter.
- [x] Add the AC-1 and AC-4 tests.
- [x] Run the AC-2 differential check and record it.
- [x] Run the AC-3 rebuild and record it (edit no tracked source while it runs: a source edit mid-build triggers the indexer's drift retry).
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| matcher | implementer | none | `graph_indexer.py`, tests |
| evidence | coordinator | matcher | AC-2 differential, AC-3 rebuild |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py`, `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`

## Affected Architecture Docs

N/A: the change is confined to the document matcher inside `graph_indexer.py`; the graph contract, data flow and stage boundaries are unchanged.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Equivalence with the current matcher is what makes this safe without a builder version bump. |
| AC-2 | required  | Fixture equivalence alone cannot prove the real term set behaves the same. |
| AC-3 | important | The only evidence the operator-visible speed-up happened. |
| AC-4 | important | Visibility for the remaining per-doc work. |
| AC-5 | required  | Standard change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned from the wave 212ym measurement and a read-only profile. | Profile scripts under the session scratchpad `docscan-prof/`; 489 docs took 403 s; the 40 largest averaged 5.0 s each, 99% in `complex_pattern.finditer`. |
| 2026-10-19 | Readiness red-team primer: no blocker. Implementation notes for exact equivalence: `str.lower()` is not `re`'s case folding (`İ` lowers to two characters), so never lowercase the whole text, only candidate slices of the original; `ı`, `ſ` and the Kelvin sign match ASCII terms under IGNORECASE, and the regex still consumes such a span when the lowered key has no target, shadowing later overlapping terms; split on Unicode `\w` runs of the original text; merge fallback terms per position with the lookup (longest wins, then resume after it) rather than as a second pass; define fallback terms structurally (any term whose edges the span split cannot produce). Order matters: `mentioned_set` gives the first term reaching a target ownership of the edge, so AC-2 compares ordered sequences. | Red-team primer report (`rt-probe/probe.py`). |
| 2026-10-19 | Implemented. `_DocTermMatcher` folds each character as `re` IGNORECASE does (`_sre.unicode_tolower` plus `re._casefix._EXTRA_CASES`, length-preserving), finds `\w` boundaries as `re` does, and at each boundary tries ends at later boundaries within the longest term's length, longest first, resuming at the match end. No separate fallback is needed: terms with non-word edges are matched by the same boundary walk. Cost is linear in text length, bounded by the longest term (200,000 pathological characters with a 192-character term: 1.6 s). AC-2 differential (scratch `212o7/differential.py` over a read-only copy of this repository's index): 102,169 complex terms; 489 documents, 489 identical ordered span sequences, 0 different, 1,836 spans; old regex scan 345.7 s, new 0.993 s. Coordinator fuzz: 80,000 random cases against the regex, 0 mismatches on Python 3.14 (3.11 not runnable here: the tool venv guard refuses it). `GRAPH_BUILDER_VERSION` unchanged (requirement 5). Gapfill: shell reads and edits used because auto mode prefers Bash for file work. | `run_tests.py --file test_graph_indexer.py --file test_indexer.py`: 984 OK. |
| 2026-10-19 | Delivery repair. Security seat (medium) and red-team (note): per-boundary cost scaled with the longest repository term (one 10,000-char term made 1 MB take about 6 minutes). Repaired: each boundary now tries whichever is fewer, the distinct term lengths (checked against a boundary bitmap) or the boundaries in the window, and a long candidate is sliced only when its first 16 folded characters match a term of that length; `_re_fold_char` cache capped at 65,536. Pathological 1 MB with a 10,002-char term: 5.3 s; with 50,000 terms up to 192 chars: 2.9 s. Code-reviewer then found no test term exceeded the 16-char prefix, so an off-by-one prefix mutant survived; added `test_long_terms_sharing_prefixes_match_the_regex`, which kills it. QA note: the linear-growth timing test could flake under load; it now compares 16x text against a 64x limit (quadratic is about 256x). Stale `matcher` annotation corrected. | `DocTermMatcherTests` and `GraphBuildProgressLoggingTests` OK; fuzz with terms up to 30 chars, 0 mismatches. |
| 2026-10-19 | QA round 2 blocked: no test guarded the security repair (forcing the old window walk, mutant N2, passed every test). Added `test_one_long_term_does_not_slow_every_position` (same text with and without one 10,002-char term, ratio below 20); N2 fails it at 319x. Code-reviewer and qa-reviewer re-approved the repaired matcher (`2134o-del-code-reviewer-2`, `2134o-del-qa-reviewer-2`); both timing tests passed 10 of 10 runs under heavy CPU load. | QA round 2 harness `qa2134o-r2/`; coordinator scratch mutant run. |
| 2026-10-19 | AC-3 measurement (forced `indexer.py --content graph --full --verbose`, no tree edits during the run, single pass, no drift retry): `doc rescans (489 changed docs)` 20:17:09 to `merge entries` 20:17:10, about 1 s, down from 5:10 on 2026-10-19; doc progress lines `250/489 docs` and `489/489 docs` printed. Whole graph extraction span 2:13 (was 7:26); the longest remaining gap is code extraction (1:22 between `250/554` and `500/554 code files`). Graph 73,706 nodes / 218,250 edges against 73,688 / 218,194 before; the difference is code added since (this wave's matcher and tests), not matching (AC-2). | Scratch log `2134o-graph-rebuild.log`. |
| 2026-10-19 | Implemented; all ACs and tasks done. Wave paused by operator instruction while 2134s is implemented; the whole framework suite runs before close. | `run_tests.py --file test_graph_indexer.py --file test_indexer.py`: 986 OK. |
| 2026-10-19 | Whole framework suite (last, both waves 2134o and 2134s in the tree): `Ran 11945 tests across 201 files in 722.422s OK` (12 skipped); green receipt. | `python3 .wavefoundry/framework/scripts/run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Replace the alternation with span lookup plus a fallback for terms a token split cannot reach, keeping exact regex semantics. | About 6000 times faster in the prototype, no new dependency, no graph change. | (a) Exclude JSON/config key paths from the alternation: 11 times faster but drops doc-to-JSON edges, a graph change. (b) Cache per document hash: no help on full rebuilds. (c) Parallel processes: at most the core count. (d) Aho-Corasick: needs a dependency. (e) Bucket the alternation by first character: keeps `re` semantics without reimplementing them, but buckets still hold thousands of terms and a regex is still tried at every position; kept as the fallback design if exact equivalence of the lookup proves too costly. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Subtle semantic drift (word boundaries, case folding, overlap order) silently changes the graph. | AC-1 keeps the old regex as the oracle; AC-2 compares every real document; requirement 5 bumps the builder version if anything differs. |
| The fallback set is large on some repository and brings back regex cost. | The Progress Log records the fallback term count on this repository; a large count is a follow-up, not a correctness issue. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
