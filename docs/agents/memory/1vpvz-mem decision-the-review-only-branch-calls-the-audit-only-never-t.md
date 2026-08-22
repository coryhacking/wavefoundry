# Decision: The review-only branch calls the audit only, never the base…

Owner: Engineering
Status: superseded
Last verified: 2026-08-19

Memory ID: `1vpvz-mem decision-the-review-only-branch-calls-the-audit-only-never-t`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-19
Updated: 2026-08-19
Source exploration cost: 3090767
Source event: `decision-log:1vmt2-enh techdocs-audit-tool-and-review-only-branch:3197ef5d31325978`
Validation: rewrite
Validated by: agent
Action delta: When adding or reviewing a read-only TechDocs branch, call only the audit path; never call the baseline generator unless that writer gains an explicit, verified dry-run contract.
Validation rationale: The decision is durable and current, but the generated candidate has a truncated title, doubled punctuation, and names only the writer rather than the router and rendered public carrier. Seed 178 and the self-hosted prompt currently enforce the audit-only branch, while techdocs_baseline.py remains write-capable with no CLI dry-run.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1vo84-mem review-only-techdocs-branches-call-the-audit-never-the-basel`
## Summary

Decision (wave 1vqqi): The review-only branch calls the audit only, never the baseline tool.. Rationale: `techdocs_baseline.py` exposes no dry-run flag, so on a host without MCP the branch would have written the trio, the one thing it promises never to do. The audit already reports the trio state and the not-applicable verdict, so the call was redundant as well as unsafe..

## Evidence

- `1vmt2-enh techdocs-audit-tool-and-review-only-branch`
- `1vqqi`

## Targets

- `techdocs_baseline.py`
