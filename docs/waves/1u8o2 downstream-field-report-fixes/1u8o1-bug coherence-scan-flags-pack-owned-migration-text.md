# Coherence Scan Flags Pack-Owned Migration Text as Stale Tool References

Change ID: `1u8o1-bug coherence-scan-flags-pack-owned-migration-text`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-01
Wave: `1u8o2 downstream-field-report-fixes`

## Rationale

Downstream field report (Solaris, 2026-08-01): `wf_audit` reports 11 `harness_coherence`
`stale_tool_reference` findings, all inside the shipped pack under `.wavefoundry/framework/seeds/`:
`wave_open_gate` (3 hits in seed-160) and `wf_cli` (8 hits across six seeds). No downstream project
can fix pack-owned text, so these are permanent noise in every downstream audit.

**Prepare-cycle grounding (2026-08-01, executed):** the real `_audit_harness_coherence` run against
this repo reproduces the field exactly, PLUS a twelfth finding the report missed:
`docs/prompts/upgrade-wavefoundry.prompt.md` (the rendered seed-160 mirror) carries `wf_cli` too,
and `docs/prompts` is inside the scan scope (`server_impl.py:13356-13359`). Two mechanism facts
that redirect the fix:

- The seed-160 `wave_open_gate` mentions (lines 182, 356, 459) are MIGRATION INSTRUCTIONS and a
  verification-checklist item; the retired name must stay in that text. Note the three hits do not
  share one phrasing shape (:459 is a checklist line, not an "update X to Y" sentence).
- The `wf_cli` hits are all ALREADY in module-path form (`wf_cli.py`); the checker regex
  (`server_impl.py:13426`) substring-matches `wf_cli` inside `wf_cli.py`, so a seed rewrite cannot
  fix them. The `NON_TOOL_IDENTIFIERS` allowlist (`:13396-13399`) already carries the precedent
  (`wave_lint_lib`) and lacks `wf_cli`.
- Inventory fragility: `wave_open_gate` flags only because the live-tools collector regex
  (`:13372`) has no `wave_` branch, while the equally retired `wf_close_wave_gate` in the SAME
  seed lines escapes only via the legacy shim `wf_close_wave_gate_response` still existing
  (`server_impl.py:7648`) and the `clean + "_response"` check (`:13439`). Removing those shims
  later would mint three new findings; tests must cover both retired names.

Companion documentation item from the same report, folded here because it lands in the same seed:
the report claimed seed-160 "states no procedure" for pre-allowlist transition debris. That claim
is STALE against this tree (docs lane, verified): seed-160:93 already carries, inline with the
never-delete caution, a partial identification ("untracked, byte-identical to the zip members")
plus the anti-false-report sentence; the 1tz6l work added it after the Solaris pack shipped, which
explains the reporter's gap. The genuine remaining delta is the `payload/*.json` manifest
criterion and an explicit removal-is-then-safe statement.

## Requirements

1. **The checker-side name-resolution fixes are REQUIRED (they silence the mirrors too):**
   `wf_cli` joins `NON_TOOL_IDENTIFIERS` (the `wave_lint_lib` precedent), and retired-name
   handling covers BOTH `wave_open_gate` and `wf_close_wave_gate` symmetrically (a
   remediation-context exemption, a retired-names allowlist for migration text, or an equivalent
   mechanism; chosen and recorded). A seed rewrite is NOT a fix: the text is already module-path
   form and the regex substring-matches it (executed proof in the Progress Log).
2. **The pack-scope decision is made with the coverage loss stated honestly.** The coherence scan
   is currently this repository's ONLY automated stale-tool-reference audit over the canonical
   seeds (docs-lint has no such check; the reconciliation scan already excludes the pack,
   `reconcile_scan.py:130`). Therefore choose ONE of, and record the choice with its tradeoff:
   (a) conditional pack exclusion with an upstream carve-out (findings suppressed when scanning a
   TARGET repo's vendored pack; still reported when the scan root is the framework source
   repository), or (b) non-blocking reclassification (pack-owned findings become an explicit
   `pack_internal` class downstream projects can ignore, preserved both sides). The filed risk
   claim "upstream still audits seeds directly" is corrected: no such surviving surface exists,
   and an unconditional exclusion would have hidden the historical 52-finding sweep.
3. **Seed-160's debris guidance is EXTENDED, not duplicated.** The existing inline identification
   at seed-160:93 gains the `payload/*.json` manifest criterion and the explicit
   removal-is-then-safe statement (optionally promoted from parenthetical to a short standalone
   sentence adjacent to the caution). Generic wording, no wavefoundry-internal IDs. Seed edit is
   gated (`seed_edit_allowed` open before, close after); the rendered prompt mirror is re-rendered
   through the canonical renderer, with "matches" meaning the renderer reports no drift, not
   textual identity.

## Scope

**Problem statement:** downstream audits carry permanent unfixable noise from pack-owned text (11
seed findings plus the rendered-mirror twelfth), the checker misclassifies a module reference as a
tool, and the seed's debris-identification guidance is one criterion short of complete.

**In scope:** `_audit_harness_coherence` in `server_impl.py` (NON_TOOL_IDENTIFIERS, retired-name
handling, the requirement 2 scope mechanism); seed-160:93's extension (gated) and its rendered
mirror; regression tests.

**Out of scope:** the migration-instruction text itself (correct as written); the reconciliation
scan; other audit surfaces except where the requirement 2 mechanism reshapes the
`harness_coherence` response (coordinate with 1u8o0's audit-shape edit per the wave serialization
watchpoint).

## Acceptance Criteria

- [ ] AC-1: The executed scan against a downstream-shaped fixture (fixture text COPIED from the
  real seed-160 lines and a rendered `docs/prompts` mirror included, per the
  fixtures-from-canonical-producers rule; live-tools note: the collector reads the RUNNING
  server's scripts directory, not the fixture root) reports zero pack-owned
  `stale_tool_reference` findings under the chosen requirement 2 mechanism; if mechanism (a) is
  chosen, a framework-source-shaped fixture still reports them; if (b), the classification field
  is asserted. The mechanism and its coverage tradeoff are recorded in the Decision Log.
- [ ] AC-2: Seed-160:93's identification is extended in place (manifest criterion plus
  removal-safe statement), stays generic, passes docs-lint, and the re-rendered mirror reports no
  drift; the never-delete caution and the anti-false-report sentence are intact.
- [ ] AC-3: Post-fix, the migration text still contains BOTH retired names (`wave_open_gate` and
  `wf_close_wave_gate`) at the instruction lines, asserted on the canonical seed and the rendered
  mirror (a checker fix that "fixed" the seed instead trips this).
- [ ] AC-4: `wf_cli` no longer flags anywhere (seeds or mirrors); the scan still catches a
  genuinely stale tool reference (a positive-control fixture with a real retired tool name in
  non-migration prose still flags).
- [ ] AC-5: Full suite and docs-lint pass.

## Tasks

- [ ] Add `wf_cli` to `NON_TOOL_IDENTIFIERS`; implement the retired-name handling covering both
      retired gate names; record the mechanism
- [ ] Decide and implement the requirement 2 scope mechanism; record the choice and coverage
      tradeoff in the Decision Log
- [ ] Build the fixture tests per AC-1 and AC-4 (copied seed text; mirror included; positive
      control)
- [ ] Extend seed-160:93 (open `seed_edit_allowed`, edit, close); re-render the mirror; AC-3
      assertions
- [ ] Full suite plus docs-lint

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          | Serialize the `server_impl.py` audit-shape edit with 1u8o0's |


## Serialization Points

- `server_impl.py` (`_audit_harness_coherence` and any `harness_coherence` response reshaping)
  is shared with 1u8o0's `wf_audit` drift extension; land both audit-shape edits against
  `docs/specs/mcp-tool-surface.md` in one pass.
- seed-160 and its rendered mirror (gated edit; shared with any concurrent seed work).

## Affected Architecture Docs

- seed-160 (gated) and its rendered mirror: the doc surfaces of requirement 3.
- `docs/specs/mcp-tool-surface.md`: required IF requirement 2's mechanism reshapes the
  `harness_coherence` response (note: the audit section does not document `harness_coherence`
  today; decide at implementation whether to document it and record the decision).
- CHANGELOG `### Fixed` bullet at the release that ships it.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | TBD      |           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-01 | Filed from the Solaris downstream defect report (11 pack-owned findings). Pre-filing verification established the migration-instruction nuance (retired names must stay in seed text; fix is checker-side). | Field report 2026-08-01; seed-160 lines 182, 356, 459 |
| 2026-08-01 | Prepare cycle grounded and extended the plan by execution: the real scan reproduces the 11 findings PLUS a twelfth in the rendered docs/prompts mirror (so pack-path exclusion alone cannot deliver zero); the seed-rewrite branch for wf_cli is proven vacuous (text already module-path form, regex substring-matches; checker exemption is required, NON_TOOL_IDENTIFIERS precedent at server_impl.py:13396-13399); the inventory fragility around wf_close_wave_gate's legacy-shim escape is recorded and both retired names enter AC-3; the "upstream still audits seeds" risk claim is corrected (no such surface; the scan is the only stale-seed-text detector, driving requirement 2's honest choice); and the debris-guidance premise is corrected as stale (seed-160:93 already carries partial identification from the 1tz6l work postdating the Solaris pack; requirement 3 reframed as extend-in-place). | Executed probe of _audit_harness_coherence (92 files, 12 findings), 2026-08-01; server_impl.py:13356-13439, :7648; reconcile_scan.py:130; seed-160:93 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-01 | The wf_cli fix is checker-side exemption, required | The seed text is already module-path form and the regex substring-matches it; rewriting seeds cannot silence the finding, and the mirror finding proves path exclusion alone is insufficient | Seed rewrite (rejected: proven vacuous by executed regex check); path exclusion only (rejected: leaves the docs/prompts mirror finding, demonstrated on this repo) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The scope mechanism silences this repo's only stale-seed-text detection | Requirement 2 forces the honest choice: conditional exclusion with an upstream carve-out, or non-blocking classification preserving detection both sides; the tradeoff is recorded, not assumed |
| Retired-name exemption over-exempts and hides a genuinely stale reference | AC-4's positive control pins that a real stale tool name in non-migration prose still flags |
| The seed edit duplicates existing guidance | Requirement 3 is extend-in-place with the existing text quoted; AC-2 asserts the caution and anti-false-report sentence remain intact |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
