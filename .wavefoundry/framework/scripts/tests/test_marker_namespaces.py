"""Shared namespace behavior, consumer mutation, and no-private-alternation census."""
from contextlib import ExitStack
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def namespace_alternations(root):
    import marker_namespaces
    names = set(marker_namespaces.MARKER_NAMESPACES)
    hits = []
    for path in root.rglob('*.py'):
        relative = path.relative_to(root)
        if path == root / 'marker_namespaces.py' or any(
            part in {'tests', '__pycache__', '.pytest_cache'} for part in relative.parts
        ):
            continue
        # Maximal runs of literal alternatives, including runs within groups.
        for match in re.finditer(r'\b[\w-]+(?:\|[\w-]+)+\b', path.read_text(encoding='utf-8')):
            if len(names.intersection(match.group().split('|'))) >= 2:
                hits.append((str(relative), match.group()))
    return hits


class MarkerNamespaceTests(unittest.TestCase):
    def setUp(self):
        from server_tools_support import load_server
        self.server = load_server()
        import chunker
        import marker_namespaces
        import render_agent_surfaces
        self.chunker = chunker
        self.namespaces = marker_namespaces
        self.renderer = render_agent_surfaces
        # Reloading server_impl purges this sibling; bind all consumers to the
        # current module just as a fresh process does, even in the full suite.
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        self.patches.enter_context(patch.object(chunker, 'marker_namespaces', marker_namespaces))
        self.patches.enter_context(patch.object(render_agent_surfaces, 'marker_namespaces', marker_namespaces))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def region(self, namespace='waveforge', annotation=''):
        return f'<!-- {namespace}:x begin{annotation} -->\nGenerated content\n<!-- {namespace}:x end -->\n'

    def assert_chunker_site(self):
        self.assertEqual(self.chunker.chunk_file(self.region(), 'docs/generated.md'), [])

    def assert_code_read_site(self):
        (self.root / 'sample.md').write_text(self.region(), encoding='utf-8')
        response = self.server.code_read_response(self.root, 'sample.md')
        self.assertEqual(response['status'], 'ok')
        self.assertEqual([(r['name'], r['start_line'], r['end_line']) for r in response['data']['marker_regions']], [('x', 1, 3)])

    def assert_stripper_site(self):
        prefix = 'prefix\n## Code and documentation questions (auto-Guru)\nobsolete\n'
        self.assertEqual(self.renderer.strip_legacy_auto_guru_section(prefix + self.region()), 'prefix\n\n' + self.region())

    def test_constant_and_capture_contract(self):
        self.assertEqual(self.namespaces.MARKER_NAMESPACES, ('wave', 'waveframework', 'wavefoundry', 'waveforge'))
        for name in self.namespaces.MARKER_NAMESPACES:
            begin, end, _ = self.namespaces.compile_marker_patterns((name,))
            self.assertEqual(begin.search(f'<!-- {name}:x begin — generated -->').group(1), 'x')
            self.assertEqual(end.search(f'<!-- {name}:x end -->').group(1), 'x')
            self.assertIsNone(end.search('<!-- end -->').group(1))
            self.assertIsNone(begin.search('<!-- unknown:x begin -->'))

    def test_three_real_consumer_sites(self):
        self.assert_chunker_site()
        self.assert_code_read_site()
        self.assert_stripper_site()

    def test_removing_waveforge_kills_each_site_oracle(self):
        begin, end, alternation = self.namespaces.compile_marker_patterns(tuple(
            name for name in self.namespaces.MARKER_NAMESPACES if name != 'waveforge'))
        with patch.multiple(self.namespaces, MARKER_BEGIN_RE=begin, MARKER_END_RE=end,
                            MARKER_NAMESPACE_ALTERNATION=alternation):
            for oracle in (self.assert_chunker_site, self.assert_code_read_site, self.assert_stripper_site):
                with self.subTest(oracle=oracle.__name__), self.assertRaises(AssertionError):
                    oracle()

    def test_named_end_preserves_following_prose_and_bare_end_still_works(self):
        for end in ('<!-- wave:x end -->', '<!-- end -->'):
            region = '<!-- wave:x begin -->\nGenerated\n' + end + '\n'
            self.assertEqual(self.chunker.chunk_file(region, 'docs/example.md'), [])
            chunks = self.chunker.chunk_file(region + '# Authored\n\nHand-authored prose.\n', 'docs/example.md')
            self.assertTrue(chunks)
            self.assertTrue(any('Hand-authored prose.' in chunk.text for chunk in chunks))

    def test_annotated_regions_zero_content_and_authored_content(self):
        for namespace in self.namespaces.MARKER_NAMESPACES:
            with self.subTest(namespace=namespace):
                region = self.region(namespace, ' — generated by renderer')
                self.assertEqual(self.chunker.chunk_file(region, 'docs/example.md'), [])
                self.assertTrue(self.chunker.chunk_file(region + '# Authored\n\nProse.\n', 'docs/example.md'))
        self.assertTrue(self.chunker.chunk_file(self.region('unknown'), 'docs/example.md'))

    def test_stripper_retains_exact_newline_space_anchor(self):
        prefix = 'prefix\n## Code and documentation questions (auto-Guru)\nobsolete\n'
        for marker in (' <!-- wave:x begin -->', '<!--wave:x begin -->', '<!--  wave:x begin -->'):
            self.assertNotIn(marker, self.renderer.strip_legacy_auto_guru_section(prefix + marker))

    def test_no_private_namespace_alternations(self):
        self.assertEqual(namespace_alternations(SCRIPTS), [])

    def test_census_planted_literal_and_distinct_name_polarity(self):
        _, _, alternation = self.namespaces.compile_marker_patterns(self.namespaces.MARKER_NAMESPACES[:2])
        planted = self.root / 'consumer.py'
        planted.write_text(f'pattern = r"{alternation}"\n', encoding='utf-8')
        self.assertEqual(len(namespace_alternations(self.root)), 1)
        name = self.namespaces.MARKER_NAMESPACES[0]
        planted.write_text(f'pattern = r"(?:{name}|{name})"\n', encoding='utf-8')
        self.assertEqual(namespace_alternations(self.root), [])


if __name__ == '__main__':
    unittest.main()
