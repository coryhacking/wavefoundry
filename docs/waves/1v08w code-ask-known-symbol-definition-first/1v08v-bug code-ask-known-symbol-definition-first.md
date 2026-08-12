# `code_ask` Known-Symbol Definition-First Routing

Change ID: `1v08v-bug code-ask-known-symbol-definition-first`
Change Status: `implementing`
Owner: Engineering
Status: implementing
Last verified: 2026-08-11
Wave: 1v08w code-ask-known-symbol-definition-first

## Rationale

`code_ask` already extracts a symbol from explanatory and navigational questions, but its symbol-first safety net injects the first two generic keyword occurrences and applies the same forced score bonus to each. A call site, test, or mention can therefore outrank the actual declaration even for a direct question such as “where is `_visibleModelId` implemented?”, and the reranker can still label that result high-confidence.

The structural definition machinery behind `code_definition` resolves the declaration correctly. `code_ask` should use that existing signal as a small deterministic correction while retaining its current hybrid retrieval for surrounding context. This is a pre-existing retrieval defect exposed by model-swap smoke testing; it is not part of the supplier-lineage model change.

## Requirements

1. When an explanatory or navigational `code_ask` question already yields a concrete symbol through the existing symbol extractor, consult only the already-published graph snapshot, its structural node metadata, and the existing graph-state source-hash receipt bound to that exact payload to identify one unambiguous, declaration-capable, source-current declaration before final candidate selection. Read graph state through a new fail-closed SQLite read-only helper patterned after `read_state_builder_version`; never instantiate `GraphStateStore` or another mutation-capable session. Read the candidate source file exactly once, hash that buffer, and build the excerpt and inclusive range from the same verified buffer so no hash-then-reread race can produce an unverified citation. This is a language-neutral graph-node contract: it applies to Python and every registered `mode="code"` graph language wherever the published graph emits a declaration-capable exact node, without a new routing-language allowlist. Do not call `code_definition_response`, add another general question classifier, or add another model inference.
2. When an exact declaration is found, keep that declaration ahead of generic keyword occurrences, call sites, tests, and prose mentions for the named symbol. A compound question may still return broader semantic and structural evidence after the declaration.
3. Restrict forced symbol promotion to a structurally confirmed exact declaration. Generic keyword occurrences may remain in the candidate pool and be reranked on their own merit, but must not receive the declaration preference merely because they contain the symbol text.
4. Preserve the existing hybrid retrieval and public response shape. Do not add a new search mode, ranking subsystem, response field, or pure-lookup short circuit. The defensive lookup must not build or refresh an index, invalidate a graph cache, call the public definition resolver, run a full-repository structural scan, or use keyword fallback as structural confirmation. When the graph is absent, stale, ambiguous, or has no exact declaration, preserve the current hybrid behavior without error and without suppressing broad results.
5. Align the canonical Guru and implementation guidance with the corrected behavior: `code_definition` remains the preferred direct tool for a known-symbol lookup, while `code_ask` defensively places a confirmed declaration first when a broader question names that symbol. Update seed `211` as the canonical installation template, mirror only the narrow tool-selection sentence into the existing self-hosted `docs/agents/guru.md` outside generated marker regions, and use `render_agent_surfaces.py` only to verify wrapper/marker stability rather than to overwrite the local Guru document.

## Scope

**Problem statement:** `code_ask` can promote a symbol usage instead of its declaration because generic keyword matches, not structural definitions, own the current symbol-injection preference.

**In scope:**

- The existing symbol-injection and candidate-selection seam in `WaveIndex.search_combined`.
- Read-only reuse of the already-published graph snapshot, structural node metadata, and the existing SQLite graph-state source-hash receipt after proving its fingerprint/stat binding to that payload; no public definition resolver, graph refresh, mutable state-store construction, or duplicate language parser.
- Focused regression coverage in the existing server-tools test suite, including an adversarial usage-before-definition case and a representative parameterized language matrix covering Python, JavaScript/TypeScript, Java, C#, C/C++, Go, Rust, Kotlin, and Swift. Map Scala, Ruby, and PHP to their existing graph-extraction fixtures, add focused Bash and Objective-C graph declaration fixtures in the existing graph-indexer suite, and add a language-neutral routing assertion; do not duplicate each language parser inside `code_ask` tests.
- The canonical Guru seed, canonical implementation seed, rendered Guru guidance, MCP tool guidance, and the existing search- and graph-architecture descriptions.

**Out of scope:**

- Embedding or reranker model changes, new benchmarks, or threshold tuning.
- A new query-intent classifier, new search mode, new response schema, or general ranking rewrite.
- Changing `code_definition`, `code_references`, graph artifact schema/builder version, or graph extraction behavior. A new read-only graph-state receipt helper is in scope; graph-state writes and recovery remain unchanged.
- Guaranteeing definition-first behavior when a question does not name a concrete resolvable symbol.
- Folding this pre-existing defect into wave `1v0r0 supplier-lineage-compliant-retrieval`.

## Acceptance Criteria

- [x] AC-1: A public `code_ask` navigational query naming a resolvable symbol returns the exact declaration ahead of call sites, tests, summaries, and prose mentions, even when those competing occurrences appear first in keyword results or receive a higher mocked reranker score. The behavior is language-neutral for Python and every registered `mode="code"` graph language wherever the published graph supplies a declaration-capable exact node; public regression coverage includes Python, JavaScript/TypeScript, Java, C#, C/C++, Go, Rust, Kotlin, and Swift, graph-extraction fixtures cover Bash, Objective-C, Scala, Ruby, and PHP, and a routing assertion proves no language allowlist is added.
- [x] AC-2: A compound explanatory question naming a resolvable symbol keeps the exact declaration first while retaining relevant broader citations or structural context after it.
- [x] AC-3: Only a structurally confirmed exact declaration whose declaration-capable graph kind and single-read live-source buffer SHA-256 match the bound read-only graph-state receipt receives forced symbol preference; the excerpt/range is built from that same verified buffer, and a generic injected usage, `code-summary`, non-declaration graph node, source-stale graph node, or hash-then-reread substitution cannot receive or retain the declaration preference.
- [x] AC-4: An absent, builder-stale, source-stale, state-receipt-missing/unbound/mismatched, ambiguous, non-declaration-kind, or unresolvable graph symbol and a question with no extracted symbol retain the current hybrid fallback, response keys, and error behavior. The receipt/race matrix covers missing/corrupt/pending state, fingerprint/size/mtime mismatch, payload replacement during observation, and source mutation while proving one source read supplies both SHA-256 and rendered excerpt/range. Every fallback asserts the baseline response-key set and exactly two embedding calls; focused spies prove `code_ask` does not instantiate `GraphStateStore`, call `code_definition_response`, `index_build_response`, graph-cache invalidation, full-repository structural scanners, or keyword fallback for structural confirmation, and no new search mode, response field, or model inference is introduced.
- [x] AC-5: Canonical seed guidance, rendered Guru guidance, MCP tool guidance, and search-architecture prose consistently state that direct structural tools remain preferred for known-symbol lookup and that `code_ask` now provides a defensive definition-first correction.

## Tasks

- [x] Replace generic symbol preference in `WaveIndex.search_combined` with a bounded, language-neutral lookup against the already-published graph snapshot and exact node metadata, while retaining ordinary keyword/semantic candidates and avoiding the mutation-capable public definition resolver.
- [x] Limit `_SYMBOL_INJECTION_BOOST` or its equivalent preference marker to structurally confirmed, declaration-capable, source-current exact declarations; read/hash/render from one source buffer and do not boost generic usages or summaries automatically.
- [x] Add a bounded read-only graph-state helper that returns a source hash only after the SQLite receipt is proven bound to the exact published payload fingerprint/size/mtime; fail closed on missing, corrupt, pending, fingerprint-mismatched, size-mismatched, mtime-mismatched, or concurrently replaced payload/state and test the full matrix in the existing graph-indexer owner without constructing `GraphStateStore`.
- [x] Extend existing `test_server_tools.py` owners with adversarial declaration-versus-usage ordering across the AC-1 representative language matrix, compound-query, summary-collision, graph-only-range, source mutation/single-buffer proof, non-declaration-kind, and expanded fallback tests; every fallback asserts exactly two embedding calls and the baseline response-key set, spies the mutable-store/index-build/cache-invalidation/public-resolver/full-scan seams on misses, maps Scala/Ruby/PHP to existing graph fixtures, adds Bash/Objective-C graph declaration fixtures, and avoids a parallel test suite.
- [x] Update `.wavefoundry/framework/seeds/211-guru.prompt.md` and `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` with the narrow corrected guidance.
- [x] Mirror the narrow seed-211 tool-selection correction into the existing self-hosted `docs/agents/guru.md` outside generated marker regions; run `render_agent_surfaces.py` only as a stability check, and update `docs/specs/mcp-tool-surface.md` plus `docs/architecture/search-architecture.md` only where definition-first behavior is described.
- [x] Run focused graph-state, retrieval/server, render, docs-lint, and canonical framework verification after the repair.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| read-only graph-state receipt helper and tests | implementer | — | Write-owning lane for `graph_indexer.py` and `test_graph_indexer.py`; publishes the bounded read-only helper consumed by retrieval |
| definition-first behavior and regression tests | implementer | read-only graph-state receipt helper and tests | Write-owning lane for `server_impl.py` and `test_server_tools.py` |
| canonical guidance and local Guru surface | implementer | behavior contract | Write-owning lane for seeds and narrow hand-authored guidance; preserve renderer-owned marker regions |
| verification | qa-reviewer | both workstreams | Read-only review lane; mutation-challenge usage-before-definition and fallback cases |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `.wavefoundry/framework/seeds/211-guru.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `docs/agents/guru.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/graph-index-system.md`

Protected/generated surface: seed `211` is the canonical installation template, while the self-hosted `docs/agents/guru.md` also contains project-local material. Mirror only the narrow tool-selection correction outside renderer-owned marker regions; do not regenerate or replace the whole local document. Reviewer lanes are read-only.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — update only the existing `code_ask` symbol-injection/candidate-selection description. No architecture hub or boundary change is required.
- `docs/architecture/graph-index-system.md` — reconcile the graph owner's consumer description with `code_ask`'s read-only structural ranking signal and bound graph-state receipt. No graph schema/build/extraction change is required.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Corrects the observed wrong-owner result on the public path. |
| AC-2 | important | Preserves `code_ask` value for cross-cutting questions instead of turning it into a pure lookup tool. |
| AC-3 | required | Prevents the current false-positive mechanism from surviving under a renamed marker. |
| AC-4 | required | Keeps the change incremental and protects existing fallback/API behavior. |
| AC-5 | required | Prevents canonical seed and rendered guidance from contradicting the corrected tool behavior. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-11 | Planned after live smoke tests showed known-symbol `code_ask` queries ranking call sites/tests above exact definitions while direct `code_definition` resolved both symbols correctly. | Live `_visibleModelId` and `_cleanup_version_eligible` smoke queries; current `search_combined`, `_agent_rerank`, and `code_definition_response` reads |
| 2026-08-11 | Readiness review narrowed the implementation to an already-published graph snapshot, prohibited mutation-capable/full-scan definition fallback, and corrected local Guru ownership. | Independent red-team, code/QA/architecture feasibility, and docs-contract reviews |
| 2026-08-11 | Thought: implement in three ordered actions — add a read-only exact-node probe plus post-selection pin, replace the existing symbol-injection tests with public adversarial/fallback coverage, then align the two seeds and three living docs before focused and canonical verification. | `wf_implement_wave` activation; pre-implementation memory brief; MCP reads of `search_combined`, `_node_def_candidate`, `_agent_rerank`, and current test owners |
| 2026-08-11 | Gapfill: the published project graph is a gzip artifact excluded from indexed code retrieval, so a bounded `gzip -dc | jq` inspection verified exactly one function node for each live smoke symbol before editing. | Builder v45 nodes for `_visibleModelId` at `dashboard.js:3819` and `_cleanup_version_eligible` at `upgrade_wavefoundry.py:2455` |
| 2026-08-11 | Observe: the first implementation slice passes seven focused tests, including public Python/JavaScript adversarial ranking, compound context retention, and stale/ambiguous read-only fallback. Thought: align only the five named guidance carriers and the `code_ask` tool docstring, preserving direct `code_definition` preference. | `RerankerTests` focused run: 7/7 OK in 2.443s |
| 2026-08-11 | Observe: implementation is complete. All five ACs and six tasks are checked; the complete reranker owner, renderer owner, docs lint, and canonical framework suite pass. | `RerankerTests` 97/97; `test_render_agent_surfaces.py` 63/63; `wf_validate_docs` clean; canonical 7,170/7,170 across 62 files in 246.711s |
| 2026-08-11 | Scope correction after delivery review: AC-1 is language-neutral wherever the published graph supplies a declaration-capable node, not limited to Python and JavaScript. Reopened the affected status, ACs, and implementation/test tasks while the summary-collision, citation-range, declaration-kind, source-binding, and expanded language-matrix repairs remain outstanding. | Operator directive; `_TS_LANGUAGE_PROFILES` code modes and `_TS_EXTENSION_TO_LANGUAGE` census in `graph_indexer.py`; delivery findings recorded in `events.jsonl` |
| 2026-08-11 | Readiness repair reconciled the source-stale contract without changing the graph artifact: add a fail-closed read-only SQLite receipt helper, prove its fingerprint/stat binding to the published payload, and compare the candidate file hash before promotion. The representative public matrix covers the major grammar families; the five remaining code profiles map to existing extractor fixtures plus a no-language-allowlist assertion. | Fresh red-team/code-readiness review; `read_state_builder_version`, `GraphStateStore.files(source_hash)`, and payload binding metadata reads in `graph_indexer.py` |
| 2026-08-11 | Implemented the language-neutral repair: one read-only SQLite statement binds the exact opened payload to its source hash, one source buffer supplies verification and citation text, declaration kinds gate authority, same-line summaries are replaced by the verified candidate, and inclusive ranges are correct. Expanded public and graph-owner regressions cover the language, receipt/race, fallback, collision, and no-extra-inference boundaries. | `RerankerTests` 102/102; `BoundGraphReceiptTests` 4/4; renderer 63/63; docs-lint clean; canonical 7,181/7,181 across 62 files in 232.214s |
| 2026-08-11 | Delivery QA found and the implementer repaired one test-integrity gap: fallback response keys now compare against an explicit canonical set, and source-hash mismatch receives the same key, two-embedding, and forbidden-seam checks as every other fallback. | Focused fallback tests 2/2; `RerankerTests` 102/102; the previously surviving global `total_ms`-removal mutant now fails every fallback row |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-11 | Select structurally confirmed definition-first preference with ordinary hybrid fallback. | It deterministically fixes the owner-ranking error through an existing capability without changing models, schemas, or the general retrieval pipeline. | Score-only tuning was rejected because it remains model-dependent and can boost usages; a new intent classifier plus exact-search mode was rejected because it broadens the contract and implementation. |
| 2026-08-11 | Keep the change separate from supplier-lineage wave `1v0r0`. | The faulty routing and confidence conditions predate the model swap; the new model only exposed the weakness. | Expanding `1v0r0` would mix an existing retrieval defect into a release/model-supplier change. |
| 2026-08-11 | Keep direct structural tools preferred in agent guidance. | `code_definition` remains the most precise and cheapest explicit lookup, while `code_ask` needs a defensive correction for broader questions that happen to name a symbol. | Recommending `code_ask` for every known-symbol lookup would add unnecessary semantic retrieval. |
| 2026-08-11 | Resolve defensive owners from the already-published graph only. | `code_definition_response` can refresh the graph and enter slow fallback scans, which is inappropriate inside observational `code_ask`; a final deterministic pin is required because a bounded score bonus cannot defeat an adversarial reranker score. | Calling the public resolver or increasing the score bonus was rejected as mutation-prone or model-dependent. |
| 2026-08-11 | Bind graph declarations to current source through the existing SQLite graph-state receipt, opened read-only and verified against the exact published payload. | The JSON graph nodes do not carry source hashes, while constructing `GraphStateStore` can mutate; a direct read-only URI probe reuses the already-published receipt without changing artifact schema or builder behavior. | Co-publishing hashes in the graph JSON would require an artifact/version change; dropping source-stale rejection would permit a wrong declaration excerpt to be pinned. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Plain-language text is mistaken for a symbol. | Apply preference only after structural resolution returns an exact declaration; otherwise preserve the existing path. |
| Structural lookup adds hot-path work or mutation. | Read only the already-published graph snapshot after extraction; never call the mutation-capable public resolver, build/refresh an index, invalidate caches, full-walk the repository, or add model inference. |
| A hard pin hides useful context. | Pin only the confirmed declaration; retain normal semantic/structural evidence after it. |
| Seed and self-hosted guidance drift. | Edit canonical seed wording first, mirror only the narrow sentence into the local Guru doc outside generated regions, and run render stability plus docs-lint tests. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
