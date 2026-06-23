# Model fetch: fall back to the OS trust store on certifi verification failure

Change ID: `1p7iu-enh model-fetch-os-trust-store-fallback`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-23
Wave: `1p7ir index-build-robustness`

## Rationale

1.8.0 introduced the `BAAI/bge-small-en-v1.5` code model, which is not in the pre-1.8.0 fastembed cache. Behind a corporate TLS-inspecting proxy the corporate root CA is present in the **OS trust store** (`/etc/ssl/certs/ca-certificates.crt`) but **not** in the venv’s bundled `certifi` — and huggingface_hub/fastembed verify against `certifi` by default. So the model download fails with `CERTIFICATE_VERIFY_FAILED` even though `curl`/system tools succeed (verified: TLS handshake to `huggingface.co` fails with the certifi bundle, succeeds with the system bundle). No OS-trust-store fallback exists in the scripts today.

This blocks the first index build after upgrade on common corporate WSL/Linux setups, and the only signal is a raw SSL stack trace.

## Requirements

1. **OS-trust-store fallback on cert failure.** When a model fetch fails with `CERTIFICATE_VERIFY_FAILED`, retry against the OS trust store (`/etc/ssl/certs/ca-certificates.crt` and platform equivalents) — and honor `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` if already set — before surfacing failure. Verification stays **ON** throughout (never disabled).
2. **Preflight detection + actionable remediation.** In the `setup_index` / preflight path, detect the certifi-vs-system CA gap and emit the two-env-var remediation, instead of a raw SSL stack trace.
3. **Secure by construction.** No code path disables TLS verification or sets an insecure context; the fallback only swaps the trusted CA bundle to the OS store.

## Scope

**Problem statement:** A model added in an upgrade can’t download behind a corporate proxy because fastembed verifies against certifi, not the OS trust store — with no fallback and an opaque error.

**In scope:**

- The model-fetch/preparation path (the fastembed/huggingface_hub download) — add the OS-trust-store retry + `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` honoring.
- Preflight gap detection + remediation messaging in `setup_index` / `setup_wavefoundry`.
- Tests for the fallback decision (cert-fail → retry with OS bundle) without disabling verification.

**Out of scope:**

- Pre-bundling the embedding models in the distribution pack (explicit follow-on — a packaging effort that also helps air-gapped hosts; raise as its own wave if pursued).
- The OOM guardrails (`1p7it`) and health honesty (`1p7is`).

## Acceptance Criteria

- [ ] AC-1: on `CERTIFICATE_VERIFY_FAILED`, the fetch retries against the OS trust store (and honors a preset `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`) before failing; verification is never disabled.
- [ ] AC-2: the `setup_index`/preflight path detects the certifi-vs-system CA gap and emits the actionable env-var remediation rather than a raw stack trace.
- [ ] AC-3: no code path disables TLS verification or installs an insecure SSL context (assert in test/review).
- [ ] AC-4: framework tests cover the fallback decision (cert-fail → OS-bundle retry) and the preflight gap detection, bytecode-free; `wave_validate` clean.
- [ ] AC-5: measured on a proxy host (or a repro with a CA only in the system store) — the model downloads with the fallback and caches for offline reuse; recorded as the value gate.

## Tasks

- [ ] Add the OS-trust-store fallback + `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` honoring to the model-fetch path.
- [ ] Add preflight certifi-vs-system gap detection + remediation messaging.
- [ ] Tests (fallback decision, preflight detection, verification-stays-on) bytecode-free.

## Agent Execution Graph


| Workstream    | Owner       | Depends On | Notes                                       |
| ------------- | ----------- | ---------- | ------------------------------------------- |
| tls-fallback  | implementer | —          | OS-store retry on cert-fail; honor env vars |
| preflight     | implementer | —          | gap detection + remediation message         |
| value-gate    | reviewer    | tls-fallback | proxy-host / system-CA repro download       |


## Serialization Points

- Independent of `1p7is`/`1p7it`/`1p7iv` (different subsystem). Pairs naturally with the OOM fixes in a 1.8.1.

## Affected Architecture Docs

- N/A — confined to the model-fetch/preflight path; no boundary/flow change. Confirm at Prepare.

## AC Priority

(Populated at Prepare wave — proposed below.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The fallback is the deliverable. |
| AC-2 | important | Turns an opaque SSL trace into actionable remediation. |
| AC-3 | required  | Security guard — verification must never be disabled. |
| AC-4 | required  | Test-locked, bytecode-free. |
| AC-5 | important | Real proxy-host value gate. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-23 | Drafted from the 1.8.0 field report. No OS-trust-store fallback present (grep-confirmed); new `bge-small` model not pre-cached → first fetch fails behind certifi-only venv. | memory `project_field_feedback_1p8_oom_tls`; `indexer.py:40-46` model split |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-23 | OS-trust-store fallback, verification kept ON | Many corporate WSL/Linux setups have the right CA only in the system store; the secure path keeps verification on. | Disable verification — rejected (insecure). Pre-bundle models — deferred (separate packaging follow-on). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Fallback masks a genuine cert problem | Only retry on `CERTIFICATE_VERIFY_FAILED`, only with a real OS/`SSL_CERT_FILE` bundle, verification still on; surface the original error if the fallback also fails. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
