# Restart Dashboard

Owner: Engineering
Status: active
Last verified: 2026-05-13

Shortcut: **`Restart dashboard`**

## Purpose

Restart the local Wavefoundry dashboard for the current repository. The restart should stop the current repository dashboard first, then start a fresh server for the same checkout.

## Operator Path

Use the MCP tool:

```text
wave_dashboard_restart
```

## Behavior

- Stop the current repository dashboard if it is running.
- Start a new dashboard process for the same repository root.
- Return the new final URL once the restarted dashboard is ready.

## Notes

- This command is repo-local and does not affect dashboards in other repositories.
- The browser opens automatically as part of the restart path, matching `Start dashboard`.
