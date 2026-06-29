# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-28

wave-id: `1p8nw secret-scan-lifecycle-ids`
Title: Secret Scan Lifecycle Ids

## Objective

Make secret-scan finding IDs first-class Wavefoundry lifecycle artifacts: replace the legacy sequential `exc-###` IDs in `docs/scan-findings.json` with lifecycle-backed `<prefix>-sec` IDs — new findings immediately, existing findings migrated once (idempotent, with legacy traceability) — while preserving the secrets-gate semantics and the file/rule/line-hash/context-hash rebinding exactly. Ships in 1.9.5 alongside the closed Windows-hardening wave `1p8gx`.

## Changes

Change ID: `1p8l0-enh secret-scan-lifecycle-sec-ids`
Change Status: `implemented`

Change ID: `1p8o5-bug secret-scan-reconcile-downstream-fixes`
Change Status: `implemented`

Completed At: 2026-06-28

## Wave Summary

Wave `1p8nw` (Secret Scan Lifecycle Ids) delivered two changes: Secret scan lifecycle `sec` IDs and Secret-scan + reconcile downstream-feedback fixes. Notable adjustments during implementation: Secret scan lifecycle `sec` IDs: Expanded scope to convert existing `exc-###` IDs as well, with legacy traceability and idempotent migration.; Secret scan lifecycle `sec` IDs: Removed generated slugs from the target ID shape; use `<prefix>-sec` only.; Secret-scan + reconcile downstream-feedback fixes: Implemented all 4 items. #1: `EXCLUDED_BASENAMES` (CHANGELOG.md + prompt-surface-manifest.json) basename-matched in `is_excluded`; seed-160:48 reconciled. #2: `scan_repo_channels()` partitions findings into `(reconciliation, host_permission_flags)` on a `StaleReference.host_permission` flag (`HOST_PERMISSION_FILES` = `.claude/settings.local.json`/`.claude/settings.json`/`.cursor/settings.json`); threaded additively through `_run_reconciliation_scan` → `summary.host_permission_flags` + a distinct operator-prose section; seed-160:50 + mcp-tool-surface.md updated. #3: found the shipping chain already wired (shipped template + seed-012 install + seed-160 upgrade + byte-parity guard) AND the link validator strips inline-code so seed-213's inline-code ref is self-resolving — added `ScanFindingsFormatReferenceSafetyTests` pinning both. #4: `check_hardcoded_secrets` writes a bare `[]` on a clean full scan (`elif scan_all and not exists`), gated to full scans so the incremental missing-file rescan trigger is preserved; gate on `[]` unchanged (`_check_secrets_gate` returns no diagnostics on empty). 1p8l0 migration + secrets-gate code untouched.

**Changes delivered:**

- **Secret scan lifecycle `sec` IDs** (`1p8l0-enh secret-scan-lifecycle-sec-ids`) — 12 ACs completed. Key decisions: --------; Select lifecycle-backed scanner IDs in the form `<prefix>-sec` for new findings and migrate existing `exc-###` entries with legacy traceability.
- **Secret-scan + reconcile downstream-feedback fixes** (`1p8o5-bug secret-scan-reconcile-downstream-fixes`) — 5 ACs completed. Key decisions: --------; Bare `[]` for the always-present ledger (not a metadata wrapper).
## Journal Watchpoints

- **Security-faithfulness — gate semantics MUST NOT change (AC-11):** `pending`/`suspected-secret` still block close, `confirmed-secret` still produces the standing reminder, cleared `false-positive` still clears. This is a security-ledger change — adversarially review the migration before close; green tests can miss a silent gate-narrowing.
- **Idempotent migration + byte-for-byte field preservation:** `exc-###`→`sec` must preserve every non-ID field (status, confirmations, override reasons, line/context hashes, redacted matched text); running it twice must not re-change IDs or duplicate `legacy_id`. Test repeated runs.
- **Collision safety:** new + migrated `sec` IDs must dedupe against existing wave/change/ADR lifecycle prefixes AND existing `docs/scan-findings.json` IDs, including multiple findings minted in one scan.
- **Line-drift rebinding:** preserve `_find_exception`'s hash-fallback so line drift updates the existing `sec` record instead of minting a duplicate.
- **Do NOT leak `sec` as a change-doc kind:** keep `sec` scanner/lifecycle-library-scoped — it must not appear in `wave_new_*` kind lists or plan scaffolding (assert the kind lists are unchanged).
- **Legacy tolerance:** keep `exc-###` parsing for not-yet-migrated / imported target repos.

## Review Evidence

- wave-council-readiness: passed 2026-06-28 — plan fully authored (11 requirements, 12 ACs, operator-clarified to convert existing `exc-###` too, no slug); sound and contained (reuses lifecycle prefix generation for a `sec` kind, scoped to `secrets_validators` + `lifecycle_id` + the scan-findings format docs + the security-reviewer seed); ACs testable (ID regex `^[0-9a-z]{5}-sec$`, idempotent migration, collision-safety vs lifecycle prefixes + finding IDs, line-drift rebinding, `sec`-not-a-change-kind, legacy traceability). Load-bearing constraint: AC-11 — the secrets-gate semantics (pending/suspected block; confirmed reminds; cleared clears) MUST NOT change; a security-ledger migration that requires an adversarial review of the migration before close. Ready to implement.
- operator-signoff: approved 2026-06-28 — operator authorized close + the official 1.9.5 release (downstream-validated on the p8ob upgrade).
- wave-council-delivery: passed 2026-06-28 — moderator: wave-council; seats: code-reviewer, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, red-team. The MANDATED migration + gate-semantics adversarial review (security ledger) was run at RUNTIME: the `exc-###`→`sec` migration is idempotent (2nd run no-op), lossless (every non-ID field preserved), and records each record's OWN old id as `legacy_id` (exc-001→1p8k0-sec/legacy `exc-001`; exc-002→1p8k1-sec/legacy `exc-002` — NOT hardcoded); new + migrated ids are collision-safe (distinct within one scan; deduped vs lifecycle prefixes + existing finding ids); `_find_exception` line-drift rebinding is unchanged. Gate semantics UNTOUCHED — `_check_secrets_gate`/`_confirmed_secret_notice` not modified, and the non-vacuous `TestGateSemanticsUnchanged` drives the REAL gate for both id shapes (pending/suspected block, confirmed reminds, cleared clears — identical pre/post migration). `sec` is not a public change-doc kind (`VALID_CHANGE_KINDS` + lifecycle `--kind` choices unchanged); `exc-###` still tolerated. Full suite 3646 green; docs-lint clean. PASS to close. **1p8o5 (downstream-feedback fixes)** verified at runtime + downstream on the p8ob upgrade: #1 exclusion FPs dropped (nested `CHANGELOG.md` + `prompt-surface-manifest.json` excluded by basename, in-scope docs still flagged); #2 host allow-rule files split into a separate `host_permission_flags` channel (`.claude/settings.local.json` out of `reconciliation`, editable docs stay in `reconciliation`); #3 the `scan-findings-format.md` reference is self-resolving (inline-code; docs-lint strips it) and the doc ships via seed-012/seed-160, with a guard locking both in; #4 the always-present `[]` ledger is gated to full-scan + file-missing (incremental trigger + no-churn preserved) and the secrets gate still no-blocks on `[]` (gate code untouched). Full suite 3660 green; docs-lint clean. PASS to close.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-28: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: migrating the security ledger (`docs/scan-findings.json`) risks losing operator classifications or silently narrowing the secrets gate — mitigated by byte-for-byte non-ID field preservation, idempotence, `legacy_id` traceability, AC-2/AC-11 tests, and a MANDATORY adversarial review of the migration + gate semantics before close; strongest-alternative: keep `exc-###` or new-IDs-only — rejected because it leaves a permanently mixed ledger and does not meet the operator's lifecycle-ID + convert-existing requirement.)

## Prepare Review Evidence

- code-reviewer: passed 2026-06-28 — implementable with clear targets (`_next_exception_id` → `_next_secret_finding_id` returning `<prefix>-sec`; an idempotent `docs/scan-findings.json` migration helper; lifecycle `sec` support via a library kind or scanner wrapper); collision + line-drift rebinding reuse existing `_find_exception` behavior.
- architecture-reviewer: passed 2026-06-28 — reuses lifecycle prefix generation; module-local to `secrets_validators` + `lifecycle_id`; no new boundary (a small note in data-and-control-flow / cross-cutting only if lifecycle-ID policy is described as waves/changes/ADRs-only).
- qa-reviewer: passed 2026-06-28 — ACs testable: ID regex `^[0-9a-z]{5}-sec$`, migration idempotence (run-twice), collision vs lifecycle prefixes + finding IDs, line-drift rebinding, `sec`-not-in-`wave_new_*`-kinds, legacy `exc-###` tolerance, and gate-semantics-unchanged (AC-11) before/after migration.
- release-reviewer: passed 2026-06-28 — ships in 1.9.5 as a second wave alongside closed `1p8gx` (multi-wave release); changes are reachable/shippable; legacy tolerance protects imported target repos.
- docs-contract-reviewer: passed 2026-06-28 — `docs/references/scan-findings-format.md` + the `213-security-reviewer` seed updates are committed (AC-9/AC-10) and distinguish scanner ledger `sec` IDs from reviewer `SEC-1` finding IDs; `seed_edit_allowed` applies.

## Dependencies

- No external wave dependencies. Ships in the same version (1.9.5) as the closed wave `1p8gx windows-upgrade-hardening` (multi-wave release); independent code (`secrets_validators`/`lifecycle_id`/`scan-findings` vs the Windows-isolation surfaces).
