# Red-team primer: wave 24buu readiness

Owner: Engineering
Status: active
Last verified: 2026-11-24

- mode: council-adversarial-primer
- depth: standard. The caller asked for 5 to 8 primer questions, so this primer gives 7.
- Artifacts read in full: wave.md, specs 24but, 24ax3, 24bn7, 24bn8 and 24bn9, and `.wavefoundry/work/24buu/upgrade-rehearsal.md`.
- Seeds read: 225 (red team) and 209 (readiness finding bar).
- Retrieval: MCP `code_outline`, `code_read` and `code_keyword` first.
  - Gapfill: some line-range reads and greps went through shell `sed` and `grep`, because the needed ranges sit in 7000-line files and shell output was cheaper. Every claim below was read in the tree.
  - Two read-only executions ran with `python3 -B` and `PYTHONPYCACHEPREFIX=/private/tmp/claude-502/pycache-redteam`: the plan-template comparison and the zip-entry import closure.
- Nothing in the repository was edited.

## thinking_stances_applied

- **Adversarial.** Tried to get grants past 24ax3's auto-receipt, and checked that 24bn8 cannot lose an edit to overwrite. Raced 24bn9's auto-cleanup against the MCP phase sequence. Produced F1, F4, F6 and F8.
- **First-principles.** For each spec, asked which process actually executes the changed code on the 1.51.0 to 1.52.0 hop. Produced F2, F5 and F7.
- **Simplicity.** Checked whether a smaller mechanism gives the same effect. Produced the zip `sys.path` alternative for 24bn7 and the label-normalization alternative for 24bn8.
- **Constructive and analogical.** Not applied separately; each finding carries its alternative.

## strongest_challenge

24ax3 turns an operator attestation into an upgrade side effect. As planned, this silently widens effective grants in exactly the case that motivated its own review gate.

- **Today.** `_review_held` (spec_tool_permissions.py) withholds every renamed tool on a legacy install until an operator writes `_RECEIPT`: "Operator reviewed the exact tool name across all effective host permission layers." The receipt exists because the server cannot see user-level or enterprise policy (`assess` docstring).
- **The plan.** Requirement 3 has upgrade write the same receipt bytes once the repository rules are clean.
- **What AC-4 requires.** A user-level `~/.claude/settings.json` that denies `mcp__wavefoundry__wf_close_change` produces a recommendation only, and "`wf_close_spec` is not withheld on that account."
- **The consequence.** That deny never matched `wf_close_spec`. After the upgrade restart, the tool the operator had denied is served and callable with no prompt.
  - The same happens for an ask rule.
  - It happens for any rule in enterprise managed settings, which the spec declines even to read.
  - It happens when `CLAUDE_CONFIG_DIR` or `CODEX_HOME` points the host somewhere other than `Path.home()`. This last case is inference from host conventions, medium confidence.
- **Why the spec contradicts itself.** Its boundary says "It never widens a grant." The step that removes the safeguard is labeled "Planner reading", not an operator decision. The operator said "read and recommend user level settings, but don't change them". That forbids writing user-level files. It does not authorize serving a tool the user layer denied.
- **Why the review gate will not catch it.** The rehearsal rerun in the watchpoint will not expose this, because the rehearsal explicitly did not exercise user-level settings. It would ship.

## best_alternative

**24ax3.** Keep the migration. Gate the receipt per route on two conditions:

1. Repository-ground assessment is clean. This needs `assess` to report repository holds separately from the review hold. Today both go into one `held` dict through `setdefault`.
2. The user-level scan finds no deny or ask rule on the old name without the identical rule on the new name.
   - Extend the scan to the readable managed-settings locations.
   - Honor `CLAUDE_CONFIG_DIR` and `CODEX_HOME`.
   - A user-level allow without a match only narrows the grant (the tool asks), so it is recommendation-only and does not block.

When condition 2 fails, keep the hold. Print the exact rule to add and the existing `spec-permissions` command.

Write a distinct receipt body, for example "Upgrade verified repository and readable user-level rules", and have `_review_held` accept either body. That way an upgrade-written receipt never claims an operator review that did not happen.

- **Better because:** it removes the five-tool lockout for the common case, the rehearsal shape with no user-level restriction. It never serves a tool that a readable layer denies.
- **Cost:** an operator with a personal deny still runs one command. One more constant, and a split of `assess`.

**Wave level.** Add a second rehearsal hop to the readiness evidence: a 1.52.0 candidate to a 1.52.x candidate. On the 1.51.0 to 1.52.0 hop, the primary phase runs 1.51.0 code (F5). Code in the primary phase therefore takes effect only one hop later.

## consequence_of_current_path

- 24ax3 ships a silent grant widening (F1).
- 24bn7 trades `ModuleNotFoundError` for `upgrade_protocol_invalid` (F3).
- 24bn8's plan-template fix is a no-op, and its replacement can strip renderer-owned blocks (F4, F6).
- 24but's recommendation never reaches target agents (F7).
- 24bn9 does nothing on the hop it targets, and on the next hop it collides with MCP `wf_upgrade` sequencing (F5, F8).

Most of this would surface only at the delivery rehearsal rerun. By then, repairs cost a delivery round each.

## recommendation

1. Return F1, F3, F4, F7 and F8 to moderator synthesis as readiness findings. Each is a seed-209 "would ship wrong behavior" or "AC cannot pass" case.
2. Route F1 to security-reviewer.
3. Route F5 and F8 to architecture-reviewer.

## evidence_basis

The code anchors in each finding, the rehearsal record, and the spec text.

## confidence

- **High:** F1 (code semantics plus the AC text), F3, F4, F5, F7 and F8.
- **Medium:** the host environment-variable sub-point of F1, and F6.

## primer_questions

1. **Receipt authority (security-reviewer).** May an upgrade write the receipt whose fixed text attests an operator review across all effective layers?
   - If yes, what stops a user-level or enterprise deny on an old name from being bypassed (AC-4)?
   - If no, is a distinct upgrade receipt body acceptable?
2. **Repository-ground holds (code-reviewer).** `assess` merges the repository holds and the review hold in one dict. How will requirement 3 decide that a route is "no longer held on repository grounds" without a refactor? What does it do with a pattern rule that matches the old name but not the new one, such as `mcp__wavefoundry__wf_*_change` in deny? That rule stays held, and no AC covers it.
3. **Which process runs each change on the 1.51.0 to 1.52.0 hop (architecture-reviewer).** The `wf` command runs the installed `upgrade_wavefoundry.py`. The primary phase therefore runs 1.51.0 code (comment at the `_emit_primary_summary_via_delegate_or_fallback` call). For each spec, which hop first runs it on the CLI path, the MCP path and the zip direct-entry path (`upgrade_bundle._incoming_runner` runs the incoming code)? Which rehearsal items should the delivery rerun still expect?
4. **How 24bn9 tells CLI from MCP.** MCP `wf_upgrade` runs the same primary command line (`upgrade_handlers`, the default phase `preflight_to_docs_gate` builds `--root --yes`). It then calls `update_index` and `cleanup` itself. What stops the new auto-cleanup from firing inside the MCP primary on 1.52 and later? And which summary sentinel does the MCP parser keep when it does fire?
5. **The real cause of the plan-template misclassification (qa-reviewer).** The `Last verified:` date is already normalized by `_comparable_baseline`. What evidence supports requirement 2 of 24bn8? Does a test reproduce the 1.51.0 bytes (`Change ID:`) rather than a date-only fixture?
6. **Where 24but's recommendation is read.** In a target repository, the agent reads `docs/prompts/upgrade-wavefoundry.prompt.md`. During the installing upgrade, only its `review-policy-upgrade` marker block is refreshed from fresh code (seed 160, the operating-memory bullet). Does 24but change `review_policy.UPGRADE_POLICY_BLOCK` and its pin in `test_review_policy.py`? If not, how does any target agent see the new rule?
7. **Writes in the cleanup phase.** 24bn8 replaces files and 24ax3 writes settings in cleanup, after the Phase 3 docs gate and the Phase 4 index. Who re-runs lint and the index for those files? And who re-renders the `wavefoundry:review-policy` block that a raw template overwrite removes from implement-wave and close-wave?

## efficacy_replay

**24but (memory revalidation counts and guidance).**
- **Motivating case:** a project under the cap, with unresolved or churned records, gets no recommendation.
- **The counts:** computed from `_memory_ranked`. They would be right in this repository, but they advise only.
- **Fails:**
  - In a target, the agent reads the rendered `UPGRADE_POLICY_BLOCK`, which still says to recommend only on `curation_required` or consolidation candidates. Seed 160 and the self-hosted copy change; the block every target receives does not (F7).
  - `target_churn` comes from the index store (`index_state_store.file_commit_times`). On any exception it silently returns `{}`, so an unavailable index reports 0 churn, which reads as clean. That is not the "existing git read" that requirement 6 claims (F9).
- **Over-flags:** older projects churn-flag most records on the first read. Accepted in the spec.

**24ax3 (spec-tool permission migration).**
- **Motivating case (rehearsal item 2):** three exact-name rules and two missing reviews.
- **Fixes it:** yes. The migration copies the rules, then writes the receipts. It controls the outcome.
- **Item 3, managed rule:** fixed only if the migration runs before `_ensure_rendered_permissions_backstop` in the `--cleanup` branch, or the render is rerun.
- **Wrongly passes:** a user-level or enterprise deny or ask (F1).
- **Misses:** pattern rules that match the old name only. These stay held, which is safe but unstated.
- **CLI on 1.51.0 to 1.52.0:** still depends on the operator running `--cleanup` by hand, because 24bn9 is inert on that hop.
- **MCP:** the primary summary is emitted before `update_index` and `cleanup`, so it still lists five holds. AC-5 does not say which summary must be empty (F10).

**24bn7 (release zip entry).**
- **Motivating case:** `ModuleNotFoundError: contained_files`.
- **The derivation:** it adds `contained_files`, `setup_commands` and `venv_bootstrap`. The executed closure over the four entry modules has 7 modules.
- **Fails anyway:** `upgrade_bundle._materializer` hard-codes `allowed_runner = {__main__.py, upgrade_bridge_bootstrap.py, subprocess_util.py, embedded_model_bundle.py}`. Any added top-level member raises "bundle contains an unexpected member", right after `retain` succeeds in `_incoming_runner`. AC-1 tests only the import, so it passes while the documented command still fails (F3).
- **Wrong file named:** the writer is `build_pack.build_upgrade_bundle`, not `upgrade_wavefoundry.py`. Both the Rationale and the Serialization Points name the wrong file (F11).

**24bn8 (replace unedited lifecycle prompts).**
- **Five prompts (rehearsal items 4 and 5):** replacing them would fix items 4 and 5, provided the write survives:
  - **Change-detection race.** Phase 1's new-code render may rewrite those files after the pre-extraction comparison. Requirement 4's "changed between the comparison and the write" check would then skip close-wave and implement-wave, which carry a `wavefoundry:review-policy` block.
  - **Marker block.** If the check is lax, writing the raw template drops that renderer-owned block (F6).
- **Plan template (item 6):** not fixed (F4). The cause is the incoming vocabulary transform, not the date.
- **AC-5:** cannot pass as written (F12).
- **Controls rather than advises:** yes, for the prompts.

**24bn9 (CLI runs cleanup).**
- **Motivating case (rehearsal item 7):** not fixed on the 1.51.0 to 1.52.0 hop through the `wf` command. That end message is printed by 1.51.0 code (F5). It is fixed on the next hop, or on the zip direct entry for protocol-2 targets.
- **Wrong behavior:** on the next hop, the MCP primary would also auto-clean, ahead of MCP's own `update_index` and `cleanup` (F8).
- **Controls the outcome.** Its skip conditions are sound in shape.

## Findings

Each finding is marked as a demonstrated plan defect or a wording note.

**F1. Auto-receipt widens effective grants. (24ax3; security)**
- Anchors: `spec_tool_permissions._review_held`, `spec_tool_permissions._RECEIPT`, `spec_tool_permissions.acknowledge`; 24ax3 requirement 3, requirement 4 and AC-4.
- **Demonstrated defect.** AC-4 requires serving a tool that a user-level deny covered under its old name. That contradicts the stated boundary "never widens a grant." Enterprise managed policy is unread by design, so it fails the same way.
- **Repair:** see best_alternative.

**F2. Repository-ground holds are not separable. (24ax3)**
- Anchor: `spec_tool_permissions.assess`. `_claude`, `_codex` and `_review_held` all write into one `held` dict with `setdefault`.
- **Demonstrated gap.** Requirement 3 as written cannot be computed from `assess`'s return value. No requirement names the refactor.
- **Inference:** an implementer may write all five receipts first. Repository holds still apply, but the persisted receipts then claim reviews for tools still held by a pattern rule, such as a deny on `wf_*_change`.
- **Repair:** add the split to requirement 3, and add a pattern-rule AC.

**F3. The zip's own allowlist rejects the added members. (24bn7)**
- Anchors: `upgrade_bundle._materializer` (`allowed_runner`), `upgrade_bundle._incoming_runner`, `build_pack.build_upgrade_bundle`.
- **Demonstrated defect.** After the fix, `retain` succeeds, then `_materializer(selected)` raises `upgrade_protocol_invalid: bundle contains an unexpected member`. AC-1 checks only the imports, so it passes while the motivating command still fails. `tests/test_upgrade_protocol.py` also pins the members (`subprocess_util.py`).
- **Repair options:**
  1. Derive `allowed_runner` from the same list, and add an end-to-end direct-entry AC.
  2. Simpler: have `upgrade_bundle` put `<zip>/.wavefoundry/framework/scripts` on `sys.path`, so lazy imports resolve from the pack's own feature members with zipimport. This needs no layout change, no allowlist change, and covers every future import.

**F4. The plan-template diagnosis is wrong. (24bn8)**
- Anchors: `render_agent_surfaces._comparable_baseline`, `render_agent_surfaces.materialize_baseline_template`, `vocabulary_profile.localize_template`, `upgrade_extensions.lifecycle_baseline_report`.
- **Demonstrated (executed).** `_comparable_baseline` already rewrites `Last verified: YYYY-MM-DD` to `{{generated_at}}`.
  - Taking the 1.51.0 template (`git show 03672b89:.wavefoundry/framework/install/plan-template.md`) with only the date substituted: it compares unequal to the incoming-code materialization of the same previous template. The only differing lines are `Change ID:` / `Change Status:` against `Spec ID:` / `Spec Status:`.
  - `localize_template` maps `Change ID` to `MEMBER_ID_LABEL`. The previous template is materialized with the incoming vocabulary, and the comparison runs in the private incoming renderer.
- **Consequences:**
  - Requirement 2 is a no-op.
  - AC-3's "Known bad: today it is reported as locally edited" is false for a date-only fixture. AC-3 can pass on a synthetic fixture while the rehearsal case still fails.
- **Repair:** normalize the shipped label lines in the comparable form, as the date already is. Or match the local copy against the previous template under identity localization as a second candidate. Fixture: the 1.51.0 bytes.

**F5. Old-code window. (24bn9, and the wave's efficacy claims)**
- Anchors: `upgrade_wavefoundry.main` (the "Phases 0–4 complete" message), the comment at the `_emit_primary_summary_via_delegate_or_fallback` call ("this process imported the OLD module before Phase 0b extraction"), and `.wavefoundry/bin/wf`, which goes through `wf_cli.py` to the installed `upgrade_wavefoundry.py`.
- **Demonstrated plan error.** 24bn9's Decision Log says that replaying the rehearsal, "the manual step disappears." On that path, the 1.51.0 primary prints the old message.
- **Repair:** correct the efficacy claim. State the expected rehearsal result per hop. Optionally rehearse 1.52.0 to 1.52.x.

**F6. Replacement versus Phase 1 render and marker regions. (24bn8; overwrite safety)**
- Anchors: `render_agent_surfaces._baseline_marker_pairs`. Executed: implement-wave and close-wave carry `<!-- wavefoundry:review-policy:begin -->`. Also `upgrade_wavefoundry._lifecycle_baseline_findings` ("never infer previous templates after extraction") and `upgrade_wavefoundry.phase_surface_rendering`.
- **Demonstrated gap.** The comparison is captured before extraction. Phase 1's new-code render can rewrite those files afterwards. Requirement 4's change check is then ambiguous:
  - Measured on raw bytes, it skips the two files that motivate 24but.
  - Measured leniently, a raw template write deletes the renderer-owned block.
- The captured finding stores no content digest to compare against.
- Writes in cleanup also fall after the docs gate and the index.
- **Repair:**
  - Record the comparable-form digest in the captured finding.
  - Splice in the template body while keeping the marker blocks, or re-render them in the same phase.
  - Consider running the replacement in the Phase 1 new-code render child while the upgrade lock holds captured findings, so the docs gate and the index cover it.

**F7. 24but misses the upgrade policy block that targets actually receive. (24but)**
- Anchors: `review_policy.UPGRADE_POLICY_BLOCK`, `review_policy_reconcile.UPGRADE_POLICY_DESTINATION`, `tests/test_review_policy.py`, which asserts `curation_required=true` in the block. Seed 160's operating-memory bullet says upgrade "replays only the shared review-policy upgrade marker from fresh code ... so the current upgrade can recommend Review memories."
- **Demonstrated defect.** AC-4 pins seed 160 and the self-hosted copy. In the self-hosted copy, lines 726 to 771 are that marker region, and a hand edit there is overwritten by the renderer. AC-4 can pass while every target's upgrade prompt states the old rule. Scope lists neither `review_policy.py` nor its test.
- **Repair:** change `UPGRADE_POLICY_BLOCK` and its pin. Have AC-4 assert on the rendered block.

**F8. Auto-cleanup would fire inside the MCP primary on 1.52 and later. (24bn9)**
- Anchors: `wf_server/upgrade_handlers` (the `wf_upgrade` command builder; the default phase passes only `--root --yes`; `next_step` says "Continue with wf_upgrade(phase='update_index'), then wf_upgrade(phase='cleanup')"), and `upgrade_wavefoundry.main`'s primary branch.
- **Demonstrated gap.** Nothing in the primary distinguishes the CLI from MCP. "MCP flow out of scope" is not a mechanism, and no AC proves that the MCP primary does not auto-clean. If it does:
  - The lock is removed before MCP's `update_index`.
  - The 24ax3 and 24bn8 work then runs only in the auto-cleanup.
  - MCP's own `cleanup` hits "no lock".
- **Repair:**
  - Add an explicit discriminator, such as a CLI-only flag, or the `WAVEFOUNDRY_STORAGE_OLD_MCP_PID` environment variable MCP already sets.
  - Add an AC that the MCP-shaped invocation does not auto-clean.
  - Check sentinel handling when cleanup prints a second summary.

**F9. Churn availability is silent. (24but)**
- Anchor: `wf_server/memory_handlers._memory_ranked`, which catches `except Exception: commit_times = {}` around `index_state_store.file_commit_times`.
- **Partly a demonstrated defect:**
  - Requirement 6's "reuses the existing git read" is factually wrong.
  - An index failure reports `target_churn: 0`, so the recommendation silently under-fires.
  - AC-2's equality holds trivially in that case.
- **Repair:** state the source correctly, and consider a `churn_available` boolean.

**F10. Which summary must be empty is unspecified. (24ax3)**
- Anchors: `upgrade_wavefoundry._spec_tool_permission_summary`, and the primary summary emitted before the fresh-code phases.
- **Wording, with test risk.** On MCP, `data['summary']` from the primary still lists the holds. Have AC-5 name the cleanup summary, and say that the primary summary may still list them.

**F11. Wrong file named. (24bn7)**
- Anchor: `build_pack.build_upgrade_bundle` (`archive.write(source.parent / "embedded_model_bundle.py", ...)`).
- **Demonstrated factual error** in the Rationale ("upgrade_wavefoundry.py lines 1379 to 1381") and the Serialization Points. Scope also says `build_pack.py` release checks are out of scope, while the fix lives in `build_pack.py`.

**F12. AC-5 cannot pass as written. (24bn8)**
- Anchor: `render_agent_surfaces._compare_lifecycle_baselines`. With `incoming_matches` and not `upstream_changed`, the loop `continue`s and emits no finding at all.
- **Demonstrated defect.** On a second upgrade with the same pack, the installed previous template equals the incoming one. No `already_current` is reported. AC-5 should say "no finding and no write".

**F13. AC-2's "Claude render of effective rules" names nothing. (24ax3)**
- Anchors: `render_platform_surfaces.render_claude_permissions` and `selected_permission_rules`. They render only the managed allow list, never deny or ask.
- **Wording.** Name the oracle: assess plus the file contents, and the managed allow list after the backstop.

**F14. AC order. (24ax3)**
- AC-8 is listed before AC-7. Wording only.

## Security notes for security-reviewer

**24ax3.**
- F1 and F2.
- Make sure the copied rules never come from the `wavefoundryManagedAllow`-claimed entries. `assess` filters them, so the migration must apply the same filter, or managed grants become unmanaged permanent grants.
- `wf_upgrade` is agent-callable. Under requirement 3, an agent-triggered upgrade writes what was previously an operator-only receipt. That is acceptable only with a distinct receipt meaning.

**24bn9.** Cleanup restarts the dashboard and unlinks owned archives (`phase_cleanup`). Running it automatically is fine on the CLI, but must never run inside the MCP primary (F8).

**24bn8.** The overwrite scope is "comparable-equal", not byte-identical. It ignores newlines, the `Last verified` date and the renderer marker regions. The spec should say so, and must preserve the marker regions (F6).
