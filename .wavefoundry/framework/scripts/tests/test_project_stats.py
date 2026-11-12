"""Project report contracts, exact fixture counts and read-only failure cases."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
for directory in (SCRIPTS, Path(__file__).resolve().parent):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
import project_stats as stats
import dashboard_lib as dashboard
import vocabulary_profile as vp
import record_paths


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(value if isinstance(value, bytes) else value.encode())
    return target


def tree_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def wave(root, ident, status="planned", members=()):
    path = f"{record_paths.WAVES_ROOT}/{ident}/{vp.RECORD_FILENAME}"
    body = f"{vp.RECORD_TITLE}\n\n{vp.ID_KEY}: `{ident}`\nStatus: {status}\n\n{vp.MEMBER_HEADING}\n\n"
    body += '\n'.join(f"{vp.MEMBER_ID_LABEL}: `{name}`\n{vp.MEMBER_STATUS_LABEL}: `planned`\n" for name in members)
    return write(root, path, body)


def change(root, ident, wave_id=None, body=""):
    path = f"{record_paths.WAVES_ROOT}/{wave_id}/{ident}.md" if wave_id else f"{record_paths.PLANS_ROOT}/{ident}.md"
    return write(root, path, f"# Sample\n\n{vp.MEMBER_ID_LABEL}: `{ident}`\n{vp.MEMBER_STATUS_LABEL}: `planned`\n" + (f"{vp.BACKREF_LABEL}: `{wave_id}`\n" if wave_id else "") + body)


def build_index_fixture(root):
    """Real canonical vectors, FTS and graph publications; no models."""
    import index_state_store as iss
    import index_compatibility as ic
    import sqlite_vector_store as vectors
    import graph_fixture_support as gfs
    directory = root / ".wavefoundry/index"
    directory.mkdir(parents=True, exist_ok=True)
    nodes = [{"id": "main.py::a", "label": "a", "kind": "function", "source_file": "main.py"},
             {"id": "main.py::b", "label": "b", "kind": "function", "source_file": "main.py"}]
    edges = [{"source": "main.py::a", "target": "main.py::b", "relation": "calls", "source_file": "main.py"}]
    gfs.publish_graph(root, nodes=nodes, edges=edges, communities=[{"community_id": "one", "node_ids": [n["id"] for n in nodes]}])
    attempt = iss.begin_build_epoch(directory, "all")
    iss.write_build_bookkeeping(directory, {
        "built_at": "2026-01-01T00:00:00Z", "model_versions": {"docs": "fixture-model", "code": "fixture-model"},
        "content": ["docs", "code"], "file_meta": {"README.md": {}, "main.py": {}},
        "walker_version": str(ic.SUPPORTED["walker_version"]),
        "chunker_versions": {k: str(ic.SUPPORTED["chunker_version"]) for k in ("docs", "code")}})
    store = iss.IndexStateStore(directory)
    try:
        for layer, texts in (("docs", ["alpha alpha beta keep_together", "beta gamma"]), ("code", ["alpha delta"])):
            rows = [{"id": f"{layer}{n}", "path": "README.md" if layer == "docs" else "main.py", "text": text, "kind": layer, "language": "python" if layer == "code" else "markdown", "tags": ""} for n, text in enumerate(texts)]
            iss.rebuild_chunk_index(directory, layer, rows)
            with store._conn:
                vectors.write_rows(store._conn, layer, [{**row, "vector": [1.] + [0.] * 383} for row in rows])
    finally:
        store.close()
    assert iss.finalize_build_epoch(directory, attempt)
    return directory


class ProjectStatsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def section(self, name):
        return stats.collect_project_stats(self.root, [name])["sections"][name]

    def test_exact_code_categories_test_conventions_and_todos(self):
        write(self.root, ".gitignore", "ignored.py\n")
        write(self.root, "ignored.py", "TODO\n")
        write(self.root, ".wavefoundry/framework/scripts/vendor.py", "TODO\n")
        write(self.root, ".wavefoundry/framework/seeds/seed.md", "TODO\n")
        write(self.root, "main.py", '# TODO\n\nx = 1\n')
        write(self.root, "tests/unit.py", '# FIXME\r\n\r\nx = 2\r\n')
        write(self.root, "test_other.py", 'x = 3\n')
        write(self.root, "contest.py", 'x = 4\n')
        write(self.root, "widget.spec.ts", '// HACK XXX\nlet n = 1;\n')
        write(self.root, "HTTPTest.java", '// TODO\nclass HTTPTest {}\n')
        write(self.root, "Contest.java", 'class Contest {}\n')
        write(self.root, "README.md", '# TODO FIXME\n\nprose\n')
        write(self.root, "tests/note.md", 'TODO\n')
        write(self.root, "openapi.spec.yaml", 'name: hello\n')
        write(self.root, "data.json", '{}\n')
        write(self.root, "binary.py", b'x\0garbage')
        write(self.root, "image.png", b'hello')
        payload = stats.collect_project_stats(self.root, ["code", "todo"])["sections"]
        code = payload["code"]
        self.assertTrue(code["available"], code)
        py = code["languages"]["python"]
        self.assertEqual(py["both"], dict(files=4, total_lines=8, blank_lines=2, comment_lines=2, code_lines=4))
        self.assertEqual(py["test"], dict(files=2, total_lines=4, blank_lines=1, comment_lines=1, code_lines=2))
        self.assertEqual(py["production"], py["test"])
        self.assertEqual(py["test_code_ratio"], .5)
        self.assertEqual(code["languages"]["java"]["test"]["files"], 1)
        self.assertEqual(code["languages"]["typescript"]["test"]["files"], 1)
        self.assertEqual(code["categories"]["documentation"]["both"]["files"], 2)
        self.assertIsNone(code["languages"]["json"]["both"]["comment_lines"])
        self.assertEqual(code["languages"]["json"]["both"]["code_lines"], 1)
        self.assertEqual(code["categories"]["data"]["both"]["files"], 2)
        self.assertEqual(code["binary_files"], 1)
        for key in stats.COUNT_KEYS:
            row = code["categories"]["code"]
            self.assertEqual(row["both"][key], None if row["production"][key] is None or row["test"][key] is None else row["production"][key] + row["test"][key])
        todo = payload["todo"]
        self.assertEqual(todo["by_marker"], {"TODO": 2, "FIXME": 1, "HACK": 1, "XXX": 1})
        self.assertEqual(todo["total"], 5)
        self.assertEqual(todo["top_files"][0], {"path": "widget.spec.ts", "count": 2})
        self.assertIn("max_file_bytes", code)
        self.assertIn(stats.LEXICAL_NOTE, stats.format_report({"sections": payload}))
        self.assertIn(stats.TEST_NOTE, stats.format_report({"sections": payload}))

    def test_lexical_delimiters_crlf_and_marker_boundaries(self):
        self.assertEqual(stats._line_counts('# a\r\n\r\nx\r\n', 'python'), stats._line_counts('# a\n\nx\n', 'python'))
        row = stats._line_counts('s = "//";\n/* a\nb */\nx\n', 'javascript')
        self.assertEqual((row["comment_lines"], row["code_lines"]), (3, 1))
        write(self.root, "x.py", "todo TODOS TODO_ TODO FIXME HACK XXX\n")
        self.assertEqual(self.section("todo")["total"], 4)

    def test_partial_walk_or_file_read_is_not_a_complete_report(self):
        import indexer
        file = write(self.root, "x.py", "x\n")
        def denied(root, **kwargs):
            kwargs["unreadable_dirs"].add("private")
            return [file]
        with patch.object(indexer, "walk_repo", side_effect=denied):
            result = stats.collect_project_stats(self.root, ["code", "todo", "secrets"])["sections"]
        for name in ("code", "todo"):
            self.assertFalse(result[name]["available"])
            self.assertFalse(result[name]["complete"])
            self.assertEqual(result[name]["unreadable_directories"], 1)
        self.assertTrue(result["secrets"]["available"])
        original = Path.read_bytes
        def unreadable(path):
            if path == file:
                raise PermissionError("private content")
            return original(path)
        with patch.object(indexer, "walk_repo", return_value=[file]), patch.object(Path, "read_bytes", unreadable):
            result = self.section("code")
        self.assertFalse(result["available"])
        self.assertEqual(result["unreadable_files"], 1)
        self.assertNotIn("private content", json.dumps(result))

    def test_lazy_selection_and_invalid_sections(self):
        write(self.root, "x.py", "x\n")
        with patch.object(dashboard, "collect_health", side_effect=AssertionError("health")), patch.object(dashboard, "collect_waves", side_effect=AssertionError("waves")), patch.object(stats, "_memories", side_effect=AssertionError("memory")):
            result = stats.collect_project_stats(self.root, ["code"])
        self.assertEqual(list(result["sections"]), ["code"])
        self.assertTrue(result["sections"]["code"]["available"])
        for selection in (["bogus"], "code", [None]):
            with self.assertRaises(ValueError):
                stats.collect_project_stats(self.root, selection)
        self.assertEqual(stats.collect_project_stats(self.root, []), {"schema_version": 1, "sections": {}})

    def test_lifecycle_real_collectors_missing_unreadable_raw_and_uncapped(self):
        a, b, c = "234aa closed", "234ab implementing", "234ac planned"
        wave(self.root, a, "closed", ["234ad-enh alpha", "234ae-bug gone"])
        wave(self.root, b, "implementing", ["234af-feat unreadable"])
        wave(self.root, c, "planned")
        change(self.root, "234ad-enh alpha", a, "\n## Acceptance Criteria\n\n- [x] AC-1: done\n- [~] AC-2: deferred\n- [ ] AC-3: open\n- [ ] AC-4: other\n\n## AC Priority\n\n| AC | Priority |\n| --- | --- |\n| AC-1 | required |\n| AC-2 | required |\n| AC-3 | required |\n| AC-4 | not-this-scope |\n\n## Tasks\n\n- [x] done\n- [~] deferred\n- [ ] open\n")
        broken = change(self.root, "234af-feat unreadable", b)
        broken.write_bytes(b'\xff')
        change(self.root, "234ag-bug plan")
        result = self.section("lifecycle")
        self.assertTrue(result["available"], result)
        self.assertEqual(result["waves"]["by_status"], {"closed": 1, "implementing": 1, "planned": 1})
        self.assertEqual(result["missing_admitted_documents"], 1)
        self.assertEqual(result["unreadable_change_documents"], 1)
        self.assertEqual(result["raw_checkboxes"]["criteria"], {"done": 1, "deferred": 1, "open": 1, "total": 3, "not_this_scope": 1})
        self.assertEqual(result["raw_checkboxes"]["tasks"], {"done": 1, "deferred": 1, "open": 1, "total": 3})
        self.assertFalse(result["progress"]["coverage"]["complete"])
        self.assertIn("incomplete", result["progress"]["coverage"]["warning"])
        self.assertEqual(result["changes"]["plan"]["by_kind"], {"bug": 1})
        for n in range(201):
            wave(self.root, f"extra{n:03d} empty")
        self.assertEqual(self.section("lifecycle")["waves"]["total"], 204)

    def test_shared_progress_fixture_parity(self):
        from test_dashboard_progress import progress_fixture, expected_checklists
        for opens in (False, True):
            waves, changes = progress_fixture(opens)
            with patch.object(dashboard, "collect_waves", return_value=waves), patch.object(dashboard, "collect_changes", return_value=changes):
                actual = self.section("lifecycle")
            self.assertEqual(actual["progress"], dashboard.collect_progress(waves, changes))
            for group, expected in expected_checklists(opens).items():
                self.assertEqual(actual["progress"][group], expected)
                self.assertIs(actual["raw_checkboxes"][group], actual["progress"][group])
            self.assertEqual(actual["unadmitted_checkboxes"]["criteria"], {"done": 1, "deferred": 0, "open": 2, "total": 3, "not_this_scope": 0})
            self.assertEqual(actual["unadmitted_checkboxes"]["tasks"], {"done": 0, "deferred": 1, "open": 2, "total": 3})

    def test_admitted_raw_counts_are_shared_not_recounted(self):
        sentinel = {
            "criteria": {"done": 7, "deferred": 2, "open": 3, "total": 12, "not_this_scope": 1},
            "tasks": {"done": 8, "deferred": 1, "open": 4, "total": 13},
            "coverage": {"complete": True, "missing_admitted_documents": 0, "unreadable_change_documents": 0, "warning": None},
        }
        with patch.object(dashboard, "collect_progress", return_value=sentinel):
            result = stats._lifecycle([], {"wave": [], "plan": []})
        self.assertIs(result["progress"], sentinel)
        for group in ("criteria", "tasks"):
            self.assertIs(result["raw_checkboxes"][group], sentinel[group])

    def test_unreadable_unadmitted_plan_does_not_degrade_admitted_coverage(self):
        broken = change(self.root, "234ag-bug plan")
        broken.write_bytes(b'\xff')
        result = self.section("lifecycle")
        self.assertTrue(result["progress"]["coverage"]["complete"])
        self.assertFalse(result["unadmitted_checkboxes"]["coverage"]["complete"])
        self.assertEqual(result["unadmitted_checkboxes"]["coverage"]["unreadable_change_documents"], 1)
        self.assertEqual(result["unreadable_change_documents"], 1)

    def test_actual_admission_not_short_or_stale_wave_metadata_owns_lifecycle_count(self):
        ident = "234aa closed-wave"
        names = ["234ab-enh short", "234ac-bug stale", "234ad-feat unreadable"]
        wave(self.root, ident, "closed", names)
        for name, metadata in zip(names[:2], ("234aa", "different-wave")):
            path = change(self.root, name, ident, "\n## Acceptance Criteria\n\n- [ ] AC-1: still open\n\n## Tasks\n\n- [~] deferred\n")
            text = path.read_text().replace(f"{vp.BACKREF_LABEL}: `{ident}`", f"{vp.BACKREF_LABEL}: `{metadata}`").replace(f"{vp.MEMBER_STATUS_LABEL}: `planned`", f"{vp.MEMBER_STATUS_LABEL}: `completed`")
            path.write_text(text)
        change(self.root, names[2], ident).write_bytes(b'\xff')
        rows = dashboard.collect_changes(self.root)["wave"]
        self.assertEqual([row["admitted_wave_id"] for row in rows], [ident] * 3)
        result = self.section("lifecycle")
        self.assertEqual(result["progress"]["changes"], {"done": 3, "total": 3})
        self.assertEqual(result["progress"]["criteria"], {"done": 0, "deferred": 0, "open": 2, "total": 2, "not_this_scope": 0})
        self.assertEqual(result["progress"]["tasks"], {"done": 0, "deferred": 2, "open": 0, "total": 2})

    def test_both_progress_fixtures_match_all_shared_snapshot_figures(self):
        from test_dashboard_progress import progress_fixture
        import copy
        build_index_fixture(self.root)
        for opens in (False, True):
            waves, changes = progress_fixture(opens)
            for n, row in enumerate(changes["wave"] + changes["plan"]):
                row.update(change_id=f"fixture-{n}", kind="enh", title="Fixture")
            roles = [{"category": "review", "name": "reviewer"}]
            with patch.object(dashboard, "collect_waves", side_effect=lambda root: copy.deepcopy(waves)), patch.object(dashboard, "collect_changes", side_effect=lambda root: copy.deepcopy(changes)), patch.object(dashboard, "collect_agents", return_value=roles), patch.object(dashboard, "collect_activity", return_value={}):
                report = stats.collect_project_stats(self.root, ["lifecycle", "documents", "index"])["sections"]
                snapshot = dashboard.collect_dashboard_snapshot(self.root, skip_git=True)
            self.assertEqual(report["lifecycle"]["progress"], snapshot["progress"])
            self.assertEqual(report["lifecycle"]["waves"]["by_status"], snapshot["project"]["wave_status_counts"])
            self.assertEqual(report["lifecycle"]["changes"]["wave"]["total"], len(snapshot["changes"]["in_waves"]))
            self.assertEqual(report["lifecycle"]["changes"]["plan"]["total"], len(snapshot["changes"]["staged"]))
            self.assertEqual(report["documents"]["agents"]["total"], len(snapshot["agents"]))
            health = snapshot["health"]
            for key in ("files_indexed", "doc_chunks", "code_chunks"):
                self.assertEqual(report["index"]["embedding"][key], health["index"]["project"][key])
            self.assertEqual(report["index"]["lexical"]["entries"], health["lexical"]["project"]["entries"])
            for key in ("nodes", "edges"):
                self.assertEqual(report["index"]["graph"][key], health["graph"]["project"]["counts"][key])

    def test_documents_missing_directories_and_dashboard_role_counts(self):
        write(self.root, "docs/specs/one.md", "# One\n")
        write(self.root, "docs/architecture/design.md", "# Design\n")
        write(self.root, "docs/architecture/decisions/234aa-adr choice.md", "# Choice\n")
        write(self.root, "docs/architecture/decisions/README.md", "# Index\n")
        with patch.object(dashboard, "collect_agents", return_value=[{"category": "review"}, {"category": "review"}, {"category": "build"}]), patch.object(dashboard, "read_prompt_manifest", return_value={"public_prompt_surface": [1, 2]}):
            result = self.section("documents")
        self.assertEqual((result["specifications"], result["architecture"], result["decisions"], result["public_prompts"]), (1, 3, 1, 2))
        self.assertEqual(result["agents"], {"total": 3, "by_category": {"build": 1, "review": 2}})
        self.assertEqual(stats._document_count(self.root / "absent"), 0)

    def test_memories_archive_bodies_count_once(self):
        import memory_records as memory
        for ident, kind, status, folder in (("234aa-mem active", "successful_pattern", "active", ""), ("234ab-mem candidate", "failed_attempt", "candidate", ""), ("234ac-mem archived", "failed_attempt", "stale", "")):
            body = memory.render_memory_record(memory_id=ident, kind=kind, summary="A fixture lesson", evidence=["fixture"], targets=["src/a.py"], status=status, date="2026-01-01")
            write(self.root, f"docs/agents/memory/{folder}{ident}.md", body)
        memory.archive_memory_record(self.root, "234ac-mem archived", reason="Fixture archival")
        result = self.section("memories")
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["by_status"], {"active": 1, "archived": 1, "candidate": 1})
        self.assertEqual(result["active_by_kind"], {"successful_pattern": 1})

    def test_tokens_exclude_all_unhealthy_figures_and_read_no_live_store(self):
        import context_efficiency as ce
        for n, status in enumerate(("healthy", "healthy", "accounting_gap")):
            path = wave(self.root, f"234a{n} token")
            state = ce.empty_checkpoint(f"234a{n} token")
            state["measurement_status"] = status
            state["pending"] = n == 2
            stage = dict(state["totals"])
            stage.update(calls=2 + n, content_source_credit=100 * (n + 1), request_debit=10, response_debit=20, direct_net=100 * (n + 1) - 30, estimated_tokens_saved=100 * (n + 1) - 30)
            state["stages"] = {"implementation": stage}
            path.write_text(path.read_text() + '\n' + ce.render_checkpoint_block(state))
        wave(self.root, "234a3 missing")
        with patch.object(ce, "_open_write_store", side_effect=AssertionError("live store")):
            result = self.section("token_savings")
        self.assertTrue(result["available"], result)
        self.assertEqual((result["records_with_marker"], result["records_without_marker"], result["pending_markers"]), (3, 1, 1))
        self.assertEqual(result["estimated_totals"]["calls"], 5)
        self.assertEqual(result["estimated_totals"]["content_source_credit"], 300)
        self.assertEqual(result["estimated_stages"]["implementation"]["content_source_credit"], 300)
        self.assertEqual(len(result["excluded_records"]), 1)
        self.assertEqual(result["limitation"], ce._CHECKPOINT_ESTIMATE_NOTE)

    def test_secret_counts_and_no_sensitive_content_including_errors(self):
        entries = []
        for count in (0, 1, 2):
            entries.append({"status": "false-positive", "rule_id": "demo", "confirmations": [{"git_user_email": f"private-person-{n}"} for n in range(count)] * 2, "override_reason": "private-override" if count == 2 else "", "file": "private-path", "matched_text": "private-match", "line_hash": "private-hash"})
        entries += [{"status": status, "rule_id": "other"} for status in ("confirmed-secret", "suspected-secret", "pending", "other")]
        entries.append({"rule_id": "other"})
        path = write(self.root, "docs/scan-findings.json", json.dumps(entries))
        result = self.section("secrets")
        self.assertEqual(result["by_status"], {"false-positive": 3, "confirmed-secret": 1, "suspected-secret": 1, "pending": 2, "unclassified": 1})
        self.assertEqual(result["false_positive_confirmations"], {"0": 1, "1": 1, "2": 1, "3+": 0})
        self.assertEqual(result["false_positive_overrides"], 1)
        self.assertEqual(result["by_rule"]["other"]["pending"], 2)
        rendered = json.dumps(result) + stats.format_report({"sections": {"secrets": result}})
        self.assertNotIn("private-", rendered)
        path.write_text('private-bad-json')
        self.assertFalse(self.section("secrets")["available"])
        self.assertNotIn("private-", json.dumps(self.section("secrets")))
        path.unlink()
        self.assertEqual(self.section("secrets")["total"], 0)
        self.assertTrue(self.section("secrets")["available"])

    def test_no_index_report_and_cli_are_read_only_and_spawn_nothing(self):
        import subprocess
        write(self.root, "x.py", "x\n")
        ce = self.root / ".wavefoundry/index/context-efficiency.sqlite3"
        ce.parent.mkdir(parents=True)
        conn = sqlite3.connect(ce)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('CREATE TABLE untouched (value TEXT)')
        conn.commit()
        conn.close()
        before = tree_bytes(self.root)
        with patch.object(subprocess, "Popen", side_effect=AssertionError("subprocess")), patch.object(dashboard, "collect_health", side_effect=AssertionError("no store")):
            report = stats.collect_project_stats(self.root)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(stats.main(["--root", str(self.root), "--json"]), 0)
        self.assertEqual(json.loads(output.getvalue()), report)
        self.assertEqual(tree_bytes(self.root), before)
        self.assertFalse(report["sections"]["index"]["available"])
        self.assertEqual(set(report["sections"]), set(stats.SECTIONS))
        for key in stats.SECTIONS:
            if key != "index":
                self.assertTrue(report["sections"][key]["available"], (key, report))

    def test_bad_build_state_is_retained_and_health_not_called(self):
        from index_state_store import state_store_path
        path = state_store_path(self.root / ".wavefoundry/index")
        write(self.root, path.relative_to(self.root), b'placeholder')
        state = write(self.root, ".wavefoundry/index/index-build.json", '{}')
        for contents in ('broken', '[]', 'null'):
            state.write_text(contents)
            before = tree_bytes(self.root)
            with patch.object(dashboard, "collect_health", side_effect=AssertionError("must not call")) as health:
                result = self.section("index")
            self.assertEqual(result["reason"], "build_state_invalid")
            health.assert_not_called()
            self.assertEqual(tree_bytes(self.root), before)
        original = Path.read_text
        def unreadable(path, *args, **kwargs):
            if path == state:
                raise PermissionError('state')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', unreadable), patch.object(dashboard, "collect_health") as health:
            self.assertEqual(self.section("index")["reason"], "build_state_unreadable")
            health.assert_not_called()

    def test_real_index_figures_and_no_bulk_payload(self):
        build_index_fixture(self.root)
        result = self.section("index")
        self.assertTrue(result["available"], result)
        self.assertEqual((result["embedding"]["files_indexed"], result["embedding"]["doc_chunks"], result["embedding"]["code_chunks"]), (2, 2, 1))
        self.assertEqual(result["lexical"], {"status": "ready", "entries": 3, "term_occurrences": 8, "distinct_terms": 5})
        self.assertEqual((result["graph"]["nodes"], result["graph"]["edges"], result["graph"]["clusters"]), (2, 1, 1))
        self.assertNotIn("main.py::a", json.dumps(result))
        health = dashboard.collect_health(self.root, 0, {"wave": [], "plan": []})
        self.assertEqual(result["embedding"]["doc_chunks"], health["index"]["project"]["doc_chunks"])
        self.assertEqual(result["graph"]["generation"], health["graph"]["project"]["generation"])

    def test_profile_changes_only_human_labels(self):
        payload = {"schema_version": 1, "sections": {"lifecycle": {"waves": {"total": 2}, "changes": {"wave": {"total": 3}, "plan": {"total": 1}}, "raw_checkboxes": {"criteria": {"total": 5}, "tasks": {"total": 7}}, "unadmitted_checkboxes": {"tasks": {"total": 2}}}, "todo": {"total": 9}}}
        before = json.dumps(payload)
        rendered = stats.format_report(payload)
        for label in (f"{vp.ITEM_NAME_PLURAL} assigned to {vp.CONTAINER_NAME_PLURAL.lower()}", f"Plans not assigned to a {vp.CONTAINER_NAME.lower()}", "Acceptance criteria", "Implementation tasks", "Source-code TODO markers"):
            self.assertIn(label, rendered)
        with patch.object(vp, 'CONTAINER_NAME', 'Set'), patch.object(vp, 'CONTAINER_NAME_PLURAL', 'Sets'), patch.object(vp, 'ITEM_NAME', 'Work'), patch.object(vp, 'ITEM_NAME_PLURAL', 'Works'):
            rendered = stats.format_report(payload)
        self.assertIn('Sets and Works', rendered)
        self.assertIn('Works assigned to sets', rendered)
        self.assertIn('Plans not assigned to a set', rendered)
        self.assertNotIn('Waves', rendered)
        self.assertNotIn('wave', rendered)
        self.assertEqual(before, json.dumps(payload))
        with patch.object(vp, 'CONTAINER_NAME', 'Set'), patch.object(vp, 'ITEM_NAME', 'Work'):
            note = stats._lifecycle([], {"wave": [], "plan": []})["progress_note"]
        self.assertIn("Lifecycle rows describe record status", note)
        self.assertNotIn("wave", note.lower())
        self.assertNotIn("change", note.lower())
        self.assertNotIn("differ by design", note)


if __name__ == '__main__':
    unittest.main()
