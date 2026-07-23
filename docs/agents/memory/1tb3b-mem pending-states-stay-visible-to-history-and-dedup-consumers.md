# pending-states-stay-visible-to-history-and-dedup-consumers

Owner: Engineering
Status: active
Last verified: 2026-07-22

Memory ID: `1tb3b-mem pending-states-stay-visible-to-history-and-dedup-consumers`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-07-22
Updated: 2026-07-22
Source event: `finding:1t8la:pending-archive-disposition-invisible`
Validation: promote
Validated by: agent
Action delta: Model crash-window intermediate states as labeled records visible to history and dedup consumers, never as invisible; hiding a pending state from statuses=None loads lets proposal/backfill regenerate the learning it represents.
Validation rationale: The generated summary echoed lane-clearance prose; the durable lesson is the labeled-pending-state principle. Verified against the repaired loader: the rename-window body surfaces as pending_archive_body to unfiltered/history consumers with its source_event visible (closing the propose/backfill regeneration window at server_impl.py disposition_sources), while DEFAULT_SURFACED_STATUSES isolation is structural.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1t8la's rename-window archive body was initially invisible to statuses=None loads, so memory_propose/backfill disposition dedup lost sight of its source_event during the window and could regenerate the learning as a fresh candidate. Repair: the loader labels the state pending_archive_body and includes it in unfiltered/history loads while default surfacing stays isolated (pending statuses are always archive-eligible, never default-surfaced). Crash-window intermediate states must be modeled as labeled and visible to history/dedup consumers, not hidden; invisibility converts a crash window into a duplication window.

## Evidence

- `pending-archive-disposition-invisible`
- `ev-pending-archive-disposition-invisible-6`
- `1t8la`

## Targets

- `.wavefoundry/framework/scripts/memory_records.py`
- `.wavefoundry/framework/scripts/server_impl.py`
