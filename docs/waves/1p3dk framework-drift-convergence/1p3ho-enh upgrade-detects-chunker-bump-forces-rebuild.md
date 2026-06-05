# Upgrade Detects Chunker Bump And Forces Rebuild

Change ID: `1p3ho-enh upgrade-detects-chunker-bump-forces-rebuild`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-05
Wave: TBD

## Rationale

Solaris field observation (2026-06-05): wave `1p3b9` shipped a `CHUNKER_VERSION` bump (`"22"` → `"23"`) as part of the chunker correctness work in `1p397`. The intent was that consumer indexes would auto-rebuild on next upgrade. After Solaris installed `1.5.0`, **their indexes were not rebuilt**.

Investigation (see CHANGELOG of session that diagnosed it) found two separate code paths for chunker-version-mismatch detection, only one of which actually rebuilds:

1. **Advisory path** (`wave_index_health`): compares `file_meta` against current; emits a `chunker_version_mismatch` diagnostic in the response. Does NOT rebuild.
2. **Rebuild path** (`indexer.build_index` lines 1917-1949): compares `meta.json` `chunker_versions` against current; when mismatch detected on a non-`--full` call, auto-escalates to full rebuild.

The rebuild path executes via `setup_index.py` (called by `wave_upgrade` Phase 4 — `upgrade_wavefoundry.py:964`), `wave_index_build` MCP tool, or a manual `setup_index.py` run. For Solaris to actually get the rebuild, **`setup_index.py` had to be called against the pre-existing project index**. Possible reasons the rebuild didn't happen:

- They skipped `wave_upgrade` entirely (manual unzip + render).
- Phase 4 ran but the auto-escalate is silent — Phase 4a (foreground/docs, blocking) was visible but Phase 4b (background/code, stdout/stderr to DEVNULL) failed invisibly.
- No post-condition check verifies "rebuild actually happened" after Phase 4 finishes.
- Operator monitoring the upgrade log saw no prominent "chunker version changed — full rebuild forced" message; the decision was buried inside `build_index`'s internals.

The framework's hardening response is to make the upgrade flow **explicit and verifiable** about chunker-version-driven rebuilds:

1. **Detect the bump at upgrade time** by reading old chunker_version from the consumer's pre-existing `meta.json` BEFORE extract and comparing it to the new pack's `chunker.py:CHUNKER_VERSION`.
2. **Route Phase 4 deterministically** — when bumped, run `phase_index_rebuild` (`--full`) instead of `phase_index_update`. No reliance on `build_index`'s internal auto-escalate.
3. **Surface the decision prominently in the upgrade log** so operators see *"chunker version 22 → 23 — full rebuild forced"* rather than discovering a silent escalate.
4. **Verify post-condition** by running `wave_index_health` after Phase 4 (or at minimum after Phase 4a, when synchronous results are available) and asserting no `chunker_version_mismatch` advisory remains. When the advisory remains, exit non-zero with actionable guidance.

The change is small (~50 LOC across `upgrade_wavefoundry.py` + a verification helper) and self-contained — no consumer-side breaking change, no schema change, no MCP tool surface change.

## Requirements

1. **Pre-extract version snapshot.** Before `phase_extract` runs, `upgrade_wavefoundry.py` reads the consumer's `.wavefoundry/index/meta.json` (when present) and captures both `chunker_versions` (per-layer dict) and the legacy scalar `chunker_version` (when only that key is present). Stored on `UpgradeContext` as `ctx.pre_extract_chunker_versions`.
2. **Post-extract version comparison.** After extract, the new pack's `chunker.py` is on disk at `.wavefoundry/framework/scripts/chunker.py`. The upgrade flow reads `CHUNKER_VERSION` from that file (via regex match — no Python import needed) and compares against `ctx.pre_extract_chunker_versions`. Stored as `ctx.chunker_version_bumped: bool` and `ctx.chunker_version_transition: (old, new)`.
3. **Phase 4 routing.** When `ctx.chunker_version_bumped is True`, `wave_upgrade`'s phase orchestration calls `phase_index_rebuild` instead of `phase_index_update`. The decision is logged prominently: `⚠  Chunker version changed: <old> → <new>. Forcing full index rebuild.`
4. **Post-Phase-4 verification.** After Phase 4a (docs index, blocking) returns, `wave_upgrade` calls `wave_index_health` against the project root and checks for any `chunker_version_mismatch` advisory on the docs layer. When the advisory is present, the upgrade exits non-zero with: `❌ Chunker version mismatch persists after rebuild. Run: python3 .wavefoundry/framework/scripts/setup_index.py --root <root> --full`. (Phase 4b/code is background — verification covers docs only since code is asynchronous.)
5. **No false positives.** When `pre_extract_chunker_versions` is empty (fresh install, no prior meta.json), the bump-detection is `False` — no forced rebuild on a clean install. When new == old, also `False`.
6. **Backward compatibility.** `UpgradeContext` gains two new attributes (`pre_extract_chunker_versions`, `chunker_version_bumped`, `chunker_version_transition`); existing hook callers that don't reference them are unaffected. The `--full` CLI flag still wins over the auto-decision when explicitly passed.
7. **Test coverage.** Tests verify: (a) old-version-22 + new-version-23 forces rebuild path; (b) old-version-23 + new-version-23 keeps incremental path; (c) no prior meta.json keeps incremental path (fresh install); (d) legacy scalar `chunker_version` key is treated the same as the per-layer dict; (e) `--full` CLI flag wins regardless of auto-decision; (f) post-verification fails-loud when advisory remains after rebuild.
8. **CHANGELOG bullet** describes the new upgrade behavior and the Solaris-feedback context.

## Scope

**Problem statement:** `wave_upgrade` Phase 4 relies on `indexer.build_index`'s internal auto-escalate to detect chunker-version changes and force a rebuild. The escalate is silent (no operator-visible decision log) and unverified (no post-condition check). When the auto-escalate doesn't fire — for any reason — the consumer's index is left stale and the upgrade is reported as successful. Solaris's installation of 1.5.0 reproduced this.

**In scope:**

- `upgrade_wavefoundry.py` — pre-extract version snapshot, post-extract comparison, Phase 4 routing, post-verification
- `UpgradeContext` — three new attributes (snapshot, bumped flag, transition tuple)
- Helper for reading `CHUNKER_VERSION` from a `chunker.py` path via regex
- Helper for invoking `wave_index_health` against a project root and parsing the advisory list
- Tests in `test_upgrade_wavefoundry.py` covering the 6 behavioral scenarios
- CHANGELOG bullet

**Out of scope:**

- Changes to `indexer.build_index`'s auto-escalate logic — that path still works and remains the backstop for non-upgrade calls (`wave_index_build` MCP tool, manual `setup_index.py` runs)
- Changes to `wave_index_health` advisory format — this change consumes it, doesn't reshape it
- The `wave_index_build(content="graph")` post-upgrade rebuild path — graph-version mismatch is handled by `1p397`'s framework graph index auto-rebuild on FIRST query; out of scope for this docs/code index rebuild change
- Solaris-side specific debugging — operator follow-up after this change ships will verify whether the failure mode is fixed

## Acceptance Criteria

- [x] AC-1: `UpgradeContext` gains attributes `pre_extract_chunker_versions: dict[str, str]`, `chunker_version_bumped: bool`, `chunker_version_transition: tuple[str, str] | None`. Defaults preserve current behavior when unset.
- [x] AC-2: Before `phase_extract`, the upgrade flow reads `<root>/.wavefoundry/index/meta.json` (when present) and populates `pre_extract_chunker_versions` from either `chunker_versions` (per-layer dict) or legacy scalar `chunker_version` (mapped to `{"docs": <scalar>, "code": <scalar>}`).
- [x] AC-3: After `phase_extract`, the upgrade flow reads `CHUNKER_VERSION` from the extracted `<root>/.wavefoundry/framework/scripts/chunker.py` via regex (no Python import). Stored as the new value.
- [x] AC-4: `chunker_version_bumped == True` when **all** of: (a) `pre_extract_chunker_versions` is non-empty, AND (b) at least one of the docs/code entries differs from the new value, AND (c) the new value is non-empty.
- [x] AC-5: When `chunker_version_bumped == True`, Phase 4 calls `phase_index_rebuild` (full rebuild) instead of `phase_index_update`. The log emits a prominent line: `⚠  Chunker version changed: <old> → <new>. Forcing full index rebuild.`
- [x] AC-6: When `chunker_version_bumped == False`, Phase 4 calls `phase_index_update` as today (no behavior change).
- [x] AC-7: After Phase 4a (docs index, blocking) returns successfully, the upgrade flow invokes a helper that runs `wave_index_health` (via subprocess `wave_index_health` MCP equivalent or direct `indexer.docs_health` call) and parses the response for any `chunker_version_mismatch` advisory naming the docs layer.
- [x] AC-8: When the advisory is present after rebuild, the upgrade exits non-zero with stderr: `❌ Chunker version mismatch persists after rebuild. Run: python3 .wavefoundry/framework/scripts/setup_index.py --root <root> --full` (literal text).
- [x] AC-9: When `pre_extract_chunker_versions` is empty (fresh install with no prior `meta.json`), `chunker_version_bumped == False`, no forced rebuild.
- [x] AC-10: When the CLI `--full` flag is passed explicitly, it wins — Phase 4 runs full rebuild regardless of auto-decision. The auto-decision is logged as "skipped (--full explicit)" for transparency.
- [x] AC-11: Test `test_upgrade_forces_rebuild_when_chunker_bumped` plants a `meta.json` with `chunker_versions: {"docs": "22", "code": "22"}`, runs the upgrade with a stub `chunker.py` declaring `CHUNKER_VERSION = "23"`, asserts `phase_index_rebuild` was called (not `phase_index_update`).
- [x] AC-12: Test `test_upgrade_uses_incremental_when_chunker_unchanged` plants `chunker_versions: {"docs": "23", "code": "23"}`, asserts `phase_index_update` was called.
- [x] AC-13: Test `test_legacy_scalar_chunker_version_is_treated_as_per_layer` plants the legacy `chunker_version: "22"` (scalar, not dict) and asserts the bump is correctly detected.
- [x] AC-14: Test `test_fresh_install_does_not_force_rebuild` runs the upgrade with no pre-existing `meta.json` and asserts `phase_index_update` (default) is used, not `phase_index_rebuild`.
- [x] AC-15: Test `test_explicit_full_flag_wins_over_auto` runs with `--full` AND a non-bumped state, asserts `phase_index_rebuild` is called and the auto-decision log notes "--full explicit".
- [x] AC-16: Test `test_post_verification_fails_loud_when_advisory_persists` mocks `wave_index_health` to return a `chunker_version_mismatch` advisory after rebuild, asserts upgrade exits non-zero with the actionable message.
- [x] AC-17: CHANGELOG bullet under `## [1.5.0]` describes the new upgrade behavior and the Solaris field-feedback context.
- [x] AC-18: Full framework test suite passes (additional ~6 tests).
- [x] AC-19: docs-lint clean.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `pre_extract_chunker_versions`, `chunker_version_bumped`, `chunker_version_transition` attributes to `UpgradeContext`
- [x] Add helper `_read_chunker_version_from_file(chunker_py_path) -> str` using regex match (no import)
- [x] Add helper `_snapshot_pre_extract_chunker_versions(root) -> dict[str, str]` reading consumer's meta.json
- [x] Wire snapshot into the upgrade-flow main() before `phase_extract`
- [x] Wire post-extract comparison and Phase 4 routing decision
- [x] Add helper `_verify_chunker_rebuild_succeeded(root) -> bool` consuming `wave_index_health` output
- [x] Wire post-Phase-4a verification with fail-loud exit
- [x] Add 6 new tests in `test_upgrade_wavefoundry.py`
- [x] Update CHANGELOG bullet
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close `framework_edit_allowed` gate

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| context-fields | implementer | — | Add three new `UpgradeContext` attributes |
| version-snapshot | implementer | context-fields | Pre-extract reader for meta.json |
| version-detect | implementer | version-snapshot | Post-extract CHUNKER_VERSION reader + bump-detection |
| phase-routing | implementer | version-detect | Phase 4 dispatch decision + prominent log |
| post-verify | implementer | phase-routing | wave_index_health invocation + fail-loud |
| tests | qa-reviewer | post-verify | Six behavioral tests |
| docs | docs-contract-reviewer | post-verify | CHANGELOG bullet |

## Serialization Points

- All implementation is in `upgrade_wavefoundry.py` (single file). Tests in `test_upgrade_wavefoundry.py`. Sequence: context-fields → version-snapshot → version-detect → phase-routing → post-verify → tests → CHANGELOG.

## Affected Architecture Docs

`N/A` — extends an existing upgrade flow's decision points; no architectural seam or data-flow change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Foundation — context fields hold the decision state. |
| AC-2 | required | Pre-extract snapshot is load-bearing for the comparison. |
| AC-3 | required | Post-extract version read drives the decision. |
| AC-4 | required | The decision predicate. |
| AC-5 | required | The headline routing change — full rebuild when bumped. |
| AC-6 | required | No regression on the unchanged path. |
| AC-7 | required | Post-condition verification closes the silent-failure case. |
| AC-8 | required | Actionable failure message for operators. |
| AC-9 | required | Fresh-install regression guard. |
| AC-10 | required | CLI flag precedence — explicit user intent wins. |
| AC-11 | required | Bump-detected test. |
| AC-12 | required | No-bump test (regression guard). |
| AC-13 | required | Legacy meta.json shape compatibility. |
| AC-14 | required | Fresh-install test. |
| AC-15 | required | CLI flag precedence test. |
| AC-16 | required | Post-verification fail-loud test. |
| AC-17 | required | CHANGELOG. |
| AC-18 | required | Suite must pass. |
| AC-19 | required | docs-lint must pass. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-05 | Change scaffolded after operator direction following Solaris field observation that 1.5.0 install didn't rebuild project indexes. | This doc; CHANGELOG for the diagnosis session |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-05 | Detect chunker bump in `wave_upgrade` itself and route Phase 4 explicitly, instead of relying on `indexer.build_index`'s internal auto-escalate | Auto-escalate is silent (no operator-visible decision log) and unverified (no post-condition check). When it doesn't fire — for any reason — the consumer is left stale and the upgrade reports success. The Solaris case is the proof point. Explicit detection + routing + verification turns "silent escalate that might happen" into "logged decision that we then verify worked." | (a) Strengthen `indexer.build_index`'s auto-escalate with a verification step — rejected; same layer that's already silent can't reliably surface a decision to the operator who's watching the upgrade log. (b) Remove auto-escalate entirely and require explicit `--full` — rejected; breaks the non-upgrade callers (MCP `wave_index_build`, manual `setup_index.py`) that depend on auto-escalate. The auto-escalate stays as the backstop for those paths; `wave_upgrade` becomes the explicit, verified path. |
| 2026-06-05 | Read CHUNKER_VERSION via regex against `chunker.py` text rather than importing the chunker module | The upgrade runs from a different cwd than the extracted scripts and may have stale Python module cache after extract. Regex against the literal file text is robust to that and avoids any import-side-effect risks during upgrade. The regex is `r'^CHUNKER_VERSION\s*=\s*["\'](\d+)["\']'` — anchored to start-of-line, easy to make brittle in a controlled way that catches accidental syntax changes to the constant. | Import the chunker module — rejected; cwd / sys.path complications during upgrade. Read meta.json from the unpacked framework-index — rejected; that's the SOURCE of the value but adds a coupling between two files for the same datum. |
| 2026-06-05 | Verify post-condition only for docs (Phase 4a, blocking), not code (Phase 4b, background) | Phase 4b runs `setup_index.py --background-code` with stdout/stderr to DEVNULL — verification would require either waiting for the background process (blocks the upgrade) or scheduling a later check (adds complexity for a code-layer-only failure mode). The docs layer is the load-bearing failure case the Solaris report surfaced; code-layer fix is queued as a follow-up if field observation surfaces it. | Verify both — rejected; would force the upgrade to wait for background completion, defeating the background-launch design. |
| 2026-06-05 | `--full` CLI flag wins over the auto-decision | Operator-explicit intent overrides framework heuristics. The auto-decision is the smart default; explicit `--full` is the override. Same pattern as every other CLI flag that disables an auto-behavior. | Auto-decision wins over `--full` — rejected; defeats operator intent. |
| 2026-06-05 | When `pre_extract_chunker_versions` is empty (no prior meta.json), `chunker_version_bumped` is False | A fresh install has no "old" version to compare against. Forcing a rebuild on every fresh install adds time for no benefit — `phase_index_update` against an empty index is effectively the same as `phase_index_rebuild` (it builds from scratch). | Treat empty as "force rebuild" — rejected; identical outcome on fresh install but adds the false impression of a "rebuild forced" event when nothing was rebuilt. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Regex against `chunker.py` could match a different `CHUNKER_VERSION` line if the file structure changes | The regex is anchored to start-of-line and matches a digit-only string. Future refactors that move the constant or change its shape would fail the regex (returning empty string), which would set `chunker_version_bumped: False` (safe default — no false rebuild). If the upgrade silently skips a rebuild that should have happened, operator can still run `setup_index.py --full` manually; the existing auto-escalate in `build_index` is a second backstop. |
| Post-Phase-4a verification adds time to the upgrade | `wave_index_health` is fast (<200ms typically). One extra call after a rebuild that took 30s-3min is negligible. |
| Background Phase 4b code-index rebuild could silently fail without post-verification | Documented as out-of-scope per Decision Log. A follow-up could add async verification (e.g., write a marker file when complete, check on next wave_index_health call) but that's its own design. |
| Existing operators with `chunker_version: "23"` (already on the new version) running this change for the first time would NOT see a rebuild, even if their indexes happen to be stale for unrelated reasons | Correct — the change is scoped to chunker-version transitions, not general staleness. General staleness is handled by `wave_index_build(mode="rebuild")` or `setup_index.py --full`. No regression. |
| Test fixtures for AC-11 / AC-12 need to plant a valid `meta.json` shape | The shape is documented in indexer.py; tests can reuse the helpers in `test_indexer.py` that already construct fixtures with `chunker_versions` keys. No new fixture infrastructure required. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state. Change doc scaffolded 2026-06-05 immediately after Solaris field observation diagnosis. Operator directed: "we should add an upgrade path for the upgrade to make sure it gets called." This change is the framework's hardening response: explicit detection + routing + verification at the upgrade layer.
