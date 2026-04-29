# 230 - Author Spec

Intent:

- Derive and write a durable behavior contract (spec) for a stable system boundary, API, or security-critical component — based on code evidence rather than design intent.

When to use:

- A key component has stable, observable behavior that downstream code, tests, or consumers depend on.
- A component is security-sensitive and its invariants must be explicitly stated for reviewers.
- A new instrumentation module is added and its attribute output contract needs to be declared.
- An existing component's behavior has been audited and verified in code.

Do NOT use for in-flight change work — that belongs in a consolidated change document (`docs/plans/`). Specs are for stable contracts that are already implemented and tested.

## Prerequisites

Before authoring a spec, verify:

1. The component's behavior is observable in source code (not just comments or design docs).
2. The component has unit or integration tests that define or confirm the behavior — cross-reference the test file.
3. No existing spec in `docs/specs/` already covers this component (check `docs/specs/` index or README).

## Tasks

### 1. Identify the component to spec

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

Cross-reference the test file (`*Test.java`, `*Spec.groovy`, etc.) to identify behaviors that tests enforce — those are especially stable and spec-worthy.

### 3. Determine spec type and placement

- Simple utility (validator, serializer, formatter) → single file, `docs/specs/<slug>.md`
- Multi-class boundary (e.g., a subsystem's public API) → single file describing the boundary, not each class
- Attribute key contract (span output) → `docs/specs/span-attribute-keys.md` or extend it
- Configuration contract → `docs/specs/configuration-properties.md` or extend it

Do not create one spec file per class unless the classes represent distinct, independently-consumed contracts.

### 4. Write the spec

Use this structure:

```markdown
# Spec: <Component Name>
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

**In scope:** what this spec covers.
**Out of scope:** what it explicitly does not cover (with cross-references to other specs).

## [Primary behavior sections]

Use tables for: constants/limits, configuration keys, attribute keys, allowed values.
Use numbered lists for: ordered resolution chains, precedence rules.
Use code blocks for: signatures, patterns, format strings.
Use plain prose for: semantics, security guarantees, threat mitigations.

## Change triggers

Bullet list of conditions under which this spec must be updated.
```

Spec quality bar:

- A reviewer unfamiliar with the codebase can confirm correctness by reading the spec, then reading the source.
- All numeric limits and string constants are copied exactly from source (not paraphrased).
- Security properties (what the component prevents, what it guarantees) are explicitly stated.
- Thread-safety and lifecycle guarantees are explicit.
- The spec says what is NOT in scope so readers know where else to look.

### 5. Update the specs index

After writing the spec, update `docs/specs/README.md` (or create it if absent) to add the new spec to the index table. Each row: title linked to the spec file, component name, one-line summary of coverage. See existing rows in `docs/specs/README.md` for the format.

### 6. Resolve missing-docs entries

If `docs/missing-docs.md` listed this component as a documentation gap, move the row from the appropriate priority table to the `## Resolved / closed` table with today's date and a short resolution note.

### 7. Update cross-references

Check whether any of these docs reference the newly-specced component without a link:

- `docs/SECURITY.md`
- `docs/architecture/threat-model.md`
- `docs/architecture/domain-map.md`
- `docs/architecture/data-and-control-flow.md`

Add links to the new spec where relevant. Do not rewrite those docs — just add the link.

## Required outputs

- `docs/specs/<slug>.md` — the spec file
- Updated `docs/specs/README.md` index
- Updated `docs/missing-docs.md` if the component was listed as a gap
- Cross-reference links added to architecture docs where appropriate

## Guardrails

- Do not spec behavior that is not yet implemented or not yet tested.
- Do not include internal implementation details that are not part of the observable contract (private helper method logic, internal algorithm choices).
- Do not include design rationale or "why we built it this way" — that belongs in a decision record (`docs/architecture/decisions/`).
- If a constant or limit is a magic number with no comments, note it as "unspecified rationale" rather than guessing.
- A spec file covers a **stable boundary**, not an in-progress feature. If the behavior is actively changing, write the change document first and spec after stabilization.
- Specs are not release notes. Do not list historical changes — only the current behavior.
