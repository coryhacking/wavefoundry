# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-09

wave-id: `1p44n framework-1p6-hardening`
Title: Framework 1P6 Hardening

## Objective

The Aceiss/Teton team's 1.6.0 upgrade field report surfaced a cluster of real defects in the framework's new hardcoded-secrets scanner and the `wave_upgrade` flow. A 5-agent grounding pass confirmed 19 of them against current source (one — `docs/scan-findings.json` self-scan — was already fixed earlier this session). This wave hardens those surfaces — upgrade-failure data-safety + state tracking, scanner performance/precision/value-filtering, the confirmation-resolution workflow, and seed/doc routing gaps — led by the data-safety lock-deletion fix (`1p44o`). Closes when all 19 ship with tests.

## Changes

Change ID: `1p44o-bug upgrade-lock-survives-gate-failure`
Change Status: `complete`

Change ID: `1p44p-bug upgrade-from-version-and-version-sources`
Change Status: `complete`

Change ID: `1p44q-bug upgrade-prune-count-reporting`
Change Status: `complete`

Change ID: `1p44r-enh resumable-upgrade-after-gate-failure`
Change Status: `complete`

Change ID: `1p44s-enh secrets-scanner-file-guards`
Change Status: `complete`

Change ID: `1p44t-enh secrets-scanner-generated-artifact-allowlist`
Change Status: `complete`

Change ID: `1p44u-enh generic-api-key-docs-path-scope`
Change Status: `complete`

Change ID: `1p44v-enh secrets-finding-dedup-and-comment-context`
Change Status: `complete`

Change ID: `1p44w-enh secrets-jwt-expiry-awareness`
Change Status: `complete`

Change ID: `1p44x-enh secrets-redaction-short-secret-tightening`
Change Status: `complete`

Change ID: `1p452-doc scan-rules-cel-header-comment-fix`
Change Status: `complete`

Change ID: `1p44y-enh false-positive-confirmation-override`
Change Status: `complete`

Change ID: `1p44z-enh secrets-confirmation-bootstrap-ordering`
Change Status: `complete`

Change ID: `1p450-enh secrets-full-scan-baseline-at-install-upgrade`
Change Status: `complete`

Change ID: `1p451-enh secrets-gate-failure-messaging`
Change Status: `complete`

Change ID: `1p453-doc seed-160-secrets-resolution-routing`
Change Status: `complete`

Change ID: `1p454-doc upgrade-cleanup-next-steps-reconcile`
Change Status: `complete`

Change ID: `1p455-doc scan-findings-format-reference-doc`
Change Status: `complete`

Change ID: `1p456-bug engine-ignores-global-value-filter`
Change Status: `complete`

Change ID: `1p457-enh false-positive-confirmation-expiry`
Change Status: `complete`

Change ID: `1p45b-bug lifecycle-id-dedup-across-plans-waves-adrs`
Change Status: `complete`

Change ID: `1p4a2-enh full-scan-reconciles-suppressed-pending-findings`
Change Status: `complete`

Change ID: `1p4d1-bug secrets-scanner-re2-python-regex-compat`
Change Status: `complete`

Completed At: 2026-06-09

## Wave Summary

Wave `1p44n` (Framework 1P6 Hardening) delivered 23 changes: Upgrade Lock Survives Docs-Gate Failure On A Half-Replaced Tree, Fix from_version Resolution and Consolidate Version Sources in Upgrade, Fix Upgrade Prune Count Reporting, Resumable Upgrade After Docs-Gate Failure, Secrets Scanner File Guards, Secrets Scanner Generated-Artifact Path Allowlist Defaults, Scope generic-api-key Docs/Markdown Prose With A Path Clause, Secrets Finding Dedup and Comment Context, Secrets Scan JWT Expiry Awareness, Secrets Redaction Short-Secret Tightening, Fix scan-rules.toml Header Comment to Reflect Actual CEL Behavior, False-Positive Confirmation Override And Reviewer-Count Clamp, Materialize Project Secrets Policy Before The First Upgrade Gate, Secrets Full-Scan Baseline at Install and Upgrade, Secrets Gate Failure Messaging Clarity, Route Secrets-Finding Resolution From Upgrade Docs Gate, Reconcile Upgrade Cleanup Next-Steps Output With Seed-160, Scan Findings Format Reference Doc, Engine Ignores the Global [allowlist] Value-Filter (regexes + stopwords), Time-Bounded False-Positive Confirmations (Yearly Re-Verification), Lifecycle ID Minting Must Dedup Across Plans, Waves, And ADRs, Full Scan Reconciles Now-Suppressed Pending Findings, and Secrets Scanner — RE2→Python Regex Compatibility (26 Detectors Silently Dead). Notable adjustments during implementation: Fix from_version Resolution and Consolidate Version Sources in Upgrade: **FIELD-TEST FOLLOW-UP — the read side was fixed but nothing WROTE it.** p49k real-project testing showed `framework_revision` still stale (`1.5.1+p3qj`) two upgrades on: only the self-host packager (`build_pack.update_manifest_revision`) ever wrote it, and the pack ships `framework/VERSION` but not the consumer's manifest — so `extractall` advances VERSION while `framework_revision` freezes, and `_read_installed_revision` (now correct) just reads a stale value. Added `_stamp_manifest_revision(root)` (read-modify-write `framework_revision` from the extracted VERSION; preserves other keys; no-op when VERSION/manifest absent/unparseable, never creates the manifest), called in `main()` right after surface rendering. Self-heals an already-stale consumer on next upgrade.; Resumable Upgrade After Docs-Gate Failure: Added `resume_after_gate` (re-runs ONLY docs-gardener+docs-lint vs the retained-lock tree; reads `failed_phase=='docs_gate'`; exits non-zero on repeat failure, 0 + clears marker on pass) + `--resume-after-gate` CLI; extract idempotence via `_tree_already_at`; server_impl valid_phases + phase→flag + docstrings; mcp-tool-surface.md wave_upgrade entry.; Secrets Scanner File Guards: Added three input guards to `scan_file_raw` (per-file size cap, NUL-byte binary sniff before `read_text`; max-line-length guard in the per-line loop), framework-owned constants near line 406, and AC-9 skip surfacing (`_record_scan_skip` → per-skip stderr line + in-process `_SCANNER_SKIPS`, reset per scan in `check_hardcoded_secrets`).

**Changes delivered:**

- **Upgrade Lock Survives Docs-Gate Failure On A Half-Replaced Tree** (`1p44o-bug upgrade-lock-survives-gate-failure`) — 7 ACs completed. Key decisions: --------; Keep the lock on a post-mutation (tree_mutated) failure and write a failure marker, rather than always removing it
- **Fix from_version Resolution and Consolidate Version Sources in Upgrade** (`1p44p-bug upgrade-from-version-and-version-sources`) — 9 ACs completed. Key decisions: --------; Read installed revision from `framework_revision` in `docs/prompts/prompt-surface-manifest.json`, falling back to `framework/VERSION`.
- **Fix Upgrade Prune Count Reporting** (`1p44q-bug upgrade-prune-count-reporting`) — 5 ACs completed. Key decisions: -------------------------------------------------------------------------------------------------; Prefer parsing `result.stderr` for `prune: ... N item(s)` to extract N as the count source.
- **Resumable Upgrade After Docs-Gate Failure** (`1p44r-enh resumable-upgrade-after-gate-failure`) — 8 ACs completed. Key decisions: --------; Add a dedicated `resume_after_gate` phase that runs only docs-gardener + docs-lint rather than re-running `preflight_to_docs_gate`.
- **Secrets Scanner File Guards** (`1p44s-enh secrets-scanner-file-guards`) — 9 ACs completed. Key decisions: -------------------------------------------------------------------; Skip over-long lines (`continue`) rather than truncate-and-scan.
- **Secrets Scanner Generated-Artifact Path Allowlist Defaults** (`1p44t-enh secrets-scanner-generated-artifact-allowlist`) — 7 ACs completed. Key decisions: ---------------------------------------------------------------------------------------------------------; Add generic name-agnostic min/map/snap path rules rather than extend the hardcoded library list at line 120.
- **Scope generic-api-key Docs/Markdown Prose With A Path Clause** (`1p44u-enh generic-api-key-docs-path-scope`) — 6 ACs completed. Key decisions: --------; Use a per-rule AND-combined path + content-signal filter clause on `generic-api-key`.
- **Secrets Finding Dedup and Comment Context** (`1p44v-enh secrets-finding-dedup-and-comment-context`) — 6 ACs completed. Key decisions: --------; Flag comment secrets via `in_comment`, do not auto-suppress
- **Secrets Scan JWT Expiry Awareness** (`1p44w-enh secrets-jwt-expiry-awareness`) — 7 ACs completed. Key decisions: --------; Surface the `exp` date and make past-exp downgrade a policy choice.
- **Secrets Redaction Short-Secret Tightening** (`1p44x-enh secrets-redaction-short-secret-tightening`) — 7 ACs completed. Key decisions: --------; Length-scale the reveal window (≤16 → ≤2+2 or full mask; ≥20 → up to 4+4) with a hard ~40% exposure cap, rather than a flat fixed window.
- **Fix scan-rules.toml Header Comment to Reflect Actual CEL Behavior** (`1p452-doc scan-rules-cel-header-comment-fix`) — 6 ACs completed. Key decisions: --------; Fix the comment text only; do not add Python-scanner support for the top-level `prefilter`/`filter` blocks.
- **False-Positive Confirmation Override And Reviewer-Count Clamp** (`1p44y-enh false-positive-confirmation-override`) — 8 ACs completed. Key decisions: --------; Ship BOTH an `override_reason` dismissal (parity with `server_impl.py:7908-7925`) and a reviewer-count clamp before `secrets_validators.py:633`.
- **Materialize Project Secrets Policy Before The First Upgrade Gate** (`1p44z-enh secrets-confirmation-bootstrap-ordering`) — 5 ACs completed. Key decisions: -------------------------------------------------------------------------------------------------; Preferred fix is to materialize `docs/scan-rules.toml` from committer auto-detect in the preflight phase before the first gate scan.
- **Secrets Full-Scan Baseline at Install and Upgrade** (`1p450-enh secrets-full-scan-baseline-at-install-upgrade`) — 7 ACs completed. Key decisions: -----------------------------------------------------------------------------------------; Add an explicit `scan_all=True` baseline at both install (seed-012, after 2.3a) and upgrade (seed-160, preflight) rather than changing the docs-lint default.
- **Secrets Gate Failure Messaging Clarity** (`1p451-enh secrets-gate-failure-messaging`) — 5 ACs completed. Key decisions: ------------------------------------------------------------------------; Sequence after 1p44y and reuse its override path in the new message text
- **Route Secrets-Finding Resolution From Upgrade Docs Gate** (`1p453-doc seed-160-secrets-resolution-routing`) — 6 ACs completed. Key decisions: ------------------------------------------------------------------------------------------; Fix as doc-only routing in seed-160; point at the existing seed-213 Pre-Scope loop.
- **Reconcile Upgrade Cleanup Next-Steps Output With Seed-160** (`1p454-doc upgrade-cleanup-next-steps-reconcile`) — 5 ACs completed. Key decisions: ------------------------------------------------------------------------; Defer the printed list to seed-160 instead of mirroring its backfills.
- **Scan Findings Format Reference Doc** (`1p455-doc scan-findings-format-reference-doc`) — 8 ACs completed. Key decisions: -------------------------------------------------------------------------------------------------; Document the schema in one new `scan-findings-format.md`; keep seed-213 authoritative for lifecycle.
- **Engine Ignores the Global [allowlist] Value-Filter (regexes + stopwords)** (`1p456-bug engine-ignores-global-value-filter`) — 8 ACs completed. Key decisions: --------; Wire the existing `[allowlist].regexes`/`stopwords` mirror rather than execute the top-level betterleaks `filter` CEL
- **Time-Bounded False-Positive Confirmations (Yearly Re-Verification)** (`1p457-enh false-positive-confirmation-expiry`) — 10 ACs completed. Key decisions: --------; Expired confirmations are ignored for counting but retained in `confirmations[]` (non-destructive).
- **Lifecycle ID Minting Must Dedup Across Plans, Waves, And ADRs** (`1p45b-bug lifecycle-id-dedup-across-plans-waves-adrs`) — 8 ACs completed. Key decisions: --------; Fix both halves: pass `repo_root` at MCP call sites AND scan ADRs in `_existing_prefixes`.
- **Full Scan Reconciles Now-Suppressed Pending Findings** (`1p4a2-enh full-scan-reconciles-suppressed-pending-findings`) — 8 ACs completed. Key decisions: ------------------------------------------------------------------------; Prune only `pending`, only on a full scan, only entries with a `line_hash`.
- **Secrets Scanner — RE2→Python Regex Compatibility (26 Detectors Silently Dead)** (`1p4d1-bug secrets-scanner-re2-python-regex-compat`) — 6 ACs completed. Key decisions: ------------------------------------------------------------------------------; Adapt at load via a translation shim; keep the `.toml` patterns Gitleaks/RE2-schema.
## Journal Watchpoints

- **Implement-first (data-safety):** `1p44o` (lock-survives-gate-failure) is the released data-safety root cause and absorbs the dashboard-reindex + cleanup-summary downstreams — implement before the rest.
- **Blocking dependencies:** `1p44r` (resumable upgrade) is **blocked by** `1p44o` (the lock must survive for resume to read state); `1p451` (messaging) **depends on** `1p44y` (override — it describes the escape path); `1p456` (value-filter) must be sequenced with `1p452` (the header comment must reflect the now-applied `[allowlist].regexes`/`stopwords`); `1p450` (baseline) pairs with `1p44z` (materialize policy first, then baseline); **`1p457` (confirmation-expiry) messaging is blocked by `1p451`** — both rewrite the same `secrets_validators.py:631-653` false-positive message branch, so land `1p44y` → `1p451` → `1p457` in that order (readiness review 2026-06-08).
- **Shared-file serialization watchpoint:** coordinate edits within each shared file — `upgrade_wavefoundry.py` (`1p44o`/`1p44p`/`1p44q`/`1p44r`/`1p454`), `secrets_validators.py` (`1p44s`/`1p44v`/`1p44x`/`1p44y`/`1p451`/`1p456`/`1p457`), `scan-rules.toml` (`1p44t`/`1p44u`/`1p44w`/`1p452`/`1p456`/`1p457`), `seed 213` (`1p457`), `cel_filter.py` (`1p44u`/`1p44w`), seeds `160`/`012` (`1p450`/`1p453`/`1p455`), `server_impl.py` mint sites (`1p45b`, coordinated with the upgrade-flow `server_impl.py` edits), `lifecycle_id.py` (`1p45b`). Note: `1p457` and `1p44y`/`1p451` all touch the `secrets_validators.py` false-positive branch + message strings — keep `_unique_confirmation_count`'s `(count, names)` arity stable.
- **Post-prepare admission watchpoint:** `1p457` (confirmation-expiry) and `1p45b` (lifecycle-ID dedup) were admitted AFTER the prepare-council PASS recorded below (which reviewed 19 changes). They have NOT been through a readiness pass — run a targeted council / re-prepare on these two before implementing them.
- **Gate watchpoint:** seed edits require `seed_edit_allowed`; the `secrets_validators.py` / `scan-rules.toml` / `upgrade_wavefoundry.py` edits are framework-maintenance → `framework_edit_allowed`. Close each gate immediately after.
- **Invariant watchpoint:** do not regress the `scan-findings.json` self-exclusion (fixed this session) or the 2778-test baseline; `1p456` must preserve recall (its AC-4); scanner changes that touch the parallel path must plumb new state through the worker initializer (`1p456` AC-6).
- **Deferred follow-up:** executing the top-level betterleaks `prefilter`/`filter` CEL blocks directly is deliberately NOT in scope — `1p456` wires the `[allowlist]` mirror instead and `1p452` documents the contract; revisit only if a betterleaks re-download needs it.

## Review Evidence

- wave-council-readiness: approved 2026-06-08 — PASS WITH IN-SESSION FIXES (moderator: wave-council; depth: full; seats: red-team primer, security-reviewer, architecture-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: best-alternative [tier-the-implementation]; must-fix-count: 0; recommended-count: 1 applied in-session [R-1: security-visibility AC-9 on 1p44s — size/binary skips must be surfaced, never silent]; strongest-challenge: the scanner is a SECURITY CONTROL, so 1p44s file-guards (skip oversized/binary) and 1p456 global value-filter (suppress matches) are higher-stakes than typical — a wrong threshold or over-suppression yields a MISSED real secret (false-negative); plus 19 changes across heavily-shared files (secrets_validators.py ×6, upgrade_wavefoundry.py ×5) risk integration conflicts; strongest-alternative: implement in strict dependency tiers — land+verify data-safety 1p44o first, then perf, then precision/workflow/docs — rather than one parallel batch (incorporated via Journal Watchpoints implement-first + dependency notes); falsification: working verdict PASS; strongest counter is silent size/binary skips on a security control; does not change the verdict because thresholds are generous (real tokens are short), recall is guarded (1p456 AC-4, 1p44s AC-7), and R-1/AC-9 makes skips visible/auditable — net security posture improves; verdict: PASS — admissible for implementation, data-safety 1p44o first)
- wave-council-delivery: approved 2026-06-08 — PASS WITH IN-SESSION FIXES (adversarial 6-dimension delivery review over the real diff with per-finding independent verification — 16 findings, 0 refuted; 2 MAJOR security findings — the 1p456 unanchored-regex false-negative and the 1p44u docs-recall gap — caught and FIXED in-session, plus the latent `finding["line"]`-is-a-number bug; see Review Checkpoints "Delivery-phase review" for full detail; full suite 2905 green post-fix; docs-lint clean)
- wave-council-delivery (post-signoff delta): approved 2026-06-09 — adversarial 4-lens review of the work added after the 2026-06-08 delivery signoff (the new change `1p4a2` ledger-prune, field-test fixes `1p44p` manifest-stamp / `1p44z` `confirmation_valid_days` materialization, and the `confirmed_at` field-name revert). Three lenses PASS — real-secret-still-blocks, classified-never-pruned, and field-fix drift all traced to live guards; refuted hypotheses (classified-prunable, incremental-prunes-untouched, skip-file-examined, datetime-fallback-residue) not carried. The incremental/skip lens caught one close-gating **MAJOR**: a project rule that fails regex compilation degraded the scan and the `1p4a2` prune fell **open**, pruning a still-valid `pending` entry on a readable file whose only matching rule was the broken one (fail-open miss of a possibly-real secret). FIXED in-session — `rules_degraded` flag + fail-closed gate (`prune_suppressed = scan_all and not rules_degraded`) + regression test `test_broken_rule_disables_prune_fail_closed`; full suite 2923 green, docs-lint clean. Delta delivered.
- wave-council-delivery (`1p4d1` RE2→Python regex shim): approved 2026-06-09 — adversarial 3-lens faithfulness review using a **Go RE2 oracle**. 25/26 RE2-ism rules oracle-faithful (no broadening, no FP flooding, fail-closed verified; the other complex cases `authress`/`gocardless`/`planetscale` confirmed across canonical + adversarial + 400-subject fuzz). One MAJOR **fail-open narrowing** caught: `curl-auth-header`'s single-quote branch went dead because the scoped flag over-ran the `|` alternation bar (100% of single-quoted curl secrets missed). FIXED in-session — `_enclosing_group_close` now stops at a same-depth `|`, so a scoped group never crosses an alternation bar — + regression tests (`test_alternation_scoped_flag_does_not_kill_branch`, `test_scoped_flag_never_crosses_alternation_bar`); all rules compile, both quote branches match, scoping-edge-cases and integration/FP lenses PASS clean. Full suite 2930 green. Shim delivered.
- operator-signoff: approved 2026-06-09 — operator requested wave closure ("let's close this wave") and explicitly scoped the RE2→Python regex fix into this wave ("let's do this now in this wave"). All 23 changes complete; CHANGELOG 1.6.0 updated; suite 2930 green; docs-lint clean; secrets gate clean (0 pending).

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-08: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, security-reviewer, architecture-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: best-alternative; strongest-challenge: scanner-as-security-control — 1p44s guards + 1p456 value-filter can cause missed-secret false-negatives if mis-tuned; 19 changes across shared files (secrets_validators.py ×6, upgrade_wavefoundry.py ×5) need careful serialization; strongest-alternative: tiered dependency-ordered implementation with data-safety 1p44o landed+verified first (captured in Journal Watchpoints); security-reviewer: skip thresholds generous + recall guarded (1p456 AC-4, 1p44s AC-7), but size/binary skips were silent → added AC-9 (surface skipped files); architecture-reviewer: the 1p44o lock-schema change (failed_phase/failed_at) is additive/optional and must land first so 1p44r/1p454/dashboard build on the final schema; qa-reviewer: every change carries test ACs and the 2778-test baseline is an invariant watchpoint; docs-contract-reviewer: 1p452 header comment must reflect the post-1p456 applied value-filter (sequenced in watchpoints); reality-checker: all 19 are file:line-grounded confirmed defects, not speculative — the one report false-alarm (install-log-format.md exists) is captured not-applicable in 1p455; must-fix: 0; recommended applied in-session: R-1 security-visibility AC-9 on 1p44s)
- **Targeted readiness — late-admitted `1p457` + `1p45b` — 2026-06-08: both READY-WITH-FIXES** (2-agent grounded readiness workflow; no admission blockers; satisfies the post-prepare admission watchpoint). Fixes are implementation-time refinements (apply when each lands — `1p457` is Tier-4, `1p45b` Tier-7). **`1p457` (confirmation-expiry):** (a) thread a fixed `as_of` through `_unique_confirmation_count`/`check_hardcoded_secrets` and into ALL false-positive-branch tests (existing too — `test_secrets_validators.py:347-369/599-628/698-735`), not just new ones, or they go wall-clock-flaky in June 2027; (b) sequence its messaging AFTER `1p451` (shared `secrets_validators.py:631-653` branch — see blocking-deps watchpoint); (c) seed-213 must name the `confirmed_at` field + the "append a new dated entry on re-confirm, never mutate" contract; (d) add a `confirmation_valid_days` policy-merge test. **`1p45b` (lifecycle-id dedup):** (a) AC-4's `discover_repo_root()` fallback would break the existing `repo_root=None` tests (`test_lifecycle_id.py:234/331`) — use a sentinel `UNSET` default so explicit `None` keeps no-scan behavior (cleaner than overloading `None`); (b) plumb `repo_root` into `new_change()` — the `server_impl.py:4734` path needs a new param (else only `:4306`/`:4768` get fixed); (c) decide + document whether `--prefix-only` fires the MCP-first stderr reminder; (d) add an ADR-populated peek/commit (`commit=False` then `True`) consistency test. No security regression in either (1p45b only widens the dedup set + adds a missing `repo_root`; 1p457 is fail-closed). Verdict: both admissible — proceed with the tiered implementation.

- **Delivery-phase review [delivery-review] — 2026-06-08: PASS WITH IN-SESSION FIXES** (adversarial multi-agent review: 6 dimensions — security-false-negative, correctness-upgrade-statemachine, shared-file-integration, test-adequacy, docs-contract-truthfulness, regression-risk — each finding independently verified against the merged diff; 16 confirmed findings, 0 refuted. **Dimension verdicts:** shared-file-integration PASS; correctness-upgrade-statemachine / test-adequacy / docs-contract PASS_WITH_NOTES; security-false-negative + regression-risk CONCERNS — both driven by the same root bug, now fixed.

  **FIXED in-session (2 MAJOR security):**
  1. *1p456 false-negative (critical):* the global value-filter applied the authored regex `(?i)^true|false|null$` via `re.search` against the captured secret; Python alternation precedence left the `false`/`null` branches unanchored, so any high-entropy secret CONTAINING "false" or ENDING in "null" was silently dropped fleet-wide across every rule — a NEW false-negative the wave introduced by wiring the previously-inert filter. **Fix:** engine now uses `re.fullmatch` (whole-value semantics — defends against any un-anchored allowlist regex) AND the regex was anchored to `(?i)^(?:true|false|null)$`. Recall test added (`test_secret_containing_noise_substring_still_fires`).
  2. *1p44u recall gap (major):* the docs clause `entropy(secret) <= 4.2` suppressed real moderate-entropy (e.g. 32-char hex) API keys in `.md`/`docs/`, with the recall test only covering entropy > 4.2. **Fix:** AND-combined with a prose-shape line signal (`matchesAny(finding["line"], [(?:\\S+\\s+){4,}\\S+])`) so a BARE key assignment in docs still fires while prose sentences are suppressed; recall test added (`test_bare_moderate_entropy_key_assignment_in_docs_still_fires`).

  **Latent bug also fixed (uncovered while fixing #2):** the CEL context's `finding["line"]` was the line NUMBER, not the line TEXT, so the existing import-statement and BitBake value-exclusion clauses (`matchesAny(finding["line"], …)`) never matched — `scan_file_raw` now passes the line text (betterleaks-correct), activating those clauses and enabling the prose signal.

  **Other fixes applied:** parallel-path test made non-tautological (detects a silent serial fallback) + a parallel worker-side oversized-file skip test; resume_after_gate MCP non-zero-exit test; `failed_at` refreshed on a repeated resume failure; `cel_filter.py` module docstring lists `jwtExpired`/`jwtExp`; `scan-findings-format.md` field-attribution caption scoped.

  **Accepted notes (no change):** 1p44s oversized/binary skips fail the gate OPEN by design (perf), surfaced via per-skip stderr (AC-9, process-safe) — an enhancement to also carry the skip count in the scan RESULT is a follow-up, not a blocker; the re-activated downgrade guard (1p44p) is an intended behavior change for re-installs/rollbacks; `_SCANNER_SKIPS` is a per-process ledger (documented). Verdict: PASS — all confirmed security findings fixed and tested; admissible for operator closure.)

## Dependencies

- No external wave dependencies.
