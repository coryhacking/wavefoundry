# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ui1d review-loop-friction`
Title: Review Loop Friction

## Objective

Remove three measured sources of review-loop friction that wave 1uhcb identified but deliberately deferred: completion and task-status tracking still supersede the review-policy receipt, the required-lane roster is scored against plan prose rather than explicit targets, and the guided review action omits the nested schema and current judgment a caller needs. When this wave closes, progress tracking costs no review cycle, reviewer rosters reflect explicit paths and requested semantic risks rather than what a plan discusses, and recording typed review evidence stops requiring schema archaeology.

## Changes

Change ID: `1ug66-enh checkbox-state-digest-split-and-mark-tool`
Change Status: `implemented`

Change ID: `1ug67-bug lane-selection-scores-plan-prose-not-scope`
Change Status: `implemented`

Change ID: `1ug68-enh guided-review-action-carries-its-schema`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: `code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `docs-contract-reviewer`, `release-reviewer`
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-08-05

## Wave Summary

Wave `1ui1d` (Review Loop Friction) delivered 3 changes: Marking a Task Done Should Not Cost a Review Cycle, but Deferring One Should, Documenting Evidence Recruits Reviewers, Because Lane Selection Scores Plan Prose, and The Legal Judgment Shape Is Discoverable Only by Reading the Deriver. Notable adjustments during implementation: Documenting Evidence Recruits Reviewers, Because Lane Selection Scores Plan Prose: Admitted into wave `1ui1d review-loop-friction` alongside both siblings on operator direction, and strengthened during a pre-Prepare discovery pass. Added: specimen 5 (change-ID kind tokens firing from the document's own header and from cross-referenced siblings); the self-demonstration table showing this document recruits all five lanes purely by describing the defect; and the BIDIRECTIONAL finding, which the original filing missed entirely — `1ug66-enh` modifies the digest function and adds an MCP tool yet recruits `code-reviewer` alone, escaping qa, docs-contract and architecture because it names no literal path. Requirement 2 is now two-directional, Requirement 3 covers the kind tokens, Requirement 5 pins before-rosters, AC-4a targets under-recruitment, and the separate-wave decision is superseded with its obligation carried forward as a named council item.; Documenting Evidence Recruits Reviewers, Because Lane Selection Scores Plan Prose: **Delivery review: three blocking findings, all repaired.** (1) `architecture-reviewer` was UNREACHABLE: its only token `docs/architecture` neither started with `.` nor ended with `/`, so `_path_token_matches` fell to the equality/suffix branch and a plan declaring `docs/architecture/current-state.md` selected NOTHING; the bare-token branch now also matches a directory prefix, and `docs/architecture.md` was added for the hub doc. (2) `_REPO_PATH_RE` hardcoded a four-prefix allowlist, so any target repo laid out as `lib/`, `pkg/`, `cmd/`, `app/` or `internal/` extracted zero paths and got zero automatic lanes with no diagnostic, violating the AGENTS.md Product Boundary; the pattern is now shape-based. (3) The AC-2 census, never run before this review, showed path-only scoring was RETROACTIVE: 775 change docs lost lanes, ZERO gained any, and five of six non-closed change docs collapsed to an EMPTY roster because every plan authored before this contract describes targets in prose. Repaired by failing OPEN: a document that declares no machine-readable target keeps its previous whole-document coverage via `LEGACY_WHOLE_DOCUMENT_TRIGGER_LANES`, labelled distinctly in the reason string, and omitting the two retired lanes so the request-only decision still holds. A fourth defect was introduced and caught during that repair: the generalized path pattern read English prose (`the runner/test corpus`, `stop dashboard/index activity`) as declared targets, which misclassified a plan as DECLARED and suppressed its own fallback; `_is_declared_target` now requires an extension or an explicit trailing separator.; Documenting Evidence Recruits Reviewers, Because Lane Selection Scores Plan Prose: Review replaced the unimplementable "declared scope prose" source with the smallest explicit contract: only repo-relative paths in the existing Serialization Points section are automatically scored, while non-path risks use the existing Requested review lanes field. The evaluator must move 3 to 4, and the census is bounded to upgrade-affected non-closed waves rather than creating a historical classification backlog. Adding paths corrected the live sibling rosters immediately, so the original under-recruitment is now a frozen pre-declaration fixture rather than a false claim about the amended files.

**Changes delivered:**

- **Marking a Task Done Should Not Cost a Review Cycle, but Deferring One Should** (`1ug66-enh checkbox-state-digest-split-and-mark-tool`) — 9 ACs completed. Key decisions: Split on the delivery contract: normalize AC `[x]` and every task marker; keep an AC `[~]` and its rationale digested; The tool enforces the `[~]` rationale only, not evidence for `[x]`
- **Documenting Evidence Recruits Reviewers, Because Lane Selection Scores Plan Prose** (`1ug67-bug lane-selection-scores-plan-prose-not-scope`) — 9 ACs completed. Key decisions: Score explicit Serialization Points paths rather than the whole corpus or Scope prose; ~~File separately from `1ug66-enh` and `1ug68-enh`~~ **SUPERSEDED — operator admitted all three into wave `1ui1d review-loop-friction`**
- **The Legal Judgment Shape Is Discoverable Only by Reading the Deriver** (`1ug68-enh guided-review-action-carries-its-schema`) — 7 ACs completed. Key decisions: Fix with a self-describing action, not a separate documented schema; Requirement 4 forbids relaxing any field
## Watchpoints

- **Blocking: `1ug67-bug` changes risk posture and must not be approved by a wave-level nod.** It is
  the only one of the three that alters what gets reviewed. Its AC-2 bounded bidirectional census is
  a NAMED council item: the delivery council must adjudicate every upgrade-affected non-closed-wave
  roster delta explicitly. Historical closed-wave output is aggregate diagnostic evidence, not a
  manual review backlog.
- **Blocking: `1ug67-bug`'s defect is bidirectional and the under-recruitment half was missed at
  filing.** Measured with the real selector: `1ug67-bug` alone recruits all five lanes purely by
  describing the defect, while the pre-declaration `1ug66-enh` and `1ug68-enh` fixtures each recruited
  `code-reviewer` alone, matched on `-enh ` in their own change IDs. Their amended live plans now
  carry explicit paths and return code, qa, and docs-contract review; Scope prose is never inferred.
  AC-4a is the gate.
- **Watchpoint: this wave's five-lane roster is explicit.** `1ug66-enh` and `1ug68-enh` now each
  select code, qa, and docs-contract review from their Serialization Points, while the wave-level
  Requested review lanes make the broader five-lane coverage intentional for this cross-cutting
  policy work. `wave.md` bytes are not digested, so recording this costs no receipt churn.
- **Watchpoint: `1ug68-enh` was filed on a premise that was REFUTED before admission, and the refuted
  text is retained on purpose.** The guided action and the finding-synthesis validator never
  disagreed; the original failure was a caller error (a softened judgment deriving `blocking=false`).
  Do not "fix" either side: `derive_blocking` and the `review_evidence.py:3376` retention rule are
  both correct and are explicitly out of scope. Its AC-1 is a paired positive-control-plus-red case
  because the originally-specified RED fixture is green on arrival.
- Watchpoint: `1ug66-enh` and `1ug67-bug` both touch `review_policy.py` / the digest path; only
  `1ug67-bug` moves `REVIEW_POLICY_EVALUATOR_VERSION`, from 3 to 4. It must update the upgrade
  migration so only a non-closed wave with a stale current receipt is asked to re-Prepare once, and
  the two changes must not both move the constant.
- **Blocking sequencing: the evaluator bump stales THIS wave's own receipt, and the readiness
  approvals recorded at Prepare will lapse when it lands.** `evaluator_version` is inside the hashed
  payload (`review_policy.py:434`), so the constant move changes `policy_input_digest` for these
  three change docs too. Measured on this wave's own bytes: `dd1fb564…` at evaluator 3 versus
  `13e15b5c…` at evaluator 4, identical input. A stale receipt gates guided signoff recording, so
  delivery approvals cannot be recorded until a re-Prepare. Wave 1uhcb hit the same thing on its
  2-to-3 bump and absorbed it as repeated readiness re-records. Do this instead: implement
  `1ug66-enh` and `1ug68-enh` first, land `1ug67-bug` with the constant move as its LAST step, then
  re-Prepare ONCE and re-affirm readiness under the fresh receipt before recording any delivery
  approval. This is disclosed behavior, not a defect; do not file it as one.
- **Blocking: `1ug67-bug` retires automatic `security-reviewer` and `performance-reviewer` selection,
  and its own coverage census cannot detect that.** Measured over `RISK_TRIGGER_LANES`: five lanes
  hold at least one path-shaped token; those two hold none, only semantic phrases. Path-only scoring
  therefore makes them permanently request-only. AC-2's old/new diff is structurally blind to it,
  because a lane that never fired historically shows a zero delta. Requirement 5 forces an explicit
  recorded decision among three alternatives and AC-4b pins whichever is chosen. **This is the one
  open design question in the wave and it is the operator's call**, since it trades automatic
  security-review coverage for author-declared coverage.
- **Watchpoint: this wave now requires SEVEN delivery lanes and a delivery council, and the last two
  arrived by the defect the wave is fixing.** Writing the `security-reviewer` /
  `performance-reviewer` finding into `1ug67-bug` named their semantic triggers, so the next Prepare
  recruited both: required lanes moved five to seven and `delivery_council_required` flipped false to
  true. Recorded as specimen 6 in `1ug67-bug` and deliberately NOT trimmed — gaming the evaluator by
  deleting load-bearing evidence is the wrong fix, and a security review of a lane-selection change
  is warranted on its merits. Plan delivery for seven lanes plus a council, not five.
- Watchpoint: AC Priority tables are populated at plan time in all three docs, per the ordering rule
  1uhcb shipped. Do not defer them to Prepare; that is the churn this wave's predecessor fixed.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-05: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: red-team enumerated RISK_TRIGGER_LANES and found that path-only scoring makes security-reviewer and performance-reviewer PERMANENTLY unreachable by automatic selection, since every trigger those two lanes carry is a semantic phrase and neither holds one path-shaped token, and that 1ug67-bug's own AC-2 census cannot detect the regression because a lane that never fired historically shows a zero old/new delta, folded as Requirement 5 with three alternatives plus AC-4b pinning the chosen branch and escalated to the operator as the wave's one open design question, and red-team further measured that the 3-to-4 evaluator bump stales this wave's OWN receipt, dd1fb564 at v3 versus 13e15b5c at v4 on identical bytes, lapsing the readiness approvals recorded at this very Prepare, folded into Requirement 4 with a Risk row and a blocking sequencing watchpoint; strongest-alternative: give security-reviewer and performance-reviewer path representation in RISK_TRIGGER_LANES instead of accepting request-only, preserving automatic coverage at the cost of enumerating security-relevant carriers, recorded as Requirement 5 alternative b rather than adopted because the choice is a risk-posture decision the operator owns; seat-evidence: docs-contract verified every load-bearing citation against the tree rather than plan prose, confirming all 20 Serialization Points paths resolve, review_policy_upgrade.py:81 policy_unchanged and :98 continue leave an evaluator-only bump marking nothing, wave_validators.py:294-365 bounds the tilde rule to required-priority ACs, and the live selector reproduces the recorded rosters, and it repaired two defects before the receipt was minted, 1ug68-enh's non-contiguous AC ids disagreeing with its priority table under a POSITIONAL fallback and 1ug66-enh's tautological close-gate sentence; disclosure: both seats were coordinator-run in-session rather than as independent subagents, so seat independence is by role and evidence rather than by separate context, and every finding is backed by an executed probe recorded in the change docs' Progress Logs)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| contract-never-reaches-target-repositories | do_now | no | completed | — |
| false-completion-claims-and-unpinned-boundaries | do_now | no | completed | — |
| path-scoring-silently-drops-lanes-and-layouts | do_now | no | completed | — |
| undeclared-plans-collapse-to-a-zero-lane-roster | do_now | no | completed | — |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
| performance-reviewer | pending | no current executed approval | record approval evidence for performance-reviewer |
| security-reviewer | pending | no current executed approval | record approval evidence for security-reviewer |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 101 | 1,642,123 |
| implement | 43 | 1,600,483 |
| review | 99 | 2,822,431 |
| **Total** | **243** | **6,065,037** |

<!-- wave:context-efficiency-state {"generation":198,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":43,"content_source_credit":1712528,"derived_artifact_credit":0,"direct_net":1600483,"estimated_tokens_saved":1600483,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":810,"response_debit":112666,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":101,"content_source_credit":1889183,"derived_artifact_credit":357,"direct_net":1642123,"estimated_tokens_saved":1642123,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13320,"response_debit":243609,"source_credit_count":76,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9512},"review":{"calls":99,"content_source_credit":3109037,"derived_artifact_credit":3492,"direct_net":2822431,"estimated_tokens_saved":2822431,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20823,"response_debit":270621,"source_credit_count":130,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":243,"content_source_credit":6710748,"derived_artifact_credit":3849,"direct_net":6065037,"estimated_tokens_saved":6065037,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":34953,"response_debit":626896,"source_credit_count":237,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12289},"wave_id":"1ui1d review-loop-friction"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 24 | 0 | 10 | 6,139,926 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":10,"estimated_exploration_avoided":6139926,"surfaced_events":24} -->
<!-- wave:exploration-avoided end -->
