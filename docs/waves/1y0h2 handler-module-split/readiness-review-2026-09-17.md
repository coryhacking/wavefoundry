# Handler Split Readiness Clarification Review

Owner: Engineering
Status: active
Last verified: 2026-09-17

Phase: readiness. Context: `snapshot-crosswave-readiness-20260917-independent`. Scope: operator-authorized alignment with the introspection registry, including change and wave mirrors. No implementation changes.

The standard red-team primer applied adversarial, constructive and simplicity stances. Its questions were whether response-module extraction preserves the existing registration and argument boundaries, and whether invocation-time delegation preserves reload ownership. The configured independent security-reviewer seat approved. A separate docs-contract seat also approved cross-wave consistency after mirror repairs. Agreement unanimous; no remaining bounded findings and no challenge round needed.

The strongest challenge was a second registration source: the old plan combined hand-authored `TOOLS` lists and census retirement with a predecessor that derives specs from existing FastMCP registration. The adopted alternative keeps decorated closures in the composition root, moves response functions and family-private helpers only, and resolves sibling responses at invocation time. It is better because the existing registration, annotations, extra-argument checks, AST census and runtime introspection remain authoritative without a second tool inventory.

The final Requirement 2 expressly prohibits captured module/callable references across reload and any `TOOLS` list. Requirements 3–4 preserve lazy shared-helper access and require purge-list entries; AC-4/5 require actual refreshed handler behavior and full-surface parity. The wave objective, scope, tasks, architecture guidance and census decision now agree. The docs-contract reviewer rejected the intermediate stale wave objective still promising `TOOLS` lists; a focused reread confirmed that known-bad contradiction was removed.

Existing source and readiness-safe registration evidence support the boundary: actual stubbed full-runner registration includes the runner survivor, while the deliberately incomplete registration omits it; a subsequent actual refresh-path spy confirms the survivor remains present before implementation re-registration. These probes are recorded in the sibling snapshot and registry readiness reports. No new handler implementation was exercised. The security seat inspected the amended documents and found no new less-trusted actor, alternate registration authority or changed path-enforcement responsibility.

Readiness approved for the bounded amended plan. All five evidence-integrity checks are true for the review itself, with the rejected incompatible composition and stale-objective controls plus actual registration-boundary evidence. This does not attest to unimplemented extraction correctness. Path confinement, regex behavior, module reload, retrieval, packaging and required delivery reviews remain future verification obligations. No production files, server reload or external requests were changed or executed by this review. The coordinator owns typed readiness and lifecycle state.
