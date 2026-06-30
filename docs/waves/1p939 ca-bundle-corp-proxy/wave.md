# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-30

wave-id: `1p939 ca-bundle-corp-proxy`
Title: CA Bundle Corp-Proxy Coverage

## Objective

Close the TLS-trust gap reported behind corporate TLS-intercepting proxies: model downloads
triggered outside `wf setup` (MCP `wave_index_build`, dashboard file-watcher, background index
refresh) currently bypass the CA trust-bundle resolution that `wf setup` already applies, causing
`CERTIFICATE_VERIFY_FAILED`. When this wave closes, every model-download launcher resolves the same
trust bundle, not just `wf setup`.

## Changes

Change ID: `1p92t-bug ca-bundle-non-setup-launchers`
Change Status: `implemented`

Completed At: 2026-06-30

## Wave Summary

Wave `1p939` (CA Bundle Corp-Proxy Coverage) delivered one change: Apply CA trust bundle on non-setup model-download launchers. Notable adjustments during implementation: Apply CA trust bundle on non-setup model-download launchers: Scope expanded after pre-implementation MCP exploration found `server_impl.py` raw `TextEmbedding` call sites not covered by the original plan (Level 3 finding); change doc and wave record updated before any code edit.; Apply CA trust bundle on non-setup model-download launchers: Implemented: `ensure_ca_bundle_applied()` / `raise_with_ca_bundle_diagnostic()` added to `setup_index.py`; called from `accel_embedder.py`'s two download functions and `server_impl.py::_ensure_model_cached()`'s embedding branch. All tasks and ACs complete.; Apply CA trust bundle on non-setup model-download launchers: Delivery-phase Wave Council review (red-team primer + 4 fixed seats + rotating seat + synthesis, plus a separate code-reviewer lane) found a fourth unfixed call site (`indexer.py`) falsifying AC-1/AC-2/AC-6, plus a ladder-parity gap and a swallowed-diagnostic gap — NEEDS REVISION verdict, qa-reviewer NOT READY. Fixed: wired `indexer.py::_text_embedding_cached_first` (AC-7); added `setup_index.retry_with_ca_bundle_ladder()` reactive fallback wired into all four call sites; added logging at the two `accel_embedder.py` swallow points; lock-protected `_ca_bundle_apply_attempted`. Corrected AC-1/AC-2/AC-4/AC-6 evidence text. Extended test coverage to exercise the real production call graph, not just the inner constructor in isolation.

**Changes delivered:**

- **Apply CA trust bundle on non-setup model-download launchers** (`1p92t-bug ca-bundle-non-setup-launchers`) — 7 ACs completed. Key decisions: Apply the CA bundle at the model-download choke point inside `accel_embedder` (`_hf_download_cached_first` / `_ensure_fastembed_model_cached`), reusing `setup_index`'s existing resolution functions.; Accept a one-way (non-restoring) `os.environ` mutation from `_apply_ca_bundle()` at the new `accel_embedder` call site, documented inline rather than wrapped in `_warm_model`'s try/finally restore discipline.
## Participants

| Lane | Trigger |
| ---- | ------- |
| `code-reviewer` | Change edits `.wavefoundry/framework/scripts/*.py` (`setup_index.py`, `accel_embedder.py`, `server_impl.py`) |
| `qa-reviewer` | Required for bug-fix changes (`review_policies.require_qa_reviewer_for_bug_fixes: true`); also has an AC priority table |

## Journal Watchpoints

- Watchpoint: field-reported on macOS behind a Zscaler proxy (2026-06-30); see memory
  `project_corporate_proxy_ca_bundle_setup_only` for the full repro and root-cause trace.
- Watch for the circular-import risk noted in the change doc's Risks table: `accel_embedder` must
  import `setup_index` function-locally (mirroring `setup_index.py:1032`), not at module level.
- No reporter machine available in this environment to validate the real corporate-proxy repro;
  verification relies on unit tests forcing a cert-verify failure plus a no-corporate-env regression
  check (see change doc Tasks).

## Prepare Review Evidence

- `qa-reviewer` signoff: approved — ACs are concretely testable (AC-1/2/3/5/6 specify exact mocked
  conditions and observable outcomes; AC-4 names the failure mode, message-substring assertion to be
  tightened at implementation, not blocking). Tasks include explicit positive (host-agent CA var
  present, forced cert-verify failure) and negative (plain env, no regression) test coverage for both
  the `accel_embedder` and `server_impl` call sites, satisfying the bug-fix test-coverage policy. AC
  priority table fully populated, no placeholders. Re-reviewed 2026-06-30 after scope correction
  (AC-6 added); no new gaps.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: pre-implementation MCP exploration found server_impl.py has two independent raw TextEmbedding call sites not covered by the original accel_embedder-only choke-point theory, and the correction itself needed verification that no further undiscovered call site remains; strongest-alternative: route non-setup downloads through _warm_model directly instead of factoring a new thinner helper, reusing its proven retry+restore path at the cost of pulling in setup-tuned candidate-iteration and print-diagnostics behavior not suited to a background indexer call)

- **Delivery-phase Wave Council [delivery-council] — 2026-06-30: NEEDS REVISION** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: ensure_ca_bundle_applied() mirrors only _warm_model's proactive host-agent-CA-var step, never its reactive OS-trust-store-candidate retry, so the wave's claim of full ladder parity for non-setup launchers overclaims what shipped — confirmed unanimously by all four fixed seats via direct code read; strongest-alternative: add the reactive OS-candidate fallback (primer/rotating-seat consensus, additive and low-risk) and — found independently during Phase 2 by qa-reviewer, reality-checker, and the separate required code-reviewer lane, not by the primer or rotating seat — wire ensure_ca_bundle_applied()/raise_with_ca_bundle_diagnostic() into a fourth, previously undiscovered raw model-download call site at indexer.py::_text_embedding_cached_first, which every named launcher (wave_index_build, dashboard watcher, background refresh) reaches whenever GPU acceleration is unavailable and which falsifies AC-1/AC-2/AC-6 as currently evidenced; qa-reviewer (required lane) verdict NOT READY and code-reviewer (required lane) verdict needs-revision both keep blocking status independent of the anonymized merit-weighing pass per the council's non-waiver guard; AC-5 (TLS verification never disabled) confirmed unanimously across all sources, no security regression found)

  **Blocking findings (qa-reviewer + code-reviewer, required lanes):**
  1. `indexer.py::_get_embedder()`/`_text_embedding_cached_first()` (`indexer.py:2066-2119`) is a fourth raw model-download call site (`text_embedding_cls(...)`, parameter-aliased — missed by the Decision Log's literal `TextEmbedding(` token sweep), never wired to `ensure_ca_bundle_applied()`. It is reached whenever `accel_embedder.make_embedder()` returns `None` (no GPU/CoreML/CUDA/ROCm/DML offload — the common case on CPU-only/Linux/WSL2/CI hosts, and the fallback even on GPU-capable hosts). All three named launchers route here on that hardware class: `wave_index_build(content='code'|'docs')` spawns `indexer.py` directly (only `content='all'`/`'graph'` route through the protected `setup_index.py`, confirmed at `server_impl.py:3467-3475`); the background index refresh spawns `indexer.py` directly (`server_impl.py:4794-4797`); the dashboard file-watcher loads `indexer.py` in-process (`dashboard_server.py:50-64`). Falsifies AC-1, AC-2, and AC-6 as currently evidenced — independently confirmed firsthand by the reviewing agent (`indexer.py` has zero `import setup_index`; `wave_index_build` routing read directly).
  2. AC-1/AC-2/AC-6 evidence citations and the Decision Log's "exhaustive code_keyword sweep" claim need correction once the indexer.py fix lands — the literal-token search for `TextEmbedding(` structurally cannot match `indexer.py`'s `text_embedding_cls(...)` parameter-aliased construction; a broader sweep is needed to rule out a fifth site before closing.

  **Required before approved (non-blocking on the AC-1/2/6 fix, but required for an honest record):**
  - Either (a) implement a reactive `_os_trust_store_candidates()` fallback in `ensure_ca_bundle_applied()` gated on a confirmed cert-verify failure (primer + rotating-seat consensus alternative — `ensure_ca_bundle_applied()` only mirrors `_warm_model`'s *proactive* host-agent-var step, never its *reactive* OS-trust-store/certifi-default retry ladder), or (b) reword the wave Objective and change-doc Requirement 1 to scope explicitly to the proactive host-agent/operator CA-var rung, matching what AC-1/AC-2/AC-3's actual tests cover.
  - Correct AC-2/AC-4 evidence-table language: `raise_with_ca_bundle_diagnostic()` is operator-visible only at the `server_impl.py::_ensure_model_cached` call site (via `_wf_log` in `_download_worker`'s except clause); it is silently swallowed with zero logging at both `accel_embedder.py` call sites (`_resolve_clean_onnx`, `_resolve_reranker_cpu_files`) and never invoked inside `_ensure_fastembed_model_cached`.

  **Advisory, not blocking:** prefer `_merged_trust_bundle()` over the single-file `_host_agent_ca_bundle()` at the long-lived MCP server call site (one-way single-PEM mutation risk in a long-lived process, security-reviewer); `_ca_bundle_apply_attempted`'s check-then-set is not lock-protected (benign race between the embedding-cache and background-download worker threads, code-reviewer).

  Full council methodology: red-team primer (standard depth, 3 stances) → 4 fixed seats (architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, each addressing the primer) → rotating fifth seat (security-reviewer, best-alternative framing) → anonymized-merit synthesis. Independently corroborated by the moderator via direct `code_read`/`code_keyword` before recording (indexer.py call site + `wave_index_build` routing confirmed firsthand, not taken on agent claim alone). Full framework test suite (3,715 tests, 39 files) passes with the diff applied — consistent with, not contradictory to, the findings above (existing tests exercise the new helpers in isolation, not the real production call graph). Do not call `wave_close` until the blocking findings are resolved and a re-review confirms; operator closure confirmation is separately required per standing policy regardless.

  **Fixes applied — 2026-06-30 (post-review):** all blocking and required-before-approved findings above had corresponding code fixes applied — `indexer.py::_text_embedding_cached_first()` wired to `ensure_ca_bundle_applied()` (AC-7, fourth call site); `setup_index.retry_with_ca_bundle_ladder()` added (reactive OS-trust-store-candidate fallback, closes the ladder-parity gap); a log line added at the `accel_embedder.py` swallow points so the AC-4 diagnostic is operator-visible; `_ca_bundle_apply_attempted` lock-protected (advisory finding). A broader call-site sweep (beyond the literal `TextEmbedding(` token that missed `indexer.py`) found two additional `TextEmbedding(` sites, both confirmed offline-only by direct read — no fifth gap. AC-1/AC-2/AC-4/AC-6 evidence corrected and AC-7 added in the change doc.

  **Independent re-review — 2026-06-30 (code-reviewer + qa-reviewer lanes, not a full council re-pass):** qa-reviewer independently re-verified every corrected AC against code/tests firsthand (re-ran the full suite, re-traced `wave_index_build`'s routing to confirm `content='code'`/`'docs'` really do hit bare `indexer.py`, re-checked the no-fifth-gap claim) and rendered **READY** — the qa-reviewer required lane is now satisfied. code-reviewer independently found one residual gap the qa-reviewer checklist didn't cover: the first fix pass had wired `retry_with_ca_bundle_ladder()` into only 3 of the 4 named call sites — `accel_embedder._ensure_fastembed_model_cached` had gained only the proactive `ensure_ca_bundle_applied()` call, contradicting the wave's "wired into all four call sites" claim. This is now fixed (`accel_embedder.py:162-178`, full ladder + logging wired in, tests updated), and the full suite re-confirmed at 3,726 tests OK. No other regressions found by either lane; AC-5 (TLS verification never disabled) holds. **Net: all four prior findings (4th call site, ladder-parity gap, swallowed diagnostic, lock race) are now resolved, plus the one gap the re-review itself surfaced.** Operator closure confirmation is still separately required per standing policy before `wave_close`.

- Prepare wave — readiness verdict: READY (re-verified 2026-06-30 after scope correction). Rotating
  seat selected as `security-reviewer` (trust boundary / TLS-CA content), confirming the system's own
  council-brief recommendation over an initial manual `performance-reviewer` pick. Original strongest
  challenge (one-way `os.environ` mutation leak risk) resolved: confirmed it does not apply to
  `accel_embedder`/indexer launcher processes (short-lived, no subsequent `uv`/`pip` invocation
  in-process) — captured as an explicit Task + Decision Log entry. Scope-correction strongest
  challenge resolved: exhaustive `code_keyword` search across `**/*.py` for both `hf_hub_download(`
  and `TextEmbedding(` (non-truncated, full result sets) confirms no remaining unaccounted-for raw
  model-download call site. Final in-scope set: `accel_embedder.py` ×2 functions plus
  `server_impl.py::_ensure_model_cached()`'s embedding branch (3 call sites total);
  `setup_index._warm_model` is already correctly covered and stays out of scope.
  `WaveIndex._get_embedder()` was flagged in an interim correction and then excluded after a full
  read showed it never makes a network call (`local_files_only=True` + `HF_HUB_OFFLINE=1` always) —
  see the change doc's second Decision Log correction. AC priority recorded on the change doc (5
  required, 1 important). No product-owner acknowledgment required — internal bug fix, no
  product-facing behavior/UX change.

- pre-implementation-review: passed (2026-06-30) — highest risk was scope incompleteness (an
  undiscovered raw model-download call site); addressed by an exhaustive non-truncated `code_keyword`
  sweep for `hf_hub_download(`/`TextEmbedding(` across `**/*.py` before the first edit, which found
  and folded in the `server_impl.py` call sites (AC-6) rather than missing them.

## Review Evidence

- wave-council-readiness signoff: approved — prepare-council — moderator=wave-council, primer-depth=standard, seats=[red-team(primer), architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer(rotating)], rotating-seat=performance-reviewer, strongest-challenge="one-way os.environ CA-bundle mutation in the new accel_embedder call site could leak a corp-only trust anchor into a later uv/pip call in the same process, unlike _warm_model's try/finally restore", strongest-alternative="route non-setup downloads through _warm_model() directly instead of factoring a new thinner helper, reusing its proven retry+restore path at the cost of pulling in setup-tuned diagnostics not suited to a background indexer call"
- wave-council-delivery signoff: needs-revision — moderator=wave-council, primer-depth=standard, seats=[architecture-reviewer, security-reviewer, qa-reviewer(required, NOT READY), reality-checker, security-reviewer(rotating)], rotating-seat=security-reviewer, strongest-challenge="ensure_ca_bundle_applied() implements only the proactive host-agent-CA-var rung of the CA ladder, never the reactive OS-trust-store-candidate retry _warm_model performs on a confirmed cert-verify failure, so a corporate-proxy environment whose only working trust rung is an OS bundle file remains broken for non-setup launchers even though wf setup succeeds there", strongest-alternative="add a thin reactive fallback to ensure_ca_bundle_applied() that walks _os_trust_store_candidates() only on a confirmed cert-verify failure, reusing _warm_model's proven candidate logic minus its print/restore machinery; separately and more urgently — discovered independently by the qa-reviewer seat, reality-checker seat, and the required code-reviewer lane, not by the primer or rotating seat — wire ensure_ca_bundle_applied() into indexer.py::_text_embedding_cached_first, a fourth raw model-download call site hit by all three named launchers whenever GPU acceleration is unavailable, never covered by this wave"
- qa-reviewer signoff (superseded, original delivery-council pass): NOT READY — required AC-1/AC-2/AC-6 evidence did not cover the real production call graph; see Review Checkpoints delivery-council entry for the AC-by-AC breakdown
- code-reviewer signoff (superseded, original delivery-council pass): needs-revision — see Review Checkpoints delivery-council entry
- `qa-reviewer` signoff (independent re-review, 2026-06-30): READY — every corrected AC (AC-1 through AC-7) independently re-verified against code/tests firsthand (full suite re-run, `wave_index_build` routing re-traced, no-fifth-gap claim re-checked); required qa-reviewer lane satisfied. See Review Checkpoints "Fixes applied" / "Independent re-review" entry.
- code-reviewer signoff (independent re-review, 2026-06-30): approved-with-notes — found and the implementer fixed one residual gap (`_ensure_fastembed_model_cached` missing ladder wiring) not covered by the qa-reviewer's AC checklist; no other regressions found, AC-5 holds. See Review Checkpoints "Independent re-review" entry.
- operator-signoff: approved — 2026-06-30, operator explicitly requested closure after the independent re-review

## Dependencies

- No external wave dependencies.
