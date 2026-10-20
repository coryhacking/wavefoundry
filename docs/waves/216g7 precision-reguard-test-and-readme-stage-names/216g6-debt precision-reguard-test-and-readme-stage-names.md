# Test the unprovenanced-escalation precision re-guard; drop shortcut names from the README diagrams

Change ID: `216g6-debt precision-reguard-test-and-readme-stage-names`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-19
Wave: 216g7 precision-reguard-test-and-readme-stage-names

## Rationale

Two leftovers from the waves closed on 2026-10-19 (`26786c70`).

- **The guard has an untested site.** Wave 2136z (change 2134z) re-applies the implicit precision guard in two places where a graph-only build is widened to embed. Three delivery reviewers removed the re-guard after the unprovenanced-layer escalation in `indexer.build_index`, and every test still passed. The code is correct, but the second site has no test that would catch its removal.
- **The README diagrams still use shortcut phrases.** Change 2134x reworded two `.wavefoundry/README.md` lines so they no longer name lifecycle shortcut phrases. The diagrams, the one-line flow and the shortcut list in the same file still use the shipped phrases, which a renamed distribution's README then shows wrongly.

## Product Intent

- **Maintainers:** if a later edit drops either re-guard, a test fails, so a graph-only build that widens to embed cannot quietly re-embed at a changed precision.
- **Readers of a distribution's README:** they see lifecycle stage names and a pointer to the distribution's own shortcut index, not phrases the distribution renamed.
- **Boundaries:** this change adds a test and rewords documentation. No product behaviour changes. AC-1 and AC-2 test the outcome.

## Requirements

1. A test in `test_indexer.py` builds a store that reaches the unprovenanced-layer escalation in `build_index`: a layer that `layer_available` reports while `model_versions` has no entry for it, with the code layer recorded at full precision and int8 predicted. The store must also pass `index_compatibility.check_connection`. On a completed epoch that check refuses a populated layer with no recorded model before the escalation runs, so the fixture uses a state that passes it, for example:
   - an uncompleted epoch (`build_state` not `complete`, generation 0) whose layer vectors remain;
   - a completed store whose docs chunks and vectors are removed while `content` still lists docs.
   On that store, a graph-only build without an explicit full request must:
   - log the escalation;
   - return the implicit-precision refusal;
   - construct no embedder;
   - leave the recorded `model_versions` unchanged.
2. The test fails when the re-guard after the unprovenanced-layer escalation is removed. It must pass or fail independently of the model-set re-guard. Each existing re-guard test keeps catching its own site.
3. The rule that sets the README's scope: every line of `.wavefoundry/README.md` that names a renameable lifecycle shortcut phrase (one a vocabulary profile can rename; fixed shortcuts such as `Upgrade Wavefoundry` stay) (for example `Plan change`, `Create wave`, `Prepare wave`, `Implement wave`, `Review wave`, `Close wave`, `Add change`) is reworded.
   - The flow diagrams and the one-line flow name the stage without its tier noun (Plan, Create, Admit, Prepare, Implement, Review, Close).
   - The shortcut list is replaced by a pointer to `docs/prompts/index.md`.
   - Product, tool and change-kind names stay literal.

## Scope

**Problem statement:** one guard site has no test, and the shipped README still uses renameable shortcut phrases.

**In scope:**

- One new test in `.wavefoundry/framework/scripts/tests/test_indexer.py`.
- The `.wavefoundry/README.md` wording.
- One CHANGELOG bullet.

**Out of scope:**

- Any change to `indexer.py` or other product code.
- Rendering the README from the vocabulary profile.
- The root `README.md`, `AGENTS.md` and other repository docs.

**Platform behaviour:** test and documentation only. The same on Windows, macOS, Linux and WSL2.

## Acceptance Criteria

- [x] AC-1: Under the default profile, the new test passes. In a scratch copy, it fails when the re-guard after the unprovenanced-layer escalation is removed. The existing `test_graph_only_model_name_change_still_widens_and_keeps_the_guard` still fails when the model-set re-guard is removed. Oracle: scratch mutants.
- [x] AC-2: `.wavefoundry/README.md` contains none of the shipped lifecycle shortcut phrases that Requirement 3 names, and it still points readers to `docs/prompts/index.md`. Oracle: a grep for each phrase in Requirement 3, case-insensitive, so `Add changes` counts as `Add change`.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the escalation re-guard test with an embedder spy, and run the two mutants in a scratch copy.
- [x] Reword the README diagrams, the one-line flow and the shortcut list.
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| test       | implementer | —          | test_indexer.py only |
| readme     | implementer | —          | .wavefoundry/README.md only |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/README.md`

## Affected Architecture Docs

N/A. The change adds a test and rewords the framework README; no module boundary, flow or verification seam changes.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Closes the untested guard site. |
| AC-2 | required | The distribution-facing outcome. |
| AC-3 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned on operator request after closing 2136y, 2136z and 215sy. | Delivery reviews of 2136z (code, qa and red-team noted the surviving mutant). |
| 2026-10-19 | Readiness round 1: code-reviewer blocked Requirement 1 (on a completed store, `check_connection` refuses a populated layer with no recorded model before the escalation, so the fixture as written cannot reach the re-guard); red-team and qa-reviewer found the same. Repaired before readying: Requirement 1 names the state to reach and two verified fixtures; Requirement 3 says renameable and keeps fixed shortcuts; the AC-2 oracle drops `test_wf_cli`, which does not read the README. Probes by three reviewers: each re-guard mutant fails only its own test. | Readiness lane and seat reports. |
| 2026-10-19 | Implemented. Added `test_graph_only_unprovenanced_escalation_keeps_the_guard` (completed store, docs chunks and vectors deleted, `docs` kept in `content`, docs dropped from `model_versions`; code recorded full, int8 predicted). Scratch mutants: removing the re-guard after the `_unprovenanced` escalation fails only the new test; removing the model-set re-guard fails only `test_graph_only_model_name_change_still_widens_and_keeps_the_guard`. README diagrams, one-line flow and stage list now use stage names, with a pointer to `docs/prompts/index.md`; case-insensitive grep for each Requirement 3 phrase finds nothing. Gapfill: shell grep/sed used for helper lookup, README rewrite and mutant setup. | `run_tests.py --file test_indexer.py --file test_wf_cli.py`: 471 tests OK; mutant runs of `ExplicitPrecisionRebuildTests` 14 tests, 1 failure each. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Test the second re-guard site; leave the code as it is. | The behaviour is correct; only evidence is missing. | Merge the two re-guards into one check after the model-set block (a code change, more review surface); leave untested (the regression risk stays). |
| 2026-10-19 | Reword the README rather than render it from the profile. | Matches 2134x; no new rendering seam. | Render the README per profile (new mechanism); leave as is (distributions show wrong phrases). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A provenance-reset fixture trips another escalation path and the test passes for the wrong reason. | AC-1 requires the mutant to fail, and the test asserts the refusal text and that no embedder is built. |
| Rewording loses the README's meaning. | Stage names stay in the same order and position, with a pointer to the shortcut index. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
