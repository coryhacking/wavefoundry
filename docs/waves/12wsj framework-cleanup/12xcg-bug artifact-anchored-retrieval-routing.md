# Artifact-Anchored Retrieval Routing

Change ID: `12xcg-bug artifact-anchored-retrieval-routing`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: `12wsj framework-cleanup`

## Rationale

The server-side `code_ask` routing currently treats artifact-heavy explanatory questions the same as broad conceptual ones. That causes queries that name a concrete artifact, symbol, or version-like token to spend a round-trip on broad semantic retrieval before the owning script or symbol is found. The routing layer should recognize that shape and go exact-first.

## Requirements

1. Add an artifact-anchored classification in `_classify_question()` and an exact-first routing path in `search_combined()`. A question qualifies as artifact-anchored when it contains **both** an implementation verb (`generated`, `derived`, `stamped`, `computed`, `encoded`, `written`) **and** a concrete artifact cue token. The detection must use a documented, auditable pattern — a small regex or explicit token-type check — committed alongside the implementation so the detection scope can be reviewed and extended without reimplementing the classifier. A token qualifies as an artifact cue if it matches one of: a version suffix pattern (e.g. `\+[a-z0-9]{4,5}`), a dotted filename (`*.py`, `*.toml`, `*.json`), or a `CamelCase` or `snake_case` identifier longer than 4 characters. Questions that carry only a generic noun without a matching artifact cue must not be classified as artifact-anchored.
2. Make the fallback explicit. An exact lookup returns a clear owner when it produces at least one `kind='code'` result. When the exact pass returns no `kind='code'` results, the server must fall through to the broad semantic pass rather than failing open or silently dropping evidence.
3. Preserve the existing broad explanatory routing for general questions that do not carry a clear artifact cue.
4. Add regression coverage for both the exact-first path and the ambiguous-fallback path.

## Scope

**Problem statement:** A question such as "how is the build number generated?" is really asking about a specific artifact contract. The retrieval layer should be able to detect that the answer likely lives in a known owner file and route there first.

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` or the nearest retrieval test file

**Out of scope:**

- agent guidance changes in `docs/agents/guru.md`
- any packaging or build-number semantics beyond retrieval routing

## Acceptance Criteria

- [x] AC-1: Artifact-anchored explanatory questions route exact-first and surface the owner file or symbol before broader prompt/docs matches.
- [x] AC-2: Ambiguous artifact queries do not fail open; they fall back to the broad semantic pass with an explicit no-clear-owner path.
- [x] AC-3: Automated tests cover both the exact-first and fallback behaviors.

## Tasks

- [x] Add artifact-anchored detection to `_classify_question()` in `server_impl.py` (locate by function name): emit `"artifact_anchored"` when the question contains both an implementation verb and a concrete artifact cue token. Commit the detection pattern as a named constant or helper alongside the classifier so it is auditable and extensible.
- [x] Update `search_combined()` in `server_impl.py` (locate by function name): when question type is `"artifact_anchored"`, run the exact pass (`code_keyword` / `code_definition`) first; fall through to the broad semantic pass when no `kind='code'` result is returned.
- [x] Add or adjust tests in `test_server_tools.py` asserting that artifact-anchored questions use exact-first ordering and that ambiguous queries fall back correctly.
- [x] Verify the routing behavior with a targeted `code_ask` call after the code change.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| routing logic | code-reviewer | — | Server-side retrieval change |
| regression tests | qa-reviewer | routing logic | Confirm exact-first and fallback paths |

## Serialization Points

- `server_impl.py`
- retrieval tests that exercise `code_ask`

## Affected Architecture Docs

`docs/agents/guru.md` should remain the docs-side companion for this change, but the server routing change itself does not require architecture-document updates.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core routing improvement |
| AC-2 | required  | Prevents silent misrouting |
| AC-3 | required  | Guards against regression |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-26 | Added to `12wsj` as the server-side companion to the Guru query-formulation fix. | Wave admission |
| 2026-05-26 | Implemented: added `_ARTIFACT_VERBS`, `_ARTIFACT_CUE_RE`, `_extract_artifact_cue()` constants and helpers; updated `_classify_question()` to emit `"artifact_anchored"`; added exact-first routing path with fallback in `search_combined()`; added `_is_test_path()` and `_partition_tests()` for test-file demotion on the artifact-anchored path. 20 new tests cover classifier, extractor, routing, and demotion. MCP verification confirmed `vector_ms: 0` and `question_type: "artifact_anchored"` on live `code_ask` call. All 1638 framework tests pass. | `server_impl.py`, `tests/test_server_tools.py`, `python3 .wavefoundry/framework/scripts/run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-26 | Keep routing changes separate from agent guidance. | The docs layer and server layer solve different parts of the retrieval problem. | Fold all behavior into `docs/agents/guru.md` |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Artifact detection is too loose | Detection requires both a concrete artifact cue and an implementation verb (Req-1); neither alone is sufficient |
| Ambiguous queries can still be noisy | Fallback triggers when exact pass returns no `kind='code'` result (Req-2); broad semantic pass is always the safety net |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
