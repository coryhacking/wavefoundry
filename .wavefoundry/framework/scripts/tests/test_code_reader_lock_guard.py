"""Wave 1zv87 (1zuq7): code readers never open a framework runtime lock.

The lifecycle and index-build locks are POSIX record locks (``lockf``), which
the kernel releases when the holding process closes ANY descriptor of the
file. A reader in the server process that opens one silently drops the lock.
The oracle is a second process that tries to take the lock byte with a raw
``lockf``: it must still see the lock busy after every refused read.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from server_tools_support import _make_repo, load_server  # noqa: E402

srv = load_server()

import lifecycle_lock  # noqa: E402
import wf_server.codenav_handlers as codenav_handlers  # noqa: E402
import wf_server.graph_handlers as graph_handlers  # noqa: E402

_PROBE = textwrap.dedent(
    """
    import fcntl, os, sys
    fd = os.open(sys.argv[1], os.O_RDWR)
    try:
        os.lseek(fd, int(sys.argv[2]), os.SEEK_SET)
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, int(sys.argv[2]))
    except OSError:
        print("held")
    else:
        print("free")
    """
)

LOCK_REL = ".wavefoundry/lifecycle-mutation.lock"


def _case_insensitive(root: Path) -> bool:
    probe = root / "CaseProbe.tmp"
    probe.write_text("", encoding="utf-8")
    try:
        return (root / "caseprobe.TMP").exists()
    finally:
        probe.unlink()


class _RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name).resolve(), {
            "src/app.py": "def app():\n    return 'needle'\n",
            ".wavefoundry/framework/scripts/tool.py": "def tool():\n    return 'needle'\n",
            ".wavefoundry/index/index-build.lock": "{}\n",
            ".wavefoundry/locks/dashboard-server.lock": "{}\n",
        })

    def assert_refused(self, response: dict) -> None:
        self.assertEqual(response["status"], "error", response)


class ResolverRefusesLockFilesTests(_RepoCase):
    """AC-2: the resolver rule and its scope."""

    def test_lock_paths_are_refused(self) -> None:
        (self.root / LOCK_REL).write_text("{}\n", encoding="utf-8")
        for rel in (
            LOCK_REL,
            ".wavefoundry/index/index-build.lock",
            ".wavefoundry/locks/dashboard-server.lock",
            ".WAVEFOUNDRY/Lifecycle-Mutation.LOCK",
            ".wavefoundry/./index/../lifecycle-mutation.lock",
        ):
            with self.subTest(rel=rel):
                self.assertIsNone(srv._resolve_repo_path(self.root, rel))
                self.assert_refused(codenav_handlers.code_read_response(self.root, rel))

    def test_case_variant_is_refused_where_it_names_the_lock(self) -> None:
        (self.root / LOCK_REL).write_text("{}\n", encoding="utf-8")
        variant = ".WAVEFOUNDRY/Lifecycle-Mutation.LOCK"
        if _case_insensitive(self.root):
            self.assertTrue((self.root / variant).is_file())
        self.assertTrue(srv._is_runtime_lock_path(self.root, self.root / variant))
        self.assert_refused(codenav_handlers.code_read_response(self.root, variant))

    def test_ordinary_and_framework_files_still_read(self) -> None:
        (self.root / "yarn.lock").write_text("# not a framework lock\n", encoding="utf-8")
        for rel in ("src/app.py", ".wavefoundry/framework/scripts/tool.py", "yarn.lock"):
            with self.subTest(rel=rel):
                self.assertIsNotNone(srv._resolve_repo_path(self.root, rel))
                self.assertEqual(codenav_handlers.code_read_response(self.root, rel)["status"], "ok")

    def test_every_resolver_reader_refuses_the_lock(self) -> None:
        (self.root / ".wavefoundry/framework/scripts/held.lock").write_text("x = 1\n", encoding="utf-8")
        rel = ".wavefoundry/framework/scripts/held.lock"
        self.assert_refused(codenav_handlers.code_outline_response(self.root, rel))
        self.assert_refused(codenav_handlers.code_hover_response(self.root, rel, 1))
        self.assert_refused(codenav_handlers.code_dependencies_response(self.root, rel))
        self.assert_refused(graph_handlers._code_impact_heuristic_response(self.root, rel))

    def test_walker_mirror_agrees_with_the_server_predicate(self) -> None:
        idx = srv._indexer_module()
        cases = [
            LOCK_REL, ".wavefoundry/index/index-build.lock", ".wavefoundry/locks/a.lock",
            ".wavefoundry/framework/test-run.lock", ".WAVEFOUNDRY/X.LOCK", ".wavefoundry/a.lock.txt",
            "yarn.lock", "src/.wavefoundry/a.lock", ".wavefoundry/framework/scripts/tool.py",
        ]
        for rel in cases:
            path = self.root / rel
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
        # Hard links: one to a lock (refused), one between ordinary files (not).
        os.link(self.root / LOCK_REL, self.root / "src/hard.py")
        os.link(self.root / "src/app.py", self.root / "src/twin.py")
        cases += ["src/hard.py", "src/twin.py", "src/app.py"]
        for rel in cases:
            path = self.root / rel
            with self.subTest(rel=rel):
                self.assertEqual(
                    srv._is_runtime_lock_path(self.root, path.resolve()),
                    idx._walk_target_is_runtime_lock(path, self.root),
                )
        self.assertTrue(srv._is_runtime_lock_path(self.root, self.root / "src/hard.py"))
        self.assertFalse(srv._is_runtime_lock_path(self.root, self.root / "src/twin.py"))


class _HeldLockCase(_RepoCase):
    def setUp(self) -> None:
        super().setUp()
        self.lock_path = self.root / LOCK_REL

    def other_process_sees(self) -> str:
        out = subprocess.run(
            [sys.executable, "-B", "-c", _PROBE, str(self.lock_path),
             str(lifecycle_lock.LIFECYCLE_MUTATION_LOCK_SENTINEL)],
            capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL,
        )
        return out.stdout.strip()


@unittest.skipIf(os.name == "nt", "POSIX record-lock release semantics")
class HeldLifecycleLockTests(_HeldLockCase):
    """AC-1 and AC-3: a refused read leaves the in-process hold intact."""

    def test_code_read_of_the_held_lock_is_refused_and_the_hold_survives(self) -> None:
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            self.assertEqual(self.other_process_sees(), "held")
            self.assert_refused(codenav_handlers.code_read_response(self.root, LOCK_REL))
            self.assertEqual(self.other_process_sees(), "held")

    def test_symlink_to_the_held_lock_is_not_opened_by_walk_readers(self) -> None:
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            # notes.py takes the known-text path; notes.xyz takes the walker's sniff.
            # Created under the hold: since wave 1zv8c the acquisition refuses a
            # hold while such a link exists, and these readers are the backstop.
            for name in ("notes.py", "notes.xyz"):
                os.symlink(os.path.join(".wavefoundry", "lifecycle-mutation.lock"), self.root / name)
            self.assertEqual(self.other_process_sees(), "held")
            walked = {p.name for p in srv._indexer_module().walk_repo(self.root)}
            self.assertNotIn("notes.py", walked)
            self.assertNotIn("notes.xyz", walked)
            self.assertIn("app.py", walked)
            self.assertEqual(self.other_process_sees(), "held")
            keyword = codenav_handlers.code_keyword_response(self.root, "needle")
            self.assertEqual(keyword["status"], "ok", keyword)
            self.assertNotIn("notes.py", {r["path"] for r in keyword["data"]["results"]})
            self.assertEqual(self.other_process_sees(), "held")
            pattern = codenav_handlers.code_pattern_response(self.root, "pid|needle")
            self.assertEqual(pattern["status"], "ok", pattern)
            self.assertEqual(self.other_process_sees(), "held")
            # Index-derived reads (graph nodes, citations) go through the same rule.
            self.assertTrue(srv._repo_rel_path_refused(self.root, "notes.py"))
            self.assertEqual(graph_handlers._scan_call_sites_in_file(self.root, "app", "notes.py"), [])
            self.assertEqual(self.other_process_sees(), "held")

    def test_hard_link_to_the_held_lock_is_not_opened(self) -> None:
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            os.link(self.lock_path, self.root / "src/hard.py")
            os.link(self.root / "src/app.py", self.root / "src/twin.py")
            self.assertEqual(self.other_process_sees(), "held")
            self.assert_refused(codenav_handlers.code_read_response(self.root, "src/hard.py"))
            self.assert_refused(codenav_handlers.code_outline_response(self.root, "src/hard.py"))
            self.assertEqual(self.other_process_sees(), "held")
            walked = {p.name for p in srv._indexer_module().walk_repo(self.root)}
            self.assertNotIn("hard.py", walked)
            self.assertIn("twin.py", walked)
            keyword = codenav_handlers.code_keyword_response(self.root, "needle")
            self.assertEqual(keyword["status"], "ok", keyword)
            self.assertIn("src/twin.py", {r["path"] for r in keyword["data"]["results"]})
            self.assertEqual(self.other_process_sees(), "held")
            pattern = codenav_handlers.code_pattern_response(self.root, "pid|needle")
            self.assertEqual(pattern["status"], "ok", pattern)
            self.assertEqual(self.other_process_sees(), "held")
            self.assertEqual(graph_handlers._scan_call_sites_in_file(self.root, "app", "src/hard.py"), [])
            self.assertEqual(self.other_process_sees(), "held")
            # A hard link between two ordinary files still reads.
            self.assertEqual(codenav_handlers.code_read_response(self.root, "src/twin.py")["status"], "ok")


@unittest.skipIf(os.name == "nt", "POSIX record-lock release semantics")
class ReferenceCandidateFilterTests(_HeldLockCase):
    """code_references opens graph-named files; each filter keeps a lock out.

    A stale graph still names a lock as a candidate file, a retry candidate
    or a constant reader. ``hard.py`` is a hard link to the held lock (the
    reference readers skip a symlink themselves, since they compare the
    resolved path against the candidate set); ``notes.py`` is a symlink to it.
    """

    def setUp(self) -> None:
        super().setUp()
        refresh = patch.object(srv, "_graph_refresh_then_recheck", return_value=None)
        refresh.start()
        self.addCleanup(refresh.stop)

    def references(self, symbol: str, candidates) -> dict:
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            # Both links are made under the hold (wave 1zv8c refuses a hold
            # while one exists); the reference readers are the backstop.
            os.symlink(os.path.join(".wavefoundry", "lifecycle-mutation.lock"), self.root / "notes.py")
            os.link(self.lock_path, self.root / "hard.py")
            self.assertEqual(self.other_process_sees(), "held")
            with patch.object(codenav_handlers, "_graph_references_candidate_files", side_effect=candidates):
                response = codenav_handlers.code_references_response(self.root, symbol)
            self.assertEqual(self.other_process_sees(), "held")
        return response

    def test_first_candidate_filter(self) -> None:
        response = self.references("needle", lambda root, symbol: frozenset({"hard.py", "src/app.py"}))
        self.assertEqual(response["status"], "ok", response)

    def test_retry_candidate_filter(self) -> None:
        def candidates(root, symbol):
            return frozenset({"src/app.py"}) if "." in symbol else frozenset({"hard.py"})

        response = self.references("schema.zzzabsent", candidates)
        self.assertEqual(response["status"], "ok", response)

    def test_constant_reader_filter(self) -> None:
        index = SimpleNamespace(
            present=True,
            resolve_symbol=lambda symbol: "const",
            get_node=lambda node_id: (
                {"kind": "constant"} if node_id == "const"
                else {"source_file": "notes.py", "source_location": "1"}
            ),
            _in={"const": [{"relation": "reads", "source": "reader"}]},
        )
        graph_query = SimpleNamespace(get_query_index=lambda root, layer="project": index)
        with patch.object(srv, "_load_graph_query", return_value=graph_query):
            response = self.references("NEEDLE_CONST", lambda root, symbol: frozenset({"src/app.py"}))
        self.assertEqual(response["status"], "ok", response)


if __name__ == "__main__":
    unittest.main()
