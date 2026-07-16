# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-15
review-evidence-source: events.jsonl

wave-id: `1so5p specialist-carrier-frontmatter`
Title: Specialist Carrier Frontmatter

## Objective

Fix a ship-blocking pack bug: freshly-rendered `docs/agents/specialists/*.md` carriers lack the `Role:`/`Category:` frontmatter that the same pack's docs-lint requires, so a 1.13.0 upgrade from 1.12.0 halts at the docs gate. When this wave closes, the specialist seeds carry correct frontmatter and the render path injects it as a destination-aware fallback, so fresh renders of the whole `docs/agents/**` carrier class pass docs-lint — verified by a fresh-root render regression test.

## Changes

Change ID: `1so5o-bug specialist-carrier-frontmatter`
Change Status: `complete`

Completed At: 2026-07-15

## Wave Summary

Wave `1so5p` (Specialist Carrier Frontmatter) delivered one change: Specialist Carrier Frontmatter — Rendered Agent Docs Fail the Pack's Own docs-lint. Notable adjustments during implementation: Specialist Carrier Frontmatter — Rendered Agent Docs Fail the Pack's Own docs-lint: Implemented all four ACs. Seed frontmatter added to `225`/`215`/`216`/`217`; `_ensure_agent_frontmatter` fresh-only fallback added to `render_agent_surfaces.py` (reuses `_expected_agent_category` via lazy import, injects only when absent, `docs/agents/**`-scoped so `docs/prompts/**` renders are untouched); two regression tests added. Targeted `FreshCarrierAgentFrontmatterTests` 2/2 OK.; Specialist Carrier Frontmatter — Rendered Agent Docs Fail the Pack's Own docs-lint: Independent fresh-context readiness review: VERDICT ready-with-notes, no blockers. All root-cause premises corroborated against the tree. Plan sharpened per its notes: pinned the injection site to the fresh-only `_initial_review_carrier_text` (dropped `_write_review_carrier_text` — runs on the update path too); AC-3 now requires the temp root to expose the seeds dir (else the seedless title-minimum branch makes the test vacuous) and to cover a review-category carrier; broadened the scope note (the reviewer carriers share the fresh-install failure class; fallback is load-bearing for ~10 carriers); added the renderer→validator import-edge risk. Confirmed: reality-checker resolves to `specialist` (specialists-dir check precedes the review-stems check), so its seed `Category: specialist` is consistent.

**Changes delivered:**

- **Specialist Carrier Frontmatter — Rendered Agent Docs Fail the Pack's Own docs-lint** (`1so5o-bug specialist-carrier-frontmatter`) — 4 ACs completed. Key decisions: Fix at both layers: correct frontmatter in the seeds AND a renderer fallback that injects it when absent.; Do not add frontmatter to seed `236`; rely on the renderer fallback for its specialist render.
## Journal Watchpoints

- Watchpoint: seed `236-archetype-council` renders to **two** destinations — an exempt `docs/prompts/` doc and a `docs/agents/specialists/` doc — so it must NOT get seed-level `Role:`/`Category:` (that would pollute the prompt render); its specialist render is covered by the renderer fallback only.
- Guard: seed edits require `seed_edit_allowed`; the renderer change requires `framework_edit_allowed` — open each only for its edits and close immediately after.
- Watchpoint: the renderer fallback must inject frontmatter ONLY when absent (never clobber seed-provided or existing project-authored frontmatter); the update path for already-correct tracked docs must stay unchanged.
- Follow-up: this repo's tracked `docs/agents/**` docs are already correct and must not be re-rendered/edited by this wave; the fix targets fresh-render output only.

## Finding Synthesis

<!-- waveframework:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 5 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- waveframework:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a naive fresh-root regression test renders the frontmatter-less title-minimum branch instead of seed-verbatim and would vacuously pass — folded into AC-3, not a readiness blocker; strongest-alternative: none material)
- Council conduct + per-seat evidence: run as one consolidated independent, code-grounded pass by a fresh reviewer with no prior-conclusion context. red-team — every load-bearing premise verified against the tree: `_initial_review_carrier_text` returns seed-verbatim for fresh carriers, the five specialist seeds lack `Role:`/`Category:`, `wave_validators.py` requires them for `docs/agents/**` via a second `rglob` pass, `docs/prompts/**` is exempt, and seed `236` dual-renders to a prompt + specialist doc — so skipping `236` at the seed layer and covering it via the fresh-only fallback is correct. The reviewer carriers share the fresh-install failure class, so the `docs/agents/**` fallback (reusing `_expected_agent_category`) is load-bearing for ~10 carriers. docs-contract-reviewer — the plan's ACs are testable; sharpened AC-3 to expose the seeds dir in the temp root and cover a review-category carrier, pinned the injection site to the fresh-only path, and recorded the renderer→validator import-edge risk. Verdict: READY-WITH-NOTES, no blockers; all notes incorporated before prepare.

## Review Evidence

- operator-signoff: <approved when operator confirms closure>
- wave-council-readiness: approved — All premises corroborated. Verdict ready-with-notes, no blockers. Notes folded into the plan: pin injection to fresh-only _initial_review_carrier_text (drop _write_review_carrier_text); AC-3 must expose the seeds dir in the temp root and cover a review-category carrier; reviewer carriers share the fresh-install failure class (fallback load-bearing for ~10 carriers); renderer->validator import-edge risk noted; reality-checker resolves to specialist (consistent).
- wave-council-delivery: approved — Independent fresh-context delivery review CONFIRMED all five areas. Reviewer reproduced the pre-fix failure (10 role + 10 category failures across specialists + reviewer carriers) and confirmed the fix drives it to zero; confirmed fresh-only injection (never update path), no clobber/duplicate, docs/prompts/** untouched, Role==dest stem, Category via _expected_agent_category (reality-checker→specialist correct), and that neutralizing the fallback fails the test (archetype-council + 5 reviewer carriers). Full suite 5,600 OK; targeted test_render_agent_surfaces 46 OK; docs-lint clean. Verdict approved, max severity none, no blockers.
- operator-signoff: approved — Independent readiness (ready-with-notes, all notes folded in) and delivery (approved, severity none, no blockers) reviews complete; full suite 5,600 OK; docs-lint clean; both fix layers verified inside wavefoundry-1.13.0.pcfw.zip. Operator approved closure.

## Dependencies

- No external wave dependencies.
