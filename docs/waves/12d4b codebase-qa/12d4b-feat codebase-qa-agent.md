# Code Insight Agent (CIA)

Change ID: `12d4b-feat codebase-qa-agent`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-04
Wave: `12d4b codebase-qa`

## Rationale

Operators and coding agents (Claude, Codex, etc.) currently have no structured way to ask natural-language questions about the codebase and receive grounded, cited answers. While the MCP surface exposes `code_search`, `code_keyword_search`, `code_references`, and `code_definition`, there is no agent that knows how to route a question through these tools, synthesize a coherent answer, and cite the specific file/line evidence. The result is that agents either hallucinate when reasoning about unfamiliar code, or operators must manually compose multi-tool retrieval chains to answer basic questions like "where does billing handle failed payments?" or "what does the auth middleware do?"

This change introduces a **Code Insight Agent (CIA)** — a read-only, retrieval-grounded agent that accepts natural-language questions about the codebase and returns answers backed by citations to indexed code and docs.

## Requirements

1. The agent must accept a natural-language question as input and return a structured answer with citations (file path, line range, excerpt) for every claim.
2. The agent must classify each question as navigational, explanatory, or instructional before choosing a retrieval strategy.
3. The agent must use a multi-pass retrieval loop: broad semantic pass first (`code_search`, `docs_search`), then targeted structural pass (`code_keyword_search`, `code_references`, `code_definition`) when the first pass identifies relevant entry points.
4. The agent must signal uncertainty explicitly — "I couldn't find evidence of X in the indexed files" is a valid answer, not a failure. It must not extrapolate beyond what the index contains.
5. The agent must be read-only by default — it must never propose edits or create files.
6. The agent must be aware of index scope: what is indexed (docs, seeds, source code), what is excluded (binary files, `.env` values, generated artifacts), and what may be stale.
7. The MCP server must expose a `code_ask(question)` tool that wraps the retrieval pattern and returns a structured response: `answer`, `citations`, `confidence` (`high/medium/low`), `gaps` (retrieval gaps the agent identified), and `question_type` (the classified question kind: `navigational`, `explanatory`, or `instructional`).
8. The `code_ask` tool must be callable by any MCP-attached coding agent (Claude Code, Codex, Cursor, etc.) without the caller needing to know which underlying retrieval tool to use.
9. `code_ask` is a mechanical routing function — it issues retrieval tool calls, assembles results, and applies heuristic confidence scoring. No LLM synthesis occurs inside the MCP server; the calling agent's context window performs synthesis from the returned citations.

## Scope

**Problem statement:** The semantic index exists but has no question-answering layer. Agents either ignore it or manually chain tools without a consistent pattern for routing, synthesis, or citation discipline.

**In scope:**

- `docs/prompts/agents/code-insight-agent.prompt.md` — CIA prompt defining the retrieval loop, classification logic, citation format, and uncertainty protocol
- `server.py` `code_ask(question)` MCP tool — routes question through retrieval tools, returns structured `{answer, citations, confidence, gaps, question_type, index_freshness}` response
- `docs/prompts/index.md` — register `code_ask` / `Ask codebase` as a public shortcut
- `docs/architecture/search-architecture.md` — document the CIA layer and `code_ask` tool
- `AGENTS.md` — thin pointer to the CIA shortcut

**Out of scope:**

- File-level summary chunks (`kind="code-summary"`) — future index enhancement; current line-window chunks are sufficient for v1
- Chunk relationship graph — future enhancement
- Streaming / incremental responses — MCP tool returns complete structured response
- Edit or refactor suggestions — agent is read-only
- Multi-turn conversation / session state — each `code_ask` call is stateless

## Acceptance Criteria

- AC-1: `code_ask` called with a question about a known indexed symbol returns an answer with at least one citation containing a file path and line range (e.g., `src/billing.py:42-58`); test uses a fixture index with a known entry point
- AC-2: The response includes `question_type` field set to one of `navigational`, `explanatory`, or `instructional` — classification taxonomy defined in the CIA prompt
- AC-3: For a question about a topic not in the index, the response `confidence` is `low` and `gaps` lists what was not found
- AC-4: The agent never proposes edits, creates files, or calls any non-read tool
- AC-5: `code_ask` is registered in the MCP server and callable via the MCP protocol; no additional configuration required beyond the existing server; Cursor/Claude Code access is a manual verification step (not automated)
- AC-6: The agent prompt documents index scope limitations (exclusions, redacted files, staleness)
- AC-7: `docs/prompts/index.md` lists `Ask codebase` / `code_ask` as a public shortcut
- AC-8: `docs/architecture/search-architecture.md` describes the CIA layer
- AC-9: `code_ask` response includes `index_freshness` field: `"current"` when no chunker_version_mismatch advisory is active, `"stale"` otherwise

## Tasks

- [ ] Draft `docs/prompts/agents/code-insight-agent.prompt.md`: question classification taxonomy (define navigational/explanatory/instructional with examples), retrieval loop (broad → targeted → structural), citation format (e.g., `src/billing.py:42-58`), uncertainty protocol, index scope section
- [ ] Implement `code_ask(question)` in `server.py`: mechanical routing — broad pass (`code_search` + `docs_search`), targeted pass (`code_keyword_search` / `code_references`); heuristic confidence scoring; assemble `{answer, citations, confidence, gaps, question_type, index_freshness}` response; no LLM synthesis in the tool; `index_freshness` is `"stale"` when `_layer_health` returns a `chunker_version_mismatch` advisory, `"current"` otherwise
- [ ] Add `code_ask` to MCP tool registration and `AGENTS.md` thin pointer
- [ ] Update `docs/prompts/index.md` — `Ask codebase` shortcut entry
- [ ] Update `docs/architecture/search-architecture.md` — CIA layer section
- [ ] Tests: `code_ask` returns structured response shape; `question_type`, `confidence`, `gaps`, `index_freshness` fields present; tool does not call any write-path tools (`wave_index_build`, `wave_sync_surfaces`, `wave_add_change`, etc.); use fixture index for AC-1 citation test

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| CIA prompt | Engineering | — | `code-insight-agent.prompt.md` — classification + retrieval loop + citation format |
| `code_ask` MCP tool | Engineering | CIA prompt | Retrieval routing logic follows prompt design |
| Docs + registration | Engineering | `code_ask` MCP tool | `index.md`, `AGENTS.md`, architecture doc |
| Tests | Engineering | `code_ask` MCP tool | Response shape, confidence/gaps, read-only constraint |

## Serialization Points

- `code_ask` MCP tool implementation must follow the CIA prompt design — the prompt defines the retrieval strategy and response shape; the tool implements it. Do not parallelize these two workstreams.
- `server.py` is a single-author surface for MCP tool registration — coordinate with any concurrent server.py changes.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — new CIA layer section documenting `code_ask`, retrieval routing, citation format, confidence model

## AC Priority

| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | Core capability — grounded answer with citation |
| AC-2 | required     | Classification drives retrieval strategy correctness; `question_type` in response makes it testable |
| AC-3 | required     | Uncertainty signaling prevents hallucination |
| AC-4 | required     | Read-only constraint is a safety invariant |
| AC-5 | required     | Must work from any MCP-attached client |
| AC-6 | important    | Scope awareness helps operators interpret gaps |
| AC-7 | important    | Discoverability |
| AC-8 | important    | Architecture doc currency |
| AC-9 | important    | Operators need staleness signal to know when to trigger rebuild |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-04 | Change doc created from design session | Conversation design map |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-04 | `code_ask` as a new MCP tool rather than documenting a multi-tool pattern | Single entry point makes the capability accessible to any MCP client without the caller needing to know retrieval internals | Document multi-tool pattern only (rejected: no consistent UX, no synthesis layer) |
| 2026-05-04 | Agent is read-only — no edit proposals | Code insight is a distinct activity from implementation; mixing them creates scope confusion and safety risk | Allow optional edit proposals (rejected: blurs the agent's role) |
| 2026-05-04 | Defer file-level summary chunks to a future wave | Existing line-window chunks are sufficient for v1; summary chunks are an optimization, not a prerequisite | Block on summary chunks (rejected: delays value; can be added incrementally) |
| 2026-05-04 | Stateless per-call design for `code_ask` | Simpler to implement and test; MCP tools are naturally stateless; multi-turn conversation can be layered later | Session state / conversation memory (deferred) |
| 2026-05-04 | `code_ask` is mechanical routing, not LLM synthesis | Synthesis in the MCP server would require an outbound API call, adding latency, cost, and failure modes. The calling agent (Claude, Codex, etc.) already has an LLM context window — let it synthesize from the citations `code_ask` returns. `code_ask` assembles retrieval results and applies heuristic confidence scoring only. | LLM synthesis inside the MCP server (rejected: latency, cost, blast radius of nested API calls) |
| 2026-05-04 | `confidence` heuristic: `high` = 2+ direct citations, `medium` = 1 citation or keyword fallback only, `low` = no evidence found | Provides a consistent, testable signal without requiring semantic similarity scoring | Embedding-similarity-based confidence (deferred: requires score normalization across tools) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Agent extrapolates beyond indexed content | Mandatory uncertainty signaling (AC-3); `confidence` field in response; agent prompt explicitly prohibits unsupported claims |
| Code index stale at query time | `code_ask` response includes index staleness note when `wave_index_health` advisory is active; operator can trigger rebuild |
| `server.py` synthesis adds latency | Retrieval passes can be parallelized; `code_ask` is a user-initiated tool, not a hot path |
| MCP clients that don't support structured JSON responses | `answer` field is plain text; citations are human-readable; degrades gracefully |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
