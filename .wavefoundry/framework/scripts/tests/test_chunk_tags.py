"""Chunk tags are written at index time and the ``tags`` filter works (wave 1z8tz, change 1z8ty).

Commit 28ca7657 moved ``docs_search``/``code_search`` tag filtering onto the
stored ``tags`` column, but nothing wrote it, so every tag filter matched zero
chunks. These tests pin the repair end to end through the REAL build path:

* AC-1: a build stores the tags ``infer_tags`` gives each path, and the filter
  returns only tagged chunks on the dense path, the code FTS half of the hybrid
  search, the docs FTS fallback and the live-walk lexical fallback.
* AC-2: a relocated waves root and a configured archive root are tagged ``wave``.
* AC-3: an index built before tags were written picks them up on the
  CHUNKER_VERSION rechunk with ZERO encoder calls.
* AC-4: the ``infer_tags`` and ``retrieval_eval`` defaults are read at call time.
* AC-5: ``reconcile_scan.is_excluded`` requires ``excluded_dirs``, and no
  non-test module assigns from a ``record_paths`` layout constant at import.
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from record_layout_support import apply_layout, patch_layout  # noqa: E402
from server_tools_support import _make_repo, load_server  # noqa: E402


def setUpModule():
    # Load the server first, as the other server-test modules do: the early
    # classes import `indexer`, which pulls in modules (`review_evidence`) that
    # a later first `load_server()` would reload under tests that already
    # captured them, breaking a following `test_indexer` in one interpreter.
    load_server()

FIXTURE = {
    "docs/waves/1abcd tagged-demo/wave.md": "# Wave Record\n\n## Objective\n\nTagged wave objective text.\n",
    "docs/agents/memory/mem-demo.md": "# Memory\n\nA remembered lesson about tagging.\n",
    "docs/references/guide.md": "# Guide\n\nReference guide text.\n",
    "docs/plain.md": "# Plain\n\nUntagged plain document text.\n",
    "src/app.py": "def app_handler():\n    return 'tagged app'\n",
    "src/tests/test_app.py": "def test_app_handler():\n    assert True\n",
    "config/settings.yaml": "name: tagged\n",
}


def _load_indexer():
    spec = importlib.util.spec_from_file_location("indexer", SCRIPTS_ROOT / "indexer.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["indexer"] = mod
    spec.loader.exec_module(mod)
    return mod


def _embedder(calls: list[str]):
    """Deterministic 384-D embeddings; every embedded text is recorded."""
    import numpy as np

    def fake_embed(texts, batch_size=256):
        for text in list(texts):
            calls.append(text)
            vector = np.zeros(384, dtype=np.float32)
            vector[0] = 1
            vector[1] = (len(text) % 13) / 13
            yield vector

    mock = MagicMock()
    mock.embed.side_effect = fake_embed
    return mock


def _rows(index_dir: Path, table: str) -> list[dict]:
    import sqlite_vector_store as vectors

    if not (index_dir / vectors.FILENAME).is_file():
        return []
    return vectors.payload_rows(index_dir, table)


def _tags_of(row: dict) -> set[str]:
    return set(str(row.get("tags") or "").split())


class _BuildCase(unittest.TestCase):
    def setUp(self):
        self.bi = _load_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.embedded: list[str] = []

    def _build(self, **kwargs) -> dict:
        with patch.object(self.bi, "_get_embedder", return_value=_embedder(self.embedded)), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = self.bi.build_index(self.root, content="all", include_tests=True, verbose=False, **kwargs)
        self.assertFalse(result.get("failed"), result.get("failure"))
        return result

    def _all_rows(self) -> list[dict]:
        return _rows(self.index_dir, "docs") + _rows(self.index_dir, "code")

    def _by_path(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for row in self._all_rows():
            out.setdefault(row["path"], set()).update(_tags_of(row))
        return out


class BuildWritesTagsTests(_BuildCase):
    """AC-1: every stored chunk carries the tags ``infer_tags`` gives its path."""

    def test_full_build_stores_inferred_tags_on_every_row(self):
        import _tag_utils

        _make_repo(self.root, FIXTURE)
        self._build(full=True)
        rows = self._all_rows()
        self.assertTrue(rows)
        for row in rows:
            expected = " ".join(_tag_utils.infer_tags(row["path"], waves_prefix="docs/waves/"))
            self.assertEqual(str(row.get("tags") or ""), expected, row["path"])
        by_path = self._by_path()
        self.assertIn("wave", by_path["docs/waves/1abcd tagged-demo/wave.md"])
        self.assertIn("memory", by_path["docs/agents/memory/mem-demo.md"])
        self.assertIn("reference", by_path["docs/references/guide.md"])
        self.assertIn("test", by_path["src/tests/test_app.py"])
        self.assertEqual(by_path["docs/plain.md"], set())

    def test_incremental_build_tags_a_new_file(self):
        _make_repo(self.root, {"docs/plain.md": FIXTURE["docs/plain.md"]})
        self._build(full=True)
        wave = self.root / "docs/waves/1abcd tagged-demo/wave.md"
        wave.parent.mkdir(parents=True)
        wave.write_text(FIXTURE["docs/waves/1abcd tagged-demo/wave.md"], encoding="utf-8")
        self._build()
        self.assertIn("wave", self._by_path()["docs/waves/1abcd tagged-demo/wave.md"])


class LayoutTaggingTests(_BuildCase):
    """AC-2: tags follow the configured record layout."""

    def test_relocated_waves_root_and_archive_are_tagged_wave(self):
        apply_layout(self, waves_root="project/records/waves", archive_root="archive/old-waves")
        _make_repo(self.root, {
            "project/records/waves/1abcd relocated/wave.md": "# Wave\n\nRelocated wave text.\n",
            "archive/old-waves/1aaaa archived/wave.md": "# Wave\n\nArchived wave text.\n",
            "docs/waves/1abce not-a-wave/wave.md": "# Notes\n\nNot under the waves root.\n",
        })
        self._build(full=True)
        by_path = self._by_path()
        self.assertIn("wave", by_path["project/records/waves/1abcd relocated/wave.md"])
        self.assertIn("wave", by_path["archive/old-waves/1aaaa archived/wave.md"])
        self.assertNotIn("wave", by_path["docs/waves/1abce not-a-wave/wave.md"])

    def test_archive_prefix_argument(self):
        import _tag_utils

        self.assertIn("wave", _tag_utils.infer_tags("archive/w/1a x/wave.md", waves_prefix="docs/waves/",
                                                     archive_prefix="archive/w/"))
        self.assertNotIn("wave", _tag_utils.infer_tags("archive/w/1a x/wave.md", waves_prefix="docs/waves/"))

    def test_record_roots_match_only_as_a_leading_prefix(self):
        import _tag_utils

        for path in ("src/archive/old.py", "src/docs/waves/1a x/wave.md", "vendor/archive/w/1a x/wave.md"):
            with self.subTest(path=path):
                self.assertNotIn("wave", _tag_utils.infer_tags(path, waves_prefix="docs/waves/",
                                                               archive_prefix="archive/"))
        self.assertIn("wave", _tag_utils.infer_tags("archive/old.md", waves_prefix="docs/waves/",
                                                    archive_prefix="archive/"))

    def test_an_empty_waves_root_tags_nothing_wave(self):
        import _tag_utils

        for prefix in ("", "/", "//"):
            with self.subTest(prefix=prefix):
                self.assertNotIn("wave", _tag_utils.infer_tags("src/app.py", waves_prefix=prefix))
                self.assertNotIn("wave", _tag_utils.infer_tags("src/app.py", waves_prefix="docs/waves/",
                                                               archive_prefix=prefix))
        with patch_layout(waves_root=""):
            self.assertEqual(_tag_utils.default_waves_prefix(), "")
            self.assertNotIn("wave", _tag_utils.infer_tags("src/app.py"))
            waves_prefix, archive_prefix = self.bi._tag_prefixes(self.root)
            self.assertNotIn("wave", _tag_utils.infer_tags(
                "src/app.py", waves_prefix=waves_prefix, archive_prefix=archive_prefix))

    def test_incremental_build_tags_a_new_archived_record(self):
        # The incremental loop must pass the build-resolved prefixes: the
        # call-time waves default would hide a lost waves prefix, but the
        # archive prefix has no default.
        apply_layout(self, archive_root="archive/old-waves")
        _make_repo(self.root, {"docs/plain.md": FIXTURE["docs/plain.md"]})
        self._build(full=True)
        archived = self.root / "archive/old-waves/1aaaa archived/wave.md"
        archived.parent.mkdir(parents=True)
        archived.write_text("# Wave\n\nArchived wave text.\n", encoding="utf-8")
        self._build()
        self.assertIn("wave", self._by_path()["archive/old-waves/1aaaa archived/wave.md"])


class RechunkUpgradeTests(_BuildCase):
    """AC-3: an index built before tags were written gains them on the
    CHUNKER_VERSION rechunk without re-embedding anything."""

    def test_chunker_bump_writes_tags_with_zero_encoder_calls(self):
        import _tag_utils

        chunker = self.bi._get_chunker()
        self.assertEqual(chunker.CHUNKER_VERSION, "43")
        _make_repo(self.root, FIXTURE)
        # The pre-change index: version 42 and no tags written.
        with patch.object(chunker, "CHUNKER_VERSION", "42"), \
                patch.object(_tag_utils, "infer_tags", lambda *a, **k: []):
            self._build(full=True)
        self.assertTrue(self.embedded, "the fixture build must embed something")
        self.assertTrue(all(not _tags_of(r) for r in self._all_rows()), "pre-change rows carry no tags")

        self.embedded.clear()
        self._build()  # the ordinary post-upgrade build at 43
        self.assertEqual(self.embedded, [], "the rechunk must reuse every embedding")
        by_path = self._by_path()
        self.assertIn("wave", by_path["docs/waves/1abcd tagged-demo/wave.md"])
        self.assertIn("memory", by_path["docs/agents/memory/mem-demo.md"])
        self.assertIn("test", by_path["src/tests/test_app.py"])
        self.assertIn("config", by_path["config/settings.yaml"])
        self.assertTrue(any(_tags_of(r) for r in _rows(self.index_dir, "docs")))
        self.assertTrue(any(_tags_of(r) for r in _rows(self.index_dir, "code")))

        # A further build is a no-op: nothing is re-embedded or rewritten.
        result = self._build()
        self.assertEqual(self.embedded, [])
        self.assertEqual(result.get("files_indexed") or 0, 0)

    def test_chunk_hash_ignores_tags(self):
        chunk = {"kind": "doc", "language": "", "section": "s", "text": "t"}
        self.assertEqual(self.bi._chunk_hash({**chunk, "tags": ["wave"]}), self.bi._chunk_hash(chunk))

    # Computed with the PRE-change `_chunk_hash` (git HEAD before wave 1z8tz)
    # for HASH_PIN_CHUNK, which carries no tags. The stored hashes of every
    # existing index were written by that function, so the current one must
    # reproduce it byte for byte or embedding reuse breaks.
    HASH_PIN_CHUNK = {"id": "docs/a.md#intro", "path": "docs/a.md", "kind": "doc", "language": "",
                      "section": "Intro", "text": "Tagged chunk text."}
    HASH_PIN = "9930c4734319aafa4b9fff5f2fe992f29e7fc9b3a49dc1577119d490ebedaa88"

    def test_chunk_hash_matches_the_pre_change_digest(self):
        self.assertEqual(self.bi._chunk_hash(self.HASH_PIN_CHUNK), self.HASH_PIN)
        tagged = {**self.HASH_PIN_CHUNK, "tags": ["wave", "agent"]}
        self.assertEqual(self.bi._chunk_hash(tagged), self.HASH_PIN, "tags must not move the hash")


class TagFilterEndToEndTests(_BuildCase):
    """AC-1: the ``tags`` filter returns only tagged chunks on every path."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        _make_repo(self.root, FIXTURE)
        self._build(full=True)

    def _index(self):
        import numpy as np

        idx = self.srv.WaveIndex(self.root)
        idx._embed_query = lambda q, model: np.array([1.0] + [0.0] * 383, dtype=np.float32)
        return idx

    def test_dense_docs_search_filters_by_tag(self):
        idx = self._index()
        with patch.object(idx, "_get_reranker", return_value=None):
            results, _ = idx.search_docs("wave objective", tags=["wave"], top_n=10)
        paths = {r["path"] for r in results}
        self.assertEqual(paths, {"docs/waves/1abcd tagged-demo/wave.md"})
        with patch.object(idx, "_get_reranker", return_value=None):
            results, _ = idx.search_docs("lesson", tags=["memory"], top_n=10)
        self.assertEqual({r["path"] for r in results}, {"docs/agents/memory/mem-demo.md"})

    def test_hybrid_code_search_filters_by_tag(self):
        idx = self._index()
        with patch.object(idx, "_get_reranker", return_value=None):
            results, _ = idx.search_code("app_handler", tags=["test"], top_n=10)
        paths = {r["path"] for r in results}
        self.assertEqual(paths, {"src/tests/test_app.py"})

    def _fts_index(self):
        index = MagicMock()
        index.root = self.root
        exc = self.srv.SemanticModelUnavailableOfflineError("offline")
        index.search_code.side_effect = exc
        index.search_docs.side_effect = exc
        index.search_combined.side_effect = exc
        return index

    def _complete(self):
        import index_state_store

        token = index_state_store.build_epoch_state_token(self.index_dir)
        self.assertEqual(token[1], "complete")
        return token

    def test_docs_fts_fallback_filters_by_tag(self):
        result = self.srv.docs_search_response(self._fts_index(), "wave objective", tags=["wave"],
                                               epoch_state=self._complete())
        self.assertEqual(result["data"]["search_mode"], "lexical_fallback")
        paths = {r["path"] for r in result["data"]["results"]}
        self.assertEqual(paths, {"docs/waves/1abcd tagged-demo/wave.md"})

    def test_code_fts_fallback_filters_by_tag(self):
        query = "app_handler test_app_handler"
        unfiltered = self.srv.code_search_response(self._fts_index(), query, epoch_state=self._complete())
        self.assertEqual({r["path"] for r in unfiltered["data"]["results"]},
                         {"src/app.py", "src/tests/test_app.py"}, "the filter fixture must not be vacuous")
        result = self.srv.code_search_response(self._fts_index(), query, tags=["test"],
                                               epoch_state=self._complete())
        self.assertEqual(result["data"]["search_mode"], "lexical_fallback")
        paths = {r["path"] for r in result["data"]["results"]}
        self.assertEqual(paths, {"src/tests/test_app.py"})

    def test_live_walk_lexical_fallback_filters_by_tag(self):
        idx = self._index()
        results = idx.search_docs_lexical("wave objective text", tags=["wave"], top_n=10)
        self.assertEqual({r["path"] for r in results}, {"docs/waves/1abcd tagged-demo/wave.md"})
        results = idx.search_docs_lexical("remembered lesson", tags=["memory"], top_n=10)
        self.assertEqual({r["path"] for r in results}, {"docs/agents/memory/mem-demo.md"})

    def test_live_walk_tags_an_archive_under_docs(self):
        # The live walk reads docs/ only, so the archive sits there. The archive
        # prefix has no call-time default, so this fails if `_live_docs_chunks`
        # drops the prefixes it resolves.
        apply_layout(self, archive_root="docs/archive/waves")
        archived = self.root / "docs/archive/waves/1aaaa archived/wave.md"
        archived.parent.mkdir(parents=True)
        archived.write_text("# Wave\n\nArchived zephyr record text.\n", encoding="utf-8")
        results = self._index().search_docs_lexical("archived zephyr record", tags=["wave"], top_n=10)
        self.assertIn("docs/archive/waves/1aaaa archived/wave.md", {r["path"] for r in results})


def _fresh_copy(source: Path):
    """A fresh copy of a flat script module under a private name, so the probe
    never replaces the shared ``sys.modules`` entry other tests hold. Callers
    pass a fixed path to a flat (never moved) script."""
    alias = f"_1z8ty_probe_{source.stem}"
    spec = importlib.util.spec_from_file_location(alias, source)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(alias, None)
    return mod


class CallTimeDefaultTests(unittest.TestCase):
    """AC-4: a module first imported under a patched layout follows the layout
    current at call time once the patch is gone."""

    SHIPPED = "docs/waves/1abcd x/wave.md"
    RELOCATED = "project/records/waves/1abcd x/wave.md"

    def test_infer_tags_default_is_read_at_call_time(self):
        import record_paths

        with patch_layout(waves_root="project/records/waves"):
            tag_utils = _fresh_copy(SCRIPTS_ROOT / "_tag_utils.py")
            self.assertIn("wave", tag_utils.infer_tags(self.RELOCATED))
            self.assertNotIn("wave", tag_utils.infer_tags(self.SHIPPED))
        self.assertEqual(record_paths.WAVES_ROOT, "docs/waves")
        self.assertIn("wave", tag_utils.infer_tags(self.SHIPPED))
        self.assertNotIn("wave", tag_utils.infer_tags(self.RELOCATED))
        self.assertFalse(hasattr(tag_utils, "_DEFAULT_WAVES_PREFIX"))

    def test_retrieval_eval_default_is_read_at_call_time(self):
        with patch_layout(waves_root="project/records/waves"):
            ev = _fresh_copy(SCRIPTS_ROOT / "retrieval_eval.py")
            self.assertEqual(ev.classify_carrier(self.RELOCATED), "wave_record")
            self.assertIsNone(ev.classify_carrier(self.SHIPPED))
        self.assertEqual(ev.classify_carrier(self.SHIPPED), "wave_record")
        self.assertIsNone(ev.classify_carrier(self.RELOCATED))
        rows = ev.carrier_rows([self.SHIPPED, self.RELOCATED], [])
        self.assertEqual([r["path"] for r in rows], [self.SHIPPED])
        self.assertFalse(hasattr(ev, "_DEFAULT_WAVES_PREFIX"))


class LayoutCaptureCensusTests(unittest.TestCase):
    """AC-5."""

    def test_is_excluded_requires_excluded_dirs(self):
        import reconcile_scan

        with self.assertRaises(TypeError):
            reconcile_scan.is_excluded("docs/a.md", name="a.md", suffix=".md")
        self.assertFalse(hasattr(reconcile_scan, "EXCLUDED_DIRS"))
        self.assertTrue(reconcile_scan.is_excluded(
            "docs/waves/1a x/wave.md", name="wave.md", suffix=".md", excluded_dirs=("docs/waves",)))

    # A layout constant read at module level captures the layout at import.
    LAYOUT_CONSTANTS = frozenset({"WAVES_ROOT", "PLANS_ROOT", "NESTED", "MAX_DEPTH", "ARCHIVE_ROOT"})
    # (file, assigned name): reason. Not a default argument; a published
    # cross-version constant (see the 1z8ty report).
    KNOWN = {
        ("review_policy.py", "SCAFFOLD_DOCS"): "published default-layout scaffold set read by the upgrade across versions",
    }

    def test_no_module_level_assignment_from_a_layout_constant(self):
        found = []
        for path in sorted(SCRIPTS_ROOT.rglob("*.py")):
            rel = path.relative_to(SCRIPTS_ROOT)
            if rel.parts[0] in {"tests", "index"} or "__pycache__" in rel.parts or rel.name == "record_paths.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)) or node.value is None:
                    continue
                if any(isinstance(n, ast.Attribute) and n.attr in self.LAYOUT_CONSTANTS
                       for n in ast.walk(node.value)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        name = getattr(target, "id", ast.unparse(target))
                        if (rel.as_posix(), name) not in self.KNOWN:
                            found.append(f"{rel.as_posix()}:{node.lineno} {name}")
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
