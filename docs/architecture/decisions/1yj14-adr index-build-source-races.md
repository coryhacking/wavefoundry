# 1yj14-adr — Index Build Source Races

Owner: Engineering
Status: accepted
Last verified: 2026-09-19

## Context

A real CE monitor can rewrite indexed wave projections while an index build holds
its build lock. Reading a held-lock predicate cannot close the check/write race;
POSIX process-owned record locks also do not report the caller as a competing owner.
A changed source invalidates prepared semantic and graph participants. Per-file
exclusion is not local: graph resolution and communities span file boundaries.

## Decision

Hold a shared flock-backed source-mutation guard across build source reads and
publication. Automatic CE projection and missing-map resource generation acquire it
without waiting and preserve pending work on contention. Build lock precedes source
guard; CE source guard precedes a nonblocking publication-lock attempt. Operator
commands remain unrestricted.

Retry a caught source drift once by preparing the entire coherent publication again,
with fresh staging. Restore a previous completed snapshot only after verified
precommit rollback on the original owned connection, unchanged external data_version,
no observed owned commit attempt and matching build ownership. Verify these conditions
under the recovery writer transaction. Keep the content generation and old timestamps,
assign a distinct reader attempt token, and rebind valid token-stamped lexical metadata.
Move independently committing scanner work before the recovery baseline and sidecar
cleanup into publication. Postcommit and uncertain publication states remain fail-closed.
An error during recovery COMMIT can leave either the fenced state or the verified
historical snapshot available; report the observed reader state and uncertainty
without retrying or claiming a fresh publication.

## Consequences and alternatives

A transient edit can recover automatically. Repeated edits stop after two preparations;
an intact historical snapshot can stay queryable without being represented as fresh.
Automatic telemetry projections may wait through both attempts. Separating the scanner
from embedding can reduce concurrency. External commits conservatively disqualify
recovery even if unrelated to mandatory index data.

Interlock alone would leave operator edits causing unavailable readers. Dependency-aware
partial exclusion would require a broader graph/community recomputation design. Restoring
only the old epoch marker after a committed replacement would mislabel new rows, so it
is rejected. This change adds no crash-recovery protocol and no whole-corpus backup.
