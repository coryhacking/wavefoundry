# Evidence-derived memory candidates from the review ledger

Change ID: `1stwk-feat evidence-derived-memory-candidates`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-17

Wave: `1stwm memory-supply`

## Rationale

The agent-memory layer (wave 1ro44) shipped in 1.13.0, but the corpus is empty by default: this repo has only the schema README under `docs/agents/memory/`. The lifecycle prompts ask agents to author candidate records, and the close-time distillation checkpoint is a prompt contract, but nothing reliably turns the structured review evidence a wave already produces into records. Supply, not storage or retrieval, is the binding constraint (see the enhancement-plan basis).

`events.jsonl` is now the canonical, typed review authority (`docs/architecture/data-and-control-flow.md` item 9): findings with dispositions, approvals, and runs, plus each change doc's Decision Log. That is a high-signal, already-typed source for durable lessons. This change adds a tool that **drafts** candidate memory records from those authoritative events and preserves the event IDs as evidence, keeping the human-gated promotion and evidence-backing invariants intact. It never ingests raw transcripts and never auto-promotes.

## Requirements

1. **A proposal tool** (`wave_memory_propose`) reads the current heads of a wave's `events.jsonl` (and the wave's admitted change-doc Decision Logs) and drafts candidate memory records. It never reads chat transcripts or any raw conversational stream. **Conservative, durable-signal selection (council re-scope):** it drafts ONLY durable-shaped signals — a file with repeated repairs across waves (`fragile_file`), a validated recurring approach (`successful_pattern`), a decision with lasting import (`decision`), a repair that fixed a real defect (`failed_attempt`) — NOT every material finding. A single-wave `review_finding` is ephemeral wave state already captured in the ledger; drafting all of them would flood the corpus, inverting the "sparse by design" posture.
1a. **Taxonomy limitation (stated honestly).** The typed ledger can only feed the kinds it contains; the cross-wave conversational kinds `operator_preference` and `environment_gotcha`/`dependency_gotcha` emerge from conversation this tool refuses to read and are already served by native `.claude/memory`. This change deliberately does not attempt them — it supplies the ledger-derivable durable kinds, operator authoring covers the rest.
2. **Evidence preservation.** Each drafted candidate carries the originating event ID(s) plus the wave/change IDs and touched file paths as its `## Evidence` refs, so it satisfies the evidence-backing schema natively.
3. **Kind mapping.** Drafts map to the existing 8 kinds deterministically (for example finding → `review_finding`; a repair that fixed a defect in a specific file → `failed_attempt` or `fragile_file`; a Decision Log entry → `decision`; a recorded successful pattern → `successful_pattern`). Ambiguous mappings default to `candidate` status with the mapping noted, never guessed silently.
4. **Human-gated, never auto-promote.** `mode='dry_run'` (default) returns the drafts only. `mode='create'` writes them as `status: candidate` records through the existing `memory_records.py` write path (forbidden-content scan, exclusive create, id-collision retry). Promotion of a candidate to `active` remains an explicit operator `wave_memory_reconcile`; this tool never writes `active` and never supersedes or deletes anything.
5. **Idempotent supply.** Re-running the proposal over the same events does not create duplicates: it consults the exact-duplicate diagnostics (companion change) and skips or flags drafts whose evidence IDs or normalized (kind, target, summary) already exist.
6. **Bounded and cited.** The tool caps drafts per run, cites the source event for each, and returns a `no_material_evidence` diagnostic when the ledger yields nothing durable — consistent with the "sparse by design" posture.
7. **Source-cost stamping (foundation for the exploration-avoided metric).** Each drafted candidate is stamped with its `source_exploration_cost` — a measured proxy for the cost of the wave/repair-cycle that produced it, taken from that source wave's 1stwj telemetry. Precision (council): the 1stwj `## Context Efficiency` block measures context-*avoided*, not context-*consumed*, so the proxy must be a defined measured quantity from the same telemetry that reflects spend — the source wave's total returned/consumed tokens across its retrieval calls (available in the 1stwj per-wave/stage store), not the avoided figure. It is a measured number, never a constant; the exact field is pinned in implementation and documented.
8. **Non-token supply signal.** The tool reports a `records_proposed` / `records_promoted` count as the wave's supply signal (not a token metric) — token savings never become a per-wave target here.

## Scope

**Problem statement:** the memory corpus stays empty because nothing turns a wave's own structured review evidence into candidate records; manual authoring plus a prompt-only distillation checkpoint is too high-friction to populate it.

**In scope (edited under `framework_edit_allowed`):**
- `.wavefoundry/framework/scripts/server_impl.py` — the `wave_memory_propose` tool: read `events.jsonl` heads + admitted change-doc Decision Logs, draft candidates, dry-run/create modes, surface + diagnostics.
- `.wavefoundry/framework/scripts/memory_records.py` (and/or a small helper) — candidate drafting/kind-mapping from typed evidence, reusing the existing write path and schema.
- Reuse the review-evidence reader (`review_evidence.py`) for the canonical `events.jsonl` heads rather than re-parsing bytes.
- Docs — the memory README + MCP tool-surface note; a lifecycle-prompt pointer so review/close suggest running the proposal.
- Tests — drafting from a fixture ledger, evidence-ID preservation, kind mapping, dry-run vs create, forbidden-content refusal, idempotency against the dedup companion.

**Out of scope:**
- **Raw transcript / conversational ingestion** — the explicit non-goal; drafts come only from the typed ledger + Decision Logs.
- **The conversational kinds** `operator_preference` / `environment_gotcha` / `dependency_gotcha` — structurally unavailable from the ledger; left to operator authoring and native memory (stated in Requirement 1a).
- **A per-wave token-savings AC/target** — token savings is an emergent, per-phase-deduped byproduct measured by the shared harness, never a wave target (the Goodhart failure 1stwj rejected).
- **Auto-promotion** — candidates never become `active` without an operator reconcile.
- **Retrieval/ranking changes** — Wave B (memory eval + fusion) owns those.
- **The exact-duplicate detection primitive itself** — companion change `1stwl` (this change consumes it).
- **Cross-repository or global memory.**

## Acceptance Criteria

- [x] AC-1: `wave_memory_propose` drafts candidate records from a wave's `events.jsonl` current heads + admitted change-doc Decision Logs; it reads no raw transcript/conversational source. (required) — `memory_supply.draft_candidates` reads `read_review_event_ledger` heads + change-doc Decision Logs only; no transcript source. Tests `test_drafts_only_code_anchored_decisions`, `test_finding_path_fragile_and_failed_attempt`.
- [x] AC-2: Each drafted candidate carries the originating event ID(s) + wave/change IDs + touched paths as `## Evidence` refs, satisfying the evidence-backing schema. (required) — decision drafts carry `[change_id, wave_id]`; finding drafts carry `[finding_id, evidence_record_id, wave_id]`; targets are the code anchors. Test `test_create_writes_candidate_and_stamps_cost` asserts evidence/target refs on the written record.
- [x] AC-3: Kinds map deterministically to the existing 8 kinds; ambiguous drafts are `candidate` with the mapping noted, never silently guessed. (required) — deterministic mapping: Decision Log → `decision`; repaired do_now finding → `failed_attempt`, or `fragile_file` when a file is repaired more than once in the wave. All drafts are `candidate` status.
- [x] AC-4: `mode='dry_run'` returns drafts only; `mode='create'` writes `status: candidate` via the existing write path (forbidden-content scan applied); the tool never writes `active`, supersedes, or deletes. (required) — `wave_memory_propose_response`; create fences the seqlock, scans `MEMORY_DISALLOWED_PATTERNS`, writes via `create_memory_record`. Tests `test_dry_run_writes_nothing`, `test_create_writes_candidate_and_stamps_cost`.
- [x] AC-5: Re-running over the same evidence is idempotent — no duplicate records — via the exact-duplicate diagnostics. (required) — dedup keys on the 1stwl `normalized_content` signal (the shared wave-id ref is not a skip reason); test `test_create_is_idempotent` (second run promotes 0, one file on disk).
- [x] AC-6: Bounded per run, each draft cites its source event; empty/immaterial ledger returns a `no_material_evidence` diagnostic. (important) — `MEMORY_PROPOSE_CAP`; each draft carries `source_event`; test `test_no_material_evidence_diagnostic`.
- [x] AC-7: Drafting is conservative — only durable-shaped signals (`fragile_file` from repeated repairs, `successful_pattern`, a lasting `decision`, a real-defect `failed_attempt`), NOT every material finding; the conversational kinds (`operator_preference`/`environment_gotcha`/`dependency_gotcha`) are explicitly not attempted. (required) — only code-anchored Decision Logs and repaired (do_now + completed) findings draft; unrepaired/maybe_later findings and prose-only decisions are skipped (`test_conservative_skips_unrepaired_findings`, `test_drafts_only_code_anchored_decisions`). `successful_pattern` is not auto-derivable from the typed ledger and is left to operator authoring (noted below).
- [x] AC-8: Each drafted candidate is stamped with a measured `source_exploration_cost` read from its source wave's `## Context Efficiency` telemetry (never a constant), as the grounding for the exploration-avoided category. (required) — `source_exploration_cost` = `request_debit + response_debit` parsed from the wave's committed `<!-- wave:context-efficiency-state -->` projection; persisted as a `Source exploration cost:` frontmatter line (render/parse in `memory_records.py`). Test asserts `50` for totals `{10,40}`.
- [x] AC-9: The tool reports `records_proposed` / `records_promoted` as the wave's supply signal; there is no per-wave token-savings target/AC. (important) — both counts + `skipped_duplicates` in the response.
- [x] AC-10: Full framework suite green; docs-lint clean. (required) — full suite 5788 OK; `wave_validate` docs-lint ok.

## Tasks

- [x] Add candidate drafting from typed `events.jsonl` heads + Decision Logs (kind mapping, evidence-ref assembly) reusing `review_evidence.py` + `memory_records.py`. — new module `memory_supply.py` (`draft_candidates`).
- [x] Add the `wave_memory_propose` MCP tool (dry_run/create), diagnostics, surfacing. — `wave_memory_propose_response` + `@mcp.tool`.
- [x] Wire exact-duplicate skip/flag (depends on `1stwl`). — dedup on the `normalized_content` signal.
- [x] Lifecycle-prompt pointer (review/close suggest proposing) + memory README + tool-surface note. — seed `004-wave-memory-overview.md` pointer (generic); memory README proposal section (the memory family's tool-surface home).
- [x] Tests: drafting, evidence preservation, kind mapping, modes, forbidden-content refusal, idempotency. — `MemoryProposeTests` (8 tests).
- [x] Full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| draft | framework | — | ledger-heads → candidate drafting + kind mapping |
| tool | framework | draft | `wave_memory_propose` MCP tool + modes + surfacing |
| verify | framework | tool | tests incl. idempotency (needs `1stwl`), docs |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` — edited under `framework_edit_allowed`.
- Depends on the exact-duplicate diagnostics primitive (`1stwl`) for idempotency.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` gets the new tool; the memory README documents the proposal flow. No boundary/layering change — a new read-then-draft tool over existing authorities, writing only `candidate` records through the existing path.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The supply mechanism, sourced only from typed evidence |
| AC-2 | required | Evidence-backing must hold natively |
| AC-3 | required | Deterministic, never-guessed kind mapping |
| AC-4 | required | Human-gated; never auto-promote/supersede/delete |
| AC-5 | required | Idempotent supply — no duplicate flood |
| AC-6 | important | Bounded, cited, honest-when-empty |
| AC-7 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-17 | Change doc authored from the validated memory-enhancement roadmap | Enhancement plan; guru map of the 1ro44 memory layer |
| 2026-07-18 | Implemented `memory_supply.py` (draft_candidates: code-anchored Decision Log rows → `decision`, repaired do_now findings → `failed_attempt`/`fragile_file`), `wave_memory_propose` tool (dry_run/create, fenced write, forbidden scan, idempotent via 1stwl normalized_content), `Source exploration cost:` render/parse in `memory_records.py` (from the wave's committed telemetry projection). Verified on real waves (1rsh9 → 6 code-anchored decisions; 1sufq → 0, prose-only). `successful_pattern` ceded to operator authoring (not cleanly derivable from the typed ledger). Docs: seed 004 pointer + README. Memory suite 93 OK. | `memory_supply.py`; `MemoryProposeTests`; live dry-run on 1rsh9/1sufq |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-17 | Draft from `events.jsonl` heads + Decision Logs only | Typed, canonical, high-signal; satisfies evidence-backing natively | Passive transcript capture (rejected — non-goal, injection surface, duplicates native memory) |
| 2026-07-17 | Write `candidate` only; operator reconcile to promote | Preserves human-gated promotion + never-auto-rewrite invariant | Auto-promote high-confidence drafts (rejected — violates the model) |
| 2026-07-17 | Idempotency via the exact-dup companion | Re-runnable supply without duplicate flood | Free re-drafting (rejected — noise) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-drafting low-signal noise | Bounded per run; draft only from material findings/decisions/repairs; operator promotes |
| Kind mis-mapping | Deterministic mapping; ambiguous → `candidate` with noted mapping, never silent guess |
| Duplicate flood on re-run | AC-5 idempotency via `1stwl` exact-dup diagnostics |
| Evidence leakage of sensitive text | Existing forbidden-content scan on the write path; evidence refs are IDs/paths, not content |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
