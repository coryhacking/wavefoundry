# Envision: company context without constraining ambition

Change ID: `222fi-enh envision-company-context`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-31
Wave: `224us envision-company-context`

## Rationale

The next Envision trial concerns a product belonging to an established company. The current core reuses project context and the research phase distinguishes capability from demand, but neither explicitly examines the owning organization's mission, portfolio or relationships. Source inspection of seed 179 and its research/review companions confirms this guidance gap; no failed company-backed field run is claimed. The operator requests incorporating this context before rebuilding the local install package. Existing company material can reveal useful opportunities and obligations, while public positioning can also become an unjustified ceiling on ambition.

## Product Intent

An operator envisioning a product within an organization receives a future and roadmap informed by relevant organizational strengths, beneficiaries and commitments, with current positioning distinguished from binding limits. Standalone projects retain proportionate briefing without invented company research. AC-2 tests these behaviors in bounded synthetic cases; AC-1 and AC-3 establish delivery of guidance, not general effectiveness. This supports the adopted Wavefoundry vision's executable intent and decision-support capability without accepting its still-open entry strategy or editing any vision.

## Requirements

1. When a product belongs to an existing organization, establish its role and relevant company context from known answers before recommending a destination. Do not require a new questionnaire or delay standalone work.
2. Research consequential mission, portfolio, customer/use-case evidence, positioning, channels/partnerships and operating obligations using authorized supplied/internal material and current official public sources where access is permitted. Keep investigation proportional; source/date consequential claims. Public marketing establishes published claims, not customer validation, internal strategy or binding commitments by itself.
3. Distinguish binding commitments from stated mission, current offerings/positioning and hypotheses. Consider how the product complements, extends, integrates with or replaces offerings, and consequential ownership/dependencies. Do not turn the current portfolio into a ceiling or silently adopt company-wide strategy. Retain operator decisions and fair alternatives-first exploration.
4. Extend existing product/domain and architecture remits conditionally to challenge company fit, beneficiary evidence, ambition anchoring and portfolio dependencies. Add no role, approval, research artifact or company-specific shipped example. Integrate consequential company evidence and remaining uncertainty into the existing argument and delivery accounting.
5. Preserve phase loading, one-document default, advisory reviews, adoption/authority boundaries and standalone proportionality. Mirror canonical changes in self-hosted prompts; update architecture explanation and the existing 1.39 changelog. Keep the skill, catalogs, seed 100/160, scripts and reconciliation mechanism unchanged.
6. Rebuild the operator's selected local 1.39 series with a new build identity after verification; retain the verified uv pin and existing dependencies. Do not upgrade target projects, commit, push, close the wave or publish an official release.

## Scope

**In scope:** seed 179, research/review companions (delivery companion only if necessary to avoid duplicating its accounting), corresponding local prompts, Envision paragraph in data-and-control-flow.md, changelog, build-stamped VERSION/prompt manifest, wave evidence and handoff. Coordinator owns writes. Reviewers and fixture author/judge are read-only on product files.

**Out of scope:** actual vision/research/review outputs; Teton, Aceiss or other target changes/research; source/runtime/renderer/upgrade changes; new skills or commands; package dependencies and model assets. Preserve earlier uncommitted packaging work and unrelated vision/relay edits.

## Acceptance Criteria

- [x] AC-1: Canonical and local guidance carry R1–R5 without drift; conditional company context does not relax authority, fair exploration or source-evidence distinctions. Record before/after core and total words with justification, targeting concise additions rather than a new checklist.
- [x] AC-2: One fresh author uses the revised guidance on two frozen short synthetic briefs: a company-backed product with a public-positioning constraint trap and a standalone project. An independent reader identifies a consequential company-informed choice, distinguishes evidenced commitments from marketing/hypotheses, finds no silent portfolio ceiling or company-wide authorization, and sees no invented company work for the standalone case. The reader must reject frozen known-bad excerpts that elevate marketing to mandate and impose irrelevant company research. Record all outputs and outcomes; no claim of superiority over the previous prompt or field validation.
- [x] AC-3: The new local package has a fresh 1.39 build identity, contains exact revised canonical guidance and matching changelog/manifest, and preserves explicit Envision family reconciliation declarations. Verify the existing family mapping still names the changed companions; no target upgrade is run. The change's authored/edited docs and scoped checks pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Freeze short briefs, reader questions and known-bad excerpts before prompt edits.
- [x] Implement conditional company context, mirror local prose and update architecture/changelog.
- [x] Run one bounded author/reader check and delivery contract checks; record evidence and word counts.
- [x] Obtain required delivery review, qualify and rebuild local package, verify artifact and hand off.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guidance and records | Coordinator | Readiness | Sole writing hand |
| Bounded behavior probe | Fresh author then independent reader | Frozen fixture and guidance | Two short outputs, one batch |
| Review and packaging | Required reviewers; coordinator builds | Implementation and evidence | No target writes |

## Serialization Points

Freeze fixtures before first seed edit. Finish material evidence and documentation edits before canonical tests/profile qualifications. No repository mutations during those executions. Readiness and delivery use actual independent contexts under the existing policy. Record final package checks after build stamping.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/179-envision-project.prompt.md`
- `.wavefoundry/framework/seeds/envision/research.prompt.md`
- `.wavefoundry/framework/seeds/envision/review.prompt.md`
- `.wavefoundry/framework/seeds/envision/delivery.prompt.md`
- `docs/prompts/envision-project.prompt.md`
- `docs/prompts/agents/envision/`
- `docs/architecture/data-and-control-flow.md`
- `.wavefoundry/framework/VERSION`
- `docs/prompts/prompt-surface-manifest.json`

Root CHANGELOG.md is also in scope. Protected sources include seed 100/160 and all scripts/registry/catalogs.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` Envision section for conditional company grounding. No runtime/module boundary changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Shipped guidance must preserve contracts |
| AC-2 | required | Exercise intended reasoning and proportionality beyond text matching |
| AC-3 | required | Operator needs a usable current local package |

## Evaluation Budget

One author context produces two brief strategic excerpts, not full visions or advisory-review ensembles. One independent reader assesses them and rejects the two fixed controls. Freeze inputs before source edits. If a required behavior remains unproven at batch end, report evidence/options to the operator; do not automatically repeat. Required implementation-wave reviews remain separate. Retain unique fixture/output/judgment evidence in one compact evidence file; routine review working notes stay in disposable work. This probe establishes behavior observed in supplied fictional material only, not research quality, company adoption or universal agent adherence.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-31 | Planned from operator request; no company trial failure alleged. Existing local build and unrelated vision changes preserved. | Current core/research/review source inspected; package 1.39.0+q0c1 is prior baseline |
| 2026-10-31 | Frozen one-batch fixture and before-edit word counts; no source edits. | `.wavefoundry/work/224us/fixture.json` SHA-256 `ecd1897d0ba405ba6271844c4272c4a0ab8f86e3128577337cb109a403f63a3c`; baseline core 1,613 / family 3,335 words |
| 2026-10-31 | Readiness test handling: author sees only instruction and briefs in a fresh context; reader persists reconstruction before seeing anchors/controls. The two cases share one author context, so they are not independent samples. | `.wavefoundry/work/224us/author-packet.json`; one predeclared batch |
| 2026-10-31 | Readback / Thought: add a conditional company-role cue to core and evidence distinctions in research, existing review remits and delivery. Before: general project context could leave portfolio assumptions implicit. After: relevant company evidence informs choices without treating marketing as mandate. AC-1/2/3; no actual vision, target, runtime or upgrade edits. | Ready receipt `review-policy-aa2c629f8e89ae93aea6`; source ownership verified |
| 2026-10-31 | Gapfill: local shell reads used for docs-only orientation and mechanical text parity; MCP source reads verified phase/delivery and family-reconciliation contracts. No runtime investigation required. | code_read of seed160 and delivery phase, architecture Envision section |
| 2026-10-31 | Observe: AC-1 parity and full docs validation pass. Core 1,613→1,656 words (+43); whole family 3,335→3,575 (+240). Growth adds conditional company discovery, source distinctions, portfolio implications and existing-role checks; no new workflow or checklist. Thought: run the frozen short probe to check choices and standalone proportionality. | `.wavefoundry/work/224us/contract-check.json`; author receives filtered packet only |
| 2026-10-31 | Observe: AC-2 passed one batch; independent reader reconstructed choices before anchors and rejected both bad controls. Company support evidence changed the destination/first experiment; standalone path imposed no company work. Limits include one shared author, one reader, conspicuous controls and synthetic excerpts only. Thought: freeze material records for canonical suite and packaging profiles. | `evaluation-evidence.json` retains exact fixture, outputs, staged packets and verdict |
| 2026-10-31 | Observe: canonical framework suite passed 12,291 tests / 214 files / 12 skips in 551.007s; current green receipt. Thought: request fresh QA, architecture and docs delivery checks, then qualify compatibility profiles and review built artifact with release lane. | inputs hash `90d82718a8e226b423b877dee31bbb337551946af7d218daafd123ce45465575`; `.wavefoundry/cache/qualification/224us-default.json` |
| 2026-10-31 | Observe: fresh architecture and docs-contract delivery approved without findings; QA verifies AC-1/2 and holds final approval for AC-3 package. Thought: qualify second and declared profiles sequentially against the same current default source, then build and independently inspect the archive. No source repair or second behavioral batch. | Retained prepackage reviews in `evaluation-evidence.json`; typed approvals in ledger |
| 2026-10-31 | Observe: both compatibility profiles and exact skip comparisons passed; local build 1.39.0+q0f4 verified all 259 source files, nested payload hashes, manifest, changelog and all Envision sources. Thought: finish QA and release artifact review; keep wave open and changes uncommitted. | `packaging-evidence.json`; archive SHA-256 `b03d2a915c80e0f414e3b081db37cc8bfd96c87d3581c5f46086c499eaad6a16` |
| 2026-10-31 | Delivery complete: all3ACs/tasks supported, QA/architecture/docs-contract/release approved independently with no findings. Bounded intent observed in synthetic excerpts; field efficacy remains unproven. Local q0f4 package ready for tests. Wave remains open; no commit/push/public release/target upgrade. | `evaluation-evidence.json`, `packaging-evidence.json`, typed delivery approvals |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-31 | Conditional core cue plus phase-specific research/review detail | Teaches reusable behavior at the relevant step without loading a company checklist for everyone | Briefing-only leaves reuse manual; mandatory company phase burdens standalone projects and overweights current marketing |
| 2026-10-31 | Small synthetic probe, no paired superiority trial | This is an explicit grounding addition, not a claim that prior instructions fail or that new visions are better | Full vision ensemble would measure much unrelated behavior; static review alone cannot observe intended reasoning |

## Risks

| Risk | Mitigation |
| --- | --- |
| Marketing mistaken for commitments or demand | Explicit source distinctions and negative control |
| Current company scope caps ambition | Separate current choices from commitments; require operator decision for changed responsibilities |
| Prompt growth and ceremony | Small core cue; phase-specific detail, no new role/file/questionnaire |
| Shared worktree/build interference | Preserve unrelated edits and freeze material inputs during qualification |

## Session Handoff

See `docs/agents/session-handoff.md`; implementation and package requested, no closure or commit authority.
