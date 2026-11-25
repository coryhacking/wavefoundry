# Author behavior contract

Owner: Engineering
Status: active
Last verified: 2026-11-24

Shortcut: **Author behavior contract** or `/wf-contract`

Write or update a behavior contract using the implementation and its tests. Use seed 230 in `.wavefoundry/framework/seeds/230-author-spec.prompt.md` for the framework's authoring guidance.

1. Trace the observable behavior from its entry point. Read the supporting tests and name the assertions that establish the promise. Identify missing verification explicitly. Route a proposed behavior to the project's planning prompt (Plan spec under the default vocabulary). Leave it out of the standing contract until the implementation and its tests establish it.
2. Read `docs/architecture/contracts/index.md` and any maintained legacy `docs/specs/` index or README. Follow their links, including links to authoritative pages outside the collection. If existing pages claim competing authority, report the conflict for the owner to resolve.
3. Update the existing authoritative page in place. If the behavior has no contract, create a page in the project's established contract home (the default is `docs/architecture/contracts/`) and link it from the index. Respect any deferred migration. Cite the source entry point and the tests that verify each promise. Link to the maintained page wherever readers need it.
4. Check that the index link resolves and that the source and test references support the wording. Preserve the existing publication audience, navigation and exclusions. Label repository-only material and use a verified repository URL when the project provides one.

Report the contract path, the behavior it covers, its evidence and any verification gap.
