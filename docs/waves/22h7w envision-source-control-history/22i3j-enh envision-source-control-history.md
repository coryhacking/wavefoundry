# Envision history and presentation

Change ID: `22i3j-enh envision-source-control-history`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-04
Wave: 22h7w envision-source-control-history

## Rationale

Teton reported that hashes and scratch-copy accounting added effort without helping strategic discussion. The useful safeguards were a stable target for concurrent reviewers, retained pre-repair text for comparison and an honest statement of later changes. Its formatter comparison was a probe, not an actual commit-hook run; this is one operator's feedback, not comparative efficacy evidence.

## Product Intent

Vision authors and operators can explore dynamic drafts and understand review coverage without mandatory fingerprints or per-edit bookkeeping. Preserve the substantive advisory-review boundary while using ordinary source control at meaningful checkpoints. AC-2 checks this bounded behavior; it does not establish universal adherence or time savings. This supports the adopted vision's useful, lightweight coordination direction without changing its destination.

## Requirements

1. Remove mandatory per-revision SHA-256, exact-byte accounting and formal early-draft revision sequences from canonical Envision core/review/delivery and their local mirrors. Readable labels remain optional aids. Keep compact review status about actual roles, pending findings and material unreviewed changes. Explain that identifying the review target prevents prior review from appearing to cover later substantive changes.
2. Keep each review target stable until its reviewers finish: leave its file unchanged or supply an existing commit/plain copy. Concurrent drafting stays outside the reviewed target and joins the single bounded repair. Retain pre-repair text through verification and delivery, using Git history/diff or a plain copy. If historical reviewed text was not preserved, disclose that and describe later changes without claiming provenance. Do not deliberately discard text needed for the current verification.
3. Prefer formatting before review. Inspect subsequent formatting via ordinary diff, word-diff or whitespace-ignoring diff while separately checking meaningful Markdown whitespace, links and structure. Confirmed formatting-only changes require neither a new revision identity nor automatic re-review. Consequential wording, link or structure changes need accurate affected coverage and remain subject to the existing repair stop.
4. Git commits are optional, project/operator-owned checkpoints, valid for provisional or unadopted visions. Do not commit automatically or require a commit per review. Reference a commit only for content actually present in it. Explicit project provenance requirements retain precedence, using source control where possible. Adoption and implementation authority remain separate.
5. Preserve staged reader reconstruction, role selection/independence, single-document default, single bounded repair/verification, and existing changed-seed179/companion reconciliation. Add no helper, gate, reviewer or workflow mechanism. Update the architecture description and changelog; leave actual visions and historical records unchanged.

6. Generated visions open with the title (new default `<Project>: Vision and Roadmap`), then the unified vision paragraph directly, without a label such as “Vision in one paragraph” or an owner/status/selection/review/adoption preamble. Use `Roadmap` as the next section, never `Roadmap at a glance`. Put routine document metadata and compact review/adoption status at the document end. Keep consequential provisional status and uncertainty beside the claims they qualify. Other headings are short, specific and descriptive, action-oriented where useful without forcing verbs; avoid empty labels, fluff and repeated opening sentences. Preserve genuine existing titles and explicit project formats/schemas. This governs generated vision content, not wholesale renaming of internal framework headings.

## Scope

In scope: seed179 and envision review/delivery companions; matching local prompts; data-and-control-flow architecture description; root changelog; focused contract checks only if existing expectations require adjustment; one generated-vision presentation case and its known-bad controls. Root will perform the separately authorized local package build after qualification.

Out of scope: source-control automation, freeze helpers, new commit policies, actual visions/Relay/research siblings, historical wave records, seed160/renderer/skill registry changes, public release, native-platform qualification. Preserve prior build metadata; the operator separately authorized a fresh local build after this extension.

## Acceptance Criteria

- [x] AC-1: Canonical/local core and affected companions consistently express Requirements 1–4 with no mandatory hashes, per-edit labels, status-only revisions or automatic commits; review/adoption/repair boundaries survive. The old guidance fails this contract check.
- [x] AC-2: One bounded synthetic review/repair/delivery walkthrough uses stable uncommitted text while new material is drafted separately, compares the repair against retained text and produces honest hash-free delivery. A formatting-only variant avoids redundant revision/review; a substantive-change variant exposes uncovered work. The evaluator rejects a known-bad claim that earlier approval covers newly added substantive material. Report omissions honestly; no additional batch without operator direction.
- [x] AC-3: Updated companions and core reach the same existing reconciliation sources; local mirrors match their canonical bodies and architecture/changelog agree. No actual vision is modified. This is delivery evidence, not a new downstream upgrade trial.

- [x] AC-4: One generated presentation case puts the unified paragraph directly after its title, Roadmap next, and routine metadata/review/adoption status at the end while preserving consequential uncertainty near claims. Its evaluator rejects known-bad process preambles, empty paragraph labels and “Roadmap at a glance”; heading clarity is judged by reader purpose, not mandatory verbs. Canonical/local guidance agrees, and existing title/format precedence survives.

## Tasks

- [x] Revise canonical/local guidance and the architecture/changelog account.
- [x] Run the bounded walkthrough and relevant contract checks; retain unique evidence.
- [x] Complete required validation and independent delivery review; update progress and handoff.

- [x] Extend generated-vision presentation guidance, run the one focused case and affected reviews, and update completion evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Authoring and integration | implementer coordinator | readiness | One writer for coupled guidance |
| Independent review | selected fresh reviewer roles | stable target | Read-only reviewers; coordinator records typed authority |

## Serialization Points

Freeze plan before readiness. Freeze material implementation inputs before final framework suite. Reviewers never edit their target or assume coverage transfers.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/179-envision-project.prompt.md`
- `.wavefoundry/framework/seeds/envision/review.prompt.md`
- `.wavefoundry/framework/seeds/envision/delivery.prompt.md`
- `docs/prompts/envision-project.prompt.md`
- `docs/prompts/agents/envision/review.prompt.md`
- `docs/prompts/agents/envision/delivery.prompt.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

Update docs/architecture/data-and-control-flow.md's Envision review-accounting paragraph. No runtime/module boundary changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the operator's demonstrated source of friction. |
| AC-2 | required | Exercises useful review continuity and rejects false coverage. |
| AC-3 | required | Keeps shipped and self-hosted instructions consistent. |
| AC-4 | required | Establishes a clear opening and usable headings without process preamble. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-04 | Complete: all4ACs/tasks met; affected QA/architecture/docs-contract approvals current, no findings. One presentation case and production metadata checks support the added contract. | Current12310tests/217files/12skips pass, source db197b038fb7ce7500d0d877a4f341784e3c473cba70077633cbaf5af9897022. Sourcegatesclosed; waveopen. Root continues authorized profile qualification/localbuild. |
| 2026-11-04 | Observe: presentation case and production metadata acceptance checks pass; current3canonical/local bodies agree. Sourcegates closed;8pathreviewmap refreshed, previoushistorymap retained. | presentation evidence retained in delivery-evidence.json; affecteddelivery review and newfullsuite pending. |
| 2026-11-04 | Readback: generated visions place title and unified paragraph before Roadmap; routine metadata/review/adoption moves to the end, with consequential uncertainty beside claims. Preserve genuine titles/explicit schemas, use clear headings without forced verbs, and leave actual visions unchanged. | R6/AC4; all affected readiness approvals refreshed on39e1a426dcf88657c187. One synthetic presentation case plus production metadata-validator controls. |
| 2026-11-04 | Operator amendment: add Requirement6, AC4 and presentation task to this open change. Prior history proof remains valid for its recorded scope; affected readiness refresh required before seed edits. | User selected direct opening paragraph, Roadmap heading, end metadata/status and concise useful headings, then requested a new local build. |
| 2026-11-04 | Complete: all3ACs/tasks met and QA/architecture/docs-contract delivery approvals recorded. Wave remains open; no closure/commit/build. | Final12310tests/217files/12skips pass, receipt ee24c17b13750cd91f2f8c856c51343083bf4b31fd261d1346946ba6a208f12e. First run failed only temporary baseline changelog scan; renamed backup unchanged,54CLIpass then fullrerun green. |
| 2026-11-04 | Observe: canonical/local parity, old-contract rejection and protected vision checks pass; one synthetic author case completed with original retained through delivery and no invented review coverage. | delivery-evidence.json; descriptive formatting scenarios only, no actual formatter/hook claim. Full suite and independent delivery review pending. |
| 2026-11-04 | Readback: replace mandatory fingerprints and status-only revisions with stable targets, retained comparison text and optional operator-owned Git. Core/companions, local mirrors and architecture/changelog only; actual visions and build metadata protected. | AC1–3; readiness approved on review-policy-d42658fed9b617e59041, all required lanes plus targeted red-team/docs-contract Council; no findings. |
| 2026-11-04 | Planning: user requested plan, review and implementation after Teton feedback. No source edits yet. | MCP current-file reads confirm mandatory hashes in both companions and core dated-label requirement. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-04 | Extend this open change with generated-vision presentation on explicit operator direction. | The unified purpose should lead immediately, with readable roadmap/headings and routine status at the end; claim-specific uncertainty remains visible. | Keeping a process preamble hides the product meaning; forcing action verbs adds a rigid style rule where a clear noun such as Roadmap works. |
| 2026-11-04 | Select readable coverage with stable targets and existing source control/plain copies. | Replays Teton's useful behavior while removing fingerprint ceremony. Guidance advises rather than enforces; the bounded case tests retention and coverage, not compliance at scale. A natural future run can reveal remaining friction. | Mandatory hashes retain the reported burden; automatic freezing adds unrequested automation and cannot prove review quality. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Simplification erases coverage honesty. | Stable target and pre-repair text remain through delivery; substantive changes stay explicit. |
| Whitespace-ignoring diff hides meaningful Markdown changes. | Require separate semantic whitespace/link/structure inspection; no automatic formatter exemption. |
| A Git reference is mistaken for adoption or review of working-tree edits. | Explicit content match and authority boundaries. |

## Session Handoff

See docs/agents/session-handoff.md for current session state. No closure or commit is authorized; root will perform the separately requested local build after qualification.
