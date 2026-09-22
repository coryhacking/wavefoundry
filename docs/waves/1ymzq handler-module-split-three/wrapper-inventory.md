# Wrapper extraction inventory

Owner: Engineering
Status: active
Last verified: 2026-09-21

Captured before extraction from server_impl SHA256 `69493d63c22ad81fe0407d5af0619e663cf824680819bf1c6861ee72507666a9`. Full approved stayers and their reasons remain in 1ymzn. Root imports below are per-call. No wrapper joins retrieval membership: the child-PID trio stays root-owned until the final index extraction.

## docs_handlers

```json
{
  "definitions": [
    "wf_validate_docs_response",
    "wf_garden_docs_response",
    "run_garden",
    "wf_sync_surfaces_response",
    "run_sync_surfaces",
    "wf_scan_secrets_response",
    "_subprocess_timeout_summary"
  ],
  "objects": [],
  "per_call_root": [
    "McpRepoCache",
    "__file__",
    "_attach_lint_to_response",
    "_bounded_subprocess_output",
    "_load_script",
    "_mcp_subprocess_run",
    "_preferred_python",
    "_response",
    "_trigger_background_index_refresh_for_paths",
    "run_validate"
  ],
  "direct_imports": [
    "from lifecycle_gate_support import SUBPROCESS_OPS_TIMEOUT_DEFAULT",
    "from lifecycle_gate_support import _diagnostic",
    "from lifecycle_gate_support import subprocess_ops_timeout_seconds",
    "from pathlib import Path",
    "from review_evidence import project_state_publication_lock",
    "from typing import Any",
    "from typing import Optional",
    "import json",
    "import os",
    "import tempfile"
  ]
}
```

### Root callers

- `run_garden`: `_subprocess_timeout_summary`
- `run_sync_surfaces`: `_subprocess_timeout_summary`
- `wf_garden_docs_response`: `run_garden`
- `wf_sync_surfaces_response`: `run_sync_surfaces`
- `wf_prepare_wave_response`: `run_garden`
- `wf_close_wave_response`: `run_garden`
- `register_mcp_surface`: `wf_garden_docs_response`, `wf_scan_secrets_response`, `wf_sync_surfaces_response`, `wf_validate_docs_response`

## dashboard_handlers

```json
{
  "definitions": [
    "wf_start_dashboard_response",
    "wf_open_dashboard_response",
    "_dashboard_cmdline_pids",
    "_dashboard_pid_is_live",
    "_dashboard_url_reachable",
    "_dashboard_already_serving",
    "_dashboard_process_metadata",
    "_remove_dashboard_metadata",
    "_terminate_dashboard_pid",
    "wf_stop_dashboard_response",
    "wf_restart_dashboard_response"
  ],
  "objects": [
    "DASHBOARD_START_WAIT_SECONDS"
  ],
  "per_call_root": [
    "DASHBOARD_START_WAIT_SECONDS",
    "_DASHBOARD_CHILD_PIDS",
    "__file__",
    "_mcp_subprocess_run",
    "_pid_is_running",
    "_preferred_python",
    "_reap_dashboard_child_pids",
    "_register_dashboard_child_pid",
    "_response",
    "_windows_no_window_flag"
  ],
  "direct_imports": [
    "from lifecycle_gate_support import _diagnostic",
    "from pathlib import Path",
    "from typing import Any",
    "import json",
    "import os"
  ]
}
```

### Root callers

- `wf_start_dashboard_response`: `DASHBOARD_START_WAIT_SECONDS`, `_dashboard_already_serving`, `_dashboard_cmdline_pids`, `_dashboard_pid_is_live`, `_dashboard_url_reachable`, `_terminate_dashboard_pid`
- `wf_open_dashboard_response`: `_dashboard_pid_is_live`, `wf_start_dashboard_response`
- `_dashboard_pid_is_live`: `_dashboard_cmdline_pids`
- `_dashboard_already_serving`: `_dashboard_cmdline_pids`, `_dashboard_pid_is_live`, `_dashboard_url_reachable`
- `wf_stop_dashboard_response`: `_dashboard_cmdline_pids`, `_dashboard_pid_is_live`, `_dashboard_process_metadata`, `_remove_dashboard_metadata`, `_terminate_dashboard_pid`
- `wf_restart_dashboard_response`: `_dashboard_process_metadata`, `wf_start_dashboard_response`, `wf_stop_dashboard_response`
- `register_mcp_surface`: `wf_open_dashboard_response`, `wf_restart_dashboard_response`, `wf_start_dashboard_response`, `wf_stop_dashboard_response`

## edit_gate_handlers

```json
{
  "definitions": [
    "wave_open_gate_response",
    "wf_close_wave_gate_response",
    "wf_gate_status_response",
    "_force_gates_closed",
    "wf_get_handoff_response",
    "wf_set_handoff_response",
    "_update_handoff_wave_ref",
    "_read_guard_overrides",
    "_write_guard_overrides"
  ],
  "objects": [
    "_VALID_GATES",
    "_EDIT_GOVERNANCE_GATE_MAP"
  ],
  "per_call_root": [
    "McpRepoCache",
    "_attach_lint_to_response",
    "_response",
    "_trigger_background_index_refresh_for_paths"
  ],
  "direct_imports": [
    "from lifecycle_gate_support import _diagnostic",
    "from pathlib import Path",
    "from typing import Any",
    "from typing import Optional",
    "import datetime",
    "import re"
  ]
}
```

### Root callers

- `_force_gates_closed`: `_VALID_GATES`, `_read_guard_overrides`, `_write_guard_overrides`
- `wave_open_gate_response`: `_VALID_GATES`, `_read_guard_overrides`, `_write_guard_overrides`
- `wf_close_wave_gate_response`: `_VALID_GATES`, `_read_guard_overrides`, `_write_guard_overrides`
- `wf_gate_status_response`: `_VALID_GATES`, `_read_guard_overrides`
- `wf_pause_wave_response`: `_force_gates_closed`, `_update_handoff_wave_ref`
- `wf_close_wave_response`: `_force_gates_closed`, `_update_handoff_wave_ref`
- `register_mcp_surface`: `wave_open_gate_response`, `wf_close_wave_gate_response`, `wf_gate_status_response`, `wf_get_handoff_response`, `wf_set_handoff_response`
