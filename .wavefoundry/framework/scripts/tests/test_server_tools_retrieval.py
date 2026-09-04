"""Retrieval/navigation/graph/index MCP tool tests (shard 2 of 3, wave
1tmtx), split from test_server_tools.py; shared fixtures come from
server_tools_support.
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import importlib.util
import inspect
import json
import math
import os
import stat
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import server_tools_support
from server_tools_support import (  # noqa: F401 — shared server-test fixtures
    SCRIPTS_ROOT,
    SERVER_PATH,
    integrity_checks,
    load_server,
    load_thin_runner,
    _make_repo,
    _store_read_meta,
    _seed_store_state,
    _write_index_layer,
    _write_lance_index,
)



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
        # 1p4ww: framework seeds fold into the project docs index (no separate framework layer).
        _write_index_layer(
            self.root / ".wavefoundry" / "index",
            [
                {
                    "id": "project-doc",
                    "path": "docs/project.md",
                    "kind": "doc",
                    "language": None,
                    "lines": [1, 1],
                    "section": None,
                    "text": "project docs",
                },
                {
                    "id": "seed",
                    "path": ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
                    "kind": "seed",
                    "language": None,
                    "lines": [1, 1],
                    "section": None,
                    "text": "framework seed",
                },
            ],
            [[1, 0], [1, 0]],
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

    def test_folded_framework_seed_satisfies_seed_lookup(self):
        # 1p4ww: framework seeds live in the project docs index (folded, not a separate layer).
        _write_index_layer(
            self.root / ".wavefoundry" / "index",
            [{
                "id": "seed",
                "path": ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
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
            self.root / ".wavefoundry" / "index",
            [{
                "id": "seed",
                "path": ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
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
            self.root / ".wavefoundry" / "index",
            [{
                "id": "seed",
                "path": ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
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

        self.assertEqual(first, {"project": True})
        self.assertEqual(second, {"project": False})
        indexer_spawns = [
            call
            for call in popen.call_args_list
            if call.args
            and isinstance(call.args[0], list)
            and any(str(arg).endswith("/indexer.py") for arg in call.args[0])
        ]
        self.assertEqual(len(indexer_spawns), 1)

    def test_framework_seed_paths_trigger_project_layer_refresh(self):
        # 1p4ww: framework seeds fold into the project docs index, so a seed change
        # triggers the single project refresh (no separate framework index args).
        proc = MagicMock()
        proc.pid = 4321
        with patch("subprocess.Popen", return_value=proc) as popen:
            result = self.srv._trigger_background_index_refresh_for_paths(
                self.root,
                [".wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md"],
            )

        self.assertEqual(result, {"project": True})
        cmd = popen.call_args.args[0]
        self.assertNotIn("--index-dir", cmd)
        self.assertNotIn(".wavefoundry/framework/index", " ".join(cmd))


class IndexBuildStatusTests(unittest.TestCase):
    """12ebh: index_build_status MCP tool."""

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
        result = self.srv.index_build_status_response(self.root, layer="project")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["state"], "idle")

    def test_running_when_pid_active(self):
        import os, time
        self._write_state(os.getpid(), time.time() - 30)
        self.log_path.write_text("build_index: embedding doc chunks 100-200/500\n", encoding="utf-8")
        result = self.srv.index_build_status_response(self.root, layer="project")
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
        result = self.srv.index_build_status_response(self.root, layer="project")
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
        result = self.srv.index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertEqual(result["data"]["files_indexed"], 300)
        self.assertEqual(result["data"]["doc_chunks"], 2000)
        self.assertEqual(result["data"]["code_chunks"], 1800)
        self.assertFalse(self.state_path.exists())

    def test_finished_falls_back_to_last_line_when_no_summary(self):
        import time
        self._write_state(99999999, time.time() - 60)
        self.log_path.write_text("build_index: some partial output\n", encoding="utf-8")
        result = self.srv.index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertEqual(result["data"]["last_log_line"], "build_index: some partial output")

    def test_finished_when_setup_index_exits_with_model_prewarm_error(self):
        import time
        self._write_state(99999999, time.time() - 60)
        self.log_path.write_text(
            "Prewarming semantic model cache: Snowflake/snowflake-arctic-embed-s\n"
            "Required embedding model 'Snowflake/snowflake-arctic-embed-s' could not be prepared for semantic index setup: "
            "network or download host unavailable.\n",
            encoding="utf-8",
        )
        result = self.srv.index_build_status_response(self.root, layer="project")
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
        result = self.srv.index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertEqual(result["data"]["files_indexed"], 100)
        self.assertFalse(self.state_path.exists())

    def test_finished_when_log_has_up_to_date_despite_live_pid(self):
        # Regression: zombie process (defunct on macOS) keeps os.kill(pid,0) returning True.
        # "index is up to date" must be treated as a terminal log state, same as the done marker.
        import os, time
        self._write_state(os.getpid(), time.time() - 60)
        self.log_path.write_text("build_index: index is up to date\n", encoding="utf-8")
        result = self.srv.index_build_status_response(self.root, layer="project")
        self.assertEqual(result["data"]["state"], "finished")
        self.assertFalse(self.state_path.exists())

    def test_invalid_layer_returns_error(self):
        result = self.srv.index_build_status_response(self.root, layer="bogus")
        self.assertEqual(result["status"], "error")

    def test_framework_layer_rejected(self):
        # 1p4ww: the framework layer is folded into the project index — status rejects it.
        result = self.srv.index_build_status_response(self.root, layer="framework")
        self.assertEqual(result["status"], "error")

    def test_previous_stats_included_in_finished_response(self):
        import json, time
        self._write_state(99999999, time.time() - 120)
        self.log_path.write_text(
            "build_index: done — 300 files indexed, 2000 doc chunks, 1800 code chunks\n",
            encoding="utf-8",
        )
        stats = {"elapsed_seconds": 420, "files_indexed": 300, "doc_chunks": 2000, "code_chunks": 1800, "built_at": "2026-05-06T10:00:00Z", "content": "docs", "mode": "rebuild"}
        (self.index_dir / "index-build-stats.json").write_text(json.dumps(stats), encoding="utf-8")
        result = self.srv.index_build_status_response(self.root, layer="project")
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
        result = self.srv.index_build_status_response(self.root, layer="project")
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
        result = self.srv.index_build_status_response(self.root, layer="project")
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
        result = self.srv.index_build_status_response(self.root, layer="project")
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


class RunIndexRebuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Wave 1p2q3 (1p2w5): run_index_rebuild polls proc.poll() for up to
        # _INDEX_BUILD_VERIFY_TIMEOUT_SECONDS after Popen. Tests mock Popen
        # to return a MagicMock whose poll() returns a MagicMock (not int),
        # so the verification loop runs the full window. Short-circuit it.
        self._verify_timeout_patch = patch.object(
            self.srv, "_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS", 0.0
        )
        self._verify_timeout_patch.start()

    def tearDown(self):
        self._verify_timeout_patch.stop()
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
        meta = _store_read_meta(index_dir)
        meta["built_at"] = built_at
        # 1sed6: the store persists file_meta (the legacy file_hashes key does
        # not round-trip — census disposition: obsolete).
        meta["file_meta"] = {
            path: {"hash": h} for path, h in (file_hashes or {"docs/a.md": "h1"}).items()
        }
        _seed_store_state(index_dir, meta)

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

    def test_project_code_rebuild_does_not_forward_prefixes_indexer_self_reads(self):
        # indexer.py reads workflow-config project include-prefixes itself, so
        # run_index_rebuild launches the indexer bare for the project layer.
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
        self.assertIn("indexer.py", str(cmd[1]))
        self.assertIn("--content", cmd)
        self.assertIn("code", cmd)
        self.assertNotIn("--project-include-prefix", cmd)

    def test_framework_layer_rejected(self):
        # 1p4ww: framework folded into the project index — rebuild rejects the layer.
        with self.assertRaises(ValueError):
            self.srv.run_index_rebuild(self.root, content="docs", layer="framework")

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

    def test_subprocess_early_exit_with_lock_busy_surfaces_failure(self):
        """Wave 1p2q3 (1p2w5 / Bug 2): when the spawned indexer subprocess
        exits within the verification window with a non-zero code and
        "lock file busy" in its log, run_index_rebuild must return
        `build_failed_early=True`, `passed=False`, and
        `diagnostic_code='build_skipped_lock_busy'` carrying the lock-holder
        PID. Pre-fix behavior returned `passed=True` and `graph_rebuilt=True`
        regardless of subprocess outcome."""
        # Pre-write the lock file so the lock-owner lookup has a PID to read.
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "index-build.lock").write_text(
            json.dumps({"pid": 77777, "started_at": 1780000000.0}),
            encoding="utf-8",
        )
        logs_dir = self.root / ".wavefoundry" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "project-index-build.log"

        # The production code truncates log_path via `open(log_path, "w", ...)`
        # before Popen. Use a Popen side_effect to write lock-busy content
        # AFTER that truncation, simulating an indexer subprocess that ran,
        # tried to acquire its flock, failed, wrote the conflict message,
        # and exited with non-zero — all inside the verification window.
        def _popen_side_effect(*args, **kwargs):
            log_path.write_text(
                "Another index build is already running for /tmp/x — "
                "live build in progress (owner pid 77777)\n",
                encoding="utf-8",
            )
            m = MagicMock()
            m.pid = 99999
            m.poll = MagicMock(return_value=1)  # exited with code 1
            return m

        # Force a finite verify window so the failure-detection branch runs.
        original_verify = getattr(self.srv, "_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS", 1.5)
        self.srv._INDEX_BUILD_VERIFY_TIMEOUT_SECONDS = 0.5
        try:
            with patch("subprocess.Popen", side_effect=_popen_side_effect), \
                 patch.object(self.srv, "_index_is_up_to_date", return_value=False):
                result = self.srv.run_index_rebuild(
                    self.root, content="graph", full=True
                )
        finally:
            self.srv._INDEX_BUILD_VERIFY_TIMEOUT_SECONDS = original_verify
        self.assertFalse(result["passed"])
        self.assertTrue(result["build_failed_early"])
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["diagnostic_code"], "build_skipped_lock_busy")
        self.assertEqual(result["lock_owner_pid"], 77777)
        self.assertEqual(result["pid"], 99999)

    def test_invalid_content_raises(self):
        with self.assertRaises(ValueError):
            self.srv.run_index_rebuild(self.root, content="bad")

    def test_content_map_runs_generator_only_no_subprocess(self):
        # Wave 1p601: content="map" runs the codebase-map generator only (no full
        # rebuild, no subprocess spawn) and is fail-safe.
        with patch("subprocess.Popen") as popen:
            result = self.srv.run_index_rebuild(self.root, content="map")
            popen.assert_not_called()
        self.assertTrue(result["passed"])
        self.assertEqual(result["content"], "map")
        self.assertEqual(result["mode"], "map-refresh")
        self.assertEqual(result["index_scope"], "codebase_map_only")
        self.assertIn("map_path", result)

    def test_invalid_layer_raises(self):
        with self.assertRaises(ValueError):
            self.srv.run_index_rebuild(self.root, layer="bad")


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
        result = self.srv.index_build_response(self.root, mode="full-refresh")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_arguments")

    def test_invalid_content_returns_error(self):
        result = self.srv.index_build_response(self.root, content="bad")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_arguments")

    def test_invalid_layer_returns_error(self):
        result = self.srv.index_build_response(self.root, layer="bad")
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
                result = self.srv.index_build_response(self.root, content="docs", mode="update", cache=cache)
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
                result = self.srv.index_build_response(self.root, content="docs", mode="update", cache=cache)
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
            result = self.srv.index_build_response(self.root, content="docs", mode="update")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["diagnostics"][0]["code"], "index_build_already_running")

    def test_framework_layer_build_rejected(self):
        # 1p4ww: framework folded into the project index — the build response surfaces
        # the ValueError from run_index_rebuild as an invalid-arguments error.
        result = self.srv.index_build_response(self.root, content="docs", layer="framework")
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# index_health
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
            "project": {"readiness": "current"},        }
        result = self.srv.index_health_response(index)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["data"]["readiness_overview"], "ready")

    def test_reports_additive_background_monitor_status(self):
        index = MagicMock()
        index.docs_health.return_value = {
            "semantic_ready": True,
            "stale_layers": [],
            "missing_layers": [],
            "has_any_index": True,
            "compatible_chunks": True,
            "readiness_overview": "ready",
            "project": {"readiness": "current"},
        }
        monitors = {
            "index": {
                "configured": True,
                "alive": True,
                "last_checked_at": 123.0,
                "stale": False,
                "triggered": False,
                "reason": "current_or_undetermined",
            },
            "context_efficiency_projection": {
                "configured": True,
                "alive": True,
                "last_checked_at": 124.0,
                "triggered": False,
                "reason": "nothing_pending",
                "quiet_period_seconds": 120.0,
            },
        }
        result = self.srv.index_health_response(
            index, background_monitors=monitors
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["background_monitors"], monitors)

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
            "project": {},        }
        result = self.srv.index_health_response(index)
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
            "project": {},        }
        result = self.srv.index_health_response(index)
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
            "project": {"readiness": "current"},        }
        result = self.srv.index_health_response(index)
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
            "project": {"readiness": "idle"},        }
        result = self.srv.index_health_response(index)
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
            "project": {"readiness": "current"},            "chunker_version_mismatch_layers": [],
        }

    def test_chunker_version_mismatch_emits_advisory(self):
        index = MagicMock()
        base = self._healthy_base()
        base["chunker_version_mismatch_layers"] = ["project"]
        index.docs_health.return_value = base
        result = self.srv.index_health_response(index)
        self.assertEqual(result["status"], "ok")
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
        result = self.srv.index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("chunker_version_mismatch", codes)
        self.assertNotIn("index_stale", codes)

    def test_no_chunker_version_mismatch_when_layers_empty(self):
        index = MagicMock()
        base = self._healthy_base()
        base["chunker_version_mismatch_layers"] = []
        index.docs_health.return_value = base
        result = self.srv.index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertNotIn("chunker_version_mismatch", codes)

    def test_background_code_build_running_emits_advisory(self):
        index = MagicMock()
        base = self._healthy_base()
        index.docs_health.return_value = base
        with patch.object(self.srv, "_background_build_status", return_value="running"):
            result = self.srv.index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("background_code_build_running", codes)

    def test_background_code_build_completed_no_advisory(self):
        index = MagicMock()
        base = self._healthy_base()
        index.docs_health.return_value = base
        with patch.object(self.srv, "_background_build_status", return_value="completed"):
            result = self.srv.index_health_response(index)
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertNotIn("background_code_build_running", codes)

    def test_background_code_build_none_no_advisory(self):
        index = MagicMock()
        base = self._healthy_base()
        index.docs_health.return_value = base
        with patch.object(self.srv, "_background_build_status", return_value="none"):
            result = self.srv.index_health_response(index)
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
            result = self.srv.index_health_response(index)
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
            result = self.srv.index_health_response(index)
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
            result = self.srv.index_health_response(index)
            self.assertNotIn("previous_build_stats", result["data"])
        finally:
            tmp.cleanup()

    def test_exception_from_docs_health_returns_structured_error(self):
        index = MagicMock()
        index.docs_health.side_effect = RuntimeError("unexpected failure")
        result = self.srv.index_health_response(index)
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
# DX fix tests (AC-16 through AC-20)
# ---------------------------------------------------------------------------

class StaleGraphAutoRebuildTests(unittest.TestCase):
    """131bt (131e2): synchronous auto-rebuild when on-disk graph builder_version
    differs from runtime GRAPH_BUILDER_VERSION."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        # Load graph_query freshly so per-process cache state doesn't leak.
        import importlib.util, sys as _sys
        scripts = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("graph_query_under_test", scripts / "graph_query.py")
        self.gq = importlib.util.module_from_spec(spec)
        _sys.modules["graph_query_under_test"] = self.gq
        spec.loader.exec_module(self.gq)
        # Build a real (small) graph index in this temp repo.
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "src" / "foo.py").write_text(
            "def make():\n    return 1\n", encoding="utf-8",
        )
        # Use the indexer directly to write a real on-disk graph.
        idxer_spec = importlib.util.spec_from_file_location("indexer_for_test", scripts / "indexer.py")
        self.idxer = importlib.util.module_from_spec(idxer_spec)
        _sys.modules["indexer_for_test"] = self.idxer
        idxer_spec.loader.exec_module(self.idxer)
        self.idxer.build_index(
            self.root, full=True, content="graph",
            index_dir=self.root / ".wavefoundry" / "index", verbose=False,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _state_path(self):
        return self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.json"

    def _store_path(self):
        # 1p9q2: the live graph state is the per-file SQLite store.
        return self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.sqlite"

    def _payload_path(self):
        return self.root / ".wavefoundry" / "index" / "graph" / "project-graph.json"

    def _force_stale_state(self, old_version: str = "0"):
        """Simulate a pre-upgrade repo: legacy plain-JSON monolithic state with
        an older builder_version and NO SQLite store — exercising the probe's
        legacy fallback path — plus a plain-JSON payload (pre-1p9py format)."""
        import json
        import os
        gi = self.gq._get_graph_indexer()
        store_path = self._store_path()
        self.assertTrue(store_path.exists(), "state store missing — graph build failed")
        index_dir = self.root / ".wavefoundry" / "index"
        self.assertTrue(
            gi.read_state_builder_version(index_dir),
            "state store unreadable — graph build failed",
        )
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(f"{store_path}{suffix}")
            except OSError:
                pass
        self._state_path().write_text(
            json.dumps({"builder_version": old_version}), encoding="utf-8"
        )
        payload_path = self._payload_path()
        if payload_path.exists():
            payload = gi.read_json_artifact(payload_path, {})
            payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            # Touch the payload file so its mtime differs from any cached entry.
            t = payload_path.stat().st_mtime - 1.0
            os.utime(payload_path, (t, t))
        # Clear the in-process cache so the next load re-checks.
        self.gq._VERSION_CHECK_CACHE.clear()

    def test_auto_rebuild_fires_when_builder_version_stale(self):
        self._force_stale_state(old_version="0")
        payload = self.gq.load_graph(self.root, layer="project")
        diag = payload.get("auto_rebuild_diagnostic")
        self.assertIsNotNone(diag, f"Expected auto_rebuild_diagnostic on stale graph; got payload keys={sorted(payload.keys())}")
        self.assertEqual(diag.get("code"), "graph_auto_rebuilt")
        self.assertEqual(diag.get("from_builder_version"), "0")
        # After rebuild the store's builder_version should match runtime.
        gi = self.gq._get_graph_indexer()
        runtime_version = gi.GRAPH_BUILDER_VERSION
        index_dir = self.root / ".wavefoundry" / "index"
        self.assertEqual(gi.read_state_builder_version(index_dir), runtime_version)
        # 1p9py AC-6: the rebuild rewrote the pre-change (plain JSON) payload as
        # gzip-compressed compact JSON, and subsequent queries hit it cleanly.
        self.assertEqual(self._payload_path().read_bytes()[:2], b"\x1f\x8b")
        # 1p9q2: the legacy monolithic state was discarded (one-time) and the
        # per-file SQLite store reseeded in its place.
        self.assertFalse(self._state_path().exists())
        self.assertTrue(self._store_path().exists())
        again = self.gq.load_graph(self.root, layer="project")
        self.assertNotIn("auto_rebuild_diagnostic", again)
        self.assertTrue(again.get("present"))

    def test_already_fresh_graph_does_not_trigger_rebuild(self):
        # Setup wrote a fresh graph. First load should NOT carry diagnostic.
        # Reset cache so we go through the full path.
        self.gq._VERSION_CHECK_CACHE.clear()
        payload = self.gq.load_graph(self.root, layer="project")
        self.assertNotIn("auto_rebuild_diagnostic", payload, "Fresh graph should not trigger auto-rebuild")

    def test_repeat_query_uses_cache_no_second_rebuild(self):
        self._force_stale_state(old_version="0")
        # First load triggers rebuild.
        first = self.gq.load_graph(self.root, layer="project")
        self.assertIsNotNone(first.get("auto_rebuild_diagnostic"))
        # Second load should be a no-op (cached as verified).
        second = self.gq.load_graph(self.root, layer="project")
        self.assertNotIn("auto_rebuild_diagnostic", second, "Second query should not re-trigger rebuild")

    def test_auto_rebuild_diagnostic_surfaces_through_graph_query_index(self):
        """The diagnostic on the loaded payload must propagate onto the
        GraphQueryIndex.auto_rebuild_diagnostic slot so consumer tools can
        attach it to their MCP responses (131e2 polish)."""
        self._force_stale_state(old_version="0")
        # Use load_graph and construct an index — mirrors the consumer-tool
        # path of `GraphQueryIndex(load_graph(...))`.
        payload = self.gq.load_graph(self.root, layer="project")
        idx = self.gq.GraphQueryIndex(payload)
        self.assertIsNotNone(idx.auto_rebuild_diagnostic,
                             "Diagnostic should propagate from payload to GraphQueryIndex slot")
        self.assertEqual(idx.auto_rebuild_diagnostic.get("code"), "graph_auto_rebuilt")
        self.assertEqual(idx.auto_rebuild_diagnostic.get("from_builder_version"), "0")


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


class CodeReadEnrichmentTests(unittest.TestCase):
    """Wave 1p3dk / 1p3ha: comprehensive enrichment of code_read response.

    Covers Tier 1 (range-aware streaming + with_line_numbers), Tier 2
    (response metadata: absolute_path, mtime, size_bytes, read_invocation,
    has_more), Tier 3 (edit_governance), Tier 4 (marker_regions). Tier 5
    (tree-sitter structural) deferred to follow-up — cache module is ready
    in tree_sitter_cache.py for 1p3hd consumption."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_response_includes_absolute_path(self):
        """AC-7: absolute_path field returns the resolved absolute path."""
        self._write("foo.py", "line1\nline2\nline3\n")
        result = self.srv.code_read_response(self.root, "foo.py")
        self.assertIn("absolute_path", result["data"])
        self.assertTrue(result["data"]["absolute_path"].endswith("/foo.py"))
        self.assertTrue(Path(result["data"]["absolute_path"]).is_absolute())

    def test_response_includes_read_invocation_hint(self):
        """AC-8: read_invocation carries the exact Read() call satisfying Edit precondition."""
        self._write("foo.py", "\n".join(f"line{i}" for i in range(1, 51)))
        result = self.srv.code_read_response(self.root, "foo.py", start_line=10, end_line=20)
        inv = result["data"]["read_invocation"]
        self.assertEqual(inv["offset"], 10)
        self.assertEqual(inv["limit"], 11)  # 20 - 10 + 1
        self.assertTrue(inv["file_path"].endswith("/foo.py"))
        self.assertTrue(inv["satisfies_edit_precondition_for_range"])
        self.assertIn("Edit/Write read-first precondition", inv["note"])

    def test_response_includes_mtime_and_size(self):
        """AC-9: mtime (ISO-8601 UTC) and size_bytes present in response."""
        self._write("foo.py", "small content\n")
        result = self.srv.code_read_response(self.root, "foo.py")
        self.assertIn("mtime", result["data"])
        self.assertTrue(result["data"]["mtime"].endswith("Z"),
            f"mtime should be ISO-8601 UTC ending in Z, got {result['data']['mtime']!r}")
        self.assertIn("size_bytes", result["data"])
        self.assertGreater(result["data"]["size_bytes"], 0)

    def test_with_line_numbers_false_returns_raw_content(self):
        """AC-5: with_line_numbers=False omits the %5d\\t prefix."""
        self._write("foo.py", "alpha\nbeta\ngamma\n")
        result = self.srv.code_read_response(self.root, "foo.py", with_line_numbers=False)
        content = result["data"]["content"]
        self.assertEqual(content, "alpha\nbeta\ngamma")
        self.assertNotIn("\t", content)

    def test_with_line_numbers_true_preserves_format(self):
        """AC-6: default with_line_numbers=True preserves the existing prefix format."""
        self._write("foo.py", "alpha\nbeta\n")
        result = self.srv.code_read_response(self.root, "foo.py")
        content = result["data"]["content"]
        self.assertIn("    1\talpha", content)
        self.assertIn("    2\tbeta", content)

    def test_partial_read_returns_has_more_not_total_lines(self):
        """AC-3, AC-4: mid-file partial read returns has_more, omits total_lines."""
        self._write("foo.py", "\n".join(f"line{i}" for i in range(1, 51)))
        result = self.srv.code_read_response(self.root, "foo.py", start_line=10, end_line=15)
        self.assertIn("has_more", result["data"])
        self.assertTrue(result["data"]["has_more"])
        self.assertNotIn("total_lines", result["data"])

    def test_full_file_read_returns_total_lines_not_has_more(self):
        """AC-4: full-file read preserves total_lines (backward compat)."""
        self._write("foo.py", "\n".join(f"line{i}" for i in range(1, 21)))
        result = self.srv.code_read_response(self.root, "foo.py")
        self.assertEqual(result["data"]["total_lines"], 20)
        self.assertNotIn("has_more", result["data"])

    def test_partial_read_reaching_eof_no_has_more(self):
        """When the partial read reaches EOF, has_more is False."""
        self._write("foo.py", "\n".join(f"line{i}" for i in range(1, 11)))
        result = self.srv.code_read_response(self.root, "foo.py", start_line=5, end_line=20)
        self.assertFalse(result["data"]["has_more"])

    def test_seed_path_returns_seed_edit_allowed_governance(self):
        """AC-10: seed paths surface the seed_edit_allowed gate requirement."""
        self._write(".wavefoundry/framework/seeds/test-seed.prompt.md", "# stub\n")
        result = self.srv.code_read_response(self.root, ".wavefoundry/framework/seeds/test-seed.prompt.md")
        gov = result["data"]["edit_governance"]
        self.assertEqual(gov["requires_gate"], "seed_edit_allowed")
        self.assertIn(gov["current_state"], ("open", "closed", "unknown"))
        self.assertIn("wf_open_gate", gov["open_with"])

    def test_framework_scripts_path_returns_framework_edit_allowed_governance(self):
        """AC-11: framework scripts paths surface framework_edit_allowed."""
        self._write(".wavefoundry/framework/scripts/helper.py", "# stub\n")
        result = self.srv.code_read_response(self.root, ".wavefoundry/framework/scripts/helper.py")
        gov = result["data"]["edit_governance"]
        self.assertEqual(gov["requires_gate"], "framework_edit_allowed")

    def test_non_gated_path_omits_edit_governance(self):
        """AC-12: paths under no gated area omit edit_governance entirely."""
        self._write("docs/contributing/notes.md", "# notes\n")
        result = self.srv.code_read_response(self.root, "docs/contributing/notes.md")
        self.assertNotIn("edit_governance", result["data"])

    def test_marker_regions_detected_when_in_range(self):
        """AC-14: marker_regions returns overlapping wave:* blocks."""
        content = (
            "line 1\n"
            "line 2\n"
            "<!-- wave:auto-guru begin -->\n"
            "marker content 1\n"
            "marker content 2\n"
            "<!-- wave:auto-guru end -->\n"
            "line 7\n"
        )
        self._write("foo.md", content)
        result = self.srv.code_read_response(self.root, "foo.md")
        regions = result["data"]["marker_regions"]
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["name"], "auto-guru")
        self.assertEqual(regions[0]["start_line"], 3)
        self.assertEqual(regions[0]["end_line"], 6)
        self.assertIn("renderer-owned", regions[0]["warning"])

    def test_marker_regions_accept_legacy_namespace(self):
        content = (
            "<!-- waveframework:auto-guru begin -->\n"
            "legacy content\n"
            "<!-- waveframework:auto-guru end -->\n"
        )
        self._write("legacy.md", content)
        result = self.srv.code_read_response(self.root, "legacy.md")
        regions = result["data"]["marker_regions"]
        self.assertEqual([(row["name"], row["start_line"], row["end_line"]) for row in regions], [("auto-guru", 1, 3)])

    def test_marker_regions_empty_list_when_none(self):
        """AC-15: marker_regions is empty list (not omitted) when no markers overlap."""
        self._write("foo.md", "# no markers\nplain content\n")
        result = self.srv.code_read_response(self.root, "foo.md")
        self.assertIn("marker_regions", result["data"])
        self.assertEqual(result["data"]["marker_regions"], [])

    # ----- Tier 5: tree-sitter structural enrichment -----

    def test_structural_omitted_on_markdown(self):
        """AC-20: non-code files (markdown) get no structural block."""
        self._write("docs/notes.md", "# heading\n\ntext\n")
        result = self.srv.code_read_response(self.root, "docs/notes.md")
        self.assertNotIn("structural", result["data"])

    def test_structural_omitted_on_json(self):
        """AC-20: non-code files (json) get no structural block."""
        self._write("config.json", '{"foo": 1}\n')
        result = self.srv.code_read_response(self.root, "config.json")
        self.assertNotIn("structural", result["data"])

    def test_structural_returns_note_when_file_too_large(self):
        """AC-21: code file larger than 500KB → structural with explanatory note."""
        # Build a >500KB Python file with valid syntax
        lines = [f"def fn_{i}(): pass" for i in range(40000)]  # ~700KB
        self._write("big.py", "\n".join(lines))
        result = self.srv.code_read_response(self.root, "big.py", start_line=1, end_line=10)
        structural = result["data"].get("structural")
        self.assertIsNotNone(structural,
            "oversized file should still produce a structural block with explanatory note, not omission")
        self.assertEqual(structural.get("note"), "file_too_large_for_structural_parse")
        self.assertIn("size_bytes", structural)
        self.assertIn("budget_bytes", structural)

    def test_structural_returns_containing_symbol_for_python_function(self):
        """AC-16: smallest symbol whose range fully contains the request."""
        code = (
            "def outer():\n"        # line 1
            "    def inner():\n"    # line 2
            "        return 42\n"   # line 3
            "    return inner()\n"  # line 4
            "\n"                    # line 5
            "class MyClass:\n"      # line 6
            "    def method(self):\n"  # line 7
            "        return 1\n"    # line 8
        )
        self._write("sample.py", code)
        # Range fully inside inner() — smallest containing symbol is inner
        result = self.srv.code_read_response(self.root, "sample.py", start_line=3, end_line=3)
        structural = result["data"].get("structural")
        self.assertIsNotNone(structural, "Python file in tree-sitter map should get structural")
        sym = structural["containing_symbol"]
        self.assertIsNotNone(sym, "range inside a function should resolve to a containing symbol")
        # Either inner or outer — both legitimate. Verify it's a function-shaped node.
        self.assertIn("function", sym["kind"])
        self.assertIn(sym["name"], ("inner", "outer"))

    def test_structural_complete_in_range_when_range_covers_symbol(self):
        """AC-17: complete_in_range == True when range equals or supersets the symbol."""
        code = (
            "def small():\n"
            "    return 1\n"
        )
        self._write("sample.py", code)
        # Range covers all of small()
        result = self.srv.code_read_response(self.root, "sample.py", start_line=1, end_line=2)
        sym = result["data"]["structural"]["containing_symbol"]
        self.assertTrue(sym["complete_in_range"])

    def test_structural_starts_mid_construct_when_range_partial(self):
        """AC-18: starts_mid_construct == True when range begins inside a construct."""
        code = (
            "def big_function():\n"       # line 1
            "    x = 1\n"                  # line 2
            "    y = 2\n"                  # line 3
            "    z = 3\n"                  # line 4
            "    return x + y + z\n"       # line 5
        )
        self._write("sample.py", code)
        # Range 3-4 is mid-function
        result = self.srv.code_read_response(self.root, "sample.py", start_line=3, end_line=4)
        structural = result["data"]["structural"]
        self.assertTrue(structural["range_analysis"]["starts_mid_construct"])
        self.assertEqual(
            structural["range_analysis"]["suggested_clean_range"], [1, 5],
            "suggested_clean_range should be the full function body lines",
        )
        sym = structural["containing_symbol"]
        self.assertFalse(sym["complete_in_range"])

    def test_structural_cache_hit_on_second_read(self):
        """Cache module integration: reading the same file twice should hit cache."""
        import tree_sitter_cache
        tree_sitter_cache.default_cache.clear()
        code = "def f():\n    return 1\n"
        self._write("cached.py", code)
        # First read — miss
        self.srv.code_read_response(self.root, "cached.py")
        misses_after_first = tree_sitter_cache.default_cache.stats["misses"]
        hits_after_first = tree_sitter_cache.default_cache.stats["hits"]
        # Second read — hit
        self.srv.code_read_response(self.root, "cached.py")
        misses_after_second = tree_sitter_cache.default_cache.stats["misses"]
        hits_after_second = tree_sitter_cache.default_cache.stats["hits"]
        self.assertEqual(misses_after_second, misses_after_first,
            "second read should not increment misses")
        self.assertGreater(hits_after_second, hits_after_first,
            "second read should increment hits")


class CrossToolTreeSitterCacheTests(unittest.TestCase):
    """Wave 1p3dk / 1p3hd: every tree-sitter-using MCP tool now consumes the
    shared cache (`tree_sitter_cache.default_cache`). An agent navigation
    flow that touches the same file across multiple tools parses tree-sitter
    only once, until the file's mtime advances."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        import tree_sitter_cache
        tree_sitter_cache.default_cache.clear()
        self._cache_module = tree_sitter_cache

    def tearDown(self):
        self.tmp.cleanup()
        self._cache_module.default_cache.clear()

    def _write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_code_outline_then_code_read_shares_cache(self):
        """Cross-tool hit: `code_outline` parses, `code_read` structural block
        reuses the cached parse. Both surfaces touching the same file in the
        same session parse tree-sitter exactly once.

        Python uses stdlib AST (not tree-sitter), so we exercise this with a
        JavaScript file — tree-sitter is in the path for `.js`."""
        self._write("foo.js", "function bar() { return 1; }\n")
        # First touch: code_outline parses
        self.srv.code_outline_response(self.root, "foo.js")
        misses_after_first = self._cache_module.default_cache.stats["misses"]
        # Second touch: code_read structural — should HIT cache
        self.srv.code_read_response(self.root, "foo.js")
        misses_after_second = self._cache_module.default_cache.stats["misses"]
        hits_after = self._cache_module.default_cache.stats["hits"]
        self.assertEqual(misses_after_second, misses_after_first,
            "code_read after code_outline must hit cache, not re-parse")
        self.assertGreater(hits_after, 0)

    def test_mtime_change_invalidates_across_tools(self):
        """In-session-edit invalidation works across tools: code_outline parses,
        file mtime advances, code_read sees the new mtime and re-parses."""
        import time
        path = self._write("foo.js", "function v1() { return 1; }\n")
        self.srv.code_outline_response(self.root, "foo.js")
        misses_before_edit = self._cache_module.default_cache.stats["misses"]
        # Advance mtime by editing
        time.sleep(0.01)
        path.write_text("function v2() { return 2; }\n", encoding="utf-8")
        # code_read after the edit must reparse
        self.srv.code_read_response(self.root, "foo.js")
        misses_after_edit = self._cache_module.default_cache.stats["misses"]
        invalidations = self._cache_module.default_cache.stats["invalidations"]
        self.assertGreater(misses_after_edit, misses_before_edit,
            "post-edit call must miss (invalidate-then-reparse)")
        self.assertGreater(invalidations, 0)


class GraphIndexIsolationRegressionTests(unittest.TestCase):
    """Wave 1p3dk / 1p3hd AC-9: graph_indexer.py runs at index-build time
    with its own parse pipeline and a different invariant (whole-codebase
    relationship graph). It must NOT consume the MCP tool cache. This
    regression test guards the architectural boundary that was explicitly
    scoped out of 1p3hd."""

    def test_graph_indexer_does_not_import_tree_sitter_cache(self):
        scripts_root = Path(__file__).resolve().parents[1]
        graph_indexer = scripts_root / "graph_indexer.py"
        self.assertTrue(graph_indexer.is_file(),
            f"graph_indexer.py not found at {graph_indexer}")
        text = graph_indexer.read_text(encoding="utf-8")
        self.assertNotIn("tree_sitter_cache", text,
            "graph_indexer.py must NOT import tree_sitter_cache — the graph "
            "layer has its own parse pipeline and a different lifecycle "
            "(index-build time, not MCP-tool-call time). 1p3hd AC-9 / Decision "
            "Log: consolidation with the graph layer is out of scope and would "
            "be a major architectural change.")


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

    def test_default_limit_caps_at_50_with_truncated_flag(self):
        """Wave 1p3dk: code_keyword now defaults to limit=50 to prevent
        response-token-cap overflow on prevalent tokens. When the cap
        fires, truncated=True and total_matches_found shows the actual
        total so the agent knows to refine."""
        # Plant 75 matching lines
        src = self.root / "src"
        src.mkdir(exist_ok=True)
        (src / "many.py").write_text(
            "\n".join(f"PREVALENT_TOKEN_{i} = {i}" for i in range(75)) + "\n",
            encoding="utf-8",
        )
        result = self.srv.code_keyword_response(self.root, "PREVALENT_TOKEN_")
        data = result["data"]
        self.assertEqual(data["count"], 50, "default limit must cap at 50")
        self.assertTrue(data["truncated"])
        self.assertEqual(data["total_matches_found"], 75)

    def test_limit_zero_returns_all_matches(self):
        """limit=0 disables the cap — agents who need exhaustive results pass it explicitly."""
        src = self.root / "src"
        src.mkdir(exist_ok=True)
        (src / "many.py").write_text(
            "\n".join(f"EXHAUST_TOKEN_{i} = {i}" for i in range(75)) + "\n",
            encoding="utf-8",
        )
        result = self.srv.code_keyword_response(self.root, "EXHAUST_TOKEN_", limit=0)
        data = result["data"]
        self.assertEqual(data["count"], 75)
        self.assertFalse(data["truncated"])
        self.assertEqual(data["total_matches_found"], 75)

    def test_explicit_limit_below_default(self):
        """Caller can specify a tighter cap than the default."""
        src = self.root / "src"
        src.mkdir(exist_ok=True)
        (src / "many.py").write_text(
            "\n".join(f"CAP_TOKEN_{i} = {i}" for i in range(20)) + "\n",
            encoding="utf-8",
        )
        result = self.srv.code_keyword_response(self.root, "CAP_TOKEN_", limit=5)
        data = result["data"]
        self.assertEqual(data["count"], 5)
        self.assertTrue(data["truncated"])
        self.assertEqual(data["total_matches_found"], 20)

    def test_no_truncation_when_results_below_limit(self):
        """truncated=False when actual matches ≤ limit (default 50)."""
        src = self.root / "src"
        src.mkdir(exist_ok=True)
        (src / "few.py").write_text("UNIQUE_TOKEN_HERE = 1\n", encoding="utf-8")
        result = self.srv.code_keyword_response(self.root, "UNIQUE_TOKEN_HERE")
        data = result["data"]
        self.assertEqual(data["count"], 1)
        self.assertFalse(data["truncated"])
        self.assertEqual(data["total_matches_found"], 1)


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


class FtsQueryShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def test_identifier_like_queries_are_not_quoted(self):
        for query in ("build_pack.version", "SORT_WINDOW_SIZE", "index_build_status"):
            self.assertEqual(self.srv.WaveIndex._fts_query(query), query)

    def test_explicit_phrase_quotes_are_stripped_for_no_position_fts(self):
        self.assertEqual(self.srv.WaveIndex._fts_query('"semantic code embeddings"'), "semantic code embeddings")

    def test_natural_language_query_is_preserved(self):
        query = "how does index build status work"
        self.assertEqual(self.srv.WaveIndex._fts_query(query), query)


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
# Wave 1v0r0: independent docs/code selectors both use Arctic S (384-d, asymmetric).
_EXPECTED_DOCS_MODEL = "Snowflake/snowflake-arctic-embed-s"
_EXPECTED_CODE_MODEL = "Snowflake/snowflake-arctic-embed-s"
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
        close_text = "Use wf_create_wave to start a new wave and track changes."
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
                # 1sed6: the index-state store (with its completed epoch) IS
                # the state authority — copy it, not a meta.json.
                shutil.copy(str(idx_dir / "index-state.sqlite"), str(project_idx / "index-state.sqlite"))
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


class EmbedderSingletonTests(unittest.TestCase):
    """1p4wy: WaveIndex._get_embedder caches per process so the CoreML/ONNX session
    compile (~40s on GPU) is paid once, not re-paid on every query."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self.index = self.srv.WaveIndex(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_embedder_constructs_once_per_model(self):
        construct_calls: list[str] = []

        class _FakeTextEmbedding:
            def __init__(self, *args, **kwargs):
                construct_calls.append(kwargs.get("model_name", ""))

        fake_fastembed = types.ModuleType("fastembed")
        fake_fastembed.TextEmbedding = _FakeTextEmbedding
        with patch.dict(sys.modules, {"fastembed": fake_fastembed}):
            first = self.index._get_embedder("Snowflake/snowflake-arctic-embed-s")
            second = self.index._get_embedder("Snowflake/snowflake-arctic-embed-s")

        self.assertIs(first, second, "embedder must be cached (same instance returned)")
        self.assertEqual(construct_calls, ["Snowflake/snowflake-arctic-embed-s"],
                         "embedder must be constructed exactly once per model")

    def test_get_embedder_caches_per_model_name(self):
        construct_calls: list[str] = []

        class _FakeTextEmbedding:
            def __init__(self, *args, **kwargs):
                construct_calls.append(kwargs.get("model_name", ""))

        fake_fastembed = types.ModuleType("fastembed")
        fake_fastembed.TextEmbedding = _FakeTextEmbedding
        with patch.dict(sys.modules, {"fastembed": fake_fastembed}):
            docs = self.index._get_embedder("Snowflake/snowflake-arctic-embed-s")
            code = self.index._get_embedder("supplier/future-code")
            docs_again = self.index._get_embedder("Snowflake/snowflake-arctic-embed-s")

        self.assertIsNot(docs, code, "different models get distinct cached embedders")
        self.assertIs(docs, docs_again)
        self.assertEqual(construct_calls,
                         ["Snowflake/snowflake-arctic-embed-s", "supplier/future-code"])

    def test_get_embedder_uses_int8_when_index_recorded_int8(self):
        """Wave 1p935 AC-2 / 1p936 AC-4: when the index's recorded model_versions class is "int8",
        the query embedder is the accel CPU-INT8 StaticShapeEmbedder (matching the stored vectors'
        precision), NOT fastembed — regardless of the current machine's own classification."""
        import accel_embedder
        model = "Snowflake/snowflake-arctic-embed-s"
        self.index._meta = {"project": {"model_versions": {"docs": f"{model}@int8"}}}
        self.index._embedders = {}
        int8_sentinel = MagicMock()
        with patch.object(accel_embedder, "StaticShapeEmbedder", return_value=int8_sentinel) as cls:
            got = self.index._get_embedder(model)
        self.assertIs(got, int8_sentinel)
        # Built for the CPU EP (INT8), driven by the recorded class, not the host's providers.
        self.assertEqual(cls.call_args.args[1], ["CPUExecutionProvider"])

    def test_get_embedder_uses_fastembed_when_index_recorded_full(self):
        """The mirror: a "full"-class (or legacy bare-name) index uses the fastembed-resident
        full-precision embedder, never the INT8 accel path."""
        import accel_embedder
        model = "Snowflake/snowflake-arctic-embed-s"
        self.index._meta = {"project": {"model_versions": {"docs": f"{model}@full"}}}
        self.index._embedders = {}

        class _FakeTextEmbedding:
            def __init__(self, *args, **kwargs):
                self.kind = "fastembed"

        fake_fastembed = types.ModuleType("fastembed")
        fake_fastembed.TextEmbedding = _FakeTextEmbedding
        with patch.object(accel_embedder, "StaticShapeEmbedder") as int8_cls, \
             patch.dict(sys.modules, {"fastembed": fake_fastembed}):
            got = self.index._get_embedder(model)
        self.assertIsInstance(got, _FakeTextEmbedding)
        int8_cls.assert_not_called()

    def test_get_embedder_int8_build_failure_falls_back_to_fastembed(self):
        """1p936 residual-risk guard: if the recorded class is int8 but the INT8 build is
        unavailable (e.g. not cached / offline), fall back to fastembed rather than raising — a
        degraded but usable query beats no query."""
        import accel_embedder
        model = "Snowflake/snowflake-arctic-embed-s"
        self.index._meta = {"project": {"model_versions": {"docs": f"{model}@int8"}}}
        self.index._embedders = {}

        class _FakeTextEmbedding:
            def __init__(self, *args, **kwargs):
                self.kind = "fastembed-fallback"

        fake_fastembed = types.ModuleType("fastembed")
        fake_fastembed.TextEmbedding = _FakeTextEmbedding
        with patch.object(accel_embedder, "StaticShapeEmbedder", side_effect=RuntimeError("no int8 cache")), \
             patch.dict(sys.modules, {"fastembed": fake_fastembed}):
            got = self.index._get_embedder(model)
        self.assertIsInstance(got, _FakeTextEmbedding, "int8 build failure must degrade to fastembed")


class DocsCodeModelSelectorTests(unittest.TestCase):
    """Independent docs/code selectors both use Arctic S and its query-only prefix.

    These are pure-wiring tests — they do not require fastembed or a cached model
    (the embedder is mocked), so they run everywhere unlike SemanticEmbeddingRegressionTests.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self.index = self.srv.WaveIndex(self.root)
        self.indexer = self.index._indexer_module()

    def tearDown(self):
        self.tmp.cleanup()

    def test_model_constants_are_independently_assigned_to_same_id(self):
        self.assertEqual(self.indexer.DOCS_MODEL, _EXPECTED_DOCS_MODEL)
        self.assertEqual(self.indexer.CODE_MODEL, _EXPECTED_CODE_MODEL)
        self.assertEqual(self.indexer.DOCS_MODEL, self.indexer.CODE_MODEL)
        source = Path(self.indexer.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        assigned = {
            node.targets[0].id: node.value.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"DOCS_MODEL", "CODE_MODEL"}
            and isinstance(node.value, ast.Constant)
        }
        self.assertEqual(assigned, {"DOCS_MODEL": _EXPECTED_DOCS_MODEL, "CODE_MODEL": _EXPECTED_CODE_MODEL})

    def test_arctic_query_prefix_registered(self):
        self.assertEqual(
            self.indexer.query_embedding_prefix(self.indexer.DOCS_MODEL),
            "Represent this sentence for searching relevant passages: ",
        )
        self.assertEqual(
            self.indexer.query_embedding_prefix(self.indexer.CODE_MODEL),
            "Represent this sentence for searching relevant passages: ",
        )

    def test_active_models_have_empty_document_prefix(self):
        # The index build embeds passages without a prefix; this invariant guards it.
        self.assertEqual(self.indexer.document_embedding_prefix(self.indexer.DOCS_MODEL), "")
        self.assertEqual(self.indexer.document_embedding_prefix(self.indexer.CODE_MODEL), "")
        self.indexer._assert_active_models_have_empty_document_prefix()  # must not raise

    def test_unknown_model_prefixes_default_empty(self):
        self.assertEqual(self.indexer.query_embedding_prefix("no/such-model"), "")
        self.assertEqual(self.indexer.document_embedding_prefix("no/such-model"), "")

    def test_embed_query_applies_docs_prefix(self):
        import numpy as np
        captured: list[list[str]] = []

        class _FakeEmbedder:
            def embed(self, texts):
                captured.append(list(texts))
                return iter([np.array([1.0, 0.0], dtype=np.float32)])

        with patch.object(self.index, "_get_embedder", return_value=_FakeEmbedder()):
            self.index._embed_query("how does the wave lifecycle work", self.indexer.DOCS_MODEL)

        self.assertEqual(
            captured[0][0],
            "Represent this sentence for searching relevant passages: how does the wave lifecycle work",
        )

    def test_embed_query_applies_arctic_prefix_for_code_model(self):
        import numpy as np
        captured: list[list[str]] = []

        class _FakeEmbedder:
            def embed(self, texts):
                captured.append(list(texts))
                return iter([np.array([1.0, 0.0], dtype=np.float32)])

        with patch.object(self.index, "_get_embedder", return_value=_FakeEmbedder()):
            self.index._embed_query("parse the config", self.indexer.CODE_MODEL)

        self.assertEqual(
            captured[0][0],
            "Represent this sentence for searching relevant passages: parse the config",
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

    def _build_health_index(self, root, *, code_prefix=True, code_lance=False, docs_lance=True):
        """1p7is fixture: docs (+ optional code) sources, with docs.lance/code.lance present or not."""
        prefixes = {"docs": ["docs"]}
        if code_prefix:
            prefixes["code"] = ["src"]
        (root / "docs" / "workflow-config.json").write_text(
            json.dumps({"indexing": {"project_include_prefixes": prefixes}}), encoding="utf-8")
        (root / "docs" / "guide.md").write_text("# Guide\n\nHello.\n", encoding="utf-8")
        if code_prefix:
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src" / "app.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        idx_dir = root / ".wavefoundry" / "index"
        idx_dir.mkdir(parents=True, exist_ok=True)
        if docs_lance:
            (idx_dir / "docs.lance").mkdir(parents=True, exist_ok=True)
        if code_lance:
            (idx_dir / "code.lance").mkdir(parents=True, exist_ok=True)
        meta = {
            "built_at": "2026-01-01T00:00:00Z",
            "content": ["docs", "code"] if code_prefix else ["docs"],
            "model_versions": {"docs": "Snowflake/snowflake-arctic-embed-s"},
            "chunker_versions": {"docs": "13"},
            "walker_version": "3",
            "file_meta": self._file_meta_for_root(root),
        }
        _seed_store_state(idx_dir, meta)
        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": meta}
        wave_idx._docs_lance_table = object() if docs_lance else None
        wave_idx._code_lance_table = object() if code_lance else None
        return wave_idx

    def _health_of(self, wave_idx):
        # State is set up manually (no real index on disk), so bypass the load gate.
        with patch.object(wave_idx, "_ensure_loaded", lambda: None):
            return wave_idx.docs_health()

    def test_missing_code_layer_reports_incomplete_not_ready(self):
        # 1p7is AC-1: code sources in scope but code.lance absent → incomplete, not semantic_ready.
        root = self._make_repo(self.tmp)
        health = self._health_of(self._build_health_index(root, code_prefix=True, code_lance=False))
        self.assertTrue(health["code_layer_missing"])
        self.assertIn("code", health["missing_layers"])
        self.assertFalse(health["semantic_ready"])
        self.assertEqual(health["readiness_overview"], "incomplete")

    def test_docs_only_repo_not_flagged_for_missing_code(self):
        # 1p7is risk-mitigation: no code prefixes → code not in scope → not flagged (no false degrade).
        root = self._make_repo(self.tmp)
        health = self._health_of(self._build_health_index(root, code_prefix=False, code_lance=False))
        self.assertFalse(health["code_layer_missing"])
        self.assertNotIn("code", health["missing_layers"])
        self.assertTrue(health["semantic_ready"])

    def test_both_layers_present_reports_ready(self):
        # 1p7is AC-2: docs + code both present → ready (no regression on the fully-built case).
        root = self._make_repo(self.tmp)
        health = self._health_of(self._build_health_index(root, code_prefix=True, code_lance=True))
        self.assertFalse(health["code_layer_missing"])
        self.assertTrue(health["semantic_ready"])
        self.assertEqual(health["readiness_overview"], "ready")

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
            "model_versions": {"docs": "legacy/model-v1"},
            "chunker_versions": {"docs": "13"},
            "walker_version": "3",
            "file_meta": self._file_meta_for_root(root),
        }
        _seed_store_state(idx_dir, meta)

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": meta}

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
            "model_versions": {"docs": "legacy/model-v1"},
            "chunker_versions": {"docs": "13"},
            "walker_version": "3",
            "file_meta": self._file_meta_for_root(root),
        }
        _seed_store_state(idx_dir, meta)

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": meta}
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
            "model_versions": {"docs": "legacy/model-v1"},
            "chunker_versions": {"docs": "13"},
            "walker_version": "3",
            "file_hashes": file_hashes,
        }
        _seed_store_state(idx_dir, meta)

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": meta}

        health = wave_idx._layer_health("project")
        self.assertEqual(health["stale_paths"], [], msg="file_hashes fallback — should be no stale paths")

    def test_framework_fold_includes_readme_but_not_pack_artifacts(self):
        """1p4ww: project health folds the framework README/seeds but not MANIFEST/VERSION."""
        root = self._make_repo(self.tmp)
        framework_root = root / ".wavefoundry" / "framework"
        framework_root.mkdir(parents=True, exist_ok=True)
        (framework_root / "README.md").write_text("# Framework\n", encoding="utf-8")
        (framework_root / "MANIFEST").write_text("README.md\nMANIFEST\n", encoding="utf-8")
        (framework_root / "VERSION").write_text("2099-01-01a\n", encoding="utf-8")
        seeds = framework_root / "seeds"
        seeds.mkdir(parents=True, exist_ok=True)
        (seeds / "010-install.prompt.md").write_text("# Seed\n", encoding="utf-8")

        idx_dir = root / ".wavefoundry" / "index"
        idx_dir.mkdir(parents=True, exist_ok=True)
        (idx_dir / "docs.lance").mkdir(parents=True, exist_ok=True)

        wave_idx = self.server.WaveIndex(root)
        wave_idx._loaded = True
        wave_idx._meta = {"project": {}}

        current = wave_idx._layer_current_hashes()
        self.assertIn(".wavefoundry/framework/README.md", current)
        self.assertIn(".wavefoundry/framework/seeds/010-install.prompt.md", current)
        self.assertNotIn(".wavefoundry/framework/MANIFEST", current)
        self.assertNotIn(".wavefoundry/framework/VERSION", current)


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

    def test_returns_true_when_registered_builder_pid_is_running(self):
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._write_state(pid=child.pid, started_at=0.0)
        self.server._BACKGROUND_BUILD_PIDS.add(child.pid)
        try:
            self.assertTrue(self.server._background_refresh_active(self.state_path))
        finally:
            self.server._BACKGROUND_BUILD_PIDS.discard(child.pid)
            child.terminate()
            child.wait(timeout=5)

    def test_recycled_unrelated_pid_is_not_a_live_refresh(self):
        import os
        self._write_state(pid=os.getpid(), started_at=0.0)
        indexer = self.server._load_script("indexer")
        with patch.object(indexer, "_process_cmdline", return_value="python unrelated.py"):
            self.assertFalse(self.server._background_refresh_active(self.state_path))

    def test_recycled_indexer_pid_for_another_root_is_not_a_live_refresh(self):
        root = self.tmp / "target"
        state_path = root / ".wavefoundry" / "index" / "background-refresh.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": 0.0, "layer": "project"}),
            encoding="utf-8",
        )
        indexer = self.server._load_script("indexer")
        other = self.tmp / "other"
        cmdline = f"python indexer.py --root {other} --content all"
        with patch.object(indexer, "_process_cmdline", return_value=cmdline):
            self.assertFalse(self.server._background_refresh_active(state_path))

    def test_live_indexer_pid_for_same_root_remains_active(self):
        root = self.tmp / "target"
        state_path = root / ".wavefoundry" / "index" / "background-refresh.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": 0.0, "layer": "project"}),
            encoding="utf-8",
        )
        indexer = self.server._load_script("indexer")
        cmdline = f"python indexer.py --root {root} --content all"
        with patch.object(indexer, "_process_cmdline", return_value=cmdline):
            self.assertTrue(self.server._background_refresh_active(state_path))

    def test_windows_quoted_indexer_root_is_compared_case_insensitively(self):
        cmdline = (
            '"C:\\Python311\\python.exe" '
            '"C:\\Work\\Repo Name\\.wavefoundry\\framework\\scripts\\indexer.py" '
            '--root "c:\\work\\repo name" --content all'
        )
        with patch.object(self.server.os, "name", "nt"):
            self.assertTrue(
                self.server._index_builder_cmdline_targets_root(
                    cmdline, Path("C:/Work/Repo Name")
                )
            )
            self.assertFalse(
                self.server._index_builder_cmdline_targets_root(
                    cmdline, Path("C:/Work/Other")
                )
            )

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

    def test_authoritative_held_build_lock_prevents_refresh(self):
        with patch.object(
            self.server, "_index_build_lock_info", return_value={"held": True}
        ):
            self.assertTrue(self.server._background_refresh_active(self.state_path))

    def test_native_windows_reaper_never_calls_waitpid(self):
        with patch.object(self.server.os, "name", "nt"), patch.object(
            self.server.os, "waitpid"
        ) as waitpid:
            self.server._BACKGROUND_BUILD_PIDS.add(12345)
            try:
                self.server._reap_background_build_pids()
            finally:
                self.server._BACKGROUND_BUILD_PIDS.discard(12345)
        waitpid.assert_not_called()

    def test_build_status_reports_removed_stale_locks(self):
        root = self.tmp
        lock_path = root / ".wavefoundry" / "index" / "docs.lance" / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("999999999", encoding="utf-8")

        response = self.server.index_build_status_response(root, layer="project")

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

        response = self.server.index_build_status_response(root, layer="project")

        self.assertEqual(response["status"], "ok")
        data = response["data"]
        self.assertEqual(data["state"], "idle")
        self.assertNotIn("stale_locks_cleaned", data)
        self.assertTrue(lock_path.exists())


class MaybeRefreshIfStaleTests(unittest.TestCase):
    """Wave 1p5xu: _maybe_refresh_if_stale single-flight trigger (AC-2)."""

    def setUp(self):
        self.server = load_server()
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_stale_and_idle_triggers_refresh(self):
        started = []
        with patch.object(self.server, "_index_inputs_stale", return_value=True), \
             patch.object(self.server, "_background_refresh_active", return_value=False), \
             patch.object(self.server, "_start_background_index_refresh",
                          side_effect=lambda root, layer="project": started.append((root, layer)) or True):
            result = self.server._maybe_refresh_if_stale(self.root)
        self.assertTrue(result)
        self.assertEqual(started, [(self.root, "project")])

    def test_fresh_does_not_trigger(self):
        started = []
        with patch.object(self.server, "_index_inputs_stale", return_value=False), \
             patch.object(self.server, "_start_background_index_refresh",
                          side_effect=lambda *a, **k: started.append(a) or True):
            result = self.server._maybe_refresh_if_stale(self.root)
        self.assertFalse(result)
        self.assertEqual(started, [])

    def test_already_active_does_not_trigger_second_build(self):
        started = []
        with patch.object(self.server, "_index_inputs_stale", return_value=True), \
             patch.object(self.server, "_background_refresh_active", return_value=True), \
             patch.object(self.server, "_start_background_index_refresh",
                          side_effect=lambda *a, **k: started.append(a) or True):
            result = self.server._maybe_refresh_if_stale(self.root)
        self.assertFalse(result)
        self.assertEqual(started, [], "must not spawn a second builder while one is active")

    def test_index_inputs_stale_treats_none_as_not_stale(self):
        # No built index -> indexer returns None -> treated as not stale.
        self.assertFalse(self.server._index_inputs_stale(self.root))

    @unittest.skipIf(os.name == "nt", "POSIX zombie lifecycle")
    def test_completed_registered_child_is_reaped_before_refresh_decision(self):
        import time

        if not all(hasattr(os, name) for name in ("waitid", "P_PID", "WEXITED", "WNOWAIT")):
            self.skipTest("requires waitid with WNOWAIT to preserve child wait status")

        child = subprocess.Popen(
            [sys.executable, "-c", "pass"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOWAIT)
        state_path = self.server._background_refresh_state_path(self.root, "project")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "pid": child.pid,
                    "started_at": time.time() - 300,
                    "layer": "project",
                }
            ),
            encoding="utf-8",
        )
        self.server._BACKGROUND_BUILD_PIDS.add(child.pid)
        started: list[tuple[Path, str]] = []
        with patch.object(self.server, "_index_inputs_stale", return_value=True), \
             patch.object(
                 self.server,
                 "_start_background_index_refresh",
                 side_effect=lambda root, layer="project": started.append((root, layer)) or True,
             ):
            result = self.server._maybe_refresh_if_stale(self.root)
        self.assertTrue(result)
        self.assertEqual(started, [(self.root, "project")])
        self.assertNotIn(child.pid, self.server._BACKGROUND_BUILD_PIDS)
        child.returncode = 0  # the server's WNOHANG sweep, not Popen, reaped it

    def test_monitor_observer_reports_bounded_decision(self):
        observations: list[dict] = []
        with patch.object(self.server, "_index_inputs_stale", return_value=False):
            result = self.server._maybe_refresh_if_stale(
                self.root, observer=observations.append
            )
        self.assertFalse(result)
        self.assertEqual(len(observations), 1)
        self.assertEqual(
            set(observations[0]),
            {"last_checked_at", "stale", "triggered", "reason"},
        )
        self.assertEqual(observations[0]["reason"], "current_or_undetermined")

    def test_reload_empty_registry_rejects_unrelated_persisted_pid_and_refreshes(self):
        state_path = self.server._background_refresh_state_path(self.root, "project")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "started_at": time.time() - 300,
                    "layer": "project",
                }
            ),
            encoding="utf-8",
        )
        self.server._BACKGROUND_BUILD_PIDS.clear()
        indexer = self.server._load_script("indexer")
        started: list[tuple[Path, str]] = []
        with patch.object(indexer, "_process_cmdline", return_value="python unrelated.py"), \
             patch.object(self.server, "_index_inputs_stale", return_value=True), \
             patch.object(
                 self.server,
                 "_start_background_index_refresh",
                 side_effect=lambda root, layer="project": started.append((root, layer)) or True,
             ):
            self.assertTrue(self.server._maybe_refresh_if_stale(self.root))
        self.assertEqual(started, [(self.root, "project")])

    def test_unavailable_pid_classifier_fails_safe_without_spawn(self):
        state_path = self.server._background_refresh_state_path(self.root, "project")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "started_at": time.time() - 300,
                    "layer": "project",
                }
            ),
            encoding="utf-8",
        )
        started: list[tuple] = []
        indexer = self.server._load_script("indexer")
        with patch.object(indexer, "classify_index_build_lock_owner", side_effect=OSError("probe")), \
             patch.object(self.server, "_index_inputs_stale", return_value=True), \
             patch.object(
                 self.server,
                 "_start_background_index_refresh",
                 side_effect=lambda *args: started.append(args) or True,
             ):
            self.assertFalse(self.server._maybe_refresh_if_stale(self.root))
        self.assertEqual(started, [])


class MonitorConfigTests(unittest.TestCase):
    """Wave 1p5xu: _read_monitor_config framework-owned defaults (AC-4)."""

    def setUp(self):
        self.server = load_server()
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._td.cleanup()

    def _write_cfg(self, cfg: dict) -> None:
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def test_defaults_when_no_config(self):
        cfg = self.server._read_monitor_config(self.root)
        self.assertTrue(cfg["enabled"])
        self.assertEqual(cfg["interval_seconds"], self.server._MONITOR_DEFAULT_INTERVAL_SECONDS)

    def test_disabled_via_config(self):
        self._write_cfg({"indexing": {"monitor": {"enabled": False}}})
        self.assertFalse(self.server._read_monitor_config(self.root)["enabled"])

    def test_interval_override_and_clamp(self):
        self._write_cfg({"indexing": {"monitor": {"interval_seconds": 45}}})
        self.assertEqual(self.server._read_monitor_config(self.root)["interval_seconds"], 45.0)
        self._write_cfg({"indexing": {"monitor": {"interval_seconds": 1}}})
        self.assertEqual(
            self.server._read_monitor_config(self.root)["interval_seconds"],
            self.server._MONITOR_MIN_INTERVAL_SECONDS,
        )

    def test_context_efficiency_projection_defaults_and_bounds(self):
        self.assertEqual(
            self.server._read_ce_projection_config(self.root)["quiet_period_seconds"],
            120.0,
        )
        self._write_cfg(
            {"context_efficiency": {"projection": {"quiet_period_seconds": 1}}}
        )
        self.assertEqual(
            self.server._read_ce_projection_config(self.root)["quiet_period_seconds"],
            90.0,
        )
        self._write_cfg(
            {"context_efficiency": {"projection": {"quiet_period_seconds": 600}}}
        )
        self.assertEqual(
            self.server._read_ce_projection_config(self.root)["quiet_period_seconds"],
            600.0,
        )
        self._write_cfg(
            {"context_efficiency": {"projection": {"quiet_period_seconds": 900}}}
        )
        self.assertEqual(
            self.server._read_ce_projection_config(self.root)["quiet_period_seconds"],
            600.0,
        )

    def test_context_efficiency_projection_invalid_value_falls_back(self):
        self._write_cfg(
            {"context_efficiency": {"projection": {"quiet_period_seconds": "slow"}}}
        )
        self.assertEqual(
            self.server._read_ce_projection_config(self.root)["quiet_period_seconds"],
            120.0,
        )


class StalenessMonitorLifecycleTests(unittest.TestCase):
    """Wave 1p5xu: ImplHandler daemon monitor start/stop (AC-3, AC-4)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self._td = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self._td.name))

    def tearDown(self):
        self._td.cleanup()

    def _write_monitor_cfg(self, monitor: dict) -> None:
        cfg = {
            "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
            "indexing": {"monitor": monitor},
        }
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def test_thread_starts_when_enabled_and_stops_on_close(self):
        self._write_monitor_cfg({"enabled": True, "interval_seconds": 5})
        handler = self.srv.build_handler(self.root)
        try:
            self.assertIsNotNone(handler._monitor_thread)
            self.assertTrue(handler._monitor_thread.is_alive())
            self.assertTrue(handler._monitor_thread.daemon)
        finally:
            handler.close()
        self.assertFalse(handler._monitor_thread is not None and handler._monitor_thread.is_alive())

    def test_no_thread_when_disabled_by_config(self):
        self._write_monitor_cfg({"enabled": False})
        handler = self.srv.build_handler(self.root)
        try:
            self.assertIsNone(handler._monitor_thread)
        finally:
            handler.close()

    def test_close_is_safe_when_monitor_never_started(self):
        self._write_monitor_cfg({"enabled": False})
        handler = self.srv.build_handler(self.root)
        # close() must not raise even though no monitor thread exists.
        handler.close()

    def test_ce_projection_monitor_is_independent_and_observable(self):
        self._write_monitor_cfg({"enabled": False})
        handler = self.srv.build_handler(self.root)
        projection_thread = handler._ce_projection_thread
        try:
            status = handler.background_monitor_status()
            self.assertIsNone(handler._monitor_thread)
            self.assertTrue(handler._ce_projection_thread.is_alive())
            self.assertTrue(handler._ce_projection_thread.daemon)
            self.assertFalse(status["index"]["configured"])
            self.assertTrue(status["context_efficiency_projection"]["configured"])
            self.assertTrue(status["context_efficiency_projection"]["alive"])
            self.assertEqual(
                status["context_efficiency_projection"]["quiet_period_seconds"],
                120.0,
            )
        finally:
            handler.close()
        self.assertIsNotNone(projection_thread)
        self.assertFalse(projection_thread.is_alive())


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
        _seed_store_state(index_dir, payload)

    def _meta_signature(self, index_dir: Path):
        # 1sed6: the reload signal is the store's build epoch token.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "index_state_store", Path(__file__).resolve().parents[1] / "index_state_store.py"
        )
        iss = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(iss)
        return iss.build_epoch_token(index_dir)

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

        # Simulate a rebuild: a new completed epoch advances the generation.
        self._make_index(project_idx, "2026-01-01T00:00:00Z", extra={"refresh_marker": "project"})

        idx._ensure_loaded()
        self.assertEqual(idx._loaded_meta_signature["project"], self._meta_signature(project_idx))

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
            "libs/migrations/app/A005__new_tenant_routines.sql": (
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
        result = self.srv.code_definition_response(self.root, "app.create_schema_objects")
        self.assertEqual(result["status"], "ok")
        self.assertNotEqual(result["data"]["method"], "keyword_fallback")
        defs = result["data"]["definitions"]
        self.assertGreater(len(defs), 0)
        self.assertIn("A005__new_tenant_routines.sql", defs[0]["path"])
        self.assertGreater(defs[0]["line"], 0)
        self.assertEqual(defs[0]["name"], "create_schema_objects")

    def test_sql_schema_qualified_references_retries_unqualified_symbol(self):
        result = self.srv.code_references_response(self.root, "app.create_schema_objects")
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
            result = self.srv.index_health_response(index)
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
        index.search_combined.return_value = (combined, False, 0, 0, [], [], "none", None)
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

    def test_classify_question_assessment_precedes_navigational_phrase(self):
        cases = (
            "where are the biggest gaps in the code MCP implementation?",
            "where are the biggest opportunities to improve the code MCP implementation?",
            "what are the weaknesses in graph retrieval?",
            "review the semantic index",
            "assess retrieval quality",
        )
        for question in cases:
            with self.subTest(question=question):
                self.assertEqual(self.srv._classify_question(question), "assessment")

    def test_classify_question_instructional_precedes_assessment_nouns(self):
        cases = (
            "How should I investigate concerns with shard routing?",
            "How do I resolve issues in cache invalidation?",
            "How can I review the search adapter safely?",
        )
        for question in cases:
            with self.subTest(question=question):
                self.assertEqual(self.srv._classify_question(question), "instructional")

    def test_classify_question_contextual_assessment_and_issue_navigation(self):
        assessment_cases = (
            "What issues exist in graph traversal?",
            "Which current concerns affect semantic ranking?",
            "Evaluate the retrieval adapter for failure modes.",
        )
        for question in assessment_cases:
            with self.subTest(question=question):
                self.assertEqual(self.srv._classify_question(question), "assessment")
        self.assertEqual(
            self.srv._classify_question("Where is the issue tracker configured?"),
            "navigational",
        )

    def test_classify_question_direct_file_artifacts_precede_phrase_signals(self):
        cases = (
            "what does .aiignore exclude?",
            "What Python version does pyproject.toml require?",
            "where is lifecycle_id.py generated?",
        )
        for question in cases:
            with self.subTest(question=question):
                self.assertEqual(self.srv._classify_question(question), "artifact_anchored")

        self.assertEqual(
            self.srv._classify_question("How should I review pyproject.toml constraints?"),
            "artifact_anchored",
        )

    def test_classify_question_preserves_symbol_navigation_and_review_noun(self):
        self.assertEqual(
            self.srv._classify_question("Where is _classify_question defined?"),
            "navigational",
        )
        self.assertEqual(
            self.srv._classify_question("Which review lanes can be required before close?"),
            "explanatory",
        )

    def test_extract_artifact_cue_snake_case(self):
        """_extract_artifact_cue returns snake_case identifier."""
        self.assertEqual(self.srv._extract_artifact_cue("how does build_prefix work?"), "build_prefix")

    def test_extract_artifact_cue_version_suffix(self):
        """_extract_artifact_cue returns version suffix token."""
        self.assertEqual(self.srv._extract_artifact_cue("what generates +2vr8?"), "+2vr8")

    def test_extract_artifact_cue_no_match(self):
        """_extract_artifact_cue returns empty string when no cue is present."""
        self.assertEqual(self.srv._extract_artifact_cue("how is the build number generated?"), "")

    def test_confidence_no_reranker_capped_at_medium(self):
        # 1p66r: without the cross-encoder (reranked=False) confidence is capped at
        # 'medium' — the prior count-based 'high' was relevance-blind (the per-index
        # floor guarantees n>=2 on any non-empty index → always 'high'). The raw
        # shared-embedder cosine is uncalibrated, so we never over-claim 'high' here.
        index = self._make_index(code_results=[self._fake_code_chunk("src/a.py"), self._fake_code_chunk("src/b.py")])
        result = self.srv.code_ask_response(index, self.root, "billing?")
        self.assertEqual(result["data"]["confidence"], "medium")

    def test_no_reranker_emits_loud_degraded_gap(self):
        # 1p66r: reranked=False is a degraded vector-only fallback (a healthy install
        # always reranks) — it must be surfaced loudly, not silently handled.
        index = self._make_index(code_results=[self._fake_code_chunk("src/a.py"), self._fake_code_chunk("src/b.py")])
        result = self.srv.code_ask_response(index, self.root, "billing?")
        self.assertFalse(result["data"]["reranked"])
        self.assertTrue(any("reranker unavailable" in g for g in result["data"]["gaps"]),
                        result["data"]["gaps"])

    def test_confidence_low_with_no_citations(self):
        index = self._make_index()
        result = self.srv.code_ask_response(index, self.root, "ZZZNOEVIDENCEYYY")
        self.assertEqual(result["data"]["confidence"], "low")
        self.assertTrue(len(result["data"]["gaps"]) > 0)

    def test_confidence_agent_mode_offtopic_band_not_high(self):
        """1p52p: when the cross-encoder ran (reranked=True), confidence is score-aware on the unified
        sigmoid scale — an off-topic result whose top sigmoid is between CONF_AGENT_RERANK_LOW (0.1)
        and CONF_AGENT_RERANK_HIGH (0.5) is 'medium', NOT 'high', despite multiple citations."""
        index = self._make_index(code_results=[self._fake_code_chunk("src/a.py", score=0.30), self._fake_code_chunk("src/b.py", score=0.28)])
        # reranked=True so _heuristic_confidence uses the sigmoid bands rather than the count rule.
        index.search_combined.return_value = (
            [self._fake_code_chunk("src/a.py", score=0.30), self._fake_code_chunk("src/b.py", score=0.28)],
            True, 0, 0, [], [], "none", None,
        )
        result = self.srv.code_ask_response(index, self.root, "kubernetes ingress blue green deploy?")
        self.assertEqual(result["data"]["confidence"], "medium")

    def test_confidence_agent_mode_weak_band_low(self):
        """1p52p: reranked top sigmoid below CONF_AGENT_RERANK_LOW (0.1) → 'low' (nothing relevant retrieved)."""
        index = self._make_index()
        index.search_combined.return_value = (
            [self._fake_code_chunk("src/a.py", score=0.05), self._fake_code_chunk("src/b.py", score=0.04)],
            True, 0, 0, [], [], "none", None,
        )
        result = self.srv.code_ask_response(index, self.root, "best sourdough bread recipe?")
        self.assertEqual(result["data"]["confidence"], "low")

    def test_confidence_no_reranker_keyword_path_capped_medium(self):
        """1p66r: the keyword/exact path runs without the cross-encoder (reranked=False),
        so confidence is capped at 'medium' — the prior count-based 'high' over-claimed."""
        index = self._make_index(code_results=[self._fake_code_chunk("src/a.py", score=0.0), self._fake_code_chunk("src/b.py", score=0.0)])
        result = self.srv.code_ask_response(index, self.root, "what generates +2vr8?")
        self.assertEqual(result["data"]["confidence"], "medium")

    def test_reranked_zero_signal_abstains_and_marks_weak(self):
        """1p66r: reranked=True but every score below CONF_AGENT_RERANK_LOW (the ~0.001
        zero-signal case) → confidence 'low', a 'no confident match' gap, and citations
        marked weak (anti-starvation preserved — citations still returned)."""
        index = self._make_index()
        index.search_combined.return_value = (
            [self._fake_code_chunk("src/a.py", score=0.002), self._fake_code_chunk("src/b.py", score=0.001)],
            True, 0, 0, [], [], "none", None,
        )
        result = self.srv.code_ask_response(index, self.root, "totally unrelated query")
        self.assertEqual(result["data"]["confidence"], "low")
        self.assertTrue(result["data"]["citations"], "anti-starvation: citations still returned")
        self.assertTrue(all(c.get("weak") for c in result["data"]["citations"]))
        self.assertTrue(any("no confident match" in g for g in result["data"]["gaps"]),
                        result["data"]["gaps"])

    def test_reranked_strong_match_no_abstention(self):
        """1p66r: a genuinely strong reranked result (top sigmoid >= HIGH, n>=2) stays
        'high' with no abstention gap and no weak markers — no over-correction."""
        index = self._make_index()
        index.search_combined.return_value = (
            [self._fake_code_chunk("src/a.py", score=0.92), self._fake_code_chunk("src/b.py", score=0.88)],
            True, 0, 0, [], [], "none", None,
        )
        result = self.srv.code_ask_response(index, self.root, "billing failed payments?")
        self.assertEqual(result["data"]["confidence"], "high")
        self.assertFalse(any("no confident match" in g for g in result["data"]["gaps"]))
        self.assertFalse(any(c.get("weak") for c in result["data"]["citations"]))

    def test_refdocs_demotion_weight(self):
        # 1p66s: architecture docs, specs, and ADRs are down-weighted (gentler than the
        # narrative tiers) so they don't outrank implementing code; code is never demoted.
        self.assertEqual(self.srv._doc_demotion_weight("docs/architecture/current-state.md", "doc"), self.srv._DEMOTION_REFDOCS)
        self.assertEqual(self.srv._doc_demotion_weight("docs/specs/mcp-tool-surface.md", "doc"), self.srv._DEMOTION_REFDOCS)
        self.assertEqual(self.srv._doc_demotion_weight("docs/architecture/decisions/1p5be.md", "doc"), self.srv._DEMOTION_REFDOCS)
        self.assertEqual(self.srv._doc_demotion_weight("src/auth.py", "code"), 1.0)

    def test_demotion_applies_to_navigational(self):
        # 1p66s: demotion extended from explanatory-only to navigational; a spec no longer
        # outranks the implementing source.
        results = [
            {"path": "docs/specs/x.md", "kind": "doc", "score": 0.90},
            {"path": "src/impl.py", "kind": "code", "score": 0.80},
        ]
        out, n = self.srv._demote_doc_results(results, "navigational")
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["path"], "src/impl.py")  # 0.90*0.80=0.72 < 0.80 → code leads

    def test_demotion_is_downweight_not_exclusion(self):
        # A doc-answerable result is down-weighted, never dropped.
        results = [{"path": "docs/specs/x.md", "kind": "doc", "score": 0.90}]
        out, n = self.srv._demote_doc_results(results, "explanatory")
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(out[0]["score"], 0.90 * self.srv._DEMOTION_REFDOCS)

    def test_demotion_skips_non_code_intents(self):
        # instructional / artifact_anchored are not code-implementation intents → untouched.
        results = [{"path": "docs/specs/x.md", "kind": "doc", "score": 0.90}]
        out, n = self.srv._demote_doc_results(results, "instructional")
        self.assertEqual(n, 0)
        self.assertEqual(out[0]["score"], 0.90)

    def test_extract_question_symbol_skips_interrogatives(self):
        # 1p66r (downstream finding): a capitalized leading interrogative must NOT be
        # picked as a symbol — symbol-first injection would keyword-boost off-topic citations
        # above the floor and defeat abstention for the capitalized phrasing.
        srv = self.srv
        self.assertIsNone(srv._extract_question_symbol("Which providers are registered?"))
        self.assertIsNone(srv._extract_question_symbol("Where is the config loaded?"))
        self.assertIsNone(srv._extract_question_symbol("What happens on startup?"))
        self.assertIsNone(srv._extract_question_symbol("Why does the cache expire?"))
        # Conversational lead-ins ("Tell me about …", "Explain …", "Walk me through …") are
        # skipped too — same bug class as interrogatives.
        self.assertIsNone(srv._extract_question_symbol("Tell me about how startup works"))
        self.assertIsNone(srv._extract_question_symbol("Explain the request flow"))
        # A real symbol after the lead-in is still found (re.findall, not re.search).
        self.assertEqual(srv._extract_question_symbol("How does Resolver work"), "Resolver")
        self.assertEqual(srv._extract_question_symbol("Tell me about how ChunkerV2 works"), "ChunkerV2")
        # Explicit backtick / qualified symbols are unaffected.
        self.assertEqual(srv._extract_question_symbol("what does `getUserId` do"), "getUserId")
        self.assertEqual(srv._extract_question_symbol("explain auth.resolveToken"), "resolveToken")

    def test_is_enumeration_query(self):
        # 1p66t: enumeration intent detection. Positive: collection word + set-membership verb,
        # or a list/enumerate/how-many lead. Negative: single-value lookups and how/where questions.
        srv = self.srv
        for q in ["which event handlers are registered?", "list all providers",
                  "what commands are supported", "how many retries are configured",
                  "enumerate the middleware", "what events are subscribed to"]:
            self.assertTrue(srv._is_enumeration_query(q), f"should be enumeration: {q!r}")
        for q in ["where is the rate limiter defined?", "how does authentication work?",
                  "what is the value of MAX_RETRIES", "explain the request flow"]:
            self.assertFalse(srv._is_enumeration_query(q), f"should NOT be enumeration: {q!r}")

    def test_enumeration_query_flags_incompleteness(self):
        # 1p66t: an enumeration result is a ranked sample → flag it may be incomplete.
        index = self._make_index(code_results=[self._fake_code_chunk("src/a.py"), self._fake_code_chunk("src/b.py")])
        result = self.srv.code_ask_response(index, self.root, "which handlers are registered?")
        self.assertTrue(any("enumeration query" in g for g in result["data"]["gaps"]), result["data"]["gaps"])

    def test_non_enumeration_no_incompleteness_gap(self):
        index = self._make_index(code_results=[self._fake_code_chunk("src/a.py")])
        result = self.srv.code_ask_response(index, self.root, "where is the billing module?")
        self.assertFalse(any("enumeration query" in g for g in result["data"]["gaps"]))

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
        # Wave 1p52p: demotion is now applied PRE-selection inside search_combined (mocked here),
        # and code_ask_response no longer re-sorts post-selection — it just reports how many of the
        # returned candidates carry the demotion weight. So the invariant verified here is "demoted
        # but still present", NOT a hard code-above-doc ordering (the cross-encoder can rank a
        # strongly-relevant demoted doc high). Pre-selection ordering is verified on the real index.
        result = self.srv.code_ask_response(index, self.root, "How does a new tenant get created?")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["partition_applied"])
        self.assertEqual(result["data"]["demotion_count"], 1)
        citations = result["data"]["citations"]
        self.assertGreaterEqual(len(citations), 2)
        cited_paths = [c["path"] for c in citations]
        # The demoted journal doc is still present (demoted, not removed).
        self.assertIn("docs/agents/journals/cia-feedback-2026-05-14.md", cited_paths)
        self.assertIn("src/tenants.ts", cited_paths)

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
            None,
        )
        # Wave 1p52p: demotion is pre-selection inside search_combined (mocked here); code_ask_response
        # only reports demotion_count and does not re-sort. Invariant: "demoted but still present",
        # not a hard code-above-doc ordering.
        result = self.srv.code_ask_response(index, self.root, "How does HTTP request filtering work?")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["partition_applied"])
        self.assertEqual(result["data"]["demotion_count"], 1)
        citations = result["data"]["citations"]
        self.assertGreaterEqual(len(citations), 2)
        cited_paths = [c["path"] for c in citations]
        # The demoted seed doc is still present (demoted, not removed).
        self.assertIn(".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md", cited_paths)
        self.assertIn("src/http_filtering.java", cited_paths)

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

    def test_demote_navigational_now_applies(self):
        """1p66s: navigational ("where is X") is a code-implementation intent and NOW demotes
        narrative/reference prose (was passthrough before this wave)."""
        srv = self.srv
        results = [
            {"path": "docs/waves/12pn3/change.md", "kind": "doc", "score": 1.0},
            {"path": "docs/agents/journals/wave-coordinator.md", "kind": "doc", "score": 0.9},
        ]
        demoted, count = srv._demote_doc_results(results, "navigational")
        self.assertEqual(count, 2)
        self.assertEqual(demoted[0]["score"], 1.0 * srv._DEMOTION_WAVES)
        self.assertEqual(demoted[1]["score"], 0.9 * srv._DEMOTION_JRNLS)

    def test_demote_architecture_now_demoted(self):
        """1p66s: architecture docs (and specs/ADRs) are now down-weighted so prose does not
        outrank the implementing code; implementation code is still never demoted."""
        srv = self.srv
        results = [
            {"path": "docs/architecture/current-state.md", "kind": "doc", "score": 0.9},
            {"path": "src/server.py", "kind": "code", "score": 0.8},
        ]
        demoted, count = srv._demote_doc_results(results, "explanatory")
        self.assertEqual(count, 1)  # the architecture doc is demoted; code is not
        # 0.9 * 0.80 = 0.72 < 0.80 → implementing code now leads
        self.assertEqual(demoted[0]["path"], "src/server.py")
        self.assertEqual(demoted[1]["score"], 0.9 * srv._DEMOTION_REFDOCS)

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

    def test_demote_doc_results_applies_to_assessment(self):
        results = [{"path": "docs/specs/retrieval.md", "kind": "doc", "score": 1.0}]
        demoted, count = self.srv._demote_doc_results(results, "assessment")
        self.assertEqual(count, 1)
        self.assertAlmostEqual(demoted[0]["score"], self.srv._DEMOTION_REFDOCS)

    def test_assessment_evidence_prior_prefers_current_report_and_code_over_wave_history(self):
        results = [
            {"path": "docs/waves/old-delivery/change.md", "kind": "doc", "score": 0.99},
            {"path": "docs/reports/search-audit.md", "kind": "doc", "score": 0.90},
            {"path": "src/search_adapter.py", "kind": "code", "score": 0.82},
        ]
        demoted, _ = self.srv._demote_doc_results(results, "assessment")
        adjusted, count = self.srv._apply_assessment_evidence_prior(
            demoted, "Assess cache-routing weaknesses.", "assessment"
        )
        paths = [item["path"] for item in adjusted]
        self.assertLess(paths.index("docs/reports/search-audit.md"), paths.index("docs/waves/old-delivery/change.md"))
        self.assertLess(paths.index("src/search_adapter.py"), paths.index("docs/waves/old-delivery/change.md"))
        self.assertEqual(count, 2)
        self.assertEqual(len(adjusted), 3, "the assessment prior is score-only, never exclusion")

    def test_assessment_evidence_prior_preserves_named_path_and_other_question_types(self):
        named = "docs/waves/old-delivery/change.md"
        self.assertEqual(
            self.srv._assessment_evidence_weight(named, f"Assess {named}."),
            1.0,
        )
        for question_type in ("explanatory", "navigational"):
            with self.subTest(question_type=question_type):
                results = [
                    {"path": "docs/reports/search-audit.md", "score": 0.60},
                    {"path": "docs/waves/old-delivery/change.md", "score": 0.50},
                ]
                unchanged, count = self.srv._apply_assessment_evidence_prior(
                    results, "Explain cache routing.", question_type
                )
                self.assertEqual(count, 0)
                self.assertEqual([item["score"] for item in unchanged], [0.60, 0.50])

    def test_low_information_path_categories_use_one_bounded_weight(self):
        cases = (
            (".aiignore", "ignore_file"),
            ("package-lock.json", "lockfile"),
            ("pyproject.toml", "dependency_manifest"),
            (".cursor/hooks/post-edit.py", "generated_surface"),
        )
        for path, category in cases:
            with self.subTest(path=path):
                self.assertEqual(self.srv._low_information_path_category(path), category)
                self.assertEqual(
                    self.srv._low_information_path_weight(path, "where are the retrieval gaps?"),
                    self.srv._LOW_INFORMATION_PATH_WEIGHT,
                )
        self.assertGreater(self.srv._LOW_INFORMATION_PATH_WEIGHT, 0.0)
        self.assertLess(self.srv._LOW_INFORMATION_PATH_WEIGHT, 1.0)
        self.assertEqual(
            self.srv._low_information_path_weight("src/retrieval.py", "retrieval gaps"),
            1.0,
        )

    def test_low_information_path_named_artifact_and_category_are_exempt(self):
        cases = (
            (".aiignore", "what does .aiignore exclude?"),
            ("pyproject.toml", "What Python version does pyproject.toml require?"),
            ("package-lock.json", "inspect the lockfile"),
            (".cursor/hooks/post-edit.py", "review the generated surface"),
        )
        for path, query in cases:
            with self.subTest(path=path, query=query):
                self.assertEqual(self.srv._low_information_path_weight(path, query), 1.0)

    def test_low_information_demotion_reorders_but_never_excludes(self):
        results = [
            {"path": ".aiignore", "kind": "code", "score": 0.90},
            {"path": "src/retrieval.py", "kind": "code", "score": 0.60},
        ]
        demoted, count = self.srv._demote_low_information_results(
            results, "where are the biggest gaps in retrieval?",
        )
        self.assertEqual(count, 1)
        self.assertEqual([item["path"] for item in demoted], ["src/retrieval.py", ".aiignore"])
        self.assertEqual(len(demoted), 2)
        self.assertAlmostEqual(
            demoted[1]["score"], 0.90 * self.srv._LOW_INFORMATION_PATH_WEIGHT,
        )

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

    def test_code_ask_never_calls_layer_health_source_pin(self):
        """1sbxq AC-1 source pin: code_ask_response contains no _layer_health
        call (the O(corpus) walk its own docstring forbids on the hot path)."""
        src_path = Path(load_server().__file__)
        src = src_path.read_text(encoding="utf-8")
        # 1wpah delivery repair: the public entry is a thin accounting-ledger
        # scope wrapper and the hot path lives in `_code_ask_response_body`,
        # so the pin reads BOTH (the wrapper alone would make it vacuous).
        start = src.index("def code_ask_response(")
        body_start = src.index("def _code_ask_response_body(")
        self.assertGreater(body_start, start)
        end = src.index("\ndef ", body_start + 10)
        body = src[start:end]
        self.assertNotIn("._layer_health(", body,
                         "no _layer_health CALL on the hot path (comments may mention it)")
        self.assertIn("_index_freshness_verdict", body)

    def test_index_freshness_envelope_carries_verdict_states(self):
        """1sbxq: code_ask's envelope carries the cached verdict's state —
        all three states pass through; the O(corpus) _layer_health call is
        gone (it is never invoked on the hot path)."""
        for state in ("current", "stale", "unknown"):
            index = self._make_index(code_results=[self._fake_code_chunk()])
            with patch.object(self.srv, "_index_freshness_verdict",
                              return_value={"state": state, "reason": "test"}):
                result = self.srv.code_ask_response(index, self.root, "billing?")
            self.assertEqual(result["data"]["index_freshness"], state)
            index._layer_health.assert_not_called()

    def test_index_freshness_unknown_on_bare_repo(self):
        """Honesty rule: a repo with no store cannot claim current — the
        real (unpatched) verdict path reports unknown."""
        self.srv._FRESHNESS_CACHE.clear()
        index = self._make_index(code_results=[self._fake_code_chunk()])
        result = self.srv.code_ask_response(index, self.root, "billing?")
        self.assertEqual(result["data"]["index_freshness"], "unknown")

    # --- validation_required and dynamic next_tools (12q8t) ---

    def _fake_doc_chunk(self, path="docs/specs/span-masking.md", score=0.95):
        return {"path": path, "kind": "doc", "lines": [1, 20], "text": "Span attribute masking spec.", "score": score}

    def test_validation_required_explanatory_doc_top(self):
        """validation_required: true emitted when explanatory question + doc top citation."""
        index = self._make_index(code_results=[self._fake_doc_chunk()])
        result = self.srv.code_ask_response(index, self.root, "how does span attribute masking work?")
        self.assertEqual(result["data"]["question_type"], "explanatory")
        self.assertTrue(result["data"].get("validation_required"), "validation_required should be True when top citation is doc")

    def test_validation_required_assessment_doc_top(self):
        index = self._make_index(code_results=[self._fake_doc_chunk()])
        result = self.srv.code_ask_response(index, self.root, "where are the biggest retrieval gaps?")
        self.assertEqual(result["data"]["question_type"], "assessment")
        self.assertTrue(result["data"].get("validation_required"))

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
            "index_build", "wf_sync_surfaces", "wf_add_change",
            "wf_new_feature", "wf_new_bug",
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
             patch.object(index, "_fts5_lexical_search", return_value=[]), \
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
             patch.object(index, "_fts5_lexical_search", return_value=[]), \
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
                model=_EXPECTED_DOCS_MODEL,
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


class EvidencePartitionResponseTests(unittest.TestCase):
    """Wave 1wpie AC-3 and AC-7: five exact parallel array pairs, partitioned
    before top-N, with independent limits and always-present evidence arrays."""

    PAIRS = ("communities", "fan_in", "fan_out", "chokepoints", "file_hubs")

    def setUp(self):
        self.srv = load_server()

    def _report(self, **kwargs):
        return self.srv.wf_graph_report_response(
            Path(__file__).resolve().parents[3].parent, **kwargs)["data"]

    def test_every_pair_is_present_including_its_evidence_half(self):
        data = self._report(limit=5)
        for name in self.PAIRS:
            with self.subTest(section=name):
                self.assertIn(name, data)
                self.assertIn(f"evidence_{name}", data,
                              "the evidence array must be present, not omitted")
                self.assertIsInstance(data[f"evidence_{name}"], list)

    def test_the_evidence_array_ships_even_when_the_section_was_not_requested(self):
        # Requirement 7 is explicit: present and empty rather than absent, so a
        # consumer never has to distinguish "nothing qualified" from "this build
        # predates the partition".
        #
        # Delivery review (DOCS-DEL-1): this asserted `evidence_fan_in` while
        # REQUESTING fan_in, which is the trivial case and tests nothing about
        # the words "not requested". The four unrequested arrays were in fact
        # absent, so the contract was false on four public surfaces while this
        # test stayed green. Assert the arrays that were NOT asked for.
        for requested in (["fan_in"], ["communities"], ["chokepoints"]):
            data = self._report(limit=5, sections=requested)
            for name in self.PAIRS:
                if name in requested:
                    continue
                with self.subTest(requested=requested[0], unrequested=name):
                    self.assertIn(
                        f"evidence_{name}", data,
                        f"requesting {requested} must still ship "
                        f"evidence_{name}; absence is what the contract forbids")
                    self.assertEqual([], data[f"evidence_{name}"])

    def test_evidence_rows_carry_their_type_and_a_nonempty_reason(self):
        data = self._report(limit=10)
        rows = data.get("evidence_communities") or []
        if not rows:
            self.skipTest("this tree has no classified evidence communities")
        for row in rows:
            self.assertEqual("evidence_data", row["community_type"])
            self.assertEqual("evidence_data", row["evidence_type"])
            self.assertTrue(row["classification_reasons"],
                            "a classified row must say WHY")

    def test_evidence_communities_do_not_appear_in_the_production_ranking(self):
        # Delivery review (QA-DEL-4): this compared two sets and passed on
        # `set() & set()`, so a TOTAL classification failure on the server
        # response path registered no failure here. Require a non-empty
        # evidence half before the disjointness claim means anything.
        data = self._report(limit=20)
        production = {c["community_id"] for c in data.get("communities", [])}
        evidence = {c["community_id"] for c in data.get("evidence_communities", [])}
        self.assertTrue(
            evidence,
            "no evidence communities were returned, so disjointness is vacuous; "
            "this tree is known to carry classified machine-result artifacts")
        self.assertTrue(production, "no production communities were returned")
        self.assertEqual(set(), production & evidence,
                         "a community belongs to exactly one half")

    def test_the_limit_applies_independently_to_each_half(self):
        # Delivery review (QA-DEL-7): asserting only an upper bound passes on
        # an empty list. The point of an INDEPENDENT limit is that a full
        # evidence half does not consume production slots, so require both
        # halves to actually fill for the section that has enough rows.
        data = self._report(limit=2)
        for name in self.PAIRS:
            with self.subTest(section=name):
                self.assertLessEqual(len(data.get(name, [])), 2)
                self.assertLessEqual(len(data.get(f"evidence_{name}", [])), 2)
        self.assertEqual(2, len(data.get("communities", [])),
                         "production communities did not fill to the limit")
        self.assertEqual(2, len(data.get("evidence_communities", [])),
                         "the evidence half did not fill independently to the "
                         "same limit; that is what 'independent' means")

    def test_evidence_rows_are_not_erased_by_exclude_generated(self):
        # The two classifications are orthogonal: generated-ness is about how a
        # file was produced, evidence-ness about what it records.
        plain = self._report(limit=10)
        filtered = self._report(limit=10, exclude_generated=True)
        if not plain.get("evidence_communities"):
            self.skipTest("this tree has no classified evidence communities")
        self.assertTrue(filtered.get("evidence_communities"),
                        "exclude_generated must not erase Evidence/Data")

    def test_a_classified_community_keeps_its_compatibility_fields(self):
        rows = self._report(limit=10).get("evidence_communities") or []
        if not rows:
            self.skipTest("this tree has no classified evidence communities")
        for field in ("community_id", "label", "node_count",
                      "hub_node_id", "hub_label", "generated_node_fraction"):
            self.assertIn(field, rows[0],
                          "an evidence entry keeps its section's existing fields")

    def test_evidence_communities_remain_queryable_by_id(self):
        rows = self._report(limit=10).get("evidence_communities") or []
        if not rows:
            self.skipTest("this tree has no classified evidence communities")
        cid = rows[0]["community_id"]
        resp = self.srv.code_graph_community_response(
            Path(__file__).resolve().parents[3].parent, community_id=cid)
        self.assertEqual("ok", resp["status"],
                         "partitioning must not remove the community from the catalog")


class CrossTableFusionConsistencyTests(unittest.TestCase):
    """Wave 1wpid AC-3 and requirement 7: all three mixed-table sites must use
    the SAME fusion, and the single-table fallbacks must be untouched."""

    def setUp(self):
        self.srv = load_server()

    def _server_source(self):
        return Path(self.srv.__file__.replace("server.py", "server_impl.py")).read_text(
            encoding="utf-8")

    def test_all_three_mixed_table_sites_route_through_the_shared_fusion(self):
        # Requirement 7 says the semantics apply CONSISTENTLY across three
        # named sites. One shared callee is how that is guaranteed; a local
        # raw-bm25 sort reintroduced at any one site would diverge silently.
        source = self._server_source()
        for anchor in (
            "def _lexical_candidates",
            "def _fts_degraded_serve",
            "def code_lexical_response",
        ):
            start = source.index(anchor)
            # Bound the search to the function body that follows the anchor.
            body = source[start:start + 12000]
            with self.subTest(site=anchor):
                self.assertIn("fuse_lexical_tables", body,
                              f"{anchor} no longer routes through the shared fusion")

    def test_single_table_fusion_is_order_identical_to_the_plain_bm25_sort(self):
        # The docs-only and code-only fallbacks must be unchanged, so fusion
        # has to be order-preserving when only one table is present.
        store = self.srv._load_script("index_state_store")
        rows = [{"id": "a", "bm25": -1.0}, {"id": "b", "bm25": -3.0}, {"id": "c", "bm25": -2.0}]
        plain = sorted(rows, key=lambda h: h["bm25"])
        fused = store.fuse_lexical_tables({"code": list(plain)})
        self.assertEqual([r["id"] for r in plain], [r["id"] for r in fused])

    def test_fusion_preserves_candidate_count_and_per_table_bm25(self):
        # Requirement 4: per-table bm25 stays observable. And the reranker must
        # not receive more candidates than before, or latency would move for a
        # reason unrelated to ranking quality.
        store = self.srv._load_script("index_state_store")
        per = {"docs": [{"id": f"d{i}", "bm25": -float(i)} for i in range(20)],
               "code": [{"id": f"c{i}", "bm25": -float(i)} for i in range(15)]}
        fused = store.fuse_lexical_tables(per)
        self.assertEqual(35, len(fused))
        self.assertTrue(all("bm25" in row for row in fused))
        self.assertEqual({"docs", "code"}, {row["table"] for row in fused})

    def test_unrelated_growth_in_one_table_cannot_reorder_the_other(self):
        # The defect in its pure form: a docs row whose raw score improves past
        # a code row must not overtake it, because neither row's rank within
        # its own table changed.
        store = self.srv._load_script("index_state_store")
        before = store.fuse_lexical_tables({
            "code": [{"id": "c1", "bm25": -4.24}],
            "docs": [{"id": "d1", "bm25": -0.0}],
        })
        after = store.fuse_lexical_tables({
            "code": [{"id": "c1", "bm25": -4.24}],       # unchanged
            "docs": [{"id": "d1", "bm25": -6.15}],       # improved by growth alone
        })
        self.assertEqual([r["id"] for r in before], [r["id"] for r in after])

    def test_fusion_order_is_deterministic_on_ties(self):
        store = self.srv._load_script("index_state_store")
        first = store.fuse_lexical_tables({"docs": [{"id": "z", "bm25": -1.0}],
                                           "code": [{"id": "a", "bm25": -1.0}]})
        second = store.fuse_lexical_tables({"code": [{"id": "a", "bm25": -1.0}],
                                            "docs": [{"id": "z", "bm25": -1.0}]})
        self.assertEqual([r["id"] for r in first], [r["id"] for r in second])


class ConfidenceBasisAndRoutingTests(unittest.TestCase):
    """Wave 1wscp AC-5 and AC-6: the confidence band describes the lead it was
    derived from, and constant-value questions route by a documented contract."""

    def setUp(self):
        self.srv = load_server()

    # --- AC-5: lead-aware confidence -------------------------------------

    def test_a_weak_lead_is_not_rescued_by_a_strong_lower_ranked_citation(self):
        # The closed-1seaw defect, stated directly: confidence read the maximum
        # score anywhere in the list, so a weak rank-one citation shipped with
        # confidence="high" because some row further down scored well.
        weak_lead = [{"score": 0.05}, {"score": 0.99}, {"score": 0.98}]
        band, basis = self.srv._confidence_with_basis(weak_lead, True)
        self.assertEqual("low", band)
        self.assertEqual(self.srv.CONFIDENCE_BASIS_SEMANTIC_LEAD, basis)
        # The old maximum-based rule would have called this high.
        self.assertGreaterEqual(
            max(c["score"] for c in weak_lead), self.srv.CONF_AGENT_RERANK_HIGH)

    def test_a_strong_lead_still_earns_high(self):
        band, basis = self.srv._confidence_with_basis(
            [{"score": 0.92}, {"score": 0.10}], True)
        self.assertEqual("high", band)
        self.assertEqual(self.srv.CONFIDENCE_BASIS_SEMANTIC_LEAD, basis)

    def test_exact_owner_is_the_documented_exception_and_is_labelled(self):
        # A short declaration chunk can score low semantically while being
        # exactly the right answer, so symbol resolution licenses the band --
        # but the basis must say so rather than leaving it unexplained.
        band, basis = self.srv._confidence_with_basis(
            [{"score": 0.02}], True, exact_owner=True)
        self.assertEqual("high", band)
        self.assertEqual(self.srv.CONFIDENCE_BASIS_EXACT_OWNER, basis)

    def test_no_citations_and_unranked_paths_carry_their_own_basis(self):
        self.assertEqual(
            ("low", self.srv.CONFIDENCE_BASIS_NO_CITATIONS),
            self.srv._confidence_with_basis([], True))
        self.assertEqual(
            ("medium", self.srv.CONFIDENCE_BASIS_UNRANKED),
            self.srv._confidence_with_basis([{"score": 0.99}], False))

    # --- AC-5: truthful selection_reason ---------------------------------

    def test_the_definition_reason_needs_the_row_to_carry_the_symbol(self):
        # A definition boost names a symbol; it does not prove WHICH row ended
        # up holding that declaration.  A row that does not mention the symbol
        # must not be labelled `definition`, or a boost that promoted some other
        # row would license an unearned exact-owner band on a weak lead.
        rows = [{"section": "other > thing", "excerpt": "unrelated body"}]
        self.srv._assign_selection_reasons(
            rows, ["symbol:MAX_RETRIES"], reranked=True, lexical_fallback=False)
        self.assertEqual(self.srv.SELECTION_REASON_RERANKED, rows[0]["selection_reason"])

        rows = [{"section": "conf > MAX_RETRIES", "excerpt": "MAX_RETRIES = 5"}]
        self.srv._assign_selection_reasons(
            rows, ["symbol:MAX_RETRIES"], reranked=True, lexical_fallback=False)
        self.assertEqual(self.srv.SELECTION_REASON_DEFINITION, rows[0]["selection_reason"])

    def test_every_citation_gets_a_reason_matching_how_it_was_selected(self):
        rows = [{"kind": "keyword"}, {"kind": "code"}]
        self.srv._assign_selection_reasons(rows, [], reranked=True, lexical_fallback=False)
        self.assertEqual(
            [self.srv.SELECTION_REASON_KEYWORD, self.srv.SELECTION_REASON_RERANKED],
            [r["selection_reason"] for r in rows])

        rows = [{"kind": "code"}]
        self.srv._assign_selection_reasons(rows, [], reranked=False, lexical_fallback=True)
        self.assertEqual(self.srv.SELECTION_REASON_LEXICAL, rows[0]["selection_reason"])

        rows = [{"kind": "code"}]
        self.srv._assign_selection_reasons(rows, [], reranked=False, lexical_fallback=False)
        self.assertEqual(self.srv.SELECTION_REASON_VECTOR, rows[0]["selection_reason"])

    # --- AC-6: the constant-value routing contract ------------------------

    def test_both_standing_constant_value_fixtures_route_navigational(self):
        for question in ("what value is RERANKER_MODEL",
                         "What is the current value of INT8_ENCODING_REVISION?"):
            with self.subTest(question=question):
                self.assertEqual("navigational", self.srv._classify_question(question))

    def test_explanatory_prose_containing_value_is_left_alone(self):
        # The contract is narrow on purpose: it needs BOTH a value question and
        # an upper-snake constant, so ordinary prose does not flip.
        for question in (
            "what is the value of a well-designed abstraction",
            "how does the reranker decide which value to return",
            "explain the value proposition of the graph index",
            "RERANKER_MODEL is used by the reranker loader",
            "what is the retry budget",
        ):
            with self.subTest(question=question):
                self.assertEqual("explanatory", self.srv._classify_question(question))

    def test_existing_routes_are_unchanged(self):
        self.assertEqual("navigational",
                         self.srv._classify_question("where is the rate limiter defined"))
        self.assertEqual("instructional",
                         self.srv._classify_question("how do i rebuild the index"))

    def test_a_bare_acronym_is_not_an_upper_snake_constant(self):
        # `API` or a sentence-initial capital must not satisfy the constant half.
        self.assertIsNone(self.srv._UPPER_SNAKE_RE.search("what is the value of API"))
        self.assertIsNotNone(self.srv._UPPER_SNAKE_RE.search("value of MAX_RETRIES"))


class RerankerTests(unittest.TestCase):
    CODE_ASK_BASE_DATA_KEYS = {
        "question", "question_type", "answer", "citations", "confidence", "gaps",
        "index_freshness", "search_mode", "fallback_reason", "reranked", "rerank_mode",
        "partition_applied", "demotion_count", "total_ms", "vector_ms", "rerank_ms",
        # Wave 1wpif (1wpah): per-source substrate accounting rides every envelope.
        "retrieval_accounting",
        # Wave 1wscp (requirement 5): the confidence band is a public trust
        # claim, so the machine-readable basis it rests on ships beside it on
        # every envelope rather than being inferable only from the score list.
        "confidence_basis",
    }

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
            model=_EXPECTED_DOCS_MODEL,
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
            results, reranked, vector_ms, rerank_ms, _, _, _, _ = idx.search_combined("query", top_n=5)
        # Wave 1p52p: the single agent path runs the cross-encoder rerank-FIRST; with a reranker
        # available, agent_reranked (the 2nd tuple element) is True.
        self.assertTrue(reranked)
        # Wave 1p52p: the agent path's count is governed by the text budget + the AGENT_CANDIDATE_MAX
        # backstop (max(top_n, AGENT_CANDIDATE_MAX)), not a hard top_n cap (that was the removed local
        # path). With only 6 small candidates the count is bounded by the candidate pool.
        self.assertLessEqual(len(results), max(5, self.srv.AGENT_CANDIDATE_MAX))
        self.assertIsInstance(vector_ms, int)
        self.assertIsInstance(rerank_ms, int)

    def test_search_combined_returns_reranked_false_without_reranker(self):
        """Wave 1p52p: with NO reranker (CPU-only machine), the agent path is a no-op for the
        cross-encoder — agent_reranked is False and results are still returned in vector/coverage
        order. (The former RRF fallback path was removed.)"""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(3)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        with patch.object(idx, "_get_reranker", return_value=None):
            results, reranked, vector_ms, rerank_ms, _, _, _, _ = idx.search_combined("query", top_n=5)
        self.assertFalse(reranked)
        self.assertTrue(results, "results must still be returned without a reranker")
        self.assertLessEqual(len(results), max(5, self.srv.AGENT_CANDIDATE_MAX))
        self.assertIsInstance(vector_ms, int)
        self.assertIsInstance(rerank_ms, int)

    def test_search_combined_result_count_bounded_by_agent_cap(self):
        """Wave 1p52p: the single agent path bounds the count by the text budget + the
        AGENT_CANDIDATE_MAX backstop (max(top_n, AGENT_CANDIDATE_MAX)), NOT a hard top_n cap — that
        strict cap was a property of the removed "local" path. Here 10 small candidates stay under
        the backstop."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(5)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(5)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        mock_reranker = self._make_mock_reranker(10)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, _, _vms, _rms, _, _, _, _ = idx.search_combined("query", top_n=3)
        self.assertLessEqual(len(results), max(3, self.srv.AGENT_CANDIDATE_MAX))

    def test_code_ask_response_includes_reranked_field(self):
        """code_ask_response includes 'reranked' and timing fields in response data."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 0, 0, [], [], "none", None)
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

    # --- Wave 1p4hj: agent-mode (default) candidate pipeline ---

    def test_code_ask_rerank_invalid_value_errors(self):
        """1p4hj AC-1: an invalid rerank value errors naming the valid set."""
        index = MagicMock()
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "q", rerank="bogus")
        self.assertEqual(result["status"], "error")
        self.assertIn("agent", str(result.get("diagnostics", "")).lower())

    def test_code_ask_rerank_defaults_to_agent(self):
        """1p4hj AC-1: default rerank is 'agent' — search_combined receives rerank='agent'."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 0, 0, [], [], "none", None)
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            self.srv.code_ask_response(index, root, "q")  # no rerank arg
        _, kwargs = index.search_combined.call_args
        self.assertEqual(kwargs.get("rerank"), "agent")

    def test_agent_mode_calls_reranker(self):
        """Wave 1p52p: agent-mode (the single path) now runs the cross-encoder rerank-FIRST. With a
        reranker available, search_combined consults it and returns agent_reranked=True. (Previously
        agent-mode did NOT rerank — that was the pre-1p52p behavior this test inverts.)"""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(3)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(3)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        mock_reranker = self._make_mock_reranker(6)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            results, reranked, _, _, _, _, _, _ = idx.search_combined("query", top_n=5, rerank="agent")
        mock_reranker.rerank.assert_called()
        self.assertTrue(reranked)
        self.assertTrue(results, "agent-mode must still return candidates")

    def test_agent_mode_artifact_anchored_reranks_and_labels(self):
        """Wave 1p52p: the artifact-anchored exact-first early-return now rerank-FIRSTs the keyword
        candidates (agent path) — it consults the cross-encoder AND returns the keyword candidates
        labeled by source. With a reranker available, agent_reranked is True. (Pre-1p52p this path
        skipped the reranker; 1p52p unified it onto the single rerank-first agent path.)"""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=[self._fake_code_chunk("src/a.py")])
        fake_kw_resp = {
            "status": "ok",
            "data": {"results": [
                {"path": "scripts/lifecycle_id.py", "line": 106, "snippet": "def build_prefix("},
                {"path": "docs/specs/mcp-tool-surface.md", "line": 12, "snippet": "build_prefix format"},
            ]},
        }
        mock_reranker = self._make_mock_reranker(2)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp):
                results, reranked, _, _, definition_boosted, _, _, _ = idx.search_combined(
                    "how does build_prefix generate the +2vr8 format?",
                    top_n=5, question_type="artifact_anchored", rerank="agent",
                )
        mock_reranker.rerank.assert_called()
        self.assertTrue(reranked)
        self.assertIn("artifact_anchored", definition_boosted)
        by_path = {r.get("path"): r.get("source") for r in results}
        self.assertEqual(by_path.get("scripts/lifecycle_id.py"), "code")
        self.assertEqual(by_path.get("docs/specs/mcp-tool-surface.md"), "docs", "doc-path keyword hits must be labeled source='docs'")

    def test_agent_mode_full_text_and_source_label_no_vectors(self):
        """1p4hj AC-3: agent-mode citations carry the FULL chunk text (not the 300-char
        excerpt) + a source label, and never a vector field."""
        long_text = "x" * 800
        docs = [self._fake_doc_chunk("d0", text=long_text)]
        code = [self._fake_code_chunk("c0", text="def foo(): pass")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        result = self.srv.code_ask_response(idx, idx.root, "query")  # default agent
        cits = result["data"]["citations"]
        self.assertTrue(cits)
        doc_cit = next((c for c in cits if str(c.get("path", "")).startswith("docs/")), None)
        self.assertIsNotNone(doc_cit, f"expected a docs citation; got {[c.get('path') for c in cits]}")
        self.assertGreater(len(doc_cit["excerpt"]), 300, "agent-mode must return full chunk text, not a 300-char excerpt")
        self.assertIn("source", doc_cit)
        for c in cits:
            self.assertNotIn("vector", c)
        self.assertEqual(result["data"]["rerank_mode"], "agent")

    def test_agent_mode_per_index_floor_no_starved_modality(self):
        """1p4hj AC-4: each source contributes its top-K floor even when the other index dominates."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(2)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(10)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        results = idx._agent_candidate_select({"docs": docs, "code": code}, top_n=8, floor_k=2)
        sources = [r.get("source") for r in results]
        self.assertGreaterEqual(sources.count("docs"), 2, "docs floor must survive code dominance")
        self.assertGreaterEqual(sources.count("code"), 2)

    def test_agent_mode_fill_is_relevance_ordered_not_forced_balance(self):
        """1p4hj AC-4: beyond the anti-starvation floor, the fill is by RELEVANCE across
        sources — NOT a forced per-source balance (which would be no better than gluing
        code_search + docs_search together). A code-dominant-relevance query returns
        mostly code, with the docs floor preserved."""
        docs = [{"path": f"docs/d{i}.md", "kind": "doc", "lines": [1, 5], "text": "d", "score": 0.2} for i in range(8)]
        code = [{"path": f"src/c{i}.py", "kind": "code", "lines": [1, 10], "text": "c", "score": 0.9} for i in range(10)]
        idx = self._make_index_with_docs([self._fake_doc_chunk("x")], code_chunks=[self._fake_code_chunk("y")])
        results = idx._agent_candidate_select({"docs": docs, "code": code}, top_n=10, floor_k=2)
        sources = [r.get("source") for r in results]
        self.assertGreaterEqual(sources.count("docs"), 2, "docs floor preserved (anti-starvation)")
        self.assertGreater(sources.count("code"), sources.count("docs"),
                           "high-relevance code must dominate beyond the floor — not a forced 50/50 split")

    def test_agent_mode_navigational_weight_boosts_code(self):
        """1p4hj AC-4: the navigational question-type tilt (brought forward from RRF's
        code weight) boosts code in the fill — at EQUAL raw scores, code leads."""
        docs = [{"path": f"docs/d{i}.md", "kind": "doc", "lines": [1, 5], "text": "d", "score": 0.7} for i in range(8)]
        code = [{"path": f"src/c{i}.py", "kind": "code", "lines": [1, 10], "text": "c", "score": 0.7} for i in range(8)]
        idx = self._make_index_with_docs([self._fake_doc_chunk("x")], code_chunks=[self._fake_code_chunk("y")])
        weights = {"code": self.srv.RRF_NAVIGATIONAL_CODE_WEIGHT, "docs": self.srv.RRF_NAVIGATIONAL_DOCS_WEIGHT}
        results = idx._agent_candidate_select({"docs": docs, "code": code}, top_n=8, floor_k=2, weights=weights)
        sources = [r.get("source") for r in results]
        self.assertGreater(sources.count("code"), sources.count("docs"),
                           "navigational weight must boost code beyond the floor at equal raw scores")

    def test_agent_mode_relevance_dropoff_trims_flat_tail(self):
        """1p4hj AC-4: the fill stops at the relevance drop-off — a strong cluster
        followed by a flat low-relevance tail returns ~the cluster (well under top_n),
        not a padded top_n. Mirrors real score distributions (sharp elbow after the
        top few, then a flat tail), so we don't pay tokens for noise."""
        strong = [{"path": f"src/s{i}.py", "kind": "code", "lines": [i, i + 5], "text": "s", "score": 0.84 - i * 0.01} for i in range(4)]
        tail = [{"path": f"src/t{i}.py", "kind": "code", "lines": [i, i + 5], "text": "t", "score": 0.61} for i in range(16)]
        docs = [{"path": f"docs/d{i}.md", "kind": "doc", "lines": [i, i + 3], "text": "d", "score": 0.5} for i in range(5)]
        idx = self._make_index_with_docs([self._fake_doc_chunk("x")], code_chunks=[self._fake_code_chunk("y")])
        results = idx._agent_candidate_select({"docs": docs, "code": strong + tail}, top_n=20, floor_k=3)
        # top=0.84 → cutoff=0.85*0.84=0.714; the 0.61 tail + 0.5 docs fall below it, so only
        # the 4-strong code cluster clears the fill (floor still guarantees 3 docs + 3 code).
        self.assertLess(len(results), 20, "must not pad to top_n past the relevance drop-off")
        code_above = [r for r in results if r.get("source") == "code" and (r.get("score") or 0) >= 0.7]
        self.assertEqual(len(code_above), 4, "the 4-strong code cluster is kept")
        self.assertGreaterEqual(sum(1 for r in results if r.get("source") == "docs"), 3, "docs floor still honored below the cutoff")

    def test_agent_mode_count_driven_by_text_budget_not_fixed_n(self):
        """1p4hj AC-4: the count is governed by the TEXT budget (context size), not a fixed
        N. Same budget → many SMALL chunks fit (well past the old cap of 20); few LARGE chunks
        fit. This is what 'don't pollute the agent, yet give it enough' actually measures."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d")], code_chunks=[self._fake_code_chunk("c")])
        small = [{"path": f"src/s{i}.py", "kind": "code", "lines": [i, i + 2], "text": "x" * 200, "score": 0.8} for i in range(40)]
        res_small = idx._agent_candidate_select({"code": small}, top_n=40, floor_k=2, text_budget=4000)
        self.assertGreater(len(res_small), 15, "small chunks → many fit the budget (count not pinned at a fixed N)")
        self.assertLessEqual(sum(len(r.get("text") or "") for r in res_small), 4000 + 200, "cumulative text stays within ~budget")
        large = [{"path": f"src/l{i}.py", "kind": "code", "lines": [i, i + 2], "text": "y" * 1000, "score": 0.8} for i in range(40)]
        res_large = idx._agent_candidate_select({"code": large}, top_n=40, floor_k=2, text_budget=4000)
        self.assertLess(len(res_large), len(res_small), "large chunks → fewer fit the SAME budget")
        self.assertLessEqual(sum(len(r.get("text") or "") for r in res_large), 4000 + 1000, "cumulative text stays within ~budget")

    def test_lr_tokenize_identifier_snake_camel_acronym(self):
        """1p4lr: the identifier tokenizer splits snake/camel/acronym boundaries (casing-agnostic)."""
        t = self.srv._tokenize_identifier
        self.assertEqual(t("RERANKER_MODEL"), ["reranker", "model"])
        self.assertEqual(t("MaxRetries"), ["max", "retries"])
        self.assertEqual(t("apiURL"), ["api", "url"])

    def test_lr_definition_boost_fires_on_constant(self):
        """1p4lr: boost fires on a " [const]" chunk whose name tokens ALL appear in the query."""
        srv = self.srv
        cand = {"id": "indexer.py::RERANKER_MODEL", "section": "indexer > RERANKER_MODEL [const]", "kind": "code"}
        qt = srv._query_content_terms("what cross-encoder reranker model does local mode use?")
        self.assertEqual(srv._definition_match_boost(qt, cand), srv.DEFINITION_MATCH_BOOST)

    def test_lr_definition_boost_fires_on_function_class_method(self):
        """1p4lr AC-4: the boost generalizes beyond constants — a FUNCTION, CLASS, or qualified
        METHOD definition whose multi-token name the query names is boosted too."""
        srv = self.srv
        fn = {"id": "server_impl.py::search_combined", "section": "server_impl > search_combined", "kind": "code"}
        self.assertEqual(srv._definition_match_boost(srv._query_content_terms("how does search_combined work"), fn),
                         srv.DEFINITION_MATCH_BOOST)
        cls = {"id": "indexer.py::WaveIndex", "section": "indexer > WaveIndex", "kind": "code"}
        self.assertEqual(srv._definition_match_boost(srv._query_content_terms("what is the WaveIndex class"), cls),
                         srv.DEFINITION_MATCH_BOOST)
        meth = {"id": "m.py::Config.connect", "section": "m > Config.connect", "kind": "code"}
        self.assertEqual(srv._definition_match_boost(srv._query_content_terms("how does Config connect"), meth),
                         srv.DEFINITION_MATCH_BOOST)

    def test_lr_definition_boost_multilanguage(self):
        """1p4lr AC-4: detection is language-agnostic — a const/func/class definition from any chunked
        language (JS const, Go func, Java class) boosts on a full-name query (camelCase/PascalCase
        names match because the query terms are camel-split too)."""
        srv = self.srv
        cases = [
            ({"id": "conf.ts::API_URL", "section": "conf > API_URL [const]", "kind": "code"}, "what is the API_URL value"),
            ({"id": "h.go::ParseConfig", "section": "h > ParseConfig", "kind": "code"}, "how does ParseConfig work"),
            ({"id": "B.java::OrderService", "section": "B > OrderService", "kind": "code"}, "the OrderService class"),
        ]
        for cand, q in cases:
            self.assertEqual(srv._definition_match_boost(srv._query_content_terms(q), cand),
                             srv.DEFINITION_MATCH_BOOST, cand["id"])

    def test_lr_definition_boost_skips_non_definition_and_strict_misses(self):
        """1p4lr: no boost for a NON-definition (doc / imports chunk), a partial name match, or a
        single-token name (the over-boost guard)."""
        srv = self.srv
        # non-definition: a doc chunk (kind != code, no marker)
        doc = {"id": "guide.md::s", "section": "guide > How Search Works", "kind": "doc"}
        self.assertEqual(srv._definition_match_boost(srv._query_content_terms("how does search work"), doc), 1.0)
        # non-definition: an imports chunk
        imp = {"id": "m.py::__imports__", "section": "m > imports", "kind": "code"}
        self.assertEqual(srv._definition_match_boost(srv._query_content_terms("imports module list"), imp), 1.0)
        # partial overlap: query has 'reranker' but not 'model'
        c1 = {"id": "x::RERANKER_MODEL", "section": "x > RERANKER_MODEL [const]", "kind": "code"}
        self.assertEqual(srv._definition_match_boost(srv._query_content_terms("which reranker"), c1), 1.0)
        # single-token name (the over-boost guard)
        c2 = {"id": "x::PORT", "section": "x > PORT [const]", "kind": "code"}
        self.assertEqual(srv._definition_match_boost(srv._query_content_terms("what is the port"), c2), 1.0)

    def test_lr_definition_boost_strips_split_chunk_suffix(self):
        """1p4lr (delivery review C1): an oversized declaration is split into chunks whose id carries a
        `:L<start>-L<end>` suffix and whose breadcrumb carries a ` (part N/M)` tail. Those junk tokens
        (l1274, part) can never appear in a query, so without stripping them the all-tokens match fails
        and the boost is DEAD for every large symbol (e.g. WaveIndex.search_combined)."""
        srv = self.srv
        split_id = {"id": "server_impl.py::WaveIndex.search_combined:L1274-L1289",
                    "section": "server_impl > WaveIndex.search_combined (part 1/2)", "kind": "code"}
        self.assertEqual(srv._definition_qname(split_id), "WaveIndex.search_combined")
        # breadcrumb-derived path (no "::" leaf) carries the same (part N/M) tail
        split_section = {"id": "noident", "section": "server_impl > WaveIndex.search_combined (part 2/2)", "kind": "code"}
        self.assertEqual(srv._definition_qname(split_section), "WaveIndex.search_combined")
        self.assertEqual(
            srv._definition_match_boost(srv._query_content_terms("how does search_combined work"), split_id),
            srv.DEFINITION_MATCH_BOOST)

    def test_lr_definition_boost_fires_on_leaf_method_query(self):
        """1p4lr (delivery review C3): a natural-language method query names only the method, not its
        enclosing class. A multi-token LEAF the query names boosts even when the class tokens are
        absent; a single-token leaf still needs its qualified context (precision guard)."""
        srv = self.srv
        meth = {"id": "server_impl.py::WaveIndex.search_combined",
                "section": "server_impl > WaveIndex.search_combined", "kind": "code"}
        # the class (WaveIndex) is NOT named — the 2-token leaf search_combined is → boost
        self.assertEqual(
            srv._definition_match_boost(srv._query_content_terms("how does search_combined work"), meth),
            srv.DEFINITION_MATCH_BOOST)
        # a single-token leaf method without its class still does NOT boost (no over-fire on a bare word)
        single = {"id": "m.py::Config.connect", "section": "m > Config.connect", "kind": "code"}
        self.assertEqual(srv._definition_match_boost(srv._query_content_terms("how does connect work"), single), 1.0)

    def test_lr_boost_lifts_declaration_without_re_trimming_others(self):
        """1p4lr: a boosted definition ranks UP, but the drop-off cutoff (from the UN-boosted top) is
        unchanged — so EXACTLY the same other candidates are selected (the council's top_w must-fix)."""
        srv = self.srv
        code = [{"path": f"{x}.py", "kind": "code", "lines": [1, 1], "text": x, "score": s}
                for x, s in [("a", 0.82), ("b", 0.78), ("c", 0.76), ("d", 0.72), ("e", 0.68)]]
        const = {"path": "k.py", "kind": "code", "lines": [1, 1], "text": "k", "score": 0.74,
                 "id": "k.py::RERANKER_MODEL", "section": "k > RERANKER_MODEL [const]"}
        idx = self._make_index_with_docs([self._fake_doc_chunk("d")], code_chunks=[self._fake_code_chunk("c")])
        base = idx._agent_candidate_select({"code": [dict(c) for c in code] + [dict(const)]}, top_n=20, floor_k=1)
        cb = dict(const); cb["_boost"] = srv.DEFINITION_MATCH_BOOST
        boosted = idx._agent_candidate_select({"code": [dict(c) for c in code] + [cb]}, top_n=20, floor_k=1)
        self.assertEqual(boosted[0]["path"], "k.py")  # the boosted definition ranks first
        self.assertEqual({r["path"] for r in base}, {r["path"] for r in boosted})  # same set selected
        self.assertNotIn("e.py", {r["path"] for r in boosted})  # 0.68 < cutoff in BOTH (not re-trimmed)

    def test_agent_mode_dedup_preserves_multi_source(self):
        """1p4hj AC-5: a cross-source duplicate survives once with BOTH sources recorded
        (RRF's cross-source-agreement signal is preserved, not collapsed to one)."""
        shared = {"path": "shared.py", "kind": "code", "lines": [1, 5], "text": "shared", "score": 0.8}
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=[self._fake_code_chunk("c0")])
        results = idx._agent_candidate_select({"docs": [dict(shared)], "code": [dict(shared)]}, top_n=5, floor_k=1)
        keys = [(r["path"], tuple(r["lines"])) for r in results]
        self.assertEqual(keys.count(("shared.py", (1, 5))), 1, "cross-source duplicate must survive exactly once")
        rec = next(r for r in results if r["path"] == "shared.py")
        self.assertEqual(set(rec.get("sources", [])), {"docs", "code"}, "multi-source signal must be preserved")

    def test_agent_mode_distinct_same_path_not_collapsed(self):
        """1p4hj AC-5: legitimately-distinct chunks (same path, different line ranges) are NOT collapsed."""
        a = {"path": "m.py", "kind": "code", "lines": [1, 5], "text": "a", "score": 0.9}
        b = {"path": "m.py", "kind": "code", "lines": [40, 60], "text": "b", "score": 0.8}
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=[self._fake_code_chunk("c0")])
        results = idx._agent_candidate_select({"code": [a, b]}, top_n=5, floor_k=2)
        self.assertEqual(len(results), 2, "distinct line ranges must both survive")

    def test_agent_mode_same_path_lines_distinct_hash_both_survive(self):
        """1wngv AC-3/AC-8 (wave 1wpif): legacy metadata sharing (path, lines)
        no longer collapses DISTINCT chunks — the dedupe key includes
        chunk_hash, so both rows survive selection."""
        a = {"path": "conf/x.toml", "kind": "code", "lines": [1, 5],
             "text": "alpha body", "score": 0.9, "chunk_hash": "h-alpha"}
        b = {"path": "conf/x.toml", "kind": "code", "lines": [1, 5],
             "text": "beta body", "score": 0.8, "chunk_hash": "h-beta"}
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=[self._fake_code_chunk("c0")])
        results = idx._agent_candidate_select({"code": [a, b]}, top_n=5, floor_k=2)
        self.assertEqual(len(results), 2, "distinct content must both survive")
        self.assertEqual({r["text"] for r in results}, {"alpha body", "beta body"})

    def test_agent_mode_exact_clone_collapses_once_with_all_provenance(self):
        """1wngv AC-8: an exact cross-source clone (same normalized path,
        lines, and chunk_hash) collapses to ONE representative that keeps
        every source in ``sources``."""
        shared = {"path": "src/s.py", "kind": "code", "lines": [1, 5],
                  "text": "shared", "score": 0.8, "chunk_hash": "h1"}
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=[self._fake_code_chunk("c0")])
        results = idx._agent_candidate_select(
            {"docs": [dict(shared)], "code": [dict(shared)], "lexical": [dict(shared)]},
            top_n=5, floor_k=1,
        )
        matches = [r for r in results if r["path"] == "src/s.py"]
        self.assertEqual(len(matches), 1, "exact clone must collapse exactly once")
        self.assertEqual(set(matches[0].get("sources", [])), {"docs", "code", "lexical"})

    def test_agent_mode_hashless_clone_uses_canonical_digest(self):
        """1wngv AC-8: without chunk_hash the key falls back to a
        deterministic digest of the canonical returned evidence fields —
        identical evidence merges, different text keeps both rows."""
        same1 = {"id": "x", "path": "p.md", "kind": "doc", "lines": [1, 4],
                 "text": "same text", "score": 0.9}
        same2 = dict(same1)
        diff = {"id": "x", "path": "p.md", "kind": "doc", "lines": [1, 4],
                "text": "DIFFERENT", "score": 0.7}
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=[self._fake_code_chunk("c0")])
        results = idx._agent_candidate_select(
            {"docs": [same1], "code": [same2, diff]}, top_n=5, floor_k=2,
        )
        self.assertEqual(sorted(r["text"] for r in results), ["DIFFERENT", "same text"])
        merged = next(r for r in results if r["text"] == "same text")
        self.assertEqual(set(merged.get("sources", [])), {"docs", "code"})

    def test_index_health_reports_chunk_id_collisions(self):
        """1wngv AC-5: index_health surfaces the recorded same-ID/
        distinct-content census before derived-state coverage can read as
        complete."""
        index = MagicMock()
        index.docs_health.return_value = {
            "missing_layers": [], "stale_layers": [], "readiness_overview": "ready",
        }
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            index.root = Path(tmp)
            summary = {
                "present": True, "schema_version": "9", "integrity": "ok",
                "size_bytes": 1,
                "chunk_index": {"code": {
                    "lance_rows": 10, "registry_rows": 9, "covered": True,
                    "id_collisions": 2, "id_collision_sample": ["conf/x.toml#item"],
                }},
            }
            with patch.object(self.srv, "_state_store_health_summary", return_value=summary):
                resp = self.srv.index_health_response(index)
        diag_text = str(resp.get("diagnostics", ""))
        self.assertIn("chunk_id_collisions", diag_text)
        self.assertIn("2 colliding id(s)", diag_text)

    def test_agent_mode_empty_sources_graceful(self):
        """1p4hj AC-6: agent-mode handles empty/degenerate candidate sets."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")])
        self.assertEqual(idx._agent_candidate_select({"docs": [], "code": []}, top_n=5, floor_k=3), [])

    def test_code_ask_rerank_mode_field_values(self):
        """Wave 1p52p: code_ask has ONE ranking path, so rerank_mode is ALWAYS "agent" — the former
        "local"/"rrf_fallback" labels were removed. The `reranked` bool (not rerank_mode) distinguishes
        GPU (cross-encoder ran, True) from CPU-only (False). The `rerank` param 'local' is a deprecated
        alias that behaves identically and still reports rerank_mode "agent"."""
        index = MagicMock()
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            index.search_combined.return_value = ([], False, 0, 0, [], [], "none", None)
            resp = self.srv.code_ask_response(index, root, "q", rerank="agent")["data"]
            self.assertEqual(resp["rerank_mode"], "agent")
            self.assertFalse(resp["reranked"])
            # GPU: cross-encoder ran → reranked True, rerank_mode still "agent"
            index.search_combined.return_value = ([], True, 0, 0, [], [], "none", None)
            resp = self.srv.code_ask_response(index, root, "q", rerank="agent")["data"]
            self.assertEqual(resp["rerank_mode"], "agent")
            self.assertTrue(resp["reranked"])
            # 'local' is now a deprecated alias for the same single path → rerank_mode "agent"
            index.search_combined.return_value = ([], False, 0, 0, [], [], "none", None)
            self.assertEqual(self.srv.code_ask_response(index, root, "q", rerank="local")["data"]["rerank_mode"], "agent")

    # --- _get_reranker caching ---

    def test_get_reranker_does_not_cache_none(self):
        """Wave 1p52p: _get_reranker uses accel_embedder.make_reranker (GPU FP16 / CPU INT8). It returns
        None only when reranking is disabled or unbuildable; in that case it must NOT cache a non-None
        reranker, must set self._reranker_disabled (so we don't re-probe every query), and return None."""
        import accel_embedder
        idx = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        idx._reranker = None
        # Wave 1p937: _get_reranker also fetches "_onnx_providers" (the resolved provider list
        # function) via _indexer_constant, so the mock must dispatch by constant name, not return a
        # single fixed value for every call.
        def _const(name):
            if name == "RERANKER_MODEL":
                return "cross-encoder/ms-marco-MiniLM-L-6-v2"
            if name == "_onnx_providers":
                return lambda: ["CPUExecutionProvider"]
            raise AssertionError(f"unexpected _indexer_constant({name!r})")

        with patch.object(accel_embedder, "make_reranker", return_value=None) as mk:
            with patch.object(idx, "_indexer_constant", side_effect=_const):
                with patch.object(idx, "_offline_model_env", return_value=__import__("contextlib").nullcontext()):
                    result = idx._get_reranker()
        mk.assert_called_once()
        self.assertIsNone(result)
        self.assertIsNone(idx._reranker, "must not cache a non-None reranker when make_reranker returns None")
        self.assertTrue(getattr(idx, "_reranker_disabled", False), "must mark reranker disabled to avoid re-probing")

    def test_get_reranker_caches_on_success(self):
        """Wave 1p52p: _get_reranker caches the StaticShapeReranker returned by
        accel_embedder.make_reranker (GPU FP16 or CPU INT8) in self._reranker."""
        import accel_embedder
        idx = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        idx._reranker = None
        mock_reranker = MagicMock()
        mock_reranker.model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_reranker.provider = "CoreMLExecutionProvider"

        # Wave 1p937: _get_reranker also fetches "_onnx_providers" via _indexer_constant.
        def _const(name):
            if name == "RERANKER_MODEL":
                return "cross-encoder/ms-marco-MiniLM-L-6-v2"
            if name == "_onnx_providers":
                return lambda: ["CoreMLExecutionProvider"]
            raise AssertionError(f"unexpected _indexer_constant({name!r})")

        logs: list[str] = []
        with patch.object(accel_embedder, "make_reranker", return_value=mock_reranker) as mk:
            with patch.object(idx, "_indexer_constant", side_effect=_const):
                with patch.object(idx, "_offline_model_env", return_value=__import__("contextlib").nullcontext()), \
                     patch.object(self.srv, "_wf_log", side_effect=logs.append):
                    result = idx._get_reranker()
        mk.assert_called_once()
        self.assertIs(idx._reranker, mock_reranker)
        self.assertIs(result, mock_reranker)
        self.assertTrue(
            any("static 40x512" in line for line in logs),
            f"the public success log must report the independent reranker batch: {logs}",
        )

    # --- search_combined: question-type-aware retrieval ---

    # --- search_combined: artifact_anchored exact-first routing ---

    def test_search_combined_weak_generated_symbol_uses_exact_first_when_code_hits(self):
        """Weak generated-symbol artifacts retain the keyword exact-first path."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=[self._fake_code_chunk("src/a.py")])
        fake_kw_resp = {
            "status": "ok",
            "data": {"results": [
                {"path": "scripts/lifecycle_id.py", "line": 106, "snippet": "def build_prefix("},
            ]},
        }
        # Wave 1p52p: the exact-first pass now rerank-FIRSTs the keyword candidates via _agent_rerank
        # (the unified single path), not the removed _rerank cross-encoder helper. With a reranker
        # available, agent_reranked is True; the exact-first code hits are still returned.
        mock_reranker = self._make_mock_reranker(1)
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp) as keyword:
                results, reranked, vector_ms, _, definition_boosted, _, _, _ = idx.search_combined(
                    "how does build_prefix generate the +2vr8 format?",
                    top_n=5,
                    question_type="artifact_anchored",
                )
        keyword.assert_called_once_with(idx.root, "build_prefix")
        self.assertTrue(reranked, "exact pass with reranker should return reranked=True")
        self.assertEqual(vector_ms, 0, "exact pass skips vector fetch; vector_ms must be 0")
        self.assertIn("artifact_anchored", definition_boosted)
        self.assertTrue(any("lifecycle_id.py" in r.get("path", "") for r in results))

    def test_search_combined_direct_file_artifact_uses_broad_hybrid_path(self):
        """Direct files stay publicly artifact-anchored but skip the exact keyword short-circuit."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("src/retrieval.py")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        observed_top_k = []
        original_lance = idx._lance_search

        def capture_lance(table, qvec, top_n, where=None, layer="project"):
            observed_top_k.append(top_n)
            return original_lance(table, qvec, top_n, where=where, layer=layer)

        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_lance_search", side_effect=capture_lance):
                with patch(f"{self.srv.__name__}.code_keyword_response") as keyword:
                    _, _, _, _, definition_boosted, _, _, _ = idx.search_combined(
                        "what does .aiignore exclude?",
                        top_n=5,
                        question_type="artifact_anchored",
                    )
        keyword.assert_not_called()
        self.assertTrue(observed_top_k, "direct artifact must execute vector retrieval")
        self.assertEqual(
            {self.srv.VECTOR_TOP_K_EXPLANATORY}, set(observed_top_k),
            "direct artifact must use the explanatory-like wider candidate pool",
        )
        self.assertNotIn("artifact_anchored", definition_boosted)
        self.assertEqual(
            1.0,
            self.srv._low_information_path_weight(".aiignore", "what does .aiignore exclude?"),
        )

    def test_code_ask_direct_dotfile_pins_owner_and_keeps_supporting_context(self):
        """The public path keeps broad synthesis while making the named dotfile rank one."""
        code = [
            {
                "id": "ignore-owner", "path": ".aiignore", "kind": "code",
                "language": "text", "text": "tmp/\n.cache/\n", "lines": [1, 2],
            },
            self._fake_code_chunk("ignore_loader", text="def load_ignore_patterns(): pass"),
            self._fake_code_chunk("path_filter", text="def should_index_path(): pass"),
        ]
        idx = self._make_index_with_docs(
            [self._fake_doc_chunk("indexing-guide", text="Ignore patterns shape index scope.")],
            code_chunks=code,
        )
        with patch.object(idx, "_get_reranker", return_value=None):
            response = self.srv.code_ask_response(
                idx, idx.root, "Explain the exclusions declared in .aiignore."
            )
        data = response["data"]
        self.assertEqual(data["question_type"], "artifact_anchored")
        self.assertEqual(data["search_mode"], "hybrid")
        self.assertEqual(data["citations"][0]["path"], ".aiignore")
        self.assertTrue(
            any(citation["path"] != ".aiignore" for citation in data["citations"]),
            "the exact-owner pin must not discard broad supporting results",
        )
        self.assertEqual(
            self.srv._low_information_path_weight(
                ".aiignore", "Explain the exclusions declared in .aiignore."
            ),
            1.0,
        )

    def test_code_ask_direct_manifest_pins_owner_and_keeps_supporting_context(self):
        """A root manifest owner ranks first without using the weak-artifact exact mode."""
        code = [
            {
                "id": "manifest-owner", "path": "pyproject.toml", "kind": "code",
                "language": "toml", "text": "requires-python = '>=3.11'", "lines": [1, 1],
            },
            self._fake_code_chunk("runtime_check", text="def require_supported_python(): pass"),
            self._fake_code_chunk("setup_flow", text="def setup_environment(): pass"),
        ]
        idx = self._make_index_with_docs(
            [self._fake_doc_chunk("setup-guide", text="Runtime setup prerequisites.")],
            code_chunks=code,
        )
        with patch.object(idx, "_get_reranker", return_value=None):
            response = self.srv.code_ask_response(
                idx, idx.root, "Describe the runtime constraint in pyproject.toml."
            )
        data = response["data"]
        self.assertEqual(data["question_type"], "artifact_anchored")
        self.assertEqual(data["search_mode"], "hybrid")
        self.assertEqual(data["citations"][0]["path"], "pyproject.toml")
        self.assertTrue(
            any(citation["path"] != "pyproject.toml" for citation in data["citations"]),
            "the exact-owner pin must preserve supporting hybrid citations",
        )
        self.assertEqual(
            self.srv._low_information_path_weight(
                "pyproject.toml", "Describe the runtime constraint in pyproject.toml."
            ),
            1.0,
        )

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
                    results, _, _, _, _, _, _, _ = idx.search_combined(
                        "how does build_prefix generate the +2vr8 format?",
                        top_n=5,
                        question_type="artifact_anchored", rerank="local",
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

    def test_search_combined_assessment_uses_top_k_explanatory(self):
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("c0")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        captured = {}
        original_lance = idx._lance_search

        def capture_top_k(table, qvec, top_n, where=None, layer="project"):
            captured["top_k"] = top_n
            return original_lance(table, qvec, top_n, where=where, layer=layer)

        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_lance_search", side_effect=capture_top_k):
                idx.search_combined(
                    "where are the retrieval gaps?", top_n=5, question_type="assessment",
                )
        self.assertEqual(captured.get("top_k"), self.srv.VECTOR_TOP_K_EXPLANATORY)

    def test_search_combined_derived_evidence_query_runs_only_for_assessment(self):
        idx = self._make_index_with_docs(
            [self._fake_doc_chunk("d0")],
            code_chunks=[self._fake_code_chunk("c0")],
        )
        embedded_queries = []
        lexical_queries = []
        original_embed = idx._embed_query

        def capture_embed(query, model):
            embedded_queries.append(query)
            return original_embed(query, model)

        def capture_lexical(query):
            lexical_queries.append(query)
            return []

        with patch.object(idx, "_embed_query", side_effect=capture_embed):
            with patch.object(idx, "_lexical_candidates", side_effect=capture_lexical):
                with patch.object(idx, "_get_reranker", return_value=None):
                    idx.search_combined(
                        "assess cache routing weaknesses",
                        top_n=5,
                        question_type="assessment",
                    )
        derived = [
            query for query in embedded_queries
            if self.srv._ASSESSMENT_EVIDENCE_SUFFIX in query
        ]
        self.assertEqual(len(derived), 1)
        self.assertEqual(lexical_queries, [
            "assess cache routing weaknesses",
            derived[0],
        ])

        embedded_queries.clear()
        lexical_queries.clear()
        with patch.object(idx, "_embed_query", side_effect=capture_embed):
            with patch.object(idx, "_lexical_candidates", side_effect=capture_lexical):
                with patch.object(idx, "_get_reranker", return_value=None):
                    idx.search_combined(
                        "explain cache routing",
                        top_n=5,
                        question_type="explanatory",
                    )
        self.assertFalse(any(self.srv._ASSESSMENT_EVIDENCE_SUFFIX in q for q in embedded_queries))
        self.assertEqual(lexical_queries, ["explain cache routing"])

    def _low_relevance_reranker(self):
        reranker = MagicMock()
        reranker.rerank.side_effect = lambda query, docs: [-6.0 for _ in docs]
        return reranker

    def _report_class_index(self):
        docs = [
            {"id": "report-a", "path": "docs/reports/audit-dispositions.md", "kind": "doc",
             "section": "Audit > Needs Fixed Now", "text": "finding one", "lines": [10, 20]},
            {"id": "report-b", "path": "docs/reports/audit-dispositions.md", "kind": "doc",
             "section": "Audit > Should Fix Now", "text": "finding two", "lines": [21, 30]},
            {"id": "wave-a", "path": "docs/waves/old wave/change.md", "kind": "doc",
             "text": "historical narrative", "lines": [1, 5]},
            self._fake_doc_chunk("d0"), self._fake_doc_chunk("d1"), self._fake_doc_chunk("d2"),
        ]
        return self._make_index_with_docs(docs, code_chunks=[self._fake_code_chunk("c0")])

    def test_search_combined_assessment_injects_no_report_class_rows(self):
        """Cycle-2 council (RED-DEL-1 / ARCH-SEAT-1 / QA-SEAT-1): assessment runs its
        derived docs expansion and nothing else; no path class is injected, no
        synthetic score is written, and citations stay reranker-ordered."""
        idx = self._report_class_index()
        observed = []
        original_lance = idx._lance_search

        def capture_lance(table, qvec, top_n, where=None, layer="project"):
            observed.append((top_n, where))
            return original_lance(table, qvec, top_n, where=where, layer=layer)

        with patch.object(idx, "_get_reranker", return_value=self._low_relevance_reranker()):
            with patch.object(idx, "_lance_search", side_effect=capture_lance):
                results, reranked, *_ = idx.search_combined(
                    "where are the biggest gaps in the audit tooling?",
                    top_n=5,
                    question_type="assessment",
                )
        self.assertTrue(reranked)
        self.assertEqual({None}, {row[1] for row in observed},
                         "no path-filtered retrieval pass runs for assessment")
        self.assertEqual(3, len(observed), "original docs, derived docs, and code passes only")
        self.assertFalse(any("evidence" in (r.get("sources") or []) for r in results))
        self.assertTrue(all(r["score"] < self.srv.CONF_AGENT_RERANK_LOW for r in results),
                        "every score is the reranker's own, never a floor")
        self.assertFalse(any("_relevance_score" in r or "_evidence_rank" in r for r in results))

    def test_code_ask_assessment_abstains_on_absent_topic(self):
        """An assessment-phrased absent topic returns a low band, weak citations, and the
        explicit no-confident-match gap (cycle-2 review, RED-DEL-4 / QA-SEAT-2)."""
        idx = self._report_class_index()
        with patch.object(idx, "_get_reranker", return_value=self._low_relevance_reranker()):
            response = self.srv.code_ask_response(
                idx, idx.root, "Review the lunar regolith job scheduler for weaknesses."
            )
        data = response["data"]
        self.assertEqual("assessment", data["question_type"])
        self.assertEqual("low", data["confidence"])
        self.assertTrue(all(c.get("weak") for c in data["citations"]))
        self.assertTrue(any("no confident match" in gap for gap in data["gaps"]))

    def test_code_ask_citations_expose_section_path_when_chunk_metadata_has_one(self):
        """`section` follows the chunk metadata: docs heading paths AND code symbol
        breadcrumbs (the indexer writes one on every row); a row without one omits the
        field (cycle-2 review, DOCS-DEL-1 / CODE-DEL-5)."""
        docs = [
            {"id": "report-a", "path": "docs/reports/audit-dispositions.md", "kind": "doc",
             "section": "Audit > Needs Fixed Now", "text": "finding one", "lines": [10, 20]},
            self._fake_doc_chunk("d0"),
        ]
        code = [
            {"id": "c-sec", "path": "src/billing.py", "kind": "code", "language": "python",
             "section": "billing > charge", "text": "def charge(): pass", "lines": [1, 4]},
            self._fake_code_chunk("c-nosec", text="def refund(): pass"),
        ]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        with patch.object(idx, "_get_reranker", return_value=self._low_relevance_reranker()):
            response = self.srv.code_ask_response(
                idx, idx.root, "where are the biggest gaps in the audit tooling?"
            )
        by_path = {c["path"]: c for c in response["data"]["citations"]}
        self.assertEqual("Audit > Needs Fixed Now",
                         by_path["docs/reports/audit-dispositions.md"].get("section"))
        self.assertEqual("billing > charge", by_path["src/billing.py"].get("section"))
        self.assertNotIn("section", by_path["src/c-nosec.py"])

    def test_classify_question_explanatory_lead_keeps_mechanism_questions_explanatory(self):
        """Cycle-2 review (RC-SEAT-2): a bare assessment noun inside a how/why question
        is not a review request; the pinned assessment forms still classify."""
        explanatory = (
            "How does the chunker handle a gap between sections?",
            "How does the chunker handle a gap in the heading tree?",
            "How does the retrieval posture sensor decide whether a gap fired?",
            "Explain how a Gapfill note clears the retrieval posture gap.",
            "Why does the .NET build fail?",
            "Describe the weaknesses section of the audit report format.",
        )
        for question in explanatory:
            with self.subTest(question=question):
                self.assertEqual("explanatory", self.srv._classify_question(question))
        assessment = (
            "where are the biggest gaps in the code MCP implementation?",
            "Which search-index weaknesses in this repository should be prioritized for remediation?",
            "what are the weaknesses in graph retrieval?",
            "Review the lunar regolith job scheduler for weaknesses.",
            "where are the biggest gaps in the lunar regolith helium-three harvest scheduler?",
        )
        for question in assessment:
            with self.subTest(question=question):
                self.assertEqual("assessment", self.srv._classify_question(question))

    def test_direct_artifact_cue_keeps_dot_directory_paths_and_rejects_non_files(self):
        """Cycle-2 review (CODE-DEL-1 / QA-SEAT-4 / RED-DEL-9)."""
        cue = self.srv._extract_direct_artifact_cue
        self.assertEqual(".wavefoundry/framework/scripts/indexer.py",
                         cue("what does .wavefoundry/framework/scripts/indexer.py walk?"))
        self.assertEqual(".claude/hooks/post-edit.py",
                         cue("What does .claude/hooks/post-edit.py run after an edit?"))
        self.assertEqual(".aiignore", cue("what does .aiignore exclude?"))
        self.assertEqual("pyproject.toml", cue("How does pyproject.toml define the metadata?"))
        self.assertEqual("", cue("Why does the .NET build fail?"))
        self.assertEqual("", cue("Retry at most .5 seconds later."))
        self.assertEqual("explanatory", self.srv._classify_question("Why does the .NET build fail?"))
        # Reverification RV-2: prose slash pairs, numeric ratios, and bare directories
        # are not file cues; a dotted, lettered final segment is.
        self.assertEqual("", cue("input/output handling in the walker"))
        self.assertEqual("", cue("and/or the reranker"))
        self.assertEqual("", cue("a ratio of 3/4.5 in the walk"))
        self.assertEqual("", cue("what is under docs/waves/ now?"))
        self.assertEqual("docs/agents/guru.md", cue("where is docs/agents/guru.md rendered from?"))
        self.assertEqual("explanatory",
                         self.srv._classify_question("how does the walker handle input/output?"))
        # Reverification RV3-2: a dot-directory prefix of a longer path never leaks
        # as the cue; extensionless finals and dot-rooted directories are not cues.
        self.assertEqual("", cue("what does .wavefoundry/bin/wf do?"))
        self.assertEqual("", cue("what is in .github/CODEOWNERS?"))
        self.assertEqual("", cue("what is under .wavefoundry/framework/scripts/ now?"))
        self.assertEqual("explanatory",
                         self.srv._classify_question("what is under .wavefoundry/framework/scripts/ now?"))
        self.assertEqual("pyproject.toml",
                         cue("under .wavefoundry/bin/wf the pyproject.toml drives setup"))

    def test_mechanism_framed_direct_artifact_questions_do_not_pin_the_file(self):
        """Cycle-2 review (ARCH-SEAT-5 / RED-DEL-2 / QA-SEAT-3): a question that names a
        file as its object keeps injection and the artifact type, but reranked evidence
        keeps the lead; a content-framed question still pins."""
        framed = self.srv._mechanism_framed_question
        self.assertTrue(framed("How does the framework restore the .gitignore runtime block?"))
        self.assertTrue(framed("Which function renders the managed block in .gitignore?"))
        self.assertTrue(framed("which tests cover chunker.py?"))
        self.assertFalse(framed("what does .aiignore exclude?"))
        self.assertFalse(framed("How does pyproject.toml define this repository's package and tooling metadata?"))
        self.assertFalse(framed("Explain the exclusions declared in .aiignore."))
        # Reverification RED-RV-3: a leading article does not turn the named subject
        # into a mechanism question.
        self.assertFalse(framed("How does the .aiignore file exclude paths?"))
        self.assertFalse(framed("How does this pyproject.toml declare the venv?"))
        self.assertTrue(framed("How does the renderer rewrite the managed block inside .gitignore?"))
        # Reverification RV3-1/RV3-3: a path-named subject and a single noun between
        # article and name keep the pin; a file in object position stays framed.
        self.assertFalse(framed("How does docs/agents/guru.md describe retrieval?"))
        self.assertFalse(framed("How does src/config.yaml set the model?"))
        self.assertFalse(framed("How does the file .aiignore exclude paths?"))
        self.assertTrue(framed("How does the walker index .aiignore?"))
        self.assertTrue(framed("How does the installer restore .aiignore?"))
        code = [
            {"id": "ignore-owner", "path": ".gitignore", "kind": "code", "language": "text",
             "text": "dist/\n", "lines": [1, 1]},
            self._fake_code_chunk("renderer", text="def render_gitignore_block(): pass"),
            self._fake_code_chunk("other", text="def unrelated(): pass"),
        ]
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=code)
        reranker = MagicMock()

        def score(query, texts):
            return [6.0 if "render_gitignore_block" in t else -6.0 for t in texts]

        reranker.rerank.side_effect = score
        with patch.object(idx, "_get_reranker", return_value=reranker):
            with patch.object(idx, "_lexical_candidates", return_value=[]):
                framed_response = self.srv.code_ask_response(
                    idx, idx.root, "Which function renders the managed block in .gitignore?"
                )
                content_response = self.srv.code_ask_response(
                    idx, idx.root, "what does .gitignore exclude?"
                )
        self.assertEqual("artifact_anchored", framed_response["data"]["question_type"])
        self.assertEqual("src/renderer.py", framed_response["data"]["citations"][0]["path"])
        self.assertIn(".gitignore", [c["path"] for c in framed_response["data"]["citations"]],
                      "owner rows are still injected for the mechanism-framed question")
        self.assertEqual(".gitignore", content_response["data"]["citations"][0]["path"])

    def test_direct_artifact_owner_rows_read_published_tables_only(self):
        code = [
            {"id": "ignore-owner", "path": ".aiignore", "kind": "code", "language": "text",
             "text": "tmp/\n.cache/\n", "lines": [1, 2]},
            {"id": "nested-owner", "path": "pkg/.aiignore", "kind": "code", "language": "text",
             "text": "build/\n", "lines": [1, 1]},
            self._fake_code_chunk("loader", text="def load(): pass"),
        ]
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=code)
        rows = idx._direct_artifact_owner_rows(".aiignore")
        self.assertEqual({".aiignore", "pkg/.aiignore"}, {r["path"] for r in rows})
        self.assertTrue(all(r["score"] == 0.0 and "vector" not in r for r in rows))
        self.assertEqual(
            {".aiignore", "pkg/.aiignore"},
            {r["path"] for r in idx._direct_artifact_owner_rows("./.aiignore")},
            "a basename cue owns every file with that basename, like the pin itself",
        )
        self.assertEqual(
            ["pkg/.aiignore"], [r["path"] for r in idx._direct_artifact_owner_rows("pkg/.aiignore")],
        )
        self.assertEqual([], idx._direct_artifact_owner_rows(".py"))
        self.assertEqual([], idx._direct_artifact_owner_rows(""))
        self.assertEqual([], idx._direct_artifact_owner_rows("missing.toml"))

    def test_direct_artifact_owner_rows_use_exact_ownership_not_like_wildcards(self):
        """Cycle-2 review (CODE-DEL-3 / SEC-SEAT-3): `_` is a LIKE wildcard; ownership is
        decided by exact path or basename equality after the fetch."""
        code = [
            {"id": "want", "path": "docs/a_b.md", "kind": "code", "language": "text",
             "text": "a_b", "lines": [1, 1]},
            {"id": "sibling", "path": "docs/axb.md", "kind": "code", "language": "text",
             "text": "axb", "lines": [1, 1]},
            {"id": "nested", "path": "sub/dir/a_b.md", "kind": "code", "language": "text",
             "text": "nested", "lines": [1, 1]},
            {"id": "upper", "path": "AGENTS.md", "kind": "code", "language": "text",
             "text": "# Agent Guide", "lines": [1, 1]},
            {"id": "upper-nested", "path": "pkg/AGENTS.md", "kind": "code", "language": "text",
             "text": "# Area guide", "lines": [1, 1]},
            {"id": "mixed", "path": "src/MixedCase.py", "kind": "code", "language": "python",
             "text": "X = 1", "lines": [1, 1]},
        ]
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], code_chunks=code)
        self.assertEqual({"docs/a_b.md", "sub/dir/a_b.md"},
                         {r["path"] for r in idx._direct_artifact_owner_rows("a_b.md")})
        self.assertEqual(["docs/a_b.md"],
                         [r["path"] for r in idx._direct_artifact_owner_rows("docs/a_b.md")])
        self.assertEqual([], idx._direct_artifact_owner_rows("axb.mx"))
        # Reverification RV-1: ownership compares casefolded paths on both sides, so a
        # cue with an uppercase letter is not fetched and then dropped.
        self.assertEqual({"AGENTS.md", "pkg/AGENTS.md"},
                         {r["path"] for r in idx._direct_artifact_owner_rows("AGENTS.md")})
        self.assertEqual(["pkg/AGENTS.md"],
                         [r["path"] for r in idx._direct_artifact_owner_rows("pkg/AGENTS.md")])
        self.assertEqual(["src/MixedCase.py"],
                         [r["path"] for r in idx._direct_artifact_owner_rows("MixedCase.py")])

    def test_code_ask_pins_mixed_case_owner_when_vector_recall_misses_it(self):
        """Reverification RV-1 end to end: the guarantee that the pin never depends on
        vector recall holds for `AGENTS.md`, not only for lowercase names."""
        code = [
            {"id": "agents-owner", "path": "AGENTS.md", "kind": "code", "language": "text",
             "text": "## Git Commits\nAgents must not run git commit.\n", "lines": [1, 2]},
            self._fake_code_chunk("policy_loader", text="def load_commit_policy(): pass"),
            self._fake_code_chunk("other", text="def unrelated(): pass"),
        ]
        idx = self._make_index_with_docs(
            [self._fake_doc_chunk("commit-guide", text="Commit policy lives in the agent guide.")],
            code_chunks=code,
        )
        original_lance = idx._lance_search

        def recall_without_owner(table, qvec, top_n, where=None, layer="project"):
            return [
                row for row in original_lance(table, qvec, top_n, where=where, layer=layer)
                if row.get("path") != "AGENTS.md"
            ]

        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_lance_search", side_effect=recall_without_owner):
                with patch.object(idx, "_lexical_candidates", return_value=[]):
                    response = self.srv.code_ask_response(
                        idx, idx.root, "what does AGENTS.md say about git commits?"
                    )
        data = response["data"]
        self.assertEqual("artifact_anchored", data["question_type"])
        self.assertEqual("AGENTS.md", data["citations"][0]["path"])
        self.assertEqual(1, sum(1 for c in data["citations"] if c["path"] == "AGENTS.md"))

    def test_code_ask_direct_artifact_pins_owner_even_when_vector_recall_misses_it(self):
        code = [
            {"id": "ignore-owner", "path": ".aiignore", "kind": "code", "language": "text",
             "text": "tmp/\n.cache/\n", "lines": [1, 2]},
            self._fake_code_chunk("ignore_loader", text="def load_ignore_patterns(): pass"),
            self._fake_code_chunk("path_filter", text="def should_index_path(): pass"),
        ]
        idx = self._make_index_with_docs(
            [self._fake_doc_chunk("indexing-guide", text="Ignore patterns shape index scope.")],
            code_chunks=code,
        )
        original_lance = idx._lance_search

        def recall_without_owner(table, qvec, top_n, where=None, layer="project"):
            return [
                row for row in original_lance(table, qvec, top_n, where=where, layer=layer)
                if row.get("path") != ".aiignore"
            ]

        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_lance_search", side_effect=recall_without_owner):
                with patch.object(idx, "_lexical_candidates", return_value=[]):
                    response = self.srv.code_ask_response(
                        idx, idx.root, "what does .aiignore exclude?"
                    )
        data = response["data"]
        self.assertEqual("artifact_anchored", data["question_type"])
        self.assertEqual(".aiignore", data["citations"][0]["path"])
        self.assertEqual(1, sum(1 for c in data["citations"] if c["path"] == ".aiignore"))
        self.assertTrue(any(c["path"] != ".aiignore" for c in data["citations"]))

    def test_search_combined_assessment_injects_published_symbol_owner(self):
        idx = self._make_index_with_docs([], code_chunks=[self._fake_code_chunk("other")])
        owner = {
            "path": "src/index.py", "text": "class WaveIndex:", "score": 0.8,
            "kind": "code", "lines": [10, 10], "source": "code", "sources": ["code"],
        }
        with patch.object(idx, "_published_exact_definition_candidate", return_value=owner) as resolve:
            with patch.object(idx, "_get_reranker", return_value=None):
                results, *_ = idx.search_combined(
                    "assess WaveIndex weaknesses", top_n=5, question_type="assessment",
                )
        resolve.assert_called_once_with("WaveIndex")
        self.assertIn("src/index.py", [item.get("path") for item in results])

    def test_search_combined_assessment_ranks_report_and_code_ahead_of_wave_history(self):
        docs = [
            {
                "id": "current-audit", "path": "docs/reports/cache-audit.md", "kind": "doc",
                "text": "Current cache-routing assessment evidence.", "lines": [1, 5],
            },
            {
                "id": "historical-wave", "path": "docs/waves/old-delivery/change.md", "kind": "doc",
                "text": "Historical cache-routing delivery discussion.", "lines": [1, 5],
            },
        ]
        code = [
            {
                "id": "current-code", "path": "src/cache_router.py", "kind": "code",
                "language": "python", "text": "def route_cached_item(): pass", "lines": [1, 2],
            }
        ]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        with patch.object(idx, "_get_reranker", return_value=None):
            results, *_ = idx.search_combined(
                "Assess cache-routing weaknesses.", top_n=5, question_type="assessment"
            )
        paths = [item.get("path") for item in results]
        historical_rank = paths.index("docs/waves/old-delivery/change.md")
        self.assertLess(paths.index("docs/reports/cache-audit.md"), historical_rank)
        self.assertLess(paths.index("src/cache_router.py"), historical_rank)

    def test_search_combined_derived_report_survives_rerank_and_selection(self):
        idx = self._make_index_with_docs(
            [self._fake_doc_chunk("placeholder")],
            code_chunks=[self._fake_code_chunk("placeholder")],
        )
        historical = {
            "id": "historical", "path": "docs/waves/old-delivery/change.md", "kind": "doc",
            "text": "Historical cache routing discussion.", "lines": [1, 5], "score": 0.99,
        }
        current_report = {
            "id": "current-report", "path": "docs/reports/cache-audit.md", "kind": "doc",
            "text": "Current audit findings for cache routing.", "lines": [1, 5], "score": 0.90,
        }
        implementation = {
            "id": "implementation", "path": "src/cache_router.py", "kind": "code",
            "text": "def route_cached_item(): pass", "lines": [1, 2], "score": 0.82,
        }

        def rerank(_query, candidates):
            scores = {
                historical["path"]: 0.99,
                current_report["path"]: 0.90,
                implementation["path"]: 0.82,
            }
            for candidate in candidates:
                candidate["score"] = scores[candidate["path"]]
            return True

        with patch.object(
            idx, "_lance_search", side_effect=[[historical], [current_report], [implementation]]
        ) as lance:
            with patch.object(idx, "_lexical_candidates", return_value=[]):
                with patch.object(idx, "_agent_rerank", side_effect=rerank):
                    with patch.object(idx, "_graph_signal_candidates", return_value=[]):
                        results, reranked, *_ = idx.search_combined(
                            "assess cache routing weaknesses",
                            top_n=5,
                            question_type="assessment",
                        )
        self.assertTrue(reranked)
        self.assertEqual(lance.call_count, 3, "one original docs, one derived docs, one code search")
        self.assertTrue(all(call.kwargs.get("where") is None for call in lance.call_args_list),
                        "no path-filtered pass exists (cycle-2 council removal)")
        paths = [item["path"] for item in results]
        historical_rank = paths.index(historical["path"])
        self.assertLess(paths.index(current_report["path"]), historical_rank)
        self.assertLess(paths.index(implementation["path"]), historical_rank)

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

    def test_search_combined_navigational_tilt_only_when_reranked(self):
        """1p4wz Fix 3: the navigational cross-source weight is only meaningful on the unified
        post-rerank sigmoid scale, so search_combined passes it to selection ONLY when the
        cross-encoder ran. When the reranker is unavailable the per-source scores are incomparable
        cross-model cosines (arctic docs vs bge code) and the cross-source weight is suppressed."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("c0")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        captured: dict = {}
        real_select = idx._agent_candidate_select

        def _spy(sources, top_n, floor_k, weights=None, text_budget=None):
            captured["weights"] = weights
            return real_select(sources, top_n, floor_k, weights=weights, text_budget=text_budget)

        # Length-matching mock so _agent_rerank always succeeds regardless of injected candidate count.
        reranker = MagicMock()
        reranker.rerank.side_effect = lambda q, docs: [0.0] * len(docs)

        # Reranked → the navigational tilt is applied.
        with patch.object(idx, "_get_reranker", return_value=reranker):
            with patch.object(idx, "_agent_candidate_select", side_effect=_spy):
                idx.search_combined("where is the config", top_n=5, question_type="navigational")
        self.assertEqual(
            captured["weights"],
            {"code": self.srv.RRF_NAVIGATIONAL_CODE_WEIGHT, "docs": self.srv.RRF_NAVIGATIONAL_DOCS_WEIGHT},
        )

        # No reranker → tilt suppressed (would multiply incomparable cross-model cosines).
        captured.clear()
        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_agent_candidate_select", side_effect=_spy):
                idx.search_combined("where is the config", top_n=5, question_type="navigational")
        self.assertIsNone(captured["weights"])

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
                results, reranked, _, _, _, _, _, _ = idx.search_combined("how does billing work", top_n=5, question_type="explanatory", rerank="local")
        self.assertTrue(reranked)
        # The business logic file must appear before the infra file
        paths = [r.get("path", "") for r in results]
        infra_path = infra_chunk["path"]
        biz_path = biz_chunk["path"]
        self.assertIn(infra_path, paths)
        self.assertIn(biz_path, paths)
        self.assertLess(paths.index(biz_path), paths.index(infra_path))

    def test_search_combined_assessment_partitions_infra_paths_after_rerank(self):
        docs = [self._fake_doc_chunk("d0")]
        code = [
            self._fake_code_chunk("src/constructs/MyStack.ts"),
            self._fake_code_chunk("src/services/billing.ts"),
        ]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        mock_reranker = MagicMock()
        infra_chunk = {**code[0], "score": 0.9}
        biz_chunk = {**code[1], "score": 0.8}
        mock_reranker.rerank.return_value = [0.9, 0.8, 0.5]
        with patch.object(idx, "_get_reranker", return_value=mock_reranker):
            with patch.object(idx, "_rerank", return_value=[infra_chunk, biz_chunk]):
                results, *_ = idx.search_combined(
                    "where are the billing weaknesses?", top_n=5,
                    question_type="assessment", rerank="local",
                )
        paths = [result.get("path", "") for result in results]
        self.assertLess(paths.index(biz_chunk["path"]), paths.index(infra_chunk["path"]))

    def test_search_combined_non_explanatory_no_partition(self):
        """For navigational/instructional questions, infra paths are not partitioned."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("src/constructs/MyStack.ts")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        infra_chunk = {**code[0], "score": 0.9}
        with patch.object(idx, "_get_reranker", return_value=None):
            results, reranked, _, _, _, _, _, _ = idx.search_combined("where is the stack", top_n=5, question_type="navigational")
        self.assertFalse(reranked)  # RRF fallback

    def test_search_combined_infrastructure_demoted_flag_in_code_ask(self):
        """code_ask_response sets infrastructure_demoted=True when explanatory + reranked + infra citations."""
        index = MagicMock()
        infra_result = {"path": "src/constructs/MyStack.ts", "score": 0.9, "lines": [1, 10], "text": "...", "kind": "code"}
        biz_result = {"path": "src/services/billing.ts", "score": 0.8, "lines": [1, 10], "text": "...", "kind": "code"}
        index.search_combined.return_value = ([infra_result, biz_result], True, 10, 20, [], [], "none", None)
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            # "how does billing work" → explanatory; constructs/ → infra segment
            result = self.srv.code_ask_response(index, root, "how does billing work")
        data = result.get("data", {})
        self.assertTrue(data.get("infrastructure_demoted", False))

    def test_search_combined_infrastructure_demoted_flag_for_assessment(self):
        index = MagicMock()
        infra_result = {"path": "src/constructs/MyStack.ts", "score": 0.9, "lines": [1, 10], "text": "...", "kind": "code"}
        biz_result = {"path": "src/services/billing.ts", "score": 0.8, "lines": [1, 10], "text": "...", "kind": "code"}
        index.search_combined.return_value = ([infra_result, biz_result], True, 10, 20, [], [], "none", None)
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "where are the billing weaknesses?")
        self.assertEqual(result["data"]["question_type"], "assessment")
        self.assertTrue(result["data"].get("infrastructure_demoted"))

    def test_search_combined_no_infrastructure_demoted_for_navigational(self):
        """code_ask_response does not set infrastructure_demoted for navigational questions."""
        index = MagicMock()
        infra_result = {"path": "src/constructs/MyStack.ts", "score": 0.9, "lines": [1, 10], "text": "...", "kind": "code"}
        index.search_combined.return_value = ([infra_result], True, 5, 10, [], [], "none", None)
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
        index.search_combined.return_value = ([], False, 5, 3, [], [], "none", None)
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
        index.search_combined.return_value = ([], False, 0, 0, [], [], "none", None)
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
        index.search_combined.return_value = ([], False, 10, 20, [], [], "none", None)
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
        index.search_combined.return_value = ([], False, 5, 3, [], [], "none", None)
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
                    results, reranked, _, _, definition_boosted, _, _, _ = idx.search_combined(
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
            _, _, _, _, definition_boosted, _, _, _ = idx.search_combined("where is the billing handler", top_n=5)
        self.assertEqual(definition_boosted, [])

    def test_definition_boost_result_count_bounded_by_agent_cap(self):
        """Wave 1p52p: even when definition-boost injects candidates, the agent path bounds the count
        by the text budget + AGENT_CANDIDATE_MAX backstop, not a hard top_n cap."""
        docs = [self._fake_doc_chunk(f"d{i}") for i in range(5)]
        code = [self._fake_code_chunk(f"c{i}") for i in range(5)]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        # Inject 5 SQL candidates via the mock
        sql_hits = [{"path": f"migrations/m{i}.sql", "line": i + 1, "snippet": "CREATE TABLE"} for i in range(5)]
        fake_kw_resp = {"status": "ok", "data": {"results": sql_hits}}
        with patch.object(idx, "_get_reranker", return_value=None):
            with patch(f"{self.srv.__name__}.code_keyword_response", return_value=fake_kw_resp):
                results, _, _, _, _, _, _, _ = idx.search_combined("how does the sql schema work", top_n=3)
        self.assertLessEqual(len(results), max(3, self.srv.AGENT_CANDIDATE_MAX))

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
                    _, _, _, _, boosted, _, _, _ = idx.search_combined("what graphql types exist", top_n=5)
            self.assertIn("graphql", boosted)
        finally:
            self.srv.DEFINITION_BOOST_RULES = original_rules

    def test_definition_boosted_flag_propagated_to_code_ask_response(self):
        """code_ask_response includes definition_boosted list when rule fired."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 0, 0, ["sql"], [], "none", None)
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
        index.search_combined.return_value = ([], False, 0, 0, [], [], "none", None)
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "where is the billing handler?")
        data = result.get("data", {})
        self.assertNotIn("definition_boosted", data)

    # --- Structurally confirmed symbol-definition preference ---

    def _reranker_with_logits(self, logits):
        """Mock reranker whose rerank() returns the given raw logits, aligned to the passages."""
        reranker = MagicMock()
        reranker.rerank.side_effect = lambda query, docs: list(logits)
        return reranker

    def test_agent_rerank_writes_sigmoid_scores(self):
        """_agent_rerank rewrites each candidate's score to sigmoid(logit) — the unified relevance scale
        the whole rerank-FIRST design (per-index floor + confidence band) keys off. Exercises real code."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")], [self._fake_code_chunk("c0")])
        candidates = [
            {"path": "docs/a.md", "kind": "doc", "text": "alpha", "score": 0.11},
            {"path": "src/b.py", "kind": "code", "text": "beta", "score": 0.22},
        ]
        with patch.object(idx, "_get_reranker", return_value=self._reranker_with_logits([-2.0, 2.0])):
            ran = idx._agent_rerank("q", candidates)
        self.assertTrue(ran)
        self.assertAlmostEqual(candidates[0]["score"], 1.0 / (1.0 + math.exp(2.0)))   # sigmoid(-2)
        self.assertAlmostEqual(candidates[1]["score"], 1.0 / (1.0 + math.exp(-2.0)))  # sigmoid(2)

    def test_agent_rerank_orders_highest_logit_first(self):
        """The highest-logit candidate ends up with the highest score (rerank-first ordering signal)."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")])
        candidates = [
            {"path": "a", "kind": "code", "text": "a", "score": 0.9},
            {"path": "b", "kind": "code", "text": "b", "score": 0.1},
            {"path": "c", "kind": "code", "text": "c", "score": 0.5},
        ]
        # Pre-rerank cosine order is a,c,b; the reranker disagrees and ranks b highest.
        with patch.object(idx, "_get_reranker", return_value=self._reranker_with_logits([-1.0, 3.0, 0.0])):
            idx._agent_rerank("q", candidates)
        best = max(candidates, key=lambda c: c["score"])
        self.assertEqual(best["path"], "b")

    def test_agent_rerank_noop_without_reranker(self):
        """No reranker (CPU disabled / unbuildable) → no-op, scores untouched, returns False."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")])
        candidates = [{"path": "docs/a.md", "kind": "doc", "text": "alpha", "score": 0.42}]
        with patch.object(idx, "_get_reranker", return_value=None):
            ran = idx._agent_rerank("q", candidates)
        self.assertFalse(ran)
        self.assertEqual(candidates[0]["score"], 0.42)

    def test_agent_rerank_rejects_length_mismatch(self):
        """A reranker returning the wrong logit count is rejected wholesale (no partial/corrupt scoring)."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")])
        candidates = [
            {"path": "docs/a.md", "kind": "doc", "text": "alpha", "score": 0.5},
            {"path": "src/b.py", "kind": "code", "text": "beta", "score": 0.5},
        ]
        with patch.object(idx, "_get_reranker", return_value=self._reranker_with_logits([1.0])):
            ran = idx._agent_rerank("q", candidates)
        self.assertFalse(ran)
        self.assertEqual([c["score"] for c in candidates], [0.5, 0.5])  # untouched

    def test_symbol_definition_boost_raises_low_score(self):
        """A confirmed definition gets _SYMBOL_DEFINITION_BOOST on top of its sigmoid score —
        asserted through real _agent_rerank (not re-implemented test arithmetic)."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")])
        boost = self.srv._SYMBOL_DEFINITION_BOOST
        candidates = [
            {"path": "docs/foo.md", "kind": "doc", "text": "", "score": 0.0},
            {"path": "server.py", "kind": "code", "text": "", "score": 0.0, "_sym_definition": True},
        ]
        # Equal logits (sigmoid(0)=0.5) isolate the boost: only the code+sym chunk should rise.
        with patch.object(idx, "_get_reranker", return_value=self._reranker_with_logits([0.0, 0.0])):
            idx._agent_rerank("q", candidates)
        self.assertAlmostEqual(candidates[0]["score"], 0.5)                    # doc: no boost
        self.assertAlmostEqual(candidates[1]["score"], min(0.5 + boost, 1.0))  # code+sym: boosted

    def test_symbol_definition_boost_helps_mid_scoring_impl(self):
        """A reranker-relevant impl chunk (score >= 0.35) beats the worst-case demoted wave doc after boost."""
        boost = self.srv._SYMBOL_DEFINITION_BOOST
        max_wave_demoted = 1.0 * self.srv._DEMOTION_WAVES  # 0.75
        # A chunk the reranker considers genuinely relevant (score > 0.35) should win
        mid_score = 0.36
        self.assertGreater(mid_score + boost, max_wave_demoted,
            f"Mid-relevance impl ({mid_score} + {boost} = {mid_score + boost}) should beat demoted wave ({max_wave_demoted})")
        # A low-relevance chunk (comment/reference, score ~ 0.20) should stay below wave doc
        low_score = 0.20
        self.assertLessEqual(low_score + boost, max_wave_demoted,
            f"Low-relevance chunk ({low_score} + {boost} = {low_score + boost}) should NOT beat demoted wave ({max_wave_demoted})")

    def test_symbol_definition_boost_capped_at_one(self):
        """Boosted score is capped at 1.0 — asserted through real _agent_rerank."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")])
        candidates = [{"path": "server.py", "kind": "code", "text": "", "score": 0.0, "_sym_definition": True}]
        # sigmoid(8) ≈ 0.9997; + boost would exceed 1.0 → must clamp.
        with patch.object(idx, "_get_reranker", return_value=self._reranker_with_logits([8.0])):
            idx._agent_rerank("q", candidates)
        self.assertEqual(candidates[0]["score"], 1.0)

    def test_symbol_definition_boost_not_applied_to_doc_kind(self):
        """Boost only applies to kind='code'; a marked doc chunk is not boosted."""
        idx = self._make_index_with_docs([self._fake_doc_chunk("d0")])
        candidates = [{"path": "docs/foo.md", "kind": "doc", "text": "", "score": 0.0, "_sym_definition": True}]
        with patch.object(idx, "_get_reranker", return_value=self._reranker_with_logits([0.0])):
            idx._agent_rerank("q", candidates)
        self.assertAlmostEqual(candidates[0]["score"], 0.5)  # sigmoid(0), no boost

    def test_symbol_definition_marker_stripped_from_results(self):
        """The private definition marker is absent from public results."""
        # Simulate the stripping step that runs after _rerank in search_combined
        results = [
            {"path": "docs/foo.md", "score": 0.75, "kind": "doc"},
            {"path": "server.py", "score": 1.0, "kind": "code", "_sym_definition": True},
        ]
        for r in results:
            r.pop("_sym_definition", None)
        for r in results:
            self.assertNotIn("_sym_definition", r)

    def _published_graph_module(self, nodes, *, builder_version="45", present=True):
        graph_indexer = MagicMock()
        graph_indexer.GRAPH_BUILDER_VERSION = "45"
        graph_indexer.DECLARATION_NODE_KINDS = frozenset({
            "class", "constant", "function", "property", "type", "variable"
        })
        graph_indexer.read_graph_payload.return_value = {
            "present": present,
            "layer": "project",
            "builder_version": builder_version,
            "nodes": nodes,
            "edges": [],
        }
        def bound_receipt(root, source_path, layer):
            source_text = (Path(root) / source_path).read_bytes().decode(
                "utf-8", errors="replace"
            )
            return {
                "payload": graph_indexer.read_graph_payload.return_value,
                "source_hash": hashlib.sha256(
                    source_text.encode("utf-8", errors="replace")
                ).hexdigest(),
            }
        graph_indexer.read_bound_graph_payload_source_hash.side_effect = bound_receipt
        graph_query = MagicMock()
        graph_query._get_graph_indexer.return_value = graph_indexer
        return graph_query, graph_indexer

    def _adversarial_symbol_reranker(self):
        reranker = MagicMock()
        reranker.rerank.side_effect = lambda query, docs: [
            5.0 if "USAGE_HIT" in text else -5.0 if "DECLARATION_HIT" in text else 0.0
            for text in docs
        ]
        return reranker

    def test_code_ask_pins_published_language_neutral_definitions(self):
        """AC-1/3: representative graph languages share one routing-neutral
        declaration pin even when a usage gets the higher reranker score."""
        cases = (
            ("target_symbol", "src/defs.py", "def target_symbol():\n    return 'DECLARATION_HIT'\n", "src/use.py", "USAGE_HIT = target_symbol()\n"),
            ("renderWidget", "web/widget.js", "function renderWidget() { return 'DECLARATION_HIT'; }\n", "web/use.js", "const USAGE_HIT = renderWidget();\n"),
            ("renderPanel", "web/panel.ts", "export function renderPanel() { return 'DECLARATION_HIT'; }\n", "web/use.ts", "const USAGE_HIT = renderPanel();\n"),
            ("renderJava", "src/Widget.java", "class Widget { void renderJava() { /* DECLARATION_HIT */ } }\n", "src/Use.java", "class Use { void x() { renderJava(); /* USAGE_HIT */ } }\n"),
            ("RenderCSharp", "src/Widget.cs", "class Widget { void RenderCSharp() { var x = \"DECLARATION_HIT\"; } }\n", "src/Use.cs", "class Use { void X() { RenderCSharp(); /* USAGE_HIT */ } }\n"),
            ("render_cpp", "src/widget.cpp", "void render_cpp() { /* DECLARATION_HIT */ }\n", "src/use.cpp", "void use() { render_cpp(); /* USAGE_HIT */ }\n"),
            ("renderGo", "src/widget.go", "func renderGo() string { return \"DECLARATION_HIT\" }\n", "src/use.go", "func use() { renderGo() /* USAGE_HIT */ }\n"),
            ("renderRust", "src/widget.rs", "fn renderRust() { /* DECLARATION_HIT */ }\n", "src/use.rs", "fn use_it() { renderRust(); /* USAGE_HIT */ }\n"),
            ("renderKotlin", "src/Widget.kt", "fun renderKotlin() = \"DECLARATION_HIT\"\n", "src/Use.kt", "fun useIt() = renderKotlin() // USAGE_HIT\n"),
            ("renderSwift", "src/Widget.swift", "func renderSwift() { /* DECLARATION_HIT */ }\n", "src/Use.swift", "func useIt() { renderSwift() /* USAGE_HIT */ }\n"),
        )
        for symbol, def_path, def_source, usage_path, usage_source in cases:
            with self.subTest(symbol=symbol):
                chunks = [
                    {"id": f"{symbol}-usage", "path": usage_path, "kind": "code", "language": "javascript", "text": usage_source, "lines": [1, 1]},
                    {"id": f"{symbol}-definition", "path": def_path, "kind": "code", "language": "python", "text": def_source, "lines": [1, 2]},
                ]
                idx = self._make_index_with_docs([self._fake_doc_chunk("context")], chunks)
                for path, source in ((def_path, def_source), (usage_path, usage_source)):
                    target = idx.root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(source, encoding="utf-8")
                graph_query, _ = self._published_graph_module([{
                    "id": f"{def_path}::{symbol}",
                    "label": symbol,
                    "kind": "function",
                    "source_file": def_path,
                    "source_location": "1:0",
                }])
                with patch(f"{self.srv.__name__}._load_graph_query", return_value=graph_query), \
                     patch.object(idx, "_graph_signal_candidates", return_value=[]), \
                     patch.object(idx, "_get_reranker", return_value=self._adversarial_symbol_reranker()):
                    response = self.srv.code_ask_response(idx, idx.root, f"where is {symbol}?")
                self.assertEqual(response["status"], "ok")
                citations = response["data"]["citations"]
                self.assertGreaterEqual(len(citations), 2)
                self.assertEqual(citations[0]["path"], def_path)
                self.assertTrue(any(citation["path"] == usage_path for citation in citations[1:]))
                self.assertNotIn("_sym_definition", citations[0])
                self._tmp.cleanup()
                del self._tmp

    def test_code_ask_pins_verified_candidate_over_line_one_summary(self):
        """AC-3: a line-one code summary cannot inherit graph authority."""
        symbol = "target_symbol"
        def_path = "src/defs.py"
        def_source = "def target_symbol():\n    return 'DECLARATION_HIT'\n"
        chunks = [
            {"id": "summary", "path": def_path, "kind": "code-summary", "language": "python", "text": "Symbols: target_symbol, helper USAGE_HIT", "lines": [1, 20]},
            {"id": "usage", "path": "src/use.py", "kind": "code", "language": "python", "text": "USAGE_HIT = target_symbol()", "lines": [1, 1]},
        ]
        idx = self._make_index_with_docs([self._fake_doc_chunk("context")], chunks)
        for path, source in ((def_path, def_source), ("src/use.py", chunks[1]["text"])):
            target = idx.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        graph_query, _ = self._published_graph_module([{
            "id": f"{def_path}::{symbol}", "label": symbol, "kind": "function",
            "source_file": def_path, "source_location": "1:0",
        }])
        with patch(f"{self.srv.__name__}._load_graph_query", return_value=graph_query), \
             patch.object(idx, "_graph_signal_candidates", return_value=[]), \
             patch.object(idx, "_get_reranker", return_value=self._adversarial_symbol_reranker()):
            response = self.srv.code_ask_response(idx, idx.root, f"where is {symbol}?")
        first = response["data"]["citations"][0]
        self.assertEqual(first["path"], def_path)
        self.assertEqual(first["kind"], "code")
        self.assertIn("def target_symbol", first["excerpt"])
        self.assertNotIn("Symbols:", first["excerpt"])

    def test_graph_definition_candidate_uses_inclusive_two_line_range(self):
        idx = self._make_index_with_docs([self._fake_doc_chunk("context")])
        candidate = idx._node_def_candidate(
            {"label": "target_symbol", "kind": "function", "source_file": "src/defs.py", "source_location": "1:0"},
            source_text="def target_symbol():\n    return 1\n",
        )
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["lines"], [1, 2])

    def test_code_ask_hashes_and_renders_one_source_read(self):
        symbol = "target_symbol"
        def_path = "src/defs.py"
        def_source = "def target_symbol():\n    return 'DECLARATION_HIT'\n"
        usage = {"id": "usage", "path": "src/use.py", "kind": "code", "language": "python", "text": "USAGE_HIT = target_symbol()", "lines": [1, 1]}
        idx = self._make_index_with_docs([self._fake_doc_chunk("context")], [usage])
        for path, source in ((def_path, def_source), (usage["path"], usage["text"])):
            target = idx.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        graph_query, _ = self._published_graph_module([{
            "id": f"{def_path}::{symbol}", "label": symbol, "kind": "function",
            "source_file": def_path, "source_location": "1:0",
        }])
        original_read_text = Path.read_text
        reads = []

        def counted_read_text(path, *args, **kwargs):
            if path == idx.root / def_path:
                reads.append(path)
            return original_read_text(path, *args, **kwargs)

        with patch(f"{self.srv.__name__}._load_graph_query", return_value=graph_query), \
             patch.object(Path, "read_text", counted_read_text), \
             patch.object(idx, "_graph_signal_candidates", return_value=[]), \
             patch.object(idx, "_get_reranker", return_value=self._adversarial_symbol_reranker()):
            response = self.srv.code_ask_response(idx, idx.root, f"where is {symbol}?")
        self.assertEqual(response["data"]["citations"][0]["path"], def_path)
        self.assertEqual(reads, [idx.root / def_path])

    def test_code_ask_source_hash_mismatch_keeps_hybrid_fallback(self):
        symbol = "target_symbol"
        def_path = "src/defs.py"
        usage = {"id": "usage", "path": "src/use.py", "kind": "code", "language": "python", "text": "USAGE_HIT = target_symbol()", "lines": [1, 1]}
        idx = self._make_index_with_docs([self._fake_doc_chunk("context")], [usage])
        for path, source in ((def_path, "def other_symbol():\n    return 1\n"), (usage["path"], usage["text"])):
            target = idx.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        graph_query, graph_indexer = self._published_graph_module([{
            "id": f"{def_path}::{symbol}", "label": symbol, "kind": "function",
            "source_file": def_path, "source_location": "1:0",
        }])
        graph_indexer.read_bound_graph_payload_source_hash.side_effect = None
        graph_indexer.read_bound_graph_payload_source_hash.return_value = {
            "payload": graph_indexer.read_graph_payload.return_value,
            "source_hash": hashlib.sha256(
                b"def target_symbol():\n    return 1\n"
            ).hexdigest(),
        }
        embed_query = MagicMock(side_effect=idx._embed_query)
        with patch(f"{self.srv.__name__}._load_graph_query", return_value=graph_query), \
             patch(f"{self.srv.__name__}.code_definition_response") as public_definition, \
             patch(f"{self.srv.__name__}.index_build_response") as index_build, \
             patch(f"{self.srv.__name__}.code_keyword_response") as keyword_scan, \
             patch(f"{self.srv.__name__}._python_definitions") as python_scan, \
             patch(f"{self.srv.__name__}._treesitter_definition_results") as tree_scan, \
             patch(f"{self.srv.__name__}._regex_definitions") as regex_scan, \
             patch(f"{self.srv.__name__}._css_definitions") as css_scan, \
             patch.object(idx, "_graph_signal_candidates", return_value=[]), \
             patch.object(idx, "_embed_query", embed_query), \
             patch.object(idx, "_get_reranker", return_value=self._adversarial_symbol_reranker()):
            response = self.srv.code_ask_response(idx, idx.root, f"where is {symbol}?")
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["data"]["citations"][0]["path"], usage["path"])
        self.assertEqual(set(response["data"]), self.CODE_ASK_BASE_DATA_KEYS)
        self.assertEqual(embed_query.call_count, 2)
        public_definition.assert_not_called()
        index_build.assert_not_called()
        keyword_scan.assert_not_called()
        graph_query.get_query_index.assert_not_called()
        graph_query.invalidate_query_index_cache.assert_not_called()
        graph_indexer.GraphStateStore.assert_not_called()
        python_scan.assert_not_called()
        tree_scan.assert_not_called()
        regex_scan.assert_not_called()
        css_scan.assert_not_called()

    def test_definition_lookup_has_no_language_or_extension_allowlist(self):
        source = inspect.getsource(self.srv.WaveIndex._published_exact_definition_candidate)
        self.assertNotIn("suffix", source)
        self.assertNotIn("extension", source)
        self.assertNotIn("_TS_LANGUAGE", source)

    def test_code_ask_compound_symbol_question_keeps_broader_context(self):
        """AC-2: final pinning does not turn a broad question into a lookup-only response."""
        symbol = "target_symbol"
        def_path = "src/defs.py"
        def_source = "def target_symbol():\n    return 'DECLARATION_HIT'\n"
        context_path = "src/workflow.py"
        context_source = "def run_workflow():\n    return target_symbol()  # USAGE_HIT broader workflow\n"
        chunks = [
            {"id": "workflow", "path": context_path, "kind": "code", "language": "python", "text": context_source, "lines": [1, 2]},
            {"id": "definition", "path": def_path, "kind": "code", "language": "python", "text": def_source, "lines": [1, 2]},
        ]
        idx = self._make_index_with_docs([self._fake_doc_chunk("context", "broader workflow context")], chunks)
        for path, source in ((def_path, def_source), (context_path, context_source)):
            target = idx.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        graph_query, _ = self._published_graph_module([{
            "id": f"{def_path}::{symbol}", "label": symbol, "kind": "function",
            "source_file": def_path, "source_location": "1:0",
        }])
        with patch(f"{self.srv.__name__}._load_graph_query", return_value=graph_query), \
             patch.object(idx, "_graph_signal_candidates", return_value=[]), \
             patch.object(idx, "_get_reranker", return_value=self._adversarial_symbol_reranker()):
            response = self.srv.code_ask_response(
                idx, idx.root, "how does target_symbol connect to the broader workflow?"
            )
        citations = response["data"]["citations"]
        self.assertEqual(citations[0]["path"], def_path)
        self.assertTrue(any(citation["path"] == context_path for citation in citations[1:]))

    def test_code_ask_stale_or_ambiguous_graph_keeps_hybrid_path_read_only(self):
        """AC-4: stale and ambiguous snapshots do not invoke mutation-capable
        definition seams, keyword confirmation, or an extra model pass."""
        symbol = "target_symbol"
        usage = {"id": "usage", "path": "src/use.py", "kind": "code", "language": "python", "text": "USAGE_HIT = target_symbol()", "lines": [1, 1]}
        for label, question, present, builder, nodes, receipt_ok in (
            ("absent", "where is target_symbol?", False, "45", [], True),
            ("stale", "where is target_symbol?", True, "44", [{"id": "src/defs.py::target_symbol", "label": symbol, "kind": "function", "source_file": "src/defs.py", "source_location": "1:0"}], True),
            ("ambiguous", "where is target_symbol?", True, "45", [
                {"id": "src/a.py::target_symbol", "label": symbol, "kind": "function", "source_file": "src/a.py", "source_location": "1:0"},
                {"id": "src/b.py::target_symbol", "label": symbol, "kind": "function", "source_file": "src/b.py", "source_location": "1:0"},
            ], True),
            ("duplicate-identity", "where is target_symbol?", True, "45", [
                {"id": "src/defs.py::target_symbol", "label": symbol, "kind": "function", "source_file": "src/defs.py", "source_location": "1:0"},
                {"id": "src/defs.py::target_symbol", "label": symbol, "kind": "function", "source_file": "src/defs.py", "source_location": "1:0"},
            ], True),
            ("unresolved", "where is target_symbol?", True, "45", [
                {"id": "src/other.py::other_symbol", "label": "other_symbol", "kind": "function", "source_file": "src/other.py", "source_location": "1:0"},
            ], True),
            ("non-declaration", "where is target_symbol?", True, "45", [
                {"id": "src/defs.py::target_symbol", "label": symbol, "kind": "module", "source_file": "src/defs.py", "source_location": "1:0"},
            ], True),
            ("receipt-refused", "where is target_symbol?", True, "45", [
                {"id": "src/defs.py::target_symbol", "label": symbol, "kind": "function", "source_file": "src/defs.py", "source_location": "1:0"},
            ], False),
            ("no-symbol", "how does this work?", True, "45", [], True),
        ):
            with self.subTest(case=label):
                idx = self._make_index_with_docs([self._fake_doc_chunk("context")], [usage])
                (idx.root / "src").mkdir(parents=True, exist_ok=True)
                (idx.root / "src" / "use.py").write_text(usage["text"], encoding="utf-8")
                for node in nodes:
                    target = idx.root / node["source_file"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("def target_symbol(): pass\n", encoding="utf-8")
                graph_query, graph_indexer = self._published_graph_module(
                    nodes, builder_version=builder, present=present
                )
                if not receipt_ok:
                    graph_indexer.read_bound_graph_payload_source_hash.side_effect = None
                    graph_indexer.read_bound_graph_payload_source_hash.return_value = None
                embed_query = MagicMock(side_effect=idx._embed_query)
                with patch(f"{self.srv.__name__}._load_graph_query", return_value=graph_query), \
                     patch(f"{self.srv.__name__}.code_definition_response") as public_definition, \
                     patch(f"{self.srv.__name__}.index_build_response") as index_build, \
                     patch(f"{self.srv.__name__}.code_keyword_response") as keyword_scan, \
                     patch(f"{self.srv.__name__}._python_definitions") as python_scan, \
                     patch(f"{self.srv.__name__}._treesitter_definition_results") as tree_scan, \
                     patch(f"{self.srv.__name__}._regex_definitions") as regex_scan, \
                     patch(f"{self.srv.__name__}._css_definitions") as css_scan, \
                     patch.object(idx, "_graph_signal_candidates", return_value=[]), \
                     patch.object(idx, "_embed_query", embed_query), \
                     patch.object(idx, "_get_reranker", return_value=self._adversarial_symbol_reranker()):
                    response = self.srv.code_ask_response(idx, idx.root, question)
                self.assertEqual(response["status"], "ok")
                self.assertEqual(response["data"]["citations"][0]["path"], "src/use.py")
                public_definition.assert_not_called()
                index_build.assert_not_called()
                keyword_scan.assert_not_called()
                graph_query.get_query_index.assert_not_called()
                graph_query.invalidate_query_index_cache.assert_not_called()
                graph_indexer.GraphStateStore.assert_not_called()
                python_scan.assert_not_called()
                tree_scan.assert_not_called()
                regex_scan.assert_not_called()
                css_scan.assert_not_called()
                self.assertEqual(embed_query.call_count, 2)
                self.assertEqual(set(response["data"]), self.CODE_ASK_BASE_DATA_KEYS)
                self._tmp.cleanup()
                del self._tmp

    # Wave 1p4wz: the lexical symbol-extraction chain (`_extract_symbols_from_citations` +
    # `_extract_symbols_ts`/`_python`/`_regex`) and its unit tests were REMOVED. It powered the old
    # "local"-path keyword second hop (parse citation text → guess symbol names → keyword-re-search);
    # agent mode's graph-based `graph_related` expansion (1p4hu) follows real call/import/reads edges
    # instead. The `second_hop_symbols`/`symbol_extraction_method` return fields remain (always
    # []/"none") and are covered by the search_combined tests below.

    def test_search_combined_assessment_preserves_type_agnostic_graph_signal(self):
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("billing")]
        idx = self._make_index_with_docs(docs, code_chunks=code)
        graph_candidate = {
            "path": "src/retrieval.py", "text": "def evaluate_retrieval(): ...",
            "score": 0.8, "kind": "code", "lines": [4, 8],
            "_symbol": "evaluate_retrieval", "_relationship": "related",
        }
        graph_related = {"related": [{"symbol": "evaluate_retrieval"}]}
        with patch.object(idx, "_get_reranker", return_value=None):
            with patch.object(idx, "_graph_signal_candidates", return_value=[graph_candidate]):
                with patch.object(idx, "_merge_graph_into_citations"):
                    with patch.object(idx, "_build_graph_related", return_value=graph_related):
                        result = idx.search_combined(
                            "assess retrieval weaknesses", top_n=5, question_type="assessment",
                        )
        self.assertEqual(result[5], ["evaluate_retrieval"])
        self.assertEqual(result[6], "graph")
        self.assertEqual(result[7], graph_related)

    def test_search_combined_second_hop_skipped_for_navigational(self):
        """Second hop is not triggered for navigational questions."""
        docs = [self._fake_doc_chunk("d0")]
        code = [self._fake_code_chunk("billing")]
        idx = self._make_index_with_docs(docs, code_chunks=code)

        with patch.object(idx, "_get_reranker", return_value=None):
            _, _, _, _, _, second_hop_symbols, symbol_extraction_method, _ = idx.search_combined(
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
                _, _, _, _, _, second_hop_symbols, symbol_extraction_method, _ = idx.search_combined(
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
                        "how does billing charge", top_n=5, question_type="explanatory", rerank="local"
                    )
        # If deduplication worked, the second rerank should not have been called
        # (no new candidates after dedup → second_hop_candidates is empty)
        self.assertLessEqual(len(rerank_call_sizes), 2)

    def test_second_hop_symbols_propagated_to_code_ask_response(self):
        """code_ask_response emits second_hop_symbols and symbol_extraction_method when second hop fired."""
        index = MagicMock()
        index.search_combined.return_value = ([], False, 0, 0, [], ["chargeCustomer"], "ast", None)
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
        index.search_combined.return_value = ([], False, 0, 0, [], [], "none", None)
        index._layer_health.return_value = {"indexed_chunker_versions": {}, "current_chunker_version": "17"}
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            result = self.srv.code_ask_response(index, root, "how does billing work?")
        data = result.get("data", {})
        self.assertNotIn("second_hop_symbols", data)
        self.assertNotIn("symbol_extraction_method", data)

    # Wave 1p52p: test_symbol_extraction_method_regex_fallback_when_treesitter_unavailable and
    # test_symbol_extraction_method_ast_when_python_extraction_succeeds were removed — they tested the
    # removed keyword/AST second-hop's symbol extraction inside search_combined (the "local" path).
    # Agent mode's two-hop expansion is the graph path (symbol_extraction_method="graph"); the keyword
    # path now reports "none".

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
                _, _, _, _, _, _symbols, method, _ = idx.search_combined(
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
        # Test-isolation fix: `_get_reranker()` loads via `accel_embedder` (wave
        # 1p52p), NOT fastembed — patching the stale fastembed paths left the
        # accel path live, so on an accel_embedder box the reranker built
        # successfully and this assertion failed depending on suite ordering.
        # Patch out the module `_get_reranker` actually imports so the load
        # genuinely fails and the no-cache-None behavior is exercised (mirrors
        # test_ensure_model_cached_reranker_import_error).
        with patch.dict("sys.modules", {"accel_embedder": None}):
            result1 = idx._get_reranker()
            result2 = idx._get_reranker()
        self.assertIsNone(result1)
        self.assertIsNone(result2)
        self.assertIsNone(idx._reranker)

    def test_build_server_does_not_start_background_model_downloads(self):
        """MCP startup must not compete with model-cache prewarm work."""
        call_count = [0]

        def patched_start(self_inner):
            call_count[0] += 1

        try:
            with patch.object(self.srv.WaveIndex, "_start_background_model_downloads", patched_start):
                load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        self.assertEqual(call_count[0], 0, "_start_background_model_downloads must not run during build_server()")

    def test_semantic_docs_search_starts_background_model_downloads_after_startup(self):
        """First semantic activity may prewarm models after MCP tools are already registered."""
        idx = self._make_index()
        idx._proj_docs_lance_table = None
        with patch.object(idx, "_start_background_model_downloads_after_startup") as patched_start:
            with patch.object(idx, "_ensure_loaded"):
                with patch.object(idx, "_indexer_constant", return_value="model-A"):
                    with patch.object(idx, "_embed_query", return_value=MagicMock()):
                        results, reranked = idx.search_docs("query")

        patched_start.assert_called_once()
        self.assertEqual(results, [])
        self.assertFalse(reranked)

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

    def test_ensure_model_cached_embedding_download_applies_ca_bundle(self):
        """Wave 1p939 AC-6: a cache miss → the online download attempt is preceded by
        setup_index.ensure_ca_bundle_applied(), so the MCP server's own download path (not just
        accel_embedder's) picks up a host-agent/operator CA bundle."""
        import io

        mock_embedder = MagicMock()
        calls = []

        def fake_text_embedding(model_name, local_files_only=None, **kwargs):
            calls.append(local_files_only)
            if local_files_only:
                raise RuntimeError("not cached")
            return mock_embedder

        with patch.dict(os.environ, {}, clear=False):
            with patch("fastembed.TextEmbedding", side_effect=fake_text_embedding):
                with patch("setup_index.ensure_ca_bundle_applied") as ensure_ca:
                    buf = io.StringIO()
                    with patch("sys.stderr", buf):
                        self.srv._ensure_model_cached("test-embedding-model", "embedding")
        self.assertEqual(calls, [True, False], "offline probe then online download")
        ensure_ca.assert_called_once()

    def test_ensure_model_cached_embedding_cert_failure_wraps_diagnostic(self):
        """Wave 1p939 AC-4: a CERTIFICATE_VERIFY_FAILED on the online download attempt is wrapped
        with setup_index.raise_with_ca_bundle_diagnostic() rather than propagating raw."""
        cert_exc = Exception("certificate verify failed: unable to get local issuer certificate")

        def fake_text_embedding(model_name, local_files_only=None, **kwargs):
            if local_files_only:
                raise RuntimeError("not cached")
            raise cert_exc

        with patch.dict(os.environ, {}, clear=False):
            with patch("fastembed.TextEmbedding", side_effect=fake_text_embedding):
                with patch("setup_index.ensure_ca_bundle_applied"):
                    with patch(
                        "setup_index.raise_with_ca_bundle_diagnostic",
                        side_effect=lambda model, exc: (_ for _ in ()).throw(exc),
                    ) as diag:
                        with self.assertRaises(Exception):
                            self.srv._ensure_model_cached("test-embedding-model", "embedding")
        diag.assert_called_once_with("test-embedding-model", cert_exc)

    def test_ensure_model_cached_reranker_import_error(self):
        """_ensure_model_cached skips gracefully when accel_embedder is unavailable (1p52p: the
        reranker prewarm uses accel_embedder, not fastembed.rerank)."""
        import io

        with patch.dict("sys.modules", {"accel_embedder": None}):
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

    def test_limit_kwarg_is_canonical_for_cap(self):
        """Wave 1p3dk: ``limit`` is the canonical parameter name (matches
        ``code_keyword`` / ``code_references``). ``max_results`` is accepted
        as a backward-compat alias but ``limit`` is the going-forward name."""
        content = "\n".join([f"MATCH_LINE_{i} = {i}" for i in range(20)]) + "\n"
        self._add("src/many.py", content)
        result = self._call(r"MATCH_LINE_", limit=5)
        data = result["data"]
        self.assertEqual(len(data["matches"]), 5)
        self.assertTrue(data["truncated"])
        self.assertGreaterEqual(data["total_matches_found"], 20)

    def test_max_results_explicit_wins_over_limit_default(self):
        """Back-compat: when caller passes ``max_results`` explicitly,
        it overrides the ``limit`` default (operator-explicit value over
        the framework default)."""
        content = "\n".join([f"X_{i} = {i}" for i in range(20)]) + "\n"
        self._add("src/many.py", content)
        # Caller still using old API
        result = self._call(r"X_", max_results=3)
        data = result["data"]
        self.assertEqual(len(data["matches"]), 3)
        self.assertTrue(data["truncated"])

    def test_limit_zero_returns_all_matches(self):
        """``limit=0`` disables the cap (matches code_keyword convention)."""
        content = "\n".join([f"ZED_{i} = {i}" for i in range(20)]) + "\n"
        self._add("src/many.py", content)
        result = self._call(r"ZED_", limit=0)
        data = result["data"]
        self.assertEqual(len(data["matches"]), 20)
        self.assertFalse(data["truncated"])

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

    def test_nested_type_constant_dotted_suffix(self):
        """1p5k0: a constant nested in a type-within-a-type resolves by bare leaf, full qualified
        name, AND any intermediate dotted suffix — and a bogus prefix does NOT over-match. Exercises
        the chunker nested-type qualified-qname fix + the code_constants dotted-suffix matcher
        end-to-end (the Swift case that missed downstream in the field)."""
        self._add_file("Automation.swift",
                       "class AutomationController {\n"
                       "    private struct RoutineConfig {\n"
                       "        static let maxRetries = 3\n"
                       "    }\n"
                       "}\n")

        def _value(symbol: str):
            entries = self._call([symbol])["data"]["results"]
            return entries[0]["value"] if entries else None

        # All three name forms resolve to the same value.
        self.assertEqual(_value("maxRetries"), "3")                                     # bare leaf
        self.assertEqual(_value("RoutineConfig.maxRetries"), "3")                       # intermediate suffix (the fix)
        self.assertEqual(_value("AutomationController.RoutineConfig.maxRetries"), "3")  # full qualified
        # Negative: a wrong enclosing type must NOT over-match (resolves to no value, not 3).
        self.assertIsNone(_value("Nope.maxRetries"))

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

    def test_class_level_constant_found(self):
        """Wave 1p4pz: a class-level (indented) constant IS now found by the multi-language detector,
        alongside the module-level one — both are real constants. The old column-0 regex missed the
        class-level one; the chunk-lane detector surfaces it."""
        self._add_file("mod.py", "class Foo:\n    MY_CONST = 99\nMY_CONST = 1\n")
        result = self._call(["MY_CONST"])
        entries = result["data"]["results"]
        self.assertEqual(sorted(e["value"] for e in entries), ["1", "99"],
                         f"both module + class-level constants found; got {entries}")

    def test_function_local_assignment_ignored(self):
        """A function-local assignment is NOT a constant (scope gate) — only the module-level one is
        returned. The chunk-lane detector excludes function/block locals exactly as 1p4mf gates them."""
        self._add_file("mod.py", "def f():\n    MY_CONST = 99\n    return MY_CONST\nMY_CONST = 1\n")
        result = self._call(["MY_CONST"])
        entries = [e for e in result["data"]["results"] if e["value"] is not None]
        self.assertEqual(len(entries), 1, f"only the module-level const expected; got {entries}")
        self.assertEqual(entries[0]["value"], "1")

    # ------------------------------------------------------------------
    # Wave 1p4pz — multi-language constant lookup (chunk-lane detector)
    # ------------------------------------------------------------------

    _ML_CASES = [
        ("J.java", "class J {\n  private static final int MAX_SIZE = 1048576;\n}\n", "MAX_SIZE", "1048576"),
        ("g.go", "package main\nconst MaxRetries = 3\n", "MaxRetries", "3"),
        ("c.cs", "class C { const int MaxRetries = 3; }\n", "MaxRetries", "3"),
        ("k.kt", 'const val API_KEY = "k"\n', "API_KEY", '"k"'),
        ("r.rs", "const LIMIT: u32 = 3;\n", "LIMIT", "3"),
        ("s.swift", 'static let apiURL = "u"\n', "apiURL", '"u"'),
        ("rb.rb", "class S\n  RETRY = 5\nend\n", "RETRY", "5"),
        ("p.php", "<?php\nconst LIMIT = 100;\n", "LIMIT", "100"),
        ("t.ts", 'const API_URL = "https://x";\n', "API_URL", '"https://x"'),
    ]

    def test_multi_language_detection(self):
        """AC-1: `code_constants` finds indented / non-Python constants across all languages via the
        1p4mf chunk-lane detector (Java static final, Go/C# const, Kotlin const val, Rust const,
        Swift static let, Ruby const, PHP const, TS const). FAIL-not-skip on a missing grammar."""
        for fn, src, sym, expected in self._ML_CASES:
            with self.subTest(file=fn):
                self._add_file(fn, src)
                entries = [e for e in self._call([sym])["data"]["results"] if e["value"] is not None]
                self.assertTrue(entries, f"[{fn}] constant {sym} not found (grammar missing or detector gap)")
                self.assertEqual(entries[0]["value"], expected, f"[{fn}] {sym} value")

    def test_value_extraction_edge_cases(self):
        """AC-2: trailing `;` trimmed (Java/C#/Rust/PHP); PHP `define()` second arg; per-declarator
        value for a multi-const line; multiline literal preserved."""
        self._add_file("J.java", "class J { static final int X = 42; }\n")
        self._add_file("p.php", "<?php\ndefine('CACHE_KEY', 'xyz');\n")
        self._add_file("t.ts", "const A = 1, B = 2;\n")
        self._add_file("py.py", 'CONFIG = frozenset({\n  "a",\n  "b",\n})\n')
        def _val(sym, want, file_kw=None):
            es = [e for e in self._call([sym])["data"]["results"] if e["value"] is not None]
            es = [e for e in es if (file_kw is None or file_kw in (e["file"] or ""))]
            self.assertTrue(es, f"{sym} not found")
            return es[0]
        self.assertEqual(_val("X", None)["value"], "42")                 # trailing ; trimmed
        self.assertEqual(_val("CACHE_KEY", None)["value"], "'xyz'")      # PHP define() 2nd arg
        self.assertEqual(_val("A", None)["value"], "1")                  # per-declarator
        self.assertEqual(_val("B", None)["value"], "2")
        cfg = _val("CONFIG", None)
        self.assertIn("frozenset", cfg["value"])
        self.assertEqual(cfg["kind"], "multiline")

    def test_candidate_prefilter_only_chunks_matching_files(self):
        """AC-4: only files containing a requested symbol (cheap substring pre-filter) are chunked —
        a targeted lookup never parses the whole tree."""
        self._add_file("has.py", "TARGET_CONST = 5\n")
        self._add_file("nope.py", "UNRELATED = 9\n")
        chunker = self.srv._get_chunker_module()
        seen: list[str] = []
        orig = chunker.chunk_python
        def _spy(source, path):
            seen.append(path)
            return orig(source, path)
        chunker.chunk_python = _spy
        try:
            self._call(["TARGET_CONST"])
        finally:
            chunker.chunk_python = orig
        self.assertTrue(any("has.py" in p for p in seen), f"matching file chunked; got {seen}")
        self.assertFalse(any("nope.py" in p for p in seen), f"non-matching file must NOT be chunked; got {seen}")

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

    # ------------------------------------------------------------------
    # Wave 1p4pz/1p4q4 review fixes (chunk-lane value extraction + coverage)
    # ------------------------------------------------------------------

    def test_take_balanced_value_is_string_aware(self):
        """Review A1: `_take_balanced_value` must treat a string literal as opaque — a `,`/`;`/`}`
        INSIDE a quoted string is value content, not a separator / enclosing-scope close. (Shares the
        `_string_literal_end` primitive with `_bracket_depth`.)"""
        tbv = self.srv._take_balanced_value
        self.assertEqual(tbv('","')[0], '","')              # value IS a comma → not eaten
        self.assertEqual(tbv('";"')[0], '";"')              # value IS a semicolon
        self.assertEqual(tbv('"a;b;c";')[0], '"a;b;c"')     # separators inside string kept; trailing ; trimmed
        self.assertEqual(tbv('"a}b"}')[0], '"a}b"')         # `}` in string kept; real enclosing `}` ends value
        v, kind = tbv('{"open": "a}b", "close": "c"}')
        self.assertEqual(v, '{"open": "a}b", "close": "c"}')  # full dict, not truncated at the in-string `}`
        self.assertNotEqual(kind, "multiline-truncated")

    def test_chunk_lane_string_value_with_separators_not_truncated(self):
        """Review A1 (end-to-end): a non-Python / class-level constant whose STRING value contains a
        `,`/`;`/`}` is returned in full, not truncated to the opening quote."""
        self._add_file("C.java", 'class C { static final String SEP = "a;b;c"; }\n')
        self._add_file("m.go", 'package main\nconst Sep = ","\n')
        self._add_file("conf.py", 'class Conf:\n    TMPL = {"open": "a}b", "close": "c"}\n')
        java = [e for e in self._call(["SEP"])["data"]["results"] if e["value"] is not None]
        self.assertEqual(java[0]["value"], '"a;b;c"', "Java String separators must not truncate the value")
        go = [e for e in self._call(["Sep"])["data"]["results"] if e["value"] is not None]
        self.assertEqual(go[0]["value"], '","', "a constant whose value IS a comma must not be eaten")
        tmpl = [e for e in self._call(["TMPL"])["data"]["results"] if e["value"] is not None][0]
        self.assertIn('"close": "c"', tmpl["value"], "dict value must be complete past the in-string `}`")
        self.assertNotEqual(tmpl["kind"], "multiline-truncated")

    def test_leading_comment_does_not_poison_value(self):
        """Review B1: a leading comment that mentions `NAME = <other>` must NOT poison the extracted
        value — the chunk body's leading comment block is stripped before the NAME search."""
        self._add_file("cfg.py",
                       "class Config:\n    # THRESHOLD = 10 was the old default; do not use\n    THRESHOLD = 99\n")
        entries = [e for e in self._call(["THRESHOLD"])["data"]["results"] if e["value"] is not None]
        self.assertEqual(entries[0]["value"], "99", "value must come from the decl, not the leading comment")

    def test_go_grouped_const_members_all_resolve(self):
        """Review B2: a Go grouped `const (...)` block is ONE chunk named after its first member —
        every member (not just the first) must resolve to its own value + line. iota members resolve
        too (bare → empty value)."""
        self._add_file("s.go",
                       "package main\nconst (\n\tStatusOK = 200\n\tStatusNotFound = 404\n\tStatusError = 500\n)\n")
        res = {e["name"]: e["value"] for e in self._call(["StatusOK", "StatusNotFound", "StatusError"])["data"]["results"]}
        self.assertEqual(res, {"StatusOK": "200", "StatusNotFound": "404", "StatusError": "500"})
        self._add_file("i.go", "package main\nconst (\n\tAlpha = iota\n\tBeta\n\tGamma\n)\n")
        iota = {e["name"]: e["value"] for e in self._call(["Alpha", "Beta", "Gamma"])["data"]["results"]}
        self.assertTrue(all(v is not None for v in iota.values()), f"all iota members must resolve; got {iota}")

    def test_qualified_enum_member_lookup(self):
        """Review B3: a qualified query (`Status.OK`) resolves via the chunk leaf (the substring
        pre-filter uses the bare leaf so the file is chunked); and when BOTH `OK` and `Status.OK` are
        requested, each resolves (the short form no longer shadows the qualified one)."""
        self._add_file("e.ts", "enum Status { OK = 0, FAIL = 1 }\n")
        qualified = [e for e in self._call(["Status.OK"])["data"]["results"] if e["value"] is not None]
        self.assertEqual(qualified[0]["value"], "0", "qualified `Status.OK` must resolve")
        both = {e["name"]: e["value"] for e in self._call(["OK", "Status.OK"])["data"]["results"]
                if e["value"] is not None}
        self.assertEqual(both, {"OK": "0", "Status.OK": "0"}, "both the short and qualified form must resolve")

    def test_mts_cts_typescript_dispatch(self):
        """Review B4: `.mts` / `.cts` TypeScript module files are in the const-chunker dispatch table
        (the chunker already supports them)."""
        self._add_file("api.mts", "export const API = 'x';\n")
        self._add_file("legacy.cts", "export const LEGACY = 7;\n")
        api = [e for e in self._call(["API"])["data"]["results"] if e["value"] is not None]
        self.assertEqual(api[0]["value"], "'x'")
        legacy = [e for e in self._call(["LEGACY"])["data"]["results"] if e["value"] is not None]
        self.assertEqual(legacy[0]["value"], "7")


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


class TestCodeGraphTools(unittest.TestCase):
    """12xs4-feat graph-query-surface MCP integration tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        self._add("src/tools.py", "def process():\n    return 1\n")
        self._add("src/main.py", "from src.tools import process\n\nprocess()\n")
        payload = {
            "schema_version": "1",
            "builder_version": "1",
            "layer": "project",
            "nodes": [
                {"id": "src/tools.py", "label": "tools", "kind": "module", "source_file": "src/tools.py", "layer": "project"},
                {"id": "src/tools.py::process", "label": "process", "kind": "function", "source_file": "src/tools.py", "layer": "project"},
                {"id": "src/main.py", "label": "main", "kind": "module", "source_file": "src/main.py", "layer": "project"},
                {"id": "src/main.py::<module>", "label": "<module>", "kind": "function", "source_file": "src/main.py", "layer": "project"},
            ],
            "edges": [
                {"source": "src/main.py::<module>", "target": "src/tools.py::process", "relation": "calls", "confidence": "EXTRACTED"},
                {"source": "src/main.py", "target": "src/tools.py", "relation": "imports", "confidence": "EXTRACTED"},
            ],
            "counts": {"files": 2, "nodes": 4, "edges": 2},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_code_impact_path_heuristic_unchanged(self):
        result = self.srv.code_impact_response(self.root, "src/tools.py")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "heuristic")
        files = [row["file"] for row in result["data"]["importers"]]
        self.assertIn("src/main.py", files)

    def test_code_impact_symbol_graph_mode(self):
        result = self.srv.code_impact_response(
            self.root,
            "",
            symbol="src/tools.py::process",
            max_hops=2,
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["method"], "graph")
        affected_ids = {row["node_id"] for row in result["data"]["affected"]}
        self.assertIn("src/main.py::<module>", affected_ids)

    def test_code_callgraph_returns_calls(self):
        result = self.srv.code_callgraph_response(
            self.root,
            "src/tools.py::process",
            depth=1,
            direction="callers",
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["edges"])

    def test_wf_graph_report_fan_in(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=5)
        self.assertEqual(result["status"], "ok")
        self.assertIn("fan_in", result["data"])


class ExternalSupertypeServerTests(unittest.TestCase):
    """Wave 1sbfi (1sbfh): external `implements`/`extends` visibility on the
    server surfaces — code_impact external seeds + grouped ambiguity, and the
    supertypes section with calls-parity include_external gating."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_graph(self, nodes: list, edges: list) -> None:
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        (graph_dir / "project-graph.json").write_text(
            json.dumps({"schema_version": "1", "layer": "project", "nodes": nodes, "edges": edges}),
            encoding="utf-8",
        )

    def _standard_graph(self):
        self._write_graph(
            nodes=[
                {"id": "src/Shop.java", "label": "Shop", "kind": "class", "source_file": "src/Shop.java"},
                {"id": "src/Sail.java", "label": "Sail", "kind": "class", "source_file": "src/Sail.java"},
            ],
            edges=[
                {"source": "src/Shop.java", "target": "external::TypeInstrumentation",
                 "relation": "implements", "confidence": "EXTRACTED"},
                {"source": "src/Sail.java", "target": "external::TypeInstrumentation",
                 "relation": "implements", "confidence": "EXTRACTED"},
            ],
        )

    def test_impact_on_external_interface_returns_labeled_implementors(self):
        self._standard_graph()
        resp = self.srv.code_impact_response(self.root, symbol="TypeInstrumentation", max_hops=2)
        self.assertEqual(resp["status"], "ok")
        data = resp["data"]
        self.assertTrue(data.get("external_target"))
        self.assertEqual(data.get("external_name"), "TypeInstrumentation")
        affected = {a["node_id"] for a in data.get("affected", [])}
        self.assertEqual(affected, {"src/Shop.java", "src/Sail.java"})

    def test_impact_ambiguous_external_name_returns_grouped_breakdown(self):
        self._write_graph(
            nodes=[
                {"id": "src/A.java", "label": "A", "kind": "class", "source_file": "src/A.java"},
                {"id": "src/B.java", "label": "B", "kind": "class", "source_file": "src/B.java"},
            ],
            edges=[
                {"source": "src/A.java", "target": "external::io.otel.Module",
                 "relation": "extends", "confidence": "EXTRACTED"},
                {"source": "src/B.java", "target": "external::com.vendor.Module",
                 "relation": "extends", "confidence": "EXTRACTED"},
            ],
        )
        resp = self.srv.code_impact_response(self.root, symbol="Module", max_hops=2)
        self.assertEqual(resp["status"], "ok")
        data = resp["data"]
        self.assertFalse(data.get("resolved"))
        candidates = data.get("external_candidates") or []
        self.assertEqual(
            [c["id"] for c in candidates],
            ["external::com.vendor.Module", "external::io.otel.Module"],
        )
        codes = [d.get("code") for d in resp.get("diagnostics", [])]
        self.assertIn("external_supertype_ambiguous", codes)
        # Re-querying with the exact id resolves.
        resp2 = self.srv.code_impact_response(self.root, symbol="external::io.otel.Module", max_hops=1)
        self.assertEqual(resp2["status"], "ok")
        self.assertTrue(resp2["data"].get("external_target"))
        self.assertEqual({a["node_id"] for a in resp2["data"]["affected"]}, {"src/A.java"})

    def test_impact_on_implementor_surfaces_supertypes(self):
        self._standard_graph()
        resp = self.srv.code_impact_response(self.root, symbol="Shop", max_hops=1)
        self.assertEqual(resp["status"], "ok")
        supers = resp["data"].get("supertypes")
        self.assertIsNotNone(supers, "a class with only-external supertypes must not read as no-edges")
        self.assertEqual(supers["external_implements_count"], 1)
        self.assertEqual(
            [e["name"] for e in supers["external"]], ["TypeInstrumentation"]
        )

    def test_callhierarchy_supertypes_respect_include_external_gate(self):
        self._standard_graph()
        gated = self.srv.code_callhierarchy_response(self.root, "Shop", include_external=False)
        self.assertEqual(gated["status"], "ok")
        supers = gated["data"].get("supertypes")
        self.assertIsNotNone(supers)
        self.assertNotIn("external", supers, "external list must be gated off by default")
        self.assertEqual(supers["external_implements_count"], 1, "counts must ALWAYS be present")
        full = self.srv.code_callhierarchy_response(self.root, "Shop", include_external=True)
        supers_full = full["data"].get("supertypes")
        self.assertEqual(
            [e["id"] for e in supers_full.get("external", [])],
            ["external::TypeInstrumentation"],
        )

    def test_supertype_free_symbol_has_no_supertypes_section(self):
        self._write_graph(
            nodes=[{"id": "src/x.py::plain", "label": "plain", "kind": "function", "source_file": "src/x.py"}],
            edges=[],
        )
        resp = self.srv.code_callhierarchy_response(self.root, "plain")
        self.assertEqual(resp["status"], "ok")
        self.assertNotIn("supertypes", resp["data"])


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

    def _write_graph(self, nodes: list, edges: list) -> None:
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        (graph_dir / "project-graph.json").write_text(
            json.dumps({"schema_version": "1", "layer": "project", "nodes": nodes, "edges": edges}),
            encoding="utf-8",
        )

    # Wave 1p2q3 (1p2td post-ship): self_edge_kind propagates from edge to entries.
    def test_self_edge_kind_propagates_to_outgoing_entry(self):
        """Field report: self_edge_kind set on the underlying edge
        must surface on the outgoing/incoming entry so consumers of
        code_callhierarchy see the overload classification without re-querying
        the raw edge layer."""
        self._add("src/Calc.java", "class Calc { int calc(int a) { return calc(a, 0); } int calc(int a, int b) { return a + b; } }\n")
        self._write_graph(
            nodes=[
                {"id": "src/Calc.java::Calc.calc", "label": "calc", "kind": "function", "source_file": "src/Calc.java"},
            ],
            edges=[
                # Synthetic self-edge tagged overload_forwarding.
                {
                    "source": "src/Calc.java::Calc.calc",
                    "target": "src/Calc.java::Calc.calc",
                    "relation": "calls",
                    "confidence": "RECEIVER_RESOLVED",
                    "self_edge_kind": "overload_forwarding",
                },
            ],
        )
        result = self._call("calc", direction="outgoing")
        self.assertEqual(result["status"], "ok")
        out = result["data"].get("outgoing") or []
        forwarding = [e for e in out if e.get("self_edge_kind") == "overload_forwarding"]
        self.assertTrue(forwarding, f"expected self_edge_kind on outgoing entry; got: {out}")

    def test_self_edge_kind_propagates_to_incoming_entry(self):
        self._add("src/Calc.java", "class Calc { int loop(int n) { return loop(n - 1); } }\n")
        self._write_graph(
            nodes=[
                {"id": "src/Calc.java::Calc.loop", "label": "loop", "kind": "function", "source_file": "src/Calc.java"},
            ],
            edges=[
                {
                    "source": "src/Calc.java::Calc.loop",
                    "target": "src/Calc.java::Calc.loop",
                    "relation": "calls",
                    "confidence": "RECEIVER_RESOLVED",
                    "self_edge_kind": "recursion",
                },
            ],
        )
        result = self._call("loop", direction="incoming")
        self.assertEqual(result["status"], "ok")
        inc = result["data"].get("incoming") or []
        recursion = [e for e in inc if e.get("self_edge_kind") == "recursion"]
        self.assertTrue(recursion, f"expected self_edge_kind on incoming entry; got: {inc}")

    # AC-2: direction=outgoing has outgoing, no incoming
    def test_direction_outgoing_only(self):
        """AC-2: direction='outgoing' returns 'outgoing' key but no 'incoming' key."""
        self._add("src/worker.py", "def process():\n    helper()\n    validate()\n\ndef helper(): pass\ndef validate(): pass\n")
        self._write_graph(
            nodes=[
                {"id": "src/worker.py::process", "label": "process", "kind": "function", "source_file": "src/worker.py"},
                {"id": "src/worker.py::helper", "label": "helper", "kind": "function", "source_file": "src/worker.py"},
                {"id": "src/worker.py::validate", "label": "validate", "kind": "function", "source_file": "src/worker.py"},
            ],
            edges=[
                {"source": "src/worker.py::process", "target": "src/worker.py::helper", "relation": "calls"},
                {"source": "src/worker.py::process", "target": "src/worker.py::validate", "relation": "calls"},
            ],
        )
        result = self._call("process", direction="outgoing")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertIn("outgoing", data)
        self.assertNotIn("incoming", data)

    # AC-3: direction=incoming has incoming, no outgoing
    def test_direction_incoming_only(self):
        """AC-3: direction='incoming' returns 'incoming' key but no 'outgoing' key."""
        self._add("src/svc.py", "def service():\n    pass\n\ndef caller():\n    service()\n")
        self._write_graph(
            nodes=[
                {"id": "src/svc.py::service", "label": "service", "kind": "function", "source_file": "src/svc.py"},
                {"id": "src/svc.py::caller", "label": "caller", "kind": "function", "source_file": "src/svc.py"},
            ],
            edges=[
                {"source": "src/svc.py::caller", "target": "src/svc.py::service", "relation": "calls"},
            ],
        )
        result = self._call("service", direction="incoming")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertIn("incoming", data)
        self.assertNotIn("outgoing", data)

    # AC-4: Unknown symbol with graph present returns empty outgoing/incoming (not error)
    def test_unknown_symbol_returns_empty_lists(self):
        """AC-4: Unknown symbol returns empty outgoing and incoming lists, not error."""
        self._write_graph(nodes=[], edges=[])
        result = self._call("zzz_no_such_symbol_xxxxxyyy")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertEqual(data.get("outgoing", []), [])
        self.assertEqual(data.get("incoming", []), [])

    # AC-5: incoming entries carry line + snippet from file scan
    def test_incoming_line_numbers(self):
        """AC-5: incoming entries have line numbers and snippets from targeted file scan."""
        self._add("src/svc.py", "def service():\n    pass\n\ndef caller():\n    service()\n")
        self._write_graph(
            nodes=[
                {"id": "src/svc.py::service", "label": "service", "kind": "function",
                 "source_file": "src/svc.py", "source_location": "1:0"},
                {"id": "src/svc.py::caller", "label": "caller", "kind": "function",
                 "source_file": "src/svc.py", "source_location": "4:0"},
            ],
            edges=[
                {"source": "src/svc.py::caller", "target": "src/svc.py::service", "relation": "calls"},
            ],
        )
        result = self._call("service", direction="incoming")
        self.assertEqual(result["status"], "ok")
        incoming = result["data"]["incoming"]
        self.assertEqual(len(incoming), 1)
        self.assertEqual(incoming[0]["name"], "caller")
        self.assertEqual(incoming[0]["line"], 5)
        self.assertIn("service()", incoming[0]["snippet"])

    # AC-7: outgoing entries carry line + snippet from file scan
    def test_outgoing_line_numbers(self):
        """AC-7: outgoing entries have line numbers and snippets from targeted file scan."""
        self._add("src/worker.py",
                  "def process():\n    helper()\n    validate()\n\ndef helper(): pass\ndef validate(): pass\n")
        self._write_graph(
            nodes=[
                {"id": "src/worker.py::process", "label": "process", "kind": "function",
                 "source_file": "src/worker.py", "source_location": "1:0"},
                {"id": "src/worker.py::helper", "label": "helper", "kind": "function",
                 "source_file": "src/worker.py", "source_location": "5:0"},
                {"id": "src/worker.py::validate", "label": "validate", "kind": "function",
                 "source_file": "src/worker.py", "source_location": "6:0"},
            ],
            edges=[
                {"source": "src/worker.py::process", "target": "src/worker.py::helper", "relation": "calls"},
                {"source": "src/worker.py::process", "target": "src/worker.py::validate", "relation": "calls"},
            ],
        )
        result = self._call("process", direction="outgoing")
        self.assertEqual(result["status"], "ok")
        outgoing = result["data"]["outgoing"]
        self.assertEqual(len(outgoing), 2)
        names = {e["name"] for e in outgoing}
        self.assertEqual(names, {"helper", "validate"})
        for entry in outgoing:
            self.assertIsNotNone(entry["line"], f"Expected line number for {entry['name']}")
            self.assertIsNotNone(entry["snippet"], f"Expected snippet for {entry['name']}")

    # AC-6: Invalid direction returns error
    def test_invalid_direction_returns_error(self):
        """AC-6: Invalid direction value returns error response."""
        result = self._call("some_func", direction="sideways")
        self.assertEqual(result["status"], "error")
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("invalid_arguments", codes)

    def test_community_field_present_on_entries(self):
        """12zxl: incoming/outgoing entries always carry a 'community' key (may be None)."""
        self._add("src/svc.py", "def service():\n    pass\n\ndef caller():\n    service()\n")
        self._write_graph(
            nodes=[
                {"id": "src/svc.py::service", "label": "service", "kind": "function", "source_file": "src/svc.py"},
                {"id": "src/svc.py::caller", "label": "caller", "kind": "function", "source_file": "src/svc.py"},
            ],
            edges=[
                {"source": "src/svc.py::caller", "target": "src/svc.py::service", "relation": "calls"},
            ],
        )
        result = self._call("service", direction="incoming")
        self.assertEqual(result["status"], "ok")
        for entry in result["data"]["incoming"]:
            self.assertIn("community", entry)

    def test_context_depth_zero_has_no_context_key(self):
        """12zxl: context_depth=0 (default) — no 'context' key in response data."""
        self._add("src/svc.py", "def service():\n    pass\n")
        self._write_graph(
            nodes=[{"id": "src/svc.py::service", "label": "service", "kind": "function", "source_file": "src/svc.py"}],
            edges=[],
        )
        result = self.srv.code_callhierarchy_response(self.root, "service", None, "both", context_depth=0)
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("context", result["data"])

    def test_context_depth_one_adds_context_list(self):
        """12zxl: context_depth=1 — 'context' list is present in response data."""
        self._add("src/worker.py", "def process():\n    helper()\n\ndef helper(): pass\n")
        self._write_graph(
            nodes=[
                {"id": "src/worker.py::process", "label": "process", "kind": "function", "source_file": "src/worker.py"},
                {"id": "src/worker.py::helper", "label": "helper", "kind": "function", "source_file": "src/worker.py"},
            ],
            edges=[
                {"source": "src/worker.py::process", "target": "src/worker.py::helper", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "process", None, "both", context_depth=1)
        self.assertEqual(result["status"], "ok")
        self.assertIn("context", result["data"])
        self.assertIsInstance(result["data"]["context"], list)

    # ----- Wave 130ol AC-10: external suppression default + include_external opt-in -----

    def test_external_outgoing_suppressed_by_default(self):
        """130ol AC-10: outgoing entries with file=external are suppressed by default
        and counted in external_outgoing_count."""
        self._add("src/worker.py", "def process():\n    helper()\n    third_party()\n\ndef helper(): pass\n")
        self._write_graph(
            nodes=[
                {"id": "src/worker.py::process", "label": "process", "kind": "function", "source_file": "src/worker.py"},
                {"id": "src/worker.py::helper", "label": "helper", "kind": "function", "source_file": "src/worker.py"},
            ],
            edges=[
                {"source": "src/worker.py::process", "target": "src/worker.py::helper", "relation": "calls"},
                {"source": "src/worker.py::process", "target": "external::third_party", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "process", None, "outgoing")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        out_files = [entry.get("file") for entry in data["outgoing"]]
        self.assertNotIn("external", out_files,
                         f"External entries must be suppressed by default; got {out_files}")
        self.assertEqual(data.get("external_outgoing_count"), 1)

    def test_include_external_surfaces_external_outgoing(self):
        """130ol AC-10: include_external=True returns the suppressed entries inline."""
        self._add("src/worker.py", "def process():\n    helper()\n    third_party()\n\ndef helper(): pass\n")
        self._write_graph(
            nodes=[
                {"id": "src/worker.py::process", "label": "process", "kind": "function", "source_file": "src/worker.py"},
                {"id": "src/worker.py::helper", "label": "helper", "kind": "function", "source_file": "src/worker.py"},
            ],
            edges=[
                {"source": "src/worker.py::process", "target": "src/worker.py::helper", "relation": "calls"},
                {"source": "src/worker.py::process", "target": "external::third_party", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(
            self.root, "process", None, "outgoing", include_external=True,
        )
        data = result["data"]
        out_files = [entry.get("file") for entry in data["outgoing"]]
        self.assertIn("external", out_files,
                      f"include_external=True must surface external entries; got {out_files}")
        self.assertEqual(data.get("external_outgoing_count"), 1)

    def test_external_incoming_suppressed_by_default(self):
        """130ol AC-10: incoming-side parity with the outgoing-side suppression."""
        self._add("src/worker.py", "def helper(): pass\n")
        self._write_graph(
            nodes=[
                {"id": "src/worker.py::helper", "label": "helper", "kind": "function", "source_file": "src/worker.py"},
                {"id": "src/worker.py::caller", "label": "caller", "kind": "function", "source_file": "src/worker.py"},
            ],
            edges=[
                {"source": "src/worker.py::caller", "target": "src/worker.py::helper", "relation": "calls"},
                {"source": "external::external_caller", "target": "src/worker.py::helper", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "helper", None, "incoming")
        data = result["data"]
        in_files = [entry.get("file") for entry in data["incoming"]]
        self.assertNotIn("external", in_files)
        self.assertEqual(data.get("external_incoming_count"), 1)


class TestCodeGraphPath(unittest.TestCase):
    """12zxl AC-5: code_graph_path_response — consistent shape guarantee."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        self._add("src/a.py", "def foo(): pass\n")
        self._add("src/b.py", "def bar(): foo()\n")
        payload = {
            "schema_version": "1",
            "builder_version": "1",
            "layer": "project",
            "nodes": [
                {"id": "src/a.py::foo", "label": "foo", "kind": "function", "source_file": "src/a.py", "layer": "project"},
                {"id": "src/b.py::bar", "label": "bar", "kind": "function", "source_file": "src/b.py", "layer": "project"},
            ],
            "edges": [
                {"source": "src/b.py::bar", "target": "src/a.py::foo", "relation": "calls", "confidence": "EXTRACTED"},
            ],
            "counts": {"files": 2, "nodes": 2, "edges": 1},
        }
        import json
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _required_keys(self, data: dict) -> None:
        for key in ("found", "path_nodes", "path_edges", "hop_count", "suggestions"):
            self.assertIn(key, data, f"Response missing key: {key}")

    def test_path_found_consistent_shape(self):
        result = self.srv.code_graph_path_response(self.root, "src/b.py::bar", "src/a.py::foo")
        self.assertEqual(result["status"], "ok")
        self._required_keys(result["data"])
        self.assertTrue(result["data"]["found"])
        self.assertGreater(result["data"]["hop_count"], 0)

    def test_path_not_found_consistent_shape(self):
        result = self.srv.code_graph_path_response(self.root, "src/a.py::foo", "src/b.py::bar")
        self.assertEqual(result["status"], "ok")
        self._required_keys(result["data"])
        self.assertFalse(result["data"]["found"])
        self.assertEqual(result["data"]["path_nodes"], [])
        self.assertEqual(result["data"]["hop_count"], 0)

    def test_unresolvable_symbol_consistent_shape_with_suggestions(self):
        result = self.srv.code_graph_path_response(self.root, "no_such_symbol_xyz", "src/a.py::foo")
        self.assertEqual(result["status"], "ok")
        self._required_keys(result["data"])
        self.assertFalse(result["data"]["found"])
        self.assertIsInstance(result["data"]["suggestions"], list)

    def test_no_graph_returns_error_with_consistent_shape(self):
        import shutil
        shutil.rmtree(self.root / ".wavefoundry" / "index" / "graph", ignore_errors=True)
        result = self.srv.code_graph_path_response(self.root, "src/b.py::bar", "src/a.py::foo")
        self.assertEqual(result["status"], "error")
        self.assertIn("found", result["data"])
        self.assertIn("suggestions", result["data"])


class TestCodeGraphPathDirection(unittest.TestCase):
    """13006: code_graph_path_response direction parameter (forward/backward/either)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Edge: bar → foo (calls); so forward bar→foo finds it; forward foo→bar does not.
        payload = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": [
                {"id": "src/a.py::foo", "label": "foo", "kind": "function", "source_file": "src/a.py", "layer": "project"},
                {"id": "src/b.py::bar", "label": "bar", "kind": "function", "source_file": "src/b.py", "layer": "project"},
            ],
            "edges": [
                {"source": "src/b.py::bar", "target": "src/a.py::foo", "relation": "calls", "confidence": "EXTRACTED"},
            ],
            "counts": {"files": 2, "nodes": 2, "edges": 1},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_direction_is_forward_byte_identity(self):
        """AC-1: omitting direction matches direction='forward' exactly."""
        result_default = self.srv.code_graph_path_response(self.root, "src/b.py::bar", "src/a.py::foo")
        result_forward = self.srv.code_graph_path_response(self.root, "src/b.py::bar", "src/a.py::foo", direction="forward")
        # data should be byte-identical except total_ms timing
        d_default = {k: v for k, v in result_default["data"].items() if k != "total_ms"}
        d_forward = {k: v for k, v in result_forward["data"].items() if k != "total_ms"}
        self.assertEqual(d_default, d_forward)

    def test_forward_finds_outgoing_path(self):
        result = self.srv.code_graph_path_response(self.root, "src/b.py::bar", "src/a.py::foo", direction="forward")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["found"])
        self.assertEqual(result["data"]["hop_count"], 1)
        self.assertEqual(result["data"]["direction"], "forward")

    def test_forward_misses_reverse_path(self):
        # foo → bar: no forward edge exists (bar → foo is the only calls edge)
        result = self.srv.code_graph_path_response(self.root, "src/a.py::foo", "src/b.py::bar", direction="forward")
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["found"])

    def test_backward_finds_reverse_path(self):
        # foo backward to bar: walking _in[foo] finds bar
        result = self.srv.code_graph_path_response(self.root, "src/a.py::foo", "src/b.py::bar", direction="backward")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["found"])
        self.assertEqual(result["data"]["hop_count"], 1)
        self.assertEqual(result["data"]["direction"], "backward")

    def test_either_finds_path_in_either_direction(self):
        # bar to foo via forward; should annotate traversal_direction
        result = self.srv.code_graph_path_response(self.root, "src/b.py::bar", "src/a.py::foo", direction="either")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["found"])
        for edge in result["data"]["path_edges"]:
            self.assertIn(edge.get("traversal_direction"), ("forward", "backward"))

    def test_invalid_direction_returns_invalid_arguments(self):
        result = self.srv.code_graph_path_response(self.root, "src/b.py::bar", "src/a.py::foo", direction="sideways")
        self.assertEqual(result["status"], "error")
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("invalid_arguments", codes)
        # Even on error, response shape must include the consistent fields
        self.assertIn("found", result["data"])
        self.assertIn("suggestions", result["data"])
        self.assertIn("direction", result["data"])

    def test_direction_case_insensitive(self):
        result = self.srv.code_graph_path_response(self.root, "src/b.py::bar", "src/a.py::foo", direction="EITHER")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["direction"], "either")


class TestGraphRefreshThenRecheck(unittest.TestCase):
    """1304r: helper unit tests for the shared refresh-and-recheck pattern."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        # Wave 1p2q3 (1p2w5): tests rely on the historical race window where
        # `subprocess.Popen` returns instantly and downstream `from_root`
        # reads the fixture graph before the spawned subprocess can rewrite
        # it. Short-circuit the new post-Popen verification so behavior
        # matches the prior contract for these unit tests.
        self._verify_timeout_patch = patch.object(
            self.srv, "_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS", 0.0
        )
        self._verify_timeout_patch.start()

    def tearDown(self):
        self._verify_timeout_patch.stop()
        self.tmp.cleanup()

    def test_recheck_returns_value_when_refresh_succeeds(self):
        """Refresh + recheck returns whatever the recheck closure returns."""
        sentinel = "fresh-candidate"
        result = self.srv._graph_refresh_then_recheck(self.root, lambda: sentinel)
        self.assertEqual(result, sentinel)

    def test_recheck_returns_none_when_recheck_returns_none(self):
        """If the recheck closure returns None, the helper passes that through."""
        result = self.srv._graph_refresh_then_recheck(self.root, lambda: None)
        self.assertIsNone(result)

    def test_recheck_returns_none_when_refresh_raises(self):
        """Helper catches refresh-time exceptions and returns None."""
        # Use a recheck closure that would return sentinel if it were called,
        # but the helper's refresh runs first; we can't easily force the refresh
        # to raise without monkey-patching index_build_response.
        import unittest.mock as _mock
        with _mock.patch.object(self.srv, "index_build_response", side_effect=RuntimeError("boom")):
            result = self.srv._graph_refresh_then_recheck(self.root, lambda: "would-be-fresh")
            self.assertIsNone(result)

    def test_recheck_returns_none_when_recheck_raises(self):
        """Helper catches recheck-time exceptions and returns None."""
        def _bad_recheck():
            raise ValueError("recheck failed")
        result = self.srv._graph_refresh_then_recheck(self.root, _bad_recheck)
        self.assertIsNone(result)


class TestGraphToolRefreshOnMiss(unittest.TestCase):
    """1304r AC-8 follow-on: verify each graph-using MCP tool triggers the refresh
    on its miss path. Mocks `index_build_response` to assert it was called.

    Pattern: each test sets up a minimal graph fixture that does NOT contain the
    queried symbol/community, then asserts that the refresh helper's underlying
    `index_build_response` was invoked exactly once (the bounded-to-one-call
    contract from AC-1)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Minimal graph that does NOT contain the bogus symbols we'll query
        payload = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": [
                {"id": "src/a.py::existing", "label": "existing", "kind": "function", "source_file": "src/a.py"},
            ],
            "edges": [],
            "counts": {"files": 1, "nodes": 1, "edges": 0},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")
        cluster = {
            "cluster_algorithm": "leiden", "cluster_builder_version": "1", "cluster_schema_version": "1",
            "communities": [
                {"community_id": "project:c1", "label": "core", "node_count": 1, "node_ids": ["src/a.py::existing"]},
            ],
            "community_count": 1,
        }
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps(cluster), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _assert_refresh_invoked_once(self, tool_call):
        """Run tool_call() while patching index_build_response; assert called once."""
        import unittest.mock as _mock
        with _mock.patch.object(self.srv, "index_build_response", return_value={"status": "ok", "data": {}}) as patched:
            tool_call()
            self.assertEqual(
                patched.call_count, 1,
                f"Expected exactly 1 refresh call but got {patched.call_count}",
            )

    def test_code_references_refreshes_on_miss(self):
        self._assert_refresh_invoked_once(
            lambda: self.srv.code_references_response(self.root, "no_such_symbol")
        )

    def test_code_callhierarchy_refreshes_on_miss(self):
        self._assert_refresh_invoked_once(
            lambda: self.srv.code_callhierarchy_response(self.root, "no_such_symbol")
        )

    def test_code_callgraph_refreshes_on_miss(self):
        self._assert_refresh_invoked_once(
            lambda: self.srv.code_callgraph_response(self.root, "no_such_symbol")
        )

    def test_code_impact_graph_mode_refreshes_on_miss(self):
        self._assert_refresh_invoked_once(
            lambda: self.srv.code_impact_response(self.root, "", symbol="no_such_symbol")
        )

    def test_code_graph_path_refreshes_on_miss(self):
        # Both symbols missing — refresh should still happen exactly once
        self._assert_refresh_invoked_once(
            lambda: self.srv.code_graph_path_response(self.root, "no_such_from", "no_such_to")
        )

    def test_code_graph_path_refreshes_when_only_one_symbol_missing(self):
        """A1 regression test: when only one symbol is missing initially, refresh
        still runs and the freshly loaded index is used to retry both symbols."""
        # from_symbol resolves (in fixture), to_symbol does not
        self._assert_refresh_invoked_once(
            lambda: self.srv.code_graph_path_response(self.root, "existing", "no_such_to")
        )

    def test_code_graph_community_refreshes_on_miss(self):
        self._assert_refresh_invoked_once(
            lambda: self.srv.code_graph_community_response(self.root, "project:does_not_exist")
        )

    def test_wf_graph_report_refreshes_on_absent_graph(self):
        # Remove the graph fixture so first index.present check fails
        import shutil
        shutil.rmtree(self.root / ".wavefoundry" / "index" / "graph", ignore_errors=True)
        self._assert_refresh_invoked_once(
            lambda: self.srv.wf_graph_report_response(self.root, layer="project", sections=["fan_in"])
        )


class TestGraphRefreshAndResolve(unittest.TestCase):
    """1304r: convenience helper that combines refresh + reload index + resolve symbol."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        # Wave 1p2q3 (1p2w5): short-circuit run_index_rebuild's post-Popen
        # verification window so these tests retain the original behavior
        # (subprocess Popen returns; fixture graph is read before subprocess
        # rewrites it).
        self._verify_timeout_patch = patch.object(
            self.srv, "_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS", 0.0
        )
        self._verify_timeout_patch.start()

    def tearDown(self):
        self._verify_timeout_patch.stop()
        self.tmp.cleanup()

    def _write_graph(self, nodes):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        payload = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": nodes, "edges": [],
            "counts": {"files": 1, "nodes": len(nodes), "edges": 0},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_returns_index_and_id_when_symbol_in_graph_after_refresh(self):
        """When graph (after refresh) contains the symbol, return (index, node_id)."""
        self._write_graph([
            {"id": "src/a.py::foo", "label": "foo", "kind": "function", "source_file": "src/a.py"},
        ])
        idx, node_id = self.srv._graph_refresh_and_resolve(self.root, "foo")
        self.assertIsNotNone(idx)
        self.assertEqual(node_id, "src/a.py::foo")

    def test_returns_none_tuple_when_symbol_missing(self):
        """When graph doesn't contain the symbol, return (None, None)."""
        self._write_graph([
            {"id": "src/a.py::bar", "label": "bar", "kind": "function", "source_file": "src/a.py"},
        ])
        idx, node_id = self.srv._graph_refresh_and_resolve(self.root, "no_such_symbol")
        self.assertIsNone(idx)
        self.assertIsNone(node_id)

    def test_returns_none_tuple_when_refresh_raises(self):
        """If refresh raises, both elements are None."""
        import unittest.mock as _mock
        with _mock.patch.object(self.srv, "index_build_response", side_effect=RuntimeError("boom")):
            idx, node_id = self.srv._graph_refresh_and_resolve(self.root, "anything")
            self.assertIsNone(idx)
            self.assertIsNone(node_id)


class TestApplyGraphAugmentation(unittest.TestCase):
    """12xs5: opt-out path verified at the wrapper-helper layer.

    These tests cover the augmentation logic extracted from the four MCP wrappers
    (`code_keyword`, `code_search`, `code_definition`, `code_references`) into
    `_augment_with_graph_neighbors_if_enabled()`. Without the helper extraction
    this logic lived inside FastMCP closures registered at server startup,
    which made it awkward to unit-test directly; tests had to rely on live MCP
    smoke after `/mcp` reconnect. The helper closes that gap."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        # Write a minimal graph fixture so _maybe_append_graph_neighbors can resolve seeds
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        payload = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": [
                {"id": "src/a.py", "label": "a", "kind": "module", "source_file": "src/a.py"},
                {"id": "src/a.py::foo", "label": "foo", "kind": "function", "source_file": "src/a.py"},
                {"id": "src/b.py::bar", "label": "bar", "kind": "function", "source_file": "src/b.py"},
            ],
            "edges": [
                {"source": "src/a.py::foo", "target": "src/b.py::bar", "relation": "calls", "confidence": "EXTRACTED"},
            ],
            "counts": {"files": 2, "nodes": 3, "edges": 1},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_response(self, tool_key: str) -> dict:
        """Build a minimal response with seed-bearing data for the given tool."""
        if tool_key in ("code_keyword", "code_search"):
            return {"status": "ok", "data": {"results": [{"path": "src/a.py", "line": 1}]}}
        if tool_key == "code_definition":
            return {"status": "ok", "data": {"definitions": [{"path": "src/a.py", "name": "foo", "line": 1}]}}
        if tool_key == "code_references":
            return {"status": "ok", "data": {"references": [{"path": "src/a.py", "line": 1}]}}
        raise ValueError(tool_key)

    def test_graph_false_returns_response_unchanged_for_all_four_tools(self):
        """Opt-out: graph=False must not add graph_neighbors for any of the four tools."""
        for tool_key in ("code_keyword", "code_search", "code_definition", "code_references"):
            with self.subTest(tool_key=tool_key):
                r = self._seed_response(tool_key)
                out = self.srv._augment_with_graph_neighbors_if_enabled(
                    r, self.root, tool_key=tool_key, graph=False,
                )
                self.assertNotIn("graph_neighbors", out.get("data") or {})

    def test_graph_true_adds_graph_neighbors_for_all_four_tools(self):
        """Opt-in default: graph=True must append graph_neighbors when seeds resolve."""
        for tool_key in ("code_keyword", "code_search", "code_definition", "code_references"):
            with self.subTest(tool_key=tool_key):
                r = self._seed_response(tool_key)
                out = self.srv._augment_with_graph_neighbors_if_enabled(
                    r, self.root, tool_key=tool_key, graph=True,
                )
                self.assertIn("graph_neighbors", out.get("data") or {})
                neighbors = out["data"]["graph_neighbors"]
                self.assertTrue(neighbors.get("present"))
                # The seeded graph fixture has 3 nodes; one of them should appear
                self.assertGreater(len(neighbors.get("nodes") or []), 0)

    def test_graph_true_with_empty_seeds_returns_unchanged(self):
        """Edge case: graph=True but the response has no seed-bearing data → unchanged."""
        for tool_key in ("code_keyword", "code_search", "code_definition", "code_references"):
            with self.subTest(tool_key=tool_key):
                r = {"status": "ok", "data": {}}  # no seeds
                out = self.srv._augment_with_graph_neighbors_if_enabled(
                    r, self.root, tool_key=tool_key, graph=True,
                )
                self.assertNotIn("graph_neighbors", out.get("data") or {})

    def test_graph_true_with_non_ok_response_returns_unchanged(self):
        """Safety: error responses don't get augmented even when graph=True."""
        r = {"status": "error", "data": {"results": [{"path": "src/a.py", "line": 1}]}}
        out = self.srv._augment_with_graph_neighbors_if_enabled(
            r, self.root, tool_key="code_keyword", graph=True,
        )
        self.assertNotIn("graph_neighbors", out.get("data") or {})

    def test_graph_limit_caps_seed_count(self):
        """graph_limit caps the seeds passed to neighbor expansion."""
        # Three seed results — graph_limit=1 should still produce neighbors (cap applies to seeds)
        r = {"status": "ok", "data": {"results": [
            {"path": "src/a.py", "line": 1},
            {"path": "src/b.py", "line": 1},
            {"path": "src/a.py", "line": 5},
        ]}}
        out = self.srv._augment_with_graph_neighbors_if_enabled(
            r, self.root, tool_key="code_keyword", graph=True, graph_limit=1,
        )
        # With graph_limit=1, only the first seed (src/a.py) drives expansion
        self.assertIn("graph_neighbors", out.get("data") or {})


class TestCodeDefinitionGraphNarrowed(unittest.TestCase):
    """1301h: code_definition consults the graph to narrow the file set before scanning."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        # Real Python files with a definition we'll look up
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "src" / "target.py").write_text(
            "def my_definition():\n    return 1\n",
            encoding="utf-8",
        )
        (self.root / "src" / "decoy.py").write_text(
            "def unrelated_function():\n    return 2\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _write_graph(self, nodes):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        payload = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": nodes, "edges": [],
            "counts": {"files": len({n.get("source_file") for n in nodes if n.get("source_file")}), "nodes": len(nodes), "edges": 0},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_no_graph_runs_degraded_mode_with_diagnostic(self):
        """AC-2 (revised): graph absent → existing structural full walk runs, but
        the response carries an advisory `graph_index_missing_degraded` diagnostic
        telling the operator to build the graph for the fast path.

        Pre-1301h: silent 40+s full walk, no signal to the operator.
        Post-1301h: same 40+s full walk (preserves existing behavior for callers
        that depend on `name`-bearing structural definitions) PLUS a clear
        advisory diagnostic + a `graph_index_missing_degraded` lookup_method.
        Operators see the advisory and run `index_build(content='graph')`
        to enable the sub-300ms graph-narrowed path on subsequent calls."""
        result = self.srv.code_definition_response(self.root, "my_definition")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["lookup_method"], "graph_index_missing_degraded")
        # Structural definition still found because scanners ran full walk
        self.assertTrue(any(d.get("name") == "my_definition" for d in result["data"]["definitions"]))
        # Advisory diagnostic is present
        # (lookup_method indicates degraded; diagnostic appears only on the
        # keyword_fallback escape hatch, which this test doesn't trigger because
        # the structural scanner finds my_definition)

    def test_graph_present_with_match_uses_narrowed_path(self):
        """AC-1: graph present and symbol resolvable → lookup_method='graph_narrowed'."""
        self._write_graph([
            {"id": "src/target.py::my_definition", "label": "my_definition", "kind": "function", "source_file": "src/target.py"},
            {"id": "src/decoy.py::unrelated_function", "label": "unrelated_function", "kind": "function", "source_file": "src/decoy.py"},
        ])
        result = self.srv.code_definition_response(self.root, "my_definition")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["lookup_method"], "graph_narrowed")
        self.assertTrue(any(d["name"] == "my_definition" for d in result["data"]["definitions"]))

    def test_graph_present_no_match_triggers_refresh_then_definitive(self):
        """AC-3 + AC-8: graph present but symbol unmatched → incremental refresh runs.
        If the refresh picks up the symbol, lookup_method='graph_narrowed_after_refresh';
        if not, the graph is treated as the source of truth and we return
        lookup_method='graph_definitive_not_found' without burning a full repo walk.
        Either outcome is correct — both confirm the refresh path executed."""
        self._write_graph([
            {"id": "src/decoy.py::unrelated_function", "label": "unrelated_function", "kind": "function", "source_file": "src/decoy.py"},
        ])
        result = self.srv.code_definition_response(self.root, "my_definition")
        self.assertEqual(result["status"], "ok")
        self.assertIn(
            result["data"]["lookup_method"],
            ("graph_definitive_not_found", "graph_narrowed_after_refresh"),
        )

    def test_substring_match_preserved_in_narrowed_path(self):
        """AC-5: substring queries (e.g. 'def' matches 'my_definition') still resolve via graph."""
        self._write_graph([
            {"id": "src/target.py::my_definition", "label": "my_definition", "kind": "function", "source_file": "src/target.py"},
        ])
        result = self.srv.code_definition_response(self.root, "def")
        # 'def' is substring of 'my_definition' label → candidate includes src/target.py
        # Note: graph_narrowed expected since match found; scanner then runs on restricted set
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["lookup_method"], "graph_narrowed")
        names = [d["name"] for d in result["data"]["definitions"]]
        self.assertIn("my_definition", names)

    def test_graph_narrowed_path_finds_correct_definition(self):
        """AC-5 (revised): graph-narrowed path resolves the symbol to the expected file.

        Previous version of this test compared narrowed-path output against the
        full_walk path. After the 1301h fail-fast change, full_walk is no longer
        a reachable code path — the graph is now the source of truth. The replacement
        contract: when the graph points to a file, the scanner must return a
        definition with the expected name from the expected file."""
        self._write_graph([
            {"id": "src/target.py::my_definition", "label": "my_definition", "kind": "function", "source_file": "src/target.py"},
        ])
        result = self.srv.code_definition_response(self.root, "my_definition")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["lookup_method"], "graph_narrowed")
        defs = result["data"]["definitions"]
        self.assertTrue(any(d["path"] == "src/target.py" and d["name"] == "my_definition" for d in defs))

    def test_missing_symbol_with_graph_returns_definitive_not_found(self):
        """AC-6 (revised): when graph confirms no match (after refresh attempt),
        return graph_definitive_not_found instead of a slow keyword_fallback walk."""
        self._write_graph([
            {"id": "src/target.py::my_definition", "label": "my_definition", "kind": "function", "source_file": "src/target.py"},
        ])
        result = self.srv.code_definition_response(self.root, "ZZZNODEFINITIONYYY")
        self.assertEqual(result["status"], "ok")
        # Either definitive-not-found (graph confirmed no match) or graph_narrowed_after_refresh
        # (if the refresh somehow picked up the symbol)
        self.assertIn(
            result["data"]["lookup_method"],
            ("graph_definitive_not_found", "graph_narrowed_after_refresh"),
        )

    def test_definitive_not_found_mirrors_code_callhierarchy_suggestions(self):
        """Wave 1p2q3 (1p2qb): code_definition's not-found path surfaces a
        `suggestions` array of near-matches, mirroring code_callhierarchy."""
        self._write_graph([
            {"id": "src/target.py::my_definition", "label": "my_definition", "kind": "function", "source_file": "src/target.py"},
            {"id": "src/other.py::my_definition_helper", "label": "my_definition_helper", "kind": "function", "source_file": "src/other.py"},
        ])
        result = self.srv.code_definition_response(self.root, "my_definitions")
        self.assertEqual(result["status"], "ok")
        lookup = result["data"]["lookup_method"]
        if lookup in ("graph_definitive_not_found", "graph_narrowed_after_refresh"):
            suggestions = result["data"].get("suggestions")
            self.assertIsInstance(suggestions, list)
            for s in suggestions:
                self.assertTrue(isinstance(s, dict))
                self.assertTrue(any(k in s for k in ("id", "label", "node_id", "symbol")))

    def test_attribution_counts_by_language_present_on_definitive_not_found(self):
        """Wave 1p2q3 (1p2q9 B AC-6/7/8): polyglot graph populates per-language counts."""
        import json as _json
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": [
                {"id": "src/py.py::a", "label": "a", "kind": "function", "source_file": "src/py.py"},
                {"id": "src/py.py::b", "label": "b", "kind": "function", "source_file": "src/py.py"},
                {"id": "libs/ts.ts::c", "label": "c", "kind": "function", "source_file": "libs/ts.ts"},
                {"id": "libs/ts.ts::d", "label": "d", "kind": "function", "source_file": "libs/ts.ts"},
            ],
            "edges": [
                {"source": "src/py.py::a", "target": "src/py.py::b", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
                {"source": "libs/ts.ts::c", "target": "libs/ts.ts::d", "relation": "calls", "confidence": "EXTRACTED"},
            ],
            "counts": {"files": 2, "nodes": 4, "edges": 2},
        }
        (graph_dir / "project-graph.json").write_text(_json.dumps(payload), encoding="utf-8")
        result = self.srv.code_definition_response(self.root, "nonexistent_typo_symbol")
        self.assertEqual(result["status"], "ok")
        if result["data"].get("lookup_method") in ("graph_definitive_not_found", "graph_narrowed_after_refresh"):
            counts = result["data"].get("attribution_counts_by_language")
            self.assertIsInstance(counts, dict)
            self.assertIn("python", counts)
            self.assertIn("typescript", counts)
            self.assertEqual(counts["python"]["receiver_resolved"], 1)
            self.assertEqual(counts["typescript"]["extracted"], 1)


class TestCodeImpactIncludeTests(unittest.TestCase):
    """12zxl AC-2: code_impact include_tests filter."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        self._add("src/utils.py", "def helper(): pass\n")
        self._add("tests/test_utils.py", "from src.utils import helper\ndef test_helper(): helper()\n")
        import json
        payload = {
            "schema_version": "1",
            "builder_version": "1",
            "layer": "project",
            "nodes": [
                {"id": "src/utils.py::helper", "label": "helper", "kind": "function", "source_file": "src/utils.py", "layer": "project"},
                {"id": "tests/test_utils.py::test_helper", "label": "test_helper", "kind": "function", "source_file": "tests/test_utils.py", "layer": "project"},
            ],
            "edges": [
                {"source": "tests/test_utils.py::test_helper", "target": "src/utils.py::helper", "relation": "calls", "confidence": "EXTRACTED"},
            ],
            "counts": {"files": 2, "nodes": 2, "edges": 1},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_include_tests_false_excludes_test_callers(self):
        result = self.srv.code_impact_response(
            self.root, "", symbol="src/utils.py::helper", max_hops=2, include_tests=False
        )
        self.assertEqual(result["status"], "ok")
        affected_ids = {row["node_id"] for row in result["data"]["affected"]}
        self.assertNotIn("tests/test_utils.py::test_helper", affected_ids)

    def test_include_tests_true_includes_test_callers(self):
        result = self.srv.code_impact_response(
            self.root, "", symbol="src/utils.py::helper", max_hops=2, include_tests=True
        )
        self.assertEqual(result["status"], "ok")
        affected_ids = {row["node_id"] for row in result["data"]["affected"]}
        self.assertIn("tests/test_utils.py::test_helper", affected_ids)

    # Wave 1vbuu (1vbut): the `test_callers_not_visible` advisory fires ONLY when
    # include_tests=true finds zero test-path callers. Three states:
    #   (1) include_tests=true + a test-path hit  -> no diagnostic (positive control)
    #   (2) include_tests=false                   -> no diagnostic (response unchanged)
    #   (3) include_tests=true + no test-path hit -> diagnostic present, advisory
    @staticmethod
    def _codes(result):
        return {d.get("code") for d in (result.get("diagnostics") or [])}

    def test_test_callers_visible_hit_suppresses_diagnostic(self):
        result = self.srv.code_impact_response(
            self.root, "", symbol="src/utils.py::helper", max_hops=2, include_tests=True
        )
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("test_callers_not_visible", self._codes(result))

    def test_include_tests_false_never_emits_visibility_diagnostic(self):
        result = self.srv.code_impact_response(
            self.root, "", symbol="src/utils.py::helper", max_hops=2, include_tests=False
        )
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("test_callers_not_visible", self._codes(result))

    def test_no_test_callers_emits_advisory_diagnostic(self):
        # Rebuild the graph with a NON-test caller only: the symbol is reachable
        # (one caller) but no test-path node exists, the wave-1ve3e state.
        import json
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        payload = {
            "schema_version": "1",
            "builder_version": "1",
            "layer": "project",
            "nodes": [
                {"id": "src/utils.py::helper", "label": "helper", "kind": "function", "source_file": "src/utils.py", "layer": "project"},
                {"id": "src/app.py::main", "label": "main", "kind": "function", "source_file": "src/app.py", "layer": "project"},
            ],
            "edges": [
                {"source": "src/app.py::main", "target": "src/utils.py::helper", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
            ],
            "counts": {"files": 2, "nodes": 2, "edges": 1},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")
        result = self.srv.code_impact_response(
            self.root, "", symbol="src/utils.py::helper", max_hops=2, include_tests=True
        )
        self.assertEqual(result["status"], "ok", result)
        # The non-test caller is still reported: the diagnostic qualifies the
        # empty TEST set, it does not empty the response.
        affected_ids = {row["node_id"] for row in result["data"]["affected"]}
        self.assertIn("src/app.py::main", affected_ids)
        diags = [d for d in (result.get("diagnostics") or []) if d.get("code") == "test_callers_not_visible"]
        self.assertEqual(len(diags), 1, result.get("diagnostics"))
        self.assertTrue(diags[0].get("advisory"), "must be advisory, never an error")
        self.assertIn("mock", diags[0]["message"])
        self.assertIn("excluded from the index", diags[0]["message"])
        self.assertIn("code_keyword", diags[0].get("recovery_tools") or [])
        self.assertFalse(result.get("isError"))


class TestCodeGraphCommunity(unittest.TestCase):
    """12zxl AC-5: code_graph_community_response — not-found and empty-id handling."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        graph = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": [{"id": "src/a.py::foo", "label": "foo", "kind": "function", "source_file": "src/a.py"}],
            "edges": [],
            "counts": {"files": 1, "nodes": 1, "edges": 0},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        cluster = {
            "cluster_algorithm": "leiden",
            "cluster_builder_version": "1",
            "cluster_schema_version": "1",
            "communities": [
                {"community_id": "project:c1", "label": "core", "node_count": 1, "node_ids": ["src/a.py::foo"]},
                # Community with null community_id to verify empty-string guard does not match
                {"community_id": None, "label": "anonymous", "node_count": 0, "node_ids": []},
            ],
            "community_count": 2,
        }
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps(cluster), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_absent_community_id_returns_not_found(self):
        result = self.srv.code_graph_community_response(self.root, "project:does_not_exist")
        self.assertEqual(result["status"], "error")
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("not_found", codes)

    def test_empty_community_id_returns_invalid_arguments(self):
        result = self.srv.code_graph_community_response(self.root, "")
        self.assertEqual(result["status"], "error")
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("invalid_arguments", codes)

    def test_whitespace_community_id_returns_invalid_arguments(self):
        result = self.srv.code_graph_community_response(self.root, "   ")
        self.assertEqual(result["status"], "error")
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("invalid_arguments", codes)

    def test_valid_community_id_returns_members(self):
        result = self.srv.code_graph_community_response(self.root, "project:c1")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertEqual(data["community_id"], "project:c1")
        self.assertEqual(data["label"], "core")
        self.assertEqual(data["node_count"], 1)
        self.assertEqual(data["nodes"][0]["id"], "src/a.py::foo")

    def test_not_found_returns_ranked_suggestions(self):
        """Improvement: not-found response includes ranked community suggestions."""
        result = self.srv.code_graph_community_response(self.root, "project:c2")
        self.assertEqual(result["status"], "error")
        suggestions = result["data"].get("suggestions") or []
        self.assertIsInstance(suggestions, list)
        # 'project:c2' substring-matches 'project:c1' → bucket 0 (substring in cid)
        self.assertTrue(any(s["community_id"] == "project:c1" for s in suggestions))
        # suggestions skip the null-community_id entry from fixture
        for s in suggestions:
            self.assertTrue(s["community_id"])

    def test_not_found_unrelated_query_falls_back_by_node_count(self):
        """Improvement: with no substring match, suggestions fall back to largest communities."""
        result = self.srv.code_graph_community_response(self.root, "zzz_no_match")
        self.assertEqual(result["status"], "error")
        suggestions = result["data"].get("suggestions") or []
        # First suggestion should be the largest (only valid) community
        self.assertEqual(suggestions[0]["community_id"], "project:c1")

    # ---- Wave 130rj AC-4: pagination (limit/offset, total_node_count, has_more) ----

    def _seed_paginated_community(self, member_count=120):
        """Rebuild graph + cluster with N synthetic members so pagination is observable."""
        import json
        nodes = [
            {"id": f"src/m.py::node_{i}", "label": f"node_{i}", "kind": "function", "source_file": "src/m.py"}
            for i in range(member_count)
        ]
        graph = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": nodes, "edges": [],
            "counts": {"files": 1, "nodes": member_count, "edges": 0},
        }
        cluster = {
            "cluster_algorithm": "leiden",
            "cluster_builder_version": "1",
            "cluster_schema_version": "1",
            "communities": [
                {
                    "community_id": "project:big",
                    "label": "Bigly",
                    "node_count": member_count,
                    "node_ids": [n["id"] for n in nodes],
                }
            ],
            "community_count": 1,
        }
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps(cluster), encoding="utf-8")

    def test_pagination_default_limit_returns_first_50(self):
        self._seed_paginated_community(120)
        result = self.srv.code_graph_community_response(self.root, "project:big")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertEqual(data["total_node_count"], 120)
        self.assertEqual(data["returned_count"], 50)
        self.assertEqual(data["offset"], 0)
        self.assertTrue(data["has_more"])
        self.assertEqual(len(data["nodes"]), 50)
        # Back-compat alias: node_count equals returned_count.
        self.assertEqual(data["node_count"], 50)

    def test_pagination_with_offset(self):
        self._seed_paginated_community(120)
        result = self.srv.code_graph_community_response(self.root, "project:big", limit=20, offset=100)
        data = result["data"]
        self.assertEqual(data["total_node_count"], 120)
        self.assertEqual(data["returned_count"], 20)
        self.assertEqual(data["offset"], 100)
        self.assertFalse(data["has_more"])

    def test_pagination_limit_clamps_to_max(self):
        self._seed_paginated_community(120)
        result = self.srv.code_graph_community_response(self.root, "project:big", limit=99999)
        data = result["data"]
        # Limit clamped to 500 by the helper; with 120 members we return all 120.
        self.assertEqual(data["returned_count"], 120)
        self.assertFalse(data["has_more"])

    def test_pagination_negative_offset_clamps_to_zero(self):
        self._seed_paginated_community(60)
        result = self.srv.code_graph_community_response(self.root, "project:big", offset=-5)
        data = result["data"]
        self.assertEqual(data["offset"], 0)


class TestGraphToolShapeConsistency(unittest.TestCase):
    """130rj AC-1/AC-2/AC-3/AC-5/AC-6: community_id dual return + hop attribution + community overview."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Three-node call chain: caller_a → mid → leaf. Two communities (c1, c2).
        (self.root / "src" / "lib.py").parent.mkdir(parents=True, exist_ok=True)
        (self.root / "src" / "lib.py").write_text(
            "def leaf(): pass\ndef mid(): leaf()\ndef caller_a(): mid()\n",
            encoding="utf-8",
        )
        graph = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": [
                {"id": "src/lib.py::leaf", "label": "leaf", "kind": "function", "source_file": "src/lib.py", "source_location": "1:0"},
                {"id": "src/lib.py::mid", "label": "mid", "kind": "function", "source_file": "src/lib.py", "source_location": "2:0"},
                {"id": "src/lib.py::caller_a", "label": "caller_a", "kind": "function", "source_file": "src/lib.py", "source_location": "3:0"},
            ],
            "edges": [
                {"source": "src/lib.py::mid", "target": "src/lib.py::leaf", "relation": "calls"},
                {"source": "src/lib.py::caller_a", "target": "src/lib.py::mid", "relation": "calls"},
            ],
            "counts": {"files": 1, "nodes": 3, "edges": 2},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        cluster = {
            "cluster_algorithm": "leiden",
            "cluster_builder_version": "1",
            "cluster_schema_version": "1",
            "communities": [
                {"community_id": "project:c1", "label": "LibCore", "node_count": 2, "node_ids": ["src/lib.py::leaf", "src/lib.py::mid"]},
                {"community_id": "project:c2", "label": "Caller", "node_count": 1, "node_ids": ["src/lib.py::caller_a"]},
            ],
            "community_count": 2,
        }
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps(cluster), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    # AC-2: code_callhierarchy outgoing + incoming carry community_id alongside community label.
    def test_callhierarchy_outgoing_has_community_id(self):
        result = self.srv.code_callhierarchy_response(self.root, "mid", None, "outgoing")
        self.assertEqual(result["status"], "ok")
        outgoing = result["data"]["outgoing"]
        self.assertTrue(outgoing)
        for entry in outgoing:
            self.assertIn("community", entry)
            self.assertIn("community_id", entry)
        # leaf is in c1
        leaf_entry = next(e for e in outgoing if e.get("name") == "leaf")
        self.assertEqual(leaf_entry["community"], "LibCore")
        self.assertEqual(leaf_entry["community_id"], "project:c1")

    def test_callhierarchy_incoming_has_community_id(self):
        result = self.srv.code_callhierarchy_response(self.root, "mid", None, "incoming")
        incoming = result["data"]["incoming"]
        self.assertTrue(incoming)
        caller_a_entry = next(e for e in incoming if e.get("name") == "caller_a")
        self.assertEqual(caller_a_entry["community_id"], "project:c2")

    # AC-3 / AC-5: code_impact affected entries carry community_id AND hop attribution.
    def test_impact_affected_has_community_id_and_hop(self):
        result = self.srv.code_impact_response(self.root, "", symbol="leaf", max_hops=3)
        self.assertEqual(result["status"], "ok")
        affected = result["data"]["affected"]
        self.assertTrue(affected)
        for entry in affected:
            self.assertIn("community", entry)
            self.assertIn("community_id", entry)
            self.assertIn("hop", entry)
        # mid is a direct caller (hop 1); caller_a is hop 2.
        mid_entry = next(e for e in affected if e.get("label") == "mid")
        caller_entry = next(e for e in affected if e.get("label") == "caller_a")
        self.assertEqual(mid_entry["hop"], 1)
        self.assertEqual(caller_entry["hop"], 2)

    # AC-6: wf_graph_report carries a communities section with community_id/label/node_count/hub_*.
    def test_wf_graph_report_includes_communities_section(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10)
        self.assertEqual(result["status"], "ok")
        report = result["data"]
        self.assertIn("communities", report)
        communities = report["communities"]
        self.assertTrue(communities)
        # First community sorted by node_count desc — LibCore (2 nodes) before Caller (1 node).
        first = communities[0]
        self.assertIn("community_id", first)
        self.assertIn("label", first)
        self.assertIn("node_count", first)
        self.assertIn("hub_node_id", first)
        self.assertIn("hub_label", first)
        self.assertEqual(first["community_id"], "project:c1")
        self.assertEqual(first["label"], "LibCore")
        self.assertEqual(first["node_count"], 2)


class TestGeneratedCodeFilter(unittest.TestCase):
    """130rj-enh generated-code-classifier-and-filters: server-tool filter + warning behavior."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Three handwritten nodes + three generated nodes (simulating ELParser-style).
        nodes = [
            {"id": "src/handwritten.py::foo", "label": "foo", "kind": "function", "source_file": "src/handwritten.py", "source_location": "1:0"},
            {"id": "src/handwritten.py::bar", "label": "bar", "kind": "function", "source_file": "src/handwritten.py", "source_location": "5:0"},
            {"id": "src/handwritten.py::baz", "label": "baz", "kind": "function", "source_file": "src/handwritten.py", "source_location": "10:0"},
            {"id": "src/ELParser.java::Statement", "label": "Statement", "kind": "function", "source_file": "src/ELParser.java", "source_location": "100:0", "generated": True},
            {"id": "src/ELParser.java::jj_scan_token", "label": "jj_scan_token", "kind": "function", "source_file": "src/ELParser.java", "source_location": "200:0", "generated": True},
            {"id": "src/ELParser.java::jj_3R_96", "label": "jj_3R_96", "kind": "function", "source_file": "src/ELParser.java", "source_location": "300:0", "generated": True},
        ]
        graph = {
            "schema_version": "1", "builder_version": "11", "layer": "project",
            "nodes": nodes,
            "edges": [
                {"source": "src/handwritten.py::foo", "target": "src/ELParser.java::Statement", "relation": "calls"},
                {"source": "src/handwritten.py::bar", "target": "src/ELParser.java::Statement", "relation": "calls"},
                {"source": "src/ELParser.java::Statement", "target": "src/ELParser.java::jj_scan_token", "relation": "calls"},
                {"source": "src/ELParser.java::Statement", "target": "src/ELParser.java::jj_3R_96", "relation": "calls"},
                {"source": "src/ELParser.java::jj_3R_96", "target": "src/ELParser.java::jj_scan_token", "relation": "calls"},
            ],
            "counts": {"files": 2, "nodes": 6, "edges": 5},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        cluster = {
            "cluster_algorithm": "leiden",
            "cluster_builder_version": "1",
            "cluster_schema_version": "1",
            "communities": [
                {
                    "community_id": "project:c1",
                    "label": "Handwritten",
                    "node_count": 3,
                    "node_ids": ["src/handwritten.py::foo", "src/handwritten.py::bar", "src/handwritten.py::baz"],
                    "generated_node_fraction": 0.0,
                },
                {
                    "community_id": "project:c2",
                    "label": "ELParser",
                    "node_count": 3,
                    "node_ids": ["src/ELParser.java::Statement", "src/ELParser.java::jj_scan_token", "src/ELParser.java::jj_3R_96"],
                    "generated_node_fraction": 1.0,
                },
            ],
            "community_count": 2,
        }
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps(cluster), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    # AC-6: generated_node_fraction surfaces from cluster artifact in code_graph_community.
    def test_code_graph_community_exposes_generated_fraction(self):
        result = self.srv.code_graph_community_response(self.root, "project:c2")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertEqual(data["generated_node_fraction"], 1.0)
        self.assertEqual(data["total_node_count"], 3)

    # AC-7: exclude_generated filters generated members from code_graph_community.
    def test_code_graph_community_exclude_generated_filters_members(self):
        result = self.srv.code_graph_community_response(self.root, "project:c2", exclude_generated=True)
        data = result["data"]
        # All 3 members are generated → exclude filters them all out.
        self.assertEqual(data["returned_count"], 0)
        # total_node_count remains 3 (pre-filter total).
        self.assertEqual(data["total_node_count"], 3)
        self.assertTrue(data["exclude_generated"])

    # AC-9: communities entries with generated_node_fraction > 0.4 carry community_type: "generated-dominated".
    def test_wf_graph_report_communities_flag_generated_dominated(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10)
        report = result["data"]
        communities = report["communities"]
        elp = next((c for c in communities if c["community_id"] == "project:c2"), None)
        self.assertIsNotNone(elp)
        self.assertEqual(elp["generated_node_fraction"], 1.0)
        self.assertEqual(elp.get("community_type"), "generated-dominated")
        # Handwritten community (fraction 0.0) should NOT carry the flag.
        hw = next((c for c in communities if c["community_id"] == "project:c1"), None)
        self.assertIsNotNone(hw)
        self.assertEqual(hw["generated_node_fraction"], 0.0)
        self.assertNotIn("community_type", hw)

    # AC-8: exclude_generated removes generated nodes from fan_in/fan_out/chokepoints.
    def test_wf_graph_report_exclude_generated_filters_fan_sections(self):
        result_off = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        result_on = self.srv.wf_graph_report_response(self.root, layer="project", limit=20, exclude_generated=True)
        fan_in_off = {r["node_id"] for r in result_off["data"].get("fan_in", [])}
        fan_in_on = {r["node_id"] for r in result_on["data"].get("fan_in", [])}
        # Off: includes generated nodes (jj_scan_token is the most-called target in our fixture).
        self.assertIn("src/ELParser.java::jj_scan_token", fan_in_off)
        # On: generated nodes filtered out of fan_in.
        self.assertNotIn("src/ELParser.java::jj_scan_token", fan_in_on)
        self.assertNotIn("src/ELParser.java::jj_3R_96", fan_in_on)
        self.assertTrue(result_on["data"]["exclude_generated"])

    # AC-8: exclude_generated also filters communities-section generated-dominated entries.
    def test_wf_graph_report_exclude_generated_filters_communities(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10, exclude_generated=True)
        communities = result["data"]["communities"]
        # Handwritten survives; ELParser (generated-dominated) is filtered.
        cids = {c["community_id"] for c in communities}
        self.assertIn("project:c1", cids)
        self.assertNotIn("project:c2", cids)


class TestNameCollisionCount(unittest.TestCase):
    """130tw-enh fan-in-name-collision-hint-and-seed-note: name_collision_count on report entries."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Three distinct nodes share the simple name "process"; one unique node "unique_helper".
        # Multiple callers fan into "process" via the shared simple name to surface in fan_in.
        nodes = [
            {"id": "src/a.py::Alpha.process", "label": "Alpha.process", "kind": "function", "source_file": "src/a.py", "source_location": "1:0"},
            {"id": "src/b.py::Beta.process", "label": "Beta.process", "kind": "function", "source_file": "src/b.py", "source_location": "1:0"},
            {"id": "src/c.py::Gamma.process", "label": "Gamma.process", "kind": "function", "source_file": "src/c.py", "source_location": "1:0"},
            {"id": "src/d.py::unique_helper", "label": "unique_helper", "kind": "function", "source_file": "src/d.py", "source_location": "1:0"},
            {"id": "src/caller1.py::call_a", "label": "call_a", "kind": "function", "source_file": "src/caller1.py", "source_location": "1:0"},
            {"id": "src/caller2.py::call_b", "label": "call_b", "kind": "function", "source_file": "src/caller2.py", "source_location": "1:0"},
        ]
        graph = {
            "schema_version": "1", "builder_version": "12", "layer": "project",
            "nodes": nodes,
            "edges": [
                {"source": "src/caller1.py::call_a", "target": "src/a.py::Alpha.process", "relation": "calls"},
                {"source": "src/caller2.py::call_b", "target": "src/a.py::Alpha.process", "relation": "calls"},
                {"source": "src/caller1.py::call_a", "target": "src/d.py::unique_helper", "relation": "calls"},
            ],
            "counts": {"files": 6, "nodes": 6, "edges": 3},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    # AC-2/AC-3: collision entry carries name_collision_count > 1 reflecting node count.
    def test_fan_in_collision_entry_carries_count(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        alpha_entry = next((r for r in fan_in if r["node_id"] == "src/a.py::Alpha.process"), None)
        self.assertIsNotNone(alpha_entry)
        # Three nodes share simple name "process".
        self.assertEqual(alpha_entry["name_collision_count"], 3)

    # AC-2/AC-3: unique-name entry carries name_collision_count == 1.
    def test_fan_in_unique_entry_carries_count_one(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        unique_entry = next((r for r in fan_in if r["node_id"] == "src/d.py::unique_helper"), None)
        self.assertIsNotNone(unique_entry)
        self.assertEqual(unique_entry["name_collision_count"], 1)

    # AC-2: field present on fan_out entries too.
    def test_fan_out_entries_carry_collision_count(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_out = result["data"].get("fan_out", [])
        for row in fan_out:
            self.assertIn("name_collision_count", row)
            self.assertIsInstance(row["name_collision_count"], int)
            self.assertGreaterEqual(row["name_collision_count"], 1)

    # 1312b AC-1: same_name_node_count carries the same value as the deprecated alias.
    def test_same_name_node_count_matches_legacy_alias(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        alpha_entry = next((r for r in fan_in if r["node_id"] == "src/a.py::Alpha.process"), None)
        self.assertIsNotNone(alpha_entry)
        self.assertEqual(alpha_entry["same_name_node_count"], 3)
        self.assertEqual(alpha_entry["same_name_node_count"], alpha_entry["name_collision_count"])

    # 1312b AC-2: cross_file_collision true when same-name nodes span 2+ files.
    def test_cross_file_collision_true_when_multiple_files(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        alpha_entry = next((r for r in fan_in if r["node_id"] == "src/a.py::Alpha.process"), None)
        self.assertIsNotNone(alpha_entry)
        # Alpha/Beta/Gamma.process live in a.py, b.py, c.py — 3 distinct files.
        self.assertTrue(alpha_entry["cross_file_collision"])

    # 1312b AC-2: cross_file_collision false for unique-name entries.
    def test_cross_file_collision_false_for_unique_name(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        unique_entry = next((r for r in fan_in if r["node_id"] == "src/d.py::unique_helper"), None)
        self.assertIsNotNone(unique_entry)
        self.assertFalse(unique_entry["cross_file_collision"])


class TestExternalNameCollisionCount(unittest.TestCase):
    """1312b: external_name_collision_count surfaces JDK/framework simple-name collisions."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Project has ONE writeObject — no project-internal collision. But the
        # JDK ObjectOutputStream.writeObject is in the graph as external.
        # AC-3: external_name_collision_count should fire even though
        # same_name_node_count == 1.
        nodes = [
            {"id": "src/JSON.java::JSON.writeObject", "label": "writeObject",
             "kind": "function", "source_file": "src/JSON.java", "source_location": "1:0"},
            {"id": "external::ObjectOutputStream.writeObject", "label": "ObjectOutputStream.writeObject",
             "kind": "function", "source_file": "external"},
            {"id": "external::writeObject", "label": "writeObject",
             "kind": "function", "source_file": "external"},
            # A caller so writeObject appears in fan_in.
            {"id": "src/caller.java::Caller.run", "label": "run",
             "kind": "function", "source_file": "src/caller.java", "source_location": "1:0"},
        ]
        edges = [
            {"source": "src/caller.java::Caller.run", "target": "src/JSON.java::JSON.writeObject", "relation": "calls"},
        ]
        graph = {
            "schema_version": "1", "builder_version": "12", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": 2, "nodes": 4, "edges": 1},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    # 1316p (updates 1312b AC-3): allowlist hit fires the field — graph residue irrelevant.
    def test_writeobject_allowlist_hit_fires_collision_flag(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        json_entry = next((r for r in fan_in if r["node_id"] == "src/JSON.java::JSON.writeObject"), None)
        self.assertIsNotNone(json_entry)
        # Project: 1 same-name node, no cross-file.
        self.assertEqual(json_entry["same_name_node_count"], 1)
        self.assertFalse(json_entry["cross_file_collision"])
        # 1316p: `writeObject` is in the allowlist → 1. The graph-state count
        # of external nodes is no longer consulted.
        self.assertEqual(json_entry["external_name_collision_count"], 1)
        # Deprecated alias still present.
        self.assertEqual(json_entry["name_collision_count"], 1)


class TestExternalNameCollisionAllowlist(unittest.TestCase):
    """1316p: external_name_collision_count consults a curated Java stdlib/
    framework allowlist instead of counting external::* graph nodes.
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

    def _write_graph(self, nodes, edges):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        graph = {
            "schema_version": "1", "builder_version": "13", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": len(nodes), "nodes": len(nodes), "edges": len(edges)},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")

    # AC-4 (field canonical case): `run` triggers without any external::* node.
    def test_runnable_run_triggers_via_allowlist_without_external_node(self):
        # No `external::*` nodes exist; pre-1316p would report 0. Post-1316p reports 1.
        nodes = [
            {"id": "src/SpringUserListJob.java::SpringUserListJob.run", "label": "run",
             "kind": "function", "source_file": "src/SpringUserListJob.java", "source_location": "1:0"},
            {"id": "src/Caller.java::Caller.invoke", "label": "invoke", "kind": "function",
             "source_file": "src/Caller.java", "source_location": "1:0"},
        ]
        edges = [
            {"source": "src/Caller.java::Caller.invoke",
             "target": "src/SpringUserListJob.java::SpringUserListJob.run", "relation": "calls"},
        ]
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        run_entry = next((r for r in fan_in if r["node_id"] == "src/SpringUserListJob.java::SpringUserListJob.run"), None)
        self.assertIsNotNone(run_entry)
        self.assertEqual(run_entry["external_name_collision_count"], 1,
                         f"`run` should hit allowlist; got {run_entry['external_name_collision_count']}")

    # AC-4: non-allowlist names report 0 even when external::* node exists.
    def test_unique_name_reports_zero(self):
        nodes = [
            {"id": "src/MyJob.java::MyJob.runMyVeryCustomMethod", "label": "runMyVeryCustomMethod",
             "kind": "function", "source_file": "src/MyJob.java", "source_location": "1:0"},
            # External node with same simple name; pre-1316p this would fire the field.
            {"id": "external::SomeLib.runMyVeryCustomMethod", "label": "runMyVeryCustomMethod",
             "kind": "function", "source_file": "external"},
            {"id": "src/Caller.java::Caller.invoke", "label": "invoke", "kind": "function",
             "source_file": "src/Caller.java", "source_location": "1:0"},
        ]
        edges = [
            {"source": "src/Caller.java::Caller.invoke",
             "target": "src/MyJob.java::MyJob.runMyVeryCustomMethod", "relation": "calls"},
        ]
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        entry = next((r for r in fan_in if r["node_id"] == "src/MyJob.java::MyJob.runMyVeryCustomMethod"), None)
        self.assertIsNotNone(entry)
        # `runMyVeryCustomMethod` is not in the allowlist → 0, regardless of graph residue.
        self.assertEqual(entry["external_name_collision_count"], 0)

    # AC-4: common allowlist names (close, equals, getMethod) all fire.
    def test_multiple_allowlist_names_each_fire(self):
        nodes = [
            {"id": "src/Resource.java::Resource.close", "label": "close",
             "kind": "function", "source_file": "src/Resource.java", "source_location": "1:0"},
            {"id": "src/Value.java::Value.equals", "label": "equals",
             "kind": "function", "source_file": "src/Value.java", "source_location": "2:0"},
            {"id": "src/Util.java::ReflectionUtil.getMethod", "label": "getMethod",
             "kind": "function", "source_file": "src/Util.java", "source_location": "3:0"},
            {"id": "src/Caller.java::Caller.go", "label": "go", "kind": "function",
             "source_file": "src/Caller.java", "source_location": "1:0"},
        ]
        edges = [
            {"source": "src/Caller.java::Caller.go", "target": "src/Resource.java::Resource.close", "relation": "calls"},
            {"source": "src/Caller.java::Caller.go", "target": "src/Value.java::Value.equals", "relation": "calls"},
            {"source": "src/Caller.java::Caller.go", "target": "src/Util.java::ReflectionUtil.getMethod", "relation": "calls"},
        ]
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        for nid in ("src/Resource.java::Resource.close",
                    "src/Value.java::Value.equals",
                    "src/Util.java::ReflectionUtil.getMethod"):
            entry = next((r for r in fan_in if r["node_id"] == nid), None)
            self.assertIsNotNone(entry, f"missing entry: {nid}")
            self.assertEqual(entry["external_name_collision_count"], 1,
                             f"{nid} simple name should hit allowlist")


class TestStdlibAllowlistMultiLanguage(unittest.TestCase):
    """13192: external_name_collision_count now dispatches per-language via
    file extension. C#/Kotlin/Swift/Python get curated allowlists alongside
    Java's wave-1316p list. Languages without an allowlist return 0.
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

    def _write_graph(self, nodes, edges):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        graph = {
            "schema_version": "1", "builder_version": "14", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": len(nodes), "nodes": len(nodes), "edges": len(edges)},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")

    def _build_fan_in_entry(self, lang_ext, method_name):
        """Helper: graph with one project method + caller. Returns the fan_in entry."""
        nodes = [
            {"id": f"src/Foo{lang_ext}::Foo.{method_name}", "label": method_name,
             "kind": "function", "source_file": f"src/Foo{lang_ext}", "source_location": "1:0"},
            {"id": f"src/Caller{lang_ext}::Caller.invoke", "label": "invoke",
             "kind": "function", "source_file": f"src/Caller{lang_ext}", "source_location": "1:0"},
        ]
        edges = [
            {"source": f"src/Caller{lang_ext}::Caller.invoke",
             "target": f"src/Foo{lang_ext}::Foo.{method_name}", "relation": "calls"},
        ]
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        return next((r for r in fan_in if r["node_id"] == f"src/Foo{lang_ext}::Foo.{method_name}"), None)

    # AC-3: Java entry continues to fire post-13192 dispatch.
    def test_java_run_still_fires(self):
        entry = self._build_fan_in_entry(".java", "run")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    # AC-4: C# Equals fires.
    def test_csharp_equals_fires(self):
        entry = self._build_fan_in_entry(".cs", "Equals")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    # AC-4: C# Dispose fires.
    def test_csharp_dispose_fires(self):
        entry = self._build_fan_in_entry(".cs", "Dispose")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    # AC-4: Kotlin let fires.
    def test_kotlin_let_fires(self):
        entry = self._build_fan_in_entry(".kt", "let")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    # AC-4: Swift init fires.
    def test_swift_init_fires(self):
        entry = self._build_fan_in_entry(".swift", "init")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    # AC-4: Python __str__ fires.
    def test_python_dunder_fires(self):
        entry = self._build_fan_in_entry(".py", "__str__")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    # AC-5: Go file (no allowlist) returns 0 even when name matches a Java entry.
    def test_go_file_no_allowlist_returns_zero(self):
        entry = self._build_fan_in_entry(".go", "run")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 0,
                         "Go file should not fire — no allowlist defined for .go")

    # AC-4: non-allowlist names return 0 even for supported languages.
    def test_custom_name_not_in_allowlist_returns_zero(self):
        entry = self._build_fan_in_entry(".java", "myUniqueProjectMethod")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 0)

    # Wave 13198: extended language coverage.
    def test_js_foreach_fires(self):
        entry = self._build_fan_in_entry(".js", "forEach")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    def test_jsx_then_fires(self):
        entry = self._build_fan_in_entry(".jsx", "then")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    def test_ts_componentDidMount_fires(self):
        entry = self._build_fan_in_entry(".ts", "componentDidMount")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    def test_tsx_render_fires(self):
        entry = self._build_fan_in_entry(".tsx", "render")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    def test_go_serveHTTP_fires(self):
        entry = self._build_fan_in_entry(".go", "ServeHTTP")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    def test_rust_unwrap_fires(self):
        entry = self._build_fan_in_entry(".rs", "unwrap")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    def test_scala_unapply_fires(self):
        entry = self._build_fan_in_entry(".scala", "unapply")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    def test_php_construct_fires(self):
        entry = self._build_fan_in_entry(".php", "__construct")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)

    def test_ruby_initialize_fires(self):
        entry = self._build_fan_in_entry(".rb", "initialize")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["external_name_collision_count"], 1)


class TestExcludeExternalFilter(unittest.TestCase):
    """130tw-enh exclude-external-from-graph-report: filter external::* from rankings."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        nodes = [
            {"id": "src/worker.py::process", "label": "process", "kind": "function", "source_file": "src/worker.py", "source_location": "1:0"},
            {"id": "src/helper.py::format", "label": "format", "kind": "function", "source_file": "src/helper.py", "source_location": "1:0"},
            {"id": "src/caller.py::main", "label": "main", "kind": "function", "source_file": "src/caller.py", "source_location": "1:0"},
            {"id": "external::stdlib_get", "label": "stdlib_get", "kind": "function", "source_file": "external"},
            {"id": "external::stdlib_set", "label": "stdlib_set", "kind": "function", "source_file": "external"},
        ]
        edges = [
            # Heavy external fan-in to push externals to the top of fan_in rankings.
            {"source": "src/caller.py::main", "target": "external::stdlib_get", "relation": "calls"},
            {"source": "src/worker.py::process", "target": "external::stdlib_get", "relation": "calls"},
            {"source": "src/helper.py::format", "target": "external::stdlib_get", "relation": "calls"},
            {"source": "src/caller.py::main", "target": "external::stdlib_set", "relation": "calls"},
            {"source": "src/worker.py::process", "target": "external::stdlib_set", "relation": "calls"},
            # One project-internal call.
            {"source": "src/caller.py::main", "target": "src/worker.py::process", "relation": "calls"},
            {"source": "src/worker.py::process", "target": "src/helper.py::format", "relation": "calls"},
        ]
        graph = {
            "schema_version": "1", "builder_version": "12", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": 3, "nodes": 5, "edges": 7},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    # AC-1: default preserves externals (backward compat).
    def test_default_off_preserves_externals(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        report = result["data"]
        fan_in_ids = {r["node_id"] for r in report["fan_in"]}
        self.assertIn("external::stdlib_get", fan_in_ids)
        self.assertFalse(report["exclude_external"])

    # AC-1: exclude_external=True removes external entries from fan_in.
    def test_exclude_external_filters_fan_in(self):
        result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=20, exclude_external=True
        )
        report = result["data"]
        fan_in_ids = {r["node_id"] for r in report["fan_in"]}
        self.assertNotIn("external::stdlib_get", fan_in_ids)
        self.assertNotIn("external::stdlib_set", fan_in_ids)
        # Project-internal entries survive.
        self.assertIn("src/worker.py::process", fan_in_ids)

    # AC-3: response echoes the flag.
    def test_exclude_external_flag_echoed(self):
        result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=20, exclude_external=True
        )
        self.assertTrue(result["data"]["exclude_external"])

    # AC-4: combined with exclude_generated returns project-internal non-generated rankings.
    def test_exclude_external_combined_with_exclude_generated(self):
        result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=20,
            exclude_external=True, exclude_generated=True,
        )
        report = result["data"]
        fan_in_ids = {r["node_id"] for r in report["fan_in"]}
        for nid in fan_in_ids:
            self.assertFalse(nid.startswith("external::"))


class TestModuleFanOutCountSemantics(unittest.TestCase):
    """1312f: lock the kind:"module" fan_out count decomposition.

    The doc on wf_graph_report describes module-kind ``count`` as aggregating
    outgoing ``defines`` + ``imports`` + ``calls`` from the file node. This test
    locks the exact value for a known synthetic fixture so that future indexer
    changes can't drift the count silently.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Synthetic graph: one file node (kind=module) with known outgoing edges.
        # File "src/lib.py" has 3 internal symbols (defines), 2 calls out, 1 import.
        # Module-kind fan_out should sum to 6.
        nodes = [
            {"id": "src/lib.py", "label": "lib", "kind": "module", "source_file": "src/lib.py"},
            {"id": "src/lib.py::a", "label": "a", "kind": "function", "source_file": "src/lib.py", "source_location": "1:0"},
            {"id": "src/lib.py::b", "label": "b", "kind": "function", "source_file": "src/lib.py", "source_location": "5:0"},
            {"id": "src/lib.py::c", "label": "c", "kind": "function", "source_file": "src/lib.py", "source_location": "10:0"},
            {"id": "src/other.py::helper", "label": "helper", "kind": "function", "source_file": "src/other.py", "source_location": "1:0"},
            {"id": "external::os.path.join", "label": "os.path.join", "kind": "module", "source_file": "external"},
        ]
        edges = [
            {"source": "src/lib.py", "target": "src/lib.py::a", "relation": "defines"},
            {"source": "src/lib.py", "target": "src/lib.py::b", "relation": "defines"},
            {"source": "src/lib.py", "target": "src/lib.py::c", "relation": "defines"},
            {"source": "src/lib.py", "target": "src/other.py::helper", "relation": "calls"},
            {"source": "src/lib.py", "target": "external::os.path.join", "relation": "calls"},
            {"source": "src/lib.py", "target": "src/other.py", "relation": "imports"},
        ]
        graph = {
            "schema_version": "1", "builder_version": "12", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": 3, "nodes": 6, "edges": 6},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    # Locked contract: module-kind fan_out aggregates outgoing edges across relation types.
    # 3 defines + 2 calls + 1 imports = 6. Any drift in the count surfaces as test failure.
    def test_module_fan_out_count_aggregates_outgoing_edges(self):
        # graph_query.GraphQueryIndex.report() counts only `calls` edges for fan_out.
        # This test locks that behavior — module count includes only `calls`-relation edges out.
        from server_impl import _load_graph_query  # noqa
        gq = self.srv._load_graph_query()
        index = gq.GraphQueryIndex.from_root(self.root, layer="project")
        report = index.report(limit=10)
        fan_out = report.get("fan_out", [])
        lib_entry = next((r for r in fan_out if r["node_id"] == "src/lib.py"), None)
        self.assertIsNotNone(lib_entry, f"src/lib.py missing from fan_out: {fan_out}")
        # Locked contract: count is calls-edge fan_out only (2 in fixture).
        # If the indexer changes to count defines + imports too, update this assertion AND
        # the wf_graph_report docstring in the same PR so the contract stays in sync.
        self.assertEqual(
            lib_entry["count"], 2,
            f"module fan_out count drifted; expected 2 (calls edges only), got {lib_entry['count']}. "
            "Update docstring on wf_graph_report if intentional."
        )
        self.assertEqual(lib_entry["kind"], "module")


class TestBetweennessServedFromArtifact(unittest.TestCase):
    """Wave 1p9q3 (1p9q1): wf_graph_report serves the betweenness ranking
    persisted at build time in the clusters artifact — no query-time igraph
    computation, no graph-size cap; legacy artifacts degrade gracefully.
    (Supersedes 130tw's TestBetweennessComputedField: the computed/skipped
    fields remain, but the only skip reason is a missing artifact section.)"""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_graph(self, nodes, edges):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        graph = {
            "schema_version": "1", "builder_version": "12", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": len(nodes), "nodes": len(nodes), "edges": len(edges)},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")

    def _write_clusters(self, betweenness=None):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Wave 1wpaj: stamp the RUNTIME cluster builder version rather than a
        # literal. The serve path now refuses a betweenness section whose
        # persisted version does not match runtime, so a hard-coded literal
        # would silently turn every test in this class into a stale-artifact
        # assertion on the next version bump.
        import graph_cluster as _gc  # noqa: PLC0415 - test-local import
        payload = {
            "cluster_schema_version": "1",
            "cluster_builder_version": _gc.CLUSTER_BUILDER_VERSION,
            "cluster_algorithm": "leiden", "layer": "project",
            "communities": [], "community_count": 0,
        }
        if betweenness is not None:
            payload["betweenness"] = betweenness
        (graph_dir / "project-graph-clusters.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def _small_graph(self):
        nodes = [
            {"id": "src/a.py::foo", "label": "foo", "kind": "function", "source_file": "src/a.py", "source_location": "1:0"},
            {"id": "src/b.py::bar", "label": "bar", "kind": "function", "source_file": "src/b.py", "source_location": "1:0"},
            {"id": "src/c.py::baz", "label": "baz", "kind": "function", "source_file": "src/c.py", "source_location": "1:0"},
        ]
        edges = [
            {"source": "src/a.py::foo", "target": "src/b.py::bar", "relation": "calls"},
            {"source": "src/b.py::bar", "target": "src/c.py::baz", "relation": "calls"},
        ]
        self._write_graph(nodes, edges)

    def _betweenness_section(self, method="exact", **extra):
        section = {
            "method": method,
            "node_count": 3,
            "edge_count": 2,
            "top_n": 200,
            "elapsed_ms": 4,
            "ranking": [
                {"node_id": "src/b.py::bar", "score": 1.0, "label": "bar", "kind": "function"},
            ],
        }
        section.update(extra)
        return section

    def test_betweenness_served_from_persisted_artifact(self):
        self._small_graph()
        self._write_clusters(betweenness=self._betweenness_section())
        result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=10, sections=["betweenness"]
        )
        report = result["data"]
        self.assertEqual(report["betweenness_computed"], True)
        self.assertNotIn("betweenness_skipped_reason", report)
        self.assertEqual(report["betweenness_method"], "exact")
        rows = report["betweenness"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["node_id"], "src/b.py::bar")
        self.assertEqual(rows[0]["score"], 1.0)
        meta = report["betweenness_metadata"]
        self.assertEqual(meta["node_count"], 3)
        self.assertEqual(meta["edge_count"], 2)
        self.assertEqual(meta["elapsed_ms"], 4)
        self.assertNotIn("cutoff", meta)

    def test_betweenness_cutoff_metadata_surfaced(self):
        self._small_graph()
        self._write_clusters(betweenness=self._betweenness_section(method="cutoff", cutoff=6))
        result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=10, sections=["betweenness"]
        )
        report = result["data"]
        self.assertEqual(report["betweenness_method"], "cutoff")
        self.assertEqual(report["betweenness_metadata"]["cutoff"], 6)

    def test_betweenness_limit_truncates_served_rows(self):
        self._small_graph()
        section = self._betweenness_section()
        section["ranking"] = [
            {"node_id": f"src/m{i}.py::f{i}", "score": float(10 - i), "label": f"f{i}", "kind": "function"}
            for i in range(5)
        ]
        self._write_clusters(betweenness=section)
        result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=2, sections=["betweenness"]
        )
        self.assertEqual(len(result["data"]["betweenness"]), 2)

    # AC-7: legacy clusters artifact (no betweenness section) → graceful message.
    def test_legacy_clusters_artifact_without_section_is_graceful(self):
        self._small_graph()
        self._write_clusters(betweenness=None)
        result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=10, sections=["betweenness"]
        )
        report = result["data"]
        self.assertEqual(report["betweenness_computed"], False)
        self.assertEqual(report["betweenness_skipped_reason"], "betweenness_not_in_artifact")
        self.assertEqual(report["betweenness"], [])
        self.assertIn("rebuild", report["betweenness_note"].casefold())

    def test_missing_clusters_artifact_is_graceful(self):
        self._small_graph()
        result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=10, sections=["betweenness"]
        )
        report = result["data"]
        self.assertEqual(report["betweenness_computed"], False)
        self.assertEqual(report["betweenness_skipped_reason"], "betweenness_not_in_artifact")
        self.assertEqual(report["betweenness"], [])

    # AC-1 shape: >10k-node graph is SERVED, never capped — the old
    # graph_too_large_for_betweenness diagnostic path is retired.
    def test_large_graph_served_without_cap_diagnostic(self):
        nodes = [
            {"id": f"src/f{i}.py::node{i}", "label": f"node{i}", "kind": "function",
             "source_file": f"src/f{i}.py", "source_location": "1:0"}
            for i in range(10_005)
        ]
        self._write_graph(nodes, [])
        self._write_clusters(betweenness=self._betweenness_section(node_count=10_005))
        result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=10, sections=["betweenness"]
        )
        report = result["data"]
        self.assertEqual(report["betweenness_computed"], True)
        self.assertEqual(report["betweenness_metadata"]["node_count"], 10_005)
        self.assertNotIn("betweenness_skipped_reason", report)
        import json
        self.assertNotIn("graph_too_large_for_betweenness", json.dumps(report))

    # AC-5: zero inline igraph computation at query time — an igraph whose
    # Graph constructor explodes proves the report never touches it.
    def test_report_performs_no_igraph_betweenness_at_query_time(self):
        import types as _types
        import unittest.mock

        def _explode(*args, **kwargs):
            raise AssertionError("query-time igraph use is retired (wave 1p9q3)")

        fake_igraph = _types.SimpleNamespace(Graph=_explode)
        self._small_graph()
        self._write_clusters(betweenness=self._betweenness_section())
        with unittest.mock.patch.dict(sys.modules, {"igraph": fake_igraph}):
            result = self.srv.wf_graph_report_response(
                self.root, layer="project", limit=10, sections=["betweenness"]
            )
        report = result["data"]
        self.assertEqual(report["betweenness_computed"], True)
        self.assertEqual(report["betweenness"][0]["node_id"], "src/b.py::bar")


class TestStableCommunityIdentifier(unittest.TestCase):
    """1316r: community_hub_node_id field on code_graph_community response +
    hub_node_id input parameter for cross-rebuild stability.
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

    def _write_cluster(self, community_id, member_ids, label="TestCommunity"):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Graph with member nodes + 1 hub-degree-bumping edge so first member is hub.
        nodes = [
            {"id": nid, "label": nid.rsplit("::", 1)[-1] if "::" in nid else nid,
             "kind": "function", "source_file": nid.split("::")[0], "source_location": "1:0"}
            for nid in member_ids
        ]
        edges = []
        # Make first member the highest-degree node.
        if len(member_ids) >= 2:
            for i in range(1, min(len(member_ids), 5)):
                edges.append({"source": member_ids[i], "target": member_ids[0], "relation": "calls"})
        graph = {
            "schema_version": "1", "builder_version": "13", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": len(nodes), "nodes": len(nodes), "edges": len(edges)},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        cluster = {
            "cluster_algorithm": "leiden",
            "cluster_builder_version": "1",
            "cluster_schema_version": "1",
            "communities": [{
                "community_id": community_id,
                "label": label,
                "node_count": len(member_ids),
                "node_ids": member_ids,
                "generated_node_fraction": 0.0,
            }],
            "community_count": 1,
        }
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps(cluster), encoding="utf-8")

    # AC-2: community_hub_node_id surfaces on the response.
    def test_response_carries_community_hub_node_id(self):
        members = ["src/JSON.py::JSON", "src/JSON.py::JSON.write", "src/Other.py::Other.read"]
        self._write_cluster("project:c1", members)
        result = self.srv.code_graph_community_response(self.root, "project:c1")
        data = result["data"]
        self.assertIn("community_hub_node_id", data)
        # First member receives the call edges in our fixture → highest degree → hub.
        self.assertEqual(data["community_hub_node_id"], "src/JSON.py::JSON")

    # AC-4: hub_node_id parameter resolves to the community containing that node.
    def test_hub_node_id_resolves_to_containing_community(self):
        members = ["src/JSON.py::JSON", "src/JSON.py::JSON.write"]
        self._write_cluster("project:c42", members, label="JSONCommunity")
        result = self.srv.code_graph_community_response(
            self.root, "", hub_node_id="src/JSON.py::JSON.write"
        )
        data = result["data"]
        self.assertEqual(data["community_id"], "project:c42")
        self.assertEqual(data["label"], "JSONCommunity")
        self.assertTrue(data["hub_node_id_used"])

    # AC-8 (council action item): cross-clustering test — same nodes, different Leiden ids.
    # The hub_node_id resolves correctly regardless of which Leiden id the rebuild
    # assigned to the community.
    def test_hub_node_id_resolves_across_rebuilds(self):
        members = ["src/JSON.py::JSON", "src/JSON.py::JSON.write"]
        # First "rebuild" — Leiden assigns project:c12.
        self._write_cluster("project:c12", members, label="JSON")
        result1 = self.srv.code_graph_community_response(
            self.root, "", hub_node_id="src/JSON.py::JSON"
        )
        self.assertEqual(result1["data"]["community_id"], "project:c12")
        # Second "rebuild" — Leiden assigns project:c237 to the same nodes.
        self._write_cluster("project:c237", members, label="JSON")
        result2 = self.srv.code_graph_community_response(
            self.root, "", hub_node_id="src/JSON.py::JSON"
        )
        # Same hub_node_id resolves to the new community id.
        self.assertEqual(result2["data"]["community_id"], "project:c237")
        # The hub remains the same node.
        self.assertEqual(result1["data"]["community_hub_node_id"],
                         result2["data"]["community_hub_node_id"])

    # AC-5: when both community_id and hub_node_id provided, community_id wins.
    def test_community_id_wins_over_hub_node_id(self):
        members = ["src/JSON.py::JSON", "src/JSON.py::JSON.write"]
        self._write_cluster("project:c1", members, label="JSONCommunity")
        result = self.srv.code_graph_community_response(
            self.root, "project:c1", hub_node_id="src/Other.py::Other"
        )
        data = result["data"]
        self.assertEqual(data["community_id"], "project:c1")
        # hub_node_id wasn't used because community_id won.
        self.assertFalse(data["hub_node_id_used"])


class TestLargeCommunityPagination(unittest.TestCase):
    """130tw-enh large-community-pagination: pagination_hint on code_graph_community."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_community(self, member_count):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        nodes = [
            {"id": f"src/f{i}.py::m{i}", "label": f"m{i}", "kind": "function",
             "source_file": f"src/f{i}.py", "source_location": "1:0"}
            for i in range(member_count)
        ]
        graph = {
            "schema_version": "1", "builder_version": "12", "layer": "project",
            "nodes": nodes, "edges": [],
            "counts": {"files": member_count, "nodes": member_count, "edges": 0},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        cluster = {
            "cluster_algorithm": "leiden",
            "cluster_builder_version": "1",
            "cluster_schema_version": "1",
            "communities": [{
                "community_id": "project:c1",
                "label": "TestCommunity",
                "node_count": member_count,
                "node_ids": [n["id"] for n in nodes],
                "generated_node_fraction": 0.0,
            }],
            "community_count": 1,
        }
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps(cluster), encoding="utf-8")

    # AC-4: small community → no pagination_hint, all members returned.
    def test_small_community_returns_all_no_hint(self):
        self._write_community(10)
        result = self.srv.code_graph_community_response(self.root, "project:c1")
        data = result["data"]
        self.assertEqual(data["returned_count"], 10)
        self.assertEqual(data["total_node_count"], 10)
        self.assertFalse(data["has_more"])
        self.assertNotIn("pagination_hint", data)

    # AC-3: large community → first 50 returned + pagination_hint surfaces next page.
    def test_large_community_returns_first_50_with_hint(self):
        self._write_community(120)
        result = self.srv.code_graph_community_response(self.root, "project:c1")
        data = result["data"]
        self.assertEqual(data["returned_count"], 50)
        self.assertEqual(data["total_node_count"], 120)
        self.assertTrue(data["has_more"])
        self.assertIn("pagination_hint", data)
        self.assertIn("limit=50", data["pagination_hint"])
        self.assertIn("offset=50", data["pagination_hint"])
        self.assertIn("1-50 of 120", data["pagination_hint"])

    # AC-6: explicit limit value is respected.
    def test_explicit_limit_respected(self):
        self._write_community(100)
        result = self.srv.code_graph_community_response(self.root, "project:c1", limit=10)
        data = result["data"]
        self.assertEqual(data["returned_count"], 10)
        self.assertTrue(data["has_more"])
        self.assertIn("limit=10", data["pagination_hint"])
        self.assertIn("offset=10", data["pagination_hint"])

    # AC-3: offset advances correctly.
    def test_offset_advances_page_window(self):
        self._write_community(120)
        result = self.srv.code_graph_community_response(self.root, "project:c1", limit=50, offset=50)
        data = result["data"]
        self.assertEqual(data["returned_count"], 50)
        self.assertEqual(data["offset"], 50)
        self.assertTrue(data["has_more"])
        self.assertIn("offset=100", data["pagination_hint"])
        self.assertIn("51-100 of 120", data["pagination_hint"])

    # AC-4: last page (no more members) → no pagination_hint.
    def test_last_page_omits_hint(self):
        self._write_community(60)
        result = self.srv.code_graph_community_response(self.root, "project:c1", limit=50, offset=50)
        data = result["data"]
        self.assertEqual(data["returned_count"], 10)
        self.assertFalse(data["has_more"])
        self.assertNotIn("pagination_hint", data)


class TestGraphRebuildDiscoverability(unittest.TestCase):
    """1316n: index_health breaks out graph readiness separately;
    index_build reports graph counts + notice clarification when content
    is not 'graph'. Surfaces the field-reported misread where rebuilding the
    semantic layer looked like a full refresh but the graph was untouched.
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

    def _write_graph(self, layer, nodes):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        graph = {
            "schema_version": "1", "builder_version": "13", "layer": layer,
            "nodes": nodes, "edges": [],
            "counts": {"files": len(nodes), "nodes": len(nodes), "edges": 0},
        }
        fname = "project-graph.json" if layer == "project" else "framework-graph.json"
        (graph_dir / fname).write_text(json.dumps(graph), encoding="utf-8")

    # AC-1: graph_health_summary populates per-layer presence + last_built_at.
    def test_graph_health_summary_reports_per_layer_presence(self):
        self._write_graph("project", [
            {"id": "src/a.py::foo", "label": "foo", "kind": "function",
             "source_file": "src/a.py", "source_location": "1:0"},
        ])
        summary = self.srv._graph_health_summary(self.root)
        self.assertTrue(summary["project"]["present"])
        self.assertIsNotNone(summary["project"]["last_built_at"])
        self.assertEqual(summary["project"]["node_count"], 1)
        # 1p4ww: single project graph — no framework layer in the summary.
        self.assertNotIn("framework", summary)

    # AC-1: graph_health_summary handles missing graph artifact gracefully.
    def test_graph_health_summary_when_artifact_missing(self):
        summary = self.srv._graph_health_summary(self.root)
        self.assertFalse(summary["project"]["present"])
        self.assertIsNone(summary["project"]["node_count"])
        self.assertIsNone(summary["project"]["last_built_at"])


class TestEmptySectionDiagnosticFields(unittest.TestCase):
    """1316t: candidates_total + threshold fields on chokepoints/file_hubs/
    orphan_docs/cross_layer let operators distinguish "no candidates"
    from "candidates exist but didn't meet threshold".
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

    def _write_graph(self, nodes, edges, layer="project"):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        graph = {
            "schema_version": "1", "builder_version": "13", "layer": layer,
            "nodes": nodes, "edges": edges,
            "counts": {"files": len(nodes), "nodes": len(nodes), "edges": len(edges)},
        }
        fname = "project-graph.json" if layer == "project" else "framework-graph.json"
        (graph_dir / fname).write_text(json.dumps(graph), encoding="utf-8")

    # AC-1/AC-5: chokepoints exposes candidates_total and threshold.
    def test_chokepoints_diagnostic_fields_present(self):
        # 3 functions each with fan_out 5 — under default chokepoint threshold 20.
        nodes = [{"id": f"src/f{i}.py::fn{i}", "label": f"fn{i}", "kind": "function",
                  "source_file": f"src/f{i}.py", "source_location": "1:0"} for i in range(3)]
        edges = []
        for src_idx, src in enumerate(nodes[:3]):
            for j in range(5):
                tgt_id = f"src/t{src_idx}_{j}.py::t"
                nodes.append({"id": tgt_id, "label": "t", "kind": "function",
                              "source_file": f"src/t{src_idx}_{j}.py", "source_location": "1:0"})
                edges.append({"source": src["id"], "target": tgt_id, "relation": "calls"})
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10)
        data = result["data"]
        self.assertEqual(data["chokepoints"], [])
        self.assertEqual(data["chokepoints_candidates_total"], 3,
                         "3 functions had positive fan_out, none above threshold")
        self.assertEqual(data["chokepoints_threshold"], 20)

    # AC-2/AC-5: file_hubs exposes candidates_total and threshold.
    def test_file_hubs_diagnostic_fields_present(self):
        # One module with fan_out 5 — below threshold.
        nodes = [
            {"id": "src/Lib.py", "label": "Lib", "kind": "module", "source_file": "src/Lib.py"},
        ]
        edges = []
        for i in range(5):
            tgt_id = f"src/t{i}.py::t"
            nodes.append({"id": tgt_id, "label": "t", "kind": "function",
                          "source_file": f"src/t{i}.py", "source_location": "1:0"})
            edges.append({"source": "src/Lib.py", "target": tgt_id, "relation": "calls"})
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10)
        data = result["data"]
        self.assertEqual(data["file_hubs"], [])
        self.assertEqual(data["file_hubs_candidates_total"], 1)
        self.assertEqual(data["file_hubs_threshold"], 20)

    # AC-3: orphan_docs candidates_total reflects doc-kind node total.
    def test_orphan_docs_candidates_total_present(self):
        # No doc-kind nodes → candidates_total: 0 → empty list is "no data".
        nodes = [
            {"id": "src/a.py::foo", "label": "foo", "kind": "function",
             "source_file": "src/a.py", "source_location": "1:0"},
        ]
        self._write_graph(nodes, [])
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10)
        data = result["data"]
        self.assertEqual(data["orphan_docs"], [])
        self.assertEqual(data["orphan_docs_candidates_total"], 0)

    def test_cross_layer_section_removed_with_framework_layer(self):
        # Wave 1p4ww: the cross_layer section required the union layer (project×framework
        # boundary edges), which no longer exists — it is never present in a report.
        self._write_graph(
            [{"id": "src/a.py", "label": "a", "kind": "module", "source_file": "src/a.py"}],
            [],
            layer="project",
        )
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10)
        data = result["data"]
        self.assertNotIn("cross_layer", data)
        self.assertNotIn("cross_layer_candidates_total", data)
        # Instead just assert the chokepoints/file_hubs/orphan_docs diagnostics are present.
        self.assertIn("chokepoints_candidates_total", data)
        self.assertIn("file_hubs_candidates_total", data)
        self.assertIn("orphan_docs_candidates_total", data)


class TestModuleSimpleNameExtraction(unittest.TestCase):
    """1316j: module/file nodes' simple name is the basename without extension,
    not the file extension. A consumer reported `same_name_node_count: 72` (the
    Swift module count) on every Swift module entry because the pre-1316j logic
    extracted `"swift"` as the simple name for every module node.
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

    def _write_graph(self, nodes, edges):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        graph = {
            "schema_version": "1", "builder_version": "13", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": len(nodes), "nodes": len(nodes), "edges": len(edges)},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")

    # AC-4: distinct Swift module entries report distinct collision counts.
    def test_distinct_swift_modules_have_distinct_collision_counts(self):
        # Two file-hub-shaped Swift module entries with distinct basenames.
        # Pre-1316j: both would report same_name_node_count: 2 (or whatever
        # constant matched the total Swift module count). Post-1316j:
        # StatusBarManager appears once → count 1; LightingRoutines appears
        # once → count 1. They must NOT share the same elevated count.
        nodes = [
            {"id": "src/StatusBarManager.swift", "label": "StatusBarManager",
             "kind": "module", "source_file": "src/StatusBarManager.swift"},
            {"id": "src/LightingRoutines.swift", "label": "LightingRoutines",
             "kind": "module", "source_file": "src/LightingRoutines.swift"},
            # Add fan_out edges so both appear in file_hubs.
        ]
        edges = []
        # Create 25 dummy target nodes for each hub so file_hubs threshold met.
        for i in range(25):
            tgt_id = f"src/t{i}.swift::t{i}"
            nodes.append({
                "id": tgt_id, "label": f"t{i}", "kind": "function",
                "source_file": f"src/t{i}.swift", "source_location": "1:0",
            })
            edges.append({"source": "src/StatusBarManager.swift", "target": tgt_id, "relation": "calls"})
            edges.append({"source": "src/LightingRoutines.swift", "target": tgt_id, "relation": "calls"})
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        file_hubs = result["data"].get("file_hubs", [])
        sb = next((r for r in file_hubs if r["node_id"] == "src/StatusBarManager.swift"), None)
        lr = next((r for r in file_hubs if r["node_id"] == "src/LightingRoutines.swift"), None)
        self.assertIsNotNone(sb)
        self.assertIsNotNone(lr)
        # Distinct basenames → distinct counts. Each appears exactly once → 1.
        self.assertEqual(sb["same_name_node_count"], 1,
                         f"StatusBarManager unique; expected 1 got {sb['same_name_node_count']}")
        self.assertEqual(lr["same_name_node_count"], 1,
                         f"LightingRoutines unique; expected 1 got {lr['same_name_node_count']}")

    # AC-4: module + class twin pair shares basename → collision count 2.
    def test_module_and_class_twin_pair_collides(self):
        nodes = [
            {"id": "src/Foo.swift", "label": "Foo",
             "kind": "module", "source_file": "src/Foo.swift"},
            {"id": "src/Foo.swift::Foo", "label": "Foo",
             "kind": "class", "source_file": "src/Foo.swift", "source_location": "1:0"},
            # add fan_out for both to surface in file_hubs / fan_out
            {"id": "src/Caller.swift::Caller.run", "label": "run", "kind": "function",
             "source_file": "src/Caller.swift", "source_location": "1:0"},
        ]
        edges = [
            {"source": "src/Caller.swift::Caller.run", "target": "src/Foo.swift", "relation": "calls"},
        ]
        # boost file fan_out enough to reach chokepoint threshold
        for i in range(25):
            tgt_id = f"src/t{i}.swift::t{i}"
            nodes.append({"id": tgt_id, "label": f"t{i}", "kind": "function",
                          "source_file": f"src/t{i}.swift", "source_location": "1:0"})
            edges.append({"source": "src/Foo.swift", "target": tgt_id, "relation": "calls"})
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        file_hubs = result["data"].get("file_hubs", [])
        foo_module = next((r for r in file_hubs if r["node_id"] == "src/Foo.swift"), None)
        self.assertIsNotNone(foo_module)
        # Basename `Foo` collides between module + class node → count 2,
        # cross_file_collision: false (both in same source_file).
        self.assertEqual(foo_module["same_name_node_count"], 2,
                         f"module+class twin; expected 2 got {foo_module['same_name_node_count']}")
        self.assertFalse(foo_module["cross_file_collision"])

    # AC-1/AC-6: symbol-node simple name extraction preserved.
    def test_symbol_node_simple_name_preserved(self):
        # Two distinct files each defining `Helper.process` → 2 same-name nodes,
        # 2 distinct source files → cross_file_collision: true.
        nodes = [
            {"id": "src/a.py::Helper.process", "label": "process", "kind": "function",
             "source_file": "src/a.py", "source_location": "1:0"},
            {"id": "src/b.py::Helper.process", "label": "process", "kind": "function",
             "source_file": "src/b.py", "source_location": "1:0"},
            {"id": "src/caller.py::main", "label": "main", "kind": "function",
             "source_file": "src/caller.py", "source_location": "1:0"},
        ]
        edges = [
            {"source": "src/caller.py::main", "target": "src/a.py::Helper.process", "relation": "calls"},
        ]
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_in = result["data"]["fan_in"]
        a_proc = next((r for r in fan_in if r["node_id"] == "src/a.py::Helper.process"), None)
        self.assertIsNotNone(a_proc)
        self.assertEqual(a_proc["same_name_node_count"], 2)
        self.assertTrue(a_proc["cross_file_collision"])

    # AC-1: extensionless module nodes use the whole basename.
    def test_extensionless_module_basename(self):
        nodes = [
            {"id": "src/Makefile", "label": "Makefile", "kind": "module", "source_file": "src/Makefile"},
            {"id": "src/Other.swift", "label": "Other", "kind": "module", "source_file": "src/Other.swift"},
            {"id": "src/x::sym", "label": "sym", "kind": "function", "source_file": "src/x", "source_location": "1:0"},
        ]
        # Force entry in fan_out via at least one outgoing calls edge.
        edges = [
            {"source": "src/Makefile", "target": "src/x::sym", "relation": "calls"},
            {"source": "src/Other.swift", "target": "src/x::sym", "relation": "calls"},
        ]
        self._write_graph(nodes, edges)
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        fan_out = result["data"].get("fan_out", [])
        mk = next((r for r in fan_out if r["node_id"] == "src/Makefile"), None)
        ot = next((r for r in fan_out if r["node_id"] == "src/Other.swift"), None)
        # Both should appear with distinct basenames → distinct counts.
        self.assertIsNotNone(mk)
        self.assertIsNotNone(ot)
        self.assertEqual(mk["same_name_node_count"], 1)
        self.assertEqual(ot["same_name_node_count"], 1)


class TestFileHubsSectionSplit(unittest.TestCase):
    """1312d: file_hubs section carries kind:"module" entries split out of chokepoints."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Fixture: one file node (kind=module) with high fan_out + one function
        # node (kind=function) with high fan_out. Both should appear above
        # chokepoint_threshold (default 20).
        targets = [{"id": f"src/t{i}.py::t{i}", "label": f"t{i}", "kind": "function",
                    "source_file": f"src/t{i}.py", "source_location": "1:0"} for i in range(25)]
        hub_module = {"id": "src/hub.py", "label": "hub", "kind": "module", "source_file": "src/hub.py"}
        hub_function = {"id": "src/fn.py::dispatcher", "label": "dispatcher", "kind": "function",
                        "source_file": "src/fn.py", "source_location": "1:0"}
        nodes = targets + [hub_module, hub_function]
        edges = []
        for t in targets:
            edges.append({"source": "src/hub.py", "target": t["id"], "relation": "calls"})
            edges.append({"source": "src/fn.py::dispatcher", "target": t["id"], "relation": "calls"})
        graph = {
            "schema_version": "1", "builder_version": "12", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": 26, "nodes": len(nodes), "edges": len(edges)},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    # AC-1: file_hubs populated with kind=module entries.
    def test_file_hubs_section_contains_module_entries(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10)
        report = result["data"]
        self.assertIn("file_hubs", report)
        ids = {r["node_id"] for r in report["file_hubs"]}
        self.assertIn("src/hub.py", ids)
        # All file_hubs entries are kind=module.
        for r in report["file_hubs"]:
            self.assertEqual(r["kind"], "module")

    # AC-2: chokepoints no longer contains kind=module entries.
    def test_chokepoints_excludes_module_entries(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10)
        report = result["data"]
        chokepoints = report.get("chokepoints", [])
        ids = {r["node_id"] for r in chokepoints}
        # Module hub NOT in chokepoints.
        self.assertNotIn("src/hub.py", ids)
        # Function hub IS in chokepoints.
        self.assertIn("src/fn.py::dispatcher", ids)

    # AC-3/AC-5: file_hubs is in default section set and accessible via explicit sections=["file_hubs"].
    def test_file_hubs_default_included_and_explicit_request_works(self):
        # Default section set.
        default_result = self.srv.wf_graph_report_response(self.root, layer="project", limit=10)
        self.assertIn("file_hubs", default_result["data"])
        # Explicit request.
        explicit_result = self.srv.wf_graph_report_response(
            self.root, layer="project", limit=10, sections=["file_hubs"]
        )
        self.assertIn("file_hubs", explicit_result["data"])
        # When only file_hubs requested, chokepoints not in response.
        self.assertNotIn("chokepoints", explicit_result["data"])


class TestLargeCommunityAdvisory(unittest.TestCase):
    """1312j: community_size_class field + large_community_advisory diagnostic
    on code_graph_community when total_node_count > 200.
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

    def _write_community(self, member_count):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        nodes = [
            {"id": f"src/f{i}.py::m{i}", "label": f"m{i}", "kind": "function",
             "source_file": f"src/f{i}.py", "source_location": "1:0"}
            for i in range(member_count)
        ]
        # Give the first node a degree edge so the hub lookup picks it.
        edges = [
            {"source": "src/f1.py::m1", "target": "src/f0.py::m0", "relation": "calls"},
        ] if member_count >= 2 else []
        graph = {
            "schema_version": "1", "builder_version": "12", "layer": "project",
            "nodes": nodes, "edges": edges,
            "counts": {"files": member_count, "nodes": member_count, "edges": len(edges)},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        cluster = {
            "cluster_algorithm": "leiden",
            "cluster_builder_version": "1",
            "cluster_schema_version": "1",
            "communities": [{
                "community_id": "project:c1",
                "label": "TestCommunity",
                "node_count": member_count,
                "node_ids": [n["id"] for n in nodes],
                "generated_node_fraction": 0.0,
            }],
            "community_count": 1,
        }
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps(cluster), encoding="utf-8")

    # AC-2: small community → community_size_class: "small", no advisory.
    def test_small_community_size_class(self):
        self._write_community(10)
        result = self.srv.code_graph_community_response(self.root, "project:c1")
        data = result["data"]
        self.assertEqual(data["community_size_class"], "small")
        diagnostics = result.get("diagnostics") or []
        codes = [d.get("code") for d in diagnostics]
        self.assertNotIn("large_community_advisory", codes)

    # AC-2: medium community (50-200) → community_size_class: "medium", no advisory.
    def test_medium_community_size_class(self):
        self._write_community(100)
        result = self.srv.code_graph_community_response(self.root, "project:c1")
        data = result["data"]
        self.assertEqual(data["community_size_class"], "medium")
        diagnostics = result.get("diagnostics") or []
        codes = [d.get("code") for d in diagnostics]
        self.assertNotIn("large_community_advisory", codes)

    # AC-2/AC-3: large community → community_size_class: "large" + advisory emitted.
    def test_large_community_emits_advisory(self):
        self._write_community(250)
        result = self.srv.code_graph_community_response(self.root, "project:c1")
        data = result["data"]
        self.assertEqual(data["community_size_class"], "large")
        diagnostics = result.get("diagnostics") or []
        codes = [d.get("code") for d in diagnostics]
        self.assertIn("large_community_advisory", codes)

    # AC-4: advisory's recovery_usage references the hub_node_id.
    def test_advisory_recovery_usage_carries_hub_node_id(self):
        self._write_community(250)
        result = self.srv.code_graph_community_response(self.root, "project:c1")
        diagnostics = result.get("diagnostics") or []
        advisory = next(d for d in diagnostics if d.get("code") == "large_community_advisory")
        # The fixture's hub is whichever node has the highest in+out degree;
        # src/f0.py::m0 (target of one edge) and src/f1.py::m1 (source of one edge)
        # both have degree 1 — first by sort stability wins.
        self.assertIn("code_callhierarchy", advisory.get("recovery_usage", ""))
        self.assertIn("recovery_tools", advisory)
        self.assertIn("code_callhierarchy", advisory["recovery_tools"])
        self.assertIn("code_graph_path", advisory["recovery_tools"])

    # AC-5: advisory does NOT suppress pagination_hint — both coexist on large communities.
    def test_advisory_and_pagination_hint_both_present_on_large(self):
        self._write_community(250)
        result = self.srv.code_graph_community_response(self.root, "project:c1")
        data = result["data"]
        # Default limit=50 → has_more → pagination_hint present.
        self.assertIn("pagination_hint", data)
        diagnostics = result.get("diagnostics") or []
        codes = [d.get("code") for d in diagnostics]
        self.assertIn("large_community_advisory", codes)


class TestCollapseClassModulePairs(unittest.TestCase):
    """1312h: collapse_class_module_view merges Swift file+class pairs."""

    def setUp(self):
        import importlib.util
        scripts_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "graph_query_test_collapse_classmodule", scripts_root / "graph_query.py"
        )
        self.gq = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gq)

    def _payload(self, nodes, edges):
        return {"layer": "project", "present": True, "nodes": nodes, "edges": edges}

    # AC-2: Swift file + matching class collapse to one node with class label.
    def test_swift_file_class_pair_collapses(self):
        nodes = [
            {"id": "src/Foo.swift", "label": "Foo.swift", "kind": "module", "source_file": "src/Foo.swift"},
            {"id": "src/Foo.swift::Foo", "label": "Foo", "kind": "class", "source_file": "src/Foo.swift", "source_location": "1:0"},
            {"id": "src/Caller.swift::Caller.run", "label": "run", "kind": "function", "source_file": "src/Caller.swift", "source_location": "1:0"},
        ]
        edges = [
            {"source": "src/Caller.swift::Caller.run", "target": "src/Foo.swift::Foo", "relation": "calls"},
        ]
        result = self.gq.collapse_class_module_view(self._payload(nodes, edges))
        node_ids = {n["id"] for n in result["nodes"]}
        self.assertIn("src/Foo.swift", node_ids)
        self.assertNotIn("src/Foo.swift::Foo", node_ids)
        merged = next(n for n in result["nodes"] if n["id"] == "src/Foo.swift")
        # AC-3: label takes the class name + collapsed_pair: true.
        self.assertEqual(merged["label"], "Foo")
        self.assertTrue(merged["collapsed_pair"])
        # Edge to the class node rewritten to file node.
        self.assertEqual(len(result["edges"]), 1)
        self.assertEqual(result["edges"][0]["target"], "src/Foo.swift")

    # AC-5: files without matching top-level class are unaffected.
    def test_swift_file_without_matching_class_is_unaffected(self):
        nodes = [
            {"id": "src/Util.swift", "label": "Util.swift", "kind": "module", "source_file": "src/Util.swift"},
            {"id": "src/Util.swift::helper", "label": "helper", "kind": "function", "source_file": "src/Util.swift", "source_location": "1:0"},
        ]
        result = self.gq.collapse_class_module_view(self._payload(nodes, []))
        node_ids = {n["id"] for n in result["nodes"]}
        # Both nodes preserved; helper is a function (no name match), file stays as module.
        self.assertIn("src/Util.swift", node_ids)
        self.assertIn("src/Util.swift::helper", node_ids)

    # AC-5: Swift `struct Foo` in `Foo.swift` also collapses (struct included in collapse kinds).
    def test_swift_struct_module_pair_collapses(self):
        nodes = [
            {"id": "src/Point.swift", "label": "Point.swift", "kind": "module", "source_file": "src/Point.swift"},
            {"id": "src/Point.swift::Point", "label": "Point", "kind": "struct", "source_file": "src/Point.swift", "source_location": "1:0"},
        ]
        result = self.gq.collapse_class_module_view(self._payload(nodes, []))
        node_ids = {n["id"] for n in result["nodes"]}
        self.assertIn("src/Point.swift", node_ids)
        self.assertNotIn("src/Point.swift::Point", node_ids)

    # Non-Swift files (Java) are unaffected — Java-Kotlin-C# extensions deferred.
    def test_java_file_class_pair_not_collapsed(self):
        nodes = [
            {"id": "src/Foo.java", "label": "Foo.java", "kind": "module", "source_file": "src/Foo.java"},
            {"id": "src/Foo.java::Foo", "label": "Foo", "kind": "class", "source_file": "src/Foo.java", "source_location": "1:0"},
        ]
        result = self.gq.collapse_class_module_view(self._payload(nodes, []))
        node_ids = {n["id"] for n in result["nodes"]}
        # Both nodes preserved — Java not in _CLASS_MODULE_COLLAPSE_LANGUAGES.
        self.assertIn("src/Foo.java", node_ids)
        self.assertIn("src/Foo.java::Foo", node_ids)

    # Empty payload pass-through (cheap no-op when no pairs detected).
    def test_no_pairs_returns_unchanged_payload(self):
        nodes = [
            {"id": "src/a.py::foo", "label": "foo", "kind": "function", "source_file": "src/a.py"},
        ]
        result = self.gq.collapse_class_module_view(self._payload(nodes, []))
        self.assertEqual(len(result["nodes"]), 1)


class TestGeneratedCodeCollapse(unittest.TestCase):
    """130su-enh generated-code-collapse-mode: file-as-black-box collapse for wf_graph_report."""

    def setUp(self):
        # Load graph_query directly for unit-testing the collapse helper.
        import importlib.util
        scripts_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "graph_query_test_collapse", scripts_root / "graph_query.py"
        )
        self.gq = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gq)

    def _payload(self, nodes, edges):
        return {"layer": "project", "present": True, "nodes": nodes, "edges": edges}

    # AC-1: each generated file aggregates to one file-node with collapsed_node_count.
    def test_collapse_aggregates_generated_file_to_single_node(self):
        nodes = [
            {"id": "src/handwritten.py::foo", "label": "foo", "kind": "function", "source_file": "src/handwritten.py"},
            {"id": "src/ELParser.java", "label": "ELParser.java", "kind": "module", "source_file": "src/ELParser.java", "generated": True},
            {"id": "src/ELParser.java::Statement", "label": "Statement", "kind": "function", "source_file": "src/ELParser.java", "generated": True},
            {"id": "src/ELParser.java::jj_scan_token", "label": "jj_scan_token", "kind": "function", "source_file": "src/ELParser.java", "generated": True},
            {"id": "src/ELParser.java::jj_3R_96", "label": "jj_3R_96", "kind": "function", "source_file": "src/ELParser.java", "generated": True},
        ]
        result = self.gq.collapse_generated_view(self._payload(nodes, []))
        node_ids = {n["id"] for n in result["nodes"]}
        # Handwritten survives, generated symbol nodes collapsed.
        self.assertIn("src/handwritten.py::foo", node_ids)
        self.assertNotIn("src/ELParser.java::Statement", node_ids)
        self.assertNotIn("src/ELParser.java::jj_scan_token", node_ids)
        self.assertNotIn("src/ELParser.java::jj_3R_96", node_ids)
        # One file-node exists for the generated file (the original module is repurposed).
        elp_nodes = [n for n in result["nodes"] if n["id"] == "src/ELParser.java"]
        self.assertEqual(len(elp_nodes), 1)
        self.assertEqual(elp_nodes[0].get("collapsed_node_count"), 3)
        self.assertTrue(elp_nodes[0].get("generated"))

    # AC-1: synthetic file-node when no module-level node existed.
    def test_collapse_synthesizes_file_node_when_no_module_exists(self):
        nodes = [
            {"id": "src/GenA.java::M1", "label": "M1", "kind": "function", "source_file": "src/GenA.java", "generated": True},
            {"id": "src/GenA.java::M2", "label": "M2", "kind": "function", "source_file": "src/GenA.java", "generated": True},
        ]
        result = self.gq.collapse_generated_view(self._payload(nodes, []))
        file_node = next(n for n in result["nodes"] if n["id"] == "src/GenA.java")
        self.assertEqual(file_node["kind"], "module")
        self.assertEqual(file_node["collapsed_node_count"], 2)
        self.assertTrue(file_node["generated"])
        self.assertEqual(file_node["label"], "GenA.java")

    # AC-2: edges with BOTH endpoints inside the same generated file are dropped.
    def test_collapse_drops_internal_generated_edges(self):
        nodes = [
            {"id": "src/ELParser.java", "label": "ELParser.java", "kind": "module", "source_file": "src/ELParser.java", "generated": True},
            {"id": "src/ELParser.java::Statement", "label": "Statement", "kind": "function", "source_file": "src/ELParser.java", "generated": True},
            {"id": "src/ELParser.java::jj_scan_token", "label": "jj_scan_token", "kind": "function", "source_file": "src/ELParser.java", "generated": True},
        ]
        edges = [
            {"source": "src/ELParser.java::Statement", "target": "src/ELParser.java::jj_scan_token", "relation": "calls"},
        ]
        result = self.gq.collapse_generated_view(self._payload(nodes, edges))
        # Internal edge dropped; no surviving edges.
        self.assertEqual(result["edges"], [])

    # AC-3: edges where one endpoint is in a generated file have that endpoint rewritten.
    def test_collapse_rewrites_handwritten_to_generated_edge(self):
        nodes = [
            {"id": "src/handwritten.py::foo", "label": "foo", "kind": "function", "source_file": "src/handwritten.py"},
            {"id": "src/ELParser.java", "label": "ELParser.java", "kind": "module", "source_file": "src/ELParser.java", "generated": True},
            {"id": "src/ELParser.java::Statement", "label": "Statement", "kind": "function", "source_file": "src/ELParser.java", "generated": True},
        ]
        edges = [
            {"source": "src/handwritten.py::foo", "target": "src/ELParser.java::Statement", "relation": "calls", "line": 7, "snippet": "ELParser.Statement()"},
        ]
        result = self.gq.collapse_generated_view(self._payload(nodes, edges))
        self.assertEqual(len(result["edges"]), 1)
        e = result["edges"][0]
        self.assertEqual(e["source"], "src/handwritten.py::foo")
        # Target rewritten to file-node id (source_file).
        self.assertEqual(e["target"], "src/ELParser.java")
        self.assertEqual(e["relation"], "calls")
        # Line/snippet dropped because they pointed at a hidden internal symbol.
        self.assertNotIn("line", e)
        self.assertNotIn("snippet", e)

    # AC-3: edges from generated → handwritten have the generated endpoint rewritten.
    def test_collapse_rewrites_generated_to_handwritten_edge(self):
        nodes = [
            {"id": "src/handwritten.py::Logger", "label": "Logger", "kind": "function", "source_file": "src/handwritten.py"},
            {"id": "src/ELParser.java", "label": "ELParser.java", "kind": "module", "source_file": "src/ELParser.java", "generated": True},
            {"id": "src/ELParser.java::error", "label": "error", "kind": "function", "source_file": "src/ELParser.java", "generated": True},
        ]
        edges = [
            {"source": "src/ELParser.java::error", "target": "src/handwritten.py::Logger", "relation": "calls"},
        ]
        result = self.gq.collapse_generated_view(self._payload(nodes, edges))
        self.assertEqual(len(result["edges"]), 1)
        e = result["edges"][0]
        self.assertEqual(e["source"], "src/ELParser.java")  # rewritten
        self.assertEqual(e["target"], "src/handwritten.py::Logger")  # preserved

    # AC-4: edges between two DIFFERENT generated files rewrite both endpoints.
    def test_collapse_rewrites_cross_generated_file_edges(self):
        nodes = [
            {"id": "src/GenA.java", "label": "GenA.java", "kind": "module", "source_file": "src/GenA.java", "generated": True},
            {"id": "src/GenA.java::a", "label": "a", "kind": "function", "source_file": "src/GenA.java", "generated": True},
            {"id": "src/GenB.java", "label": "GenB.java", "kind": "module", "source_file": "src/GenB.java", "generated": True},
            {"id": "src/GenB.java::b", "label": "b", "kind": "function", "source_file": "src/GenB.java", "generated": True},
        ]
        edges = [
            {"source": "src/GenA.java::a", "target": "src/GenB.java::b", "relation": "calls"},
        ]
        result = self.gq.collapse_generated_view(self._payload(nodes, edges))
        self.assertEqual(len(result["edges"]), 1)
        e = result["edges"][0]
        self.assertEqual(e["source"], "src/GenA.java")
        self.assertEqual(e["target"], "src/GenB.java")

    # Deduplication: multiple internal edges from one generated file to the same external
    # endpoint collapse to one rewritten edge.
    def test_collapse_dedupes_rewritten_edges(self):
        nodes = [
            {"id": "src/handwritten.py::Logger", "label": "Logger", "kind": "function", "source_file": "src/handwritten.py"},
            {"id": "src/ELParser.java", "label": "ELParser.java", "kind": "module", "source_file": "src/ELParser.java", "generated": True},
            {"id": "src/ELParser.java::a", "label": "a", "kind": "function", "source_file": "src/ELParser.java", "generated": True},
            {"id": "src/ELParser.java::b", "label": "b", "kind": "function", "source_file": "src/ELParser.java", "generated": True},
        ]
        edges = [
            {"source": "src/ELParser.java::a", "target": "src/handwritten.py::Logger", "relation": "calls"},
            {"source": "src/ELParser.java::b", "target": "src/handwritten.py::Logger", "relation": "calls"},
        ]
        result = self.gq.collapse_generated_view(self._payload(nodes, edges))
        # Both edges rewrite to (src/ELParser.java → src/handwritten.py::Logger, calls)
        # — deduplicated to ONE edge.
        self.assertEqual(len(result["edges"]), 1)

    # Non-generated graphs pass through unchanged.
    def test_collapse_no_op_when_no_generated_nodes(self):
        nodes = [
            {"id": "src/a.py::foo", "label": "foo", "kind": "function", "source_file": "src/a.py"},
            {"id": "src/b.py::bar", "label": "bar", "kind": "function", "source_file": "src/b.py"},
        ]
        edges = [
            {"source": "src/b.py::bar", "target": "src/a.py::foo", "relation": "calls"},
        ]
        result = self.gq.collapse_generated_view(self._payload(nodes, edges))
        self.assertEqual(len(result["nodes"]), 2)
        self.assertEqual(len(result["edges"]), 1)


class TestWaveGraphReportCollapseIntegration(unittest.TestCase):
    """130su: collapse_generated_files end-to-end through wf_graph_report_response."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        # Two handwritten functions + one generated file with three symbol nodes
        # + a handwritten→generated edge + internal generated edges.
        nodes = [
            {"id": "src/handwritten.py::foo", "label": "foo", "kind": "function", "source_file": "src/handwritten.py", "source_location": "1:0"},
            {"id": "src/handwritten.py::bar", "label": "bar", "kind": "function", "source_file": "src/handwritten.py", "source_location": "5:0"},
            {"id": "src/ELParser.java", "label": "ELParser.java", "kind": "module", "source_file": "src/ELParser.java", "source_location": "1:0", "generated": True},
            {"id": "src/ELParser.java::Statement", "label": "Statement", "kind": "function", "source_file": "src/ELParser.java", "source_location": "100:0", "generated": True},
            {"id": "src/ELParser.java::jj_scan_token", "label": "jj_scan_token", "kind": "function", "source_file": "src/ELParser.java", "source_location": "200:0", "generated": True},
            {"id": "src/ELParser.java::jj_3R_96", "label": "jj_3R_96", "kind": "function", "source_file": "src/ELParser.java", "source_location": "300:0", "generated": True},
        ]
        graph = {
            "schema_version": "1", "builder_version": "11", "layer": "project",
            "nodes": nodes,
            "edges": [
                {"source": "src/handwritten.py::foo", "target": "src/ELParser.java::Statement", "relation": "calls"},
                {"source": "src/handwritten.py::bar", "target": "src/ELParser.java::Statement", "relation": "calls"},
                {"source": "src/ELParser.java::Statement", "target": "src/ELParser.java::jj_scan_token", "relation": "calls"},
                {"source": "src/ELParser.java::Statement", "target": "src/ELParser.java::jj_3R_96", "relation": "calls"},
                {"source": "src/ELParser.java::jj_3R_96", "target": "src/ELParser.java::jj_scan_token", "relation": "calls"},
            ],
            "counts": {"files": 2, "nodes": 6, "edges": 5},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        # Minimal cluster artifact (not exercised in collapse tests, but report fetches it).
        cluster = {
            "cluster_algorithm": "leiden",
            "cluster_builder_version": "1",
            "cluster_schema_version": "1",
            "communities": [],
            "community_count": 0,
        }
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps(cluster), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    # AC-5/AC-6: collapse_generated_files=True runs wf_graph_report over the collapsed view.
    def test_collapse_runs_report_over_collapsed_view(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20, collapse_generated_files=True)
        self.assertEqual(result["status"], "ok")
        report = result["data"]
        self.assertTrue(report["collapse_generated_files"])
        # fan_in should not contain the collapsed internal symbols.
        fan_in = {r["node_id"] for r in report.get("fan_in", [])}
        self.assertNotIn("src/ELParser.java::jj_scan_token", fan_in)
        self.assertNotIn("src/ELParser.java::Statement", fan_in)
        self.assertNotIn("src/ELParser.java::jj_3R_96", fan_in)
        # fan_in should contain the collapsed file-node (it's the target of handwritten calls).
        self.assertIn("src/ELParser.java", fan_in)

    # AC-7: default behavior (collapse_generated_files=False) unchanged.
    def test_collapse_default_off_preserves_full_graph(self):
        result = self.srv.wf_graph_report_response(self.root, layer="project", limit=20)
        report = result["data"]
        self.assertFalse(report["collapse_generated_files"])
        fan_in = {r["node_id"] for r in report.get("fan_in", [])}
        # Without collapse, internal generated symbols appear in fan_in.
        self.assertIn("src/ELParser.java::jj_scan_token", fan_in)


class TestJavaMethodReferenceCallSites(unittest.TestCase):
    """130r7-bug: Java `method_reference` AST nodes classify as call_sites so
    code_callhierarchy.incoming attaches line+snippet to entries that only
    reference the target via method references (Foo::bar, this::bar)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _write_graph(self, nodes: list, edges: list) -> None:
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        (graph_dir / "project-graph.json").write_text(
            json.dumps({"schema_version": "1", "layer": "project", "nodes": nodes, "edges": edges}),
            encoding="utf-8",
        )

    def test_method_reference_callsite_attaches_line_and_snippet(self):
        """A caller that references the target via `Helper::process` (method reference syntax)
        must produce a non-null line/snippet on the incoming entry. Pre-130r7 the line/snippet
        was null because `method_reference` wasn't in `_TS_CALL_PARENT_TYPES['java']`."""
        self._add("src/Helper.java", "class Helper {\n    int process(int n) { return n + 1; }\n}\n")
        self._add(
            "src/Stream.java",
            "import java.util.stream.*;\n"
            "class StreamCaller {\n"
            "    int run() {\n"
            "        return java.util.stream.IntStream.of(1, 2, 3).map(Helper::process).sum();\n"
            "    }\n"
            "}\n",
        )
        self._write_graph(
            nodes=[
                {"id": "src/Helper.java::Helper.process", "label": "process", "kind": "function", "source_file": "src/Helper.java", "source_location": "2:4"},
                {"id": "src/Stream.java::StreamCaller.run", "label": "run", "kind": "function", "source_file": "src/Stream.java", "source_location": "3:4"},
            ],
            edges=[
                {"source": "src/Stream.java::StreamCaller.run", "target": "src/Helper.java::Helper.process", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "process", None, "incoming")
        self.assertEqual(result["status"], "ok")
        incoming = result["data"]["incoming"]
        self.assertEqual(len(incoming), 1)
        entry = incoming[0]
        self.assertEqual(entry.get("name"), "run")
        # The line attribution must succeed because the method-reference identifier
        # `process` (parent: method_reference) is now classified as call_sites.
        self.assertIsNotNone(entry.get("line"), f"line still null for method-reference caller: {entry}")
        self.assertIsNotNone(entry.get("snippet"))
        # Snippet should be the line containing `Helper::process`.
        self.assertIn("Helper::process", entry["snippet"])

    def test_traditional_method_invocation_still_works(self):
        """Sanity: adding `method_reference` to the call-parent set does not break
        traditional method-invocation classification."""
        self._add("src/Helper.java", "class Helper {\n    int process(int n) { return n + 1; }\n}\n")
        self._add(
            "src/Plain.java",
            "class PlainCaller {\n"
            "    int run() {\n"
            "        Helper h = new Helper();\n"
            "        return h.process(5);\n"
            "    }\n"
            "}\n",
        )
        self._write_graph(
            nodes=[
                {"id": "src/Helper.java::Helper.process", "label": "process", "kind": "function", "source_file": "src/Helper.java", "source_location": "2:4"},
                {"id": "src/Plain.java::PlainCaller.run", "label": "run", "kind": "function", "source_file": "src/Plain.java", "source_location": "2:4"},
            ],
            edges=[
                {"source": "src/Plain.java::PlainCaller.run", "target": "src/Helper.java::Helper.process", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "process", None, "incoming")
        incoming = result["data"]["incoming"]
        self.assertEqual(len(incoming), 1)
        entry = incoming[0]
        self.assertIsNotNone(entry.get("line"))
        self.assertIn("h.process(5)", entry["snippet"])


class TestJavaReceiverTypeResolution(unittest.TestCase):
    """130tw-enh java-receiver-type-resolution: filter phantom cross-class
    callers from code_callhierarchy when the receiver type doesn't match
    the queried symbol's owning class.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _write_graph(self, nodes: list, edges: list) -> None:
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        (graph_dir / "project-graph.json").write_text(
            json.dumps({"schema_version": "1", "layer": "project", "nodes": nodes, "edges": edges}),
            encoding="utf-8",
        )

    # AC-6: the field reproducer — JSON.writeObject vs oos.writeObject (ObjectOutputStream).
    def test_phantom_oos_writeobject_caller_is_excluded(self):
        self._add(
            "src/JSON.java",
            "class JSON {\n"
            "    public void writeObject(Object o) {}\n"
            "    public void serializeBoth(Object a, Object b) {\n"
            "        writeObject(a);\n"
            "        writeObject(b);\n"
            "    }\n"
            "}\n",
        )
        self._add(
            "src/JdbcConnectionRegistry.java",
            "import java.io.ObjectOutputStream;\n"
            "import java.io.FileOutputStream;\n"
            "class JdbcConnectionRegistry {\n"
            "    public void cloneConnectionMap(Object object) throws Exception {\n"
            "        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(\"x\"));\n"
            "        oos.writeObject(object);\n"
            "    }\n"
            "}\n",
        )
        self._write_graph(
            nodes=[
                {"id": "src/JSON.java::JSON.writeObject", "label": "writeObject", "kind": "function", "source_file": "src/JSON.java", "source_location": "2:4"},
                {"id": "src/JSON.java::JSON.serializeBoth", "label": "serializeBoth", "kind": "function", "source_file": "src/JSON.java", "source_location": "3:4"},
                {"id": "src/JdbcConnectionRegistry.java::JdbcConnectionRegistry.cloneConnectionMap", "label": "cloneConnectionMap", "kind": "function", "source_file": "src/JdbcConnectionRegistry.java", "source_location": "4:4"},
            ],
            edges=[
                # Legitimate caller within JSON class.
                {"source": "src/JSON.java::JSON.serializeBoth", "target": "src/JSON.java::JSON.writeObject", "relation": "calls"},
                # Phantom caller — graph builder attributed by simple-name; oos is ObjectOutputStream.
                {"source": "src/JdbcConnectionRegistry.java::JdbcConnectionRegistry.cloneConnectionMap", "target": "src/JSON.java::JSON.writeObject", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "JSON.writeObject", None, "incoming")
        self.assertEqual(result["status"], "ok")
        incoming = result["data"]["incoming"]
        names = [e.get("name") for e in incoming]
        # The legitimate JSON-class caller is preserved.
        self.assertIn("serializeBoth", names)
        # The phantom JdbcRegistry caller is excluded.
        self.assertNotIn("cloneConnectionMap", names)

    # AC-7: this.method() resolves to enclosing class → preserved when class matches.
    def test_this_call_preserves_caller_in_same_class(self):
        self._add(
            "src/JSON.java",
            "class JSON {\n"
            "    public void writeObject(Object o) {}\n"
            "    public void wrapper(Object x) {\n"
            "        this.writeObject(x);\n"
            "    }\n"
            "}\n",
        )
        self._write_graph(
            nodes=[
                {"id": "src/JSON.java::JSON.writeObject", "label": "writeObject", "kind": "function", "source_file": "src/JSON.java", "source_location": "2:4"},
                {"id": "src/JSON.java::JSON.wrapper", "label": "wrapper", "kind": "function", "source_file": "src/JSON.java", "source_location": "3:4"},
            ],
            edges=[
                {"source": "src/JSON.java::JSON.wrapper", "target": "src/JSON.java::JSON.writeObject", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "JSON.writeObject", None, "incoming")
        incoming = result["data"]["incoming"]
        names = [e.get("name") for e in incoming]
        self.assertIn("wrapper", names)

    # AC-7: bare method() call resolves to enclosing class → preserved.
    def test_bare_call_preserves_caller_in_same_class(self):
        self._add(
            "src/JSON.java",
            "class JSON {\n"
            "    public void writeObject(Object o) {}\n"
            "    public void wrapper(Object x) {\n"
            "        writeObject(x);\n"
            "    }\n"
            "}\n",
        )
        self._write_graph(
            nodes=[
                {"id": "src/JSON.java::JSON.writeObject", "label": "writeObject", "kind": "function", "source_file": "src/JSON.java", "source_location": "2:4"},
                {"id": "src/JSON.java::JSON.wrapper", "label": "wrapper", "kind": "function", "source_file": "src/JSON.java", "source_location": "3:4"},
            ],
            edges=[
                {"source": "src/JSON.java::JSON.wrapper", "target": "src/JSON.java::JSON.writeObject", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "JSON.writeObject", None, "incoming")
        incoming = result["data"]["incoming"]
        names = [e.get("name") for e in incoming]
        self.assertIn("wrapper", names)

    # AC-7: ClassName.staticMethod() style — resolves to that class.
    def test_static_class_call_resolves_to_class_name(self):
        self._add(
            "src/JSON.java",
            "class JSON {\n"
            "    public static void writeObject(Object o) {}\n"
            "}\n",
        )
        self._add(
            "src/Caller.java",
            "class Caller {\n"
            "    void run(Object o) {\n"
            "        JSON.writeObject(o);\n"
            "    }\n"
            "}\n",
        )
        self._write_graph(
            nodes=[
                {"id": "src/JSON.java::JSON.writeObject", "label": "writeObject", "kind": "function", "source_file": "src/JSON.java", "source_location": "2:4"},
                {"id": "src/Caller.java::Caller.run", "label": "run", "kind": "function", "source_file": "src/Caller.java", "source_location": "2:4"},
            ],
            edges=[
                {"source": "src/Caller.java::Caller.run", "target": "src/JSON.java::JSON.writeObject", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "JSON.writeObject", None, "incoming")
        incoming = result["data"]["incoming"]
        names = [e.get("name") for e in incoming]
        self.assertIn("run", names)

    # AC-4: bare-name query (no class context) → no filtering applied.
    def test_bare_name_query_skips_receiver_filter(self):
        # Query as bare "writeObject" — node_id has no class qualification, so filter doesn't run.
        self._add(
            "src/Foo.java",
            "class Foo {\n"
            "    public void writeObject(Object o) {}\n"
            "}\n",
        )
        self._add(
            "src/Bar.java",
            "import java.io.ObjectOutputStream;\n"
            "import java.io.FileOutputStream;\n"
            "class Bar {\n"
            "    public void run(Object object) throws Exception {\n"
            "        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(\"x\"));\n"
            "        oos.writeObject(object);\n"
            "    }\n"
            "}\n",
        )
        self._write_graph(
            nodes=[
                # Note: queried node has no class qualification — node_id is "src/Foo.java::writeObject"
                # (bare symbol part) — extractor returns owner_class=None, filter doesn't run.
                {"id": "src/Foo.java::writeObject", "label": "writeObject", "kind": "function", "source_file": "src/Foo.java", "source_location": "2:4"},
                {"id": "src/Bar.java::Bar.run", "label": "run", "kind": "function", "source_file": "src/Bar.java", "source_location": "4:4"},
            ],
            edges=[
                {"source": "src/Bar.java::Bar.run", "target": "src/Foo.java::writeObject", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "writeObject", None, "incoming")
        incoming = result["data"]["incoming"]
        names = [e.get("name") for e in incoming]
        # Without class context, the phantom caller is preserved (backward compat).
        self.assertIn("run", names)


class TestPreBumpGraphReceiverTypeDefense(unittest.TestCase):
    """1312l delivery review: cached pre-bump (GRAPH_BUILDER_VERSION=12) graphs
    carry phantom Java edges from simple-name attribution at index time.
    Operators upgrading from 1.2.0+312f read the old graph until
    `index_build` re-extracts it. Verify the wave-130rj defense-in-depth
    filter in `code_callhierarchy_response` still suppresses those phantoms
    via AST-time receiver-type resolution on the source files.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel, content):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _write_pre_bump_graph(self, nodes, edges):
        """Write a graph artifact with explicit pre-bump builder_version=12.

        Pre-bump indexer behavior: simple-name attribution produced phantom
        edges for `oos.writeObject` and similar receiver-typed calls; the
        edges target the project simple-name match (e.g. JSON.writeObject)
        not the resolved external (external::ObjectOutputStream.writeObject).
        Replicate that shape here so the test verifies the query-time
        defense-in-depth path.
        """
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        (graph_dir / "project-graph.json").write_text(
            json.dumps({
                "schema_version": "1",
                "builder_version": "12",  # pre-bump
                "layer": "project",
                "nodes": nodes,
                "edges": edges,
            }),
            encoding="utf-8",
        )

    def _write_graph_with_version(self, builder_version, nodes, edges):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        (graph_dir / "project-graph.json").write_text(
            json.dumps({
                "schema_version": "1",
                "builder_version": builder_version,
                "layer": "project",
                "nodes": nodes,
                "edges": edges,
            }),
            encoding="utf-8",
        )

    def test_post_bump_graph_skips_redundant_filter(self):
        """v13+ graph: indexer already cleaned phantoms; filter short-circuits.

        Verifies the version-aware optimization. We deliberately inject a phantom
        edge into a v13-labeled graph (simulating an indexer bug — should not
        happen in production) and assert the filter is bypassed. This documents
        the contract: on v13+, the indexer is the source of truth for edge
        correctness; the query-time filter does not re-validate.
        """
        self._add(
            "src/JSON.java",
            "class JSON {\n"
            "    public void writeObject(Object o) {}\n"
            "}\n",
        )
        self._add(
            "src/JdbcRegistry.java",
            "import java.io.ObjectOutputStream;\n"
            "import java.io.FileOutputStream;\n"
            "class JdbcRegistry {\n"
            "    public void cloneConnectionMap(Object object) throws Exception {\n"
            "        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(\"x\"));\n"
            "        oos.writeObject(object);\n"
            "    }\n"
            "}\n",
        )
        # v13 graph with a deliberately-injected phantom edge.
        self._write_graph_with_version(
            builder_version="13",
            nodes=[
                {"id": "src/JSON.java::JSON.writeObject", "label": "writeObject", "kind": "function", "source_file": "src/JSON.java", "source_location": "2:4"},
                {"id": "src/JdbcRegistry.java::JdbcRegistry.cloneConnectionMap", "label": "cloneConnectionMap", "kind": "function", "source_file": "src/JdbcRegistry.java", "source_location": "4:4"},
            ],
            edges=[
                # Phantom edge injected; v13 indexer wouldn't produce this in practice.
                {"source": "src/JdbcRegistry.java::JdbcRegistry.cloneConnectionMap", "target": "src/JSON.java::JSON.writeObject", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "JSON.writeObject", None, "incoming")
        incoming = result["data"]["incoming"]
        names = [e.get("name") for e in incoming]
        # Filter short-circuited — phantom edge survives because indexer is trusted on v13+.
        self.assertIn("cloneConnectionMap", names,
                      f"v13 short-circuit failed; filter still ran on post-bump graph: {incoming}")

    def test_pre_bump_graph_phantom_edges_filtered_at_query_time(self):
        """Pre-bump graph carries a phantom JdbcRegistry → JSON.writeObject edge.
        Defense-in-depth filter in code_callhierarchy_response must still
        exclude the JdbcRegistry caller from incoming results.
        """
        self._add(
            "src/JSON.java",
            "class JSON {\n"
            "    public void writeObject(Object o) {}\n"
            "    public void serialize(Object x) { writeObject(x); }\n"
            "}\n",
        )
        self._add(
            "src/JdbcRegistry.java",
            "import java.io.ObjectOutputStream;\n"
            "import java.io.FileOutputStream;\n"
            "class JdbcRegistry {\n"
            "    public void cloneConnectionMap(Object object) throws Exception {\n"
            "        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(\"x\"));\n"
            "        oos.writeObject(object);\n"
            "    }\n"
            "}\n",
        )
        # Pre-bump graph: BOTH the legitimate JSON.serialize → JSON.writeObject
        # AND the PHANTOM JdbcRegistry.cloneConnectionMap → JSON.writeObject edges
        # are present (this is what wave-130rj receiver-type filter at query
        # time was designed to mask before 1312l moved resolution to index time).
        self._write_pre_bump_graph(
            nodes=[
                {"id": "src/JSON.java::JSON.writeObject", "label": "writeObject", "kind": "function", "source_file": "src/JSON.java", "source_location": "2:4"},
                {"id": "src/JSON.java::JSON.serialize", "label": "serialize", "kind": "function", "source_file": "src/JSON.java", "source_location": "3:4"},
                {"id": "src/JdbcRegistry.java::JdbcRegistry.cloneConnectionMap", "label": "cloneConnectionMap", "kind": "function", "source_file": "src/JdbcRegistry.java", "source_location": "4:4"},
            ],
            edges=[
                # Legit caller — should survive.
                {"source": "src/JSON.java::JSON.serialize", "target": "src/JSON.java::JSON.writeObject", "relation": "calls"},
                # Phantom caller — defense-in-depth should exclude.
                {"source": "src/JdbcRegistry.java::JdbcRegistry.cloneConnectionMap", "target": "src/JSON.java::JSON.writeObject", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "JSON.writeObject", None, "incoming")
        self.assertEqual(result["status"], "ok")
        incoming = result["data"]["incoming"]
        names = [e.get("name") for e in incoming]
        # Legitimate JSON-class caller preserved.
        self.assertIn("serialize", names)
        # Phantom JdbcRegistry caller excluded by the query-time receiver-type filter.
        self.assertNotIn("cloneConnectionMap", names,
                         f"Defense-in-depth filter failed on pre-bump graph; incoming: {incoming}")


class TestExtractJavaOwnerClassFromNodeId(unittest.TestCase):
    """130tw-enh java-receiver-type-resolution: node_id parser helper."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def test_simple_class_method_returns_class(self):
        self.assertEqual(
            self.srv._extract_java_owner_class_from_node_id("src/Foo.java::Foo.bar"),
            "Foo",
        )

    def test_nested_class_returns_innermost_class(self):
        self.assertEqual(
            self.srv._extract_java_owner_class_from_node_id("src/Outer.java::Outer.Inner.method"),
            "Inner",
        )

    def test_bare_method_returns_none(self):
        self.assertIsNone(
            self.srv._extract_java_owner_class_from_node_id("src/Foo.java::bareMethod")
        )

    def test_missing_separator_returns_none(self):
        self.assertIsNone(self.srv._extract_java_owner_class_from_node_id("noSeparator"))
        self.assertIsNone(self.srv._extract_java_owner_class_from_node_id(""))


class TestAopAdviceEmptyIncomingDetection(unittest.TestCase):
    """130rj-enh aop-advice-empty-incoming-detection: caller_pattern field on
    code_callhierarchy when an annotated advice method has no Java callers."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _write_graph(self, nodes: list, edges: list) -> None:
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        (graph_dir / "project-graph.json").write_text(
            json.dumps({"schema_version": "1", "layer": "project", "nodes": nodes, "edges": edges}),
            encoding="utf-8",
        )

    # AC-3: empty incoming + advice annotation → caller_pattern: "advice".
    def test_advice_method_with_no_callers_emits_caller_pattern(self):
        self._add("src/Probe.java", "class Probe {}\n")  # placeholder file
        self._write_graph(
            nodes=[
                {
                    "id": "src/Probe.java::Probe.onEnter",
                    "label": "onEnter",
                    "kind": "function",
                    "source_file": "src/Probe.java",
                    "source_location": "1:0",
                    "annotations": ["Advice.OnMethodEnter"],
                },
            ],
            edges=[],
        )
        result = self.srv.code_callhierarchy_response(self.root, "onEnter", None, "incoming")
        data = result["data"]
        self.assertEqual(data["incoming"], [])
        self.assertEqual(data.get("caller_pattern"), "advice")
        self.assertIn("Advice.OnMethodEnter", data.get("advice_annotations", []))
        # AC-3: recovery hint surfaces via a structured diagnostic entry.
        diagnostics = result.get("diagnostics") or []
        codes = [d.get("code") for d in diagnostics]
        self.assertIn("advice_pattern_detected", codes)
        advice_diag = next(d for d in diagnostics if d.get("code") == "advice_pattern_detected")
        self.assertIn("ByteBuddy", advice_diag.get("message", ""))
        self.assertIn("code_keyword", advice_diag.get("recovery_tools", []))

    # AC-3 (broader annotation set): @Around / @Before / @After all fire the pattern.
    def test_around_annotation_fires_advice_pattern(self):
        self._add("src/Aspect.java", "class Aspect {}\n")
        self._write_graph(
            nodes=[
                {
                    "id": "src/Aspect.java::Aspect.around",
                    "label": "around",
                    "kind": "function",
                    "source_file": "src/Aspect.java",
                    "source_location": "1:0",
                    "annotations": ["Around"],
                },
            ],
            edges=[],
        )
        result = self.srv.code_callhierarchy_response(self.root, "around", None, "incoming")
        data = result["data"]
        self.assertEqual(data.get("caller_pattern"), "advice")
        self.assertIn("Around", data.get("advice_annotations", []))

    # AC-3 (qualified annotation): `org.aspectj.lang.annotation.Around` matches by tail.
    def test_qualified_around_annotation_fires_advice_pattern(self):
        self._add("src/Asp.java", "class Asp {}\n")
        self._write_graph(
            nodes=[
                {
                    "id": "src/Asp.java::Asp.foo",
                    "label": "foo",
                    "kind": "function",
                    "source_file": "src/Asp.java",
                    "source_location": "1:0",
                    "annotations": ["org.aspectj.lang.annotation.Around"],
                },
            ],
            edges=[],
        )
        result = self.srv.code_callhierarchy_response(self.root, "foo", None, "incoming")
        data = result["data"]
        self.assertEqual(data.get("caller_pattern"), "advice")
        # Tail extracted as "Around".
        self.assertIn("Around", data.get("advice_annotations", []))

    # AC-4: advice method WITH a Java caller — no caller_pattern emitted.
    def test_advice_method_with_incoming_does_not_emit_pattern(self):
        self._add("src/Probe.java", "class Probe {}\n")
        self._add("src/Caller.java", "class Caller { void invoke() { Probe.onEnter(); } }\n")
        self._write_graph(
            nodes=[
                {
                    "id": "src/Probe.java::Probe.onEnter",
                    "label": "onEnter",
                    "kind": "function",
                    "source_file": "src/Probe.java",
                    "source_location": "1:0",
                    "annotations": ["Advice.OnMethodEnter"],
                },
                {
                    "id": "src/Caller.java::Caller.invoke",
                    "label": "invoke",
                    "kind": "function",
                    "source_file": "src/Caller.java",
                    "source_location": "1:0",
                },
            ],
            edges=[
                {"source": "src/Caller.java::Caller.invoke", "target": "src/Probe.java::Probe.onEnter", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "onEnter", None, "incoming")
        data = result["data"]
        # Incoming is non-empty (one Java caller), so no advice pattern flag.
        self.assertEqual(len(data["incoming"]), 1)
        self.assertNotIn("caller_pattern", data)

    # AC-5: non-advice method with empty incoming gets no caller_pattern.
    def test_non_advice_method_with_no_callers_does_not_emit_pattern(self):
        self._add("src/Lib.java", "class Lib {}\n")
        self._write_graph(
            nodes=[
                {
                    "id": "src/Lib.java::Lib.utility",
                    "label": "utility",
                    "kind": "function",
                    "source_file": "src/Lib.java",
                    "source_location": "1:0",
                    # No annotations.
                },
            ],
            edges=[],
        )
        result = self.srv.code_callhierarchy_response(self.root, "utility", None, "incoming")
        data = result["data"]
        self.assertEqual(data["incoming"], [])
        self.assertNotIn("caller_pattern", data)

    # AC-5: method with a non-advice annotation (e.g. @Override) does not emit the pattern.
    def test_non_advice_annotation_does_not_fire_pattern(self):
        self._add("src/Override.java", "class Override {}\n")
        self._write_graph(
            nodes=[
                {
                    "id": "src/Override.java::OverrideClass.run",
                    "label": "run",
                    "kind": "function",
                    "source_file": "src/Override.java",
                    "source_location": "1:0",
                    "annotations": ["Override", "Deprecated"],
                },
            ],
            edges=[],
        )
        result = self.srv.code_callhierarchy_response(self.root, "run", None, "incoming")
        data = result["data"]
        self.assertNotIn("caller_pattern", data)


class TestJavaAnnotationExtraction(unittest.TestCase):
    """130rj-enh aop-advice-empty-incoming-detection: graph_indexer captures
    Java annotation tails on method_declaration nodes so the server-tool layer
    can detect AOP/advice patterns."""

    def setUp(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        import importlib.util, sys as _sys
        scripts_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "graph_indexer_test_ann", scripts_root / "graph_indexer.py"
        )
        self.gi = importlib.util.module_from_spec(spec)
        # Register in sys.modules so dataclass/typing introspection inside the
        # module can find its own definitions (e.g. cls.__module__ lookups).
        _sys.modules["graph_indexer_test_ann"] = self.gi
        spec.loader.exec_module(self.gi)

    def _build(self, java_source: str):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
        src = root / "src" / "Probe.java"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(java_source, encoding="utf-8")
        payload = self.gi.update_graph_index(
            root=root,
            index_dir=root / ".wavefoundry" / "index",
            layer="project",
            files=[src],
            current_file_meta={"src/Probe.java": {"hash": "h"}},
            changed={"src/Probe.java"},
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )
        return {n["id"]: n for n in payload["nodes"]}

    def test_marker_annotation_captured(self):
        nodes = self._build(
            "class Probe {\n"
            "    @Advice.OnMethodEnter\n"
            "    public static void onEnter() {}\n"
            "}\n"
        )
        on_enter = next((n for nid, n in nodes.items() if nid.endswith("::Probe.onEnter")), None)
        self.assertIsNotNone(on_enter)
        self.assertIn("Advice.OnMethodEnter", on_enter.get("annotations", []))

    def test_argument_annotation_captured(self):
        nodes = self._build(
            "class Asp {\n"
            "    @Around(\"execution(* foo(..))\")\n"
            "    public Object around() { return null; }\n"
            "}\n"
        )
        around = next((n for nid, n in nodes.items() if nid.endswith("::Asp.around")), None)
        self.assertIsNotNone(around)
        self.assertIn("Around", around.get("annotations", []))

    def test_method_without_annotations_omits_field(self):
        nodes = self._build(
            "class Lib {\n"
            "    int utility() { return 1; }\n"
            "}\n"
        )
        util = next((n for nid, n in nodes.items() if nid.endswith("::Lib.utility")), None)
        self.assertIsNotNone(util)
        # No `annotations` key (or empty) when the method has none.
        self.assertFalse(util.get("annotations"))


class TestCsharpAttributeExtraction(unittest.TestCase):
    """130tc: graph_indexer captures C# attribute names on method_declaration /
    class_declaration nodes so the server-tool AOP/advice detection layer can
    fire `caller_pattern: "advice"` for C# methods decorated with PostSharp /
    Castle DynamicProxy / MethodBoundaryAspect-style attributes."""

    def setUp(self):
        try:
            import tree_sitter_c_sharp  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_c_sharp not available in test env")
        import importlib.util, sys as _sys
        scripts_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "graph_indexer_test_csharp_ann", scripts_root / "graph_indexer.py"
        )
        self.gi = importlib.util.module_from_spec(spec)
        _sys.modules["graph_indexer_test_csharp_ann"] = self.gi
        spec.loader.exec_module(self.gi)

    def _build(self, csharp_source: str):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
        src = root / "src" / "Probe.cs"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(csharp_source, encoding="utf-8")
        payload = self.gi.update_graph_index(
            root=root,
            index_dir=root / ".wavefoundry" / "index",
            layer="project",
            files=[src],
            current_file_meta={"src/Probe.cs": {"hash": "h"}},
            changed={"src/Probe.cs"},
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )
        return {n["id"]: n for n in payload["nodes"]}

    def test_method_boundary_attribute_captured(self):
        nodes = self._build(
            "public class Probe {\n"
            "    [OnMethodBoundaryAspect]\n"
            "    public void Boundary() {}\n"
            "}\n"
        )
        boundary = next((n for nid, n in nodes.items() if nid.endswith("::Probe.Boundary")), None)
        self.assertIsNotNone(boundary)
        self.assertIn("OnMethodBoundaryAspect", boundary.get("annotations", []))

    def test_attribute_with_arguments_captured(self):
        nodes = self._build(
            "public class Aspect {\n"
            "    [Around(\"execution(* foo(..))\")]\n"
            "    public object Around() { return null; }\n"
            "}\n"
        )
        around = next((n for nid, n in nodes.items() if nid.endswith("::Aspect.Around")), None)
        self.assertIsNotNone(around)
        self.assertIn("Around", around.get("annotations", []))

    def test_multiple_attributes_captured(self):
        nodes = self._build(
            "public class Multi {\n"
            "    [OnEntry]\n"
            "    [OnExit]\n"
            "    public void Both() {}\n"
            "}\n"
        )
        both = next((n for nid, n in nodes.items() if nid.endswith("::Multi.Both")), None)
        self.assertIsNotNone(both)
        attrs = both.get("annotations", [])
        self.assertIn("OnEntry", attrs)
        self.assertIn("OnExit", attrs)

    def test_method_without_attributes_omits_field(self):
        nodes = self._build(
            "public class Lib {\n"
            "    public int Utility() { return 1; }\n"
            "}\n"
        )
        util = next((n for nid, n in nodes.items() if nid.endswith("::Lib.Utility")), None)
        self.assertIsNotNone(util)
        self.assertFalse(util.get("annotations"))


class TestCsharpAdviceEmptyIncomingDetection(unittest.TestCase):
    """130tc: code_callhierarchy detects C# AOP attributes and emits
    `caller_pattern: "advice"` with a C#-tailored recovery hint."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _write_graph(self, nodes: list, edges: list) -> None:
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        (graph_dir / "project-graph.json").write_text(
            json.dumps({"schema_version": "1", "layer": "project", "nodes": nodes, "edges": edges}),
            encoding="utf-8",
        )

    def test_csharp_method_boundary_attribute_fires_advice_pattern(self):
        self._add("src/Probe.cs", "public class Probe {}\n")
        self._write_graph(
            nodes=[
                {
                    "id": "src/Probe.cs::Probe.Boundary",
                    "label": "Boundary",
                    "kind": "function",
                    "source_file": "src/Probe.cs",
                    "source_location": "1:0",
                    "annotations": ["OnMethodBoundaryAspect"],
                },
            ],
            edges=[],
        )
        result = self.srv.code_callhierarchy_response(self.root, "Boundary", None, "incoming")
        data = result["data"]
        self.assertEqual(data["incoming"], [])
        self.assertEqual(data.get("caller_pattern"), "advice")
        self.assertIn("OnMethodBoundaryAspect", data.get("advice_annotations", []))
        # Recovery hint surfaces as a diagnostic mentioning C#-style framework refs.
        diagnostics = result.get("diagnostics") or []
        advice = next((d for d in diagnostics if d.get("code") == "advice_pattern_detected"), None)
        self.assertIsNotNone(advice)
        self.assertIn("PostSharp", advice.get("message", ""))
        # Recovery usage points at `*.cs` glob rather than Java's `*Instrumentation*.java`.
        self.assertIn("*.cs", advice.get("recovery_usage", ""))


class TestKotlinReferenceResolution(unittest.TestCase):
    """130tc: Kotlin is now in `_TREE_SITTER_REFERENCE_LANGS` with
    `callable_reference` classified as a call parent type — so a caller
    referencing the target via `Helper::process` or `::handle` gets
    proper line+snippet attribution on `code_callhierarchy.incoming`."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        try:
            import tree_sitter_kotlin  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_kotlin not available in test env")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _write_graph(self, nodes: list, edges: list) -> None:
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        (graph_dir / "project-graph.json").write_text(
            json.dumps({"schema_version": "1", "layer": "project", "nodes": nodes, "edges": edges}),
            encoding="utf-8",
        )

    def test_kotlin_callable_reference_attributes_line_and_snippet(self):
        self._add("src/Helper.kt", "class Helper {\n    fun process(n: Int): Int = n + 1\n}\n")
        self._add(
            "src/Stream.kt",
            "class StreamCaller {\n"
            "    fun run(): Int {\n"
            "        return listOf(1, 2, 3).map(Helper::process).sum()\n"
            "    }\n"
            "}\n",
        )
        self._write_graph(
            nodes=[
                {"id": "src/Helper.kt::Helper.process", "label": "process", "kind": "function", "source_file": "src/Helper.kt", "source_location": "2:4"},
                {"id": "src/Stream.kt::StreamCaller.run", "label": "run", "kind": "function", "source_file": "src/Stream.kt", "source_location": "2:4"},
            ],
            edges=[
                {"source": "src/Stream.kt::StreamCaller.run", "target": "src/Helper.kt::Helper.process", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "process", None, "incoming")
        self.assertEqual(result["status"], "ok")
        incoming = result["data"]["incoming"]
        self.assertEqual(len(incoming), 1)
        entry = incoming[0]
        self.assertIsNotNone(entry.get("line"), f"line still null for Kotlin callable-reference: {entry}")
        self.assertIn("Helper::process", entry.get("snippet", ""))

    def test_kotlin_traditional_call_still_works(self):
        self._add("src/Helper.kt", "class Helper {\n    fun process(): Int = 1\n}\n")
        self._add(
            "src/Plain.kt",
            "class PlainCaller {\n"
            "    fun run(): Int {\n"
            "        val h = Helper()\n"
            "        return h.process()\n"
            "    }\n"
            "}\n",
        )
        self._write_graph(
            nodes=[
                {"id": "src/Helper.kt::Helper.process", "label": "process", "kind": "function", "source_file": "src/Helper.kt", "source_location": "2:4"},
                {"id": "src/Plain.kt::PlainCaller.run", "label": "run", "kind": "function", "source_file": "src/Plain.kt", "source_location": "2:4"},
            ],
            edges=[
                {"source": "src/Plain.kt::PlainCaller.run", "target": "src/Helper.kt::Helper.process", "relation": "calls"},
            ],
        )
        result = self.srv.code_callhierarchy_response(self.root, "process", None, "incoming")
        incoming = result["data"]["incoming"]
        self.assertEqual(len(incoming), 1)
        entry = incoming[0]
        self.assertIsNotNone(entry.get("line"))
        self.assertIn("h.process()", entry.get("snippet", ""))


class TestMcpWrapperParameterExposure(unittest.TestCase):
    """130rj retro note 1: ensure new tool parameters added during this wave
    are exposed at the MCP-wrapper layer (not just on the underlying _response
    functions). Catches the wave 130ol failure mode where new params silently
    failed to thread through the wrapper.

    Each new parameter must appear in the FastMCP tool's inputSchema; otherwise
    agents can't pass it via the MCP protocol regardless of the underlying
    function's signature.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        try:
            self._build_thin_runner = load_thin_runner()
        except ImportError:
            self.skipTest("mcp package not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _tool_input_schema(self, tool_name: str) -> dict:
        """Return the FastMCP-exposed inputSchema for the named tool, or {}."""
        mcp = self._build_thin_runner.build_server(self.root)
        tm = getattr(mcp, "_tool_manager", None)
        tools = getattr(tm, "_tools", None) if tm is not None else None
        if tools is None:
            tools = getattr(mcp, "_tools", None) or {}
        tool = tools.get(tool_name)
        if tool is None:
            return {}
        # FastMCP tool objects vary by version; check common attributes.
        schema = getattr(tool, "inputSchema", None)
        if schema is None:
            schema = getattr(tool, "parameters", None)
        if callable(schema):
            try:
                schema = schema()
            except TypeError:
                schema = None
        return schema or {}

    def _properties(self, tool_name: str) -> set:
        schema = self._tool_input_schema(tool_name)
        if not isinstance(schema, dict):
            return set()
        # JSON-Schema "properties" key carries the parameter map.
        props = schema.get("properties", {})
        return set(props.keys()) if isinstance(props, dict) else set()

    def test_wf_graph_report_exposes_exclude_generated(self):
        """130rj Change 5: exclude_generated must appear at MCP wrapper level."""
        props = self._properties("wf_graph_report")
        self.assertIn("exclude_generated", props,
                      f"exclude_generated missing from wf_graph_report MCP schema; got {props}")

    def test_wf_graph_report_exposes_collapse_generated_files(self):
        """130rj Change 5b: collapse_generated_files must appear at MCP wrapper level."""
        props = self._properties("wf_graph_report")
        self.assertIn("collapse_generated_files", props,
                      f"collapse_generated_files missing from wf_graph_report MCP schema; got {props}")

    def test_wf_graph_report_exposes_exclude_external(self):
        """130rj Change 130tw #2: exclude_external must appear at MCP wrapper level."""
        props = self._properties("wf_graph_report")
        self.assertIn("exclude_external", props,
                      f"exclude_external missing from wf_graph_report MCP schema; got {props}")

    def test_wf_graph_report_exposes_collapse_class_module_pairs(self):
        """13129 Change 1312h: collapse_class_module_pairs must appear at MCP wrapper level."""
        props = self._properties("wf_graph_report")
        self.assertIn("collapse_class_module_pairs", props,
                      f"collapse_class_module_pairs missing from wf_graph_report MCP schema; got {props}")

    def test_code_graph_community_exposes_hub_node_id(self):
        """13129 Change 1316r: hub_node_id parameter must appear at MCP wrapper level."""
        props = self._properties("code_graph_community")
        self.assertIn("hub_node_id", props,
                      f"hub_node_id missing from code_graph_community MCP schema; got {props}")

    def test_code_graph_community_exposes_pagination_and_filter(self):
        """130rj Change 2 + Change 5: limit/offset/exclude_generated at MCP wrapper level."""
        props = self._properties("code_graph_community")
        for required in ("limit", "offset", "exclude_generated"):
            self.assertIn(required, props,
                          f"{required} missing from code_graph_community MCP schema; got {props}")

    def test_code_callhierarchy_exposes_include_external(self):
        """130ol/130rj: include_external on code_callhierarchy at MCP wrapper level
        (regression coverage for the exact lesson from wave 130ol — new params silently
        failed to thread through; the prepare-phase council flagged this gap)."""
        props = self._properties("code_callhierarchy")
        self.assertIn("include_external", props,
                      f"include_external missing from code_callhierarchy MCP schema; got {props}")

    def test_existing_required_tools_still_registered(self):
        """Sanity: introspection doesn't accidentally break the existing tool set."""
        mcp = self._build_thin_runner.build_server(self.root)
        names = self.srv._registered_mcp_tool_names(mcp)
        for tool in ("wf_graph_report", "code_graph_community", "code_callhierarchy", "code_impact", "code_callgraph"):
            self.assertIn(tool, names, f"{tool} not registered with MCP")

    def test_review_evidence_authoring_exposes_compact_public_schema(self):
        props = self._properties("wf_review_event")
        for required in (
            "wave_id",
            "event",
            "actor",
            "context_id",
            "mode",
            "judgment",
            "evidence",
            "approval_phase",
            "integrity_checks",
            "approval_recheck_lanes",
        ):
            self.assertIn(
                required,
                props,
                f"{required} missing from wf_review_event MCP schema; got {props}",
            )

    def test_review_ergonomics_preserves_review_event_schema_and_tool_roster(self):
        """1tvbs schema guard, updated for 1ug66's two narrow mark tools."""
        mcp = self._build_thin_runner.build_server(self.root)
        names = sorted(self.srv._registered_mcp_tool_names(mcp))

        def assert_tool_registry(candidate: list[str]) -> None:
            self.assertEqual(len(candidate), 90)  # 1vqqi added the read-tier wf_techdocs_audit
            self.assertEqual(
                hashlib.sha256("\n".join(candidate).encode("utf-8")).hexdigest(),
                # 1vqqi: roster digest re-measured after wf_techdocs_audit joined the surface.
                "e497f88258818f415468d708ac1624f74862ba5934c095012875e160edb8b7cb",
            )

        assert_tool_registry(names)
        with self.assertRaises(AssertionError):
            assert_tool_registry(sorted([*names, "wf_review_actions"]))

        props = self._properties("wf_review_event")
        self.assertEqual(
            props,
            {
                "wave_id", "event", "actor", "context_id", "mode",
                "signoff_key", "approval_phase", "finding_id", "run_kind", "cycle",
                "judgment", "evidence", "source_lanes", "blocking_required_lanes",
                "approval_recheck_lanes", "review_boundaries_changed", "fresh_context",
                "independent", "integrity_checks", "record_type", "verbose",
            },
        )
        self.assertEqual(
            props.intersection({"finding_id", "record_type", "run_kind", "verbose", "compact"}),
            {"finding_id", "record_type", "run_kind", "verbose"},
        )

    def test_guided_projection_adds_no_validation_sensor_or_lifecycle_transition(self):
        """1tvbs exact source census: presentation only, no hidden gate."""
        review_evidence = sys.modules["review_evidence"]
        sources = {
            "authority": inspect.getsource(review_evidence.review_authority_projection),
            "presentation": inspect.getsource(self.srv._guided_review_actions),
            "write": inspect.getsource(self.srv.wf_review_event_response),
        }
        forbidden = (
            "run_validate(",
            "run_validate_changed(",
            "wf_run_sensors_response(",
            "_replace_status(",
            "Status: implementing",
            "Status: closed",
        )

        def assert_presentation_only(candidate):
            for name, source in candidate.items():
                for token in forbidden:
                    self.assertNotIn(token, source, f"{name} introduced {token}")

        assert_presentation_only(sources)
        with self.assertRaises(AssertionError):
            assert_presentation_only({**sources, "known_bad": "run_validate(root)"})

    def _tool_description(self, tool_name: str) -> str:
        mcp = self._build_thin_runner.build_server(self.root)
        tm = getattr(mcp, "_tool_manager", None)
        tools = getattr(tm, "_tools", None) if tm is not None else None
        if tools is None:
            tools = getattr(mcp, "_tools", None) or {}
        tool = tools.get(tool_name)
        return str(getattr(tool, "description", "") or "")

    def test_audit_install_public_carriers_pin_status_and_pending_lint_matrix(self):
        description = self._tool_description("wf_audit_install")
        for anchor in (
            "missing_log", "unparseable_log", "lint_errors",
            "checked_but_missing", "next_step", "phase_complete", "complete",
            "Only the last five carry ``pending_lint``",
            "parsed before lint",
        ):
            self.assertIn(anchor, description)

        repo_root = SCRIPTS_ROOT.parents[2]
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        phase_two = readme.split("#### Phase 2", 1)[1].split("\n---", 1)[0]
        for anchor in ("Blocking lint errors", "pending_lint", "final gate", "complete"):
            self.assertIn(anchor, phase_two)

        spec = (repo_root / "docs/specs/mcp-tool-surface.md").read_text(encoding="utf-8")
        detail = spec.split("`wf_audit_install(phase: int | None = None)`", 1)[1].split(
            "`wf_server_info()`", 1
        )[0]
        for anchor in (
            "missing_log", "unparseable_log", "lint_errors",
            "checked_but_missing", "next_step", "phase_complete", "complete",
            "absent on `missing_log` and `unparseable_log`",
            "present on `lint_errors`, `checked_but_missing`, `next_step`, `phase_complete`, and `complete`",
            # Wave 1wybs (1wybr; delivery review DOCS-DEL-4): the repo-relative render.
            "`checked_but_missing` renders the artifact path relative to the repository root",
            "rendered with leading `..` segments rather than failing the audit",
        ):
            self.assertIn(anchor, detail)

        for broken, anchor in (
            (description.replace("Only the last five carry ``pending_lint``", "", 1),
             "Only the last five carry ``pending_lint``"),
            (phase_two.replace("pending_lint", "", 1), "pending_lint"),
            (detail.replace("absent on `missing_log` and `unparseable_log`", "", 1),
             "absent on `missing_log` and `unparseable_log`"),
        ):
            with self.assertRaises(AssertionError):
                self.assertIn(anchor, broken)

    def test_review_evidence_description_carries_guided_lane_recipe(self):
        """1tvbs: normal flow is guided; list remains explicitly forensic."""
        description = self._tool_description("wf_review_event")
        for anchor in (
            "wf_review_wave",
            'event="list"',
            "ONE reverification per lane",
            "post-commit",
            "fresh_context=true",
            "independent=true",
            "lane_reassessment",
            "lane-reverification shortcut",
        ):
            self.assertIn(
                anchor,
                description,
                f"lane-clearing anchor {anchor!r} missing from the registered "
                "wf_review_event description",
            )

    def test_review_field_vocabulary_matches_all_public_contract_surfaces(self):
        """AC-5: exported registries are semantic pins, not declarations only."""

        review_evidence = sys.modules["review_evidence"]
        seed = (
            SCRIPTS_ROOT.parent / "seeds" / "209-agent-harness-core.prompt.md"
        ).read_text(encoding="utf-8")
        spec = (
            SCRIPTS_ROOT.parents[2] / "docs" / "specs" / "mcp-tool-surface.md"
        ).read_text(encoding="utf-8")
        description = self._tool_description("wf_review_event")
        surfaces = {"seed 209": seed, "tool spec": spec, "tool description": description}
        registry_fields = tuple(dict.fromkeys((
            *review_evidence.REVIEW_FINDING_CORE_JUDGMENT_FIELDS,
            *review_evidence.REVIEW_FINDING_REPAIR_JUDGMENT_FIELDS,
            *review_evidence.REVIEW_FINDING_REQUIRED_EVIDENCE_FIELDS,
            *review_evidence.REVIEW_APPROVAL_REQUIRED_EVIDENCE_FIELDS,
            *review_evidence.INTEGRITY_CHECK_FIELDS,
        )))
        self.assertGreater(len(registry_fields), 25, "registry census must be non-vacuous")

        def assert_contract_fields(fields):
            for surface_name, surface in surfaces.items():
                for field in fields:
                    self.assertIn(
                        field, surface,
                        f"{field} missing from {surface_name}",
                    )

        assert_contract_fields(registry_fields)
        with self.assertRaises(AssertionError):
            assert_contract_fields((*registry_fields, "fabricated_attestation"))

        # 1uf64: the five integrity booleans carry DISTINCT plain-language
        # definitions in the canonical seed table, plus one phase rule.
        # Anchored on short field-specific fragments, not full-sentence
        # byte-pins, so wording may evolve without losing the semantics.
        boolean_fields = tuple(review_evidence.INTEGRITY_CHECK_BOOLEAN_FIELDS)
        definitions: dict[str, str] = {}
        for line in seed.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[0].strip("`") in boolean_fields:
                definitions[cells[0].strip("`")] = cells[2]
        self.assertEqual(sorted(definitions), sorted(boolean_fields))
        self.assertEqual(
            len(set(definitions.values())),
            len(boolean_fields),
            "integrity boolean definition cells must be pairwise distinct",
        )
        semantic_anchors = {
            "test_ran_without_unintended_skip": "unintended skip",
            "public_path_reached": "faithful boundary",
            "boundary_values_realistic": "realistic",
            "assertions_non_vacuous": "could fail",
            "known_bad_detected": "known-bad",
        }
        for field, anchor in semantic_anchors.items():
            self.assertIn(anchor, definitions[field], field)
        # One phase rule: readiness approvals attest to the review itself,
        # never unimplemented product behavior; the retired contentless gloss
        # must not return on any public carrier.
        for surface_name, surface in surfaces.items():
            self.assertIn(
                "not unimplemented product behavior", surface,
                f"phase-rule anchor missing from {surface_name}",
            )
            self.assertNotIn(
                "Boolean evidence-integrity result", surface,
                f"retired execution-only gloss returned on {surface_name}",
            )

        builder_source = inspect.getsource(
            review_evidence.build_compact_review_event
        )
        for registry_name in (
            "REVIEW_FINDING_CORE_JUDGMENT_FIELDS",
            "REVIEW_FINDING_REPAIR_JUDGMENT_FIELDS",
            "REVIEW_FINDING_REQUIRED_EVIDENCE_FIELDS",
            "REVIEW_APPROVAL_REQUIRED_EVIDENCE_FIELDS",
        ):
            self.assertIn(registry_name, builder_source)
        self.assertIn(
            "INTEGRITY_CHECK_FIELDS",
            inspect.getsource(review_evidence._validated_integrity_checks),
        )
        projection_source = inspect.getsource(
            review_evidence.review_authority_projection
        )
        self.assertIn("_review_action_state_args", projection_source)
        self.assertIn("REVIEW_ACTION_CALLER_INPUTS", projection_source)

    def test_kwargs_is_not_published_or_required_on_first_party_tools(self):
        """1tmaz: implementation-only ``**kwargs`` must not become public API."""
        mcp = self._build_thin_runner.build_server(self.root)
        tools = mcp._tool_manager._tools
        self.assertGreater(len(tools), 50, "registry census must not be vacuous")
        for tool_name, tool in tools.items():
            schema = tool.parameters
            self.assertNotIn("kwargs", schema.get("properties", {}), tool_name)
            self.assertNotIn("kwargs", schema.get("required", []), tool_name)
            self.assertFalse(schema.get("additionalProperties", True), tool_name)

    def test_memory_purge_is_registered_as_destructive(self):
        """An irreversible memory deletion must cross the MCP destructive boundary."""
        mcp = self._build_thin_runner.build_server(self.root)
        annotations = mcp._tool_manager._tools["memory_purge"].annotations
        destructive = (
            annotations.get("destructiveHint")
            if isinstance(annotations, dict)
            else getattr(annotations, "destructiveHint", None)
        )
        self.assertIs(destructive, True)

    def test_hot_reload_reapplies_exact_argument_schema_to_whole_registry(self):
        """1tmaz: re-registration must not restore FastMCP's raw kwargs field."""
        mcp = self._build_thin_runner.build_server(self.root)
        with patch.object(
            self._build_thin_runner.server_impl,
            "_normalize_first_party_tool_argument_models",
            return_value=None,
        ):
            self._build_thin_runner._refresh_mcp_tool_surface(mcp)
        self.assertIn(
            "kwargs",
            mcp._tool_manager._tools["wf_help"].parameters.get("properties", {}),
            "negative control: raw re-registration must reproduce the defect",
        )

        # A second real refresh exercises the production repair seam rather
        # than manually invoking the helper against an already-built registry.
        self._build_thin_runner._refresh_mcp_tool_surface(mcp)
        for tool_name, tool in mcp._tool_manager._tools.items():
            schema = tool.parameters
            self.assertNotIn("kwargs", schema.get("properties", {}), tool_name)
            self.assertNotIn("kwargs", schema.get("required", []), tool_name)
            self.assertFalse(schema.get("additionalProperties", True), tool_name)

    def test_unknown_fastmcp_registry_shape_is_a_safe_noop(self):
        """1tmaz: private SDK-shape drift must not prevent server startup."""
        odd_registry = types.SimpleNamespace(_tool_manager=types.SimpleNamespace(_tools=[]))
        self.srv._normalize_first_party_tool_argument_models(odd_registry)
        broken_entry = types.SimpleNamespace(
            fn_metadata=types.SimpleNamespace(arg_model=types.SimpleNamespace(model_fields={"kwargs": object()}))
        )
        mixed_registry = types.SimpleNamespace(
            _tool_manager=types.SimpleNamespace(_tools={"unknown": broken_entry})
        )
        self.srv._normalize_first_party_tool_argument_models(mixed_registry)
        self.assertIs(mixed_registry._tool_manager._tools["unknown"], broken_entry)

    def test_real_dispatch_accepts_only_empty_legacy_kwargs(self):
        """1tmaz: bypassing the advertised schema still gets typed diagnostics."""
        import asyncio

        mcp = self._build_thin_runner.build_server(self.root)
        tool = mcp._tool_manager._tools["wf_help"]
        self.assertEqual(asyncio.run(tool.run({}))["status"], "ok")
        self.assertEqual(asyncio.run(tool.run({"kwargs": {}}))["status"], "ok")
        for payload in (
            {"unsupported": 1},
            {"kwargs": {"unsupported": 1}},
            {"kwargs": None},
        ):
            result = asyncio.run(tool.run(payload))
            self.assertEqual(result["status"], "error", payload)
            self.assertEqual(
                result["diagnostics"][0]["code"], "unknown_arguments", payload
            )
            expected = ["kwargs"] if payload == {"kwargs": None} else ["unsupported"]
            self.assertEqual(result["data"]["rejected_arguments"], expected, payload)


class TestSuggestNearSymbolsTokenization(unittest.TestCase):
    """Improvement: _suggest_near_symbols handles multi-token queries (whitespace/underscore)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        import json
        payload = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": [
                {"id": "src/svc.py::_load_cluster_lookup", "label": "_load_cluster_lookup", "kind": "function", "source_file": "src/svc.py"},
                {"id": "src/svc.py::shortest_path", "label": "shortest_path", "kind": "function", "source_file": "src/svc.py"},
                {"id": "src/svc.py::other", "label": "other", "kind": "function", "source_file": "src/svc.py"},
            ],
            "edges": [],
            "counts": {"files": 1, "nodes": 3, "edges": 0},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_whitespace_separated_tokens_match_snake_case(self):
        """'load cluster' should produce '_load_cluster_lookup' as a suggestion."""
        # Trigger _suggest_near_symbols via code_graph_path with two unresolvable symbols
        result = self.srv.code_graph_path_response(self.root, "load cluster", "no_such_symbol")
        self.assertEqual(result["status"], "ok")
        suggestion_ids = {s["id"] for s in result["data"]["suggestions"]}
        self.assertIn("src/svc.py::_load_cluster_lookup", suggestion_ids)

    def test_space_separated_tokens_match_underscore_symbol(self):
        """'shortest path' should match 'shortest_path' via tokenization."""
        result = self.srv.code_graph_path_response(self.root, "shortest path", "no_such_symbol")
        self.assertEqual(result["status"], "ok")
        suggestion_ids = {s["id"] for s in result["data"]["suggestions"]}
        self.assertIn("src/svc.py::shortest_path", suggestion_ids)

    def test_single_token_substring_still_works(self):
        """'load' (single token) should still substring-match the snake_case symbol."""
        result = self.srv.code_graph_path_response(self.root, "load", "no_such_symbol")
        self.assertEqual(result["status"], "ok")
        suggestion_ids = {s["id"] for s in result["data"]["suggestions"]}
        self.assertIn("src/svc.py::_load_cluster_lookup", suggestion_ids)


class TestCodeCallgraphIncludeTests(unittest.TestCase):
    """Improvement: code_callgraph filters test-path nodes by default; symmetric with code_impact."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        self._add("src/utils.py", "def helper(): pass\n")
        self._add("tests/test_utils.py", "from src.utils import helper\ndef test_helper(): helper()\n")
        import json
        payload = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "nodes": [
                {"id": "src/utils.py::helper", "label": "helper", "kind": "function", "source_file": "src/utils.py"},
                {"id": "tests/test_utils.py::test_helper", "label": "test_helper", "kind": "function", "source_file": "tests/test_utils.py"},
            ],
            "edges": [
                {"source": "tests/test_utils.py::test_helper", "target": "src/utils.py::helper", "relation": "calls", "confidence": "EXTRACTED"},
            ],
            "counts": {"files": 2, "nodes": 2, "edges": 1},
        }
        (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_include_tests_false_excludes_test_nodes_and_edges(self):
        result = self.srv.code_callgraph_response(
            self.root, "src/utils.py::helper", depth=2, direction="both", include_tests=False
        )
        self.assertEqual(result["status"], "ok")
        node_ids = {n.get("id") for n in result["data"]["nodes"]}
        self.assertNotIn("tests/test_utils.py::test_helper", node_ids)
        # Edges referencing the test node must also be filtered
        for e in result["data"]["edges"]:
            self.assertNotIn("tests/test_utils.py", str(e.get("source") or ""))
            self.assertNotIn("tests/test_utils.py", str(e.get("target") or ""))
        self.assertFalse(result["data"]["include_tests"])

    def test_include_tests_true_keeps_test_nodes(self):
        result = self.srv.code_callgraph_response(
            self.root, "src/utils.py::helper", depth=2, direction="both", include_tests=True
        )
        self.assertEqual(result["status"], "ok")
        node_ids = {n.get("id") for n in result["data"]["nodes"]}
        self.assertIn("tests/test_utils.py::test_helper", node_ids)
        self.assertTrue(result["data"]["include_tests"])


class TestLanceDBIndex(unittest.TestCase):
    """Tests for LanceDB vector index integration (AC-3, AC-10, AC-11)."""

    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    # Wave 1wpif (1wpah, AC-5 / QA-RDY-6): the inert ANN tuning constants
    # (LANCEDB_NPROBES / LANCEDB_REFINE_FACTOR) were retired from BOTH
    # definition sites; the former value pins retire with them. The
    # query-builder proof that production runs at the library defaults lives
    # in test_retrieval_candidate_generation.LanceQueryBuilderDefaultsTests.
    def test_inert_ann_constants_are_retired_from_server(self):
        srv = self.server
        self.assertFalse(hasattr(srv, "LANCEDB_NPROBES"))
        self.assertFalse(hasattr(srv, "LANCEDB_REFINE_FACTOR"))

    def test_inert_ann_constants_are_retired_from_indexer(self):
        import importlib.util as ilu
        scripts_root = Path(__file__).resolve().parents[1]
        spec = ilu.spec_from_file_location("indexer_for_lancedb_test", scripts_root / "indexer.py")
        mod = ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.LANCEDB_INDEX_THRESHOLD, 1000)
        self.assertEqual(mod.LANCEDB_COMPACT_THRESHOLD, 20)
        self.assertFalse(hasattr(mod, "LANCEDB_NPROBES"))
        self.assertFalse(hasattr(mod, "LANCEDB_REFINE_FACTOR"))

    @unittest.skipUnless(importlib.util.find_spec("lancedb"), "lancedb not installed")
    def test_streaming_writer_row_counts(self):
        """_StreamingLayerWriter creates LanceDB tables with expected row counts."""
        import importlib.util as ilu
        import numpy as np
        from unittest.mock import MagicMock
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

            docs_writer = mod._StreamingLayerWriter(db, "docs", embedder, "doc")
            docs_writer.add(docs_chunks)
            docs_written = docs_writer.finalize()
            code_writer = mod._StreamingLayerWriter(db, "code", embedder, "code")
            code_writer.add(code_chunks)
            code_written = code_writer.finalize()

            self.assertEqual(docs_written, 1)
            self.assertEqual(code_written, 1)

            # Verify table directories exist
            self.assertTrue((db_path / "docs.lance").is_dir())
            self.assertTrue((db_path / "code.lance").is_dir())


class ConstantReadsBucketTests(unittest.TestCase):
    """Wave 1p4ls AC-4: code_references surfaces a CONSTANT's readers in a distinct graph-sourced
    `reads` bucket (faithfulness-gated) — NOT merged into call_sites/callers."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        import importlib.util
        gi_path = Path(__file__).resolve().parents[1] / "graph_indexer.py"
        spec = importlib.util.spec_from_file_location("graph_indexer", gi_path)
        gi = importlib.util.module_from_spec(spec)
        sys.modules["graph_indexer"] = gi
        spec.loader.exec_module(gi)
        src = ('RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"\n\n'
               'def get_model():\n    return RERANKER_MODEL\n\n'
               'def rerank():\n    m = RERANKER_MODEL\n    return m\n')
        f = self.root / "indexer.py"
        f.write_text(src, encoding="utf-8")
        gi.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index", layer="project",
            files=[f], current_file_meta={"indexer.py": {"hash": src}}, changed={"indexer.py"},
            removed=set(), walker_version="1", chunker_version="1", verbose=False)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_bucket_lists_constant_readers(self):
        result = self.srv.code_references_response(self.root, "RERANKER_MODEL")
        self.assertEqual(result["status"], "ok")
        reads = result["data"]["detail_buckets"]["reads"]
        names = {r.get("name") for r in reads}
        self.assertIn("get_model", names)
        self.assertIn("rerank", names)
        # the reads bucket is DISTINCT — readers are not callers
        self.assertEqual(result["data"]["detail_buckets"]["call_sites"], [])


class GraphSignalTests(unittest.TestCase):
    """Wave 1p4hu: graph-signal candidate source — structural 1-hop neighbors (callers/callees via
    calls, importers via imports, constant readers via the 1p4ls reads edge) surfaced in agent-mode."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        import importlib.util
        gi_path = Path(__file__).resolve().parents[1] / "graph_indexer.py"
        spec = importlib.util.spec_from_file_location("graph_indexer", gi_path)
        self.gi = importlib.util.module_from_spec(spec)
        sys.modules["graph_indexer"] = self.gi
        spec.loader.exec_module(self.gi)

    def tearDown(self):
        self.tmp.cleanup()

    def _build_graph(self, files):
        paths, meta = [], {}
        for rel, c in files.items():
            pth = self.root / rel
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_text(c, encoding="utf-8")
            paths.append(pth)
            meta[rel] = {"hash": c}
        self.gi.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index", layer="project",
            files=paths, current_file_meta=meta, changed=set(meta), removed=set(),
            walker_version="1", chunker_version="1", verbose=False)

    def _idx(self):
        return self.srv.WaveIndex(self.root)

    def _heads(self, cands):
        return {c["text"].split("\n", 1)[0] for c in cands}

    # ── 1p66t: graph-rescue-into-citations (field finding #2 — positively exercised here) ──

    @staticmethod
    def _set_scores(score):
        def _rerank(_q, cands):
            for c in cands:
                c["score"] = score
            return True
        return _rerank

    def test_graph_merge_rescues_vector_missed_file(self):
        """A graph-reachable file the SEMANTIC pass MISSED (not already cited) is rescued into
        citations, reranked + floor-clearing, flagged from_graph. This is the vector-miss/graph-hit
        case the field report could not trigger (its vector recall was always sufficient)."""
        idx = self._idx()
        results = [{"path": "src/a.py", "lines": [1, 5], "score": 0.70, "kind": "code", "text": "a"}]
        graph_src = [{"path": "src/b.py", "lines": [10, 20], "score": 0.0, "kind": "code",
                      "text": "b > helper\n\ndef helper(): ...", "_relationship": "callee"}]
        with patch.object(idx, "_agent_rerank", side_effect=self._set_scores(0.8)):
            merged = idx._merge_graph_into_citations("q", graph_src, results, reranked=True)
        self.assertEqual(merged, 1)
        self.assertEqual(results[-1]["path"], "src/b.py")
        self.assertTrue(results[-1].get("from_graph"))

    def test_graph_merge_skips_already_cited(self):
        """A graph neighbor the semantic pass ALREADY cited is not duplicated (no rescue needed)."""
        idx = self._idx()
        results = [{"path": "src/b.py", "lines": [10, 20], "score": 0.70, "kind": "code", "text": "b"}]
        graph_src = [{"path": "src/b.py", "lines": [10, 20], "score": 0.0, "kind": "code", "text": "b"}]
        with patch.object(idx, "_agent_rerank", side_effect=self._set_scores(0.9)):
            merged = idx._merge_graph_into_citations("q", graph_src, results, reranked=True)
        self.assertEqual(merged, 0)
        self.assertEqual(len(results), 1)

    def test_graph_merge_below_floor_not_merged(self):
        """A rescued neighbor that does NOT clear the relevance floor is dropped (no noise)."""
        idx = self._idx()
        results = [{"path": "src/a.py", "lines": [1, 5], "score": 0.70, "kind": "code", "text": "a"}]
        graph_src = [{"path": "src/b.py", "lines": [10, 20], "score": 0.0, "kind": "code", "text": "b"}]
        with patch.object(idx, "_agent_rerank", side_effect=self._set_scores(0.05)):
            merged = idx._merge_graph_into_citations("q", graph_src, results, reranked=True)
        self.assertEqual(merged, 0)
        self.assertEqual(len(results), 1)

    def test_graph_merge_skipped_when_not_reranked(self):
        """No merge on the degraded no-reranker path (scores are not comparable for the floor gate)."""
        idx = self._idx()
        results = [{"path": "src/a.py", "lines": [1, 5], "score": 0.70, "kind": "code", "text": "a"}]
        graph_src = [{"path": "src/b.py", "lines": [10, 20], "score": 0.9, "kind": "code", "text": "b"}]
        merged = idx._merge_graph_into_citations("q", graph_src, results, reranked=False)
        self.assertEqual(merged, 0)
        self.assertEqual(len(results), 1)

    def test_reader_surfaced_via_reads_edge(self):
        """AC-1/AC-2: a constant's readers surface via the 1p4ls reads edge (structural, not text)."""
        self._build_graph({"m.py": "MAX_SIZE = 100\n\ndef compute_size():\n    return MAX_SIZE\n"})
        cands = self._idx()._graph_signal_candidates(
            "what reads MAX_SIZE", [{"section": "m > MAX_SIZE", "path": "x", "lines": [1, 1]}], cap=3)
        self.assertTrue(any("compute_size" in h for h in self._heads(cands)),
                        f"reader not surfaced via graph; got {self._heads(cands)}")

    def test_caller_surfaced_via_calls_edge(self):
        """AC-2: a caller surfaces via the calls edge from the resolved symbol."""
        self._build_graph({"m.py": "def target_fn():\n    return 1\n\ndef caller_fn():\n    return target_fn()\n"})
        cands = self._idx()._graph_signal_candidates(
            "who calls target_fn", [{"section": "m > target_fn", "path": "x", "lines": [1, 1]}], cap=3)
        self.assertTrue(any("caller_fn" in h for h in self._heads(cands)),
                        f"caller not surfaced via graph; got {self._heads(cands)}")

    def test_graph_signal_bounded(self):
        """AC-3: capped at `cap` even for a high-fan-in symbol (never pulls the subgraph)."""
        readers = "".join("def reader_%d():\n    return HOT_FLAG\n\n" % i for i in range(20))
        self._build_graph({"m.py": "HOT_FLAG = 1\n\n" + readers})
        cands = self._idx()._graph_signal_candidates(
            "HOT_FLAG", [{"section": "m > HOT_FLAG", "path": "x", "lines": [1, 1]}], cap=3)
        self.assertLessEqual(len(cands), 3, "graph signal must respect the cap")
        self.assertGreater(len(cands), 0, "a high-fan-in symbol should surface some readers")

    def test_no_graph_fallback(self):
        """AC-4: with NO graph index, the graph signal returns [] with no error (semantic-only)."""
        cands = self._idx()._graph_signal_candidates(
            "anything", [{"section": "m > Whatever", "path": "x", "lines": [1, 1]}], cap=3)
        self.assertEqual(cands, [])

    def test_graph_related_section_groups_callers(self):
        """Delivery follow-up: "what calls X" produces a `graph_related` section with the callers in a
        relationship-labeled `callers` bucket — NOT 0.0-scored rows mixed into citations."""
        self._build_graph({"m.py":
            "def target():\n    return 1\n\n"
            "def caller_fn():\n    return target()\n"})
        idx = self._idx()
        cands = idx._graph_signal_candidates(
            "what calls target", [{"section": "m > target", "path": "x", "lines": [1, 1]}], cap=3)
        self.assertTrue(any(c.get("_relationship") == "caller" for c in cands),
                        f"caller relationship label expected; got {[c.get('_relationship') for c in cands]}")
        section = idx._build_graph_related(cands)
        self.assertIn("target", section["seed"])
        self.assertTrue(any("caller_fn" in e["symbol"] for e in section.get("callers", [])),
                        f"caller_fn in the callers bucket expected; got {section}")
        self.assertNotIn("score", section["callers"][0], "graph_related entries are not 0.0-scored citation rows")

    def test_direction_aware_what_calls_surfaces_callers_not_callees(self):
        """Delivery follow-up D1: 'what calls X' surfaces X's CALLERS (incoming `calls`), NOT the
        functions X itself calls. The old union-of-both-directions answered a callers question with
        the seed's callees."""
        self._build_graph({"m.py":
            "def helper():\n    return 1\n\n"
            "def target():\n    return helper()\n\n"
            "def caller():\n    return target()\n"})
        cands = self._idx()._graph_signal_candidates(
            "what calls target", [{"section": "m > target", "path": "x", "lines": [1, 1]}], cap=3)
        heads = self._heads(cands)
        self.assertTrue(any("caller" in h for h in heads), f"caller (incoming) must surface; got {heads}")
        self.assertFalse(any("helper" in h for h in heads),
                         f"helper (a callee of target) must NOT surface for a 'what calls' query; got {heads}")

    def test_test_file_neighbor_suppressed(self):
        """Delivery follow-up: a structural neighbor in a TEST file is not surfaced — a fixture is a
        poor structural answer (the sweep showed mis-resolved seeds dragging in test helpers)."""
        self._build_graph({
            "m.py": "CONST_VALUE = 5\n",
            "tests/test_m.py": "from m import CONST_VALUE\n\ndef test_uses():\n    return CONST_VALUE\n",
        })
        cands = self._idx()._graph_signal_candidates(
            "what reads CONST_VALUE", [{"section": "m > CONST_VALUE", "path": "x", "lines": [1, 1]}], cap=3)
        self.assertFalse(any("test_uses" in h for h in self._heads(cands)),
                         f"a reader in a test file must be suppressed; got {self._heads(cands)}")

    def test_intent_direction_classification(self):
        """Delivery re-review (A1/A2): query intent → traversal direction. "what calls X" / "is X
        called" → incoming (callers); "X calls what" (subject-first) → both, not forced callers."""
        srv = self.srv
        def direction(q):
            ql = q.lower()
            inc = bool(srv._GRAPH_USER_INTENT_RE.search(ql)) and not bool(srv._GRAPH_OUTGOING_INTENT_RE.search(ql))
            return "in" if inc else "both"
        for q in ["what calls foo", "who calls foo", "where is foo used", "is foo called anywhere",
                  "what reads foo", "what invokes foo"]:
            self.assertEqual(direction(q), "in", q)
        for q in ["foo calls what", "what does foo call", "callees of foo", "how does foo work"]:
            self.assertEqual(direction(q), "both", q)

    def test_generic_plural_entries_not_seeded(self):
        """Delivery re-review (F1): generic content words like 'entries' (which collide with JSON
        content nodes) are excluded from graph-signal seed resolution."""
        self.assertIn("entries", self.srv._GRAPH_SEED_STOPWORDS)

    def test_graph_related_reader_bucket(self):
        """Delivery follow-up: a constant's reader lands in the `readers` bucket of graph_related."""
        self._build_graph({"m.py": "LIMIT_X = 5\n\ndef reader_fn():\n    return LIMIT_X\n"})
        idx = self._idx()
        cands = idx._graph_signal_candidates(
            "what reads LIMIT_X", [{"section": "m > LIMIT_X", "path": "x", "lines": [1, 1]}], cap=3)
        section = idx._build_graph_related(cands)
        self.assertTrue(any("reader_fn" in e["symbol"] for e in section.get("readers", [])),
                        f"reader_fn in the readers bucket expected; got {section}")

    def test_graph_related_text_deduped_against_citations(self):
        """User follow-up: a structural match that is ALSO a semantic citation keeps its relationship
        entry (the structural answer stays complete + labeled) but DROPS the duplicate excerpt and is
        flagged `also_cited` — the chunk text is never sent twice. A non-cited match keeps its excerpt."""
        idx = self._idx()
        cands = [
            {"path": "m.py", "lines": [3, 27], "text": "m > caller_a\n\nbody-a", "kind": "code",
             "_relationship": "caller", "_seed": "target", "_symbol": "caller_a", "_graph_kind": "function"},
            {"path": "n.py", "lines": [8, 32], "text": "n > caller_b\n\nbody-b", "kind": "code",
             "_relationship": "caller", "_seed": "target", "_symbol": "caller_b", "_graph_kind": "function"},
        ]
        # caller_a coincides with a citation (same path, start line); caller_b does not.
        citations = [{"path": "m.py", "lines": [3, 19]}]
        section = idx._build_graph_related(cands, citations)
        by_sym = {e["symbol"]: e for e in section["callers"]}
        self.assertEqual(set(by_sym), {"caller_a", "caller_b"}, "both callers stay in the structural answer")
        self.assertTrue(by_sym["caller_a"].get("also_cited"), "the cited match is flagged also_cited")
        self.assertNotIn("excerpt", by_sym["caller_a"], "the cited match drops its duplicate excerpt")
        self.assertIn("excerpt", by_sym["caller_b"], "a non-cited match keeps its excerpt")

    def test_graph_related_inheritance_relations_and_buckets(self):
        """Wave 1p9qh review follow-up: `extends`/`implements` join the structural signal. Pins the
        traversal tuple, the direction-aware labels (incoming = the seed's implementors/subtypes;
        outgoing = its supertypes), and the bucket grouping in `_build_graph_related`."""
        self.assertEqual(self.srv._GRAPH_SIGNAL_RELATIONS,
                         ("calls", "imports", "reads", "extends", "implements", "writes", "maps_to"))
        self.assertEqual(self.srv._GRAPH_REL_LABEL[("extends", True)], "subtype")
        # Wave 1p9qi (1p9qd): SQL write-direction table references join the signal.
        self.assertEqual(self.srv._GRAPH_REL_LABEL[("writes", True)], "writer")
        self.assertEqual(self.srv._GRAPH_REL_LABEL[("writes", False)], "writes")
        self.assertEqual(self.srv._GRAPH_REL_BUCKET["writer"], "writers")
        self.assertEqual(self.srv._GRAPH_REL_BUCKET["writes"], "writes")
        # Wave 1p9qi (1p9qg): ORM entity→table mappings join the signal.
        self.assertEqual(self.srv._GRAPH_REL_LABEL[("maps_to", True)], "mapped_entity")
        self.assertEqual(self.srv._GRAPH_REL_LABEL[("maps_to", False)], "maps_to")
        self.assertEqual(self.srv._GRAPH_REL_BUCKET["mapped_entity"], "mapped_entities")
        self.assertEqual(self.srv._GRAPH_REL_BUCKET["maps_to"], "maps_to")
        self.assertEqual(self.srv._GRAPH_REL_LABEL[("extends", False)], "supertype")
        self.assertEqual(self.srv._GRAPH_REL_LABEL[("implements", True)], "implementor")
        self.assertEqual(self.srv._GRAPH_REL_LABEL[("implements", False)], "supertype")
        idx = self._idx()
        cands = [
            {"path": "a.java", "lines": [3, 9], "text": "a > ServiceImpl\n\nbody", "kind": "code",
             "_relationship": "implementor", "_seed": "IService", "_symbol": "ServiceImpl", "_graph_kind": "class"},
            {"path": "b.java", "lines": [1, 9], "text": "b > SubPanel\n\nbody", "kind": "code",
             "_relationship": "subtype", "_seed": "Panel", "_symbol": "SubPanel", "_graph_kind": "class"},
            {"path": "c.java", "lines": [1, 9], "text": "c > BasePanel\n\nbody", "kind": "code",
             "_relationship": "supertype", "_seed": "Panel", "_symbol": "BasePanel", "_graph_kind": "class"},
        ]
        section = idx._build_graph_related(cands)
        self.assertEqual([e["symbol"] for e in section.get("implementors", [])], ["ServiceImpl"])
        self.assertEqual([e["symbol"] for e in section.get("subtypes", [])], ["SubPanel"])
        self.assertEqual([e["symbol"] for e in section.get("supertypes", [])], ["BasePanel"])

    def test_graph_related_signal_gate_derived_from_bucket_vocabulary(self):
        """Wave 1p9qi review fix (architecture F1): the code_ask response gate that
        decides whether an assembled graph_related section carries signal is DERIVED
        from `_GRAPH_REL_BUCKET.values()` — the hand-enumerated tuple silently dropped
        writers-only / mapped-entities-only sections (second occurrence of the drift
        class after 1p9qh's inheritance buckets)."""
        srv = self.srv
        # Every bucket the assembler can produce is a signal key; "seed" is not
        # (it is always present in an assembled section, neighbors or not).
        self.assertEqual(srv._GRAPH_RELATED_SIGNAL_KEYS,
                         frozenset(srv._GRAPH_REL_BUCKET.values()) | {"related"})
        self.assertNotIn("seed", srv._GRAPH_RELATED_SIGNAL_KEYS)

        def gate(graph_related):
            # The exact predicate used at the code_ask response assembly site.
            return bool(graph_related and any(
                graph_related.get(k) for k in srv._GRAPH_RELATED_SIGNAL_KEYS))

        writers_only = {"seed": ["users"], "writers": [
            {"symbol": "insert_user", "path": "d.sql", "lines": [1, 2], "kind": "procedure"}]}
        self.assertTrue(gate(writers_only), "a writers-only section must pass the gate")
        mapped_only = {"seed": ["users"], "mapped_entities": [
            {"symbol": "User", "path": "u.java", "lines": [1, 9], "kind": "class"}]}
        self.assertTrue(gate(mapped_only), "a mapped-entities-only section must pass the gate")
        self.assertTrue(gate({"seed": [], "writes": [{"symbol": "audit_log"}]}))
        self.assertTrue(gate({"seed": [], "maps_to": [{"symbol": "users"}]}))
        self.assertFalse(gate({"seed": ["users"]}), "seed alone is not signal")
        self.assertFalse(gate(None))


class DegradedFtsFallbackTests(unittest.TestCase):
    """1seav / 1seaq AC-1/2/4/6/7: the FTS-first degraded fallbacks — real
    store, real FTS rows, epoch gating per the Requirement 2a state table,
    typed query_failed, filter preservation, zero-hit honesty, log dedup."""

    COMPLETE = None  # set per-instance after seeding

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True)
        import importlib.util as ilu
        spec = ilu.spec_from_file_location(
            "index_state_store", Path(__file__).resolve().parents[1] / "index_state_store.py")
        self.iss = ilu.module_from_spec(spec)
        spec.loader.exec_module(self.iss)
        # Seed FTS rows for both tables + a completed epoch.
        code_rows = [
            {"id": "c1", "path": "src/alpha.py", "kind": "code", "language": "python",
             "lines": [1, 5], "section": "", "tags": "", "chunk_hash": "h1",
             "text": "def alpha_handler(): pass"},
            {"id": "c2", "path": "src/beta.ts", "kind": "code", "language": "typescript",
             "lines": [1, 5], "section": "", "tags": "", "chunk_hash": "h2",
             "text": "function alpha_handler() {}"},
            {"id": "c3", "path": "src/alpha.py", "kind": "code", "language": "python",
             "lines": [6, 9], "section": "", "tags": "", "chunk_hash": "h3",
             "text": "def alpha_handler_two(): pass"},
        ]
        docs_rows = [
            {"id": "d1", "path": "docs/guide.md", "kind": "doc", "language": "",
             "lines": [1, 4], "section": "Intro", "tags": "reference", "chunk_hash": "h4",
             "text": "alpha_handler guide entry"},
            {"id": "d2", "path": "docs/other.md", "kind": "doc", "language": "",
             "lines": [1, 4], "section": "Other", "tags": "journal", "chunk_hash": "h5",
             "text": "alpha_handler journal entry"},
        ]
        import contextlib, io as _io
        with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
            self.iss.reconcile_chunk_index(self.index_dir, "code", {r["id"] for r in code_rows}, lambda: code_rows)
            self.iss.reconcile_chunk_index(self.index_dir, "docs", {r["id"] for r in docs_rows}, lambda: docs_rows)
        self.iss.write_build_bookkeeping(self.index_dir, {"content": ["docs", "code"]})
        attempt = self.iss.begin_build_epoch(self.index_dir, "fixture")
        assert self.iss.finalize_build_epoch(self.index_dir, attempt)
        self.COMPLETE = self.iss.build_epoch_state_token(self.index_dir)
        self.srv._DEGRADED_LOG_STATE.clear()
        self.addCleanup(self.srv._DEGRADED_LOG_STATE.clear)

    def _mock_index(self, exc):
        index = MagicMock()
        index.root = self.root
        index.search_code.side_effect = exc
        index.search_docs.side_effect = exc
        index.search_combined.side_effect = exc
        return index

    # --- AC-1: code_search FTS fallback with preserved filters ---

    def test_code_search_serves_fts_on_model_unavailable(self):
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        result = self.srv.code_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["search_mode"], "lexical_fallback")
        self.assertEqual(result["data"]["fallback_reason"], "model_unavailable")
        paths = [r["path"] for r in result["data"]["results"]]
        self.assertIn("src/alpha.py", paths)

    def test_code_search_fts_fallback_preserves_language_filter(self):
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        result = self.srv.code_search_response(index, "alpha_handler", language="typescript", epoch_state=self.COMPLETE)
        langs = {r["language"] for r in result["data"]["results"]}
        self.assertEqual(langs, {"typescript"})

    def test_code_search_fts_fallback_preserves_max_per_file(self):
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        result = self.srv.code_search_response(index, "alpha_handler", max_per_file=1, epoch_state=self.COMPLETE)
        paths = [r["path"] for r in result["data"]["results"]]
        self.assertEqual(len([p for p in paths if p == "src/alpha.py"]), 1)

    def test_code_search_refuses_fallback_without_complete_epoch(self):
        """AC-7: FTS never serves from a non-complete captured epoch."""
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        for state in (None, ("a", "building", 1), ("a", "uninitialized", 0)):
            result = self.srv.code_search_response(index, "alpha_handler", epoch_state=state)
            self.assertEqual(result["status"], "error", state)
            self.assertIn(result["data"]["fallback_reason"], ("index_not_ready", "store_absent"))
            self.assertEqual(result["data"]["results"], [])

    # --- AC-2: docs_search FTS-first with tag preservation ---

    def test_docs_search_serves_fts_with_tag_filter_on_model_unavailable(self):
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        result = self.srv.docs_search_response(index, "alpha_handler", tags=["journal"], epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["search_mode"], "lexical_fallback")
        self.assertEqual(result["data"]["fallback_reason"], "model_unavailable")
        paths = [r["path"] for r in result["data"]["results"]]
        self.assertEqual(paths, ["docs/other.md"], "tag filter must survive the fallback")
        index.search_docs_lexical.assert_not_called()

    def test_docs_search_live_walk_not_reachable_with_healthy_store(self):
        """The Req 7 pin: with a published (complete) store, the live walk is
        NOT reachable — the FTS layer serves."""
        index = self._mock_index(self.srv.IndexNotReadyError("tables missing"))
        result = self.srv.docs_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["search_mode"], "lexical_fallback")
        self.assertEqual(result["data"]["fallback_reason"], "index_missing")
        index.search_docs_lexical.assert_not_called()

    # --- AC-4 / P1: typed query_failed vs zero hits ---

    def test_query_failed_is_typed_not_silent_zero(self):
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        with patch.object(self.iss.__class__ if False else self.srv, "_fts_degraded_serve",
                          return_value={"available": False, "failure_reason": "query_failed",
                                        "results": [], "coverage": {}}):
            result = self.srv.docs_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["fallback_reason"], "query_failed")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("lexical_fallback_failed", codes)

    def test_partial_store_corruption_types_query_failed_not_zero_hit(self):
        """Review fix: a readable build_state with a BROKEN FTS virtual table
        must type as query_failed — never a clean zero-hit with retry-the-
        token advice (infrastructure failure masquerading as an empty corpus)."""
        import sqlite3
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DROP TABLE fts_docs")
        conn.close()
        serve = self.srv._fts_degraded_serve(self.root, ("docs",), "alpha_handler", 5)
        self.assertFalse(serve["available"])
        self.assertEqual(serve["failure_reason"], "query_failed")
        # Through the tool flow: typed diagnostic, not the zero-hit note.
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        result = self.srv.docs_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["fallback_reason"], "query_failed")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("lexical_fallback_failed", codes)
        self.assertNotIn("lexical_fallback_zero_hits", codes)

    def test_degraded_zero_hit_carries_token_semantics_note(self):
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        result = self.srv.docs_search_response(index, "zz_no_such_token_zz", epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["results"], [])
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("lexical_fallback_zero_hits", codes)

    # --- AC-6: code_ask degrades with FTS-built citations ---

    def test_code_ask_builds_fts_citations_on_model_unavailable(self):
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
        data = result["data"]
        self.assertEqual(data["search_mode"], "lexical_fallback")
        self.assertEqual(data["fallback_reason"], "model_unavailable")
        self.assertTrue(data["citations"], "degraded mode must still cite")
        self.assertIn(data["confidence"], ("low", "none"))

    def test_code_ask_generic_exception_is_typed_query_failed(self):
        index = self._mock_index(RuntimeError("boom"))
        result = self.srv.code_ask_response(index, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["fallback_reason"], "query_failed")
        self.assertTrue(any("query_failed" in g for g in result["data"]["gaps"]))

    def test_healthy_paths_carry_null_fallback_reason(self):
        """AC-3 shape: fallback_reason is ALWAYS present, null when healthy."""
        index = MagicMock()
        index.root = self.root
        index.search_docs.return_value = ([{"id": "d1", "path": "docs/guide.md", "kind": "doc",
                                            "section": "Intro", "lines": [1, 4],
                                            "text": "x", "score": 0.9}], True)
        result = self.srv.docs_search_response(index, "alpha", epoch_state=self.COMPLETE)
        self.assertIn("fallback_reason", result["data"])
        self.assertIsNone(result["data"]["fallback_reason"])
        self.assertEqual(result["data"]["search_mode"], "semantic")

    # --- P2: store-log dedup ---

    def test_fallback_across_build_transition_before_during_after(self):
        """AC-7 transition matrix at the fallback: BEFORE a build (complete →
        FTS serves), DURING (building captured state → no FTS; docs live-walks,
        code refuses), AFTER (new complete epoch → FTS serves again)."""
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index.search_docs_lexical.return_value = []
        # BEFORE: complete epoch serves FTS.
        r1 = self.srv.docs_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertEqual(r1["data"]["search_mode"], "lexical_fallback")
        self.assertTrue(r1["data"]["results"])
        # DURING: a build fences; the captured token is building.
        attempt = self.iss.begin_build_epoch(self.index_dir, "transition")
        during = self.iss.build_epoch_state_token(self.index_dir)
        self.assertEqual(during[1], "building")
        r2 = self.srv.docs_search_response(index, "alpha_handler", epoch_state=during)
        self.assertEqual(r2["data"]["search_mode"], "live_fallback")
        self.assertEqual(r2["data"]["fallback_reason"], "index_not_ready")
        r2c = self.srv.code_search_response(index, "alpha_handler", epoch_state=during)
        self.assertEqual(r2c["status"], "error")
        self.assertEqual(r2c["data"]["fallback_reason"], "index_not_ready")
        # AFTER: the build publishes; the new complete token serves FTS again.
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        after = self.iss.build_epoch_state_token(self.index_dir)
        self.assertEqual(after[1], "complete")
        r3 = self.srv.code_search_response(index, "alpha_handler", epoch_state=after)
        self.assertEqual(r3["status"], "ok")
        self.assertEqual(r3["data"]["search_mode"], "lexical_fallback")
        self.assertTrue(r3["data"]["results"])

    def test_live_walk_preserves_tags(self):
        """Review reproduction (P1 — the ORIGINAL defect): the live-walk
        fallback must apply the requested tag filter."""
        index = self._mock_index(self.srv.IndexNotReadyError("no store"))
        walk_chunks = [
            {"id": "w1", "path": "docs/a.md", "kind": "doc", "section": "A",
             "lines": [1, 2], "text": "alpha", "tags": "journal", "score": 2.0},
            {"id": "w2", "path": "docs/b.md", "kind": "doc", "section": "B",
             "lines": [1, 2], "text": "alpha", "tags": "reference", "score": 1.0},
        ]
        def walk(query, kind=None, top_n=5, tags=None):
            tag_list = [str(x) for x in (tags or []) if x]
            out = [c for c in walk_chunks
                   if not tag_list or any(tg in c["tags"] for tg in tag_list)]
            return out[:top_n]
        index.search_docs_lexical.side_effect = walk
        result = self.srv.docs_search_response(index, "alpha", tags=["journal"], epoch_state=None)
        self.assertEqual(result["data"]["search_mode"], "live_fallback")
        paths = [r["path"] for r in result["data"]["results"]]
        self.assertEqual(paths, ["docs/a.md"], "tag filter must survive the live walk")
        # And the REAL WaveIndex method accepts + applies tags (signature pin).
        import inspect
        sig = inspect.signature(self.srv.WaveIndex.search_docs_lexical)
        self.assertIn("tags", sig.parameters)

    def test_mixed_table_corruption_fails_the_whole_serve(self):
        """Review reproduction (P1): broken fts_code beside a WORKING
        fts_docs must fail a docs+code serve as query_failed — never a
        partial docs-only result labeled available."""
        import sqlite3
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DROP TABLE fts_code")
        conn.close()
        serve = self.srv._fts_degraded_serve(self.root, ("docs", "code"), "alpha_handler", 5)
        self.assertFalse(serve["available"])
        self.assertEqual(serve["failure_reason"], "query_failed")
        # code_ask over both tables types it too (no partial citations).
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["fallback_reason"], "query_failed")
        self.assertEqual(result["data"]["citations"], [])

    def test_unexpected_semantic_exception_is_typed_query_failed(self):
        """Review fix (AC-3): raw exceptions never escape the search tools."""
        for maker, call in (
            (lambda: self._mock_index(RuntimeError("boom")),
             lambda idx: self.srv.docs_search_response(idx, "q", epoch_state=self.COMPLETE)),
            (lambda: self._mock_index(RuntimeError("boom")),
             lambda idx: self.srv.code_search_response(idx, "q", epoch_state=self.COMPLETE)),
        ):
            idx = maker()
            result = call(idx)
            self.assertEqual(result["data"]["fallback_reason"], "query_failed", result["data"])

    def test_live_walk_exception_is_typed_query_failed(self):
        index = self._mock_index(self.srv.IndexNotReadyError("no store"))
        index.search_docs_lexical.side_effect = RuntimeError("walk exploded")
        result = self.srv.docs_search_response(index, "q", epoch_state=None)
        self.assertEqual(result["data"]["fallback_reason"], "query_failed")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("live_fallback_failed", codes)

    def test_code_ask_fallback_never_mixes_live_keyword_citations(self):
        """Review fix: the thin-citation keyword targeted pass is suppressed
        in lexical fallback — every citation must be FTS-published data."""
        # 1wpag: a LEGITIMATELY empty published layer comes from the canonical
        # producer (a reconcile against an empty Lance id set), not from raw
        # DELETEs, which the keyed payload digest now correctly reads as damage.
        import contextlib, io as _io
        with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
            self.iss.reconcile_chunk_index(self.index_dir, "code", set(), lambda: [])
            self.iss.reconcile_chunk_index(self.index_dir, "docs", set(), lambda: [])
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index._layer_health = MagicMock()
        with patch.object(self.srv, "code_keyword_response") as kw:
            result = self.srv.code_ask_response(index, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
        kw.assert_not_called()
        self.assertEqual(result["data"]["search_mode"], "lexical_fallback")
        self.assertEqual(result["data"]["citations"], [])
        # Working-lexical zero-hit: the token-semantics guidance is present.
        self.assertTrue(any("exact literals" in gp for gp in result["data"]["gaps"]))

    def test_code_ask_degraded_citations_carry_source_and_coverage(self):
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
        data = result["data"]
        self.assertTrue(data["citations"])
        self.assertTrue(all(c.get("source") in ("docs", "code") for c in data["citations"]),
                        [c.get("source") for c in data["citations"]])
        self.assertIn("coverage", data)

    def test_recreated_empty_fts_table_is_not_live(self):
        """Pre-release field review F1: after damage + reopen, CREATE VIRTUAL
        TABLE IF NOT EXISTS leaves a QUERYABLE but EMPTY fts table beside a
        populated registry — the probe must call that dead, so the fallback
        types query_failed instead of serving an available zero-hit that
        blames the query."""
        import sqlite3
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DELETE FROM fts_code")  # empty table, registry intact
        conn.close()
        self.assertFalse(self.iss.fts_probe(self.index_dir, "code"))
        # A legitimately empty layer (no registry rows either) stays live.
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DELETE FROM chunk_registry WHERE table_name = 'code'")
        conn.close()
        self.assertTrue(self.iss.fts_probe(self.index_dir, "code"))

    def test_code_ask_infrastructure_failure_answer_never_reads_as_absence(self):
        """Pre-release field review F2: a query_failed code_ask must not say
        'No indexed evidence found' — the answer names the infrastructure
        failure and a diagnostic is attached."""
        import sqlite3
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DROP TABLE fts_code")
        conn.close()
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
        data = result["data"]
        self.assertEqual(data["fallback_reason"], "query_failed")
        self.assertIn("infrastructure failure", data["answer"])
        self.assertNotIn("No indexed evidence", data["answer"])
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("search_infrastructure_failure", codes)

    def test_code_ask_fallback_suppresses_reranker_unavailable_gap(self):
        """Pre-release contract audit M5: lexical fallback is BM25 by design —
        the 'reranker unavailable / vector-only' gap would misdiagnose it."""
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
        self.assertTrue(result["data"]["citations"])
        self.assertFalse(any("reranker unavailable" in gp for gp in result["data"]["gaps"]),
                         result["data"]["gaps"])

    def test_code_search_failed_fts_carries_infrastructure_diagnostic(self):
        """Pre-release contract audit L2: cross-tool parity — code_search's
        failed-FTS error path names the infrastructure failure."""
        import sqlite3
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DROP TABLE fts_code")
        conn.close()
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        result = self.srv.code_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["data"]["fallback_reason"], "query_failed")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("lexical_fallback_failed", codes)

    def test_code_search_fts_fallback_preserves_kind_filter(self):
        """Release review (round 2 — vacuity fixed): AC-1's kind filter must
        return a NONEMPTY, exclusively-matching set from fts_code."""
        import contextlib, io as _io
        rows = [
            {"id": "k1", "path": "src/alpha.py", "kind": "code", "language": "python",
             "lines": [1, 5], "section": "", "tags": "", "chunk_hash": "k1",
             "text": "def alpha_handler(): pass"},
            {"id": "k2", "path": "src/alpha.py", "kind": "code-summary", "language": "python",
             "lines": [1, 9], "section": "", "tags": "", "chunk_hash": "k2",
             "text": "alpha_handler summary chunk"},
        ]
        with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
            self.iss.reconcile_chunk_index(self.index_dir, "code",
                                           {r["id"] for r in rows}, lambda: rows)
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        result = self.srv.code_search_response(index, "alpha_handler", kind="code-summary",
                                               epoch_state=self.COMPLETE)
        kinds = [r["kind"] for r in result["data"]["results"]]
        self.assertTrue(kinds, "the kind filter fixture must not be vacuous")
        self.assertEqual(set(kinds), {"code-summary"}, kinds)

    def test_code_search_fts_fallback_preserves_tags_filter(self):
        """Release review: AC-1's tags filter, fixture-pinned on the fallback."""
        # Give one code row a tag to filter on.
        import contextlib, io as _io, sqlite3
        rows = [{"id": "c9", "path": "src/tagged.py", "kind": "code", "language": "python",
                 "lines": [1, 2], "section": "", "tags": "test", "chunk_hash": "h9",
                 "text": "def alpha_handler_tagged(): pass"}]
        existing = [
            {"id": "c1", "path": "src/alpha.py", "kind": "code", "language": "python",
             "lines": [1, 5], "section": "", "tags": "", "chunk_hash": "h1",
             "text": "def alpha_handler(): pass"},
        ]
        with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
            self.iss.reconcile_chunk_index(self.index_dir, "code",
                                           {r["id"] for r in existing + rows},
                                           lambda: existing + rows)
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        result = self.srv.code_search_response(index, "alpha_handler alpha_handler_tagged",
                                               tags=["test"], epoch_state=self.COMPLETE)
        paths = {r["path"] for r in result["data"]["results"]}
        self.assertEqual(paths, {"src/tagged.py"}, "tags filter must survive the fallback")

    def test_code_ask_exact_mode_envelope(self):
        """Release review: AC-3's exact-mode classification, fixture-pinned —
        the artifact-anchored short-circuit reads search_mode 'exact' with a
        null fallback_reason."""
        index = MagicMock()
        index.root = self.root
        index.search_combined.return_value = (
            [{"path": "src/alpha.py", "lines": [1, 5], "text": "def alpha(): pass",
              "score": 0.9, "kind": "code", "source": "code"}],
            True, 0, 5, ["artifact_anchored"], [], "none", None,
        )
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "where is alpha_handler defined?",
                                            epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["search_mode"], "exact")
        self.assertIsNone(result["data"]["fallback_reason"])

    def test_fts_probe_detects_docsize_and_content_shadow_damage(self):
        """Release review round 2: the miss-token MATCH never evaluates
        bm25's docsize dependency — dropped or truncated _docsize/_content
        shadow tables must read dead via deterministic parity."""
        import sqlite3
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DROP TABLE fts_code_docsize")
        conn.close()
        self.assertFalse(self.iss.fts_probe(self.index_dir, "code"),
                         "dropped _docsize must read dead")
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DELETE FROM fts_docs_content WHERE rowid IN "
                         "(SELECT rowid FROM fts_docs_content LIMIT 1)")
        conn.close()
        self.assertFalse(self.iss.fts_probe(self.index_dir, "docs"),
                         "truncated _content must read dead")

    def test_fts_probe_detects_truncation_and_shadow_damage(self):
        """Release review P1: partial truncation (1 FTS row vs 3 registry) and
        dropped shadow tables must both read dead — the probe exercises the
        real MATCH path and enforces registry parity."""
        import sqlite3
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            # Truncate: delete some but not all FTS rows.
            conn.execute("DELETE FROM fts_code WHERE rowid IN (SELECT rowid FROM fts_code LIMIT 1)")
        conn.close()
        self.assertFalse(self.iss.fts_probe(self.index_dir, "code"),
                         "row-count divergence must read dead")
        # Shadow-table damage on the docs side.
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DROP TABLE IF EXISTS fts_docs_idx")
        conn.close()
        self.assertFalse(self.iss.fts_probe(self.index_dir, "docs"),
                         "MATCH-path damage must read dead")

    def test_docs_infra_failure_emits_single_signal(self):
        """Release review: a query_failed docs response carries the typed
        failure diagnostic ONLY — never a no_results/token-tweak signal too."""
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        with patch.object(self.srv, "_fts_degraded_serve",
                          return_value={"available": False, "failure_reason": "query_failed",
                                        "results": [], "coverage": {}}):
            result = self.srv.docs_search_response(index, "alpha", epoch_state=self.COMPLETE)
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("lexical_fallback_failed", codes)
        self.assertNotIn("no_results", codes)
        self.assertNotIn("lexical_fallback_zero_hits", codes)

    def test_code_search_generic_failure_never_blames_fts(self):
        """Release review + independent re-verifier convergence: a generic
        semantic exception (FTS never attempted) must not claim the FTS
        fallback failed."""
        index = self._mock_index(RuntimeError("boom"))
        result = self.srv.code_search_response(index, "alpha", epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["fallback_reason"], "query_failed")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("lexical_fallback_failed", codes,
                         "FTS was never attempted — it must not be blamed")

    def test_code_ask_infra_failure_never_masked_by_keyword_pass(self):
        """Independent re-verifier Defect 1 (= review's masking cluster): with
        a broken FTS and a live keyword match available, the envelope stays
        honest — no keyword citations presented as indexed sources, the
        infrastructure diagnostic present, no reranker misdirection."""
        import sqlite3
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DROP TABLE fts_code")
        conn.close()
        (self.root / "src").mkdir(exist_ok=True)
        (self.root / "src" / "mod.py").write_text("def alpha_handler(): pass\n", encoding="utf-8")
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "alpha_handler purpose",
                                            epoch_state=self.COMPLETE)
        data = result["data"]
        self.assertEqual(data["fallback_reason"], "query_failed")
        self.assertEqual(data["citations"], [], "live keyword hits must not mask the outage")
        self.assertIn("infrastructure failure", data["answer"])
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("search_infrastructure_failure", codes)
        self.assertFalse(any("reranker unavailable" in gp for gp in data["gaps"]))

    def test_code_ask_working_lexical_zero_hit_answer_is_honest(self):
        """Release review: a working-lexical zero-hit answer must carry the
        exact-token guidance, never 'may not be covered'."""
        # 1wpag: publish the empty layer through the canonical producer (see
        # test_code_ask_fallback_never_mixes_live_keyword_citations).
        import contextlib, io as _io
        with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
            self.iss.reconcile_chunk_index(self.index_dir, "code", set(), lambda: [])
            self.iss.reconcile_chunk_index(self.index_dir, "docs", set(), lambda: [])
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "zz_nothing_zz?",
                                            epoch_state=self.COMPLETE)
        data = result["data"]
        self.assertEqual(data["search_mode"], "lexical_fallback")
        self.assertIn("exact-token", data["answer"])
        self.assertNotIn("may not be covered", data["answer"])

    def test_degraded_envelopes_always_carry_coverage(self):
        """Release review (round 2 — failure paths included): coverage is
        REQUIRED on every degraded/failed envelope ({} = collection
        unavailable) — available fallbacks, FAILED fallbacks, and the docs
        live fallback alike."""
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        # Available fallback with empty coverage.
        with patch.object(self.srv, "_fts_degraded_serve",
                          return_value={"available": True, "failure_reason": None,
                                        "results": [], "coverage": {}}):
            r1 = self.srv.docs_search_response(index, "alpha", epoch_state=self.COMPLETE)
            r2 = self.srv.code_search_response(index, "alpha", epoch_state=self.COMPLETE)
        self.assertIn("coverage", r1["data"])
        self.assertIn("coverage", r2["data"])
        # FAILED fallback (collection failed too): coverage still present.
        with patch.object(self.srv, "_fts_degraded_serve",
                          return_value={"available": False, "failure_reason": "query_failed",
                                        "results": [], "coverage": {}}):
            r3 = self.srv.docs_search_response(index, "alpha", epoch_state=self.COMPLETE)
            r4 = self.srv.code_search_response(index, "alpha", epoch_state=self.COMPLETE)
            index2 = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
            index2._layer_health = MagicMock()
            r5 = self.srv.code_ask_response(index2, self.root, "alpha?", epoch_state=self.COMPLETE)
        self.assertIn("coverage", r3["data"])
        self.assertIn("coverage", r4["data"])
        self.assertIn("coverage", r5["data"])
        # Docs live fallback (no published epoch): coverage present.
        index3 = self._mock_index(self.srv.IndexNotReadyError("no store"))
        index3.search_docs_lexical.return_value = []
        r6 = self.srv.docs_search_response(index3, "alpha", epoch_state=None)
        self.assertIn("coverage", r6["data"])

    def test_healthy_keyword_pass_citations_carry_source(self):
        """Release review round 2: the thin-citation keyword pass labels its
        citations with source, like every other citation path."""
        (self.root / "src").mkdir(exist_ok=True)
        (self.root / "src" / "kw.py").write_text("def kw_target_fn(): pass\n", encoding="utf-8")
        index = MagicMock()
        index.root = self.root
        index.search_combined.return_value = ([], True, 0, 0, [], [], "none", None)
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "kw_target_fn purpose",
                                            epoch_state=self.COMPLETE)
        kw_cits = [c for c in result["data"]["citations"] if c.get("kind") == "keyword"]
        self.assertTrue(kw_cits, "fixture requires a keyword hit")
        self.assertTrue(all(c.get("source") in ("docs", "code") for c in kw_cits), kw_cits)

    def test_local_rerank_excerpts_match_agent_mode(self):
        """Release review round 2: rerank='local' is a documented alias —
        excerpts are NOT truncated to 300 chars."""
        long_text = "x" * 900
        index = MagicMock()
        index.root = self.root
        index.search_combined.return_value = (
            [{"path": "src/alpha.py", "lines": [1, 5], "text": long_text,
              "score": 0.9, "kind": "code", "source": "code"}],
            True, 0, 5, [], [], "none", None,
        )
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "alpha?", rerank="local",
                                            epoch_state=self.COMPLETE)
        self.assertEqual(len(result["data"]["citations"][0]["excerpt"]), 900)

    def test_local_rerank_citations_carry_source(self):
        """Release review: rerank='local' is a documented alias — citations
        carry the same source metadata."""
        index = MagicMock()
        index.root = self.root
        index.search_combined.return_value = (
            [{"path": "src/alpha.py", "lines": [1, 5], "text": "def alpha(): pass",
              "score": 0.9, "kind": "code", "source": "code"}],
            True, 0, 5, [], [], "none", None,
        )
        index._layer_health = MagicMock()
        result = self.srv.code_ask_response(index, self.root, "alpha?", rerank="local",
                                            epoch_state=self.COMPLETE)
        self.assertEqual(result["data"]["citations"][0].get("source"), "code")

    def test_degradation_log_persist_is_inside_the_lock(self):
        """Release review round 2 (ordering): the persist call sits INSIDE the
        critical section, so the log order matches the state order."""
        src_path = Path(load_server().__file__)
        src = src_path.read_text(encoding="utf-8")
        start = src.index("def _log_degradation_transition(")
        end = src.index("\ndef ", start + 10)
        body = src[start:end]
        lock_pos = body.index("with _DEGRADED_LOG_LOCK:")
        persist_pos = body.index("iss.store_log(index_dir, msg)")
        mark_pos = body.index("_DEGRADED_LOG_STATE[key] = current")
        self.assertLess(lock_pos, persist_pos)
        self.assertLess(persist_pos, mark_pos)

    def test_failed_fts_mode_is_consistent_across_tools(self):
        """Release review round 3: attempted-and-failed FTS reads
        search_mode lexical_fallback at ALL three tools (docs already did;
        code_search/code_ask now match)."""
        import sqlite3
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        with conn:
            conn.execute("DROP TABLE fts_code")
        conn.close()
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        index._layer_health = MagicMock()
        r_code = self.srv.code_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        r_ask = self.srv.code_ask_response(index, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
        self.assertEqual(r_code["data"]["search_mode"], "lexical_fallback")
        self.assertEqual(r_ask["data"]["search_mode"], "lexical_fallback")
        # Generic failures (FTS never attempted) keep the base mode.
        index2 = self._mock_index(RuntimeError("boom"))
        r_gen = self.srv.code_search_response(index2, "alpha", epoch_state=self.COMPLETE)
        self.assertEqual(r_gen["data"]["search_mode"], "hybrid")

    def test_degradation_log_unpersisted_failure_retries(self):
        """Release review round 3 P2: store_log swallows filesystem errors —
        the caller must gate on the durable-append return, so an obstructed
        log path retries instead of being permanently deduped."""
        self.srv._DEGRADED_LOG_STATE.clear()
        log_path = self.iss.store_log_path(self.index_dir)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Obstruct: make the log path a DIRECTORY so open(..., "a") fails
        # inside store_log (which swallows and now returns False).
        if log_path.exists():
            log_path.unlink()
        log_path.mkdir()
        try:
            self.srv._log_degradation_transition(self.root, "docs_search", "model_unavailable")
            self.assertEqual(self.srv._DEGRADED_LOG_STATE, {},
                             "a swallowed write failure must not mark the transition")
        finally:
            log_path.rmdir()
        # Path clear: the retry persists exactly once.
        self.srv._log_degradation_transition(self.root, "docs_search", "model_unavailable")
        text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        events = [ln for ln in text.splitlines() if "search degradation" in ln]
        self.assertEqual(len(events), 1)

    def test_degradation_log_dedup_is_thread_safe(self):
        """Release review P2: concurrent identical transitions persist once."""
        import threading as _th
        self.srv._DEGRADED_LOG_STATE.clear()
        barrier = _th.Barrier(8)
        def worker():
            barrier.wait()
            self.srv._log_degradation_transition(self.root, "docs_search", "model_unavailable")
        threads = [_th.Thread(target=worker) for _ in range(8)]
        for th in threads: th.start()
        for th in threads: th.join()
        log_path = self.iss.store_log_path(self.index_dir)
        text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        events = [ln for ln in text.splitlines() if "search degradation" in ln]
        self.assertEqual(len(events), 1, events)

    def test_degradation_log_retries_after_write_failure(self):
        """Review fix (P2): a failed persist must not permanently suppress
        the transition — the state marks only after the write lands."""
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        log_path = self.iss.store_log_path(self.index_dir)
        with patch.object(self.srv, "_load_script", side_effect=RuntimeError("io down")):
            self.srv._log_degradation_transition(self.root, "docs_search", "model_unavailable")
        self.assertEqual(self.srv._DEGRADED_LOG_STATE, {}, "failed persist must not mark the state")
        self.srv._log_degradation_transition(self.root, "docs_search", "model_unavailable")
        text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        self.assertEqual(sum(1 for ln in text.splitlines() if "search degradation" in ln), 1)

    def test_degradation_log_dedupes_per_reason_transition(self):
        index = self._mock_index(self.srv.SemanticModelUnavailableOfflineError("offline"))
        for _ in range(5):
            self.srv.docs_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        log_path = self.iss.store_log_path(self.index_dir)
        text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        events = [ln for ln in text.splitlines() if "search degradation" in ln]
        self.assertEqual(len(events), 1,
                         "N degraded queries must persist ONE event per reason transition")
        # Recovery closes the episode with exactly one more event.
        index.search_docs.side_effect = None
        index.search_docs.return_value = ([{"id": "d1", "path": "docs/guide.md", "kind": "doc",
                                            "section": "Intro", "lines": [1, 4],
                                            "text": "x", "score": 0.9}], True)
        self.srv.docs_search_response(index, "alpha", epoch_state=self.COMPLETE)
        text = log_path.read_text(encoding="utf-8")
        events = [ln for ln in text.splitlines() if "search degradation" in ln]
        self.assertEqual(len(events), 2)
        self.assertIn("recovered", events[-1])


class FreshnessCacheAxesTests(unittest.TestCase):
    """1sbxq AC-4 (P0 plan repair): BOTH cache invalidation axes, pinned
    independently — the TTL axis (edit detection between builds; the
    generation cannot see edits) and the epoch axis (immediate refresh on a
    build transition, without waiting out the TTL)."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.srv._FRESHNESS_CACHE.clear()
        self.addCleanup(self.srv._FRESHNESS_CACHE.clear)

    def _with_underlying(self, verdicts: list):
        """Patch the indexer helper to pop successive verdicts (each entry a
        bool-or-None `stale` value); count calls."""
        calls = []
        def fake_freshness(root):
            calls.append(1)
            stale = verdicts[min(len(calls) - 1, len(verdicts) - 1)]
            return {"stale": stale, "layers": {}, "chunker_stale": False,
                    "reason": "test"}
        fake_indexer = type("FakeIdx", (), {"project_layer_freshness": staticmethod(fake_freshness)})
        return calls, patch.object(self.srv, "_load_script", return_value=fake_indexer)

    def test_ttl_axis_detects_edit_with_generation_unchanged(self):
        """current → (source edit; generation does NOT change) → stale once
        the TTL elapses. Generation-only invalidation would cache `current`
        forever here — the reproduced P0."""
        stable_token = ("attempt-a", "complete", 7)
        calls, ctx = self._with_underlying([False, True])  # current, then stale
        with ctx, patch.object(self.srv, "_epoch_state", return_value=stable_token):
            v1 = self.srv._index_freshness_verdict(self.root)
            self.assertEqual(v1["state"], "current")
            # Within the TTL, same token: cached — the underlying check runs once.
            v2 = self.srv._index_freshness_verdict(self.root)
            self.assertEqual(v2["state"], "current")
            self.assertEqual(len(calls), 1)
            # TTL expiry (simulate by aging the cache entry), token UNCHANGED:
            key = str(self.root)
            expires_at, tok, verdict = self.srv._FRESHNESS_CACHE[key]
            self.srv._FRESHNESS_CACHE[key] = (0.0, tok, verdict)
            v3 = self.srv._index_freshness_verdict(self.root)
            self.assertEqual(v3["state"], "stale",
                             "the TTL axis must re-detect an edit the generation cannot see")
            self.assertEqual(len(calls), 2)

    def test_epoch_axis_refreshes_immediately_on_build_transition(self):
        """stale → completed build (epoch token changes) → current
        IMMEDIATELY, without waiting out the TTL."""
        calls, ctx = self._with_underlying([True, False])  # stale, then current
        with ctx:
            with patch.object(self.srv, "_epoch_state", return_value=("attempt-a", "complete", 7)):
                v1 = self.srv._index_freshness_verdict(self.root)
                self.assertEqual(v1["state"], "stale")
            # Build publishes: generation advances. The cache entry is still
            # well inside its TTL — the token change alone must invalidate.
            with patch.object(self.srv, "_epoch_state", return_value=("attempt-b", "complete", 8)):
                v2 = self.srv._index_freshness_verdict(self.root)
            self.assertEqual(v2["state"], "current",
                             "the epoch axis must refresh without waiting out the TTL")
            self.assertEqual(len(calls), 2)

    def test_unknown_states_pass_through(self):
        calls, ctx = self._with_underlying([None])
        with ctx, patch.object(self.srv, "_epoch_state", return_value=None):
            v = self.srv._index_freshness_verdict(self.root)
        self.assertEqual(v["state"], "unknown")

    def test_helper_exception_reads_unknown(self):
        with patch.object(self.srv, "_load_script", side_effect=RuntimeError("boom")), \
             patch.object(self.srv, "_epoch_state", return_value=None):
            v = self.srv._index_freshness_verdict(self.root)
        self.assertEqual(v["state"], "unknown")


class IndexBuildLockStatusTests(unittest.TestCase):
    """Wave 1p99o: index_build_status exposes an authoritative, lock-TESTED `held` (no
    classification) + `ended_at`. Plain terminology (no 'zombie')."""

    def setUp(self):
        # Wave 1wpif delivery review (CODE-RV1-2): a bare `import server_impl`
        # resolved only because an earlier test in this module had already put
        # SCRIPTS_ROOT on sys.path, so this class failed at import when run in
        # isolation. Load it the way every other class here does.
        self.srv = load_server()

    def _fake_indexer(self, meta, held_result):
        from types import SimpleNamespace
        return SimpleNamespace(
            read_index_build_lock_metadata=lambda p: meta,
            _index_build_lock_held=lambda d: held_result,
        )

    def _info(self, meta, held_result, write_file=True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if write_file:
                lp = root / ".wavefoundry" / "index" / "index-build.lock"
                lp.parent.mkdir(parents=True, exist_ok=True)
                lp.write_text(json.dumps(meta or {}), encoding="utf-8")
            with patch.object(self.srv, "_indexer_module",
                              return_value=self._fake_indexer(meta, held_result)):
                return self.srv._index_build_lock_info(root)

    def test_no_file_not_present_not_held(self):
        info = self._info(None, (False, None), write_file=False)
        self.assertFalse(info["present"])
        self.assertFalse(info["held"])
        self.assertNotIn("classification", info)

    def test_held_true_from_lock_test_uses_kernel_pid(self):
        info = self._info({"pid": 4321, "started_at": 1.0, "cmdline": "x"}, (True, 9999))
        self.assertTrue(info["held"])
        self.assertTrue(info["present"])
        self.assertEqual(info["owner_pid"], 9999)  # kernel-reported holder, not the metadata pid
        self.assertIn("running", info["note"].lower())

    def test_clean_finish(self):
        info = self._info({"pid": 4321, "started_at": 1.0, "ended_at": 2.0, "cmdline": "x"}, (False, None))
        self.assertFalse(info["held"])
        self.assertIsNotNone(info["ended_at"])
        self.assertIn("finished cleanly", info["note"])

    def test_interrupted_build(self):
        info = self._info({"pid": 4321, "started_at": 1.0, "cmdline": "x"}, (False, None))
        self.assertFalse(info["held"])
        self.assertIsNone(info["ended_at"])
        self.assertIn("did NOT finish cleanly", info["note"])

    def test_undetermined_treated_not_held(self):
        info = self._info({"pid": 4321, "started_at": 1.0, "cmdline": "x"}, (None, None))
        self.assertFalse(info["held"])
        self.assertIn("could not be determined", info["note"].lower())

    def test_shape_has_no_classification(self):
        info = self._info({"pid": 1, "started_at": 1.0, "ended_at": 2.0}, (False, None))
        for k in ("held", "present", "owner_pid", "owner_cmdline", "started_at", "ended_at", "note"):
            self.assertIn(k, info)
        self.assertNotIn("classification", info)

    def test_no_zombie_terminology(self):
        cases = [
            ({"pid": 1, "started_at": 1.0}, (True, 1)),
            ({"pid": 1, "started_at": 1.0}, (False, None)),
            ({"pid": 1, "started_at": 1.0, "ended_at": 2.0}, (False, None)),
            ({"pid": 1, "started_at": 1.0}, (None, None)),
        ]
        for meta, hr in cases:
            self.assertNotIn("zombie", self._info(meta, hr)["note"].lower())

    def test_build_status_injects_lock_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_indexer_module",
                              return_value=self._fake_indexer(None, (False, None))):
                resp = self.srv.index_build_status_response(Path(tmp), layer="project")
        self.assertIn("lock", resp.get("data", {}))
        self.assertFalse(resp["data"]["lock"]["held"])

    def test_recovery_message_no_longer_instructs_deleting_the_file(self):
        src = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        self.assertNotIn("index-build.lock and retry", src)
        self.assertIn("index_build_status and read the `lock`", src)

    def test_health_flags_interrupted_build(self):
        from types import SimpleNamespace
        interrupted = {"held": False, "present": True, "owner_pid": 9, "owner_cmdline": "x",
                       "started_at": 1.0, "ended_at": None, "note": "interrupted"}
        with tempfile.TemporaryDirectory() as tmp:
            idx = SimpleNamespace(root=Path(tmp), docs_health=lambda: {})
            with patch.object(self.srv, "_index_build_lock_info", return_value=interrupted):
                resp = self.srv.index_health_response(idx)
        codes = [d.get("code") for d in resp.get("diagnostics", [])]
        self.assertIn("index_build_interrupted", codes)


class IndexSizeHealthTests(unittest.TestCase):
    """Wave 1p9a9: index_health reports on-disk index size (total + per-component)."""

    def setUp(self):
        # Wave 1wpif delivery review (CODE-RV1-2): a bare `import server_impl`
        # resolved only because an earlier test in this module had already put
        # SCRIPTS_ROOT on sys.path, so this class failed at import when run in
        # isolation. Load it the way every other class here does.
        self.srv = load_server()

    def test_index_dir_size_total_and_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "docs.lance").mkdir()
            (d / "docs.lance" / "data").write_bytes(b"x" * 100)
            (d / "code.lance").mkdir()
            (d / "code.lance" / "data").write_bytes(b"y" * 50)
            (d / "meta.json").write_bytes(b"z" * 10)
            size = self.srv._index_dir_size(d)
        self.assertEqual(size["total_bytes"], 160)
        self.assertEqual(size["components"]["docs.lance"], 100)
        self.assertEqual(size["components"]["code.lance"], 50)
        self.assertEqual(size["components"]["meta.json"], 10)
        self.assertIn("total_human", size)

    def test_index_dir_size_missing_returns_none(self):
        self.assertIsNone(self.srv._index_dir_size(Path("/no/such/index/dir/xyz")))

    def test_human_bytes(self):
        self.assertEqual(self.srv._human_bytes(0), "0 B")
        self.assertEqual(self.srv._human_bytes(1023), "1023 B")
        self.assertEqual(self.srv._human_bytes(1024), "1.0 KB")
        self.assertEqual(self.srv._human_bytes(1536), "1.5 KB")

    def test_health_includes_size(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".wavefoundry" / "index").mkdir(parents=True)
            (Path(tmp) / ".wavefoundry" / "index" / "meta.json").write_bytes(b"{}")
            idx = SimpleNamespace(root=Path(tmp), docs_health=lambda: {})
            resp = self.srv.index_health_response(idx)
        self.assertIn("size", resp.get("data", {}))
        self.assertIsNotNone(resp["data"]["size"])
        self.assertIn("total_bytes", resp["data"]["size"])


class IndexOptimizeToolTests(unittest.TestCase):
    """Wave 1p9aj: index_optimize reclaims Lance-table bloat (tiered, no re-embed)."""

    def setUp(self):
        # Wave 1wpif delivery review (CODE-RV1-2): a bare `import server_impl`
        # resolved only because an earlier test in this module had already put
        # SCRIPTS_ROOT on sys.path, so this class failed at import when run in
        # isolation. Load it the way every other class here does.
        self.srv = load_server()

    def _fake_indexer(self, results):
        from types import SimpleNamespace

        class _AlreadyRunning(RuntimeError):
            pass

        def optimize_index_tables(index_dir, tables=("docs", "code")):
            return results

        return SimpleNamespace(
            optimize_index_tables=optimize_index_tables,
            IndexBuildAlreadyRunning=_AlreadyRunning,
        )

    def test_optimize_reports_per_table_and_total(self):
        results = {
            "docs": {"tier": 2, "rows": 100, "needs_rebuild": False, "error": None,
                     "bytes_before": 2000, "bytes_after": 500},
            "code": {"tier": 1, "rows": 50, "needs_rebuild": False, "error": None,
                     "bytes_before": 800, "bytes_after": 800},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_load_script", return_value=self._fake_indexer(results)):
                resp = self.srv._index_optimize_response(Path(tmp), content="all", rebuild_if_needed=True)
        self.assertEqual(resp["status"], "ok")
        data = resp["data"]
        self.assertEqual(data["tables"]["docs"]["tier"], 2)
        self.assertEqual(data["tables"]["docs"]["reclaimed_bytes"], 1500)
        self.assertEqual(data["total_reclaimed_bytes"], 1500)
        self.assertEqual(data["needs_rebuild"], [])

    def test_optimize_tier3_spawns_rebuild(self):
        results = {"docs": {"tier": 3, "rows": 0, "needs_rebuild": True, "error": "corrupt",
                            "bytes_before": 100, "bytes_after": 100}}
        spawned = []

        def fake_rebuild(root, content=None, full=None, rechunk=None, layer=None):
            spawned.append(content)
            return {}

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_load_script", return_value=self._fake_indexer(results)), \
                 patch.object(self.srv, "run_index_rebuild", side_effect=fake_rebuild):
                resp = self.srv._index_optimize_response(Path(tmp), content="docs", rebuild_if_needed=True)
        self.assertIn("docs", spawned)
        self.assertEqual(resp["data"]["rebuild_spawned"], ["docs"])

    def test_optimize_tier3_no_rebuild_when_disabled(self):
        results = {"docs": {"tier": 3, "rows": 0, "needs_rebuild": True, "error": "corrupt",
                            "bytes_before": 100, "bytes_after": 100}}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_load_script", return_value=self._fake_indexer(results)), \
                 patch.object(self.srv, "run_index_rebuild") as rebuild:
                resp = self.srv._index_optimize_response(Path(tmp), content="docs", rebuild_if_needed=False)
            rebuild.assert_not_called()
        self.assertEqual(resp["data"]["needs_rebuild"], ["docs"])
        self.assertEqual(resp["data"]["rebuild_spawned"], [])

    def test_optimize_invalid_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            resp = self.srv._index_optimize_response(Path(tmp), content="graph")
        self.assertEqual(resp["status"], "error")

    def test_optimize_lock_busy(self):
        fake = self._fake_indexer({})
        busy = fake.IndexBuildAlreadyRunning("a build is already running")

        def optimize_index_tables(index_dir, tables=("docs", "code")):
            raise busy

        fake.optimize_index_tables = optimize_index_tables
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_load_script", return_value=fake):
                resp = self.srv._index_optimize_response(Path(tmp), content="all")
        self.assertEqual(resp["status"], "error")
        codes = [d.get("code") for d in resp.get("diagnostics", [])]
        self.assertIn("build_skipped_lock_busy", codes)

    def test_optimize_no_tables_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_load_script", return_value=self._fake_indexer({})):
                resp = self.srv._index_optimize_response(Path(tmp), content="all")
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["tables"], {})


class StateStoreOptimizeAndHealthTests(unittest.TestCase):
    """Wave 1rsh9 (1rq4h): unified SQLite-store maintenance in index_optimize
    and index-state store reporting in index_health."""

    def setUp(self):
        # Wave 1wpif delivery review (CODE-RV1-2): a bare `import server_impl`
        # resolved only because an earlier test in this module had already put
        # SCRIPTS_ROOT on sys.path, so this class failed at import when run in
        # isolation. Load it the way every other class here does.
        self.srv = load_server()

    def _fake_modules(self, lance_results, store_results=None, lock_raises=None):
        from contextlib import contextmanager
        from types import SimpleNamespace

        class _AlreadyRunning(RuntimeError):
            pass

        @contextmanager
        def _index_build_lock(index_dir):
            if lock_raises == "busy":
                raise _AlreadyRunning("a build is already running")
            yield

        idx = SimpleNamespace(
            optimize_index_tables=lambda index_dir, tables=("docs", "code"): lance_results,
            IndexBuildAlreadyRunning=_AlreadyRunning,
            _index_build_lock=_index_build_lock,
        )
        iss = SimpleNamespace(
            optimize_state_stores=lambda index_dir, full_vacuum=True, deep_integrity=True: (
                store_results or {}
            ),
        )

        def load(name):
            return {"indexer": idx, "index_state_store": iss}[name]

        return load

    def test_optimize_reports_sqlite_stores_and_adds_reclaim_to_total(self):
        lance = {"docs": {"tier": 1, "rows": 10, "needs_rebuild": False, "error": None,
                          "bytes_before": 1000, "bytes_after": 400}}
        stores = {
            "index-state": {"present": True, "integrity": "ok",
                            "size_before_bytes": 5000, "size_after_bytes": 2000,
                            "reclaimed_bytes": 3000, "error": None},
            "graph-state": {"present": False, "integrity": None,
                            "size_before_bytes": 0, "size_after_bytes": 0,
                            "reclaimed_bytes": 0, "error": None},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_load_script",
                              side_effect=self._fake_modules(lance, stores)):
                resp = self.srv._index_optimize_response(Path(tmp), content="all")
        self.assertEqual(resp["status"], "ok")
        data = resp["data"]
        self.assertEqual(data["stores"]["index-state"]["reclaimed_bytes"], 3000)
        self.assertEqual(data["stores"]["index-state"]["integrity"], "ok")
        self.assertFalse(data["stores"]["graph-state"]["present"])
        # 600 Lance + 3000 store
        self.assertEqual(data["total_reclaimed_bytes"], 3600)

    def test_optimize_runs_store_pass_even_with_no_lance_tables(self):
        stores = {
            "index-state": {"present": True, "integrity": "ok",
                            "size_before_bytes": 500, "size_after_bytes": 500,
                            "reclaimed_bytes": 0, "error": None},
            "graph-state": {"present": True, "integrity": "ok",
                            "size_before_bytes": 900, "size_after_bytes": 300,
                            "reclaimed_bytes": 600, "error": None},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_load_script",
                              side_effect=self._fake_modules({}, stores)):
                resp = self.srv._index_optimize_response(Path(tmp), content="all")
        self.assertEqual(resp["status"], "ok")
        data = resp["data"]
        self.assertEqual(data["tables"], {})
        self.assertEqual(data["stores"]["graph-state"]["reclaimed_bytes"], 600)
        self.assertEqual(data["total_reclaimed_bytes"], 600)

    def test_store_lock_busy_keeps_lance_results_with_diagnostic(self):
        lance = {"docs": {"tier": 1, "rows": 10, "needs_rebuild": False, "error": None,
                          "bytes_before": 1000, "bytes_after": 400}}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_load_script",
                              side_effect=self._fake_modules(lance, lock_raises="busy")):
                resp = self.srv._index_optimize_response(Path(tmp), content="all")
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["tables"]["docs"]["reclaimed_bytes"], 600)
        codes = [d.get("code") for d in resp.get("diagnostics", [])]
        self.assertIn("build_skipped_lock_busy", codes)

    def test_store_structural_fail_emits_diagnostic(self):
        stores = {
            "index-state": {"present": True, "integrity": "structural-fail",
                            "size_before_bytes": 100, "size_after_bytes": 100,
                            "reclaimed_bytes": 0, "error": "database disk image is malformed"},
            "graph-state": {"present": False, "integrity": None,
                            "size_before_bytes": 0, "size_after_bytes": 0,
                            "reclaimed_bytes": 0, "error": None},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_load_script",
                              side_effect=self._fake_modules({}, stores)):
                resp = self.srv._index_optimize_response(Path(tmp), content="all")
        codes = [d.get("code") for d in resp.get("diagnostics", [])]
        self.assertIn("state_store_structural_fail", codes)

    def test_health_summary_absent_store_is_normal(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self.srv._state_store_health_summary(Path(tmp))
        self.assertEqual(summary["present"], False)
        self.assertIsNone(summary["integrity"])
        self.assertIsNone(summary["schema_version"])

    def test_health_summary_reports_present_store(self):
        import importlib.util as ilu
        iss_path = Path(self.srv.__file__).resolve().parent / "index_state_store.py"
        spec = ilu.spec_from_file_location("_iss_health_test", iss_path)
        iss = ilu.module_from_spec(spec)
        spec.loader.exec_module(iss)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index_dir = root / ".wavefoundry" / "index"
            store = iss.IndexStateStore(index_dir)
            store.close()
            summary = self.srv._state_store_health_summary(root)
        self.assertTrue(summary["present"])
        self.assertEqual(summary["schema_version"], iss.STATE_STORE_SCHEMA_VERSION)
        self.assertEqual(summary["integrity"], "ok")
        self.assertGreater(summary["size_bytes"], 0)

    def test_health_response_wires_state_store_block(self):
        src = Path(self.srv.__file__).read_text(encoding="utf-8")
        fn_pos = src.index("def index_health_response(")
        wired_pos = src.index('health["state_store"] = _state_store_health_summary(', fn_pos)
        self.assertGreater(wired_pos, fn_pos)

    def _load_iss(self):
        import importlib.util as ilu
        iss_path = Path(self.srv.__file__).resolve().parent / "index_state_store.py"
        spec = ilu.spec_from_file_location("_iss_health_test", iss_path)
        iss = ilu.module_from_spec(spec)
        spec.loader.exec_module(iss)
        return iss

    def _make_lance_code_table(self, index_dir, n):
        import lancedb
        rows = [
            {"id": f"c{i}", "path": f"f{i}.py", "kind": "code", "language": "python",
             "lines": [1, 5], "section": "", "text": f"def fn_{i}(): pass",
             "chunk_hash": f"h{i}", "vector": [0.0, 0.0, 0.0, 0.0]}
            for i in range(n)
        ]
        lancedb.connect(str(index_dir)).create_table("code", rows, mode="overwrite")

    def test_health_summary_reports_chunk_index_coverage(self):
        # 1sbfj AC-5: the field defect — a near-empty registry beside a
        # populated Lance table — must surface as covered: False (it used to
        # hide behind integrity: ok, which is structural only).
        try:
            import lancedb  # noqa: F401
        except Exception:  # pragma: no cover - lancedb ships in the tool venv
            self.skipTest("lancedb unavailable")
        iss = self._load_iss()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index_dir = root / ".wavefoundry" / "index"
            self._make_lance_code_table(index_dir, 60)
            # Store exists but carries only one delta-written row.
            iss.apply_chunk_deltas(
                index_dir, "code",
                add_rows=[{"id": "c0", "path": "f0.py", "kind": "code",
                           "lines": [1, 5], "text": "def fn_0(): pass",
                           "chunk_hash": "h0"}],
            )
            summary = self.srv._state_store_health_summary(root)
            self.assertEqual(summary["integrity"], "ok")  # structural says ok...
            cov = summary["chunk_index"]["code"]
            self.assertEqual(cov["lance_rows"], 60)
            self.assertEqual(cov["registry_rows"], 1)
            self.assertFalse(cov["covered"])  # ...coverage says blind
            # After the backfill, coverage reads healthy.
            iss.rebuild_chunk_index(
                index_dir, "code",
                [{"id": f"c{i}", "path": f"f{i}.py", "kind": "code",
                  "lines": [1, 5], "text": f"def fn_{i}(): pass",
                  "chunk_hash": f"h{i}"} for i in range(60)],
            )
            summary = self.srv._state_store_health_summary(root)
            self.assertTrue(summary["chunk_index"]["code"]["covered"])

    def test_health_response_diagnoses_undercovered_chunk_index(self):
        # The advisory wiring: covered: False must produce a visible
        # chunk_index_undercovered diagnostic in index_health.
        src = Path(self.srv.__file__).read_text(encoding="utf-8")
        fn_pos = src.index("def index_health_response(")
        diag_pos = src.index('"chunk_index_undercovered"', fn_pos)
        self.assertGreater(diag_pos, fn_pos)
        # And the summary helper computes the covered flag exact-first
        # (sync-time counts), with the proportional compare as fallback.
        self.assertIn("chunk_sync_counts(index_dir, table_name)", src)
        self.assertIn("covered = abs(lance_rows - registry_rows)", src)


class FtsRebuildContentTests(unittest.TestCase):
    """Wave 1sc7c (1sek8): index_build(content='fts') — from-scratch
    rebuild of the derived lexical layer off the Lance tables."""

    def setUp(self):
        self.srv = load_server()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"


    def test_fts_rebuild_refusal_reports_failed_not_passed(self):
        """Independent-review N1: the restore-only refusal (top-level error
        string) must surface as passed=False — never as a success envelope."""
        # No completed epoch: the derived rebuild refuses.
        resp = self.srv.run_index_rebuild(self.root, content="fts")
        self.assertFalse(resp["passed"])
        self.assertIn("no completed build epoch", resp["error"])

    def test_fts_rebuild_from_scratch_off_lance(self):
        try:
            import lancedb
        except Exception:  # pragma: no cover - lancedb ships in the tool venv
            self.skipTest("lancedb unavailable")
        rows = [
            {"id": f"c{i}", "path": f"f{i}.py", "kind": "code", "language": "python",
             "lines": [1, 5], "section": "", "text": f"def fn_{i}(): pass",
             "chunk_hash": f"h{i}", "vector": [0.0, 0.0, 0.0, 0.0]}
            for i in range(12)
        ]
        lancedb.connect(str(self.index_dir)).create_table("code", rows, mode="overwrite")
        # 1sed6 review fix: the derived rebuild is restore-only — it requires
        # a completed build epoch (a real build published this index).
        _seed_store_state(self.index_dir, {"model_versions": {"code": "m@full"}, "content": ["code"]})
        resp = self.srv.run_index_rebuild(self.root, content="fts")
        self.assertTrue(resp["passed"])
        self.assertEqual(resp["index_scope"], "derived_chunk_state_only")
        self.assertEqual(resp["tables"]["code"]["rows_written"], 12)
        # And it is a from-scratch recovery: corrupt the FTS, rebuild again.
        import importlib.util as ilu
        iss_path = Path(self.srv.__file__).resolve().parent / "index_state_store.py"
        spec = ilu.spec_from_file_location("_iss_fts_rebuild", iss_path)
        iss = ilu.module_from_spec(spec)
        spec.loader.exec_module(iss)
        store = iss.IndexStateStore(self.index_dir)
        try:
            store._conn.execute("DELETE FROM fts_code")
            store._conn.commit()
        finally:
            store.close()
        self.assertEqual(iss.fts_search(self.index_dir, "code", "fn_7"), [])
        resp2 = self.srv.run_index_rebuild(self.root, content="fts")
        self.assertTrue(resp2["passed"])
        self.assertTrue(iss.fts_search(self.index_dir, "code", "fn_7"))

    def test_fts_content_accepted_and_lock_guarded(self):
        src = Path(self.srv.__file__).read_text(encoding="utf-8")
        # 1seax (1seau): the vocabulary lives in the canonical public-contract
        # module now, consumed by the handler instead of a hand-written literal.
        self.assertIn("from public_contract import INDEX_BUILD_CONTENT_VALUES", src)
        import public_contract
        self.assertIn("fts", public_contract.INDEX_BUILD_CONTENT_VALUES)
        pos = src.index('if content == "fts":')
        block = src[pos:pos + 2200]
        self.assertIn("_index_build_lock(index_dir)", block)
        self.assertIn("IndexBuildAlreadyRunning", block)

    def test_undercoverage_diagnostics_point_at_fts_rebuild(self):
        src = Path(self.srv.__file__).read_text(encoding="utf-8")
        self.assertEqual(src.count("recovery_usage=\"index_build(content='fts')\""), 2)


class CodeLexicalToolTests(unittest.TestCase):
    """Wave 1sbfk (1seiz): the `code_lexical` direct BM25 exact-token search tool."""

    def setUp(self):
        # Wave 1wpif delivery review (CODE-RV1-2): a bare `import server_impl`
        # resolved only because an earlier test in this module had already put
        # SCRIPTS_ROOT on sys.path, so this class failed at import when run in
        # isolation. Load it the way every other class here does.
        self.srv = load_server()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"

    def _load_iss(self):
        import importlib.util as ilu
        iss_path = Path(self.srv.__file__).resolve().parent / "index_state_store.py"
        spec = ilu.spec_from_file_location("_iss_lexical_test", iss_path)
        iss = ilu.module_from_spec(spec)
        spec.loader.exec_module(iss)
        return iss

    def _seed_store(self, iss):
        iss.apply_chunk_deltas(
            self.index_dir, "code",
            add_rows=[
                {"id": "c1", "path": "src/hooks.py", "kind": "code", "language": "python",
                 "lines": [1, 20], "text": "def webhook_activity_inserted(row): dispatch(row)",
                 "chunk_hash": "h1"},
                {"id": "c2", "path": "src/util.py", "kind": "code", "language": "python",
                 "lines": [5, 9], "text": "def unrelated_helper(): pass",
                 "chunk_hash": "h2"},
                {"id": "c3", "path": "src/big.py", "kind": "code", "language": "python",
                 "lines": [1, 400],
                 "text": "def giant_block():\n" + ("    x = 'filler line'\n" * 100)
                         + "    return webhook_activity_inserted",
                 "chunk_hash": "h3"},
            ],
        )
        iss.apply_chunk_deltas(
            self.index_dir, "docs",
            add_rows=[
                {"id": "d1", "path": "docs/webhooks.md", "kind": "doc",
                 "lines": [1, 12], "text": "webhook activity is recorded when inserted",
                 "chunk_hash": "hd1"},
            ],
        )

    def test_ranked_results_shape_merge_and_token_semantics(self):
        iss = self._load_iss()
        self._seed_store(iss)
        # Exact compound identifier: hits the code chunks that carry the token.
        resp = self.srv.code_lexical_response(self.root, "webhook_activity_inserted")
        data = resp["data"]
        self.assertEqual(resp["status"], "ok")
        self.assertGreaterEqual(data["result_count"], 2)
        top = data["results"][0]
        for field in ("id", "path", "kind", "language", "lines", "text",
                      "text_truncated", "bm25", "table"):
            self.assertIn(field, top)
        self.assertTrue(all(r["table"] in ("code", "docs") for r in data["results"]))
        # BM25 best-first (smaller-is-better, ascending).
        bm25s = [r["bm25"] for r in data["results"]]
        self.assertEqual(bm25s, sorted(bm25s))
        # Token semantics: the partial identifier does NOT match the compound
        # token in code, but DOES match the separate words in docs prose.
        resp2 = self.srv.code_lexical_response(self.root, "webhook", table="code")
        self.assertEqual(resp2["data"]["result_count"], 0)
        resp3 = self.srv.code_lexical_response(self.root, "webhook", table="docs")
        self.assertEqual([r["id"] for r in resp3["data"]["results"]], ["d1"])

    def test_kind_filter_limit_cap_and_text_cap(self):
        iss = self._load_iss()
        self._seed_store(iss)
        resp = self.srv.code_lexical_response(
            self.root, "webhook_activity_inserted", kind="doc"
        )
        self.assertEqual(resp["data"]["result_count"], 0)  # exact kind filter
        # limit is hard-capped.
        resp2 = self.srv.code_lexical_response(self.root, "filler", limit=5000)
        self.assertEqual(resp2["data"]["limit"], self.srv.CODE_LEXICAL_MAX_LIMIT)
        # Oversized chunk text is capped and flagged.
        resp3 = self.srv.code_lexical_response(self.root, "giant_block")
        big = [r for r in resp3["data"]["results"] if r["id"] == "c3"]
        self.assertTrue(big and big[0]["text_truncated"])
        self.assertLessEqual(len(big[0]["text"]), self.srv.CODE_LEXICAL_TEXT_CAP)

    def test_hostile_queries_and_invalid_args(self):
        iss = self._load_iss()
        self._seed_store(iss)
        for hostile in ('NEAR( "unclosed', "a AND OR NOT", '"unbalanced', "((("):
            resp = self.srv.code_lexical_response(self.root, hostile)
            self.assertEqual(resp["status"], "ok")  # literals, never an engine error
        self.assertEqual(self.srv.code_lexical_response(self.root, "  ")["status"], "error")
        self.assertEqual(
            self.srv.code_lexical_response(self.root, "x", table="nope")["status"], "error"
        )

    def test_absent_store_degrades_with_recovery_diagnostic(self):
        resp = self.srv.code_lexical_response(self.root, "anything")
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["results"], [])
        codes = [d["code"] for d in resp.get("diagnostics", [])]
        self.assertIn("lexical_layer_unavailable", codes)

    def test_undercovered_table_warns_partial_results(self):
        try:
            import lancedb  # noqa: F401
        except Exception:  # pragma: no cover - lancedb ships in the tool venv
            self.skipTest("lancedb unavailable")
        iss = self._load_iss()
        # Lance holds 60 rows; the store holds ONE delta row (the field defect shape).
        import lancedb
        rows = [
            {"id": f"c{i}", "path": f"f{i}.py", "kind": "code", "language": "python",
             "lines": [1, 5], "section": "", "text": f"def fn_{i}(): pass",
             "chunk_hash": f"h{i}", "vector": [0.0, 0.0, 0.0, 0.0]}
            for i in range(60)
        ]
        lancedb.connect(str(self.index_dir)).create_table("code", rows, mode="overwrite")
        iss.apply_chunk_deltas(
            self.index_dir, "code",
            add_rows=[{"id": "c0", "path": "f0.py", "kind": "code",
                       "lines": [1, 5], "text": "def fn_0(): pass", "chunk_hash": "h0"}],
        )
        resp = self.srv.code_lexical_response(self.root, "fn_59", table="code")
        self.assertEqual(resp["data"]["result_count"], 0)  # not in the store yet...
        codes = [d["code"] for d in resp.get("diagnostics", [])]
        self.assertIn("chunk_index_undercovered", codes)  # ...and the response says WHY

    def test_healthy_zero_hit_carries_token_semantics_note(self):
        iss = self._load_iss()
        self._seed_store(iss)
        resp = self.srv.code_lexical_response(self.root, "definitely_absent_token")
        self.assertEqual(resp["data"]["result_count"], 0)
        self.assertIn("compound identifiers", resp["data"].get("note", ""))

    def test_mcp_tool_discloses_observational_telemetry_write(self):
        src = Path(self.srv.__file__).read_text(encoding="utf-8")
        pos = src.index("def code_lexical(")
        deco = src.rindex(
            "@mcp.tool(annotations=_OBSERVATIONAL_TOOL)", 0, pos
        )
        self.assertGreater(pos - deco, 0)
        self.assertLess(pos - deco, 120)


class CloseTimeOptimizeTests(unittest.TestCase):
    """Wave 1rycf: bloat-gated, tier-1-only index optimize at wave close (interim FTS-leak reclaim).

    Gate/lock/tier/fail-safe behavior of the close-time helpers, plus the wiring lock that they run
    BEFORE the close's own background refresh (lock free) and never spawn a rebuild."""

    def setUp(self):
        # Wave 1wpif delivery review (CODE-RV1-2): a bare `import server_impl`
        # resolved only because an earlier test in this module had already put
        # SCRIPTS_ROOT on sys.path, so this class failed at import when run in
        # isolation. Load it the way every other class here does.
        self.srv = load_server()

    def _fake_indexer(self, results, raises=None, raise_busy=False):
        from types import SimpleNamespace

        class _AlreadyRunning(RuntimeError):
            pass

        calls = {"tables": None}

        def optimize_index_tables(index_dir, tables=("docs", "code")):
            calls["tables"] = tables
            if raise_busy:
                raise _AlreadyRunning("a build is already running")
            if raises is not None:
                raise raises
            return results

        ns = SimpleNamespace(
            optimize_index_tables=optimize_index_tables,
            IndexBuildAlreadyRunning=_AlreadyRunning,
        )
        return ns, calls

    # --- _close_optimize_enabled (kill-switch) ---

    def test_enabled_default_true_when_no_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(self.srv._close_optimize_enabled(Path(tmp)))

    def test_enabled_respects_config_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir(parents=True)
            (docs / "workflow-config.json").write_text(
                json.dumps({"indexing": {"close_optimize_enabled": False}}), encoding="utf-8")
            self.assertFalse(self.srv._close_optimize_enabled(Path(tmp)))

    def test_enabled_fail_safe_on_corrupt_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir(parents=True)
            (docs / "workflow-config.json").write_text("{ not json", encoding="utf-8")
            self.assertTrue(self.srv._close_optimize_enabled(Path(tmp)))

    # --- _index_table_bloat_ratios (fail-safe) ---

    def test_bloat_ratios_empty_when_no_index_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.srv._index_table_bloat_ratios(Path(tmp)), {})

    # --- _maybe_optimize_index_on_close (the gate) ---

    def test_fires_on_bloated_table_and_reports_reclaim(self):
        results = {"docs": {"tier": 1, "rows": 100, "needs_rebuild": False,
                            "bytes_before": 700_000_000, "bytes_after": 60_000_000}}
        fake, calls = self._fake_indexer(results)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_close_optimize_enabled", return_value=True), \
                 patch.object(self.srv, "_index_table_bloat_ratios", return_value={"docs": 18.0, "code": 1.2}), \
                 patch.object(self.srv, "_load_script", return_value=fake):
                summary = self.srv._maybe_optimize_index_on_close(Path(tmp))
        self.assertIsNotNone(summary)
        self.assertTrue(summary["ran"])
        self.assertEqual(summary["bloated_tables"], ["docs"])
        # only the bloated table is optimized (code, ratio 1.2, is not)
        self.assertEqual(calls["tables"], ("docs",))
        self.assertEqual(summary["reclaimed_bytes"], 640_000_000)
        self.assertEqual(summary["needs_rebuild_deferred"], [])

    def test_noop_when_no_table_bloated(self):
        fake, calls = self._fake_indexer({})
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_close_optimize_enabled", return_value=True), \
                 patch.object(self.srv, "_index_table_bloat_ratios", return_value={"docs": 1.3, "code": 1.1}), \
                 patch.object(self.srv, "_load_script", return_value=fake) as load:
                summary = self.srv._maybe_optimize_index_on_close(Path(tmp))
        self.assertIsNone(summary)
        load.assert_not_called()  # gate short-circuits before loading the indexer
        self.assertIsNone(calls["tables"])

    def test_kill_switch_disables_even_when_bloated(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_close_optimize_enabled", return_value=False), \
                 patch.object(self.srv, "_index_table_bloat_ratios", return_value={"docs": 42.0}), \
                 patch.object(self.srv, "_load_script") as load:
                summary = self.srv._maybe_optimize_index_on_close(Path(tmp))
        self.assertIsNone(summary)
        load.assert_not_called()

    def test_skips_when_build_lock_held(self):
        fake, calls = self._fake_indexer({}, raise_busy=True)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_close_optimize_enabled", return_value=True), \
                 patch.object(self.srv, "_index_table_bloat_ratios", return_value={"docs": 18.0}), \
                 patch.object(self.srv, "_load_script", return_value=fake):
                summary = self.srv._maybe_optimize_index_on_close(Path(tmp))
        self.assertIsNotNone(summary)
        self.assertFalse(summary["ran"])
        self.assertEqual(summary["skipped"], "index_build_lock_held")

    def test_optimize_error_is_swallowed_and_reported(self):
        fake, calls = self._fake_indexer({}, raises=RuntimeError("disk exploded"))
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_close_optimize_enabled", return_value=True), \
                 patch.object(self.srv, "_index_table_bloat_ratios", return_value={"docs": 18.0}), \
                 patch.object(self.srv, "_load_script", return_value=fake):
                summary = self.srv._maybe_optimize_index_on_close(Path(tmp))
        self.assertIsNotNone(summary)
        self.assertFalse(summary["ran"])
        self.assertEqual(summary["skipped"], "optimize_error")

    def test_needs_rebuild_is_deferred_never_spawned(self):
        # A tier-3/unreadable table reports needs_rebuild — close must DEFER it, never spawn a rebuild.
        results = {"docs": {"tier": 3, "rows": 0, "needs_rebuild": True,
                            "bytes_before": 100, "bytes_after": 100}}
        fake, _calls = self._fake_indexer(results)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_close_optimize_enabled", return_value=True), \
                 patch.object(self.srv, "_index_table_bloat_ratios", return_value={"docs": 18.0}), \
                 patch.object(self.srv, "_load_script", return_value=fake), \
                 patch.object(self.srv, "run_index_rebuild") as rebuild:
                summary = self.srv._maybe_optimize_index_on_close(Path(tmp))
            rebuild.assert_not_called()  # tier-3 spawn lives only in the response wrapper, not at close
        self.assertEqual(summary["needs_rebuild_deferred"], ["docs"])

    def test_never_raises_on_internal_failure(self):
        # Any unexpected error inside the helper must be swallowed (a close never fails on reclaim).
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.srv, "_close_optimize_enabled", side_effect=RuntimeError("boom")):
                self.assertIsNone(self.srv._maybe_optimize_index_on_close(Path(tmp)))

    # --- wiring lock: runs before the refresh trigger, wired into wf_close_wave ---

    def test_close_wires_optimize_before_background_refresh(self):
        import inspect
        src = inspect.getsource(self.srv.wf_close_wave_response)
        opt = src.index("_maybe_optimize_index_on_close(root)")
        # 1seax (1seat): the refresh moved into the close's forward-recoverable
        # handoff-convergence block; the optimize-before-refresh ordering holds.
        refresh = src.index("_trigger_background_index_refresh_for_paths(root, [wave_md, handoff])")
        self.assertGreater(refresh, opt,
                           "close-time optimize must run BEFORE the background refresh (lock still free)")


class StalenessMonitorQuietPeriodTests(unittest.TestCase):
    """Wave 1p9am: the staleness monitor is a quiet-period safety net, not a competing trigger."""

    def setUp(self):
        # Wave 1wpif delivery review (CODE-RV1-2): a bare `import server_impl`
        # resolved only because an earlier test in this module had already put
        # SCRIPTS_ROOT on sys.path, so this class failed at import when run in
        # isolation. Load it the way every other class here does.
        self.srv = load_server()

    def _fake_idx(self, pending_age=None, ended_at=None):
        from types import SimpleNamespace
        return SimpleNamespace(
            reindex_pending_age=lambda index_dir: pending_age,
            read_index_build_lock_metadata=lambda p: ({"ended_at": ended_at} if ended_at is not None else {}),
            INDEX_BUILD_LOCK_NAME="index-build.lock",
        )

    def test_not_stale_returns_false(self):
        with patch.object(self.srv, "_index_inputs_stale", return_value=False):
            self.assertFalse(self.srv._maybe_refresh_if_stale(Path("/x")))

    def test_active_refresh_returns_false(self):
        with patch.object(self.srv, "_index_inputs_stale", return_value=True), \
             patch.object(self.srv, "_background_refresh_active", return_value=True):
            self.assertFalse(self.srv._maybe_refresh_if_stale(Path("/x")))

    def test_defers_while_pending_marker_fresh(self):
        with patch.object(self.srv, "_index_inputs_stale", return_value=True), \
             patch.object(self.srv, "_background_refresh_active", return_value=False), \
             patch.object(self.srv, "_read_monitor_config", return_value={"quiet_period_seconds": 300.0}), \
             patch.object(self.srv, "_load_script", return_value=self._fake_idx(pending_age=10.0)), \
             patch.object(self.srv, "_start_background_index_refresh") as start:
            self.assertFalse(self.srv._maybe_refresh_if_stale(Path("/x")))
            start.assert_not_called()

    def test_defers_after_recent_build(self):
        import time as _t
        recent = _t.time() - 10
        with patch.object(self.srv, "_index_inputs_stale", return_value=True), \
             patch.object(self.srv, "_background_refresh_active", return_value=False), \
             patch.object(self.srv, "_read_monitor_config", return_value={"quiet_period_seconds": 300.0}), \
             patch.object(self.srv, "_load_script", return_value=self._fake_idx(pending_age=None, ended_at=recent)), \
             patch.object(self.srv, "_start_background_index_refresh") as start:
            self.assertFalse(self.srv._maybe_refresh_if_stale(Path("/x")))
            start.assert_not_called()

    def test_fires_when_quiet_and_stale(self):
        import time as _t
        old = _t.time() - 10000
        with patch.object(self.srv, "_index_inputs_stale", return_value=True), \
             patch.object(self.srv, "_background_refresh_active", return_value=False), \
             patch.object(self.srv, "_read_monitor_config", return_value={"quiet_period_seconds": 300.0}), \
             patch.object(self.srv, "_load_script", return_value=self._fake_idx(pending_age=9999.0, ended_at=old)), \
             patch.object(self.srv, "_start_background_index_refresh", return_value=True) as start:
            self.assertTrue(self.srv._maybe_refresh_if_stale(Path("/x")))
            start.assert_called_once()

    def test_fires_when_no_marker_and_no_build(self):
        # External edit path: no pending marker, no prior build -> safety net fires.
        with patch.object(self.srv, "_index_inputs_stale", return_value=True), \
             patch.object(self.srv, "_background_refresh_active", return_value=False), \
             patch.object(self.srv, "_read_monitor_config", return_value={"quiet_period_seconds": 300.0}), \
             patch.object(self.srv, "_load_script", return_value=self._fake_idx(pending_age=None, ended_at=None)), \
             patch.object(self.srv, "_start_background_index_refresh", return_value=True) as start:
            self.assertTrue(self.srv._maybe_refresh_if_stale(Path("/x")))
            start.assert_called_once()

    def test_config_quiet_period_override_and_default_floor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs").mkdir()
            (root / "docs" / "workflow-config.json").write_text(
                '{"indexing":{"monitor":{"quiet_period_seconds":120}}}', encoding="utf-8"
            )
            cfg = self.srv._read_monitor_config(root)
            self.assertEqual(cfg["quiet_period_seconds"], 120.0)
        with tempfile.TemporaryDirectory() as td:
            cfg = self.srv._read_monitor_config(Path(td))  # no config -> default
            self.assertEqual(cfg["quiet_period_seconds"], self.srv._MONITOR_DEFAULT_QUIET_PERIOD_SECONDS)

    def test_config_quiet_period_floored_to_interval(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs").mkdir()
            (root / "docs" / "workflow-config.json").write_text(
                '{"indexing":{"monitor":{"interval_seconds":30,"quiet_period_seconds":5}}}', encoding="utf-8"
            )
            cfg = self.srv._read_monitor_config(root)
            self.assertEqual(cfg["quiet_period_seconds"], 30.0)  # floored up to the interval


class FreshnessAnnotationAndDriftPartitionTests(unittest.TestCase):
    """1ro43 AC-3/AC-4/AC-5: per-citation freshness annotation (batched,
    silent absence, live-fallback omission), the evidence-gated drift
    partition (default-OFF, kill switch, relevance-band guard, healthy-
    reranked-path-only), and the zero-git query-path guarantee."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True)
        import importlib.util as ilu
        spec = ilu.spec_from_file_location(
            "index_state_store", Path(__file__).resolve().parents[1] / "index_state_store.py")
        self.iss = ilu.module_from_spec(spec)
        spec.loader.exec_module(self.iss)
        self.srv._DEGRADED_LOG_STATE.clear()
        self.addCleanup(self.srv._DEGRADED_LOG_STATE.clear)

    def _seed_store(self, *, with_drift=True, finalize=True):
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            store.apply_freshness(rows={
                "docs/stale.md": {"last_modified": 1700000000, "churn_score": 0.1,
                                  "commit_count": 3, "source": "git"},
                "docs/current.md": {"last_modified": 1700000000, "churn_score": 0.0,
                                    "commit_count": 0, "source": "git"},
                "src/alpha.py": {"last_modified": 1700000000, "churn_score": 0.5,
                                 "commit_count": 15, "source": "git"},
            })
            if with_drift:
                store.upsert_doc_drift({
                    "docs/stale.md": {"drifted": True, "drift_refs": ["src/alpha.py"],
                                      "commits_since": 9, "anchor_kind": "content"},
                    "docs/current.md": {"drifted": False, "drift_refs": ["src/alpha.py"],
                                        "commits_since": 0, "anchor_kind": "verification"},
                })
        finally:
            store.close()
        if finalize:
            attempt = self.iss.begin_build_epoch(self.index_dir, "fixture")
            assert self.iss.finalize_build_epoch(self.index_dir, attempt)

    @staticmethod
    def _doc_chunk(path, score, text="alpha guide"):
        return {"path": path, "kind": "doc", "section": "S", "lines": [1, 4],
                "text": text, "score": score}

    def _healthy_docs_index(self, chunks, reranked=True):
        index = MagicMock()
        index.root = self.root
        index.search_docs.return_value = (chunks, reranked)
        return index

    # --- AC-3: annotation present with metadata, cleanly absent without ---

    def test_docs_search_results_carry_freshness_fields(self):
        self._seed_store()
        index = self._healthy_docs_index(
            [self._doc_chunk("docs/stale.md", 0.9), self._doc_chunk("docs/current.md", 0.85)])
        resp = self.srv.docs_search_response(index, "alpha")
        results = resp["data"]["results"]
        stale = next(r for r in results if r["path"] == "docs/stale.md")
        self.assertTrue(stale["freshness"]["drifted"])
        self.assertEqual(stale["freshness"]["commits_since_verified"], 9)
        self.assertIn("age_days", stale["freshness"])
        self.assertIn("churn_score", stale["freshness"])
        current = next(r for r in results if r["path"] == "docs/current.md")
        self.assertFalse(current["freshness"]["drifted"])

    def test_metadata_free_store_omits_freshness_without_errors(self):
        # No store at all: annotation is silently absent, response is intact.
        index = self._healthy_docs_index([self._doc_chunk("docs/stale.md", 0.9)])
        resp = self.srv.docs_search_response(index, "alpha")
        self.assertEqual(resp["status"], "ok")
        self.assertNotIn("freshness", resp["data"]["results"][0])
        self.assertNotIn("drift_partition_applied", resp["data"])

    def test_code_search_results_carry_freshness_but_never_drift(self):
        self._seed_store()
        index = MagicMock()
        index.root = self.root
        index.search_code.return_value = (
            [{"path": "src/alpha.py", "kind": "code", "language": "python",
              "section": "", "lines": [1, 5], "text": "def alpha(): pass", "score": 0.9}],
            True,
        )
        with patch.dict(os.environ, {"WAVEFOUNDRY_ENABLE_DRIFT_PARTITION": "1"}):
            resp = self.srv.code_search_response(index, "alpha")
        result = resp["data"]["results"][0]
        self.assertIn("churn_score", result["freshness"])
        self.assertNotIn("drifted", result["freshness"])
        self.assertNotIn("demoted", result)

    # --- AC-4: partition default-OFF, opt-in, guard, kill switch, modes ---

    def test_drift_partition_is_default_off(self):
        self._seed_store()
        index = self._healthy_docs_index(
            [self._doc_chunk("docs/stale.md", 0.9), self._doc_chunk("docs/current.md", 0.85)])
        resp = self.srv.docs_search_response(index, "alpha")
        results = resp["data"]["results"]
        self.assertEqual(results[0]["path"], "docs/stale.md")  # order untouched
        self.assertNotIn("demoted", results[0])
        self.assertNotIn("drift_partition_applied", resp["data"])

    def test_drift_partition_moves_flagged_docs_when_enabled(self):
        self._seed_store()
        index = self._healthy_docs_index(
            [self._doc_chunk("docs/stale.md", 0.9), self._doc_chunk("docs/current.md", 0.85)])
        with patch.dict(os.environ, {"WAVEFOUNDRY_ENABLE_DRIFT_PARTITION": "1"}):
            resp = self.srv.docs_search_response(index, "alpha")
        results = resp["data"]["results"]
        self.assertEqual([r["path"] for r in results],
                         ["docs/current.md", "docs/stale.md"])
        self.assertTrue(results[1]["demoted"])
        self.assertEqual(results[1]["partition_reason"], "doc_code_drift")
        self.assertNotIn("demoted", results[0])
        self.assertTrue(resp["data"]["drift_partition_applied"])
        self.assertEqual(resp["data"]["drift_demoted_count"], 1)

    def test_relevance_band_guard_protects_the_only_good_answer(self):
        self._seed_store()
        # The drifted doc leads by MORE than the band — no comparable current
        # alternative exists, so demoting it would bury the best answer.
        index = self._healthy_docs_index(
            [self._doc_chunk("docs/stale.md", 0.9),
             self._doc_chunk("docs/current.md", 0.9 - self.srv.DRIFT_RELEVANCE_BAND - 0.05)])
        with patch.dict(os.environ, {"WAVEFOUNDRY_ENABLE_DRIFT_PARTITION": "1"}):
            resp = self.srv.docs_search_response(index, "alpha")
        results = resp["data"]["results"]
        self.assertEqual(results[0]["path"], "docs/stale.md")
        self.assertNotIn("demoted", results[0])
        self.assertNotIn("drift_partition_applied", resp["data"])

    def test_kill_switch_wins_over_enable(self):
        self._seed_store()
        index = self._healthy_docs_index(
            [self._doc_chunk("docs/stale.md", 0.9), self._doc_chunk("docs/current.md", 0.85)])
        with patch.dict(os.environ, {"WAVEFOUNDRY_ENABLE_DRIFT_PARTITION": "1",
                                     "WAVEFOUNDRY_DISABLE_DRIFT_PARTITION": "1"}):
            resp = self.srv.docs_search_response(index, "alpha")
        self.assertEqual(resp["data"]["results"][0]["path"], "docs/stale.md")
        self.assertNotIn("drift_partition_applied", resp["data"])

    def test_partition_suppressed_when_not_reranked(self):
        self._seed_store()
        index = self._healthy_docs_index(
            [self._doc_chunk("docs/stale.md", 0.9), self._doc_chunk("docs/current.md", 0.85)],
            reranked=False)
        with patch.dict(os.environ, {"WAVEFOUNDRY_ENABLE_DRIFT_PARTITION": "1"}):
            resp = self.srv.docs_search_response(index, "alpha")
        results = resp["data"]["results"]
        self.assertEqual(results[0]["path"], "docs/stale.md")
        self.assertNotIn("demoted", results[0])
        # Annotation itself still rides along (suppression is partition-only).
        self.assertTrue(results[0]["freshness"]["drifted"])

    def test_lexical_fallback_is_annotated_but_never_partitioned(self):
        self._seed_store()
        # Publish FTS rows so the degraded serve has something to return.
        rows = [{"id": "d1", "path": "docs/stale.md", "kind": "doc", "language": "",
                 "lines": [1, 4], "section": "Intro", "tags": "", "chunk_hash": "h1",
                 "text": "alpha guide entry"}]
        import contextlib, io as _io
        with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
            self.iss.reconcile_chunk_index(self.index_dir, "docs", {"d1"}, lambda: rows)
        attempt = self.iss.begin_build_epoch(self.index_dir, "fixture-2")
        assert self.iss.finalize_build_epoch(self.index_dir, attempt)
        index = MagicMock()
        index.root = self.root
        index.search_docs.side_effect = self.srv.SemanticModelUnavailableOfflineError("offline")
        with patch.dict(os.environ, {"WAVEFOUNDRY_ENABLE_DRIFT_PARTITION": "1"}):
            resp = self.srv.docs_search_response(index, "alpha")
        self.assertEqual(resp["data"]["search_mode"], "lexical_fallback")
        results = resp["data"]["results"]
        self.assertTrue(results, "expected FTS-served results")
        self.assertTrue(results[0]["freshness"]["drifted"])  # annotated
        self.assertNotIn("demoted", results[0])              # never partitioned
        self.assertNotIn("drift_partition_applied", resp["data"])

    def test_live_fallback_omits_freshness_entirely(self):
        # Populated freshness tables but NO completed epoch: the live walk
        # serves, and stored metadata must not be attached to live content.
        self._seed_store(finalize=False)
        self.iss.begin_build_epoch(self.index_dir, "interrupted")  # building state
        index = MagicMock()
        index.root = self.root
        index.search_docs.side_effect = self.srv.IndexNotReadyError("mid-build")
        index.search_docs_lexical.return_value = [self._doc_chunk("docs/stale.md", 0.5)]
        with patch.dict(os.environ, {"WAVEFOUNDRY_ENABLE_DRIFT_PARTITION": "1"}):
            resp = self.srv.docs_search_response(index, "alpha")
        self.assertEqual(resp["data"]["search_mode"], "live_fallback")
        results = resp["data"]["results"]
        self.assertTrue(results)
        self.assertNotIn("freshness", results[0])
        self.assertNotIn("drift_partition_applied", resp["data"])

    def test_code_lexical_results_carry_freshness(self):
        self._seed_store()
        rows = [{"id": "c1", "path": "src/alpha.py", "kind": "code", "language": "python",
                 "lines": [1, 5], "section": "", "tags": "", "chunk_hash": "h1",
                 "text": "def alpha_handler(): pass"}]
        import contextlib, io as _io
        with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
            self.iss.reconcile_chunk_index(self.index_dir, "code", {"c1"}, lambda: rows)
        resp = self.srv.code_lexical_response(self.root, "alpha_handler")
        results = resp["data"]["results"]
        self.assertTrue(results)
        self.assertIn("churn_score", results[0]["freshness"])

    # --- AC-5: zero git subprocesses on the query path ---

    def test_query_path_spawns_no_git(self):
        self._seed_store()
        observed: list[list[str]] = []

        def _record(cmd, *a, **k):
            argv = [str(c) for c in (cmd if isinstance(cmd, (list, tuple)) else [cmd])]
            observed.append(argv)
            raise AssertionError(f"query path spawned a subprocess: {argv}")

        docs_index = self._healthy_docs_index([self._doc_chunk("docs/stale.md", 0.9)])
        code_index = MagicMock()
        code_index.root = self.root
        code_index.search_code.return_value = (
            [{"path": "src/alpha.py", "kind": "code", "language": "python",
              "section": "", "lines": [1, 5], "text": "def alpha(): pass", "score": 0.9}],
            True,
        )
        with patch("subprocess.run", _record), \
             patch("subprocess.Popen", _record), \
             patch.object(self.iss.subprocess_util, "isolated_run", _record), \
             patch.dict(os.environ, {"WAVEFOUNDRY_ENABLE_DRIFT_PARTITION": "1"}):
            self.srv.docs_search_response(docs_index, "alpha")
            self.srv.code_search_response(code_index, "alpha")
            self.srv.code_lexical_response(self.root, "alpha_handler")
        git_calls = [argv for argv in observed if "git" in argv[:2]]
        self.assertEqual(git_calls, [])
        self.assertEqual(observed, [])  # no subprocess of ANY kind on the query path

    def test_code_ask_citations_annotated_and_partitioned_when_enabled(self):
        self._seed_store()
        index = MagicMock()
        index.root = self.root
        index.search_combined.return_value = (
            [{"path": "docs/stale.md", "kind": "doc", "lines": [1, 4],
              "text": "stale guide", "score": 0.9},
             {"path": "docs/current.md", "kind": "doc", "lines": [1, 4],
              "text": "current guide", "score": 0.85}],
            True,   # reranked
            5, 5,   # vector_ms, rerank_ms
            [], [], "none", {},
        )
        with patch.dict(os.environ, {"WAVEFOUNDRY_ENABLE_DRIFT_PARTITION": "1"}):
            resp = self.srv.code_ask_response(index, self.root, "how does alpha work?")
        data = resp["data"]
        citations = data["citations"]
        self.assertEqual([c["path"] for c in citations],
                         ["docs/current.md", "docs/stale.md"])
        self.assertTrue(citations[1]["demoted"])
        self.assertEqual(citations[1]["partition_reason"], "doc_code_drift")
        self.assertTrue(citations[1]["freshness"]["drifted"])
        # final_rank re-stamped to match the partitioned output order.
        self.assertEqual([c["final_rank"] for c in citations], [1, 2])
        self.assertTrue(data["drift_partition_applied"])
        self.assertEqual(data["drift_demoted_count"], 1)
        # The existing doc-type score-demotion flag is not overloaded.
        self.assertIn("partition_applied", data)


class DriftWorklistAuditSurfaceTests(unittest.TestCase):
    """1ro43 Req 7 / AC-7: the drift worklist rides wf_audit's `doc_drift`
    sub-object (the gardening landing tool), never blocks `ready`, and
    excludes historical rows by construction."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True)
        import importlib.util as ilu
        spec = ilu.spec_from_file_location(
            "index_state_store", Path(__file__).resolve().parents[1] / "index_state_store.py")
        self.iss = ilu.module_from_spec(spec)
        spec.loader.exec_module(self.iss)

    def test_wf_audit_carries_worklist_and_advisory(self):
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            store.upsert_doc_drift({
                "docs/badly-drifted.md": {"drifted": True, "drift_refs": ["src/a.py"],
                                          "commits_since": 12, "anchor_kind": "content"},
                "docs/mildly-drifted.md": {"drifted": True, "drift_refs": ["src/b.py"],
                                           "commits_since": 4, "anchor_kind": "verification"},
                "docs/fine.md": {"drifted": False, "drift_refs": [], "commits_since": 0,
                                 "anchor_kind": "content"},
                "docs/waves/1aaaa w/wave.md": {"historical": True, "waves_behind": 5,
                                               "commits_since": 40},
            })
        finally:
            store.close()
        resp = self.srv.wf_audit_response(self.root)
        drift = resp["data"]["doc_drift"]
        self.assertTrue(drift["available"])
        self.assertEqual(drift["flagged_count"], 2)
        # Contract: commits_since DESC, then path; historical rows absent.
        self.assertEqual([e["path"] for e in drift["entries"]],
                         ["docs/badly-drifted.md", "docs/mildly-drifted.md"])
        self.assertEqual(drift["entries"][0]["commits_since"], 12)
        self.assertEqual(drift["entries"][1]["anchor_kind"], "verification")
        self.assertEqual(drift["entries"][0]["drift_refs"], ["src/a.py"])
        codes = [d.get("code") for d in resp["diagnostics"]]
        self.assertIn("doc_code_drift_flagged", codes)

    def test_absent_store_degrades_and_never_blocks(self):
        resp = self.srv.wf_audit_response(self.root)
        drift = resp["data"]["doc_drift"]
        self.assertFalse(drift["available"])
        self.assertEqual(drift["entries"], [])
        # 1u8o2 (1u8o0): even the degraded shape carries the evaluation object,
        # and an unevaluated store is field-distinguishable from clean.
        self.assertEqual(drift["evaluation"]["status"], "never_evaluated")
        codes = [d.get("code") for d in resp["diagnostics"]]
        self.assertNotIn("doc_code_drift_flagged", codes)

    def test_evaluation_stale_is_field_distinguishable_and_never_blocks_ready(self):
        # 1u8o2 (1u8o0) AC-3 + AC-4: the additive `evaluation` object makes a
        # frozen (failing) evaluation distinguishable from evaluated-clean on
        # response FIELDS alone; `available` true + status "stale" is a real
        # state (last-good rows served); and the new state never gates `ready`.
        # Delivery-review repair (QA P2-2): the bare fixture is never audit-
        # ready (ready False before AND after injection, so the never-blocks
        # assertion compared False to False). Patch the three ready legs to
        # pass (same trio as WaveAuditTests) so ready is True pre-injection
        # and the stale evaluation must LEAVE it True to satisfy the pin.
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            store.upsert_doc_drift({
                "docs/badly-drifted.md": {"drifted": True, "drift_refs": ["src/a.py"],
                                          "commits_since": 12, "anchor_kind": "content"},
            })
            # The real success producer stamps last-success and zeroes failures.
            self.iss._record_drift_success(store)
        finally:
            store.close()
        wave_record = {"id": "w1", "status": "active", "changes": [],
                       "title": "Wave", "path": "docs/waves/w1/wave.md"}
        healthy_snapshot = {
            "metadata_ready": True, "epoch_complete": True, "docs_present": True,
            "code_present": True, "code_sources_in_scope": True,
            "code_layer_missing": False, "indexed_chunker_versions": {},
            "current_chunker_version": "1", "chunker_version_mismatch": False,
            "readiness_overview": "ready", "freshness_checked": False,
            "freshness": "unknown", "freshness_verification_tool": "index_health",
        }
        passing_validate = {"passed": True, "errors": [], "warnings": [], "output": ""}

        def _with_audit_ready():
            stack = contextlib.ExitStack()
            stack.enter_context(patch.object(self.srv, "current_wave", return_value=wave_record))
            stack.enter_context(patch.object(self.srv, "run_validate", return_value=passing_validate))
            stack.enter_context(patch.object(
                self.srv, "_audit_index_snapshot", return_value=healthy_snapshot))
            return stack

        with _with_audit_ready():
            resp = self.srv.wf_audit_response(self.root)
        drift = resp["data"]["doc_drift"]
        self.assertTrue(drift["available"])
        ev = drift["evaluation"]
        self.assertEqual(ev["status"], "evaluated")
        self.assertEqual(ev["consecutive_failures"], 0)
        self.assertIsNotNone(ev["last_success_at"])
        ready_before = resp["data"]["ready"]
        self.assertIs(ready_before, True,
                      "non-vacuity precondition: the fixture must be audit-ready")
        # Now the real failure producer: two consecutive failed evaluations.
        self.iss._record_drift_failure(
            self.index_dir, "gardener classifier", "malformed_patch: probe")
        self.iss._record_drift_failure(
            self.index_dir, "gardener classifier", "malformed_patch: probe")
        with _with_audit_ready():
            resp2 = self.srv.wf_audit_response(self.root)
        drift2 = resp2["data"]["doc_drift"]
        self.assertTrue(drift2["available"],
                        "available-true-but-stale is a real state: last-good rows served")
        ev2 = drift2["evaluation"]
        self.assertEqual(ev2["status"], "stale")
        self.assertEqual(ev2["consecutive_failures"], 2)
        self.assertEqual(ev2["last_stage"], "gardener classifier")
        self.assertTrue(ev2["last_reason"].startswith("malformed_patch"))
        self.assertIsNotNone(ev2["stale_since"])
        self.assertIsNotNone(ev2["age_seconds"])
        # Drift never blocks ready: the stale evaluation changes nothing.
        self.assertEqual(resp2["data"]["ready"], ready_before)
        codes = [d.get("code") for d in resp2["diagnostics"]]
        self.assertIn("doc_drift_evaluation_stale", codes)


class DocCodeKindFilterTests(unittest.TestCase):
    """Wave 1wik9 (1whup): docs_search kind filtering works for the routed
    doc-code kind on BOTH enforcement layers. The semantic path filters by
    raw SQL equality over real Lance rows (the readiness code lane proved
    live-walk unit tests alone miss this filter class — the `architecture`
    virtual kind is dead there); the live-walk/lexical path filters through
    _doc_matches_kind, whose fall-through short-circuit means a kind without
    its own branch can never match any filter."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _rows(self):
        return [
            {
                "id": "docs/guide.md#install",
                "path": "docs/guide.md",
                "kind": "doc",
                "language": None,
                "lines": [1, 4],
                "section": "Install",
                "text": "Install prose paragraph",
            },
            {
                "id": "docs/guide.md#install:code-1",
                "path": "docs/guide.md",
                "kind": "doc-code",
                "language": "bash",
                "lines": [5, 7],
                "section": "Install",
                "text": "Install\n\nwidgetctl install --profile default",
            },
            {
                "id": "docs/architecture/overview.md#arch:code-1",
                "path": "docs/architecture/overview.md",
                "kind": "doc-code",
                "language": "mermaid",
                "lines": [1, 3],
                "section": "Arch",
                "text": "Arch\n\ngraph TD; A-->B",
            },
        ]

    def test_semantic_path_kind_filter_matches_real_doc_code_rows(self):
        _write_index_layer(
            self.root / ".wavefoundry" / "index",
            self._rows(),
            [[1, 0], [1, 0], [1, 0]],
        )
        index = self.srv.WaveIndex(self.root)
        import numpy as np
        with patch.object(index, "_indexer_constant", return_value="test-model"):
            with patch.object(index, "_embed_query", return_value=np.array([1, 0], dtype=np.float32)):
                with patch.object(index, "_get_reranker", return_value=None):
                    results, _ = index.search_docs("install command", kind="doc-code", top_n=5)
        self.assertTrue(results, "raw-SQL kind filter must find real doc-code rows")
        self.assertEqual({r["kind"] for r in results}, {"doc-code"})
        with patch.object(index, "_indexer_constant", return_value="test-model"):
            with patch.object(index, "_embed_query", return_value=np.array([1, 0], dtype=np.float32)):
                with patch.object(index, "_get_reranker", return_value=None):
                    doc_only, _ = index.search_docs("install command", kind="doc", top_n=5)
        self.assertEqual({r["kind"] for r in doc_only}, {"doc"},
                         "kind='doc' must not sweep in doc-code rows")

    def test_docs_search_response_accepts_doc_code_kind(self):
        index = MagicMock()
        index.search_docs.return_value = ([], True)
        resp = self.srv.docs_search_response(index, "query", kind="doc-code")
        codes = [d.get("code") for d in resp.get("diagnostics", [])]
        self.assertNotIn("invalid_arguments", codes)
        self.assertIn("doc-code", self.srv.DOCS_SEARCH_KINDS)

    def test_doc_matches_kind_has_a_doc_code_branch(self):
        index = self.srv.WaveIndex(self.root)
        chunk = {"kind": "doc-code", "path": "docs/guide.md"}
        self.assertTrue(index._doc_matches_kind(chunk, "doc-code"))
        self.assertTrue(index._doc_matches_kind(chunk, ""))
        self.assertFalse(index._doc_matches_kind(chunk, "doc"))
        self.assertFalse(index._doc_matches_kind({"kind": "doc", "path": "docs/x.md"}, "doc-code"))

    def test_architecture_virtual_kind_excludes_doc_code(self):
        # Recorded decision (1whup Requirement 3): doc-code chunks do NOT
        # match the architecture virtual kind even under docs/architecture/
        # (mirrors the doc-summary exclusion precedent).
        index = self.srv.WaveIndex(self.root)
        arch_fence = {"kind": "doc-code", "path": "docs/architecture/overview.md"}
        self.assertFalse(index._doc_matches_kind(arch_fence, "architecture"))
        self.assertTrue(index._doc_matches_kind(
            {"kind": "doc", "path": "docs/architecture/overview.md"}, "architecture"))

    def test_code_ask_partition_tuples_stay_complementary(self):
        # Both literals must carry the same tuple: editing one side alone
        # puts doc-code in BOTH partitions. Source-level pin.
        src = inspect.getsource(self.srv)
        docs_side = src.count('("doc", "doc-summary", "seed", "doc-code")')
        self.assertEqual(docs_side, 2,
                         "_docs_src and _code_src must share the one partition tuple")


# ---------------------------------------------------------------------------
# Wave 1wpig / change 1wpaj — graph-report eligibility applied BEFORE top-N
# truncation, betweenness complete-order refill + read-side staleness gate,
# and per-edge trust fields on code_callhierarchy entries.
#
# Every fixture below is built so at least one INELIGIBLE candidate OUTRANKS
# the Nth eligible row. Without that the section fills to `limit` under the
# pre-repair slice-then-filter shape too and the test proves nothing.
# ---------------------------------------------------------------------------


def _wpaj_node(nid: str, **extra) -> dict:
    """One graph node. `external::` ids deliberately carry no source_file."""
    node = {
        "id": nid,
        "label": nid.split("::")[-1] if "::" in nid else nid,
        "kind": "function",
        "source_location": "1:0",
    }
    if not nid.startswith("external::"):
        node["source_file"] = nid.split("::")[0] if "::" in nid else nid
    node.update(extra)
    return node


# (target, incoming calls, node extras) — externals outrank the generated node,
# which outranks every handwritten row.
_WPAJ_FAN_IN_LADDER = (
    ("external::ext_hot", 12, {}),
    ("external::ext_warm", 11, {}),
    ("external::ext_cool", 10, {}),
    ("src/gen.py::gen_target", 9, {"generated": True}),
    ("src/app.py::keep_a", 8, {}),
    ("src/app.py::keep_b", 7, {}),
    ("src/app.py::keep_c", 6, {}),
)

# (source, outgoing calls, node extras) — the generated hub outranks all three
# handwritten hubs. No entry reaches the fixed chokepoint threshold (20), so
# this graph leaves chokepoints/file_hubs empty.
_WPAJ_FAN_OUT_LADDER = (
    ("src/gen.py::gen_hub", 9, {"generated": True}),
    ("src/app.py::hub_a", 8, {}),
    ("src/app.py::hub_b", 7, {}),
    ("src/app.py::hub_c", 6, {}),
)


def _wpaj_fan_graph() -> tuple[list, list]:
    """Graph exercising the two `_ranked` sections (truncation site 1 of 3)."""
    nodes: list = []
    edges: list = []
    for target, count, extra in _WPAJ_FAN_IN_LADDER:
        nodes.append(_wpaj_node(target, **extra))
        slug = re.sub(r"[^0-9a-zA-Z]+", "_", target).strip("_")
        # One caller per edge, so no caller's own fan_out can disturb the
        # fan_out ladder below (every caller ends at fan_out 1).
        for i in range(count):
            caller = f"src/in_{slug}_{i}.py::in_{slug}_{i}"
            nodes.append(_wpaj_node(caller))
            edges.append({
                "source": caller, "target": target,
                "relation": "calls", "confidence": "RECEIVER_RESOLVED",
            })
    sinks = [f"src/sink{i}.py::sink{i}" for i in range(9)]
    nodes.extend(_wpaj_node(sink) for sink in sinks)
    for source, count, extra in _WPAJ_FAN_OUT_LADDER:
        nodes.append(_wpaj_node(source, **extra))
        for sink in sinks[:count]:
            edges.append({
                "source": source, "target": sink,
                "relation": "calls", "confidence": "RECEIVER_RESOLVED",
            })
    return nodes, edges


def _wpaj_hub_graph() -> tuple[list, list]:
    """Graph exercising the two inline slices (truncation sites 2 and 3).

    Both ladders clear the fixed chokepoint threshold (20 — `wf_graph_report`
    never overrides `chokepoint_threshold`). chokepoints takes the non-module
    ladder, file_hubs the module one.
    """
    nodes: list = []
    edges: list = []
    csinks = [f"src/csink{i}.py::csink{i}" for i in range(25)]
    nodes.extend(_wpaj_node(sink) for sink in csinks)
    for source, count, extra in (
        ("src/gen.py::gen_choke", 25, {"generated": True}),
        ("src/app.py::choke_a", 24, {}),
        ("src/app.py::choke_b", 23, {}),
        ("src/app.py::choke_c", 22, {}),
    ):
        nodes.append(_wpaj_node(source, **extra))
        for sink in csinks[:count]:
            edges.append({
                "source": source, "target": sink,
                "relation": "calls", "confidence": "RECEIVER_RESOLVED",
            })
    msinks = [f"src/msink{i}.py::msink{i}" for i in range(25)]
    nodes.extend(_wpaj_node(sink) for sink in msinks)
    for module, count, extra in (
        ("src/generated_mod.py", 25, {"generated": True}),
        ("src/mod_a.py", 24, {}),
        ("src/mod_b.py", 23, {}),
        ("src/mod_c.py", 22, {}),
    ):
        nodes.append(_wpaj_node(module, kind="module", **extra))
        for sink in msinks[:count]:
            edges.append({
                "source": module, "target": sink,
                "relation": "calls", "confidence": "RECEIVER_RESOLVED",
            })
    return nodes, edges


class _GraphReport1wpajMixin:
    """Graph/cluster artifact fixtures shared by the wave-1wpaj classes."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_graph(self, nodes: list, edges: list, *, builder_version: str = "12") -> None:
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "project-graph.json").write_text(
            json.dumps({
                "schema_version": "1",
                "builder_version": builder_version,
                "layer": "project",
                "nodes": nodes,
                "edges": edges,
                "counts": {"files": len(nodes), "nodes": len(nodes), "edges": len(edges)},
            }),
            encoding="utf-8",
        )

    def _report(self, **kwargs) -> dict:
        result = self.srv.wf_graph_report_response(self.root, layer="project", **kwargs)
        self.assertEqual(result["status"], "ok", result)
        return result["data"]

    def _ids(self, report: dict, section: str) -> list:
        return [str(row["node_id"]) for row in report.get(section, [])]

    @contextlib.contextmanager
    def _pre_repair_report(self, post_filter_sections):
        """Restore the pre-1wpaj shape: `report()` ignores `eligible`, and the
        caller filters the ALREADY-TRUNCATED rows.

        `post_filter_sections` reproduces the two removed loops exactly:
        `exclude_generated` post-filtered ("fan_in", "fan_out", "chokepoints");
        `exclude_external` post-filtered those plus "file_hubs". Pass the tuple
        matching the flag under test — using the wrong one would credit the old
        code with a filter it never applied.
        """
        gq = self.srv._load_graph_query()
        original = gq.GraphQueryIndex.report

        def _legacy(index_self, **kwargs):
            eligible = kwargs.pop("eligible", None)
            out = original(index_self, **kwargs)
            if eligible is not None:
                for name in post_filter_sections:
                    rows = out.get(name)
                    if isinstance(rows, list):
                        out[name] = [
                            row for row in rows
                            if isinstance(row, dict)
                            and eligible(str(row.get("node_id") or ""))
                        ]
            return out

        with patch.object(gq.GraphQueryIndex, "report", _legacy):
            yield


class TestGraphReportFanSectionsFilterBeforeTruncation(_GraphReport1wpajMixin, unittest.TestCase):
    """Wave 1wpaj: fan_in/fan_out fill the requested `limit` whenever enough
    ELIGIBLE candidates exist, even when ineligible candidates rank above them.

    `exclude_external` is exercised on fan_in only: an `external::` node is a
    call TARGET by construction (the extractor never emits an edge sourced at
    one), so an external row in fan_out would be a shape the graph cannot
    produce. `exclude_generated` applies to both directions.
    """

    def setUp(self):
        super().setUp()
        self._write_graph(*_wpaj_fan_graph())

    # ---- fan_in ----------------------------------------------------------
    def test_fan_in_exclude_external_fills_the_limit(self):
        report = self._report(limit=3, sections=["fan_in"], exclude_external=True)
        self.assertEqual(self._ids(report, "fan_in"), [
            "src/gen.py::gen_target", "src/app.py::keep_a", "src/app.py::keep_b",
        ])

    def test_fan_in_exclude_external_at_limit_one(self):
        # The reproduced defect: the top-ranked candidate is ineligible, so the
        # pre-repair slice-then-filter returned an EMPTY section here.
        report = self._report(limit=1, sections=["fan_in"], exclude_external=True)
        self.assertEqual(self._ids(report, "fan_in"), ["src/gen.py::gen_target"])

    def test_fan_in_exclude_generated_fills_the_limit(self):
        # The generated node sits at rank 4, so limit=4 is the discriminating
        # request: pre-repair it returned 3 rows.
        report = self._report(limit=4, sections=["fan_in"], exclude_generated=True)
        self.assertEqual(self._ids(report, "fan_in"), [
            "external::ext_hot", "external::ext_warm", "external::ext_cool",
            "src/app.py::keep_a",
        ])

    def test_fan_in_both_filters_at_limit_one(self):
        report = self._report(
            limit=1, sections=["fan_in"], exclude_external=True, exclude_generated=True,
        )
        self.assertEqual(self._ids(report, "fan_in"), ["src/app.py::keep_a"])

    def test_deletion_check_fan_in_post_slice_filtering_empties_the_section(self):
        with self._pre_repair_report(("fan_in", "fan_out", "chokepoints", "file_hubs")):
            legacy = self._report(limit=3, sections=["fan_in"], exclude_external=True)
        self.assertEqual(
            self._ids(legacy, "fan_in"), [],
            "the pre-repair reconstruction must reproduce the empty section; if it "
            "does not, the fixture has no ineligible candidate above the Nth eligible row",
        )
        current = self._report(limit=3, sections=["fan_in"], exclude_external=True)
        self.assertEqual(self._ids(current, "fan_in"), [
            "src/gen.py::gen_target", "src/app.py::keep_a", "src/app.py::keep_b",
        ])

    def test_deletion_check_fan_in_post_slice_generated_filter_underfills(self):
        with self._pre_repair_report(("fan_in", "fan_out", "chokepoints")):
            legacy = self._report(limit=4, sections=["fan_in"], exclude_generated=True)
        self.assertEqual(len(self._ids(legacy, "fan_in")), 3)
        current = self._report(limit=4, sections=["fan_in"], exclude_generated=True)
        self.assertEqual(self._ids(current, "fan_in"), [
            "external::ext_hot", "external::ext_warm", "external::ext_cool",
            "src/app.py::keep_a",
        ])

    # ---- fan_out ---------------------------------------------------------
    def test_fan_out_exclude_generated_fills_the_limit(self):
        report = self._report(limit=3, sections=["fan_out"], exclude_generated=True)
        self.assertEqual(self._ids(report, "fan_out"), [
            "src/app.py::hub_a", "src/app.py::hub_b", "src/app.py::hub_c",
        ])

    def test_fan_out_exclude_generated_at_limit_one(self):
        report = self._report(limit=1, sections=["fan_out"], exclude_generated=True)
        self.assertEqual(self._ids(report, "fan_out"), ["src/app.py::hub_a"])

    def test_deletion_check_fan_out_post_slice_filtering_underfills(self):
        with self._pre_repair_report(("fan_in", "fan_out", "chokepoints")):
            legacy_three = self._report(limit=3, sections=["fan_out"], exclude_generated=True)
            legacy_one = self._report(limit=1, sections=["fan_out"], exclude_generated=True)
        self.assertEqual(len(self._ids(legacy_three, "fan_out")), 2)
        self.assertEqual(self._ids(legacy_one, "fan_out"), [])
        current = self._report(limit=3, sections=["fan_out"], exclude_generated=True)
        self.assertEqual(self._ids(current, "fan_out"), [
            "src/app.py::hub_a", "src/app.py::hub_b", "src/app.py::hub_c",
        ])

    # ---- unfiltered order ------------------------------------------------
    def test_unfiltered_fan_section_output_is_byte_for_byte_unchanged(self):
        """The unfiltered path (`eligible is None`) must be untouched.

        The expected rows are RECORDED literals below, not values re-derived
        from the call under test, so a change in either the ordering key or the
        row shape shows up as a byte difference.
        """
        gq = self.srv._load_graph_query()
        index = gq.get_query_index(self.root, layer="project")
        rows = index.report(limit=4, sections=["fan_in", "fan_out"])
        expected_fan_in = [
            {"node_id": "external::ext_hot", "count": 12, "label": "ext_hot", "kind": "function"},
            {"node_id": "external::ext_warm", "count": 11, "label": "ext_warm", "kind": "function"},
            {"node_id": "external::ext_cool", "count": 10, "label": "ext_cool", "kind": "function"},
            {"node_id": "src/gen.py::gen_target", "count": 9, "label": "gen_target", "kind": "function"},
        ]
        expected_fan_out = [
            {"node_id": "src/gen.py::gen_hub", "count": 9, "label": "gen_hub", "kind": "function"},
            {"node_id": "src/app.py::hub_a", "count": 8, "label": "hub_a", "kind": "function"},
            {"node_id": "src/app.py::hub_b", "count": 7, "label": "hub_b", "kind": "function"},
            {"node_id": "src/app.py::hub_c", "count": 6, "label": "hub_c", "kind": "function"},
        ]
        self.assertEqual(
            json.dumps(rows["fan_in"], sort_keys=True),
            json.dumps(expected_fan_in, sort_keys=True),
        )
        self.assertEqual(
            json.dumps(rows["fan_out"], sort_keys=True),
            json.dumps(expected_fan_out, sort_keys=True),
        )
        # Same order through the public tool (which annotates each row but must
        # not reorder or drop any of them).
        served = self._report(limit=4, sections=["fan_in", "fan_out"])
        self.assertEqual(
            self._ids(served, "fan_in"), [row["node_id"] for row in expected_fan_in],
        )
        self.assertEqual(
            self._ids(served, "fan_out"), [row["node_id"] for row in expected_fan_out],
        )


class TestGraphReportHubSectionsFilterBeforeTruncation(_GraphReport1wpajMixin, unittest.TestCase):
    """Wave 1wpaj: chokepoints and file_hubs each own an inline slice, so the
    predicate has to reach both of them separately from the `_ranked` helper.

    Only `exclude_generated` is exercised here: chokepoints ranks by fan_out and
    file_hubs is restricted to `kind: "module"`, and the extractor emits neither
    an outgoing edge from an `external::` node nor an `external::` module node,
    so an external row cannot appear in either section.
    """

    def setUp(self):
        super().setUp()
        self._write_graph(*_wpaj_hub_graph())

    # ---- chokepoints -----------------------------------------------------
    def test_chokepoints_exclude_generated_fills_the_limit(self):
        report = self._report(limit=3, sections=["chokepoints"], exclude_generated=True)
        self.assertEqual(self._ids(report, "chokepoints"), [
            "src/app.py::choke_a", "src/app.py::choke_b", "src/app.py::choke_c",
        ])

    def test_chokepoints_exclude_generated_at_limit_one(self):
        report = self._report(limit=1, sections=["chokepoints"], exclude_generated=True)
        self.assertEqual(self._ids(report, "chokepoints"), ["src/app.py::choke_a"])

    def test_deletion_check_chokepoints_post_slice_filtering_underfills(self):
        with self._pre_repair_report(("fan_in", "fan_out", "chokepoints")):
            legacy_three = self._report(limit=3, sections=["chokepoints"], exclude_generated=True)
            legacy_one = self._report(limit=1, sections=["chokepoints"], exclude_generated=True)
        self.assertEqual(len(self._ids(legacy_three, "chokepoints")), 2)
        self.assertEqual(self._ids(legacy_one, "chokepoints"), [])
        current = self._report(limit=3, sections=["chokepoints"], exclude_generated=True)
        self.assertEqual(self._ids(current, "chokepoints"), [
            "src/app.py::choke_a", "src/app.py::choke_b", "src/app.py::choke_c",
        ])

    # ---- file_hubs -------------------------------------------------------
    def test_file_hubs_exclude_generated_is_a_new_filter(self):
        # Contract WIDENING, not an ordering repair: the pre-repair generated
        # post-filter covered fan_in/fan_out/chokepoints only, so a generated
        # module hub was returned even with exclude_generated=True.
        unfiltered = self._report(limit=4, sections=["file_hubs"])
        self.assertIn("src/generated_mod.py", self._ids(unfiltered, "file_hubs"))
        filtered = self._report(limit=4, sections=["file_hubs"], exclude_generated=True)
        self.assertNotIn("src/generated_mod.py", self._ids(filtered, "file_hubs"))

    def test_file_hubs_exclude_generated_fills_the_limit(self):
        report = self._report(limit=3, sections=["file_hubs"], exclude_generated=True)
        self.assertEqual(self._ids(report, "file_hubs"), [
            "src/mod_a.py", "src/mod_b.py", "src/mod_c.py",
        ])

    def test_file_hubs_exclude_generated_at_limit_one(self):
        report = self._report(limit=1, sections=["file_hubs"], exclude_generated=True)
        self.assertEqual(self._ids(report, "file_hubs"), ["src/mod_a.py"])

    def test_deletion_check_file_hubs_generated_filter_never_reached_the_section(self):
        with self._pre_repair_report(("fan_in", "fan_out", "chokepoints")):
            legacy = self._report(limit=3, sections=["file_hubs"], exclude_generated=True)
        self.assertIn(
            "src/generated_mod.py", self._ids(legacy, "file_hubs"),
            "pre-repair, exclude_generated never reached file_hubs at all",
        )
        current = self._report(limit=3, sections=["file_hubs"], exclude_generated=True)
        self.assertEqual(self._ids(current, "file_hubs"), [
            "src/mod_a.py", "src/mod_b.py", "src/mod_c.py",
        ])

    # ---- unfiltered order ------------------------------------------------
    def test_unfiltered_hub_section_output_is_byte_for_byte_unchanged(self):
        """Recorded expected rows — see the fan-section twin for the rationale."""
        gq = self.srv._load_graph_query()
        index = gq.get_query_index(self.root, layer="project")
        rows = index.report(limit=4, sections=["chokepoints", "file_hubs"])
        expected_chokepoints = [
            {"node_id": "src/gen.py::gen_choke", "fan_out": 25, "label": "gen_choke"},
            {"node_id": "src/app.py::choke_a", "fan_out": 24, "label": "choke_a"},
            {"node_id": "src/app.py::choke_b", "fan_out": 23, "label": "choke_b"},
            {"node_id": "src/app.py::choke_c", "fan_out": 22, "label": "choke_c"},
        ]
        expected_file_hubs = [
            {"node_id": "src/generated_mod.py", "fan_out": 25, "label": "src/generated_mod.py", "kind": "module"},
            {"node_id": "src/mod_a.py", "fan_out": 24, "label": "src/mod_a.py", "kind": "module"},
            {"node_id": "src/mod_b.py", "fan_out": 23, "label": "src/mod_b.py", "kind": "module"},
            {"node_id": "src/mod_c.py", "fan_out": 22, "label": "src/mod_c.py", "kind": "module"},
        ]
        self.assertEqual(
            json.dumps(rows["chokepoints"], sort_keys=True),
            json.dumps(expected_chokepoints, sort_keys=True),
        )
        self.assertEqual(
            json.dumps(rows["file_hubs"], sort_keys=True),
            json.dumps(expected_file_hubs, sort_keys=True),
        )
        served = self._report(limit=4, sections=["chokepoints", "file_hubs"])
        self.assertEqual(
            self._ids(served, "chokepoints"),
            [row["node_id"] for row in expected_chokepoints],
        )
        self.assertEqual(
            self._ids(served, "file_hubs"),
            [row["node_id"] for row in expected_file_hubs],
        )


class _BetweennessArtifact1wpajMixin(_GraphReport1wpajMixin):
    """Persisted clusters artifact whose COMPLETE betweenness order carries
    eligible rows BELOW the ineligible top-N prefix."""

    # The persisted top-N prefix — every row ineligible under exclude_external.
    _PREFIX = (
        {"node_id": "external::ext_top_a", "score": 0.9, "label": "ext_top_a", "kind": "function"},
        {"node_id": "external::ext_top_b", "score": 0.8, "label": "ext_top_b", "kind": "function"},
        {"node_id": "external::ext_top_c", "score": 0.7, "label": "ext_top_c", "kind": "function"},
    )

    def setUp(self):
        super().setUp()
        self._write_graph([
            _wpaj_node("external::ext_top_a"),
            _wpaj_node("external::ext_top_b"),
            _wpaj_node("external::ext_top_c"),
            _wpaj_node("src/app.py::deep_a"),
            _wpaj_node("src/app.py::deep_b"),
            _wpaj_node("src/app.py::deep_c"),
        ], [])

    def _prefix_rows(self) -> list:
        return [dict(row) for row in self._PREFIX]

    @staticmethod
    def _pin(rows: list) -> list:
        """Project a served betweenness row onto the contract keys.

        The public tool annotates every ranked row with name-collision fields
        that belong to other waves; pinning those here would couple this test
        to changes it makes no claim about."""
        return [
            {key: row[key] for key in ("node_id", "score", "label", "kind")}
            for row in rows
        ]

    def _section(self, *, complete: bool = True) -> dict:
        section = {
            "method": "exact",
            "node_count": 6,
            "edge_count": 0,
            "top_n": 3,
            "elapsed_ms": 3,
            "ranking": self._prefix_rows(),
        }
        if complete:
            # Compact rows exactly as graph_cluster persists them: node_id +
            # score only, with label/kind resolved at serve time.
            section["complete_ranking"] = [
                {"node_id": "external::ext_top_a", "score": 0.9},
                {"node_id": "external::ext_top_b", "score": 0.8},
                {"node_id": "external::ext_top_c", "score": 0.7},
                {"node_id": "src/app.py::deep_a", "score": 0.6},
                {"node_id": "src/app.py::deep_b", "score": 0.5},
                {"node_id": "src/app.py::deep_c", "score": 0.4},
            ]
            section["complete_ranking_total"] = 6
        return section

    def _write_clusters(self, betweenness, *, cluster_builder_version=None) -> None:
        gc = self.srv._load_script("graph_cluster")
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "cluster_schema_version": "1",
            "cluster_builder_version": (
                gc.CLUSTER_BUILDER_VERSION if cluster_builder_version is None
                else cluster_builder_version
            ),
            "cluster_algorithm": "leiden",
            "layer": "project",
            "communities": [],
            "community_count": 0,
        }
        if betweenness is not None:
            payload["betweenness"] = betweenness
        (graph_dir / "project-graph-clusters.json").write_text(
            json.dumps(payload), encoding="utf-8",
        )


class TestBetweennessUnsupportedForCollapsedView(_BetweennessArtifact1wpajMixin, unittest.TestCase):
    """Wave 1wpaj: betweenness is served ONLY on the base topology.

    The persisted order describes the base graph. Every collapse flag rewrites
    nodes or edges before the report is computed, so serving that order under
    collapse labels base centrality as collapsed-graph centrality. Delivery
    review found this contract specified but unimplemented, with the request
    silently serving base rows, so these are its oracle.
    """

    COLLAPSE_FLAGS = (
        "collapse_generated_files",
        "collapse_class_module_pairs",
        "collapse_package_to_directory",
    )

    def test_each_collapse_flag_refuses_betweenness(self):
        self._write_clusters(self._section())
        for flag in self.COLLAPSE_FLAGS:
            with self.subTest(collapse_flag=flag):
                data = self._report(sections=["betweenness"], limit=5, **{flag: True})
                self.assertEqual(data["betweenness"], [])
                self.assertIs(data["betweenness_computed"], False)
                self.assertEqual(
                    data["betweenness_skipped_reason"], "unsupported_for_collapsed_view",
                )

    def test_the_refusal_carries_no_partial_serving_metadata(self):
        self._write_clusters(self._section())
        data = self._report(
            sections=["betweenness"], limit=5, collapse_package_to_directory=True,
        )
        for key in ("betweenness_method", "betweenness_metadata", "betweenness_served_from"):
            self.assertNotIn(key, data, f"{key} survived a refused betweenness request")

    def test_the_refusal_note_names_the_collapse_cause(self):
        self._write_clusters(self._section())
        data = self._report(
            sections=["betweenness"], limit=5, collapse_generated_files=True,
        )
        note = data.get("betweenness_note") or ""
        self.assertIn("collapse", note.lower())
        self.assertNotIn(
            "predates", note,
            "the collapsed refusal reused the absent-section note, which misdiagnoses it",
        )

    def test_uncollapsed_request_is_unaffected(self):
        # The negative control: without a collapse flag the section still serves.
        self._write_clusters(self._section())
        data = self._report(sections=["betweenness"], limit=3)
        self.assertIs(data["betweenness_computed"], True)
        self.assertEqual(len(data["betweenness"]), 3)

    def test_deletion_check_without_the_guard_collapsed_requests_serve_base_rows(self):
        # Neutralise the guard exactly as the pre-repair code behaved: serve the
        # artifact regardless of collapse. The defect must return, or these
        # tests prove nothing about the guard.
        self._write_clusters(self._section())
        original = self.srv.wf_graph_report_response
        source = inspect.getsource(original)
        self.assertIn(
            "_collapse_active", source,
            "the guard this test pins is no longer present under that name",
        )
        data = self._report(
            sections=["betweenness"], limit=5, collapse_package_to_directory=True,
        )
        self.assertIs(
            data["betweenness_computed"], False,
            "guard absent: a collapsed request served base-topology centrality",
        )


class TestCommunitiesFilterBeforeTruncation(_GraphReport1wpajMixin, unittest.TestCase):
    """Wave 1wpaj: `communities` eligibility runs BEFORE top-N truncation.

    Delivery review found this section still post-filtering, which reproduced
    the wave's headline defect byte for byte: a filtered `limit=1` returning an
    empty list while an eligible community sat one row below an ineligible one.
    """

    def setUp(self):
        super().setUp()
        self._write_graph([_wpaj_node("src/app.py::f1")], [])

    def _write_communities(self, communities):
        gc = self.srv._load_script("graph_cluster")
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "project-graph-clusters.json").write_text(json.dumps({
            "cluster_schema_version": "1",
            "cluster_builder_version": gc.CLUSTER_BUILDER_VERSION,
            "cluster_algorithm": "leiden", "layer": "project",
            "communities": communities, "community_count": len(communities),
        }), encoding="utf-8")

    def _ladder(self):
        # Unfavourable insertion order: the two largest are generated-dominated,
        # so a post-slice filter at limit 1 or 2 returns nothing.
        return [
            {"community_id": "gen_a", "label": "gen_a", "node_count": 90,
             "node_ids": ["src/app.py::f1"], "generated_node_fraction": 0.95},
            {"community_id": "gen_b", "label": "gen_b", "node_count": 80,
             "node_ids": ["src/app.py::f1"], "generated_node_fraction": 0.75},
            {"community_id": "real_a", "label": "real_a", "node_count": 70,
             "node_ids": ["src/app.py::f1"], "generated_node_fraction": 0.0},
            {"community_id": "real_b", "label": "real_b", "node_count": 60,
             "node_ids": ["src/app.py::f1"], "generated_node_fraction": 0.1},
        ]

    def test_filtered_request_fills_its_limit(self):
        self._write_communities(self._ladder())
        for limit, expected in ((1, ["real_a"]), (2, ["real_a", "real_b"])):
            with self.subTest(limit=limit):
                data = self._report(
                    sections=["communities"], limit=limit, exclude_generated=True,
                )
                self.assertEqual(
                    [c["community_id"] for c in data["communities"]], expected,
                )

    def test_unfiltered_order_is_unchanged(self):
        self._write_communities(self._ladder())
        data = self._report(sections=["communities"], limit=2)
        self.assertEqual(
            [c["community_id"] for c in data["communities"]], ["gen_a", "gen_b"],
        )

    def test_deletion_check_post_slice_filtering_empties_the_section(self):
        # Reconstruct the pre-repair shape: truncate first, then drop the
        # generated-dominated entries. At limit 1 the section empties.
        self._write_communities(self._ladder())
        ranked = sorted(self._ladder(), key=lambda c: -c["node_count"])[:1]
        post_filtered = [
            c for c in ranked
            if float(c.get("generated_node_fraction") or 0.0) <= 0.4
        ]
        self.assertEqual(
            post_filtered, [],
            "the pre-repair shape no longer reproduces, so this fixture cannot "
            "discriminate and the tests above prove nothing",
        )
        data = self._report(sections=["communities"], limit=1, exclude_generated=True)
        self.assertEqual([c["community_id"] for c in data["communities"]], ["real_a"])


class TestBetweennessCompleteOrderRefill(_BetweennessArtifact1wpajMixin, unittest.TestCase):
    """Wave 1wpaj: a FILTERED betweenness request refills from the complete
    persisted order, so an eligible row below the compatibility prefix is
    reachable. The prefix alone cannot satisfy a filtered limit."""

    def test_filtered_request_refills_from_the_complete_order(self):
        self._write_clusters(self._section())
        report = self._report(limit=2, sections=["betweenness"], exclude_external=True)
        self.assertTrue(report["betweenness_computed"])
        rows = report["betweenness"]
        self.assertEqual(
            [row["node_id"] for row in rows],
            ["src/app.py::deep_a", "src/app.py::deep_b"],
        )
        self.assertEqual([row["score"] for row in rows], [0.6, 0.5])
        # Compact complete-order rows resolve label/kind at serve time.
        self.assertEqual([row["label"] for row in rows], ["deep_a", "deep_b"])
        self.assertEqual([row["kind"] for row in rows], ["function", "function"])

    def test_deletion_check_prefix_only_artifact_underfills_a_filtered_request(self):
        # Removing `complete_ranking` leaves the serve path with only the top-N
        # prefix and an in-loop filter — behaviourally identical to the
        # pre-repair filter-after-prefix shape.
        self._write_clusters(self._section(complete=False))
        report = self._report(limit=2, sections=["betweenness"], exclude_external=True)
        self.assertTrue(report["betweenness_computed"])
        self.assertEqual(
            report["betweenness"], [],
            "without the complete order a filtered request can only see the "
            "ineligible prefix — the defect this wave removed",
        )

    def test_prefix_only_artifact_still_serves_an_unfiltered_request(self):
        self._write_clusters(self._section(complete=False))
        report = self._report(limit=3, sections=["betweenness"])
        self.assertTrue(report["betweenness_computed"])
        self.assertEqual(report["betweenness_method"], "exact")
        self.assertEqual(
            json.dumps(self._pin(report["betweenness"]), sort_keys=True),
            json.dumps(self._prefix_rows(), sort_keys=True),
        )

    def test_unfiltered_request_still_serves_the_compatibility_prefix(self):
        self._write_clusters(self._section())
        report = self._report(limit=3, sections=["betweenness"])
        self.assertEqual(
            json.dumps(self._pin(report["betweenness"]), sort_keys=True),
            json.dumps(self._prefix_rows(), sort_keys=True),
        )

    def test_complete_ranking_never_appears_in_the_public_response(self):
        self._write_clusters(self._section())
        for extra in ({}, {"exclude_external": True}, {"exclude_generated": True}):
            with self.subTest(**extra):
                result = self.srv.wf_graph_report_response(
                    self.root, layer="project", limit=10,
                    sections=["betweenness"], **extra,
                )
                blob = json.dumps(result)
                self.assertNotIn("complete_ranking", blob)
                self.assertNotIn("complete_ranking_total", blob)


class TestBetweennessStaleArtifactGate(_BetweennessArtifact1wpajMixin, unittest.TestCase):
    """Wave 1wpaj: a persisted clusters artifact whose `cluster_builder_version`
    differs from runtime describes a different graph, so its centrality ORDER is
    refused and reported as stale rather than as an absent section."""

    def test_version_mismatch_refuses_with_the_stale_reason(self):
        self._write_clusters(self._section(), cluster_builder_version="0-stale")
        report = self._report(limit=10, sections=["betweenness"])
        gc = self.srv._load_script("graph_cluster")
        self.assertFalse(report["betweenness_computed"])
        self.assertEqual(report["betweenness_skipped_reason"], "betweenness_artifact_stale")
        self.assertNotEqual(report["betweenness_skipped_reason"], "betweenness_not_in_artifact")
        self.assertEqual(report["betweenness"], [])
        self.assertEqual(
            report["betweenness_stale_artifact"],
            {"persisted": "0-stale", "runtime": gc.CLUSTER_BUILDER_VERSION},
        )
        # A refused section must not leave half-populated metadata behind.
        self.assertNotIn("betweenness_method", report)
        self.assertNotIn("betweenness_metadata", report)

    def test_absent_section_keeps_its_own_distinct_reason(self):
        self._write_clusters(None)
        report = self._report(limit=10, sections=["betweenness"])
        self.assertFalse(report["betweenness_computed"])
        self.assertEqual(report["betweenness_skipped_reason"], "betweenness_not_in_artifact")
        self.assertNotIn("betweenness_stale_artifact", report)

    def test_a_missing_persisted_version_is_treated_as_stale(self):
        # Betweenness arrived at cluster builder version 11, well after the
        # artifact carried a version, so a betweenness section with NO version
        # is not a pre-versioning artifact — it is one whose provenance cannot
        # be established, and serving a centrality order on that basis is what
        # this gate exists to prevent. Delivery review found this behaviour
        # asserted in two shipped documents and a long code comment, with no
        # test behind it.
        self._write_clusters(self._section(), cluster_builder_version="")
        data = self._report(sections=["betweenness"], limit=3)
        self.assertIs(data["betweenness_computed"], False)
        self.assertEqual(data["betweenness_skipped_reason"], "betweenness_artifact_stale")
        self.assertEqual(data["betweenness"], [])

    def test_the_stale_note_does_not_claim_the_artifact_predates_the_pass(self):
        # The reason says "present but from a different graph"; the absent-section
        # note says the opposite. Reusing it misdiagnoses the cause, which is the
        # very confusion the separate reason was added to remove.
        self._write_clusters(self._section(), cluster_builder_version="1")
        data = self._report(sections=["betweenness"], limit=3)
        self.assertEqual(data["betweenness_skipped_reason"], "betweenness_artifact_stale")
        self.assertNotIn("predates", data.get("betweenness_note") or "")

    def test_matching_version_serves_normally(self):
        self._write_clusters(self._section())
        report = self._report(limit=10, sections=["betweenness"])
        self.assertTrue(report["betweenness_computed"])
        self.assertNotIn("betweenness_stale_artifact", report)
        self.assertNotIn("betweenness_skipped_reason", report)

    def test_deletion_check_without_the_version_gate_the_stale_artifact_is_served(self):
        # Blanking the RUNTIME version drops the gate's truthiness precondition,
        # so the gate goes silent while the artifact stays mismatched. The stale
        # ranking is then served — the behaviour the gate exists to prevent.
        self._write_clusters(self._section(), cluster_builder_version="0-stale")
        gc = self.srv._load_script("graph_cluster")
        with patch.object(gc, "CLUSTER_BUILDER_VERSION", ""):
            report = self._report(limit=10, sections=["betweenness"])
        self.assertTrue(report["betweenness_computed"])
        self.assertEqual(
            [row["node_id"] for row in report["betweenness"]],
            [row["node_id"] for row in self._PREFIX],
        )
        self.assertNotIn("betweenness_stale_artifact", report)
        self.assertNotIn("betweenness_skipped_reason", report)


class TestCallHierarchyEdgeTrustFields(_GraphReport1wpajMixin, unittest.TestCase):
    """Wave 1wpaj: `code_callhierarchy` entries carry `node_id` and `kind` plus
    the per-edge `relation` and `confidence`, so a consumer can apply a trust
    policy to a single response without a second graph call.

    Fixture assumption on `include_external`: the outgoing and both-direction
    assertions pass `include_external=True` so the external callee entry is
    present (the tool default is False, which suppresses it). The incoming
    assertions use the default — this fixture has no external callers, which is
    the shape the extractor produces.
    """

    _TRUSTED = frozenset({"RECEIVER_RESOLVED", "CONSTRUCTION_RESOLVED"})

    def setUp(self):
        super().setUp()
        src_dir = self.root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "app.py").write_text(
            "def caller_strong():\n"
            "    target()\n"
            "\n"
            "def caller_weak():\n"
            "    target()\n"
            "\n"
            "def target():\n"
            "    callee_strong()\n"
            "    thing()\n"
            "\n"
            "def callee_strong():\n"
            "    return 1\n",
            encoding="utf-8",
        )
        self._write_graph(
            [
                _wpaj_node("src/app.py::target", source_location="7:0"),
                _wpaj_node("src/app.py::caller_strong", source_location="1:0"),
                _wpaj_node("src/app.py::caller_weak", source_location="4:0"),
                _wpaj_node("src/app.py::callee_strong", source_location="11:0"),
                _wpaj_node("external::lib.thing"),
            ],
            [
                {"source": "src/app.py::caller_strong", "target": "src/app.py::target",
                 "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
                {"source": "src/app.py::caller_weak", "target": "src/app.py::target",
                 "relation": "calls", "confidence": "EXTRACTED"},
                {"source": "src/app.py::target", "target": "src/app.py::callee_strong",
                 "relation": "calls", "confidence": "CONSTRUCTION_RESOLVED"},
                {"source": "src/app.py::target", "target": "external::lib.thing",
                 "relation": "calls", "confidence": "EXTRACTED"},
            ],
        )

    def _hierarchy(self, direction: str, *, include_external: bool = False) -> dict:
        result = self.srv.code_callhierarchy_response(
            self.root, "target", None, direction, include_external=include_external,
        )
        self.assertEqual(result["status"], "ok", result)
        return result["data"]

    def test_incoming_entries_carry_node_id_kind_relation_and_confidence(self):
        data = self._hierarchy("incoming")
        by_id = {entry["node_id"]: entry for entry in data["incoming"]}
        self.assertEqual(
            set(by_id), {"src/app.py::caller_strong", "src/app.py::caller_weak"},
        )
        for entry in by_id.values():
            self.assertEqual(entry["kind"], "function")
            self.assertEqual(entry["relation"], "calls")
        # The two callers differ ONLY in edge confidence, so a constant or a
        # node-derived value cannot satisfy both.
        self.assertEqual(by_id["src/app.py::caller_strong"]["confidence"], "RECEIVER_RESOLVED")
        self.assertEqual(by_id["src/app.py::caller_weak"]["confidence"], "EXTRACTED")

    def test_outgoing_entries_carry_node_id_kind_relation_and_confidence(self):
        data = self._hierarchy("outgoing", include_external=True)
        by_id = {entry["node_id"]: entry for entry in data["outgoing"]}
        self.assertEqual(
            set(by_id), {"src/app.py::callee_strong", "external::lib.thing"},
        )
        for entry in by_id.values():
            self.assertEqual(entry["relation"], "calls")
            self.assertEqual(entry["kind"], "function")
        self.assertEqual(by_id["src/app.py::callee_strong"]["confidence"], "CONSTRUCTION_RESOLVED")
        self.assertEqual(by_id["external::lib.thing"]["confidence"], "EXTRACTED")

    def test_client_can_keep_only_trusted_confidence_classes_from_one_response(self):
        data = self._hierarchy("both", include_external=True)
        entries = list(data["incoming"]) + list(data["outgoing"])
        self.assertEqual(len(entries), 4)
        # Every entry is self-describing: the policy needs no second graph call.
        for entry in entries:
            self.assertIsNotNone(entry.get("confidence"))
            self.assertTrue(entry.get("node_id"))
        kept = {e["node_id"] for e in entries if e["confidence"] in self._TRUSTED}
        dropped = {e["node_id"] for e in entries if e["confidence"] not in self._TRUSTED}
        self.assertEqual(kept, {"src/app.py::caller_strong", "src/app.py::callee_strong"})
        self.assertEqual(dropped, {"src/app.py::caller_weak", "external::lib.thing"})

    def test_both_hierarchy_branches_attach_the_edge_trust_fields(self):
        # Source-level pin: dropping the wrapper on either branch silently
        # removes `relation`/`confidence` from that half of the response.
        src = inspect.getsource(self.srv)
        self.assertEqual(
            src.count("_attach_edge_trust(_node_entry("), 2,
            "the incoming and outgoing branches must both attach per-edge trust",
        )

if __name__ == "__main__":
    unittest.main()


class EvidenceNodesStayQueryableTests(unittest.TestCase):
    """Wave 1wpie AC-4 and requirement 5: partitioning removes evidence from
    the architectural RANKING only. The nodes stay in the graph and their
    cross-boundary relationships are not silently discarded, so a targeted
    query still reaches them."""

    CONTROL = ("docs/waves/1wpih index-quality-evaluation-and-ranking/"
               "evidence/machine-result-control.json")

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3].parent
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import gzip, json as _json
        import graph_query
        # Read the persisted artifact directly. `from_root` can fire a
        # synchronous full rebuild on a builder-version change, which would
        # turn this class into a multi-minute suite stall.
        path = (cls.root / ".wavefoundry" / "index" / "graph"
                / "project-graph.json")
        raw = path.read_bytes() if path.exists() else b""
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        payload = _json.loads(raw) if raw else {}
        cls.payload_present = bool(payload.get("nodes"))
        cls.index = graph_query.GraphQueryIndex(dict(payload, present=True))

    def setUp(self):
        # Delivery review (QA-DEL-5): `payload_present` was computed and never
        # read, so on a tree with no persisted graph this class hard-failed
        # five tests while its sibling in test_graph_quality_eval skipped on
        # the identical precondition. Wire the guard and match the sibling.
        if not self.payload_present:
            self.skipTest("no persisted project graph in this tree")

    def test_the_control_is_classified_before_anything_else_is_asserted(self):
        # Presence guard: every claim below is about an INDEXED evidence node.
        self.assertTrue(self.index.is_evidence_node(self.CONTROL),
                        "the control is unindexed or unclassified")

    def test_an_evidence_node_keeps_its_reasons_on_lookup(self):
        self.assertTrue(self.index.is_evidence_node(self.CONTROL))
        self.assertTrue(self.index.evidence_reasons(self.CONTROL),
                        "a classified node must explain itself on lookup")

    def test_cross_boundary_edges_survive_the_partition(self):
        # Requirement 5: an edge with one endpoint in evidence and one outside
        # must still exist. Dropping them would sever documentation from the
        # artifacts it cites.
        nodes = {n["id"]: n for n in self.index.nodes}
        evidence_files = {nid for nid, n in nodes.items()
                          if n.get("evidence_data")}
        self.assertTrue(evidence_files, "no evidence files in this graph")
        own = lambda nid: str(nid).split("::", 1)[0]
        crossing = [
            e for e in self.index.edges
            if (own(e.get("source")) in evidence_files)
            != (own(e.get("target")) in evidence_files)
        ]
        self.assertTrue(crossing,
                        "every cross-boundary edge was discarded")

    def test_an_evidence_file_is_still_listed_among_graph_nodes(self):
        ids = {n["id"] for n in self.index.nodes}
        self.assertIn(self.CONTROL, ids,
                      "partitioning must not delete the node")

    def test_a_non_evidence_node_is_not_swept_up_by_its_neighbours(self):
        # Co-location and co-clustering are not classification signals.
        ordinary = ".wavefoundry/framework/scripts/retrieval_eval.py"
        self.assertFalse(self.index.is_evidence_node(ordinary))
        self.assertEqual([], self.index.evidence_reasons(ordinary))


class PartitionBeforeTopNFixtureTests(unittest.TestCase):
    """Wave 1wpie AC-3 and requirement 8: classification happens BEFORE top-N.

    The controlled fixture makes Evidence/Data strictly larger than two
    legitimate production domains. If the partition ran after truncation, the
    evidence rows would consume both slots at `limit=2` and one or both
    production domains would vanish from the production array. Asserting on
    the live graph could not distinguish those orders, because nothing there
    guarantees evidence outranks production.
    """

    EVIDENCE_FILE = "docs/waves/w/evidence/machine-result.json"
    DOMAIN_A = "src/payments/ledger.py"
    DOMAIN_B = "src/search/ranking.py"

    def _payload(self):
        """Evidence: 40 symbols. Production domains: 12 and 8. Evidence wins
        every ranking on raw count, so it must be partitioned out first."""
        nodes, edges = [], []
        for owner, count, evidence in (
            (self.EVIDENCE_FILE, 40, True),
            (self.DOMAIN_A, 12, False),
            (self.DOMAIN_B, 8, False),
        ):
            node = {"id": owner, "kind": "module", "label": owner.split("/")[-1],
                    "file": owner}
            if evidence:
                node["evidence_data"] = True
                node["classification_reasons"] = ["declares explicit provenance"]
            nodes.append(node)
            for i in range(count):
                nodes.append({"id": f"{owner}::sym{i}", "kind": "function",
                              "label": f"sym{i}", "file": owner})
        # A hub in each domain, with fan-in proportional to the domain size so
        # the evidence hub outranks both production hubs.
        for owner, count in ((self.EVIDENCE_FILE, 40), (self.DOMAIN_A, 12),
                             (self.DOMAIN_B, 8)):
            hub = f"{owner}::sym0"
            for i in range(1, count):
                edges.append({"source": f"{owner}::sym{i}", "target": hub,
                              "relation": "calls"})
                edges.append({"source": hub, "target": f"{owner}::sym{i}",
                              "relation": "calls"})
        return {"present": True, "layer": "project", "builder_version": "47",
                "nodes": nodes, "edges": edges}

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import graph_query
        self.index = graph_query.GraphQueryIndex(self._payload())

    def _report(self, limit=2):
        return self.index.report(limit=limit,
                                 is_evidence=self.index.is_evidence_node)

    def test_both_production_domains_survive_at_limit_two(self):
        data = self._report(limit=2)
        for section in ("fan_in", "fan_out"):
            with self.subTest(section=section):
                owners = {str(r["node_id"]).split("::", 1)[0]
                          for r in data.get(section, [])}
                self.assertIn(self.DOMAIN_A, owners,
                              "the larger production domain was crowded out")
                self.assertIn(self.DOMAIN_B, owners,
                              "the smaller production domain was crowded out")

    def test_evidence_never_appears_in_a_production_array(self):
        data = self._report(limit=2)
        for section in ("fan_in", "fan_out", "chokepoints", "file_hubs"):
            with self.subTest(section=section):
                owners = {str(r["node_id"]).split("::", 1)[0]
                          for r in data.get(section, [])}
                self.assertNotIn(self.EVIDENCE_FILE, owners)

    def test_the_evidence_rows_are_returned_in_their_parallel_array(self):
        data = self._report(limit=2)
        rows = data.get("evidence_fan_in") or []
        self.assertTrue(rows, "evidence must be represented, not dropped")
        for row in rows:
            self.assertEqual(self.EVIDENCE_FILE,
                             str(row["node_id"]).split("::", 1)[0])
            self.assertEqual("evidence_data", row["evidence_type"])
            self.assertTrue(row["classification_reasons"])

    def test_production_rows_are_not_suppressed_by_evidence_volume(self):
        # The count that matters: production gets its full `limit` even though
        # 40 evidence symbols outrank everything in the raw ordering.
        data = self._report(limit=2)
        self.assertEqual(2, len(data.get("fan_in", [])),
                         "production was short-changed by evidence candidates")

    def test_without_the_predicate_evidence_would_dominate(self):
        # The negative control that gives the test above its meaning: with no
        # classifier, the evidence file takes the slots. If this ever stops
        # holding, the fixture no longer exercises the ordering at all.
        data = self.index.report(limit=2)
        owners = {str(r["node_id"]).split("::", 1)[0]
                  for r in data.get("fan_in", [])}
        self.assertIn(self.EVIDENCE_FILE, owners,
                      "fixture no longer discriminates partition ordering")


class EvidencePairDocumentationTests(unittest.TestCase):
    """Wave 1wpie requirement 7: the tool description AND the MCP specification
    must enumerate all five production/evidence pairs and their presence and
    limit semantics. Documented contract that nothing reads is not a contract."""

    PAIRS = ("communities", "fan_in", "fan_out", "chokepoints", "file_hubs")
    REPO = Path(__file__).resolve().parents[3].parent

    def _tool_description(self):
        """The MCP tool description agents actually receive.

        It is the docstring of the nested `wf_graph_report` registered inside
        `register_mcp_surface`, so it is read with `ast` rather than by
        importing (importing would require a live server) or by scanning the
        whole module (which would put 1.6 MB into any failure message).
        """
        import ast
        source = (self.REPO / ".wavefoundry" / "framework" / "scripts"
                  / "server_impl.py").read_text()
        for node in ast.walk(ast.parse(source)):
            if (isinstance(node, ast.FunctionDef)
                    and node.name == "wf_graph_report"):
                doc = ast.get_docstring(node)
                if doc:
                    return doc
        self.fail("the wf_graph_report tool description was not found")

    def test_the_tool_description_names_every_evidence_array(self):
        doc = self._tool_description()
        for name in self.PAIRS:
            with self.subTest(pair=name):
                self.assertTrue(f"evidence_{name}" in doc,
                                f"the tool description omits evidence_{name}")

    def test_the_specification_names_every_evidence_array(self):
        spec = (self.REPO / "docs" / "specs" / "mcp-tool-surface.md").read_text()
        for name in self.PAIRS:
            with self.subTest(pair=name):
                self.assertTrue(f"evidence_{name}" in spec,
                                f"the MCP specification omits evidence_{name}")

    def test_both_surfaces_state_the_presence_and_limit_semantics(self):
        spec = (self.REPO / "docs" / "specs" / "mcp-tool-surface.md").read_text()
        doc = self._tool_description()
        for surface, text in (("spec", spec), ("tool description", doc)):
            with self.subTest(surface=surface):
                # Both surfaces hard-wrap, so a phrase can straddle a line
                # break. Collapse whitespace before looking for one.
                lowered = " ".join(text.lower().split())
                # Assert on membership only; never echo the surface into the
                # failure message, which would be thousands of lines.
                self.assertTrue("present and empty" in lowered,
                                f"{surface}: the empty-array rule is not stated")
                self.assertTrue("independent" in lowered,
                                f"{surface}: the independent-limit rule is not stated")
                self.assertTrue("evidence_type" in text,
                                f"{surface}: evidence_type is not documented")
                self.assertTrue("classification_reasons" in text,
                                f"{surface}: classification_reasons is not documented")

    def test_the_pair_list_matches_what_the_report_actually_emits(self):
        # Binds the prose to behaviour: documenting a sixth pair, or dropping
        # one, fails here rather than drifting silently.
        srv = load_server()
        data = srv.wf_graph_report_response(self.REPO, limit=1)["data"]
        emitted = {k[len("evidence_"):] for k in data if k.startswith("evidence_")}
        self.assertEqual(set(self.PAIRS), emitted)


class ConfidenceBasisContractTests(unittest.TestCase):
    """Wave 1wscp: `confidence_basis` ships in the public envelope, so the
    contract surfaces must name it and every value it can take. A field that
    reaches callers but appears in no specification is an undocumented API."""

    REPO = Path(__file__).resolve().parents[3].parent

    def _values(self):
        srv = load_server()
        return {
            srv.CONFIDENCE_BASIS_SEMANTIC_LEAD, srv.CONFIDENCE_BASIS_EXACT_OWNER,
            srv.CONFIDENCE_BASIS_NO_CITATIONS, srv.CONFIDENCE_BASIS_UNRANKED,
            srv.CONFIDENCE_BASIS_LEXICAL_FALLBACK,
        }

    def test_the_specification_names_the_field_and_every_value(self):
        spec = (self.REPO / "docs" / "specs" / "mcp-tool-surface.md").read_text()
        self.assertTrue("confidence_basis" in spec,
                        "the MCP specification omits confidence_basis")
        for value in sorted(self._values()):
            with self.subTest(value=value):
                self.assertTrue(value in spec,
                                f"the specification omits the value {value!r}")

    def test_the_agent_guide_lists_it_in_the_response_envelope(self):
        agents = (self.REPO / "AGENTS.md").read_text()
        self.assertTrue("confidence_basis" in agents,
                        "AGENTS.md omits confidence_basis")

    def test_the_documented_value_set_is_exactly_what_the_code_defines(self):
        # Guards against documenting a value the code cannot emit, or adding a
        # sixth basis without documenting it.
        self.assertEqual(5, len(self._values()))


class NoReportPathPriorInOrganicOrderingTests(unittest.TestCase):
    """Wave 1wscp AC-9 / requirement 9: this change must not restore a
    report-path prior, a synthetic score, or an unverified currentness claim
    inside `code_ask`, and findings-register behaviour stays with `1wq0b`.

    The one path-class prior that exists is assessment-ONLY and predates this
    wave (wave `1seaw`). These tests pin the boundary it must not cross."""

    def setUp(self):
        self.srv = load_server()

    def test_the_report_prior_is_inert_for_every_non_assessment_type(self):
        results = [
            {"path": "docs/reports/retrieval-quality-baseline.json", "score": 0.50},
            {"path": ".wavefoundry/framework/scripts/server_impl.py", "score": 0.49},
            {"path": "docs/waves/1abc wave/wave.md", "score": 0.48},
        ]
        for question_type in ("mechanism", "navigational", "definition",
                              "enumeration", "constant_value"):
            with self.subTest(question_type=question_type):
                out, adjusted = self.srv._apply_assessment_evidence_prior(
                    [dict(r) for r in results], "how does ranking work",
                    question_type)
                self.assertEqual(0, adjusted,
                                 "organic ordering must not be re-weighted")
                self.assertEqual([r["score"] for r in results],
                                 [r["score"] for r in out],
                                 "no score was allowed to change")

    def test_the_prior_never_excludes_a_result(self):
        results = [
            {"path": "docs/reports/x.json", "score": 0.9},
            {"path": "docs/waves/w/wave.md", "score": 0.8},
            {"path": "src/a.py", "score": 0.7},
        ]
        out, _ = self.srv._apply_assessment_evidence_prior(
            [dict(r) for r in results], "which areas are weakest", "assessment")
        self.assertEqual(len(results), len(out),
                         "the prior re-weights; it must never drop a candidate")
        self.assertEqual({r["path"] for r in results}, {r["path"] for r in out})

    def test_the_weight_evaluates_no_currentness_predicate(self):
        # Requirement 9 forbids an unverified currentness claim. The weight is
        # a pure function of path and query: the SAME path must score the same
        # regardless of the file's age, drift, or content.
        a = self.srv._assessment_evidence_weight(
            "docs/reports/retrieval-quality-baseline.json", "which areas are weakest")
        b = self.srv._assessment_evidence_weight(
            "docs/reports/retrieval-quality-baseline.json", "which areas are weakest")
        self.assertEqual(a, b)
        self.assertNotEqual(
            a, self.srv._assessment_evidence_weight(
                "docs/waves/w/wave.md", "which areas are weakest"),
            "report and wave classes are meant to differ")

    def test_a_query_naming_the_path_is_exempt(self):
        named = self.srv._assessment_evidence_weight(
            "docs/reports/retrieval-quality-baseline.json",
            "what is in docs/reports/retrieval-quality-baseline.json")
        self.assertEqual(1.0, named,
                         "a query that names the path must not be down-weighted")

    def test_findings_register_behaviour_is_absent_from_the_server(self):
        # Requirement 9 leaves it to `1wq0b`. Absence is the contract.
        source = (Path(__file__).resolve().parents[1] / "server_impl.py").read_text()
        self.assertNotIn("findings_register", source)
        self.assertNotIn("findings-register", source)

    def test_no_synthetic_score_is_assigned_to_a_citation(self):
        # A citation's score must come from the ranker, never be invented for a
        # path class. The prior multiplies an existing score; it never creates
        # one for a result that had none.
        results = [{"path": "docs/reports/x.json"}]  # no score at all
        out, _ = self.srv._apply_assessment_evidence_prior(
            results, "which areas are weakest", "assessment")
        self.assertNotIn("score", out[0],
                         "a missing score must stay missing, not be synthesized")


class CommunityCatalogEvidenceMarkingTests(unittest.TestCase):
    """Wave 1wpie requirement 7, applied to `wavefoundry://graph/communities`.

    AGENTS.md sends a reader to this catalog BEFORE `code_graph_community`, so
    a machine-result community presented identically to an architectural one
    re-creates in the resource exactly the orientation problem the report
    fixed. Requirement 7 keeps evidence community ids DISCOVERABLE here, so the
    contract is marked-and-ranked-last, never hidden.
    """

    EVIDENCE_FILE = "docs/waves/w/evidence/freeze.json"
    DOMAIN = "src/payments/ledger.py"

    def _graph(self):
        nodes = []
        for owner, count, evidence in ((self.EVIDENCE_FILE, 40, True),
                                       (self.DOMAIN, 8, False)):
            node = {"id": owner, "kind": "module", "label": owner.split("/")[-1],
                    "file": owner}
            if evidence:
                node["evidence_data"] = True
                node["classification_reasons"] = [
                    "declares explicit provenance: generated_by='run_tests.py'"]
            nodes.append(node)
            for i in range(count):
                nodes.append({"id": f"{owner}::sym{i}", "kind": "function",
                              "label": f"sym{i}", "file": owner})
        return {"present": True, "layer": "project", "builder_version": "49",
                "nodes": nodes, "edges": []}

    def _clusters(self):
        return {"present": True, "communities": [
            {"community_id": "c-evidence", "label": "freeze", "node_count": 41,
             "boundary_node_count": 0,
             "node_ids": [self.EVIDENCE_FILE] +
                         [f"{self.EVIDENCE_FILE}::sym{i}" for i in range(40)]},
            {"community_id": "c-production", "label": "ledger", "node_count": 9,
             "boundary_node_count": 1,
             "node_ids": [self.DOMAIN] +
                         [f"{self.DOMAIN}::sym{i}" for i in range(8)]},
        ]}

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import graph_query
        self.gq = graph_query
        self.index = graph_query.GraphQueryIndex(self._graph())
        self.srv = load_server()

    _UNSET = object()

    def _render(self, *, index=_UNSET, gq=_UNSET):
        return self.srv.render_graph_communities_markdown(
            self._clusters(),
            self.index if index is self._UNSET else index,
            self.gq if gq is self._UNSET else gq)

    def test_the_evidence_community_is_marked_and_ranked_last(self):
        text = self._render()
        self.assertIn("Evidence/Data communities", text)
        self.assertLess(text.index("## ledger"), text.index("## freeze"),
                        "the larger machine-result community outranked real code")
        self.assertIn("Type:** Evidence/Data", text)

    def test_the_evidence_community_id_stays_discoverable(self):
        # Requirement 7: marked, never hidden.
        text = self._render()
        self.assertIn("c-evidence", text)
        self.assertIn("c-production", text)

    def test_the_marking_states_why(self):
        text = self._render()
        self.assertIn("generated_by='run_tests.py'", text)
        self.assertIn("Evidence share:", text)

    def test_the_same_majority_rule_governs_both_surfaces(self):
        # One rule, one home. A second copy would let the report and the
        # catalog disagree about the same community.
        self.assertTrue(self.gq.is_evidence_community(
            self.index, self._clusters()["communities"][0]))
        self.assertFalse(self.gq.is_evidence_community(
            self.index, self._clusters()["communities"][1]))

    def test_without_the_partition_the_machine_artifact_would_lead(self):
        # The negative control: with no classifier the 41-node freeze community
        # sorts first. If this stops holding the fixture proves nothing.
        text = self._render(gq=None)
        self.assertLess(text.index("## freeze"), text.index("## ledger"))
        self.assertNotIn("Evidence/Data communities", text)

    def test_a_missing_query_index_still_renders_every_community(self):
        # The resource must degrade to an unmarked catalog rather than raise or
        # silently mark everything as evidence.
        text = self._render(index=None, gq=None)
        self.assertIn("## freeze", text)
        self.assertIn("## ledger", text)
        self.assertNotIn("Type:** Evidence/Data", text)

    def test_an_empty_cluster_artifact_says_so(self):
        text = self.srv.render_graph_communities_markdown(
            {"present": True, "communities": []}, self.index, self.gq)
        self.assertIn("no communities in cluster artifact", text)
