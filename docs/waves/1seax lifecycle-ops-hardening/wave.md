# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-12

wave-id: `1seax lifecycle-ops-hardening`
Title: Lifecycle Ops Hardening

## Objective

Land the right-sized remainder of the 2026-07-12 external code review: (1) lifecycle-mutation concurrency and interruption safety — an advisory per-root mutation lock, a write-ordering audit guaranteeing forward-recoverability, and idempotent-retry fixtures — deliberately NOT the review's proposed transaction-journal/rollback layer, which was assessed as disproportionate for git-versioned markdown with zero field incidents; (2) selective subprocess bounds (timeouts + bounded capture) for the short MCP-reachable ops (gardener, surface render), with upgrade/setup explicitly exempt as long-running-by-design; (3) the materially stale operational contracts (RELIABILITY.md, performance-budget.md) rewritten from measured evidence, plus a declarative docs-vs-code-constants lint check so documented facts fail the docs gate when they drift instead of waiting for the next external review to notice.

## Changes

Change ID: `1seat-debt lifecycle-mutation-lock-and-subprocess-bounds`
Change Status: `planned`

Change ID: `1seau-doc ops-docs-refresh-and-constants-lint`
Change Status: `planned`

## Wave Summary

P2-priority hardening pair from the external review, both right-sized during validation: lifecycle mutation lock + forward-recoverability + selective subprocess bounds (transaction-journal machinery explicitly rejected), and evidence-based ops-docs refresh with a drift-preventing constants lint.

## Journal Watchpoints

- Watchpoint (right-sizing holds): the rejected alternatives (transaction journal, blanket subprocess deadlines, correlation IDs) are recorded with rationale in the change docs — reviewers should challenge the fixes' sufficiency, not silently re-expand toward the rejected machinery.
- Watchpoint (exemption pins): upgrade/setup/index-build spawns must be PINNED as timeout-exempt — a deadline there converts slow-network success into failure.
- Watchpoint (happy-path invariance): the mutation lock must be invisible uncontended; existing lifecycle tests pass unmodified except for additive envelope fields.
- Watchpoint (measured, not aspirational): the performance-budget rewrite cites the recorded measurements (1sc7c hook costs, heal timing, FTS rebuild duration) — no unquantified claims.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-12: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, architecture-reviewer; rotating-seat: red-team emphasis; strongest-challenge: the right-sizing itself — is an advisory lock plus retry fixtures ENOUGH, or does rejecting the review's transaction layer under-protect as multi-agent use grows? Resolved on evidence: the failure base rate is zero across the framework's entire wave history, every mutation's artifacts are git-versioned human-readable markdown (git IS the recovery journal), forward-recoverability converts any interruption into \"re-run the same call\", and the lock closes the one genuinely growing risk (concurrent sessions interleaving writes) using the OS-lock pattern the index-build lock has proven in the field — the journal/rollback machinery would add failure modes to defend against failures git already makes visible; strongest-alternative: the review's full transaction layer — kept ON RECORD in the change doc's Decision Log as the escalation path if multi-agent incidents ever materialize)
- Council seat notes: reality-checker — orderings verified against `2952df8f` (`_move_change_doc` ~6048 before `wave_md.write_text` ~6067; close's wave.md-then-handoff two-step); the zero-incident base rate is drawn from the full `docs/waves/` history; the stale-docs claims verified by direct read (performance-budget's \"None currently; all operations are local file I/O with small data volumes\" against a system with GPU embedding sessions and 100MB indexes); the measured inputs for the rewrite exist (1sc7c hook costs, 38s heal, 3.4s FTS rebuild). red-team — pressed lock-leak-on-crash (kernel releases OS locks on exit — the proven index-lock pattern, not a PID file); pressed the timeout exemption inversion (an exempt op that hangs forever): upgrade/setup already write persistent progress logs and the operator-facing status tools report liveness — observability, not deadlines, is the correct control there; pressed constants-lint brittleness (a renamed constant breaking lint): the check fails loudly naming the missing constant — self-announcing drift is the feature, not a bug. qa-reviewer — interruption fixtures are enumerated per mutation (admission, removal, close) at the specific inter-step seams, plus the contended-lock fixture and the drift-seeded lint fixture; happy-path invariance is an explicit AC. architecture-reviewer — the mutation lock joins the documented locking inventory (cross-cutting-concerns) beside the index-build and table locks with distinct scope; the constants-lint reuses the declarative check pattern (`check_deprecated_role_references` shape) rather than inventing a framework; the docs rewrite is evidence-cited by requirement. seat_agreement: unanimous.
- AC priority: confirmed at prepare as proposed (`1seat` AC-3 important, all else required). Product-owner acknowledgment: operator-directed 2026-07-12 ("build these waves now"); opportunistic scheduling.

## Review Evidence

- wave-council-readiness: approved 2026-07-12 — prepare council synthesis verdict READY: the deliberate severity downgrade from the review's P0 is evidence-based and recorded with the escalation path preserved; fixtures target the known seams instead of a fault-injection framework; the docs half is measurement-cited with a drift-preventing lint. Seats unanimous; full synthesis in Review Checkpoints.
- operator-signoff: approved when operator confirms closure

## Dependencies

- No external wave dependencies. Opportunistic scheduling after `1seav`/`1seaw`; the docs change can land any time.
