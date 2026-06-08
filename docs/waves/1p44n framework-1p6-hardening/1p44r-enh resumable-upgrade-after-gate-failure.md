# Resumable Upgrade After Docs-Gate Failure

Change ID: `1p44r-enh resumable-upgrade-after-gate-failure`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

When a Wavefoundry framework upgrade fails at the docs gate, the only retry path
re-extracts the pack unconditionally. The zip-application block in
`upgrade_wavefoundry.py:1538-1543` extracts the zip with no guard checking
whether the on-disk tree already matches `to_version`, so re-running
`preflight_to_docs_gate` repeats the full extract / surface-render / prune
sequence even though the tree is already at the target version. The downgrade
guard at `upgrade_wavefoundry.py:986-993` only blocks *lower* versions and is
effectively disabled because `from_version` is `None` (per 1p44p), so it offers
no protection against a redundant same-version re-extract.

On the MCP side, `wave_upgrade` exposes only
`('preflight_to_docs_gate','update_index','rebuild_index','cleanup')` as
`valid_phases` (`server_impl.py:6301-6307`), with the phase→flag mapping at
`server_impl.py:6331-6338` and the tool docstring/registration at
`server_impl.py:15539-15561`. There is no phase that re-runs *only* the docs
gate against the already-extracted tree. Combined with the retained lock from
1p44o (which preserves the `failed_phase` marker across the failure), we can make
upgrade recoverable: re-run docs-gardener + docs-lint without a destructive full
re-extract.

## Requirements

1. Add a new upgrade phase (`resume_after_gate`) that re-runs ONLY the
   docs-gardener and docs-lint steps against the already-extracted tree — no
   extract, no surface rendering, no pruning.
2. The resume phase MUST read the `failed_phase` marker from the retained
   upgrade lock (introduced by 1p44o) to confirm the prior run failed at the
   docs gate before resuming.
3. Make extract idempotent: skip the zip-application block when the on-disk
   `framework/VERSION` already equals `to_version`, so re-running
   `preflight_to_docs_gate` does not re-extract a tree already at target.
4. Wire the new phase into the MCP surface: add it to `valid_phases`, add the
   phase→flag mapping, update the `wave_upgrade` docstring, and keep the
   registered tool signature consistent.
5. The resume phase MUST exit non-zero when the docs gate fails again and zero
   when the gate passes, matching the existing gate exit-code semantics.
6. Update `docs/specs/mcp-tool-surface.md` to document the new `wave_upgrade`
   phase.

## Scope

**Problem statement:** A docs-gate failure during a framework upgrade can only
be retried by re-running `preflight_to_docs_gate`, which re-extracts the pack
unconditionally and re-renders/prunes surfaces, even when the tree already
matches `to_version`. There is no MCP phase to re-run just the gate, and no
idempotence guard on extract, making recovery destructive and slow.

**In scope:**

- A `resume_after_gate` phase in `upgrade_wavefoundry.py` that re-runs only
  docs-gardener + docs-lint against the extracted tree.
- An idempotence guard on the zip-application block keyed on the on-disk
  `framework/VERSION` equalling `to_version`.
- Reading the `failed_phase` marker from the retained lock (depends on 1p44o).
- MCP wiring in `server_impl.py`: `valid_phases`, phase→flag mapping, docstring,
  registered tool.
- Unit tests for the new phase and the extract-idempotence guard, plus an MCP
  wrapper-layer test for the new phase.
- Documenting the phase in `docs/specs/mcp-tool-surface.md`.

**Out of scope:**

- Re-enabling or changing the downgrade guard (`upgrade_wavefoundry.py:986-993`)
  — owned by 1p44p.
- The lock-retention mechanism itself — owned by 1p44o (this change consumes it).
- Index update/rebuild phase behavior (`update_index`, `rebuild_index`).
- Any change to docs-gardener or docs-lint internals beyond invoking them.

## Acceptance Criteria

- [ ] AC-1: A new `resume_after_gate` phase re-runs docs-gardener + docs-lint
  against the already-extracted tree and performs NO extract, surface render, or
  prune.
- [ ] AC-2: The zip-application block in `upgrade_wavefoundry.py` is skipped
  (idempotent) when on-disk `framework/VERSION` already equals `to_version`; a
  re-run of `preflight_to_docs_gate` on an at-target tree does not re-extract.
- [ ] AC-3: The resume phase reads the `failed_phase` marker from the retained
  upgrade lock and only proceeds when the prior failure was the docs gate.
- [ ] AC-4: `resume_after_gate` is present in `valid_phases`, mapped to the
  correct CLI flag, and documented in the `wave_upgrade` docstring; the MCP tool
  rejects unknown phases as before.
- [ ] AC-5: The resume phase exits non-zero on a repeated gate failure and zero
  when the gate passes, matching existing gate exit-code semantics.
- [ ] AC-6 (regression/unit): Unit tests cover (a) the resume phase running the
  gate without re-extracting, (b) extract idempotence when the tree already
  equals `to_version`, and (c) reading `failed_phase` from the lock.
- [ ] AC-7 (MCP wrapper-layer): An MCP wrapper-layer test exercises
  `wave_upgrade(phase="resume_after_gate")`, asserting phase validation and the
  correct flag mapping into the upgrade command.
- [ ] AC-8: `docs/specs/mcp-tool-surface.md` documents the new `wave_upgrade`
  phase.

## Tasks

- [ ] Add an extract-idempotence guard around the zip-application block
  (`upgrade_wavefoundry.py:1538-1543`): skip extract when on-disk
  `framework/VERSION` already equals `to_version`.
- [ ] Implement the `resume_after_gate` code path in `upgrade_wavefoundry.py`
  that runs only docs-gardener + docs-lint (no extract/surface/prune).
- [ ] Read the `failed_phase` marker from the retained lock (1p44o) and gate the
  resume on it being the docs gate.
- [ ] Add a CLI flag (e.g. `--resume-after-gate`) and wire it to the new path.
- [ ] Add `resume_after_gate` to `valid_phases` (`server_impl.py:6301`) and the
  phase→flag mapping (`server_impl.py:6331-6338`).
- [ ] Update the `wave_upgrade` docstring (`server_impl.py:15539-15561`) to
  describe the new phase and its place in the resume sequence.
- [ ] Add unit tests for the resume phase, extract idempotence, and lock-marker
  read.
- [ ] Add an MCP wrapper-layer test for `phase="resume_after_gate"`.
- [ ] Update `docs/specs/mcp-tool-surface.md` with the new phase.

## Agent Execution Graph


| Workstream            | Owner       | Depends On            | Notes |
| --------------------- | ----------- | --------------------- | ----- |
| extract-idempotence   | Engineering | 1p44o (lock retain)   | Guard zip-apply on VERSION == to_version |
| resume-phase-core     | Engineering | extract-idempotence   | docs-gardener + docs-lint only; reads failed_phase |
| mcp-wiring            | Engineering | resume-phase-core     | valid_phases, flag map, docstring; coordinate with 1p44z |
| tests-and-docs        | Engineering | mcp-wiring            | unit + MCP wrapper tests; mcp-tool-surface.md |


## Serialization Points

- `upgrade_wavefoundry.py` — both the extract-idempotence guard and the resume
  phase edit this file; serialize the two workstreams.
- `server_impl.py` — MCP phase registration (`valid_phases`, flag mapping,
  docstring) is shared with 1p44z; coordinate edits to avoid conflicting
  changes to the `wave_upgrade` surface.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` — the `wave_upgrade` phase surface gains a new
`resume_after_gate` phase and must document it. No other architecture boundary,
flow, or layering doc is affected; the change is confined to the upgrade script
and its MCP wrapper.

## AC Priority


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Core behavior: gate re-run without re-extract is the whole point of the change. |
| AC-2 | required   | Extract idempotence is what makes resume non-destructive and safe to re-run. |
| AC-3 | required   | Reading failed_phase from the lock is the resume trigger contract (depends on 1p44o). |
| AC-4 | required   | Without MCP wiring the phase is unreachable from the agent surface. |
| AC-5 | important  | Correct exit-code semantics let callers detect repeated gate failure. |
| AC-6 | required   | Regression/unit coverage protects the resume + idempotence logic. |
| AC-7 | required   | MCP wrapper-layer test is mandatory for new MCP surface. |
| AC-8 | important  | Spec doc keeps the tool surface discoverable and accurate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-08 | Add a dedicated `resume_after_gate` phase that runs only docs-gardener + docs-lint rather than re-running `preflight_to_docs_gate`. | The existing retry re-extracts unconditionally (`upgrade_wavefoundry.py:1538-1543`); a narrow resume phase avoids the destructive surface render/prune and is fast. | Make `preflight_to_docs_gate` itself skip already-done sub-steps (more invasive, broader blast radius); document a manual unzip+run-phases workaround (poor UX, error-prone). |
| 2026-06-08 | Gate extract on on-disk `framework/VERSION` == `to_version` for idempotence, and read `failed_phase` from the retained lock (1p44o) to authorize resume. | The downgrade guard (`986-993`) only blocks lower versions and is disabled (`from_version` is None per 1p44p), so a same-version re-extract is currently unguarded; the lock marker is the durable signal that the prior run failed at the gate. | Re-derive failure state from logs (fragile); always re-extract (the status quo we are fixing). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Resume phase runs before 1p44o lands, so the lock has no `failed_phase` marker to read. | Hard dependency on 1p44o; resume gracefully errors with a clear message when the marker is absent. |
| `server_impl.py` edits conflict with 1p44z (shared MCP phase registration). | Coordinate via the Serialization Points; sequence the `wave_upgrade` edits and re-run the MCP wrapper tests after merge. |
| Idempotence guard skips extract when it should not (e.g. partial/corrupt tree at matching VERSION). | Key the guard strictly on `framework/VERSION` equality and document that a forced full re-extract path remains available for corruption recovery. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
