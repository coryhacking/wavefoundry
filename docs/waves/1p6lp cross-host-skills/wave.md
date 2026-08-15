# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-15

wave-id: `1p6lp cross-host-skills`
Title: Cross Host Skills

## Objective

Treat skills as a first-class, cross-host surface. Today they're two ad-hoc, inconsistent paths (Codex `auto-guru` with frontmatter; Claude `upgrade-wave` without, a flat file current Claude Code likely does not even load) and an incomplete catalog; meanwhile `SKILL.md` has converged into a cross-tool standard (Codex/Claude/Antigravity, all project-local). This wave builds **one skill registry + a shared `SKILL.md` emitter** (change `1p6lo`), migrates the two existing skills onto it with cross-host parity and `wf-` names (incl. Antigravity, deferred from `1p6l5`), promotes standalone red-team review to an operator command (change `1v877`), and adds the operator-curated set of ten **`wf-` lifecycle-command skills** (change `1p6lw`). When it closes, Wavefoundry renders consistent, `/wf`-discoverable skills across the skill-supporting hosts from one source.

## Changes

Change ID: `1p6lo-enh unified-cross-host-skill-rendering`
Change Status: `implemented`

Change ID: `1p6lw-enh core-lifecycle-command-skills`
Change Status: `implemented`

Change ID: `1v877-enh red-team-standalone-review-command`
Change Status: `implemented`

Completed At: 2026-08-15

## Wave Summary

Wave `1p6lp` (Cross Host Skills) delivered 3 changes: Unified cross-host skill rendering (SKILL.md registry), Core lifecycle-command skills (the `wf-` operator loop), and Red-team standalone review command. Notable adjustments during implementation: Unified cross-host skill rendering (SKILL.md registry): Revived from parked state. Line refs re-verified (constant `:308`, write `:1370`; `render_upgrade_skill` `:2085`/`:2152`; maintenance pin `:384`); census gained the conditional agent-role carrier recognition (`render_agent_surfaces.py:206`); added the `wf-` namespace requirement + renames (`auto-guru`→`wf-guru`, `upgrade-wave`→`wf-upgrade`); resolved body-sourcing open question to thin pointers.; Unified cross-host skill rendering (SKILL.md registry): Implemented. Registry (`Skill` dataclass, `SKILL_REGISTRY`, `render_skills`) lives in `render_agent_surfaces.py` (open question 2 resolved per recommendation); called before the Guru gate so lifecycle skills are not Guru-gated; carrier-region graft keeps re-renders byte-convergent (wf-guru on Codex is also a review carrier). `wf-upgrade` given cross-host parity with a host-neutral body (open question 3 resolved: the old body was already host-neutral apart from its title). Cursor stays on its rule (open question 1: status quo kept). Maintenance guard now covers the `wf-` skill prefix on all three hosts, replacing the single exact path. Self-hosted surfaces re-rendered: old paths removed, `wf-guru`/`wf-upgrade` present on `.codex`/`.claude`/`.agents`; second render writes nothing. Focused tests: 197 across 4 files OK; Claude Code live-discovered both skills.; Unified cross-host skill rendering (SKILL.md registry): Delivery-review finding, repaired in-cycle (qa lane): the rendered-hook maintenance-guard prefix change had no pinning test (nor did the old exact path it replaced). Assertions added to the rendered-hook fixture asserting the three `wf-` prefixes present and the retired flat path absent; executed.

**Changes delivered:**

- **Unified cross-host skill rendering (SKILL.md registry)** (`1p6lo-enh unified-cross-host-skill-rendering`) — 7 ACs completed. Key decisions: Build one skill registry + shared `SKILL.md` emitter; migrate both existing skills onto it.; Split mechanism (this change) from the lifecycle-command skill *content* (sibling change).
- **Core lifecycle-command skills (the `wf-` operator loop)** (`1p6lw-enh core-lifecycle-command-skills`) — 6 ACs completed. Key decisions: Scope to the core 5-step loop (operator-chosen).; Thin-pointer bodies → backing prompt + MCP tool.
- **Red-team standalone review command** (`1v877-enh red-team-standalone-review-command`) — 5 ACs completed. Key decisions: Promote red-team-in-isolation to an operator command via a new seed in the operator-command band.; The command records no signoffs and satisfies no gate.
## Watchpoints

- **Sequencing:** `1p6lo` (the registry/emitter) lands first; `1v877` (the red-team command) is independent of it but must land before or with `1p6lw`, whose `wf-council` skill points at the new prompt. `1p6lw` lands last: it is **BLOCKED** on both `1p6lo` (registry) and `1v877` (third pointer target).
- **`SKILL.md` is a cross-tool standard** (frontmatter `name`/`description` + body + optional `scripts/`/`examples/`/`resources/`): Codex `.codex/skills/<name>/SKILL.md`, Claude `.claude/skills/<name>/SKILL.md`, Antigravity `.agents/skills/<name>/SKILL.md` (all project-local). Author once, emit per host.
- **Migration gotchas:** the existing Claude `upgrade-wave` is a *flat, frontmatter-less* `.claude/skills/upgrade-wave.md`; standardizing to `wf-upgrade/SKILL.md` + frontmatter must stale-clean the old path and update `is_framework_maintenance_surface` (`render_platform_surfaces.py:384`). The `auto-guru` to `wf-guru` rename must likewise stale-clean `.codex/skills/auto-guru/` and follow the conditional review-protocol carrier recognition (`render_agent_surfaces.py:206`).
- **Naming:** all registry skills are `wf-` kebab-case (operator direction 2026-08-14); the two migrated skills rename to `wf-guru` and `wf-upgrade` in the same move.
- **Gating:** per-skill; `wf-guru` requires `docs/agents/guru.md` (guru_available); `wf-upgrade` is maintenance (preserve its current ungated-on-guru behavior, host-dir-aware); the ten `1p6lw` lifecycle skills are host-dir-gated only. `1v877` grants no review authority: the red-team command records no signoffs and satisfies no gate.
- **Open questions** (in `1p6lo`): Cursor inclusion; registry home (`render_agent_surfaces.py` recommended); `wf-upgrade` cross-host parity vs Claude-only (body is Claude-specific). Body sourcing is resolved: thin pointers.
- **Follow-up:** `1p6lw` was re-curated 2026-08-14 to ten skills (core loop + Interrogate, Evaluate, Memory review, Pause, and the `wf-council` router over the three on-demand review forms). Still deferred, with reasons recorded in `1p6lw` Scope: Package (repo-conditional gating), dedicated archetype/red-team skills (router covers them), single-change variants, per-kind planning skills, single-call lifecycle plumbing, install/migration one-timers.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-14: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the plan's rename census was incomplete, citing two rename-following sites while the tree holds at least five (tier-3 destinations list `render_agent_surfaces.py:1094`, seeds 050/160 under `seed_edit_allowed`, `platform-mapping.md` wrapper-eligibility prose, and the `is_framework_maintenance_surface` pin living inside a rendered hook template so already-installed target repos keep the old path until upgraded), repaired before readiness by recording the full census in `1p6lo` Requirement 5; strongest-alternative: keep the two migrated skills un-renamed to shrink the blast radius, rejected because `/wf` discoverability depends on the whole family carrying the prefix and the migration already rewrites both files, so a later rename would repeat the same census)

Seat evidence (code-grounded, verified against the tree 2026-08-14):

- red-team: every load-bearing claim in both change docs re-resolved against HEAD: `CODEX_AUTO_GURU_SKILL` (`render_agent_surfaces.py:308`, write `:1370`), `render_upgrade_skill` (`render_platform_surfaces.py:2085`, call `:2152`), maintenance pin (`:384`), carrier candidates (`render_agent_surfaces.py:206`), all nine backing prompt docs present on disk, `memory-review`/`pause-wave` prompt tool citations confirmed by grep, `.agents/` present so Antigravity emission is live in this repo. Census gap found and repaired in-session (see strongest-challenge).
- security-reviewer: no trust-boundary change. Skills are read-only rendered instruction surfaces; the thin-pointer bodies carry gate reminders (operator-owned close, stage gate) that restate existing boundaries rather than weaken them; the renderer-owned permission allowlist channel (`1u2az`) is untouched by this render path; no secret material enters skill bodies. No findings.
- docs-contract-reviewer: catalog obligations are named in both change docs (AGENTS.md Tier-3 table, `platform-mapping.md` per-host rows); seed edits (050/160, audit 040) are scoped under the `seed_edit_allowed` gate; skills point at stable `docs/prompts/<command>.prompt.md` paths that survive re-render, honoring the thin-pointer no-drift contract; docs-lint passes on the refreshed docs. No findings.

- **Prepare-phase Wave Council [prepare-council] — 2026-08-14: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the new `wf-council` router and `1v877` command could blur the review-authority boundary by making an adversarial pass feel like a recorded review, mitigated by `1v877` AC-5 pinning no-signoff/no-gate at required priority and the wave gating watchpoint stating the command grants no review authority; strongest-alternative: dedicated `wf-archetype-council` and `wf-red-team` skills instead of one router, rejected because their descriptions would overlap each other and Wave Council, which is this change's own recorded top risk)

Delta seat evidence for the scope expansion (change `1v877` admitted + tenth skill `wf-council`), code-grounded 2026-08-14:

- red-team: `1v877`'s load-bearing claims re-resolved against HEAD: the specialist doc defines seven standalone modes plus two council-bound modes and an Output Shape section (`docs/agents/specialists/red-team.md`); dangling reach-fors confirmed at `archetype-council.prompt.md:17/:26/:89` and `council-review.prompt.md:21`; seeds 225/236/237 located; seed number 177 verified free (band holds 170/175/176); `docs/prompts/prompt-surface-manifest.json` exists as claimed. `1p6lw`'s two existing `wf-council` pointer targets exist; the third is `1v877`'s deliverable with the dependency recorded. No unrepaired findings.
- docs-contract-reviewer: `1v877` AC Priority populated at plan time per the scaffold's receipt warning; the no-signoff boundary mirrors the Archetype precedent and expands no review authority; catalog obligations (index.md, AGENTS.md shortcut table, manifest regeneration) are named requirements; `1p6lw` counts, ACs, dependencies, decision log, and risks were reconciled to ten skills. No findings.

- **Delivery-phase Wave Council [delivery-council] — 2026-08-14: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: the transition window in half-upgraded target repos, where an old rendered hook still guards only the retired flat path while new `wf-` skills sit unguarded until the next re-render, judged bounded because skills are instruction files, the render self-heals, and the window is disclosed as a transition note in `1p6lo` Requirement 5; strongest-alternative: a standalone `render_skills.py` module instead of consolidating into `render_agent_surfaces.py`, rejected because that module already owned tier-3 skill emission and the consolidation makes the renderer the single writer of every skill surface, which the prior two-writer split was the defect)

Delivery seat evidence (code-grounded, probes executed 2026-08-14):

- red-team (council-adversarial-primer, standard depth): strongest challenge and alternative above; primer questions resolved by probe: no test or manifest still pins the retired flat path (grep clean after the guard-assertion repair), and the pack ships framework source only, so no skill file enters the distribution zip.
- code-reviewer: final `render_skills` re-read against its consumers; the region graft uses the reconcilers' own upsert functions so end-state bytes match (executed proof: second full render writes an empty manifest, and `test_second_full_render_is_convergent` pins it); `_skill_output_destinations` mirrors the emit gates exactly; the retired `render_upgrade_skill`/`CODEX_AUTO_GURU_SKILL` writers have zero remaining references. Diff census: exactly five framework scripts changed (two renderers, three test files). No findings.
- qa-reviewer: every required AC across the three change docs re-checked against executed evidence, not checkbox state (full suite 7239/62 OK `suite-1p6lp-2.log`; convergence manifest; live host discovery of all twelve skills; reach-for sweep; `wf_get_prompt` resolution). The containment defect has an executed falsification pair: the pre-fix code fails two setup/upgrade integration tests (`suite-1p6lp.log`) and the post-fix code passes them plus the new regression (`t-fix.log`). One finding, repaired in-cycle: the rendered-hook maintenance-guard prefix change shipped with no pinning test (also true of the old exact path it replaced); assertions added to the rendered-hook fixture in `test_render_platform_surfaces.py` and executed (94 tests OK, `t-guard.log`). No `[~]` ACs exist; AC priority tables match delivered scope.
- security-reviewer: deletion containment now refuses symlink escapes before any unlink (regression executed: outside sentinel survives); the maintenance guard widens to the `wf-` prefix on three hosts while leaving operator skills outside the namespace unguarded, verified in the rendered hook body and now test-pinned; the permissions surface is untouched (zero diff lines against `render_claude_permissions`/provenance/write-tier); `1v877` adds no signoff vocabulary and the review-authority modules have no diff. No open findings.
- docs-contract-reviewer: registry-to-catalog parity executed (12/12 skill names present in both AGENTS.md and `platform-mapping.md`; manifest holds 20 rows including Red-team review and parses as JSON); seed edits mirrored in their rendered docs (236/237/225 cross-refs, the specialist doc's `improvement-review` drift repaired toward the seed); docs-lint clean after gardening. No findings.
- architecture-reviewer (rotating): the ownership shift is the right direction; render_agent_surfaces becomes the single skill writer and render_platform_surfaces keeps host plumbing, with the import direction unchanged. Strongest unconsidered alternative recorded in the verdict line; second alternative considered and declined: guru-wrapper parity suggests `.claude/agents/guru.md` could also become a registry entry, deferred because subagent wrappers carry a different schema (`tools:` allowlists) and their own carrier governance. No findings.

## Review Evidence

- wave-council-readiness: approved (2026-08-14 — prepare-phase council PASS above; three-seat council (red-team fixed, docs-contract-reviewer rotating, security-reviewer from the initial brief derivation) run inline against the refreshed `1p6lo`/`1p6lw` change docs and this wave record; the one census finding was repaired in the change doc before this approval)
- wave-council-delivery: approved (2026-08-14 — delivery-phase council PASS above; six-seat council run inline at standard primer depth; the one qa finding, an untested rendered-hook guard change, was repaired and re-executed in the same cycle; full suite 7239 tests across 62 files OK)
- code-reviewer: approved (2026-08-14 — delivery seat evidence above; convergence and retirement claims executed, diff census exact)
- qa-reviewer: approved (2026-08-14 — delivery seat evidence above; executed falsification pair for the containment defect; guard coverage gap found and repaired in-cycle)
- security-reviewer: approved (2026-08-14 — delivery seat evidence above; containment regression executed, guard polarity test-pinned, permissions surface untouched)
- docs-contract-reviewer: approved (2026-08-14 — delivery seat evidence above; parity probes executed, lint clean)
- architecture-reviewer: approved (2026-08-14 — delivery seat evidence above; single-writer consolidation endorsed)
- wave-council-readiness: approved (2026-08-14 — refreshed for the same-day scope expansion: change `1v877` admitted and `1p6lw` re-curated to ten skills with the `wf-council` router; delta council PASS recorded above (red-team fixed, docs-contract-reviewer rotating); all delta claims verified code-grounded before this approval)
- operator-signoff: approved (2026-08-15 — operator explicitly invoked Close wave via the `/wf-close-wave` skill after the delivery council PASS and the follow-up wave `1ve3a` was readied)

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 16 | 348,830 |
| implement | 93 | 131,881 |
| review | 10 | 0 |
| **Total** | **119** | **480,711** |

<!-- wave:context-efficiency-state {"generation":113,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":93,"content_source_credit":168599,"derived_artifact_credit":0,"direct_net":131881,"estimated_tokens_saved":131881,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3176,"response_debit":37428,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3886},"plan":{"calls":16,"content_source_credit":357709,"derived_artifact_credit":910,"direct_net":348830,"estimated_tokens_saved":348830,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":209,"response_debit":13960,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4380},"review":{"calls":10,"content_source_credit":0,"derived_artifact_credit":910,"direct_net":-2674,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":88,"response_debit":4842,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":119,"content_source_credit":526308,"derived_artifact_credit":1820,"direct_net":478037,"estimated_tokens_saved":480711,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3473,"response_debit":56230,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9612},"wave_id":"1p6lp cross-host-skills"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 5 | 2,482,582 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":2482582,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
