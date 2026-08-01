# Renderer-Owned MCP Permission Allowlist for Claude Code Surfaces

Change ID: `1u2az-enh rendered-mcp-permission-allowlist`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-31
Wave: `1u2b0 host-surface-hardening`

## Rationale

Target repositories repeatedly hit permission friction with the wavefoundry MCP tool surface, in
three field-observed forms:

1. **Stale allowlists after tool renames.** The 1.14.0 no-alias `wave_*` renames (plus the 1.15.0
   `wf_review_evidence` to `wf_review_event` rename) left 13 to 26 stale allow rules in target
   repos' `.claude/settings.local.json`, and every renamed tool call prompted until the operator
   hand-edited the file (agents cannot self-edit it; the `host_permission_flags` reconciliation
   channel exists precisely because of this).
2. **Lifecycle writes blocked mid-flow.** During the 1tz6l close-out the Claude Code auto-mode
   classifier denied a `wf_review_event` approval write mid-sequence; the deterministic fix was a
   one-line allow rule the operator had to authorize.
3. **Per-repo drift.** Each repo accumulates its own ad-hoc allowlist, so behavior differs across
   otherwise identical installs.

The framework already owns adjacent surface: `render_platform_surfaces.render_claude_settings`
(`:1233-1296`) renders the hooks portion of the committed `.claude/settings.json` today via a
deterministic merge that preserves operator content, and the seed-050 `.gitignore` block shows the
managed-content pattern. Deriving an allowlist from the server's tool roster makes renames
self-heal on upgrade, retroactively fixing failure form 1 for the committed file.

**Council authority constraint (P1, resolved in-plan, 2026-07-31):** the repo's own doctrine
(seed-160:74, `docs/specs/mcp-tool-surface.md:858`, `reconcile_scan.py:146-156`) says agents never
self-edit allow rules; a naive design would let an agent flip a tier knob and call
`wf_sync_surfaces(mode='run')` to self-grant allow rules for operator-consent tools
(`wf_close_wave`, gates), laundering a permission escalation through a subprocess. The requirements
below narrow that channel as far as the framework can: permissions rendering runs only on the
upgrade/install path, and agent-invocable `wf_sync_surfaces` never touches the permissions content.
Delivery review corrected two claims that were originally stated too strongly here, and the
Decision Log rows dated 2026-07-31 are authoritative over this paragraph: `wf_upgrade` is itself
agent-callable and does render (bounded to the read tier, and it cannot allowlist itself because it
is write-tier), and the mutating-tier knob's protection is a host guarantee plus prompt policy
rather than a framework-structural one.

## Requirements

1. The upgrade/install render path emits a framework-owned allowlist into the committed
   `.claude/settings.json` `permissions.allow` array via a **provenance-tracked set-merge**: the
   renderer records which entries it emitted (a dedicated provenance key in the file, since rules
   are only honored inside the literal `permissions.allow` array and JSON has no comment markers)
   and on later renders adds/removes only entries it recorded emitting. Ownership is NEVER inferred
   from the `mcp__wavefoundry__` name prefix: an operator-authored rule that happens to name a
   wavefoundry tool (the exact failure-form-2 fix) must survive every render. Evaluate the existing
   `render_claude_settings` value-marker ownership pattern (`:1244-1282`) at Prepare before
   inventing new mechanics.
2. The allowlist derives from a canonical tool roster with a **dedicated permission-tier
   attribute**. Council-verified constraints: `public_contract.py` carries no tool roster today,
   the roster lives only in decorated closures inside `register_mcp_surface` (unimportable from the
   stdlib-only renderer), and `readOnlyHint` is the WRONG datum (the retrieval tools are
   deliberately `_OBSERVATIONAL_TOOL` with `readOnlyHint: False` because they write telemetry).
   The design therefore extracts a lightweight stdlib roster module (tool name + tier) consumed by
   both `register_mcp_surface` and the renderer, with a parity test asserting registration and
   roster agree; decide at Prepare whether the runner-registered reload-survivor tools are roster
   members.
3. **Tiered by risk; the write tier is operator-gated end-to-end:** the read-only tier (retrieval,
   listing, status, search tools) renders in the distributed default. The mutating lifecycle tier
   (`wf_review_event`, `wf_prepare_wave`, `wf_close_wave`, gates, `wf_upgrade`, `memory_*` writes,
   `index_build`) renders ONLY when an operator-owned knob enables it; the knob must not live in
   workflow-config or any agent-editable rendered block. Candidate homes to decide at Prepare, with
   the constraint that "framework owns generic defaults; per-project config stays minimal": an
   operator-authored entry in the settings file itself outside the managed provenance, or an
   explicit `wf` CLI flag the operator runs.
4. **The agent-invocable surface-sync render never widens permissions:** `wf_sync_surfaces(mode='run')`
   must not add, remove, or modify `permissions` content, and a test pins this negative. Permissions
   rendering happens only on the upgrade/install orchestration path, but that path is
   **operator-approved rather than agent-unreachable**, and the requirement is scoped accordingly
   (corrected during delivery review): `wf_upgrade` is an agent-callable MCP tool whose first phase
   renders, with impact bounded to the read tier because the write tier needs the operator knob and
   `wf_upgrade` is itself write-tier; and the renderer's switch can be passed through the `wf`
   dispatcher, an accepted residual outside the threat model because unrestricted shell access
   already implies write access to `.claude/settings.json`. Both residuals are stated in the shipped
   docs rather than papered over.
5. Operator-authored allow/deny/ask entries are preserved **value-identically under canonical
   re-serialization** (the existing renderer re-serializes the whole file with `indent=2`, and the
   Claude Code host itself appends saved prompt rules and rewrites the file, so byte-for-byte and
   render-to-render byte-stability claims only hold with no interleaved writers). Deny-wins over
   allow is host semantics, stated as rationale, not tested here.
6. **The upgrade surfaces the permissions diff as the operator's consent point:** even the
   read-only tier is a prompting-posture change shipped by upgrade; the upgrade output must name
   the rendered permissions delta explicitly rather than folding it into a generic
   surfaces-rendered line.
7. **Channel split in reconciliation moves in lockstep:** `reconcile_scan.py` currently classifies
   all of `.claude/settings.json` as operator-territory (`HOST_PERMISSION_FILES`, `:152-156`).
   After this change, stale wavefoundry rules inside the renderer's provenance self-heal at the
   next upgrade render (and the scan should say so), while entries outside the provenance and all
   of `settings.local.json` remain genuinely operator-owned. Seed-160 (:33, :74) and
   `docs/specs/mcp-tool-surface.md:858` are rewritten coordinately. The upgrade phase ordering
   (render-surfaces precedes the reconciliation scan, seed-160:49) becomes a tested invariant
   rather than an accident. Note the standing fragile-file memory on `reconcile_scan.py`: both
   1tz6l repairs there were channel-boundary bugs; rerun its near-miss controls.
8. Non-Claude hosts are out of scope for rendering but the design must not preclude equivalent
   surfaces later (Cursor settings, etc.).

## Scope

**Problem statement:** wavefoundry MCP permission allowlists are hand-maintained per repo, go
stale on tool renames, and interrupt lifecycle flows; the framework renders the settings surface
but does not own an allowlist block, and any fix must not create an agent-driven permission
escalation channel.

**In scope:**

- `render_platform_surfaces.py` (provenance-tracked permissions merge for `.claude/settings.json`;
  the `wf_sync_surfaces` render path excludes permissions, and the boundary is stated as
  operator-approved and host-enforced rather than structurally unreachable by an agent, since
  `wf_upgrade` is agent-callable and its orchestration does render, bounded to the read tier)
- The new lightweight roster module (name + tier) + parity test against `register_mcp_surface`
- `reconcile_scan.py` channel split for renderer-provenance entries (with near-miss controls)
- Upgrade output: explicit permissions-delta line; phase-ordering test (render before scan)
- Tests: provenance merge (operator wavefoundry-named rule survives; retired renderer rule pruned),
  roster-derivation rename self-heal, tier partition, agent-path negative, ordering invariant
- Docs/seed companions (seed gate): seed-050 (:61, :322, :335, :353 settings-seeding sections),
  seed-160 (:33, :74 host-rules prose), `docs/specs/mcp-tool-surface.md:858`,
  `docs/agents/platform-mapping.md` (rendered-surface row), rendered prompt surfaces reconciled

**Out of scope:**

- Editing `.claude/settings.local.json` (host-local; stays operator-owned, reported via
  `host_permission_flags`)
- The Claude Code auto-mode classifier's behavior (external)
- Rendering permission surfaces for non-Claude hosts (follow-up)

## Acceptance Criteria

- [x] AC-1: An upgrade/install render produces the read-only-tier allowlist in
  `.claude/settings.json` matching the roster; re-rendering with no interleaved writers is
  byte-stable, and rendering after a host or operator write preserves their entries
  value-identically under canonical re-serialization.
- [x] AC-2: A simulated tool rename in the roster updates the rendered entries on the next
  upgrade/install render with no renderer code edit; retired renderer-emitted rules are pruned via
  provenance while an operator-authored rule naming a wavefoundry tool survives.
- [x] AC-3: `wf_sync_surfaces(mode='run')` leaves `permissions` content untouched (pinned by test
  at both source and behavior level). The surrounding boundary is **operator approval plus host
  enforcement, not structural agent-unreachability**, and is documented that way after delivery
  review: `wf_upgrade` is an ordinary agent-callable MCP tool whose first phase passes the render
  switch, so an agent can trigger a render, bounded to the READ tier because the write tier
  requires the operator knob and `wf_upgrade` is itself write-tier and therefore cannot allowlist
  itself or self-perpetuate; passing the include-permissions switch to the renderer through the
  `wf` dispatcher is an accepted residual outside the threat model, since an agent with
  unrestricted shell access can write `.claude/settings.json` directly and the switch grants it
  nothing new. The mutating tier renders only when the operator-owned knob is set (pinned by
  test: clearing the knob prunes the write-tier rules again), and that knob's home is operator
  territory by HOST enforcement plus prompt policy, not by the framework: the framework's own
  pre-edit guard on `.claude/settings.json` is `framework_edit_allowed`, which the agent-callable
  gate tool can open, so writing the knob takes the same capability as writing the rendered rules
  by hand.
- [x] AC-4: The upgrade output names the permissions delta as an explicit consent line; the
  reconciliation scan distinguishes renderer-provenance entries (self-heal guidance) from
  operator-territory entries (edit guidance), with near-miss controls, and the render-before-scan
  ordering is a tested invariant.
- [x] AC-5: Roster/registration parity test passes; docs and seed companions updated
  (seed-050, seed-160, mcp-tool-surface.md:858, platform-mapping.md); docs-lint passes; full
  framework suite passes.

## Tasks

- [x] Decide at Prepare: provenance mechanics (evaluate the `render_claude_settings` value-marker
  pattern first), the operator knob's home, and reload-survivor roster membership
- [x] Extract the roster module with tier data; add the registration parity test
- [x] Implement the provenance-tracked permissions merge on the upgrade/install path only
- [x] Implement the reconcile_scan channel split + upgrade consent line + ordering test
- [x] Update seed/docs companions under the seed gate; re-render surfaces
- [x] Run the full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                              |
| ---------- | ----------- | ---------- | -------------------------------------------------- |
| design     | implementer | —          | Provenance mechanics + knob home + roster shape    |
| impl       | implementer | design     | Renderer merge, roster module, scan split, tests   |
| docs       | implementer | impl       | Seed/spec/platform-mapping companions              |


## Serialization Points

- `render_platform_surfaces.py` and `reconcile_scan.py` (coordinated: channel split depends on
  provenance shape); seed edits under `seed_edit_allowed`

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (:858 host-rules contract; in scope). No `docs/architecture/`
boundary or flow doc describes host permission surfaces; audit again at Prepare after the knob-home
decision.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-3 | required | Council P1: the change must not create an agent permission-escalation channel |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-31 | Prepare-time decisions recorded (provenance key, knob home, roster shape, caller switch); Change Status set to implementing | Decision Log rows dated 2026-07-31 (implementation) below |
| 2026-07-31 | Roster module extracted (`mcp_tool_roster.py`, 84 tools: 42 read / 42 write) and provenance-tracked permissions merge implemented (`render_claude_permissions`, `--include-permissions` switch default OFF); upgrade + install orchestrations pass the switch, `run_sync_surfaces` does not | `mcp_tool_roster.py`; `render_platform_surfaces.py` (`PERMISSIONS_PROVENANCE_KEY`, `render_claude_permissions`, `parse_args`, `main`); `upgrade_wavefoundry.phase_surface_rendering`; `setup_wavefoundry._run_render_platform_surfaces`; `server_impl.run_sync_surfaces` invariant docstring |
| 2026-07-31 | Renderer tests green: provenance merge (byte-stable re-render, value-identical operator/host preservation, rename self-heal + operator wavefoundry-named rule survival, knob-gated write tier, agent-path negative, corrupt-file no-op), roster/registration AST parity, sync-surfaces source-level negative with positive controls | `tests/test_render_platform_surfaces.py` `ClaudePermissionsRenderTests` / `SyncSurfacesNeverRendersPermissionsTests` / `RosterRegistrationParityTests`; module run: 78 tests OK |
| 2026-07-31 | reconcile_scan three-channel split implemented with near-miss controls; upgrade consent line + `permissions_delta` / `renderer_provenance_flags` summary fields; render-before-scan ordering pinned; full test_reconcile_scan rerun (fragile file) | `reconcile_scan.py` (`renderer_provenance_rules`, `scan_repo_channels` 3-tuple); `tests/test_reconcile_scan.py` `RendererProvenanceChannelTests` / `UpgradeRenderBeforeScanOrderingTests` (38 tests OK); `tests/test_upgrade_wavefoundry.py` `PermissionsRenderConsentTests` (381 tests OK); `tests/test_setup_wavefoundry.py` argv pin |
| 2026-07-31 | Docs/seed companions updated under the seed gate and reconciled to rendered prompt surfaces; docs-lint pass | seed-050 settings sections; seed-160 :33 rename prose + host-rules three-channel rewrite; `docs/prompts/upgrade-wavefoundry.prompt.md`; `docs/specs/mcp-tool-surface.md` (`wf_sync_surfaces` entry + summary-block contract); `docs/agents/platform-mapping.md` rendered-surface section; `wf_validate_docs` passed |
| 2026-07-31 | First full-suite run showed 1 failure in the server-tools batch; investigated: the failing test is `test_repeated_warm_estimator_and_projection_budgets` (warm p95 perf budget, 47ms vs 25ms) failing only under machine load; passes in isolation and in two subsequent full runs. Investigation also exposed spurious roster-parity warnings on the hot-reload path (runner survivor already registered) and stub registrations; hardened the check (runner tools excluded from both sides, empty registered set skipped) | reproduction: paired `test_server_tools test_server_context_efficiency` run under load; fix in `server_impl.register_mcp_surface` parity block; warning count 0 on rerun |
| 2026-07-31 | Full framework suite green in the foreground; Change Status set to implemented | `run_tests.py`: Ran 6605 tests across 61 files, OK |
| 2026-07-31 | Delivery-review docs repair pass (findings F4 seed-050 drop procedure, F6 AC-3 overclaim, F7 knob-space claim, F5-doc first-render timing, F8-doc hand-over procedure, F9 stale duplicate contract, F10 changelog, plus the docs P3 list). seed-050: accurate rule-removal mechanism (deny entry, clearing the write knob, or de-provenancing which converts to operator-owned rather than suppressing), full 42-tool write-tier enumeration with the all-or-nothing consequence for `wf_close_wave` and both gates, boundary restated as operator-approved plus host-enforced naming `wf_upgrade` and the dispatcher residual, first-render timing with the old-code window, hand-over procedure for repos that already carry the rules. seed-160: same paragraph in the host-rules section plus a rendered-allowlist line in the verification checklist. Rendered upgrade prompt: same paragraph, and the second stale copy of the reconciliation-scan contract deleted in favor of the canonical section. `mcp-tool-surface.md`: `wf_sync_surfaces` boundary honesty, permissions-delta field shape, `Permissions delta` output line name, `renderer_provenance_flags` in phase semantics. `platform-mapping.md` render-boundary + timing paragraphs. CHANGELOG `[1.15.0]` **Added** bullet | seed-050 Claude Code permissions block (edited under `seed_edit_allowed`, closed immediately after); seed-160 host-rules paragraph + verification checklist; `docs/prompts/upgrade-wavefoundry.prompt.md`; `docs/specs/mcp-tool-surface.md` (`wf_sync_surfaces`, summary-block contract); `docs/agents/platform-mapping.md`; `CHANGELOG.md`; `wf_validate_docs` pass |
| 2026-07-31 | Cross-agent coordination notes for this repair pass: the spec is written to the POST-repair consent shape (top-level `permissions_added` / `permissions_removed` lists plus a scalar `permissions_changed`) rather than the delivered `permissions_delta` dict, and the first-render-timing prose is written to the new-code backstop landing in the upgrade's index-refresh phase. Both belong to sibling repair agents; reconcile field names and backstop wording before close | this Progress Log row; spec summary-block paragraph; F1 / F5 repair owners |
| 2026-07-31 | Reverification cycle 2, repair pass. Three defects in this change doc's scope. (1) `permissions-backstop-unreachable-on-default-upgrade-path`: the first-pass backstop had exactly one call site, guarded by `args.update_index`, which an ordinary upgrade never passes; added a second, default-path call site in main()'s `if args.cleanup:` branch (the sole caller of `phase_cleanup`, mirroring the `_ensure_lifecycle_policy_backstop` two-site precedent), placed before `phase_cleanup` so the persisted delta still reaches the operator consent line, and gated on lock presence so a lock-less `--cleanup` never mutates a committed file outside an upgrade. Every reverified property preserved: permissions-only, idempotent, fail-safe, `--include-permissions` still the single gate. (2) `provenance-span-matches-any-allow-array`: replaced the depth-blind key scan with a position-tracking scan; `allow` must now be the direct child of the TOP-LEVEL `permissions` object and the provenance array must be top-level, so a foreign `somePlugin.config.allow` stays operator-side. (3) `renderer-docstring-retains-structural-overclaim`: the `render_claude_permissions` docstring and the In-Scope bullet above no longer claim agent-reachable renders are structurally unable to widen permissions; both now state the operator-approved, host-enforced boundary and name `wf_upgrade` as an agent-callable path that does render, bounded to the read tier. Timing prose in seed-050, seed-160, the rendered upgrade prompt and `platform-mapping.md` updated to name the cleanup phase as the always-reached site (the CHANGELOG bullet is phase-agnostic and was already true) | `upgrade_wavefoundry.py` main() `if args.cleanup:` branch + `_ensure_rendered_permissions_backstop` docstring; `reconcile_scan.py` `_json_key_value_spans` / `provenance_governed_spans`; `render_platform_surfaces.py` `render_claude_permissions` docstring; seed-050 / seed-160 (under `seed_edit_allowed`, closed immediately after); `docs/prompts/upgrade-wavefoundry.prompt.md`; `docs/agents/platform-mapping.md`. Tests: `PermissionsRenderBackstopTests::test_default_upgrade_path_reaches_the_backstop` (AST guard-chain), `::test_cleanup_invocation_really_renders_the_block` (behavioural `main(['--cleanup'])`), `::test_cleanup_without_an_upgrade_lock_renders_nothing` (gate control), `RendererProvenanceChannelTests::test_foreign_array_named_allow_stays_operator_side`, `::test_governed_spans_are_positional_not_key_named`. Mutation-checked: removing the cleanup call site fails the two new reachability tests; removing the lock gate fails the control; restoring the old span scanner fails both new span tests and no others |


## Decision Log


| Date       | Decision                                     | Reason                                                                                             | Alternatives                                                                                    |
| ---------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 2026-07-31 | Derive from a new roster module; tier writes as operator-gated opt-in | Renames self-heal; readOnlyHint is deliberately false on retrieval tools so a dedicated tier attribute is required; teams may want prompts on ledger writes | Hardcoded list (rejected: the stale-rename class); allowlist everything by default (rejected: removes deliberate review friction); derive tier from readOnlyHint (rejected: falsifies MCP semantics or excludes the retrieval tier) |
| 2026-07-31 | Permissions rendering only on the upgrade/install path; agent-reachable renders never touch permissions | Council P1: wf_sync_surfaces is agent-invocable, and the repo doctrine forbids agent self-editing of allow rules; the escalation channel must be closed structurally | Allow agent renders with knob in workflow-config (rejected: agent-editable knob = self-granted permissions) |
| 2026-07-31 | Provenance-tracked set-merge, not name-prefix pruning or a side namespace | Rules are honored only inside permissions.allow; the host itself rewrites the file; prefix pruning would delete operator-authored wavefoundry rules | Dedicated key namespace (rejected: host never reads it, zero effect); marker comments (impossible in JSON); prefix ownership (rejected: deletes operator rules) |
| 2026-07-31 | Rendering into the committed file (vs an operator-applied artifact) stays the default, pending Prepare | Self-heal-on-upgrade is the point; the consent tradeoff is mitigated by the explicit upgrade diff line and git review of the committed file | `wf` subcommand emitting an allowlist the operator applies on request (kept as the documented fallback if Prepare finds tier-1 consent insufficient) |
| 2026-07-31 | Provenance mechanics: dedicated top-level `wavefoundryManagedAllow` key listing exactly the allow entries the renderer emitted; merge prunes only claimed-and-no-longer-desired entries, appends missing desired entries (sorted), and NEVER claims a pre-existing entry, so an operator rule naming a wavefoundry tool survives even a later roster retirement | Evaluated the `render_claude_settings` value-marker ownership pattern first as the plan requires: it keys ownership off a marker substring inside each hook command value, but allow rules are bare strings honored only inside `permissions.allow`, so there is no marker slot, and name-prefix inference is banned; a provenance list of exact emitted values is the only shape that keys ownership without inspecting values | Value markers (no slot in bare rule strings); prefix ownership (banned, deletes operator rules); side namespace (host never reads it) |
| 2026-07-31 | Operator knob home: operator-authored top-level `wavefoundryAllowWriteTools: true` in `.claude/settings.json`, outside the provenance key; the renderer only reads it | `.claude/settings.json` is already doctrine-recognized operator territory (reconcile_scan `HOST_PERMISSION_FILES`; agents cannot self-edit it under host auto-mode guards), the knob persists across upgrades and is git-reviewable; defense in depth: even a flipped knob takes effect only on the operator-run upgrade/install render, whose output names the permissions delta as the consent line | `wf` CLI flag (rejected: non-persistent, silently reverts the tier on the next upgrade unless re-passed); workflow-config or any rendered block (rejected by the council P1: agent-editable) |
| 2026-07-31 | Reload-survivor roster membership: runner-registered tools (`wf_reload_mcp`) ARE roster members (write tier) and are listed in `RUNNER_TOOLS` so the implementation-side parity check excludes them | They are part of the published agent-facing tool surface and need allow rules like any other tool; they are registered by `server.py` after `register_mcp_surface` returns, so the impl-side comparison must exclude them while the AST parity test censuses both registration sites | Exclude from roster (rejected: their allow rules would go stale on rename with no self-heal) |
| 2026-07-31 | Roster consumption on the server side: `register_mcp_surface` runs a fail-safe parity check (stderr warning on drift, never raises); the hard gate is the AST parity test | A hard startup assertion would deny the entire MCP server on any roster drift, which is worse than the defect it guards against; the warning gives runtime signal while the test blocks the merge | Hard RuntimeError at registration (rejected: availability); test-only with no runtime consumption (rejected: plan asks both consumers to touch the roster) |
| 2026-07-31 | Caller distinction: new renderer argparse switch `--include-permissions`, default OFF; `upgrade_wavefoundry.phase_surface_rendering` and `setup_wavefoundry._run_render_platform_surfaces` pass it; `server_impl.run_sync_surfaces` does not, and the negative is pinned at source level (server_impl.py never names the switch) plus a renderer default-off behavioral test | An explicit argv switch is visible in every spawn site and testable without importing the MCP runtime; the source-level pin makes the escalation channel structurally detectable with positive controls on the two operator paths | Environment variable (rejected: inherited implicitly by child processes, exactly the laundering risk); separate script entry point (rejected: heavier, same properties) |
| 2026-07-31 | Delivery repair: describe the render boundary as **operator-approved plus host-enforced**, and name `wf_upgrade` explicitly as an agent-reachable render path, instead of claiming permissions rendering is structurally unreachable by agents | The delivery review disproved the stronger claim: `wf_upgrade` is an ordinary agent-callable MCP tool whose first phase passes the render switch. The property that is true and still sufficient is bounded impact: an agent-triggered upgrade emits at most the READ tier, because the write tier needs the operator knob and `wf_upgrade` is itself write-tier, so it cannot allowlist itself or self-perpetuate. The underlying design claims that ARE true (the tested `wf_sync_surfaces` negative, switch default OFF) are left intact | Keep the structural-unreachability wording (rejected: false, and it is the exact class of claim the council P1 was about); remove or gate `wf_upgrade`'s agent callability (rejected: out of scope, and it would break the ordinary agent-driven upgrade flow for no capability gain, since the read tier is the distributed default anyway) |
| 2026-07-31 | Delivery repair: record the `wf render-surfaces --include-permissions` dispatcher path as an **accepted residual with its boundary stated**, in the shipped docs, rather than omitting it | The `wf` dispatcher forwards argv verbatim, so an agent with unrestricted shell access can pass the switch; that same agent can already write `.claude/settings.json` directly, so the switch grants it nothing new. Naming the residual keeps the threat-model boundary auditable and stops a future reader from re-deriving the gap as a fresh finding | Omit it (rejected: the docs would again claim more than the code guarantees); filter argv in the dispatcher (rejected: it is a generic passthrough, and the renderer can be invoked directly by the same actor, so the restriction would be decorative) |
| 2026-07-31 | Delivery repair: scope the knob-home claim to a **host guarantee plus prompt policy**, not framework enforcement | `.claude/settings.json` is operator territory because the HOST prompts before an agent edits it. The framework's own pre-edit guard there is `framework_edit_allowed`, which the agent-callable gate tool opens, so "outside agent-editable space" described the host, not the framework. Writing the knob needs exactly the same capability as writing the rendered rules by hand, so the knob is not a weaker link than the file: the claim was wrong, not the design | Harden by making host permission files an unconditional pre-edit deny instead of a gate-unlockable path (not taken in this wave: it changes the guard model for every framework edit surface and needs its own change doc; the doc scoping was mandatory either way); leave the wording (rejected: overclaims framework enforcement) |
| 2026-07-31 | Architecture-doc audit re-run after the knob-home decision: no `docs/architecture/` boundary or flow doc describes host permission surfaces; the contract lives in `docs/specs/mcp-tool-surface.md` + `docs/agents/platform-mapping.md`, both updated | Matches the plan's Affected Architecture Docs note; creating a new architecture doc for one rendered file would duplicate the spec | New architecture doc (rejected: duplication) |


## Risks


| Risk                                                            | Mitigation                                                                       |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Agent-driven permission escalation through a render entry point  | Bounded, not eliminated: rendering is confined to the upgrade/install path with a pinned negative test on wf_sync_surfaces, and the agent-reachable `wf_upgrade` route emits at most the read tier because the write tier needs the operator knob and wf_upgrade cannot allowlist itself; the knob's protection is host enforcement plus prompt policy |
| Host rewrites of settings.json break stability assumptions       | Provenance set-merge; byte-stability claimed only with no interleaved writers      |
| Rendered allows loosen a team's intended prompting posture       | Read-only tier only by default; explicit upgrade consent line; deny always wins (host semantics) |
| reconcile_scan channel split reintroduces boundary bugs          | Fragile-file memory heeded: near-miss controls rerun; both channels tested          |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
