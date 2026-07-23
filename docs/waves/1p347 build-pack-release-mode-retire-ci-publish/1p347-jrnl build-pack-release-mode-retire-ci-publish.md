# Journal - Build Pack Release Mode Retire CI Publish

Owner: Engineering
Status: active
Last verified: 2026-06-03

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-06-03

wave-id: `1p347 build-pack-release-mode-retire-ci-publish`

## Operating Identity

- Role: wave-coordinator — coordinating a single-change wave that consolidates the release pipeline into `build_pack.py` and retires the CI publish workflow.
- Responsibilities include: preserve the bare `build_pack.py --version X.Y.Z` local-only behavior (operator-explicit requirement); ensure every pre-flight refusal mode is tested; dogfood the new `--release` flow by cutting v1.4.1 with it.

## Salience Triggers

- **High:** any change that alters bare `build_pack.py --version X.Y.Z` behavior — that's a backwards-compat break and blocks done.
- **High:** dogfood failure — if `build_pack.py --release` can't ship its own v1.4.1, the change is not implemented; synthetic tests are not sufficient evidence.
- **High:** partial-state errors during `--release` (tag pushed but release create failed) — recovery path must be in the error message, not just the docs.
- **Medium:** pre-flight refusal mode missing a test case — would let a release-time footgun slip past CI-of-CI.
- **Medium:** the deleted CI workflow leaves a discoverability gap (future contributor expects CI publish) — docs must call this out clearly.

## Distillation

- The CI publish workflow was always shipping a strictly worse artifact (no framework index) than the maintainer's local build. Replacing it with `build_pack.py --release` is the minimal-surface fix.
- Local-only behavior is a contract for non-pusher users and must be preserved verbatim. The `--release` flag layers on top, never replaces.
- Pre-flight gates are the wave's safety property: each refusal mode catches a class of release failure. They are tested individually.
- The verification of "the new release command works" is shipping v1.4.1 of this change via the command itself — dogfood, not synthetic.

## Active Signals

wave-id: `1p347 build-pack-release-mode-retire-ci-publish`

- Created 2026-06-03: one planned change, `1p349-enh build-pack-release-cli-with-optional-tag-and-publish`. Single-session refactor targeting 1.4.1.

## Promotion Evidence

- Stable artifact: `docs/waves/1p347 build-pack-release-mode-retire-ci-publish/wave.md`

## Retirement And Supersession

- Retires when the wave closes with `1p349` `implemented` and 1.4.1 is shipped via `build_pack.py --release` itself.

## Governance

- No secrets, credentials, or PII in journals.
- Framework script edits require the normal wave stage gate before implementation.
