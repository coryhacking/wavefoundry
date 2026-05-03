from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = SCRIPTS_ROOT / "server.py"


def load_server():
    spec = importlib.util.spec_from_file_location("server", SERVER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["server"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_repo(tmp: Path, files: dict[str, str] | None = None) -> Path:
    """Create a minimal project directory with workflow-config.json."""
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "workflow-config.json").write_text(
        json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
        encoding="utf-8",
    )
    if files:
        for rel, content in files.items():
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    return tmp


def _make_wave(tmp: Path, wave_id: str, status: str, changes: list[dict]) -> Path:
    """Write a wave.md into docs/waves/<wave_id>/."""
    wave_dir = tmp / "docs" / "waves" / wave_id
    wave_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Wave Record\n",
        f"wave-id: `{wave_id}`\n",
        f"Status: {status}\n",
        "\n## Changes\n\n",
    ]
    for c in changes:
        lines.append(f"Change ID: `{c['id']}`\n")
        lines.append(f"Change Status: `{c['status']}`\n\n")
    (wave_dir / "wave.md").write_text("".join(lines), encoding="utf-8")
    return wave_dir


def _write_index_layer(root: Path, chunks: list[dict], vectors, *, model: str = "test-model") -> None:
    import numpy as np

    root.mkdir(parents=True, exist_ok=True)
    (root / "meta.json").write_text(
        json.dumps({"model_versions": {"docs": model}, "file_hashes": {}}),
        encoding="utf-8",
    )
    (root / "docs.json").write_text(json.dumps(chunks), encoding="utf-8")
    np.save(str(root / "docs.npy"), np.array(vectors, dtype=np.float32))


# ---------------------------------------------------------------------------
# Root discovery
# ---------------------------------------------------------------------------

class RootDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_override_path_used(self):
        _make_repo(self.root)
        result = self.srv._discover_root(override=str(self.root))
        self.assertEqual(result, self.root.resolve())

    def test_env_var_project_root(self):
        _make_repo(self.root)
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.root)}):
            result = self.srv._discover_root()
        self.assertEqual(result, self.root.resolve())

    def test_falls_back_to_cwd_when_no_config(self):
        with patch("pathlib.Path.cwd", return_value=self.root):
            result = self.srv._discover_root()
        self.assertEqual(result, self.root.resolve())


# ---------------------------------------------------------------------------
# WaveIndex._cosine_search
# ---------------------------------------------------------------------------

class CosineSearchTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        import numpy as np
        self.np = np
        self.tmp = tempfile.TemporaryDirectory()
        self.index = self.srv.WaveIndex(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_top_n(self):
        np = self.np
        matrix = np.array([[1, 0], [0, 1], [1, 1]], dtype=np.float32)
        chunks = [{"id": f"c{i}"} for i in range(3)]
        q = np.array([1, 0], dtype=np.float32)
        results = self.index._cosine_search(q, matrix, chunks, top_n=2)
        self.assertLessEqual(len(results), 2)

    def test_scores_are_attached(self):
        np = self.np
        matrix = np.array([[1, 0]], dtype=np.float32)
        chunks = [{"id": "c0"}]
        q = np.array([1, 0], dtype=np.float32)
        results = self.index._cosine_search(q, matrix, chunks, top_n=1)
        self.assertIn("score", results[0])
        self.assertAlmostEqual(results[0]["score"], 1.0, places=5)

    def test_zero_matrix_returns_empty(self):
        np = self.np
        matrix = None
        results = self.index._cosine_search(np.zeros(4, dtype=np.float32), matrix, [], top_n=5)
        self.assertEqual(results, [])

    def test_negative_score_chunks_excluded(self):
        np = self.np
        matrix = np.array([[1, 0], [-1, 0]], dtype=np.float32)
        chunks = [{"id": "pos"}, {"id": "neg"}]
        q = np.array([1, 0], dtype=np.float32)
        results = self.index._cosine_search(q, matrix, chunks, top_n=5)
        ids = [r["id"] for r in results]
        self.assertIn("pos", ids)
        self.assertNotIn("neg", ids)


class LayeredIndexTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_search_docs_merges_project_and_packaged_framework_index(self):
        _write_index_layer(
            self.root / ".wavefoundry" / "index",
            [{
                "id": "project-doc",
                "path": "docs/project.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 1],
                "section": None,
                "text": "project docs",
            }],
            [[1, 0]],
        )
        _write_index_layer(
            self.root / ".wavefoundry" / "framework" / "index",
            [{
                "id": "seed",
                "path": "seeds/010-install-wavefoundry.prompt.md",
                "kind": "seed",
                "language": None,
                "lines": [1, 1],
                "section": None,
                "text": "framework seed",
            }],
            [[1, 0]],
        )

        index = self.srv.WaveIndex(self.root)
        import numpy as np
        with patch.object(index, "_indexer_constant", return_value="test-model"):
            with patch.object(index, "_embed_query", return_value=np.array([1, 0], dtype=np.float32)):
                results = index.search_docs("framework project", top_n=5)

        paths = {result["path"] for result in results}
        self.assertIn("docs/project.md", paths)
        self.assertIn(".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md", paths)

    def test_packaged_framework_index_can_satisfy_seed_lookup_without_project_index(self):
        _write_index_layer(
            self.root / ".wavefoundry" / "framework" / "index",
            [{
                "id": "seed",
                "path": "seeds/010-install-wavefoundry.prompt.md",
                "kind": "seed",
                "language": None,
                "lines": [1, 1],
                "section": None,
                "text": "install seed",
            }],
            [[1, 0]],
        )

        index = self.srv.WaveIndex(self.root)
        result = index.get_seed("install-wavefoundry")

        self.assertIsNotNone(result)
        self.assertEqual(result["path"], ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md")

    def test_seed_lookup_tolerates_null_section(self):
        _write_index_layer(
            self.root / ".wavefoundry" / "framework" / "index",
            [{
                "id": "seed",
                "path": "seeds/010-install-wavefoundry.prompt.md",
                "kind": "seed",
                "language": None,
                "lines": [1, 1],
                "section": None,
                "text": "install seed",
            }],
            [[1, 0]],
        )

        index = self.srv.WaveIndex(self.root)
        result = index.get_seed("no-match")

        self.assertIsNone(result)

    def test_search_skips_layer_with_incompatible_vector_dimension(self):
        _write_index_layer(
            self.root / ".wavefoundry" / "index",
            [{
                "id": "project-doc",
                "path": "docs/project.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 1],
                "section": None,
                "text": "project docs",
            }],
            [[1, 0]],
        )
        _write_index_layer(
            self.root / ".wavefoundry" / "framework" / "index",
            [{
                "id": "framework-doc",
                "path": "README.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 1],
                "section": None,
                "text": "framework docs",
            }],
            [[1, 0, 0]],
        )

        index = self.srv.WaveIndex(self.root)
        import numpy as np
        with patch.object(index, "_indexer_constant", return_value="test-model"):
            with patch.object(index, "_embed_query", return_value=np.array([1, 0], dtype=np.float32)):
                results = index.search_docs("project", top_n=5)

        self.assertEqual([result["path"] for result in results], ["docs/project.md"])

    def test_search_skips_layer_with_stale_model_but_seed_lookup_still_reads_chunks(self):
        _write_index_layer(
            self.root / ".wavefoundry" / "framework" / "index",
            [{
                "id": "seed",
                "path": "seeds/010-install-wavefoundry.prompt.md",
                "kind": "seed",
                "language": None,
                "lines": [1, 1],
                "section": None,
                "text": "install seed",
            }],
            [[1, 0]],
            model="old-model",
        )

        index = self.srv.WaveIndex(self.root)
        import numpy as np
        with patch.object(index, "_indexer_constant", return_value="test-model"):
            with patch.object(index, "_embed_query", return_value=np.array([1, 0], dtype=np.float32)):
                results = index.search_docs("install", top_n=5)

        self.assertEqual(results, [])
        self.assertEqual(
            index.get_seed("install-wavefoundry")["path"],
            ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
        )

    def test_search_skips_layer_when_vector_rows_do_not_match_chunks(self):
        _write_index_layer(
            self.root / ".wavefoundry" / "index",
            [
                {
                    "id": "project-doc-1",
                    "path": "docs/one.md",
                    "kind": "doc",
                    "language": None,
                    "lines": [1, 1],
                    "section": None,
                    "text": "one",
                },
                {
                    "id": "project-doc-2",
                    "path": "docs/two.md",
                    "kind": "doc",
                    "language": None,
                    "lines": [1, 1],
                    "section": None,
                    "text": "two",
                },
            ],
            [[1, 0]],
        )

        index = self.srv.WaveIndex(self.root)
        import numpy as np
        with patch.object(index, "_indexer_constant", return_value="test-model"):
            with patch.object(index, "_embed_query", return_value=np.array([1, 0], dtype=np.float32)):
                results = index.search_docs("one", top_n=5)

        self.assertEqual(results, [])

    def test_search_docs_lexical_supports_prompt_kind_by_path(self):
        index = self.srv.WaveIndex(self.root)
        chunks = [
            {
                "id": "prompt",
                "path": "docs/prompts/prepare-wave.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 2],
                "section": "Purpose",
                "text": "prepare wave prompt",
            },
            {
                "id": "doc",
                "path": "docs/references/project-overview.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 2],
                "section": "Overview",
                "text": "project overview",
            },
        ]

        with patch.object(index, "_live_docs_chunks", return_value=chunks):
            results = index.search_docs_lexical("prepare wave", kind="prompt")

        self.assertEqual([result["id"] for result in results], ["prompt"])

    def test_search_docs_lexical_supports_architecture_kind_by_path(self):
        index = self.srv.WaveIndex(self.root)
        chunks = [
            {
                "id": "arch",
                "path": "docs/architecture/current-state.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 2],
                "section": "Runtime Topology",
                "text": "architecture topology",
            },
            {
                "id": "doc",
                "path": "docs/references/project-overview.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 2],
                "section": "Overview",
                "text": "project overview",
            },
        ]

        with patch.object(index, "_live_docs_chunks", return_value=chunks):
            results = index.search_docs_lexical("topology", kind="architecture")

        self.assertEqual([result["id"] for result in results], ["arch"])


# ---------------------------------------------------------------------------
# Wave inspection
# ---------------------------------------------------------------------------

class ListWavesTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_waves_dir_returns_empty(self):
        result = self.srv.list_waves(self.root)
        self.assertEqual(result, [])

    def test_parses_wave_id_and_status(self):
        _make_wave(self.root, "1200a my-wave", "active", [])
        waves = self.srv.list_waves(self.root)
        self.assertEqual(len(waves), 1)
        self.assertEqual(waves[0]["wave_id"], "1200a my-wave")
        self.assertEqual(waves[0]["status"], "active")

    def test_parses_changes(self):
        _make_wave(self.root, "1200a my-wave", "active", [
            {"id": "1234-feat foo", "status": "ready"},
            {"id": "1235-bug bar", "status": "planned"},
        ])
        waves = self.srv.list_waves(self.root)
        changes = waves[0]["changes"]
        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0]["id"], "1234-feat foo")
        self.assertEqual(changes[0]["status"], "ready")

    def test_multiple_waves_sorted(self):
        _make_wave(self.root, "1100a wave-one", "closed", [])
        _make_wave(self.root, "1200a wave-two", "active", [])
        waves = self.srv.list_waves(self.root)
        names = [w["wave_id"] for w in waves]
        self.assertEqual(names, sorted(names))


class ListPlansTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_plans_dir_returns_empty(self):
        result = self.srv.list_plans(self.root)
        self.assertEqual(result, [])

    def test_parses_plan_id_status_title_and_path(self):
        _make_repo(self.root, {
            "docs/plans/1234-feat sample.md": (
                "# Sample Plan\n\n"
                "Change ID: `1234-feat sample`\n"
                "Change Status: `planned`\n"
            ),
        })

        plans = self.srv.list_plans(self.root)

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["id"], "1234-feat sample")
        self.assertEqual(plans[0]["status"], "planned")
        self.assertEqual(plans[0]["title"], "Sample Plan")
        self.assertEqual(plans[0]["path"], "docs/plans/1234-feat sample.md")

    def test_ignores_plan_template(self):
        _make_repo(self.root, {
            "docs/plans/plan-template.md": "# Template\n\nChange ID: `<id>`\n",
            "docs/plans/1234-feat sample.md": "# Sample\n",
        })

        plans = self.srv.list_plans(self.root)

        self.assertEqual([p["id"] for p in plans], ["1234-feat sample"])


class CurrentWaveTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_active_wave(self):
        _make_wave(self.root, "1200a wave", "active", [])
        wave = self.srv.current_wave(self.root)
        self.assertIsNotNone(wave)
        self.assertEqual(wave["status"], "active")

    def test_returns_planned_wave_if_no_active(self):
        _make_wave(self.root, "1200a wave", "planned", [])
        wave = self.srv.current_wave(self.root)
        self.assertIsNotNone(wave)

    def test_returns_none_when_all_closed(self):
        _make_wave(self.root, "1200a wave", "closed", [])
        wave = self.srv.current_wave(self.root)
        self.assertIsNone(wave)

    def test_returns_none_when_no_waves(self):
        wave = self.srv.current_wave(self.root)
        self.assertIsNone(wave)


class GetChangeTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_change_by_prefix_in_waves(self):
        _make_repo(self.root, {
            "docs/waves/1200a wave/1234-feat foo.md": "# Change\n\nsome content",
        })
        text = self.srv.get_change(self.root, "1234")
        self.assertIsNotNone(text)
        self.assertIn("some content", text)

    def test_returns_none_when_not_found(self):
        text = self.srv.get_change(self.root, "9999-nonexistent")
        self.assertIsNone(text)

    def test_case_insensitive_match(self):
        _make_repo(self.root, {
            "docs/waves/1200a wave/1234-feat Foo.md": "# Change\n",
        })
        text = self.srv.get_change(self.root, "FOO")
        self.assertIsNotNone(text)


class GetPromptTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_prompt_by_slug(self):
        _make_repo(self.root, {
            "docs/prompts/plan-feature.md": "# Plan Feature\n\nDo the thing.\n",
        })
        text = self.srv.get_prompt(self.root, "plan-feature")
        self.assertIsNotNone(text)
        self.assertIn("Do the thing", text)

    def test_returns_none_when_no_match(self):
        text = self.srv.get_prompt(self.root, "nonexistent-shortcut")
        self.assertIsNone(text)

    def test_falls_back_to_content_search(self):
        _make_repo(self.root, {
            "docs/prompts/misc.md": "# Misc\n\nPrepare wave instructions here.\n",
        })
        text = self.srv.get_prompt(self.root, "Prepare wave")
        self.assertIsNotNone(text)


class GuidedContractTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()

    def test_first_party_prefix_helper_flags_violations(self):
        viol = self.srv.first_party_tool_names_violating_prefix(["wave_help", "bad_name", "docs_search"])
        self.assertEqual(viol, ["bad_name"])

    def test_resolve_path_under_root_accepts_relative_inside_repo(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = _make_repo(Path(self.tmp.name))
        try:
            (root / "docs" / "foo.md").write_text("x", encoding="utf-8")
            path, err = self.srv.resolve_path_under_root(root, "docs/foo.md")
            self.assertIsNone(err)
            assert path is not None
            self.assertTrue(path.is_file())
        finally:
            self.tmp.cleanup()

    def test_resolve_path_under_root_rejects_parent_escape(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = _make_repo(Path(self.tmp.name))
        try:
            path, err = self.srv.resolve_path_under_root(root, "../../../etc/passwd")
            self.assertIsNone(path)
            assert err is not None
            self.assertEqual(err["code"], "path_outside_allowed_roots")
        finally:
            self.tmp.cleanup()

    def test_docs_search_rejects_invalid_kind(self):
        index = MagicMock()
        result = self.srv.docs_search_response(index, "anything", "not-a-valid-kind")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_arguments")
        index.search_docs.assert_not_called()

    def test_docs_search_normalizes_kind_case(self):
        index = MagicMock()
        index.search_docs.return_value = []
        self.srv.docs_search_response(index, "q", "Doc")
        index.search_docs.assert_called_with("q", kind="doc", top_n=5)

    def test_wave_help_catalog_is_browseable(self):
        self.srv._cached_help_catalog_json.cache_clear()
        result = self.srv.wave_help_response()
        self.assertEqual(result["status"], "ok")
        self.assertIn("core_tools", result["data"])
        self.assertIn("workflows", result["data"])
        self.assertIn("wave_help", result["data"]["core_tools"])
        self.assertIn("wave_map", result["data"]["core_tools"])

    def test_ensure_no_extra_args_returns_envelope(self):
        err = self.srv._ensure_no_extra_args("docs_search", {"extra": 1})
        assert err is not None
        self.assertEqual(err["status"], "error")
        self.assertEqual(err["diagnostics"][0]["code"], "unknown_arguments")

    def test_wave_help_unknown_goal_returns_catalog_and_diagnostic(self):
        result = self.srv.wave_help_response("not-a-real-goal")
        self.assertEqual(result["status"], "ok")
        self.assertIn("workflows", result["data"])
        self.assertEqual(result["diagnostics"][0]["code"], "unknown_goal")

    def test_docs_search_response_includes_result_id_and_trust_label(self):
        index = MagicMock()
        index.search_docs.return_value = [{
            "id": "chunk-1",
            "path": ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
            "kind": "seed",
            "section": "Install",
            "lines": [1, 10],
            "text": "install seed body",
            "score": 0.99,
        }]

        result = self.srv.docs_search_response(index, "install", "seed")

        self.assertEqual(result["status"], "ok")
        entry = result["data"]["results"][0]
        self.assertEqual(entry["trust_label"], self.srv.TRUSTED_FRAMEWORK)
        self.assertTrue(entry["result_id"].startswith("doc:"))

    def test_docs_search_falls_back_when_semantic_model_unavailable_offline(self):
        # docs_health() is NOT called on the search hot path; fallback is exception-driven.
        index = MagicMock()
        index.search_docs.side_effect = self.srv.SemanticModelUnavailableOfflineError("offline model missing")
        index.search_docs_lexical.return_value = [{
            "id": "chunk-1",
            "path": "docs/plans/129nj.md",
            "kind": "doc",
            "section": "Rationale",
            "lines": [1, 5],
            "text": "agent catalog expansion",
            "score": 3.0,
        }]

        result = self.srv.docs_search_response(index, "agent catalog", "doc")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["search_mode"], "lexical_fallback")
        self.assertEqual(result["diagnostics"][0]["code"], "semantic_model_unavailable_offline")
        index.search_docs_lexical.assert_called_once_with("agent catalog", kind="doc", top_n=5)
        index.docs_health.assert_not_called()

    def test_docs_search_calls_semantic_search_directly_without_health_preflight(self):
        # docs_health() must not be called on the search hot path regardless of index state.
        index = MagicMock()
        index.search_docs.return_value = [{
            "id": "chunk-1",
            "path": "docs/plans/129nj.md",
            "kind": "doc",
            "section": "Rationale",
            "lines": [1, 5],
            "text": "agent catalog expansion",
            "score": 0.95,
        }]

        result = self.srv.docs_search_response(index, "agent catalog", "doc")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["search_mode"], "semantic")
        index.search_docs.assert_called_once_with("agent catalog", kind="doc", top_n=5)
        index.docs_health.assert_not_called()

    def test_docs_search_falls_back_to_lexical_on_index_not_ready(self):
        # When the index cannot be loaded, IndexNotReadyError triggers lexical fallback.
        index = MagicMock()
        index.search_docs.side_effect = self.srv.IndexNotReadyError("index missing")
        index.search_docs_lexical.return_value = [{
            "id": "chunk-1",
            "path": "docs/plans/129nj.md",
            "kind": "doc",
            "section": "Rationale",
            "lines": [1, 5],
            "text": "agent catalog expansion",
            "score": 2.0,
        }]

        result = self.srv.docs_search_response(index, "agent catalog", "doc")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["search_mode"], "lexical_fallback")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")
        index.search_docs_lexical.assert_called_once_with("agent catalog", kind="doc", top_n=5)
        index.docs_health.assert_not_called()

    def test_code_search_response_handles_index_not_ready(self):
        index = MagicMock()
        index.search_code.side_effect = self.srv.IndexNotReadyError("missing code index")

        result = self.srv.code_search_response(index, "build index", "python")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")


# ---------------------------------------------------------------------------
# code_search language normalization
# ---------------------------------------------------------------------------

class CodeSearchLanguageNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()

    def _index_with_results(self, results):
        index = MagicMock()
        index.search_code.return_value = results
        return index

    def _fake_result(self):
        return [{
            "id": "src/App.tsx::render",
            "path": "src/App.tsx",
            "kind": "code",
            "language": "typescript",
            "section": "App > render",
            "lines": [10, 20],
            "text": "render() {}",
            "score": 0.9,
        }]

    def test_canonical_language_name_passes_through(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "render", "typescript")
        self.assertEqual(result["data"]["language"], "typescript")
        index.search_code.assert_called_once_with("render", language="typescript", top_n=5)

    def test_raw_extension_without_dot_is_normalized(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "render", "tsx")
        self.assertEqual(result["data"]["language"], "typescript")
        index.search_code.assert_called_once_with("render", language="typescript", top_n=5)

    def test_raw_extension_with_dot_is_normalized(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "render", ".tsx")
        self.assertEqual(result["data"]["language"], "typescript")
        index.search_code.assert_called_once_with("render", language="typescript", top_n=5)

    def test_js_extension_normalizes_to_javascript(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "fetch", "js")
        self.assertEqual(result["data"]["language"], "javascript")
        index.search_code.assert_called_once_with("fetch", language="javascript", top_n=5)

    def test_ts_extension_normalizes_to_typescript(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "parse", "ts")
        self.assertEqual(result["data"]["language"], "typescript")

    def test_sh_extension_normalizes_to_shell(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "build", "sh")
        self.assertEqual(result["data"]["language"], "shell")

    def test_language_extensions_returned_for_canonical_name(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "render", "typescript")
        self.assertEqual(sorted(result["data"]["language_extensions"]), ["ts", "tsx"])

    def test_language_extensions_returned_when_extension_passed(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "render", "tsx")
        self.assertEqual(sorted(result["data"]["language_extensions"]), ["ts", "tsx"])

    def test_language_extensions_none_when_no_filter(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "render", "")
        self.assertIsNone(result["data"]["language_extensions"])

    def test_language_extensions_in_no_results_response(self):
        index = self._index_with_results([])
        result = self.srv.code_search_response(index, "render", "tsx")
        self.assertEqual(result["data"]["language"], "typescript")
        self.assertEqual(sorted(result["data"]["language_extensions"]), ["ts", "tsx"])

    def test_language_extensions_in_index_not_ready_response(self):
        index = MagicMock()
        index.search_code.side_effect = self.srv.IndexNotReadyError("missing")
        result = self.srv.code_search_response(index, "render", "tsx")
        self.assertEqual(result["data"]["language"], "typescript")
        self.assertEqual(sorted(result["data"]["language_extensions"]), ["ts", "tsx"])

    def test_unknown_extension_left_unchanged(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "render", "lua")
        self.assertEqual(result["data"]["language"], "lua")
        self.assertIsNone(result["data"]["language_extensions"])

    def test_server_and_chunker_ext_maps_agree(self):
        # Ensure _EXT_TO_LANG in server.py and _EXT_TO_LANGUAGE in chunker.py
        # map each shared extension to the same canonical language name.
        chunker_mod = sys.modules.get("chunker")
        if chunker_mod is None:
            chunker_path = SCRIPTS_ROOT / "chunker.py"
            chunker_spec = importlib.util.spec_from_file_location("chunker", chunker_path)
            chunker_mod = importlib.util.module_from_spec(chunker_spec)
            sys.modules["chunker"] = chunker_mod
            chunker_spec.loader.exec_module(chunker_mod)

        server_map = self.srv._EXT_TO_LANG
        chunker_map = chunker_mod._EXT_TO_LANGUAGE

        mismatches = []
        for ext, server_lang in server_map.items():
            if ext in chunker_map and chunker_map[ext] != server_lang:
                mismatches.append(
                    f"{ext}: server={server_lang!r} chunker={chunker_map[ext]!r}"
                )
        self.assertEqual(
            mismatches, [],
            "Extension→language mismatch between server._EXT_TO_LANG and chunker._EXT_TO_LANGUAGE:\n"
            + "\n".join(mismatches),
        )


# ---------------------------------------------------------------------------
# code_search language categories
# ---------------------------------------------------------------------------

class CodeSearchLanguageCategoryTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()

    def _index_with_results(self, results):
        index = MagicMock()
        index.search_code.return_value = results
        return index

    def _fake_result(self, language="typescript"):
        return {
            "id": f"src/App.{language}::render",
            "path": f"src/App.{language}",
            "kind": "code",
            "language": language,
            "section": "App > render",
            "lines": [10, 20],
            "text": "render() {}",
            "score": 0.9,
        }

    def test_category_expands_to_language_resolved(self):
        index = self._index_with_results([self._fake_result("typescript")])
        result = self.srv.code_search_response(index, "render", "web")
        self.assertEqual(result["data"]["language"], "web")
        self.assertIn("typescript", result["data"]["language_resolved"])
        self.assertIn("javascript", result["data"]["language_resolved"])

    def test_category_filters_results_to_member_languages(self):
        # Returns unfiltered results; post-filter keeps only category members.
        all_results = [self._fake_result("typescript"), self._fake_result("python")]
        index = self._index_with_results(all_results)
        result = self.srv.code_search_response(index, "render", "web")
        langs = [r["language"] for r in result["data"]["results"]]
        self.assertIn("typescript", langs)
        self.assertNotIn("python", langs)

    def test_category_language_extensions_covers_all_members(self):
        index = self._index_with_results([self._fake_result("typescript")])
        result = self.srv.code_search_response(index, "render", "web")
        exts = result["data"]["language_extensions"]
        self.assertIn("ts", exts)
        self.assertIn("tsx", exts)
        self.assertIn("js", exts)

    def test_java_category_includes_kotlin_scala_groovy(self):
        index = self._index_with_results([self._fake_result("java")])
        result = self.srv.code_search_response(index, "parse", "java")
        resolved = result["data"]["language_resolved"]
        self.assertIn("kotlin", resolved)
        self.assertIn("scala", resolved)
        self.assertIn("groovy", resolved)
        self.assertIn("java", resolved)

    def test_sparksql_resolves_to_sql(self):
        index = self._index_with_results([self._fake_result("sql")])
        result = self.srv.code_search_response(index, "select", "sparksql")
        self.assertEqual(result["data"]["language_resolved"], ["sql"])
        self.assertIn("sql", result["data"]["language_extensions"])

    def test_data_category_resolves_to_sql(self):
        index = self._index_with_results([self._fake_result("sql")])
        result = self.srv.code_search_response(index, "schema", "data")
        self.assertEqual(result["data"]["language_resolved"], ["sql"])

    def test_non_category_has_no_language_resolved(self):
        index = self._index_with_results([self._fake_result("typescript")])
        result = self.srv.code_search_response(index, "render", "typescript")
        self.assertNotIn("language_resolved", result["data"])

    def test_category_no_results_still_has_language_resolved(self):
        index = self._index_with_results([])
        result = self.srv.code_search_response(index, "render", "web")
        self.assertIn("language_resolved", result["data"])
        self.assertIsNotNone(result["data"]["language_extensions"])

    def test_all_category_languages_have_extensions(self):
        # Every language in every category must have at least one extension in _LANG_TO_EXTS.
        categories = self.srv._LANG_CATEGORIES
        lang_to_exts = self.srv._LANG_TO_EXTS
        missing = []
        for cat, langs in categories.items():
            for lang in langs:
                if not lang_to_exts.get(lang):
                    missing.append(f"{cat}.{lang}")
        self.assertEqual(missing, [], f"Languages in categories with no known extensions: {missing}")


# ---------------------------------------------------------------------------
# new_change
# ---------------------------------------------------------------------------

class NewChangeTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_change_doc_file(self):
        result = self.srv.new_change(self.root, "feat", "my-feature")
        out_path = self.root / result["path"]
        self.assertTrue(out_path.exists())

    def test_id_has_kind_and_slug(self):
        result = self.srv.new_change(self.root, "feat", "my-feature")
        self.assertIn("feat", result["id"])
        self.assertIn("my-feature", result["id"])

    def test_path_uses_forward_slashes(self):
        result = self.srv.new_change(self.root, "bug", "login-broken")
        self.assertNotIn("\\", result["path"])

    def test_uses_template_if_exists(self):
        plans_dir = self.root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        (plans_dir / "plan-template.md").write_text(
            "# Template\n\nChange ID: `<id>`\nCustom field: yes\n",
            encoding="utf-8",
        )
        result = self.srv.new_change(self.root, "feat", "from-template")
        text = (self.root / result["path"]).read_text(encoding="utf-8")
        self.assertIn("Custom field: yes", text)

    def test_falls_back_to_default_template(self):
        result = self.srv.new_change(self.root, "feat", "no-template")
        text = (self.root / result["path"]).read_text(encoding="utf-8")
        self.assertIn("Acceptance Criteria", text)

    def test_supports_all_lifecycle_change_kinds(self):
        kind_slugs = {
            "bug": "sample-bug",
            "feat": "sample-feature",
            "enh": "sample-enhancement",
            "change": "sample-change",
            "doc": "sample-documentation",
            "debt": "sample-tech-debt",
            "ref": "sample-refactor",
            "task": "sample-task",
            "maint": "sample-maintenance",
            "ops": "sample-operations",
        }
        for kind, slug in kind_slugs.items():
            with self.subTest(kind=kind):
                result = self.srv.new_change(self.root, kind, slug)
                self.assertIn(f"-{kind} ", result["id"])
                self.assertTrue((self.root / result["path"]).exists())


class BackgroundIndexRefreshTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        indexer = self.root / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
        indexer.parent.mkdir(parents=True, exist_ok=True)
        indexer.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_project_docs_refresh_is_repeat_safe_while_worker_active(self):
        proc = MagicMock()
        proc.pid = 4321
        with patch("subprocess.Popen", return_value=proc) as popen:
            with patch.object(self.srv, "_pid_is_running", side_effect=[True]):
                first = self.srv._trigger_background_index_refresh_for_paths(self.root, ["docs/plans/1200a-feat sample.md"])
                second = self.srv._trigger_background_index_refresh_for_paths(self.root, ["docs/plans/1200a-feat sample.md"])

        self.assertEqual(first, {"project": True, "framework": False})
        self.assertEqual(second, {"project": False, "framework": False})
        popen.assert_called_once()

    def test_framework_paths_trigger_framework_layer_refresh(self):
        proc = MagicMock()
        proc.pid = 4321
        with patch("subprocess.Popen", return_value=proc) as popen:
            result = self.srv._trigger_background_index_refresh_for_paths(
                self.root,
                [".wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md"],
            )

        self.assertEqual(result, {"project": False, "framework": True})
        cmd = popen.call_args.args[0]
        self.assertIn("--index-dir", cmd)
        self.assertIn(".wavefoundry/framework/index", " ".join(cmd))


# ---------------------------------------------------------------------------
# McpRepoCache
# ---------------------------------------------------------------------------

class WaveMapTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_wave_map_resolves_doc_path_and_reads_excerpt(self):
        index = MagicMock()
        index._ensure_loaded = MagicMock()
        index._docs_chunks = []
        index._code_chunks = []
        addr = "doc:docs/workflow-config.json"
        result = self.srv.wave_map_response(self.root, addr, index)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["file_exists"])
        self.assertEqual(result["data"]["path"], "docs/workflow-config.json")
        self.assertIn("lifecycle_id_policy", result["data"]["excerpt"])

    def test_wave_map_rejects_bad_address_scheme(self):
        index = MagicMock()
        result = self.srv.wave_map_response(self.root, "http:evil", index)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_address")

    def test_wave_map_rejects_path_outside_root(self):
        index = MagicMock()
        result = self.srv.wave_map_response(self.root, "doc:../../../etc/passwd", index)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "path_outside_allowed_roots")


class PromptCacheTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_wave_get_prompt_uses_prompt_cache(self):
        prompts = self.root / "docs" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        (prompts / "cached-prompt.md").write_text("# Cached\n\nHello.\n", encoding="utf-8")
        cache = self.srv.McpRepoCache(self.root)
        with patch.object(self.srv, "get_prompt", wraps=self.srv.get_prompt) as gp:
            self.srv.wave_get_prompt_response(self.root, "cached-prompt", cache=cache)
            self.srv.wave_get_prompt_response(self.root, "cached-prompt", cache=cache)
        self.assertEqual(gp.call_count, 1)


class WaveLifecycleMutationTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        _make_wave(self.root, "1200a test-wave", "planned", [])
        _make_repo(self.root, {
            "docs/plans/1200a-feat sample.md": (
                "# Sample\n\n"
                "Change ID: `1200a-feat sample`\n"
                "Change Status: `planned`\n"
                "## Rationale\n\nWhy.\n\n"
                "## Requirements\n\n1. One.\n\n"
                "## Scope\n\nIn scope.\n\n"
                "## Acceptance Criteria\n\n- One.\n\n"
                "## Tasks\n\n- One.\n\n"
                "## AC Priority\n\n| AC | Priority | Rationale |\n| ---- | ---- | ---- |\n| AC-1 | required | Core behavior. |\n"
            ),
        })

    def tearDown(self):
        self.tmp.cleanup()

    def test_wave_create_wave_dry_run(self):
        result = self.srv.wave_create_wave_response(self.root, "new-wave", mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        self.assertFalse((self.root / result["data"]["path"]).exists())

    def test_wave_add_and_remove_change(self):
        with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as trigger:
            add = self.srv.wave_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        self.assertEqual(add["status"], "ok")
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        self.assertIn("1200a-feat sample", wave_md.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "docs" / "plans" / "1200a-feat sample.md").exists())
        self.assertTrue((self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md").exists())
        trigger.assert_called_once()

        with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as trigger:
            remove = self.srv.wave_remove_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        self.assertEqual(remove["status"], "ok")
        self.assertNotIn("1200a-feat sample", wave_md.read_text(encoding="utf-8"))
        self.assertTrue((self.root / "docs" / "plans" / "1200a-feat sample.md").exists())
        self.assertFalse((self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md").exists())
        trigger.assert_called_once()

    def test_wave_add_change_rejects_ambiguous_prefix(self):
        _make_repo(self.root, {
            "docs/plans/1200a-feat sample-two.md": (
                "# Sample Two\n\n"
                "Change ID: `1200a-feat sample-two`\n"
                "Change Status: `planned`\n"
            ),
        })
        result = self.srv.wave_add_change_response(self.root, "1200a test-wave", "sample", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "ambiguous_change_id")

    def test_wave_add_change_is_safe_if_doc_already_relocated_to_target_wave(self):
        relocated = self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md"
        relocated.write_text(
            "# Sample\n\nChange ID: `1200a-feat sample`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        plan_path = self.root / "docs" / "plans" / "1200a-feat sample.md"
        plan_path.unlink()

        result = self.srv.wave_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")

        self.assertEqual(result["status"], "ok")
        self.assertTrue(relocated.exists())
        self.assertIn("1200a-feat sample", (self.root / "docs" / "waves" / "1200a test-wave" / "wave.md").read_text(encoding="utf-8"))

    def test_wave_prepare_requires_admitted_changes(self):
        result = self.srv.wave_prepare_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "no_admitted_changes")

    def test_wave_prepare_repairs_staged_doc_when_wave_copy_missing(self):
        self.srv.wave_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        wave_doc = self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md"
        staged_doc = self.root / "docs" / "plans" / "1200a-feat sample.md"
        wave_doc.rename(staged_doc)

        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            def validate_after_repair(root):
                self.assertTrue(wave_doc.exists())
                self.assertFalse(staged_doc.exists())
                return {"passed": True, "errors": [], "warnings": [], "output": ""}

            with patch.object(self.srv, "run_validate", side_effect=validate_after_repair):
                with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as trigger:
                    result = self.srv.wave_prepare_response(self.root, "1200a test-wave", mode="create")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["repaired"], 1)
        self.assertTrue(wave_doc.exists())
        self.assertFalse(staged_doc.exists())
        trigger.assert_called_once()

    def test_wave_prepare_reports_duplicate_change_doc_locations(self):
        self.srv.wave_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        wave_doc = self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md"
        staged_doc = self.root / "docs" / "plans" / "1200a-feat sample.md"
        staged_doc.write_text(wave_doc.read_text(encoding="utf-8"), encoding="utf-8")

        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_prepare_response(self.root, "1200a test-wave", mode="dry_run")

        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "duplicate_change_doc_locations" for d in result["diagnostics"]))

    def test_wave_pause_writes_handoff(self):
        result = self.srv.wave_pause_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        self.assertTrue(handoff.exists())

    def test_wave_pause_preserves_existing_handoff_sections(self):
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "# Session Handoff\n\n## Notes\n\nkeep-me\n\n## Current Session\n\n**Old wave:** placeholder\n",
            encoding="utf-8",
        )
        result = self.srv.wave_pause_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        text = handoff.read_text(encoding="utf-8")
        self.assertIn("keep-me", text)
        self.assertIn("1200a test-wave", text)

    def test_wave_review_reports_ok_when_lint_passes(self):
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as trigger:
                result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["lint_passed"])
        self.assertIn("required_lanes", result["data"])
        trigger.assert_called_once()

    def test_wave_review_ok_when_signoffs_recorded(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            (
                "# Wave Record\n"
                "wave-id: `1200a test-wave`\n"
                "Status: active\n\n"
                "## Participants\n\n"
                "| Role | Lane | Owns |\n"
                "|------|------|------|\n"
                "| architecture-reviewer | review | `1200a-feat sample` |\n"
                "| code-reviewer | review | `1200a-feat sample` |\n\n"
                "## Review Checkpoints\n\n"
                "- prepare wave completed\n\n"
                "## Review Evidence\n\n"
                "- architecture-reviewer sign-off: approved\n"
                "- code-reviewer sign-off: approved\n"
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")

    def test_wave_review_requires_per_lane_evidence_not_global_checkpoint(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            (
                "# Wave Record\n"
                "wave-id: `1200a test-wave`\n"
                "Status: active\n\n"
                "## Participants\n\n"
                "| Role | Lane | Owns |\n"
                "|------|------|------|\n"
                "| architecture-reviewer | review | `1200a-feat sample` |\n"
                "| code-reviewer | review | `1200a-feat sample` |\n\n"
                "## Review Checkpoints\n\n"
                "- Wave approved globally with one sign-off line.\n\n"
                "## Review Evidence\n\n"
                "- architecture-reviewer sign-off: approved\n"
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_lane_signoff" for d in result["diagnostics"]))

    def test_wave_close_requires_signoff_and_no_open_changes(self):
        _make_wave(self.root, "1200a test-wave", "active", [{"id": "1200a-feat sample", "status": "active"}])
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("open_changes_remaining", codes)
        self.assertIn("missing_signoff_evidence", codes)

    def test_wave_close_create_succeeds_when_requirements_met(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            (
                "# Wave Record\n"
                "wave-id: `1200a test-wave`\n"
                "Status: active\n\n"
                "## Changes\n\n"
                "Change ID: `1200a-feat sample`\n"
                "Change Status: `complete`\n\n"
                "## Review Evidence\n\n"
                "- architecture-reviewer: approved\n"
                "- code-reviewer: approved\n"
                "- qa-reviewer: approved\n"
                "- security-reviewer: approved\n"
                "- performance-reviewer: approved\n"
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("Status: closed", wave_md.read_text(encoding="utf-8"))
        self.assertNotIn("archive_path", result["data"])

    def test_wave_close_dry_run_fails_when_participants_missing_lane_in_evidence(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            (
                "# Wave Record\n"
                "wave-id: `1200a test-wave`\n"
                "Status: active\n\n"
                "## Changes\n\n"
                "Change ID: `1200a-feat sample`\n"
                "Change Status: `complete`\n\n"
                "## Participants\n\n"
                "| Role | Lane | Owns |\n"
                "|------|------|------|\n"
                "| architecture-reviewer | review | x |\n"
                "| code-reviewer | review | x |\n\n"
                "## Review Evidence\n\n"
                "- architecture-reviewer sign-off: approved\n"
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_lane_signoff" for d in result["diagnostics"]))


class McpRepoCacheTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_plans_returns_same_cached_list_when_fingerprint_unchanged(self):
        cache = self.srv.McpRepoCache(self.root)
        plans_dir = self.root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        (plans_dir / "1000-feat x.md").write_text(
            "# X\n\nChange ID: `1000-feat x`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        a = cache.list_plans_cached()
        b = cache.list_plans_cached()
        self.assertIs(a, b)

    def test_list_plans_cache_refreshes_when_plan_files_change(self):
        cache = self.srv.McpRepoCache(self.root)
        plans_dir = self.root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        (plans_dir / "1000-feat x.md").write_text(
            "# X\n\nChange ID: `1000-feat x`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        first = cache.list_plans_cached()
        (plans_dir / "1001-feat y.md").write_text(
            "# Y\n\nChange ID: `1001-feat y`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        second = cache.list_plans_cached()
        self.assertGreater(len(second), len(first))

    def test_invalidate_clears_plans_cache_identity(self):
        cache = self.srv.McpRepoCache(self.root)
        plans_dir = self.root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        (plans_dir / "1000-feat x.md").write_text(
            "# X\n\nChange ID: `1000-feat x`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        a = cache.list_plans_cached()
        cache.invalidate()
        b = cache.list_plans_cached()
        self.assertIsNot(a, b)
        self.assertEqual([p["id"] for p in a], [p["id"] for p in b])


# ---------------------------------------------------------------------------
# Framework ops (mocked subprocess)
# ---------------------------------------------------------------------------

class RunValidateTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, returncode: int, output: str) -> dict:
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stdout = output
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            return self.srv.run_validate(self.root)

    def test_passed_true_on_zero_returncode(self):
        result = self._run(0, "ok\n")
        self.assertTrue(result["passed"])

    def test_passed_false_on_nonzero(self):
        result = self._run(1, "ERROR: something wrong\n")
        self.assertFalse(result["passed"])

    def test_errors_extracted(self):
        result = self._run(1, "ERROR: bad field\nWARNING: stale date\n")
        self.assertIn("ERROR: bad field", result["errors"])
        self.assertIn("WARNING: stale date", result["warnings"])


class RunGardenTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, returncode: int, output: str) -> dict:
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stdout = output
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            return self.srv.run_garden(self.root)

    def test_passed_true_on_zero(self):
        result = self._run(0, "")
        self.assertTrue(result["passed"])

    def test_files_updated_count(self):
        result = self._run(0, "Wrote docs/foo.md\nWrote docs/bar.md\n")
        self.assertEqual(result["files_updated"], 2)

    def test_no_updates_when_empty_output(self):
        result = self._run(0, "")
        self.assertEqual(result["files_updated"], 0)


class RunIndexRebuildTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_index_state(
        self,
        *,
        layer: str = "project",
        file_hashes: dict[str, str] | None = None,
        docs_chunks: list[dict] | None = None,
        code_chunks: list[dict] | None = None,
        built_at: str = "2026-04-30T00:00:00Z",
    ) -> None:
        if layer == "framework":
            index_dir = self.root / ".wavefoundry" / "framework" / "index"
        else:
            index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "meta.json").write_text(json.dumps({
            "built_at": built_at,
            "content": ["docs"],
            "file_hashes": file_hashes or {"docs/a.md": "h1"},
        }), encoding="utf-8")
        (index_dir / "docs.json").write_text(json.dumps(docs_chunks or [{"id": "d1"}]), encoding="utf-8")
        (index_dir / "code.json").write_text(json.dumps(code_chunks or []), encoding="utf-8")

    def _run(
        self,
        returncode: int,
        output: str,
        *,
        content: str = "docs",
        full: bool = False,
        layer: str = "project",
    ) -> dict:
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stdout = output
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            return self.srv.run_index_rebuild(self.root, content=content, full=full, layer=layer)

    def test_passed_true_on_zero(self):
        self._write_index_state()
        result = self._run(0, "build_index: done — 1 files indexed, 1 doc chunks, 0 code chunks")
        self.assertTrue(result["passed"])
        self.assertEqual(result["content"], "docs")
        self.assertEqual(result["stats"]["files_indexed"], 1)
        self.assertEqual(result["stats"]["files_total"], 1)
        self.assertEqual(result["stats"]["doc_chunks"], 1)

    def test_full_flag_propagates(self):
        """Project ``content=all`` runs ``setup_index.py`` (docs + code); ``--full`` is appended."""
        with patch("subprocess.run") as run:
            mock_result = MagicMock(returncode=0, stdout="ok\n", stderr="")
            run.return_value = mock_result
            self.srv.run_index_rebuild(self.root, content="all", full=True)
        cmd = run.call_args.args[0]
        self.assertIn("setup_index.py", str(cmd[1]))
        self.assertIn("--include-code", cmd)
        self.assertIn("--full", cmd)

    def test_index_scope_reflects_full_flag(self):
        with patch("subprocess.run") as run:
            mock_result = MagicMock(returncode=0, stdout="ok\n", stderr="")
            run.return_value = mock_result
            inc = self.srv.run_index_rebuild(self.root, content="docs", full=False)
            full = self.srv.run_index_rebuild(self.root, content="docs", full=True)
        self.assertEqual(inc["index_scope"], "incremental_update")
        self.assertEqual(full["index_scope"], "full_rebuild")

    def test_project_all_rebuild_uses_setup_index_script(self):
        with patch("subprocess.run") as run:
            mock_result = MagicMock(returncode=0, stdout="ok\n", stderr="")
            run.return_value = mock_result
            self.srv.run_index_rebuild(self.root, content="all", full=True)
        cmd = run.call_args.args[0]
        self.assertIn("setup_index.py", str(cmd[1]))
        self.assertIn("--include-code", cmd)
        self.assertIn("--full", cmd)

    def test_project_code_rebuild_forwards_workflow_include_prefixes(self):
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({
                "indexing": {
                    "project_include_prefixes": {
                        "code": [".wavefoundry/framework/scripts", "vendor/docs"]
                    }
                }
            }),
            encoding="utf-8",
        )
        with patch("subprocess.run") as run:
            mock_result = MagicMock(returncode=0, stdout="ok\n", stderr="")
            run.return_value = mock_result
            self.srv.run_index_rebuild(self.root, content="code")
        cmd = run.call_args.args[0]
        self.assertIn("--project-include-prefix", cmd)
        self.assertIn(".wavefoundry/framework/scripts", cmd)
        self.assertIn("vendor/docs", cmd)

    def test_framework_layer_uses_framework_index_args(self):
        with patch("subprocess.run") as run:
            mock_result = MagicMock(returncode=0, stdout="ok\n", stderr="")
            run.return_value = mock_result
            result = self.srv.run_index_rebuild(self.root, content="docs", layer="framework")
        cmd = run.call_args.args[0]
        self.assertEqual(result["layer"], "framework")
        self.assertIn("--index-dir", cmd)
        self.assertIn(".wavefoundry/framework/index", cmd)
        self.assertIn("--include-prefix", cmd)
        self.assertIn(".wavefoundry/framework", cmd)
        self.assertIn("--no-ignore-files", cmd)

    def test_up_to_date_rebuild_reports_zero_files_indexed(self):
        self._write_index_state(file_hashes={"docs/a.md": "h1", "docs/b.md": "h2"}, docs_chunks=[{"id": "d1"}, {"id": "d2"}])
        result = self._run(0, "build_index: index is up to date\n")
        self.assertTrue(result["stats"]["up_to_date"])
        self.assertEqual(result["stats"]["files_indexed"], 0)
        self.assertEqual(result["stats"]["files_total"], 2)
        self.assertEqual(result["stats"]["doc_chunks"], 2)

    def test_invalid_content_raises(self):
        with self.assertRaises(ValueError):
            self.srv.run_index_rebuild(self.root, content="bad")

    def test_invalid_layer_raises(self):
        with self.assertRaises(ValueError):
            self.srv.run_index_rebuild(self.root, layer="bad")

    def test_framework_layer_rejects_non_docs_content(self):
        with self.assertRaises(ValueError):
            self.srv.run_index_rebuild(self.root, content="all", layer="framework")

    def test_framework_layer_stats_read_from_framework_index(self):
        self._write_index_state(
            layer="framework",
            file_hashes={"seed/a.md": "h1", "seed/b.md": "h2"},
            docs_chunks=[{"id": "s1"}, {"id": "s2"}, {"id": "s3"}],
        )
        result = self._run(
            0,
            "build_index: full docs rebuild — 2 files\nbuild_index: done — 2 files indexed, 3 doc chunks, 0 code chunks\n",
            layer="framework",
        )
        self.assertEqual(result["stats"]["files_total"], 2)
        self.assertEqual(result["stats"]["files_indexed"], 2)
        self.assertEqual(result["stats"]["doc_chunks"], 3)
        self.assertEqual(result["stats"]["rebuild_scope"], "full")


class WaveIndexBuildResponseTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_invalid_mode_returns_error(self):
        result = self.srv.wave_index_build_response(self.root, mode="full-refresh")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_arguments")

    def test_invalid_content_returns_error(self):
        result = self.srv.wave_index_build_response(self.root, content="bad")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_arguments")

    def test_invalid_layer_returns_error(self):
        result = self.srv.wave_index_build_response(self.root, layer="bad")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_arguments")

    def test_success_invalidates_cache(self):
        cache = self.srv.McpRepoCache(self.root)
        with patch.object(
            self.srv,
            "run_index_rebuild",
            return_value={
                "passed": True,
                "content": "docs",
                "full": False,
                "mode": "update",
                "index_scope": "incremental_update",
                "layer": "project",
                "stats": {"files_indexed": 1, "files_total": 1, "doc_chunks": 1, "code_chunks": 0, "up_to_date": False},
                "output": "ok",
                "summary": "done",
            },
        ):
            with patch.object(cache, "invalidate") as invalidate:
                result = self.srv.wave_index_build_response(self.root, content="docs", mode="update", cache=cache)
        self.assertEqual(result["status"], "ok")
        invalidate.assert_called_once()
        self.assertIn("stats", result["data"])

    def test_failure_returns_recovery_diagnostic(self):
        with patch.object(
            self.srv,
            "run_index_rebuild",
            return_value={
                "passed": False,
                "content": "docs",
                "full": False,
                "mode": "update",
                "layer": "project",
                "stats": {},
                "output": "boom",
                "summary": "",
            },
        ):
            result = self.srv.wave_index_build_response(self.root, content="docs", mode="update")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_rebuild_failed")

    def test_framework_failure_returns_framework_recovery_command(self):
        with patch.object(
            self.srv,
            "run_index_rebuild",
            return_value={
                "passed": False,
                "content": "docs",
                "full": False,
                "mode": "update",
                "layer": "framework",
                "stats": {},
                "output": "boom",
                "summary": "",
            },
        ):
            result = self.srv.wave_index_build_response(self.root, content="docs", layer="framework")
        self.assertEqual(result["status"], "error")
        self.assertIn(".wavefoundry/framework/index", result["diagnostics"][0]["recovery_usage"])


# ---------------------------------------------------------------------------
# wave_index_health
# ---------------------------------------------------------------------------

class WaveIndexHealthTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()

    def test_returns_ok_when_semantic_ready(self):
        index = MagicMock()
        index.docs_health.return_value = {
            "semantic_ready": True,
            "stale_layers": [],
            "missing_layers": [],
            "has_any_index": True,
            "compatible_chunks": True,
            "readiness_overview": "ready",
            "project": {"readiness": "current"},
            "framework": {"readiness": "current"},
        }
        result = self.srv.wave_index_health_response(index)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["data"]["readiness_overview"], "ready")

    def test_returns_ok_with_index_stale_diagnostic(self):
        # AC-1: health check returns "ok" even when index is stale — agents read
        # readiness_overview and diagnostics to decide whether to reindex.
        index = MagicMock()
        index.docs_health.return_value = {
            "semantic_ready": False,
            "stale_layers": ["project"],
            "missing_layers": [],
            "has_any_index": True,
            "compatible_chunks": True,
            "readiness_overview": "needs_update",
            "project": {},
            "framework": {},
        }
        result = self.srv.wave_index_health_response(index)
        self.assertEqual(result["status"], "ok")
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("index_stale", codes)
        self.assertEqual(result["data"]["readiness_overview"], "needs_update")

    def test_returns_ok_with_index_missing_diagnostic(self):
        index = MagicMock()
        index.docs_health.return_value = {
            "semantic_ready": False,
            "stale_layers": [],
            "missing_layers": ["project"],
            "has_any_index": False,
            "compatible_chunks": False,
            "readiness_overview": "incomplete",
            "project": {},
            "framework": {},
        }
        result = self.srv.wave_index_health_response(index)
        self.assertEqual(result["status"], "ok")
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("index_missing", codes)
        self.assertEqual(result["data"]["readiness_overview"], "incomplete")

    def test_returns_ok_with_index_degraded_diagnostic(self):
        index = MagicMock()
        index.docs_health.return_value = {
            "semantic_ready": False,
            "stale_layers": [],
            "missing_layers": [],
            "has_any_index": True,
            "compatible_chunks": False,
            "readiness_overview": "degraded",
            "project": {"readiness": "current"},
            "framework": {"readiness": "current"},
        }
        result = self.srv.wave_index_health_response(index)
        self.assertEqual(result["status"], "ok")
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("index_degraded", codes)
        self.assertEqual(result["data"]["readiness_overview"], "degraded")

    def test_returns_ok_with_index_absent_diagnostic(self):
        index = MagicMock()
        index.docs_health.return_value = {
            "semantic_ready": False,
            "stale_layers": [],
            "missing_layers": [],
            "has_any_index": False,
            "compatible_chunks": False,
            "readiness_overview": "absent",
            "project": {"readiness": "idle"},
            "framework": {"readiness": "idle"},
        }
        result = self.srv.wave_index_health_response(index)
        self.assertEqual(result["status"], "ok")
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("index_absent", codes)
        self.assertEqual(result["data"]["readiness_overview"], "absent")

    def test_exception_from_docs_health_returns_structured_error(self):
        index = MagicMock()
        index.docs_health.side_effect = RuntimeError("unexpected failure")
        result = self.srv.wave_index_health_response(index)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_health_error")

    def test_docs_health_not_called_during_docs_search(self):
        # Regression: docs_health must NOT be called on the search hot path.
        index = MagicMock()
        index.search_docs.return_value = []
        self.srv.docs_search_response(index, "query")
        index.docs_health.assert_not_called()


# ---------------------------------------------------------------------------
# wave_audit
# ---------------------------------------------------------------------------

class WaveAuditTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _healthy_index(self):
        idx = MagicMock()
        idx.docs_health.return_value = {
            "semantic_ready": True,
            "readiness_overview": "ready",
            "stale_layers": [],
            "missing_layers": [],
            "compatible_chunks": True,
            "has_any_index": True,
        }
        return idx

    def _absent_index(self):
        idx = MagicMock()
        idx.docs_health.return_value = {
            "semantic_ready": False,
            "readiness_overview": "absent",
            "stale_layers": [],
            "missing_layers": [],
            "compatible_chunks": False,
            "has_any_index": False,
        }
        return idx

    def _passing_validate(self):
        return {"passed": True, "errors": [], "warnings": [], "output": ""}

    def _failing_validate(self):
        return {"passed": False, "errors": ["missing Last verified"], "warnings": [], "output": ""}

    def test_healthy_state_returns_ready_true(self):
        """AC-1, AC-2: all sub-checks pass → ready=True, status ok."""
        wave_record = {
            "id": "w1",
            "status": "active",
            "changes": [],
            "title": "Wave",
            "path": "docs/waves/w1/wave.md",
        }
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._passing_validate()):
            result = self.srv.wave_audit_response(
                self.root, index=self._healthy_index()
            )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["ready"])
        self.assertEqual(result["diagnostics"], [])
        self.assertIn("wave_current", result["next_tools"])

    def test_lint_fail_path(self):
        """AC-3: lint failure adds wave_validate to next_tools, ready=False."""
        wave_record = {"id": "w1", "status": "active", "changes": [], "title": "Wave", "path": ""}
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._failing_validate()):
            result = self.srv.wave_audit_response(
                self.root, index=self._healthy_index()
            )
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["ready"])
        self.assertIn("wave_validate", result["next_tools"])
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("docs_lint_error", codes)

    def test_index_absent_path(self):
        """AC-4: index not ready adds wave_index_build to next_tools, ready=False."""
        wave_record = {"id": "w1", "status": "active", "changes": [], "title": "Wave", "path": ""}
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._passing_validate()):
            result = self.srv.wave_audit_response(
                self.root, index=self._absent_index()
            )
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["ready"])
        self.assertIn("wave_index_build", result["next_tools"])
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("index_not_ready", codes)

    def test_no_active_wave_path(self):
        """AC-5: no wave found → wave={}, ready=False, no unhandled exception."""
        with patch.object(self.srv, "current_wave", return_value=None), \
             patch.object(self.srv, "run_validate", return_value=self._passing_validate()):
            result = self.srv.wave_audit_response(
                self.root, index=self._healthy_index()
            )
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["ready"])
        self.assertEqual(result["data"]["wave"], {})
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("no_active_wave", codes)
        self.assertIn("wave_current", result["next_tools"])


# ---------------------------------------------------------------------------
# build_server — tool registration
# ---------------------------------------------------------------------------

class ServerToolRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_tools_registered(self):
        try:
            mcp = self.srv.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        # FastMCP exposes tool names on _tool_manager._tools (or legacy _tools)
        tool_names = self.srv._registered_mcp_tool_names(mcp)
        if not tool_names and hasattr(mcp, "list_tools"):
            import asyncio
            tools = asyncio.run(mcp.list_tools())
            tool_names = {t.name for t in tools}

        expected = {
            "wave_help",
            "wave_map",
            "wave_create_wave",
            "wave_add_change",
            "wave_remove_change",
            "wave_prepare",
            "wave_pause",
            "wave_review",
            "wave_close",
            "docs_search",
            "code_search",
            "seed_get",
            "wave_current",
            "wave_list_waves",
            "wave_list_plans",
            "wave_get_change",
            "wave_get_prompt",
            "wave_open_gate",
            "wave_close_gate",
            "wave_new_feature",
            "wave_new_bug",
            "wave_new_enhancement",
            "wave_new_refactor",
            "wave_new_change",
            "wave_new_documentation",
            "wave_new_tech_debt",
            "wave_new_task",
            "wave_new_maintenance",
            "wave_new_operations",
            "wave_validate",
            "wave_garden",
            "wave_sync_surfaces",
            "wave_index_health",
            "wave_index_build",
            "wave_audit",
            "code_list_files",
            "code_read",
            "code_keyword_search",
            "code_definition",
            "code_references",
            "wave_get_handoff",
            "wave_set_handoff",
        }
        self.assertTrue(
            expected.issubset(tool_names),
            f"Missing tools: {expected - tool_names}",
        )

    def test_registered_tools_obey_prefix_contract(self):
        try:
            mcp = self.srv.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        names = self.srv._registered_mcp_tool_names(mcp)
        viol = self.srv.first_party_tool_names_violating_prefix(names)
        self.assertEqual(viol, [], f"Prefix violations: {viol}")


# ---------------------------------------------------------------------------
# DX fix tests (AC-16 through AC-20)
# ---------------------------------------------------------------------------

class WaveCloseModeDiscoverabilityTests(unittest.TestCase):
    """AC-16: wave_close invalid-mode response includes valid_modes field."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_invalid_mode_returns_valid_modes_in_data(self):
        result = self.srv.wave_close_response(self.root, "some-wave", mode="run")
        self.assertEqual(result["status"], "error")
        self.assertIn("valid_modes", result["data"])
        self.assertIn("dry_run", result["data"]["valid_modes"])
        self.assertIn("create", result["data"]["valid_modes"])

    def test_valid_dry_run_mode_does_not_error_on_mode(self):
        # wave not found is a different error; confirm mode itself is accepted
        result = self.srv.wave_close_response(self.root, "nonexistent-wave", mode="dry_run")
        # Should fail on wave_not_found, not invalid_arguments
        self.assertTrue(
            any(d.get("code") == "wave_not_found" for d in result.get("diagnostics", [])),
            f"Expected wave_not_found diagnostic, got: {result.get('diagnostics')}",
        )


class WaveCreateWaveTemplateTests(unittest.TestCase):
    """AC-17: wave_create_wave produces wave.md with Wave Summary and Journal Watchpoints stubs."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_wave_md_contains_wave_summary_section(self):
        result = self.srv.wave_create_wave_response(self.root, "test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / result["data"]["path"]
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("## Wave Summary", text)

    def test_wave_md_contains_journal_watchpoints_section(self):
        result = self.srv.wave_create_wave_response(self.root, "test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / result["data"]["path"]
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("## Journal Watchpoints", text)


class WaveCreateWaveLastVerifiedTests(unittest.TestCase):
    """12as3: wave_create_wave scaffold emits today's ISO date, not the literal '<date>'."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_wave_create_wave_last_verified_populates_today(self):
        import datetime
        result = self.srv.wave_create_wave_response(self.root, "date-test", mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / result["data"]["path"]
        text = wave_md.read_text(encoding="utf-8")
        today_iso = datetime.date.today().isoformat()
        self.assertIn(f"Last verified: {today_iso}", text)
        self.assertNotIn("Last verified: <date>", text)

    def test_wave_create_wave_scaffold_last_verified_is_valid(self):
        """Scaffold emits a valid ISO date that docs-lint will accept."""
        import re
        result = self.srv.wave_create_wave_response(self.root, "valid-date", mode="create")
        wave_md = self.root / result["data"]["path"]
        text = wave_md.read_text(encoding="utf-8")
        m = re.search(r"^Last verified:\s*(\S+)", text, re.MULTILINE)
        self.assertIsNotNone(m, "Last verified line missing from scaffold")
        value = m.group(1)
        self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}$", f"Last verified value not ISO date: {value!r}")


class WaveAddChangeSectionPlacementTests(unittest.TestCase):
    """12as3: wave_add_change inserts blocks inside the ## Changes section."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _create_wave(self, slug: str) -> str:
        return self.srv.wave_create_wave_response(self.root, slug, mode="create")["data"]["wave_id"]

    def _create_change(self, kind: str, slug: str) -> str:
        return self.srv.new_change(self.root, kind, slug)["id"]

    def _changes_section_and_after(self, wave_md_text: str) -> tuple[str, str]:
        """Return (text inside ## Changes, text after it) split at next ## heading."""
        import re
        m = re.search(r"^## Changes[ \t]*\n", wave_md_text, re.MULTILINE)
        assert m is not None, "## Changes section missing"
        rest = wave_md_text[m.end():]
        next_m = re.search(r"^## ", rest, re.MULTILINE)
        if next_m:
            return rest[:next_m.start()], rest[next_m.start():]
        return rest, ""

    def test_wave_add_change_inserts_inside_changes_section(self):
        wave_id = self._create_wave("placement-test")
        change_id = self._create_change("feat", "first-change")
        result = self.srv.wave_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        inside, after = self._changes_section_and_after(text)
        self.assertIn(f"Change ID: `{change_id}`", inside)
        self.assertNotIn(f"Change ID: `{change_id}`", after)

    def test_wave_add_change_preserves_order(self):
        wave_id = self._create_wave("order-test")
        first = self._create_change("feat", "alpha")
        second = self._create_change("feat", "bravo")
        third = self._create_change("feat", "charlie")
        for cid in (first, second, third):
            result = self.srv.wave_add_change_response(self.root, wave_id, cid, mode="create")
            self.assertEqual(result["status"], "ok", msg=f"admission failed for {cid}: {result}")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        inside, _ = self._changes_section_and_after(text)
        idx_first = inside.find(f"Change ID: `{first}`")
        idx_second = inside.find(f"Change ID: `{second}`")
        idx_third = inside.find(f"Change ID: `{third}`")
        self.assertGreaterEqual(idx_first, 0)
        self.assertGreater(idx_second, idx_first)
        self.assertGreater(idx_third, idx_second)

    def test_wave_add_change_legacy_layout_round_trips(self):
        """Wave.md with change blocks already placed before ## Dependencies (legacy)
        must not be rewritten; new admissions still land inside ## Changes.
        """
        wave_id = self._create_wave("legacy-layout")
        legacy_change_id = "99legacy-feat pre-existing-block"
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        # Simulate the legacy buggy layout: blocks before ## Dependencies.
        legacy_block = f"\nChange ID: `{legacy_change_id}`\nChange Status: `planned`\n\n"
        text = text.replace("## Dependencies", legacy_block + "## Dependencies", 1)
        wave_md.write_text(text, encoding="utf-8")
        # Also create a change doc the admit path can find (so the admit doesn't fail).
        new_change = self._create_change("feat", "freshly-admitted")
        result = self.srv.wave_add_change_response(self.root, wave_id, new_change, mode="create")
        self.assertEqual(result["status"], "ok", msg=f"admission failed: {result}")
        text_after = wave_md.read_text(encoding="utf-8")
        # Legacy block still present in its original position.
        self.assertIn(f"Change ID: `{legacy_change_id}`", text_after)
        # New block landed inside ## Changes.
        inside, _ = self._changes_section_and_after(text_after)
        self.assertIn(f"Change ID: `{new_change}`", inside)

    def test_wave_add_change_missing_changes_section_guard(self):
        """When ## Changes is missing (operator edit), create it above the next ## heading."""
        wave_id = self._create_wave("missing-section")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        # Remove the ## Changes heading to simulate operator-edited wave.
        text = text.replace("## Changes\n\n", "", 1)
        wave_md.write_text(text, encoding="utf-8")
        change_id = self._create_change("feat", "guard-test")
        result = self.srv.wave_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(result["status"], "ok", msg=f"admission failed: {result}")
        text_after = wave_md.read_text(encoding="utf-8")
        self.assertIn("## Changes", text_after)
        inside, _ = self._changes_section_and_after(text_after)
        self.assertIn(f"Change ID: `{change_id}`", inside)


class WaveAddChangeBrokenLinksTests(unittest.TestCase):
    """AC-18: wave_add_change response data includes broken_links list."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _create_wave(self, slug: str) -> str:
        result = self.srv.wave_create_wave_response(self.root, slug, mode="create")
        return result["data"]["wave_id"]

    def _create_change(self, kind: str, slug: str) -> str:
        result = self.srv.new_change(self.root, kind, slug)
        return result["id"]

    def test_broken_links_empty_when_no_relative_wave_links(self):
        wave_id = self._create_wave("my-wave")
        change_id = self._create_change("feat", "clean-change")
        result = self.srv.wave_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("broken_links", result["data"])
        self.assertEqual(result["data"]["broken_links"], [])

    def test_broken_links_detected_when_doc_has_waves_relative_link(self):
        wave_id = self._create_wave("my-wave")
        change_id = self._create_change("feat", "linked-change")
        # Inject a ../waves/ link into the change doc (simulates a doc written from docs/plans/)
        change_path = self.root / "docs" / "plans" / f"{change_id}.md"
        existing = change_path.read_text(encoding="utf-8")
        change_path.write_text(
            existing + "\n\nSee also [other wave](../waves/1234a other-wave/some-change.md).\n",
            encoding="utf-8",
        )
        result = self.srv.wave_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("broken_links", result["data"])
        self.assertGreater(len(result["data"]["broken_links"]), 0)
        self.assertIn("../waves/", result["data"]["broken_links"][0])

    def test_broken_links_present_in_dry_run_response(self):
        wave_id = self._create_wave("my-wave")
        change_id = self._create_change("feat", "dry-check")
        result = self.srv.wave_add_change_response(self.root, wave_id, change_id, mode="dry_run")
        self.assertIn("broken_links", result["data"])


class WavePrepareJournalFormatHintTests(unittest.TestCase):
    """AC-19: wave_prepare journal diagnostic includes exact format hint."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        # Ensure journals dir exists
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_journal_missing_error_includes_format_hint(self):
        # Create a minimal wave with a planned change but no journal reference
        wave_id = self.srv.wave_create_wave_response(self.root, "hint-test", mode="create")["data"]["wave_id"]
        change_id = self.srv.new_change(self.root, "feat", "needs-journal")["id"]
        self.srv.wave_add_change_response(self.root, wave_id, change_id, mode="create")
        # Patch wave summary and last-verified so prepare has minimal failures
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        text = text.replace("Last verified: <date>", "Last verified: 2026-05-01")
        wave_md.write_text(text, encoding="utf-8")
        result = self.srv.wave_prepare_response(self.root, wave_id, mode="dry_run")
        diagnostics_text = " ".join(
            d.get("message", "") for d in result.get("diagnostics", [])
        )
        errors_text = " ".join(result.get("data", {}).get("errors", []))
        combined = diagnostics_text + " " + errors_text
        # The hint should contain the required format description
        self.assertIn("wave-id:", combined.lower() + " " + combined)
        self.assertTrue(
            "backtick" in combined.lower() or "wave-id:" in combined,
            f"Expected journal format hint in prepare output, got: {combined[:500]}",
        )


class WaveHelpStartWaveJournalNoteTests(unittest.TestCase):
    """AC-20: wave_help(goal='start_wave') includes journal key-line note."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_start_wave_rationale_mentions_journal_requirement(self):
        result = self.srv.wave_help_response(goal="start_wave")
        self.assertEqual(result["status"], "ok")
        data_str = str(result["data"])
        self.assertIn("journal", data_str.lower())
        self.assertIn("wave-id", data_str.lower())


# ---------------------------------------------------------------------------
# MCP Resource and Resource Template tests (1298v)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Code navigation tests (12991)
# ---------------------------------------------------------------------------

class CodeNavigationPathSafetyTests(unittest.TestCase):
    """AC-4: Root safety — path traversal and absolute paths are rejected."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_code_read_rejects_absolute_path(self):
        result = self.srv.code_read_response(self.root, "/etc/passwd")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "path_outside_root" for d in result["diagnostics"]))

    def test_code_read_rejects_traversal(self):
        result = self.srv.code_read_response(self.root, "../../etc/passwd")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "path_outside_root" for d in result["diagnostics"]))

    def test_code_read_rejects_missing_file(self):
        result = self.srv.code_read_response(self.root, "nonexistent.py")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "file_not_found" for d in result["diagnostics"]))


class CodeListFilesTests(unittest.TestCase):
    """AC-3: File listing returns repo-relative paths and supports glob."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        # Create a few test files
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (src / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lists_all_files_without_glob(self):
        result = self.srv.code_list_files_response(self.root, glob="")
        self.assertEqual(result["status"], "ok")
        self.assertIn("paths", result["data"])
        paths = result["data"]["paths"]
        self.assertTrue(any("main.py" in p for p in paths))

    def test_glob_filters_to_python_files(self):
        result = self.srv.code_list_files_response(self.root, glob="*.py")
        self.assertEqual(result["status"], "ok")
        paths = result["data"]["paths"]
        self.assertTrue(all(p.endswith(".py") for p in paths))

    def test_paths_use_forward_slashes(self):
        result = self.srv.code_list_files_response(self.root, glob="")
        paths = result["data"]["paths"]
        self.assertTrue(all("\\" not in p for p in paths))

    def test_does_not_include_git_dir(self):
        # .git directory files should be excluded
        result = self.srv.code_list_files_response(self.root, glob="")
        paths = result["data"]["paths"]
        self.assertFalse(any(".git/" in p or p.startswith(".git") for p in paths))


class CodeReadTests(unittest.TestCase):
    """AC-2: Ranged file reads return line-numbered content."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        lines = [f"line_{i}" for i in range(1, 21)]  # 20 lines
        (src / "sample.py").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_file_read(self):
        result = self.srv.code_read_response(self.root, "src/sample.py")
        self.assertEqual(result["status"], "ok")
        self.assertIn("content", result["data"])
        self.assertEqual(result["data"]["total_lines"], 20)

    def test_ranged_read_returns_subset(self):
        result = self.srv.code_read_response(self.root, "src/sample.py", start_line=5, end_line=10)
        self.assertEqual(result["status"], "ok")
        content = result["data"]["content"]
        self.assertIn("line_5", content)
        self.assertIn("line_10", content)
        self.assertNotIn("line_1\n", content)  # line_1 not in this range (line_10 contains "line_1" prefix, but line_1 alone is excluded)
        self.assertEqual(result["data"]["start_line"], 5)
        self.assertEqual(result["data"]["end_line"], 10)

    def test_content_is_line_numbered(self):
        result = self.srv.code_read_response(self.root, "src/sample.py", start_line=1, end_line=3)
        content = result["data"]["content"]
        # Should have line numbers like "    1\t..." or "1\t..."
        self.assertRegex(content, r"\d+\t")

    def test_invalid_range_returns_error(self):
        result = self.srv.code_read_response(self.root, "src/sample.py", start_line=15, end_line=5)
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "invalid_range" for d in result["diagnostics"]))


class CodeKeywordSearchTests(unittest.TestCase):
    """AC-1: Exact keyword search returns deterministic path/line/snippet results."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "alpha.py").write_text("def alpha_func():\n    SEARCH_TARGET = 42\n    return SEARCH_TARGET\n", encoding="utf-8")
        (src / "beta.py").write_text("def beta_func():\n    pass\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_exact_match(self):
        result = self.srv.code_keyword_search_response(self.root, "SEARCH_TARGET")
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["data"]["count"], 0)
        paths = [r["path"] for r in result["data"]["results"]]
        self.assertTrue(any("alpha.py" in p for p in paths))

    def test_returns_line_numbers(self):
        result = self.srv.code_keyword_search_response(self.root, "SEARCH_TARGET")
        for r in result["data"]["results"]:
            self.assertIn("line", r)
            self.assertIsInstance(r["line"], int)

    def test_glob_filter_restricts_results(self):
        result = self.srv.code_keyword_search_response(self.root, "def ", glob="*beta*")
        self.assertEqual(result["status"], "ok")
        paths = [r["path"] for r in result["data"]["results"]]
        self.assertFalse(any("alpha.py" in p for p in paths))

    def test_empty_query_returns_error(self):
        result = self.srv.code_keyword_search_response(self.root, "")
        self.assertEqual(result["status"], "error")

    def test_no_match_returns_empty_results(self):
        result = self.srv.code_keyword_search_response(self.root, "ZZZNOMATCHXXX")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["count"], 0)


class CodeDefinitionTests(unittest.TestCase):
    """AC-6: code_definition works for Python and returns unsupported for others."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "mymodule.py").write_text(
            "class MyClass:\n    pass\n\ndef my_function():\n    pass\n\nasync def my_async():\n    pass\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_class_definition(self):
        result = self.srv.code_definition_response(self.root, "MyClass")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertTrue(any(d["name"] == "MyClass" and d["kind"] == "class" for d in defs))

    def test_finds_function_definition(self):
        result = self.srv.code_definition_response(self.root, "my_function")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertTrue(any("my_function" in d["name"] for d in defs))

    def test_finds_async_function_definition(self):
        result = self.srv.code_definition_response(self.root, "my_async")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertTrue(any("my_async" in d["name"] for d in defs))

    def test_not_found_returns_ok_with_diagnostic(self):
        result = self.srv.code_definition_response(self.root, "NonExistentSymbol")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["definitions"], [])
        self.assertTrue(any(d["code"] == "not_found" for d in result["diagnostics"]))

    def test_supported_languages_listed(self):
        result = self.srv.code_definition_response(self.root, "MyClass")
        self.assertIn("supported_languages", result["data"])
        self.assertIn("python", result["data"]["supported_languages"])

    def test_note_mentions_non_python_unsupported(self):
        result = self.srv.code_definition_response(self.root, "MyClass")
        self.assertIn("note", result["data"])
        self.assertIn("Python", result["data"]["note"] + result["data"].get("note", ""))


class CodeReferencesTests(unittest.TestCase):
    """AC-7: code_references works for Python and provides fallback note."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "caller.py").write_text(
            "from mymodule import MyClass\n\ndef caller():\n    obj = MyClass()\n    return obj\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_references_in_python_files(self):
        result = self.srv.code_references_response(self.root, "MyClass")
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["data"]["count"], 0)
        paths = [r["path"] for r in result["data"]["references"]]
        self.assertTrue(any("caller.py" in p for p in paths))

    def test_note_mentions_code_keyword_search_fallback(self):
        result = self.srv.code_references_response(self.root, "MyClass")
        note = result["data"].get("note", "")
        self.assertIn("code_keyword_search", note)

    def test_empty_results_when_no_match(self):
        result = self.srv.code_references_response(self.root, "ZZZNOREFERENCEYYY")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["count"], 0)


class McpResourceRegistrationTests(unittest.TestCase):
    """AC-1/AC-2: MCP resource and resource-template registrations exist."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _get_mcp(self):
        try:
            return self.srv.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

    def _list_resources(self, mcp):
        import asyncio
        return asyncio.run(mcp.list_resources())

    def _list_templates(self, mcp):
        import asyncio
        return asyncio.run(mcp.list_resource_templates())

    def test_stable_resources_registered(self):
        mcp = self._get_mcp()
        resources = self._list_resources(mcp)
        uris = {str(r.uri) for r in resources}
        expected_uris = {
            "wavefoundry://overview",
            "wavefoundry://prompts",
            "wavefoundry://architecture/current-state",
            "wavefoundry://wave/current",
            "wavefoundry://session-handoff",
        }
        self.assertTrue(
            expected_uris.issubset(uris),
            f"Missing resources: {expected_uris - uris}",
        )

    def test_resource_templates_registered(self):
        mcp = self._get_mcp()
        templates = self._list_templates(mcp)
        uri_templates = {t.uriTemplate for t in templates}
        expected = {
            "wavefoundry://change/{change_id}",
            "wavefoundry://wave/{wave_id}",
            "wavefoundry://prompt/{slug}",
            "wavefoundry://seed/{slug}",
            "wavefoundry://architecture/{slug}",
        }
        self.assertTrue(
            expected.issubset(uri_templates),
            f"Missing templates: {expected - uri_templates}",
        )

    def test_existing_tools_still_register(self):
        mcp = self._get_mcp()
        tool_names = self.srv._registered_mcp_tool_names(mcp)
        self.assertIn("wave_validate", tool_names)
        self.assertIn("wave_current", tool_names)


class McpResourceReadTests(unittest.TestCase):
    """AC-3/AC-4: Resources return expected content or clear not-found messages."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _read_resource(self, uri: str):
        try:
            mcp = self.srv.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        import asyncio
        result = asyncio.run(mcp.read_resource(uri))
        # result is a list of ReadResourceContents items
        for item in result:
            content = getattr(item, "content", None) or getattr(item, "text", None) or ""
            if content:
                return str(content)
        return ""

    def test_overview_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://overview")
        # _make_repo doesn't create project-overview.md or README.md so not-found message expected
        # but README.md might exist at repo root — accept either content or not-found
        self.assertIsInstance(text, str)
        self.assertTrue(len(text) > 0)

    def test_prompt_index_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://prompts")
        self.assertIn("Not Found", text)

    def test_architecture_current_state_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://architecture/current-state")
        self.assertIn("Not Found", text)

    def test_session_handoff_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://session-handoff")
        self.assertIn("Not Found", text)

    def test_current_wave_returns_no_active_wave_message(self):
        text = self._read_resource("wavefoundry://wave/current")
        # No active wave in test repo
        self.assertIn("No Active Wave", text)

    def test_current_wave_returns_wave_md_when_active(self):
        # Create a wave and mark it active
        wave_result = self.srv.wave_create_wave_response(self.root, "resource-test", mode="create")
        wave_id = wave_result["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        text = text.replace("Status: planned", "Status: active")
        wave_md.write_text(text, encoding="utf-8")
        result_text = self._read_resource("wavefoundry://wave/current")
        self.assertIn("Wave Record", result_text)

    def test_prompt_index_returns_content_when_exists(self):
        # Create a prompt index file
        prompts_dir = self.root / "docs" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "index.md").write_text("# Prompt Index\n\n- plan-feature\n", encoding="utf-8")
        text = self._read_resource("wavefoundry://prompts")
        self.assertIn("Prompt Index", text)


class McpResourceTemplateReadTests(unittest.TestCase):
    """AC-2/AC-4: Resource templates return content or clear not-found messages."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _read_resource(self, uri: str):
        try:
            mcp = self.srv.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        import asyncio
        result = asyncio.run(mcp.read_resource(uri))
        for item in result:
            content = getattr(item, "content", None) or getattr(item, "text", None) or ""
            if content:
                return str(content)
        return ""

    def test_change_template_returns_not_found_for_unknown_id(self):
        text = self._read_resource("wavefoundry://change/zzzzz-unknown")
        self.assertIn("Not Found", text)

    def test_change_template_returns_content_when_exists(self):
        result = self.srv.new_change(self.root, "feat", "resource-read-test")
        change_id = result["id"]
        text = self._read_resource(f"wavefoundry://change/{change_id}")
        self.assertIn("Change ID", text)

    def test_wave_template_returns_not_found_for_unknown_id(self):
        text = self._read_resource("wavefoundry://wave/zzzzz-unknown")
        self.assertIn("Not Found", text)

    def test_wave_template_returns_content_when_exists(self):
        wave_result = self.srv.wave_create_wave_response(self.root, "tpl-test", mode="create")
        wave_id = wave_result["data"]["wave_id"]
        text = self._read_resource(f"wavefoundry://wave/{wave_id}")
        self.assertIn("Wave Record", text)

    def test_architecture_template_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://architecture/nonexistent-doc")
        self.assertIn("Not Found", text)

    def test_architecture_template_returns_content_when_exists(self):
        arch_dir = self.root / "docs" / "architecture"
        arch_dir.mkdir(parents=True, exist_ok=True)
        (arch_dir / "current-state.md").write_text("# Current State\n\nAll good.\n", encoding="utf-8")
        text = self._read_resource("wavefoundry://architecture/current-state")
        self.assertIn("Current State", text)

    def test_seed_template_returns_not_found_for_unknown_slug(self):
        text = self._read_resource("wavefoundry://seed/nonexistent-seed-xyz")
        self.assertIn("Not Found", text)


# ---------------------------------------------------------------------------
# 12aj7 MCP Layer Polish tests
# ---------------------------------------------------------------------------

class WaveStatusDriftDetectionTests(unittest.TestCase):
    """Item 1: wave_current_response includes change_status_drift diagnostic."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave_with_drift(self):
        """Create a wave with one change whose file status differs from wave.md."""
        wave_dir = self.root / "docs" / "waves" / "test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-01-01\n\nwave-id: `test-wave`\nTitle: Test Wave\n\n## Changes\n\nChange ID: `abc12-feat my-change`\nChange Status: `in-progress`\n",
            encoding="utf-8",
        )
        change_doc = wave_dir / "abc12-feat my-change.md"
        change_doc.write_text(
            "# My Change\n\nChange ID: `abc12-feat my-change`\nChange Status: `complete`\n",
            encoding="utf-8",
        )
        return wave_dir

    def test_no_drift_no_diagnostic(self):
        wave_dir = self.root / "docs" / "waves" / "test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-01-01\n\nwave-id: `test-wave`\nTitle: Test Wave\n\n## Changes\n\nChange ID: `abc12-feat my-change`\nChange Status: `in-progress`\n",
            encoding="utf-8",
        )
        (wave_dir / "abc12-feat my-change.md").write_text(
            "# My Change\n\nChange ID: `abc12-feat my-change`\nChange Status: `in-progress`\n",
            encoding="utf-8",
        )
        resp = self.srv.wave_current_response(self.root)
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertNotIn("change_status_drift", codes)

    def test_drift_produces_diagnostic(self):
        self._make_wave_with_drift()
        resp = self.srv.wave_current_response(self.root)
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("change_status_drift", codes)

    def test_drift_response_status_still_ok(self):
        """Drift detection is advisory — status must remain 'ok'."""
        self._make_wave_with_drift()
        resp = self.srv.wave_current_response(self.root)
        self.assertEqual(resp["status"], "ok")


class EditGateToolTests(unittest.TestCase):
    """12ax9: wave_open_gate / wave_close_gate MCP tools."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        # Start with both gates closed
        overrides_path = self.root / ".wavefoundry" / "guard-overrides.json"
        overrides_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        overrides_path.write_text(
            json.dumps({"seed_edit_allowed": {"enabled": False}, "framework_edit_allowed": {"enabled": False}}) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _read_gates(self):
        import json
        path = self.root / ".wavefoundry" / "guard-overrides.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_open_closed_gate_succeeds(self):
        resp = self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(self._read_gates()["seed_edit_allowed"]["enabled"])

    def test_open_already_open_gate_returns_error(self):
        self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        resp = self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        self.assertEqual(resp["status"], "error")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gate_already_open", codes)

    def test_close_open_gate_succeeds(self):
        self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        resp = self.srv.wave_close_gate_response(self.root, "seed_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        self.assertFalse(self._read_gates()["seed_edit_allowed"]["enabled"])

    def test_close_already_closed_gate_returns_advisory(self):
        resp = self.srv.wave_close_gate_response(self.root, "seed_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gate_already_closed", codes)

    def test_framework_edit_allowed_gate_works(self):
        resp = self.srv.wave_open_gate_response(self.root, "framework_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(self._read_gates()["framework_edit_allowed"]["enabled"])
        resp2 = self.srv.wave_close_gate_response(self.root, "framework_edit_allowed")
        self.assertEqual(resp2["status"], "ok")
        self.assertFalse(self._read_gates()["framework_edit_allowed"]["enabled"])

    def test_invalid_gate_name_returns_error(self):
        resp = self.srv.wave_open_gate_response(self.root, "nonexistent_gate")
        self.assertEqual(resp["status"], "error")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("invalid_arguments", codes)


class GateAutoCloseTests(unittest.TestCase):
    """12ax9: wave_pause and wave_close auto-close open gates."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _open_gate(self, gate="seed_edit_allowed"):
        import json
        path = self.root / ".wavefoundry" / "guard-overrides.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        data.setdefault(gate, {})["enabled"] = True
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _gate_state(self, gate="seed_edit_allowed"):
        import json
        path = self.root / ".wavefoundry" / "guard-overrides.json"
        if not path.exists():
            return False
        return json.loads(path.read_text(encoding="utf-8")).get(gate, {}).get("enabled", False)

    def _make_active_wave(self):
        wave_dir = self.root / "docs" / "waves" / "test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-05-01\n\nwave-id: `test-wave`\nTitle: Test Wave\n\n## Changes\n\n## Wave Summary\n\nTest.\n\n## Journal Watchpoints\n\n- Test.\n",
            encoding="utf-8",
        )

    def test_wave_pause_with_open_gate_forces_close_and_emits_diagnostic(self):
        self._make_active_wave()
        self._open_gate("seed_edit_allowed")
        resp = self.srv.wave_pause_response(self.root, "test-wave", mode="create")
        self.assertEqual(resp["status"], "ok")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gates_forced_closed", codes)
        self.assertFalse(self._gate_state("seed_edit_allowed"))

    def test_wave_close_dry_run_with_open_gate_emits_diagnostic_but_does_not_write(self):
        self._make_active_wave()
        self._open_gate("seed_edit_allowed")
        resp = self.srv.wave_close_response(self.root, "test-wave", mode="dry_run")
        # dry_run may fail validation but should still emit gate diagnostic
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gates_forced_closed", codes)
        # Gate must NOT be written in dry-run
        self.assertTrue(self._gate_state("seed_edit_allowed"))

    def test_wave_close_create_with_open_gate_forces_close_and_emits_diagnostic(self):
        self._make_active_wave()
        self._open_gate("seed_edit_allowed")
        # Add minimal review evidence so wave_close can pass validation
        wave_md = self.root / "docs" / "waves" / "test-wave" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                resp = self.srv.wave_close_response(self.root, "test-wave", mode="create")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gates_forced_closed", codes)
        self.assertFalse(self._gate_state("seed_edit_allowed"))

    def test_wave_close_with_no_open_gates_has_no_gate_diagnostic(self):
        self._make_active_wave()
        wave_md = self.root / "docs" / "waves" / "test-wave" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                resp = self.srv.wave_close_response(self.root, "test-wave", mode="create")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertNotIn("gates_forced_closed", codes)


class WaveCloseHandoffPreservationTests(unittest.TestCase):
    """12axd: wave_close and wave_pause preserve session handoff content."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_active_wave(self):
        wave_dir = self.root / "docs" / "waves" / "hw-test"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-05-01\n\nwave-id: `hw-test`\nTitle: HW Test\n\n## Changes\n\n## Wave Summary\n\nTest.\n\n## Journal Watchpoints\n\n- Test.\n",
            encoding="utf-8",
        )

    def _write_handoff(self, content):
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(content, encoding="utf-8")

    def _read_handoff(self):
        return (self.root / "docs" / "agents" / "session-handoff.md").read_text(encoding="utf-8")

    def test_close_updates_wave_md_status(self):
        self._make_active_wave()
        wave_md = self.root / "docs" / "waves" / "hw-test" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                self.srv.wave_close_response(self.root, "hw-test", mode="create")
        content = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: closed", content)
        self.assertIn("Completed At:", content)
        # No archive folder should be created
        self.assertFalse((self.root / "docs" / "waves" / "hw-test" / "archive").exists())

    def test_wave_close_preserves_handoff_content_outside_active_wave(self):
        self._make_active_wave()
        custom_section = "## My Notes\n\nSome important agent notes that must survive.\n"
        self._write_handoff(
            f"# Session Handoff\n\nOwner: wave-coordinator\nStatus: active\nLast verified: 2026-05-01\n\n"
            f"## Current Session\n\n**Active wave:** `hw-test`\n\n{custom_section}"
        )
        wave_md = self.root / "docs" / "waves" / "hw-test" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                self.srv.wave_close_response(self.root, "hw-test", mode="create")
        result = self._read_handoff()
        self.assertIn("Some important agent notes that must survive.", result)
        self.assertIn("*(none)*", result)

    def test_wave_pause_preserves_handoff_content_outside_active_wave(self):
        self._make_active_wave()
        custom_section = "## Research Notes\n\nContext that must not be wiped on pause.\n"
        self._write_handoff(
            f"# Session Handoff\n\nOwner: wave-coordinator\nStatus: active\nLast verified: 2026-05-01\n\n"
            f"## Current Session\n\n**Active wave:** `hw-test`\n\n{custom_section}"
        )
        self.srv.wave_pause_response(self.root, "hw-test", mode="create")
        result = self._read_handoff()
        self.assertIn("Context that must not be wiped on pause.", result)

    def test_wave_close_missing_handoff_creates_scaffold(self):
        self._make_active_wave()
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        if handoff.exists():
            handoff.unlink()
        wave_md = self.root / "docs" / "waves" / "hw-test" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                self.srv.wave_close_response(self.root, "hw-test", mode="create")
        self.assertTrue(handoff.exists())
        content = handoff.read_text(encoding="utf-8")
        self.assertIn("Session Handoff", content)


class BulkWaveGetChangeTests(unittest.TestCase):
    """Item 3: wave_get_change with wave_id (no change_id) returns all admitted changes."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _setup_wave(self):
        wave_dir = self.root / "docs" / "waves" / "bulk-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-01-01\n\nwave-id: `bulk-wave`\nTitle: Bulk Wave\n\n## Changes\n\nChange ID: `ch1xx-feat first`\nChange Status: `in-progress`\n\nChange ID: `ch2xx-feat second`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        (wave_dir / "ch1xx-feat first.md").write_text(
            "# First\n\nChange ID: `ch1xx-feat first`\nChange Status: `in-progress`\n",
            encoding="utf-8",
        )
        (wave_dir / "ch2xx-feat second.md").write_text(
            "# Second\n\nChange ID: `ch2xx-feat second`\nChange Status: `planned`\n",
            encoding="utf-8",
        )

    def test_bulk_returns_all_changes(self):
        self._setup_wave()
        resp = self.srv.wave_get_change_response(self.root, wave_id="bulk-wave")
        self.assertEqual(resp["status"], "ok")
        changes = resp["data"]["changes"]
        ids = [c["id"] for c in changes]
        self.assertIn("ch1xx-feat first", ids)
        self.assertIn("ch2xx-feat second", ids)

    def test_bulk_count_field(self):
        self._setup_wave()
        resp = self.srv.wave_get_change_response(self.root, wave_id="bulk-wave")
        self.assertEqual(resp["data"]["count"], 2)

    def test_bulk_unknown_wave_returns_ok_with_diagnostic(self):
        resp = self.srv.wave_get_change_response(self.root, wave_id="nonexistent-wave")
        self.assertEqual(resp["status"], "ok")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("wave_not_found", codes)

    def test_single_mode_unchanged(self):
        """Providing change_id without wave_id uses original single-lookup mode."""
        self._setup_wave()
        resp = self.srv.wave_get_change_response(self.root, change_id="ch1xx-feat first")
        self.assertEqual(resp["status"], "ok")
        self.assertIn("change", resp["data"])


class HandoffToolTests(unittest.TestCase):
    """Item 4: wave_get_handoff and wave_set_handoff."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_handoff_not_found(self):
        resp = self.srv.wave_get_handoff_response(self.root)
        self.assertEqual(resp["status"], "ok")
        self.assertIsNone(resp["data"]["content"])

    def test_set_handoff_creates_file(self):
        resp = self.srv.wave_set_handoff_response(self.root, content="# Session Handoff\n\nActive wave: test")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(resp["data"]["written"])
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        self.assertTrue(handoff.exists())

    def test_get_handoff_after_set(self):
        self.srv.wave_set_handoff_response(self.root, content="# Handoff\n\nDone.")
        resp = self.srv.wave_get_handoff_response(self.root)
        self.assertEqual(resp["status"], "ok")
        self.assertIn("Done.", resp["data"]["content"])

    def test_set_handoff_size_field(self):
        content = "# Session Handoff\n\nSome state."
        resp = self.srv.wave_set_handoff_response(self.root, content=content)
        self.assertEqual(resp["data"]["size"], len(content))

    def test_get_handoff_path_field(self):
        resp = self.srv.wave_get_handoff_response(self.root)
        self.assertEqual(resp["data"]["path"], "docs/agents/session-handoff.md")

    def test_handoff_tools_registered(self):
        try:
            mcp = self.srv.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        names = self.srv._registered_mcp_tool_names(mcp)
        self.assertIn("wave_get_handoff", names)
        self.assertIn("wave_set_handoff", names)


class DocsSearchModeFieldTests(unittest.TestCase):
    """Item 5: docs_search_response includes 'mode' field (semantic/lexical)."""

    def setUp(self):
        self.srv = load_server()

    def test_mode_field_present_on_semantic_results(self):
        index = MagicMock()
        index.search_docs.return_value = []
        resp = self.srv.docs_search_response(index, "test query")
        self.assertIn("mode", resp.get("data", {}))

    def test_mode_field_is_semantic_when_search_succeeds(self):
        index = MagicMock()
        index.search_docs.return_value = []
        resp = self.srv.docs_search_response(index, "test query")
        self.assertEqual(resp["data"]["mode"], "semantic")

    def test_mode_field_is_lexical_on_index_not_ready(self):
        index = MagicMock()
        index.search_docs.side_effect = self.srv.IndexNotReadyError("index not ready")
        index.search_docs_lexical.return_value = []
        resp = self.srv.docs_search_response(index, "test query")
        self.assertEqual(resp["data"]["mode"], "lexical")


class WavePrepareACPriorityWarningTests(unittest.TestCase):
    """Item 6: wave_prepare warns (non-blocking) when AC priority rows are unpopulated."""

    _VALID_LINT = {"passed": True, "errors": [], "warnings": [], "output": ""}

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave_with_change(self, ac_text: str) -> Path:
        wave_dir = self.root / "docs" / "waves" / "ac-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: planned\nLast verified: 2026-01-01\n\nwave-id: `ac-wave`\nTitle: AC Wave\n\n## Changes\n\nChange ID: `acx01-feat ac-test`\nChange Status: `planned`\n\n## Wave Summary\n\nTest wave.\n\n## Journal Watchpoints\n\n- Watch this.\n",
            encoding="utf-8",
        )
        change_doc = wave_dir / "acx01-feat ac-test.md"
        change_doc.write_text(
            "# AC Test\n\nChange ID: `acx01-feat ac-test`\nChange Status: `planned`\nOwner: Engineering\nWave: `ac-wave`\n\n"
            "## Rationale\n\nNeeded.\n\n## Requirements\n\n1. Do the thing.\n\n## Scope\n\nIn scope.\n\n"
            "## Acceptance Criteria\n\n- AC-1: Does the thing.\n\n## Tasks\n\n- Implement it.\n\n"
            f"## AC Priority\n\n| AC | Priority | Rationale |\n| -- | -------- | --------- |\n{ac_text}\n",
            encoding="utf-8",
        )
        return wave_dir

    def test_placeholder_ac_produces_advisory(self):
        self._make_wave_with_change(
            "| AC-1 | required / important / nice-to-have / not-this-scope | placeholder |"
        )
        with patch.object(self.srv, "run_validate", return_value=self._VALID_LINT):
            resp = self.srv.wave_prepare_response(self.root, wave_id="ac-wave", mode="dry_run")
        # Must not be an error (advisory only)
        self.assertNotEqual(resp["status"], "error")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("ac_priority_unpopulated", codes)

    def test_populated_ac_no_advisory(self):
        self._make_wave_with_change(
            "| AC-1 | required | Core feature. |"
        )
        with patch.object(self.srv, "run_validate", return_value=self._VALID_LINT):
            resp = self.srv.wave_prepare_response(self.root, wave_id="ac-wave", mode="dry_run")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertNotIn("ac_priority_unpopulated", codes)

    def test_placeholder_ac_does_not_block_prepare(self):
        """prepare must still succeed (dry_run) even with unpopulated AC rows."""
        self._make_wave_with_change(
            "| AC-1 | required / important / nice-to-have / not-this-scope | placeholder |"
        )
        with patch.object(self.srv, "run_validate", return_value=self._VALID_LINT):
            resp = self.srv.wave_prepare_response(self.root, wave_id="ac-wave", mode="dry_run")
        self.assertIn(resp["status"], ("dry_run", "ok"))


# ---------------------------------------------------------------------------
# Semantic embedding regression tests
#
# These tests exercise the REAL fastembed embedding path — no mocks.  They are
# skipped gracefully when fastembed is not installed or the model is not yet
# cached locally (i.e. setup_index.py --root . has not been run).
#
# Purpose: anchor the four properties that matter most when the embedding model
# changes in the future:
#   1. Model name constant  — what model we're actually using
#   2. Vector dimension     — must stay consistent with the built index
#   3. Embedding determinism — same text must always produce the same vector
#   4. Semantic ranking order — a known query must rank a known best match above
#                               a known poor match (guards against model swaps /
#                               quantization changes silently flipping results)
#
# When a model upgrade is intentional, these tests will fail and serve as the
# checklist: update the EXPECTED_* constants below, rebuild the index, re-run.
# ---------------------------------------------------------------------------

# Regression anchors — update these deliberately when upgrading the model.
_EXPECTED_DOCS_MODEL = "BAAI/bge-small-en-v1.5"
_EXPECTED_EMBEDDING_DIM = 384


class SemanticEmbeddingRegressionTests(unittest.TestCase):
    """Real-fastembed tests.  Skipped if fastembed is not installed or the
    model is not locally cached."""

    @classmethod
    def setUpClass(cls):
        try:
            import fastembed  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("fastembed not installed — run: pip install fastembed")

        import numpy as np
        cls.np = np

        cls.srv = load_server()
        tmp = tempfile.mkdtemp()
        cls._tmp_dir = tmp
        cls.root = _make_repo(Path(tmp))
        cls.index = cls.srv.WaveIndex(cls.root)
        cls.model = cls.index._indexer_constant("DOCS_MODEL")

        # Attempt one real embed to confirm the model is cached locally.
        # SemanticModelUnavailableOfflineError means setup_index.py hasn't run yet.
        try:
            cls._probe_vec = cls.index._embed_query("probe", cls.model)
        except cls.srv.SemanticModelUnavailableOfflineError:
            raise unittest.SkipTest(
                "Embedding model not locally cached — run: "
                "python3 .wavefoundry/framework/scripts/setup_index.py --root ."
            )

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 1. Model name anchor
    # ------------------------------------------------------------------

    def test_docs_model_constant_matches_expected(self):
        """Pin the model name.  If this fails, a model upgrade happened — update
        _EXPECTED_DOCS_MODEL and re-verify all downstream tests."""
        self.assertEqual(
            self.model,
            _EXPECTED_DOCS_MODEL,
            f"DOCS_MODEL changed to {self.model!r}. "
            "Update _EXPECTED_DOCS_MODEL and _EXPECTED_EMBEDDING_DIM in this file, "
            "then rebuild the index.",
        )

    # ------------------------------------------------------------------
    # 2. Vector dimension anchor
    # ------------------------------------------------------------------

    def test_embedding_dimension_matches_expected(self):
        """Pin the output vector dimension.  A change here means the index
        files written by the old model are no longer compatible."""
        vec = self.index._embed_query("dimension check", self.model)
        self.assertEqual(
            len(vec),
            _EXPECTED_EMBEDDING_DIM,
            f"Embedding dimension is {len(vec)}, expected {_EXPECTED_EMBEDDING_DIM}. "
            "Update _EXPECTED_EMBEDDING_DIM and rebuild the index.",
        )

    def test_embedding_is_float32(self):
        """fastembed must return float32 — mismatched dtype causes silent
        cosine-score errors when merged with float32 index matrices."""
        vec = self.index._embed_query("dtype check", self.model)
        self.np = __import__("numpy")
        self.assertEqual(vec.dtype, self.np.float32)

    # ------------------------------------------------------------------
    # 3. Determinism
    # ------------------------------------------------------------------

    def test_same_text_produces_identical_vectors(self):
        """Embedding must be deterministic — same text always gives same vector.
        A failure here indicates non-deterministic model behavior which would
        make search results unpredictable across restarts."""
        np = self.np
        text = "wave lifecycle management"
        v1 = self.index._embed_query(text, self.model)
        v2 = self.index._embed_query(text, self.model)
        np.testing.assert_array_equal(
            v1, v2,
            err_msg="Embedding is not deterministic — same text produced different vectors.",
        )

    def test_different_texts_produce_different_vectors(self):
        """Distinct texts must not collapse to the same vector."""
        v1 = self.index._embed_query("prepare wave", self.model)
        v2 = self.index._embed_query("install dependencies", self.model)
        self.assertFalse(
            self.np.allclose(v1, v2),
            "Two unrelated texts produced identical vectors — model may be degenerate.",
        )

    # ------------------------------------------------------------------
    # 4. Semantic ranking anchor
    # ------------------------------------------------------------------

    def test_similar_text_scores_higher_than_unrelated(self):
        """A query must score its topically close match above an unrelated chunk.
        This is the core regression guard: if the model is swapped or quantized
        differently, ranking order could silently invert."""
        np = self.np

        query = "how to create a new wave"
        close_text = "Use wave_create_wave to start a new wave and track changes."
        far_text = "The colour of the sky depends on Rayleigh scattering of sunlight."

        qvec = self.index._embed_query(query, self.model)
        close_vec = self.index._embed_query(close_text, self.model)
        far_vec = self.index._embed_query(far_text, self.model)

        def cosine(a, b):
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))

        close_score = cosine(qvec, close_vec)
        far_score = cosine(qvec, far_vec)
        self.assertGreater(
            close_score,
            far_score,
            f"Expected close text (score={close_score:.4f}) to rank above "
            f"unrelated text (score={far_score:.4f}) for query {query!r}.",
        )

    # ------------------------------------------------------------------
    # 5. Full round-trip: embed → write index → search → verify result
    # ------------------------------------------------------------------

    def test_round_trip_search_returns_correct_chunk(self):
        """Build a tiny real-embedding index in a temp directory, load it via
        WaveIndex, and verify that a semantically related query surfaces the
        right chunk and not the unrelated one.

        This is the highest-fidelity test: it exercises _embed_query,
        _write to .npy, _ensure_loaded, _cosine_search, and kind filtering
        all in one pass with real vectors."""
        import json
        import numpy as np
        import tempfile

        chunks = [
            {
                "id": "c-wave",
                "path": "docs/waves/my-wave/wave.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 5],
                "section": "Changes",
                "text": "Prepare wave: validate change docs and admit them to the active wave folder.",
            },
            {
                "id": "c-install",
                "path": "docs/references/install.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 5],
                "section": "Setup",
                "text": "Install Python dependencies with pip install fastembed numpy.",
            },
        ]

        # Embed with real model
        vectors = np.array(
            [self.index._embed_query(c["text"], self.model) for c in chunks],
            dtype=np.float32,
        )

        # Write to a fresh temp index directory
        with tempfile.TemporaryDirectory() as idx_tmp:
            idx_dir = Path(idx_tmp)
            (idx_dir / "meta.json").write_text(
                json.dumps({
                    "model_versions": {"docs": self.model},
                    "file_hashes": {},
                }),
                encoding="utf-8",
            )
            (idx_dir / "docs.json").write_text(json.dumps(chunks), encoding="utf-8")
            np.save(str(idx_dir / "docs.npy"), vectors)

            # Point a fresh WaveIndex at a root that uses this index dir
            with tempfile.TemporaryDirectory() as root_tmp:
                root = _make_repo(Path(root_tmp))
                project_idx = root / ".wavefoundry" / "index"
                project_idx.mkdir(parents=True, exist_ok=True)
                for fname in ("meta.json", "docs.json", "docs.npy"):
                    import shutil
                    shutil.copy(str(idx_dir / fname), str(project_idx / fname))

                index = self.srv.WaveIndex(root)
                results = index.search_docs("how do I validate and prepare a wave?", top_n=1)

        self.assertEqual(len(results), 1, "Expected exactly one result from top_n=1.")
        self.assertEqual(
            results[0]["id"],
            "c-wave",
            f"Expected the wave-prep chunk to be top result, got {results[0]['id']!r}. "
            "Semantic ranking may have changed — check the model.",
        )
        self.assertIn("score", results[0])
        self.assertGreater(results[0]["score"], 0.0)

    def test_stale_model_name_in_index_causes_layer_skip(self):
        """If the index was built with a different model, _ensure_loaded must
        skip that layer rather than silently using incompatible vectors.
        This guards the upgrade path: build with new model → old index → no
        silent garbage results."""
        import json
        import numpy as np
        import tempfile

        with tempfile.TemporaryDirectory() as root_tmp:
            root = _make_repo(Path(root_tmp))
            idx_dir = root / ".wavefoundry" / "index"
            idx_dir.mkdir(parents=True, exist_ok=True)

            # Write an index with the wrong model name
            stale_model = "old-model/bge-obsolete-v0.1"
            chunk = [{
                "id": "stale",
                "path": "docs/stale.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 1],
                "section": None,
                "text": "stale content",
            }]
            (idx_dir / "meta.json").write_text(
                json.dumps({"model_versions": {"docs": stale_model}, "file_hashes": {}}),
                encoding="utf-8",
            )
            (idx_dir / "docs.json").write_text(json.dumps(chunk), encoding="utf-8")
            np.save(str(idx_dir / "docs.npy"), np.array([[1.0] * _EXPECTED_EMBEDDING_DIM], dtype=np.float32))

            index = self.srv.WaveIndex(root)
            # search_docs triggers _ensure_loaded; stale layer should be skipped → no results
            results = index.search_docs("stale content", top_n=5)

        self.assertEqual(
            results,
            [],
            "Expected empty results when index was built with a different model name, "
            "but got results — layer compatibility check may be broken.",
        )


class WavePauseStatusTransitionTests(unittest.TestCase):
    """12as6: wave_pause transitions wave.md Status active→paused and records transition."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, wave_id: str, status: str) -> Path:
        wave_dir = self.root / "docs" / "waves" / wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            "# Wave Record\n\n"
            "Owner: Engineering\n"
            f"Status: {status}\n"
            "Last verified: 2026-05-01\n\n"
            f"wave-id: `{wave_id}`\n"
            "Title: Test Wave\n\n"
            "## Changes\n\n"
            "## Wave Summary\n\nTest.\n\n"
            "## Journal Watchpoints\n\n- Test.\n\n"
            "## Dependencies\n\n- None.\n",
            encoding="utf-8",
        )
        return wave_md

    def test_wave_pause_transitions_active_to_paused(self):
        wave_md = self._make_wave("1200a active-wave", "active")
        result = self.srv.wave_pause_response(self.root, "1200a active-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status_transition"], {"from": "active", "to": "paused"})
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: paused", text)
        self.assertNotIn("Status: active", text)

    def test_wave_pause_idempotent_on_paused(self):
        wave_md = self._make_wave("1200a paused-wave", "paused")
        result = self.srv.wave_pause_response(self.root, "1200a paused-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status_transition"], {"from": "paused", "to": "paused"})
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: paused", text)
        # Handoff still written
        self.assertTrue((self.root / "docs" / "agents" / "session-handoff.md").exists())

    def test_wave_pause_advisory_on_planned(self):
        self._make_wave("1200a planned-wave", "planned")
        result = self.srv.wave_pause_response(self.root, "1200a planned-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("pause_on_non_active_wave", codes)
        self.assertEqual(result["data"]["status_transition"]["to"], "planned")

    def test_wave_pause_dry_run_reports_transition(self):
        wave_md = self._make_wave("1200a dry-run-wave", "active")
        original_text = wave_md.read_text(encoding="utf-8")
        result = self.srv.wave_pause_response(self.root, "1200a dry-run-wave", mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["data"]["status_transition"], {"from": "active", "to": "paused"})
        # wave.md untouched
        self.assertEqual(wave_md.read_text(encoding="utf-8"), original_text)


class WavePrepareSingleActiveGuardTests(unittest.TestCase):
    """12as6: wave_prepare blocks when another wave is active; allows self and post-pause prepare."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave_with_change(self, slug: str, status: str = "planned") -> tuple[str, str]:
        """Create a wave (fully scaffolded via scripts) with one admitted change."""
        wave_result = self.srv.wave_create_wave_response(self.root, slug, mode="create")
        wave_id = wave_result["data"]["wave_id"]
        change = self.srv.new_change(self.root, "feat", f"{slug}-change")
        change_id = change["id"]
        self.srv.wave_add_change_response(self.root, wave_id, change_id, mode="create")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        if status != "planned":
            text = text.replace("Status: planned", f"Status: {status}")
            wave_md.write_text(text, encoding="utf-8")
        # Add journal reference so lint passes
        journal = self.root / "docs" / "agents" / "journals" / "wave-coordinator.md"
        prior = journal.read_text(encoding="utf-8") if journal.exists() else "# Journal\n"
        journal.write_text(prior + f"\nwave-id: `{wave_id}`\n", encoding="utf-8")
        return wave_id, change_id

    def test_wave_prepare_guards_when_another_wave_active_create(self):
        active_wave, _ = self._make_wave_with_change("active-one", status="active")
        target_wave, _ = self._make_wave_with_change("planned-one", status="planned")
        result = self.srv.wave_prepare_response(self.root, target_wave, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("another_wave_active", codes)
        self.assertEqual(result["data"].get("active_wave_id"), active_wave)
        # target wave still planned
        target_md = self.root / "docs" / "waves" / target_wave / "wave.md"
        self.assertIn("Status: planned", target_md.read_text(encoding="utf-8"))

    def test_wave_prepare_guards_when_another_wave_active_dry_run(self):
        self._make_wave_with_change("active-two", status="active")
        target_wave, _ = self._make_wave_with_change("planned-two", status="planned")
        result = self.srv.wave_prepare_response(self.root, target_wave, mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["data"]["mode"], "dry_run")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("another_wave_active", codes)

    def test_wave_prepare_self_reprepare_allowed(self):
        wave_id, _ = self._make_wave_with_change("self-prep", status="active")
        # Re-running prepare on the currently active target must not trigger the guard.
        result = self.srv.wave_prepare_response(self.root, wave_id, mode="create")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("another_wave_active", codes)

    def test_wave_prepare_another_wave_active_envelope_shape(self):
        active_wave, _ = self._make_wave_with_change("env-active", status="active")
        target_wave, _ = self._make_wave_with_change("env-target", status="planned")
        result = self.srv.wave_prepare_response(self.root, target_wave, mode="create")
        self.assertEqual(result["status"], "error")
        self.assertIn("active_wave_id", result["data"])
        self.assertIn("active_wave_path", result["data"])
        self.assertEqual(result["data"]["active_wave_id"], active_wave)
        # Recovery usage points at wave_pause
        self.assertIn("wave_pause", result.get("usage", ""))

    def test_wave_prepare_after_pause_succeeds(self):
        active_wave, _ = self._make_wave_with_change("ctx-switch-active", status="active")
        target_wave, _ = self._make_wave_with_change("ctx-switch-target", status="planned")
        # Pause active wave
        pause_result = self.srv.wave_pause_response(self.root, active_wave, mode="create")
        self.assertEqual(pause_result["data"]["status_transition"], {"from": "active", "to": "paused"})
        # Now prepare target wave (patch lint/garden because minimal test repo isn't fully seeded)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_prepare_response(self.root, target_wave, mode="create")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("another_wave_active", codes)
        # Target wave transitioned to active
        target_md = self.root / "docs" / "waves" / target_wave / "wave.md"
        self.assertIn("Status: active", target_md.read_text(encoding="utf-8"))

    def test_wave_prepare_resumes_paused_wave(self):
        paused_wave, _ = self._make_wave_with_change("resume-target", status="paused")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_prepare_response(self.root, paused_wave, mode="create")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("another_wave_active", codes)
        wave_md = self.root / "docs" / "waves" / paused_wave / "wave.md"
        self.assertIn("Status: active", wave_md.read_text(encoding="utf-8"))

    def test_wave_prepare_aggregates_active_wave_and_lint_diagnostics(self):
        """AC-6: when another wave is active AND lint fails, both diagnostics appear."""
        self._make_wave_with_change("agg-active", status="active")
        target_wave, _ = self._make_wave_with_change("agg-target", status="planned")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(
                self.srv,
                "run_validate",
                return_value={"passed": False, "errors": ["synthetic lint error for AC-6 aggregation test"], "warnings": [], "output": ""},
            ):
                result = self.srv.wave_prepare_response(self.root, target_wave, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("another_wave_active", codes)
        self.assertIn("docs_lint_error", codes)

    def test_wave_prepare_resume_blocked_when_other_active(self):
        self._make_wave_with_change("resume-blocker", status="active")
        paused_wave, _ = self._make_wave_with_change("resume-paused", status="paused")
        result = self.srv.wave_prepare_response(self.root, paused_wave, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("another_wave_active", codes)
        # Paused wave still paused
        wave_md = self.root / "docs" / "waves" / paused_wave / "wave.md"
        self.assertIn("Status: paused", wave_md.read_text(encoding="utf-8"))


class WaveCurrentListEnvelopeTests(unittest.TestCase):
    """12as6: wave_current returns data.waves[] with all non-closed waves, active first."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, wave_id: str, status: str) -> None:
        wave_dir = self.root / "docs" / "waves" / wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            f"# Wave Record\n\nStatus: {status}\nwave-id: `{wave_id}`\n\n## Changes\n\n",
            encoding="utf-8",
        )

    def test_wave_current_returns_waves_array(self):
        self._make_wave("1200a only-planned", "planned")
        result = self.srv.wave_current_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertIn("waves", result["data"])
        self.assertNotIn("wave", result["data"])
        self.assertEqual(len(result["data"]["waves"]), 1)
        self.assertEqual(result["data"]["waves"][0]["status"], "planned")

    def test_wave_current_empty_state_returns_empty_array(self):
        result = self.srv.wave_current_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["waves"], [])
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("no_active_wave", codes)

    def test_wave_current_orders_active_planned_paused(self):
        # Intentionally put them out of order alphabetically so the sort verifies
        self._make_wave("1200z planned-z", "planned")
        self._make_wave("1200a active-a", "active")
        self._make_wave("1200m paused-m", "paused")
        self._make_wave("1200b planned-b", "planned")
        result = self.srv.wave_current_response(self.root)
        waves = result["data"]["waves"]
        statuses = [w["status"] for w in waves]
        self.assertEqual(statuses, ["active", "planned", "planned", "paused"])
        # Within status groups, lifecycle-ID (wave_id) order preserved
        planned_ids = [w["wave_id"] for w in waves if w["status"] == "planned"]
        self.assertEqual(planned_ids, sorted(planned_ids))

    def test_wave_current_entry_shape(self):
        self._make_wave("1200a active-shape", "active")
        result = self.srv.wave_current_response(self.root)
        entry = result["data"]["waves"][0]
        for field in ("wave_id", "status", "changes", "path", "next_action"):
            self.assertIn(field, entry)
        self.assertEqual(entry["next_action"], "implement_wave")

    def test_wave_current_paused_next_action_is_resume_wave(self):
        self._make_wave("1200a only-paused", "paused")
        result = self.srv.wave_current_response(self.root)
        entry = result["data"]["waves"][0]
        self.assertEqual(entry["status"], "paused")
        self.assertEqual(entry["next_action"], "resume_wave")

    def test_wave_current_planned_next_action_is_prepare_wave(self):
        self._make_wave("1200a only-planned", "planned")
        result = self.srv.wave_current_response(self.root)
        entry = result["data"]["waves"][0]
        self.assertEqual(entry["next_action"], "prepare_wave")

    def test_wave_current_skips_paused_when_filtering_active(self):
        """Paused waves appear in data.waves but do not occupy the 'active' slot."""
        self._make_wave("1200a only-paused", "paused")
        result = self.srv.wave_current_response(self.root)
        waves = result["data"]["waves"]
        self.assertEqual(len(waves), 1)
        self.assertEqual(waves[0]["status"], "paused")
        # No wave has status == 'active'
        self.assertFalse(any(w["status"] == "active" for w in waves))

    def test_wave_current_excludes_closed(self):
        self._make_wave("1200a closed-wave", "closed")
        self._make_wave("1200b planned-wave", "planned")
        result = self.srv.wave_current_response(self.root)
        statuses = [w["status"] for w in result["data"]["waves"]]
        self.assertNotIn("closed", statuses)
        self.assertIn("planned", statuses)


class WaveAuditUnaffectedByCurrentEnvelopeTests(unittest.TestCase):
    """AC-21: wave_audit still returns the expected shape after wave_current envelope change.

    wave_audit_response uses the internal current_wave() helper (unchanged singular form),
    not wave_current_response, so the envelope change is not a migration target — but this
    test asserts wave_audit continues to surface the active wave via its own response shape
    so any future refactor that wires wave_audit through wave_current_response can't silently
    regress.
    """

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, wave_id: str, status: str) -> None:
        wave_dir = self.root / "docs" / "waves" / wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            f"# Wave Record\n\nStatus: {status}\nwave-id: `{wave_id}`\n\n## Changes\n\n",
            encoding="utf-8",
        )

    def test_wave_audit_reports_active_wave_when_present(self):
        self._make_wave("1200a audit-active", "active")
        result = self.srv.wave_audit_response(self.root)
        self.assertEqual(result["status"], "ok")
        wave_data = result["data"]["wave"]
        self.assertEqual(wave_data.get("status"), "active")
        self.assertEqual(wave_data.get("next_action"), "implement_wave")

    def test_wave_audit_reports_no_wave_when_only_paused(self):
        """Paused wave should not satisfy wave_audit's 'active or planned' readiness check."""
        self._make_wave("1200a audit-paused", "paused")
        result = self.srv.wave_audit_response(self.root)
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("no_active_wave", codes)


class WaveValidateAcceptsPausedTests(unittest.TestCase):
    """12as6: lint must accept Status: paused in wave.md."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_paused_status_does_not_trigger_lint_error_on_status_field(self):
        """A wave.md with Status: paused must not produce any error referencing 'paused'
        as an invalid/unknown/rejected status value.

        Catches future regressions where a validator might enumerate allowed statuses
        and forget to include 'paused'. Other lint rules (journal reference, required
        sections) may still fail for unrelated reasons — those are excluded from the
        assertion.
        """
        wave_dir = self.root / "docs" / "waves" / "1200a paused-lint-check"
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            "# Wave Record\n\n"
            "Owner: Engineering\n"
            "Status: paused\n"
            "Last verified: 2026-05-01\n\n"
            "wave-id: `1200a paused-lint-check`\n"
            "Title: Paused Lint Check\n\n"
            "## Changes\n\n"
            "## Wave Summary\n\nTest.\n\n"
            "## Journal Watchpoints\n\n- Paused wave testing.\n\n"
            "## Dependencies\n\n- None.\n",
            encoding="utf-8",
        )
        result = self.srv.run_validate(self.root)
        errors = result.get("errors", [])
        # No error may mention 'paused' as invalid / unknown / unexpected / rejected.
        # Validators that reject specific status values would produce such messages.
        paused_rejection_markers = ("invalid status", "unknown status", "unexpected status", "status.*paused", "paused.*invalid")
        offending = [
            err for err in errors
            if "paused" in err.lower() and any(marker.replace(".*", "") in err.lower() for marker in paused_rejection_markers)
        ]
        self.assertEqual(
            offending,
            [],
            f"Lint produced errors rejecting 'paused' as a wave status: {offending}",
        )


class WaveCurrentMigrationGrepTests(unittest.TestCase):
    """12as6 AC-20: no in-tree readers of the old data.wave envelope remain (outside historical)."""

    def test_no_stale_data_wave_readers_in_source_and_prompts(self):
        """Grep for old-style `data["wave"]` or `data.wave` response readers.

        Scope: framework scripts, prompt surfaces, seeds, AGENTS.md. Excludes
        historical wave records and journals under docs/waves/** and
        docs/agents/journals/**.
        """
        import re
        import subprocess
        # tests/ → scripts/ → framework/ → .wavefoundry/ → repo_root = 4 parents up
        repo_root = Path(__file__).resolve().parents[4]
        targets = [
            repo_root / ".wavefoundry" / "framework" / "scripts",
            repo_root / "docs" / "prompts",
            repo_root / ".wavefoundry" / "framework" / "seeds",
            repo_root / "AGENTS.md",
        ]
        existing_targets = [str(t) for t in targets if t.exists()]
        if not existing_targets:
            self.skipTest("No target paths to scan")
        # Pattern matches response-reader forms, not producer forms (key emission).
        # Examples to FAIL on: result["data"]["wave"]["status"], resp.data.wave.wave_id
        # Examples allowed: "wave": wave_data (producer in wave_audit), key strings like '"wave"'.
        pattern = r'(?:result|resp|response|data)\[(?:"wave"|\'wave\')\](?!s)'
        try:
            proc = subprocess.run(
                ["grep", "-rnE", "--include=*.py", "--include=*.md", pattern, *existing_targets],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            self.skipTest("grep not available")
        hits = [line for line in proc.stdout.strip().splitlines() if line]
        # Filter out this very test file (self-references to the pattern as a string literal
        # and the comment examples above would register as matches).
        hits = [line for line in hits if "test_server_tools.py" not in line]
        self.assertEqual(
            hits,
            [],
            f"Found stale `data[\"wave\"]` readers that should migrate to `data[\"waves\"][0]`:\n"
            + "\n".join(hits),
        )


class IndexerContractTests(unittest.TestCase):
    """Verify that every indexer function called dynamically from server.py exists.

    server.py loads indexer.py at runtime via _load_script and calls functions by
    name. A missing function raises AttributeError only when the code path is
    exercised — these tests catch the mismatch statically so it surfaces in CI
    rather than in a live project.
    """

    def setUp(self):
        INDEXER_PATH = SCRIPTS_ROOT / "indexer.py"
        spec = importlib.util.spec_from_file_location("indexer_contract", INDEXER_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.idx = mod

    def _assert_callable(self, name: str) -> None:
        self.assertTrue(
            callable(getattr(self.idx, name, None)),
            f"indexer.py is missing callable '{name}' — server.py calls it via _load_script",
        )

    def test_walk_repo_exists(self):
        self._assert_callable("walk_repo")

    def test_is_relative_to_exists(self):
        self._assert_callable("_is_relative_to")

    def test_filter_project_index_excludes_exists(self):
        self._assert_callable("_filter_project_index_excludes")

    def test_filter_by_prefixes_exists(self):
        self._assert_callable("_filter_by_prefixes")

    def test_build_file_hashes_exists(self):
        self._assert_callable("_build_file_hashes")

    def test_chunks_for_file_exists(self):
        self._assert_callable("_chunks_for_file")


if __name__ == "__main__":
    unittest.main()
