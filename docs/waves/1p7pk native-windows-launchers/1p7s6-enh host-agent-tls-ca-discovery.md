# Host-agent CA-bundle env vars in the model-fetch TLS trust-store discovery

Change ID: `1p7s6-enh host-agent-tls-ca-discovery`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-06-25
Wave: `1p7pk native-windows-launchers`

## Rationale

The `1p7iu` TLS fallback (shipped in 1.8.x) recovers a model download that fails `CERTIFICATE_VERIFY_FAILED` behind a corporate TLS-inspecting proxy: `_os_trust_store_bundle()` in `setup_index.py` resolves a CA bundle from `SSL_CERT_FILE` → `REQUESTS_CA_BUNDLE` → platform OS-trust-store locations, then retries once with verification still ON.

But the **host coding agents** that run Wavefoundry expose their *own* CA-bundle env vars for exactly these environments, and `_os_trust_store_bundle` ignores them:

- **`CODEX_CA_CERTIFICATE`** (Codex) — "Points to a PEM CA bundle for environments with corporate TLS interception or private root CAs. **Takes precedence over `SSL_CERT_FILE`**."
- **`CLAUDE_CODE_CERT_STORE`** (Claude Code) — the CA bundle Claude Code itself uses.

When the host sets one of these, it is the **authoritative** bundle for that environment — the host already solved CA discovery for its own HTTPS/login/WebSocket clients. Two gaps follow from ignoring them:

1. **Missed resolution.** If a Codex/Claude Code user is behind a corporate proxy and has only the host var set (not `SSL_CERT_FILE`), `_os_trust_store_bundle` returns the platform guess or `None` — even though the correct bundle was sitting in `CODEX_CA_CERTIFICATE`.
2. **Wasted failed attempt.** The fallback is purely reactive (try certifi → fail → retry). When the host has *already declared* the right bundle, the first fetch is a guaranteed-to-fail round-trip before recovery.

This change teaches `_os_trust_store_bundle` the host-agent vars (with Codex's stated precedence) and uses them **proactively** when set, so the download succeeds on the first try.

## Requirements

1. `_os_trust_store_bundle()` resolution order prepends the host-agent vars ahead of the generic ones: `CODEX_CA_CERTIFICATE` → `CLAUDE_CODE_CERT_STORE` → `SSL_CERT_FILE` → `REQUESTS_CA_BUNDLE` → platform OS-trust-store locations. First entry pointing at an existing file wins. (Order honors Codex's "takes precedence over `SSL_CERT_FILE`".)
2. **Proactive use.** When a host-agent CA var points at a real file, configure the trusted CA bundle from it **before** the first model-fetch attempt — a set host-agent var implies a TLS-intercepting environment where the default certifi bundle fails anyway, so the proactive path removes the wasted failed first attempt. **Precedence reconciliation (security finding):** the candidate ORDER follows Requirement 1 (host-agent vars ahead of `SSL_CERT_FILE`, honoring Codex's stated precedence), but a set `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` is **never silently discarded** — it stays a candidate later in the chain, and any per-attempt env mutation is scoped/restored so the operator's original settings survive. Precedence only changes try-order; iteration (Req 5) means a non-winning candidate just costs one extra attempt, not a wrong result.
3. **Secure by construction.** No code path disables verification or sets an insecure context; this only selects WHICH trusted CA bundle to verify against. The existing `test_no_path_disables_tls_verification` guard must continue to hold.
4. The `CERTIFICATE_VERIFY_FAILED` remediation message names the host-agent vars (`CODEX_CA_CERTIFICATE` / `CLAUDE_CODE_CERT_STORE`) alongside `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`.
5. **Candidate iteration, certifi-default last (red-team finding).** The trust-store resolution exposes the result as an **ordered candidate list**, and the model-fetch retry tries candidates in order — host-agent vars → operator vars → platform locations → **the certifi default as the final fallback** — so a host-agent bundle that *itself* fails cert-verify degrades to the next candidate instead of hard-failing via today's single-bundle `already_tried` short-circuit. Because the proactive path (Req 2) skips the certifi-first attempt, the certifi default MUST remain the last resort so a wrong/stale host-agent var can never make recovery *worse* than today's certifi-first baseline. Each candidate tried at most once; verification stays ON for each.

## Scope

**Problem statement:** The model-fetch TLS fallback ignores the host coding agent's own CA-bundle env vars (`CODEX_CA_CERTIFICATE`, `CLAUDE_CODE_CERT_STORE`), so under Codex/Claude Code behind a corporate proxy the download can fail to resolve (or wastes a failed first attempt) even though the host already declared the correct bundle.

**In scope:**

- `_os_trust_store_bundle()` — prepend the host-agent vars (with precedence) in `setup_index.py`.
- The model-fetch path (`_warm_model` / its setup caller) — proactive pre-configuration of the CA bundle from a host-agent var when set, before the first attempt.
- The `ModelPrewarmError` remediation message — name the host-agent vars.
- Tests for the resolution order/precedence, proactive pre-config, the still-reachable platform fallback, and verification-stays-on.

**Out of scope:**

- The rest of the `1p7iu` TLS-fallback mechanism (chain-aware cert detection, `huggingface_hub.close_session()` retry) — already shipped, unchanged.
- Pre-bundling models in the distribution pack (separate packaging follow-on).
- A real corporate-proxy host download (the value gate — carried, downstream).

**Depends on:** `1p7iu` (the TLS-fallback path this extends — already implemented).

## Acceptance Criteria

- [x] AC-1: `_os_trust_store_bundle()` resolves in order `CODEX_CA_CERTIFICATE` → `CLAUDE_CODE_CERT_STORE` → `SSL_CERT_FILE` → `REQUESTS_CA_BUNDLE` → platform locations (first existing file wins); the reactive cert-fail retry honors a host-agent var. Verified by a test (incl. the precedence: `CODEX_CA_CERTIFICATE` beats a set `SSL_CERT_FILE`). — `_os_trust_store_candidates`/`_os_trust_store_bundle`; `test_each_ca_env_var_honored`, `test_codex_var_takes_precedence_over_ssl_cert_file`.
- [x] AC-2: when a host-agent CA var points at a real file and `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` are unset, the model fetch configures the CA bundle from it **before** the first attempt (no guaranteed-fail round-trip); and if that bundle still fails cert-verify, the retry **iterates to the next candidate** (the platform store) rather than hard-failing (per Requirement 5). Verified by a test (proactive pre-config + host-agent-bundle-fails-then-platform-store-tried). — `_warm_model` proactive pre-config + candidate iteration; `test_warm_model_proactive_preconfig_skips_failed_first_attempt`, `test_warm_model_iterates_to_platform_store_when_host_bundle_fails`.
- [x] AC-3: no code path disables TLS verification — only the trusted CA bundle is selected/swapped; `test_no_path_disables_tls_verification` (no `_create_unverified_context`/`CERT_NONE`/`verify=False`) still passes.
- [x] AC-4: tests cover each env var honored; the precedence (incl. `CODEX_CA_CERTIFICATE` over a set `SSL_CERT_FILE`, with the operator's `SSL_CERT_FILE` preserved as a later candidate); proactive pre-config; candidate iteration to the platform store **and the certifi-default last resort**; and verification-stays-on; framework tests bytecode-free; `wave_validate` clean. — `test_candidates_end_with_certifi_default`, `test_warm_model_iterates_to_certifi_default_last`, `test_warm_model_restores_operator_env_after_run` + the AC-1/AC-2 tests; 12 TLS tests green.
- [~] AC-5: real corporate-proxy host value gate (a download under Codex/Claude Code behind an actual TLS-inspecting proxy with only the host var set) — **deferred/downstream**; recorded as the remaining gate, like `1p7iu` AC-5. (Operator-run; cannot be exercised in CI — no real TLS-inspecting proxy here.)

## Tasks

- [x] Prepend `CODEX_CA_CERTIFICATE` + `CLAUDE_CODE_CERT_STORE` in `_os_trust_store_bundle()`'s env-var loop (ahead of `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`).
- [x] Add proactive CA-bundle pre-configuration to the model-fetch path when a host-agent var is set and the stack CA env is unset.
- [x] Expose the trust store as an ordered candidate list + iterate candidates on cert-fail (replace the single-bundle `already_tried` short-circuit) so a failing host-agent bundle degrades to the platform store (Requirement 5).
- [x] Name the host-agent vars in the `ModelPrewarmError` remediation message.
- [x] Tests (resolution order/precedence, proactive pre-config, platform fallback still reached, verification-stays-on) bytecode-free.

## Agent Execution Graph


| Workstream    | Owner       | Depends On   | Notes                                                   |
| ------------- | ----------- | ------------ | ------------------------------------------------------- |
| ca-discovery  | implementer | —            | prepend host-agent vars in `_os_trust_store_bundle`     |
| proactive     | implementer | ca-discovery | pre-config the bundle before the first fetch when set   |
| tests         | implementer | ca-discovery | order/precedence, proactive, platform fallback, secure  |


## Serialization Points

- Independent subsystem (model-fetch/TLS). Pairs naturally with the next TLS/model-fetch touch; no coordination with the `1p7pk` launcher wave.

## Affected Architecture Docs

- N/A — confined to the model-fetch/preflight path in `setup_index.py`; no boundary/flow/verification-architecture change. Confirm at Prepare.

## AC Priority

(Proposed; confirmed at Prepare.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The host-agent var discovery is the deliverable. |
| AC-2 | important | Removes the guaranteed-fail first attempt + resolves the host-var-only case; the user-visible win. |
| AC-3 | required  | Security guard — verification must never be disabled. |
| AC-4 | required  | Test-locked, bytecode-free. |
| AC-5 | important | Real proxy-host value gate. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-24 | Drafted from operator-provided host-agent CA env vars (`CODEX_CA_CERTIFICATE` precedence; `CLAUDE_CODE_CERT_STORE`). Extends the shipped `1p7iu` fallback, which resolves only `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` → platform. | `setup_index.py:379` `_os_trust_store_bundle`; memory `reference_host_agent_ca_env_vars_tls`; Codex/Claude Code env-var docs |
| 2026-06-24 | Readied. Wave Council readiness review caught that the single-bundle `already_tried` short-circuit would make a wrong/stale host-agent var *worse* than today — added Requirement 5 (ordered candidate iteration) + a task + tightened AC-2. Readiness signoff recorded; wave stays `planned` (readied), not opened (1p7pk holds the OPEN slot). | `wave.md` Review Evidence `wave-council-readiness`; Requirement 5 |
| 2026-06-24 | Implemented (admitted into OPEN wave 1p7pk). `_os_trust_store_candidates()` returns the ordered list host-agent (`CODEX_CA_CERTIFICATE`→`CLAUDE_CODE_CERT_STORE`) → operator (`SSL_CERT_FILE`→`REQUESTS_CA_BUNDLE`) → platform → **certifi-default last**; `_os_trust_store_bundle()` kept as a thin first-candidate accessor. `_warm_model` does proactive pre-config when a host-agent var is set + stack CA unset (skips the certifi-first attempt) and iterates candidates on cert-fail (each tried once, `close_session` rebuild between attempts, verification ON), replacing the `already_tried` short-circuit. Operator's set `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` is never discarded — per-attempt env is scoped + restored. `ModelPrewarmError` names the host-agent vars. 12 TLS tests green incl. `test_no_path_disables_tls_verification`; full suite green bar the known secrets flake; machine not mutated. | `setup_index._os_trust_store_candidates`/`_warm_model`/`_apply_ca_bundle`/`_host_agent_ca_bundle`/`_certifi_default_bundle`; `test_setup_index.TlsTrustStoreFallbackTests` (12) |
| 2026-06-24 | Pre-close review fix (security: trust-anchor leak): the operator's `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` were restored only on SUCCESS (failure paths guarded with the *inverse* `if not _operator_set_stack`), so on all-candidates-fail / a non-cert error mid-retry a set operator env was left clobbered with the last-tried bundle. Restoration is now **symmetric via try/finally** — the TRUE original (snapshotted once) is restored on EVERY exit when the operator set it (success or failure); when unset, the winning bundle persists on success and is popped on failure. This also fixes the `_prewarm_required_model` second-order corruption (the 2nd `warm_fn` attempt now snapshots from the restored true original, not a mutated env). Verification stays ON. Removed the dead unreachable `_build()` after the unconditional `raise`. New tests: operator-set + all-candidates-fail → `ModelPrewarmError` AND original `SSL_CERT_FILE` preserved; non-cert error during a retry → operator env restored. | `setup_index._warm_model` try/finally; `test_setup_index` `test_warm_model_restores_operator_env_on_all_candidates_fail`, `test_warm_model_restores_operator_env_on_non_cert_error_mid_retry` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-24 | Prepend host-agent vars (Codex precedence) AND use them proactively when set | A set host-agent var is the host's authoritative bundle for a TLS-intercept env where certifi fails anyway — use it first, skip the guaranteed-fail attempt. | Reactive-only (add to the order but keep certifi-first) — rejected: wastes a fetch and still misses the host-var-only case on the first try. Disable verification — rejected (insecure). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A stale/wrong host-agent var breaks a fetch certifi would have handled | Only use it when it points at an existing file; verification stays ON (a wrong bundle fails loud, never silently mis-trusts); on cert-fail the platform-location fallback is still reached, so recovery isn't worse than today. |
| Proactively setting `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` could mask an operator's own intent | Only pre-configure when those are UNSET (operator override always wins); host-agent vars are read, never overwritten. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
