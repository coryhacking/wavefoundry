# Code-reviewer seed gains state-and-assumption + failure-path correctness checklists

Change ID: `1p3ix-enh code-reviewer-state-and-assumption-correctness`
Change Status: `implemented`
Owner: framework-maintainer
Status: implemented
Last verified: 2026-06-05
Wave: 1p3iv indexer-drift-skips-empty-files

## Rationale

Operator-surfaced meta-question during the 1p3iw bug fix: "we should have caught this edge case — is there a QA or code review question we should add specifically to address this? How do we address cases like this going forward?" The 1p3iw bug class — code that observes a state, takes a corrective action, but doesn't converge because the assumption "this state = broken" doesn't hold universally — is one of several classes of bugs that share a root cause: **code commits to behavior based on an assumption about input or system state that doesn't hold universally.**

The existing `seed-221` `### Re-entrant Safety` section (three lines) gestures at one specific case (consecutive-call safety) but doesn't enumerate the broader cluster of state-and-assumption checks. A parallel cluster — what happens at *failure paths and boundaries* — is also missing from the seed despite producing equivalent bug yield in practice (subprocess hangs without timeouts, silent error swallowing, off-by-one in boundary arithmetic, unbounded inputs at trust boundaries, recurring diagnostics that train operators to ignore them).

This change expands `seed-221` to make these two clusters explicit and reviewable. Generic phrasing — applies to the category of issues across any consumer project, not just wavefoundry.

## Requirements

1. `seed-221` (`221-code-reviewer.prompt.md`) `### Re-entrant Safety` section is replaced by two new sections under `## What to Check`: `### State And Assumption Correctness` and `### Failure Path And Boundary Correctness`.
2. **State And Assumption Correctness** covers 7 patterns: re-entrant safety (preserved from prior section), convergence after correction, legitimate-state enumeration, idempotence under repeat, cache key completeness, schema evolution backward compatibility, inverse/negation correctness.
3. **Failure Path And Boundary Correctness** covers 6 patterns: error handling and failure paths, resource cleanup on every exit, diagnostic quality, boundary arithmetic, trust-boundary input validation, failure-path test coverage.
4. Each section has a brief intro explaining the bug-class root so a reviewer skimming knows when to apply it.
5. Each pattern has an `*(applies when: ...)* ` hint so reviewers can decide whether the pattern is in-scope for the PR under review — avoids the "13 checklist items, skip the ones that don't feel relevant" failure mode.
6. Phrasing stays generic — no wavefoundry-specific code paths, no project-specific identifiers, no `seed-*` or `1p3*` references in the pattern text itself.
7. Existing sections (`### Acceptance Criteria Coverage`, `### Branch Completeness`, `### Multi-Site Consistency`, `### Test Coverage`, `### Seed Prompt Safety`) remain unchanged.

## Scope

**Problem statement:** Code reviewer seed surface enumerates a narrow set of code-correctness checks, leaving common bug classes (convergence failures, idempotence failures, cache-key collisions, schema-evolution breaks, unbounded inputs, silent error swallowing, subprocess hangs, off-by-one boundaries) without explicit review guidance. The 1p3iw bug class was one instance of a missing-pattern that the existing seed didn't surface.

**In scope:**

- Rewrite `### Re-entrant Safety` (3 lines) → two new sections with 13 patterns total.
- Each pattern includes an "applies when" hint to scope reviewer effort.
- CHANGELOG bullet under `[1.5.0]` `### Changed`.

**Out of scope:**

- Mirroring these patterns into `seed-216` (reality-checker), `seed-225` (red-team), or any other review surface — operator directive was to enhance code-reviewer specifically. Cross-references can be added in a follow-on if the patterns prove valuable from other stances.
- Implementing automated checks for any pattern (e.g., a lint rule for subprocess-without-timeout). Patterns are reviewer-facing checklist items; automation can come later if a pattern's signal is high enough.
- Restructuring the `## Verdict Format` or `## Fix-Now Threshold` sections — the new patterns slot into the existing verdict shape.

## Acceptance Criteria

- [x] AC-1: `seed-221` `### Re-entrant Safety` no longer exists as a standalone section.
- [x] AC-2: `seed-221` contains `### State And Assumption Correctness` with the 7 named patterns (re-entrant safety preserved as one bullet).
- [x] AC-3: `seed-221` contains `### Failure Path And Boundary Correctness` with the 6 named patterns.
- [x] AC-4: Each pattern has a `*(applies when: ...)* ` hint at the start of its description.
- [x] AC-5: Each new section has a brief intro paragraph explaining the bug-class root.
- [x] AC-6: Pattern text does not reference wavefoundry-specific code paths, identifiers, or seed numbers. (Verified — grep across the new sections for `seed-*` / `1p3*` / `wave_*` / `meta.json` / `CHUNKER_VERSION` / `wavefoundry` returned zero hits.)
- [x] AC-7: Existing seed sections unchanged. (Edit was scoped to the `### Re-entrant Safety` → two-new-sections replacement; other sections untouched.)
- [x] AC-8: `docs-lint` returns clean.

## Tasks

- [x] Edit `seed-221`: replace `### Re-entrant Safety` with `### State And Assumption Correctness` (7 patterns) + `### Failure Path And Boundary Correctness` (6 patterns).
- [x] Verify generic phrasing — grep for project-specific identifiers in the new sections.
- [x] Verify existing sections untouched.
- [x] Run docs-lint.
- [x] Add CHANGELOG bullet under `[1.5.0]` `### Changed`.

## Agent Execution Graph


| Workstream         | Owner               | Depends On | Notes |
| ------------------ | ------------------- | ---------- | ----- |
| seed-221 rewrite   | framework-maintainer | —          | Single seed file. |
| Verification       | framework-maintainer | seed-221 rewrite | grep audit + docs-lint. |


## Serialization Points

- `seed-221` is touched by one Edit; no serialization concerns.

## Affected Architecture Docs

N/A — change is confined to the code-reviewer review surface. No domain map / layering / cross-cutting impact.

## AC Priority


| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | The restructure IS the change. |
| AC-2 | required     | First cluster — the load-bearing addition tied to the 1p3iw bug class. |
| AC-3 | required     | Second cluster — operator approved both. |
| AC-4 | required     | "Applies when" hints prevent the "skip if not relevant" failure mode of long checklists. |
| AC-5 | important    | Intros help reviewers route the pattern by intent. |
| AC-6 | required     | Generic phrasing is a load-bearing operator directive. |
| AC-7 | required     | Existing sections are validated review surface — don't drift them. |
| AC-8 | required     | docs-lint clean. |


## Progress Log


| Date       | Update                                              | Evidence |
| ---------- | --------------------------------------------------- | -------- |
| 2026-06-05 | Change admitted into wave 1p3iv; implementation done. | `wave_new_enhancement` + `wave_add_change` → `1p3ix`. |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-05 | Two new sections (State And Assumption + Failure Path And Boundary) rather than one combined section. | The two clusters share the root "code commits to an assumption that doesn't hold universally" but the assumptions are about different things (state vs. failure/boundary). Splitting matches how reviewers actually scan: "I'm reviewing self-healing code → State And Assumption" vs "I'm reviewing error-path code → Failure Path And Boundary." Easier to apply selectively. | (a) One combined "Correctness" section — would dilute the routing signal; reviewers would skim and miss patterns. (b) Three or more sections — finer-grained but adds cognitive load without proportional benefit. |
| 2026-06-05 | Each pattern carries an `*(applies when: ...)* ` hint. | 13 patterns is enough that "skip if not relevant" is a real risk — reviewers cherry-pick. Explicit hints make "in-scope for THIS PR" a clear judgment rather than a vague feeling. | (a) No hints — would shift skim burden onto reviewers and increase miss rate. (b) "Always check" vs "conditional check" tags — too binary; the actual condition matters. |
| 2026-06-05 | Generic phrasing — no wavefoundry-specific identifiers in pattern text. | Operator directive ("keep it generic so it applies to the category of issues, not this project"). seed-221 ships in every consumer pack; project-specific text would either confuse downstream agents or require translation. | (a) Anchor each pattern with a wavefoundry-internal worked example — explicitly rejected by operator. |
| 2026-06-05 | No cross-references in `seed-216` (reality-checker) or `seed-225` (red-team). | Operator directive was code-reviewer specifically. Cross-weaving can come later if these patterns prove valuable from other stances. | (a) Mirror into all three review surfaces immediately — over-weaving in one pass; better to ship the home and iterate. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| 13 patterns is a long checklist; reviewers may skim and skip. | "Applies when" hints reduce skim burden. Section intros explain the bug-class root so a reviewer can route. Future telemetry: if a pattern never produces findings across many reviews, retire or merge. |
| Generic phrasing makes patterns abstract enough that reviewers can't operationalize them. | Each pattern includes a concrete question (not just a category name) plus failure-mode examples ("stale timestamps, leaked entries, growing counters" for re-entrancy). Reviewers don't need to invent the question — it's written. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
