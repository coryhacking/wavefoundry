# Guru — Spec-Top-Citation Hardening + Agent Rename

Change ID: `12q8t-enh cia-spec-top-citation-hardening`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-18
Wave: 12pn3 search-retrieval-quality

## Rationale

A Guru session on span attribute masking revealed two compounding failure modes. An explanatory question ("how does span attribute masking work?") returned a spec doc as the highest-ranked citation. The agent synthesized from the spec without reading the implementation — missing several undocumented behaviors only visible in source: substring skip patterns, a ConcurrentHashMap cache trim at MAX_CACHE_SIZE=4096, Throwable fingerprinting via SHA-256, and a `com.sun.*` skip rule for Java 9+ illegal access warnings. When `code_read` was eventually called, all of these were confirmed. The reranker was correct — the spec was semantically the best match. The failure was in synthesis: the agent rationalized around a required follow-up because the spec citation looked authoritative.

A second failure compounded the first: when `code_read` was finally called, it read the entire 1,072-line file to answer a question requiring ~150 lines across four methods, because `code_outline` was not used first.

The index, reranker, and partition logic were not at fault. The fix is partly structural (a `validation_required` field that agents cannot rationalize around) and partly behavioral (explicit spec-top-citation and large-file-read rules in seed-211 and the Guru role doc).

## Requirements

1. `code_ask_response()` in `server.py` emits `validation_required: True` in the response payload when `question_type == "explanatory"` and the top citation `kind` is `"doc"` or `"doc-summary"`. A single spec citation at rank 1 is sufficient to trigger — not "top 2 both doc".
2. `code_ask_response()` emits `next_tools: ["code_outline", "code_read"]` (replacing `["code_read", "docs_search"]`) when the top citation's source file exceeds 300 lines and `code_read` would otherwise be the recommended next tool. The file line count is determined by reading the file at response construction time; if the read fails, fall back to the default `next_tools`.
3. The `code_ask` MCP tool docstring is updated to state explicitly: when `validation_required: true` is present, `code_read` in `next_tools` is a required continuation, not optional.
4. `seed-211` Pass 3 gains two new rules:
 a. **Spec-top-citation rule:** When `code_ask` returns a spec or architecture doc as the highest-ranked citation for an explanatory question, that spec is the starting point — not the answer. Read the implementation file named in the spec's source metadata field before synthesizing. Look for any field naming a source file (`Verification method:`, `Source:`, `Derived from:`, or similar) and follow it. This is not optional.
 b. **Large-file read discipline:** Before calling `code_read` on any file, call `code_outline(path)` first to get the full symbol map. Identify the specific methods that answer the question, then call `code_read` with `start_line` and `end_line` for only those ranges.
5. `seed-211` Pass 1→3 shortcut exception is extended: when orientation returns only `kind="doc"` results for an explanatory question, do not skip to synthesis — proceed to Pass 3 using `code_outline` + targeted `code_read` on the implementation file named in the doc's source metadata.
6. `seed-211` gains a closing **Incident documentation** section: when a Guru session reveals a systematic retrieval failure mode, record it as an Incident in `docs/agents/journals/guru.md` and evaluate whether seed-211 or the `code_ask` tool description requires a hardening change.
7. The Guru role doc (`docs/agents/guru.md`) gains an explicit self-audit rule: "Do not skip a tool listed in `next_tools` without recording the reason. When a skipped tool call would have produced a more complete or verified answer, record it in the Guru journal before closing the session."
8. The agent is renamed from **Code Insight Agent (CIA)** to **Guru**. Rationale: "Guru" carries strong semantic priming inside LLMs for deep, authoritative, domain-specific expertise — the model has seen "the Kubernetes guru," "the billing guru," "ask the guru" thousands of times and primes confident, cited, low-hedging behavior. "Code Insight Agent" / "CIA" carries no such prior. The rename covers: seed file, role doc, journal, shortcut, all active doc references. Historical wave docs are left unchanged (they are records of past work).

## Scope

**Problem statement:** Guru agents rationalize around required tool calls when a high-confidence spec citation appears. The existing prose guidance is insufficient — agents skip `code_read` because the spec looks authoritative. A second failure: large files are read in full when targeted reads would suffice.

**In scope:**

- `validation_required` field in `code_ask_response()` (`server.py`)
- Dynamic `next_tools` emission based on top citation file size (`server.py`)
- `code_ask` docstring update (`server.py`)
- seed-211 spec-top-citation rule, large-file read discipline, Pass 1→3 exception, Incident documentation section
- Guru role doc self-audit rule

**Out of scope:**

- Changes to the reranker, index, or partition logic (confirmed not at fault)
- Changes to `seed-009` (Guru feedback loop belongs in seed-211, not the general maintenance contract)
- Enforcing `code_outline` for files under 300 lines

## Acceptance Criteria

- AC-1: `code_ask` response for an explanatory question where the top citation is a spec doc includes `validation_required: true`.
- AC-2: `code_ask` response for an explanatory question where the top citation file exceeds 300 lines includes `next_tools: ["code_outline", "code_read"]`.
- AC-3: `code_ask` response for a navigational question does not include `validation_required`.
- AC-4: `code_ask` response when top citation is `kind="code"` does not include `validation_required`.
- AC-5: seed-211 Pass 3 contains the spec-top-citation rule and large-file read discipline.
- AC-6: seed-211 Pass 1→3 shortcut exception covers the doc-only orientation result case.
- AC-7: seed-211 contains an Incident documentation section.
- AC-8: Guru role doc contains an explicit self-audit rule for skipped `next_tools` calls.
- AC-9: All existing tests pass.
- AC-10: Primary shortcut is **Guru** in `docs/prompts/index.md`; legacy aliases **Ask codebase**, **Ask CIA**, and **Code insight** route to Guru.
- AC-11: Seed at `.wavefoundry/framework/seeds/211-guru.prompt.md`; role doc at `docs/agents/guru.md`; journal at `docs/agents/journals/guru.md` with `Role: guru`.
- AC-12: Active framework seeds and agent prompts reference Guru paths (historical wave docs unchanged).

## Tasks

- In `server.py` `code_ask_response()`, after assembling `data` dict and before `_response()` call:
 - Add: `if question_type == "explanatory" and citations and citations[0].get("kind") in ("doc", "doc-summary"): data["validation_required"] = True`
 - For `next_tools`: compute file line count for `citations[0]["path"]`; if > 300 and `code_read` would be emitted, use `["code_outline", "code_read"]` instead of `["code_read", "docs_search"]`
- Update `code_ask` MCP tool docstring: add a note that when `validation_required: true` is present, `code_read` in `next_tools` is a required continuation
- Open seed gate, edit `seed-211` Pass 3, close gate
- Update Guru role doc (`docs/agents/guru.md`) with self-audit rule
- Rename: `211-code-insight-agent.prompt.md` → `211-guru.prompt.md`; `docs/agents/code-insight-agent.md` → `docs/agents/guru.md`; journal → `docs/agents/journals/guru.md`; update active references (seeds 010/030/050/100/160/214, `AGENTS.md`, `docs/prompts/index.md`, agent prompt bodies, `search-architecture.md`)
- Add unit tests:
 - `test_validation_required_explanatory_doc_top`: emitted when explanatory + doc top citation
 - `test_validation_required_not_emitted_navigational`: not emitted for navigational
 - `test_validation_required_not_emitted_code_top`: not emitted when top citation is code
 - `test_next_tools_outline_for_large_file`: `code_outline` prepended when top citation file > 300 lines
 - `test_next_tools_no_outline_for_small_file`: default `next_tools` when top citation file ≤ 300 lines

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------------- | ------------------ | ------------- | --------------------------------------------------- |
| server-fields | framework-engineer | — | validation_required + dynamic next_tools in server.py |
| server-docstring | framework-engineer | — | code_ask docstring update |
| seed-211 | framework-engineer | — | Pass 3 rules + shortcut exception + incident section |
| guru-role-doc | framework-engineer | — | Self-audit rule in docs/agents/guru.md |
| guru-rename | framework-engineer | — | Three file renames + active reference sweep |
| tests | framework-engineer | server-fields | Unit tests for new response fields |

## Serialization Points

- `server-fields` must land before `tests`; all other workstreams are independent

## Affected Architecture Docs

N/A — confined to `server.py` response construction and agent behavioral docs; no boundary, data-flow, or index impact.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required | Primary structural fix — the durable hardening |
| AC-2 | required | Large-file discipline at the server level |
| AC-3 | required | Must not over-fire |
| AC-4 | required | Must not over-fire |
| AC-5 | required | Belt-and-suspenders for agents on older server versions |
| AC-6 | required | Closes the Pass 1→3 shortcut loophole |
| AC-7 | nice-to-have | Feedback loop — useful but not blocking |
| AC-8 | required | Self-audit creates repo-local feedback path |
| AC-9 | required | No regression |
| AC-10 | required | Guru shortcut and legacy aliases |
| AC-11 | required | Rename file paths |
| AC-12 | required | Active reference sweep |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Implemented. Hardening: `validation_required`, dynamic `next_tools`, seed-211 rules, Guru self-audit, 5 unit tests. Rename: CIA → Guru (seed `211-guru.prompt.md`, `docs/agents/guru.md`, `docs/agents/journals/guru.md`, shortcut **Guru**, legacy aliases preserved). Active doc/seed references updated; historical wave docs unchanged. 1352 tests pass. | `run_tests.py` OK |
| 2026-05-18 | Follow-on: architecture write-up escalation in Guru seed + role doc; `chunking-and-indexing-pipeline.md` registered in `docs/ARCHITECTURE.md`; architecture-reviewer collaboration note. Motivated by shallow “how are docs chunked?” chat answer vs full pipeline doc. | `docs/agents/guru.md`, `211-guru.prompt.md` |

## Follow-on (same change — behavioral docs)

Generic workflow in **seed-211** / **seed-214**; project pointers in `docs/agents/guru.md` and `docs/agents/architecture-reviewer.md`. Guru must consult **council-moderator** on architecture-doc escalations when council policy is enabled.

**Reference implementation:** `docs/architecture/chunking-and-indexing-pipeline.md`.

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-18 | `validation_required` fires when top-1 citation is doc, not top-2 | Single spec at rank 1 is the exact failure case; top-2 condition is too conservative | Top-2 both doc (misses the primary failure case) |
| 2026-05-18 | 300-line threshold for `code_outline` injection into `next_tools` | Files under 300 lines are cheap to read in full; files above 300 lines have enough symbols that outline navigation pays for itself | 500 lines (too permissive); always (noisy for small files) |
| 2026-05-18 | Incident documentation in seed-211, not seed-009 | seed-009 is the general maintenance contract; Guru-specific feedback loop is out of scope there | seed-009 (wrong scope) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `validation_required` fires for doc citations that ARE the correct answer (e.g. navigational queries to a spec) | Condition is scoped to `question_type == "explanatory"` only; navigational queries are unaffected |
| File line count read at response time adds latency | File read is a local OS stat + line count; typically <1ms; negligible vs 25s reranker |
| seed-211 rule verbosity | Rules are additive and scoped to Pass 3; existing structure is unchanged |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
