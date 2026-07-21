# Standardized Read Surface for the Review-Evidence Ledger

Change ID: `1t6ow-enh review-evidence-list-action`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-21
Wave: `1t59p wf-audit-bounded-index-health`

## Rationale

`wf_review_evidence` is a writer (with dry-run preview) and the wave.md projection is a compact summary, so there is no first-class way to inspect the raw `events.jsonl` chain state before appending to it. In practice agents fall back to ad-hoc `python3` heredoc snippets that `json.loads` the ledger to see record shapes, lanes, cycles, and finding heads (the operator observed this repeatedly across waves 1seax and 1t59p, including three writes that were initially rejected because the caller could not see the required lane and actor fields without a manual dump). A standardized read action removes the ad-hoc scripting, makes chain state discoverable through `next_tools`, and gives every host the same bounded, typed view of the ledger.

## Requirements

1. **Read action on the existing tool:** `wf_review_evidence(event="list")` returns ledger records read-only. For this event, `actor` and `context_id` are accepted but not semantically required (pass-through identity only); `mode` is ignored; nothing is ever written, serialized under no lock, and the call succeeds on a wave whose ledger is absent or empty (returns an empty listing with a diagnostic, never an error).
2. **Record projection:** each returned record carries a stable identity (`record_id` / `evidence_record_id` / `review_run_id`, whichever the record type defines), `record_type`, `run_kind`, `cycle`, `finding_id` (when present), `disposition`, `repair_execution_state`, `source_lanes` / `blocking_required_lanes` / `approval_recheck_lanes`, `supersedes_record_id`, `claim_kind` / `claim_id` / `signoff_key` for evidence records, and the `verification_context` (actor, context_id, fresh/independent flags). Full evidence bodies (proposition/observed/etc.) are included only when `verbose` is requested; the default row is the compact index an appender needs.
3. **Chain summary:** the response carries a derived per-finding summary: current head record ID, disposition, repair state, unresolved required lanes, and whether the head is terminal — the same derivation the close gate uses, so an appender can see what the gate will see. Approvals summarize per signoff key with currency (follows-every-affected-repair or not).
4. **Filters and bounds:** optional `finding_id` and `record_type` filters; output bounded (cap with an explicit truncation marker naming the total), never an unbounded dump of a large ledger.
5. **Discoverability weave:** `wf_review_evidence`'s docstring documents the list event; write-path validation errors that depend on existing chain state (for example the required-lane and same-actor rules) name the list event in their recovery hints; the canonical review-evidence protocol seed gains a one-line pointer that chain state is inspected via the list event, not by hand-parsing `events.jsonl` (seed gate applies; no restating of the write contract).
6. **No write-path changes:** the append/validation semantics of the existing events are untouched.

## Scope

**Problem statement:** the review-evidence ledger has a typed write surface but no typed read surface, so correct appends require ad-hoc file parsing.

**In scope:**

- `wf_review_evidence` list event in `server_impl.py` (+ `review_evidence.py` reader helpers if the parsing lives there today)
- Focused tests: listing shapes, filters, bounds/truncation, chain summary parity with the close gate derivation, absent/empty ledger, read-only proof (no lock taken, no file mtime change)
- `docs/specs/mcp-tool-surface.md` Tool Detail entry; recovery-hint updates; the protocol seed pointer (seed gate)

**Out of scope:**

- Any change to write/append validation semantics
- A separate new tool name (the surface stays on `wf_review_evidence`)
- Dashboard rendering of the ledger

## Acceptance Criteria

- [x] AC-1: `wf_review_evidence(event="list")` returns the compact record index with the Requirement 2 fields, honors `finding_id`/`record_type` filters, and bounds output with an explicit truncation marker.
- [x] AC-2: the response's per-finding chain summary matches the close gate's derivation (head, terminal state, unresolved required lanes) on a fixture ledger with a multi-cycle repair chain, verified by test against the same derivation the gate uses (no duplicated logic drifting apart).
- [x] AC-3: the list event is read-only: proven by test that no lifecycle lock is taken and the ledger file is byte-identical after the call; absent/empty ledgers return an empty listing without error.
- [x] AC-4: write-path lane/actor validation errors name the list event in recovery hints; the tool docstring and spec Tool Detail document the read surface; the protocol seed carries the one-line pointer.
- [x] AC-5: full framework test suite and docs validation pass (6,102 tests across 59 files, OK, 2026-07-21; docs-lint ok).

## Tasks

- [x] Confirm where the close gate derives chain state today and expose that derivation for reuse (single source, no parallel reimplementation). (No extraction needed: current_synthesis_heads/review_status_rows/review_evidence_summary already exist and the gate consumes them; the list event composes them directly.)
- [x] Implement the list event (projection, filters, bounds, chain summary) with tests. (_review_evidence_list_response + branch-before-validation; ReviewEvidenceListEventTests, 7 tests, canonical-writer fixtures.)
- [x] Wire recovery hints, docstring, spec entry, and the seed pointer (seed gate). (Both invalid_review_event sites name event='list'; tool docstring + spec Tool Detail; seed 209 one-line pointer.)
- [x] Full suite + docs validation. (6,102/6,102 OK; docs-lint ok; two live reload + probe rounds.)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| derivation-reuse | implementer | — | Locate/expose the gate's chain derivation first |
| list-event | implementer | derivation-reuse | Projection, filters, bounds, summary + tests |
| docs-weave | docs-contract-reviewer | list-event | Spec, docstring, recovery hints, seed pointer |

## Serialization Points

- The chain-derivation reuse lands before the list event so the summary and the close gate share one implementation.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (Tool Detail for the list event). No architecture-boundary change; the review-evidence protocol seed gains only a discoverability pointer.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The read surface itself. |
| AC-2 | required | Gate-parity is the point: appenders must see what the gate sees; a drifting parallel derivation would be a third truth. |
| AC-3 | required | Read-only guarantee is the safety contract. |
| AC-4 | required | Discoverability is why this beats the ad-hoc script. |
| AC-5 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-21 | Drafted from operator direction after repeated ad-hoc ledger-dump scripts were observed across 1seax/1t59p; three ledger writes in those waves were initially rejected for lane/actor fields discoverable only by hand-parsing events.jsonl. | Session observations; rejected-write envelopes (1seax repair_start, 1t59p repair_start and lane clearance). |
| 2026-07-21 | Implemented and live-verified: list event composes the gate's own derivations; 9 tests incl. read-only/lock-free proof and canonical-envelope fixtures; recovery hints fired on their first real rejected write (the repair_start ordering error) before this row was written. | ReviewEvidenceListEventTests; live filtered list on the 1t59p ledger. |
| 2026-07-21 | Operator extension: CE state-source credit for the list event (the response conveys whole-ledger state via summary/chain/approvals, so it credits events.jsonl through the canonical once-only source-proof machinery). Live verification then CAUGHT a pre-existing 1t3ek defect: artifact extractors' int `0` early returns made the per-artifact cost recorder throw and silently drop the ENTIRE debit row for every non-create wf_review_evidence response; repaired with list-typed returns at all three sites + a regression test on the wrapper's exact consumption expression. Post-repair live proof: repeat list calls debit (telemetry 10 to 11) but never re-credit (source_credit 109 to 109) — the once-only rule holds. | `ev-artifact-extractor-int-return-drops-telemetry*`; telemetry/source_credit row censuses 2026-07-21. |
| 2026-07-21 | Neutral-repeat policy implemented (content-hash event identity feeding the store's replay dedup) and live-verified: an identical-content pair with DIFFERENT actor/context recorded one measured call then one fully neutral call (telemetry 13 to 14 to 14; credit 124 flat). During verification, wf_reload_mcp refused on a phantom wave key `1t6ow` (a change ID focused by a stale-code session through the unresolved-argument fall-through in `_lifecycle_context_result`); operator approved the store retirement (compact idiom: tombstone + delete, 1 telemetry + 1 wave_state row) plus two hardenings: focus gated on wave resolution (left untouched, never nulled, on failure) and the projection barrier now skips unknown wave keys with `skipped_unknown_waves` instead of refusing reload/upgrade. Both reproduced hermetically. | `ev-unresolved-wave-focus-creates-phantom-telemetry-*`; neutrality probe counts; test_server_context_efficiency 64/64. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-21 | Extend `wf_review_evidence` with a list event rather than adding a new tool. | Keeps the ledger surface single-named and discoverable; avoids growing the 82-tool surface. | New `wf_review_evidence_list` tool; MCP resource template (rejected: resources return raw markdown, not the typed filtered projection appenders need). |
| 2026-07-21 | Operator policy: identical-content repeat listings are NEUTRAL (0 credit, 0 debit) via a content-hash event identity; the first listing of a ledger version earns the state-source credit. | A repeat unchanged-version read is an operational check, not retrieval work: crediting it would manufacture savings, and debiting it distorts the headline against a check that surfaced nothing new. The response hash is the version identity (same ledger version + filters + verbosity => same response), so caller identity variations stay neutral while any real change measures normally. | Debit-only repeats (operator: punitive); duplicate credit (inflates savings); separate operational-overhead bucket (more machinery than the policy needs). |
| 2026-07-21 | Chain summary reuses the close gate's derivation. | The reader exists so appenders see what the gate sees; a parallel derivation would drift. | Independent summary logic in the list path. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Parallel chain-derivation logic drifts from the gate. | Reuse the gate's derivation function; parity test on a multi-cycle fixture. |
| Unbounded output on large ledgers. | Cap with explicit truncation marker; compact default rows, verbose opt-in. |
| List event accidentally acquires write-path requirements (actor/lane validation). | Read path branches before validation; absent/empty-ledger test plus read-only proof test. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
