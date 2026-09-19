# Decision: Config-declared typed gates; no imported policy code

Owner: Engineering
Status: rejected
Last verified: 2026-09-18

Memory ID: `1ybkm-mem decision-config-declared-typed-gates-no-imported-policy-code`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-18
Updated: 2026-09-18
Source exploration cost: 426027
Source event: `decision-log:1y0bd-enh config-declared-phase-gates:ccb993f8ea4b2012`
Validation: reject
Validated by: agent
Action delta: No durable action is lost by rejecting: the decision is canonical in the new decision record `1yb53-adr config-declared-phase-gates.md`, which carries the same rationale plus the consequences an implementer needs, including the prepare-versus-close trust asymmetry this wave's delivery review proved by probe.
Validation rationale: The underlying decision is sound, but the generated candidate is anchored on `extensions/*_policy.py`, the path of the REJECTED alternative. That path does not exist and never will, so the record cannot be checked against the tree and a rewrite is refused for exactly that reason. Rejecting rather than retaining avoids leaving an unverifiable record in the corpus. Nothing is lost: the decision is canonical in the ADR this wave authored, and the generalizable rule about extracted modules is captured in the sibling candidate promoted from this same wave.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Decision (wave 1y0h0): Config-declared typed gates; no imported policy code. Rationale: Operator selection on 2026-09-14. Auto-importing repository Python at MCP startup would run untrusted code in every host that starts the server on project open; the RFC's precedent is wrong because upgrade hooks load from the pack, not the repository. Config is committed, reviewed, and already the project's extension idiom.

## Evidence

- `1y0bd-enh config-declared-phase-gates`
- `1y0h0`

## Targets

- `extensions/*_policy.py`
