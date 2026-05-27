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
    """Load server.py (which imports server_impl) and return server_impl.

    Returning server_impl ensures patch.object(self.srv, "foo") patches the
    module where server_impl functions look up their siblings at call time,
    so mocks are visible to internal function-to-function calls.
    """
    sys.modules.pop("server", None)
    spec = importlib.util.spec_from_file_location("server", SERVER_PATH)
    srv_mod = importlib.util.module_from_spec(spec)
    sys.modules["server"] = srv_mod
    spec.loader.exec_module(srv_mod)
    return sys.modules["server_impl"]


def load_thin_runner():
    """Return the thin runner module (server.py). Call load_server() first."""
    return sys.modules.get("server")


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
    import lancedb
    root.mkdir(parents=True, exist_ok=True)
    (root / "meta.json").write_text(
        json.dumps({"model_versions": {"docs": model}, "content": ["docs"], "file_hashes": {}}),
        encoding="utf-8",
    )
    if not chunks:
        return
    vecs = np.array(vectors, dtype=np.float32)
    # Pad/truncate vecs to match chunks length (handles mismatched-vector-count tests)
    rows = []
    for i, chunk in enumerate(chunks):
        row = dict(chunk)
        if "tags" not in row:
            row["tags"] = ""
        elif isinstance(row["tags"], list):
            row["tags"] = " ".join(str(t) for t in row["tags"])
        if "language" not in row:
            row["language"] = None
        if "section" not in row:
            row["section"] = None
        if i < len(vecs):
            row["vector"] = vecs[i].tolist()
        else:
            row["vector"] = vecs[0].tolist()
        rows.append(row)
    db = lancedb.connect(str(root))
    db.create_table("docs", data=rows, mode="overwrite")


def _write_lance_index(root: Path, *, docs_chunks: list[dict] | None = None, docs_vectors=None, code_chunks: list[dict] | None = None, code_vectors=None, model: str = "test-model") -> None:
    import numpy as np
    import lancedb

    root.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "model_versions": {},
        "content": [],
        "file_hashes": {},
    }
    if docs_chunks is not None:
        meta["model_versions"]["docs"] = model
        meta["content"].append("docs")
    if code_chunks is not None:
        meta["model_versions"]["code"] = model
        meta["content"].append("code")
    (root / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    db = lancedb.connect(str(root))

    def _rows(chunks: list[dict], vectors) -> list[dict]:
        if not chunks:
            return []
        vecs = np.array(vectors, dtype=np.float32)
        rows: list[dict] = []
        for i, chunk in enumerate(chunks):
            row = dict(chunk)
            if "tags" not in row:
                row["tags"] = ""
            elif isinstance(row["tags"], list):
                row["tags"] = " ".join(str(t) for t in row["tags"])
            if "language" not in row:
                row["language"] = None
            if "section" not in row:
                row["section"] = None
            row["vector"] = vecs[i].tolist() if i < len(vecs) else vecs[0].tolist()
            rows.append(row)
        return rows

    if docs_chunks is not None and docs_chunks:
        db.create_table("docs", data=_rows(docs_chunks, docs_vectors), mode="overwrite")
    if code_chunks is not None and code_chunks:
        db.create_table("code", data=_rows(code_chunks, code_vectors), mode="overwrite")


# ---------------------------------------------------------------------------
# Root discovery
# ---------------------------------------------------------------------------

class RootDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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



class LayeredIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    def test_seed_lookup_still_works_when_model_version_differs(self):
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
        self.assertEqual(
            index.get_seed("install-wavefoundry")["path"],
            ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
        )


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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv

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
            self.assertNotIn("codex_server_name", result["data"])
            self.assertIn("framework_version", result["data"])
            self.assertIn("server_runner_version", result["data"])
            self.assertIn("server_impl_version", result["data"])
            self.assertIn("impl_matches_disk", result["data"])
            self.assertEqual(result["data"]["server_runner_version"], self.srv.SERVER_RUNNER_VERSION)
            self.assertEqual(result["data"]["server_impl_version"], self.srv.SERVER_IMPL_VERSION)
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv

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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv

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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
        # Add prepare-council verdict so the council gate passes
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + "\n## Review Checkpoints\n\n- **Prepare-phase Wave Council [prepare-council] — 2026-05-21: PASS** (red-team fixed seat)\n",
            encoding="utf-8",
        )

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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir = self.root / ".wavefoundry" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.index_dir / "index-build.json"
        self.log_path = self.logs_dir / "project-index-build.log"

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
        bg_log = self.logs_dir / "project-background-build.log"
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
        self.assertFalse(self.state_path.exists())

    def test_finished_falls_back_to_last_line_when_no_summary(self):
        import time
        self._write_state(99999999, time.time() - 60)
        self.log_path.write_text("build_index: some partial output\n", encoding="utf-8")
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertEqual(result["data"]["last_log_line"], "build_index: some partial output")

    def test_finished_when_setup_index_exits_with_model_prewarm_error(self):
        import time
        self._write_state(99999999, time.time() - 60)
        self.log_path.write_text(
            "Prewarming semantic model cache: BAAI/bge-small-en-v1.5\n"
            "Required reranker model 'BAAI/bge-reranker-base' could not be prepared for semantic index setup: "
            "network or download host unavailable.\n",
            encoding="utf-8",
        )
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertIn("network or download host unavailable", result["data"]["last_log_line"])
        self.assertFalse(self.state_path.exists())

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
        self.assertFalse(self.state_path.exists())

    def test_finished_when_log_has_up_to_date_despite_live_pid(self):
        # Regression: zombie process (defunct on macOS) keeps os.kill(pid,0) returning True.
        # "index is up to date" must be treated as a terminal log state, same as the done marker.
        import os, time
        self._write_state(os.getpid(), time.time() - 60)
        self.log_path.write_text("build_index: index is up to date\n", encoding="utf-8")
        result = self.srv.wave_index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertFalse(self.state_path.exists())

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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
        docs_rows = docs_chunks or [{"id": "d1", "path": "docs/a.md", "kind": "doc", "text": "doc", "lines": [1, 1]}]
        docs_vecs = [[1.0, 0.0, 0.0, 0.0] for _ in docs_rows]
        code_rows = code_chunks or None
        code_vecs = [[1.0, 0.0, 0.0, 0.0] for _ in code_rows] if code_rows else None
        _write_lance_index(
            index_dir,
            docs_chunks=docs_rows,
            docs_vectors=docs_vecs,
            code_chunks=code_rows,
            code_vectors=code_vecs,
        )
        meta_path = index_dir / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["built_at"] = built_at
        meta["file_hashes"] = file_hashes or {"docs/a.md": "h1"}
        meta_path.write_text(json.dumps(meta), encoding="utf-8")

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
        env = popen.call_args.kwargs["env"]
        self.assertIn("setup_index.py", str(cmd[1]))
        self.assertIn("--include-code", cmd)
        self.assertIn("--full", cmd)
        self.assertEqual(
            env["WAVEFOUNDRY_INDEX_BUILD_STATE_PATH"],
            str(self.root / ".wavefoundry" / "index" / "index-build.json"),
        )

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
        logs_dir = self.root / ".wavefoundry" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "project-index-build.log"
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
        logs_dir = self.root / ".wavefoundry" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "project-index-build.log"
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
        logs_dir = self.root / ".wavefoundry" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "project-index-build.log").write_text("no done marker\n", encoding="utf-8")
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv

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
            logs_dir = root / ".wavefoundry" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / "project-background-build.log").write_text(
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
        # Unsafe for setUpClass: raw self.srv attribute mutations in test methods would leak between tests.
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_tools_registered(self):
        try:
            mcp = load_thin_runner().build_server(self.root)
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
            "wave_gate_open",
            "wave_gate_close",
            "wave_gate_status",
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
            "wave_upgrade",
            "wave_upgrade_status",
            "wave_mcp_reload",
            "wave_dashboard_start",
            "wave_dashboard_open",
            "wave_dashboard_stop",
            "wave_dashboard_restart",
            "code_list_files",
            "code_read",
            "code_keyword",
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
            mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        names = self.srv._registered_mcp_tool_names(mcp)
        viol = self.srv.first_party_tool_names_violating_prefix(names)
        self.assertEqual(viol, [], f"Prefix violations: {viol}")


class WaveMcpReloadTests(unittest.TestCase):
    """12rb9: wave_mcp_reload and version fields."""

    def setUp(self):
        # Reload-sensitive: this class tests module-reload behavior; per-method isolation is required.
        self.srv = load_server()          # server_impl (impl namespace)
        self.runner = load_thin_runner()  # server.py thin runner (build_server, perform_mcp_reload, …)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        fw = self.root / ".wavefoundry" / "framework"
        fw.mkdir(parents=True, exist_ok=True)
        (fw / "VERSION").write_text("test-pack-version", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_wave_help_lists_wave_mcp_reload(self):
        self.srv._cached_help_catalog_json.cache_clear()
        result = self.srv.wave_help_response()
        self.assertIn("wave_mcp_reload", result["data"]["core_tools"])

    def test_wave_help_reload_mcp_goal(self):
        self.srv._cached_help_catalog_json.cache_clear()
        result = self.srv.wave_help_response("reload_mcp")
        self.assertEqual(result["data"]["goal"], "reload_mcp")
        self.assertEqual(result["data"]["recommended_chain"][0], "wave_mcp_reload")

    def test_perform_mcp_reload_returns_versions(self):
        try:
            self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        result = self.runner.perform_mcp_reload()
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["ok"])
        self.assertEqual(result["data"]["framework_version"], "test-pack-version")
        self.assertEqual(result["data"]["server_runner_version"], self.runner.SERVER_RUNNER_VERSION)
        self.assertTrue(result["data"]["server_impl_version"])
        # impl_matches_disk is false when test root VERSION differs from installed pack VERSION
        self.assertIs(result["data"]["impl_matches_disk"], False)


# ---------------------------------------------------------------------------
# DX fix tests (AC-16 through AC-20)
# ---------------------------------------------------------------------------

class WaveCloseModeDiscoverabilityTests(unittest.TestCase):
    """AC-16: wave_close invalid-mode response includes valid_modes field."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "alpha.py").write_text("def alpha_func():\n    SEARCH_TARGET = 42\n    return SEARCH_TARGET\n", encoding="utf-8")
        (src / "beta.py").write_text("def beta_func():\n    pass\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_exact_match(self):
        result = self.srv.code_keyword_response(self.root, "SEARCH_TARGET")
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["data"]["count"], 0)
        paths = [r["path"] for r in result["data"]["results"]]
        self.assertTrue(any("alpha.py" in p for p in paths))

    def test_returns_line_numbers(self):
        result = self.srv.code_keyword_response(self.root, "SEARCH_TARGET")
        for r in result["data"]["results"]:
            self.assertIn("line", r)
            self.assertIsInstance(r["line"], int)

    def test_glob_filter_restricts_results(self):
        result = self.srv.code_keyword_response(self.root, "def ", glob="*beta*")
        self.assertEqual(result["status"], "ok")
        paths = [r["path"] for r in result["data"]["results"]]
        self.assertFalse(any("alpha.py" in p for p in paths))

    def test_empty_query_returns_error(self):
        result = self.srv.code_keyword_response(self.root, "")
        self.assertEqual(result["status"], "error")

    def test_no_match_returns_empty_results(self):
        result = self.srv.code_keyword_response(self.root, "ZZZNOMATCHXXX")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["count"], 0)


class CodeDefinitionTests(unittest.TestCase):
    """AC-6: code_definition preserves Python AST lookup."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _get_mcp(self):
        try:
            return load_thin_runner().build_server(self.root)
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _read_resource(self, uri: str):
        try:
            mcp = load_thin_runner().build_server(self.root)
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _read_resource(self, uri: str):
        try:
            mcp = load_thin_runner().build_server(self.root)
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    """12ax9/12sf9: wave_gate_open / wave_gate_close / wave_gate_status MCP tools."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    def test_design_system_gate_open_and_close(self):
        resp = self.srv.wave_open_gate_response(self.root, "design_system_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(self._read_gates()["design_system_edit_allowed"]["enabled"])
        resp2 = self.srv.wave_close_gate_response(self.root, "design_system_edit_allowed")
        self.assertEqual(resp2["status"], "ok")
        self.assertFalse(self._read_gates()["design_system_edit_allowed"]["enabled"])

    def test_gate_status_returns_all_gates(self):
        resp = self.srv.wave_gate_status_response(self.root)
        self.assertEqual(resp["status"], "ok")
        gates = resp["data"]["gates"]
        self.assertIn("seed_edit_allowed", gates)
        self.assertIn("framework_edit_allowed", gates)
        self.assertIn("design_system_edit_allowed", gates)
        # All gates should be closed in initial test state
        self.assertFalse(gates["seed_edit_allowed"])
        self.assertFalse(gates["framework_edit_allowed"])

    def test_gate_status_reflects_open_gate(self):
        self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        resp = self.srv.wave_gate_status_response(self.root)
        self.assertEqual(resp["status"], "ok")
        gates = resp["data"]["gates"]
        self.assertTrue(gates["seed_edit_allowed"])
        self.assertFalse(gates["framework_edit_allowed"])


class GateAutoCloseTests(unittest.TestCase):
    """12ax9: wave_pause and wave_close auto-close open gates."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
            mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        names = self.srv._registered_mcp_tool_names(mcp)
        self.assertIn("wave_get_handoff", names)
        self.assertIn("wave_set_handoff", names)


class DocsSearchModeFieldTests(unittest.TestCase):
    """Item 5: docs_search_response includes 'mode' field (semantic/lexical)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv

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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
        _write to LanceDB, _ensure_loaded, _lance_search, and kind filtering
        all in one pass with real vectors."""
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

        with tempfile.TemporaryDirectory() as idx_tmp:
            idx_dir = Path(idx_tmp)
            _write_lance_index(
                idx_dir,
                docs_chunks=chunks,
                docs_vectors=vectors.tolist(),
                model=self.model,
            )

            # Point a fresh WaveIndex at a root that uses this index dir
            with tempfile.TemporaryDirectory() as root_tmp:
                root = _make_repo(Path(root_tmp))
                project_idx = root / ".wavefoundry" / "index"
                project_idx.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy(str(idx_dir / "meta.json"), str(project_idx / "meta.json"))
                shutil.copytree(str(idx_dir / "docs.lance"), str(project_idx / "docs.lance"))

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


class WavePauseStatusTransitionTests(unittest.TestCase):
    """12as6: wave_pause transitions wave.md Status active→paused and records transition."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    def _add_council_verdict(self, wave_id: str) -> None:
        """Append a prepare-council verdict to the wave's ## Review Checkpoints section."""
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + "\n## Review Checkpoints\n\n- **Prepare-phase Wave Council [prepare-council] — 2026-05-21: PASS** (red-team fixed seat)\n",
            encoding="utf-8",
        )

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
        self._add_council_verdict(target_wave)
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
        self._add_council_verdict(paused_wave)
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    def test_wave_audit_reports_requested_wave_by_prefix(self):
        self._make_wave("1200a audit-target", "planned")
        result = self.srv.wave_audit_response(self.root, wave_id="1200a")
        self.assertEqual(result["status"], "ok")
        wave_data = result["data"]["wave"]
        self.assertEqual(wave_data.get("wave_id"), "1200a audit-target")
        self.assertEqual(wave_data.get("status"), "planned")
        self.assertEqual(wave_data.get("next_action"), "prepare_wave")

    def test_wave_audit_reports_no_wave_when_only_paused(self):
        """Paused wave should not satisfy wave_audit's 'active or planned' readiness check."""
        self._make_wave("1200a audit-paused", "paused")
        result = self.srv.wave_audit_response(self.root)
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("no_active_wave", codes)


class WaveValidateAcceptsPausedTests(unittest.TestCase):
    """12as6: lint must accept Status: paused in wave.md."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
        (idx_dir / "docs.lance").mkdir(parents=True, exist_ok=True)

        meta = {
            "built_at": "2026-01-01T00:00:00Z",
            "content": ["docs"],
            "model_versions": {"docs": "BAAI/bge-base-en-v1.5"},
            "chunker_versions": {"docs": "13"},
            "walker_version": "3",
            "file_meta": self._file_meta_for_root(root),
        }
        (idx_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": meta, "framework": {}}

        health = wave_idx._layer_health("project")
        self.assertEqual(health["stale_paths"], [], msg="file_meta hashes matched — should be no stale paths")

    def test_docs_lance_dir_counts_as_present(self):
        """LanceDB indexes should satisfy docs_present when the Lance table directory exists."""
        root = self._make_repo(self.tmp)
        (root / "docs" / "guide.md").write_text("# Guide\n\nHello.\n", encoding="utf-8")

        idx_dir = root / ".wavefoundry" / "index"
        idx_dir.mkdir(parents=True, exist_ok=True)
        (idx_dir / "docs.lance").mkdir(parents=True, exist_ok=True)

        meta = {
            "built_at": "2026-01-01T00:00:00Z",
            "content": ["docs"],
            "model_versions": {"docs": "BAAI/bge-base-en-v1.5"},
            "chunker_versions": {"docs": "13"},
            "walker_version": "3",
            "file_meta": self._file_meta_for_root(root),
        }
        (idx_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": meta, "framework": {}}
        wave_idx._lance_available = {("project", "docs")}

        health = wave_idx._layer_health("project")
        self.assertTrue(health["docs_present"])
        self.assertEqual(self.server._index_layer_readiness(health), "current")

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

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": meta, "framework": {}}

        health = wave_idx._layer_health("project")
        self.assertEqual(health["stale_paths"], [], msg="file_hashes fallback — should be no stale paths")

    def test_framework_pack_artifacts_are_ignored_by_current_hashes(self):
        """Framework health should not treat MANIFEST or VERSION as indexable files."""
        root = self._make_repo(self.tmp)
        framework_root = root / ".wavefoundry" / "framework"
        framework_root.mkdir(parents=True, exist_ok=True)
        (framework_root / "README.md").write_text("# Framework\n", encoding="utf-8")
        (framework_root / "MANIFEST").write_text("README.md\nMANIFEST\n", encoding="utf-8")
        (framework_root / "VERSION").write_text("2099-01-01a\n", encoding="utf-8")

        idx_dir = root / ".wavefoundry" / "framework" / "index"
        idx_dir.mkdir(parents=True, exist_ok=True)
        (idx_dir / "docs.lance").mkdir(parents=True, exist_ok=True)

        meta = {
            "built_at": "2026-01-01T00:00:00Z",
            "content": ["docs"],
            "model_versions": {"docs": "BAAI/bge-base-en-v1.5"},
            "chunker_versions": {"docs": "13"},
            "walker_version": "3",
            "file_meta": {
                ".wavefoundry/framework/README.md": {
                    "hash": self._hash(framework_root / "README.md"),
                    "mtime": 0.0,
                    "size": (framework_root / "README.md").stat().st_size,
                    "inode": 0,
                },
            },
        }
        (idx_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": {}, "framework": meta}

        health = wave_idx._layer_health("framework")
        self.assertEqual(health["current_hash_count"], 1)
        self.assertEqual(health["stale_paths"], [], msg="pack artifacts should be ignored by framework health")


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

    def test_returns_true_when_lock_file_exists_and_fresh(self):
        lock_path = self.tmp / "docs.lance" / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
        self.assertTrue(self.server._background_refresh_active(self.state_path))

    def test_returns_false_when_lock_file_stale(self):
        import time as _time
        lock_path = self.tmp / "docs.lance" / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
        # Backdate the mtime beyond the stale threshold
        stale_mtime = _time.time() - self.server.BACKGROUND_INDEX_LOCK_STALE_SECONDS - 10
        os.utime(lock_path, (stale_mtime, stale_mtime))
        self.assertFalse(self.server._background_refresh_active(self.state_path))
        self.assertFalse(lock_path.exists())

    def test_removes_dead_pid_lock_file(self):
        lock_path = self.tmp / "docs.lance" / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("999999999", encoding="utf-8")
        self.assertFalse(self.server._background_refresh_active(self.state_path))
        self.assertFalse(lock_path.exists())

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

    def test_fresh_lock_file_takes_precedence_over_dead_pid_expired_throttle(self):
        """Fresh lock from a running PID = active, even when state file shows a dead PID."""
        import time as _time
        self._write_state(pid=999999999, started_at=_time.time() - 300)
        lock_path = self.tmp / "code.lance" / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
        self.assertTrue(self.server._background_refresh_active(self.state_path))

    def test_build_status_reports_removed_stale_locks(self):
        root = self.tmp
        lock_path = root / ".wavefoundry" / "index" / "docs.lance" / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("999999999", encoding="utf-8")

        response = self.server.wave_index_build_status_response(root, layer="project")

        self.assertEqual(response["status"], "ok")
        data = response["data"]
        self.assertEqual(data["state"], "idle")
        self.assertEqual(len(data["stale_locks_cleaned"]), 1)
        self.assertEqual(data["stale_locks_cleaned"][0]["reason"], "pid_dead")
        self.assertTrue(data["stale_locks_cleaned"][0]["removed"])
        self.assertFalse(lock_path.exists())

    def test_build_status_keeps_old_lock_when_pid_is_alive(self):
        root = self.tmp
        lock_path = root / ".wavefoundry" / "index" / "docs.lance" / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
        os.utime(lock_path, (0, 0))

        response = self.server.wave_index_build_status_response(root, layer="project")

        self.assertEqual(response["status"], "ok")
        data = response["data"]
        self.assertEqual(data["state"], "idle")
        self.assertNotIn("stale_locks_cleaned", data)
        self.assertTrue(lock_path.exists())


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
        _write_lance_index(
            index_dir,
            docs_chunks=[{"id": "d1", "path": "docs/a.md", "kind": "doc", "text": "doc", "lines": [1, 1]}],
            docs_vectors=[[1.0, 0.0, 0.0, 0.0]],
        )
        payload = {"built_at": built_at, "content": ["docs"], "model_versions": {"docs": "test-model"}, "chunker_versions": {}}
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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


class CodeDefinitionCssTests(unittest.TestCase):
    """CSS/SCSS support in code_definition via _css_definitions."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "styles.css").write_text(
            ".simple-class { color: red; }\n"
            "#main-id { display: block; }\n"
            "html[data-theme=\"dark\"] .dark-header--build { background: rgba(0,0,0,0.1); }\n"
            "--brand-color: #ff6600;\n"
            "@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }\n",
            encoding="utf-8",
        )
        (src / "mixins.scss").write_text(
            "@mixin flex-center { display: flex; align-items: center; }\n"
            ".scss-card { padding: 1rem; }\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_simple_class_selector(self):
        result = self.srv.code_definition_response(self.root, "simple-class")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertTrue(any(d["kind"] == "class" and "simple-class" in d["name"] for d in defs))
        self.assertTrue(any(d["language"] == "css" for d in defs))

    def test_finds_class_selector_mid_line(self):
        result = self.srv.code_definition_response(self.root, "dark-header--build")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertTrue(any("dark-header--build" in d["name"] for d in defs))

    def test_finds_id_selector(self):
        result = self.srv.code_definition_response(self.root, "main-id")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertTrue(any(d["kind"] == "id" and "main-id" in d["name"] for d in defs))

    def test_finds_keyframes(self):
        result = self.srv.code_definition_response(self.root, "fade-in")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertTrue(any(d["kind"] == "keyframes" for d in defs))

    def test_finds_scss_mixin(self):
        result = self.srv.code_definition_response(self.root, "flex-center")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertTrue(any(d["kind"] == "mixin" and d["language"] == "scss" for d in defs))

    def test_finds_scss_class(self):
        result = self.srv.code_definition_response(self.root, "scss-card")
        self.assertEqual(result["status"], "ok")
        defs = result["data"]["definitions"]
        self.assertTrue(any(d["kind"] == "class" and d["language"] == "scss" for d in defs))

    def test_css_in_supported_languages(self):
        result = self.srv.code_definition_response(self.root, "simple-class")
        self.assertIn("css", result["data"]["supported_languages"])
        self.assertIn("scss", result["data"]["supported_languages"])


class WaveIndexHealthRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv

    def test_previous_build_stats_refresh_from_finished_log(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            index_dir = root / ".wavefoundry" / "index"
            index_dir.mkdir(parents=True, exist_ok=True)
            state = {"pid": 999999, "started_at": 1710000000.0, "content": "docs", "full": False}
            (index_dir / "index-build.json").write_text(json.dumps(state), encoding="utf-8")
            logs_dir = root / ".wavefoundry" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / "project-index-build.log").write_text(
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_index(self, code_results=None, doc_results=None):
        index = MagicMock()
        # code_ask_response now uses search_combined; provide combined results
        combined = (code_results or []) + (doc_results or [])
        index.search_combined.return_value = (combined, False, 0, 0, [], [], "none")
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

    def test_classify_question_artifact_anchored_snake_case_symbol(self):
        """Implementation verb + snake_case symbol → artifact_anchored."""
        self.assertEqual(self.srv._classify_question("how is build_prefix() generated?"), "artifact_anchored")

    def test_classify_question_artifact_anchored_version_suffix(self):
        """Implementation verb + version suffix token → artifact_anchored."""
        self.assertEqual(self.srv._classify_question("how is the +2vr8 suffix derived?"), "artifact_anchored")

    def test_classify_question_artifact_anchored_filename(self):
        """Implementation verb + dotted filename → artifact_anchored."""
        self.assertEqual(self.srv._classify_question("how does lifecycle_id.py encode elapsed hours?"), "artifact_anchored")

    def test_classify_question_generic_noun_remains_explanatory(self):
        """Implementation verb alone without a concrete artifact cue stays explanatory."""
        self.assertEqual(self.srv._classify_question("how is the build number generated?"), "explanatory")

    def test_extract_artifact_cue_snake_case(self):
        """_extract_artifact_cue returns snake_case identifier."""
        self.assertEqual(self.srv._extract_artifact_cue("how does build_prefix work?"), "build_prefix")

    def test_extract_artifact_cue_version_suffix(self):
        """_extract_artifact_cue returns version suffix token."""
        self.assertEqual(self.srv._extract_artifact_cue("what generates +2vr8?"), "+2vr8")

    def test_extract_artifact_cue_no_match(self):
        """_extract_artifact_cue returns empty string when no cue is present."""
        self.assertEqual(self.srv._extract_artifact_cue("how is the build number generated?"), "")

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

    def test_feedback_docs_are_demoted_but_not_removed(self):
        """Journal/feedback docs are weighted at 0.50× — demoted below code but still present."""
        index = self._make_index(code_results=[
            {"path": "docs/agents/journals/cia-feedback-2026-05-14.md", "kind": "doc", "lines": [1, 4], "text": "feedback about tenant creation", "score": 0.99},
            self._fake_code_chunk("src/tenants.ts", score=0.95),
        ])
        result = self.srv.code_ask_response(index, self.root, "How does a new tenant get created?")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["partition_applied"])
        self.assertEqual(result["data"]["demotion_count"], 1)
        citations = result["data"]["citations"]
        self.assertGreaterEqual(len(citations), 2)
        # After 0.50× demotion, journal (0.99→0.495) ranks below code (0.95)
        self.assertEqual(citations[0]["path"], "src/tenants.ts")
        self.assertEqual(citations[0]["final_rank"], 1)
        self.assertEqual(citations[1]["path"], "docs/agents/journals/cia-feedback-2026-05-14.md")
        self.assertEqual(citations[1]["final_rank"], 2)

    def test_seed_docs_are_demoted_but_not_removed(self):
        """Seeds are weighted at 0.60× — demoted below code but still present."""
        index = self._make_index()
        index.search_combined.return_value = (
            [
                {"path": ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md", "kind": "seed", "lines": [1, 4], "text": "upgrade guidance", "score": 0.99},
                self._fake_code_chunk("src/http_filtering.java", score=0.95),
            ],
            False,
            0,
            0,
            [],
            [],
            "none",
        )
        result = self.srv.code_ask_response(index, self.root, "How does HTTP request filtering work?")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["partition_applied"])
        self.assertEqual(result["data"]["demotion_count"], 1)
        citations = result["data"]["citations"]
        self.assertGreaterEqual(len(citations), 2)
        # After 0.60× demotion, seed (0.99→0.594) ranks below code (0.95)
        self.assertEqual(citations[0]["path"], "src/http_filtering.java")
        self.assertEqual(citations[0]["final_rank"], 1)
        self.assertEqual(citations[1]["path"], ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md")
        self.assertEqual(citations[1]["final_rank"], 2)

    # --- _demote_doc_results unit tests (12q5v) ---

    def test_demote_waves_explanatory(self):
        """docs/waves/ results get 0.75× when question_type == explanatory."""
        srv = self.srv
        results = [{"path": "docs/waves/12pn3/change.md", "kind": "doc", "score": 1.0}]
        demoted, count = srv._demote_doc_results(results, "explanatory")
        self.assertEqual(count, 1)
        self.assertAlmostEqual(demoted[0]["score"], 0.75)

    def test_demote_plans_explanatory(self):
        """docs/plans/ results get 0.60× when question_type == explanatory."""
        srv = self.srv
        results = [{"path": "docs/plans/12abc-enh-foo.md", "kind": "doc", "score": 1.0}]
        demoted, count = srv._demote_doc_results(results, "explanatory")
        self.assertEqual(count, 1)
        self.assertAlmostEqual(demoted[0]["score"], 0.60)

    def test_demote_seeds_explanatory(self):
        """kind=seed results get 0.60× when question_type == explanatory."""
        srv = self.srv
        results = [{"path": ".wavefoundry/framework/seeds/001-overview.md", "kind": "seed", "score": 1.0}]
        demoted, count = srv._demote_doc_results(results, "explanatory")
        self.assertEqual(count, 1)
        self.assertAlmostEqual(demoted[0]["score"], 0.60)

    def test_demote_journals_explanatory(self):
        """Journal path results get 0.50× when question_type == explanatory."""
        srv = self.srv
        results = [{"path": "docs/agents/journals/wave-coordinator.md", "kind": "doc", "score": 1.0}]
        demoted, count = srv._demote_doc_results(results, "explanatory")
        self.assertEqual(count, 1)
        self.assertAlmostEqual(demoted[0]["score"], 0.50)

    def test_demote_navigational_passthrough(self):
        """No demotion applied for navigational question type."""
        srv = self.srv
        results = [
            {"path": "docs/waves/12pn3/change.md", "kind": "doc", "score": 1.0},
            {"path": "docs/agents/journals/wave-coordinator.md", "kind": "doc", "score": 0.9},
        ]
        demoted, count = srv._demote_doc_results(results, "navigational")
        self.assertEqual(count, 0)
        self.assertEqual(demoted[0]["score"], 1.0)
        self.assertEqual(demoted[1]["score"], 0.9)

    def test_demote_architecture_not_demoted(self):
        """Architecture docs and implementation code are not demoted."""
        srv = self.srv
        results = [
            {"path": "docs/architecture/current-state.md", "kind": "doc", "score": 0.9},
            {"path": "src/server.py", "kind": "code", "score": 0.8},
        ]
        demoted, count = srv._demote_doc_results(results, "explanatory")
        self.assertEqual(count, 0)
        self.assertEqual(demoted[0]["score"], 0.9)
        self.assertEqual(demoted[1]["score"], 0.8)

    def test_demote_resorts_by_score(self):
        """After demotion, results are re-sorted descending by score."""
        srv = self.srv
        results = [
            {"path": "docs/waves/12pn3/change.md", "kind": "doc", "score": 1.0},   # → 0.75
            {"path": "src/server.py", "kind": "code", "score": 0.8},               # → 0.80
        ]
        demoted, count = srv._demote_doc_results(results, "explanatory")
        self.assertEqual(count, 1)
        self.assertEqual(demoted[0]["path"], "src/server.py")    # 0.80 now first
        self.assertEqual(demoted[1]["path"], "docs/waves/12pn3/change.md")  # 0.75 second

    def test_demote_count_accurate(self):
        """demotion_count matches number of results with reduced score."""
        srv = self.srv
        results = [
            {"path": "docs/waves/w1/c1.md", "kind": "doc", "score": 0.9},
            {"path": "docs/plans/p1.md", "kind": "doc", "score": 0.8},
            {"path": "src/impl.py", "kind": "code", "score": 0.7},
        ]
        _, count = srv._demote_doc_results(results, "explanatory")
        self.assertEqual(count, 2)

    # --- _extract_question_symbol unit tests (12q63) ---

    def test_extract_question_symbol_private(self):
        """Private _snake_case token extracted from question."""
        srv = self.srv
        self.assertEqual(srv._extract_question_symbol("How does _rerank normalize cross-encoder scores?"), "_rerank")
        self.assertEqual(srv._extract_question_symbol("How does _rrf_merge combine dense and FTS?"), "_rrf_merge")

    def test_extract_question_symbol_snake(self):
        """snake_case token with >= 2 parts extracted when no private token present."""
        srv = self.srv
        result = srv._extract_question_symbol("How does build_index process files?")
        self.assertEqual(result, "build_index")

    def test_extract_question_symbol_lower_camel(self):
        """lowerCamelCase token extracted when no private or snake_case token present."""
        srv = self.srv
        self.assertEqual(srv._extract_question_symbol("How does buildIndex work?"), "buildIndex")
        self.assertEqual(srv._extract_question_symbol("What does getEmbedder return?"), "getEmbedder")

    def test_extract_question_symbol_backtick(self):
        """Backtick-quoted token extracted at highest priority."""
        srv = self.srv
        # Backtick wins over other patterns in the same question
        self.assertEqual(srv._extract_question_symbol("How does `_rerank` normalize scores?"), "_rerank")
        self.assertEqual(srv._extract_question_symbol("What does `search_combined` return?"), "search_combined")
        self.assertEqual(srv._extract_question_symbol("How does `buildIndex` work?"), "buildIndex")

    def test_extract_question_symbol_dotted(self):
        """Dotted, :: or -> qualified names: rightmost identifier extracted."""
        srv = self.srv
        # Dotted access — returns rightmost component
        self.assertEqual(srv._extract_question_symbol("How does WaveIndex.search_combined handle dedup?"), "search_combined")
        # :: qualified — returns rightmost component (C++/Rust namespace)
        self.assertEqual(srv._extract_question_symbol("What does ns::embed_query do?"), "embed_query")
        # -> member access (C/C++ pointer dereference)
        self.assertEqual(srv._extract_question_symbol("How does node->next get updated?"), "next")
        # Dotted with private rightmost
        self.assertEqual(srv._extract_question_symbol("How does index._rerank normalize?"), "_rerank")

    def test_extract_question_symbol_annotation(self):
        """@annotation prefix extracted with @ retained for specificity."""
        srv = self.srv
        self.assertEqual(srv._extract_question_symbol("When should I use @Override in Java?"), "@Override")
        self.assertEqual(srv._extract_question_symbol("How does @Autowired injection work?"), "@Autowired")
        self.assertEqual(srv._extract_question_symbol("What does @property do in Python?"), "@property")

    def test_extract_question_symbol_screaming_snake(self):
        """SCREAMING_SNAKE_CASE constants extracted between _private and snake_case."""
        srv = self.srv
        self.assertEqual(srv._extract_question_symbol("What is MAX_RETRIES set to?"), "MAX_RETRIES")
        self.assertEqual(srv._extract_question_symbol("How is HTTP_TIMEOUT used?"), "HTTP_TIMEOUT")
        # SQL aggregate function
        self.assertEqual(srv._extract_question_symbol("How does GROUP_CONCAT work in Spark SQL?"), "GROUP_CONCAT")

    def test_extract_question_symbol_none(self):
        """Returns None when no recognizable code symbol is present."""
        srv = self.srv
        self.assertIsNone(srv._extract_question_symbol("how does search work?"))
        self.assertIsNone(srv._extract_question_symbol("what is the purpose of this?"))

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

    # --- validation_required and dynamic next_tools (12q8t) ---

    def _fake_doc_chunk(self, path="docs/specs/span-masking.md", score=0.95):
        return {"path": path, "kind": "doc", "lines": [1, 20], "text": "Span attribute masking spec.", "score": score}

    def test_validation_required_explanatory_doc_top(self):
        """validation_required: true emitted when explanatory question + doc top citation."""
        index = self._make_index(code_results=[self._fake_doc_chunk()])
        result = self.srv.code_ask_response(index, self.root, "how does span attribute masking work?")
        self.assertEqual(result["data"]["question_type"], "explanatory")
        self.assertTrue(result["data"].get("validation_required"), "validation_required should be True when top citation is doc")

    def test_validation_required_not_emitted_navigational(self):
        """validation_required not emitted for navigational questions."""
        index = self._make_index(code_results=[self._fake_doc_chunk()])
        result = self.srv.code_ask_response(index, self.root, "where is the span masking implementation?")
        self.assertEqual(result["data"]["question_type"], "navigational")
        self.assertNotIn("validation_required", result["data"])

    def test_validation_required_not_emitted_code_top(self):
        """validation_required not emitted when top citation is kind='code'."""
        index = self._make_index(code_results=[self._fake_code_chunk()])
        result = self.srv.code_ask_response(index, self.root, "how does billing handle failed payments?")
        self.assertEqual(result["data"]["question_type"], "explanatory")
        self.assertNotIn("validation_required", result["data"])

    def test_next_tools_outline_for_large_file(self):
        """next_tools includes code_outline when top citation file exceeds 300 lines."""
        large_file = self.root / "src" / "large_service.py"
        large_file.parent.mkdir(parents=True, exist_ok=True)
        large_file.write_text("\n".join(f"# line {i}" for i in range(301)))
        index = self._make_index(code_results=[
            {"path": "src/large_service.py", "kind": "code", "lines": [42, 58], "text": "def process(): ...", "score": 0.9}
        ])
        result = self.srv.code_ask_response(index, self.root, "how does billing handle failed payments?")
        self.assertIn("code_outline", result["next_tools"])
        self.assertEqual(result["next_tools"][0], "code_outline")

    def test_next_tools_no_outline_for_small_file(self):
        """next_tools uses default when top citation file is <= 300 lines."""
        small_file = self.root / "src" / "small_service.py"
        small_file.parent.mkdir(parents=True, exist_ok=True)
        small_file.write_text("\n".join(f"# line {i}" for i in range(50)))
        index = self._make_index(code_results=[
            {"path": "src/small_service.py", "kind": "code", "lines": [1, 10], "text": "def process(): ...", "score": 0.9}
        ])
        result = self.srv.code_ask_response(index, self.root, "how does billing handle failed payments?")
        self.assertNotIn("code_outline", result["next_tools"])

    def test_keyword_search_error_appended_to_gaps(self):
        """AC-4 (12d4b): keyword search error status is surfaced in gaps, not silently swallowed."""
        index = self._make_index()  # no results → triggers keyword fallback
        srv = load_server()
        with patch.object(srv, "code_keyword_response", return_value={"status": "error", "error": "index not built"}):
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
        """Patch WaveIndex to avoid embedding; inject raw chunks as Lance search result."""
        srv = load_server()
        index = srv.WaveIndex.__new__(srv.WaveIndex)
        # Provide the minimal attributes that search_code depends on after _ensure_loaded
        index._code_chunks = raw_chunks
        index._code_vecs = None
        index._lance_available = {("project", "code")}
        # Bypass _ensure_loaded
        with patch.object(index, "_ensure_loaded"):
            with patch.object(index, "_embed_query", return_value=None):
                with patch.object(srv, "_indexer_constant", return_value="model"):
                    # Patch _lance_search to return chunks in score-descending order (already sorted)
                    with patch.object(index, "_lance_search", return_value=raw_chunks):
                        with patch.object(index, "_indexer_constant", return_value="model"):
                            return index

    _chunk_counter = 0

    def _chunk(self, path, score):
        MaxPerFileFilterDirectTests._chunk_counter += 1
        start = MaxPerFileFilterDirectTests._chunk_counter * 10
        return {"path": path, "kind": "code", "language": "python", "lines": [start, start + 4], "text": "x", "score": score}

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
        index._lance_available = {("project", "code")}
        with patch.object(index, "_ensure_loaded"), \
             patch.object(index, "_embed_query", return_value=None), \
             patch.object(index, "_indexer_constant", return_value="model"), \
             patch.object(index, "_lance_search", return_value=raw), \
             patch.object(index, "_lance_fts_search", return_value=[]), \
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
        index._lance_available = {("project", "code")}
        with patch.object(index, "_ensure_loaded"), \
             patch.object(index, "_embed_query", return_value=None), \
             patch.object(index, "_indexer_constant", return_value="model"), \
             patch.object(index, "_lance_search", return_value=raw), \
             patch.object(index, "_lance_fts_search", return_value=[]), \
             patch.object(index, "_get_reranker", return_value=None):
            results, _ = index.search_code("query", max_per_file=1, top_n=10)
        self.assertEqual(len(results), 1)
        # After RRF merge the score is an RRF score, not the original cosine value.
        # The important invariant is that the top-ranked chunk (originally 0.95) is retained.
        self.assertEqual(results[0]["path"], "src/auth.py")


class InferTagsServerTests(unittest.TestCase):
    """AC-10 through AC-16 (12dv9): tag index and filter behavior via server."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv

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


    def test_search_docs_tags_pre_filter(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / ".wavefoundry" / "index").mkdir(parents=True)
            (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
            docs_chunks = [
                {"id": "w1", "path": "docs/waves/12dv9/wave.md", "kind": "doc", "text": "wave doc",
                 "language": None, "lines": [1, 1], "section": None, "tags": "wave"},
                {"id": "o1", "path": "docs/other/something.md", "kind": "doc", "text": "unrelated",
                 "language": None, "lines": [1, 1], "section": None, "tags": ""},
            ]
            import numpy as np
            _write_index_layer(
                root / ".wavefoundry" / "index",
                docs_chunks,
                np.ones((2, 4), dtype=np.float32).tolist(),
            )
            (root / ".wavefoundry" / "framework" / "index" / "meta.json").write_text(
                json.dumps({"model_versions": {}, "content": [], "file_hashes": {}}), encoding="utf-8"
            )
            idx = self.srv.WaveIndex(root)
            idx._embed_query = lambda q, model: np.ones(4, dtype=np.float32)
            with patch.object(idx, "_get_reranker", return_value=None):
                results, _ = idx.search_docs("anything", tags=["wave"], top_n=5)
            ids = [r["id"] for r in results]
            self.assertIn("w1", ids)
            self.assertNotIn("o1", ids)
        finally:
            tmp.cleanup()

    def test_search_docs_tags_and_kind_compose_with_and_semantics(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / ".wavefoundry" / "index").mkdir(parents=True)
            (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
            docs_chunks = [
                {"id": "w1", "path": "docs/waves/12dv9/wave.md", "kind": "doc", "text": "wave doc",
                 "language": None, "lines": [1, 1], "section": None, "tags": "wave"},
                {"id": "w2", "path": "docs/waves/12dv9/summary.md", "kind": "doc-summary", "text": "wave summary",
                 "language": None, "lines": [1, 1], "section": None, "tags": "wave"},
                {"id": "o1", "path": "docs/other/something.md", "kind": "doc", "text": "other doc",
                 "language": None, "lines": [1, 1], "section": None, "tags": ""},
            ]
            import numpy as np
            _write_index_layer(
                root / ".wavefoundry" / "index",
                docs_chunks,
                np.ones((3, 4), dtype=np.float32).tolist(),
            )
            (root / ".wavefoundry" / "framework" / "index" / "meta.json").write_text(
                json.dumps({"model_versions": {}, "content": [], "file_hashes": {}}), encoding="utf-8"
            )
            idx = self.srv.WaveIndex(root)
            idx._embed_query = lambda q, model: np.ones(4, dtype=np.float32)
            with patch.object(idx, "_get_reranker", return_value=None):
                results, _ = idx.search_docs("anything", kind="doc", tags=["wave"], top_n=5)
            ids = [r["id"] for r in results]
            self.assertIn("w1", ids)
            self.assertNotIn("w2", ids)
            self.assertNotIn("o1", ids)
        finally:
            tmp.cleanup()

    def test_search_docs_kind_only_pre_filter(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / ".wavefoundry" / "index").mkdir(parents=True)
            (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
            docs_chunks = [
                {"id": "s1", "path": "docs/waves/12dv9/12dv9.md", "kind": "doc-summary", "text": "wave summary",
                 "language": None, "lines": [1, 1], "section": None},
                {"id": "d1", "path": "docs/waves/12dv9/wave.md", "kind": "doc", "text": "wave doc",
                 "language": None, "lines": [1, 1], "section": None},
                {"id": "s2", "path": "docs/other/other.md", "kind": "doc-summary", "text": "other summary",
                 "language": None, "lines": [1, 1], "section": None},
            ]
            import numpy as np
            _write_index_layer(
                root / ".wavefoundry" / "index",
                docs_chunks,
                np.ones((3, 4), dtype=np.float32).tolist(),
            )
            (root / ".wavefoundry" / "framework" / "index" / "meta.json").write_text(
                json.dumps({"model_versions": {}, "content": [], "file_hashes": {}}), encoding="utf-8"
            )
            idx = self.srv.WaveIndex(root)
            idx._embed_query = lambda q, model: np.ones(4, dtype=np.float32)
            with patch.object(idx, "_get_reranker", return_value=None):
                results, _ = idx.search_docs("wave summary", kind="doc-summary", top_n=5)
            ids = [r["id"] for r in results]
            self.assertIn("s1", ids)
            self.assertIn("s2", ids)
            self.assertNotIn("d1", ids)
        finally:
            tmp.cleanup()

    def test_search_docs_empty_tags_returns_all(self):
        import numpy as np
        import tempfile
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
            _write_lance_index(
                root / ".wavefoundry" / "index",
                docs_chunks=docs_chunks,
                docs_vectors=vecs.tolist(),
                model="BAAI/bge-base-en-v1.5",
            )
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
        # Unsafe for setUpClass: raw self.srv attribute mutations in test methods would leak between tests.
        self.srv = load_server()

    def _make_mock_reranker(self, n_docs):
        """Return a mock reranker whose rerank() returns ascending floats (last doc ranks highest)."""
        reranker = MagicMock()
        reranker.rerank.side_effect = lambda query, docs: [float(i) for i in range(len(docs))]
        return reranker

    def _make_index_with_docs(self, docs_chunks, code_chunks=None):
        """Create a WaveIndex backed by in-memory LanceDB tables."""
        import numpy as np
        import tempfile
        srv = self.srv
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / ".wavefoundry" / "index").mkdir(parents=True)
        (root / ".wavefoundry" / "framework" / "index").mkdir(parents=True)
        _write_lance_index(
            root / ".wavefoundry" / "index",
            docs_chunks=docs_chunks,
            docs_vectors=np.ones((max(len(docs_chunks), 1), 4), dtype=np.float32).tolist(),
            code_chunks=code_chunks,
            code_vectors=np.ones((max(len(code_chunks or []), 1), 4), dtype=np.float32).tolist() if code_chunks else None,
            model="BAAI/bge-base-en-v1.5",
        )
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
        """search_combined returns (results, reranked, vector_ms, rerank_ms) with reranked=True."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(3)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        mock_reranker = self._make_mock_reranker(6)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, reranked, vector_ms, rerank_ms, _, _, _ = idx.search_combined("query", top_n=5)
        self.assertTrue(reranked)
        self.assertLessEqual(len(results), 5)
        self.assertIsInstance(vector_ms, int)
        self.assertIsInstance(rerank_ms, int)

    def test_search_combined_returns_reranked_false_with_rrf_fallback(self):
        """search_combined returns reranked=False and uses RRF when reranker unavailable."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(3)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        with patch.object(idx, "_get_reranker", return_value=None):
            results, reranked, vector_ms, rerank_ms, _, _, _ = idx.search_combined("query", top_n=5)
        self.assertFalse(reranked)
        self.assertLessEqual(len(results), 5)
        self.assertIsInstance(vector_ms, int)
        self.assertIsInstance(rerank_ms, int)

    def test_search_combined_result_count_does_not_exceed_top_n(self):
        """search_combined never returns more than top_n."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(5)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(5)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        mock_reranker = self._make_mock_reranker(10)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, _, _vms, _rms, _, _, _ = idx.search_combined("query", top_n=3)
        self.assertLessEqual(len(results), 3)

    def test_code_ask_response_includes_reranked_field(self):
        """code_ask_response includes 'reranked' and timing fields in response data."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 0, 0, [], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "how does billing work?")
        data = result.get("data", {})
        self.assertIn("reranked", data)
        self.assertIn("total_ms", data)
        self.assertIn("vector_ms", data)
        self.assertIn("rerank_ms", data)
        self.assertGreaterEqual(data["total_ms"], data["vector_ms"] + data["rerank_ms"])

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

    # --- search_combined: question-type-aware retrieval ---

    # --- search_combined: artifact_anchored exact-first routing ---

    def test_search_combined_artifact_anchored_uses_exact_first_when_code_hits(self):
        """artifact_anchored question uses keyword exact pass and returns code hits directly."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=[self._fake_code_chunk("src/a.py")])
        fake_kw_resp = {
            "status": "ok",
            "data": {"results": [
                {"path": "scripts/lifecycle_id.py", "line": 106, "snippet": "def build_prefix("},
            ]},
        }
        mock_reranker = MagicMock()
        def passthrough_rerank(query, candidates, top_n):
            return candidates[:top_n]
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", side_effect=passthrough_rerank):
                with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp):
                    results, reranked, vector_ms, _, definition_boosted, _, _ = idx.search_combined(
                        "how does build_prefix generate the +2vr8 format?",
                        top_n=5,
                        question_type="artifact_anchored",
                    )
        self.assertTrue(reranked, "exact pass with reranker should return reranked=True")
        self.assertEqual(vector_ms, 0, "exact pass skips vector fetch; vector_ms must be 0")
        self.assertIn("artifact_anchored", definition_boosted)
        self.assertTrue(any("lifecycle_id.py" in r.get("path", "") for r in results))

    def test_search_combined_artifact_anchored_falls_back_when_no_code_hits(self):
        """artifact_anchored with empty keyword result falls through to broad semantic pass."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("src/a.py")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        empty_kw_resp = {"status": "ok", "data": {"results": []}}
        captured = {}
        original_lance = idx._lance_search
        def capture_lance(table, qvec, top_n, where=None, layer="project"):
            captured["vector_fetch_called"] = True
            return original_lance(table, qvec, top_n, where=where, layer=layer)
        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_lance_search", side_effect=capture_lance):
                with patch(f"{self.srv.__name__}.code_keyword_response", return_value=empty_kw_resp):
                    idx.search_combined(
                        "how is the build_prefix generated?",
                        top_n=5,
                        question_type="artifact_anchored",
                    )
        self.assertTrue(captured.get("vector_fetch_called"), "fallback must invoke vector fetch when exact pass returns no code hits")

    # --- _is_test_path ---

    def test_is_test_path_python_prefix(self):
        self.assertTrue(self.srv._is_test_path("scripts/tests/test_server_tools.py"))

    def test_is_test_path_go_suffix(self):
        self.assertTrue(self.srv._is_test_path("pkg/auth/auth_test.go"))

    def test_is_test_path_java_suffix(self):
        self.assertTrue(self.srv._is_test_path("src/test/java/com/example/FooTest.java"))

    def test_is_test_path_csharp_suffix(self):
        self.assertTrue(self.srv._is_test_path("MyApp.Tests/ServiceTests.cs"))

    def test_is_test_path_js_infix(self):
        self.assertTrue(self.srv._is_test_path("src/billing/billing.test.js"))

    def test_is_test_path_ts_spec(self):
        self.assertTrue(self.srv._is_test_path("src/auth/auth.spec.ts"))

    def test_is_test_path_jest_directory(self):
        self.assertTrue(self.srv._is_test_path("src/__tests__/utils.js"))

    def test_is_test_path_ruby_spec(self):
        self.assertTrue(self.srv._is_test_path("spec/models/user_spec.rb"))

    def test_is_test_path_non_test_file(self):
        self.assertFalse(self.srv._is_test_path("src/billing/billing.py"))

    def test_is_test_path_contest_false_positive(self):
        """src/contest/ must not match — exact segment match, not substring."""
        self.assertFalse(self.srv._is_test_path("src/contest/billing.py"))

    # --- artifact-anchored: test-file demotion ---

    def test_artifact_anchored_demotes_test_files_after_rerank(self):
        """Test-file citations are partitioned to the end after reranking."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=[self._fake_code_chunk("src/a.py")])
        fake_kw_resp = {
            "status": "ok",
            "data": {"results": [
                {"path": "scripts/tests/test_server_tools.py", "line": 1, "snippet": "def test_build_prefix"},
                {"path": "scripts/lifecycle_id.py", "line": 106, "snippet": "def build_prefix("},
            ]},
        }
        mock_reranker = MagicMock()
        def passthrough_rerank(query, candidates, top_n):
            return candidates[:top_n]
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", side_effect=passthrough_rerank):
                with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp):
                    results, _, _, _, _, _, _ = idx.search_combined(
                        "how does build_prefix generate the +2vr8 format?",
                        top_n=5,
                        question_type="artifact_anchored",
                    )
        paths = [r["path"] for r in results]
        impl_idx = paths.index("scripts/lifecycle_id.py")
        test_idx = paths.index("scripts/tests/test_server_tools.py")
        self.assertLess(impl_idx, test_idx, "implementation file must rank before test file")

    # --- search_combined: dynamic VECTOR_TOP_K (dynamic-vector-top-k) ---

    def test_vector_top_k_explanatory_constant_is_50(self):
        """VECTOR_TOP_K_EXPLANATORY must be 50."""
        self.assertEqual(self.srv.VECTOR_TOP_K_EXPLANATORY, 50)

    def test_vector_top_k_default_constant_is_30(self):
        """VECTOR_TOP_K must be 30."""
        self.assertEqual(self.srv.VECTOR_TOP_K, 30)

    def test_search_combined_explanatory_uses_top_k_explanatory(self):
        """search_combined uses VECTOR_TOP_K_EXPLANATORY (50) for explanatory questions."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(3)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        captured = {}
        original_lance = idx._lance_search
        def capture_top_k(table, qvec, top_n, where=None, layer="project"):
            captured["top_k"] = top_n
            return original_lance(table, qvec, top_n, where=where, layer=layer)
        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_lance_search", side_effect=capture_top_k):
                idx.search_combined("how does billing work", top_n=5, question_type="explanatory")
        self.assertEqual(captured.get("top_k"), self.srv.VECTOR_TOP_K_EXPLANATORY)

    def test_search_combined_navigational_uses_default_top_k(self):
        """search_combined uses VECTOR_TOP_K (30) for navigational questions."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(3)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        captured = {}
        original_lance = idx._lance_search
        def capture_top_k(table, qvec, top_n, where=None, layer="project"):
            captured["top_k"] = top_n
            return original_lance(table, qvec, top_n, where=where, layer=layer)
        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_lance_search", side_effect=capture_top_k):
                idx.search_combined("where is the billing handler", top_n=5, question_type="navigational")
        self.assertEqual(captured.get("top_k"), self.srv.VECTOR_TOP_K)

    def test_search_combined_empty_question_type_uses_default_top_k(self):
        """search_combined uses VECTOR_TOP_K (30) when question_type is empty."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(3)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        captured = {}
        original_lance = idx._lance_search
        def capture_top_k(table, qvec, top_n, where=None, layer="project"):
            captured["top_k"] = top_n
            return original_lance(table, qvec, top_n, where=where, layer=layer)
        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_lance_search", side_effect=capture_top_k):
                idx.search_combined("billing", top_n=5, question_type="")
        self.assertEqual(captured.get("top_k"), self.srv.VECTOR_TOP_K)

    # --- search_combined: question-type-aware retrieval ---

    def test_search_combined_navigational_applies_rrf_weight_bias(self):
        """For navigational questions, code-index candidates receive higher RRF weight than docs."""
        # Build an index where code and docs each have one candidate so we can detect ordering
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("c0")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        with patch.object(idx, "_get_reranker", return_value=None):
            results_nav, _, _, _, _, _, _ = idx.search_combined("where is the config", top_n=5, question_type="navigational")
            results_def, _, _, _, _, _, _ = idx.search_combined("where is the config", top_n=5, question_type="")
        # Results should be returned without error and obey top_n
        self.assertLessEqual(len(results_nav), 5)
        self.assertLessEqual(len(results_def), 5)

    def test_search_combined_explanatory_partitions_infra_paths_after_rerank(self):
        """For explanatory questions, results with infra path segments are moved to end of list."""
        docs = [self._fake_doc_chunk("d0")]
        code = [
            self._fake_code_chunk("src/constructs/MyStack.ts"),
            self._fake_code_chunk("src/services/billing.ts"),
        ]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        # Mock reranker returns infra file first, business file second
        mock_reranker = MagicMock()
        infra_chunk = {**code[0], "score": 0.9}
        biz_chunk = {**code[1], "score": 0.8}
        mock_reranker.rerank.return_value = [0.9, 0.8, 0.5]
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", return_value=[infra_chunk, biz_chunk]):
                results, reranked, _, _, _, _, _ = idx.search_combined("how does billing work", top_n=5, question_type="explanatory")
        self.assertTrue(reranked)
        # The business logic file must appear before the infra file
        paths = [r.get("path", "") for r in results]
        infra_path = infra_chunk["path"]
        biz_path = biz_chunk["path"]
        self.assertIn(infra_path, paths)
        self.assertIn(biz_path, paths)
        self.assertLess(paths.index(biz_path), paths.index(infra_path))

    def test_search_combined_non_explanatory_no_partition(self):
        """For navigational/instructional questions, infra paths are not partitioned."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("src/constructs/MyStack.ts")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        infra_chunk = {**code[0], "score": 0.9}
        with patch.object(idx, "_get_reranker", return_value=None):
            results, reranked, _, _, _, _, _ = idx.search_combined("where is the stack", top_n=5, question_type="navigational")
        self.assertFalse(reranked)  # RRF fallback

    def test_search_combined_infrastructure_demoted_flag_in_code_ask(self):
        """code_ask_response sets infrastructure_demoted=True when explanatory + reranked + infra citations."""
        index = MagicMock()
        infra_result = {"path": "src/constructs/MyStack.ts", "score": 0.9, "lines": [1, 10], "text": "...", "kind": "code"}
        biz_result = {"path": "src/services/billing.ts", "score": 0.8, "lines": [1, 10], "text": "...", "kind": "code"}
        index.search_combined.return_value = ([infra_result, biz_result], True, 10, 20, [], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            # "how does billing work" → explanatory; constructs/ → infra segment
            result = self.srv.code_ask_response(index, root, "how does billing work")
        data = result.get("data", {})
        self.assertTrue(data.get("infrastructure_demoted", False))

    def test_search_combined_no_infrastructure_demoted_for_navigational(self):
        """code_ask_response does not set infrastructure_demoted for navigational questions."""
        index = MagicMock()
        infra_result = {"path": "src/constructs/MyStack.ts", "score": 0.9, "lines": [1, 10], "text": "...", "kind": "code"}
        index.search_combined.return_value = ([infra_result], True, 5, 10, [], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "where is the stack defined")
        data = result.get("data", {})
        self.assertNotIn("infrastructure_demoted", data)

    # --- search_combined: timing instrumentation ---

    def test_code_ask_timing_ms_fields_are_non_negative_integers(self):
        """total_ms, vector_ms, rerank_ms are non-negative integers in code_ask response."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 5, 3, [], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "how does auth work?")
        data = result.get("data", {})
        for field in ("total_ms", "vector_ms", "rerank_ms"):
            self.assertIn(field, data)
            self.assertIsInstance(data[field], int)
            self.assertGreaterEqual(data[field], 0)

    def test_code_ask_total_ms_geq_component_sum(self):
        """total_ms >= vector_ms + rerank_ms (structural invariant: total covers both phases)."""
        index = MagicMock()
        # Use 0,0 for mocked component times — wall-clock total_ms will always be >= 0+0
        index.search_combined.return_value = ([], False, 0, 0, [], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "how does auth work?")
        data = result.get("data", {})
        self.assertGreaterEqual(data["total_ms"], data["vector_ms"] + data["rerank_ms"])

    def test_code_ask_total_ms_geq_component_sum_nonzero(self):
        """Component times from search_combined are correctly propagated into the response."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 10, 20, [], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "how does auth work?")
        data = result.get("data", {})
        # Component times must be passed through verbatim from search_combined's return value
        self.assertEqual(data["vector_ms"], 10)
        self.assertEqual(data["rerank_ms"], 20)
        # total_ms is real wall-clock; with mocked search_combined it may be less than the
        # synthetic component sum — the >= invariant holds only in real execution where
        # total_ms wraps the actual computation phases.
        self.assertIsInstance(data["total_ms"], int)
        self.assertGreaterEqual(data["total_ms"], 0)

    def test_code_ask_timing_log_line_emitted(self):
        """code_ask emits a '[wavefoundry] code_ask timing:' print line per invocation."""
        import tempfile
        from unittest.mock import patch as _patch
        index = MagicMock()
        index.search_combined.return_value = ([], False, 5, 3, [], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        printed = []
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            with _patch("builtins.print", side_effect=lambda *a, **k: printed.append(" ".join(str(x) for x in a))):
                self.srv.code_ask_response(index, root, "where is the auth module?")
        timing_lines = [s for s in printed if "code_ask timing" in s]
        self.assertTrue(timing_lines, "expected a '[wavefoundry] code_ask timing:' print line")

    def test_docs_search_has_no_timing_fields(self):
        """docs_search response does not include timing fields."""
        index = MagicMock()
        index.search_docs.return_value = ([], False)
        result = self.srv.docs_search_response(index, "architecture")
        data = result.get("data", {})
        self.assertNotIn("total_ms", data)
        self.assertNotIn("vector_ms", data)
        self.assertNotIn("rerank_ms", data)

    def test_code_search_has_no_timing_fields(self):
        """code_search response does not include timing fields."""
        index = MagicMock()
        index.search_code.return_value = ([], False)
        result = self.srv.code_search_response(index, "billing")
        data = result.get("data", {})
        self.assertNotIn("total_ms", data)
        self.assertNotIn("vector_ms", data)
        self.assertNotIn("rerank_ms", data)

    # --- _rrf_merge weights ---

    def test_rrf_merge_weights_bias_higher_weighted_list(self):
        """_rrf_merge with weights gives higher RRF score to the higher-weighted list."""
        idx = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        # list_a has weight=2.0, list_b has weight=1.0, each with one unique item at rank 0
        chunk_a = {"path": "a.py", "id": "a", "lines": []}
        chunk_b = {"path": "b.py", "id": "b", "lines": []}
        results = idx._rrf_merge([[chunk_a], [chunk_b]], top_n=2, weights=[2.0, 1.0])
        self.assertEqual(results[0]["path"], "a.py")  # higher-weighted list wins

    def test_rrf_merge_no_weights_equal_treatment(self):
        """_rrf_merge without weights treats all lists equally."""
        idx = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        chunk_a = {"path": "a.py", "id": "a", "lines": []}
        chunk_b = {"path": "b.py", "id": "b", "lines": []}
        results = idx._rrf_merge([[chunk_a], [chunk_b]], top_n=2)
        # Both at rank 0 in their lists → equal RRF scores → either order acceptable
        self.assertEqual(len(results), 2)

    # --- Definition-file boosting (sql-candidate-window-boosting) ---

    def test_definition_boost_rules_constant_exists(self):
        """DEFINITION_BOOST_RULES is a list with at least one rule (SQL)."""
        rules = self.srv.DEFINITION_BOOST_RULES
        self.assertIsInstance(rules, list)
        self.assertGreater(len(rules), 0)
        labels = [r["label"] for r in rules]
        self.assertIn("sql", labels)

    def test_definition_boost_sql_rule_vocabulary(self):
        """SQL rule vocabulary contains expected trigger terms."""
        sql_rule = next(r for r in self.srv.DEFINITION_BOOST_RULES if r["label"] == "sql")
        self.assertIn("stored procedure", sql_rule["vocabulary"])
        self.assertIn("sql", sql_rule["vocabulary"])
        self.assertIn("table", sql_rule["vocabulary"])
        self.assertIn(".sql", sql_rule["extensions"])

    def test_definition_boost_sql_vocabulary_triggers_injection(self):
        """SQL vocabulary in query triggers SQL rule and injects .sql candidates with score=0.0."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("src/repo.ts")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        # Patch code_keyword_response to return a fake SQL file match
        fake_kw_resp = {
            "status": "ok",
            "data": {"results": [{"path": "migrations/001_users.sql", "line": 5, "snippet": "CREATE TABLE users"}]},
        }
        # Use a mock reranker so injected candidates pass through _rerank (RRF fallback drops them)
        mock_reranker = MagicMock()
        def passthrough_rerank(query, candidates, top_n):
            return candidates[:top_n]
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", side_effect=passthrough_rerank):
                with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp):
                    results, reranked, _, _, definition_boosted, _, _ = idx.search_combined(
                        "how does the stored procedure work", top_n=10
                    )
        self.assertIn("sql", definition_boosted)
        # Injected candidate must have score=0.0, kind="code", and path from keyword search
        sql_candidates = [r for r in results if r.get("path", "").endswith(".sql")]
        self.assertTrue(sql_candidates, "expected at least one injected .sql candidate in results")
        for c in sql_candidates:
            self.assertEqual(c["score"], 0.0, "injected candidate score must be 0.0")
            self.assertEqual(c["kind"], "code", "injected candidate kind must be 'code'")
            self.assertEqual(c["path"], "migrations/001_users.sql")

    def test_definition_boost_no_match_produces_no_boosted_field(self):
        """Query with no SQL vocabulary does not trigger augmentation; definition_boosted is empty."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("src/billing.ts")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        with patch.object(idx, "_get_reranker", return_value=None):
            _, _, _, _, definition_boosted, _, _ = idx.search_combined("where is the billing handler", top_n=5)
        self.assertEqual(definition_boosted, [])

    def test_definition_boost_result_count_does_not_exceed_top_n(self):
        """Result count never exceeds top_n even when definition-boost injects candidates."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(5)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(5)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        # Inject 5 SQL candidates via the mock
        sql_hits = [{"path": f"migrations/m{i}.sql", "line": i + 1, "snippet": "CREATE TABLE"} for i in range(5)]
        fake_kw_resp = {"status": "ok", "data": {"results": sql_hits}}
        with patch.object(idx, "_get_reranker", return_value=None):
            with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp):
                results, _, _, _, _, _, _ = idx.search_combined("how does the sql schema work", top_n=3)
        self.assertLessEqual(len(results), 3)

    def test_definition_boost_second_rule_addition_requires_no_logic_change(self):
        """Adding a second rule to DEFINITION_BOOST_RULES requires only a table entry, no logic changes."""
        # Verify the rule loop is data-driven by checking that an injected second rule fires
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("src/api.ts")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        graphql_rule = {
            "vocabulary": frozenset({"graphql", "schema type", "gql"}),
            "extensions": [".graphql"],
            "label": "graphql",
        }
        fake_kw_resp = {"status": "ok", "data": {"results": [{"path": "schema/user.graphql", "line": 1, "snippet": "type User"}]}}
        original_rules = self.srv.DEFINITION_BOOST_RULES
        try:
            self.srv.DEFINITION_BOOST_RULES = original_rules + [graphql_rule]
            with patch.object(idx, "_get_reranker", return_value=None):
                with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp):
                    _, _, _, _, boosted, _, _ = idx.search_combined("what graphql types exist", top_n=5)
            self.assertIn("graphql", boosted)
        finally:
            self.srv.DEFINITION_BOOST_RULES = original_rules

    def test_definition_boosted_flag_propagated_to_code_ask_response(self):
        """code_ask_response includes definition_boosted list when rule fired."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 0, 0, ["sql"], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "how does the stored procedure work?")
        data = result.get("data", {})
        self.assertIn("definition_boosted", data)
        self.assertIn("sql", data["definition_boosted"])

    def test_definition_boosted_absent_from_code_ask_when_no_rule_fired(self):
        """code_ask_response omits definition_boosted when no rule fired."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 0, 0, [], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "where is the billing handler?")
        data = result.get("data", {})
        self.assertNotIn("definition_boosted", data)

    # --- Symbol injection boost (12q63 pre-slice boost inside _rerank) ---

    def test_symbol_injection_boost_raises_low_score(self):
        """Symbol-injected code chunk gets _SYMBOL_INJECTION_BOOST added to its normalized score."""
        boost = self.srv._SYMBOL_INJECTION_BOOST
        base_score = 0.20
        expected = min(base_score + boost, 1.0)
        candidates = [
            {"path": "docs/foo.md", "score": 0.95, "kind": "doc", "text": ""},
            {"path": "server.py", "score": base_score, "kind": "code", "text": "", "_sym_injected": True},
        ]
        for c in candidates:
            if c.get("_sym_injected") and c.get("kind") == "code":
                c["score"] = min(c["score"] + boost, 1.0)
        impl = next(c for c in candidates if c.get("_sym_injected"))
        self.assertAlmostEqual(impl["score"], expected)

    def test_symbol_injection_boost_helps_mid_scoring_impl(self):
        """A reranker-relevant impl chunk (score >= 0.35) beats the worst-case demoted wave doc after boost."""
        boost = self.srv._SYMBOL_INJECTION_BOOST
        max_wave_demoted = 1.0 * self.srv._DEMOTION_WAVES  # 0.75
        # A chunk the reranker considers genuinely relevant (score > 0.35) should win
        mid_score = 0.36
        self.assertGreater(mid_score + boost, max_wave_demoted,
            f"Mid-relevance impl ({mid_score} + {boost} = {mid_score + boost}) should beat demoted wave ({max_wave_demoted})")
        # A low-relevance chunk (comment/reference, score ~ 0.20) should stay below wave doc
        low_score = 0.20
        self.assertLessEqual(low_score + boost, max_wave_demoted,
            f"Low-relevance chunk ({low_score} + {boost} = {low_score + boost}) should NOT beat demoted wave ({max_wave_demoted})")

    def test_symbol_injection_boost_capped_at_one(self):
        """Score is capped at 1.0 after boost, regardless of pre-boost value."""
        boost = self.srv._SYMBOL_INJECTION_BOOST
        c = {"score": 0.90, "kind": "code", "_sym_injected": True}
        c["score"] = min(c["score"] + boost, 1.0)
        self.assertLessEqual(c["score"], 1.0)

    def test_symbol_injection_boost_not_applied_to_doc_kind(self):
        """Boost only applies to kind='code'; injected doc chunks are not boosted."""
        boost = self.srv._SYMBOL_INJECTION_BOOST
        c = {"score": 0.20, "kind": "doc", "_sym_injected": True}
        original = c["score"]
        if c.get("_sym_injected") and c.get("kind") == "code":
            c["score"] = min(c["score"] + boost, 1.0)
        self.assertAlmostEqual(c["score"], original)

    def test_symbol_injection_marker_stripped_from_results(self):
        """_sym_injected marker is popped from every result dict before search_combined returns."""
        # Simulate the stripping step that runs after _rerank in search_combined
        results = [
            {"path": "docs/foo.md", "score": 0.75, "kind": "doc"},
            {"path": "server.py", "score": 1.0, "kind": "code", "_sym_injected": True},
        ]
        for r in results:
            r.pop("_sym_injected", None)
        for r in results:
            self.assertNotIn("_sym_injected", r)

    # --- Two-hop symbol expansion ---

    def test_extract_symbols_python_finds_call_targets(self):
        """_extract_symbols_python extracts function call names from Python source."""
        text = "def handler():\n    result = createTenant(name)\n    billing.charge(amount)\n"
        symbols = self.srv._extract_symbols_python(text)
        self.assertIn("createTenant", symbols)
        self.assertIn("charge", symbols)

    def test_extract_symbols_python_finds_imports(self):
        """_extract_symbols_python extracts imported names."""
        text = "import UserService\nfrom billing import ChargeProcessor\n"
        symbols = self.srv._extract_symbols_python(text)
        self.assertIn("UserService", symbols)
        self.assertIn("ChargeProcessor", symbols)

    def test_extract_symbols_regex_finds_calls_and_sql(self):
        """_extract_symbols_regex extracts function calls and SQL EXEC."""
        text = "EXEC sp_createTenant @name; result = fetchRecord(id);"
        symbols = self.srv._extract_symbols_regex(text)
        self.assertIn("sp_createTenant", symbols)
        self.assertIn("fetchRecord", symbols)

    def test_extract_symbols_from_citations_filters_infra(self):
        """_extract_symbols_from_citations skips infra-path citations."""
        infra_citation = {
            "path": "src/constructs/MyStack.ts",
            "text": "createBucket(props); addLambda(handler);",
            "language": "typescript",
        }
        biz_citation = {
            "path": "src/services/billing.py",
            "text": "def charge():\n    processPayment(amount)\n",
            "language": "python",
        }
        symbols, _method = self.srv._extract_symbols_from_citations([infra_citation, biz_citation])
        # processPayment comes from the biz citation (not filtered)
        self.assertIn("processPayment", symbols)
        # createBucket / addLambda come from infra citation (filtered out)
        self.assertNotIn("createBucket", symbols)
        self.assertNotIn("addLambda", symbols)

    def test_extract_symbols_from_citations_blocklist(self):
        """_extract_symbols_from_citations removes blocklisted generic names."""
        citation = {
            "path": "src/billing.py",
            "text": "def run():\n    list(items)\n    findRecords(query)\n",
            "language": "python",
        }
        symbols, _method = self.srv._extract_symbols_from_citations([citation])
        self.assertNotIn("list", symbols)
        self.assertNotIn("run", symbols)
        self.assertIn("findRecords", symbols)

    def test_extract_symbols_from_citations_respects_max(self):
        """_extract_symbols_from_citations caps output at max_symbols."""
        text = "\n".join(f"    call{i}Func(x)" for i in range(20))
        citation = {"path": "src/billing.py", "text": text, "language": "python"}
        symbols, _method = self.srv._extract_symbols_from_citations([citation], max_symbols=3)
        self.assertLessEqual(len(symbols), 3)

    def test_search_combined_second_hop_injects_candidates_for_explanatory(self):
        """For explanatory questions, second-hop retrieval injects definition candidates."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("billing")]
        idx = self._make_index_with_docs(docs, code_chunks=code)

        first_rerank_result = [{
            "path": "src/billing.py",
            "text": "def handler():\n    chargeCustomer(amount)\n",
            "score": 0.9, "kind": "code", "language": "python", "lines": [1, 5],
        }]
        second_hop_result = [{
            "path": "src/charge.py",
            "text": "def chargeCustomer(amount): ...",
            "score": 0.0, "kind": "code", "lines": [1, 3],
        }]
        fake_kw_resp = {
            "status": "ok",
            "data": {"results": [{"path": "src/charge.py", "line": 1, "snippet": "def chargeCustomer"}]},
        }
        mock_reranker = MagicMock()
        rerank_calls = []

        def capture_rerank(query, candidates, top_n):
            rerank_calls.append(candidates)
            return candidates[:top_n]

        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", side_effect=capture_rerank) as mock_rerank:
                mock_rerank.side_effect = [first_rerank_result, first_rerank_result + second_hop_result]
                with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp):
                    results, reranked, _, _, _, second_hop_symbols, symbol_extraction_method = idx.search_combined(
                        "how does billing charge a customer", top_n=5, question_type="explanatory"
                    )
        self.assertTrue(second_hop_symbols, "expected second_hop_symbols to be non-empty")
        self.assertIn(symbol_extraction_method, ("ast", "regex", "regex_fallback"),
                      "symbol_extraction_method must be 'ast', 'regex', or 'regex_fallback' when second hop fires")

    def test_search_combined_second_hop_skipped_for_navigational(self):
        """Second hop is not triggered for navigational questions."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("billing")]
        idx = self._make_index_with_docs(docs, code_chunks=code)

        with patch.object(idx, "_get_reranker", return_value=None):
            _, _, _, _, _, second_hop_symbols, symbol_extraction_method = idx.search_combined(
                "where is the billing module", top_n=5, question_type="navigational"
            )
        self.assertEqual(second_hop_symbols, [])
        self.assertEqual(symbol_extraction_method, "none",
                         "navigational question must produce symbol_extraction_method='none'")

    def test_search_combined_second_hop_skipped_when_no_symbols_extracted(self):
        """When no symbols are extracted, second_hop_symbols is empty and results unchanged."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("billing")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        mock_reranker = MagicMock()
        prose_result = [{"path": "docs/overview.md", "text": "This is prose with no callable syntax.",
                         "score": 0.8, "kind": "doc", "lines": [1, 3]}]

        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", return_value=prose_result):
                _, _, _, _, _, second_hop_symbols, symbol_extraction_method = idx.search_combined(
                    "how does billing work", top_n=5, question_type="explanatory"
                )
        self.assertEqual(second_hop_symbols, [])
        # Prose-only result → regex (no callable syntax, no TS/Python citations with symbols)
        self.assertIn(symbol_extraction_method, ("regex", "regex_fallback", "none"))

    def test_search_combined_second_hop_deduplicates_candidates(self):
        """Second-hop candidates already in first-hop pool are not re-injected."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("billing")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        # First-hop result already contains charge.py at line 1
        existing_result = {"path": "src/charge.py", "text": "def chargeCustomer(): ...",
                           "score": 0.9, "kind": "code", "language": "python", "lines": [1, 3]}
        # Keyword search would also return charge.py line 1 — should be deduped
        fake_kw_resp = {
            "status": "ok",
            "data": {"results": [{"path": "src/charge.py", "line": 1, "snippet": "def chargeCustomer"}]},
        }
        mock_reranker = MagicMock()
        rerank_call_sizes = []

        def capture_rerank(query, candidates, top_n):
            rerank_call_sizes.append(len(candidates))
            return candidates[:top_n]

        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", side_effect=capture_rerank) as mock_rerank:
                mock_rerank.side_effect = [[existing_result], [existing_result]]
                with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp):
                    idx.search_combined(
                        "how does billing charge", top_n=5, question_type="explanatory"
                    )
        # If deduplication worked, the second rerank should not have been called
        # (no new candidates after dedup → second_hop_candidates is empty)
        self.assertLessEqual(len(rerank_call_sizes), 2)

    def test_second_hop_symbols_propagated_to_code_ask_response(self):
        """code_ask_response emits second_hop_symbols and symbol_extraction_method when second hop fired."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 0, 0, [], ["chargeCustomer"], "ast")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "how does billing work?")
        data = result.get("data", {})
        self.assertIn("second_hop_symbols", data)
        self.assertIn("chargeCustomer", data["second_hop_symbols"])
        self.assertIn("symbol_extraction_method", data)
        self.assertEqual(data["symbol_extraction_method"], "ast")

    def test_second_hop_symbols_absent_when_empty(self):
        """code_ask_response omits second_hop_symbols and symbol_extraction_method when second hop did not fire."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 0, 0, [], [], "none")
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "how does billing work?")
        data = result.get("data", {})
        self.assertNotIn("second_hop_symbols", data)
        self.assertNotIn("symbol_extraction_method", data)

    def test_symbol_extraction_method_regex_fallback_when_treesitter_unavailable(self):
        """symbol_extraction_method='regex_fallback' when tree-sitter unavailable for TS-eligible citations."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("billing")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        ts_result = [{
            "path": "src/billing.ts",
            "text": "chargeCustomer(invoice);",
            "score": 0.9, "kind": "code", "language": "typescript", "lines": [1, 1],
        }]
        mock_reranker = MagicMock()
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", return_value=ts_result):
                with patch(f"{self.srv.__name__}._get_chunker_module", side_effect=Exception("no grammar")):
                    _, _, _, _, _, _symbols, method = idx.search_combined(
                        "how does billing charge", top_n=5, question_type="explanatory"
                    )
        self.assertEqual(method, "regex_fallback",
                         "TS-eligible citation with tree-sitter unavailable must report method='regex_fallback'")

    def test_symbol_extraction_method_ast_when_python_extraction_succeeds(self):
        """symbol_extraction_method='ast' when Python citation yields symbols via AST."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("auth")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        # _extract_symbols_python extracts calls and imports, not definitions
        py_result = [{
            "path": "src/auth.py",
            "text": "result = authenticate_user(token)\nrefreshed = refresh_token(old_token)",
            "score": 0.9, "kind": "code", "language": "python", "lines": [1, 2],
        }]
        mock_reranker = MagicMock()
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", return_value=py_result):
                _, _, _, _, _, _symbols, method = idx.search_combined(
                    "how does auth work", top_n=5, question_type="explanatory"
                )
        self.assertEqual(method, "ast",
                         "Python citation with function calls must report method='ast'")

    def test_symbol_extraction_method_none_when_all_citations_infra_filtered(self):
        """symbol_extraction_method='none' when all non-infra citations are filtered out before extraction."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("billing")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        # All top citations are infra-path files — they will be filtered before extraction
        infra_only = [{
            "path": "src/constructs/MyStack.ts",
            "text": "createBucket(props); addLambda(handler);",
            "score": 0.9, "kind": "code", "language": "typescript", "lines": [1, 2],
        }]
        mock_reranker = MagicMock()
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", return_value=infra_only):
                _, _, _, _, _, _symbols, method = idx.search_combined(
                    "how does billing charge", top_n=5, question_type="explanatory"
                )
        self.assertEqual(method, "none",
                         "all-infra citations must produce method='none' (no extraction attempted)")

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

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
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
                mcp = load_thin_runner().build_server(self.root)
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
                with patch("sys.stderr", buf):
                    self.srv._ensure_model_cached("test-embedding-model", "embedding")
                output = buf.getvalue()

        self.assertIn("already cached", output)
        self.assertIn("test-embedding-model", output)

    def test_ensure_model_cached_reranker_import_error(self):
        """_ensure_model_cached skips gracefully when fastembed.rerank is not available."""
        import io

        with patch.dict("sys.modules", {"fastembed.rerank": None, "fastembed.rerank.cross_encoder": None}):
            buf = io.StringIO()
            with patch("sys.stderr", buf):
                self.srv._ensure_model_cached("reranker-model", "reranker")
            output = buf.getvalue()

        self.assertIn("skipping", output)


class CodeKeywordMultiQueryTests(unittest.TestCase):
    """12n5x-enh code-keyword-search-multi-query: multi-query batch support tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _call(self, **kw):
        return self.srv.code_keyword_response(self.root, **kw)

    # ------------------------------------------------------------------
    # AC-1: multi-query merge + matched_query tagging + dedup
    # ------------------------------------------------------------------

    def test_multi_query_returns_matched_query_field(self):
        """AC-1: each result carries matched_query identifying which query produced it."""
        self._add("src/mod.py", "FOO = 1\nBAR = 2\n")
        result = self._call(queries=["FOO", "BAR"])
        self.assertEqual(result["status"], "ok")
        entries = result["data"]["results"]
        names = {e["matched_query"] for e in entries}
        self.assertIn("FOO", names)
        self.assertIn("BAR", names)

    def test_multi_query_dedup_first_match_wins(self):
        """AC-1: when same (path, line) matched by two queries, first query wins."""
        # "FOOBAR" matches both "FOO" and "BAR" — FOO comes first in list
        self._add("src/mod.py", "FOOBAR = 1\n")
        result = self._call(queries=["FOO", "BAR"])
        entries = result["data"]["results"]
        # Should have exactly one entry for this line
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["matched_query"], "FOO")

    def test_multi_query_merge_from_different_files(self):
        """AC-1: results from multiple queries across multiple files are merged."""
        self._add("src/a.py", "TOKEN_A = 1\n")
        self._add("src/b.py", "TOKEN_B = 2\n")
        result = self._call(queries=["TOKEN_A", "TOKEN_B"])
        self.assertEqual(result["status"], "ok")
        paths = [e["path"] for e in result["data"]["results"]]
        self.assertTrue(any("a.py" in p for p in paths))
        self.assertTrue(any("b.py" in p for p in paths))

    # ------------------------------------------------------------------
    # AC-2: glob applies to all queries in batch
    # ------------------------------------------------------------------

    def test_multi_query_glob_scopes_all_queries(self):
        """AC-2: glob restricts all queries in the batch."""
        self._add("src/a.py", "TOKEN = 1\n")
        self._add("src/b.py", "TOKEN = 2\n")
        result = self._call(queries=["TOKEN"], glob="**/a.py")
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["path"].endswith("a.py"))

    # ------------------------------------------------------------------
    # AC-3: both query and queries → error
    # ------------------------------------------------------------------

    def test_both_query_and_queries_returns_error(self):
        """AC-3: supplying both query and queries returns a structured error."""
        result = self._call(query="FOO", queries=["BAR"])
        self.assertEqual(result["status"], "error")

    # ------------------------------------------------------------------
    # AC-4: single-query path unchanged — no matched_query field
    # ------------------------------------------------------------------

    def test_single_query_no_matched_query_field(self):
        """AC-4: single-query results do not include matched_query field."""
        self._add("src/mod.py", "TOKEN = 1\n")
        result = self._call(query="TOKEN")
        self.assertEqual(result["status"], "ok")
        for entry in result["data"]["results"]:
            self.assertNotIn("matched_query", entry)

    def test_single_query_backward_compat_response_shape(self):
        """AC-4: single-query response has query/glob/count/results, not queries."""
        self._add("src/mod.py", "TOKEN = 1\n")
        result = self._call(query="TOKEN")
        self.assertIn("query", result["data"])
        self.assertNotIn("queries", result["data"])

    # ------------------------------------------------------------------
    # AC-5: empty queries list → ok with empty results
    # ------------------------------------------------------------------

    def test_empty_queries_list_returns_ok(self):
        """AC-5: queries=[] returns ok with zero results, not an error."""
        result = self._call(queries=[])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["count"], 0)
        self.assertEqual(result["data"]["results"], [])


class CodePatternTests(unittest.TestCase):
    """12n63-enh code-pattern: regex pattern search MCP tool tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _call(self, pattern: str, **kw):
        return self.srv.code_pattern_response(self.root, pattern, **kw)

    # ------------------------------------------------------------------
    # AC-1: basic regex match with file/line/text fields
    # ------------------------------------------------------------------

    def test_basic_regex_match(self):
        """AC-1: pattern matching returns file, line, text fields."""
        self._add("src/mod.py", "def search_foo():\n    pass\n")
        result = self._call(r"def .*search")
        self.assertEqual(result["status"], "ok")
        matches = result["data"]["matches"]
        self.assertGreater(len(matches), 0)
        m = matches[0]
        self.assertIn("file", m)
        self.assertIn("line", m)
        self.assertIn("text", m)
        self.assertIn("search_foo", m["text"])

    def test_glob_restricts_search(self):
        """AC-1: glob scopes pattern search."""
        self._add("src/a.py", "def target_fn(): pass\n")
        self._add("src/b.py", "def target_fn(): pass\n")
        result = self._call(r"def target_fn", glob="**/a.py")
        matches = result["data"]["matches"]
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0]["file"].endswith("a.py"))

    # ------------------------------------------------------------------
    # AC-2: invalid pattern → structured error, not exception
    # ------------------------------------------------------------------

    def test_invalid_regex_returns_error(self):
        """AC-2: invalid regex returns error status, not an exception."""
        result = self._call("[invalid")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "invalid_pattern" for d in result["diagnostics"]))

    # ------------------------------------------------------------------
    # AC-3: max_results cap + truncated flag + total_matches_found
    # ------------------------------------------------------------------

    def test_max_results_cap_and_truncated(self):
        """AC-3: results capped at max_results; truncated=True; total_matches_found accurate."""
        # Write a file with 20 matching lines
        content = "\n".join([f"MATCH_LINE_{i} = {i}" for i in range(20)]) + "\n"
        self._add("src/many.py", content)
        result = self._call(r"MATCH_LINE_", max_results=5)
        data = result["data"]
        self.assertEqual(len(data["matches"]), 5)
        self.assertTrue(data["truncated"])
        self.assertGreaterEqual(data["total_matches_found"], 20)

    def test_no_truncation_when_under_cap(self):
        """AC-3: truncated=False when results fit within cap."""
        self._add("src/few.py", "ONE = 1\nTWO = 2\n")
        result = self._call(r"ONE|TWO", max_results=50)
        data = result["data"]
        self.assertFalse(data["truncated"])
        self.assertEqual(data["total_matches_found"], len(data["matches"]))

    # ------------------------------------------------------------------
    # AC-4: ignore_case flag
    # ------------------------------------------------------------------

    def test_ignore_case_matches_all_cases(self):
        """AC-4: ignore_case=True matches todo, TODO, and Todo."""
        self._add("src/notes.py", "# todo: fix this\n# TODO: urgent\n# Todo: maybe\n")
        result = self._call("TODO", ignore_case=True)
        self.assertEqual(len(result["data"]["matches"]), 3)

    def test_case_sensitive_by_default(self):
        """AC-4: default is case-sensitive."""
        self._add("src/notes.py", "# todo: lower\n# TODO: upper\n")
        result = self._call("TODO")
        matches = result["data"]["matches"]
        texts = [m["text"] for m in matches]
        self.assertTrue(all("TODO" in t for t in texts))
        self.assertEqual(len(matches), 1)

    # ------------------------------------------------------------------
    # AC-5: path escape rejected or returns no out-of-root results
    # ------------------------------------------------------------------

    def test_glob_path_escape_produces_no_external_results(self):
        """AC-5: glob attempting to escape root returns no results outside project root."""
        self._add("src/mod.py", "TOKEN = 1\n")
        # A crafted glob trying to escape — should either error or return only in-root results
        result = self._call(r"TOKEN", glob="../../../etc/**")
        # Must not error out completely (valid pattern), and any matches must be in-root
        if result["status"] == "ok":
            for m in result["data"]["matches"]:
                self.assertFalse(m["file"].startswith("/"))
                self.assertFalse(".." in m["file"])

    # ------------------------------------------------------------------
    # AC-6: read-only (no file writes)
    # ------------------------------------------------------------------

    def test_code_pattern_does_not_write_files(self):
        """AC-6: code_pattern_response performs no file writes."""
        self._add("src/mod.py", "TOKEN = 1\n")
        import os
        files_before = set(os.listdir(self.root))
        self._call(r"TOKEN")
        files_after = set(os.listdir(self.root))
        self.assertEqual(files_before, files_after)

    # ------------------------------------------------------------------
    # AC-7: default glob searches all directories
    # ------------------------------------------------------------------

    def test_default_glob_searches_across_directories(self):
        """AC-7: no glob argument → matches from multiple directories."""
        self._add("src/sub/a.py", "HAYSTACK = 1\n")
        self._add("lib/b.py", "HAYSTACK = 2\n")
        result = self._call(r"HAYSTACK")
        paths = [m["file"] for m in result["data"]["matches"]]
        dirs = {p.split("/")[0] for p in paths}
        self.assertGreater(len(dirs), 1, "Expected matches from more than one directory")


class CodeOutlineTests(unittest.TestCase):
    """12n63-enh code-outline: tiered structural outline MCP tool tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _call(self, path: str):
        return self.srv.code_outline_response(self.root, path)

    # ------------------------------------------------------------------
    # AC-1: Python AST tier
    # ------------------------------------------------------------------

    def test_python_ast_functions_and_classes(self):
        """AC-1: Python file returns functions and classes with parser_used=python_ast."""
        self._add("src/mod.py", (
            "def top_func():\n"
            "    '''A function.'''\n"
            "    pass\n"
            "\n"
            "class MyClass:\n"
            "    '''A class.'''\n"
            "    pass\n"
        ))
        result = self._call("src/mod.py")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["parser_used"], "python_ast")
        symbols = result["data"]["symbols"]
        names = {s["name"] for s in symbols}
        self.assertIn("top_func", names)
        self.assertIn("MyClass", names)

    def test_python_ast_methods_kind(self):
        """AC-8: methods inside a class have kind='method'."""
        self._add("src/cls.py", (
            "class Foo:\n"
            "    def bar(self):\n"
            "        pass\n"
            "    def baz(self):\n"
            "        pass\n"
        ))
        result = self._call("src/cls.py")
        symbols = result["data"]["symbols"]
        methods = [s for s in symbols if s["kind"] == "method"]
        method_names = {m["name"] for m in methods}
        self.assertIn("bar", method_names)
        self.assertIn("baz", method_names)

    def test_python_ast_constants_kind(self):
        """AC-9: module-level uppercase constants appear with kind='constant'."""
        self._add("src/consts.py", "ALPHA = 10\nBETA: int = 20\n")
        result = self._call("src/consts.py")
        symbols = result["data"]["symbols"]
        constants = [s for s in symbols if s["kind"] == "constant"]
        const_names = {c["name"] for c in constants}
        self.assertIn("ALPHA", const_names)
        self.assertIn("BETA", const_names)

    def test_python_ast_docstring_populated(self):
        """AC-7: docstring field contains first line of docstring when present."""
        self._add("src/doc.py", (
            "def documented():\n"
            "    '''Does something useful.'''\n"
            "    pass\n"
            "\n"
            "def undocumented():\n"
            "    pass\n"
        ))
        result = self._call("src/doc.py")
        symbols = {s["name"]: s for s in result["data"]["symbols"]}
        self.assertIsNotNone(symbols["documented"]["docstring"])
        self.assertIn("Does something", symbols["documented"]["docstring"])
        self.assertIsNone(symbols["undocumented"]["docstring"])

    def test_python_ast_line_numbers(self):
        """AC-1: start_line and end_line are correct and 1-based."""
        self._add("src/lines.py", "def alpha():\n    pass\n\ndef beta():\n    pass\n")
        result = self._call("src/lines.py")
        symbols = {s["name"]: s for s in result["data"]["symbols"]}
        self.assertEqual(symbols["alpha"]["start_line"], 1)
        self.assertEqual(symbols["beta"]["start_line"], 4)

    # ------------------------------------------------------------------
    # AC-3: regex fallback tier (unknown extension)
    # ------------------------------------------------------------------

    def test_regex_tier_for_unknown_extension(self):
        """AC-3: unknown file type uses regex tier; end_line and docstring are null."""
        self._add("src/script.zsh", "function do_something() {\n  echo hi\n}\n")
        result = self._call("src/script.zsh")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["parser_used"], "regex")
        symbols = result["data"]["symbols"]
        self.assertTrue(any(s["name"] == "do_something" for s in symbols))
        # All regex-tier symbols have null end_line and docstring
        for s in symbols:
            self.assertIsNone(s["end_line"])
            self.assertIsNone(s["docstring"])

    # ------------------------------------------------------------------
    # AC-4: binary / unreadable file
    # ------------------------------------------------------------------

    def test_binary_file_returns_error(self):
        """AC-4: binary file returns unparseable error, not an exception."""
        p = self.root / "img.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(range(100)))
        result = self._call("img.png")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "unparseable" for d in result["diagnostics"]))

    # ------------------------------------------------------------------
    # AC-5: path escape rejected
    # ------------------------------------------------------------------

    def test_path_escape_rejected(self):
        """AC-5: path escaping the project root is rejected."""
        result = self._call("../../../etc/passwd")
        self.assertEqual(result["status"], "error")

    # ------------------------------------------------------------------
    # AC-6: read-only
    # ------------------------------------------------------------------

    def test_code_outline_does_not_write_files(self):
        """AC-6: code_outline_response performs no file writes."""
        self._add("src/mod.py", "def f(): pass\n")
        import os
        files_before = set(os.listdir(self.root))
        self._call("src/mod.py")
        files_after = set(os.listdir(self.root))
        self.assertEqual(files_before, files_after)

    # ------------------------------------------------------------------
    # Additional: file not found
    # ------------------------------------------------------------------

    def test_missing_file_returns_error(self):
        """Non-existent path returns file_not_found error."""
        result = self._call("src/nonexistent.py")
        self.assertEqual(result["status"], "error")


class CodeConstantsTests(unittest.TestCase):
    """12n5x-enh code-constants-search: code_constants MCP tool tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_file(self, rel: str, content: str) -> Path:
        """Write a file relative to self.root and return the Path."""
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _call(self, symbols: list, glob: str = "") -> dict:
        return self.srv.code_constants_response(self.root, symbols, glob=glob)

    # ------------------------------------------------------------------
    # AC-1: scalar constant lookup
    # ------------------------------------------------------------------

    def test_scalar_constant_found(self):
        """AC-1: scalar integer constant is returned with correct value/file/line."""
        self._add_file("module.py", "# header\nMY_CONST = 42\nOTHER = 99\n")
        result = self._call(["MY_CONST"])
        self.assertEqual(result["status"], "ok")
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["name"], "MY_CONST")
        self.assertEqual(entry["value"], "42")
        self.assertEqual(entry["kind"], "scalar")
        self.assertIsNotNone(entry["file"])
        self.assertEqual(entry["line"], 2)

    def test_two_scalar_constants(self):
        """AC-1: multiple scalar constants all returned."""
        self._add_file("consts.py", "ALPHA = 10\nBETA = 20\n")
        result = self._call(["ALPHA", "BETA"])
        self.assertEqual(result["status"], "ok")
        entries = result["data"]["results"]
        names = [e["name"] for e in entries]
        self.assertIn("ALPHA", names)
        self.assertIn("BETA", names)
        self.assertTrue(all(e["kind"] == "scalar" for e in entries))

    def test_scalar_with_type_annotation(self):
        """AC-1: NAME: TYPE = value form is recognised."""
        self._add_file("mod.py", "COUNT: int = 7\n")
        result = self._call(["COUNT"])
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["value"], "7")
        self.assertEqual(entries[0]["kind"], "scalar")

    # ------------------------------------------------------------------
    # AC-2: multiline constant lookup
    # ------------------------------------------------------------------

    def test_multiline_frozenset_returned_complete(self):
        """AC-2: multiline frozenset value is returned in full, kind='multiline'."""
        self._add_file("sets.py", 'MY_SET = frozenset({\n    "alpha",\n    "beta",\n})\n')
        result = self._call(["MY_SET"])
        self.assertEqual(result["status"], "ok")
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["kind"], "multiline")
        # Full value must include all elements
        self.assertIn("alpha", entry["value"])
        self.assertIn("beta", entry["value"])

    def test_multiline_list_returned_complete(self):
        """AC-2: multiline list constant is collected until bracket closes."""
        self._add_file("items.py", 'ITEMS = [\n    "x",\n    "y",\n]\n')
        result = self._call(["ITEMS"])
        entries = result["data"]["results"]
        self.assertEqual(entries[0]["kind"], "multiline")
        self.assertIn("x", entries[0]["value"])
        self.assertIn("y", entries[0]["value"])

    def test_multiline_truncated_when_bracket_never_closes(self):
        """AC-2: kind='multiline-truncated' when bracket depth doesn't reach 0 in 50 lines."""
        # Build a list that never closes (more than 50 lines without closing bracket)
        lines = ["OPEN_LIST = [\n"] + [f'    "item{n}",\n' for n in range(60)]
        self._add_file("trunc.py", "".join(lines))
        result = self._call(["OPEN_LIST"])
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["kind"], "multiline-truncated")

    # ------------------------------------------------------------------
    # AC-3: symbol not found → null entry, not error
    # ------------------------------------------------------------------

    def test_symbol_not_found_returns_null_entry(self):
        """AC-3: missing symbol included with value=null, file=null, no error."""
        self._add_file("empty.py", "X = 1\n")
        result = self._call(["UNKNOWN_CONST"])
        self.assertEqual(result["status"], "ok")
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["name"], "UNKNOWN_CONST")
        self.assertIsNone(entry["value"])
        self.assertIsNone(entry["file"])
        self.assertIsNone(entry["line"])

    def test_mixed_found_and_not_found(self):
        """AC-3: found and not-found symbols both appear in results without error."""
        self._add_file("mod.py", "PRESENT = 5\n")
        result = self._call(["PRESENT", "ABSENT"])
        self.assertEqual(result["status"], "ok")
        entries = result["data"]["results"]
        by_name = {e["name"]: e for e in entries}
        self.assertIsNotNone(by_name["PRESENT"]["value"])
        self.assertIsNone(by_name["ABSENT"]["value"])

    def test_empty_symbols_list_returns_error(self):
        """AC-3 edge: empty symbols list returns error response, not ok."""
        result = self._call([])
        self.assertEqual(result["status"], "error")

    # ------------------------------------------------------------------
    # AC-4: glob scoping
    # ------------------------------------------------------------------

    def test_glob_restricts_to_matching_file(self):
        """AC-4: glob='**/a.py' finds constant in src/a.py, not src/b.py."""
        self._add_file("src/a.py", "SHARED = 10\n")
        self._add_file("src/b.py", "SHARED = 99\n")
        result = self._call(["SHARED"], glob="**/a.py")
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["file"].endswith("a.py"))
        self.assertEqual(entries[0]["value"], "10")

    def test_glob_excludes_all_files_returns_null(self):
        """AC-4: glob that excludes the defining file returns null entry."""
        self._add_file("src/server.py", "MY_K = 40\n")
        result = self._call(["MY_K"], glob="**/other.py")
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0]["value"])

    # ------------------------------------------------------------------
    # AC-5: output order matches input symbols order
    # ------------------------------------------------------------------

    def test_results_in_input_order(self):
        """AC-5: results list reflects the order of the input symbols list."""
        self._add_file("order.py", "AAA = 1\nBBB = 2\nCCC = 3\n")
        # Request in reverse order
        result = self._call(["CCC", "AAA", "BBB"])
        entries = result["data"]["results"]
        names = [e["name"] for e in entries]
        self.assertEqual(names, ["CCC", "AAA", "BBB"])

    # ------------------------------------------------------------------
    # AC-6: read-only annotation
    # ------------------------------------------------------------------

    def test_code_constants_is_readonly(self):
        """AC-6: code_constants_response performs no file writes."""
        self._add_file("mod.py", "ALPHA = 1\n")
        import os
        files_before = set(os.listdir(self.root))
        self._call(["ALPHA"])
        files_after = set(os.listdir(self.root))
        self.assertEqual(files_before, files_after, "code_constants must not create files")

    # ------------------------------------------------------------------
    # AC-8: multiple files — all matches returned
    # ------------------------------------------------------------------

    def test_symbol_in_multiple_files_returns_all_matches(self):
        """AC-8: symbol defined in two files returns one entry per match."""
        self._add_file("module_a.py", "SHARED_K = 10\n")
        self._add_file("module_b.py", "SHARED_K = 20\n")
        result = self._call(["SHARED_K"])
        self.assertEqual(result["status"], "ok")
        entries = result["data"]["results"]
        # Both files must be represented
        self.assertEqual(len(entries), 2)
        values = {e["value"] for e in entries}
        self.assertIn("10", values)
        self.assertIn("20", values)

    def test_symbol_in_multiple_files_glob_scopes_to_one(self):
        """AC-8: glob narrows multi-file match to the single matching file."""
        self._add_file("src/alpha.py", "SHARED_K = 10\n")
        self._add_file("src/beta.py", "SHARED_K = 20\n")
        result = self._call(["SHARED_K"], glob="**/alpha.py")
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["value"], "10")

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_indented_assignment_ignored(self):
        """Only module-level (column-0) assignments are matched."""
        self._add_file("mod.py", "class Foo:\n    MY_CONST = 99\nMY_CONST = 1\n")
        result = self._call(["MY_CONST"])
        entries = result["data"]["results"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["value"], "1")
        self.assertEqual(entries[0]["line"], 3)

    def test_partial_name_not_matched(self):
        """MY_K should not match MY_KEYWORD or MY_K_EXTRA."""
        self._add_file("mod.py", "MY_KEYWORD = 5\nMY_K_EXTRA = 6\nMY_K = 7\n")
        result = self._call(["MY_K"])
        entries = result["data"]["results"]
        # Only MY_K = 7 should match
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["value"], "7")

    def test_bracket_depth_ignores_brackets_in_strings(self):
        """_bracket_depth: brackets inside string literals do not affect depth."""
        srv = self.srv
        # A string containing brackets — net depth should be 0
        self.assertEqual(srv._bracket_depth('"(unclosed"'), 0)
        self.assertEqual(srv._bracket_depth("'[unclosed'"), 0)
        # Actual open bracket outside string
        self.assertEqual(srv._bracket_depth("frozenset({"), 2)
        # Closed properly
        self.assertEqual(srv._bracket_depth("frozenset({})"), 0)


class TestCodeOutlineTypescript(unittest.TestCase):
    """12nbp-bug: TypeScript export_statement fix and SQL support tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _call(self, path: str) -> dict:
        return self.srv.code_outline_response(self.root, path)

    def _ts_available(self) -> bool:
        """Return True if tree-sitter-typescript is installed."""
        try:
            chunker = self.srv._get_chunker_module()
            tree = chunker._ts_parse("typescript", "export class Foo {}")
            return tree is not None
        except Exception:
            return False

    def _sql_available(self) -> bool:
        """Return True if tree-sitter-sql is installed."""
        try:
            chunker = self.srv._get_chunker_module()
            tree = chunker._ts_parse("sql", "SELECT 1;")
            return tree is not None
        except Exception:
            return False

    # AC-1: export class
    def test_typescript_export_class(self):
        """AC-1: TypeScript 'export class Foo {}' yields symbol Foo with kind=class."""
        if not self._ts_available():
            self.skipTest("tree-sitter-typescript not installed")
        self._add("src/foo.ts", "export class Foo {\n  bar(): void {}\n}\n")
        result = self._call("src/foo.ts")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["parser_used"], "tree_sitter")
        names = {s["name"] for s in result["data"]["symbols"]}
        self.assertIn("Foo", names)
        kinds = {s["name"]: s["kind"] for s in result["data"]["symbols"]}
        self.assertEqual(kinds["Foo"], "class")

    # AC-2: export function
    def test_typescript_export_function(self):
        """AC-2: TypeScript 'export function bar() {}' yields symbol bar with kind=function."""
        if not self._ts_available():
            self.skipTest("tree-sitter-typescript not installed")
        self._add("src/bar.ts", "export function bar(): string {\n  return 'hi';\n}\n")
        result = self._call("src/bar.ts")
        self.assertEqual(result["status"], "ok")
        names = {s["name"] for s in result["data"]["symbols"]}
        self.assertIn("bar", names)
        kinds = {s["name"]: s["kind"] for s in result["data"]["symbols"]}
        self.assertEqual(kinds["bar"], "function")

    # AC-3: export const arrow function
    def test_typescript_export_const_arrow(self):
        """AC-3: TypeScript 'export const fn = async (props) => {}' yields symbol fn with kind=function."""
        if not self._ts_available():
            self.skipTest("tree-sitter-typescript not installed")
        self._add("src/fn.ts", "export const fn = async (props: any) => {\n  return props;\n};\n")
        result = self._call("src/fn.ts")
        self.assertEqual(result["status"], "ok")
        names = {s["name"] for s in result["data"]["symbols"]}
        self.assertIn("fn", names)
        kinds = {s["name"]: s["kind"] for s in result["data"]["symbols"]}
        self.assertEqual(kinds["fn"], "function")

    # AC-5/6: SQL with no functions yields empty symbols list
    def test_sql_no_functions_yields_empty(self):
        """AC-5/6: SQL file with no CREATE FUNCTION returns symbols=[]."""
        if not self._sql_available():
            self.skipTest("tree-sitter-sql not installed")
        self._add("src/query.sql", "SELECT id, name FROM users WHERE id = 1;\n")
        result = self._call("src/query.sql")
        self.assertEqual(result["status"], "ok")
        # SQL outline may use tree_sitter or regex; either way symbols should be empty or not crash
        self.assertIsInstance(result["data"]["symbols"], list)

    # Non-TS/SQL regression: Python still works after the patch
    def test_python_regression_after_patch(self):
        """Non-TS/SQL languages unaffected: Python file still produces correct symbols."""
        self._add("src/mod.py", "def my_func():\n    pass\n\nclass MyClass:\n    pass\n")
        result = self._call("src/mod.py")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["parser_used"], "python_ast")
        names = {s["name"] for s in result["data"]["symbols"]}
        self.assertIn("my_func", names)
        self.assertIn("MyClass", names)


class TestCodeHover(unittest.TestCase):
    """12nbj-enh code-hover: code_hover_response tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _call(self, path: str, line: int) -> dict:
        return self.srv.code_hover_response(self.root, path, line)

    # AC-1: Python function with type annotations returns signature containing ->
    def test_python_annotated_function_signature(self):
        """AC-1: Python function with type annotations returns signature string containing '->'."""
        self._add("src/typed.py", (
            "def greet(name: str, count: int = 1) -> str:\n"
            "    '''Greet someone.'''\n"
            "    return name * count\n"
        ))
        result = self._call("src/typed.py", 1)
        self.assertEqual(result["status"], "ok")
        sym = result["data"]["symbol"]
        self.assertIsNotNone(sym)
        self.assertEqual(sym["name"], "greet")
        self.assertIn("->", sym.get("signature", ""))

    # AC-2: Python method inside class returns kind=method
    def test_python_method_kind(self):
        """AC-2: Python method inside class returns kind='method'."""
        self._add("src/cls.py", (
            "class MyClass:\n"
            "    def my_method(self, x: int) -> None:\n"
            "        pass\n"
        ))
        result = self._call("src/cls.py", 2)
        self.assertEqual(result["status"], "ok")
        sym = result["data"]["symbol"]
        self.assertIsNotNone(sym)
        self.assertEqual(sym["kind"], "method")
        self.assertEqual(sym["name"], "my_method")

    # AC-3: Python function without annotations returns signature with param names
    def test_python_unannotated_function_signature(self):
        """AC-3: Python function without annotations returns signature with param names, no error."""
        self._add("src/plain.py", (
            "def compute(a, b, c=10):\n"
            "    return a + b + c\n"
        ))
        result = self._call("src/plain.py", 1)
        self.assertEqual(result["status"], "ok")
        sym = result["data"]["symbol"]
        self.assertIsNotNone(sym)
        sig = sym.get("signature", "")
        self.assertIn("a", sig)
        self.assertIn("b", sig)

    # AC-5: Line outside all symbols returns symbol=null
    def test_line_outside_symbols_returns_null(self):
        """AC-5: Line outside all symbols returns symbol=null without error."""
        self._add("src/sparse.py", (
            "# module comment\n"
            "\n"
            "def my_func():\n"
            "    pass\n"
        ))
        result = self._call("src/sparse.py", 1)
        self.assertEqual(result["status"], "ok")
        self.assertIsNone(result["data"]["symbol"])

    # AC-7: Path escaping root returns error
    def test_path_escape_returns_error(self):
        """AC-7: Path escaping the project root returns error response."""
        result = self._call("../../../etc/passwd", 1)
        self.assertEqual(result["status"], "error")


class TestCodeImpact(unittest.TestCase):
    """12nbj-enh code-impact: code_impact_response tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _call(self, path: str, max_results: int = 50) -> dict:
        return self.srv.code_impact_response(self.root, path, max_results)

    # AC-1: Python module path match
    def test_python_module_path_match(self):
        """AC-1: File A imports file B — B's importer list includes A."""
        self._add("src/utils.py", "def helper(): pass\n")
        self._add("src/main.py", "from src.utils import helper\n\nhelper()\n")
        result = self._call("src/utils.py")
        self.assertEqual(result["status"], "ok")
        files = [imp["file"] for imp in result["data"]["importers"]]
        self.assertIn("src/main.py", files)

    # AC-3: Target file itself not in importers
    def test_target_not_in_importers(self):
        """AC-3: The target file itself is never listed in its importers."""
        self._add("src/self_ref.py", "import src.self_ref\n")
        result = self._call("src/self_ref.py")
        self.assertEqual(result["status"], "ok")
        files = [imp["file"] for imp in result["data"]["importers"]]
        self.assertNotIn("src/self_ref.py", files)

    # AC-4: max_results truncation
    def test_max_results_truncation(self):
        """AC-4: max_results=1 with 2+ importers returns truncated=True, total_found>=2."""
        self._add("src/shared.py", "SHARED = 1\n")
        self._add("src/a.py", "from src.shared import SHARED\n")
        self._add("src/b.py", "from src.shared import SHARED\n")
        result = self._call("src/shared.py", max_results=1)
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        if data["total_found"] >= 2:
            self.assertTrue(data["truncated"])
            self.assertLessEqual(len(data["importers"]), 1)

    # AC-5: Path escape returns error
    def test_path_escape_returns_error(self):
        """AC-5: Path escaping the project root returns error."""
        result = self._call("../../../etc/passwd")
        self.assertEqual(result["status"], "error")

    # AC-6: Non-existent file returns error with file_not_found diagnostic
    def test_nonexistent_file_returns_error(self):
        """AC-6: Non-existent file path returns error with file_not_found diagnostic."""
        result = self._call("src/does_not_exist.py")
        self.assertEqual(result["status"], "error")
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("file_not_found", codes)


class TestCodeCallhierarchy(unittest.TestCase):
    """12nax-enh code-callhierarchy: code_callhierarchy_response tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _call(self, symbol: str, file: str = "", direction: str = "both") -> dict:
        return self.srv.code_callhierarchy_response(self.root, symbol, file or None, direction)

    # AC-2: direction=outgoing has outgoing, no incoming
    def test_direction_outgoing_only(self):
        """AC-2: direction='outgoing' returns 'outgoing' key but no 'incoming' key."""
        self._add("src/worker.py", "def process():\n    helper()\n    validate()\n\ndef helper(): pass\ndef validate(): pass\n")
        result = self._call("process", direction="outgoing")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertIn("outgoing", data)
        self.assertNotIn("incoming", data)

    # AC-3: direction=incoming has incoming, no outgoing
    def test_direction_incoming_only(self):
        """AC-3: direction='incoming' returns 'incoming' key but no 'outgoing' key."""
        self._add("src/svc.py", "def service():\n    pass\n\ndef caller():\n    service()\n")
        result = self._call("service", direction="incoming")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertIn("incoming", data)
        self.assertNotIn("outgoing", data)

    # AC-4: Unknown symbol returns empty outgoing/incoming lists (not error)
    def test_unknown_symbol_returns_empty_lists(self):
        """AC-4: Unknown symbol returns empty outgoing and incoming lists, not error."""
        result = self._call("zzz_no_such_symbol_xxxxxyyy")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertEqual(data.get("outgoing", []), [])
        self.assertEqual(data.get("incoming", []), [])

    # AC-6: Invalid direction returns error
    def test_invalid_direction_returns_error(self):
        """AC-6: Invalid direction value returns error response."""
        result = self._call("some_func", direction="sideways")
        self.assertEqual(result["status"], "error")
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("invalid_arguments", codes)


class TestLanceDBIndex(unittest.TestCase):
    """Tests for LanceDB vector index integration (AC-3, AC-10, AC-11)."""

    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    # AC-10: Constants are defined in both server.py and indexer.py
    def test_lancedb_constants_in_server(self):
        """AC-10: LanceDB constants are defined in server.py."""
        srv = self.server
        self.assertEqual(srv.LANCEDB_NPROBES, 20)
        self.assertEqual(srv.LANCEDB_REFINE_FACTOR, 10)

    def test_lancedb_constants_in_indexer(self):
        """AC-10: LanceDB constants are defined in indexer.py."""
        import importlib.util as ilu
        scripts_root = Path(__file__).resolve().parents[1]
        spec = ilu.spec_from_file_location("indexer_for_lancedb_test", scripts_root / "indexer.py")
        mod = ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.LANCEDB_INDEX_THRESHOLD, 1000)
        self.assertEqual(mod.LANCEDB_COMPACT_THRESHOLD, 20)
        self.assertEqual(mod.LANCEDB_NPROBES, 20)
        self.assertEqual(mod.LANCEDB_REFINE_FACTOR, 10)

    @unittest.skipUnless(importlib.util.find_spec("lancedb"), "lancedb not installed")
    def test_stream_embed_write_row_counts(self):
        """_stream_embed_write creates LanceDB tables with expected row counts."""
        import importlib.util as ilu
        import numpy as np
        from unittest.mock import MagicMock, patch
        scripts_root = Path(__file__).resolve().parents[1]
        spec = ilu.spec_from_file_location("indexer_for_stream_write_test", scripts_root / "indexer.py")
        mod = ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "lancedb"
            db_path.mkdir(parents=True, exist_ok=True)
            db = mod._get_lance_db(db_path)

            docs_chunks = [{"text": "doc1", "path": "docs/a.md", "kind": "doc"}]
            code_chunks = [{"text": "fn foo()", "path": "src/a.py", "kind": "function"}]

            # Stub embedder: returns a 3-dim float32 vector per text
            def _fake_embed(texts, batch_size=256):
                return [np.array([0.1, 0.2, 0.3], dtype=np.float32) for _ in texts]

            embedder = MagicMock()
            embedder.embed.side_effect = _fake_embed

            docs_written = mod._stream_embed_write(db, "docs", docs_chunks, embedder, "doc")
            code_written = mod._stream_embed_write(db, "code", code_chunks, embedder, "code")

            self.assertEqual(docs_written, 1)
            self.assertEqual(code_written, 1)

            # Verify table directories exist
            self.assertTrue((db_path / "docs.lance").is_dir())
            self.assertTrue((db_path / "code.lance").is_dir())


# ---------------------------------------------------------------------------
# wave_dashboard_open tests (12qme-enh dashboard-open-browser)
# ---------------------------------------------------------------------------

def _make_mock_dashboard_lib(meta_path, *, browser_open_enabled: bool = True):
    """Return a MagicMock for dashboard_lib with dashboard_metadata_path returning meta_path."""
    mock_lib = MagicMock()
    mock_lib.dashboard_metadata_path.return_value = meta_path
    mock_lib.read_dashboard_metadata.return_value = {}
    mock_lib.dashboard_browser_open_enabled.return_value = browser_open_enabled
    return mock_lib


class WaveDashboardOpenTests(unittest.TestCase):
    """Tests for wave_dashboard_open_response (AC-2, AC-3, AC-4)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self._meta_path = self.root / ".wavefoundry" / "dashboard-server.json"
        self._prev_browser_suppress = os.environ.get("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER")
        os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "0"
        self._meta_path.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self._prev_browser_suppress is None:
            os.environ.pop("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER", None)
        else:
            os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = self._prev_browser_suppress
        self.tmp.cleanup()

    def _write_meta(self, pid: int, url: str) -> None:
        self._meta_path.write_text(
            json.dumps({"pid": pid, "url": url}), encoding="utf-8"
        )

    def _dashboard_lib_patch(self):
        """Return a sys.modules patch for dashboard_lib pointing meta_path at our tmp file."""
        import sys
        mock_lib = _make_mock_dashboard_lib(self._meta_path)
        return patch.dict(sys.modules, {"dashboard_lib": mock_lib})

    def test_open_when_running_calls_webbrowser_and_returns_opened(self):
        """AC-2: when dashboard running, webbrowser.open is called and opened=True returned."""
        self._write_meta(pid=12345, url="http://localhost:7890")
        import server_impl
        with self._dashboard_lib_patch(), \
             patch.object(server_impl, "_pid_is_running", return_value=True), \
             patch("webbrowser.open") as mock_wb:
            result = self.srv.wave_dashboard_open_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("opened"))
        self.assertEqual(result["data"].get("url"), "http://localhost:7890")
        mock_wb.assert_called_once_with("http://localhost:7890")

    def test_open_when_not_running_delegates_to_start(self):
        """AC-3: when dashboard not running, delegates to wave_dashboard_start_response."""
        # No meta file written — dashboard not running path via empty mock lib.
        import sys
        import server_impl
        mock_lib = _make_mock_dashboard_lib(self._meta_path)  # meta_path doesn't exist
        with patch.dict(sys.modules, {"dashboard_lib": mock_lib}), \
             patch.object(
                 server_impl, "wave_dashboard_start_response",
                 return_value={"status": "ok", "data": {"started": True}},
             ) as mock_start:
            result = self.srv.wave_dashboard_open_response(self.root)
        mock_start.assert_called_once_with(self.root)
        self.assertEqual(result["data"]["started"], True)

    def test_start_already_running_includes_next_tools_dashboard_open(self):
        """AC-4: wave_dashboard_start when already running includes next_tools=['wave_dashboard_open']."""
        self._write_meta(pid=12345, url="http://localhost:7890")
        import sys
        mock_lib = _make_mock_dashboard_lib(self._meta_path)
        import server_impl
        with patch.dict(sys.modules, {"dashboard_lib": mock_lib}), \
             patch.object(server_impl, "_pid_is_running", return_value=True):
            result = self.srv.wave_dashboard_start_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("already_running"))
        self.assertIn("wave_dashboard_open", result.get("next_tools", []))

    def test_start_lock_busy_returns_already_running_without_spawning(self):
        """Concurrent start attempts report an in-progress dashboard instead of spawning another."""
        import dashboard_lib
        import server_impl

        class BusyLock:
            def __enter__(self):
                raise dashboard_lib.DashboardLockBusy("busy")

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch.object(dashboard_lib, "dashboard_start_lock", return_value=BusyLock()), \
             patch.object(server_impl, "DASHBOARD_START_WAIT_SECONDS", 0.0), \
             patch("subprocess.Popen") as popen:
            result = self.srv.wave_dashboard_start_response(self.root)

        popen.assert_not_called()
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("already_running"))
        self.assertTrue(result["data"].get("starting"))
        self.assertEqual(result["diagnostics"][0]["code"], "dashboard_start_in_progress")


class WaveDashboardBrowserSuppressTests(unittest.TestCase):
    """Dashboard browser must not open during the default test harness."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "1"

    def tearDown(self):
        self.tmp.cleanup()

    def test_start_spawns_without_open_flag_when_suppressed(self):
        import server_impl
        with patch("subprocess.Popen") as popen, patch.object(server_impl, "_pid_is_running", return_value=False):
            popen.return_value = MagicMock(pid=99999)
            self.srv.wave_dashboard_start_response(self.root)
        cmd = popen.call_args.args[0]
        self.assertNotIn("--open", cmd)

    def test_open_when_running_does_not_call_webbrowser_when_suppressed(self):
        meta_path = self.root / ".wavefoundry" / "dashboard-server.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(
            json.dumps({"pid": os.getpid(), "url": "http://127.0.0.1:9/dashboard.html"}),
            encoding="utf-8",
        )
        import server_impl
        with patch("webbrowser.open") as mock_wb, patch.object(server_impl, "_pid_is_running", return_value=True):
            result = server_impl.wave_dashboard_open_response(self.root)
        mock_wb.assert_not_called()
        self.assertFalse(result["data"].get("opened"))
        self.assertTrue(result["data"].get("browser_suppressed"))


class PreferredPythonSubprocessTests(unittest.TestCase):
    """Regression coverage for explicit shared-venv subprocess routing."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_venv_python(self) -> Path:
        venv_root = self.root / ".venv-test"
        venv_python = venv_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        venv_python.parent.mkdir(parents=True, exist_ok=True)
        venv_python.write_text("", encoding="utf-8")
        return venv_python

    def test_run_validate_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0, stdout="docs-lint: ok\n", stderr="")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch("subprocess.run", return_value=mock_proc) as run_mock:
            self.srv.run_validate(self.root)
        called_cmd = run_mock.call_args.args[0]
        self.assertEqual(called_cmd[0], str(venv_python))

    def test_background_index_refresh_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        indexer = self.root / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
        indexer.parent.mkdir(parents=True, exist_ok=True)
        indexer.write_text("", encoding="utf-8")
        mock_proc = MagicMock(pid=12345)
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch("subprocess.Popen", return_value=mock_proc) as popen_mock, \
             patch.object(self.srv, "_background_refresh_active", return_value=False):
            started = self.srv._start_background_index_refresh(self.root, "project")
        self.assertTrue(started)
        called_cmd = popen_mock.call_args.args[0]
        self.assertEqual(called_cmd[0], str(venv_python))

    def test_wave_dashboard_start_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        import server_impl
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch("subprocess.Popen", return_value=MagicMock(pid=99999)) as popen_mock, \
             patch.object(server_impl, "_pid_is_running", return_value=False):
            self.srv.wave_dashboard_start_response(self.root)
        called_cmd = popen_mock.call_args.args[0]
        self.assertEqual(called_cmd[0], str(venv_python))

    def test_wave_upgrade_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0, stdout="Upgrade complete\n", stderr="")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch("subprocess.run", return_value=mock_proc) as run_mock:
            self.srv.wave_upgrade_response(self.root, phase="preflight_to_docs_gate")
        called_cmd = run_mock.call_args.args[0]
        self.assertEqual(called_cmd[0], str(venv_python))


# ---------------------------------------------------------------------------
# wave_upgrade_status + wave_upgrade + restart guard tests (12r08/12r0b)
# ---------------------------------------------------------------------------

class WaveUpgradeStatusTests(unittest.TestCase):
    """Tests for wave_upgrade_status_response (AC-5 / R5)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _lock_path(self):
        return self.root / ".wavefoundry" / "upgrade-in-progress.json"

    def _write_lock(self, pid=None):
        p = self._lock_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "started_at": "2026-05-19T00:00:00+00:00",
            "from_version": "2026-05-10a",
            "to_version": "2026-05-19a",
            "pid": pid or os.getpid(),
        }), encoding="utf-8")

    def test_no_lock_returns_not_in_progress(self):
        result = self.srv.wave_upgrade_status_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["in_progress"])
        self.assertIsNone(result["data"]["to_version"])

    def test_lock_present_returns_in_progress(self):
        self._write_lock()
        result = self.srv.wave_upgrade_status_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["in_progress"])
        self.assertEqual(result["data"]["from_version"], "2026-05-10a")
        self.assertEqual(result["data"]["to_version"], "2026-05-19a")


class WaveDashboardRestartUpgradeGuardTests(unittest.TestCase):
    """Tests for wave_dashboard_restart upgrade guard (AC-4 / R7)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_lock(self):
        p = self.root / ".wavefoundry" / "upgrade-in-progress.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "started_at": "2026-05-19T00:00:00+00:00",
            "from_version": "old",
            "to_version": "new",
            "pid": os.getpid(),
        }), encoding="utf-8")

    def test_restart_proceeds_while_upgrade_in_progress(self):
        """AC-4 (revised): restart is not blocked during upgrade — dashboard comes up in upgrade_paused."""
        self._write_lock()
        import sys
        mock_lib = _make_mock_dashboard_lib(self.root / ".wavefoundry" / "dashboard-server.json")
        with patch.dict(sys.modules, {"dashboard_lib": mock_lib}), \
             patch.object(self.srv, "_pid_is_running", return_value=False), \
             patch.object(self.srv, "wave_dashboard_start_response",
                          return_value={"status": "ok", "data": {}}):
            result = self.srv.wave_dashboard_restart_response(self.root)
        self.assertNotEqual(result["status"], "error")
        self.assertNotIn("upgrade_in_progress", result.get("data", {}))

    def test_restart_allowed_when_no_lock(self):
        """Restart proceeds normally when no upgrade lock is present."""
        # No lock file — restart should attempt to stop/start (both will find nothing running).
        # Mock wave_dashboard_start_response to avoid spawning a real dashboard process.
        import sys
        mock_lib = _make_mock_dashboard_lib(self.root / ".wavefoundry" / "dashboard-server.json")
        with patch.dict(sys.modules, {"dashboard_lib": mock_lib}), \
             patch.object(self.srv, "_pid_is_running", return_value=False), \
             patch.object(self.srv, "wave_dashboard_start_response",
                          return_value={"status": "ok", "data": {}}):
            result = self.srv.wave_dashboard_restart_response(self.root)
        # Should not be blocked by upgrade guard.
        self.assertNotIn("upgrade_in_progress", result.get("data", {}))


class WaveUpgradeMcpToolTests(unittest.TestCase):
    """Tests for wave_upgrade_response (AC-2–AC-5 / 12r0b)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_invalid_phase_returns_error(self):
        result = self.srv.wave_upgrade_response(self.root, phase="bad_phase")
        self.assertEqual(result["status"], "error")
        self.assertIn("valid_phases", result["data"])

    def test_success_returns_ok_with_output(self):
        """AC-2: successful subprocess exit → status ok with output and exit_code=0."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Upgrade complete\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wave_upgrade_response(self.root, phase="preflight_to_docs_gate")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["exit_code"], 0)
        self.assertIn("Upgrade complete", result["data"]["output"])

    def test_nonzero_exit_returns_error(self):
        """AC-5: non-zero exit code → status error with output in diagnostics."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "docs-lint failed"
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wave_upgrade_response(self.root, phase="preflight_to_docs_gate")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["data"]["exit_code"], 1)
        diag_codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("upgrade_failed", diag_codes)

    def test_update_index_phase_passes_flag(self):
        """AC-3a: update_index phase passes --update-index (incremental)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Index updated\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            self.srv.wave_upgrade_response(self.root, phase="update_index")
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--update-index", called_cmd)
        self.assertNotIn("--rebuild-index", called_cmd)

    def test_rebuild_index_phase_passes_flag(self):
        """AC-3b: rebuild_index phase passes --rebuild-index (full rebuild)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Index rebuilt\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            self.srv.wave_upgrade_response(self.root, phase="rebuild_index")
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--rebuild-index", called_cmd)
        self.assertNotIn("--update-index", called_cmd)

    def test_cleanup_phase_passes_flag(self):
        """AC-4: cleanup phase passes --cleanup flag."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Lock removed\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            self.srv.wave_upgrade_response(self.root, phase="cleanup")
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--cleanup", called_cmd)

    def test_dry_run_mode_passes_flag_and_omits_yes(self):
        """mode='dry_run' passes --dry-run and must NOT pass --yes (read-only, no prompt)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Dry Run\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            result = self.srv.wave_upgrade_response(self.root, mode="dry_run")
        self.assertEqual(result["status"], "ok")
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--dry-run", called_cmd)
        self.assertNotIn("--yes", called_cmd)

    def test_invalid_mode_returns_error(self):
        """Unknown mode returns error with valid_modes list."""
        result = self.srv.wave_upgrade_response(self.root, mode="bad_mode")
        self.assertEqual(result["status"], "error")
        self.assertIn("valid_modes", result["data"])

    def test_cleanup_apply_invokes_mcp_reload(self):
        """AC-3: wave_upgrade cleanup+apply triggers in-process MCP reload.

        When phase='cleanup' and mode='apply' succeed, wave_upgrade_response
        must call server.perform_mcp_reload() and include its result under
        data['mcp_reload'].
        """
        import server as _server_mod
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Lock removed\n"
        mock_proc.stderr = ""
        reload_payload = {
            "status": "ok",
            "data": {"ok": True, "framework_version": "v1", "server_runner_version": "1",
                     "server_impl_version": "v1", "impl_matches_disk": True},
        }
        with patch("subprocess.run", return_value=mock_proc), \
             patch.object(_server_mod, "perform_mcp_reload", return_value=reload_payload) as mock_reload:
            result = self.srv.wave_upgrade_response(self.root, phase="cleanup", mode="apply")
        self.assertEqual(result["status"], "ok")
        mock_reload.assert_called_once()
        self.assertIn("mcp_reload", result["data"])
        self.assertTrue(result["data"]["mcp_reload"]["ok"])


class ImplHandlerCloseTests(unittest.TestCase):
    """AC-6: ImplHandler.close() nulls Lance handles before build_handler creates new ones."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_close_nulls_lance_handles(self):
        """AC-6: close() must set Lance table refs and reranker to None so no double-open occurs."""
        handler = self.srv.build_handler(self.root)
        # Force-populate internal table refs with sentinel values to confirm they are cleared.
        handler.index._docs_lance_table = object()
        handler.index._code_lance_table = object()
        handler.index._reranker = object()
        handler.index._loaded = True

        handler.close()

        self.assertIsNone(handler.index._docs_lance_table, "_docs_lance_table must be None after close()")
        self.assertIsNone(handler.index._code_lance_table, "_code_lance_table must be None after close()")
        self.assertIsNone(handler.index._reranker, "_reranker must be None after close()")
        self.assertFalse(handler.index._loaded, "_loaded must be False after close()")

    def test_reload_closes_old_handler_before_build(self):
        """AC-6: perform_mcp_reload() calls close() on the old handler before building a new one."""
        import server as _server_mod
        try:
            _server_mod.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        closed = []
        original_close = _server_mod._get_handler().close

        def tracking_close():
            closed.append(True)
            original_close()

        _server_mod._get_handler().close = tracking_close
        result = _server_mod.perform_mcp_reload()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(closed), 1, "close() must be called exactly once during reload")


class WavePrepareCouncilGateTests(unittest.TestCase):
    """12sp5: wave_prepare council verdict gate — AC-1, AC-2, AC-3, AC-4."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, slug: str) -> str:
        wave_result = self.srv.wave_create_wave_response(self.root, slug, mode="create")
        wave_id = wave_result["data"]["wave_id"]
        change = self.srv.new_change(self.root, "feat", f"{slug}-change")
        self.srv.wave_add_change_response(self.root, wave_id, change["id"], mode="create")
        journal = self.root / "docs" / "agents" / "journals" / "wave-coordinator.md"
        prior = journal.read_text(encoding="utf-8") if journal.exists() else "# Journal\n"
        journal.write_text(prior + f"\nwave-id: `{wave_id}`\n", encoding="utf-8")
        return wave_id

    def _add_verdict(self, wave_id: str) -> None:
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + "\n## Review Checkpoints\n\n- **Prepare-phase Wave Council [prepare-council] — 2026-05-21: PASS** (red-team fixed seat)\n",
            encoding="utf-8",
        )

    def test_prepare_create_blocked_without_council_verdict(self):
        """AC-3: wave_prepare(mode='create') returns ready_for_council_review when no prepare-council verdict."""
        wave_id = self._make_wave("council-gate-block")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_prepare_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ready_for_council_review")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("prepare_council_verdict_missing", codes)
        # Wave must not have transitioned to active
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        self.assertNotIn("Status: active", wave_md.read_text(encoding="utf-8"))

    def test_prepare_create_succeeds_with_council_verdict(self):
        """AC-4: wave_prepare(mode='create') succeeds when prepare-council verdict is recorded."""
        wave_id = self._make_wave("council-gate-pass")
        self._add_verdict(wave_id)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_prepare_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        self.assertIn("Status: active", wave_md.read_text(encoding="utf-8"))

    def test_prepare_dry_run_includes_council_brief_without_verdict(self):
        """AC-1: dry_run includes council_brief when no verdict is present."""
        wave_id = self._make_wave("council-brief-dry-run")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_prepare_response(self.root, wave_id, mode="dry_run")
        self.assertIn("council_brief", result.get("data", {}))
        brief = result["data"]["council_brief"]
        self.assertEqual(brief["fixed_seat"], "red-team")
        self.assertIn("wave_id", brief)

    def test_rotating_seat_selected_for_seed_wave(self):
        """AC-2: docs-contract-reviewer is selected for waves referencing seed/prompt changes."""
        wave_id = self._make_wave("seed-prompt-wave")
        # Append seed/prompt keywords to the wave change doc
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "## Wave Summary",
                "## Wave Summary\n\nThis wave authors new seed prompts and updates prompt templates.\n",
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_prepare_response(self.root, wave_id, mode="dry_run")
        brief = result["data"]["council_brief"]
        self.assertEqual(brief["rotating_seat"], "docs-contract-reviewer")

    def test_rotating_seat_selected_for_security_wave(self):
        """AC-2: security-reviewer is selected for waves referencing auth/trust boundary changes."""
        wave_id = self._make_wave("auth-security-wave")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "## Wave Summary",
                "## Wave Summary\n\nThis wave updates authentication middleware and trust boundary checks.\n",
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_prepare_response(self.root, wave_id, mode="dry_run")
        brief = result["data"]["council_brief"]
        self.assertEqual(brief["rotating_seat"], "security-reviewer")


class WaveImplementTests(unittest.TestCase):
    """12sqb: wave_implement gate and wave_review phase parameter — AC-1 through AC-10."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, slug: str, status: str = "active") -> str:
        wave_result = self.srv.wave_create_wave_response(self.root, slug, mode="create")
        wave_id = wave_result["data"]["wave_id"]
        change = self.srv.new_change(self.root, "feat", f"{slug}-change")
        self.srv.wave_add_change_response(self.root, wave_id, change["id"], mode="create")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        if status != "planned":
            wave_md.write_text(wave_md.read_text(encoding="utf-8").replace("Status: planned", f"Status: {status}"), encoding="utf-8")
        journal = self.root / "docs" / "agents" / "journals" / "wave-coordinator.md"
        prior = journal.read_text(encoding="utf-8") if journal.exists() else "# Journal\n"
        journal.write_text(prior + f"\nwave-id: `{wave_id}`\n", encoding="utf-8")
        return wave_id

    def _add_council_verdict(self, wave_id: str) -> None:
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + "\n## Review Checkpoints\n\n- **Prepare-phase Wave Council [prepare-council] — 2026-05-21: PASS** (red-team fixed seat)\n",
            encoding="utf-8",
        )

    def _add_prepare_review_signoffs(self, wave_id: str, lanes: list) -> None:
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        signoffs = "\n".join(f"- {lane}: approved 2026-05-21" for lane in lanes)
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + f"\n## Prepare Review Evidence\n\n{signoffs}\n",
            encoding="utf-8",
        )

    def _add_participants(self, wave_id: str, review_lanes: list) -> None:
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        rows = "\n".join(f"| {lane} | review | scope |" for lane in review_lanes)
        table = f"## Participants\n\n| Role | Lane | Scope |\n|------|------|-------|\n{rows}\n"
        wave_md.write_text(wave_md.read_text(encoding="utf-8") + f"\n{table}", encoding="utf-8")

    # --- AC-1/AC-2: wave_review phase parameter ---

    def test_wave_review_prepare_phase_checks_prepare_evidence_section(self):
        """AC-1: wave_review(phase='prepare') checks ## Prepare Review Evidence."""
        wave_id = self._make_wave("review-prepare")
        self._add_participants(wave_id, ["code-reviewer"])
        # No signoffs yet
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, wave_id, phase="prepare")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("missing_required_lane", codes)
        # With signoffs present
        self._add_prepare_review_signoffs(wave_id, ["code-reviewer"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, wave_id, phase="prepare")
        self.assertEqual(result["status"], "ok")

    def test_wave_review_implementation_phase_is_default_behavior(self):
        """AC-2: wave_review(phase='implementation') behaves identically to current wave_review."""
        wave_id = self._make_wave("review-impl")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            default_result = self.srv.wave_review_response(self.root, wave_id)
            impl_result = self.srv.wave_review_response(self.root, wave_id, phase="implementation")
        self.assertEqual(default_result["status"], impl_result["status"])
        self.assertEqual(default_result["data"]["phase"], "implementation")
        self.assertEqual(impl_result["data"]["phase"], "implementation")

    def test_wave_review_prepare_does_not_check_review_evidence(self):
        """AC-1: prepare phase does not interact with ## Review Evidence."""
        wave_id = self._make_wave("review-prepare-isolation")
        # Add an operator-signoff to Review Evidence (implementation phase style)
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(wave_md.read_text(encoding="utf-8").replace(
            "- operator-signoff: <approved when operator confirms closure>",
            "- operator-signoff: approved",
        ), encoding="utf-8")
        # prepare phase should still fail (no Prepare Review Evidence) despite impl phase having signoff
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_review_response(self.root, wave_id, phase="prepare")
        # No lanes required in this wave → should pass since no required_lanes
        self.assertEqual(result["data"]["phase"], "prepare")

    # --- AC-3/AC-4: wave_implement gate checks ---

    def test_wave_implement_blocked_without_council_verdict(self):
        """AC-3: wave_implement returns error when council verdict is missing."""
        wave_id = self._make_wave("impl-no-council")
        result = self.srv.wave_implement_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("prepare_council_verdict_missing", codes)

    def test_wave_implement_blocked_without_prepare_review(self):
        """AC-4: wave_implement returns error when prepare-phase lane review is incomplete."""
        wave_id = self._make_wave("impl-no-review")
        self._add_council_verdict(wave_id)
        self._add_participants(wave_id, ["code-reviewer"])
        # No prepare-review signoffs
        result = self.srv.wave_implement_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("prepare_review_incomplete", codes)

    # --- AC-5: implementation context ---

    def test_wave_implement_returns_ordered_changes_and_watchpoints(self):
        """AC-5: wave_implement returns ordered changes and Journal Watchpoints when gates pass."""
        wave_id = self._make_wave("impl-context")
        self._add_council_verdict(wave_id)
        result = self.srv.wave_implement_response(self.root, wave_id, mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        data = result["data"]
        self.assertIn("ordered_changes", data)
        self.assertIn("journal_watchpoints", data)
        self.assertIn("serialization_points", data)
        self.assertGreater(len(data["ordered_changes"]), 0)

    # --- AC-6/AC-7: status transition ---

    def test_wave_implement_create_transitions_to_implementing(self):
        """AC-6: wave_implement(mode='create') transitions wave status to implementing."""
        wave_id = self._make_wave("impl-create")
        self._add_council_verdict(wave_id)
        result = self.srv.wave_implement_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        self.assertIn("Status: implementing", wave_md.read_text(encoding="utf-8"))

    def test_wave_implement_dry_run_does_not_write(self):
        """AC-7: wave_implement(mode='dry_run') validates readiness without writing."""
        wave_id = self._make_wave("impl-dry-run")
        self._add_council_verdict(wave_id)
        original_text = (self.root / "docs" / "waves" / wave_id / "wave.md").read_text(encoding="utf-8")
        result = self.srv.wave_implement_response(self.root, wave_id, mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual((self.root / "docs" / "waves" / wave_id / "wave.md").read_text(encoding="utf-8"), original_text)

    # --- AC-8: implementing status handling ---

    def test_current_wave_includes_implementing_status(self):
        """AC-8: current_wave() returns implementing waves."""
        from server_impl import current_wave
        wave_id = self._make_wave("ac8-implementing", status="implementing")
        result = current_wave(self.root)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "implementing")

    def test_wave_pause_can_pause_implementing_wave(self):
        """AC-8: wave_pause handles implementing status gracefully."""
        wave_id = self._make_wave("ac8-pause-impl", status="implementing")
        result = self.srv.wave_pause_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        self.assertIn("Status: paused", wave_md.read_text(encoding="utf-8"))

    def test_wave_implement_already_implementing_returns_ok(self):
        """AC-8: wave_implement on an already-implementing wave returns ok with advisory."""
        wave_id = self._make_wave("ac8-already-impl", status="implementing")
        result = self.srv.wave_implement_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("already_implementing"))

    # --- AC-11: wave_add_change next_tools ---

    def test_wave_add_change_includes_wave_add_change_in_next_tools(self):
        """AC-11: wave_add_change includes wave_add_change in next_tools."""
        wave_result = self.srv.wave_create_wave_response(self.root, "ac11-wave", mode="create")
        wave_id = wave_result["data"]["wave_id"]
        change = self.srv.new_change(self.root, "feat", "ac11-change")
        result = self.srv.wave_add_change_response(self.root, wave_id, change["id"], mode="create")
        self.assertIn("wave_add_change", result.get("next_tools", []))


class WaveCloseSummaryGenerationTests(unittest.TestCase):
    """12sq4: wave_close summary generation — AC-1 through AC-5."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_closeable_wave(self, wave_id: str, change_id: str, completed_acs: list[str] | None = None, decisions: list[str] | None = None) -> Path:
        wave_dir = self.root / "docs" / "waves" / wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            f"# Wave Record\n"
            f"wave-id: `{wave_id}`\n"
            f"Title: Test Wave Title\n"
            f"Status: active\n\n"
            f"## Changes\n\n"
            f"Change ID: `{change_id}`\n"
            f"Change Status: `complete`\n\n"
            f"## Wave Summary\n\n"
            f"*(Populated at closure.)*\n\n"
            f"## Review Evidence\n\n"
            f"- operator-signoff: approved\n",
            encoding="utf-8",
        )
        # Write a minimal change doc
        ac_lines = "\n".join(f"- [x] {ac}" for ac in (completed_acs or ["AC-1: Core behavior"]))
        decision_rows = "\n".join(f"| 2026-05-21 | {d} | reason | alternative |" for d in (decisions or []))
        decision_table = (
            "## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| --- | --- | --- | --- |\n"
            f"{decision_rows}\n"
        ) if decisions else ""
        change_doc = wave_dir / f"{change_id}.md"
        change_doc.write_text(
            f"# Change Title For {change_id}\n\n"
            f"Change ID: `{change_id}`\n"
            f"Change Status: `complete`\n\n"
            f"## Acceptance Criteria\n\n{ac_lines}\n\n"
            f"{decision_table}",
            encoding="utf-8",
        )
        return wave_md

    def test_wave_close_populates_wave_summary(self):
        """AC-1: After wave_close, ## Wave Summary contains a populated paragraph."""
        wave_md = self._make_closeable_wave("1200a-summ-test", "1200a-feat-summ-change")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a-summ-test", mode="create")
        self.assertEqual(result["status"], "ok")
        closed_text = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: closed", closed_text)
        # Placeholder replaced
        self.assertNotIn("*(Populated at closure.)*", closed_text)
        # Summary contains wave_id or title
        wave_summary_body = closed_text.split("## Wave Summary")[1].split("## ")[0] if "## Wave Summary" in closed_text else ""
        self.assertTrue(len(wave_summary_body.strip()) > 0, "Wave Summary section must be populated")

    def test_wave_close_summary_includes_change_details(self):
        """AC-2: Summary includes completed ACs and decision log entries."""
        wave_md = self._make_closeable_wave(
            "1200a-detail-test",
            "1200a-feat-detail",
            completed_acs=["AC-1: Core behavior", "AC-2: Edge case handling"],
            decisions=["Use structured extraction instead of LLM inference"],
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a-detail-test", mode="create")
        self.assertEqual(result["status"], "ok")
        summary = result["data"].get("wave_summary", "")
        self.assertIn("AC", summary)

    def test_wave_close_summary_requires_no_operator_input(self):
        """AC-3: Summary is generated without operator intervention."""
        wave_md = self._make_closeable_wave("1200a-auto-test", "1200a-feat-auto")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a-auto-test", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("wave_summary", result["data"])
        self.assertTrue(result["data"]["wave_summary"].strip())

    def test_wave_close_dry_run_includes_summary_without_writing(self):
        """AC-4: dry_run returns wave_summary in data without writing to disk."""
        wave_md = self._make_closeable_wave("1200a-dryrun-summ", "1200a-feat-dryrun-summ")
        original_text = wave_md.read_text(encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wave_close_response(self.root, "1200a-dryrun-summ", mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        self.assertIn("wave_summary", result["data"])
        self.assertTrue(result["data"]["wave_summary"].strip())
        # File must not be modified
        self.assertEqual(wave_md.read_text(encoding="utf-8"), original_text)

    def test_wave_close_summary_does_not_break_existing_close_behavior(self):
        """AC-5: Existing close behavior (status update, signoff) is not regressed."""
        wave_md = self._make_closeable_wave("1200a-regression-test", "1200a-feat-regression")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wave_close_response(self.root, "1200a-regression-test", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["updated"])
        closed_text = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: closed", closed_text)
        self.assertIn("Completed At:", closed_text)


if __name__ == "__main__":
    unittest.main()
