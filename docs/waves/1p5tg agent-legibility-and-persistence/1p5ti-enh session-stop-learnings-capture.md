# Session-stop learnings capture

Change ID: `1p5ti-enh session-stop-learnings-capture`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Last verified: 2026-06-16
Wave: `1p5tg agent-legibility-and-persistence`

## Rationale

The README's headline failure mode is "your AI coding agent forgets what it did last session." The framework already counters this with `session-handoff.md` and file-based memory — but both depend on the agent *remembering to update them* before the session ends. The large-codebase guidance recommends a **stop hook** that captures learnings and proposes handoff/memory updates at session end, so persistence doesn't rely on the agent's discipline mid-flow.

A `Stop`-event hook gives us a deterministic capture point: when a session ends, snapshot the current wave/handoff state and surface a concise "did you record what changed?" nudge (open wave, changed ACs, uncommitted work, candidate learnings). This makes the next session's startup hydrate from accurate state instead of a stale or missing handoff.

## Requirements

1. **Host-agnostic, canonical intent generic.** The session-end hook is defined once generically (seed + capture script) and **rendered to each supported host's hook format** — Claude Code today (a `Stop`/`SubagentStop` entry via `render_platform_surfaces`, alongside the current `PreToolUse`/`PostToolUse`), and other hosts as they expose a session-end hook. Nothing Claude-specific in the canonical definition; the Claude rendering is one target, not the source of truth. Seed-defined so every project picks it up on render/upgrade. **Existing installs** receive it through the upgrade settings migration, which must add the hook **without clobbering operator-added hooks** (follow the established custom-preserving migration pattern).
2. On fire, the hook runs a fast, self-contained script that produces a **capture summary** geared toward what saves the next session tokens: current open wave + its changed/at-risk ACs, uncommitted-work signal (git status summary), session-handoff staleness signal, and — the highest-value part — **candidate learnings/quirks** worth recording (e.g. a build/test quirk or decision discovered this session) framed as **memory candidates** for the agent/operator to confirm. Written to a predictable location and/or surfaced as the hook's nudge output.
3. The hook is **non-blocking and fail-safe**: it must never prevent the session from ending, must exit non-fatally on any error (no live server, not a git repo, missing files), and must complete quickly.
4. The hook **never auto-edits memory or auto-commits**. It captures and nudges only; any handoff/memory write stays in the agent/operator loop (consistent with "confirm before close," "never commit unless asked," and memory-curation discipline).
5. Discoverability + docs: the hook and its behavior are documented seed-first (e.g. in the agents/hooks surface docs) and woven into related seeds (session-handoff, memory guidance) so it isn't an orphan.

## Scope

**Problem statement:** Cross-session persistence depends on the agent manually updating handoff/memory before stopping; when it doesn't, the next session starts blind. There's no deterministic end-of-session capture point.

**In scope:**

- A seed-defined `Stop`/`SubagentStop` hook + the capture script it invokes (under `.wavefoundry/framework/`), rendered through the existing surface-rendering mechanism.
- The capture summary content (open wave, changed ACs, uncommitted-work signal, handoff-staleness signal) and where it lands.
- Tests for the capture script (pure logic paths: wave-state read, git-status summary, fail-safe on missing inputs) + docs.

**Out of scope:**

- Auto-writing `session-handoff.md` or memory files, and any auto-commit — explicitly excluded (capture/nudge only).
- LLM-summarized "learnings" generation inside the hook — the hook surfaces signals; the agent does the synthesis. (Can be a later enhancement.)
- Host-specific hook formats beyond what the current surface-rendering path already supports.

## Acceptance Criteria

- [x] AC-1: The session-end capture is defined in one host-agnostic source generator (`claude_stop_source`) and rendered to the host format — Claude `Stop` in `.claude/settings.json` + the `session-capture` hook bundle (launcher/.py/.cmd) — by `render_platform_surfaces`. Existing installs receive it when the upgrade runs its render phase: `render_claude_settings` owns the framework hooks block (so the Stop entry lands deterministically) while preserving the operator's non-hook settings keys. Verified by `RenderPlatformSurfacesScriptTests`. *(Delivery-council fixes: capture writes to the gitignored `.wavefoundry/logs/`, not `cache/`; `SubagentStop` dropped — it would fire on every subagent completion. Implementation note: render owns the hooks block, so no separate clobber-preserving upgrade migration is needed.)*
- [x] AC-2: On fire, the capture script emits a summary covering open-wave + AC progress, uncommitted-work signal, handoff-staleness signal, and **candidate learnings/quirks framed as memory candidates**; verified by `SessionCaptureHookTests.test_captures_active_wave_and_ac_progress`.
- [x] AC-3: The hook is non-fatal and fast under adverse conditions (not a git repo, no open wave) — it exits 0 and never blocks session end; covered by `test_no_active_wave_is_clean_exit` + `test_not_a_repo_is_fail_safe`.
- [x] AC-4: The hook performs no memory writes and no git commits (capture/nudge only; `test_never_writes_memory_or_commits`); documented seed-first via the generic source; **full suite 3160 OK**; docs-lint clean.

## Tasks

- [x] Define the session-end hook generically in a seed; render it to the host format (Claude `Stop`/`SubagentStop`) via the surface-rendering output.
- [x] Implement the capture script (wave-state read + git-status summary + handoff-staleness check + candidate-learnings/memory-candidate surfacing; fail-safe; fast).
- [x] Add unit tests (state coverage + adverse-condition fail-safe + no-write/no-commit assertions).
- [x] Document seed-first + weave pointers into session-handoff/memory seeds; run full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| capture    | Engineering | —          | capture script + tests |
| hook-wire  | Engineering | capture    | seed hook + surface rendering |
| docs       | Engineering | hook-wire  | seed-first docs + cross-links |


## Serialization Points

- Hook wiring depends on the capture script's invocation contract (args/exit codes), so it follows the script.

## Affected Architecture Docs

`N/A` for runtime architecture — this is an agent-operations surface (hook + capture tooling). A pointer is added to the agents/hooks and session-handoff docs (operational docs, not architecture contract).

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Without the rendered hook there's no deterministic capture point. |
| AC-2 | required | The capture summary is the value delivered. |
| AC-3 | required | A hook that can block or crash session-end is unacceptable. |
| AC-4 | required | No-auto-write/commit is a safety contract; discoverability prevents orphaning. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Prepare spike: integration point confirmed — `render_platform_surfaces.py::render_claude_settings` writes `.claude/settings.json` `hooks` (currently `PreToolUse`/`PostToolUse`); add a `Stop` entry there. Existing installs get it via the upgrade settings migration, which already rewrites `hooks` while preserving operator customs (precedent: pycache-row strip). New obligation: the migration must add the Stop hook WITHOUT clobbering operator-added hooks. | `render_platform_surfaces.py:653`, `test_upgrade_wavefoundry.py` (SettingsJsonPycacheRowStripTests) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-15 | Capture + nudge only; no auto-write to memory/handoff, no auto-commit | Keeps the operator/agent in the loop (consistent with confirm-before-close, never-commit-unless-asked, curated memory); a hook silently editing memory or committing is a footgun | Auto-write handoff (rejected — can clobber curated state, fires on every stop); auto-commit (rejected — violates commit policy) |
| 2026-06-15 | Seed-defined + rendered via the existing surface path | Every project gets it on upgrade; no per-project hand-install; consistent with seed-first | Per-project hand-installed hook (rejected — drifts, undiscoverable) |
| 2026-06-16 | Capture writes to gitignored `.wavefoundry/logs/` and is intentionally NOT indexed | The artifact is transient + overwritten every session + uncurated; indexing it would churn the index and surface stale session state as canonical retrieval noise. Durable value flows via curation into `session-handoff.md`/memory, which ARE committed + indexed. The next session reads the capture by its predictable path, not via search. | Index the capture (rejected — re-index churn + stale noise); append-only history file (rejected — unneeded for a safety-net nudge) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Hook fires noisily / slows session end | Fast, summary-only, non-fatal; no network/server dependency; quiet when nothing is open |
| Hook errors block the session ending | Exit non-fatally on every path; tests assert clean exit under adverse conditions |
| Capture summary becomes a clobber vector | Capture/nudge only; never writes handoff/memory or commits — the agent/operator applies updates |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
