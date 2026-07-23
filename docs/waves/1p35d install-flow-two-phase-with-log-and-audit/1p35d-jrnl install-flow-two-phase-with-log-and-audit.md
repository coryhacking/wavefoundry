# Journal - Install Flow Two-Phase With Log And Audit

Owner: Engineering
Status: active
Last verified: 2026-06-03

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-06-03

wave-id: `1p35d install-flow-two-phase-with-log-and-audit`

## Operating Identity

- Role: wave-coordinator — coordinating a six-change wave that restructures install around a markdown-native state machine (checkbox install log) and a single validating MCP tool (`wave_install_audit`).
- Responsibilities include: hold scope discipline (resist tempting late-admits even though six changes is already wide); ensure the install log is treated as the state machine, not a side artifact; preserve the Phase 1 MCP-free invariant; ensure lint-as-you-go discipline is wired into `wave_install_audit` (not optional, not skippable).

## Salience Triggers

- **High:** any C1 step that requires MCP — that breaks Phase 1's MCP-free invariant and means the install can't bootstrap from a fresh zip.
- **High:** a change that introduces a log-write path without a corresponding artifact-verify path in `wave_install_audit` — that's the install-completes-without-producing-artifacts root cause this wave exists to prevent.
- **High:** `wave_install_audit` short-circuits docs-lint or skips it when artifact-verification fails — lint must always run; both checks surface as diagnostics.
- **Medium:** the pycache hook removal slips out of C5 (kept in seed-080 spec when it shouldn't be) — the fix is the removal + the docs-lint exclusion, not the wiring.
- **Medium:** install-wavefoundry.md content drifts toward marketing prose instead of agent-readable bootstrap instructions — the filename matches the shortcut phrase to make it discoverable; the content must reward that.

## Distillation

- Install state machines hate distance between intent and verification. A pre-populated checkbox log keeps them adjacent: each row both names the step (intent) and points at the artifact whose presence verifies completion (verification).
- The Phase 1 / Phase 2 split is forced by MCP's bootstrap topology: Phase 1 brings MCP up, so Phase 1 can't depend on MCP. Phase 2 can use MCP freely because Phase 1 made it available.
- Pre-extraction discoverability is a different surface from in-zip artifacts. Mixing them in implementation produces files that try to serve both audiences and serve neither well.
- The pycache hook was a symptom-patch. Fixing the docs-lint exclusion is the root-cause fix. Removing the hook reduces surface area without losing functionality.

## Active Signals

wave-id: `1p35d install-flow-two-phase-with-log-and-audit`

- Created 2026-06-03: six planned changes targeting 1.5.0. Source: downstream consumer install retrospective spanning ~20 individual findings clustered around install-verification gaps.

## Promotion Evidence

- Stable artifact: `docs/waves/1p35d install-flow-two-phase-with-log-and-audit/wave.md`

## Retirement And Supersession

- Retires when the wave closes with all six changes `implemented` and 1.5.0 ships via `build_pack.py --release`.

## Governance

- No secrets, credentials, or PII in journals.
- Framework script edits require the normal wave stage gate before implementation.
