# Memory Propose Draws Targets From the Verification Command

Change ID: `1t728-bug memory-propose-target-misattribution`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

At wave 1t3ek close, `memory_propose` drafted a factually wrong `fragile_file`
candidate: "Fragile: run_tests.py, required 3 separate repairs" — when all
three cited findings repaired the credit instrumentation in `server_impl.py`.
The drafter's target extraction (`draft_candidates`, memory_supply.py:384-388)
feeds `command_or_fixture` into `_code_targets`, and every repair record's
`command_or_fixture` named the verification command (`python3 run_tests.py`),
so the verification harness was mistaken for the repaired file. The candidate
had to be corrected by hand via `memory_validate(verdict='rewrite')`.
Auto-drafted wrong memories are worse than no memories: they surface as
advisories on the wrong files.

## Requirements

1. Target extraction for repaired-finding drafts (`failed_attempt` /
   `fragile_file`) must not treat `command_or_fixture` as a target source: it
   describes HOW the claim was verified, not WHAT was repaired. Targets come
   from `public_path` and `artifact_or_test_id` (the repaired-surface fields).
2. The regression fixture must be generated from the canonical producer shape:
   build the evidence records through `wf_review_evidence`-shaped data mirroring
   the real 1t3ek cycle-4 records (repair fields naming `server_impl.py`
   surfaces, `command_or_fixture` naming the suite command), and assert the
   draft targets the repaired file, never the verification command.
3. Existing drafts and dispositions are untouched (idempotency across
   dispositions is preserved); no store or record-shape change.

## Scope

**Problem statement:** `_text_refs(artifact_or_test_id, public_path,
command_or_fixture)` at memory_supply.py:384-388 pollutes target extraction
with verification-command file tokens.

**In scope:**

- The target-source field set in `draft_candidates`
- Canonical-shape regression test for the 1t3ek misattribution

**Out of scope:**

- Retroactive correction of the already-rewritten 1t3ek record (done by hand)
- Cross-wave fragile-file detection (recorded as deliberately not attempted)

## Acceptance Criteria

- [x] AC-1: A repaired-finding evidence record whose `command_or_fixture` names
      a runnable file but whose `public_path`/`artifact_or_test_id` name the
      repaired surface drafts a candidate targeting the repaired surface only,
      verified by a canonical-shape regression test.
- [x] AC-2: A record whose only file token appears in `command_or_fixture`
      drafts nothing (no concrete anchor) rather than a wrong-target record.
- [x] AC-3: Existing drafting behavior for Decision Log candidates and
      idempotent re-runs is unchanged (existing tests stay green).
- [x] AC-4: Full framework test suite passes (6,036 tests across 56 files, OK, 2026-07-20).

## Tasks

- [x] Remove `command_or_fixture` from the repaired-finding target sources
- [x] Canonical-shape regression tests (AC-1, AC-2)
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| drafter    | Engineering | —          | memory_supply.py only |


## Serialization Points

- None; single-module change.

## Affected Architecture Docs

`N/A` — single-module fix in the memory-supply drafter; no boundary or flow
change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The observed live defect |
| AC-2 | required | The no-anchor fallback must stay honest |
| AC-3 | required | Drafting is close-gated; regressions block closes |
| AC-4 | required | Suite-green delivery gate |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Targets come from `public_path` + `artifact_or_test_id` only; `command_or_fixture` dropped from target extraction | Its file tokens name the verification harness (`_PATH_TOKEN_RE` extracted `run_tests.py` from the suite command on 1t3ek), not the repaired surface | Rank fields by priority keeping command as last resort (rejected: a wrong advisory is worse than none — AC-2 makes the no-anchor case draft nothing) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Dropping `command_or_fixture` loses a legitimate target some record only names there | AC-2 makes that case draft nothing — an honest gap beats a wrong advisory; the field remains available to future explicit-anchor work |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
