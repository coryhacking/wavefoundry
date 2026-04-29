# Wave — MCP Server Foundation

Owner: Engineering
Status: active
Last verified: 2026-04-29

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

| Role | Lane | Owns |
|------|------|------|
| implementer | implement | `12926-feat wavefoundry-mcp-index` |
| architecture-reviewer | review | `12926-feat wavefoundry-mcp-index` — MCP tool contracts, index design |
| code-reviewer | review | `12926-feat wavefoundry-mcp-index` — scripts, server |
| performance-reviewer | review | `12926-feat wavefoundry-mcp-index` — index build and query paths |
| factor-12-admin-processes | review (advisory) | `12926-feat wavefoundry-mcp-index` — CLI tool contracts |
| factor-13-api-first | review (advisory) | `12926-feat wavefoundry-mcp-index` — MCP tool surface contracts |
| framework-operator (persona) | design review / acceptance | `12926-feat wavefoundry-mcp-index` |

## Changes

Change ID: `12926-feat wavefoundry-mcp-index`
Change Status: `ready`

Change ID: `1293b-feat mcp-wave-lifecycle`
Change Status: `planned`
Depends On: `12926-feat wavefoundry-mcp-index`

## Dependencies

- No external wave dependencies.
- `1293b-feat mcp-wave-lifecycle` must not begin implementation until
  `12926-feat wavefoundry-mcp-index` is complete and its MCP server interface is stable.

## Current Assumptions

- A-1 (frozen): `fastembed` provides cross-platform ONNX wheels for Win x64, macOS
  arm64/x64, Linux x64/arm64 without C extension compilation.
- A-2 (frozen): `nomic-embed-code` and `bge-small-en-v1.5` are available in the
  fastembed model registry.
- A-3 (tentative): Index build time on a large repo (>5k files) is acceptable via
  incremental rebuild; full rebuild is an infrequent operator operation.
- A-4 (tentative): `1293b-feat mcp-wave-lifecycle` will be fully planned within the
  same wave after `12926` implementation is underway and the MCP server interface
  is visible.

## Outputs Produced or Expected

- `.wavefoundry/framework/scripts/build_index.py`
- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/index/` (runtime artifact, not checked in)
- Updated `render_platform_surfaces.py` with MCP config emission
- Updated post-edit hook with incremental index rebuild
- Updated `AGENTS.md` startup instructions routing through MCP tools
- Updated architecture docs: current-state, domain-map, data-and-control-flow
- `1293b-feat mcp-wave-lifecycle` fully planned (stub → planned)

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
- architecture-reviewer sign-off on MCP tool contracts and index design before implementation begins
- performance-reviewer sign-off on index build and query paths before merge
- factor-13 advisory review of MCP tool surface contracts (advisory)
- factor-12 advisory review of CLI tool contracts — `build_index.py`, `server.py` (advisory)
- framework-operator persona acceptance of operator-facing install/upgrade changes

## Journal Refs

- `docs/agents/journals/framework-operator.md`

## Journal Watchpoints

- Watchpoint: fastembed wheel unavailable on a target platform — A-1 invalidated; block implementation and reassess embedding stack
- Watchpoint: incremental index build time unacceptable on large repo — A-3 may need ANN fallback; block merge until resolved
- Watchpoint: `1293b` planning reveals MCP server interface changes needed — block `12926` merge until interface is restabilized

## Completion Criteria

- `12926-feat wavefoundry-mcp-index` implemented, reviewed, and all required ACs passing
- `1293b-feat mcp-wave-lifecycle` fully planned (stub converted to complete change doc)
- All required review lanes signed off for `12926`
- Architecture docs updated and docs-lint passing
- AGENTS.md updated to route through MCP tools

## Handoff or Next-Wave Notes

- The follow-on wave for `1293b` implementation should treat the `12926` MCP server
  interface as a hard contract; changes to it require re-review.
- BM25 hybrid search (deferred from `12926`) is a candidate for a subsequent wave
  once semantic search quality is validated in practice.

## Wave Summary

*(Populated at closure.)*
