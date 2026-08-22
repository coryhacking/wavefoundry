# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-08-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false

wave-id: `1vt2t techdocs-cost-ceiling-and-map-links`
Title: Techdocs Cost Ceiling And Map Links

## Objective

This repository's TechDocs audit reports two findings, both links on a published page pointing at per-area `AGENTS.md` files the built site deliberately does not contain. When this wave closes the generated codebase map names those targets as prose paths instead of hyperlinks, the dogfood reports zero findings, and the two prose surfaces that still claim the map "links" them say what it actually does. Now, because it is the last thing between this repository and a clean audit.

## Changes


Change ID: `1vt2s-enh codebase-map-area-agents-prose-paths`
Change Status: `planned`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (renderer, tests, regenerated map, both prose carriers)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

## Wave Summary

One enhancement, `1vt2s-enh`, confined to the codebase-map renderer plus the two prose surfaces that describe its output. It began as a two-change wave; `1vt2r-enh techdocs-crossing-group-cost-ceiling` was WITHDRAWN at readiness after a council falsified its central premise, and its withdrawal record carries the disqualifying measurement.

## Watchpoints

- **Watchpoint (blocking): three seed edits need the gate.** Seeds `020-run-contract`,
  `030-inventory-and-map` and `050-agent-entry-surface-bootstrap` all carry the stale claim and all
  ship to every target repository. Open `seed_edit_allowed` before each edit and close it
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
  codebase-map` exposes no `--force`.
- **Follow-up, deferred not dropped:** `1vt2r` returns to `docs/plans/` withdrawn. Its premise
  (crossing-group count predicts matcher cost) is falsified in its own header, and any retry must
  begin with adversarial search over the pattern space rather than a hand-built case list.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | pending | no current executed approval | record approval evidence for wave-council-readiness |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| docs-contract-reviewer | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 10 | 38,288 |
| **Total** | **10** | **38,288** |

<!-- wave:context-efficiency-state {"generation":8,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":10,"content_source_credit":37978,"derived_artifact_credit":2731,"direct_net":38288,"estimated_tokens_saved":38288,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":143,"response_debit":3594,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":10,"content_source_credit":37978,"derived_artifact_credit":2731,"direct_net":38288,"estimated_tokens_saved":38288,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":143,"response_debit":3594,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1316},"wave_id":"1vt2t techdocs-cost-ceiling-and-map-links"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
