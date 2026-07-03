# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-03

wave-id: `1p9pe post-release-followup-hardening`
Title: Post Release Followup Hardening

## Objective

Close the concrete follow-up hardening items discovered during the 1.10.1 close and release path. When this wave closes, Python parse warnings name their real source files, renderers preserve operator-owned host config, post-write lint uses the cheap incremental path, and model-warm socket stalls fail in-thread before the wall-clock watchdog has to abandon the worker.

## Changes

Change ID: `1p9p6-bug python-parse-filename-and-invalid-escape`
Change Status: `planned`

Change ID: `1p9p7-bug renderer-overwrite-safety`
Change Status: `planned`

Change ID: `1p9p8-enh post-write-lint-incremental-changed`
Change Status: `planned`

Change ID: `1p9p9-enh model-warm-hf-hub-socket-timeouts`
Change Status: `planned`

Change ID: `1p9pk-enh prepare-council-verification-rigor`
Change Status: `planned`

## Participants

| Role | Responsibility |
|------|----------------|
| implementer | Implement the four scoped framework hardening changes and keep changes confined to the admitted docs. |
| code-reviewer | Review script, renderer, chunker/indexer, and server changes for correctness and local-pattern fit. |
| qa-reviewer | Reconcile required ACs, bug-fix coverage, regression tests, full suite, and docs-lint evidence. |
| architecture-reviewer | Confirm docs-lint gate boundaries, renderer ownership boundaries, and indexer/setup control flow remain coherent. |
| security-reviewer | Review renderer write/removal safety, file/path handling, environment-variable scope, and parser diagnostics. |
| performance-reviewer | Review post-write lint latency, indexer parse-sweep cost, model-warm timeout behavior, and setup/index hot paths. |
| wave-council | Synthesize prepare and delivery verdicts. |

## Wave Summary

Four scoped post-release hardening changes: one source-level invalid-escape fix plus indexing-path diagnostics, one renderer overwrite-safety fix, one post-write lint latency reduction, and one setup model-warm socket-timeout improvement. This wave intentionally stays on the release-follow-up defects and does not resume the larger cross-host skills roadmap.

## Journal Watchpoints

- Follow-up from `1p9j0` / `1p9jn` / `1.10.1`: keep the wave narrow and do not fold in unrelated cross-host skills work from planned wave `1p6lp`.
- Watchpoint (`1p9p7`): run any self-render only after the `.codex/config.toml` non-destructive merge fix is in place, so the restored `wave_close` approval guardrail is not clobbered again.
- Watchpoint (`1p9p8`): preserve the full-corpus docs-lint gates for `wave_validate`, prepare, review, close, and install audit; only the advisory post-write attachment moves to `--changed`.
- Watchpoint (`1p9p9`): HF Hub socket timeouts complement the model-warm wall-clock deadline; do not weaken the deadline or overstate the socket-timeout scope.
- Coordination: `setup_index.py` is touched by `1p9p9`; renderer files are touched by `1p9p7`; `server_impl.py` is touched by `1p9p8`; chunker/graph-indexer files are touched by `1p9p6`, so the four changes can proceed mostly independently and join at the test pass.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-03: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the wave bundles four independent release-follow-up hardenings that touch different hot paths, so the implementation must keep boundaries strict — especially preserving full-corpus lifecycle lint gates while changing only the advisory post-write path, and preserving operator-owned renderer config while still keeping framework-managed config current; strongest-alternative: split into four tiny waves, rejected because all four plans are already scoped, independent, and share the same immediate post-release hardening context. Readiness disposition: plans are complete enough for implementation, QA is required for the two bug fixes and AC-heavy enhancements, architecture/security/performance review are selected for the affected boundaries, and `1p6lp` remains out of scope.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-03: READY-WITH-NOTES (independent re-review; supersedes the PASS above)** (moderator: wave-council; primer-depth: standard; seats actually run: red-team (adversarial primer, fixed), reality-checker (site-verification), qa-reviewer (AC-testability); rotating-seat: none additional. This corrective pass was run because the PASS above was thin — its recorded roster (red-team/architecture/qa/reality-checker + a duplicated security-reviewer) did not match its recorded evidence (code/security/performance), and it verified nothing against the tree. The three lanes here found defects the thin pass missed; `1p9pk` was admitted to fix the machinery that allowed it. strongest-challenge: three of the five plans were authored by the coordinating agent, so independent code-grounded verification was the load-bearing check — and it flipped one plan to NOT-READY that green tests would not have caught. strongest-alternative: split the NOT-READY `1p9p9` out until its mechanism is redesigned — declined; kept in-wave with its Requirement/AC corrected in place.)
  - **`1p9p8` — READY after two factual corrections (applied):** the plan cited a nonexistent helper `_lint_changed` (real name `_run_incremental_checks`, `wave_lint_lib/cli.py:168`) and a "five lifecycle callers" census that is actually six (omitted `wave_audit`; `run_validate` callers confirmed at `server_impl.py:3036,6251,6432,6501,9042,9267,9725`). Core edit site correct; corrected in the change doc. qa also broadened AC-3 to guard all gates (not "at least one") and flagged AC-4/AC-5 vacuity edges.
  - **`1p9p9` — NOT-READY as written; mechanism corrected in place:** the `os.environ` scoping approach is a verified no-op — `huggingface_hub.constants.HF_HUB_DOWNLOAD_TIMEOUT` is read once at import (empirically: env set before import → constant honored; env mutated after import → constant unchanged), and the warm imports huggingface_hub before the context manager runs. The codebase already documents this exact hazard for the sibling CA case (`setup_index.py:772-782` `close_session` workaround). Corrected to a scoped monkeypatch of `huggingface_hub.constants.*` with an effectiveness AC asserting the constant reflects the configured value during the warm.
  - **`1p9p6` — READY-WITH-NOTES; causal story unsettled:** framework test files are excluded from indexing (`indexer.py:1013/1175`) yet `test_wf_cli.py` appears in `meta.json`, so which pass emitted the observed `<unknown>:293` is not confidently established. Both fixes (source escape + `filename=`) are individually correct (empirically: `filename=` renames the warning from `<unknown>` to the real path), but the plan must not rest on the causal claim — added an effectiveness check that a real rebuild over a fixture invalid-escape source now names its path.
  - **`1p9p7` — READY-WITH-NOTES:** copilot-removal gating is clean; the marker-region `.codex/config.toml` fix carries a TOML migration hazard on this self-hosted repo (an unmarked pre-existing `[mcp_servers.wavefoundry]` table + a marker-absent upsert would produce a duplicate-table → invalid TOML). Add a requirement/AC that the existing unmarked framework table is absorbed, and that the self-rendered file parses as valid TOML (round-trip), plus a copilot-in-scope-still-renders guard AC.
  - **`1p9pk` — new, admitted this pass:** fixes the prepare-council machinery that allowed the thin PASS — de-dup the rotating seat in the verdict template, add a roster⇄evidence consistency validator, and require code-grounded verification in the brief/seed.
- **`1p9pk` independent readiness review [prepare-council] — 2026-07-03: READY-WITH-NOTES, notes applied** (seats actually run: red-team (adversarial + validator-feasibility, resumed after a session-limit interruption), reality-checker (site-verification); moderator: this coordinating agent as wave-council. Applying `1p9pk`'s own discipline to itself since it was self-authored.) Reality-checker: all seven code/seed/wave claims VERIFIED against the tree (the duplicated-`security-reviewer` template output matches `1p9pe`'s recorded roster verbatim — strong corroboration). Red-team's load-bearing result: the roster⇄evidence validator IS feasible (so READY, not NOT-READY), but the plan had **not stated the rule that makes it non-vacuous** — the loose "corroborated by checkpoint prose" reading lets a seat self-certify inside its own verdict line. Notes applied in-doc: (1) AC-3/AC-4 + Requirement 2 now pin the exact rule — literal role-token match; corpus = Prepare-Review-Evidence ∪ Review-Evidence ∪ Review-Checkpoints minus the matched verdict line's own text and minus Participants/Changes; tolerance set `{red-team, wave-council}`; (2) the AC-3 test fixture must be a **frozen pre-corrective** `1p9pe` snapshot because the live wave.md now self-heals (the corrective checkpoint bullet names reality-checker/qa in prose); (3) the "mechanical backstop for code-grounded verification" claim is bounded to *unnamed/unevidenced* seats (the validator cannot detect shallow, zero-code review); (4) seed target committed to `237` Phase-2 per-seat protocol (`215` is moderator orchestration; `007` gets a pointer); (5) the `seed_edit_allowed` gate is now named in Tasks; (6) AC-6's self-containment claim corrected — it was itself an unverified assertion (no test enforces internal-ID absence; seed 237 already carries a bare `(wave 1304x / 1305d)` note and the suite is green), reframed as a manual discipline. AC-1 de-dup confirmed information-lossless (the "served as both" signal lives in the separate `rotating-seat:` field). Residual UNREVIEWED: red-team did not fully read the shipped-reference test internals (flagged for the implementer); noted that the corrective READY-WITH-NOTES verdict line itself is invisible to the machine parser (regex matches only PASS/PASS WITH NOTES/BLOCKED) — acceptable, the validator reads the thin PASS line it is meant to police.

## Review Evidence

- wave-council-readiness: approved 2026-07-03 — READY. Four admitted post-release follow-up changes are wave-owned and narrow: invalid-escape + parse filename diagnostics (`1p9p6`), renderer overwrite/removal safety (`1p9p7`), post-write lint incrementalization without weakening lifecycle gates (`1p9p8`), and HF Hub socket timeouts as a complement to the model-warm deadline (`1p9p9`). Required review lanes are selected; no product-owner acknowledgment is required because these are framework hardening and operational correctness changes, not product UX changes. The larger cross-host skills wave `1p6lp` is explicitly out of scope.
- operator-signoff: <approved when operator confirms closure>

## Prepare Review Evidence

- code-reviewer: approved 2026-07-03 — plan is implementable and keeps edits localized to the named framework scripts/tests/rendered surfaces. The main coordination risk is shared test files, and the wave record captures the intended independent workstreams and join-at-suite verification.
- security-reviewer: approved 2026-07-03 — plan identifies the relevant trust/safety boundaries: preserving operator-owned Codex config, avoiding accidental Copilot hook removal, scoping HF Hub timeout environment variables, and keeping parser diagnostics as observability rather than execution. No new unbounded user-input parsing or broader file-access surface is introduced by the plan.
- performance-reviewer: approved 2026-07-03 — plan focuses performance-sensitive work where it belongs: post-write lint changes only the advisory path to `--changed`, lifecycle gates stay full-corpus, the invalid-escape sweep is compile-only and bounded to tracked Python files, and HF socket timeouts complement rather than replace the existing model-warm wall-clock watchdog.

## Dependencies

- No external wave dependencies.
