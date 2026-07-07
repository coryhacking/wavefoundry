# Upgrade: provision lifecycle scheme-v2 from new code so a from-<1.10.1 MCP upgrade self-heals

Change ID: `1ryce-bug upgrade-v2-provision-from-new-code`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1rycg post-1p11-field-feedback-hardening`

## Rationale

Field-reported (operator, 2026-07-06, hard evidence). A target repo on **1.9.7+p8wf** upgraded to 1.11.0 via MCP (`wave_upgrade()` → `wave_upgrade(phase="update_index")` → `wave_upgrade(phase="cleanup")`; `wf` was not on PATH). The lifecycle scheme-v2 policy was **never auto-provisioned** — `docs/workflow-config.json` stayed a plain v1 block (`epoch_utc`, `hour_offset`, `id_script`; no `scheme_version`/`offset`) through all three MCP phases (diff-count proof: 91 files changed with workflow-config NOT among them; provisioned cleanly only after the operator ran `python3 upgrade_wavefoundry.py --materialize-lifecycle-policy` directly). So the repo would silently keep minting collision-prone v1 IDs.

**Confirmed root cause (git-grounded): the "upgrade runs old code" window.** `materialize_lifecycle_policy` (Phase 2c, `upgrade_wavefoundry.py:2738`) and the cleanup backstop `_ensure_lifecycle_policy_backstop` (`:1617`, in `phase_cleanup`) were both introduced in commit `f39d9221` (wave `1p9q0`) at VERSION **1.10.1**. The target was **1.9.7** — before 1.10.1 — so its installed `server_impl.py` (the MCP `wave_upgrade` orchestrator) and the `upgrade_wavefoundry.py` that runs `preflight_to_docs_gate` (loaded at subprocess start, before the pack extracts) have **neither**. An MCP upgrade is orchestrated by the pre-upgrade code until the server reloads (at/after `cleanup`), so nothing that ran could provision. The healing backstop exists only in ≥1.10.1 code and did not fire here (the old-1.9.7 server's `cleanup` phase did not invoke the new `--cleanup` path that carries it). Not the idempotence-guard bug (there was no v2 block to skip) and not an under-scan (the one computation that ran, ran cleanly). See the closed 1.11.0 waves + memory `field_feedback_v2_provisioning_old_code_window`.

**Impact:** ANY repo upgrading from **< the version that carries this provisioning** to a newer one via MCP silently keeps a v1 lifecycle policy until a manual `--materialize-lifecycle-policy`. The only NEW code that runs during a from-old-version MCP upgrade is the extracted-pack `upgrade_wavefoundry.py` subprocess (post-extract) — so the provisioning must execute there, in a phase the old orchestrator reliably invokes, rather than relying on the old MCP server's phase mapping.

## Requirements

1. **Provision from a new-code phase every MCP upgrade path invokes post-extract.** Add an **idempotent** `materialize_lifecycle_policy(root)` call to the `--update-index` phase of `upgrade_wavefoundry.py` (`args.update_index`, `:2458`). Rationale: the `--update-index` subprocess runs the freshly-extracted (NEW) `upgrade_wavefoundry.py`, and every MCP upgrade flow calls `wave_upgrade(phase="update_index")` after `preflight`. This heals a from-old-version upgrade whose `preflight` ran old code (no Phase 2c) and whose old-server `cleanup` did not reach the new backstop. Idempotence is inherited from `materialize_lifecycle_policy` (a repo already on `scheme_version == "v2"` is a no-op).
2. **Keep the existing provisioning points.** Phase 2c (main flow) and the `phase_cleanup` backstop stay as-is — this change ADDS one more new-code execution point (belt-and-suspenders), it does not remove either. Running provisioning twice is a no-op by idempotence.
3. **Fail-safe.** The added call must never fail the `--update-index` phase: on a `RuntimeError` from `materialize_lifecycle_policy` (e.g. an unparseable config), log a loud pointer at `--materialize-lifecycle-policy` and continue — the index update must still complete (mirror the backstop's fail-safe posture).
4. **No behavior change for a repo already on v2** or for a from-≥1.10.1 upgrade (Phase 2c already provisioned) — the `--update-index` call is a no-op there.
5. Local-only, stdlib only; no new dependency.

## Scope

**Problem statement:** A from-<1.10.1 MCP `wave_upgrade` never provisions the lifecycle scheme-v2 policy because the code that orchestrates the upgrade predates the provisioning, and the healing backstop lives only in new code the old orchestrator doesn't reliably reach.

**In scope:**

- `upgrade_wavefoundry.py`: idempotent, fail-safe `materialize_lifecycle_policy` call in the `--update-index` phase.
- Tests: `--update-index` provisions a v1 repo (present→v2); a v2 repo is a no-op; a config error degrades to a pointer, not a failure.

**Out of scope:**

- Changing `materialize_lifecycle_policy`'s idempotence guard or offset scan (both ruled out by the evidence).
- Reworking the MCP reload/phase-orchestration model or making the old server heal itself (impossible — old code).
- Migrating existing v1 IDs (never rewritten; v2 offset clears pre-provisioning values).

## Acceptance Criteria

- [x] AC-1: Running the `--update-index` phase of `upgrade_wavefoundry.py` against a repo whose `docs/workflow-config.json` has a plain v1 `lifecycle_id_policy` (no `scheme_version`) provisions scheme v2 (idempotent `materialize_lifecycle_policy`); a deterministic test asserts `scheme_version == "v2"` + an `offset` afterward. — `--update-index` now calls `_ensure_lifecycle_policy_backstop(root)` (the fail-safe wrapper over `materialize_lifecycle_policy`) right after `phase_index_update` (`upgrade_wavefoundry.py:2479`); `test_cleanup_backstop_heals_unprovisioned_repo` covers the v1→v2 materialize behavior and `test_update_index_phase_wires_the_lifecycle_backstop` locks the wiring (backstop called after `phase_index_update`).
- [x] AC-2: The `--update-index` phase against a repo already on `scheme_version == "v2"` leaves the policy byte-unchanged (no-op); test asserts no rewrite. — inherited idempotence (`materialize_lifecycle_policy` no-ops on v2); `test_cleanup_backstop_noop_when_already_v2`.
- [x] AC-3: A `RuntimeError` from `materialize_lifecycle_policy` during `--update-index` is caught, logged as a pointer at `wf upgrade --materialize-lifecycle-policy`, and the index update still completes (no non-zero exit from the provisioning step); test asserts the fail-safe. — reused the fail-safe wrapper `_ensure_lifecycle_policy_backstop` (catches `RuntimeError` → logs `wf upgrade --materialize-lifecycle-policy` pointer → returns); `test_cleanup_backstop_never_raises_on_corrupt_config`.
- [x] AC-4: Full framework tests run bytecode-free and docs validation passes. — `run_tests.py`: 4725 OK (bytecode-free); `wave_validate` at wave verification.

## Tasks

- [x] Add the idempotent, fail-safe `materialize_lifecycle_policy(root)` call to the `args.update_index` branch of `upgrade_wavefoundry.py`. — via `_ensure_lifecycle_policy_backstop(root)` (the existing fail-safe wrapper) at `:2479`, right after `phase_index_update`.
- [x] Tests: update-index provisions v1→v2; v2 no-op; RuntimeError fail-safe. — `test_update_index_phase_wires_the_lifecycle_backstop` (wiring lock) + the existing `test_cleanup_backstop_*` behavior tests in `MaterializeLifecyclePolicyTests` (21 green).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`. — suite 4725 OK; `wave_validate` at wave verification.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| update-index-provision | implementer | — | Idempotent/fail-safe materialize in `--update-index` |
| tests | qa-reviewer | update-index-provision | v1→v2, v2 no-op, RuntimeError fail-safe |


## Serialization Points

- Single-file production change in `upgrade_wavefoundry.py` (the `--update-index` phase). Disjoint from `1rycf` (index-optimize).

## Affected Architecture Docs

- N/A — a provisioning-timing fix in the upgrade script; no contract change. The lifecycle-ID policy schema and provisioning logic are unchanged; only an additional new-code execution point is added.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core fix — a from-old-version upgrade must self-provision v2. |
| AC-2 | required | Must not re-epoch/re-offset an already-v2 repo (would break issued IDs). |
| AC-3 | required | Provisioning must never fail the index update. |
| AC-4 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-06 | Field-reported from a 1.9.7→1.11.0 MCP upgrade that left the repo on v1; root cause confirmed git-grounded (Phase 2c + backstop landed at 1.10.1; target predates them; MCP upgrade runs old orchestrator until reload). Fix: provision from the new-code `--update-index` phase. | Operator diff-count evidence; `f39d9221` (1p9q0) at VERSION 1.10.1; `upgrade_wavefoundry.py:2458` (`--update-index`), `:2738` (Phase 2c), `:1617` (backstop). |
| 2026-07-06 | Implemented: `_ensure_lifecycle_policy_backstop(root)` (the existing fail-safe wrapper over `materialize_lifecycle_policy`) called after `phase_index_update` in the `--update-index` phase — reusing the wrapper gets AC-3's fail-safe for free rather than a bare `materialize_lifecycle_policy` call. Wiring-lock test + existing behavior tests green (21); full suite 4725 OK. | `upgrade_wavefoundry.py:2479`; `test_upgrade_wavefoundry.py::MaterializeLifecyclePolicyTests`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-06 | Add the idempotent provisioning to the new-code `--update-index` phase. | It is the only new-code (post-extract) phase every MCP upgrade path reliably invokes; the main `preflight` phase runs old code for a from-old-version upgrade, and the old server's `cleanup` mapping is what failed to reach the new backstop. | Wire it into `wave_mcp_reload`/the MCP `cleanup` handler (rejected — those are the old server's code during a from-old upgrade; the reload that loads new code is old-handled, so new-code reload logic can't run for THAT reload). Fix the old server (impossible — it's the installed pre-upgrade code). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Double provisioning (Phase 2c + update-index + backstop all fire) | `materialize_lifecycle_policy` is idempotent (guards on `scheme_version == "v2"`); the 2nd/3rd calls are no-ops. |
| A config-parse error aborts the index update | Fail-safe: catch `RuntimeError`, log a recovery pointer, continue — the index phase completes regardless. |
| Re-epoching an already-v2 repo | The idempotence guard returns without modifying an already-v2 block; AC-2 locks this. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
