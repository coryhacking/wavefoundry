# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-03

wave-id: `1p337 config-key-back-compat-hotfix`
Title: Config-Key Back-Compat Hotfix — ship 1.4.0

## Objective

Single-change hotfix wave addressing a downstream-operator-reported transition-state defect shipped in `1p2q3` (packaged across 1.3.27–1.3.31) and propagated through `1p31b` (1.3.32). Seed prose was renamed (`wave_council_policy` → `wave_review`; `wave_execution` → `wave_implement`) but the runtime reader at `server_impl.py:1280` and the `docs-lint` required-keys check at `wave_lint_lib/constants.py:41` still consume the legacy names with no fallback. Consumers who follow the upgraded seed guidance and rename their `workflow-config.json` keys silently lose Wave Council enforcement AND fail docs-lint. The fix is reader-side back-compat with new-key precedence and a one-shot deprecation note on legacy-key read.

This wave is intentionally narrow: one change, bounded ~10 LOC across two files plus tests. Created and shipped in a single session to minimize the transition-gap exposure window.

## Changes

Change ID: `1p336-bug workflow-config-renamed-keys-missing-reader-back-compat`
Change Status: `implemented`

Change ID: `1p33b-doc migrate-active-docs-to-canonical-renamed-config-keys`
Change Status: `implemented`

Change ID: `1p33f-enh default-enable-wave-council-in-project-skeleton`
Change Status: `implemented`

Change ID: `1p33i-enh unify-review-surfaces-as-specialists`
Change Status: `implemented`

Completed At: 2026-06-03

## Wave Summary

Wave `1p337` (Config-Key Back-Compat Hotfix — ship 1.4.0) delivered 4 changes: Workflow-Config Renamed Keys Missing Reader-Side Back-Compat, Migrate Active Docs To Canonical Renamed Config Keys, Default-Enable Wave Council In Project Skeleton, and Unify Review Surfaces As Specialists.

**Changes delivered:**

- **Workflow-Config Renamed Keys Missing Reader-Side Back-Compat** (`1p336-bug workflow-config-renamed-keys-missing-reader-back-compat`) — 12 ACs completed. Key decisions: New-key-first precedence with legacy fallback (read `wave_review`; if absent, read `wave_council_policy`) — the new key wins when both are present; One-shot deprecation note (fires at most once per process) on legacy-key read
- **Migrate Active Docs To Canonical Renamed Config Keys** (`1p33b-doc migrate-active-docs-to-canonical-renamed-config-keys`) — 16 ACs completed. Key decisions: Migrate self-host `docs/workflow-config.json` to new key names as part of this change, not deferred to a future cleanup; Add `(formerly wave_council_policy)` annotation only on 1-2 high-traffic operator surfaces, not on every reference
- **Default-Enable Wave Council In Project Skeleton** (`1p33f-enh default-enable-wave-council-in-project-skeleton`) — 16 ACs completed. Key decisions: Default `enabled: true` only — do not set `required_for_all_waves: true` in the skeleton; Admit to `1p337` rather than create a new wave for 1.3.34
- **Unify Review Surfaces As Specialists** (`1p33i-enh unify-review-surfaces-as-specialists`) — 16 ACs completed. Key decisions: Move all three review surfaces (red-team, wave-council, archetype-council) under `docs/agents/specialists/`; Name files after the council/surface, not the moderator function (`wave-council.md`, not `wave-council-moderator.md`)
## Participants

- `code-reviewer` — required (framework script edits in `server_impl.py` and `wave_lint_lib/`)
- `qa-reviewer` — required (regression discipline on the six test scenarios per AC-10)
- `architecture-reviewer` — required (back-compat fallback semantics, alias-tuple data structure)
- `security-reviewer` — not required (no trust boundary touched, no new file write surface)
- `red-team` — Wave Council adversarial primer per `wave_review.enabled` policy
- `reality-checker` — required (Wave Council Phase 2 fixed seat)
- `council-moderator` — required (Wave Council coordinator)

Rotating fifth Phase 2 seat: `reality-checker` is already a fixed seat; the rotating fifth defaults to `senior-engineering-challenger` since this is a back-compat surface where claim-correctness matters more than prose precision.

## Journal Watchpoints

- **Single-change scope discipline:** this wave is intentionally narrow. Resist admitting adjacent fixes (a broader cross-cut audit for other seed-vs-runtime drift) — those belong in a separate follow-on. The bounded scope is what makes this shippable in one session.
- **No-silent-break promise (AC-9) blocks declaring done:** existing consumer configs with legacy keys must work exactly as before. Verify this explicitly during implementation by running the test suite against the legacy-key path before declaring done — a regression here blocks close.
- **One-shot deprecation note (AC-4):** the note fires *at most once per process*, *only* when the legacy key was the source of the returned policy. Tests must verify the not-spammy and not-spurious behaviors.
- **Alias-tuple generalization (AC-5):** keeps the validator extensible for future renames. Tempting to special-case the `wave_execution`/`wave_implement` rename; resist. The data-structure generalization is cheap and composes.
- **Self-host masking:** this repo's own `workflow-config.json` still uses the legacy keys. The fix's behavior on the legacy path is what runs here; the new-key path is verified by synthetic test fixtures. Do not infer "fix works" from this repo's `wave_audit` output alone.

## Review Evidence

- wave-council-readiness: approved 2026-06-03 by `council-moderator` — bounded single-change hotfix scope confirmed; must-fix QA-1 (test isolation for one-shot deprecation note) folded into implementation plan; SEC-2 (spec exact deprecation note text) folded into AC-4 verification. Standard primer-depth, 3-stance red-team primer + 4 fixed seats (architecture-reviewer, qa-reviewer, reality-checker, senior-engineering-challenger). Verdict: READY.
- wave-council-delivery (1p336): approved 2026-06-03 by `council-moderator` — all 4 seats independently verified the implementation. architecture-reviewer confirmed new-key-first precedence is unambiguous and alias-tuple data structure composes for future renames; qa-reviewer confirmed test isolation (QA-1 must-fix) — each server-tools test resets the one-shot guard in `setUp`-equivalent; reality-checker confirmed AC-9 no-silent-break via all prior `WaveCouncilPolicyTests` still passing on the legacy key path; senior-engineering-challenger confirmed SEC-1 changelog claim reach and SEC-2 deprecation note text match the spec verbatim. 14 new tests across 2 test files; full suite 2299 tests across 24 files pass. Verdict: PASS.
- wave-council-delivery (1p33b): approved 2026-06-03 by `council-moderator` — primer-depth standard (doc-only change), 3-stance red-team primer + 4 fixed seats (architecture-reviewer, qa-reviewer, reality-checker, senior-engineering-challenger). All 16 ACs verified with evidence; end-to-end runtime verification on the dogfooded self-host config confirmed `_read_wave_council_policy()` returns via new-key path with `_WAVE_REVIEW_LEGACY_DEPRECATION_NOTED=False`; `wave_audit` returned ready=true post-migration; 2299-test suite green. Strongest-challenge sustained as advisory: late-admit-during-active-wave is operator-discretion, not default — applies forward as journal-watchpoint reinforcement, not a blocker on this verdict. Verdict: PASS.
- wave-council-delivery (1p33f): approved 2026-06-03 by `council-moderator` — primer-depth standard (validator + skeleton + prose; no trust boundary), 3-stance red-team primer + 4 fixed seats. architecture-reviewer confirmed the validator entry composes with the `1p336` alias-tuple pattern (no logic change); qa-reviewer confirmed the three new tests mirror the `wave_implement` pattern including the `legacy` substring assertion; reality-checker confirmed AC-14 (self-host config unchanged) and the new alias-tuple satisfies on this repo's existing `wave_review` key; senior-engineering-challenger confirmed the install-seed prose reformat at lines 246-247 is benign English-prose and not a parsed surface. Strongest-challenges all rejected: (A) `enabled` is distinct from `required_for_all_waves` in the runtime, (B) alias-tuple back-compat means no in-place upgrade breaks, (C) self-host posture intentional per [[framework-owns-defaults]]. Full suite 2308 tests pass. Verdict: PASS.
- wave-council-delivery (1p33i): approved 2026-06-03 by `wave-council` — primer-depth standard (taxonomy refactor + file moves + role-string rename across runtime; no trust boundary), 3-stance red-team primer + 4 fixed seats. architecture-reviewer confirmed identifier-only change with no new boundaries; qa-reviewer confirmed test-string flips atomic with code flip and runtime smoke returns new role-name on dogfooded self-host config; reality-checker grep-verified no `council-moderator` reference remains in any active surface — four residual categories all intentional (closed-wave records, in-flight 1p337 verdicts per AC-10, this change doc's subject-references, dated `docs/reports/reindex-*` audit artifacts); senior-engineering-challenger sustained the late-admit advisory but rejected it as a blocker. 2308 tests pass; lint clean. The 1p33i verdict is the first one issued under the new `wave-council` role-name identity. Verdict: PASS.
- operator-signoff: approved 2026-06-03 — operator authorized close with explicit "close wave" after downstream testing confirmed the package (1.4.0+p33n) including the late seed-176 case-sensitivity fix. Earlier in the wave a prior signoff was recorded in error on "package and then I'll test" wording and removed when the operator reopened ("I didn't tell you to close it"); the close-authorization lesson is captured in operator memory [[close-not-implied-by-package-or-test]] and applies going forward.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-03: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, architecture-reviewer, qa-reviewer, reality-checker, senior-engineering-challenger; rotating-seat: senior-engineering-challenger; strongest-challenge: process gap not symptom — seed-prose changes that imply consumer-config changes shipped without runtime back-compat; this hotfix patches the known defect but the underlying pattern could repeat without a rename-audit process change, accepted as advisory and folded into change-doc Related Work; strongest-alternative: cross-cut audit for all seed-vs-runtime drift bundled with the fixes — rejected as scope-expansion that defers the known defect's transition-gap closure)
- Must-fix QA-1: test isolation for the one-shot deprecation note — implementation uses per-test state reset rather than module-level state, with explicit test verifying not-spammy and not-spurious behaviors. SEC-2: exact deprecation note text specified inline in AC-4 implementation: *"workflow-config.json: legacy key `wave_council_policy` is deprecated; rename to `wave_review`. The runtime accepts both for now."* SEC-1 (advisory): claim reach 1.3.27–1.3.32 to be verified via `git log` on `_read_wave_council_policy()` before changelog finalization.

## Dependencies

- No external wave dependencies.
- Successor concern (out of scope for this wave): a cross-cut audit for any other seed-vs-runtime drift surfaces. If discovered, scope as a follow-on after 1.4.0 ships.
