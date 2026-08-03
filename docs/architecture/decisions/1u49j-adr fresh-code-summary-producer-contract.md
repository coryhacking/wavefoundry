# 1u49j-adr: Fresh-code summary producer behind a pinned contract

Owner: Engineering
Status: accepted
Last verified: 2026-08-03

## Context

Any fix to how the upgrade itself runs, or reports, is absent on the upgrade that installs it,
because the in-process orchestrator is pre-extraction code. Three consecutive releases each
produced a false "the fix does not work" field report from exactly this window: extraction-behavior
debris (behavior class), a `runner_stale` response field returning null (server-resident class),
and a reconciliation summary reporting `[]` instead of real findings (reporting class, confirmed as
an unpinned cross-version call: the old orchestrator unpacked a 2-tuple from a scan module that had
grown a third channel, and a blanket exception swallow turned the arity error into silent empty
channels).

The remedies differ by defect class, and conflating them produces either overclaiming disclosures
(a fourth false field report) or unnecessary machinery.

## Decision

Defect classes in upgrade fixes are remedied three ways, one per class:

1. **Behavior class** (the fix changes what the upgrade DOES mid-run): a hook bridge, new-pack code
   executing inside the old parent via the upgrade hook surface. Field-proven by the
   `pre_index_update` publication-authorization bridge.
2. **Reporting class, sentinel-carried** (the fix changes what the upgrade REPORTS under the
   summary sentinel): the primary-phase summary is produced by a subprocess running the freshly
   extracted tree's `upgrade_wavefoundry.py --emit-summary --root <root>`, behind a pinned,
   permanent, old-calls-new contract. The parent captures the child's sentinel line and re-emits
   the JSON payload byte-verbatim through its own logger under its own sentinel prefix; exactly one
   sentinel is emitted per run (the delegated output and the in-process fallback are mutually
   exclusive by construction). Delegation failures degrade to the parent's own in-process summary
   carrying the `summary_source_degraded` marker, never fail the upgrade, and are never labeled as
   new-schema output. The payload carries a `summary_schema_version` token; a parent that does not
   recognize the token degrades rather than mis-parsing. The contract (flag name, argv shape,
   sentinel prefix value, envelope, token handling, pinned timeout) is pinned at ship time and
   locked by a permanent contract test that stands guard for the entire fielded population of old
   runners. The pins are a tripwire against silent drift, not an unpassable boundary: additive
   evolution needs no ceremony, and deliberate breaking evolution is supported by bumping the
   schema version token (old runners route to marked degradation for their transition run) and
   updating the contract test in the same change; only a silent rename or reshape is blocked.
3. **Server-resident class** (fields the MCP server computes in its own process: `runner_stale`,
   diagnostics composition, the summary bounder, restart suppression): only a host restart cures
   these, on every release. The restart disclosure is their remedy surface; no bridge or producer
   can reach them.

**Flat-scalar field rule for future summary fields:** the server's summary bounder is
passthrough-with-caps, not an allowlist. New sentinel-carried fields survive old servers only when
they respect the bounder's shape limits: flat scalars and lists. Lists are paged with explicit
truncation counts; oversized scalar values are dropped with a truncation marker; a nested dict is
treated as ONE scalar value and is dropped entirely once it exceeds the per-value character cap.
Future summary fields must therefore be flat scalars or lists of small items, and any field that
must never be dropped (such as the degradation marker) must be registered in the server's terminal
key set AND stay small enough to survive the unknown-scalar budget path on servers that predate the
registration.

## Consequences

**Positive:**

- Sentinel-carried reporting changes shipped after this decision take effect on the upgrade that
  installs them, instead of one upgrade later.
- The pg1a defect mechanism (in-process cross-version import at the emit site) is structurally
  closed: the delegated producer imports the scan module from the same extracted tree it belongs
  to, so no arity skew is possible on the delegated path.
- Silent schema drift is closed by the version token: an old parent facing an unrecognizable
  future envelope degrades with a marker instead of transporting misparsed output.

**Negative / tradeoffs:**

- The subprocess boundary adds a failure mode to every upgrade's summary; it is bounded by the
  four-class marked degradation (entry point absent, non-zero exit, malformed or absent sentinel,
  timeout) plus unrecognized-token degradation, each deterministically tested.
- One residual window remains by construction: the upgrade that installs the producer contract
  itself is still driven by a parent that predates it, so that one transition run reports an
  UNMARKED old-schema summary (a pre-contract runner has no marker code; the marker belongs to the
  new-runner degradation path). This is expected and disclosed, not a defect.
- Server-resident fields remain uncovered; the class boundary must be restated wherever the
  remedy is described, or disclosures overclaim.

**Constraints imposed:**

- The entry-point surface (`--emit-summary`, argv shape, sentinel prefix value, token handling,
  pinned timeout constant) never changes silently; the contract test exists to catch accidental
  drift. Deliberate versioned evolution is supported: additive changes need no ceremony, and a
  breaking reshape bumps the schema version (old parents degrade cleanly, with a marker) and
  updates the contract test in the same change.
- The producer must stay stdlib-only at module import time, runnable under the FROM version's tool
  venv, with no dependence on post-upgrade state.
- Parent-only facts (currently `skipped_scan_locations`) must be persisted to the upgrade lock
  before delegating; the lock is the contract's state carrier and the producer must tolerate
  old-schema locks.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Authoritative emission from an already-fresh spawned phase (`--update-index` / `--cleanup`), the topology whose first-time success the permissions-rendering prior art actually proves | The default upgrade flow runs no such phase (the primary emit is the old parent's final act), and last-sentinel-wins parsing means a second authoritative emitter collides with the parent's own emit |
| Per-fix hook bridges for reporting changes | Hook failure semantics abort the upgrade with exit 3, the opposite of the required degrade-with-marker posture; each bridge is a new transition surface needing its own fail-safety |
| In-process import of the new module by the old parent | This is the pg1a defect mechanism itself: an unpinned cross-version call whose skew gets swallowed |
| Bridging the parser side too | No mechanism exists to replace running-server code without a restart, and none is needed for sentinel-carried content: the bounder is passthrough-with-caps, field-proven by an old server surfacing a newer pack's summary fields |
| An unversioned output envelope | Silent schema drift is invisible to a launch-failure marker; only an explicit token lets an old parent distinguish "newer but compatible" from "unrecognizable" |
| Accept the one-cycle window and disclose | Three false field reports in two days is the measured cost of that posture |

## References

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` (`_emit_delegated_summary`,
  `_emit_primary_summary_via_delegate_or_fallback`, `_delegated_summary_payload`)
- `.wavefoundry/framework/scripts/server_impl.py` (`UPGRADE_SUMMARY_TERMINAL_KEYS`,
  `_bounded_upgrade_summary`, `_parse_upgrade_summary`)
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
  (`DelegatedSummaryContractTests`, the permanent contract test)
- `docs/architecture/cross-cutting-concerns.md` (pointer)
- `docs/architecture/layering-rules.md` (Boundary Invariants row)
- `docs/architecture/data-and-control-flow.md` (summary production process note)
