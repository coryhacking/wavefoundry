# Paired-Evaluation Scaffold: Making the Counterfactual Measurable

Change ID: `1t72a-enh paired-evaluation-scaffold`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

The measured Context Efficiency ledger is now closed and conservative, and
every counterfactual claim ("what would the agent have spent without the
tool") is deliberately gated behind paired evaluations. The gate exists —
`wf_context_efficiency_eval` registers applicability, attaches artifacts, and
`score_context_efficiency_pairs.py` enforces a strict schema (two arms per
pair, provider-reported usage, blind quality scores, at least 5 qualifying
pairs) with the residual flowing into wave snapshots — but nothing helps
anyone PRODUCE a valid pair artifact. The counterfactual half of the accounting
is therefore structurally unreachable in practice: an operator must
reverse-engineer the scorer's schema from its validator. This change makes the
existing gate usable without weakening it.

## Requirements

1. **Scaffold mode**: `wf_context_efficiency_eval` gains `mode='scaffold'`,
   which writes a pair-artifact skeleton JSON for a registered (wave, phase)
   scope: applicability prefilled from the registered scope, `pairs` populated
   with `MIN_QUALIFYING_PAIRS` canonical empty pair entries (both arms carrying
   every required field with placeholder values that FAIL the scorer until
   genuinely filled — placeholders must never accidentally qualify).
2. **Scaffold validates against the real scorer**: the scaffold's shape is
   generated from the scorer's own canonical field sets (QUALITY_KEYS,
   APPLICABILITY_KEYS, the arm field set) — no hand-maintained parallel schema
   (the templates-generate-valid-docs principle applied to JSON, and the
   fixtures-from-canonical-producers principle applied to the scaffold).
3. **Protocol guide**: a reference doc describes the paired-evaluation
   protocol end to end: matched task specs, the two arms (with-tooling vs
   baseline), provider-reported usage capture, blind quality scoring, the
   5-pair minimum and quality gate, and the register → run → fill → attach
   flow. The doc states plainly that the residual is the ONLY sanctioned
   channel for counterfactual savings.
4. **Discoverability**: the reference doc is linked from
   `docs/references/context-efficiency.md` where the paired-evaluation gate is
   already named, and the eval tool's error path points at the scaffold mode.
5. No change to scoring, gating, thresholds, or the attach/revoke semantics:
   this change makes the gate reachable, not weaker.

## Scope

**Problem statement:** the counterfactual measurement gate exists but has no
production path; nothing generates a valid pair artifact or documents the
protocol.

**In scope:**

- `mode='scaffold'` in the eval tool path
- The protocol reference doc + cross-links
- Tests: scaffold shape derives from scorer constants; placeholder scaffold is
  rejected by the scorer; a filled scaffold attaches cleanly

**Out of scope:**

- Automated counterfactual execution (running baseline-arm agents is
  operator/harness work, not framework code)
- Any change to the scorer's quality gate or the 5-pair minimum
- Cross-wave evaluation reuse policy

## Acceptance Criteria

- [x] AC-1: `mode='scaffold'` writes a skeleton whose applicability echoes the
      registered scope and whose arm/quality/applicability field sets are
      derived from the scorer's canonical constants, verified by test.
- [x] AC-2: The unfilled scaffold is REJECTED by `score_pairs` (placeholders
      never qualify), and the same scaffold with genuinely filled arms scores
      and attaches through `mode='attach'`, verified end-to-end by test.
- [x] AC-3: The protocol reference doc exists, is docs-lint clean, and is
      linked from the context-efficiency reference; the eval tool's
      error/usage text names the scaffold mode.
- [x] AC-4: Full framework test suite passes (6,036 tests across 56 files, OK, 2026-07-20).

## Tasks

- [x] Implement `mode='scaffold'` deriving shape from scorer constants
- [x] Write the paired-evaluation protocol reference doc + cross-links
- [x] End-to-end tests: scaffold rejected unfilled, attaches when filled
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| scaffold   | Engineering | —          | Eval tool path + scorer constants |
| protocol   | Engineering | scaffold   | Reference doc mirrors the shipped shape |


## Serialization Points

- `server_impl.py` is shared with 1t729; sequence their edits.

## Affected Architecture Docs

`docs/references/context-efficiency.md` (paired-evaluation section gains the
protocol link and scaffold pointer). New reference doc under
`docs/references/`. `N/A` otherwise.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Scaffold must mirror the real scorer, not a parallel schema |
| AC-2 | required | The gate must stay exactly as strict as before |
| AC-3 | required | Unreachable protocol was the defect; discoverability is the fix |
| AC-4 | required | Suite-green delivery gate |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Arm/pair field sets lifted to scorer module constants (`ARM_KEYS`, `PAIR_KEYS`) used by BOTH the validator and the scaffold generator | Single source of truth; a test asserts set equality so scaffold/validator drift is structurally impossible | Scaffold hardcodes the shape (rejected: the parallel-schema drift the change exists to prevent) |
| 2026-07-20 | Placeholders are deliberately invalid (empty ids, negative token counts, incomplete arms) so score_pairs REJECTS an unfilled scaffold | The gate must stay exactly as strict; a scaffold must never accidentally qualify | Valid-looking zeros (rejected: a lazily attached scaffold would score) |
| 2026-07-20 | `mode='scaffold'` refuses to overwrite an existing report_path | A filled artifact must never be clobbered by a scaffold rerun | Overwrite-with-backup (rejected: silent data motion) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Scaffold placeholders accidentally qualify as a scored pair | AC-2 asserts the unfilled scaffold is rejected by the real scorer |
| Parallel-schema drift between scaffold and scorer | Scaffold generation imports the scorer's canonical constants; a test asserts set equality |
| Protocol doc overpromises automation | Doc explicitly scopes baseline-arm execution as operator/harness work |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
