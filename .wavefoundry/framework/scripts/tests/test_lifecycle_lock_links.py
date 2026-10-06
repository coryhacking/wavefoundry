"""Wave 1zv8c (1zv8b): lifecycle-lock acquisition refuses a hold that an
in-process reader could release through a link to the lock file.

On macOS and Linux the lifecycle lock is a POSIX record lock, which the holding
process loses when it closes any descriptor of the file. These tests pin the
acquisition check: a symlink to a runtime lock in the scanned trees, a hard link
to the lock file, and a record-root directory link leading outside the
repository are refused; ordinary links are not.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from server_tools_support import load_server  # noqa: E402
from record_layout_support import RecordTreeBuilder  # noqa: E402

srv = load_server()
# The module identities the server and the CLI entry points resolve at call time.
lifecycle_lock = srv._lifecycle_lock_authority
runtime_lock = sys.modules[lifecycle_lock.RuntimeFileLock.__module__]
record_paths = lifecycle_lock.record_paths

LOCK_REL = ".wavefoundry/lifecycle-mutation.lock"

_PROBE_CHILD = (
    "import sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from pathlib import Path\n"
    "import lifecycle_lock, runtime_lock\n"
    "probe = runtime_lock.probe_runtime_lock(\n"
    "    Path(sys.argv[2]) / lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL,\n"
    "    offset=lifecycle_lock.LIFECYCLE_MUTATION_LOCK_SENTINEL, style='record')\n"
    "print('held' if probe.held else ('free' if probe.held is False else 'unknown'), flush=True)\n"
)


def _symlink(target: "str | Path", link: Path, *, directory: bool = False) -> None:
    """A relative link at ``link``; a ``Path`` target is made relative to its parent."""
    link.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(target, Path):
        target = os.path.relpath(target, link.parent)
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        raise unittest.SkipTest(f"symlinks unavailable here: {exc}")


class _LinkCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / ".wavefoundry").mkdir()
        builder = RecordTreeBuilder(self.root)
        self.waves, self.plans = builder.waves_dir, builder.plans_dir
        self.wave = self.waves / "1abcd wave"
        self.wave.mkdir(parents=True)
        (self.wave / "record.md").write_text("# Wave\n", encoding="utf-8")
        self.plans.mkdir(parents=True, exist_ok=True)
        self.lock = self.root / LOCK_REL
        self.lock.write_text("{}\n", encoding="utf-8")

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def acquire(self) -> list[str]:
        """Enter the lock; return ``["ran"]`` when the body ran."""
        ran: list[str] = []
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            ran.append("ran")
        return ran

    def refused(self) -> lifecycle_lock.LifecycleLockLinkRefused:
        ran: list[str] = []
        with self.assertRaises(lifecycle_lock.LifecycleLockLinkRefused) as caught:
            with lifecycle_lock.lifecycle_mutation_lock(self.root):
                ran.append("ran")
        self.assertEqual(ran, [])
        self.assertIsNone(runtime_lock.process_hold(self.lock))
        self.assertEqual(caught.exception.lock_rel, LOCK_REL)
        text = str(caught.exception)
        self.assertNotIn(str(self.root), text)
        self.assertNotIn(os.path.realpath(self.root), text)
        return caught.exception

    def assert_lock_free_for_another_process(self) -> None:
        if os.name == "nt":
            return  # The child probe pins POSIX record-lock release.
        out = subprocess.run(
            [sys.executable, "-B", "-c", _PROBE_CHILD, str(SCRIPTS_ROOT), str(self.root)],
            capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
        )
        self.assertEqual(out.stdout.strip(), "free", out.stderr[-2000:])


class SymlinkRefusalTests(_LinkCase):
    def test_markdown_symlink_in_a_record_root_is_refused_and_released(self) -> None:
        _symlink(self.lock, self.wave / "notes.md")
        exc = self.refused()
        self.assertEqual(exc.link_rel, self.rel(self.wave / "notes.md"))
        self.assertEqual(exc.cause, "lock_link")
        self.assertIn("remove the link", str(exc))
        self.assert_lock_free_for_another_process()

    def test_symlink_reached_through_an_in_repo_directory_link_is_refused(self) -> None:
        shared = self.root / "records/shared"
        shared.mkdir(parents=True)
        _symlink(self.lock, shared / "notes.md")
        _symlink(shared, self.waves / "1efgh linked", directory=True)
        exc = self.refused()
        self.assertEqual(exc.link_rel, self.rel(self.waves / "1efgh linked/notes.md"))
        self.assert_lock_free_for_another_process()

    def test_any_runtime_lock_target_is_refused(self) -> None:
        index_lock = self.root / ".wavefoundry/index/index-build.lock"
        index_lock.parent.mkdir()
        index_lock.write_text("{}\n", encoding="utf-8")
        _symlink(index_lock, self.plans / "p.md")
        self.assertEqual(self.refused().link_rel, self.rel(self.plans / "p.md"))

    def test_root_level_markdown_link_is_refused(self) -> None:
        _symlink(".wavefoundry/lifecycle-mutation.lock", self.root / "AGENTS.md")
        self.assertEqual(self.refused().link_rel, "AGENTS.md")

    def test_docs_outside_the_record_roots_is_scanned(self) -> None:
        _symlink(self.lock, self.root / "docs/agents/memory/m.md")
        self.assertEqual(self.refused().link_rel, "docs/agents/memory/m.md")

    def test_archive_root_is_scanned(self) -> None:
        _symlink(self.lock, self.root / "history/old/notes.md")
        self.assertEqual(self.acquire(), ["ran"])  # no archive configured
        with patch.object(record_paths, "ARCHIVE_ROOT", "history"):
            self.assertEqual(self.refused().link_rel, "history/old/notes.md")

    def test_case_variant_target_is_refused_on_a_case_insensitive_volume(self) -> None:
        probe = self.root / ".WAVEFOUNDRY"
        if not probe.exists():
            self.skipTest("case-sensitive volume")
        _symlink(self.root / ".WAVEFOUNDRY/Lifecycle-Mutation.LOCK", self.wave / "case.md")
        self.assertEqual(self.refused().link_rel, self.rel(self.wave / "case.md"))

    def test_a_removed_link_is_accepted_again(self) -> None:
        link = self.wave / "notes.md"
        _symlink(self.lock, link)
        self.refused()
        link.unlink()
        self.assertEqual(self.acquire(), ["ran"])


class HardLinkRefusalTests(_LinkCase):
    def test_hard_link_to_the_lock_is_refused_and_a_fresh_lock_is_accepted(self) -> None:
        try:
            os.link(self.lock, self.root / "docs/hard.md")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"hard links unavailable here: {exc}")
        exc = self.refused()
        self.assertEqual(exc.cause, "hard_link")
        self.assertIsNone(exc.link_rel)
        self.assertIn("hard links", str(exc))
        self.assert_lock_free_for_another_process()
        (self.root / "docs/hard.md").unlink()
        self.lock.unlink()  # recreated by the next acquire, link count 1
        self.assertEqual(self.acquire(), ["ran"])

    def test_a_missing_lock_file_is_created_and_accepted(self) -> None:
        self.lock.unlink()
        self.assertEqual(self.acquire(), ["ran"])


class AcceptedLinkTests(_LinkCase):
    def test_ordinary_file_and_directory_links_are_accepted(self) -> None:
        (self.root / "src").mkdir()
        (self.root / "src/readme.md").write_text("x\n", encoding="utf-8")
        _symlink(self.root / "src/readme.md", self.wave / "readme.md")
        _symlink(self.root / "src", self.waves / "1src", directory=True)
        _symlink(self.root / "src/missing.md", self.plans / "dangling.md")
        _symlink("yarn.lock", self.root / "docs/lockish.lock")
        self.assertEqual(self.acquire(), ["ran"])

    def test_a_directory_cycle_ends(self) -> None:
        _symlink("..", self.wave / "up", directory=True)
        _symlink(self.root / "docs", self.plans / "loop", directory=True)
        # Each resolved directory is listed once; a walk that re-entered the
        # cycle would only stop at the OS link-depth limit, far past this bound.
        with patch.object(lifecycle_lock, "_LINK_SCAN_ENTRY_LIMIT", 40):
            self.assertEqual(self.acquire(), ["ran"])

    def test_outside_directory_link_outside_record_roots_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            _symlink(outside, self.root / "docs/vendor", directory=True)
            self.assertEqual(self.acquire(), ["ran"])


class BoundTests(_LinkCase):
    def test_record_root_directory_link_outside_the_repository_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            _symlink(outside, self.waves / "1out wave", directory=True)
            exc = self.refused()
        self.assertEqual(exc.cause, "outside_link")
        self.assertEqual(exc.link_rel, self.rel(self.waves / "1out wave"))
        self.assertNotIn(os.path.realpath(outside), str(exc))
        self.assert_lock_free_for_another_process()

    def test_a_link_high_up_the_tree_hits_the_entry_bound(self) -> None:
        bulk = self.root / "src/bulk"
        bulk.mkdir(parents=True)
        for index in range(80):
            (bulk / f"f{index}.txt").write_text("", encoding="utf-8")
        with patch.object(lifecycle_lock, "_LINK_SCAN_ENTRY_LIMIT", 60):
            self.assertEqual(self.acquire(), ["ran"])  # src is not scanned
            _symlink(self.root, self.waves / "1top", directory=True)
            exc = self.refused()
        self.assertEqual(exc.cause, "link_scan_limit")
        self.assert_lock_free_for_another_process()

    def test_git_and_a_venv_are_not_entered_and_the_index_is_not_counted(self) -> None:
        for rel in (".git/objects", ".wavefoundry/venv/lib", ".wavefoundry/index/shards"):
            folder = self.root / rel
            folder.mkdir(parents=True)
            for index in range(80):
                (folder / f"f{index}").write_text("", encoding="utf-8")
        _symlink(self.root, self.waves / "1top", directory=True)
        with patch.object(lifecycle_lock, "_LINK_SCAN_ENTRY_LIMIT", 60):
            self.assertEqual(self.acquire(), ["ran"])


class SpellingVariantTests(_LinkCase):
    """DEL-1: the root is matched by identity, so another spelling of the
    checkout (or an ancestor) in a link target is still judged a lock."""

    def variant_root(self) -> Path:
        spelled = self.root.parent / self.root.name.swapcase()
        if spelled.name == self.root.name or not spelled.exists():
            self.skipTest("case-sensitive volume")
        return spelled

    def test_ancestor_case_variant_target_is_refused(self) -> None:
        spelled = self.variant_root()
        _symlink(str(spelled / LOCK_REL), self.wave / "notes.md")
        self.assertEqual(self.refused().link_rel, self.rel(self.wave / "notes.md"))
        self.assert_lock_free_for_another_process()

    def test_unicode_normalisation_variant_target_is_refused(self) -> None:
        import unicodedata

        nfc = unicodedata.normalize("NFC", "caf\u00e9")
        nfd = unicodedata.normalize("NFD", nfc)
        repo = self.root / nfc
        (repo / ".wavefoundry").mkdir(parents=True)
        lock = repo / LOCK_REL
        lock.write_text("{}\n", encoding="utf-8")
        if not (self.root / nfd / LOCK_REL).exists():
            self.skipTest("volume does not normalise Unicode names")
        waves = RecordTreeBuilder(repo).waves_dir
        _symlink(str(self.root / nfd / LOCK_REL), waves / "1abcd wave/notes.md")
        with self.assertRaises(lifecycle_lock.LifecycleLockLinkRefused):
            with lifecycle_lock.lifecycle_mutation_lock(repo):
                self.fail("the body ran")

    def test_the_held_identity_catches_a_link_the_name_test_misses(self) -> None:
        _symlink(self.lock, self.wave / "notes.md")
        with patch.object(lifecycle_lock, "is_runtime_lock_path", return_value=False):
            self.assertEqual(self.refused().cause, "lock_link")

    def test_a_case_variant_directory_link_is_inside_the_repository(self) -> None:
        spelled = self.variant_root()
        (self.root / "records").mkdir()
        _symlink(str(spelled / "records"), self.waves / "1case wave", directory=True)
        self.assertEqual(self.acquire(), ["ran"])

    def test_readers_judge_a_case_variant_root_spelling(self) -> None:
        spelled = self.variant_root()
        target = spelled / LOCK_REL
        root = Path(os.path.realpath(self.root))
        self.assertTrue(runtime_lock.is_runtime_lock_path(root, target))
        self.assertTrue(srv._is_runtime_lock_path(root, target))
        link = self.root / "src/notes.py"
        _symlink(str(target), link)
        self.assertTrue(srv._indexer_module()._walk_target_is_runtime_lock(link, self.root))


class FrameworkTreeTests(_LinkCase):
    """DEL-2: the close gate hashes ``.wavefoundry/framework/`` in-process."""

    def test_a_link_in_the_framework_tree_is_refused(self) -> None:
        _symlink(self.lock, self.root / ".wavefoundry/framework/scripts/held.py")
        self.assertEqual(self.refused().link_rel, ".wavefoundry/framework/scripts/held.py")

    def test_a_link_among_the_state_files_is_refused(self) -> None:
        _symlink(self.lock, self.root / ".wavefoundry/guard-overrides.json")
        self.assertEqual(self.refused().link_rel, ".wavefoundry/guard-overrides.json")


class WavefoundryTreeTests(_LinkCase):
    """DEL-7: in-process readers under the lock open files throughout
    ``.wavefoundry/`` (the guard-skip ledger under the index, the
    context-efficiency store under ``logs/``), so all of it is scanned except a
    project-local virtual environment."""

    def test_a_link_at_the_guard_skip_ledger_is_refused(self) -> None:
        import scanner_skips

        _symlink(self.lock, self.root / scanner_skips.LEDGER_REL)
        self.assertEqual(self.refused().link_rel, scanner_skips.LEDGER_REL)
        self.assert_lock_free_for_another_process()

    def test_a_link_at_the_context_efficiency_store_is_refused(self) -> None:
        import context_efficiency

        rel = context_efficiency.STORE_RELATIVE_PATH.as_posix()
        _symlink(self.lock, self.root / rel)
        self.assertEqual(self.refused().link_rel, rel)

    def test_a_link_anywhere_else_under_wavefoundry_is_refused(self) -> None:
        for rel in (".wavefoundry/bin/wf-held", ".wavefoundry/locks-adjacent/deep/x.json"):
            with self.subTest(rel=rel):
                link = self.root / rel
                _symlink(self.lock, link)
                self.assertEqual(self.refused().link_rel, rel)
                link.unlink()

    def test_a_venv_is_not_scanned(self) -> None:
        _symlink(self.lock, self.root / ".wavefoundry/venv/lib/held.py")
        _symlink(self.lock, self.root / ".wavefoundry/venv/bin/python-held")
        self.assertEqual(self.acquire(), ["ran"])


class PnpmLayoutTests(_LinkCase):
    """DEL-8: directory links into a tree the real walk lists cost nothing."""

    def test_a_pnpm_layout_is_accepted_whatever_the_order(self) -> None:
        modules = self.root / "docs/node_modules"
        for index in range(6):
            name = f"pkg{index}"
            real = modules / ".pnpm" / f"{name}@1.0.0" / "node_modules" / name
            real.mkdir(parents=True)
            for leaf in range(15):  # 90 real files, each reachable both ways
                (real / f"f{leaf}.js").write_text("", encoding="utf-8")
            _symlink(real, modules / name, directory=True)
            # A sibling link inside .pnpm, as pnpm writes for dependencies.
            _symlink(real, real.parent / f"dep{index}", directory=True)
        with patch.object(lifecycle_lock, "_LINK_SCAN_ENTRY_LIMIT", 50):
            self.assertEqual(self.acquire(), ["ran"])
            # A further link into the already-listed tree, from a record root,
            # costs nothing either.
            _symlink(modules, self.waves / "1mods", directory=True)
            self.assertEqual(self.acquire(), ["ran"])

    def test_a_link_only_large_tree_still_hits_the_bound(self) -> None:
        bulk = self.root / "vendor/pkg"
        bulk.mkdir(parents=True)
        for index in range(80):
            (bulk / f"f{index}.js").write_text("", encoding="utf-8")
        _symlink(bulk, self.root / "docs/node_modules/pkg", directory=True)
        with patch.object(lifecycle_lock, "_LINK_SCAN_ENTRY_LIMIT", 50):
            self.assertEqual(self.refused().cause, "link_scan_limit")

    def test_a_lock_link_inside_a_link_target_is_still_refused(self) -> None:
        bulk = self.root / "vendor/pkg"
        bulk.mkdir(parents=True)
        _symlink(self.lock, bulk / "held.js")
        _symlink(bulk, self.root / "docs/node_modules/pkg", directory=True)
        self.assertEqual(self.refused().link_rel, "docs/node_modules/pkg/held.js")


    def test_a_link_nested_inside_a_followed_link_is_followed_and_counted(self) -> None:
        inner = self.root / "vendor/inner"
        inner.mkdir(parents=True)
        for index in range(30):
            (inner / f"f{index}.js").write_text("", encoding="utf-8")
        outer = self.root / "src/outer"
        outer.mkdir(parents=True)
        for index in range(30):
            (outer / f"f{index}.js").write_text("", encoding="utf-8")
        _symlink(inner, outer / "inner", directory=True)
        _symlink(outer, self.root / "docs/node_modules/outer", directory=True)
        with patch.object(lifecycle_lock, "_LINK_SCAN_ENTRY_LIMIT", 50):
            self.assertEqual(self.refused().cause, "link_scan_limit")
        _symlink(self.lock, inner / "held.js")
        self.assertEqual(self.refused().link_rel, "docs/node_modules/outer/inner/held.js")

class ScanShapeTests(_LinkCase):
    def test_a_large_real_tree_is_not_counted(self) -> None:
        # DEL-3: only entries reached through directory links count.
        bulk = self.root / "docs/node_modules/pkg"
        bulk.mkdir(parents=True)
        for index in range(80):
            (bulk / f"f{index}.js").write_text("", encoding="utf-8")
        with patch.object(lifecycle_lock, "_LINK_SCAN_ENTRY_LIMIT", 60):
            self.assertEqual(self.acquire(), ["ran"])

    def test_the_bound_remedy_names_directory_links(self) -> None:
        _symlink(self.root, self.waves / "1top", directory=True)
        bulk = self.root / "src"
        bulk.mkdir()
        for index in range(80):
            (bulk / f"f{index}.txt").write_text("", encoding="utf-8")
        with patch.object(lifecycle_lock, "_LINK_SCAN_ENTRY_LIMIT", 60):
            exc = self.refused()
        self.assertIn("through directory links", str(exc))
        self.assertIn("replace or remove that directory link", str(exc))

    def test_a_non_string_waves_root_is_not_scanned_as_the_repository(self) -> None:
        # DEL-4: an unusable layout constant must not make the whole checkout a record root.
        with tempfile.TemporaryDirectory() as outside:
            _symlink(outside, self.root / "src/vendor", directory=True)
            with patch.object(record_paths, "WAVES_ROOT", None):
                self.assertEqual(self.acquire(), ["ran"])

    def test_a_windows_junction_is_a_link_without_is_junction(self) -> None:
        # DEL-4: Python 3.11 has no DirEntry.is_junction; the reparse tag decides.
        class _Entry:
            def __init__(self, tag):
                self.tag = tag

            def is_symlink(self):
                return False

            def stat(self, follow_symlinks=True):
                return SimpleNamespace(st_reparse_tag=self.tag)

        with patch.object(lifecycle_lock.os, "name", "nt"):
            self.assertTrue(lifecycle_lock._is_link_entry(_Entry(0xA0000003)))
            self.assertFalse(lifecycle_lock._is_link_entry(_Entry(0x9000001A)))  # cloud placeholder
            self.assertFalse(lifecycle_lock._is_link_entry(_Entry(0)))


class SharedPredicateTests(unittest.TestCase):
    def test_shared_predicate_cases(self) -> None:
        root = Path("/repo")
        for rel, expected in (
            (LOCK_REL, True),
            (".wavefoundry/index/index-build.lock", True),
            (".WAVEFOUNDRY/X.LOCK", True),
            (".wavefoundry/a.lock.txt", False),
            ("yarn.lock", False),
            ("src/.wavefoundry/a.lock", False),
            (".wavefoundry", False),
        ):
            with self.subTest(rel=rel):
                self.assertIs(runtime_lock.is_runtime_lock_path(root, root / rel), expected)
                self.assertIs(runtime_lock.is_runtime_lock_path(str(root), str(root / rel)), expected)
        self.assertFalse(runtime_lock.is_runtime_lock_path(root, Path("/elsewhere/.wavefoundry/a.lock")))

    def test_runtime_lock_stays_stdlib_only(self) -> None:
        import ast

        tree = ast.parse((SCRIPTS_ROOT / "runtime_lock.py").read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names.add(node.module.split(".")[0])
        self.assertLessEqual(names, set(sys.stdlib_module_names) | {"__future__"}, names)

    def test_server_and_walker_use_the_shared_predicate(self) -> None:
        idx = srv._indexer_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            target = root / LOCK_REL
            target.parent.mkdir()
            target.write_text("", encoding="utf-8")
            # The server reaches the helper through lifecycle_lock (a reload
            # never purges runtime_lock); the walker imports it at call time.
            self.assertIs(lifecycle_lock.is_runtime_lock_path, runtime_lock.is_runtime_lock_path)
            with patch.object(lifecycle_lock, "is_runtime_lock_path", return_value=False), \
                    patch.object(runtime_lock, "is_runtime_lock_path", return_value=False):
                self.assertFalse(srv._is_runtime_lock_path(root, target))
                self.assertFalse(idx._walk_target_is_runtime_lock(target, root))
            self.assertTrue(srv._is_runtime_lock_path(root, target))
            self.assertTrue(idx._walk_target_is_runtime_lock(target, root))


class ServerRefusalTests(_LinkCase):
    def _wrapped(self, tool_name, fn):
        class _Tool: ...
        class _TM: ...
        class _MCP: ...
        tool = _Tool(); tool.fn = fn
        tm = _TM(); tm._tools = {tool_name: tool}
        mcp = _MCP(); mcp._tool_manager = tm
        handler = SimpleNamespace(root=self.root)
        srv._wrap_lifecycle_mutation_lock(mcp, lambda: handler)
        return tool.fn

    def _assert_path_free(self, result) -> None:
        text = json.dumps(result)
        for absolute in {str(self.root), os.path.realpath(self.root)}:
            self.assertNotIn(absolute, text)
            self.assertNotIn(json.dumps(absolute)[1:-1], text)

    def test_lifecycle_tool_refuses_with_the_link_code_and_writes_nothing(self) -> None:
        _symlink(self.lock, self.wave / "notes.md")
        before = (self.wave / "record.md").read_bytes()
        called = []
        result = self._wrapped("wf_close_wave", lambda **kw: called.append(kw))()
        self.assertEqual(called, [])
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["lifecycle_lock_link_refused"])
        self.assertIs(result["data"]["mutation_applied"], False)
        self.assertEqual(result["data"]["link"], self.rel(self.wave / "notes.md"))
        message = result["diagnostics"][0]["message"]
        self.assertIn(self.rel(self.wave / "notes.md"), message)
        self.assertIn("Remove the link", message)
        self.assertEqual((self.wave / "record.md").read_bytes(), before)
        self._assert_path_free(result)
        self.assert_lock_free_for_another_process()

    def test_hard_link_refusal_names_the_remedy(self) -> None:
        try:
            os.link(self.lock, self.root / "docs/hard.md")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"hard links unavailable here: {exc}")
        result = self._wrapped("wf_set_handoff", lambda **kw: {"status": "ok"})()
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["lifecycle_lock_link_refused"])
        self.assertIn("hard link", result["diagnostics"][0]["message"])
        self._assert_path_free(result)

    def test_bound_refusal_names_directory_links(self) -> None:
        _symlink(self.root, self.waves / "1top", directory=True)
        (self.root / "src").mkdir()
        for index in range(80):
            (self.root / f"src/f{index}.txt").write_text("", encoding="utf-8")
        with patch.object(lifecycle_lock, "_LINK_SCAN_ENTRY_LIMIT", 60):
            result = self._wrapped("wf_set_handoff", lambda **kw: {"status": "ok"})()
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["lifecycle_lock_link_refused"])
        self.assertIn("through directory links", result["diagnostics"][0]["message"])
        self._assert_path_free(result)

    def test_from_lock_refusal_kind(self) -> None:
        exc = lifecycle_lock.LifecycleLockLinkRefused(
            "x", lock_rel=LOCK_REL, link_rel="docs/a.md", cause="lock_link")
        busy = srv.LifecycleMutationBusy.from_lock_refusal(exc)
        self.assertEqual((busy.kind, busy.link_rel, busy.cause), ("link_refused", "docs/a.md", "lock_link"))
        plain = srv.LifecycleMutationBusy.from_lock_refusal(
            lifecycle_lock.LifecycleLockUnavailable("x", lock_rel=LOCK_REL))
        self.assertEqual(plain.kind, "unavailable")


class SetupAndUpgradeReportingTests(_LinkCase):
    def setUp(self) -> None:
        super().setUp()
        _symlink(self.lock, self.wave / "notes.md")

    def test_setup_reconciliation_reports_the_link_refusal(self) -> None:
        import setup_reconciliation
        import sqlite_storage_migration as migration

        framework = self.root / ".wavefoundry/framework"
        framework.mkdir(parents=True)
        (framework / "VERSION").write_text("1.24.0")
        (self.root / ".wavefoundry/index").mkdir()
        with patch.object(migration, "discover_hosts", return_value=([], [])):
            with self.assertRaises(setup_reconciliation.MigrationRequired) as caught:
                with setup_reconciliation.session(self.root, []):
                    self.fail("setup ran under a refused lock")
        message = str(caught.exception)
        self.assertTrue(message.startswith("lifecycle_lock_link_refused: "), message)
        self.assertIn(self.rel(self.wave / "notes.md"), message)
        self.assertNotIn("storage_setup_busy", message)
        self.assert_lock_free_for_another_process()

    def _upgrade(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPTS_ROOT / "upgrade_wavefoundry.py"), "--root", str(self.root), *extra],
            capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL,
        )

    def test_upgrade_lock_sites_report_the_link_refusal_without_a_traceback(self) -> None:
        for extra in (("--yes",), ("--update-index",)):
            with self.subTest(extra=extra):
                out = self._upgrade(*extra)
                self.assertIn(
                    "ERROR: lifecycle_lock_link_refused: lifecycle mutation lock "
                    f"{LOCK_REL} refused: {self.rel(self.wave / 'notes.md')}",
                    out.stderr,
                )
                self.assertNotIn("upgrade_in_progress", out.stderr)
                self.assertNotIn("Traceback", out.stderr + out.stdout)
                self.assertEqual(out.returncode, 3, out.stderr[-2000:])

    def test_upgrade_refusal_wording(self) -> None:
        import upgrade_wavefoundry

        link = lifecycle_lock.LifecycleLockLinkRefused("lifecycle mutation lock refused: docs/a.md")
        busy = lifecycle_lock.LifecycleLockBusy("lifecycle mutation lock is held")
        self.assertEqual(
            upgrade_wavefoundry._strict_transaction_refusal(link),
            "lifecycle_lock_link_refused: lifecycle mutation lock refused: docs/a.md",
        )
        self.assertTrue(
            upgrade_wavefoundry._strict_transaction_refusal(busy).startswith(
                "upgrade_in_progress: cannot acquire strict upgrade transaction: "
            )
        )


if __name__ == "__main__":
    unittest.main()
