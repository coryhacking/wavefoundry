# Let an operator select one reviewer for a small internal change

Change ID: `240t6-enh operator-selected-small-change-lane`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 241lp operator-selected-small-change-review

## Rationale

A two-line internal fix can spend more time waiting for review than the edit takes. The operator selected option A in decision spec 2136q. The benefit to verify is a shorter path to reviewed work while the operator retains control of what closes.

## Product Intent

An operator can prepare, implement and review a narrowly bounded internal fix with one independent code reviewer at readiness and delivery. The operator sees why a change qualifies, when the ordinary reviews take over, and what evidence still stands between the change and closure.

## Requirements

1. Accept an optional small-lane request on the existing `wf_add_change` admission, in dry-run and create modes. The operator must explicitly direct that selection for this admission. Record their direction, one sentence describing the intended diff, and the exact repository-relative paths in the wave's durable admission record. Admission retries must preserve the original selection and baseline. The tool follows the same trust model as operator-directed close. A model's inference, a mark in the spec, and the operator's general decision to ship this feature confer no authority to select it for a wave. Absence selects ordinary review, including on existing records.
2. Limit initial eligibility to one spec and at most three distinct declared regular-file paths across code, tests and fixtures. Resolve paths inside the repository. Count both rename endpoints, additions, deletions and relevant untracked files. Capture the baseline from the local Git checkout at admission, before product edits. Pin its commit identity and require a clean product scope, accounting for staged, unstaged and untracked work. At subsequent gates compare the complete current product tree with that pinned baseline, including changes committed since admission. Treat unexpected index/worktree differences, missing baseline objects, unresolved Git state and unsupported file types as specific reasons for ordinary review. Exempt only identified lifecycle-owned records and generated bookkeeping for this operation. A directory-wide exception for docs or framework files would hide real edits. Keep this baseline available through pause, resume and close, including after disposable work cleanup.
3. Exclude seed, hook, security, release and public-contract changes. Check the declared paths and the effect described in the spec, since an internal path can change an external contract. The independent reviewer assesses the described behavior and can require ordinary review when the impact is ambiguous. An additional requested specialist, uncovered risk, second spec or material expansion routes the wave to ordinary review. Give the operator the specific reason.
4. For an eligible selection, Prepare requires executed code-reviewer readiness approval. Review requires executed independent code-reviewer delivery approval. Retain the ordinary requirements for a spec, admission, current approvals, finding repairs, operator signoff, test receipt and explicit close. Show the selected lane, required signoffs and next action in the existing lifecycle responses. Never synthesize a council approval for a council that did not meet.
5. Bind the selection and its scope to the current policy receipt. Reassess the actual edits before delivery review and at close. Bind delivery approval to the reviewed file contents. Editing an approved file again requires fresh review even if its path stays eligible. When scope expands, return to the normal policy and identify missing or stale approvals. Retain review history. Apply the same decision through Prepare, activation, resume, Review, individual spec close and wave close.
6. Explain eligibility, selection, escalation and closure in the canonical seeds and lifecycle prompts that own those instructions. Reconcile the corresponding self-hosted guidance. Keep vocabulary, historical records and default behavior compatible with downstream distributions.

The code reviewer traces the proposed effect to its consumers and checks a prior-state compatibility case where applicable. Record a reviewer's escalation durably. A later revert, resume or retry cannot restore the narrow lane after escalation. A configured mandatory specialist also routes the wave to ordinary review. Once escalated, require fresh ordinary approvals under the ordinary receipt. The tool must recheck and bind the same file identities, modes and contents when recording a narrow delivery approval and when consuming it at either close route. An unstable or incomplete read yields ordinary review. Individual spec close retains its existing purpose. For a small selection it additionally requires current review clearance, including ordinary clearance after escalation. Wave close retains operator signoff, the applicable suite receipt and explicit authority to close.

## Scope

Deliver the lane through existing lifecycle tools and records. The first implementation covers single-spec waves. Separate work would be needed to attribute files to individual specs in a mixed wave. Preserve operator-owned close and the test receipt. This plan itself goes through ordinary review because it changes public lifecycle behavior.

## Acceptance Criteria

- [x] AC-1: A representative internal fix selected by the operator passes Prepare and Review with one independent code reviewer per phase. An equivalent unselected wave follows the ordinary rules, and past records retain their existing interpretation.
- [x] AC-2: Over-budget changes, protected surfaces, a public-contract change in an internal path, a second spec, a requested specialist and an unverifiable baseline each produce an actionable ordinary-review result. Exercise an internal helper whose modified return value changes a public response and verify that both close routes honor the reviewer's escalation.
- [x] AC-3: A change eligible at admission that later touches an undeclared file or changes its contract cannot use its earlier narrow approval to close. Review and both close routes name the missing ordinary approvals, including after resume. A later edit to the same allowed file requires approval of its revised contents.
- [x] AC-4: Missing delivery approval, an open blocking finding, missing operator signoff, and an invalid test receipt each independently prevent closure. Review history identifies the reviews that actually ran.
- [x] AC-5: An operator following the shipped guidance can select the lane, inspect its reasons, and complete or leave it through existing entry points. During qualification, compare three representative eligible internal cases with independent ordinary reviews of identical inputs. Record each side’s findings before revealing the other result. Include a historical compatibility control drawn from 210eb and check whether the existing-state issue is caught or escalated. Report unique material findings, reviewer effort, queue time and full-suite time separately, identifying unavailable observations. The qualification report distinguishes fixture results from later production experience. The comparison adds no recurring approval.

## Tasks

- [x] Trace admission, policy receipt, signoff and changed-file evidence through Prepare and both close routes. Identify the exact lifecycle-owned bookkeeping and exercise three versus four product paths, including staged, untracked, renamed, deleted and post-admission committed files.
- [x] Implement selection, eligibility, phase-specific approvals and escalation using the existing policy resolver.
- [x] Reconcile the canonical and self-hosted guidance and exercise normal, small and widened changes through the served tools.
- [x] Run the regression suite and record an eligible comparison and a protected or expanded control.

## Agent Execution Graph

The lifecycle builder owns selection and receipt handling. The docs builder follows the settled tool contract. Independent code, QA and lifecycle policy reviewers check the implementation of the lane itself.

## Serialization Points

- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/wf_server/`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/020-run-contract.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/190-close-wave.prompt.md`
- `.wavefoundry/framework/seeds/215-council-chair.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/`
- `docs/prompts/`

## Affected Architecture Docs

Update the lifecycle flow in `docs/architecture/data-and-control-flow.md`, the review policy in `docs/contributing/review-and-evals.md` and the served contract in `docs/specs/mcp-tool-surface.md`. Reconcile the stage gate in the root agent guide. Keep unrelated generated instructions and historical ledgers intact.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the new operator outcome and default behavior. |
| AC-2 | required | Limits eligibility. |
| AC-3 | required | Detects drift after readiness. |
| AC-4 | required | Preserves independent verification and close authority. |
| AC-5 | required | Checks usability and the proposed saving. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-21 | Planned after the operator selected the permanent lane. | Decision spec 2136q. |
| 2026-11-22 | Readback: the operator selects the lane at admission. One independent code reviewer verifies the plan and the delivered contents in their respective phases. Expanded scope or an uncertain public effect restores ordinary review. The operator still directs closure. | AC-1 through AC-5. This wave uses ordinary review. |
| 2026-11-22 | Eight registered lifecycle cases passed on both the default and renamed profiles. Removing the protected-path check wrongly admitted a public file. Ignoring the requested reviewer wrongly kept the narrow lane. | Both guard changes failed their intended assertions. The independent review comparison records findings and effort in [review-comparison.md](evidence/review-comparison.md). |
| 2026-11-22 | Delivery review found that restoring the working tree could discard a scope escalation and that replacing a file with identical bytes could reuse its approval. Both regression cases failed before repair and passed through the served Review and close previews after repair. | The two public lifecycle cases passed in 53.26 seconds. Review now retains the escalation for Prepare. Delivery approval also binds file identity across separate reads. |
| 2026-11-22 | The full framework suite passed with four workers and the original timing limits. | `run_tests.py` ran 13,221 tests across 255 files in 922 seconds with zero failures and 12 skips. The repository snapshot check passed. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-21 | Select the permanent lane explicitly and use existing review records. | A two-line internal filter is a plausible candidate. The public API change in dashboard wave 2423b would go through ordinary review. | Keeping the waiver leaves no standard operator path. Reducing readiness only retains the usual delivery roster. |
| 2026-11-21 | Propose one spec and up to three named files for initial qualification. | A mechanical bound and an actual diff make expansion observable. Test the value against elapsed readiness and any material finding missed in a comparable review. | Size alone misses public behavior changes. An unbounded description is difficult to enforce. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A small edit changes a public contract or depends on specialist knowledge. | Review the effect and protected paths, honor requested reviewers and restore ordinary review when evidence changes. |
| A shared or dirty checkout makes ownership unclear. | Use verifiable baseline and diff evidence. Explain why ordinary review is required when attribution fails. |
| The lane saves little time or misses useful findings. | Review the first eligible uses with actual timing and independent findings. Revisit eligibility if the benefit is small or a material defect escapes. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
