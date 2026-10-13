# Reload the complete framework implementation

Change ID: `20jo3-enh complete-framework-runtime-reload`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-10-12
Wave: TBD

## Rationale

The operator wants reload to adopt upgraded code, rather than another diagnostic listing stale modules or a routine instruction to restart the host. A successful wf_reload_mcp should leave the running framework implementation current behind the existing MCP connection, including setup assessment, renderers, indexing and imported helpers.

Current perform_mcp_reload re-executes server_impl, refreshes selected helpers and rebuilds the handler. Other Python imports and retained references survive. setup_readiness compares 29 source fingerprints, while the runner refreshes only the server_impl entry in its loaded identity. An offline comparison of published 1.29.0+pw75 and local 1.30.0+pw8f found render_agent_surfaces.py was the only changed member of that fingerprint set; a generic restart warning therefore does not establish that setup_readiness.py changed. This comparison does not establish the field project's starting version.

The selected starting approach extends the existing controlled reload boundary to the complete framework implementation, with explicit ownership of the small process/transport core. Readiness must prove that the boundary can be made coherent; a replacement worker process remains an alternative if retained references cannot be safely reconstructed. This is planned work, not a claim that full reload already works.

## Requirements

1. For ordinary framework Python implementation upgrades, one successful wf_reload_mcp adopts current installed code across the implementation and its framework-owned imported dependencies. Preserve the MCP connection and registered tool behavior without requiring the operator to restart the host. Automatic post-upgrade reload uses the same mechanism.
2. Derive the refresh set from the loaded module origins under the canonical scripts root, package/flat aliases and the dependency references retained by the new handler and tools. Do not use a growing hand-maintained list of changed helpers as the completeness rule. Include modules imported lazily after reload. Process/transport survivors must have explicit ownership and safe rebinding; unchanged ownership does not authorize executing changed stale behavior.
3. Make reload one bounded lifecycle transition: coordinate request admission and active calls, settle or transfer owned background work, refresh code and dependent references, construct the replacement handler, then publish it. A busy or failed transition returns a truthful non-success outcome with a retry or recovery action. Never expose a half-reloaded runtime as success or restore an already-closed handler as healthy.
4. Preserve lock ownership and exception identity where required, storage/recovery checkpoints, in-flight model-download ownership, index contents and uncommitted project files. Reuse existing lock and worker ownership rules; do not reset state merely to silence freshness checks. Reload itself must not trigger a full index rebuild, new model download, source qualification suite or evidence-file collection.
5. Mark loaded identity current only for code actually adopted. Verify the handler's setup assessment and actual post-reload behavior, not only disk/version equality. Repeated reload converges without duplicated monitors, writers or tool registrations. Keep extension helper reload and tool-list notification contracts intact.
6. Keep genuine interpreter/native dependency changes and bootstrap/transport replacement separate from ordinary implementation reload. Readiness must explicitly establish this residual boundary and how it is detected. Do not present an arbitrary Python helper change as an unavoidable host restart. If a larger process-supervision design is required, amend and review that scope before implementation.

## Scope

**In scope:** Complete implementation reload behind the existing MCP transport; reference and ownership lifecycle; setup identity; public reload and automatic upgrade integration; regression coverage; corrected operator guidance.

**Out of scope:** A stale-module reporting feature, suppressing warnings without adopting code, third-party/native-package hot reload, interpreter replacement, reconciliation scanner timeout repair, performance-threshold changes, host UI automation, and upgrade-wide requalification or recuration.

## Acceptance Criteria

- [ ] AC-1: A registered reload followed by real registered calls uses changed framework helper behavior, including setup assessment and renderer/index dependencies, on the same MCP session. Retained imported-object references and subsequent lazy imports use the new implementation; a known-stale implementation fails the oracle.
- [ ] AC-2: Selected active-call, held-lock, background-worker and repeated-reload cases preserve ownership and persistent state without duplicate writers or monitors. A blocked transition finishes with an explicit bounded non-success result rather than pretending currentness.
- [ ] AC-3: Import/build/publication failure controls demonstrate the documented coherent recovery outcome. Freshness cannot become current without executing the replacement implementation, and no disposed handler resumes normal serving as a fallback.
- [ ] AC-4: Public and automatic upgrade reload share the behavior; unchanged and extension-bearing controls preserve tool schemas/notification semantics and a healthy existing index without rebuilding it. Guidance clearly states the proven reload boundary and any genuine process-replacement exception.

## Tasks

- [ ] T-1: Before readiness, bound the implementation/transport ownership split and retained-reference paths; select controlled in-process refresh or explicitly amend for worker replacement if required.
- [ ] T-2: Implement bounded quiescence, coherent dependency refresh and handler publication using existing ownership mechanisms.
- [ ] T-3: Integrate executed-code identity, tool registration and automatic upgrade reload; preserve error/retry semantics.
- [ ] T-4: Add focused registered-path regression and failure controls covering the acceptance criteria; obtain independent code, QA, architecture and security review.
- [ ] T-5: Update canonical seed/operator guidance and architecture contracts, run normal change qualification, and record concise outcomes in wave.md once admitted.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Ownership and reload design | architecture-reviewer with implementer | plan | Resolve boundary before readiness |
| Runtime implementation and tests | implementer | admitted/readied wave | One write owner for runner and handler |
| Contract guidance | implementer | selected design | Seed first, then rendered surface |
| Independent review | required reviewer lanes and council | phase-specific evidence | No substitute for readiness or delivery authority |

## Serialization Points

One implementer owns the runner, server_impl and setup identity transition. Runtime/core state modules are read-only discovery targets until the readiness design names any necessary edits; a change to their ownership requires a plan amendment. Seeds and rendered guidance have one write owner; reviewers are read-only. Preserve existing published 1.29.0 and local 1.30.0+pw8f artifacts. Do not alter host configuration or restart an attached session during discovery.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/runtime_lock.py`
- `.wavefoundry/framework/scripts/sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_reload_runner.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

Root CHANGELOG.md is also an intended documentation edit. Test-file placement must follow the existing suite; use existing reload test classes rather than assuming every named concern needs a new file.

## Affected Architecture Docs

Update docs/architecture/data-and-control-flow.md for request admission, code refresh, state ownership and publication/failure transitions. Update docs/specs/mcp-tool-surface.md for successful reload guarantees and bounded non-success behavior. Canonical seed 160 and its rendered upgrade prompt must describe actual reload coverage, without substituting diagnostics for adoption.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Actual updated behavior without routine host restart is the operator's goal |
| AC-2 | required | Reload must preserve active work and single-owner guarantees |
| AC-3 | required | Partial mutation must not produce false success or unhealthy recovery |
| AC-4 | required | Upgrade integration and supported boundary must match runtime behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Planned from the operator's correction: reload code, rather than add stale-module reporting. No source edits, live reload or restart performed. Indexed orientation was stale; claims were validated against live source and an offline archive comparison. | perform_mcp_reload; _reload_module_in_place; ImplHandler.close; setup_readiness.SOURCE_FILES and assess_setup; ReloadedSourceIdentityTests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-12 | Prefer complete controlled implementation reload through the existing transport, subject to ownership/reference proof before readiness | Extends the current capability and preserves the operator's session without introducing a second transport architecture by default | Add helper names individually: perpetuates incomplete reload. Blindly evict every module: breaks shared identity/ownership. Replace a worker behind a stable supervisor: gives a cleaner isolation boundary but adds process/protocol ownership; select only if in-process coherence cannot be demonstrated and admit the additional scope. |
| 2026-10-12 | Verify execution and state preservation; do not build a stale-module reporting feature | Operator explicitly rejected reporting as the remedy | Reset fingerprints or merely improve messages: does not load code. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Old functions/classes survive through aliases or retained objects | Derive dependency/reference boundary and verify actual registered behavior |
| Reload releases locks or races active work | Establish bounded quiescence/ownership protocol before mutation |
| Failed replacement leaves neither handler usable | Specify and test coherent failure recovery before claiming transactional reload |
| Bootstrap/native state cannot support in-process replacement | Resolve the residual boundary at readiness; do not silently broaden or misrepresent coverage |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
