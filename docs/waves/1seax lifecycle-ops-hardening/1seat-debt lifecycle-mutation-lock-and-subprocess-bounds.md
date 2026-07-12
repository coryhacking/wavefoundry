# Lifecycle Mutation Lock, Idempotent-Retry Guarantees, and Selective Subprocess Bounds

Change ID: `1seat-debt lifecycle-mutation-lock-and-subprocess-bounds`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-12
Wave: `1seax lifecycle-ops-hardening`

## Rationale

External code review (2026-07-12), validated against `2952df8f` — with the severity DELIBERATELY downgraded from the review's P0. The mechanics are real: `wave_add_change` moves the change doc, then writes `wave.md` (~6048/6067); removal reverses; `wave_close` writes `wave.md` then the handoff separately. A crash or concurrent call between steps leaves a half-mutation. But the blast radius is git-versioned, human-readable markdown: failures are visible in `git status`, most operations self-heal on retry (re-running admission finds the doc at target and completes the record), and there are zero field incidents across the framework's entire wave history. The review's proposed transaction layer (recovery journal, rollback, fault injection at every filesystem boundary) is disproportionate — rejected per "simplest solution first."

The right-sized version: (a) an advisory lifecycle-mutation lock so two agents/sessions can't interleave lifecycle writes on the same repo; (b) an ordering audit ensuring every multi-file mutation writes the REFERENCING record last (so a partial state is always re-runnable forward); (c) tests proving idempotent retry for each mutation. Plus the selective subset of the review's subprocess finding: timeouts + bounded capture for SHORT MCP-reachable subprocess ops (gardener, surface render) — explicitly NOT for upgrade/setup, which are long-running by design (in-line model downloads).

## Requirements

1. **Advisory lifecycle-mutation lock, scoped by CENSUS not by hand-list (plan-review revision):** one per-root lock (index-build-lock OS pattern). The covered set is derived from a complete census of MCP tools carrying mutation behavior — the review caught that a hand-written list omitted at least `wave_set_handoff` (races pause/close handoff writes) and `wave_gate_open`/`wave_gate_close` (race close's forced gate mutation). The census enumerates EVERY writer and marks each: covered-by-lifecycle-lock / protected-by-another-lock (index-build, table locks) / safely-independent-with-rationale. The census table is required AC-1 evidence in this doc. A held lock returns a structured busy response, never corrupts.
2. **Ordering audit + forward-recoverability:** each multi-file lifecycle mutation documented and (where needed) reordered so the referencing record is written last; for each, a retry after any single-step interruption completes the operation (no manual repair).
3. **Idempotent-retry tests:** per mutation, simulate the interruption between steps (move done, record not written; record written, handoff not) and assert a re-run converges. No fault-injection framework — targeted fixtures at the known seams.
4. **Close-gate signoff-token hardening (plan-review addition):** `_lane_has_signoff_in_evidence` accepts any lane line containing an approval token, so unbracketed conditional phrasing ("approved when operator confirms closure") reads as real approval — the placeholder convention is the only guard. Harden the parser to reject conditional/future-tense approval phrasing (or require an explicit affirmative form), with fixtures for the phrasings this session actually produced.
5. **Prepare seat-alignment validation (council amendment):** `wave_prepare`'s verdict validation compares the recorded council seats against the generated brief's required seats (fixed + rotating) instead of validating structure only; mismatch is a named diagnostic.
6. **Selective subprocess bounds:** timeouts for the gardener and surface-render subprocess calls (short ops; generous defaults, config-tunable like the 1p9bg docs-lint bound) + bounded captured output with a truncation marker. Upgrade/setup/index-build spawns explicitly EXEMPT (long-running by design; already logged to persistent files).
7. **No behavior change on the happy path:** all lifecycle tool responses keep their shapes; the lock is invisible when uncontended.

## Scope

**Problem statement:** lifecycle mutations lack a concurrency guard and interruption-recovery guarantees; two short subprocess paths lack bounds.

**In scope:** `server_impl.py` lifecycle tools + a small lock helper; the two subprocess call sites; fixtures.
**Out of scope:** transaction journal/rollback machinery (rejected — see Rationale); upgrade/setup deadlines; `meta.json`/index writes (already atomic-swap + locked).

## Acceptance Criteria

- [ ] AC-1: Two concurrent lifecycle mutations on the same root serialize via the lock; the loser gets a structured busy response (fixture with a held lock). Evidence includes the COMPLETE writer census table (every mutating MCP tool dispositioned: lifecycle-lock / other-lock / independent-with-rationale).
- [ ] AC-5: Unbracketed conditional signoff phrasing no longer passes the close gate's lane check (fixture: this session's exact phrasing), and bracketed placeholders still read as missing.
- [ ] AC-6: `wave_prepare` flags a recorded council whose seats do not include the brief's required rotating seat (fixture), while matching councils pass unchanged.
- [ ] AC-2: For admission, removal, and close: an interruption between file steps leaves a state from which re-running the SAME tool call converges to the correct end state — fixture-pinned per mutation.
- [ ] AC-3: Gardener and surface-render subprocess calls carry timeouts and bounded output (truncation flagged); upgrade/setup spawns are pinned as exempt.
- [ ] AC-4: Full suite bytecode-free + docs validation; uncontended-path behavior unchanged (existing lifecycle tests pass unmodified except where they assert new envelope fields).

## Tasks

- [ ] Lock helper + wiring across the mutating lifecycle tools.
- [ ] Ordering audit table in this doc; reorder where a mutation is not forward-recoverable.
- [ ] Interruption/retry fixtures (admission, removal, close); concurrency fixture.
- [ ] Subprocess timeouts + bounded capture at the two sites; exemption pins.
- [ ] Suite + validate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| lock+audit | implementer | — | The concurrency guard |
| retry-fixtures | qa-reviewer | lock+audit | Interruption seams |
| subprocess-bounds | implementer | — | Two sites, selective |


## Serialization Points

- None external; single-wave internal ordering only (audit before reorder).

## Affected Architecture Docs

- `docs/architecture/cross-cutting-concerns.md` (locking inventory) — one entry. N/A otherwise (no boundary change).

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The multi-agent concurrency gap is the real risk. |
| AC-2 | required | Forward-recoverability is the right-sized transactionality. |
| AC-3 | important | Bounded ops; low incidence, low cost. |
| AC-4 | required | Standard gate + no-regression. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-12 | Plan-review revision (external, validated) + council amendment: hand-written lock scope replaced by a required writer CENSUS (omissions caught: `wave_set_handoff` ~6492, gate tools ~6385); two validator-hardening items adopted into scope — close-gate signoff-token parsing (verified: only `<...>` placeholders are skipped at ~5151, so this session's unbracketed phrasing pre-approved closure on three waves before repair) and prepare seat-alignment validation (the structural parser accepted councils missing the brief's rotating seat). | Plan review; parser source reads; the three repaired wave records. |
| 2026-07-12 | Drafted from the external code review (P0-2 + P1 subprocess), validated against `2952df8f` and DOWNGRADED: mechanics confirmed (move-then-write ~6048/6067; close's two-step write), but git-backed markdown + visible failures + retry-mostly-self-heals + zero field incidents make the proposed journal/rollback layer disproportionate. Right-sized to lock + ordering audit + retry guarantees + selective bounds. | Review report; source reads; wave-history incident base rate (none). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-12 | Advisory lock + forward-recoverable ordering + retry tests — NOT a transaction journal with rollback. | Matches actual risk (concurrent agents; interrupted retries) at a fraction of the machinery; git is the recovery journal a docs repo already has. | **Full transaction layer (review's proposal):** disproportionate; adds its own failure modes. **Do nothing:** the concurrency gap is real as multi-agent use grows. |
| 2026-07-12 | Upgrade/setup/index spawns exempt from deadlines. | In-line model downloads and full rebuilds are legitimately long; a deadline converts slow-network success into failure. Persistent logs already cover observability. | **Blanket deadlines (review's proposal):** breaks legitimate operations. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Lock leaks on crash | OS-lock pattern (released by the kernel on exit), mirroring the proven index-build lock. |
| Reordering changes observable intermediate states some test pins | Audit first; touch only non-forward-recoverable orderings. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
