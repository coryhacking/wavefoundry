# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-08

wave-id: `1p45n wave-readiness-activation-decoupling`
Title: Wave Readiness Activation Decoupling

## Objective

Decouple wave **readiness** from **activation** so any number of waves can be planned and fully prepared (readied) while exactly one wave is OPEN (being implemented). Today `wave_prepare` fuses readiness with the `planned→active` flip and the single-active guard fires at readiness time — blocking even a second wave's dry-run while one is open. When this wave closes, readiness runs freely in parallel and the single-OPEN invariant is enforced only at the activation step.

## Changes

Change ID: `1p45l-enh prepare-ready-mode-decouples-readiness-from-activation`
Change Status: `implemented`

Change ID: `1p45m-doc single-open-wave-stage-gate-reconciliation`
Change Status: `implemented`

Change ID: `1p45s-bug wave-review-severity-substring-false-positive`
Change Status: `implemented`

Completed At: 2026-06-08

## Wave Summary

Wave `1p45n` (Wave Readiness Activation Decoupling) delivered 3 changes: Decouple Wave Readiness From Activation — `wave_prepare(mode='ready')` + Single-OPEN Guard at the Activation Step, Reframe Single-Active As Single-OPEN; Split READY From OPEN Across Seeds, Stage Gate, And Docs, and `wave_review` Severity Detection Substring-Matches Inside Larger Words (False High-Severity). Notable adjustments during implementation: Decouple Wave Readiness From Activation — `wave_prepare(mode='ready')` + Single-OPEN Guard at the Activation Step: Added `wave_prepare(mode='ready')` (readiness without activation/guard) and relocated the single-OPEN guard to all three activation paths — `wave_prepare(create)`, `wave_implement` (now accepts a readied `planned` wave), and `wave_reopen` (previously unguarded). Updated the tool docstring + `mcp-tool-surface.md` + prepare/implement prompts.

**Changes delivered:**

- **Decouple Wave Readiness From Activation — `wave_prepare(mode='ready')` + Single-OPEN Guard at the Activation Step** (`1p45l-enh prepare-ready-mode-decouples-readiness-from-activation`) — 9 ACs completed. Key decision: **Selected — Option C:** add `wave_prepare(mode='ready')` (full readiness, persist evidence, no guard, no activation) and relocate the single-OPEN guard to the activation step (`wave_implement`), with no new wave status.
- **Reframe Single-Active As Single-OPEN; Split READY From OPEN Across Seeds, Stage Gate, And Docs** (`1p45m-doc single-open-wave-stage-gate-reconciliation`) — 6 ACs completed. Key decision: Carry the doc/stage-gate/seed reframing as a **separate change** from the behavior change (`1p45l`).
- **`wave_review` Severity Detection Substring-Matches Inside Larger Words (False High-Severity)** (`1p45s-bug wave-review-severity-substring-false-positive`) — 4 ACs completed. Key decision: Fix via whole-word/token matching of severity levels rather than introducing a structured `severity:` evidence field.
## Journal Watchpoints

- **Implement order:** `1p45m` (doc reframing) depends on `1p45l` (behavior + vocabulary) — land/settle `1p45l` first so the docs match the code and reuse its exact terms (OPEN, readied, single-OPEN).
- **Single guard chokepoint:** after `1p45l`, the single-OPEN guard (`_find_other_active_wave`, which counts `active`+`implementing`) must have exactly one enforcement point — the activation step (`wave_implement`, and within `wave_prepare(mode='create')` because it activates). Do not leave it firing at readiness or dry-run.
- **`1p45s` serialization:** `1p45s` (severity-matcher bug) edits `_max_severity_from_evidence` in the same `server_impl.py` as `1p45l`'s `wave_prepare`/`wave_implement` — different functions; coordinate edits. `1p45s` is independent of the prepare/implement behavior and can land in any order relative to `1p45l`/`1p45m`.
- **Gate watchpoint:** `server_impl.py` + `mcp-tool-surface.md` → `framework_edit_allowed`; seed edits (`170`/`180`/`020`/`110`, prepare/pause prompts) → `seed_edit_allowed`; `AGENTS.md` / `docs/prompts/` → `framework_edit_allowed`. Close each gate immediately after.
- **Test reconciliation:** doc-string-assertion tests reference current seed/prompt wording (`test_server_tools.py`, `test_dashboard_server.py`); `1p45m` must update any that assert the old single-active phrasing — treat failures as the migration signal, not regressions.
- **Meta (the proof of the gap):** this wave could not be **prepared** until `1p458` closed — the `another_wave_active` block fires at *readiness* time today, which is exactly what `1p45l` relocates to the activation step. Resolved: `1p458` closed, `1p45n` prepared. Implementing `1p45n` still takes the single OPEN slot (correct) until it closes.

## Participants

| Role | Lane | Scope |
| ---- | ---- | ----- |
| code-reviewer | required | `1p45l` + `1p45s` — `server_impl.py` lifecycle/tooling changes |
| qa-reviewer | required | All three — AC tables present; `1p45s` is a bug fix (`require_qa_reviewer_for_bug_fixes`) |
| architecture-reviewer | required | `1p45l` — MCP tool contract (`wave_prepare` modes / `wave_implement` precondition) + the single-OPEN lifecycle invariant |
| docs-contract-reviewer | required | `1p45l` (mcp-tool-surface spec + prepare/implement seeds) + `1p45m` (seed/stage-gate/README behavioral-contract sweep) |

## Review Evidence

- wave-council-readiness: approved 2026-06-08 — PASS (moderator: wave-council; primer-depth: full; seats: red-team primer, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: docs-contract-reviewer [seed/spec behavioral-contract changes]; must-fix-count: 0; recommended-applied-in-session: 3 [AC-9 + a guard-at-every-activation-path requirement after the red-team found `wave_reopen` (`server_impl.py:8234`) transitions closed/paused→active with NO single-OPEN guard — a pre-existing latent two-active-wave hole this change must close; an implement-rejects-non-active test-migration task (AC-3); an Option-C visibility-tradeoff risk]; strongest-challenge: relocating the guard risks leaving an activation path unguarded → two OPEN waves; grounded — the guard must run at ALL three `→active`/`→implementing` sites: `wave_prepare(create)` (`:7543`), `wave_implement` (`:7844`), and `wave_reopen` (`:8234`, today unguarded); reality-checker confirmed `wave_implement` already re-gates the council verdict (`:7769`) + lane reviews (`:7789-7803`) so an un-readied planned wave cannot open; strongest-alternative: Option B (a durable, dashboard-visible `ready` status) — rejected for now (wide blast radius across every status consumer; reserved); product-owner: operator-directed capability + operator-authorized prepare; verdict: PASS — admissible for implementation)
- code-reviewer: approved 2026-06-08 — the `server_impl.py` guard relocation + `mode='ready'` are correct; exactly three Status→active/implementing write sites, each guarded; `wave_reopen` hole closed; severity matcher uses whole-word matching.
- qa-reviewer: approved 2026-06-08 — `1p45l` AC-1..AC-9 + `1p45s` AC-1..AC-4 each have real coverage, proven non-vacuous by revert-simulation; no over-mocking; full suite green (2789).
- architecture-reviewer: approved 2026-06-08 — no new module boundary; the wave-status enum is unchanged (readied = `planned` + evidence) so no status consumer breaks; the tool-contract change is documented in `mcp-tool-surface.md`.
- docs-contract-reviewer: approved 2026-06-08 — the single-OPEN reframe is consistent across the live prompt/seed/spec/README/AGENTS surfaces after the in-session fix to three stale architecture-doc lines (`data-and-control-flow.md:84-85`, `current-state.md:36`) that the sweep had missed.
- wave-council-delivery: approved 2026-06-08 — PASS (moderator: wave-council; primer-depth: full; seats: red-team primer, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: docs-contract-reviewer; must-fix-count: 0; one finding [doc-consistency] fixed in-session; backed by 3 independent adversarial verifiers — GUARD-COMPLETENESS pass: the only three `Status→active/implementing` writes in `server_impl.py` (prepare `:7554` create-only, implement `:7883`, reopen `:8291`) are each guarded by `_find_other_active_wave` (`:7455`/`:7836`/`:8275`); `ready`/`dry_run` unguarded; pause/close deactivations correctly unguarded; no fourth path. TEST-FIDELITY pass: all 12 target tests proven non-vacuous by revert-simulation, guard + severity scanner never mocked, AC coverage complete. DOC-CONSISTENCY concern→resolved: three live architecture-doc lines still described the old single-active behavior — exactly the surface `1p45l`'s Affected-Architecture-Docs note flagged — reframed in-session to single-OPEN/guard-at-activation. strongest-challenge: a relocated guard risks an unguarded activation path → two OPEN waves — refuted exhaustively; strongest-alternative: Option B durable `ready` status (reserved); 2789 tests green, docs-lint clean; verdict: PASS — clear to close)
- operator-signoff: approved 2026-06-08 — operator requested review + close.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-08: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: docs-contract-reviewer; strongest-challenge: guard relocation could leave an activation path unguarded → two OPEN waves; reality-checker grounded it — `wave_reopen` (`:8234`) transitions closed/paused→active with NO guard today, so the design must guard all three activation sites (prepare-create `:7543`, implement `:7844`, reopen `:8234`); folded AC-9 + a guard-all-paths requirement; architecture-reviewer: a deliberate MCP-tool-contract change (`wave_prepare` modes + `wave_implement` precondition); "readied = planned + evidence" keeps the status enum unchanged so no status consumer breaks — contract owned here, narrative sweep in `1p45m`; security-reviewer: the single-OPEN guard is a correctness/integrity invariant (not a trust boundary); the bypass risk is closed by guarding all paths (AC-9); no file-access/path/regex surface; qa-reviewer: ACs now span AC-1..AC-9, `wave_implement` re-gates verdict+lanes so un-readied planned waves can't open, flagged migration of the implement-rejects-non-active tests (AC-3 task); qa required because `1p45s` is a bug fix; reality-checker: all three activation sites + the re-gates verified against live source; strongest-alternative: Option B durable visible `ready` status (reserved — Option C accepted tradeoff: readied planned waves are visually indistinguishable from non-readied); material disagreements: none; must-fix: 0; verdict: PASS)
- pre-implementation-review: passed (2026-06-08) — top risk is the guard-relocation control-flow correctness across all three activation paths (`wave_prepare(create)` `:7543`, `wave_implement` `:7844`, `wave_reopen` `:8234`) plus restructuring `wave_prepare` so the single-OPEN guard runs only on the activating path (not `ready`/`dry_run`); addressed by editing each activation site explicitly + AC-1..AC-9 tests. Second risk: the doc-string-assertion test migration (`test_server_tools.py`/`test_dashboard_server.py` assert old single-active wording + implement-rejects-non-active) — treat failures as the migration signal. Builder lanes: `software-engineer` (`server_impl.py` — `1p45l`/`1p45s`), `technical-writer` (`1p45m` seed/doc sweep). Implement order: `1p45l` → `1p45m` (vocabulary dependency); `1p45s` independent.
- **Delivery-phase Wave Council [delivery-council] — 2026-06-08: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: docs-contract-reviewer; backed by 3 independent adversarial verifiers. red-team: relocating the single-OPEN guard could leave an activation path unguarded → two OPEN waves; reality-checker refuted it exhaustively — the only three `Status→active/implementing` writes (prepare create-only `:7554`, implement `:7883`, reopen `:8291`) are each guarded, `ready`/`dry_run` + pause/close correctly unguarded, no fourth path. qa-reviewer: all 12 `1p45l`/`1p45s` tests proven non-vacuous by revert-simulation, no over-mocking, every AC covered, suite green (2789). architecture-reviewer: no new boundary; status enum unchanged (readied = planned + evidence) so no consumer breaks; tool-contract change documented in the spec. security-reviewer: the guard is a correctness/integrity invariant, now airtight across all activation paths; no file-access/trust-boundary surface. docs-contract-reviewer (rotating): the live reframe is consistent, but flagged three stale LIVE architecture-doc lines (`data-and-control-flow.md:84-85`, `current-state.md:36`) — pre-flagged by `1p45l`'s Affected-Architecture-Docs note, missed by the sweep — fixed in-session. material disagreements: none; findings: 1 (doc-consistency) fixed in-session; must-fix: 0. verdict: PASS — clear to close.)

## Dependencies

- No blocking external wave dependencies. Intra-wave: `1p45m` depends on `1p45l`.
- Sequencing note: `1p458` is now closed, so the slot is free and this wave is being prepared. (Fittingly, the limitation that *would* have blocked preparing this alongside an open wave is exactly what `1p45l` removes.)
