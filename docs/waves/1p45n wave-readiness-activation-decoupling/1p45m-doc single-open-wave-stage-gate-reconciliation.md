# Reframe Single-Active As Single-OPEN; Split READY From OPEN Across Seeds, Stage Gate, And Docs

Change ID: `1p45m-doc single-open-wave-stage-gate-reconciliation`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-06-08
Wave: 1p45n wave-readiness-activation-decoupling

## Rationale

Once `1p45l` decouples readiness from activation (`wave_prepare(mode='ready')` + single-OPEN guard at the activation step), the documentation and seeds that **conflate "single-active" with readiness** — and that **bundle activation into Prepare** — become wrong. The lifecycle sweep (2026-06-08) found the conflation written across many surfaces, each of which tells an agent it must pause the open wave to prepare another:

- `prepare-wave` step 8 makes `Status: active` the terminal action of readiness; the "Single-Active-Wave Rule" section instructs pause-then-prepare.
- `pause-wave` frames pause as the thing that "frees the slot so another wave can be **prepared**."
- the `AGENTS.md` Stage Gate couples *is-ready* with *is-active*.
- `README` bundles readiness with the active flip.
- `seed 020` / `seed 110` carry soft "only one wave should normally be active" hedges that conflict with the hard guard, and `seed 110`'s status model (`planned/active/blocked/completed/superseded`) omits the statuses the code actually uses (`implementing`, `paused`) and has no notion of "readied".
- `project-overview` / `README` are silent on multi-wave concurrency.

This change reconciles all of them to one vocabulary: **OPEN** = `active`/`implementing` (the single-at-a-time states); **readied** = `planned` + recorded readiness evidence (council verdict + lane signoffs); **single-OPEN invariant** enforced only at the open/activation step. It weaves the ready-vs-open distinction across the related seeds with discoverability pointers rather than leaving it stated in one place.

## Requirements

1. The prepare-wave prompt/seed reframes readiness as terminal-at-readied: record the readiness verdict and leave the wave **readied (`planned`)**; activation (open) is a separate step. The "Single-Active-Wave Rule" becomes the "Single-OPEN-Wave Rule" — at most one OPEN wave; others may be **readied without pausing**; the guard applies only at open.
2. `pause-wave` is reframed: pause frees the slot so another wave can be **OPENED**, not prepared/readied (readying needs no pause).
3. The `AGENTS.md` Stage Gate splits READY from OPEN — the sequence is plan → admit → **ready** → **open (implement)**; readiness of other waves does not displace the currently OPEN wave.
4. `README` and `docs/references/project-overview.md` state explicitly that any number of waves may be planned and **readied in parallel** while exactly one is OPEN.
5. `seed 020` and `seed 110` soft hedges ("only one wave should normally be active …") are reconciled with the hard single-OPEN rule — stated once at open time, with the hedges marked non-normative; `seed 110`'s wave-status model is reconciled with `constants.py` (document the statuses the code actually uses, define "readied" as `planned` + evidence, and reference the real transitions).
6. All touched surfaces use consistent terminology — **OPEN** (active/implementing), **readied** (planned + evidence), **single-OPEN** — and none contradicts the `1p45l` tool contract.

## Scope

**Problem statement:** Seeds, the stage gate, and operator docs describe a single-**active** rule that conflates readiness with activation and tells agents to pause to prepare — wrong once `1p45l` lands.

**In scope:**

- `prepare-wave` prompt + its owning seed: reframe step 8 and the Single-Active-Wave Rule → Single-OPEN-Wave Rule + readied terminal state.
- `pause-wave` prompt: reframe the "frees the slot" wording.
- `AGENTS.md`: Stage Gate split of READY from OPEN.
- `README`: readiness-vs-open wording + multi-wave concurrency statement.
- `docs/references/project-overview.md`: multi-wave concurrency statement.
- `seed 020`, `seed 110`: reconcile the hard rule and the status model (and align `seed 110` with `constants.py`).
- Weave discoverability pointers (ready-vs-open) into the related lifecycle seeds (`170-plan-feature`, `180-implement-feature`, `create-wave`, `add-change-to-wave`).

**Out of scope:**

- The behavior change itself (`1p45l`) — this change is documentation/seeds only.
- Introducing a new durable `ready` status, or any code/state-machine change.
- Dashboard surfacing of a "readied" state.

## Acceptance Criteria

- [x] AC-1: The prepare-wave prompt/seed describes Prepare as ending in a **readied (`planned`)** wave, and the rule section reads as single-OPEN (others readied without pausing; guard at open).
- [x] AC-2: `pause-wave` states pause frees the slot to **OPEN** another wave (not to prepare/ready one).
- [x] AC-3: The `AGENTS.md` Stage Gate sequence splits READY from OPEN and states that readiness of other waves does not displace the OPEN wave.
- [x] AC-4: `README` and `docs/references/project-overview.md` each state that many waves may be planned/readied in parallel while one is OPEN.
- [x] AC-5: `seed 020`/`seed 110` hedges are reconciled with the hard single-OPEN rule, and `seed 110`'s status model matches `constants.py` (statuses documented; "readied" defined as planned + evidence).
- [x] AC-6: Terminology (OPEN / readied / single-OPEN) is consistent across all touched surfaces and consistent with the `1p45l` tool contract; docs-lint passes and `python3 .wavefoundry/framework/scripts/run_tests.py` is green (no doc-string-assertion tests regress).

## Tasks

- [x] Reframe the prepare-wave prompt + owning seed (step 8 + Single-OPEN-Wave Rule + readied terminal).
- [x] Reframe `pause-wave` ("frees the slot to OPEN").
- [x] Update the `AGENTS.md` Stage Gate (split READY from OPEN).
- [x] Update `README` + `docs/references/project-overview.md` (multi-wave parallel readiness, one OPEN).
- [x] Reconcile `seed 020`/`seed 110` hedges + the `seed 110`↔`constants.py` status model.
- [x] Weave ready-vs-open discoverability pointers into `170`/`180`/`create-wave`/`add-change-to-wave`.
- [x] Run docs-lint and `python3 .wavefoundry/framework/scripts/run_tests.py` (some doc-string-assertion tests reference seed/prompt text — update them to the new wording if they fail).

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| seed-and-prompt-reframe | technical-writer | — | prepare-wave / pause-wave / 020 / 110 + woven pointers. |
| stage-gate-and-readmes | technical-writer | seed-and-prompt-reframe | AGENTS Stage Gate, README, project-overview. |
| lint-and-test-reconcile | docs-contract-reviewer | stage-gate-and-readmes | docs-lint; fix any seed/prompt-text assertion tests. |


## Serialization Points

- Depends on `1p45l` for final vocabulary (single-OPEN, readied) and behavior — this change must land after (or be co-reviewed with) `1p45l` so docs match code.
- `docs/specs/mcp-tool-surface.md` is owned by `1p45l`; this change does not edit it — coordinate terminology only.
- Seed edits require the `seed_edit_allowed` gate; framework-maintenance doc edits (`docs/prompts/`, `AGENTS.md`) require `framework_edit_allowed`. Single write owner per surface.

## Affected Architecture Docs

N/A — documentation, seed, and stage-gate wording reconciliation. It clarifies the wave-lifecycle narrative but introduces no module boundary, data-flow, or verification-surface change; the lifecycle state model's authoritative definition (`seed 110`/`constants.py`) is reconciled here at the doc level, with the behavioral contract owned by `1p45l`.

## AC Priority

_Confirmed at Prepare wave 1p45n (2026-06-08) — classifications interrogated by the readiness council._


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The prepare-wave surface is where the conflation is most load-bearing for agents. |
| AC-2 | required   | pause-wave's "prepare" wording directly causes the unnecessary-pause behavior. |
| AC-3 | required   | The stage gate governs first-edit gating; it must not couple ready with open. |
| AC-4 | important  | Makes the supported concurrency explicit for operators. |
| AC-5 | important  | Removes the soft/hard contradiction and the status-model drift. |
| AC-6 | required   | Consistency + green suite/lint; no contradiction with the `1p45l` contract. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Reframed single-active → single-OPEN and split READY from OPEN across the prepare/pause/implement prompts, the `AGENTS.md` stage gate, `README`, `project-overview`, the create-wave prompt, and seeds `020`/`110` (status model reconciled with the code — adds `implementing`/`paused`, defines `readied` = `planned` + evidence). | docs-lint clean; `run_tests.py` green (2789) — no doc-string-assertion regressions; no stale single-active language remains in the checked surfaces. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Carry the doc/stage-gate/seed reframing as a **separate change** from the behavior change (`1p45l`). | Different review lanes (docs-contract / technical-writer vs code), and the sweep depends on `1p45l`'s final vocabulary; splitting keeps each change coherently reviewable and lets the contract settle first. | Fold the doc sweep into `1p45l` (one change) — rejected: mixes a code-contract change with a broad multi-file narrative sweep, muddying review and the AC set. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Doc-string-assertion tests reference current seed/prompt wording (e.g. dashboard/server tests assert prompt text). | AC-6 task explicitly updates any such tests to the new wording; run the full suite. |
| Terminology drifts from the `1p45l` contract. | Depends-on `1p45l`; reuse its exact terms (OPEN, readied, single-OPEN); co-review. |
| Seed edits touch protected surfaces. | `seed_edit_allowed` / `framework_edit_allowed` gates; single write owner per surface; close gates immediately after. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
