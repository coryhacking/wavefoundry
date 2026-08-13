# Wavefoundry — Wave Framework

**Version:** see `framework/VERSION`

This directory contains the Wave Framework — a structured agent operating surface for software repositories. It gives AI coding agents a persistent, auditable way to plan, execute, review, and close work, and ships as a local MCP server that agents connect to directly.

---

## The Problem This Solves

AI coding agents do good work within a single session. Across sessions, they drift: they start over, forget decisions, skip reviews, and produce code that no one can audit after the fact.

The typical failure modes are quiet:
- A feature gets half-implemented because the second session didn't know what the first left unfinished.
- A security review gets skipped because the agent summarized what it *would* have checked rather than what it *did* check.
- Documentation diverges from the code it describes, with no one responsible for the gap.

These aren't model failures. They are **harness failures** — failures of the operating context in which the agent works.

The Wave Framework addresses this by giving agents a persistent operating surface: structured delivery units, enforced lifecycle gates, computational and inferential feedback sensors, and a local MCP server that agents interact with through tools rather than convention.

---

## Day-to-Day Framework Usage

```
┌─────────────────────────────────────────────────────────────────┐
│                    WAVE FRAMEWORK LIFECYCLE                      │
└─────────────────────────────────────────────────────────────────┘

  You have one or more changes to deliver
          │
          ▼
  ┌────────────────────┐
  │   Plan feature(s)  │  For each change: author a change doc with
  │                    │  WHY, WHAT, ACs, RISKS. Lives in docs/plans/.
  └─────────┬──────────┘
            │  Plan one change or bundle compatible changes together
            ▼
  ┌────────────────────┐
  │    Create wave     │  Open a delivery unit. Admit one or more
  │                    │  change docs. Wave gets an ID (e.g. 12ecs).
  │  Change A ──┐      │  Changes with compatible assumptions and
  │  Change B ──┤ wave │  interfaces can share a single wave.
  │  Change C ──┘      │
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐
  │    Prepare wave    │  Readiness gate runs automatically.
  │                    │  Verifies all changes are ready, deps are
  │                    │  stable, no blocking assumptions.
  └─────────┬──────────┘
            │  Gate passes? ──► No ──► Fix blockers, re-prepare
            ▼
  ┌────────────────────────────────────────────────────────────┐
  │                     Implement wave                          │
  │                                                             │
  │  Coordinator builds a dependency graph across changes:      │
  │                                                             │
  │    Change A (no deps)  ──────────────────────►  complete   │
  │         │                                                   │
  │         ▼ (unblocks)                                        │
  │    Change B (needs A)  ──────────────────────►  complete   │
  │                                                             │
  │    Change C (no deps)  ──────────────────────►  complete   │
  │    (runs in parallel with A when assumptions are stable)    │
  │                                                             │
  │  Each change follows the coordinator loop:                  │
  │    Thought → Action → Observe → (fix if needed) → repeat   │
  │                                                             │
  │  Run wf_run_sensors() after implementation to             │
  │  verify computational quality gates (lint, tests, etc.)     │
  └─────────┬──────────────────────────────────────────────────┘
            │
            ▼
  ┌────────────────────┐
  │    Review wave     │  Run required reviewer lanes across ALL
  │                    │  changes in the wave:
  │                    │  • Computational sensors
  │                    │  • Security reviewer
  │                    │  • Performance reviewer
  │                    │  • Architecture reviewer
  │                    │  • Operator signoff (always required)
  └─────────┬──────────┘
            │  All lanes recorded? ──► No ──► Address findings
            ▼
  ┌────────────────────┐
  │    Close wave      │  Server enforces: operator signoff + all
  │                    │  required lane signoffs must be recorded.
  │                    │  Disposition of every change is explicit:
  │                    │  complete / deferred / moved / retried.
  │                    │  Validate memory candidates. Promote memory.
  └─────────┬──────────┘
            │
            ▼
  Wave sealed. Permanent record of: what was planned, implemented,
  reviewed, decided, and why — for every change in the wave.
```

**Key principle:** gates are enforced by the server, not by agent instruction. `wf_close_wave` will not succeed without required signoffs recorded. The agent cannot talk its way past the checks.

---

## What's in This Directory

```
.wavefoundry/
  framework/
    seeds/        Numbered prompt documents (001–214+) — framework memory
    scripts/      Server, indexer, chunker, lint, gardener, packaging tools
    index/        Packaged semantic index (framework layer)
    README.md     Internal framework maintainer doc
    VERSION       Current distribution version
    MANIFEST      File manifest for upgrade pruning
  README.md       This file — project owner orientation
```

Each release ships exactly one semver package (`wavefoundry-MAJOR.MINOR.PATCH.<build>.zip`). Fresh
installs and protocol-2 upgrades extract that package through `Upgrade Wavefoundry`; a protocol-1 /
1.14 installation moving to 1.15 executes the same package directly after explicit host shutdown.

---

## Core Concepts

### Waves

A *wave* is the delivery unit. Work is never planned directly into production — it is first authored as a change document, admitted into a wave, and then implemented through the wave lifecycle. This keeps scope explicit, makes handoffs durable, and gives every closed wave a permanent record.

```
Plan feature(s) → Create wave → Add changes → Prepare wave → Implement → Review → Close wave
```

**A wave can contain one change or many.** A single bug fix is a wave. A coordinated feature spanning data model, API, and UI is also a wave — the three changes are admitted together, their dependencies are declared, and the coordinator sequences their execution. What makes them a wave is that they share compatible assumptions and can be reviewed and closed as a unit.

- A change may appear in more than one wave — if work is incomplete at closure, the same Change ID carries forward into the next wave
- A wave closes even when some changes remain incomplete, as long as their disposition is explicit (deferred, moved, retried)
- Only one wave should normally be active per Change ID at a time

Wave state and all review evidence live in ordinary Markdown files under `docs/waves/`. Nothing is hidden in a database. You can read every wave record in a text editor.

### Seeds

Seeds are numbered prompt documents (001–214+) that define how agents should behave at each lifecycle step. They live in `framework/seeds/`. When you type a shortcut like `Plan feature` or `Prepare wave`, the agent retrieves the relevant seed and follows it.

Seeds are the framework's long-term memory — they encode operational lessons in a form agents can retrieve and apply across sessions.

### The MCP Server

The local MCP server (`framework/scripts/server.py`) exposes 47 tools:

| Surface | Tools |
|---------|-------|
| Wave lifecycle | `wf_current_wave`, `wf_prepare_wave`, `wave_review`, `wf_close_wave`, `wf_run_sensors`, creation/mutation surface |
| Docs and code search | `docs_search`, `code_search`, `code_read`, `code_definition`, `code_references`, `code_ask` |
| Audit and health | `wf_audit`, `wf_validate_docs`, `wf_garden_docs`, `index_health`, `index_build` |
| Framework navigation | `seed_get`, `wf_help`, `wf_map`, `wf_get_prompt` |

The server runs locally over stdio — no hosted service, no network dependency, no data leaving the machine.

### The Feedback Harness

Beyond process gates, the framework ships a three-dimension feedback harness:

**Maintainability — Computational sensors**
Project-registered shell commands run via `wf_run_sensors`. Pass/fail determined by exit code. Any existing quality gate (lint, tests, type-check) can be wired in without framework coupling.

```json
{
  "sensors": [
    { "name": "lint", "command": ["ruff", "check", "."] },
    { "name": "tests", "command": ["pytest"] }
  ]
}
```

**Architecture — Inferential sensor lane**
The architecture reviewer (seed 214) reads your `docs/architecture/` docs and assesses layer violations, boundary crossings, and decision conflicts. Produces a structured verdict with severity.

**Behaviour — Security and performance lanes**
The security reviewer (seed 213) checks path confinement, untrusted content handling, and privilege escalation. The performance reviewer (seed 212) checks algorithmic complexity, hot-path regressions, and unbounded in-memory accumulation. Both produce structured verdicts with `critical` / `high` / `medium` / `low` / `none` severity.

Declare which lanes are required in `docs/workflow-config.json`:

```json
{
  "required_review_lanes": ["security-review", "architecture-review"]
}
```

A declared lane missing its signoff blocks `wf_close_wave` the same way a missing operator signoff does.

### The Semantic Index

The framework ships a local search index with three layers: semantic embeddings over your project docs and code (independent layer selectors currently share Snowflake Arctic Embed S at FP16 GPU / INT8 CPU batch 32, plus the local MiniLM L6 reranker at batch 40), a BM25 full-text layer for exact identifiers, error strings, and rare tokens, and a structural code graph for call, impact, and dependency queries. It runs entirely offline and updates incrementally. `docs_search` falls back to lexical search when the index is unavailable.

`code_ask` is mechanical retrieval routing, not LLM synthesis — it fuses semantic and lexical candidates, reranks them locally, and returns ranked citations from which the calling agent synthesizes its answer to a natural-language question about the codebase.

### The Coordinator Loop

When a wave contains multiple changes, the coordinator — not each individual implementer — owns execution order, dependency sequencing, and exceptional named checkpoints. The coordinator follows an explicit ReAct-derived loop: **Thought → Action → Observe**, recorded in the wave's Progress Log. Routine inferential review runs later through the distinct `Review wave` phase.

**Before the first edit**, the coordinator produces a wave plan: an ordered sequence of lane invocations with explicit inputs per change, and which changes can run in parallel vs. sequentially.

**Dependency graph execution**

Changes within a wave declare dependencies on each other. The coordinator builds a dependency graph and respects it:

```
  Change A  ──────────────────► complete
      │
      └─► unblocks Change B  ──► complete
  
  Change C  (no deps on A/B)  ──► runs in parallel with A
```

- Independent changes run concurrently when their assumptions are stable and confirmed
- A change does not begin until everything it depends on is complete
- If a dependency is invalidated mid-wave, the coordinator pauses, re-evaluates, and records a `Reflect:` entry before continuing

**Three loop levels**

When a reviewer or sensor finds a problem, the coordinator chooses the right response level based on what the finding *is*, not just its severity:

| Level | Trigger | Response |
|-------|---------|----------|
| **L1 — Micro** | Fix is local to the implementer, no reviewer needed | Fix inline; no log entry required |
| **L2 — Focused independent checkpoint** | Implementation exposes a risky boundary that is not safely implementer-internal | Request one named reviewer, fix, and re-check that boundary; no re-Prepare needed |
| **L3 — Wave lifecycle** | Finding invalidates a frozen assumption or changes scope | Stop. Record `Reflect:`. Re-Prepare or re-plan. |

**CRITIC — finding classification before looping**

After an exceptional named checkpoint or the distinct delivery review, findings are evaluated against the admitted change's acceptance criteria — not just "reviewer clean." A change is not done until its ACs are met. "Reviewer approved" alone is not the exit condition.

**Carry-forward at closure**

Not all changes need to finish for a wave to close. At closure, the coordinator records the explicit disposition of every change:

| Status | Meaning |
|--------|---------|
| `complete` | Change delivered and verified in this wave |
| `deferred` | Work deprioritized; same Change ID carries to a future wave |
| `moved` | Work reassigned to a different wave or scope |
| `retried` | Work failed; same Change ID retried with revised approach |

This disposition record is what lets future sessions continue without reconstructing history.

---

## Getting Started

### Installing

For a fresh install, place the feature zip (`wavefoundry-MAJOR.MINOR.PATCH.<build>.zip`) in the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`, and run:

```
Upgrade Wavefoundry
```

The agent adopts the zip, bootstraps the operating surface, and refreshes the local framework files. After upgrade, restart MCP and run:

```
index_build(content="docs", mode="update")
```

### Upgrading

```
Upgrade Wavefoundry
```

The agent detects drift, reconciles prompts and hook surfaces, runs the docs gate, restarts MCP, and updates the index.

When a 1.14 / protocol-1 installation is moving to 1.15, use the same matching
`wavefoundry-<version>.zip` package. Fully stop the dashboard and every attached MCP/agent host;
the agent then executes the exact returned argv once through its ordinary non-MCP shell. The
operator does not copy or type that command. After it returns, restart every attached host and
follow the structured reconciliation/cleanup result. No special upgrade package, separate bridge
asset, or second copied command is required.

### Starting a session

```
wf_current_wave()        ← See active waves and current state
wf_audit()          ← Combined wave + lint + index health snapshot
wf_help()           ← Full shortcut phrase table
```

### Opening a wave

```
Plan feature          ← Author a change doc and plan the work
Create wave           ← Open a delivery unit and admit the change
Prepare wave          ← Run readiness gate before touching code
Implement wave        ← Execute admitted changes
Review wave           ← Run required reviewer lanes
Close wave            ← Seal with operator signoff
```

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `docs/workflow-config.json` | Lifecycle epoch, wave settings, review policies, sensor config |
| `docs/repo-profile.json` | Project archetypes, traits, factor-review applicability |
| `AGENTS.md` | Agent entry map, shortcuts, stage gate, git commits policy |

---

## Design Principles

**Local-first.** The server runs as a subprocess in the agent's host. No accounts, no hosted service, no data leaving the machine.

**File-based state.** All wave state, change records, review evidence, and configuration live in ordinary Markdown and JSON files. Nothing is hidden in a database. Agents and humans can read, edit, and version-control everything.

**Structural enforcement over convention.** Gates are enforced by the server, not by agent instruction. The harness dimensions are declared in config and enforced the same way — a declared lane that is missing its signoff blocks closure whether or not the agent remembers to check.

**Feedforward and feedback together.** Seeds (feedforward) guide agents through correct behavior. Sensors and reviewers (feedback) catch what the feedforward missed. Both are necessary; neither alone is sufficient.

---

## Non-Goals

- Not specific to any one language or tech stack
- Not a hosted service — no network dependency for install, upgrade, validation, indexing, or packaging
- Not a replacement for human review — the harness directs attention, it does not eliminate judgment
- Not a code generator — the framework structures how agents work, not what they produce
