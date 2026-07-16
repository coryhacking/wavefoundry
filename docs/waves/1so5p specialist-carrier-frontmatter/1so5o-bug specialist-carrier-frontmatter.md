# Specialist Carrier Frontmatter — Rendered Agent Docs Fail the Pack's Own docs-lint

Change ID: `1so5o-bug specialist-carrier-frontmatter`
Change Status: `complete`
Owner: Engineering
Status: complete
Wave: `1so5p specialist-carrier-frontmatter`
Last verified: 2026-07-15

## Rationale

Upgrading a target repo from 1.12.0 to a 1.13.0 pack halted at the docs gate (exit 1) with the pack's own docs-lint rejecting the pack's own rendered output: five newly-added specialist carrier docs under `docs/agents/specialists/` (`red-team`, `wave-council`, `archetype-council`, `reality-checker`, `senior-engineering-challenger`) were materialized without the `Role:`/`Category:` frontmatter that the docs-lint agent-metadata validator requires. The upgrade left the tree half-extracted with the lock and a failure marker (the intended safe-fail state); the operator recovered manually by patching the five files and running `resume_after_gate → update_index → cleanup → wave_mcp_reload`.

Root cause (canonical source):

- `render_agent_surfaces.py:_initial_review_carrier_text` materializes a *fresh* carrier destination by returning the seed body **verbatim** (`seed_path.read_text()`).
- The specialist seed sources (`225-red-team`, `215-wave-council`, `236-archetype-council`, `216-reality-checker`, `217-senior-engineering-challenger`) carry **no** `Role:`/`Category:` frontmatter, so the fresh render has none.
- `wave_lint_lib/wave_validators.py` requires every `docs/agents/**/*.md` to declare `Role:` equal to the filename slug and `Category:` equal to the path-derived category (`specialist` under `docs/agents/specialists/`).
- The bug is masked in this self-hosted repo because the five `.md` files are tracked **with** correct frontmatter, so the renderer's *update* path preserves them and lint passes. In a target upgrading from 1.12.0 the five are **new**, so they render fresh from seed-verbatim → no frontmatter → validator rejects them → the docs gate blocks the upgrade.

`docs/prompts/**` is **not** subject to the agent Role/Category rule (only `docs/agents/**` is). This matters because seed `236` renders to **two** destinations — `docs/prompts/archetype-council.prompt.md` and `docs/agents/specialists/archetype-council.md` — so seed-level frontmatter is the wrong layer for `236` (it would pollute the prompt render).

## Requirements

1. **Seed frontmatter (source-of-truth fix).** Add `Role: <destination-slug>` and `Category: specialist` frontmatter to the four **single-destination** specialist seeds — `225-red-team` (`Role: red-team`), `215-wave-council` (`Role: wave-council`), `216-reality-checker` (`Role: reality-checker`), `217-senior-engineering-challenger` (`Role: senior-engineering-challenger`) — each with `Category: specialist`. Do **not** add this frontmatter to seed `236-archetype-council`, whose dual render would stamp the exempt prompt doc; its specialist render is covered by the renderer fallback below.
2. **Renderer fallback (robust safety net).** When `render_agent_surfaces.py` materializes a *fresh* carrier whose destination is under `docs/agents/**`, ensure the written content declares the required `Role:` (the destination filename slug) and `Category:` (derived exactly as the validator derives it, via `_expected_agent_category`) — injecting them into the frontmatter only when absent, never overwriting a value the seed or an existing project-authored file already provides. **Inject in the fresh-carrier path only** — `_initial_review_carrier_text` (or the missing-destination branch in `reconcile_review_protocol_surfaces`); do **not** inject in `_write_review_carrier_text`, which also runs on the *update* write and cannot distinguish fresh from update (that would risk AC-4). This fixes the whole `docs/agents/**` carrier class (current and future), including seed `236`'s specialist render, without touching `docs/prompts/**` renders. **Scope note:** the class is broader than the five specialists — the reviewer carriers (`239-qa-reviewer`, `214-architecture-reviewer`, `212-performance-reviewer`, `221-code-reviewer`, `213-security-reviewer`) also render fresh from frontmatter-less seeds, so a genuine fresh *install* is the same failure class; the `docs/agents/**` fallback is load-bearing for all ~10 carriers, and `_expected_agent_category` (not a hardcoded `specialist`) is required so reviewer carriers get `Category: review`.
3. **Regression test.** Render the specialist carriers into a fresh temporary repo root (the missing-destination path) and assert `docs-lint` passes on the result — the exact check that would have caught this before ship. Cover at least one single-destination specialist seed (validates Requirement 1) and seed `236` (validates the fallback + that the prompt render is not polluted).
4. **No behavior change to existing/tracked surfaces.** The renderer's *update* path must continue to preserve project-authored frontmatter and the owned protocol region; already-correct `docs/agents/**` docs (here and in older targets) must be untouched.

## Scope

**Problem statement:** Freshly-rendered `docs/agents/specialists/*.md` carriers lack the `Role:`/`Category:` frontmatter that the same pack's docs-lint requires, so a 1.13.0 upgrade blocks at the docs gate.

**In scope:**

- Seed frontmatter for the four single-destination specialist seeds.
- A destination-aware frontmatter fallback in the fresh-carrier render path for `docs/agents/**` destinations.
- A fresh-root render + docs-lint regression test.

**Out of scope:**

- Re-rendering or editing the tracked `docs/agents/**` docs in this self-hosted repo (already correct).
- Any change to `docs/prompts/**` rendering or to the docs-lint validator's requirements themselves.
- Broader agent-surface schema changes; changing which carriers exist.
- Backfilling the operator's already-recovered target repo (their patch stands; the renderer fallback makes future re-renders self-correct).

## Acceptance Criteria

- [x] AC-1: The four single-destination specialist seeds declare `Role: <slug>` + `Category: specialist`; a fresh render of each produces a `docs/agents/specialists/<slug>.md` that passes docs-lint. (Seeds `225`/`215`/`216`/`217` edited; `test_fresh_carriers_pass_the_pack_agent_metadata_validators` asserts red-team renders seed-verbatim with Role/Category and the agent validators return no failures.)
- [x] AC-2: The fresh-carrier render path injects the correct `Role:`/`Category:` for any `docs/agents/**` destination lacking them (derived from the destination), so a fresh render of seed `236`'s specialist carrier passes docs-lint while its `docs/prompts/archetype-council.prompt.md` render gains no `Role:`/`Category:`. (`_ensure_agent_frontmatter` in `render_agent_surfaces.py`, fresh-only at the `reconcile_review_protocol_surfaces` create branch; test asserts archetype-council specialist doc gets Role/Category from the fallback and the prompt render does not.)
- [x] AC-3: A regression test renders carriers into a fresh temp root **that exposes `.wavefoundry/framework/seeds/`** (so carriers render seed-verbatim via `_initial_review_carrier_text`, NOT the frontmatter-less title-minimum branch) and asserts the agent-metadata validators return no failures. Covers a single-destination specialist seed, seed `236`'s specialist render (+ unpolluted prompt), and `qa-reviewer` (`Category: review` via the non-`specialist` branch). Fails against the pre-fix renderer (archetype/qa assertions depend on the fallback).
- [x] AC-4: The renderer's update path is unchanged — `test_fallback_is_fresh_only_and_does_not_clobber_existing_frontmatter` proves an existing specialist doc's project-authored frontmatter is preserved with exactly one Role/Category each; full framework suite + docs-lint pass.

## Tasks

- [x] Add `Role:`/`Category: specialist` frontmatter to seeds `225`, `215`, `216`, `217` (skip `236`); confirmed no seed-header validator objects (seeds validated only for numeric prefix + `.prompt.md`).
- [x] Add a destination-aware frontmatter fallback in the **fresh-carrier** render path (`_ensure_agent_frontmatter`, called at the `reconcile_review_protocol_surfaces` create branch — NOT `_write_review_carrier_text`), reusing the validator's `_expected_agent_category` via a lazy local import; inject only when absent.
- [x] Add a fresh-root render regression test in `test_render_agent_surfaces.py` that exposes `.wavefoundry/framework/seeds/` in the temp root and covers a single-destination specialist seed, seed `236`, and `qa-reviewer`; plus a fresh-only/no-clobber test.
- [x] Run the full bytecode-free suite + docs-lint; confirm the carriers render valid from a clean root.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seed-frontmatter | implementer | — | Role/Category on the four single-destination specialist seeds (gated by `seed_edit_allowed`) |
| renderer-fallback | implementer | — | Destination-aware injection for fresh `docs/agents/**` carriers (gated by `framework_edit_allowed`); reuse `_expected_agent_category` |
| verification | qa-reviewer | seed-frontmatter, renderer-fallback | Fresh-root render + docs-lint regression test; full suite |


## Serialization Points

- The renderer fallback and the seed frontmatter must both land before the regression test asserts a clean fresh render (the test exercises both paths).

## Affected Architecture Docs

N/A — a localized fix to the agent-surface render path and specialist seed frontmatter with no boundary, data-flow, or verification-architecture change. The rendering contract is already documented in `docs/agents/platform-mapping.md`; no ADR is warranted for a defect repair.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Source-of-truth fix; without it fresh specialist renders stay invalid. |
| AC-2 | required | The robust fallback that fixes the class (incl. seed 236) and prevents recurrence. |
| AC-3 | required | The pre-ship check that would have caught this; guards against regression. |
| AC-4 | required | The fix must not disturb existing correct surfaces. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-15 | Filed from a field upgrade failure: 1.13.0 pack's docs-lint rejected five newly-rendered specialist carriers lacking `Role:`/`Category:` frontmatter; upgrade halted at the docs gate. Root cause traced to `_initial_review_carrier_text` returning seed-verbatim while the specialist seeds carry no such frontmatter. | Operator upgrade report 2026-07-15; `render_agent_surfaces.py:_initial_review_carrier_text`; `wave_validators.py` Role/Category checks; seeds `225/215/236/216/217` MISSING Role/Category. |
| 2026-07-15 | Implemented all four ACs. Seed frontmatter added to `225`/`215`/`216`/`217`; `_ensure_agent_frontmatter` fresh-only fallback added to `render_agent_surfaces.py` (reuses `_expected_agent_category` via lazy import, injects only when absent, `docs/agents/**`-scoped so `docs/prompts/**` renders are untouched); two regression tests added. Targeted `FreshCarrierAgentFrontmatterTests` 2/2 OK. | `render_agent_surfaces.py:_ensure_agent_frontmatter` + fresh branch call; seeds `225/215/216/217`; `test_render_agent_surfaces.py::FreshCarrierAgentFrontmatterTests`. |
| 2026-07-15 | Independent fresh-context readiness review: VERDICT ready-with-notes, no blockers. All root-cause premises corroborated against the tree. Plan sharpened per its notes: pinned the injection site to the fresh-only `_initial_review_carrier_text` (dropped `_write_review_carrier_text` — runs on the update path too); AC-3 now requires the temp root to expose the seeds dir (else the seedless title-minimum branch makes the test vacuous) and to cover a review-category carrier; broadened the scope note (the reviewer carriers share the fresh-install failure class; fallback is load-bearing for ~10 carriers); added the renderer→validator import-edge risk. Confirmed: reality-checker resolves to `specialist` (specialists-dir check precedes the review-stems check), so its seed `Category: specialist` is consistent. | Independent readiness review 2026-07-15 against `render_agent_surfaces.py` (fresh-write flow lines 894/909/912/916/925), `wave_validators.py` (role second-pass rglob line 400, `_expected_agent_category` line ~431), carrier registry (236 dual dest lines 69/71), `test_render_agent_surfaces.py` (seedless temp-root pattern). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-15 | Fix at both layers: correct frontmatter in the seeds AND a renderer fallback that injects it when absent. | Belt-and-suspenders per operator direction — the seed carries the right thing at source, and the renderer guarantees validity for any carrier that forgets (future-proofing the class). | Seeds only (fragile — a future carrier re-triggers it); renderer only (leaves seed sources subtly wrong). |
| 2026-07-15 | Do not add frontmatter to seed `236`; rely on the renderer fallback for its specialist render. | Seed `236` renders to both a specialist doc and an exempt `docs/prompts/` doc; seed-level `Category: specialist` would wrongly stamp the prompt. The destination-aware fallback scopes injection to `docs/agents/**` only. | Add to `236` and strip on the prompt render — more code, more surface. |
| 2026-07-15 | Derive `Category` in the fallback from the validator's own `_expected_agent_category` logic. | Single source of truth for the category convention; keeps renderer and validator from drifting. | Hardcode `specialist` — narrower and would drift if categories change. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A seed-header validator rejects the new `Role:`/`Category:` lines on seed files | Verify seeds are not subject to the `docs/agents/**` agent-metadata rule (they live under `.wavefoundry/framework/seeds/`); run the full suite after the seed edits. |
| The fallback clobbers project-authored or seed-provided frontmatter | Inject only when the field is absent; the update path already preserves bytes outside the owned region. AC-4 + the suite guard this. |
| The fix is scoped too narrowly and a non-specialist `docs/agents/**` carrier still renders invalid on a fresh install | Derive `Category` generally via `_expected_agent_category` so the fallback covers the whole `docs/agents/**` carrier class, not just specialists (readiness review confirmed the reviewer carriers share this failure class on a fresh install). |
| Reusing private `_expected_agent_category` adds a renderer→`wave_lint_lib` import edge that might not resolve in a setup/upgrade/hook subprocess | No import cycle exists (validators don't import the renderer); verify resolution in those subprocess contexts during implementation, and fall back to an inline copy of the small specialists/review derivation if fragile. |
| The regression test vacuously passes by rendering the frontmatter-less title-minimum branch instead of seed-verbatim | AC-3 requires the temp root to expose `.wavefoundry/framework/seeds/`; the test must assert the rendered file contains the seed body, not just that lint passes. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
