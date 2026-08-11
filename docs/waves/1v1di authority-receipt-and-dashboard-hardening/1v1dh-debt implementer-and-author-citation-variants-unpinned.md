# The Implementer And Author Citation Variants Have No Pins

Change ID: `1v1dh-debt implementer-and-author-citation-variants-unpinned`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-11
Wave: 1v1di authority-receipt-and-dashboard-hardening

## Rationale

`1v1c4` pinned the citation-rule family's review-phase carriers byte-exact (seed 237's authoring paragraph, the live prompt copy, seed 209's evidence variant) after that family drifted once already. Its census, plus the `1uzwi` delivery qa lane's supplement (recorded in `1v1c4`'s Progress Log, 2026-08-10), found the remaining two carriers unpinned, both verified against today's tree: seed `170-plan-feature.prompt.md` carries the `1urlb`-era change-document variant ("When a change document cites code, cite a **resolvable anchor**...", the expanded multi-paragraph wording, line 92 today), and seed `180-implement-feature.prompt.md` carries the implement-phase variant (the "Cite by symbol, so the citation survives the cycle" bullet, line 73 today). A repo-wide grep finds zero test references to either. A drifted copy of either seed ships to every target repository at its next upgrade with no gate noticing, which is precisely how the family's first drift happened.

## Requirements

1. **Both variants gain exact pins** in `CouncilSeedVerificationContractTests` (`test_docs_lint.py`), the family's established home, per the `1v1c4` mechanics: pin each variant's distinctive head sentence exactly plus its load-bearing carve-out clauses, red-first by mutating a scratch copy, observed as failures rather than skips.
2. **The family census closes.** With these two, every known carrier of the citation rule (seeds 170, 180, 209, 237; the live `council-review.prompt.md` copy; the `_prepare_council_instructions` runtime brief) has an exact or clause pin. The closing census table is recorded here, and any newly discovered carrier is pinned in the same change rather than deferred again.

## Scope

**Problem statement:** two of the six citation-rule carriers remain drift-unprotected after two waves of pinning work.

**In scope:** the two pin tests in `test_docs_lint.py`; the closing family census. Seeds are read, never edited: no `seed_edit_allowed` gate is needed.

**Out of scope:** rewording any variant; the renderer-region parity check (`1v1c5`, shipped); pins for text outside this family.

## Closing Family Census

Recorded 2026-08-11 per AC-3, backed by repo-wide sweeps on the family's distinctive phrases ("resolvable anchor", "Cite by symbol", "cites code"; index-excluded dirs and historical wave/plan records excluded). The sweeps surface exactly the six known carriers plus the two pin homes (`test_docs_lint.py`, `test_server_tools.py`); no new carrier was discovered.


| # | Carrier | Variant | Pin | Test |
| - | ------- | ------- | --- | ---- |
| 1 | `seeds/237-council-review.prompt.md` | Review-phase authoring paragraph | Byte-exact (`CITATION_PARAGRAPH_237`) | `test_1uu9y_citation_paragraph_pinned_in_seed_237_and_live_copy` (`test_docs_lint.py`, `1v1c4`) |
| 2 | `docs/prompts/council-review.prompt.md` | Live rendered copy of #1 | Byte-exact (same constant) | Same test (`1v1c4`) |
| 3 | `seeds/209-agent-harness-core.prompt.md` | Evidence-recording variant | Byte-exact | `test_1uu9y_citation_paragraph_pinned_in_seed_209` (`test_docs_lint.py`, `1v1c4`) |
| 4 | `server_impl.py` `_prepare_council_instructions` | Runtime council brief | Clause pin | `test_brief_carries_the_finding_authoring_citation_rule` (`test_server_tools.py`) |
| 5 | `seeds/170-plan-feature.prompt.md` | Change-document authoring variant (`1urlb` era) | Head sentence exact + resolvability clause + carve-out header and first case | `test_1urlb_citation_variant_pinned_in_seed_170` (this change) |
| 6 | `seeds/180-implement-feature.prompt.md` | Implement-phase variant | Bullet head exact + anchor vocabulary + name-the-case obligation + history-falsification clause | `test_1urlb_citation_variant_pinned_in_seed_180` (this change) |


The readiness council independently confirmed the `1usqm`-era seed 211 / guru surface no longer carries citation-rule text, so the family closes at six.

## Acceptance Criteria

- [x] AC-1: A drifted seed-170 change-document variant fails a named test, demonstrated red-first by mutating a scratch copy (failure, not skip).
- [x] AC-2: A drifted seed-180 implement-phase variant fails a named test, same protocol.
- [x] AC-3: The closing family census table (all six carriers with their pin or clause pin) is recorded in this document, backed by a repo-wide sweep on the family's distinctive phrases.
- [x] AC-4: The full framework suite and docs-lint pass.

## Tasks

- [x] Write both pins beside the `1v1c4` precedent; red-first on scratch mutations.
- [x] Run the family sweep; record the closing census.
- [x] Full suite; docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| pins | implementer | — | `1v1c4` mechanics, same test class |
| census | implementer | pins | AC-3 closing table |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`

## Affected Architecture Docs

`N/A` with rationale: drift protection for shipped seed text; no behavior or boundary changes.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The unprotected author-phase carrier. |
| AC-2 | required | The unprotected implement-phase carrier. |
| AC-3 | important | Close the family, not two more instances of it. |
| AC-4 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-11 | Planned from the `1v1c4` census discovery (seed 170, recorded there 2026-08-10) and the `1uzwi` delivery qa lane's supplement (seed 180, recorded in `1v1c4`'s Progress Log; the earlier attribution to the `1uzwh` lane was a wave-id swap, corrected at readiness). Premises executed before authoring: seed 170 line 92 and seed 180 line 73 carry the variants verbatim; a repo-wide grep finds zero test references to either | executed greps of seeds and tests, 2026-08-11 |
| 2026-08-11 | Readiness council: both variant locations and the zero-reference claim re-executed independently; the council also confirmed the `1usqm`-era sixth site (seed 211 / guru surface) no longer carries citation-rule text, so the six-carrier family census closes exactly as Requirement 2 states | seat reports, executed greps, 2026-08-11 |
| 2026-08-11 | Thought (coordinator, in-session): pin per the Decision Log's head-plus-load-bearing-clauses design. Seed 170: the exact head sentence, the resolvability sentence, and the carve-out table header plus its first case. Seed 180: the exact bullet head, the anchor-vocabulary sentence (noting its wording differs from 170's by one article, pinned as the seed actually reads), the name-the-case-inline obligation, and the history-falsification clause. Both pins UNCONDITIONAL per the qa lane (no existence-guarded skips; seeds ship everywhere). Red-first by scratch mutation of each seed | implementation start, 2026-08-11 |
| 2026-08-11 | Both pins written beside the `1v1c4` precedents in `CouncilSeedVerificationContractTests`. Red demonstrated on a scratch byte-copy of `.wavefoundry/framework`: seed 170 mutated to drop "resolvable" from the head sentence, seed 180 mutated to weaken the name-the-case obligation; both tests reported FAILED (failures=2), failures not skips. Green in the live tree: class runs 13 tests OK including both new pins | scratch-mutation run + live class run, 2026-08-11 |
| 2026-08-11 | Closing family census recorded (six carriers, each with its pin and test named); repo-wide sweeps on "resolvable anchor", "Cite by symbol", and "cites code" surfaced exactly the six carriers plus the two pin homes, no new carrier | Closing Family Census section; executed sweeps, 2026-08-11 |
| 2026-08-11 | AC gate evidence (coordinator, shared across the wave's three docs): full framework suite via `run_tests.py` reports 7129 tests across 62 files, OK, rc=0 captured unpiped; `wf_validate_docs` passed with zero warnings after the readiness seat-evidence rows were recorded. Independently re-executed by the delivery docs-contract seat: same 7129/62 OK rc=0 and "docs-lint: ok" | run_tests.py 2026-08-11 rc=0; wf_validate_docs 2026-08-11; docs-contract seat rerun 2026-08-11 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-11 | Pin head sentences exactly plus load-bearing clauses, rather than the full multi-paragraph seed-170 prose byte-exact | The 170 variant is expanded prose whose incidental wording legitimately evolves; the head sentence and carve-out vocabulary are the contract, matching how the runtime brief is clause-pinned | Full-paragraph byte pins (rejected: every editorial touch becomes a two-step change without adding drift protection where it matters) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Clause pins pass on a reworded-but-weakened rule | Each pin includes the exact head sentence, the anchor vocabulary list, and the name-the-case-inline obligation; the `1v1c4` precedent shows this catches one-character drifts |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
