# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-01

wave-id: `1p99f retire-framework-index-seed-references`
Title: Retire Framework Index Seed References

## Objective

Retire the stale framework-index narrative from the shipped seeds. Wave `1p4ww` eliminated the
separate framework semantic/graph index (single project index now; framework seeds fold into the
project docs index; `build_pack` ships source only), but 6 canonical seeds — and the prompts rendered
from them — still tell downstream consumers that a framework index is built/shipped and that they can
query via `layer="framework"`. When this wave closes, the seeds and rendered prompts match the
single-project-index reality, so consumers get correct guidance. Ships in the 1.9.9 release alongside
closed wave `1p93a`.

## Changes

Change ID: `1p994-enh retire-framework-index-seed-references`
Change Status: `implemented`

Completed At: 2026-07-01

## Wave Summary

Wave `1p99f` (Retire Framework Index Seed References) delivered one change: Retire framework-index references in shipped seeds (single project index is the reality). Notable adjustments during implementation: Retire framework-index references in shipped seeds (single project index is the reality): Planned (not admitted). Found during the framework-index docs-drift sweep: 6 shipped seeds + 3 rendered prompts still describe the `1p4ww`-removed framework index/`layer="framework"`. Ground truth reverified in code (build_pack ships source only; framework/union graph layers removed; framework seeds fold into the project docs index).; Retire framework-index references in shipped seeds (single project index is the reality): Implemented. Admitted to wave `1p99f`; prepare-council PASS (rotating docs-contract-reviewer). Edited the 6 seeds under `seed_edit_allowed` (source-only build_pack wording; `011` project-index fold; `100`/`package-` dropped `--skip-framework-index`; `211-guru` removed `layer="framework"`) + reconciled the 3 rendered prompts. AC-1..6 met; false positives (`seed-050` gitignore entry, methodology "Wave Framework layer") preserved; no wave/ADR refs added.

**Changes delivered:**

- **Retire framework-index references in shipped seeds (single project index is the reality)** (`1p994-enh retire-framework-index-seed-references`) — 6 ACs completed. Key decisions: Fix the seeds (source of truth) + re-render prompts, not the rendered prompts directly.; Seeds state the current reality with NO wave/ADR IDs.
## Journal Watchpoints

- Guard: `seed_edit_allowed` for all 6 seed edits (`.wavefoundry/framework/seeds/`); the rendered-prompt
  reconciliation (`docs/prompts/`) follows the seed edits (seeds are the source of truth).
- Shipped-seed convention: corrections state the current reality plainly with **no** internal
  wave/ADR-ID references (downstream repos can't resolve `1p4ww`/`1p4xx`/`decisions/…`).
- Preserve false positives: "Wave Framework **layer**" = installed-methodology text, and the `seed-050`
  rendered `.gitignore` `framework/index/` defensive-ignore entry, stay untouched.
- Watchpoint: verification is a grep gate (seeds + `docs/prompts/` clean) plus the framework suite +
  docs gate — a seed↔prompt or shipped-reference-doc consistency guard could block if a seed is edited
  but its rendered prompt is not reconciled in the same change.
- Follow-up: none expected — this is the seed half of the framework-index drift cleanup; the authored-doc
  half already landed in `docs/`.

## Review Evidence

- wave-council-readiness: approved 2026-07-01 — READY. Single-change seed-content cleanup retiring the
  `1p4ww`-removed framework-index / `layer="framework"` narrative from 6 shipped seeds + the 3 rendered
  prompts. Red-team's strongest challenge — a shipped-reference-doc / seed↔`build_pack.py` alignment
  guard firing if a seed's packaging text is edited without reconciling the rendered prompt — is
  mitigated by reconciling both together and AC-6 running the full suite before close. Other risks
  bounded: over-correcting methodology "Wave Framework layer" text and adding wave/ADR refs to seeds are
  gated by AC-3 (false-positive preservation) and AC-2 (self-contained wording). Architecture: confined
  to seed content + rendered prompts, mirrors the landed authored-doc cleanup, no behavior change.
  Security: pure documentation correction, no auth/secrets/network/executable change — reduces
  misinformation. QA/reality-checker: objective grep gate + suite + docs gate, not vacuous. No blocking
  findings.
- wave-council-delivery: approved 2026-07-01 — PASS. Delivery review of the shipped seed/prompt edits. Computational lanes: docs-lint ok, sensor max-severity none. Red-team: all 6 seeds + 3 rendered prompts corrected to the source-only / single-project-index reality; the grep gate returns only corrected negation/fold statements + the intentional `seed-050` gitignore entry + pre-existing provenance parentheticals; the `--skip-framework-index` removal matches the actual `build_pack.py` (flag absent), so `seed-009`'s seed↔script alignment contract is now satisfied; 3,788 tests pass with no shipped-reference-doc/alignment guard tripped. Docs-contract-reviewer (rotating): seed → rendered-prompt → `build_pack.py` contract consistent across all three; seeds self-contained (no unresolvable refs added). Architecture/security/qa: content-only, no behavior/auth/secrets change, objective grep + suite + docs-lint gate, not vacuous. No blocking findings.
- operator-signoff: pending operator confirmation at closure

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a shipped-reference-doc / seed↔`build_pack.py` alignment guard could fire if a seed's packaging description is edited without reconciling the rendered prompt in the same change — MITIGATED by reconciling seed + rendered prompt together and AC-6 running the full framework suite + docs gate before close, plus AC-2 no-wave/ADR-refs and AC-3 false-positive preservation; strongest-alternative: hand-edit only the rendered prompts — rejected because the prompts render from seeds, so the seed would keep shipping the drift to consumers and be overwritten on re-render. Docs-contract-reviewer (rotating): the seed↔rendered-prompt↔`build_pack.py` contract must stay consistent — corrections align all three to the source-only reality; seeds stay self-contained with no wave/ADR IDs the consumer can't resolve.)

## Dependencies

- No external wave dependencies.
