# Retire The Ten Optional Flat Server Aliases

Change ID: `1yxwn-ref retire-optional-flat-server-aliases`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-25
Wave: `1yxyw retire-optional-server-aliases`

## Rationale

Wave `1yzd0` moved twelve server modules into `scripts/wf_server/` and kept a flat three-line `sys.modules` alias for each. Only two of those aliases are required.

- **Why two are required.** An installed 1.25 or 1.26 upgrade runner validates a new pack with `upgrade_protocol._validate_imports`. That check walks every import of each upgrade-mandatory module, including function-local ones, and resolves each against the pack's flat module stems only; `wf_server` is never available to it. The mandatory `upgrade_wavefoundry.py` and `upgrade_extensions.py` import `server_impl` and `dashboard_handlers`, function-locally, and the installed runners import those two in-process against the new tree. Those two aliases therefore stay.
- **The other ten.** `mcp_tool_registry` and nine handler modules (`codenav`, `graph`, `techdocs`, `memory`, `index`, `upgrade`, `edit_gate`, `docs`, `context_efficiency`) keep an alias only so that existing importers, mostly tests, work unchanged.

The operator asked to drop those ten by switching every importer to `wf_server.*` names. The result is one spelling per implementation, except for the two modules installed runners need, and ten fewer names in the global flat scripts namespace.

**Release framing.** 1.27.0 is built (commit `902f7edc`) but not tagged, and it still carries the full flat modules; wave `1yzd0` is under `[Unreleased]`. This change ships in the same release as `1yzd0` (see Requirement 9). As a result, no released version carries the ten aliases. Forks migrate once, from full flat modules to `wf_server.*`, and the "flat names are the permanent public import surface" statement in ADR `1yx4m` is narrowed before it reaches any release. The cleanup is worth its evaluator re-receipt cycle and test churn only on that condition.

**Census** (2026-09-25, against the `1yzd0` working tree). The predicate: any `import`/`from` statement, `importlib.import_module`/`__import__` call, `sys.modules` subscript or membership test, `patch`/`patch.object` target string, or other string constant (including code embedded in subprocess scripts) whose module token is one of the ten names or starts with `<name>.`.

- **Production outside the package:**
  - `memory_cli.py` (a top-level `import memory_handlers`);
  - `project_context_efficiency.py` (a lazy `import context_efficiency_handlers` inside `except Exception: pass`);
  - `mcp_tool_extensions.RESERVED_MODULE_NAMES`, whose entries stay;
  - the logical file keys in `retrieval_eval.py`.
- **Tests:**
  - 10 import statements;
  - 4 `importlib.import_module('<name>')` calls, all in `test_handler_modules`;
  - 127 quoted dotted names (mostly `patch("index_handlers._x")` targets) across 17 files;
  - bare-name checks such as `'graph_handlers' in sys.modules` in `test_server_package`, which becomes vacuous after removal and must be rewritten;
  - 23 test files mention one of the names at all.
- **Wave evidence scripts under `docs/waves/`:** historical, not edited.
- **Installed runners.** v1.25.0 and v1.26.0 `upgrade_wavefoundry`, `upgrade_extensions`, `upgrade_protocol`, `memory_backfill` and `server` import none of the ten; v1.25.0 has no handler modules at all. The 1.26 `server_impl` imports its handlers only at module top. The only lazy import of any of the ten, in v1.26.0 and at HEAD, is `project_context_efficiency.py`, which runs in its own hook process. A readiness probe reloaded v1.25.0, v1.26.0 and HEAD runners onto a simulated post-removal tree, and each served the edited code.

## Requirements

1. **Remove ten aliases.** Delete the flat files `mcp_tool_registry.py`, `codenav_handlers.py`, `graph_handlers.py`, `techdocs_handlers.py`, `memory_handlers.py`, `index_handlers.py`, `upgrade_handlers.py`, `edit_gate_handlers.py`, `docs_handlers.py` and `context_efficiency_handlers.py` from `.wavefoundry/framework/scripts/`. Keep `server_impl.py` and `dashboard_handlers.py` byte-identical.
2. **Retired names stay guarded.** `wf_server/server_impl.py` gains a `_RETIRED_FLAT_NAMES` constant naming the ten. `_FLAT_ALIASES` keeps only the two retained aliases, and eager registration covers only those two.
   - **Warning.** A flat file with a retired name that is still present is reported as a warning that names the file and says to delete it; the server still starts. The files are framework-owned and unedited, so a present file only means the upgrade's MANIFEST-diff prune did not run or could not be proven. The warning is written in two places: after pruning, by an `upgrade_extensions` `post_pruning` hook that only reports and never deletes (it holds its own copy of the ten names, pinned to `_RETIRED_FLAT_NAMES` by a test, because upgrade-mandatory modules cannot import `wf_server`); and by the server, which lists the leftover files as a `wf_server_info` diagnostic (stderr alone reaches only host logs, not the agent) and logs the same warning on stderr at start, never on stdout. The hook catches every error and only logs, because an old runner turns a hook exception into `sys.exit(3)` after pruning has already changed the tree. A leftover is permanent until deleted by hand: the next upgrade's old MANIFEST no longer lists it. While it remains, an unmigrated extension or fork that still imports a retired flat name binds to that stale copy instead of failing, which the warning names as the reason to delete it.
   - **Purge.** The reload purge evicts the flat key and the `wf_server.<name>` key of every moved module except `server_impl`, from `_FLAT_ALIASES` plus `_RETIRED_FLAT_NAMES`. That evicts the old flat module objects a 1.25, 1.26 or 1.27 host still holds after an in-place reload, which would otherwise stay live beside the package modules.
   - **Pin.** `mcp_tool_extensions.RESERVED_MODULE_NAMES` keeps all twelve names and `wf_server`, pinned to `_FLAT_ALIASES`, `_RETIRED_FLAT_NAMES` and `wf_server` together.
3. **Importers.** Every importer outside the package names the ten by their package names: `import wf_server.memory_handlers as memory_handlers`, `from wf_server.memory_handlers import ...`, `importlib.import_module("wf_server.index_handlers")`, `patch("wf_server.index_handlers._x")`. Code that must survive `wf_reload_mcp` never uses `from wf_server import <name>`, because that form reads the stale attribute on the never-evicted parent package. Upgrade-mandatory modules import only flat names, even function-locally, and only `server_impl` and `dashboard_handlers`.
4. **Reserved names.** An extension module can never take one of the twelve names or `wf_server` (Requirement 2).
5. **Evaluator.** `load_fixture_corpus` checks each relevance path's existence on its implementing path, resolved through `SERVER_PACKAGE_MODULES` (today it checks `root / path` before resolution). The fixture file and its digest stay byte-identical. This changes evaluator identity, so the change repeats the `1yzd0` sequence:
   - an evaluator-only step, independently reviewed and committed by the operator;
   - a baseline receipt on that commit;
   - the removal;
   - an after receipt with the same evaluator and fixture digest, with the operator-review attribution for any cross-generation fail.
6. **Censuses and structure tests.**
   - `test_server_package` pins the two retained aliases by exact bytes, asserts that the ten flat files are absent, and covers the retired-name warning with a known-bad control (a restored flat file is named in the warning, and the server still starts).
   - A census refuses the ten names outside `wf_server/` under the Rationale's predicate, and refuses `from wf_server import <evicted module>` outside the package. The allowlist is `RESERVED_MODULE_NAMES`, `_RETIRED_FLAT_NAMES`, the `upgrade_extensions` `post_pruning` hook's name list, the evaluator's logical keys and the tests that pin those four. The census has known-bad controls for each form, including a flat-name import added to `upgrade_extensions.py` outside the hook's list.
   - The vacuous bare-name assertions are rewritten against package names.
   - `framework_files.package_module_names()` and `source_path` keep working when a moved module has no flat file.
7. **Upgrade.** Deletion authority stays the ordinary MANIFEST-diff prune; nothing else deletes the ten files. An upgrade from v1.26.0 and the 1.27.0 release source prunes them and leaves no flat copy; an upgrade from v1.25.0, which never shipped them, leaves none. For 1.27.0 the source is the `v1.27.0` tag if it has been published, else commit `902f7edc`; both carry full flat modules. When pruning is unproven (no saved old MANIFEST), the files are kept, the upgrade's `post_pruning` report warns that they should be deleted, and the server still starts and repeats the warning. The fixtures run from installed-runner roots whose paths contain a space, and reach a working server as in the `1yzd0` matrix. An in-process reload from a 1.26 flat-module state leaves one live module object per moved module.
8. **Documentation.** Everything that would become false is updated.
   - **ADR `1yx4m`:** a dated "Amendment (wave 1yxyw)" section that keeps the original clauses and marks them narrowed. It covers:
     - "each keeps a flat file";
     - "one alias table … both purge key sets" (now the alias table plus `_RETIRED_FLAT_NAMES`);
     - the dual-key purge;
     - "code that imports … flat names keeps working";
     - "two spellings";
     - the permanent public import surface (now `server_impl` and `dashboard_handlers`);
     - the alias-removal precondition, scoped to the two, with the reason it never applied to the ten;
     - the clauses "The alias files cannot be removed yet" and the retained-alias `ImportError` constraint, both scoped to `server_impl` and `dashboard_handlers`;
     - the leftover behavior: the MANIFEST prune deletes the ten; any that remain are reported with a warning to delete them, stay until deleted by hand, and let a stale flat import succeed meanwhile.
   - **Index entries:** the ADR README row and `docs/ARCHITECTURE.md`.
   - **Specs and architecture docs:**
     - `docs/specs/mcp-tool-surface.md`, including the "Server package layout" paragraph, its refusal sentence for the two retained aliases, and the warning for the retired names;
     - `docs/architecture/current-state.md`, `domain-map.md` and `layering-rules.md`. The layering-rules outside-consumers row splits into mandatory modules (flat only) and other consumers (package names for the ten), and its "Flat aliases → `wf_server` package" row is scoped to the two retained aliases.
   - **Evaluator docs:** `docs/contributing/review-and-evals.md` (existence checks go through the implementing path).
   - **Code comments:** in `retrieval_eval.py` and `mcp_tool_extensions.py`.
   - **Memory record `1ywls-mem`:** now "reached through flat aliases".
   - **`CHANGELOG.md`:** rewrite the `1yzd0` `[Unreleased]` bullet into one statement of the shipped result. The bullet gives the migration for fork code:
     - `import wf_server.<name> as <name>` and `from wf_server.<name> import ...`;
     - `patch("wf_server.<name>.<attr>")`;
     - never `from wf_server import <name>` in code that must survive `wf_reload_mcp`;
     - extension override modules that import handler modules switch;
     - fork edits to the ten modules go to `wf_server/<name>.py`;
     - a leftover flat file of a retired name is reported with a warning to delete it, because while it remains a stale flat import succeeds;
     - the refusal sentence is kept, scoped to the two retained aliases.
9. **One release.** The release that carries `1yzd0` also carries this change. No pack is cut, and no version is tagged, from a tree that contains `1yzd0` without this change.

## Scope

**Problem statement:** ten flat alias files exist only for internal convenience, giving those modules two spellings and keeping ten server-owned names in the global scripts namespace.

**In scope:**

- Deleting the ten alias files.
- The retired-name warning, purge and reserved-name pin.
- Narrowing the alias table and eager registration.
- Rewriting importers and patch targets.
- The evaluator existence check and its receipt sequence.
- Censuses, the upgrade matrix, and the docs, ADR, memory record and changelog updates.

**Out of scope:**

- Removing the `server_impl` and `dashboard_handlers` aliases. That still needs an upgrade-protocol change that validates package modules, and a minimum upgrade-from version at or above it.
- Renaming modules, such as `mcp_tool_registry` to `tool_registry`.
- Editing historical wave evidence.

## Acceptance Criteria

- [ ] AC-1: The scripts root holds exactly two flat alias files (`server_impl.py` and `dashboard_handlers.py`) with their pinned bytes, and none of the ten retired names exists as a flat file. The alias table and eager registration list exactly the two, and `_RETIRED_FLAT_NAMES` lists exactly the ten. `RESERVED_MODULE_NAMES` is pinned to both tables and `wf_server`.
- [ ] AC-2: No module outside `wf_server/`, in production or tests, names one of the ten by its flat name under the stated predicate, and none uses `from wf_server import <evicted module>`. Both rules are enforced by a census with known-bad controls. `project_context_efficiency.py` is executed with its import error exposed, and it reaches the package module. The upgrade-mandatory modules pass the real `upgrade_protocol` validation against a pack without the ten.
- [ ] AC-3: `wf_reload_mcp` serves edited code for every moved module with one live module object each. That holds both from a current-tree start and from a 1.26 flat-module in-process state. A flat file with a retired name produces a `wf_server_info` diagnostic and a stderr warning naming it and saying to delete it, and the server still serves; the known-bad control restores a full flat copy (from `902f7edc`), and a negative case with no leftover asserts both warnings are absent.
- [ ] AC-4: Installed-runner fixtures from v1.25.0, v1.26.0 and the 1.27.0 source (the `v1.27.0` tag, else commit `902f7edc`), in paths containing a space, upgrade to a pack without the ten and reach a working server (`--dry-run` plus a stdio `wf_server_info`) with none of the ten present; the v1.26.0 and 1.27.0 fixtures remove them through the MANIFEST diff. An unproven-prune case (the installed MANIFEST removed before upgrading) keeps the files, the captured upgrade output of the `post_pruning` hook names each one with the instruction to delete it, and `wf_server_info` repeats the warning. A `post_pruning` hook that hits an unreadable scripts directory logs and does not abort the upgrade.
- [ ] AC-5: The evaluator resolves existence through the implementing path, with the fixture digest unchanged. A test loads the golden fixture from a layout with the package present and the flat files absent. A baseline receipt before the removal, and an after receipt with the same evaluator and fixture digest, are recorded; any cross-generation fail carries the attribution.
- [ ] AC-6: The ADR amendment, the index entries, the spec and architecture docs, the evaluator workflow doc, the code comments, memory record `1ywls` and the single changelog statement agree with the shipped behavior and give the fork migration. This change's own suites and new tests pass, and its edited docs validate.

## Tasks

- [ ] Evaluator step: resolve fixture existence through the implementing path, with the new-layout test; independent focused review; operator commit; baseline receipt on that commit.
- [ ] Land the flat-name census, with the stated predicate and its controls, as a red test first; then rewrite importers, patch targets, `import_module` calls, embedded scripts and bare-name assertions.
- [ ] Add `_RETIRED_FLAT_NAMES` with the startup warning, purge and reserved-name pin, and the report-only `post_pruning` warning; delete the ten alias files; narrow `_FLAT_ALIASES` and eager registration.
- [ ] Update the structure tests, helpers and mutation evidence (retired-file warnings, the stale flat-key purge, the census controls).
- [ ] Run the upgrade matrix (v1.25.0, v1.26.0, 1.27.0 source), the in-process 1.26 reload and a fresh install; record the after receipt; check graph ownership.
- [ ] Amend ADR `1yx4m`; update the index entries, spec, architecture docs, evaluator workflow doc, code comments, memory record `1ywls` and the changelog statement.
- [ ] Run the delivery lanes and final gates.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Evaluator step and baseline | implementer | readiness, `1yzd0` closed | Own reviewed, operator-committed step |
| Importer rewrite and removal | implementer | baseline recorded | Single write owner |
| Verification | code, qa, release, docs-contract, architecture reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/retrieval_eval.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/memory_cli.py`
- `.wavefoundry/framework/scripts/project_context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/decisions/`
- `docs/architecture/current-state.md`
- `docs/architecture/domain-map.md`
- `docs/architecture/layering-rules.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/review-and-evals.md`
- `docs/agents/memory/`

- `CHANGELOG.md` and `docs/ARCHITECTURE.md` are edited too.

## Affected Architecture Docs

- ADR `1yx4m` (dated amendment) and the decisions README index row.
- `docs/ARCHITECTURE.md`: its ADR index line.
- `docs/architecture/current-state.md`, `domain-map.md` and `layering-rules.md`: the alias descriptions and invariants, with the outside-consumer row split.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The change itself, with the guards that keep the retired names safe |
| AC-2 | required | A missed importer fails at runtime or is swallowed; the upgrade constraint must still hold |
| AC-3 | required | Reload is the live-edit path; a leftover flat file must not go unreported |
| AC-4 | required | Installed runners must still upgrade |
| AC-5 | required | The evaluator refuses the fixture otherwise |
| AC-6 | required | Forks need one accurate migration statement |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-25 | Round-3 repair reverified at receipt `review-policy-c00425fa6fc6a491f35d`: ARCH-R3-1 resolved; every lane and both council seats approve. Carried note (wording only): where Requirement 7 and the Risks row say the server repeats the warning at start, Requirement 2 governs, so the warning is both a `wf_server_info` diagnostic and stderr | readiness-review.md |
| 2026-09-25 | Readiness round 3 on the revision (receipt `review-policy-33cd8bbbf3a95cb325e4`): code, QA, release, docs-contract and both council seats (red-team, security) approve; architecture blocks ARCH-R3-1 (the census allowlist omitted the `post_pruning` hook's own name list). Repaired with the findings folded in: the allowlist and a known-bad control for the hook list; the superseded Decision Log row marked narrowed; the leftover also surfaces as a `wf_server_info` diagnostic (red-team: stderr reaches only host logs); the hook never raises; AC-3 negative case; AC-4 v1.25.0 wording, captured hook output, unreadable-directory case; ADR, layering-rules and changelog wording (retained-alias refusal kept, permanent leftover and stale flat import stated) | readiness-review.md |
| 2026-09-25 | Operator decision on a plan review: the MANIFEST-diff prune is the only deletion of the ten (they are framework-owned and unedited), and a leftover is warned about, not refused. This supersedes readiness implementation notes (1) (an unlinking upgrade hook) and (2) (passing the refusal remedy through `server.py`), and turns note (3) into the unproven-prune warning case in Requirement 7 and AC-4. Requirement 7 no longer claims v1.25.0 carries the ten files | Requirements 2 and 7; AC-3, AC-4; Decision Log |
| 2026-09-25 | Evaluator step implemented: `load_fixture_corpus` checks existence through `_implementing_path`, shared with `implementing_relevance_paths`; two tests load the golden corpus with the flat files absent and present. Independent review approved; its two low test findings were fixed, and the third (a shifted refusal code) was accepted. Awaiting the operator commit before the baseline receipt | evidence/e0p/ |
| 2026-09-25 | Readiness round 2 (receipt `review-policy-60db6ebc9b7c940b8775`): every lane and both council seats approve. Implementation notes carried from the round, none changing the plan: (1) old runners run the new pack's `upgrade_extensions` hooks, so a `post_extract` or `pre_pruning` hook explicitly unlinks the ten retired flat files, making removal independent of the MANIFEST-diff prune (the red-team's strongest alternative); the refusal then only catches fork merges; (2) when the refusal fires, `server.py`'s import-failure message must pass the refusal's own remedy through instead of advising `wf setup`, and AC-3's known-bad control asserts the operator-visible text; (3) AC-4 adds an unproven-prune case (no prior MANIFEST) and the ADR amendment states the loud-stop behavior when a leftover file remains; (4) the Rationale's reload probe is re-proven by AC-3 and AC-4 and its scratch evidence is cited at delivery. Verified during the round: the in-process `import server_impl` in the upgrade runner comes after pruning, so the refusal does not fire during a normal upgrade | readiness-review.md |
| 2026-09-25 | Readiness round 1 (receipt `review-policy-9a919bf44bf6a558e0c0`): code and QA approve; release, architecture, docs-contract and the red-team seat block. One bounded repair:
  - the retired names keep their stale-copy refusal, reload eviction and reserved-name pin through `_RETIRED_FLAT_NAMES`;
  - the old-runner mechanism is stated accurately;
  - the census predicate is stated and the counts re-derived;
  - `project_context_efficiency` is executed and the new-layout evaluator test is added;
  - the release framing is joint release with `1yzd0`, a single changelog statement, and a matrix of v1.25.0, v1.26.0 and the 1.27.0 source;
  - the complete stale-docs list and a dated ADR amendment are added | readiness-review.md |
| 2026-09-25 | Planned at the operator's request during wave `1yzd0` delivery review | this document |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-25 | Keep `server_impl` and `dashboard_handlers` flat | Installed 1.25/1.26 runners resolve every import of the upgrade-mandatory modules against flat stems, and those modules import these two | Remove all twelve now (every installed runner rejects the pack) |
| 2026-09-25 | Guard the retired names with `_RETIRED_FLAT_NAMES` (refuse, purge, reserve); refuse narrowed to warn by the operator decision below | Narrowing the alias table alone would drop the `1yzd0` stale-copy guard and the old-runner flat-key eviction for the ten, which the red-team reproduced | Delete the files and shrink the table only; keep ten refusing stub files |
| 2026-09-25 | Warn about any present retired flat file; do not refuse and do not delete it outside the MANIFEST prune (operator decision, superseding the refusal chosen at readiness) | The ten files are framework-owned and unedited, so the ordinary MANIFEST-diff prune is the right deletion authority. Every install that holds them (first shipped in v1.26.0) has a MANIFEST, so a leftover means only a missed or unproven prune; a warning to delete it is enough. Deleting without ownership evidence repeats the removed legacy-fallback hazard (`prune_framework.py`) | Refuse the import; an extra upgrade hook that unlinks the ten without the MANIFEST; delete only content-matched files |
| 2026-09-25 | Keep the fixture byte-identical and resolve existence in the evaluator | Rewriting the fixture changes its digest; resolving in the evaluator keeps one fixture and reuses `SERVER_PACKAGE_MODULES` | Rewrite the two relevance paths to package paths |
| 2026-09-25 | Ship with `1yzd0` in one release, stated once in the changelog | No released version then carries the ten aliases, forks migrate once, and ADR `1yx4m`'s permanent-surface statement is narrowed before release | Separate releases, with a one-release deprecation of the ten names |
| 2026-09-25 | Amend ADR `1yx4m` with a dated section | The narrowed claim never reached a release; a dated amendment keeps the history visible, as `1ye5y`'s scoped supersession did | A successor ADR; a silent in-place rewrite |

## Risks

| Risk | Mitigation |
| --- | --- |
| A fork or extension imports one of the ten flat names | Changelog migration; the names stay reserved; a leftover flat file is reported by the upgrade and at server start |
| A dotted patch target, `import_module` call or bare-name check is missed | The census covers every form in the stated predicate; the full suite runs |
| A missed rewrite in `project_context_efficiency` is swallowed | AC-2 executes it with the import error exposed |
| A release is cut between `1yzd0` and this change | Requirement 9 and the wave watchpoint forbid it |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
