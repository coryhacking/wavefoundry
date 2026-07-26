# Reconcile Agent And Platform Surface Ownership

Change ID: `1tjjj-bug reconcile-agent-and-platform-surface-ownership`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-25
Wave: `1tj0l cwd-independent-host-surface-launchers`

## Rationale

Host surfaces are rendered by two scripts whose ownership boundary is undocumented and violated in
exactly one place. `render_platform_surfaces.py` renders how a host *connects* (MCP registration,
hooks, launchers, ignore and attribute files). `render_agent_surfaces.py` renders what an agent
*reads* (tier-2 thin pointers, tier-3 native routing), and is gated on Guru availability.

`.codex/config.toml` carries Codex MCP registration, which is connection wiring, yet it is upserted
by `render_agent_surfaces.py` behind that Guru gate. This is not only a tidiness problem; it
produces a live defect. In `render_agent_surfaces.render_agent_surfaces` the guard at line 1190,
`if not guru_available(repo_root): return framework_written`, returns before the Codex MCP upsert at
roughly line 1235. Any target repository without `docs/agents/guru.md` therefore receives MCP
registration for Claude, Cursor, Junie, and Antigravity (all rendered by the ungated platform
renderer) but never for Codex.

The misplacement also explains a discoverability failure: Codex is absent from the platform
renderer's `--platform` choices and from `detect_platforms`, so a reader auditing MCP registration
in the obvious place finds every host except Codex.

## Requirements

1. A single documented rule assigns every rendered host surface to exactly one renderer:
   platform surfaces own host connection wiring; agent surfaces own agent-readable instruction and
   routing content.
2. Codex MCP registration renders from `render_platform_surfaces.py`, ungated by Guru availability,
   with parity to the other four MCP hosts.
3. `.codex/skills/auto-guru/SKILL.md` remains in `render_agent_surfaces.py`; it is Guru-tier routing
   content and its Guru gate is correct.
4. The framework-managed-region upsert semantics for `.codex/config.toml` are preserved exactly:
   operator-authored TOML outside the marked region is never clobbered, the file is read with
   `newline=""` so operator bytes round-trip verbatim, and a fail-safe merge stays loud and does not
   report the path as written.
5. Codex is selectable via `--platform codex` and is recognised by `detect_platforms`.

## Scope

**Problem statement:** Codex MCP registration lives in the Guru-gated agent-surface renderer instead
of the platform renderer, so repositories without `docs/agents/guru.md` silently lose Codex MCP
registration, and the renderer ownership boundary is inconsistent and undocumented.

**In scope:**

- Move the complete `.codex/config.toml` framework-region upsert family—template and marker
  constants, parsing/validation helpers, `upsert_codex_mcp_config`, and its call site—from
  `render_agent_surfaces.py` to `render_platform_surfaces.py` as one cohesive ownership unit.
- Add `codex` to `detect_platforms`, to the `--platform` choices, and to the platform dispatch.
- Add `.codex` to the platform renderer's render-path preflight destinations.
- Remove `.codex/config.toml` from `_agent_surface_output_destinations` and from the agent renderer's
  preflight list.
- Document the ownership rule in `docs/architecture/domain-map.md` (or the closest existing
  renderer-boundary doc) and in module docstrings for both renderers.
- Regression coverage proving Codex MCP registration renders when `docs/agents/guru.md` is absent.

**Out of scope:**

- The cwd-anchoring defect in hook commands (`1tjjk-bug`) and MCP stanzas (`1tjjl-bug`). This change
  relocates ownership without altering emitted command strings.
- `.codex/skills/auto-guru/SKILL.md` placement, which is already correct.
- Any change to the Guru gate itself for genuinely Guru-tier surfaces.

## Acceptance Criteria

- [ ] AC-1: With `docs/agents/guru.md` absent from a temp repository, running the platform renderer
  writes `.codex/config.toml` containing the `wavefoundry` MCP entry. A red test asserting this
  fails against the current code (Codex registration missing) and passes after the move.
- [ ] AC-2: `render_agent_surfaces.py` no longer writes or declares `.codex/config.toml`; a
  case-insensitive census over the agent renderer finds no `config.toml` write target, and
  `_agent_surface_output_destinations` no longer lists it.
- [ ] AC-3: Operator-authored TOML outside the framework region round-trips byte-for-byte through the
  relocated upsert. Test seeds a `config.toml` carrying the existing
  `[mcp_servers.wavefoundry.tools.wf_close_wave]` approval stanza plus an unrelated `[mcp_servers.*]`
  table, renders, and asserts both survive verbatim including line endings.
- [ ] AC-4: A fail-safe merge still prints a warning naming the file and reason and does not report
  the path as written; asserted by forcing the fail-safe branch.
- [ ] AC-5: `--platform codex` dispatches no other platform-specific renderer, and
  `detect_platforms` returns `codex` for a repository containing `.codex/`. The renderer's existing
  common bin/ignore/attribute work and agent-surface reconciliation still run, matching every other
  explicit `--platform` invocation; this change does not redefine global CLI selection semantics.
- [ ] AC-6: The renderer ownership rule is stated in a durable doc and in both module docstrings, and
  a docs reference exists that a future reader can find from the codebase map.
- [ ] AC-7: An **existing** target repository that upgrades receives Codex MCP registration from the
  relocated renderer, proven by a seeded old-pack-to-new-pack fixture rather than by a fresh-install
  render, and asserted to be present after a **single** upgrade. Required because upgrade Phase 1 runs
  `render_platform_surfaces.py` and this repository has a documented old-code-window hazard in which
  the orchestrator executes pre-upgrade code — the mechanism that silently skipped scheme-v2
  provisioning in the field. If the relocated renderer is reached only by pre-upgrade code, existing
  projects would gain Codex registration one upgrade late and silently; the fixture must distinguish
  those two outcomes rather than assume the favourable one.

## Tasks

- [ ] Write the red test for AC-1 (Guru-absent repo, Codex MCP registration expected) and confirm it
  fails for the stated reason before any production edit.
- [ ] Move the full Codex MCP upsert helper/constant family and its call site into
  `render_platform_surfaces.py` as a `render_codex_mcp_config(repo_root)` renderer, preserving
  `newline=""` read/write discipline and the fail-safe warning path verbatim. Run a symbol/string
  census so no parsing helper or marker authority remains split across the two modules.
- [ ] Add `codex` to `detect_platforms`, `--platform` choices, dispatch, and the preflight
  destination map (`.codex`).
- [ ] Remove `.codex/config.toml` from the agent renderer's destinations and preflight.
- [ ] Port the existing Codex upsert tests to the platform renderer test module; add AC-3 and AC-4
  coverage.
- [ ] Document the ownership rule in the architecture docs and both module docstrings.
- [ ] Determine whether upgrade Phase 1 reaches the relocated renderer with pre- or post-upgrade code,
  then build the AC-7 seeded old-pack-to-new-pack fixture proving Codex registration lands after a
  single upgrade. If the old-code window applies, repair it here rather than deferring.
- [ ] Re-render surfaces and confirm `.codex/config.toml` is byte-identical to its committed form
  (this change must not alter emitted content).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | AC-1 red test must fail first, for the stated reason |
| relocate-renderer | implementer | red-test | Move upsert plus call site; preserve newline and fail-safe semantics |
| platform-wiring | implementer | relocate-renderer | detect_platforms, --platform, dispatch, preflight |
| agent-cleanup | implementer | relocate-renderer | Remove destination and preflight entries |
| docs-boundary | implementer | platform-wiring, agent-cleanup | Ownership rule in architecture docs plus docstrings |

## Serialization Points

- `render_platform_surfaces.py` and `render_agent_surfaces.py` are both edited by this change and by
  no other change in this wave until it lands; `1tjjk` and `1tjjl` must start after it.
- `.codex/config.toml` is a committed surface; re-render must prove byte-identical output.

## Affected Architecture Docs

`docs/architecture/domain-map.md` gains the renderer ownership rule. `docs/architecture/testing-architecture.md`
is unaffected. No ADR is required: this records an existing implicit boundary and repairs one
violation rather than choosing a new architecture.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Proves the Guru-gated registration defect is repaired. |
| AC-2 | required | Enforces the corrected renderer ownership boundary. |
| AC-3 | required | Protects operator-authored TOML and line endings. |
| AC-4 | required | Preserves fail-safe behavior and truthful write reporting. |
| AC-5 | required | Adds Codex platform dispatch without changing global CLI semantics. |
| AC-6 | required | Makes the ownership rule durable and discoverable. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Pre-implementation review revisions: cohesive helper-family move and bounded `--platform codex` semantics added | Readiness finding `codex-platform-only-criterion-conflicts-with-orchestrator` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-25 | Move Codex MCP registration to the platform renderer rather than removing the Guru gate | The gate is correct for Guru-tier surfaces; the defect is that connection wiring sits behind it. Moving the surface fixes the defect without weakening the gate for the surfaces it legitimately protects. | Drop the Guru gate for the whole agent renderer, rejected because tier-2 and tier-3 Guru content genuinely should not render without `guru.md`; special-case the gate around the Codex block, rejected because it preserves the inconsistent ownership that hid the bug. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Relocation silently changes emitted `.codex/config.toml` bytes | Re-render and diff against the committed file; require byte-identical output as a task gate. |
| Operator TOML outside the framework region is clobbered by the ported upsert | AC-3 seeds operator content, including the existing approval-mode stanza, and asserts verbatim round-trip. |
| Codex surfaces render twice if the agent renderer call site is left behind | AC-2 census asserts the agent renderer has no remaining `config.toml` write target. |
| Only the public upsert function moves while its marker/parser helpers remain split | Move and census the cohesive helper/constant family as one ownership unit. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
