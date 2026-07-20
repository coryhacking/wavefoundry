# Wavefoundry: The Agent Harness for Software Repositories

Owner: Engineering
Status: active
Last verified: 2026-07-20

---

## The Problem

AI coding agents are capable. They can read a codebase, understand a problem, write correct code, and explain what they did. What they struggle with is *operating across time* — maintaining coherent state across sessions, enforcing process on themselves, handing off work cleanly, and verifying that what was done actually matched what was intended.

The typical failure modes are not dramatic. They are quiet:

- A feature gets half-implemented across two sessions because the second session didn't know what the first left unfinished.
- A security review gets skipped because the agent summarized what it *would* have checked rather than what it *did* check.
- Documentation diverges from the code it describes, with no one responsible for the gap.
- A wave of changes ships with no record of what was decided, why a particular approach was chosen, or what risks were accepted.
- An operator discovers weeks later that a guardrail was bypassed because the agent couldn't find the constraint, not because it chose to ignore it.

These aren't model failures. They are *harness failures* — failures of the operating context in which the agent works.

---

## The Insight: Agent = Model + Harness

Martin Böckeler's framing is useful here: an AI agent is not just the model. It is the model *plus its harness* — the scaffolding of feedforward guidance and feedback sensors that shapes behavior before and after each action.

Most teams deploying AI coding agents invest heavily in feedforward: system prompts, tool descriptions, coding guidelines, instructions about what to do. Feedback — structured mechanisms that verify what actually happened and route that signal back to human review — gets much less attention. The result is a lopsided harness that guides well but cannot verify.

Wavefoundry addresses this asymmetry. It gives agents both:

- **Feedforward guidance** — numbered seed prompts that cover every lifecycle step, from planning a change to reviewing architecture to distilling journal lessons at closure
- **Feedback sensors** — computational sensors (shell commands that produce exit codes), inferential sensors (LLM-run reviewer agents that assess code changes along specific dimensions), and structural gates (server-enforced checks that block closure until required evidence is recorded)

The goal is not to eliminate human judgment. It is to *direct* human judgment to the places where it matters most — and to reduce the amount of human attention spent verifying that routine process was followed correctly.

---

## The Wave Framework

The core organizing concept in Wavefoundry is the *wave*: a bounded delivery unit that contains one or more admitted change documents, a lifecycle state, review evidence, and a closure record.

### Why waves instead of issues or PRs?

Issues and pull requests are excellent for tracking *what changed*. They are weaker at tracking *why*, *what was reviewed*, *what was decided*, and *what was left for later*. In a world where agents do most of the implementation, the gap between "code was written" and "work was done correctly" is harder to close without structured evidence.

Waves address this by making the lifecycle explicit:

```
Plan feature       → Author a change document with rationale, requirements, ACs, and scope
Create wave        → Open a delivery unit and admit the change
Prepare wave       → Run a readiness check; the gate must pass before any code is touched
Implement wave     → Execute the admitted changes under coordinator oversight
Review wave        → Run required reviewer lanes; record structured verdicts with severity
Close wave         → Seal with operator signoff; distill journal lessons; promote durable memory
```

Each step has a gate. Gates are enforced by the server — not by agent instruction, not by convention, and not by hoping the agent remembers. `wf_close_wave` will not succeed without operator signoff. If the project declares `security-review` as a required lane, `wf_close_wave` will not succeed without a recorded `security-review` signoff. The agent cannot talk its way past these checks.

### The change document

The change document is the unit of planning. Before any code is touched, a change document must exist that answers:

- **Why** does this work exist? (Rationale)
- **What** exactly is being delivered? (Requirements and scope)
- **How will we know it's done?** (Acceptance criteria with explicit priority: required vs. important vs. nice-to-have)
- **What could go wrong?** (Risks and serialization points)

This is not bureaucracy for its own sake. When an agent returns to a wave after a context loss, or when a second agent takes over a first agent's work, the change document is the ground truth that prevents drift and scope creep. It is also the record that a future agent can consult to understand *why* a decision was made without reconstructing it from git history.

---

## The Feedback Harness

Böckeler identifies three dimensions of software harness quality: maintainability, architecture fitness, and behaviour. Wavefoundry implements all three.

### Maintainability: Computational Sensors

Projects declare computational sensors in `docs/workflow-config.json`:

```json
{
  "sensors": [
    { "name": "lint", "command": ["ruff", "check", "."], "dimension": "maintainability" },
    { "name": "type-check", "command": ["mypy", "src/"], "dimension": "maintainability" },
    { "name": "tests", "command": ["python3", "-m", "pytest"], "dimension": "behaviour" }
  ]
}
```

`wf_run_sensors` runs each sensor as a subprocess, captures exit code and output, and returns a structured result. Sensors must pass before inferential reviewer lanes are invoked. Because sensors are just shell commands, any project can wire in its existing quality gates without framework coupling.

### Architecture Fitness: Inferential Sensor Lane

The architecture reviewer (seed 214) reads `docs/architecture/` — current state, layering rules, domain map, cross-cutting concerns, and architecture decision records — before assessing a wave's changes. It checks for layer violations, boundary crossings, unwanted coupling, and decisions that conflict with recorded architecture choices.

The reviewer produces a structured verdict: `approved`, `approved-with-notes`, or `needs-revision`, with a `severity` rating and specific findings. If the architecture docs are absent, it notes this as a finding rather than failing — the framework works on projects that have no architecture docs yet, and it reports the gap.

### Behaviour: Security and Performance Lanes

The security reviewer (seed 213) checks path confinement, untrusted content handling, privilege escalation, and write-path tool exposure. The performance reviewer (seed 212) checks algorithmic complexity, hot-path regressions, and unbounded in-memory accumulation.

Both produce structured verdicts with severity. `wf_review_wave` aggregates severity across all recorded signoffs and emits a `high_severity_finding` advisory when `max_severity` is `critical` or `high` — so operators receive a triage signal before they begin reviewing the diff.

### Declaring Required Lanes

Projects declare which lanes are structurally required:

```json
{
  "required_review_lanes": ["security-review", "architecture-review"]
}
```

`wf_review_wave` reads this config and includes all declared lanes in `required_lanes` alongside the always-required operator lane. `wf_close_wave` blocks on any missing declared-lane signoff — the same enforcement pattern as operator signoff. A project that declares a lane is required cannot close a wave without it.

---

## The Semantic Index

Finding the right context is a prerequisite for correct agent behavior. Wavefoundry ships a local semantic search index built on `fastembed` and `BAAI/bge-base-en-v1.5`. The index covers:

- Project docs (waves, plans, architecture, contributing guides, specs)
- Framework seeds (all 214+ numbered prompt documents)
- Code (Python AST-aware chunking; tree-sitter for JS/TS/Go/Rust/Java/C/C++/C#/Kotlin/Bash)

The index runs entirely offline. It builds incrementally using file hashes — only changed files are re-embedded on update. Post-edit hooks trigger background incremental refreshes automatically when agents write to docs. `docs_search` falls back to lexical search when the semantic index is unavailable, so search always returns something useful even on first install.

`code_ask` combines semantic code search with an LLM synthesis pass: the agent retrieves relevant code chunks, then synthesizes a structured answer to a natural-language question about the codebase. This is the retrieval layer that makes agents effective on large codebases they haven't fully read.

---

## The MCP Server

Everything above is accessible through a local MCP server. The server runs as a stdio subprocess in the agent's host process (Claude Code, Cursor, Copilot, Junie, and others). It exposes 47 tools organized around four concerns:

**Wave lifecycle** — create and manage change documents and waves; prepare, review, and close; run sensors; check gates

**Docs and code search** — semantic search over docs and code; code navigation (definition, references, dependencies); code-aware question answering

**Audit and health** — combined wave/lint/index health snapshot; index build and status; docs gate (validate, garden); platform surface sync

**Framework navigation** — retrieve seeds by slug; get the full prompt catalog; map the framework structure

The server is local-first by design. It has no network dependencies. All state lives in ordinary files in the repository. Nothing is hidden in a database or sent to a remote service. Any operator can read the full state of any wave by opening the relevant Markdown file.

---

## How Wavefoundry Develops Itself

Wavefoundry uses the Wave Framework to build Wavefoundry. The self-hosting boundary is explicit:

- `.wavefoundry/framework/` contains the canonical framework source — seeds, scripts, and packaged index
- `docs/` contains Wavefoundry's own operating surface — waves, architecture docs, contributing guides, agent journals

Changes to the framework itself go through the full wave lifecycle. The architecture reviewer checks that changes don't violate Wavefoundry's own layering rules. The security reviewer checks that new MCP tools don't introduce path traversal or injection risks. Sensors verify that the test suite passes before reviewer lanes are invoked.

When a wave closes, `build_pack.py` packages the framework into a dated zip. Downstream projects adopt the new pack by dropping the zip at their repository root and running `Upgrade Wavefoundry`. The upgrade flow detects drift, reconciles prompt and hook surfaces, restarts MCP, and updates both index layers.

This self-hosting model means every wave that improves Wavefoundry is also a demonstration that the framework works as designed.

---

## Who This Is For

**Teams deploying AI coding agents** on non-trivial codebases who want more than convention-based process. If you find that agents do good work within a session but drift across sessions — starting over, forgetting decisions, skipping reviews — the Wave Framework gives agents a persistent operating surface that survives context loss.

**Individual developers** who use AI agents as implementation partners and want the agent's work to be auditable. The wave record is a permanent log of what was planned, what was implemented, what was reviewed, and what was decided. It makes it easy to return to a feature weeks later and understand what happened.

**Engineering teams** who want to extend AI agent deployment beyond greenfield features to maintenance, refactoring, and compliance work — domains where audit trails and review enforcement matter more than raw generation speed.

---

## Current State

Wavefoundry is in active development and self-hosted on its own framework.

**Shipped:**
- Full wave lifecycle MCP surface (47 tools)
- Local semantic index (docs + code) with incremental update and offline fallback
- Three-dimension feedback harness: computational sensors, security/performance/architecture inferential lanes, severity triage
- Required review lane enforcement at wf_review_wave and wf_close_wave
- Background index rebuild with non-blocking progress reporting
- Platform surface rendering for Claude Code, Cursor, Copilot, Junie
- Pack distribution and upgrade flow with MANIFEST-aware pruning

**In progress:**
- Code Insight Agent (code_ask) — semantic code search with LLM synthesis
- Prompt indexing quality improvements for kind="prompt" content
- Agent feedback harness coverage metrics and coherence checks in wf_audit

**Planned:**
- Behaviour test generation loop
- Hotfix bypass detection
- Harnessability assessment surfaced in wf_current_wave

Distribution: `wavefoundry-2026-05-06g.zip`
