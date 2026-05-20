# 209 — Agent Harness Core

Owner: Engineering
Status: active
Last verified: 2026-05-19

## Purpose

Define the shared contracts that all harness participants use: evidence grounding, briefing packet format, finding record schema, reachability labels, and coordination behaviors.

## Evidence Grounding

| Source | Weight | Rule |
|--------|--------|------|
| Repository evidence (code, docs, configs, wave records) | Highest | Prefer over memory, assumptions, or inferred behavior |
| Stricter project rule in `docs/` | Wins over framework default | When a project-specific rule contradicts a generic framework default, the project rule applies in that context |
| Missing docs | Gap to record | Do not assume absence means absence of constraint; record the gap as a finding |

Separate facts (evidenced in the repository), inferences (derived from patterns), and unknowns (no evidence found) in all outputs.

## Briefing Packet

A briefing packet is the structured context shared with every council seat or review lane before it runs in isolation.

**Required fields:**

| Field | Description |
|-------|-------------|
| `wave_id` | Active wave identifier |
| `phase` | `readiness` or `delivery` |
| `change_ids` | List of admitted change IDs in scope |
| `trust_boundaries_touched` | Which trust or security boundaries this wave crosses |
| `files_in_scope` | File paths or glob patterns directly modified by the wave |

**Optional fields:**

| Field | Description |
|-------|-------------|
| `architecture_refs` | Relevant architecture docs consulted |
| `prior_artifacts` | Prior review outputs, journals, or prior-wave findings that are still relevant |
| `explicit_non_goals` | What is intentionally out of scope |
| `recommended_model_tier` | Suggested model capability tier for complex seats |

The briefing packet is assembled once per phase (readiness or delivery) before any seat runs. Seats must not expand the briefing packet; they may flag missing evidence as a gap.

## Finding Record Schema

Every finding produced by any harness participant must use this schema:

| Field | Required | Description |
|-------|----------|-------------|
| `finding_id` | Yes | Stable identifier, e.g. `SEC-001`, `CODE-003` |
| `file` | Yes | Repo-relative path |
| `lines` | Yes | Line range, e.g. `42-48` |
| `class` | Yes | Vulnerability or defect class (e.g. `path-traversal`, `missing-branch`, `complexity-regression`) |
| `summary` | Yes | One-line description of the finding |
| `reachability` | Yes | One of the reachability labels below |
| `confidence` | Yes | `high`, `medium`, or `low` — reviewer confidence in the finding |
| `severity` | Yes | `critical`, `high`, `medium`, `low`, or `none` |
| `recommended_fix` | Yes | What should be done to resolve the finding |
| `components` | No | For exploit-chain findings: list of contributing component finding IDs |

## Reachability Labels

Use exactly these labels (no others):

| Label | Meaning |
|-------|---------|
| `reachable-from-caller-input` | An attacker or untrusted caller can reach this code through normal API or tool inputs |
| `reachable-from-untrusted-content` | The vulnerable behavior is triggered by content read from an untrusted source (e.g. user files, repository content, config) |
| `not-externally-reachable` | The code path is only reachable from internal or trusted caller contexts |

## Harness Behaviors

**Narrow scope:** Each participant reviews only the files and boundaries in scope per the briefing packet. Do not expand scope to adjacent files without recording a `Deviation:` and returning it to the coordinator.

**No self-approval:** Code or changes being reviewed may not be signed off by the author. When the same agent that implemented a change also runs the reviewer lane, record the conflict and escalate.

**Split questions:** Defect questions (is this code correct?) and reachability questions (can an attacker reach this?) are separate. Do not conflate correctness and reachability in a single finding.

**Parallel tasks with merge and deduplicate:** When multiple lanes run concurrently and produce overlapping findings, the coordinator deduplicates by `finding_id` before recording the merged Observe. Two findings with different IDs that describe the same defect must be merged by the coordinator before the next Thought.

**Gapfill pointer:** After all lanes complete, if any evidence referenced in the briefing packet was absent or incomplete, the coordinator records a `Gapfill:` entry in Progress Log noting what was missing and where it should be added before the next wave.

## Project Harness Extensions

<!-- Fill from target repository evidence during upgrade render. Never add product-specific content to this seed body. -->
