## Install

Drop the attached `.zip` at your repo root **without extracting it** — the agent unpacks it as the first step, extracting only `.wavefoundry/*` and `install-wavefoundry.md` (`unzip -o <zip> '.wavefoundry/*' 'install-wavefoundry.md' -d .`; the zip also carries its own installer runner members at the zip root, which must not land in your repo). Then type this shortcut phrase as a chat message to your AI agent (Claude Code, Cursor, Codex, Junie, GitHub Copilot, Windsurf, Air, or Warp):

```
Install Wavefoundry
```

That is the only operator-typed command — the agent runs the rest of the install. Prerequisites: Python 3.11+, an MCP-aware agent host. Full walkthrough and host-specific notes in the [README](https://github.com/coryhacking/wavefoundry#quick-start).

## Upgrade

Already running Wavefoundry on protocol 2? Drop the attached `.zip` at your repo root **without extracting it** and type this shortcut phrase to your agent:

```
Upgrade Wavefoundry
```

The agent unpacks the zip, advances the framework, runs any required migrations and index rebuilds, and reloads the MCP server. **Review the version notes below** for anything that re-indexes or changes behavior on this upgrade.

**Upgrading a protocol-1 / Wavefoundry 1.14 installation to 1.15:** use the same matching
`wavefoundry-<version>.zip` package. Fully stop the dashboard and every attached MCP/agent host,
then let the agent execute the exact returned argv through its ordinary non-MCP shell. The operator
does not copy or type that command. Restart every attached host once the package returns, then
follow its structured reconciliation, cleanup, and audit guidance. The package contains and
verifies the exact feature payload; there is no special upgrade package, second operator command,
or separate bridge asset to coordinate.

---
