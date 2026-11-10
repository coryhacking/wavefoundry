# Write for the reader's task

Owner: Engineering
Status: active
Last verified: 2026-11-10

Help the intended reader understand, decide or act accurately. Before drafting, identify that reader, what they already know, and what they need from this artifact. Let that task and the consequences of misunderstanding determine the detail. Brevity is useful when it removes effort without removing meaning.

Use this guide when authoring or substantially revising prose. Apply it to documents naturally touched later; it does not authorize rewriting history. Explicit user formats and project writing policies take precedence. Surface consequential conflicts. A consequential point is one that would change the reader's decision, action or result if omitted, missed or misread. Keep required headings, metadata, identifiers, evidence schemas and audit records intact.

## Relevant: give readers what they need

Start with the answer, intended outcome or decision the reader came for. Explain why it matters in concrete terms. Include the conditions, limits and supporting evidence needed to use it correctly. A status update should reveal the current result and next authorized action before recounting work performed.

Separate observed facts, interpretations, proposals and unknowns. State the scope of evidence beside the claim it supports. A successful example proves that example; a planned test is still planned. Keep uncertainty visible when removing it would change a decision. Omit procedural history unless it explains a live constraint, tradeoff or continuation need.

## Findable: put information where readers look

Order the document around the reader's questions. Give the main point first, then the explanation and evidence needed to assess it. Use descriptive headings and stable project anchors. Put a condition or exception close to the statement it qualifies. Link to the authoritative detail with a label that tells readers what they will find.

Use paragraphs for connected reasoning, lists for sequences or genuinely parallel items, and tables for comparisons. Choose diagrams when they make a relationship easier to inspect. Avoid splitting one argument across many tiny sections or making readers assemble its meaning from disconnected bullets. Keep one canonical owner for reusable guidance.

When developing an argument, identify its governing thought: the answer, intended outcome, recommendation or unresolved decision relevant to the reader. Develop distinct supporting points that together explain or justify it. Each summary must follow from the reasons or evidence beneath it. Group comparable ideas and order them by dependency, time, structure or importance. Check for missing support, repetition and conclusions stronger than the evidence. Keep consequential uncertainty and contrary evidence visible. Cross-cutting concerns may need explicit connections; the reader's task determines the grouping and number of points. Situation, complication and question can clarify that task when useful, without adding a compulsory introduction or displacing a requested answer-first opening. Evidence and exploration shape the recommendation before presentation is organized; required reference layouts, procedural order and artifact contracts retain precedence.

## Understandable: make meaning explicit

Use familiar words and direct verbs. Name the actor when responsibility matters. Keep a term consistent for the same concept, and distinguish concepts that have different effects. Retain necessary technical vocabulary; explain it for the audience instead of replacing it with an inaccurate everyday word. Make pronoun references clear.

For an instruction or requirement, preserve who acts, the triggering conditions, the action and required outcome. Give each step one coherent instruction; separate independent actions when order or verification matters. Keep exceptions, prohibitions, permissions, numerical constraints and units explicit. Do not weaken **must** into **should**, turn a recommendation into a requirement, or convert an example into a universal promise. Active voice often clarifies ownership; passive voice remains useful when the actor is unknown or immaterial.

In a requirement, acceptance criterion or status claim, name the setting, file, function, command, term, error text or limit the claim depends on, and define a term the reader cannot look up. If it is not yet known, say so and say what will identify it; do not guess a name. For example, “The importer reads its size limit from a setting that is not yet identified; the implementer will identify it by reading the importer's configuration loader before changing code.” A limit that a requirement imposes carries its number and unit, or states that the value is undecided and who will decide it. An adjective is a limit when a requirement acts on it and it stands for a quantity, as in “reject oversized records”. An adjective that names a category, as in “reject corrupt records”, is a term to define. An adjective of quality that a requirement acts on, as in “return a helpful error”, needs a definition or the observable result it requires. Any other adjective is a description. A requirement must not contain a hedge that leaves the obligation open, such as “if feasible”, “as needed” or “where possible”. When removing a hedge from an obligation, keep **must**; if the obligation is conditional, state the condition. Use **should** or “we recommend” only for text that was a recommendation, not a requirement. When the obligation depends on a condition, state the condition; a stated condition is not a hedge. A plan that fixes a defect shows the observed failure (the input or action, the actual result and the expected result) or says that the failure has not been reproduced.

For example, “The importer must reject a record larger than 8 MiB before storing it; an operator may raise the limit for an approved migration” cannot become “Large records are usually rejected.” The shorter sentence loses the actor, threshold, timing, obligation and authorized exception. An abstract version fails differently: “The importer should reject oversized records where appropriate, using the configured size limit.” There, “the configured size limit” names no setting, “oversized” states no number, “where appropriate” leaves the obligation open, and “should” weakens **must**.

There is no universal word or sentence limit. A long technical explanation can be necessary to expose a failure mode, dependency or consequential tradeoff. Remove repetition and needless indirection; retain the reasoning the reader needs to assess the result.

## Usable: support the next decision or action

Make prerequisites, expected results, failure handling and authority boundaries visible where readers act. Distinguish what is complete from what is proposed, blocked or awaiting a decision. Say what evidence would resolve a consequential unknown and who can authorize the next step. Clear prose does not grant permission.

Match the artifact to its purpose while preserving its existing contract:

| Artifact | What the reader should recover |
| --- | --- |
| Vision | One coherent account of enduring purpose, intended future and beneficiary value; then the reasoning, useful stages and unresolved choices. Preserve ambition and distinguish selected direction from possibilities. |
| Specification | Observable obligations, actors, conditions, inputs/outputs, exceptions and boundaries, with enough precision to verify behavior. |
| Architecture | Responsibilities, interactions, data/control flow, failure modes and consequential tradeoffs; explain why the boundaries matter. |
| Decision record | The decision, relevant alternatives, evidence, assumptions and consequences, including costs and conditions for reconsideration. |
| Change plan | The problem, intended outcome, scope and verification; show how the proposed work addresses the need. |
| Wave or status record | Current objective, actual progress, blockers, unresolved decisions and next authorized action, with evidence for completion claims. |
| Review finding | The concrete failure, affected behavior, evidence, consequence and actionable correction; distinguish an error from an editorial preference. |
| Handoff or release note | What changed, why it matters, verification and limits, remaining work, and the next step or operator action when needed. |
| Memory | The future action, when it applies, supporting evidence and consequential limits. |
| Prompt | The task and intended outcome, necessary inputs, ordered instructions, boundaries and expected result. |

## Check the reader's task

Before delivery, read the artifact as its intended reader. Can you find and explain the main point, how its supporting points justify it, the relevant obligation or choice, consequential limits and next action without reconstructing the author's work history? Check the explanation against its source: a fluent summary that changes meaning is a defect. Repair that defect before polishing style.

Existing applicable reviewers use these same reader tasks within their assigned remit and normal stop rules. Ask for a reconstruction of meaning, not a readability score or a shorter version. Keep factual and contractual findings distinct from preferences. This guide adds no review lane, council, approval gate or prose linter. Agent reconstructions provide bounded evidence; they do not establish human comprehension. Later operator feedback can inform ordinary revisions without a separate survey process.

## Basis and limits

This original guidance uses the relevant, findable, understandable and usable principles described by [ISO 24495-1:2023](https://www.iso.org/standard/78907.html), with selected precision practices informed by [ASD-STE100](https://www.asd-ste100.org/about.html). It is not a reproduction of either standard, an implementation of the full STE dictionary, or a claim of certified or fully verified compliance. Argument organization also draws on Barbara Minto's [Pyramid Principle](https://www.barbaraminto.com/). The guide is locally usable without fetching those sources.
