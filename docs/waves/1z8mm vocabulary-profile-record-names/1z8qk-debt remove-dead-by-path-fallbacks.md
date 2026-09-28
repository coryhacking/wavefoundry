# Remove Dead By-Path Import Fallbacks

Change ID: `1z8qk-debt remove-dead-by-path-fallbacks`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-27
Wave: 1z8mm vocabulary-profile-record-names

## Rationale

Two modules import a sibling by name and, on `ImportError`, fall back to loading it by file path. Neither fallback can run:

- `_tag_utils.py` falls back to loading `record_paths.py` by path. That load fails: `record_paths` defines a dataclass, and a module executed from a spec without a `sys.modules` entry cannot resolve its own dataclass. It has been broken since wave `1y0gz` (found during wave `1z8mm`). It is also unreachable: `chunker` imports `index_compatibility` and `marker_namespaces` by name before `_tag_utils`, and the server imports `record_paths` by name at startup before it loads `_tag_utils` through `_load_script`.
- `chunker.py` falls back to loading `_tag_utils.py` by path. It is unreachable for the same reason: `chunker` imports `index_compatibility` and `marker_namespaces` by name a few lines earlier, so a process without the scripts directory on `sys.path` fails before the fallback.

Dead fallbacks suggest a supported loading mode that does not exist, and the `_tag_utils` one would have to grow a `vocabulary_profile` preload to keep pretending.

## Requirements

1. `_tag_utils.py` imports `record_paths` by name only.
2. `chunker.py` imports `_tag_utils` by name only.
3. Behavior is otherwise unchanged: the same tag inference and chunking.

## Scope

**Problem statement:** two import fallbacks are unreachable, and one of them cannot work.

**In scope:**

- the two `except ImportError` branches and the comment that describes the first.

**Out of scope:**

- `server_impl._load_script` and other loaders;
- any other by-path loading.

## Acceptance Criteria

- [x] AC-1: neither module contains a by-path fallback, and both import their sibling by name.
- [x] AC-2: the change's own suites pass, and the documents this change edits validate.

## Tasks

- [x] Remove both fallbacks.
- [x] Run the suites that cover tag inference and chunking; do not bump `CHUNKER_VERSION` (no chunk output changes); reload the MCP server after the edit, since `chunker` is an index source and a running server reports `index_runtime_stale` until reloaded; CHANGELOG is not needed (no user-visible change).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Removal | implementer | readiness | Two small edits |
| Review | combined reviewer | Removal | Code and QA |

## Serialization Points

- `.wavefoundry/framework/scripts/_tag_utils.py`, `.wavefoundry/framework/scripts/chunker.py`

## Affected Architecture Docs

`N/A`: removes unreachable code only.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The change itself |
| AC-2 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Implemented: both modules import their sibling by name; `CHUNKER_VERSION` unchanged. Delivery review: all lanes approved | `test_chunker` (579 tests), `test_record_layout_cold_sites`, `test_record_layout_census` |
| 2026-09-27 | Readiness review: both claims hold (the `_tag_utils` fallback cannot load; every loader of `chunker` and `_tag_utils` already has the scripts directory on `sys.path`); K3 adopted into Tasks. All four lanes approved | readiness review (probes with `-P` against HEAD and the current tree) |
| 2026-09-27 | Planned at the operator's request after wave `1z8mm` found the `_tag_utils` fallback broken; the `chunker` fallback was found unreachable on inspection | a by-path load of `_tag_utils.py` in an isolated interpreter fails at HEAD in the `record_paths` dataclass |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | Remove rather than repair | Nothing reaches either fallback; repairing it would add a `vocabulary_profile` preload for a mode no caller uses | Repair the `_tag_utils` fallback |

## Risks

| Risk | Mitigation |
| --- | --- |
| A caller does load `chunker` or `_tag_utils` without the scripts directory on `sys.path` | Such a caller already fails today (earlier by-name imports, or the dataclass error); the full suite and the index build exercise the real paths |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
