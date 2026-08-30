# Guidance-Surface Drift Guards

Change ID: `1wgwn-enh guidance-surface-drift-guards`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-28
Wave: 1wip2 guidance-surface-drift-guards

## Rationale

Three drift classes bit the 1.20.0 release cycle, and each was caught by a human or
agent pass rather than a machine guard. (1) The seed-211 / `docs/agents/guru.md`
Index Scope byte-parity has NO shipped test: the 1wik9 delivery review (DOCS-DEL-1)
proved the previously cited oracle, `tests/test_shipped_reference_docs.py`, guards
only the install-log and scan-findings template pairs, so mirror drift is invisible
until a reviewer byte-diffs by hand. (2) The root `CHANGELOG.md` carries version
constants with no machine check: the 1.20.0 section shipped "`CHUNKER_VERSION` to
34" in the pm1l pack while the delivered tree was 37, the second recurrence of the
class first seen at 1.16.0; the docs-constants claim table covers
`performance-budget.md` and `RELIABILITY.md` but not the one release surface that
travels inside every pack. (3) Both 1.20.0 consumer upgrades found the target's
project-adapted `guru.md` still instructing retired API surfaces (a
`layer="framework"` parameter that has never existed publicly since the ADR 1p4xx
fold; `setup_wavefoundry.py` / `setup_index.py` command names superseded by
`wf setup` / `wf update-indexes`); the mechanical reconciliation scan reported zero
findings both times because its shared vocabulary
(`render_platform_surfaces._RETIRED_SURFACE_REPLACEMENTS`) covers retired bin
wrappers and file surfaces, not retired API tokens. Only the prompt-driven upgrade
editing pass caught the rot. All three guards are small, and every one was paid for
by executed field evidence this week.

## Requirements

1. A shipped test MUST assert byte-parity of the seed-211 Index Scope section
   against `docs/agents/guru.md`: the `## Index Scope` heading through the line
   before the next `## ` heading in each file, compared byte-for-byte
   (byte-identical at 5,672 bytes on 2026-08-28, reproduced independently by both
   council seats). Council correction (red-team finding 5): one seed/guru parity
   oracle ALREADY exists — `GuruCitationContractRenderTests` byte-compares the
   Citation Format block in `test_server_tools_lifecycle.py` — so the census
   records that oracle, the new test cross-references it, and the actionable
   premise is the narrower true one: the Index Scope region has no oracle. The
   test is mutation-proven: a one-byte divergence in a scratch copy of either
   twin fails it.
2. The docs-constants validation MUST gain a CHANGELOG version-constants check
   with council-repaired scoping (red-team finding 4): in the docs gate it runs
   ONLY when the top section heading is `## [Unreleased]` and is a no-op when the
   top section is dated (a released section is history the moment it is dated;
   checking it deadlocks the gate at the first post-release constant bump). The
   SAME claims check runs in `build_pack.py`'s changelog-first gate against the
   `## [<version>]` section being packed — the release-time coverage the pm1l
   pack actually escaped through. Claims are backtick-anchored constant names
   (`CHUNKER_VERSION`, `WALKER_VERSION`, `GRAPH_BUILDER_VERSION`) with a
   connector-plus-numeral pattern (the red-team prototype catches the shipped
   stale phrasing "to 34" while passing "moved to 13", "finishes this release at
   37", and historical quoted forms); expected values bind to the same constant
   sources the existing claim table uses (`chunker.py`, `indexer.py`,
   `graph_indexer.py`). Absence of a claim is never a failure; prose forms like
   "is unchanged" are outside the numeral pattern class and recorded as such.
3. The live `docs/agents/guru.md` drift found by the council MUST be repaired:
   the passages at its Enable/registration guidance (currently instructing
   `setup_wavefoundry.py` where seed-211's corresponding text says `wf setup`)
   converge to seed-211's current wording. Disposition recorded, not assumed:
   the architecture docs' `setup_index.py` runbook commands are LEGITIMATE
   implementation documentation (`wf` dispatches to those scripts; red-team
   finding 3) and are not edited. The mechanical retired-API token guard planned
   earlier is DROPPED per the council's executed falsification (inert extension
   mechanism, 53 false findings on healthy surfaces, half the tokens not
   retired); the guidance-posture drift class stays with the upgrade editing
   pass, which has caught it in the field twice.
4. Boundaries: no reconciliation-scan or vocabulary changes; no seed edits (the
   trimmed shape touches no seed); no renderer ownership changes to guru.md; no
   new lint severity classes; CHANGELOG historical and dated sections untouched
   by the docs-gate check; the recorded parity follow-up in
   `docs/agents/session-handoff.md` is closed when the test lands (archived
   1wik9 records untouched).

## Scope

**Problem statement:** two drift classes that shipped or nearly shipped this
release cycle have no machine guard (the guru Index Scope mirror; changelog
version constants at build and gate time), and the live guru.md carries a real
divergence from seed-211 that every pass this week missed.

**In scope:**

- `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py` (Index
  Scope parity test with cross-reference to the existing Citation-block oracle)
- `.wavefoundry/framework/scripts/wave_lint_lib/docs_constants_validators.py`
  and `.wavefoundry/framework/scripts/tests/test_docs_constants_lint.py`
  (Unreleased-scoped CHANGELOG check)
- `.wavefoundry/framework/scripts/build_pack.py` and
  `.wavefoundry/framework/scripts/tests/test_build_pack.py` (claims check in the
  changelog-first packaging gate)
- `docs/agents/guru.md` (convergence of the drifted passages to seed-211's
  current text; docs-only edit outside the parity region)
- `docs/agents/session-handoff.md` (close the parity follow-up bullet)
- `docs/architecture/testing-architecture.md` and
  `docs/contributing/build-and-verification.md` (changelog-first gate sentence
  gains the claims check)

**Out of scope:**

- the reconciliation scan, its vocabulary, and any retired-API token class
  (dropped by council falsification; recorded in the Decision Log)
- seed edits of any kind
- renderer ownership changes to `docs/agents/guru.md`
- checking CHANGELOG prose beyond the backtick-anchored numeral claim patterns
- editing architecture docs' legitimate `setup_index.py` implementation runbooks

## Acceptance Criteria

- [x] AC-1: The Index Scope parity test passes on the current tree, fails on a
  one-byte scratch mutation of either twin, and its census records the existing
  Citation-block oracle with a cross-reference in both directions.
- [x] AC-2: The CHANGELOG check passes on the current tree in BOTH homes; in the
  docs gate it is provably a no-op when the top section is dated (the
  post-release state is a test case); a seeded stale numeral under an
  `[Unreleased]` top section fails with a one-line-fix message; the packaging
  gate fails a scratch pack whose target section carries the seeded stale
  numeral (the pm1l escape reproduced and blocked); historical quoted phrasings
  never flag.
- [x] AC-3: `docs/agents/guru.md`'s drifted passages match seed-211's current
  corresponding text (verified by direct comparison recorded as evidence), the
  architecture-runbook non-edit disposition is recorded, and the session-handoff
  parity follow-up bullet is closed.
- [x] AC-4: Full suite and docs gate pass; the testing-architecture tier row and
  the build-and-verification changelog-first sentence are updated.

## Tasks

- [x] Execute and record the census: parity-region boundaries, the existing
  Citation-block oracle, current changelog claim phrasings in both homes, and
  the exact guru.md passages diverging from seed-211.
- [x] Implement the Index Scope parity test with the mutation proof and oracle
  cross-references.
- [x] Implement the Unreleased-scoped docs-gate check and the packaging-gate
  claims check with their positive, seeded-stale, dated-top-section, and
  historical-phrasing tests.
- [x] Converge the drifted guru.md passages; record the runbook non-edit
  disposition; close the session-handoff follow-up bullet.
- [x] Update carriers; run the canonical suite and docs gate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Census | qa-reviewer | none | Region boundaries, existing oracle, claim phrasings, divergence list; executed before any guard is written. |
| Parity test | implementer | Census | Mutation-proven before it counts. |
| CHANGELOG checks | implementer | Census | One claims engine, two homes (docs gate Unreleased-only; packaging gate on the packed section). |
| Guru convergence and carriers | docs-contract-reviewer | Census | Docs-only edits; follow-up closure rides here. |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/docs_constants_validators.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `docs/agents/guru.md`

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md`: tier row for the three guards.
- Others N/A: no boundary, flow, or ownership changes; three additive checks on
  existing surfaces.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The parity fact is load-bearing for every Guru session; it drifted from its cited oracle once already. |
| AC-2 | required | Second recurrence of the changelog-numeral class; the changelog ships inside every pack. |
| AC-3 | required | Two consumer upgrades proved the rot class is real and the current scan is blind to it. |
| AC-4 | required | Standing closure gates. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-28 | Planned from executed probes: no test in the tree compares seed-211 to `docs/agents/guru.md` (the shipped-reference module guards install-log and scan-findings pairs; the render-surfaces tests cover the `.claude/agents/guru.md` stub, a different file); the docs-constants claim table enumerates `performance-budget.md` and `RELIABILITY.md` docs only; the reconciliation scan's vocabulary is imported from `render_platform_surfaces._RETIRED_SURFACE_REPLACEMENTS` (retired bin wrappers and surfaces, no API tokens). Field evidence: DOCS-DEL-1 (wave 1wik9), the pm1l stale-numeral correction, and two consumer-upgrade editing-pass reports dated 2026-08-28. | Session probes 2026-08-28; wave 1wik9 events.jsonl DOCS-DEL-1 chain; field-feedback records. |
| 2026-08-28 | Prepare-council repairs applied before readiness, all falsified by execution. Red-team seat: the planned vocabulary extension site is INERT for API tokens (its consumers interpolate keys into bin-path shapes only, so the scan would search for .wavefoundry/bin/&lt;token&gt;; the module docstring documents the trap); injecting the tokens as content patterns produced 53 false findings on healthy live surfaces including the canonical negation sentences and the retirement ADR; setup_wavefoundry.py and setup_index.py are the LIVE implementation wf dispatches to, not retired surfaces; the changelog check's top-section scoping deadlocked the docs gate in the ordinary post-release state (dated top section plus the next cycle's first constant bump); and the plan's no-existing-parity-test premise was FALSE (GuruCitationContractRenderTests byte-guards the Citation block). Docs-contract seat: AC-3 was internally unsatisfiable as written; live rot found in guru.md's registration passages (setup_wavefoundry.py where seed-211 says wf setup); the follow-up closure step was missing; constant source modules unnamed. Repairs: the retired-token guard is DROPPED (class stays with the upgrade editing pass), the changelog check is Unreleased-scoped in the docs gate and added to the packaging changelog-first gate (the pm1l escape point), the parity premise corrected with the existing-oracle cross-reference, the guru convergence and follow-up closure added as Requirement 3, and the runbook non-edit disposition recorded. | Red-team and docs-contract council seat reports 2026-08-28 (proto_scan.py probe: 53 findings baseline 0; changelog prototype catches the shipped to-34 phrasing). |
| 2026-08-28 | Implemented. Census executed through the real machinery (`evidence/census_drift_guards.py`): parity regions byte-identical (5,672 bytes, matching sha, exactly one heading per twin), the Citation-block oracle confirmed present, the CHANGELOG top section DATED (the docs-gate no-op state live right now) with both top claims matching live constants and zero historical pattern matches (quoted forms immune by construction), guru divergence pinned at lines 746/748 vs seed 757/759. Delivered: GuruIndexScopeParityTests (byte-parity + heading-uniqueness pins; mutation-proven in a scratch tree — a one-byte divergence inside the region fails the test; cross-referenced with the existing Citation-block oracle in both docstrings); the shared claims engine check_changelog_section_constants in docs_constants_validators with check_changelog_unreleased_constants riding the existing check_docs_constants entry (Unreleased-only; dated top section provably a no-op even with a seeded stale claim), and build_pack._check_changelog_claims wired into BOTH packaging preflight paths (release and non-release) against the section being packed — the seeded pm1l phrasing (`CHUNKER_VERSION` to 34) is caught by the engine and refused by the gate with build_zip never called, per the new test_build_pack regressions. Guru.md registration passages converged to seed-211's current text (zero setup_wavefoundry.py mentions remain; the architecture runbooks' setup_index.py commands are legitimate implementation documentation and untouched, per the recorded disposition); the session-handoff parity follow-up bullet closed. Carriers: package-wavefoundry changelog-first sentence, testing-architecture tier row. 10 new regressions green (2 parity, 6 claims-engine, 2 packaging-gate); full suite 7,651 green; docs gate ok. | `evidence/census_drift_guards.json`; scratchpad parity_mutation run (mutation FAILS the test); suite_1wip2.log (exit 0). |
| 2026-08-28 | Record correction (implementation discovery): the changelog-first contract sentence lives in `docs/prompts/package-wavefoundry.prompt.md`, not `docs/contributing/build-and-verification.md` as the scope and AC-4 named; the packaging prompt carrier was updated and build-and-verification needed no edit (it carries no changelog-first sentence). AC-4's carrier list reads with that substitution. | grep census of the mechanically-enforced sentence across docs/. |
| 2026-08-28 | DOCS-DEL-1 repairs (cycle 1): the reverse cross-reference added to GuruCitationContractRenderTests' docstring in test_server_tools_lifecycle.py (a scope addition beyond the declared In-scope list, recorded here: a docstring-only edit satisfying AC-1's both-directions clause), and an EXECUTED release-preflight claims regression added (test_release_preflight_refuses_stale_version_constant_claim drives main() with --release and read-only-mocked git/gh preflights; the stale claim refuses with build_zip and the docs gate never called), so the Progress Log's BOTH-paths claim is now test-backed on both homes rather than executed-once-by-reviewer on the release side. Verifier boundary observations recorded without repair: the wrap-after-connector edge fires only on genuinely stale claims (safe direction), the acknowledged to/at over-match residual is loud and scoped, and a non-canonical Unreleased heading fails open (no-op), all per the Risks table. | test_build_pack.py release-home regression; test_server_tools_lifecycle.py docstring; independent delivery verification report 2026-08-28. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-28 | DROP the mechanical retired-API token guard; the guidance-posture drift class stays with the upgrade editing pass. | Council falsification by execution: the named extension site cannot express tokens, a content-pattern injection false-fires 53 times on healthy surfaces (including the negation sentences the parity guard locks in place and the retirement ADR), and half the token set is the live implementation rather than a retired surface. The editing pass has caught this class in the field twice and handles the judgment the tokens cannot. | Negation-aware exemption tuples were considered and rejected as a growing exemption ledger guarding a class that is not mechanically well-defined; excluding decision records from the scan was rejected as scope creep on shipped behavior. |
| 2026-08-28 | The CHANGELOG check runs Unreleased-only in the docs gate and additionally inside the packaging changelog-first gate against the section being packed. | The top section is the dated released section in the ordinary post-release state, so an unconditional top-section check deadlocks the first constant bump of the next cycle against untouchable history; the packaging gate is where the pm1l stale numeral actually escaped and is version-explicit. | Checking the dated top section with a grace mechanism was rejected (grace windows are drift); requiring an always-present Unreleased section was rejected (forces empty boilerplate into releases). |
| 2026-08-28 | CHANGELOG claims are optional-but-must-match; historical sections are never checked. | Historical sections legitimately carry old numerals (historical-reference preservation), and a release section that omits a constant is not wrong. | Checking all sections was rejected (false positives on every historical entry); required claims were rejected (boilerplate). |


## Risks


| Risk | Mitigation |
| --- | --- |
| CHANGELOG claim regexes over-match prose. | Patterns anchor on the backticked constant name plus a connector and numeral; the red-team prototype passed all current and historical phrasings; absent-claim behavior is a no-op; the census re-enumerates phrasings in both homes. |
| The packaging-gate check surprises release flows. | It extends the existing changelog-first hard gate build_pack already enforces (a missing section already refuses the build); a mismatching numeral is the same defect class with the same one-line fix message. |
| Parity test couples to heading text. | Boundaries extract by the `## Index Scope` heading in both files; renaming the section is itself a parity-relevant change the test should surface. |
| Two parity oracles in two modules drift apart. | Cross-references in both directions recorded by the census and in test docstrings; consolidating the oracle homes is deliberately out of scope. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
