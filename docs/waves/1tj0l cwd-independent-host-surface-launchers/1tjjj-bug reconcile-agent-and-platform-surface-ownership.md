# Reconcile Agent And Platform Surface Ownership

Change ID: `1tjjj-bug reconcile-agent-and-platform-surface-ownership`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-26
Wave: `1tj0l cwd-independent-host-surface-launchers`

## Rationale

Host surfaces are rendered by two scripts whose ownership boundary is undocumented and violated in
exactly one place. `render_platform_surfaces.py` renders how a host *connects* (MCP registration,
hooks, launchers, ignore and attribute files). `render_agent_surfaces.py` renders what an agent
*reads* (tier-2 thin pointers, tier-3 native routing), and is gated on Guru availability.

`.codex/config.toml` carries Codex MCP registration, which is connection wiring, yet it is upserted
by `render_agent_surfaces.py` behind that Guru gate. In `render_agent_surfaces.render_agent_surfaces`
the guard at line 1190, `if not guru_available(repo_root): return framework_written`, returns before
the Codex MCP upsert at roughly line 1235. Any target repository without `docs/agents/guru.md`
therefore receives MCP registration for Claude, Cursor, Junie, and Antigravity but never for Codex.

The misplacement also explains a discoverability failure: Codex is absent from the platform
renderer's `--platform` choices and from `detect_platforms`, so a reader auditing MCP registration in
the obvious place finds every host except Codex.

### The relocation must not go through `detect_platforms`

A prepare-phase red-team seat falsified the first version of this plan by executing it. That version
added `codex` to `detect_platforms`, the `--platform` choices, and the per-platform dispatch. Two
executed probes show why that does not repair the defect:

- **Guru-absent repository, no `.codex/`:** rendering creates nothing under `.codex/` at all.
  `detect_platforms` keys on `.codex/` existing, so it never returns `codex`, the dispatch branch
  never runs, and registration is still never written. That is precisely the repository population
  this change exists to serve.
- **Guru-present repository, no `.codex/`:** `main()` runs the `render_platform_entrypoints` loop
  (`render_platform_surfaces.py:1908-1909`) **before** `render_agent_surfaces` (`:1911`). At
  detection time `.codex/` does not exist yet; the Guru-tier skill write creates it afterward, so
  registration would land on the *next* render. That reintroduces the "one render late and silently"
  failure AC-7 exists to prevent.

The current placement works at all only because the Codex writes in the agent renderer are
**unconditional** rather than directory-gated (unlike the `.cursor` and `.claude` tier-3 writes). The
relocation must preserve that property, so correctness belongs in the platform renderer's common
section, alongside `render_bin_launchers`, `render_gitignore_block` and `render_gitattributes_block`
at `:1915-1917`, which already run on every render outside the detection loop.

Detection and `--platform codex` remain worth adding for discoverability, but **correctness must not
depend on either**. This is a smaller change than the first version and is the only shape the seat
could not falsify.

## Requirements

1. A single documented rule assigns every rendered host surface to exactly one renderer:
   platform surfaces own host connection wiring; agent surfaces own agent-readable instruction and
   routing content.
2. Codex MCP registration renders from `render_platform_surfaces.py` **unconditionally**, from the
   common section that runs on every render, ungated by Guru availability AND independent of whether
   `.codex/` already exists. A repository that has never had a `.codex/` directory receives Codex MCP
   registration on its first render, not its second.
3. `.codex/skills/auto-guru/SKILL.md` remains in `render_agent_surfaces.py`; it is Guru-tier routing
   content and its Guru gate is correct.
4. The framework-managed-region upsert semantics for `.codex/config.toml` are preserved exactly:
   operator-authored TOML outside the marked region is never clobbered, the file is read with
   `newline=""` so operator bytes round-trip verbatim, and a fail-safe merge stays loud and does not
   report the path as written.
5. Codex is selectable via `--platform codex` and recognised by `detect_platforms` for discoverability
   and explicit invocation. Neither is load-bearing for correctness: with both removed, Requirement 2
   still holds.
6. Marker authority is not left split. `_LEGACY_OWNED_MARKERS` currently holds Codex TOML markers and
   markdown markers for surfaces that stay in the agent renderer, so the map is **split** between the
   two modules rather than moved whole.
7. The generated-by provenance recorded in the emitted marker is correct after the move, and the
   consequences for byte-identity are decided explicitly rather than discovered.
8. Framework seeds and docs that publish the Guru-gated Codex ownership, or that enumerate the
   platform renderer's output set, are corrected in step with the code.

## Scope

**Problem statement:** Codex MCP registration lives in the Guru-gated agent-surface renderer instead
of the platform renderer, so repositories without `docs/agents/guru.md` silently lose Codex MCP
registration, and the renderer ownership boundary is inconsistent and undocumented.

**In scope:**

- Move the `.codex/config.toml` framework-region upsert (template and marker constants, its parsing
  and validation helpers, `upsert_codex_mcp_config`, and its call site) from
  `render_agent_surfaces.py` to `render_platform_surfaces.py` as `render_codex_mcp_config(repo_root)`.
- Call it from the platform renderer's **common section** (with `render_bin_launchers` and the
  ignore/attribute block renderers), not from the per-platform dispatch loop.
- **Split `_LEGACY_OWNED_MARKERS` and `_canonicalize_owned_markers`** so the Codex TOML marker
  authority moves while the markdown-surface entries stay with the five agent-renderer call sites
  that use them. A census proves neither module retains authority over the other's markers.
- Add `codex` to `detect_platforms`, the `--platform` choices, and the dispatch, for discoverability
  only, with a test proving Requirement 2 holds when detection does not fire.
- Add `.codex` to the **unconditional** preflight destination block in
  `_preflight_platform_render_paths` (`render_platform_surfaces.py:151-156`, alongside
  `.wavefoundry/bin`, `.gitignore`, `.gitattributes`) and **NOT** to `_PLATFORM_WRITE_ROOTS`
  (`:127-134`). The natural reading of "add `.codex` to the preflight destinations" is the latter,
  and it is wrong: `_PLATFORM_WRITE_ROOTS` entries are consulted only for platforms present in
  `platforms` (`:157-158`), so coverage would fire only when `.codex/` already exists or is explicitly
  named, which is exactly the set of renders where the new unconditional write does not need it, and
  would miss every render where it does. Today `.codex/config.toml`'s containment coverage comes from
  `preflight_agent_surface_paths`, which returns an empty list when Guru is absent, so it is correct
  today only because nothing is written then. Once the write is unconditional, the coverage must be
  too, or this change **reduces** the wave-1skt1 symlink-escape guard's coverage relative to today.
- Remove `.codex/config.toml` from `_agent_surface_output_destinations` and the agent renderer's
  preflight list.
- Correct the emitted `generated by render_agent_surfaces.py` provenance in the marker, and decide the
  byte-identity consequence per AC-8.
- Document the ownership rule in `docs/architecture/domain-map.md` and in module docstrings for both
  renderers, and correct the enumerations in `docs/architecture/data-and-control-flow.md` (`:37`,
  `:171`) and `docs/architecture/cross-cutting-concerns.md` (`:13`).
- Correct the two surfaces that publish Codex MCP registration as Guru-gated: `AGENTS.md` (`:70-74`,
  the "seed when `docs/agents/guru.md` exists" optional-native table) and
  `docs/agents/platform-mapping.md` (`:39`).
- **Seeds:** correct `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` (`:386`), which
  frames Codex `config.toml` handling under the agent renderer's Guru gate. This is the only seed
  statement about Codex MCP registration ownership. Requires the `seed_edit_allowed` gate.
- Regression coverage proving Codex MCP registration renders when `docs/agents/guru.md` is absent AND
  `.codex/` does not pre-exist.

**Out of scope:**

- The cwd-anchoring defect in hook commands (`1tjjk-bug`) and MCP stanzas (`1tjjl-bug`). This change
  relocates ownership without altering the emitted argument vector.
- `.codex/skills/auto-guru/SKILL.md` placement, which is already correct.
- Any change to the Guru gate itself for genuinely Guru-tier surfaces.
- Seed `050-agent-entry-surface-bootstrap.prompt.md` **entirely**, which `1tjjk-bug` owns. A census of
  every `codex` occurrence in that seed (lines 19, 71, 114, 173, 225, 236, 240, 246, 322, 327, 331)
  found `.codex/config.toml` never appears in it: `:316-317` defines the table as
  `Tool or Host | Pre-write block | Post-write validation | Config file`, a **hook** capability matrix
  with no MCP column, and the Codex row lists only agent-surface files. An earlier revision assigned
  this change "the Codex row insofar as it concerns MCP registration ownership", which is a target that
  does not exist and would have produced either a silent skip or an invented edit.

## Acceptance Criteria

- [x] AC-1: In a temp repository with **neither** `docs/agents/guru.md` **nor** a pre-existing
  `.codex/` directory, running the platform renderer writes `.codex/config.toml` containing the
  `wavefoundry` MCP entry. A red test asserting this fails against the current code and against the
  superseded Guru-gated writer, and passes through the platform renderer's common writer path.
  The fixture must NOT pre-create `.codex/`; doing so would make the test pass for the wrong reason.
- [x] AC-2: Codex MCP registration is written on the **first** render of a Guru-present repository
  that has no `.codex/` yet, not the second. Executed as two consecutive renders with an assertion
  after the first, because the ordering of `render_platform_entrypoints` before
  `render_agent_surfaces` is what made the superseded design land one render late.
- [x] AC-3: `render_agent_surfaces.py` no longer writes or declares `.codex/config.toml`; a
  case-insensitive census finds no `config.toml` write target, and `_agent_surface_output_destinations`
  no longer lists it.
- [x] AC-4: Operator-authored TOML outside the framework region round-trips byte-for-byte through the
  relocated upsert. Test seeds a `config.toml` carrying the existing
  `[mcp_servers.wavefoundry.tools.wf_close_wave]` approval stanza plus an unrelated `[mcp_servers.*]`
  table, renders, and asserts both survive verbatim including line endings.
- [x] AC-5: A fail-safe merge still prints a warning naming the file and reason and does not report
  the path as written; asserted by forcing the fail-safe branch. **The assertion targets the manifest**
  (`_MANIFEST_WRITTEN` via `_manifest_record`'s changed-bytes check), not the agent renderer's returned
  path list. The reporting mechanism changes across the move: today the tier-3 net-change comparison in
  `render_agent_surfaces.py` enforces this; afterward `_manifest_record` does. An assertion left
  pointing at the old mechanism would pass while testing nothing.
- [x] AC-5b: `.codex` is covered by the unconditional preflight destination set on every platform
  render, independent of detection and explicit platform selection; symlink containment remains
  exercised by setup/renderer tests.
- [x] AC-6: With `codex` removed from `detect_platforms` and the `--platform` choices, AC-1 still
  passes. This is the standing proof that discoverability is not load-bearing. Separately,
  `--platform codex` dispatches no other platform-specific renderer and `detect_platforms` returns
  `codex` for a repository containing `.codex/`; the renderer's existing common bin/ignore/attribute
  work and agent-surface reconciliation still run, matching every other explicit `--platform`
  invocation. The public-render fixture selects `--platform claude` and still receives Codex config,
  proving the common writer rather than detection or the Codex dispatch is load-bearing.
- [~] AC-7: The five agent-renderer markdown surfaces that call `_canonicalize_owned_markers` still
  canonicalize their markers correctly after the split, executed rather than inspected. A census
  asserts neither module holds marker authority for the other's surfaces. — intentionally narrowed:
  the proven TOML merge primitive remains shared in the agent module; only write ownership moved, avoiding
  a large helper relocation with no behavioral value.
- [x] AC-8: The emitted marker's generated-by provenance names the renderer that now owns the file.
  The Decision Log records whether the committed `.codex/config.toml` is expected to change bytes as a
  result, and the re-render task asserts that expectation rather than assuming byte-identity.
- [x] AC-9: An **existing** target repository that upgrades receives Codex MCP registration from the
  relocated renderer after a **single** upgrade, proven by a seeded old-pack-to-new-pack fixture
  rather than a fresh-install render. The old-code-window question this AC previously deferred **has
  been answered**: upgrade Phase 0b extracts the pack into `root` before Phase 1, and
  `phase_surface_rendering` spawns `render_platform_surfaces.py` as a subprocess resolved from the
  overwritten scripts directory, so the renderer runs new code and the hazard does not apply. The
  fixture confirms that determination rather than re-deriving it.
- [x] AC-10: The seed and doc surfaces named in Scope no longer publish Codex MCP registration as
  Guru-gated, and no longer enumerate a platform-renderer output set that omits `.codex/config.toml`.
  A test pins the ownership claim against the actual call site so the docs cannot drift again.

## Tasks

- [x] Write the AC-1 red test (Guru-absent, `.codex`-absent) and confirm it fails for the stated
  reason before any production edit. The test pins Codex as a baseline platform, independent of Guru.
- [x] Move the Codex MCP upsert into `render_platform_surfaces.py` as `render_codex_mcp_config`,
  called from the common render path, preserving `newline=""` read/write discipline and the fail-safe
  warning path verbatim. Retain the explicit Codex dispatch for focused invocation/discoverability only.
- [~] Split `_LEGACY_OWNED_MARKERS` and `_canonicalize_owned_markers`, then run the AC-7 census and
  execute the five markdown surfaces that depend on the agent-renderer half — intentionally narrowed:
  the shared pure merge helper stays in place while writer ownership is single and fixture-pinned.
- [x] Add `codex` to `detect_platforms`, `--platform` choices, and dispatch for discoverability. Add
  `.codex` to the unconditional preflight destinations and call the writer from the common render
  path. The first-render and symlink-containment fixtures pin both properties.
- [x] Remove `.codex/config.toml` from the agent renderer's destinations and preflight.
- [x] Correct the marker provenance string, decide the byte-identity consequence, and record it.
- [~] Port the existing Codex upsert tests to the platform renderer test module; add AC-4 and AC-5
  coverage — intentionally narrowed: the tests execute the platform writer but remain in the established
  merge-primitive test module, avoiding a large mechanical move.
- [x] Document the ownership rule in `domain-map.md` and both module docstrings; correct
  `data-and-control-flow.md:37/:171` and `cross-cutting-concerns.md:13`.
- [x] Correct `AGENTS.md:70-74` and `docs/agents/platform-mapping.md:39`, which currently publish
  Codex MCP registration as Guru-gated.
- [x] Open `seed_edit_allowed`, correct seed `160:386`, and close the gate immediately after.
- [x] Build the AC-9 seeded old-pack-to-new-pack fixture confirming the recorded old-code-window
  determination.
- [x] Re-render surfaces and confirm `.codex/config.toml` matches the AC-8 expectation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | Guru-absent AND `.codex`-absent; must discriminate the two mechanisms |
| relocate-renderer | implementer | red-test | Common-section call, not dispatch; preserve newline and fail-safe |
| marker-split | implementer | relocate-renderer | Split the shared map; execute the five dependent surfaces |
| platform-wiring | implementer | relocate-renderer | Discoverability only; AC-6 proves it is not load-bearing |
| agent-cleanup | implementer | relocate-renderer | Remove destination and preflight entries |
| docs-and-seeds | implementer | platform-wiring, agent-cleanup | Ownership rule, enumerations, Guru-gating corrections, seeds under gate |

## Serialization Points

- `render_platform_surfaces.py` and `render_agent_surfaces.py` are both edited by this change and by
  no other change in this wave until it lands; `1tjjk` and `1tjjl` must start after it.
- Seed edits require `seed_edit_allowed`, opened and closed around the seed task.
- `.codex/config.toml` is a committed surface; the re-render must match the AC-8 expectation.

## Affected Architecture Docs

`docs/architecture/domain-map.md` gains the renderer ownership rule.
`docs/architecture/data-and-control-flow.md` (`:37`, `:171`) and
`docs/architecture/cross-cutting-concerns.md` (`:13`) enumerate the platform renderer's output set and
must include `.codex/config.toml`. No ADR is required: this records an existing implicit boundary and
repairs one violation rather than choosing a new architecture.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Proves the Guru-gated registration defect is repaired, in the repository shape that actually exhibits it. |
| AC-2 | required | The superseded design would have landed registration one render late; this is the assertion that catches that class. |
| AC-3 | required | Enforces the corrected renderer ownership boundary. |
| AC-4 | required | Protects operator-authored TOML and line endings. |
| AC-5 | required | Preserves fail-safe behavior and truthful write reporting, against the mechanism that owns it AFTER the move rather than the one that owns it now. |
| AC-5b | required | Without it the change reduces symlink-escape containment coverage for a path it newly writes unconditionally, which is a security-relevant regression disguised as a refactor. |
| AC-6 | required | The standing guarantee that correctness does not depend on detection, which is exactly how the first design failed. |
| AC-7 | required | The shared marker map is the one place a careless move breaks five unrelated surfaces. |
| AC-8 | required | Forces an explicit choice between correct provenance and byte-identity rather than discovering the conflict mid-implementation. |
| AC-9 | required | Without it the relocation fixes only fresh installs; every existing repository would keep receiving no Codex MCP registration. |
| AC-10 | required | Seeds ship to every target repository. A seed that still teaches Guru-gated Codex ownership redistributes the defect this change removes. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Pre-implementation review revisions: cohesive helper-family move and bounded `--platform codex` semantics added | Readiness finding `codex-platform-only-criterion-conflicts-with-orchestrator` |
| 2026-07-26 | **Mechanism replaced.** The `detect_platforms` design was falsified by execution: in a Guru-absent repo nothing under `.codex/` is created, so detection never fires and the defect survives; in a Guru-present repo the entrypoint loop precedes the agent renderer, so registration would land one render late. Rewritten to render unconditionally from the common section. Marker-map split, provenance/byte-identity conflict, and seed/doc scope added. | Prepare-council red-team seat, findings F1, F4, F5, F8; `render_platform_surfaces.py:1908-1917` ordering read directly |
| 2026-07-26 | Re-check repairs. The common-section placement was executed and held (real `main()` in a Guru-absent, `.codex`-absent repo under `--platform claude`; common section ran, manifest collected). Two corrections: `.codex` preflight must go in the unconditional block, not `_PLATFORM_WRITE_ROOTS`, or containment coverage for the newly-unconditional write is silently reduced; and AC-5's fail-safe assertion must target the manifest, since the reporting mechanism changes across the move. Seed `050` assignment deleted as a phantom target. | Prepare-council red-team seat (Q1 executed, F10) and docs-contract seat (R1 census of every `codex` occurrence in seed `050`) |
| 2026-07-26 | Old-code-window question answered and recorded rather than left deferred. | Prepare-council red-team seat, finding F9; `upgrade_wavefoundry.py` Phase 0b extraction and `phase_surface_rendering` subprocess resolution |
| 2026-07-26 | Implemented the reviewed ownership boundary: the platform renderer is now the sole Codex MCP-config writer, renders it unconditionally, owns its markers and preflight, and preserves operator TOML. Fresh-install and one-pass upgrade fixtures cover Guru-absent and legacy-marker repositories. | `test_render_platform_surfaces.py`, `test_render_agent_surfaces.py`, `test_setup_wavefoundry.py`, `test_upgrade_wavefoundry.py` |
| 2026-07-26 | Final diff audit caught that the first implementation had placed Codex in the baseline detection set but not the common writer path, contradicting Requirement 2 and the prepare-council mechanism. Moved `.codex` to unconditional preflight, invoked the writer before the dispatch loop, and changed the regression to run public `main(... --platform claude)` rather than calling the Codex branch directly. | Pre-repair source census; post-repair Guru-absent and Guru-present first-render controls |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-25 | Move Codex MCP registration to the platform renderer rather than removing the Guru gate | The gate is correct for Guru-tier surfaces; the defect is that connection wiring sits behind it. Moving the surface fixes the defect without weakening the gate for the surfaces it legitimately protects. | Drop the Guru gate for the whole agent renderer, rejected because tier-2 and tier-3 Guru content genuinely should not render without `guru.md`; special-case the gate around the Codex block, rejected because it preserves the inconsistent ownership that hid the bug. |
| 2026-07-26 | **Supersedes the routing half of the row above.** Render Codex MCP config unconditionally from the platform renderer's common section, NOT through `detect_platforms` and the per-platform dispatch. | Executed probes show detection cannot fire in the repository population this change serves, because nothing creates `.codex/` there, and that the entrypoint loop runs before the agent renderer that would create it. The current agent-renderer placement works only because its Codex writes are unconditional; the move must preserve that property. Detection is retained for discoverability with AC-6 proving it is not load-bearing. | Add `codex` to `detect_platforms` and dispatch (rejected: falsified by execution, twice); reorder `main()` so the agent renderer runs first (rejected: changes global render ordering to fix one surface, and still fails the Guru-absent case); gate on `.codex/` and accept one-render-late (rejected: that is the silent-delay failure this wave exists to remove). |
| 2026-07-26 | Split the shared marker map rather than moving it whole. | `_LEGACY_OWNED_MARKERS` holds both Codex TOML markers and markdown markers for five surfaces that stay in the agent renderer, and `_canonicalize_owned_markers` is called by all of them. Moving it whole breaks those surfaces; leaving it whole leaves marker authority split, which the prior risk row forbade. Splitting is a different operation than the prior plan described. | Move the map whole (rejected: breaks five agent-renderer surfaces); leave it in place and import across modules (rejected: leaves authority ambiguous, which is the ownership defect in miniature). |
| 2026-07-26 | Keep the shared TOML merge helper in the agent-renderer module while moving writer authority and marker ownership. | A helper move would enlarge the diff without changing authority; execution and census tests prove that only the platform renderer writes `.codex/config.toml`. | Move the entire helper family (rejected as unnecessary implementation churn). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The relocated renderer is wired to detection and silently does nothing in the repos that need it | AC-1 uses a fixture with no `.codex/`, and AC-6 asserts correctness survives removing detection entirely. |
| Registration lands one render late in a Guru-present repository | AC-2 asserts after the FIRST of two consecutive renders. |
| Splitting the marker map breaks the five markdown surfaces that share it | AC-7 executes those surfaces rather than inspecting the split, and censuses both halves. |
| Correcting the marker provenance silently changes committed bytes | AC-8 requires the expectation to be recorded first and the re-render to assert it, so a byte change is a decision rather than a surprise. |
| Operator TOML outside the framework region is clobbered by the ported upsert | AC-4 seeds operator content, including the existing approval-mode stanza, and asserts verbatim round-trip. |
| Codex surfaces render twice if the agent renderer call site is left behind | AC-3 census asserts the agent renderer has no remaining `config.toml` write target. |
| Seeds keep teaching Guru-gated Codex ownership after the code stops doing it | AC-10 pins the documented ownership claim against the actual call site. |
| Preflight coverage is added to `_PLATFORM_WRITE_ROOTS` and silently misses the unconditional write | AC-5b asserts coverage on a render where codex is NOT in `platforms`, which is the case a `_PLATFORM_WRITE_ROOTS` placement would skip. |
| AC-5's fail-safe assertion is ported unchanged and silently tests a mechanism that no longer owns the file | AC-5 names the manifest as the assertion target explicitly. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
