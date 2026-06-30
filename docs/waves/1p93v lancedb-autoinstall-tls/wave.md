# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-30

wave-id: `1p93v lancedb-autoinstall-tls`
Title: Lancedb Autoinstall Tls

## Objective

Close the one unwired pip-install call site found during a post-1p939 sweep: `indexer.py`'s
`lancedb` auto-install spawns a bare `pip install` with no TLS-conflict mitigation, unlike every
other pip/uv install call site in `setup_index.py`. When this wave closes, that call site reuses
the same `_pip_tls_env()` helper, closing the same corp-proxy TLS failure class wave `1p939` closed
for model downloads.

## Changes

Change ID: `1p93u-bug lancedb-autoinstall-bare-pip-tls`
Change Status: `implemented`

Completed At: 2026-06-30

## Wave Summary

Wave `1p93v` (Lancedb Autoinstall Tls) delivered one change: Apply pip TLS-conflict mitigation to indexer.py's lancedb auto-install.

**Changes delivered:**

- **Apply pip TLS-conflict mitigation to indexer.py's lancedb auto-install** (`1p93u-bug lancedb-autoinstall-bare-pip-tls`) — 3 ACs completed. Key decisions: Reuse `setup_index._pip_tls_env()` at the `indexer.py` call site rather than writing a new helper or duplicating CA-merge logic.
## Participants

| Lane | Trigger |
| ---- | ------- |
| `code-reviewer` | Change edits `.wavefoundry/framework/scripts/indexer.py` |
| `qa-reviewer` | Required for bug-fix changes (`review_policies.require_qa_reviewer_for_bug_fixes: true`) |

## Journal Watchpoints

- Watchpoint: discovered via a deliberate sweep (not a field report) prompted by the operator
  asking whether other downloaded Python dependencies share wave 1p939's TLS-trust gap; see this
  session's conversation for the sweep methodology (grep for every `pip`/`uv install` subprocess
  invocation across `.wavefoundry/framework/scripts/**/*.py`, cross-checked against which call
  sites already pass `env=_uv_install_env()`/`_pip_tls_env()`).
- Watch for the same circular-import risk pattern as wave 1p939: `indexer.py` must import
  `setup_index` function-locally, not at module level (no module-level import exists today in
  either direction — confirmed before this wave was opened).
- No corporate-proxy machine available in this environment to validate the real repro; verification
  relies on unit tests asserting the correct `env=` kwarg is passed to the subprocess call under a
  forced CA-var-set condition, plus a no-corporate-env regression check.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: this is the fourth pip/uv call site found needing this exact fix — should the mitigation move down into `subprocess_util.isolated_run()` itself (auto-detect a pip/uv install command and apply the TLS env transparently) so a fifth occurrence can't happen, rather than patching one more call site by hand?; strongest-alternative: make `isolated_run()` pip/uv-aware — rejected for this wave: `isolated_run()` is a generic cross-OS subprocess wrapper used by many non-pip/uv callers (window-flag/stdin/encoding isolation only); teaching it to special-case pip/uv commands and silently rewrite their env is a broader, higher-blast-radius behavior change than this narrowly-scoped reuse of an already-shipped helper, and isn't grounded in a demonstrated recurring-gap rate (one prior + one new instance, not a pattern yet); worth a follow-up architectural change if a fifth call site appears. Architecture-reviewer: clean reuse, function-local import confirmed non-circular (no existing import either direction in `indexer.py`/`setup_index.py`), no domain-map impact. Security-reviewer (fixed + rotating): `_pip_tls_env()` is reused unchanged — no new logic, no verification-disabling path, identical contract to the three already-shipped call sites; rotating seat reaffirms no alternative stronger than the primer's systemic-fix note, which is explicitly deferred rather than silently dropped. qa-reviewer: AC-1/2/3 concretely testable via a mocked `subprocess_util.isolated_run` call asserting the `env=` kwarg; AC priority table fully populated. Reality-checker: the one load-bearing assumption — that `_pip_tls_env()`'s existing contract (inherit unchanged when no CA var; merged bundle when one is set) applies identically to this new call site — holds because `lancedb` is a plain PyPI package with no special index/auth requirement, same as the three existing call sites' packages.)

- **Delivery-phase review [delivery-review] — 2026-06-30: PASS** (implementation-phase self-review, proportionate to scope — see Review Evidence for the line-by-line verification performed; no blocking findings; `qa-reviewer` re-confirmed AC-1/AC-2/AC-3 against the real diff and tests, not the change doc's claims alone)

## Review Evidence

- wave-council-readiness signoff: approved — prepare-council — moderator=wave-council, primer-depth=standard, seats=[red-team(primer), architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer(rotating)], rotating-seat=security-reviewer, strongest-challenge="this is the fourth pip/uv call site found needing this fix — should the mitigation move into subprocess_util.isolated_run() itself so a fifth occurrence can't happen?", strongest-alternative="make isolated_run() pip/uv-aware — rejected for this wave: broader, higher-blast-radius change to a generic cross-OS subprocess wrapper used by many non-pip/uv callers, not grounded in a demonstrated recurring-gap rate yet; worth a follow-up if a fifth call site appears"
- `qa-reviewer` signoff (prepare-phase): approved — AC-1/AC-2/AC-3 are concretely testable (mocked `subprocess_util.isolated_run` call, asserting the `env=` kwarg under both a CA-var-set and plain-env condition); AC priority table fully populated, no placeholders.
- wave-council-delivery signoff: approved — moderator=wave-council (implementation-phase self-review, proportionate to change size: one function, one new `import` + one `env=` kwarg, mirroring 3 already-shipped call sites — no agent fan-out, but verified line-by-line, not rubber-stamped). Confirmed: `isolated_run(cmd, check=False, env=...)` forwards `env` straight to `subprocess.run` with no interference (re-read `subprocess_util.py:74-101`); `env=None` and "no `env` kwarg at all" are semantically identical to `subprocess.run` (AC-2 genuinely a no-op, not just by test assertion); `patch.object(self.bi.venv_bootstrap/.subprocess_util, ...)` and `patch("setup_index._pip_tls_env", ...)` all correctly target the same shared module objects `_auto_install_lancedb()` resolves at call time (modules are `sys.modules`-cached singletons); no circular import (confirmed via grep, no `import indexer`/`from indexer` anywhere in `setup_index.py`); `_pip_tls_env()` itself unchanged and already proven safe at 3 other call sites. AC-5-equivalent (no TLS-verification-disabling) holds — no `verify=` touched anywhere. No findings.
- `qa-reviewer` signoff (delivery-phase): approved — re-verified AC-1/AC-2/AC-3 against the actual diff and the 3 new tests in `LanceDbAutoInstallTlsTests`; all three pass and genuinely exercise the claimed behavior (positive: `env` kwarg equals the mocked merged-bundle dict; negative: `env` kwarg is `None`); full suite re-confirmed 3,729 tests OK.
- operator-signoff: approved — 2026-06-30, operator explicitly requested closure

## Dependencies

- No external wave dependencies.
