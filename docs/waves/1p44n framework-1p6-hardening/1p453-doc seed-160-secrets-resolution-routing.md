# Route Secrets-Finding Resolution From Upgrade Docs Gate

Change ID: `1p453-doc seed-160-secrets-resolution-routing`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

A hardcoded-secrets finding hard-aborts the upgrade, but `seed-160` never tells the agent how to resolve it. The secrets scanner is the **first** docs-lint check (`wave_lint_lib/cli.py:87` runs `check_hardcoded_secrets` before all other checks; `cli.py:127-132` returns `1` on any failure), and the upgrade `phase_docs_gate` does `sys.exit(1)` at `upgrade_wavefoundry.py:1150-1151` on any non-zero lint result. So a single secrets finding stops the entire upgrade at the docs gate.

`seed-160` references the scan only for threshold backfill (lines 153-158) and prompt-body regeneration (line 122, pointing at the seed-213 doc file). Across its 453 lines there is **no** "docs gate failed on a secrets finding" resolution subsection: the docs-gate steps (step 11 near line 207, and the operating-memory docs-gate re-run at lines 207-238) never mention secrets. The actual resolution loop lives in `213-security-reviewer.prompt.md:12-55` (the Pre-Scope Step), but it is routed only from the CLOSE path (`190-finalize-feature.prompt.md:73`) and never from `wave_upgrade`.

The lint output itself is not silent — it names `scan-findings.json`, the `pending` status, and "run security reviewer to classify" (`secrets_validators.py:611/617/624/627`), and `wave_upgrade` returns that text (`server_impl.py:6356-6367`). So this is a **discoverability gap** inside seed-160, not a total absence of guidance. The fix is doc-only: give the upgrading agent an explicit pointer to the seed-213 resolution loop, the status transitions, and the requirement to re-run the docs gate after each resolution because the scan re-runs as the first lint check.

## Requirements

1. Add a subsection to `seed-160` titled "Docs gate failed on a secrets finding — resolve first" (exact wording flexible, but it must clearly name the secrets-finding docs-gate-failure case).
2. The subsection must route the agent to the seed-213 Pre-Scope resolution loop (`213-security-reviewer.prompt.md` Pre-Scope Step) as the authoritative procedure for classifying findings.
3. The subsection must name the `scan-findings.json` status transitions: `pending` → `false-positive` / `suspected-secret` / `confirmed-secret`.
4. The subsection must state that the docs gate must be RE-RUN after each resolution, because the secrets scan runs as the **first** lint check and a non-zero result aborts the upgrade.
5. Place the guidance so an agent hitting a docs-gate failure finds it: anchor it at the docs-gate re-run (step 11, near line 207), with a discoverability pointer from the step 0 pre-flight and/or the operating-memory docs-gate re-run.
6. The change is doc/guidance only — no behavioral code change, no new MCP surface.

## Scope

**Problem statement:** When the upgrade docs gate fails on a hardcoded-secrets finding, `seed-160` gives the agent no procedure to resolve it. The resolution loop exists in seed-213 but is only reachable from the close path, so an agent driving an upgrade has no in-seed pointer to it, the status-transition vocabulary, or the re-run requirement.

**In scope:**

- Adding a "Docs gate failed on a secrets finding — resolve first" subsection to `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`.
- Pointer from that subsection to the seed-213 Pre-Scope Step resolution loop.
- Naming the `pending` → `false-positive` / `suspected-secret` / `confirmed-secret` status transitions in seed-160.
- A discoverability cross-reference at the docs-gate re-run (step 11) and at step 0 pre-flight and/or the operating-memory docs-gate re-run (lines 207-238).
- Stating the re-run-after-each-resolution requirement tied to the scan being the first lint check.

**Out of scope:**

- Any change to the secrets scanner, `cli.py`, `secrets_validators.py`, `upgrade_wavefoundry.py`, or `server_impl.py` (code is correct; only seed guidance is missing).
- Changes to `seed-213` itself or to the close-path routing in `seed-190`.
- Auto-running the security reviewer from `wave_upgrade` (behavior change — not this scope).
- Changing classification heuristics or confirmation thresholds.

## Acceptance Criteria

- [ ] AC-1: `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` contains a "Docs gate failed on a secrets finding — resolve first" subsection (or equivalently-titled subsection clearly scoped to the secrets-finding docs-gate failure).
- [ ] AC-2: That subsection explicitly routes the agent to the seed-213 Pre-Scope Step resolution loop (`213-security-reviewer.prompt.md`).
- [ ] AC-3: That subsection names the status transitions `pending` → `false-positive` / `suspected-secret` / `confirmed-secret`.
- [ ] AC-4: That subsection states the docs gate must be re-run after each resolution, with the reason that the secrets scan runs as the first lint check and any non-zero result aborts the upgrade.
- [ ] AC-5: A discoverability cross-reference to the new subsection appears at the docs-gate re-run (step 11, near line 207) and at step 0 pre-flight and/or the operating-memory docs-gate re-run (lines 207-238).
- [ ] AC-6 (regression / verification): `.wavefoundry/bin/docs-lint` (or MCP `wave_validate`) reports clean over the edited seed and any touched docs; the secrets scanner itself does not flag the new prose (no provider-prefixed example credentials).

## Tasks

- [ ] Open `seed_edit_allowed` gate (`wave_gate_open(gate="seed_edit_allowed")`; CLI fallback `.wavefoundry/bin/wave-gate open seed_edit_allowed`).
- [ ] Re-read `seed-160` docs-gate steps (step 11 near line 207; operating-memory docs-gate re-run lines 207-238) and step 0 pre-flight to confirm anchor points.
- [ ] Re-read `213-security-reviewer.prompt.md:12-55` to mirror the exact status-transition vocabulary.
- [ ] Author the "Docs gate failed on a secrets finding — resolve first" subsection in `seed-160` with: seed-213 pointer, the three status transitions, and the re-run-after-each-resolution note tied to the scan being the first lint check.
- [ ] Add the discoverability cross-references at step 11 and at step 0 pre-flight and/or the operating-memory docs-gate re-run.
- [ ] Run the docs gate (`wave_validate` over MCP, or `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`) and fix any failures.
- [ ] Close `seed_edit_allowed` gate (`wave_gate_close(gate="seed_edit_allowed")`).

## Agent Execution Graph


| Workstream            | Owner       | Depends On | Notes                                                                                  |
| --------------------- | ----------- | ---------- | -------------------------------------------------------------------------------------- |
| seed-160-subsection   | Engineering | —          | Author the resolution subsection; requires `seed_edit_allowed`. Shared file with 1p450/1p455. |
| seed-160-crossrefs    | Engineering | seed-160-subsection | Add discoverability pointers at step 11 and step 0 / operating-memory docs-gate re-run. |
| docs-gate-verify      | Engineering | seed-160-crossrefs  | Run `wave_validate` / `docs-lint`; confirm clean and scanner does not flag new prose.   |


## Serialization Points

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` — shared with the 1p450 and 1p455 seed edits; requires `seed_edit_allowed` and coordination so concurrent seed-160 edits do not conflict.

## Affected Architecture Docs

N/A — doc/guidance-only change to a single framework seed prompt; no module boundary, control/data-flow, or verification-architecture impact.

## AC Priority


| AC   | Priority   | Rationale                                                                                           |
| ---- | ---------- | -------------------------------------------------------------------------------------------------- |
| AC-1 | required   | The resolution subsection is the core deliverable; without it the discoverability gap remains.     |
| AC-2 | required   | Routing to seed-213 is the whole point — the resolution loop already exists there.                 |
| AC-3 | required   | The status-transition vocabulary is what lets the agent act on the lint output.                    |
| AC-4 | required   | Re-run-after-resolution is essential correctness; the scan is the first check and re-runs each gate.|
| AC-5 | important  | Cross-references make the subsection discoverable from where the agent actually hits the failure.   |
| AC-6 | required   | Docs-lint clean is the gate for any docs change; also guards the new prose against self-flagging.   |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date       | Decision                                                                                   | Reason                                                                                                            | Alternatives                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 2026-06-08 | Fix as doc-only routing in seed-160; point at the existing seed-213 Pre-Scope loop.        | The resolution loop and lint guidance already exist; the only gap is discoverability inside the upgrade seed.    | Auto-run the security reviewer from `wave_upgrade` (behavior change, out of scope); duplicate the loop into seed-160 (drift risk). |
| 2026-06-08 | Anchor at the step 11 docs-gate re-run with a pointer from step 0 pre-flight / lines 207-238. | That is where an agent actually encounters the docs-gate failure, maximizing the chance it finds the guidance.  | Single mention buried in step 0 only (agent hits the failure at the gate, not pre-flight).        |


## Risks


| Risk                                                                                  | Mitigation                                                                                              |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| New prose includes an example credential string and trips the secrets scanner itself. | Use redacted/placeholder phrasing only; no provider-prefixed sample values; verify with docs-lint (AC-6). |
| Status-transition wording drifts from seed-213, confusing agents.                     | Mirror the exact `pending` → `false-positive` / `suspected-secret` / `confirmed-secret` vocabulary from seed-213 and point to it as authoritative. |
| Concurrent seed-160 edits (1p450/1p455) conflict.                                     | Coordinate via `seed_edit_allowed` gate and the serialization point before parallel work proceeds.     |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
