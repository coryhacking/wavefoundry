# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vt2t techdocs-cost-ceiling-and-map-links`
Title: Techdocs Cost Ceiling And Map Links

## Objective

This repository's TechDocs audit reports one finding: a link on a published page points at a per-area `AGENTS.md` file the built site deliberately does not contain. When this wave closes the generated codebase map names every area-context target as a prose path instead of a hyperlink, the dogfood reports zero findings, and the eight primary carriers plus active source/test contract prose say what the map actually does. Now, because it is the last thing between this repository and a zero-finding publication audit.

## Changes


Change ID: `1vt2s-enh codebase-map-area-agents-prose-paths`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (renderer, tests, both generated outputs, eight primary carriers, active source/test contract prose)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-07

## Wave Summary

Wave `1vt2t` (Techdocs Cost Ceiling And Map Links) delivered one change: Emit per-area `AGENTS.md` references in the codebase map as prose paths, not hyperlinks. Notable adjustments during implementation: Emit per-area `AGENTS.md` references in the codebase map as prose paths, not hyperlinks: Architecture review found the declared graph-index paragraph still attributes map refresh to ordinary `indexer.py::build_index`, whose current source explicitly removed that hook. Requirement 5 and AC-5 now require the same paragraph to name current refresh ownership.

**Changes delivered:**

- **Emit per-area `AGENTS.md` references in the codebase map as prose paths, not hyperlinks** (`1vt2s-enh codebase-map-area-agents-prose-paths`) — 6 ACs completed. Key decisions: Delete `_area_context_link_href` and replace its three href-specific tests with rendered prose-path coverage.; Admit both generated files written by forced map regeneration and review their complete pending refresh.
## Watchpoints

- **Watchpoint (blocking): four seed edits need the gate.** Seeds `020-run-contract`,
  `030-inventory-and-map`, `040-docs-structure-bootstrap`, and
  `050-agent-entry-surface-bootstrap` carry stale link or regeneration claims and ship to every
  target repository. Open `seed_edit_allowed` before each edit and close it
  immediately after. Editing them ungated is a guard violation, not a slip.
- **Watchpoint: de-linking must not become dropping.** The orientation value is why the area-context
  line exists. `1vt2s` AC-2 blocks a change that removes the reference rather than the hyperlink.
- **Watchpoint: `_area_context_link_href` carries a Windows pin.** Wave `1p6d6` made it use
  `posixpath.relpath` because `ntpath.relpath` emits a backslash href that breaks the link and
  docs-lint on a Windows-generated map. Removing the helper retires the guard along with the hazard
  it guards, which is legitimate but must be a recorded decision, not a silent deletion. Three tests
  reference it.
- **Watchpoint (blocking): the claim census must search for MEANING, not one phrase.** Three
  successive drafts undercounted the carriers, finding two of eight, because each searched a single
  phrasing. One draft went further and recorded `docs/index.md` as "checked and NOT affected" from a
  search whose output was truncated before its match was visible, then wrote that exclusion into
  this record as an instruction not to act on it. **That instruction was wrong and is withdrawn.**
  `docs/index.md` is a declared target and carries three falsified assertions, including a "two
  findings" count this change takes to zero. Run the AC-3b census LAST and over the claim, not the
  wording.
- **Watchpoint: regenerating the map needs `index_build(content='map')`.** `generate_codebase_map`
  skips when `_fingerprint_inputs` matches, and that fingerprint does not cover the renderer, so a
  renderer-only change can leave the map stale while every command reports success. `wf
  codebase-map` exposes no `--force`. The forced path also refreshes the generated modules block in
  `docs/repo-index.md`; both generated outputs are declared review targets. Their pending graph
  topology refresh predates implementation and is admitted as the mechanical result of this one
  required public regeneration, so both complete generated diffs must be reviewed.
- **Follow-up, deferred not dropped:** `1vt2r` returns to `docs/plans/` withdrawn. Its premise
  (crossing-group count predicts matcher cost) is falsified in its own header, and any retry must
  begin with adversarial search over the pattern space rather than a hand-built case list.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-07: PASS** (moderator: wave-council;
  primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat:
  docs-contract-reviewer; strongest-challenge: forced public regeneration writes both generated
  files and can absorb a broad topology refresh unless the full write set and diff are admitted;
  strongest-alternative: boundary-aware conditional linking, rejected because both known
  publication-boundary cases require the same prose-path result; repairs: initial council findings
  in cycle 1, reachable audit expectation in cycle 2, regeneration ownership in cycle 3, and final
  chronology plus active-carrier census in cycle 4; cycle 5 names the complete missing-file
  resource write set. Every finding was recorded before repair and independently reverified by all
  blocking lanes.)
- **Delivery-phase Wave Council [delivery-council] — 2026-09-07: PASS** (moderator: wave-council;
  primer-depth: standard; fingerprint:
  `45e868fba226cde5aef3eaa119ff47fc50fbb537b6fbcd68926fe1ee62b86be9`; seats: red-team primer,
  architecture-reviewer, security-reviewer, qa-reviewer, and reality-checker; rotating fifth seat:
  docs-contract-reviewer. Seat agreement: unanimous; max severity: none; no challenge round. The
  primer's exact-owner concern was repaired and killed by six owner-removal mutants plus generated
  banner parity. Fresh final-fingerprint QA proves all ACs, 8,524 framework tests, clean docs
  validation, and TechDocs at 62 survivors, 4 nav entries, and 0 findings with only
  `audience_not_informative`. Ordinary-index exclusion is directly pinned; a dedicated ready-only
  negative test remains a future improvement because the branch was unchanged and the exact
  create-only guard plus lifecycle checks prove current behavior. The pre-existing verbose no-op
  `regenerated` message has no supported caller and does not affect an AC. Boundary-aware
  conditional linking was rejected because both known publication-boundary cases require prose and
  the alternative adds publication-policy coupling.)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1VT2T-001 | do_now | no | completed | architecture-reviewer |
| ARCH-PREP-1VT2T-001 | not_issue | no | not_required | — |
| ARCH-PREP-1VT2T-005 | not_issue | no | not_required | — |
| CODE-DELIVERY-1VT2T-001 | do_now | no | completed | code-reviewer |
| DOC-DEL-1VT2T-001 | do_now | no | completed | docs-contract-reviewer |
| DOCS-PREP-1VT2T-001 | not_issue | no | not_required | — |
| DOCS-PREP-1VT2T-002 | not_issue | no | not_required | — |
| DOCS-PREP-1VT2T-003 | not_issue | no | not_required | — |
| DOCS-PREP-1VT2T-004 | not_issue | no | not_required | — |
| QA-DEL-1VT2T-001 | do_now | no | completed | qa-reviewer |
| QA-PREP-1VT2T-001 | not_issue | no | not_required | — |
| RED-PREP-1VT2T-002 | not_issue | no | not_required | — |

*Machine review state — 12 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 8*
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

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 813 | 3,566,179 |
| implement | 74 | 890,374 |
| review | 833 | 21,275,322 |
| **Total** | **1,720** | **25,731,875** |

<!-- wave:context-efficiency-state {"generation":1009,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":74,"content_source_credit":1007620,"derived_artifact_credit":0,"direct_net":890374,"estimated_tokens_saved":890374,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2465,"response_debit":118850,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4069},"plan":{"calls":813,"content_source_credit":6246424,"derived_artifact_credit":3425,"direct_net":3566179,"estimated_tokens_saved":3566179,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":51868,"response_debit":2637498,"source_credit_count":548,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":833,"content_source_credit":23861137,"derived_artifact_credit":1269,"direct_net":21275322,"estimated_tokens_saved":21275322,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":49942,"response_debit":2539031,"source_credit_count":593,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1720,"content_source_credit":31115181,"derived_artifact_credit":4694,"direct_net":25731875,"estimated_tokens_saved":25731875,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":104275,"response_debit":5295379,"source_credit_count":1180,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11654},"wave_id":"1vt2t techdocs-cost-ceiling-and-map-links"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 29 | 0 | 12 | 19,263,545 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":12,"estimated_exploration_avoided":19263545,"surfaced_events":29} -->
<!-- wave:exploration-avoided end -->
