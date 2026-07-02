# Wave Record

Owner: Engineering
Status: implementing
Last verified: 2026-07-02

wave-id: `1p9gr socks-proxy-dependency`
Title: Setup Dependency And Code Index Defaults

## Objective

Harden first-time setup by adding default SOCKS proxy support to Wavefoundry's dependency manifests and by making `wf setup` build the code index alongside docs instead of treating semantic code embeddings as optional guidance.

## Changes

Change ID: `1p9gq-change socks-proxy-dependency`
Change Status: `implemented`

## Wave Summary

This wave updates the package and setup dependency lists for httpx SOCKS support, then corrects initial setup behavior/guidance so the code index is part of the normal setup path. Default setup treats docs and code the same by building both in the foreground; `--background-code` and `--background-docs` remain explicit fast-start options. It also fixes a setup accelerator fallback bug where CoreML could be re-enabled after the setup provider probe selected CPU.

## Journal Watchpoints

- Watchpoint: follow-up required if the dependency probe checks plain `httpx` instead of `socksio`; that would miss existing environments where httpx is present without SOCKS support.
- Watchpoint: default `wf setup` should complete docs and code indexes in the foreground; keep `--background-code` / `--background-docs` only as explicit one-layer-detached fast-start paths.
- Watchpoint: setup-selected CPU must stay authoritative for accelerator prewarm/index subprocesses; do not let raw ONNX Runtime provider availability re-enable CoreML unless the operator explicitly requested it.

## Review Evidence

- wave-council-readiness: approved 2026-07-02 — readiness pass for first-setup hardening. Scope covers `pyproject.toml`, `setup_index.REQUIRED_IMPORTS`, setup default code-index behavior, focused setup tests, and setup/index guidance. Strongest challenges: probing plain `httpx` would falsely pass in environments where httpx is present without SOCKS support; a default background code pass could make setup look complete while code search is still unavailable. Mitigations: probe `socksio`, build docs and code synchronously by default, and keep background layer flags as explicit fast-start tradeoffs. Ready to implement.
- provider-crash-fix: reproduced 2026-07-02 — setup selected `CPUExecutionProvider`, then accelerator prewarm independently re-enabled CoreML from raw ONNX Runtime availability and crashed in native CoreML code. Fixed by honoring `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED=CPUExecutionProvider` in accelerator GPU availability fallback while preserving explicit operator GPU requests.
- wave-council-delivery: approved 2026-07-02 — delivery review found one issue before commit: `--background-docs` built only code in the foreground but still prewarmed docs+code models in the parent process, violating the one-layer-detached contract. Fixed by making `_indexer_models` / `prewarm_models` layer-aware with `code_only`, updating scheduling tests, and rerunning full verification.
- operator-signoff: approved 2026-07-02 — operator requested review and commit if the reviewed wave was OK.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team; rotating-seat: none; strongest-challenge: first-setup hardening has two false-completion traps: probing plain `httpx` would miss missing SOCKS support, and foreground-only docs indexing can leave code search absent after the documented `wf setup`; strongest-alternative: keep docs-first setup as the default and only launch code in the background, rejected because it still treats code as incomplete at setup return; mitigation: map `httpx[socks]` to `socksio`, build docs and code synchronously by default, keep background layer flags as explicit fast-start options, and align setup guidance/tests with that contract.)
- **Delivery Wave Council [delivery-council] — 2026-07-02: PASS** (moderator: wave-council; primer-depth: focused; seats: red-team, qa; rotating-seat: reality-checker; strongest-challenge: background layer flags must not perform the detached layer's model work in the foreground, and setup-selected CPU must not be bypassed by accelerator raw-provider availability; mitigation: layer-aware prewarm selection, setup-selected CPU honored by `accel_embedder`, targeted scheduling/accelerator tests, production-style provider probe, and full framework suite.)

## Dependencies

- No external wave dependencies.
