"""Shared literal-checkbox Progress semantics (wave 2347r)."""
from __future__ import annotations

import copy
import inspect
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import dashboard_lib as dashboard


def item(mark="", priority="required"):
    return {"checkbox_mark": mark, "done": mark == "x", "deferred": mark == "~", "priority": priority}


def change(wave, *, status="planned", acs=(), tasks=()):
    return {"wave_id": wave, "status": status, "ac_items": list(acs),
            "tasks_items": list(tasks), "tasks_total": len(tasks),
            "tasks_completed": sum(i["done"] for i in tasks)}


def progress_fixture(open_waves=True):
    waves = [{"wave_id": "closed", "status": "ClOsEd", "change_count": 2},
             {"wave_id": "planned", "status": "planned", "change_count": 1}]
    changes = {"wave": [
        change("closed", acs=[item(), item("~"), item(priority="not-this-scope")], tasks=[item()]),
        change("planned", acs=[item(), item("x")], tasks=[item(), item("x")]),
    ], "plan": [change(None, acs=[item("x"), item()], tasks=[item("~")]),
                change("closed", acs=[item()], tasks=[item(), item()])]}
    if open_waves:
        waves += [{"wave_id": "completed", "status": "completed", "change_count": 1},
                  {"wave_id": "paused", "status": "paused", "change_count": 2},
                  {"wave_id": "open-a", "status": "IMPLEMENTING", "change_count": 1},
                  {"wave_id": "open-b", "status": "active", "change_count": 1}]
        changes["wave"] += [
            change("completed", acs=[item()], tasks=[item(), item()]),
            change("paused", acs=[item("~")], tasks=[item("~"), item("x")]),
            {**change("paused"), "read_error": "unreadable"},
            change("open-a", status="IMPLEMENTED", acs=[item("x"), item("~"), item()], tasks=[item("x"), item("~"), item()]),
            change("open-b", acs=[item("x"), item()], tasks=[item("x"), item()]),
        ]
    return waves, changes


def expected_checklists(open_waves=True):
    return {
        "criteria": {"done": 3, "deferred": 3, "open": 5, "total": 11, "not_this_scope": 1},
        "tasks": {"done": 4, "deferred": 2, "open": 6, "total": 12},
    } if open_waves else {
        "criteria": {"done": 1, "deferred": 1, "open": 2, "total": 4, "not_this_scope": 1},
        "tasks": {"done": 1, "deferred": 0, "open": 2, "total": 3},
    }


class SharedProgressTests(unittest.TestCase):
    def assertChecklists(self, result, opens=True):
        for group, expected in expected_checklists(opens).items():
            self.assertEqual(result[group], expected)
            self.assertEqual(result[group]["total"], sum(result[group][k] for k in ("done", "deferred", "open")))

    def test_all_admitted_statuses_and_missing_unreadable_documents(self):
        waves, changes = progress_fixture()
        before = copy.deepcopy((waves, changes))
        result = dashboard.collect_progress(waves, changes)
        self.assertChecklists(result)
        self.assertEqual(result["waves"], {"done": 2, "total": 6})
        self.assertEqual(result["changes"], {"done": 4, "total": 8})
        self.assertEqual(result["coverage"], {
            "complete": False, "missing_admitted_documents": 1, "unreadable_change_documents": 1,
            "warning": "Checklist coverage is incomplete; counts include only readable admitted documents.",
        })
        self.assertEqual((waves, changes), before)

    def test_no_open_wave_still_excludes_unadmitted_plans(self):
        waves, changes = progress_fixture(False)
        result = dashboard.collect_progress(waves, changes)
        self.assertChecklists(result, False)
        self.assertEqual(result["waves"], {"done": 1, "total": 2})
        self.assertEqual(result["changes"], {"done": 2, "total": 3})
        self.assertEqual(dashboard.collect_checklist_counts(changes["plan"]), {
            "criteria": {"done": 1, "deferred": 0, "open": 2, "total": 3, "not_this_scope": 0},
            "tasks": {"done": 0, "deferred": 1, "open": 2, "total": 3},
        })

    def test_status_changes_never_change_checkbox_scope_or_markers(self):
        waves, changes = progress_fixture()
        before = dashboard.collect_progress(waves, changes)
        for wave in waves:
            wave["status"] = "completed"
        for row in changes["wave"]:
            row["status"] = "completed"
        after = dashboard.collect_progress(waves, changes)
        for group in ("criteria", "tasks", "coverage"):
            self.assertEqual(before[group], after[group])
        self.assertChecklists(after)

    def test_terminal_markdown_preserves_markers_without_changing_legacy_cards(self):
        acs = dashboard._parse_ac_items("- [ ] AC-1: open\n- [~] AC-2: completed but deferred\n- [x] AC-3: done\n", "", "completed")
        tasks = dashboard._parse_tasks("- [ ] open\n- [~] completed but deferred\n- [x] done\n", "completed")
        for items in (acs, tasks["items"]):
            self.assertEqual([i["checkbox_mark"] for i in items], ["", "~", "x"])
            self.assertEqual([i["done"] for i in items], [True, False, True])
        result = dashboard.collect_checklist_counts([change("closed", status="completed", acs=acs, tasks=tasks["items"])])
        for group in ("criteria", "tasks"):
            self.assertEqual({k: result[group][k] for k in ("done", "deferred", "open", "total")}, {"done": 1, "deferred": 1, "open": 1, "total": 3})
        self.assertEqual(tasks["completed"], 2)

    def test_missing_marker_does_not_infer_done_and_unreadable_records_are_not_counted(self):
        result = dashboard.collect_checklist_counts([
            change("closed", status="completed", acs=[{"done": True}], tasks=[{"done": True}]),
            {**change("closed", acs=[item("x")], tasks=[item("x")]), "read_error": "unreadable"},
        ])
        for group in ("criteria", "tasks"):
            self.assertEqual(result[group]["done"], 0)
            self.assertEqual(result[group]["open"], 1)
            self.assertEqual(result[group]["total"], 1)

    def test_empty(self):
        result = dashboard.collect_progress([], {"wave": [], "plan": []})
        self.assertEqual(result["waves"], {"done": 0, "total": 0})
        self.assertEqual(result["changes"], {"done": 0, "total": 0})
        for group in ("criteria", "tasks"):
            self.assertEqual({k: result[group][k] for k in ("done", "deferred", "open", "total")}, dict.fromkeys(("done", "deferred", "open", "total"), 0))
        self.assertTrue(result["coverage"]["complete"])
        self.assertIsNone(result["coverage"]["warning"])

    def test_snapshot_uses_shared_function(self):
        sentinel = {"waves": {"done": 7, "total": 11}}
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(dashboard, "collect_progress", return_value=sentinel) as progress, \
                patch.object(dashboard, "collect_health", return_value={}), \
                patch.object(dashboard, "collect_activity", return_value={}), \
                patch.object(dashboard, "collect_git_stats", return_value={}):
            snapshot = dashboard.collect_dashboard_snapshot(Path(tmp))
        self.assertIs(snapshot["progress"], sentinel)
        self.assertEqual(progress.call_args.args, (snapshot["waves"], {"wave": snapshot["changes"]["in_waves"], "plan": snapshot["changes"]["staged"]}))

    def test_known_bad_variants_fail_exact_count_contract(self):
        # Compile local variants without editing source or replacing production tests.
        counts_source = inspect.getsource(dashboard.collect_checklist_counts)
        progress_source = inspect.getsource(dashboard.collect_progress)
        variants = {
            "closed completion credit": (counts_source.replace('mark = item.get("checkbox_mark")', 'mark = "x" if change.get("wave_id") == "closed" else item.get("checkbox_mark")'), progress_source),
            "omit planned with open wave": (counts_source, progress_source.replace('counts = collect_checklist_counts(in_waves)', 'counts = collect_checklist_counts([c for c in in_waves if c.get("wave_id") != "planned"])')),
            "include plan via Wave metadata": (counts_source, progress_source.replace('in_waves = change_sets.get("wave", [])', 'in_waves = change_sets.get("wave", []) + [c for c in change_sets.get("plan", []) if c.get("wave_id")]')),
            "invent missing checkbox completion": (counts_source, progress_source.replace('unreadable = sum(', 'counts["criteria"]["done"] += missing\n    counts["criteria"]["total"] += missing\n    unreadable = sum(')),
            "drop deferred from total": (counts_source.replace('counts[group]["total"] += 1', 'counts[group]["total"] += int(state != "deferred")'), progress_source),
        }
        for name, (counts, progress) in variants.items():
            with self.subTest(name=name):
                self.assertNotEqual((counts, progress), (counts_source, progress_source))
                namespace = dict(dashboard.__dict__)
                exec(compile(counts + "\n" + progress, "<progress-negative-control>", "exec"), namespace)
                with self.assertRaises(AssertionError):
                    self.assertChecklists(namespace["collect_progress"](*progress_fixture()))


if __name__ == "__main__":
    unittest.main()
