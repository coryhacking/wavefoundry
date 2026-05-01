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


class ChangeCreateResponseTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_does_not_write_file(self):
        result = self.srv.wave_change_create_response(self.root, "feat", "guided-tools", mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        self.assertFalse((self.root / result["data"]["path"]).exists())

    def test_create_writes_file_once_and_repeat_is_safe(self):
        first = self.srv.wave_change_create_response(self.root, "feat", "guided-tools", mode="create")
        second = self.srv.wave_change_create_response(self.root, "feat", "guided-tools", mode="create")

        self.assertEqual(first["status"], "ok")
        self.assertTrue((self.root / first["data"]["path"]).exists())
        self.assertEqual(second["status"], "ok")
        self.assertEqual(second["diagnostics"][0]["code"], "already_exists")

    def test_invalid_kind_returns_error(self):
        result = self.srv.wave_change_create_response(self.root, "wave", "not-allowed", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_arguments")

    def test_empty_slug_returns_error(self):
        result = self.srv.wave_change_create_response(self.root, "feat", "   ", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_arguments")

    def test_create_triggers_background_index_refresh(self):
        with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as trigger:
            result = self.srv.wave_change_create_response(self.root, "feat", "guided-tools", mode="create")

        self.assertEqual(result["status"], "ok")
        trigger.assert_called_once_with(self.root, [result["data"]["path"]])


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
        self.assertIn("wave_pause", text)

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
        self.assertTrue(result["data"]["archive_path"])

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
            "wave_change_create",
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


if __name__ == "__main__":
    unittest.main()
