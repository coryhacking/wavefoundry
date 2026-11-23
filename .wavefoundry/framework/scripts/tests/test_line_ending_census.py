"""Wave 244in (change 244fj) AC-9, AC-10 and AC-14: the line-ending census.

The census (``line_ending_census_engine.py``) is the authoritative inventory
of framework writers.  Every writer function and every call to a ``wrapper``
has exactly one entry in ``tests/fixtures/line-ending-census.json``:

* ``in_place``: edits an existing file and publishes ``line_endings.merge``;
* ``in_place_raw``: a raw substitution inside existing lines, with a reason;
* ``generated``: writes LF bytes for a file the framework generates in full;
* ``wrapper``: writes caller-supplied content to a caller-named path; every
  call to it is keyed and classified on its own;
* ``exempt``: with a reason (binary payloads, process logs, pid files).

A ``generated`` entry pins its in-scope callers, and a caller that is itself
a writer needs a recorded ``writer_callers_reason``, so a function other
writers use to do their writing cannot hide behind ``generated`` (council
advisory at readiness): it must be a ``wrapper``.
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_ending_census_engine as engine  # noqa: E402

_FUNCTIONS = None


def _functions():
    global _FUNCTIONS
    if _FUNCTIONS is None:
        _FUNCTIONS = engine.scan_tree()
    return _FUNCTIONS


def _source(module: str) -> str:
    return (engine.SCRIPTS_ROOT / (module.replace(".", "/") + ".py")).read_text(encoding="utf-8")


class LineEndingCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = engine.load_table()

    def census(self, *, table=None, extra=None):
        functions = _functions() if extra is None else engine.scan_tree(extra_sources=extra)
        return engine.census(table or self.table, functions)

    def test_table_lives_in_the_fixture(self):
        self.assertEqual(engine.TABLE_PATH.name, "line-ending-census.json")
        self.assertEqual(engine.TABLE_PATH.parent.name, "fixtures")
        self.assertTrue(engine.TABLE_PATH.is_file())

    def test_scope_is_every_non_test_script_including_benchmarks(self):
        modules = {engine.module_name(path) for path in engine.iter_source_files()}
        self.assertIn("benchmarks.embed_bench", modules)
        self.assertIn("wf_server.server_impl", modules)
        self.assertFalse(any(module.startswith("tests.") for module in modules))

    def test_delivered_tree_has_no_census_failure(self):
        """AC-14: zero unclassified writers and wrapper call sites, no stale
        entry, every count current, every ``in_place`` writer merges and every
        text-mode write sets ``newline``."""
        report = self.census()
        self.assertEqual(report["failures"], [], "\n".join(report["failures"]))
        self.assertTrue(report["writers"])
        self.assertTrue(report["sites"])

    def test_generated_text_writes_are_lf(self):
        """AC-6, statically for every ``generated`` entry: each text-mode
        write passes ``newline="\\n"`` (no translation on any platform), or
        ``newline=""`` on LF content; bytes writes need no newline."""
        functions = _functions()
        checked = 0
        for key, entry in self.table["functions"].items():
            if entry["class"] != "generated":
                continue
            for prim in functions[key].primitives:
                if prim.text_mode is False:
                    continue
                checked += 1
                with self.subTest(key=key, line=prim.line):
                    self.assertIn(prim.newline_value, ("\n", ""))
        self.assertGreater(checked, 20)

    def test_known_writers_are_classified(self):
        """AC-10."""
        entries = self.table["functions"]
        in_place = [
            "wf_server.server_impl:wf_review_event_response.transact",
            "wf_server.server_impl:wf_prepare_wave_response",
            "wf_server.server_impl:_publish_prepare_policy_state",
            "wf_server.server_impl:_retain_review_escalation",
            "wf_server.server_impl:_write_handoff_text",
            "wf_server.server_impl:wf_implement_wave_response",
            "wf_server.server_impl:wf_close_wave_response",
            "wf_server.server_impl:wf_pause_wave_response",
            "wf_server.server_impl:wf_remove_change_response",
            "wf_server.server_impl:wf_reopen_wave_response",
            "wf_server.server_impl:wf_add_change_response",
            "wf_server.server_impl:_prepare_fix_heading_spacing",
            "wf_server.server_impl:wf_close_change_response",
            "wf_server.context_efficiency_handlers:_project_context_efficiency_wave",
            "memory_records:record_memory_validation",
            "memory_records:reconcile_memory_record",
            "memory_records:archive_memory_record",
            "memory_records:migrate_memory_ids_to_lifecycle_naming",
            "memory_records:migrate_memory_ids_to_lifecycle_naming._repair_text_file",
            "render_agent_surfaces:patch_thin_pointer",
            "render_agent_surfaces:render_agent_surfaces",
            "render_agent_surfaces:reconcile_context_efficiency_surface",
            "render_agent_surfaces:patch_root_bridge",
            "render_agent_surfaces:_repair_change_prompt_manifest",
            "render_agent_surfaces:_write_prompt_manifest",
            "render_agent_surfaces:render_agent_surfaces._tier3_write",
            "render_agent_surfaces:reconcile_review_protocol_surfaces",
            "render_agent_surfaces:reconcile_review_policy_surfaces",
            "render_platform_surfaces:_merge_mcp_server",
            "render_platform_surfaces:render_claude_settings",
            "render_platform_surfaces:render_claude_permissions",
            "render_platform_surfaces:render_gitignore_block",
            "render_platform_surfaces:render_gitattributes_block",
            "render_platform_surfaces:render_aiignore",
            "render_platform_surfaces:render_codex_mcp_config",
            "upgrade_extensions:_reconcile_docs_scalar_claims",
            "upgrade_extensions:_backfill_role_field_on_agent_docs",
            "upgrade_extensions:_strip_pycache_row_from_settings_file",
            "upgrade_extensions:_rewrite_legacy_config_keys",
            "upgrade_extensions:_repair_declaring_scaffold_on_path",
            "upgrade_wavefoundry:materialize_lifecycle_policy",
            "upgrade_wavefoundry:_stamp_manifest_revision",
            "setup_wavefoundry:_provision_workflow_defaults_if_absent",
            "review_policy_reconcile:reconcile_upgrade_policy_surface",
            "review_policy_upgrade:refresh_review_status_blocks",
            "docs_gardener:ensure_manifest",
            "gen_codebase_map:_refresh_repo_index_modules",
            "build_pack:_stamp_readme_version_badge",
            "build_pack:update_manifest_revision",
            "wave_lint_lib.secrets_validators:save_exceptions",
            "design_token_build:update_manifest_parity",
        ]
        for key in in_place:
            with self.subTest(key=key):
                self.assertEqual(entries.get(key, {}).get("class"), "in_place")
        raw = [
            "wf_server.server_impl:_mark_change_item_response",
            "docs_gardener:refresh_last_verified",
            "render_agent_surfaces:migrate_council_role_renames",
            "render_agent_surfaces:migrate_lifecycle_document_renames",
        ]
        for key in raw:
            with self.subTest(key=key):
                self.assertEqual(entries.get(key, {}).get("class"), "in_place_raw")
        for transform in ("_upsert_review_protocol_region", "_upsert_review_policy_region", "_merge_claude_agent"):
            with self.subTest(transform=transform):
                self.assertNotIn(f"render_agent_surfaces:{transform}", entries)
        self.assertFalse(any(key.endswith("_write_repo_text_platform_newlines") for key in entries))
        self.assertNotIn("_write_repo_text_platform_newlines", _source("render_agent_surfaces"))

    # -- AC-9 known-bad copies ---------------------------------------------
    def assert_failure(self, report, prefix, needle):
        hits = [f for f in report["failures"] if f.startswith(prefix) and needle in f]
        self.assertTrue(hits, f"expected {prefix} naming {needle!r}; got {report['failures']}")

    def test_bad_unclassified_write_text(self):
        extra = {"zz_bad_writer": "from pathlib import Path\n\ndef write(p):\n    Path(p).write_text('x', encoding='utf-8', newline='\\n')\n"}
        self.assert_failure(self.census(extra=extra), "UNCLASSIFIED ", "zz_bad_writer:write")

    def test_bad_new_caller_of_atomic_write_json(self):
        extra = {"zz_bad_json": "import upgrade_wavefoundry\n\ndef save(p):\n    upgrade_wavefoundry._atomic_write_json(p, {})\n"}
        report = self.census(extra=extra)
        self.assert_failure(report, "UNCLASSIFIED ", "zz_bad_json:save")
        self.assert_failure(report, "UNCLASSIFIED_SITE", "zz_bad_json:save -> upgrade_wavefoundry:_atomic_write_json #1")

    def test_bad_in_place_without_merge(self):
        source = _source("memory_records")
        needle = 'path.write_text(line_endings.merge(original, text), encoding="utf-8", newline="")\n    return path\n\n\ndef reconcile_memory_record'
        self.assertIn(needle, source)
        bad = source.replace(needle, needle.replace("line_endings.merge(original, text)", "text"), 1)
        # The same edit in the other writer keeps the module consistent.
        start = bad.index("def reconcile_memory_record")
        end = bad.index("def archive_eligibility")
        body = bad[start:end].replace("line_endings.merge(original, text)", "text")
        bad = bad[:start] + body + bad[end:]
        report = self.census(extra={"memory_records": bad})
        self.assert_failure(report, "IN_PLACE_WITHOUT_MERGE", "memory_records:reconcile_memory_record")

    def test_bad_second_write_in_classified_function(self):
        source = _source("wave_gate")
        needle = 'path.write_text(json.dumps(data, indent=2) + "\\n", encoding="utf-8", newline="\\n")'
        self.assertIn(needle, source)
        bad = source.replace(needle, needle + "\n    " + needle, 1)
        self.assert_failure(self.census(extra={"wave_gate": bad}), "COUNT", "wave_gate:_write")

    def test_bad_generated_write_without_newline(self):
        source = _source("wave_gate")
        needle = 'encoding="utf-8", newline="\\n")'
        bad = source.replace(needle, 'encoding="utf-8")', 1)
        self.assertNotEqual(bad, source)
        self.assert_failure(self.census(extra={"wave_gate": bad}), "NEWLINE_UNSET", "wave_gate:_write")

    def test_bad_stale_entry(self):
        table = copy.deepcopy(self.table)
        table["functions"]["wave_gate:_no_such_writer"] = {"class": "generated", "primitive_calls": 1, "wrapper_calls": 0}
        self.assert_failure(self.census(table=table), "STALE", "wave_gate:_no_such_writer")
        table = copy.deepcopy(self.table)
        site = next(iter(table["wrapper_call_sites"]))
        table["wrapper_call_sites"][site.replace("#1", "#99")] = {"class": "generated"}
        self.assert_failure(self.census(table=table), "STALE_SITE", "#99")

    def test_bad_from_import_callers_of_durable_json_replace(self):
        extra = {"zz_bad_from": (
            "from upgrade_lib import _durable_json_replace as djr\n\n"
            "def top(p):\n    djr(p, {})\n\n"
            "def local(p):\n    from upgrade_lib import _durable_json_replace\n    _durable_json_replace(p, {})\n"
        )}
        report = self.census(extra=extra)
        self.assert_failure(report, "UNCLASSIFIED ", "zz_bad_from:top")
        self.assert_failure(report, "UNCLASSIFIED ", "zz_bad_from:local")
        self.assert_failure(report, "UNCLASSIFIED_SITE", "zz_bad_from:local -> upgrade_lib:_durable_json_replace #1")

    def test_bad_carrier_caller_without_merge(self):
        extra = {"zz_bad_carrier": (
            "import render_agent_surfaces as ras\n\n"
            "def patch(root, path, text):\n"
            "    ras._write_review_carrier_text(path, ras._upsert_review_policy_region(text, ''), root=root)\n"
        )}
        report = self.census(extra=extra)
        self.assert_failure(report, "UNCLASSIFIED_SITE", "zz_bad_carrier:patch -> render_agent_surfaces:_write_review_carrier_text #1")
        table = copy.deepcopy(self.table)
        table["functions"]["zz_bad_carrier:patch"] = {"class": "in_place", "primitive_calls": 0, "wrapper_calls": 1}
        table["wrapper_call_sites"]["zz_bad_carrier:patch -> render_agent_surfaces:_write_review_carrier_text #1"] = {"class": "in_place"}
        report = self.census(table=table, extra=extra)
        self.assert_failure(report, "IN_PLACE_WITHOUT_MERGE", "zz_bad_carrier:patch")
        self.assert_failure(report, "IN_PLACE_SITE_WITHOUT_MERGE", "zz_bad_carrier:patch")

    def test_bad_in_place_caller_of_exempt_or_wrapper_shaped_writer(self):
        """Finding 244in-arch-exempt-wrapper-blindspot: a new in-place caller
        that publishes transformed text through a wrapper-shaped writer, or
        through any ``exempt`` writer, fails the census."""
        extra = {"zz_bad_exempt": (
            "from pathlib import Path\n"
            "import setup_readiness\n"
            "import upgrade_extensions\n"
            "import accel_embedder\n\n"
            "def stamp(p):\n"
            "    text = Path(p).read_text(encoding='utf-8').replace('a', 'b')\n"
            "    setup_readiness._write_stamp_exclusive(Path(p), text.encode())\n\n"
            "def journal(p):\n"
            "    upgrade_extensions._write_journal_exclusive(p, b'x', None)\n\n"
            "def ref(cache):\n"
            "    accel_embedder._ensure_ref_main(cache, 'org/name', 'abc')\n"
        )}
        report = self.census(extra=extra)
        self.assert_failure(report, "UNCLASSIFIED ", "zz_bad_exempt:stamp")
        self.assert_failure(report, "UNCLASSIFIED_SITE", "zz_bad_exempt:stamp -> setup_readiness:_write_stamp_exclusive #1")
        self.assert_failure(report, "UNCLASSIFIED_SITE", "zz_bad_exempt:journal -> upgrade_extensions:_write_journal_exclusive #1")
        self.assert_failure(report, "EXEMPT_CALLERS", "accel_embedder:_ensure_ref_main")
        self.assertEqual(self.table["functions"]["setup_readiness:_write_stamp_exclusive"]["class"], "wrapper")
        self.assertEqual(self.table["functions"]["upgrade_extensions:_write_journal_exclusive"]["class"], "wrapper")

    def test_bad_in_place_writer_with_translating_newline(self):
        """An ``in_place`` writer that passes ``newline="\\r\\n"`` rewrites every
        ending ``merge`` kept, so the census fails it."""
        source = _source("memory_records")
        start = source.index("def reconcile_memory_record")
        end = source.index("def archive_eligibility")
        body = source[start:end]
        self.assertIn('newline="")', body)
        bad = source[:start] + body.replace('newline="")', 'newline="\\r\\n")') + source[end:]
        self.assert_failure(self.census(extra={"memory_records": bad}), "IN_PLACE_NEWLINE",
                            "memory_records:reconcile_memory_record")

    def test_bad_wrapper_relabelled_generated(self):
        """Council advisory: a wrapper relabelled ``generated`` stops
        propagation, so every hidden caller must surface as a failure."""
        table = copy.deepcopy(self.table)
        key = "upgrade_lib:_durable_json_replace"
        self.assertEqual(table["functions"][key]["class"], "wrapper")
        table["functions"][key]["class"] = "generated"
        report = self.census(table=table)
        self.assert_failure(report, "GENERATED_CALLERS", key)
        self.assert_failure(report, "STALE", "upgrade_lib:write_upgrade_lock")


if __name__ == "__main__":
    unittest.main()
