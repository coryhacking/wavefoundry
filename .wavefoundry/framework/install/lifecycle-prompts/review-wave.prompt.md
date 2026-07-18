# Review Wave

Shortcut: **`Review wave`**

## Purpose

Evaluate the implemented wave against its acceptance criteria, public
contracts, failure modes, and current repository state.

## Review method

1. Review the actual diff and current tree, not the implementation summary.
2. Reproduce material claims through public or registered paths where safe.
3. Use an independent reference for changed behavior and state the common-mode
   limitations of that reference.
4. Classify every finding through the canonical action matrix: `do_now`,
   `maybe_later`, `dont_do_later`, or `not_issue`.
5. Record executable evidence and finding synthesis through the typed evidence
   tool when available.
6. A newly discovered finding may be recorded, started, repaired, and
   reverified in the same open repair cycle. Do not stop merely because an
   earlier review pass already ran.
7. Re-run only affected lanes for bounded repairs unless a load-bearing
   boundary objectively requires a full council.

## Approval

Approval requires current, lane-authorized evidence after every repair that
affects that lane. Implementer-authored verification can prove behavior but is
not independent delivery approval. Keep operator signoff pending until the
operator explicitly supplies it.

