# 171 - Plan Arc

**Shortcut:** `Plan arc` · **Alias:** `Plan initiative` · **Skill:** `wf-plan-arc`

Plan a bounded outcome across useful waves, or resume that work from its records. Keep one concise arc document so another contributor can recover the outcome, evidence and next useful step. This optional workflow adds no approval gate; ordinary changes need no arc. Honor a read-only or response-only request without writing.

## 1. Recover the outcome and current position

Reuse the request, prior choices and relevant project records. Establish who benefits, the outcome, its owner, boundaries and what would count as success. Reuse the existing arc when resuming. If equivalent project-owned planning already exists, preserve its ownership and use it rather than duplicate it.

Where useful, distinguish **Vision → Horizon → Arc → Wave → Change**: the vision describes the destination; a horizon marks a stage of progress; an arc pursues a bounded outcome; a wave delivers an increment and contains changes. A horizon may have several arcs and an arc several waves. Features can describe capabilities without becoming another required layer. Preserve legitimate work outside this hierarchy.

For vision context, use the project's Plan change **Vision-to-plan bridge**: explicit designation or operator direction counts as adoption, not Git tracking or file presence. An undesignated root `VISION.md` is discovery-only; do not read it to decide relevance. No adopted vision means ordinary planning. Start small and follow consequential references.

Read the identified relevant waves, changes, decisions and handoff, following references needed for dependencies or conflicts. Prefer target-scoped MCP retrieval and typed lifecycle records when available; verify consequential claims against current sources. Distinguish delivered capabilities, accepted evidence, intended benefit and remaining obligations. Closure alone proves neither benefit nor authority for the next action. Check stale summaries against their sources; expose contradictions and missing evidence without inventing a dependency or reading all history. Cite available sources and revisions for consequential claims.

## 2. Recommend the next useful advance

Explain the remaining path at the detail needed now, then recommend a bounded wave/change proposal or a decision that must come first. Preserve intermediate value, significant prerequisites and unaffected work. Distinguish facts, interpretations, proposals and uncertainty; no detailed backlog or fixed questionnaire is required.

If a missing choice would materially change outcome, scope, priority or responsibility, explain the credible options, consequences and your recommendation, then ask one focused question. Reuse earlier answers; after an answer, briefly say how it changes priorities. Honor deferral, draft-first and no-interview requests with explicit provisional choices. Silence is not selection. Pause only the dependent recommendation and continue useful independent investigation. When an assumption changes, revise the affected path rather than reopen settled direction.

## 3. Keep one concise record and hand back the next step

Use the distribution's declared naming: `vocabulary_profile.ARC_NAME`, `ARC_KIND`, the `plan-arc` prompt-name entry and `record_paths.ARCS_ROOT`. Defaults are Arc, arc, Plan arc and `docs/arcs`. Resolve these from the installed framework; do not hardcode Arc when the distribution uses Epic or another name.

For a new arc, use the existing `wf lifecycle-id --kind arc --slug <arc-slug>` producer with the active kind substituted for `arc`. Use that generated prefix and slug for both folder and filename:

```text
docs/arcs/<lifecycle-id> <arc-slug>/<lifecycle-id>-arc <arc-slug>.md
```

The Epic example is `docs/epics/<id> <slug>/<id>-epic <slug>.md`. `record_paths.arc_record_path` resolves and validates the active convention. Do not invent IDs, overwrite an existing record or silently rename records when vocabulary changes. An explicit migration preserves IDs and content and repairs references. Keep waves at their configured root and link to them; do not nest, move or duplicate them under arcs.

Use ordinary document metadata (owner, status and last verified) and a `Record ID` matching the filename. Metadata describes the document; it is not a lifecycle state machine. A short record should let its reader recover:

- **Outcome:** beneficiary, intended result, success evidence, boundaries and relevant horizon, if any.
- **Path:** useful increments, important dependencies and unresolved decisions.
- **Progress:** linked waves and the evidence for delivered outcomes and remaining obligations.
- **Next step:** the next useful wave/change proposal or decision, with its rationale.

Adapt headings to the project. Preserve operator edits and unrelated content when revising. Summarize progress from authoritative records rather than copy their task lists or acceptance checks. Supporting files are optional when they help; create no empty folder hierarchy or second tracker. If evidence is missing, name the gap and useful next test.

Apply `.wavefoundry/framework/docs/writing-guide.md`; read the record against its sources and the reader's task. No routine council, independent reader or scoring exercise is part of Plan arc. Return the record path, what changed and the next useful step.

The record grants no readiness, implementation or other lifecycle authority. A separately requested Plan change or wave action follows its existing workflow and rechecks mutable facts. Do not create, admit, open, close, implement or commit a wave/change merely because the arc recommends it. Leave visions and their review records unchanged. Installing or rendering this workflow never runs it or creates arc records.
