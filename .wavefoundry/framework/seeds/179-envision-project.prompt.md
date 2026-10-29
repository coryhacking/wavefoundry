# 179 - Envision Project

**Applicable when:** any project. Establish or revise an ambitious product vision and an adaptive roadmap through useful, enduring capabilities and their technical and nontechnical prerequisites. This is an authoring workflow, not implementation planning or autonomous execution.

**Shortcut:** `Envision project` · **Skill:** `wf-envision`

Imagine what this product could make possible for people and why that future matters. Seek the greatest relevant value, financial and otherwise, while making tradeoffs and uncertainty visible. The vision names the desired future; supporting strategy explains the choices and path from today's reality. A roadmap of technical and nontechnical advances makes that path credible. Selecting the next investment follows from this argument.

## Scope and output

Default output is `VISION.md` at the repository root; a new document is titled `<Project>: Vision and Roadmap`. Preserve existing titles and canonical locations unless the operator requests a change, and honor requested filenames. Preserve valid existing material and unrelated operator edits. Detailed review evidence belongs in a sibling such as `VISION-review.md`, or the existing canonical review location; honor response-only evidence requests. A discussion, prompt-writing request or explicit read-only review writes neither artifact: return the requested advice and review record in the conversation.

For a new or substantially revised vision, the default advisory scope is architecture review, a standalone red-team challenge and Archetype Council. A substantial revision changes purpose, beneficiary, the set of horizons or their order; other edits use affected reviews proportionately. Select review scope and depth by stakes, maturity and uncertainty. Narrowing the default requires a stated reason tied to that brief, never lower author effort alone; high-stakes or highly uncertain visions keep the default unless the operator directs otherwise. Honor explicit full-review requests and operator-directed narrowing or omission. These are advisory artifact reviews, not lifecycle gates. This workflow creates no wave, implementation backlog, deployment, commit or publication, and grants no implementation or approval authority.

## 1. Establish the brief

Reuse the conversation, existing vision and project context. Establish the intended ambition, beneficiary, outcome, planning horizon, constraints and deliverable. Use an adaptive interview only for material gaps: who struggles and what progress they seek; what they do or use today; the team's pivotal insight; why now; whom and what the product will deliberately not serve; who adopts, pays for or sustains it and why; and what failure would look like even if it ships. Do not turn this question bank into a mandatory questionnaire.

When material information is missing, combine necessary questions and your inferred-brief readback in one pre-draft exchange. Keep the questions brief and separate them from the review notice in readable paragraphs. With a sufficient brief, state the interpretation and proceed without seeking confirmation. Defer nonblocking questions into the draft; explain the consequence of genuinely blocking strategic ambiguity.

In that same briefing, state selected review scope, any reason for narrowing and expected effort. Do not separately ask approval for the readback or routine reviews: the notice lets the operator steer. When all three forms and a five-axis Council are selected, review involves eight role contexts: architecture, red-team, chair and five seats. A small new vision does not automatically require that full set; apply the stakes rule above. Distinguish selected scope from actual concurrency or host reuse; invent no cost or duration estimates. Reuse an already explicit scope without another interruption.

A twelve-month horizon and unlimited resources are optional parameters, not defaults. Do not impose autonomous agents, cloud services, a business model or a fixed number of horizons. Use only this project's brief and sources.

## 2. Ground the need and starting point

Build a compact diagnosis: the progress beneficiaries seek in their circumstances, what makes it hard, the insight that opens a better possibility and why the opportunity is timely. Use supplied interviews, observations, usage/support evidence or research. Distinguish sourced observations, interpretations and untested hypotheses. An enduring need or provisional timing hypothesis is legitimate; invented urgency, customers or testimony is not. Repository facts establish capability, not demand. Missing primary research permits a provisional vision with visible gaps; identify the cheapest useful research into the most consequential uncertain need. Neither a fixed interview count nor this workflow substitutes for primary research or stakeholder alignment.

Follow the target repository's instructions and investigation workflow. Where Wavefoundry retrieval is configured for that target, use Guru and indexed retrieval, then validate load-bearing claims against current source. Confirm a delegated worker's actual tool access. If target-scoped MCP retrieval is unavailable, use targeted local inspection and disclose the evidence gap; an index attached to a different repository is not evidence for this target.

Inspect the existing vision, project orientation, architecture, operating constraints and implementation relevant to the direction. Use focused safe checks where an executable claim matters. Distinguish verified capabilities, partial foundations, new engineering and unresolved research. Historical plans, passing record validation and confident prose do not prove shipped behavior. Do not run unrelated suites, setup or environment changes merely to author the vision.

Use a supplied landscape or external research within the operator's authorized scope. Otherwise disclose the landscape gap or request the needed research scope; do not silently add network research to a local-only engagement. Identify tensions between the destination and today's architecture or product boundary. Explain the transition and future decision needed; neither silently change today's contract nor treat it as an eternal limit on ambition.

## 3. Draft the vision and roadmap

Lead with a short, repeatable destination statement in the beneficiary's language: what becomes possible and why it matters. Follow it with a concise roadmap overview before detailed rationale. The opening alone should convey the distinctive future; the roadmap explains how useful stages make it real. Write a coherent argument, not a feature wishlist or completed headings.

Scale depth to stakes, maturity and uncertainty, with no fixed word ceiling. Diagnosis, strategic choices and non-goals, foundations, useful horizons, consequential dependencies, riskiest assumptions and the next bounded advance remain core. Add analytical detail only when it helps a consequential choice or makes the path credible; a small internal tool or library need not carry a competitor study or elaborate measurement machinery.

### Destination and strategic choices

When the destination is open, explore meaningfully different futures and recommend one with reasons. When the operator has chosen it, preserve it. Do not limit the future to an extrapolation of today's implementation or backlog. Make the destination memorable through a concrete end-to-end experience: what people do, what the system does, where human judgment remains and what people receive. Connect the diagnosis and pivotal insight to this experience. Explain financial and nonfinancial value, costs and beneficiary tradeoffs without inventing a common score or asserting that one direction is provably optimal.

Compare real alternatives where consequential, including existing manual practice, competing products, do-it-yourself or doing nothing. Explain who/where to focus, why people would choose this product, and deliberate non-goals and sacrifices. Use advantage analysis when it helps explain a choice; distinguish a benefit from the mechanism that could sustain its value. Label unproven claims; do not invent a moat. For internal, public or open products, enduring usefulness, adoption and stewardship may matter more than excluding competitors.

### From the destination to useful horizons

Work backward from the ultimate experience to necessary capabilities, foundations and prerequisites, then forward through useful horizons. Cite current capabilities concisely, including their verification limits and the distance to the destination. If source and documentation conflict, explain the consequence for the path. Label proposals and unresolved research.

Assess value, usability, feasibility and viability at the destination. Each horizon needs a beneficiary outcome, useful intermediate value if later horizons never arrive, and meaningful conditions for advancing or reconsidering. Identify which consequential risk it reduces and what evidence will resolve it. Near horizons have concrete end-to-end demonstrations, exit criteria and failure conditions; an unchanged baseline must fail a new capability demonstration. Detail and precision decrease with distance: later horizons state intended outcomes, consequential assumptions, provisional advancement/reconsideration conditions and evidence needed to firm them up. Qualitative conditions are valid. Do not invent distant numerical targets, dates or implementation commitments; retain justified operator-supplied timing as an explicit aspiration or constraint. Where research must precede a usable slice, name its uncertainty, stopping condition and the beneficiary value it enables; research activity or infrastructure completion alone is not product value.

Treat relevant nontechnical work as roadmap work alongside engineering: research, adoption, distribution, funding, partnerships, operating practices and team capability may have milestones and prerequisites. Include only tracks the product needs, connecting each to an outcome or uncertainty it resolves. Explain cross-workstream dependencies, including where a nontechnical prerequisite gates an engineering advance; count these dependencies toward the critical path, not as a disconnected checklist.

Explain how each advance enables what follows. Include components, state ownership, interfaces, instrumentation and uncertainties where they explain the path. Show dependencies, parallel opportunities, critical path and timing assumptions; exit evidence establishes completion. If unlimited-resource analysis helps the argument, explain what extra experiments or specialists buy and which bottlenecks remain; more workers do not imply proportional progress. Keep detailed tickets outside the vision.

### Endurance and adaptation

Explain how the product remains operable and changeable, at the depth its risks warrant. Distinguish durable principles from current rules proposed for reconsideration. Name consequential sources of truth, ownership/contracts, trust boundaries, execution locations and integrations; use a component/data-flow diagram when it clarifies existing and proposed foundations. Address maintenance, feedback, human decisions, costly-to-reverse commitments, replaceable boundaries and migration where relevant. Keep unresolved designs visible and preserve justified options without speculative extensibility.

For a major assumption that could fail, explain what remains useful, what would change and which decision returns to the operator. Revisit the vision when horizons meet or miss exit criteria, critical assumptions or questions change, or new beneficiary/market evidence changes the brief. Adaptation should preserve the purpose where justified while making any proposed change of destination explicit.

### Evidence and next investment

State how success and failure would be recognized, proportionate to the claim. Where measurement helps, propose a primary beneficiary outcome metric with guardrails against harm or gaming, or a small justified set if one number would distort the purpose. Explain necessary baselines, observation windows and limits; do not force a detailed evaluation design onto a claim that needs a simpler demonstration. Include reliability, total cost, maintenance burden, failures, abandonment, human rescues and delayed regressions where relevant. Distinguish targets and proposed metrics from observed results; activity counts are not success measures.

Map the riskiest assumptions to cheap discriminating experiments and the evidence that would change the decision. Use independent evaluation, repeated attempts and held-out cases when the credibility of the claim needs them, whether or not the product is agentic. For agentic systems, specifically assess evidence quality and separation of evaluator from evaluated system. State what cannot yet be justified, simulated, measured or guaranteed. Connect a compelling ultimate demonstration to the next bounded investigation or change to consider.

An optional clarity check is a short fictional future announcement and three hard customer FAQ questions. Keep it temporary unless requested, label it as imagined and never invent real testimony. This tests narrative clarity, not customer validation.

## 4. Review one identified draft

The author coordinates review but does not impersonate independent reviewers. Give each worker the same identified draft (path and revision or content fingerprint), brief, evidence sources, write boundaries and relevant unresolved questions. Reviewer work is read-only against source and the vision. Parallel independent reads are useful; serialize revisions so reviewers know which draft they judged.

Give reviewers the reader outcome test in section 3. Preserve the requested ambition across every review and repair. Correct false capability claims, broken reasoning, unsupported certainty and dependency errors. Challenges to the destination's size or direction are explicit strategic decisions for the operator, not permission to silently substitute a safer or smaller future. Keep contrary feasibility evidence, consequences and alternatives visible; distinguish desired outcomes, assumptions and established facts. Continue reviews under the established scope without another routine approval; return only for material scope/authority changes or unresolved strategic choices.

Use the target's canonical role and prompt documents. The installed seeds provide a fallback when a project omits a local role or command; this does not require enabling a role, changing configuration or installing anything:

| Review | Canonical instructions | Focus on the vision |
| --- | --- | --- |
| Architecture | `docs/agents/architecture-reviewer.md` (or the project's actual role); fallback `.wavefoundry/framework/seeds/214-architecture-reviewer.prompt.md` | Current-state accuracy, foundations, dependency order, ownership, interfaces, trust boundaries and feasible transition. |
| Red-team | `docs/prompts/red-team-review.prompt.md` and `docs/agents/specialists/red-team.md`; fallback seeds `177-red-team-review.prompt.md` and `225-red-team.prompt.md` | Failure modes, unsupported bets, stronger alternatives and disconfirming evidence; choose an appropriate standalone lens and retain its canonical output. |
| Archetype Council | `docs/prompts/archetype-council.prompt.md`, full protocol `.wavefoundry/framework/seeds/236-archetype-council.prompt.md`, and `docs/agents/specialists/council-chair.md` (fallback seed `215-council-chair.prompt.md`) | Strategic choices, reader understanding, testable claims, enduring value, adaptability and simplicity. |

Run the selected forms under their canonical independence and execution protocols. When all three are selected, architecture and standalone red-team may run independently, then the council-chair conducts Archetype Council; its optional primer may reuse the actual red-team output for this draft. Follow seed 236's seat/axis selection, isolated execution, synthesis and closing reconciliation/falsification protocol rather than copying it here. Report selected, omitted and unavailable coverage, context sharing and actual execution honestly; proportionate scope does not relax a selected form's protocol.

**Artifact-only boundary:** instructions about delivery-wave records in generic role documents apply when performing that lifecycle. Here, do not call Prepare, Review wave or review-approval tools, create wave records or write `council-readiness`/`council-delivery` approvals. A vision review does not replace required specialist or Wave Council approval for later implementation. Credible security issues go to the appropriate specialist; red-team does not issue security signoffs.

**Capability limit:** if independent workers, required instructions or a review capability are unavailable, continue useful authorized drafting or advice. Label any author self-check as such, identify the missing review and leave that outcome pending. Never claim it passed, silently relabel the author as a reviewer, or reconfigure the host to make it available. If a review is explicitly omitted by the operator, record that scope without pretending it ran. A draft with pending review remains usable but is not described as independently reviewed in those areas.

## 5. Reconcile, validate and deliver

Collect initial findings before editing. Apply canonical dispositions, explain material decisions and incorporate accepted improvements into the argument. Preserve genuine research uncertainty and operator-owned strategic choices as open questions. When revising an existing vision, preserve unrelated material, reconcile contradictions and explain substantive directional changes.

Use one initial review pass, one bounded author repair pass and one focused verification by affected reviewers. At that boundary, report remaining actionable findings and decisions rather than starting an automatic review loop or claiming convergence. A material change of direction may need a new brief and review scope; obtain that decision before proceeding with dependent work.

Put draft identity, actual reviews/axes, verdicts, material dispositions, incorporated changes, open review decisions and unavailable/omitted coverage in the sibling review file or selected evidence location. Preserve existing sibling content rather than blindly overwriting it. Keep at most a short dated review-status link in the vision; enduring assumptions and strategic questions still belong in its argument. Keep routine seat transcripts temporary and retain evidence for material conclusions. Read-only requests keep this record in the response and change no files.

Check citations, links, prerequisite order and the horizon content contract. Run applicable documentation validation: with target-scoped Wavefoundry MCP use `wf_validate_docs`; without it use the project's supported docs check (Wavefoundry CLI: POSIX `./.wavefoundry/bin/wf docs-lint`, native Windows `.\.wavefoundry\bin\wf.cmd docs-lint`). Fix introduced defects and report unrelated failures without widening scope. Passing docs lint proves document consistency, not that the future capabilities exist.

At delivery, state whether the project or operator has explicitly adopted the vision; authoring, review and Git tracking alone do not adopt it. If it is not adopted, explain how to designate it with a one-line pointer in `AGENTS.md` or the project overview, for example `Canonical product vision and roadmap: VISION.md`, using the actual path. Do not write a designation without operator direction; preserve existing adoption when revising a designated vision.

Once adopted, subsequent Plan change work identifies which horizon and outcome the requested change advances and carries forward consequential prerequisites and assumptions; it does not select work or redirect the request to manufacture alignment. A designated uncommitted vision counts; a committed draft does not. **Delivery evidence informs horizon progress; recording it in the vision is an Envision revision or an explicit operator edit.** Met or missed exit conditions inform reconsideration without silently changing the destination or authorizing subsequent work. Planning leaves vision and review artifacts unchanged, adds no tracker, mandatory section or vision prerequisite, and accepts legitimate changes without direct horizon fit.

Return the document path or requested read-only advice, central direction, value and horizon sequence, actual review outcome and material open decisions. Explain how the result meets the brief, what the operator should inspect first, and what changed in direction and why. Recommend the next bounded investment without automatically creating plans or starting work.
