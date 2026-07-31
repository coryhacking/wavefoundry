# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1tz6l release-upgrade-hardening`
Title: Release Upgrade Hardening

## Objective

Make the 1.15 release and upgrade path both reliable and operator-comprehensible: review-policy
receipts must survive gardener-only metadata updates, and protocol-bridge upgrades must preserve
their safety boundary while reducing the handoff to one explicit MCP stop, one agent-driven
standalone run, and one full host restart—with machine-resolvable recovery phases continuing
automatically.

## Changes

Change ID: `1txh7-enh protocol-bridge-upgrade-handoff`
Change Status: `complete`

Change ID: `1tz6k-bug review-policy-receipt-metadata-stability`
Change Status: `complete`

Change ID: `1u0cc-bug upgrade-extract-leaks-bundle-runner-files`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-07-31

## Wave Summary

Wave `1tz6l` (Release Upgrade Hardening) delivered 3 changes: Guided One-Command Protocol-Bridge Upgrade Handoff, Stabilize Review-Policy Receipts Against Gardener Metadata, and Upgrade Extraction Leaks Bundle Runner Files Into the Project Root. Notable adjustments during implementation: Guided One-Command Protocol-Bridge Upgrade Handoff: Removed inactive protocol-bridge rollback trees from the live reconciliation corpus without a broad name exclusion.; Guided One-Command Protocol-Bridge Upgrade Handoff: Replaced the unimplemented detached-supervisor proposal with the simpler operator-stop/agent-shell/restart contract and reopened implementation scope around the field-proven gaps.; Upgrade Extraction Leaks Bundle Runner Files Into the Project Root: Filter helper `_extract_feature_members` + skip-count log implemented; ordering-guard test re-anchored; 8 regression tests added (all green targeted); seed-160/seed-010/install-block scoped-extraction companions landed; prompt surface + dashboard reference reconciled; docs-lint clean

**Changes delivered:**

- **Guided One-Command Protocol-Bridge Upgrade Handoff** (`1txh7-enh protocol-bridge-upgrade-handoff`) — 22 ACs completed. Key decisions: Preserve explicit quiescence and no self-replacement.; Make the one normal Wavefoundry zip both extractable and directly executable for the verified two-hop upgrade.
- **Stabilize Review-Policy Receipts Against Gardener Metadata** (`1tz6k-bug review-policy-receipt-metadata-stability`) — 8 ACs completed. Key decisions: Normalize only the top-level `Last verified` value.
- **Upgrade Extraction Leaks Bundle Runner Files Into the Project Root** (`1u0cc-bug upgrade-extract-leaks-bundle-runner-files`) — 5 ACs completed. Key decisions: Filter members at extraction, allowlist-based; Keep extracting the bootstrap, keep existing cleanup
## Watchpoints

- Watchpoint: normalize only the single top-level gardener-owned `Last verified` value; all substantive change
  content remains digest-significant.
- Watchpoint: reuse the existing bridge, feature runner, hashes, locks, rollback, and checkpoint authorities;
  the convenience bundle must not fork upgrade semantics.
- Watchpoint: treat native Windows, WSL2, macOS, and Linux as first-class rehearsal targets, including paths
  with spaces, backslashes, and Unicode.
- Blocking guard: keep explicit host quiescence and no-self-replacement intact; no tool may kill a host or infer
  `--confirm-hosts-stopped`.
- Blocking guard: only genuine judgment and the final tool-schema restart may stop the standalone
  runner; an empty memory worklist or a passed docs gate must not require another manual recovery.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| bridge-build-id-path-escape | do_now | no | completed | code-reviewer, architecture-reviewer, release-reviewer, wave-council-delivery |
| bridge-recovery-carriers-violate-agent-shell-multihost-contract | do_now | no | completed | docs-contract-reviewer, release-reviewer, wave-council-delivery |
| bundle-windows-backslash-payload-escape | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, wave-council-delivery |
| combined-hop-recovery-not-terminal-or-total | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer, wave-council-delivery |
| dashboard-quiescence-plan-contradicts-held-lock | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, wave-council-delivery |
| evaluator-v2-transition-unpinned | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| graph-maintenance-invalidates-upgrade-staging-receipt | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, wave-council-delivery |
| memory-id-rename-and-gate-resume-deadlock | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, wave-council-delivery |
| memory-pause-masquerades-as-docs-failure | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, wave-council-delivery |
| public-release-emits-special-upgrade-package | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer, wave-council-delivery |
| receipt-normalization-missing-from-mcp-spec | do_now | no | completed | docs-contract-reviewer, wave-council-delivery |
| release-main-bundle-wiring-unpinned | do_now | no | completed | qa-reviewer, release-reviewer, wave-council-delivery |
| release-main-does-not-enforce-single-public-package | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer, wave-council-delivery |
| release-upgrade-carriers-stale | do_now | no | completed | docs-contract-reviewer, release-reviewer, wave-council-delivery |
| retained-feature-staging-follows-existing-link | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, wave-council-delivery |
| retired-carrier-preflight-hides-complete-recovery-worklist | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer, wave-council-delivery |
| rollback-bridge-backup-leaks-into-live-reconciliation-scan | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer, wave-council-delivery |
| upgrade-created-assets-not-ignored | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer, wave-council-delivery |
| upgrade-mcp-response-exceeds-host-cap | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer, wave-council-delivery |
| upgrade-reconciliation-misses-live-guidance-and-misroutes-host-rules | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer, wave-council-delivery |
| upgrade-renders-policy-gate-without-required-baselines | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, wave-council-delivery |
| upgrade-response-cap-aggregate-bypasses | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| windows-bridge-lock-mutates-before-acquire | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, wave-council-delivery |
| windows-handoff-uses-pythonw | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer, wave-council-delivery |

*Machine review evidence — 485 records; 126 runs; 24 findings; current: do_now 24, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Prepare Review Evidence

- red-team: confirmed `policy_input_digest` hashes raw admitted-change bytes at
  `review_policy.py:343-370`, while the repository already owns a narrow leading-frontmatter
  gardener recognizer at `index_state_store.py:3187-3222`. The plan was tightened to share that
  recognition boundary rather than create a drift-prone second parser. For the upgrade path, the
  existing protocol-floor extension refuses before extraction and emits structured bridge fields,
  while `wf_upgrade_response` currently reduces nonzero exits to generic `upgrade_failed`; both
  claimed seams are real.
- docs-contract-reviewer: the combined wave preserves the two authority boundaries that matter:
  substantive change bytes remain receipt-significant, and a protocol-1 runner still cannot replace
  itself or extract a protocol-2 feature. The upgrade plan now makes structured argv authoritative
  across Windows and POSIX and presents one operator-facing package without turning legacy
  component artifacts into competing instructions.
- red-team (field-report re-Prepare): the Solaris transcript maps to live implementation seams:
  `_detect_dashboard` trusts readable lock metadata rather than testing lock ownership;
  `upgrade_wavefoundry.py` can persist `failed_phase="docs_gate"` immediately before returning the
  separately modeled `awaiting_memory_validation` state; and the public wrapper retains combined
  subprocess output. The tightened plan requires honest phase identity and bounded output. Its
  zero-work shortcut is constrained to the canonical total worklist count, not an empty page or
  missing payload, so it cannot skip unresolved judgment.
- docs-contract-reviewer (field-report re-Prepare): replacing the proposed supervisor with an
  operator-stop/agent-shell/restart sequence preserves the no-self-replacement and quiescence
  contracts while removing unnecessary process orchestration. Widened retired-guidance discovery is
  report-only outside registered or framework-owned sections, excludes closed wave history, and
  therefore does not grant the upgrader authority over project-authored prose.

Synthesis verdict: READY. The field findings are in scope, independently falsifiable, and bounded by
the existing upgrade authorities; no additional plan blocker remains.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: adding a new review-policy regex would duplicate the already hardened gardener-frontmatter recognizer and let the two authority boundaries drift — resolved by requiring a shared recognition rule and cross-consumer lookalike regression; strongest-alternative: document the existing two-command bridge flow more clearly — rejected because it would preserve generic MCP failure, multi-asset coordination, and copied-command risk while leaving the established safety boundary unchanged.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: an apparently empty memory page is not proof that the retained run has no pending judgment — resolved by requiring the canonical total worklist count and synchronized run state to be zero before automatic publication; strongest-alternative: add a detached upgrade supervisor that waits for MCP process exit — rejected because the successful Solaris run proves the agent's ordinary shell already supplies the needed out-of-process executor, while a supervisor would add cross-platform process census and recovery state without removing the mandatory final host restart.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-30: FAIL** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the 60K prose cap left `data.summary` unbounded and an executed 10,000-row fixture produced a 1,047,683-character MCP envelope; strongest-alternative: narrow the impossible claim that an incoming pack can cap an already-running 1.14 wrapper, preserve a compact terminal bridge result, and use the agent's ordinary shell as the no-operator-command overflow fallback; additional blockers: precise live `.wavefoundry/` coverage and every-attached-host restart wording.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: bounding only raw output or list fields still allowed structured scalar/nested and bridge-prose payloads to exceed the host cap — resolved by bounding all repo-sized collections and oversized structured values, omitting unknown bridge detail with counts, and proving the complete public envelope under three adversarial fixtures; strongest-alternative: promise a retrofit of the already-running protocol-1 wrapper — rejected as impossible, with an honest agent-shell fallback that requires no operator-entered terminal command.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-31: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; scope: late admission of `1u0cc-bug upgrade-extract-leaks-bundle-runner-files` into the readied wave, both seats run in isolation against the plan with code-grounded verification of the extractall site, cleanup helper, bundle layout constants, and install-surface claims; strongest-challenge: the plan's original out-of-scope rationale claimed the installer prompt already instructs runner-member cleanup, which no shipped surface substantiates, so the field defect would have survived through the documented manual install and unzip-fallback paths — resolved by bringing seed-160/seed-010/install-block scoped-extraction companions into scope; strongest-alternative: hash-guarded post-extract deletion of runner names reusable by manual paths — rejected for the automated path because allowlist filtering never writes the debris and never risks collision destruction, while manual paths get scoped extraction instructions instead of any delete list.)

## Implementation Progress

- **Thought — 2026-07-30:** implement the receipt canonicalization first because it is the smaller
  authority change and gives the wave a stable lifecycle receipt before the larger release-artifact
  work. Then compose the existing bridge components into the zipapp, add typed refusal promotion,
  reconcile the canonical upgrade guidance, and verify focused modules before the full suite.
- **Gapfill — 2026-07-30:** MCP definitions, references, outlines, and targeted reads established the
  implementation seams. Several combined test-file reads exceeded the response cap, so subsequent
  narrow shell reads are limited to the already identified test classes and builder ranges; no broad
  grep-based discovery substitutes for MCP retrieval.
- **Observe — 2026-07-30:** the receipt implementation now shares one stdlib-only frontmatter
  recognizer between drift detection and review-policy hashing, fails closed on duplicate or
  malformed fields, and bumps evaluator semantics to v2. Focused review-policy verification passed
  22/22; the public lifecycle regression and contract docs remain before this change is complete.
- **Observe — 2026-07-30:** the public midnight regression now keeps receipt currency aligned across
  Prepare, Review, Implement, and Close, while the substantive mutation control still goes stale.
  Moving the recognizer also exposed and repaired one secondary drift-parser reference; doc-drift
  verification passes 91/91.
- **Observe — 2026-07-30:** the release builder now presents one `.pyz` bridge asset. The bundle
  materializes only after explicit confirmation and all three locks, reuses the canonical bootstrap,
  retains the exact feature pack for checkpoint recovery, executes the isolated hash-pinned runner
  once, and returns one bounded structured result. A local `v1.14.0` checkout rehearsal reached the
  real retained docs-gate checkpoint with exact resume argv and rollback state.
- **Observe — 2026-07-30:** canonical verification is green: 6,509 tests across 61 files, docs-lint
  clean, focused protocol/receipt/upgrade tests green, and framework/seed edit gates closed.
- **Observe — 2026-07-30:** delivery review found eight bounded correctness and evidence gaps. All
  were repaired in cycle 1: bridge identifiers and bundle payload names now validate across POSIX
  and Windows before mutation; Windows handoff and lock behavior are deterministic; combined-hop
  recovery is total; evaluator migration, closed-ledger immutability, release-entrypoint wiring, and
  the public receipt contract are pinned. Both original path-escape probes now reject at validation.
  Canonical verification is green at 6,518 tests across 61 files; docs-lint is clean and both edit
  gates are closed.
- **Observe — 2026-07-30:** the fresh carrier census and code/architecture pass found two final
  gaps: stale release/operator prose and predictable retained-feature staging. The official
  carriers now distinguish protocol-2 feature-zip use from the protocol-1→2 bundle across every
  current release surface. Feature retention now uses an exclusive regular temporary file and
  verifies the final contained archive; the full-install regression proves an old predictable
  staging link cannot change an external sentinel. The public Windows refusal payload also pins the
  console interpreter at its call site. Final canonical verification is 6,520/6,520 across 61
  files; docs-lint is clean and both edit gates are closed.
- **Observe — 2026-07-30:** the first external 1.14.0 upgrade proved the single-package bridge but
  exposed two adoption gaps: lifecycle preflight revealed custom retired prose one token per retry,
  and surface rendering activated review-policy validation without rendering portable baselines for
  older direct docs. The repair preserves fail-closed project prose, returns the complete token/line
  worklist at once, and gives every existing carrier a separate marker-owned renderer companion.
  The production validator now passes against the actual v1.14.0 carrier family after one render;
  retry is byte-stable, absent optional docs remain absent, the full upgrade/policy/renderer set is
  444/444, the canonical suite is 6,524/6,524, and docs-lint is clean.
- **Observe — 2026-07-30:** the Solaris field-report repairs are implemented. Upgrade now keeps
  docs success distinct from a memory pause, runs one bounded canonical memory batch before asking
  for judgment, caps MCP-visible output while preserving the complete log, gives known lifecycle
  carriers deterministic replacement previews, reports other live retired prose without rewriting
  it, treats the canonical dashboard lifetime lock as authoritative, and manages rollback/upgrade
  artifacts without hiding project-owned paths. Focused affected modules pass 466/466; the
  canonical isolated suite passes 6,542/6,542 across 61 files; docs-lint is clean.
- **Observe — 2026-07-30:** fresh amended-plan review found and closed four contract gaps before
  approval. The final public response boundary caps raw output, list collections, oversized
  scalar/nested summary values, and bridge prose/unknown fields; three independent probes stayed
  between 61K and 85K under the named 100K cap while preserving terminal and recovery authority.
  The protocol-1 limitation is explicit, live `.wavefoundry/` guidance is scanned without scanning
  generated internals, every host carrier uses the plural restart rule, and the rendered policy
  marker is byte-identical to canonical source. Focused repair verification passes 91/91; the final
  canonical suite passes 6,545/6,545 across 61 files, including 1,522 server-tool tests.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 143 | 3,092,498 |
| implement | 222 | 4,455,085 |
| review | 884 | 31,794,809 |
| **Total** | **1,249** | **39,342,392** |

<!-- wave:context-efficiency-state {"generation":1184,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":222,"content_source_credit":5103764,"derived_artifact_credit":0,"direct_net":4455085,"estimated_tokens_saved":4455085,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6976,"response_debit":643064,"source_credit_count":156,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1361},"plan":{"calls":143,"content_source_credit":3357558,"derived_artifact_credit":3230,"direct_net":3092498,"estimated_tokens_saved":3092498,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7990,"response_debit":273902,"source_credit_count":127,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13602},"review":{"calls":884,"content_source_credit":34396578,"derived_artifact_credit":113409,"direct_net":31794809,"estimated_tokens_saved":31794809,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":172896,"response_debit":2543628,"source_credit_count":812,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1249,"content_source_credit":42857900,"derived_artifact_credit":116639,"direct_net":39342392,"estimated_tokens_saved":39342392,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":187862,"response_debit":3460594,"source_credit_count":1095,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":16309},"wave_id":"1tz6l release-upgrade-hardening"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 112 | 0 | 13 | 41611495 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":41611495,"surfaced_events":112} -->
<!-- wave:exploration-avoided end -->
