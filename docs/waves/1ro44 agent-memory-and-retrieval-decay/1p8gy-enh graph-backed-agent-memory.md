# Graph-backed agent memory

Change ID: `1p8gy-enh graph-backed-agent-memory`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-04
Wave: `1ro44 agent-memory-and-retrieval-decay`

## Rationale

Wavefoundry already preserves more project context than generic MCP memory systems: wave records, change docs, review evidence, session handoff, role journals, a semantic docs/code index, and a persistent structural graph. Agents still lose important operational memory at the moment of action: prior failed approaches, operator preferences, fragile files, review findings, environment gotchas, and decisions often live in long wave prose or journals and are not surfaced automatically before a similar edit, review, or setup path.

External MCP memory systems point at the useful shape but not the right product boundary for Wavefoundry. The MCP reference memory server is a generic entity/relation graph; Mem0/OpenMemory emphasizes user facts and hosted retrieval; Graphiti/Zep emphasizes temporal knowledge graphs; projectmem emphasizes local coding-agent memory with pre-action warnings. Wavefoundry should borrow the typed, temporal, evidence-backed parts and implement them locally on top of the existing semantic and graph systems.

This enhancement adds a first-class Wave Memory layer: local, repo-visible memory records with explicit evidence, target references, status/supersession, semantic retrieval, graph attachment, and lifecycle capture at pause/review/close. The goal is not generic chat memory. The goal is to improve agent work quality by making prior learning appear when it changes the next action.

The graph platform work landed in waves 1p9q3 and 1p9qh (2026-07-04) materially strengthens the case for graph attachment and changes how this feature should be built. Incremental merge with per-file SQLite deltas means memory-record graph updates can ride the existing delta path instead of forcing full rebuilds when a record is added or reconciled. The in-process graph query cache (~1000x warm-call speedup) makes per-call action-time memory lookup on `code_read`/`code_impact`/`code_callhierarchy` affordable, which was the riskiest latency assumption in the original draft. Build-time betweenness centrality (persisted top-200) gives advisories a principled priority signal — a `fragile_file` memory attached to a high-centrality file matters more than one on a leaf. Community detection gives memory an attachment scope above single files ("this area is fragile"), and the Java/C# inheritance-edge and receiver-resolution accuracy work makes symbol-level `target_refs` resolve reliably in enterprise target repos.

## Requirements

1. Add a typed memory record format for project memory. Records must include `memory_id`, `kind`, `status`, `summary`, `evidence_refs`, `target_refs`, `confidence`, `created_at`, `updated_at`, and optional `supersedes` / `superseded_by` fields.
2. Store durable memory as plain repo-visible Markdown under `docs/agents/memory/` so existing docs indexing can search it, diff it, review it, and package/upgrade it like other operating-surface docs.
3. Support these initial memory kinds: `failed_attempt`, `successful_pattern`, `review_finding`, `operator_preference`, `environment_gotcha`, `fragile_file`, `decision`, and `dependency_gotcha`.
4. Add MCP tools:
   - `wave_memory_add` to create a candidate or active memory record from structured inputs.
   - `wave_memory_search` to retrieve relevant memory by semantic query, exact target refs, kind, status, and recency.
   - `wave_memory_brief` to assemble a short cited briefing for contexts such as `session_start`, `pre_implementation`, `review`, `close`, `setup`, or `file_edit`.
   - `wave_memory_reconcile` to mark memory active, stale, superseded, or rejected without deleting history.
5. Extend the graph index with memory nodes and typed edges from memory records to referenced files, symbols, config keys, docs, waves, changes, and review lanes.
6. Surface memory in existing action paths where it can prevent mistakes:
   - `wave_current` / `wave_audit`: recent active memory relevant to the current wave.
   - `wave_review`: prior review findings and intentionally deferred AC patterns.
   - `code_read` / `code_impact` / `code_callhierarchy`: active memory attached to the file or symbol being inspected.
   - `wave_prepare` / `wave_implement`: advisory warnings for fragile files, repeated failed attempts, or operator preferences.
   Advisory payloads at every surfacing point are capped by named constants, ride the warm graph-query-cache path (no meaningful added latency), and every surfacing point degrades to the tool's current response when the memory directory, graph layer, or index is absent (readiness-council amendment).
7. Add lifecycle capture:
   - `pause-wave` writes working state to `session-handoff.md` as today and may propose memory candidates for durable lessons.
   - `review-wave` proposes memory candidates from blocking findings, repeated fixes, and reviewer lessons.
   - `close-wave` requires a memory distillation checkpoint: promote, reject, or defer proposed memories.
8. Do not store raw transcripts, secrets, credentials, full logs, or personal/user-profile facts unrelated to repository work. Memory must be evidence-backed and scoped to software-delivery behavior.
9. Preserve local-only operation. No hosted memory service, no network dependency, and no remote embedding service are required.
10. Provide validation and tests so memory records are well-formed, references are resolvable when possible, stale/superseded records do not appear as active warnings, and generated briefings carry citations.
11. Memory graph integration must ride the incremental-merge path (wave 1p9q3): adding or reconciling a memory record applies a per-file delta through the SQLite graph state store — it must not trigger a full graph rebuild. Memory-record writes must correctly invalidate (or coexist with) the in-process graph query cache, and memory nodes/edges require a `GRAPH_BUILDER_VERSION` bump in the same change.
12. Advisory prioritization uses graph signals: when multiple memories compete for a capped advisory slot, rank by target centrality (build-time betweenness where available, degree fallback) and memory confidence. Memory records may target a graph community (`community` target-ref scope) in addition to files/symbols, and `wave_memory_brief` groups community-scoped advisories accordingly.
13. Kind-aware decay uses the freshness primitive from `1ro43-enh churn-aware-retrieval-decay` (same wave): `failed_attempt` confidence attenuates as target-file churn accumulates after `created_at` (the failure may no longer reproduce); `operator_preference` and `decision` never decay on code churn; `environment_gotcha` decays on elapsed time. `fragile_file` is the exception (readiness-council amendment): churn on a fragile file is ambiguous evidence — it can mean the fragility was refactored away or that the file is actively unstable — so churn sets a **needs-reverification** flag on the advisory instead of attenuating confidence, and a `fragile_file` memory never drops below briefing inclusion from churn alone; only reconciliation (status/supersession) retires it. Decayed confidence affects advisory ranking and briefing inclusion, never record deletion — status/supersession remains the only lifecycle mechanism.

## Scope

**Problem statement:** Wavefoundry has durable artifacts and strong retrieval, but it does not have a typed, action-time memory layer. Useful lessons are captured inconsistently and retrieved only when an agent happens to search the right prose. Agents can repeat failed approaches, miss operator preferences, ignore fragile-file context, or rediscover review lessons that the repository already learned.

**In scope:**

- New memory record directory and schema under `docs/agents/memory/`.
- MCP tools for add/search/brief/reconcile.
- Docs-lint validation for memory frontmatter/sections and forbidden content patterns.
- Semantic indexing of memory records through the existing docs index.
- Graph-index extraction of memory nodes and edges to files/symbols/docs/waves/changes, integrated with the incremental-merge delta path and query cache (graph builder version bump included).
- Centrality-weighted advisory ranking and community-scoped memory attachment.
- Kind-aware decay of memory confidence via the `1ro43` freshness primitive (consumption side only).
- Action-time advisory surfacing in selected MCP responses.
- Seed/prompt updates for pause, review, close, Guru, and implementation workflows.
- Tests for schema validation, retrieval, graph edges, tool responses, lifecycle capture, and stale/superseded filtering.

**Out of scope:**

- Hosted/cloud memory services such as Mem0, Zep, or external vector databases.
- Personal assistant memory unrelated to this repository or its target repositories.
- Cross-repository global identity memory.
- Automatic promotion of memories without an explicit lifecycle checkpoint or operator/reviewer approval.
- Raw transcript ingestion or full conversation logging.
- Replacing role journals, session handoff, wave records, or `docs/references/project-context-memory.md`; this layer links to and distills from them.

## Acceptance Criteria

- [ ] AC-1: A documented memory schema exists under `docs/agents/memory/README.md`, and docs-lint validates required fields, known `kind` values, valid `status` values, evidence refs, target refs, and forbidden raw-secret/transcript patterns.
- [ ] AC-2: `wave_memory_add`, `wave_memory_search`, `wave_memory_brief`, and `wave_memory_reconcile` are available through MCP and return structured, cited responses with diagnostics and recovery hints.
- [ ] AC-3: Memory records are included in the existing docs semantic index; `docs_search` and `wave_memory_search` can retrieve records by concept, kind, and evidence text without a separate vector store.
- [ ] AC-4: The graph index emits `memory` nodes and edges from memory records to referenced files, symbols, waves, changes, docs, config keys, and review lanes; graph consumers can display or query those edges without breaking existing graph schemas.
- [ ] AC-5: `code_read`, `code_impact`, and `code_callhierarchy` surface active memory attached to the requested file or symbol, capped and cited, while excluding `stale`, `rejected`, and `superseded` records by default.
- [ ] AC-6: `wave_prepare`, `wave_review`, and `wave_audit` include relevant memory advisories for current-wave files, change IDs, review lanes, and deferred AC patterns.
- [ ] AC-7: `pause-wave`, `review-wave`, and `close-wave` prompt surfaces include memory-capture/distillation steps; close requires every proposed memory candidate to be promoted, rejected, or explicitly deferred.
- [ ] AC-8: Memory reconciliation preserves history through status/supersession instead of deleting or overwriting records; searches default to active memory but can include superseded/stale records when requested.
- [ ] AC-9: Tests cover schema validation, MCP tool behavior, semantic retrieval, graph extraction, action-time surfacing, lifecycle prompt text, and stale/superseded filtering.
- [ ] AC-10: Full framework tests run bytecode-free and docs validation passes.
- [ ] AC-11: Adding or reconciling a memory record updates the graph through the incremental per-file delta path (no full rebuild is triggered; a test asserts the delta path is taken), the graph query cache serves correct results after a memory write, and `GRAPH_BUILDER_VERSION` is bumped for the new node/edge shapes.
- [ ] AC-12: Advisory ranking under a cap prefers higher-centrality targets (betweenness where persisted, degree fallback) at equal confidence; community-scoped memory records attach to a community id, appear in `wave_memory_brief` grouped by community, and survive community re-detection via stable community references or graceful re-resolution.
- [ ] AC-13: Memory confidence decay is kind-aware using the `1ro43` freshness primitive: a `failed_attempt` whose target file churned since `created_at` ranks below an equivalent fresh one and can be excluded from briefings past a threshold; `operator_preference` ranking is unaffected by target churn; decay never deletes or auto-supersedes a record.

## Tasks

- [ ] Add `docs/agents/memory/README.md` and initial memory record template.
- [ ] Implement memory parsing/validation helpers in the framework scripts layer.
- [ ] Add docs-lint rules for memory record schema, allowed statuses/kinds, evidence refs, target refs, and forbidden raw transcript/secret patterns.
- [ ] Add MCP handlers and tool registrations for `wave_memory_add`, `wave_memory_search`, `wave_memory_brief`, and `wave_memory_reconcile`.
- [ ] Update the docs index classifier/chunker path so memory records are indexed as a distinct memory-tagged doc type or tag.
- [ ] Extend graph extraction to emit memory nodes and edges from `target_refs` / `evidence_refs`, wired through the incremental-merge delta path with query-cache invalidation and a `GRAPH_BUILDER_VERSION` bump.
- [ ] Implement centrality-weighted advisory ranking (betweenness/degree) and community-scoped target refs with briefing grouping.
- [ ] Consume the `1ro43` freshness primitive for kind-aware confidence decay in `wave_memory_search` / `wave_memory_brief` ranking.
- [ ] Add memory snippets to `code_read`, `code_impact`, and `code_callhierarchy` responses when target refs match.
- [ ] Add memory advisories to `wave_audit`, `wave_prepare`, and `wave_review`.
- [ ] Update seeds/prompts for pause, review, close, Guru, and implementation to use memory capture and memory briefings.
- [ ] Add dashboard support for memory counts and active advisories if the MCP response model exposes them cleanly.
- [ ] Add unit tests and fixture records for all memory kinds, statuses, supersession, and graph refs.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| schema-validation | implementer | - | Memory record format, docs-lint, fixtures |
| mcp-tools | implementer | schema-validation | Add/search/brief/reconcile tool surface |
| index-integration | implementer | schema-validation | Semantic indexing tags and graph nodes/edges |
| action-surfacing | implementer | mcp-tools, index-integration | Briefings and advisories in existing tools |
| lifecycle-prompts | implementer | schema-validation | Pause/review/close/Guru/implementation prompt changes |
| tests-docs | qa-reviewer | all implementation streams | Regression tests, docs-lint, bytecode-free suite |


## Serialization Points

- Memory schema must land before MCP tools, graph extraction, and prompt surfaces so every consumer reads one contract.
- Graph schema changes require a graph builder version bump and tests before action-time surfacing depends on memory edges.
- Graph extraction must integrate with the incremental-merge state store and query cache landed in 1p9q3; do not add a parallel write path.
- Kind-aware decay (AC-13) depends on the `1ro43` freshness primitive stabilizing first — same wave, explicit cross-change seam.
- Prompt/seed edits should land after the tool names and response shapes stabilize.
- Dashboard work, if included, should follow the MCP response shape rather than drive it.

## Affected Architecture Docs

- `docs/ARCHITECTURE.md` - add the memory architecture child doc if the implementation creates one.
- `docs/architecture/current-state.md` - update topology with memory records, MCP tools, and action-time surfacing.
- `docs/architecture/domain-map.md` - add the memory domain and interactions with index, graph, lifecycle, and dashboard.
- `docs/architecture/data-and-control-flow.md` - document add/search/brief/reconcile and lifecycle capture flows.
- `docs/architecture/search-architecture.md` - describe semantic retrieval of memory records and ranking/citation behavior.
- `docs/architecture/graph-index-system.md` - document memory nodes and edge types.
- `docs/architecture/testing-architecture.md` - add memory schema/tool/graph test tiers.
- ADR likely required: local typed memory records vs hosted memory service vs generic graph-only memory.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Schema and validation are the contract; without them memory becomes unreviewable prose. |
| AC-2 | required | MCP tool access is how agents will use memory consistently. |
| AC-3 | required | Reuses the existing semantic index and avoids a second retrieval stack. |
| AC-4 | required | Graph attachment is the Wavefoundry-specific advantage over generic MCP memory. |
| AC-5 | required | Action-time surfacing is the main quality improvement for coding agents. |
| AC-6 | required | Wave lifecycle tools must expose memory where mistakes are normally prevented. |
| AC-7 | required | Capture/distillation must be part of lifecycle closure or it will decay. |
| AC-8 | required | Supersession prevents stale memory from misleading agents. |
| AC-9 | required | The feature touches shared tool surfaces and must be test-locked. |
| AC-10 | required | Standard framework verification gate. |
| AC-11 | required | Full-rebuild-per-memory-write would make capture unusable; the 1p9q3 delta path exists precisely for this, and version bump is a standing convention. |
| AC-12 | important | Centrality/community ranking improves advisory quality but a flat-ranked v1 is still functional. |
| AC-13 | important | Kind-aware decay meaningfully reduces stale-warning noise; status/supersession alone is an acceptable v1 fallback. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-28 | Drafted from operator request after research into MCP memory systems and Wavefoundry's existing memory/index/graph capabilities. | Research summary: MCP reference memory server, Mem0/OpenMemory, Graphiti/Zep, Letta/MemGPT, projectmem, Codebase-Memory; local context from `docs/agents/wave-coordinator.md`, `docs/references/wavefoundry-overview.md`, and graph-index docs. |
| 2026-07-04 | Updated for the 1p9q3/1p9qh graph platform: incremental-merge delta path, query cache, build-time betweenness, communities, and symbol-resolution accuracy now underpin Requirements 11–13 and ACs 11–13; kind-aware decay wired to `1ro43-enh churn-aware-retrieval-decay` in the same wave. | Commit 38c52ccd (wave 1p9q3); wave 1p9qh implemented changes; `1ro43` change doc. |
| 2026-07-04 | Readiness-council amendments applied: `fragile_file` churn now sets a needs-reverification flag instead of attenuating confidence (churn on a fragile file is ambiguous evidence, Req 13); advisory surfacing gains named caps, cache-path latency posture, and graceful absence (Req 6). | Prepare-council synthesis in wave record Review Checkpoints. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-04 | Integrate memory graph writes into the 1p9q3 incremental-merge/query-cache infrastructure rather than a standalone memory graph or write path. | One graph store, one merge path, one cache: memory edges become queryable through every existing graph tool for free, and per-record updates stay cheap enough for lifecycle capture. | **Separate memory graph artifact:** isolates risk but duplicates merge/cache/versioning machinery and hides memory from existing graph consumers. **Full rebuild on memory write:** simplest, but makes capture cost scale with repo size and defeats the point of the delta store. |
| 2026-06-28 | Select a local typed memory layer backed by Markdown records, semantic indexing, and graph edges. | This fits Wavefoundry's local-only, project-visible contract and uses the existing index/graph strengths to surface memory at action time. | **Hosted memory service** such as Mem0/Zep: strong retrieval products but violates local-only/no-network-by-default and adds operator trust/dependency burden. **Generic MCP knowledge graph only:** simple and close to the MCP reference server, but loses Wavefoundry-specific evidence, lifecycle, and graph-node targeting. **Journal-only improvements:** low implementation cost, but still depends on agents remembering to search long prose and does not create action-time warnings. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Memory becomes stale and agents follow bad advice | Status/supersession fields, default active-only search, and close-time reconciliation. |
| Memory becomes noisy and over-triggers warnings | Typed kinds, confidence, capped snippets, target-ref matching, and advisory severity levels. |
| Agents store secrets, raw transcripts, or personal facts | Schema guidance, docs-lint forbidden-pattern checks, and prompt text that forbids raw transcript/personal memory. |
| Graph schema changes destabilize existing graph consumers | Add memory nodes/edges behind a graph builder version bump, preserve existing node/edge fields, and test old consumers. |
| Memory capture becomes burdensome at close | Use proposed candidates and require promote/reject/defer decisions, not hand-authored essays. |
| Duplicate role journals and project-context memory create confusion | Define memory records as typed retrieval/action artifacts; journals remain role retrospectives, and project-context memory remains curated durable narrative. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
