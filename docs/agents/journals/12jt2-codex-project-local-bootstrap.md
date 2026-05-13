# Journal — Codex Project-Local Bootstrap

Owner: Engineering
Status: active
Last verified: 2026-05-12

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-05-12

## Operating Identity

- Role: wave-coordinator — coordinating the Codex bootstrap wave so each Wavefoundry repo can register its own MCP server entry.
- Responsibilities include: preserving the project-local launch path, keeping the server naming deterministic, and sequencing the prepare/implement lifecycle.

## Salience Triggers

- **High:** Codex naming drifts from the checkout path — the launcher must preserve `wavefoundry-<hash>` for every checkout, with the hash stable for that folder path.
- **Medium:** The repo-local bootstrap path regresses to a manual doc-only instruction — the launcher is intended to be runnable, not just described.

## Distillation

- **Project-local launchers beat ad hoc instructions:** the repository should own the startup command even when the Codex attachment file remains global.
- **Checkout-path naming is special-cased:** every repository should derive a hash-suffixed name from the absolute checkout path, and the label should change when the repo is moved or recloned.

## Active Signals

wave-id: `12jt2 codex-project-local-bootstrap`

- Bootstrap launcher and docs are being prepared for implementation.

## Promotion Evidence

- Stable artifact: `docs/waves/12jt2 codex-project-local-bootstrap/wave.md`

## Retirement And Supersession

- None yet.

## Governance

- No secrets, credentials, or PII in journals.
- Keep the launcher deterministic and idempotent so repeated install runs do not create config churn.
