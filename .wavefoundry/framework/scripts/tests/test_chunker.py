from __future__ import annotations

import importlib.util
import sys
import textwrap
import unittest
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
CHUNKER_PATH = SCRIPTS_ROOT / "chunker.py"


def load_chunker():
    spec = importlib.util.spec_from_file_location("chunker", CHUNKER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["chunker"] = mod
    spec.loader.exec_module(mod)
    return mod


class ChunkDataclassTests(unittest.TestCase):
    def setUp(self):
        self.chunker = load_chunker()

    def test_chunk_has_required_fields(self):
        c = self.chunker.Chunk(
            id="src/foo.py::my_func",
            path="src/foo.py",
            kind="code",
            language="python",
            lines=(1, 5),
            section=None,
            text="def my_func():\n    pass\n",
        )
        self.assertEqual(c.id, "src/foo.py::my_func")
        self.assertEqual(c.path, "src/foo.py")
        self.assertEqual(c.kind, "code")
        self.assertEqual(c.language, "python")
        self.assertEqual(c.lines, (1, 5))
        self.assertIsNone(c.section)
        self.assertIn("my_func", c.text)

    def test_chunk_to_dict(self):
        c = self.chunker.Chunk(
            id="docs/foo.md#intro",
            path="docs/foo.md",
            kind="doc",
            language=None,
            lines=(1, 3),
            section="Intro",
            text="Some text.",
        )
        d = c.to_dict()
        self.assertEqual(d["id"], "docs/foo.md#intro")
        self.assertEqual(d["path"], "docs/foo.md")
        self.assertEqual(d["kind"], "doc")
        self.assertIsNone(d["language"])
        self.assertEqual(d["lines"], [1, 3])
        self.assertEqual(d["section"], "Intro")
        self.assertEqual(d["text"], "Some text.")


class PythonChunkerTests(unittest.TestCase):
    def setUp(self):
        self.chunker = load_chunker()

    def _chunks(self, source: str, path: str = "src/foo.py") -> list:
        return self.chunker.chunk_python(source, path)

    def test_top_level_function(self):
        source = textwrap.dedent("""\
            def greet(name):
                return f"hello {name}"
        """)
        chunks = self._chunks(source)
        self.assertEqual(len(chunks), 1)
        c = chunks[0]
        self.assertEqual(c.id, "src/foo.py::greet")
        self.assertEqual(c.kind, "code")
        self.assertEqual(c.language, "python")
        self.assertIn("greet", c.text)

    def test_class_with_methods(self):
        source = textwrap.dedent("""\
            class MyClass:
                def __init__(self):
                    self.x = 1

                def compute(self):
                    return self.x * 2
        """)
        chunks = self._chunks(source)
        ids = [c.id for c in chunks]
        self.assertIn("src/foo.py::MyClass", ids)
        self.assertIn("src/foo.py::MyClass.__init__", ids)
        self.assertIn("src/foo.py::MyClass.compute", ids)

    def test_module_docstring_is_doc_kind(self):
        source = textwrap.dedent("""\
            \"\"\"Module that does things.\"\"\"

            def foo():
                pass
        """)
        chunks = self._chunks(source)
        kinds = {c.kind for c in chunks}
        self.assertIn("doc", kinds)
        self.assertIn("code", kinds)

    def test_function_with_docstring_splits_doc_and_code(self):
        source = textwrap.dedent("""\
            def compute(x):
                \"\"\"Return x squared.\"\"\"
                return x * x
        """)
        chunks = self._chunks(source)
        kinds = [c.kind for c in chunks]
        self.assertIn("doc", kinds)
        self.assertIn("code", kinds)

    def test_empty_file_returns_no_chunks(self):
        self.assertEqual(self._chunks(""), [])

    def test_syntax_error_falls_back_to_line_window(self):
        source = "def broken(\n    pass\n"
        chunks = self._chunks(source)
        self.assertTrue(len(chunks) >= 1)
        for c in chunks:
            self.assertEqual(c.language, "python")

    def test_line_numbers_are_one_indexed(self):
        source = textwrap.dedent("""\
            def first():
                pass

            def second():
                pass
        """)
        chunks = self._chunks(source)
        for c in chunks:
            self.assertGreaterEqual(c.lines[0], 1)
            self.assertGreaterEqual(c.lines[1], c.lines[0])

    def test_path_is_preserved_normalized(self):
        source = "def f(): pass\n"
        chunks = self.chunker.chunk_python(source, "src/sub/foo.py")
        self.assertTrue(all("src/sub/foo.py" in c.path for c in chunks))

    def test_chunk_file_splits_large_python_code_chunks(self):
        source = "def huge():\n" + "\n".join(
            f"    value_{i} = '{'x' * 120}'" for i in range(120)
        )
        chunks = self.chunker.chunk_file(source, "src/huge.py")
        code_chunks = [c for c in chunks if c.kind == "code"]

        self.assertGreater(len(code_chunks), 1)
        self.assertTrue(all(len(c.text) <= self.chunker.MAX_CODE_CHUNK_CHARS for c in code_chunks))
        self.assertTrue(all("src/huge.py::huge:L" in c.id for c in code_chunks))


class MarkdownChunkerTests(unittest.TestCase):
    def setUp(self):
        self.chunker = load_chunker()

    def _chunks(self, source: str, path: str = "docs/foo.md") -> list:
        return self.chunker.chunk_markdown(source, path)

    def test_sections_split_on_h2(self):
        source = textwrap.dedent("""\
            # Title

            Intro text.

            ## Section One

            Content one.

            ## Section Two

            Content two.
        """)
        chunks = self._chunks(source)
        sections = [c.section for c in chunks]
        self.assertIn("Section One", sections)
        self.assertIn("Section Two", sections)

    def test_id_uses_slugified_section(self):
        source = "## How Does Prepare Wave Work\n\nContent.\n"
        chunks = self._chunks(source)
        self.assertEqual(len(chunks), 1)
        self.assertIn("how-does-prepare-wave-work", chunks[0].id)

    def test_kind_is_doc(self):
        source = "## Intro\n\nSome content.\n"
        chunks = self._chunks(source)
        self.assertTrue(all(c.kind == "doc" for c in chunks))

    def test_language_is_none(self):
        source = "## Intro\n\nSome content.\n"
        chunks = self._chunks(source)
        self.assertTrue(all(c.language is None for c in chunks))

    def test_fenced_code_block_is_code_kind(self):
        source = textwrap.dedent("""\
            ## Usage

            Some prose.

            ```python
            def foo():
                pass
            ```
        """)
        chunks = self._chunks(source)
        kinds = {c.kind for c in chunks}
        self.assertIn("code", kinds)
        self.assertIn("doc", kinds)

    def test_empty_file_returns_no_chunks(self):
        self.assertEqual(self._chunks(""), [])

    def test_title_only_file(self):
        source = "# Just A Title\n"
        chunks = self._chunks(source)
        # title with no body may produce zero or one chunk — just don't crash
        self.assertIsInstance(chunks, list)


class SeedChunkerTests(unittest.TestCase):
    def setUp(self):
        self.chunker = load_chunker()

    def test_seed_kind(self):
        source = "# Plan Feature\n\nDo this and that.\n"
        chunks = self.chunker.chunk_markdown(
            source,
            ".wavefoundry/framework/seeds/020-plan-feature.prompt.md",
            kind_override="seed",
        )
        self.assertTrue(all(c.kind == "seed" for c in chunks))


class LineWindowChunkerTests(unittest.TestCase):
    def setUp(self):
        self.chunker = load_chunker()

    def _chunks(self, source: str, path: str = "src/foo.js") -> list:
        return self.chunker.chunk_line_window(source, path, language="javascript")

    def test_produces_chunks(self):
        source = "\n".join(f"line {i}" for i in range(1, 60))
        chunks = self._chunks(source)
        self.assertTrue(len(chunks) >= 1)

    def test_id_uses_line_range(self):
        source = "\n".join(f"line {i}" for i in range(1, 10))
        chunks = self._chunks(source)
        for c in chunks:
            self.assertRegex(c.id, r"src/foo\.js:L\d+-L\d+")

    def test_kind_is_code(self):
        source = "const x = 1;\n" * 10
        chunks = self._chunks(source)
        self.assertTrue(all(c.kind == "code" for c in chunks))

    def test_language_preserved(self):
        source = "const x = 1;\n" * 10
        chunks = self._chunks(source)
        self.assertTrue(all(c.language == "javascript" for c in chunks))

    def test_overlap_means_consecutive_chunks_share_lines(self):
        # With overlap, the end of chunk N should overlap the start of chunk N+1
        source = "\n".join(f"line {i}" for i in range(1, 200))
        chunks = self._chunks(source)
        if len(chunks) > 1:
            self.assertLess(chunks[0].lines[1], chunks[1].lines[1])


class ChunkFileDispatchTests(unittest.TestCase):
    """Tests for the top-level chunk_file dispatcher."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_python_file_dispatches_to_python(self):
        source = "def foo(): pass\n"
        chunks = self.chunker.chunk_file(source, "src/foo.py")
        self.assertTrue(all(c.language == "python" for c in chunks))

    def test_markdown_file_dispatches_to_markdown(self):
        source = "## Section\n\nContent.\n"
        chunks = self.chunker.chunk_file(source, "docs/foo.md")
        self.assertTrue(all(c.language is None for c in chunks))

    def test_seed_file_gets_seed_kind(self):
        source = "## Seed\n\nContent.\n"
        chunks = self.chunker.chunk_file(
            source, ".wavefoundry/framework/seeds/020-foo.prompt.md"
        )
        self.assertTrue(all(c.kind == "seed" for c in chunks))

    def test_unknown_extension_uses_line_window(self):
        source = "some content\n" * 20
        chunks = self.chunker.chunk_file(source, "config/foo.yaml")
        self.assertTrue(len(chunks) >= 1)

    def test_path_normalization_forward_slashes(self):
        source = "def f(): pass\n"
        # Simulate Windows-style path
        chunks = self.chunker.chunk_file(source, r"src\sub\foo.py")
        for c in chunks:
            self.assertNotIn("\\", c.path)
            self.assertNotIn("\\", c.id)


class DesignJsonChunkerTests(unittest.TestCase):
    """Tests for docs/design/**/*.json routing to doc-kind chunks (AC-10)."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_valid_token_file_produces_doc_chunks(self):
        source = '{"color": {"primary": {"500": {"$value": "#2563EB", "$type": "color"}}}}'
        chunks = self.chunker.chunk_file(source, "docs/design/tokens/primitives.tokens.json")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.kind == "doc" for c in chunks))

    def test_valid_token_file_language_is_json(self):
        source = '{"spacing": {"4": {"$value": "16px", "$type": "dimension"}}}'
        chunks = self.chunker.chunk_file(source, "docs/design/tokens/semantic.tokens.json")
        self.assertTrue(all(c.language == "json" for c in chunks))

    def test_malformed_json_falls_back_and_does_not_crash(self):
        source = '{"broken": '
        chunks = self.chunker.chunk_file(source, "docs/design/tokens/primitives.tokens.json")
        self.assertIsInstance(chunks, list)
        self.assertTrue(len(chunks) >= 1)

    def test_malformed_json_fallback_kind_is_code(self):
        # Fallback is line-window which uses kind="code"
        source = '{"broken": '
        chunks = self.chunker.chunk_file(source, "docs/design/tokens/primitives.tokens.json")
        self.assertTrue(all(c.kind == "code" for c in chunks))

    def test_non_design_json_unchanged_routing(self):
        # A JSON file outside docs/design/ must still use the code/line-window path
        source = '{"key": "value"}'
        chunks = self.chunker.chunk_file(source, "src/config/settings.json")
        self.assertTrue(all(c.kind == "code" for c in chunks))

    def test_nested_design_path_is_routed(self):
        source = '{"z": {"modal": {"$value": 1400, "$type": "number"}}}'
        chunks = self.chunker.chunk_file(
            source, "docs/design/tokens/modes/light.tokens.json"
        )
        self.assertTrue(all(c.kind == "doc" for c in chunks))

    def test_manifest_json_in_design_is_doc(self):
        source = '{"schemaVersion": "1.0.0", "canonicalRoot": "docs/design"}'
        chunks = self.chunker.chunk_file(source, "docs/design/manifest.json")
        self.assertTrue(all(c.kind == "doc" for c in chunks))


if __name__ == "__main__":
    unittest.main()
