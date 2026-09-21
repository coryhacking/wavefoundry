# Close Wave Folder Cleanup

Change ID: `1yk53-enh close-wave-folder-cleanup`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-21
Wave: 1ykqj close-wave-folder-cleanup

## Rationale

The operator had to request folder cleanup separately while closing 1ycrj. Make cleanup an ordinary close-time agent task so a future reader finds the final result and its evidence without scratch files or competing final summaries. Keep the change to concise instructions; no new deletion automation, evidence format or validator.

## Requirements

1. Before final docs validation and closure, inspect the current wave folder and organize established wave-owned artifacts; timestamps alone do not establish ownership.
2. Keep wave.md, admitted change docs and the authoritative events.jsonl ledger in place. Preserve unique review evidence, reproducible probes and historical fingerprints required to substantiate claims. Do not rewrite immutable ledger evidence to tidy paths.
3. Remove only verified disposable scratch output and redundant copies with no unique evidence or live reference. Group movable supporting artifacts under evidence/ when useful; retain ledger-cited paths or a durable reference-preserving mapping. Update mutable references and verify they resolve. Do not impose a layout migration or touch other waves/unrelated files.
4. Consolidate repeated status narration into a clear final outcome and evidence index in an existing wave summary or delivery report. Record cleanup disposition, including retained artifacts, then run existing validation. Finalize Feature consumes the same guidance; no new computational gate or deletion tool.

## Scope

Intended edits: .wavefoundry/framework/seeds/190-finalize-feature.prompt.md, docs/prompts/close-wave.prompt.md, docs/prompts/finalize-feature.prompt.md, CHANGELOG.md. Canonical seed owns behavior; local close prompt carries the same checklist and finalize prompt points to it. The existing report-archive task must use evidence of wave ownership rather than date alone.

Protected: review ledger/history, unique evidence, admitted documents, unrelated files and closed-wave archives. Write owner: coordinator. Independent docs-contract reviewer checks instruction clarity and examples; council seats are read-only. No runtime code, automated deletion, required report file, retrospective folder migration, new tests or validator changes.

## Acceptance Criteria

- [x] AC-1: Canonical and local closure instructions explicitly place cleanup before final validation, preserve authoritative files and unique evidence, and bound removal/moves by ownership and reference checks; a reviewer can reject a destructive cleanup scenario from the wording.
- [x] AC-2: Close and single-change finalization reach one consistent cleanup policy without a new machine gate or required artifact; document comparison and scenario walkthrough verify this.
- [x] AC-3: The documents changed by this work validate; no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the concise canonical/local cleanup checklist and finalize pointer.
- [x] Independently review scratch, duplicate, unique-evidence and ledger-reference scenarios; validate docs and current framework receipt.

## Serialization Points

- `.wavefoundry/framework/seeds/190-finalize-feature.prompt.md`
- `docs/prompts/close-wave.prompt.md`
- `docs/prompts/finalize-feature.prompt.md`

## Affected Architecture Docs

N/A: instruction-only clarification of closure hygiene; no runtime module boundary, authority format or computational gate changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Cleanup must preserve evidence. |
| AC-2 | required | One consistent closure policy. |
| AC-3 | required | Authored docs remain valid. |

## Decision Log

| Date | Decision | Reason / alternatives |
| --- | --- | --- |
| 2026-09-21 | Add a bounded agent checklist | Chosen: directly addresses the repeated operator request. Automatic deletion risks destroying audit evidence and adds machinery; a mandatory folder schema creates needless archive migrations. Neither is needed. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Brief: make current-wave cleanup a normal close step while retaining authoritative evidence and references; inspect canonical seed 190 and local close/finalize prompts | Prior 1ycrj cleanup; seed 190 tasks 15–19 |

| 2026-09-21 | Readback / Thought: add a four-part cleanup checklist before closure validation, preserve ledger-cited paths, unique evidence and other waves, and make dates discovery-only. Seed/local detailed sections match; single-change finalization points to the same rule. No new tool, gate or artifact | Current readiness approved; pre-implementation memory confirms handoff remains active until closure succeeds |

| 2026-09-21 | Observe: canonical/local cleanup blocks are identical; Finalize pointer precedes closure state. Independent docs delivery review passed seven scenarios and rejected an in-memory missing-protection mutation. Full suite passed 9,452 tests (12 skips), current green receipt independently hash-checked; docs validation clean. No new memory candidates | delivery-review.md; test-cache.json hash 2c47637fff44a76d15a681a5e64539c39559617b2da03d9541323cb8a3c9ba89 |

## Risks

| Risk | Mitigation |
| --- | --- |
| Tidying discards audit evidence or breaks references | Ownership, uniqueness and reference checks; retain historical ledger paths. |
| Checklist grows into another gate | Agent instruction only; existing validation, no mandatory new report. |
