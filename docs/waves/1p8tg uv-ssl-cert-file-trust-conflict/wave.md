# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-29

wave-id: `1p8tg uv-ssl-cert-file-trust-conflict`
Title: Uv Ssl Cert File Trust Conflict

## Objective

Fix `wf setup` failing `uv pip install` with a TLS `UnknownIssuer` on corporate-MITM hosts when `SSL_CERT_FILE` is set. Isolate every uv invocation from the model-download cert bundle (scrub `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`, set `UV_NATIVE_TLS=1`) and make the OS-trust-store fallback a merged superset bundle instead of a single PEM.

## Changes

Change ID: `1p8tf-bug uv-ssl-cert-file-trust-conflict`
Change Status: `implemented`

Completed At: 2026-06-29

## Wave Summary

Wave `1p8tg` (Uv Ssl Cert File Trust Conflict) delivered one change: uv dep-install fails under SSL_CERT_FILE — isolate uv TLS from the model-download cert bundle. Notable adjustments during implementation: uv dep-install fails under SSL_CERT_FILE — isolate uv TLS from the model-download cert bundle: Drafted from a confirmed native-Windows corp-MITM field report. Root cause mapped in `setup_index.py` (single-PEM bundle + process-global `SSL_CERT_FILE` + un-scoped uv subprocess env).

**Changes delivered:**

- **uv dep-install fails under SSL_CERT_FILE — isolate uv TLS from the model-download cert bundle** (`1p8tf-bug uv-ssl-cert-file-trust-conflict`) — 6 ACs completed. Key decisions: Fix A (scope `SSL_CERT_FILE` out of uv + `UV_NATIVE_TLS=1`) is the core; B (merged superset bundle) ships as a companion in the same wave; A is additive — the prior per-store TLS ladder is untouched.
## Journal Watchpoints

- Guard requirement: implementation needs `framework_edit_allowed` open (edits to `setup_index.py`); close immediately after.
- Sequencing: both code edits (uv env-scoping + bundle-merge) touch `setup_index.py` — coordinate to avoid churn.
- Watchpoint: verify the exact uv knob (`--native-tls` / `UV_NATIVE_TLS=1`) against uv docs + the operator's box before finalizing; the env-scrub is the load-bearing fix even if the native-TLS hint is a no-op.
- Blocking for full closure: AC-7 (real-world Windows corp-MITM validation) is repro-gated — cannot be verified on macOS; mark `[~]` with note until the operator confirms the build.

## Review Evidence

- wave-council-readiness: approved 2026-06-29 — one cited-root-cause bug change; localized to `setup_index.py`; 7 ACs (5 unit-assertable, 1 suite/lint, 1 Windows-repro-gated `[~]`); core fix A is independent of companion B; the single uv-knob uncertainty is carried as an explicit task + risk with the env-scrub as the load-bearing path. No dependencies.
- wave-council-delivery: approved 2026-06-29 — PASS. All ACs verified against the diff (AC-1..6 met; AC-7 `[~]` Windows-repro-gated). Faithfulness intact: no fail-open (the static `verify=False`/`CERT_NONE` guard still passes); the merged bundle unions only already-trusted stores; the prior 1p7s6/1p7iu per-store ladder is textually unchanged (additive). Strongest challenge (recorded as a Risk + carried to AC-7): Fix A assumes the corp root is in the OS trust store — true in Brian's validated test A — with A2 (feed uv the merged superset as SSL_CERT_FILE) as the ready fallback if AC-7 shows otherwise. Suite 3692 green; docs-lint ok.
- operator-signoff: pending operator confirmation at closure

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer [added lens, TLS change]; rotating-seat: none; strongest-challenge: if uv falls back to bundled webpki-roots rather than the native store when `SSL_CERT_FILE` is scrubbed, scrubbing alone could swap one failure for another — bounded by the field evidence that deps install with the var unset, and caught by the verify-the-knob task + the load-bearing operator AC-7; strongest-alternative: bundle-merge (B) only — rejected as less certain than scrubbing because it relies on uv honoring a superset it treats as exclusive. Security note carried to delivery: confirm the scrub removes only the CA-file vars and leaves native-store verification intact, no fail-open.)

## Dependencies

- No external wave dependencies.
