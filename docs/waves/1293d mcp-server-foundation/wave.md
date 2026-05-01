# Wave — MCP Server Foundation

Owner: Engineering
Status: closed
Last verified: 2026-04-30
Completed At: 2026-04-29

wave-id: `1293d mcp-server-foundation`
Title: MCP Server Foundation

## Objective

Implement the Wavefoundry MCP server and semantic index as the foundation for scalable
agent operation across large target repositories. Deliver search and retrieval, change
creation tools, and framework operation tools in the first change. Define the
transactional wave lifecycle state machine as a planned stub for the follow-on change.

## Coordinator

wave-coordinator

## Participants


| Role                         | Lane                       | Owns                                                                                           |
| ---------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------- |
| implementer                  | implement                  | `12926-feat wavefoundry-mcp-index`                                                             |
| implementer                  | implement                  | `12993-feat mcp-guided-tool-contracts`                                                         |
| architecture-reviewer        | review                     | `12926-feat wavefoundry-mcp-index` — MCP tool contracts, index design                          |
| architecture-reviewer        | review                     | `12993-feat mcp-guided-tool-contracts` — guided MCP contract, response envelopes               |
| code-reviewer                | review                     | `12926-feat wavefoundry-mcp-index` — scripts, server                                           |
| code-reviewer                | review                     | `12993-feat mcp-guided-tool-contracts` — server contract migration, compatibility wrappers     |
| docs-contract-reviewer       | review                     | `12993-feat mcp-guided-tool-contracts` — MCP behavioral contract and response envelope         |
| qa-reviewer                  | review                     | `12993-feat mcp-guided-tool-contracts` — contract test coverage and retry/dry-run verification |
| security-reviewer            | review                     | `12993-feat mcp-guided-tool-contracts` — allowed roots and untrusted-content labeling          |
| performance-reviewer         | review                     | `12926-feat wavefoundry-mcp-index` — index build and query paths                               |
| performance-reviewer         | review                     | `12993-feat mcp-guided-tool-contracts` — recovery-loop cache behavior                          |
| factor-12-admin-processes    | review (advisory)          | `12926-feat wavefoundry-mcp-index` — CLI tool contracts                                        |
| factor-13-api-first          | review (advisory)          | `12926-feat wavefoundry-mcp-index` — MCP tool surface contracts                                |
| factor-13-api-first          | review (advisory)          | `12993-feat mcp-guided-tool-contracts` — structured MCP API ergonomics                         |
| framework-operator (persona) | design review / acceptance | `12926-feat wavefoundry-mcp-index`                                                             |
| framework-operator (persona) | design review / acceptance | `12993-feat mcp-guided-tool-contracts`                                                         |


## Changes

Change ID: `12926-feat wavefoundry-mcp-index`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `1293b-feat mcp-wave-lifecycle`
Previous Change Status: `ready`
Change Status: `complete`
Depends On: `12926-feat wavefoundry-mcp-index`

Change ID: `12993-feat mcp-guided-tool-contracts`
Previous Change Status: `ready`
Change Status: `complete`
Depends On: `12926-feat wavefoundry-mcp-index`

## Dependencies

- No external wave dependencies.
- `1293b-feat mcp-wave-lifecycle` must not begin implementation until
`12926-feat wavefoundry-mcp-index` is complete and its MCP server interface is stable.
- `12993-feat mcp-guided-tool-contracts` depends on the `12926` server baseline but may
be implemented in the same wave once the initial MCP tools are available.

## Current Assumptions

- A-1 (frozen): `fastembed` provides cross-platform ONNX wheels for Win x64, macOS
arm64/x64, Linux x64/arm64 without C extension compilation.
- A-2 (frozen): `bge-small-en-v1.5` is available in the fastembed model registry.
- A-3 (tentative): Index build time on a large repo (>5k files) is acceptable via
incremental rebuild; full rebuild is an infrequent operator operation.
- A-4 (tentative): `1293b-feat mcp-wave-lifecycle` will be fully planned within the
same wave after `12926` implementation is underway and the MCP server interface
is visible.

## Outputs Produced or Expected

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/index/` (runtime artifact, not checked in)
- Updated `render_platform_surfaces.py` with MCP config emission
- Updated post-edit hook with incremental index rebuild
- Updated `AGENTS.md` startup instructions routing through MCP tools
- Updated architecture docs: current-state, domain-map, data-and-control-flow
- `1293b-feat mcp-wave-lifecycle` planned and moved to active implementation after
`12926-feat wavefoundry-mcp-index` completion
- Guided MCP contract update: discovery tool, response envelope, breadcrumbs, dry-run
mutation modes, compatibility wrapper strategy

## Protected Surfaces

- `AGENTS.md` and `docs/prompts/` — require `framework_edit_allowed` guard before editing; single write owner
- `docs/prompts/prompt-surface-manifest.json` — coordinator confirmation before any write
- `.wavefoundry/framework/seeds/` — require `seed_edit_allowed` guard; `12926` does not edit seeds

## Review Checkpoints

- **Prepare wave — readiness verdict (2026-04-29): READY**
  - `12926-feat wavefoundry-mcp-index`: all required sections present and complete;
  AC Priority populated (12 required, 5 important); review lanes assigned; change doc
  relocated to wave directory. Change Status: `planned` → `ready`.
  - `1293b-feat mcp-wave-lifecycle`: admitted as stub; full planning deferred pending
  `12926` implementation. AC Priority and review lanes deferred to planning pass.
  Implementation must not begin from this stub.
  - Product-owner acknowledgment: framework-operator persona — wave installs a new MCP
  server as part of the standard framework install/upgrade, shifting operator-facing
  product behavior. Advisory review required before merge of `12926`.
- **Prepare wave — readiness verdict (2026-04-30): BLOCKED for expanded admit set**
  - `12993-feat mcp-guided-tool-contracts`: change doc has required planning sections
  and AC Priority populated, but cannot pass readiness while the formal MCP tool
  contract spec is missing at `docs/specs/mcp-tool-surface.md`.
  - Required review lanes for `12993` are now recorded: architecture-reviewer,
  docs-contract-reviewer, code-reviewer, qa-reviewer, security-reviewer,
  performance-reviewer, factor-13-api-first, and framework-operator persona.
  - `1293b-feat mcp-wave-lifecycle` remained a stub/deferred change and was not
  implementation-ready at this checkpoint.
  - Product-owner / framework-operator acknowledgment: the admission delta affects MCP
  API behavior; operator requested the change, but delivery-scope sign-off remains
  required after the MCP tool contract spec exists and before implementation merge.
- **Spec prerequisite update (2026-04-30):**
  - Created `docs/specs/mcp-tool-surface.md` and removed it from `docs/missing-docs.md`.
  - Next `Prepare wave` pass should re-evaluate `12993` readiness against that spec and
  the recorded review lanes.
- **Prepare wave — readiness verdict (2026-04-30): READY for `12993`**
  - `12993-feat mcp-guided-tool-contracts`: formal MCP tool contract spec now exists at
  `docs/specs/mcp-tool-surface.md`; planning sections, AC Priority, and required
  review lanes are present. Change Status: `planned` -> `ready`.
  - `1293b-feat mcp-wave-lifecycle` remained deferred/stubbed and was not part of the
  implementation slice for this pass.
  - Product-owner / framework-operator acknowledgment: operator requested the guided
  MCP contract expansion; design-review and delivery-scope sign-off remain required
  before merge of operator-facing MCP contract changes.
- architecture-reviewer sign-off on MCP tool contracts and index design before implementation begins
- architecture-reviewer sign-off on the guided response envelope before broad MCP tool migration
- performance-reviewer sign-off on index build and query paths before merge
- factor-13 advisory review of MCP tool surface contracts (advisory)
- factor-13 advisory review of `12993` structured MCP API ergonomics (advisory)
- factor-12 advisory review of CLI tool contracts — `setup_index.py`, `indexer.py`, `server.py` (advisory)
- framework-operator persona acceptance of operator-facing install/upgrade changes
- **Implementation state update (2026-04-29):**
  - `1293b-feat mcp-wave-lifecycle` moved to `ready` after dependency
    `12926-feat wavefoundry-mcp-index` reached `complete` and the planned lifecycle
    mutation surface/tests landed for this wave slice.
  - `12993-feat mcp-guided-tool-contracts` moved to `ready` after contract slices
    (envelope, discovery, anchors, validation strictness, cache semantics) landed.

## Review Evidence

- architecture-reviewer sign-off (12926, 12993): approved
- code-reviewer sign-off (12926, 12993): approved
- docs-contract-reviewer sign-off (12993): approved
- qa-reviewer sign-off (12993): approved
- security-reviewer sign-off (12993): approved
- performance-reviewer sign-off (12926, 12993): approved
- factor-13-api-first advisory review (12926, 12993): complete
- factor-12-admin-processes advisory review (12926): complete
- framework-operator acceptance (12926, 12993): approved

## Full Wave Review (2026-04-30)

### Scope
All three changes (`12926`, `1293b`, `12993`). 267 framework tests pass. `docs-lint` clean.

### AC Verification

**12926 — required ACs:**
- AC-1 ✅ `setup_index.py` dependency check + isolated venv help (covered by `test_setup_index.py`)
- AC-2 ✅ Incremental rebuild: hash-based skip in `indexer.py`; `test_indexer.py` verifies changed-only rebuild
- AC-3 ✅ `docs_search` semantic path wired; lexical fallback when index not ready
- AC-5 ✅ `seed_get` by name/slug (covered by server tests)
- AC-6 ✅ `wave_current` parses active wave state; "no active wave" handled
- AC-7 ✅ `wave_get_prompt` returns full prompt text
- AC-8 ✅ `wave_validate` returns structured pass/fail matching `docs_lint.py`
- AC-9 ✅ `wave_new_feature` scaffolds plan doc in one call
- AC-10 ✅ All 10 kinds (`bug`, `feat`, `enh`, `ref`, `change`, `doc`, `debt`, `task`, `maint`, `ops`) registered; `test_all_tools_registered` enumerates them
- AC-12 ✅ `wave_sync_surfaces` regenerates platform configs and returns written paths
- AC-13 ✅ Claude Code post-edit hook fires background `indexer.py` subprocess; hook does not block edit pipeline. **Note:** git hooks (post-commit, post-merge, post-rewrite, post-checkout) are generated at `.wavefoundry/git-hooks/` but require `git config core.hooksPath .wavefoundry/git-hooks` to activate — this is a manual operator step not yet documented in setup/contributing docs.
- AC-14 ✅ `.mcp.json` and `.junie/mcp/mcp.json` both contain valid wavefoundry server entries
- AC-15 ✅ Global fastembed cache via default platform cache dir; no per-project re-download
- AC-16 ✅ 267/267 tests pass
- AC-17 ✅ `--watch` without `watchdog` exits cleanly with install instruction

**12993 — required ACs:**
- AC-1 ✅ `wave_help()` returns structured workflow catalogue
- AC-2 ✅ `wave_help(goal="plan_feature")` returns recommended chain with usage hints
- AC-3 ✅ All tools return `{status, data, diagnostics, next_tools, usage}` envelope
- AC-4 ✅ `wave_change_create(mode="dry_run")` reports planned path without writing
- AC-5 ✅ `wave_change_create(mode="create")` is repeat-safe; repeat calls return `already_exists` diagnostic
- AC-6 ✅ `wave_new_*` wrappers delegate to consolidated creation path
- AC-9 ✅ `resolve_path_under_root` rejects parent-escape paths; tests cover traversal rejection
- AC-10 ✅ `trust_label` field in all search/read results (`TRUSTED_FRAMEWORK`, `TRUSTED_PROJECT_METADATA`, `UNTRUSTED_PROJECT_CONTENT`)
- AC-11 ✅ Tests cover discovery, envelopes, dry-run, wrappers, anchors, root rejection
- AC-13 ✅ Core verbs documented in `wave_help` catalogue
- AC-14 ✅ Prefix contract enforced at registration; `test_registered_tools_obey_prefix_contract` would fail on violations
- AC-15 ✅ `wave_map` resolves `doc:`/`code:`/`seed:` stable addresses from search `result_id`
- AC-16 ✅ Stable diagnostic field names (`code`, `message`, `recovery_tools`, `recovery_usage`) across all tools
- AC-17 ✅ `mode` enum (`dry_run` / `create`) shared across lifecycle mutation tools
- AC-18 ✅ `_ensure_no_extra_args` guards on all MCP tool handlers; unknown kwargs return diagnostic
- AC-19 ✅ `wave_help` designated as audit/recovery landing tool; cited in mutation responses
- AC-20 ✅ `McpRepoCache` caches wave/plan lists and prompt text keyed by mtime fingerprints; `wave_help` catalogue uses `lru_cache`; index `_loaded` state resets on mutation
- AC-21 ✅ Repeat mutation calls return `already_exists` diagnostic with existing path and next recovery tool

**1293b — ACs:**
- AC-1–7 ✅ Lifecycle tools (`wave_create_wave`, `wave_add_change`, `wave_remove_change`, `wave_prepare`, `wave_pause`, `wave_review`, `wave_close`) implemented and tested

### Issues Found and Resolved

**Issue 1 — Performance regression (FIXED):**
`docs_search_response()` unconditionally called `index.docs_health()` on every search request, triggering an O(repo) filesystem walk + SHA-256 hash pass before any retrieval work. Root cause: pre-flight staleness check was wired into the hot search path rather than relying on exception-based fallback.

Fix: removed `docs_health()` pre-flight from `docs_search_response()`. Fallback is now fully exception-driven: `IndexNotReadyError` → lexical fallback with `index_not_ready` diagnostic; `SemanticModelUnavailableOfflineError` → lexical fallback. `docs_health()` remains available as an explicit standalone call. The `index_stale` and `index_missing` pre-flight diagnostic codes are retired; staleness detection is delegated to background reindex hooks.

Affected tests: `test_docs_search_reports_stale_index_and_uses_lexical_fallback` and `test_docs_search_reports_missing_index_and_uses_lexical_fallback` replaced by `test_docs_search_calls_semantic_search_directly_without_health_preflight` (asserts `docs_health` is never called) and `test_docs_search_falls_back_to_lexical_on_index_not_ready` (asserts `IndexNotReadyError` → lexical fallback). Test count: 256 → 267.

**Issue 2 — Stale architecture docs (FIXED):**
`docs/architecture/data-and-control-flow.md` Path 6 step 3 and `docs/architecture/current-state.md` risk row both described `docs_search` as checking layer health on every call. Both updated to accurately describe the exception-driven fallback and the deliberate decision to avoid per-query repo walks.

### Open Operational Gap (non-blocking)

Git hooks at `.wavefoundry/git-hooks/` (post-commit, post-merge, post-rewrite, post-checkout) are generated and correct but require `git config core.hooksPath .wavefoundry/git-hooks` to activate. This manual step is not yet documented in setup or contributing docs. The primary incremental-reindex path (Claude Code post-edit hook) is unaffected. Recommend documenting the git hooks activation step in `docs/contributing/build-and-verification.md` in the `1297t` wave alongside the other MCP routing updates.

## Journal Refs

- `docs/agents/journals/framework-operator.md`

## Journal Watchpoints

- Watchpoint: fastembed wheel unavailable on a target platform — A-1 invalidated; block implementation and reassess embedding stack
- Watchpoint: incremental index build time unacceptable on large repo — A-3 may need ANN fallback; block merge until resolved
- Watchpoint: `1293b` planning reveals MCP server interface changes needed — block `12926` merge until interface is restabilized

## Completion Criteria

Close this wave only when all items below are satisfied:

- `12926-feat wavefoundry-mcp-index` implemented, reviewed, and all required ACs passing
- `1293b-feat mcp-wave-lifecycle` either:
  - completed in this wave, or
  - explicitly deferred with documented compatibility/hand-off expectations
- `12993-feat mcp-guided-tool-contracts` either:
  - completed in this wave, or
  - explicitly deferred with documented compatibility expectations
- Required review-lane sign-offs for all non-deferred changes are recorded in this
wave record (including framework-operator acceptance where required)
- Architecture docs updated and docs-lint passing
- AGENTS.md updated to route through MCP tools

## Handoff or Next-Wave Notes

- The follow-on wave for `1293b` implementation should treat the `12926` MCP server
interface as a hard contract; changes to it require re-review.
- BM25 hybrid search (deferred from `12926`) is a candidate for a subsequent wave
once semantic search quality is validated in practice.

## Wave Summary

- Closed on 2026-04-29 after completing the MCP index baseline (`12926`), guided
  MCP contract hardening (`12993`), and lifecycle mutation implementation slice
  (`1293b`) with passing framework test suite and docs-lint.
- Delivered a guided MCP contract with stable anchors, trust labels, strict
  diagnostics, cache semantics, and lifecycle mutation tools (`wave_create_wave`,
  `wave_add_change`, `wave_remove_change`, `wave_prepare`, `wave_pause`,
  `wave_review`, `wave_close`).
- Remaining candidate work (not required for this wave close): BM25 hybrid search
  and deeper lifecycle orchestration automation beyond the delivered mutation scope.