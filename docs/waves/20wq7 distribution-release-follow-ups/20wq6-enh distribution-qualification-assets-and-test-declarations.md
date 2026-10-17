# Distribution qualification assets, test declarations and lookup wording

Change ID: `20wq6-enh distribution-qualification-assets-and-test-declarations`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-17
Wave: `20wq7 distribution-release-follow-ups`

## Rationale

A downstream distribution reported three bounded problems against `2452c73f` (its items K5, K6 and G19). First, the compatibility qualification scope refuses any profile asset that the upstream coverage inventory does not list, so a distribution that keeps its own profile JSON beside ours always falls back to a full profile run, and the only way out is editing an upstream-owned inventory. Second, one lifecycle test class still builds its MCP server from whatever extension declaration the checkout ships, so a distribution whose declaration overrides `wf_close_wave` runs the shipped-default assertions against its own override (the other two tests it named were repaired by wave 20st7). Third, the threat model's Tensorwell paragraph says the controlled executable lookup excludes repository and current-directory entries, while the code never refuses the working directory there.

This change removes only the asset-set refusal. A fork that also edits pinned coverage contracts (`vocabulary_profile.py`, `record_paths.py`, `mcp_tool_extensions.py`) still falls back to a full profile run, as it should, and at HEAD the upstream inventory itself is stale (it classifies 188 of 200 workers and four contract digests no longer match), so the upstream tree falls back to full as well. Refreshing the inventory is a separate decision.

## Requirements

1. **Declared distribution profile assets.** `tests/record_layout_support.qualification_scope` accepts an optional distribution-owned list at `tests/fixtures/profiles/qualification/distribution-assets.json` under the scripts folder. Its shape is exactly `{"schema_version": 1, "assets": {"tests/fixtures/profiles/<name>.json": "<64 lowercase hex sha256>"}}`. When the file is absent, behavior is unchanged. When present, the asset-set check accepts the on-disk profile JSON set if it equals the inventory's `profile_assets` plus the declared assets. Every declared path must be a direct child of `tests/fixtures/profiles/` (no nested folder, no `..`, no backslash, no drive or absolute form), end in `.json`, be absent from the inventory's `profile_assets`, not be named `second.json` or `declared.json`, and its on-disk bytes must match the declared digest. Any violation, an unreadable or malformed list, a list over 1 MiB, an unexpected key, a wrong schema version or a non-hex digest returns the full scope, as every other uncertainty does. The existing contract-binding check (`unbound profile asset`) applies to the inventory's `profile_assets` only. A declared asset can be the active base layer that `expected_profile` applies under every profile, so it is an input to profile runs; its bytes are bound by each qualification report's source hash, which covers the whole framework tree including `tests/fixtures`. The scope dictionary is unchanged.
2. **Lifecycle test owns its declaration.** `RetainedUpgradePreviewTests` in `tests/test_server_tools_lifecycle.py` installs the shipped base declaration with `declaration_support.apply_base_declaration(self)` at the start of `setUp`, before `build_server`, so its registered `wf_prepare_wave`, `wf_close_wave` and `wf_pause_wave` entries are the core tools whatever the checkout declares. Cleanups run last-in-first-out, so the handler closes before the declaration is restored. Its existing alias and override test keeps its own nested `base_declaration(...)`. No assertion is weakened or removed.
3. **Threat-model wording.** In `docs/architecture/threat-model.md`, the Tensorwell automatic-start sentence says the controlled PATH lookup for `tensorwell` skips empty and relative entries and refuses an entry or candidate that resolves inside the target repository after following links. It no longer mentions the working directory, which only setup's `uv` lookup refuses, and only when no target root is known. No other live doc or seed repeats the old wording; the closed wave `20njt` record keeps it as history.
4. **Docs.** `docs/contributing/build-and-verification.md` mentions the optional distribution asset list where it describes the coverage inventory, and corrects the classified-worker count it states.
5. **Platforms.** All items behave the same on Windows, macOS, Linux and WSL2. Declared paths use forward slashes, and digests are over on-disk bytes, so under Git `autocrlf` on Windows the distribution declares the digest of its checked-out bytes. The test change is a declaration patch and the wording changes are documentation. The executable-lookup code is unchanged.

## Scope

**Problem statement:** a distribution cannot declare its own profile assets, one test class assumes the shipped declaration, and the threat model overstates the Tensorwell lookup exclusion.

**In scope:** Requirements 1 to 5 and their tests.

**Out of scope:** refreshing or reclassifying the coverage inventory (including its stale digests), relaxing contract pinning for forks, any change to either executable lookup, other tests not named by the report, and items K3, K4, G13 and G14 from the same report, which the operator will plan separately. The release owner adds one CHANGELOG bullet for Requirement 1 under the next release section.

## Acceptance Criteria

- [x] AC-1: In the existing `CompatibilityCoverageTests` temporary scripts tree, a declared distribution asset with a matching digest keeps the `second` and `declared` scopes at `compatibility` with a scope dictionary equal to the one without it. Each of these returns `full`: a wrong digest, a non-hex digest, a declared asset missing on disk, one that repeats an inventory asset, one named `second.json`, a nested path `tests/fixtures/profiles/sub/x.json`, a `..` path, a backslash path, a non-`.json` path, an unexpected key, a wrong schema version, malformed JSON and a list over 1 MiB. With the list present, an additional unlisted asset still returns `full`.
- [x] AC-2: `RetainedUpgradePreviewTests` passes under the default, `second` and `declared` profiles with zero skips. In a scratch clone, an added extension module registers `wf_close_wave` and the clone's `mcp_tool_extensions.py` declares it as an override. Running the class by name, the unrepaired class fails in `test_registered_actual_lint_previews_are_read_only_for_default_and_positional_modes` (and any other test reaching the overridden close) because `read_only_preview` is absent from the override's result, and the repaired class passes.
- [x] AC-3: The threat-model sentence matches `tensorwell_client._controller`, and nothing in it contradicts `setup_index._trusted_path_uv`; full docs validation passes.
- [x] AC-4: The focused files pass under the default profile, and the wave's single final whole-suite run (shared with 20qvs AC-5) passes with a fresh green receipt.

## Tasks

- [x] Add the declared distribution asset list to `qualification_scope`.
- [x] Add the AC-1 tests to `tests/test_profile_support.py`.
- [x] Install the base declaration in `RetainedUpgradePreviewTests.setUp` and run the AC-2 control in a scratch clone.
- [x] Correct the threat-model sentence and the build-and-verification inventory text.
- [x] Run focused files under default, second and declared; the whole suite runs once at the end of the wave.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| scope-and-tests | implementer | none | Requirements 1 and 2 |
| docs | implementer | none | Requirements 3 and 4 |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/test_profile_support.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `docs/architecture/threat-model.md`
- `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` (Requirement 3). No boundary or flow change otherwise.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The distribution-facing behavior and its fail-closed edges. |
| AC-2 | required | Proves the test no longer depends on the checkout's declaration. |
| AC-3 | required | The security documentation must match the code. |
| AC-4 | required | Release qualification needs a green tree. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-17 | Qualification on the final tree, one run at a time: canonical default `--no-cache` 11,890 tests / 200 files / 12 skips, receipt inputs_hash `fc8af1b262ad8b54c413e8155d3c62f8d9f8d23f7a4ed8e02b234f4351a49da7`; `--qualify-profile second` 11,882 / 200 / 28 skips; `--qualify-profile declared` 11,890 / 200 / 12 skips; both scopes `full fallback: coverage unproven`. `qualification_report.py --compare` passes for both (second: 16 default-only skips; declared: equal). The new gate, called read-only on the real tree, lists all three as passed with no exception. A first attempt was invalid: a reviewer's concurrent focused run held the runner lock and raced the live-tree build's generated files during a profile copy, and the declared run exposed two wave-caused census failures (a timed git call outside the tree-kill routing census, and a patched loader not asserted), both fixed and confirmed by code and security before the rerun. | scratchpad 20wq7-qual-{default,second,declared}.log; .wavefoundry/cache/qualification/{default,second,declared}.json |
| 2026-10-17 | Implemented. `qualification_scope` accepts the optional distribution-owned list through `_distribution_profile_assets`; two new `CompatibilityCoverageTests`; `RetainedUpgradePreviewTests.setUp` calls `apply_base_declaration`; threat-model Tensorwell sentence and build-and-verification inventory paragraph corrected. Focused: `test_profile_support` 82/82; `test_server_tools_lifecycle` 640 with 2 pre-existing skips under default and declared on a repaired clone, identical to HEAD (an earlier two-file run reported 639 and 5 skips across both files, not reproduced). AC-2 control (scratch clone, profile `closeover` overriding `wf_close_wave`): repaired 640 OK; unrepaired fails exactly `test_registered_actual_lint_previews_are_read_only_for_default_and_positional_modes` and `test_close_reports_new_unpublished_secrets_in_same_lint_pass` with `read_only_preview` absent. Mutants: digest and repeat-inventory guards killed; widening the path pattern is equivalent for scope outcome because the asset-set equality already refuses non-direct children (the pattern only keeps the digest read inside the profiles folder); the 64-hex and name rules are likewise redundant with digest equality and the inventory listing. Delivery finding DEL-2 (QA): the oversized control was invalid JSON, so it passed without the size bound; repaired to a valid list padded past 1 MiB, size-bound mutant now killed. Gapfill: shell reads and Python edit scripts were used because the targets and anchors were fixed by readiness. | scratchpad 20wq7-ctl-closeover-{repaired,unrepaired}.log, 20wq7-mutants.log, 20wq7-mutants2.log; events.jsonl DEL-2 |
| 2026-10-17 | Readiness corrections folded in before approval: contract-binding check limited to inventory assets; declared assets described as bound by the report source hash; inventory refresh dropped (four digests already stale, 188 of 200 classified); threat-model wording limited to the Tensorwell lookup; build-and-verification text added; AC-1 and AC-2 controls made specific. | Readiness reports from red-team, code and architecture, QA, security, docs-contract and release |
| 2026-10-17 | Planned from a distribution report against `2452c73f`, items K5, K6 and G19. Checked at HEAD `3c6416d6`: the asset refusal and the lifecycle test remain; the core-read and legacy-hook tests the report named were already repaired by wave 20st7; only the threat model carries the old lookup wording. | `record_layout_support.py` asset check; `test_server_tools_lifecycle.py` `RetainedUpgradePreviewTests`; `setup_index.py` refused-root line |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-17 | A separate distribution-owned list, not edits to the upstream inventory. | A distribution then never edits an upstream-owned file, and upgrades never conflict on it. | Relax the exact-set check to a subset check (rejected: an unlisted asset would pass silently). |
| 2026-10-17 | Declared assets stay out of the scope dictionary. | A declared asset can be the active base layer, so it is an input, but each report's source hash already covers its bytes and `compare` rejects any source-hash difference. | Add a `distribution_assets` digest map to the scope (red-team's alternative; not needed for binding, adds a second record of the same bytes). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A declared asset changes profile behavior without a coverage contract. | Its bytes are bound by the report source hash; a repeat of an inventory asset or of `second.json`/`declared.json` is refused. |
| The base declaration in setUp hides a real override defect. | The class tests core behavior; distribution overrides are covered by the declared-profile golden tests, and the class's own override test keeps its nested declaration. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
