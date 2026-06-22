# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-06-22

## Just closed — `1p75h design-system-foundation` (CLOSED 2026-06-22)
4 changes delivered: `1p6z6` (token extraction), `12atj` (token build pipeline), `1p72v` (WFDS primitive module + dashboard tokenization + operator nav polish), `1p799` (design-system adopt-existing / `external-reference` mode). Both councils recorded (readiness + delivery, incl. `1p799` addenda). Suite was 3367 green at close.

## Vendor-neutrality scrub — DONE (operator-directed, separate concern)
External consumer-project names (`aceiss`/`teton`/`solaris`/project-`javaagent`) removed from the **packaged + live surface** (`.wavefoundry/framework/**`, `docs/design-system/**`, `docs/architecture/design-system.md`) **and the repo-root `CHANGELOG.md`** (which build_pack ships into every package at `.wavefoundry/CHANGELOG.md` — caught by grepping the built zip). Historical `docs/waves`/`docs/plans`/`docs/agents/journals` intentionally left intact. Built-zip grep gate = 0.

## Local downstream test build
`~/.wavefoundry/dist/wavefoundry-1.8.0.p79q.zip` — version `1.8.0+p79p/q`, **local only** (not tagged/pushed). Verified ships zero external-project names. `framework/VERSION` reverted to `1.7.3+p6n0` (no release). Operator was validating it against a Java-agent consumer → produced the factor-surface feedback that became `1p79y`.

## NEW wave — `1p79y factor-surface-integrity` (PLANNED, not started)
One change `1p79x-enh factor-surface-integrity`, admitted. From downstream feedback (pack `1.8.0+p79p`); a **pre-existing** gap (~1.6.x), independent of `1p75h`. All 3 reported issues verified against code. Fixes: (1) `factor_review`-keyed declared-but-missing validator in `wave_lint_lib/wave_validators.py` (canonical-existence + orphan-wrapper + wrapper-frontmatter, replacing the static 4-factor list — reuses the `1p799` pattern); (2) `seed-238` factor-aware reconciliation; (3) `seed-160` factor backfill; (4) `render_platform_surfaces.py` frontmatter audit. 9 ACs, priorities proposed. `next_action: prepare_wave`. NOT yet prepared/implemented.

## Commit / push state (operator-owned — NOT yet requested)
Everything since `origin/main` `64b340f` is **uncommitted**: all of `1p75h` (4 changes + close status) + the vendor scrub + `CHANGELOG.md` + the `1p79y`/`1p79x` plan+wave. Push needs the **`coryhacking`** gh account (`gh auth switch --user coryhacking`, push, switch back). No `git commit` without explicit operator request in the current turn.

## Standing constraints
- `~/.wavefoundry/venv/bin/python`; tests bytecode-free. Gates open-before/close-after (`framework_edit_allowed`, `seed_edit_allowed`). Signoff/wave-record lines: no `<` angle brackets. Commit msgs: no AI attribution / no `Co-Authored-By`. Wave watchpoints must contain a marker word (`watchpoint`/`follow-up`/`block`/`retry`/`defer`/`move`).
- Dashboard served off-disk at `http://127.0.0.1:8821/dashboard.html`.

## Other planned, not started
- `1p6lp cross-host-skills` (`1p6lo` + `1p6lw`).
