# uv dep-install fails under SSL_CERT_FILE — isolate uv TLS from the model-download cert bundle

Change ID: `1p8tf-bug uv-ssl-cert-file-trust-conflict`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-29
Wave: `1p8tg uv-ssl-cert-file-trust-conflict` (requires `framework_edit_allowed` at implementation)

## Rationale

On a native-Windows corporate-MITM-proxy host, `wf setup` fails at the `uv pip install` step with a TLS `UnknownIssuer` error whenever `SSL_CERT_FILE` is set in the environment; with `SSL_CERT_FILE` unset (uv using the OS/native store) the install succeeds. Root cause (field report, confirmed against our code): **uv treats `SSL_CERT_FILE` as its *exclusive* trust anchor** — it loads only that single PEM and rejects PyPI's chain rather than augmenting the platform store. But our embedding-model download path needs the corporate root trusted, and the operator's only lever today is to set `SSL_CERT_FILE` globally — which then poisons uv.

Confirmed in `setup_index.py`:

- `_os_trust_store_candidates()` (`:423-444`) selects the **first existing** candidate file — it never merges/concatenates — so in a corp-MITM env the bundle is a **single corp-root PEM, not a superset**.
- `_apply_ca_bundle()` (`:479-492`) writes that PEM to **`os.environ["SSL_CERT_FILE"]` and `["REQUESTS_CA_BUNDLE"]` process-globally**.
- `_install_deps()` (`:271-312`) invokes uv (`:289-293`) via `subprocess_util.isolated_run(cmd)` (`:303`) with **no `env=` and no `--native-tls`/`UV_NATIVE_TLS`** — uv inherits the unmodified `os.environ`, including any operator-set `SSL_CERT_FILE`. Same for the `_bootstrap_uv()` pip step (`:259-268`).
- Sequencing (`main()` `:1219-1280`): uv (`ensure_deps()`, step 1) runs **before** the in-process fastembed/HuggingFace download (`prewarm_models()`→`_warm_model()`, step 3). So at uv-time, `SSL_CERT_FILE` can only have been set by the **operator's shell** — and we never scrub or scope it for uv.

The operator workaround (install deps first with no `SSL_CERT_FILE`, then run with it set so the uv step is a no-op) proves the fix direction. This change makes that automatic and invisible.

## Requirements

1. **Isolate uv's TLS from `SSL_CERT_FILE` (core).** Every `uv` invocation (`_install_deps`, and the uv-bootstrap pip step in `_bootstrap_uv`) must run with an env where `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE` (and `SSL_CERT_DIR` if present) are **removed**, and `UV_NATIVE_TLS=1` is **set**, so uv uses the OS/native certificate store regardless of the operator's environment. The change must not mutate the parent `os.environ` — build a scoped env dict passed via `env=`.
2. **Preserve the model-download trust path.** The fastembed/HuggingFace download must still trust the corporate root: the existing `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` mechanism for `_warm_model()` stays intact (scrubbing applies only to the uv subprocess env, not to the in-process download).
3. **Merged superset trust bundle (companion robustness).** `_os_trust_store_*` should produce a **merged** bundle (OS/corporate roots concatenated with certifi roots), written to a stable file under the tool dir, instead of selecting a single candidate file. Point `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` at that superset so every certifi/requests consumer validates both PyPI and the model host — and uv survives even if it ever inherits it. Preserve the existing candidate-priority ordering when assembling the merge; dedupe; tolerate unreadable candidates.
4. **No behavior change on non-corp / POSIX hosts.** When no corp/host-agent CA material is present, the existing default path (certifi) must be unchanged; `UV_NATIVE_TLS=1` on uv is safe on all platforms (uv falls back to its store on POSIX).

## Scope

**Problem statement:** `wf setup` uv dep-install fails `UnknownIssuer` when `SSL_CERT_FILE` is set, because uv treats it as the sole trust anchor; our cert-bundle mechanism sets it process-globally as a single PEM for the model download, and we don't isolate uv from it.

**In scope:**

- `setup_index.py`: scoped env for uv invocations (`_install_deps`, `_bootstrap_uv`); merged-superset bundle in `_os_trust_store_candidates`/`_os_trust_store_bundle`/`_apply_ca_bundle`.
- `test_setup_index.py`: unit coverage for uv env isolation and the merged bundle.

**Out of scope:**

- Changing the embedding model, the download retry/fallback ladder, or the host-agent CA candidate set (`CODEX_CA_CERTIFICATE`/`CLAUDE_CODE_CERT_STORE`/`NODE_EXTRA_CA_CERTS` — already shipped).
- `venv_bootstrap.py` / `setup_wavefoundry.py` / `subprocess_util.py` CA behavior (they touch no CA vars today and should keep not doing so).
- Any non-TLS setup change.

## Acceptance Criteria

- [x] AC-1: every `uv` invocation runs with `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`(/`SSL_CERT_DIR`) removed from its env and `UV_NATIVE_TLS=1` set; the parent `os.environ` is not mutated by this scoping. (`_uv_install_env()`; `test_uv_env_scrubs_cert_vars_and_sets_native_tls`)
- [x] AC-2: with `SSL_CERT_FILE` set in the environment to a single non-PyPI-anchoring PEM, the uv invocation env no longer contains it (regression-locks the field bug). (`test_uv_env_scrubs_cert_vars_and_sets_native_tls`)
- [x] AC-3: a merged superset bundle (corp/OS roots + certifi) is produced rather than a single selected file; contains certs from more than one source, dedupes, and tolerates an unreadable candidate. (`_merged_trust_bundle()`; `test_merged_bundle_is_superset_and_dedupes`, `test_merged_bundle_tolerates_unreadable_candidate`) **Implementation note:** delivered as a NEW additive `_os_trust_store_*`-family function consumed by pip (`_pip_tls_env`), leaving the existing per-store ladder (`_os_trust_store_candidates`/`_os_trust_store_bundle`/`_warm_model`) byte-for-byte unchanged — deliberately, so this does not rework/counter the validated 1p7s6/1p7iu TLS work (operator's "does this counter prior work?" concern).
- [x] AC-4: the model-download trust path is preserved — `_warm_model()`'s per-store ladder is untouched (the change is additive). (existing ladder tests stay green; `test_warm_model_ladder_functions_unchanged`)
- [x] AC-5: no behavior change when no corp/host-agent CA material is present — `_uv_install_env`/`_merged_trust_bundle`/`_pip_tls_env` all return `None` (inherit) in a plain env. (`test_uv_env_none_when_no_cert_vars`, `test_merged_bundle_none_in_plain_env`, `test_pip_env_none_in_plain_env`)
- [x] AC-6: the full framework suite + docs-lint stay green. (suite 3692 ok; docs-lint ok)
- [~] AC-7 (field validation, Windows-repro-gated): the reporting operator confirms `wf setup` completes on the corp-MITM Windows host with `SSL_CERT_FILE` set, without manual pre-install. *Not verifiable on macOS — awaits operator validation of a build; the mechanism is locked by unit tests in the meantime.*

## Tasks

- [x] Add a helper that builds the uv subprocess env (copy `os.environ`, drop the CA-file vars, set `UV_NATIVE_TLS=1`) and pass it via `env=` from `_install_deps` and `_bootstrap_uv` (under `framework_edit_allowed`). (`_uv_install_env` for the uv binary; `_pip_tls_env` for the pip-bootstrap + pip fallback — pip gets the superset rather than a scrub, since it can't use the OS store portably and needs the corp root if PyPI is MITM'd.)
- [x] Assemble a merged, deduped superset bundle file (priority order preserved; unreadable candidates skipped). (`_merged_trust_bundle`, written to `~/.wavefoundry/cache/ca/merged-ca-<hash>.pem`. Implemented additively — `_apply_ca_bundle` and the ladder are unchanged.)
- [x] Verify `UV_NATIVE_TLS`/`--native-tls` is the correct uv knob. (`UV_NATIVE_TLS=1` is the documented uv env equivalent of `--native-tls`; the env-scrub is the load-bearing fix even if the hint is a no-op. Final confirmation on the operator's box is folded into AC-7.)
- [x] Add `test_setup_index.py` cases for AC-1/2/3/4/5. (8 cases in `UvSslCertFileIsolationTests`.)
- [x] Run the framework suite + docs-lint; confirm green. (suite 3692 ok; docs-lint ok)
- [~] Hand the build to the reporting operator for AC-7 validation. *Pending a build/release for the operator to test.*

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| uv env isolation (`_install_deps`/`_bootstrap_uv`) | implementer | — | `framework_edit_allowed`; the certain core fix |
| merged superset bundle (`_os_trust_store_*`) | implementer | — | same file (`setup_index.py`) — coordinate edits |
| tests + suite/docs-lint | qa-reviewer | both | AC-1..6 |

## Serialization Points

- Both code workstreams edit `setup_index.py` — open `framework_edit_allowed` for the pass and coordinate the two edits (the env helper and the bundle-merge) to avoid churn.

## Affected Architecture Docs

`N/A` — confined to the setup-index TLS/cert-bundle handling within a single module; no boundary, data-flow, or verification-architecture change. (If the merged-bundle approach is judged a durable design choice worth recording, consider a short ADR at Prepare; default N/A.)

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The core fix — isolates uv from the poisoning env var. |
| AC-2 | required | Regression-locks the exact field failure. |
| AC-3 | important | Robustness companion; not strictly required to fix the report but closes the single-PEM gap. |
| AC-4 | required | Must not regress the model-download trust path. |
| AC-5 | required | No collateral change on default/POSIX hosts. |
| AC-6 | required | Suite + docs-lint green. |
| AC-7 | important | Real-world confirmation; Windows-repro-gated, post-build. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-29 | Drafted from a confirmed native-Windows corp-MITM field report. Root cause mapped in `setup_index.py` (single-PEM bundle + process-global `SSL_CERT_FILE` + un-scoped uv subprocess env). | `setup_index.py:423,479,271,259,1219`; field memory `field-feedback-uv-ssl-cert-file-conflict`. |
| 2026-06-29 | Implemented A+B. A: `_uv_install_env` scrubs the CA-file vars + sets `UV_NATIVE_TLS=1` for the uv binary; `_pip_tls_env` points pip (bootstrap + fallback) at the merged superset. B: `_merged_trust_bundle` builds a deduped union of trusted stores, gated on corp material present (plain env unchanged). Prior per-store ladder left untouched (additive) — answers the "don't counter prior work" check. | `setup_index.py` diff; framework suite 3692 ok (was 3684); 8 new `UvSslCertFileIsolationTests`; docs-lint ok; existing TLS-ladder + `test_no_path_disables_tls_verification` faithfulness tests stay green. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-29 | Fix A (scope `SSL_CERT_FILE` out of uv + `UV_NATIVE_TLS=1`) is the core; B (merged superset bundle) ships as a companion in the same wave. | A directly and certainly neutralizes uv's exclusive-anchor behavior; B closes the single-PEM gap for all certifi/requests consumers and de-risks uv inheriting the var. | A only (leaves the single-PEM gap); B only (relies on uv honoring a superset — less certain than scrubbing); operator manual two-step (not durable). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `UV_NATIVE_TLS`/`--native-tls` may not be the exact/sufficient uv knob, or may not pick up the corp root from the Windows store. | Verify against uv docs + the operator's box before finalizing (a task); the env-scrub alone already removes the poisoning var even if the native-TLS hint is a no-op. |
| Merged-bundle assembly could itself fail to anchor PyPI in some corp setups. | A (scrub + native store) is independent of B and is the primary fix; B is additive robustness, not the load-bearing path. |
| macOS CI cannot reproduce the Windows corp-MITM failure. | Lock the mechanism with unit tests on the env dict + bundle contents; gate the real-world AC-7 on operator validation of the build. |
| Editing `setup_index.py` networking risks collateral regressions. | Scope changes to the named functions; keep the default/POSIX path untouched (AC-5); full suite must stay green (AC-6). |
| **(delivery-review, red-team)** Fix A (scrub + `UV_NATIVE_TLS`) assumes the corp root is in the **OS trust store**. A consumer whose corp root is only a standalone PEM (`SSL_CERT_FILE`), not in the OS store, *and* whose PyPI is MITM-intercepted would regress (uv previously used that PEM directly). | Validated case (Brian's "test A") has the root in the Windows store, and a system-wide MITM root belongs there. AC-7 will expose it if real. **Ready fallback (A2):** feed uv the merged superset as `SSL_CERT_FILE` (a complete exclusive anchor) instead of scrubbing — adopt A2 only if AC-7 shows the OS-store assumption fails. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
