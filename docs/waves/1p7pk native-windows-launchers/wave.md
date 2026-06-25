# Wave Record

Owner: Engineering
Status: implementing
Last verified: 2026-06-24

wave-id: `1p7pk native-windows-launchers`
Title: Native Windows Launchers

## Objective

Two co-equal goals per `1p7pb-adr`: **(A)** the launcher and config surfaces work from a single committed checkout on macOS, Linux, **and native Windows (no WSL2)** for **CLI hosts** — every config names a single byte-identical **`command: "python"`**; `setup_wavefoundry` makes `python` resolve (verify on Windows; **symlink** `python`→venv on macOS/Linux — a symlink, not a shell alias, which a raw spawn ignores); GUI hosts are a documented residual with a gitignored absolute-venv-path fallback; and **(B) a single runtime execution surface** — *exactly one* venv resolver (`reexec_into_tool_venv`), with no config, launcher, hook body, or spawner re-deriving the venv path (enforced by a standing scan test). Every runtime-entry surface converges: the `render_platform_surfaces` configs, the Codex config in `render_agent_surfaces.py`, `.air/mcp.json`, the nine `bin/*` shims (thin `exec python` forwarders), the git hooks, and `run_tests`/`wave-dashboard`. Closes C-1/C-3/M-3/L-1 in `docs/references/native-windows-support.md`. Now: a mixed macOS/Windows team needs one repo that Just Works, and a real Windows host is available to verify it.

## Changes

Change ID: `1p7pl-ref shared-venv-bootstrap`
Change Status: `implementing`

Change ID: `1p7pm-enh interpreter-direct-launcher-rendering`
Change Status: `implementing`

Change ID: `1p7pn-enh git-hook-bootstrap-and-gitattributes`
Change Status: `implementing`

Change ID: `1p7s6-enh host-agent-tls-ca-discovery`
Change Status: `implementing`

Change ID: `1p7tz-enh wf-cli-dispatcher`
Change Status: `implementing`

Change ID: `1p7ww-enh upgrade-mcp-first-and-reconciliation`
Change Status: `implementing`

## Wave Summary

Three changes implement `1p7pb-adr`: `1p7pl-ref` lands the shared stdlib venv-bootstrap (consolidating the scattered resolvers; macOS/Linux runtime unchanged); `1p7pm-enh` flips **all** config surfaces (incl. Codex via `render_agent_surfaces.py` + `.air`) to the byte-identical `command: "python"`, adds the `setup_wavefoundry` `python`-verify + macOS/Linux symlink (+ the GUI-host gitignored absolute-path fallback), turns the `bin/*` shims into thin `exec python` forwarders, and carries the real-host smoke gate; `1p7pn-enh` migrates the git hooks onto the bootstrap, adds `.gitattributes`, and moves dashboard daemonization into Python.

A fourth change, **`1p7s6-enh`** (operator-admitted 2026-06-24, after the original three were code-complete), rides along: it extends the shipped `1p7iu` TLS fallback with host-agent CA-bundle env-var discovery (`CODEX_CA_CERTIFICATE` precedence, `CLAUDE_CODE_CERT_STORE`) in `setup_index._os_trust_store_bundle`. It is a **different subsystem** (model-fetch/TLS, not launchers), folded into this wave by operator direction; it carries its own prepare-council readiness review (red-team + security findings — certifi-default last resort, operator-`SSL_CERT_FILE` preserved) inside its change doc.

A fifth change, **`1p7tz-enh`** (operator-admitted 2026-06-25, after the launcher cutover settled), completes the launcher work: it retires the nine POSIX-only `.wavefoundry/bin/*` wrappers (**hard cutover**, operator-directed) in favor of one cross-OS `wf` Python dispatcher (`wf_cli.py`) behind a `wf` (bash) + `wf.cmd` (Windows) shim pair, and sweeps every live reference to `wf <subcommand>`. It closes gap C-2 (the last POSIX-only launcher surface); its review is the pre-close review (no separate prepare-council, like `1p7s6`).

A sixth change, **`1p7ww-enh`** (operator-admitted 2026-06-25, from 1.9.0-upgrade field feedback), is guidance-only: it routes agents to the `wave_upgrade()` MCP tool (the upgrade seed/prompt now LEAD with the MCP-first directive; the manual procedure is the relabeled no-MCP `wf upgrade` fallback), lists `wave_upgrade`/`wave_upgrade_status` in the tool surface (+ spec entry), and surfaces a major/minor reconciliation recommendation in `upgrade_wavefoundry.py` (sibling of the config-review line). No mechanical/launcher change; its review is the pre-close review.

## Journal Watchpoints

- **Goal-B invariant (single resolver):** the close-time success test is a standing scan — exactly one venv-resolution implementation (the shared helper); any other file with a `Scripts`-vs-`bin`/`WAVEFOUNDRY_TOOL_VENV` branch fails it unless explicitly allowlisted with rationale. This converts every "kept as sugar / out of scope" call into an explicit, defensible scope-out.
- **Two Windows-breaking misses the surface sweep caught** (must not regress): `.codex/config.toml` is rendered by `render_agent_surfaces.py` (a *different* file — `1p7pm` must edit it) and `.air/mcp.json` has no renderer at all; both still name the bash wrapper → Codex/Air unspawnable on Windows until flipped. The no-pathed-launcher guard must scan the on-disk config set, or it passes green while these stay broken.
- **Sequencing:** `1p7pl` (shared bootstrap) must land and keep macOS/Linux CI green **before** `1p7pm`/`1p7pn` flip configs onto the bare interpreter — every entry point must self-bootstrap into the venv first.
- **Blocking close gate:** `1p7pm` AC-6 is operator-run — CLI-host MCP attach via `command: "python"` + a hook fire on a real python.org-Windows **and** macOS post-symlink, plus the GUI-host residual exercised against the gitignored absolute-path fallback. The wave does **not** close green until this passes — native Windows cannot be claimed while every `nt` branch is unverified.
- **Late-admitted change (`1p7s6-enh`):** admitted 2026-06-24 *after* the prepare-council reviewed the original three, so it was NOT in that council's scope — it carries its own prepare-council verdict in its change doc instead. It is a separate subsystem (TLS/model-fetch); the wave cannot close until it too is implemented + green. Check the late-admitted-change drift diagnostic explicitly at close.
- **Second late-admitted change (`1p7tz-enh`):** admitted 2026-06-25 (operator-directed) *after* the prepare-council and after `1p7s6` — folded in before shipping so the launcher surface settles in one wave. It was NOT in any prepare-council's scope; **its review is the pre-close review** (mirror the `1p7s6` handling). It is the operator-CLI surface (`bin/*` → `wf` dispatcher, hard cutover); the wave cannot close until it too is implemented + green, and the late-admitted-change drift diagnostic must be checked explicitly at close for BOTH `1p7s6` and `1p7tz`.
- **Third late-admitted change (`1p7ww-enh`):** admitted 2026-06-25 (operator-directed, from 1.9.0-upgrade field feedback) — folded in before shipping. NOT in any prepare-council's scope; **its review is the pre-close review** (same handling as `1p7s6`/`1p7tz`). It is guidance/tool-surface only (MCP-first upgrade routing in `seed-160`/prompt; `wave_upgrade`/`wave_upgrade_status` discoverability; a major/minor reconciliation recommendation in `upgrade_wavefoundry.py`) — no mechanical change. Includes a gated `seed-160` edit. The wave cannot close until it too is green; check the late-admitted-change drift diagnostic at close for `1p7s6`, `1p7tz`, AND `1p7ww`.
- **Guard:** all code edits are framework-maintenance — open `framework_edit_allowed` before editing `render_platform_surfaces.py`/entry scripts, close after.
- **Hard constraints to watch in review:** the macOS/Linux `python` fix is a **symlink, not a shell alias** (a raw spawn ignores aliases); no `os.execv` on the Windows re-exec path (orphans the host stdio pipe → MCP crash); bootstrap stdlib-only + stderr-only (stdout corrupts the JSON-RPC handshake). GUI hosts are an explicit out-of-scope residual (fallback only), not a silent gap.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-24: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, reality-checker, qa-reviewer; rotating-seat: architecture-reviewer; scope: re-reviewed after the operator reframed to dual co-equal goals + a runtime-entry sweep (full convergence, all configs incl. Codex/Air) + a dedicated red-team of the interim `uv` command + real-machine PATH checks; command decision settled on committed `command: "python"` with a setup symlink on macOS/Linux, CLI-host-scoped; strongest-challenge: the `uv` interim was red-teamed out — `uv` is absent on the team's machines (network install + runtime SPOF + throwaway resolution hop) and *worst* on the GUI-host launchd-PATH axis, while `python` is present-but-misnamed (a network-free symlink) and the venv is already resolved PATH-independently by the bootstrap; the residual GUI-host PATH problem is scoped out with a gitignored absolute-venv-path fallback (AC-6 exercises it); single-resolver scan-test invariant (1p7pl AC-5) + on-disk no-pathed-launcher guard (1p7pm AC-3) retained; strongest-alternative: absolute-venv-path as the *default* — rejected (gitignored/per-machine, sacrifices the committed shared config + Codex auto-trust) but kept as the GUI fallback)

- **Operator prepare-review (interrogation) — 2026-06-24:** four findings applied before re-ready. **P0** setup circularity — `setup-wavefoundry`/`setup-index` are carved out of the `python` flip; they run on system `python3`→`python` *before* the symlink exists, and `setup_wavefoundry.py` creates the venv then the symlink before the fleet relies on `python` (`1p7pm` Req-5/Req-4/AC-4/AC-5). **P1** fresh-bootstrap path locked with a test (`1p7pl` Req-4/AC-5: no venv + no symlink + `python3 setup_wavefoundry.py` ⇒ venv created, deps, symlink runs; bootstrap no-ops, never blocks `ensure_deps`). **P1** hook inner spawns use `sys.executable`, not `python3` (`1p7pl` Req-5/Req-6 — the third interpreter tier). **P2** dashboard forwarder uses `python` + the self-detach child spawn uses `sys.executable` (`1p7pn` Req-3/AC-3). The three-tier interpreter model (setup=system python / configs=`python` / inner spawns=`sys.executable`) is recorded in `1p7pb-adr`.

## Review Evidence

- wave-council-readiness: approved 2026-06-24 — inline readiness review across 4 stances + a dedicated red-team of the interim `uv` command; verdict READY. Decision iterated (per-OS-token → bare-python → uv → **committed `command: "python"` + setup symlink, CLI-host-scoped**) under real-machine evidence: macOS has `python3` not `python`, Windows has `python` not `python3`, neither has `uv`; raw process spawn ignores shell aliases (→ symlink, not alias); CLI hosts inherit the shell PATH (→ symlink visible) while GUI hosts don't (→ documented residual + gitignored absolute-path fallback). Scope = full convergence (all configs incl. Codex via render_agent_surfaces + Air, bin forwarders, hook-shim/resolver retirement, dashboard daemonization) locked by the single-resolver scan test. Standing findings: no `os.execv` on Windows; bootstrap stdlib-only/stderr-only; nt real coverage = AC-6. All scope/decision changes operator-directed, not silent.
- wave-council-delivery: approved 2026-06-25 — two inline pre-close delivery reviews; verdict PASS. First review over the original three (`1p7pl`/`1p7pm`/`1p7pn`): the shared `venv_bootstrap` consolidation, the byte-identical `command: "python"` config cutover across all hosts incl. Codex/Air, the setup `ensure_python_resolves` symlink/heal, the bin forwarders, the git-hook bootstrap, `.gitattributes`, and dashboard self-detach. Findings fixed + test-locked: machine-mutation test hygiene (heal mocked / `WAVEFOUNDRY_SKIP_PYTHON_HEAL` opt-out so the suite never touches the real `~/.local/bin`); symmetric Windows-detach on both rendered reindex spawns; `run_tests` adoption-scan; the TLS operator-env restore made symmetric via try/finally (a clobbered trust anchor can no longer leak on failure). Second review over the three late-admitted (`1p7s6`/`1p7tz`/`1p7ww`): host-agent TLS CA discovery, the `wf` dispatcher hard cutover, and MCP-first upgrade routing. Findings fixed + test-locked: the `write_text` newline MAJOR (default `newline=None` would corrupt a native-Windows re-render — doubled CR in `wf.cmd`, CRLF shebangs on bash/`.py` — fixed to `newline=""`, verbatim terminators); the three missed dynamic `bin/wrapper` references (the real `maybe_docs_lint` hook breakage + two probes), now routed to `sys.executable`/`_preferred_python` and guarded by a strengthened dynamic-bin scan; the reconciliation-recommendation wiring test. Security clean throughout: TLS verification is never disabled (only the trusted CA bundle is selected); `test_no_path_disables_tls_verification` holds. Full parallel suite green (only the known pre-existing in-suite secrets flake). Remaining gates are operator-owned: the `1p7pm` AC-6 real-host smoke and final operator closure signoff.
- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.
