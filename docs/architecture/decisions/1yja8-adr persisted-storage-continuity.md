# 1yja8-adr — Persisted Storage Continuity

Owner: Engineering
Status: accepted
Last verified: 2026-09-19

## Context

After a macOS OS upgrade and reboot, this repository retained its resolved path
and inode but its device changed from 16777231 to 16777233. Exact persisted
device/inode equality made its intact index unreadable. The portable stat API
does not promise a durable volume identifier: inode uniqueness is relative to
the device/filesystem, as documented by [Python stat](https://docs.python.org/3/library/os.html#os.stat_result)
and [Linux inode](https://man7.org/linux/man-pages/man7/inode.7.html). This is an
observed failure, not a claim that every reboot renumbers devices or that all
filesystems on a platform return zero inode.

## Decision

This decision supersedes the original `1yhhs-bug` adopt-and-restamp proposal. The operator resolved the identity guarantee and restamping branches during readiness; the amended plan, rather than the original proposal, is the delivery contract for wave `1yja8`.

Use one pure `storage_identity` comparison for persisted-versus-live identities.
Callers retain resolved path and owned artifact-role checks. Compare nonzero
inodes when both are available; otherwise use the explicitly weaker path basis.
Reject malformed values. Device drift is reported separately and does not gate
continuity. Existing receipt versions, identity shapes and device values remain
historical evidence; neither bytes nor returned recovered mappings are restamped.
Normal owner-authorized transitions retain their writes and exact record bindings.

The helper is a stdlib sibling utility. Setup includes it in its source inventory;
incoming upgrade hooks can load it from the selected archive before extraction.
Retrieval comparisons bind repository identity in both generation modes and store
inode only in same-generation mode, preserving controlled rebuild comparisons.
Within-run race snapshots and persisted-to-persisted equality, tokens and hashes
remain strict. Identity maps do not gain capture paths because authorized cutover
renames a staged database to the live role.

## Consequences and alternatives

A replacement volume at the same path can reuse an inode; with an unavailable
inode, path alone cannot detect replacement. The operator explicitly accepted
this limitation for the scoped reboot fix. Independent schema, ownership,
package and continuation checks still apply, including destructive cleanup.
Persistent volume identification with legacy-record recovery could strengthen
identity but needs a broader design. Coordinated restamping would introduce
writes into observers and risk exact continuation bindings, so it is omitted.

Injected tests establish comparison logic, not native qualification on unavailable
platforms. A bounded source census guards known consumers; it cannot prove
arbitrary dataflow or discover every future spelling of an identity check.
