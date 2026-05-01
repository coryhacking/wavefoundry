# Wave Admission Relocates Change Docs

Change ID: `129pc-enh wave-admit-relocates-change-doc`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-04-30
Wave: `129p8 mcp-docs-search-reliability`

## Rationale

Wavefoundry's lifecycle surface currently encodes two conflicting rules about where admitted change docs live.

Some operator-facing workflow docs already describe `Add change to wave` as the step that relocates a consolidated change doc from `docs/plans/` into `docs/waves/<wave-id>/`. But the rendered prompts, canonical seeds, and MCP lifecycle implementation still treat relocation as part of `Prepare wave`. That split creates unnecessary ambiguity:

- operators cannot tell whether admission is supposed to be metadata-only or a file move
- MCP lifecycle tooling cannot guarantee that the wave folder is the complete working set immediately after admission
- `Prepare wave` carries a mixed responsibility of readiness review plus first-time filesystem normalization
- lifecycle docs drift because different surfaces describe different move points

The cleaner contract is:

- `Add change to wave` admits the change and relocates the file into the active wave immediately
- `Prepare wave` validates that all admitted change docs are inside the wave folder and repairs drift if a file is missing or still staged elsewhere

That gives the wave folder a simpler meaning as soon as a change is admitted: it becomes the active working home for the wave's canonical change docs, while `Prepare wave` remains a defensive readiness gate rather than the primary relocation step.

## Requirements

1. `Add change to wave` must relocate the admitted change doc from `docs/plans/<change-id>.md` to `docs/waves/<wave-id>/<change-id>.md` as part of successful admission.
2. The admission contract must remain idempotent enough for recovery-oriented workflows:
   - if the admitted file is already in the target wave folder, admission should not fail solely because the move already happened
   - if the file cannot be found in either the staging path or the target wave path, the tool must return a structured error
3. `Prepare wave` must validate that every admitted change doc exists under `docs/waves/<wave-id>/`.
4. If an admitted change doc is still present under `docs/plans/` during `Prepare wave`, and the target wave path is missing, `Prepare wave` must relocate it into the wave folder as a repair step before evaluating readiness.
5. If both staged and relocated copies exist, `Prepare wave` must return a clear diagnostic rather than silently choosing one, unless an existing repository policy already defines a deterministic safe repair.
6. `Prepare wave` must treat admitted change placement as part of readiness validation, but no longer as the normal first-time relocation step.
7. `Remove change from wave` contract and docs must remain coherent with the new behavior. If an active admitted change is removed from a wave, the doc should return to the appropriate non-wave location according to current lifecycle rules.
8. The prompt docs, seed docs, lifecycle overview docs, and MCP tool contract must all consistently describe relocation as admission-time behavior with prepare-time validation and repair.
9. The canonical framework seeds must be updated so seeded target repositories inherit the same lifecycle rule.
10. MCP lifecycle tools must reflect the new filesystem behavior and return structured diagnostics for relocation/repair failures without leaving the wave record and filesystem in contradictory states.
11. Tests must cover:
    - successful move on `Add change to wave`
    - add-change idempotency when the file is already relocated
    - prepare-time repair when the admitted file is still in `docs/plans/`
    - prepare-time diagnostics when duplicate staged and wave copies exist
    - remove-change behavior remains coherent after the relocation point changes
12. This change must not weaken the repository-code stage gate. Implementation still requires a clean `Prepare wave` pass as the immediately preceding lifecycle step.

## Scope

**Problem statement:** the lifecycle currently disagrees about when admitted change docs move into the wave folder, and the MCP implementation does not yet make the wave folder the canonical home at admission time.

**In scope:**

- changing the lifecycle rule so admission relocates the change doc immediately
- prepare-time validation and repair of admitted change placement
- MCP lifecycle implementation updates for `wave_add_change`, `wave_prepare`, and any directly affected helpers
- prompt docs and workflow docs that describe admission, prepare, and removal behavior
- canonical seed updates so the behavior propagates to target repositories
- tests covering relocation, repair, diagnostics, and remove-change coherence

**Out of scope:**

- broader redesign of wave lifecycle phases
- changing the requirement that `Prepare wave` must pass immediately before implementation
- moving closed-wave archival behavior
- altering change-document content requirements
- unrelated MCP search/indexing work already covered by `129p7-bug mcp-docs-search-reliability`

## Acceptance Criteria

- AC-1: After a successful `Add change to wave`, the admitted change doc exists at `docs/waves/<wave-id>/<change-id>.md` and no longer exists only as the active canonical copy in `docs/plans/`.
- AC-2: `wave_add_change` updates the wave record and filesystem coherently; if relocation fails, the tool returns a structured error and does not leave a misleading success state.
- AC-3: `Prepare wave` reports a clean readiness path when all admitted changes are already inside the wave folder.
- AC-4: `Prepare wave` repairs an admitted change doc that is still staged in `docs/plans/` when the wave copy is missing, then continues readiness evaluation.
- AC-5: `Prepare wave` returns a clear diagnostic when duplicate staged and wave copies exist and automatic repair is unsafe or ambiguous.
- AC-6: `Remove change from wave` behavior and documentation remain coherent with admission-time relocation.
- AC-7: Prompt docs, lifecycle docs, and canonical seeds consistently describe relocation as part of `Add change to wave`, with `Prepare wave` validating and repairing placement.
- AC-8: MCP lifecycle tests cover add-change relocation, prepare-time repair, duplicate-copy diagnostics, and remove-change behavior after the contract shift.

## Tasks

- Audit all local docs, prompt docs, and seed docs that currently describe prepare-time relocation versus admit-time relocation.
- Decide the exact transactional behavior for `wave_add_change` so wave-record mutation and file relocation stay consistent on error.
- Update `.wavefoundry/framework/scripts/server.py` so `wave_add_change_response` relocates the file and returns structured diagnostics on failure.
- Update `.wavefoundry/framework/scripts/server.py` so `wave_prepare_response` validates admitted file placement and repairs the simple missing-wave-copy case.
- Decide and document the duplicate-copy policy for `Prepare wave`.
- Review whether any shared helper should own change-doc path resolution so add/prepare/remove stay consistent.
- Update `docs/prompts/add-change-to-wave.md`.
- Update `docs/prompts/prepare-wave.md`.
- Update `docs/prompts/remove-change-from-wave.md`.
- Update `docs/prompts/index.md` and any lifecycle overview docs that summarize the move point.
- Update `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`.
- Update any additional canonical seeds that currently encode prepare-time relocation, keeping the touched seed set disciplined and consistent.
- Update `docs/specs/mcp-tool-surface.md` if the lifecycle tool contract or diagnostics need explicit clarification.
- Add or update tests under `.wavefoundry/framework/scripts/tests/` for add/prepare/remove relocation behavior.

## Agent Execution Graph


| Workstream            | Owner         | Depends On        | Notes                                                                    |
| --------------------- | ------------- | ----------------- | ------------------------------------------------------------------------ |
| contract-audit        | planner       | —                 | Lock down the new lifecycle rule and locate every conflicting surface    |
| mutation-design       | planner       | contract-audit    | Define add/prepare/remove behavior, repair policy, and failure semantics |
| lifecycle-implementation | implementer | mutation-design | Update MCP add/prepare/remove behavior and shared helpers                |
| tests                 | implementer   | lifecycle-implementation | Cover relocation, repair, and duplicate diagnostics                |
| docs-and-seeds        | implementer   | mutation-design, tests | Reconcile prompts, workflow docs, spec, and canonical seeds        |
| review                | code-reviewer | lifecycle-implementation, docs-and-seeds | Check contract consistency and edge-case handling    |


## Serialization Points

- `server.py` lifecycle mutation behavior should be settled before updating prompt wording broadly, otherwise docs may overfit a transient implementation detail.
- Any helper that resolves change-doc locations should be shared across add/prepare/remove in one pass to avoid contract drift.
- Seed updates should follow the local prompt/doc decision so the framework exports one stable rule instead of mirroring a draft.
- `docs/specs/mcp-tool-surface.md` must be updated in the same change if MCP lifecycle error or repair semantics become externally visible.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md`

`docs/ARCHITECTURE.md` and the deeper architecture set are likely `N/A` unless implementation work reveals a meaningful lifecycle-control-flow change worth documenting beyond the MCP tool contract.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Admission-time relocation is the primary contract change this plan exists to deliver. |
| AC-2 | required | Wave-record and filesystem coherence are mandatory for a mutation tool that moves tracked artifacts. |
| AC-3 | required | `Prepare wave` must accept the new steady state where admitted docs are already inside the wave folder. |
| AC-4 | required | The requested behavior explicitly includes prepare-time repair when a doc was not moved earlier. |
| AC-5 | important | Duplicate-copy diagnostics are important for safe recovery, but they are a secondary edge-case path after the main move/repair flow. |
| AC-6 | required | `Remove change from wave` must remain coherent or the lifecycle becomes inconsistent after relocation moves earlier. |
| AC-7 | required | Prompt docs, lifecycle docs, and canonical seeds all need to converge on one rule to remove the current drift. |
| AC-8 | required | Lifecycle mutation behavior needs regression coverage because it changes both filesystem and wave-record semantics. |


## Progress Log


| Date       | Update         | Evidence                 |
| ---------- | -------------- | ------------------------ |
| 2026-04-30 | Plan authored. | This conversation thread |
| 2026-04-30 | Prepare wave completed; change relocated into active wave and marked ready. | `docs/waves/129p8 mcp-docs-search-reliability/wave.md` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-04-30 | Move admitted change docs at `Add change to wave`, then let `Prepare wave` validate and repair placement. | This makes the wave folder the canonical active working set immediately after admission while preserving a defensive readiness gate. | Keep relocation only at `Prepare wave`; rejected because it preserves the current ambiguity and delays filesystem normalization. |
| 2026-04-30 | Keep `Prepare wave` as the stage gate immediately before implementation even though relocation moves earlier. | Readiness review and reviewer-lane selection still belong at prepare time. | Treat successful admission as sufficient to start implementation; rejected because it weakens the existing gate. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `wave_add_change` can leave `wave.md` and the filesystem out of sync if relocation is not handled transactionally. | Define and test failure semantics so admission is only recorded as successful when both metadata and file placement are coherent. |
| Duplicate staged and relocated copies may create ambiguity during repair. | Make duplicate-copy handling explicit and diagnostic-first unless a safe deterministic resolution is established. |
| Prompt docs and seeds may drift again because multiple surfaces describe the move point. | Audit all relocation references and update them in one coordinated change. |
| Remove-change behavior may become confusing after the relocation point shifts earlier. | Update add/prepare/remove docs and tests together instead of treating remove as a follow-on cleanup. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
