# Stop Dashboard

Owner: Engineering
Status: active
Last verified: 2026-07-20

Shortcut: **`Stop dashboard`**

## Purpose

Stop the local Wavefoundry dashboard for the current repository. This command targets only the dashboard process recorded for this checkout, so dashboards in other repositories are unaffected.

## Operator Path

Use the MCP tool:

```text
wf_stop_dashboard
```

## Behavior

- If the current repository dashboard is running, stop it and clear stale repo-local metadata.
- If the dashboard is already stopped, report that state and leave other repositories untouched.
- If repo-local metadata is present but the process is gone, clean up the stale metadata.

## Notes

- This is a loopback-only control command for the current repository.
- There is no browser-launch fallback for stop; the command is control-only.
