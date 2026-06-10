# Secrets Scanner — RE2→Python Regex Compatibility (26 Detectors Silently Dead)

Change ID: `1p4d1-bug secrets-scanner-re2-python-regex-compat`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

The scan ruleset is Gitleaks-schema, written for Go's RE2 engine. **26 of the 279 rule regexes use RE2 syntax that Python's `re` rejects**, so they fail `re.compile` — and the compile loop swallows the failure (`except re.error: continue` in `secrets_validators.py`). Those 26 rules therefore **never run**, and their secret types are **silently undetected**:

- **~22**: an inline `(?i)` flag placed *mid-pattern* ("global flags not at the start of the expression"). RE2 allows a flag anywhere (scoped to the enclosing group); Python requires global flags at position 0.
- **~4**: the `\z` end-of-text anchor ("bad escape `\z`"). Python spells it `\Z`.

Affected detectors include `adobe-client-secret`, `sendgrid-api-token`, `slack-session-cookie`, `sentry-org-token`, `planetscale-*`, `postman-api-token`, `linear-api-key`, `doppler/dynatrace/easypost/flutterwave/frameio/duffel`, `gocardless-api-token`, `facebook-page-access-token`, `alibaba-access-key-id`, `authress-*`, `curl-auth-header/user`, `intra42-client-secret`, `sendinblue-api-token`, `openshift-user-token`.

Surfaced during `1p44n` close-readiness: an operator question ("do all the regexes compile?") prompted a full compile check. This is **pre-existing** (the ruleset never compiled fully under Python), not a regression of this wave — but it is squarely a "secrets-scanner hardening" defect, so it's fixed here. It also explains why `1p4a2`'s coarse `rules_degraded` was permanently True (the 26 always fail) — this fix restores a clean ruleset so the `1p4a2` prune is actually active in production.

## Requirements

1. Every shipped framework rule regex MUST compile under Python `re`, so every rule actually runs.
2. The ruleset MUST stay in Gitleaks/RE2 schema (do **not** rewrite the `.toml` patterns to Python-specific syntax). Adapt at load via a translation shim so future Gitleaks imports work without per-rule porting.
3. The translation MUST be faithful: relocate RE2 inline flags to Python **scoped** groups preserving the original flag SCOPE (a `(?i)` inside a group affects only that group — a case-sensitive token prefix stays case-sensitive), and map `\z`→`\Z`. No charset or structural changes.
4. The shim MUST be a strict NO-OP on patterns that already compile (translate only the ones that fail).
5. A genuinely-malformed regex (not an RE2-ism) MUST still fail to compile and be skipped (and handled by `1p4a2`'s fail-closed prune guard) — never masked.

## Scope

**Problem statement:** 26 Gitleaks rule regexes use RE2-only syntax (`(?i)` mid-pattern, `\z`) that Python's `re` can't compile, so those detectors are silently dead and their secret types go undetected.

**In scope:**

- A `_re2_to_re` translation shim in `secrets_validators.py`: scope-preserving `(?i)`→`(?i:…)` (wrap to the enclosing group's close) and `\z`→`\Z`, applied in the compile loop **only when the original fails to compile**.
- Tests: all framework regexes compile; idempotence on valid patterns; faithful transforms (prefix case-sensitivity preserved); representative-token detection for previously-dead rules; genuinely-broken regex still skipped.

**Out of scope:**

- Editing the `.toml` rule patterns (the shim keeps them Gitleaks-schema).
- The top-level betterleaks `prefilter`/`filter` CEL blocks (separate, deferred per `1p452`/`1p456`).
- RE2 constructs not present in the ruleset.

## Acceptance Criteria

- [x] AC-1: Every regex in `.wavefoundry/framework/scan-rules.toml` compiles under Python `re` after translation (0 failures). — `test_all_framework_rules_compile` (279/279 compile; was 26 failing).
- [x] AC-2: The shim is a strict no-op on patterns that already compile (translate only on `re.error`; the 253 valid patterns are never touched). — `test_shim_translates_only_on_failure`.
- [x] AC-3: The translation is scope-faithful — a case-sensitive token prefix stays case-sensitive (`p8e-` rejects `P8E-`) while the CI token charset is honored; `authress`'s existing `(?-i:acc)` is preserved. — `test_shim_preserves_prefix_case_sensitivity`.
- [x] AC-4: A representative token for previously-dead rule classes now produces a match. — `test_previously_dead_rules_now_detect` (adobe / sendgrid / slack-session-cookie / gocardless).
- [x] AC-5: A genuinely-malformed regex still fails to compile (shim does not mask it) and is skipped. — `test_genuinely_malformed_regex_still_skipped`.
- [x] AC-6 (regression): full framework suite green (2928); `docs-lint` clean.

## Tasks

- [x] Add `_re2_to_re` + helpers (`_translate_end_anchor`, `_scope_inline_flags`, `_enclosing_group_close`, `_in_char_class`, `_is_escaped`) to `secrets_validators.py`.
- [x] Wire into the compile loop: on `re.error`, retry `re.compile(_re2_to_re(pattern_str))`; only mark `rules_degraded` / skip if the translated form also fails. (Worker path inherits the translated `pattern.pattern`, so no second wiring needed.)
- [x] Add unit + integration tests (AC-1…AC-5) — `TestRe2PythonRegexCompat` (5 tests).
- [x] Run the full suite + `wave_validate`; mark ACs and flip Change Status to `complete`.
- [x] Rewrite the `scan-rules.toml` header to reflect that the ruleset is now wavefoundry's own (adapted from betterleaks, not a verbatim copy) and document every local divergence — the RE2→Python shim, the CEL execution model, the `[policy]` section, the `[allowlist]` value-filter / self-exclusion / generated-artifact paths, the generic-api-key docs-prose clause, and the jwt expiry clause — with re-apply notes for the next upstream re-download. (Operator request; the shim is what crystallized the provenance shift.)

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| shim | Engineering | — | `_re2_to_re` + helpers in `secrets_validators.py` |
| wire | Engineering | shim | translate-on-failure in the compile loop |
| tests | Engineering | wire | all-compile / idempotence / faithfulness / detection / malformed |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` — the compile loop in `check_hardcoded_secrets`; additive (a translate-retry on `re.error`), shared with `1p4a2`'s `rules_degraded` logic in the same loop.

## Affected Architecture Docs

N/A — confined to the secrets-validator module's regex-compile path; no boundary/flow/verification-architecture change.

## AC Priority


| AC   | Priority   | Rationale                                                                |
| ---- | ---------- | ------------------------------------------------------------------------ |
| AC-1 | required   | The core fix — every detector must actually compile and run.             |
| AC-2 | required   | No-op on valid patterns — zero churn/risk on the 253 working rules.      |
| AC-3 | required   | Faithfulness — wrong-scope translation would broaden and add false positives. |
| AC-4 | required   | Proves the previously-dead detectors now fire end-to-end.                |
| AC-5 | important  | A real malformed rule must not be silently masked by the shim.           |
| AC-6 | required   | Suite + lint green is the regression gate.                               |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-09 | Found during close-readiness: 26/279 framework regexes fail Python `re.compile` (mid-pattern `(?i)`, `\z`) → silently dead detectors. Prototyped a scope-preserving RE2→Python shim and proved it against all 280: `fail_after=0`, idempotent on valid patterns (0 touched), faithful (adobe/alibaba prefixes reject wrong-case; authress `(?-i:acc)` preserved; representative tokens match). | `/tmp/re2shim.py` prototype run; before/after diff of the 26. |
| 2026-06-09 | Implemented `_re2_to_re` + helpers in `secrets_validators.py`; wired translate-on-`re.error` into the `check_hardcoded_secrets` compile loop. Verified via the scanner path: 279/279 rules compile (`rules_degraded=NO`), previously-dead `sendgrid` (a `(?i)` case) and `slack-session-cookie` (a `\z` case) now detect their tokens. | `TestRe2PythonRegexCompat` (5 tests); full suite **2928 green**; `wave_validate` → `docs-lint: ok`. |
| 2026-06-09 | **Adversarial faithfulness review (3-lens, Go RE2 oracle) caught one MAJOR — a fail-OPEN narrowing.** `curl-auth-header` has a `(?i)` in EACH branch of a `"…"|'…'` alternation sharing one group; `_enclosing_group_close` wrapped the first `(?i)` past the `|` to the outer group close, swallowing the bar and killing the single-quote branch (100% of single-quoted curl secrets missed; 124/300 oracle-sampled). Fixed: `_enclosing_group_close` now also stops at a same-depth `|`, so a scoped `(?…:…)` group never crosses an alternation bar. Verified: all compile; curl double- AND single-quote (Bearer/X-Api-Key) branches match; other 25 unchanged. The other 2 lenses (scoping edge cases, integration/FP) PASS clean. | `_enclosing_group_close` `|`-stop; `test_alternation_scoped_flag_does_not_kill_branch` + `test_scoped_flag_never_crosses_alternation_bar`; full suite **2930 green**; docs-lint ok. |
| 2026-06-09 | **Rewrote the `scan-rules.toml` header (operator request).** The ruleset is no longer a verbatim betterleaks copy — reframed as wavefoundry's own (adapted from betterleaks/Gitleaks), dropped the now-false "auto-generated / default betterleaks config" verbatim block, retitled it, and added a full divergence record so future re-downloads know what to re-apply: the RE2→Python shim (+ when to extend it), the CEL execution model, and the local `[policy]` / `[allowlist]` value-filter + self-exclusion + generated-artifact paths / generic-api-key docs-prose / jwt-expiry additions (each tagged with its wave change ID). Enumerated via a 3-lens divergence audit. | TOML parses; title updated; 280/280 rules still compile; full suite **2930 green**. |


## Decision Log


| Date       | Decision                                                                       | Reason                                                                                                                                                                | Alternatives                                                                                                              |
| ---------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 2026-06-09 | Adapt at load via a translation shim; keep the `.toml` patterns Gitleaks/RE2-schema. | One tested function vs 26 hand-edits; future Gitleaks imports work without re-porting; the ruleset stays consistent with its documented Gitleaks-schema origin. | Rewrite the 26 patterns to Python syntax (rejected: re-breaks on next import, 26 error-prone hand-edits).                 |
| 2026-06-09 | Scope-preserving `(?i:…)` wrap (to the enclosing group's close), not whole-pattern `re.IGNORECASE`. | Keeps case-sensitive vendor prefixes (`p8e-`, `LTAI`, `SG.`) exact — avoids prefix false-positives; matches RE2's actual flag scope. | Whole-pattern `IGNORECASE` (rejected: broadens prefixes → FPs); move `(?i)` to position 0 (rejected: same broadening).   |
| 2026-06-09 | Translate only on compile failure (no-op on valid patterns).                     | Idempotent; zero churn on the 253 already-valid rules; minimal surface; a genuinely-malformed rule still surfaces as a real failure. | Translate every pattern (rejected: rewrote 153 valid patterns unnecessarily — non-idempotent, added risk).               |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A faithful-port edge case subtly changes a pattern's match set. | The transform is minimal (flag relocation to scoped group + `\z`→`\Z`), proven to compile for all 280, strictly idempotent on valid patterns, and faithfulness is spot-checked (prefix case-sensitivity rejects wrong-case; representative tokens match; `authress`'s `(?-i:acc)` preserved). |
| The 26 now-active detectors add false positives on real repos. | These are standard Gitleaks vendor-prefixed token rules (high-signal, anchored prefixes); the global value-filter / allowlists and the confirmation workflow absorb residual noise; net detection strictly improves — real secrets of these 26 types were previously **missed**. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
