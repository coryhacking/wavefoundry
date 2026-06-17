# Code-reviewer: maintainability & dead-code mode (generic, all projects)

Change ID: `1p5zy-enh code-reviewer-dead-code-mode`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Wave: `1p5x8 large-codebase-map`
Last verified: 2026-06-16

## Rationale

The `code-reviewer` lane (seed `221-code-reviewer.prompt.md`) is a **universal role** ("applicable when: any project") and already a **standing council seat at wave close** — so it is the right place to add a maintainability / dead-code dimension: it makes the sweep a *recurring* check inherited by every wavefoundry project on upgrade, not a one-off. This is generic framework capability, not specific to any project; the detection leans entirely on the framework's own generic `code_*` graph tools (present in every install) and the existing review discipline.

The capability: act as a senior engineer doing a code-quality/maintainability pass — find **dead code** (unused functions/files/components/routes/APIs/variables/imports/dependencies), **duplicate logic** to consolidate, **unused UI components**, **overly complex** implementations to simplify, **legacy/abandoned** code, **redundant expensive operations** (repeated reads/fetches/recompute), and **files disconnected** from the application; for each: why it's unnecessary, the impact of removing it, the risks, and a cleanup plan. **Aggressive but safe**: the goal is to simplify and reduce technical debt while never deleting something that is actually load-bearing.

## Requirements

1. **Generic — works in any project, no project-specific content.** Describe patterns and lean on the framework's own tools; no product names, no hardcoded paths, no this-repo internals. Stays within the harness-extension boundary (seed `221` is already declared universal).
2. **Two modes in the one seed.**
   - **Scoped maintainability dimension (runs at every close review):** does *this change* introduce or leave dead code, duplication, over-complexity, or an abandoned/disconnected file **in or adjacent to** the diff? Respects Step-0 scope; feeds the existing fix-now-or-follow-on threshold (small removals fixed in-session; larger cleanups → a dedicated wave).
   - **Whole-codebase cleanup sweep (explicit / periodic):** the full audit across the codebase, invoked on demand — recommended on the **same cadence as the framework-config review** (`238`, at major/minor upgrade). Not run on every wave (expensive + noisy); it is an explicit pass.
3. **Detect with the graph, not grep.** Primary signals: `code_references(symbol)` and `code_callhierarchy(symbol, direction="incoming")` for dead code; `code_graph_community` + the generated **codebase map** for abandoned/disconnected areas; structural/community overlap for duplication; `code_impact`/`code_callgraph` for blast radius. Use the index, don't scan.
4. **"Aggressive but SAFE" — the false-positive guard is mandatory.** Zero static references ≠ dead. Before recommending any deletion, rule out **generic dynamic surfaces**: framework registration / decorators / dependency injection, reflection, plugin / entry-point / hook registration, callbacks, symbols referenced by **string or serialized name**, test fixtures, and the **public API surface**. Corroborate an empty graph result with `code_references`/`code_keyword` (reuse the existing rule at `221` line ~120); treat **EXTRACTED graph edges as heuristic/confidence-weighted** — never delete on a single zeroed edge. (Language-specific advice/AOP exceptions per seed-211 still apply.)
5. **Recommend-only, structured output, never auto-delete.** Each finding: **target** (file + symbol/line), **verdict** (keep / simplify / **remove**), **why** it's unnecessary, **impact** of removing it, **risks** (the dynamic-surface checks above), and a **cleanup plan**. Removals land through a normal reviewed wave — the reviewer recommends, it does not delete.
6. **Categories, generically.** Dead code (functions/files/components/routes/APIs/variables/imports/dependencies); duplicate logic; unused UI components; over-complex implementations; legacy/no-longer-needed code; **redundant expensive operations** (repeated reads/fetches/recompute in a loop or per-tick); abandoned/disconnected files; general technical-debt reduction.
7. **Weave + cross-link (seed-first, no orphans).** Cross-link the **framework-config review** (`238`) and state the boundary: `238` prunes the **agent-operating surface** (seeds/prompts/config/docs); this prunes **code**. Update the council/review seeds and the prompt catalog as needed so the new mode is discoverable.

## Scope

**In scope:**

- A new "Maintainability & Dead-Code" section in seed `221-code-reviewer.prompt.md` covering both modes, the graph-detection method, the false-positive guard, and the recommend-only output — all generic.
- Cross-links: `238` (config review), the council seeds, and (decision below) an optional public command.
- Render the seed change into per-project surfaces (seed-first) + keep `221` generic (the code-reviewer's own "Seed Prompt Safety" check applies to itself).

**Out of scope:**

- The actual act of deleting code in any project (the lane recommends; removals are separate reviewed work).
- Project-specific tuning or examples.
- Changing the `code_*` tools themselves.

## Open decision (settle at prepare)

- **Public command?** Add a discoverable "Codebase cleanup review" entry to the public prompt catalog (like `238` got), or keep the whole-codebase sweep an internal code-reviewer mode invoked by the council/operator. Recommendation: a public command for the on-demand sweep (discoverability), with the scoped dimension remaining internal to the close review.

## Acceptance Criteria

- [x] AC-1: Seed `221` gains a generic Maintainability & Dead-Code section with **both** modes (scoped-at-close + on-demand whole-codebase), no project-specific content; passes the code-reviewer's own seed-safety check.
- [x] AC-2: The detection method is graph-tool-based (`code_references` / `code_callhierarchy` / `code_graph_community` / codebase map) and the **mandatory false-positive guard** (dynamic-surface enumeration + corroborate empty graph results + EXTRACTED-edge caution) is explicit.
- [x] AC-3: Output is recommend-only and structured (target / verdict keep-simplify-remove / why / impact / risks / cleanup plan); the seed states removals land via a reviewed wave and respects the fix-now-or-follow-on threshold.
- [x] AC-4: The mode is cross-linked with `238` (with the surface-vs-code boundary stated) and discoverable (council seeds + catalog/command per the open decision); seed-first parity holds; full suite + docs-lint clean.

## Tasks

- [x] Author the generic Maintainability & Dead-Code section in `221` (two modes; graph detection; false-positive guard; recommend-only keep/simplify/remove output; fix-now threshold tie-in).
- [x] Settle the public-command decision; if yes, add the public prompt + catalog/manifest entry (seed-first).
- [x] Cross-link `238` (surface vs code) + weave into the council/review seeds; render per-project surfaces.
- [x] Tests/parity as applicable (seed renders; manifest parity if a command is added); full suite + docs-lint.

## Affected Architecture Docs

`N/A` — agent-operations seed/prompt change; no runtime/contract behavior change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The generic two-mode section in `221` is the deliverable. |
| AC-2 | required | Graph detection + the false-positive guard are what make it reliable and SAFE. |
| AC-3 | required | Recommend-only structured output keeps removals reviewed, never silent. |
| AC-4 | required | Cross-link + discoverability prevent an orphaned capability; seed-first parity. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Scoped from operator request: add a dead-code/maintainability review to the code-reviewer seed because it is already the close-wave council seat. Generic for all wavefoundry projects (not this repo). Leans on the framework's own `code_*` graph tools + review discipline; reuses the existing empty-graph-corroboration rule and EXTRACTED-edge confidence caution. | `221-code-reviewer.prompt.md`, `238-framework-config-review.prompt.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Add to the code-reviewer seed (`221`), not a new standalone agent | `221` is universal + already a close-wave council seat → the sweep recurs by default and is inherited by every project | A new dedicated cleanup agent (rejected — code-reviewer already owns code quality and runs at close); a one-off prompt (rejected — wouldn't recur) |
| 2026-06-16 | Two modes: scoped-at-close + on-demand whole-codebase | A full-repo sweep every close is expensive/noisy; the scoped dimension fits the per-wave review, the explicit sweep handles the "entire codebase" audit on cadence | Whole-codebase on every close (rejected — noise); scoped-only (rejected — loses the full-audit value the operator asked for) |
| 2026-06-16 | Detect via graph tools + mandatory false-positive guard | Static "unused" is unreliable across dynamic surfaces; the graph + corroboration make "aggressive but safe" real | grep/static-only (rejected — false positives delete live code) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The sweep recommends deleting live code (dynamic/reflection/registration) | Mandatory false-positive guard; corroborate empty graph with `code_references`/`code_keyword`; EXTRACTED-edge caution; recommend-only |
| Seed drifts project-specific | The code-reviewer's own seed-safety check applies to `221`; generic patterns only |
| Overlap/confusion with the config review (`238`) | Explicit boundary: `238` = agent-operating surface, this = code; cross-linked |
| Whole-codebase sweep becomes noise if run every wave | Scoped dimension at close; the full sweep is explicit / on the `238` cadence |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
