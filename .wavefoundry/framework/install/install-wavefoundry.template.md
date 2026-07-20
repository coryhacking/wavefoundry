# Install Wavefoundry — {{version}}

You've extracted the Wavefoundry framework zip at your repository root. This file is the agent-readable bootstrap entry point. Follow the steps below to complete the install.

## Where is the content?

The framework tree lives under `.wavefoundry/`. macOS Finder hides dot-prefixed folders by default — that's why this extracted folder may look empty. Press **Cmd + Shift + .** in Finder to show hidden files, or run `ls -la` in a terminal.

## Quick reference

- `.wavefoundry/framework/` — seeds, scripts, dashboard assets, VERSION
- `.wavefoundry/framework/install/` — install templates (framework source of truth)
- `.wavefoundry/README.md` — project-owner orientation
- `.wavefoundry/CHANGELOG.md` — release history

## What to do next

**Step 1 — Bootstrap the install log.**

Check whether `.wavefoundry/install-log.md` exists.

- **It does not exist (first install):** copy `.wavefoundry/framework/install/install-log.template.md` to `.wavefoundry/install-log.md`. This becomes your project's live install state machine. The template is overwritten on framework upgrades; your live log is NOT, so your install progress is preserved.
- **It exists (resuming or upgrading):** continue from the first unchecked row. If you're unsure whether the existing `[x]` markers are still valid (fresh agent session, partial recovery from an abort), call `wf_audit_install` first — it validates each checked row's expected artifact and points at the next action.

**Step 2 — Execute the log.**

Open `.wavefoundry/install-log.md`. Read the first unchecked row (`- [ ]`). Each row points at a seed prompt to execute and an expected artifact to verify. Run the step, confirm the artifact exists, mark `[x]`, advance.

Phase 1 (the "Harness — no MCP required" section) runs without MCP. When Phase 1 finishes, the log instructs you to **ask the operator to restart the AI agent** so the Wavefoundry MCP server becomes available. After restart, Phase 2 begins, and `wf_audit_install` becomes the validating gate.

## If your agent is unsure how to start

Type this exact phrase in your AI agent's chat:

```
Install Wavefoundry
```

The agent will pick up this file (`install-wavefoundry.md`) and follow the bootstrap from there.

## Supported AI agents

Wavefoundry's MCP server registers via per-host configs (rendered by `render_platform_surfaces.py` during Phase 1). Supported hosts include Claude Code, Cursor, Codex, Junie, Windsurf, Air, Warp, and any other MCP-aware coding agent.

## Reference

Full framework documentation, change history, and contribution guide: https://github.com/coryhacking/wavefoundry
