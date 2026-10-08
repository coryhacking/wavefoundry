# Prompt-Name and Council-Key Follow-Through

Change ID: `200xx-enh prompt-name-and-council-key-follow-through`
Change Status: `implemented`
Owner: framework-operator
Status: implemented
Last verified: 2026-10-07
Wave: 200xy security-follow-ups

## Rationale

Wave `1zyb4` lets a distribution rename the tier-named lifecycle prompts (change `1zxnw`) and writes tier-neutral council signoff keys (change `1zxnx`). Both left named follow-ups. A fresh install under a prompt-name profile with a rename chain can reach a state where a later render refuses with a migration conflict, which a distribution's operators cannot repair without reading renderer internals. The reconcile scan reports a renamed key's default shortcut but not its default aliases, so stale phrases such as "Ready wave" survive a profile rename unreported. And this repository still names the old council keys in its own config and in two reconciled prompt regions, which `1zxnx` deferred only because, at planning time, a config spelling change would have rotated review-policy receipts.

Brief: finish the two `1zyb4` changes; consumers are distribution maintainers (fresh installs, reconcile findings) and this repository's own operators (council key wording); success is a converging render on a fresh profiled install, alias findings in the scan, and the new council keys in this repository's config and generated prompt text with no receipt rotated. Wave `1zyb4` closed and was committed in `404e4950`; this change was first planned against the `1zxnw` and `1zxnx` change documents and its facts are now re-verified against that code.

Code-grounded facts (verified against HEAD `404e4950` on 2026-10-07):

- `render_agent_surfaces` runs `migrate_profile_prompt_names` before `render_skills` and `reconcile_lifecycle_prompt_baselines`. When the manifest is absent or unreadable, `migrate_profile_prompt_names` returns early with a diagnostic under a non-default profile and records nothing, but the render continues: `reconcile_lifecycle_prompt_baselines` still materializes missing lifecycle prompts at the profile's derived paths (`LIFECYCLE_PROMPT_BASELINES` destinations use `vocabulary_profile.prompt_doc`). When the manifest is readable, the migration records every pending key through `_record_applied_prompt_name`, even when that key's source file is absent, so a later materialization at the derived path is already recorded. The manifest is created outside the renderer: by `docs_gardener.ensure_manifest` (`default_manifest_payload`, no `prompt_names`) or by the install agent (seed 012 step 2.9, seed 100 step 7). On a fresh install the first render comes earlier: seed 012 step 2.5 runs seed 050, whose items 15 and 20 run `wf render-surfaces`, before step 2.9 writes the manifest. So a render that runs before any manifest exists writes profile-named prompts with no record; the next render, with a manifest, plans moves from the default names and, in a chain such as the `tests/fixtures/profiles/prompt-names.json` asset (`implement-wave` to `implement-set` while `implement-change` takes `implement-wave`), finds the target already occupied by different content and raises. The conflict sequence is `inferred` from the code; AC-1's reproducer executes it. Three later passes also act at profile-derived paths: `reconcile_review_protocol_surfaces` creates a missing `create_if_missing` carrier, `reconcile_review_policy_surfaces` raises `missing review-policy lifecycle carrier` when such a carrier is absent, and `reconcile_context_efficiency_surface` creates its carrier when missing. Several of those carriers are lifecycle prompts at profile-derived paths, so skipping only the baseline write would make the policy pass raise on the same render.
- `reconcile_scan._profile_prompt_name_tables` reports, per overridden key, the default public path, agent path, skill name and shortcut, but not `DEFAULT_PROMPT_NAMES[key]["aliases"]` (for example `Ready wave` on `prepare-wave`). Its `current` set already holds current shortcuts and current aliases (`vocabulary_profile.shortcut_aliases`), so a token that is a live alias is never reported today.
- `docs/workflow-config.json` names `wave-council-readiness` and `wave-council-delivery` under `wave_review.phases`. `review_policy._digest_wave_review` maps `council-readiness` and `council-delivery` to the legacy spelling on a copy before hashing, so either spelling in the config yields the same receipt digest (`1zxnx` Requirement 12, AC-11).
- `review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS` holds four strings naming `wave-council-readiness`: two old-side legacy matchers (the implement-wave Readiness Handoff pair and the prepare-wave typed-approval pair, which must keep matching text written by earlier releases) and two replacement sides (the `council-review.prompt.md` pair and the prepare-wave pair). `1zxnx` Requirement 11 deferred the two replacement sides because editing a carrier's reconciled text makes `review_policy_upgrade.plan_review_policy_upgrade` plan carrier edits, and any planned carrier edit marks every open or readied declared wave in a target for re-Prepare at upgrade. Carrier text is not a receipt digest input (`review_policy.policy_input_snapshot` hashes the `wave_review` policy, lanes, review policies, change bodies, requested lanes, phase gates and sensors). The table is applied only by `review_policy_reconcile.plan_reconciliation` and `apply_reconciliation`, through `reconcile_lifecycle_sections(root)` and the upgrade's `review_policy_upgrade`; `wf render-surfaces` never applies it, and this repository is never upgraded. Its targets are exact-text prose sections, not marker-managed regions.

## Requirements

1. **No unrecorded profile names.** Under a non-default prompt-name profile, no renderer pass writes a file at a mapped key's profile-derived public prompt or agent prompt path in a render where `migrate_profile_prompt_names` could not read the manifest record (manifest absent, unreadable, not an object, or an invalid `prompt_names`). Those writes are skipped for that render, and any pass that requires or creates a file at such a skipped path also skips that path for the render instead of raising or creating it: `reconcile_review_protocol_surfaces`, `reconcile_review_policy_surfaces` and `reconcile_context_efficiency_surface`. The existing migration diagnostic also says that the lifecycle prompts at profile names were not materialized and that a rerun after the manifest exists will create them. The set of passes is derived by that rule (every write whose destination is `vocabulary_profile.prompt_doc(key)` or `vocabulary_profile.agent_prompt_doc(key)` for a key whose slug differs from its default); the implementer records the census. Under the default profile, or with a readable manifest, behavior is unchanged. Note (plan only, no seed edit): on a fresh install under a non-default profile, carrier verification at seed 012 step 2.5 finds the profile-path carriers absent until step 2.9 writes the manifest and the next render creates them; the migration diagnostic above covers that state.
2. **Alias findings.** For each overridden key, `_profile_prompt_name_tables` also reports each default alias as a shortcut-shaped phrase (and on the guru `description:` line, as shortcuts are), suggesting the key's current shortcut. The existing `current` set (current shortcuts and current aliases) is unchanged, so a default token reused by any current shortcut or alias is still never reported; a test pins that. Under the default profile the table stays empty.
3. **Config spelling.** This repository's `docs/workflow-config.json` names `council-readiness` and `council-delivery` as the two `signoff_key` values; nothing else in the file changes.
4. **Region strings.** The two replacement-side strings in `review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS` (the `council-review.prompt.md` pair and the prepare-wave typed-approval pair) name `council-readiness`. For each, a legacy pair is added whose old side is the current replacement text exactly, so a carrier already reconciled by an earlier release converges to the new text. The two existing old-side matchers are unchanged. This repository's two prompts are updated by running `review_policy_reconcile.reconcile_lifecycle_sections(root)` against it (the same function the upgrade applies), which rewrites the two exact-text sections in `docs/prompts/` and nothing else.
5. **Disclosure.** One CHANGELOG entry states that reconciled prompt text now names the new council keys, that the upgrade therefore marks open or readied waves for one re-Prepare in repositories that hold them, and that the earlier keys stay accepted everywhere. Seed 160 is not edited (`1zxnx` already added the key sentence). The entry text is recorded in this change's Progress Log; change `1zyv1` (the wave's last change) writes it under the existing `## [1.29.0]` heading in its final CHANGELOG pass.

## Scope

**Problem statement:** two `1zyb4` follow-ups are open, and this repository still writes the old council keys in its own config and generated text.

**In scope:**

- Requirements 1 to 5 and their tests.

**Out of scope:**

- Retiring the old council keys as `wf_review_event` input or as config values in target repositories (a later release, after the `1zxnx` alias period).
- Migrating target repositories' configs.
- Renaming the `wave-council` actor or role.
- Codex `apply_patch` gating (Wavefoundry renders no Codex hook).
- Shortcut resolution in `server_impl.get_prompt` through the manifest (the separate `1zxnw` follow-up).

## Acceptance Criteria

- [x] AC-1: On a fresh fixture target under the `prompt-names` profile asset with no manifest, a render followed by `docs_gardener.ensure_manifest` and a second render completes without raising, ends with every lifecycle prompt at its profile path, a manifest whose `prompt_names` lists every overridden key, and a third render that writes nothing. Fails today with the migration conflict at the second render.
- [x] AC-2: The first render in AC-1 exits cleanly (no exception, including no `missing review-policy lifecycle carrier`), writes no file at a mapped key's profile-derived prompt or agent prompt path from any pass, and its diagnostic names the skipped materialization; under the default profile the same sequence writes exactly what it writes today (byte comparison).
- [x] AC-3: Under the `prompt-names` profile, `reconcile_scan` reports a document line holding a bold or backticked `Ready wave` with the suggestion `Prepare set`, and reports nothing for a token that is a current shortcut or a current alias (a regression pin on today's `current` set); under defaults this repository's scan findings are unchanged.
- [x] AC-4: `policy_input_snapshot` computed for this repository's config before and after the Requirement 3 edit is identical, and no open or readied wave in this repository has its current receipt superseded by the edit.
- [x] AC-5: The reconciler, given a carrier holding the original legacy text, a carrier holding the current replacement text, and a carrier holding the new text, converges all three to the new text, and the third is a no-op; the two old-side matchers still match their legacy text.
- [x] AC-6: After `reconcile_lifecycle_sections(root)` runs against this repository, `docs/prompts/council-review.prompt.md` and `docs/prompts/prepare-wave.prompt.md` name `council-readiness` in their reconciled regions, and no other file under `docs/prompts/` changed.
- [x] AC-7: The `1zxnx` census command, rerun, no longer finds the old keys in `docs/workflow-config.json`, the two replacement-side strings or their reconciled regions; the remaining hits are the ones `1zxnx` AC-8 lists minus those, plus the two added legacy pairs. The rerun is recorded in the Progress Log.
- [x] AC-8: The CHANGELOG entry text carrying the Requirement 5 disclosure is recorded in the Progress Log and present under `## [1.29.0]` after the `1zyv1` CHANGELOG pass.
- [x] AC-9: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `framework_edit_allowed`.
- [x] `render_agent_surfaces.py`: carry the migration's record status into the materializing passes and skip mapped profile-path writes when unreadable, including the skip in `reconcile_review_protocol_surfaces`, `reconcile_review_policy_surfaces` and `reconcile_context_efficiency_surface`; record the writer census in the Progress Log (AC-1, AC-2).
- [x] `reconcile_scan.py`: default aliases in the profile table (AC-3).
- [x] `review_policy_reconcile.py`: two replacement strings and two legacy pairs (AC-5).
- [x] Tests in `tests/test_vocabulary_prompt_names.py`, the reconcile-scan tests and the review-policy reconcile tests (AC-1 to AC-5), each confirmed failing against the unfixed code in a scratch copy.
- [x] Close `framework_edit_allowed`.
- [x] Edit `docs/workflow-config.json` (AC-4) and run `review_policy_reconcile.reconcile_lifecycle_sections(root)` on this repository (AC-6).
- [x] Record the CHANGELOG entry text in the Progress Log for the `1zyv1` CHANGELOG pass; census rerun (AC-7, AC-8).
- [x] Run `wf_validate_docs`, then the full suite last (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 renderer and scan | software-engineer | - | Requirements 1 and 2 |
| ws-2 council keys | implementer | - | Requirements 3 to 5 |

## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/reconcile_scan.py`, `.wavefoundry/framework/scripts/review_policy_reconcile.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/workflow-config.json`
- `docs/prompts/council-review.prompt.md`, `docs/prompts/prepare-wave.prompt.md`
- Within the wave this change lands third, after `200v1` and `200v2` (`render_agent_surfaces.py` is shared with `200v2`) and before `1zyv1` (`reconcile_scan.py` is shared, and its final render runs after these prompt updates).

## Affected Architecture Docs

N/A: the renderer change narrows when an existing pass writes, the scan gains entries in an existing table, and the council-key edits change wording and one config value; no boundary, flow or verification topology changes. `docs/architecture/layering-rules.md` (the `1zxnw` paragraph on the manifest record) is checked and edited only if it states when profile-named prompts are first written.

## Platform Behavior

String, JSON and path-derivation changes with no new file operations: the skip removes writes, and the reconciler writes carriers through the existing helper that preserves each file's newline style, so behavior is identical on Windows, macOS, Linux and WSL2. Manifest paths stay repository-relative POSIX on every platform.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | A profiled fresh install must converge. |
| AC-2 | required | Proves the skip and zero change under defaults. |
| AC-3 | important | Stale aliases are a reconcile gap, not a failure. |
| AC-4 | required | A spelling edit must not lapse approvals. |
| AC-5 | required | Already reconciled targets must converge. |
| AC-6 | important | This repository's generated text. |
| AC-7 | important | Confirms the follow-through is complete. |
| AC-8 | required | Targets must learn about the one-time re-Prepare. |
| AC-9 | required | Change-local health. |

## Progress Log

| Date | Update | Evidence |
| ---- | ---- | ---- |
| 2026-10-07 | Planned from the `1zyb4` watchpoints and the `1zxnx` deferrals; claims verified against the working tree and the `1zxnx` change document. | Rationale facts. |
| 2026-10-07 | Revised after readiness review round 1 (five findings); facts re-verified against HEAD `404e4950`, where wave `1zyb4` is committed. | Rationale facts; Decision Log. |
| 2026-10-07 | Implemented Requirement 1. `ProfilePromptMigration` gains `record_readable`; `unrecorded_profile_prompt_paths` returns the public and agent prompt paths of every key whose profile slug differs from its default when the record was unreadable (empty otherwise, and always empty under the default profile). The migration diagnostic adds that the lifecycle prompts at the profile's names were not materialized and that a rerun after the manifest exists creates them. | `render_agent_surfaces.py`. |
| 2026-10-07 | Writer census (every write, creation or requirement at `vocabulary_profile.prompt_doc(key)` or `agent_prompt_doc(key)` in a render): `reconcile_lifecycle_prompt_baselines` (`LIFECYCLE_PROMPT_BASELINES` profile destinations), `reconcile_review_protocol_surfaces` (both calls; registry carriers at the review-wave public and agent paths and create-wave), `reconcile_review_policy_surfaces` (renderer blocks at prepare, review, close, implement and agent review paths; the `missing review-policy lifecycle carrier` raise), `reconcile_context_efficiency_surface` (create-wave), and `render_skills` declared prompt-doc creations (a declared `prompt_doc` is a declaration literal, skipped when it equals a skipped path). Each takes `skip_paths`. Not in the census: `migrate_review_plan_prompt` (review-plan, unmapped), `migrate_change_prompt_renames` (default literal paths, not profile-derived), the manifest repair, scaffold baselines, the upgrade-policy carrier and the Guru tier-2/3 surfaces (no prompt paths); the profile migration itself runs only with a readable record. | Census by `rg` for `prompt_doc(` and `agent_prompt_doc(` over the scripts and the registries. |
| 2026-10-07 | Implemented Requirement 2: each default alias is a phrase candidate suggesting the key's current shortcut; `current` unchanged. Implemented Requirement 4: `_COUNCIL_REVIEW_TYPED_AUTHORITY` and `_PREPARE_TYPED_APPROVAL` name `council-readiness`; each gains a legacy pair (appended last, so existing pair indices hold) whose old side is the earlier text exactly; the two old-side matchers are unchanged. | `reconcile_scan.py`, `review_policy_reconcile.py`. |
| 2026-10-07 | Tests: `test_vocabulary_prompt_names.py` `FreshProfiledInstallTests` (AC-1, AC-2: profiled fresh target render, `ensure_manifest`, render, render; default profile sequence byte-identical to the same sequence with the skip forced off), `test_scan_reports_a_default_alias_but_not_current_names` and `test_a_default_alias_is_reported_with_the_current_shortcut` plus a current-alias pin (AC-3); `test_review_policy.py` `test_council_key_replacements_converge_from_every_earlier_text` and `test_legacy_matchers_naming_the_earlier_key_still_match` (AC-5); `test_declared_extension_skills.py` `test_a_skipped_prompt_doc_is_not_created_and_its_skill_waits`. Against the unfixed code in scratch every new test failed, and the AC-1 sequence raised `prompt name migration blocked: docs/prompts/close-wave.prompt.md -> docs/prompts/close-set.prompt.md: both exist` at the second render. Fixed code: prompt names 32 OK, review policy 107 OK, reconcile scan 67 OK, declared skills 47 OK, council signoff keys 25 OK, vocabulary census 5 OK, profile literal census 8 OK. | Scratch runs via `run_tests.py --file`. |
| 2026-10-07 | Mutation probes in scratch, each restored: removing the skip from the policy pass, the baseline pass, the protocol pass or the context pass; an always-empty skip set; a skip set computed under defaults; dropping the diagnostic text; dropping the alias candidates; dropping aliases from `current`; disabling either legacy pair; the old key in a replacement side; ignoring `skip_paths` in declared creations. Every probe failed its tests. | Scratch. |
| 2026-10-07 | AC-4: receipt for wave `200xy` recomputed with `lifecycle_gate_support._prepare_policy_state` before and after the `docs/workflow-config.json` edit (scratch first, then this repository): `policy_input_digest` `ae8bfb271d84f71e7f81aa142dd937841d023488ef405e27326ec0a6820225f1` and receipt `review-policy-e94625ce98673c7ec841` both times, `receipt_append_required` false. `200xy` is the only non-closed wave in this repository. Docs-lint passed in scratch after the config edit. | Scratch script `receipt.py`. |
| 2026-10-07 | AC-6: `review_policy_reconcile.reconcile_lifecycle_sections(root)` run on this repository returned exactly `docs/prompts/council-review.prompt.md` and `docs/prompts/prepare-wave.prompt.md`; the word diff of each is the one key token. A dry `plan_reconciliation` before the code change planned no edits. `docs/architecture/layering-rules.md` checked: it does not state when profile-named prompts are first written, so it is not edited. AC-3 defaults: this repository's `scan_repo` findings are 0 rows with both the old and the new `reconcile_scan.py`. | Command output. |
| 2026-10-07 | AC-7 census rerun (`rg -c --hidden -g '!.git' -g '!.wavefoundry/index' 'wave-council-(readiness\|delivery)' .`, outside `docs/waves/`): `docs/workflow-config.json` and both reconciled prompt regions no longer appear; `review_policy_reconcile.py` 5 (one comment, the two old-side matchers, the two added legacy pairs); alias code `review_evidence.py` 3, `review_policy.py` 2, `server_impl.py` 1; `docs/plans/1vwye-...` 1; tests and legacy-ledger fixtures. CHANGELOG has no hit (none at HEAD either). | Census output. |
| 2026-10-07 | Proposed CHANGELOG bullet for `1zyv1` (under `## [1.29.0]`): "Prompts reconciled by the upgrade now name the tier-neutral council key `council-readiness`, and this repository's own review config uses `council-readiness` and `council-delivery`. Because the reconciled prompt text changes, the upgrade marks each open or readied wave for one re-Prepare in repositories that hold one, together with the earlier key change in this release. The earlier keys `wave-council-readiness` and `wave-council-delivery` stay accepted everywhere. A fresh install under a prompt-name profile no longer writes renamed lifecycle prompts before the prompt-surface manifest exists, so the next render converges instead of stopping on a name conflict, and the reconcile scan also reports a renamed prompt's earlier aliases." | AC-8 text. |
| 2026-10-07 | Gapfill: shell `rg`/`grep`/`sed` used for code discovery and the census (MCP code tools not loaded in this implementer session). | This log. |
| 2026-10-07 | Full scratch suite (`run_tests.py --no-cache`): first run 11643 tests across 168 files, one file failed: `test_render_agent_surfaces.py` (2 errors, two render-order mocks whose lambdas did not accept the new `skip_paths` keyword); the mocks now accept keywords, the file passes alone (146 OK), and a second full run passed: 11643 tests across 168 files OK. Under the `prompt-names` second-profile run, `test_review_policy.py` and `test_reconcile_scan.py` report `no unittest summary` with 0 failures, the same on the unfixed code (pre-existing, not attributable). | Scratch logs. |
| 2026-10-07 | Delivery-review repair DEL-4(b): `FreshProfiledInstallTests` gains a Guru-enabled variant (`docs/agents/guru.md` present) whose first render writes nothing at a renamed key's prompt paths; dropping `skip_paths` from the second `reconcile_review_protocol_surfaces` call in `render_agent_surfaces` fails it in a scratch copy (killed, restored). | `test_a_guru_enabled_first_render_also_skips_profile_paths`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-07 | Skip profile-path writes while the manifest record is unreadable, rather than record at manifest creation. | The renderer cannot record without a manifest, and a readable manifest already gets every pending key recorded; the gap is only the render with no record. This keeps one owner (the migration) for `prompt_names`. | Write `prompt_names` at creation in `docs_gardener.ensure_manifest` and seed 100: claims names applied that may not be, and the seed path relies on prose. Let the renderer create the manifest: takes over an artifact the gardener and the install agent own. |
| 2026-10-07 | Suggest the key's current shortcut for a default alias. | Simplest correct suggestion; every alias resolves to the same prompt. | Same-position current alias: a positional pairing the profile does not define. |
| 2026-10-07 | Edit this repository's config now. | With the digest mapping from `1zxnx`, the spelling no longer feeds the receipt, which was the only reason for the deferral. | Wait for the alias retirement: leaves this repository writing the old keys. |
| 2026-10-07 | Update the two replacement strings now, with legacy pairs for the current text, and disclose the one-time re-Prepare. | Requested follow-through; legacy pairs make already reconciled targets converge. | Keep deferring to the alias retirement (the `1zxnx` plan): no re-Prepare now, but this repository and targets keep teaching the old key. Change the strings without legacy pairs: reconciled targets silently keep the old text. |
| 2026-10-07 | Skip the skipped paths in the three carrier passes too, not only in the baseline pass. | `reconcile_review_policy_surfaces` raises on an absent `create_if_missing` carrier and the other two passes create carriers at profile-derived paths, so a baseline-only skip makes the first render raise or still writes unrecorded names. | Let the policy pass raise: the fresh install fails at seed 050. |
| 2026-10-07 | Keep the skip; reject writing default-named prompts while the record is unreadable and letting the next migration move them. | Default-named files written under a non-default profile are themselves a migration input the record does not cover, and any project edit between the two renders turns the move into a conflict, the failure this change removes. | Write default names first: relies on the next render's move succeeding. |
| 2026-10-07 | Limit Requirement 2 to reporting default aliases; keep a regression pin that a current alias is not reported. | `_profile_prompt_name_tables` already puts current aliases in `current` (verified), so the earlier claim that it did not was false. | Re-add aliases to `current`: a no-op edit. |
| 2026-10-07 | Update this repository's two prompts with `reconcile_lifecycle_sections(root)`. | `wf render-surfaces` never applies `KNOWN_SECTION_REPLACEMENTS` and this repository is never upgraded; the reconciler is the one owner of those exact-text sections. | Hand-edit the prompts: a second writer that can drift from the table. Render surfaces: does nothing for these sections. |
| 2026-10-07 | Coordinator decision (cross-change): change `1zyv1` writes the CHANGELOG under `## [1.29.0]`; this change records its entry text. | One owner for the final CHANGELOG pass. | Each change edits CHANGELOG. |
| 2026-10-07 | Operator decision: Requirement 4 ships in the same unreleased 1.29.0 as `1zxnx`, so targets re-Prepare once rather than twice; stale-alias findings suggest the key's current shortcut. | 1.29.0 is unreleased; one combined re-Prepare is cheaper than two. | Defer to the alias retirement. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The `1zxnx` code differs from its change document. | Facts re-verified against HEAD `404e4950`; AC-4 recomputes the digest on the landed code. |
| A distribution relied on profile-named prompts appearing before its manifest existed. | The diagnostic names the rerun; the next render materializes them with the record. |
| Shared files with other changes in this wave (`render_agent_surfaces.py` with `200v2`, `reconcile_scan.py` with `1zyv1`). | Wave serialization order: this change lands after `200v2` and before `1zyv1`. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
