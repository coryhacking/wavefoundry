# Arc records with downstream naming

Change ID: `22euo-enh arc-records-and-downstream-naming`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-03
Wave: 22bs0 initiative-continuity

## Rationale

Give a substantial outcome a durable, concise home across waves. The operator selected Arc as the working name and requested the existing lifecycle filename convention, while allowing downstream distributions to use Epic. The implemented first change in wave `22bs0` provides response-only Plan initiative guidance; this second change adds the requested record and naming contract while preserving the earlier evidence for its tested scope.

## Product Intent

Teams and successor agents can recover an outcome, its remaining obligations and the next useful wave from one short arc document. This advances the multi-wave continuity direction in the adopted [vision](../../../VISION.md), including building, improving, replacing and taking over software. Ordinary changes remain free to proceed directly to a wave.

## Requirements

1. Use the conceptual hierarchy **Vision → Horizon → Arc → Wave → Change**. An arc describes a bounded outcome that may span several waves. Horizons remain in the vision; changes remain inside waves. Do not require a feature/story tier or a vision link when none genuinely fits.
2. Default record layout: `docs/arcs/<lifecycle-id> <arc-slug>/<lifecycle-id>-arc <arc-slug>.md`. The same ID and slug appear in the folder and filename. Use the existing lifecycle ID policy and collision checks, extended to recognize arc records; do not create a separate counter or treat an arc as a change admitted to a wave.
3. Plan arc creates or revises one concise record containing the outcome and beneficiary, success evidence, boundaries, significant dependencies and decisions, linked waves, current progress and next useful advance. Preserve operator edits. Recover progress from authoritative wave/change records; closing a wave alone does not establish the arc's outcome. Additional files are optional supporting material, created only when useful.
4. Keep wave records at their configured wave root. Arc records link to them; do not move or duplicate waves, tickets, acceptance checklists or evidence. Arc progress is a narrative summary with links, not another lifecycle ledger. No arc admission, readiness or closure gate is added.
5. Make the vocabulary and record root distribution-owned through the existing fork/profile mechanisms. A documented Epic example produces `docs/epics/<id> <slug>/<id>-epic <slug>.md`, the label Epic, command Plan epic, backing prompt `plan-epic.prompt.md` and skill `wf-plan-epic`. Default equivalents use Arc and `plan-arc`. Derive active names consistently and reject unsafe paths and name collisions using existing conventions. Specify the exact profile keys during implementation; no new configuration service is required.
6. Preserve IDs and content across naming changes. Changing a distribution's vocabulary must not silently move existing records or break references. Document explicit migration of paths and links when requested. Reconcile existing Plan initiative surfaces and project customizations without leaving two competing canonical workflows; retain Plan initiative as a compatibility phrase where unambiguous.
7. Deliver the record guidance and naming support through canonical seeds, rendering, installation and upgrade. Generated skills remain thin pointers. Keep the workflow optional, lightweight and advisory; creating an arc grants no implementation authority and changes no existing wave gates.

## Scope

**Problem statement:** Response-only initiative planning has no stable record location, and its public name is currently fixed.

**In scope:**

- Plan initiative → Plan arc guidance and thin skill, the relevant Envision/Plan change bridges and catalogs.
- Vocabulary/profile naming, record paths, lifecycle ID recognition, minimal document validation and focused regression coverage.
- Seed delivery/reconciliation, rendered local surfaces, architecture and distribution documentation.

**Out of scope:**

- New runtime, MCP lifecycle endpoints, scheduling, status database, dashboard, mandatory feature/story records or additional review gates.
- Relocation of existing waves, automatic renaming of user records, rewriting historical evidence, or revising the product vision in this change.

## Acceptance Criteria

- [x] AC-1: A default Arc fixture and an Epic-profile fixture produce the specified folder/file pair, consistent command/prompt/skill names and collision-safe lifecycle IDs. Existing wave/change naming remains unchanged; unsafe paths and conflicting names are rejected.
- [x] AC-2: One small create-and-resume walkthrough recovers the outcome, remaining obligation and next useful wave from an arc with two linked wave records, preserving an operator edit and distinguishing delivered work from unproven benefit. A no-arc change still plans normally. Record observed results and limits without claiming broad workflow superiority.
- [x] AC-3: Fresh delivery and an existing customized Plan initiative upgrade yield one usable canonical workflow, preserve custom content and leave existing records/links intact. The Epic example is covered by the same delivery checks. No new lifecycle gate or duplicate wave records are introduced.

## Tasks

- [x] Define the profile and record contract, compatibility behavior and concise template.
- [x] Extend naming, ID recognition and delivery; update canonical guidance and render local surfaces.
- [x] Run the focused fixtures and one walkthrough; update affected docs and record evidence.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Naming and record contract | Implementer | — | One owner for shared profile and ID edits. |
| Guidance and delivery | Implementer | Contract | Reuse existing renderer and reconciliation paths. |
| Verification | QA | Delivery | Focused fixtures and one walkthrough. |


## Serialization Points

One implementer owns shared naming and delivery edits. Review the final integrated surfaces together.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/lifecycle_id.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`
- `docs/prompts/`
- `docs/architecture/data-and-control-flow.md`

Scope edits within these directories to the requirements above. Registry/catalog, distribution documentation and generated skill updates are included; unrelated source and prior wave evidence are protected.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` for the arc record and continuation flow, and the applicable distribution/profile documentation for Arc/Epic naming and explicit migration. Update the architecture hub only if navigation changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the requested naming and downstream override. |
| AC-2 | required | Checks that the record supports continuation without adding a mandatory layer. |
| AC-3 | required | Carries the behavior safely to existing projects. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-03 | Observe: implementation and independent delivery review complete. All ACs and tasks are met; wave remains open. The admission-time Session Handoff below is historical; this row records current completion without changing the reviewed contract. | Full suite 12,310 tests / 217 files / 12 skips passes, receipt inputs 8ab092cfa28ac8d410dc63ad344622f522af6d28c5df3fd4bb227f9f5370f7ac. Fresh code, QA, architecture, docs-contract and targeted Council approve. One stale import expectation was repaired and independently reverified; the temporary baseline scan issue was corrected without product changes. See arc-delivery-evidence.json and typed review records. |
| 2026-11-03 | Observe: core implementer reports seven focused tests passing through public ID generation, safe paths, collision discovery, registered migration and Epic rendering. | Core regression checks continue; this is interim evidence, not delivery approval. |
| 2026-11-03 | Thought: exercise the current prompt through one isolated create/resume author and the seed100/160 merge instructions through four small fixture targets. | arc_walkthrough and arc_reconciliation contexts have disjoint fixture write scopes; no actual project records or visions are writable. Frozen walkthrough oracle is withheld from author. No added review or repeated authoring batch. |
| 2026-11-03 | Observe: shared contract and concise record guidance drafted. Stable seed171 now describes Plan arc; local plan-arc replaces its known prior self-hosted copy. Distribution names use ARC_NAME, ARC_KIND, ARCS_ROOT and the plan-arc prompt override. | Seed100/160 distinguish byte-preserving registered migration from agent prose reconciliation and unresolved conflicts. Frozen continuation inputs/oracle: .wavefoundry/work/22bs0/arc-walkthrough. |
| 2026-11-03 | Observe: all four fresh readiness lanes and targeted Council approve the expanded scope; no findings or plan repair. Prepare ready and Implement succeeded; source gates opened. | Receipt review-policy-1e0657061135d91fc15f. Standard red-team primer, docs-contract seat, chair and closing reconciliation; runtime identity unverified. |
| 2026-11-03 | Readback: replace the optional response-only entry with Plan arc, preserving its continuation reasoning in one durable lifecycle-named document. Example: docs/arcs/ID shared-inference/ID-arc shared-inference.md; Epic uses the declared root, kind and prompt override. AC-1 covers naming/IDs, AC-2 continuation, AC-3 delivery. No new wave gate or endpoint. | Python implementer owns profile, path, ID, renderer and focused tests; coordinator owns canonical/local guidance, catalogs and integration. |
| 2026-11-03 | Thought: implement the shared naming and collision contract in parallel with its seed/document guidance, then integrate before testing. | ARC_NAME, ARC_KIND, ARCS_ROOT and existing PROMPT_NAME_OVERRIDES; keep canonical seed 171 filename stable for reconciliation. |
| 2026-11-03 | Thought: run independent readiness on the expanded scope before edits, then implement shared naming/record support, guidance and delivery, followed by focused checks and required delivery review. User explicitly requested preparation, review and implementation. | Readiness receipt review-policy-1e0657061135d91fc15f; independent review coordinator arc_readiness. Current capable model selected for cross-cutting contract judgment; actual runtime identity unverified. |
| 2026-11-03 | Admitted to wave 22bs0 at operator direction. Product intent reviewed against the requested lightweight arc record and downstream Epic naming; expanded readiness remains pending. | Operator request and wave Changes section; no new source edits or approval claims. |
| 2026-11-02 | Authored a follow-up plan from the operator's arc naming and downstream Epic requirements. No source edits, admission or readiness. | Current Plan initiative remains delivered in wave 22bs0. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-02 | Use one lifecycle-named document in an ID-and-slug folder. | Follows the operator's filename convention and the existing wave folder shape; supporting material can remain beside it. | A flat file has no supporting-material home; arc.md omits the requested identifying filename. |
| 2026-11-02 | Extend existing distribution naming mechanisms. | vocabulary_profile already owns prompt overrides and record_paths owns fork-editable roots. Plan initiative is currently fixed, so explicit support is needed. | Hardcoded Arc prevents downstream Epic; a new runtime configuration layer adds unnecessary machinery. |
| 2026-11-02 | Keep waves in their current folders and link them. | Preserves wave authority and avoids duplicate records and migrations. | Nesting waves under arcs couples existing discovery and lifecycle behavior to optional planning. |

## Evidence and Evaluation

Source inspection confirms `vocabulary_profile.py` owns `DEFAULT_PROMPT_NAMES` and currently reserves Plan initiative as fixed; `record_paths.py` owns fork-editable record roots; `lifecycle_id.py` owns the shared ID policy. Proposed arc behavior is unimplemented (`execution_status: unverified`). Validate exact ID recognition and profile extension points before coding; do not infer support merely from these existing mechanisms.

The efficacy check is a single bounded continuation walkthrough, supported by focused naming/delivery regression tests. Success means recovering the remaining obligation and useful next step without duplicating wave state. Count neither document creation nor a closed wave as proof of beneficiary value. If the walkthrough fails, report the failure and repair options before adding another agent evaluation batch. Required framework checks remain ordinary delivery gates, not additional arc process.

## Risks

| Risk | Mitigation |
| --- | --- |
| A lightweight record grows into another lifecycle. | Keep narrative progress and wave links; add no approval or state-transition machinery. |
| Renaming breaks existing customizations or links. | Preserve IDs and content; require explicit migration and exercise upgrade reconciliation. |
| Arc is confused with an admitted change kind. | Treat it as an optional planning record; reuse ID generation without adding change admission behavior. |
| Broad profile changes affect unrelated workflows. | Test default and Epic names together with unchanged wave/change contracts. |

## Session Handoff

Admitted to wave 22bs0 as its second change; not yet readied or implemented. Preserve the first change’s implementation and evidence. Prepare wave must reconcile the expanded scope before arc source edits. Admission does not authorize a commit, build or closure.
