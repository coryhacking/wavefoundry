# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vqqi techdocs-audit-and-review-branch`
Title: Techdocs Audit And Review Branch

## Objective

Give the **Refresh TechDocs** workflow a mechanical publication audit and a genuinely read-only branch. `wf_techdocs_audit` (read tier, CLI `wf techdocs-audit`) computes what the workflow's rules imply but nobody computes: the `mkdocs.yml` publication boundary, `nav` target existence, relative links that dangle or escape the boundary, published-page metadata, the trio's marker-derived ownership, and the audience invariant on the two agent startup-order documents. The review-only branch of the workflow runs that audit and returns findings plus proposed edits, writing nothing on either host type. Citation resolution was planned here and removed at readiness after the prepare council falsified it; it is deferred to a redesign as an enforced lint validator.

## Changes

Change ID: `1vmt2-enh techdocs-audit-tool-and-review-only-branch`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-08-19

## Wave Summary

Wave `1vqqi` (Techdocs Audit And Review Branch) delivered one change: TechDocs Publication Audit and the Review-Only Branch of Refresh TechDocs. Notable adjustments during implementation: TechDocs Publication Audit and the Review-Only Branch of Refresh TechDocs: **Thought — delivery repair continuation:** fresh code review falsified three still-open repair claims without widening scope. DEL-8 accepted a valid doubled-single-quote multiline scalar as a complete first-line value; DEL-9 let `PYTHONWARNINGS=error` escape from the separator-classification compile; DEL-12 stripped significant leading whitespace from quoted patterns and reversed the publication boundary. Keep each defect on its existing cycle-1 chain and repair under the already-open repair cycle.; TechDocs Publication Audit and the Review-Only Branch of Refresh TechDocs: **Observe — delivery parser/regex repair:** single-quote scanning now treats doubled quotes as escapes and degrades multiline folding; significant-leading-whitespace quoted patterns are explicitly refused before normalization; both regex compiles use the same warning-to-refusal scope. Focused regression tests cover each exact counterexample and the full library/CLI/MCP matrix stays green under warnings-as-errors.; TechDocs Publication Audit and the Review-Only Branch of Refresh TechDocs: **Thought (historical, later narrowed):** the operator explicitly reversed the earlier decision to accept `RV4-F2` and `RV4-F4`. Ordered sequence before the first code edit: (1) add required AC-9/AC-10 and failing regressions; (2) make escaping `nav` symlinks a named degrade before external `is_file`/content read; (3) place raw `audit_techdocs` behind one isolated ten-second worker used by CLI and MCP; (4) align contracts; (5) rerun focused tests, dogfood, the full suite, and full docs validation. Prepare cycle 1 later added the no-parent-I/O expiry requirement and made realpath metadata lookup explicit.

**Changes delivered:**

- **TechDocs Publication Audit and the Review-Only Branch of Refresh TechDocs** (`1vmt2-enh techdocs-audit-tool-and-review-only-branch`) — 11 ACs completed. Key decisions: Citation resolution is removed from this change and deferred, to be redesigned as an enforced `wave_lint_lib` validator rather than a read-tier report.; The review-only branch calls the audit only, never the baseline tool.
## Watchpoints

- Watchpoint: the audit gates nothing. Findings live in `data.findings`, degrade reasons and the not-applicable verdict are `advisory=True` diagnostics, severity words are the literals `low`/`medium`/`high` (never `blocking`, which is this framework's derived review-evidence boolean, and never `critical`), and no lifecycle gate consults it.
- Watchpoint: a read-tier registration costs **four hard gates and three numeric pins**, measured by the prepare council in an isolated copy rather than assumed: roster parity, the `AGENTS.md` census, the roster count-and-digest pin, and `test_write_tier_permissions_delta_survives_bounding_with_counts`, which despite its name counts read plus write and so breaks on a read-tier add. Plus the sanctioned advisory-site set, and a hand re-render of `.claude/settings.json` (42 managed rules today, stale at 43).
- Watchpoint: the review-only branch must be read-only **by construction**, not by prompt. It calls the audit only; it never calls `wf_techdocs_baseline`, which has no dry-run flag on its CLI and would write the trio on a no-MCP host.
- Watchpoint: explicit degrades keep a wrong answer from looking clean. In particular, `nav_target_escapes_root` names an escaping logical nav entry and `survivor_target_escapes_root` names escaping survivor candidates after realpath metadata classification but before external `is_file`, open, or content read; refused survivor paths remain in link-boundary scoring. `audit_timeout` is the terminal, repository-I/O-free report when the ten-second worker deadline expires. The existing shape, draft and audience degrades remain unchanged.
- Watchpoint: the audience baseline is **HEAD content**. Three readiness lanes falsified the plan's earlier claim that "the last commit that touched the file" differs from `HEAD`: it is byte-identical for that path in every repository state. The check is informative only against an uncommitted authoring edit, and a byte-identical baseline reports `baseline_identical` with the `audience_not_informative` degrade rather than a pass.
- Watchpoint: citation checking is **out of scope**. Seed 178's manual Step 3 re-resolve clause is retained and its literal pins must keep biting; the audit is additive to it.
- Watchpoint: this wave's receipt sets `delivery_council_required: true`, so delivery gets the four lanes plus a full council pass.

## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-19: FAIL** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `TimeoutExpired` still called `_trio_state` in the parent, leaving repository I/O outside the claimed hard public bound, while realpath performed external `lstat` despite stronger no-stat/no-touch prose; strongest-alternative: make expiry construction constant-size and repository-I/O-free, then either build a component-wise zero-metadata resolver or narrow every carrier to AC-9's actual no-`is_file`/open/content-read boundary; findings: `PREP-TIMEOUT-001`, `PREP-CONTAINMENT-002`, both repair cycle 1)

- **Prepare-phase Wave Council [prepare-council] — 2026-08-19: PASS after repair cycle 1** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: prove that timeout expiry performs no parent-side repository I/O and that escaping nav symlinks never reach external `is_file`, open, or content-read operations despite realpath metadata classification; strongest-alternative: constant-size empty timeout sections plus the narrower AC-9 containment contract; evidence: fresh independent tripwires and known-bad mutants cleared both lanes for `PREP-TIMEOUT-001` and `PREP-CONTAINMENT-002`)

- **Prepare-phase Wave Council [prepare-council] — 2026-08-19: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `parse_mkdocs` kept a five-member block-scalar header allowlist with an APPROXIMATING fall-through, so both ends failed open: an indentation indicator such as `|2` missed the allowlist and became a one-element pattern list holding the header token, with `shape_ok` true and no degrade, publishing an unpublished tree a real `get_files` run hides; while `>` and `>-` were IN the allowlist and read line-per-pattern although YAML folds them, producing false findings against a tree `mkdocs build --strict` accepts; strongest-alternative: invert the parser's default from allow-and-approximate to recognize-or-degrade at the scalar header, which is smaller than enumerating more headers and is future-proof against the next shape, and which is the alternative taken)

Second readiness pass, run because delivery reverification amended Requirements 2, 3 and 9, the RV4-F2 Risks row and the Progress Log, which re-digested the review-policy receipt. Red-team **FAIL** (2 blocking), docs-contract **PASS WITH CONDITIONS** (5). All seven applied before this verdict.

- **Red-team blocking finding 1** is recorded above as the strongest challenge. Repaired by narrowing the recognized set to the literal headers this module models (`|`, `|-`, `|+`) and degrading on every other block-scalar header. Measured after: all seven unmodelled headers degrade, the three modelled ones agree with `mkdocs.structure.files.get_files` exactly. The finding is sharper than it looks, because PyYAML emits `|2` for precisely the leading-whitespace case the previous round had just added a degrade for, so that repair created the shape this one broke on.
- **Red-team blocking finding 2:** the `nav` check scored the RAW `mkdocs.yml` string while `_page_findings` scored an `os.path.relpath`-normalized one. `./index.md` therefore kept a leading `.` segment that MkDocs' default `.*` exclusion matched, emitting a false `techdocs_nav_target_excluded` at the tool's top severity rank against a tree `mkdocs build --strict` accepts; and a `./`-padded entry long enough to trip the new subject bound stat-ed True, passed the existence check, then had its real finding erased. One `os.path.normpath` after the lexical containment guard closes both directions; verified against the oracle on five shapes.
- **Docs-contract condition 1 caught the same reasoning error for the third time.** The rewritten RV4-F2 row claimed "worst admitted cost is therefore 15.8ms per call at the component cap", a figure read off a SINGLE-COMPONENT measurement. The seat measured 276ms; following it down gave **28.3 seconds**, because `excluded()` re-matches every pattern against each ancestor PREFIX and every prefix begins with the same expensive leading component, so cost is ancestors TIMES the per-component cost. Repaired with a 32-component cap, and the new figure was set by ADVERSARIAL SEARCH rather than extrapolation: 648ms worst admitted under all three caps, with the 28.3s shape refused in 0.028ms. This repository's deepest published page has 4 components, so the cap keeps 8x headroom.
- **Docs-contract conditions 2 to 5, applied:** one clean uncontended full suite recorded (the seat's failure and a second lane's were both concurrent-suite contention, each passing in isolation); the parse degrade count corrected from three to four, since `draft_docs_present` was named nowhere in the change document; the round-local `RV5-*` labels re-cited through their `DEL-*` ledger records with the citation convention stated, because only `DEL-*` ids resolve in `events.jsonl`; and the unbalanced parenthetical on the Requirement 3 line closed.
- **Not repaired, disclosed:** the refusal degrade reports the generic `mkdocs_shape` token and the envelope names no specific pattern, so an operator whose block carries an untranslatable pattern learns that the shape is off but not which line. Both seats rated this non-blocking and it is recorded as a follow-up rather than an envelope change late in review.

- **Prepare-phase Wave Council [prepare-council] — 2026-08-18: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the plan's headline citation requirement was falsified by the very history it cited, since its containment rule passes two of the four real stale citations exactly as the overlap rule it condemned does, its sub-range exception had a real historical instance that would have filed clean, and 11 of 52 locators in the measured corpus have no resolvable symbol at all; strongest-alternative: delete the citation resolver and replace it with an enforced `wave_lint_lib` validator running in the post-edit hook, `wf_validate_docs` and the close gate, adopted in part by the operator's decision to ship the publication half now and defer the citation question to its own change)

Both seats blocked the plan as written (red-team FAIL, docs-contract PASS-with-conditions) and both cleared it after amendment; max-severity high; every condition was applied to the change doc before readiness was recorded, and the largest removed a requirement rather than repairing it. Per-seat evidence:

- **Red-team** verified against the tree and produced the pass's most reusable artifact, an executed gate census: baseline suite 7349 tests across 63 files green in an isolated byte copy, then one bare read-tier registration added with nothing else changed, giving exactly three failures and one more after the roster and `AGENTS.md` entries. That establishes four hard gates and three numeric pins with a measured digest, and it falsified the plan's claim that the write-tier count pins were unaffected (observed `90 != 89`, because `allow_rules(include_write=True)` returns read plus write). It withdrew half of one of its own findings when the census contradicted it: `server.py` needs no edit for an impl-registered tool. Its remaining findings covered the vacuous `HEAD` audience baseline, the `exclude_docs_absent` hole left by `techdocs-cli generate` re-serialization, missing `docs_dir` containment for an MCP-exposed reader, and AC-2's agreement test being two stdlib approximations checked against each other.
- **Docs-contract** blocked on two: the review-only branch's no-MCP path would have written, because `techdocs_baseline.py` accepts only `--root` and `--json` and the `dry_run` keyword reaches the module solely from the MCP tool; and the pin ledger was wrong in the direction that makes an implementer skip work. It also found that Requirement 1 named `classify_techdocs_baseline` for per-member state, which is precisely the defect `1vj4e` DEL-2 repaired, five carrier omissions including `.claude/settings.json` and the `SKILL_REGISTRY` description, a severity vocabulary that collides with this framework's derived `blocking` boolean, missing precedence rules between overlapping codes, an exit-code taxonomy that inverts its sibling verb, and that the `Review memories` precedent has a shape the plan had not adopted.
- **One measurement corrected the previous wave's record.** `docs/references/codebase-map.md` carries two out-of-boundary hrefs, not the one three `1vj4e` delivery lanes recorded. Line 260 links `../../AGENTS.md`, which escapes `docs_dir`, and that is the exception they recorded; line 249 links `../design-system/AGENTS.md`, which resolves to a file that exists inside `docs_dir` but which `exclude_docs` removes from the built site. A link-resolution sweep passes the second; only a boundary-aware sweep catches it. Both counts are right for their own check, and the widening is this tool's demonstrated value.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | — |
| DEL-10 | do_now | no | completed | — |
| DEL-11 | do_now | no | completed | — |
| DEL-12 | do_now | no | completed | — |
| DEL-13 | do_now | no | completed | — |
| DEL-14 | do_now | no | completed | — |
| DEL-15 | do_now | no | completed | — |
| DEL-16 | do_now | no | completed | — |
| DEL-17 | do_now | no | completed | code-reviewer, docs-contract-reviewer, wave-council-delivery |
| DEL-2 | do_now | no | completed | — |
| DEL-3 | do_now | no | completed | — |
| DEL-4 | do_now | no | completed | — |
| DEL-5 | do_now | no | completed | — |
| DEL-6 | do_now | no | completed | — |
| DEL-7 | do_now | no | completed | — |
| DEL-8 | do_now | no | completed | — |
| DEL-9 | do_now | no | completed | — |
| PREP-CONTAINMENT-002 | do_now | no | completed | wave-council-readiness |
| PREP-HANDOFF-STATE-004 | do_now | no | completed | wave-council-readiness, wave-council-delivery, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer |
| PREP-SURVIVOR-CONTAINMENT-003 | do_now | no | completed | wave-council-readiness, wave-council-delivery, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer |
| PREP-SURVIVOR-DIR-LINK-005 | do_now | no | completed | wave-council-readiness, wave-council-delivery, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer |
| PREP-TIMEOUT-001 | do_now | no | completed | wave-council-readiness |
| PREP-UNSAFE-SURVIVOR-BOUND-006 | do_now | no | completed | wave-council-readiness, wave-council-delivery, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer |

*Machine review state — 23 findings; current: do_now 23, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 91 | 2,798,956 |
| implement | 165 | 3,477,775 |
| review | 963 | 27,609,226 |
| **Total** | **1,219** | **33,885,957** |

<!-- wave:context-efficiency-state {"generation":1203,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":165,"content_source_credit":3789429,"derived_artifact_credit":0,"direct_net":3477775,"estimated_tokens_saved":3477775,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5769,"response_debit":307919,"source_credit_count":97,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2034},"plan":{"calls":91,"content_source_credit":2939898,"derived_artifact_credit":3008,"direct_net":2798956,"estimated_tokens_saved":2798956,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9785,"response_debit":144241,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10076},"review":{"calls":963,"content_source_credit":31638811,"derived_artifact_credit":4508,"direct_net":27609226,"estimated_tokens_saved":27609226,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":188832,"response_debit":3846607,"source_credit_count":899,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1219,"content_source_credit":38368138,"derived_artifact_credit":7516,"direct_net":33885957,"estimated_tokens_saved":33885957,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":204386,"response_debit":4298767,"source_credit_count":1068,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13456},"wave_id":"1vqqi techdocs-audit-and-review-branch"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 91 | 0 | 17 | 81,964,107 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":17,"estimated_exploration_avoided":81964107,"surfaced_events":91} -->
<!-- wave:exploration-avoided end -->
