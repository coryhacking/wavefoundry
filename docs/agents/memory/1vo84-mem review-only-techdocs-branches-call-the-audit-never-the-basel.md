# Review-only TechDocs branches call the audit, never the baseline writer

Owner: Engineering
Status: active
Last verified: 2026-08-19

Memory ID: `1vo84-mem review-only-techdocs-branches-call-the-audit-never-the-basel`
Kind: `decision`
Confidence: 0.95
Created: 2026-08-19
Updated: 2026-08-19
Source exploration cost: 3090767
Source event: `decision-log:1vmt2-enh techdocs-audit-tool-and-review-only-branch:3197ef5d31325978`
Validation: promote
Validated by: agent
Action delta: When adding or reviewing a read-only TechDocs branch, call only the audit path; never call the baseline generator unless that writer gains an explicit, verified dry-run contract.
Validation rationale: The decision is durable and current, but the generated candidate has a truncated title, doubled punctuation, and names only the writer rather than the router and rendered public carrier. Seed 178 and the self-hosted prompt currently enforce the audit-only branch, while techdocs_baseline.py remains write-capable with no CLI dry-run.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

A review-only TechDocs workflow must call `wf_techdocs_audit` (or `wf techdocs-audit`) only. Do not call `wf_techdocs_baseline` or its CLI fallback: the baseline path is a writer and its CLI has no dry-run contract. The audit already reports trio ownership and not-applicable state, so invoking the writer is both unsafe and redundant.

## Evidence

- `1vqqi decision log 2026-08-18`
- `1vmt2 AC-7`
- `TechdocsCarrierLiteralPinTests.test_seed_178_carries_the_workflow_boundary_and_checklist`

## Targets

- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `docs/prompts/refresh-techdocs.prompt.md`
- `.wavefoundry/framework/scripts/techdocs_baseline.py`
