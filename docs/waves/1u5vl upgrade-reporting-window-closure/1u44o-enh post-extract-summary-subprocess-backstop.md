# Build Upgrade Summaries and Post-Extract Reporting on Freshly Extracted Code

Change ID: `1u44o-enh post-extract-summary-subprocess-backstop`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-01
Wave: `1u5vl upgrade-reporting-window-closure`

## Rationale

Three consecutive releases have confirmed one structural pattern: any fix to how the upgrade
itself runs, or reports, is absent on the upgrade that installs it, because the in-process
orchestrator is pre-extraction code. Field-confirmed instances (operator-reported, 2026-07-31 and
2026-08-01):

| Release | Shipped fix | Failed on its own installing upgrade | Covered by this remedy? |
| ------- | ----------- | ------------------------------------ | ----------------------- |
| pfxp | extraction allowlist (1u0cc) | installer debris landed anyway | No (behavior class; hook bridge) |
| pg1a | runner_stale restart signal (1u2ay) | returned null, not true | **No (server-resident; restart only)** |
| pg1a | three-channel reconciliation summary | reported [] instead of 34 findings | **Yes (sentinel-carried)** |

The third instance was initially suspected to be a standing regression. The pg1a-to-pg5l field run
retracted that: the pg5l upgrade, whose summary was still built by the pg1a-era orchestrator,
reported `reconciliation_total: 34, reconciliation_returned: 34` with a direct-scan cross-check of
`[34, 0, 0]`. The mechanism is structurally confirmed at the API level (code lane, 2026-08-01):
the pfxp-era orchestrator unpacked a 2-tuple from `reconcile_scan.scan_repo_channels` while the
pg1a module returns three channels; the lazy post-extraction import raised `ValueError` on unpack,
and the blanket `except Exception` at the call site swallowed it into empty channels. The blind
spot, not a bug, and precisely an UNPINNED cross-version call.

**The covered class must be stated honestly (red-team, 2026-08-01).** This remedy covers
**sentinel-carried summary fields**: content the upgrade runner emits under the summary sentinel
and the server parses into `wf_upgrade` responses. It does NOT cover server-resident response
assembly: fields the MCP server computes in its own process (`runner_stale` from launch-vs-disk
identity, diagnostics composition, the summary bounder, restart suppression). Those remain old
code until the host restarts, on every release, and only the restart disclosure covers them. The
`runner_stale` row above is motivation for naming the pattern, not a defect this change fixes.

Two remedies are field-proven, one per defect class:

- **Behavior class** (the fix changes what the upgrade DOES mid-run): wave 1u44n's
  `pre_index_update` hook bridge (new-pack code executing inside the old parent) made the
  publication-authorization fix effective on the installing upgrade; the pg1a-initiated pg5l run
  published Phase 4a cleanly.
- **Reporting class, sentinel-carried** (the fix changes what the upgrade REPORTS): run the
  producer on freshly extracted code. The permissions rendering backstop is the prior art that
  worked first time (42 managed rules on the installing upgrade), with one topology caveat: it is
  CALLED FROM phases that already run in a fresh post-extract process (`--update-index`,
  lock-gated `--cleanup`), and it does not capture child output (the parent re-derives state from
  disk). The primary-phase summary emit has no such fresh-process phase to ride: it is the old
  parent's final act, after the last hook dispatch, in the pre-extraction process. What is
  field-proven is "subprocess on fresh code works"; the old-parent-delegates piece is new
  machinery this change builds, and its output transport is a real design (capture and re-emit),
  not a copy.

**Why delegation suffices at the parse layer (code lane, verified):** the old server's
`_parse_upgrade_summary` takes the last sentinel line and `json.loads` it with only a dict check,
and `_bounded_upgrade_summary` is passthrough-with-caps, not an allowlist: terminal keys get
guaranteed budget, unknown scalars pass under a shared character budget, lists page with explicit
truncation counts. The field proof is in this change's own motivating data: the pg1a-era server
surfaced pg5l's brand-new `renderer_provenance_flags` and `permissions_*` fields. New-schema
fields survive an old server, bounded but visible, provided they respect the bounder's shape
limits (flat scalars and lists; oversized values are dropped with a truncation marker).

This change generalizes the reporting-class remedy: the primary-phase summary and the
reconciliation scan run on the freshly extracted code behind a pinned, permanent invocation
contract, so a new summary schema, sensor, or channel reports correctly on the upgrade that ships
it, instead of one upgrade later.

## Requirements

1. **The primary-phase summary is produced by the freshly extracted code.** The old-code window
   for reporting is exactly one site: the primary-phase sentinel emit at the end of `main()`
   (currently `upgrade_wavefoundry.py:4510` via `_emit_primary_phase_summary`), which runs in the
   process that imported the OLD module before Phase 0b extraction. After extraction, the parent
   delegates summary production to a subprocess running the extracted tree's entry point
   (requirement 5) and transports the child's sentinel line into its own stdout contract.

   Constraints, each load-bearing:

   - **The cleanup emit path is NOT delegated.** `phase_cleanup` runs in a fresh process on the
     freshly extracted code by construction (both the CLI and MCP `cleanup` phases spawn after
     extraction), so it already produces new-schema output; wrapping it in a nested subprocess
     adds a failure mode for zero window closure. The emit-path census (task 1) records this
     classification per path.
   - **Capture and re-emit through the parent's logger.** The prior-art backstop does not capture
     child output; the summary subprocess must, because the upgrade-log contract ("the upgrade log
     retains the complete sentinel") and the truncation hint pointing at `log_path` depend on the
     sentinel flowing through `_log`. The parent captures the child's sentinel and re-emits it
     through its own logging path under its own sentinel constant, so a pre-restart server parser
     parses it unchanged. Byte-verbatim applies to the JSON payload; the sentinel PREFIX is the
     parent's own constant and is itself frozen contract surface, locked by the requirement 5
     contract test alongside the argv and envelope.
   - **Exactly one sentinel per run.** The server parser is last-sentinel-wins. The delegation and
     the parent's own fallback emit must be mutually exclusive by construction (single emit site
     choosing delegated output or fallback), so a successful delegate cannot be silently
     overridden by a later parent emit, and vice versa. A test drives the
     delegate-succeeded-then-fallback-also-fires ordering hazard and proves it cannot occur.
   - **Parent-only facts travel through an input carrier.** One summary input is in-memory only:
     `skipped_scan_locations` (module global filled during pack search, per-process permission
     grants make it non-rescannable from a child). The parent persists it to the upgrade lock (or
     passes it through the contract's input channel) before delegating. The 18-key source census
     (code lane, 2026-08-01) found every other key lock- or disk-reconstructable; the standalone
     `--cleanup` path is the existence proof.

2. **The reconciliation scan is invoked through the same pinned contract, replacing the in-process
   cross-version import.** The pg1a defect mechanism is the in-process `import reconcile_scan` at
   the emit site with a blanket exception swallow: old code calling a new module's API and eating
   the skew. Under this change the scan output consumed by the summary comes from the extracted
   tree's producer (as part of the requirement 1 delegation); the in-process path survives only as
   the requirement 3 degradation fallback and is marked as such.

3. **Fail-safe transport with an explicit, surviving degradation marker.** A delegation failure
   degrades to the old parent's own in-process summary, never fails the upgrade, and never
   presents old-schema output as new. Four failure classes are named and each is separately
   tested with a deterministic fixture:

   - entry point absent in the extracted tree (the realistic case: upgrading TO a pack older than
     this change, or a downgrade) — this is a MARKER-CARRYING degradation, not a silent no-op; the
     prior-art `if not script.exists(): return` shape is the anti-pattern;
   - non-zero child exit;
   - malformed or absent sentinel in child output;
   - timeout, with the timeout an injectable parameter pinned by a named constant.

   The degradation marker is a summary field registered in `UPGRADE_SUMMARY_TERMINAL_KEYS` (or
   otherwise proven to survive `_bounded_upgrade_summary`), so bounding can never silently drop
   the very field that discloses degradation. The survival test runs a second variant with the
   marker ABSENT from the terminal-key set: a server launched before this change can outlive
   multiple upgrades without restart and bounds the marker through the unknown-scalar budget path,
   so the marker must be flat and small enough to survive that path too. On degradation the three-way outcome holds: marker
   present, upgrade exit status unchanged, fallback summary never labeled as new-schema.

4. **The disclosure states the honest class boundaries, everywhere operators will read it.** Three
   elements, all required: (a) reporting-class (sentinel-carried) changes shipped after this
   change take effect on the upgrade that installs them; (b) behavior-class fixes still require a
   hook bridge, and server-resident response fields still require a host restart; (c) the one
   remaining reporting-class window firing is THIS change's own installing upgrade (from any
   pre-1u44o runner), and that transition run's old-schema summary must not be reported as the
   backstop failing to work. Landing surfaces, all named: the living `### Upgrading to 1.15.0`
   section of `CHANGELOG.md` (a numbered item; this is the operator-facing surface); seed-160's
   old-code-window paragraph (line ~81; the line ~91 allowlist sentence is behavior-class and
   stays); and the requirement 6 design note for future release authors. There is no
   "changelog template guidance" doc in this repo; durable authoring guidance lives in the design
   note.

5. **The delegation entry point is a pinned, old-calls-new compatibility contract: a tripwire
   against silent drift, not an unpassable wall (operator clarification, 2026-08-01).** Every
   fielded runner that ships this change will invoke the TO-tree entry point on all future
   upgrades. Additive evolution needs no ceremony. Breaking evolution is allowed deliberately: bump
   the schema version token (old fielded runners then route to the marked degradation path for
   their one transition run instead of consuming drifted output as-if-new) and update the contract
   test in the same change. The only thing the contract hard-blocks is SILENT drift, the pg1a
   defect mechanism. The contract, pinned at ship time:

   - **Identity:** a fixed standalone flag on `upgrade_wavefoundry.py` in the extracted tree
     (matching the `--update-index`/`--cleanup` precedent). NOT a hook (hook failure semantics
     abort the upgrade with exit 3, the opposite of requirement 3's posture) and NOT an in-process
     import (the pg1a failure pattern).
   - **Input:** `--root` argv plus the upgrade lock as the state carrier. The new producer
     tolerates an old-schema lock (fields absent that only newer FROM runners write); this inverse
     skew direction is a named test case.
   - **Output:** sentinel-delimited JSON on stdout carrying an explicit schema/contract version
     token. The FROM side treats an unrecognized version token as the requirement 3 degradation
     path, never as new-schema output (this closes the silent-drift case a launch-failure marker
     cannot see).
   - **Import surface:** stdlib-only at module import time for the entry point and everything it
     imports, runnable under the FROM version's tool venv against a partially upgraded target,
     with no dependence on post-upgrade state (published index, completed docs gate, memory
     checkpoints). Prior art: `reconcile_scan.py`, `render_platform_surfaces.py`.
   - **Documentation:** the contract is documented where the hook contract is documented (module
     header or adjacent), with the evolution rule stated.
   - **A permanent contract test** locks the entry-point name, argv shape, output envelope, the
     sentinel prefix value, and version-token handling, and fails if a future edit renames or reshapes the surface without a
     deliberate versioned-compatibility decision. This test is the suite's standing guard for the
     entire fielded population of old runners.

6. **The two-remedy pattern is recorded once, canonically.** An ADR under
   `docs/architecture/decisions/` (the canonical home; shipped seeds must not cite internal field
   history) records: the remedy classes (hook bridge for behavior; fresh-code producer behind the
   pinned contract for sentinel-carried reporting; host restart for server-resident fields), the
   flat-scalar field-shape rule for future summary fields (the bounder drops oversized values and
   treats nested dicts as one scalar), and the named-and-rejected alternative (moving authoritative
   emission into an already-fresh spawned phase; rejected because the default flow runs no such
   phase and last-wins sentinel parsing collides). A one-paragraph pointer lands in
   `docs/architecture/cross-cutting-concerns.md`.

7. **Regression tests defeat the known vacuity traps.** Named traps and their defeats:

   - **AC-1's same-schema trap:** extracting the CURRENT scripts and asserting fields populated
     proves nothing (producer and parent share a schema). The fixture's extracted tree must carry
     a SCHEMA-DIVERGENT producer emitting a probe field the parent's own `_build_upgrade_summary`
     cannot produce; the assertion is that the probe field appears in the captured sentinel, which
     can only happen through delegation. The test enters through the parent's real emit path (not
     the producer function), pins the spawned argv as resolving inside the fixture root's
     extracted tree, and asserts transport under the parent's own sentinel constant.
   - **Parser-side end-to-end:** a new-schema field must survive `_parse_upgrade_summary` and
     `_bounded_upgrade_summary` into `wf_upgrade_response`'s `data['summary']`, not merely appear
     in the sentinel line.
   - **The pg1a reproduction (requirement 2):** install a mismatched-shape `reconcile_scan` stub
     (wrong arity or renamed API) against the retained in-process fallback and observe the silent
     empty channels; then drive the delegated path and observe findings flow. No dead orchestrator
     code is preserved; the in-process path legitimately remains as the degradation fallback.
   - **Re-point, never delete, the existing pins.** Known census (qa lane, 2026-08-01), all in
     scope for deliberate re-points: `test_upgrade_wavefoundry.py` direct
     `_emit_primary_phase_summary` behavioral tests (~:1826, ~:4812), `main()` flow tests patching
     the emit (~:2263, ~:2403), `_print_operator_summary` scan-wiring cluster (~:4599-:4707) and
     monkeypatched-scan tests (~:4841, ~:4871), the summary shape-parity cluster including the AST
     pin that `main()` calls the emit exactly once (~:4943), `_build_upgrade_summary` field and
     permissions-delta tests (~:5174, ~:7045-:7135); `test_reconcile_scan.py` AST ordering pin and
     the EXHAUSTIVE emitter-set pin (~:820-:868), which breaks by construction on any new emitter
     and is the highest deletion-temptation test in the set; `test_server_tools.py`
     `wf_upgrade_response` summary cluster (~:23722-:24800), extending the sentinel round-trip
     (~:24758) to the child-transport contract.

## Scope

**Problem statement:** the primary-phase upgrade summary is assembled by pre-extraction code, so
every reporting change ships one upgrade late, producing false field bug reports (three confirmed
instances, one of which is server-resident and excluded from this remedy's reach).

**In scope:**

- The primary-phase summary emit seam in `upgrade_wavefoundry.py` and the parent-side delegation
  (spawn, capture, re-emit, mutual-exclusion, degradation)
- The pinned entry-point contract (requirement 5) and its permanent contract test
- The reconciliation-scan routing (replacing the in-process cross-version import at the emit site)
- The parent-only-facts input carrier (`skipped_scan_locations` persistence)
- The degradation marker and its bounder survivability, including its rendering in
  `wf_upgrade_response`
- Disclosure updates: CHANGELOG Upgrading section, seed-160 old-code-window paragraph, the ADR
- Regression tests per requirement 7, including the enumerated re-points

**Out of scope:**

- Behavior-class fixes (hook-bridge pattern, proven in wave 1u44n)
- Server-resident response assembly (`runner_stale`, diagnostics, the bounder itself); host
  restart remains their only remedy and the restart disclosure their surface
- The cleanup emit path's execution model (already fresh-process new code; census records it)
- The permissions-rendering backstop itself (shipped, field-proven prior art)
- Retroactive repair of pfxp/pg1a-era summaries

**Sequencing precondition (release lane, firm):** the 1u44n-era tree is COMMITTED before the first
1u5vl implementation edit. The tree carries two closed waves' delivery-verified state in the same
files this change edits; detection (AC-7's regression gates) is not restoration, and
`build_pack.py --release` refuses a dirty tree regardless. There is no rebase alternative.

## Acceptance Criteria

- [x] AC-1: On an upgrade driven by the CURRENT (old) parent with a schema-divergent extracted
  tree, the delegated summary's probe field appears in the emitted sentinel AND survives into
  `wf_upgrade_response`'s `data['summary']`; the spawned argv resolves inside the extracted
  fixture tree; transport uses the parent's own sentinel constant; and the producer tolerates an
  old-schema upgrade lock. The test enters through the parent's real emit path; a same-schema
  fixture cannot satisfy this AC.
  (`DelegatedSummarySchemaDivergentTests.test_probe_field_transports_through_the_parents_real_emit_path`
  plus `test_server_tools.test_new_schema_probe_field_survives_into_response_summary`;
  old-schema lock tolerance of the real producer in
  `DelegatedSummaryContractTests.test_real_child_envelope_and_old_schema_lock_tolerance`.)
- [x] AC-2: Each of the four named failure classes (entry point absent, non-zero exit, malformed
  or absent sentinel, injected timeout) degrades to the parent's own summary with the degradation
  marker present, the upgrade's exit status unchanged, and the fallback never presented as
  new-schema. The marker survives `_bounded_upgrade_summary` (terminal-key registration PLUS the
  absent-from-terminal-set survival variant of requirement 3). The delegate-succeeded-then-fallback-ordering hazard is driven and
  proven impossible (single mutually exclusive emit site).
  (`DelegatedSummaryDegradationTests` covers all four classes plus the old-pack flag-rejection
  variant and the ordering-hazard canary; `test_server_tools` carries the terminal-key
  budget-pressure survival test and the absent-from-terminal-set stale-server variant; the
  structural mutual-exclusion pin is
  `test_fallback_emitter_is_called_only_from_the_delegator`.)
- [x] AC-3: The pg1a empty-channel scenario is reproduced (mismatched-shape scan module against
  the in-process fallback yields silent empty channels) and shown repaired through the delegated
  path; findings flow end to end into the summary and response.
  (`DelegatedSummaryPg1aReproductionTests`: red-first; the repro test passed against the
  pre-change tree while the delegated-path test failed with AttributeError; both green after
  implementation. Response-side flow covered by the parser-side end-to-end test in
  `test_server_tools.py`.)
- [x] AC-4: The disclosure carries all three elements of requirement 4 (sentinel-carried fixes now
  install-effective; behavior-class and server-resident exclusions stated; this change's own
  installing upgrade named as the last reporting-class window firing, with the
  do-not-report-as-failure sentence) and lands on all three named surfaces: CHANGELOG
  `### Upgrading to 1.15.0`, seed-160 line ~81, and the ADR.
  (CHANGELOG numbered item 8 carries (a)/(b)/(c) including the do-not-report sentence; seed-160's
  new reporting paragraph carries (a)/(b)/(c) with the same sentence; the ADR states the class
  taxonomy in the Decision and the last-window residual with the not-a-defect framing in the
  Consequences.)
- [x] AC-5: The entry-point contract is documented (identity, input, output with version token,
  failure semantics, timeout constant, import-surface rule, additive-only evolution) and locked by
  a permanent contract test that fails on rename or reshape; an unrecognized version token routes
  to the AC-2 degradation path.
  (Contract documented in the `_emit_delegated_summary` docstring plus the constants block beside
  the sentinel; locked by `DelegatedSummaryContractTests`; token routing in
  `test_unrecognized_version_token_routes_to_degradation`.)
- [x] AC-6: The ADR exists under `docs/architecture/decisions/` with the cross-cutting-concerns
  pointer, records the three-way remedy taxonomy and the flat-scalar field rule, and
  `docs/architecture/layering-rules.md` (Boundary Invariants row for the FROM-runner to TO-tree
  producer edge) and `docs/architecture/data-and-control-flow.md` (which process builds the
  summary) are updated.
  (`1u49j-adr fresh-code-summary-producer-contract.md`, accepted; the rejected
  fresh-phase-emission alternative is the first row of its Alternatives table; docs-lint passes
  via `wf_validate_docs`.)
- [x] AC-7: The full framework suite passes; the wave 1u44n publication and bridge test clusters
  stay green; every enumerated existing pin from requirement 7 is re-pointed rather than deleted
  (including the two AST pins); and the emit-path census with per-path process/version
  classification is recorded in this doc.
  (Full suite `run_tests.py`: 6690 tests / 61 files OK; seam cluster together: 2131 OK;
  `Phase4PublisherGrantTests` + `PreIndexUpdateBridgeTests`: 14 OK; re-point census in the
  Progress Log; census table above.)

## Tasks

- [x] Census the emit paths and classify each by executing process and code version (primary emit:
      old in-process; cleanup emit: fresh post-extract process; standalone index phases: no
      sentinel); record in this doc (see Emit-Path Census below)
- [x] Persist `skipped_scan_locations` to the upgrade lock (or the contract input channel) before
      delegation (`_persist_skipped_scan_locations`, called first inside the single emit site)
- [x] Design and document the entry-point contract per requirement 5 (identity flag, argv, lock
      input with old-schema tolerance, sentinel JSON output with version token, timeout constant,
      stdlib-only import surface, additive-only evolution rule) (contract constants block beside
      `WAVE_UPGRADE_SUMMARY_SENTINEL`; full contract in the `_emit_delegated_summary` docstring)
- [x] Implement the delegation at the primary emit with capture-and-re-emit through `_log`, single
      mutually exclusive emit site, and the four-class degradation with the surviving marker
      (`_emit_primary_summary_via_delegate_or_fallback` + `_delegated_summary_payload`)
- [x] Route the summary's reconciliation input through the delegated producer; retain the
      in-process path only as the marked degradation fallback (`_emit_delegated_summary` computes
      the scan fresh; `_emit_primary_phase_summary` docstring marks the fallback)
- [x] Write the permanent entry-point contract test (`DelegatedSummaryContractTests`: sentinel
      value, flag literal, argv shape, pinned timeout in the spawn, real-child envelope with
      old-schema lock, unrecognized-token degradation)
- [x] Write the AC-1 schema-divergent fixture test, the parser-side end-to-end test, the AC-2
      failure-class tests, and the AC-3 pg1a reproduction
      (`DelegatedSummarySchemaDivergentTests`, `test_server_tools` probe/marker tests,
      `DelegatedSummaryDegradationTests`, `DelegatedSummaryPg1aReproductionTests`)
- [x] Re-point the enumerated existing pins (requirement 7 census), including the two AST pins
      (re-point census recorded in the Progress Log)
- [x] Author the ADR and the cross-cutting-concerns pointer; update layering-rules (Boundary
      Invariants row) and data-and-control-flow
      (`docs/architecture/decisions/1u49j-adr fresh-code-summary-producer-contract.md`; pointer
      section "Upgrade Remedy Classes (fresh-code reporting)"; FROM-runner to TO-tree producer
      row; data-and-control-flow summary-process paragraph)
- [x] Update CHANGELOG `### Upgrading to 1.15.0` and seed-160 line ~81 with the requirement 4
      disclosure (open `seed_edit_allowed` before the seed edit; close after); leave seed-160
      line ~91 untouched
      (CHANGELOG item 8 plus a `### Fixed` bullet; seed-160 gained the "Upgrade REPORTING no
      longer waits a cycle" paragraph appended to the ~:81 old-code-window block, gate opened and
      closed around the edit; the ~:91 allowlist transition sentence is untouched; the rendered
      `docs/prompts/upgrade-wavefoundry.prompt.md` mirror carries the same paragraph so seed and
      rendered surface do not drift)
- [x] Add a companion provenance sentence to the spec's structured-summary bullet
      (`docs/specs/mcp-tool-surface.md` ~:919) so the 1u44n value-domain statement and the new
      subprocess-vs-fallback provenance do not drift
- [x] Note in passing (audit-only, no scope expansion): `HOOK_NAMES` omits
      `pre/post_index_update` though `main()` dispatches them (recorded in the Emit-Path Census
      section of this doc)
- [x] Full suite plus the 1u44n test clusters (full suite: 6690 tests across 61 files, OK;
      phase-transition seam cluster run together per the fragile-file watchpoint: 2131 tests OK;
      1u44n clusters `Phase4PublisherGrantTests` + `PreIndexUpdateBridgeTests`: 14 tests OK)

## Emit-Path Census (task 1, recorded 2026-08-01)

Every sentinel- or summary-producing path in `upgrade_wavefoundry.py`, classified by executing
process and code version at emit time:

| Path | Site | Executing process | Code version at emit | Classification |
| ---- | ---- | ----------------- | -------------------- | -------------- |
| Primary emit | `main()` end of default phases 0-4 (`_emit_primary_phase_summary`, call site formerly ~:4510) | The OLD parent process; the module was imported before Phase 0b extraction | FROM (old) code emitting against the freshly extracted TO tree | THE old-code reporting window; delegated by this change |
| Cleanup emit (success) | `phase_cleanup` -> `_print_operator_summary` -> `_emit_summary_line` | Fresh `--cleanup` subprocess spawned after extraction (CLI `upgrade-wavefoundry --cleanup`; MCP `wf_upgrade(phase='cleanup')`) | TO (new) code by construction | Already fresh; NOT delegated (nested subprocess would add a failure mode for zero window closure) |
| Cleanup emit (failed-phase branch) | `phase_cleanup` failure branch -> `_print_operator_summary` | Same fresh `--cleanup` subprocess | TO (new) code | Not delegated (same fresh-process argument) |
| Standalone `--update-index` / `--rebuild-index` | No sentinel emit at all (publication outcome recorded in the lock; printed failure marker only) | Fresh subprocess | TO (new) code | No sentinel; out of scope |
| Delegated producer (NEW, this change) | `--emit-summary` standalone flag | Fresh subprocess the old parent spawns from the extracted tree | TO (new) code | The requirement 1 delegation target |

Audit-only note (no scope expansion): `HOOK_NAMES` (~:1077) omits `pre_index_update` /
`post_index_update` even though `main()` dispatches both on the default path (~:4455, ~:4468) and
the standalone `--update-index` branch dispatches them too (~:3814, ~:3843). Recorded here only;
dry-run hook inventory therefore under-reports those two hook points.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                   |
| ---------- | ----------- | ---------- | ----------------------------------------- |
| fix        | implementer | —          | Delegation, contract, reconciliation routing, and disclosure updates move together |


## Serialization Points

- `upgrade_wavefoundry.py` (the primary emit seam; also carries the just-closed 1u44n changes).
  PRECONDITION: the 1u44n-era tree is committed before the first implementation edit here; there
  is no rebase alternative (release lane, 2026-08-01).
- `server_impl.py` (degradation-marker rendering in `wf_upgrade_response`; terminal-key
  registration) and `test_server_tools.py`'s summary cluster move with it.

## Affected Architecture Docs

- NEW ADR under `docs/architecture/decisions/` (two-remedy taxonomy, flat-scalar rule,
  rejected alternative). Required.
- `docs/architecture/cross-cutting-concerns.md` — pointer paragraph. Required.
- `docs/architecture/layering-rules.md` — Boundary Invariants row for the FROM-runner to TO-tree
  producer contract. Required.
- `docs/architecture/data-and-control-flow.md` — which process builds the summary. Required.
- `docs/specs/mcp-tool-surface.md` ~:919 — provenance companion to the structured-summary bullet.
  Required.
- `CHANGELOG.md` `### Upgrading to 1.15.0` — the requirement 4 disclosure item. Required.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` ~:81 — reporting-class
  disclosure update (gated by `seed_edit_allowed`); line ~91 stays. Required.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The delegation is the change; the vacuity guard is what makes its proof real |
| AC-2 | required | A silent degradation recreates the false-report pattern this change exists to end |
| AC-3 | required | The motivating field defect must be reproduced and shown repaired |
| AC-4 | required | An overbroad disclosure would itself ship the fourth false field report |
| AC-5 | required | Without the pinned contract, this change plants the mechanism for a silent 1.17+ reopening |
| AC-6 | required | The taxonomy is the durable defense; unrecorded patterns get rediscovered in the field |
| AC-7 | required | Two closed waves' verified state shares these files; regression gates are non-negotiable |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-01 | Filed from three field-confirmed instances of the old-code reporting window (pfxp extraction debris, pg1a runner_stale null, pg1a reconciliation []); the pg5l field run retracted the standing-regression theory for the third instance and proved both remedy classes. | Operator field reports 2026-07-31 and 2026-08-01; pg5l run: reconciliation 34/34, direct scan cross-check [34, 0, 0] |
| 2026-08-01 | Implementation complete; change marked implemented. All docs surfaces landed (ADR `1u49j`, cross-cutting pointer, layering-rules Boundary Invariants row, data-and-control-flow paragraph, mcp-tool-surface provenance sentence, CHANGELOG Upgrading item 8 + Fixed bullet, seed-160 disclosure with the gate opened and closed around both seed edits, rendered prompt mirror). Operator mid-implementation clarification (tripwire-not-wall contract framing) folded into ADR, module docstrings, argparse help, contract-test docstring, seed/prompt disclosure, layering row, CHANGELOG. Verification: docs-lint ok (`wf_validate_docs` twice, after each docs pass); seam cluster together (test_upgrade_wavefoundry, test_review_policy, test_index_state_store, test_upgrade_protocol, test_server_tools, test_reconcile_scan): 2131 tests OK; full suite: 6690 tests / 61 files OK; 1u44n clusters 14 tests OK. Em-dash rule enforced across every added line (scripted pass over diff-added lines; zero remaining in authored text). | Suite outputs recorded in this row; AC list above carries per-AC test names |
| 2026-08-01 | Re-point census executed (requirement 7; re-point, never delete): `test_upgrade_wavefoundry.py` direct emit behavioral tests (:1826, :4812) KEPT unchanged (they now cover the retained fallback; signature stayed backward compatible); main-flow patch sites (:2263, :2403) re-pointed to patch `_emit_primary_summary_via_delegate_or_fallback`; `_print_operator_summary` scan-wiring cluster and monkeypatched-scan tests KEPT (cleanup emit untouched); shape-parity cluster KEPT; emit-call-count AST pin re-pointed to the delegator plus a new zero-direct-fallback-calls assertion and a new module-wide callers pin (`test_fallback_emitter_is_called_only_from_the_delegator`); `_build_upgrade_summary` field/permissions tests KEPT; `test_reconcile_scan.py` ordering pin re-pointed to the delegator and the EXHAUSTIVE emitter set deliberately extended with `_emit_delegated_summary`; `test_server_tools.py` sentinel round-trip (:24758 cluster) extended with `test_round_trip_delegated_child_transport`. Both target files green: 470 tests OK. | `unittest tests.test_upgrade_wavefoundry tests.test_reconcile_scan`: `Ran 470 tests ... OK` |
| 2026-08-01 | AC-3 red-first cycle complete: mechanism-repro test (mismatched 4-channel `reconcile_scan` stub -> `_run_reconciliation_scan` returns `([], [], [])` silently; end-to-end sentinel reports `[]`) PASSED against the pre-change tree; the delegated-path test FAILED red (`AttributeError: module 'upgrade_wavefoundry' has no attribute '_emit_primary_summary_via_delegate_or_fallback'`); after implementing the delegation (constants, `--emit-summary` producer, `_delegated_summary_payload`, single emit site, marker registration in `server_impl.UPGRADE_SUMMARY_TERMINAL_KEYS`) both tests PASS. | `tests.test_upgrade_wavefoundry.DelegatedSummaryPg1aReproductionTests`: red run `FAILED (errors=1)`; green run `Ran 2 tests ... OK` |
| 2026-08-01 | Implementation started (wave OPEN at HEAD 15723021, clean tree). Emit-path census recorded (task 1); contract frozen in the Decision Log (`--emit-summary`, `summary_schema: 1`, `_SUMMARY_DELEGATE_TIMEOUT_S`, marker `summary_source_degraded`). Gapfill note: after initial MCP retrieval (code_outline + code_keyword + code_read on the emit seam), remaining bulk-range exploration of `upgrade_wavefoundry.py` / `server_impl.py` / test pins used harness Read for context economy (repeated MCP advisory payloads); no semantic search was replaced by grep. | Census table in this doc; MCP calls: code_outline, code_keyword x2, code_read x4 |
| 2026-08-01 | Six-lane prepare review (red-team seat, code, qa, architecture, docs-contract/rotating seat, release) of the first draft; consolidated repair pass folded. Red-team NOT-READY corrections: the covered class split honestly (sentinel-carried vs server-resident; runner_stale is server-resident and out of this remedy's reach), the entry-point stability contract promoted to requirement 5, parent-only-facts input carrier promoted into requirement 1, the last-wins sentinel hazard closed in requirement 1/AC-2, and the two refuted Decision Log absolutes rewritten (a pre-emit hook seam DOES exist and is rejected on fail-safety; the old parser is passthrough, field-proven by pg5l's new fields surfacing through the pg1a server). Code lane confirmed the pg1a mechanism structurally (2-tuple unpack vs 3-channel return, swallowed), the 18-key source census (only skipped_scan_locations is memory-only), the cleanup emit already running fresh-process new code, and the capture-and-re-emit transport requirement. QA lane: AC-1 schema-divergent vacuity guard, parser-side end-to-end coverage, marker bounder-survivability, four enumerated failure classes, and the full re-point census including two AST pins. Architecture lane: standalone-flag identity (not hook, not import), lock-as-input with old-schema tolerance, stdlib-only import surface, ADR as canonical home, layering-rules and data-and-control-flow additions. Docs lane: the phantom "changelog template guidance" surface re-pointed at the living CHANGELOG Upgrading section, AC-4 made congruent with the last-window residual, drafted disclosure adopted as the acceptance target. Release lane: commit-before-implement precondition (rebase alternative struck), the contract test as the standing guard for the fielded runner population, pack-contents and release-preflight checks clean. | Six lane reports 2026-08-01; approvals recorded to the sibling events.jsonl at readiness || 2026-08-01 | Delivery review cycle 1: five fresh-context lanes (code, qa, architecture, docs-contract, release) all PASS with executed verification; seven mutation checks across two lanes with the delivered tests killing all briefed mutants. Findings, all repaired by the coordinator and reverified by their originating lanes: docs/release P2 (the CHANGELOG and ADR disclosure wrongly attributed the degradation marker to the transition run; a pre-mechanism runner has no marker code, so both surfaces now state the transition summary is UNMARKED); code-lane P3 pair folded as hardening (the summary child's env now pops WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN per the non-publisher-child precedent, and the unrecognized-token marker clamps the child-controlled repr to 40 chars so an oversized drifted token cannot bound away the disclosure); qa-lane P2 (its self-authored mutant D2 survived: nothing proved the real producer reads a NONEMPTY skipped_scan_locations from the lock; a new contract test round-trips a nonempty value through the real child and is confirmed to kill exactly that mutant). Lane highlights: architecture proved the producer runs under a venv-less Python 3.9.6 with zero third-party imports; release staged the REAL base-commit tree and proved the old argparse rejects the flag with exit 2 into marked degradation; code proved the sentinel lands in the upgrade log through _log and that partial or double child sentinels can never reach the server parser. | Five lane reports plus four reverification confirmations, 2026-08-01; ledger delivery records |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-01 | Generalize the fresh-code producer rather than adding per-field bridges | The subprocess-on-fresh-code mechanism is field-proven (permissions backstop); per-field hook bridges for reporting would multiply transition surfaces each needing its own fail-safety. A hook-bridge seam for the summary DOES exist (`post_index_update` dispatches before the primary emit), but is rejected on fail-safety and complexity: hook failures abort the upgrade with exit 3, the opposite of the required degrade-with-marker posture, and the emission would still race the parent's own emit under last-sentinel-wins parsing | Per-fix hook bridges (rejected: fail-fatal semantics, transition-surface multiplication); accept the one-cycle window and disclose (rejected: three false field reports in two days is the measured cost) |
| 2026-08-01 | Runner-side delegation is sufficient for sentinel-carried fields; the parser needs no bridge | The old server's parser is passthrough-with-caps, not an allowlist: field-proven by the pg1a-era server surfacing pg5l's new summary fields. The residual parser-side risks are size bounds (handled by the flat-scalar rule and terminal-key marker registration), not field filtering. Server-RESIDENT response fields are a different class entirely and are excluded from scope with the restart disclosure | Bridge the parser too (rejected: no mechanism exists to replace running-server code without restart, and none is needed for sentinel-carried content) |
| 2026-08-01 | Ship in 1.15.0 (operator direction, 2026-08-01) | The delegation lives on the FROM side, so each release of delay costs one more windowed generation: landed in 1.15.0 it protects 1.16+'s sentinel-carried reporting on their installing upgrades. Every recent release has touched reporting surfaces | Land in the next cycle (rejected by operator); accepted residual either way: this change's own installing upgrade is the last reporting-class window firing, and requirement 4(c) mandates the disclosure |
| 2026-08-01 | Entry point is a fixed standalone flag with a frozen, versioned, tested contract | The fielded runner population is frozen code invoking this surface forever; the pg1a defect was precisely an unpinned cross-version call. Standalone-flag precedent has held (`--update-index`, `--cleanup`); hooks are fail-fatal; in-process import is the failure pattern itself | A new hook name (rejected: exit-3 semantics); in-process import of the new module (rejected: the pg1a mechanism); an unversioned envelope (rejected: silent schema drift is invisible to a launch-failure marker) |
| 2026-08-01 | Delegate only the primary emit; the cleanup emit stays as-is | The cleanup phase already runs in a fresh post-extract process on new code (census-confirmed); a nested subprocess there adds a failure mode for zero window closure | Delegate both emit paths symmetrically (rejected: redundant machinery on the already-fresh path) |
| 2026-08-01 | Authoritative-emission-from-a-fresh-phase rejected as the primary design | The default upgrade flow runs no post-extract phase that could own the primary report, and last-sentinel-wins parsing means a second authoritative emitter collides with the parent's; recorded in the ADR as the named alternative since the prior art's first-time success belongs to that topology | Move the authoritative summary into `--update-index`/`--cleanup` (rejected: not on the default path; ordering collision) |
| 2026-08-01 | Commit the 1u44n-era tree before the first implementation edit | Two closed waves' delivery-verified state sits uncommitted in the same files this change edits; detection is not restoration, this repo has already lost uncommitted work to a subagent's git call once, and the release build refuses a dirty tree regardless | "Rebase deliberately" (struck: with delivered-but-uncommitted verified state there is no defensible rebase path) |
| 2026-08-01 | Entry-point contract frozen (implementer): flag `--emit-summary`; argv `[<tool-venv python>, <root>/.wavefoundry/framework/scripts/upgrade_wavefoundry.py, --emit-summary, --root, <root>]`; input = `--root` plus the upgrade lock (old-schema tolerant); output = exactly one stdout line `WAVE_UPGRADE_SUMMARY_JSON:{json}` whose payload carries `summary_schema: 1` (`SUMMARY_SCHEMA_VERSION`); parent recognizes token set {1}, anything else degrades; timeout pinned by `_SUMMARY_DELEGATE_TIMEOUT_S = 300` (precedent `_HOOK_TIMEOUT_S`); degradation marker field `summary_source_degraded` (flat short string, terminal-key registered) | Matches the `--update-index`/`--cleanup` standalone-flag precedent; the sentinel prefix reuses the frozen `WAVE_UPGRADE_SUMMARY_SENTINEL` value the fielded server population already parses; the token travels inside the payload so it survives byte-verbatim re-emit; 300s matches the only existing pinned subprocess timeout precedent for upgrade-spawned work | `--summary` (rejected: reads as a human prose request); `--emit-primary-summary` (rejected: the contract is about WHERE the summary is produced, not which phase consumes it; shorter name survives additive evolution better); a second sentinel prefix for delegated output (rejected: the old-server parser only knows the frozen prefix; a new prefix would strand delegated output on every pre-restart server) |
| 2026-08-01 | Contract framing per operator clarification (folded mid-implementation): the pins are a TRIPWIRE against silent drift, not an unpassable boundary; additive evolution needs no ceremony, deliberate breaking evolution bumps `SUMMARY_SCHEMA_VERSION` and updates the contract test in the same change, and only silent rename/reshape is hard-blocked. Mechanism unchanged (flag, token, timeout, degradation, contract test all as designed); the framing was carried into the ADR, the module contract docstring and constants comment, the argparse help, the contract-test docstring, the seed-160 disclosure (and its rendered mirror), the layering-rules row, and the CHANGELOG bullet | Freeze-forever wording (superseded: it misstates the evolution path and would deter legitimate versioned changes) |
| 2026-08-01 | Delegation mechanics: parent persists `skipped_scan_locations` to the lock, then a single mutually exclusive emit site (`_emit_primary_summary_via_delegate_or_fallback`) either re-emits the child payload byte-verbatim through `_log` under the parent's own sentinel constant or calls `_emit_primary_phase_summary(degradation_marker=...)`; the fallback summary never carries `summary_schema` | One if/else at one call site makes the last-wins collision structurally impossible; the marker rides `_build_upgrade_summary` output so the fallback stays honest old-schema; token absent on fallback means a fallback can never be mistaken for new-schema output | Emit both and let last-wins pick (rejected: the exact ordering hazard requirement 1 names); child writes the upgrade log directly (rejected: the log contract requires the sentinel to flow through the parent's `_log`) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The subprocess boundary adds a failure mode to every upgrade's summary | Requirement 3: four named failure classes, each deterministically tested; degrade to the parent's summary with a bounder-surviving marker; never fail the upgrade |
| A future release renames or reshapes the entry point, silently reopening the window for the fielded population | Requirement 5's permanent contract test plus the version token; unrecognized token routes to marked degradation |
| `upgrade_wavefoundry.py` is a named fragile file carrying two closed waves' uncommitted verified state | Commit-first precondition (Scope, Serialization Points); AC-7 regression gates on top; seam test cluster rerun per the fragile-file watchpoint |
| The disclosure overclaims and itself produces the fourth false field report | Requirement 4's three mandatory elements including the server-resident exclusion and the last-window residual; AC-4 checks all three on all three surfaces |
| A future summary field violates the bounder's shape limits and dies at old servers despite delegation | The ADR's flat-scalar field rule; the parser-side end-to-end test pattern in requirement 7 |
| The delegate and the parent fallback both emit, and last-wins parsing picks the wrong one | Single mutually exclusive emit site, with the ordering hazard driven by an AC-2 test |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
