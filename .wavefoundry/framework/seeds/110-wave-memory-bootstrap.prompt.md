# 110 - Wave Memory Bootstrap

Intent:

- Create the repo-local wave artifact model used to coordinate non-trivial work over time.

Core rules:

- Waves are the primary unit of coordinated execution and knowledge transfer.
- A wave may contain one small change or multiple compatible feature bundles and workstreams.
- Wave artifacts must support variable depth without forcing different document types for small and large work.
- A wave may contain one or more changes, and each change may contain optional tracked tasks/subtasks when finer execution tracking is useful.
- Changes should normally remain durable across waves; unfinished work is usually carried forward under the same `Change ID` unless the work has truly become a different change.

Wave memory goals:

- Preserve operational truth for the current wave so later agents can tell what is in scope, what is active, and what is done.
- Preserve coordination truth so later agents can tell who is coordinating, who owns which changes or tasks, and how dependencies and review checkpoints constrain execution.
- Preserve assumption truth so invalidated interfaces, changed findings, and frozen decisions remain visible rather than being rediscovered.
- Preserve operating-memory truth when role/persona behavior, operator directives, or high-salience observations must survive compaction or handoff.
- Preserve disposition truth so blocked, deferred, moved, retried, superseded, and completed work are all explicit.
- Preserve carry-forward truth so unfinished work normally continues under the same `Change ID` unless the work has materially changed.
- Preserve handoff truth so a later wave or later session can continue without re-deriving missing context.

Required target-repo outputs:

- `docs/waves/README.md`
- per-wave roots such as `docs/waves/<wave-id>/`
- when the legacy baseline is captured into `wave-0`:
  - `docs/waves/00000 wave-zero-plans-and-specs/wave.md` (single file; no subdirectories required)

Wave artifact anchors:

Every `wave.md` must carry the anchors below, grouped into the natural section layout shown in the left column:

| Section group                   | Required anchors                                                                      |
|---------------------------------|---------------------------------------------------------------------------------------|
| identity and status             | `wave-id`, `Title`, `Status`                                                          |
| scope                           | `Objective`                                                                           |
| coordinator and participants    | `Coordinator`, `Participants`                                                         |
| changes and dependencies        | `Planned or active changes`, `Dependencies`                                           |
| assumptions and findings        | `Current assumptions`                                                                 |
| outputs                         | `Outputs produced or expected`                                                        |
| review and approvals            | `Review checkpoints`                                                                  |
| journal and evidence            | `Journal refs`, `Journal Watchpoints`, optional `Salience / Impact` where decision-relevant |
| completion and handoff          | `Completion criteria`, `Handoff or next-wave notes`                                   |
| disposition (when applicable)   | `deferred`, `moved`, `retry`, or `blocked` for incomplete work                        |
| changes inside the wave         | change-level anchors in `## Changes` / `## Corpus` (see below)                        |

`wave-id` is the folder name under `docs/waves/`. **`Change ID` does not belong in the wave record header** — it lives in the body (`## Changes` or `## Corpus`).

Wave identity rules:

- `wave-id` should be the folder-safe identifier for the wave under `docs/waves/`.
- Reserve `00000 wave-zero-plans-and-specs` for the closed historical baseline wave synthesized from pre-wave legacy corpora discovered during init.
- Use `docs/waves/00000 wave-zero-plans-and-specs/wave.md` as the single baseline-wave record. Keep all content inline — corpus inventory, normalization notes, review checkpoints, journal refs — rather than splitting across subdirectories. A flat single-file wave is the preferred layout.
- Give the wave-0 baseline a final `Title` that starts with `Legacy`; prefer `Legacy` for a broad mixed corpus or generate a more specific title such as `Legacy plans and specs` when the captured baseline has a clearer focus.
- Use the `<prefix> <slug>` form for normal waves (from `lifecycle_id.py --kind wave --slug <slug>`), such as `00057 routine-behavior-contract`; do not insert a literal `-wave` token — that is not what the generator emits.
- Use the `<id-prefix>-<kind> <slug>` form for change IDs, where `<kind>` is one of: `bug`, `feat`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`; for example `00051-bug runtime-retry` or `1mgvh-ref plan-spec-consolidation`.
- Generate both forms with `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>`; the script uses 4 Crockford Base32 digits for hours since the configured lifecycle epoch in `docs/workflow-config.json` (`lifecycle_id_policy`) plus one Crockford minute-bucket character; all output is lowercase.
- A wave may contain one or more changes; keep those change references inside the wave artifact instead of making the change ID the folder key.
- When a wave-0 baseline exists, treat it as closed historical input (completed scaffold) rather than as an active delivery wave; subsequent execution waves begin after wave-0 is fully closed.
- Keep journals, personas, workflow memory, and shared core docs in their canonical homes; the baseline wave record should reference those promoted outputs rather than duplicating them inside the legacy baseline folder.

Scalable change model:

- changes can be atomic or composite
- a wave with one simple change can stay compact as long as the required wave anchors remain explicit
- changes may represent:
  - feature
  - feature slice
  - story
  - task
  - review lane
  - integration lane
  - docs lane
- composite changes may contain optional tasks, subtasks, nested workstreams, or child work records inside the change document
- large waves should make retries, partial failure, and moved work explicit rather than implying clean completion

Required change anchors in normal wave records:

- `Change ID`
- `Change Status`
- optional `Previous Change Status`
- `Depends On` when a change depends on another admitted `Change ID`

Optional task/subtask anchors inside a change document when finer tracking is useful:

- `Task ID` or `Subtask ID`
- `Type`
- `Title` or `Scope`
- `Status`
- `Owner`
- `Depends On`
- `Inputs`
- `Expected Outputs`
- `Review Requirements`
- `Blockers or Risks`
- `Children` or `Workstreams` when composite

Recommended change-level anchors when a wave tracks multiple changes:

- `Change ID` — belongs in the body of `wave.md` (inside `## Changes` or `## Corpus`), **never** in the wave record header
- change title or scope
- `Change Status` in this wave
- change-specific tasks/subtasks
- change-specific risks or review requirements when they differ from the rest of the wave

Recommended participant anchors when a participant is named explicitly:

- participant identifier or role
- lane type (`implement`, `review`, `challenge`, `approve`, `coordinate`)
- owned changes or tasks
- reporting expectations
- escalation or blocking authority when relevant

Recommended assumption anchors:

- assumption identifier
- status (`frozen`, `tentative`, `invalidated`, `confirmed`)
- affected changes, tasks, or workstreams
- evidence or rationale

Recommended wave-event anchors when meaningful:

- event type
- affected changes or tasks
- triggering finding
- salience or impact signal when it affects routing, escalation, preservation, or future behavior
- coordinator action
- resulting state change

Wave status model:

- `planned`
- `active`
- `blocked`
- `completed`
- `superseded`

Recommended change status model:

- `planned`
- `ready`
- `active`
- `blocked`
- `review`
- `complete`
- `deferred`
- `moved`
- `retry`
- `superseded`

Guardrails:

- Only one wave should normally be `active` for a given feature thread unless evidence from the repository justifies overlap.
- Parallelism is allowed inside a wave only after its shared assumptions and interfaces are stable enough.
- Keep the artifact contract stable enough that later prompts, scripts, and agents can recover wave state, decisions, and carry-forward intent without requiring identical prose layout.
- Do not split a change into a new `Change ID` merely because the wave ended; carry unfinished work forward by default and split only when the remaining work is materially different.
- Do not wait for closure to preserve compaction-sensitive operating memory. Critical or high-salience role/persona observations may be journaled during planning, implementation, review, handoff, or closure.
- Keep salience lightweight in wave records. Use it only when it changes admission priority, reviewer/persona routing, escalation, handoff, memory preservation, or future behavior.
- **State each wave-level rule once in its most natural `wave.md` section; cite rather than restate.** `wave.md` is a coordination record, not a marketing summary: every fact (objective, admitted changes, serialization points, protected surfaces, reviewer roster, completion criteria, etc.) should appear **in exactly one section**, namely the section whose anchor it most naturally belongs to. If another section needs to reference the fact, cite the anchor (e.g. "see `## Changes`", "per `Serialization Points` below") instead of repeating the prose. Details that belong in a change doc (`## Requirements`, `## Acceptance Criteria`, `## Tasks`, `## Risks`, `## Decision Log`, `## Agent Execution Graph`) **must stay in the change doc** — `wave.md` cites them, it does not duplicate them. The admitted-changes list plus the `## Changes` table is the authoritative in-scope record; prose elsewhere in `wave.md` must not re-narrate what those entries already say. Keep the scaffolding sections (`Objective`, `Participants`, `Protected Surfaces`, `Knowledge Transfer Plan`, `Persona Review Plan`, `Journal Watchpoints`, `Review Checkpoints`, `Readiness Checkpoints`, `Serialization Points`, `Completion Criteria`, `Wave Summary`, `Changes`) — just state each bullet inside them **once**. `Wave Summary` is populated at closure and must be retained empty (`*(Populated at closure.)*` or equivalent placeholder) pre-closure rather than dropped.
- When bootstrapping from legacy material: record the closed wave-0 baseline in `docs/waves/00000 wave-zero-plans-and-specs/wave.md` with a `## Corpus` table indexing all captured plans; run applicable review lanes and document real findings per change type; populate journal files with distilled lessons; update `docs/references/project-context-memory.md` and other core memory docs with reusable workflow guidance; then admit subsequent execution waves only after wave-0 is fully closed with all reviews, journals, and core-doc promotions recorded.
