# Full Scan Reconciles Now-Suppressed Pending Findings

Change ID: `1p4a2-enh full-scan-reconciles-suppressed-pending-findings`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

When a ruleset or allowlist change makes a previously-flagged value no longer a finding, the existing `pending` entry in `docs/scan-findings.json` lingers indefinitely. Its source line still exists, so the line-removed stale sweep (`_sweep_stale_exceptions`) does not touch it, and the per-hit matching loop in `_match_hits_for_file` only processes values the **current** ruleset still produces — so nothing re-evaluates a now-suppressed pending entry against the current rules. The phantom keeps **hard-blocking `wave_close`** (which blocks on any `pending`) and clutters the ledger, making a fixed bug look live.

Field-tested example (this wave): `DynamoDB/Secrets` (`exc-001` in a real project) was flagged under the `p3zo` build, where the `finding["line"]`=line-number bug defeated the 1p44u docs-prose clause's prose-shape test. The line-text fix landed in `p49k`, after which **every** scan correctly suppresses that capture (reproduced: `eval_filter(generic-api-key) => True`) — yet `exc-001` persisted in the ledger because no pass reconciles pending entries against the current ruleset. The operator saw a phantom FP for an already-fixed bug.

## Requirements

1. On a **full** scan (`scan_all=True`), an existing `pending` finding whose source line still exists but which the current ruleset no longer produces as a hit is removed from `docs/scan-findings.json`.
2. Only `pending` entries are pruned — `false-positive`, `suspected-secret`, `confirmed-secret`, and operator-acknowledged entries are **never** removed by this pass.
3. Entries without a stored `line_hash` (legacy, pre-hash entries) are never pruned.
4. **Incremental** scans never prune (they re-evaluate only changed files, so an untouched file's entries must stay); files skipped by the size/binary guards (1p44s) never trigger pruning of their entries.
5. All existing reconciliation behavior is preserved — the line-removed sweep, line-drift rebinding, the path-allowlist sweep, and the deleted-file sweep are unchanged.

## Scope

**Problem statement:** A ruleset improvement leaves phantom `pending` entries that the current ruleset already suppresses; they keep blocking `wave_close` and cluttering the ledger because no reconciliation pass re-evaluates still-present-but-now-suppressed pending entries.

**In scope:**

- A full-scan-only prune, inside `_match_hits_for_file`, of `pending` entries that have a `line_hash` (so they survived the line-removed sweep → line present) but whose `id` was not bound to any current hit (`id ∉ matched_ids` → not produced by the current ruleset).
- Threading `scan_all` into `_match_hits_for_file` as `prune_suppressed`.
- Unit tests covering prune, classification-preservation, still-produced retention, incremental safety, legacy-entry safety, and line-removed regression.
- A behavioral note in `docs/references/scan-findings-format.md`.

**Out of scope:**

- Pruning any non-`pending` entry (never — operator classifications are load-bearing).
- Reconciliation on incremental scans.
- Any change to the `wave_close` hard-block-on-`pending` semantics.
- Surfacing a per-scan prune count in the `wave_scan_secrets` MCP response (possible follow-up; this pass is silent, consistent with the three existing ledger sweeps).

## Acceptance Criteria

- [x] AC-1: On a full scan, a `pending` entry whose line is present but no longer produced by the current ruleset is removed from `docs/scan-findings.json`.
- [x] AC-2: `false-positive` / `suspected-secret` / `confirmed-secret` entries that are no longer produced are **not** removed (classifications preserved).
- [x] AC-3: A `pending` entry that **is** still produced by the current ruleset is not removed.
- [x] AC-4: An incremental scan (`scan_all=False`) does **not** prune now-suppressed pending entries (untouched-file safety).
- [x] AC-5: A `pending` entry without a `line_hash` (legacy) is not pruned.
- [x] AC-6: A `pending` entry whose line was **removed** is still handled by the existing line-removed sweep (no regression / no double-handling).
- [x] AC-7: Full framework suite green (2923); `docs-lint` clean.
- [x] AC-8 (security / fail-closed): when any rule fails regex compilation (degraded ruleset), the full-scan prune is skipped entirely (`prune_suppressed = scan_all and not rules_degraded`) — a `pending` entry the broken rule would catch is never silently dropped. Regression test `test_broken_rule_disables_prune_fail_closed`.

## Tasks

- [x] Add `_sweep_suppressed_pending(exceptions, rel_path, matched_ids)` helper (pending-only, line_hash-required, id-not-in-matched_ids).
- [x] Thread `prune_suppressed: bool = False` into `_match_hits_for_file`; invoke the sweep after the existing line-removed sweep, guarded by `lines`.
- [x] Pass `scan_all` as `prune_suppressed` from the `check_hardcoded_secrets` phase-2 call.
- [x] Register freshly-created entries in `matched_ids` so a new current hit is never pruned (regression caught by the suite).
- [x] Add unit + integration + end-to-end tests (`TestSuppressedPendingReconciliation`, 10) covering AC-1…AC-6.
- [x] Add a behavioral note to `docs/references/scan-findings-format.md` (full-scan reconciliation of pending entries) + re-sync the framework template copy.
- [x] Run the full suite + `wave_validate`; mark ACs and flip Change Status to `complete`.

## Agent Execution Graph


| Workstream            | Owner       | Depends On         | Notes                                                        |
| --------------------- | ----------- | ------------------ | ------------------------------------------------------------ |
| implement-prune       | Engineering | —                  | Helper + thread `scan_all` + phase-2 call in secrets_validators.py |
| tests                 | Engineering | implement-prune    | `TestSuppressedPendingReconciliation`                        |
| doc-note              | Engineering | implement-prune    | scan-findings-format.md (both copies) reconciliation note    |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` — `_match_hits_for_file` is the shared per-file reconciliation path; the edit is additive (a new guarded sweep after the existing one) and does not alter the hit-matching loop.

## Affected Architecture Docs

N/A — confined to the secrets-validator module's per-file reconciliation path; no module boundary, control-flow, layering, or verification-architecture change. The reference doc `docs/references/scan-findings-format.md` (not an architecture doc) gains a one-paragraph behavioral note.

## AC Priority


| AC   | Priority   | Rationale                                                                            |
| ---- | ---------- | ------------------------------------------------------------------------------------ |
| AC-1 | required   | The core behavior — prune now-suppressed pending phantoms on full scan.              |
| AC-2 | required   | Safety: never drop operator classifications — the highest-risk failure mode.         |
| AC-3 | required   | Correctness: a still-valid pending finding must survive.                             |
| AC-4 | required   | Safety: incremental scans must not prune untouched-file entries.                     |
| AC-5 | important  | Legacy entries without `line_hash` are left for backward compatibility.              |
| AC-6 | important  | No regression / no double-handling with the existing line-removed sweep.            |
| AC-7 | required   | Suite + lint green is the regression gate.                                           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-09 | Change opened from field-test follow-up: `exc-001` (`DynamoDB/Secrets`) was a phantom `pending` entry the current ruleset already suppresses, surfaced because no pass reconciles pending entries against current rules. Designed the full-scan-only, pending-only prune grounded in `_match_hits_for_file`'s `matched_ids` + the existing line-removed sweep. | This doc; reconciliation-flow read of `secrets_validators.py:324-391, 833-976, 1164-1182`. |
| 2026-06-09 | Implemented: `_sweep_suppressed_pending` helper; `prune_suppressed=scan_all` threaded through `_match_hits_for_file`; reconciliation note in scan-findings-format.md (both copies). **Regression caught by the suite:** the first cut pruned freshly-created pending entries because new entries were never added to `matched_ids` (only `_find_exception` populated it for existing entries) — two existing tests (`test_new_match_appends_pending_entry_and_fails`, JWT `test_integration_exp_date_persisted_in_findings`) failed; fixed by registering each new entry's id in `matched_ids`. Without that, a full scan would have dropped every NEW finding — a real security hole the tests blocked. | `secrets_validators.py` (helper + thread + `matched_ids.add` on new entry); `TestSuppressedPendingReconciliation` (10 tests); full suite **2922 green**; `wave_validate` → `docs-lint: ok`. |
| 2026-06-09 | **Close-readiness adversarial review (4-lens) caught one close-gating `major`:** a project rule that fails regex compilation degraded the scan, and the prune fell open — a still-valid `pending` entry on a readable file (whose only matching rule was the broken one) was pruned as if suppressed. Fixed: `rules_degraded` flag set in the `except re.error` branch; prune now `scan_all and not rules_degraded` (fail-closed). Added `test_broken_rule_disables_prune_fail_closed` (confirmed meaningful: `load_merged_ruleset` returns no error so the broken regex reaches the compile loop and raises `re.error`). Three other lenses PASS (real-secret/classified/field-fixes protected; refuted hypotheses traced to live guards). | `secrets_validators.py` (`rules_degraded` + fail-closed gate); full suite **2923 green**; `wave_validate` → `docs-lint: ok`. |


## Decision Log


| Date       | Decision                                                                 | Reason                                                                                                                                                              | Alternatives                                                                                          |
| ---------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 2026-06-09 | Prune only `pending`, only on a full scan, only entries with a `line_hash`. | Conservative scoping: never drop operator classifications, never touch untouched-file entries (incremental), never touch legacy entries. Full scan aligns with when ruleset changes take effect (a rules-hash change already auto-escalates to a full scan). | Prune on every scan (rejected: incremental doesn't re-evaluate untouched files → would lose real findings); prune any status (rejected: would erase operator decisions). |
| 2026-06-09 | Delete the phantom entry rather than mark it `superseded`.                  | Matches the operator's intent ("drop the ones now suppressed") and the three existing ledger sweeps (path-allowlist, deleted-file, line-removed) which all delete silently; `git` history of `docs/scan-findings.json` is the audit trail. | Add a `superseded` status/field (rejected: new ledger state + gate handling for marginal audit value over git history). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A real secret still in `pending` (untriaged) that the current ruleset now **over-suppresses** would have its only remaining gate-block (the pending entry) pruned. | Pruning is `pending`-only (anything an operator has classified is untouchable) and predicated on the current ruleset NOT producing the hit — meaning a fresh scan already would not flag it, so the ledger is being aligned to current detection, not weakened beyond it. Over-suppression is a ruleset bug to fix at the rule, not to paper over with a stale ledger entry. Full-scan-only bounds when this can happen to ruleset-change events. |
| A project rule that fails to compile produces no hits → its pending entries get pruned on a full scan (a fail-OPEN miss of a possibly-real secret). | **Fixed (close-readiness adversarial review, finding #1).** A regex-compile failure now sets `rules_degraded`, and the full-scan prune is skipped entirely when degraded (`prune_suppressed = scan_all and not rules_degraded`) — **fail-closed**: a missing hit on a broken ruleset is never misread as a legitimate suppression. Regression test `test_broken_rule_disables_prune_fail_closed`. The earlier "accepted" stance was wrong for a security control. |
| Silent deletion reduces in-band auditability. | Consistent with the three existing ledger sweeps (all silent); `git` history of `docs/scan-findings.json` preserves what was removed and when. Surfacing a prune count in the MCP response is a documented possible follow-up. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
