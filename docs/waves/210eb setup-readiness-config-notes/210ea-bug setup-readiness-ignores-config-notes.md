# Setup readiness ignores configuration notes

Change ID: `210ea-bug setup-readiness-ignores-config-notes`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: 210eb setup-readiness-config-notes

## Rationale

`wf setup --check` reports `setup_inputs_changed` when the recorded setup stamp differs from the current setup inputs. For `docs/workflow-config.json`, `setup_readiness._configuration_identity` hashes the whole `indexing`, `setup`, `platforms`, `embedding` and `providers` sections. The `setup` section carries a `notes` prose string, so a wording edit to that string makes readiness report that setup must run again, although setup reads nothing from it. The function's own comment already says notes do not change setup fitness, but the code never removed them. In this repository the stamp of 2026-10-08 differs from the current configuration only in `setup.notes` text (and in the `VERSION` file and framework sources, which are correct triggers and stay).

## Requirements

1. `_configuration_identity` leaves out a `notes` key at the top level of each hashed `docs/workflow-config.json` section before digesting it. Every other key in those sections still counts.
2. No other identity input changes: framework source hashes, `VERSION`, the defaults file, launch surfaces and the environment projection are compared as before.
3. Stamps written before this change carry a digest that included `notes`, so where `setup.notes` is non-empty, checks keep reporting `setup_inputs_changed` until the next `wf setup` or upgrade rewrites the stamp. Because `setup_readiness.py` is itself a hashed source, that `wf setup` runs after this fix lands. No migration is added.
4. Behaviour is the same on Windows, macOS, Linux and WSL2: the change is a dictionary filter before hashing, with no path, process or filesystem difference.

## Scope

**Problem statement:** a prose-only edit to `setup.notes` falsely reports that setup must run again.

**In scope:** Requirement 1 in `.wavefoundry/framework/scripts/setup_readiness.py` and a regression test in `test_setup_readiness.py`.

**Out of scope:**

- Source-hash and `VERSION` triggers, which correctly fire after framework edits.
- A self-hosting exemption for this repository.
- Nested `notes` keys below the section top level; none exist today.

## Acceptance Criteria

- [x] AC-1: With a stamp written for a configuration, changing only `setup.notes` leaves the assessment `ready`, and changing a real `setup` key (for example a timeout) makes it `action_required` with `setup_inputs_changed`.
- [x] AC-2: The new test fails against the unpatched `_configuration_identity` in a scratch copy.
- [x] AC-3: One whole-suite `--no-cache` run passes with a fresh green receipt.

## Tasks

- [x] Apply Requirement 1 and add the regression test.
- [x] Run the AC-2 mutant in a scratch copy.
- [x] Run the whole suite for the receipt.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| readiness | implementer | none | Requirement 1 and test |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_readiness.py`, `.wavefoundry/framework/scripts/tests/test_setup_readiness.py`

## Affected Architecture Docs

N/A: a hashing filter inside one module, with no boundary, flow or verification-architecture change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The fix itself. |
| AC-2 | required | The test must catch the old behaviour. |
| AC-3 | required | The receipt must be current before close. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Planned after diffing the 2026-10-08 setup stamp against the current tree: 17 hashed sources, `VERSION` and `docs/workflow-config.json` differ, and the configuration difference is only `setup.notes` text. The environment projection matches. | `wf setup --check --json` reason `setup_inputs_changed` |
| 2026-10-18 | Implemented under `framework_edit_allowed`: `_configuration_identity` drops the top-level `notes` key of each dict section; the comparison text in `assess_setup` is unchanged. New test `test_setup_notes_edit_after_stamp_does_not_request_setup`. AC-2: with the filter removed in a scratch copy the test fails (`'action_required' != 'ready'`). Delivery code and QA lanes approved; QA mutants: filter removed, whole `setup` dropped and `setup` dropped beside the filter were caught, while a drop-all-strings filter and a non-dict section set to `None` were missed. The test then gained a string-valued setting and a list section, and both mutants are now caught. Gapfill: shell and scratch copies for mutants. | scratchpad ac2-210eb, del-210eb |
| 2026-10-18 | AC-3: whole suite `--no-cache` ran 11902 tests, OK (12 skips), with a fresh green receipt. | scratchpad 210eb-full.txt; `.wavefoundry/framework/test-cache.json` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-18 | Drop only the top-level `notes` key per section. | Smallest change that removes the observed false positive. | Exempt the framework source repo (rejected: the source triggers are correct); recursive prose filtering (rejected: no nested notes exist). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A future setting named `notes` that setup reads would be ignored. | `notes` is prose by convention across workflow-config; the regression test names the key. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
