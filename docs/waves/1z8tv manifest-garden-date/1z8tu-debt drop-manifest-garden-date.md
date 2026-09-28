# Drop the Manifest's Last-Gardened Date

Change ID: `1z8tu-debt drop-manifest-garden-date`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-28
Wave: 1z8tv manifest-garden-date

## Rationale

The docs gardener stamps `last_gardened_at` in `docs/prompts/prompt-surface-manifest.json` with today's date whenever a run stamps any other document. Nothing reads the field: in `.wavefoundry/framework/scripts` its only references are the gardener's own writes (`docs_gardener.default_manifest_payload` and `ensure_manifest`). It only produces commits: over the 60 days to 2026-09-28, 21 of the 75 commits that touched the manifest changed nothing but that date.

## Requirements

1. The gardener no longer writes `last_gardened_at`: `default_manifest_payload` omits it, and `ensure_manifest` removes it from an existing manifest, so a target's manifest drops the line once on its next gardening run and never changes again for date reasons.
2. The now-unused date plumbing goes too: `default_manifest_payload` takes no date, and `ensure_manifest` takes neither a date nor the `bump_last_gardened` flag. The other manifest keys and their reconciliation are unchanged.
3. This repository's own manifest drops the field.

## Scope

**Problem statement:** a date field nothing reads churns the manifest in most wave commits.

**In scope:**

- `docs_gardener` manifest writing and its tests.

**Out of scope:**

- `Last verified` stamping of documents, which lint reads;
- the other manifest keys.

## Acceptance Criteria

- [x] AC-1: a gardening run, whether or not it stamps documents, leaves an existing manifest without `last_gardened_at` and otherwise reconciled as before; a manifest that already lacks the key is not rewritten by a later-date run, with or without stamped documents.
- [x] AC-2: a newly created manifest has no `last_gardened_at`.
- [x] AC-3: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] Remove the field and the date and bump parameters from the gardener.
- [x] Update the callers and tests that pass the date or the bump flag: `tests/test_docs_gardener.py` (the `ensure_manifest` and `default_manifest_payload` calls; `test_non_bumping_run_does_not_stamp_the_date` and the steady-state test that asserted the kept date are rewritten to assert removal) and `tests/test_docs_lint.py` (its `default_manifest_payload` call); add the no-rewrite-on-a-later-date tests.
- [x] Drop the field from this repository's manifest; CHANGELOG `[Unreleased]`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Removal | implementer | readiness | One module and its tests |
| Review | combined reviewer | Removal | Code and QA |

## Serialization Points

- `.wavefoundry/framework/scripts/docs_gardener.py`, `.wavefoundry/framework/scripts/tests/`
- `docs/prompts/prompt-surface-manifest.json`
- `CHANGELOG.md`

## Affected Architecture Docs

`N/A`: removes an unread field.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The churn must stop without disturbing reconciliation |
| AC-2 | required | New installs must not reintroduce it |
| AC-3 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Delivery review: code, qa and docs-contract approve. Finding `keyless-nothing-stamped-subtest-stamps` (the "nothing stamped" subtest restamped the session handoff, so it was a stamping run) repaired test-only: the handoff is brought to the run's date first and the run asserts `paths == []`; independently reverified with mutants M5 and M6. Full suite green after the repair | `run_tests.py` 9835 tests across 135 files OK; delivery ledger |
| 2026-09-28 | Implemented. `default_manifest_payload(root)` and `ensure_manifest(root)` no longer take a date or a bump flag; `ensure_manifest` pops `last_gardened_at` on every run, after reconciliation, and the change-only write keeps a key-less manifest untouched. Tests: `test_stamping_run_removes_the_date`, `test_keyless_manifest_is_not_rewritten_on_a_later_date` (subtests with and without a stamped document), `test_new_manifest_has_no_date`, and the entry-point test now asserts removal on a run that stamps nothing; `_minimal_manifest` no longer carries the key, so the empty-run test still reports nothing. Mutation-checked in a scratch copy: keeping the key, re-stamping the date on stamping runs, and a date in the default payload each fail the intended tests. Gapfill: none for retrieval (census via `code_keyword`, reads via `code_read`); the bulk-mechanical edits used a scripted replace with exact-count asserts | `test_docs_gardener` 24 OK; scratch mutants M1-M3 |
| 2026-09-28 | Readiness review: all lanes ready; adopted F3 (the `test_docs_lint` caller named in Tasks) and F4 (AC-1 covers runs that stamp nothing and a manifest that already lacks the key). Confirmed nothing reads the key and no writer (`build_pack`, `upgrade_wavefoundry`) adds it back | readiness review |
| 2026-09-28 | Planned at the operator's request (option 1: remove the field) | `git log` of the manifest over 60 days; census of `last_gardened` references |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Remove the field rather than stamp it only on real content changes | Nothing reads it, so any stamping logic would maintain a value with no consumer | Stamp only when other manifest content changes |

## Risks

| Risk | Mitigation |
| --- | --- |
| A downstream tool reads the field | None in this repository; the one-time removal is noted in the CHANGELOG |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
