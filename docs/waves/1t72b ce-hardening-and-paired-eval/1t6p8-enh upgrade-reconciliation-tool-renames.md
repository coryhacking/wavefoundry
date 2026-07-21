# Upgrade Reconciliation Covers the MCP Tool Renames

Change ID: `1t6p8-enh upgrade-reconciliation-tool-renames`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

The 1.14.0 release renames 61 MCP tools (`wave_*` to `wf_*`/`memory_*`/`index_*`),
but the upgrade's retired-surface reconciliation scan consumes only the
bin-wrapper map from the 1.9.0 cutover. A target repo upgrading from 1.13.0
gets ZERO flags for its own docs, prompts, scripts, or host permission
allow-rules that still name `wave_close`, `mcp__wavefoundry__wave_validate`,
and the other old tool names — and stale allow-rules silently stop matching,
so every renamed tool call starts prompting. A same-day self-repo sweep proved
the hazard class is real: two live agent surfaces here still carried old
names. Additionally, the 1.13-to-1.14 hop cannot hot-reload across the rename
(the reload survivor itself was renamed), and no target-facing surface says a
full host restart is required.

## Requirements

1. **One canonical rename map**: `_RENAMED_MCP_TOOLS` (old name to new name,
   all 61 entries) lives co-located with `_RETIRED_SURFACE_REPLACEMENTS` in
   `render_platform_surfaces.py`, derived from the shipped rename record —
   never re-authored elsewhere. `reconcile_scan` imports it.
2. **Scan coverage**: the reconciliation scan flags old tool names in
   repo-authored files in two forms — the fully-qualified
   `mcp__wavefoundry__<old>` form and the bare `<old>` token form — with the
   new name as the suggestion. Existing channel semantics hold: hits in host
   permission/allow-rule files route to the operator-flag channel, everything
   else to the editable reconciliation list. The existing exclusion set
   applies.
3. **Config-key safety**: `wave_review` and `wave_implement` are legitimate
   workflow-config KEYS as well as old tool names. Their BARE token form is
   never flagged; only their `mcp__wavefoundry__` form is. This is asserted by
   test — a false rename instruction against workflow-config keys would break
   target configs.
4. **Memory-record history**: `docs/agents/memory/` joins the scan exclusions.
   Memory records quoting historical decisions legitimately name old tools,
   and the memory corpus has its own hygiene loop (validate/reconcile), not
   doc edits.
5. **Restart callout**: the upgrade seed states that when an upgrade renames
   MCP tools (the 1.14.0 `wave_*` rename), the upgrading session cannot
   hot-reload across the rename — the reload tool itself was renamed — so a
   full host restart (or fresh session) is required after the upgrade, and the
   old session's tool list is stale until then.
6. **Self-repo cleanliness**: the live scan on this repository reports zero
   editable-channel findings after the change (the two live agent-surface
   misses found in the sweep are fixed in this same change).

## Scope

**Problem statement:** the reconciliation scan is blind to the 1.14.0 tool
renames, and the rename's one-time restart boundary is undocumented on
target-facing surfaces.

**In scope:**

- The rename map + suggestion helper in `render_platform_surfaces.py`
- Scan patterns, config-key safety, and memory-dir exclusion in
  `reconcile_scan.py`
- The upgrade-seed restart callout (seed edit, gated)
- The two self-repo agent-surface fixes (persona + implementer journal
  standing line)
- Tests: canonical-oracle map validation, both pattern forms, both channels,
  config-key safety, exclusions, longest-name boundary correctness

**Out of scope:**

- Any tool aliasing or back-compat shims (1t3gs decided none)
- CHANGELOG/release-notes drafting (release mechanics, post-close)
- Auto-editing host permission files (operator-flag channel by design)

## Acceptance Criteria

- [x] AC-1: `_RENAMED_MCP_TOOLS` contains all 61 renames (the 1t3gs doc's "47" header undercounted its own table; the census oracle settled it) and is
      oracle-verified: every NEW name is a currently registered MCP tool and
      no OLD name is, asserted against the live registration census — the map
      cannot drift from the shipped surface.
- [x] AC-2: A doc naming `wave_close` is flagged with suggestion
      `wf_close_wave`; `mcp__wavefoundry__wave_validate` in
      `.claude/settings.local.json` routes to the host-permission channel;
      verified by test.
- [x] AC-3: Bare `wave_review`/`wave_implement` are NEVER flagged (config
      keys); their `mcp__wavefoundry__` forms ARE; `wave_index_build` does not
      match inside `wave_index_build_status`; verified by test.
- [x] AC-4: `docs/agents/memory/` and the existing exclusion set are
      respected; the live self-repo scan reports zero editable-channel
      findings; verified by test plus a live run.
- [x] AC-5: The upgrade seed carries the rename restart callout; docs-lint
      passes.
- [x] AC-6: Full framework test suite passes (6,048 tests across 56 files, OK, 2026-07-20; two isolated-verified perf-budget flakes under contention on earlier runs, disclosed).

## Tasks

- [x] Canonical rename map + suggestion helper
- [x] Scan patterns, config-key safety, memory-dir exclusion
- [x] Upgrade-seed restart callout (seed gate; rendered prompt synced)
- [x] Self-repo agent-surface fixes
- [x] Tests per AC; live self-repo scan
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| map+scan   | Engineering | —          | render_platform_surfaces.py + reconcile_scan.py |
| seed       | Engineering | map+scan   | Restart callout references the shipped behavior |


## Serialization Points

- Sixth late admission into wave `1t72b`; a third superseding delivery
  approval follows implementation.

## Affected Architecture Docs

`N/A` — upgrade-tooling extension confined to the scan module, its map source,
and one seed; no boundary or flow change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The map is only trustworthy oracle-anchored |
| AC-2 | required | The field-facing migration coverage |
| AC-3 | required | A false rename instruction against config keys breaks targets |
| AC-4 | required | History must not be flagged; self-repo must be clean |
| AC-5 | required | The restart boundary is the release's sharpest edge |
| AC-6 | required | Suite-green delivery gate |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-20 | Map (61 entries, derived from the shipped 1t3gs rename record), scan patterns (qualified + bare with config-key carve-out), memory-dir exclusion, seed + rendered-prompt restart callout, self-repo fixes (persona, implementer journal, spike script) all landed; 32 scan tests green | RenamedMcpToolScanTests |
| 2026-07-20 | Live self-repo scan proved the design end-to-end on first run: 2 editable-channel hits (an old spike script, fixed) and 2 HOST-channel flags — stale `mcp__wavefoundry__wave_review`/`wave_implement` allow rules in `.claude/settings.local.json`, correctly routed to the operator channel (agents must not self-edit permission files) | live scan output; the operator flags reported for manual edit |
| 2026-07-20 | The pre-channels self-host guard (`NoLiveReferenceToRetiredWrapperTests`) failed the suite on the two operator-owned allow-rule flags — it asserted BOTH channels empty. Scoped it to the editable channel per the channel design (host findings surface at upgrade time, never gate the suite on operator-owned files) and fixed its formatting to use the `matched` field | test_wf_cli.py guard update; suite rerun |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | The map holds 61 renames, not the 47 the 1t3gs header claimed | The census oracle (two-directional, against server_impl's registration AST plus server.py's reload survivor) confirmed all 61 mapped pairs; the historical header undercounted its own table | Trust the header (rejected: the oracle exists precisely because hand counts drift) |
| 2026-07-20 | Bare-token matching skips `wave_review`/`wave_implement`; only their `mcp__wavefoundry__` form flags | Both are legitimate workflow-config KEYS; a bare flag would instruct a config-breaking rename | Exclude workflow-config.json by basename instead (rejected: the names appear in prose about config too) |
| 2026-07-20 | `docs/agents/memory/` joins the scan exclusions | Memory records quote historical decisions and have their own hygiene loop (validate/reconcile) | Flag and let agents edit records (rejected: bypasses the memory lifecycle) |
| 2026-07-20 | The lookbehind `(?<![\\w.])` makes qualified-span masking redundant but it stays as defense in depth | An `_`-preceded bare token can never match, so `mcp__wavefoundry__wave_close` single-flags naturally | Rely on the lookbehind alone (kept the mask: two independent guards on a correctness property) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Hand-copied map drifts from the real tool surface (fixture-echo class) | AC-1 oracle asserts the map against the live registration census in both directions |
| Bare-token matching over-flags prose that mentions old names deliberately (migration guides) | The exclusion set already drops CHANGELOG/waves/journals/memory; remaining prose hits are genuine stale instructions |
| Alternation matches a shorter name inside a longer one | Longest-first alternation plus word-boundary; AC-3 pins the sharpest pair |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
