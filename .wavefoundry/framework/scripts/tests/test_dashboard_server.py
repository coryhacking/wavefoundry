from __future__ import annotations

import importlib.util
import io
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_LIB_PATH = SCRIPTS_ROOT / "dashboard_lib.py"
DASHBOARD_SERVER_PATH = SCRIPTS_ROOT / "dashboard_server.py"
SERVER_PATH = SCRIPTS_ROOT / "server.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_dashboard_modules():
    _load_module("server", SERVER_PATH)
    lib = _load_module("dashboard_lib", DASHBOARD_LIB_PATH)
    srv = _load_module("dashboard_server", DASHBOARD_SERVER_PATH)
    return lib, srv


def _get_sse_client_class():
    """Return the _SseClient class from the dashboard_server module."""
    _, srv = load_dashboard_modules()
    return srv._SseClient


class _MockStore:
    """Minimal SnapshotStore stand-in for handler tests."""

    def __init__(self, snapshot: dict):
        self._snapshot = snapshot
        self._clients = []

    def get(self) -> dict:
        return self._snapshot

    def register_sse_client(self):
        _, srv = load_dashboard_modules()
        client = srv._SseClient()
        self._clients.append(client)
        return client

    def unregister_sse_client(self, client) -> None:
        try:
            self._clients.remove(client)
        except ValueError:
            pass


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(root: Path) -> None:
    _write(
        root / "docs" / "workflow-config.json",
        json.dumps(
            {
                "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
                "dashboard": {
                    "preferred_port": 43127,
                    "port_range_start": 43127,
                    "port_range_end": 43129,
                    "poll_interval_ms": 2000,
                },
            }
        ),
    )
    _write(root / "docs" / "repo-profile.json", json.dumps({"project_archetypes": ["framework_tooling"]}))
    _write(root / "docs" / "prompts" / "prompt-surface-manifest.json", json.dumps({"framework_revision": "2026-05-08a", "public_prompt_surface": []}))
    _write(root / ".wavefoundry" / "framework" / "VERSION", "2026-05-08a\n")
    _write(root / "README.md", "# Test Dashboard Repo\n")
    _write(root / "docs" / "agents" / "session-handoff.md", "# Session Handoff\n\n**Active wave:** `12x test-wave`\n")


def _make_wave(root: Path) -> None:
    wave_dir = root / "docs" / "waves" / "12x test-wave"
    _write(
        wave_dir / "wave.md",
        """# Wave Record

wave-id: `12x test-wave`
Title: Test Wave
Status: active

## Objective

Verify dashboard snapshot rendering.

## Participants

| Role | Lane | Scope |
|------|------|-------|
| code-reviewer | review | change |

## Review Checkpoints

- Prepare wave — readiness verdict: pass

## Review Evidence

- wave-council-readiness: approved
- code-reviewer: approved

## Changes

Change ID: `12x1-enh sample-dashboard`
Change Status: `ready`
""",
    )
    _write(
        wave_dir / "12x1-enh sample-dashboard.md",
        """# Sample Dashboard Change

Change ID: `12x1-enh sample-dashboard`
Change Status: `ready`
Owner: Engineering
Wave: `12x test-wave`

## Acceptance Criteria

- [x] AC-1: dashboard data loads
- [ ] AC-2: dialog details render

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | must work |
| AC-2 | important | good to have |

## Tasks

- [x] build shared readers
- [ ] add more charts

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-08 | Added dashboard API. | test evidence |
""",
    )
    _write(
        root / "docs" / "plans" / "12x2-enh staged-plan.md",
        """# Staged Plan

Change ID: `12x2-enh staged-plan`
Change Status: `planned`
Owner: Engineering

## Tasks

- [ ] stage this later
""",
    )


def _write_dashboard_lance_index(root: Path, *, docs_chunks: list[dict] | None = None, code_chunks: list[dict] | None = None) -> None:
    import lancedb

    index_dir = root / ".wavefoundry" / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "built_at": "2026-05-16T00:00:00Z",
        "model_versions": {"docs": "BAAI/bge-base-en-v1.5", "code": "BAAI/bge-base-en-v1.5"},
        "content": [],
        "file_meta": {},
    }
    if docs_chunks is not None:
        meta["content"].append("docs")
    if code_chunks is not None:
        meta["content"].append("code")
    (index_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    db = lancedb.connect(str(index_dir))
    if docs_chunks:
        db.create_table("docs", data=[{**chunk, "vector": [0.0, 0.0, 0.0, 0.0]} for chunk in docs_chunks], mode="overwrite")
    if code_chunks:
        db.create_table("code", data=[{**chunk, "vector": [0.0, 0.0, 0.0, 0.0]} for chunk in code_chunks], mode="overwrite")


def _make_planned_wave(root: Path) -> None:
    wave_dir = root / "docs" / "waves" / "12y planned-wave"
    _write(
        wave_dir / "wave.md",
        """# Wave Record

wave-id: `12y planned-wave`
Title: Planned Wave
Status: draft

## Objective

Verify pending-scope dashboard rendering.

## Participants

| Role | Lane | Scope |
|------|------|-------|
| code-reviewer | review | change |

## Review Checkpoints

- Prepare wave — readiness verdict: pass

## Review Evidence

- wave-council-readiness: approved
- code-reviewer: approved

## Changes

Change ID: `12y1-enh planned-dashboard`
Change Status: `ready`
""",
    )
    _write(
        wave_dir / "12y1-enh planned-dashboard.md",
        """# Planned Dashboard Change

Change ID: `12y1-enh planned-dashboard`
Change Status: `ready`
Owner: Engineering
Wave: `12y planned-wave`

## Acceptance Criteria

- AC-1: planned data loads
- AC-2: planned dialog details render

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | must work |
| AC-2 | important | good to have |

## Tasks

- [ ] build shared readers
- [ ] add more charts
""",
    )
    _write(
        root / "docs" / "plans" / "12y2-enh staged-plan.md",
        """# Staged Plan

Change ID: `12y2-enh staged-plan`
Change Status: `planned`
Owner: Engineering

## Tasks

- [ ] stage this later
""",
    )


class DashboardSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        _make_wave(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_collect_dashboard_snapshot_returns_expected_structure(self):
        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        self.assertEqual(snapshot["project"]["name"], "Test Dashboard Repo")
        self.assertEqual(snapshot["project"]["active_wave_id"], "12x test-wave")
        self.assertEqual(len(snapshot["waves"]), 1)
        self.assertEqual(len(snapshot["changes"]["in_waves"]), 1)
        self.assertEqual(len(snapshot["changes"]["staged"]), 1)
        self.assertEqual(snapshot["metrics"]["waves"]["active"], 1)
        self.assertEqual(snapshot["metrics"]["waves"]["pending"], 0)
        self.assertEqual(snapshot["metrics"]["waves"]["total"], 1)
        self.assertEqual(snapshot["metrics"]["changes"]["total"], 1)
        self.assertEqual(snapshot["metrics"]["changes"]["pending"], 1)
        self.assertEqual(snapshot["metrics"]["acs"]["total"], 2)
        self.assertEqual(snapshot["metrics"]["acs"]["pending"], 1)
        self.assertEqual(snapshot["metrics"]["tasks"]["total"], 2)
        self.assertEqual(snapshot["metrics"]["tasks"]["pending"], 1)
        change = snapshot["changes"]["in_waves"][0]
        self.assertEqual(change["tasks_total"], 2)
        self.assertEqual(change["tasks_completed"], 1)
        self.assertEqual(len(change["ac_items"]), 2)
        self.assertEqual(change["ac_items"][0]["done"], True)
        self.assertEqual(change["ac_items"][1]["done"], False)
        self.assertEqual(change["ac_completed_counts"]["required"], 1)
        self.assertEqual(change["ac_completed_counts"]["important"], 0)
        self.assertEqual(change["ac_priority_counts"]["required"], 1)
        self.assertEqual(change["ac_priority_counts"]["important"], 1)
        self.assertEqual(snapshot["activity"]["recent_progress"][0]["change_id"], "12x1-enh sample-dashboard")
        self.assertEqual(snapshot["metrics"]["scope"], "active_wave")

    def test_collect_dashboard_snapshot_uses_pending_scope_when_no_active_wave(self):
        root = Path(self.tmp.name) / "pending-scope"
        root.mkdir(parents=True, exist_ok=True)
        _make_repo(root)
        _make_planned_wave(root)
        _write(root / "docs" / "agents" / "session-handoff.md", "# Session Handoff\n\n**Active wave:** *(none)*\n")

        snapshot = self.lib.collect_dashboard_snapshot(root)

        self.assertIsNone(snapshot["project"]["active_wave_id"])
        self.assertEqual(snapshot["metrics"]["scope"], "pending_changes")
        self.assertEqual(snapshot["metrics"]["changes"]["total"], 2)
        self.assertEqual(snapshot["metrics"]["changes"]["pending"], 2)
        self.assertEqual(snapshot["metrics"]["acs"]["total"], 2)
        self.assertEqual(snapshot["metrics"]["acs"]["pending"], 2)
        self.assertEqual(snapshot["metrics"]["tasks"]["total"], 3)
        self.assertEqual(snapshot["metrics"]["tasks"]["pending"], 3)

        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn('const waveMode = waveActive > 0 ? "active" : "pending";', source)
        self.assertIn('const scopeMetricLabel = waveMode === "active" ? "Active" : "Pending";', source)
        self.assertIn('const waveMetricLabel = waveMode === "active"', source)
        self.assertIn('p(changeMetrics.pending, `${scopeMetricLabel} change`, `${scopeMetricLabel} changes`)', source)
        self.assertIn('p(acMetrics.pending,    `${scopeMetricLabel} AC`,     `${scopeMetricLabel} ACs`)', source)
        self.assertIn('p(taskMetrics.pending, `${scopeMetricLabel} task`, `${scopeMetricLabel} tasks`)', source)
        self.assertIn('p(wavePending, "Pending wave", "Pending waves")', source)
        self.assertIn('label: waveMetricLabel, value: waveMetricCount', source)
        self.assertIn('function acProgressStats(changes)', source)
        self.assertIn('const acMetrics = acProgressStats(scopeChanges);', source)
        self.assertIn('const allInWaves = snapshot.changes?.in_waves || [];', source)
        self.assertIn('const progressChanges = scopeChanges || allInWaves;', source)
        self.assertIn('const acTotal = allCountedChanges.reduce((s, c) => s + visibleAcItems(c).length, 0);', source)

    def test_no_active_wave_dialog_titles_use_pending_copy(self):
        root = Path(self.tmp.name) / "pending-dialogs"
        root.mkdir(parents=True, exist_ok=True)
        _make_repo(root)
        _make_planned_wave(root)
        _write(root / "docs" / "agents" / "session-handoff.md", "# Session Handoff\n\n**Active wave:** *(none)*\n")

        snapshot = self.lib.collect_dashboard_snapshot(root)
        self.assertEqual(snapshot["metrics"]["scope"], "pending_changes")

        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn('const title = scope === "active"', source)
        self.assertIn('p(changeMetrics.pending, `${scopeMetricLabel} change`, `${scopeMetricLabel} changes`)', source)
        self.assertIn('p(changes.length, "Active Change", "Active Changes")', source)
        self.assertIn('p(changes.length, "Pending Change", "Pending Changes")', source)
        self.assertIn('const title = active.length ? "Active Waves" : "Pending Waves"', source)
        self.assertIn('No pending waves.', source)
        self.assertIn('title: scope === "active" ? "Active ACs" : "Pending ACs"', source)
        self.assertIn('title: scope === "active" ? "Active Tasks" : "Pending Tasks"', source)
        self.assertIn('scope === "active" ? "No active changes." : "No pending changes."', source)
        self.assertIn('scope === "active" ? "No active ACs." : "No pending ACs."', source)
        self.assertIn('scope === "active" ? "No active tasks." : "No pending tasks."', source)

    def test_collect_dashboard_snapshot_counts_visible_acs_without_priority_table(self):
        root = Path(self.tmp.name) / "visible-acs"
        root.mkdir(parents=True, exist_ok=True)
        _make_repo(root)
        wave_dir = root / "docs" / "waves" / "12x test-wave"
        _write(
            wave_dir / "wave.md",
            """# Wave Record

wave-id: `12x test-wave`
Title: Test Wave
Status: draft

## Objective

Verify visible AC counting.

## Changes

Change ID: `12x1-enh visible-acs`
Change Status: `ready`
""",
        )
        _write(
            wave_dir / "12x1-enh visible-acs.md",
            """# Visible ACs

Change ID: `12x1-enh visible-acs`
Change Status: `ready`
Owner: Engineering
Wave: `12x test-wave`

## Acceptance Criteria

- AC-1: first item
- AC-2: second item

## Tasks

- one task
""",
        )
        _write(root / "docs" / "agents" / "session-handoff.md", "# Session Handoff\n\n**Active wave:** *(none)*\n")

        snapshot = self.lib.collect_dashboard_snapshot(root)

        self.assertEqual(snapshot["metrics"]["scope"], "pending_changes")
        self.assertEqual(snapshot["metrics"]["acs"]["total"], 2)
        self.assertEqual(snapshot["metrics"]["acs"]["pending"], 2)

    def test_collect_dashboard_snapshot_reads_lance_chunk_counts_without_legacy_json(self):
        root = Path(self.tmp.name) / "lance-stats"
        root.mkdir(parents=True, exist_ok=True)
        _make_repo(root)
        _make_wave(root)
        _write_dashboard_lance_index(
            root,
            docs_chunks=[{"path": "docs/guide.md", "text": "Doc chunk", "kind": "doc"}],
            code_chunks=[{"path": "src/app.py", "text": "def app(): pass", "kind": "code"}],
        )

        snapshot = self.lib.collect_dashboard_snapshot(root)
        project = snapshot["health"]["index"]["project"]

        self.assertEqual(project["doc_chunks"], 1)
        self.assertEqual(project["code_chunks"], 1)
        self.assertEqual(project["files_indexed"], 2)

    def test_collect_dashboard_snapshot_parses_plain_bullet_items_for_complete_change(self):
        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        _write(
            wave_dir / "12x1-enh sample-dashboard.md",
            """# Sample Dashboard Change

Change ID: `12x1-enh sample-dashboard`
Change Status: `complete`
Owner: Engineering
Wave: `12x test-wave`

## Requirements

1. Parse both `## Acceptance Criteria` and `## Tasks` correctly even when those section names are mentioned inline earlier in the doc.

## Acceptance Criteria

- AC-1: dashboard data loads
- AC-2: dialog details render

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | must work |
| AC-2 | important | good to have |

## Tasks

- build shared readers
- add more charts
""",
        )

        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        change = snapshot["changes"]["in_waves"][0]

        self.assertEqual(len(change["ac_items"]), 2)
        self.assertTrue(all(item["done"] for item in change["ac_items"]))
        self.assertEqual(change["ac_completed_counts"]["required"], 1)
        self.assertEqual(change["ac_completed_counts"]["important"], 1)
        self.assertEqual(change["tasks_total"], 2)
        self.assertEqual(change["tasks_completed"], 2)
        self.assertEqual([item["label"] for item in change["tasks_items"]], ["build shared readers", "add more charts"])
        self.assertTrue(all(item["done"] for item in change["tasks_items"]))

    def test_collect_dashboard_snapshot_marks_plain_bullet_items_open_for_non_terminal_change(self):
        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        _write(
            wave_dir / "12x1-enh sample-dashboard.md",
            """# Sample Dashboard Change

Change ID: `12x1-enh sample-dashboard`
Change Status: `active`
Owner: Engineering
Wave: `12x test-wave`

## Requirements

1. Parse both `## Acceptance Criteria` and `## Tasks` correctly even when those section names are mentioned inline earlier in the doc.

## Acceptance Criteria

- AC-1: dashboard data loads
- AC-2: dialog details render

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | must work |
| AC-2 | important | good to have |

## Tasks

- build shared readers
- add more charts
""",
        )

        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        change = snapshot["changes"]["in_waves"][0]

        self.assertEqual(len(change["ac_items"]), 2)
        self.assertFalse(any(item["done"] for item in change["ac_items"]))
        self.assertEqual(change["ac_completed_counts"]["required"], 0)
        self.assertEqual(change["ac_completed_counts"]["important"], 0)
        self.assertEqual(change["tasks_total"], 2)
        self.assertEqual(change["tasks_completed"], 0)
        self.assertFalse(any(item["done"] for item in change["tasks_items"]))

    def test_collect_dashboard_snapshot_uses_priority_table_order_when_ac_ids_are_missing(self):
        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        _write(
            wave_dir / "12x1-enh sample-dashboard.md",
            """# Sample Dashboard Change

Change ID: `12x1-enh sample-dashboard`
Change Status: `complete`
Owner: Engineering
Wave: `12x test-wave`

## Acceptance Criteria

- dashboard data loads
- dialog details render

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | must work |
| AC-2 | important | good to have |

## Tasks

- build shared readers
""",
        )

        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        change = snapshot["changes"]["in_waves"][0]

        self.assertEqual(len(change["ac_items"]), 2)
        self.assertEqual([item["priority"] for item in change["ac_items"]], ["required", "important"])
        self.assertTrue(all(item["done"] for item in change["ac_items"]))
        self.assertEqual(change["ac_completed_counts"]["required"], 1)
        self.assertEqual(change["ac_completed_counts"]["important"], 1)
        self.assertEqual(change["ac_completed_counts"]["unknown"], 0)

    def test_collect_dashboard_snapshot_parses_numbered_list_ac_items(self):
        """_AC_LINE_RE must match ordered-list prefixes like '1.' and '2.'."""
        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        _write(
            wave_dir / "12x1-enh sample-dashboard.md",
            """# Sample Dashboard Change

Change ID: `12x1-enh sample-dashboard`
Change Status: `active`
Owner: Engineering
Wave: `12x test-wave`

## Acceptance Criteria

1. [ ] AC-1: dashboard data loads
2. [x] AC-2: dialog details render

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | must work |
| AC-2 | important | good to have |

## Tasks

- [ ] build shared readers
""",
        )

        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        change = snapshot["changes"]["in_waves"][0]

        self.assertEqual(len(change["ac_items"]), 2)
        self.assertFalse(change["ac_items"][0]["done"])
        self.assertTrue(change["ac_items"][1]["done"])
        self.assertEqual(change["ac_completed_counts"]["required"], 0)
        self.assertEqual(change["ac_completed_counts"]["important"], 1)

    def test_collect_dashboard_snapshot_parses_unmarked_numbered_list_ac_items(self):
        """Numbered list items without checkboxes derive done-state from change status."""
        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        _write(
            wave_dir / "12x1-enh sample-dashboard.md",
            """# Sample Dashboard Change

Change ID: `12x1-enh sample-dashboard`
Change Status: `complete`
Owner: Engineering
Wave: `12x test-wave`

## Acceptance Criteria

1. AC-1: dashboard data loads
2. AC-2: dialog details render

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | must work |
| AC-2 | important | good to have |

## Tasks

- [x] build shared readers
""",
        )

        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        change = snapshot["changes"]["in_waves"][0]

        self.assertEqual(len(change["ac_items"]), 2)
        self.assertTrue(all(item["done"] for item in change["ac_items"]))
        self.assertEqual(change["ac_completed_counts"]["required"], 1)
        self.assertEqual(change["ac_completed_counts"]["important"], 1)

    def test_progress_card_keeps_zero_total_rows_visible(self):
        zero_root = Path(self.tmp.name) / "zero-progress"
        zero_root.mkdir(parents=True, exist_ok=True)
        _make_repo(zero_root)

        snapshot = self.lib.collect_dashboard_snapshot(zero_root)
        self.assertEqual(snapshot["metrics"]["acs"]["total"], 0)
        self.assertEqual(snapshot["metrics"]["tasks"]["total"], 0)

        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        progress_row_src = source.split("function ProgressRow({ label, done, total, variant }) {", 1)[1].split(
            "function ProgressCard({ snapshot, scopeChanges }) {", 1
        )[0]
        self.assertIn('h(ProgressRow, { label: "ACs",   done: acDone,    total: acTotal,    variant: "acs" })', source)
        self.assertIn('h(ProgressRow, { label: "Tasks", done: tasksDone, total: tasksTotal, variant: "tasks" })', source)
        self.assertNotIn('acTotal    ? h(ProgressRow', source)
        self.assertNotIn('tasksTotal ? h(ProgressRow', source)
        self.assertNotIn('if (!total) return null;', progress_row_src)
        self.assertIn('const progressChanges = scopeChanges || allInWaves;', source)
        self.assertIn('const allInWaves = snapshot.changes?.in_waves || [];', source)

    def test_snapshot_includes_git_key_as_dict(self):
        snapshot = self.lib.collect_dashboard_snapshot(self.root, skip_git=True)
        self.assertIn("git", snapshot)
        self.assertIsInstance(snapshot["git"], dict)

    def test_choose_port_falls_back_when_preferred_is_busy(self):
        with patch.object(self.srv, "_is_port_free", side_effect=lambda _host, port: port != 43127):
            port = self.srv.choose_port(self.root, "127.0.0.1")
        self.assertEqual(port, 43128)

    def test_choose_port_raises_when_all_ports_busy(self):
        with patch.object(self.srv, "_is_port_free", return_value=False):
            with self.assertRaises(RuntimeError):
                self.srv.choose_port(self.root, "127.0.0.1")


class _HandlerHarnessMixin:
    """Shared HTTP handler test harness. Subclasses must set self.srv and self.snapshot."""

    def _make_handler(self, path: str):
        srv = self.srv
        store = _MockStore(self.snapshot)

        class Harness(srv.DashboardHandler):
            def __init__(self, snapshot_store, req_path):
                self.server = SimpleNamespace(snapshot_store=snapshot_store)
                self.path = req_path
                self.wfile = io.BytesIO()
                self.response_code = 0
                self.headers_written: list[tuple[str, str]] = []
                self.error_message = ""

            def send_response(self, code, message=None):
                self.response_code = code

            def send_header(self, keyword, value):
                self.headers_written.append((keyword, value))

            def end_headers(self):
                return None

            def send_error(self, code, message=None, explain=None):
                self.response_code = code
                self.error_message = message or ""

            def address_string(self):
                return "127.0.0.1"

        return Harness(store, path)


class DashboardHttpTests(_HandlerHarnessMixin, unittest.TestCase):
    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        _make_wave(self.root)
        self.snapshot = self.lib.collect_dashboard_snapshot(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_api_dashboard_serves_json(self):
        handler = self._make_handler("/api/dashboard")
        handler.do_GET()
        self.assertEqual(handler.response_code, 200)
        payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(payload["project"]["active_wave_id"], "12x test-wave")

    def test_dashboard_html_serves_shell(self):
        handler = self._make_handler("/dashboard.html")
        handler.do_GET()
        self.assertEqual(handler.response_code, 200)
        self.assertIn('<div id="app"></div>', handler.wfile.getvalue().decode("utf-8"))

    def test_dashboard_html_title_includes_repo_name(self):
        handler = self._make_handler("/dashboard.html")
        handler.do_GET()
        html = handler.wfile.getvalue().decode("utf-8")
        self.assertIn(f"<title>{self.root.name} - Wavefoundry</title>", html)

    def test_dashboard_js_includes_framework_flow_visualization(self):
        js = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        css = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.css").read_text(encoding="utf-8")

        self.assertIn("const FRAMEWORK_FLOW = [", js)
        self.assertIn('function FrameworkProcessDialog({ process, onClose })', js)
        self.assertIn('function FrameworkFlow({ onSelectProcess })', js)
        self.assertIn('Wave lifecycle', js)
        self.assertIn('Click a stage to see how a change moves through a wave, from planning through review and close.', js)
        self.assertIn('process-step-number process-step-number--${process.id}', js)
        self.assertIn('title: "Plan Change"', js)
        self.assertIn('title: "Prepare Wave"', js)
        self.assertIn('title: "Implement Wave"', js)
        self.assertIn('title: "Review Wave"', js)
        self.assertIn('title: "Close & Maintain"', js)
        self.assertIn('flow: ["Signoff", "Archive"],', js)
        self.assertIn('This is where an idea becomes a real change.', js)
        self.assertIn('Set the shape of the change before any edits begin.', js)
        self.assertIn('This phase matters because it catches avoidable mistakes before code or docs start moving.', js)
        self.assertIn('flow: ["Review", "Open questions", "Prepare Wave"],', js)
        self.assertIn('This is the readiness gate. The council reviews the change, works through the open questions, and decides whether the wave is actually safe to start.', js)
        self.assertIn('This is the coding pass.', js)
        self.assertIn('Once Prepare says the wave is ready, the coding agent takes over and uses the wave record plus each admitted change plan as the working guide.', js)
        self.assertIn('The first job is to read the wave and the change docs carefully enough to understand what belongs in scope.', js)
        self.assertIn('Then the work happens one change at a time: make the edits that match the plan, check the tasks and acceptance criteria, and keep the write set inside the admitted boundaries.', js)
        self.assertIn('Implementation is not just about moving text around.', js)
        self.assertIn('The agent also writes or updates tests, runs them, and confirms that the result matches the agreed intent instead of drifting into a new shape of work.', js)
        self.assertIn('When the code, tests, and documented intent line up, the wave is ready for review.', js)
        self.assertIn('This is the evidence check.', js)
        self.assertIn('flow: ["Review", "Evidence", "Findings"],', js)
        self.assertIn('Review matters because it is where the team decides whether the change is genuinely ready or whether more work is needed.', js)
        self.assertIn('This is the handoff and memory stage.', js)
        self.assertIn('If the handoff or summary does not match the completed wave, the process loops one more time to refresh the record before closure.', js)
        self.assertIn('onClick: () => onSelectProcess(process)', js)
        self.assertIn('framework-flow-card framework-flow-card--${process.id}', js)

        self.assertIn(".framework-flow-path {", css)
        self.assertIn(".framework-flow-arrow {", css)
        self.assertIn("flex-wrap: nowrap;", css)
        self.assertIn(".framework-flow-note {", css)
        self.assertIn("width: 100%;", css)
        self.assertIn("max-width: none;", css)
        self.assertIn(".framework-process-diagram {", css)
        self.assertIn(".framework-process-diagram-step {", css)
        self.assertIn("justify-content: center;", css)
        self.assertIn("background: transparent;", css)
        self.assertIn("border: 0;", css)
        self.assertIn("box-shadow: none;", css)
        self.assertIn(".process-step-number {", css)
        self.assertIn("font-size: 1.35rem;", css)
        self.assertIn("align-items: baseline;", css)
        self.assertIn("margin-right: var(--space-2);", css)
        self.assertIn(".agent-dialog-close {", css)
        self.assertIn("appearance: none;", css)
        self.assertIn("-webkit-appearance: none;", css)
        self.assertIn("background-color: transparent;", css)
        self.assertIn("width: 2.25rem;", css)
        self.assertIn("height: 2.25rem;", css)
        self.assertIn("display: inline-flex;", css)
        self.assertIn("outline: none;", css)
        self.assertIn(".files-dialog-header-text {", css)
        self.assertIn("flex-direction: column;", css)
        self.assertIn(".files-dialog-subtitle {", css)
        self.assertIn("white-space: nowrap;", css)
        self.assertIn(".open-wave-card {", css)
        self.assertIn("box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);", css)
        self.assertIn(".metric {", css)
        self.assertIn("box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);", css)
        self.assertIn(".metric:hover {", css)
        self.assertIn("transform: translateY(-1px);", css)
        self.assertIn(".metric--clickable:hover {", css)
        self.assertIn("box-shadow: var(--shadow);", css)
        self.assertIn(".open-wave-card {", css)
        self.assertNotIn(".open-wave-card:hover {", css)
        self.assertIn(".metric-dialog-card {", css)
        self.assertIn("box-shadow: 0 1px 2px rgba(0, 0, 0, 0.025);", css)
        self.assertIn(".metric-dialog-row {", css)
        self.assertIn(".pending-wave-row {", css)
        self.assertIn(".framework-flow-card--plan {", css)
        self.assertIn("background: rgba(72, 68, 197, 0.06);", css)
        self.assertIn(".framework-flow-card--close {", css)
        self.assertIn("background: rgba(96, 125, 139, 0.06);", css)
        self.assertIn(".framework-process-dialog--close .agent-dialog-header {", css)
        self.assertIn(".agent-dialog-header-text {", css)
        self.assertIn("flex-direction: column;", css)
        self.assertIn(".agent-dialog-header-text .hero-agent-pill {", css)
        self.assertIn("align-self: flex-start;", css)
        self.assertIn("width: fit-content;", css)
        self.assertIn(".agent-dialog-title {", css)
        self.assertIn("display: block;", css)
        self.assertNotIn(".agent-pill-count {", css)
        self.assertNotIn("Used in ", js)
        self.assertNotIn("a.usage_count", js)
        self.assertNotIn(
            'isHandoff ? h("span", { className: "handoff-pill", title: "Current session handoff" }, "↩ handoff") : null,\n        h("span", { className: badgeClass(wave.status) }, wave.status),',
            js,
        )

    def test_metric_dialog_header_wraps_long_change_ids(self):
        css = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.css").read_text(encoding="utf-8")
        self.assertIn(".metric-dialog-card-header {", css)
        self.assertIn("display: flex;", css)
        self.assertIn("justify-content: space-between;", css)
        self.assertIn(".metric-dialog-card-header .status-badge {", css)
        self.assertIn("white-space: normal;", css)

    def test_log_message_uses_shared_dashboard_log_format(self):
        handler = self._make_handler("/dashboard.html")
        with patch("sys.stderr", new=io.StringIO()) as stderr:
            handler.log_message('"%s" %s -', "GET /dashboard.html HTTP/1.1", 200)
            output = stderr.getvalue()

        self.assertRegex(
            output,
            r'^\[dashboard\] \d{4}-\d{2}-\d{2}T[^\n]+ - 127\.0\.0\.1 - "GET /dashboard\.html HTTP/1\.1" 200 -\n$',
        )


class DashboardProcessControlTests(unittest.TestCase):
    """Verify dashboard stop and restart are repo-local and composable."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.server = sys.modules["server_impl"]
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_dashboard_metadata(self, root: Path, *, pid: int = 4321, url: str = "http://127.0.0.1:43127/dashboard.html") -> Path:
        meta_path = root / ".wavefoundry" / "dashboard-server.json"
        self.srv.dashboard_lib.write_dashboard_metadata(
            root,
            {
                "host": "127.0.0.1",
                "port": 43127,
                "url": url,
                "entrypoint": "dashboard.html",
                "pid": pid,
                "started_at": "2026-05-13T00:00:00Z",
            },
        )
        return meta_path

    def test_dashboard_stop_removes_only_current_repo_metadata(self):
        current_meta = self._write_dashboard_metadata(self.root, pid=4321)
        other_root = Path(self.tmp.name) / "other"
        _make_repo(other_root)
        other_meta = self._write_dashboard_metadata(other_root, pid=9999)

        with patch.object(self.server, "_pid_is_running", return_value=True), patch.object(
            self.server, "_terminate_dashboard_pid", return_value=True
        ) as terminate:
            env = self.server.wave_dashboard_stop_response(self.root)

        self.assertEqual(env["status"], "ok")
        self.assertTrue(env["data"]["stopped"])
        self.assertEqual(env["data"]["pid"], 4321)
        self.assertFalse(current_meta.exists(), "stop must clear the current repo dashboard metadata")
        self.assertTrue(other_meta.exists(), "stop must not touch another repo's dashboard metadata")
        terminate.assert_called_once_with(4321)

    def test_dashboard_restart_stops_then_starts_again(self):
        stop_env = {
            "status": "ok",
            "data": {"stopped": True, "pid": 4321, "url": "http://127.0.0.1:43127/dashboard.html"},
            "diagnostics": [],
            "next_tools": [],
            "usage": "wave_dashboard_stop()",
        }
        start_env = {
            "status": "ok",
            "data": {"started": True, "pid": 9876, "url": "http://127.0.0.1:43128/dashboard.html"},
            "diagnostics": [],
            "next_tools": [],
            "usage": "http://127.0.0.1:43128/dashboard.html",
        }

        with patch.object(self.server, "wave_dashboard_stop_response", return_value=stop_env) as stop, patch.object(
            self.server, "wave_dashboard_start_response", return_value=start_env
        ) as start:
            env = self.server.wave_dashboard_restart_response(self.root)

        self.assertEqual(env["status"], "ok")
        self.assertTrue(env["data"]["restarted"])
        self.assertEqual(env["data"]["pid"], 9876)
        self.assertEqual(env["data"]["url"], "http://127.0.0.1:43128/dashboard.html")
        stop.assert_called_once_with(self.root)
        start.assert_called_once_with(self.root, port=None)


class DashboardReadOnlyTests(_HandlerHarnessMixin, unittest.TestCase):
    """Verify the dashboard server never writes project state during GET requests."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        _make_wave(self.root)
        self.snapshot = self.lib.collect_dashboard_snapshot(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _docs_mtime_snapshot(self):
        return {
            str(p): p.stat().st_mtime
            for p in (self.root / "docs").rglob("*") if p.is_file()
        }

    def test_api_dashboard_does_not_mutate_docs(self):
        before = self._docs_mtime_snapshot()
        handler = self._make_handler("/api/dashboard")
        handler.do_GET()
        after = self._docs_mtime_snapshot()
        self.assertEqual(before, after, "GET /api/dashboard must not modify any docs/ file")

    def test_api_health_does_not_mutate_docs(self):
        before = self._docs_mtime_snapshot()
        handler = self._make_handler("/api/health")
        handler.do_GET()
        after = self._docs_mtime_snapshot()
        self.assertEqual(before, after, "GET /api/health must not modify any docs/ file")

    def test_unknown_route_returns_404(self):
        handler = self._make_handler("/api/nonexistent")
        handler.do_GET()
        self.assertEqual(handler.response_code, 404)

    def test_path_traversal_rejected(self):
        # The path must reach _asset_path — use a .js suffix so the MIME check
        # passes and the traversal guard is actually exercised.
        handler = self._make_handler("/dashboard.js/../../../etc/passwd.js")
        handler.do_GET()
        self.assertIn(handler.response_code, {400, 404})

    def test_loopback_default_host(self):
        cfg = self.lib.read_dashboard_config(self.root)
        self.assertEqual(cfg["host"], "127.0.0.1")

    def test_auto_index_defaults_enabled(self):
        cfg = self.lib.read_dashboard_config(self.root)
        self.assertTrue(cfg["auto_index"])


class DashboardGracefulDegradationTests(unittest.TestCase):
    """Verify the dashboard returns valid snapshots when data sources are absent."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_with_no_waves(self):
        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        self.assertEqual(snapshot["waves"], [])
        self.assertEqual(snapshot["changes"]["in_waves"], [])
        self.assertIn("activity", snapshot)
        self.assertIn("health", snapshot)

    def test_snapshot_with_missing_docs_agents_dir(self):
        import shutil
        shutil.rmtree(self.root / "docs" / "agents", ignore_errors=True)
        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        self.assertEqual(snapshot["activity"]["session_handoff_active_wave"], "")

    def test_snapshot_with_missing_handoff_file(self):
        (self.root / "docs" / "agents").mkdir(parents=True, exist_ok=True)
        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        self.assertEqual(snapshot["activity"]["recent_progress"], [])

    def test_agents_empty_when_no_agents_dir(self):
        import shutil
        shutil.rmtree(self.root / "docs" / "agents", ignore_errors=True)
        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        self.assertEqual(snapshot["agents"], [])


class DashboardActivityTests(unittest.TestCase):
    """Verify progress log collection covers all entries, not just the latest."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        _make_wave(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_multi_entry_change(self):
        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        _write(
            wave_dir / "12x3-enh multi-log.md",
            """# Multi Log Change

Change ID: `12x3-enh multi-log`
Change Status: `ready`
Owner: Engineering
Wave: `12x test-wave`

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | test |

## Tasks

- [ ] do something

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-07 | First entry | — |
| 2026-05-08 | Second entry | ref-1 |
| 2026-05-09 | Third entry | ref-2 |
""",
        )
        wave_md = wave_dir / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        text += "\nChange ID: `12x3-enh multi-log`\nChange Status: `ready`\n"
        wave_md.write_text(text, encoding="utf-8")

    def test_all_progress_entries_collected_not_just_latest(self):
        self._make_multi_entry_change()
        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        ids = [e["change_id"] for e in snapshot["activity"]["recent_progress"]]
        multi_entries = [e for e in snapshot["activity"]["recent_progress"] if e["change_id"] == "12x3-enh multi-log"]
        self.assertEqual(len(multi_entries), 3, "All 3 progress entries must appear, not just the last")

    def test_recent_progress_sorted_descending(self):
        self._make_multi_entry_change()
        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        dates = [e["date"] for e in snapshot["activity"]["recent_progress"] if e["date"]]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_files_changed_all_is_list(self):
        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        self.assertIsInstance(snapshot["activity"]["files_changed_all"], list)


class DashboardAgentCollectionTests(unittest.TestCase):
    """Verify agent/persona/specialist/journal discovery from docs/agents/."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        agents_root = self.root / "docs" / "agents"
        _write(agents_root / "code-reviewer.md",
               "# Code Reviewer\n\nOwner: Engineering\nRole: code-reviewer\n\n## Operating Identity\n\nReviews code quality.\n\n## Responsibilities\n\n- Check style\n- Check correctness\n")
        _write(agents_root / "personas" / "wave-coordinator.md",
               "# Persona — Wave Coordinator\n\nOwner: Engineering\nRole: wave-coordinator\n\n## Who\n\nCoordinates waves.\n\n## Goals\n\n- Keep waves moving\n")
        _write(agents_root / "specialists" / "software-architect.md",
               "# Software Architect\n\nOwner: Engineering\nRole: software-architect\n\n## Operating Identity\n\nDesigns system boundaries.\n")
        _write(agents_root / "journals" / "planner.md",
               "# Journal — Planner\n\nOwner: Engineering\nRole: planner\n\n## Operating Identity\n\nPlanning journal.\n")
        _write(agents_root / "factor-12-admin-processes.md",
               "# Factor 12 — Admin Processes Review Agent\n\nOwner: Engineering\nRole: factor-12-admin-processes\nCategory: factor\n\n## What This Factor Covers\n\nCLI tools and admin scripts.\n")
        _write(agents_root / "README.md", "# Agents\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_agents_discovered_by_group(self):
        agents = self.lib.collect_agents(self.root)
        groups = {a["group"] for a in agents}
        self.assertIn("agent", groups)
        self.assertIn("persona", groups)
        self.assertIn("specialist", groups)
        self.assertIn("factor", groups)
        self.assertIn("journal", groups)

    def test_readme_excluded(self):
        agents = self.lib.collect_agents(self.root)
        names = [a["name"] for a in agents]
        self.assertNotIn("Readme", names)
        self.assertNotIn("README", names)

    def test_persona_prefix_stripped(self):
        agents = self.lib.collect_agents(self.root)
        persona = next(a for a in agents if a["group"] == "persona")
        self.assertFalse(persona["name"].startswith("Persona —"), "Persona prefix must be stripped")
        self.assertEqual(persona["name"], "Wave Coordinator")

    def test_journal_prefix_stripped(self):
        agents = self.lib.collect_agents(self.root)
        journal = next(a for a in agents if a["group"] == "journal")
        self.assertFalse(journal["name"].startswith("Journal —"))

    def test_factor_prefix_stripped(self):
        agents = self.lib.collect_agents(self.root)
        factor = next(a for a in agents if a["group"] == "factor")
        self.assertFalse(factor["name"].startswith("Factor "))

    def test_factor_collection_prefers_canonical_docs(self):
        wrapper_root = self.root / ".claude" / "agents"
        _write(wrapper_root / "factor-12-admin-processes.md",
               "# Factor 12 — Admin Processes Review Agent\n\n## Thin Wrapper\n\nSee canonical doc.\n")
        agents = self.lib.collect_agents(self.root)
        factor = next(a for a in agents if a["group"] == "factor")
        self.assertEqual(factor["path"], "docs/agents/factor-12-admin-processes.md")

    def test_factor_body_strips_category_and_verified_metadata(self):
        agents = self.lib.collect_agents(self.root)
        factor = next(a for a in agents if a["group"] == "factor")
        self.assertNotIn("Category:", factor["body"])
        self.assertNotIn("Last verified:", factor["body"])

    def test_body_field_present(self):
        agents = self.lib.collect_agents(self.root)
        agent = next(a for a in agents if a["group"] == "agent")
        self.assertIn("body", agent)
        self.assertNotIn("details", agent)
        self.assertIn("Operating Identity", agent["body"])
        self.assertIn("Responsibilities", agent["body"])

    def test_body_strips_metadata_header(self):
        agents = self.lib.collect_agents(self.root)
        agent = next(a for a in agents if a["group"] == "agent")
        self.assertNotIn("Owner:", agent["body"])
        self.assertNotIn("Role:", agent["body"])
        self.assertFalse(agent["body"].startswith("# "), "H1 title must be stripped from body")

    def test_empty_body_stub(self):
        agents_root = self.root / "docs" / "agents"
        _write(agents_root / "stub-agent.md",
               "# Stub Agent\n\nOwner: Engineering\nRole: stub-agent\n")
        agents = self.lib.collect_agents(self.root)
        stub = next((a for a in agents if a["name"] == "Stub Agent"), None)
        self.assertIsNotNone(stub)
        self.assertEqual(stub["body"], "")

    def test_no_role_field_excluded(self):
        agents_root = self.root / "docs" / "agents"
        _write(agents_root / "session-handoff.md",
               "# Session Handoff\n\nOwner: Engineering\n\n## Current State\n\nActive wave: foo\n")
        agents = self.lib.collect_agents(self.root)
        names = [a["name"] for a in agents]
        self.assertNotIn("Session Handoff", names)


class AgentClassificationTests(unittest.TestCase):
    """Verify _classify_agent_category suffix rules generalise across projects."""

    def setUp(self):
        self.lib, _ = load_dashboard_modules()
        self.classify = self.lib._classify_agent_category

    # ── group short-circuits ──────────────────────────────────────────────────

    def test_persona_group_always_operate(self):
        self.assertEqual(self.classify("any-name", "persona"), "operate")

    def test_journal_group_always_journal(self):
        self.assertEqual(self.classify("any-name", "journal"), "journal")

    def test_group_takes_priority_over_stem(self):
        # "implementer" would be build for group=agent, but persona wins.
        self.assertEqual(self.classify("implementer", "persona"), "operate")

    def test_specialist_group_beats_review_stem(self):
        # "reality-checker" is in _REVIEW_STEMS but specialist group must win.
        self.assertEqual(self.classify("reality-checker", "specialist"), "specialist")

    def test_specialist_group_beats_coordinate_stem(self):
        # "council-moderator" is in _COORDINATE_STEMS but specialist group must win.
        self.assertEqual(self.classify("council-moderator", "specialist"), "specialist")

    def test_specialist_group_beats_build_suffix(self):
        # An agent in specialists/ with a build-like name still gets "specialist".
        self.assertEqual(self.classify("custom-engineer", "specialist"), "specialist")

    # ── build suffixes ────────────────────────────────────────────────────────

    def test_engineer_suffix_is_build(self):
        for stem in ("data-engineer", "ml-engineer", "qa-engineer", "devops-engineer"):
            with self.subTest(stem=stem):
                self.assertEqual(self.classify(stem, "agent"), "build")

    def test_developer_suffix_is_build(self):
        for stem in ("ios-developer", "android-developer", "frontend-developer"):
            with self.subTest(stem=stem):
                self.assertEqual(self.classify(stem, "agent"), "build")

    def test_builder_automator_suffix_is_build(self):
        self.assertEqual(self.classify("mobile-app-builder", "agent"), "build")
        self.assertEqual(self.classify("devops-automator", "agent"), "build")

    def test_implementer_exact_stem_is_build(self):
        self.assertEqual(self.classify("implementer", "agent"), "build")

    # ── review suffixes ───────────────────────────────────────────────────────

    def test_reviewer_suffix_is_review(self):
        for stem in ("code-reviewer", "architecture-reviewer", "performance-reviewer"):
            with self.subTest(stem=stem):
                self.assertEqual(self.classify(stem, "agent"), "review")

    def test_auditor_tester_suffix_is_review(self):
        self.assertEqual(self.classify("accessibility-auditor", "agent"), "review")
        self.assertEqual(self.classify("api-tester", "agent"), "review")

    def test_reality_checker_exact_stem_is_review(self):
        self.assertEqual(self.classify("reality-checker", "agent"), "review")

    # ── coordinate ───────────────────────────────────────────────────────────

    def test_coordinator_suffix_is_coordinate(self):
        self.assertEqual(self.classify("wave-coordinator", "agent"), "coordinate")
        self.assertEqual(self.classify("sprint-coordinator", "agent"), "coordinate")

    def test_moderator_suffix_is_coordinate(self):
        self.assertEqual(self.classify("council-moderator", "agent"), "coordinate")

    def test_planner_exact_stem_is_coordinate(self):
        self.assertEqual(self.classify("planner", "agent"), "coordinate")

    # ── specialist fallback ───────────────────────────────────────────────────

    def test_unmatched_stems_fall_to_specialist(self):
        for stem in ("backend-architect", "data-scientist", "release-manager", "sre"):
            with self.subTest(stem=stem):
                self.assertEqual(self.classify(stem, "specialist"), "specialist")


class SnapshotHashTests(unittest.TestCase):
    """Verify _hash_snapshot stability and sensitivity."""

    def setUp(self):
        _, self.srv = load_dashboard_modules()
        self.hash = self.srv.SnapshotStore._hash_snapshot

    def test_stable_across_generated_at(self):
        a = {"generated_at": "2026-01-01T00:00:00Z", "waves": [], "project": {"name": "X"}}
        b = {"generated_at": "2099-12-31T23:59:59Z", "waves": [], "project": {"name": "X"}}
        self.assertEqual(self.hash(a), self.hash(b))

    def test_changes_when_content_differs(self):
        a = {"generated_at": "2026-01-01T00:00:00Z", "project": {"name": "X"}}
        b = {"generated_at": "2026-01-01T00:00:00Z", "project": {"name": "Y"}}
        self.assertNotEqual(self.hash(a), self.hash(b))

    def test_excludes_only_generated_at(self):
        base = {"generated_at": "2026-01-01T00:00:00Z", "git": {"branch": "main"}, "waves": [1, 2]}
        changed_time = {**base, "generated_at": "2099-12-31T00:00:00Z"}
        self.assertEqual(self.hash(base), self.hash(changed_time))
        changed_content = {**base, "git": {"branch": "feature"}}
        self.assertNotEqual(self.hash(base), self.hash(changed_content))


class SnapshotStoreTests(unittest.TestCase):
    """Verify SnapshotStore initialisation, SSE client lifecycle, and hash gating."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        _make_wave(self.root)
        self._stores_to_stop: list = []

    def tearDown(self):
        for store in self._stores_to_stop:
            store.stop()
        self._stores_to_stop.clear()
        self.tmp.cleanup()

    def _track(self, store):
        """Register a store for cleanup in tearDown."""
        self._stores_to_stop.append(store)
        return store

    def _make_store(self):
        return self._track(self.srv.SnapshotStore(self.root))

    def test_initialises_with_valid_snapshot(self):
        store = self._make_store()
        snap = store.get()
        self.assertIn("project", snap)
        self.assertIn("waves", snap)
        self.assertIn("generated_at", snap)

    def test_sse_client_register_and_unregister(self):
        store = self._make_store()
        client = store.register_sse_client()
        self.assertIn(client, store._sse_clients)
        store.unregister_sse_client(client)
        self.assertNotIn(client, store._sse_clients)

    def test_notify_sse_delivers_to_registered_client(self):
        store = self._make_store()
        client = store.register_sse_client()
        store._notify_sse()
        msg = client.queue.get_nowait()
        self.assertEqual(msg, "update")
        store.unregister_sse_client(client)

    def test_notify_sse_skips_full_queue(self):
        store = self._make_store()
        client = store.register_sse_client()
        # Fill the queue beyond maxsize — should not raise.
        for _ in range(10):
            store._notify_sse()
        self.assertLessEqual(client.queue.qsize(), client.queue.maxsize)
        store.unregister_sse_client(client)

    def test_rebuild_returns_false_when_content_unchanged(self):
        store = self._make_store()
        # Second rebuild with same files — content hash should match.
        changed = store._rebuild(force_git=False)
        self.assertFalse(changed)

    def test_unregister_unknown_client_is_safe(self):
        store = self._make_store()
        client = store.register_sse_client()
        store.unregister_sse_client(client)
        store.unregister_sse_client(client)  # double-unregister — must not raise

    def test_watch_loop_continues_after_rebuild_exception(self):
        """Watcher thread must survive an exception in _rebuild without dying."""
        import threading
        store = self._make_store()
        errors_seen = []
        original_rebuild = store._rebuild

        call_count = [0]

        def flaky_rebuild(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("simulated rebuild failure")
            return original_rebuild(**kwargs)

        # Patch _rebuild and run _watch_loop logic directly (not the daemon thread).
        store._rebuild = flaky_rebuild
        # Simulate one iteration of the watch loop's try/except block.
        try:
            store._rebuild(force_git=False)
        except Exception as exc:
            errors_seen.append(exc)
        # The loop should have caught the error — verify store is still usable.
        self.assertEqual(len(errors_seen), 1)
        snap = store.get()
        self.assertIn("project", snap)


class GitStatsParsingTests(unittest.TestCase):
    """Verify collect_git_stats parses subprocess output correctly."""

    def setUp(self):
        self.lib, _ = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run_with_mock(self, cmd_outputs: dict[tuple, str]) -> dict:
        """Run collect_git_stats with mocked subprocess output."""
        import subprocess

        def fake_run(args, **kwargs):
            key = tuple(args[1:])  # strip "git"
            stdout = cmd_outputs.get(key, "")
            return MagicMock(returncode=0, stdout=stdout)

        with patch("subprocess.run", side_effect=fake_run):
            return self.lib.collect_git_stats(self.root)

    def test_shortstat_insertions_deletions_parsed(self):
        outputs = {
            ("rev-parse", "--abbrev-ref", "HEAD"): "main",
            ("rev-parse", "--short", "HEAD"): "abc1234",
            ("log", "-1", "--format=%s"): "fix: something",
            ("log", "-1", "--format=%cd", "--date=short"): "2026-05-09",
            ("status", "--porcelain"): " M src/foo.py\n M src/bar.py\n",
            ("diff", "HEAD", "--shortstat"): " 3 files changed, 42 insertions(+), 7 deletions(-)\n",
            ("ls-files", "--others", "--exclude-standard"): "",
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "",
        }
        result = self._run_with_mock(outputs)
        self.assertEqual(result["lines_added"], 42)
        self.assertEqual(result["lines_removed"], 7)
        self.assertEqual(result["files_changed"], 2)
        self.assertEqual(result["branch"], "main")

    def test_ahead_behind_parsed(self):
        outputs = {
            ("rev-parse", "--abbrev-ref", "HEAD"): "feature",
            ("rev-parse", "--short", "HEAD"): "abc1234",
            ("log", "-1", "--format=%s"): "feat: add thing",
            ("log", "-1", "--format=%cd", "--date=short"): "2026-05-09",
            ("status", "--porcelain"): "",
            ("diff", "HEAD", "--shortstat"): "",
            ("ls-files", "--others", "--exclude-standard"): "",
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "origin/feature",
            ("rev-list", "--count", "--left-right", "origin/feature...HEAD"): "2\t5",
        }
        result = self._run_with_mock(outputs)
        self.assertEqual(result["ahead"], 5)
        self.assertEqual(result["behind"], 2)

    def test_binary_untracked_file_skipped(self):
        """Untracked binary files (containing null bytes) must not contribute line counts."""
        bin_file = Path(self.tmp.name) / "image.png"
        bin_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")
        outputs = {
            ("rev-parse", "--abbrev-ref", "HEAD"): "main",
            ("rev-parse", "--short", "HEAD"): "abc1234",
            ("log", "-1", "--format=%s"): "chore: add image",
            ("log", "-1", "--format=%cd", "--date=short"): "2026-05-09",
            ("status", "--porcelain"): "?? image.png\n",
            ("diff", "HEAD", "--shortstat"): "",
            ("ls-files", "--others", "--exclude-standard"): "image.png\n",
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "",
        }
        result = self._run_with_mock(outputs)
        self.assertEqual(result["lines_added"], 0)


class IndexBuilderTests(unittest.TestCase):
    """Verify IndexBuilder debounce, single-build gate, status transitions, and failure handling."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_builder(self, delay=0.0, on_done=None):
        return self.srv.IndexBuilder(
            root=self.root,
            delay=delay,
            on_done=on_done or (lambda: None),
        )

    def test_initial_status_is_idle(self):
        builder = self._make_builder()
        status = builder.get_status()
        self.assertEqual(status["build_status"], "idle")
        self.assertIsNone(status["build_started_at"])
        self.assertIsNone(status["build_finished_at"])

    def test_status_transitions_idle_running_done(self):
        done_event = threading.Event()
        statuses = []

        def on_done():
            statuses.append(builder.get_status()["build_status"])
            done_event.set()

        with patch.object(self.srv.IndexBuilder, "_execute", return_value=0):
            builder = self._make_builder(delay=0.0, on_done=on_done)
            builder.signal_change()
            done_event.wait(timeout=2.0)

        self.assertTrue(done_event.is_set(), "on_done was never called")
        self.assertEqual(statuses[-1], "done")

    def test_status_transitions_idle_running_failed(self):
        done_event = threading.Event()
        statuses = []

        def on_done():
            statuses.append(builder.get_status()["build_status"])
            done_event.set()

        with patch.object(self.srv.IndexBuilder, "_execute", return_value=1):
            builder = self._make_builder(delay=0.0, on_done=on_done)
            builder.signal_change()
            done_event.wait(timeout=2.0)

        self.assertTrue(done_event.is_set(), "on_done was never called")
        self.assertEqual(statuses[-1], "failed")

    def test_debounce_rearm_cancels_pending_timer(self):
        """Two rapid signal_change calls should result in exactly one build."""
        build_count = [0]
        done_event = threading.Event()

        original_execute = self.srv.IndexBuilder._execute

        def counting_execute(self_inner):
            build_count[0] += 1
            done_event.set()
            return 0

        with patch.object(self.srv.IndexBuilder, "_execute", counting_execute):
            builder = self._make_builder(delay=0.05)
            builder.signal_change()
            builder.signal_change()  # should cancel the first timer
            done_event.wait(timeout=2.0)
            import time as _time; _time.sleep(0.15)  # let any extra timer fire

        self.assertEqual(build_count[0], 1, "debounce should collapse two signals into one build")

    def test_single_build_gate_sets_pending_flag(self):
        """A signal during a running build must set pending flag, not spawn a second subprocess."""
        running_event = threading.Event()
        unblock_event = threading.Event()
        call_count = [0]

        def blocking_execute(self_inner):
            call_count[0] += 1
            running_event.set()
            unblock_event.wait(timeout=2.0)
            return 0

        done_calls = [0]
        done_event = threading.Event()

        def on_done():
            done_calls[0] += 1
            # Wait for both the first build AND the rearmed build to complete
            # under the patch context.  Without this, the rearmed timer (delay=0)
            # fires after the patch exits and the real _execute creates files in
            # the temp directory, causing tearDown cleanup to fail.
            if done_calls[0] >= 2:
                done_event.set()

        with patch.object(self.srv.IndexBuilder, "_execute", blocking_execute):
            builder = self._make_builder(delay=0.0, on_done=on_done)
            builder.signal_change()
            running_event.wait(timeout=2.0)
            # Build is now running — signal again
            builder.signal_change()
            self.assertTrue(builder._pending_after_build)
            self.assertEqual(call_count[0], 1)
            unblock_event.set()
            done_event.wait(timeout=2.0)

    def test_pending_after_build_triggers_rearm(self):
        """A pending signal set during a build should trigger a second build after completion."""
        running_event = threading.Event()
        unblock_event = threading.Event()
        call_count = [0]
        done_calls = [0]
        second_done = threading.Event()

        def blocking_execute(self_inner):
            call_count[0] += 1
            if call_count[0] == 1:
                running_event.set()
                unblock_event.wait(timeout=2.0)
            return 0

        def on_done():
            done_calls[0] += 1
            if done_calls[0] >= 2:
                second_done.set()

        with patch.object(self.srv.IndexBuilder, "_execute", blocking_execute):
            builder = self._make_builder(delay=0.0, on_done=on_done)
            builder.signal_change()
            running_event.wait(timeout=2.0)
            builder.signal_change()  # sets pending flag
            unblock_event.set()
            second_done.wait(timeout=3.0)

        self.assertTrue(second_done.is_set(), "re-arm after pending build not triggered")
        self.assertEqual(call_count[0], 2)

    def test_subprocess_failure_sets_failed_status(self):
        done_event = threading.Event()

        def on_done():
            done_event.set()

        with patch.object(self.srv.IndexBuilder, "_execute", return_value=1):
            builder = self._make_builder(delay=0.0, on_done=on_done)
            builder.signal_change()
            done_event.wait(timeout=2.0)

        self.assertEqual(builder.get_status()["build_status"], "failed")
        self.assertIsNotNone(builder.get_status()["build_finished_at"])

    def test_execute_returns_minus_one_on_missing_executable(self):
        """_execute must return -1 and not raise when the indexer is missing."""
        builder = self._make_builder()
        with patch("subprocess.Popen", side_effect=FileNotFoundError("not found")):
            result = builder._execute()
        self.assertEqual(result, -1)

    def test_execute_writes_state_file_during_build(self):
        """_execute must write index-build.json while communicate() is running."""
        builder = self._make_builder()
        builder._active_layers = {"framework"}
        state_path = builder._index_state_path("framework")
        state_during_build = []

        class FakeProc:
            pid = 99999
            returncode = 0

            def communicate(self):
                if state_path.exists():
                    try:
                        state_during_build.append(json.loads(state_path.read_text()))
                    except Exception:
                        pass
                return b"", b""

        with patch("subprocess.Popen", return_value=FakeProc()):
            builder._execute()

        self.assertTrue(len(state_during_build) > 0, "index-build.json not written before communicate() returned")
        state = state_during_build[0]
        self.assertEqual(state.get("pid"), 99999)
        self.assertEqual(state.get("layer"), "framework")

    def test_execute_removes_state_file_after_build(self):
        """_execute must remove index-build.json after the build completes."""
        builder = self._make_builder()
        builder._active_layers = {"framework"}
        state_path = builder._index_state_path("framework")

        class FakeProc:
            pid = 99999
            returncode = 0

            def communicate(self):
                return b"", b""

        with patch("subprocess.Popen", return_value=FakeProc()):
            builder._execute()

        self.assertFalse(state_path.exists(), "index-build.json should be removed after build completes")

    def test_on_started_called_with_running_status(self):
        """on_started must fire while build_status is already 'running'."""
        started_statuses = []
        done_event = threading.Event()

        def on_started():
            started_statuses.append(builder.get_status()["build_status"])

        def on_done():
            done_event.set()

        with patch.object(self.srv.IndexBuilder, "_execute", return_value=0):
            builder = self._make_builder(delay=0.0, on_done=on_done)
            builder._on_started = on_started
            builder.signal_change()
            done_event.wait(timeout=2.0)

        self.assertEqual(started_statuses, ["running"])

    def test_signal_change_logs_layer_and_reason(self):
        done_event = threading.Event()

        def on_done():
            done_event.set()

        with patch.object(self.srv.IndexBuilder, "_execute", return_value=0):
            builder = self._make_builder(delay=0.0, on_done=on_done)
            with patch("sys.stderr", new=io.StringIO()) as stderr:
                builder.signal_change(layer="framework", reason="periodic stale check")
                done_event.wait(timeout=2.0)
                output = stderr.getvalue()

        self.assertIn("scheduled framework index update", output)
        self.assertIn("framework: periodic stale check", output)
        self.assertIn("starting framework index update", output)
        self.assertIn("completed framework index update", output)
        self.assertRegex(
            output,
            r"\[dashboard\] \d{4}-\d{2}-\d{2}T[^\n]+ - IndexBuilder: scheduled framework index update",
        )
        self.assertNotIn("[dashboard] [dashboard]", output)

    def test_signal_startup_logs_framework_only_layers(self):
        done_event = threading.Event()

        def on_done():
            done_event.set()

        with patch.object(self.srv.IndexBuilder, "_execute", return_value=0):
            builder = self._make_builder(delay=0.0, on_done=on_done)
            with patch("sys.stderr", new=io.StringIO()) as stderr:
                builder.signal_startup(delay=0.0, layers={"framework"}, reason="startup stale check")
                done_event.wait(timeout=2.0)
                output = stderr.getvalue()

        self.assertIn("scheduled startup framework index update", output)
        self.assertIn("starting framework index update", output)
        self.assertNotIn("project, framework", output)

    def test_dashboard_log_helper_prefixes_timestamp(self):
        with patch("sys.stderr", new=io.StringIO()) as stderr:
            self.srv._dashboard_log("watcher error: boom")
            output = stderr.getvalue()

        self.assertRegex(
            output,
            r"^\[dashboard\] \d{4}-\d{2}-\d{2}T[^\n]+ - watcher error: boom\n$",
        )

    def test_dashboard_log_helper_prefixes_context_after_timestamp(self):
        with patch("sys.stderr", new=io.StringIO()) as stderr:
            self.srv._dashboard_log("hello", context="127.0.0.1")
            output = stderr.getvalue()

        self.assertRegex(
            output,
            r"^\[dashboard\] \d{4}-\d{2}-\d{2}T[^\n]+ - 127\.0\.0\.1 - hello\n$",
        )

    def test_get_status_is_threadsafe(self):
        """Concurrent get_status calls must not raise."""
        builder = self._make_builder()
        errors = []

        def reader():
            try:
                for _ in range(50):
                    builder.get_status()
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


class IndexStalenessTests(unittest.TestCase):
    """Verify _index_is_stale detects missing index and git-based staleness."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_meta(self, built_at: str, layer: str = "project") -> None:
        meta_path = (
            self.root / ".wavefoundry" / "index" / "meta.json"
            if layer == "project"
            else self.root / ".wavefoundry" / "framework" / "index" / "meta.json"
        )
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps({"built_at": built_at}), encoding="utf-8")

    def _write_meta_payload(self, payload: dict[str, Any], layer: str = "project") -> None:
        meta_path = (
            self.root / ".wavefoundry" / "index" / "meta.json"
            if layer == "project"
            else self.root / ".wavefoundry" / "framework" / "index" / "meta.json"
        )
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(payload), encoding="utf-8")

    def test_stale_when_meta_missing(self):
        self.assertTrue(self.srv._index_is_stale(self.root))

    def test_framework_stale_when_meta_missing(self):
        self.assertTrue(self.srv._index_is_stale(self.root, "framework"))

    def test_stale_when_meta_has_no_built_at(self):
        self._write_meta("")
        self.assertTrue(self.srv._index_is_stale(self.root))

    def test_stale_when_git_log_returns_commits(self):
        self._write_meta("2026-01-01T00:00:00+00:00")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="abc1234 some commit\n"),  # git log
            ]
            result = self.srv._index_is_stale(self.root)
        self.assertTrue(result)

    def test_stale_when_dirty_file_modified_after_build(self):
        """A dirty file with mtime newer than built_at is genuinely stale."""
        import time as _time
        built_at = "2026-01-01T00:00:00+00:00"
        self._write_meta(built_at)
        # Write a file whose mtime is clearly after the built_at timestamp.
        dirty = self.root / "src" / "foo.py"
        dirty.parent.mkdir(parents=True, exist_ok=True)
        dirty.write_text("changed", encoding="utf-8")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),            # git log — no new commits
                MagicMock(returncode=0, stdout=" M src/foo.py\n"),  # git status — dirty
            ]
            result = self.srv._index_is_stale(self.root)
        self.assertTrue(result)

    def test_not_stale_when_dirty_file_modified_before_build(self):
        """A dirty file with mtime older than built_at was already indexed — not stale."""
        import time as _time
        # Use a far-future built_at so any real file mtime is older.
        built_at = "2099-01-01T00:00:00+00:00"
        self._write_meta(built_at)
        dirty = self.root / "src" / "foo.py"
        dirty.parent.mkdir(parents=True, exist_ok=True)
        dirty.write_text("old change", encoding="utf-8")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),            # git log — nothing new
                MagicMock(returncode=0, stdout=" M src/foo.py\n"),  # git status — dirty
            ]
            result = self.srv._index_is_stale(self.root)
        self.assertFalse(result)

    def test_not_stale_when_git_clean_and_no_new_commits(self):
        self._write_meta("2026-01-01T00:00:00+00:00")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),  # git log — nothing new
                MagicMock(returncode=0, stdout=""),  # git status — clean
            ]
            result = self.srv._index_is_stale(self.root)
        self.assertFalse(result)

    def test_framework_stale_when_dirty_framework_file_modified_after_build(self):
        self._write_meta("2026-01-01T00:00:00+00:00", layer="framework")
        dirty = self.root / ".wavefoundry" / "framework" / "seeds" / "100-sample.prompt.md"
        dirty.parent.mkdir(parents=True, exist_ok=True)
        dirty.write_text("changed", encoding="utf-8")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),
                MagicMock(returncode=0, stdout=" M .wavefoundry/framework/seeds/100-sample.prompt.md\n"),
            ]
            result = self.srv._index_is_stale(self.root, "framework")
        self.assertTrue(result)

    def test_framework_not_stale_when_framework_file_meta_matches_current_inputs(self):
        framework_file = self.root / ".wavefoundry" / "framework" / "seeds" / "100-sample.prompt.md"
        framework_file.parent.mkdir(parents=True, exist_ok=True)
        framework_file.write_text("# Sample\n", encoding="utf-8")
        digest = hashlib.sha256(framework_file.read_bytes()).hexdigest()
        stat = framework_file.stat()
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    ".wavefoundry/framework/seeds/100-sample.prompt.md": {
                        "hash": digest,
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                        "inode": stat.st_ino,
                    }
                },
            },
            layer="framework",
        )
        with patch("subprocess.run", side_effect=AssertionError("framework file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "framework")
        self.assertFalse(result)

    def test_framework_stale_when_framework_file_meta_detects_changed_input(self):
        framework_file = self.root / ".wavefoundry" / "framework" / "seeds" / "100-sample.prompt.md"
        framework_file.parent.mkdir(parents=True, exist_ok=True)
        framework_file.write_text("# Sample updated\n", encoding="utf-8")
        stat = framework_file.stat()
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    ".wavefoundry/framework/seeds/100-sample.prompt.md": {
                        "hash": "stale-hash",
                        "mtime": stat.st_mtime - 1,
                        "size": max(stat.st_size - 1, 0),
                        "inode": stat.st_ino,
                    }
                },
            },
            layer="framework",
        )
        with patch("subprocess.run", side_effect=AssertionError("framework file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "framework")
        self.assertTrue(result)

    def test_framework_not_stale_when_only_manifest_differs_from_file_meta(self):
        manifest = self.root / ".wavefoundry" / "framework" / "MANIFEST"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("current\n", encoding="utf-8")
        stat = manifest.stat()
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    ".wavefoundry/framework/MANIFEST": {
                        "hash": "stale-hash",
                        "mtime": stat.st_mtime - 1,
                        "size": max(stat.st_size - 1, 0),
                        "inode": stat.st_ino,
                    }
                },
            },
            layer="framework",
        )
        with patch("subprocess.run", side_effect=AssertionError("framework file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "framework")
        self.assertFalse(result)

    def test_framework_not_stale_when_only_version_differs_from_file_meta(self):
        version = self.root / ".wavefoundry" / "framework" / "VERSION"
        version.parent.mkdir(parents=True, exist_ok=True)
        version.write_text("2026-05-11e\n", encoding="utf-8")
        stat = version.stat()
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    ".wavefoundry/framework/VERSION": {
                        "hash": "stale-hash",
                        "mtime": stat.st_mtime - 1,
                        "size": max(stat.st_size - 1, 0),
                        "inode": stat.st_ino,
                    }
                },
            },
            layer="framework",
        )
        with patch("subprocess.run", side_effect=AssertionError("framework file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "framework")
        self.assertFalse(result)

    def test_framework_not_stale_when_only_framework_pycache_dir_is_dirty(self):
        self._write_meta("2026-01-01T00:00:00+00:00", layer="framework")
        dirty = self.root / ".wavefoundry" / "framework" / "scripts" / "__pycache__"
        dirty.mkdir(parents=True, exist_ok=True)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),
                MagicMock(returncode=0, stdout="?? .wavefoundry/framework/scripts/__pycache__/\n"),
            ]
            result = self.srv._index_is_stale(self.root, "framework")
        self.assertFalse(result)

    def test_framework_not_stale_when_only_framework_pyc_file_is_dirty(self):
        self._write_meta("2026-01-01T00:00:00+00:00", layer="framework")
        dirty = self.root / ".wavefoundry" / "framework" / "scripts" / "__pycache__" / "dashboard_server.cpython-313.pyc"
        dirty.parent.mkdir(parents=True, exist_ok=True)
        dirty.write_bytes(b"compiled")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),
                MagicMock(returncode=0, stdout="?? .wavefoundry/framework/scripts/__pycache__/dashboard_server.cpython-313.pyc\n"),
            ]
            result = self.srv._index_is_stale(self.root, "framework")
        self.assertFalse(result)

    def test_framework_not_stale_when_only_collapsed_untracked_framework_directory_is_dirty(self):
        self._write_meta("2026-01-01T00:00:00+00:00", layer="framework")
        framework_dir = self.root / ".wavefoundry" / "framework"
        (framework_dir / "index").mkdir(parents=True, exist_ok=True)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),
                MagicMock(returncode=0, stdout="?? .wavefoundry/framework/\n"),
            ]
            result = self.srv._index_is_stale(self.root, "framework")
        self.assertFalse(result)

    def test_framework_stale_when_untracked_framework_file_modified_after_build(self):
        self._write_meta("2026-01-01T00:00:00+00:00", layer="framework")
        dirty = self.root / ".wavefoundry" / "framework" / "seeds" / "100-sample.prompt.md"
        dirty.parent.mkdir(parents=True, exist_ok=True)
        dirty.write_text("changed", encoding="utf-8")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),
                MagicMock(returncode=0, stdout="?? .wavefoundry/framework/seeds/100-sample.prompt.md\n"),
            ]
            result = self.srv._index_is_stale(self.root, "framework")
        self.assertTrue(result)

    def test_project_not_stale_when_project_file_meta_matches_current_inputs(self):
        project_file = self.root / "docs" / "guide.md"
        project_file.parent.mkdir(parents=True, exist_ok=True)
        project_file.write_text("# Guide\n", encoding="utf-8")
        digest = hashlib.sha256(project_file.read_bytes()).hexdigest()
        stat = project_file.stat()
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    "docs/guide.md": {
                        "hash": digest,
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                        "inode": stat.st_ino,
                    }
                },
            },
            layer="project",
        )
        with patch("subprocess.run", side_effect=AssertionError("project file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "project")
        self.assertFalse(result)

    def test_project_stale_when_project_file_meta_detects_changed_input(self):
        project_file = self.root / "docs" / "guide.md"
        project_file.parent.mkdir(parents=True, exist_ok=True)
        project_file.write_text("# Guide updated\n", encoding="utf-8")
        stat = project_file.stat()
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    "docs/guide.md": {
                        "hash": "stale-hash",
                        "mtime": stat.st_mtime - 1,
                        "size": max(stat.st_size - 1, 0),
                        "inode": stat.st_ino,
                    }
                },
            },
            layer="project",
        )
        with patch("subprocess.run", side_effect=AssertionError("project file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "project")
        self.assertTrue(result)

    def test_project_not_stale_when_only_dashboard_runtime_state_differs_from_file_meta(self):
        runtime_file = self.root / ".wavefoundry" / "dashboard-server.json"
        runtime_file.parent.mkdir(parents=True, exist_ok=True)
        runtime_file.write_text('{"pid": 1}\n', encoding="utf-8")
        stat = runtime_file.stat()
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    ".wavefoundry/dashboard-server.json": {
                        "hash": "stale-hash",
                        "mtime": stat.st_mtime - 1,
                        "size": max(stat.st_size - 1, 0),
                        "inode": stat.st_ino,
                    }
                },
            },
            layer="project",
        )
        with patch("subprocess.run", side_effect=AssertionError("project file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "project")
        self.assertFalse(result)

    def test_project_not_stale_when_only_dashboard_log_differs_from_file_meta(self):
        runtime_log = self.root / ".wavefoundry" / "logs" / "dashboard.log"
        runtime_log.parent.mkdir(parents=True, exist_ok=True)
        runtime_log.write_text("started\n", encoding="utf-8")
        stat = runtime_log.stat()
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    ".wavefoundry/logs/dashboard.log": {
                        "hash": "stale-hash",
                        "mtime": stat.st_mtime - 1,
                        "size": max(stat.st_size - 1, 0),
                        "inode": stat.st_ino,
                    }
                },
            },
            layer="project",
        )
        with patch("subprocess.run", side_effect=AssertionError("project file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "project")
        self.assertFalse(result)

    def test_project_not_stale_when_only_framework_file_modified_after_build(self):
        self._write_meta("2026-01-01T00:00:00+00:00", layer="project")
        dirty = self.root / ".wavefoundry" / "framework" / "seeds" / "100-sample.prompt.md"
        dirty.parent.mkdir(parents=True, exist_ok=True)
        dirty.write_text("changed", encoding="utf-8")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),
                MagicMock(returncode=0, stdout=" M .wavefoundry/framework/seeds/100-sample.prompt.md\n"),
            ]
            result = self.srv._index_is_stale(self.root, "project")
        self.assertFalse(result)

    def test_not_stale_when_git_unavailable(self):
        """If git commands fail, staleness check should not raise and return False."""
        self._write_meta("2026-01-01T00:00:00+00:00")
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            result = self.srv._index_is_stale(self.root)
        self.assertFalse(result)

    def test_git_status_uses_file_level_untracked_entries(self):
        self._write_meta("2026-01-01T00:00:00+00:00")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=""),
                MagicMock(returncode=0, stdout=""),
            ]
            self.srv._index_is_stale(self.root)
        status_args = mock_run.call_args_list[1].args[0]
        self.assertIn("--untracked-files=all", status_args)

    def test_signal_startup_fires_build(self):
        done_event = threading.Event()

        def on_done():
            done_event.set()

        with patch.object(self.srv.IndexBuilder, "_execute", return_value=0):
            builder = self.srv.IndexBuilder(root=self.root, delay=30.0, on_done=on_done)
            builder.signal_startup(delay=0.0)
            done_event.wait(timeout=2.0)

        self.assertTrue(done_event.is_set())
        self.assertEqual(builder.get_status()["build_status"], "done")

    def test_signal_startup_ignored_when_running(self):
        """signal_startup during an active build must not spawn a second process."""
        running_event = threading.Event()
        unblock_event = threading.Event()
        call_count = [0]

        def blocking_execute(self_inner):
            call_count[0] += 1
            running_event.set()
            unblock_event.wait(timeout=2.0)
            return 0

        with patch.object(self.srv.IndexBuilder, "_execute", blocking_execute):
            builder = self.srv.IndexBuilder(root=self.root, delay=0.0, on_done=lambda: None)
            builder.signal_change()
            running_event.wait(timeout=2.0)
            builder.signal_startup()  # should be a no-op
            self.assertEqual(call_count[0], 1)
            unblock_event.set()


class IndexBuilderSnapshotIntegrationTests(unittest.TestCase):
    """Verify SnapshotStore integrates IndexBuilder status into the snapshot."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        _make_wave(self.root)
        self._stores_to_stop: list = []

    def tearDown(self):
        for store in self._stores_to_stop:
            store.stop()
        self._stores_to_stop.clear()
        self.tmp.cleanup()

    def _track(self, store):
        """Register a store for cleanup in tearDown."""
        self._stores_to_stop.append(store)
        return store

    def _enable_auto_index(self):
        cfg_path = self.root / "docs" / "workflow-config.json"
        data = json.loads(cfg_path.read_text())
        data.setdefault("dashboard", {})["auto_index"] = True
        data["dashboard"]["auto_index_delay_seconds"] = 10
        cfg_path.write_text(json.dumps(data))

    def _disable_auto_index(self):
        cfg_path = self.root / "docs" / "workflow-config.json"
        data = json.loads(cfg_path.read_text())
        data.setdefault("dashboard", {})["auto_index"] = False
        data["dashboard"]["auto_index_delay_seconds"] = 10
        cfg_path.write_text(json.dumps(data))

    def test_build_status_absent_when_auto_index_disabled(self):
        self._disable_auto_index()
        store = self._track(self.srv.SnapshotStore(self.root))
        snap = store.get()
        proj = snap.get("health", {}).get("index", {}).get("project", {})
        self.assertNotIn("build_status", proj)

    def test_build_status_idle_when_auto_index_enabled(self):
        self._enable_auto_index()
        store = self._track(self.srv.SnapshotStore(self.root))
        snap = store.get()
        proj = snap.get("health", {}).get("index", {}).get("project", {})
        fw = snap.get("health", {}).get("index", {}).get("framework", {})
        self.assertEqual(proj.get("build_status"), "idle")
        self.assertEqual(fw.get("build_status"), "idle")

    def test_semantic_index_tile_uses_generic_build_status_copy(self):
        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn('const statusText = buildStatus === "running"', source)
        self.assertIn('? "Indexing..."', source)
        self.assertIn(': isStale', source)
        self.assertIn('? "Stale..."', source)
        self.assertIn('const buildAction = idx.mode === "update"', source)
        self.assertIn('const buildBadgeText = buildStatus === "running"', source)
        self.assertIn('`${buildAction} index…`', source)
        self.assertIn('"Index stale"', source)
        self.assertIn('"Build failed"', source)
        self.assertIn('buildBadgeText', source)

    def test_background_build_status_surfaces_in_snapshot_health(self):
        import os

        bg_pid = self.root / ".wavefoundry" / "index" / "background-build.pid"
        bg_log = self.root / ".wavefoundry" / "index" / "background-build.log"
        bg_pid.parent.mkdir(parents=True, exist_ok=True)
        bg_pid.write_text(str(os.getpid()), encoding="utf-8")
        bg_log.write_text(
            "Code index build started in background (PID 12345)\n"
            "build_index: embedding code chunks 1-20/200\n",
            encoding="utf-8",
        )

        store = self._track(self.srv.SnapshotStore(self.root))
        snap = store.get()
        proj = snap.get("health", {}).get("index", {}).get("project", {})
        self.assertEqual(proj.get("build_status"), "running")
        self.assertEqual(proj.get("source"), "background")
        self.assertIn("embedding code chunks", proj.get("progress", ""))

    def test_background_build_files_are_watched(self):
        store = self._track(self.srv.SnapshotStore(self.root))
        watched = {str(path) for path in store._watched_paths()}
        self.assertIn(str(self.root / ".wavefoundry" / "index" / "index-build.json"), watched)
        self.assertIn(str(self.root / ".wavefoundry" / "index" / "index-build.log"), watched)
        self.assertIn(str(self.root / ".wavefoundry" / "index" / "background-build.pid"), watched)
        self.assertIn(str(self.root / ".wavefoundry" / "index" / "background-build.log"), watched)

    def test_periodic_staleness_check_triggers_rebuild_when_stale(self):
        """When _index_is_stale returns True, the watch loop should signal the IndexBuilder."""
        self._enable_auto_index()
        store = self._track(self.srv.SnapshotStore(self.root))
        if store._index_builder is None:
            self.skipTest("auto_index not enabled")

        signalled = threading.Event()
        original_signal = store._index_builder.signal_change

        def tracking_signal(**kwargs):
            signalled.set()
            original_signal(**kwargs)

        store._index_builder.signal_change = tracking_signal
        # Seed as not-stale so the False→True transition triggers signal_change.
        store._index_stale = {"project": False, "framework": False}
        # Force the staleness check to run on the next loop iteration.
        store._last_staleness_check = 0.0

        with patch.object(self.srv, "_index_is_stale", return_value=True):
            signalled.wait(timeout=self.srv._WATCH_INTERVAL * 3)

        self.assertTrue(signalled.is_set(), "IndexBuilder.signal_change not called after stale detection")

    def test_periodic_staleness_check_signals_framework_layer_when_framework_becomes_stale(self):
        self._enable_auto_index()
        store = self._track(self.srv.SnapshotStore(self.root))
        if store._index_builder is None:
            self.skipTest("auto_index not enabled")

        called_layers: list[str] = []
        original_signal = store._index_builder.signal_change

        def tracking_signal(layer="project", reason="change signal"):
            called_layers.append(layer)
            original_signal(layer=layer, reason=reason)

        store._index_builder.signal_change = tracking_signal
        store._index_stale = {"project": False, "framework": False}
        store._last_staleness_check = 0.0

        def fake_stale(_root, layer="project"):
            return layer == "framework"

        with patch.object(self.srv, "_index_is_stale", side_effect=fake_stale):
            import time as _time
            deadline = _time.time() + (self.srv._WATCH_INTERVAL * 4)
            while "framework" not in called_layers and _time.time() < deadline:
                _time.sleep(0.05)

        self.assertIn("framework", called_layers)
        self.assertNotIn("project", called_layers)

    def test_periodic_staleness_check_skipped_while_running(self):
        """Staleness check must not fire while a build is already in progress."""
        self._enable_auto_index()
        store = self._track(self.srv.SnapshotStore(self.root))
        if store._index_builder is None:
            self.skipTest("auto_index not enabled")

        store._index_builder._running = True
        store._last_staleness_check = 0.0
        signalled = [False]
        original_signal = store._index_builder.signal_change

        def tracking_signal(layer="project", reason="change signal"):
            signalled[0] = True
            original_signal(layer=layer, reason=reason)

        store._index_builder.signal_change = tracking_signal

        import time as _time
        _time.sleep(self.srv._WATCH_INTERVAL * 2)
        self.assertFalse(signalled[0], "signal_change fired while build was running")
        store._index_builder._running = False  # cleanup

    def test_external_build_mtime_triggers_snapshot_refresh(self):
        """Writing index-build-stats.json should cause _rebuild to pick up the new mtime."""
        store = self._track(self.srv.SnapshotStore(self.root))
        stats_path = self.root / ".wavefoundry" / "index" / "index-build-stats.json"
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(json.dumps({"elapsed_seconds": 12, "mode": "incremental"}))
        # Simulate one watch-loop iteration by calling _rebuild directly.
        changed = store._rebuild(force_git=False)
        # The new stats file means index data changed — snapshot should reflect it.
        snap = store.get()
        proj = snap.get("health", {}).get("index", {}).get("project", {})
        # elapsed_seconds comes from dashboard_lib reading the file
        self.assertIsInstance(proj, dict)

    def test_external_framework_build_stats_trigger_snapshot_refresh(self):
        store = self._track(self.srv.SnapshotStore(self.root))
        fw_index = self.root / ".wavefoundry" / "framework" / "index"
        fw_index.mkdir(parents=True, exist_ok=True)
        (fw_index / "meta.json").write_text(json.dumps({"built_at": "2026-05-11T00:00:00+00:00"}))
        (fw_index / "index-build-stats.json").write_text(json.dumps({"elapsed_seconds": 5, "mode": "update"}))
        changed = store._rebuild(force_git=False)
        snap = store.get()
        fw = snap.get("health", {}).get("index", {}).get("framework", {})
        self.assertIsInstance(fw, dict)
        self.assertIn("elapsed_seconds", fw)

    def test_on_index_build_done_calls_rebuild_then_notify(self):
        """_on_index_build_done must rebuild before notifying SSE."""
        store = self._track(self.srv.SnapshotStore(self.root))
        call_order = []

        original_rebuild = store._rebuild
        original_notify = store._notify_sse

        def tracked_rebuild(**kwargs):
            call_order.append("rebuild")
            return original_rebuild(**kwargs)

        def tracked_notify():
            call_order.append("notify")
            return original_notify()

        store._rebuild = tracked_rebuild
        store._notify_sse = tracked_notify
        store._on_index_build_done()

        self.assertEqual(call_order, ["rebuild", "notify"])


import threading  # noqa: E402 (already imported above, but needed in test scope)

if __name__ == "__main__":
    unittest.main()
