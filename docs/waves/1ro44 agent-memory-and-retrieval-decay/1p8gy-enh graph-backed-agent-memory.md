# Graph-backed agent memory

Change ID: `1p8gy-enh graph-backed-agent-memory`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-14
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
5. Extend the graph index with memory nodes and typed edges from memory records to referenced files, symbols, config keys, and docs. Constraints from the 2026-07-13 pre-implementation review: (a) wave records, change docs, and review lanes are **not graph nodes** — `docs/waves/` and `docs/plans/` are excluded from graph doc-scan by design — so wave/change/lane references stay plain record fields resolved at query time, not graph edges; (b) the graph payload prunes zero-edge doc nodes, so a `memory` node must either be exempted from the prune or guaranteed at least one resolvable edge, with defined behavior (record still valid, advisory still served from the record store) when no `target_refs` resolve; (c) markdown already rides the per-file doc delta path as generic `doc` nodes — typed `memory` nodes extend `_kind_for_path`/doc extraction and the doc-kind sets that assume `{doc, seed}`.
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
12. Advisory prioritization uses graph signals: when multiple memories compete for a capped advisory slot, rank by target centrality (build-time betweenness where available, degree fallback) and memory confidence. Memory records may target a graph community (`community` target-ref scope) in addition to files/symbols, and `wave_memory_brief` groups community-scoped advisories accordingly. Community references persist the community's **hub node id** (the established stable cross-rebuild anchor, re-resolved to the current community by membership scan), never the raw `community_id` — Leiden re-clustering renumbers ids.
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

- [x] AC-1: A documented memory schema exists under `docs/agents/memory/README.md`, and docs-lint validates required fields, known `kind` values, valid `status` values, evidence refs, target refs, and forbidden raw-secret/transcript patterns. *(Evidence: `docs/agents/memory/README.md` (schema, kinds/decay table, forbidden content, template); `check_memory_docs` in `wave_lint_lib/wave_validators.py` registered in both full and incremental pipelines; `tests/test_docs_lint.py` MemoryRecordLintTests — all eight kinds pass well-formed, seven violation classes fail loudly incl. secret content and supersession-without-link; memory records exempt from agent role/category metadata like journals.)*
- [x] AC-2: `wave_memory_add`, `wave_memory_search`, `wave_memory_brief`, and `wave_memory_reconcile` are available through MCP and return structured, cited responses with diagnostics and recovery hints. *(Response builders + registrations in `server_impl.py`; forbidden content refused BEFORE write; every error path carries a typed diagnostic with recovery tools. Evidence: `tests/test_memory_records.py` MemoryToolTests — full add/search/brief/reconcile flow, refusals, supersedes side-effect, caps.)*
- [x] AC-3: Memory records are included in the existing docs semantic index; `docs_search` and `wave_memory_search` can retrieve records by concept, kind, and evidence text without a separate vector store. *(Records live under `docs/`, so the docs index embeds them by construction; `memory` tag added in `_tag_utils.infer_tags`; `wave_memory_search` fuses an optional semantic assist over the docs index with token-containment fallback — no separate vector store exists. Semantic-assist degrade pinned by test; live-index inclusion confirmed at the wave-end build.)*
- [x] AC-4: The graph index emits `memory` nodes and edges from memory records to referenced files, symbols, docs, and config keys; wave/change/review-lane references resolve as record fields at query time (amended 2026-07-13 — wave/change docs are excluded from graph doc-scan by design, so they cannot be edge targets); memory nodes with unresolvable `target_refs` survive the zero-edge doc prune (or are exempted from it) and their records remain retrievable; graph consumers can display or query memory edges without breaking existing graph schemas. *(Evidence: `graph_indexer.py` — `memory` kind in `_kind_for_path` (README excluded), typed `memory_targets` edges for file+`symbol:` targets in `_extract_doc_artifact`, zero-edge-prune exemption; `tests/test_graph_indexer.py` MemoryGraphExtractionTests — node kind, both edge types, prune survival vs plain-doc pruning, wave-refs-never-edges. Existing prose `doc_references_code` extraction still rides for free.)*
- [x] AC-5: `code_read`, `code_impact`, and `code_callhierarchy` surface active memory attached to the requested file or symbol, capped and cited, while excluding `stale`, `rejected`, and `superseded` records by default. *(Re-verified 2026-07-14 round-4 re-review: the raw-edit invalidation path is now checked and cross-process fail-closed. `memory_invalidate` returns True only when the generation DURABLY advances; on failure the indexer FAILS the build BEFORE recording file metadata (`_build_failed_result`), so the recovered retry re-detects the edit and advances the generation — a "clean" build can no longer strand a warm reader. Evidence: `test_indexer.MemoryInvalidationBuildTailTests.test_advance_failure_fails_build_before_bookkeeping` (real `build_index`, file_meta preserved, recovery advances) + `RealChildProcessCoherenceTests` (a genuine OS child process observes the fence/clear).)*
- [x] AC-6: `wave_prepare`, `wave_review`, and `wave_audit` include relevant memory advisories for current-wave files, change IDs, review lanes, and deferred AC patterns. *(`_memory_advisories_for_wave` — matches records whose evidence/target refs mention the wave or admitted change ids, tops up with fragile-file records flagged `needs_reverification`; attached at all three lifecycle responses. Evidence: ActionTimeAdvisoryTests wave-matching + graceful-empty fixtures.)*
- [x] AC-7: `pause-wave`, `review-wave`, and `close-wave` prompt surfaces include memory-capture/distillation steps; close requires every proposed memory candidate to be promoted, rejected, or explicitly deferred. *(Canonical directives in seed 100 (pause/review/close/implement bullets) + rendered local surfaces; the close checkpoint is the cheap decide-pass the council required. Evidence: LifecyclePromptTextTests pins the text on both the seed and the renders.)*
- [x] AC-8: Memory reconciliation preserves history through status/supersession instead of deleting or overwriting records; searches default to active memory but can include superseded/stale records when requested. *(Re-verified 2026-07-14: fenced tool mutations preserve the record and advance status; a forced finalize failure leaves `dirty=1`, and a separately loaded server with an already-warm cache bypasses and excludes the stale record. The remaining raw-edit invalidation defect is tracked under AC-5/AC-9, not reconciliation.)*
- [x] AC-9: Tests cover schema validation, MCP tool behavior, semantic retrieval, graph extraction, action-time surfacing, lifecycle prompt text, and stale/superseded filtering. *(Re-verified 2026-07-14 round-4 re-review with the required integration matrix: `MemoryInvalidationBuildTailTests` drives the REAL `build_index` add/edit/delete/no-op/unrelated/README matrix plus the forced late-build-failure and forced advance-failure (build-fails-before-bookkeeping) paths; `TwoProcessCacheCoherenceTests` uses two independently loaded server instances sharing only the on-disk seqlock, and `RealChildProcessCoherenceTests` adds a genuine separate-OS-process probe; `WriterTokenInterleaveTests` proves one writer cannot clear another's fence + TTL self-heal; reset-ABA remains covered. No test now simulates the second process by clearing one module's cache.)*
- [x] AC-10: Full framework tests run bytecode-free and docs validation passes. *(2026-07-14 after round-4 re-review remediation: `run_tests.py` — full suite OK bytecode-free (count in the wave checkpoint); `wave_validate` docs-lint clean; `git diff --check` clean.)*
- [x] AC-11: Adding or reconciling a memory record updates the graph through the incremental per-file delta path (no full rebuild is triggered; a test asserts the delta path is taken), the graph query cache serves correct results after a memory write, and `GRAPH_BUILDER_VERSION` is bumped for the new node/edge shapes. *(Evidence: `test_memory_write_rides_the_incremental_delta_path` — `merge_stats.mode == "incremental"`, `files_changed == 1`; `test_query_cache_serves_memory_node_after_a_write` — stat-validated cache reload; `GRAPH_BUILDER_VERSION` 43 → 44 with the rationale in the constant comment; `wave_memory_add`/`reconcile` fire the background index refresh whose hook build carries `content=all` incl. the graph delta.)*
- [x] AC-12: Advisory ranking under a cap prefers higher-centrality targets (betweenness where persisted, degree fallback) at equal confidence; community-scoped memory records attach to a community id, appear in `wave_memory_brief` grouped by community, and survive community re-detection via stable community references or graceful re-resolution. *(`_memory_ranked`: decayed-confidence primary, persisted-betweenness tie-break from the cluster artifact with graceful absence (flat ranking); community refs use the `community:hub:<node-id>` form — the hub node id is the established stable cross-rebuild anchor per the pre-implementation-review amendment — and `wave_memory_brief` groups them under `community_scoped`. Evidence: MemoryToolTests community grouping fixture.)*
- [x] AC-13: Memory confidence decay is kind-aware using the `1ro43` freshness primitive: a `failed_attempt` whose target file churned since `created_at` ranks below an equivalent fresh one and can be excluded from briefings past a threshold; `operator_preference` ranking is unaffected by target churn; decay never deletes or auto-supersedes a record. *(`memory_records.apply_decay` consumes `freshness_for_path(since_ts)`; hyperbolic churn/time decay with named halving constants; `fragile_file` sets `needs_reverification` and never drops below briefing inclusion from churn (council amendment); `BRIEFING_CONFIDENCE_FLOOR` exclusion. Evidence: DecayTests — churn attenuation to exactly half at the halving count, operator_preference immunity, fragile_file flag-not-attenuate, time decay, absent-store no-decay; decay is a ranking view, records untouched.)*

## Tasks

- [x] Add `docs/agents/memory/README.md` and initial memory record template. *(Schema doc + inline template; "agent memory layer" naming per the pre-implementation-review amendment.)*
- [x] Implement memory parsing/validation helpers in the framework scripts layer. *(`memory_records.py`: parse/load/render/write/reconcile/decay/match, tolerant parsing — malformed files skipped by readers, rejected by lint.)*
- [x] Add docs-lint rules for memory record schema, allowed statuses/kinds, evidence refs, target refs, and forbidden raw transcript/secret patterns. *(`check_memory_docs` + MEMORY_* constants; journal forbidden-content patterns extended with personal-fact phrasing; both lint pipelines; MemoryRecordLintTests.)*
- [x] Add MCP handlers and tool registrations for `wave_memory_add`, `wave_memory_search`, `wave_memory_brief`, and `wave_memory_reconcile`. *(Mutating/read-only annotations per convention; unknown-args guard; background index refresh on writes. Note: new tools require an MCP reconnect to appear in live sessions.)*
- [x] Update the docs index classifier/chunker path so memory records are indexed as a distinct memory-tagged doc type or tag. *(`_tag_utils.infer_tags`: `docs/agents/memory/` → `memory` tag, shared by chunker and server; records index through the existing docs path and the post-edit hook's `content=all` refresh.)*
- [x] Extend graph extraction to emit memory nodes and edges from `target_refs` / `evidence_refs`, wired through the incremental-merge delta path with query-cache invalidation and a `GRAPH_BUILDER_VERSION` bump. *(Targets → typed `memory_targets` edges; evidence path refs ride the existing backtick-path pass; version 44.)*
- [x] Implement centrality-weighted advisory ranking (betweenness/degree) and community-scoped target refs with briefing grouping. *(`_memory_ranked`: decayed-confidence primary key, persisted-betweenness tie-break from the cluster artifact (artifact-stat-cached, graceful absence → flat); `community:hub:<node-id>` refs group under `community_scoped` in `wave_memory_brief`. Evidence: MemoryToolTests community grouping + HotPathBoundedIOTests centrality-cache count.)*
- [x] Consume the `1ro43` freshness primitive for kind-aware confidence decay in `wave_memory_search` / `wave_memory_brief` ranking. *(`_memory_ranked`: decayed confidence primary, persisted betweenness tie-break with graceful absence.)*
- [x] Add memory snippets to `code_read`, `code_impact`, and `code_callhierarchy` responses when target refs match. *(`memory_advisories` data field, `edit_governance`-style conditional presence.)*
- [x] Add memory advisories to `wave_audit`, `wave_prepare`, and `wave_review`. *(All three lifecycle responses; wave_review also passes phase-agnostic change-id matching.)*
- [x] Update seeds/prompts for pause, review, close, Guru, and implementation to use memory capture and memory briefings. *(Seed 100 lifecycle bullets + new pause-wave bullet; seeds 180/190/211 + 004 naming-boundary section; rendered pause/review/close/implement prompt surfaces + guru.md — behind the seed gate, no internal artifact ids in seed text.)*
- [~] Add dashboard support for memory counts and active advisories if the MCP response model exposes them cleanly. *(Audited 2026-07-13: the response model DOES expose them cleanly (`wave_memory_search`/`wave_memory_brief` structured views), but no AC requires a dashboard panel and the wave's advisory value ships through the MCP surfaces — dashboard panel recorded as optional follow-on scope rather than silently expanding this wave.)*
- [x] Add unit tests and fixture records for all memory kinds, statuses, supersession, and graph refs. *(All eight kinds round-trip + lint fixtures; five statuses; supersession history; graph target refs incl. symbol and community scopes.)*
- [x] Make memory invalidation cross-process and reset-ABA safe when the durable generation write fails; check the indexer's `memory_advance` result and guarantee warm readers fail closed when it cannot advance; add the real two-cache and build-tail round-4 integration matrix. *(Done 2026-07-14 round-4 re-review: `memory_invalidate` is a checked/typed contract (True only on a durable generation advance); the indexer fails the build before bookkeeping on failure so the retry re-detects the edit; writer-owned fence tokens (`memory_writers`) stop one writer clearing another's fence, with a TTL self-heal; two-independent-instance + real child-process + real `build_index` matrix tests landed. Reset-ABA remains defended by the random epoch.)*
- [x] Document `memory-state.sqlite` ownership, MCP/indexer writers, dirty/failure behavior, and cache-key contract in `docs/architecture/data-and-control-flow.md`; remove stale per-target freshness/cache descriptions. *(Verified 2026-07-14: dedicated-store ownership, epoch/generation/dirty keys, tool and indexer writers, `(epoch, generation, dir_mtime)` reader key, dirty/unreadable bypass, and rebuildability are documented.)*
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`. *(5,140 tests OK; docs-lint clean.)*

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
| 2026-07-14 | Delivery round-4 review reopened AC-5, AC-8, and AC-9. Local eviction does not invalidate another MCP process after a failed durable bump; the generation-only key also aliases after `memory-state.sqlite` recreation, and hook-driven raw edits are not invalidated until late optional build work succeeds. | Executed independent two-module cache probe (`active` remained served after disk became `stale`), generation-1 delete/recreate ABA probe, source trace from changed-path detection to the late indexer build-tail bump; full council checkpoint in `wave.md`. |
| 2026-06-28 | Drafted from operator request after research into MCP memory systems and Wavefoundry's existing memory/index/graph capabilities. | Research summary: MCP reference memory server, Mem0/OpenMemory, Graphiti/Zep, Letta/MemGPT, projectmem, Codebase-Memory; local context from `docs/agents/wave-coordinator.md`, `docs/references/wavefoundry-overview.md`, and graph-index docs. |
| 2026-07-04 | Updated for the 1p9q3/1p9qh graph platform: incremental-merge delta path, query cache, build-time betweenness, communities, and symbol-resolution accuracy now underpin Requirements 11–13 and ACs 11–13; kind-aware decay wired to `1ro43-enh churn-aware-retrieval-decay` in the same wave. | Commit 38c52ccd (wave 1p9q3); wave 1p9qh implemented changes; `1ro43` change doc. |
| 2026-07-04 | Readiness-council amendments applied: `fragile_file` churn now sets a needs-reverification flag instead of attenuating confidence (churn on a fragile file is ambiguous evidence, Req 13); advisory surfacing gains named caps, cache-path latency posture, and graceful absence (Req 6). | Prepare-council synthesis in wave record Review Checkpoints. |
| 2026-07-14 | Self-directed adversarial pass (operator-requested; 4 parallel executed-probe reviewers). Core held: ancestry pruning self-defending, fail-closed walks, delimiter injection, cache/generation/symlink atomicity all survived. Fixed further findings: merge-DAG attribution (`-c` in the history walk); parser/lint bullet parity (unsafe `*`-bullet surfaced → mirror lint exactly) + confidence/date grammar alignment (lint now calendar-validates); drift torn write → single `replace_attribution_and_drift` transaction; gardener confirm fail-open + DoS → one `git cat-file --batch` (real error fails closed, one subprocess) + pass-1 truncation guard; heading-less normalization scoped to frontmatter; reader/lint nested-record parity (`is_relative_to`); hash-prefixed drift fingerprint. +14 regression tests; suite 5,352 OK. Full per-finding disposition in the wave record. | Wave record Review Checkpoints (adversarial-pass); `memory_records.py`, `index_state_store.py`, `wave_lint_lib/wave_validators.py`; `tests/test_memory_records.py`, `tests/test_doc_drift.py`, `tests/test_docs_lint.py`. |
| 2026-07-14 | Delivery re-review ROUND 3 remediated (6 findings): per-record symlink read (loader per-candidate containment); cache failure aliasing (typed `read_memory_generation`, atomic bump in a dedicated `memory-state.sqlite` decoupled from canonical state, unconditional post-mutation cache eviction, bypass when generation unreadable); gardener parse-failure + line-shape (patch-structure validation + metadata-scoped content comparison; fenced/body date stays material); history walk fail-open (typed `_collect_git_history` with SHA/parent validation; BOTH walks must succeed before replace); indexer over-invalidation (gated on changed/removed via `_memory_record_touched`); evidence drift (AC-2 ancestry wording, round-2 count/parse-claim corrected). +11 regression tests; suite 5,266 OK. | Wave record Review Checkpoints (round-3 remediation); `memory_records.py`, `index_state_store.py`, `server_impl.py`, `indexer.py`; `tests/test_memory_records.py`, `tests/test_doc_drift.py`, `tests/test_indexer.py`. |
| 2026-07-14 | Delivery re-review ROUND 2 remediated (7 blockers): symlink boundary now covers reads + validates-before-mkdir via the single `canonical_memory_root` chokepoint; runtime parse mirrors all load-bearing lint rules (superseded-link, section bullets); gardener detector returns typed `(ok, pairs)` and preserves prior drift on failure; normalization scoped to the canonical header date line; churn counted over `anchor..HEAD` ancestry (merge-DAG correct) via the `%P` graph; advisory cache keyed on a bounded monotonic memory generation (tool + indexer bumped) — no O(N) walk, no aliasing; centrality task checked + AC-5 warm-cache wording corrected. +23 regression tests; suite 5,254 OK. Full per-finding disposition in the wave record. | Wave record Review Checkpoints (round-2 remediation); `memory_records.py`, `index_state_store.py`, `server_impl.py`, `indexer.py`; `tests/test_memory_records.py`, `tests/test_doc_drift.py`. |
| 2026-07-14 | Delivery re-review round remediated (2 P0 / 6 P1 / 1 P2): symlinked-memory-root escape (root-resolution containment), malformed-record surfacing (fail-closed `parse_memory_record` + lint requires Status/non-empty Summary), creation TOCTOU (`open("x")` exclusive + `create_memory_record` retry), gardener-only drift anchor (`_gardener_only_pairs` material-content detector), stale drift fingerprint (normalized-content digest), timestamps-as-topology (position/ancestry counting), incomplete/echoing secret scan (title+targets scanned, field-only diagnostic), hot-path caches (records+betweenness cached, batched freshness), substring wave matching (exact `_lifecycle_id_tokens`). +96 regression tests; suite 5,242 OK. Full per-finding disposition in the wave record. | Wave record Review Checkpoints (remediation checkpoint); `memory_records.py`, `index_state_store.py`, `server_impl.py`, `wave_lint_lib/wave_validators.py`; `tests/test_memory_records.py`, `tests/test_doc_drift.py`, `tests/test_docs_lint.py`. |
| 2026-07-14 | Delivery-review security finding remediated: caller-supplied `memory_id` (and `supersedes`/`superseded_by`) reached `docs/agents/memory/<id>.md` unvalidated — `../` could escape the memory root through the MCP surface (write via add; `Status:`-line alteration of arbitrary docs via reconcile). Fix: `validate_memory_id` grammar gate (`[a-z0-9][a-z0-9-]*`, max 64) + `_contained_record_path` resolved-path containment at the `memory_records.py` chokepoint; tool-layer pre-write refusals with typed diagnostics. MemoryIdTraversalTests (6 fixtures / 13 evil ids) pin refusal-with-no-side-effects for add AND reconcile; suite 5,146 OK. | Wave record Review Checkpoints (blocker + remediation entries); `memory_records.py`; `tests/test_memory_records.py` MemoryIdTraversalTests. |
| 2026-07-13 | Implementation complete. `memory_records.py` (parse/render/write/reconcile/kind-aware decay via `freshness_for_path`); four `wave_memory_*` MCP tools (forbidden content refused pre-write; record files are source of truth, semantic index an optional assist); `check_memory_docs` lint in both pipelines + `docs/agents/memory/README.md` schema; graph `memory` nodes + `memory_targets` edges on the delta path with the zero-edge-prune exemption (`GRAPH_BUILDER_VERSION` 44); capped advisories on code_read/code_impact/code_callhierarchy + wave_prepare/wave_review/wave_audit; lifecycle capture/distillation directives in seed 100 (+180/190/211/004) and the rendered pause/review/close/implement surfaces. Tests: 25 memory fixtures + 6 graph fixtures + lint fixtures; full suite 5,140 OK. | `memory_records.py`; `tests/test_memory_records.py`; `tests/test_graph_indexer.py` MemoryGraphExtractionTests; `tests/test_docs_lint.py` MemoryRecordLintTests; ADR `1sk58`; AC evidence notes above. |
| 2026-07-13 | Pre-implementation review (executed probes) reconciled the plan with post-readiness landings. Graph substrate VERIFIED intact (1p9q3 store, per-file deltas, three cache-invalidation mechanisms, `GRAPH_BUILDER_VERSION` now "43"); betweenness top-200 persisted; docs-lint/journal-lint and `infer_tags` extension points confirmed. Amendments applied inline: Req 5/AC-4 narrowed graph edge targets (wave/change/lane refs are record fields — those docs are not graph nodes) and added the zero-edge-prune constraint; Req 12 pins community refs to hub node ids. Naming: this doc's "Wave Memory layer" collides with the framework's established "Wave Memory" term (seeds 004/110 = wave-state/handoff continuity model) — this feature is consistently named the **agent memory layer / memory records** in shipped surfaces, and the lifecycle-prompts workstream keeps seed terminology coherent. Seed inventory for prompt updates: lifecycle capture text lands in seed 100 (pause/review/close directives are rendered from it, not standalone seeds) plus 211 (Guru), 180/190 (implement/finalize), 209 (harness core), 004/110 (memory overview/bootstrap) — all behind the `seed_edit_allowed` gate, no internal wave/ADR IDs in shipped seed text. The `1ro43` freshness seam (AC-13) is already satisfied: `freshness_for_path(index_dir, path, since_ts)` is landed, live production code. If memory search consults the semantic index (not just the graph/record store), it adopts the 1sed7 single-capture epoch discipline and the typed degraded-serving contract standard for search-family tools. | Reviewer findings vs `graph_indexer.py` (store :1126, doc extraction :12983, prune :14103, scan excludes :168), `graph_query.py` cache mechanisms, `graph_cluster.py` betweenness/remap, `_tag_utils.py`, `wave_lint_lib` validators, live graph/store probes. |


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
