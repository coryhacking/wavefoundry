# Model fetch: fall back to the OS trust store on certifi verification failure

Change ID: `1p7iu-enh model-fetch-os-trust-store-fallback`
Change Status: `implemented`
Owner: Engineering
Status: implemented
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

- [x] AC-1: on `CERTIFICATE_VERIFY_FAILED`, `_warm_model` retries the fetch against the OS trust store (`_os_trust_store_bundle` — honors a preset `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`, then platform locations) before failing; verification never disabled — it only swaps the trusted CA bundle.
- [x] AC-2: on the cert failure (and when the OS store can't resolve it) the path emits the **actionable two-env-var remediation** (`SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`) instead of a raw SSL stack trace — handled inline at the fetch (the retry IS the detection), so no separate proactive preflight probe was needed.
- [x] AC-3: no code path disables verification — `test_no_path_disables_tls_verification` asserts the source has no `_create_unverified_context` / `CERT_NONE` / `verify=False`.
- [x] AC-4: tests cover the cert-error detection (chain-aware), env-honoring bundle resolution, cert-fail → OS-bundle retry, non-cert-error no-retry, and verification-stays-on; bytecode-free; `wave_validate` clean.
- [~] AC-5: real proxy-host value gate **deferred** — the fallback decision is locally validated (5 tests incl. the cert-fail→retry path); a download behind an actual TLS-inspecting proxy needs such a host (downstream), recorded as the remaining gate.

## Tasks

- [x] Add the OS-trust-store fallback + `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` honoring to `_warm_model` (the setup model-fetch path).
- [x] Emit certifi-vs-system gap remediation inline on the cert failure (the retry is the detection) — no separate preflight probe needed.
- [x] Tests (cert-error chain detection, env-honoring bundle, fallback retry, non-cert no-retry, verification-stays-on) bytecode-free.

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
| 2026-06-23 | **Implemented.** `_warm_model` wraps the fastembed download: on a chain-aware `CERTIFICATE_VERIFY_FAILED`, resolve an OS CA bundle (`_os_trust_store_bundle` — preset `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` first, then Debian/RHEL/SUSE/Alpine-macOS locations), set the env, and retry ONCE — verification stays ON (only the CA bundle is swapped). No bundle / already-tried → a `ModelPrewarmError` with the two-env-var remediation. 5 tests; suite 3437 OK. | `setup_index.py` `_os_trust_store_bundle`/`_is_cert_verify_error`/`_warm_model`; `test_setup_index.py` `TlsTrustStoreFallbackTests` |
| 2026-06-23 | **DEFECT CAUGHT + FIXED (review).** The first cut was a NO-OP: `huggingface_hub` 1.16.1 (which fastembed's `snapshot_download` uses) caches a GLOBAL `httpx.Client` whose SSL context is built ONCE against certifi — so setting the env after the first attempt left the cached client untouched and the retry failed identically. The mocked test masked it (it never exercised the real session). Fix: call `huggingface_hub.close_session()` after setting the env so the retry rebuilds the client against the OS bundle (documented for "an SSL certificate has been updated"); test now asserts `close_session` is called, locking the regression. Chain verified: fastembed → `snapshot_download` → `get_session()` cached `_GLOBAL_CLIENT`. | `huggingface_hub/utils/_http.py` `get_session`/`close_session`; `setup_index._warm_model`; test `hf.close_session.assert_called_once()` |


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
