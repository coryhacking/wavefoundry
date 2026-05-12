# Packaging: Incremental Framework Index Update

Change ID: `12j9a-enh package-framework-index-incrementally`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

Packaging currently rebuilds the packaged framework docs index with `full=True` every time. That is reliable, but it is slower than necessary when only a small portion of the framework docs or seeds changed. The indexer already supports incremental updates and automatically escalates to a full rebuild when model, chunker, or walker/schema drift is detected, so packaging should use that faster path by default.

## Requirements

1. Framework packaging should request an incremental docs-index update by default instead of forcing a full rebuild every time.
2. Model/chunker/walker drift and missing-index cases must still fall back to a full rebuild through the existing indexer behavior.
3. Packaging tests must prove the packer requests the incremental path and still includes the generated framework index in the zip.
4. Verification must pass.

## Scope

**Problem statement:** package builds pay full framework docs reindex cost even when the existing packaged index can be updated incrementally.

**In scope:**

- `.wavefoundry/framework/scripts/build_pack.py`
  - Request incremental framework docs index updates during packaging
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
  - Add regressions for incremental packaging behavior

**Out of scope:**

- Redesigning the indexer fallback logic
- Changing project index build behavior

## Acceptance Criteria

- AC-1: Packaging requests incremental framework docs index updates by default.
- AC-2: Packaging still relies on the existing indexer fallback path when version/schema drift requires a full rebuild.
- AC-3: Packaged framework index artifacts are still included in the zip.
- AC-4: Verification passes.

## Tasks

- Change framework packaging to request incremental docs index updates
- Add regressions for incremental build-pack behavior
- Run targeted packaging tests and docs lint

## Affected Architecture Docs

N/A - packaging strategy refinement only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Reduces package-time index work in the common case |
| AC-2 | required | Preserves correctness under version/schema drift |
| AC-3 | required | Keeps the shipped framework index intact |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created for incremental packaged framework index updates with version/schema-drift fallback preserved in the indexer. | `build_pack.py`; `indexer.py`; `test_build_pack.py` |
| 2026-05-11 | Packaging now requests incremental framework docs index updates by default and leaves model/chunker/walker drift fallback to the shared indexer. Packaging tests, docs lint, and the full framework suite passed. | `build_pack.py`; `test_build_pack.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_build_pack.py'`; `./.wavefoundry/bin/docs-lint`; `python3 -B .wavefoundry/framework/scripts/run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Use the indexer's existing incremental update path during packaging instead of adding package-specific rebuild logic | The indexer already detects model/chunker/walker drift and escalates to a full rebuild when needed | Keep always-full rebuilds (rejected: slower than necessary) |

## Risks

| Risk | Mitigation |
|------|------------|
| Packaging could accidentally skip a needed full rebuild | Keep fallback logic in the shared indexer and cover the packaging call contract with tests |
| Test coverage could prove only inclusion, not call mode | Assert the packer requests `full=False` explicitly in packaging tests |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
