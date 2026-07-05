# Renderer overwrite safety: preserve operator customizations in `.codex/config.toml` and gate copilot-artifact removal on detection

Change ID: `1p9p7-bug renderer-overwrite-safety`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-04
Wave: `1p9pe post-release-followup-hardening`

## Rationale

Two related renderer defects, both surfaced during wave `1p9j0`'s all-platform re-render (DF-2), let a routine render silently destroy committed project-local state. This contradicts the AGENTS.md safety rule "Never overwrite project-local customizations without showing a diff or conflict report."

**(a) `render_agent_surfaces` unconditionally overwrites `.codex/config.toml`.** At `.wavefoundry/framework/scripts/render_agent_surfaces.py:329-330` the renderer does `write_text(codex_mcp_config, CODEX_MCP_CONFIG_TOML)` — a full-file overwrite with a canned three-line template (`CODEX_MCP_CONFIG_TOML`, defined at `:149`, contains only `[mcp_servers.wavefoundry]` + `command` + `args`). Any operator-added TOML — during `1p9j0` this was a committed `[mcp_servers.wavefoundry.tools.wave_close]` `approval_mode = "approve"` guardrail — is deleted on every render/upgrade, with no diff and no warning. (The clobber was caught by the delivery-council reality-checker and restored by hand via `git checkout`.) The loss is silent because the file is a generated artifact the renderer believes it fully owns, but operators legitimately extend it with Codex-native config (approval modes, extra tool policy) the framework template does not carry.

**(b) An explicit `--platform` list that omits copilot removes `.github/hooks/` even when the repo has copilot surfaces.** At `render_platform_surfaces.py:1723-1725`, `platforms = set(args.platform or detect_platforms(repo_root))` and then `if "copilot" not in platforms: remove_copilot_artifacts(repo_root)`. When the operator (or a sibling render step) runs `render_platform_surfaces --platform claude`, `args.platform = ["claude"]` overrides detection entirely, so `platforms = {"claude"}` — copilot is absent even though `detect_platforms` would have added it from an existing `.github/copilot-instructions.md`. `remove_copilot_artifacts` (`:89`) then deletes the repo's committed `.github/hooks/*` copilot hooks. The removal decision keys off the *invocation's* platform set rather than whether the repo *actually has* copilot surfaces. This is the exact footgun that made the `1p9j0` DF-2 fix require a single auto-detect re-render instead of a per-platform loop.

Both are "renderer destroys committed state on a normal invocation" defects. This change makes the codex-config write non-destructive (framework-managed region only) and gates copilot-artifact removal on detection, not the explicit platform set.

## Requirements

1. `render_agent_surfaces` must not delete operator-authored content from `.codex/config.toml` on re-render. The framework-managed `[mcp_servers.wavefoundry]` command/args must still be written and kept current, but any operator-added tables/keys (e.g. `[mcp_servers.wavefoundry.tools.*]`, approval modes, unrelated `[mcp_servers.*]`) must survive a render/upgrade byte-for-byte.
2. The framework-managed region of `.codex/config.toml` must be clearly delimited so the boundary between "renderer owns this" and "operator owns this" is explicit and machine-detectable (a TOML `#`-comment marker region mirroring the existing `upsert_marked_region` precedent for markdown, or an equivalent structured-merge that preserves non-framework keys).
3. On a fresh repo with no `.codex/config.toml`, the renderer must still create the file with the framework-managed region (create-if-missing behavior unchanged in effect).
4. `remove_copilot_artifacts` must run only when the repo does **not** have copilot surfaces per `detect_platforms` (i.e., no `.github/copilot-instructions.md`), regardless of whether the current invocation's explicit `--platform` list names copilot. An explicit `--platform claude` on a repo that has copilot surfaces must NOT delete `.github/hooks/*`.
5. The copilot-render behavior when copilot IS in scope is unchanged: `render_platform_surfaces --platform copilot` (or auto-detect on a copilot repo) still renders the copilot hooks and config.
6. No behavioral change for repos that genuinely have no copilot surfaces: `remove_copilot_artifacts` still cleans up stale copilot files there, exactly as today.

## Scope

**Problem statement:** A normal `render_agent_surfaces` / `render_platform_surfaces` invocation can silently delete committed project-local state — operator customizations in `.codex/config.toml`, and `.github/hooks/*` when an explicit `--platform` list omits copilot on a copilot repo — violating the "never overwrite customizations without a diff" rule.

**In scope:**

- Make the `.codex/config.toml` write in `render_agent_surfaces.py` (`:329-331`) preserve operator content: introduce a TOML `#`-marker framework-managed region (mirroring `upsert_marked_region` / the `MARKER_BEGIN`/`MARKER_END` pattern at `:10-11`, `:162`) or a structured TOML merge that upserts only `[mcp_servers.wavefoundry]` command/args and leaves everything else intact.
- Gate `remove_copilot_artifacts` in `render_platform_surfaces.py` (`:1724`) on `detect_platforms(repo_root)` (does the repo have copilot surfaces?) rather than on the invocation's `platforms` set.
- Tests: a re-render preserves an operator-added `[mcp_servers.wavefoundry.tools.wave_close]` block; a fresh repo gets the file created; an explicit `--platform claude` render on a repo with `.github/copilot-instructions.md` leaves `.github/hooks/*` intact; a repo with no copilot surfaces still has stale copilot artifacts removed.

**Out of scope:**

- The other unconditional generated-artifact writes in `render_agent_surfaces.py` (the auto-guru `SKILL.md`, `guru.md`, cursor rule) — these are purely framework-generated content operators are not expected to hand-edit; only `config.toml` is a documented operator-extensible surface. (If a future finding shows operators customize those, handle it separately.)
- Any change to `CODEX_MCP_CONFIG_TOML`'s framework-managed content, or to how Codex loads the config.
- A general merge framework for every rendered surface; this change addresses the two named destructive paths only.
- Restoring the specific `1p9j0` guardrail (already restored by hand); this change prevents recurrence.

## Acceptance Criteria

- [x] AC-1: Re-rendering agent surfaces on a repo whose `.codex/config.toml` contains an operator-added block (e.g. `[mcp_servers.wavefoundry.tools.wave_close]` `approval_mode = "approve"`) preserves that block byte-for-byte while keeping the framework-managed `[mcp_servers.wavefoundry]` command/args current. Verified by a unit test that seeds the operator block, renders, and asserts the block survives. — `CodexConfigOverwriteSafetyTests.test_rerender_preserves_operator_block_byte_for_byte` (+ `test_stale_framework_region_is_refreshed`, `test_unrelated_operator_server_table_survives`)
- [x] AC-2: The framework-managed region of `.codex/config.toml` is delimited by a stable marker (or an equivalent structured-merge boundary) so a second render is idempotent and the operator/framework ownership split is explicit. A test asserts two consecutive renders produce identical bytes and the marker/region is present. — `test_double_render_is_idempotent` (fresh and with operator content); markers `CODEX_CONFIG_MARKER_BEGIN`/`_END`
- [x] AC-3: On a repo with no `.codex/config.toml`, a render creates it containing the framework-managed region. Verified by a unit test on a fresh temp repo. — `test_create_if_missing_renders_marked_framework_region`
- [x] AC-4: `render_platform_surfaces --platform claude` on a repo containing `.github/copilot-instructions.md` (and `.github/hooks/*`) does NOT delete `.github/hooks/*`. Verified by a unit test that seeds copilot surfaces, renders with an explicit non-copilot platform, and asserts the hooks remain. — `CopilotRemovalDetectionGateTests.test_explicit_non_copilot_render_preserves_copilot_hooks`
- [x] AC-5: On a repo with no copilot surfaces, a render still removes stray `.github/hooks/*` copilot artifacts (no regression to the cleanup behavior). Verified by a unit test. — `test_no_copilot_repo_still_removes_stale_artifacts`
- [x] AC-6: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` is clean; re-rendering this repo's own surfaces produces no unexpected diff (rendered-surface fidelity; the `.codex/config.toml` guardrail block is preserved). — full suite green (see Progress Log); `wave_validate` clean; self-render diff = only the one-time marker migration on `.codex/config.toml` (operator `wave_close` block intact, valid TOML, second render byte-identical)
- [x] AC-7 (readiness corrective pass, applied 2026-07-04): **migration absorption + TOML validity** — on a repo whose existing `.codex/config.toml` carries an UNMARKED pre-existing `[mcp_servers.wavefoundry]` table (this repo's exact on-disk state: unmarked framework table at lines 1-3 + the restored operator `wave_close` block at lines 5-6), the first marked render ABSORBS the unmarked framework table into the managed region (never duplicates it), and the resulting file parses as valid TOML (`tomllib.loads` round-trip asserted). A duplicate `[mcp_servers.wavefoundry]` table is the named migration hazard — the test seeds precisely the current on-disk shape. — `test_absorbs_unmarked_framework_table_this_repos_shape` (seeds the exact 6-line shape; asserts single table header, marker presence, operator block byte-for-byte, `tomllib` round-trip, one-time migration idempotence); plus fail-safe `test_unparseable_merge_leaves_existing_untouched`
- [x] AC-8 (readiness corrective pass, applied 2026-07-04): **copilot-in-scope still renders** — a render on a repo WITH copilot surfaces in scope still produces/refreshes the copilot artifacts (the removal-guard fix must not suppress legitimate rendering). Unit-tested. — `test_copilot_in_scope_still_renders_artifacts` (auto-detect AND explicit `--platform copilot` paths)

## Tasks

- [x] Design the `.codex/config.toml` framework-managed region: choose TOML `#`-marker region (mirror `upsert_marked_region`, adapting the marker to a TOML comment) vs a `tomllib`-parse structured merge; record the choice in the Decision Log.
- [x] Implement the non-destructive codex-config write in `render_agent_surfaces.py` (`:329-331`): read existing content, upsert the framework region, preserve everything else; create-if-missing when absent.
- [x] Change the copilot-removal guard in `render_platform_surfaces.py` (`:1724`) to key off `detect_platforms(repo_root)` (repo has copilot surfaces?) instead of the invocation's `platforms` set.
- [x] Add tests: operator-block preservation, idempotent double-render, create-if-missing, explicit-non-copilot-render-preserves-hooks, no-copilot-repo-still-cleans-up.
- [x] Re-render this repo's surfaces and confirm no unexpected diff (the committed `.codex/config.toml` guardrail block stays).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`; clean any `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-codex-config-merge | implementer | — | Non-destructive `.codex/config.toml` write in `render_agent_surfaces.py`; region/merge design. |
| ws2-copilot-removal-guard | implementer | — | Gate `remove_copilot_artifacts` on detection in `render_platform_surfaces.py`; independent file. |
| ws3-tests-and-rerender | implementer | ws1-codex-config-merge, ws2-copilot-removal-guard | Tests for both paths; re-render this repo; run suite + `wave_validate`. |


## Serialization Points

- ws1 and ws2 touch disjoint files (`render_agent_surfaces.py` vs `render_platform_surfaces.py`) and can proceed in parallel. ws3 joins after both and is the only step that re-renders this repo's live surfaces.

## Affected Architecture Docs

N/A — the change is confined to two renderer functions' write/removal safety; it introduces no new module boundary, data/control-flow, or verification-architecture change (the render pipeline's structure is unchanged; only two writes become non-destructive). No `docs/ARCHITECTURE.md` or `docs/architecture/*` update is warranted. The operator-extensibility contract for `.codex/config.toml` (framework region vs operator region) is documented inline at the write site and in the marker text.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Preserving operator content in `.codex/config.toml` is the core of defect (a); the guardrail loss already happened once. |
| AC-2 | required | An explicit framework/operator boundary + idempotence is what makes the write safe and non-drifting. |
| AC-3 | required | Create-if-missing preserves the current fresh-repo behavior; regressing it would break new installs. |
| AC-4 | required | Not deleting `.github/hooks/*` on an explicit non-copilot render is the core of defect (b); it caused the DF-2 rework. |
| AC-5 | required | The cleanup behavior for genuine non-copilot repos must not regress. |
| AC-6 | required | Suite + docs-lint + clean self-render are the standing merge gates; the self-render also proves the guardrail block survives. |
| AC-7 | required | Corrective-pass mandate: the migration hazard (duplicate TOML table on this very repo) would break the Codex host on first self-render; absorption + round-trip validity is the guard. |
| AC-8 | required | Corrective-pass mandate: the removal-guard fix must not flip into suppressing legitimate copilot rendering. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from wave `1p9j0` DF-2. Verified (a) `render_agent_surfaces.py:329-331` unconditionally overwrites `.codex/config.toml` from `CODEX_MCP_CONFIG_TOML` (`:149`, which lacks the operator `wave_close` block); (b) `render_platform_surfaces.py:1723-1725` gates `remove_copilot_artifacts` on the invocation's `platforms` set, so `--platform claude` deletes `.github/hooks/*` even when `detect_platforms` (`:50-55`) would add copilot from `.github/copilot-instructions.md`. Existing marker-region precedent for markdown: `upsert_marked_region` / `MARKER_BEGIN`/`MARKER_END` (`render_agent_surfaces.py:10-11,162`). | `render_agent_surfaces.py:149,329-330,162`; `render_platform_surfaces.py:50-55,89,1723-1725`; `1p9j0` reality-checker finding + hand-restore of `.codex/config.toml`. |
| 2026-07-04 | Implemented both fixes. (a) `render_agent_surfaces.py`: added `CODEX_CONFIG_MARKER_BEGIN`/`_END` TOML comment markers + `upsert_codex_mcp_config()` (marked-region upsert; create-if-missing; one-time absorption of the unmarked framework table; `tomllib`-validated fail-safe that returns existing content unchanged if a merge would not parse); write site now reads existing bytes with `newline=""` and upserts instead of clobbering. (b) `render_platform_surfaces.py` `main()`: `remove_copilot_artifacts` now gated on `detect_platforms(repo_root)` (repo property), not the invocation's `--platform` set. Tests: `CodexConfigOverwriteSafetyTests` (8 tests) in `test_render_agent_surfaces.py`; `CopilotRemovalDetectionGateTests` (3 tests) in `test_render_platform_surfaces.py`. | Module runs: `test_render_agent_surfaces.py` 19/19 OK, `test_render_platform_surfaces.py` 53/53 OK. |
| 2026-07-04 | AC-6 payoff: self-rendered this repo's surfaces with the fixed renderer. `git diff .codex/config.toml` shows ONLY the one-time migration — two marker comment lines added around the framework table; the operator `[mcp_servers.wavefoundry.tools.wave_close]` `approval_mode = "approve"` block survived untouched; `tomllib` parse confirms valid TOML (`command = "python3"`, `wave_close.approval_mode = "approve"`); a second render is byte-identical (idempotent) and no other file diffed. Full suite green + `wave_validate` clean. Retires the standing "restore-after-re-render" watchpoint (wave.md updated). | Self-render diff: `.codex/config.toml` +2 marker lines only; `shasum` stable across renders `6c0dcf00721b…`; full suite `run_tests.py`: 4470 tests across 43 files, OK; `wave_validate`: `docs-lint: ok`; `__pycache__` cleaned. |
| 2026-07-04 | Review-fix lane (convergent red-team primer + code + architecture + security findings, all reproduced before fixing): hardened `upsert_codex_mcp_config`. (i) Single-exit `tomllib` validation — EVERY mutating branch (marker-replace, migration, append) now computes a candidate that one final guard validates, returning the existing content unchanged on failure (pre-fix only the migration branch validated: the append branch demonstrably wrote duplicate-table corruption for the quoted header spelling, and marker-replace sliced through an operator string containing marker text — the marker match is now line-anchored, and marker text outside a well-formed region fail-safes). (ii) Quoted/whitespace TOML-equivalent header spellings (`[mcp_servers."wavefoundry"]`, `[ mcp_servers.wavefoundry ]`) now MIGRATE instead of duplicating; the dotted-key form fail-safes instead of corrupting. (iii) Absorption depth-desync bail: an unbalanced `[` inside an operator-modified string value desynced `_codex_value_bracket_delta` and the absorber ate to EOF, silently dropping operator subtables while producing VALID TOML the parse guard cannot flag (reproduced) — absorption now fail-safes when bracket depth never rebalances, plus a continuation-line cap as the stronger guard. (iv) Loud fail-safe: any fail-safe branch emits a stderr warning naming the file and reason, and the path is NOT reported in `written`. 9 new tests (`CodexConfigUpsertHardeningTests`); all 8 prior `CodexConfigOverwriteSafetyTests` unchanged and green (module 28/28). | `render_agent_surfaces.py` (`upsert_codex_mcp_config`, `_CODEX_MARKER_REGION_RE`, `_CODEX_TABLE_HEADER_RE`, `_CODEX_ABSORB_MAX_VALUE_LINES`, write site in `render_agent_surfaces()`); `tests/test_render_agent_surfaces.py::CodexConfigUpsertHardeningTests`; pre-fix reproducers: quoted-header/dotted-key → invalid TOML written, marker-in-string → sliced, unbalanced-bracket → operator subtable dropped with valid output. |
| 2026-07-04 | Follow-up candidates recorded from the security lane (no code change in this wave): (a) atomic temp+replace for the split-ownership `.codex/config.toml` write — the upsert currently truncate-writes in place, so a crash mid-write could leave a partial file (S3); (b) recorded exposure: the one-time migration absorbs the unmarked framework table into the canonical template, so operator-customized `command`/`args` VALUES inside that unmarked table are silently refreshed to the framework defaults (operator keys/subtables survive; only framework-owned key values are normalized). | Security-lane S3 finding; migration semantics of `upsert_codex_mcp_config` (absorption replaces the framework-owned assignments with `CODEX_MCP_CONFIG_TOML`). |
| 2026-07-04 | Delivery-council fix-now lane (all findings reproduced before fixing). (i) S-NEW-1 FIXED in-session (security seat, empirically proven): a triple-quoted operator string whose body reproduces BOTH marker comment lines as whole physical lines matched the line-anchored `_CODEX_MARKER_REGION_RE` *inside the string*; the replace branch sliced the string, silently dropping operator content (probe: `blob = """…begin…/command = "evil"/…end…"""` + real unmarked framework table below — `command = "evil"` vanished, result still parsed, no fail-safe). Fix: pre-branch fail-safe — when the existing content parses, marker text inside a MULTILINE parsed string value (`_codex_marker_in_multiline_string`) fail-safes before branch selection; single-line marker mentions stay on the normal path (no-false-positive pinned against this repo's on-disk shape). (ii) Rotating-seat semantic-equivalence exit guard: the single validated exit now also requires the tomllib-parsed existing and candidate documents to be EQUAL after normalizing framework-owned differences (`_codex_normalized_doc`: `command`/`args` refresh in `mcp_servers.wavefoundry`; creation of that table/parent when absent — the recorded migration-refresh exposure above is the deliberate tolerance). This structurally closes valid-TOML content loss the parse check cannot flag: reproduced a balanced-bracket absorption desync (`args = ["x", "--open[["]` … `key = "]]close"`) that evaded BOTH the depth fail-safe and the continuation cap, ate the operator table, and parsed cleanly — now caught only by this guard; the bracket heuristics are demoted to defense-in-depth. (iii) CRLF residual FIXED in-session (was slated as a justified non-fix): `_CODEX_MARKER_REGION_RE` line tails now tolerate `\r` (`[ \t\r]*`), so a CRLF-rewritten config matches its marker region and refreshes instead of perpetually fail-safing with a stale block; operator CRLF bytes outside the region survive byte-for-byte. (iv) QA seat: added the missing marker-replace-branch tomllib-exit test (well-formed marked region + operator-owned duplicate `[mcp_servers.wavefoundry]` table outside it → duplicate-table candidate → fail-safe, existing unchanged). (v) Docstring precision (architecture seat): the docstring now names the one deliberate unvalidated exit — the no-existing-content branch returns constant renderer content with no operator merge, so there is nothing to corrupt. (vi) Regex parity (architecture seat): `_PREPARE_COUNCIL_VERDICT_LINE_RE` (wave_validators) and `_PREPARE_COUNCIL_VERDICT_RE` (server_impl) verified literally identical (pattern and flags) — pinned with an equality test rather than a divergence note. Justified non-fix retained: fail-safe exits 0 by design — other surfaces still render, the stderr warning naming the file is the signal, and changing exit semantics is a contract change out of scope. | `render_agent_surfaces.py` (`_codex_marker_in_multiline_string`, `_codex_normalized_doc`, `_CODEX_MARKER_REGION_RE`, `upsert_codex_mcp_config`); `tests/test_render_agent_surfaces.py::CodexConfigCouncilFixNowTests` (6 tests; module 34/34 OK); `tests/test_docs_lint.py::PrepareCouncilVerdictRegexParityTests`; pre-fix reproducers run against the unpatched module: probe-B string slice (evil line dropped, result parsed, `reasons == []`) and balanced-bracket desync (operator table eaten, valid TOML, `reasons == []`) — both now fail-safe with existing content unchanged. |
| 2026-07-04 | Follow-up candidate: plan `1rqh2-debt remove-tomllib-import-fallback` (already authored) covers removing the pre-3.11 `tomllib` import fallback per ADR 12tm5, after which `upsert_codex_mcp_config`'s parse and equivalence guards run unconditionally. | `docs/plans/1rqh2-debt remove-tomllib-import-fallback.md`; ADR 12tm5. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Fix both renderer destructive paths in one change (they share a root cause: renderer destroys committed state on a normal invocation). | Same reviewer finding, same file family, same safety rule; splitting them adds coordination overhead for two small edits. | Two separate changes — rejected as needless fragmentation of one coherent safety fix. |
| 2026-07-03 | Prefer a framework-managed marker region (or structured TOML merge) over create-if-missing-only for `.codex/config.toml`. | Create-if-missing would freeze the framework's `[mcp_servers.wavefoundry]` command/args on first write, so a future framework change to the launch command would not propagate to existing repos. A managed region keeps the framework block current AND preserves operator content. | (i) Create-if-missing only — rejected: framework block goes stale. (ii) Full overwrite with a diff/prompt — rejected: renders are non-interactive; a region merge is the non-interactive-safe form. |
| 2026-07-03 | Gate copilot removal on `detect_platforms` (repo has surfaces?) not the invocation's `--platform` set. | The removal should reflect whether the repo is a copilot project, which is a property of the repo, not of which platform a given render invocation targeted. | Require callers to always pass a full `--platform` list — rejected: fragile, and the auto-detect path is the intended common invocation. |
| 2026-07-04 | **Chose the TOML `#`-comment marker region** (`CODEX_CONFIG_MARKER_BEGIN`/`_END`) over a `tomllib`-parse structured merge, with a line-scanning one-time absorption of the pre-existing unmarked `[mcp_servers.wavefoundry]` table (absorbs only the contiguous framework-owned `command`/`args` assignments incl. multi-line value continuations; stops at the first operator-authored line). `tomllib` is used as a merge VALIDATOR only: if an absorbed merge would not parse, the existing file is returned unchanged (stale framework block is recoverable; a corrupted operator config is not). | Mirrors the established `upsert_marked_region` markdown precedent; preserves operator bytes, comments, and key order exactly (a `tomllib` round-trip merge cannot — `tomllib` has no writer and drops comments/ordering); markers are TOML comments so operator keys left after the end marker still belong to the framework table, making absorption safe. | Structured `tomllib` merge — rejected: stdlib has no TOML writer, so re-serialization would destroy operator comments/ordering (the exact class of loss this change exists to prevent). Create-if-missing only — rejected at planning (framework block goes stale). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A TOML `#`-marker region is brittle if an operator edits inside the managed region. | The marker text says "generated — do not edit; add your own config outside this region", mirroring the markdown precedent; the upsert replaces only between markers, so operator content outside is always preserved; AC-2 pins idempotence. |
| Structured `tomllib` merge (if chosen) mis-handles comments or key ordering, producing churn. | Prefer the marker-region approach unless a merge is demonstrably cleaner; either way AC-2's double-render-identical-bytes test catches churn. |
| Gating copilot removal on detection leaves a stale `.github/hooks/*` on a repo that intentionally dropped copilot but kept `copilot-instructions.md`. | Detection is the documented signal for "is this a copilot repo"; removing copilot means removing its instruction file too, which flips detection and re-enables cleanup — consistent and predictable. |
| Re-rendering this repo during ws3 re-clobbers the restored guardrail before the fix lands. | ws3 runs the render only AFTER ws1's non-destructive write is in place; if a pre-fix render is needed, restore the block from git first (as was done in `1p9j0`). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
