# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-06-08

wave-id: `1p44n framework-1p6-hardening`
Title: Framework 1P6 Hardening

## Objective

The Aceiss/Teton team's 1.6.0 upgrade field report surfaced a cluster of real defects in the framework's new hardcoded-secrets scanner and the `wave_upgrade` flow. A 5-agent grounding pass confirmed 19 of them against current source (one — `docs/scan-findings.json` self-scan — was already fixed earlier this session). This wave hardens those surfaces — upgrade-failure data-safety + state tracking, scanner performance/precision/value-filtering, the confirmation-resolution workflow, and seed/doc routing gaps — led by the data-safety lock-deletion fix (`1p44o`). Closes when all 19 ship with tests.

## Changes

Change ID: `1p44o-bug upgrade-lock-survives-gate-failure`
Change Status: `planned`

Change ID: `1p44p-bug upgrade-from-version-and-version-sources`
Change Status: `planned`

Change ID: `1p44q-bug upgrade-prune-count-reporting`
Change Status: `planned`

Change ID: `1p44r-enh resumable-upgrade-after-gate-failure`
Change Status: `planned`

Change ID: `1p44s-enh secrets-scanner-file-guards`
Change Status: `planned`

Change ID: `1p44t-enh secrets-scanner-generated-artifact-allowlist`
Change Status: `planned`

Change ID: `1p44u-enh generic-api-key-docs-path-scope`
Change Status: `planned`

Change ID: `1p44v-enh secrets-finding-dedup-and-comment-context`
Change Status: `planned`

Change ID: `1p44w-enh secrets-jwt-expiry-awareness`
Change Status: `planned`

Change ID: `1p44x-enh secrets-redaction-short-secret-tightening`
Change Status: `planned`

Change ID: `1p452-doc scan-rules-cel-header-comment-fix`
Change Status: `planned`

Change ID: `1p44y-enh false-positive-confirmation-override`
Change Status: `planned`

Change ID: `1p44z-enh secrets-confirmation-bootstrap-ordering`
Change Status: `planned`

Change ID: `1p450-enh secrets-full-scan-baseline-at-install-upgrade`
Change Status: `planned`

Change ID: `1p451-enh secrets-gate-failure-messaging`
Change Status: `planned`

Change ID: `1p453-doc seed-160-secrets-resolution-routing`
Change Status: `planned`

Change ID: `1p454-doc upgrade-cleanup-next-steps-reconcile`
Change Status: `planned`

Change ID: `1p455-doc scan-findings-format-reference-doc`
Change Status: `planned`

Change ID: `1p456-bug engine-ignores-global-value-filter`
Change Status: `planned`

Change ID: `1p457-enh false-positive-confirmation-expiry`
Change Status: `planned`

Change ID: `1p45b-bug lifecycle-id-dedup-across-plans-waves-adrs`
Change Status: `planned`

## Wave Summary

21 changes across six clusters: **upgrade-state** (4 — data-safety lock-on-gate-failure, resumability, version/prune reporting), **scanner performance** (2 — engine file guards, generated-artifact allowlist), **scanner precision/correctness** (6 — generic-api-key docs scope, finding dedup, JWT expiry, redaction tightening, CEL header comment, and wiring the authored-but-inert global value-filter), **confirmation workflow** (5 — false-positive override, bootstrap ordering, full-scan baseline, messaging, and time-bounded confirmation expiry `1p457`), **seed/doc gaps** (3 — resolution routing, cleanup next-steps, scan-findings format doc), and **lifecycle tooling** (1 — `1p45b` ID-minting dedup across plans/waves/ADRs). The first five clusters are scanner/upgrade-layer fixes to the in-flight 1.6.0 code; `1p45b` is a separate lifecycle-ID correctness fix surfaced this session. The data-safety fix `1p44o` is implemented first. Runs in parallel with `1p41l` (graph-tools) — no cross-dependency.

## Journal Watchpoints

- **Implement-first (data-safety):** `1p44o` (lock-survives-gate-failure) is the released data-safety root cause and absorbs the dashboard-reindex + cleanup-summary downstreams — implement before the rest.
- **Blocking dependencies:** `1p44r` (resumable upgrade) is **blocked by** `1p44o` (the lock must survive for resume to read state); `1p451` (messaging) **depends on** `1p44y` (override — it describes the escape path); `1p456` (value-filter) must be sequenced with `1p452` (the header comment must reflect the now-applied `[allowlist].regexes`/`stopwords`); `1p450` (baseline) pairs with `1p44z` (materialize policy first, then baseline).
- **Shared-file serialization watchpoint:** coordinate edits within each shared file — `upgrade_wavefoundry.py` (`1p44o`/`1p44p`/`1p44q`/`1p44r`/`1p454`), `secrets_validators.py` (`1p44s`/`1p44v`/`1p44x`/`1p44y`/`1p451`/`1p456`/`1p457`), `scan-rules.toml` (`1p44t`/`1p44u`/`1p44w`/`1p452`/`1p456`/`1p457`), `seed 213` (`1p457`), `cel_filter.py` (`1p44u`/`1p44w`), seeds `160`/`012` (`1p450`/`1p453`/`1p455`), `server_impl.py` mint sites (`1p45b`, coordinated with the upgrade-flow `server_impl.py` edits), `lifecycle_id.py` (`1p45b`). Note: `1p457` and `1p44y`/`1p451` all touch the `secrets_validators.py` false-positive branch + message strings — keep `_unique_confirmation_count`'s `(count, names)` arity stable.
- **Post-prepare admission watchpoint:** `1p457` (confirmation-expiry) and `1p45b` (lifecycle-ID dedup) were admitted AFTER the prepare-council PASS recorded below (which reviewed 19 changes). They have NOT been through a readiness pass — run a targeted council / re-prepare on these two before implementing them.
- **Gate watchpoint:** seed edits require `seed_edit_allowed`; the `secrets_validators.py` / `scan-rules.toml` / `upgrade_wavefoundry.py` edits are framework-maintenance → `framework_edit_allowed`. Close each gate immediately after.
- **Invariant watchpoint:** do not regress the `scan-findings.json` self-exclusion (fixed this session) or the 2778-test baseline; `1p456` must preserve recall (its AC-4); scanner changes that touch the parallel path must plumb new state through the worker initializer (`1p456` AC-6).
- **Deferred follow-up:** executing the top-level betterleaks `prefilter`/`filter` CEL blocks directly is deliberately NOT in scope — `1p456` wires the `[allowlist]` mirror instead and `1p452` documents the contract; revisit only if a betterleaks re-download needs it.

## Review Evidence

- wave-council-readiness: approved 2026-06-08 — PASS WITH IN-SESSION FIXES (moderator: wave-council; depth: full; seats: red-team primer, security-reviewer, architecture-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: best-alternative [tier-the-implementation]; must-fix-count: 0; recommended-count: 1 applied in-session [R-1: security-visibility AC-9 on 1p44s — size/binary skips must be surfaced, never silent]; strongest-challenge: the scanner is a SECURITY CONTROL, so 1p44s file-guards (skip oversized/binary) and 1p456 global value-filter (suppress matches) are higher-stakes than typical — a wrong threshold or over-suppression yields a MISSED real secret (false-negative); plus 19 changes across heavily-shared files (secrets_validators.py ×6, upgrade_wavefoundry.py ×5) risk integration conflicts; strongest-alternative: implement in strict dependency tiers — land+verify data-safety 1p44o first, then perf, then precision/workflow/docs — rather than one parallel batch (incorporated via Journal Watchpoints implement-first + dependency notes); falsification: working verdict PASS; strongest counter is silent size/binary skips on a security control; does not change the verdict because thresholds are generous (real tokens are short), recall is guarded (1p456 AC-4, 1p44s AC-7), and R-1/AC-9 makes skips visible/auditable — net security posture improves; verdict: PASS — admissible for implementation, data-safety 1p44o first)
- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-08: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, security-reviewer, architecture-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: best-alternative; strongest-challenge: scanner-as-security-control — 1p44s guards + 1p456 value-filter can cause missed-secret false-negatives if mis-tuned; 19 changes across shared files (secrets_validators.py ×6, upgrade_wavefoundry.py ×5) need careful serialization; strongest-alternative: tiered dependency-ordered implementation with data-safety 1p44o landed+verified first (captured in Journal Watchpoints); security-reviewer: skip thresholds generous + recall guarded (1p456 AC-4, 1p44s AC-7), but size/binary skips were silent → added AC-9 (surface skipped files); architecture-reviewer: the 1p44o lock-schema change (failed_phase/failed_at) is additive/optional and must land first so 1p44r/1p454/dashboard build on the final schema; qa-reviewer: every change carries test ACs and the 2778-test baseline is an invariant watchpoint; docs-contract-reviewer: 1p452 header comment must reflect the post-1p456 applied value-filter (sequenced in watchpoints); reality-checker: all 19 are file:line-grounded confirmed defects, not speculative — the one report false-alarm (install-log-format.md exists) is captured not-applicable in 1p455; must-fix: 0; recommended applied in-session: R-1 security-visibility AC-9 on 1p44s)

## Dependencies

- No external wave dependencies.
