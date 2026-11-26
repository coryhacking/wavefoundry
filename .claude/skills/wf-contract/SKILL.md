---
name: wf-contract
description: Write or update a behavior contract using the implementation and its tests. On request, inspect a selected boundary for drift without editing.
---

# Author behavior contract (Wavefoundry skill)

- For an explicit inspection or drift check, follow **Inspect contract drift on request** in `.wavefoundry/framework/seeds/230-author-spec.prompt.md`. Return the report in the response and stop before any authoring steps.
- For ordinary authoring, follow `docs/prompts/author-behavior-contract.prompt.md`, including the project's own authoring instructions.
