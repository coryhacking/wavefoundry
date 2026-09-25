# Readiness Review: 1yzcz setup-readiness-at-session-start

Owner: Engineering
Status: active
Last verified: 2026-09-24

## Round 1 (full review)

Receipt `review-policy-ea4f21d9826f92d7a8ef`. Three independent contexts: red-team (fixed council seat); docs-contract (rotating seat) with architecture; code, QA, security and release.

Blocking findings, each confirmed against the tree by more than one lane:

- READY-SELECTED-ENV (red-team RT-READY-1, code CODE-READY-1, release REL-READY-1, architecture ARCH-READY-1, docs DOCS-READY-1): ordinary setup sets `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED` in its own process (`setup_index.report_embedding_provider_decision`) before `write_setup_stamp`, so every setup-written stamp mismatches every fresh checker. Live in 1.25.0 and 1.26.0; reproduced by the code lane on the `SetupReadinessTests` fixture. The plan's projection kept the variable compared and its probe claim was false.
- READY-HOOK-ACTIVATION (red-team RT-READY-2, code CODE-READY-2, architecture ARCH-READY-2): composing the hook through `compose_script` runs `HOOK_BOOTSTRAP`, which activates the tool environment (executing `.pth` files, writing bytecode) and can `sys.exit(2)` past its `except Exception`, contradicting the `1y3og` pre-activation contract and "always exit 0".
- READY-UPGRADE-SITE (architecture ARCH-READY-3): the upgrade refresh site was unspecified; only `phase_cleanup` in the standalone `--cleanup` process, after the upgrade lock is removed, can assess ready.

QA and security approved. Non-blocking findings folded into the same repair: `timeout` on the command object, inputs-changed retry, action-specific notes, output sanitizing, identity-guarded and create-only adoption in `server.main`, subprocess-ready fixture, docs census (spec, seeds 050/160, prompt mirror, layering rules, docstring), AGENTS parity test, `1y3hc` supersession, changelog operator notes, first-pull adoption risk.

## Repair (one bounded pass)

Both change docs rewritten from Requirements through Risks; see their Progress Log rows dated 2026-09-24.

## Round 2 (focused verification by the blocking lanes)

Receipt `review-policy-f1e3774b36df5d2af674`. Code, QA, security, release and architecture approve; every round-1 finding resolved. Red-team (RT-READY-10) and docs-contract (DOCS-READY-6) each found one AC wording contradiction: 1yzcx AC-3 listed the Python version mismatch among one-line failure paths although `assess_setup` reports it as `action_required`, which Requirement 4 renders as a block. One-clause fix applied with the lanes' non-blocking notes (ValueError catch in adoption, hard-link filesystem risk, activation wording, parseable body syntax, fixture dependency census and `WAVEFOUNDRY_TOOL_VENV`, recovery fixture interpreter, byte-identity boundary). Confirmation of the clause requested from the two seats.
