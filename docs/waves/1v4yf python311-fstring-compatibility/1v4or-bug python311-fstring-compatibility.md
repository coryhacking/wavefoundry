# Restore Python 3.11 Compatibility for Memory Archive Rendering

Change ID: `1v4or-bug python311-fstring-compatibility`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-13
Wave: 1v4yf python311-fstring-compatibility

## Rationale

Wavefoundry supports Python 3.11, but `.wavefoundry/framework/scripts/memory_records.py` currently contains a nested f-string whose outer and inner literals both use single quotes. Python 3.12 and newer accept this grammar, while Python 3.11 raises `SyntaxError: f-string: unmatched '['` during import. The setup flow imports this module while rendering host surfaces, so setup cannot proceed on an otherwise supported Python 3.11 installation.

An inventory that parsed every framework Python source with Python 3.11 found exactly one failure: `memory_records.py:1136`.

## Requirements

1. The archive-manifest renderer must use syntax accepted by Python 3.11 without changing its rendered archive-path value.
2. The framework source must parse successfully under Python 3.11, including `memory_records.py`.
3. Regression coverage must prove the archive manifest renders the fallback archive path when a record omits `archive_path`.
4. The supported-Python compatibility check must be runnable without publishing indexes or mutating production memory records.

## Scope

**Problem statement:** a Python-3.12-only nested f-string prevents `wf setup` from importing `memory_records.py` on the supported Python 3.11 runtime.

**In scope:**

- Replace the incompatible expression in `_render_archive_manifest` with a Python-3.11-compatible equivalent.
- Add or extend focused regression coverage for the fallback archive path and Python-3.11 parsing.
- Document the verification evidence in this change record while implementing.

**Out of scope:**

- Changing Wavefoundry's minimum supported Python version.
- Refactoring unrelated memory-record rendering or archive semantics.
- Altering setup's historical-memory validation gate.

## Acceptance Criteria

- [x] AC-1: `python3.11 -m py_compile .wavefoundry/framework/scripts/memory_records.py` exits successfully.
- [x] AC-2: Parsing every `.wavefoundry/framework/**/*.py` source with Python 3.11 reports zero syntax failures.
- [x] AC-3: The archive-manifest fallback renders `docs/agents/memory/archive/<memory-id>.md` when `archive_path` is absent, with existing explicit archive paths unchanged.
- [x] AC-4: `wf setup` can reach its normal post-render phases on Python 3.11; any historical-memory validation pause is reported as that separate gate rather than a syntax/import failure.

## Tasks

- [x] Update the incompatible nested f-string in `memory_records.py` with the smallest Python-3.11-compatible expression.
- [x] Add focused regression coverage for archive-manifest fallback rendering and Python-3.11 source parsing.
- [x] Run the focused test module, Python-3.11 compile checks, the framework suite, and the docs gate.
- [x] Update this change record's tasks, ACs, and Progress Log with the verification evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Compatibility repair | implementer | — | Small syntax-only implementation in one renderer. |
| Verification | qa-reviewer | Compatibility repair | Exercise Python 3.11 parsing, renderer fallback, and setup entry point. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/memory_records.py`, `.wavefoundry/framework/scripts/tests/test_memory_records.py`

## Affected Architecture Docs

N/A — this is a syntax-compatibility repair within one renderer; no architecture boundary, data flow, or public contract changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Restores importability on the supported runtime. |
| AC-2 | required | Prevents other Python-3.12-only syntax from remaining undiscovered. |
| AC-3 | required | Preserves the archive register's output contract. |
| AC-4 | required | Proves the reported operator workflow is unblocked. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-13 | Planned after Python-3.11 compatibility inventory. | `ast.parse` over `.wavefoundry/framework/**/*.py`: one failure, `memory_records.py:1136`; `python3.11 -m py_compile` reproduces the same error. |
| 2026-08-13 | Implemented the compatibility repair and regression coverage. | `python3.11 -m py_compile .wavefoundry/framework/scripts/memory_records.py` and a Python-3.11 AST inventory of all framework sources both pass; `test_memory_records.py` passes 204 tests; `wf setup` under Python 3.11 completes rendering and server smoke testing, then stops only at the existing historical-memory validation gate; default-interpreter framework suite and docs gardener/lint pass. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- |
| 2026-08-13 | Repair source compatibility rather than raise the minimum runtime. | Python 3.11 is a supported Wavefoundry interpreter and the defect is localized. | Require Python 3.12+ (rejected: breaks the published support contract). |
| 2026-08-13 | Add a Python-3.11 parse regression in addition to renderer behavior coverage. | Behavior tests run under a newer interpreter cannot detect parser incompatibility. | Rely on local setup only (rejected: version-dependent and incomplete). |

## Risks

| Risk | Mitigation |
| --- | --- |
| A quote-only repair changes the fallback path output. | Assert exact fallback and explicit-path strings in focused tests. |
| Other source files contain Python-3.12-only syntax. | Parse the full framework source corpus under Python 3.11. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
