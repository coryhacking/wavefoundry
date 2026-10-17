## Install

**Verify first.** Before dropping any downloaded asset in place, compare its SHA-256 with its single line in this release's `SHA256SUMS` asset: `shasum -a 256 <zip>` on macOS, `sha256sum <zip>` on Linux and WSL2, or `(Get-FileHash -LiteralPath <zip> -Algorithm SHA256).Hash -eq '<hex>'` in Windows PowerShell (`-eq` ignores case). Stop if the digest differs or the asset has no line or more than one. Releases published before `SHA256SUMS` was added have none; for those, compare against the SHA-256 digest GitHub shows beside the asset on the release page, and stop if none is shown. This checks the downloaded bytes against a digest published in the same GitHub release: it catches corruption, truncation and a copy altered after it left the release, but not a replacement by someone able to edit the release, who could edit `SHA256SUMS` too. It is not a signature; release signing is not yet provided.

Drop the attached `.zip` at your repo root **without extracting it** — the agent unpacks it as the first step, extracting only `.wavefoundry/*` and `install-wavefoundry.md` (`unzip -o <zip> '.wavefoundry/*' 'install-wavefoundry.md' -d .`; the zip also carries its own installer runner members at the zip root, which must not land in your repo). Then type this shortcut phrase as a chat message to your AI agent (Claude Code, Cursor, Codex, Junie, GitHub Copilot, Windsurf, Air, or Warp):

```
Install Wavefoundry
```

That is the only operator-typed command — the agent runs the rest of the install. Prerequisites: Python 3.11+, an MCP-aware agent host. Full walkthrough and host-specific notes in the [README](https://github.com/coryhacking/wavefoundry#quick-start).

Choose the lean ZIP for the smallest download, or the optional `.with-models.zip` for included offline model sources. Extract the same framework paths from either choice; never unpack `payload/` into the project. Keep the combined ZIP available and pass it to setup with `--model-bundle <combined.zip>` when model provisioning is needed.

## Upgrade

Already running Wavefoundry on protocol 2? Verify the `.zip` against `SHA256SUMS` as above, then drop it at your repo root **without extracting it** and type this shortcut phrase to your agent:

```
Upgrade Wavefoundry
```

The agent unpacks the zip, advances the framework, runs any required migrations and index rebuilds, and reloads the MCP server. **Review the version notes below** for anything that re-indexes or changes behavior on this upgrade.

For the optional combined ZIP on an existing 1.31.0 installation, automatic discovery cannot recognize the new filename. Stop the target dashboard and attached MCP servers, then have the agent run `python3 <combined.zip> --root <repo> --confirm-hosts-stopped` through its ordinary shell. Follow its retained continuation or restart instructions. New discovery prefers lean when both variants have the same version/build; select combined explicitly when it is needed.

**Upgrading a protocol-1 installation at 1.8.0 or later:** same package, same shortcut phrase, and
no intermediate version to stage through. The agent stops the dashboard and every attached MCP/agent
host, then runs the exact returned command through its ordinary non-MCP shell; the operator does not
copy or type that command. Restart every attached host once the package returns, then follow its
structured reconciliation, cleanup, and audit guidance. There is no special upgrade package, second
operator command, or separate bridge asset to coordinate. A source below 1.8.0 stops before any
change is made and must first be upgraded to that floor.

---
