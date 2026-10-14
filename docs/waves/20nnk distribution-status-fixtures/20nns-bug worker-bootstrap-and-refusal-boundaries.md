# Harden worker startup and public refusal diagnostics

Change ID: `20nns-bug worker-bootstrap-and-refusal-boundaries`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-14
Wave: `20nnk distribution-status-fixtures`

## Rationale

The guard module executes from source, but its sitecustomize bootstrap still uses normal interpreter startup imports. worker_environment currently adds that bootstrap without checking its adjacent cache. Separately, project_state_publication_lock exposes the underlying guard message through its exception string even though detail is path-free. Both are narrow worker-boundary repairs.

## Requirements

1. Before producing a guarded child environment, inspect the owned bootstrap location and refuse an existing adjacent __pycache__ or legacy bootstrap bytecode carrier without following links or deleting it. Cover all guarded launch callers, including nested workers.
2. Preserve source guard execution, bytecode-prefix opt-out and legitimate sitecustomize chaining. Document that prelaunch validation is cooperative hygiene, not protection against hostile same-user races or startup imports already executed.
3. Use a stable path-free ProjectPublicationUnavailable message as well as detail for guard refusals, including malformed protection metadata; public rendering must not substitute the raw cause.
4. Retain protected-root refusal behavior and exception type. No unguarded fallback after bootstrap refusal, automatic recursive cleanup or broadened production use of test variables.

## Scope

test_worker_guard, bootstrap launch integration, review_evidence refusal translation, focused subprocess/publication tests and threat-model documentation. No new sandbox, global Python cache policy or source authentication.

## Acceptance Criteria

- [x] AC-1: A disposable bootstrap carrying cached bytecode is refused before a guarded child starts; clean bootstrap and nested/chained startup controls preserve guard behavior.
- [x] AC-2: Refused bootstrap state is preserved for diagnosis, linked/nonregular carriers fail safely, and no unguarded fallback launches.
- [x] AC-3: Both string and structured public refusal forms omit scratch absolute-root/account identifiers while retaining the handled exception type and refusing publication.
- [x] AC-4: Documentation distinguishes prelaunch hygiene from authentication and identifies the remaining race and pre-startup limits.

## Tasks

- [x] Trace all guarded environment producers and add a bounded no-follow bootstrap hygiene check before launch.
- [x] Replace public guard refusal text with stable path-free wording; preserve handled type and protection behavior.
- [x] Exercise finite scratch subprocess and exception-rendering controls; update threat-model limits without adding permanent artifacts.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | Readiness approval | Sole source write owner |
| Independent review | Required specialist lanes | Reviewable implementation | Read-only; report findings to coordinator |

## Serialization Points

Only the implementer edits the declared targets after readiness. Reviewers are read-only; the coordinator owns lifecycle records. Shared runner, server, policy, seed and prompt changes serialize with adjacent waves. Seed/default/prompt changes require existing edit guards and renderer ownership; do not hand-edit generated regions.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/test_worker_guard.py`
- `.wavefoundry/framework/scripts/test_worker_bootstrap/sitecustomize.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_repo_guard.py`
- `.wavefoundry/framework/scripts/tests/test_bytecode_cache.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/cross-cutting-concerns.md`

## Affected Architecture Docs

docs/contributing/build-and-verification.md and docs/architecture/cross-cutting-concerns.md: bootstrap bytecode trust and public refusal diagnostics.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-2 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-3 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-4 | required | Establishes the scoped behavior or preserves its boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Planned from current source inspection; implementation and qualification pending. | Requirements and declared review targets above. |
| 2026-10-14 | Observe: Added the existing bytecode-cache test file to review targets because it owns the scratch bootstrap and chaining fixtures needed by the admitted startup controls. | WorkerBootstrapSourceTests; new refusal controls must call worker_environment before launch, while existing direct-PYTHONPATH controls intentionally bypass that producer. |

| 2026-10-14 | Readback: Before worker launch, inspect the owned bootstrap path without resolving away links and refuse adjacent bytecode caches/legacy bytecode without deleting anything. Publish a path-free refusal message and detail while preserving handled exception type, nested protection and chained customization. | Guard, review_evidence, admitted worker/bytecode/review tests and threat docs. This is cooperative startup hygiene, not same-user race isolation or authentication. |

| 2026-10-14 | Observe: ARCH-DEL-BOOTSTRAP reproduces the cache-enabled fixture producer retaining the inherited source bootstrap while removing bytecode opt-outs. Python writes adjacent shim bytecode, and the correct subsequent prelaunch refusal stops qualification. | AC-1 reopened. Preserve refusal and diagnostic artifact. Proposed bounded fixture-only startup prefix retains guard markers/path chaining and intended cache behavior; verify actual inherited protection and canonical per-file execution. No production cleanup or unguarded fallback. |

| 2026-10-14 | Repair cycle 1 verification: Whole bytecode file passes 67 guarded tests, zero skips. Removing private startup prefix fails test_writable_probe_preserves_nested_guard_and_chain_without_adjacent_cache; removing nested sensor -B fails test_configure_exports_nothing_and_a_sensor_child_gets_no_prefix (each one assertion failure, no errors/skips). Both mutations use disposable copied bootstrap; production guard unchanged and live source bootstrap clean. Two diagnosed source artifacts retained outside repository with verified hash. | Updated 28-file fingerprint 42f2f93278db003d75ba896a6046ad5b0402bd87be890cf44b02adfd12cae8f4; independent reverification and final combined qualification pending. |

| 2026-10-14 | Combined qualification caught a default-layout literal in the repaired bytecode sensor fixture. Replace it with the existing profile-resolved record root within the already admitted test owner; retain bootstrap refusal and marker controls. | test_profile_literal_census identifies only test_bytecode_cache.py:1568; no census exemption or production guard change. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Select prelaunch refusal of cached bootstrap carriers and path-free boundary translation. | Refuse preexisting bootstrap bytecode before guarded child launch and keep publication refusal text free of local paths. | Document adjacent-cache trust only: no runtime hygiene improvement. Build a new source-authenticated launcher: materially broader than a cooperative test guard needs. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Contract regression or scope expansion | Startup cannot be fixed after sitecustomize has already imported, and a same-user race remains. Validate before child launch, state limitations and avoid claiming complete hostile-code isolation. |

## Session Handoff

Planned only. Prepare/readiness must pass before code edits. Keep durable decisions and final command/results in wave.md; compact execution detail stays in ignored cache or temporary storage. No new permanent evidence folder. See docs/agents/session-handoff.md for sequencing.
