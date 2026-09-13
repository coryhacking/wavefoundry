from __future__ import annotations

import contextlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
import graph_call_census as census_module


def write_fixture(path: Path) -> None:
    """Real persisted rows: both false-target kinds and positive/negative controls."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript("""
            CREATE TABLE graph_nodes (node_id TEXT PRIMARY KEY, kind TEXT, source_file TEXT);
            CREATE TABLE graph_edges (source_id TEXT, target_id TEXT, relation TEXT, confidence TEXT);
        """)
        connection.executemany("INSERT INTO graph_nodes VALUES (?, ?, ?)", [
            ("Caller.java::run", "function", "Caller.java"),
            ("other.py::run", "function", "other.py"),
            ("Defs.java::field", "variable", "Defs.java"),
            ("Defs.java::CONST", "constant", "Defs.java"),
            ("Defs.java::method", "function", "Defs.java"),
            ("Defs.java::Type", "class", "Defs.java"),
            ("module.py", "module", "module.py"),
        ])
        connection.executemany("INSERT INTO graph_edges VALUES (?, ?, ?, ?)", [
            ("Caller.java::run", "Defs.java::field", "calls", "RECEIVER_RESOLVED"),
            ("Caller.java::run", "Defs.java::CONST", "calls", "EXTRACTED"),
            ("Caller.java::run", "Defs.java::method", "calls", "RECEIVER_RESOLVED"),
            ("Caller.java::run", "Defs.java::Type", "calls", "CONSTRUCTION_RESOLVED"),
            ("other.py::run", "Defs.java::method", "calls", "EXTRACTED"),
            ("other.py::run", "module.py", "calls", "EXTRACTED"),
            ("Caller.java::run", "external::normal", "calls", "EXTRACTED"),
            ("Caller.java::run", "external::e-", "calls", "EXTRACTED"),
            ("other.py::run", "external::e-", "calls", "EXTRACTED"),
            ("Caller.java::run", "Defs.java::field", "reads", "EXTRACTED"),
            ("Caller.java::run", "Defs.java::CONST", "reads", "EXTRACTED"),
            ("module.py", "other.py::run", "defines", "EXTRACTED"),
            ("Caller.java::run", "external::ignore-", "imports", "EXTRACTED"),
        ])
        connection.commit()
    finally:
        connection.close()


class GraphCallCensusTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.database = self.root / ".wavefoundry/index/index.sqlite"
        write_fixture(self.database)

    def test_sql_populations_have_nonvacuous_kind_confidence_and_language_controls(self):
        result = census_module.census(self.root)
        self.assertEqual(result["non_callable_call_targets"], [
            {"language": "java", "target_kind": "constant", "confidence": "EXTRACTED", "count": 1},
            {"language": "java", "target_kind": "variable", "confidence": "RECEIVER_RESOLVED", "count": 1},
        ])
        self.assertEqual(result["callable_call_targets"], [
            {"language": "java", "target_kind": "class", "confidence": "CONSTRUCTION_RESOLVED", "count": 1},
            {"language": "java", "target_kind": "function", "confidence": "RECEIVER_RESOLVED", "count": 1},
            {"language": "python", "target_kind": "function", "confidence": "EXTRACTED", "count": 1},
        ])
        self.assertEqual(result["reads_defines"], [
            {"relation": "defines", "count": 1}, {"relation": "reads", "count": 2},
        ])
        self.assertEqual(result["calls_by_language_and_confidence"], [
            {"language": "java", "confidence": "CONSTRUCTION_RESOLVED", "count": 1},
            {"language": "java", "confidence": "EXTRACTED", "count": 3},
            {"language": "java", "confidence": "RECEIVER_RESOLVED", "count": 2},
            {"language": "python", "confidence": "EXTRACTED", "count": 3},
        ])
        self.assertIn({"language": "java", "kind": "variable", "count": 1}, result["node_kinds"])
        self.assertIn({"target_kind": "module", "confidence": "EXTRACTED", "count": 1},
                      result["calls_by_target_kind_and_confidence"])
        self.assertEqual(result["external_call_targets"], [
            {"language": "java", "confidence": "EXTRACTED", "count": 2, "distinct_targets": 2},
            {"language": "python", "confidence": "EXTRACTED", "count": 1, "distinct_targets": 1},
        ])
        self.assertEqual(result["malformed_external_call_targets"], [
            {"language": "java", "target_id": "external::e-", "confidence": "EXTRACTED", "count": 1},
            {"language": "python", "target_id": "external::e-", "confidence": "EXTRACTED", "count": 1},
        ])

    def test_every_malformed_operator_is_counted_but_normal_and_noncall_rows_are_not(self):
        malformed = ["a->b", "a?.b", "a!.b", "a(b", "a[b", "a<b"]
        with contextlib.closing(sqlite3.connect(self.database)) as connection:
            connection.executemany("INSERT INTO graph_edges VALUES (?, ?, 'calls', 'EXTRACTED')",
                                   [("Caller.java::run", "external::" + name) for name in malformed])
            connection.commit()
        result = census_module.census(self.root)
        targets = {row["target_id"] for row in result["malformed_external_call_targets"]}
        self.assertEqual(targets, {"external::e-", *("external::" + name for name in malformed)})

    def test_uri_metacharacters_read_intended_database_without_creating_files(self):
        names = ["repo#fragment", "repo%encoded", "repo with space", "repo-café-雪"]
        # '?' is not a legal Windows filename; its URI encoding is still tested below.
        if os.name != "nt":
            names.append("repo?query")
        for name in names:
            with self.subTest(name=name):
                database = self.root / name / "index.sqlite"
                write_fixture(database)
                paths_before = set(self.root.rglob("*"))
                bytes_before = database.read_bytes()
                result = census_module.census(self.root, database)
                self.assertEqual(result["database"], str(database))
                self.assertEqual(sum(row["count"] for row in result["non_callable_call_targets"]), 2)
                self.assertEqual(database.read_bytes(), bytes_before)
                self.assertEqual(set(self.root.rglob("*")), paths_before)

    def test_windows_drive_and_unc_uri_construction_without_native_io(self):
        # PureWindowsPath validates encoding on every host, not Windows execution.
        drive = PureWindowsPath("C:/repo #?% café/index.sqlite")
        unc = PureWindowsPath("//server/share/repo #?% café/index.sqlite")
        self.assertEqual(census_module._read_only_uri(drive),
                         "file:///C:/repo%20%23%3F%25%20caf%C3%A9/index.sqlite?mode=ro")
        self.assertEqual(census_module._read_only_uri(unc),
                         "file://server/share/repo%20%23%3F%25%20caf%C3%A9/index.sqlite?mode=ro")

    def test_checkpointed_wal_without_sidecars_is_refused_without_creation(self):
        with contextlib.closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        paths_before = set(self.root.rglob("*"))
        bytes_before = self.database.read_bytes()
        with patch.object(census_module.sqlite3, "connect") as connect:
            with self.assertRaisesRegex(ValueError, "owning application"):
                census_module.census(self.root)
            connect.assert_not_called()
        self.assertEqual(set(self.root.rglob("*")), paths_before)
        self.assertEqual(self.database.read_bytes(), bytes_before)

    def test_existing_nonempty_wal_latest_commit_is_visible_without_data_writes(self):
        with contextlib.closing(sqlite3.connect(self.database)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO graph_edges VALUES "
                           "('Caller.java::run', 'Defs.java::field', 'calls', 'EXTRACTED')")
            writer.commit()
            wal = Path(str(self.database) + "-wal")
            self.assertGreater(wal.stat().st_size, 32)
            paths_before = set(self.root.rglob("*"))
            bytes_before, wal_before = self.database.read_bytes(), wal.read_bytes()
            result = census_module.census(self.root)
            self.assertEqual(sum(row["count"] for row in result["non_callable_call_targets"]), 3)
            self.assertEqual(self.database.read_bytes(), bytes_before)
            self.assertEqual(wal.read_bytes(), wal_before)
            self.assertEqual(set(self.root.rglob("*")), paths_before)

            # A detached copy with committed WAL but absent SHM is refused;
            # immutable=1 would silently omit the third call and is not used.
            copy = self.root / "detached/index.sqlite"
            copy.parent.mkdir()
            copy.write_bytes(bytes_before)
            Path(str(copy) + "-wal").write_bytes(wal_before)
            paths_before = set(self.root.rglob("*"))
            with self.assertRaisesRegex(ValueError, "owning application"):
                census_module.census(self.root, copy)
            self.assertEqual(set(self.root.rglob("*")), paths_before)

    def test_wal_sidecars_reject_nonfiles_and_symlink_escape(self):
        with contextlib.closing(sqlite3.connect(self.database)) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
        wal, shm = (Path(str(self.database) + suffix) for suffix in ("-wal", "-shm"))
        wal.mkdir()
        shm.touch()
        with self.assertRaisesRegex(ValueError, "regular files beneath"):
            census_module.census(self.root)
        wal.rmdir()
        outside = self.root / "outside-wal"
        outside.touch()
        try:
            wal.symlink_to(outside)
        except OSError as error:
            if os.name == "nt":
                self.skipTest(f"Windows symlink privilege unavailable: {error}")
            raise
        with patch.object(census_module.sqlite3, "connect") as connect:
            with self.assertRaisesRegex(ValueError, "regular files beneath"):
                census_module.census(self.database.parent, self.database)
            connect.assert_not_called()

    def test_missing_database_never_creates_file_or_directory(self):
        paths_before = set(self.root.rglob("*"))
        with self.assertRaises(FileNotFoundError):
            census_module.census(self.root, "missing#?%/index.sqlite")
        self.assertEqual(set(self.root.rglob("*")), paths_before)

    def test_parent_traversal_absolute_and_symlink_escapes_are_refused_before_connect(self):
        inner = self.root / "inner"
        inner.mkdir()
        with patch.object(census_module.sqlite3, "connect") as connect:
            for database in ("../.wavefoundry/index/index.sqlite", self.database):
                with self.subTest(database=str(database)), self.assertRaisesRegex(ValueError, "beneath"):
                    census_module.census(inner, database)
            connect.assert_not_called()
        link = inner / "escape.sqlite"
        try:
            link.symlink_to(self.database)
        except OSError as error:
            if os.name == "nt":
                self.skipTest(f"Windows symlink privilege unavailable: {error}")
            raise
        with patch.object(census_module.sqlite3, "connect") as connect:
            with self.assertRaisesRegex(ValueError, "beneath"):
                census_module.census(inner, link)
            connect.assert_not_called()

    def test_connection_is_read_only_and_explicitly_closed_on_success_and_query_error(self):
        original_connect = sqlite3.connect
        connections = []

        class TrackedConnection(sqlite3.Connection):
            closed = False

            def close(self):
                self.closed = True
                super().close()

        def connect(database_uri, **kwargs):
            connection = original_connect(database_uri, factory=TrackedConnection, **kwargs)
            connections.append(connection)
            with self.assertRaisesRegex(sqlite3.OperationalError, "readonly"):
                connection.execute("CREATE TABLE unintended_write (value)")
            return connection

        with patch.object(census_module.sqlite3, "connect", side_effect=connect):
            census_module.census(self.root)
            with patch.dict(census_module.CENSUS_QUERIES, {"bad_query": "SELECT * FROM missing_table"}):
                with self.assertRaises(sqlite3.OperationalError):
                    census_module.census(self.root)
        self.assertEqual(len(connections), 2)
        self.assertTrue(all(connection.closed for connection in connections))

    def test_cli_subprocess_reaches_census_and_emits_json(self):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS_ROOT / "graph_call_census.py"),
             "--root", str(self.root), "--database", ".wavefoundry/index/index.sqlite"],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual(sum(row["count"] for row in data["non_callable_call_targets"]), 2)
        self.assertEqual(result.stderr, "")

    def test_cli_failure_is_nonzero_and_does_not_create_missing_database(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = census_module.main(["--root", str(self.root), "--database", "absent.sqlite"])
        self.assertEqual(status, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("graph_call_census:", stderr.getvalue())
        self.assertFalse((self.root / "absent.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
