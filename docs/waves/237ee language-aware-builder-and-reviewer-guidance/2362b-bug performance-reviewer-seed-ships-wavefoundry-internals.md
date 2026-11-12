# Performance reviewer seed ships Wavefoundry internals

Change ID: `2362b-bug performance-reviewer-seed-ships-wavefoundry-internals`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-11
Wave: 237ee language-aware-builder-and-reviewer-guidance

## Rationale

A Rust and Swift project on 1.42.0+q2u7 reports that its performance reviewer arrived with Wavefoundry's own review content and nothing for its stack. The tree confirms it: seed 212 says "You are running **performance-reviewer** on Wavefoundry" and its checks name `chunker.py`, `indexer.py`, `server.py`, `chunk_file` and `re.compile`. Every consumer receives that text. Seed 222 states the principle for its own body ("Never add product-specific content to this seed body"); seed 212 has no such statement and does not follow it.

## Product Intent

A consumer project's performance reviewer checks that project's own hot paths, in stack-neutral terms, and never reviews against Wavefoundry's modules. AC-1 and AC-2 together establish this for the shipped seed. Whether reviews in consumer projects improve is a field question the seed text alone cannot prove.

## Requirements

1. **No product-specific content.** The shipped seed 212 names no module, function, constant or cap that belongs to this repository, and does not name Wavefoundry as the project under review. The rule governs, not the list of names found today.
2. **Stack-neutral checks.** Keep the existing concerns in generic form: algorithmic complexity, repeated work per item or per request, patterns compiled or built inside loops, filter-before-cap ordering, bounded memory and no unbounded accumulation across calls. Add the costs that hold in any language: allocation per item or request, whole-buffer copies across thread or process boundaries, thread or runtime creation per operation, data reshaped twice, and lock hold times.
3. **Name the hot paths first.** Step 0 already asks which hot paths are in scope. Extend it: the reviewer names the project's hot paths from the briefing packet or the project's architecture docs before reviewing. When neither identifies any, the reviewer says so and returns to the coordinator instead of guessing.
4. **Evidence for speed claims.** A claim that something is faster or slower needs a measurement or a stated estimate method, not inspection alone. State this in the checks and reword the seed's "not measured numbers" exclusion so the two agree: the lane runs no benchmark suite of its own, and a speed claim still needs a measurement or a stated estimate method.
5. **Review-time language sections.** The renderer copies seed 212 word for word into a missing `docs/agents/performance-reviewer.md` (the review-protocol carrier registry and `_initial_review_carrier_text`), so the seed cannot rely on generation-time customization. Language-specific checks are sections the reviewer applies when the code under review is in that language, and a Project Harness Extensions section is left for the project to fill. This change ships that structure and no language section.
6. **Wavefoundry keeps its own checks locally.** This repository's project-local reviewer docs keep the index-build and query-path checks. `docs/prompts/agents/performance-reviewer.prompt.md` already holds them; confirm and keep them there.
7. **Upgrade delivery.** Seed 160 names only the optional `docs/prompts/agents/performance-reviewer.prompt.md` body for seed 212, with no instruction, and has no rule that refreshes an existing `docs/agents/performance-reviewer.md`. Add a separate seed 160 rule, leaving the existing changed-carrier sentence untouched, that names seed 212 and both destinations: when seed 212 changed, merge it into the existing role doc and the optional prompt body when present, replace inherited Wavefoundry-specific sections with the project's own hot paths and preserve project additions. Correct the seed 212 entry's list indentation. Update this repository's rendered upgrade prompt and add a changelog entry.

## Scope

**Problem statement:** The shipped performance-reviewer seed carries one project's internals to every project.

**In scope:**

- `.wavefoundry/framework/seeds/212-performance-reviewer.prompt.md`
- A seed 212 delivery rule in `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` and this repository's rendered `docs/prompts/upgrade-wavefoundry.prompt.md`
- This repository's project-local performance reviewer docs, only to confirm they keep the local checks
- Focused tests over the seed text and the renderer-created role doc, and the changelog

**Out of scope:**

- Language blocks (Rust is added by `2362c-enh design-over-diagnostic-guidance-and-rust-stack`)
- Seed 211 (Guru), which mentions `chunker.py` only inside an "e.g." illustration
- Review-lane selection, severity vocabulary and the verdict format
- Any renderer or lint change

## Acceptance Criteria

- [x] AC-1: A test over the shipped seed 212 fails on the current text and passes after the change: the seed contains no `<module>.py` file name of a framework script, none of the internal identifiers removed by this change (kept as a regression list), and no statement that the review runs on Wavefoundry. The test derives the module file names from the framework scripts directory; the tool-posture line naming Wavefoundry MCP tools is allowed. The same assertions hold for the role doc text the renderer creates for a missing `docs/agents/performance-reviewer.md` in a fresh temporary tree.
- [x] AC-2: The seed still states each generic concern in Requirement 2, requires the reviewer to name the project's hot paths or report that none could be identified, and requires a measurement or stated estimate method for speed claims. It no longer excludes measured numbers without that qualification, and its language-specific structure is worded as review-time conditions. The same test checks these.
- [x] AC-3: This repository's project-local performance reviewer prompt still contains the index-build and query-path checks after the change.
- [x] AC-4: Seed 160 instructs merging a changed seed 212 into an existing `docs/agents/performance-reviewer.md` and the optional prompt body, with the replace-inherited and preserve-additions rules; a test fails on the current seed 160 text. The changelog describes the change. The documents this change edits validate, and the change's own tests pass.

## Tasks

- [x] Open `seed_edit_allowed`; rewrite seed 212 per Requirements 1 to 5; close the gate.
- [x] Update the seed 160 entry and the changelog.
- [x] Add the seed-content test; confirm the local reviewer docs.
- [x] Run focused tests and docs validation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Seed and upgrade text | implementer | none | Seed gate open only for the edit |
| Verification | independent reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/seeds/212-performance-reviewer.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `.wavefoundry/framework/scripts/tests/`, `docs/prompts/upgrade-wavefoundry.prompt.md`

## Affected Architecture Docs

N/A. The change edits prompt text and adds one test; no module boundary, data flow or verification seam changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the reported defect and keeps it from returning |
| AC-2 | required | The generic reviewer must still review something |
| AC-3 | required | This repository must not lose its own checks |
| AC-4 | required | Without it an upgrading project keeps the old reviewer |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-11 | Planning only. Confirmed the seed text and that the project-local prompt already holds the Wavefoundry checks. Correction after readiness finding CODE-RDY-1: the renderer creates a missing performance-reviewer role doc by copying seed 212 word for word; executed `_initial_review_carrier_text` returned text equal to the seed. Existing role docs are merged by the upgrading agent. | `grep` of seed 212 lines 20 to 34; `docs/prompts/agents/performance-reviewer.prompt.md` lines 9 and 18; seed 160 line 547 |
| 2026-11-11 | Readback: ship project-grounded performance guidance in seed 212 and explicit existing-carrier upgrade reconciliation in seed 160; keep this repository’s local index/query checks. Before: a Rust consumer receives chunker.py/indexer.py checks. After: the reviewer names that project’s hot paths and assesses bounded work, costs and evidence. AC-1–4; seeds, upgrade carrier, tests and changelog only, no renderer or lint change. | Current amended plan and source readback |
| 2026-11-11 | Thought: apply the readied guidance through seeds and existing authored carriers, then verify actual missing-role delivery and negative controls. Observe: six seeds and local carriers updated; local performance-specific checks retained; no renderer, lint, template or runtime changes. Gapfill: targeted Python replacements performed bulk mechanical Markdown edits after MCP reads. | Scoped diff; baseline seeds in disposable work |
| 2026-11-11 | Observe: eight new guidance tests and the existing changed-carrier pin pass; eight tests also pass under the second profile with no skips. Actual missing-role renderer exercised. Original six seeds fail the changed contract checks; leaked-module and removed-lock-cost mutants are detected. Full docs validation passes; both edit gates closed. | `test_language_guidance.py`; `TechdocsCarrierLiteralPinTests.test_upgrade_carriers_pin_merge_safe_project_prompt_reconciliation`; disposable focused logs |
| 2026-11-11 | Final verification: canonical suite passes 12,822 tests across 249 files, 12 reported skips, 604.553 seconds (exit 0). Required delivery approvals are current; all readiness and delivery findings are terminal. No source or review input changed during the final run. Field effectiveness, native Windows and full release-profile qualification remain unverified. | Framework test receipt; typed ledger; `full-suite-final.log` in disposable work |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-11 | Readiness primer repair: deliver through seed 160's changed-carrier rule. | The primer showed, and the tree confirms, that seed 160 never refreshes an existing performance-reviewer role doc, so the reporter's upgrade would change nothing. | Rely on the generic "missing or stale" rule: leaves the refresh to each agent's judgment. |
| 2026-11-11 | CODE-RDY-1 repair: review-time language sections instead of a generation-time hook. | The renderer copies the seed word for word on a fresh install, so only text that is correct as copied works on both paths. | A fresh-tree render that strips blocks: new renderer mechanism for a prose change. |
| 2026-11-11 | Remove the internal content from the shipped seed and keep it in this repository's local docs. | Replay: the reporting project would receive generic checks plus a prompt to name its own hot paths. The seed only advises; the reviewer acts because Step 0 gates the review. It can miss projects with no documented hot paths, which Requirement 3 turns into an explicit report. Success is the reporter's upgrade check 3. | Gate the content behind "this is the Wavefoundry source repository": keeps dead text in every consumer's prompt. Leave as is and add blocks: the false identity line remains. |

## Risks

| Risk | Mitigation |
| --- | --- |
| This repository loses its own performance checks | AC-3; the local prompt already holds them |
| The generic text becomes too vague to act on | Requirement 3 forces named hot paths; Requirement 4 forces evidence |
| A consumer's local additions are overwritten at upgrade | Seed 160 states the preserve rule |
| Step 0 stalls reviews in projects with no documented hot paths | The reviewer reports the gap once and proceeds on the files in scope when the coordinator confirms |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
