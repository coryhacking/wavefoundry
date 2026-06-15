# Refresh the operator upgrade docs to match the shipped 1.6 flow

Change ID: `1p5dm-doc upgrade-operator-docs-1-6-refresh`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p5dk 1-6-release-hardening`

## Rationale

The operator-facing upgrade instructions describe a **pre-1.6 multi-step manual flow** while the code implements a single end-to-end flow. Concretely, `docs/prompts/upgrade-wavefoundry.prompt.md`:

- tells the operator to run a **separate** `wave_index_build(content="docs", mode="update")` after the upgrade (step 4 + verification step 6), but 1.6 **always runs the index update in-process as Phase 4** (`upgrade_wavefoundry.py:1931-1941`);
- frames a **hard MCP host restart** as mandatory (steps 3, 6), but 1.6 reloads **in-process** via `wave_mcp_reload` after cleanup (`server_impl.py:6795-6809`);
- says **nothing** about the secrets gate or `--resume-after-gate` — yet a secrets finding can fail the upgrade docs gate, and recovery is via the retained-lock resume path;
- states **no upgrade floor** and no multi-version-skip guidance;
- never warns that 1.6 forces a **graph re-extract + full index rebuild** (only conditionally mentions `CHUNKER_VERSION`).

`docs/references/dashboard-install-upgrade.md:76` also still describes the upgrade as a manual `unzip -o`, contradicting the auto-extract built into the flow. "Last verified" dates predate the 1.6 hardening waves (1p44n/1p44r). An operator following these docs today will run removed steps and be blindsided by the secrets gate and the rebuild cost.

## Requirements

1. Rewrite the upgrade prompt so the index update is **automatic** (Phase 4); demote the manual `wave_index_build` call to a recovery-only note.
2. Change the MCP step from "restart the host" to **`wave_mcp_reload()`** (or `wave_upgrade` cleanup, which reloads automatically), keeping a host restart only as a fallback for hosts that can't hot-reload.
3. Add a **"Secrets scan & resume"** section describing the *real* mechanism: the Phase-4 index build runs a **full-tree** secrets scan up front (it auto-escalates to full when `docs/scan-findings.json` is absent — as on a 1.5→1.6 upgrade — or on a rules-hash / scanner-version change), classifying findings into `docs/scan-findings.json`; the **docs gate (Phase 3) is incremental** and is what can *block the upgrade* on a changed-file `pending`/`suspected-secret` finding; unresolved full-tree findings in untouched files then block the next `wave_close`. Recovery from a blocked docs gate: resolve `scan-findings.json` via the security reviewer (seed-213), then resume non-destructively with `--resume-after-gate` (or `wave_upgrade(phase="resume_after_gate")`).
4. State the supported **upgrade floor** and whether multi-version skips (e.g. 1.4.x → 1.6) are supported in a single run — matching the actual code behavior delivered/confirmed by `1p5do`.
5. Add a **version-transition expectation** note: 1.6 forces a graph re-extract and a full index rebuild, so the first post-upgrade build is substantial (cross-link the existing time estimate).
6. Fix `dashboard-install-upgrade.md` to describe automatic zip adoption, not manual `unzip -o`; add the agent-body secrets/resume contract item to `agents/upgrade-wave-context.prompt.md`; bump "Last verified".

## Scope

**Problem statement:** operator upgrade instructions describe a flow that no longer exists and omit the 1.6 secrets gate, resume path, floor, and forced-rebuild cost.

**In scope:**

- **`.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` (SEED — edit FIRST; this is what propagates to downstream projects on upgrade).** Mental-model steps 3–4 (in-process reload, auto index, forced-rebuild note), `--resume-after-gate` in the secrets-resolution loop, the 1.4.0 warn-floor + skip note. The seed already carried the secrets baseline + resolution loop (and the MCP-subprocess-full-scan nuance), so those needed no change.
- `docs/prompts/upgrade-wavefoundry.prompt.md` (self-host rendered copy: steps 3–4, verification checklist, new secrets/resume + floor + version-transition sections).
- `docs/prompts/agents/upgrade-wave-context.prompt.md` (self-host agent body — not seeded; add secrets/resume contract item).
- `docs/references/dashboard-install-upgrade.md` (self-host reference — not seeded; replace the manual `unzip -o` description).

**Out of scope:**

- The CHANGELOG (`1p5dl`) and any code (`1p5do`). This change documents the flow as it will be after `1p5do` lands — coordinate the floor wording with it.
- `release-flow.md` / `install-assets.md` (verified accurate; not upgrade-operator docs).

## Acceptance Criteria

- [x] AC-1: steps 3–4 + verification step 6 now describe auto Phase-4 index update and in-process `wave_mcp_reload`, with the manual `wave_index_build`/host-restart demoted to the post-editing-pass / hosts-that-can't-hot-reload case.
- [x] AC-2: a "Secrets scan and resume" section documents the Phase-4 full-tree baseline (records), the incremental docs gate (blocks), the `scan-findings.json` + seed-213 resolution loop, `--resume-after-gate`, and the next-`wave_close` block on untouched-file findings.
- [x] AC-3: a "Supported version range" section states the 1.4.0 warn-floor and that multi-version skips are allowed (only downgrades blocked) — consistent with `1p5do`.
- [x] AC-4: steps 4 (How Framework Updates Work + Verification) note that 1.6 bumps both `CHUNKER_VERSION` and `GRAPH_BUILDER_VERSION` → first post-upgrade index is a full re-chunk + re-embed + graph re-extract.
- [x] AC-5: `dashboard-install-upgrade.md` now describes automatic zip adoption (no manual `unzip -o`); `upgrade-wave-context.prompt.md` carries the secrets/resume contract item; "Last verified" dates bumped on both prompts; docs-lint clean.

## Tasks

- [x] Rewrite prompt steps 3–4 + verification checklist; add "Secrets scan and resume" + "Supported version range" sections; add the version-transition forced-rebuild note.
- [x] Fix `dashboard-install-upgrade.md` unzip description; add agent-context secrets/resume contract item; bump dates.
- [x] docs-lint clean; instructions re-verified against `upgrade_wavefoundry.py` (auto Phase-4 index, in-process reload, secrets gate, `--resume-after-gate`, 1.4.0 floor).

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- Wording of the floor/skip section depends on the behavior `1p5do` lands — author after (or in lockstep with) `1p5do` so the docs match the code.

## Affected Architecture Docs

`N/A` — operator/prompt documentation; no architecture change. (Cross-references the upgrade flow but does not alter it.)

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Operators following stale steps run removed/wrong commands. |
| AC-2 | required  | The secrets gate can block an upgrade with no documented recovery today. |
| AC-3 | important | Floor/skip guidance prevents silent partial migrations; must match `1p5do`. |
| AC-4 | important | The forced-rebuild cost is a surprise without a warning. |
| AC-5 | important | The manual-unzip description and agent-contract gap are smaller but real staleness. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-13 | Rewrote `upgrade-wavefoundry.prompt.md`: steps 3–4 (in-process `wave_mcp_reload`, auto Phase-4 index, forced-rebuild note) + verification step 4/6; added "Secrets scan and resume" and "Supported version range" (1.4.0 warn-floor, skips allowed) sections. Fixed `dashboard-install-upgrade.md` manual-`unzip` description; added the secrets/resume contract item to `upgrade-wave-context.prompt.md`; bumped both "Last verified" dates. docs-lint clean. | `upgrade-wavefoundry.prompt.md`, `dashboard-install-upgrade.md`, `upgrade-wave-context.prompt.md` |
| 2026-06-14 | **Seed-first correction (operator-flagged):** the rendered copies were edited but `seeds/160-upgrade-wavefoundry.prompt.md` (what downstream projects get) was still stale — caught at package time. Updated the seed: mental-model steps 3–4 (in-process reload, auto index, 1.6 forced rebuild), added `--resume-after-gate` to the secrets-resolution loop, and the 1.4.0 warn-floor + skip note in the version guard. Seed already carried the secrets baseline + resolution loop. Full suite **3116 OK**; docs-lint clean. | `seeds/160-upgrade-wavefoundry.prompt.md` |
| 2026-06-14 | **`~/Downloads/` 5th search path — doc enumerations (paired with the 1p5do code change):** updated every "four search paths/locations" claim to five + `~/Downloads/` across the seed (placement prose, exhaustive lists, `--list-zips` count) and the rendered prompt (Distribution directories, Agent-safe zip discovery, step-1/step-0 placement). docs-lint clean. | `seeds/160-upgrade-wavefoundry.prompt.md`, `upgrade-wavefoundry.prompt.md` |
| 2026-06-14 | **Agent zip-discovery hardening (operator-flagged):** downstream agents kept running `ls wavefoundry-*.zip` at the repo root, finding nothing (the pack lives in `~/.wavefoundry/dist/`), and wrongly concluding "nothing to upgrade." Elevated the "never `ls`, use `--detect-zip` / `--list-zips`" guidance to a prominent hard rule with the "empty repo-root `ls` ≠ no pack; pack lives in dist/" clarification — in the seed (mental model) and the rendered prompt (step 1 + Agent-safe zip discovery). docs-lint clean. | `seeds/160-upgrade-wavefoundry.prompt.md`, `upgrade-wavefoundry.prompt.md` |
| 2026-06-14 | **`wave_upgrade(mode='dry_run')` doc error fixed (downstream solaris/p5ku-flagged):** the discovery/preview guidance referenced a nonexistent MCP call — `wave_upgrade` takes only `phase=` (preflight_to_docs_gate/update_index/rebuild_index/cleanup/resume_after_gate); there is no `mode=` and no dry-run/discovery phase. Was a pre-existing error propagated into the new hard rule. Corrected all 5 occurrences (seed ×3, prompt ×2) to point discovery/preview at the CLI-only `--detect-zip` / `--list-zips` / `--dry-run`, and added the explicit "MCP `wave_upgrade` runs the upgrade, has no dry-run phase" clarification. The already-shipped p5ku pack carries the old wording — fixed in-tree for the next repackage. docs-lint clean. | `seeds/160-upgrade-wavefoundry.prompt.md`, `upgrade-wavefoundry.prompt.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Docs describe floor/skip behavior `1p5do` hasn't finalized | Serialize: author the floor section after `1p5do` lands its behavior |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
