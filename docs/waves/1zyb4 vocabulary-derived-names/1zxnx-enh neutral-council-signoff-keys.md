# Neutral Council Signoff Keys

Change ID: `1zxnx-enh neutral-council-signoff-keys`
Change Status: `implemented`
Owner: framework-operator
Status: implemented
Last verified: 2026-10-06
Wave: 1zyb4 vocabulary-derived-names

## Rationale

The two council signoff keys, `wave-council-readiness` and `wave-council-delivery`, embed the container name. Waveforge, a downstream distribution, calls its container a "set" and its item a "wave", so to its operators the keys name the wrong tier. The keys are not record vocabulary in `vocabulary_profile.py`; they are literals in the gates, the evidence model and the prompts. Renaming them to `council-readiness` and `council-delivery` makes them tier-neutral for every distribution with no profile setting.

The keys are also history: 220 tracked `events.jsonl` ledgers and 340 wave records carry them, and ledgers are never rewritten (event identities and the review-policy receipts hash them). So the rename must write the new keys while every reader keeps accepting the old ones.

Code-grounded facts this plan relies on:

- The expected approval actor is derived from the key prefix, not configured: `review_evidence.py` maps `operator-signoff` to `operator`, any key starting `wave-council-` to `wave-council`, and every other key to itself (the status-row derivation and the approval validator, `approval actor must be ...`). A new key `council-readiness` would therefore demand actor `council-readiness` unless the rule changes. `moderator_role` in the config phases is stored by `lifecycle_gate_support._read_wave_council_policy` but read nowhere else.
- Phase rules compare exact strings: `approval_record_phase` (claim `approval:wave-council-readiness` means readiness), the approval validator (`wave-council-readiness` requires `approval_phase=readiness`, `wave-council-delivery` requires delivery), `server_impl._review_event_recovery_phase`, the readiness-approval test in `wf_review_event_response`, `lifecycle_gates` council results, and the readiness defaults in `lifecycle_gates.council_signoff_gate` and `wf_implement_wave_response`.
- Required keys come from `docs/workflow-config.json` `wave_review.phases.<phase>.signoff_key`, defaulting in `lifecycle_gate_support` (normal and fail-closed branches) and `review_evidence.required_review_status_keys`. Many target configs carry no `phases` (`migrate_wave_review_policy` writes only `enabled` and `delivery_mode`), so they run on the defaults; this repository's config names both keys explicitly.
- docs-lint re-renders every declared wave's review-evidence projection from its ledger and fails on any difference ("review evidence projection is stale"); for non-closed waves it also re-renders the bounded status block, whose rows are labelled by the required keys. A change of the default key spelling would therefore make every non-closed wave's status block stale in every target at upgrade, and the upgrade only reprojects waves when the review policy moved (`review_policy_upgrade.plan_review_policy_upgrade`), which also marks them for re-Prepare.
- The signoff key IS part of the review-policy receipt digest: `lifecycle_gate_support` passes the `normalize_wave_review_policy` result, a copy of the config's whole `wave_review` object including `phases.<phase>.signoff_key`, to `review_policy.policy_input_snapshot(wave_review=...)`, which hashes `dict(wave_review)`. Editing a config's key spelling therefore rotates the receipt of every readied wave and lapses its approvals. A config with no `phases` hashes differently from one with explicit phases already today.

## Requirements

1. **Canonical keys.** Add to `review_evidence.py` `COUNCIL_SIGNOFF_KEYS` (`council-readiness`, `council-delivery`), `LEGACY_COUNCIL_SIGNOFF_KEYS` (old to new), and `canonical_signoff_key(key)` (legacy to new, identity otherwise), plus `is_council_signoff_key(key)` (a canonical council key, or any key starting `wave-council-`, which keeps today's rule for custom keys).
2. **Write new keys.** `wf_review_event` canonicalizes `signoff_key` before validation and event identity, so every new approval carries `signoff_key` `council-*` and `claim_id` `approval:council-*`. An old-key input is accepted during the alias period (Requirement 9) and the response carries an info diagnostic naming the new key. Dry run and create behave alike.
3. **Read old keys everywhere.** Every comparison of a signoff key or approval claim compares canonical forms: approval lookup by claim (`_approval_rows` and its callers, so the latest approval or withdrawal wins across both spellings), `approval_record_phase`, the approval validator's phase rules, finding re-check membership (`signoff_key in affected`), the finding-actor fallback that excludes council keys (`not key.startswith("wave-council-")`, which becomes `not is_council_signoff_key(key)`), `review_status_signoff_keys` (one row per canonical key), the `typed_keys` set and the `preserve_generated` test in `render_review_status_projection` (a generated approval or withdrawal line is dropped when the canonical form of its key is in the canonical typed set), the legacy prose branch (`authorization` detection and `signoff_recorded`), the review authority's `signoff_current`/`signoff_recorded`, `lifecycle_gate_support._required_wave_council_signoffs`, `lifecycle_gates` council results, `server_impl._review_event_recovery_phase`, the readiness test in `wf_review_event_response`, and the dashboard rows. Config values are canonicalized at these comparison sites only, so a config naming the old keys requires the same canonical keys as one naming the new keys; configs are never rewritten. The policy object itself is not canonicalized, because it feeds the receipt digest (Requirement 12).
4. **Expected actor unchanged.** `is_council_signoff_key` keys (both spellings) require actor `wave-council`, and the same predicate replaces every `startswith("wave-council-")` test (status-row actor, approval validator, finding-actor fallback); operator and specialist rules are unchanged. The role, its doc `docs/agents/specialists/wave-council.md`, seed 215, `moderator_role`, the `prepare-council` verdict line `moderator: wave-council`, `PREPARE_COUNCIL_ROSTER_TOLERANCE` and both `_COORDINATE_STEMS` keep the name `wave-council`.
5. **History stays byte-identical.** The review-evidence projection renders each record's key as recorded, never canonicalized, so the projection of every existing ledger is unchanged; no `events.jsonl` and no wave record under `docs/waves/` is edited.
6. **Sticky status labels.** Implemented inside `review_evidence.render_review_status_projection`, the one renderer shared by docs-lint, the lifecycle gates, the dashboard and the upgrade reprojection, so every caller produces the same block. In the bounded status block of a non-closed wave, a canonical council key is rendered with the spelling that block already uses for it, and that sticky spelling is the key the WHOLE row is rendered with: `review_status_rows` interpolates it into the Next action text (the reverification, fresh-approval and record-approval messages) and the Signoff cell, and `review_status_human_table` renders those cells, so every cell of the row (Signoff, Why, Next action) uses it. Canonical forms stay internal to comparison. A block with no row for the key uses the new spelling. Existing open and readied waves in every target therefore render exactly as before, and new waves show `council-*`.
7. **New defaults.** The default keys in `lifecycle_gate_support` (both branches), `review_evidence.required_review_status_keys` (including the malformed-policy branch), the readiness fallbacks in `lifecycle_gates.council_signoff_gate` and `wf_implement_wave_response`, and the remediation and advisory texts (`lifecycle_gate_support` readiness remediation, `server_impl._prepare_council_location_advisory`, the `wf_review_event` docstring example) use the new keys.
8. **Docs and prompts.** Every live mention of the keys moves to the new spelling at its canonical source, then renders: seeds 001, 007 (including the example config), 050, 100, 170, 176, 180, 190, 215, 233, 236, 237; the review-wave lifecycle template; the `wf-prepare-wave` registry body; `docs/prompts/` outside framework-owned reconciled regions (12 files), `docs/agents/` (2), `docs/contributing/` (4), `docs/specs/mcp-tool-surface.md`, AGENTS.md, README.md. This repository's `docs/workflow-config.json` is NOT edited: its key spelling feeds the receipt digest, reads accept both spellings, and the edit belongs to the retire-alias follow-up. Seed 160 and the rendered upgrade prompt gain one sentence: the new keys are written from this release, the old keys stay valid in configs, tool calls and history, and nothing needs rewriting.
9. **Alias period.** Old keys are accepted as `wf_review_event` input and as config values from the release that ships this change through at least the next minor release. Retiring that input alias is a separate change (the retire-alias follow-up) that must first migrate target configs and, in the same release, update the two replacement-side `review_policy_reconcile.py` region strings that still name the old keys (Requirement 11). Reading old keys from ledgers and wave records is permanent, because history is immutable.
10. CHANGELOG: one Unreleased entry stating the new keys, the permanent read compatibility, the alias period and that no ledger, wave record or config is rewritten.
11. **Deferred region strings.** The four `review_policy_reconcile.py` strings that name `wave-council-readiness` are not edited in this change, so no reconciled carrier changes and no target wave is marked for re-Prepare at upgrade. Two of them (in `KNOWN_SECTION_REPLACEMENTS`, the old-side matcher of the implement-wave Readiness Handoff pair and of the prepare-wave typed-approval pair) are legacy matchers that must keep matching text written by earlier releases, so they stay permanently. The other two (the replacement side of the council-review and prepare-wave pairs) name the key agents are told to record; the old key there stays valid because reads accept both spellings and writes convert, and the retire-alias follow-up updates only these two.
12. **Digest input stays spelling-independent.** `review_policy.policy_input_snapshot` maps each council `signoff_key` value in the `wave_review.phases` it hashes to the LEGACY spelling before hashing (`council-readiness` to `wave-council-readiness`, `council-delivery` to `wave-council-delivery`), on a copy, leaving the caller's object untouched. Canonicalization happens only at comparison sites, never in the digest input. A config naming the old keys and one naming the new keys therefore produce the same digest, every existing receipt digest is unchanged, and a config with no `phases` keeps today's digest.

## Scope

**Problem statement:** the council signoff keys name the container tier, which reads as the wrong tier in a distribution with a different vocabulary, and they are fixed in immutable history.

**In scope:** Requirements 1 to 12; tests for every new behavior; regenerated `lifecycle-gate-golden.json` and `lifecycle-gate-pre-configured-golden.json`; the `register-surface-handler-digests.json` entry for `wf_review_event` (docstring example).

**Out of scope:**

- Renaming the actor or role `wave-council` (doc, seed 215, `moderator_role`, verdict line, roster tolerance, coordinate stems). Named follow-up, if Waveforge still needs it: it needs the same read-alias treatment for the actor in 220 ledgers and touches the role surfaces, so it is a separate plan.
- The retire-alias follow-up (separate change, no earlier than the release after the one that ships this change): migrate target configs to the new keys (including this repository's `docs/workflow-config.json`, disclosing the one re-Prepare per readied wave), update the two replacement-side `review_policy_reconcile.py` strings, and stop accepting old keys as tool input. The two legacy matchers stay.
- A reconcile-scan pattern for the old keys: they stay valid, so a mention is not a broken instruction (and `test_wf_cli` requires zero findings in this repository, where other changes' plans and history mention them).
- Rewriting any ledger, wave record, archive, CHANGELOG entry or other change's plan (`docs/plans/1vwye-...` keeps its one mention).
- Making the key a vocabulary-profile setting: neutral keys need no setting.

### Census

Predicate: a line containing `wave-council-readiness` or `wave-council-delivery`, outside `.git` and `.wavefoundry/index`. Command:

```
rg -c --hidden -g '!.git' -g '!.wavefoundry/index' 'wave-council-(readiness|delivery)' .
```

At HEAD `06c02e63`, outside `docs/waves/`: framework scripts `review_evidence.py` 9, `lifecycle_gate_support.py` 7, `server_impl.py` 6, `lifecycle_gates.py` 2, `render_agent_surfaces.py` 1 (edit); `review_policy_reconcile.py` 4 (deferred, Requirement 11); tests and fixtures 18 files (edit or extend; the two lifecycle goldens 40 and 22 lines are regenerated); seeds 13 files, the review-wave template 1, rendered skills 3 (edit or re-render); `docs/prompts` 12 files (outside reconciled regions), `docs/agents` 2, `docs/contributing` 4, `docs/specs` 1, AGENTS.md 1, README.md 1 (edit); `docs/workflow-config.json` 2 (deferred to the follow-up); CHANGELOG.md 2 and `docs/plans/1vwye-...` 1 (not edited). Under `docs/waves/`: 608 files, of them 220 `events.jsonl` and 340 wave records (never edited).

## Acceptance Criteria

- [x] AC-1: `canonical_signoff_key` maps each old key to its new key and leaves `council-readiness`, `council-delivery`, `operator-signoff` and specialist keys unchanged; `is_council_signoff_key` is true for both spellings and for a custom `wave-council-x` key, false for `council-review` and specialist keys.
- [x] AC-2: `wf_review_event` approvals given the old key or the new key write `signoff_key: council-*` and `claim_id: approval:council-*`; the old-key call returns an info diagnostic naming the new key; the actor must be `wave-council` for both spellings and the phase rules hold for both.
- [x] AC-3: On a fixture wave whose ledger holds only old-key approvals, the prepare activation gate, `wf_implement_wave`, the review gate and the close gate pass exactly as they do for the same ledger with new keys; a mixed ledger (old-key readiness, new-key delivery) closes; across spellings the later of an approval and a withdrawal decides the state, in both orders.
- [x] AC-4: A config with old `signoff_key` values, one with new values and one with no `phases` yield the same required keys at every phase, and no run writes `docs/workflow-config.json`.
- [x] AC-5: After the change, `wf_validate_docs` passes, and a SHA-256 manifest of every file under `docs/waves/` except the files of this wave's own folder, taken before implementation starts and again before close, is identical, so every recorded projection still matches its ledger.
- [x] AC-6: An open fixture wave whose status block labels `wave-council-readiness` keeps that label after a new-key approval is recorded and shows it approved; a newly created wave's block shows `council-readiness`; docs-lint is clean on both. Subtests: an existing block holding a pending, a stale and a withheld council row labelled `wave-council-*` renders byte-identical before and after the change (Signoff, Why and Next action cells), and a generated old-key approval line is dropped by `preserve_generated` when the ledger holds the new-key approval.
- [x] AC-7: The regenerated lifecycle goldens differ from the previous ones only by the two key tokens (a test or recorded diff check replaces the old tokens in the old golden and compares).
- [x] AC-8: The census command, rerun, returns old keys only in `docs/waves/`, CHANGELOG past entries, the four deferred `review_policy_reconcile.py` strings and their reconciled regions in `docs/prompts/`, `docs/workflow-config.json`, `docs/plans/1vwye-...`, this change doc, the alias code and its tests, and the fixtures that model legacy ledgers.
- [x] AC-9: `register-surface-handler-digests.json` changes only the `wf_review_event` digest, with a description sentence naming this change, and its test passes.
- [x] AC-10: The CHANGELOG Unreleased section carries the Requirement 10 entry with the alias period.
- [x] AC-11: `policy_input_snapshot` returns the same digest for a config with old `signoff_key` values and the same config with new values; the digest for each of the old-key config and a no-`phases` config equals the digest the pre-change code computes for it (pinned values); the caller's policy object is unchanged after the call; and the current receipt of this repository's open wave is not superseded by the change.

## Tasks

- [x] Open `framework_edit_allowed`; close it after the script and test edits.
- [x] `review_evidence.py`: constants, canonicalization at every comparison, raw-key projection, sticky labels, new defaults (AC-1, AC-3, AC-5, AC-6).
- [x] Before any edit, record the SHA-256 manifest of `docs/waves/` outside this wave's folder (AC-5).
- [x] `review_policy.policy_input_snapshot`: legacy-spelling mapping on a copy of the hashed phases, with pinned-digest tests (AC-11).
- [x] `lifecycle_gate_support.py`, `lifecycle_gates.py`, `server_impl.py` helpers and the `wf_review_event` docstring; dashboard rows (AC-2 to AC-4).
- [x] Tests for AC-1 to AC-6; regenerate the lifecycle goldens and run the AC-7 check; update the handler-digest fixture (AC-9).
- [x] Open `seed_edit_allowed`, edit the seeds, close it; edit the template and registry body (not the reconcile strings); re-render surfaces; edit the live docs (not `docs/workflow-config.json`).
- [x] CHANGELOG entry; census rerun recorded in the Progress Log (AC-8, AC-10).
- [x] `wf_validate_docs`, then `run_tests.py` last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 evidence model and gates | software-engineer | - | Requirements 1 to 7 and 12, goldens, handler digest |
| ws-2 seeds, prompts, docs | implementer | ws-1 | Requirements 8 to 10, render, census |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/lifecycle_gate_support.py`, `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/`, `.wavefoundry/framework/scripts/tests/fixtures/lifecycle-gate-golden.json`, `.wavefoundry/framework/scripts/tests/fixtures/lifecycle-gate-pre-configured-golden.json`, `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `.wavefoundry/framework/seeds/`, `.wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md`
- `.claude/skills/wf-prepare-wave/SKILL.md`, `.codex/skills/wf-prepare-wave/SKILL.md`, `.agents/skills/wf-prepare-wave/SKILL.md`
- `docs/prompts/`, `docs/agents/wave-coordinator.md`, `docs/agents/specialists/wave-council.md`
- `docs/contributing/agent-team-workflow.md`, `docs/contributing/discovery-delivery-workflow.md`, `docs/contributing/feature-wave-lifecycle-overview.md`, `docs/contributing/review-and-evals.md`
- `docs/specs/mcp-tool-surface.md`
- `.wavefoundry/framework/scripts/review_policy.py`
- Root-level files edited (not path tokens): AGENTS.md, README.md, CHANGELOG.md.

Notes: only the `wf_review_event` `@mcp.tool` handler source changes (its docstring), so only its digest is recomputed; every other `server_impl.py` edit is in helpers. The tool-surface goldens carry no descriptions and stay unchanged. Dependency: none on `1zxnw` semantically; both edit `render_agent_surfaces.py` (registry text), so this change is implemented after `1zxnw` in wave E and rebases onto it. `review_policy_reconcile.py` is not edited here (Requirement 11).

## Affected Architecture Docs

N/A for the hub and child docs: no boundary, flow or verification-topology change; the evidence model gains a canonicalization step at comparison sites only. `docs/specs/mcp-tool-surface.md` (key names in the `wf_review_event` contract) is edited under Requirement 8.

## Platform Behavior

Pure string handling on ledger records, config values and projections; no file is moved, locked or rewritten beyond the ordinary event and projection writes, so behavior is identical on Windows, macOS, Linux and WSL2. The sticky-label read of the status block uses the existing projection parser, which already accepts LF and CRLF records; the projection keeps each record's newline style as today.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | One mapping every reader uses. |
| AC-2 | required | New events must carry the neutral keys. |
| AC-3 | required | Existing and mixed ledgers must keep passing every gate. |
| AC-4 | required | Existing configs must keep working without rewrites. |
| AC-5 | required | History is immutable and must still lint. |
| AC-6 | required | Upgrades must not stale open waves in targets. |
| AC-7 | important | Proves the golden churn is the rename only. |
| AC-8 | required | Rename complete in live sources. |
| AC-9 | required | The handler-digest test fails otherwise. |
| AC-10 | important | Distributions need the alias period. |
| AC-11 | required | A spelling must never rotate receipts or lapse approvals. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-06 | Planned from the verified Waveforge request R1(4); census taken at HEAD `06c02e63`. | Census command in Scope. |
| 2026-10-06 | Implementation note (readiness re-check): in `policy_input_snapshot`, copy the nested `phases` mapping and each phase mapping before rewriting `signoff_key` to the legacy spelling; a shallow `dict()` copy of `wave_review` would mutate the caller's policy. | Readiness finding N1 follow-up; AC-11 asserts the caller's object is unchanged. |
| 2026-10-06 | AC-5 manifest taken before any edit: SHA-256 of every file under `docs/waves/` outside this wave's folder (2106 files). | Manifest digest `bd4cb99a7cbf851d`; rechecked identical after implementation. |
| 2026-10-06 | Implemented Requirements 1 to 7 and 12: canonical keys and predicates in `review_evidence.py`, canonical comparison at every site (approval rows keyed by canonical claim, phase, affect relation, actor, status keys, prose branch, `signoff_recorded`, generated-line drop), sticky labels in `render_review_status_projection` via `review_status_display_keys` (also used by the dashboard rows), new defaults, `wf_review_event` input canonicalized before validation and identity with an info `signoff_key_alias` diagnostic, digest input mapped to the earlier spelling on a copy. | `review_evidence.py`, `review_policy.py`, `lifecycle_gate_support.py`, `lifecycle_gates.py`, `dashboard_lib.py`, `wf_server/server_impl.py`. |
| 2026-10-06 | Tests: new `test_council_signoff_keys.py` (22 tests: AC-1, AC-2, AC-3 legacy/new/mixed ledgers through prepare, implement, review and close, AC-4, AC-6, AC-11 pinned digests); existing tests updated where outputs now name the new key. | Scratch focused runs green; full scratch suite in the implementer report. |
| 2026-10-06 | AC-7: `lifecycle-gate-golden.json` regenerated (40 lines) equals the previous file with only the two key tokens replaced (49 tokens, recorded check); the frozen `lifecycle-gate-pre-configured-golden.json` takes the same token replacement (22 lines). AC-9: only the `wf_review_event` digest changed. | Scratch diff check: token-only diff True. |
| 2026-10-06 | AC-5/AC-11 on this repository: full docs-lint clean; every non-closed declared wave (1zxnz, 1zxo0, 1zyb2, 1zyb3, 1zyb4) recomputes its current receipt digest exactly; prepare, review and close dry-run statuses, diagnostic codes and status-block rows are identical to the pre-change code (only `required_council_signoffs` spelling differs); closed waves keep their topology snapshot. | Scratch comparison against a pre-change tree. |
| 2026-10-06 | Requirement 8: seeds 001, 007, 050, 100, 170, 176, 180, 190, 215, 233, 236, 237, the review-wave template, the `wf-prepare-wave` registry body (three skills re-rendered), 12 `docs/prompts` files outside reconciled regions, `docs/agents` (2), `docs/contributing` (4), `docs/specs/mcp-tool-surface.md`, AGENTS.md and README.md moved to the new keys; seed 160 and the rendered upgrade prompt (outside the owned region) gained the upgrade sentence. Not edited: `docs/workflow-config.json`, `review_policy_reconcile.py`. | Census below. |
| 2026-10-06 | AC-8 census rerun (same predicate): outside `docs/waves/` the old keys remain only in the alias code (`review_evidence.py` 3, `review_policy.py` 2, `server_impl.py` 1 docstring), the four deferred `review_policy_reconcile.py` strings and their two reconciled regions (`docs/prompts/council-review.prompt.md` 1, `docs/prompts/prepare-wave.prompt.md` 1), `docs/workflow-config.json` 2, CHANGELOG past entries 2, `docs/plans/1vwye-...` 1, and tests and fixtures that model legacy ledgers or exercise the input alias (13 test files, 2 fixtures). | `rg -c` per the Scope predicate. |
| 2026-10-06 | Gapfill: shell `rg`/`grep` used for the census and site discovery (MCP code tools not loaded in the implementer session). | Census command. |
| 2026-10-06 | Full scratch suite (`run_tests.py --no-cache`): 11590 tests across 167 files; three files failed, then passed on rerun: `test_events_only_residue_census.py` (the new test named a legacy prose helper; rewritten through the authority facade), and the load-sensitive `test_indexer.py` 100K-row budget and `test_subprocess_util.py` grandchild timing, both green rerun alone (471 tests OK across the four rerun files). Mutation probes in scratch: reading old keys literally, removing the digest mapping, removing the sticky spelling and not converting input each fail the new tests; the first and third also fail docs-lint on this repository's open waves. | Scratch logs. |
| 2026-10-06 | Delivery repair DEL-1a: new `test_dashboard_rows_keep_the_sticky_label` drives a legacy-labelled status block plus a new-key approval through the real writer and asserts `dashboard_lib._review_evidence_dashboard_state` keeps the earlier row spelling in `approvals` and the projection. | Probe: passing `status_keys` instead of `display_keys` to the table and rows fails the test. |
| 2026-10-06 | Delivery repair DEL-2: the unreleased 1.29.0 CHANGELOG bullets for waves 1zls7 and 1zime respelled to `council-readiness`; the 1zxnx bullet notes the cross-rename replay. | CHANGELOG diff. |
| 2026-10-06 | Delivery repair DEL-3a: `wf_review_event` replay matches an approval first recorded under the earlier key: when the canonical identity has no bundle, it also looks up the identity with each earlier spelling (`legacy_signoff_key_spellings`) and accepts that record's digest computed with the earlier spelling. No ledger is rewritten and new records keep canonical identities. New `test_a_legacy_key_approval_replays_after_the_rename` (legacy record written below the input wrapper; retries in both spellings and both modes leave the ledger byte-identical; a new context appends with the canonical identity). No `@mcp.tool` handler source changed. | Probes: disabling the legacy lookup, or comparing only the canonical digest, each fail the test. |
| 2026-10-06 | Gapfill: shell `grep`/`sed` used for site discovery in the delivery repair (MCP code tools not loaded in the repair session). | Repair session. |
| 2026-10-07 | Delivery repair verification: full scratch suite (`run_tests.py --no-cache`, no concurrent probes) ran 11598 tests across 167 files; one failure, `test_context_efficiency.py` `test_candidate_scale_p95_budgets` (10-candidate warm p95 10.7 ms against a 10 ms budget), passed alone on rerun (86 tests OK): a timing flake under suite load, unrelated to the repair. Touched files `test_council_signoff_keys.py` (24) and `test_vocabulary_prompt_names.py` (27) pass; `wf_validate_docs` clean. | Scratch run log. |
| 2026-10-07 | Repair: new `LifecycleCompatibilityTests.test_a_legacy_key_approval_with_different_evidence_is_a_conflict` (legacy-key approval written below the canonicalizing wrapper, then same context_id with different evidence in both spellings, dry_run and create): `review_event_identity_conflict`, ledger byte-identical. Kills the mutant adding the stored bundle's own request digest to `replay_digests` (4 subtests fail). Scratch `--file`: test_council_signoff_keys 25 ok, test_server_tools_lifecycle 614 ok. CHANGELOG bullet attributed `Wave 1zyb4 / 1zxnx.` | Repair session. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-06 | Rename the keys only; keep actor and role `wave-council`. | Smallest coherent option: the key names the phase approval, the actor names the role, and the expected actor is one derivation rule; renaming the role touches the role doc, seed 215, config `moderator_role`, the verdict line, roster tolerance and coordinate stems, and needs its own read alias over 220 ledgers. | Rename the actor value without the role: actor and role slug disagree and `moderator_role` contradicts the gate. Rename actor and role here: doubles the change. |
| 2026-10-06 | Canonicalize at comparison, render history as recorded. | Ledgers are never rewritten and docs-lint compares projections byte for byte; canonical comparison makes old and new approvals equivalent without touching history. | Rewrite ledgers: breaks event identities and receipts. Canonicalize projections: stales every recorded projection. |
| 2026-10-06 | Sticky status labels in non-closed waves. | A default-spelling change would otherwise stale every open or readied wave in every target at upgrade, and the only upgrade reprojection path also marks waves for re-Prepare. | Reproject at upgrade: forces re-Prepare churn. Keep old defaults: new targets keep the old keys. |
| 2026-10-06 | Map council keys to the legacy spelling in the digest input, never canonicalize the digest input (coordinator decision). | Keeps every existing receipt digest and lets either spelling hash alike. | Canonicalize to the new spelling in the digest: changes every explicit-phase config's digest and lapses readied approvals in every target. |
| 2026-10-06 | Defer the four `review_policy_reconcile.py` region strings to the retire-alias follow-up (coordinator decision). | Editing them is a carrier change, which marks every open or readied target wave for re-Prepare at upgrade; the old key there stays valid because reads accept both and writes convert. | Update them now: consistent prose, but re-Prepare churn in targets for a cosmetic rename. |
| 2026-10-06 | Role rename stays a named follow-up only, not planned now (coordinator decision). | Smallest coherent change ships first. | Plan it now. |
| 2026-10-06 | Never rewrite configs; canonicalize their values at comparison sites only; defer this repository's config to the retire-alias follow-up (coordinator decision). | Zero churn for targets; the config's `wave_review` object feeds the receipt digest, so a hand edit here would rotate readied receipts. | Upgrade migration of config values: moves the config bytes and, with the reconcile prose change, adds nothing but churn. |
| 2026-10-06 | No reconcile-scan pattern for the old keys. | The old keys stay valid; flagging them would be noise and would break `test_wf_cli` here. | Scan as retired: misreports valid text. |
| 2026-10-06 | Independent of `1zxnw`, implemented after it. | No semantic dependency; one shared file. | Declare a hard dependency: none is real. |
| 2026-10-06 | Sticky spelling is implemented by passing a display key into the review-status projection; every comparison inside it stays canonical. | Signoff, Why and Next action then all keep a wave's existing spelling, with no projection churn on open waves. | Rewrite rows to the new key (churns every open wave's projection). |
| 2026-10-06 | The old-key input notice is an info diagnostic, not an advisory tag. | The sanctioned advisory-site set is pinned by a test, and the notice changes nothing about readiness. | Add a new advisory site (widens a pinned contract for an informational message). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Project prompts keep the old key inside reconciled regions until the retire-alias follow-up, while seeds teach the new key. | Both spellings are accepted and writes convert, so the mixed wording is valid; the follow-up updates the regions together with the config migration. |
| A comparison site is missed and an old-key approval stops satisfying a gate. | AC-3 runs every gate on legacy, new and mixed ledgers; the census lists every code site; the full suite runs on this repository's 220 real ledgers through docs-lint (AC-5). |
| Shared files with earlier waves: `server_impl.py` (A, B, C), `lifecycle_gate_support.py` (B, path helpers), `render_agent_surfaces.py` (`1zxnw`). | Wave E lands last; rebase on B's `lifecycle_gate_support.py`; implement after `1zxnw`. |
| Agents in targets keep calling `wf_review_event` with the old key from project prompts not yet reconciled. | Accepted and canonicalized with an info diagnostic during the alias period; seed 160 tells upgraders. |
| A distribution configured a custom `wave-council-*` key. | `is_council_signoff_key` keeps the old prefix rule, so its expected actor is unchanged. |
