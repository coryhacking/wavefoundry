# Distribution Seams and Neutral Council Role

Change ID: `200ew-enh distribution-seams-and-neutral-council-role`
Change Status: `implemented`
Owner: framework-operator
Status: implementing
Last verified: 2026-10-07
Wave: 200ey containment-and-distribution-seams

## Rationale

The Waveforge maintainers, who ship the framework under their own vocabulary, reported four seams (public report R1, R2, R7, R9) where a distribution has to patch framework internals or live with framework vocabulary. Prompt keys built by string concatenation in the reconcile scan are invisible to a distribution's literal-key census. The member-document reader, which a distribution's lifecycle extension tools need, is private. The council moderator is named `wave-council`, so a distribution that calls its delivery unit something other than a wave still records, displays and lints a role named after waves; wave `1zyb4` (change `1zxnx`) made the signoff keys neutral (`council-readiness`, `council-delivery`) but explicitly left the actor and role. And `wf_reload_mcp` reloads the server but leaves the public `lifecycle_id` module from before the reload, so helpers that import it keep the old vocabulary until the host restarts.

Brief: goal is that a distribution can rely on public, literal, vocabulary-neutral framework seams; consumers are distribution maintainers and this repository's operators (who see the renamed role); success is literal keys, published reader helpers, a neutral council role with every earlier name still accepted on read, and a fresh `lifecycle_id` after reload. This change lands last in the wave (after `20397`) and owns the wave's CHANGELOG `## [1.29.0]` bullets and the AGENTS.md census edit; `20397` makes its own AGENTS.md backstop edit first.

Code-grounded facts (verified against the working tree at HEAD `b97fa4ba` on 2026-10-07):

- R1: `reconcile_scan._RETIRED_CHANGE_PROMPT_PATTERNS` builds its replacement paths with `vocabulary_profile.prompt_slug(verb + '-change')` over `verb in ("plan", "implement")`; every other key in the module is literal or iterates `DEFAULT_PROMPT_NAMES`.
- R2: `server_impl.EXTENSION_PUBLIC_HELPERS` lists eleven helpers (nine call-time wrappers around private counterparts, so they follow a reload or a test patch); `docs/specs/mcp-tool-surface.md` (Registration) documents it and `tests/test_extension_public_helpers.py` pins it. `lifecycle_gate_support.is_change_id`, `MemberDocRefused` and `_read_member_doc_bytes` exist and are not published.
- R7 census (`rg -P 'wave-council(?![-\w])'` excluding `.git`, `docs/waves/` and the index): 356 lines in 78 files outside `docs/waves/`; 2035 lines under `docs/waves/`; 2381 `"actor": "wave-council"` occurrences in 228 ledgers (recounted at readiness round 1). Scripts: `review_evidence.COUNCIL_ACTOR = "wave-council"` and `_LEGACY_COUNCIL_KEY_PREFIX = COUNCIL_ACTOR + "-"` (so the prefix that keeps a distribution's own `wave-council-<x>` key working is derived from the actor); the expected approval actor is `COUNCIL_ACTOR` for every council key on the read side (`actor_valid` in the review status projection) and the write side (event validation, "approval actor must be"); `lane_l.startswith(COUNCIL_ACTOR)` and `COUNCIL_ACTOR in affected` in lane logic. `lifecycle_gate_support` defaults `moderator_role` to `"wave-council"`; `wave_lint_lib/wave_validators` requires `docs/agents/specialists/wave-council.md`, lists it in `_COORDINATE_STEMS` and `PREPARE_COUNCIL_ROSTER_TOLERANCE`; `dashboard_lib._COORDINATE_STEMS` lists it; `review_policy` registers `ReviewPolicyCarrier("215-wave-council.prompt.md", "docs/agents/specialists/wave-council.md", "renderer", ...)`. Seeds: 44 lines in 15 files, owner `215-wave-council.prompt.md` (`Role: wave-council`). `docs/workflow-config.json` names `"moderator_role": "wave-council"` in both phases. No rendered host surface in this repository carries the name. `review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS` holds no actor string. `review_policy._digest_wave_review` already maps the new key spellings to the old ones before hashing; the moderator role is in the same hashed policy.
- R7 native wrappers and host strings (readiness round 1): `render_agent_surfaces.review_protocol_carriers` adopts `.claude/agents/<role>.md` and `.codex/skills/agent-role-<role>/SKILL.md` as conditional review carriers when present, so a target may hold `.claude/agents/wave-council.md` and `.codex/skills/agent-role-wave-council/SKILL.md` (this repository holds neither). `render_agent_surfaces.CLAUDE_GURU_AGENT` and the four `.claude/agents/factor-*.md` wrappers (agent-authored from seed 050, no renderer string) carry neither `wave-council` nor `Wave Council`. `lifecycle_gates.py` names the actor in one message ("`wave-council` for council signoffs", line 240) besides the "Required Wave Council signoff missing" display string. `docs/architecture/domain-map.md` and `docs/architecture/current-state.md` carry neither name.
- R7 re-Prepare marking (readiness round 1): `review_policy_upgrade.plan_review_policy_upgrade` marks open or readied waves only when the migrated `docs/workflow-config.json` bytes differ, `review_policy_reconcile.plan_reconciliation` plans an edit to a `LIFECYCLE_RECONCILER_CARRIERS` path, or a receipt's evaluator version is stale. The council role doc is a `renderer`-owned carrier, not in `LIFECYCLE_RECONCILER_CARRIERS`, and `review_policy.policy_input_snapshot` hashes the digest copy of `wave_review`, lanes, policies, change bodies and phase gates, never carrier paths or text. The role-doc move therefore marks nothing and rotates no receipt; the 1.29.0 re-Prepare comes from change `200xx`'s reconciled prompt text, already disclosed.
- R7 identity: `derive_review_event_identity` hashes the actor, so recorded events are never rewritten; `review_evidence.canonical_signoff_key`, `legacy_signoff_key_spellings` and the server's `signoff_key_alias` notice are the model for accepting an earlier spelling.
- Display name census ("Wave Council", 2026-10-07): renderer-controlled strings are the `wf-council` skill description in `render_agent_surfaces.SKILL_REGISTRY` and the seed bodies `_initial_review_carrier_text` copies verbatim into a missing carrier (seeds 214, 215, 225, 236 and 237 carry the name; seeds 212, 213, 216, 217, 221 and 239 do not); no `install/lifecycle-prompts` template and no executable-review protocol block carries it. Runtime strings: `server_impl` prepare guidance and verdict messages (the `wf_prepare_wave` and `wf_implement_wave` paths) and the `wf_implement_wave` tool description, `lifecycle_gates` "Required Wave Council signoff missing", the `wave_validators` missing-verdict message, and `lifecycle_gate_support._prepare_council_verdict_template`. The legacy checkpoint line headed `Prepare-phase Wave Council [prepare-council]` is a parsed record format (written by that template, parsed by `wave_validators` and `server_impl` regexes). Seed prose read raw by agents: 18 seeds; `.wavefoundry/framework/README.md` also ships the name. `review_evidence` projections, ledgers and diagnostic codes (`missing_wave_council_signoff`) carry no display name. AGENTS.md's skill line is agent-authored, not rendered.
- R9: `server.perform_mcp_reload` reloads `server_impl`, whose re-execution evicts an explicit module set (`vocabulary_profile`, `record_paths`, `lifecycle_gate_support` and others) but not `lifecycle_id`. The server's own access is fresh (`_lifecycle_module` uses `_load_script`), but `sys.modules["lifecycle_id"]` keeps the old `_vocab` and `KIND_CHOICES`, and `wave_lint_lib/secrets_validators` (module import), `memory_records`, `upgrade_wavefoundry` and `build_pack` (function-local imports) bind to it.

## Requirements

1. **R1 literal keys.** `_RETIRED_CHANGE_PROMPT_PATTERNS` names `prompt_slug("plan-change")` and `prompt_slug("implement-change")` literally (one entry per key and prompt root), producing the same patterns as today. The rule: no call to a `vocabulary_profile` name function (`prompt_slug`, `prompt_doc`, `agent_prompt_doc`, `skill_name`, `shortcut`) in the framework scripts takes a key built at run time, except loops over `DEFAULT_PROMPT_NAMES`; a census test enforces it.
2. **R2 published helpers.** `EXTENSION_PUBLIC_HELPERS` adds `read_member_doc_bytes` (a call-time wrapper over `lifecycle_gate_support._read_member_doc_bytes`, same signature and refusal), `is_change_id` and `MemberDocRefused`. `docs/specs/mcp-tool-surface.md` documents each, and `tests/test_extension_public_helpers.py` pins them.
3. **R7 actor name.** The council moderator actor and role are named `council-chair`. `review_evidence.COUNCIL_ACTOR = "council-chair"` and `LEGACY_COUNCIL_ACTORS = ("wave-council",)`.
4. **R7 old names accepted on read forever.** For every council key, an approval whose actor is `COUNCIL_ACTOR` or any `LEGACY_COUNCIL_ACTORS` entry is a valid council approval in the status projection, the independence and distinctness checks and lane logic (`startswith` and membership tests check every council actor name). Recorded events, ledgers and closed wave records are never rewritten.
5. **R7 old names on write.** `wf_review_event` given a legacy council actor records the approval with `COUNCIL_ACTOR` and returns an `actor_alias` diagnostic, as `signoff_key_alias` does for keys; a replay of an approval first recorded under a legacy actor is recognized by its stored identity (legacy actor spellings are tried as `legacy_signoff_key_spellings` does for keys).
6. **R7 key prefix frozen.** `_LEGACY_COUNCIL_KEY_PREFIX` becomes the literal `"wave-council-"`, no longer derived from the actor, so `wave-council-readiness`, `wave-council-delivery` and a distribution's own `wave-council-<x>` key stay council keys forever. No prefix is derived from the new actor.
7. **R7 profile constant.** `vocabulary_profile.EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS: dict[str, str] = {}` maps a distribution's earlier council key spellings to `council-readiness` or `council-delivery`. `vocabulary_profile.validate()` refuses a key that collides with a current key, a value outside the two keys, or a non-string entry, following `EXTRA_CHANGE_KINDS`. `review_evidence.LEGACY_COUNCIL_SIGNOFF_KEYS` is the built-in mapping merged with it, so `canonical_signoff_key`, `legacy_signoff_key_spellings` and `is_council_signoff_key` honor the extra keys. The built-in pair stays a separate name in `review_evidence`, and `review_policy._DIGEST_COUNCIL_SIGNOFF_SPELLING` maps only the built-in spellings (it stays the reverse of the built-in pair, as `200ex` restates its test): a distribution config that names its own legacy key hashes that literal key, so declaring an extra key never changes an existing receipt digest.
8. **R7 config and digest.** `lifecycle_gate_support`'s `moderator_role` default becomes `council-chair` and either name is accepted. This repository's `docs/workflow-config.json` names `council-chair` in both phases. `review_policy._digest_wave_review` maps `moderator_role` `council-chair` to `wave-council` on its copy before hashing, so the config edit rotates no receipt; the prose `non_waiver_rule` value is not edited. The upgrade's config migration (`review_policy.migrate_wave_review_policy`) does not rewrite a target's `moderator_role`, so the migrated config bytes are unchanged and no wave is marked for re-Prepare by this change.
9. **R7 role doc and seed.** Seed `215-wave-council.prompt.md` is renamed `215-council-chair.prompt.md` (`Role: council-chair`, title "Council Chair"), and the role doc renders at `docs/agents/specialists/council-chair.md`; the `review_policy` carrier names both new paths. The render moves an existing `docs/agents/specialists/wave-council.md` to the new path with a role-doc rename table modeled on `render_agent_surfaces.CHANGE_PROMPT_RENAMES` (byte move through the exclusive publish, mode kept by change `1zyv2`'s rule, both-present reported as a conflict, links reported and never rewritten), then reconciles the new doc's managed regions. The same table moves the native wrappers `review_protocol_carriers` adopts when present: `.claude/agents/wave-council.md` to `.claude/agents/council-chair.md` and `.codex/skills/agent-role-wave-council/SKILL.md` to `.codex/skills/agent-role-council-chair/SKILL.md`, with the same move, conflict and link rules. `wave_validators` accepts the role doc at either path until migrated, and `_COORDINATE_STEMS` (both modules) and `PREPARE_COUNCIL_ROSTER_TOLERANCE` hold both names. Seed 160 gains the upgrade note for the move.
10. **R7 census rule.** Every occurrence of the actor token `wave-council` (not followed by `-` or a word character) in framework scripts, seeds, this repository's live docs (`docs/agents/`, `docs/prompts/`, `docs/contributing/`, `docs/references/`, `docs/specs/`), config, README, `install/install-log.template.md` and tests is either renamed, is a listed legacy acceptance (Requirements 4 to 9), or is in a historical comment or docstring (one that records what an earlier wave did, for example a `Wave 1zyb4` note, and that no tool description or message reads). Named script sites include the `lifecycle_gates.py` actor message ("`wave-council` for council signoffs"). Excluded as history: `docs/waves/`, ledgers, `CHANGELOG.md` entries before `## [1.29.0]`, `docs/architecture/decisions/`, `docs/reports/` and `docs/plans/` (historical). `docs/architecture/domain-map.md` and `docs/architecture/current-state.md` carry neither name: no edit. A census test over the shipped tree enforces the rule; the before and after census is recorded.
11. **R9 reload.** `server_impl`'s reload eviction set includes `lifecycle_id`, so after `wf_reload_mcp` every importer resolves a module built from the current vocabulary profile.
12. **Wave release notes.** This change writes, under the existing `## [1.29.0]` heading, the bullets recorded in the Progress Logs of `1zyv2`, `200eu`, `200ev`, `200ex` and `20397` plus its own (below), and makes the AGENTS.md edit for any AGENTS.md line the Requirement 10 census finds (after `20397`'s own AGENTS.md backstop edit). It amends the existing `## [1.29.0]` sentence "The approving actor and role remain `wave-council`." in the council-key bullet to name `council-chair` and point to this change's bullet. Its own bullet discloses that the council role doc (and any native wrapper) moves; it claims no re-Prepare from the move, which marks no wave (Rationale, re-Prepare marking fact).
13. **Council display name constant.** `vocabulary_profile.COUNCIL_DISPLAY_NAME: str = "Wave Council"` (a single-line assignment, so `apply_profile` can edit it) names the role-based council protocol on every renderer-controlled and runtime surface. `vocabulary_profile.validate()` refuses a non-string, an empty, multi-line or space-padded value, a value over 64 characters, a value containing `` ` ``, `*`, `|`, `[` or `]` (the `_shortcut_problem` rule), and a value whose casefold equals `Archetype Council` or whose `<name> review` phrase casefold equals a `FIXED_PROMPT_SHORTCUTS` entry or a profile shortcut or alias; each message names `COUNCIL_DISPLAY_NAME`. Both new constants (`COUNCIL_DISPLAY_NAME` and `EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS`) are registered as fork-editable profile constants: added to the `vocabulary_profile` entry of `SHIPPED_DEFAULTS` (and so `_EDITABLE`) in `.wavefoundry/framework/scripts/tests/record_layout_support.py`, and to the non-vocabulary exclusion sets in `.wavefoundry/framework/scripts/tests/test_profile_support.py` that list `ARCHIVE_PROFILE`, `EXTRA_CHANGE_KINDS` and `PROMPT_NAME_OVERRIDES`.
14. **Renderer substitution.** The `wf-council` skill description takes the constant, and `_initial_review_carrier_text` replaces each exact `Wave Council` in a seed body it materializes with the constant (fresh carriers only, before the existing frontmatter and protocol-region steps). An existing carrier is never rewritten outside its managed region, and no managed region carries the name.
15. **Runtime strings.** The `server_impl` prepare guidance and verdict messages, the `wf_implement_wave` tool description, the `lifecycle_gates` missing-signoff message, the `wave_validators` missing-verdict message and the free-text `observed` hint of the typed verdict template take the constant. Fixed and not substituted: the legacy checkpoint line format `Prepare-phase Wave Council [prepare-council]` (its template and both parse regexes), diagnostic codes, comments and docstrings that are not tool descriptions, and every ledger, projection and closed record.
16. **Seed prose and shipped docs out of reach.** Seed prose read raw by agents and `.wavefoundry/framework/README.md` keep `Wave Council`; a distribution edits its own copies at merge time, as for any seed prose. The `vocabulary_profile` module docstring and the vocabulary profile paragraph of `docs/architecture/layering-rules.md` state which surfaces follow the constant and that seed prose and already-rendered docs do not. No prose in this repository is renamed.

## Scope

**Problem statement:** a distribution must patch framework internals for literal keys, the member-document reader and a fresh `lifecycle_id`, and every distribution records and displays a council role named after waves.

**In scope:**

- Requirements 1 to 16 and their tests; seeds edited under `seed_edit_allowed`.

**Out of scope:**

- Renaming "Wave Council" in this repository's own prose, seeds, AGENTS.md or README (the default name stays "Wave Council"), and rewriting already-rendered carriers in any target.
- Profile substitution inside seed prose read raw by agents (Requirement 16).
- Retiring the earlier actor or keys as input (never, by operator decision, for reads; input aliases stay for this release).
- Extra legacy council actors from a profile (only keys were requested).
- Unknown tool names in generated hooks (held by the operator; deferred).

## Acceptance Criteria

- [x] AC-1: `_RETIRED_CHANGE_PROMPT_PATTERNS` is equal before and after the edit under the default and `prompt-names` profiles, and the census test fails on a scratch module that calls `prompt_slug` with a concatenated key.
- [x] AC-2: An extension module in a declared-profile fixture calls `server_impl.read_member_doc_bytes`, `is_change_id` and catches `MemberDocRefused` for a linked member doc; `tests/test_extension_public_helpers.py` lists the three names.
- [x] AC-3: A fixture ledger holding approvals recorded with actor `wave-council` under both the old and the new keys projects the same `status_rows` after the change as before (byte comparison of each row's `signoff_key`, `state`, `why` and `next_action`; `expected_actor` and `actor_role` change to `council-chair`), and an approval with actor `council-chair` is valid; a mutant that drops the legacy actor from the read check fails this AC.
- [x] AC-4: `wf_review_event` with actor `wave-council` records `council-chair` and returns `actor_alias`; a replay of an approval first recorded with `wave-council` is recognized as a replay, not a new event.
- [x] AC-5: `is_council_signoff_key` is true for `wave-council-readiness`, `wave-council-delivery` and a custom `wave-council-x`, and false for `council-chair-x`; a profile with `EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS` maps its spelling to the current key, and invalid entries are refused at import with a named problem.
- [x] AC-6: `policy_input_snapshot` for this repository's config before and after the `moderator_role` edit is identical, and no open or readied wave's current receipt is superseded by it.
- [x] AC-7: A render on a fixture holding only `docs/agents/specialists/wave-council.md` moves it to `council-chair.md` (bytes before reconciliation identical, mode kept) and a second render writes nothing; with both present it reports a conflict and changes neither; the same three cases hold for `.claude/agents/wave-council.md` and for `.codex/skills/agent-role-wave-council/SKILL.md`; docs-lint passes on both the legacy-only and the migrated fixture.
- [x] AC-8: The Requirement 10 census test passes on the shipped tree and fails when a scratch seed reintroduces the actor token; the before and after census is recorded in the Progress Log.
- [x] AC-9: After `wf_reload_mcp` with a changed `vocabulary_profile` in a scratch install, `sys.modules["lifecycle_id"].KIND_CHOICES` reflects the change and `secrets_validators` binds the fresh module. Fails today.
- [x] AC-10: The `## [1.29.0]` section holds the bullets recorded by `1zyv2`, `200eu`, `200ev`, `200ex`, `20397` and this change (each matched against its Progress Log text), with no reproduction detail; the sentence "The approving actor and role remain `wave-council`." is amended to name `council-chair`; and AGENTS.md matches the census outcome.
- [x] AC-11: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-12: Under the default profile the substitution is the identity: every rendered skill file and every carrier materialized on a fresh fixture tree is byte-identical to the same render with the substitution step removed, and `fixtures/tool-surface-golden.json` and the Requirement 15 messages are byte-identical to today's apart from the Requirement 3 actor rename.
- [x] AC-13: Under the `prompt-names` profile fixture with `COUNCIL_DISPLAY_NAME = "Review Board"`, the `wf-council` description, fresh carriers from seeds 214, 215, 225, 236 and 237, the Requirement 15 messages and the `wf_implement_wave` description name "Review Board" with no `Wave Council` left, an existing carrier keeps its bytes outside the managed region, and a legacy checkpoint line still parses; a mutant that restores the literal in the renderer fails this AC.
- [x] AC-14: `validate()` refuses each Requirement 13 invalid value at import with a message naming `COUNCIL_DISPLAY_NAME`, and accepts "Review Board".
- [x] AC-15: A census test finds no `Wave Council` string literal in framework scripts outside `vocabulary_profile.py` except the Requirement 15 fixed sites, and fails on a scratch module that adds one.

## Tasks

- [x] Open `framework_edit_allowed`.
- [x] `reconcile_scan.py` literal keys and the census test (Requirement 1, AC-1).
- [x] `wf_server/server_impl.py`: three published helpers; `lifecycle_id` in the reload eviction set (Requirements 2 and 11, AC-2, AC-9).
- [x] `review_evidence.py`: actor constants, read-side acceptance, write-side alias and replay, frozen prefix, merged legacy keys (Requirements 3 to 7, AC-3 to AC-5).
- [x] `vocabulary_profile.py`: `EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS` and its validation (Requirement 7, AC-5).
- [x] `lifecycle_gate_support.py`, `review_policy.py`, `wave_lint_lib/wave_validators.py`, `dashboard_lib.py`, `lifecycle_gates.py`: defaults, digest mapping, role doc paths, stems and tolerance (Requirements 8 and 9, AC-6).
- [x] `render_agent_surfaces.py`: role-doc rename table and move, including the `.claude/agents/wave-council.md` and `.codex/skills/agent-role-wave-council/SKILL.md` native wrappers (Requirement 9, AC-7).
- [x] `tests/record_layout_support.py` and `tests/test_profile_support.py`: register `COUNCIL_DISPLAY_NAME` and `EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS` in `SHIPPED_DEFAULTS` (so `_EDITABLE`) and in the non-vocabulary exclusion sets (Requirements 7 and 13).
- [x] Open `seed_edit_allowed`.
- [x] Rename seed 215 and update every seed occurrence under the census rule, including the seed 160 upgrade note (Requirements 9 and 10).
- [x] Close `seed_edit_allowed`.
- [x] Tests across the census (goldens `fixtures/lifecycle-gate-golden.json` and `fixtures/lifecycle-gate-pre-configured-golden.json` regenerated, `test_council_signoff_keys.py`, `test_server_tools_lifecycle.py`, `test_review_evidence.py`, `test_docs_lint.py` and the rest), each new test confirmed failing against the unfixed code in a scratch copy; mutation probes recorded.
- [x] `vocabulary_profile.py`: `COUNCIL_DISPLAY_NAME`, its validation and the module docstring note (Requirements 13 and 16, AC-14).
- [x] `render_agent_surfaces.py`: `wf-council` description and fresh-carrier substitution in `_initial_review_carrier_text` (Requirement 14, AC-12, AC-13).
- [x] `wf_server/server_impl.py`, `lifecycle_gates.py`, `wave_lint_lib/wave_validators.py`, `lifecycle_gate_support.py`: Requirement 15 strings from the constant, legacy checkpoint format left literal (AC-12, AC-13).
- [x] Tests: `COUNCIL_DISPLAY_NAME` in the `fixtures/profiles/prompt-names.json` profile; default identity, custom render, validation and the literal census (AC-12 to AC-15), each confirmed failing against the unfixed code in a scratch copy; renderer-literal mutant recorded.
- [x] Close `framework_edit_allowed`.
- [x] Add the display-name sentence to the vocabulary profile paragraph of `docs/architecture/layering-rules.md` (Requirement 16).
- [x] Author the actor-rename decision record under `docs/architecture/decisions/` (Affected Architecture Docs).
- [x] `docs/specs/mcp-tool-surface.md`: entries for `read_member_doc_bytes`, `is_change_id`, `MemberDocRefused` and the `actor_alias` diagnostic (Requirements 2 and 5).
- [x] Edit `docs/workflow-config.json` (AC-6), render this repository's surfaces to move the role doc, update live docs under the census rule, record the census (AC-7, AC-8).
- [x] Final CHANGELOG pass under `## [1.29.0]` (the five sibling bullets including `20397`'s, this change's bullets, and the amended "approving actor and role" sentence) and the AGENTS.md edit after `20397`'s (Requirement 12, AC-10).
- [x] Run `wf_validate_docs`, then the full suite last (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 seams | implementer | - | Requirements 1, 2, 11 |
| ws-2 council identity | software-engineer | - | Requirements 3 to 8 |
| ws-3 role doc, seeds, census | implementer | ws-2 | Requirements 9 and 10 |
| ws-5 council display name | implementer | ws-3 | Requirements 13 to 16 |
| ws-4 release notes | implementer | ws-1, ws-2, ws-3, ws-5 | Requirement 12, after every other change in the wave |

## Serialization Points

Lands last in the wave, after `20397`. It shares the review evidence module with `200ev`, the agent-surface renderer with `1zyv2` and `200eu`, the server implementation and the lifecycle gate support module with `1zyv2`, the tool-surface spec and seeds with `200ev` and `20397`, seed 050, the agent team workflow doc and the root agent guide with `20397` (which edits them first), and test files across the suite with `200ex`; it writes the wave's release notes. The root-level changelog, agent guide and readme are edited as prose.

- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/test_profile_support.py`
- `.wavefoundry/framework/scripts/tests/test_council_signoff_keys.py`
- `.wavefoundry/framework/scripts/tests/fixtures/profiles/prompt-names.json`
- `.wavefoundry/framework/seeds/`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `docs/architecture/layering-rules.md`
- `docs/architecture/decisions/`
- `docs/workflow-config.json`
- `docs/agents/specialists/`
- `docs/prompts/`
- `docs/contributing/`
- `docs/contributing/agent-team-workflow.md`
- `docs/references/`
- `docs/specs/mcp-tool-surface.md`
- `CHANGELOG.md`
- `AGENTS.md`
- `README.md`

## Platform Behavior

Name, mapping, validation and digest changes are string and dictionary operations with identical behavior on Windows, macOS, Linux and WSL2. The role-doc move uses the existing exclusive publish and change `1zyv2`'s contained primitive, so its platform behavior (descriptor-anchored on POSIX, checked path with a documented window on Windows) applies; repository-relative paths stay POSIX in every message and manifest. The reload eviction is a `sys.modules` edit with no file operation. The display-name substitution is an exact string replacement on decoded text before the existing carrier write path, so newline handling and the write primitive are unchanged on every platform; validation compares with `casefold`, which is locale-independent.

## Affected Architecture Docs

- `docs/architecture/domain-map.md` and `docs/architecture/current-state.md`: no edit (neither carries `wave-council` nor `Wave Council`, checked at readiness round 1).
- `docs/architecture/decisions/`: a short decision record for the actor rename (recording that `council-moderator`, retired by ADR `1p5be`, was not revived); the existing ADR `1p5be` is history and is not edited.
- `docs/specs/mcp-tool-surface.md`: the three published helpers and the `actor_alias` diagnostic.
- `docs/architecture/layering-rules.md`: the vocabulary profile paragraph names `COUNCIL_DISPLAY_NAME` and the surfaces it reaches (Requirement 16).

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | important | Distribution census seam. |
| AC-2 | required | Distribution tools need the reader. |
| AC-3 | required | Recorded approvals must keep their meaning forever. |
| AC-4 | required | Callers using the old actor keep working. |
| AC-5 | required | Old and distribution keys stay council keys. |
| AC-6 | required | A naming edit must not lapse approvals. |
| AC-7 | required | Existing targets migrate without loss. |
| AC-8 | required | The rename is complete, not partial. |
| AC-9 | important | Reload freshness. |
| AC-10 | required | The wave's release notes. |
| AC-11 | required | Change-local health. |
| AC-12 | required | The default profile changes no output. |
| AC-13 | required | A distribution's name reaches every renderer and runtime surface. |
| AC-14 | important | A bad name fails at import, not in rendered output. |
| AC-15 | important | Keeps new literals from reappearing. |

## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-08 | Final quiet-tree canonical host run passed: 11,885 tests, 173 files, 385.389 seconds, 20 intentional skips; fresh green receipt written. Full docs lint passes with the standing 20397 AC-8 wording advisory. All ACs/tasks now complete. | `.wavefoundry/framework/test-cache.json`, inputs hash `5723cd56d77db3438ef5eb5d9fbaec5e243e7d43416ab66caec123f8d0e33038`; `/private/tmp/200ey-final-host-canonical.log`. Independent QA/code each passed 14 checks and caught five known-bad controls for cycle 2. |
| 2026-10-08 | Delivery cycle 2 readback before test edits: the canonical run completed red (11,885 tests, 173 files, 20 intentional skips): default-layout literal in the actor fixture, a retained callable/new-module spy mismatch after reload, and three historical digest failures from the approved actor rename. Independent QA reproduced all three before mutation. Typed F-TEST-LAYOUT, F-TEST-MODULE and F-TEST-ACTOR repair starts precede the bounded edits. | Repair only the three test files: derive the configured wave path, spy on the retained callable's owner, and preserve historical hashes with assertions plus normalization of only the two approved actor phrases. No product behavior change, skip, broad allowlist or wholesale digest update. |
| 2026-10-07 | Planned from the Waveforge maintainers' public report (R1, R2, R7, R9) and the operator's decisions; facts re-verified against the working tree. Lands last in the wave, after wave `200xy` commits. | Rationale facts. |
| 2026-10-07 | Own CHANGELOG bullets (under `## [1.29.0]`): Changed: "The council moderator role is now `council-chair` (role doc `docs/agents/specialists/council-chair.md`, seed `215-council-chair.prompt.md`). Approvals recorded by `wave-council`, and the keys `wave-council-readiness` and `wave-council-delivery`, stay valid forever; `wave_review` input naming `wave-council` is accepted and recorded as `council-chair` with a notice. Upgrading moves an existing role doc, and because a review carrier moves, open or readied waves in a target may be marked for one re-Prepare, together with the earlier key change in this release. A distribution can declare its own earlier council key spellings in `EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS`. A distribution can also name the council protocol with `COUNCIL_DISPLAY_NAME` (default 'Wave Council'), which the `wf-council` skill, newly created role and prompt docs, and server and lint messages follow; seed prose and docs already rendered are unchanged." Added: "Extension tools can call `read_member_doc_bytes`, `is_change_id` and catch `MemberDocRefused` through the published helpers." Fixed: "`wf_reload_mcp` now also refreshes `lifecycle_id`, so helpers that import it see the current vocabulary." | AC-10 text. |
| 2026-10-07 | Readiness round 1 findings applied (F6 native wrappers in the rename table and AC-7; F7 digest maps only the built-in spellings; F8 re-Prepare disclosure dropped after re-verification; F9 AC-12 actor-rename carve-out; F10 AC-3 scoped to `status_rows`; F11 profile-constant registration, ADR and spec tasks and Serialization Points; F12 amend the 1.29.0 "approving actor and role" sentence; F13 historical comments class, `docs/plans/` (historical), `lifecycle_gates.py` actor message, domain-map and current-state no edit; F15 `20397` in Requirement 12 and AC-10; F17 guru and factor wrapper strings checked; census recounted). Revised own Changed bullet, replacing the first one above (Added and Fixed unchanged): "The council moderator role is now `council-chair` (role doc `docs/agents/specialists/council-chair.md`, seed `215-council-chair.prompt.md`). Approvals recorded by `wave-council`, and the keys `wave-council-readiness` and `wave-council-delivery`, stay valid forever; `wave_review` input naming `wave-council` is accepted and recorded as `council-chair` with a notice. Upgrading moves an existing role doc, and any native role wrapper, to the new name; the move changes no review-policy receipt. A distribution can declare its own earlier council key spellings in `EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS`. A distribution can also name the council protocol with `COUNCIL_DISPLAY_NAME` (default 'Wave Council'), which the `wf-council` skill, newly created role and prompt docs, and server and lint messages follow; seed prose and docs already rendered are unchanged." | `review_policy_upgrade.plan_review_policy_upgrade`, `review_policy.policy_input_snapshot`, `LIFECYCLE_RECONCILER_CARRIERS`; census `rg` at HEAD `b97fa4ba`. |
| 2026-10-07 | Readiness round 2 (final) fixes applied by the coordinator. | Round 2 review. |

| 2026-10-08 | Readback: take over the interrupted implementation. Complete and verify literal reconcile keys, public member helpers, council-chair alias/read/replay compatibility and profile display name; preserve existing receipts and historical ledgers. Finish AC-1–15 with focused regression/mutation evidence and wave-wide release notes. Before: older council actor works only as wave-council; after: new writes use council-chair while old approvals and replays remain valid. | Existing partial script/seed/test/docs edits retained; admitted scope unchanged; canonical wf_implement_wave dry_run confirms wave already implementing. No close, commit or push authorized. |


| 2026-10-08 | Source takeover audit corrected the extension validator: historical string keys may contain spaces or capitals; a redundant built-in mapping is accepted, but a conflicting remap, current-key collision, invalid destination or non-string entry is refused. | `vocabulary_profile.legacy_council_key_errors`; spaced-key public write and invalid-profile tests. |
| 2026-10-08 | Superseding release wording: `wf_review_event` approvals naming `wave-council` are recorded as `council-chair` with an `actor_alias` notice; `wave_review` accepts either moderator role and the upgrade leaves its configured spelling unchanged. Other clauses in the revised Changed bullet remain unchanged. | Corrected CHANGELOG and seed 160; Requirement 8 keeps migration receipt-neutral. |
| 2026-10-08 | Actor census after takeover: 47 permitted tokens in 20 framework carriers, and 3 in live repository surfaces (MCP spec: 1; current CHANGELOG: 2). No unlisted framework tokens; live sites explicitly describe legacy acceptance. Root AGENTS/README, install template and live role/prompt/config surfaces have zero actor tokens. Earlier readiness census reported 356 matching lines in 78 non-wave files and 2,035 wave lines (2,381 old-actor occurrences in 228 ledgers); historical records remain excluded and untouched. | `ActorTokenCensusTests`, explicit `live_actor_token_census(Path.cwd())`; token counts are not comparable to earlier matching-line counts. |
| 2026-10-08 | 80 focused tests passed with no skips; actual HEAD scratch modules preserve default reconcile patterns and old/new-key readiness/delivery status-row bytes. Sixteen deliberately broken scratch modules were rejected by targeted tests. | `test_distribution_seams`, `test_council_signoff_keys`, `test_extension_public_helpers`, `PublicHelperServingTests`; `/tmp/200ew-final-focused.log`, `/tmp/200ew-baseline.log`, mutation table below. Native Windows unexecuted; custom-name public runtime checks and final full suite remain in progress. |

| 2026-10-08 | Custom-name public runtime verification completed: default and Review Board names in prepare guidance, missing/malformed verdicts for prepare/implement, typed missing-signoff; fixed legacy checkpoint still parses. Final focused total: 82 tests, no skips; seven additional per-site literal-restoration mutants rejected (23 takeover mutants total). | `CouncilDisplayNameRuntimeTests`, `/tmp/200ew-final-focused.log`, `/tmp/200ew-runtime-mutation-results.json`; tree frozen before scratch probes. |

### Takeover mutation evidence

Every mutant below was confined to a scratch copy; the live source was never mutated. Each targeted test passed on current source and failed for the named regression. Whole-file escalation was unnecessary because none survived.

| Mutant | Targeted guard | Expected / observed |
| --- | --- | --- |
| M-read-legacy | Legacy actor status-row acceptance | fail / fail |
| M-frozen-prefix | Frozen earlier council-key prefix | fail / fail |
| M-write-alias | Public old-actor canonical write | fail / fail |
| M-replay-actor | Historical approval identity replay | fail / fail |
| M-digest-role | Moderator-role receipt neutrality | fail / fail |
| M-role-render | Full-render role/native-wrapper move | fail / fail |
| M-reload-id | Fresh lifecycle-id and secrets binding | fail / fail |
| M-display-render | Profiled fresh carrier display name | fail / fail |
| M-display-validate | Display validator integration | fail / fail |
| M-extra-validate | Extension-key validator integration | fail / fail |
| M-reader-refusal | Public member reader link refusal | fail / fail |
| M-literal-key | Concatenated reconcile-key census | fail / fail |
| M-actor-census | Reintroduced seed actor census | fail / fail |
| M-display-census | Reintroduced runtime literal census | fail / fail |
| M-extra-merge | Profile legacy-key canonicalization | fail / fail |
| M-builtin-remap | Conflicting built-in key remap | fail / fail |

Detailed targeted test names and observed assertion failures: `/tmp/200ew-mutation-results.json`. The AST key census catches the required concatenation regression; it does not prove arbitrary variable provenance.

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-07 | Operator decision: R7 is in scope in full: rename the actor and its role doc and seed, accept the old actor and old keys on read forever, add a profile constant for extra legacy keys, migrate rendered role docs with the existing retire and rename pattern, never rewrite ledgers. | Operator direction. | - |
| 2026-10-07 | Selected the name `council-chair`. | Hyphenated, so it passes `_PREPARE_COUNCIL_ROLE_TOKEN_RE` (which filters single-word roles); carries no delivery-unit noun; is not a prefix of any council key, so no key can be mistaken for a role-derived key; collides with no fixed prompt slug or skill name (`council-review`, `archetype-council`, `wf-council`); and is not a retired name (no hit for it in the repository). | `council` (the operator's example): filtered by the roster token rule and a prefix of both current keys. `council-moderator`: matches `moderator_role`, but ADR `1p5be` retired it as the earlier name of this same role, so reviving it makes historical records ambiguous. `review-council`: inverts `council-review` (seed 237). |
| 2026-10-07 | Freeze the legacy key prefix to `wave-council-` and derive no prefix from the new actor. | The prefix exists only to keep earlier and distribution keys valid; deriving it from the new name would widen the council key set to unrelated keys. | Derive from the new actor too: `council-chair-*` keys gain meaning nobody asked for. |
| 2026-10-07 | Map the new `moderator_role` to the old spelling in the digest copy. | Same mechanism `1zxnx` used for keys; the edit stays receipt-neutral. | Accept receipt rotation: lapses readiness in every open wave. |
| 2026-10-07 | Write-side input alias for the old actor rather than a refusal. | Callers and prompts written before the release keep working, as for the keys. | Refuse the old actor on write: breaks every older prompt surface at once. |
| 2026-10-07 | Coordinator decision: this change writes the wave's CHANGELOG bullets and any AGENTS.md edit; the other five record their bullets in their Progress Logs. | One owner for root files; it lands last. | Each change edits CHANGELOG. |
| 2026-10-07 | Operator decision: unknown tool names in generated hooks are deferred (held by the operator); Q11 is informational. | Operator direction. | - |
| 2026-10-07 | Operator decisions: the actor name `council-chair` is accepted; one combined re-Prepare for this release's key and role changes is acceptable. | Operator direction. | - |
| 2026-10-07 | Operator decision: the vocabulary profile supplies the council's display name; default 'Wave Council'. Mechanism: one single-line constant `COUNCIL_DISPLAY_NAME` validated at import like `PROMPT_NAME_OVERRIDES`, read by the renderer's own strings, fresh-carrier materialization and runtime messages; the parsed legacy checkpoint format, diagnostic codes, ledgers, projections and closed records stay literal; seed prose stays raw. | Same model as `1zxnw`: a fork edits one constant and every surface the framework controls follows; the default keeps this repository's output byte-identical. Ledgers and projections carry no display name, so nothing historical needs rewriting. | Keep the name fixed (the earlier decision): a distribution must patch the renderer and server strings. Derive it from `CONTAINER_NAME` (`f"{CONTAINER_NAME} Council"`): couples two names a distribution may want separately and gives no way to keep "Wave Council" with another tier name. Template substitution inside every seed: seeds are read raw by agents, and rewriting their prose breaks the seed-is-source rule. Profile the legacy checkpoint format too: breaks parsing of existing legacy prose waves. |
| 2026-10-07 | Coordinator decision (readiness round 1): keep `200ew` as one change. | Its parts share the same files (review evidence, renderer, server, seeds) and land together last; a split adds coordination and a seventh change for no isolation gain. | Split the council rename from the seams and display name: considered and rejected, adds coordination and a seventh change. |
| 2026-10-07 | Coordinator decision (readiness round 1): re-verify the re-Prepare claim against `review_policy_upgrade.plan_review_policy_upgrade` and `policy_input_snapshot`; the move marks nothing, so Requirement 12, the CHANGELOG proposal and Risks drop the disclosure. | Marking follows migrated config bytes, a planned `LIFECYCLE_RECONCILER_CARRIERS` edit or a stale evaluator; the role doc is a `renderer` carrier and the snapshot hashes no carrier. The 1.29.0 re-Prepare comes from `200xx` and is already disclosed. | Keep the disclosure: tells targets to expect a re-Prepare this change does not cause. |
| 2026-10-07 | Coordinator decision (readiness round 1): `20397` lands before this change; both edit seed 050, `docs/contributing/agent-team-workflow.md` and `AGENTS.md`, and this change's AGENTS.md census edit and CHANGELOG pass follow `20397`'s edits. | `20397` is small guidance text; landing it first lets this change's broad census and release pass include it. | `20397` after this change: the final CHANGELOG and AGENTS.md pass would no longer be last. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A reader that checks the actor is missed and historical approvals read as invalid. | AC-3 byte-compares projections over legacy ledgers; the census test (AC-8) lists every read site. |
| A later edit makes the role-doc move or the `moderator_role` rename mark target waves for re-Prepare (a config migration that rewrites `moderator_role`, or the role doc joining `LIFECYCLE_RECONCILER_CARRIERS`). | Requirement 8 keeps the migration from rewriting `moderator_role`; AC-6 checks the digest; the move is renderer-owned and outside the reconciler, so today it marks nothing and the CHANGELOG claims no re-Prepare from it. |
| The fresh-carrier replacement rewrites an occurrence that is not the protocol name, or leaves a mixed name because seed prose stays raw. | The census shows every seed occurrence is the protocol name and no carrier seed holds the parsed checkpoint format; AC-13 checks no literal survives in fresh carriers; Requirement 16 documents that seed prose and existing docs keep the default. |
| Broad test churn conflicts with sibling changes. | Lands last; rebases on the other five. |
| A distribution configured its own actor name. | Out of scope; its approvals keep the expected-actor rule it has today only if it used `wave-council`; recorded as a follow-up if reported. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
