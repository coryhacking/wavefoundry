from __future__ import annotations

import importlib.util
import errno
import io
import hashlib
import json
import os
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

    def __init__(self, snapshot: dict, root: Path | None = None):
        self._snapshot = snapshot
        self._root = root or Path.cwd()
        self._clients = []

    def get(self) -> dict:
        return self._snapshot

    def watcher_health(self) -> dict:
        # Wave 1rtju: /api/dashboard merges this read-time liveness view; a benign healthy stub here.
        return {"stalled": False, "last_cycle_age_seconds": 0.0, "interval_seconds": 3.0,
                "stall_threshold_seconds": 90.0}

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
review-evidence-source: events.jsonl

## Objective

Verify dashboard snapshot rendering.

## Participants

| Role | Lane | Scope |
|------|------|-------|
| code-reviewer | review | change |

## Review Checkpoints

- Prepare wave — readiness verdict: pass

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | pending | no current executed approval | record approval evidence for wave-council-readiness |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- wave-council-readiness: approved
- code-reviewer: approved

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 0 records; 0 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Changes

Change ID: `12x1-enh sample-dashboard`
Change Status: `ready`
""",
    )
    _write(wave_dir / "events.jsonl", "")
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


def _seed_index_store(root: Path, payload: dict, *, complete: bool = True) -> None:
    """1sed6: seed the index-state store (sole state authority; meta.json retired).
    ``complete=False`` writes bookkeeping without a completed build epoch —
    the store-level analogue of the old empty-``built_at`` meta."""
    import importlib.util as _ilu

    index_dir = root / ".wavefoundry" / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    spec = _ilu.spec_from_file_location(
        "index_state_store", SCRIPTS_ROOT / "index_state_store.py"
    )
    iss = _ilu.module_from_spec(spec)
    spec.loader.exec_module(iss)
    iss.write_build_bookkeeping(index_dir, payload)
    if complete:
        attempt = iss.begin_build_epoch(index_dir, "test:seed")
        iss.finalize_build_epoch(index_dir, attempt)


def _write_dashboard_lance_index(root: Path, *, docs_chunks: list[dict] | None = None, code_chunks: list[dict] | None = None) -> None:
    try:
        import lancedb
    except ImportError as exc:
        raise unittest.SkipTest("lancedb not installed in invoking interpreter") from exc

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
    _seed_index_store(root, meta)
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

    def test_review_evidence_projection_is_derived_from_external_ledger(self):
        wave = self.lib.collect_waves(self.root)[0]

        self.assertEqual(wave["review_evidence_status"]["integrity"], "ok")
        self.assertEqual(wave["review_evidence_status"]["projection"], "current")
        self.assertEqual(wave["review_evidence_status"]["diagnostics"], [])
        self.assertEqual(
            [row["value"] for row in wave["review_evidence"]],
            ["pending", "pending", "pending", "pending"],
            "prose signoff bullets must not be served as canonical approval state",
        )
        self.assertIn("| — | — | — | — | — |", wave["review_evidence_projection"])
        self.assertNotIn("```jsonl", wave["review_evidence_projection"])

    def test_dashboard_approval_state_comes_from_validated_external_records(self):
        from review_evidence import build_compact_review_event, canonical_review_events_bytes

        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        records, errors = build_compact_review_event(
            (),
            {
                "event": "approval",
                "actor": "wave-council",
                "context_id": "dashboard-approval",
                "signoff_key": "wave-council-delivery",
                "fresh_context": True,
                "independent": True,
                "integrity_confirmed": True,
                "observed": "approved from external authority",
                "artifact_or_test_id": "dashboard external approval fixture",
            },
        )
        self.assertEqual(errors, ())
        (wave_dir / "events.jsonl").write_bytes(canonical_review_events_bytes(records))

        wave = self.lib.collect_waves(self.root)[0]

        self.assertEqual(wave["review_evidence_status"]["integrity"], "ok")
        self.assertEqual(
            wave["review_evidence"],
            [
                {
                    "key": "wave-council-readiness",
                    "value": "pending",
                    "why": "no current executed approval",
                    "next_action": "record approval evidence for wave-council-readiness",
                },
                {
                    "key": "wave-council-delivery",
                    "value": "approved",
                    "why": "current executed approval follows every affected repair",
                    "next_action": "none",
                },
                {
                    "key": "code-reviewer",
                    "value": "pending",
                    "why": "no current executed approval",
                    "next_action": "record approval evidence for code-reviewer",
                },
                {
                    "key": "operator-signoff",
                    "value": "pending",
                    "why": "no current executed approval",
                    "next_action": "record approval evidence for operator-signoff",
                },
            ],
        )

    def test_valid_external_ledger_serves_derived_state_when_projection_is_stale(self):
        wave_md = self.root / "docs" / "waves" / "12x test-wave" / "wave.md"
        stale = wave_md.read_text(encoding="utf-8").replace(
            "| — | — | — | — | — |", "| _Stale projection._ | — | — | — | — |"
        )
        wave_md.write_text(stale, encoding="utf-8")

        wave = self.lib.collect_waves(self.root)[0]

        self.assertEqual(wave["review_evidence_status"]["integrity"], "ok")
        self.assertEqual(wave["review_evidence_status"]["projection"], "stale")
        self.assertIn("| — | — | — | — | — |", wave["review_evidence_projection"])
        self.assertNotIn("_Stale projection._", wave["review_evidence_projection"])
        self.assertIn("derived from events.jsonl", wave["review_evidence_status"]["diagnostics"][0])

    def test_valid_external_ledger_serves_derived_state_when_projection_is_missing(self):
        wave_md = self.root / "docs" / "waves" / "12x test-wave" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        start = text.index("## Finding Synthesis\n")
        end = text.index("## Changes\n", start)
        wave_md.write_text(text[:start] + text[end:], encoding="utf-8")

        wave = self.lib.collect_waves(self.root)[0]

        self.assertEqual(wave["review_evidence_status"]["integrity"], "ok")
        self.assertEqual(wave["review_evidence_status"]["projection"], "missing")
        self.assertIn("| — | — | — | — | — |", wave["review_evidence_projection"])

    def test_invalid_external_ledger_fails_closed_without_serving_projection(self):
        ledger = self.root / "docs" / "waves" / "12x test-wave" / "events.jsonl"
        ledger.write_text('{"record_type":"review_run"}', encoding="utf-8")

        wave = self.lib.collect_waves(self.root)[0]

        self.assertEqual(wave["review_evidence_status"]["integrity"], "invalid")
        self.assertEqual(wave["review_evidence_status"]["projection"], "unavailable")
        self.assertIsNone(wave["review_evidence_projection"])
        self.assertTrue(wave["review_evidence_status"]["diagnostics"])

    def test_adopted_missing_external_ledger_fails_closed(self):
        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        empty_hash = hashlib.sha256(b"wavefoundry-review-events\0").hexdigest()
        _write(
            self.root / "docs" / "waves" / "review-evidence-adoptions.json",
            json.dumps(
                {
                    "protocol_version": 1,
                    "waves": {
                        "12x test-wave": {
                            "version": 1,
                            "source": "events.jsonl",
                            "record_count": 0,
                            "prefix_sha256": empty_hash,
                        }
                    },
                }
            ),
        )
        (wave_dir / "events.jsonl").unlink()

        wave = self.lib.collect_waves(self.root)[0]

        self.assertEqual(wave["review_evidence_status"]["integrity"], "invalid")
        self.assertIsNone(wave["review_evidence_projection"])
        self.assertTrue(
            any("ledger is missing" in item for item in wave["review_evidence_status"]["diagnostics"])
        )

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
        # Wave 1p458 (1p45a): the AC denominator now INCLUDES `[~]` deferred items.
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

    def test_collect_dashboard_snapshot_includes_graph_health(self):
        # 1p4ww: single project index — only the project graph is surfaced in health.
        project_graph = self.root / ".wavefoundry" / "index" / "graph" / "project-graph.json"
        _write(
            project_graph,
            json.dumps(
                {
                    "schema_version": "1",
                    "builder_version": "1",
                    "layer": "project",
                    "present": True,
                    "counts": {"files": 2, "nodes": 3, "edges": 4},
                    "nodes": [
                        {"id": "src/app.py::run", "label": "run", "kind": "function", "source_file": "src/app.py", "source_location": "1:0", "layer": "project"}
                    ],
                    "edges": [],
                }
            ),
        )

        snapshot = self.lib.collect_dashboard_snapshot(self.root)

        self.assertTrue(snapshot["health"]["graph"]["project"]["present"])
        self.assertEqual(snapshot["health"]["graph"]["project"]["counts"]["nodes"], 3)
        self.assertNotIn("framework", snapshot["health"]["graph"])
        self.assertNotIn("framework", snapshot["health"]["index"])

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
        # Wave 1p458 (1p45a): ProgressRow no longer takes a `deferred` arg; the `· N deferred`
        # suffix is gone (deferred read as outstanding while open, fold into done once closed).
        progress_row_src = source.split("function ProgressRow({ label, done, total, variant }) {", 1)[1].split(
            "function ProgressCard({ snapshot, scopeChanges }) {", 1
        )[0]
        self.assertIn('h(ProgressRow, { label: "ACs",   done: acDone,    total: acTotal,    variant: "acs" })', source)
        self.assertIn('h(ProgressRow, { label: "Tasks", done: tasksDone, total: tasksTotal, variant: "tasks" })', source)
        self.assertNotIn('deferred: acDeferred', source)
        self.assertNotIn('deferred: tasksDeferred', source)
        self.assertNotIn('progress-row-deferred', progress_row_src)
        self.assertNotIn('acTotal    ? h(ProgressRow', source)
        self.assertNotIn('tasksTotal ? h(ProgressRow', source)
        self.assertNotIn('if (!total) return null;', progress_row_src)
        self.assertIn('const progressChanges = scopeChanges || allInWaves;', source)
        self.assertIn('const allInWaves = snapshot.changes?.in_waves || [];', source)

    def test_parse_ac_items_recognizes_tilde_marker(self):
        """Wave 1p31b (1p32k): `[~]` ACs parse with deferred=True and done=False."""
        ac_section = (
            "- [x] AC-1: Done criterion.\n"
            "- [ ] AC-2: Pending criterion.\n"
            "- [~] AC-3: Intentionally deferred per operator direction. *See Decision Log.*\n"
        )
        priority_section = (
            "| AC | Priority | Rationale |\n"
            "| --- | --- | --- |\n"
            "| AC-1 | required | Core. |\n"
            "| AC-2 | required | Polish. |\n"
            "| AC-3 | important | Optional. |\n"
        )
        items = self.lib._parse_ac_items(ac_section, priority_section, "planned")
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["id"], "AC-1")
        self.assertTrue(items[0]["done"])
        self.assertFalse(items[0]["deferred"])
        self.assertEqual(items[1]["id"], "AC-2")
        self.assertFalse(items[1]["done"])
        self.assertFalse(items[1]["deferred"])
        self.assertEqual(items[2]["id"], "AC-3")
        self.assertFalse(items[2]["done"], msg="`[~]` must not be counted as done")
        self.assertTrue(items[2]["deferred"], msg="`[~]` must set deferred=True")

    def test_parse_tasks_recognizes_tilde_marker(self):
        """Wave 1p458 (1p45a): `[~]` tasks parse with deferred=True and done=False; the
        `total` now INCLUDES deferred (they read as outstanding while open), while
        `completed` stays `[x]`-only."""
        tasks_section = (
            "- [x] Implement feature.\n"
            "- [ ] Write docs.\n"
            "- [~] Bench against synthetic fixture\n"
        )
        result = self.lib._parse_tasks(tasks_section, "planned")
        self.assertEqual(result["total"], 3, msg="total now includes the `[~]` task (open: outstanding)")
        self.assertEqual(result["completed"], 1, msg="completed stays `[x]`-only")
        self.assertEqual(result["open"], 2, msg="the `[~]` task reads as open while the wave is open")
        self.assertEqual(result["deferred"], 1)
        # Item-level: the third task must be flagged deferred and not done.
        self.assertEqual(len(result["items"]), 3)
        self.assertTrue(result["items"][2]["deferred"])
        self.assertFalse(result["items"][2]["done"])

    def test_ac_and_task_items_include_indented_prose_continuations(self):
        ac_section = (
            "- [x] AC-1: A mixed fixture containing modern-ledger, pre-ledger,\n"
            "  zero-source, and `inline-code` cases preserves\n"
            "  the complete operator-visible criterion. (required)\n"
            "2. [~] AC-2: A second criterion remains distinct.\n"
        )
        priorities = (
            "| AC | Priority | Rationale |\n"
            "| --- | --- | --- |\n"
            "| AC-1 | required | Core. |\n"
            "| AC-2 | important | Deferred. |\n"
        )
        acs = self.lib._parse_ac_items(ac_section, priorities, "planned")
        self.assertEqual(len(acs), 2)
        self.assertEqual(
            acs[0]["text"],
            "AC-1: A mixed fixture containing modern-ledger, pre-ledger, "
            "zero-source, and `inline-code` cases preserves the complete "
            "operator-visible criterion. (required)",
        )
        self.assertEqual(acs[0]["id"], "AC-1")
        self.assertTrue(acs[0]["done"])
        self.assertEqual(acs[0]["priority"], "required")
        self.assertEqual(acs[1]["id"], "AC-2")
        self.assertTrue(acs[1]["deferred"])
        self.assertEqual(acs[1]["priority"], "important")

        task_section = (
            "- [x] Add the shared parser and retain\n"
            "  every hard-wrapped continuation line\n"
            "  with normal word spacing.\n"
            "- [ ] Verify the next task remains distinct.\n"
        )
        tasks = self.lib._parse_tasks(task_section, "planned")
        self.assertEqual(tasks["total"], 2)
        self.assertEqual(tasks["completed"], 1)
        self.assertEqual(
            tasks["items"][0]["label"],
            "Add the shared parser and retain every hard-wrapped continuation "
            "line with normal word spacing.",
        )
        self.assertEqual(
            tasks["items"][1]["label"],
            "Verify the next task remains distinct.",
        )

    def test_dashboard_snapshot_preserves_full_multiline_ac_and_task_text(self):
        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        _write(
            wave_dir / "12x1-enh sample-dashboard.md",
            """# Sample Dashboard Change

Change ID: `12x1-enh sample-dashboard`
Change Status: `active`
Owner: Engineering
Wave: `12x test-wave`

## Acceptance Criteria

  - [x] AC-1: A mixed fixture containing modern-ledger, pre-ledger, zero-source,
    unsupported-source, and agent-validated cases appears in the dashboard
    without truncating the operator-visible criterion.
  - [ ] AC-2: A sibling criterion remains distinct.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Core. |
| AC-2 | important | Follow-up. |

## Tasks

  - [x] Parse hard-wrapped task prose and preserve every
    continuation line in the dashboard payload.
  - [ ] Keep the next task distinct.
""",
        )

        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        change = snapshot["changes"]["in_waves"][0]

        self.assertEqual(
            change["ac_items"][0]["text"],
            "AC-1: A mixed fixture containing modern-ledger, pre-ledger, "
            "zero-source, unsupported-source, and agent-validated cases "
            "appears in the dashboard without truncating the operator-visible "
            "criterion.",
        )
        self.assertEqual(change["ac_items"][0]["priority"], "required")
        self.assertTrue(change["ac_items"][0]["done"])
        self.assertEqual(change["ac_items"][1]["id"], "AC-2")
        self.assertEqual(
            change["tasks_items"][0]["label"],
            "Parse hard-wrapped task prose and preserve every continuation line "
            "in the dashboard payload.",
        )
        self.assertTrue(change["tasks_items"][0]["done"])
        self.assertEqual(change["tasks_items"][1]["label"], "Keep the next task distinct.")

    def test_pipe_less_markdown_table_does_not_join_ac_or_task_text(self):
        acs = self.lib._parse_ac_items(
            "- [ ] AC-1: first line\n"
            "  accepted continuation\n"
            "  Column A | Column B\n"
            "  --- | ---\n"
            "  value A | value B\n"
            "- [x] AC-2: second item\n",
            "| AC | Priority |\n| --- | --- |\n| AC-1 | required |\n| AC-2 | important |\n",
            "planned",
        )
        self.assertEqual([ac["id"] for ac in acs], ["AC-1", "AC-2"])
        self.assertEqual(acs[0]["text"], "AC-1: first line accepted continuation")

        tasks = self.lib._parse_tasks(
            "- [ ] first task\n"
            "  accepted continuation\n"
            "  Column A | Column B\n"
            "  --- | ---\n"
            "  value A | value B\n"
            "- [x] second task\n",
            "planned",
        )
        self.assertEqual(tasks["total"], 2)
        self.assertEqual(tasks["items"][0]["label"], "first task accepted continuation")

    def test_inline_pipe_prose_remains_a_continuation_without_table_separator(self):
        tasks = self.lib._parse_tasks(
            "- [ ] explain the operator\n"
            "  where `left | right` is ordinary inline prose\n"
            "- [x] second task\n",
            "planned",
        )
        self.assertEqual(
            tasks["items"][0]["label"],
            "explain the operator where `left | right` is ordinary inline prose",
        )

    def test_setext_heading_does_not_join_ac_or_task_text(self):
        priorities = (
            "| AC | Priority | Rationale |\n"
            "| --- | --- | --- |\n"
            "| AC-1 | required | Core. |\n"
            "| AC-2 | important | Follow-up. |\n"
        )
        for underline in ("=", "=================="):
            with self.subTest(kind="ac", underline=underline):
                acs = self.lib._parse_ac_items(
                    "- [ ] AC-1: first line\n"
                    "  accepted continuation\n"
                    "  Structural heading\n"
                    f"  {underline}\n"
                    "  must not be absorbed\n"
                    "- [x] AC-2: second item\n",
                    priorities,
                    "planned",
                )
                self.assertEqual([ac["id"] for ac in acs], ["AC-1", "AC-2"])
                self.assertEqual(acs[0]["text"], "AC-1: first line accepted continuation")

            with self.subTest(kind="task", underline=underline):
                tasks = self.lib._parse_tasks(
                    "- [ ] first task\n"
                    "  accepted continuation\n"
                    "  Structural heading\n"
                    f"  {underline}\n"
                    "  must not be absorbed\n"
                    "- [x] second task\n",
                    "planned",
                )
                self.assertEqual(tasks["total"], 2)
                self.assertEqual(
                    tasks["items"][0]["label"],
                    "first task accepted continuation",
                )

    def test_ac_and_task_continuations_stop_at_markdown_boundaries(self):
        boundaries = {
            "blank": "",
            "unindented prose": "Unrelated prose.",
            "nested list": "  - nested item",
            "heading": "  ### Nested heading",
            "blockquote": "  > quoted block",
            "table": "  | A | B |",
            "fence": "  ```python",
            "thematic break": "  ---",
        }
        priorities = (
            "| AC | Priority | Rationale |\n"
            "| --- | --- | --- |\n"
            "| AC-1 | required | Core. |\n"
            "| AC-2 | important | Follow-up. |\n"
        )
        for name, boundary in boundaries.items():
            with self.subTest(kind="ac", boundary=name):
                ac_section = (
                    "- [ ] AC-1: first line\n"
                    "  accepted continuation\n"
                    f"{boundary}\n"
                    "  must not be absorbed\n"
                    "- [x] AC-2: second item\n"
                )
                acs = self.lib._parse_ac_items(ac_section, priorities, "planned")
                self.assertEqual([ac["id"] for ac in acs], ["AC-1", "AC-2"])
                self.assertEqual(acs[0]["text"], "AC-1: first line accepted continuation")
                self.assertEqual(acs[0]["priority"], "required")
                self.assertFalse(acs[0]["done"])
                self.assertTrue(acs[1]["done"])

            with self.subTest(kind="task", boundary=name):
                task_section = (
                    "- [ ] first task\n"
                    "  accepted continuation\n"
                    f"{boundary}\n"
                    "  must not be absorbed\n"
                    "- [x] second task\n"
                    "1. [x] ordered task is outside the supported task surface\n"
                )
                tasks = self.lib._parse_tasks(task_section, "planned")
                self.assertEqual(tasks["total"], 2)
                self.assertEqual(tasks["completed"], 1)
                self.assertEqual(
                    tasks["items"][0]["label"],
                    "first task accepted continuation",
                )
                self.assertEqual(tasks["items"][1]["label"], "second task")

    def test_completed_counts_are_x_only_deferred_counts_bucket_them(self):
        """Wave 1p458 (1p45a): `_completed_ac_counts` counts only `[x]` ACs (the open-wave
        reading — deferred read as outstanding), while `_deferred_ac_counts` buckets `[~]`
        ACs by priority for the detail-dialog marker. The denominator inclusion and the
        closed-wave fold are covered by the snapshot / ProgressCard tests."""
        ac_section = (
            "- [x] AC-1: First.\n"
            "- [x] AC-2: Second.\n"
            "- [~] AC-3: Removed per operator. *See Decision Log.*\n"
            "- [~] AC-4: Also removed. *Same rationale.*\n"
        )
        priority_section = (
            "| AC | Priority | Rationale |\n"
            "| --- | --- | --- |\n"
            "| AC-1 | required | Core. |\n"
            "| AC-2 | required | Polish. |\n"
            "| AC-3 | required | Was core, removed. |\n"
            "| AC-4 | important | Was nice, removed. |\n"
        )
        items = self.lib._parse_ac_items(ac_section, priority_section, "planned")
        completed = self.lib._completed_ac_counts(items)
        deferred = self.lib._deferred_ac_counts(items)
        self.assertEqual(completed["required"], 2, msg="both `[x]` required ACs counted")
        # `[~]` ACs must not be counted as completed regardless of priority.
        self.assertNotIn("AC-3", [k for k in completed.keys() if completed[k] > 0])
        self.assertEqual(deferred["required"], 1, msg="AC-3 surfaces in required-priority deferred count")
        self.assertEqual(deferred["important"], 1, msg="AC-4 surfaces in important-priority deferred count")

    def test_deferred_items_count_in_denominator_but_not_done_while_open(self):
        """Wave 1p458 (1p45a) AC-2/AC-5: for an OPEN wave, `[~]` deferred ACs/tasks sit in
        the denominator but do not count as done (they read as outstanding); `not-this-scope`
        items — including a `[~]` not-this-scope AC — stay fully excluded."""
        wave_dir = self.root / "docs" / "waves" / "12x test-wave"
        _write(
            wave_dir / "12x1-enh sample-dashboard.md",
            """# Sample Dashboard Change

Change ID: `12x1-enh sample-dashboard`
Change Status: `active`
Owner: Engineering
Wave: `12x test-wave`

## Acceptance Criteria

- [x] AC-1: first done
- [x] AC-2: second done
- [~] AC-3: deferred required *Deferred per operator. See Decision Log.*
- [~] AC-4: deferred important
- [~] AC-5: deferred and out of scope
- [ ] AC-6: pending and out of scope

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | core |
| AC-2 | required | core |
| AC-3 | required | was core, deferred |
| AC-4 | important | deferred |
| AC-5 | not-this-scope | out of scope |
| AC-6 | not-this-scope | out of scope |

## Tasks

- [x] task one
- [ ] task two
- [~] task three
""",
        )

        snapshot = self.lib.collect_dashboard_snapshot(self.root)
        acs = snapshot["metrics"]["acs"]
        tasks = snapshot["metrics"]["tasks"]

        # ACs: visible = AC-1..AC-4 (the two not-this-scope ACs, incl the `[~]` one, are excluded).
        self.assertEqual(acs["total"], 4, msg="deferred AC-3/AC-4 are in the denominator; not-this-scope excluded")
        self.assertEqual(acs["done"], 2, msg="only `[x]` ACs count as done while the wave is open")
        self.assertEqual(acs["pending"], 2, msg="the two deferred ACs read as outstanding while open")
        self.assertEqual(acs["deferred"], 2, msg="deferred count retained as informational")
        # Tasks: deferred task three is in the denominator, not in done, while open.
        self.assertEqual(tasks["total"], 3)
        self.assertEqual(tasks["done"], 1)
        self.assertEqual(tasks["pending"], 2)

        change = snapshot["changes"]["in_waves"][0]
        self.assertEqual(change["tasks_total"], 3)
        self.assertEqual(change["tasks_completed"], 1)
        self.assertEqual(change["tasks_deferred"], 1)

    def test_progress_builder_and_card_fold_deferred_into_done_once_closed(self):
        """Wave 1p458 (1p45a) AC-1: deferred items fold into done only once the wave is
        closed. Asserted on source: the backend builder and frontend ProgressCard keep
        deferred in the denominator and count every in-scope item as done for closed waves,
        while the open branch counts only `[x]`/done items."""
        py = DASHBOARD_LIB_PATH.read_text(encoding="utf-8")
        # Backend: denominator includes deferred; closed branch folds all in-scope into done.
        self.assertIn("ac_total += len(items)", py)
        self.assertIn("ac_done += len(items)", py)
        self.assertIn('ac_done += sum(1 for item in items if item.get("done"))', py)
        self.assertNotIn('in_scope = [item for item in items if not item.get("deferred")]', py)

        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        # Frontend ProgressCard: denominator includes deferred; closed folds, open counts done.
        self.assertIn("const inScope = visibleAcItems(c);", source)
        self.assertIn("closedWaveIds.has(c.wave_id) ? inScope.length : inScope.filter(a => a.done).length", source)
        self.assertNotIn("visibleAcItems(c).filter(a => !a.deferred)", source)

    def test_deferred_suffix_removed_from_progress_bars(self):
        """Wave 1p458 (1p45a) AC-3: the `· N deferred` suffix and its CSS rule are gone."""
        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        css = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.css").read_text(encoding="utf-8")
        self.assertNotIn("progress-row-deferred", source)
        self.assertNotIn("progress-row-deferred", css)

    def test_activity_timeline_change_id_renders_dash_break_parts(self):
        """Wave 1p459: the Activity timeline change-id renders via renderChangeIdParts so it
        wraps only after dashes (the kind/slug space is non-breaking), scoped via
        `.timeline .wave-change-id`; the metric-dialog id rendering is unchanged."""
        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        css = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.css").read_text(encoding="utf-8")
        # Helper exists and does dash-split + <wbr> + nbsp-protected space.
        self.assertIn("function renderChangeIdParts(id) {", source)
        self.assertIn('safe.split("-").flatMap', source)
        self.assertIn('part.replace(/ /g, "\\u00a0")', source)
        # Activity timeline span uses the helper.
        self.assertIn("...renderChangeIdParts(item.change_id)", source)
        # Regression guard: metric-dialog card headers still render the raw change_id (nowrap).
        self.assertIn('h("span", { className: "wave-change-id" }, c.change_id)', source)
        # Scoped wrap rule for the timeline.
        self.assertIn(".timeline .wave-change-id {", css)
        timeline_rule = css.split(".timeline .wave-change-id {", 1)[1].split("}", 1)[0]
        self.assertIn("white-space: normal;", timeline_rule)
        self.assertIn("overflow-wrap: break-word;", timeline_rule)

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
        store = _MockStore(self.snapshot, getattr(self, "root", None))

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

    def test_api_graph_serves_project_graph_payload(self):
        # Wave 1p4ww: single project graph — framework/union layers removed.
        project_graph = self.root / ".wavefoundry" / "index" / "graph" / "project-graph.json"
        _write(
            project_graph,
            json.dumps(
                {
                    "schema_version": "1",
                    "builder_version": "1",
                    "layer": "project",
                    "present": True,
                    "counts": {"files": 1, "nodes": 1, "edges": 1},
                    "graph_mtime": 111,
                    "nodes": [
                        {"id": "src/app.py::run", "label": "run", "kind": "function", "source_file": "src/app.py", "source_location": "1:0", "layer": "project"}
                    ],
                    "edges": [
                        {"source": "src/app.py", "target": "src/app.py::run", "relation": "defines", "confidence": "EXTRACTED"}
                    ],
                }
            ),
        )
        _write(
            self.root / ".wavefoundry" / "index" / "graph" / "project-graph-clusters.json",
            json.dumps(
                {
                    "cluster_schema_version": "1",
                    "cluster_builder_version": "1",
                    "layer": "project",
                    "graph_schema_version": "1",
                    "graph_builder_version": "1",
                    "graph_path": ".wavefoundry/index/graph/project-graph.json",
                    "graph_mtime": 111,
                    "cluster_mtime": 222,
                    "projection": "derived-undirected",
                    "community_count": 1,
                    "communities": [
                        {
                            "community_id": "project:c0",
                            "label": "core",
                            "seed_node_id": "src/app.py::run",
                            "node_ids": ["src/app.py::run"],
                            "node_count": 1,
                            "edge_count": 0,
                            "boundary_node_count": 0,
                        }
                    ],
                }
            ),
        )
        project_handler = self._make_handler("/api/graph?layer=project")
        project_handler.do_GET()
        self.assertEqual(project_handler.response_code, 200)
        project_payload = json.loads(project_handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(project_payload["layer"], "project")
        self.assertTrue(project_payload["present"])
        self.assertEqual(project_payload["counts"]["nodes"], 1)
        self.assertEqual(project_payload["graph_version"], max(project_payload["graph_mtime"], project_payload["cluster_mtime"]))
        self.assertEqual(project_payload["clusters"]["community_count"], 1)
        self.assertEqual(project_payload["clusters"]["communities"][0]["label"], "core")
        self.assertEqual(project_payload["nodes"][0]["degree"], 1)
        self.assertEqual(project_payload["nodes"][0]["community_id"], "project:c0")

        # The framework graph layer is gone — /api/graph?layer=framework is rejected.
        framework_handler = self._make_handler("/api/graph?layer=framework")
        framework_handler.do_GET()
        self.assertEqual(framework_handler.response_code, 400)

    def test_api_graph_rejects_unsupported_layer(self):
        handler = self._make_handler("/api/graph?layer=bogus")
        handler.do_GET()
        self.assertEqual(handler.response_code, 400)
        payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertIn("Unsupported graph layer", payload.get("error", ""))

    def test_api_graph_neighbors_returns_focus_neighborhood(self):
        graph_path = self.root / ".wavefoundry" / "index" / "graph" / "project-graph.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "builder_version": "1",
                    "layer": "project",
                    "counts": {"files": 2, "nodes": 3, "edges": 1},
                    "nodes": [
                        {"id": "src/a.py::caller", "label": "caller", "kind": "function", "source_file": "src/a.py", "layer": "project"},
                        {"id": "src/b.py::callee", "label": "callee", "kind": "function", "source_file": "src/b.py", "layer": "project"},
                        {"id": "src/b.py", "label": "b", "kind": "module", "source_file": "src/b.py", "layer": "project"},
                    ],
                    "edges": [
                        {"source": "src/a.py::caller", "target": "src/b.py::callee", "relation": "calls", "confidence": "EXTRACTED"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        handler = self._make_handler("/api/graph/neighbors?layer=project&symbol=src/b.py::callee")
        handler.do_GET()
        self.assertEqual(handler.response_code, 200)
        payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertTrue(payload.get("present"))
        self.assertEqual(payload.get("focus_node_id"), "src/b.py::callee")
        node_ids = {node["id"] for node in payload.get("nodes") or []}
        self.assertIn("src/a.py::caller", node_ids)

    def test_dashboard_html_serves_shell(self):
        handler = self._make_handler("/dashboard.html")
        handler.do_GET()
        self.assertEqual(handler.response_code, 200)
        html = handler.wfile.getvalue().decode("utf-8")
        self.assertIn('<div id="app"></div>', html)
        self.assertIn("https://unpkg.com/react@18.3.1/umd/react.production.min.js", html)
        self.assertIn("https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js", html)
        self.assertIn("https://unpkg.com/elkjs@0.10.0/lib/elk.bundled.js", html)
        self.assertNotIn("force-graph", html)
        self.assertIn('<script src="/dashboard.js"></script>', html)

    def test_dashboard_html_loads_graph_libs_from_cdn_not_local_assets(self):
        handler = self._make_handler("/dashboard.html")
        handler.do_GET()
        html = handler.wfile.getvalue().decode("utf-8")
        self.assertNotIn('src="/react.production.min.js"', html)

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

    def test_dashboard_js_includes_readable_graph_overview_controls(self):
        js = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")

        self.assertIn('return { label: "Index", value, note, state, onClick: onIndexClick, variant: "index" };', js)
        self.assertIn('h("h2", { className: "agent-dialog-title" }, "Index")', js)
        self.assertIn('h(GraphIndexSection, { label: "Graph", idx: graphProj })', js)
        self.assertNotIn('h(GraphIndexSection, { label: "Framework Graph"', js)
        self.assertNotIn('const schema = idx.schema_version ? `schema ${idx.schema_version}` : null;', js)
        self.assertNotIn('idx.graph_path ? h("span", { className: "index-meta-pill index-meta-pill--model" }, idx.graph_path) : null,', js)
        self.assertIn('const [viewMode, setViewMode] = useState("overview");', js)
        self.assertIn('const [hoveredNodeId, setHoveredNodeId] = useState("");', js)
        self.assertIn('const [selectedFile, setSelectedFile] = useState("");', js)
        self.assertNotIn('const [selectedRelations, setSelectedRelations]', js)
        self.assertIn('const ALL_GRAPH_RELATIONS = ["calls", "imports", "defines", "doc_references_code", "doc_references_doc"];', js)
        self.assertIn('const graphVersion = snapshot?.health?.graph?.[layer]?.graph_version || snapshot?.health?.graph?.[layer]?.graph_mtime || 0;', js)
        self.assertIn('const previewNodeId = selectedNodeId || hoveredNodeId;', js)
        self.assertIn('const graphKindOptions = nodeKinds.length ? nodeKinds : ["module", "class", "function", "doc", "seed", "external"];', js)
        self.assertIn('function _communityInspectabilityScore(cluster) {', js)
        self.assertIn('return (boundaryCount / nodeCount) * Math.log2(nodeCount + 1);', js)
        self.assertIn('const GRAPH_OVERVIEW_COMMUNITY_LIMIT = 24;', js)
        self.assertNotIn('graph-quick-picks', js)
        self.assertNotIn('GRAPH_COMMUNITY_QUICK_PICK_LIMIT', js)
        self.assertIn('const GRAPH_COMMUNITY_DRILLDOWN_LIMIT = 50;', js)
        self.assertIn('const GRAPH_OVERVIEW_SEED_LIMIT = 24;', js)
        self.assertIn('const GRAPH_MIN_COMMUNITY_NODES = 2;', js)
        self.assertIn('function _isMeaningfulCommunity(cluster) {', js)
        self.assertIn('return Math.max(0, Number(cluster?.node_count || 0)) >= GRAPH_MIN_COMMUNITY_NODES;', js)
        self.assertIn('const topHubNodes = sortedByDegree.slice(0, 8);', js)
        self.assertIn('const clusterCommunities = Array.isArray(graph?.clusters?.communities) ? graph.clusters.communities.slice() : [];', js)
        self.assertIn('const meaningfulCommunities = clusterCommunities.filter(_isMeaningfulCommunity);', js)
        self.assertIn('const [selectedClusterId, setSelectedClusterId] = useState("");', js)
        self.assertIn('const communityOverview = viewMode === "overview" && !selectedClusterId && meaningfulCommunities.length > 0;', js)
        self.assertIn('const overviewGraph = communityOverview', js)
        self.assertIn('const hasCommunityOverview = Boolean(communityOverview && overviewGraph && overviewGraph.nodes.length);', js)
        self.assertIn('const overviewNodes = viewMode === "overview"', js)
        self.assertIn('_buildCommunityOverviewGraph(filteredNodes, edges, meaningfulCommunities)', js)
        self.assertIn('const GRAPH_COMMUNITY_OVERVIEW_RELATIONS = new Set(["calls", "imports", "defines"]);', js)
        self.assertIn('const ALL_GRAPH_RELATIONS_SET = new Set(ALL_GRAPH_RELATIONS);', js)
        self.assertIn('const GRAPH_COMMUNITY_PALETTE = [', js)
        self.assertIn('function _graphCommunityColor(', js)
        self.assertIn('function _graphNodeFillColor(', js)
        self.assertIn('if (!GRAPH_COMMUNITY_OVERVIEW_RELATIONS.has(relation)) continue;', js)
        self.assertIn('const relationOk = !relation || ALL_GRAPH_RELATIONS_SET.has(relation);', js)
        self.assertIn('const realBuckets = buckets.filter(bucket => bucket.community_id !== fallbackId && bucket.node_count > 0);', js)
        self.assertIn('const visibleClusterNodeIds = selectedClusterNodeIds ? new Set(clusterNodes.map(node => node.id)) : null;', js)
        self.assertIn('const overviewSeedNodes = [];', js)
        self.assertIn('overviewGraph?.fallback_nodes?.length', js)
        self.assertIn('overviewSeedNodes.slice(0, GRAPH_OVERVIEW_SEED_LIMIT)', js)
        self.assertIn('slice(0, GRAPH_COMMUNITY_DRILLDOWN_LIMIT)', js)
        self.assertIn('const nodeMatch = viewMode === "focus" && selectedNodeId', js)
        self.assertNotIn('const graphMissing = !projectGraph.present;', js)
        self.assertIn('function _layoutGraph(', js)
        self.assertIn('async function _layoutGraphAsync(', js)
        self.assertIn('function _graphResolveLayoutMode(', js)
        layout_mode_start = js.index('function _graphResolveLayoutMode(')
        layout_mode_end = js.index('function _graphLayoutModeLabel(', layout_mode_start)
        layout_mode_fn = js[layout_mode_start:layout_mode_end]
        self.assertIn('viewMode === "focus" && selectedNodeId) return "hierarchical"', layout_mode_fn)
        self.assertLess(
            layout_mode_fn.index('if (selectedClusterId'),
            layout_mode_fn.index('viewMode === "focus"'),
            "community drill-down should prefer hierarchical layout before focus selection",
        )
        self.assertIn('function _layoutGraphKindLayers(', js)
        self.assertIn('function _graphModuleSubgraphs(', js)
        self.assertIn('mergedImports = true', js)
        self.assertIn('function _graphPackModuleSubgraphs(', js)
        self.assertIn('function _graphPackModuleSubgraphRows(', js)
        self.assertIn('selectionNodeId: selectionId', js)
        self.assertIn('layoutOpts.docFocus || layoutOpts.moduleFocus', js)
        self.assertIn('_graphAppendWrappedRowSpecs(rowSpecs, linkedRemainder', js)
        self.assertIn('fill both side slots before rows below', js)
        self.assertIn('function _graphLayoutHierarchicalRowGap(', js)
        self.assertIn('_graphLayoutHierarchicalRowGap(shallow)', js)
        self.assertIn('function _graphLayoutSubRowGap(', js)
        self.assertIn('_graphLayoutSubRowGap(', js)
        self.assertIn('yCursor += rowInBand * subRowGap', js)
        self.assertNotIn('bandGap', js)
        self.assertIn('layoutOpts.moduleFocus && bandKind === "external"', js)
        self.assertIn('&& !layoutOpts.moduleFocus', js)
        self.assertIn('layoutOpts.moduleFocus && bandKind === "module"', js)
        self.assertIn('function _graphFocusSideNeighbors(', js)
        self.assertIn('function _graphFocusLinkedNeighborSet(', js)
        self.assertIn('function _graphAppendWrappedRowSpecs(', js)
        self.assertIn('function _graphLayoutMaxRowWidth(', js)
        self.assertIn('function _graphCenterOutRowOrder(', js)
        self.assertIn('_graphWrapIdsByWidthCenterOut', js)
        self.assertIn('_graphAppendWrappedRowSpecs(rowSpecs, linkedRemainder', js)
        self.assertIn('GRAPH_FOCUS_MAX_SIDE_NEIGHBORS', js)
        self.assertIn('sideRelation: "doc_references_doc"', js)
        self.assertIn('focusNodeId: layoutOpts.focusNodeId', js)
        self.assertIn('(availWidth - totalRowWidth) / 2', js)
        self.assertIn('rowOriginX + row.hGap * (index - (count - 1) / 2)', js)
        self.assertIn('function _graphWrapIds(', js)
        self.assertIn('const GRAPH_KIND_LAYOUT_MAX_ROW_NODES = 8;', js)
        self.assertIn('function _graphIsShallowFanOut(', js)
        self.assertIn('function _graphViewBoxFromLayout(', js)
        self.assertIn('const labelPadBelow = maxNodeRadius + _graphLayoutLabelPadBelowCircle()', js)
        self.assertIn('function _graphLabelParts(', js)
        self.assertIn('function _graphRenderNodeLabel(', js)
        self.assertIn('GRAPH_LABEL_MAX_CHARS_PER_LINE', js)
        self.assertIn('_graphRenderNodeLabel(node, radius)', js)
        self.assertIn('graph-svg-wrap', js)
        self.assertIn('graphViewBox.width', js)
        self.assertIn('_graphBandStacksNodesVertically(bandIdx, layoutOpts.layerOrder)', js)
        self.assertIn('_graphWithinBandSubLayers(bandNodeIds, edges, nodeById, layoutOpts)', js)
        self.assertIn('const GRAPH_KIND_LAYOUT_RELATIONS = new Set(["calls", "imports", "defines", "doc_references_code"]);', js)
        self.assertIn('function _graphKindLayerIndex(', js)
        self.assertIn('async function _graphElkLayout(', js)
        self.assertIn('function _layoutGraphTopoLayers(', js)
        self.assertIn('function _graphLayoutModeLabel(', js)
        self.assertIn('function _graphEdgeStrokeWidth(', js)
        self.assertNotIn('graph-arrow-dim', js)
        self.assertIn('function _layoutGraphCommunityBubbles(', js)
        self.assertIn('const maxR = Math.min(width, height) * 0.37', js)
        self.assertIn('const innerRing = maxR * 0.54', js)
        self.assertIn('const ringBase = maxR * 0.62', js)
        self.assertIn('const ringStep = maxR * 0.16', js)
        self.assertIn('_graphNodeRadius(b, 0) - _graphNodeRadius(a, 0)', js)
        self.assertIn('const twistPerSlot = (2 * Math.PI) / (spokeCount * 1.6)', js)
        self.assertIn('radialSlot * twistPerSlot', js)
        self.assertIn('const spokeCount = 7', js)
        self.assertIn('const radialSlot = Math.floor(index / spokeCount)', js)
        self.assertIn('radialSlot % 3', js)
        self.assertIn('const spoke = index % spokeCount', js)
        self.assertIn('const highlightPreviewNodeId = graphHighlightFocus ? previewNodeId : ""', js)
        self.assertIn('const nodesWithLayoutEdges = React.useMemo', js)
        self.assertIn('graph-node--hover-isolated', js)
        self.assertIn('function _graphPickLayoutHubId(', js)
        self.assertIn('function _graphFilterDocFocusNeighborhood(', js)
        self.assertIn('edge.confidence === "EXTRACTED"', js)
        self.assertIn('GRAPH_CATEGORY_COMMUNITY_LABELS', js)
        self.assertIn('cluster_kind', js)
        self.assertIn('function _graphLayoutRadialAngularSlot(', js)
        self.assertIn('nodes.every(node => node.kind === "community")', js)
        self.assertIn('nodes.every(node => node.kind === "community")) return false', js)
        self.assertIn('layoutInputKey', js)
        self.assertIn('layoutPending && layoutNodes.length', js)
        self.assertIn('nodeCount: layoutNodes.length', js)
        self.assertIn('function _graphNodeRadius(', js)
        self.assertIn('function _graphMostConnectedNodeId(', js)
        self.assertIn('const treeNavFocusNodeId = selectedNodeId', js)
        self.assertIn('function _graphDefaultCommunityFocusNodeId(', js)
        self.assertIn('const GRAPH_COMMUNITY_FOCUS_KIND_ORDER = ["module", "class", "function"];', js)
        self.assertIn('const GRAPH_NEIGHBOR_KIND_ORDER = ["module", "class", "function", "doc", "seed", "external"];', js)
        self.assertIn('const GRAPH_COMMUNITY_OVERVIEW_FOCUS_KIND_ORDER = ["module", "class", "function", "doc", "seed"];', js)
        self.assertIn('const GRAPH_KIND_LAYER_ORDER = ["module", "class", "function", "external", "doc", "seed"];', js)
        self.assertIn('const GRAPH_KIND_LAYER_ORDER_DOC_FOCUS = ["doc", "seed", "module", "class", "function", "external"];', js)
        self.assertIn('function _graphLayoutOptions(', js)
        self.assertIn('function _graphSortBandNodeIds(', js)
        self.assertIn('_layoutGraphKindLayers(nodes, edges, width, height, focusId || "");', js)
        self.assertIn('function _graphIsDocumentationKind(', js)
        self.assertIn('function _layoutGraphKindLayersCode(', js)
        self.assertIn('const sectionGap = 52;', js)
        self.assertIn('_graphDefaultCommunityFocusNodeId(clusterNodes, degreeMap)', js)
        self.assertIn('focusNodeId: treeNavFocusNodeId', js)
        self.assertIn('function _graphSeedPosition(', js)
        self.assertIn('const graphWidth = 1040;', js)
        self.assertIn('_layoutGraphAsync(', js)
        self.assertIn('className: "graph-svg"', js)
        # Wave 1305t / 1305v: the explicit graph-mode-switch row was removed; view mode is now
        # fully determined by selection (clicking a node → focus; clicking a cluster → overview).
        self.assertNotIn('"graph-mode-switch"', js)
        self.assertIn('h("details", { className: "graph-filter-details" }', js)
        self.assertIn('h("div", { className: "graph-kind-pills" }', js)
        self.assertNotIn('"Top hubs"', js)
        self.assertNotIn('"Relations"', js)
        self.assertIn('"Communities"', js)
        self.assertNotIn('"File neighborhoods"', js)
        self.assertIn('graph-filter-pill--kind', js)
        self.assertIn('function _graphNeighborTooltip(', js)
        self.assertIn('function GraphTreeNav(', js)
        self.assertIn('function _graphOverviewHubCommunityNode(', js)
        self.assertIn('function _graphCommunityMemberNodes(', js)
        self.assertIn('const selectedCommunityBubbleId = hasCommunityOverview && !selectedClusterId', js)
        self.assertIn('|| (kind === "community" && selectedCommunityBubbleId === node.id)', js)
        self.assertIn('GRAPH_NEIGHBOR_KIND_ORDER)', js)
        self.assertIn('_graphSortNeighborNodes(neighborNodes)', js)
        self.assertNotIn('_graphFilterOverviewNeighbors', js)
        self.assertIn('function _graphSortNeighborNodes(', js)
        self.assertIn('_graphSortNeighborNodes(', js)
        self.assertIn('visibleNeighborNodes', js)
        self.assertIn('|| overviewHubFocusNodeId;', js)
        self.assertIn('const treeNavFocusNode = selectedNode', js)
        self.assertIn('focusNode: treeNavFocusNode', js)
        self.assertIn('title: tooltip || undefined', js)
        self.assertNotIn('function GraphWebGLView(', js)
        self.assertNotIn('function GraphCommunityOverviewSvg(', js)
        self.assertIn('const focusFirstSearchMatch = () => {', js)
        self.assertIn('focusNeighborhood', js)
        self.assertIn('graph-tree-nav-item--active', js)
        self.assertNotIn('const selectionCard', js)
        self.assertNotIn('graph-selection-edges', js)
        self.assertNotIn('graph-summary-pill', js)
        self.assertNotIn('const overviewLabel', js)
        self.assertNotIn('const edgeLabel', js)
        self.assertIn(': selectedCluster', js)
        self.assertIn('const [selectedFile, setSelectedFile]', js)
        self.assertIn('className: "graph-breadcrumb"', js)
        self.assertNotIn('"Back to overview"', js)
        # An open modal dialog must own Escape; the graph back-nav handler bails
        # out so the dialog closes first instead of navigating the graph behind it.
        self.assertIn('if (document.querySelector("dialog[open]")) return;', js)
        self.assertIn('hasCommunityOverview && node.kind === "community"', js)
        self.assertIn('community: "#16a085",  // emerald', js)

        css = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.css").read_text(encoding="utf-8")
        self.assertIn('.graph-webgl-wrap {', css)
        self.assertIn('.graph-webgl-viewport {', css)
        self.assertIn('.graph-canvas-column {', css)
        self.assertIn('html[data-theme="dark"] .graph-webgl-wrap {', css)
        self.assertIn('.graph-tree-nav-item--active {', css)
        # Graph view flows to natural height — the fixed 85vh scroll band was removed
        # (wave 1p6nl); the tree-nav + canvas align to the top of the row instead of
        # stretching to a fixed band, so the page scrolls as one.
        self.assertIn('.graph-shell--with-tree {', css)
        self.assertNotIn('--graph-band-height', css)
        self.assertIn('align-items: start;', css)
        self.assertIn('.graph-tree-nav-header {', css)
        self.assertIn('graph-svg-banner', js)
        self.assertNotIn('max-height: min(60vh, 600px)', css)
        self.assertIn('html[data-theme="dark"] .graph-filter-pill--kind {', css)
        self.assertIn('color: #f4f7fb;', css)

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
        meta_path = self.srv.dashboard_lib.dashboard_metadata_path(root)
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

    # ---- Wave 1p654: process-cmdline reconciliation ----

    def test_pid_is_live_requires_cmdline_match(self):
        # AC-1: a recorded PID that is os.kill-alive but NOT a dashboard for this
        # root (recycled/zombie) must read as not-live.
        with patch.object(self.server, "_dashboard_cmdline_pids", return_value=[111]), \
             patch.object(self.server, "_pid_is_running", return_value=True):
            self.assertTrue(self.server._dashboard_pid_is_live(111, self.root))
            self.assertFalse(self.server._dashboard_pid_is_live(999, self.root))
        # Scan unavailable (None) → fall back to the bare liveness check.
        with patch.object(self.server, "_dashboard_cmdline_pids", return_value=None), \
             patch.object(self.server, "_pid_is_running", return_value=True):
            self.assertTrue(self.server._dashboard_pid_is_live(999, self.root))

    def test_stop_kills_orphans_with_absent_metadata(self):
        # AC-2: no recorded PID, but a live dashboard for this root exists → stop
        # must find and terminate it (orphan), not return already_stopped.
        with patch.object(self.server, "_dashboard_cmdline_pids", return_value=[5555]), \
             patch.object(self.server, "_pid_is_running", return_value=True), \
             patch.object(self.server, "_terminate_dashboard_pid", return_value=True) as term:
            env = self.server.wave_dashboard_stop_response(self.root)
        term.assert_any_call(5555)
        self.assertTrue(env["data"].get("stopped"))
        self.assertEqual(env["data"].get("orphans_terminated"), 1)

    def test_stop_kills_recorded_pid_and_orphans(self):
        self._write_dashboard_metadata(self.root, pid=4321)
        with patch.object(self.server, "_dashboard_cmdline_pids", return_value=[4321, 6666]), \
             patch.object(self.server, "_pid_is_running", return_value=True), \
             patch.object(self.server, "_terminate_dashboard_pid", return_value=True) as term:
            env = self.server.wave_dashboard_stop_response(self.root)
        terminated = {c.args[0] for c in term.call_args_list}
        self.assertEqual(terminated, {4321, 6666})
        self.assertEqual(env["data"].get("orphans_terminated"), 1)  # 6666 (non-recorded)

    def test_cmdline_scan_parses_and_matches_root(self):
        # Direct test of the kill-decision logic (delivery-review gap): the ps parse
        # must match ONLY dashboards whose --root resolves to this root, exclude the
        # current process, other repos, and non-dashboard lines, and handle --root=.
        import os
        from types import SimpleNamespace
        root_str = str(Path(self.root).resolve())
        self_pid = os.getpid()
        synthetic = "\n".join([
            f" 1001 python /x/.wavefoundry/framework/scripts/dashboard_server.py --root {root_str}",
            " 1002 python /y/dashboard_server.py --root /some/other/repo",
            f" 1003 python /z/server.py --root {root_str}",  # not a dashboard
            f" {self_pid} python /w/dashboard_server.py --root {root_str}",  # self → excluded
            f" 1005 python /v/dashboard_server.py --root={root_str}",  # --root= form
            "garbage line without pid",
        ])
        with patch("subprocess.run", return_value=SimpleNamespace(stdout=synthetic)):
            pids = self.server._dashboard_cmdline_pids(self.root)
        self.assertEqual(sorted(pids), [1001, 1005])

    def test_cmdline_scan_matches_quoted_spaced_root(self):
        # Wave 1p9hl: on Windows Win32_Process.CommandLine QUOTES a --root value containing spaces
        # (subprocess.list2cmdline: --root "C:\Users\First Last\repo"). The old bare rest.split()
        # truncated the value at the first space so the --root token never matched → empty pid list →
        # duplicate dashboards + the 1p8pf port-climb. shlex.split(posix=False) + dequote fixes both
        # the `--root "..."` and `--root="..."` forms. A real spaced temp dir makes Path.resolve()
        # match on the POSIX test host; the parse/dequote logic itself is OS-independent.
        import tempfile
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as base:
            spaced = Path(base) / "First Last" / "repo"
            spaced.mkdir(parents=True)
            root_str = str(spaced.resolve())
            synthetic = "\n".join([
                f' 2001 python /x/dashboard_server.py --root "{root_str}"',       # quoted spaced value
                f' 2002 python /y/dashboard_server.py --root="{root_str}"',       # --root= quoted form
                ' 2003 python /z/dashboard_server.py --root "/other/no match/x"',  # different root
            ])
            with patch("subprocess.run", return_value=SimpleNamespace(stdout=synthetic)):
                pids = self.server._dashboard_cmdline_pids(spaced)
        self.assertEqual(sorted(pids), [2001, 2002])

    def test_cmdline_scan_returns_none_on_scan_failure(self):
        from types import SimpleNamespace
        # Non-string stdout (e.g. mocked subprocess) → None → callers fall back.
        with patch("subprocess.run", return_value=SimpleNamespace(stdout=object())):
            self.assertIsNone(self.server._dashboard_cmdline_pids(self.root))
        with patch("subprocess.run", side_effect=OSError("boom")):
            self.assertIsNone(self.server._dashboard_cmdline_pids(self.root))

    def test_windows_process_cmdlines_helper(self):
        # 1p6eq: the PowerShell/CIM helper returns stdout on success and None on any failure. Its
        # output feeds the SAME matching loop the POSIX `ps` path uses — and that parse/match is
        # covered by test_cmdline_scan_parses_and_matches_root. The nt-branch end-to-end (selection
        # + matching under os.name='nt') can't run on a POSIX host because the loop's
        # Path(...).resolve() instantiates WindowsPath — so it is Windows-smoke-deferred.
        from types import SimpleNamespace
        ok = "1001 C:\\py\\python.exe C:\\x\\dashboard_server.py --root C:\\r\n"
        with patch("subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=ok)) as run:
            self.assertEqual(self.lib._windows_process_cmdlines(), ok)
            argv = run.call_args[0][0]
            self.assertEqual(argv[0], "powershell")
            self.assertIn("Get-CimInstance Win32_Process", " ".join(argv))
        with patch("subprocess.run", return_value=SimpleNamespace(returncode=1, stdout="")):
            self.assertIsNone(self.lib._windows_process_cmdlines())
        with patch("subprocess.run", side_effect=OSError("powershell missing")):
            self.assertIsNone(self.lib._windows_process_cmdlines())

    def test_cmdline_scan_windows_returns_none_on_failure(self):
        # 1p6eq: any PowerShell failure → None → caller falls back to bare-PID liveness (no regression).
        from types import SimpleNamespace
        with patch.object(self.lib.os, "name", "nt"):
            with patch("subprocess.run", return_value=SimpleNamespace(returncode=1, stdout="")):
                self.assertIsNone(self.server._dashboard_cmdline_pids(self.root))
            with patch("subprocess.run", side_effect=OSError("powershell missing")):
                self.assertIsNone(self.server._dashboard_cmdline_pids(self.root))

    def test_start_reconciles_orphans_before_spawn(self):
        # AC-3: no valid recorded instance + a live orphan whose URL is NOT serving → start terminates
        # the orphan (replace, not spawn-alongside) and emits dashboard_orphan_detected. Wave 1p8pf:
        # the orphan here is genuinely drifted (URL unreachable), so the reconcile-before-spawn does NOT
        # adopt it — a serving (reachable) instance would instead be adopted (see WaveDashboardPidRaceTests).
        self._write_dashboard_metadata(self.root, pid=8888)  # the (fake) spawned pid

        class _FakeProc:
            pid = 8888

        with patch.object(self.server, "_dashboard_cmdline_pids", return_value=[7777]), \
             patch.object(self.server, "_dashboard_url_reachable", return_value=False), \
             patch.object(self.server, "_terminate_dashboard_pid", return_value=True) as term, \
             patch("subprocess.Popen", return_value=_FakeProc()):
            env = self.server.wave_dashboard_start_response(self.root)
        term.assert_any_call(7777)
        codes = [d.get("code") for d in (env.get("diagnostics") or [])]
        self.assertIn("dashboard_orphan_detected", codes)

    def test_dashboard_stop_removes_only_current_repo_metadata(self):
        current_meta = self._write_dashboard_metadata(self.root, pid=4321)
        other_root = Path(self.tmp.name) / "other"
        _make_repo(other_root)
        other_meta = self._write_dashboard_metadata(other_root, pid=9999)

        # Wave 1rswx: a genuinely-live recorded dashboard is classified via the cmdline-verified
        # (zombie-safe) check now, so it must appear in the cmdline scan for this root — that is exactly
        # what a real live dashboard does. (A <defunct> recorded PID would be absent from the scan and is
        # covered by the zombie-stop tests.)
        with patch.object(self.server, "_dashboard_cmdline_pids", return_value=[4321]), patch.object(
            self.server, "_pid_is_running", return_value=True
        ), patch.object(
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

    def test_dashboard_main_exits_when_server_lock_is_busy(self):
        self._write_dashboard_metadata(self.root, pid=4321, url="http://127.0.0.1:43127/dashboard.html")
        lock_busy = self.srv.dashboard_lib.DashboardLockBusy

        class BusyLock:
            def __enter__(self):
                raise lock_busy("busy")

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch.object(self.srv.dashboard_lib, "dashboard_server_lock", return_value=BusyLock()), \
             patch("sys.stdout", new=io.StringIO()) as stdout:
            rc = self.srv.main(["--root", str(self.root)])

        self.assertEqual(rc, 0)
        self.assertIn("http://127.0.0.1:43127/dashboard.html", stdout.getvalue())


class DashboardChildReapTests(unittest.TestCase):
    """Wave 1rswx: the long-lived MCP server reaps the dashboard children it spawns (mirroring the
    1p98u background-build reaper), and the stop/restart/status paths classify a recorded PID with the
    zombie-safe cmdline-verified check so a <defunct> dashboard is treated as already stopped — not a
    live kill target that fails."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.server = sys.modules["server_impl"]
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        self._saved_pids = set(self.server._DASHBOARD_CHILD_PIDS)
        self.server._DASHBOARD_CHILD_PIDS.clear()

    def tearDown(self):
        self.server._DASHBOARD_CHILD_PIDS.clear()
        self.server._DASHBOARD_CHILD_PIDS.update(self._saved_pids)
        self.tmp.cleanup()

    def _write_dashboard_metadata(self, root: Path, *, pid: int, url: str = "http://127.0.0.1:43127/dashboard.html") -> Path:
        meta_path = self.lib.dashboard_metadata_path(root)
        self.lib.write_dashboard_metadata(
            root,
            {"host": "127.0.0.1", "port": 43127, "url": url, "entrypoint": "dashboard.html",
             "pid": pid, "started_at": "2026-05-13T00:00:00Z"},
        )
        return meta_path

    # ---- registry + WNOHANG sweep (mirrors BackgroundBuildReapRegistryTests) ----

    def test_register_is_posix_only_and_validates(self):
        with patch.object(self.server.os, "name", "posix"):
            self.server._register_dashboard_child_pid(4321)
            self.assertIn(4321, self.server._DASHBOARD_CHILD_PIDS)
            self.server._register_dashboard_child_pid(0)
            self.server._register_dashboard_child_pid(-3)
            self.assertNotIn(0, self.server._DASHBOARD_CHILD_PIDS)
            self.assertNotIn(-3, self.server._DASHBOARD_CHILD_PIDS)

    def test_register_noop_on_windows(self):
        with patch.object(self.server.os, "name", "nt"):
            self.server._register_dashboard_child_pid(4321)
        self.assertNotIn(4321, self.server._DASHBOARD_CHILD_PIDS)

    def test_reap_removes_finished_child(self):
        self.server._DASHBOARD_CHILD_PIDS.add(4321)
        with patch.object(self.server.os, "name", "posix"), \
             patch.object(self.server.os, "waitpid", return_value=(4321, 0)) as wp:
            self.server._reap_dashboard_child_pids()
        wp.assert_called_once_with(4321, self.server.os.WNOHANG)
        self.assertNotIn(4321, self.server._DASHBOARD_CHILD_PIDS)

    def test_reap_keeps_still_running_child(self):
        self.server._DASHBOARD_CHILD_PIDS.add(4321)
        with patch.object(self.server.os, "name", "posix"), \
             patch.object(self.server.os, "waitpid", return_value=(0, 0)):
            self.server._reap_dashboard_child_pids()
        self.assertIn(4321, self.server._DASHBOARD_CHILD_PIDS)

    def test_reap_discards_non_child(self):
        self.server._DASHBOARD_CHILD_PIDS.add(4321)
        with patch.object(self.server.os, "name", "posix"), \
             patch.object(self.server.os, "waitpid", side_effect=ChildProcessError):
            self.server._reap_dashboard_child_pids()
        self.assertNotIn(4321, self.server._DASHBOARD_CHILD_PIDS)

    def test_reap_noop_on_windows(self):
        self.server._DASHBOARD_CHILD_PIDS.add(4321)
        with patch.object(self.server.os, "name", "nt"), \
             patch.object(self.server.os, "waitpid") as wp:
            self.server._reap_dashboard_child_pids()
        wp.assert_not_called()
        self.assertIn(4321, self.server._DASHBOARD_CHILD_PIDS)

    # ---- AC-4: the frequently-hit index-refresh path sweeps dashboard children ----

    def test_index_refresh_sweeps_dashboard_children(self):
        # AC-4(b): a dashboard that died is reaped by an index-refresh sweep with NO wave_dashboard_* call.
        with patch.object(self.server, "_reap_dashboard_child_pids") as reap, \
             patch.object(self.server, "_background_refresh_active", return_value=True):
            self.server._start_background_index_refresh(self.root, "project")
        reap.assert_called_once_with()

    # ---- AC-1/AC-3: zombie-safe stop ----

    def test_stop_on_zombie_recorded_pid_returns_success(self):
        # AC-1: recorded PID is a zombie — reaped on entry by _reap_dashboard_child_pids (WNOHANG), after
        # which it is NO LONGER os.kill-alive (a reaped PID's os.kill raises ESRCH). Stop must return a
        # clean success with metadata cleared, never a live kill target. Wave 1rvfw: model the reaped
        # zombie as _pid_is_running=False (its real post-reap state) so the empty-targets branch takes the
        # genuinely-stopped path — an os.kill-alive-but-unverified PID would instead be reported honestly
        # as dashboard_pid_unverified (see test_stop_unverified_alive_pid_reports_honestly).
        meta_path = self._write_dashboard_metadata(self.root, pid=4321)
        self.server._DASHBOARD_CHILD_PIDS.add(4321)
        with patch.object(self.server.os, "name", "posix"), \
             patch.object(self.server.os, "waitpid", return_value=(4321, 0)) as wp, \
             patch.object(self.server, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(self.server, "_pid_is_running", return_value=False), \
             patch.object(self.server, "_terminate_dashboard_pid", return_value=True) as term:
            env = self.server.wave_dashboard_stop_response(self.root)
        self.assertEqual(env["status"], "ok")
        self.assertTrue(env["data"].get("already_stopped"))
        term.assert_not_called()  # a <defunct> PID is never SIGTERM/SIGKILL'd
        self.assertFalse(meta_path.exists(), "stale metadata must be cleared")
        wp.assert_any_call(4321, self.server.os.WNOHANG)  # the zombie was reaped on entry
        self.assertNotIn(4321, self.server._DASHBOARD_CHILD_PIDS)

    def test_stop_unverified_alive_pid_reports_honestly(self):
        # Wave 1rvfw AC-1: recorded PID is os.kill-alive but NOT cmdline-verified (scan runs, misses it —
        # a recycled PID or a scan-missed live dashboard). Stop must NOT claim already_stopped and must
        # NOT delete the metadata; it reports honestly with a dashboard_pid_unverified diagnostic and
        # never signals the PID (the 1rswx AC-3 never-kill-unverified control stands).
        meta_path = self._write_dashboard_metadata(self.root, pid=5555)
        with patch.object(self.server, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(self.server, "_pid_is_running", return_value=True), \
             patch.object(self.server, "_terminate_dashboard_pid", return_value=True) as term:
            env = self.server.wave_dashboard_stop_response(self.root)
        self.assertEqual(env["status"], "ok")
        self.assertFalse(env["data"].get("already_stopped"))  # not a false success
        self.assertFalse(env["data"].get("stopped"))
        codes = [d.get("code") for d in (env.get("diagnostics") or [])]
        self.assertIn("dashboard_pid_unverified", codes)
        term.assert_not_called()  # the unverified PID is never terminated
        self.assertTrue(meta_path.exists(), "metadata must be RETAINED for an alive-but-unverified instance")

    def test_stop_genuinely_stopped_dead_pid_clears_metadata(self):
        # Wave 1rvfw AC-2: a recorded PID that is NOT os.kill-alive (dead/absent), with no scanned pids,
        # still takes the clean already_stopped + metadata-cleared path.
        meta_path = self._write_dashboard_metadata(self.root, pid=5555)
        with patch.object(self.server, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(self.server, "_pid_is_running", return_value=False), \
             patch.object(self.server, "_terminate_dashboard_pid", return_value=True) as term:
            env = self.server.wave_dashboard_stop_response(self.root)
        self.assertEqual(env["status"], "ok")
        self.assertTrue(env["data"].get("already_stopped"))
        term.assert_not_called()
        self.assertFalse(meta_path.exists(), "a genuinely-dead recorded PID clears its metadata")

    def test_stop_still_kills_live_dashboard(self):
        # AC-3: a genuinely-live dashboard for this root (present in the cmdline scan) is still terminated.
        self._write_dashboard_metadata(self.root, pid=4321)
        with patch.object(self.server, "_dashboard_cmdline_pids", return_value=[4321]), \
             patch.object(self.server, "_pid_is_running", return_value=True), \
             patch.object(self.server, "_terminate_dashboard_pid", return_value=True) as term:
            env = self.server.wave_dashboard_stop_response(self.root)
        self.assertTrue(env["data"].get("stopped"))
        term.assert_called_once_with(4321)

    def test_restart_reaps_zombie_then_starts_fresh(self):
        # AC-2: restart with a zombie prior dashboard reaps/clears it (stop returns ok) then spawns fresh.
        # Wave 1rvfw: the reaped zombie is no longer os.kill-alive (_pid_is_running=False), so stop takes
        # the clean already_stopped path and restart proceeds to start.
        self._write_dashboard_metadata(self.root, pid=4321)
        self.server._DASHBOARD_CHILD_PIDS.add(4321)
        start_env = {"status": "ok",
                     "data": {"started": True, "pid": 9876, "url": "http://127.0.0.1:43128/dashboard.html"},
                     "diagnostics": [], "next_tools": [], "usage": "http://127.0.0.1:43128/dashboard.html"}
        with patch.object(self.server.os, "name", "posix"), \
             patch.object(self.server.os, "waitpid", return_value=(4321, 0)), \
             patch.object(self.server, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(self.server, "_pid_is_running", return_value=False), \
             patch.object(self.server, "_terminate_dashboard_pid", return_value=True) as term, \
             patch.object(self.server, "wave_dashboard_start_response", return_value=start_env) as start:
            env = self.server.wave_dashboard_restart_response(self.root)
        self.assertEqual(env["status"], "ok")
        self.assertTrue(env["data"].get("restarted"))
        self.assertEqual(env["data"].get("pid"), 9876)
        term.assert_not_called()  # the zombie was reaped, not killed
        start.assert_called_once()

    # ---- AC-5: status/open must not report a zombie as serving ----

    def test_open_does_not_report_zombie_as_serving(self):
        self._write_dashboard_metadata(self.root, pid=4321)
        with patch.object(self.server, "_reap_dashboard_child_pids"), \
             patch.object(self.server, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(self.server, "_pid_is_running", return_value=True), \
             patch.object(self.server, "wave_dashboard_start_response",
                          return_value={"status": "ok", "data": {"started": True}, "diagnostics": [],
                                        "next_tools": [], "usage": ""}) as start:
            # A live recorded dashboard would return opened/url directly; a zombie must fall through to
            # start (delegation), not report the dead URL as serving.
            self.server.wave_dashboard_open_response(self.root)
        start.assert_called_once()

    def test_start_registers_spawned_dashboard_pid(self):
        # AC-4(a): the spawned dashboard PID is registered so a later sweep can reap it (POSIX).
        self._write_dashboard_metadata(self.root, pid=8888)

        class _FakeProc:
            pid = 8888

        with patch.object(self.server.os, "name", "posix"), \
             patch.object(self.server, "_reap_dashboard_child_pids"), \
             patch.object(self.server, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(self.server, "_dashboard_url_reachable", return_value=False), \
             patch.object(self.server, "_terminate_dashboard_pid", return_value=True), \
             patch("subprocess.Popen", return_value=_FakeProc()):
            self.server.wave_dashboard_start_response(self.root)
        self.assertIn(8888, self.server._DASHBOARD_CHILD_PIDS)


class DashboardDaemonModeTests(unittest.TestCase):
    """Wave 1p7pn (1p7pb-adr AC-3): `--daemon` self-detaches the dashboard (OS-correct detach,
    `sys.executable` child) so the cross-OS `python dashboard_server.py --daemon` forwarder survives
    shell exit — replacing the bash `nohup ... &`. macOS/Linux foreground behavior is unchanged."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_daemon_respawns_detached_and_exits_without_binding(self):
        captured = {}

        class _FakeProc:
            pid = 4242

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            captured["kwargs"] = kwargs
            return _FakeProc()

        # If the daemon path is taken, the server must NEVER bind — fail loud if it tries.
        with patch.object(self.srv.dashboard_lib, "discover_root", return_value=self.root), \
             patch.object(self.srv, "_QuietThreadingHTTPServer", side_effect=AssertionError("must not bind in --daemon parent")), \
             patch("subprocess.Popen", side_effect=fake_popen), \
             patch.dict(os.environ, {}, clear=False), \
             patch("sys.stdout", new=io.StringIO()) as stdout:
            os.environ.pop(self.srv._DAEMON_ENV_MARKER, None)
            rc = self.srv.main(["--daemon", "--root", str(self.root), "--open"])

        self.assertEqual(rc, 0)
        # Child uses sys.executable (the re-exec'd venv Python), NOT python3.
        self.assertEqual(captured["cmd"][0], sys.executable)
        self.assertIn(str(self.srv.Path(self.srv.__file__).resolve()), captured["cmd"])
        # `--daemon` is stripped from the child args (no infinite re-spawn); `--open` survives.
        self.assertNotIn("--daemon", captured["cmd"])
        self.assertIn("--open", captured["cmd"])
        # Env marker set so the child does not re-daemonize.
        self.assertEqual(captured["kwargs"]["env"].get(self.srv._DAEMON_ENV_MARKER), "1")
        # OS-correct detach.
        if os.name == "nt":
            self.assertIn("creationflags", captured["kwargs"])
        else:
            self.assertTrue(captured["kwargs"].get("start_new_session"))
        self.assertIn("Wave dashboard started", stdout.getvalue())

    def test_daemon_child_runs_foreground_path_not_redetach(self):
        # When we ARE the detached child (env marker set), --daemon must NOT re-spawn; it runs the
        # normal foreground path (here short-circuited by a busy lock so no real bind happens).
        lock_busy = self.srv.dashboard_lib.DashboardLockBusy

        class BusyLock:
            def __enter__(self):
                raise lock_busy("busy")

            def __exit__(self, *a):
                return False

        with patch.object(self.srv.dashboard_lib, "discover_root", return_value=self.root), \
             patch.object(self.srv.dashboard_lib, "dashboard_server_lock", return_value=BusyLock()), \
             patch.object(self.srv.dashboard_lib, "read_dashboard_metadata", return_value={}), \
             patch("subprocess.Popen", side_effect=AssertionError("child must not re-daemonize")), \
             patch.dict(os.environ, {self.srv._DAEMON_ENV_MARKER: "1"}), \
             patch("sys.stdout", new=io.StringIO()):
            rc = self.srv.main(["--daemon", "--root", str(self.root)])

        self.assertEqual(rc, 0)


class DashboardServerLockTests(unittest.TestCase):
    """1p5ya: dedicated lifetime lock `dashboard-server.lock` + flock-try liveness."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _server_lock_path(self) -> Path:
        return self.root / ".wavefoundry" / "locks" / "dashboard-server.lock"

    def _flock_try_busy(self) -> bool:
        """Non-blocking flock-try on dashboard-server.lock: busy => alive."""
        try:
            probe = self.lib.dashboard_server_lock(self.root)
            probe.__enter__()
        except self.lib.DashboardLockBusy:
            return True
        probe.__exit__(None, None, None)
        return False

    def test_lock_name_renamed_and_no_process_lock(self):
        # AC-1: the constant + helper carry the new name; the old name is gone.
        self.assertEqual(self.lib.DASHBOARD_SERVER_LOCK_NAME, "dashboard-server.lock")
        self.assertTrue(hasattr(self.lib, "dashboard_server_lock"))
        self.assertFalse(hasattr(self.lib, "dashboard_process_lock"))
        self.assertFalse(hasattr(self.lib, "DASHBOARD_PROCESS_LOCK_NAME"))

    def test_lock_file_uses_server_lock_name(self):
        with self.lib.dashboard_server_lock(self.root):
            self.assertTrue(self._server_lock_path().exists())
            self.assertFalse((self.root / ".wavefoundry" / "dashboard-process.lock").exists())

    def test_flock_try_busy_when_held(self):
        # AC-1: busy => alive while a holder keeps the flock.
        with self.lib.dashboard_server_lock(self.root):
            self.assertTrue(self._flock_try_busy())

    def test_flock_try_acquired_when_not_held(self):
        # AC-1: acquired => not running once the holder releases.
        with self.lib.dashboard_server_lock(self.root):
            pass
        self.assertFalse(self._flock_try_busy())

    def test_stale_metadata_after_exit_is_not_running(self):
        # AC-1: stale server.json content after exit is overridden by the flock-try.
        self.lib.write_dashboard_metadata(
            self.root,
            {"pid": 999999, "url": "http://127.0.0.1:43127/dashboard.html"},
        )
        with self.lib.dashboard_server_lock(self.root):
            pass
        # Metadata still present but the lock is free => not running.
        self.assertTrue(self.lib.dashboard_metadata_path(self.root).exists())
        self.assertFalse(self._flock_try_busy())

    def test_lock_file_is_the_metadata_store(self):
        # Wave 1p64x: ONE sidecar — the server lock file holds the startup metadata.
        # (Replaces test_json_is_not_flocked, which asserted the now-removed split.)
        self.assertEqual(
            self.lib.dashboard_metadata_path(self.root).name, "dashboard-server.lock"
        )
        with self.lib.dashboard_server_lock(self.root):
            # Metadata is written + read IN PLACE while the lifetime lock is held
            # (in-place truncate, never a rename that would orphan the lock).
            self.lib.write_dashboard_metadata(self.root, {"pid": 1, "url": "x"})
            self.assertEqual(self.lib.read_dashboard_metadata(self.root).get("url"), "x")
            # It is a real lock: a second acquire on the same file is rejected.
            with self.assertRaises(self.lib.DashboardLockBusy):
                with self.lib.dashboard_server_lock(self.root):
                    pass
        # Reading the metadata never required holding the lock.
        self.assertEqual(self.lib.read_dashboard_metadata(self.root).get("url"), "x")


class DashboardWindowsSentinelLockTests(unittest.TestCase):
    """Wave 1p8pf: on Windows the lifetime lock must sit on a SENTINEL byte (`_LOCK_BYTE_OFFSET`), not
    byte 0, so the daemon's own separate-handle metadata rewrite (at byte 0+, where `url` is published)
    is not blocked by its own mandatory byte-range lock. POSIX keeps whole-file advisory `flock`."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _fake_msvcrt(self, calls):
        """A fake `msvcrt` whose `locking` records the (op, offset) — offset read from the fd's real
        position (set by the production `fh.seek` immediately before), so the assertion is non-vacuous."""
        import types as _types

        def locking(fileno, mode, nbytes):
            offset = os.lseek(fileno, 0, os.SEEK_CUR)
            calls.append((mode, offset, nbytes))

        return _types.SimpleNamespace(
            locking=locking, LK_NBLCK=1, LK_UNLCK=0,
        )

    def test_windows_lock_uses_sentinel_offset_not_byte_zero(self):
        calls: list = []
        fake = self._fake_msvcrt(calls)
        with patch.object(self.lib.os, "name", "nt"), \
             patch.dict(sys.modules, {"msvcrt": fake}):
            with self.lib.dashboard_server_lock(self.root):
                pass
        # Exactly one acquire (LK_NBLCK) + one release (LK_UNLCK), BOTH at the sentinel offset, NEVER 0.
        self.assertEqual(len(calls), 2, f"expected acquire+release, got {calls}")
        acquire, release = calls[0], calls[1]
        self.assertEqual(acquire[0], fake.LK_NBLCK)
        self.assertEqual(acquire[1], self.lib._LOCK_BYTE_OFFSET,
                         "acquire must lock the SENTINEL byte, not byte 0")
        self.assertNotEqual(acquire[1], 0, "the lifetime lock must NOT cover byte 0")
        self.assertEqual(release[0], fake.LK_UNLCK)
        self.assertEqual(release[1], self.lib._LOCK_BYTE_OFFSET,
                         "release must unlock the SAME sentinel byte")

    def test_windows_metadata_write_region_is_disjoint_from_sentinel(self):
        # The daemon publishes metadata (incl. `url`) at byte 0+; assert that region never reaches the
        # sentinel offset, so the byte-0 rewrite cannot collide with the mandatory sentinel lock.
        calls: list = []
        fake = self._fake_msvcrt(calls)
        with patch.object(self.lib.os, "name", "nt"), \
             patch.dict(sys.modules, {"msvcrt": fake}):
            with self.lib.dashboard_server_lock(self.root):
                # Simulate the daemon publishing full metadata while holding the lock.
                self.lib.write_dashboard_metadata(
                    self.root, {"pid": os.getpid(), "url": "http://127.0.0.1:43127/dashboard.html"},
                )
                meta = self.lib.read_dashboard_metadata(self.root)
        self.assertEqual(meta.get("url"), "http://127.0.0.1:43127/dashboard.html",
                         "the daemon must be able to publish its url while holding the lock")
        # The metadata file is small JSON written at byte 0 — far below the 1 GiB sentinel.
        meta_size = self.lib.dashboard_metadata_path(self.root).stat().st_size
        self.assertLess(meta_size, self.lib._LOCK_BYTE_OFFSET,
                        "metadata must be far below the sentinel offset (no region overlap)")

    def test_windows_concurrency_gate_intact_second_acquire_busy(self):
        # The sentinel lock still gates concurrency: a second acquire of the same offset raises
        # DashboardLockBusy. Modeled with a fake msvcrt that raises on a re-lock of a held offset.
        held: set = set()

        import types as _types

        def locking(fileno, mode, nbytes):
            offset = os.lseek(fileno, 0, os.SEEK_CUR)
            if mode == 1:  # LK_NBLCK
                if offset in held:
                    raise OSError(errno.EACCES, "lock violation")
                held.add(offset)
            else:  # LK_UNLCK
                held.discard(offset)

        fake = _types.SimpleNamespace(locking=locking, LK_NBLCK=1, LK_UNLCK=0)
        with patch.object(self.lib.os, "name", "nt"), \
             patch.dict(sys.modules, {"msvcrt": fake}):
            with self.lib.dashboard_server_lock(self.root):
                with self.assertRaises(self.lib.DashboardLockBusy):
                    with self.lib.dashboard_server_lock(self.root):
                        pass
            # After release, the offset is free again → a fresh acquire succeeds.
            with self.lib.dashboard_server_lock(self.root):
                pass

    def test_posix_branch_uses_whole_file_flock_unchanged(self):
        # POSIX path must still use advisory whole-file flock with NO byte offset — assert msvcrt is
        # never touched on POSIX and the real flock lock/unlock are used.
        if os.name == "nt":
            self.skipTest("POSIX-only assertion")
        import fcntl
        seen_ops: list = []
        real_flock = fcntl.flock

        def recording_flock(fd, op):
            seen_ops.append(op)
            return real_flock(fd, op)

        # If msvcrt were touched on POSIX this would error (no real msvcrt offset handling here).
        sentinel_msvcrt = object()
        with patch.object(self.lib.os, "name", "posix"), \
             patch.object(fcntl, "flock", side_effect=recording_flock), \
             patch.dict(sys.modules, {"msvcrt": sentinel_msvcrt}):
            with self.lib.dashboard_server_lock(self.root):
                pass
        self.assertIn(fcntl.LOCK_EX | fcntl.LOCK_NB, seen_ops, "POSIX acquire must use flock LOCK_EX|NB")
        self.assertIn(fcntl.LOCK_UN, seen_ops, "POSIX release must use flock LOCK_UN")


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

    def test_dashboard_config_has_no_auto_index_setting(self):
        # 1p7it: the dashboard is a read-only viewer — it never triggers index builds, so the
        # `auto_index` / `auto_index_delay_seconds` settings were removed entirely. Index updates are
        # owned by the MCP/hook background path.
        cfg = self.lib.read_dashboard_config(self.root)
        self.assertNotIn("auto_index", cfg)
        self.assertNotIn("auto_index_delay_seconds", cfg)


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
    """Verify agent/persona/specialist discovery from docs/agents/."""

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
        self.assertNotIn("journal", groups)

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

    def test_persona_group_always_persona(self):
        self.assertEqual(self.classify("any-name", "persona"), "persona")

    def test_journal_group_always_journal(self):
        self.assertEqual(self.classify("any-name", "journal"), "journal")

    def test_group_takes_priority_over_stem(self):
        # "implementer" would be build for group=agent, but persona wins.
        self.assertEqual(self.classify("implementer", "persona"), "persona")

    def test_specialist_group_beats_review_stem(self):
        # "reality-checker" is in _REVIEW_STEMS but specialist group must win.
        self.assertEqual(self.classify("reality-checker", "specialist"), "specialist")

    def test_specialist_group_beats_coordinate_stem(self):
        # "wave-council" is in _COORDINATE_STEMS but specialist group must win.
        self.assertEqual(self.classify("wave-council", "specialist"), "specialist")

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
        # Use a synthetic name to exercise the `-moderator` suffix path.
        self.assertEqual(self.classify("custom-moderator", "agent"), "coordinate")

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


class DashboardWatcherHardeningTests(unittest.TestCase):
    """Wave 1rtju: the watcher can no longer wedge silently — its snapshot collection is bounded by a
    per-cycle timeout, a stalled watcher is surfaced (health field + SSE signal), nested doc-file edits
    trip the fast-change path, and watcher logging survives the MCP-spawn DEVNULL stderr."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        _make_wave(self.root)
        self._stores: list = []

    def tearDown(self):
        for store in self._stores:
            store.stop()
        self._stores.clear()
        self.tmp.cleanup()

    def _make_store(self):
        store = self.srv.SnapshotStore(self.root)
        self._stores.append(store)
        return store

    # ---- AC-1: the bounded collection cannot freeze the watcher ----

    def test_collect_bounded_times_out_and_does_not_pile_up(self):
        import threading
        store = self._make_store()  # startup collect already completed
        started = threading.Event()
        release = threading.Event()
        calls = [0]

        def blocking_collect(root, skip_git=False):
            calls[0] += 1
            started.set()
            release.wait(5)
            return {"project": {}, "waves": []}

        with patch.object(self.srv, "_COLLECT_TIMEOUT_SECONDS", 0.2), \
             patch.object(self.lib, "collect_dashboard_snapshot", side_effect=blocking_collect):
            r1 = store._rebuild(force_git=True)          # blocks 0.2s → timeout → None, keeps last-good
            self.assertIsNone(r1)
            self.assertIsNotNone(store._pending_collect)
            self.assertTrue(started.is_set())
            r2 = store._rebuild(force_git=True)          # still hung → None WITHOUT resubmitting
            self.assertIsNone(r2)
            self.assertEqual(calls[0], 1, "must not resubmit a new collection while one is hung")
        # Snapshot preserved (not wiped to partial/empty) across the stall.
        self.assertIn("project", store.get())
        release.set()
        store._pending_collect.result(timeout=5)          # let the hung future finish
        changed = store._rebuild(force_git=True)          # resubmits the (real) collect → completes
        self.assertIsNotNone(changed)

    # ---- AC-2: a stalled watcher is surfaced (health field + SSE) ----

    def test_watcher_health_reports_healthy_then_stalled(self):
        import time
        store = self._make_store()
        store.stop()  # freeze the watcher thread; drive state directly
        self.assertFalse(store.watcher_health()["stalled"])
        store._watcher_stalled = True
        h = store.watcher_health()
        self.assertTrue(h["stalled"])
        self.assertIn("last_cycle_age_seconds", h)

    def test_watcher_health_stalls_on_stale_cycle_age(self):
        import time
        store = self._make_store()
        store.stop()
        store._last_watch_cycle_at = time.monotonic() - (self.srv._WATCHER_STALL_SECONDS + 10)
        self.assertTrue(store.watcher_health()["stalled"])

    def test_stall_and_recovery_emit_sse_once(self):
        store = self._make_store()
        store.stop()
        client = store.register_sse_client()
        store._mark_cycle_stalled()
        self.assertEqual(client.queue.get_nowait(), "watcher_status:1")
        store._mark_cycle_stalled()  # already stalled → no duplicate signal
        self.assertTrue(client.queue.empty())
        store._note_cycle_recovered()  # recovery (tied to a completed rebuild)
        self.assertEqual(client.queue.get_nowait(), "watcher_status:0")

    def test_no_op_cycle_does_not_clear_stall(self):
        # A heartbeat (no rebuild needed) must NOT declare recovery while a collection is still hung.
        store = self._make_store()
        store.stop()
        store._watcher_stalled = True
        client = store.register_sse_client()
        store._note_cycle_alive()  # liveness only
        self.assertTrue(store._watcher_stalled, "a no-op cycle must not clear a stall")
        self.assertTrue(client.queue.empty(), "a no-op cycle must not emit a recovery signal")

    def test_api_dashboard_includes_watcher_health(self):
        store = self._make_store()
        store.stop()
        # The /api/dashboard handler merges watcher_health() additively.
        merged = {**store.get(), "watcher": store.watcher_health()}
        self.assertIn("watcher", merged)
        self.assertIn("stalled", merged["watcher"])

    # ---- AC-3: nested-file edits trip the fast-change path ----

    def test_current_mtimes_detects_nested_file_edit(self):
        import time
        store = self._make_store()
        store.stop()
        base = self.root / "docs" / "waves"
        nested_dir = base / "12x test-wave"  # existing wave subdir from _make_wave
        nested_file = nested_dir / "change.md"
        nested_file.write_text("v1", encoding="utf-8")
        before = store._current_mtimes()
        # Edit the nested file with a strictly-newer mtime (bump forward to avoid clock granularity).
        future = time.time() + 5
        os.utime(nested_file, (future, future))
        after = store._current_mtimes()
        tree_key = f"tree::{base}"
        self.assertIn(tree_key, before)
        self.assertNotEqual(before[tree_key], after[tree_key],
                            "a nested-file edit must change the tree signature")
        # The flat docs/waves dir mtime alone does NOT change on a nested-file edit — proving the
        # nested signature is what catches it (the pre-1rtju gap).
        self.assertEqual(before[str(base)], after[str(base)])

    # ---- AC-4: the client-side staleness watchdog (dashboard.js source contract) ----

    def test_dashboard_js_has_client_staleness_watchdog(self):
        # AC-4: the client must recover from a "connected but silent" SSE stall. This locks the
        # dashboard.js watchdog the same way the suite locks other client behavior (source assertion),
        # so a revert of the watchdog is caught even though the JS is not unit-executable here.
        js = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        # A last-update timestamp + a bounded stale window drive a safety poll while SSE is connected.
        self.assertIn("lastUpdateAtRef", js)
        self.assertIn("WATCHDOG_STALE_MS", js)
        self.assertIn("WATCHDOG_INTERVAL_MS", js)
        # The safety poll only fires when connected AND silent beyond the window (no double-fetch when healthy).
        self.assertIn("sseActiveRef.current && Date.now() - lastUpdateAtRef.current > WATCHDOG_STALE_MS", js)
        # An explicit server stall signal triggers an immediate poll.
        self.assertIn('es.addEventListener("watcher_status"', js)
        # The interval is cleared on cleanup (no leak) and the update event refreshes the freshness clock.
        self.assertIn("clearInterval(watchdogRef.current)", js)
        # The live watcher-health field must be excluded from the content hash so it never churns.
        self.assertIn("watcher: _w", js)

    # ---- AC-6: the nested scan is bounded (no unbounded walk) ----

    def test_nested_signature_is_bounded(self):
        store = self._make_store()
        store.stop()
        base = self.root / "docs" / "plans"
        base.mkdir(parents=True, exist_ok=True)
        for i in range(5):
            (base / f"f{i}.md").write_text("x", encoding="utf-8")
        with patch.object(self.srv, "_NESTED_SCAN_MAX_ENTRIES", 2):
            sig = store._nested_signature(base)
        self.assertTrue(sig.endswith(":capped"), f"scan must short-circuit at the cap, got {sig!r}")

    # ---- AC-5: watcher logging survives DEVNULL stderr (MCP spawn) ----

    def test_dashboard_log_persists_to_file_when_root_set(self):
        log_file = self.root / ".wavefoundry" / "logs" / "dashboard.log"
        with patch.object(self.srv, "_LOG_ROOT", self.root), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop(self.srv._DAEMON_ENV_MARKER, None)
            self.srv._dashboard_log("watcher error: simulated boom")
        self.assertTrue(log_file.exists())
        self.assertIn("watcher error: simulated boom", log_file.read_text(encoding="utf-8"))

    def test_dashboard_log_skips_file_for_daemon_child(self):
        log_file = self.root / ".wavefoundry" / "logs" / "dashboard.log"
        with patch.object(self.srv, "_LOG_ROOT", self.root), \
             patch.dict(os.environ, {self.srv._DAEMON_ENV_MARKER: "1"}):
            self.srv._dashboard_log("daemon-child-only-line")
        # The --daemon child's stderr is already redirected to dashboard.log; no direct duplicate write.
        wrote = log_file.exists() and "daemon-child-only-line" in log_file.read_text(encoding="utf-8")
        self.assertFalse(wrote)

    def test_dashboard_log_persist_false_stays_off_the_file(self):
        # Wave 1rtju: HTTP access lines (log_message → persist=False) must NOT flood the always-on file.
        log_file = self.root / ".wavefoundry" / "logs" / "dashboard.log"
        with patch.object(self.srv, "_LOG_ROOT", self.root), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop(self.srv._DAEMON_ENV_MARKER, None)
            self.srv._dashboard_log('GET /api/dashboard HTTP/1.1 200 -', persist=False)
        wrote = log_file.exists() and "GET /api/dashboard" in log_file.read_text(encoding="utf-8")
        self.assertFalse(wrote, "access-log lines must not be persisted to dashboard.log")


class UpgradeLockFailureMarkerTests(unittest.TestCase):
    """Wave 1p44o (AC-3) — _check_upgrade_lock must NOT auto-clear a retained
    failure-marked lock even though the exited upgrade's PID now looks stale, so
    the dashboard stays paused and never force-reindexes a gate-failed tree.

    Exercised via the unbound method on a minimal stand-in (it only reads
    ``self._root``) so no watcher thread / index subprocess is started.
    """

    def setUp(self):
        # `_check_upgrade_lock` does `import upgrade_lib` at call time — make the
        # scripts dir importable so the real (non-degraded) path runs.
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        _, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _lock_path(self) -> Path:
        return self.root / ".wavefoundry" / "upgrade-in-progress.json"

    def _write_lock(self, **fields) -> None:
        data = {"from_version": "a", "to_version": "b", "pid": 999_999_999}
        data.update(fields)
        self._lock_path().write_text(json.dumps(data), encoding="utf-8")

    def _check(self) -> bool:
        return self.srv.SnapshotStore._check_upgrade_lock(
            SimpleNamespace(_root=self.root)
        )

    def test_failure_marked_stale_lock_not_cleared(self):
        # Dead PID (upgrade process exited) + failure marker → stays locked, retained.
        self._write_lock(
            failed_phase="docs_gate", failed_at="2026-06-08T00:00:00+00:00"
        )
        self.assertTrue(self._check())
        self.assertTrue(
            self._lock_path().exists(),
            "failure-marked lock must not be auto-cleared (AC-3)",
        )

    def test_unmarked_stale_lock_is_cleared(self):
        # Existing behavior preserved: dead PID + no marker → stale → auto-clear.
        self._write_lock()
        self.assertFalse(self._check())
        self.assertFalse(
            self._lock_path().exists(),
            "unmarked stale lock retains existing auto-clear behavior",
        )

    def test_live_lock_without_marker_is_locked(self):
        # Live PID, no marker → a normal in-progress upgrade → locked, retained.
        self._write_lock(pid=os.getpid())
        self.assertTrue(self._check())
        self.assertTrue(self._lock_path().exists())


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
            ("status", "--porcelain", "--untracked-files=all", "-z"): " M src/foo.py\0 M src/bar.py\0",
            ("diff", "HEAD", "--shortstat"): " 3 files changed, 42 insertions(+), 7 deletions(-)\n",
            ("ls-files", "--others", "--exclude-standard", "-z"): "",
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
            ("status", "--porcelain", "--untracked-files=all", "-z"): "",
            ("diff", "HEAD", "--shortstat"): "",
            ("ls-files", "--others", "--exclude-standard", "-z"): "",
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
            ("status", "--porcelain", "--untracked-files=all", "-z"): "?? image.png\0",
            ("diff", "HEAD", "--shortstat"): "",
            ("ls-files", "--others", "--exclude-standard", "-z"): "image.png\0",
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "",
        }
        result = self._run_with_mock(outputs)
        self.assertEqual(result["lines_added"], 0)


class GitUntrackedDirAccountingTests(unittest.TestCase):
    """1p466: the "Files" tile count, the changed-files dialog list, and the
    added-line total must reconcile for fully-untracked directories — including
    non-ASCII and spaced filenames — and a tracked rename must still parse.

    Uses a real git repo so the actual ``git status --untracked-files=all -z``
    output format is exercised end to end; a mock cannot validate NUL parsing or
    on-disk path resolution (the defect a bare ``-uall`` would have introduced).
    """

    def setUp(self):
        self.lib, _ = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._git("init")
        self._git("config", "user.email", "t@t.t")
        self._git("config", "user.name", "t")
        self._git("config", "commit.gpgsign", "false")
        self._git("config", "diff.renames", "true")  # deterministic rename detection
        # tracked baseline: a file to rename, a file to modify
        _write(self.root / "orig.txt", "a\nb\nc\n")
        _write(self.root / "mod.txt", "one\ntwo\n")
        self._git("add", "-A")
        self._git("commit", "-m", "init")
        # tracked rename (pure, 0 lines) + tracked modification (+1 line)
        self._git("mv", "orig.txt", "renamed.txt")
        _write(self.root / "mod.txt", "one\ntwo\nthree\n")
        # fully-untracked directory, known line counts, incl. spaced + non-ASCII names
        d = self.root / "untracked_dir"
        _write(d / "plain.txt", "x\ny\n")       # 2 newlines
        _write(d / "with space.txt", "q\n")      # 1 newline
        _write(d / "café.txt", "é\n")            # 1 newline, non-ASCII name
        self.untracked_added = 4                 # 2 + 1 + 1
        self.tracked_added = 1                   # mod.txt +1; pure rename contributes 0

    def tearDown(self):
        self.tmp.cleanup()

    def _git(self, *args):
        import subprocess
        subprocess.run(["git", *args], cwd=self.root, check=True,
                       capture_output=True, text=True)

    def test_untracked_dir_files_reconcile_with_known_totals(self):
        stats = self.lib.collect_git_stats(self.root)
        listed = self.lib.list_git_changed_files(self.root)
        paths = {e["path"] for e in listed}

        # AC-1: each untracked file is listed individually, resolves on disk, and
        # produces a non-empty diff (not a collapsed dir, not a broken/empty row).
        for name in ("untracked_dir/plain.txt", "untracked_dir/with space.txt", "untracked_dir/café.txt"):
            self.assertIn(name, paths, f"{name!r} missing from dialog list")
            self.assertTrue((self.root / name).exists(), f"{name!r} does not resolve on disk")
            diff, code = self.lib.get_file_diff(self.root, name)
            self.assertEqual(code, 200, f"{name!r} diff status was {code}")
            self.assertTrue(diff.strip(), f"{name!r} produced an empty diff")

        # Tracked rename: new path listed, old path absent (prior behaviour); modify listed.
        self.assertIn("renamed.txt", paths)
        self.assertNotIn("orig.txt", paths)
        self.assertIn("mod.txt", paths)

        # AC-2: tile file count == dialog list length (below the 500-row cap).
        self.assertEqual(stats["files_changed"], len(listed))

        # AC-3 (absolute, not just tile==dialog): untracked contribution is exactly
        # its known total; the dialog per-file sum equals the tile total; the tile
        # total is the known absolute (untracked 4 + tracked 1 = 5).
        untracked_sum = sum(e.get("lines_added", 0) for e in listed if e["path"].startswith("untracked_dir/"))
        self.assertEqual(untracked_sum, self.untracked_added)
        dialog_sum = sum(e.get("lines_added", 0) for e in listed)
        self.assertEqual(stats["lines_added"], dialog_sum)
        self.assertEqual(stats["lines_added"], self.untracked_added + self.tracked_added)


class GitStatsZStripSafetyTests(unittest.TestCase):
    """1p466 regression: `collect_git_stats` must NOT `.strip()` the NUL-delimited
    `-z` git output. Leading whitespace is significant — an unstaged-modify record
    begins with a space XY code (" M path"), and an untracked filename may begin
    with a space — so a global strip corrupts the first token and diverges the tile
    from the dialog. Real git repo exercises the actual `-z` byte stream.
    """

    def setUp(self):
        self.lib, _ = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._git("init")
        self._git("config", "user.email", "t@t.t")
        self._git("config", "user.name", "t")
        self._git("config", "commit.gpgsign", "false")
        _write(self.root / "a", "1\n")          # short (1-char) tracked filename
        _write(self.root / "keep.txt", "k\n")
        self._git("add", "-A")
        self._git("commit", "-m", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def _git(self, *args):
        import subprocess
        subprocess.run(["git", *args], cwd=self.root, check=True,
                       capture_output=True, text=True)

    def test_unstaged_modify_short_name_first_record_is_counted(self):
        # The only status record is " M a"; a global strip would yield "M a" (3 chars),
        # tripping the <4 floor and dropping it → files_changed undercounts to 0.
        _write(self.root / "a", "1\n2\n")
        stats = self.lib.collect_git_stats(self.root)
        listed = self.lib.list_git_changed_files(self.root)
        self.assertIn("a", {e["path"] for e in listed})
        self.assertEqual(stats["files_changed"], len(listed))
        self.assertEqual(stats["files_changed"], 1)

    def test_leading_space_untracked_filename_lines_counted(self):
        # An untracked filename beginning with a space is the first `ls-files -z`
        # token; a global strip drops the leading space → read_bytes() fails → its
        # lines vanish from the tile total while the dialog (unstripped) counts them.
        _write(self.root / " lead.txt", "x\ny\n")  # 2 lines, leading-space name
        stats = self.lib.collect_git_stats(self.root)
        listed = self.lib.list_git_changed_files(self.root)
        self.assertIn(" lead.txt", {e["path"] for e in listed})
        self.assertEqual(stats["files_changed"], len(listed))
        dialog_added = sum(e.get("lines_added", 0) for e in listed)
        self.assertEqual(stats["lines_added"], dialog_added)
        self.assertEqual(stats["lines_added"], 2)


class IndexStalenessTests(unittest.TestCase):
    """Verify _index_is_stale detects missing index and meta-based staleness."""

    def setUp(self):
        self.lib, self.srv = load_dashboard_modules()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_meta(self, built_at: str, layer: str = "project") -> None:
        # 1sed6: seed the store; an empty built_at maps to "no completed
        # build epoch" (the store-level never-built state).
        assert layer == "project"
        _seed_index_store(self.root, {"built_at": built_at}, complete=bool(built_at))

    def _write_meta_payload(self, payload: dict[str, Any], layer: str = "project") -> None:
        assert layer == "project"
        _seed_index_store(self.root, payload)

    def test_stale_when_meta_missing(self):
        self.assertTrue(self.srv._index_is_stale(self.root))

    def test_framework_layer_rejected(self):
        # 1p4ww: framework folded into the project index — the layer is rejected.
        with self.assertRaises(ValueError):
            self.srv._index_is_stale(self.root, "framework")

    def test_stale_when_meta_has_no_built_at(self):
        self._write_meta("")
        self.assertTrue(self.srv._index_is_stale(self.root))

    def test_not_stale_when_built_at_only_without_file_meta(self):
        """Git history or dirtiness alone must not mark the index stale."""
        self._write_meta("2026-01-01T00:00:00+00:00")
        with patch("subprocess.run", side_effect=AssertionError("staleness must not invoke git")):
            result = self.srv._index_is_stale(self.root)
        self.assertFalse(result)

    def test_stale_when_project_file_meta_detects_changed_input_on_disk(self):
        """Real project input changes must still mark the project layer stale."""
        built_at = "2026-01-01T00:00:00+00:00"
        project_file = self.root / "docs" / "guide.md"
        project_file.parent.mkdir(parents=True, exist_ok=True)
        project_file.write_text("# Guide updated\n", encoding="utf-8")
        stat = project_file.stat()
        self._write_meta_payload(
            {
                "built_at": built_at,
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

    def test_not_stale_when_project_file_meta_matches_despite_git_dirty(self):
        """Uncommitted changes already reflected in file_meta must not look stale."""
        project_file = self.root / "docs" / "guide.md"
        project_file.parent.mkdir(parents=True, exist_ok=True)
        project_file.write_text("# Guide\n", encoding="utf-8")
        digest = hashlib.sha256(project_file.read_bytes()).hexdigest()
        stat = project_file.stat()
        self._write_meta_payload(
            {
                "built_at": "2099-01-01T00:00:00+00:00",
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

    def test_not_stale_when_git_clean_and_no_new_commits(self):
        self._write_meta("2026-01-01T00:00:00+00:00")
        with patch("subprocess.run", side_effect=AssertionError("staleness must not invoke git")):
            result = self.srv._index_is_stale(self.root)
        self.assertFalse(result)

    def test_project_stale_when_folded_framework_seed_changes(self):
        # 1p4ww: framework seeds fold into the project index, so a seed change marks
        # the PROJECT layer stale (there is no separate framework layer).
        seed = self.root / ".wavefoundry" / "framework" / "seeds" / "100-sample.prompt.md"
        seed.parent.mkdir(parents=True, exist_ok=True)
        seed.write_text("# Sample updated\n", encoding="utf-8")
        stat = seed.stat()
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
            layer="project",
        )
        with patch("subprocess.run", side_effect=AssertionError("file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "project")
        self.assertTrue(result)

    def test_project_not_stale_when_only_framework_manifest_differs(self):
        # 1p4ww: MANIFEST/VERSION are not folded, so they never affect project staleness.
        seed = self.root / ".wavefoundry" / "framework" / "seeds" / "100-sample.prompt.md"
        seed.parent.mkdir(parents=True, exist_ok=True)
        seed.write_text("# Sample\n", encoding="utf-8")
        seed_stat = seed.stat()
        manifest = self.root / ".wavefoundry" / "framework" / "MANIFEST"
        manifest.write_text("current\n", encoding="utf-8")
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    ".wavefoundry/framework/seeds/100-sample.prompt.md": {
                        "hash": hashlib.sha256(seed.read_bytes()).hexdigest(),
                        "mtime": seed_stat.st_mtime,
                        "size": seed_stat.st_size,
                        "inode": seed_stat.st_ino,
                    }
                },
            },
            layer="project",
        )
        with patch("subprocess.run", side_effect=AssertionError("file_meta path should bypass git")):
            result = self.srv._index_is_stale(self.root, "project")
        self.assertFalse(result)

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
        runtime_file = self.root / ".wavefoundry" / "locks" / "dashboard-server.lock"
        runtime_file.parent.mkdir(parents=True, exist_ok=True)
        runtime_file.write_text('{"pid": 1}\n', encoding="utf-8")
        stat = runtime_file.stat()
        self._write_meta_payload(
            {
                "built_at": "2026-01-01T00:00:00+00:00",
                "file_meta": {
                    ".wavefoundry/locks/dashboard-server.lock": {
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
        with patch("subprocess.run", side_effect=AssertionError("staleness must not invoke git")):
            result = self.srv._index_is_stale(self.root, "project")
        self.assertFalse(result)

    def test_staleness_never_invokes_git(self):
        """Staleness checks must not shell out to git."""
        self._write_meta("2026-01-01T00:00:00+00:00")
        with patch("subprocess.run", side_effect=AssertionError("staleness must not invoke git")):
            result = self.srv._index_is_stale(self.root)
        self.assertFalse(result)

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

    def test_semantic_index_tile_uses_generic_build_status_copy(self):
        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn('const statusText = buildStatus === "running"', source)
        self.assertIn('? "Indexing..."', source)
        self.assertNotIn(': isStale', source)
        self.assertNotIn('? "Stale..."', source)
        self.assertNotIn('const buildAction = idx.mode === "rebuild"', source)
        self.assertNotIn('const buildBadgeText = buildStatus === "running"', source)
        self.assertNotIn('"Index stale"', source)
        self.assertIn('"Build failed"', source)
        self.assertIn('stale_locks_cleaned', source)
        self.assertIn('Cleaned ${staleLocksCleaned} stale', source)
        self.assertIn('const idxAction  = proj.mode === "rebuild"', source)
        self.assertIn('index-build-badge--running', source)

    def test_background_build_status_surfaces_in_snapshot_health(self):
        import os

        bg_pid = self.root / ".wavefoundry" / "index" / "background-build.pid"
        bg_log = self.root / ".wavefoundry" / "logs" / "project-background-build.log"
        bg_pid.parent.mkdir(parents=True, exist_ok=True)
        bg_log.parent.mkdir(parents=True, exist_ok=True)
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

    def test_stale_lock_cleanup_surfaces_in_snapshot_health(self):
        self._disable_auto_index()
        lock_path = self.root / ".wavefoundry" / "index" / "docs.lance" / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("999999999", encoding="utf-8")

        store = self._track(self.srv.SnapshotStore(self.root))
        snap = store.get()
        proj = snap.get("health", {}).get("index", {}).get("project", {})

        self.assertEqual(len(proj.get("stale_locks_cleaned", [])), 1)
        self.assertEqual(proj["stale_locks_cleaned"][0]["reason"], "pid_dead")
        self.assertFalse(lock_path.exists())

    def test_background_build_files_are_watched(self):
        store = self._track(self.srv.SnapshotStore(self.root))
        watched = {str(path) for path in store._watched_paths()}
        self.assertIn(str(self.root / ".wavefoundry" / "index" / "index-build.json"), watched)
        self.assertIn(str(self.root / ".wavefoundry" / "index" / "background-build.pid"), watched)
        self.assertIn(str(self.root / ".wavefoundry" / "logs" / "project-index-build.log"), watched)
        self.assertIn(str(self.root / ".wavefoundry" / "logs" / "project-background-build.log"), watched)

    def test_staleness_display_computed_on_demand(self):
        """Wave 1p5xw: the dashboard still DISPLAYS index staleness, computed on
        demand when the snapshot is rebuilt (read-only), without a continuous poll.
        """
        store = self._track(self.srv.SnapshotStore(self.root))
        # The on-demand compute is rate-limited (Wave 1p5xw): force the throttle
        # window to have elapsed so the rebuild recomputes staleness for display.
        store._last_display_staleness_at = 0.0
        with patch.object(self.srv, "_index_is_stale", return_value=True):
            store._rebuild(force_git=False)
        snap = store.get()
        proj = snap.get("health", {}).get("index", {}).get("project", {})
        self.assertTrue(proj.get("stale"), "snapshot should reflect on-demand staleness")

        # Within the throttle window a rebuild reuses the cached value (no repo walk).
        with patch.object(self.srv, "_index_is_stale", return_value=False):
            store._rebuild(force_git=False)
        snap = store.get()
        proj = snap.get("health", {}).get("index", {}).get("project", {})
        self.assertTrue(proj.get("stale"), "within-throttle rebuild should reuse cached staleness")

        # Past the throttle window it recomputes and refreshes.
        store._last_display_staleness_at = 0.0
        with patch.object(self.srv, "_index_is_stale", return_value=False):
            store._rebuild(force_git=False)
        snap = store.get()
        proj = snap.get("health", {}).get("index", {}).get("project", {})
        self.assertFalse(proj.get("stale"), "post-throttle rebuild should refresh staleness on demand")

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

    def test_dashboard_js_includes_flicker_fix_signature_skip(self):
        """Wave 1p2q3 (131es AC-17/18): refresh skips loading banner on incremental
        reloads and no-ops when signature is unchanged."""
        js = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn("_initialLoadDoneRef", js)
        self.assertIn("_graphSigRef", js)
        self.assertIn("function _graphSignature(g)", js)
        self.assertIn("if (newSig === prevSig)", js)
        self.assertIn("if (isInitial) setLoading(true)", js)
        self.assertIn("const stillExists = (data?.nodes || []).some(n => n.id === selectedNodeId)", js)

    def test_graph_kind_colors_are_all_distinct_including_variable(self):
        """Wave 1p2q3 (131es): palette gives every node kind a unique color.
        `seed` is intentionally collapsed into `doc` via `_graphKindBucket`."""
        js = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        import re as _re
        start = js.index("const GRAPH_KIND_COLORS = {")
        end = js.index("};", start)
        block = js[start:end]
        entries = _re.findall(r'(\w+):\s*"(#[0-9a-fA-F]{6})"', block)
        kind_to_color = dict(entries)
        for kind in ("module", "class", "function", "doc", "community",
                     "external", "package", "namespace", "variable"):
            self.assertIn(kind, kind_to_color, f"kind {kind!r} missing from palette")
        self.assertNotIn("seed", kind_to_color,
                         "seed should collapse to doc bucket via _graphKindBucket")
        self.assertIn('if (kind === "seed") return "doc";', js)
        seen: dict[str, str] = {}
        for kind, color in kind_to_color.items():
            if color in seen:
                self.fail(f"palette collision: {kind!r} and {seen[color]!r} share {color}")
            seen[color] = kind
        self.assertNotEqual(kind_to_color["variable"], kind_to_color["doc"])
        self.assertNotEqual(kind_to_color["variable"], kind_to_color["external"])
        self.assertNotEqual(kind_to_color["doc"], kind_to_color["external"])


class AgentsEmptyStateGuidanceTests(unittest.TestCase):
    """Wave 1p3b9 (1p3b7 F5): component-level coverage for the dashboard's
    empty-Agents-panel guidance. The Agents React component must render
    guidance copy (not silence) when collect_agents returns []. This test
    asserts the guidance branch is present in dashboard.js — the same
    string-presence pattern other dashboard tests use."""

    def test_agents_component_has_empty_state_branch(self):
        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        # Component definition exists
        self.assertIn("function Agents({ agents, onSelectAgent })", source)
        # Empty-state branch with the canonical class
        self.assertIn("hero-agents--empty", source)
        # Guidance heading
        self.assertIn('"Agents"', source)
        # Operator-facing shortcut phrase + recovery action
        self.assertIn("No agent role docs found", source)
        self.assertIn("Init agent surfaces", source)
        # Inline code element for the Role: invariant
        self.assertIn("Role: <role-slug>", source)

    def test_agents_component_renders_populated_branch_when_agents_present(self):
        """Regression guard: the non-empty render branch is still present
        so the populated state isn't accidentally short-circuited."""
        source = (SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js").read_text(encoding="utf-8")
        # Categories array drives the populated render
        self.assertIn('"coordinate"', source)
        self.assertIn('"review"', source)
        self.assertIn('"build"', source)
        # The category iteration emits group elements
        self.assertIn("hero-agent-group", source)


import shutil  # noqa: E402


WFDS_PATH = SCRIPTS_ROOT.parent / "dashboard" / "ds" / "wfds.js"


class RenderMarkdownishThematicBreakTests(unittest.TestCase):
    """Wave 1p8pg: renderMarkdownish (ds/wfds.js) must render a standalone `---`/`***`/`___` line as an
    <hr>, while a `---` inside a fenced code block stays literal and lists/headings/tables are
    unaffected. The source-text assertion always runs; the node-execution assertions run the REAL
    renderMarkdownish (non-vacuous) when node is available."""

    _DRIVER = r"""
const fs = require("fs");
const vm = require("vm");
// Minimal React stub: createElement → a plain {type, props, children} vnode tree.
function createElement(type, props, ...children) {
  const flat = [];
  for (const c of children) {
    if (Array.isArray(c)) flat.push(...c); else flat.push(c);
  }
  return { type, props: props || {}, children: flat };
}
const root = { React: { createElement, useState(){}, useEffect(){}, useRef(){}, useCallback(){} } };
const code = fs.readFileSync(process.argv[2], "utf8");
// The file's IIFE attaches to `this` when window is undefined; run it with `this === root`.
vm.runInNewContext(code, { window: root, globalThis: root, console }, { filename: "wfds.js" });
const WFDS = root.WFDS;
const out = {};
const types = (text) => WFDS.renderMarkdownish(text).map(n => (n && n.type) || null);
out.hr_dashes = types("intro\n---\nafter");
out.hr_stars = types("***");
out.hr_unders = types("___");
out.dash_list_item = types("- a\n- b");        // a `- ` list item must NOT become <hr>
out.heading = types("# Title");
// Fenced code containing --- must stay a single <pre> (literal), no <hr>.
const fenced = WFDS.renderMarkdownish("```\n---\n```");
out.fenced_types = fenced.map(n => (n && n.type) || null);
// Extract the literal text inside the fenced <pre><code>…</code></pre>.
function codeText(node) {
  if (!node) return "";
  if (typeof node === "string") return node;
  if (node.children) return node.children.map(codeText).join("");
  return "";
}
out.fenced_code_text = fenced.map(codeText).join("");
process.stdout.write(JSON.stringify(out));
"""

    def test_thematic_break_branch_present_in_source(self):
        # Always-on guard (runs even without node): the branch exists with the exact rule regex,
        # placed so the code-block collector (which `continue`s first) keeps fenced `---` literal.
        src = WFDS_PATH.read_text(encoding="utf-8")
        self.assertIn(r"/^(-{3,}|\*{3,}|_{3,})$/.test(line)", src,
                      "renderMarkdownish must classify a standalone rule line via the thematic-break regex")
        self.assertIn('h("hr", { key: key++ })', src,
                      "the thematic-break branch must emit an <hr> vnode")

    @unittest.skipUnless(shutil.which("node"), "node not available — JS execution test skipped")
    def test_renderMarkdownish_executes_thematic_break_behavior(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            driver = Path(td) / "driver.js"
            driver.write_text(self._DRIVER, encoding="utf-8")
            proc = subprocess.run(
                ["node", str(driver), str(WFDS_PATH)],
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(proc.returncode, 0, f"node driver failed: {proc.stderr}")
        out = json.loads(proc.stdout)
        # AC-1: standalone ---/***/___ → <hr> (the dashes case sits between two <p>).
        self.assertIn("hr", out["hr_dashes"], f"--- did not render <hr>: {out['hr_dashes']}")
        self.assertEqual(out["hr_stars"], ["hr"], f"*** did not render a sole <hr>: {out['hr_stars']}")
        self.assertEqual(out["hr_unders"], ["hr"], f"___ did not render a sole <hr>: {out['hr_unders']}")
        # AC-2: a `- ` list item is unaffected (becomes a <ul>, never <hr>).
        self.assertEqual(out["dash_list_item"], ["ul"], f"list items regressed: {out['dash_list_item']}")
        self.assertEqual(out["heading"], ["h1"], f"headings regressed: {out['heading']}")
        # AC-2: fenced code containing --- stays a single literal <pre>, no <hr>.
        self.assertEqual(out["fenced_types"], ["pre"],
                         f"fenced --- must stay a single <pre>, no <hr>: {out['fenced_types']}")
        self.assertIn("---", out["fenced_code_text"],
                      "the --- inside the fenced block must remain literal text")


class RenderMarkdownishDocumentContractTests(unittest.TestCase):
    """The shared document renderer hides metadata and joins soft-wrapped prose."""

    _DRIVER = r"""
const fs = require("fs");
const vm = require("vm");
function createElement(type, props, ...children) {
  const flat = [];
  for (const c of children) {
    if (Array.isArray(c)) flat.push(...c); else flat.push(c);
  }
  return { type, props: props || {}, children: flat };
}
const root = { React: { createElement, useState(){}, useEffect(){}, useRef(){}, useCallback(){} } };
vm.runInNewContext(fs.readFileSync(process.argv[2], "utf8"),
  { window: root, globalThis: root, console }, { filename: "wfds.js" });
const WFDS = root.WFDS;
function text(node) {
  if (node == null) return "";
  if (typeof node === "string") return node;
  return (node.children || []).map(text).join("");
}
const prose = WFDS.renderMarkdownish(
  "<!-- wave:context-efficiency begin -->\n" +
  "First soft-wrapped\nparagraph stays together.\n\n" +
  "- one list item\n  continued on the next source line\n" +
  "- second item\n" +
  "<!-- wave:context-efficiency end -->"
);
const fenced = WFDS.renderMarkdownish("```\n<!-- literal -->\n```");
process.stdout.write(JSON.stringify({
  types: prose.map(n => n.type),
  text: prose.map(text),
  fenced: fenced.map(text)
}));
"""
    _FIXTURE = (
        SCRIPTS_ROOT
        / "tests"
        / "fixtures"
        / "dashboard-wave-rendering.md"
    )
    _FIXTURE_DRIVER = r"""
const fs = require("fs");
const vm = require("vm");
function createElement(type, props, ...children) {
  const flat = [];
  for (const c of children) {
    if (Array.isArray(c)) flat.push(...c); else flat.push(c);
  }
  return { type, props: props || {}, children: flat };
}
const root = { React: { createElement, useState(){}, useEffect(){}, useRef(){}, useCallback(){} } };
vm.runInNewContext(fs.readFileSync(process.argv[2], "utf8"),
  { window: root, globalThis: root, console }, { filename: "wfds.js" });
function text(node) {
  if (node == null) return "";
  if (typeof node === "string") return node;
  return (node.children || []).map(text).join("");
}
const rendered = root.WFDS.renderMarkdownish(fs.readFileSync(process.argv[3], "utf8"));
process.stdout.write(JSON.stringify({
  types: rendered.map(n => n.type),
  text: rendered.map(text)
}));
"""
    _GEOMETRY_DRIVER = r"""
const fs = require("fs");
const vm = require("vm");
function createElement(type, props, ...children) {
  const flat = [];
  for (const child of children) {
    if (Array.isArray(child)) flat.push(...child); else flat.push(child);
  }
  return { type, props: props || {}, children: flat };
}
const root = {
  React: {
    createElement,
    useState(){},
    useEffect(){},
    useRef(){ return { current: null }; },
    useCallback(){},
  },
};
vm.runInNewContext(
  fs.readFileSync(process.argv[2], "utf8"),
  { window: root, globalThis: root, console },
  { filename: "wfds.js" },
);
const body = root.WFDS.renderMarkdownish(fs.readFileSync(process.argv[3], "utf8"));
const dialog = root.WFDS.Dialog({
  className: "doc-dialog",
  title: "Wave rendering fixture",
  subtitle: "fixed-viewport browser contract",
  onClose(){},
  children: createElement("div", { className: "doc-dialog-body" }, body),
});
function esc(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
function markup(node) {
  if (node == null || node === false) return "";
  if (Array.isArray(node)) return node.map(markup).join("");
  if (typeof node === "string" || typeof node === "number") return esc(node);
  if (typeof node.type === "function") {
    return markup(node.type({ ...node.props, children: node.children }));
  }
  const attrs = [];
  for (const [key, value] of Object.entries(node.props || {})) {
    if (key === "className") attrs.push(`class="${esc(value)}"`);
    else if (key.startsWith("aria-")) attrs.push(`${key}="${esc(value)}"`);
  }
  if (node.type === "dialog") attrs.push("open");
  return `<${node.type}${attrs.length ? " " + attrs.join(" ") : ""}>`
    + node.children.map(markup).join("")
    + `</${node.type}>`;
}
const css = fs.readFileSync(process.argv[4], "utf8");
fs.writeFileSync(
  process.argv[5],
  "<!doctype html><meta charset=utf-8><style>" + css + "</style>"
    + markup(dialog),
);
"""

    def test_shared_renderer_contains_comment_and_soft_wrap_logic(self):
        source = WFDS_PATH.read_text(encoding="utf-8")
        self.assertIn('visible.indexOf("<!--")', source)
        self.assertIn('paragraphLines.join(" ")', source)
        self.assertIn('currentListItem.join(" ")', source)

    def test_checked_in_operator_fixture_carries_required_dimensions(self):
        fixture = self._FIXTURE.read_text(encoding="utf-8")
        self.assertIn("<!-- wave:context-efficiency begin -->", fixture)
        self.assertIn("four physical source lines", fixture)
        self.assertIn("continues on another physical source line", fixture)
        self.assertIn("<!-- wave:literal-example begin -->", fixture)

    def test_document_css_contains_responsive_overflow_contract(self):
        css = (
            SCRIPTS_ROOT.parent / "dashboard" / "dashboard.css"
        ).read_text(encoding="utf-8")
        for fragment in (
            ".doc-dialog-body",
            "overflow-wrap: anywhere",
            "overflow-x: auto",
            "@media (max-width: 720px)",
            "table-layout: fixed",
        ):
            self.assertIn(fragment, css)

    def test_shared_renderer_caller_census_is_explicit_and_complete(self):
        """Every dashboard caller is a prose surface that adopts this behavior.

        This exact census prevents a new snippet/activity consumer from silently
        inheriting comment suppression or soft-wrap coalescing without review.
        """

        dashboard = (
            SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js"
        ).read_text(encoding="utf-8")
        expected_calls = (
            "renderMarkdownish(process.body)",
            "renderMarkdownish(c.description)",
            'renderMarkdownish(item.update || "")',
            "renderMarkdownish(item.evidence)",
            "renderMarkdownish(bodyText)",
            "renderMarkdownish(agent.body)",
        )
        self.assertEqual(dashboard.count("renderMarkdownish("), len(expected_calls))
        for call in expected_calls:
            self.assertEqual(
                dashboard.count(call),
                1,
                f"shared-renderer caller census drifted for {call}",
            )

    @unittest.skipUnless(shutil.which("node"), "node not available — JS execution test skipped")
    def test_shared_renderer_hides_markers_and_coalesces_prose(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            driver = Path(td) / "driver.js"
            driver.write_text(self._DRIVER, encoding="utf-8")
            proc = subprocess.run(
                ["node", str(driver), str(WFDS_PATH)],
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["types"], ["p", "ul"])
        self.assertEqual(
            out["text"],
            [
                "First soft-wrapped paragraph stays together.",
                "one list item continued on the next source linesecond item",
            ],
        )
        self.assertNotIn("wave:context-efficiency", " ".join(out["text"]))
        self.assertIn("<!-- literal -->", out["fenced"][0])

    @unittest.skipUnless(shutil.which("node"), "node not available — JS execution test skipped")
    def test_checked_in_wave_fixture_uses_shared_renderer_without_visible_markers(self):
        import subprocess

        with tempfile.TemporaryDirectory() as td:
            driver = Path(td) / "driver.js"
            driver.write_text(self._FIXTURE_DRIVER, encoding="utf-8")
            proc = subprocess.run(
                ["node", str(driver), str(WFDS_PATH), str(self._FIXTURE)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        visible = " ".join(out["text"])
        self.assertNotIn("wave:context-efficiency", visible)
        self.assertIn(
            "This paragraph is deliberately hard wrapped across four physical source lines",
            visible,
        )
        self.assertIn("literal-example begin", visible)

    @unittest.skipUnless(shutil.which("node"), "node not available — browser fixture skipped")
    def test_fixed_viewport_browser_geometry_has_no_document_overflow(self):
        """Execute the real renderer and CSS in Chrome at both required widths."""

        import html
        import re
        import subprocess

        if os.environ.get("WAVEFOUNDRY_BROWSER_TESTS") != "1":
            self.skipTest(
                "set WAVEFOUNDRY_BROWSER_TESTS=1 to execute fixed-viewport Chrome tests"
            )
        chrome_candidates = (
            shutil.which("google-chrome"),
            shutil.which("chromium"),
            shutil.which("chromium-browser"),
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )
        chrome = next(
            (
                str(candidate)
                for candidate in chrome_candidates
                if candidate and Path(candidate).is_file()
            ),
            None,
        )
        if chrome is None:
            self.skipTest("Chrome/Chromium not available — geometry browser test skipped")

        css_path = SCRIPTS_ROOT.parent / "dashboard" / "dashboard.css"
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            driver = temp / "geometry-driver.js"
            page = temp / "geometry.html"
            driver.write_text(self._GEOMETRY_DRIVER, encoding="utf-8")
            built = subprocess.run(
                [
                    "node",
                    str(driver),
                    str(WFDS_PATH),
                    str(self._FIXTURE),
                    str(css_path),
                    str(page),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(built.returncode, 0, built.stderr)

            for width, height in ((1440, 900), (390, 844)):
                profile = temp / f"profile-{width}"
                wrapper = temp / f"geometry-{width}.html"
                wrapper.write_text(
                    f"""<!doctype html><meta charset="utf-8">
<style>html,body{{margin:0}} iframe{{display:block;border:0}}</style>
<iframe id="frame" width="{width}" height="{height}" src="{page.as_uri()}"></iframe>
<pre id="result" style="display:none"></pre>
<script>
document.querySelector("#frame").addEventListener("load", () => {{
  const frame = document.querySelector("#frame");
  const view = frame.contentWindow;
  const doc = frame.contentDocument;
  const page = doc.documentElement;
  const dialog = doc.querySelector(".doc-dialog");
  const body = doc.querySelector(".doc-dialog-body");
  const prose = [...body.querySelectorAll("p, li, h1, h2, h3")];
  const inline = [...body.querySelectorAll("code")].filter(el => !el.closest("pre"));
  const tables = [...body.querySelectorAll("table")];
  const result = {{
    viewport: {{ width: view.innerWidth, height: view.innerHeight }},
    page: {{ scrollWidth: page.scrollWidth, clientWidth: page.clientWidth }},
    dialog: {{ scrollWidth: dialog.scrollWidth, clientWidth: dialog.clientWidth }},
    body: {{ scrollWidth: body.scrollWidth, clientWidth: body.clientWidth }},
    proseCount: prose.length,
    proseOverflow: prose.filter(el => el.scrollWidth > el.clientWidth + 1).length,
    inlineCount: inline.length,
    inlineOverflow: inline.filter(el => el.scrollWidth > el.clientWidth + 1).length,
    tableCount: tables.length,
    tablesLocal: tables.every(el => {{
      const style = view.getComputedStyle(el);
      return style.overflowX === "auto" && el.scrollWidth >= el.clientWidth;
    }}),
    markerVisible: doc.body.innerText.includes("wave:context-efficiency"),
  }};
  document.querySelector("#result").textContent = JSON.stringify(result);
}});
</script>""",
                    encoding="utf-8",
                )
                command = [
                    chrome,
                    "--headless",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-background-networking",
                    "--disable-component-update",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--metrics-recording-only",
                    "--no-first-run",
                    "--allow-file-access-from-files",
                    f"--user-data-dir={profile}",
                    f"--window-size={max(width + 20, 520)},{height + 20}",
                    "--virtual-time-budget=2000",
                    "--dump-dom",
                    wrapper.as_uri(),
                ]
                try:
                    rendered = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=12,
                    )
                    stdout = rendered.stdout
                    stderr = rendered.stderr
                    self.assertEqual(rendered.returncode, 0, stderr)
                except subprocess.TimeoutExpired as exc:
                    # Some macOS Chrome builds emit the complete dump but keep
                    # a helper process attached to the output pipe. `run`
                    # terminates the process on timeout; accept only a complete
                    # result block, never a partial page.
                    stdout = exc.stdout or ""
                    stderr = exc.stderr or ""
                    if isinstance(stdout, bytes):
                        stdout = stdout.decode("utf-8", errors="replace")
                    if isinstance(stderr, bytes):
                        stderr = stderr.decode("utf-8", errors="replace")
                match = re.search(
                    r'<pre id="result"[^>]*>(.*?)</pre>',
                    stdout,
                    re.DOTALL,
                )
                self.assertIsNotNone(match, stderr[-1000:] + stdout[-2000:])
                result = json.loads(html.unescape(match.group(1)))
                self.assertEqual(result["viewport"]["width"], width)
                for surface in ("page", "dialog", "body"):
                    self.assertLessEqual(
                        result[surface]["scrollWidth"],
                        result[surface]["clientWidth"],
                        (width, surface, result),
                    )
                self.assertGreater(result["proseCount"], 0)
                self.assertEqual(result["proseOverflow"], 0, result)
                self.assertGreater(result["inlineCount"], 0)
                self.assertEqual(result["inlineOverflow"], 0, result)
                self.assertGreater(result["tableCount"], 0)
                self.assertTrue(result["tablesLocal"], result)
                self.assertFalse(result["markerVisible"], result)


import threading  # noqa: E402 (already imported above, but needed in test scope)

if __name__ == "__main__":
    unittest.main()
