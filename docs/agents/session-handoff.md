# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-08-21

## Active wave: none

### Last closed: `1vwyc prompt-surface-correctness` (CLOSED 2026-08-21 on explicit operator instruction; tree uncommitted)

`1vwyc` delivered one change, `1vwyb-bug seed-role-doc-paths-stale`: six seed citations repointed
from `docs/agents/<name>.md` to `docs/agents/specialists/<name>.md` (seed-160 lines 178, 179, 490,
491, 517 and seed-237 line 71; wave-council x4, archetype-council x2). The flat-layout
accommodation at seed-160 lines 191 and 489 was kept unchanged by explicit Decision Log entry. All
five ACs completed with executed evidence: AC-2 checked against `canonical_role_paths()` with 0
violations, AC-4 digest sweeps showed only the wave's three bookkeeping files changed, docs-lint
clean, `audit_agent_surfaces()` finding_count 0 before and after, full suite 7464 tests across 64
files OK with `--no-cache` (run twice independently).

Ledger history worth knowing: implementation bookkeeping superseded the readiness receipt (designed
mechanic; final receipt `review-policy-e1144cedacf6a93ba051`), and both readiness signoffs were
re-recorded from fresh independent contexts using an inverse-transform digest proof (the change doc
with the enumerated bookkeeping inverted reproduces the pre-implementation digest byte-for-byte)
plus falsification probes. The delivery-phase docs-contract review APPROVE
(`ev-approval-docs-contract-reviewer-3`) came from a third fresh context that re-verified every AC
with its own checker, sweeps, and uncached suite run, and swept the whole seed corpus for residual
flat-path citations (zero). Operator signoff (`ev-approval-operator-signoff`) was recorded on the
explicit close instruction; `wf_close_wave(mode='create')` transitioned the wave with clean lint
and no diagnostics.

Deferred with reasons recorded in the change doc and `docs/plans/` withdrawal banners: the
recurrence guard (needs the flat-layout accommodation question settled first; three designs were
blocked on evidence), `1vvs3`, `1vwyd`, and `1vwye`. The `1vwyc` CHANGELOG bullet is staged under
`## [1.19.0]`. Nothing is committed; the commit is operator-owned.

### Last closed: `1vvei techdocs-python-only-validation` (CLOSED 2026-08-21)

`1vvei` removed external
TechDocs render/build/preview commands from the live workflow carriers, keeps rendering
operator-owned, and adds a bounded Python-only parser for plain and quoted nav paths with spaces.
The delivery review found and repaired one fail-closed YAML-scalar gap (`QA-DEL-1`); all seven ACs
and all tasks are complete, and all specialist, council, and operator approvals are recorded. Final
evidence: 84 warning-strict audit tests and 7,464 framework tests across 64 files passed; docs lint
and diff checks are clean; no dependency manifest changed.

`1vqqi techdocs-audit-and-review-branch` is **CLOSED** (2026-08-19). All seven approvals are
recorded in its ledger: the four delivery lanes, `wave-council-delivery`, `wave-council-readiness`
and operator signoff. Its 339-record `events.jsonl` is an append-only archive; do not edit it.

`1vt2q mcp-reload-notification-delivery` is **CLOSED** (2026-08-20). It delivered truthful MCP
tool-list notification outcomes for direct reloads while preserving scheduled delivery for the
synchronous upgrade path:

- **`1vt2q mcp-reload-notification-delivery`** carries `1vt2p-bug`: `wf_reload_mcp` cannot observe
  or report the tool-list notification it schedules. **Its original root cause was falsified by
  execution** (a garbage-collection hazard that does not occur on this stack), and the plan was
  re-cut around making the direct tool `async def` and awaiting the send while the synchronous
  upgrade caller retains explicit scheduling. Implementation and all five typed finding chains are
  terminal; all four specialist delivery approvals and operator signoff are recorded.

`1vry5 techdocs-pattern-fidelity` is **CLOSED** (2026-08-20).

Release state: the closed-wave entries, including `1vvei`, are assigned to the planned
**1.19.0** release in `CHANGELOG.md` (the never-published 1.18.x numbers are skipped: test packs
stamped 1.18.0+pkff and 1.18.1+pkjs escaped to a target repo, so 1.19.0 keeps upgrade selection
unambiguous). The tree is uncommitted.

**Current 1vt2q evidence:** a fresh stdio MCP process observed the real
`ToolListChangedNotification`, then refetched and saw an injected tool. The final full suite passed
7,459 tests across 64 files; the post-review carrier repair passed 147 focused reload, packaging,
and shipped-reference tests plus clean docs lint. The accepted cancellation gap remains explicit:
canceling the direct request can drop its awaited send, while the scheduled upgrade-path control
survives caller cancellation; no retry is attempted because it could duplicate a partially sent
frame.

The `1vqqi` delivery history below is retained as background.

- **DEL-1 (blocking)** `parse_mkdocs` read canonical YAML as empty and still reported `clean`:
  a zero-indent block sequence (what PyYAML and js-yaml emit by default) ended every sub-block
  collector at the first unindented line. Repaired with a shared `_in_sub_block` predicate,
  section-header rejection in `nav`, and an explicit `mkdocs_shape` degrade for a quoted scalar
  spanning lines.
- **DEL-2 (blocking)** the matcher disagreed with git in BOTH directions on character classes and
  mid-token `**`; the AC-2 cross-check had been scoped to a corpus that could not reach either
  family. Repaired and re-measured at 399 single-pattern comparisons over 19 families plus 1457
  whole-block paths, 0 disagreements.
- **DEL-3 (blocking)** four AC-named proofs could not fail (mutants survived) and two were absent.
  Repaired; the symlink case was rebuilt around a symlinked FILE (SUPERSEDED later in the wave by
  RT-3: enumeration moved from `rglob` to `os.walk(followlinks=True)` like MkDocs, so
  in-root symlinked DIRECTORIES are followed too and containment is the only guard).
- **DEL-4 (blocking)** the read-tier MCP envelope was unbounded (1.8MB / 12001 findings). Now
  capped with `findings_total`, `findings_omitted` and `truncated`; `survivor_count` stays true.
- **DEL-5 (blocking)** `not_applicable` forced exit 0 over real findings, and the subcommand was
  the only one with no help description. Exit status now follows content.
- **DEL-6 / DEL-7 (non-blocking)** ten documentation and carrier defects, and AC-8's second
  dogfood occurrence left undecided under a completed task; both repaired.

**Historical completion:** `1vqqi` closed after the required readiness, specialist delivery,
delivery-council, and operator approvals were recorded on its final receipt.

### Last closed: `1vj4e backstage-techdocs-baseline` (CLOSED 2026-08-18 on explicit operator instruction; tree uncommitted)

**Delivery review (2026-08-18) — four required lanes, each run in fresh independent contexts across two repair cycles; all four APPROVED.** Six findings, all resolved with executed evidence:

- **DEL-1 (blocking)** stale `path:line` locators on the two dogfood-published pages, found independently by all four lanes; caused by this wave's own Requirement 10 amendment inserting 185 lines into `server_impl.py` after the pages were authored. Repaired by converting the churn-heavy anchors to symbol form.
- **DEL-6 (blocking)** the DEL-1 repair was incomplete: a substring sweep never saw the tool-family table's 20 bare parenthesized numbers, and the two recomputed ranges were re-broken by exactly +33 when the sibling DEL-2 repair inserted `techdocs_member_states` above them. Repaired and re-resolved LAST, after every other edit.
- **DEL-2** failure paths misreported the tree (`written_paths: []` while two members were on disk; the mixed-only classifier feeding the failure envelope) and an `OSError` escaped both entries. Repaired with `TechdocsWriteFailed` carrying what the run wrote and the new public `techdocs_member_states`.
- **DEL-5** `UnicodeDecodeError` is a `ValueError`, so a non-UTF-8 target-local template still escaped; the module write loop now normalizes it too.
- **DEL-3** two shipped "CLI only" claims the in-wave MCP tool contradicts (module docstring, `install-assets.md`), plus the guard test's own name.
- **DEL-4** the framework-generic seed-178 contract asked for line-range citations nothing keeps true; Step 2 now prefers the symbol form and Step 3 requires re-resolution after all other edits, both literal-pinned in the seed AND in the self-hosted twin.

**Verification:** full suite 7349 tests / 63 files OK; docs-lint clean; published-page locators re-resolved after all edits at 0 unresolvable (52 enumerated by the architecture lane with an exact-span oracle, corroborated by docs-contract). `1vmpz` AC-3 and the dogfood task are `[x]`; AC-3's link-boundary clause was narrowed in place and carries a status note naming the one accepted exception and the ledger record `ev-approval-docs-contract-reviewer-6` that holds the dogfood evidence.

**Readiness re-recorded:** the AC-3 note re-digested the receipt (designed mechanic). A delta-scoped two-seat council (red-team + docs-contract) PASSED with conditions, all applied; `wave-council-readiness` recorded as `ev-approval-wave-council-readiness-7`.

**Closed:** operator signoff recorded as `ev-approval-operator-signoff` on the explicit close instruction; `wf_close_wave(mode='create')` transitioned the wave to `closed` with a clean dry-run and lint. Nothing is committed — the commit is operator-owned.

**Next:**
1. Commit the tree when ready (61 uncommitted entries at close, spanning this wave and the earlier closed-but-uncommitted `1viyu`).
2. At release, rename `CHANGELOG.md` `## [Unreleased]` to `## [1.17.2] - <date>` (`build_pack --version` needs the exact heading) and disclose that a new MCP tool appears to a host only after a reconnect.
3. Done: `1vmt2-enh` was amended and admitted as wave `1vqqi` (see the active-wave section above).

**Lessons recorded as memory:** `1vqqy-mem` (the techdocs family must normalize every exception its write loop can raise, and a caller-set change must reach the docstring, the block comment and `install-assets.md`) and `1vo1a-mem` (a citation sweep must cover every surface form, run last, and not be guarded only by its author's own checker).

## Open questions / Deferred decisions

- **Release:** publish the accumulated closed-wave changes as **1.19.0**; update the dated heading if the actual release date differs before packaging.
- **Framework follow-ups found during 1vj4e memory curation (not admitted, plan fresh):** `memory_validate`'s missing-target guard checks the CANDIDATE's `target_refs` rather than `rewrite_targets`, so a draft with dangling auto-derived targets cannot be corrected in place and `rewrite` collapses to `reject` (hit live on `1voan-mem`, whose targets were a reviewer's scratch scripts). And `memory_supply`'s repeated-repairs deriver extracts targets from literal `<name>.py` tokens, so it is blind to symbol-form citations: it attributed this wave's `render_agent_surfaces.py` repairs to DEL-1 and DEL-3 while the real ones were DEL-2, DEL-3 and DEL-5. That matters because DEL-4 of this same wave made the symbol form the PREFERRED citation style, so the deriver will under-attribute more as targets adopt it.
- **Editorial residuals accepted in 1vj4e (not defects):** `upgrade_wavefoundry.py`'s module docstring documents exit codes 0-3 while code 4 is live (the published page's claim is carried by its `wf_upgrade` anchor); `docs/architecture/cross-cutting-concerns.md` still documents the removed `dashboard.auto_index` setting, as do `dashboard-install-upgrade.md` and `dashboard-adapter-model.md`; a mid-write I/O failure can leave a truncated member that the marker rule classifies as project-owned, which the missing-only rerun will not repair (inherited from the non-atomic write helper, and the operator does get the partial advisory naming the file).
- **Admitted (wave `1vqqi`, 2026-08-18):** the read-tier `wf_techdocs_audit` MCP tool + `wf techdocs-audit` CLI over `techdocs_audit_lib.py`, and the review-only branch of **Refresh TechDocs**. The change doc now lives at `docs/waves/1vqqi techdocs-audit-and-review-branch/1vmt2-enh techdocs-audit-tool-and-review-only-branch.md`. The exact-symbol-span citation requirement that this note previously carried was **deferred out of scope** by that wave's readiness council (a containment test is indistinguishable from overlap on the real defect corpus, and there are six locator forms rather than three); an enforced `wave_lint_lib` citation validator is the follow-up that would replace it.
- **Deferred by design (1vj4e):** opt-in auto-generation of the trio at setup/upgrade behind a workflow-config flag (reuse `classify_techdocs_baseline` for the upgrade summary). The `wf_techdocs_baseline` MCP tool is IN this wave (1vj4d Requirement 10 / AC-8, operator decision 2026-08-18; delta readiness pass on receipt `review-policy-fa9da5386ecaa3d7be1f`).
- **Follow-up, now MINTED as `1vt2s-enh codebase-map-area-agents-prose-paths` (was prose only):** `gen_codebase_map` should emit per-area `AGENTS.md` references as prose paths rather than hyperlinks, which takes this repository's dogfood from 2 findings to 0. Wave `1vqqi` recorded the standing-explanation branch for both occurrences; that decision stands and this change resolves the tension rather than restating it.
- **Carried from 1viyu:** upgrade disclosure for metadata-less lifecycle prompt copies; RTD-2 shared install-asset resolve/stamp helper; framework README journal prose; `memory-review.prompt.md` static date; `pending_lint.note` wording.
- **Observation:** the semantic index reported `index_not_ready` during the dogfood (guru fell back to file-based tools); verified current with `index_health()` later the same day.

## Older closed, uncommitted waves

`1viyu` (closed 2026-08-18, uncommitted, four bug changes from the fresh-install field report) and `1uwpf`, `1usqm`, `1uugh`, `1ur6o` (closed 2026-08-10) plus the 1.17.x waves were recorded in earlier handoffs; their carried-forward findings live in their wave records (`docs/waves/<id>/wave.md` Watchpoints) and in `docs/plans/1us4q-bug ...` (parked, do not re-attempt without its Progress Log).

## Current Session

**Active wave:** *(none)*
