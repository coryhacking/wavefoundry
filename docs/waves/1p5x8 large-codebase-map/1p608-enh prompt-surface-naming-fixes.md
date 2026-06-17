# Prompt-surface naming fixes (concrete bugs) + convergence plan

Change ID: `1p608-enh prompt-surface-naming-fixes`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Wave: `1p5x8 large-codebase-map`
Last verified: 2026-06-16

## Rationale

teton field report (1.7.0+p5zy): the prompt surface carries three naming generations (`*-context` → `*-framework` → `*-wavefoundry`) plus a retired `package-wave-framework` tombstone, with concrete correctness bugs and confusing labels. Two classes of work:

1. **Concrete bugs (fix now — low-risk correctness):**
   - **Broken pointer:** `docs/prompts/install-wavefoundry.prompt.md` links `docs/prompts/init-wave-framework.md`, but the file is `init-wave-framework.prompt.md` (missing `.prompt` infix).
   - **Inverted labels:** `docs/prompts/index.md` calls the 123-line canonical bodies (`init`/`upgrade-wave-framework.prompt.md`) "stubs … for bookmarks," while the real 9-line stubs are the `*-context` files. Fix the labels so canonical/stub are described correctly.

2. **Naming convergence (delicate — captured, sequenced carefully):** converge on one canonical body per flow with a single thin redirect layer; make the seed-100 bootstrap emit consistent stub/canonical labeling; retire `package-wave-framework` from the generated set (or document why it persists — it's referenced by `index.md`/agents/README/seeds + `constants.py` `FORBIDDEN_ROOT_WRAPPERS_RETIRED`, so it can only be resolved upstream). This is a broad rename across generated surfaces; do it carefully (case-insensitive sweep, parity tests) — do NOT break the prompt surface.

## Requirements

1. **Fix the broken pointer** in `install-wavefoundry.prompt.md` to the correct `.prompt.md` target (and audit for other missing-`.prompt`-infix links).
2. **Correct the inverted stub/canonical labels** in `index.md` so the canonical bodies and the thin `*-context` stubs are described accurately.
3. **Converge the naming** to one canonical body per flow with a single thin redirect; fix seed-100 to emit consistent labeling; retire the `package-wave-framework` tombstone from the generated set (updating `constants.py`/index/agents/README/seeds together via a complete case-insensitive sweep) — or, if the tombstone must persist, document why in one place. Verify the prompt-surface manifest + any parity tests stay green; do not break discoverability.
4. Generic + seed-first (changes originate in seeds, then render); no project-specific content.

## Acceptance Criteria

- [x] AC-1: The `install-wavefoundry.prompt.md` pointer resolves (correct `.prompt.md` target); no other broken `*-framework`/`*-wavefoundry` prompt links remain (docs-lint clean).
- [x] AC-2: `index.md` labels canonical bodies vs `*-context` stubs accurately (no inverted "stub"/"canonical" descriptions).
- [x] AC-3: Naming converged to one canonical body per flow + thin redirect; seed-100 labeling consistent; `package-wave-framework` retired from the generated set (complete case-insensitive sweep across `constants.py`/index/agents/README/seeds) or its persistence documented; manifest + parity tests green; full suite + docs-lint clean.

## Tasks

- [x] Fix the broken pointer + audit for other missing-infix links (AC-1).
- [x] Correct the inverted stub/canonical labels in `index.md` (AC-2).
- [x] Converge naming + seed-100 labeling + retire/justify `package-wave-framework` (case-insensitive sweep; manifest/parity green) (AC-3).
- [x] Full suite + docs-lint.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | A broken prompt pointer is a correctness bug. |
| AC-2 | required | Inverted canonical/stub labels actively mislead. |
| AC-3 | important | Convergence is the real cleanup; delicate (broad sweep) — do it safely, don't break the surface. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | teton field report (surfaced during a seed-238 config review): broken pointer, inverted stub/canonical labels, 3-generation naming sprawl + `package-wave-framework` tombstone resolvable only upstream. | `docs/prompts/index.md`, `docs/prompts/install-wavefoundry.prompt.md`, `constants.py` |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
