# Rename the Delegation Envelope Token to summary_schema_version Before 1.15.0 Ships

Change ID: `1u8o4-ref rename-summary-schema-to-schema-version`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-01
Wave: `1u8o5 rename-summary-schema-version-key`

## Rationale

Operator-directed (2026-08-01): the delegation envelope's version token is named `summary_schema`
while the repository's own convention everywhere else is `schema_version` (the review-policy
receipts, context-efficiency state blocks, index state store, and dashboard payloads all carry
`schema_version`).
`summary_schema: 1` reads as "the schema is 1" when the value versions the schema. The correct
name is `summary_schema_version`.

The deadline is structural: the key name is frozen contract surface that every fielded runner
looks up forever. Today the fielded delegation population is two operator-controlled test repos
(pg8h, pg9m); after the official 1.15.0 release it is every downstream repository, and the rename
would cost each of them a degraded transition run for a naming preference. Pre-release, the cost
is one benign, disclosed run on the test repos, and that run is itself valuable: it exercises the
unrecognized-token degradation path live, the one contract branch every reviewer tested
synthetically but nobody has observed in the field.

This is the sanctioned deliberate-evolution path of the contract (a tripwire, not a wall): the
surface changes together with its contract test in the same change, exactly as the 1u49j ADR and
the operator's tripwire-not-wall clarification prescribe.

## Requirements

1. **The key renames everywhere it is contract surface, in one change:** the constant pair
   (`SUMMARY_SCHEMA_KEY` value `"summary_schema"` becomes `"summary_schema_version"`; the constant
   NAMES may stay or follow, recorded either way), the producer's payload emission, the parent's
   recognizer lookup, and `_RECOGNIZED_SUMMARY_SCHEMAS` semantics unchanged (the VALUE stays 1;
   only the key renames, so this is a key rename, not a token bump).
2. **The permanent contract test updates in the same change** (the tripwire rule): the envelope
   pin asserts the new key as a RAW string literal (never constant-vs-constant); a companion
   assertion documents that the OLD key is absent from the emitted payload, so a half-rename
   (emitting both) cannot pass. QA-lane placement requirements: the old-key-absent assertion
   uses the raw literal `"summary_schema"` (post-rename the constant IS the new key, so the
   constant form would assert the wrong thing) and runs against the REAL spawned producer's
   payload in `test_real_child_envelope_and_old_schema_lock_tolerance`, not a stub and not the
   fallback summary (both vacuous).
3. **The old-runner transition is verified red-first as the designed degradation:** a test drives
   the CURRENT parent recognizer (looking up the old key) against a producer emitting only the new
   key and asserts the marked-degradation outcome via exact equality (fallback summary proven
   real, `summary_source_degraded` equal to `unrecognized_schema_token_None`, no schema key on
   the fallback). This pins that fielded pg8h/pg9m runners take exactly one benign marked run.
   Two guards: the existing `unrecognized_schema_token_999` test re-points to a NEW-key payload
   with unrecognized VALUE (marker stays `_999`); the cross-version `_None` test is a separate,
   additive test — collapsing the two is a forbidden contract-test weakening. The old-recognizer
   simulation (patching the constant back) is faithful only because the census proved every
   functional lookup routes through `SUMMARY_SCHEMA_KEY`; the test carries a comment saying so.
4. **Every doc surface that names the key updates** (council-verified census, 2026-08-01):
   `docs/specs/mcp-tool-surface.md:919` (provenance sentence, two occurrences),
   `docs/architecture/decisions/1u49j-adr ...md:36`, `docs/architecture/layering-rules.md:28`
   (Boundary Invariants row), seed-160 line 83 (names the key, so the `seed_edit_allowed` gate
   applies) AND its rendered mirror `docs/prompts/upgrade-wavefoundry.prompt.md:57` (regenerate
   after the gated seed edit; never hand-drift the mirror), CHANGELOG (only the Fixed bullet at
   :126 names the key; Upgrading item 8 does NOT and instead needs a prose addition
   distinguishing the two transition populations: pre-mechanism parents take one UNMARKED
   old-schema run as already described, while pg8h/pg9m mechanism-bearing parents take one
   MARKED `summary_source_degraded` run from the rename), and `docs/agents/session-handoff.md`
   standing verification hook (:235, :296) so the field-proof check names the new key. The
   1u5vl change-doc references and events.jsonl are historical records and stay untouched.
   Non-functional literals in `upgrade_wavefoundry.py` docstrings/argparse help (:3009, :3133,
   :3696) update in the same pass.
5. **The delegation and contract test clusters stay green**, plus the full suite. The
   `test_upgrade_wavefoundry.py` re-point surface is four classes (code-lane census):
   `DelegatedSummaryPg1aReproductionTests` (:5120), `DelegatedSummaryContractTests`
   (:5161/:5178/:5304), `DelegatedSummaryDegradationTests` (:5441), and
   `DelegatedSummarySchemaDivergentTests` (:5496) — re-point, never delete.
   `test_server_tools.py` `WaveUpgradeMcpToolTests` carries four functional raw-literal
   occurrences (:24796, :24818, :24829, :24839) that must re-point in the same change; note
   the :24829/:24839 pair does NOT self-enforce (the server never inspects the key, so a
   missed re-point stays green there) — the census edit is the only guard for those two.

## Scope

**Problem statement:** the frozen envelope key deviates from the repo-wide `schema_version`
naming convention, and the only cheap moment to fix it is before the contract's public release.

**In scope:** the key literal and its constants in `upgrade_wavefoundry.py`; the contract and
delegation tests (`test_upgrade_wavefoundry.py` and the `test_server_tools.py`
`WaveUpgradeMcpToolTests` literals); the spec, ADR, layering-rules row, CHANGELOG,
session-handoff hook, and seed-160 with the gate plus its rendered mirror regen.

**Out of scope:** the token VALUE and recognized-set semantics (unchanged); the degradation
mechanics (unchanged); historical wave records (1u5vl docs stay as written).

## Acceptance Criteria

- [x] AC-1: The emitted payload carries `summary_schema_version: 1` and does NOT carry the old
  key; the parent recognizes it; the contract test pins both facts.
- [x] AC-2: The old-key parent versus new-key producer cross-version case degrades with the
  marker exactly as designed (red-first against a simulated old recognizer), pinning the fielded
  runners' one-run transition.
- [x] AC-3: Every in-scope doc surface (the Requirement 4 census: spec, ADR, layering-rules row,
  CHANGELOG with the rename disclosure, session-handoff hook, seed-160 gated plus its rendered
  mirror) names only the new key; docs-lint passes.
- [x] AC-4: The delegation clusters and full framework suite pass; the contract-test re-points
  are re-points, not deletions.

## Tasks

- [x] Census every occurrence of the key literal and its constants (code, tests, docs)
- [x] Rename the key, constants, and recognizer lookup; update the contract test in the same edit
- [x] Add the both-keys-cannot-coexist assertion and the cross-version degradation test
- [x] Update spec, ADR, layering-rules row, CHANGELOG (+ rename disclosure), session-handoff
  hook; gated seed-160 edit, then apply the identical paragraph edit to the rendered mirror
  (no push-button prompt-mirror renderer exists; the paragraph is byte-identical between seed
  :83 and mirror :57, so drift is trivially checkable)
- [x] Delegation clusters (the four `test_upgrade_wavefoundry.py` classes in Requirement 5 plus
  `WaveUpgradeMcpToolTests`) + full suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          | Lands after wave 1u8o2 closes (single-OPEN slot) |


## Serialization Points

- `upgrade_wavefoundry.py`, `test_upgrade_wavefoundry.py`, and `test_server_tools.py`
  (the 1u5vl delegation surfaces; no concurrent work expected once 1u8o2 closes)

## Affected Architecture Docs

- `docs/architecture/decisions/1u49j-adr fresh-code-summary-producer-contract.md` (names the key).
  Required.
- `docs/architecture/layering-rules.md` (Boundary Invariants row at :28 names the key). Required.
- `docs/specs/mcp-tool-surface.md` (provenance sentence at :919). Required.
- CHANGELOG `## [1.15.0] - unreleased` (Fixed bullet :126 in-place key update; Upgrading item 8
  prose addition distinguishing the marked vs unmarked transition populations). Required.
- seed-160 (:83 names the key): update under `seed_edit_allowed`, then regenerate the rendered
  mirror `docs/prompts/upgrade-wavefoundry.prompt.md`. Required.
- `docs/agents/session-handoff.md` standing verification hook (:235, :296). Required.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The rename itself; a payload carrying the old key or both keys defeats the change and the contract test must forbid it |
| AC-2 | required | The only behavioral risk is the fielded runners' transition; pinning the marked degradation red-first proves the disclosed one-run cost is what actually happens |
| AC-3 | required | A doc surface still naming the old key after release becomes a permanent false reference on frozen contract text |
| AC-4 | required | The tripwire rule: contract-surface changes ship with their updated contract test and a green suite in the same change |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-01 | Filed on operator direction ("Let's do it before we ship 1.15.0") after the pg8h-to-pg9m field run proved the delegation live; the rename must precede the official release or be abandoned, since post-release it costs every downstream repo a degraded transition run. | Operator messages 2026-08-01; field run pg8h-to-pg9m (summary_schema: 1 observed) |
| 2026-08-01 | Readiness council ran (red-team + docs-contract-reviewer, both code-grounded): conditional PASS; census gaps and two false premises folded into Requirements 4-5, Scope, Serialization Points, and Affected Architecture Docs in-phase. | Council seat reports 2026-08-01; census 55 lines across 14 files, functional occurrences all via `SUMMARY_SCHEMA_KEY` except designed test-literal tripwires |
| 2026-08-01 | Implementation census re-run: case-insensitive grep found the key in exactly the 10 living files the plan names (upgrade_wavefoundry.py, the two test files, spec :919, ADR 1u49j :36, layering-rules :28, seed-160 :83 + mirror :57, CHANGELOG :126, session-handoff :235/:296); no surface outside the Requirement 4-5 census. | `grep -rniI summary_schema` 2026-08-01, 1u5vl historical files and 1u8o5 wave narrative excluded |
| 2026-08-01 | Red-first: all test re-points and the two additive tests (cross-version `_None` degradation, raw-literal old-key-absent on the real child) landed BEFORE the source rename; delegation clusters ran red as designed. | `python3 -m unittest` four delegation classes: 16 tests, 6 failures + 1 error, every failure the new-key pin against old-key code |
| 2026-08-01 | Source rename landed: `SUMMARY_SCHEMA_KEY` value now `"summary_schema_version"` (constant names unchanged); non-functional literals in the `_emit_delegated_summary` docstring, the `--emit-summary` producer docstring, and the argparse help updated in the same pass. Delegation clusters green. AC-1 and AC-2 met. | upgrade_wavefoundry.py :91/:3009/:3133/:3696; four delegation classes 16 tests OK; `WaveUpgradeMcpToolTests` 52 tests OK |
| 2026-08-01 | All Requirement 4 doc surfaces renamed: spec :919 (both occurrences), ADR 1u49j :36, layering-rules :28, seed-160 :83 under the open `seed_edit_allowed` gate with the mirror :57 paragraph kept byte-identical (diff-verified), CHANGELOG Fixed bullet in-place plus the Upgrading item 8 two-population disclosure (unmarked pre-mechanism run vs one marked pg8h/pg9m run with the false-report-stopping sentence), session-handoff hook :235/:296 re-pointed to the new key and the marked-then-unmarked expectation. docs-lint passes. AC-3 met. | Edits 2026-08-01; `diff` of seed :83 vs mirror :57 byte-identical; `wf docs-lint`: ok |
| 2026-08-01 | Full framework suite green and final case-insensitive census clean: remaining `summary_schema` matches are only the 1u8o5 wave narrative, constant NAMES in `upgrade_wavefoundry.py` (kept per Decision Log), and the designed test-literal tripwires (old-key-absent raw literal, old-recognizer simulation); no living doc or functional surface carries the bare old key. AC-4 met; all ACs and tasks complete; Change Status set to implemented. | `run_tests.py`: 6722 tests across 61 files, OK; census grep 2026-08-01 (1u5vl and events.jsonl excluded) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-01 | Rename to `summary_schema_version`, now | Matches the repo-wide `schema_version` convention (receipts, CE state, index state store, dashboard payloads); the pre-release window is the only cheap moment; the test-repo transition run doubles as the first live exercise of the unrecognized-token degradation branch | `summary_version` (rejected: ambiguous between content and shape); keep `summary_schema` (rejected by operator; viable only as the post-release fallback; the red-team steelman notes old parents degrade as `unrecognized_schema_token_None`, which AC-2 pins explicitly); emit both keys during a transition window (rejected: a half-rename the contract test must forbid, and unnecessary pre-release) |
| 2026-08-01 | Fold the readiness-council census into Requirement 4 verbatim | Both seats found the same enumeration gaps (layering-rules row, rendered seed mirror, `test_server_tools.py` literals, session-handoff hook, wrong CHANGELOG item-8 premise); the false memory-records example resolved as premise-only (no memory surface names the key, so nothing to update, just the Rationale citation fix); fixing the plan text in-phase repairs AC-3's reach before the receipt mints | Leave discovery to the implementation census (rejected: the plan would carry known-false claims through readiness) |
| 2026-08-01 | Constant NAMES stay (`SUMMARY_SCHEMA_KEY`, `SUMMARY_SCHEMA_VERSION`, `_RECOGNIZED_SUMMARY_SCHEMAS`); only the VALUE of `SUMMARY_SCHEMA_KEY` renames | The names already read correctly ("the key naming the summary schema"; "the version of the summary schema"), every functional lookup routes through them (which is also what makes the cross-version simulation faithful), and renaming them would churn the permanent contract test and the tripwire comment block for zero clarity gain | Rename to `SUMMARY_SCHEMA_VERSION_KEY` (rejected: reads as "the key of the version" and forces a same-change edit of every constant reference with no behavioral meaning) |
| 2026-08-01 | Fold the five prepare-lane conditions in before implementation | QA required three test-design pins (999-vs-None non-collapse, raw-literal old-key-absent placement, named delegation classes); code lane named the four-class re-point surface; docs-contract flagged the stale "if applicable" hedge and the no-push-button mirror regen nuance | Record approvals against the unamended text (rejected: the qa approval was explicitly conditional on these edits) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A missed occurrence leaves a split-brain key | Task 1's census plus AC-1's old-key-absent assertion; case-insensitive grep per the rename-gate rule |
| The test repos' next upgrade is misread as a delegation failure | The CHANGELOG rename sentence names the one expected marked run; the degradation is the disclosed designed behavior |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
