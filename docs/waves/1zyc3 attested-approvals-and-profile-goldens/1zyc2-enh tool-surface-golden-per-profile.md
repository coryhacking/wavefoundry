# The Tool-Surface Golden Covers Only The Shipped Declaration

Change ID: `1zyc2-enh tool-surface-golden-per-profile`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-06
Wave: 1zyc3 attested-approvals-and-profile-goldens

## Rationale

Downstream request (Waveforge, follow-up e13693a9): a golden tool-surface fixture per declaration profile. `tests/test_tool_surface_golden.py` boots the real server under `apply_base_declaration` and compares the served surface with `tests/fixtures/tool-surface-golden.json`, so it pins only the shipped empty declaration. A distribution's served surface (aliases, mapped parameters, hidden names, extension tools, overrides) is checked only by the narrower core-parameter comparison (`core_schema_drift`), so an unintended change to it goes unnoticed.

## Requirements

1. A per-profile golden lives at `tests/fixtures/tool-surface-golden/<profile>.json` for each profile asset under `tests/fixtures/profiles/` whose `mcp_tool_extensions` entry declares anything (today only `declared`; a distribution's own asset, active or not, is covered the same way). The shipped `tests/fixtures/tool-surface-golden.json` and its test are unchanged.
2. A separate test class (not a subclass of the shipped golden tests) iterates those assets with one `subTest` per asset. For each it boots the server exactly as the shipped test does, under `apply_base_declaration(self, **declaration)` where `declaration` is that asset's `mcp_tool_extensions` entry alone (shipped-empty plus that asset, never layered on the active asset), with JSON lists coerced to the tuples the declaration module requires (as `record_layout_support.apply_profile` does), and with the asset's record-layout and vocabulary parts ignored. It serializes the served surface with tiers from `mcp_tool_roster.all_tool_tiers()` and compares it with the golden through the existing `check_golden`.
3. `WF_UPDATE_TOOL_SURFACE_GOLDEN=1` rewrites the shipped golden and every per-profile golden, byte-stable as today; a declaring asset without a golden file fails with a message naming the file and the flag.
4. An asset whose declaration is invalid fails its subtest with the declaration problems rather than producing a golden.
5. `docs/contributing/build-and-verification.md` and `docs/architecture/testing-architecture.md` (where the golden and its flag are documented) describe the per-profile files. CHANGELOG gets one Added bullet under `## [1.29.0]`.

## Scope

**Problem statement:** a distribution's served tool surface has no golden.

**In scope:**

- The per-profile golden test, fixtures for the shipped profile assets, regeneration, docs, CHANGELOG.

**Out of scope:**

- Changing the shipped golden or the core-parameter comparison.
- Golden files for profiles that declare no tools.

## Acceptance Criteria

- [x] AC-1: The `declared` profile has a committed golden that includes its aliases with their tiers and the mapped alias's renamed and pinned parameters, and the test passes in the default suite.
- [x] AC-2: Changing a declared alias's mapping, tier or target, or a core tool's schema as served under the profile, fails the test with a per-tool diff; regeneration with the flag rewrites only golden files and is byte-stable on a second run.
- [x] AC-3: A profile asset that declares tools but has no golden file fails with a message naming the file and flag; an invalid declaration fails with its problems; the shipped golden test is unchanged.
- [x] AC-4: Docs and the CHANGELOG bullet describe the per-profile goldens; the change's own tests pass and no failure elsewhere is attributable to this change.

## Tasks

- [x] Per-profile boot, serialization with roster tiers, comparison
- [x] Fixture for `declared` (and any other declaring asset)
- [x] Regeneration and missing-file message
- [x] Docs and CHANGELOG
- [x] Tests (mutation of a declared mapping)

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| profile-goldens | implementer | attested-names (golden regeneration) | regenerate goldens after 1zyc1's schema change |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_tool_surface_golden.py`, `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden/`, `docs/contributing/build-and-verification.md`, `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` documents the tool-surface golden; add the per-profile files.

## Platform Behavior

Test-only; fixtures are written with LF and UTF-8 on every platform, as the shipped golden is.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the requested golden |
| AC-2 | required | it must catch real drift and regenerate cleanly |
| AC-3 | required | clear failures; shipped golden untouched |
| AC-4 | required | docs and release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-06 | Implemented: `ProfileToolSurfaceGoldenTests` (separate class, one subtest per declaring asset, `base_declaration` per boot, tuples coerced, tiers from `all_tool_tiers()`, `check_golden`); `tests/fixtures/tool-surface-golden/declared.json` generated after 1zyc1's golden change; invalid declarations fail with `ExtensionDeclarationError` problems or the boot refusal; docs and CHANGELOG | scratch copy: test_tool_surface_golden 22 OK (shipped golden unchanged by this change); drift proven through the declaration (renamed mapping, dropped pin, alias retargeted to a write tool for tier and target) and the served registry (core schema), never shipped code; mutation probes: corrupted `declared.json` fails with per-tool diff, removed golden fails naming file and flag, dropped tuple coercion fails |
| 2026-10-06 | Gapfill: shell grep/sed used to read `declaration_support.py`, `record_layout_support.py` and the profile assets in full | implementer session |
| 2026-10-06 | Readiness review folded in: tuple coercion of JSON lists (N6); each golden boots shipped-empty plus that asset alone with layout parts ignored; separate test class with a subtest per asset (N7); "plus the active asset" removed as redundant | readiness review |
| 2026-10-06 | Planned from Waveforge Part 3 #5 | map of `test_tool_surface_golden`, profile assets and `_install_served_names` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-06 | Full per-profile surface, not a delta against the shipped golden | a full file is directly reviewable and catches everything served under the profile; one flag regenerates all files after a core schema change | delta files |
| 2026-10-06 | Iterate declaring profile assets in the default suite | catches drift without a `--profile` run; a distribution marks its own asset active | golden only under `--profile` |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Every schema change now also rewrites profile goldens | one flag regenerates all; diffs are reviewable |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
