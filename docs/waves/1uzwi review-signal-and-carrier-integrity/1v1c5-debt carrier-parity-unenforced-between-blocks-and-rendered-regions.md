# Carrier Parity Is Unenforced Between Policy Blocks And Rendered Regions

Change ID: `1v1c5-debt carrier-parity-unenforced-between-blocks-and-rendered-regions`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-10
Wave: 1uzwi review-signal-and-carrier-integrity

## Rationale

Editing a `REVIEW_POLICY_SURFACE_BLOCKS` entry in `review_policy.py` without re-running `reconcile_review_policy_surfaces` leaves the rendered `docs/prompts/*.md` marker regions stale — and **nothing detects it**. `check_review_policy_carriers` tests marker presence and obligation-anchor substrings only; it contains zero references to `REVIEW_POLICY_SURFACE_BLOCKS` (verified 2026-08-10), and `test_policy_renderer_materializes_all_registered_policy_blocks` asserts marker counts, not content. The gap was hit live during `1uwpf`'s since-withdrawn `1us4q`: `docs-lint` passed with the block source edited and both rendered files stale, and two delivery lanes independently confirmed the mechanism.

Bounded severity, per the `1uwpf` architecture lane: **target repositories self-heal**, because the reconciler rewrites regions wholesale at every upgrade. The exposure is this source repository between a block edit and the next render — exactly the self-hosting drift `AGENTS.md` warns about. The same lane asked that this be filed as a change document rather than left as a Progress Log row, since (by that wave's own findings) a Progress Log row recruits no review lane.

## Requirements

1. **docs-lint fails when a rendered marker region differs from its block source.** For each `REVIEW_POLICY_SURFACE_BLOCKS` destination whose file exists, the region between the markers must equal the block (modulo the renderer's own framing, taken from `_upsert_review_policy_region` — the check reuses the renderer's composition, never a second implementation of it; `1us4q`'s guard died of a parallel reimplementation and that lesson is load-bearing here).
2. **A missing carrier file stays the existing checks' business.** This check compares content where both sides exist; presence is already covered.
3. **The check runs on the full lint path; the incremental path covers the rendered side.** The incremental path (`_run_incremental_checks`) processes git-changed docs files fired by the docs post-edit hook, so it can catch a hand-edited rendered region; a `review_policy.py` block edit is a `.py` change the docs hook never fires on, and that direction is covered by the full lint path and the close gate's full pass. This asymmetry is the contract (a readiness-council correction to the earlier both-paths-both-directions promise, which was not implementable for the source side).
4. **Fails on zero carriers today**, verified — all 12 regions were byte-identical at `1uwpf` close.

## Scope

**Problem statement:** a two-sided contract (block source, rendered region) with a one-sided gate.

**In scope:** the new check in `wave_lint_lib`; registration on both lint paths; red-first tests including a corpus pass.

**Out of scope:** text outside marker regions (`1v1c4`); the reconciler itself; any block content change.

## Acceptance Criteria

- [x] AC-1: A block edited without re-render fails docs-lint naming the destination, the region, and the fix (`reconcile_review_policy_surfaces`), red-first on a scratch fixture.
- [x] AC-2: The comparison reuses the renderer's own region composition, asserted mechanically: the check imports and calls the renderer's composition helper (`_upsert_review_policy_region` today; promoted to a public name if the implementer prefers, with the deliberate coupling to renderer-owned code recorded either way). This is the `1us4q` lesson pinned.
- [x] AC-3: The live corpus passes with zero failures, and the check is registered on the full lint path plus the incremental path for rendered-side changes (Requirement 3's stated asymmetry) — with the corpus test rooted at the **repository root constant that resolves to this repo**, not the scripts-tree parent (the `PROJECT_ROOT` vacuity from `1uwpf` qa, named so it cannot recur).
- [x] AC-4: A hand-edit **inside** a rendered region also fails (the check is symmetric about which side drifted).
- [x] AC-5: The full framework suite and docs-lint pass.

## Tasks

- [x] Red-first fixture: edited block, stale region; hand-edited region, current block.
- [x] Implement via the renderer's composition helper; register both paths.
- [x] Corpus pass; full suite; docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-tests | implementer | — | Both drift directions |
| check | implementer | red-tests | Renderer-helper reuse is the contract |
| registration | implementer | check | Both paths; corpus pass |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/core_validators.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`

## Affected Architecture Docs

`N/A` with rationale: adds a gate over an existing contract; no flow changes. If implementation shows `data-and-control-flow.md`'s renderer path needs a sentence for the new check, that lands with it and is disclosed here.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The debt. |
| AC-2 | required | A second region parser is how `1us4q`'s guard died; reuse is the design. |
| AC-3 | required | An error-level check must ship green, and its corpus test must actually scan the corpus. |
| AC-4 | important | Hand-edits inside regions are the likelier accident in a self-hosting repo. |
| AC-5 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Planned from wave `1uwpf`'s carried-forward findings (found by the coordinator mid-`1us4q`, confirmed independently by the docs-contract and architecture lanes; filing as a change doc is the architecture lane's explicit ask). Premises verified before authoring: zero `REVIEW_POLICY_SURFACE_BLOCKS` references in the carrier check; all 12 regions currently byte-identical | grep plus the two lanes' executed confirmations, 2026-08-10 |
| 2026-08-10 | Readiness council (red-team and docs-contract seats): both premises re-executed independently (12 destinations AST-counted; zero references confirmed; drift 0 of 12 via the renderer's own helper). Requirement 3's both-paths promise was not implementable for the source side (the docs hook never fires on a `.py` edit) and now states the asymmetry; AC-2's no-parallel-parser clause restated mechanically; the reconciler-idempotence alternative recorded in the Decision Log | red-team seat report, executed scratch parity run, 2026-08-10 |
| 2026-08-10 | Thought: implement `check_review_policy_carrier_parity` in `core_validators.py` mirroring the reconciler's own iteration (registry rows with `owner == "renderer"` and a block present, the code lane's filter note), composing the expected region ONLY via `_upsert_review_policy_region` (call-time import; the code lane verified no import cycle). Dispositions pinned per the qa lane's fixture finding: missing file skipped, exists-with-neither-marker skipped (the base lint fixture holds that state today and presence is the existing checks' business), single/malformed markers FAIL (the reconciler warns-and-skips; a gate must not), well-formed region differing from block FAILS in either drift direction. `only=` parameter carries the incremental rendered-side registration | implementation start, 2026-08-10 |
| 2026-08-10 | Implemented. `check_review_policy_carrier_parity` in `core_validators.py`, registered at `_run_full_checks` (beside the sibling carrier check) and inside `_run_incremental_checks`'s `changed_docs` block with `only=changed_docs`. Eight tests in `ReviewPolicyCarrierParityTests`: matching-pass, hand-edit fail (AC-4), block-edit fail via scoped `patch.dict` (AC-1), regionless-skip and missing-file-skip dispositions pinned, malformed-markers fail, live-corpus pass rooted at the self-host repo with a non-vacuity probe (AC-3), and full+incremental registration exercised through the real `cli` functions on a drifted base-fixture copy. Executed red demonstration: the identical drifted fixture passes the clean `git archive HEAD` extract's docs-lint (rc=0, no parity message: the documented gap) and fails the new tree's (rc=1, parity message present). Live corpus green in situ via `wf_validate_docs` with the check registered. Registry note discovered while implementing: the registry holds duplicate renderer rows per destination, so the check dedupes to one report per destination | ReviewPolicyCarrierParityTests 8/8; OLD-vs-NEW executed lint comparison, 2026-08-10 |
| 2026-08-10 | Delivery-review dispositions, all minor, no code change: (1) whole-region deletion (markers plus content) on a destination whose obligation anchors are satisfied by prose outside the region is invisible to every current gate (parity skips by the pinned regionless disposition; the carrier check's anchors still match); bounded because the reconciler self-heals at the next render; a presence-family check is future debt if wanted. (2) Verified-correct-but-unpinned behaviors named by the qa lane: duplicate-registry-row dedupe (4 live destinations hold 2 renderer rows each), the only= exclusion direction, composite-conjunct ordering, the unreadable-carrier branch; each verified by executed probe. (3) AC-2's helper reuse is established by implementation inspection plus the Decision Log coupling record rather than a delivered test assertion. (4) Code lane: `_contained_review_carrier_path` raises RuntimeError uncaught on a symlink-escaping destination (fail-closed either way, identical to the renderer's own call sites); CRLF carriers read as drift by design, matching reconciler semantics. Canonical suite tally on the delivered tree: 7087/62 OK | code and qa delivery lane reports, executed probes, 2026-08-10 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | Compare via the renderer's own composition helper | The one region-shape authority already exists; `1us4q` demonstrated what a parallel implementation costs (five constructible divergences) | Independent region parser (rejected on the `1us4q` evidence); a pre-commit hook (rejected: commits are operator-owned and often batch many waves) |
| 2026-08-10 | Error, not warning | Fails on zero carriers today and the fix is one function call; a warning on a never-firing check is invisible | Warning (rejected: no signal) |
| 2026-08-10 | Readiness-council alternative recorded, kept open for implementation measurement: a reconciler-idempotence gate (run `reconcile_review_policy_surfaces` against a temp corpus copy; fail lint if it would write anything) | Zero composition logic, covers every renderer-owned region family including `wave:executable-review-evidence`, immune by construction to parallel reimplementation; cost is a corpus copy per full-lint run | Composed comparison per destination (the default; cheaper per run, same no-parallel-parser contract either way) |
| 2026-08-10 | Composed comparison shipped; the helper stays private (`_upsert_review_policy_region`), the coupling deliberate and recorded here per AC-2 | The check is a lint-side consumer of renderer-owned composition; promoting the name adds an API surface without changing the contract, and the call-time import keeps module load independent (no cycle, code lane verified). The reconciler-idempotence shape stays available if a future marker family needs coverage | Promote to a public name (rejected for now: no second consumer exists) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The renderer's framing makes byte-comparison brittle | AC-2 mandates composing the expected region with the renderer's helper, so framing changes move both sides together |
| The check blocks a legitimate mid-edit lint run | The failure message names the one-call fix; the state it blocks is precisely the drift being shipped |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
