# Decouple Wave Readiness From Activation — `wave_prepare(mode='ready')` + Single-OPEN Guard at the Activation Step

Change ID: `1p45l-enh prepare-ready-mode-decouples-readiness-from-activation`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-06-08
Wave: 1p45n wave-readiness-activation-decoupling

## Rationale

Operators must be able to **plan and fully prepare (readiness/council/AC-priority) any number of waves while one wave is being worked**, with the "only one at a time" constraint applying solely to the **OPEN** (being-implemented) wave — never to planning or readiness. (See the operator-stated model captured 2026-06-08.)

Today the framework fuses readiness with activation. `wave_prepare(mode='create')` runs the full readiness pipeline (docs-gardener, docs-lint, prepare-phase Wave Council verdict) **and** writes `Status: active` in the same call (`server_impl.py:7540-7545`), and the single-active guard fires *before* that write (`:7442-7466`) keyed on whether any **other** wave is `active` or `implementing` (`_find_other_active_wave`, `:1768-1790`). Because the guard runs before the `mode == "create"` branch and returns on any diagnostic (`:7460`), it blocks **both** `create` and `dry_run` — so a second wave cannot even be readiness-checked while one is open; the only documented path is to `wave_pause` the open wave first.

`wave_implement` (`:7733-7808`) already requires an `active` wave, re-validates the persisted readiness evidence (council verdict `:7769`, required lane reviews `:7789-7803`), and owns the `→implementing` transition. That makes it the natural — and only necessary — chokepoint for the single-OPEN invariant. This change moves the guard there and adds a readiness-only prepare mode, so readiness becomes free to run in parallel while activation stays serialized.

## Requirements

1. `wave_prepare(mode='ready')` runs the full readiness pipeline (docs-gardener + docs-lint + the prepare-phase Wave Council verdict requirement, identical to `create`) and validates the recorded council signoff, but MUST NOT invoke the single-OPEN guard and MUST NOT transition the wave to `active`. After a clean `ready` pass the wave remains `Status: planned` ("readied").
2. No new wave status is introduced. A "readied" wave is `planned` plus a recorded, valid prepare-phase council verdict (and required lane signoffs) — readiness is expressed by persisted evidence, not a new state value.
3. Any number of waves may be readied concurrently while another wave is `active` or `implementing`; `wave_prepare(mode='ready')` succeeds irrespective of other waves' open state.
4. The single-OPEN invariant (at most one wave in `active` or `implementing`) is enforced ONLY at activation transitions — but at **every** one of them. The guard (`_find_other_active_wave`) MUST run, blocking with `another_wave_active`, at each path that writes `active`/`implementing`: `wave_implement` (`server_impl.py:7844`), `wave_prepare(mode='create')` (`:7543`), AND `wave_reopen` (`:8234`, which today transitions `closed`/`paused`→`active` with NO guard — a pre-existing single-active hole this change must close). Readiness paths (`ready` / `dry_run`) never guard.
5. `wave_implement` MUST accept a readied `planned` wave as a valid starting state (in addition to its current `active` precondition), re-validate the persisted readiness evidence (council verdict + required lane reviews — it already does at `:7769-7803`), run the single-OPEN guard, then transition the wave to `implementing`.
6. `wave_prepare(mode='create')` retains its current "prepare-and-open" behavior — readiness + single-OPEN guard + transition to `active` — for backward compatibility and the common single-wave flow. Its guard is the same single-OPEN guard, applied because `create` activates.
7. `wave_prepare(mode='dry_run')` is read-only and MUST NOT be blocked by the single-OPEN guard (it neither readies nor opens). Today it is incorrectly blocked because the guard runs before the mode check; this is corrected so dry-run validates readiness without taking the slot.
8. When `wave_prepare(mode='create')` or `wave_implement` is blocked by another open wave, the `another_wave_active` diagnostic MUST name `wave_prepare(mode='ready')` as an alternative recovery to pausing the open wave.
9. The tool-surface contract (`docs/specs/mcp-tool-surface.md`) and the owning seeds (implement-feature / the prepare-wave + implement-wave prompt surfaces) describe `ready` mode and the relocated single-OPEN guard.

## Scope

**Problem statement:** Readiness and activation are fused in `wave_prepare(mode='create')`, and the single-OPEN guard runs at readiness time (and even blocks dry-run), so a second wave cannot be readied while one is open without pausing the open wave.

**In scope:**

- `server_impl.py` `wave_prepare_response`: add the `ready` mode; gate the single-OPEN guard so it runs only for the activating path (`create`), not for `ready` or `dry_run`; `ready` records/validates evidence and leaves the wave `planned`.
- `server_impl.py` `wave_implement_response`: accept a readied `planned` wave; add the single-OPEN guard (`_find_other_active_wave`) at the activation transition; keep the existing council-verdict + lane-review re-gates.
- The `another_wave_active` diagnostic messaging (both call sites) — suggest `wave_prepare(mode='ready')`.
- `docs/specs/mcp-tool-surface.md` — `wave_prepare` modes (`dry_run`/`ready`/`create`) and `wave_implement` guard.
- Owning seeds: `170-plan-feature` / `180-implement-feature` (the seed that owns Prepare wave) — describe ready vs open; the prepare-wave / implement-wave prompt surfaces.
- Tests (`test_server_tools.py`): `ready` does not activate and is not guard-blocked; concurrent `ready` while another wave is open; `implement` runs the guard and accepts a readied `planned` wave; `create` still prepares+opens and is guarded; `dry_run` is not blocked.

**Out of scope:**

- A durable `ready`/`prepared` wave status (Option B) — explicitly not done; readiness = `planned` + recorded evidence.
- The single-OPEN terminology + stage-gate documentation sweep across `AGENTS.md`, `README`, `seed 110`/`020`, `project-overview`, `pause-wave`, and the `seed 110`↔`constants.py` status-model reconciliation — sibling change `1p45m`.
- Any change to council/lane review content, the close flow, or dashboard surfacing of a "readied" state.

## Acceptance Criteria

- [x] AC-1: `wave_prepare(mode='ready')` on a wave with clean docs and a recorded valid council verdict completes successfully **while another wave is `active`/`implementing`**, leaves the target `Status: planned`, and emits no `another_wave_active` diagnostic.
- [x] AC-2: After a clean `ready` pass the wave is recognized as "readied" (planned + valid persisted council verdict + required lane signoffs) with no new status value introduced.
- [x] AC-3: `wave_implement(mode='create')` accepts a readied `planned` wave and, when no other wave is `active`/`implementing`, transitions it to `implementing`.
- [x] AC-4: `wave_implement` blocks with `another_wave_active` when another wave is already `active`/`implementing` — the single-OPEN guard now lives at the activation step.
- [x] AC-5: `wave_prepare(mode='create')` still performs readiness + single-OPEN guard + transition to `active` (backward compatible), and is blocked by `another_wave_active` when another wave is open.
- [x] AC-6: `wave_prepare(mode='dry_run')` is not blocked by the single-OPEN guard and reports readiness without taking the slot or writing status.
- [x] AC-7: The `another_wave_active` diagnostic (from prepare-create and implement) names `wave_prepare(mode='ready')` as an alternative recovery to pausing the open wave.
- [x] AC-8: `docs/specs/mcp-tool-surface.md` and the prepare/implement seeds document `ready` mode and the relocated guard; `python3 .wavefoundry/framework/scripts/run_tests.py` is green and docs-lint passes.
- [x] AC-9: `wave_reopen` runs the single-OPEN guard and blocks with `another_wave_active` when another wave is already `active`/`implementing` (closing the pre-existing unguarded-reopen hole); reopening succeeds when no wave is OPEN.

## Tasks

- [x] `server_impl.py` `wave_prepare_response`: introduce `mode='ready'`; move the single-OPEN guard (`:7442-7466`) so it runs only when the call will activate (`create`); for `ready`, run readiness + council-verdict validation and return without the activation write (`:7540-7545`) and without the guard.
- [x] `server_impl.py` `wave_prepare_response`: ensure `dry_run` skips the single-OPEN guard (requirement 7).
- [x] `server_impl.py` `wave_implement_response`: accept `current_status == "planned"` (readied) in addition to `active`; add the single-OPEN guard via `_find_other_active_wave` before transitioning to `implementing`; keep council-verdict + lane re-gates.
- [x] `server_impl.py` `wave_reopen_response` (`:8224-8242`): run the single-OPEN guard before the `closed`/`paused`→`active` write (`:8234`) — closing the pre-existing unguarded-reopen hole.
- [x] Update the `another_wave_active` diagnostic text at both sites to offer `wave_prepare(mode='ready')`.
- [x] `docs/specs/mcp-tool-surface.md`: document `wave_prepare` modes and the `wave_implement` guard.
- [x] Update the implement-feature seed (owner of Prepare wave) + prepare-wave / implement-wave prompt surfaces to describe ready-vs-open.
- [x] Tests: add coverage for AC-1..AC-9 in `test_server_tools.py` — including the `wave_reopen` guard (AC-9); **migrate existing tests that assert `wave_implement` rejects non-active waves** (`wave_not_active`, `:7758`) to the new accept-readied-`planned` behavior. Run `python3 .wavefoundry/framework/scripts/run_tests.py` and docs-lint.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| prepare-ready-mode | software-engineer | — | `wave_prepare`: add `ready`, gate the single-OPEN guard to the activating path, skip it for dry_run. |
| implement-guard | software-engineer | prepare-ready-mode | `wave_implement`: accept readied `planned`, run the single-OPEN guard at activation. |
| contract-docs-and-seeds | docs-contract-reviewer | implement-guard | mcp-tool-surface spec + implement/prepare seeds describe ready-vs-open and the relocated guard. |
| tests | qa-reviewer | implement-guard | AC-1..AC-7 coverage in `test_server_tools.py`. |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` — `wave_prepare_response` and `wave_implement_response` share the single-OPEN guard helper (`_find_other_active_wave`); coordinate so the guard has exactly one enforcement point (activation) after the change.
- `docs/specs/mcp-tool-surface.md` — manifest/contract surface; coordinate with sibling `1p45m`'s doc sweep so the contract and the narrative reframing agree on terminology (single-OPEN, readied).

## Affected Architecture Docs

This alters a primary control path (the wave lifecycle: where the single-OPEN invariant is enforced) and the MCP tool contract. Update `docs/specs/mcp-tool-surface.md` (tool contract). The lifecycle **state model** itself (statuses + transitions) is documented in `seed 110` and `constants.py`; reconciling that model with the new ready/open distinction is handled by sibling `1p45m`. Implementer to confirm at Prepare whether `docs/architecture/data-and-control-flow.md` carries a wave-lifecycle diagram that needs the guard-location update.

## AC Priority

_Confirmed at Prepare wave 1p45n (2026-06-08) — classifications interrogated by the readiness council; AC-9 added for the `wave_reopen` guard hole found during prepare._


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The core capability — ready a wave while another is open. |
| AC-2 | required   | "Readied = planned + evidence" is the chosen model (no new status). |
| AC-3 | required   | A readied wave must be openable via the activation step. |
| AC-4 | required   | The single-OPEN invariant must hold — guard at activation. |
| AC-5 | required   | Backward compatibility: the existing prepare-and-open flow must not break. |
| AC-6 | important  | Dry-run readiness should never take the slot (fixes today's over-blocking). |
| AC-7 | important  | Discoverability of the new escape path from the block diagnostic. |
| AC-8 | required   | Contract docs/seeds match behavior; green suite + lint. |
| AC-9 | required   | Close the latent unguarded-`wave_reopen` single-active hole — invariant integrity. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Added `wave_prepare(mode='ready')` (readiness without activation/guard) and relocated the single-OPEN guard to all three activation paths — `wave_prepare(create)`, `wave_implement` (now accepts a readied `planned` wave), and `wave_reopen` (previously unguarded). Updated the tool docstring + `mcp-tool-surface.md` + prepare/implement prompts. | `run_tests.py` green (2789); AC-1/3/4/6/7/9 behavioral, AC-5 existing; closed the pre-existing unguarded-reopen hole (AC-9). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | **Selected — Option C:** add `wave_prepare(mode='ready')` (full readiness, persist evidence, no guard, no activation) and relocate the single-OPEN guard to the activation step (`wave_implement`), with no new wave status. | Delivers the operator's model (ready many, open one) by reusing trusted machinery — `wave_implement` already re-validates persisted readiness evidence — at the smallest blast radius (one tool's modes + the guard's location). Backward compatible: `create` still prepares-and-opens. | **(A) Doc-only reframing** — rejected as primary: clarifies wording but does not actually allow readiness without taking the slot (the guard still blocks). Kept as the sibling doc sweep `1p45m`. **(B) New durable `ready` status + separate Open step** — rejected for now: cleanest and makes "readied" first-class/visible, but touches every status consumer (state machine, tools, lint, dashboard, `wave_current`) — medium-high blast radius; reserve for a later wave if "readied" should be dashboard-visible. |
| 2026-06-08 | Keep `wave_prepare(mode='create')` as a "prepare-and-open" convenience rather than removing it. | Avoids breaking the common single-wave flow and existing callers/tests; `create` simply runs the guard because it activates. | Remove `create`, force ready→implement always (more disruptive, larger test churn). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Two waves could end up OPEN if any activation path is left unguarded. | The single-OPEN guard runs at **every** activation transition — `wave_implement`, `wave_prepare(mode='create')`, and `wave_reopen` (`:8234`, previously unguarded) — all using one source of truth (`_find_other_active_wave`, which counts `active`+`implementing`). AC-4 + AC-9 tests; the implementation audits all `→active`/`→implementing` writes. |
| `wave_implement` accepting `planned` could open an UN-readied wave. | `wave_implement` already re-gates the council verdict (`:7769`) and required lane reviews (`:7789-7803`); a non-readied `planned` wave fails those gates. AC-3 asserts only a readied wave opens. |
| Existing callers/tests assume `prepare(create)` always activates / `wave_implement` rejects non-active. | `create` behavior is unchanged (AC-5); `ready` is additive; the implement-rejects-planned tests are migrated (AC-3 task). |
| Readied `planned` waves are visually indistinguishable from non-readied `planned` waves (no `ready` status under Option C). | Accepted tradeoff — readiness is recorded in evidence; Option B (a durable, dashboard-visible `ready` status) is the reserved upgrade if visibility becomes load-bearing (see Decision Log). |
| Terminology drift between this contract change and the sibling doc sweep. | Serialization point on `mcp-tool-surface.md`; `1p45m` depends on this change's vocabulary (single-OPEN, readied). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
