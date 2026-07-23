# Journal - Config-Key Back-Compat Hotfix

Owner: Engineering
Status: active
Last verified: 2026-06-03

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-06-03

wave-id: `1p337 config-key-back-compat-hotfix`

## Operating Identity

- Role: wave-coordinator — coordinating a single-change hotfix that closes a transition-state defect shipped in `1p2q3` (1.3.27–1.3.31) and propagated through `1p31b` (1.3.32).
- Responsibilities include: hold the bounded scope (resist admitting adjacent cross-cut audits); enforce the no-silent-break promise on existing consumer configs; verify the one-shot deprecation note fires only on legacy-key reads.

## Salience Triggers

- **High:** scope creep toward a broader cross-cut audit for other seed-vs-runtime drift surfaces. Bounded scope is what makes 1.3.33 shippable in a single session.
- **High:** a test failure on the legacy-key path during implementation — that's the no-silent-break promise breaking and blocks close.
- **Medium:** deprecation-note implementation fires on every process startup or on no-legacy-no-new paths. Both are noise patterns that dilute the signal.

## Distillation

- The bug was identified by a downstream-operator audit; their methodology (verify runtime behavior before applying renames) is the model for future upgrade audits.
- The fix is reader-side back-compat with new-key precedence. Forward migration is the right direction; back-compat is the gradual-migration affordance.
- Two sites need patching: `server_impl.py:1280` (`_read_wave_council_policy`) and `wave_lint_lib/constants.py:41` + `core_validators.py:190-211` (required-keys check).

## Active Signals

wave-id: `1p337 config-key-back-compat-hotfix`

- Created 2026-06-03: one planned change, `1p336-bug workflow-config-renamed-keys-missing-reader-back-compat`. Single-session hotfix targeting 1.3.33.

## Promotion Evidence

- Stable artifact: `docs/waves/1p337 config-key-back-compat-hotfix/wave.md`

## Retirement And Supersession

- Retires when the wave closes with `1p336` `implemented` and 1.3.33 is shipped.

## Governance

- No secrets, credentials, or PII in journals.
- Framework script edits require the normal wave stage gate before implementation.
