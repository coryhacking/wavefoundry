# Pure Comparison Focused Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Verdict: approved for implementation of the bounded API repair, not delivery or closure.
Reviewed receipt: `review-policy-df8b0f463c2bae1ebca0`.
Containment plan fingerprint: `2ebc1ead7903eef9c87e9cd9456992f511974eea` (`git hash-object`).
Context: `pure-comparison-readiness-20260921`; a new worker that did not implement the repair. All perspectives below share this context and are correlated, not five independent confirmations. Earlier packet reviews remain the substantive review of unchanged extraction plans.

## Scope and executed evidence

Reviewed Requirements 1–3, scope and decision record of the updated containment plan, current primitive through MCP code_read, current renderer via exact AST extraction, and wave ordering/upgrade fallback requirements. Read the code, QA, architecture, security, release and docs-contract role instructions and seed 215 focused-reverification protocol. Budget: one bounded focused pass; targeted probes only, no suite reruns.

The original reproduction `/private/tmp/1ymzq_extra_resolution_probe.py` ran successfully: current renderer returns the missing inside target after two resolutions; naive resolving-helper adoption incorrectly raises escape refusal when the third resolution alone raises OSError.

Independent in-memory AST substitution changed only the current renderer's `is_relative_to` call to the proposed pure comparison. Six differential cases matched original return or exception class, message, cause and exact resolve-call count: missing-target success with an extra-resolution bomb; root OSError; candidate OSError; root RuntimeError; candidate RuntimeError; outside target. Both stat and lstat were patched to raise on any call. Four PureWindowsPath comparisons independently covered case aliases, different drives, same UNC share and different UNC shares. These are feasibility probes against the actual wrapper body, not claims that an unimplemented helper has shipped. No source files changed.

| Mechanism | Known-bad control | Observed |
| --- | --- | --- |
| Preserve original filesystem operations | Resolving-helper adoption adds a third resolve that fails | Wrong escape refusal reproduced; pure substitution retains success and exactly two resolves |
| Preserve failure boundary | Root/candidate errors injected at original resolve calls | Pure substitution matches original class, message and cause |
| Pure comparison | stat/lstat forbidden during proposed substitution | No hidden calls; six cases pass |

Future delivery must test the real installed helper and all adopting boundaries; Windows filesystem behavior and the full suite were not run here. Native PureWindowsPath comparison is not Windows filesystem evidence.

## Focused Council

This is focused repair replay after prior full readiness, with a full-risk containment lens. Sequential perspectives are logically separated but not context-isolated. No unrelated plan sweep was repeated.

Adversarial primer: strongest challenge is lexical containment accidentally receiving unresolved `..` or symlink spellings. Best alternative is leave every existing comparator local. Questions: (1) who resolves and enforces symlink policy, (2) can the comparison introduce new IO/error boundaries, (3) does the repair change retrieval sequencing or upgrade compatibility? Considered inversion (unresolved input), failure (extra IO), boundary (symlink policy), counterfactual (leave copies), and operational (identity/upgrade) stances.

- Code perspective. Pre-primer read: separating existing resolution from comparison can preserve exact caller behavior. Primer effect: confirmed; the explicit resolved absolute no-`..` precondition names the obligation. Answers: wrappers own resolution; comparison forbids IO; unchanged module registration keeps the staged identity sequence. No findings in my lane: the exact original wrapper probe demonstrates feasibility without exception translation changes.
- QA perspective. Pre-primer read: exact call counts and outcome parity are needed because final success alone misses extra IO. Primer effect: extended; delivery must also prohibit stat/lstat and cover native path semantics. Answers: per-site pins and differential tests prove caller policy; the new requirement detects re-resolution; R1 remains compared with R0. No findings in my lane: required tests now falsify the demonstrated contradiction. This is readiness coverage, not an AC-completion attestation.
- Architecture perspective. Pre-primer read: one stdlib owner with resolving and pure entry points avoids importing caller-specific error policy. Primer effect: confirmed; one final comparator shared by both entry points is the appropriate dependency direction. Answers: policy remains in wrappers; pure primitive adds no IO dependency; module membership and extraction order remain fixed. No findings in my lane: no new package, import cycle or exception-policy owner is proposed.
- Docs-contract perspective. Pre-primer read: resolving API and pure API need distinct caller obligations. Primer effect: confirmed; Requirement 1 names the precondition and Requirement 2 retains the review_policy symlink walk. Answers: callers explicitly own resolution/symlink checks; IO prohibition is explicit; receipt sequence unchanged. No findings in my lane for this repair. The already-known objective count residue is not a new contract choice and remains editorial cleanup.
- Security perspective. The local operator/repository actor assumptions remain unchanged; this is correctness under required AC-2, not an invented attacker escalation. No findings in my lane: resolved-input precondition, retained stronger clauses and unchanged indexer removal veto preserve the existing boundary. No escaping-path allowance or new authority is proposed. No exploit chain identified; regex/tool boundaries are untouched.
- Release perspective. No findings in my lane: the repair stays in the already-staged stdlib module, changes no packaging/version/tool contract, and does not alter the upgrade plan's pre-extract module-absence fallback or pinned memory seam. No package was built; unchanged extraction delivery still requires its planned tests.
- Rotating best-alternative perspective: keeping local comparisons is feasible but leaves the approved consolidation objective unmet; deferring the entire consolidation is broader scheduling cost with no additional correctness benefit now that no-IO comparison preserves original boundaries. No stronger alternative within the approved objective.

Synthesis considered arguments first by merit (IO preservation, input precondition, dependency direction, contract clarity, compatibility) then attached the perspectives above. All support this bounded repair. Shared support is one correlated signal. No challenge round or new blocking finding is warranted.

### Falsification Check

Working verdict: ready to implement the pure comparison repair. The strongest contrary argument is accidental future use on unresolved paths. It does not overturn readiness because the API precondition is explicit, every current adoption retains its original resolution and stronger checks, and the plan requires delivered per-site verification. It remains a delivery obligation, not evidence that implementation is already safe.
