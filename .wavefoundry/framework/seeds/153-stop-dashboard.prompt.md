# Stop Dashboard

Intent:

- Expose a first-class operator command for stopping the local dashboard for the current repository.
- Keep the command repo-local so multiple dashboards in different checkouts can be controlled independently.

Canonical public prompt doc:

- `docs/prompts/stop-dashboard.prompt.md`

Tasks:

1. Generate a public prompt doc that describes `Stop dashboard` as the repo-local control command for the dashboard process recorded in the current checkout.
2. Make the operator-facing path use the MCP tool `wave_dashboard_stop`.
3. Explain that the command targets only the current repository's dashboard metadata and process.
4. Clarify that dashboards in other repositories are unaffected.
5. Keep the prompt clear that stop is control-only and has no browser-launch fallback.

Guardrails:

- Do not describe stop as a shell wrapper or browser launcher.
- Do not imply cross-repo process control.
- Keep the prompt aligned with the dashboard metadata and process-control behavior implemented in the MCP server.
