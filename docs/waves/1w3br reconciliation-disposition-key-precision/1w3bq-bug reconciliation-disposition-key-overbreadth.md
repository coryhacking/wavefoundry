# Make Reconciliation Dispositions Finding-Specific

Change ID: `1w3bq-bug reconciliation-disposition-key-overbreadth`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-22
Wave: 1w3br reconciliation-disposition-key-precision

## Rationale

Reconciliation dispositions currently key a finding by file path, retired surface, and matched substring. That survives harmless line movement, but it is broader than a finding: every occurrence of the same retired token in one file receives the same key. A truthful historical note can therefore silence a later live instruction containing that token in the same file. The `1.19.0+pkw3` downstream upgrade demonstrated the boundary concretely: seven historical occurrences in `docs/agents/session-handoff.md` collapsed to three keys, so each recorded judgment also suppresses any future identical token in that file.

The scanner must keep historical-record dispositions durable across unrelated edits without turning them into file/token allowlists. Compatibility also matters: existing repositories already have version-1 keys, whose bytes and candidate relationships must remain visible without allowing an information-poor legacy key to suppress a current finding.

## Requirements

1. Introduce one exact version-2 disposition identity. Its wire form is `v2:` followed by the first 32 lowercase hexadecimal characters of SHA-256 over five ordered UTF-8 fields: repository-relative file, retired surface, matched text, complete logical-line text without its line terminator, and nearest preceding Markdown ATX heading outside fenced code (the complete heading line without its line terminator, or empty when none applies). Canonicalize each field as its UTF-8 byte length in ASCII decimal, then `:`, then its bytes, and concatenate the five encoded fields without another separator. The key must not include an absolute path or physical line number, so harmless line movement and unrelated edits preserve identity.
2. Treat duplicate candidates conservatively. If two current findings resolve to the same version-2 fingerprint, no disposition may suppress either until the operator makes the source text/context distinguishable; report the ambiguity instead of selecting by scan order or line number.
3. Preserve version-1 store bytes and diagnostic compatibility without preserving their unsafe suppression authority. A legacy 16-hex key never suppresses a current finding: with zero current candidates it is dormant; with one candidate it reports that candidate and its proposed v2 key for operator reclassification; with multiple candidates it reports every candidate and the ambiguity. Only an explicit, unique v2 `historical-record` entry may suppress a finding.
4. Keep `scan_repo` as the complete audit view. Apply dispositions only at the reported reconciliation-channel boundary, as today. Malformed stores continue to fail open and suppress nothing.
5. Emit the exact versioned key and disposition state in structured findings and human upgrade guidance. Distinguish `unrecorded`, `v2-historical-record`, `v2-ambiguous`, `legacy-dormant`, `legacy-reclassification-required`, `legacy-ambiguous`, and `unknown-version`; explain that legacy entries remain preserved but fail open, and give the operator path for adding the proposed v2 `historical-record` entry after reclassification. Do not auto-edit `docs/reconcile-dispositions.json`.
6. Preserve the existing additive store schema (`[{"key": ..., "status": "historical-record"}]`) and accept both legacy 16-lowercase-hex keys and exact `v2:<32-lowercase-hex>` keys. Unknown versions, malformed keys, and legacy keys suppress nothing while their store bytes remain untouched.
7. Add non-vacuous regressions using the exact downstream shape: seven distinct historical logical lines produce exactly three legacy v1 keys and seven distinct v2 keys. Seven explicit v2 `historical-record` entries reduce the historical reported count from seven to zero; appending one live instruction with a reused retired token yields eight raw findings and exactly one reported finding. Execute and reject the known-bad v1 blanket behavior, which reports zero after that append. Also cover harmless line movement, heading-context change, genuinely identical duplicate-fingerprint ambiguity, malformed stores, legacy zero/one/many diagnostics, and unknown-version handling.
8. Update canonical upgrade guidance, its self-hosted authored twin, tests, and the current release changelog section selected at implementation time. Do not change the retired-surface classifier, scan exclusions, host-permission/provenance channel routing, or any wave-review lifecycle contract.

## Scope

**Problem statement:** A disposition intended for one truthful historical finding can suppress a different current finding because version-1 identity ignores line content and context.

**In scope:**

- Versioned, content/context-specific disposition identity.
- Conservative duplicate handling and legacy-key compatibility.
- Structured and human-readable ambiguity/action guidance.
- Exact downstream-derived and mutation-style regression controls.
- Canonical seed plus self-hosted upgrade-guidance parity.

**Out of scope:**

- Changing which retired surfaces are detected.
- Rewriting or deleting historical narrative.
- Automatically editing or migrating downstream disposition stores.
- Using physical line numbers, absolute paths, timestamps, or scan-order ordinals as identity.
- Changing secrets-scan disposition behavior or sharing a store between scanners.
- Changing upgrade blocking policy; reconciliation remains report-only.

## Acceptance Criteria

- [x] AC-1: Two findings in the same file with the same retired surface and matched token but different logical-line text or nearest Markdown heading receive different exact `v2:<32-lowercase-hex>` keys derived from the specified length-prefixed payload; moving either line without changing its text/heading leaves its key unchanged.
- [x] AC-2: When multiple current findings share one complete version-2 fingerprint, neither is dispositioned, every candidate remains in the reported reconciliation channel, and structured plus human output names the ambiguity without relying on line order.
- [x] AC-3: A legacy version-1 `historical-record` entry never suppresses a current finding and never mutates the store; zero candidates are dormant, one candidate reports `legacy-reclassification-required` plus its proposed v2 key, and multiple candidates report `legacy-ambiguous` for every candidate. Only one explicit, non-duplicated v2 entry suppresses.
- [x] AC-4: `scan_repo` continues to return dispositioned findings, `scan_repo_channels` alone applies suppression, malformed/unknown-version stores fail open, and host-permission plus renderer-provenance routing is unchanged.
- [x] AC-5: Structured findings expose their exact versioned key and one of the declared disposition states; upgrade prose explains live repair, version-2 historical recording, fail-open legacy reclassification, and ambiguous-key recovery without creating a new stale-reference hit in living guidance.
- [x] AC-6: The downstream-derived fixture proves exact counts: seven historical raw findings, three unique v1 keys, seven unique v2 keys, zero reported after seven v2 dispositions, then eight raw and exactly one reported after appending a live instruction. Known-bad version-1 blanket suppression is executed and rejected because it reports zero after the append.
- [x] AC-7: Focused reconciliation, CLI, upgrade, shipped-guidance, channel-boundary, and packaging tests pass; the complete framework suite passes without unintended skips; `wf_validate_docs` and `git diff --check` are clean; the selected release changelog section describes the compatibility boundary accurately.

## Tasks

- [x] Define the exact `v2:<32-lowercase-hex>` parser and length-prefixed five-field fingerprint without changing classifier ownership.
- [x] Implement exact Markdown heading-context capture and conservative duplicate grouping in `reconcile_scan.py`.
- [x] Keep legacy keys diagnostic-only, add zero/one/many reclassification states, and keep unknown/malformed keys fail-open without store mutation.
- [x] Extend structured findings and upgrade summary guidance with key version, disposition state, and ambiguity recovery.
- [x] Update seed 160 and the self-hosted upgrade prompt without introducing a living retired-reference literal.
- [x] Add the exact seven/v1-three/v2-seven/live-eighth fixture, legacy known-bad controls, duplicate ambiguity, movement, context-change, and channel-routing tests.
- [x] Update the implementation-time release changelog section and run focused/full verification, docs lint, and diff validation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| identity-contract | implementer | — | Pin v2 inputs, duplicate semantics, and legacy compatibility before code changes. |
| scanner-implementation | implementer | identity-contract | Keep raw audit and three-channel routing boundaries intact. |
| upgrade-guidance | implementer | identity-contract | Update structured/human carriers without repeating retired literals in living docs. |
| verification | qa-reviewer | scanner-implementation, upgrade-guidance | Execute downstream fixture, known-bad algorithm, channel matrix, and full suite. |

Write-owning lane: `implementer`. Read-only delivery lanes: `code-reviewer`, `qa-reviewer`, `docs-contract-reviewer`, and `release-reviewer`.

Protected surfaces:

- Existing `docs/reconcile-dispositions.json` bytes in target repositories are operator-owned and must not be auto-rewritten.
- `scan_repo` remains the complete, unsuppressed audit view.
- Host-permission and renderer-provenance channel ownership remains unchanged.
- Closed waves, changelog history, and downstream historical narratives remain truthful evidence.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py`
- `.wavefoundry/framework/scripts/tests/test_wf_cli.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `CHANGELOG.md`

## Affected Architecture Docs

N/A. The change refines identity and compatibility inside the existing reconciliation scanner and upgrade-reporting path; it adds no module, channel, persistence location, or permanent test tier. Record this N/A in the Progress Log after implementation unless scope expands.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Establishes the finding-specific identity that fixes the defect. |
| AC-2 | required | Prevents duplicate transposition from recreating silent suppression. |
| AC-3 | required | Keeps existing stores usable only where their meaning is unambiguous. |
| AC-4 | required | Preserves fail-open audit and channel ownership boundaries. |
| AC-5 | required | Makes the compatibility and recovery path actionable to operators. |
| AC-6 | required | Reproduces the field failure and kills the old blanket behavior. |
| AC-7 | required | Supplies integrated delivery and release evidence. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-22 | Plan authored from the downstream `1.19.0+pkw3` disposition report; implementation has not started. | Seven occurrences, three legacy keys, reconciliation 7→0 after dispositions; current `disposition_key` contract. |
| 2026-08-22 | Readiness cycle 1 made legacy keys diagnostic-only and pinned the exact v2 wire format plus 7/3/7/8→1 oracle. | `RED-READY-LEGACY-RETARGET-001`; `QA-READY-V2-ORACLE-001`; current replacement-live probe remains suppressed under v1. |
| 2026-08-22 | Thought: implement in dependency order—capture stable line/heading context, add v2 identity and fail-open disposition states at `scan_repo_channels`, update the fresh-runner summary and guidance carriers, then execute focused, mutation, package, and full-suite verification. | Wave readied and opened on receipt `review-policy-91b19d1cb76f3294eb86`; pre-implementation memory brief reviewed. |
| 2026-08-22 | Implemented finding-specific v2 identities, conservative duplicate handling, diagnostic-only v1 compatibility, structured/operator guidance, and canonical/self-hosted documentation. No architecture document changed because the existing scanner, channel, store, and upgrade ownership boundaries remain intact. | Exact 7/3/7 and appended-live 8→1 regression; movement/context/fence/duplicate/legacy/unknown/store-preservation controls; clean live reconciliation census. |
| 2026-08-22 | Verification complete. A pre-existing background-refresh test assertion was narrowed to count index-worker launches rather than incidental liveness subprocesses; product behavior was unchanged. | 60 scanner tests; 526 upgrade and shipped-reference tests; 112 packaging tests; 51 CLI tests; full suite 7,496 tests across 64 files in 227.437s; `wf_validate_docs`; `git diff --check`. |
| 2026-08-22 | Delivery review tightened closing-fence recognition and exposed settled-v2 and dormant-v1 store states through a separate read-only diagnostic projection; the three finding channels and operator-owned store remain unchanged. | Backtick/tilde trailing-text fence controls; structured and human `legacy-dormant` / `v2-historical-record` regressions; 598 affected tests; full suite 7,499 tests across 64 files in 229.265s; clean docs lint, diff check, and 0/0/0 live channel census. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-22 | Select the exact `v2:<32-lowercase-hex>` content + heading-context fingerprint, conservative duplicate refusal, and diagnostic-only legacy compatibility. | It survives harmless movement, distinguishes the observed historical lines, avoids automatic store mutation, and never lets a v1 key retarget suppression to replacement prose. | **Physical line number:** simple but harmless edits resurrect judgments and line insertion can retarget them. **Legacy key + occurrence ordinal:** compact but scan-order insertion can transfer a judgment. **Unique-only v1 suppression:** rejected because replacement live prose can remain the sole candidate. |
| 2026-08-22 | Keep the store additive and operator-owned. | Automatic migration cannot know whether an old broad judgment intended one or several current occurrences. | Rewrite every v1 key to all current v2 candidates; drop all legacy entries immediately. |
| 2026-08-22 | Treat exact duplicate fingerprints as ambiguous instead of adding scan order. | Two indistinguishable candidates cannot safely inherit one judgment; visible false positives are safer than hidden live instructions. | Suppress all duplicates; select first/last occurrence. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Existing v1 dispositions reappear as findings. | Preserve the entries, report zero/one/many candidate state and proposed v2 keys, and require explicit operator reclassification before suppression. |
| Heading edits invalidate otherwise historical judgments. | This is fail-safe and intentional; the changed context requires reclassification. |
| Identical lines under one heading remain indistinguishable. | Suppress none while duplicate fingerprints exist; require source clarification or separate contextual wording. |
| Living upgrade guidance flags its own retired examples. | Keep exact literals in excluded canonical seed/test fixtures and use classifier-neutral wording in the self-hosted prompt. |
| Scanner channel behavior drifts during refactor. | Run reconciliation, host-permission, and renderer-provenance suites together with near-miss controls. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
