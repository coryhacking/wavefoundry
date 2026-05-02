# Single-active-wave guard, wave_pause status transition, and wave_current list return

Change ID: `12as6-enh single-active-wave-guard`
Change Status: `done`
Owner: Engineering
Status: done
Last verified: 2026-05-01
Wave: 12as7 wave-lifecycle-tool-fixes

## Rationale

Nothing in the framework prevents a second wave from going `active`. `wave_prepare` flips status to `active` (`.wavefoundry/framework/scripts/server.py:3357`) without checking whether another wave already holds that status. Downstream tools assume one: `current_wave()` at `server.py:811` returns the **first** wave with status `active` or `planned` — if two are active, agents and `wave_audit` / post-edit hooks silently see whichever comes first in directory order. Operators who forget to `wave_pause` the current wave before preparing a new one can end up with split state (two journal captures, two handoff contexts, two review surfaces) without any diagnostic.

Discovered during 2026-05-01 session: **`wave_pause` today does not change wave status** — it only writes a session-handoff entry (`server.py:3370`, `wave_pause_response`). The wave.md `Status:` field stays `active` after pause. This means the recovery path the proposed guard recommends (`wave_pause` then re-run `wave_prepare`) doesn't actually clear the "another wave is active" condition without a manual wave.md edit. Operator hit this while trying to context-switch from `12ahv mcp-agent-surface` to `12as1 design-system-extraction` on 2026-05-01 — `wave_pause` succeeded but `12ahv` stayed `active`; manual edit to `Status: paused` was required.

This change has three parts that must land together:
1. **Guard:** single-active-wave enforcement in `wave_prepare` with a clear recovery diagnostic.
2. **Recovery:** extend `wave_pause` to actually transition wave status from `active` to `paused`, so the guard's recommended recovery path works end-to-end.
3. **Visibility:** change `wave_current` to return **all** non-closed waves (active, planned, paused — active first if present) as `data.waves[]` so operators and agents can see the full in-flight lifecycle state at a glance. Today `wave_current` returns only one wave and masks the rest.

Without all three, the guard's error message ("Pause it before preparing") doesn't match reality, and operators can't see what other waves exist when choosing whether to pause.

**Breaking change note:** the `wave_current` envelope moves from `data.wave` (object or null) to `data.waves` (array, possibly empty). Hard break — no transitional dual-emit period. All call sites update in this change. Rationale in Decision Log below.

## Requirements

1. **Hard guard in `wave_prepare_response` (`server.py:3235`).** Before flipping status to `active` at line 3357, check whether any other wave already has status `active`. If so, return `status: "error"` with the envelope below instead of performing the status flip.
2. **Error envelope shape.** When another wave is active:
   ```json
   {
     "status": "error",
     "data": {
       "wave_id": "<target wave id>",
       "mode": "create",
       "active_wave_id": "<other wave id>",
       "active_wave_path": "<repo-relative path>"
     },
     "diagnostics": [{
       "code": "another_wave_active",
       "message": "Wave '<active wave id>' is already active. Pause it before preparing '<target wave id>'.",
       "recovery_tools": ["wave_pause", "wave_current"],
       "recovery_usage": "wave_pause(wave_id='<active wave id>', mode='create')"
     }],
     "next_tools": ["wave_pause", "wave_current"],
     "usage": "wave_pause(wave_id='<active wave id>', mode='create')"
   }
   ```
3. **Dry-run must also guard.** `mode="dry_run"` must return the same diagnostic shape (with `mode: "dry_run"` in `data`). Dry-run is used by agents to check readiness before committing; letting dry-run pass silently when a prepare-create would fail defeats the purpose of a read-only preview.
4. **Self-prepare is allowed.** If the target wave is itself already `active` (e.g., operator re-runs `wave_prepare` on the currently active wave), the guard must not trigger. That path stays a no-op status flip and continues through the rest of the existing prepare logic (lint, garden, admitted-change relocation).
5. **Detection method.** Reuse existing `list_waves(root)` / `cache.list_waves_cached()` to enumerate wave statuses. Do not introduce a new filesystem scanner. The guard check runs after admitted-change validation and after lint/garden (so lint/garden failures still surface as the primary diagnostics); it runs before the status write at line 3357.
6. **Ordering with other diagnostics.** If both (a) another wave is active and (b) lint or garden fails, both diagnostics must appear in the response. The existing code already aggregates diagnostics into a single error response when any are present — extend that aggregation rather than short-circuiting.
7. **Prompt surface update.** `docs/prompts/prepare-wave.md` must document the guard: one-active-wave rule, recovery path, and a pointer to `wave_pause`.
8. **Seed update.** `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` (or whichever seed owns prepare-wave guidance — locate at implementation) must mention the guard so target repos get the rule when they refresh.
9. **AGENTS.md update.** The "Stage Gate (repository code)" section in `AGENTS.md` should note that preparing a new wave requires pausing any currently active wave first, with a short recovery phrase pointing at `wave_pause`.
10. **No new policy enforcement beyond `wave_prepare`.** Do not add a validator that flags "two waves currently active" as a lint failure. A validator would spuriously fire during the brief window a pause is in flight, and legitimate tooling states (paused but still tracked, closing but not yet closed) could trip it. The guard belongs at the transition, not the state.

11. **`wave_pause` status transition (`server.py:3370` `wave_pause_response`).** Extend `wave_pause_response` to transition the wave.md `Status:` field from `active` to `paused` when `mode="create"`. Behavior:
    - If current status is `active` → rewrite to `paused`.
    - If current status is already `paused` → no-op (idempotent), return successful response.
    - If current status is `planned` or anything else → no-op, but add a non-blocking advisory diagnostic `pause_on_non_active_wave` (informational, not an error) so operators know pause on a planned wave only wrote the handoff.
    - The existing session-handoff write must continue to run regardless of status transition outcome.
    - Dry-run preview must report the intended transition in `data` (e.g., `"status_transition": {"from": "active", "to": "paused"}`) without writing.

12. **`paused` is a recognized status but not a `current_wave` result.** `current_wave` at `server.py:811` today returns the first wave with status `active` or `planned`. Paused waves must not appear in `current_wave`. No change needed to `current_wave` logic itself — since it already filters to `("active", "planned")`, adding `paused` to the status vocabulary naturally excludes paused waves. Document this explicitly in the prompt doc so operators understand a paused wave is intentionally not "the current wave."

13. **Resume path.** Operators resume a paused wave by re-running `wave_prepare(wave_id, mode="create")`. Resume semantics:
    - The guard check in Requirement 1 **still applies** on resume: if **any other** wave is `active`, resume fails with the same `another_wave_active` diagnostic. Resuming while another wave is active would recreate the split-state problem the guard exists to prevent.
    - The self-target case (the wave being resumed is itself the one currently in `paused` state) does **not** trigger the guard — that's the allowed transition, not a concurrent-active state. The existing self-prepare allowance (Requirement 4) covers `active → active`; extend that logic to also cover `paused → active` on the same wave.
    - In short: the guard keys on "is any *other* wave `active`?" — not on the target wave's current status. Target status just controls which transition runs (`planned → active`, `paused → active`, or `active → active` idempotent).

14. **Docs lint acceptance.** `paused` must not trigger any docs-lint warning. Verify the existing lint rules do not restrict Status values; if they do, extend the recognized vocabulary to include `paused`. Add a test that asserts a paused wave.md passes lint unchanged.

15. **`wave_current` returns all non-closed waves.** Replace the current single-wave response (`data.wave` object or null) with a list response (`data.waves` array, possibly empty). Behavior:
    - Include every wave whose status is **not** `closed` (i.e., `active`, `planned`, `paused`, plus any other transient statuses like `stub` or `ready` if they exist in the repo).
    - Ordering: active first (0 or 1 entry), then planned in lifecycle-ID order, then paused in lifecycle-ID order, then any other statuses in lifecycle-ID order. "Lifecycle-ID order" = the natural ordering used by `list_waves`.
    - Each entry keeps the existing per-wave shape (`wave_id`, `status`, `changes`, `path`) plus a per-entry `next_action`:
      - `active` → `"implement_wave"`
      - `planned` → `"prepare_wave"`
      - `paused` → `"resume_wave"`
      - other → `"prepare_wave"` (conservative default)
    - Empty array (no non-closed waves): `status: "ok"`, `data.waves: []`, same `no_active_wave` diagnostic as today.
    - Top-level `next_tools` and `usage` still point at `wave_get_change` for the first entry (if any); otherwise `wave_list_waves` / `wave_list_plans` as today.

16. **Breaking change — hard envelope migration.** `data.wave` is **removed**. Callers must read `data.waves[0]` (with empty-array handling) to get the equivalent of the pre-change "current wave." No transitional period. The existing `change_status_drift` diagnostic still attaches to the response and still refers only to the active wave (if any); other waves are not drift-scanned in this call.

17. **Call-site migration — in-tree.** All in-tree consumers of `data.wave` must be updated in this change:
    - `wave_audit_response` (search for `wave_current_response` calls)
    - Any prompt or AGENTS.md text that tells operators to read `data.wave`
    - Existing tests under `.wavefoundry/framework/scripts/tests/test_server_tools.py` that assert on `data.wave` — rewrite to read `data.waves`
    - Prompt surface docs under `docs/prompts/` that show example `wave_current` responses
    - Seeds under `.wavefoundry/framework/seeds/` that embed `wave_current` examples
    - `AGENTS.md` MCP tool table entries mentioning `wave_current`
    Implementation must grep for `data.wave` and `data\["wave"\]` (and similar) before declaring migration complete. New grep must return zero hits outside historical wave records and progress logs.

18. **`change_status_drift` diagnostic behavior unchanged.** Drift detection still runs only on the active wave (since drift is a mismatch between wave.md Change Status and change doc status, and is only meaningful for in-flight waves). The diagnostic attaches to the response regardless of how many waves appear in `data.waves`; it describes the active wave.

19. **`resume_wave` is a semantic hint, not a new tool.** The `next_action` value `"resume_wave"` on paused entries is an operator-facing hint. The underlying transition is still `wave_prepare(wave_id, mode="create")` on the paused wave (which triggers `paused → active` per Requirement 13 and the single-active-wave guard per Requirement 1). Seeded guidance and prompt docs must document this mapping explicitly: "When a wave shows `next_action: resume_wave`, call `wave_prepare` on that wave." A dedicated `wave_resume` MCP tool is **out of scope** for this change (listed under Out of scope below); it can be added in a follow-on if the alias becomes ergonomically valuable.

## Scope

**Problem statement:** `wave_prepare` has no check preventing a second wave from becoming `active`, and `wave_pause` does not transition status — it only writes a session-handoff entry. Together these leave operators with no working recovery path for context-switching between waves. The fix is a single-site guard at the state transition plus a status-transition extension to `wave_pause` so the guard's recommended recovery actually works.

**In scope:**

- `server.py` `wave_prepare_response` — guard check before line 3357 status flip.
- Diagnostic envelope with `another_wave_active` code and `wave_pause` recovery.
- Equivalent behavior in `dry_run` and `create` modes.
- `server.py` `wave_pause_response` (`:3370`) — extend to transition `Status:` from `active` to `paused` when `mode="create"`.
- `server.py` `wave_prepare_response` — allow `paused → active` self-transition on the target wave (resume path).
- `paused` added to the recognized wave-status vocabulary.
- `server.py` `wave_current_response` (`:1640`) — breaking change from `data.wave` to `data.waves[]`; include active/planned/paused/other non-closed waves; paused-wave entries carry `next_action: "resume_wave"`.
- In-tree migration of every `data.wave` reader.
- Tests under `.wavefoundry/framework/scripts/tests/test_server_tools.py`.
- Prompt doc updates: `docs/prompts/prepare-wave.md`, `docs/prompts/pause-wave.md`.
- Seed update: the seed(s) that own `wave_prepare`, `wave_pause`, and `wave_current` guidance; also seeds/prompts that embed `wave_current` examples.
- `AGENTS.md` updates: pause-then-prepare note, `wave_current` envelope shape update, `resume_wave` next-action.

**Out of scope:**

- A standalone lint validator that flags multiple active waves as a docs-lint failure (explicitly deferred per Requirement 10).
- Automatic pause of the active wave. Pause is an operator decision — the guard surfaces the choice, it does not make the choice.
- Multi-wave implementation workflows. If we ever want true concurrent waves, that is a separate design.
- Changes to `wave_current` / `list_waves` / `wave_audit` logic (they already filter on `active`/`planned`, so `paused` naturally excludes — just document).
- A dedicated `wave_resume` MCP tool. Resume is modeled as re-running `wave_prepare` on the paused wave, surfaced via the `next_action: "resume_wave"` operator hint. A new tool is a possible follow-on if the alias proves valuable.

## Acceptance Criteria

- **AC-1** (Guard blocks `create`): with wave A active and wave B planned, `wave_prepare(wave_id="B", mode="create")` returns `status: "error"` with a `another_wave_active` diagnostic; wave B's status stays `planned`. Asserted by `test_wave_prepare_guards_when_another_wave_active_create`.
- **AC-2** (Guard blocks `dry_run`): same setup, `mode="dry_run"` returns the same diagnostic shape with `data.mode == "dry_run"`. Asserted by `test_wave_prepare_guards_when_another_wave_active_dry_run`.
- **AC-3** (Self-prepare allowed from `active`): with wave A active, `wave_prepare(wave_id="A", mode="create")` does not trigger the guard; the existing no-op status flip and lint/garden flow still runs. Asserted by `test_wave_prepare_self_reprepare_allowed`.
- **AC-4** (Diagnostic envelope shape): response matches the shape in Requirement 2 (codes, keys, `recovery_usage` string pattern). Asserted by `test_wave_prepare_another_wave_active_envelope_shape`.
- **AC-5** (Recovery path works end-to-end): pause wave A via `wave_pause(mode="create")` (which transitions A to `paused` per Requirement 11) → re-run `wave_prepare(wave_id="B", mode="create")` → wave B becomes active, wave A remains `paused`. Asserted by `test_wave_prepare_after_pause_succeeds`.
- **AC-6** (Diagnostic aggregation): when another wave is active AND lint fails, both diagnostics appear in the response. Asserted by `test_wave_prepare_aggregates_active_wave_and_lint_diagnostics`.
- **AC-7** (Pause transitions status from `active` to `paused`): `wave_pause(wave_id="A", mode="create")` on an active wave rewrites `Status: active` to `Status: paused` in wave.md and still writes the session-handoff entry. Asserted by `test_wave_pause_transitions_active_to_paused`.
- **AC-8** (Pause idempotent on already-paused wave): `wave_pause(mode="create")` on a paused wave is a no-op status-wise and returns success; handoff still updates. Asserted by `test_wave_pause_idempotent_on_paused`.
- **AC-9** (Pause advisory on non-active wave): `wave_pause(mode="create")` on a planned wave does not change status but returns a non-blocking `pause_on_non_active_wave` advisory diagnostic. Asserted by `test_wave_pause_advisory_on_planned`.
- **AC-10** (Pause dry-run reports transition): `wave_pause(mode="dry_run")` on an active wave returns `data.status_transition == {"from": "active", "to": "paused"}` and does not write wave.md. Asserted by `test_wave_pause_dry_run_reports_transition`.
- **AC-11** (Resume path — `paused → active` with no other active wave): `wave_prepare(wave_id="A", mode="create")` on a paused wave A transitions `paused → active` when no other wave is `active`. The guard does not trigger because the target is the wave doing the transition. Asserted by `test_wave_prepare_resumes_paused_wave`.
- **AC-11b** (Resume blocked when another wave is active): with wave A paused and wave B active, `wave_prepare(wave_id="A", mode="create")` returns the same `another_wave_active` diagnostic as the planned → active case. The guard keys on "is any other wave active?", not on the target wave's status. Asserted by `test_wave_prepare_resume_blocked_when_other_active`.
- **AC-12** (Paused waves excluded from `wave_current`): `wave_current` does not return a wave with `Status: paused`. Existing `current_wave` filter on `("active", "planned")` already handles this — AC verifies with a test. Asserted by `test_wave_current_skips_paused`.
- **AC-13** (Paused passes docs lint): a wave.md with `Status: paused` passes `wave_validate` with no new errors. Asserted by `test_wave_validate_accepts_paused_status`.
- **AC-14** (Prompt docs): `docs/prompts/prepare-wave.md` and `docs/prompts/pause-wave.md` describe the one-active-wave rule, the pause-then-prepare recovery path, and the `paused` status.
- **AC-15** (Seed and AGENTS.md): seed prompts and `AGENTS.md` note the guard and the pause transition.
- **AC-16** (Envelope compat): no other `wave_prepare` or `wave_pause` behavior changes beyond what is specified. Existing tests pass without modification (except pause tests that asserted status stays `active` — those must be updated to match the new transition semantics).
- **AC-17** (`wave_current` returns `data.waves[]`): response shape is `data.waves` array, not `data.wave`. Empty array when nothing is open. Asserted by `test_wave_current_returns_waves_array`.
- **AC-18** (`wave_current` ordering): with one active, two planned, one paused, response order is active → planned (lifecycle-ID order) → paused (lifecycle-ID order). Asserted by `test_wave_current_orders_active_planned_paused`.
- **AC-19** (`wave_current` entry shape): each entry retains the previous per-wave fields (`wave_id`, `status`, `changes`, `path`) plus `next_action`. Paused entries have `next_action: "resume_wave"`; active entries `"implement_wave"`; planned entries `"prepare_wave"`. Asserted by `test_wave_current_entry_shape` and `test_wave_current_paused_next_action_is_resume_wave`.
- **AC-20** (`wave_current` breaking migration): all in-tree callers of `data.wave` are updated. A test asserts a fresh `rg "data.wave\b|data\[.wave.\]" .wavefoundry/framework/ docs/` (or the repo's equivalent) returns zero hits outside `docs/agents/journals/**` and `docs/waves/**` (historical). Asserted by `test_wave_current_no_stale_data_wave_references`.
- **AC-21** (`wave_audit` still works): `wave_audit` reads the active wave via `data.waves[0]` when `data.waves[0].status == "active"`, else reports "no active wave" (unchanged behavior from operator perspective). Asserted by existing `wave_audit` tests after their internal updates.

## Tasks

- Before editing framework scripts, set `.wavefoundry/guard-overrides.json` `framework_edit_allowed.enabled: true`; restore after. Before editing seeds, set `seed_edit_allowed.enabled: true`; restore after.
- `.wavefoundry/framework/scripts/server.py` `wave_prepare_response`:
  - Add a helper `_find_other_active_wave(root, target_wave_md, cache) -> Optional[Wave]` that returns the first wave with status `active` whose path is not the target. Reuse `list_waves` / `cache.list_waves_cached`.
  - In `wave_prepare_response`, after admitted-change validation and after lint/garden (so existing diagnostics accumulate), compute the other-active-wave result.
  - When another wave is active, append the `another_wave_active` diagnostic. Keep the existing `if diagnostics: return _response("error", ...)` aggregation at line 3353-3354. Ensure `data` includes `active_wave_id` and `active_wave_path` when the guard triggers.
  - The guard check runs for both `mode="dry_run"` and `mode="create"`. Dry-run already returns before the line 3357 write; adding the diagnostic is enough.
  - Extend the status-flip at line 3357 to accept current status values of `active`, `planned`, **or `paused`** — all transition to `active`. Previously it wrote `active` only when the status was not already `active`; keep that idempotency.
- `.wavefoundry/framework/scripts/server.py` `wave_current_response` (`:1640`):
  - Replace single-wave return with list return. Build the list by filtering `list_waves(root)` (or `cache.list_waves_cached()`) to exclude `closed` status, then sort: active first, then planned (lifecycle-ID order), then paused (lifecycle-ID order), then others.
  - Attach `next_action` per entry using the mapping in Requirement 15 (active → `implement_wave`, planned → `prepare_wave`, paused → `resume_wave`, other → `prepare_wave`).
  - Keep the existing `change_status_drift` detection; run it only against the active wave (if any) per Requirement 18.
  - Keep `no_active_wave` diagnostic when `data.waves == []`.
  - Update the top-level `usage` and `next_tools` to use `data.waves[0]` when non-empty; otherwise the existing empty-state recovery.
- In-tree call-site migration (Requirement 17):
  - `wave_audit_response` — find any read of `data.wave` and rewrite to `data.waves[0]` with empty-array guard.
  - Grep for `data.wave`, `data\["wave"\]`, and `wave.get("wave")` style reads across `.wavefoundry/framework/scripts/**`, `docs/prompts/**`, `.wavefoundry/framework/seeds/**`, and `AGENTS.md`. Update every hit. Historical journals and wave records under `docs/agents/journals/**` and `docs/waves/**` are frozen history — do not touch.
  - Update any docstrings or prompt-surface examples showing `wave_current` responses.
- `.wavefoundry/framework/scripts/server.py` `wave_pause_response` (`:3370`):
  - After resolving the wave path, read the wave.md, locate the `Status:` line via the existing `_STATUS_PATTERN`.
  - Compute `status_transition`: if current is `active` → `paused`; if `paused` → no-op; if anything else → no-op + advisory diagnostic `pause_on_non_active_wave`.
  - For `mode="dry_run"`: include `status_transition` in `data`, do not write wave.md.
  - For `mode="create"`: if transition is `active → paused`, write the new status to wave.md before writing the session-handoff entry. Do not re-order the handoff write — it still runs after the status write (or on its own when no transition occurs).
  - Include `status_transition: {"from": "...", "to": "..."}` in the response `data` regardless of mode.
  - Invalidate the cache and trigger background index refresh for wave.md when it is rewritten.
- Add tests in `.wavefoundry/framework/scripts/tests/test_server_tools.py`:
  - `test_wave_prepare_guards_when_another_wave_active_create`
  - `test_wave_prepare_guards_when_another_wave_active_dry_run`
  - `test_wave_prepare_self_reprepare_allowed`
  - `test_wave_prepare_another_wave_active_envelope_shape`
  - `test_wave_prepare_after_pause_succeeds`
  - `test_wave_prepare_aggregates_active_wave_and_lint_diagnostics`
  - `test_wave_prepare_resumes_paused_wave`
  - `test_wave_prepare_resume_blocked_when_other_active`
  - `test_wave_pause_transitions_active_to_paused`
  - `test_wave_pause_idempotent_on_paused`
  - `test_wave_pause_advisory_on_planned`
  - `test_wave_pause_dry_run_reports_transition`
  - `test_wave_current_skips_paused`
  - `test_wave_validate_accepts_paused_status`
  - `test_wave_current_returns_waves_array`
  - `test_wave_current_orders_active_planned_paused`
  - `test_wave_current_entry_shape`
  - `test_wave_current_paused_next_action_is_resume_wave`
  - `test_wave_current_empty_state_returns_empty_array`
  - `test_wave_current_no_stale_data_wave_references` (asserts the in-tree grep returns no hits)
- Review existing `wave_pause` tests — any assertion that `Status:` stays unchanged after pause must be updated to match the new transition semantics. Document the updated assertions in the change's Progress Log.
- Review existing `wave_current` tests (grep `wave_current_response` and `current_wave(` in `test_server_tools.py`) — assertions on `data["wave"]` must rewrite to `data["waves"][0]` (with empty-array handling). `test_no_active_wave_path` at test_server_tools.py:1739 and `test_current_wave_returns_no_active_wave_message` at :2362 and siblings around :485-500 and :2452-2503 must migrate.
- Review existing `wave_audit` tests — any that read `wave_current` results must migrate to the new envelope.
- Run framework tests: `python3 .wavefoundry/framework/scripts/run_tests.py`. All existing tests (after the updates above) must pass.
- Update `docs/prompts/prepare-wave.md` with the one-active-wave rule and recovery path.
- Update `docs/prompts/pause-wave.md` with the status-transition behavior and the `paused` status.
- Update `docs/prompts/` entries that mention `wave_current` response shape (grep; likely `docs/prompts/index.md`, `docs/prompts/implement-wave.md`, agent prompt docs under `docs/prompts/agents/`) with the new `data.waves[]` shape and `resume_wave` next-action.
- Update the seed(s) that own `wave_prepare`, `wave_pause`, and `wave_current` guidance (locate via grep at implementation).
- Update `AGENTS.md`:
  - Stage Gate section: short note about pausing the current active wave before preparing a new one.
  - `wave_pause` transitions status (brief note).
  - `wave_current` returns `data.waves[]` of non-closed waves, active first; paused entries' `next_action` is `resume_wave` which maps to `wave_prepare`.
- Update any `docs/references/` or `docs/architecture/` docs that embed `wave_current` examples.
- Restore all guard flags to `false`.
- Run `wave_validate` to confirm docs lint is clean.

## Agent Execution Graph


| Workstream                 | Owner       | Depends On                                   | Notes                                                                               |
| -------------------------- | ----------- | -------------------------------------------- | ----------------------------------------------------------------------------------- |
| pause-status-transition    | implementer | —                                            | `wave_pause_response` writes `active → paused`                                      |
| guard-implementation       | implementer | —                                            | Helper + `wave_prepare_response` change                                             |
| resume-path                | implementer | pause-status-transition, guard-implementation | Accept `paused → active` in `wave_prepare`                                          |
| wave-current-list-shape    | implementer | —                                            | `wave_current_response` returns `data.waves[]`; paused → `resume_wave` next-action  |
| callsite-migration         | implementer | wave-current-list-shape                      | Update every `data.wave` reader in-tree (server, tests, prompts, seeds, AGENTS.md)  |
| tests                      | implementer | pause-status-transition, guard-implementation, resume-path, wave-current-list-shape, callsite-migration | 19 new tests + existing pause/current/audit test updates |
| docs                       | implementer | all above                                    | prepare-wave / pause-wave / wave_current prompts, seeds, `AGENTS.md`                |
| review                     | reviewer    | all above                                    | code-reviewer + qa-reviewer + docs-contract lanes                                   |


## Serialization Points

- `server.py` `wave_prepare_response` and `wave_pause_response` are single-owner edits. They are adjacent functions (`:3235` and `:3370`) but do not share helpers beyond `_STATUS_PATTERN`; parallel work within this change is safe.
- No collision with `12as3-bug wave-create-scaffold-and-admit-placement` (different functions).

## Affected Architecture Docs

N/A — contained to a single server function and its tests, plus prompt/seed/AGENTS documentation. No module-boundary, data-flow, or verification-contract impact. If `docs/architecture/current-state.md` describes the wave lifecycle explicitly, add a one-line note about the guard at implementation.

## AC Priority

(Populated at Prepare wave.)


| AC    | Priority     | Rationale                                                                       |
| ----- | ------------ | ------------------------------------------------------------------------------- |
| AC-1  | required     | Core protection: guard must block create when another wave is active.           |
| AC-2  | required     | Dry-run must surface the same diagnostic; silent dry-run defeats readiness check. |
| AC-3  | required     | Self-prepare must remain idempotent; re-running prepare on the active wave is a common recovery. |
| AC-4  | required     | Envelope shape is the downstream contract; agents rely on diagnostic codes.     |
| AC-5  | required     | End-to-end pause-then-prepare is the recovery the diagnostic suggests.          |
| AC-6  | important    | Diagnostic aggregation keeps error batching consistent with existing behavior.  |
| AC-7  | required     | Pause must transition status; without this the guard's recovery path doesn't work. |
| AC-8  | required     | Pause idempotency on paused wave prevents accidental state churn on re-invocation. |
| AC-9  | important    | Advisory on planned wave keeps operators informed without erroring.             |
| AC-10 | important    | Dry-run transition preview matches create-mode semantics.                       |
| AC-11 | required     | Resume path is the mirror of pause; without it paused waves cannot re-enter.    |
| AC-11b | required    | Resume must still honor the single-active-wave invariant; bypassing it on resume defeats the guard. |
| AC-12 | required     | Paused waves must be excluded from `wave_current` to restore single-active semantics. |
| AC-13 | required     | Lint must accept `paused` or the scaffold breaks on first pause.                |
| AC-14 | important    | Prompt doc visibility is how operators discover the rule without hitting it.    |
| AC-15 | important    | Seed propagation gets the rule into target repos on refresh.                    |
| AC-16 | required     | Envelope compat prevents silent breakage of downstream MCP callers.             |
| AC-17 | required     | `data.waves[]` is the new envelope; callers migrate in this change.             |
| AC-18 | required     | Ordering determines which wave an operator sees first; active-first is the invariant. |
| AC-19 | required     | Per-entry `next_action` is how operators learn what to do next; `resume_wave` is required for paused. |
| AC-20 | required     | Grep-based migration check prevents stale `data.wave` readers from slipping through. |
| AC-21 | required     | `wave_audit` is the most-called consumer; broken audit would silently confuse lifecycle recovery. |


## Progress Log


| Date       | Update                                                                                                                                           | Evidence                   |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------- |
| 2026-05-01 | Enhancement opened after noticing no enforcement exists for "one active wave at a time" during wave `12as1 design-system-extraction` creation  | Session transcript; `server.py:811`, `server.py:3357` |
| 2026-05-01 | Scope expanded: `wave_pause` today only writes the session-handoff entry, it does not transition wave status. Manual `Status: paused` edit on `12ahv mcp-agent-surface` was required to clear it from `wave_current` during context-switch to `12as1`. This change now also extends `wave_pause` to write `active → paused`, adds resume semantics in `wave_prepare` (paused → active), and adds `paused` to the recognized status vocabulary. | Operator direction; `server.py:3370` `wave_pause_response`; manual edit to `docs/waves/12ahv mcp-agent-surface/wave.md` line 4 on 2026-05-01 |
| 2026-05-01 | Scope expanded further: `wave_current` changes from returning a single wave (`data.wave`) to returning all non-closed waves (`data.waves[]` — active first, then planned, then paused). Hard-break envelope change with full in-tree migration. Per-entry `next_action` becomes `"resume_wave"` for paused entries (semantic hint; underlying transition remains `wave_prepare`). No new `wave_resume` tool in this change. | Operator direction; `server.py:1640` `wave_current_response` |
| 2026-05-01 | Implementation: added `_find_other_active_wave` helper and guard check in `wave_prepare_response` (server.py:3410); extended `wave_pause_response` with status-transition logic (server.py:3406+); rewrote `wave_current_response` to return `data.waves[]` with per-entry `next_action` mapping (active→implement_wave, planned→prepare_wave, paused→resume_wave); added 17 new tests across four test classes; updated `docs/prompts/prepare-wave.md` and `docs/prompts/pause-wave.md` and `AGENTS.md`. No other in-tree `data["wave"]` readers existed (audit producer-key in `wave_audit_response` is a separate envelope and unaffected). All 426 framework tests pass; docs lint clean. | server.py, tests/test_server_tools.py, docs/prompts/*.md, AGENTS.md diffs |


## Decision Log


| Date       | Decision                                                                                          | Reason                                                                                                                  | Alternatives                                                          |
| ---------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 2026-05-01 | Guard lives in `wave_prepare_response`, not in a separate validator                               | State transition is the right place; a validator would fire on legitimate transient states (pausing, closing, etc.)   | Validator at lint time; state-machine check elsewhere                 |
| 2026-05-01 | Dry-run triggers the guard identically to create                                                  | Silent dry-run passes defeat the readiness-check purpose of dry-run                                                     | Dry-run bypasses guard (less safe)                                    |
| 2026-05-01 | No automatic pause — operator decides whether to pause                                            | Pausing changes wave state and handoff semantics; the guard surfaces the choice without making it                       | Auto-pause the current active wave when `wave_prepare` is called on another |
| 2026-05-01 | Diagnostic aggregates with lint/garden rather than short-circuiting                               | Matches existing aggregation behavior at `server.py:3353-3354`; operators see full picture in one response              | Short-circuit on guard failure before running lint/garden             |
| 2026-05-01 | `wave_pause` transitions status from `active` to `paused` (new lifecycle state)                    | Without the transition, the guard's recovery recommendation doesn't actually clear "another wave is active"             | Keep pause handoff-only; require manual wave.md edit (error-prone)    |
| 2026-05-01 | Resume modeled as re-running `wave_prepare` on the paused wave, not a new `wave_resume` tool       | Minimal surface-area addition; `wave_prepare` already handles status writes and lint/garden; one tool owns state transitions to `active` | Dedicated `wave_resume` tool                             |
| 2026-05-01 | `paused` added to status vocabulary; `current_wave` unchanged (already filters to active/planned) | Natural filter: adding a new terminal-ish state doesn't require touching the selector                                   | Extend `current_wave` to explicitly exclude paused                    |
| 2026-05-01 | Resume (`wave_prepare` on a paused wave) still enforces the single-active-wave guard               | Resuming while another wave is active would recreate the split-state problem that motivated the guard                   | Allow resume to bypass the guard                                      |
| 2026-05-01 | `wave_current` returns `data.waves[]` (hard break, no transitional dual-emit)                      | Transitional dual-emit would bake the old contract into seeds/prompts/tests; one-shot migration keeps the contract clean | Transitional `data.wave` alongside `data.waves` for one release       |
| 2026-05-01 | Ordering: active (0/1) → planned → paused → other                                                  | Active-first matches existing "what should I do next?" operator flow; paused after planned keeps the reader focused on in-flight work | Alphabetical by wave_id; paused before planned                 |
| 2026-05-01 | `resume_wave` is a next-action hint, not a new MCP tool                                            | Keeps the surface-area minimal; `wave_prepare` already owns all `→ active` transitions; operators can add a `wave_resume` tool later if the alias becomes valuable | Ship a `wave_resume` tool now                          |
| 2026-05-01 | Non-closed includes any status other than `closed` (future-proof for `stub`/`ready`/unknown)       | Conservative inclusion; a future status unknown today is almost certainly in-flight if it isn't closed                   | Enum-restrict to active/planned/paused only                           |


## Risks


| Risk                                                                                        | Mitigation                                                                             |
| ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Guard fires during legitimate transient state (active → paused mid-flight)                  | Guard runs at `wave_prepare` only; pause itself is a single atomic status write; tests cover post-pause prepare |
| Self-prepare incorrectly triggers guard                                                     | AC-3 and AC-11 tests cover self-prepare from `active` and from `paused`; helper compares wave paths, not just statuses |
| Dry-run change surprises existing callers                                                   | Dry-run already returns diagnostics for other failure modes (lint, missing sections); adding another is consistent |
| Seed update lands in the wrong file                                                         | Implementation locates the correct seed via grep for `wave_prepare` / `wave_pause` guidance; documents the choice in the change's Progress Log |
| Message wording implies the operator must pause rather than choose                          | Message explicitly says "Pause it before preparing '<target>'" — recovery_tools list shows the option, does not force it |
| Existing `wave_pause` tests assert status stays `active`; transition change breaks them      | Tasks list requires auditing and updating those tests; the change is a deliberate semantics update, not a silent regression |
| `paused` status confuses tooling that only knew `active`/`planned`/`closed`                 | AC-12 and AC-13 tests confirm `wave_current` skips paused and lint accepts it; grep for status consumers at implementation and update them or explicitly decide they stay unchanged |
| Resume path skips re-validation                                                             | Resume is `wave_prepare`, which already runs lint/garden/admitted-change checks — no separate code path |
| Paused wave accumulates handoff entries across repeated pauses                              | `_merge_pause_into_session_handoff` already handles merge semantics; no new entry type introduced by this change |
| `data.wave` migration misses a caller (external tool, undocumented script)                  | AC-20 grep test catches in-tree stragglers; external callers are out of our control, but the breaking change is called out prominently in the Rationale and Progress Log so downstream consumers see it |
| `data.waves[]` ordering assumption quietly drifts                                           | Ordering spelled out in Requirement 15 with explicit test (AC-18); any change requires a new ADR or change |
| `next_action: "resume_wave"` tempts operators to call a tool that doesn't exist              | Prompt docs and AGENTS.md explicitly map `resume_wave` → `wave_prepare`; seeded guidance mentions the alias status |
| Paused waves pile up and clutter `wave_current`                                             | Response is read-only and every entry is still in-flight; if clutter becomes a problem, add a `max` param later. Out of scope for this change |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
