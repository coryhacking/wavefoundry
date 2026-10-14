# Export the container status contract

Change ID: `20nnj-ref export-container-status-contract`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-14
Wave: `20nnk distribution-status-fixtures`

## Rationale

Item/change status tables are exported, while wave/container classifications are repeated across lifecycle, renderer, memory and context-efficiency code. A shared API should preserve the distinct meanings of known statuses, nonclosed work and the single OPEN slot.

## Requirements

1. Export immutable constants for supported container statuses and the OPEN-slot subset beside existing status tables; derive values from existing lifecycle writes and validators, accounting for documented legacy states.
2. Replace equivalent complete-status and OPEN-slot literal sets across all framework consumers with the exported constants. Keep operation-specific transition subsets explicit; do not substitute a broad set where a narrower rule is intended.
3. Preserve existing handling of planned/readied, paused, closed, legacy and unknown values, and preserve item/change status semantics and the single-OPEN guard.
4. Document the import seam and meaning of open versus merely nonclosed; no new distribution override or new lifecycle status.

## Scope

Shared lint constants and equivalent consumers discovered by status classification, plus tests/docs. No status transition redesign, record migration or expanded OPEN eligibility.

## Acceptance Criteria

- [x] AC-1: Exported status collections cover the existing supported lifecycle states and identify exactly the current OPEN-slot states through behavioral transition controls.
- [x] AC-2: Representative lifecycle, lint, renderer, memory and context-efficiency consumers agree on equivalent classifications, while operation-specific subsets retain their old behavior.
- [x] AC-3: Planned/readied and paused records do not occupy the OPEN slot; unknown and legacy values preserve their documented acceptance/refusal behavior.
- [x] AC-4: An importing distribution can use the constants without loading the server or changing the item/change status API.

## Tasks

- [x] Inventory status producers/classifiers and document legacy and operation-specific distinctions.
- [x] Export constants and replace only equivalent repeated sets; add behavior/import controls.
- [x] Document the seam and record the consumer census in the wave summary.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | Readiness approval | Sole source write owner |
| Independent review | Required specialist lanes | Reviewable implementation | Read-only; report findings to coordinator |

## Serialization Points

Only the implementer edits the declared targets after readiness. Reviewers are read-only; the coordinator owns lifecycle records. Shared runner, server, policy, seed and prompt changes serialize with adjacent waves. Seed/default/prompt changes require existing edit guards and renderer ownership; do not hand-edit generated regions.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/__init__.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`
- `.wavefoundry/framework/scripts/tests/`
- `.claude/hooks/session-capture.py` (generated through the platform renderer only)
- `docs/specs/mcp-tool-surface.md`

Integration fixtures under the admitted tests owner must include the newly required wave_lint_lib package in miniature feature packs and explicitly import the lazy validator consumer before checking its fresh parser after reload. Preserve the real bundle exit/checkpoint assertions, lazy package boundary and parser identity oracle. Regenerate the committed hook through its canonical renderer; do not hand-edit it.

## Affected Architecture Docs

docs/specs/mcp-tool-surface.md and docs/architecture/data-and-control-flow.md: public status vocabulary and OPEN-slot semantics.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-2 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-3 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-4 | required | Establishes the scoped behavior or preserves its boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Planned from current source inspection; implementation and qualification pending. | Requirements and declared review targets above. |

| 2026-10-14 | Readback: Export immutable supported container statuses and the OPEN subset beside item tables; replace equivalent OPEN classifiers only. Before, repeated active/implementing sets can drift; after, distributions import one contract while planned/readied/paused remain outside OPEN and operation-specific/legacy handling stays unchanged. | Status constants, listed renderer/context/server/memory/lint consumers, focused tests and contract docs; all admitted ACs. |

| 2026-10-14 | Observe: ARCH-DEL-IMPORT independently reproduces cold context_efficiency import failure through the package eager CLI import. Add package __init__.py to the declared owners for the existing lightweight/equivalent consumer contract; propose lazy public main with cold context-first/constants-first and actual CLI regression controls. | AC-2 reopened. Canonical initial worker failures and independent chair cold-process probe agree. Focused owner readiness update and recorded repair-start precede code edits. |

| 2026-10-14 | Repair cycle 1 verification: Cold context/constants orders and real CLI success/failure equivalence pass. Restoring eager import fails test_cold_context_first_and_constants_first_do_not_cycle_or_import_server; dropping lazy main return fails test_package_main_keeps_noarg_api_and_actual_cli_return_behavior (each one assertion failure, no errors/skips). Final distribution file passes 47 tests under each second/declared profile; final CLI fixture control passes default. | Updated 28-file fingerprint 42f2f93278db003d75ba896a6046ad5b0402bd87be890cf44b02adfd12cae8f4; independent reverification and final combined qualification pending. |

| 2026-10-14 | Combined qualification found the committed generated hook stale, a miniature pack missing wave_lint_lib, and a reload test assuming the formerly eager validator import. AC-2 reopened; exact generated output and fixture propagation are admitted above. | Independent temporary-fixture package addition makes the unchanged real-bundle exit/checkpoint test pass. Original cold-import repair remains terminal; do not restore eager loading. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Select immutable shared constants with equivalent-consumer replacement. | Give framework consumers one supported definition of container statuses and the OPEN-slot subset. | Document copied literals only: downstream drift remains. Add a configurable state machine: changes lifecycle authority and is unnecessary for a read-only import seam. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Contract regression or scope expansion | Conflating nonclosed work with OPEN would reject parallel preparation or admit multiple active waves. Preserve narrow operation subsets and exercise paused/planned controls. |

## Session Handoff

Planned only. Prepare/readiness must pass before code edits. Keep durable decisions and final command/results in wave.md; compact execution detail stays in ignored cache or temporary storage. No new permanent evidence folder. See docs/agents/session-handoff.md for sequencing.
