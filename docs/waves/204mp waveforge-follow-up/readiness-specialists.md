# Waveforge follow-up specialist readiness review

Owner: Engineering
Status: active
Last verified: 2026-10-08
Wave: `204mp waveforge-follow-up`

Phase: readiness. Receipt: `review-policy-5de6f84316a3a4bf9e13`.
Context: `204mp-public-specialists-20261008-independent`.

This explicitly requested report preserves one independent review across code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer and docs-contract-reviewer dimensions. These are five judgments from **one context**, not five independent corroborations. The reviewer authored none of the plans or implementation and writes no typed approval. The coordinator may record these judgments; a separate independent chair must synthesize readiness.

## Scope and assessment

Reviewed the current admitted documents 204ml, 204mm and 204mn, wave record and current-scope briefing before reading the primer. Change 204mo/C6 moved intact to 206is; the older briefing and primer's four-change wording is historical and cannot make C6 a blocker for this receipt. No wave activation, source edits, full suite, reload of the shared live server, closure or publication ran.

Pre-primer read: the three plans need portable independent test oracles, collision-safe council identity compatibility and a resumable exact-link migration, with the main risks at inventory omissions, configured role collisions and partially completed moves.

Primer effect: extended — its distinction between migration eligibility, ownership and completion sharpened the retry and configured-role checks; its strongest journal-location challenge is outside the current admission boundary.

| Required lane | Readiness verdict | Basis |
| --- | --- | --- |
| code-reviewer | approved | Current migration, census and identity mechanisms were read live; the selected defects have implementable, scoped requirements and falsifiable ACs. No findings in my lane: no demonstrated contradiction or unresolved build-changing choice in C1–C5. |
| qa-reviewer | approved | Independent historical payload checks, current-defect reproductions, canonical producer identity controls and CLI gate controls ran without skips. No findings in my lane: future delivery tests remain required rather than being represented as completed. |
| architecture-reviewer | approved | Profile declaration owns compatibility vocabulary; runtime configuration owns project roles; review evidence remains the authority facade; contained migration owns exact destination changes. No findings in my lane: the plan permits runtime collision enforcement without making the import-cheap profile read repository config. |
| security-reviewer | approved | Collision preservation and actor/phase/repair guards were exercised at their named boundaries; contained reads/writes remain required. No findings in my lane: no demonstrated less-trusted actor/authority delta or new bypass in the plan; same-user correctness risks are not asserted as privilege escalation. |
| docs-contract-reviewer | approved | Current requirements preserve strict docs gating, managed regions, historical roots, canonical actor writes and immutable ledgers. No findings in my lane: the new seam and migration contracts name their specification/architecture updates and do not promise delivered behavior. |

These judgments apply to readiness of this receipt only. No required product AC is marked complete by this report. Concrete blocking plan findings: none. Finding synthesis: empty candidate set; no severity or actionability facts are invented for implementation notes.

## Primer responses

**Strongest challenge and question 1:** the unresolved pre-relocation journal predicate was a real issue for the original C6 scope. It is now owned by 206is. There is no journal trigger, callback or source-root change in this three-change wave, so answering that question is unnecessary for C1–C5 readiness. This is a scope boundary, not a waiver of C6.

**Question 2:** 204mm requirement 1 expressly rejects active non-council reviewer/operator collisions; requirement 3 preserves authorization and repair identity. Live `review_policy.project_lanes_for_phase` reads both base required lanes and phase-specific required lanes, and `review_evidence.required_signoff_keys` also reads the wave roster. Therefore import-time profile shape validation alone cannot satisfy the requirement: enforcement at the runtime review/policy boundary must include actual configured and wave-declared roles, plus operator identity. The declared server/evidence scope permits that implementation without reversing module dependencies. The selected existing producer tests show canonical writes and replay, wrong actor/phase rejection, and conflict detection; a separate compact-producer control shows legacy/current council spellings are one repair actor. Delivery must repeat these with declared aliases, dynamic role collisions and real reload. `review_policy._DIGEST_COUNCIL_MODERATOR_SPELLING` remains a built-in historical mapping, independent of the expanded recognition tuple; the C3 independent golden controls preserve that distinction.

**Question 3:** a retry may reconcile a mapped old path only when old is absent and the exact mapped new destination is a contained regular file; both-present remains a collision. This is current-state evidence under the narrow rename map, not proof of a globally atomic prior migration. The present function demonstrably loses its link report on that retry, so new discovery must not depend on the invocation's `written` list. Requirements already demand destination-span edits, inline and reference forms, escaped/encoded destinations, optional titles, code masking with original offsets, custom modes and explicit historical exclusions. Neither `is_history_path` alone nor the reporter's simple regex implements that contract. Unsupported syntax stays unchanged with a diagnostic and may still fail the strict docs gate, as intended.

For C1, the tracked upstream ownership inventory must include eligible zero-hit files and owned fixtures, while downstream test execution consumes the frozen inventory without Git. Its explicit maintenance command should offer a check/diff workflow comparing the sorted eligible tracked set with the committed inventory, with a known zero-hit omission negative control. That is an implementation note for the already-required inventory/update contract, not a request to replace the accepted design. The inventory itself must be covered without embedding legacy actor literals in a self-referential occurrence oracle. Missing owned files and stale allowances remain errors.

**Best alternative:** for current C1–C5, using a broad Markdown parser/serializer or scanning the downstream checkout dynamically is weaker: the former can rewrite unrelated bytes and the latter conflates file presence with ownership. A narrow destination-span recognizer and explicit upstream inventory preserve the named properties with less scope. The primer's smallest authorized journal predicate remains the appropriate alternative decision for 206is, not work to add here.

## Executed evidence

All commands ran in fresh `python3 -B` processes with `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests`. TemporaryDirectory fixtures confined writes to scratch roots; no network, credentials or external effects. Six prioritized probe groups stay within the full-depth 3–8 budget. The full primer has five stances and three questions; generated receipt metadata still says standard because the source hardcodes it. This report neither changes that metadata nor misstates the actual review depth.

### E1 — Existing review lifecycle compatibility

Public path: `wf_server.server_impl.wf_review_event_response` through `test_council_signoff_keys.LifecycleCompatibilityTests` and canonical lifecycle fixture producers.

Command: `python3 -B -m unittest -v test_council_signoff_keys.LifecycleCompatibilityTests.test_old_actor_input_writes_the_new_actor test_council_signoff_keys.LifecycleCompatibilityTests.test_old_key_input_writes_the_new_key test_council_signoff_keys.LifecycleCompatibilityTests.test_a_legacy_key_approval_replays_after_the_rename test_council_signoff_keys.LifecycleCompatibilityTests.test_a_legacy_key_approval_with_different_evidence_is_a_conflict`.

Expected and observed: 4 tests passed, 0 skips, 0.918 seconds. Legacy actor writes became canonical actor records with alias notices; a signoff name used as actor was rejected with the expected actor diagnostic; wrong approval phase was rejected with the expected readiness-phase diagnostic. Historical replay remained replay, while changed evidence was rejected as conflict. These controls demonstrate the existing seams that C4 must extend. Fixture setup stubs garden/docs validation and post-write lint; this does not prove the whole MCP middleware chain or current docs lint. No extra declared actor was implemented or tested.

### E2 — Repair identity and runtime roles

Faithful boundary: `review_evidence.build_compact_review_event`, the canonical event producer, using `RepairReverificationIndependenceTests._chain_through_repair_start` to create valid state.

Reproduction: build a repair chain with `repair_actor=LEGACY_COUNCIL_ACTORS[0]`, context `legacy-repair`; submit `_clearing_reverification(actor=COUNCIL_ACTOR, context_id='fresh-canonical')`; require no appended rows and `reverification_actor_not_distinct`. Submit the same chain with actor `qa-reviewer` and context `fresh-independent`; require nonempty rows and no errors. Both assertions passed. This directly rejects the known-bad two-spellings/two-actors interpretation, beside a legitimate distinct-actor control; it does not claim a registered MCP repair invocation.

Adjacent current-config check: `project_lanes_for_phase` with base `['custom-auditor']`, prepare extra `['project-reviewer']` and close extra `['release-reviewer']` returned exactly the respective two-item lists. It establishes that the collision domain cannot be inferred from a fixed shipped-name list. New collision/reload behavior remains unimplemented.

### E3 — Role migration baseline, retry and collision

Faithful boundary: production `render_agent_surfaces.migrate_council_role_renames`, called directly because no new link-repair implementation exists yet.

Reproduction: in a temporary root create the first `COUNCIL_ROLE_RENAMES` source with bytes `b'# Custom role\r\n'` and mode 0640. Create adjacent `specialist.md` with `b'# Mine\r\n[chair](wave-council.md#role)\r\n'`. Invoke the migration twice. Expected and observed: first invocation moved the role, preserved exact role bytes and 0640 mode, left the custom document bytes unchanged and produced a link report. Second invocation returned empty `written` and `link_report` while the stale link remained. This is the pre-fix retry defect, not a passing new link-repair AC.

Then recreate the old role with `b'collision original'` while the destination exists. The migration raised the collision error containing `All files were preserved`; exact snapshots of old role, new role and custom document remained equal. This tests the shared write boundary's real refusal and legitimate first-move control. No full upgrade-driver repair, injected unlink failure, Windows mode/ACL behavior, parser syntax coverage or dry-run repair is claimed.

### E4 — Census ownership baseline

Faithful boundary: current `test_distribution_seams.actor_token_census`.

Reproduction: temporary framework with only `scripts/tests/downstream_added.py` containing `LEGACY_ACTOR`; require exact census `{'scripts/tests/downstream_added.py': 1}`. Add `scripts/owned_zero.py` with `pass\n`; it is absent from occurrence output. Replace its content with `LEGACY_ACTOR`; require its count becomes 1. All assertions passed. The downstream result refutes the current ownership assumption; the zero-hit-to-hit adjacent control explains why an allowlist of current occurrences would be insufficient. This is a bounded two-file test, not a closed census of all upstream files. Future inventory omission/missing-file/update-command tests remain required.

### E5 — Independent historical digest reference

Production comparison boundary: `review_policy.policy_input_snapshot`; independent expected value uses only literal payload fields, legacy table/actor spellings, `json` and `hashlib`.

Reproduction: construct seven fields: schema_version 1, evaluator_version 7, wave_review with enabled true/delivery_mode universal and prepare/review legacy signoff keys plus built-in legacy moderator, project_required_review_lanes `['code-reviewer']`, review_policies `{}`, changes `[{'change_id':'1aaaa-enh pinned','kind':'enh','sha256':sha256(b'# Pinned\n')}]`, requested_lanes `[]`. Hash UTF-8 JSON with sorted keys, separators `(',', ':')`, ensure_ascii false. No production canonicalizer, snapshot or digest helper computes the expected value.

Observed: historical digest exactly `e9890bb019dede839a4db0108256ffd250220007af7836d1870d3dd5db2a1082`; replacing wave_review with enabled true/delivery_mode targeted exactly `e73c274d443770ba4e64740c25700dadd457a340225587c3c2d1a54ef1705081`. A copy with evaluator_version 8 differed and was rejected by equality. Production snapshot of the canonical council keys/actor with the same tiny fixture matched the independent historical digest. Both goldens and the deliberate mutation control passed. This verifies feasibility and today's default compatibility, not the planned renamed-profile implementation or a universal digest reference.

### E6 — Strict upgrade gate

Public path: `upgrade_wavefoundry.main`, using the fixture's canonical upgrade lock and memory-state producers.

Command: `python3 -B -m unittest -v test_upgrade_wavefoundry.HistoricalMemoryUpgradeGateTests.test_resume_after_memory_cannot_bypass_failed_review_or_docs_gate test_upgrade_wavefoundry.HistoricalMemoryUpgradeGateTests.test_publication_verbs_cannot_bypass_failed_review_or_docs_gate`.

Expected and observed: 2 tests passed, 0 skips, 0.149 seconds. A retained failed docs gate caused memory resume/publication refusal and index publication was not called; the diagnostic directed the caller to `--resume-after-gate`, with memory state retained. This is actual CLI guard evidence with mocked publication boundaries, not an end-to-end successful upgraded docs tree. C5 explicitly retains this refusal contract.

## Evidence integrity and limits

For the readiness propositions above, each lane may cite this report and the relevant E1–E6 groups with `execution_status=executed`, `probe_class=local_safe`, `authorization_status=authorized`, `safe_boundary=false`, `unexecuted_remainder_prohibited=false`, `universal_claim=false`. Named direct producer/migration boundaries were actually executed rather than inferred. The five integrity booleans are honestly **true**: `test_ran_without_unintended_skip`, `public_path_reached` (the explicitly named public or faithful boundary), `boundary_values_realistic`, `assertions_non_vacuous`, `known_bad_detected`. Known-bad method: `readiness-safe-control`, specifically wrong actor/phase/conflicting replay, equivalent repair identities, current missing retry behavior, downstream ownership leakage, perturbed historical payload and retained failed docs gate. Fresh context and independence are true for this readiness reviewer. Record each lane's exact actor when converting its judgment into an event; do not claim separate reviewer contexts.

MCP `code_read` and `code_keyword` were discovered and successfully invoked before source retrieval. Reads were from current files; no semantic-index freshness or stale shared-server runtime claim is made. Relevant roots/roles, seeds 180/209/215, current architecture layering/threat model and the source anchors named above were consulted. Source mechanism claims are bounded to those reads and probes; no whole-tree actor-consumer or inventory completeness claim is made. The shared Rust wave edits other graph paths and no graph qualification ran here.

Delivery still owes default/renamed profile tests without new skips, inventory omission/missing/stale controls, actual declaration reload, runtime configured-role collisions, byte-preserved legacy ledgers, extra-alias replay/repair guards, parser preservation controls, contained-path refusals, upgrade-driver custom-doc success, preview and interrupted retry. These are not skipped readiness checks and cannot inherit the readiness booleans as delivery evidence.

## Reviewed fingerprints

Git working-tree blob hashes captured after the probes (not commits):

| Artifact | Hash |
| --- | --- |
| 204ml admitted document | `5b45eef6246a235642055b23a2bdc869d750bf79` |
| 204mm admitted document | `d3104dbf677bf9003547333d159794c88ed2c26d` |
| 204mn admitted document | `c241852694bc336f1fead1afc956f2e3c169c655` |
| scripts/review_evidence.py | `b8f6c17a6ebb70bf7daeebe5a95d9781300996e5` |
| scripts/review_policy.py | `a67dca16eb6461493467eb987f20b168b9ee2058` |
| scripts/vocabulary_profile.py | `850edd68ad3200312c1012b6964fb16322655907` |
| scripts/render_agent_surfaces.py | `e1f85b8d24a9a284263683e3a8f370ded619092c` |
| scripts/upgrade_wavefoundry.py | `8dadb8e521a9b7b04cbde761a82e056be25fcfbc` |
| scripts/tests/test_distribution_seams.py | `c81059293654443b6a9c98759e4dc4735874fe18` |
| scripts/tests/test_council_signoff_keys.py | `0c771e34fd00ab7a47836d6d9c785f188560c067` |

Script paths in this table are relative to `.wavefoundry/framework/`. A source or digested plan change requires assessing its effect before reusing this evidence.

Validation boundary: `wf_validate_docs()` after report creation returned `passed: true`, empty errors/warnings and `docs-lint: ok`.
