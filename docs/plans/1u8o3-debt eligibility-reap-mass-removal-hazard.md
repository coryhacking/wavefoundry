# Shipped Eligibility Reap Lacks the Mass-Removal Protections Its Sibling Now Has

Change ID: `1u8o3-debt eligibility-reap-mass-removal-hazard`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-01
Wave: TBD

## Rationale

Disclosed during wave 1u8o2's prepare and delivery reviews (architecture and code lanes,
2026-08-01) and deliberately kept out of that wave's scope: the SHIPPED Lance eligibility reap
(`_reap_stranded_lance_rows` and the walk-derived `docs_eligible_rel` / `code_eligible_rel`
comprehensions, at `indexer.py` ~:4167-4192 on the post-1u8o2 tree; symbols are the durable
anchors) carries the exact hazard 1u8o2's new orphan-store reconciliation was
required to design out. Eligibility sets are comprehensions over the walk, and `walk_repo`
silently omits unreadable directories, so a transiently unreadable subtree (permissions incident,
unmounted volume, agent sandbox restriction) reads as ineligible: its Lance rows are reaped, its
layer hashes dropped (`_cleanup_layer_state_for_reaped`, `indexer.py:2383`), and recovery forces a
full re-embed of the subtree.

The 1u8o2 reconciliation demonstrates the shape of the protections: per-path absence
classification at a discrete stat seam (ENOENT removes; other OSError preserves) and a
mass-removal circuit breaker (would-remove over half the store AND at least a floor count defers
loudly). The shipped reap has neither. This record exists so the disclosed-unfixed hazard survives
wave 1u8o2's close instead of evaporating with the session handoff.

## Requirements

1. The eligibility reap distinguishes walk-absent-because-unreadable from genuinely ineligible:
   an unreadable subtree preserves its rows and layer hashes (conservative on IO errors),
   mirroring the 1u8o2 absence-classification semantics at a testable seam.
2. A mass-removal circuit breaker guards the reap: a would-reap count exceeding a recorded
   threshold defers loudly (message naming the situation and remedy) instead of reaping, with the
   same no-silent-data-effect posture as the 1u8o2 breaker.
3. Regression tests drive both protections with error injection at the seam (never chmod) and a
   breaker-threshold fixture; the existing reap behavior for genuine deletions and scope
   departures is pinned unchanged.
4. The walk's silent omission of unreadable directories is either surfaced to the reap (the
   classification input) or documented as the boundary the classification compensates for; record
   the choice.

## Scope

**Problem statement:** a transient IO failure can silently reap and force re-embed of an entire
subtree because the shipped reap trusts walk-derived eligibility without absence classification or
a breaker.

**In scope:** `_reap_stranded_lance_rows` and its eligibility inputs in `indexer.py`; the
walk-omission surface; regression tests.

**Out of scope:** the 1u8o2 orphan-store reconciliation (already protected); ignore-rule
semantics; the reap's genuine-deletion behavior.

## Acceptance Criteria

- [ ] AC-1: An injected unreadable subtree preserves its Lance rows and layer hashes through a
  build; recovery after the subtree returns requires no re-embed.
- [ ] AC-2: A would-reap count over the recorded threshold defers loudly and the build succeeds;
  below threshold the reap proceeds as today.
- [ ] AC-3: Genuine-deletion and scope-departure reaping are pinned unchanged; full suite passes.

## Tasks

- [ ] Red-first: inject an unreadable subtree and demonstrate the current reap-and-rehash loss
- [ ] Implement the classification and breaker at the reap, reusing the 1u8o2 seams where sensible
- [ ] Requirement 4 decision recorded; tests; full suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          |       |


## Serialization Points

- `indexer.py` (shared with any concurrent index work; lands after wave 1u8o2)

## Affected Architecture Docs

Candidates at Prepare: `docs/architecture/data-and-control-flow.md` item 15 vicinity (the reap's
protections would then match the reconciliation's); CHANGELOG `### Fixed` at the shipping release.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | TBD      |           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-01 | Filed as the close-surviving record of the hazard disclosed and deliberately descoped during wave 1u8o2 (architecture lane prepare P3 and delivery P3-4; code lane concurrence). | Wave 1u8o2 lane reports 2026-08-01; indexer.py `docs_eligible_rel`/`code_eligible_rel` (~:4167-4192 post-1u8o2), `_cleanup_layer_state_for_reaped` :2383 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Making the reap conservative strands genuinely deleted rows | AC-3 pins the genuine-deletion path; the 1u8o2 orphan reconciliation is the backstop for anything the conservative reap misses |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
