# Add narrate Mode to code_graph_path (Deterministic Plain-English Per-Hop Explanation)

Change ID: `1p41q-enh code-graph-path-narrate-mode`
Change Status: `deferred`
Owner: Engineering
Status: deferred
Last verified: 2026-06-08
Wave: 1p41l graph-tools-field-feedback-round-5

> **Deferred 2026-06-08 (operator value re-assessment).** Retained in wave `1p41l` marked `deferred` (a terminal status) so the decision stays visible in the dashboard; not built. The two headline value cases were already found unrealizable (external `::*` nodes are non-transitive; the indexer has no `field` edge), and the remaining forward/backward rendering is already served by the existing guru recipes (`guru.md:245` reads `either`-mode paths via `traversal_direction`; `:281` directs inspecting `path_edges[i].relation`) — so narration is convenience over a redundant restatement of structured data agents are already guided to read. Revisit **only if a field team requests narration with a concrete use case**.

## Rationale

Aceiss field eval §3.5 asks for a `narrate: true` option on `code_graph_path` that produces a plain-English, per-hop explanation of a path so an agent need not interpret the raw edge list.

Round-5 grounding confirmed: no narration exists today (`grep narrate/narration` returns empty), and **all raw materials are present** — `path_edges` carry `source`/`target`/`relation`/`confidence` and, in `either` mode, `traversal_direction` (`graph_query.py:1192`); `path_nodes` carry `label`/`kind`/`source_file`. Narration is a **mechanical per-hop templating layer with no model call**, consistent with the no-LLM-synthesis policy.

**Scope corrected at pre-implementation review (2026-06-08):** the original framing led on an AOP/external-bridge case (`… → external::callDepth ← …`) and a "shared field" narration — both **unrealizable** in the current engine. External `::*` nodes are **non-transitive** (`graph_query.py:1155-1160`; a path *through* an external node returns `found:false`, asserted by `test_external_node_is_non_transitive_intermediate`), so an external node is only ever a path *endpoint*, never a crossed hop. And the indexer emits only `calls`/`imports`/`defines` edges — there is **no** `field`/`reads`/`writes` relation. Narration is therefore scoped to the realizable set: forward and backward (`either`-mode) hops over `calls`/`imports`/`defines`, naming the relation + confidence + node labels. Because an agent can already read this from the structured output, the value is convenience/token-savings — the **lowest-priority** round-5 tool.

## Requirements

1. Add `narrate: bool = False` to `code_graph_path` (and its `graph_query.py` backing function).
2. When `narrate=true`, add a `narration` field to the response: an ordered list of plain-English hop strings derived purely from the structured path (no model call). Examples: `` `FooEntry` calls `BarHandler` [RECEIVER_RESOLVED] `` (forward) and `` `BarExit` is called by `BazAdvice` [EXTRACTED] `` (backward, `either`-mode — a reversed `calls` edge). No invented relations (the graph has no `field`/shared-state edge).
3. Narration reflects `traversal_direction` (forward vs backward — a reversed edge) and names the actual `relation` (`calls`/`imports`/`defines`, never a guessed verb like "references") + confidence + node labels. It does **not** narrate external-bridge crossings — external `::*` nodes are non-transitive, so they appear only as path endpoints, never as crossed hops.
4. Additive and back-compatible: with `narrate=false` (default), the response shape is unchanged.

## Scope

**Problem statement:** AOP/event-driven `code_graph_path` results are hard to interpret from the raw edge list; there is no human-readable rendering.

**In scope:**

- `narrate` param + a deterministic per-hop formatter in `graph_query.py`.
- MCP wiring (`server_impl.py`), docstring, `mcp-tool-surface.md` + `211-guru.prompt.md` mention, unit tests.

**Out of scope:**

- Any LLM/model call (narration is a pure function over the path).
- Changes to path-search semantics (weighted-cost search, `min_confidence`, `direction` unchanged).
- Narration for any tool other than `code_graph_path`.

## Acceptance Criteria

- [~] AC-1: `code_graph_path(..., narrate=true)` returns a `narration` list with **`len(narration) == hop_count == len(path_edges)`** (one entry per edge, not per node); it is an **empty list** when `found=false` or for the zero-hop identity case (`from == to`, `graph_query.py:1118-1125`).
- [~] AC-2: narration is produced deterministically from `path_edges`/`path_nodes` with no model call — verifiable as a pure, unit-tested function over a fixed path.
- [~] AC-3: forward and backward (`either`-mode) hops over `calls`/`imports`/`defines` are phrased distinctly and name the actual relation + confidence + node labels.
- [~] AC-4: `narrate=false` (default) leaves the response shape byte-for-byte unchanged (back-compat); existing `code_graph_path` tests still pass.
- [~] AC-5: unit tests cover forward-only, `either`-mode with a backward hop, the zero-hop identity case (`from == to` → empty narration), and `found=false` (empty narration). No external-intermediate case — the engine cannot emit one.
- [~] AC-6: `run_tests.py` and docs-lint pass; `211-guru.prompt.md` + the prompt-surface manifest document the param. `code_graph_path` is not currently in `docs/specs/mcp-tool-surface.md` — **add** a `code_graph_path` entry there (with the `narrate` param), not amend a non-existent one.
- [~] AC-7: an **MCP wrapper-layer** regression test asserts `code_graph_path(narrate=true)` returns the `narration` list through the tool boundary and that `narrate=false` omits it (carry-forward lesson from waves `130rj`/`130ol`).

## Tasks

- [~] Add a `narrate_path(path_nodes, path_edges)` pure formatter in `graph_query.py`.
- [~] Thread the `narrate` param through `code_graph_path` (query fn + MCP tool in `server_impl.py`); attach `narration` only when true.
- [~] Add unit tests (forward, backward [`either`-mode reversed `calls`], zero-hop identity, `found=false`).
- [~] Document in `docs/specs/mcp-tool-surface.md` and `211-guru.prompt.md`; update prompt-surface manifest if required.

## Agent Execution Graph


| Workstream          | Owner       | Depends On | Notes |
| ------------------- | ----------- | ---------- | ----- |
| narration formatter | Engineering | —          | Pure function in `graph_query.py` |
| MCP wiring + docs   | Engineering | formatter  | `server_impl.py` (shared file w/ 1p41o) |


## Serialization Points

- `server_impl.py` `code_graph_path` registration shares the tool-registration region with `1p41o` (the only sibling still in the wave — `1p41p` was removed) — sequence the edits.

## Affected Architecture Docs

N/A — additive, deterministic rendering of an existing tool's output; no boundary or flow change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core narrate output |
| AC-2 | required  | No-LLM constraint is the design invariant |
| AC-3 | important | Forward/backward phrasing is the feature's value |
| AC-4 | required  | Back-compat — default response unchanged |
| AC-5 | required  | Three path shapes need tests |
| AC-6 | required  | Framework tests + lint + spec |
| AC-7 | important | Wrapper-layer regression (130rj/130ol lesson) |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-07 | Deterministic templating, no LLM | Matches no-synthesis policy; path data is sufficient | LLM-narrated hops (rejected — violates policy, adds latency/cost) |
| 2026-06-08 | **Trimmed (pre-impl review):** removed the external-bridge and "shared field" narration cases; scoped to forward/backward `calls`/`imports`/`defines`; added identity/not-found/length ACs; fixed stale `1p41p` refs and the `mcp-tool-surface.md` clause. | Grounding showed external `::*` nodes are non-transitive (`graph_query.py:1155-1160`) so the external-intermediate hop the original AC-3/AC-5 tested is unemittable, and the indexer has no `field` relation — both headline value cases were unrealizable. Kept (trimmed) per operator decision rather than deferred. | Defer the whole change (documented strongest-alternative); keep the external/field cases (untestable). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Marginal value (agent can synthesize from edges) | Keep scope tiny; lowest priority; ship only if cheap |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
