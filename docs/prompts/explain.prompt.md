# Explain

Owner: Engineering
Status: active
Last verified: 2026-11-22

Shortcut: **`Explain`** or `/wf-explain`

Help the operator take responsibility for the changed code. Explain what the team built, how it works, why it took this shape and what still needs attention. Use the project's names for lifecycle records. Keep the walkthrough in the conversation.

## Choose the delivery

Use the delivery just reviewed when the engineer accepts the review offer. A direct request can name an open or closed record or a single admitted change. Ask which record they mean if the reference is ambiguous. Read the record, its decisions and review findings. Use `wf_get_change(wave_id=...)` for the admitted set or `wf_get_change(change_id=...)` for one change. Follow relevant code, documentation, diffs and verification records using the project's read-only retrieval tools. If a record is missing or work is unfinished, say which claims the available evidence supports.

On request, walk through a spec that is still in progress. Separate behavior that an executed check verified, work and checks that are still planned, and unknowns. Name each executed check with its result, and label a planned check as planned. A routine fix needs no walkthrough unless the operator asks for one.

## Walk through the change

- Start with one observable difference for a user or maintainer. For several changes, explain how they fit together and offer a place to drill down. For one named change, include a sibling only when a dependency explains the behavior.
- Trace a representative input or action through the real entry point to its result. Link to the relevant files and name the symbols. For a documentation or configuration change, trace the instruction or setting through to what the reader or system does.
- Use a diagram when it helps the maintainer follow a consequential request, state transition or recovery path. Keep a straightforward change in prose. Link a maintained architecture diagram if it accurately shows that path. If it is stale, identify the discrepancy and trace the path you verified.
- For a new diagram, name the components and give each arrow a verb that reads from source to target. Explain what crosses each boundary. Cite the entry point and the implementation or test supporting the trace, and say where the evidence ends. For a graphical walkthrough, follow **Dashboard flowchart syntax** in the project's planning prompt. Keep the diagram in the conversation and route permanent corrections through the project's documentation workflow.
- When the design changed, show where responsibility, data flow or a public contract moved. For a library added, replaced or removed, name it, locate its use and explain why the team chose it and what it requires of the maintainer. Check the diff and dependency manifest for the reviewed revision.
- If the implementation or its design record identifies a named algorithm, give its name, point to where it runs and explain what it does here. Explain why the algorithm works for this input and, separately, why the team picked it. Tie the selection to a recorded constraint, alternative or tradeoff. If the record explains only suitability, leave the selection rationale unknown. Leave unnamed logic in plain language.
- Tell the operator whether the team considered performance and security. For each, state the concern, the decision and any remaining exposure that the record supports. For a performance change, connect the old bottleneck to the implementation change and its effect on the user or operator. Give the before and after values, units, workload and comparison conditions when recorded. If the team measured only an intermediate metric such as queue operations, say what improved and whether it measured the resulting latency, cost or capacity. Label predictions as expectations. For security, distinguish a proposed safeguard from one the team exercised. If the diff shows a safeguard but the review gives no rationale, describe what the code does. If you find no recorded assessment, say so briefly. Silence establishes neither safety nor a performance result.
- Describe implementation problems that shaped the result, including ones the team resolved before review. Use the progress log, diff or finding to explain what failed, how the team handled it, and any cost or workaround the operator inherits. Skip routine debugging details.
- Explain a consequential choice and the alternative the team considered. Cite the decision, spec or finding that records the reason. If no one recorded a reason or alternative, say so. Identify any inference as your own.
- For each material claim, name the test, check or observation, its condition and the assertion that distinguishes success from failure. Identify what ran and its result. Match a historical result to the version of the check that ran. A stronger assertion in today's source or a green suite without that link leaves the stronger claim unverified. For example, counting failed accepts shows that the server retried. A fresh request succeeding on the same server shows that it recovered.
- Finish with the work the operator inherits: outstanding TODOs, temporary compromises, deferred checks or open decisions that affect this change. Say what will resolve each one and give its owner, issue or revisit condition when recorded. Separate resolved issues from remaining work and planned follow-ups from your own suggestions.
- Keep the handoff proportionate. Omit empty categories. When the operator asks about one, distinguish a verified absence from a gap in the record. Give the recorded reproduction command or next check when useful. Let the operator choose where to go deeper.

## Show the path in a terminal

In Codex CLI and Claude Code terminal sessions, draw the path directly in the reply in a fenced `text` block. Use the same default when the display is unknown. Put each verb on the arrow from its source to its target. For example, a handler reads a record and sends a reply:

```text
Handler
  +-- reads from --> Store
  +-- sends reply to --> Client
```

Keep lines short enough to read without wrapping. Stack steps vertically or split a wide graph into short paths. Repeat component names at joins and keep both verbs on parallel paths. Plain ASCII works when box-drawing characters display poorly. For zooming or sharing, link an existing SVG or dashboard view after the text diagram. If the reader requests a new SVG, handle the export separately from the read-only walkthrough.

## Test my understanding

Offer this optional exercise after the walkthrough, or start it on an explicit request. Ask **one** practical question about maintaining this delivery and end the turn. Choose a design decision, algorithm, dependency, performance or security tradeoff, workaround or open task with a real consequence. Wait for the engineer's answer. Use the actual assertion or decision to explain what their answer establishes and where it falls short. Let them retry, ask another question or stop. Accept a stop immediately. Keep answers and feedback unscored.

Use read-only operations throughout. A walkthrough, a declined or unanswered offer, and a teach-back have no effect on approvals, checklists or closure. Leave files and review events alone. If the conversation reveals a discrepancy, cite the evidence and point the engineer to the normal review or repair workflow.
