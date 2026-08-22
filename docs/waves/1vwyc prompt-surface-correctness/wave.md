# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vwyc prompt-surface-correctness`
Title: Prompt Surface Correctness

## Objective

Repair the six seed citations that name role documents at paths which do not resolve, so a freshly
materialized prompt doc no longer carries a broken reference. Nothing else. Two prepare-council
rounds blocked every larger design attached to this defect, and the citation census is the only part
that survived both unchanged.

## Changes

Change ID: `1vwyb-bug seed-role-doc-paths-stale`
Change Status: `implemented`


## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (seeds 160, 237), qa (verification)
- Requested review lanes: none
- Required review lanes: docs-contract-reviewer

Completed At: 2026-08-21

## Wave Summary

Wave `1vwyc` (Prompt Surface Correctness) delivered one change: Six seed citations name role docs at paths that do not resolve. Notable adjustments during implementation: Six seed citations name role docs at paths that do not resolve: Scope cut to citations only after a second prepare-council BLOCK.

**Changes delivered:**

- **Six seed citations name role docs at paths that do not resolve** (`1vwyb-bug seed-role-doc-paths-stale`) — 5 ACs completed. Key decisions: Fix the seeds, not the rendered twins.; `product-owner` and `data-engineer` citations do not change.
## Watchpoints

- **Scope is citations only. Do not re-attach a recurrence guard here.** Three designs were blocked
  in one session: a tier model duplicating shipped `1vgep` machinery, a `_RETIRED_CONTENT_PATTERNS`
  tombstone whose table matches text rather than file existence, and a resolver that satisfied every
  acceptance criterion while being blind to all six defects. The guard is wanted and is deferred to
  its own design pass with the accommodation question settled first.
- **Six repoints, not eight.** Seed-160 lines 191 and 489 read "specialists/ (or flat)" deliberately.
  Repointing them blindly corrupts the text and silently retires a policy accommodation.
- **Seed gate required.** `wf_open_gate(gate="seed_edit_allowed")` before editing, closed
  immediately after.
- **Seeds 160 and 237 carry no marker fence at or near the edit sites.** Not a universal claim:
  seed-030 line 105 carries a real `wave:repo-index-modules` fence and is not touched here.
- **Do not modify anything under `docs/prompts/` or `docs/waves/`.** Both were sites of accidental
  damage earlier in this wave: a blanket prose substitution corrupted the generated finding-synthesis
  region in this record, and string-splicing edits left three duplicate Watchpoints sections that
  `docs-lint` passed because `WAVE_REQUIRED_SECTIONS` matches by substring containment.
- **BLOCKING history: do not revive `1vwye` or `1vvs3` or `1vwyd` without new evidence.** Each
  carries a withdrawal banner in `docs/plans/` recording exactly what falsified it. `1vwye` in
  particular read a deliberate legacy-protocol selector as an accidental skip; the code path that
  actually refused the field target's wave was never identified and must be found first.
- **Cross-repo measurement informed this wave and must not be trusted uninspected.** Several of the
  coordinator's own measurements were falsified by the councils. Re-derive before relying on any
  figure recorded here.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the wave ships a known defect class with no recurrence guard, so the next role-doc move reintroduces it, which is accepted deliberately on the Risks table after three separate guard designs were falsified on evidence in one session; strongest-alternative: fold the six repoints into the deferred guard's design pass so the accommodation question and the guard land together, rejected because it leaves six broken citations in shipped seeds for an unbounded interval to buy nothing, since the repoints are independent of the accommodation decision AC-3 forces to be explicit)

**Third round, both seats PASS.** Red-team confirmed all six repoint sites, both accommodation
sites, file existence for both repaired roles, the repair arithmetic (wave-council 4,
archetype-council 2), the `canonical_role_paths()` oracle by execution, and both halves of the
marker-fence claim. It swept AC-2 across all 32 `docs/agents/` citation lines in the two seeds and
found it satisfiable and non-vacuous: it would catch a repoint that over-corrects `qa-reviewer` or
`code-reviewer` into `specialists/`. It also found independent corroboration of the seed-vs-twin
drift: `docs/prompts/council-review.prompt.md:70` already carries the `specialists/` path while its
seed's line 71 is still flat.

Docs-contract verified record integrity **by exact parse rather than substring**, which is the check
that matters here: `WAVE_REQUIRED_SECTIONS` is `("## Wave Summary",)` tested with `section not in
text`, so a clean `docs-lint` proves nothing about structure. Every `## ` heading now appears exactly
once. It confirmed the Serialization Points parse to exactly the two seed paths, AC priority parity
at AC-1..AC-5, `Affected Architecture Docs: N/A` as defensible (zero citations of the flat role paths
anywhere in `docs/architecture/` or `docs/specs/`), and that AC-2 and AC-5 use `agent_surface_integrity`
read-only with no advisory-to-gating promotion smuggled back. It re-derived the corpus census
incidentally and reproduced it exactly.

**The AC-1/AC-3 contradiction found in round two is resolved:** the Rationale table parses to exactly
6 rows and neither 191 nor 489 is among them, so AC-1's scope no longer collides with AC-3's.

- **Prepare-phase Wave Council [prepare-council], 2026-08-21: BLOCK** (moderator: wave-council;
  primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat:
  docs-contract-reviewer; strongest-challenge: the single measurement that shaped this wave,
  "rendering would delete about half of five lifecycle prompts", was an artifact of comparing raw
  template files against rendered copies and is wrong by roughly a factor of two; strongest-alternative:
  land a drastically reduced `1vwyb` against already-shipped machinery, withdraw `1vwyd`, and re-plan
  the render change against re-measured figures)

Both seats independently returned BLOCK. Findings that survived coordinator re-verification against
the tree:

**Falsified measurements (all three were the coordinator's own).**

- A real render pass into a scratch tree produces documents at 0.68 to 1.00 of the current copies
  (review-wave 0.98, create-wave 0.93, prepare-wave 0.92, implement-wave 0.83, close-wave 0.68,
  memory-review 1.00), not the claimed ~0.5. The renderer INSERTS fenced regions in the same pass
  (`_upsert_review_policy_region` appends when markers are absent), so comparing a raw template file
  against a rendered copy double-counts them. This number narrowed `1vvs3` from 18 docs to 12, sized
  `1vwyd`, and anchored AC-9's threshold.
- Divergence is bidirectional. Templates carry 23 to 41 lines each that this repository's copies
  lack, including the automatic-lane-derivation contract seed-160 mandates and which `git log -S`
  shows this repo's `prepare-wave` has never held. `{{generated_at}}` is not a skeleton marker: wave
  `1viyu` added it on 2026-08-17 so materialized carriers pass `check_metadata`.
- The `run_tests.py` leak is in two of six documents (`close-wave`, `implement-wave`), not one.

**Duplicated shipped machinery.** `agent_surface_integrity.canonical_role_paths()` already derives
the two-tier role map from `REVIEW_POLICY_CARRIER_REGISTRY` (13 roles), and
`audit_agent_surfaces()` already reports duplicate roles with `canonical_path` and remediation,
wired into `wf_audit` and `upgrade_wavefoundry._run_agent_surface_integrity_scan`. Shipped test
`test_audit_follows_a_registry_destination_change` carries the comment "AC-2: no parallel
role-path list", which the rejected Requirement 3 would have violated. Delivered by wave `1vgep`,
2026-08-16. None of the three change docs mentioned it.

**Unsatisfiable or satisfiable-but-wrong ACs.** `1vwyd` AC-2 drops reworded and renderer-sourced
content and has an unconditional escape hatch; `1vwyd` AC-5 guards one direction only and passes on
a `close-wave` shipping without the seed-190 operator-consent gate; `1vwyb` AC-1 and AC-3 contradict;
`1vwyb` AC-7's predicate is not expressible in `_RETIRED_CONTENT_PATTERNS`, which matches text not
file existence; `1vvs3` AC-9's length guard cannot detect a same-length content swap; `1vvs3` AC-4's
arithmetic uses 27 when `docs/prompts/` holds 41 files.

**Disclosure gaps.** `docs/architecture/domain-map.md` states the ownership rule normatively and is
named by neither plan. `upgrade_merge_notes` has no writer and no reconcile path
(`_FRAMEWORK_OWNED_MANIFEST_KEYS` is `("generated_artifacts",)`), so installed targets keep the
false promise permanently.

**Confirmed correct and carried forward.** `1vwyb`'s citation census (20 distinct paths, 15 resolve,
5 do not; 8 occurrences at the stated lines) was independently re-derived by both seats and is exact.
The `memory-review` zero-diff control is genuine. The `upgrade_merge_notes` quotation is verbatim.
The 12-doc render set and the 6/3 classifications enumerate cleanly by name.

**Disposition:** `1vwyb` reduced and re-cut against the shipped audit; `1vwyd` withdrawn; `1vvs3`
removed from this wave pending re-measurement. No readiness approval recorded.

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
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
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
| plan | 24 | 0 |
| implement | 35 | 51 |
| review | 12 | 8,266 |
| **Total** | **71** | **8,317** |

<!-- wave:context-efficiency-state {"generation":71,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":35,"content_source_credit":18178,"derived_artifact_credit":535,"direct_net":51,"estimated_tokens_saved":51,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3836,"response_debit":16936,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2110},"plan":{"calls":24,"content_source_credit":12230,"derived_artifact_credit":2346,"direct_net":-1879,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3030,"response_debit":16931,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":12,"content_source_credit":23830,"derived_artifact_credit":516,"direct_net":8266,"estimated_tokens_saved":8266,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2479,"response_debit":14947,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":71,"content_source_credit":54238,"derived_artifact_credit":3397,"direct_net":6438,"estimated_tokens_saved":8317,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9345,"response_debit":48814,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6962},"wave_id":"1vwyc prompt-surface-correctness"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
