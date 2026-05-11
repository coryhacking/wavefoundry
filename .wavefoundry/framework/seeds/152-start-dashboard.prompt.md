# 152 - Start Dashboard

Intent:

- Expose the local Wave Framework dashboard as a first-class operator command rather than an undocumented script path.

Canonical public prompt doc to generate in the target repository:

- `docs/prompts/start-dashboard.prompt.md`

Tasks:

1. Generate a public prompt doc that describes the dashboard as a **local-only**, **read-only**, **loopback HTTP** surface backed by `.wavefoundry/framework/scripts/dashboard_server.py`.
2. In the public prompt surface and any agent-oriented body, make the operator-facing command **`Start dashboard`** open the browser by default by invoking the low-level script with `--open`:

   ```bash
   python3 .wavefoundry/framework/scripts/dashboard_server.py --root . --open
   ```

3. Document that the low-level script is still composable and startup-only by default:

   ```bash
   python3 .wavefoundry/framework/scripts/dashboard_server.py --root .
   ```

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
