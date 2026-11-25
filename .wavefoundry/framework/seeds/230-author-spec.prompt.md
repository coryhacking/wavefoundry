# 230 - Author Behavior Contract

**Applicable when:** the project needs a new or updated standing behavior contract. Universal authoring lane.

Shortcut: **Author behavior contract** or `/wf-contract`. Both use `docs/prompts/author-behavior-contract.prompt.md`.

Intent:

- Derive and write a durable behavior contract for a stable system boundary, API, or security-critical component — based on code evidence rather than design intent.

When to use:

- A key component has stable, observable behavior that downstream code, tests, or consumers depend on.
- A component is security-sensitive and its invariants must be explicitly stated for reviewers.
- A new instrumentation module is added and its attribute output contract needs to be declared.
- An existing component's behavior has been audited and verified in code.

Plan proposed work in a change spec under the configured plans root until admission moves it into a wave. Behavior contracts describe stable boundaries that are already implemented and tested.

## Prerequisites

Before authoring a behavior contract, verify:

1. The component's behavior is observable in source code (not just comments or design docs).
2. The component has unit or integration tests that define or confirm the behavior — cross-reference the test file.
3. Locate the maintained contract before writing. Start at `docs/architecture/contracts/index.md`, any legacy `docs/specs/` index or README, and their linked sources. Exclude the old `docs/specs/changes/` change packages. If two pages claim authority, report the conflict and preserve both until ownership is resolved.

Identify any missing verification and leave those claims open. Contract authoring preserves the existing publication audience and configuration. A request to publish an excluded page needs its own owner decision.

## Tasks

### 1. Identify the component to document as a behavior contract

Determine the exact scope:

- What is the public surface? (methods, constants, attribute keys, configuration keys)
- What are the invariants? (preconditions, postconditions, guarantees that must never break)
- What are the security properties, if any?
- What downstream consumers depend on this behavior? (instrumentation modules, tests, span consumers)

### 2. Read the authoritative source

Read the production source file(s) end-to-end. Do not rely on comments alone — extract actual values:

- Numeric limits and constants (copy exact values, not approximations)
- Default values and sentinel handling (e.g., null, empty string, "none")
- Character sets and regex patterns (describe allowed input precisely)
- Thread safety model (what is synchronized, what is `ThreadLocal`, what is `volatile`)
- Caching model (cache sizes, eviction policy, cache invalidation triggers)
- Date/string formatting patterns (copy exact format strings)

Cross-reference the test file (`*Test.java`, `*Spec.groovy`, etc.) to identify behaviors that tests enforce — those are especially stable and behavior-contract-worthy.

### 3. Determine behavior contract type and placement

Use the established collection for new pages. The fresh-install default is `docs/architecture/contracts/`. Update an existing canonical page where its owner maintains it.

- Simple utility (validator, serializer, formatter) → single file, e.g. `docs/architecture/contracts/<slug>.md`
- Multi-class boundary (e.g., a subsystem's public API) → single file describing the boundary, not each class
- Attribute key contract (span output) → create or extend `span-attribute-keys.md` in the maintained collection
- Configuration contract → create or extend `configuration-properties.md` in the maintained collection

Do not create one behavior contract file per class unless the classes represent distinct, independently-consumed contracts.

### 4. Write the behavior contract

Use this structure:

```markdown
# Behavior Contract: <Component Name>
Owner: <team>
Status: current
Last verified: <YYYY-MM-DD>

**Owner:** <team>
**Status:** active
**Last verified:** <YYYY-MM-DD>
**Verification method:** Derived from `<source file path>` (and `<test file path>` if applicable)

## Purpose

One paragraph: what does this component do, why does it exist, who depends on it.

## Scope

**In scope:** what this behavior contract covers.
**Out of scope:** what it explicitly does not cover (with cross-references to other behavior contracts).

## [Primary behavior sections]

Use tables for: constants/limits, configuration keys, attribute keys, allowed values.
Use numbered lists for: ordered resolution chains, precedence rules.
Use code blocks for: signatures, patterns, format strings.
Use plain prose for: semantics, security guarantees, threat mitigations.

## Change triggers

Bullet list of conditions under which this behavior contract must be updated.
```

Behavior contract quality bar:

- A reviewer unfamiliar with the codebase can confirm correctness by reading the behavior contract, then reading the source.
- All numeric limits and string constants are copied exactly from source (not paraphrased).
- Security properties (what the component prevents, what it guarantees) are explicitly stated.
- Thread-safety and lifecycle guarantees are explicit.
- The behavior contract says what is NOT in scope so readers know where else to look.

### 5. Update the behavior contracts index

Update the maintained index with the component, a one-line coverage summary and a link to the authoritative page. An API reference or another maintained page outside the collection may own the complete promise. Where publication differs from repository access, preserve the intended audience, label repository-only references, and use a verified repository URL when the project provides one.

### 6. Resolve missing-docs entries

If `docs/missing-docs.md` listed this component as a documentation gap, move the row from the appropriate priority table to the `## Resolved / closed` table with today's date and a short resolution note. Keep that heading exactly as written (an ATX H2, `## Resolved / closed`, in the canonical `docs/missing-docs.md`): the retired-surface reconciliation scan's archive allowlist (`reconcile_scan.py`) treats table rows under it as historical record, so a resolution note that names a later-retired surface is not reported as a stale reference; prose under that heading, and rows and prose anywhere else in the file, are still scanned as live guidance.

### 7. Update cross-references

Check whether any of these docs reference the newly documented component without a link:

- `docs/SECURITY.md`
- `docs/architecture/threat-model.md`
- `docs/architecture/domain-map.md`
- `docs/architecture/data-and-control-flow.md`

Add links to the new behavior contract where relevant. Do not rewrite those docs — just add the link.

*Consider **Archetype review** on the behavior contract's interface contracts and acceptance section when the behavior contract is text-precision-heavy (boundary contracts, attribute key declarations, configuration schemas). Default seats: Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman — Spock and Marcus Aurelius are particularly load-bearing for behavior contract invariants and time-axis stability. Optional and operator-invoked. Seed: `236-archetype-council.prompt.md`.*

## Required outputs

- A verified behavior contract at its maintained location
- A link from the maintained index (fresh default `docs/architecture/contracts/index.md`)
- Updated `docs/missing-docs.md` if the component was listed as a gap
- Cross-reference links added to architecture docs where appropriate

## Guardrails

- Do not write a behavior contract for behavior that is not yet implemented or not yet tested.
- Do not include internal implementation details that are not part of the observable contract (private helper method logic, internal algorithm choices).
- Do not include design rationale or "why we built it this way" — that belongs in a decision record (`docs/architecture/decisions/`).
- If a constant or limit is a magic number with no comments, note it as "unspecified rationale" rather than guessing.
- A behavior contract file covers a **stable boundary**, not an in-progress feature. If the behavior is actively changing, write the spec first and write the behavior contract after stabilization.
- Behavior contracts are not release notes. Do not list historical changes — only the current behavior.
