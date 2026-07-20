# Restart Dashboard

Intent:

- Expose a first-class operator command for restarting the local dashboard for the current repository.
- Keep the restart path repo-local so it does not interfere with dashboards in other checkouts.

Canonical public prompt doc:

- `docs/prompts/restart-dashboard.prompt.md`

Tasks:

1. Generate a public prompt doc that describes `Restart dashboard` as the repo-local dashboard stop/start command.
2. Make the operator-facing path use the MCP tool `wf_restart_dashboard`.
3. Explain that restart stops the current repository dashboard and then starts a fresh one for the same checkout.
4. Clarify that the browser opens automatically when the restarted dashboard comes back up.
5. Keep the prompt clear that restart is scoped to the current repository only.

Guardrails:

- Do not describe restart as a generic system restart.
- Do not imply it can control dashboards in other repositories.
- Keep the prompt aligned with the dashboard process-control behavior implemented in the MCP server.
