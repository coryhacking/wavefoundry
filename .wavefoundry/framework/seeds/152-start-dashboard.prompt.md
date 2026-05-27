# 152 - Start Dashboard

Intent:

- Expose the local Wave Framework dashboard as a first-class operator command rather than an undocumented script path.

Canonical public prompt doc to generate in the target repository:

- `docs/prompts/start-dashboard.prompt.md`

Tasks:

1. Generate a public prompt doc that describes the dashboard as a **local-only**, **read-only**, **loopback HTTP** surface backed by `.wavefoundry/framework/scripts/dashboard_server.py`.
2. Create `.wavefoundry/bin/wave-dashboard` as a persistent-process launcher that wraps `dashboard_server.py` with `nohup` so the server survives shell exit. The script must:
   - resolve `REPO_ROOT` from its own location using the same pattern as `.wavefoundry/bin/docs-gardener` (`cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd`)
   - write logs to `.wavefoundry/logs/dashboard.log` (create the directory with `mkdir -p` if needed)
   - launch `dashboard_server.py` with `--root "$REPO_ROOT"` and `--open` baked in so the browser opens by default
   - pass `"$@"` after the fixed flags so callers can append extra arguments
   - print `Wave dashboard started (pid $!). Log: $LOG` after forking
   - be made executable (`chmod +x`)

3. In the public prompt surface and any agent-oriented body, make the operator-facing command **`Start dashboard`** use the bin launcher:

   ```bash
   .wavefoundry/bin/wave-dashboard
   ```

   The bin launcher opens the browser automatically — no `--open` flag is needed in the public docs. Document that the low-level no-browser fallback is to call the script directly:

   ```bash
   python3 .wavefoundry/framework/scripts/dashboard_server.py --root .
   ```
   Also note `Stop dashboard` and `Restart dashboard` as related repo-local control commands in the public prompt surface.

4. Require both paths to **always print the final bound URL** including host and port, even when the browser is opened automatically.
5. Describe the runtime contract:
   - UI state lives in the browser
   - the server reads live repository state and exposes JSON endpoints
   - any `.wavefoundry/` dashboard metadata file is for **host-local endpoint discovery only**, not as the canonical dashboard data source
6. Explain port selection from `docs/workflow-config.json` `dashboard`: try preferred port, then reuse recorded host-local metadata when valid, then scan the configured fallback range.
7. Describe the dashboard as **MCP-informed, not MCP-transported**: it reuses shared Python readers rather than making the browser speak stdio MCP.
8. Keep the prompt clear that the dashboard is optional operational tooling and does not replace wave docs, review evidence, or MCP tools as the canonical source of truth.
9. When the target repository has `docs/design-system/`, point the dashboard prompt at the seeded dashboard design-system rules rather than implying ad hoc CSS.

Guardrails:

- Do not describe the dashboard as remotely accessible, authenticated, or multi-user.
- Do not describe a persistent `dashboard.json` snapshot file as the primary state source.
- Do not imply that the browser writes repository state.
