# Factor-surface integrity — declared-but-missing validator + seed reconciliation

Change ID: `1p79x-enh factor-surface-integrity`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-22
Wave: TBD

## Rationale

Downstream field feedback (a Java-agent consumer, pack `1.8.0+p79p`) surfaced a real, long-standing gap in the **factor-review agent surface**, verified against the framework code:

- **No declared-but-missing validator.** `wave_lint_lib/wave_validators.py` (`_AGENT_ROLE_REQUIRED_PATHS`, lines 58-75) hardcodes a **static** set of only **4 factor canonical paths** (`factor-03/05/12/13`). It never consults `docs/repo-profile.json` `factor_review`, so a repo with applicable factors `02/09/11/14/15` has **zero** canonical-source requirement; and there is **no validation of `.claude/agents/factor-*.md` wrappers** (no orphan-wrapper or frontmatter check). A repo can ship rendered wrappers **without their canonical sources**, with wrappers that have **no YAML frontmatter** (so Claude Code can't load them as subagents), and `docs-lint` passes clean — a silent, half-built, broken surface.
- **seed-238 (Config Review) contradicts seed-050.** `seed-238` has **no factor-awareness** (zero "factor" mentions) — it treats the whole agent surface with a removal bias ("orphaned primitives → keep/revise/retire"). So it flags the factor wrappers as orphans to relocate/retire, when `seed-050` task 5 establishes them as the framework's **correct rendered wrappers** of a canonical+wrapper pair (canonical `docs/agents/factor-<nn>-<name>.md`, wrapper `.claude/agents/…`, both in `platform-mapping.md`). Following seed-238 literally deepens the drift and never names the real defect (the missing canonical source).
- **seed-160 (Upgrade) doesn't repair the drift.** It has factor *generation* and *pack-relocation* notes (lines 101, 333) and a checklist that wrappers exist for applicable factors (line 467), but **no step that detects "applicable factor missing its canonical doc" or "wrapper missing frontmatter" and repairs it**. A repo drifted before the canonical-source convention stays broken across every upgrade — as this one did from 1.6.x through 1.8.0.

The highest-leverage fix is the validator (#1): it converts a silent broken state into an actionable gate finding, which then gives the config review (#2) and the upgrade backfill (#3) something concrete to act on. This is **the same "declared-but-missing" check the design-system validators already apply to `external-reference` token sources** (`1p799`) — extending that proven pattern to the factor surface.

## Requirements

1. **Factor-surface validator — the declared-but-missing gate.** In `wave_lint_lib/wave_validators.py`, make factor-doc validation **keyed off `docs/repo-profile.json` `factor_review`** instead of the static `_AGENT_ROLE_REQUIRED_PATHS` factor entries. For each factor marked `applicable`:
   - require the canonical `docs/agents/factor-<nn>-<name>.md` to exist with `Role: factor-<nn>-<name>` + `Category: factor` headers;
   - flag any `.claude/agents/factor-*.md` **wrapper with no matching canonical source** (orphan wrapper);
   - flag any factor wrapper **missing YAML frontmatter** (not subagent-loadable).
   Not-applicable / partial factors with no docs must NOT be flagged (no false positives). Mirror the `1p799` external-reference "declared-but-missing" validation shape.
2. **seed-238 reconciliation.** Make the Framework Config Review **factor-aware**: factor docs are a framework-governed canonical+wrapper pair (per `seed-050` task 5), excluded from the generic "orphaned primitive → relocate/retire" path. When the review finds wrappers-without-sources or frontmatter-less wrappers, it must direct the operator to **regenerate via `seed-050` task 5 / an Upgrade-wave reconciliation** — never hand-relocate or retire the wrapper, and never suggest a `docs/agents/factors/` subdir (canonical home is `docs/agents/` **flat**). It must name the real defect (missing canonical source), not just the wrapper symptom.
3. **seed-160 factor-surface backfill (merge-safe).** Add an upgrade editing-pass step: for each `applicable` factor lacking a canonical `docs/agents/factor-<nn>-<name>.md`, **regenerate it from the `seed-050` task 5 template + repo evidence**, then **re-render wrappers via `render_platform_surfaces.py`** so `.claude/agents/` copies get valid frontmatter. Respect the existing "never overwrite operator-refined content" guardrail. (Line 101's pack-relocation note is insufficient — it handles "pack moved the canonical," not "canonical never existed.")
4. **Renderer audit (audit-and-skip).** Audit whether `render_platform_surfaces.py` currently emits YAML frontmatter for factor wrappers. If it does **not** (so re-rendering wouldn't make them loadable), fix it. If it already does, record that the downstream symptom is purely stale-never-re-rendered (resolved by R3's backfill) — no fabricated change.
5. **Tests.** Framework tests covering R1: applicable-factor-missing-canonical → fail; orphan wrapper (no canonical) → fail; wrapper-missing-frontmatter → fail; correct canonical+wrapper pair for an applicable factor → pass; not-applicable factor with no docs → pass. Bytecode-free.
6. **Gates + hygiene.** `wave_validators.py` + renderer edits under `framework_edit_allowed`; `seed-238`/`seed-160` (and `seed-050` if a pointer to the new gate is warranted) under `seed_edit_allowed`. Introduce **no** external-project names (the vendor-neutrality scrub must stay at zero).

## Scope

**Problem statement:** The framework lets a factor-review surface exist as wrappers-without-sources (and frontmatter-less wrappers) undetected, gives config-review advice that contradicts its own generation contract, and never repairs the drift on upgrade.

**In scope:**

- `wave_lint_lib/wave_validators.py`: `factor_review`-keyed canonical-existence + orphan-wrapper + wrapper-frontmatter checks (replacing the static factor list).
- Framework tests for the new validator behavior.
- `seed-238` factor-aware reconciliation; `seed-160` factor-surface backfill; `seed-050` pointer to the gate if warranted.
- `render_platform_surfaces.py` factor-wrapper frontmatter audit (+ fix only if broken).

**Out of scope:**

- Reworking the factor taxonomy or the factor list itself.
- Generating factor docs for this (wavefoundry) repo beyond what its own `factor_review` already declares.
- The design-system surface (separate; already shipped in `1p75h`).

**Depends on:** none (independent of `1p75h`). Reuses the `1p799` declared-but-missing validation pattern as a template.

## Acceptance Criteria

- [ ] AC-1: `docs-lint`, keyed off `repo-profile.json` `factor_review`, fails when an `applicable` factor lacks its canonical `docs/agents/factor-<nn>-<name>.md` (with `Role:` + `Category: factor`). The static 4-factor list is no longer the source of truth.
- [ ] AC-2: `docs-lint` flags a `.claude/agents/factor-*.md` wrapper that has no matching canonical source (orphan wrapper).
- [ ] AC-3: `docs-lint` flags a factor wrapper missing YAML frontmatter (not subagent-loadable).
- [ ] AC-4: a correct canonical+wrapper pair for an `applicable` factor passes; a `not-applicable`/`partial` factor with no docs passes (no false positive). Verified including against this repo's own `factor_review` (self-hosting — no regression on wavefoundry's `03/05/12/13`).
- [ ] AC-5: `seed-238` treats factor docs as a governed canonical+wrapper pair — excludes them from the generic orphan-retire path, directs regenerate-not-relocate on wrappers-without-sources/frontmatter, and never suggests `docs/agents/factors/`.
- [ ] AC-6: `seed-160` has a merge-safe factor-surface backfill (regenerate missing canonical from the `seed-050` template + evidence; re-render wrappers for valid frontmatter; never overwrite operator-refined content).
- [ ] AC-7: `render_platform_surfaces.py` audited for factor-wrapper frontmatter — fixed if broken, else the audit result is recorded (already-correct).
- [ ] AC-8: framework tests cover the validator (missing-canonical / orphan-wrapper / missing-frontmatter → fail; correct pair + not-applicable → pass), bytecode-free; `docs-lint` / `wave_validate` clean.
- [ ] AC-9: all edits under the appropriate gates; no external-project names introduced (grep `aceiss|teton|solaris` over changed files = 0).

## Tasks

- [ ] Open gates per scope (`framework_edit_allowed` for validators/renderer/tests; `seed_edit_allowed` for seeds); close after each.
- [ ] Make the factor validator `factor_review`-keyed; add orphan-wrapper + frontmatter checks (reuse the `1p799` declared-but-missing shape).
- [ ] Add framework tests (fail + pass cases incl. the self-hosting `factor_review`).
- [ ] Audit `render_platform_surfaces.py` factor-wrapper frontmatter; fix if broken.
- [ ] Edit `seed-238` (factor-aware reconciliation), `seed-160` (factor backfill), `seed-050` (gate pointer if warranted).
- [ ] Run framework tests bytecode-free; `wave_validate` clean; grep external-names = 0; close gates.

## Agent Execution Graph


| Workstream        | Owner       | Depends On        | Notes                                                              |
| ----------------- | ----------- | ----------------- | ----------------------------------------------------------------- |
| validator         | implementer | —                 | `factor_review`-keyed existence + orphan-wrapper + frontmatter    |
| validator-tests   | implementer | validator         | fail + pass cases incl. self-hosting                              |
| renderer-audit    | implementer | —                 | factor-wrapper frontmatter audit (+ fix if broken)                |
| seed-updates      | implementer | validator         | seed-238 reconcile + seed-160 backfill (reference the gate)       |
| review            | reviewer    | all above         | framework-code + docs-contract lanes                              |


## Serialization Points

- The validator contract (the `factor_review`-keyed rules) is the spec the seed reconciliations reference — land the validator before the seed text describes it.

## Affected Architecture Docs

- Likely **N/A** — change is confined to the validator + seeds + (maybe) the renderer, with no module-boundary/data-flow shift. If a framework doc records the agent-surface validation contract (e.g. `docs/contributing/build-and-verification.md` or a platform-mapping reference), add a one-line pointer to the new factor gate. Confirm exact target at Prepare.

## AC Priority

(Populated at Prepare wave — proposed below.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The declared-but-missing canonical gate — the highest-leverage fix; converts silent breakage to an actionable finding. |
| AC-2 | required  | Orphan-wrapper detection (wrapper without canonical) is the exact downstream symptom. |
| AC-3 | required  | Frontmatter check — a wrapper that can't load as a subagent is functionally broken. |
| AC-4 | required  | No false positives (not-applicable factors) + self-hosting non-regression is the correctness guard. |
| AC-5 | required  | seed-238 must stop contradicting seed-050 (actively harmful guidance today). |
| AC-6 | required  | seed-160 backfill is what actually repairs drifted repos on upgrade. |
| AC-7 | important | Renderer audit closes the loop on wrapper loadability; fix only if broken. |
| AC-8 | required  | Validator behavior must be test-locked, bytecode-free, clean. |
| AC-9 | required  | Gated framework edits; vendor-neutrality stays at zero. |


## Progress Log


| Date       | Update                                                                 | Evidence                          |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| 2026-06-22 | Plan created from downstream field feedback (Java-agent consumer, pack `1.8.0+p79p`). All three reported issues verified against the code: `wave_validators.py:58-75` static 4-factor list (no `factor_review` keying, no wrapper validation); `seed-238` has zero factor-awareness; `seed-160` has factor generation/relocation notes but no missing-canonical/malformed-wrapper repair. | `wave_validators.py:58-75`, `seed-050` task 5 (line 48), `seed-238` (0 factor mentions), `seed-160` (lines 101/333/467) |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-22 | **Divergent pre-plan — selected: one coordinated change (validator + seed-238 + seed-160 + renderer audit)** | The `factor_review`-keyed validator contract is the shared spec both seed reconciliations must reference; doing them together guarantees consistency and ships a complete fix (gate + consistent guidance + upgrade repair) rather than a half-fix. The feedback itself notes #1 drives #2/#3. | (B) Validator-only now, defer the seeds — rejected: leaves contradictory seed-238 advice + no upgrade repair shipping; the gate would flag drift that upgrade can't fix and config-review still mis-advises (half a fix). (C) Three separate changes — rejected: more ceremony, and splitting one shared contract across change boundaries risks inconsistency. |
| 2026-06-22 | Reuse the `1p799` "declared-but-missing" validation pattern | Same shape already proven for design-system `external-reference` token sources; consistency across the two surfaces + less novel risk. | Invent a bespoke factor-only check (rejected — needless divergence). |
| 2026-06-22 | Replace the static `_AGENT_ROLE_REQUIRED_PATHS` factor entries with a `factor_review`-keyed check | The static list is itself slightly wrong — it demands `03/05/12/13` regardless of a repo's actual applicability and ignores every other applicable factor. Keying off `factor_review` is the correct generalization. | Keep the static list + add a separate dynamic check (rejected — two overlapping sources of truth). |


## Risks


| Risk                                                                 | Mitigation                                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Dropping the static 4-factor list regresses coverage on wavefoundry's own repo | AC-4 self-hosting check — confirm this repo's `factor_review` marks `03/05/12/13` applicable and their canonical docs exist, so the dynamic check covers at least what the static list did. |
| `seed-160` backfill overwrites an operator-refined canonical factor doc | Merge-safe: regenerate only when the canonical is **absent**; never overwrite existing content (mirror the `factor_review` repo-profile guardrail). |
| Renderer turns out to already emit frontmatter (R4) | Audit-and-skip — record "already-correct"; the downstream repo's issue is then purely stale, resolved by R3's backfill. No fabricated change. |
| New test fixtures reintroduce external-project names | Use generic factor names / `com.example`-style evidence; AC-9 grep gate = 0. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
