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
            - (void)doFoo {}
            @end
            @implementation Bar
            - (void)doBar {}
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
        # AC-14: CHUNKER_VERSION must be >= "10" after 12b0v/12b0w additions
        version = self.chunker.CHUNKER_VERSION
        self.assertGreaterEqual(int(version), 10)


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


if __name__ == "__main__":
    unittest.main()
