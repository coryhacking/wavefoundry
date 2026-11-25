# Code-reviewer readiness review: wave 24buu

Owner: Engineering
Status: active
Last verified: 2026-11-24

- Lane: code-reviewer, readiness, fresh context, independent (did not author the specs or the primer).
- Read in full: wave.md; specs 24but, 24ax3, 24bn7, 24bn8, 24bn9; `.wavefoundry/work/24buu/upgrade-rehearsal.md`; `.wavefoundry/work/24buu/readiness/red-team.md`; `docs/agents/code-reviewer.md`; seed 209 readiness finding bar.
- Retrieval: MCP tools were loaded via ToolSearch. Gapfill: most code reads went through shell `sed`/`grep` on known line ranges in 5000 to 7000 line files, and `git show 03672b89:` was needed to read the 1.51.0 code, which the index does not hold.
- Executed (read-only): a zipimport probe with `python3 -I -B` and `PYTHONPYCACHEPREFIX=/private/tmp/claude-502/pycache-review`. With the 1.51.0 release zip on `sys.path` plus `<zip>/.wavefoundry/framework/scripts` appended, `embedded_model_bundle` resolved from the zip root and `contained_files` from the zip's scripts folder. This confirms 24bn7's mechanism is feasible.
- No repository file was edited.

## Verdict

**Not approved.** There are two demonstrated defects, both in 24but. The other four specs, and the wave-level revisions, are implementable and their load-bearing code claims hold.

## Findings

### CR-1. `churn_available` cannot detect an absent or unreadable index as specified (24but requirement 1, AC-7)

- Anchors: `index_state_store.file_commit_times`, `index_state_store.open_read_only`, `wf_server/memory_handlers._memory_ranked` (the `except Exception: commit_times = {}` guard).
- **Code fact.** `file_commit_times` returns `{}` without raising in three cases:
  - `open_read_only` returns `None` because the store is absent, unreadable or has the wrong schema version.
  - The query raises one of the `_SQL_ERRORS`.
  - Its docstring says "Empty on absent/unreadable store."
- **What still raises.** Only `sqlite_runtime.RuntimeUnavailable` / `StorageRecoveryRequired` and import faults reach the `except Exception` in `_memory_ranked`.
- **Consequence.** Requirement 1 defines `churn_available` as false "when the commit-time read ... fails". The read does not signal these failures. The Tasks and Serialization Points touch only `memory_handlers.py`. Followed as written, an absent or wrong-schema index reports `churn_available: true, target_churn: 0`. That is the "unavailable index reads as clean" case requirement 1 exists to prevent (F9). AC-7 says the read is "made to fail", which an injected exception satisfies, so AC-7 passes while the motivating case still ships wrong.
- **Repair.**
  - Give the read an availability signal, for example a variant or flag that tells "store unavailable" apart from "no rows". Add `index_state_store.py` to the Serialization Points.
  - Pin AC-7 with three fixtures: an absent store, a wrong-schema store and a raising read.
  - Add one control: with no file targets there is no read, and `churn_available` stays true.
- F9 is therefore only partly resolved.

### CR-2. AC-1's exact equality omits `churn_available` (24but AC-1 against requirement 1)

- Anchor: 24but AC-1, `memory_handlers.memory_brief_response`.
- **The contradiction.** Requirement 1 makes `churn_available` a field of `revalidation`. AC-1 requires `revalidation` to be *equal to* a four-key dict without it.
- **Consequence.** An implementation that follows requirement 1 fails AC-1. One that passes AC-1 drops the field that AC-7 requires. The required AC cannot pass as written.
- **Repair.** Add `"churn_available": true` to the expected object.

## Do the revisions resolve F1 to F14?

| Item | Resolved? | Basis |
| --- | --- | --- |
| F1 | Yes | 24ax3 requirement 5: an outside-layer deny or ask holds the route and gets no receipt. Requirement 7 adds a distinct upgrade body. AC-4 pins it with a known-bad case. See note N1 for the Codex gap. |
| F2 | Yes | Requirement 4 separates the holds. Requirement 2.3 and AC-5 cover the pattern rule. |
| F3 | Yes | 24bn7 keeps the member set (`upgrade_bundle._materializer` `allowed_runner` is unchanged) and resolves imports through zipimport. I probed it as feasible. AC-1 now requires passing `_materializer`. |
| F4 | Yes | 24bn8 requirement 2 adds identity-label matching. AC-3 uses the 1.51.0 bytes. Confirmed that `materialize_baseline_template` calls `vocabulary_profile.localize_template` with the incoming labels. |
| F5 | Yes | 24bn9 states it takes effect from 1.52.0 on. wave.md adds the second-hop rehearsal. |
| F6 | Yes | The digest is taken over the comparable form, and `_comparable_baseline` strips the owned marker regions and the date. This makes it stable across Phase 1 marker re-rendering. In `render_agent_surfaces.render_agent_surfaces`, `reconcile_lifecycle_prompt_baselines` runs before `reconcile_review_policy_surfaces`, so the replace-then-render-regions order fits. |
| F7 | Yes | 24but requirement 4 and AC-4 now target `review_policy.UPGRADE_POLICY_BLOCK`. The new-code `render_agent_surfaces` replays it through `reconcile_upgrade_policy_surface` inside the Phase 1 render child, so targets receive it on the 1.51.0 to 1.52.0 hop. |
| F8 | Yes | `--no-auto-cleanup` passed by `upgrade_handlers`, pinned by AC-2. See note N5. |
| F9 | Partly | See CR-1. |
| F10 | Yes | AC-6 names the cleanup summary. Since the migration now runs in Phase 1, the delegated primary summary should be empty too. |
| F11 | Yes | The Rationale names `build_pack.build_upgrade_bundle`. |
| F12 | Yes | AC-5 now reads "writes nothing and reports no `replaced` path", which matches the `continue` in `_compare_lifecycle_baselines`. |
| F13 | Yes | AC-2 is now a table comparison. |
| F14 | Yes | The ACs are in order. |

## Which process runs each change (primer question 3), verified

- **The Phase 1 render child runs new code on the 1.51.0 hop, on both the CLI and MCP paths.**
  - In `git show 03672b89:.../upgrade_wavefoundry.py` (lines 2254 to 2268), the 1.51.0 `phase_surface_rendering` spawns `SCRIPTS_DIR/render_platform_surfaces.py --repo-root --include-permissions --manifest` through `_run_upgrade_child` after Phase 0b extraction.
  - `SCRIPTS_DIR` is the installed path, so the child loads the extracted tree.
  - `child_tee.run` inherits `os.environ`, so `CLAUDE_CONFIG_DIR` and `CODEX_HOME` reach it.
  - Phase 1 precedes `phase_docs_gate` and `phase_index_update` in `main`.
- **The lifecycle findings are captured by incoming code.**
  - The zip's `upgrade_extensions.pre_extract` calls `lifecycle_baseline_report(persist=True)`.
  - That function runs the private incoming `render_agent_surfaces.lifecycle_baseline_drift` and stores the result in the lock verbatim, so 24bn8's new digest field survives the old primary.
- **The zip direct entry runs the zip's own code.** `__main__.py` is `upgrade_bundle.py` (`build_pack.build_upgrade_bundle`), and `_incoming_runner` runs the staged incoming `upgrade_wavefoundry.py`.
- **24bn9 runs in the primary**, so it is inert until 1.52.0 is installed, as the spec now says.

## Efficacy replays

| Spec | Conclusion |
| --- | --- |
| 24ax3 | Controls rehearsal items 2, 3 and 8, given the ordering in N2. |
| 24bn7 | Controls item 1. |
| 24bn8 | Controls items 4 to 6. |
| 24bn9 | Controls item 7 on the second hop only. |
| 24but | The counts and the block reach targets. The unavailable-index case fails (CR-1). |

## Implementation notes (non-blocking)

- **N1. 24ax3 requirement 5, Codex user-level config.** Requirement 5 is worded in Claude's vocabulary (deny, ask, allow). In Codex, the restriction is `disabled_tools` (and `tools.<old>` tables) on an old name. Treat it as holding the route, as the Boundaries sentence requires, and add one fixture beside AC-4.
- **N2. 24ax3 ordering.** `selected_permission_rules` keeps a managed old rule while the route is held, and the review hold lifts only once a receipt exists. So within the child, run the migration, then write the receipts, then run `render_claude_permissions`, or AC-6 fails.
  - The Phase 1 call gates the permissions render on `"claude" in platforms`. Run the migration and receipts outside that gate so a Codex-only project migrates.
  - The `--permissions-only` backstop branch must run the same steps.
  - The managed-settings paths per platform are unnamed in the spec. Name them in code and tests.
  - Requirement 2.2's `tools.<old>` table copy has no AC.
- **N3. 24bn7.** Append the zip's scripts path after the zip root so the top-level members win. Keep the standalone copied-bridge use of `upgrade_bundle.py` working. AC-1's run must not be a dry run, because `_incoming_runner` skips `retain` on a dry run. Consider covering the protocol-1 branch too: `upgrade_bridge_bootstrap.install`, then `retain`.
- **N4. 24bn8.**
  - Persist the `replaced` state into the lock, so that the delegated primary summary, the cleanup summary and any agent-invoked render in the lock window agree.
  - Gate the replacement to the upgrade render (lock findings present).
- **N5. 24bn9.** The Decision Log's rejection reason for the environment-variable alternative is factually wrong.
  - `upgrade_handlers` sets `WAVEFOUNDRY_STORAGE_OLD_MCP_PID` on every `wf_upgrade` child, and has since at least `599039d9`.
  - Consider honoring either the flag or that variable, which also covers a stale-loaded handler that predates the flag.
