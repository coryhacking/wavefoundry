# Apply pip TLS-conflict mitigation to indexer.py's lancedb auto-install

Change ID: `1p93u-bug lancedb-autoinstall-bare-pip-tls`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-30
Wave: `1p93v lancedb-autoinstall-tls`

## Rationale

Discovered while auditing whether other downloaded Python dependencies share the TLS-trust gap
fixed in wave `1p939` (CA bundle corp-proxy coverage, model downloads). `setup_index.py` already
mitigates the known `uv`/`pip`-vs-`SSL_CERT_FILE` conflict (uv treats `SSL_CERT_FILE` as its
*exclusive* trust anchor and rejects PyPI when it's set to a single corp-only PEM; pip has an
analogous failure mode) at its three pip/uv install call sites, via `_uv_install_env()` /
`_pip_tls_env()` (wave 1p8tf, `field_feedback_uv_ssl_cert_file_conflict`):

```
setup_index.py:266  pip install uv      → env=_pip_tls_env()
setup_index.py:294  uv pip install ...  → env=_uv_install_env()
setup_index.py:308  pip install ...     → env=_pip_tls_env()
```

A sweep of every `pip`/`uv` install subprocess invocation across `.wavefoundry/framework/scripts/`
found a fourth, unwired call site: `indexer.py::_auto_install_lancedb()` (`indexer.py:1117-1133`)
spawns `[venv_python, "-m", "pip", "install", "lancedb"]` via `subprocess_util.isolated_run(cmd,
check=False)` with **no `env=` override**. `isolated_run` only applies stdin/window-flag/encoding
isolation (confirmed by reading `subprocess_util.py:74-101`) — it never touches TLS env vars. The
subprocess therefore inherits whatever `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` is set in the parent
process unchanged, reproducing the same structural failure `_pip_tls_env()` exists to fix, at a call
site nobody wired it into.

Two concrete trigger paths:

1. An operator who already has `SSL_CERT_FILE` set in their shell to a single corp-only PEM (a
   common corp-proxy baseline, independent of anything this project's code does) hits this the first
   time `lancedb` needs cold-start auto-installing into the tool venv.
2. After wave `1p939`'s fix, `setup_index.ensure_ca_bundle_applied()` may already have set
   `SSL_CERT_FILE` to a single host-agent CA PEM earlier in the same `indexer.py` process (e.g. an
   embedding download ran first) before the lancedb auto-install runs later in that same process.

This is the same bug *class* as wave `1p939`, in the same file (`indexer.py` is the recurring
non-setup-launcher blind spot), on the dependency-install side instead of the model-download side.

## Requirements

1. `_auto_install_lancedb()`'s `pip install lancedb` subprocess must apply the same pip
   TLS-conflict mitigation `_pip_tls_env()` already provides at `setup_index.py`'s three pip/uv
   install call sites.
2. The fix must reuse `setup_index._pip_tls_env()` rather than duplicating CA-merge logic in
   `indexer.py`, consistent with wave `1p939`'s reuse principle.
3. No behavior change in a plain (non-corporate) environment — `_pip_tls_env()` already returns
   `None` (inherit unchanged) when no CA-file env var is set, so this call site must remain a true
   no-op there.

## Scope

**Problem statement:** `indexer.py`'s lancedb auto-install spawns `pip install lancedb` with no
environment override, bypassing the pip TLS-conflict mitigation (`_pip_tls_env()`) applied
everywhere else pip is invoked in this codebase, leaving this one call site exposed to the
`SSL_CERT_FILE`-narrows-trust failure mode `_pip_tls_env()` exists to fix.

**In scope:**

- Apply `setup_index._pip_tls_env()` to the `pip install lancedb` subprocess call in
  `indexer.py::_auto_install_lancedb()`.
- Regression coverage: a plain env (no CA var set) passes no env override (current behavior
  unchanged); a CA-var-set env passes the merged-superset bundle.

**Out of scope:**

- `_uv_install_env()` / `_pip_tls_env()`'s own internal logic — unchanged, already correct and
  tested (wave 1p8tf).
- The HF Hub / model-download CA-bundle work (wave `1p939`) — a different download path/library
  (`huggingface_hub`, not `pip`), already closed.
- Any other dependency-management surface (e.g. `wf setup`'s own `uv`/`pip install` flows) —
  already covered per the sweep in Rationale; no other unwired call site was found.

## Acceptance Criteria

- [x] AC-1: `_auto_install_lancedb()`'s `pip install lancedb` subprocess call passes
      `env=setup_index._pip_tls_env()` so it picks up the merged-superset CA bundle when an
      operator/host-agent CA var is set. Evidence: `indexer.py:1117-1130`;
      `test_applies_pip_tls_env_when_ca_var_set` (`test_indexer.py`).
- [x] AC-2: With no CA var set, the call passes no env override (`None` → inherit), matching
      current behavior exactly — no regression in the plain environment. Evidence:
      `test_no_env_override_in_plain_env` (`test_indexer.py`).
- [x] AC-3: No circular import — `setup_index` is imported function-locally inside
      `_auto_install_lancedb()`, mirroring the established direction-safety pattern from wave
      `1p939` (`accel_embedder`/`server_impl` ↔ `setup_index`, never module-level in the reverse
      direction). Evidence: `indexer.py:1129` (function-local `import setup_index`); manual review
      confirms no module-level import either direction in `indexer.py`/`setup_index.py`.

## Tasks

- [x] Add a function-local `import setup_index` inside `indexer.py::_auto_install_lancedb()`. Done:
      `indexer.py:1129`.
- [x] Pass `env=setup_index._pip_tls_env()` to the `subprocess_util.isolated_run(cmd, check=False)`
      call at `indexer.py:1127`. Done: `indexer.py:1130`.
- [x] Add unit tests for `_auto_install_lancedb()`: a positive case (CA var set → the subprocess
      call receives the merged-bundle env) and a negative case (plain env → no env override passed,
      i.e. inherits unchanged). Done: `LanceDbAutoInstallTlsTests` (`test_indexer.py`, 3 tests —
      also covers the pre-existing install-failure path, untouched by this fix).
- [x] Open `wave_gate_open(gate='framework_edit_allowed')` before editing `indexer.py` and close it
      immediately after, per AGENTS.md Key Guardrails. Done.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`. Done: 3,729 tests across 39 files,
      OK (2026-06-30).

## Agent Execution Graph

| Workstream     | Owner       | Depends On | Notes                                        |
| -------------- | ----------- | ---------- | --------------------------------------------- |
| [workstream-1] | implementer | —          | Single-lane fix; no parallelizable sub-scope. |

## Serialization Points

- `indexer.py` is the only file edited (reuses `setup_index._pip_tls_env()` read-only, no edits to
  `setup_index.py`). No known in-flight work touches `indexer.py`'s `_auto_install_lancedb()`.

## Affected Architecture Docs

N/A — confined to `indexer.py`'s existing lancedb auto-install helper, reusing an existing
`setup_index` TLS-env helper; no module-boundary, integration-contract, or primary data/control-flow
change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The actual defect — without this, the call site remains exposed to the same corp-proxy TLS failure mode wave 1p939 closed elsewhere. |
| AC-2 | required | A regression here would break pip installs for every plain-environment operator — unacceptable trade for a corp-proxy-only fix. |
| AC-3 | required | Prevents a circular-import regression between `indexer.py` and `setup_index.py`, matching the established safety pattern. |

## Progress Log

| Date       | Update                                 | Evidence |
| ---------- | --------------------------------------- | -------- |
| 2026-06-30 | Change doc authored after a post-1p939 sweep for other unwired pip/uv install call sites found this gap. | This doc; Rationale call-site sweep |
| 2026-06-30 | Implemented: `indexer.py::_auto_install_lancedb()` now imports `setup_index` function-locally and passes `env=setup_index._pip_tls_env()` to the `pip install lancedb` subprocess call. All tasks and ACs complete. | `indexer.py:1117-1130` diff; `LanceDbAutoInstallTlsTests` (3 new tests, `test_indexer.py`); full suite 3,729 tests OK |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------- |
| 2026-06-30 | Reuse `setup_index._pip_tls_env()` at the `indexer.py` call site rather than writing a new helper or duplicating CA-merge logic. | Identical problem shape to the three already-fixed `setup_index.py` call sites; `_pip_tls_env()` is already proven correct and tested (wave 1p8tf). | (A) Write a thinner pip-specific helper local to `indexer.py` — rejected: duplicates logic for no benefit, the existing helper already does exactly what's needed and is one function-local import away. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `_pip_tls_env()` returns a full copy of `os.environ` (plus the merged-bundle override) when a CA var is set — could pass more env to the pip subprocess than the bare call does today. | Identical to the three existing, already-shipped call sites in `setup_index.py` — a pip subprocess inheriting the full parent environment is the standard/expected behavior; no narrowing or new exposure. |
| Circular import between `indexer.py` and `setup_index.py`. | Function-local import only, mirroring the established `accel_embedder`/`server_impl` ↔ `setup_index` pattern from wave `1p939`; confirmed no module-level import exists in either direction today. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
