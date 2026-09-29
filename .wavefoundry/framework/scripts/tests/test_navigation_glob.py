"""Navigation globs: ``**/`` matches zero or more directories (wave 1za2y, change 1z9ya)."""
from __future__ import annotations

import fnmatch
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from server_tools_support import _make_repo, load_server, load_thin_runner  # noqa: E402

SYMBOL = "GLOBPROBE_VALUE"
FILES = ("top.py", "A/direct.py", "A/b/nested.py", "A/b/c/deep.py", "B/other.py", "A/notes.txt")


def _old_filter(relpath: str, name: str, glob: str) -> bool:
    """The filter every navigation tool used before this change."""
    return fnmatch.fnmatch(relpath, glob) or fnmatch.fnmatch(name, glob)


class GlobMatcherTests(unittest.TestCase):
    def setUp(self):
        load_server()
        import wf_server.codenav_handlers as codenav_handlers
        self.match = codenav_handlers._glob_matches

    def test_double_star_matches_zero_or_more_directories(self):
        for relpath, glob in (
            ("A/direct.py", "A/**/*.py"),
            ("A/b/nested.py", "A/**/*.py"),
            ("top.py", "**/*.py"),
            ("a/b/y.py", "a/**/b/**/*.py"),
            ("a/x/b/y.py", "a/**/b/**/*.py"),
            ("top.py", "**/[t]op.py"),
            ("x.py", "**/[!]]*.py"),
            ("a/b/c.py", "**/a*c.py"),
        ):
            with self.subTest(relpath=relpath, glob=glob):
                self.assertTrue(self.match(relpath, relpath.rsplit("/", 1)[-1], glob))
        for relpath, glob in (
            ("B/direct.py", "A/**/*.py"), ("A/x.txt", "A/**/*.py"), ("a/sub.py", "a/**/b.py"),
            # Delivery repair: `**/` inside a segment is two stars, not zero directories.
            ("ab.py", "a**/b.py"), ("src/ab.py", "src/a**/b.py"),
            ("pop.py", "**/[t]op.py"), ("x.txt", "**/[!]]*.py"),
        ):
            with self.subTest(relpath=relpath, glob=glob):
                self.assertFalse(self.match(relpath, relpath.rsplit("/", 1)[-1], glob))

    def test_every_existing_form_matches_as_before(self):
        paths = list(FILES) + ["docs/a/b/x.md", "src/a/b.py", "src/b.py", "q/beta1.py", "a**b/x.py"]
        forms = ("*.py", "A/*.py", "docs/*.md", "*beta*", "A/b/nested.py", "src/**", "A/b/**", "a**b/*.py", "*")
        for glob in forms:
            for relpath in paths:
                name = relpath.rsplit("/", 1)[-1]
                with self.subTest(glob=glob, relpath=relpath):
                    self.assertEqual(self.match(relpath, name, glob), _old_filter(relpath, name, glob))

    def test_many_double_star_segments_stay_fast(self):
        glob = "/".join(["**"] * 40) + "/*.py"
        path = "/".join(["d"] * 60) + "/x.txt"
        started = time.perf_counter()
        self.assertFalse(self.match(path, "x.txt", glob))
        self.assertLess(time.perf_counter() - started, 1.0)


class GlobThroughToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        for rel in FILES:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{SYMBOL} = 1\n", encoding="utf-8")
        load_server()
        self.runner = load_thin_runner()
        self.mcp = self.runner.build_server(self.root)
        self.addCleanup(lambda: self.runner._get_handler().close())

    def call(self, name, **args):
        return self.mcp._tool_manager._tools[name].fn(**args)

    def assert_files(self, result, expected, unexpected):
        text = repr(result.get("data"))
        for rel in expected:
            self.assertIn(rel, text, result)
        for rel in unexpected:
            self.assertNotIn(rel, text, result)

    def test_each_tool_includes_direct_and_nested_files(self):
        glob = "A/**/*.py"
        expected = ("A/direct.py", "A/b/nested.py", "A/b/c/deep.py")
        unexpected = ("top.py", "B/other.py", "A/notes.txt")
        for name, args in (
            ("code_list_files", {"glob": glob}),
            ("code_keyword", {"query": SYMBOL, "glob": glob}),
            ("code_constants", {"symbols": [SYMBOL], "glob": glob}),
            ("code_pattern", {"pattern": SYMBOL, "glob": glob}),
        ):
            with self.subTest(tool=name):
                self.assert_files(self.call(name, **args), expected, unexpected)

    def test_leading_double_star_includes_a_root_file(self):
        result = self.call("code_list_files", glob="**/*.py")
        self.assert_files(result, ("top.py", "A/direct.py", "B/other.py"), ("A/notes.txt",))


if __name__ == "__main__":
    unittest.main()
