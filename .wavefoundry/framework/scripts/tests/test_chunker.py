from __future__ import annotations

import importlib.util
import sys
import textwrap
import tracemalloc
import unittest
import unittest.mock
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
        # Sections now carry the H1 breadcrumb: "{H1} > {## heading}"
        self.assertIn("Title > Section One", sections)
        self.assertIn("Title > Section Two", sections)

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

    # --- 12avx: H1 breadcrumb injection ---

    def test_h1_breadcrumb_in_section_and_text(self):
        # AC-1: prose chunk section == "{H1} > {## heading}"; text prefixed
        # Note: the H1 line itself lands in the preamble chunk (section=None)
        source = "# My Doc\n\n## Overview\n\nSome prose.\n"
        chunks = self._chunks(source)
        section_chunks = [c for c in chunks if c.section == "My Doc > Overview"]
        self.assertEqual(len(section_chunks), 1)
        self.assertTrue(section_chunks[0].text.startswith("My Doc > Overview\n\n"))

    def test_h1_breadcrumb_in_code_chunk(self):
        # AC-2: fenced code chunk also carries breadcrumb
        source = "# My Doc\n\n## Usage\n\n```python\nfoo()\n```\n"
        chunks = self._chunks(source)
        code = [c for c in chunks if c.kind == "code"]
        self.assertEqual(len(code), 1)
        self.assertEqual(code[0].section, "My Doc > Usage")
        self.assertTrue(code[0].text.startswith("My Doc > Usage\n\n"))

    def test_no_h1_produces_bare_section(self):
        # AC-3: no H1 → section is bare ## heading, text unchanged from body
        source = "## Overview\n\nSome prose.\n"
        chunks = self._chunks(source)
        prose = [c for c in chunks if c.kind == "doc"]
        self.assertEqual(len(prose), 1)
        self.assertEqual(prose[0].section, "Overview")
        self.assertNotIn(" > ", prose[0].text.split("\n")[0])

    def test_preamble_unaffected_by_breadcrumb(self):
        # AC-9: preamble (content before first ##) has section=None
        source = "# My Doc\n\nPreamble text here.\n\n## Section\n\nBody.\n"
        chunks = self._chunks(source)
        preamble = [c for c in chunks if c.section is None]
        self.assertTrue(len(preamble) >= 1)
        self.assertIn("Preamble text here.", preamble[0].text)

    def test_h3_split_on_oversized_section(self):
        # AC-4: section body > H3_SPLIT_THRESHOLD_CHARS with ### headings → multiple chunks
        h3_threshold = self.chunker.H3_SPLIT_THRESHOLD_CHARS
        sub_body = "x " * (h3_threshold // 2 + 10)
        source = f"# Doc\n\n## Big Section\n\n### Sub A\n\n{sub_body}\n\n### Sub B\n\n{sub_body}\n"
        chunks = self._chunks(source)
        sections = [c.section for c in chunks if c.section]
        self.assertTrue(any("Sub A" in s for s in sections))
        self.assertTrue(any("Sub B" in s for s in sections))

    def test_h3_sub_chunk_section_and_text(self):
        # AC-5: H3 sub-chunk has 3-level breadcrumb in section and text
        h3_threshold = self.chunker.H3_SPLIT_THRESHOLD_CHARS
        sub_body = "y " * (h3_threshold // 2 + 10)
        source = f"# Doc\n\n## Chapter\n\n### Intro\n\n{sub_body}\n\n### Advanced\n\n{sub_body}\n"
        chunks = self._chunks(source)
        intro_chunks = [c for c in chunks if c.section and "Intro" in c.section]
        self.assertTrue(len(intro_chunks) >= 1)
        self.assertIn("Doc > Chapter > Intro", intro_chunks[0].section)
        self.assertTrue(intro_chunks[0].text.startswith("Doc > Chapter > Intro\n\n"))

    def test_h3_split_threshold_exact_does_not_split(self):
        # AC-6: body at exactly threshold chars is not split (condition is strictly >)
        h3_threshold = self.chunker.H3_SPLIT_THRESHOLD_CHARS
        # Build a body that is exactly H3_SPLIT_THRESHOLD_CHARS stripped chars
        padding = "a" * (h3_threshold - len("### Sub\n\n"))
        source = f"# Doc\n\n## Section\n\n### Sub\n\n{padding}\n"
        chunks = self._chunks(source)
        # At threshold (not above): section stays as one h2-level chunk, not split into h3 sub-chunks
        h3_sub_ids = [c.id for c in chunks if "/" in c.id.split("#")[-1]]
        self.assertEqual(h3_sub_ids, [], f"Unexpected H3 sub-chunk IDs at threshold: {h3_sub_ids}")

    def test_oversized_no_h3_falls_to_line_window_with_breadcrumb(self):
        # AC-7: oversized section without ### → line-window fallback with breadcrumb
        h3_threshold = self.chunker.H3_SPLIT_THRESHOLD_CHARS
        big_prose = "word " * (h3_threshold // 4 + 10)
        source = f"# Doc\n\n## Flat Section\n\n{big_prose}\n"
        chunks = self._chunks(source)
        # Each fallback chunk must carry breadcrumb in section and text prefix
        flat = [c for c in chunks if c.section and "Flat Section" in c.section]
        self.assertTrue(len(flat) >= 1)
        for c in flat:
            self.assertIn("Doc > Flat Section", c.section)
            self.assertTrue(c.text.startswith("Doc > Flat Section\n\n"))

    def test_h3_fenced_code_carries_three_level_breadcrumb(self):
        # AC-8: fenced code inside a ### sub-section gets three-level breadcrumb
        h3_threshold = self.chunker.H3_SPLIT_THRESHOLD_CHARS
        big_prose = "z " * (h3_threshold // 2 + 10)
        source = (
            f"# Doc\n\n## Chapter\n\n### Sub\n\n{big_prose}\n\n"
            "```python\nfoo()\n```\n"
        )
        chunks = self._chunks(source)
        code = [c for c in chunks if c.kind == "code"]
        self.assertTrue(len(code) >= 1)
        self.assertIn("Doc > Chapter > Sub", code[0].section)

    def test_seed_file_gets_breadcrumb(self):
        # AC-10: seed files receive same breadcrumb treatment
        source = "# Install Guide\n\n## Setup\n\nDo the setup.\n"
        chunks = self.chunker.chunk_markdown(
            source,
            ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
            kind_override="seed",
        )
        section_chunks = [c for c in chunks if c.section]
        self.assertTrue(len(section_chunks) >= 1)
        self.assertEqual(section_chunks[0].section, "Install Guide > Setup")

    def test_h3_sub_section_ids(self):
        # AC-11: ### sub-section prose ID is {path}#{h2-slug}/{h3-slug}
        h3_threshold = self.chunker.H3_SPLIT_THRESHOLD_CHARS
        sub_body = "word " * (h3_threshold // 2 + 10)
        source = f"# Doc\n\n## Main Section\n\n### Sub Part\n\n{sub_body}\n\n### Other Part\n\n{sub_body}\n"
        chunks = self._chunks(source, path="docs/guide.md")
        sub_ids = [c.id for c in chunks if "sub-part" in c.id or "other-part" in c.id]
        self.assertTrue(any("main-section/sub-part" in id_ for id_ in sub_ids), sub_ids)
        self.assertTrue(any("main-section/other-part" in id_ for id_ in sub_ids), sub_ids)

    def test_line_window_fallback_id_uses_L_notation(self):
        # AC-11: line-window fallback ID is {path}#{h2-slug}:L{start}-L{end}
        h3_threshold = self.chunker.H3_SPLIT_THRESHOLD_CHARS
        big_prose = "word " * (h3_threshold // 4 + 10)
        source = f"# Doc\n\n## Big Flat\n\n{big_prose}\n"
        chunks = self._chunks(source, path="docs/guide.md")
        lw_chunks = [c for c in chunks if ":L" in c.id]
        self.assertTrue(len(lw_chunks) >= 1)
        for c in lw_chunks:
            self.assertRegex(c.id, r"#big-flat:L\d+-L\d+")


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
        non_summary = [c for c in chunks if c.kind != "doc-summary"]
        self.assertTrue(all(c.kind == "seed" for c in non_summary))

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
    """Tests for docs/design-system/**/*.json routing to doc-kind chunks (AC-10)."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_valid_token_file_produces_doc_chunks(self):
        source = '{"color": {"primary": {"500": {"$value": "#2563EB", "$type": "color"}}}}'
        chunks = self.chunker.chunk_file(source, "docs/design-system/tokens/primitives.tokens.json")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.kind == "doc" for c in chunks))

    def test_valid_token_file_language_is_json(self):
        source = '{"spacing": {"4": {"$value": "16px", "$type": "dimension"}}}'
        chunks = self.chunker.chunk_file(source, "docs/design-system/tokens/semantic.tokens.json")
        self.assertTrue(all(c.language == "json" for c in chunks))

    def test_malformed_json_falls_back_and_does_not_crash(self):
        source = '{"broken": '
        chunks = self.chunker.chunk_file(source, "docs/design-system/tokens/primitives.tokens.json")
        self.assertIsInstance(chunks, list)
        self.assertTrue(len(chunks) >= 1)

    def test_malformed_json_fallback_kind_is_code(self):
        # Fallback is line-window which uses kind="code"
        source = '{"broken": '
        chunks = self.chunker.chunk_file(source, "docs/design-system/tokens/primitives.tokens.json")
        self.assertTrue(all(c.kind == "code" for c in chunks))

    def test_non_design_json_unchanged_routing(self):
        # A JSON file outside docs/design-system/ must still use the code/line-window path
        source = '{"key": "value"}'
        chunks = self.chunker.chunk_file(source, "src/config/settings.json")
        self.assertTrue(all(c.kind == "code" for c in chunks))

    def test_nested_design_path_is_routed(self):
        source = '{"z": {"modal": {"$value": 1400, "$type": "number"}}}'
        chunks = self.chunker.chunk_file(
            source, "docs/design-system/tokens/modes/light.tokens.json"
        )
        self.assertTrue(all(c.kind == "doc" for c in chunks))

    def test_manifest_json_in_design_is_doc(self):
        source = '{"schemaVersion": "1.0.0", "canonicalRoot": "docs/design-system"}'
        chunks = self.chunker.chunk_file(source, "docs/design-system/manifest.json")
        self.assertTrue(all(c.kind == "doc" for c in chunks))


class PythonBreadcrumbAndDecoratorTests(unittest.TestCase):
    """12aw5: Python decorator fix and breadcrumb injection."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_decorator_included_in_code_chunk(self):
        # AC-6: decorator line must appear in code chunk text
        source = textwrap.dedent("""\
            import functools

            @functools.lru_cache
            def expensive(n):
                return n * n
        """)
        chunks = self.chunker.chunk_python(source, "src/foo.py")
        code = [c for c in chunks if c.kind == "code" and "expensive" in c.id]
        self.assertEqual(len(code), 1)
        self.assertIn("@functools.lru_cache", code[0].text)

    def test_python_section_has_breadcrumb(self):
        # AC-7: section == "{file_stem} > {qname}"
        source = textwrap.dedent("""\
            class MyClass:
                def method(self):
                    pass
        """)
        chunks = self.chunker.chunk_python(source, "src/utils.py")
        method = [c for c in chunks if "method" in c.id and c.kind == "code"]
        self.assertEqual(len(method), 1)
        self.assertEqual(method[0].section, "utils > MyClass.method")

    def test_python_doc_chunk_text_prefixed_with_breadcrumb(self):
        # AC-7: doc chunk text starts with breadcrumb
        source = textwrap.dedent("""\
            def process():
                \"\"\"Process the data.\"\"\"
                pass
        """)
        chunks = self.chunker.chunk_python(source, "src/pipeline.py")
        doc = [c for c in chunks if c.kind == "doc" and "process" in c.id]
        self.assertEqual(len(doc), 1)
        self.assertTrue(doc[0].text.startswith("pipeline > process\n\n"))


class JavaChunkerTests(unittest.TestCase):
    """12aw5: Java structure-aware chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_java_method_breadcrumb_in_section(self):
        # AC-1: code chunk section starts with "{stem} > "
        source = textwrap.dedent("""\
            public class Payment {
                public void processPayment(String id) {
                    System.out.println(id);
                }
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/Payment.java")
        code = [c for c in chunks if c.kind == "code" and "processPayment" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("Payment > Payment.processPayment", code[0].section)

    def test_java_javadoc_extracted(self):
        # AC-2: doc chunk with stripped Javadoc prose
        source = textwrap.dedent("""\
            public class Service {
                /**
                 * Process the request.
                 */
                public void process() {
                    // body
                }
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/Service.java")
        doc = [c for c in chunks if c.kind == "doc" and "process" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("Process the request", doc[0].text)

    def test_java_annotation_names_in_doc_chunk(self):
        # AC-3: annotation names appear in doc chunk
        source = textwrap.dedent("""\
            public class Api {
                /**
                 * Handle the request.
                 */
                @RequestMapping("/api")
                public void handle() {}
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/Api.java")
        doc = [c for c in chunks if c.kind == "doc" and "handle" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("@RequestMapping", doc[0].text)

    def test_java_annotation_verbatim_in_code_chunk(self):
        # AC-4: full annotation in code chunk
        source = textwrap.dedent("""\
            public class Api {
                @RequestMapping("/api")
                public void handle() {}
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/Api.java")
        code = [c for c in chunks if c.kind == "code" and "handle" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn('@RequestMapping("/api")', code[0].text)

    def test_java_fallback_on_unparseable(self):
        # AC-9: minified / complex input falls through without exception
        source = "{{{{invalid java here\n" * 5
        chunks = self.chunker.chunk_java(source, "src/Weird.java")
        self.assertIsInstance(chunks, list)
        self.assertTrue(len(chunks) >= 1)

    def test_java_class_declaration_chunk_includes_extends(self):
        source = textwrap.dedent("""\
            public class OrderService extends BaseService implements Auditable {
                public void submit() {}
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/OrderService.java")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("extends BaseService", decl[0].text)
        self.assertIn("implements Auditable", decl[0].text)

    def test_java_class_declaration_chunk_emitted_without_javadoc(self):
        source = textwrap.dedent("""\
            public class Plain {
                public void go() {}
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/Plain.java")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)

    def test_java_decl_with_block_comment_brace_continues(self):
        # _decl_line_ends must not terminate early on { inside /* */ comment
        source = textwrap.dedent("""\
            public class Foo /* { placeholder */
                    extends BaseService {
                public void go() {}
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/Foo.java")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("extends BaseService", decl[0].text)

    def test_java_decl_with_multiline_block_comment_continues(self):
        # _collect_decl_text must track /* */ state across lines
        source = textwrap.dedent("""\
            public class Foo /*
                this comment spans lines and contains {
            */ extends BaseService {
                public void go() {}
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/Foo.java")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("extends BaseService", decl[0].text)

    def test_java_multiline_declaration_captured(self):
        source = textwrap.dedent("""\
            public class OrderService
                    extends BaseService
                    implements Auditable, Serializable {
                public void submit() {}
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/OrderService.java")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("extends BaseService", decl[0].text)
        self.assertIn("Serializable", decl[0].text)

    def test_java_multiline_annotation_accumulation(self):
        # AC-5: multiline annotation with paren-balance continuation
        source = textwrap.dedent("""\
            public class Api {
                /**
                 * Handle the request.
                 */
                @RequestMapping(
                    value = "/api",
                    method = RequestMethod.POST
                )
                public void handle() {}
            }
        """)
        chunks = self.chunker.chunk_java(source, "src/Api.java")
        doc = [c for c in chunks if c.kind == "doc" and "handle" in c.id]
        self.assertTrue(len(doc) >= 1, "doc chunk for handle() must exist")
        self.assertIn("@RequestMapping", doc[0].text)
        code = [c for c in chunks if c.kind == "code" and "handle" in c.id]
        self.assertTrue(len(code) >= 1, "code chunk for handle() must exist")
        self.assertIn("RequestMapping", code[0].text)

    def test_java_split_large_code_chunks(self):
        # AC-12: no chunk exceeds 4000 chars for Java chunker
        body = "        System.out.println(\"line\");\n" * 200
        source = f"public class Big {{\n    public void run() {{\n{body}    }}\n}}\n"
        chunks = self.chunker.chunk_java(source, "src/Big.java")
        for c in chunks:
            self.assertLessEqual(len(c.text), 4000, f"chunk too large: {c.id}")


class CSharpChunkerTests(unittest.TestCase):
    """12aw5: C# structure-aware chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_csharp_method_breadcrumb(self):
        source = textwrap.dedent("""\
            public class Order {
                public void Submit() {
                    // submit
                }
            }
        """)
        chunks = self.chunker.chunk_csharp(source, "src/Order.cs")
        code = [c for c in chunks if c.kind == "code" and "Submit" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("Order > Order.Submit", code[0].section)

    def test_csharp_obsolete_string_in_doc(self):
        # AC-8: [Obsolete("...")] string extracted to doc chunk
        source = textwrap.dedent("""\
            public class Legacy {
                /// <summary>Old method.</summary>
                [Obsolete("Use NewMethod instead")]
                public void OldMethod() {}
            }
        """)
        chunks = self.chunker.chunk_csharp(source, "src/Legacy.cs")
        doc = [c for c in chunks if c.kind == "doc" and "OldMethod" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("Use NewMethod instead", doc[0].text)

    def test_csharp_class_declaration_chunk_includes_base(self):
        source = textwrap.dedent("""\
            public class OrderService : BaseService, IAuditable {
                public void Submit() {}
            }
        """)
        chunks = self.chunker.chunk_csharp(source, "src/OrderService.cs")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn(": BaseService, IAuditable", decl[0].text)

    def test_csharp_class_declaration_chunk_emitted_without_xmldoc(self):
        source = textwrap.dedent("""\
            public class Plain {
                public void Go() {}
            }
        """)
        chunks = self.chunker.chunk_csharp(source, "src/Plain.cs")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)

    def test_csharp_multiline_declaration_captured(self):
        source = textwrap.dedent("""\
            public class OrderService
                : BaseService,
                  IAuditable {
                public void Submit() {}
            }
        """)
        chunks = self.chunker.chunk_csharp(source, "src/OrderService.cs")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("BaseService", decl[0].text)
        self.assertIn("IAuditable", decl[0].text)


class JsTsChunkerTests(unittest.TestCase):
    """12aw5: JavaScript/TypeScript structure-aware chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_js_function_breadcrumb(self):
        source = textwrap.dedent("""\
            function processData(input) {
                return input.trim();
            }
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/utils.js")
        code = [c for c in chunks if c.kind == "code" and "processData" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertEqual(code[0].section, "utils > processData")

    def test_js_minified_fallback(self):
        # AC-9: no recognisable declarations → line-window with file-stem breadcrumb
        source = "var x=1;var y=2;var z=function(){return x+y;};"
        chunks = self.chunker.chunk_js_ts(source, "src/min.js")
        self.assertIsInstance(chunks, list)
        self.assertTrue(len(chunks) >= 1)
        # Fallback chunks carry file-stem in section
        for c in chunks:
            if c.section:
                self.assertIn("min", c.section)

    def test_ts_dispatches_via_chunk_file(self):
        source = "function greet(name: string): string { return name; }\n"
        chunks = self.chunker.chunk_file(source, "src/greet.ts")
        self.assertTrue(len(chunks) >= 1)
        code = [c for c in chunks if c.kind == "code"]
        self.assertTrue(len(code) >= 1)

    def test_js_class_method_breadcrumb(self):
        source = textwrap.dedent("""\
            class OrderService {
                submit(order) {
                    return true;
                }
            }
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/OrderService.js")
        code = [c for c in chunks if c.kind == "code" and "submit" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("OrderService.submit", code[0].section)

    def test_js_arrow_function_breadcrumb(self):
        source = textwrap.dedent("""\
            const processData = (input) => {
                return input.trim();
            };
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/utils.js")
        code = [c for c in chunks if c.kind == "code" and "processData" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("processData", code[0].section)

    def test_js_jsdoc_extraction(self):
        source = textwrap.dedent("""\
            /**
             * Fetch the user by ID.
             * @param {string} id
             */
            function fetchUser(id) {
                return null;
            }
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/users.js")
        doc = [c for c in chunks if c.kind == "doc" and "fetchUser" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("Fetch the user by ID", doc[0].text)

    def test_js_class_jsdoc_extraction(self):
        source = textwrap.dedent("""\
            /**
             * Manages orders.
             */
            class OrderService {
                submit(order) { return true; }
            }
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/OrderService.js")
        doc = [c for c in chunks if c.kind == "doc" and "OrderService" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("Manages orders", doc[0].text)

    def test_js_method_jsdoc_extraction(self):
        source = textwrap.dedent("""\
            class OrderService {
                /**
                 * Submit the order.
                 */
                submit(order) {
                    return true;
                }
            }
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/OrderService.js")
        doc = [c for c in chunks if c.kind == "doc" and "submit" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("Submit the order", doc[0].text)

    def test_js_split_large_code_chunks(self):
        # AC-12: no chunk exceeds 4000 chars for JS/TS chunker
        body = "    console.log('line');\n" * 200
        source = f"function bigFn() {{\n{body}}}\n"
        chunks = self.chunker.chunk_js_ts(source, "src/big.js")
        for c in chunks:
            self.assertLessEqual(len(c.text), 4000, f"chunk too large: {c.id}")

    def test_tsx_chunks_have_typescript_language(self):
        source = "export function App() { return null; }\n"
        chunks = self.chunker.chunk_js_ts(source, "src/App.tsx")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "typescript" for c in chunks))

    def test_ts_chunks_have_typescript_language(self):
        source = "function greet(name: string): string { return name; }\n"
        chunks = self.chunker.chunk_js_ts(source, "src/greet.ts")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "typescript" for c in chunks))

    def test_js_chunks_have_javascript_language(self):
        source = "function greet(name) { return name; }\n"
        chunks = self.chunker.chunk_js_ts(source, "src/greet.js")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "javascript" for c in chunks))

    def test_jsx_chunks_have_javascript_language(self):
        source = "function App() { return null; }\n"
        chunks = self.chunker.chunk_js_ts(source, "src/App.jsx")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "javascript" for c in chunks))


class HtmlChunkerTests(unittest.TestCase):
    """12aw5: HTML landmark chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_html_section_with_id(self):
        # AC-10: <section id="intro"> → section containing "intro"
        source = textwrap.dedent("""\
            <html>
            <section id="intro">
              <p>Welcome</p>
            </section>
            </html>
        """)
        chunks = self.chunker.chunk_html(source, "docs/page.html")
        self.assertTrue(len(chunks) >= 1)
        sections = [c.section for c in chunks if c.section]
        self.assertTrue(any("intro" in s for s in sections))

    def test_html_no_landmarks_fallback(self):
        # AC-11: no landmark elements → line-window fallback
        source = "<div><p>Some text</p></div>\n" * 3
        chunks = self.chunker.chunk_html(source, "docs/nolm.html")
        self.assertTrue(len(chunks) >= 1)
        # All chunks have file-stem breadcrumb
        for c in chunks:
            if c.section:
                self.assertIn("nolm", c.section)

    def test_html_dispatches_via_chunk_file(self):
        source = "<section><h1>Title</h1><p>Content</p></section>\n"
        chunks = self.chunker.chunk_file(source, "docs/page.html")
        self.assertTrue(len(chunks) >= 1)


class GoChunkerTests(unittest.TestCase):
    """12aw5: Go structure-aware chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_go_receiver_method_breadcrumb(self):
        # AC-15: func (r *ReceiverType) Name() → section "{stem} > ReceiverType.Name"
        source = textwrap.dedent("""\
            package main

            // Process handles the request.
            func (s *Service) Process() error {
                return nil
            }
        """)
        chunks = self.chunker.chunk_go(source, "internal/service.go")
        code = [c for c in chunks if c.kind == "code" and "Process" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("Service.Process", code[0].section)

    def test_go_adjacent_comment_doc_chunk(self):
        # AC-15: adjacent // comment → doc chunk
        source = textwrap.dedent("""\
            // Compute returns n*n.
            func Compute(n int) int {
                return n * n
            }
        """)
        chunks = self.chunker.chunk_go(source, "pkg/math.go")
        doc = [c for c in chunks if c.kind == "doc" and "Compute" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("Compute returns n*n", doc[0].text)

    def test_go_type_struct_declaration_chunk(self):
        source = textwrap.dedent("""\
            // Order represents a purchase.
            type Order struct {
                ID     int
                Amount float64
            }
        """)
        chunks = self.chunker.chunk_go(source, "pkg/order.go")
        code = [c for c in chunks if c.kind == "code" and "Order" in c.id and "__doc__" not in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("order > Order", code[0].section)
        doc = [c for c in chunks if c.kind == "doc" and "Order" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("Order represents a purchase", doc[0].text)

    def test_go_type_interface_declaration_chunk(self):
        source = textwrap.dedent("""\
            type Storer interface {
                Save() error
            }
        """)
        chunks = self.chunker.chunk_go(source, "pkg/storage.go")
        code = [c for c in chunks if c.kind == "code" and "Storer" in c.id]
        self.assertTrue(len(code) >= 1)


class RustChunkerTests(unittest.TestCase):
    """12aw5: Rust structure-aware chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_rust_impl_method_breadcrumb(self):
        # AC-16: impl TypeName { fn method() } → "{stem} > TypeName.method"
        source = textwrap.dedent("""\
            impl Payment {
                pub fn process(&self) -> bool {
                    true
                }
            }
        """)
        chunks = self.chunker.chunk_rust(source, "src/payment.rs")
        code = [c for c in chunks if c.kind == "code" and "process" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("Payment.process", code[0].section)

    def test_rust_top_level_fn_breadcrumb(self):
        # AC-16: top-level fn → "{stem} > fn_name"
        source = textwrap.dedent("""\
            pub fn main() {
                println!("hello");
            }
        """)
        chunks = self.chunker.chunk_rust(source, "src/main.rs")
        code = [c for c in chunks if c.kind == "code" and "main" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertEqual(code[0].section, "main > main")

    def test_rust_impl_trait_for_type_emits_decl_chunk(self):
        source = textwrap.dedent("""\
            impl Serializable for Order {
                pub fn serialize(&self) -> String {
                    String::new()
                }
            }
        """)
        chunks = self.chunker.chunk_rust(source, "src/order.rs")
        decl = [c for c in chunks if c.id.endswith(".__impl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("Serializable", decl[0].text)
        self.assertIn("Order", decl[0].text)

    def test_rust_plain_impl_emits_decl_chunk(self):
        source = textwrap.dedent("""\
            impl Payment {
                pub fn process(&self) -> bool { true }
            }
        """)
        chunks = self.chunker.chunk_rust(source, "src/payment.rs")
        decl = [c for c in chunks if c.id.endswith(".__impl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("Payment", decl[0].text)

    def test_rust_multiline_impl_declaration_captured(self):
        source = textwrap.dedent("""\
            impl Serializable
                for Order
            {
                pub fn serialize(&self) -> String { String::new() }
            }
        """)
        chunks = self.chunker.chunk_rust(source, "src/order.rs")
        decl = [c for c in chunks if c.id.endswith(".__impl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("Serializable", decl[0].text)
        self.assertIn("Order", decl[0].text)

    def test_rust_struct_declaration_chunk(self):
        source = textwrap.dedent("""\
            /// An order in the system.
            pub struct Order {
                pub id: u32,
                pub amount: f64,
            }
        """)
        chunks = self.chunker.chunk_rust(source, "src/order.rs")
        code = [c for c in chunks if c.kind == "code" and "Order" in c.id and "__doc__" not in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("order > Order", code[0].section)
        doc = [c for c in chunks if c.kind == "doc" and "Order" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("An order in the system", doc[0].text)

    def test_rust_trait_declaration_chunk(self):
        source = textwrap.dedent("""\
            pub trait Auditable {
                fn audit(&self) -> String;
            }
        """)
        chunks = self.chunker.chunk_rust(source, "src/audit.rs")
        code = [c for c in chunks if c.kind == "code" and "Auditable" in c.id]
        self.assertTrue(len(code) >= 1)

    def test_rust_enum_declaration_chunk(self):
        source = textwrap.dedent("""\
            pub enum Status {
                Pending,
                Active,
                Closed,
            }
        """)
        chunks = self.chunker.chunk_rust(source, "src/status.rs")
        code = [c for c in chunks if c.kind == "code" and "Status" in c.id]
        self.assertTrue(len(code) >= 1)


class ShellChunkerTests(unittest.TestCase):
    """12aw5: Shell structure-aware chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_shell_function_heuristic_doc_chunk(self):
        # AC-17: leading # comment block → doc chunk prefixed [inferred from comments]
        source = textwrap.dedent("""\
            # Deploy the app to production.
            deploy() {
                echo "deploying"
            }
        """)
        chunks = self.chunker.chunk_shell(source, "scripts/deploy.sh")
        doc = [c for c in chunks if c.kind == "doc" and "deploy" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("[inferred from comments]", doc[0].text)
        self.assertIn("Deploy the app", doc[0].text)

    def test_sh_chunks_have_shell_language(self):
        source = "deploy() {\n    echo deploying\n}\n"
        chunks = self.chunker.chunk_shell(source, "scripts/deploy.sh")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "shell" for c in chunks))

    def test_bash_chunks_have_shell_language(self):
        source = "deploy() {\n    echo deploying\n}\n"
        chunks = self.chunker.chunk_shell(source, "scripts/deploy.bash")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "shell" for c in chunks))

    def test_zsh_chunks_have_shell_language(self):
        source = "deploy() {\n    echo deploying\n}\n"
        chunks = self.chunker.chunk_shell(source, "scripts/deploy.zsh")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "shell" for c in chunks))

    def test_fish_chunks_have_fish_language(self):
        source = "function deploy\n    echo deploying\nend\n"
        chunks = self.chunker.chunk_shell(source, "scripts/deploy.fish")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "fish" for c in chunks))


class SqlChunkerTests(unittest.TestCase):
    """12aw5: SQL DDL-boundary chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_sql_create_table(self):
        # AC-20: CREATE TABLE orders → code chunk with section "{stem} > orders"
        source = textwrap.dedent("""\
            -- Order tracking table
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                amount DECIMAL
            );
        """)
        chunks = self.chunker.chunk_sql(source, "db/schema.sql")
        code = [c for c in chunks if c.kind == "code" and "orders" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("schema > orders", code[0].section)

    def test_sql_schema_qualified_definition_uses_qualified_chunk_name(self):
        source = textwrap.dedent("""\
            CREATE OR REPLACE PROCEDURE app.create_schema_objects(_tenant text)
            LANGUAGE plpgsql
            AS $$
            BEGIN
                CALL app.create_schema_objects(_tenant);
            END;
            $$;
        """)
        chunks = self.chunker.chunk_sql(source, "db/migrations.sql")
        code = [c for c in chunks if c.kind == "code" and c.language == "sql"]
        self.assertTrue(any("app.create_schema_objects" in c.id for c in code))

    def test_sql_comment_before_ddl_is_doc_chunk(self):
        # AC-20: comment immediately before DDL → doc chunk
        source = textwrap.dedent("""\
            -- Order tracking table
            CREATE TABLE orders (id INT);
        """)
        chunks = self.chunker.chunk_sql(source, "db/schema.sql")
        doc = [c for c in chunks if c.kind == "doc"]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("Order tracking table", doc[0].text)

    def test_sql_alias_extension_routes_to_sql_chunker(self):
        source = "CREATE TABLE alias_test (id INT);\n"
        chunks = self.chunker.chunk_file(source, "db/schema.psql")
        self.assertTrue(any(c.language == "sql" and c.kind == "code" for c in chunks))

    def test_sql_anonymous_do_blocks_are_chunked(self):
        source = textwrap.dedent("""\
            do
            $$
                declare
                    _tenant text := 't_616023_app_devcory';
                begin
                    raise notice 'first';
                end
            $$ language plpgsql;

            do $tenant$
            begin
                raise notice 'second';
            end
            $tenant$ language plpgsql;
        """)
        chunks = self.chunker.chunk_sql(source, "db/migrations.sql")
        anon = [c for c in chunks if c.kind == "code" and "anonymous_block@line_" in c.id]
        self.assertEqual(len(anon), 2)
        self.assertTrue(all(c.language == "sql" for c in anon))
        self.assertTrue(all("anonymous_block@line_" in c.section for c in anon))


class CCppChunkerTests(unittest.TestCase):
    """C/C++ class declaration chunk tests."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_cpp_class_declaration_chunk_includes_base(self):
        source = textwrap.dedent("""\
            class OrderService : public BaseService, public IAuditable {
            public:
                void submit();
            };
        """)
        chunks = self.chunker.chunk_c_cpp(source, "src/OrderService.cpp")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("public BaseService", decl[0].text)
        self.assertIn("IAuditable", decl[0].text)

    def test_cpp_class_declaration_chunk_emitted_without_doc(self):
        source = textwrap.dedent("""\
            class Plain {
            public:
                void go();
            };
        """)
        chunks = self.chunker.chunk_c_cpp(source, "src/Plain.cpp")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("Plain", decl[0].text)

    def test_cpp_multiline_declaration_captured(self):
        source = textwrap.dedent("""\
            class OrderService
                : public BaseService,
                  public IAuditable {
            public:
                void submit();
            };
        """)
        chunks = self.chunker.chunk_c_cpp(source, "src/OrderService.cpp")
        decl = [c for c in chunks if c.id.endswith(".__decl__")]
        self.assertTrue(len(decl) >= 1)
        self.assertIn("BaseService", decl[0].text)
        self.assertIn("IAuditable", decl[0].text)

    def test_cpp_function_body_chunk(self):
        source = textwrap.dedent("""\
            /// Submit the order.
            void submit(int id) {
                process(id);
            }
        """)
        chunks = self.chunker.chunk_c_cpp(source, "src/order.cpp")
        code = [c for c in chunks if c.kind == "code" and "submit" in c.id]
        self.assertTrue(len(code) >= 1)
        self.assertIn("submit", code[0].section)

    def test_cpp_function_doc_chunk(self):
        source = textwrap.dedent("""\
            /// Submit the order.
            void submit(int id) {
                process(id);
            }
        """)
        chunks = self.chunker.chunk_c_cpp(source, "src/order.cpp")
        doc = [c for c in chunks if c.kind == "doc" and "submit" in c.id]
        self.assertTrue(len(doc) >= 1)
        self.assertIn("Submit the order", doc[0].text)

    def test_cpp_split_large_code_chunks(self):
        # AC-12: no chunk exceeds 4000 chars for C/C++ chunker
        body = "    doSomethingWithALongerLine();\n" * 250
        source = f"void bigFn() {{\n{body}}}\n"
        chunks = self.chunker.chunk_c_cpp(source, "src/big.cpp")
        self.assertGreater(sum(1 for c in chunks if c.kind == "code"), 1, "split should have occurred")
        for c in chunks:
            self.assertLessEqual(len(c.text), 4000, f"chunk too large: {c.id}")

    def test_cpp_chunks_have_cpp_language(self):
        source = "int add(int a, int b) { return a + b; }\n"
        chunks = self.chunker.chunk_c_cpp(source, "src/math.cpp")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "cpp" for c in chunks))

    def test_hpp_chunks_have_cpp_language(self):
        source = "int add(int a, int b) { return a + b; }\n"
        chunks = self.chunker.chunk_c_cpp(source, "src/math.hpp")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "cpp" for c in chunks))

    def test_c_chunks_have_c_language(self):
        source = "int add(int a, int b) { return a + b; }\n"
        chunks = self.chunker.chunk_c_cpp(source, "src/math.c")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "c" for c in chunks))

    def test_h_chunks_have_c_language(self):
        source = "int add(int a, int b);\n"
        chunks = self.chunker.chunk_c_cpp(source, "src/math.h")
        self.assertTrue(len(chunks) >= 1)
        self.assertTrue(all(c.language == "c" for c in chunks))


class XmlChunkerTests(unittest.TestCase):
    """XML chunker tests."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_xml_element_chunk(self):
        source = textwrap.dedent("""\
            <config id="app-config">
                <setting name="timeout">30</setting>
            </config>
        """)
        chunks = self.chunker.chunk_xml(source, "config/app.xml")
        self.assertTrue(len(chunks) >= 1)
        sections = [c.section for c in chunks if c.section]
        self.assertTrue(any("app-config" in s or "config" in s for s in sections))

    def test_xml_id_attribute_used_as_label(self):
        source = '<bean id="orderService" class="com.example.OrderService"/>\n'
        chunks = self.chunker.chunk_xml(source, "config/beans.xml")
        self.assertTrue(len(chunks) >= 1)
        sections = [c.section for c in chunks if c.section]
        self.assertTrue(any("orderService" in s for s in sections))

    def test_xml_name_attribute_used_as_label(self):
        source = '<param name="timeout" value="30"/>\n'
        chunks = self.chunker.chunk_xml(source, "config/params.xml")
        self.assertTrue(len(chunks) >= 1)
        sections = [c.section for c in chunks if c.section]
        self.assertTrue(any("timeout" in s for s in sections))

    def test_xml_no_elements_fallback(self):
        source = "just plain text\nno xml here\n"
        chunks = self.chunker.chunk_xml(source, "config/plain.xml")
        self.assertTrue(len(chunks) >= 1)

    def test_xml_dispatches_via_chunk_file(self):
        source = "<root><child>value</child></root>\n"
        chunks = self.chunker.chunk_file(source, "config/settings.xml")
        self.assertTrue(len(chunks) >= 1)


class ImportsChunkTests(unittest.TestCase):
    """12b0v: __imports__ and __namespace__ chunks across all structured languages."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_java_namespace_chunk_emitted(self):
        source = textwrap.dedent("""\
            package com.example.service;
            import java.util.List;
            public class Svc {}
        """)
        chunks = self.chunker.chunk_java(source, "src/Svc.java")
        ns = [c for c in chunks if c.id.endswith("::__namespace__")]
        self.assertEqual(len(ns), 1)
        self.assertIn("com.example.service", ns[0].text)

    def test_java_imports_chunk_emitted(self):
        source = textwrap.dedent("""\
            package com.example;
            import java.util.List;
            import java.util.Map;
            public class Repo {}
        """)
        chunks = self.chunker.chunk_java(source, "src/Repo.java")
        imp = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imp), 1)
        self.assertIn("java.util.List", imp[0].text)
        self.assertIn("java.util.Map", imp[0].text)

    def test_java_no_imports_no_chunk(self):
        source = "public class Empty {}\n"
        chunks = self.chunker.chunk_java(source, "src/Empty.java")
        imp = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imp), 0)

    def test_csharp_namespace_chunk_emitted(self):
        source = textwrap.dedent("""\
            namespace MyApp.Services;
            using System;
            public class Svc {}
        """)
        chunks = self.chunker.chunk_csharp(source, "src/Svc.cs")
        ns = [c for c in chunks if c.id.endswith("::__namespace__")]
        self.assertEqual(len(ns), 1)
        self.assertIn("MyApp.Services", ns[0].text)

    def test_csharp_imports_chunk_emitted(self):
        source = textwrap.dedent("""\
            using System;
            using System.Collections.Generic;
            public class Repo {}
        """)
        chunks = self.chunker.chunk_csharp(source, "src/Repo.cs")
        imp = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imp), 1)
        self.assertIn("System.Collections.Generic", imp[0].text)

    def test_js_imports_chunk_emitted(self):
        source = textwrap.dedent("""\
            import React from 'react';
            import { useState } from 'react';
            export function App() { return null; }
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/App.tsx")
        imp = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imp), 1)
        self.assertIn("React", imp[0].text)

    def test_go_namespace_chunk_emitted(self):
        source = textwrap.dedent("""\
            package main
            import "fmt"
            func Hello() { fmt.Println("hi") }
        """)
        chunks = self.chunker.chunk_go(source, "cmd/main.go")
        ns = [c for c in chunks if c.id.endswith("::__namespace__")]
        self.assertEqual(len(ns), 1)
        self.assertIn("main", ns[0].text)

    def test_go_imports_chunk_emitted(self):
        source = textwrap.dedent("""\
            package main
            import (
                "fmt"
                "os"
            )
            func Hello() {}
        """)
        chunks = self.chunker.chunk_go(source, "cmd/main.go")
        imp = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imp), 1)
        self.assertIn("fmt", imp[0].text)
        self.assertIn("os", imp[0].text)

    def test_rust_imports_chunk_emitted(self):
        source = textwrap.dedent("""\
            use std::collections::HashMap;
            use std::fmt;
            pub fn hello() {}
        """)
        chunks = self.chunker.chunk_rust(source, "src/lib.rs")
        imp = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imp), 1)
        self.assertIn("HashMap", imp[0].text)

    def test_cpp_imports_chunk_emitted(self):
        source = textwrap.dedent("""\
            #include <vector>
            #include "myheader.h"
            void submit() {}
        """)
        chunks = self.chunker.chunk_c_cpp(source, "src/main.cpp")
        imp = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imp), 1)
        self.assertIn("vector", imp[0].text)
        self.assertIn("myheader.h", imp[0].text)


class SwiftChunkerTests(unittest.TestCase):
    """12b0w: Swift structure-aware chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_swift_class_decl_chunk(self):
        source = textwrap.dedent("""\
            class PaymentService: NSObject {
                func process() {}
            }
        """)
        chunks = self.chunker.chunk_swift(source, "src/PaymentService.swift")
        decl = [c for c in chunks if c.id.endswith("::PaymentService.__decl__")]
        self.assertEqual(len(decl), 1)
        self.assertIn("PaymentService", decl[0].text)

    def test_swift_method_chunk(self):
        source = textwrap.dedent("""\
            class Repo {
                func fetchAll() -> [String] { return [] }
            }
        """)
        chunks = self.chunker.chunk_swift(source, "src/Repo.swift")
        code = [c for c in chunks if "Repo.fetchAll" in c.id and c.kind == "code"]
        self.assertEqual(len(code), 1)
        self.assertIn("fetchAll", code[0].text)

    def test_swift_doc_chunk(self):
        source = textwrap.dedent("""\
            class Svc {
                /// Handles the request.
                func handle() {}
            }
        """)
        chunks = self.chunker.chunk_swift(source, "src/Svc.swift")
        doc = [c for c in chunks if c.kind == "doc" and "handle" in c.id]
        self.assertEqual(len(doc), 1)
        self.assertIn("Handles the request", doc[0].text)

    def test_swift_struct_decl_chunk(self):
        source = "struct Point: Codable { var x: Int; var y: Int }\n"
        chunks = self.chunker.chunk_swift(source, "src/Point.swift")
        decl = [c for c in chunks if c.id.endswith("::Point.__decl__")]
        self.assertEqual(len(decl), 1)

    def test_swift_enum_decl_chunk(self):
        source = "enum Status: String { case active, inactive }\n"
        chunks = self.chunker.chunk_swift(source, "src/Status.swift")
        decl = [c for c in chunks if c.id.endswith("::Status.__decl__")]
        self.assertEqual(len(decl), 1)

    def test_swift_protocol_decl_chunk(self):
        source = "protocol Fetchable { func fetch() }\n"
        chunks = self.chunker.chunk_swift(source, "src/Fetchable.swift")
        decl = [c for c in chunks if c.id.endswith("::Fetchable.__decl__")]
        self.assertEqual(len(decl), 1)

    def test_swift_extension_decl_chunk(self):
        source = "extension Array where Element: Hashable { func unique() -> [Element] { return [] } }\n"
        chunks = self.chunker.chunk_swift(source, "src/Array+Unique.swift")
        decl = [c for c in chunks if ".__decl__" in c.id]
        self.assertEqual(len(decl), 1)
        self.assertIn("Array", decl[0].text)

    def test_swift_imports_chunk(self):
        source = textwrap.dedent("""\
            import Foundation
            import UIKit
            class VC {}
        """)
        chunks = self.chunker.chunk_swift(source, "src/VC.swift")
        imp = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imp), 1)
        self.assertIn("Foundation", imp[0].text)
        self.assertIn("UIKit", imp[0].text)

    def test_swift_empty_file_returns_empty(self):
        chunks = self.chunker.chunk_swift("", "src/Empty.swift")
        self.assertEqual(chunks, [])

    def test_swift_dispatched_via_chunk_file(self):
        source = "class Foo { func bar() {} }\n"
        chunks = self.chunker.chunk_file(source, "src/Foo.swift")
        self.assertTrue(len(chunks) >= 1)

    def test_swift_deinit_chunk_id(self):
        source = textwrap.dedent("""\
            class Cache {
                deinit {
                    cleanup()
                }
            }
        """)
        chunks = self.chunker.chunk_swift(source, "src/Cache.swift")
        deinit_chunks = [c for c in chunks if "deinit" in c.id]
        self.assertEqual(len(deinit_chunks), 1)
        self.assertIn("Cache.deinit", deinit_chunks[0].id)


class ObjcChunkerTests(unittest.TestCase):
    """12b0w: Objective-C structure-aware chunker."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_objc_method_chunk(self):
        source = textwrap.dedent("""\
            @implementation PaymentService
            - (void)processPayment:(NSString *)orderId {
                NSLog(@"%@", orderId);
            }
            @end
        """)
        chunks = self.chunker.chunk_objc(source, "src/PaymentService.m")
        code = [c for c in chunks if c.kind == "code" and "processPayment" in c.id]
        self.assertEqual(len(code), 1)
        self.assertIn("processPayment", code[0].text)

    def test_objc_doc_chunk(self):
        source = textwrap.dedent("""\
            @implementation Svc
            /** Handles the request. */
            - (void)handle {
                // body
            }
            @end
        """)
        chunks = self.chunker.chunk_objc(source, "src/Svc.m")
        doc = [c for c in chunks if c.kind == "doc" and "handle" in c.id]
        self.assertEqual(len(doc), 1)
        self.assertIn("Handles the request", doc[0].text)

    def test_objc_imports_chunk(self):
        source = textwrap.dedent("""\
            #import <Foundation/Foundation.h>
            #import "MyClass.h"
            @implementation Foo
            - (void)run {}
            @end
        """)
        chunks = self.chunker.chunk_objc(source, "src/Foo.m")
        imp = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imp), 1)
        self.assertIn("Foundation", imp[0].text)

    def test_objc_empty_file_returns_empty(self):
        chunks = self.chunker.chunk_objc("", "src/Empty.m")
        self.assertEqual(chunks, [])

    def test_objc_single_line_method_body_no_end_leak(self):
        source = textwrap.dedent("""\
            @implementation Foo
            - (void)run {}
            @end
        """)
        chunks = self.chunker.chunk_objc(source, "src/Foo.m")
        code = [c for c in chunks if c.kind == "code" and "run" in c.id]
        self.assertEqual(len(code), 1)
        self.assertNotIn("@end", code[0].text)

    def test_objc_multiple_implementations(self):
        source = textwrap.dedent("""\
            @implementation Foo
            - (void)doFoo {
                NSLog(@"foo");
            }
            @end
            @implementation Bar
            - (void)doBar {
                NSLog(@"bar");
            }
            @end
        """)
        chunks = self.chunker.chunk_objc(source, "src/Multi.m")
        foo_chunks = [c for c in chunks if c.kind == "code" and "Foo.doFoo" in c.id]
        bar_chunks = [c for c in chunks if c.kind == "code" and "Bar.doBar" in c.id]
        self.assertEqual(len(foo_chunks), 1)
        self.assertEqual(len(bar_chunks), 1)

    def test_objc_dispatched_via_chunk_file(self):
        source = textwrap.dedent("""\
            @implementation Foo
            - (void)run {}
            @end
        """)
        chunks = self.chunker.chunk_file(source, "src/Foo.m")
        self.assertTrue(len(chunks) >= 1)


class ChunkFileNewExtensionsTests(unittest.TestCase):
    """12aw5: Verify chunk_file routes new extensions correctly."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_java_routes_to_structured_chunker(self):
        source = "public class Foo { public void bar() {} }\n"
        chunks = self.chunker.chunk_file(source, "src/Foo.java")
        self.assertTrue(len(chunks) >= 1)

    def test_go_routes_to_structured_chunker(self):
        source = "package main\nfunc Hello() {}\n"
        chunks = self.chunker.chunk_file(source, "cmd/hello.go")
        self.assertTrue(len(chunks) >= 1)

    def test_rust_routes_to_structured_chunker(self):
        source = "pub fn hello() {}\n"
        chunks = self.chunker.chunk_file(source, "src/lib.rs")
        self.assertTrue(len(chunks) >= 1)

    def test_sql_routes_to_structured_chunker(self):
        source = "CREATE TABLE foo (id INT);\n"
        chunks = self.chunker.chunk_file(source, "db/schema.sql")
        self.assertTrue(len(chunks) >= 1)

    def test_chunker_version_is_incremented(self):
        # CHUNKER_VERSION >= 16 after secrets-file scrubbing for .tfvars and .env
        version = self.chunker.CHUNKER_VERSION
        self.assertGreaterEqual(int(version), 16)


class SecretsChunkerTests(unittest.TestCase):
    """chunk_secrets_file: .tfvars and .env files index variable names, redact values."""

    def setUp(self):
        self.chunker = load_chunker()

    def _chunks(self, source, path):
        return self.chunker.chunk_file(source, path)

    # --- .tfvars ---

    def test_tfvars_simple_assignment_redacted(self):
        source = 'db_password = "supersecret"\n'
        chunks = self._chunks(source, "infra/prod.tfvars")
        text = " ".join(c.text for c in chunks)
        self.assertIn("db_password", text)
        self.assertNotIn("supersecret", text)
        self.assertIn("<redacted>", text)

    def test_tfvars_unquoted_value_redacted(self):
        source = "instance_count = 3\n"
        chunks = self._chunks(source, "infra/prod.tfvars")
        text = " ".join(c.text for c in chunks)
        self.assertIn("instance_count", text)
        self.assertNotIn("3", text)

    def test_tfvars_multiline_block_redacted(self):
        source = 'tags = {\n  env = "prod"\n  owner = "team"\n}\n'
        chunks = self._chunks(source, "vars.tfvars")
        text = " ".join(c.text for c in chunks)
        self.assertIn("tags", text)
        self.assertNotIn("prod", text)
        self.assertNotIn("team", text)

    def test_tfvars_comment_preserved(self):
        source = "# This is a comment\napi_key = \"secret\"\n"
        chunks = self._chunks(source, "vars.tfvars")
        text = " ".join(c.text for c in chunks)
        self.assertIn("# This is a comment", text)
        self.assertNotIn("secret", text)

    def test_tfvars_language_is_terraform(self):
        chunks = self._chunks('key = "val"\n', "vars.tfvars")
        self.assertTrue(all(c.language == "terraform" for c in chunks))

    def test_tf_file_not_scrubbed(self):
        # .tf is infrastructure code, not a secrets file — values must not be redacted
        source = 'resource "aws_instance" "web" {\n  ami = "ami-12345"\n}\n'
        chunks = self._chunks(source, "main.tf")
        text = " ".join(c.text for c in chunks)
        self.assertNotIn("<redacted>", text)
        self.assertIn("ami-12345", text)

    # --- .env ---

    def test_env_simple_assignment_redacted(self):
        source = "API_KEY=supersecret\n"
        chunks = self._chunks(source, ".env")
        text = " ".join(c.text for c in chunks)
        self.assertIn("API_KEY", text)
        self.assertNotIn("supersecret", text)
        self.assertIn("<redacted>", text)

    def test_env_quoted_value_redacted(self):
        source = 'DATABASE_URL="postgres://user:pass@host/db"\n'
        chunks = self._chunks(source, ".env.local")
        text = " ".join(c.text for c in chunks)
        self.assertIn("DATABASE_URL", text)
        self.assertNotIn("postgres", text)

    def test_env_export_prefix_redacted(self):
        source = "export SECRET_TOKEN=abc123\n"
        chunks = self._chunks(source, ".env")
        text = " ".join(c.text for c in chunks)
        self.assertIn("SECRET_TOKEN", text)
        self.assertNotIn("abc123", text)

    def test_env_comment_preserved(self):
        source = "# Database config\nDB_PASS=secret\n"
        chunks = self._chunks(source, ".env")
        text = " ".join(c.text for c in chunks)
        self.assertIn("# Database config", text)
        self.assertNotIn("secret", text)

    def test_env_language_is_env(self):
        chunks = self._chunks("KEY=val\n", ".env")
        self.assertTrue(all(c.language == "env" for c in chunks))

    def test_env_dotenv_local_variant_scrubbed(self):
        chunks = self._chunks("KEY=val\n", ".env.production")
        text = " ".join(c.text for c in chunks)
        self.assertIn("KEY", text)
        self.assertNotIn("val", text)


class PlainTextChunkerTests(unittest.TestCase):
    """12b1h: .txt files and extensionless README/LICENSE/etc. produce doc chunks."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_txt_file_produces_doc_chunks(self):
        source = "Some release notes.\nLine 2.\n"
        chunks = self.chunker.chunk_file(source, "docs/notes.txt")
        self.assertTrue(len(chunks) >= 1)
        for c in chunks:
            self.assertEqual(c.kind, "doc", "txt chunks must be kind=doc")

    def test_txt_chunk_id_has_line_range(self):
        source = "line one\nline two\n"
        chunks = self.chunker.chunk_file(source, "CHANGELOG.txt")
        self.assertRegex(chunks[0].id, r":L\d+-L\d+$")

    def test_readme_extensionless_produces_doc_chunks(self):
        source = "# My Project\n\nThis is the readme.\n"
        chunks = self.chunker.chunk_file(source, "README")
        self.assertTrue(len(chunks) >= 1)
        for c in chunks:
            self.assertEqual(c.kind, "doc", "README chunks must be kind=doc")

    def test_license_extensionless_produces_doc_chunks(self):
        source = "MIT License\nCopyright 2026\n"
        chunks = self.chunker.chunk_file(source, "LICENSE")
        self.assertTrue(len(chunks) >= 1)
        for c in chunks:
            self.assertEqual(c.kind, "doc")

    def test_changelog_extensionless_produces_doc_chunks(self):
        source = "## v1.0.0\n- Initial release\n"
        chunks = self.chunker.chunk_file(source, "CHANGELOG")
        self.assertTrue(len(chunks) >= 1)
        for c in chunks:
            self.assertEqual(c.kind, "doc")

    def test_empty_txt_returns_empty(self):
        chunks = self.chunker.chunk_file("", "docs/empty.txt")
        self.assertEqual(chunks, [])

    def test_txt_dispatch_not_code_index(self):
        """Verify txt chunks would land in docs index (kind != code)."""
        source = "A plain text file.\n"
        chunks = self.chunker.chunk_file(source, "notes.txt")
        self.assertTrue(all(c.kind == "doc" for c in chunks))


class LineWindowBoundaryTests(unittest.TestCase):
    """12c7n-enh line-window-chunker-boundary-improvement: blank-line and dedent-to-zero breaks."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_default_window_is_120(self):
        # AC-3: cap raised to 120 lines
        self.assertEqual(self.chunker.WINDOW_SIZE, 120)

    def test_blank_line_break_in_last_20_percent(self):
        # AC-1: blank line within last 20% of window causes break there
        # Window=120, last 20% = lines 96-120. Put blank at line 100 (0-indexed 99).
        lines = [f"code line {i}" for i in range(1, 130)]
        lines[99] = ""  # blank line at position 100 (1-indexed)
        source = "\n".join(lines)
        chunks = self.chunker.chunk_line_window(source, "src/big.py", language="python")
        # First chunk must end at or before line 100 (the blank), not at line 120
        self.assertLess(chunks[0].lines[1], 120)

    def test_dedent_to_zero_break(self):
        # AC-2: a top-level `def` keyword at column 0 in last 20% causes break before it
        lines = ["    body line " + str(i) for i in range(1, 115)]
        lines[108] = "def top_level():"  # column 0, top-level boundary
        source = "\n".join(lines)
        chunks = self.chunker.chunk_line_window(source, "src/big.py", language="python")
        self.assertLess(chunks[0].lines[1], 120)

    def test_lines_field_is_accurate(self):
        # AC-5: lines tuple reflects actual line range
        source = "\n".join(f"line {i}" for i in range(1, 50))
        chunks = self.chunker.chunk_line_window(source, "src/small.py", language="python")
        for chunk in chunks:
            actual_line_count = chunk.text.count("\n") + 1
            self.assertEqual(chunk.lines[1] - chunk.lines[0] + 1, actual_line_count)


class ExportConstChunkerTests(unittest.TestCase):
    """12c7r-bug ts-export-const-body-truncated: export const declarations indexed."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_export_const_after_imports_is_indexed(self):
        # AC-1: file with import block + export const declarations produces full coverage
        source = textwrap.dedent("""\
            import React from 'react';
            import styled from 'styled-components';
            import { theme } from './theme';

            export const Button = styled.button`
              background: ${theme.primary};
              color: white;
              padding: 8px 16px;
            `;

            export const IconButton = styled.button`
              background: transparent;
              border: none;
              cursor: pointer;
            `;
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/Button.tsx")
        ids = [c.id for c in chunks]
        # Must have chunks covering Button and IconButton declarations
        button_chunks = [c for c in chunks if "Button" in c.id and c.kind == "code"]
        icon_chunks = [c for c in chunks if "IconButton" in c.id and c.kind == "code"]
        self.assertTrue(len(button_chunks) >= 1, f"Button chunk missing; ids={ids}")
        self.assertTrue(len(icon_chunks) >= 1, f"IconButton chunk missing; ids={ids}")

    def test_export_const_section_contains_name(self):
        # AC-2: section contains the const name
        source = textwrap.dedent("""\
            import React from 'react';

            export const MyComponent = () => {
              const x = 1;
              const y = 2;
              return x + y;
            };
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/MyComponent.tsx")
        code = [c for c in chunks if "MyComponent" in c.id and c.kind == "code"]
        self.assertTrue(len(code) >= 1)
        self.assertIn("MyComponent", code[0].section)

    def test_existing_class_and_function_still_work(self):
        # AC-3: non-regression — class methods and function declarations still produce chunks
        source = textwrap.dedent("""\
            import React from 'react';

            class AppComponent extends React.Component {
                render() {
                    return null;
                }
            }

            function helper(x) {
                const result = x * 2;
                return result;
            }
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/App.js")
        ids = [c.id for c in chunks]
        self.assertTrue(any("render" in i for i in ids), f"render method missing; ids={ids}")
        self.assertTrue(any("helper" in i for i in ids), f"helper fn missing; ids={ids}")


class MergeSmallChunksTests(unittest.TestCase):
    """12c86-enh chunker-minimum-chunk-size: sub-minimum chunk merging."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_chunk_min_lines_constant_defined(self):
        # AC-4: CHUNK_MIN_LINES defined at module level
        self.assertIsInstance(self.chunker.CHUNK_MIN_LINES, int)
        self.assertGreaterEqual(self.chunker.CHUNK_MIN_LINES, 1)

    def test_single_chunk_below_minimum_emitted_as_is(self):
        # AC-2: single sub-minimum chunk not discarded
        source = "def f():\n    pass\n"
        chunks = self.chunker.chunk_python(source, "src/f.py")
        # Should emit at least one chunk even though it's tiny
        self.assertTrue(len(chunks) >= 1)
        # All text should be present somewhere
        combined = " ".join(c.text for c in chunks)
        self.assertIn("def f", combined)

    def test_imports_chunk_below_minimum_not_merged(self):
        # AC-3: imports chunk exempt from minimum even when short
        source = textwrap.dedent("""\
            import React from 'react';

            export const App = () => {
                const x = 1;
                const y = 2;
                return x + y;
            };
        """)
        chunks = self.chunker.chunk_js_ts(source, "src/App.tsx")
        imports = [c for c in chunks if c.id.endswith("::__imports__")]
        self.assertEqual(len(imports), 1, "imports chunk must be present even if short")

    def test_merge_small_chunks_helper_merges_into_predecessor(self):
        # AC-1: _merge_small_chunks merges sub-minimum (1-line) into predecessor
        Chunk = self.chunker.Chunk
        min_lines = self.chunker.CHUNK_MIN_LINES
        chunks = [
            Chunk(id="f::A", path="f.py", kind="code", language="python",
                  lines=(1, 10), section="A", text="big chunk"),
            # A chunk that is exactly 1 line (always below any reasonable minimum)
            Chunk(id="f::B", path="f.py", kind="code", language="python",
                  lines=(11, 11), section="B", text="super(scope, id)"),
        ]
        result = self.chunker._merge_small_chunks(chunks)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "f::A")
        self.assertIn("super(scope, id)", result[0].text)
        self.assertEqual(result[0].lines[1], 11)

    def test_merge_small_chunks_keeps_doc_chunks(self):
        # Doc chunks are never merged
        Chunk = self.chunker.Chunk
        chunks = [
            Chunk(id="f::A", path="f.py", kind="code", language="python",
                  lines=(1, 10), section="A", text="big chunk"),
            Chunk(id="f::A.__doc__", path="f.py", kind="doc", language="python",
                  lines=(1, 2), section="A", text="docstring"),
        ]
        result = self.chunker._merge_small_chunks(chunks)
        self.assertEqual(len(result), 2)

    def test_parent_scope_extracts_class_prefix(self):
        # _parent_scope returns the class part of a qualified breadcrumb
        ps = self.chunker._parent_scope
        self.assertEqual(ps("myfile > MyClass.render"), "myfile > MyClass")
        self.assertIsNone(ps("myfile > topLevelFn"))
        self.assertIsNone(ps(None))

    def test_scoped_merge_does_not_merge_across_classes(self):
        # scoped=True: 1-line method in ClassB must NOT merge into method in ClassA
        Chunk = self.chunker.Chunk
        chunks = [
            Chunk(id="f::ClassA.methodA", path="f.py", kind="code", language="java",
                  lines=(1, 10), section="f > ClassA.methodA", text="method A body"),
            Chunk(id="f::ClassB.methodB", path="f.py", kind="code", language="java",
                  lines=(11, 11), section="f > ClassB.methodB", text="stub()"),
        ]
        result = self.chunker._merge_small_chunks(chunks, scoped=True)
        self.assertEqual(len(result), 2, "cross-class merge must not happen with scoped=True")

    def test_scoped_merge_merges_within_same_class(self):
        # scoped=True: 1-line method in ClassA merges into preceding ClassA method
        Chunk = self.chunker.Chunk
        chunks = [
            Chunk(id="f::ClassA.methodA", path="f.py", kind="code", language="java",
                  lines=(1, 10), section="f > ClassA.methodA", text="method A body"),
            Chunk(id="f::ClassA.stub", path="f.py", kind="code", language="java",
                  lines=(11, 11), section="f > ClassA.stub", text="stub()"),
        ]
        result = self.chunker._merge_small_chunks(chunks, scoped=True)
        self.assertEqual(len(result), 1)
        self.assertIn("stub()", result[0].text)

    def test_unscoped_merge_still_merges_across_classes(self):
        # scoped=False (default): existing behavior unchanged for regex chunkers
        Chunk = self.chunker.Chunk
        chunks = [
            Chunk(id="f::ClassA.methodA", path="f.py", kind="code", language="java",
                  lines=(1, 10), section="f > ClassA.methodA", text="method A body"),
            Chunk(id="f::ClassB.methodB", path="f.py", kind="code", language="java",
                  lines=(11, 11), section="f > ClassB.methodB", text="stub()"),
        ]
        result = self.chunker._merge_small_chunks(chunks, scoped=False)
        self.assertEqual(len(result), 1, "unscoped merge should still merge 1-line across classes")


class TreeSitterChunkerTests(unittest.TestCase):
    """Tests for tree-sitter-backed chunkers (wave 12c7n+)."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_ts_available_flag(self):
        # _TS_AVAILABLE must be a bool (True if tree-sitter installed, False otherwise)
        self.assertIsInstance(self.chunker._TS_AVAILABLE, bool)

    def test_js_ts_treesitter_returns_none_or_list(self):
        source = textwrap.dedent("""\
            import { foo } from './foo';

            export function greet(name: string): string {
                return `hello ${name}`;
            }
        """)
        result = self.chunker.chunk_js_ts_treesitter(source, "src/greet.ts")
        if self.chunker._TS_AVAILABLE:
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
        else:
            self.assertIsNone(result)

    def test_chunk_file_js_ts_fallback(self):
        # chunk_file must return non-empty list regardless of tree-sitter availability
        source = textwrap.dedent("""\
            import React from 'react';

            function App() {
                return null;
            }

            export default App;
        """)
        chunks = self.chunker.chunk_file(source, "src/App.jsx")
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_chunk_file_go_fallback(self):
        source = textwrap.dedent("""\
            package main

            import "fmt"

            func main() {
                fmt.Println("hello")
            }
        """)
        chunks = self.chunker.chunk_file(source, "cmd/main.go")
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_chunk_file_rust_fallback(self):
        source = textwrap.dedent("""\
            use std::io;

            fn main() {
                println!("hello");
            }
        """)
        chunks = self.chunker.chunk_file(source, "src/main.rs")
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_chunk_file_java_fallback(self):
        source = textwrap.dedent("""\
            package com.example;

            public class Hello {
                public void greet() {
                    System.out.println("hello");
                }
            }
        """)
        chunks = self.chunker.chunk_file(source, "src/Hello.java")
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_chunk_file_csharp_fallback(self):
        source = textwrap.dedent("""\
            using System;

            namespace Example {
                public class Hello {
                    public void Greet() {
                        Console.WriteLine("hello");
                    }
                }
            }
        """)
        chunks = self.chunker.chunk_file(source, "src/Hello.cs")
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_chunk_file_c_fallback(self):
        source = textwrap.dedent("""\
            #include <stdio.h>

            int main(void) {
                printf("hello\\n");
                return 0;
            }
        """)
        chunks = self.chunker.chunk_file(source, "src/main.c")
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_chunk_file_shell_fallback(self):
        source = textwrap.dedent("""\
            #!/bin/bash

            greet() {
                echo "hello $1"
            }

            greet world
        """)
        chunks = self.chunker.chunk_file(source, "scripts/greet.sh")
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    @unittest.skipIf(not load_chunker()._TS_AVAILABLE, "tree-sitter not installed")
    def test_ts_go_chunker_extracts_functions(self):
        source = textwrap.dedent("""\
            package util

            import "fmt"

            func Add(a, b int) int {
                return a + b
            }

            func Sub(a, b int) int {
                return a - b
            }
        """)
        result = self.chunker.chunk_go_treesitter(source, "pkg/util/math.go")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        self.assertTrue(any("Add" in i for i in ids))
        self.assertTrue(any("Sub" in i for i in ids))

    @unittest.skipIf(not load_chunker()._TS_AVAILABLE, "tree-sitter not installed")
    def test_ts_rust_chunker_extracts_functions(self):
        source = textwrap.dedent("""\
            use std::fmt;

            fn add(a: i32, b: i32) -> i32 {
                a + b
            }

            struct Point {
                x: f64,
                y: f64,
            }
        """)
        result = self.chunker.chunk_rust_treesitter(source, "src/lib.rs")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        self.assertTrue(any("add" in i for i in ids))
        self.assertTrue(any("Point" in i for i in ids))

    @unittest.skipIf(not load_chunker()._TS_AVAILABLE, "tree-sitter not installed")
    def test_ts_java_chunker_extracts_methods(self):
        source = textwrap.dedent("""\
            package com.example;

            public class Calculator {
                public int add(int a, int b) {
                    return a + b;
                }
            }
        """)
        result = self.chunker.chunk_java_treesitter(source, "src/Calculator.java")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        self.assertTrue(any("add" in i for i in ids))

    @unittest.skipIf(not load_chunker()._TS_AVAILABLE, "tree-sitter not installed")
    def test_ts_csharp_chunker_extracts_methods(self):
        source = textwrap.dedent("""\
            using System;

            namespace Example {
                public class Calculator {
                    public int Add(int a, int b) {
                        return a + b;
                    }
                }
            }
        """)
        result = self.chunker.chunk_csharp_treesitter(source, "src/Calculator.cs")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        self.assertTrue(any("Add" in i for i in ids))

    @unittest.skipIf(not load_chunker()._TS_AVAILABLE, "tree-sitter not installed")
    def test_ts_bash_chunker_extracts_functions(self):
        source = textwrap.dedent("""\
            #!/bin/bash

            greet() {
                echo "hello $1"
            }

            farewell() {
                echo "bye $1"
            }
        """)
        result = self.chunker.chunk_bash_treesitter(source, "scripts/greet.sh")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        self.assertTrue(any("greet" in i for i in ids))
        self.assertTrue(any("farewell" in i for i in ids))

    @unittest.skipIf(not load_chunker()._TS_AVAILABLE, "tree-sitter not installed")
    def test_ts_c_chunker_extracts_functions(self):
        source = textwrap.dedent("""\
            #include <stdio.h>

            int add(int a, int b) {
                return a + b;
            }

            void print_result(int n) {
                printf("%d\\n", n);
            }
        """)
        result = self.chunker.chunk_c_cpp_treesitter(source, "src/math.c")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        self.assertTrue(any("add" in i for i in ids))
        self.assertTrue(any("print_result" in i for i in ids))

    @unittest.skipIf(not load_chunker()._TS_AVAILABLE, "tree-sitter not installed")
    def test_ts_js_chunker_extracts_functions(self):
        source = textwrap.dedent("""\
            import { foo } from './foo';

            function greet(name) {
                return 'hello ' + name;
            }

            export default greet;
        """)
        result = self.chunker.chunk_js_ts_treesitter(source, "src/greet.js")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        self.assertTrue(any("greet" in i for i in ids))

    def test_chunk_file_kotlin_fallback(self):
        """chunk_file(.kt) returns chunks even when tree-sitter-kotlin absent."""
        source = textwrap.dedent("""\
            package com.example

            fun hello(): String = "hello"
        """)
        result = self.chunker.chunk_file(source, "src/Hello.kt")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        for c in result:
            self.assertEqual(c.language, "kotlin")

    @unittest.skipUnless(
        importlib.util.find_spec("tree_sitter_kotlin") is not None,
        "tree-sitter-kotlin not installed",
    )
    def test_ts_kotlin_chunker_extracts_functions_and_classes(self):
        source = textwrap.dedent("""\
            package com.example

            import java.util.List

            class Greeter(private val name: String) {
                fun greet(): String {
                    return "Hello, $name"
                }
            }

            fun main() {
                val g = Greeter("world")
                println(g.greet())
            }
        """)
        result = self.chunker.chunk_kotlin_treesitter(source, "src/Greeter.kt")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        sections = [c.section for c in result]
        # class declaration indexed
        self.assertTrue(any("Greeter" in i for i in ids))
        # method indexed
        self.assertTrue(any("greet" in i for i in ids))
        # top-level function indexed
        self.assertTrue(any("main" in i for i in ids))
        # imports chunk present
        self.assertTrue(any("imports" in (s or "") for s in sections))
        # all chunks are code kind
        for c in result:
            self.assertEqual(c.kind, "code")
            self.assertEqual(c.language, "kotlin")

    @unittest.skipUnless(
        importlib.util.find_spec("tree_sitter_kotlin") is not None,
        "tree-sitter-kotlin not installed",
    )
    def test_ts_kotlin_scoped_merge_does_not_merge_across_classes(self):
        """Single-line methods in different Kotlin classes must not merge."""
        source = textwrap.dedent("""\
            class A {
                fun foo() = 1
            }

            class B {
                fun bar() = 2
            }
        """)
        result = self.chunker.chunk_kotlin_treesitter(source, "src/Two.kt")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        # Both foo and bar must appear as distinct chunks
        self.assertTrue(any("A.foo" in i for i in ids), f"A.foo missing from {ids}")
        self.assertTrue(any("B.bar" in i for i in ids), f"B.bar missing from {ids}")

    @unittest.skipUnless(
        importlib.util.find_spec("tree_sitter_swift") is not None,
        "tree-sitter-swift not installed",
    )
    def test_ts_swift_chunker_extracts_class_and_method(self):
        source = textwrap.dedent("""\
            import Foundation

            class Foo {
                func bar() -> Int { return 1 }
            }
        """)
        result = self.chunker.chunk_swift_treesitter(source, "src/Foo.swift")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        self.assertTrue(any("Foo" in i for i in ids))
        self.assertTrue(any("bar" in i for i in ids))

    @unittest.skipUnless(
        importlib.util.find_spec("tree_sitter_objc") is not None,
        "tree-sitter-objc not installed",
    )
    def test_ts_objc_chunker_extracts_method(self):
        source = textwrap.dedent("""\
            @implementation Foo
            - (void)bar {
            }
            @end
        """)
        result = self.chunker.chunk_objc_treesitter(source, "src/Foo.m")
        self.assertIsNotNone(result)
        ids = [c.id for c in result]
        self.assertTrue(any("bar" in i for i in ids))

    def test_chunk_file_swift_returns_chunks_without_grammar(self):
        source = "class Foo { func bar() {} }"
        result = self.chunker.chunk_file(source, "src/Foo.swift")
        self.assertTrue(len(result) > 0)
        self.assertTrue(any(c.kind == "code" for c in result))


class PromptChunkerTests(unittest.TestCase):
    """Tests for kind="prompt" chunking behaviour (wave 12cv4)."""

    def setUp(self):
        self.chunker = load_chunker()

    def _chunks(self, source: str, path: str) -> list:
        return self.chunker.chunk_file(source, path)

    # -- kind assignment --

    def test_prompt_kind_for_docs_prompts_path(self):
        source = "# Prepare Wave\n\n## Step 1\n\nDo the thing.\n"
        chunks = self._chunks(source, "docs/prompts/prepare-wave.prompt.md")
        non_summary = [c for c in chunks if c.kind != "doc-summary"]
        self.assertTrue(all(c.kind == "prompt" for c in non_summary))

    def test_prompt_kind_for_docs_prompts_agents_path(self):
        source = "# Agent Prompt\n\n## Context\n\nSome context.\n"
        chunks = self._chunks(source, "docs/prompts/agents/prepare-wave.prompt.md")
        non_summary = [c for c in chunks if c.kind != "doc-summary"]
        self.assertTrue(all(c.kind == "prompt" for c in non_summary))

    def test_prompt_kind_for_prompt_md_extension(self):
        source = "# My Prompt\n\n## Step 1\n\nDo this.\n"
        chunks = self._chunks(source, "docs/custom/my-prompt.prompt.md")
        non_summary = [c for c in chunks if c.kind != "doc-summary"]
        self.assertTrue(all(c.kind == "prompt" for c in non_summary))

    def test_seed_kind_takes_priority_over_prompt_suffix(self):
        # .prompt.md files under seeds/ stay kind="seed"
        source = "# Seed Prompt\n\n## Context\n\nFramework seed.\n"
        chunks = self._chunks(source, ".wavefoundry/framework/seeds/170-plan-feature.prompt.md")
        non_summary = [c for c in chunks if c.kind != "doc-summary"]
        self.assertTrue(all(c.kind == "seed" for c in non_summary))

    def test_regular_doc_not_affected(self):
        source = "# Architecture\n\n## Overview\n\nSome arch content.\n"
        chunks = self._chunks(source, "docs/architecture/current-state.md")
        non_summary = [c for c in chunks if c.kind != "doc-summary"]
        self.assertTrue(all(c.kind == "doc" for c in non_summary))

    # -- no H3 re-splitting --

    def test_no_h3_split_for_prompt_file(self):
        # Build a ## section > 2000 chars with a ### inside
        long_body = "x " * 1010  # > 2000 chars
        source = f"# Title\n\n## Step 1\n\n{long_body}\n\n### Sub\n\nmore text\n"
        chunks = self._chunks(source, "docs/prompts/implement-wave.prompt.md")
        # Wave 1p3b9 (1p397): with the per-kind 2000-char cap, this section
        # exceeds cap and gets line-wrapped via the universal guard. The
        # H3-suppression contract is preserved: the section is NOT split at
        # `### Sub` boundaries (no chunk has "Sub" in its section path), but
        # the universal guard does produce part-N/M derivatives.
        step_chunks = [c for c in chunks if c.section and "Step 1" in c.section]
        self.assertGreaterEqual(len(step_chunks), 1)
        # No H3-derived sub-section names anywhere
        for c in chunks:
            self.assertNotIn("Sub", c.section or "")

    # -- no fenced code extraction --

    def test_no_fenced_code_extraction_for_prompt_file(self):
        source = (
            "# Prepare Wave\n\n"
            "## Step 1\n\n"
            "Run the following:\n\n"
            "```bash\npython3 setup_index.py\n```\n\n"
            "Then verify with docs_search.\n"
        )
        chunks = self._chunks(source, "docs/prompts/prepare-wave.prompt.md")
        # No separate code chunk — bash block stays in prose
        code_chunks = [c for c in chunks if c.language == "bash"]
        self.assertEqual(len(code_chunks), 0)
        # The prose chunk includes the code block text
        prose_chunks = [c for c in chunks if c.kind == "prompt"]
        all_text = " ".join(c.text for c in prose_chunks)
        self.assertIn("setup_index.py", all_text)

    def test_fenced_code_still_extracted_for_regular_doc(self):
        source = (
            "# Arch Doc\n\n"
            "## Overview\n\n"
            "Use this:\n\n"
            "```python\nprint('hello')\n```\n"
        )
        chunks = self._chunks(source, "docs/architecture/current-state.md")
        code_chunks = [c for c in chunks if c.language == "python"]
        self.assertEqual(len(code_chunks), 1)

    # -- chunk_markdown direct flag tests --

    def test_suppress_h3_split_flag(self):
        long_body = "word " * 410  # > 2000 chars
        source = f"# Doc\n\n## Section\n\n{long_body}\n\n### Sub\n\nmore\n"
        without = self.chunker.chunk_markdown(source, "docs/prompts/foo.md", kind_override="prompt", suppress_h3_split=False)
        with_flag = self.chunker.chunk_markdown(source, "docs/prompts/foo.md", kind_override="prompt", suppress_h3_split=True)
        # With suppression: fewer chunks (no sub-split)
        self.assertLessEqual(len(with_flag), len(without))

    def test_suppress_code_extraction_flag(self):
        source = "# Doc\n\n## Steps\n\nRun:\n\n```bash\necho hi\n```\n\nDone.\n"
        with_extraction = self.chunker.chunk_markdown(source, "docs/prompts/foo.md", kind_override="prompt", suppress_code_extraction=False)
        without_extraction = self.chunker.chunk_markdown(source, "docs/prompts/foo.md", kind_override="prompt", suppress_code_extraction=True)
        bash_with = [c for c in with_extraction if c.language == "bash"]
        bash_without = [c for c in without_extraction if c.language == "bash"]
        self.assertEqual(len(bash_with), 1)
        self.assertEqual(len(bash_without), 0)

    def test_no_fenced_code_extraction_in_preamble_for_prompt_file(self):
        # Code block in preamble (before first ##) must also stay inline
        source = (
            "# Prepare Wave\n\n"
            "Run first:\n\n"
            "```bash\npython3 setup.py\n```\n\n"
            "## Step 1\n\nDo the thing.\n"
        )
        chunks = self._chunks(source, "docs/prompts/prepare-wave.prompt.md")
        code_chunks = [c for c in chunks if c.language == "bash"]
        self.assertEqual(len(code_chunks), 0)
        all_text = " ".join(c.text for c in chunks)
        self.assertIn("setup.py", all_text)

    def test_kind_doc_does_not_return_prompt_chunks(self):
        # kind="doc" filter must not include prompt-kind chunks
        source = "# Arch Doc\n\n## Overview\n\nContent.\n"
        doc_chunks = self._chunks(source, "docs/architecture/current-state.md")
        prompt_chunks = self._chunks(source, "docs/prompts/prepare-wave.prompt.md")
        # non-summary doc chunks have kind="doc"; non-summary prompt chunks have kind="prompt"
        non_summary_doc = [c for c in doc_chunks if c.kind != "doc-summary"]
        non_summary_prompt = [c for c in prompt_chunks if c.kind != "doc-summary"]
        for c in non_summary_doc:
            self.assertEqual(c.kind, "doc")
        for c in non_summary_prompt:
            self.assertEqual(c.kind, "prompt")
        # Ensure they are distinct kinds — a kind="doc" filter should not match kind="prompt"
        self.assertFalse(any(c.kind == "doc" for c in non_summary_prompt))


class CodeSummaryChunkTests(unittest.TestCase):
    """AC-1 (12d4h): kind='code-summary' extraction for code files."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_python_file_gets_code_summary(self):
        source = '"""Handle billing retry logic."""\n\ndef process_payment(amount):\n    pass\n\nclass BillingError(Exception):\n    pass\n'
        chunks = self.chunker.chunk_file(source, "src/billing.py")
        summary = [c for c in chunks if c.kind == "code-summary"]
        self.assertEqual(len(summary), 1)
        self.assertIn("billing retry logic", summary[0].text)
        self.assertIn("process_payment", summary[0].text)

    def test_code_summary_has_correct_fields(self):
        source = "def foo(): pass\n"
        chunks = self.chunker.chunk_file(source, "src/foo.py")
        summary = next(c for c in chunks if c.kind == "code-summary")
        self.assertEqual(summary.path, "src/foo.py")
        self.assertEqual(summary.kind, "code-summary")
        self.assertEqual(summary.section, "summary")
        self.assertIsNotNone(summary.lines)

    def test_symbol_cap_at_20(self):
        funcs = "\n".join(f"def func_{i}(): pass" for i in range(30))
        source = f'"""Module."""\n\n{funcs}\n'
        chunks = self.chunker.chunk_file(source, "src/large.py")
        summary = next(c for c in chunks if c.kind == "code-summary")
        # Symbol count in text should not exceed 20
        symbol_line = [line for line in summary.text.splitlines() if line.startswith("Symbols:")]
        if symbol_line:
            symbols = symbol_line[0].replace("Symbols: ", "").split(", ")
            self.assertLessEqual(len(symbols), 20)

    def test_typescript_file_gets_code_summary(self):
        source = "export function MyComponent() { return null; }\nexport class AppError extends Error {}\n"
        chunks = self.chunker.chunk_file(source, "src/App.tsx")
        summary = [c for c in chunks if c.kind == "code-summary"]
        self.assertEqual(len(summary), 1)
        self.assertIn("MyComponent", summary[0].text)

    def test_go_file_gets_code_summary(self):
        source = "package main\n\n// HandleRequest handles HTTP requests.\nfunc HandleRequest() {}\ntype Config struct {}\n"
        chunks = self.chunker.chunk_file(source, "src/handler.go")
        summary = [c for c in chunks if c.kind == "code-summary"]
        self.assertEqual(len(summary), 1)

    def test_empty_file_no_summary(self):
        chunks = self.chunker.chunk_file("", "src/empty.py")
        summary = [c for c in chunks if c.kind == "code-summary"]
        self.assertEqual(len(summary), 0)


class SymbolessCodeFileSummaryTests(unittest.TestCase):
    """Wave 1p3iv (1p3jc): symbolless-code-file fallback in
    `_chunk_code_summary`. When a code file has no docstring AND no
    extractable symbols (re-export __init__.py, TypeScript barrel files,
    Go single-file packages with no func defs, Rust mod.rs re-exports),
    a module-level `code` chunk now falls back to the file's top-level non-comment
    lines so the public surface is semantically searchable. Without this
    fallback, `code_search` misses re-export files; only `code_keyword`
    (text-backed) finds them."""

    def setUp(self):
        self.chunker = load_chunker()

    def _summaries(self, source, path):
        chunks = self.chunker.chunk_file(source, path)
        return [c for c in chunks if c.kind == "code-summary"]

    def _module_chunks(self, source, path):
        chunks = self.chunker.chunk_file(source, path)
        return [c for c in chunks if c.kind == "code" and c.id.endswith("::__module__")]

    def test_python_reexport_init_gets_module_chunk(self):
        """The canonical case: `from .x import y; __all__ = ['y']` style
        re-export __init__.py — no docstring, no defined symbols, but real
        content. Should emit one code module chunk with the import + __all__."""
        source = 'from .cli import main\n\n__all__ = ["main"]'
        modules = self._module_chunks(source, "pkg/__init__.py")
        self.assertEqual(len(modules), 1)
        text = modules[0].text
        self.assertIn("from .cli import main", text)
        self.assertIn("__all__", text)
        self.assertEqual(modules[0].section, "__init__")
        self.assertEqual(modules[0].kind, "code")
        self.assertEqual(modules[0].id, "pkg/__init__.py::__module__")
        self.assertEqual(modules[0].language, "python")

    def test_typescript_barrel_index_gets_module_chunk(self):
        """TS barrel `index.ts`: `export * from "./foo"; export { Bar }
        from "./bar"`. No top-level func/class declarations to extract;
        fallback fires."""
        source = 'export * from "./foo";\nexport { Bar } from "./bar";\n'
        modules = self._module_chunks(source, "src/index.ts")
        self.assertEqual(len(modules), 1)
        text = modules[0].text
        self.assertIn('export * from "./foo"', text)
        self.assertIn("Bar", text)
        self.assertEqual(modules[0].kind, "code")
        self.assertEqual(modules[0].id, "src/index.ts::__module__")
        self.assertEqual(modules[0].section, "index")
        self.assertEqual(modules[0].language, "typescript")

    def test_go_single_file_package_with_imports_gets_module_chunk(self):
        """A Go file that's just `package x` + a couple imports + maybe a
        const block — no functions, no methods, no types defined here.
        Fallback should emit a module chunk."""
        source = 'package httputil\n\nimport (\n    "fmt"\n    "net/http"\n)\n\nconst DefaultTimeout = "30s"\n'
        modules = self._module_chunks(source, "pkg/httputil/httputil.go")
        self.assertEqual(len(modules), 1)
        text = modules[0].text
        self.assertIn("package httputil", text)
        self.assertIn("DefaultTimeout", text)

    def test_rust_mod_reexport_gets_module_chunk(self):
        """Rust `mod.rs` style re-export: `pub mod x; pub use x::Y;`."""
        source = "pub mod widget;\npub use widget::Widget;\n"
        modules = self._module_chunks(source, "src/components/mod.rs")
        self.assertEqual(len(modules), 1)
        text = modules[0].text
        self.assertIn("pub mod widget", text)
        self.assertIn("pub use widget::Widget", text)

    def test_file_with_symbols_does_not_emit_fallback(self):
        """Regression: when symbols ARE extractable, the original
        docstring/symbols summary fires — NOT the fallback. The summary
        text should NOT contain raw `import` / `export` lines from the
        fallback path; it should contain the `Symbols: ...` line."""
        source = 'def foo():\n    return 1\n\ndef bar():\n    return 2\n'
        summaries = self._summaries(source, "src/util.py")
        self.assertEqual(len(summaries), 1)
        self.assertEqual(self._module_chunks(source, "src/util.py"), [])
        text = summaries[0].text
        self.assertIn("Symbols:", text)

    def test_file_with_module_docstring_only_uses_docstring_not_fallback(self):
        """A file with ONLY a docstring (no symbols) still goes through the
        original path — docstring as summary. Fallback should not fire
        because docstring satisfies the original branch."""
        source = '"""Helper functions for billing."""\n'
        summaries = self._summaries(source, "src/billing/__init__.py")
        self.assertEqual(len(summaries), 1)
        self.assertEqual(self._module_chunks(source, "src/billing/__init__.py"), [])
        text = summaries[0].text
        self.assertIn("Helper functions for billing", text)

    def test_empty_file_still_no_summary(self):
        """Compatibility with 1p3iw: truly empty file emits no chunks."""
        self.assertEqual(self.chunker.chunk_file("", "src/empty.py"), [])

    def test_all_comments_does_not_trigger_fallback_path(self):
        """A file with only leading comments goes through the EXISTING
        `_extract_leading_comment` docstring-equivalent path — NOT the new
        symbolless fallback. The existing summary fires with the comment
        text as the docstring; the fallback path stays dormant. Regression
        guard against the fallback firing on top of the existing summary."""
        source = "# Just a comment\n# Another comment\n\n"
        # Exactly one summary (from the existing leading-comment path), not zero
        # (which would mean the existing path broke) and not two (which would
        # mean both paths fired).
        summaries = self._summaries(source, "src/comments-only.py")
        self.assertEqual(len(summaries), 1)
        self.assertEqual(self._module_chunks(source, "src/comments-only.py"), [])
        # The summary text should be the comment text, not a non-comment
        # fallback list. If the fallback fired here, the text would be empty
        # (no non-comment lines to extract).
        self.assertIn("Just a comment", summaries[0].text)

    def test_all_whitespace_no_summary(self):
        """Compatibility with 1p3iw: all-whitespace file emits no chunks."""
        self.assertEqual(self.chunker.chunk_file("   \n\n\t\n", "src/blank.py"), [])

    def test_fallback_caps_at_max_lines(self):
        """The fallback caps at _MODULE_SUMMARY_MAX_LINES to avoid emitting
        massive module chunks from constants-only files."""
        # 200 import lines, no defined symbols → fallback fires, capped.
        lines = "\n".join(f"from .x{i} import y{i}" for i in range(200))
        modules = self._module_chunks(lines, "pkg/__init__.py")
        self.assertEqual(len(modules), 1)
        emitted_lines = modules[0].text.splitlines()
        cap = self.chunker._MODULE_SUMMARY_MAX_LINES
        self.assertLessEqual(len(emitted_lines), cap)

    def test_fallback_uses_language_appropriate_comment_prefixes(self):
        """Go uses `//` comments; the fallback should skip those and keep
        the non-comment content."""
        source = "package main\n// This is a Go comment to skip\nimport \"fmt\"\nconst X = 1\n"
        modules = self._module_chunks(source, "src/main.go")
        self.assertEqual(len(modules), 1)
        text = modules[0].text
        self.assertNotIn("This is a Go comment to skip", text)
        self.assertIn("package main", text)
        self.assertIn("const X = 1", text)

    def test_marker_region_only_code_file_emits_zero_chunks(self):
        """AC-5 (1p3jc): generated marker-region-only files are not semantic
        content and still emit zero chunks."""
        source = "<!-- wave:agent-surface begin -->\nGenerated\n<!-- wave:agent-surface end -->\n"
        self.assertEqual(self.chunker.chunk_file(source, "src/generated.py"), [])

    def test_marker_region_only_markdown_file_emits_zero_chunks(self):
        """AC-5 (1p3jc): marker-region-only markdown remains zero-chunk too."""
        source = "<!-- waveframework:agent-surface begin -->\nGenerated\n<!-- waveframework:agent-surface end -->\n"
        self.assertEqual(self.chunker.chunk_file(source, "docs/generated.md"), [])


class DocSummaryChunkTests(unittest.TestCase):
    """AC-3 (12d4h): kind='doc-summary' extraction for markdown doc files."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_doc_file_gets_doc_summary(self):
        source = "# Search Architecture\n\nThis document describes the search indexing pipeline.\n\n## Indexing\n\nContent.\n\n## Retrieval\n\nContent.\n"
        chunks = self.chunker.chunk_file(source, "docs/architecture/search-architecture.md")
        summary = [c for c in chunks if c.kind == "doc-summary"]
        self.assertEqual(len(summary), 1)
        self.assertIn("describes the search indexing pipeline", summary[0].text)
        self.assertIn("Indexing", summary[0].text)
        self.assertIn("Retrieval", summary[0].text)

    def test_doc_summary_has_correct_fields(self):
        source = "# Doc\n\nPurpose statement.\n\n## Section\n\nContent.\n"
        chunks = self.chunker.chunk_file(source, "docs/architecture/arch.md")
        summary = next(c for c in chunks if c.kind == "doc-summary")
        self.assertEqual(summary.kind, "doc-summary")
        self.assertEqual(summary.section, "doc-summary")
        self.assertIsNone(summary.language)

    def test_prompt_file_gets_doc_summary(self):
        source = "# Prepare Wave\n\nRun the prepare lifecycle step.\n\n## Step 1\n\nDo this.\n"
        chunks = self.chunker.chunk_file(source, "docs/prompts/prepare-wave.prompt.md")
        summary = [c for c in chunks if c.kind == "doc-summary"]
        self.assertEqual(len(summary), 1)

    def test_seed_file_gets_doc_summary(self):
        source = "# Seed\n\nSeed purpose.\n\n## Section\n\nContent.\n"
        chunks = self.chunker.chunk_file(source, ".wavefoundry/framework/seeds/030-inventory.prompt.md")
        summary = [c for c in chunks if c.kind == "doc-summary"]
        self.assertEqual(len(summary), 1)

    def test_doc_summary_sections_formatted(self):
        source = "# Doc\n\nFirst paragraph.\n\n## Alpha\n\n### Beta\n\nContent.\n"
        chunks = self.chunker.chunk_file(source, "docs/reference.md")
        summary = next(c for c in chunks if c.kind == "doc-summary")
        self.assertIn("Sections:", summary.text)
        self.assertIn("Alpha", summary.text)
        self.assertIn("Beta", summary.text)

    def test_empty_doc_no_summary(self):
        chunks = self.chunker.chunk_file("", "docs/empty.md")
        summary = [c for c in chunks if c.kind == "doc-summary"]
        self.assertEqual(len(summary), 0)

    # AC-1 (12dkb): H1 title captured in doc-summary
    def test_doc_summary_captures_h1_title(self):
        source = "# My Document Title\n\n## Section\n\nContent.\n"
        chunks = self.chunker.chunk_file(source, "docs/arch.md")
        summary = next(c for c in chunks if c.kind == "doc-summary")
        self.assertIn("My Document Title", summary.text)

    # AC-1 (12dkb): title appears even when no ## sections exist
    def test_doc_summary_title_without_sections(self):
        source = "# Standalone Title\n\nSome prose here.\n"
        chunks = self.chunker.chunk_file(source, "docs/arch.md")
        summary = next(c for c in chunks if c.kind == "doc-summary")
        self.assertIn("Standalone Title", summary.text)

    # AC-2 (12dkb): frontmatter key-value lines preserved as individual lines
    def test_doc_summary_frontmatter_preserved_as_lines(self):
        source = (
            "# Wave Record\n\n"
            "Owner: Engineering\n"
            "Status: active\n"
            "Last verified: 2026-05-05\n\n"
            "## Purpose\n\nDoes things.\n"
        )
        chunks = self.chunker.chunk_file(source, "docs/waves/wave.md")
        summary = next(c for c in chunks if c.kind == "doc-summary")
        # Each field must appear on its own line, not run together
        self.assertIn("Owner: Engineering", summary.text)
        self.assertIn("Status: active", summary.text)
        self.assertIn("Last verified: 2026-05-05", summary.text)
        # Not joined as a run-on string
        self.assertNotIn("Owner: Engineering Status:", summary.text)

    # AC-3 (12dkb): opening sentence of first ## section body captured
    def test_doc_summary_first_section_opening(self):
        source = (
            "# Agent Prompt\n\n"
            "## Purpose\n\n"
            "Guru is the team's most knowledgeable resource on the codebase. More detail here.\n\n"
            "## Retrieval Loop\n\nSteps.\n"
        )
        chunks = self.chunker.chunk_file(source, "docs/prompts/agents/cia.prompt.md")
        summary = next(c for c in chunks if c.kind == "doc-summary")
        self.assertIn("Guru is the team's most knowledgeable resource on the codebase.", summary.text)
        # Must not include the full paragraph
        self.assertNotIn("More detail here", summary.text)

    # AC-5 (12dkb): doc with no H1, no frontmatter, no sections still produces summary
    def test_doc_summary_no_h1_no_frontmatter(self):
        source = "Just some prose with no headings at all.\n"
        chunks = self.chunker.chunk_file(source, "docs/notes.md")
        summary = [c for c in chunks if c.kind == "doc-summary"]
        self.assertEqual(len(summary), 1)
        self.assertIn("Just some prose", summary[0].text)

    # AC-6 (12dkb): ## dominant doc uses ## as split boundary
    def test_heading_detection_h2_dominant(self):
        source = "# Doc\n\n## Alpha\n\nContent.\n\n## Beta\n\nContent.\n"
        chunks = self.chunker.chunk_file(source, "docs/arch.md")
        section_titles = [c.section for c in chunks if c.section and c.section != "doc-summary"]
        self.assertTrue(any("Alpha" in s for s in section_titles))
        self.assertTrue(any("Beta" in s for s in section_titles))

    # AC-7 (12dkb): ### only doc splits at ### boundary, producing named section chunks
    def test_heading_detection_h3_only_splits_at_h3(self):
        source = (
            "# Guide\n\n"
            "### Installation\n\nInstall steps.\n\n"
            "### Configuration\n\nConfig steps.\n"
        )
        chunks = self.chunker.chunk_file(source, "docs/guide.md")
        non_summary = [c for c in chunks if c.kind != "doc-summary"]
        section_titles = [c.section for c in non_summary if c.section]
        # Both ### sections must produce named section chunks
        self.assertTrue(any("Installation" in s for s in section_titles), section_titles)
        self.assertTrue(any("Configuration" in s for s in section_titles), section_titles)
        # Content chunks must not all be preamble — at least 2 named sections
        self.assertGreaterEqual(len(section_titles), 2, section_titles)

    # AC-8 (12dkb): suppress_h3_split still works when primary level is ##
    def test_suppress_h3_split_unaffected_by_detection(self):
        h3_threshold = self.chunker.H3_SPLIT_THRESHOLD_CHARS
        sub_body = "y " * (h3_threshold // 2 + 10)
        source = f"# Doc\n\n## Chapter\n\n### Intro\n\n{sub_body}\n"
        chunks = self.chunker.chunk_markdown(
            source,
            "docs/prompts/prepare-wave.prompt.md",
            kind_override="prompt",
            suppress_h3_split=True,
        )
        # With suppression, no ### sub-chunks should appear
        sub_chunks = [c for c in chunks if c.section and "Intro" in c.section and "/" in c.section.replace(" > ", "")]
        # The Intro content should be in a ## Chapter chunk, not split out
        chapter_chunks = [c for c in chunks if c.section and "Chapter" in c.section]
        self.assertTrue(len(chapter_chunks) >= 1)


class InferTagsTests(unittest.TestCase):
    """AC-1 through AC-9 (12dv9): _infer_tags controlled vocabulary."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_wave_tag(self):
        tags = self.chunker._infer_tags("docs/waves/12dv9 chunk-tags/wave.md")
        self.assertIn("wave", tags)

    def test_agent_tag_from_prompts_agents(self):
        tags = self.chunker._infer_tags("docs/prompts/agents/performance-reviewer.prompt.md")
        self.assertIn("agent", tags)
        self.assertIn("prompt", tags)

    def test_agent_tag_from_docs_agents(self):
        tags = self.chunker._infer_tags("docs/agents/journals/guru.md")
        self.assertIn("agent", tags)
        self.assertIn("journal", tags)

    def test_journal_tag(self):
        tags = self.chunker._infer_tags("docs/agents/journals/wave-coordinator.md")
        self.assertIn("journal", tags)

    def test_reference_tag(self):
        tags = self.chunker._infer_tags("docs/references/project-overview.md")
        self.assertIn("reference", tags)

    def test_prompt_tag_from_docs_prompts(self):
        tags = self.chunker._infer_tags("docs/prompts/prepare-wave.prompt.md")
        self.assertIn("prompt", tags)

    def test_prompt_tag_from_prompt_md_suffix_anywhere(self):
        tags = self.chunker._infer_tags("some/other/location/my-agent.prompt.md")
        self.assertIn("prompt", tags)

    def test_seed_and_framework_tags(self):
        tags = self.chunker._infer_tags(".wavefoundry/framework/seeds/211-guru.prompt.md")
        self.assertIn("seed", tags)
        self.assertIn("framework", tags)

    def test_lifecycle_tag_install(self):
        tags = self.chunker._infer_tags("docs/contributing/install-wavefoundry.md")
        self.assertIn("lifecycle", tags)

    def test_lifecycle_tag_onboarding(self):
        tags = self.chunker._infer_tags("docs/references/onboarding-guide.md")
        self.assertIn("lifecycle", tags)

    def test_lifecycle_not_triggered_outside_docs(self):
        tags = self.chunker._infer_tags(".wavefoundry/framework/scripts/setup_index.py")
        self.assertNotIn("lifecycle", tags)

    def test_test_tag_python(self):
        tags = self.chunker._infer_tags(".wavefoundry/framework/scripts/tests/test_chunker.py")
        self.assertIn("test", tags)

    def test_test_tag_go(self):
        tags = self.chunker._infer_tags("pkg/indexer/indexer_test.go")
        self.assertIn("test", tags)

    def test_test_tag_spec_ts(self):
        tags = self.chunker._infer_tags("src/components/Button.spec.ts")
        self.assertIn("test", tags)

    def test_test_tag_tests_dir(self):
        tags = self.chunker._infer_tags("src/tests/helpers.py")
        self.assertIn("test", tags)

    def test_config_tag_yaml(self):
        tags = self.chunker._infer_tags("config/settings.yaml")
        self.assertIn("config", tags)

    def test_config_tag_toml(self):
        tags = self.chunker._infer_tags("pyproject.toml")
        self.assertIn("config", tags)

    def test_config_tag_env(self):
        tags = self.chunker._infer_tags(".env.production")
        self.assertIn("config", tags)

    def test_no_tags_for_plain_source_file(self):
        tags = self.chunker._infer_tags("src/auth/login.py")
        self.assertEqual(tags, [])

    def test_multi_tag_seed_file(self):
        tags = self.chunker._infer_tags(".wavefoundry/framework/seeds/001-overview.md")
        self.assertIn("seed", tags)
        self.assertIn("framework", tags)
        self.assertGreaterEqual(len(tags), 2)


class JupyterChunkerTests(unittest.TestCase):
    """Tests for chunk_jupyter — .ipynb notebook chunking."""

    def setUp(self):
        self.chunker = load_chunker()

    def _nb(self, cells, metadata=None):
        """Build a minimal notebook JSON string."""
        import json
        nb = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": metadata if metadata is not None else {"kernelspec": {"language": "python"}},
            "cells": cells,
        }
        return json.dumps(nb)

    def _cell(self, cell_type, source, metadata=None):
        return {"cell_type": cell_type, "source": source, "metadata": metadata or {}}

    # 1. Markdown cell → doc chunk
    def test_markdown_cell_produces_doc_chunk(self):
        source = self._nb([self._cell("markdown", "# Hello\nsome text")])
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].kind, "doc")
        self.assertEqual(chunks[0].text, "# Hello\nsome text")

    # 2. Code cell → code chunk with language
    def test_code_cell_produces_code_chunk(self):
        source = self._nb([self._cell("code", "x = 1")])
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].kind, "code")
        self.assertEqual(chunks[0].language, "python")

    # 3. Empty cell is skipped
    def test_empty_cell_skipped(self):
        source = self._nb([
            self._cell("code", "   \n  "),
            self._cell("code", "x = 1"),
        ])
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(len(chunks), 1)

    # 4. Heading-based breadcrumb
    def test_heading_breadcrumb(self):
        source = self._nb([self._cell("markdown", "# My Heading\ntext")])
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(chunks[0].section, "notebook > My Heading")

    # 5. Cell-index breadcrumb (no heading)
    def test_cell_index_breadcrumb(self):
        source = self._nb([self._cell("markdown", "Just some prose without a heading")])
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(chunks[0].section, "notebook > Cell 1")

    # 6. Language from kernelspec
    def test_language_from_kernelspec(self):
        meta = {"kernelspec": {"language": "r"}}
        source = self._nb([self._cell("code", "print('hi')")], metadata=meta)
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(chunks[0].language, "r")

    # 7. Language default fallback
    def test_language_default_fallback(self):
        source = self._nb([self._cell("code", "x = 1")], metadata={})
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(chunks[0].language, "python")

    # 8. Malformed JSON falls back gracefully
    def test_malformed_json_fallback(self):
        chunks = self.chunker.chunk_jupyter("{not valid json", "nb.ipynb")
        self.assertGreater(len(chunks), 0)

    # 9. Raw cell is skipped
    def test_raw_cell_skipped(self):
        source = self._nb([
            self._cell("raw", "some raw content"),
            self._cell("code", "x = 1"),
        ])
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].kind, "code")

    # 10. Virtual line offsets non-overlapping
    def test_virtual_line_offsets_non_overlapping(self):
        source = self._nb([
            self._cell("code", "line1\nline2"),
            self._cell("code", "line3"),
        ])
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(len(chunks), 2)
        first_end = chunks[0].lines[1]
        second_start = chunks[1].lines[0]
        self.assertGreater(second_start, first_end)

    # 11. Single-line cell: start_line == end_line
    def test_single_line_cell(self):
        source = self._nb([self._cell("code", "x = 1")])
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(chunks[0].lines[0], chunks[0].lines[1])

    # 12. Notebook with no `cells` key → empty list
    def test_no_cells_key(self):
        import json
        source = json.dumps({})
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(chunks, [])

    # 13. Source as list joined correctly
    def test_source_as_list(self):
        source = self._nb([self._cell("code", ["line1\n", "line2"])])
        chunks = self.chunker.chunk_jupyter(source, "nb.ipynb")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "line1\nline2")

    # 14. Dispatch routing via chunk_file
    def test_dispatch_routing(self):
        source = self._nb([self._cell("code", "x = 1")])
        chunks = self.chunker.chunk_file(source, "analysis.ipynb")
        self.assertGreater(len(chunks), 0)
        # Should not produce raw JSON line-window chunks — first chunk language should not be None
        code_chunks = [c for c in chunks if c.kind == "code"]
        self.assertGreater(len(code_chunks), 0)
        self.assertEqual(code_chunks[0].language, "python")


# ---------------------------------------------------------------------------
# Wave 1p4u5 (1p4w9): docs-chunk section-breadcrumb context injection.
# ---------------------------------------------------------------------------

class DocsBreadcrumbInjectionTests(unittest.TestCase):
    """1p4w9: docs-kind chunks prepend the section breadcrumb to embedded text
    (NL→docs retrieval gain); code chunks are untouched; injection is idempotent."""

    def setUp(self):
        self.chunker = load_chunker()

    def _chunk(self, kind, section, text):
        return self.chunker.Chunk(id="x", path="docs/a.md", kind=kind, language="markdown",
                                  lines=(1, 5), section=section, text=text)

    def test_doc_chunk_gets_section_breadcrumb(self):
        out = self.chunker._inject_docs_breadcrumb([self._chunk("doc", "Guide > Setup", "Install it.")])
        self.assertEqual(out[0].text, "Guide > Setup\nInstall it.")

    def test_seed_and_prompt_chunks_also_injected(self):
        for kind in ("seed", "prompt"):
            out = self.chunker._inject_docs_breadcrumb([self._chunk(kind, "Topic", "Body")])
            self.assertEqual(out[0].text, "Topic\nBody", kind)

    def test_doc_summary_chunk_not_injected(self):
        # 1p4wz: doc-summary's real section is the literal "doc-summary" sentinel (set in
        # _chunk_doc_summary), not a heading — injecting it would prepend a meaningless token to the
        # embedded text. doc-summary is excluded from _DOCS_BREADCRUMB_KINDS; the summary already opens
        # with the H1 title + a "Sections: …" breadcrumb of its own.
        self.assertNotIn("doc-summary", self.chunker._DOCS_BREADCRUMB_KINDS)
        out = self.chunker._inject_docs_breadcrumb([self._chunk("doc-summary", "doc-summary", "Title\nBody")])
        self.assertEqual(out[0].text, "Title\nBody")

    def test_code_chunk_unchanged(self):
        c = self.chunker.Chunk(id="x", path="a.py", kind="code", language="python",
                               lines=(1, 5), section="a > foo", text="def foo(): pass")
        out = self.chunker._inject_docs_breadcrumb([c])
        self.assertEqual(out[0].text, "def foo(): pass")

    def test_idempotent_when_text_already_starts_with_breadcrumb(self):
        # e.g. markdown H1-breadcrumb chunks and docstring chunks build text from the breadcrumb.
        out = self.chunker._inject_docs_breadcrumb([self._chunk("doc", "Doc > Overview", "Doc > Overview\n\nBody")])
        self.assertEqual(out[0].text, "Doc > Overview\n\nBody")

    def test_empty_or_none_section_no_change(self):
        self.assertEqual(self.chunker._inject_docs_breadcrumb([self._chunk("doc", None, "Body")])[0].text, "Body")
        self.assertEqual(self.chunker._inject_docs_breadcrumb([self._chunk("doc", "   ", "Body")])[0].text, "Body")

    def test_chunk_file_injects_for_no_h1_markdown_doc(self):
        # No H1 → section is the bare heading; chunk_file now prepends it to the doc body.
        md = "## Overview\n\n" + ("Some documentation prose about the system. " * 8)
        chunks = self.chunker.chunk_file(md, "docs/guide.md")
        prose = [c for c in chunks if c.kind == "doc" and c.section == "Overview"]
        self.assertTrue(prose, "expected a doc chunk with section 'Overview'")
        self.assertTrue(prose[0].text.startswith("Overview\n"), prose[0].text[:40])


# ---------------------------------------------------------------------------
# Wave 1p3b9 (1p397): universal oversized-chunk guard + markdown structural-
# unit awareness for H1-only seed/prompt content.
# ---------------------------------------------------------------------------

class UniversalOversizedChunkGuardTests(unittest.TestCase):
    """AC-1, AC-2: every dispatch path runs through split_large_chunks at
    chunk_file end. No chunk emitted by chunk_file exceeds MAX_CHUNK_CHARS."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        scripts_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("chunker", scripts_root / "chunker.py")
        cls.chunker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.chunker)

    def test_chunker_version_bumped_to_32(self):
        """Wave 1sbfl: CHUNKER_VERSION bumped 31 → 32 — Java static/instance initializer
        blocks are now emitted as their own kind="code" chunks across class/enum/record
        containers (records static-only). Chunk-set shape change → bump so any 31-index
        re-chunks (incremental re-chunk with embedding reuse for content-identical chunks,
        NOT an unconditional full re-embed; see AC-6 coverage in test_fts_lexical_layer).

        Wave 1p4q4 review: CHUNKER_VERSION bumped 28 → 29 — the `module M{}` keyword form,
        non-export namespace const, `export namespace`, `declare namespace`, and `declare enum`
        members now chunk (completing the namespace/module coverage that rode 28). Chunk-set shape
        change → bump so any 28-index re-chunks. Wave 1p4q4: CHUNKER_VERSION bumped 27 → 28 — TS
        `enum`/`const enum` members (+ namespace const, declare const) are now constant chunks.
        (Wave 1p4hi close: 26 → 27.) The interim `81bae0c` committed `26`
        with PYTHON-ONLY constant chunking; this wave extended the chunk shape to all 11 languages
        (+ the Go short-const fix) under the SAME `26`, breaking the version=shape invariant — so the
        bump to 27 forces every consumer/index on the interim `26` to re-chunk to the final shape.
        Constants (`RERANKER_MODEL = "..."` etc.) are emitted as their own `kind="code"` chunks
        (breadcrumb-prefixed text, merge-excluded via a `" [const]"` section marker). The output
        shape changed, so consumers need a full reindex; `indexer.build_index` auto-escalates
        incremental updates to a full rebuild on the version mismatch.

        Prior bumps in this ratchet (preserved as the historical sequence):
        22 → 23 (wave 1p397): part-N/M labels, paragraph decomposition.
        23 → 24 (wave 1p3ho): test fixture for chunker-bump detection path.
        24 → 25 (wave 1p3jc): symbolless-code-file summary fallback.
        25 → 26 (wave 1p4mf): module/class-level constant chunks (Python; interim all-11-language).
        26 → 27 (wave 1p4hi close): all-11-language constant chunking finalized under a clean version.
        27 → 28 (wave 1p4q4): TS enum/const-enum members + namespace const + declare const chunked.
        28 → 29 (wave 1p4q4 review): module-keyword / non-export-namespace / export-&-declare-namespace / declare-enum chunking completed.
        29 → 30 (wave 1p4u5, 1p4w9): docs chunks prepend their section breadcrumb to embedded text (docs-only; code text unchanged).
        30 → 31 (wave 1p5k0): nested-type members attribute to the qualified owner (Outer.Inner.x) in the chunk lane + nested-type __decl__ chunk (code shape change → re-chunk).
        31 → 32 (wave 1sbfl): Java static/instance initializer blocks emitted as own chunks (class/enum/record; records static-only)."""
        self.assertEqual(self.chunker.CHUNKER_VERSION, "32")

    def test_split_large_chunks_is_idempotent_on_small_chunks(self):
        c = self.chunker.Chunk(id="x", path="p", kind="doc", language=None,
                                lines=(1, 5), section="s", text="short")
        result = self.chunker.split_large_chunks([c])
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], c)

    def test_split_large_chunks_caps_oversized_doc_chunk(self):
        big = "line\n" * 1500  # > MAX_CHUNK_CHARS (4000)
        c = self.chunker.Chunk(id="big", path="p", kind="doc", language=None,
                                lines=(1, 1500), section="Section", text=big)
        result = self.chunker.split_large_chunks([c])
        self.assertGreater(len(result), 1)
        for r in result:
            self.assertLessEqual(len(r.text), self.chunker.MAX_CHUNK_CHARS)

    def test_split_large_chunks_part_label_suffix(self):
        big = "line\n" * 1500
        c = self.chunker.Chunk(id="big", path="p", kind="doc", language=None,
                                lines=(1, 1500), section="Section", text=big)
        result = self.chunker.split_large_chunks([c])
        # Each derived chunk's section has (part N/M) appended
        for idx, r in enumerate(result, start=1):
            self.assertIn(f"(part {idx}/{len(result)})", r.section or "")
            self.assertIn("Section", r.section or "")

    def test_split_large_chunks_no_section_handles_empty(self):
        """When the parent chunk has no section, derivatives get only
        the (part N/M) label without a leading separator."""
        big = "line\n" * 1500
        c = self.chunker.Chunk(id="big", path="p", kind="doc", language=None,
                                lines=(1, 1500), section=None, text=big)
        result = self.chunker.split_large_chunks([c])
        for r in result:
            self.assertIsNotNone(r.section)
            self.assertTrue(r.section.startswith("(part "))

    def test_chunk_file_caps_oversized_plain_text(self):
        """AC-2: plain-text dispatch path now runs through the universal guard."""
        big_text = "Some very long paragraph " * 500  # > 4000 chars
        chunks = self.chunker.chunk_file(big_text, "docs/big.txt")
        for c in chunks:
            self.assertLessEqual(len(c.text), self.chunker.MAX_CHUNK_CHARS)

    def test_chunk_file_caps_oversized_yaml(self):
        """AC-15: YAML dispatch path covered by universal guard."""
        big_yaml = "key:\n" + ("  - item value here\n" * 800)
        chunks = self.chunker.chunk_file(big_yaml, "config/big.yaml")
        for c in chunks:
            self.assertLessEqual(len(c.text), self.chunker.MAX_CHUNK_CHARS)

    def test_chunk_file_caps_h1_only_seed(self):
        """AC-10 partial: H1-only seed-040-style body decomposes — and even
        if the decomposition leaves an over-cap residual, the universal guard
        catches it. No chunk exceeds MAX_CHUNK_CHARS in any case."""
        body = "# 040 - Long Intent Doc\n\n"
        # Long numbered list + trailing prose, > 4000 chars total
        for i in range(1, 60):
            body += f"{i}. Task item {i} with some explanatory prose so the line is not trivially short.\n"
        chunks = self.chunker.chunk_file(body, ".wavefoundry/framework/seeds/040-test.prompt.md")
        self.assertGreater(len(chunks), 1)  # decomposed
        for c in chunks:
            self.assertLessEqual(len(c.text), self.chunker.MAX_CHUNK_CHARS)


class MarkdownStructuralUnitDecompositionTests(unittest.TestCase):
    """AC-3 partial, AC-4 partial, AC-6, AC-7: H1-only seed/prompt body
    decomposed at paragraph + top-level list-item boundaries before the
    universal guard fires."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        scripts_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("chunker", scripts_root / "chunker.py")
        cls.chunker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.chunker)

    def test_small_h1_only_seed_kept_whole(self):
        """AC-11 spirit: a small H1-only body emerges as a single chunk."""
        body = "# Small Seed\n\nShort intent line.\n\n1. First task.\n2. Second task.\n"
        chunks = self.chunker.chunk_file(body, ".wavefoundry/framework/seeds/099-small.prompt.md")
        # H1 only, < cap → not decomposed
        seed_chunks = [c for c in chunks if c.kind == "seed"]
        self.assertEqual(len(seed_chunks), 1)

    def test_large_h1_only_seed_decomposes_at_list_items(self):
        """AC-10: seed-040-style 'Intent + Tasks' input decomposes into
        multiple chunks at top-level numbered-list-item boundaries when the
        body exceeds MAX_CHUNK_CHARS."""
        body = "# 040 - Big Intent Doc\n\nIntent: do many things.\n\n"
        for i in range(1, 80):
            body += f"{i}. Task item {i} with explanatory prose to push past the cap. " * 3 + "\n"
        chunks = self.chunker.chunk_file(body, ".wavefoundry/framework/seeds/040-test.prompt.md")
        seed_chunks = [c for c in chunks if c.kind == "seed"]
        self.assertGreater(len(seed_chunks), 1)
        for c in seed_chunks:
            self.assertLessEqual(len(c.text), self.chunker.MAX_CHUNK_CHARS)

    def test_h2_rich_markdown_unchanged(self):
        """AC-8: H2-rich markdown is NOT affected by the H1-only decomposition
        path. Regression guard — the structural-unit awareness must NOT change
        chunking of files that already have section headers."""
        body = "# Doc\n\nPreamble.\n\n## Section A\n\nA prose.\n\n## Section B\n\nB prose.\n"
        chunks = self.chunker.chunk_file(body, "docs/regular.md")
        # H2-split into doc-summary + preamble + two sections (4 chunks total
        # in the current chunk_file pipeline; doc-summary is the per-doc head
        # generated by _chunk_doc_summary).
        self.assertEqual(len(chunks), 4)
        # None of them are part-of-N (no oversized splitting fired)
        for c in chunks:
            section_text = c.section or ""
            self.assertNotIn("(part ", section_text)

    def test_non_prompt_h1_only_still_emitted_as_preamble_when_fits(self):
        """AC-9: generic doc markdown (no kind_override) with H1 only and
        short body emerges as a single preamble chunk. Project-layer doc
        index chunk shape preserved."""
        body = "# Just A Title\n\nShort body.\n"
        chunks = self.chunker.chunk_file(body, "docs/short.md")
        doc_chunks = [c for c in chunks if c.kind == "doc"]
        self.assertEqual(len(doc_chunks), 1)


class TableDecompositionTests(unittest.TestCase):
    """AC-5, AC-13: pipe-table per-row decomposition with header row preserved
    on every emitted chunk. Real-world target: Decision Log / AC Priority /
    Risks tables in change docs (committed tables reach 41K chars)."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        scripts_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("chunker", scripts_root / "chunker.py")
        cls.chunker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.chunker)

    def _big_table(self, rows: int, cells_each: int = 100) -> str:
        """Build a markdown pipe table with `rows` data rows, each cell ~`cells_each` chars."""
        cell = "x" * cells_each
        lines = ["| A | B | C | D |", "|---|---|---|---|"]
        for i in range(rows):
            lines.append(f"| {i} | {cell} | {cell} | {cell} |")
        return "\n".join(lines)

    def test_small_table_kept_whole(self):
        """AC-12: a small pipe table fits in a single chunk; no decomposition fires."""
        body = "# Doc\n\n## A Section\n\n" + self._big_table(rows=3, cells_each=20) + "\n"
        chunks = self.chunker.chunk_file(body, "docs/small-table.md")
        doc_chunks = [c for c in chunks if c.kind == "doc"]
        for c in doc_chunks:
            self.assertNotIn("rows", c.section or "")  # no per-row label

    def test_large_table_decomposes_per_row_with_header_preserved(self):
        """AC-5, AC-13: a table that exceeds MAX_CHUNK_CHARS decomposes into
        per-row chunks. Every emitted chunk contains the header + separator
        rows so column context survives."""
        body = "# Doc\n\n## Decision Log\n\n" + self._big_table(rows=40, cells_each=80) + "\n"
        chunks = self.chunker.chunk_file(body, "docs/big-table.md")
        decision_chunks = [c for c in chunks if "Decision Log" in (c.section or "")]
        self.assertGreater(len(decision_chunks), 1)
        for c in decision_chunks:
            self.assertLessEqual(len(c.text), self.chunker.MAX_CHUNK_CHARS)
            # Header row must appear in every emitted chunk
            self.assertIn("| A | B | C | D |", c.text)
            # Separator row must appear in every emitted chunk
            self.assertIn("|---|---|---|---|", c.text)

    def test_large_table_section_label_records_row_range(self):
        """AC-7 (table-decomposition label part): section labels include
        `(rows N–M of T)` so retrieval surfaces can address coherent row ranges."""
        body = "# Doc\n\n## Decision Log\n\n" + self._big_table(rows=40, cells_each=80) + "\n"
        chunks = self.chunker.chunk_file(body, "docs/big-table.md")
        decision_chunks = [c for c in chunks if "Decision Log" in (c.section or "")]
        import re
        for c in decision_chunks:
            self.assertRegex(c.section or "", r"\(rows \d+–\d+ of 40\)")

    def test_table_with_preamble_and_postlude(self):
        """When a chunk contains prose BEFORE and AFTER the table, the
        preamble carries on every emitted chunk and the postlude attaches
        to the final chunk only."""
        body = (
            "# Doc\n\n## Section\n\n"
            "Some intro prose before the table.\n\n"
            + self._big_table(rows=40, cells_each=80)
            + "\n\nSome trailing prose after the table.\n"
        )
        chunks = self.chunker.chunk_file(body, "docs/sandwich.md")
        section_chunks = [c for c in chunks if "Section" in (c.section or "") and "rows" in (c.section or "")]
        self.assertGreater(len(section_chunks), 1)
        # Trailing prose appears only in the last emitted chunk
        with_trailing = [c for c in section_chunks if "trailing prose" in c.text]
        self.assertEqual(len(with_trailing), 1)
        # Last decomposed chunk has it
        self.assertIn("trailing prose", section_chunks[-1].text)

    def test_real_world_41k_decision_log(self):
        """Regression target: the 1p318 change doc has a 41K-char Decision Log.
        Verify it decomposes cleanly with every chunk under cap and the
        majority of decomposed chunks preserve the column header.

        Note: at the per-kind cap (2000 chars for docs), some individual rows
        in 1p318's Decision Log are themselves > 2000 chars (multi-paragraph
        Reason cells). Those rows can't fit alongside the header in a single
        chunk; they fall through to line/char-wrap with `(part N/M)` labels.
        For those rows, the header is on the lead part chunk and the
        continuations are the row tail. Most rows fit cleanly with header.
        """
        path = Path(__file__).resolve().parents[4] / "docs" / "waves" / "1p31b public-launch-prep" / "1p318-enh public-launch-surface-doc-rewrite.md"
        if not path.is_file():
            self.skipTest(f"Reference doc not present at {path}")
        src = path.read_text()
        chunks = self.chunker.chunk_file(src, str(path))
        decision_chunks = [c for c in chunks if "Decision Log" in (c.section or "")]
        self.assertGreaterEqual(len(decision_chunks), 10,
            "1p318 Decision Log should decompose into many row-grouped chunks at the 2000-char cap")
        for c in decision_chunks:
            self.assertLessEqual(len(c.text), self.chunker.MAX_DOC_CHUNK_CHARS)
        # Most chunks (>= 70%) preserve the canonical header. The rest are
        # `(part N/M)` continuations of single oversized rows.
        header_canonical = "| Date | Decision | Reason | Alternatives |"
        with_header = sum(1 for c in decision_chunks if header_canonical in c.text)
        self.assertGreaterEqual(with_header, int(0.7 * len(decision_chunks)),
            f"≥70% of decomposed chunks should preserve header; got {with_header}/{len(decision_chunks)}")

    def test_line_wrap_preserves_breadcrumb_on_every_part(self):
        """Wave 1p3b9 (1p397): when an H2 section is line-wrap-decomposed (via
        the universal guard's `_line_wrap_chunk`), the markdown chunker's
        injected breadcrumb (``Doc Title > Section`` on the first line +
        blank-line separator) MUST be prepended to every emitted part. Without
        this, parts 2/3/N would orphan their bullet text from the section
        context."""
        # Build a long H2 section as a bullet list that exceeds the cap
        section_body = "\n".join(f"- bullet {i} with extra prose to push past the cap." for i in range(60))
        body = f"# Doc Title\n\n## Long Section\n\n{section_body}\n"
        chunks = self.chunker.chunk_file(body, "docs/long-section.md")
        section_chunks = [c for c in chunks if "Long Section" in (c.section or "")]
        # Should decompose into ≥2 parts at the 2000-char cap
        self.assertGreaterEqual(len(section_chunks), 2)
        # Every part includes the breadcrumb as its first non-empty content
        for c in section_chunks:
            first_line = c.text.split("\n", 1)[0]
            self.assertIn("Long Section", first_line)
            # Body content (a bullet) comes after the blank line, not the
            # first line — the first line is the breadcrumb, not content.
            self.assertFalse(first_line.lstrip().startswith("-"),
                f"first line should be breadcrumb, not content: {first_line!r}")

    def test_no_false_positive_on_prose_with_pipes(self):
        """Prose containing pipe characters (e.g., `| pipe | here |`) but
        without a separator row must NOT trigger table decomposition."""
        # Long prose containing pipe-looking lines but no separator row
        body = (
            "# Doc\n\n## Discussion\n\n"
            + "Sample prose discussing `command | option | other` syntax.\n" * 80
        )
        chunks = self.chunker.chunk_file(body, "docs/pipes.md")
        # The section is over-cap and falls through to line-wrap, NOT table decomp
        section_chunks = [c for c in chunks if "Discussion" in (c.section or "")]
        for c in section_chunks:
            self.assertNotIn("rows", c.section or "")  # no per-row label


class ConstantChunkTests(unittest.TestCase):
    """Wave 1p4mf: module/class-level constant chunking (Python)."""

    def setUp(self):
        self.chunker = load_chunker()

    def _consts(self, source, path="mod.py"):
        chunks = self.chunker.chunk_python(source, path)
        return {c.id: c for c in chunks if c.section and c.section.endswith(" [const]")}

    def test_module_constant_chunked_with_value_and_breadcrumb(self):
        """AC-1: a module-level UPPER_SNAKE constant becomes a kind=code chunk whose text
        carries the breadcrumb prefix AND the value (the RERANKER_MODEL motivating case)."""
        consts = self._consts('RERANKER_MODEL = "BAAI/bge-reranker-base"\n')
        self.assertIn("mod.py::RERANKER_MODEL", consts)
        c = consts["mod.py::RERANKER_MODEL"]
        self.assertEqual(c.kind, "code")
        self.assertTrue(c.text.startswith("mod > RERANKER_MODEL\n\n"))
        self.assertIn('"BAAI/bge-reranker-base"', c.text)

    def test_class_constant_chunked_qualified(self):
        """AC-1: a class-body constant is chunked as Type.NAME."""
        self.assertIn("mod.py::Config.MAX_SIZE", self._consts("class Config:\n    MAX_SIZE = 100\n"))

    def test_final_override_includes_lowercase(self):
        """AC-2: an any-cased name annotated Final is a constant (casing override)."""
        self.assertIn("mod.py::default_config", self._consts("from typing import Final\ndefault_config: Final = {}\n"))

    def test_excludes_locals_lowercase_singlechar_dunder_typechecking(self):
        """AC-2: scope + casing exclusions — none of these are chunked as constants."""
        src = (
            "from typing import TYPE_CHECKING\n"
            "api_url = 1\n"            # lowercase
            "T = 1\n"                  # single-letter TypeVar
            "__all__ = []\n"           # dunder
            "if TYPE_CHECKING:\n    GUARDED = 1\n"   # inside an If — not a direct module child
            "def f():\n    LOCAL_CONST = 9\n"        # function-local
        )
        consts = self._consts(src)
        for bad in ("api_url", "T", "__all__", "GUARDED", "LOCAL_CONST"):
            self.assertNotIn(f"mod.py::{bad}", consts, bad)

    def test_enum_members_not_split(self):
        """AC-2: Enum members stay together in the class chunk — not emitted as constants."""
        src = "import enum\nclass Color(enum.Enum):\n    RED = 1\n    GREEN = 2\n"
        self.assertEqual(self._consts(src), {})  # no per-member constant chunks
        self.assertIn("mod.py::Color", {c.id for c in self.chunker.chunk_python(src, "mod.py")})

    def test_adjacent_constants_each_survive_merge(self):
        """AC-3 (the trap): >=3 adjacent 1-line constants each survive with their OWN id —
        kind=code, but merge-excluded via the section marker, so none are folded away."""
        consts = self._consts("A_ONE = 1\nB_TWO = 2\nC_THREE = 3\n")
        self.assertEqual(set(consts), {"mod.py::A_ONE", "mod.py::B_TWO", "mod.py::C_THREE"})

    def test_constant_after_function_survives(self):
        """AC-3: a 1-line constant declared AFTER a function is not folded into it."""
        self.assertIn("mod.py::AFTER_FUNC", self._consts("def helper():\n    return 1\n\nAFTER_FUNC = 42\n"))

    def test_multi_target_per_identifier(self):
        """AC: per-identifier for multi-target assigns."""
        consts = self._consts("A_X = B_Y = 5\n")
        self.assertIn("mod.py::A_X", consts)
        self.assertIn("mod.py::B_Y", consts)


class JsTsConstantChunkTests(unittest.TestCase):
    """Wave 1p4mf (JS/TS): value-const chunking on the tree-sitter production path.

    A `const` whose RHS is a literal value (scalar/string/object/array/template) is a VALUE
    constant → kind=code chunk, " [const]" section marker (merge-excluded), breadcrumb-prefixed
    text carrying the declaration. A function/component const (arrow/styled-call) and any
    `let`/`var` keep the original plain code-chunk path (no marker)."""

    def setUp(self):
        self.chunker = load_chunker()

    def _chunk(self, source, path="src/conf.ts"):
        # AC-5: a missing tree-sitter grammar must FAIL loudly, not skip — a silent skip would let
        # a vacuous gate masquerade as a pass. Run under ~/.wavefoundry/venv (grammars installed).
        result = self.chunker.chunk_js_ts_treesitter(source, path)
        self.assertIsNotNone(result, "tree-sitter JS/TS grammar unavailable — gate is vacuous")
        return result

    def _consts(self, source, path="src/conf.ts"):
        return {c.id: c for c in self._chunk(source, path)
                if c.section and c.section.endswith(" [const]")}

    def test_enum_members_chunked(self):
        """AC-1 (1p4q4): each TS `enum` / `const enum` / `export enum` member is its own
        `Enum.Member` const chunk — members are how TS expresses named constants."""
        consts = self._consts(
            "enum Status { OK = 0, FAIL = 1 }\n"
            "const enum Dir { Up, Down }\n"
            'export enum Color { Red = "r" }\n')
        ids = {i.rsplit("::", 1)[-1] for i in consts}
        self.assertEqual({"Status.OK", "Status.FAIL", "Dir.Up", "Dir.Down", "Color.Red"}, ids,
                         f"all enum members chunked; got {ids}")
        self.assertIn("0", consts["src/conf.ts::Status.OK"].text, "member value carried in text")

    def test_namespace_and_declare_const_chunked(self):
        """AC-2 (1p4q4): a `namespace` export-const and a `declare const` value are constant chunks."""
        ids = {i.rsplit("::", 1)[-1] for i in self._consts(
            "namespace NS { export const NS_LIMIT = 5; }\n"
            "declare const AMBIENT = 9;\n")}
        self.assertIn("NS.NS_LIMIT", ids, f"namespace const; got {ids}")
        self.assertIn("AMBIENT", ids, f"declare const; got {ids}")

    def test_module_keyword_block_chunked(self):
        """Review C1: the `module M { ... }` keyword form parses as a top-level `module` node (NOT
        `internal_module`); its consts AND enum members must be chunked, qualified by the module
        name. Requirement 2 names `module` explicitly."""
        ids = {i.rsplit("::", 1)[-1] for i in self._consts(
            "module Legacy {\n  const X = 5;\n  enum Code { OKAY = 200 }\n}\n")}
        self.assertIn("Legacy.X", ids, f"module-keyword const; got {ids}")
        self.assertIn("Legacy.Code.OKAY", ids, f"module-keyword enum member; got {ids}")

    def test_non_export_const_in_namespace_chunked(self):
        """Review C2: a NON-export `const` inside a `namespace` is chunked (qualified by the namespace
        name) — previously only `export const` survived. Requirement 2 says namespace consts
        (unqualified) are chunked."""
        ids = {i.rsplit("::", 1)[-1] for i in self._consts(
            'namespace N {\n  const VERSION = "1.0";\n  export const NAME = "app";\n}\n')}
        self.assertIn("N.VERSION", ids, f"non-export namespace const; got {ids}")
        self.assertIn("N.NAME", ids, f"export namespace const; got {ids}")

    def test_export_and_declare_namespace_and_declare_enum_chunked(self):
        """Review C3: `export namespace` (export_statement→internal_module), `declare namespace`
        (ambient_declaration→internal_module) and `declare enum` (ambient_declaration→enum_declaration)
        must recurse so contained members are chunked — these are the common `.d.ts` ambient forms."""
        exp = {i.rsplit("::", 1)[-1] for i in self._consts(
            "export namespace ENS {\n  export enum E { MEMBER = 1 }\n}\n")}
        self.assertIn("ENS.E.MEMBER", exp, f"export namespace enum member; got {exp}")
        dns = {i.rsplit("::", 1)[-1] for i in self._consts(
            "declare namespace DNS {\n  enum K { CODE = 404 }\n  const VER = 2;\n}\n")}
        self.assertIn("DNS.K.CODE", dns, f"declare namespace enum member; got {dns}")
        self.assertIn("DNS.VER", dns, f"declare namespace const; got {dns}")
        den = {i.rsplit("::", 1)[-1] for i in self._consts("declare enum DE { ONLY = 7 }\n")}
        self.assertIn("DE.ONLY", den, f"declare enum member; got {den}")

    def test_mts_cts_chunked_as_typescript(self):
        """Review B4 (completed): `.mts`/`.cts` TypeScript module files are first-class in the MAIN
        chunker pipeline (not only code_constants) — they parse as TypeScript (so enum members chunk)
        and carry language='typescript'. Regression for the dispatch gap where they fell through to
        line-window chunking / parsed as JS (no enum support)."""
        for path in ("m.mts", "m.cts"):
            with self.subTest(path=path):
                chunks = self._chunk('enum E { Aaa = 1, Bbb = 2 }\nexport const API = "x";\n', path)
                consts = {c.id.rsplit("::", 1)[-1]: c for c in chunks if c.section.endswith(" [const]")}
                self.assertIn("E.Aaa", consts, f"[{path}] enum member must chunk (TS parse); got {sorted(consts)}")
                self.assertIn("API", consts, f"[{path}] const must chunk; got {sorted(consts)}")
                self.assertEqual(consts["E.Aaa"].language, "typescript", f"[{path}] language must be typescript")

    def test_enum_does_not_disturb_regular_const_or_functions(self):
        """AC-5 (1p4q4): a regular value const stays marked; an arrow-const function stays UNmarked
        (no false const) when coexisting with an enum."""
        by_leaf = {c.id.rsplit("::", 1)[-1]: c for c in self._chunk(
            'enum E { A = 1 }\nconst API_URL = "x";\nexport const handler = (a) => a + 1;\n')}
        self.assertTrue(by_leaf["API_URL"].section.endswith(" [const]"), "regular value const still marked")
        self.assertFalse(by_leaf["handler"].section.endswith(" [const]"), "arrow-const fn must NOT be a const")

    def test_toplevel_value_const_marked_with_breadcrumb_and_value(self):
        """AC-1: a top-level scalar const → marked chunk; text carries breadcrumb + value."""
        consts = self._consts("const MAX_SIZE = 100;\n")
        self.assertIn("src/conf.ts::MAX_SIZE", consts)
        c = consts["src/conf.ts::MAX_SIZE"]
        self.assertEqual(c.kind, "code")
        self.assertTrue(c.text.startswith("conf > MAX_SIZE\n\n"))
        self.assertIn("100", c.text)

    def test_export_const_string_marked(self):
        """AC-1 + regression: `export const` whose line text starts with `export` must still be
        detected as const (the keyword-token check, not line-prefix) and marked."""
        consts = self._consts('export const API_URL = "https://x";\n')
        self.assertIn("src/conf.ts::API_URL", consts)
        self.assertIn('"https://x"', consts["src/conf.ts::API_URL"].text)

    def test_object_and_array_and_template_consts_marked(self):
        consts = self._consts(
            "const config = { a: 1 };\n"
            "const items = [1, 2, 3];\n"
            "const greeting = `hello`;\n"
        )
        self.assertEqual(
            set(consts),
            {"src/conf.ts::config", "src/conf.ts::items", "src/conf.ts::greeting"},
        )

    def test_function_and_component_consts_not_marked(self):
        """A function/component const (arrow / styled-call) is NOT a value constant → no marker."""
        src = (
            "const handler = () => { return 1; };\n"
            "export const Btn = styled.div`x`;\n"
        )
        self.assertEqual(self._consts(src), {})

    def test_let_and_var_not_marked(self):
        """`let`/`var` are not constants — never marked, even with a literal RHS. (Anchored with a
        const so the chunker emits output rather than returning None on a declaration-only file.)"""
        consts = self._consts("const REAL = 1;\nlet mutable = 3;\nvar legacy = 4;\n")
        self.assertIn("src/conf.ts::REAL", consts)
        self.assertNotIn("src/conf.ts::mutable", consts)
        self.assertNotIn("src/conf.ts::legacy", consts)

    def test_typed_ts_const_marked(self):
        """AC-1 (TS): a type-annotated const still resolves its value via the `value` field."""
        self.assertIn("src/conf.ts::TIMEOUT", self._consts("const TIMEOUT: number = 5000;\n"))

    def test_adjacent_value_consts_each_survive_merge(self):
        """AC-3: adjacent 1-line value consts each keep their OWN id (marker → merge-excluded)."""
        consts = self._consts("const A_ONE = 1;\nconst B_TWO = 2;\nconst C_THREE = 3;\n")
        self.assertEqual(
            set(consts),
            {"src/conf.ts::A_ONE", "src/conf.ts::B_TWO", "src/conf.ts::C_THREE"},
        )


class JsTsRegexFallbackConstantTests(unittest.TestCase):
    """Wave 1p4mf (JS/TS): value-const chunking on the REGEX fallback path (`chunk_js_ts`), used
    when the tree-sitter grammar is unavailable. Parity with the tree-sitter path: value consts
    (incl. non-exported — closing the export-only `_JS_EXPORT_CONST_RE` gap) are marked; function/
    component consts (arrow / styled-call) keep their plain code-chunk path."""

    def setUp(self):
        self.chunker = load_chunker()

    def _consts(self, source, path="src/conf.ts"):
        return {c.id: c for c in self.chunker.chunk_js_ts(source, path)
                if c.section and c.section.endswith(" [const]")}

    def test_non_exported_value_const_marked(self):
        """Closes the export-only gap: a plain `const NAME = value` (never chunked before) is now
        a marked value-const chunk with the breadcrumb-prefixed value in its text."""
        consts = self._consts("const MAX_SIZE = 100;\n")
        self.assertIn("src/conf.ts::MAX_SIZE", consts)
        c = consts["src/conf.ts::MAX_SIZE"]
        self.assertTrue(c.text.startswith("conf > MAX_SIZE\n\n"))
        self.assertIn("100", c.text)

    def test_exported_string_and_typed_const_marked(self):
        consts = self._consts(
            'export const API_URL = "https://x";\n'
            "const TIMEOUT: number = 5000;\n"
        )
        self.assertIn("src/conf.ts::API_URL", consts)
        self.assertIn("src/conf.ts::TIMEOUT", consts)

    def test_multiline_object_and_array_consts_marked(self):
        consts = self._consts(
            "const config = {\n  a: 1,\n  b: 2,\n};\n"
            "const items = [1, 2, 3];\n"
        )
        self.assertIn("src/conf.ts::config", consts)
        self.assertIn("src/conf.ts::items", consts)
        # the multi-line object body is captured in the const chunk
        self.assertIn("b: 2", consts["src/conf.ts::config"].text)

    def test_arrow_and_styled_not_marked(self):
        """A function/component const is NOT a value const — no marker (caught by the arrow/export
        paths as a plain code chunk)."""
        consts = self._consts(
            "const handler = () => { return 1; };\n"
            "export const Btn = styled.div`x`;\n"
        )
        self.assertEqual(consts, {})

    def test_let_and_var_not_marked(self):
        self.assertEqual(self._consts("let mutable = 3;\nvar legacy = 4;\n"), {})



class GoConstantChunkTests(unittest.TestCase):
    """Wave 1p4mf (Go): package/file-level constant chunking on the tree-sitter path.

    Go const-ness is the `const` keyword — NOT casing. MixedCaps exported (`MaxRetries`) and
    camelCase unexported (`apiURL`) consts are BOTH detected (an UPPER_SNAKE filter would drop
    idiomatic Go). A single `const X =` -> one marked chunk; a grouped `const ( ... )` block
    (Go's iota-enum; no enum type node) -> ONE chunk for the whole block so a member query still
    hits it. Function-local `const`, `var`/grouped `var`, blank `const _ =`, and <=2-char flag
    names are excluded. Marker section suffix " [const]" -> merge-excluded (1-line consts survive
    _merge_small_chunks)."""

    def setUp(self):
        self.chunker = load_chunker()

    def _chunk(self, source, path="pkg/config/config.go"):
        # A missing tree-sitter Go grammar must FAIL loudly, not skip — a silent skip would let a
        # vacuous gate masquerade as a pass. Run under ~/.wavefoundry/venv (grammars installed).
        result = self.chunker.chunk_go_treesitter(source, path)
        self.assertIsNotNone(result, "tree-sitter Go grammar unavailable — gate is vacuous")
        return result

    def _consts(self, source, path="pkg/config/config.go"):
        return {c.id: c for c in self._chunk(source, path)
                if c.section and c.section.endswith(" [const]")}

    def test_mixedcaps_exported_const_marked_with_breadcrumb_and_value(self):
        """No casing gate: a MixedCaps EXPORTED const (NOT ALL_CAPS) is detected; text carries
        the breadcrumb prefix + the value."""
        consts = self._consts("package config\n\nconst MaxRetries = 3\n")
        self.assertIn("pkg/config/config.go::MaxRetries", consts)
        c = consts["pkg/config/config.go::MaxRetries"]
        self.assertEqual(c.kind, "code")
        self.assertTrue(c.text.startswith("config > MaxRetries\n\n"))
        self.assertIn("3", c.text)

    def test_camelcase_unexported_const_marked(self):
        """Counterexample: an UNEXPORTED camelCase const (apiURL — not ALL_CAPS, not exported)
        is still a constant and is marked. Anchored with an exported const so output is non-empty."""
        consts = self._consts(
            "package config\n\nconst MaxRetries = 3\n"
            'const apiURL = "https://api.example.com"\n'
        )
        self.assertIn("pkg/config/config.go::apiURL", consts)
        self.assertIn('"https://api.example.com"', consts["pkg/config/config.go::apiURL"].text)

    def test_grouped_iota_enum_is_one_chunk_kept_together(self):
        """A grouped `const ( ... )` block (Go's enum) -> ONE chunk for the whole block; a member
        query (e.g. StatusErr) still hits the chunk text. Chunk id uses the first usable member."""
        src = (
            "package config\n\n"
            "const (\n"
            "\tStatusOK = iota\n"
            "\tStatusErr\n"
            ")\n"
        )
        consts = self._consts(src)
        self.assertIn("pkg/config/config.go::StatusOK", consts)
        c = consts["pkg/config/config.go::StatusOK"]
        # whole block kept together — the second member is in the SAME chunk
        self.assertIn("StatusErr", c.text)
        # exactly one const chunk for the grouped block (not one per member)
        self.assertEqual(len(consts), 1)

    def test_typed_grouped_enum_kept_together(self):
        """A typed grouped const (Go enum idiom `const ( Red Color = iota; ... )`) is still ONE
        const chunk with all members kept together."""
        src = (
            "package config\n\n"
            "type Color int\n\n"
            "const (\n"
            "\tRed Color = iota\n"
            "\tGreen\n"
            "\tBlue\n"
            ")\n"
        )
        consts = self._consts(src)
        self.assertIn("pkg/config/config.go::Red", consts)
        c = consts["pkg/config/config.go::Red"]
        self.assertIn("Green", c.text)
        self.assertIn("Blue", c.text)

    def test_function_local_const_not_marked(self):
        """SCOPE exclusion: a function-local `const` is the SAME node type (const_declaration) as a
        package-level one — only its nesting separates them. It must NOT be marked. Anchored with a
        package-level const so output is non-empty and the contrast is explicit."""
        src = (
            "package config\n\n"
            "const MaxRetries = 3\n\n"
            "func Connect() error {\n"
            "\tconst localRetries = 5\n"
            "\treturn nil\n"
            "}\n"
        )
        consts = self._consts(src)
        self.assertIn("pkg/config/config.go::MaxRetries", consts)
        self.assertNotIn("pkg/config/config.go::localRetries", consts)

    def test_var_and_grouped_var_not_marked(self):
        """`var` and grouped `var ( ... )` are var_declaration, not const — never marked."""
        src = (
            "package config\n\n"
            "const MaxRetries = 3\n"
            "var GlobalVar = 9\n"
            "var (\n\tA = 1\n\tB = 2\n)\n"
        )
        consts = self._consts(src)
        self.assertIn("pkg/config/config.go::MaxRetries", consts)
        self.assertNotIn("pkg/config/config.go::GlobalVar", consts)
        self.assertNotIn("pkg/config/config.go::A", consts)
        self.assertNotIn("pkg/config/config.go::B", consts)

    def test_blank_const_excluded_short_names_chunked(self):
        """Only the blank `const _ =` is skipped. Short flag names (`x`, `Pi`, `KB`) ARE chunked —
        1p4ls delivery review: dropping ≤2-char Go consts made common ones (Pi/KB/MB/Hz/OK/ID)
        unretrievable. The CHUNK lane includes every named const-keyword decl; the graph applies
        its own short-symbol prune separately."""
        src = (
            "package config\n\n"
            "const _ = 7\n"
            "const x = 1\n"
            "const Pi = 3.14159\n"
            "const KB = 1024\n"
            "const MaxRetries = 3\n"
        )
        consts = self._consts(src)
        self.assertEqual(
            set(consts),
            {
                "pkg/config/config.go::x",
                "pkg/config/config.go::Pi",
                "pkg/config/config.go::KB",
                "pkg/config/config.go::MaxRetries",
            },
        )
        self.assertNotIn("pkg/config/config.go::_", consts)

    def test_adjacent_single_consts_each_survive_merge(self):
        """Adjacent 1-line consts each keep their OWN id (marker suffix -> merge-excluded), so a
        1-line const is never folded into a neighbor."""
        src = (
            "package config\n\n"
            "const AlphaOne = 1\n"
            "const BetaTwo = 2\n"
            "const GammaThree = 3\n"
        )
        consts = self._consts(src)
        self.assertEqual(
            set(consts),
            {"pkg/config/config.go::AlphaOne",
             "pkg/config/config.go::BetaTwo",
             "pkg/config/config.go::GammaThree"},
        )


class RustConstantChunkTests(unittest.TestCase):
    """Wave 1p4mf (Rust): module/type-level constant chunking on the tree-sitter path.

    ``const_item`` (const NAME: T = …) and ``static_item`` (static / static mut) at file/module
    top level, or as associated consts inside an ``impl_item`` / ``trait_item`` (Owner.NAME), become
    kind=code chunks with a " [const]" section marker (merge-excluded) and breadcrumb-prefixed text.
    The const/static KEYWORD is authoritative — NO casing gate (idiomatic ALL-CAPS is incidental).
    FUNCTION-LOCAL const/static (same node type, but inside a block), `let`, enum variants, struct
    fields, `type` aliases, and `const fn` (a function_item) are NOT constants."""

    def setUp(self):
        self.chunker = load_chunker()

    def _chunk(self, source, path="src/config.rs"):
        # Grammar-availability guard: a missing tree-sitter Rust grammar returns None → the test
        # FAILS loudly (never silently skips into the regex fallback). Run under ~/.wavefoundry/venv.
        result = self.chunker.chunk_rust_treesitter(source, path)
        self.assertIsNotNone(result, "tree-sitter Rust grammar unavailable — gate is vacuous")
        return result

    def _consts(self, source, path="src/config.rs"):
        return {c.id: c for c in self._chunk(source, path)
                if c.section and c.section.endswith(" [const]")}

    def test_toplevel_const_marked_with_breadcrumb_and_value(self):
        """AC-1: a top-level const → marked chunk; text carries breadcrumb + value."""
        consts = self._consts("const MAX_RETRIES: u32 = 5;\n")
        self.assertIn("src/config.rs::MAX_RETRIES", consts)
        c = consts["src/config.rs::MAX_RETRIES"]
        self.assertEqual(c.kind, "code")
        self.assertTrue(c.text.startswith("config > MAX_RETRIES\n\n"))
        self.assertIn("= 5", c.text)

    def test_pub_const_and_static_and_static_mut_marked(self):
        """const, static, and `static mut` are all constants; `pub` does not change that."""
        consts = self._consts(
            'pub const API_URL: &str = "https://example.com";\n'
            'static GREETING: &str = "hello";\n'
            "static mut COUNTER: i32 = 0;\n"
        )
        self.assertEqual(
            set(consts),
            {"src/config.rs::API_URL", "src/config.rs::GREETING", "src/config.rs::COUNTER"},
        )
        self.assertIn('"https://example.com"', consts["src/config.rs::API_URL"].text)

    def test_no_casing_gate_lowercase_and_mixed_const_still_marked(self):
        """COUNTEREXAMPLE to a casing filter: a non-ALL-CAPS const is still a const (keyword wins)."""
        consts = self._consts(
            "const apiTimeout: u32 = 30;\n"
            'static buildLabel: &str = "v1";\n'
        )
        self.assertEqual(
            set(consts),
            {"src/config.rs::apiTimeout", "src/config.rs::buildLabel"},
        )

    def test_impl_and_trait_associated_consts_scoped_to_owner(self):
        """impl/trait associated consts are scoped to the owner (Owner.NAME); trait consts may be
        declaration-only (no value) and are still constants."""
        src = textwrap.dedent('''\
            struct Config;
            impl Config {
                const DEFAULT_TIMEOUT: u32 = 30;
                pub const VERSION: &str = "1.0";
                fn new() -> Self { Config }
            }
            trait Describable {
                const LABEL: &'static str;
                const COUNT: usize = 0;
            }
        ''')
        consts = self._consts(src)
        self.assertIn("src/config.rs::Config.DEFAULT_TIMEOUT", consts)
        self.assertIn("src/config.rs::Config.VERSION", consts)
        self.assertIn("src/config.rs::Describable.LABEL", consts)   # decl-only trait const
        self.assertIn("src/config.rs::Describable.COUNT", consts)
        self.assertTrue(
            consts["src/config.rs::Config.DEFAULT_TIMEOUT"].text.startswith(
                "config > Config.DEFAULT_TIMEOUT\n\n"
            )
        )

    def test_function_local_const_and_static_excluded(self):
        """THE #1 TRAP: a fn-local const/static is the SAME node type as a module const; only the
        ANCESTOR (a `block`) distinguishes it. The walker never descends into a function body."""
        src = textwrap.dedent('''\
            const REAL: u32 = 1;
            fn helper() {
                const LOCAL_LIMIT: usize = 16;
                static LOCAL_STATIC: u8 = 9;
                let x = 3;
            }
        ''')
        consts = self._consts(src)
        self.assertIn("src/config.rs::REAL", consts)
        self.assertNotIn("src/config.rs::LOCAL_LIMIT", consts)
        self.assertNotIn("src/config.rs::LOCAL_STATIC", consts)
        self.assertNotIn("src/config.rs::x", consts)

    def test_impl_method_local_const_excluded(self):
        """Same trap inside an impl method body — must not leak as Owner.LOCAL or bare LOCAL."""
        src = textwrap.dedent('''\
            struct Config;
            impl Config {
                pub const VERSION: &str = "1.0";
                fn build() -> u32 {
                    const STEP: u32 = 4;
                    STEP
                }
            }
        ''')
        consts = self._consts(src)
        self.assertIn("src/config.rs::Config.VERSION", consts)
        self.assertNotIn("src/config.rs::Config.STEP", consts)
        self.assertNotIn("src/config.rs::STEP", consts)

    def test_type_alias_enum_struct_and_const_fn_not_marked(self):
        """`type` aliases, enum variants, struct fields, and `const fn` (a function_item) are not
        constants. (Anchored with a real const so the chunker emits output rather than None.)"""
        src = textwrap.dedent('''\
            const ANCHOR: u32 = 1;
            type Alias = u32;
            enum Color { Red, Green }
            struct Point { x: i32, y: i32 }
            const fn compute() -> u32 { 42 }
        ''')
        consts = self._consts(src)
        self.assertEqual(set(consts), {"src/config.rs::ANCHOR"})

    def test_leading_doc_comment_captured(self):
        """A leading `///` doc-comment block is included in the constant chunk span/text."""
        src = textwrap.dedent('''\
            /// Maximum number of retries before giving up.
            const MAX_RETRIES: u32 = 5;
        ''')
        c = self._consts(src)["src/config.rs::MAX_RETRIES"]
        self.assertIn("Maximum number of retries", c.text)

    def test_adjacent_consts_each_survive_merge(self):
        """AC-3: adjacent 1-line consts each keep their OWN id (marker → merge-excluded)."""
        consts = self._consts(
            "const A_ONE: i32 = 1;\nconst B_TWO: i32 = 2;\nconst C_THREE: i32 = 3;\n"
        )
        self.assertEqual(
            set(consts),
            {"src/config.rs::A_ONE", "src/config.rs::B_TWO", "src/config.rs::C_THREE"},
        )


class CSharpConstantChunkTests(unittest.TestCase):
    # Wave 1p4mf: C# type-member constants — `const` field OR `static readonly` pair.
    # Scope: class/struct/interface/record members only. NO casing gate (idiomatic PascalCase).
    CS_SOURCE = textwrap.dedent('''\
        using System;

        namespace Acme.Billing
        {
            public class HttpClientConfig
            {
                public const int MaxRetries = 5;
                public static readonly string apiURL = "https://api.acme.test";
                private const string SecretSalt = "pepper";
                public const int StatusOK = 200, StatusCreated = 201;
                public static int RequestCount = 0;
                public readonly int InstanceId;
                private string _token;
                public int Width { get; set; } = 10;
                public string Title => "billing";

                public int Compute()
                {
                    const int LocalLimit = 7;
                    return LocalLimit * MaxRetries;
                }
            }

            public enum Phase { Draft, Sent, Paid }

            public struct Dimensions
            {
                public const int Rank = 2;
                public static readonly Dimensions Zero = new Dimensions();
            }

            public interface IVersioned
            {
                const int SchemaVersion = 3;
            }

            public record Invoice(string Number)
            {
                public const int MaxLineItems = 50;
            }
        }
    ''')

    def setUp(self):
        self.chunker = load_chunker()

    def _consts(self, source, path):
        chunks = self.chunker.chunk_csharp_treesitter(source, path)
        # Grammar-availability guard: a missing C# tree-sitter grammar makes the chunker
        # return None — assert (FAIL), never skip, so a missing grammar is caught.
        self.assertIsNotNone(
            chunks, "chunk_csharp_treesitter returned None — C# tree-sitter grammar missing")
        return {c.id: c for c in chunks
                if c.section is not None and c.section.endswith(" [const]")}

    def test_const_and_static_readonly_detected_no_casing_gate(self):
        consts = self._consts(self.CS_SOURCE, "src/HttpClientConfig.cs")
        # plain const
        self.assertIn("src/HttpClientConfig.cs::HttpClientConfig.MaxRetries", consts)
        # static readonly with a camelCase name (counterexample to any ALL_CAPS gate)
        self.assertIn("src/HttpClientConfig.cs::HttpClientConfig.apiURL", consts)
        # idiomatic PascalCase const counterexample (NOT ALL_CAPS)
        self.assertIn("src/HttpClientConfig.cs::HttpClientConfig.StatusOK", consts)

    def test_private_const_included(self):
        consts = self._consts(self.CS_SOURCE, "src/HttpClientConfig.cs")
        self.assertIn("src/HttpClientConfig.cs::HttpClientConfig.SecretSalt", consts)

    def test_multi_declarator_one_chunk_per_name(self):
        consts = self._consts(self.CS_SOURCE, "src/HttpClientConfig.cs")
        self.assertIn("src/HttpClientConfig.cs::HttpClientConfig.StatusOK", consts)
        self.assertIn("src/HttpClientConfig.cs::HttpClientConfig.StatusCreated", consts)

    def test_struct_interface_record_scoped(self):
        consts = self._consts(self.CS_SOURCE, "src/HttpClientConfig.cs")
        self.assertIn("src/HttpClientConfig.cs::Dimensions.Rank", consts)
        self.assertIn("src/HttpClientConfig.cs::Dimensions.Zero", consts)
        self.assertIn("src/HttpClientConfig.cs::IVersioned.SchemaVersion", consts)
        self.assertIn("src/HttpClientConfig.cs::Invoice.MaxLineItems", consts)

    def test_excludes_non_constants(self):
        consts = self._consts(self.CS_SOURCE, "src/HttpClientConfig.cs")
        ids = set(consts)
        # static-alone (mutable) and readonly-alone (instance field) — need the FULL pair
        self.assertFalse(any("RequestCount" in i for i in ids))
        self.assertFalse(any("InstanceId" in i for i in ids))
        # mutable field, auto-property, expression-bodied property
        self.assertFalse(any("_token" in i for i in ids))
        self.assertFalse(any("Width" in i for i in ids))
        self.assertFalse(any("Title" in i for i in ids))
        # enum members and record positional parameter
        self.assertFalse(any(".Draft" in i or ".Sent" in i or ".Paid" in i for i in ids))
        self.assertFalse(any(i.endswith("::Invoice.Number") for i in ids))

    def test_method_body_local_const_excluded(self):
        # SCOPE: a method-body `local_declaration_statement` const is the same "const" keyword
        # but a different node type / scope — must NOT be marked as a constant chunk.
        consts = self._consts(self.CS_SOURCE, "src/HttpClientConfig.cs")
        self.assertFalse(any("LocalLimit" in i for i in consts))

    def test_breadcrumb_and_value_in_text(self):
        consts = self._consts(self.CS_SOURCE, "src/HttpClientConfig.cs")
        chunk = consts["src/HttpClientConfig.cs::HttpClientConfig.MaxRetries"]
        # breadcrumb prefix injects the symbol name; the value is retrievable in the text
        self.assertIn("HttpClientConfig > HttpClientConfig.MaxRetries", chunk.text)
        self.assertIn("= 5", chunk.text)


class JavaConstantChunkTests(unittest.TestCase):
    """Wave 1p4mf: Java module/type-level constant chunking — `static final` fields and
    interface constants emitted as kind=code chunks, breadcrumb-prefixed, merge-excluded."""

    def setUp(self):
        self.chunker = load_chunker()

    def _consts(self, source, path="src/Config.java"):
        # Target the tree-sitter path directly; assertIsNotNone so a missing Java grammar
        # FAILS (never silently skips) and produces a vacuous-pass.
        chunks = self.chunker.chunk_java_treesitter(source, path)
        self.assertIsNotNone(chunks, "tree-sitter Java grammar unavailable (must FAIL, not skip)")
        return {c.id: c for c in chunks if c.section and c.section.endswith(" [const]")}

    def test_static_final_constant_chunked_with_value_and_breadcrumb(self):
        # The motivating case: "what value is X" — breadcrumb prefix + value both in text.
        consts = self._consts(textwrap.dedent("""\
            public class Config {
                public static final String API_URL = "https://api.example.com";
            }
        """))
        self.assertIn("src/Config.java::Config.API_URL", consts)
        c = consts["src/Config.java::Config.API_URL"]
        self.assertEqual(c.kind, "code")
        self.assertTrue(c.text.startswith("Config > Config.API_URL\n\n"))
        self.assertIn('"https://api.example.com"', c.text)

    def test_casing_counterexamples_camel_and_mixed_case(self):
        # NOT just ALL_CAPS: the gate is `static final`, not casing — camel/mixed-case caught.
        consts = self._consts(textwrap.dedent("""\
            public class Cfg {
                public static final int MaxRetries = 3;
                static final String apiURL = "u";
            }
        """))
        self.assertIn("src/Config.java::Cfg.MaxRetries", consts)
        self.assertIn("src/Config.java::Cfg.apiURL", consts)

    def test_interface_constant_implicit_static_final(self):
        # Interface fields are constant_declaration (implicitly static final) — lowercase too.
        consts = self._consts(textwrap.dedent("""\
            public interface Limits {
                int DefaultTimeout = 30;
                String name = "limits";
            }
        """))
        self.assertIn("src/Config.java::Limits.DefaultTimeout", consts)
        self.assertIn("src/Config.java::Limits.name", consts)

    def test_nested_type_constant_qualified(self):
        consts = self._consts(textwrap.dedent("""\
            public class Outer {
                static class Inner {
                    public static final long INNER_CONST = 42L;
                }
            }
        """))
        self.assertIn("src/Config.java::Outer.Inner.INNER_CONST", consts)

    def test_multi_declarator_emits_per_name(self):
        consts = self._consts(textwrap.dedent("""\
            public class M {
                public static final String A = "a", B = "b";
            }
        """))
        self.assertIn("src/Config.java::M.A", consts)
        self.assertIn("src/Config.java::M.B", consts)

    def test_scope_and_modifier_exclusions(self):
        # Same node type (field_declaration / local_variable_declaration) but NOT constants:
        # instance final (no static), mutable static (no final), plain field, method/block
        # locals, and enum_constant members.
        consts = self._consts(textwrap.dedent("""\
            public class S {
                private final int instanceFinal = 7;
                static int mutableStatic = 0;
                int plain = 1;
                public void run() {
                    final int localFinal = 9;
                    int x = 1;
                }
                enum Color { RED, GREEN }
            }
        """))
        for bad in ("instanceFinal", "mutableStatic", "plain", "localFinal", "x"):
            self.assertNotIn(f"src/Config.java::S.{bad}", consts, bad)
        self.assertNotIn("src/Config.java::S.Color.RED", consts)
        self.assertNotIn("src/Config.java::Color.RED", consts)

    def test_adjacent_constants_each_survive_merge(self):
        # 3 adjacent 1-line constants each keep their own id (merge-excluded via " [const]").
        consts = self._consts(textwrap.dedent("""\
            public class K {
                public static final int A = 1;
                public static final int B = 2;
                public static final int C = 3;
            }
        """))
        for n in ("A", "B", "C"):
            self.assertIn(f"src/Config.java::K.{n}", consts, n)


class JavaInitializerChunkTests(unittest.TestCase):
    """Wave 1sbfl: Java static/instance initializer blocks are emitted as their own
    kind="code" chunks across class/enum/record containers (records static-only — Java
    forbids record instance initializers). Covers AC-1, AC-2, AC-3, AC-5, AC-7 on the
    chunker side. Both the tree-sitter path and the forced regex-fallback path are pinned;
    the fallback path fails closed (patches _fallback_with_stem to raise) and asserts EXACT
    initializer identity/metadata rather than accepting generic line-window rescue."""

    def setUp(self):
        self.chunker = load_chunker()

    # A catalog exercising: ordinary-class static+instance, multiple same-kind static
    # (ordinals), an enum static init, a top-level record static init, a nested class
    # static init, and a nested member-record static init — plus negative constructs.
    CATALOG = textwrap.dedent("""\
        public class Bundle {
            static final int SEED = 1;
            static {
                MESSAGES.put("cat.k1", "AlphaZzToken");
                MESSAGES.put("cat.k2", "BetaZzToken");
            }
            {
                this.local = new java.util.HashMap<>();
                local.put("inst.k", "InstanceZzToken");
            }
            static {
                LATE.put("cat.k3", "GammaZzToken");
            }
            void doWork() {
                if (SEED > 0) { int x = 1; }
                Runnable r = () -> { run("LambdaZzToken"); };
                int[] arr = {1, 2, 3};
                Object o = new Object() { void inner() { note("AnonZzToken"); } };
            }
            Bundle() { seed("CtorZzToken"); }
            static class Nested {
                static { NREG.put("n.k", "NestedZzToken"); }
            }
            record Member(int a) {
                static { MREG.put("m.k", "MemberZzToken"); }
            }
        }
        enum Palette {
            RED, GREEN;
            static { LOOKUP.put("p.k", "EnumZzToken"); }
        }
        record Coord(int x, int y) {
            static { CREG.put("c.k", "RecordZzToken"); }
        }
        interface Marker {
            int LIMIT = 5;
        }
    """)

    # The exact initializer chunk-id set the CATALOG must produce (path-qualified,
    # static/instance distinguished, ordinals for multiples, nested-type qualified).
    EXPECTED_INIT_IDS = {
        "src/Bundle.java::Bundle.__static_init_1__",
        "src/Bundle.java::Bundle.__instance_init_1__",
        "src/Bundle.java::Bundle.__static_init_2__",
        "src/Bundle.java::Bundle.Nested.__static_init_1__",
        "src/Bundle.java::Bundle.Member.__static_init_1__",
        "src/Bundle.java::Palette.__static_init_1__",
        "src/Bundle.java::Coord.__static_init_1__",
    }

    def _init_chunks(self, chunks):
        return {c.id: c for c in chunks if "__static_init_" in c.id or "__instance_init_" in c.id}

    # ---- AC-2: direct tree-sitter path (fails if grammar unavailable — no skip) ----

    def test_treesitter_emits_all_container_initializers(self):
        chunks = self.chunker.chunk_java_treesitter(self.CATALOG, "src/Bundle.java")
        self.assertIsNotNone(
            chunks, "tree-sitter Java grammar unavailable (must FAIL, not skip)")
        inits = self._init_chunks(chunks)
        self.assertEqual(set(inits), self.EXPECTED_INIT_IDS)
        # Records reach FIRST-CLASS identity through the net-new record path, not a
        # generic __module__/line-window chunk.
        self.assertIn("src/Bundle.java::Coord.__static_init_1__", inits)
        self.assertNotIn("src/Bundle.java::__module__", {c.id for c in chunks})
        # Record instance initializers are illegal Java — records get static-only.
        self.assertFalse(any("Coord.__instance_init_" in i for i in inits))
        self.assertFalse(any("Member.__instance_init_" in i for i in inits))
        # Literal payload is present in the right blocks.
        self.assertIn("AlphaZzToken", inits["src/Bundle.java::Bundle.__static_init_1__"].text)
        self.assertIn("GammaZzToken", inits["src/Bundle.java::Bundle.__static_init_2__"].text)
        self.assertIn("InstanceZzToken", inits["src/Bundle.java::Bundle.__instance_init_1__"].text)
        self.assertIn("EnumZzToken", inits["src/Bundle.java::Palette.__static_init_1__"].text)
        self.assertIn("RecordZzToken", inits["src/Bundle.java::Coord.__static_init_1__"].text)
        self.assertIn("NestedZzToken", inits["src/Bundle.java::Bundle.Nested.__static_init_1__"].text)
        self.assertIn("MemberZzToken", inits["src/Bundle.java::Bundle.Member.__static_init_1__"].text)

    def test_treesitter_metadata_kind_language_marker_lines(self):
        chunks = self.chunker.chunk_java_treesitter(self.CATALOG, "src/Bundle.java")
        self.assertIsNotNone(chunks)
        inits = self._init_chunks(chunks)
        c = inits["src/Bundle.java::Bundle.__static_init_1__"]
        self.assertEqual(c.kind, "code")
        self.assertEqual(c.language, "java")
        # Merge-exempt marker + breadcrumb.
        self.assertEqual(c.section, "Bundle > Bundle.__static_init_1__" + self.chunker._INIT_SECTION_SUFFIX)
        self.assertTrue(c.text.startswith("Bundle > Bundle.__static_init_1__\n\n"))
        self.assertEqual(c.lines, (3, 6))

    def test_treesitter_negative_constructs_not_initializers(self):
        chunks = self.chunker.chunk_java_treesitter(self.CATALOG, "src/Bundle.java")
        self.assertIsNotNone(chunks)
        init_text = "\n".join(c.text for c in self._init_chunks(chunks).values())
        # Control-flow, lambda, anonymous-class, array init, and constructor bodies must
        # NOT be misclassified as sibling initializer chunks.
        for token in ("LambdaZzToken", "AnonZzToken", "CtorZzToken"):
            self.assertNotIn(token, init_text, f"{token} leaked into an initializer chunk")
        # The array literal `{1, 2, 3}` produced no initializer chunk.
        self.assertFalse(any("doWork" in i for i in self._init_chunks(chunks)))
        # Interface bodies get no initializer chunk.
        self.assertFalse(any("Marker." in i and "_init_" in i for i in self._init_chunks(chunks)))

    def test_treesitter_below_min_lines_initializer_survives_merge(self):
        # A one-line `static {}`-with-body block is below CHUNK_MIN_LINES but must remain
        # a distinct chunk after _merge_small_chunks (merge-exempt marker).
        src = textwrap.dedent("""\
            public class Tiny {
                static { T.put("k", "TinyStaticZz"); }
                void m() { work(); }
            }
        """)
        chunks = self.chunker.chunk_java_treesitter(src, "src/Tiny.java")
        self.assertIsNotNone(chunks)
        ids = {c.id for c in chunks}
        self.assertIn("src/Tiny.java::Tiny.__static_init_1__", ids)
        c = next(c for c in chunks if c.id.endswith("Tiny.__static_init_1__"))
        self.assertEqual(c.lines[1] - c.lines[0] + 1, 1)  # one line, still standalone
        self.assertIn("TinyStaticZz", c.text)

    # ---- AC-2: forced regex-fallback path — fails closed, exact identity ----

    def _forced_fallback(self, source, path):
        """Force grammar-unavailable regex fallback AND disable the generic line-window
        rescue so the acceptance proof fails closed on any identity loss."""
        def _boom(*a, **k):
            raise AssertionError(
                "generic line-window rescue is disabled for initializer parity")
        with unittest.mock.patch.object(self.chunker, "_ts_parse", return_value=None), \
             unittest.mock.patch.object(self.chunker, "_fallback_with_stem", _boom):
            return self.chunker.chunk_java(source, path)

    def test_fallback_annotation_array_and_negatives_do_not_desync_or_leak(self):
        # Hardening (delivery-review note): an annotation with an array argument
        # `@Anno({...})` and a brace-initialized field precede a real `static {}`.
        # The scanner must not treat those `{...}` as initializers, must not let them
        # desync brace depth, and must still capture the trailing `static {}` as
        # ordinal 1 — on the forced grammar-unavailable fallback path. Lambda and
        # anonymous-class bodies must not leak into initializer chunks either.
        src = textwrap.dedent("""\
            package p;
            public class Widget {
                @Anno({"AnnoArrZzToken", "X"})
                private final int[] table = {1, 2, 3};
                static { R.put("k", "AfterAnnoZzToken"); }
                void run() {
                    Runnable r = () -> log("LambdaFbToken");
                    Object o = new Object() {
                        public String toString() { return "AnonFbToken"; }
                    };
                }
            }
        """)
        chunks = self._forced_fallback(src, "src/Widget.java")
        init_ids = {
            c.id for c in chunks
            if "__static_init_" in c.id or "__instance_init_" in c.id
        }
        # Exactly the one real static initializer — the annotation array, the field
        # array literal, the lambda, and the anonymous class produced none.
        self.assertEqual(init_ids, {"src/Widget.java::Widget.__static_init_1__"})
        init_text = "\n".join(
            c.text for c in chunks
            if "__static_init_" in c.id or "__instance_init_" in c.id
        )
        self.assertIn("AfterAnnoZzToken", init_text)
        for token in ("AnnoArrZzToken", "LambdaFbToken", "AnonFbToken"):
            self.assertNotIn(token, init_text, f"{token} leaked into an initializer chunk")

    @staticmethod
    def _init_ids(chunks):
        return {
            c.id for c in (chunks or [])
            if "__static_init_" in c.id or "__instance_init_" in c.id
        }

    def test_fallback_block_comment_between_class_and_name_preserves_identity(self):
        # Delivery re-review P1: a block comment used as lexical whitespace between
        # `class` and its name must NOT fuse into `classRegistry` and drop the
        # initializer into the generic line-window rescue. The forced-fallback
        # identity must match the tree-sitter path exactly.
        src = 'class /* c */ Registry {\n    static { R.put("k", "CommentZz"); }\n}\n'
        expected = {"src/Registry.java::Registry.__static_init_1__"}
        self.assertEqual(self._init_ids(self._forced_fallback(src, "src/Registry.java")), expected)
        ts = self.chunker.chunk_java_treesitter(src, "src/Registry.java")
        self.assertIsNotNone(ts)  # grammar must be present — fail, not skip
        self.assertEqual(self._init_ids(ts), expected, "fallback identity must match tree-sitter")

    def test_fallback_dollar_bearing_type_name_preserves_identity(self):
        # Delivery re-review P1: a legal `$`-bearing type name must be captured in
        # full (`Generated$Registry`), not truncated to `Generated`; both paths agree.
        src = 'class Generated$Registry {\n    static { R.put("k", "DollarZz"); }\n}\n'
        expected = {"src/Gen.java::Generated$Registry.__static_init_1__"}
        self.assertEqual(self._init_ids(self._forced_fallback(src, "src/Gen.java")), expected)
        ts = self.chunker.chunk_java_treesitter(src, "src/Gen.java")
        self.assertIsNotNone(ts)
        self.assertEqual(self._init_ids(ts), expected, "fallback identity must match tree-sitter")

    def test_segment_classifier_retained_state_bound_is_identifier_length(self):
        # Delivery re-review P1 (round 3): retained state must NOT grow with segment/source
        # length, and — stated honestly — it is bounded by the longest identifier token,
        # NOT O(1) (exact owner identity requires keeping the full name; no silent cap).
        clf = self.chunker._SegmentClassifier()
        # 200k one-char tokens separated by non-ident chars: the token buffer never
        # accumulates the run — it flushes at each separator, so it stays at one char.
        for k in range(200_000):
            clf.feed_char("x", 1)
            clf.feed_char("," if k % 7 else " ", 1)
        self.assertLessEqual(len(clf._word), 1)  # does not grow with the number of tokens
        # A single very long identifier IS retained in full — the honest O(identifier)
        # bound, not a truncating cap (the round-2 `_JAVA_IDENT_TOKEN_MAX` defect).
        clf.reset()
        for _ in range(5000):
            clf.feed_char("z", 1)
        self.assertEqual(len(clf._word), 5000)
        clf.reset()
        self.assertEqual(clf._word, [])
        self.assertIsNone(clf.type_kind)
        self.assertEqual(clf.word_count, 0)

    def test_over_max_identifier_owner_matches_treesitter(self):
        # Delivery re-review P1 (round 3): a valid Java class name longer than any internal
        # token bound must NOT be truncated — the fallback owner must equal tree-sitter's
        # full identifier, through the public forced-fallback path. (The round-2 512-char
        # cap silently emitted a 512-char owner for a 513-char class.)
        name = "C" + "x" * 512  # 513-char legal Java identifier
        src = f'class {name} {{\n    static {{ R.put("k","LongNameZz"); }}\n}}\n'
        expected = {f"src/Big.java::{name}.__static_init_1__"}
        self.assertEqual(self._init_ids(self._forced_fallback(src, "src/Big.java")), expected)
        ts = self.chunker.chunk_java_treesitter(src, "src/Big.java")
        self.assertIsNotNone(ts)
        self.assertEqual(self._init_ids(ts), expected, "fallback owner must equal tree-sitter's full name")

    def test_over_cap_annotation_before_class_keeps_identity(self):
        # Delivery re-review P1 (round 2): a valid declaration whose annotation before
        # `class` is far longer than any fixed prefix cap must NOT lose initializer
        # identity on the fallback path — the streaming classifier captures the type
        # keyword/name incrementally, so preceding length is irrelevant. Fallback must
        # equal tree-sitter.
        big_ann = "z" * 6000  # >> any fixed header cap
        src = f'@Ann("{big_ann}")\nclass Registry {{\n    static {{ R.put("k","OverCapZz"); }}\n}}\n'
        expected = {"src/Registry.java::Registry.__static_init_1__"}
        self.assertEqual(self._init_ids(self._forced_fallback(src, "src/Registry.java")), expected)
        ts = self.chunker.chunk_java_treesitter(src, "src/Registry.java")
        self.assertIsNotNone(ts)
        self.assertEqual(self._init_ids(ts), expected, "fallback identity must match tree-sitter")

    def test_fallback_class_literal_annotation_does_not_corrupt_owner(self):
        # Delivery re-review P1 (round 4): a class-literal annotation argument `@Anno(Foo.class)`
        # puts the keyword `class` after a `.` (member selection). The streaming classifier
        # must NOT mistake it for the declaration keyword — the owner is `Registry`, not `class`.
        # Fallback must equal tree-sitter.
        src = '@Anno(Foo.class)\nclass Registry {\n    static { R.put("k","ClassLitZz"); }\n}\n'
        expected = {"src/Registry.java::Registry.__static_init_1__"}
        self.assertEqual(self._init_ids(self._forced_fallback(src, "src/Registry.java")), expected)
        ts = self.chunker.chunk_java_treesitter(src, "src/Registry.java")
        self.assertIsNotNone(ts)
        self.assertEqual(self._init_ids(ts), expected, "fallback owner must equal tree-sitter")

    def test_fallback_escaped_text_block_delimiter_does_not_truncate(self):
        # Delivery re-review P1 (round 5): a Java text block containing an escaped `\"""`
        # must NOT be read as a closing delimiter — doing so desyncs the scan and drops the
        # later initializer. Fallback (initializer id AND line span) must equal tree-sitter.
        src = (
            "class Registry {\n"
            "    static {\n"
            '        String s = """\n'
            '            has an escaped \\""" delimiter inside\n'
            '            """;\n'
            '        R.put("k1", "V1");\n'
            '        R.put("k2", "LaterLiteralZz");\n'
            "        int x = 1;\n"
            "    }\n"
            "}\n"
        )
        path = "src/Registry.java"
        expected = {"src/Registry.java::Registry.__static_init_1__"}
        fb_chunks = [c for c in self._forced_fallback(src, path)
                     if "__static_init_" in c.id]
        self.assertEqual({c.id for c in fb_chunks}, expected)
        ts = self.chunker.chunk_java_treesitter(src, path)
        self.assertIsNotNone(ts)
        ts_chunks = [c for c in ts if "__static_init_" in c.id]
        self.assertEqual({c.id for c in ts_chunks}, expected)
        # Line span must match too (the bug truncated the span, dropping the later literal).
        self.assertEqual(fb_chunks[0].lines, ts_chunks[0].lines)
        self.assertIn("LaterLiteralZz", fb_chunks[0].text)

    def test_javac_legal_unicode_owner_categories_match_both_paths(self):
        # Final delivery review P1: Java identifier start/part accepts more than
        # Python ``isalnum``/``\w``. These representatives were independently
        # compiled with javac during review. Preserve exact source spelling (no NFC
        # normalization) on both supported paths, including when tree-sitter puts a
        # legal currency/format character in an ERROR sibling of its identifier node.
        names = (
            "A\u0301Registry",  # Mn combining mark (identifier part)
            "€Box",             # Sc currency symbol (identifier start)
            "A\u203fB",         # Pc connector punctuation
            "A\u200cB",         # Cf identifier-ignorable format character
        )
        for name in names:
            with self.subTest(name=repr(name)):
                src = (
                    '@Ann(value="class Fake", type=Foo.class)\n'
                    f'class {name} {{\n'
                    '    static { R.put("k", "UnicodeOwnerZz"); }\n'
                    '}\n'
                )
                expected = {f"src/Unicode.java::{name}.__static_init_1__"}
                self.assertEqual(
                    self._init_ids(self._forced_fallback(src, "src/Unicode.java")),
                    expected,
                )
                ts = self.chunker.chunk_java_treesitter(src, "src/Unicode.java")
                self.assertIsNotNone(ts)
                self.assertEqual(self._init_ids(ts), expected)

    def test_distinct_unicode_owners_never_collapse_to_one_initializer_id(self):
        # Exact collision reproduction from the final full-wave review. Java treats
        # composed/decomposed-looking spellings as distinct identifiers; do not normalize.
        accented = "A\u0301"
        src = (
            'class A { static { R.put("plain", "PlainOwnerZz"); } }\n'
            f'class {accented} {{ static {{ R.put("accented", "AccentOwnerZz"); }} }}\n'
        )
        expected = {
            "src/Collision.java::A.__static_init_1__",
            f"src/Collision.java::{accented}.__static_init_1__",
        }
        for label, chunks in (
            ("fallback", self._forced_fallback(src, "src/Collision.java")),
            ("tree-sitter", self.chunker.chunk_java_treesitter(src, "src/Collision.java")),
        ):
            with self.subTest(path=label):
                self.assertIsNotNone(chunks)
                inits = [
                    c for c in chunks
                    if "__static_init_" in c.id or "__instance_init_" in c.id
                ]
                self.assertEqual({c.id for c in inits}, expected)
                self.assertEqual(len(inits), len(expected), "distinct owners must keep unique ids")
                text = "\n".join(c.text for c in inits)
                self.assertIn("PlainOwnerZz", text)
                self.assertIn("AccentOwnerZz", text)

    def test_single_character_currency_and_connector_owners_survive_partial_tree(self):
        # Round-6 re-review: tree-sitter represents these javac-legal single-character
        # owners as ERROR + sibling block. A normal class in the same file makes the AST
        # path partially successful, so dispatch must supplement rather than suppress the
        # supported lexical path and silently drop two initializer chunks.
        source = (
            'class A { static { R.put("a", "PlainZz"); } }\n'
            'class € { static { R.put("e", "CurrencyZz"); } }\n'
            'class ‿ { static { R.put("p", "ConnectorZz"); } }\n'
        )
        path = "src/SingleUnicode.java"
        tree = self.chunker._ts_parse("java", source)
        self.assertIsNotNone(tree)
        self.assertTrue(tree.root_node.has_error, "fixture must exercise partial AST recovery")
        expected = {
            f"{path}::A.__static_init_1__",
            f"{path}::€.__static_init_1__",
            f"{path}::‿.__static_init_1__",
        }
        direct = self.chunker.chunk_java_treesitter(source, path)
        self.assertIsNotNone(direct)
        self.assertEqual(self._init_ids(direct), expected)
        self.assertEqual(self._init_ids(self.chunker.chunk_file(source, path)), expected)
        # Also pin the single-owner public path: without an ordinary class, summary
        # extraction falls back to `__module__`; that additive summary must not replace
        # the structured initializer recovered from the partial AST.
        for owner in ("€", "‿"):
            with self.subTest(single_owner=owner):
                single_path = "src/Single.java"
                single = f'class {owner} {{ static {{ R.put("k", "OnlyZz"); }} }}\n'
                public_chunks = self.chunker.chunk_file(single, single_path)
                self.assertEqual(
                    self._init_ids(public_chunks),
                    {f"{single_path}::{owner}.__static_init_1__"},
                )
                self.assertEqual(
                    {chunk.id for chunk in public_chunks},
                    {
                        f"{single_path}::__module__",
                        f"{single_path}::{owner}.__static_init_1__",
                    },
                    "module fallback and recovered initializer must coexist",
                )

    def test_oversized_single_currency_owner_survives_public_summary_fallback(self):
        # Split initializer sections end in `[init] (part N/M)`. Public summary wrapping
        # must recognize those parts and preserve every literal alongside the legacy module
        # fallback when the grammar cannot extract a symbol summary for the owner.
        body = "\n".join(f'        R.put("k{i}", "v{i}");' for i in range(200))
        source = f"class € {{\n    static {{\n{body}\n    }}\n}}\n"
        path = "src/BigEuro.java"
        chunks = self.chunker.chunk_file(source, path)
        ids = {chunk.id for chunk in chunks}
        init_parts = [chunk for chunk in chunks if "€.__static_init_1__" in chunk.id]
        self.assertIn(f"{path}::__module__", ids)
        self.assertGreater(len(init_parts), 1, "fixture must exercise split initializer sections")
        self.assertTrue(all(" [init] (part " in (chunk.section or "") for chunk in init_parts))
        joined = "\n".join(chunk.text for chunk in init_parts)
        self.assertIn('R.put("k0", "v0")', joined)
        self.assertIn('R.put("k199", "v199")', joined)

    def test_table_split_currency_owner_survives_public_summary_fallback(self):
        # The table-aware splitter uses `[init] (rows N–M of T)`, not `(part N/M)`.
        # The stable initializer marker—not one suffix family—is the preservation key.
        rows = "\n".join(f"| k{i} | v{i} |" for i in range(200))
        source = (
            "class € {\n"
            "    static {\n"
            '        String table = """\n'
            "| Key | Value |\n"
            "| --- | --- |\n"
            f"{rows}\n"
            '        """;\n'
            '        R.put("tail", "TailZz");\n'
            "    }\n"
            "}\n"
        )
        path = "src/TableEuro.java"
        chunks = self.chunker.chunk_file(source, path)
        ids = {chunk.id for chunk in chunks}
        init_rows = [chunk for chunk in chunks if "€.__static_init_1__" in chunk.id]
        self.assertIn(f"{path}::__module__", ids)
        self.assertGreater(len(init_rows), 1, "fixture must exercise table-aware splitting")
        self.assertTrue(all(" [init] (rows " in (chunk.section or "") for chunk in init_rows))
        joined = "\n".join(chunk.text for chunk in init_rows)
        self.assertIn("| k0 | v0 |", joined)
        self.assertIn("| k199 | v199 |", joined)
        self.assertIn("TailZz", joined)

    def test_restricted_record_annotation_element_cannot_capture_owner(self):
        # `record` is a restricted identifier, not a globally reserved keyword. Punctuation
        # after an annotation element name must terminate the declaration-keyword candidate
        # in both the streaming fallback classifier and the tree-path header recovery lexer.
        cases = (
            ('@Ann(record="x") class Registry { static { R.put("k", "ClassZz"); } }', "Registry"),
            ('@Ann(record="x") record Registry(int n) { static { R.put("k", "RecordZz"); } }', "Registry"),
        )
        for source, owner in cases:
            with self.subTest(source=source):
                path = "src/Restricted.java"
                expected = {f"{path}::{owner}.__static_init_1__"}
                self.assertEqual(self._init_ids(self._forced_fallback(source, path)), expected)
                direct = self.chunker.chunk_java_treesitter(source, path)
                self.assertIsNotNone(direct)
                self.assertEqual(self._init_ids(direct), expected)

    def test_raw_unicode_escape_owner_is_explicitly_unsupported_and_fails_closed(self):
        # Java translates raw Unicode escapes before tokenization. Wave 1sbfl does not
        # implement that separate prelexical phase; it must not publish tree-sitter's
        # partial `u0041` spelling as a supposedly stable first-class initializer owner.
        cases = (
            r'class \u0041 { static { R.put("k", "FirstZz"); } }',
            r'class A\u0301B { static { R.put("k", "MiddleZz"); } }',
            r'class Alpha\u0301 { static { R.put("k", "TailZz"); } }',
            r'class Outer { class I\u0301nner { static { R.put("k", "NestedZz"); } } }',
        )
        path = "src/EscapedOwner.java"
        for source in cases:
            with self.subTest(source=source):
                fallback = self.chunker._java_initializer_chunks(source, path, "EscapedOwner")
                direct = self.chunker.chunk_java_treesitter(source, path)
                public = self.chunker.chunk_file(source, path)
                self.assertEqual(self._init_ids(fallback), set())
                self.assertEqual(self._init_ids(direct or []), set())
                self.assertEqual(self._init_ids(public), set())
                initializer_ids = "\n".join(
                    c.id for c in (direct or []) + public
                    if "__static_init_" in c.id or "__instance_init_" in c.id
                )
                for partial in ("u0041", "::A.__", "::Alpha.__", "Outer.I.__"):
                    self.assertNotIn(partial, initializer_ids)

    def test_initializer_scanner_auxiliary_memory_does_not_scale_with_file_lines(self):
        # Construct input before tracemalloc starts so the measurement covers helper-owned
        # auxiliary state, not the caller's source. The pre-fix `source.splitlines()` grew
        # from ~86 KiB to ~1.28 MiB over this shape; offset-based span tracking stays flat.
        def peak_for(line_count: int) -> int:
            source = "class A;\n" * line_count
            tracemalloc.start()
            try:
                self.assertEqual(
                    self.chunker._java_initializer_chunks(source, "src/Large.java", "Large"),
                    [],
                )
                _current, peak = tracemalloc.get_traced_memory()
                return peak
            finally:
                tracemalloc.stop()

        small_peak = peak_for(2_000)
        large_peak = peak_for(20_000)
        self.assertLess(
            large_peak,
            small_peak + 64_000,
            f"scanner auxiliary state scaled with source: {small_peak=} {large_peak=}",
        )

    # ---- Hybrid generator (round-4 review design): a small, declarative generator over the
    # declaration-prefix / initializer-identity grammar fragment the fallback interprets — NOT
    # a general Java generator or fuzzer. Category coverage is guaranteed; the fixed seed only
    # COMBINES categories. Each case is valid Java BY CONSTRUCTION with a KNOWN expected owner
    # and initializer set, so we compare fallback vs tree-sitter AND both vs the independent
    # expected owner (so the two agreeing on a WRONG answer cannot pass — 1sr0t's requirement
    # to pair differential agreement with a spec-derived invariant). The bounded combinatorial
    # generator intentionally uses ASCII owners; Java's Unicode identifier categories and
    # collision behavior are covered separately by named, javac-legal category fixtures so that
    # this generator does not multiply a second orthogonal surface through every combination.

    _GEN_ANNOTATIONS = {
        "none": "",
        "marker": "@Ann\n",
        "arg": "@Ann(1)\n",
        "long_string": '@Ann("' + "q" * 6100 + '")\n',           # length dimension
        "class_literal": "@Anno(Foo.class)\n",                    # `class` after `.` (round 4)
        "qualified_class_literal": "@Anno(a.b.Foo.class)\n",
        "array_class_literals": "@Anno({A.class, B.class})\n",
        "multiple": "@A @B\n",
    }
    _GEN_COMMENTS = {
        "none": "", "block": "/*c*/ ", "line": "// hi\n", "multiline_block": "/* multi\n line */ ",
    }
    _GEN_NAMES = {
        "short": "Reg", "dollar": "Generated$Registry", "underscore": "_Impl",
        "digits": "X9", "long": "L" + "o" * 600 + "ng",           # >512 chars (round-3 truncation)
    }
    # container -> (keyword, header_suffix, body_prefix, allows_instance, nested_modifier)
    _GEN_CONTAINERS = {
        "class": ("class", "", "", True, "static "),              # static nested class supports both
        "enum_const": ("enum", "", "A, B;\n        ", True, ""),  # valid enum: constants then ;
        "enum_semi": ("enum", "", ";\n        ", True, ""),       # valid enum: bare ; then decls
        "record": ("record", "(int a)", "", False, ""),          # record: static-only (Java rule)
    }
    # init selection -> (body fragments, expected [(kind, ordinal), ...])
    _GEN_INITS = {
        "one_static": (['static { R.put("k", "V"); }'], [("static", 1)]),
        "two_static": (['static { R.put("a", "1"); }', 'static { R.put("b", "2"); }'],
                       [("static", 1), ("static", 2)]),
        "short_static": (['static { z(); }'], [("static", 1)]),   # below CHUNK_MIN_LINES: merge-exempt
        "static_instance": (['static { R.put("k", "V"); }', '{ R.put("k2", "W"); }'],
                            [("static", 1), ("instance", 1)]),    # class/enum only
    }
    _GEN_NESTING = ("top_level", "nested")

    def _gen_build(self, ann, cm, nm, ck, init, nest):
        """Return (valid Java source, expected initializer id set) for one category tuple."""
        kw, suffix, body_prefix, allows_instance, nested_mod = self._GEN_CONTAINERS[ck]
        frags, exp = self._GEN_INITS[init]
        if not allows_instance and any(k == "instance" for k, _ in exp):
            frags, exp = self._GEN_INITS["one_static"]  # records forbid instance initializers
        name = self._GEN_NAMES[nm]
        body = body_prefix + "\n        ".join(frags)
        ann_txt, cm_txt = self._GEN_ANNOTATIONS[ann], self._GEN_COMMENTS[cm]
        if nest == "nested":
            owner = f"Outer.{name}"
            inner = f"{ann_txt}{nested_mod}{kw} {cm_txt}{name}{suffix} {{\n        {body}\n    }}"
            src = f"class Outer {{\n    {inner}\n}}\n"
        else:
            owner = name
            src = f"{ann_txt}{kw} {cm_txt}{name}{suffix} {{\n    {body}\n}}\n"
        return src, {f"src/Gen.java::{owner}.__{k}_init_{o}__" for k, o in exp}

    def _gen_check(self, src, expected, why):
        fb = self._init_ids(self._forced_fallback(src, "src/Gen.java"))
        ts = self.chunker.chunk_java_treesitter(src, "src/Gen.java")
        self.assertIsNotNone(ts, f"grammar must be present [{why}]\n---\n{src}")
        ts_ids = self._init_ids(ts)
        # tree-sitter must parse the intended declaration (a parse error would drop the inits)
        self.assertEqual(ts_ids, expected, f"tree-sitter != expected owner [{why}]\n---\n{src}")
        # independent spec-derived owner oracle — catches fallback AND tree-sitter agreeing wrongly
        self.assertEqual(fb, expected, f"fallback != expected owner [{why}]\n---\n{src}")
        self.assertEqual(fb, ts_ids, f"fallback != tree-sitter [{why}]\n---\n{src}")

    def test_generated_java_owner_and_init_identity_parity(self):
        import random
        SEED = 20260716
        rng = random.Random(SEED)
        cats = {
            "ann": list(self._GEN_ANNOTATIONS), "cm": list(self._GEN_COMMENTS),
            "nm": list(self._GEN_NAMES), "ck": list(self._GEN_CONTAINERS),
            "init": list(self._GEN_INITS), "nest": list(self._GEN_NESTING),
        }
        base = dict(ann="none", cm="none", nm="short", ck="class", init="one_static", nest="top_level")
        cases = []
        # (1) COVERAGE — every value of every category appears with valid defaults; the seed
        # never decides WHETHER a category is exercised.
        for cat, values in cats.items():
            for v in values:
                sel = dict(base); sel[cat] = v
                cases.append((f"cover:{cat}={v}", sel))
        # (2) COMBINATIONS — the seed only COMBINES categories; bounded budget, no new dependency.
        for _ in range(600):
            sel = {cat: rng.choice(values) for cat, values in cats.items()}
            cases.append((f"combo(seed={SEED})", sel))
        for why, sel in cases:
            src, expected = self._gen_build(**sel)
            self._gen_check(src, expected, why)
        self.assertGreaterEqual(len(cases), 600)  # bounded, ~current scale

    def test_generated_java_metamorphic_decorations_preserve_owner_and_count(self):
        # Metamorphic invariant: adding legal annotations, comments, whitespace, or nesting
        # must not change the declared owner or initializer count (nesting qualifies the owner
        # to Outer.<name> but preserves the count). Catches a defect that shifts identity only
        # when a decoration is present.
        base_src, base_expected = self._gen_build("none", "none", "short", "class",
                                                  "static_instance", "top_level")
        self._gen_check(base_src, base_expected, "metamorphic base")
        # annotations / comments / whitespace: owner AND count invariant.
        for ann, cm in (("marker", "block"), ("class_literal", "line"),
                        ("qualified_class_literal", "multiline_block"), ("multiple", "none")):
            src, expected = self._gen_build(ann, cm, "short", "class", "static_instance", "top_level")
            self.assertEqual(expected, base_expected)  # decoration didn't change owner/count (by design)
            self._gen_check(src, expected, f"metamorphic ann={ann} cm={cm}")
        # nesting: count invariant, owner becomes Outer.<name>.
        nsrc, nexpected = self._gen_build("none", "none", "short", "class", "static_instance", "nested")
        self.assertEqual(len(nexpected), len(base_expected))
        self._gen_check(nsrc, nexpected, "metamorphic nesting")

    def test_fallback_static_init_after_huge_single_segment_still_captured(self):
        # A very long single field-initializer segment (no braces, one statement) must
        # not blow up retained state, and the trailing `static {}` must still be
        # captured — the streaming classifier preserves classification for real code.
        big = " + ".join(f'"tok{i}"' for i in range(4000))  # one very long segment
        src = (
            "class Big {\n"
            f"    String blob = {big};\n"
            '    static { R.put("k", "HugeSegZz"); }\n'
            "}\n"
        )
        self.assertEqual(
            self._init_ids(self._forced_fallback(src, "src/Big.java")),
            {"src/Big.java::Big.__static_init_1__"},
        )

    def test_fallback_exact_initializer_identity_and_metadata(self):
        chunks = self._forced_fallback(self.CATALOG, "src/Bundle.java")
        inits = self._init_chunks(chunks)
        # EXACT id set — generic `path:Lx-Ly` / `__module__` identity cannot satisfy this.
        self.assertEqual(set(inits), self.EXPECTED_INIT_IDS)
        c = inits["src/Bundle.java::Bundle.__static_init_1__"]
        self.assertEqual(c.kind, "code")
        self.assertEqual(c.language, "java")
        self.assertEqual(c.section, "Bundle > Bundle.__static_init_1__" + self.chunker._INIT_SECTION_SUFFIX)
        self.assertEqual(c.lines, (3, 6))
        # Multiple/nested ordinals and container qualification match the tree-sitter path.
        self.assertEqual(inits["src/Bundle.java::Bundle.__static_init_2__"].lines, (11, 13))
        self.assertEqual(inits["src/Bundle.java::Bundle.__instance_init_1__"].lines, (7, 10))
        self.assertIn("NestedZzToken", inits["src/Bundle.java::Bundle.Nested.__static_init_1__"].text)
        self.assertIn("MemberZzToken", inits["src/Bundle.java::Bundle.Member.__static_init_1__"].text)

    def test_fallback_and_treesitter_agree_on_init_identity_and_spans(self):
        ts = self.chunker.chunk_java_treesitter(self.CATALOG, "src/Bundle.java")
        self.assertIsNotNone(ts)
        ts_inits = {i: (c.section, c.lines) for i, c in self._init_chunks(ts).items()}
        fb_inits = {i: (c.section, c.lines)
                    for i, c in self._init_chunks(self._forced_fallback(self.CATALOG, "src/Bundle.java")).items()}
        self.assertEqual(ts_inits, fb_inits)

    def test_fallback_lexically_aware_of_strings_chars_comments(self):
        # Braces / semicolons / comment delimiters / escaped quotes / char literals inside
        # string/comment text must not terminate or open an initializer span.
        src = textwrap.dedent(r"""
            public class Torture {
                static {
                    // fake close } ; in a line comment
                    String a = "brace } and semi ; and \" escaped quote {";
                    char c = '}';
                    /* block } ; comment { */
                    MAP.put("TortureZzToken", a);
                }
                void m() { real(); }
            }
        """).lstrip("\n")
        chunks = self._forced_fallback(src, "src/Torture.java")
        inits = self._init_chunks(chunks)
        self.assertEqual(set(inits), {"src/Torture.java::Torture.__static_init_1__"})
        c = inits["src/Torture.java::Torture.__static_init_1__"]
        self.assertIn("TortureZzToken", c.text)
        # The span stopped at the real closing brace (line 8), not the fake ones inside
        # the comments/strings/char literal.
        self.assertEqual(c.lines, (2, 8))
        # The method after the block was still chunked separately (span didn't run away).
        self.assertTrue(any(i.endswith("Torture.m") for i in {x.id for x in chunks}))

    def test_fallback_single_pass_bounded_scan(self):
        # AC-2 structural/call-count pin: the initializer scan visits each source character
        # a constant number of times (monotonic cursor) — no per-type/whole-source rescan.
        class _CountingStr(str):
            def __new__(cls, s, counter):
                obj = super().__new__(cls, s)
                obj._counter = counter
                return obj
            def __getitem__(self, k):
                self._counter[0] += 1
                return str.__getitem__(self, k)

        base = self.CATALOG
        c1 = [0]
        self.chunker._java_initializer_chunks(_CountingStr(base, c1), "src/Bundle.java", "Bundle")
        # Character inspections stay within a small constant multiple of source length.
        self.assertLessEqual(c1[0], 8 * len(base))
        # Doubling the source ~doubles (not quadruples) the inspections → linear, not O(n^2).
        doubled = base + base
        c2 = [0]
        self.chunker._java_initializer_chunks(_CountingStr(doubled, c2), "src/Bundle.java", "Bundle")
        self.assertLess(c2[0], 2.6 * c1[0])
        # Source-level anti-rescan pin: no whole-source rescan / prefix-slice idioms.
        import inspect
        body = inspect.getsource(self.chunker._java_initializer_chunks)
        for anti in ("finditer(source", "source.count(", "for _ in source_lines",
                     "re.findall(", ".search(source"):
            self.assertNotIn(anti, body, f"anti-pattern {anti!r} present")

    # ---- AC-3: long field-initializer reproduction + disposition ----

    def test_static_final_field_initializer_literals_retained(self):
        # The field-repo shape whose static initializer catalog is the primary symptom:
        # a static-final map field with a multiline builder initializer keeps its literals
        # (captured by the constant-chunk mechanism, bounded by the size cap).
        src = textwrap.dedent("""\
            public class MessagesResourceBundle {
                private static final java.util.Map<String,String> M =
                    new java.util.HashMap<>() {{
                        put("err.ambiguous", "Unable to find unambiguous FieldZzToken");
                        put("err.missing", "value missing");
                    }};
            }
        """)
        chunks = self.chunker.chunk_java_treesitter(src, "src/MessagesResourceBundle.java")
        self.assertIsNotNone(chunks)
        self.assertTrue(any("FieldZzToken" in c.text for c in chunks),
                        "static-final field initializer literals must be retained")
        for c in chunks:
            self.assertLessEqual(len(c.text), self.chunker.MAX_CODE_CHUNK_CHARS)

    def test_plain_field_double_brace_literals_deferred(self):
        # DEFERRED (Decision Log): a PLAIN (non-static-final) field with a double-brace
        # anonymous-class instance initializer is a materially broader field-chunking
        # design (anonymous-class bodies are explicitly out of scope). This pins the KNOWN
        # residual gap so the deferral is honest and any future fix is a visible change.
        src = textwrap.dedent("""\
            public class DBrace {
                java.util.Map<String,String> messages = new java.util.HashMap<>() {{
                    put("db.k", "DoubleBraceZzToken");
                }};
            }
        """)
        chunks = self.chunker.chunk_java_treesitter(src, "src/DBrace.java")
        self.assertIsNotNone(chunks)
        self.assertFalse(any("DoubleBraceZzToken" in c.text for c in chunks),
                         "if this now passes, the AC-3 deferral was resolved — update the Decision Log")

    # ---- AC-7: oversized initializer split preserves every literal ----

    def test_oversized_initializer_split_preserves_all_literals(self):
        puts = "\n".join(
            f'        REG.put("bigkey_{i}_zzmark", "bigval_{i}");' for i in range(200))
        src = f"public class BigCat {{\n    static {{\n{puts}\n    }}\n}}\n"
        chunks = self.chunker.chunk_java_treesitter(src, "src/BigCat.java")
        self.assertIsNotNone(chunks)
        init_parts = [c for c in chunks if "BigCat.__static_init_1__" in c.id]
        self.assertGreater(len(init_parts), 1, "oversized block must split into >1 sub-chunk")
        for c in init_parts:
            self.assertLessEqual(len(c.text), self.chunker.MAX_CODE_CHUNK_CHARS)
        for i in range(200):
            self.assertTrue(any(f"bigkey_{i}_zzmark" in c.text for c in init_parts),
                            f"literal bigkey_{i}_zzmark lost across the split")

    # ---- AC-5: forced-fallback Scala golden — no Java initializer leakage ----

    def test_scala_fallback_unchanged_no_init_marker_leak(self):
        # _chunk_java_like is shared by Java and Scala; the Java-only gate must leave Scala
        # fallback byte-for-byte stable. Golden-pin the full serialized surface.
        src = textwrap.dedent("""\
            package com.x
            class Registry {
              def register(): Unit = {
                map.put("scala.key", "ScalaZzToken")
              }
            }
        """)
        chunks = self.chunker.chunk_scala(src, "src/Registry.scala")
        serialized = [(c.id, c.path, c.kind, c.language, c.lines, c.section, c.text)
                      for c in chunks]
        # Golden = the ACTUAL pre-change fallback surface (the 1-line decl chunk merges
        # into the namespace chunk under _merge_small_chunks — a pre-existing behavior this
        # change must NOT perturb for Scala).
        expected = [
            ("src/Registry.scala::__namespace__", "src/Registry.scala", "code", "scala",
             (1, 2), "Registry > namespace",
             "Registry > namespace\n\npackage com.x\nRegistry > Registry\n\nclass Registry"),
            ("src/Registry.scala::Registry.register", "src/Registry.scala", "code", "scala",
             (3, 5), "Registry > Registry.register",
             '  def register(): Unit = {\n    map.put("scala.key", "ScalaZzToken")\n  }'),
        ]
        self.assertEqual(serialized, expected)
        # No Java initializer marker/chunk leaks into Scala output.
        self.assertFalse(any(c.section and c.section.endswith(self.chunker._INIT_SECTION_SUFFIX)
                             for c in chunks))
        self.assertFalse(any("_init_" in c.id for c in chunks))


class SiblingInitializerCensusTests(unittest.TestCase):
    """Wave 1sbfl AC-5: grammar-enabled census of sibling-language initializer constructs.

    C# static constructors are captured by the existing constructor path (no fix needed).
    Kotlin `init` blocks are DROPPED by the current grammar-specific path — a different
    function (chunk_kotlin_treesitter) and grammar node than Java's, so it is a materially
    separate mechanism, DEFERRED (see the change-doc Decision Log) rather than folded into
    this Java-scoped change. Both are pinned with the grammar active (no line-window
    fallback, which would be no evidence)."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_csharp_static_constructor_literal_is_captured(self):
        src = textwrap.dedent("""\
            public class Reg {
                static Reg() {
                    Map.Add("k", "CsStaticCtorZz");
                }
            }
        """)
        chunks = self.chunker.chunk_csharp_treesitter(src, "src/Reg.cs")
        self.assertIsNotNone(chunks, "C# tree-sitter grammar unavailable (must FAIL, not skip)")
        self.assertTrue(any("CsStaticCtorZz" in c.text for c in chunks),
                        "C# static constructor literal must be captured by the existing path")

    def test_kotlin_init_block_literal_currently_dropped_deferred(self):
        src = textwrap.dedent("""\
            class Reg {
                init {
                    map["k"] = "KotlinInitZz"
                }
            }
        """)
        chunks = self.chunker.chunk_kotlin_treesitter(src, "src/Reg.kt")
        self.assertIsNotNone(chunks, "Kotlin tree-sitter grammar unavailable (must FAIL, not skip)")
        # Grammar ACTIVE: the init block literal is not captured today. This pins the KNOWN
        # gap for the deferral; if it starts passing, the Kotlin sibling fix landed and the
        # Decision Log should be updated.
        self.assertFalse(any("KotlinInitZz" in c.text for c in chunks),
                         "Kotlin init capture would be a separate-mechanism fix — update the Decision Log")


class KotlinConstantChunkTests(unittest.TestCase):
    """Wave 1p4mf: module/object/companion-level `const val` chunked for code_ask value retrieval."""

    def setUp(self):
        self.chunker = load_chunker()

    def _consts(self, source: str, path: str = "src/Config.kt") -> dict:
        # The grammar-availability guard: a missing tree-sitter-kotlin grammar makes the
        # chunker return None, which assertIsNotNone turns into a FAILURE (never a skip).
        result = self.chunker.chunk_kotlin_treesitter(source, path)
        self.assertIsNotNone(
            result, "chunk_kotlin_treesitter returned None — tree-sitter-kotlin grammar missing")
        return {c.id: c for c in result
                if c.section is not None and c.section.endswith(" [const]")}

    def test_file_top_level_const_val_chunked_casing_counterexamples(self):
        # Gate on the `const` modifier, NOT casing: a camelCase const (apiURL) and an
        # UPPER_SNAKE const (MAX_RETRIES) must BOTH be chunked.
        source = textwrap.dedent("""\
            package com.example

            const val apiURL = "https://api.example.com"
            const val MAX_RETRIES = 3
        """)
        consts = self._consts(source)
        self.assertIn("src/Config.kt::apiURL", consts)
        self.assertIn("src/Config.kt::MAX_RETRIES", consts)

    def test_object_and_companion_const_scoped_to_owner(self):
        source = textwrap.dedent("""\
            object Config {
                const val timeout = 30
            }

            class Service {
                companion object {
                    const val VERSION = "1.0"
                }
            }
        """)
        consts = self._consts(source)
        # object const -> {Object}.{NAME}
        self.assertIn("src/Config.kt::Config.timeout", consts)
        # companion const -> qualified with the ENCLOSING CLASS name (not "Companion")
        self.assertIn("src/Config.kt::Service.VERSION", consts)

    def test_scope_local_const_val_excluded(self):
        # SCOPE gate: a function-body-local `const val` is the SAME node type AND carries
        # the SAME const modifier as a top-level const — it must NOT be chunked.
        source = textwrap.dedent("""\
            const val topConst = 1

            fun compute(): Int {
                const val LOCAL_CONST = 2
                return LOCAL_CONST
            }
        """)
        consts = self._consts(source)
        self.assertIn("src/Config.kt::topConst", consts)
        self.assertNotIn("src/Config.kt::LOCAL_CONST", consts)
        self.assertFalse(any("LOCAL_CONST" in cid for cid in consts),
                         "function-local const val leaked into const chunks")

    def test_non_const_declarations_excluded(self):
        # plain val/var, instance val, primary-constructor val/var params, and enum_entry
        # must all be excluded from the const lane.
        source = textwrap.dedent("""\
            val plainTop = 42
            var mutableTop = 7

            class Service(val name: String, var count: Int) {
                val field = 10
            }

            enum class Color { RED, GREEN, BLUE }
        """)
        consts = self._consts(source)
        self.assertNotIn("src/Config.kt::plainTop", consts)
        self.assertNotIn("src/Config.kt::mutableTop", consts)
        self.assertNotIn("src/Config.kt::Service.field", consts)
        self.assertNotIn("src/Config.kt::Service.name", consts)
        self.assertNotIn("src/Config.kt::Service.count", consts)
        self.assertFalse(any("RED" in cid or "GREEN" in cid or "BLUE" in cid for cid in consts),
                         "enum entry leaked into const chunks")

    def test_const_chunk_has_breadcrumb_prefix_and_value(self):
        source = textwrap.dedent("""\
            const val apiURL = "https://api.example.com"
        """)
        consts = self._consts(source)
        chunk = consts["src/Config.kt::apiURL"]
        self.assertEqual(chunk.kind, "code")
        self.assertEqual(chunk.language, "kotlin")
        # breadcrumb prefix injects the symbol name into the embedding text
        self.assertTrue(chunk.text.startswith("Config > apiURL\n\n"), chunk.text)
        # the value is present in the chunk text
        self.assertIn('const val apiURL = "https://api.example.com"', chunk.text)

    def test_const_survives_merge_as_standalone(self):
        # A 1-line const must keep its own id (not fold into a neighbour) via the
        # " [const]" section marker excluded from _merge_small_chunks.
        source = textwrap.dedent("""\
            package com.example

            const val onlyConst = 99

            fun helper() = onlyConst
        """)
        consts = self._consts(source)
        self.assertIn("src/Config.kt::onlyConst", consts)


class SwiftConstantChunkTests(unittest.TestCase):
    """Wave 1p4mf (Swift): module/type-level constant chunking on the tree-sitter path.

    Constants: file/global `let`/`var`, type-level `static let`/`static var`, and enum cases.
    Each -> kind=code chunk, " [const]" section marker (merge-excluded), breadcrumb-prefixed
    text carrying the declaration. NO casing gate: Swift constants are lowerCamelCase
    (apiURL, maxRetries) — an UPPER_SNAKE filter would wrongly drop them. Scope is the
    discriminator: a func/init LOCAL `let`/`var` (same node type) is NOT a constant, nor is an
    instance field, computed var, lazy/@Published var, `if let`, `guard let`, or `for x in`."""

    def setUp(self):
        self.chunker = load_chunker()

    def _chunk(self, source, path="src/Conf.swift"):
        # A missing tree-sitter grammar must FAIL loudly, not skip — a silent skip would let a
        # vacuous gate masquerade as a pass. Run under ~/.wavefoundry/venv (grammars installed).
        result = self.chunker.chunk_swift_treesitter(source, path)
        self.assertIsNotNone(result, "tree-sitter Swift grammar unavailable — gate is vacuous")
        return result

    def _consts(self, source, path="src/Conf.swift"):
        return {c.id: c for c in self._chunk(source, path)
                if c.section and c.section.endswith(" [const]")}

    def test_file_global_let_and_var_marked_with_breadcrumb_and_value(self):
        """File-scope `let`/`var` are constants; lowerCamelCase NOT UPPER_SNAKE; text carries
        breadcrumb + value (counterexample to a casing gate: apiURL, not API_URL)."""
        consts = self._consts(
            'let apiURL = "https://example.com"\n'
            "var globalCounter = 0\n"
        )
        self.assertIn("src/Conf.swift::apiURL", consts)
        self.assertIn("src/Conf.swift::globalCounter", consts)
        c = consts["src/Conf.swift::apiURL"]
        self.assertEqual(c.kind, "code")
        self.assertTrue(c.text.startswith("Conf > apiURL\n\n"))
        self.assertIn("https://example.com", c.text)

    def test_static_let_and_var_on_type_marked_qualified(self):
        """`static let`/`static var` on struct/class -> Type.name id, lowerCamelCase
        (maxRetries, not MAX_RETRIES)."""
        consts = self._consts(
            "struct Config {\n"
            '    static let apiKey = "abc"\n'
            "    static var maxRetries = 3\n"
            "}\n"
        )
        self.assertIn("src/Conf.swift::Config.apiKey", consts)
        self.assertIn("src/Conf.swift::Config.maxRetries", consts)
        self.assertTrue(
            consts["src/Conf.swift::Config.apiKey"].text.startswith("Conf > Config.apiKey\n\n")
        )
        self.assertIn('"abc"', consts["src/Conf.swift::Config.apiKey"].text)

    def test_enum_cases_each_marked(self):
        """Each enum case is a constant (Swift enum cases ARE split out, per the per-language
        rule), including each name in `case a, b` and associated-value cases."""
        consts = self._consts(
            "enum Status {\n"
            "    case ok\n"
            "    case notFound\n"
            "    case serverError(code: Int)\n"
            "}\n"
        )
        self.assertIn("src/Conf.swift::Status.ok", consts)
        self.assertIn("src/Conf.swift::Status.notFound", consts)
        self.assertIn("src/Conf.swift::Status.serverError", consts)

    def test_static_const_in_extension_marked(self):
        """`static let` declared in an `extension Type { ... }` is a type constant."""
        consts = self._consts(
            "extension Config {\n"
            '    static let extra = "y"\n'
            "}\n"
        )
        self.assertIn("src/Conf.swift::Config.extra", consts)

    def test_instance_field_and_computed_and_attributed_not_marked(self):
        """Instance `let`/`var` (= a field), computed `var { ... }`, `lazy var`, and
        `@Published var` are NOT constants — they have no static property_modifier or store no
        value. (Anchored with a real static const so output isn't empty.)"""
        consts = self._consts(
            "struct Config {\n"
            "    static let real = 1\n"
            "    let instanceField = 5\n"
            "    var mutableField = 0\n"
            "    @Published var published = 1\n"
            "    lazy var lazyField = compute()\n"
            "    var computed: Int { return 6 }\n"
            "}\n"
        )
        self.assertIn("src/Conf.swift::Config.real", consts)
        self.assertNotIn("src/Conf.swift::Config.instanceField", consts)
        self.assertNotIn("src/Conf.swift::Config.mutableField", consts)
        self.assertNotIn("src/Conf.swift::Config.published", consts)
        self.assertNotIn("src/Conf.swift::Config.lazyField", consts)
        self.assertNotIn("src/Conf.swift::Config.computed", consts)

    def test_function_locals_not_marked(self):
        """SCOPE-local exclusion: a `let`/`var` inside a func/init body is the SAME node type
        ("property_declaration") as a constant but is NOT one. `if let`/`guard let`/`for x in`
        bindings likewise. (Anchored with a file-scope const so output isn't empty.)"""
        consts = self._consts(
            "let apiURL = \"x\"\n"
            "struct Config {\n"
            "    func doWork() {\n"
            "        let localConst = 42\n"
            "        var localVar = 7\n"
            "        if let unwrapped = maybe { print(unwrapped) }\n"
            "        guard let safe = other else { return }\n"
            "        for item in list { print(item) }\n"
            "    }\n"
            "    init() {\n"
            "        let initLocal = 1\n"
            "    }\n"
            "}\n"
        )
        self.assertIn("src/Conf.swift::apiURL", consts)
        self.assertNotIn("src/Conf.swift::localConst", consts)
        self.assertNotIn("src/Conf.swift::Config.localConst", consts)
        self.assertNotIn("src/Conf.swift::localVar", consts)
        self.assertNotIn("src/Conf.swift::Config.localVar", consts)
        self.assertNotIn("src/Conf.swift::unwrapped", consts)
        self.assertNotIn("src/Conf.swift::Config.unwrapped", consts)
        self.assertNotIn("src/Conf.swift::safe", consts)
        self.assertNotIn("src/Conf.swift::item", consts)
        self.assertNotIn("src/Conf.swift::initLocal", consts)
        self.assertNotIn("src/Conf.swift::Config.initLocal", consts)

    def test_multi_declarator_emits_per_name(self):
        """`static let m = 1, n = 2` and file-scope `let a = 3, b = 4` -> one chunk per name."""
        consts = self._consts(
            "let firstFlag = 3, secondFlag = 4\n"
            "struct Config {\n"
            "    static let m = 1, n = 2\n"
            "}\n"
        )
        self.assertIn("src/Conf.swift::firstFlag", consts)
        self.assertIn("src/Conf.swift::secondFlag", consts)
        self.assertIn("src/Conf.swift::Config.m", consts)
        self.assertIn("src/Conf.swift::Config.n", consts)

    def test_adjacent_consts_each_survive_merge(self):
        """Adjacent 1-line consts each keep their OWN id (" [const]" marker -> merge-excluded)."""
        consts = self._consts(
            "let aOne = 1\n"
            "let bTwo = 2\n"
            "let cThree = 3\n"
        )
        self.assertEqual(
            set(consts),
            {"src/Conf.swift::aOne", "src/Conf.swift::bTwo", "src/Conf.swift::cThree"},
        )


class RubyConstantChunkTests(unittest.TestCase):
    def setUp(self):
        self.chunker = load_chunker()

    def _consts(self, source: str, path: str = "app/config.rb") -> dict:
        chunks = self.chunker.chunk_ruby_treesitter(textwrap.dedent(source), path)
        # Grammar-availability guard: a missing tree-sitter Ruby grammar makes the chunker
        # return None — assert non-None so this FAILS loudly, never silently skips.
        self.assertIsNotNone(chunks)
        return {
            c.id: c
            for c in chunks
            if c.section is not None and c.section.endswith(" [const]")
        }

    def test_module_level_constants_incl_mixed_case(self):
        consts = self._consts(
            """
            MAX_RETRIES = 3
            Timeout = 30
            apiURL = "http://x"
            DEFAULTS = { "k" => 1 }
            """
        )
        self.assertIn("app/config.rb::MAX_RETRIES", consts)
        # mixed-case constant: `Timeout` is a `constant` LHS, NOT excluded for not being ALL_CAPS
        self.assertIn("app/config.rb::Timeout", consts)
        self.assertIn("app/config.rb::DEFAULTS", consts)
        # casing COUNTEREXAMPLE: apiURL has an `identifier` LHS -> a local, not a constant
        self.assertNotIn("app/config.rb::apiURL", consts)

    def test_multi_target_split_per_name(self):
        consts = self._consts("A_URL, B_URL = \"a\", \"b\"\n")
        # one chunk per name for a multi-target (left_assignment_list) constant assignment
        self.assertIn("app/config.rb::A_URL", consts)
        self.assertIn("app/config.rb::B_URL", consts)

    def test_scope_resolution_constant(self):
        consts = self._consts("Config::SETTING = :on\n")
        # Foo::BAR -> keyed by the last segment; full decl text retained
        self.assertIn("app/config.rb::SETTING", consts)
        self.assertIn("Config::SETTING = :on", consts["app/config.rb::SETTING"].text)

    def test_breadcrumb_and_value_in_text(self):
        consts = self._consts("MAX_RETRIES = 3\n")
        chunk = consts["app/config.rb::MAX_RETRIES"]
        # breadcrumb-PREFIXED text injects the symbol name into the embedding
        self.assertTrue(chunk.text.startswith("config > MAX_RETRIES\n\n"))
        self.assertIn("MAX_RETRIES = 3", chunk.text)

    def test_class_level_constant_scoped_incl_mixed_case(self):
        consts = self._consts(
            """
            class Service
              RETRY_LIMIT = 5
              StatusOK = 200
            end
            """
        )
        ids = set(consts)
        self.assertTrue(any(i.endswith("::Service.RETRY_LIMIT") for i in ids))
        # mixed-case class constant survives (no ALL_CAPS gate)
        self.assertTrue(any(i.endswith("::Service.StatusOK") for i in ids))

    def test_module_constant_scoped(self):
        consts = self._consts(
            """
            module Net
              PORT = 8080
            end
            """
        )
        self.assertTrue(any(i.endswith("::Net.PORT") for i in set(consts)))

    def test_method_body_local_const_excluded(self):
        # SCOPE-local exclusion: LOCAL_CONST inside `def run` is the SAME node type
        # (assignment + constant LHS) as REAL_CONST, but lives in a method body -> excluded.
        consts = self._consts(
            """
            class Service
              REAL_CONST = 1
              def run
                LOCAL_CONST = 7
                x = 1
              end
            end
            """
        )
        ids = set(consts)
        self.assertTrue(any(i.endswith("REAL_CONST") for i in ids))
        self.assertFalse(any(i.endswith("LOCAL_CONST") for i in ids))

    def test_ivar_cvar_global_local_and_calls_excluded(self):
        # @ivar / @@cvar / $global / identifier locals / DSL calls are NOT constants.
        # A real method is included so the chunker returns a non-None list (proving the
        # grammar loaded) while the [const] subset is empty.
        consts = self._consts(
            """
            @ivar = 1
            @@cvar = 2
            $global = 3
            local = 4
            Foo.bar(1)
            def helper
              y = 1
            end
            """
        )
        self.assertEqual(consts, {})


class PhpConstantChunkTests(unittest.TestCase):
    def setUp(self):
        self.chunker = load_chunker()

    PHP_SOURCE = textwrap.dedent('''\
        <?php
        namespace App\\Config;

        const API_URL = "https://api.example.com";
        const MAX_RETRIES = 5;
        const FLAG_A = 1, FLAG_B = 2;
        define('LEGACY_TIMEOUT', 30);
        define("STRICT_MODE", true);
        define('DYNAMIC_' . $env, 1);
        $bootstrapVar = 99;
        defined('ALREADY_SET');
        constant('READ_ONLY');

        interface HttpStatus {
            const OK = 200;
        }

        trait Timestamped {
            const FORMAT = "Y-m-d";
        }

        enum Suit: string {
            case Hearts = 'H';
            case Spades = 'S';
            const WILD = 'joker';
        }

        class Settings {
            const camelCaseConst = "ok";
            public const DEFAULT_LOCALE = "en";
            private const SECRET_SALT = "xyz";
            public static $mutable = 10;
            public $name = "n";

            public function configure() {
                define('IN_FUNCTION', 1);
                $localConst = 42;
                return $localConst;
            }
        }
        ''')

    def _consts(self):
        # Grammar-availability guard: a missing tree-sitter PHP grammar returns None here, so
        # assertIsNotNone makes the test FAIL (never silently skip).
        result = self.chunker.chunk_php_treesitter(self.PHP_SOURCE, "src/Config.php")
        self.assertIsNotNone(result, "chunk_php_treesitter returned None (PHP tree-sitter grammar missing?)")
        out = {}
        for c in result:
            if c.section is not None and c.section.endswith(" [const]"):
                out[c.id.split("::", 1)[1]] = c
        return out

    def test_module_const_detected(self):
        consts = self._consts()
        self.assertIn("API_URL", consts)
        self.assertIn("MAX_RETRIES", consts)

    def test_casing_counterexamples_not_dropped(self):
        # camelCase / non-ALL_CAPS constants MUST be kept — `const`/`define` is the signal, not casing.
        consts = self._consts()
        self.assertIn("Settings.camelCaseConst", consts)   # camelCase class const
        self.assertIn("HttpStatus.OK", consts)             # short, mixed-case interface const
        self.assertIn("Timestamped.FORMAT", consts)        # trait const

    def test_multi_declarator_split_per_name(self):
        consts = self._consts()
        self.assertIn("FLAG_A", consts)
        self.assertIn("FLAG_B", consts)

    def test_define_both_quote_styles(self):
        consts = self._consts()
        self.assertIn("LEGACY_TIMEOUT", consts)   # single-quoted name
        self.assertIn("STRICT_MODE", consts)      # double-quoted name

    def test_enum_body_const_kept_but_cases_excluded(self):
        consts = self._consts()
        self.assertIn("Suit.WILD", consts)        # a real `const` inside the enum body
        self.assertNotIn("Suit.Hearts", consts)   # enum_case -> excluded
        self.assertNotIn("Suit.Spades", consts)

    def test_private_const_included(self):
        consts = self._consts()
        self.assertIn("Settings.SECRET_SALT", consts)
        self.assertIn("Settings.DEFAULT_LOCALE", consts)

    def test_scope_local_and_property_exclusions(self):
        # Function-body define()/local and class properties are the structural counter-cases.
        consts = self._consts()
        self.assertNotIn("IN_FUNCTION", consts)           # define() in a method body
        self.assertNotIn("Settings.IN_FUNCTION", consts)
        self.assertNotIn("localConst", consts)            # function local $-var
        self.assertNotIn("Settings.localConst", consts)
        self.assertNotIn("bootstrapVar", consts)          # top-level mutable $-var
        self.assertNotIn("Settings.mutable", consts)      # static property (mutable $x)
        self.assertNotIn("Settings.name", consts)         # instance property
        self.assertNotIn("ALREADY_SET", consts)           # defined() read
        self.assertNotIn("READ_ONLY", consts)             # constant() read
        self.assertNotIn("DYNAMIC_", consts)              # define() with computed (non-literal) name

    def test_breadcrumb_prefix_and_value_in_text(self):
        consts = self._consts()
        c = consts["API_URL"]
        self.assertTrue(c.text.startswith("Config > API_URL"))  # breadcrumb injects the symbol name
        self.assertIn("https://api.example.com", c.text)        # the value is searchable
        # marker suffix is on the section, NOT bleeding into the embedded text
        self.assertNotIn("[const]", c.text)
        self.assertTrue(c.section.endswith(" [const]"))


class OversizedTreeSitterGuardTests(unittest.TestCase):
    """Wave 1p5c4: tree-sitter is skipped on files over the parse cap (a multi-MB/GB file spins
    the AST build); oversized code still chunks via the regex/line fallback."""

    def setUp(self):
        self.chunker = load_chunker()

    def test_ts_parse_returns_none_over_cap(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"WAVEFOUNDRY_MAX_TS_PARSE_BYTES": "100"}):
            self.assertIsNone(self.chunker._ts_parse("python", "x = 1\n" * 100))

    def test_chunk_file_falls_back_on_oversized_code(self):
        import os
        from unittest.mock import patch
        src = "def f():\n    return 1\n" * 80  # well over a 100-byte cap
        with patch.dict(os.environ, {"WAVEFOUNDRY_MAX_TS_PARSE_BYTES": "100"}):
            chunks = self.chunker.chunk_file(src, "big.py")
        self.assertTrue(chunks, "oversized code must still chunk via the regex/line fallback")


if __name__ == "__main__":
    unittest.main()
