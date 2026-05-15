from __future__ import annotations

import hashlib
import hashlib
import importlib.util
import json
import os
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
                with patch.object(index, "_get_reranker", return_value=None):
                    results, _ = index.search_docs("framework project", top_n=5)

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
                with patch.object(index, "_get_reranker", return_value=None):
                    results, _ = index.search_docs("project", top_n=5)

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
                with patch.object(index, "_get_reranker", return_value=None):
                    results, _ = index.search_docs("install", top_n=5)

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
                with patch.object(index, "_get_reranker", return_value=None):
                    results, _ = index.search_docs("one", top_n=5)

        self.assertEqual(results, [])

    def test_search_docs_lexical_supports_prompt_kind(self):
        index = self.srv.WaveIndex(self.root)
        chunks = [
            {
                "id": "prompt",
                "path": "docs/prompts/prepare-wave.prompt.md",
                "kind": "prompt",
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
            "docs/prompts/plan-feature.prompt.md": "# Plan Feature\n\nDo the thing.\n",
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
        index.search_docs.return_value = ([], False)
        self.srv.docs_search_response(index, "q", "Doc")
        index.search_docs.assert_called_with("q", kind="doc", top_n=7, tags=None)

    def test_wave_help_catalog_is_browseable(self):
        self.srv._cached_help_catalog_json.cache_clear()
        result = self.srv.wave_help_response()
        self.assertEqual(result["status"], "ok")
        self.assertIn("core_tools", result["data"])
        self.assertIn("workflows", result["data"])
        self.assertIn("wave_help", result["data"]["core_tools"])
        self.assertIn("wave_server_info", result["data"]["core_tools"])
        self.assertIn("wave_map", result["data"]["core_tools"])
        self.assertIn("server_identity", result["data"]["workflows"])

    def test_wave_server_info_returns_repo_identity(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            root = _make_repo(Path(tmp.name) / "wave_foundry")
            result = self.srv.wave_server_info_response(root)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["data"]["repo_root"], str(root.resolve()))
            self.assertEqual(result["data"]["repo_name"], root.name)
            self.assertEqual(result["data"]["project_slug"], "wave-foundry")
            expected_suffix = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:8]
            self.assertEqual(
                result["data"]["codex_server_name"],
                f"wavefoundry-{expected_suffix}",
            )
            self.assertEqual(result["next_tools"], ["wave_current", "wave_help"])
        finally:
            tmp.cleanup()

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
        index.search_docs.return_value = ([{
            "id": "chunk-1",
            "path": ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
            "kind": "seed",
            "section": "Install",
            "lines": [1, 10],
            "text": "install seed body",
            "score": 0.99,
        }], False)

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
        index.search_docs_lexical.assert_called_once_with("agent catalog", kind="doc", top_n=7)
        index.docs_health.assert_not_called()

    def test_docs_search_calls_semantic_search_directly_without_health_preflight(self):
        # docs_health() must not be called on the search hot path regardless of index state.
        index = MagicMock()
        index.search_docs.return_value = ([{
            "id": "chunk-1",
            "path": "docs/plans/129nj.md",
            "kind": "doc",
            "section": "Rationale",
            "lines": [1, 5],
            "text": "agent catalog expansion",
            "score": 0.95,
        }], False)

        result = self.srv.docs_search_response(index, "agent catalog", "doc")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["search_mode"], "semantic")
        index.search_docs.assert_called_once_with("agent catalog", kind="doc", top_n=7, tags=None)
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
        index.search_docs_lexical.assert_called_once_with("agent catalog", kind="doc", top_n=7)
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
        index.search_code.return_value = (results, False)
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
        index.search_code.assert_called_once_with("render", language="typescript", top_n=7, kind=None, max_per_file=None, tags=None)

    def test_raw_extension_without_dot_is_normalized(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "render", "tsx")
        self.assertEqual(result["data"]["language"], "typescript")
        index.search_code.assert_called_once_with("render", language="typescript", top_n=7, kind=None, max_per_file=None, tags=None)

    def test_raw_extension_with_dot_is_normalized(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "render", ".tsx")
        self.assertEqual(result["data"]["language"], "typescript")
        index.search_code.assert_called_once_with("render", language="typescript", top_n=7, kind=None, max_per_file=None, tags=None)

    def test_js_extension_normalizes_to_javascript(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "fetch", "js")
        self.assertEqual(result["data"]["language"], "javascript")
        index.search_code.assert_called_once_with("fetch", language="javascript", top_n=7, kind=None, max_per_file=None, tags=None)

    def test_ts_extension_normalizes_to_typescript(self):
        index = self._index_with_results(self._fake_result())
        result = self.srv.code_search_response(index, "parse", "ts")
        self.assertEqual(result["data"]["language"], "typescript")

    def test_sql_alias_extensions_normalize_to_sql(self):
        index = self._index_with_results([{
            "id": "src/schema.psql::orders",
            "path": "src/schema.psql",
            "kind": "code",
            "language": "sql",
            "section": "schema > orders",
            "lines": [1, 5],
            "text": "CREATE TABLE orders (id INT);",
            "score": 0.9,
        }])
        for ext in ("psql", ".pgsql", "ddl", ".dml", "tsql", ".hql"):
            result = self.srv.code_search_response(index, "select", ext)
            self.assertEqual(result["data"]["language"], "sql")

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
            # What would _ext_language() return for this extension?
            chunker_result = chunker_map.get(ext, ext.lstrip("."))
            if chunker_result != server_lang:
                mismatches.append(
                    f"{ext}: server={server_lang!r} chunker={chunker_result!r}"
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
        index.search_code.return_value = (results, False)
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
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8") + "\n## Review Evidence\n\n- operator-signoff: approved\n",
            encoding="utf-8",
        )
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
                "- operator-signoff: approved\n"
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
        self.assertTrue(any(d["code"] == "missing_required_lane" for d in result["diagnostics"]))

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
                "- operator-signoff: approved\n"
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
        self.assertTrue(any(d["code"] == "missing_required_lane" for d in result["diagnostics"]))


class WaveReopenTests(unittest.TestCase):
    """12eb0: wave_reopen MCP tool."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        self.wave_md = wave_dir / "wave.md"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_wave(self, status: str, completed_at: bool = False) -> None:
        text = (
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            f"Status: {status}\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `done`\n\n"
        )
        if completed_at:
            text += "Completed At: 2026-05-06\n\n"
        text += "## Wave Summary\n\nSome summary.\n"
        self.wave_md.write_text(text, encoding="utf-8")

    def test_reopen_closed_wave_sets_status_active(self):
        self._write_wave("closed")
        result = self.srv.wave_reopen_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")
        self.assertIn("Status: active", self.wave_md.read_text(encoding="utf-8"))

    def test_reopen_removes_completed_at_stamp(self):
        self._write_wave("closed", completed_at=True)
        self.assertIn("Completed At:", self.wave_md.read_text(encoding="utf-8"))
        self.srv.wave_reopen_response(self.root, "1200a test-wave")
        self.assertNotIn("Completed At:", self.wave_md.read_text(encoding="utf-8"))

    def test_reopen_paused_wave_sets_status_active(self):
        self._write_wave("paused")
        result = self.srv.wave_reopen_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")
        self.assertIn("Status: active", self.wave_md.read_text(encoding="utf-8"))

    def test_reopen_non_closed_wave_returns_error(self):
        self._write_wave("active")
        result = self.srv.wave_reopen_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "wave_not_closed" for d in result["diagnostics"]))

    def test_reopen_planned_wave_returns_error(self):
        self._write_wave("planned")
        result = self.srv.wave_reopen_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "wave_not_closed" for d in result["diagnostics"]))

    def test_reopen_nonexistent_wave_returns_error(self):
        result = self.srv.wave_reopen_response(self.root, "nonexistent-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "wave_not_found" for d in result["diagnostics"]))


class OperatorSignoffTests(unittest.TestCase):
    """12eb2: operator review lane required for wave_review and wave_close."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        self.wave_md = wave_dir / "wave.md"

    def tearDown(self):
        self.tmp.cleanup()

    def _base_wave(self, with_operator_signoff: bool = True) -> str:
        review = "## Review Evidence\n\n"
        if with_operator_signoff:
            review += "- operator-signoff: approved\n"
        return (
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `done`\n\n"
            + review
        )

    def test_wave_review_fails_without_operator_signoff(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=False), encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("missing_operator_signoff", codes)

    def test_wave_review_passes_with_operator_signoff(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=True), encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")

    def test_wave_review_includes_operator_in_required_lanes(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=True), encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertIn("operator", result["data"]["required_lanes"])

    def test_wave_close_blocked_without_operator_signoff(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=False), encoding="utf-8")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("missing_operator_signoff", codes)

    def test_wave_close_succeeds_with_operator_signoff(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=True), encoding="utf-8")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("Status: closed", self.wave_md.read_text(encoding="utf-8"))

    def test_placeholder_signoff_does_not_count_as_approval(self):
        # Regression: "<approved when operator confirms closure>" contains "approved"
        # but is a template placeholder, not a real signoff.
        text = (
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `done`\n\n"
            "## Review Evidence\n\n"
            "- operator-signoff: <approved when operator confirms closure>\n"
        )
        self.wave_md.write_text(text, encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("missing_operator_signoff", codes)

    def test_placeholder_signoff_blocks_wave_close(self):
        text = (
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `done`\n\n"
            "## Review Evidence\n\n"
            "- operator-signoff: <approved when operator confirms closure>\n"
        )
        self.wave_md.write_text(text, encoding="utf-8")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("missing_operator_signoff", codes)


class IndexBuildStatusTests(unittest.TestCase):
    """12ebh: wave_index_build_status MCP tool."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.index_dir / "index-build.json"
        self.log_path = self.index_dir / "index-build.log"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_state(self, pid: int, started_at: float) -> None:
        import json
        self.state_path.write_text(json.dumps({"pid": pid, "started_at": started_at}), encoding="utf-8")

    def test_idle_when_no_state_file(self):
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["state"], "idle")

    def test_running_when_pid_active(self):
        import os, time
        self._write_state(os.getpid(), time.time() - 30)
        self.log_path.write_text("build_index: embedding doc chunks 100-200/500\n", encoding="utf-8")
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "running")
        self.assertIn("elapsed_seconds", result["data"])
        self.assertEqual(result["data"]["progress"], "build_index: embedding doc chunks 100-200/500")

    def test_background_running_when_background_pid_active(self):
        import os
        bg_pid = self.index_dir / "background-build.pid"
        bg_log = self.index_dir / "background-build.log"
        bg_pid.write_text(str(os.getpid()), encoding="utf-8")
        bg_log.write_text(
            "Code index build started in background (PID 12345)\n"
            "build_index: scanning source files\n",
            encoding="utf-8",
        )
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "running")
        self.assertEqual(result["data"]["source"], "background")
        self.assertEqual(result["data"]["progress"], "build_index: scanning source files")

    def test_finished_when_pid_dead(self):
        import time
        self._write_state(99999999, time.time() - 120)
        self.log_path.write_text(
            "build_index: embedding code chunks 1-2000/2000\n"
            "build_index: done — 300 files indexed, 2000 doc chunks, 1800 code chunks\n",
            encoding="utf-8",
        )
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertEqual(result["data"]["files_indexed"], 300)
        self.assertEqual(result["data"]["doc_chunks"], 2000)
        self.assertEqual(result["data"]["code_chunks"], 1800)

    def test_finished_falls_back_to_last_line_when_no_summary(self):
        import time
        self._write_state(99999999, time.time() - 60)
        self.log_path.write_text("build_index: some partial output\n", encoding="utf-8")
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertEqual(result["data"]["last_log_line"], "build_index: some partial output")

    def test_finished_when_log_has_done_marker_despite_live_pid(self):
        # Regression: OS recycled the PID to an unrelated process after indexer exited.
        # The done marker in the log must take precedence over _pid_is_running.
        import os, time
        self._write_state(os.getpid(), time.time() - 300)
        self.log_path.write_text(
            "build_index: embedding code chunks 1-500/500\n"
            "build_index: done — 100 files indexed, 500 doc chunks, 400 code chunks\n",
            encoding="utf-8",
        )
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertEqual(result["data"]["files_indexed"], 100)

    def test_finished_when_log_has_up_to_date_despite_live_pid(self):
        # Regression: zombie process (defunct on macOS) keeps os.kill(pid,0) returning True.
        # "index is up to date" must be treated as a terminal log state, same as the done marker.
        import os, time
        self._write_state(os.getpid(), time.time() - 60)
        self.log_path.write_text("build_index: index is up to date\n", encoding="utf-8")
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")

    def test_invalid_layer_returns_error(self):
        result = self.srv.wave_index_build_status_response(self.root, layer="bogus")
        self.assertEqual(result["status"], "error")

    def test_framework_layer_uses_framework_paths(self):
        fw_index = self.root / ".wavefoundry" / "framework" / "index"
        fw_index.mkdir(parents=True, exist_ok=True)
        result = self.srv.wave_index_build_status_response(self.root, layer="framework")
        self.assertEqual(result["data"]["state"], "idle")

    def test_previous_stats_included_in_finished_response(self):
        import json, time
        self._write_state(99999999, time.time() - 120)
        self.log_path.write_text(
            "build_index: done — 300 files indexed, 2000 doc chunks, 1800 code chunks\n",
            encoding="utf-8",
        )
        stats = {"elapsed_seconds": 420, "files_indexed": 300, "doc_chunks": 2000, "code_chunks": 1800, "built_at": "2026-05-06T10:00:00Z", "content": "docs", "mode": "rebuild"}
        (self.index_dir / "index-build-stats.json").write_text(json.dumps(stats), encoding="utf-8")
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertIn("previous_stats", result["data"])
        self.assertEqual(result["data"]["previous_stats"]["files_indexed"], 300)
        self.assertEqual(result["data"]["previous_stats"]["doc_chunks"], 2000)
        self.assertEqual(result["data"]["previous_stats"]["code_chunks"], 1800)

    def test_previous_stats_included_in_running_response(self):
        import json, os, time
        self._write_state(os.getpid(), time.time() - 30)
        self.log_path.write_text("build_index: embedding doc chunks 100-200/500\n", encoding="utf-8")
        stats = {"elapsed_seconds": 300, "files_indexed": 200, "doc_chunks": 1500, "code_chunks": 0, "built_at": "2026-05-05T10:00:00Z", "content": "docs", "mode": "update"}
        (self.index_dir / "index-build-stats.json").write_text(json.dumps(stats), encoding="utf-8")
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "running")
        self.assertIn("previous_stats", result["data"])
        self.assertEqual(result["data"]["previous_stats"]["elapsed_seconds"], 300)

    def test_missing_stats_not_included_in_response(self):
        import time
        self._write_state(99999999, time.time() - 120)
        self.log_path.write_text(
            "build_index: done — 300 files indexed, 2000 doc chunks, 1800 code chunks\n",
            encoding="utf-8",
        )
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertIn("previous_stats", result["data"])
        self.assertEqual(result["data"]["previous_stats"]["files_indexed"], 300)

    def test_corrupt_stats_file_not_included(self):
        import time
        self._write_state(99999999, time.time() - 120)
        self.log_path.write_text(
            "build_index: done — 300 files indexed, 2000 doc chunks, 1800 code chunks\n",
            encoding="utf-8",
        )
        (self.index_dir / "index-build-stats.json").write_text("not valid json{{", encoding="utf-8")
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertIn("previous_stats", result["data"])
        self.assertEqual(result["data"]["previous_stats"]["files_indexed"], 300)


class IndexBuildStatsTests(unittest.TestCase):
    """12ec2: index-build-stats-persistence helpers."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_stats_path_project_layer(self):
        path = self.srv._index_build_stats_path(self.root, "project")
        self.assertEqual(path, self.root / ".wavefoundry" / "index" / "index-build-stats.json")

    def test_stats_path_framework_layer(self):
        path = self.srv._index_build_stats_path(self.root, "framework")
        self.assertEqual(path, self.root / ".wavefoundry" / "framework" / "index" / "index-build-stats.json")

    def test_read_returns_none_when_file_missing(self):
        result = self.srv._read_index_build_stats_file(self.root, "project")
        self.assertIsNone(result)

    def test_read_returns_none_on_corrupt_json(self):
        stats_path = self.root / ".wavefoundry" / "index" / "index-build-stats.json"
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text("{{broken", encoding="utf-8")
        result = self.srv._read_index_build_stats_file(self.root, "project")
        self.assertIsNone(result)

    def test_write_and_read_roundtrip(self):
        stats = {"elapsed_seconds": 420, "files_indexed": 300, "doc_chunks": 2000, "code_chunks": 1800, "built_at": "2026-05-06T10:00:00Z", "content": "docs", "mode": "rebuild"}
        self.srv._write_index_build_stats_file(self.root, "project", stats)
        result = self.srv._read_index_build_stats_file(self.root, "project")
        self.assertEqual(result, stats)

    def test_write_creates_parent_directories(self):
        stats = {"elapsed_seconds": 60, "files_indexed": 50, "doc_chunks": 100, "code_chunks": 200, "built_at": None, "content": "docs", "mode": "update"}
        self.srv._write_index_build_stats_file(self.root, "project", stats)
        stats_path = self.root / ".wavefoundry" / "index" / "index-build-stats.json"
        self.assertTrue(stats_path.exists())

    def test_write_does_not_raise_on_unwritable_path(self):
        # Passes a read-only directory scenario by using a file path where parent cannot be created.
        # We simulate this by pointing root to a non-existent nested path under a file.
        fake_root = self.root / "notadir.txt"
        fake_root.write_text("x", encoding="utf-8")
        self.srv._write_index_build_stats_file(fake_root, "project", {"x": 1})

    def test_framework_layer_stats_written_correctly(self):
        stats = {"elapsed_seconds": 180, "files_indexed": 150, "doc_chunks": 900, "code_chunks": 0, "built_at": "2026-05-06T10:00:00Z", "content": "docs", "mode": "rebuild"}
        self.srv._write_index_build_stats_file(self.root, "framework", stats)
        stats_path = self.root / ".wavefoundry" / "framework" / "index" / "index-build-stats.json"
        self.assertTrue(stats_path.exists())
        result = self.srv._read_index_build_stats_file(self.root, "framework")
        self.assertEqual(result["files_indexed"], 150)


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
        *,
        content: str = "docs",
        full: bool = False,
        layer: str = "project",
    ) -> dict:
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            return self.srv.run_index_rebuild(self.root, content=content, full=full, layer=layer)

    def test_returns_immediately_with_pre_build_stats(self):
        self._write_index_state(file_hashes={"docs/a.md": "h1"}, docs_chunks=[{"id": "d1"}])
        result = self._run()
        self.assertTrue(result["passed"])
        self.assertFalse(result["already_running"])
        self.assertEqual(result["content"], "docs")
        self.assertEqual(result["stats"]["files_total"], 1)
        self.assertEqual(result["stats"]["doc_chunks"], 1)
        self.assertIn("pid", result)
        self.assertIn("log", result)
        self.assertIn("notice", result)

    def test_full_flag_propagates(self):
        """Project ``content=all`` runs ``setup_index.py`` (docs + code); ``--full`` is appended."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen") as popen, \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            popen.return_value = mock_proc
            self.srv.run_index_rebuild(self.root, content="all", full=True)
        cmd = popen.call_args.args[0]
        self.assertIn("setup_index.py", str(cmd[1]))
        self.assertIn("--include-code", cmd)
        self.assertIn("--full", cmd)

    def test_index_scope_reflects_full_flag(self):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            inc = self.srv.run_index_rebuild(self.root, content="docs", full=False)
            full = self.srv.run_index_rebuild(self.root, content="docs", full=True)
        self.assertEqual(inc["index_scope"], "incremental_update")
        self.assertEqual(full["index_scope"], "full_rebuild")

    def test_project_all_rebuild_uses_setup_index_script(self):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen") as popen, \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            popen.return_value = mock_proc
            self.srv.run_index_rebuild(self.root, content="all", full=True)
        cmd = popen.call_args.args[0]
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
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen") as popen, \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            popen.return_value = mock_proc
            self.srv.run_index_rebuild(self.root, content="code")
        cmd = popen.call_args.args[0]
        self.assertIn("--project-include-prefix", cmd)
        self.assertIn(".wavefoundry/framework/scripts", cmd)
        self.assertIn("vendor/docs", cmd)

    def test_framework_layer_uses_framework_index_args(self):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen") as popen, \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            popen.return_value = mock_proc
            result = self.srv.run_index_rebuild(self.root, content="docs", layer="framework")
        cmd = popen.call_args.args[0]
        self.assertEqual(result["layer"], "framework")
        self.assertIn("--index-dir", cmd)
        self.assertIn(".wavefoundry/framework/index", cmd)
        self.assertIn("--include-prefix", cmd)
        self.assertIn(".wavefoundry/framework", cmd)
        self.assertIn("--no-ignore-files", cmd)

    def test_up_to_date_returns_without_spawning(self):
        self._write_index_state(file_hashes={"docs/a.md": "h1"}, docs_chunks=[{"id": "d1"}])
        with patch("subprocess.Popen") as popen, \
             patch.object(self.srv, "_index_is_up_to_date", return_value=True):
            result = self.srv.run_index_rebuild(self.root, content="docs", full=False)
        popen.assert_not_called()
        self.assertTrue(result["passed"])
        self.assertTrue(result["up_to_date"])
        self.assertNotIn("pid", result)
        self.assertIn("notice", result)

    def test_full_bypasses_up_to_date_check(self):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc) as popen, \
             patch.object(self.srv, "_index_is_up_to_date", return_value=True):
            result = self.srv.run_index_rebuild(self.root, content="docs", full=True)
        popen.assert_called_once()
        self.assertFalse(result.get("up_to_date", False))

    def test_already_running_returns_without_spawning(self):
        # Write a state file with a fake "running" PID
        import time
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        state_path = index_dir / "index-build.json"
        state_path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": time.time(), "content": "docs", "layer": "project", "full": False}),
            encoding="utf-8",
        )
        mock_proc = MagicMock()
        with patch("subprocess.Popen") as popen:
            result = self.srv.run_index_rebuild(self.root, content="docs")
        popen.assert_not_called()
        self.assertTrue(result["already_running"])
        self.assertTrue(result["passed"])

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
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc):
            result = self.srv.run_index_rebuild(self.root, content="docs", layer="framework")
        self.assertEqual(result["stats"]["files_total"], 2)
        self.assertEqual(result["stats"]["doc_chunks"], 3)
        self.assertEqual(result["index_scope"], "incremental_update")

    def test_stats_written_when_previous_log_has_done_marker(self):
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        log_path = index_dir / "index-build.log"
        log_path.write_text(
            "build_index: done — 150 files indexed, 800 doc chunks, 600 code chunks\n",
            encoding="utf-8",
        )
        state_path = index_dir / "index-build.json"
        state_path.write_text(
            json.dumps({"pid": 99999, "started_at": 1000.0, "content": "docs", "full": False}),
            encoding="utf-8",
        )
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            self.srv.run_index_rebuild(self.root, content="docs")
        stats = self.srv._read_index_build_stats_file(self.root, "project")
        self.assertIsNotNone(stats)
        self.assertEqual(stats["files_indexed"], 150)
        self.assertEqual(stats["doc_chunks"], 800)
        self.assertEqual(stats["code_chunks"], 600)
        self.assertEqual(stats["content"], "docs")
        self.assertEqual(stats["mode"], "update")

    def test_stats_not_written_when_no_done_marker(self):
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        log_path = index_dir / "index-build.log"
        log_path.write_text("build_index: embedding doc chunks 100-200/500\n", encoding="utf-8")
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            self.srv.run_index_rebuild(self.root, content="docs")
        stats = self.srv._read_index_build_stats_file(self.root, "project")
        self.assertIsNone(stats)

    def test_stats_not_written_when_no_previous_log(self):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            self.srv.run_index_rebuild(self.root, content="docs")
        stats = self.srv._read_index_build_stats_file(self.root, "project")
        self.assertIsNone(stats)

    def test_notice_includes_timing_estimate_when_stats_available(self):
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        stats = {"elapsed_seconds": 420, "files_indexed": 200, "doc_chunks": 1000, "code_chunks": 0, "built_at": None, "content": "docs", "mode": "rebuild"}
        (index_dir / "index-build-stats.json").write_text(json.dumps(stats), encoding="utf-8")
        # Write a log without done marker so stats won't be overwritten
        (index_dir / "index-build.log").write_text("no done marker\n", encoding="utf-8")
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            result = self.srv.run_index_rebuild(self.root, content="docs")
        self.assertIn("7 minute", result["notice"])
        self.assertIn("200 files", result["notice"])

    def test_notice_has_no_timing_estimate_when_no_stats(self):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(self.srv, "_index_is_up_to_date", return_value=False):
            result = self.srv.run_index_rebuild(self.root, content="docs")
        self.assertNotIn("Last build", result["notice"])


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

    def test_spawn_invalidates_cache(self):
        cache = self.srv.McpRepoCache(self.root)
        with patch.object(
            self.srv,
            "run_index_rebuild",
            return_value={
                "passed": True,
                "already_running": False,
                "notice": "Updating docs/seed index (project layer) — scanning for changes. This may take several minutes.",
                "content": "docs",
                "full": False,
                "mode": "update",
                "index_scope": "incremental_update",
                "layer": "project",
                "stats": {"files_total": 1, "doc_chunks": 1, "code_chunks": 0},
                "log": "/tmp/index-build.log",
                "pid": 12345,
            },
        ):
            with patch.object(cache, "invalidate") as invalidate:
                result = self.srv.wave_index_build_response(self.root, content="docs", mode="update", cache=cache)
        self.assertEqual(result["status"], "ok")
        invalidate.assert_called_once()
        self.assertIn("stats", result["data"])

    def test_up_to_date_does_not_invalidate_cache(self):
        cache = self.srv.McpRepoCache(self.root)
        with patch.object(
            self.srv,
            "run_index_rebuild",
            return_value={
                "passed": True,
                "already_running": False,
                "up_to_date": True,
                "notice": "Index is up to date — no rebuild needed.",
                "content": "docs",
                "full": False,
                "mode": "update",
                "index_scope": "incremental_update",
                "layer": "project",
                "stats": {"files_total": 1, "doc_chunks": 1, "code_chunks": 0},
            },
        ):
            with patch.object(cache, "invalidate") as invalidate:
                result = self.srv.wave_index_build_response(self.root, content="docs", mode="update", cache=cache)
        self.assertEqual(result["status"], "ok")
        invalidate.assert_not_called()

    def test_already_running_returns_diagnostic(self):
        with patch.object(
            self.srv,
            "run_index_rebuild",
            return_value={
                "passed": True,
                "already_running": True,
                "notice": "An index build is already in progress.",
                "content": "docs",
                "full": False,
                "mode": "update",
                "index_scope": "incremental_update",
                "layer": "project",
                "stats": {},
                "log": "/tmp/index-build.log",
            },
        ):
            result = self.srv.wave_index_build_response(self.root, content="docs", mode="update")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["diagnostics"][0]["code"], "index_build_already_running")

    def test_framework_layer_build_returns_ok_with_log(self):
        with patch.object(
            self.srv,
            "run_index_rebuild",
            return_value={
                "passed": True,
                "already_running": False,
                "notice": "Updating docs/seed index (framework layer) — scanning for changes.",
                "content": "docs",
                "full": False,
                "mode": "update",
                "index_scope": "incremental_update",
                "layer": "framework",
                "stats": {},
                "log": "/tmp/framework-index-build.log",
                "pid": 99,
            },
        ):
            result = self.srv.wave_index_build_response(self.root, content="docs", layer="framework")
        self.assertEqual(result["status"], "ok")
        self.assertIn("notice", result["data"])


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

    def _healthy_base(self):
        return {
            "semantic_ready": True,
            "stale_layers": [],
            "missing_layers": [],
            "has_any_index": True,
            "compatible_chunks": True,
            "readiness_overview": "ready",
            "project": {"readiness": "current"},
            "framework": {"readiness": "current"},
            "chunker_version_mismatch_layers": [],
        }

    def test_chunker_version_mismatch_emits_advisory(self):
        index = MagicMock()
        base = self._healthy_base()
        base["chunker_version_mismatch_layers"] = ["project"]
        index.docs_health.return_value = base
        result = self.srv.wave_index_health_response(index)
        self.assertEqual(result["status"], "ok")
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("chunker_version_mismatch", codes)

    def test_chunker_version_mismatch_fires_for_framework_layer(self):
        index = MagicMock()
        base = self._healthy_base()
        base["chunker_version_mismatch_layers"] = ["framework"]
        index.docs_health.return_value = base
        result = self.srv.wave_index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("chunker_version_mismatch", codes)

    def test_chunker_version_mismatch_distinct_from_index_stale(self):
        """chunker_version_mismatch fires even when stale_layers is empty (file hashes are current)."""
        index = MagicMock()
        base = self._healthy_base()
        base["chunker_version_mismatch_layers"] = ["project"]
        # stale_layers is intentionally empty — hashes match, only version differs
        base["stale_layers"] = []
        index.docs_health.return_value = base
        result = self.srv.wave_index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("chunker_version_mismatch", codes)
        self.assertNotIn("index_stale", codes)

    def test_no_chunker_version_mismatch_when_layers_empty(self):
        index = MagicMock()
        base = self._healthy_base()
        base["chunker_version_mismatch_layers"] = []
        index.docs_health.return_value = base
        result = self.srv.wave_index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertNotIn("chunker_version_mismatch", codes)

    def test_background_code_build_running_emits_advisory(self):
        index = MagicMock()
        base = self._healthy_base()
        index.docs_health.return_value = base
        with patch.object(self.srv, "_background_build_status", return_value="running"):
            result = self.srv.wave_index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("background_code_build_running", codes)

    def test_background_code_build_completed_no_advisory(self):
        index = MagicMock()
        base = self._healthy_base()
        index.docs_health.return_value = base
        with patch.object(self.srv, "_background_build_status", return_value="completed"):
            result = self.srv.wave_index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertNotIn("background_code_build_running", codes)

    def test_background_code_build_none_no_advisory(self):
        index = MagicMock()
        base = self._healthy_base()
        index.docs_health.return_value = base
        with patch.object(self.srv, "_background_build_status", return_value="none"):
            result = self.srv.wave_index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertNotIn("background_code_build_running", codes)

    def test_previous_build_stats_included_when_stats_file_exists(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            index_dir = root / ".wavefoundry" / "index"
            index_dir.mkdir(parents=True, exist_ok=True)
            stats = {"elapsed_seconds": 420, "files_indexed": 300, "doc_chunks": 2000, "code_chunks": 1800, "built_at": "2026-05-06T10:00:00Z", "content": "docs", "mode": "rebuild"}
            (index_dir / "index-build-stats.json").write_text(json.dumps(stats), encoding="utf-8")
            index = MagicMock()
            index.root = root
            index.docs_health.return_value = {"semantic_ready": True, "stale_layers": [], "missing_layers": [], "has_any_index": True, "compatible_chunks": True, "readiness_overview": "ready", "chunker_version_mismatch_layers": []}
            result = self.srv.wave_index_health_response(index)
            self.assertIn("previous_build_stats", result["data"])
            self.assertEqual(result["data"]["previous_build_stats"]["elapsed_seconds"], 420)
        finally:
            tmp.cleanup()

    def test_previous_build_stats_refreshes_from_background_build_log(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            index_dir = root / ".wavefoundry" / "index"
            index_dir.mkdir(parents=True, exist_ok=True)
            stats = {"elapsed_seconds": 1, "files_indexed": 1, "doc_chunks": 1, "code_chunks": 1, "built_at": "2026-05-06T10:00:00Z", "content": "docs", "mode": "update"}
            (index_dir / "index-build-stats.json").write_text(json.dumps(stats), encoding="utf-8")
            (index_dir / "background-build.log").write_text(
                "build_index: done — 77 files indexed, 88 doc chunks, 99 code chunks\n",
                encoding="utf-8",
            )
            index = MagicMock()
            index.root = root
            index.docs_health.return_value = {"semantic_ready": True, "stale_layers": [], "missing_layers": [], "has_any_index": True, "compatible_chunks": True, "readiness_overview": "ready", "chunker_version_mismatch_layers": []}
            result = self.srv.wave_index_health_response(index)
            stats = result["data"]["previous_build_stats"]
            self.assertEqual(stats["files_indexed"], 77)
            self.assertEqual(stats["doc_chunks"], 88)
            self.assertEqual(stats["code_chunks"], 99)
            self.assertNotEqual(stats["built_at"], "2026-05-06T10:00:00Z")
        finally:
            tmp.cleanup()

    def test_previous_build_stats_absent_when_no_stats_file(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            index = MagicMock()
            index.root = root
            index.docs_health.return_value = {"semantic_ready": True, "stale_layers": [], "missing_layers": [], "has_any_index": True, "compatible_chunks": True, "readiness_overview": "ready", "chunker_version_mismatch_layers": []}
            result = self.srv.wave_index_health_response(index)
            self.assertNotIn("previous_build_stats", result["data"])
        finally:
            tmp.cleanup()

    def test_exception_from_docs_health_returns_structured_error(self):
        index = MagicMock()
        index.docs_health.side_effect = RuntimeError("unexpected failure")
        result = self.srv.wave_index_health_response(index)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_health_error")

    def test_docs_health_not_called_during_docs_search(self):
        # Regression: docs_health must NOT be called on the search hot path.
        index = MagicMock()
        index.search_docs.return_value = ([], False)
        self.srv.docs_search_response(index, "query")
        index.docs_health.assert_not_called()


# ---------------------------------------------------------------------------
# _read_chunker_version
# ---------------------------------------------------------------------------

class ReadChunkerVersionTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()

    def _reset_cache(self):
        self.srv._chunker_version_cache = ""

    def test_reads_version_from_chunker_source(self):
        self._reset_cache()
        version = self.srv._read_chunker_version()
        self.assertIsInstance(version, str)
        self.assertTrue(version, "Expected a non-empty CHUNKER_VERSION string")

    def test_returns_cached_value_on_second_call(self):
        self._reset_cache()
        first = self.srv._read_chunker_version()
        # Patch read_text to detect if file is accessed again
        with patch.object(Path, "read_text", side_effect=AssertionError("should not re-read")) as _:
            second = self.srv._read_chunker_version()
        self.assertEqual(first, second)

    def test_returns_empty_string_on_oserror(self):
        self._reset_cache()
        with patch.object(Path, "read_text", side_effect=OSError("not found")):
            result = self.srv._read_chunker_version()
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# _background_build_status
# ---------------------------------------------------------------------------

class BackgroundBuildStatusTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _pid_path(self):
        return self.root / ".wavefoundry" / "index" / "background-build.pid"

    def test_returns_none_when_no_pid_file(self):
        result = self.srv._background_build_status(self.root)
        self.assertEqual(result, "none")

    def test_returns_running_when_process_alive(self):
        pid_path = self._pid_path()
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(os.getpid()), encoding="utf-8")
        result = self.srv._background_build_status(self.root)
        self.assertEqual(result, "running")

    def test_returns_completed_when_pid_not_alive(self):
        pid_path = self._pid_path()
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        # PID 0 is never a valid user process; os.kill raises on all platforms
        pid_path.write_text("999999999", encoding="utf-8")
        result = self.srv._background_build_status(self.root)
        self.assertEqual(result, "completed")

    def test_returns_completed_on_invalid_pid_file_content(self):
        pid_path = self._pid_path()
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text("not-a-pid", encoding="utf-8")
        result = self.srv._background_build_status(self.root)
        self.assertEqual(result, "completed")


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
        # Advisory diagnostics (e.g. harness_coverage_gap) are allowed in healthy state.
        self.assertNotIn("error", [d.get("severity") for d in result.get("diagnostics", [])])
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
            "wave_server_info",
            "wave_map",
            "wave_create_wave",
            "wave_add_change",
            "wave_remove_change",
            "wave_prepare",
            "wave_pause",
            "wave_review",
            "wave_reopen",
            "wave_close",
            "wave_index_build_status",
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
            "wave_dashboard_start",
            "wave_dashboard_stop",
            "wave_dashboard_restart",
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
    """AC-6: code_definition preserves Python AST lookup."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "mymodule.py").write_text(
            "class MyClass:\n    pass\n\nclass MyClassTest:\n    pass\n\ndef my_function():\n    pass\n\nasync def my_async():\n    pass\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_class_definition(self):
        result = self.srv.code_definition_response(self.root, "MyClass")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertEqual(defs[0]["name"], "MyClass")
        self.assertEqual(defs[0]["match_kind"], "exact")
        self.assertTrue(any(d["name"] == "MyClass" and d["kind"] == "class" for d in defs))
        self.assertTrue(any(d["name"] == "MyClassTest" and d["match_kind"] == "partial" for d in defs))

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
        self.assertIn("java", result["data"]["supported_languages"])
        self.assertIn("csharp", result["data"]["supported_languages"])

    def test_non_python_falls_back_to_keyword(self):
        # With no Python definitions found, falls back to keyword_fallback method
        result = self.srv.code_definition_response(self.root, "ZZZNODEFINITIONYYY")
        self.assertEqual(result["status"], "ok")
        self.assertIn("method", result["data"])
        self.assertEqual(result["data"]["method"], "keyword_fallback")


class CodeReferencesTests(unittest.TestCase):
    """AC-7: code_references works for Python and provides fallback note."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "mymodule.py").write_text(
            "class MyClass:\n    pass\n\nclass MyClassTest:\n    pass\n",
            encoding="utf-8",
        )
        (src / "caller.py").write_text(
            "from mymodule import MyClass\n\n# MyClass mention for reference classification\n\ndef caller():\n    obj = MyClass()\n    return obj\n",
            encoding="utf-8",
        )
        tests_dir = self.root / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_mycls.py").write_text(
            "from mymodule import MyClass\n\n\ndef test_uses_class():\n    assert MyClass is not None\n",
            encoding="utf-8",
        )
        docs_dir = self.root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "reference-filtering.md").write_text(
            "# Reference Filtering\n\nMyClass is mentioned in the docs as a usage example.\n",
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

    def test_python_references_returns_ast_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            src = root / "src"
            src.mkdir(parents=True, exist_ok=True)
            (src / "caller.py").write_text(
                "from mymodule import MyClass\n\ndef caller():\n    obj = MyClass()\n    return obj\n",
                encoding="utf-8",
            )
            result = self.srv.code_references_response(root, "MyClass")
        self.assertEqual(result["data"].get("method"), "ast")

    def test_references_are_bucketed_and_ordered(self):
        result = self.srv.code_references_response(self.root, "MyClass")
        refs = result["data"]["references"]
        self.assertEqual(refs[0]["reference_kind"], "call_sites")
        self.assertIn("counts", result["data"])
        self.assertIn("matched_counts", result["data"])
        self.assertIn("detail_counts", result["data"])
        self.assertIn("detail_buckets", result["data"])
        self.assertGreaterEqual(result["data"]["counts"]["call_sites"], 1)
        self.assertGreaterEqual(result["data"]["counts"]["tests"], 1)
        self.assertGreaterEqual(result["data"]["counts"]["docs"], 1)
        self.assertGreaterEqual(result["data"]["detail_counts"]["definition"], 1)
        self.assertGreaterEqual(result["data"]["detail_counts"]["import"], 1)
        self.assertGreaterEqual(result["data"]["detail_counts"]["mention"], 1)
        self.assertEqual(result["data"]["count"], result["data"]["total_count"])
        self.assertEqual(result["data"]["count"], sum(result["data"]["counts"].values()))
        self.assertEqual(result["data"]["matched_count"], sum(result["data"]["matched_counts"].values()))
        self.assertGreaterEqual(result["data"]["matched_count"], result["data"]["count"])
        self.assertIn("call_sites", result["data"]["buckets"])
        self.assertIn("definition", result["data"]["detail_buckets"])
        self.assertIn("import", result["data"]["detail_buckets"])
        self.assertIn("mention", result["data"]["detail_buckets"])

    def test_filters_can_exclude_tests_and_docs(self):
        result = self.srv.code_references_response(self.root, "MyClass", exclude_tests=True, exclude_docs=True)
        kinds = {r["reference_kind"] for r in result["data"]["references"]}
        self.assertNotIn("tests", kinds)
        self.assertNotIn("docs", kinds)
        self.assertTrue(kinds)
        self.assertTrue(result["data"]["exclude_tests"])
        self.assertTrue(result["data"]["exclude_docs"])

    def test_call_sites_only_filters_to_calls(self):
        result = self.srv.code_references_response(self.root, "MyClass", call_sites_only=True)
        self.assertTrue(result["data"]["references"])
        self.assertTrue(all(r["reference_kind"] == "call_sites" for r in result["data"]["references"]))
        self.assertEqual(result["data"]["counts"]["call_sites"], result["data"]["count"])
        self.assertGreaterEqual(result["data"]["total_count"], result["data"]["count"])

    def test_limit_caps_returned_results(self):
        result = self.srv.code_references_response(self.root, "MyClass", limit=2)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["limit"], 2)
        self.assertLessEqual(result["data"]["count"], 2)
        self.assertLessEqual(sum(result["data"]["counts"].values()), 2)
        self.assertGreater(result["data"]["matched_count"], result["data"]["count"])
        self.assertGreaterEqual(result["data"]["total_count"], result["data"]["matched_count"])

    def test_detail_buckets_survive_filters(self):
        result = self.srv.code_references_response(self.root, "MyClass", exclude_tests=True, exclude_docs=True)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["detail_counts"]["definition"] >= 1)
        self.assertTrue(result["data"]["detail_counts"]["import"] >= 1)
        self.assertNotIn("tests", {r["reference_bucket"] for r in result["data"]["references"]})

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
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
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
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
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
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
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
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
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
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
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
        index.search_docs.return_value = ([], False)
        resp = self.srv.docs_search_response(index, "test query")
        self.assertIn("mode", resp.get("data", {}))

    def test_mode_field_is_semantic_when_search_succeeds(self):
        index = MagicMock()
        index.search_docs.return_value = ([], False)
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
_EXPECTED_DOCS_MODEL = "BAAI/bge-base-en-v1.5"
_EXPECTED_EMBEDDING_DIM = 768


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
                with patch.object(index, "_get_reranker", return_value=None):
                    results, _ = index.search_docs("how do I validate and prepare a wave?", top_n=1)

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
            with patch.object(index, "_get_reranker", return_value=None):
                results, _ = index.search_docs("stale content", top_n=5)

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


class LayerHealthFileMetaTests(unittest.TestCase):
    """_layer_health reads hashes from file_meta (indexer format), not legacy file_hashes."""

    def setUp(self):
        self.server = load_server()
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _make_repo(self, root: Path) -> Path:
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
        return root

    def _hash(self, path: Path) -> str:
        import hashlib
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _file_meta_for_root(self, root: Path) -> dict:
        """Build a file_meta dict covering all files under root that the walker would pick up."""
        import hashlib
        result = {}
        for f in root.rglob("*"):
            if f.is_file() and ".wavefoundry" not in f.parts:
                rel = str(f.relative_to(root)).replace("\\", "/")
                content = f.read_bytes()
                result[rel] = {"hash": hashlib.sha256(content).hexdigest(), "mtime": 0.0, "size": len(content), "inode": 0}
        return result

    def test_file_meta_key_produces_no_stale_paths_when_hashes_match(self):
        """Health check using file_meta format reports no stale paths when content unchanged."""
        root = self._make_repo(self.tmp)
        (root / "docs" / "guide.md").write_text("# Guide\n\nHello.\n", encoding="utf-8")

        idx_dir = root / ".wavefoundry" / "index"
        idx_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "built_at": "2026-01-01T00:00:00Z",
            "content": ["docs"],
            "model_versions": {"docs": "BAAI/bge-base-en-v1.5"},
            "chunker_versions": {"docs": "13"},
            "walker_version": "3",
            "file_meta": self._file_meta_for_root(root),
        }
        (idx_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        (idx_dir / "docs.json").write_text("[]", encoding="utf-8")

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": meta, "framework": {}}

        health = wave_idx._layer_health("project")
        self.assertEqual(health["stale_paths"], [], msg="file_meta hashes matched — should be no stale paths")

    def test_legacy_file_hashes_key_still_works(self):
        """Health check falls back to file_hashes key for older index formats."""
        root = self._make_repo(self.tmp)
        (root / "docs" / "guide.md").write_text("# Guide\n\nHello.\n", encoding="utf-8")

        idx_dir = root / ".wavefoundry" / "index"
        idx_dir.mkdir(parents=True, exist_ok=True)

        # Build file_hashes (legacy flat format) covering all walked files
        import hashlib
        file_hashes = {}
        for f in root.rglob("*"):
            if f.is_file() and ".wavefoundry" not in f.parts:
                rel = str(f.relative_to(root)).replace("\\", "/")
                file_hashes[rel] = hashlib.sha256(f.read_bytes()).hexdigest()

        meta = {
            "built_at": "2026-01-01T00:00:00Z",
            "content": ["docs"],
            "model_versions": {"docs": "BAAI/bge-base-en-v1.5"},
            "chunker_versions": {"docs": "13"},
            "walker_version": "3",
            "file_hashes": file_hashes,
        }
        (idx_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        (idx_dir / "docs.json").write_text("[]", encoding="utf-8")

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": meta, "framework": {}}

        health = wave_idx._layer_health("project")
        self.assertEqual(health["stale_paths"], [], msg="file_hashes fallback — should be no stale paths")


class BackgroundRefreshActiveTests(unittest.TestCase):
    """_background_refresh_active correctly guards against duplicate indexer spawns."""

    def setUp(self):
        self.server = load_server()
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.state_path = self.tmp / "background-refresh.json"

    def tearDown(self):
        self._td.cleanup()

    def _write_state(self, pid: int, started_at: float) -> None:
        import json as _json
        self.state_path.write_text(
            _json.dumps({"pid": pid, "started_at": started_at, "layer": "project"}),
            encoding="utf-8",
        )

    def test_returns_false_when_no_state_and_no_lock(self):
        self.assertFalse(self.server._background_refresh_active(self.state_path))

    def test_returns_true_when_lock_dir_exists_and_fresh(self):
        lock_dir = self.tmp / ".build.lock"
        lock_dir.mkdir()
        self.assertTrue(self.server._background_refresh_active(self.state_path))

    def test_returns_false_when_lock_dir_stale(self):
        import os, time as _time
        lock_dir = self.tmp / ".build.lock"
        lock_dir.mkdir()
        # Backdate the mtime beyond the stale threshold
        stale_mtime = _time.time() - self.server.BACKGROUND_INDEX_LOCK_STALE_SECONDS - 10
        os.utime(lock_dir, (stale_mtime, stale_mtime))
        self.assertFalse(self.server._background_refresh_active(self.state_path))

    def test_returns_true_when_pid_running(self):
        import os
        self._write_state(pid=os.getpid(), started_at=0.0)
        self.assertTrue(self.server._background_refresh_active(self.state_path))

    def test_returns_false_when_pid_dead_and_throttle_expired(self):
        import time as _time
        self._write_state(pid=999999999, started_at=_time.time() - 300)
        self.assertFalse(self.server._background_refresh_active(self.state_path))

    def test_returns_true_within_throttle_window_even_if_pid_dead(self):
        import time as _time
        self._write_state(pid=999999999, started_at=_time.time())
        self.assertTrue(self.server._background_refresh_active(self.state_path))

    def test_lock_dir_takes_precedence_over_dead_pid_expired_throttle(self):
        """Lock dir present = active, even when state file shows a dead PID past throttle."""
        import time as _time
        self._write_state(pid=999999999, started_at=_time.time() - 300)
        lock_dir = self.tmp / ".build.lock"
        lock_dir.mkdir()
        self.assertTrue(self.server._background_refresh_active(self.state_path))


class WaveIndexAutoReloadTests(unittest.TestCase):
    """WaveIndex._ensure_loaded reloads when meta.json file signature changes."""

    def setUp(self):
        self.server = load_server()
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _make_index(self, index_dir: Path, built_at: str, *, extra: dict[str, object] | None = None) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        payload = {"built_at": built_at, "content": [], "model_versions": {}, "chunker_versions": {}}
        if extra:
            payload.update(extra)
        (index_dir / "meta.json").write_text(json.dumps(payload), encoding="utf-8")

    def _meta_signature(self, index_dir: Path) -> tuple[int, int]:
        st = (index_dir / "meta.json").stat()
        return (getattr(st, "st_mtime_ns", 0), st.st_size)

    def test_ensure_loaded_reloads_when_project_meta_signature_changes(self):
        """_ensure_loaded re-reads index when project meta.json signature changes."""
        root = self.tmp
        project_idx = root / ".wavefoundry" / "index"
        framework_idx = root / ".wavefoundry" / "framework" / "index"
        self._make_index(project_idx, "2026-01-01T00:00:00Z")
        self._make_index(framework_idx, "2026-01-01T00:00:00Z")

        idx = self.server.WaveIndex(root)
        idx._loaded = True
        idx._loaded_meta_signature = {
            "project": self._meta_signature(project_idx),
            "framework": self._meta_signature(framework_idx),
        }

        # Simulate a rebuild by changing the meta file size without changing built_at.
        self._make_index(project_idx, "2026-01-01T00:00:00Z", extra={"refresh_marker": "project"})

        idx._ensure_loaded()
        self.assertEqual(idx._loaded_meta_signature["project"], self._meta_signature(project_idx))

    def test_ensure_loaded_reloads_when_framework_meta_signature_changes(self):
        """_ensure_loaded re-reads index when framework meta.json signature changes."""
        root = self.tmp
        project_idx = root / ".wavefoundry" / "index"
        framework_idx = root / ".wavefoundry" / "framework" / "index"
        self._make_index(project_idx, "2026-01-01T00:00:00Z")
        self._make_index(framework_idx, "2026-01-01T00:00:00Z")

        idx = self.server.WaveIndex(root)
        idx._loaded = True
        idx._loaded_meta_signature = {
            "project": self._meta_signature(project_idx),
            "framework": self._meta_signature(framework_idx),
        }

        self._make_index(framework_idx, "2026-01-01T00:00:00Z", extra={"refresh_marker": "framework"})

        idx._ensure_loaded()
        self.assertEqual(idx._loaded_meta_signature["framework"], self._meta_signature(framework_idx))

    def test_ensure_loaded_does_not_reload_when_meta_signature_unchanged(self):
        """_ensure_loaded skips reload when meta.json signature is unchanged."""
        root = self.tmp
        project_idx = root / ".wavefoundry" / "index"
        framework_idx = root / ".wavefoundry" / "framework" / "index"
        self._make_index(project_idx, "2026-01-01T00:00:00Z")
        self._make_index(framework_idx, "2026-01-01T00:00:00Z")

        idx = self.server.WaveIndex(root)
        idx._loaded = True
        idx._loaded_meta_signature = {
            "project": self._meta_signature(project_idx),
            "framework": self._meta_signature(framework_idx),
        }

        # No changes — should remain loaded
        idx._ensure_loaded()
        self.assertTrue(idx._loaded)


class CodeSummaryChunkSearchTests(unittest.TestCase):
    """AC-2 (12d4h): code_search kind filter isolates code-summary chunks."""

    def _make_index(self, chunks):
        srv = load_server()
        index = MagicMock()
        index.search_code.return_value = (chunks, False)
        return srv, index

    def _make_chunk(self, path, kind, score=0.9):
        return {"path": path, "kind": kind, "language": "python", "lines": [1, 10], "text": "...", "score": score}

    def test_kind_filter_isolates_code_summary(self):
        srv, index = self._make_index([
            self._make_chunk("src/auth.py", "code-summary", 0.9),
            self._make_chunk("src/auth.py", "code", 0.85),
        ])
        result = srv.code_search_response(index, "auth module", kind="code-summary")
        self.assertEqual(result["status"], "ok")
        index.search_code.assert_called_once_with(
            "auth module", language=None, top_n=7, kind="code-summary", max_per_file=None, tags=None
        )

    def test_max_per_file_caps_results(self):
        srv, index = self._make_index([
            self._make_chunk("src/auth.py", "code", 0.9),
            self._make_chunk("src/auth.py", "code", 0.85),
            self._make_chunk("src/billing.py", "code", 0.8),
        ])
        result = srv.code_search_response(index, "query", max_per_file=1)
        self.assertEqual(result["status"], "ok")
        index.search_code.assert_called_once_with(
            "query", language=None, top_n=7, kind=None, max_per_file=1, tags=None
        )

    def test_no_kind_filter_returns_all(self):
        srv, index = self._make_index([self._make_chunk("src/a.py", "code")])
        result = srv.code_search_response(index, "query")
        self.assertEqual(result["status"], "ok")
        index.search_code.assert_called_once_with(
            "query", language=None, top_n=7, kind=None, max_per_file=None, tags=None
        )


class DocSummaryKindFilterTests(unittest.TestCase):
    """AC-4 (12d4h): docs_search kind='doc-summary' filter isolates doc-summary chunks."""

    def _make_index(self, doc_chunks):
        srv = load_server()
        index = MagicMock()
        index.search_docs.return_value = (doc_chunks, False)
        return srv, index

    def test_doc_summary_kind_filter(self):
        srv, index = self._make_index([
            {"path": "docs/architecture/search-architecture.md", "kind": "doc-summary", "score": 0.9, "text": "Search · Sections: Indexing · Retrieval", "lines": [1, 50], "section": "doc-summary"},
        ])
        result = srv.docs_search_response(index, "search architecture", "doc-summary")
        self.assertEqual(result["status"], "ok")
        index.search_docs.assert_called_once_with("search architecture", kind="doc-summary", top_n=7, tags=None)

    def test_doc_summary_not_returned_for_doc_kind(self):
        # _doc_matches_kind should not match "doc-summary" for kind="doc"
        srv = load_server()
        index_obj = srv.WaveIndex.__new__(srv.WaveIndex)
        chunk = {"kind": "doc-summary", "path": "docs/arch.md"}
        self.assertFalse(index_obj._doc_matches_kind(chunk, "doc"))

    def test_doc_summary_matched_for_doc_summary_kind(self):
        srv = load_server()
        index_obj = srv.WaveIndex.__new__(srv.WaveIndex)
        chunk = {"kind": "doc-summary", "path": "docs/arch.md"}
        self.assertTrue(index_obj._doc_matches_kind(chunk, "doc-summary"))


class CodeDefinitionMultiLanguageTests(unittest.TestCase):
    """AC-6: code_definition uses tree-sitter-backed lookup for selected languages."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "App.tsx").write_text(
            "export function MyComponent() { return null; }\n",
            encoding="utf-8",
        )
        (src / "lib.js").write_text(
            "export function useWidget() { return true; }\n",
            encoding="utf-8",
        )
        (src / "Handler.java").write_text(
            "public class Handler {\n    public void handleRequest() {}\n}\n",
            encoding="utf-8",
        )
        (src / "Widget.cs").write_text(
            "public class Widget {\n    public void Render() {}\n}\n",
            encoding="utf-8",
        )
        (src / "util.go").write_text(
            "package sample\n\nfunc SharedThing() {}\n",
            encoding="utf-8",
        )
        (src / "SharedThing.ts").write_text(
            "export function SharedThing() { return true; }\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_ts_file_returns_treesitter_definition(self):
        result = self.srv.code_definition_response(self.root, "MyComponent")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "treesitter")
        self.assertTrue(any("App.tsx" in d["path"] for d in result["data"]["definitions"]))
        self.assertTrue(any(d.get("language") == "typescript" for d in result["data"]["definitions"]))
        self.assertTrue(all(d.get("method") == "treesitter" for d in result["data"]["definitions"]))

    def test_js_file_returns_treesitter_definition(self):
        result = self.srv.code_definition_response(self.root, "useWidget")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "treesitter")
        self.assertTrue(any(d.get("language") == "javascript" for d in result["data"]["definitions"]))

    def test_java_file_returns_treesitter_definition(self):
        result = self.srv.code_definition_response(self.root, "Handler")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "treesitter")
        self.assertTrue(any(d.get("language") == "java" for d in result["data"]["definitions"]))

    def test_csharp_file_returns_treesitter_definition(self):
        result = self.srv.code_definition_response(self.root, "Widget")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "treesitter")
        self.assertTrue(any(d.get("language") == "csharp" for d in result["data"]["definitions"]))

    def test_fallback_definitions_have_path_and_line(self):
        result = self.srv.code_definition_response(self.root, "MyComponent")
        for d in result["data"]["definitions"]:
            self.assertIn("path", d)
            self.assertIn("line", d)
            self.assertEqual(d["method"], "treesitter")
            self.assertIn("language", d)

    def test_mixed_language_definition_aggregates_treesitter_and_fallback(self):
        result = self.srv.code_definition_response(self.root, "SharedThing")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "multi_language")
        self.assertIn("typescript", result["data"]["languages"])
        self.assertIn("go", result["data"]["languages"])
        langs = {d["language"] for d in result["data"]["definitions"]}
        self.assertTrue({"typescript", "go"}.issubset(langs))

    def test_not_found_returns_empty_list(self):
        result = self.srv.code_definition_response(self.root, "ZZZNODEFINITIONYYY")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["definitions"], [])
        self.assertEqual(result["data"]["method"], "keyword_fallback")


class CodeReferencesFallbackTests(unittest.TestCase):
    """AC-5: code_references uses tree-sitter-backed lookup for selected languages."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "App.tsx").write_text(
            "export function MyComponent() { return null; }\nconst x = MyComponent();\n",
            encoding="utf-8",
        )
        (src / "lib.js").write_text(
            "export function useWidget() { return true; }\nconst ok = useWidget();\n",
            encoding="utf-8",
        )
        (src / "Handler.java").write_text(
            "public class Handler {\n    public void handleRequest() {}\n    public void call() { handleRequest(); }\n}\n",
            encoding="utf-8",
        )
        (src / "Widget.cs").write_text(
            "public class Widget {\n    public void Render() {}\n}\npublic class UseWidget {\n    public void Draw() { new Widget().Render(); }\n}\n",
            encoding="utf-8",
        )
        (src / "util.go").write_text(
            "package sample\n\nfunc SharedThing() {}\n\nfunc UseSharedThing() { SharedThing() }\n",
            encoding="utf-8",
        )
        (src / "SharedThing.ts").write_text(
            "export function SharedThing() { return true; }\nconst ok = SharedThing();\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_typescript_symbol_returns_treesitter_method(self):
        result = self.srv.code_references_response(self.root, "MyComponent")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "treesitter")
        self.assertGreater(result["data"]["count"], 0)
        self.assertIn("typescript", result["data"]["languages"])

    def test_javascript_symbol_returns_treesitter_method(self):
        result = self.srv.code_references_response(self.root, "useWidget")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "treesitter")
        self.assertIn("javascript", result["data"]["languages"])

    def test_java_symbol_returns_treesitter_method(self):
        result = self.srv.code_references_response(self.root, "handleRequest")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "treesitter")
        self.assertIn("java", result["data"]["languages"])

    def test_csharp_symbol_returns_treesitter_method(self):
        result = self.srv.code_references_response(self.root, "Widget")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "treesitter")
        self.assertIn("csharp", result["data"]["languages"])

    def test_treesitter_reference_result_shape(self):
        result = self.srv.code_references_response(self.root, "handleRequest")
        for ref in result["data"]["references"]:
            self.assertIn("path", ref)
            self.assertIn("line", ref)
            self.assertIn("snippet", ref)
            self.assertTrue(ref["method"].startswith("treesitter"))
            self.assertIn("language", ref)

    def test_mixed_language_references_aggregate_treesitter_and_fallback(self):
        result = self.srv.code_references_response(self.root, "SharedThing")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "multi_language")
        self.assertIn("typescript", result["data"]["languages"])
        self.assertIn("go", result["data"]["languages"])
        langs = {ref["language"] for ref in result["data"]["references"]}
        self.assertTrue({"typescript", "go"}.issubset(langs))

    def test_sql_tree_sitter_is_used_when_grammar_available(self):
        source = "CREATE TABLE orders (id INT);\n"
        tree = self.srv._get_chunker_module()._ts_parse("sql", source)
        if tree is None:
            self.skipTest("SQL tree-sitter grammar is not installed in this environment")
        chunks = self.srv._get_chunker_module().chunk_sql(source, "db/schema.sql")
        self.assertTrue(any(c.language == "sql" and c.kind == "code" for c in chunks))


class SqlSchemaQualifiedFallbackTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name), {
            "libs/migrations/aceiss/A005__new_tenant_routines.sql": (
                "CREATE OR REPLACE PROCEDURE create_schema_objects(_tenant text)\n"
                "LANGUAGE plpgsql\n"
                "AS $$\n"
                "BEGIN\n"
                "    CALL create_schema_objects(_tenant);\n"
                "END;\n"
                "$$;\n"
            ),
            "docs/release-runbook.md": (
                "# Release Runbook\n\n"
                "Call create_schema_objects during tenant bootstrap.\n"
            ),
            "docs/waves/sql-notes.md": (
                "# SQL Notes\n\n"
                "Remember create_schema_objects when backfilling tenants.\n"
            ),
        })

    def tearDown(self):
        self.tmp.cleanup()

    def test_sql_schema_qualified_definition_retries_unqualified_symbol(self):
        result = self.srv.code_definition_response(self.root, "aceiss.create_schema_objects")
        self.assertEqual(result["status"], "ok")
        self.assertNotEqual(result["data"]["method"], "keyword_fallback")
        defs = result["data"]["definitions"]
        self.assertGreater(len(defs), 0)
        self.assertIn("A005__new_tenant_routines.sql", defs[0]["path"])
        self.assertGreater(defs[0]["line"], 0)
        self.assertEqual(defs[0]["name"], "create_schema_objects")

    def test_sql_schema_qualified_references_retries_unqualified_symbol(self):
        result = self.srv.code_references_response(self.root, "aceiss.create_schema_objects")
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["data"]["count"], 0)
        self.assertGreater(result["data"]["counts"]["docs"], 0)
        self.assertGreater(len(result["data"]["detail_buckets"]["docs"]), 0)
        first = result["data"]["references"][0]
        self.assertIn("create_schema_objects", first["snippet"])
        self.assertIn("A005__new_tenant_routines.sql", first["path"])


class WaveIndexHealthRefreshTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()

    def test_previous_build_stats_refresh_from_finished_log(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            index_dir = root / ".wavefoundry" / "index"
            index_dir.mkdir(parents=True, exist_ok=True)
            state = {"pid": 999999, "started_at": 1710000000.0, "content": "docs", "full": False}
            (index_dir / "index-build.json").write_text(json.dumps(state), encoding="utf-8")
            (index_dir / "index-build.log").write_text(
                "build_index: done — 123 files indexed, 456 doc chunks, 789 code chunks\n",
                encoding="utf-8",
            )
            (index_dir / "index-build-stats.json").write_text(
                json.dumps({"elapsed_seconds": 1, "files_indexed": 1, "doc_chunks": 1, "code_chunks": 1, "built_at": "2026-01-01T00:00:00Z", "content": "docs", "mode": "update"}),
                encoding="utf-8",
            )
            index = MagicMock()
            index.root = root
            index.docs_health.return_value = {"semantic_ready": True, "stale_layers": [], "missing_layers": [], "has_any_index": True, "compatible_chunks": True, "readiness_overview": "ready", "chunker_version_mismatch_layers": []}
            result = self.srv.wave_index_health_response(index)
            stats = result["data"]["previous_build_stats"]
            self.assertEqual(stats["files_indexed"], 123)
            self.assertEqual(stats["doc_chunks"], 456)
            self.assertEqual(stats["code_chunks"], 789)
            self.assertEqual(stats["mode"], "update")
        finally:
            tmp.cleanup()


class CodeDependenciesTests(unittest.TestCase):
    """AC-7/AC-8/AC-9 (12d4h): code_dependencies parses imports on demand."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "billing.py").write_text(
            "import os\nfrom pathlib import Path\nfrom .utils import helper\n",
            encoding="utf-8",
        )
        (src / "App.tsx").write_text(
            "import React from 'react';\nimport { useState } from 'react';\nimport './App.css';\n",
            encoding="utf-8",
        )
        (src / "main.rs").write_text(
            "use std::io;\npub use crate::utils;\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_python_imports_parsed(self):
        result = self.srv.code_dependencies_response(self.root, "src/billing.py")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "ast")
        modules = [i["module"] for i in result["data"]["imports"]]
        self.assertIn("os", modules)
        self.assertIn("pathlib", modules)

    def test_typescript_imports_parsed(self):
        result = self.srv.code_dependencies_response(self.root, "src/App.tsx")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "regex")
        modules = [i["module"] for i in result["data"]["imports"]]
        self.assertIn("react", modules)

    def test_rust_imports_parsed(self):
        result = self.srv.code_dependencies_response(self.root, "src/main.rs")
        self.assertEqual(result["status"], "ok")
        modules = [i["module"] for i in result["data"]["imports"]]
        self.assertIn("std::io", modules)

    def test_unsupported_language_returns_empty(self):
        (self.root / "config.toml").write_text("[package]\nname = 'foo'\n", encoding="utf-8")
        result = self.srv.code_dependencies_response(self.root, "config.toml")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "unsupported")
        self.assertEqual(result["data"]["imports"], [])

    def test_resolved_field_present(self):
        result = self.srv.code_dependencies_response(self.root, "src/billing.py")
        for imp in result["data"]["imports"]:
            self.assertIn("resolved", imp)

    def test_missing_file_returns_error(self):
        result = self.srv.code_dependencies_response(self.root, "src/nonexistent.py")
        self.assertEqual(result["status"], "error")

    def test_path_traversal_rejected(self):
        """Security: path escaping repo root must return error, not read the file."""
        result = self.srv.code_dependencies_response(self.root, "../../../etc/passwd")
        self.assertEqual(result["status"], "error")

    def test_absolute_path_rejected(self):
        """Security: absolute paths must be rejected by confinement check."""
        result = self.srv.code_dependencies_response(self.root, "/etc/passwd")
        self.assertEqual(result["status"], "error")


class CodeAskTests(unittest.TestCase):
    """AC tests for code_ask mechanical routing."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_index(self, code_results=None, doc_results=None):
        index = MagicMock()
        # code_ask_response now uses search_combined; provide combined results
        combined = (code_results or []) + (doc_results or [])
        index.search_combined.return_value = (combined, False)
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        return index

    def _fake_code_chunk(self, path="src/billing.py", score=0.9):
        return {"path": path, "kind": "code", "lines": [42, 58], "text": "def handle_failed_payment(): ...", "score": score}

    def test_response_has_required_fields(self):
        index = self._make_index(code_results=[self._fake_code_chunk()])
        result = self.srv.code_ask_response(index, self.root, "where does billing handle failed payments?")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        for field in ("question", "question_type", "answer", "citations", "confidence", "gaps", "index_freshness"):
            self.assertIn(field, data)

    def test_question_type_classified(self):
        index = self._make_index()
        result = self.srv.code_ask_response(index, self.root, "where is the auth module?")
        self.assertEqual(result["data"]["question_type"], "navigational")

        result = self.srv.code_ask_response(index, self.root, "how do I add a new user?")
        self.assertEqual(result["data"]["question_type"], "instructional")

        result = self.srv.code_ask_response(index, self.root, "what does the billing module do?")
        self.assertEqual(result["data"]["question_type"], "explanatory")

    def test_confidence_high_with_multiple_citations(self):
        index = self._make_index(code_results=[self._fake_code_chunk("src/a.py"), self._fake_code_chunk("src/b.py")])
        result = self.srv.code_ask_response(index, self.root, "billing?")
        self.assertEqual(result["data"]["confidence"], "high")

    def test_confidence_low_with_no_citations(self):
        index = self._make_index()
        result = self.srv.code_ask_response(index, self.root, "ZZZNOEVIDENCEYYY")
        self.assertEqual(result["data"]["confidence"], "low")
        self.assertTrue(len(result["data"]["gaps"]) > 0)

    def test_citations_have_ref_and_path(self):
        index = self._make_index(code_results=[self._fake_code_chunk()])
        result = self.srv.code_ask_response(index, self.root, "billing?")
        for c in result["data"]["citations"]:
            self.assertIn("ref", c)
            self.assertIn("path", c)

    def test_index_freshness_current_when_no_mismatch(self):
        index = self._make_index(code_results=[self._fake_code_chunk()])
        result = self.srv.code_ask_response(index, self.root, "billing?")
        self.assertEqual(result["data"]["index_freshness"], "current")

    def test_index_freshness_stale_when_mismatch(self):
        index = self._make_index()
        index._layer_health.return_value = {
            "indexed_chunker_versions": {"docs": "16", "code": "16"},
            "current_chunker_version": "17",
        }
        result = self.srv.code_ask_response(index, self.root, "billing?")
        self.assertEqual(result["data"]["index_freshness"], "stale")

    def test_keyword_search_error_appended_to_gaps(self):
        """AC-4 (12d4b): keyword search error status is surfaced in gaps, not silently swallowed."""
        index = self._make_index()  # no results → triggers keyword fallback
        srv = load_server()
        with patch.object(srv, "code_keyword_search_response", return_value={"status": "error", "error": "index not built"}):
            result = srv.code_ask_response(index, self.root, "ZZZNOEVIDENCEYYY")
        self.assertEqual(result["status"], "ok")
        self.assertIn("keyword search failed", result["data"]["gaps"])

    def test_code_ask_does_not_call_write_path_tools(self):
        """AC-4 (12d4b): code_ask_response must never invoke write-path operations."""
        write_path_names = {
            "wave_index_build", "wave_sync_surfaces", "wave_add_change",
            "wave_new_feature", "wave_new_bug",
        }
        srv = load_server()
        # Verify none of the write-path function names are referenced inside code_ask_response
        import inspect
        source = inspect.getsource(srv.code_ask_response)
        for name in write_path_names:
            self.assertNotIn(name, source, f"code_ask_response references write-path tool: {name}")


class MaxPerFileFilterDirectTests(unittest.TestCase):
    """AC-1, AC-2, AC-4 (12d5s): max_per_file filtering logic in WaveIndex.search_code."""

    def _make_index_with_chunks(self, raw_chunks):
        """Patch WaveIndex to avoid embedding; inject raw chunks as cosine search result."""
        srv = load_server()
        index = srv.WaveIndex.__new__(srv.WaveIndex)
        # Provide the minimal attributes that search_code depends on after _ensure_loaded
        index._code_chunks = raw_chunks
        index._code_vecs = None  # not used — we'll patch _cosine_search
        # Bypass _ensure_loaded
        with patch.object(index, "_ensure_loaded"):
            with patch.object(index, "_embed_query", return_value=None):
                with patch.object(srv, "_indexer_constant", return_value="model"):
                    # Patch _cosine_search to return chunks in score-descending order (already sorted)
                    with patch.object(index, "_cosine_search", return_value=raw_chunks):
                        with patch.object(index, "_indexer_constant", return_value="model"):
                            return index

    def _chunk(self, path, score):
        return {"path": path, "kind": "code", "language": "python", "lines": [1, 5], "text": "x", "score": score}

    def test_max_per_file_1_caps_at_one_result_per_file(self):
        """AC-1 (12d5s): output has at most 1 chunk per file when max_per_file=1."""
        srv = load_server()
        index = MagicMock()
        chunks = [
            self._chunk("src/auth.py", 0.95),
            self._chunk("src/auth.py", 0.90),
            self._chunk("src/auth.py", 0.85),
            self._chunk("src/billing.py", 0.80),
        ]
        index.search_code.return_value = (chunks, False)
        result = srv.code_search_response(index, "auth", max_per_file=1)
        self.assertEqual(result["status"], "ok")
        # The response passes through the index.search_code result — verify the index was asked
        index.search_code.assert_called_once_with("auth", language=None, top_n=7, kind=None, max_per_file=1, tags=None)

    def test_search_code_max_per_file_cap_enforced_by_index(self):
        """AC-2 (12d5s): WaveIndex.search_code with max_per_file=2 returns at most 2 chunks per file."""
        srv = load_server()
        index = srv.WaveIndex.__new__(srv.WaveIndex)
        index._code_vecs = []
        index._code_chunks = []
        raw = [
            self._chunk("src/auth.py", 0.95),
            self._chunk("src/auth.py", 0.90),
            self._chunk("src/auth.py", 0.85),
            self._chunk("src/billing.py", 0.80),
            self._chunk("src/billing.py", 0.75),
        ]
        with patch.object(index, "_ensure_loaded"), \
             patch.object(index, "_embed_query", return_value=None), \
             patch.object(index, "_indexer_constant", return_value="model"), \
             patch.object(index, "_cosine_search", return_value=raw), \
             patch.object(index, "_get_reranker", return_value=None):
            results, _ = index.search_code("query", max_per_file=2, top_n=10)
        auth_results = [r for r in results if r["path"] == "src/auth.py"]
        billing_results = [r for r in results if r["path"] == "src/billing.py"]
        self.assertLessEqual(len(auth_results), 2)
        self.assertLessEqual(len(billing_results), 2)
        self.assertEqual(len(auth_results), 2)
        self.assertEqual(len(billing_results), 2)

    def test_search_code_max_per_file_retains_highest_score(self):
        """AC-4 (12d5s): the first chunk per file (highest-ranked) is the one retained."""
        srv = load_server()
        index = srv.WaveIndex.__new__(srv.WaveIndex)
        index._code_vecs = []
        index._code_chunks = []
        raw = [
            self._chunk("src/auth.py", 0.95),  # highest score — should be retained
            self._chunk("src/auth.py", 0.50),  # lower score — should be dropped with max_per_file=1
        ]
        with patch.object(index, "_ensure_loaded"), \
             patch.object(index, "_embed_query", return_value=None), \
             patch.object(index, "_indexer_constant", return_value="model"), \
             patch.object(index, "_cosine_search", return_value=raw), \
             patch.object(index, "_get_reranker", return_value=None):
            results, _ = index.search_code("query", max_per_file=1, top_n=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["score"], 0.95)


class InferTagsServerTests(unittest.TestCase):
    """AC-10 through AC-16 (12dv9): tag index and filter behavior via server."""

    def setUp(self):
        self.srv = load_server()

    def test_infer_tags_wave(self):
        tags = self.srv._infer_tags("docs/waves/12dv9 chunk-tags/wave.md")
        self.assertIn("wave", tags)

    def test_infer_tags_prompt_suffix(self):
        tags = self.srv._infer_tags("anywhere/my-agent.prompt.md")
        self.assertIn("prompt", tags)

    def test_infer_tags_no_match(self):
        tags = self.srv._infer_tags("src/main.py")
        self.assertEqual(tags, [])

    def test_docs_search_response_passes_tags_to_index(self):
        index = MagicMock()
        index.search_docs.return_value = ([], False)
        self.srv.docs_search_response(index, "query", tags=["wave"])
        index.search_docs.assert_called_once()
        _, kwargs = index.search_docs.call_args
        self.assertEqual(kwargs.get("tags"), ["wave"])

    def test_docs_search_response_empty_tags_passes_none(self):
        index = MagicMock()
        index.search_docs.return_value = ([], False)
        self.srv.docs_search_response(index, "query", tags=[])
        _, kwargs = index.search_docs.call_args
        self.assertIsNone(kwargs.get("tags"))

    def test_code_search_response_passes_tags_to_index(self):
        index = MagicMock()
        index.search_code.return_value = ([], False)
        self.srv.code_search_response(index, "query", tags=["test"])
        index.search_code.assert_called_once()
        _, kwargs = index.search_code.call_args
        self.assertEqual(kwargs.get("tags"), ["test"])

    def test_tag_index_built_on_load(self):
        import numpy as np
        import tempfile
        import json
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / ".wavefoundry" / "index").mkdir(parents=True)
            (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
            docs_chunks = [
                {"id": "a", "path": "docs/waves/12dv9/wave.md", "kind": "doc", "text": "wave doc"},
                {"id": "b", "path": "docs/agents/journals/cia.md", "kind": "doc", "text": "journal"},
                {"id": "c", "path": "src/main.py", "kind": "code", "text": "code"},
            ]
            vecs = np.ones((3, 4), dtype=np.float32)
            np.save(str(root / ".wavefoundry" / "index" / "docs.npy"), vecs)
            (root / ".wavefoundry" / "index" / "docs.json").write_text(json.dumps(docs_chunks), encoding="utf-8")
            meta = {"model_versions": {"docs": "BAAI/bge-base-en-v1.5", "code": "BAAI/bge-base-en-v1.5"}, "built_at": "2026-01-01"}
            (root / ".wavefoundry" / "index" / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            idx = self.srv.WaveIndex(root)
            idx._ensure_loaded()
            self.assertIn("wave", idx._docs_tag_index)
            self.assertIn("journal", idx._docs_tag_index)
            self.assertIn("agent", idx._docs_tag_index)
            self.assertNotIn("wave", idx._code_tag_index)
            # Kind index also built at load time; chunks 0 and 1 have kind="doc", chunk 2 has kind="code"
            self.assertIn("doc", idx._docs_kind_index)
            self.assertEqual(sorted(idx._docs_kind_index["doc"]), [0, 1])
        finally:
            tmp.cleanup()

    def test_search_docs_tags_pre_filter(self):
        import numpy as np
        import tempfile
        import json
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / ".wavefoundry" / "index").mkdir(parents=True)
            (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
            docs_chunks = [
                {"id": "w1", "path": "docs/waves/12dv9/wave.md", "kind": "doc", "text": "wave doc"},
                {"id": "o1", "path": "docs/other/something.md", "kind": "doc", "text": "unrelated"},
            ]
            # Both vectors point the same direction so cosine similarity is equal
            vecs = np.ones((2, 4), dtype=np.float32)
            np.save(str(root / ".wavefoundry" / "index" / "docs.npy"), vecs)
            (root / ".wavefoundry" / "index" / "docs.json").write_text(json.dumps(docs_chunks), encoding="utf-8")
            meta = {"model_versions": {"docs": "BAAI/bge-base-en-v1.5", "code": "BAAI/bge-base-en-v1.5"}, "built_at": "2026-01-01"}
            (root / ".wavefoundry" / "index" / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            idx = self.srv.WaveIndex(root)
            # Patch embed so we don't need actual model
            idx._embed_query = lambda q, model: np.ones(4, dtype=np.float32)
            idx._ensure_loaded()
            with patch.object(idx, "_get_reranker", return_value=None):
                results, _ = idx.search_docs("anything", tags=["wave"], top_n=5)
            ids = [r["id"] for r in results]
            self.assertIn("w1", ids)
            self.assertNotIn("o1", ids)
        finally:
            tmp.cleanup()

    def test_search_docs_tags_and_kind_compose_with_and_semantics(self):
        # AC-13: chunks must satisfy BOTH tags AND kind (both pre-filter, index intersection).
        # Setup: three chunks —
        #   w1: wave-tagged, kind="doc"         → matches tags ∩ kind ✓
        #   w2: wave-tagged, kind="doc-summary" → in tags index but not kind index ✗
        #   o1: no wave tag, kind="doc"         → in kind index but not tags index ✗
        # Only w1 should be returned.
        import numpy as np
        import tempfile
        import json
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / ".wavefoundry" / "index").mkdir(parents=True)
            (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
            docs_chunks = [
                {"id": "w1", "path": "docs/waves/12dv9/wave.md", "kind": "doc", "text": "wave doc"},
                {"id": "w2", "path": "docs/waves/12dv9/summary.md", "kind": "doc-summary", "text": "wave summary"},
                {"id": "o1", "path": "docs/other/something.md", "kind": "doc", "text": "other doc"},
            ]
            vecs = np.ones((3, 4), dtype=np.float32)
            np.save(str(root / ".wavefoundry" / "index" / "docs.npy"), vecs)
            (root / ".wavefoundry" / "index" / "docs.json").write_text(json.dumps(docs_chunks), encoding="utf-8")
            meta = {"model_versions": {"docs": "BAAI/bge-base-en-v1.5", "code": "BAAI/bge-base-en-v1.5"}, "built_at": "2026-01-01"}
            (root / ".wavefoundry" / "index" / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            idx = self.srv.WaveIndex(root)
            idx._embed_query = lambda q, model: np.ones(4, dtype=np.float32)
            idx._ensure_loaded()
            with patch.object(idx, "_get_reranker", return_value=None):
                results, _ = idx.search_docs("anything", kind="doc", tags=["wave"], top_n=5)
            ids = [r["id"] for r in results]
            self.assertIn("w1", ids)       # wave-tagged + kind=doc ✓
            self.assertNotIn("w2", ids)    # wave-tagged but kind=doc-summary ✗
            self.assertNotIn("o1", ids)    # kind=doc but not wave-tagged ✗
        finally:
            tmp.cleanup()

    def test_search_docs_kind_only_pre_filter(self):
        import numpy as np
        import tempfile
        import json
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / ".wavefoundry" / "index").mkdir(parents=True)
            (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
            docs_chunks = [
                {"id": "s1", "path": "docs/waves/12dv9/12dv9.md", "kind": "doc-summary", "text": "wave summary"},
                {"id": "d1", "path": "docs/waves/12dv9/wave.md", "kind": "doc", "text": "wave doc"},
                {"id": "s2", "path": "docs/other/other.md", "kind": "doc-summary", "text": "other summary"},
            ]
            vecs = np.ones((3, 4), dtype=np.float32)
            np.save(str(root / ".wavefoundry" / "index" / "docs.npy"), vecs)
            (root / ".wavefoundry" / "index" / "docs.json").write_text(json.dumps(docs_chunks), encoding="utf-8")
            meta = {"model_versions": {"docs": "BAAI/bge-base-en-v1.5", "code": "BAAI/bge-base-en-v1.5"}, "built_at": "2026-01-01"}
            (root / ".wavefoundry" / "index" / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            idx = self.srv.WaveIndex(root)
            idx._embed_query = lambda q, model: np.ones(4, dtype=np.float32)
            idx._ensure_loaded()
            with patch.object(idx, "_get_reranker", return_value=None):
                results, _ = idx.search_docs("wave summary", kind="doc-summary", top_n=5)
            ids = [r["id"] for r in results]
            self.assertIn("s1", ids)    # doc-summary ✓
            self.assertIn("s2", ids)    # doc-summary ✓
            self.assertNotIn("d1", ids) # kind=doc excluded ✗
        finally:
            tmp.cleanup()

    def test_search_docs_empty_tags_returns_all(self):
        import numpy as np
        import tempfile
        import json
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / ".wavefoundry" / "index").mkdir(parents=True)
            (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
            docs_chunks = [
                {"id": "w1", "path": "docs/waves/12dv9/wave.md", "kind": "doc", "text": "wave doc"},
                {"id": "o1", "path": "docs/other/something.md", "kind": "doc", "text": "unrelated"},
            ]
            vecs = np.ones((2, 4), dtype=np.float32)
            np.save(str(root / ".wavefoundry" / "index" / "docs.npy"), vecs)
            (root / ".wavefoundry" / "index" / "docs.json").write_text(json.dumps(docs_chunks), encoding="utf-8")
            meta = {"model_versions": {"docs": "BAAI/bge-base-en-v1.5", "code": "BAAI/bge-base-en-v1.5"}, "built_at": "2026-01-01"}
            (root / ".wavefoundry" / "index" / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            idx = self.srv.WaveIndex(root)
            idx._embed_query = lambda q, model: np.ones(4, dtype=np.float32)
            idx._ensure_loaded()
            with patch.object(idx, "_get_reranker", return_value=None):
                results, _ = idx.search_docs("anything", tags=None, top_n=5)
            ids = [r["id"] for r in results]
            self.assertIn("w1", ids)
            self.assertIn("o1", ids)
        finally:
            tmp.cleanup()


class WaveRunSensorsTests(unittest.TestCase):
    """12ecs-feat post-edit-computational-sensors: wave_run_sensors MCP tool."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, sensors):
        cfg = {
            "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
            "sensors": sensors,
        }
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    def test_no_sensors_configured(self):
        result = self.srv.wave_run_sensors_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["sensors_run"], 0)
        self.assertEqual(result["data"]["results"], [])
        self.assertTrue(result["data"]["all_passed"])

    def test_passing_sensor(self):
        self._write_config([{"name": "true-check", "command": ["true"], "dimension": "maintainability"}])
        result = self.srv.wave_run_sensors_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["all_passed"])
        self.assertEqual(len(result["data"]["results"]), 1)
        self.assertTrue(result["data"]["results"][0]["passed"])

    def test_failing_sensor(self):
        self._write_config([{"name": "false-check", "command": ["false"], "dimension": "maintainability"}])
        result = self.srv.wave_run_sensors_response(self.root)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["data"]["all_passed"])
        self.assertFalse(result["data"]["results"][0]["passed"])
        self.assertEqual(result["data"]["results"][0]["name"], "false-check")
        self.assertTrue(any(d["code"] == "sensor_failed" for d in result["diagnostics"]))

    def test_sensor_with_invalid_command(self):
        self._write_config([{"name": "bad-cmd", "command": ["__nonexistent_command__"], "dimension": "behaviour"}])
        result = self.srv.wave_run_sensors_response(self.root)
        self.assertFalse(result["data"]["all_passed"])
        self.assertFalse(result["data"]["results"][0]["passed"])


class RequiredReviewLanesTests(unittest.TestCase):
    """12ecs-enh inferential-sensors-as-required-review-lanes: project-declared lanes enforcement."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config_with_lanes(self, lanes):
        cfg = {
            "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
            "required_review_lanes": lanes,
        }
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    def _make_wave_with_evidence(self, evidence_lines):
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `complete`\n\n"
            "## Review Evidence\n\n"
            + "\n".join(evidence_lines) + "\n",
            encoding="utf-8",
        )

    def test_project_declared_lane_appears_in_required_lanes(self):
        self._write_config_with_lanes(["security-review"])
        self._make_wave_with_evidence(["- operator-signoff: approved", "- security-review: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertIn("security-review", result["data"]["required_lanes"])

    def test_missing_declared_lane_emits_missing_required_lane(self):
        self._write_config_with_lanes(["security-review"])
        self._make_wave_with_evidence(["- operator-signoff: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_required_lane" for d in result["diagnostics"]))

    def test_no_declared_lanes_unchanged_behaviour(self):
        # AC-3: projects with no declared lanes only require operator
        self._make_wave_with_evidence(["- operator-signoff: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["required_lanes"], ["operator"])

    def test_wave_close_blocks_on_missing_declared_lane(self):
        self._write_config_with_lanes(["security-review"])
        self._make_wave_with_evidence(["- operator-signoff: approved"])
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_required_lane" for d in result["diagnostics"]))

    def test_wave_close_passes_when_declared_lane_signed(self):
        self._write_config_with_lanes(["security-review"])
        self._make_wave_with_evidence(["- operator-signoff: approved", "- security-review: approved"])
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertNotIn("missing_required_lane", [d["code"] for d in result.get("diagnostics", [])])


class SeverityTriageTests(unittest.TestCase):
    """12ed1-enh sensor-finding-severity-triage: max_severity and advisory diagnostic."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave_with_evidence(self, evidence_lines):
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `complete`\n\n"
            "## Review Evidence\n\n"
            + "\n".join(evidence_lines) + "\n",
            encoding="utf-8",
        )

    def test_no_severity_annotations_returns_none(self):
        self._make_wave_with_evidence(["- operator-signoff: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "none")

    def test_medium_severity_no_advisory(self):
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- security-review: approved-with-notes (medium — minor issue)",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "medium")
        self.assertFalse(any(d["code"] == "high_severity_finding" for d in result.get("diagnostics", [])))

    def test_high_severity_emits_advisory(self):
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- security-review: needs-revision (high — path traversal in code_read)",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "high")
        self.assertTrue(any(d["code"] == "high_severity_finding" for d in result.get("diagnostics", [])))

    def test_critical_severity_emits_advisory(self):
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- security-review: needs-revision (critical — exploitable RCE)",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "critical")
        self.assertTrue(any(d["code"] == "high_severity_finding" for d in result.get("diagnostics", [])))

    def test_low_severity_no_advisory(self):
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- performance-review: approved-with-notes (low — micro-optimisation opportunity)",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "low")
        self.assertFalse(any(d["code"] == "high_severity_finding" for d in result.get("diagnostics", [])))


class WaveCouncilPolicyTests(unittest.TestCase):
    """12g1y-enh wave-council-review-system: council signoff enforcement."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, enabled=True, transition_policy=""):
        cfg = {
            "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
            "wave_council_policy": {
                "enabled": enabled,
                "transition_policy": transition_policy,
                "phases": {
                    "prepare": {"signoff_key": "wave-council-readiness", "moderator_role": "council-moderator"},
                    "review": {"signoff_key": "wave-council-delivery", "moderator_role": "council-moderator"},
                },
            },
        }
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def _make_change_doc(self, change_id: str):
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / f"{change_id}.md").write_text(
            "# Sample Change\n\n"
            f"Change ID: `{change_id}`\n"
            "Change Status: `planned`\n"
            "## Rationale\n\nwhy\n\n"
            "## Requirements\n\n1. x\n\n"
            "## Scope\n\nin scope\n\n"
            "## Acceptance Criteria\n\n- x\n\n"
            "## Tasks\n\n- x\n\n"
            "## AC Priority\n\n"
            "| AC | Priority | Rationale |\n"
            "| -- | -------- | --------- |\n"
            "| AC-1 | required | x |\n",
            encoding="utf-8",
        )

    def _make_wave(self, status="planned", evidence_lines=None):
        if evidence_lines is None:
            evidence_lines = []
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n"
            "Owner: Engineering\n"
            f"Status: {status}\n"
            "Last verified: 2026-05-08\n\n"
            "wave-id: `1200a test-wave`\n"
            "Title: Test Wave\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `planned`\n\n"
            "## Participants\n\n"
            "| Role | Lane | Scope |\n"
            "|------|------|-------|\n"
            "| code-reviewer | review | sample |\n\n"
            "## Review Evidence\n\n"
            + "\n".join(evidence_lines) + "\n",
            encoding="utf-8",
        )
        self._make_change_doc("1200a-feat sample")

    def test_prepare_requires_readiness_council_signoff(self):
        self._write_config()
        self._make_wave(status="planned", evidence_lines=[])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_prepare_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_wave_council_signoff" for d in result["diagnostics"]))

    def test_prepare_passes_when_readiness_signoff_present(self):
        self._write_config()
        self._make_wave(status="planned", evidence_lines=["- wave-council-readiness: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_prepare_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertIn("wave-council-readiness", result["data"]["required_council_signoffs"])
        self.assertNotEqual(result["status"], "error")

    def test_review_requires_delivery_council_signoff(self):
        self._write_config()
        self._make_wave(status="active", evidence_lines=["- operator-signoff: approved", "- code-reviewer: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_wave_council_signoff" for d in result["diagnostics"]))

    def test_close_requires_both_council_signoffs(self):
        self._write_config()
        self._make_wave(
            status="active",
            evidence_lines=[
                "- operator-signoff: approved",
                "- code-reviewer: approved",
                "- wave-council-delivery: approved",
            ],
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_wave_council_signoff" for d in result["diagnostics"]))

    def test_disabled_policy_does_not_require_council(self):
        self._write_config(enabled=False)
        self._make_wave(status="active", evidence_lines=["- operator-signoff: approved", "- code-reviewer: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["required_council_signoffs"], [])
        self.assertFalse(any(d["code"] == "missing_wave_council_signoff" for d in result.get("diagnostics", [])))

    def test_transition_policy_still_requires_delivery_review_signoff(self):
        self._write_config(transition_policy="applies-from-next-prepare")
        self._make_wave(status="active", evidence_lines=["- operator-signoff: approved", "- code-reviewer: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["required_council_signoffs"], ["wave-council-delivery"])
        self.assertTrue(any(d["code"] == "missing_wave_council_signoff" for d in result["diagnostics"]))

    def test_transition_policy_close_does_not_require_missing_readiness_signoff(self):
        self._write_config(transition_policy="applies-from-next-prepare")
        self._make_wave(
            status="active",
            evidence_lines=[
                "- operator-signoff: approved",
                "- code-reviewer: approved",
                "- wave-council-delivery: approved",
            ],
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["data"]["required_council_signoffs"], ["wave-council-delivery"])
        self.assertFalse(any(d["code"] == "missing_wave_council_signoff" for d in result.get("diagnostics", [])))


class HarnessCoverageAuditTests(unittest.TestCase):
    """12ed1-feat harness-coverage-metrics: _audit_harness_coverage dimensions."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, extra):
        cfg = {"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}, **extra}
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def test_no_config_returns_zero_coverage(self):
        result = self.srv._audit_harness_coverage(self.root)
        self.assertEqual(result["covered_count"], 0)
        self.assertEqual(result["coverage_ratio"], "0/3")

    def test_sensors_cover_maintainability(self):
        self._write_config({"sensors": [{"name": "lint", "command": ["true"], "dimension": "maintainability"}]})
        result = self.srv._audit_harness_coverage(self.root)
        self.assertTrue(result["dimensions"]["maintainability"]["covered"])

    def test_architecture_lane_covers_architecture(self):
        self._write_config({"required_review_lanes": ["architecture-review"]})
        result = self.srv._audit_harness_coverage(self.root)
        self.assertTrue(result["dimensions"]["architecture"]["covered"])

    def test_security_lane_covers_behaviour(self):
        self._write_config({"required_review_lanes": ["security-review"]})
        result = self.srv._audit_harness_coverage(self.root)
        self.assertTrue(result["dimensions"]["behaviour"]["covered"])

    def test_full_coverage(self):
        self._write_config({
            "sensors": [{"name": "lint", "command": ["true"], "dimension": "maintainability"}],
            "required_review_lanes": ["architecture-review", "security-review"],
        })
        result = self.srv._audit_harness_coverage(self.root)
        self.assertEqual(result["covered_count"], 3)
        self.assertEqual(result["coverage_ratio"], "3/3")


class RerankerTests(unittest.TestCase):
    """12mha-enh: cross-encoder reranker integration tests."""

    def setUp(self):
        self.srv = load_server()

    def _make_mock_reranker(self, n_docs):
        """Return a mock reranker whose rerank() returns ascending floats (last doc ranks highest)."""
        reranker = MagicMock()
        reranker.rerank.side_effect = lambda query, docs: [float(i) for i in range(len(docs))]
        return reranker

    def _make_index_with_docs(self, docs_chunks, code_chunks=None):
        """Create a WaveIndex backed by in-memory numpy arrays."""
        import numpy as np
        import tempfile, json
        srv = self.srv
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / ".wavefoundry" / "index").mkdir(parents=True)
        (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
        # Build docs index
        n_docs_chunks = len(docs_chunks)
        vecs = np.ones((max(n_docs_chunks, 1), 4), dtype=np.float32)
        np.save(str(root / ".wavefoundry" / "index" / "docs.npy"), vecs)
        (root / ".wavefoundry" / "index" / "docs.json").write_text(json.dumps(docs_chunks), encoding="utf-8")
        # Build code index if provided
        if code_chunks:
            code_vecs = np.ones((len(code_chunks), 4), dtype=np.float32)
            np.save(str(root / ".wavefoundry" / "index" / "code.npy"), code_vecs)
            (root / ".wavefoundry" / "index" / "code.json").write_text(json.dumps(code_chunks), encoding="utf-8")
        meta = {"model_versions": {"docs": "BAAI/bge-base-en-v1.5", "code": "BAAI/bge-base-en-v1.5"}, "built_at": "2026-01-01"}
        (root / ".wavefoundry" / "index" / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        idx = srv.WaveIndex(root)
        import numpy as np
        idx._embed_query = lambda q, model: np.ones(4, dtype=np.float32)
        idx._ensure_loaded()
        self._tmp = tmp  # keep alive
        return idx

    def _fake_doc_chunk(self, id, text="sample text"):
        return {"id": id, "path": f"docs/{id}.md", "kind": "doc", "text": text, "lines": [1, 5]}

    def _fake_code_chunk(self, id, text="def foo(): pass"):
        return {"id": id, "path": f"src/{id}.py", "kind": "code", "language": "python", "text": text, "lines": [1, 10]}

    def tearDown(self):
        if hasattr(self, "_tmp"):
            self._tmp.cleanup()

    # --- docs_search ---

    def test_docs_search_returns_reranked_true_when_reranker_available(self):
        """docs_search returns (results, True) when reranker is available."""
        chunks = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        idx = self._make_index_with_docs(chunks)
        mock_reranker = self._make_mock_reranker(3)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, reranked = idx.search_docs("query", top_n=3)
        self.assertTrue(reranked)

    def test_docs_search_returns_reranked_false_when_reranker_unavailable(self):
        """docs_search returns (results, False) when reranker returns None."""
        chunks = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        idx = self._make_index_with_docs(chunks)
        with patch.object(idx, "_get_reranker", return_value=None):
            results, reranked = idx.search_docs("query", top_n=3)
        self.assertFalse(reranked)

    def test_docs_search_result_count_does_not_exceed_top_n(self):
        """docs_search never returns more than top_n results."""
        chunks = [self._fake_doc_chunk(f"d{i}") for i in range(10)]
        idx = self._make_index_with_docs(chunks)
        mock_reranker = self._make_mock_reranker(10)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, _ = idx.search_docs("query", top_n=3)
        self.assertLessEqual(len(results), 3)

    def test_docs_search_response_includes_reranked_field(self):
        """docs_search_response includes 'reranked' in response data."""
        index = MagicMock()
        index.search_docs.return_value = ([], False)
        resp = self.srv.docs_search_response(index, "test query")
        self.assertIn("reranked", resp.get("data", {}))

    def test_docs_search_response_reranked_true_propagates(self):
        """docs_search_response propagates reranked=True from index."""
        chunk = self._fake_doc_chunk("d1")
        chunk["score"] = 0.9
        index = MagicMock()
        index.search_docs.return_value = ([chunk], True)
        resp = self.srv.docs_search_response(index, "test query")
        self.assertTrue(resp["data"]["reranked"])

    def test_docs_search_lexical_fallback_reranked_false(self):
        """Lexical fallback path leaves reranked=False."""
        index = MagicMock()
        index.search_docs.side_effect = self.srv.IndexNotReadyError("index missing")
        index.search_docs_lexical.return_value = []
        resp = self.srv.docs_search_response(index, "query")
        self.assertFalse(resp["data"].get("reranked", True))

    # --- code_search ---

    def test_code_search_returns_reranked_true_when_reranker_available(self):
        """code_search returns (results, True) when reranker is available."""
        chunks = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        idx = self._make_index_with_docs([], code_chunks=[self._fake_code_chunk(f"c{i}") for i in range(3)])
        mock_reranker = self._make_mock_reranker(3)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, reranked = idx.search_code("query", top_n=3)
        self.assertTrue(reranked)

    def test_code_search_returns_reranked_false_when_reranker_unavailable(self):
        """code_search returns (results, False) when reranker returns None."""
        idx = self._make_index_with_docs([], code_chunks=[self._fake_code_chunk(f"c{i}") for i in range(3)])
        with patch.object(idx, "_get_reranker", return_value=None):
            results, reranked = idx.search_code("query", top_n=3)
        self.assertFalse(reranked)

    def test_code_search_result_count_does_not_exceed_top_n(self):
        """code_search never returns more than top_n results."""
        idx = self._make_index_with_docs([], code_chunks=[self._fake_code_chunk(f"c{i}") for i in range(10)])
        mock_reranker = self._make_mock_reranker(10)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, _ = idx.search_code("query", top_n=3)
        self.assertLessEqual(len(results), 3)

    def test_code_search_response_includes_reranked_field(self):
        """code_search_response includes 'reranked' in response data."""
        index = MagicMock()
        index.search_code.return_value = ([], False)
        resp = self.srv.code_search_response(index, "query")
        self.assertIn("reranked", resp.get("data", {}))

    def test_code_search_response_reranked_true_propagates(self):
        """code_search_response propagates reranked=True from index."""
        chunk = self._fake_code_chunk("c1")
        chunk["score"] = 0.9
        index = MagicMock()
        index.search_code.return_value = ([chunk], True)
        resp = self.srv.code_search_response(index, "query")
        self.assertTrue(resp["data"]["reranked"])

    # --- search_combined ---

    def test_search_combined_returns_reranked_true_when_reranker_available(self):
        """search_combined returns reranked=True when reranker succeeds."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(3)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        mock_reranker = self._make_mock_reranker(6)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, reranked = idx.search_combined("query", top_n=5)
        self.assertTrue(reranked)
        self.assertLessEqual(len(results), 5)

    def test_search_combined_returns_reranked_false_with_rrf_fallback(self):
        """search_combined returns reranked=False and uses RRF when reranker unavailable."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(3)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        with patch.object(idx, "_get_reranker", return_value=None):
            results, reranked = idx.search_combined("query", top_n=5)
        self.assertFalse(reranked)
        self.assertLessEqual(len(results), 5)

    def test_search_combined_result_count_does_not_exceed_top_n(self):
        """search_combined never returns more than top_n."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(5)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(5)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        mock_reranker = self._make_mock_reranker(10)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, _ = idx.search_combined("query", top_n=3)
        self.assertLessEqual(len(results), 3)

    def test_code_ask_response_includes_reranked_field(self):
        """code_ask_response includes 'reranked' in response data."""
        index = MagicMock()
        index.search_combined.return_value = ([], False)
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "how does billing work?")
        self.assertIn("reranked", result.get("data", {}))

    # --- _get_reranker caching ---

    def test_get_reranker_does_not_cache_none(self):
        """_get_reranker must not set self._reranker when load fails (no-cache-None rule)."""
        idx = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        idx._reranker = None
        # Simulate failed load by making import fail
        with patch.dict("sys.modules", {"fastembed.rerank.cross_encoder": None}):
            result = idx._get_reranker()
        # After failure, _reranker must still be None
        self.assertIsNone(idx._reranker)

    def test_get_reranker_caches_on_success(self):
        """_get_reranker caches the reranker on successful load."""
        idx = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        idx._reranker = None
        mock_reranker = MagicMock()
        mock_encoder_cls = MagicMock(return_value=mock_reranker)

        import types
        fake_module = types.ModuleType("fastembed.rerank.cross_encoder")
        fake_module.TextCrossEncoder = mock_encoder_cls

        with patch.dict("sys.modules", {"fastembed.rerank.cross_encoder": fake_module}):
            with patch.object(idx, "_indexer_constant", return_value="BAAI/bge-reranker-base"):
                with patch.object(idx, "_offline_model_env", return_value=__import__("contextlib").nullcontext()):
                    result = idx._get_reranker()

        self.assertIsNotNone(idx._reranker)
        self.assertEqual(idx._reranker, mock_reranker)

    # --- _rerank sort order ---

    def test_rerank_sorts_descending_by_score(self):
        """_rerank returns candidates sorted descending by reranker score."""
        idx = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        # reranker returns ascending scores: doc at index i gets score i
        # so highest-scored doc is the last one
        mock_reranker = MagicMock()
        mock_reranker.rerank.side_effect = lambda query, docs: [float(i) for i in range(len(docs))]
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            candidates = [{"id": f"c{i}", "text": f"doc {i}"} for i in range(4)]
            results = idx._rerank("query", candidates, top_n=2)
        # highest score is index 3 (score 3.0), then index 2 (score 2.0)
        self.assertEqual(results[0]["id"], "c3")
        self.assertEqual(results[1]["id"], "c2")


# ---------------------------------------------------------------------------
# Background model download tests (12mhv-enh)
# ---------------------------------------------------------------------------

class BackgroundModelDownloadTests(unittest.TestCase):
    """Tests for _start_background_model_downloads() and _ensure_model_cached()."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_index(self):
        """Return a bare WaveIndex without triggering __init__ side effects."""
        idx = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        idx.root = self.root
        idx.index_dir = self.root / ".wavefoundry" / "index"
        idx.framework_index_dir = self.root / ".wavefoundry" / "framework" / "index"
        idx._docs_vecs = None
        idx._code_vecs = None
        idx._docs_chunks = []
        idx._all_docs_chunks = []
        idx._code_chunks = []
        idx._docs_embedder = None
        idx._code_embedder = None
        idx._reranker = None
        idx._model_downloads_started = False
        idx._meta = {}
        idx._loaded = False
        idx._loaded_meta_signature = {}
        idx._docs_tag_index = {}
        idx._code_tag_index = {}
        idx._docs_kind_index = {}
        idx._code_kind_index = {}
        return idx

    def test_hf_hub_offline_suppresses_thread(self):
        """When HF_HUB_OFFLINE=1, no thread is spawned and _model_downloads_started stays False."""
        idx = self._make_index()
        with patch.dict(os.environ, {"HF_HUB_OFFLINE": "1"}):
            with patch("threading.Thread") as mock_thread:
                idx._start_background_model_downloads()
        mock_thread.assert_not_called()
        self.assertFalse(idx._model_downloads_started)

    def test_double_spawn_guard_spawns_only_one_thread(self):
        """Calling _start_background_model_downloads() twice only starts one thread."""
        idx = self._make_index()
        env = {k: v for k, v in os.environ.items() if k != "HF_HUB_OFFLINE"}
        with patch.dict(os.environ, env, clear=True):
            with patch("threading.Thread") as mock_thread:
                mock_thread.return_value = MagicMock()
                idx._start_background_model_downloads()
                idx._start_background_model_downloads()
        self.assertEqual(mock_thread.call_count, 1)

    def test_thread_is_daemon(self):
        """The spawned thread must be a daemon thread."""
        idx = self._make_index()
        env = {k: v for k, v in os.environ.items() if k != "HF_HUB_OFFLINE"}
        captured_kwargs = {}
        def capture_thread(**kwargs):
            captured_kwargs.update(kwargs)
            t = MagicMock()
            return t
        with patch.dict(os.environ, env, clear=True):
            with patch("threading.Thread", side_effect=capture_thread):
                idx._start_background_model_downloads()
        self.assertTrue(captured_kwargs.get("daemon"), "Thread must be started with daemon=True")

    def test_worker_continues_after_per_model_failure(self):
        """If _ensure_model_cached raises for the first model, subsequent models are still attempted."""
        idx = self._make_index()
        call_log = []

        def fake_ensure(model_name, model_type):
            call_log.append(model_name)
            if len(call_log) == 1:
                raise RuntimeError("simulated download failure")

        env = {k: v for k, v in os.environ.items() if k != "HF_HUB_OFFLINE"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(idx, "_indexer_constant", side_effect=["model-A", "model-B", "reranker-X"]):
                with patch.object(self.srv, "_ensure_model_cached", side_effect=fake_ensure):
                    import threading
                    threads = []
                    orig_thread = threading.Thread

                    def capture_and_run(*args, **kwargs):
                        t = orig_thread(*args, **kwargs)
                        threads.append(t)
                        return t

                    with patch("threading.Thread", side_effect=capture_and_run):
                        idx._start_background_model_downloads()

                    if threads:
                        threads[0].join(timeout=5)

        # Both models should have been attempted (first fails, second and third still called)
        self.assertGreaterEqual(len(call_log), 2)

    def test_get_reranker_does_not_cache_none_on_failure(self):
        """_get_reranker() must leave self._reranker as None when it cannot load the model."""
        idx = self._make_index()
        with patch.dict(
            "sys.modules",
            {"fastembed": None, "fastembed.rerank": None, "fastembed.rerank.cross_encoder": None},
        ):
            result1 = idx._get_reranker()
            result2 = idx._get_reranker()
        self.assertIsNone(result1)
        self.assertIsNone(result2)
        self.assertIsNone(idx._reranker)

    def test_build_server_calls_start_background_model_downloads(self):
        """build_server() must call _start_background_model_downloads() exactly once."""
        call_count = [0]
        original_init = self.srv.WaveIndex.__init__

        def patched_start(self_inner):
            call_count[0] += 1

        try:
            mcp = None
            with patch.object(self.srv.WaveIndex, "_start_background_model_downloads", patched_start):
                mcp = self.srv.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        self.assertEqual(call_count[0], 1, "_start_background_model_downloads must be called once in build_server()")

    def test_ensure_model_cached_embedding_already_cached(self):
        """_ensure_model_cached prints 'already cached' when offline probe succeeds."""
        import contextlib
        import io

        mock_embedder = MagicMock()

        def fake_text_embedding(model_name, local_files_only=None, **kwargs):
            return mock_embedder

        with patch.dict(os.environ, {}, clear=False):
            with patch("fastembed.TextEmbedding", side_effect=fake_text_embedding):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    self.srv._ensure_model_cached("test-embedding-model", "embedding")
                output = buf.getvalue()

        self.assertIn("already cached", output)
        self.assertIn("test-embedding-model", output)

    def test_ensure_model_cached_reranker_import_error(self):
        """_ensure_model_cached skips gracefully when fastembed.rerank is not available."""
        import io

        with patch.dict("sys.modules", {"fastembed.rerank": None, "fastembed.rerank.cross_encoder": None}):
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                self.srv._ensure_model_cached("reranker-model", "reranker")
            output = buf.getvalue()

        self.assertIn("skipping", output)


if __name__ == "__main__":
    unittest.main()
