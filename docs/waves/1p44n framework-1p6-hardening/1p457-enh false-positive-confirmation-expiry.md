# Time-Bounded False-Positive Confirmations (Yearly Re-Verification)

Change ID: `1p457-enh false-positive-confirmation-expiry`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

A `false-positive` secrets finding is suppressed once it accumulates `false_positive_confirmations_required` (default 2) confirmations from distinct reviewers. Confirmations already record a `confirmed_at` UTC ISO-8601 timestamp (seed-213 write-back; see fixtures in `test_secrets_validators.py:359-365`), but **nothing consumes that timestamp**. `_unique_confirmation_count` (`secrets_validators.py:388-398`) counts every distinct `git_user_email` regardless of age, so a sign-off from years ago still suppresses the finding forever.

That is the wrong default for a security gate. A line classified as a false positive in 2024 may have changed meaning, and the reviewers who vouched for it may be long gone. The confirmation should age out: after a configurable window (default one year) a stale confirmation stops counting, the finding drops back below threshold, and the gate re-prompts for a fresh, dated sign-off. The timestamp is already captured — this change makes it load-bearing.

This is the natural follow-on to the gate's existing distinct-reviewer logic: the threshold stays at its policy value, the same person is never re-asked while their confirmation is still valid, but the wall clock now participates so confirmations are renewed rather than permanent.

## Requirements

1. A new `[policy]` key `confirmation_valid_days` (default `365`) controls the maximum age, in days, of a confirmation that still counts toward `false_positive_confirmations_required`. It is shipped in `.wavefoundry/framework/scan-rules.toml` `[policy]` (alongside `false_positive_confirmations_required` at `:93-94`) and overridable per-project in `docs/scan-rules.toml` `[policy]` via the existing `load_merged_ruleset` merge.
2. When counting confirmations for a `false-positive` finding, a confirmation counts only if its `confirmed_at` parses as a UTC datetime AND is no older than `confirmation_valid_days` relative to the scan's "now". Stale confirmations are ignored for counting but are **left in place** in `confirmations[]` (history is preserved, never mutated or pruned by this change).
3. A confirmation whose `confirmed_at` is missing, empty, or unparseable is treated as expired (fail-closed), forcing a fresh dated confirmation rather than silently counting.
4. The expiry clock is **per-confirmation** (each entry ages from its own `confirmed_at`), so re-verification across findings is naturally staggered rather than a single shared annual epoch.
5. When a previously-suppressed finding re-opens because confirmations expired, the gate failure message must make the cause explicit (e.g. report how many confirmations expired and that re-verification is needed), distinct from the "never confirmed" wording.
6. `confirmation_valid_days = 0` (or absent/non-positive) means "no expiry" — confirmations never age out — so the feature is opt-out and existing repos can pin the old behavior.
7. `_unique_confirmation_count`'s public return shape `(count, names)` must be preserved so the parallel change `1p44y` (which reads it and edits the same false-positive branch) is not clobbered; expiry filtering happens inside it (plus a separate helper for the expired-count message detail).

## Scope

**Problem statement:** Confirmations record `confirmed_at` but the counter (`secrets_validators.py:388-398`) ignores it, so a `false-positive` suppression is permanent. There is no re-verification path; a years-old sign-off keeps a finding green indefinitely.

**In scope:**

- New `confirmation_valid_days` policy key (framework default 365, project-overridable) wired through `load_merged_ruleset` → `check_hardcoded_secrets` → `_match_hits_for_file` → the false-positive branch.
- Age-filtering in `_unique_confirmation_count` (drop confirmations older than the window / with unparseable `confirmed_at`), with the count/names arity preserved.
- A small expired-count helper used only for the failure-message detail.
- An "as-of now" reference (`datetime.now(timezone.utc)`, the imports already exist at `secrets_validators.py:8`) threaded down so tests can inject a fixed reference time.
- Failure-message wording on the false-positive branch (`secrets_validators.py:636-653`) noting expired confirmations, coordinated with `1p451` and `1p44y` which touch the same strings.
- Seed-213 documentation of expiry, the operator prompt showing each confirmation's age, and "re-confirming appends a NEW dated entry (never mutate the old one)."
- `docs/SECURITY.md` and `docs/specs/mcp-tool-surface.md` notes that confirmations are time-bounded.
- Unit tests in `test_secrets_validators.py` and policy-plumbing tests in `test_scan_secrets.py`.

**Out of scope:**

- The reviewer-count clamp and `override_reason` dismissal (owned by `1p44y`); this change composes with them (expiry lowers the effective count, the clamp lowers the threshold, the override bypasses both) but does not implement them.
- Pruning or rewriting stale `confirmations[]` entries — history is retained.
- A global/shared annual re-verification epoch (explicitly per-confirmation; see Decision Log).
- Changing the dedupe semantics of the non-false-positive status branches.
- Any installer change to the default `confirmation_valid_days` based on team size.

## Acceptance Criteria

- [x] AC-1: With `confirmation_valid_days = 365`, a `false-positive` finding whose only confirmations are all older than 365 days is NOT suppressed — it fails the gate and re-prompts. — `test_all_expired_not_suppressed`.
- [x] AC-2: A finding with a mix of fresh and expired confirmations counts only the fresh ones; below threshold fails, at/above suppressed. — `test_mixed_fresh_and_expired_counts_fresh_only`, `test_two_fresh_confirmations_suppress`.
- [x] AC-3: A confirmation with a missing/empty/unparseable `confirmed_at` does not count (treated as expired). — `_parse_confirmed_at` returns None → dropped. `test_unparseable_confirmed_at_not_counted`.
- [x] AC-4: Expired confirmations remain present in `confirmations[]` after a scan (no mutation/pruning); only their count contribution changes. — `test_expired_confirmations_left_in_place`.
- [x] AC-5: `confirmation_valid_days` read from merged policy — project override changes the window; `0`/absent/non-positive disables expiry. — `max(0, int(policy.get("confirmation_valid_days", 365)))`. `test_project_override_window`, `test_zero_days_disables_expiry`.
- [x] AC-6: When a finding re-opens due to expiry, its gate-failure message distinctly indicates expired confirmations / re-verification needed. — `_expired_confirmation_count` + `_expiry_note` ("N prior confirmation(s) EXPIRED…"). `test_expiry_message_is_distinct`.
- [x] AC-7: `_unique_confirmation_count` still returns `(count, names)`. — new params are keyword-optional; `test_unique_confirmation_count_arity_preserved` + `1p44y` tests still green.
- [x] AC-8: Regression — existing `test_secrets_validators.py` fixtures still pass and `run_tests.py` is green. — full suite 2863 green; `_run_check` now defaults to a fixed `_FIXED_AS_OF` so the dated fixtures are wall-clock-independent.
- [x] AC-9: New tests cover AC-1..AC-5 with an injected fixed "as-of" time plus the policy-merge override. — `TestConfirmationExpiry` (9 tests).
- [x] AC-10: Seed-213 documents the expiry rule, age display in the operator prompt, and the append-new-entry-on-re-confirm contract. — added; SECURITY.md + mcp-tool-surface.md also note time-bounded confirmations.

## Tasks

- [x] Add `confirmation_valid_days = 365` to `.wavefoundry/framework/scan-rules.toml` `[policy]` with a header comment explaining yearly re-verification and the `0 = no expiry` opt-out.
- [x] In `check_hardcoded_secrets` (`secrets_validators.py:676+`), read `confirmation_valid_days` from merged `policy` (next to `:699`) and capture an `as_of = datetime.now(timezone.utc)` reference; thread both through `_match_hits_for_file`.
- [x] Extend `_match_hits_for_file` signature (`:561-570`) to accept `confirmation_valid_days` and `as_of`, passing them into the count call on the false-positive branch (`:631-653`).
- [x] Add age filtering inside `_unique_confirmation_count` (`:388-398`): parse `confirmed_at` (ISO-8601, trailing `Z` → `+00:00`), skip entries that fail to parse or exceed the window; preserve the `(count, names)` return. Accept `as_of`/`valid_days` as parameters (defaulting to no-expiry when `valid_days` is falsy).
- [x] Add a small `_expired_confirmation_count(entry, as_of, valid_days)` helper for the message detail only.
- [x] Update the false-positive failure-message strings to surface expired-confirmation count; reconcile wording with `1p451` and `1p44y` (shared strings).
- [x] Update seed-213 (`.wavefoundry/framework/seeds/213-security-reviewer.prompt.md:31-53`): expiry rule, per-confirmation age in the operator prompt, append-new-dated-entry on re-confirm.
- [x] Note time-bounded confirmations in `docs/SECURITY.md` and `docs/specs/mcp-tool-surface.md`.
- [x] Add unit tests (AC-1..AC-5, AC-9) with an injected reference time; add policy-plumbing coverage in `test_scan_secrets.py`.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`; run `.wavefoundry/bin/docs-lint` on this plan.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| policy-key | Engineering | — | Add `confirmation_valid_days` to framework `scan-rules.toml` `[policy]`; confirm merge via `load_merged_ruleset`. |
| count-expiry | Engineering | policy-key | Age filter in `_unique_confirmation_count` + `_expired_confirmation_count` helper; thread `as_of`/`valid_days` from `check_hardcoded_secrets` through `_match_hits_for_file`. |
| messaging | Engineering | count-expiry | Expired-confirmation failure wording; reconcile with `1p451`/`1p44y`. |
| seed-and-docs | Engineering | count-expiry | Seed-213 expiry rule + age display + append-new-entry contract; SECURITY.md / mcp-tool-surface.md notes. |
| tests | Engineering | count-expiry | Injected-time unit tests (AC-1..AC-5, AC-9) + policy plumbing; full suite green. |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` — shared with `1p44s`, `1p44v`, `1p44x`, `1p451`, and especially `1p44y`. This change and `1p44y` both edit `_unique_confirmation_count` and the false-positive branch (`:631-653`); keep `_unique_confirmation_count`'s `(count, names)` return shape so they compose. The false-positive failure-message strings overlap with `1p451` and `1p44y` — sequence message edits and reconcile expected strings.
- Confirmation entry schema (`confirmed_at`, `git_user_email`, `git_user_name`, `verdict`, `reason`) — read-only contract shared with seed-213 write-back; do not rename fields.

## Affected Architecture Docs

N/A — the change is confined to the secrets-gate validator module (`secrets_validators.py`), its policy file, and the security-reviewer seed/docs. It adds a policy knob and a time filter to existing counting logic; no new module boundary, data flow, or verification surface is introduced.

## AC Priority

(Provisional — revisited at Prepare wave.)


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Core behavior — expired confirmations stop suppressing. |
| AC-2 | required   | Mixed fresh/expired counting is the common steady-state case. |
| AC-3 | required   | Fail-closed on bad timestamps; security-relevant. |
| AC-4 | required   | History preservation — the chosen non-destructive semantics. |
| AC-5 | required   | Configurability + opt-out for existing repos. |
| AC-6 | important  | Actionable re-verification messaging. |
| AC-7 | required   | Prevents clobbering parallel change 1p44y. |
| AC-8 | required   | Regression safety. |
| AC-9 | required   | Deterministic tests via injected time. |
| AC-10 | important | Reviewer guidance must match the new behavior. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | DELIVERY-REVIEW NOTE: the readiness 'confirmation_valid_days policy-merge test' lives in TestConfirmationExpiry (test_project_override_window / test_zero_days_disables_expiry), not test_scan_secrets.py — AC-5/AC-9 fully covered with deterministic injected as_of. | — |
| 2026-06-08 | Added `confirmation_valid_days` (`[policy]`, default 365); `_parse_confirmed_at` + age-filtering in `_unique_confirmation_count` (arity preserved) + `_expired_confirmation_count`; threaded `confirmation_valid_days`/`as_of` through `check_hardcoded_secrets`→`_match_hits_for_file`; distinct EXPIRED message note. seed-213 + SECURITY.md + mcp-tool-surface.md documented expiry. Readiness fixes applied: `_run_check` defaults to a fixed `as_of` (all FP-branch tests deterministic); seed-213 names `confirmed_at` + append-on-re-confirm; policy-merge override tests added. | `secrets_validators.py`, `scan-rules.toml`, seed-213, SECURITY.md, mcp-tool-surface.md; `TestConfirmationExpiry` (9 tests); full suite 2863 green. |
| 2026-06-08 | **FIELD-NAME ROOT CAUSE + OPERATOR DECISION (field test).** Real-project p49k testing showed every prior false-positive confirmation silently "expired": 1p457 renamed the confirmation timestamp field `datetime` → `confirmed_at` (writer seed-213 + reader + doc + tests), but the one project that had scanned under the never-distributed p3zo build still held `datetime`-keyed confirmations the new reader couldn't see (fail-closed → expired). Root-caused via git (HEAD `_unique_confirmation_count(entry)` read no timestamp; `confirmed_at` exists only in this uncommitted wave). Operator confirmed only that single local project used `datetime` and migrated it to `confirmed_at`, so **no back-compat is carried** — reader reads `confirmed_at` only (clean canonical). Kept the prevention: seed-213 now names the field `confirmed_at` explicitly at both write sites — the prior "ISO-8601 datetime" phrasing with no field name is what led the old prompt to write the `datetime` key. | `secrets_validators.py` reads `confirmed_at` only; seed-213 write sites name `confirmed_at`; full suite **2905 green**; docs-lint ok. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Expired confirmations are ignored for counting but retained in `confirmations[]` (non-destructive). | Preserves the audit trail of who previously vouched and when; re-confirming appends a new dated entry alongside the old. | Prune stale entries on re-scan (loses history). |
| 2026-06-08 | Default `confirmation_valid_days = 365`, configurable per-project; `0`/absent = no expiry. | Matches the "re-verify yearly" intent while letting existing repos opt out and small/large teams tune the window. | Hardcoded TTL (not tunable); no-expiry-by-default opt-in (no yearly re-verification unless each project opts in). |
| 2026-06-08 | Per-confirmation clock (age from each entry's own `confirmed_at`), not a shared annual epoch. | Re-verification staggers naturally per finding instead of a once-a-year flood; matches the gate's existing per-finding model. | Single shared expiry epoch (synchronized annual re-verification of everything at once). |
| 2026-06-08 | Missing/unparseable `confirmed_at` is treated as expired (fail-closed). | A confirmation with no provable date cannot be trusted to be within the window; forces a fresh dated sign-off. | Treat undated confirmations as never-expiring (fail-open — weakens the gate). |
| 2026-06-08 | Keep `_unique_confirmation_count` returning `(count, names)`; filter age inside it. | The parallel change `1p44y` reads this arity and edits the same branch; preserving it avoids a clobber. | Change return arity to include expired count (breaks 1p44y). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Message-string edits collide with `1p451` / `1p44y` on the same false-positive branch. | Serialization point + sequence message edits after the count change; reconcile expected strings across the three changes. |
| Tests bound to real wall-clock become flaky as fixtures age past 365 days. | AC-9: inject a fixed `as_of` reference into the count path; never rely on `datetime.now()` in assertions. |
| `confirmed_at` formats drift (e.g. offset vs `Z`, fractional seconds) and parse inconsistently. | Normalize trailing `Z`→`+00:00`, accept timezone-aware ISO-8601; on any parse failure fall back to "expired" (AC-3) rather than crash. |
| Operators surprised when a long-green finding re-opens. | AC-6 distinct re-verification message + seed-213 guidance explaining the expiry window and how to re-confirm. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
