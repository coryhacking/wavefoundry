Owner: Engineering
Status: active
Last verified: 2026-11-24

## Final architecture reverification

ARCH-D1 is repaired. The domain-map rule and both data-flow statements now allow only verified upgrade replacement. Ordinary render, local edits and missing-only TechDocs remain protected. Five integrated-tree boundary tests passed. The former blanket prohibitions are present in the known-bad HEAD documents and absent in the live texts.

The final q5u0/q5u1 route artifacts give each of the six hops 18 passing checks and one terminal cleanup summary. Both direct archive primaries and the installed successor removed their locks. Both MCP primaries and the legacy installed primary retained theirs until explicit cleanup. These results establish delivery of the specified guidance, routes, signals and bounded automatic cleanup for the exercised CPU-pinned macOS fixture.

# Architecture delivery review

Withhold architecture approval for ARCH-D1. The implementation demonstrates a supported whole-file write that the normative dependency rule forbids. This defect is independent of CR-D1. The unchanged input fingerprint matched the review packet.

## Proposed correction

In `docs/architecture/domain-map.md`, replace the missing-only/never-regenerated clause in dependency rule 2 with the following text. Keep the surrounding clauses about managed regions and role migration.

> Ordinary rendering materializes absent lifecycle prompts and the plan template. During an upgrade, the extracted Phase 1 renderer may replace an existing registered lifecycle prompt or plan template when the pre-extraction comparison proves it matched the previous template and the renderer verifies the saved digest at the contained destination. It preserves the local verification date, regenerates the owned regions, and records the replacement in the upgrade checkpoint. Edited, unknown and linked destinations remain project-owned. The separate TechDocs command creates only absent members of its three-file baseline.

In `docs/architecture/data-and-control-flow.md` Path 3 “State written,” replace “never rewritten afterwards” with “existing registered lifecycle prompts and the plan template are eligible for the comparison-proven upgrade replacement described in Upgrade lifecycle baseline drift.” Recast telemetry step 10’s final sentence as “Existing project-authored prose is preserved. Upgrade may replace a registered copy that still matches the previous shipped baseline, as described in Upgrade lifecycle baseline drift.” The checkpoint belongs to the upgrade process. This grants no full-file rewrite to normal setup, surface sync or TechDocs.

## Process boundaries and controls

Seven tests passed across arch-controls.log and arch-exclusions.log, including an actual Phase 1 subprocess reading the historical 1.51 templates, no-checkpoint byte preservation, six proven replacements, unchanged repeat mtimes, late edits, links and all TechDocs state-matrix cases. The CLI cleanup test exercises an extracted child and checks a single terminal result. Opt-out and pending-continuation controls retained their intervention. The direct archive test reached its stub continuation. Commands and test identifiers are in architecture-reviewer.json and the logs.

I reran the same public-renderer fault injection on the frozen and staged repair trees (`PYTHONPATH=.:tests ~/.wavefoundry/venv/bin/python -B <absolute delivery/code-retry.py>` from each scripts directory). On the original, retry reported success with a missing policy marker and stale finding. The staged repair restored the marker and recorded replacement. Its two additional retry tests passed, including checkpoint denial before publication and a later local date edit. Persisting the exact intended byte digest before publication makes the two-file sequence recoverable without a new database or transaction owner. These checks simulate a refused checkpoint write. An OS kill, native Windows and adversarial concurrent writes were outside the seat budget.

## Council seat

The strongest manual alternative is to keep the checkpoint after publication, present its verified replacement/merge distinctions, and require a separate explicit cleanup. That is still an appropriate supported path when a stop or external handoff is pending. Applied universally, it reinstates the second command on clean CLI upgrades. Requiring operators to merge every prompt would also leave untouched repositories with retired tool names until someone acted. The implementation's conditional action preserves the original ownership boundary when a match cannot be established.

The original public-package rehearsals substantiate kept memory bytes, route migration, and the 1.53.0 inventories with the CPU provider pinned. They required manual cleanup on the successor CLI hop. At review time the confirmed rehearsal directories contained only baseline preparation logs. The focused child and checkpoint controls establish the repaired decision. Council should reserve final packaged successor credit until the new archive and installed-CLI transcripts show one cleanup-complete sentinel each and a removed lock, and the MCP transcript shows phase retention. Whether maintainers follow a delivered keep recommendation remains a field outcome.
