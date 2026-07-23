# Repaired defect pending-archive-disposition-invisible

Owner: Engineering
Status: superseded
Last verified: 2026-07-22

Memory ID: `1taym-mem repaired-defect-pending-archive-disposition-invisible`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-22
Updated: 2026-07-22
Source exploration cost: 408549
Source event: `finding:1t8la:pending-archive-disposition-invisible`
Validation: rewrite
Validated by: agent
Action delta: Model crash-window intermediate states as labeled records visible to history and dedup consumers, never as invisible; hiding a pending state from statuses=None loads lets proposal/backfill regenerate the learning it represents.
Validation rationale: The generated summary echoed lane-clearance prose; the durable lesson is the labeled-pending-state principle. Verified against the repaired loader: the rename-window body surfaces as pending_archive_body to unfiltered/history consumers with its source_event visible (closing the propose/backfill regeneration window at server_impl.py disposition_sources), while DEFAULT_SURFACED_STATUSES isolation is structural.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1tb3b-mem pending-states-stay-visible-to-history-and-dedup-consumers`
## Summary

Real defect fixed in wave 1t8la: Code lane independently reassessed and cleared after repair; chain terminal.

## Evidence

- `pending-archive-disposition-invisible`
- `ev-pending-archive-disposition-invisible-6`
- `1t8la`

## Targets

- `memory_records.py`
- `server_impl.py`
