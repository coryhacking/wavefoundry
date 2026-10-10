# Repair exact links when role documents move

Change ID: `204mn-bug moved-role-document-links`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-10
Wave: `204mp waveforge-follow-up`

## Rationale

The council-role migration moves owned role documents but only reports inbound links. A project-customized specialist document can retain a broken destination and stop the upgrade at docs-lint. Preserve customization while repairing destinations controlled by the migration. Addresses Waveforge public request C5 against `d11da852`, received 2026-10-08. Deliverable: framework fixes, focused regression evidence and documented compatibility behavior. This document authorizes planning only; implementation follows admission and readiness.

## Requirements

1. Derive rename pairs from COUNCIL_ROLE_RENAMES. Rewrite only local Markdown destinations resolving exactly to a confirmed moved role document, preserving labels, fragments, queries and unrelated bytes.
2. Eligible documents are current project Markdown under docs. Exclude journals/snapshots with is_history_path, and exclude resolved live wave and archive roots, staged plans, reports and architecture decisions explicitly: the shared classifier covers only journals/snapshots, not every historical record. Cover ordinary inline destinations and reference definitions (including angle-bracket destinations, optional titles, fragments and query suffixes); preserve destination escaping/percent encoding. Mask fenced and inline code before matching while retaining original offsets; do not rewrite external URLs, images or plain-text mentions. Leave unsupported or ambiguous syntax unchanged and report it, rather than guessing at a replacement.
3. Use contained reads/writes, preserve mode and user content, and refuse ambiguous source/destination collisions without overwriting either file. Preview reports edits without applying them.
4. Reconcile remaining exact links on retry when an earlier attempt moved the role document but did not finish link updates. Document partial-failure behavior; do not claim multi-file atomicity.
5. Keep the upgrade docs gate strict and preserve managed-region rendering ownership. This change does not broaden lifecycle-document migrations.

## Scope

In scope: the public request C5 and the declared review targets below.

Out of scope: other requests, native host hook classification, packaging skip-parity policy, publishing, release creation, and unrelated refactors.

## Acceptance Criteria

- [x] AC-1: An upgrade fixture with a customized specialist document linking the old council role keeps its custom content, links to the new role and passes its docs gate.
- [x] AC-2: Inline/reference destinations and fragments are repaired, while unrelated links, external URLs, code examples and historical records remain unchanged.
- [x] AC-3: A dry run changes no fixture files and reports planned edits; a successful rerun produces no additional edits.
- [x] AC-4: A retry after a completed move repairs remaining inbound links; collisions and refused paths preserve user files and produce actionable diagnostics.

## Tasks

- [x] Confirm supported Markdown destination forms and history exclusions during readiness.
- [x] Implement preview/apply exact link repair and retry discovery around the role migration.
- [x] Exercise customized docs, collisions, preserved content and interrupted retries through the upgrade driver.
- [x] Update migration documentation and collect code, QA and docs-contract evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Contract and fixtures | Implementer | Readiness | Own declared source/test edits only |
| Documentation | Technical writer | Contract | Own named documentation; coordinate shared files |
| Independent review | Code reviewer and QA reviewer | Implementation | Read-only review and evidence; additional lanes selected at Prepare |

## Serialization Points

One writer per shared file. Complete test-oracle repairs before consumers extend those tests; serialize `upgrade_extensions.py`, shared profile modules and the MCP surface specification across changes. Reviewers do not edit implementation files. Generated local surfaces are regenerated from canonical sources, never patched in lieu of seeds.

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`

## Affected Architecture Docs

docs/specs/mcp-tool-surface.md and docs/architecture/data-and-control-flow.md: role migration link ownership, preview and retry behavior.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Direct evidence for the requested compatibility behavior |
| AC-2 | required | Direct evidence for the requested compatibility behavior |
| AC-3 | required | Direct evidence for the requested compatibility behavior |
| AC-4 | required | Direct evidence for the requested compatibility behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | All14 findings independently cleared; five required delivery lanes approved. Canonical11977 tests across177 files pass with20 skips; independent QA recomputes the current matching input hash. All ACs/tasks are complete and status implemented; operator closure remains pending. | evidence/delivery-20261009-04; evidence/delivery-20261009-final-qualification |
| 2026-10-09 | Finding14 and repair start preceded atomic URI/email literal handling. Frozen27 C5 owner tests pass without skips; saved pre-autolink source detects four failures and two earlier-code controls. URI/email removal mutants and the newly pinned title-image-reference metadata mutant fail the intended byte assertions. AC-2 is complete on implementation evidence; all14 findings and final delivery approvals remain pending fresh independent review and canonical qualification. | evidence/delivery-20261009-autolink-repair; [consolidated evidence](wave.md#evidence-retention) |
| 2026-10-09 | Findings09–13 and repair starts are typed before bounded lexical/context/encoded-diagnostic repair. New4 methods/34 incoming cases pass, saved pre-repair source has24 assertion failures/ten controls; native pointer derives from the declared pair and strict default owners107/0 pass. One prior reference fixture now has a genuine definition boundary, retaining exact rewrite assertions. Source frozen and gates closed; fresh independent review and final whole-suite qualification remain pending, so AC-2 remains unchecked. | delivery-round-2.md; evidence/delivery-20261009-02; /tmp/wf-204mp-lexical-final-packet.json |
| 2026-10-09 | Fresh code/QA actual incoming preview/install/reinstall probes find valid inline HTML attribute backticks hiding ordinary links, and paragraph-continuation text misclassified as a reference definition. AC-2 reopened; complete bounded findings and primary-oracle validation are still being collected on unchanged24-path source. A separate new native-fixture literal fails the strict upstream actor census. No repair source edit or terminal judgment is recorded. | /tmp/wf-204mp-final-codeqa-extra.json; /tmp/wf-204mp-final-security-selected-public-security-controls.log |
| 2026-10-09 | Recorded03–08 repair starts preceded final container-reference, HTML, fence-info, escape and native-component repair plus canonical migration guidance correction. Final C5 owner22/0 skips; new23-case incoming preview/install/reinstall matrix, saved old-source17 failures/six controls, seven new mechanism/two diagnostic mutants detected. AC-2 complete on implementation evidence; all eight findings remain open for fresh independent review and canonical qualification. | implementation-evidence.md; evidence/delivery-20261009-repair |
| 2026-10-08 | Implemented recorded block/escape/setext repair; C5 owner17/0 skips,35 exact-byte installing/reinstall cases, four new and six recursive mutants detected. AC-2 implementation complete; both findings remain open pending fresh reverification and canonical qualification. | c5-preservation-review.md; /tmp/wf-204mp-block-c5-owner.log |
| 2026-10-08 | Fresh architecture/docs verifier confirms recursive containers pass but discovers seven required-preservation failures in ordinary inline block/escape boundaries and setext heading classification. AC-2 reopened; no terminal reverification or lane approval. New typed finding and repair start will precede another bounded mask edit, after graph207t4 implementation freezes. | /tmp/wf-204mp-independent-recursive-04-results.json; 25 installing/reinstall cases / 7 failures; final23hashes unchanged |
| 2026-10-08 | Readback: resume the existing open cycle-1 C5 repair after the phase fix. Replace ordered quote-then-list stripping with an active recursive container stack consumed in actual prefix order; retain lazy paragraph state when inner markers are omitted. Keep original offsets, contained I/O, preview and role authority unchanged. Actual installing/reinstall expected-byte cases will include the independently failing list-to-quote and partial nested-quote shapes. No AC narrowing or terminal claim. | Live current mask read; independent third-round scripts and still-open typed finding |
| 2026-10-08 | Corrected two progress rows accidentally inserted in the execution table by an unanchored table-delimiter replacement. Restored the original reviewable execution contract; tracking rows now reside only in Progress Log. No requirement or scope changed and no new source edit followed the fresh finding. | Public receipt mismatch diagnosed from changed204mn digest; corrected heading-anchored insertion |
| 2026-10-08 | Third fresh delivery round still fails ARCH-DOC-204MP-01: quote containers exposed by list prefixes are not classified recursively, and partial omitted nested quote markers reset lazy paragraph state. Both architecture/docs unsuccessful reverifications were recorded in open cycle 1, clearing no lane; code/QA also withhold approval. AC-2 reopened and status review. Root queues a unified recursive-container repair after the readiness-phase fix; stop source work with gate closed and current 23-path snapshot unchanged. | Independent architecture/docs matrix 18 cases / 3 failures / 18.493s; independent code/QA own 7 cases / 1 failure plus same-family siblings; existing owners/default/renamed remain green; /tmp/wf-204mp-ad-independent-03.log, /tmp/wf-204mp-codeqa-own-container-03.log; typed ARCH-DOC-204MP-01 failed reverifications |
| 2026-10-08 | Observe: continued cycle-1 repair classifies code at quote/list content columns while masking original offsets. Installing-driver exact-byte CRLF matrix covers 15 quoted/list/ordered/tab/fence/lazy-paragraph shapes with repeat installation. Reflect: six container-specific child-source mutants detect both code rewrites and live-link omissions; no parser dependency or authority/containment/preview changes. Fresh lane reverification remains pending and final QA awaits separately scoped graph qualification. | C5 owner 16 passed / 0 skips, 18.647s; whole upgrade owner 700 passed / 2 existing Windows junction skips, 68.727s; subprocess guards/classification/C5 42 passed / 0 skips, 64.066s; 6 container mutants and 8 existing C5 mutants detected; ownership check 523 paths; /tmp/wf-204mp-container-repair-owner-final.log, /tmp/wf-204mp-upgrade-container-owner.log, /tmp/wf-204mp-container-guards.log, /tmp/wf-204mp-container-mutants.log, /tmp/wf-204mp-container-c5-mutants.log |
| 2026-10-08 | Fresh architecture/docs and code/QA reverification found code rewriting and live-link omissions in quote/list containers. Continue the same open repair cycle 1 under its original recorded repair_start; unsuccessful reverification cleared no lane. Tool rejects duplicate starts or cycle 2 before cycle 1 completion, so no approval, waiver, or false terminal disposition was manufactured. AC-2 reopened; implement container-relative masking in the same helper/test owner. | ARCH-DOC-204MP-01 typed failed reverifications; /tmp/wf-204mp-arch-doc-nested-probe.log; /tmp/wf-204mp-fresh-codeqa-nested.log; root bounded same-cycle authorization |
| 2026-10-08 | Observe: bounded repair masks four-column space/tab code chunks at block boundaries, preserves blank continuations, and keeps indented ordinary paragraph continuation links repairable. Actual installing-driver exact-byte CRLF regression covers adjacent live, fenced, inline, space/tab/mixed code and repeat install. Reflect: no authority, containment or preview path changed; fresh architecture/docs and code/QA rechecks remain required. | C5 owner 15 passed / 0 skips, 6.271s; whole upgrade owner 699 passed / 2 existing Windows junction skips, 54.031s; 3 new actual-child masking mutants and all 8 C5 guard mutants detected; /tmp/wf-204mp-indented-repair-owner.log, /tmp/wf-204mp-upgrade-indented-owner.log, /tmp/wf-204mp-indented-mutants.log, /tmp/wf-204mp-indented-c5-mutants.log |
| 2026-10-08 | Independent delivery review found ARCH-DOC-204MP-01: actual installing driver rewrites four-space and tab-indented code examples. AC-2 reopened and status is review; architecture/docs approvals withheld. Security approved exercised authority/containment boundaries with notes; QA remains withheld for the separate graph qualification failure. No source repair yet. | Typed initial-delivery finding; render_agent_surfaces._role_link_mask_code; /tmp/wf-204mp-indented-code-probe.py; /tmp/wf-security-204mp-probes.log |
| 2026-10-08 | Qualification checkpoint: 11942-test canonical run passed every admitted owner, upgrade 698, subprocess guards and indexer; only two existing live-repository EvidencePartitionResponseTests failed with empty evidence communities. Fresh graph-only setup completed but reused unchanged clusters, and original 8-test class still reports 2 failures and 4 existing conditional skips. No fixture assertions or unrelated source were edited. Independent C1–C5 review proceeds with final QA withheld for this external graph/community qualification block. | /tmp/wf-204mp-canonical-qualified.log (399.996s); /tmp/wf-204mp-graph-refresh.log; /tmp/wf-204mp-evidence-partition-refreshed.log (11.401s); /tmp/wf-204mp-evidence-snapshot-refreshed.log; frozen 23 paths unchanged |
| 2026-10-08 | Observe: unavailable incoming helper now reports a path-free retry diagnostic and leaves the role-preview target unchanged, without launching a child; unrelated loader errors propagate. Whole upgrade owner and all breadth/routing/C5 controls are green. Reflect: preserve existing preview diagnostic behavior instead of weakening the old fixture; both deletion of the diagnostic catch and broadening it to Exception are detected. | test_upgrade_wavefoundry: 698 tests passed, 2 existing native Windows junction skips, 54.215s; guards/classification/C5: 40 passed, 0 skips, 50.002s; all 8 C5 mutants plus 2 preview error mutants caught; /tmp/wf-204mp-upgrade-final-owner.log, /tmp/wf-204mp-final-guards.log, /tmp/wf-c5-mutants-final.log, /tmp/wf-204mp-preview-error-mutants.log |
| 2026-10-08 | Thought: second canonical qualification exposed incoming-helper unavailability escaping the existing dry-run diagnostics contract. Catch only _IncomingModuleUnavailable at helper resolution; print an actionable path-free role-preview diagnostic without launching a child or writing the target, then continue other migration previews. Unexpected loader failures still propagate. | /tmp/wf-204mp-canonical-final.log; PostExtractDryRunBranchTests.test_preview_messages_say_when_no_log_was_written; new unavailable-helper and unrelated-failure controls |
| 2026-10-08 | Observe: qualification repair loads incoming subprocess_util privately and launches windowless Python through its tree-timeout helper with UTF-8 child environment, detached stdin and tolerant decode. Reflect: canonical failure was an implementation integration defect, not a guard exception; the taxonomy has one real routed row, no exclusions. Image-only/shared/collapsed/shortcut reference definitions stay unchanged and reported. | 37 focused guards/C5 tests passed, 0 skips, 48.431s; new real Popen boundary 1 passed, 0 skips, 0.962s; all 8 C5 mutants re-killed; /tmp/wf-204mp-preview-repair-focused.log, /tmp/wf-204mp-preview-launch.log, /tmp/wf-c5-mutants-repair.log; test_tree_kill_routing.py added as directly affected path |
| 2026-10-08 | Thought: canonical qualification exposed a raw preview subprocess bypassing isolation and timed-call routing. Repair only the incoming helper launch via private sibling loading, windowless interpreter, UTF-8 environment and tree timeout; preserve preview read-only behavior. Confirm image reference definitions shared with normal links remain unchanged and reported. | /tmp/wf-204mp-canonical.log; named subprocess guards; admitted C5 preview and image preservation contract |
| 2026-10-08 | Observe: exact current-doc inline/reference links now repair after byte-preserving role moves; retries require explicit new role identity. Actual installing surface phase and strict docs gate pass with customized specialist prose. Interrupted driver leaves move complete and peer unchanged, then retry repairs it. Preview from incoming scripts in a private -B child changes no target files. Reflect: file publications are individually atomic, not a multi-file transaction; unsupported destinations remain reported and history stays unchanged. | CouncilRoleLinkRepairUpgradeTests: final 11 controls / 0 skips, 16.543s; full test_upgrade_wavefoundry owner 694 / 2 existing skips, 60.428s; /tmp/wf-c5-final-focused.log and /tmp/wf-c5-upgrade-owner.log |
| 2026-10-08 | Eight guard mutants killed: delete current/history exclusions or code masking, loosen exact target, bypass retry identity or contained reads, strip encoding style, omit all-pair collision preflight, enable preview writes. Each known-bad run reached its intended named test and failed its behavior assertion; collision mutant exposed an absent old document after an earlier move. | /tmp/wf-c5-mutants.py and /tmp/wf-c5-mutants.log; tests test_destinations_preserve_suffixes_encoding_titles_and_history, test_retry_requires_new_document_role_identity, test_linked_peer_refusal_preserves_role_and_outside_content, test_percent_case_and_escaped_opening_are_preserved, test_all_pairs_preflight_before_any_role_move, test_upgrade_driver_dry_run_reports_without_target_writes |
| 2026-10-08 | Readback: repair exact local inline/reference destinations to confirmed moved council roles; keep customized bytes, modes, code examples and historical roots; isolated incoming-pack preview makes no target writes. Example: a specialist link to wave-council.md becomes council-chair.md; its prose stays untouched. Thought: plan narrow spans before moving and reconcile retry links from explicit role identity. | AC-1–4; render_agent_surfaces.py, upgrade_extensions.py, test_upgrade_wavefoundry.py |
| 2026-10-08 | Planned from public report and current source inspection; not implemented or readied | Declared source targets and request C5 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-08 | Rewrite exact owned destinations in current documentation and retain the strict docs gate. | Preserve the requested behavior and existing compatibility boundaries | Downgrading broken links to warnings leaves navigation broken; broad text replacement risks unrelated prose and historical records. |

| 2026-10-08 | Use narrow destination-span replacement with explicit record-root exclusions in addition to is_history_path. | The existing classifier covers only journals/snapshots, and docs-lint strips only simple inline/fenced syntax; neither alone implements the promised preservation contract. | Reusing the lint regex unmodified misses reference definitions and can alter examples; treating every docs file as current rewrites historical evidence. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A partial move or broad replacement can lose customization or make retries ineffective. | Use exact destination matching, byte-preservation controls, explicit collision handling and interrupted-upgrade fixtures. |

## Session Handoff

See `docs/agents/session-handoff.md`. Readiness must resolve the design choices named above before implementation.
