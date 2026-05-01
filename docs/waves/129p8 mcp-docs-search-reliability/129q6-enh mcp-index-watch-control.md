# MCP-Managed Index Watch Control

Change ID: `129q6-enh mcp-index-watch-control`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-04-30
Wave: `129p8 mcp-docs-search-reliability`

## Rationale

Wavefoundry already has two ways to keep the docs index fresh:

1. hook-driven background reindex in clients such as Claude Code and Cursor
2. a CLI watcher mode in `indexer.py --watch`

That leaves a clear gap in Codex-like environments: the native repo hooks do not run, so semantic search can fall behind unless the operator manually reruns `setup_index.py` or starts a watcher by hand.

The existing watcher capability should not stay as an undocumented side path. The framework needs an explicit MCP control surface so agents can:

- detect whether background index watching is active
- start it when the current environment does not run hooks
- stop it cleanly
- understand whether the watcher is healthy or missing dependencies

It also needs a mutation-time freshness path. When MCP tools themselves create or modify indexed docs, the framework should not rely on an external editor hook that may never fire. MCP-driven writes should either trigger a background incremental reindex immediately or ensure a watcher is running so the new content is indexed shortly after the mutation.

This should be implemented as MCP-managed control over the existing watcher process, not by turning the stdio MCP server itself into a long-lived filesystem daemon. The server is request-driven and client lifecycle is not stable enough to make in-process watching the primary design.

## Requirements

1. Wavefoundry must expose an MCP control path for background index watching in environments where native post-edit hooks do not run.
2. The control path must be built around the existing repo-local watcher capability in `indexer.py --watch`, or a direct successor with equivalent semantics, rather than a separate duplicated watcher implementation.
3. The stdio MCP server must remain request-driven. This change must not require `server.py` to keep an always-on in-process filesystem observer as its primary runtime model.
4. The tool surface must include, at minimum:
   - watcher status
   - watcher start
   - watcher stop
   - manual rebuild for project and framework index layers
   - rebuild statistics sufficient to confirm what was indexed
5. Start semantics must be repeat-safe. Starting an already running watcher should not create duplicate watcher processes for the same repository root.
6. Status semantics must report whether:
   - a watcher is running for the current repo root
   - the watcher was started by Wavefoundry control tooling
   - required watcher dependencies are missing
   - the last known watcher startup failed
7. Stop semantics must shut down only the watcher associated with the targeted repository root and must not kill unrelated processes.
8. The design must work for Wavefoundry self-hosting and for seeded target repositories without assuming a specific editor or client.
9. The control path must provide clear recovery guidance when watcher dependencies such as `watchdog` are not installed.
10. The watcher path must preserve existing manual recovery paths:
   - `python3 .wavefoundry/framework/scripts/setup_index.py`
   - hook-driven incremental rebuild where supported
11. If watcher state is persisted on disk, the persistence format and location must be explicit, repo-local, and safe to ignore in git.
12. The MCP contract, architecture docs, and operator-facing verification docs must explain when to prefer:
   - hook-driven indexing
   - watcher-driven indexing
   - manual rebuild
13. Additional project-local index roots must be configurable in `docs/workflow-config.json` using a generic path-prefix contract, not a Wavefoundry-specific boolean.
14. The generic config surface must let self-hosting or atypical repos opt specific excluded paths into the project semantic index without forcing those paths on every seeded repository.
15. Manual rebuild paths that operate through MCP or `setup_index.py` must honor the configured additional project index prefixes consistently.
16. When a mutating MCP tool changes content that belongs in the docs index, Wavefoundry must ensure a background freshness action occurs without relying on editor hooks. Acceptable implementations are:
   - trigger a background incremental reindex for the affected repo root, or
   - auto-start or confirm a watcher for that repo root
17. Mutation-triggered freshness behavior must be repeat-safe and must not spawn unbounded duplicate background jobs for the same repo root.
18. The design must identify which MCP tools participate in mutation-triggered freshness, such as change creation, wave lifecycle mutations, docs gardening, or other indexed-doc writers.
19. This change must not expand into general MCP job orchestration, remote daemon control, or replacing the existing post-edit hook system.

## Scope

**Problem statement:** Codex and other non-hook environments currently have no first-class Wavefoundry mechanism to keep the semantic index fresh in the background, even though the repository already contains a watcher implementation in `indexer.py`.

**In scope:**

- MCP tool contract for index watcher start / stop / status
- MCP tool contract for manual project or framework index rebuild
- reuse or hardening of `indexer.py --watch`
- watcher process ownership model for one repo root
- repeat-safe startup and clean shutdown behavior
- mutation-triggered background index freshness after MCP writes to indexed docs
- explicit workflow-config policy for additional project index prefixes
- dependency and failure diagnostics for watcher startup
- architecture and operator-doc updates for hook vs watcher vs manual rebuild paths
- tests covering watcher control semantics where practical

**Out of scope:**

- converting `server.py` into an always-on daemon
- replacing Claude/Cursor hook-driven indexing
- background watching for arbitrary non-index framework jobs
- remote or multi-repo watcher orchestration from one process
- redesigning semantic search itself

## Acceptance Criteria

- AC-1: A Wavefoundry MCP caller can ask whether background index watching is active for the current repo root and receive a structured answer.
- AC-2: A Wavefoundry MCP caller can start background index watching for the current repo root without manually invoking `indexer.py --watch`.
- AC-3: Repeated watcher start requests for the same repo root are safe and do not create duplicate watcher processes.
- AC-4: A Wavefoundry MCP caller can stop the watcher for the current repo root cleanly.
- AC-5: When watcher dependencies are missing, the MCP response reports that state clearly and gives a concrete recovery command instead of failing silently.
- AC-5a: A Wavefoundry MCP caller can trigger a project-index rebuild explicitly without dropping to shell.
- AC-5b: A Wavefoundry MCP caller can trigger a framework-index rebuild for packaged seeds/docs explicitly without dropping to shell.
- AC-5c: Successful manual rebuild responses include structured index statistics so operators can see how many files and chunks are currently indexed, and whether the rebuild was a no-op.
- AC-6: The design preserves existing hook-driven indexing behavior and does not require clients with working hooks to adopt the watcher path.
- AC-5d: Additional project index roots can be declared explicitly in `docs/workflow-config.json` using a generic prefix list, and self-hosting repos can use that path to include framework implementation code in project code search without changing the default for other repos.
- AC-5e: MCP/manual rebuild paths honor configured additional project index prefixes consistently.
- AC-7: Operator-facing docs explain the intended indexing modes for:
  - hook-capable clients
  - non-hook clients such as Codex
  - manual rebuild fallback
- AC-8: Tests cover duplicate-start protection, status reporting, and missing-dependency diagnostics at minimum.
- AC-9: After a mutating MCP tool writes indexed docs, Wavefoundry triggers a background freshness action without requiring an editor hook.
- AC-10: Mutation-triggered freshness is repeat-safe and does not create unbounded duplicate watcher or reindex processes for the same repo root.

## Tasks

- Confirm the current watcher implementation in `indexer.py --watch` is sufficient as the execution primitive, or define the minimal hardening needed before MCP controls are layered on top.
- Decide the watcher ownership model:
  - detached subprocess launched by MCP tool
  - PID/state file recorded in repo-local runtime state
  - other repeat-safe control mechanism
- Define the MCP tool names and response contract for watcher start / stop / status.
- Define the MCP tool name and response contract for manual project and framework index rebuild.
- Define the rebuild statistics returned to MCP callers after manual project or framework rebuilds.
- Define the generic workflow-config contract for additional project index prefixes.
- Decide whether watcher state belongs under `.wavefoundry/index/`, another repo-local runtime directory, or an adjacent explicit state file.
- Implement duplicate-start protection for a single repo root.
- Implement clean stop behavior scoped to the targeted repo root only.
- Add clear missing-dependency and startup-failure diagnostics.
- Decide whether watcher startup should preflight the docs index or require `setup_index.py` first.
- Decide the mutation-time freshness policy:
  - always trigger one background incremental reindex after qualifying MCP writes
  - auto-start watcher when absent
  - hybrid approach
- Identify which mutating MCP tools should trigger freshness after writing indexed content.
- Implement repeat-safe mutation-triggered freshness for qualifying MCP tools.
- Wire workflow-config additional project index prefixes through rebuild/setup paths and document the self-hosting use case.
- Add tests for watcher control behavior and diagnostics.
- Update `docs/specs/mcp-tool-surface.md`.
- Update `docs/architecture/current-state.md` and `docs/architecture/data-and-control-flow.md`.
- Update `docs/contributing/build-and-verification.md` with the recommended operator workflow for non-hook environments.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| watcher-design | planner | — | settle control model, persistence, and repeat-safety |
| contract-design | planner | watcher-design | MCP tool names, envelopes, and recovery semantics |
| watcher-runtime | implementer | contract-design | process launch, status, and stop behavior |
| mutation-freshness | implementer | contract-design | ensure MCP writes trigger background index freshness |
| tests | implementer | watcher-runtime, mutation-freshness | duplicate start, dependency failure, status coverage |
| docs | implementer | contract-design, tests | specs, architecture, and operator guidance |


## Serialization Points

- The watcher ownership and persistence model should be settled before MCP tool handlers are implemented, because it determines how start / stop / status remain repeat-safe.
- The mutation-time freshness policy should be settled before multiple mutating MCP tools are updated, so they all use one consistent mechanism.
- Tool names and response envelopes should be settled before tests are written broadly, because this is a contract surface.
- If the watcher state file location is introduced, docs and ignore policy must be updated in the same change.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/contributing/build-and-verification.md`

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Status visibility is the minimum operator contract for background behavior. |
| AC-2 | required | Starting the watcher through MCP is the core feature. |
| AC-3 | required | Duplicate watchers would create wasted work and confusing state. |
| AC-4 | required | Background control is incomplete without clean shutdown. |
| AC-5 | required | Missing-dependency clarity is necessary because `watchdog` is optional today. |
| AC-5a | required | Manual deterministic rebuild of the active project index is required for recovery in non-hook environments. |
| AC-5b | required | Packaged framework docs/seeds need the same deterministic MCP rebuild path to keep seed search recoverable. |
| AC-5c | required | Operators need structured rebuild statistics so MCP-triggered recovery is auditable without reading raw subprocess logs. |
| AC-5d | important | Explicit generic config is better than a Wavefoundry-only framework-code toggle and keeps the feature reusable across seeded repos. |
| AC-5e | required | Config that is only honored by one rebuild path would create confusing drift between MCP, setup, and shell workflows. |
| AC-6 | important | Hook-driven indexing must remain the preferred path where it already works. |
| AC-7 | important | Operators need a clear mental model for when to use hooks, watcher, or manual rebuild. |
| AC-8 | required | Process-control regressions are easy to reintroduce without tests. |
| AC-9 | required | MCP-originated writes must not depend on external editor hooks to become searchable. |
| AC-10 | required | Background freshness must remain bounded and repeat-safe under repeated MCP mutations. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-04-30 | Plan authored. | This conversation thread |
| 2026-04-30 | Reworked the indexing policy into a generic include-prefix surface (`indexing.project_include_prefixes.{docs,code}`) so self-hosting framework code and other excluded roots can be opt-in per content pass, with a compatibility shim for the prior boolean key. | `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py`, `.wavefoundry/framework/scripts/tests/test_indexer.py`, `docs/workflow-config.json`, `docs/architecture/data-and-control-flow.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-04-30 | Use MCP as a control plane for a watcher process, not as the watcher implementation itself. | The stdio server is request-driven and should not become the primary always-on filesystem daemon. | In-process watch loop inside `server.py`; rejected as brittle across client lifecycles. |
| 2026-04-30 | Treat hook-driven indexing as the preferred path where available, with MCP-managed watching as the fallback for non-hook environments. | This preserves existing lightweight behavior and avoids forcing every client into a daemon model. | Replace hooks entirely with a watcher; rejected as unnecessary scope expansion. |
| 2026-04-30 | MCP mutations that write indexed docs should also trigger background freshness directly. | MCP-originated writes do not necessarily pass through editor hook systems, so relying on hooks alone leaves the index stale in Codex-like environments. | Depend on operators to start a watcher manually every time; rejected as too fragile. |
| 2026-04-30 | Add a first-class MCP rebuild tool alongside background freshness. | Operators and agents still need a deterministic synchronous recovery path that does not rely on hooks or watcher state. | Keep rebuild as shell-only guidance; rejected because MCP already owns adjacent index-health and lifecycle operations. |
| 2026-04-30 | Extend the MCP rebuild path to support the packaged framework index, not just the active project index. | Seed/docs maintenance and self-hosting verification already depend on direct framework-index rebuilds, so the same deterministic recovery path should be available through MCP. | Leave framework rebuild shell-only; rejected because it splits equivalent recovery paths across two interfaces. |
| 2026-04-30 | Return structured index statistics from manual rebuild responses instead of expecting operators to infer them from raw command output. | The indexer already computes stable counts, and MCP should expose them directly so rebuilds are auditable in non-shell workflows. | Leave counts buried in subprocess output; rejected because it weakens MCP as an operator surface. |
| 2026-04-30 | Use generic additional project index prefixes in `docs/workflow-config.json` instead of a Wavefoundry-specific framework-code boolean. | Self-hosting Wavefoundry is one use case, but the extension point should work for any repo that needs extra excluded roots in code search. | Keep a dedicated `include_framework_code` toggle; rejected because it hardcodes one repo pattern into the shared config contract. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Watcher PID/state tracking becomes flaky across process crashes or client restarts. | Use explicit status validation, not just “PID file exists,” and clean stale state on detection. |
| Duplicate watchers are accidentally spawned for the same repo root. | Add explicit repeat-safe startup checks keyed to repo root and validated process metadata. |
| Optional `watchdog` dependency creates confusing partial behavior. | Make missing dependency a first-class MCP diagnostic with a concrete install/recovery path. |
| The watcher path diverges from hook-driven indexing behavior over time. | Keep both paths routed through the same underlying `indexer.py` incremental build behavior. |
| Mutation-triggered freshness floods the repo with repeated background rebuilds during MCP-heavy workflows. | Coalesce repeated triggers, or prefer watcher confirmation over one-process-per-mutation spawning when the write volume is high. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
