# Evaluate Decision

Owner: Engineering
Status: active
Last verified: 2026-06-27

Shortcut: **`Evaluate decision`** | Aliases: **`Evaluate option`** / **`Compare options`** / **`Architecture evaluation`**

## Purpose

Structured multi-seat evaluation of an architectural decision, technology comparison, or build-vs-buy question. Combines a red-team adversarial pass with a Wave Council review, followed by an operator interview, and produces an ADR.

## When to Use

- Choosing between two technical approaches where both have real merit
- Revisiting a prior decision in light of new information
- Documenting the reasoning behind a technology choice before it is forgotten
- Any time the question has been deferred with "there were complications" as the rationale

## Behavior

Follows the seven-phase contract in `.wavefoundry/framework/seeds/176-evaluate-decision.prompt.md`:

1. **Frame** — scope the question, establish current state, define what is out of scope
2. **Guru: current-state grounding** — read the actual implementation before the red-team argues; correct framing assumptions from code evidence
3. **Red-team** — adversarial comparison; argue from the strongest version of each option; name specific failure modes and the conditions under which the losing option would win
4. **Council** — reality-checker challenges red-team framing; red-team second pass challenges itself; wave-council synthesizes with explicit bounds
5. **Operator interview** — the most important phase; operator probes assumptions, adds historical context, refines scope; agents update analysis in response, not just acknowledge
6. **Guru: feasibility check** — ground the recommended future path in current code structure; confirm additive vs restructuring before writing the ADR
7. **ADR** — written after the operator interview; includes context scope, single-sentence decision, alternatives not fully rejected, explicit revisit conditions, and what will not be built

## ADR

Use the template at `docs/architecture/decisions/template.md`. Generate a lifecycle ID for the filename:

```bash
wf lifecycle-id --kind doc --slug <short-name>
```

## Example

The evaluation of MCP-embedded tree-sitter vs LSP-backed code navigation (May 2026):

1. **Framed**: structural navigation only; semantic search (`code_search`, `code_ask`) explicitly out of scope
2. **Guru**: confirmed `code_definition`, `code_references`, `code_outline` follow a provider-merge pattern — gave the red-team accurate entry points
3. **Red-team**: LSP wins on type precision; loses on deployment complexity, startup latency, state management, language coverage gaps
4. **Council**: reality-checker flagged the precision ceiling as a future concern; red-team second pass noted the semantic index has its own freshness trade-offs; wave-council added explicit revisit conditions
5. **Operator interview**: clarified LSP is irrelevant to semantic search; introduced IDE-resident server bridging; confirmed standalone servers already exist — we should not build our own LSP client
6. **Guru**: confirmed LSP tier-0 insertion is additive — three functions, same merge pattern, no restructuring needed
7. **ADR**: `docs/architecture/decisions/12t6f-adr code-nav-lsp-vs-mcp.md`

The operator interview added three dimensions that materially changed the ADR's alternatives section. Guru's feasibility check confirmed the future path is low-friction, which strengthened the revisit guidance.

## Notes

- Run the full three-seat council even when the red-team evaluation feels conclusive — the reality-checker and second-pass reliably surface nuances that improve the ADR.
- The operator interview is not optional. Agents work from the repository; the operator holds context that is not in it.
- If the evaluation produces "it depends," the ADR must name exactly what it depends on.
