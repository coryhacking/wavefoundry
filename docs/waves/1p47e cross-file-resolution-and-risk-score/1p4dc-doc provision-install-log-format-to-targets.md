# Provision install-log-format.md to Target Projects

Change ID: `1p4dc-doc provision-install-log-format-to-targets`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p47e cross-file-resolution-and-risk-score

## Rationale

Three install seeds point at `docs/references/install-log-format.md` for the install-log row format and the trustworthy-`[x]`-marker invariant:

- `011-install-wavefoundry-phase-1.prompt.md:11` — "The full row format and trustworthy-invariant rule are in `docs/references/install-log-format.md` **(created during Phase 2 step 2.4 — until then, the rules are inline below)**."
- `010-install-wavefoundry.prompt.md:22, :35, :37` — three more references for the trustworthy invariant / state machine / row format.

But the claim is false: **Phase 2 step 2.4 is "Generate per-role agent docs (seed-050)"** — it does not create `install-log-format.md`. The doc exists in the wavefoundry self-host (`docs/references/install-log-format.md`, 100 lines), but the pack ships only `.wavefoundry/framework/`, and **no seed provisions the doc to target projects**. So in every installed/upgraded target those seed references dangle — the reference doc simply does not exist.

This is the **identical class of gap** that `1p455` fixed for `scan-findings-format.md` (ship the reference doc as a framework template, then provision it via the install/upgrade seeds). It was explicitly flagged as the same latent gap in `1p455`'s decision log. This change applies that proven pattern to `install-log-format.md`.

## Requirements

1. Ship `docs/references/install-log-format.md` as a framework template at `.wavefoundry/framework/docs/references/install-log-format.md` (byte-identical to the self-host copy), so `build_pack` carries it in the pack.
2. Provision it on fresh install: a Phase 2 seed step copies the template to `docs/references/install-log-format.md` if absent (do not author a thin version).
3. Refresh it on upgrade: `seed-160` refreshes `docs/references/install-log-format.md` from the template (it is framework-tracked reference documentation).
4. Correct `seed-011`'s "created during Phase 2 step 2.4" claim to point at the actual provisioning step.
5. Keep `docs-lint` clean and the framework template byte-identical to the live self-host copy.

## Scope

**Problem statement:** `install-log-format.md` is referenced by three install seeds but is never shipped in the pack or provisioned to target projects, so the references dangle in every installed/upgraded repo.

**In scope:**

- A framework template at `.wavefoundry/framework/docs/references/install-log-format.md`.
- A `seed-012` (install Phase 2) provisioning step (mirroring `seed-012` step 2.3a for `scan-findings-format.md`).
- A `seed-160` (upgrade) refresh step (mirroring the `scan-findings-format.md` refresh bullet).
- A `seed-011` reference correction (replace the false "Phase 2 step 2.4" claim).

**Out of scope:**

- Rewriting the *content* of `install-log-format.md` (it is correct; this change only provisions it).
- Changing the install-log format / row schema itself.
- `scan-findings-format.md` provisioning (already done in `1p455`).

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/framework/docs/references/install-log-format.md` exists and is byte-identical to `docs/references/install-log-format.md` (`diff -q` → IDENTICAL), so `build_pack` ships it (not under any excluded path).
- [x] AC-2: `seed-012` Phase 2 (after the step 2.3 docs-structure bootstrap) provisions `docs/references/install-log-format.md` by copying the shipped template if absent.
- [x] AC-3: `seed-160` refreshes `docs/references/install-log-format.md` from the shipped template (sibling to the `scan-findings-format.md` refresh bullet).
- [x] AC-4: `seed-011` no longer claims "created during Phase 2 step 2.4" (grep → 0); it now reads "provisioned during Phase 2 step 2.3 from the shipped framework template" (grep → 1). `seed-010`'s references resolve because the doc is now provisioned.
- [x] AC-5 (regression): `docs-lint` clean; `grep -l` confirms both `seed-012` and `seed-160` reference + provision `install-log-format.md`; the template `diff -q`-matches the live copy.

## Tasks

- [x] Open `framework_edit_allowed` + `seed_edit_allowed`.
- [x] `cp docs/references/install-log-format.md .wavefoundry/framework/docs/references/install-log-format.md` (ship the template).
- [x] `seed-012` (Phase 2): add a provisioning step that copies the template into `docs/references/install-log-format.md` if absent (mirror step 2.3a).
- [x] `seed-160`: add a refresh bullet (mirror the `scan-findings-format.md` refresh).
- [x] `seed-011`: correct the "created during Phase 2 step 2.4" parenthetical to reference the actual provisioning step.
- [x] `wave_validate` / `docs-lint`; confirm `diff -q` template vs live; grep both seeds for `install-log-format.md`.
- [x] Close gates.

## Agent Execution Graph


| Workstream      | Owner       | Depends On       | Notes                                                              |
| --------------- | ----------- | ---------------- | ------------------------------------------------------------------ |
| ship-template   | Engineering | —                | `cp` self-host doc → `.wavefoundry/framework/docs/references/`      |
| wire-seeds      | Engineering | ship-template    | `seed-012` provision + `seed-160` refresh + `seed-011` reference fix |
| verify          | Engineering | wire-seeds       | `docs-lint` + `diff -q` + cross-reference grep (AC-5)              |


## Serialization Points

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` and `012-install-wavefoundry-phase-2.prompt.md` — shared install/upgrade seeds; the provisioning step sits beside the existing `scan-findings-format.md` provisioning, so land them together under `seed_edit_allowed`.
- `.wavefoundry/framework/docs/references/install-log-format.md` — new framework template; land it before the seed steps that reference it.

## Affected Architecture Docs

N/A — ships one existing reference doc as a framework template and adds provisioning pointers to three install/upgrade seeds. No module boundary, control-flow, or verification-architecture change. Directly parallels `1p455` (which provisioned `scan-findings-format.md`).

## AC Priority


| AC   | Priority   | Rationale                                                                          |
| ---- | ---------- | ---------------------------------------------------------------------------------- |
| AC-1 | required   | Shipping the doc as a framework template is the prerequisite — without it the pack can't carry the doc to targets. |
| AC-2 | required   | Install-time provisioning is the core fix: fresh installs must receive the doc the seeds reference. |
| AC-3 | required   | Upgrade-time refresh keeps the doc current and provisions it for already-installed targets. |
| AC-4 | important  | Correcting seed-011's false "Phase 2 step 2.4" claim removes the misleading pointer; the doc resolving matters more than the exact wording. |
| AC-5 | required   | docs-lint + byte-identical template + cross-reference grep is the regression gate proving the provisioning is wired and non-dangling. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-09 | Change opened from the `1p455` follow-on flag: confirmed `install-log-format.md` exists in the self-host (100 lines) but is NOT a framework template and is provisioned by NO seed, while `seed-011:11` + `seed-010:22/35/37` reference it (and `seed-011` falsely claims it's "created during Phase 2 step 2.4"). Fix mirrors the `1p455` scan-findings-format.md provisioning pattern. | `grep install-log-format` across seeds; `ls` confirms no framework template. |
| 2026-06-09 | **Implemented.** Shipped `.wavefoundry/framework/docs/references/install-log-format.md` (byte-identical to the live copy); added the provisioning blockquote to `seed-012` after step 2.3; added the upgrade-refresh bullet to `seed-160` (sibling to scan-findings-format); corrected `seed-011`'s "step 2.4" claim → "provisioned during Phase 2 step 2.3". All 5 ACs verified (diff IDENTICAL; both seeds reference/provision; seed-011 grep 0/1). | `diff -q` IDENTICAL; `grep -l` both seeds; `wave_validate` → `docs-lint: ok`. |


## Decision Log


| Date       | Decision                                                                       | Reason                                                                                                          | Alternatives                                                                                          |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| 2026-06-09 | Mirror the `1p455` pattern: ship as a framework template + seed provisioning.  | Same gap, same proven fix; keeps the two reference docs provisioned identically; the pack ships only `.wavefoundry/framework/`, so a repo-local doc never reaches targets. | Repoint the seeds to other shipped sources (rejected: loses the consolidated install-log reference); leave as self-host-only (rejected: the shipped seeds keep dangling for targets). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The framework template drifts from the live self-host copy. | Provision/refresh from the single shipped template; verify `diff -q` byte-identical at implementation and on self-host upgrades (`seed-160` refresh). |
| Provisioning timing — `install-log-format.md` is referenced from Phase 1 (`seed-011`) but provisioned in Phase 2. | `seed-011` already carries the rules inline "until then"; the corrected reference makes the Phase-2 provisioning explicit, matching the existing `scan-findings-format.md` (also Phase-2-provisioned) model. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
