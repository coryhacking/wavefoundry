# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-15

wave-id: `1p5tg agent-legibility-and-persistence`
Title: Agent Legibility And Persistence

## Objective

Adopt two general-health practices from Anthropic's "How Claude Code works in large codebases" guidance, each delivered as a **generic, seed-rooted framework capability** that every downstream project inherits on upgrade (no project-specific implementation). Add a **session-stop learnings capture** so wave/handoff state survives across sessions without manual prompting ("forgets last session" → persistence); and establish a **framework-config review** — a removal-biased prompt that, on **every** major/minor upgrade, is recommended to a senior/principal owner to evaluate (human-initiated, never auto-run) — so seeds, CLAUDE.md, and constraints get audited and stale ones retired (anti-drift / the over-accretion repeatedly flagged in council review). When this wave closes, the framework is more durable across sessions and has a standing, owner-gated process to prevent constraint bloat. (The on-mission large-codebase **map** was split out to its own wave, `1p5x8 large-codebase-map`, where XL-scaling can be designed first-class rather than diluted here.)

## Changes


Change ID: `1p5ti-enh session-stop-learnings-capture`
Change Status: `implemented`

Change ID: `1p5tj-doc framework-config-review-cadence`
Change Status: `implemented`

Change ID: `1p5tk-enh config-review-due-at-upgrade`
Change Status: `implemented`


Completed At: 2026-06-16

## Wave Summary

Wave `1p5tg agent-legibility-and-persistence` (Agent Legibility And Persistence) delivered 3 changes: Session-stop learnings capture, Framework-config review prompt + cadence policy, and Config-review recommendation at major/minor upgrade. Notable adjustments during implementation: Session-stop learnings capture: Prepare spike: integration point confirmed — `render_platform_surfaces.py::render_claude_settings` writes `.claude/settings.json` `hooks` (currently `PreToolUse`/`PostToolUse`); add a `Stop` entry there. Existing installs get it via the upgrade settings migration, which already rewrites `hooks` while preserving operator customs (precedent: pycache-row strip). New obligation: the migration must add the Stop hook WITHOUT clobbering operator-added hooks.; Config-review recommendation at major/minor upgrade: Simplified per operator direction: dropped the marker + dual time/wave-count threshold subsystem. New design = recommend the review on every major/minor upgrade, stateless. This also removed the only intra-wave shared contract (the former "record completed review" marker).

**Changes delivered:**

- **Session-stop learnings capture** (`1p5ti-enh session-stop-learnings-capture`) — 4 ACs completed. Key decisions: --------; Capture + nudge only; no auto-write to memory/handoff, no auto-commit
- **Framework-config review prompt + cadence policy** (`1p5tj-doc framework-config-review-cadence`) — 5 ACs completed. Key decisions: --------; Deliver a guided review prompt + policy, not an automated linter
- **Config-review recommendation at major/minor upgrade** (`1p5tk-enh config-review-due-at-upgrade`) — 3 ACs completed. Key decisions: --------; Recommend the review on every major/minor upgrade, stateless
## Journal Watchpoints

- **Generic + seed-rooted, never project-specific (governs the whole wave)** — every deliverable ships in framework seeds/scripts so downstream projects inherit it on upgrade. No wavefoundry-repo-specific names, paths, or hardcoded values; any defaults are framework-owned (config-overridable, not pre-emitted per project). This is the operator's explicit constraint for this wave.
- **Changes are independent** — `1p5ti` (stop hook), `1p5tj` (review prompt + policy), and `1p5tk` (upgrade recommendation) touch disjoint surfaces. `1p5tk` simply points at `1p5tj`'s prompt; with the marker/threshold subsystem removed there is no shared state contract between them.
- **Seed-first** — `1p5ti` (hook), `1p5tj` (review prompt + policy), `1p5tk` (recommendation wording) add agent-facing surfaces; update framework seeds before per-project rendered docs, and weave discoverability pointers into related seeds (don't orphan the new prompt/hook). Open `seed_edit_allowed` for seed edits.
- **Framework-edit gate** — `1p5ti` (hook script/renderer via `render_claude_settings`) and `1p5tk` (recommendation line in the upgrade flow) touch `.wavefoundry/framework/scripts/**`; open `framework_edit_allowed` before edits, close after. Each new/changed script needs tests via `~/.wavefoundry/venv/bin/python run_tests.py`.
- **Stop-hook must not block or annoy** — `1p5ti` runs on session stop; it must be fast, non-fatal on error, and must not gate the user's ability to end a session. Capture/nudge only; never auto-commit or auto-edit memory without the agent/operator in the loop. The upgrade settings migration must add the hook without clobbering operator-added hooks.
- **Due-check stays as simple as possible** — `1p5tk` is just a recommendation surfaced on **every** major/minor upgrade (not patch): no marker, no thresholds, no wave-count state. Recommend-only, addressed to a senior/principal owner, human-initiated, and fully fail-safe (never raises into / blocks the upgrade). The "evaluate it each major/minor upgrade" cadence *is* the policy.

## Review Evidence

- wave-council-readiness: READY — prepare-council passed 2026-06-16, then re-scoped the same day. Now three generic, seed-rooted, independent general-health changes. The on-mission large-codebase map was split out to its own wave (1p5x8) so its XL-scaling can be designed first-class; the upgrade recommendation (1p5tk) was simplified to the bare minimum per operator direction — surfaced on every major/minor upgrade, no marker/threshold/wave-count state — which also removed the only intra-wave contract. The remaining scope is strictly simpler than what the council reviewed. Confirmed integration point: the stop hook (1p5ti) renders through the existing render_claude_settings path with an established custom-preserving upgrade migration. Conditions carried into implement, not blockers: 1p5ti must respect Stop-hook semantics (exit 0, never block session end) and not clobber operator hooks on upgrade; 1p5tk must be a single fail-safe recommendation line gated to major/minor upgrades (never raises into the upgrade); all three are seed-first with discoverability pointers. Strongest challenge: are these worth a wave given they are general-health rather than XL-specific — accepted as low-cost, low-risk durability/anti-drift wins now that the on-mission map carries the XL mission separately. Strongest alternative: defer the persistence hook entirely — left in as an explicitly-modest safety net, cheap to ship.
- wave-council-delivery: READY — delivery-council passed 2026-06-16. All three changes implemented + tested, full suite 3160 OK (+13), docs-lint clean. Two findings were caught by inspecting the delivered code and fixed in-session (PASS WITH IN-SESSION FIXES): (1) the capture file wrote to `.wavefoundry/cache/`, which is NOT gitignored — repointed to the already-gitignored `.wavefoundry/logs/`; (2) `SubagentStop` would fire the capture on every subagent completion (noise + redundant captures) — dropped, keeping main-session `Stop` only. Re-rendered + re-ran the suite green after both fixes. Strongest challenge: do persistence + config-hygiene earn a wave when they are general-health rather than XL-specific — accepted (the XL mission is carried by 1p5x8; these are low-cost, low-risk, now-verified durability/anti-drift wins). Security/runtime: no new network surface; the stop hook is fail-safe (always exits 0, never blocks, captures filenames/state not contents, never writes memory/commits); the upgrade recommendation is stateless + fail-safe and cannot block an upgrade. Closeable on merits.
- operator-signoff: approved — 2026-06-16, operator requested close. Three changes implemented + verified (`1p5ti` session-end capture hook, `1p5tj` framework-config review prompt + policy, `1p5tk` stateless major/minor upgrade recommendation); full suite 3160 OK; docs-lint clean; prepare-council PASS and delivery-council PASS WITH IN-SESSION FIXES (capture path repointed to gitignored `.wavefoundry/logs/`; `SubagentStop` dropped). Follow-on dashboard/index-freshness work is scoped separately in wave `1p5xt`.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; note: re-scoped after the council — the project map split to wave 1p5x8 and the upgrade due-check (1p5tk) simplified to a stateless every-major/minor recommendation, leaving three independent general-health changes strictly simpler than reviewed; strongest-challenge: an archetype value-council found persistence + config-hygiene are general-health rather than XL-specific levers — accepted as low-cost, low-risk wins with the XL mission now carried by 1p5x8; strongest-alternative: defer the stop hook as off-mission — kept as an explicitly-modest, cheap safety net; security/runtime: no new network surface, the stop hook captures filenames/state not contents, and the upgrade recommendation is fail-safe and cannot block an upgrade)

- **Delivery-phase Wave Council [delivery-council] — 2026-06-16: PASS WITH IN-SESSION FIXES** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; in-session-fixes: capture file repointed from non-gitignored `.wavefoundry/cache/` to the gitignored `.wavefoundry/logs/`; `SubagentStop` dropped (would fire on every subagent completion) keeping main-session `Stop` only — both re-rendered + suite re-run green; strongest-challenge: general-health (persistence + config-hygiene) rather than XL-specific levers — accepted, XL mission carried by 1p5x8, these are low-cost verified wins; strongest-alternative: defer the stop hook — rejected, it is cheap and now hardened; security/runtime: no new network surface, stop hook always exits 0 / never blocks / captures filenames not contents / never writes memory or commits, upgrade recommendation stateless + fail-safe; full suite 3160 OK, docs-lint clean)

## Dependencies

- No external wave dependencies.
