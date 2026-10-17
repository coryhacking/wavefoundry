"""Tests for build_pack.py."""

import json
import os
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import build_pack  # noqa: E402
import model_bundle  # noqa: E402
import vocabulary_profile  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR / "tests"))
from record_layout_support import waves_dir  # noqa: E402

FAKE_PREFIX = "2tm5"
_QUALIFICATION_SECTION = "### Qualification\n\n- stub\n"
FAKE_VERSION = "1.0.0"


class BuildPackTests(unittest.TestCase):

    _ALLOWED_PACK_PREFIXES = (
        ".wavefoundry/framework/",
        ".wavefoundry/README.md",
        ".wavefoundry/CHANGELOG.md",
        # The only visible bootstrap file at the archive root. The live install
        # log is operator-owned state and must never ship in the pack.
        "install-wavefoundry.md",
    )

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _build(self, version=FAKE_VERSION, build_prefix=FAKE_PREFIX, extra_args=None):
        """Call build_pack.build_zip and return the resulting Path."""
        return build_pack.build_zip(self.tmp, version, build_prefix, write_version=False, update_manifest=False, inject_install_templates=False)

    def _zip_names(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            return zf.namelist()

    def _assert_pack_member_contract(self, names):
        self.assertNotIn(
            "wavefoundry-install-log.md",
            names,
            "the operator-owned live install log must never ship at the zip root",
        )
        for name in names:
            self.assertTrue(
                any(
                    name.startswith(prefix) or name == prefix
                    for prefix in self._ALLOWED_PACK_PREFIXES
                ),
                f"Entry does not start with expected prefix: {name}",
            )

    # ------------------------------------------------------------------
    # Filename format
    # ------------------------------------------------------------------

    def test_zip_filename_uses_semver_format(self):
        """Zip filename must be wavefoundry-MAJOR.MINOR.PATCH.<build>.zip."""
        path = self._build(version="1.0.0", build_prefix="2abc")
        self.assertEqual(path.name, "wavefoundry-1.0.0.2abc.zip")

    def test_standard_feature_package_contains_verification_manifest_without_model_payload(self):
        path = self._build()
        names = self._zip_names(path)
        manifest = ".wavefoundry/framework/model-set-verification-manifest.json"
        self.assertIn(manifest, names)
        self.assertIn(".wavefoundry/framework/MANIFEST", names)
        self.assertFalse(any(name.startswith("models/") for name in names))
        with zipfile.ZipFile(path) as archive:
            payload = json.loads(archive.read(manifest))
            package_manifest = archive.read(".wavefoundry/framework/MANIFEST").decode("utf-8")
        self.assertEqual(payload["model_set_version"], model_bundle.MODEL_SET_VERSION)
        self.assertIn("model-set-verification-manifest.json", package_manifest)

    def test_build_suffix_uses_rightmost_four_characters(self):
        self.assertEqual(build_pack._build_suffix("12tm5"), "2tm5")
        self.assertEqual(build_pack._build_suffix("abcd"), "abcd")

    # ------------------------------------------------------------------
    # Build suffix — standalone pure-time index (wave 1p9q0 AC-9)
    # ------------------------------------------------------------------

    def test_suffix_same_day_different_buckets_differ_and_order(self):
        from datetime import datetime, timezone
        a = build_pack.compute_build_suffix(datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc))
        b = build_pack.compute_build_suffix(datetime(2026, 7, 3, 10, 5, tzinfo=timezone.utc))
        self.assertNotEqual(a, b)
        self.assertLess(a, b)

    def test_suffix_multi_year_span_stays_monotonic_within_lap(self):
        from datetime import datetime, timedelta, timezone
        # Days 0 → 5,831 relative to a lap start cover the full ~16-yr lap.
        epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
        samples = [epoch + timedelta(days=d, hours=12) for d in (0, 100, 1000, 3000, 5831)]
        suffixes = [build_pack.compute_build_suffix(ts, epoch) for ts in samples]
        self.assertEqual(suffixes, sorted(suffixes))
        self.assertEqual(len(set(suffixes)), len(suffixes))

    def test_suffix_independent_of_lifecycle_policy(self):
        """The suffix must not read the repo lifecycle policy at all — a v2
        offset/epoch change never moves the build number."""
        from datetime import datetime, timezone
        import lifecycle_id
        ts = datetime(2026, 7, 3, 14, 23, tzinfo=timezone.utc)
        expected = build_pack.compute_build_suffix(ts)
        def _boom(*a, **k):
            raise AssertionError("build suffix must not read lifecycle policy")
        with patch.object(lifecycle_id, "load_lifecycle_policy", _boom):
            self.assertEqual(build_pack.compute_build_suffix(ts), expected)

    def test_suffix_value_identical_with_shipped_pack_lineage(self):
        """Pinned 1999-05-01 build epoch keeps the suffix value-identical with
        the pre-decoupling formula (last-4 of the v1 prefix on this epoch)."""
        from datetime import datetime, timezone
        import lifecycle_id
        ts = datetime(2026, 7, 3, 14, 23, tzinfo=timezone.utc)
        legacy = lifecycle_id.build_prefix(
            ts, policy=(build_pack.BUILD_EPOCH_UTC, 0))[-4:]
        self.assertEqual(build_pack.compute_build_suffix(ts), legacy)

    def test_suffix_min_width_four_after_lap_wrap(self):
        from datetime import datetime, timezone
        # 7 minutes after a lap start → packed value 1 → must still emit 4 chars.
        epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
        s = build_pack.compute_build_suffix(datetime(2026, 1, 1, 0, 7, tzinfo=timezone.utc), epoch)
        self.assertEqual(s, "0001")

    def test_suffix_rejects_pre_epoch_timestamp(self):
        from datetime import datetime, timezone
        with self.assertRaises(ValueError):
            build_pack.compute_build_suffix(datetime(1998, 1, 1, tzinfo=timezone.utc))

    def test_collision_warning_regex_is_width_tolerant(self):
        """The same-semver warning must keep firing if the suffix width ever
        changes — a `{4}` pin here went silently vacuous once before."""
        import io
        from contextlib import redirect_stderr
        out = self.tmp / "dist"
        out.mkdir()
        (out / "wavefoundry-9.9.9.abcde.zip").write_bytes(b"x")  # 5-char suffix
        err = io.StringIO()
        with redirect_stderr(err):
            build_pack._warn_on_same_semver_collision(out, "9.9.9")
        self.assertIn("existing pack(s) at version 9.9.9", err.getvalue())

    def test_pack_version_file_uses_plus_build_separator(self):
        """VERSION file uses MAJOR.MINOR.PATCH+<build> with '+' separator."""
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "stub.txt").write_text("stub", encoding="utf-8")
        path = build_pack.build_zip(
            self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=True, update_manifest=False, inject_install_templates=False
        )
        self.assertEqual(path.name, "wavefoundry-1.0.0.2tm5.zip")
        self.assertEqual((fw / "VERSION").read_text(encoding="utf-8"), "1.0.0+2tm5\n")
        with zipfile.ZipFile(path) as zf:
            member = ".wavefoundry/framework/VERSION"
            self.assertIn(member, zf.namelist())
            self.assertEqual(zf.read(member).decode(), "1.0.0+2tm5\n")

    def test_multi_digit_minor_version_in_filename(self):
        """1.10.0 must produce the correct filename (not confused with 1.1.0)."""
        path = self._build(version="1.10.0", build_prefix="2xyz")
        self.assertEqual(path.name, "wavefoundry-1.10.0.2xyz.zip")

    # ------------------------------------------------------------------
    # write_pack_version
    # ------------------------------------------------------------------

    def test_write_pack_version_stamps_plus_format(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        build_pack.write_pack_version(fw, "1.0.0", "2tm5")
        self.assertEqual((fw / "VERSION").read_text(encoding="utf-8"), "1.0.0+2tm5\n")

    # ------------------------------------------------------------------
    # Framework index removal (1p4ww)
    # ------------------------------------------------------------------

    def test_build_zip_does_not_ship_framework_index(self):
        # 1p4ww: the framework index is no longer built or shipped — the pack carries
        # framework SOURCE only (seeds/README fold into each project's docs index).
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seeds").mkdir()
        (fw / "seeds" / "010-install.prompt.md").write_text("seed", encoding="utf-8")
        path = build_pack.build_zip(
            self.tmp,
            "1.0.0",
            "12tm5",
            framework_dir=fw,
            write_version=True,
            update_manifest=False,
            inject_install_templates=False,
        )
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        self.assertFalse(any(".lance" in name for name in names))
        self.assertFalse(any("/framework/index/" in name for name in names))
        self.assertTrue(any(name.endswith("seeds/010-install.prompt.md") for name in names))

    # ------------------------------------------------------------------
    # Zip contents
    # ------------------------------------------------------------------

    def test_zip_is_non_empty(self):
        path = self._build()
        names = self._zip_names(path)
        self.assertGreater(len(names), 0)

    def test_all_entries_begin_with_wavefoundry_prefix(self):
        path = self._build()
        self._assert_pack_member_contract(self._zip_names(path))

    def test_phantom_root_install_log_fails_the_public_member_contract(self):
        path = self._build()
        names = self._zip_names(path)
        with self.assertRaises(AssertionError):
            self._assert_pack_member_contract(names + ["wavefoundry-install-log.md"])

    def test_wavefoundry_readme_included_in_pack(self):
        path = self._build()
        names = self._zip_names(path)
        self.assertIn(".wavefoundry/README.md", names)

    def test_wavefoundry_changelog_included_in_pack(self):
        path = self._build()
        names = self._zip_names(path)
        self.assertIn(".wavefoundry/CHANGELOG.md", names)

    def test_expected_files_present(self):
        path = self._build()
        names = self._zip_names(path)
        # At least one prompt file.
        self.assertTrue(any(n.endswith(".prompt.md") for n in names), names[:5])
        # Core scripts.
        self.assertTrue(
            any(n.endswith("render_platform_surfaces.py") for n in names), names[:5]
        )
        self.assertIn(
            ".wavefoundry/framework/seeds/215-council-chair.prompt.md",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/seeds/216-reality-checker.prompt.md",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/scripts/dashboard_server.py",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/scripts/review_evidence.py",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/scripts/server_impl.py",
            names,
        )
        # Wave 1yzd0: the flat file is the alias older runners require; the
        # implementation ships in the package.
        self.assertIn(
            ".wavefoundry/framework/scripts/wf_server/server_impl.py",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/scripts/context_efficiency.py",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/scripts/runtime_lock.py",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/scripts/score_context_efficiency_pairs.py",
            names,
        )
        self.assertNotIn(
            ".wavefoundry/framework/evals/context-efficiency-pairs.schema.json",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/dashboard/dashboard.html",
            names,
        )

    def test_install_pack_carries_typed_review_evidence_authoring(self):
        path = self._build()
        with zipfile.ZipFile(path, "r") as archive:
            writer = archive.read(
                ".wavefoundry/framework/scripts/review_evidence.py"
            ).decode("utf-8")
            server = archive.read(
                ".wavefoundry/framework/scripts/wf_server/server_impl.py"
            ).decode("utf-8")
        self.assertIn("def build_compact_review_event", writer)
        self.assertIn("def review_evidence_human_table", writer)
        self.assertIn("def wf_review_event(", server)
        # Wave 1tmb2: the packaged implementation carries the chain-aware
        # independence enforcement — upgrade replaces these files wholesale, so
        # the new contract is live after the normal MCP reload with no ledger
        # migration or compatibility alias.
        self.assertIn(
            'REVERIFICATION_CONTEXT_NOT_FRESH = "reverification_context_not_fresh"',
            writer,
        )
        self.assertIn(
            'REVERIFICATION_ACTOR_NOT_DISTINCT = "reverification_actor_not_distinct"',
            writer,
        )
        self.assertIn("def repair_independence_violations", writer)
        self.assertIn("REVIEW_EVIDENCE_INDEPENDENCE_INVALID", server)

    def test_install_pack_carries_the_vendored_dashboard_scripts(self):
        # Wave 1zim2 (1zilx): the dashboard loads its scripts from its own origin,
        # so the vendored copies, their licences and the notice ship byte-for-byte.
        path = self._build()
        vendor = SCRIPTS_DIR.parent / "dashboard" / "vendor"
        members = (
            "react/react.production.min.js", "react/LICENSE",
            "react-dom/react-dom.production.min.js", "react-dom/LICENSE",
            "elkjs/elk.bundled.js", "elkjs/LICENSE.md", "README.md",
        )
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            html = archive.read(".wavefoundry/framework/dashboard/dashboard.html").decode("utf-8")
            for rel in members:
                arcname = ".wavefoundry/framework/dashboard/vendor/" + rel
                with self.subTest(member=rel):
                    self.assertIn(arcname, names)
                    self.assertEqual(archive.read(arcname), (vendor / rel).read_bytes())
        self.assertIn('src="/vendor/elkjs/elk.bundled.js"', html)
        self.assertNotIn("unpkg.com", html)

    def test_install_pack_carries_dashboard_document_renderer_and_memory_backfill(self):
        path = self._build()
        with zipfile.ZipFile(path, "r") as archive:
            renderer = archive.read(
                ".wavefoundry/framework/dashboard/ds/wfds.js"
            ).decode("utf-8")
            css = archive.read(
                ".wavefoundry/framework/dashboard/dashboard.css"
            ).decode("utf-8")
            backfill = archive.read(
                ".wavefoundry/framework/scripts/memory_backfill.py"
            ).decode("utf-8")
            memory_cli = archive.read(
                ".wavefoundry/framework/scripts/memory_cli.py"
            ).decode("utf-8")
            setup = archive.read(
                ".wavefoundry/framework/scripts/setup_wavefoundry.py"
            ).decode("utf-8")
            server = archive.read(
                ".wavefoundry/framework/scripts/wf_server/server_impl.py"
            ).decode("utf-8")
        self.assertIn('visible.indexOf("<!--")', renderer)
        self.assertIn('paragraphLines.join(" ")', renderer)
        self.assertIn(".doc-dialog-body", css)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn("memory_backfill_runs", backfill)
        self.assertIn("def main", memory_cli)
        self.assertIn("historical_memory_report", setup)
        self.assertNotIn("index_publication_scope", setup)
        self.assertNotIn("wave_setup_resume_after_memory", server)
        self.assertNotIn("wf_resume_setup_after_memory", server)

    def test_extracted_install_pack_reproduces_lifecycle_focus_contract(self):
        """1tmb3 AC-10: the packaged server code reproduces council-ready
        focus plus failed-call reporting after extraction. Upgrade replaces
        these files wholesale, so the contract is live after the normal MCP
        reload with no data migration, compatibility alias, or fallback."""
        import subprocess
        import tempfile

        path = self._build()
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "installed"
            target.mkdir()
            with zipfile.ZipFile(path, "r") as archive:
                archive.extractall(target)
            scripts = target / ".wavefoundry" / "framework" / "scripts"
            (target / "docs").mkdir(parents=True, exist_ok=True)
            (target / "docs" / "workflow-config.json").write_text(
                json.dumps({
                    "lifecycle_id_policy": {
                        "epoch_utc": "2020-01-01T00:00:00Z", "hour_offset": 0,
                    }
                }),
                encoding="utf-8",
            )
            # Records in the packaged tree's layout and vocabulary (the pack
            # carries the loaded record_paths and vocabulary_profile).
            import vocabulary_profile as vp
            from record_layout_support import RecordTreeBuilder

            for wave_id in ("1aaaa other-wave", "1bbbb target-wave"):
                wave_md = RecordTreeBuilder(target).waves_dir / wave_id / vp.RECORD_FILENAME
                wave_md.parent.mkdir(parents=True)
                wave_md.write_text(
                    f"{vp.RECORD_TITLE}\n\nStatus: planned\n\n{vp.ID_KEY}: `{wave_id}`\n",
                    encoding="utf-8",
                )
            probe = r"""
import json, sys
from pathlib import Path
from types import SimpleNamespace
scripts = Path(sys.argv[1])
root = Path(sys.argv[2])
sys.path.insert(0, str(scripts))
import context_efficiency
import server_impl
handler = SimpleNamespace(
    root=root, cache={}, telemetry=context_efficiency.ProcessTelemetry(root)
)
handler.telemetry.set_focus("1aaaa other-wave", "implement", new_phase=True)
failed = server_impl._lifecycle_context_result(
    handler, "wf_prepare_wave", "1bbbb target-wave",
    {"status": "error", "data": {"wave_id": "1bbbb target-wave"},
     "diagnostics": [{"code": "missing_wave_council_signoff", "message": "m"}]},
    focus_stage="plan", credit=False, flush=False,
)
ready = server_impl._lifecycle_context_result(
    handler, "wf_prepare_wave", "1bbbb target-wave",
    {"status": "ready_for_council_review",
     "data": {"wave_id": "1bbbb target-wave", "mode": "ready", "council_brief": {}},
     "diagnostics": []},
    focus_stage="plan", credit=False, flush=True,
)
print(json.dumps({
    "failed_codes": [d["code"] for d in failed["diagnostics"]],
    "failed_destination": failed["data"]["focus_attribution"]["effective"]["destination"],
    "ready_projection": ready["data"]["context_efficiency_persistence"].get("projection"),
    "focus_wave": handler.telemetry.focus.wave_id,
    "focus_stage": handler.telemetry.focus.stage,
}))
"""
            result = subprocess.run(
                [sys.executable, "-B", "-c", probe, str(scripts), str(target)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            out = json.loads(result.stdout)
            self.assertIn("focus_target_not_engaged", out["failed_codes"])
            self.assertEqual(out["failed_destination"], "1aaaa other-wave")
            self.assertEqual(out["ready_projection"], "published")
            self.assertEqual(out["focus_wave"], "1bbbb target-wave")
            self.assertEqual(out["focus_stage"], "plan")

    def test_extracted_install_pack_executes_new_review_memory_and_dashboard_paths(self):
        import shutil
        import subprocess
        import tempfile

        path = self._build()
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "installed"
            target.mkdir()
            with zipfile.ZipFile(path, "r") as archive:
                archive.extractall(target)
            waves_dir(target).mkdir(parents=True)
            scripts = target / ".wavefoundry" / "framework" / "scripts"
            python_probe = r"""
import json, sys
from pathlib import Path
scripts = Path(sys.argv[1])
root = Path(sys.argv[2])
sys.path.insert(0, str(scripts))
import memory_backfill
import review_evidence
import dashboard_lib
rendered = review_evidence.render_review_status_projection(
    "# Wave\n\nStatus: implementing\n\n## Review Evidence\n\n",
    [],
    ["qa-reviewer", "operator-signoff"],
)
run_id = memory_backfill.ensure_run(root, "setup")
summary = memory_backfill.sync_inventory(root, run_id)
acs = dashboard_lib._parse_ac_items(
    "- [x] AC-1: packaged first line\n  packaged continuation\n",
    "| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Core. |\n",
    "planned",
)
tasks = dashboard_lib._parse_tasks(
    "- [ ] packaged task\n  packaged task continuation\n",
    "planned",
)
print(json.dumps({
    "status_marker": "<!-- wave:review-status begin -->" in rendered,
    "qa_pending": "| qa-reviewer | pending |" in rendered,
    "memory_state": summary["state"],
    "ac_text": acs[0]["text"],
    "ac_priority": acs[0]["priority"],
    "task_text": tasks["items"][0]["label"],
}))
"""
            python_result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    python_probe,
                    str(scripts),
                    str(target),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(python_result.returncode, 0, python_result.stderr)
            python_out = json.loads(python_result.stdout)
            self.assertTrue(python_out["status_marker"])
            self.assertTrue(python_out["qa_pending"])
            self.assertEqual(python_out["memory_state"], "indexed")
            self.assertEqual(
                python_out["ac_text"],
                "AC-1: packaged first line packaged continuation",
            )
            self.assertEqual(python_out["ac_priority"], "required")
            self.assertEqual(
                python_out["task_text"],
                "packaged task packaged task continuation",
            )

            if not shutil.which("node"):
                self.skipTest("node not available — packaged renderer execution skipped")
            fixture = (
                SCRIPTS_DIR
                / "tests"
                / "fixtures"
                / "dashboard-wave-rendering.md"
            )
            node_probe = r"""
const fs = require("fs");
const vm = require("vm");
function createElement(type, props, ...children) {
  const flat = [];
  for (const child of children) Array.isArray(child) ? flat.push(...child) : flat.push(child);
  return {type, props: props || {}, children: flat};
}
const root = {React: {createElement, useState(){}, useEffect(){}, useRef(){}, useCallback(){}}};
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"),
  {window: root, globalThis: root, console});
function text(node) {
  if (node == null) return "";
  if (typeof node === "string") return node;
  return (node.children || []).map(text).join("");
}
const rendered = root.WFDS.renderMarkdownish(fs.readFileSync(process.argv[2], "utf8"));
process.stdout.write(JSON.stringify(rendered.map(text)));
"""
            renderer = (
                target
                / ".wavefoundry"
                / "framework"
                / "dashboard"
                / "ds"
                / "wfds.js"
            )
            node_result = subprocess.run(
                ["node", "-e", node_probe, str(renderer), str(fixture)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(node_result.returncode, 0, node_result.stderr)
            visible = " ".join(json.loads(node_result.stdout))
            self.assertNotIn("wave:context-efficiency", visible)
            self.assertIn(
                "four physical source lines so the renderer must join "
                "the lines into one semantic paragraph",
                visible,
            )

    def test_extracting_install_pack_does_not_mutate_historical_waves(self):
        path = self._build()
        target = self.tmp / "target"
        legacy_wave = waves_dir(target) / "legacy-wave" / vocabulary_profile.RECORD_FILENAME
        legacy_wave.parent.mkdir(parents=True)
        sentinel = b"# Historical wave\n\nLegacy narrative remains byte-stable.\n"
        legacy_wave.write_bytes(sentinel)

        with zipfile.ZipFile(path, "r") as archive:
            archive.extractall(target)

        self.assertEqual(legacy_wave.read_bytes(), sentinel)
        self.assertFalse((legacy_wave.parent / "events.jsonl").exists())
        self.assertFalse(
            (
                target
                / ".wavefoundry"
                / "framework"
                / "scripts"
                / "migrate_self_host_review_events.py"
            ).exists()
        )

    def test_tests_excluded_from_pack(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("scripts/tests/", name, name)
            self.assertFalse(name.endswith("run_tests.py"), name)
            self.assertFalse(name.endswith("build_pack.py"), name)

    def test_benchmarks_excluded_from_pack(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("scripts/benchmarks/", name, name)

    def test_pycache_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("__pycache__", name, name)

    def test_pyc_files_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertFalse(name.endswith(".pyc"), name)

    def test_ds_store_excluded(self):
        self.assertFalse(
            build_pack.should_exclude("some/path/.DS_Store", ".DS_Store") is False
        )
        self.assertTrue(build_pack.should_exclude(".DS_Store", ".DS_Store"))

    def test_pytest_cache_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn(".pytest_cache", name, name)

    def test_scripts_tests_tmp_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("scripts/tests/tmp", name, name)

    def test_transient_artifact_extensions_excluded(self):
        """Regression for 130o2: transient artifacts (.lock, .log, editor backups) must not ship."""
        for ext in build_pack.TRANSIENT_ARTIFACT_EXTENSIONS:
            self.assertTrue(
                build_pack.should_exclude(f"some/path/file{ext}", f"file{ext}"),
                f"should_exclude must reject *{ext} files",
            )
            self.assertTrue(
                build_pack.should_exclude(f"file{ext}", f"file{ext}"),
                f"should_exclude must reject root-level *{ext} files",
            )

    def test_lock_and_log_files_not_in_pack(self):
        """End-to-end: a framework tree with lock/log files produces a pack without them."""
        fw = self.tmp / "fw-with-transients"
        fw.mkdir(parents=True)
        (fw / "scripts").mkdir()
        (fw / "scripts" / "tool.py").write_text("def t(): pass\n", encoding="utf-8")
        (fw / "test-run.lock").write_text("pid\n", encoding="utf-8")
        (fw / "index").mkdir()
        (fw / "index" / "index-build.lock").write_text("pid\n", encoding="utf-8")
        (fw / "index" / "index-build.log").write_text("log line\n", encoding="utf-8")
        (fw / "stray.bak").write_text("editor backup\n", encoding="utf-8")
        (fw / "stray.tmp").write_text("temp\n", encoding="utf-8")

        path = build_pack.build_zip(
            self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False
        )
        names = self._zip_names(path)
        for name in names:
            self.assertFalse(name.endswith(".lock"), f"lock file leaked: {name}")
            self.assertFalse(name.endswith(".log"), f"log file leaked: {name}")
            self.assertFalse(name.endswith(".bak"), f"backup file leaked: {name}")
            self.assertFalse(name.endswith(".tmp"), f"tmp file leaked: {name}")
        # Regular source files still pack
        self.assertTrue(any(n.endswith("scripts/tool.py") for n in names))

    # ------------------------------------------------------------------
    # --output argument
    # ------------------------------------------------------------------

    def test_output_dir_arg_writes_to_that_directory(self):
        import tempfile
        alt_dir = Path(tempfile.mkdtemp())
        try:
            path = build_pack.build_zip(alt_dir, "1.0.0", "2abc", write_version=False, update_manifest=False, inject_install_templates=False)
            self.assertEqual(path.parent, alt_dir)
            self.assertTrue(path.exists())
        finally:
            import shutil
            shutil.rmtree(str(alt_dir), ignore_errors=True)

    def test_nonexistent_output_dir_exits_nonzero(self):
        argv = [
            "build_pack.py",
            "--version", "1.0.0",
            "--output", "/nonexistent/path/that/does/not/exist",
        ]
        with patch.object(sys, "argv", argv), patch.object(build_pack, "_reexec_with_venv_if_needed"):
            with self.assertRaises(SystemExit) as ctx:
                build_pack.main()
        self.assertNotEqual(ctx.exception.code, 0)

    def test_version_flag_is_required(self):
        """main() exits non-zero when --version is omitted."""
        argv = ["build_pack.py", "--output", str(self.tmp)]
        with patch.object(sys, "argv", argv), patch.object(build_pack, "_reexec_with_venv_if_needed"):
            with self.assertRaises(SystemExit) as ctx:
                build_pack.main()
        self.assertNotEqual(ctx.exception.code, 0)

    def test_invalid_version_format_exits_nonzero(self):
        """main() rejects version strings that are not MAJOR.MINOR.PATCH."""
        argv = [
            "build_pack.py",
            "--version", "2026-05-20a",
            "--output", str(self.tmp),
        ]
        with patch.object(sys, "argv", argv), patch.object(build_pack, "_reexec_with_venv_if_needed"):
            with self.assertRaises(SystemExit) as ctx:
                build_pack.main()
        self.assertNotEqual(ctx.exception.code, 0)

    def test_pre_v1_versions_exit_nonzero(self):
        argv = [
            "build_pack.py",
            "--version", "0.8.0",
            "--output", str(self.tmp),
        ]
        with patch.object(sys, "argv", argv), patch.object(build_pack, "_reexec_with_venv_if_needed"):
            with self.assertRaises(SystemExit) as ctx:
                build_pack.main()
        self.assertNotEqual(ctx.exception.code, 0)

    # ------------------------------------------------------------------
    # Changelog-first builds (1t9tj)
    # ------------------------------------------------------------------

    def _main_with_repo(self, version, changelog_text):
        """Drive main() against a temp repo root; returns (exit_code, stderr,
        build_zip mock, check_docs_gate mock)."""
        import contextlib
        import io

        if changelog_text is not None:
            (self.tmp / "CHANGELOG.md").write_text(
                changelog_text, encoding="utf-8"
            )
        argv = ["build_pack.py", "--version", version, "--output", str(self.tmp)]
        stderr = io.StringIO()
        fake_zip = self.tmp / f"wavefoundry-{version}.{FAKE_PREFIX}.zip"
        def _fake_build(*_args, **_kwargs):
            fake_zip.write_bytes(b"package")
            return fake_zip
        code = 0
        with patch.object(sys, "argv", argv), \
             patch.object(build_pack, "_reexec_with_venv_if_needed"), \
             patch.object(build_pack, "find_repo_root", return_value=self.tmp), \
             patch.object(build_pack, "_current_build_suffix", return_value=FAKE_PREFIX), \
             patch.object(build_pack, "check_docs_gate") as gate, \
             patch.object(build_pack, "build_zip", side_effect=_fake_build) as bz, \
             patch.object(build_pack, "build_protocol_bridge_artifacts", return_value={}), \
             contextlib.redirect_stderr(stderr), \
             contextlib.redirect_stdout(io.StringIO()):
            try:
                build_pack.main()
            except SystemExit as exc:
                code = exc.code
        return code, stderr.getvalue(), bz, gate

    def test_versioned_build_refuses_without_changelog_section(self):
        """Every versioned build requires its `## [version]` entry, before any
        side effect — the pack ships CHANGELOG.md as its only offline release
        surface."""
        code, err, bz, gate = self._main_with_repo(
            "9.9.9", "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n- old\n"
        )
        self.assertNotEqual(code, 0)
        self.assertIn("## [9.9.9]", err)
        self.assertIn("Create the changelog entry first", err)
        bz.assert_not_called()
        gate.assert_not_called()

    def test_versioned_build_refuses_when_changelog_missing_entirely(self):
        code, err, bz, _gate = self._main_with_repo("9.9.9", None)
        self.assertNotEqual(code, 0)
        self.assertIn("Create the changelog entry first", err)
        bz.assert_not_called()

    def test_release_preflight_refuses_stale_version_constant_claim(self):
        """DOCS-DEL-1 repair (wave 1wip2): the RELEASE preflight home of the
        claims check is executed, not only source-pinned — a stale claim in
        the packed section refuses the release before any side effect."""
        import contextlib
        import io

        (self.tmp / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [9.9.9] - 2026-08-28\n\n"
            "- rechunk everything; `CHUNKER_VERSION` to 1\n",
            encoding="utf-8",
        )
        argv = [
            "build_pack.py", "--version", "9.9.9",
            "--output", str(self.tmp), "--release", "--with-models",
        ]
        stderr = io.StringIO()
        code = 0
        with patch.object(sys, "argv", argv), \
             patch.object(build_pack, "_reexec_with_venv_if_needed"), \
             patch.object(build_pack, "find_repo_root", return_value=self.tmp), \
             patch.object(build_pack, "_check_git_working_tree_clean"), \
             patch.object(build_pack, "_check_on_main_branch"), \
             patch.object(build_pack, "_check_tag_does_not_exist"), \
             patch.object(build_pack, "_check_gh_authenticated"), \
             patch.object(build_pack, "check_docs_gate") as gate, \
             patch.object(build_pack, "build_zip") as bz, \
             contextlib.redirect_stderr(stderr), \
             contextlib.redirect_stdout(io.StringIO()):
            try:
                build_pack.main()
            except SystemExit as exc:
                code = exc.code
        self.assertNotEqual(code, 0)
        err = stderr.getvalue()
        self.assertIn("release preflight failed", err)
        self.assertIn("version-constant claims", err)
        self.assertIn("`CHUNKER_VERSION` claim `1`", err)
        bz.assert_not_called()
        gate.assert_not_called()

    def test_versioned_build_refuses_stale_version_constant_claim(self):
        """Wave 1wip2 (1wgwn): the packed section's version-constant claims
        must match the live code constants — the coverage the 1.20.0 pm1l
        pack escaped through (it shipped `CHUNKER_VERSION` "to 34" while the
        delivered tree was 37)."""
        code, err, bz, _gate = self._main_with_repo(
            "9.9.9",
            "# Changelog\n\n## [9.9.9] - 2026-08-28\n\n"
            "- rechunk everything; `CHUNKER_VERSION` to 1\n",
        )
        self.assertNotEqual(code, 0)
        self.assertIn("version-constant claims", err)
        self.assertIn("`CHUNKER_VERSION` claim `1`", err)
        bz.assert_not_called()

    def test_versioned_build_proceeds_with_matching_constant_claim(self):
        import sys as _sys
        _sys.path.insert(0, str(Path(build_pack.__file__).resolve().parent))
        from wave_lint_lib.docs_constants_validators import _module_constant
        live = _module_constant("chunker.py", "CHUNKER_VERSION")
        code, err, bz, _gate = self._main_with_repo(
            "9.9.9",
            "# Changelog\n\n## [9.9.9] - 2026-08-28\n\n"
            f"- rechunk everything; `CHUNKER_VERSION` to {live}\n",
        )
        self.assertEqual(code, 0, err)
        bz.assert_called_once()

    def test_versioned_build_proceeds_once_section_exists(self):
        code, err, bz, _gate = self._main_with_repo(
            "9.9.9", "# Changelog\n\n## [9.9.9] - 2026-07-22\n\n- the fix\n"
        )
        self.assertEqual(code, 0)
        self.assertNotIn("Create the changelog entry first", err)
        bz.assert_called_once()

    def test_release_preflight_changelog_check_is_unchanged(self):
        """The release path keeps its own preflight wording; the new plain-path
        check must not fire there (source pin: the plain-path check lives in
        the else branch of the release-mode preflight)."""
        source = (SCRIPTS_DIR / "build_pack.py").read_text(encoding="utf-8")
        release_msg = source.index("Add the section (with release notes) before --release.")
        plain_msg = source.index("Create the changelog entry first")
        self.assertLess(release_msg, plain_msg)
        release_gate = source.index("if args.release or args.release_dry_run:")
        else_branch = source.index("    else:", release_gate)
        self.assertLess(release_gate, else_branch)
        self.assertLess(else_branch, plain_msg)

    # ------------------------------------------------------------------
    # MANIFEST
    # ------------------------------------------------------------------

    def test_manifest_deleted_from_framework_dir_after_zip(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seed.md").write_text("seed", encoding="utf-8")
        build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False)
        self.assertFalse((fw / "MANIFEST").exists(), "MANIFEST should be deleted after packaging")

    def test_manifest_included_in_zip(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seed.md").write_text("seed", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False)
        with zipfile.ZipFile(path) as zf:
            self.assertIn(".wavefoundry/framework/MANIFEST", zf.namelist())

    def test_manifest_lists_all_packed_files(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "a.md").write_text("a", encoding="utf-8")
        (fw / "b.txt").write_text("b", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False)
        with zipfile.ZipFile(path) as zf:
            manifest_text = zf.read(".wavefoundry/framework/MANIFEST").decode()
        entries = {line for line in manifest_text.splitlines() if line.strip()}
        self.assertIn("a.md", entries)
        self.assertIn("b.txt", entries)
        self.assertIn("MANIFEST", entries)

    def test_manifest_does_not_list_excluded_files(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        scripts_dir = fw / "scripts"
        scripts_dir.mkdir(parents=True)
        tests_dir = scripts_dir / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_foo.py").write_text("x", encoding="utf-8")
        (scripts_dir / "run_tests.py").write_text("x", encoding="utf-8")
        (scripts_dir / "build_pack.py").write_text("x", encoding="utf-8")
        (scripts_dir / "repair_ppol_memory_staging.py").write_text("x", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False)
        with zipfile.ZipFile(path) as zf:
            manifest_text = zf.read(".wavefoundry/framework/MANIFEST").decode()
        entries = {line for line in manifest_text.splitlines() if line.strip()}
        self.assertNotIn("scripts/run_tests.py", entries)
        self.assertNotIn("scripts/build_pack.py", entries)
        self.assertNotIn("scripts/repair_ppol_memory_staging.py", entries)
        with zipfile.ZipFile(path) as zf:
            self.assertNotIn(".wavefoundry/framework/scripts/repair_ppol_memory_staging.py", zf.namelist())
        self.assertFalse(any("tests/" in e for e in entries))

    def test_manifest_does_not_list_the_vendored_scripts_verifier(self):
        """Wave 1zls7 (1zltw AC-4): the network-using verifier is development-only."""
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        scripts_dir = fw / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "verify_vendored_scripts.py").write_text("x", encoding="utf-8")
        (scripts_dir / "kept.py").write_text("x", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False)
        with zipfile.ZipFile(path) as zf:
            manifest_text = zf.read(".wavefoundry/framework/MANIFEST").decode()
            names = zf.namelist()
        entries = {line for line in manifest_text.splitlines() if line.strip()}
        self.assertIn("scripts/kept.py", entries)
        self.assertNotIn("scripts/verify_vendored_scripts.py", entries)
        self.assertNotIn(".wavefoundry/framework/scripts/verify_vendored_scripts.py", names)

    def test_worker_guard_ships_as_an_inert_production_dependency_without_startup_shim(self):
        import shutil
        import subprocess

        fw = self.tmp / "mini-worker-fw"
        scripts = fw / "scripts"
        scripts.mkdir(parents=True)
        for name in ("review_evidence", "test_worker_guard", "review_policy", "runtime_lock",
                     "gardener_metadata", "record_paths", "vocabulary_profile",
                     "operator_identity", "subprocess_util"):
            shutil.copy2(SCRIPTS_DIR / f"{name}.py", scripts / f"{name}.py")
        shutil.copytree(SCRIPTS_DIR / "test_worker_bootstrap", scripts / "test_worker_bootstrap")
        archive_path = build_pack.build_zip(
            self.tmp, "1.0.0", "2tm5", framework_dir=fw,
            write_version=False, update_manifest=False, inject_install_templates=False)
        extracted = self.tmp / "extracted"
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            entries = set(archive.read(".wavefoundry/framework/MANIFEST").decode().splitlines())
            self.assertIn("scripts/test_worker_guard.py", entries)
            self.assertIn(".wavefoundry/framework/scripts/test_worker_guard.py", names)
            self.assertFalse(any("test_worker_bootstrap" in name for name in (*names, *entries)))
            archive.extractall(extracted)
        installed = extracted / ".wavefoundry/framework/scripts"
        code = """import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
before = (os.open, sys.dont_write_bytecode, sys.pycache_prefix)
import review_evidence, test_worker_guard
assert Path(review_evidence.__file__).parent == Path(sys.argv[1])
assert Path(test_worker_guard.__file__).parent == Path(sys.argv[1])
assert review_evidence.refuse_publication is test_worker_guard.refuse_publication
test_worker_guard.install()
review_evidence.refuse_publication(Path(sys.argv[1]))
assert before == (os.open, sys.dont_write_bytecode, sys.pycache_prefix)
"""
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("PYTHONPYCACHEPREFIX", None)
        env.pop("WAVEFOUNDRY_TEST_WORKER_PROTECTED_ROOTS", None)
        result = subprocess.run([sys.executable, "-B", "-I", "-c", code, str(installed)],
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lint_exclusions_doc_ships_in_pack(self):
        """Wave 1p3b9 (1p3b5): the operator-visible `lint-exclusions.md`
        reference doc lives under `.wavefoundry/framework/docs/` so it ships
        in every release pack. Consumers running `Upgrade Wavefoundry`
        receive the doc; enterprise security review reads it locally.
        Regression guard against accidental relocation outside the pack tree."""
        fw = self.tmp / "mini-fw-with-docs"
        fw.mkdir(parents=True)
        docs_dir = fw / "docs"
        docs_dir.mkdir(parents=True)
        (docs_dir / "lint-exclusions.md").write_text(
            "# docs-lint Exclusions\n\nTest content.\n", encoding="utf-8"
        )
        path = build_pack.build_zip(
            self.tmp, "1.0.0", "2tm5", framework_dir=fw,
            write_version=False, update_manifest=False, inject_install_templates=False,
        )
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        self.assertIn(".wavefoundry/framework/docs/lint-exclusions.md", names)


class ManifestRevisionTests(unittest.TestCase):
    """Tests for update_manifest_revision()."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        (self.tmp / "docs" / "prompts").mkdir(parents=True)
        self.manifest_path = self.tmp / "docs" / "prompts" / "prompt-surface-manifest.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_manifest(self, data: dict) -> None:
        self.manifest_path.write_text(json.dumps(data), encoding="utf-8")

    def _read_manifest(self) -> dict:
        import json
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def test_writes_revision_to_manifest(self):
        self._write_manifest({"framework_revision": "1.0.0+2tm5", "other": "val"})
        build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")
        self.assertEqual(self._read_manifest()["framework_revision"], "1.0.0+2xyz")

    def test_preserves_other_manifest_fields(self):
        self._write_manifest({"framework_revision": "1.0.0+2tm5", "other": "val"})
        build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")
        self.assertEqual(self._read_manifest()["other"], "val")

    def test_adds_field_when_missing(self):
        self._write_manifest({"other_key": "value"})
        build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")
        self.assertEqual(self._read_manifest()["framework_revision"], "1.0.0+2xyz")

    def test_warns_when_manifest_missing(self):
        import io
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")
        self.assertIn("warning", captured.getvalue())

    def test_manifest_not_found_does_not_raise(self):
        build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")

    def test_build_zip_stamps_manifest_before_zip_is_written(self):
        fw = self.tmp / ".wavefoundry" / "framework"
        fw.mkdir(parents=True)
        (self.tmp / "docs" / "prompts").mkdir(parents=True, exist_ok=True)
        manifest_path = self.tmp / "docs" / "prompts" / "prompt-surface-manifest.json"
        self._write_manifest({"framework_revision": "1.0.0+2tm5"})
        (fw / "stub.txt").write_text("stub", encoding="utf-8")
        build_pack.build_zip(self.tmp, "1.0.0", "2xyz", framework_dir=fw, write_version=False, update_manifest=True, inject_install_templates=False)
        import json
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))["framework_revision"]
        self.assertEqual(recorded, "1.0.0+2xyz")


class DocsGateTests(unittest.TestCase):
    """Tests for check_docs_gate().

    Wave 1p7tz: the `bin/docs-gardener`/`bin/docs-lint` wrappers were retired — check_docs_gate now
    runs `[sys.executable, .wavefoundry/framework/scripts/docs_gardener.py|docs_lint.py]` directly. The
    fixtures create fake `.py` scripts under framework/scripts/ that exit with the chosen code."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self.scripts_dir = self.tmp / ".wavefoundry" / "framework" / "scripts"
        self.scripts_dir.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_script(self, module: str, exit_code: int) -> None:
        # `module` is e.g. "docs_gardener.py" — a valid Python file run under sys.executable.
        (self.scripts_dir / module).write_text(
            f"import sys\nsys.exit({exit_code})\n", encoding="utf-8"
        )

    def test_passes_when_both_commands_succeed(self):
        self._make_script("docs_gardener.py", 0)
        self._make_script("docs_lint.py", 0)
        build_pack.check_docs_gate(self.tmp)

    def test_fails_when_docs_gardener_fails(self):
        self._make_script("docs_gardener.py", 1)
        self._make_script("docs_lint.py", 0)
        with self.assertRaises(SystemExit) as ctx:
            build_pack.check_docs_gate(self.tmp)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_fails_when_docs_lint_fails(self):
        self._make_script("docs_gardener.py", 0)
        self._make_script("docs_lint.py", 1)
        with self.assertRaises(SystemExit) as ctx:
            build_pack.check_docs_gate(self.tmp)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_fails_when_docs_gardener_not_found(self):
        with self.assertRaises(SystemExit) as ctx:
            build_pack.check_docs_gate(self.tmp)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_fails_when_docs_lint_not_found(self):
        self._make_script("docs_gardener.py", 0)
        with self.assertRaises(SystemExit) as ctx:
            build_pack.check_docs_gate(self.tmp)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_error_message_names_the_failing_command(self):
        import io
        self._make_script("docs_gardener.py", 0)
        self._make_script("docs_lint.py", 1)
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            with self.assertRaises(SystemExit):
                build_pack.check_docs_gate(self.tmp)
        self.assertIn("docs-lint", captured.getvalue())


# ---------------------------------------------------------------------------
# Release orchestration helpers (wave 1p347 / change 1p349)
# ---------------------------------------------------------------------------


class ChangelogSectionExtractionTests(unittest.TestCase):
    """Tests for _extract_changelog_section()."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self.changelog = self.tmp / "CHANGELOG.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write(self, text):
        self.changelog.write_text(text, encoding="utf-8")

    def test_extracts_named_section_body_only(self):
        """Heading is excluded; body is returned verbatim."""
        self._write(
            "# Changelog\n\n"
            "## [1.4.0] - 2026-06-03\n\n"
            "### Fixed\n\n- alpha\n- beta\n\n"
            "## [1.3.32] - 2026-05-01\n\n"
            "- previous\n"
        )
        body = build_pack._extract_changelog_section(self.changelog, "1.4.0")
        self.assertIn("### Fixed", body)
        self.assertIn("- alpha", body)
        self.assertNotIn("## [1.4.0]", body)
        self.assertNotIn("## [1.3.32]", body)

    def test_returns_empty_when_section_missing(self):
        """Section absent → empty string (caller refuses the release)."""
        self._write("# Changelog\n\n## [1.3.32]\n\n- previous\n")
        body = build_pack._extract_changelog_section(self.changelog, "1.4.0")
        self.assertEqual(body.strip(), "")

    def test_returns_empty_when_file_absent(self):
        """Missing CHANGELOG → empty string (caller refuses the release)."""
        body = build_pack._extract_changelog_section(
            self.tmp / "missing.md", "1.4.0"
        )
        self.assertEqual(body, "")

    def test_section_at_end_of_file_extracted(self):
        """No subsequent `## [` heading → section runs to EOF."""
        self._write("# Changelog\n\n## [1.4.0]\n\n- only\n")
        body = build_pack._extract_changelog_section(self.changelog, "1.4.0")
        self.assertIn("- only", body)


class ReleaseNotesInstallPrependTests(unittest.TestCase):
    """Wave 1p35d (1p35p): release notes carry an `## Install` block at the
    top so an agent or operator landing on the GitHub Releases page sees the
    zip-at-root → shortcut-phrase flow alongside the download link. Source of
    truth lives at `.wavefoundry/framework/install/install-block.md`."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        (self.tmp / build_pack.RELEASE_NOTES_INSTALL_BLOCK_REL.parent).mkdir(
            parents=True, exist_ok=True
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_block(self, content: str) -> None:
        (self.tmp / build_pack.RELEASE_NOTES_INSTALL_BLOCK_REL).write_text(
            content, encoding="utf-8"
        )

    def test_shipped_block_has_install_and_upgrade_sections(self):
        # The shipped release-notes header must carry BOTH a fresh-install path AND an
        # upgrade path (an existing consumer needs "Upgrade Wavefoundry", not Install).
        repo_root = Path(build_pack.__file__).resolve().parents[3]
        block = (repo_root / build_pack.RELEASE_NOTES_INSTALL_BLOCK_REL).read_text(encoding="utf-8")
        self.assertIn("## Install", block)
        self.assertIn("## Upgrade", block)
        self.assertIn("Upgrade Wavefoundry", block)
        # Install precedes Upgrade in document order.
        self.assertLess(block.index("## Install"), block.index("## Upgrade"))

    def test_upgrade_block_flows_into_assembled_notes(self):
        # The upgrade block reaches the assembled release notes, above the changelog body.
        self._write_block("## Install\n\nfresh.\n\n## Upgrade\n\nUpgrade Wavefoundry\n\n---\n\n")
        notes = build_pack._assemble_release_notes(self.tmp, "### Changed\n\n- thing\n")
        self.assertIn("## Upgrade", notes)
        self.assertIn("Upgrade Wavefoundry", notes)
        self.assertLess(notes.index("## Upgrade"), notes.index("### Changed"))

    def test_install_block_is_prepended_to_changelog_body(self):
        self._write_block("## Install\n\nDrop the zip.\n\n---\n\n")
        notes = build_pack._assemble_release_notes(
            self.tmp, "### Changed\n\n- thing\n"
        )
        self.assertTrue(notes.startswith("## Install"))
        self.assertIn("Drop the zip.", notes)
        # Changelog body still present after the block.
        self.assertIn("### Changed", notes)
        self.assertIn("- thing", notes)
        # Install block precedes the changelog body in document order.
        self.assertLess(notes.index("## Install"), notes.index("### Changed"))

    def test_block_missing_falls_through_to_changelog_only(self):
        """No install block on disk → notes are the CHANGELOG body alone."""
        notes = build_pack._assemble_release_notes(
            self.tmp, "### Changed\n\n- thing\n"
        )
        self.assertEqual(notes, "### Changed\n\n- thing\n")

    def test_empty_block_file_falls_through(self):
        """An on-disk-but-empty block file is treated as no block."""
        self._write_block("")
        notes = build_pack._assemble_release_notes(self.tmp, "### Changed\n- x\n")
        self.assertEqual(notes, "### Changed\n- x\n")

    def test_block_includes_shortcut_phrase_and_supported_hosts(self):
        """The shipped install block at the repo source-of-truth path names the
        canonical shortcut phrase and the supported agent-host list. Regression
        guard against future drift — if the block evolves, this asserts the
        agent-facing affordances stay present."""
        repo_block = (
            Path(__file__).resolve().parents[2]
            / "install" / "install-block.md"
        )
        self.assertTrue(repo_block.is_file(), f"missing {repo_block}")
        text = repo_block.read_text(encoding="utf-8")
        self.assertIn("Install Wavefoundry", text)
        for host in ("Claude Code", "Cursor", "Codex"):
            self.assertIn(host, text)


class ReleasePreflightTests(unittest.TestCase):
    """Tests for pre-flight gate refusals."""

    def _mock_run(self, return_codes_and_outputs):
        """Patch subprocess.run to return a sequence of mocked CompletedProcess objs."""
        class _CP:
            def __init__(self, rc, out="", err=""):
                self.returncode = rc
                self.stdout = out
                self.stderr = err
        results = iter(_CP(rc, out, err) for rc, out, err in return_codes_and_outputs)
        def _next(*args, **kwargs):
            return next(results)
        return _next

    def test_working_tree_dirty_refuses(self):
        runner = self._mock_run([(0, " M foo.py\n", "")])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_git_working_tree_clean(Path("/tmp"))
        self.assertIn("working tree", str(ctx.exception).lower())

    def test_working_tree_clean_passes(self):
        runner = self._mock_run([(0, "", "")])
        with patch("build_pack.subprocess.run", runner):
            build_pack._check_git_working_tree_clean(Path("/tmp"))  # no exception

    def test_non_main_branch_refuses(self):
        runner = self._mock_run([(0, "feature-branch\n", "")])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_on_main_branch(Path("/tmp"))
        self.assertIn("feature-branch", str(ctx.exception))
        self.assertIn("main", str(ctx.exception))

    def test_main_branch_passes(self):
        runner = self._mock_run([(0, "main\n", "")])
        with patch("build_pack.subprocess.run", runner):
            build_pack._check_on_main_branch(Path("/tmp"))

    def test_local_tag_exists_refuses(self):
        """rev-parse rc=0 means the tag exists locally."""
        runner = self._mock_run([(0, "abc123\n", "")])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_tag_does_not_exist(Path("/tmp"), "v1.4.0")
        self.assertIn("local tag", str(ctx.exception))

    def test_remote_tag_exists_refuses(self):
        runner = self._mock_run([
            (1, "", "fatal: not a ref"),               # local: missing
            (0, "abc123\trefs/tags/v1.4.0\n", ""),     # remote: present
        ])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_tag_does_not_exist(Path("/tmp"), "v1.4.0")
        self.assertIn("remote tag", str(ctx.exception))

    def test_tag_absent_locally_and_remotely_passes(self):
        runner = self._mock_run([
            (1, "", "fatal: not a ref"),  # local: missing
            (0, "", ""),                  # remote: empty stdout
        ])
        with patch("build_pack.subprocess.run", runner):
            build_pack._check_tag_does_not_exist(Path("/tmp"), "v1.4.0")

    def test_gh_unauthenticated_refuses(self):
        runner = self._mock_run([(1, "", "not logged in")])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_gh_authenticated()
        self.assertIn("gh auth", str(ctx.exception).lower())

    def test_gh_authenticated_passes(self):
        runner = self._mock_run([(0, "Logged in", "")])
        with patch("build_pack.subprocess.run", runner):
            build_pack._check_gh_authenticated()


class TagMessageDerivationTests(unittest.TestCase):
    """Tests for _derive_tag_message()."""

    def _mock_run(self, rc, stdout):
        class _CP:
            def __init__(self, r, o):
                self.returncode = r
                self.stdout = o
                self.stderr = ""
        def _runner(*args, **kwargs):
            return _CP(rc, stdout)
        return _runner

    def test_close_wave_subject_used_verbatim(self):
        runner = self._mock_run(0, "Close wave 1p337 and ship 1.3.32 → 1.4.0\n")
        with patch("build_pack.subprocess.run", runner):
            msg = build_pack._derive_tag_message(Path("/tmp"), "1.4.0")
        self.assertEqual(msg, "Close wave 1p337 and ship 1.3.32 → 1.4.0")

    def test_ascii_arrow_close_wave_subject_recognized(self):
        runner = self._mock_run(0, "Close wave 1p347 and ship 1.4.0 -> 1.4.1\n")
        with patch("build_pack.subprocess.run", runner):
            msg = build_pack._derive_tag_message(Path("/tmp"), "1.4.1")
        self.assertEqual(msg, "Close wave 1p347 and ship 1.4.0 -> 1.4.1")

    def test_non_close_subject_falls_back_to_default(self):
        runner = self._mock_run(0, "chore: tweak gitignore\n")
        with patch("build_pack.subprocess.run", runner):
            msg = build_pack._derive_tag_message(Path("/tmp"), "1.4.1")
        self.assertEqual(msg, "Release v1.4.1")

    def test_git_failure_falls_back_to_default(self):
        runner = self._mock_run(1, "")
        with patch("build_pack.subprocess.run", runner):
            msg = build_pack._derive_tag_message(Path("/tmp"), "1.4.1")
        self.assertEqual(msg, "Release v1.4.1")

    def test_git_log_decoded_as_utf8(self):
        """Wave 1p9j0 (F12): the git-log decode passes encoding='utf-8', so a unicode `→`
        subject survives intact (no cp1252 UnicodeDecodeError/mojibake) and the regex matches."""
        captured = {}

        class _CP:
            returncode = 0
            stdout = "Close wave 1p337 and ship 1.3.32 → 1.4.0\n"
            stderr = ""

        def _runner(*args, **kwargs):
            captured.update(kwargs)
            return _CP()

        with patch("build_pack.subprocess.run", _runner):
            msg = build_pack._derive_tag_message(Path("/tmp"), "1.4.0")
        self.assertEqual(msg, "Close wave 1p337 and ship 1.3.32 → 1.4.0")
        self.assertEqual(captured.get("encoding"), "utf-8")


# ---------------------------------------------------------------------------
# Release orchestration ordering (wave 1p5l4): the build stamp must be committed
# BEFORE tagging, so the tag lands on the stamp commit (matching the v1.4/v1.5
# convention), and main must be pushed so origin reflects the tagged commit.
# ---------------------------------------------------------------------------


class ReleaseOrchestrationOrderingTests(unittest.TestCase):
    """`_run_release_orchestration` commits the stamp, then tags, then pushes main + tag."""

    def _repo_with_version(self, stamp="1.6.0+ptest"):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        vfile = root / build_pack.FRAMEWORK_REL / "VERSION"
        vfile.parent.mkdir(parents=True, exist_ok=True)
        vfile.write_text(stamp + "\n", encoding="utf-8")
        return root

    def _asset(self, name, body=b"asset"):
        """A real release asset file: SHA256SUMS hashes every asset it uploads."""
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / name
        path.write_bytes(body)
        return path

    class _Recorder:
        """Records argv of each subprocess.run and returns success for all."""
        def __init__(self):
            self.calls = []

        def __call__(self, argv, **kwargs):
            self.calls.append(list(argv))

            class _CP:
                def __init__(self, rc, out="", err=""):
                    self.returncode = rc
                    self.stdout = out
                    self.stderr = err

            # `git diff --cached --quiet` → rc=1 means there ARE staged changes
            # (the stamp), so the commit step proceeds.
            if argv[:3] == ["git", "diff", "--cached"]:
                return _CP(1)
            # `git log -1 --format=%s` (tag-message derivation): non-close subject.
            if argv[:2] == ["git", "log"]:
                return _CP(0, "Close wave 1p5dk and ship 1.5.1 -> 1.6.0\n")
            return _CP(0, "ok")

    def _verbs(self, calls):
        """Reduce recorded argv lists to comparable verb tuples."""
        verbs = []
        for c in calls:
            if c[:2] == ["git", "commit"]:
                verbs.append("commit")
            elif c[:2] == ["git", "tag"]:
                verbs.append("tag")
            elif c[:1] == ["git"] and "push" in c and "HEAD:main" in c:
                verbs.append("push-main")
            elif c[:1] == ["git"] and "push" in c and any(x == "v1.6.0" for x in c):
                verbs.append("push-tag")
            elif c[:2] == ["gh", "release"]:
                verbs.append("gh-release")
        return verbs

    def test_dry_run_makes_no_git_or_remote_mutations_and_says_so(self):
        """Release review round 4: --release-dry-run performs NO commit, tag,
        push, or gh release; the completion message names the retained local
        side effects and never claims "no side effects"."""
        root = self._repo_with_version()
        rec = self._Recorder()
        with patch("build_pack.subprocess.run", rec):
            build_pack._run_release_orchestration(
                root, "1.6.0", self._asset("wavefoundry-1.6.0.ptest.zip"),
                "notes", dry_run=True,
            )
        self.assertEqual(self._verbs(rec.calls), [],
                         "dry-run must perform zero git/gh mutations")
        # The user-facing statements are honest.
        src = Path(build_pack.__file__).read_text(encoding="utf-8")
        self.assertNotIn("no side effects taken", src)
        done_msg_pos = src.index("[--release-dry-run] complete")
        tail = src[done_msg_pos:done_msg_pos + 500]
        self.assertIn("no commit, tag, push, or GitHub", tail)
        self.assertIn("stamps remain", tail)
        self.assertIn("git restore --", src)

    def test_dry_run_local_build_side_effects_are_real(self):
        """Release review rounds 4+7: the LOCAL half of dry-run is real — the
        archive is created and VERSION is stamped (tracked change left). A
        contract fixture must EXECUTE: no try/except-to-skip (a signature
        mismatch here should fail loudly, not silently pass the suite)."""
        import tempfile, zipfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out_dir = Path(tmp.name)
        root = self._repo_with_version(stamp="1.5.0+pold")
        # Minimal framework tree so build_zip has something to package.
        fw = root / build_pack.FRAMEWORK_REL
        (fw / "scripts").mkdir(parents=True, exist_ok=True)
        (fw / "scripts" / "placeholder.py").write_text("# x\n", encoding="utf-8")
        vfile = fw / "VERSION"
        before = vfile.read_text(encoding="utf-8")
        zip_path = build_pack.build_zip(
            out_dir,
            "1.6.0",
            "ptest",
            framework_dir=fw,
            update_manifest=False,
            inject_install_templates=False,  # stub framework dir (documented convention)
        )
        self.assertTrue(Path(zip_path).exists(), "archive must be created")
        self.assertTrue(zipfile.is_zipfile(zip_path))
        after = vfile.read_text(encoding="utf-8")
        self.assertNotEqual(before, after, "VERSION stamp is a real tracked change")
        self.assertIn("1.6.0", after)
        # The stamp REMAINS on disk after the build returns — the retained
        # local side effect the dry-run completion message names.
        self.assertIn("1.6.0", vfile.read_text(encoding="utf-8"))

    def test_commit_precedes_tag_and_main_is_pushed(self):
        root = self._repo_with_version()
        rec = self._Recorder()
        with patch("build_pack.subprocess.run", rec):
            build_pack._run_release_orchestration(
                root, "1.6.0", self._asset("wavefoundry-1.6.0.ptest.zip"),
                "notes", dry_run=False,
            )
        verbs = self._verbs(rec.calls)
        # The exact release-action sequence.
        self.assertEqual(verbs, ["commit", "tag", "push-main", "push-tag", "gh-release"])
        # And specifically: the stamp commit lands before the tag.
        self.assertLess(verbs.index("commit"), verbs.index("tag"))

    def test_release_uploads_single_wavefoundry_package(self):
        root = self._repo_with_version()
        rec = self._Recorder()
        package = self._asset("wavefoundry-1.6.0.ptest.zip")
        with patch("build_pack.subprocess.run", rec):
            build_pack._run_release_orchestration(
                root,
                "1.6.0",
                package,
                "notes",
                dry_run=False,
            )
        release_call = next(c for c in rec.calls if c[:3] == ["gh", "release", "create"])
        self.assertEqual(release_call.count(str(package)), 1)
        self.assertEqual(
            [arg for arg in release_call if arg.endswith((".zip", ".pyz"))],
            [str(package)],
        )

    def test_release_main_wires_feature_and_matching_model_assets(self):
        self._assert_release_assets(False)

    def test_release_main_wires_additional_combined_asset(self):
        self._assert_release_assets(True)

    def _assert_release_assets(self, embedded):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo_with_version()
            output = Path(tmp)
            feature = output / "wavefoundry-1.16.0.ptest.zip"
            feature.write_bytes(b"feature")
            model = output / "wavefoundry-models-2.zip"
            model.write_bytes(b"models")
            internal = {
                "bridge": output / "internal-bridge.zip",
                "selection": output / "internal-selection.json",
            }
            combined = output / "wavefoundry-1.16.0.ptest.with-models.zip"
            combined.write_bytes(b"combined")
            orchestration = MagicMock()
            argv = [
                "build_pack.py",
                "--version",
                "1.16.0",
                "--output",
                str(output),
                "--with-embedded-models" if embedded else "--with-models",
                "--release-dry-run",
            ]
            with patch.object(sys, "argv", argv), patch.object(
                build_pack, "_reexec_with_venv_if_needed"
            ), patch.object(
                build_pack, "find_repo_root", return_value=root
            ), patch.object(
                build_pack, "_current_build_suffix", return_value="ptest"
            ), patch.object(
                build_pack, "_check_git_working_tree_clean"
            ), patch.object(
                build_pack, "_check_on_main_branch"
            ), patch.object(
                build_pack, "_check_tag_does_not_exist"
            ), patch.object(
                build_pack, "_check_gh_authenticated"
            ), patch.object(
                build_pack, "_extract_changelog_section", return_value="release notes"
            ), patch.object(
                build_pack, "_assemble_release_notes", return_value="assembled notes"
            ), patch.object(
                build_pack, "check_docs_gate"
            ), patch.object(
                build_pack, "_check_release_qualification", return_value=_QUALIFICATION_SECTION
            ) as qualification_gate, patch.object(
                build_pack, "_current_framework_inputs_hash", return_value="a" * 64
            ), patch.object(
                build_pack, "_warn_on_same_semver_collision"
            ), patch.object(
                build_pack, "build_zip", return_value=feature
            ), patch.object(
                build_pack, "build_protocol_bridge_artifacts", return_value=internal
            ) as bridge_build, patch.object(
                build_pack, "build_upgrade_bundle", return_value=feature
            ) as bundle_build, patch.object(
                build_pack, "_run_release_orchestration", orchestration
            ), patch(
                "model_bundle.build_bundle", return_value=model
            ) as model_build, patch.object(build_pack, "build_embedded_package", return_value=combined) as embedded_build:
                build_pack.main()
                self.assertEqual(embedded_build.call_count, int(embedded))

            qualification_gate.assert_called_once()
            bridge_build.assert_called_once()
            bundle_build.assert_called_once_with(
                feature,
                internal,
                version="1.16.0",
                build_prefix="ptest",
            )
            model_build.assert_called_once_with(
                output,
            )
            orchestration.assert_called_once_with(
                root,
                "1.16.0",
                feature,
                "assembled notes\n\n" + _QUALIFICATION_SECTION,
                dry_run=True,
                extra_assets=[model, combined] if embedded else [model],
            )
            self.assertEqual(orchestration.call_args.args[2], feature)
            self.assertEqual(orchestration.call_args.kwargs["extra_assets"], [model, combined] if embedded else [model])

    def test_release_main_rejects_extra_current_build_public_package(self):
        import contextlib
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo_with_version()
            output = Path(tmp)
            feature = output / "wavefoundry-1.6.0.ptest.zip"
            feature.write_bytes(b"feature")
            internal = {
                "bridge": output / "internal-bridge.zip",
                "selection": output / "internal-selection.json",
            }

            def emit_extra_package(*_args, **_kwargs):
                (output / "wavefoundry-upgrade-extra.pyz").write_bytes(b"extra")
                (output / "wavefoundry-upgrade-1.6.0.ptest.json").write_text(
                    "{}", encoding="utf-8"
                )
                return feature

            argv = [
                "build_pack.py",
                "--version",
                "1.6.0",
                "--output",
                str(output),
                "--release-dry-run",
                "--with-models",
            ]
            stderr = io.StringIO()
            self.enterContext(contextlib.redirect_stderr(stderr))
            model = output / "wavefoundry-models-3.zip"

            def emit_model(*_args, **_kwargs):
                model.write_bytes(b"models")
                return model

            model_build = self.enterContext(
                patch("model_bundle.build_bundle", side_effect=emit_model)
            )
            with patch.object(sys, "argv", argv), patch.object(
                build_pack, "_reexec_with_venv_if_needed"
            ), patch.object(
                build_pack, "find_repo_root", return_value=root
            ), patch.object(
                build_pack, "_current_build_suffix", return_value="ptest"
            ), patch.object(
                build_pack, "_check_git_working_tree_clean"
            ), patch.object(
                build_pack, "_check_on_main_branch"
            ), patch.object(
                build_pack, "_check_tag_does_not_exist"
            ), patch.object(
                build_pack, "_check_gh_authenticated"
            ), patch.object(
                build_pack, "_extract_changelog_section", return_value="release notes"
            ), patch.object(
                build_pack, "_assemble_release_notes", return_value="assembled notes"
            ), patch.object(
                build_pack, "check_docs_gate"
            ), patch.object(
                build_pack, "_check_release_qualification", return_value=_QUALIFICATION_SECTION
            ) as qualification_gate, patch.object(
                build_pack, "_current_framework_inputs_hash", return_value="a" * 64
            ), patch.object(
                build_pack, "_warn_on_same_semver_collision"
            ), patch.object(
                build_pack, "build_zip", return_value=feature
            ), patch.object(
                build_pack, "build_protocol_bridge_artifacts", return_value=internal
            ), patch.object(
                build_pack, "build_upgrade_bundle", side_effect=emit_extra_package
            ), patch.object(
                build_pack, "_run_release_orchestration"
            ) as orchestration:
                with self.assertRaises(SystemExit) as raised:
                    build_pack.main()

            self.assertEqual(raised.exception.code, 1)
            model_build.assert_called_once_with(output)
            qualification_gate.assert_called_once()
            orchestration.assert_not_called()
            self.assertIn("unexpected current-build package(s)", stderr.getvalue())
            self.assertIn("wavefoundry-upgrade-extra.pyz", stderr.getvalue())
            self.assertIn("wavefoundry-upgrade-1.6.0.ptest.json", stderr.getvalue())
            refusals = [
                line for line in stderr.getvalue().splitlines() if line.startswith("error:")
            ]
            self.assertEqual(len(refusals), 1, stderr.getvalue())
            self.assertNotIn(model.name, refusals[0])

    def test_public_artifact_census_includes_bridge_composition_json(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            before = build_pack._public_package_snapshot(output)
            expected = output / "wavefoundry-1.6.0.ptest.zip"
            expected.write_bytes(b"package")
            composition = output / "wavefoundry-upgrade-1.6.0.ptest.json"
            composition.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(
                RuntimeError,
                "wavefoundry-upgrade-1.6.0.ptest.json",
            ):
                build_pack._enforce_single_public_package(
                    output,
                    expected,
                    before,
                )

    def test_release_main_rejects_preexisting_special_upgrade_artifact(self):
        import contextlib
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo_with_version()
            output = Path(tmp)
            stale = output / "wavefoundry-upgrade-1.15.0.stale.pyz"
            stale.write_bytes(b"stale")
            feature = output / "wavefoundry-1.6.0.ptest.zip"
            argv = [
                "build_pack.py",
                "--version",
                "1.6.0",
                "--output",
                str(output),
                "--release-dry-run",
                "--with-models",
            ]
            stderr = io.StringIO()
            self.enterContext(contextlib.redirect_stderr(stderr))
            model_build = self.enterContext(patch("model_bundle.build_bundle"))
            with patch.object(sys, "argv", argv), patch.object(
                build_pack, "_reexec_with_venv_if_needed"
            ), patch.object(
                build_pack, "find_repo_root", return_value=root
            ), patch.object(
                build_pack, "_current_build_suffix", return_value="ptest"
            ), patch.object(
                build_pack, "_check_git_working_tree_clean"
            ), patch.object(
                build_pack, "_check_on_main_branch"
            ), patch.object(
                build_pack, "_check_tag_does_not_exist"
            ), patch.object(
                build_pack, "_check_gh_authenticated"
            ), patch.object(
                build_pack, "_extract_changelog_section", return_value="release notes"
            ), patch.object(
                build_pack, "_assemble_release_notes", return_value="assembled notes"
            ), patch.object(
                build_pack, "check_docs_gate"
            ), patch.object(
                build_pack, "_check_release_qualification", return_value=_QUALIFICATION_SECTION
            ) as qualification_gate, patch.object(
                build_pack, "_current_framework_inputs_hash", return_value="a" * 64
            ), patch.object(
                build_pack, "_warn_on_same_semver_collision"
            ), patch.object(
                build_pack, "build_zip", return_value=feature
            ) as build:
                with self.assertRaises(SystemExit) as raised:
                    build_pack.main()

            self.assertEqual(raised.exception.code, 1)
            build.assert_not_called()
            model_build.assert_not_called()
            qualification_gate.assert_called_once()
            self.assertIn(
                "stale public bridge/composition artifact(s)", stderr.getvalue()
            )
            self.assertIn("wavefoundry-upgrade-1.15.0.stale.pyz", stderr.getvalue())
            self.assertEqual(stale.read_bytes(), b"stale")

    def test_release_main_rejects_feature_only_release_before_build(self):
        root = self._repo_with_version()
        argv = ["build_pack.py", "--version", "1.6.0", "--release-dry-run"]
        with patch.object(sys, "argv", argv), patch.object(
            build_pack, "_reexec_with_venv_if_needed"
        ), patch.object(
            build_pack, "find_repo_root", return_value=root
        ), patch.object(build_pack, "build_zip") as build:
            with self.assertRaises(SystemExit) as raised:
                build_pack.main()
        self.assertEqual(raised.exception.code, 1)
        build.assert_not_called()

    def test_commit_message_carries_the_version_stamp(self):
        root = self._repo_with_version("1.6.0+ptest")
        rec = self._Recorder()
        with patch("build_pack.subprocess.run", rec):
            build_pack._run_release_orchestration(
                root, "1.6.0", self._asset("x.zip"), "notes", dry_run=False,
            )
        commit_call = next(c for c in rec.calls if c[:2] == ["git", "commit"])
        self.assertIn("Bump VERSION to 1.6.0+ptest after release", commit_call)

    def test_dry_run_takes_no_side_effects_and_shows_commit_before_tag(self):
        import io, contextlib
        root = self._repo_with_version()
        rec = self._Recorder()
        buf = io.StringIO()
        with patch("build_pack.subprocess.run", rec), contextlib.redirect_stderr(buf):
            build_pack._run_release_orchestration(
                root, "1.6.0", self._asset("x.zip"), "notes", dry_run=True,
            )
        # No git/gh side-effects beyond the tag-message git-log lookup.
        side_effects = [c for c in rec.calls if c[:2] in (["git", "commit"], ["git", "tag"], ["gh", "release"])]
        self.assertEqual(side_effects, [], "dry-run must not commit/tag/release")
        out = buf.getvalue()
        self.assertLess(out.index("git commit"), out.index(f"git tag -a v1.6.0"))
        self.assertIn("git push origin HEAD:main", out)


# ---------------------------------------------------------------------------
# Install-log / install-entry-doc templates (wave 1p35d / change 1p35f)
# ---------------------------------------------------------------------------


class InstallTemplateInjectionTests(unittest.TestCase):
    """Tests for the root bootstrap entry and framework-tree install assets."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _build(self, version="1.0.0", build_prefix="2tm5"):
        return build_pack.build_zip(
            self.tmp, version, build_prefix,
            write_version=False, update_manifest=False,
        )

    def _zip_names(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            return zf.namelist()

    def _zip_read(self, zip_path, arcname):
        with zipfile.ZipFile(zip_path) as zf:
            return zf.read(arcname).decode("utf-8")

    def test_install_wavefoundry_md_at_zip_root(self):
        """AC-7: install-wavefoundry.md ships at the zip root, not under .wavefoundry/."""
        zp = self._build()
        names = self._zip_names(zp)
        self.assertIn("install-wavefoundry.md", names)
        self.assertNotIn(".wavefoundry/install-wavefoundry.md", names)

    def test_install_log_template_ships_in_framework_tree(self):
        """AC-6: install-log.template.md ships inside the framework tree (not at zip root).

        The agent copies it to .wavefoundry/install-log.md on first install;
        the live log is never in the zip (preserved across upgrades).
        """
        zp = self._build()
        names = self._zip_names(zp)
        self.assertIn(".wavefoundry/framework/install/install-log.template.md", names)
        # Live log MUST NOT be in the zip — that's the operator-preserved instance.
        self.assertNotIn("install-log.md", names)
        self.assertNotIn(".wavefoundry/install-log.md", names)
        self.assertNotIn("wavefoundry-install-log.md", names)

    def test_fresh_install_assets_ship_in_framework_tree(self):
        names = set(self._zip_names(self._build()))
        expected = {
            ".wavefoundry/framework/install/plan-template.md",
            ".wavefoundry/framework/install/workflow-config.defaults.json",
        }
        self.assertTrue(
            expected.issubset(names),
            f"missing fresh-install assets: {sorted(expected - names)}",
        )

    def test_techdocs_baseline_templates_ship_in_framework_tree(self):
        """Wave 1vj4e (1vj4d AC-6): the three Backstage/TechDocs templates ship under
        `*.template.*` names (never a literal catalog-info.yaml a Backstage location glob
        could ingest) and travel with the framework tree scan."""
        names = set(self._zip_names(self._build()))
        expected = {
            ".wavefoundry/framework/install/catalog-info.template.yaml",
            ".wavefoundry/framework/install/mkdocs.template.yml",
            ".wavefoundry/framework/install/techdocs-index.template.md",
        }
        self.assertTrue(expected.issubset(names), f"missing techdocs templates: {sorted(expected - names)}")
        self.assertNotIn(".wavefoundry/framework/install/catalog-info.yaml", names)
        self.assertNotIn(".wavefoundry/framework/install/mkdocs.yml", names)
        # The generated trio itself is project state, never a pack member.
        for rel in ("catalog-info.yaml", "mkdocs.yml", "docs/index.md"):
            self.assertNotIn(rel, names)
        self.assertIn(".wavefoundry/framework/scripts/techdocs_baseline.py", names)

    def test_lifecycle_prompt_baselines_ship_in_framework_tree(self):
        zp = self._build()
        names = set(self._zip_names(zp))
        expected = {
            ".wavefoundry/framework/install/lifecycle-prompts/"
            + prompt
            for prompt in (
                "create-wave.prompt.md",
                "prepare-wave.prompt.md",
                "implement-wave.prompt.md",
                "review-wave.prompt.md",
                "close-wave.prompt.md",
                "memory-review.prompt.md",
                "review-plan.prompt.md",
            )
        }
        self.assertTrue(expected.issubset(names), expected - names)
        self.assertIn(
            ".wavefoundry/framework/seeds/240-memory-review.prompt.md",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/seeds/175-review-plan.prompt.md",
            names,
        )
        self.assertNotIn(
            ".wavefoundry/framework/seeds/175-interrogate-plan.prompt.md",
            names,
        )
        self.assertNotIn(
            ".wavefoundry/framework/install/lifecycle-prompts/interrogate-plan.prompt.md",
            names,
        )

    def test_install_md_no_longer_present(self):
        """AC-8: INSTALL.md is removed; not aliased."""
        zp = self._build()
        names = self._zip_names(zp)
        self.assertNotIn("INSTALL.md", names)

    def test_install_wavefoundry_md_has_version_substituted(self):
        """AC-7: {{version}} placeholder is substituted with the build version."""
        zp = self._build(version="1.5.0")
        body = self._zip_read(zp, "install-wavefoundry.md")
        self.assertIn("1.5.0", body)
        self.assertNotIn("{{version}}", body)

    def test_install_log_template_preserves_generated_at_placeholder(self):
        """The {{generated_at}} placeholder is NOT substituted at packaging time.

        Substitution happens when the agent copies the template to
        .wavefoundry/install-log.md on first install; build_pack ships
        the template verbatim.
        """
        zp = self._build()
        body = self._zip_read(zp, ".wavefoundry/framework/install/install-log.template.md")
        self.assertIn("{{generated_at}}", body)

    def test_install_log_template_contains_phase_1_and_phase_2(self):
        """AC-4 + AC-5: template has both phase headings and the boundary marker."""
        zp = self._build()
        body = self._zip_read(zp, ".wavefoundry/framework/install/install-log.template.md")
        self.assertIn("Phase 1", body)
        self.assertIn("Phase 2", body)
        # Restart marker between phases (Phase 1 last row mentions restart agent).
        self.assertIn("restart", body.lower())

    def test_install_log_template_phase_2_starts_with_wf_audit_install(self):
        """AC-5: first Phase 2 row is a wf_audit_install call."""
        zp = self._build()
        body = self._zip_read(zp, ".wavefoundry/framework/install/install-log.template.md")
        heading = "## Phase 2 — Project discovery (MCP required)"
        self.assertIn(heading, body)
        phase_2_section = body.split(heading, 1)[1]
        first_row = next(
            line for line in phase_2_section.splitlines()
            if line.startswith("- [")
        )
        self.assertIn("2.1", first_row)
        self.assertIn("wf_audit_install", first_row)

    def test_install_wavefoundry_md_explains_template_to_log_copy(self):
        """The entry doc instructs the agent to copy template -> .wavefoundry/install-log.md."""
        zp = self._build()
        body = self._zip_read(zp, "install-wavefoundry.md")
        self.assertIn(".wavefoundry/install-log.md", body)
        self.assertIn("install-log.template.md", body)


class ReadmeVersionBadgeStampTests(unittest.TestCase):
    """Wave 1p5s1: _stamp_readme_version_badge rewrites the static version badge."""

    def _repo(self, readme_text):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "README.md").write_text(readme_text, encoding="utf-8")
        return root

    _BADGE = "[![Version](https://img.shields.io/badge/version-1.0.0-purple)](url)\n"
    _OTHER = (
        "[![MCP](https://img.shields.io/badge/MCP-local_server-0a7ea4)](m)\n"
        "[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](L)\n"
    )

    def test_rewrites_version(self):
        root = self._repo(self._BADGE + self._OTHER)
        self.assertTrue(build_pack._stamp_readme_version_badge(root, "1.6.3"))
        text = (root / "README.md").read_text()
        self.assertIn("badge/version-1.6.3-purple", text)
        self.assertNotIn("version-1.0.0-purple", text)
        # other badges untouched
        self.assertIn("badge/MCP-local_server-0a7ea4", text)
        self.assertIn("badge/License-Apache_2.0-blue.svg", text)

    def test_idempotent(self):
        root = self._repo(self._BADGE)
        build_pack._stamp_readme_version_badge(root, "1.6.3")
        # second call: already at 1.6.3 → no change
        self.assertFalse(build_pack._stamp_readme_version_badge(root, "1.6.3"))

    def test_noop_when_no_badge(self):
        root = self._repo("# Project\n\nNo version badge here.\n")
        self.assertFalse(build_pack._stamp_readme_version_badge(root, "1.6.3"))

    def test_noop_when_readme_absent(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(build_pack._stamp_readme_version_badge(Path(tmp), "1.6.3"))


class BuildPackVenvActivationTests(unittest.TestCase):
    """Wave 1p802: ``_reexec_with_venv_if_needed`` (name kept for back-compat) now delegates to
    ``venv_bootstrap.activate_tool_venv`` — in-process activation, NO ``os.execv``/re-exec. The numpy
    short-circuit stays in build_pack (an interpreter that already has numpy never re-activates)."""

    def test_activates_venv_when_numpy_absent(self):
        with patch.dict(sys.modules, {"numpy": None}), \
             patch.object(build_pack.venv_bootstrap, "activate_tool_venv") as activate:
            build_pack._reexec_with_venv_if_needed()
            activate.assert_called_once()

    def test_short_circuits_when_numpy_present(self):
        # numpy importable → no activation needed (CI env with deps installed).
        import types
        fake_numpy = types.ModuleType("numpy")
        with patch.dict(sys.modules, {"numpy": fake_numpy}), \
             patch.object(build_pack.venv_bootstrap, "activate_tool_venv") as activate:
            build_pack._reexec_with_venv_if_needed()
            activate.assert_not_called()


class VendoredScriptCheckTests(unittest.TestCase):
    """Wave 1zv8c / 1zv8a: build_zip refuses a pack whose vendored scripts differ from their pins."""

    def setUp(self):
        import hashlib
        import tempfile
        import shutil
        self._tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tmp = Path(self._tmp)
        self.fw = self.tmp / "fw"
        vendor = self.fw / "dashboard" / "vendor"
        (vendor / "demo").mkdir(parents=True)
        self.script = vendor / "demo" / "demo.js"
        self.script.write_bytes(b"console.log(1);\n")
        sha = hashlib.sha256(b"console.log(1);\n").hexdigest()
        (vendor / "README.md").write_text(
            "| File | Package | Source in the tarball | Licence | SHA-256 |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"| `demo/demo.js` | `demo@1.0.0` | `package/demo.js` | MIT (`demo/LICENSE`) | `{sha}` |\n\n"
            "## Registry integrity\n\n"
            "| Package | Tarball | `dist.integrity` |\n"
            "| --- | --- | --- |\n"
            "| `demo@1.0.0` | `https://registry.npmjs.org/demo/-/demo-1.0.0.tgz` | `sha512-AAAA` |\n",
            encoding="utf-8",
        )

    def _build(self):
        return build_pack.build_zip(
            self.tmp, "1.0.0", "2tm5", framework_dir=self.fw,
            write_version=False, update_manifest=False, inject_install_templates=False,
        )

    def test_build_proceeds_when_every_vendored_file_matches(self):
        self.assertTrue(self._build().exists())

    def test_build_refuses_a_changed_vendored_file_naming_it(self):
        self.script.write_bytes(b"console.log(2);\n")
        with self.assertRaises(SystemExit) as ctx:
            self._build()
        self.assertIn("demo/demo.js", str(ctx.exception))
        self.assertEqual(list(self.tmp.glob("wavefoundry-*.zip")), [])


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# Release qualification gate, build provenance and SHA256SUMS (wave 20wq7)
# ---------------------------------------------------------------------------

import copy  # noqa: E402
import hashlib  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

import qualification_report  # noqa: E402
from record_layout_support import load_profile  # noqa: E402


class ReleaseQualificationGateTests(unittest.TestCase):
    HASH = "a" * 64

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        shutil.copytree(SCRIPTS_DIR / "tests/fixtures/profiles",
                        self.root / build_pack.FRAMEWORK_REL / "scripts/tests/fixtures/profiles")
        (self.root / ".wavefoundry/cache/qualification").mkdir(parents=True)
        for profile in ("default", "second", "declared"):
            self.write(profile, self.report(profile))

    def report(self, profile, skips=None):
        """A realistic report, as ExactReaderTests builds it."""
        skips = skips or []
        report = {"owner": qualification_report.OWNER, "schema_version": 1, "run_id": "f" * 32,
                  "complete": True, "availability": "executed", "returncode": 0,
                  "identity": {"source_hash": self.HASH, "profile": profile},
                  "scope": {"kind": "full", "discovered_workers": ["test_one.py"]},
                  "expected_workers": ["test_one.py"], "observed_workers": ["test_one.py"],
                  "workers": [{"name": "test_one.py", "returncode": 0, "tests": 2, "skipped": len(skips),
                               "terminal": True, "complete": True, "issues": [], "skips": skips}]}
        if profile != "default":
            definition = load_profile(profile)
            report["applied_profile"] = copy.deepcopy(definition["modules"])
            report["identity"].update(profile_input_hash=qualification_report.digest(definition),
                                      applied_profile_hash=qualification_report.digest(report["applied_profile"]))
            # As in a real profile run: the executed hash covers the rewritten copy.
            report["executed_identity"] = {"profile": profile, "source_hash": "d" * 64}
        return report

    def failing(self, profile):
        report = self.report(profile)
        report["returncode"] = 1
        report["workers"][0]["returncode"] = 1
        return report

    def write(self, profile, report):
        qualification_report.write_report(self.root, f".wavefoundry/cache/qualification/{profile}.json", report)

    def gate(self, exceptions=None):
        return build_pack._check_release_qualification(self.root, exceptions or {}, inputs_hash=self.HASH)

    def assertRefused(self, pattern, exceptions=None):
        with self.assertRaisesRegex(RuntimeError, pattern):
            self.gate(exceptions)

    def test_all_three_current_reports_pass_and_are_listed(self):
        section = self.gate()
        self.assertTrue(section.startswith("### Qualification\n"))
        for profile in ("default", "second", "declared"):
            self.assertIn(f"- {profile}: passed, 2 tests in 1 worker files, 0 skips (source aaaaaaaaaaaa)", section)

    def test_default_report_refusals_name_the_profile_and_reason(self):
        cases = {
            "missing": (None, r"for default is missing.*--qualification-report"),
            "red": ({"returncode": 1}, r"default qualification does not pass \(qualification did not pass\)"),
            "non-full scope": ({"scope": {"kind": "compatibility", "discovered_workers": ["test_one.py"]}},
                               r"default qualification report is not a full run"),
            "other profile": ({"identity": {"source_hash": self.HASH, "profile": "second"}},
                              r"does not name profile default"),
            "stale": ({"identity": {"source_hash": "b" * 64, "profile": "default"}},
                      r"qualification report for default is stale"),
        }
        path = self.root / ".wavefoundry/cache/qualification/default.json"
        for label, (change, pattern) in cases.items():
            with self.subTest(label=label):
                if change is None:
                    path.unlink()
                else:
                    self.write("default", {**self.report("default"), **change})
                # Even an exception for every other profile never excuses the default.
                self.assertRefused(pattern, {"second": "timing", "declared": "timing"})
                self.write("default", self.report("default"))

    def test_failing_profile_refuses_without_an_exception(self):
        for profile in ("second", "declared"):
            with self.subTest(profile=profile):
                self.write(profile, self.failing(profile))
                self.assertRefused(rf"{profile} qualification refused: qualification did not pass.*"
                                   rf"--accept-qualification-exception {profile}=REASON")
                self.write(profile, self.report(profile))

    def test_exception_admits_a_failing_current_report_and_names_it(self):
        failing = self.failing("second")
        self.assertNotEqual(failing["executed_identity"]["source_hash"], self.HASH)
        self.write("second", failing)
        section = self.gate({"second": "renamed-profile timing p95 above budget"})
        self.assertIn("- second: accepted exception: renamed-profile timing p95 above budget "
                      "(refusal: qualification did not pass; failing workers: test_one.py; "
                      "2 tests in 1 worker files, 0 skips, source aaaaaaaaaaaa)", section)
        self.assertIn("- declared: passed", section)

    def test_exception_admits_a_skip_difference_on_a_valid_report(self):
        extra = {"id": "test_one.C.test_x", "reason": "unexpected", "default_profile_only": None}
        self.write("declared", self.report("declared", [extra]))
        self.assertRefused(r"declared qualification refused: declared profile has unexpected skips")
        self.assertIn("- declared: accepted exception: known skip", self.gate({"declared": "known skip"}))

    def test_exception_never_admits_missing_stale_or_structurally_invalid_reports(self):
        exceptions = {"second": "timing"}
        (self.root / ".wavefoundry/cache/qualification/second.json").unlink()
        self.assertRefused(r"for second is missing", exceptions)
        stale = self.failing("second"); stale["identity"]["source_hash"] = "b" * 64
        self.write("second", stale)
        self.assertRefused(r"for second is stale", exceptions)
        wrong = self.failing("second"); wrong["identity"]["profile"] = "declared"
        self.write("second", wrong)
        self.assertRefused(r"does not name profile second", exceptions)
        incomplete = self.failing("second"); incomplete["complete"] = False
        self.write("second", incomplete)
        self.assertRefused(r"second qualification cannot take an exception: qualification incomplete", exceptions)
        provenance = self.failing("second"); provenance["identity"]["applied_profile_hash"] = "e" * 64
        self.write("second", provenance)
        self.assertRefused(r"second qualification cannot take an exception: mismatched applied-profile", exceptions)
        no_executed = self.failing("second"); no_executed.pop("executed_identity")
        self.write("second", no_executed)
        self.assertRefused(r"second qualification cannot take an exception: missing or malformed actual-profile",
                           exceptions)
        scope = self.failing("second"); scope["scope"] = {"kind": "full", "discovered_workers": ["test_two.py"]}
        self.write("second", scope)
        self.assertRefused(r"second qualification cannot take an exception: qualification scope mismatch", exceptions)

    def test_exception_never_admits_a_failure_with_no_failing_worker(self):
        # A runner or repository guard failure: top-level returncode 1, every worker green.
        guard = self.report("second")
        guard["returncode"] = 1
        self.write("second", guard)
        self.assertRefused(r"second qualification cannot take an exception: the run failed with no failing "
                           r"worker \(a runner or repository guard failure\)", {"second": "timing"})

    def test_guard_failure_with_a_skip_difference_still_refuses(self):
        skip = {"id": "test_one.C.test_skip", "reason": "reason", "default_profile_only": None}
        cases = {
            "missing skip or changed reason": ("second", [skip], []),
            "unexpected second-profile skip": ("second", [], [{**skip, "reason": "unmarked"}]),
            "declared profile has unexpected skips": ("declared", [], [skip]),
        }
        for message, (profile, default_skips, profile_skips) in cases.items():
            with self.subTest(message=message):
                self.write("default", self.report("default", default_skips))
                for other in ("second", "declared"):
                    self.write(other, self.report(other, default_skips))
                guard = self.report(profile, profile_skips)
                guard["returncode"] = 1  # every worker green
                self.write(profile, guard)
                self.assertRefused(rf"{profile} qualification cannot take an exception: the run failed with no "
                                   rf"failing worker", {profile: "known"})

    def test_each_listed_skip_refusal_is_admitted_and_recorded(self):
        skip = {"id": "test_one.C.test_skip", "reason": "reason", "default_profile_only": None}
        cases = {
            "missing skip or changed reason": ("second", [skip], []),
            "unexpected second-profile skip": ("second", [], [{**skip, "reason": "unmarked"}]),
            "declared profile has unexpected skips": ("declared", [], [skip]),
        }
        self.assertEqual(set(cases), set(build_pack._EXCEPTABLE_SKIP_REFUSALS))
        for message, (profile, default_skips, profile_skips) in cases.items():
            with self.subTest(message=message):
                self.write("default", self.report("default", default_skips))
                for other in ("second", "declared"):
                    self.write(other, self.report(other, default_skips))
                self.write(profile, self.report(profile, profile_skips))
                self.assertRefused(rf"{profile} qualification refused: {message}")
                self.assertIn(f"- {profile}: accepted exception: known (refusal: {message}; failing workers: none",
                              self.gate({profile: "known"}))
                failing = self.report(profile, profile_skips)
                failing["returncode"] = 1
                failing["workers"][0]["returncode"] = 1
                self.write(profile, failing)
                self.assertIn(f"refusal: qualification did not pass; skip difference: {message}; "
                              "failing workers: test_one.py", self.gate({profile: "known"}))

    def test_default_scope_must_cover_its_own_workers(self):
        bad = self.report("default")
        bad["scope"] = {"kind": "full", "discovered_workers": ["test_one.py", "test_two.py"]}
        self.write("default", bad)
        self.assertRefused(r"default qualification report is not a full run")

    def test_comparator_errors_other_than_value_error_refuse_without_text(self):
        self.write("second", self.failing("second"))
        with patch.object(qualification_report, "compare", side_effect=KeyError("secret/path")):
            with self.assertRaises(RuntimeError) as raised:
                self.gate({"second": "timing"})
        self.assertIn("could not be compared (KeyError)", str(raised.exception))
        self.assertNotIn("secret/path", str(raised.exception))

    def test_runner_outside_the_repository_refuses(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, True)
        (outside / "run_tests.py").write_text("", encoding="utf-8")
        scripts = self.root / ".wavefoundry/framework/scripts"
        try:
            (scripts / "run_tests.py").symlink_to(outside / "run_tests.py")
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(RuntimeError, "resolves outside this repository"):
            build_pack._current_framework_inputs_hash(self.root)

    def test_exception_for_a_passing_profile_is_refused_as_stale(self):
        self.assertRefused(r"qualification exception for declared is stale: its report passes", {"declared": "x"})

    def test_exception_values_are_parsed_strictly(self):
        parse = build_pack._parse_qualification_exceptions
        self.assertEqual(parse(["second=" + "r" * 500]), {"second": "r" * 500})
        self.assertEqual(parse(["declared=a=b"]), {"declared": "a=b"})
        bad = {
            "default": ["default=timing"], "unknown": ["third=timing"], "no reason marker": ["second"],
            "duplicate": ["second=a", "second=b"], "empty": ["second="], "blank": ["second=   "],
            "501 characters": ["second=" + "r" * 501], "multi-line": ["second=a\nb"],
            "line separator": ["second=a b"], "control": ["second=a\x07b"], "C1 control": ["second=a\x85b"],
            "format character": ["second=a\u202eb"],
        }
        for label, values in bad.items():
            with self.subTest(label=label), self.assertRaises(RuntimeError):
                parse(values)

    def test_inputs_hash_refuses_when_the_runner_is_absent_or_unloadable(self):
        with self.assertRaisesRegex(RuntimeError, "is absent"):
            build_pack._current_framework_inputs_hash(self.root)
        runner = self.root / ".wavefoundry/framework/scripts/run_tests.py"
        runner.write_text("raise SystemExit(2)\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "could not be loaded"):
            build_pack._current_framework_inputs_hash(self.root)
        import lifecycle_gate_support
        fake = MagicMock(); fake._hash_inputs.return_value = "short"
        with patch.object(lifecycle_gate_support, "_load_framework_test_runner", return_value=fake) as loader:
            with self.assertRaisesRegex(RuntimeError, "malformed"):
                build_pack._current_framework_inputs_hash(self.root)
        loader.assert_called_once_with(runner)
        fake._hash_inputs.return_value = self.HASH
        with patch.object(lifecycle_gate_support, "_load_framework_test_runner", return_value=fake) as loader:
            self.assertEqual(build_pack._current_framework_inputs_hash(self.root), self.HASH)
        loader.assert_called_once_with(runner)

    def test_real_inputs_hash_matches_the_runner_hash(self):
        import lifecycle_gate_support
        runner = SCRIPTS_DIR / "run_tests.py"
        module = lifecycle_gate_support._load_framework_test_runner(runner)
        self.assertIsNotNone(module)
        self.assertEqual(build_pack._current_framework_inputs_hash(SCRIPTS_DIR.parents[2]), module._hash_inputs())

    def _main(self, argv_tail, **patches):
        import contextlib
        import io
        version = self.root / build_pack.FRAMEWORK_REL / "VERSION"
        version.write_bytes(b"9.9.8+pold\n")
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\n## [9.9.9] - 2026-10-17\n\n- change\n",
                                                encoding="utf-8")
        argv = ["build_pack.py", "--version", "9.9.9", "--output", str(self.root), "--with-models", *argv_tail]
        stderr = io.StringIO()
        code = 0
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(sys, "argv", argv))
            for name in ("_reexec_with_venv_if_needed", "_check_git_working_tree_clean", "_check_on_main_branch",
                         "_check_tag_does_not_exist", "_check_gh_authenticated", "_warn_on_same_semver_collision"):
                stack.enter_context(patch.object(build_pack, name))
            stack.enter_context(patch.object(build_pack, "find_repo_root", return_value=self.root))
            stack.enter_context(patch.object(build_pack, "_current_build_suffix", return_value="ptest"))
            gate = stack.enter_context(patch.object(build_pack, "check_docs_gate"))
            build = stack.enter_context(patch.object(build_pack, "build_zip"))
            for name, value in patches.items():
                stack.enter_context(patch.object(build_pack, name, **value))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            try:
                build_pack.main()
            except SystemExit as exc:
                code = exc.code
        return code, stderr.getvalue(), build, gate, version.read_bytes()

    def test_release_dry_run_refuses_before_build_when_a_report_is_missing(self):
        (self.root / ".wavefoundry/cache/qualification/declared.json").unlink()
        code, err, build, gate, version = self._main(
            ["--release-dry-run"], _current_framework_inputs_hash={"return_value": self.HASH})
        self.assertEqual(code, 1)
        self.assertIn("release preflight failed: qualification report for declared is missing", err)
        build.assert_not_called()
        gate.assert_not_called()
        self.assertEqual(version, b"9.9.8+pold\n")

    def test_tree_change_between_preflight_and_build_refuses(self):
        code, err, build, gate, _ = self._main(
            ["--release-dry-run"], _current_framework_inputs_hash={"side_effect": [self.HASH, "b" * 64]})
        self.assertEqual(code, 1)
        self.assertIn("changed after release qualification was checked", err)
        gate.assert_called_once()
        build.assert_not_called()

    def test_dry_run_prints_the_section_and_passes_no_release_tag(self):
        build = MagicMock(side_effect=RuntimeError("stop after build_zip is called"))
        code, err, _build, _gate, _ = self._main(
            ["--release-dry-run"], _current_framework_inputs_hash={"return_value": self.HASH},
            build_zip={"new": build})
        self.assertEqual(code, 1)
        self.assertIn("[--release-dry-run] release notes qualification section:", err)
        self.assertIn("- declared: passed, 2 tests in 1 worker files", err)
        self.assertIsNone(build.call_args.kwargs["release_tag"])
        code, _err, _build, _gate, _ = self._main(
            ["--release"], _current_framework_inputs_hash={"return_value": self.HASH},
            build_zip={"new": build})
        self.assertEqual(build.call_args.kwargs["release_tag"], "v9.9.9")

    def test_exception_flag_is_refused_outside_release_modes(self):
        code, err, build, _gate, _ = self._main(["--accept-qualification-exception", "second=x"])
        self.assertEqual(code, 1)
        self.assertIn("applies only with --release or --release-dry-run", err)
        build.assert_not_called()


class BuildProvenanceTests(unittest.TestCase):
    GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@localhost", "-c", "commit.gpgsign=false"]

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.out = self.base / "out"
        self.out.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env["GIT_CONFIG_NOSYSTEM"] = "1"

    def git(self, cwd, *args, check=True):
        return subprocess.run([*self.GIT, *args], cwd=str(cwd), check=check, capture_output=True,
                              text=True, env=self.env)

    def framework(self, repo):
        fw = repo / ".wavefoundry" / "framework"
        fw.mkdir(parents=True, exist_ok=True)
        (fw / "seed.md").write_text("seed\n", encoding="utf-8")
        return fw

    def checkout(self, name="repo"):
        repo = self.base / name
        fw = self.framework(repo)
        self.git(repo, "init", "-q")
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "--no-verify", "-m", "one")
        return repo, fw

    def build(self, fw, **kwargs):
        path = build_pack.build_zip(self.out, "1.0.0", "2tm5", framework_dir=fw, write_version=False,
                                    update_manifest=False, inject_install_templates=False, **kwargs)
        with zipfile.ZipFile(path) as zf:
            record = json.loads(zf.read(".wavefoundry/framework/BUILD-PROVENANCE.json"))
            manifest = zf.read(".wavefoundry/framework/MANIFEST").decode("utf-8").splitlines()
        path.unlink()
        return record, manifest

    def test_record_has_exactly_six_fields_and_is_in_the_manifest(self):
        repo, fw = self.checkout()
        record, manifest = self.build(fw)
        head = self.git(repo, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(record, {"schema_version": 1, "release_version": "1.0.0+2tm5", "build_id": "2tm5",
                                  "source_commit": head, "source_tree_clean": True, "release_tag": None})
        self.assertIn("BUILD-PROVENANCE.json", manifest)
        self.assertFalse((fw / "BUILD-PROVENANCE.json").exists())

    def test_dirty_tree_release_tag_and_two_commits(self):
        repo, fw = self.checkout()
        first, _ = self.build(fw)
        (repo / "untracked.txt").write_text("x\n", encoding="utf-8")
        dirty, _ = self.build(fw, release_tag="v1.0.0")
        self.assertIs(dirty["source_tree_clean"], False)
        self.assertEqual(dirty["release_tag"], "v1.0.0")
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "--no-verify", "-m", "two")
        second, _ = self.build(fw)
        self.assertRegex(second["source_commit"], r"^[0-9a-f]{40}$")
        self.assertNotEqual(first["source_commit"], second["source_commit"])
        self.assertIsNone(second["release_tag"])

    def test_outside_a_checkout_or_nested_in_another_both_source_fields_are_null(self):
        loose = self.base / "loose"
        fw = self.framework(loose)
        self.assertNotEqual(self.git(loose, "rev-parse", "--show-toplevel", check=False).returncode, 0)
        record, _ = self.build(fw)
        self.assertIsNone(record["source_commit"])
        self.assertIsNone(record["source_tree_clean"])
        outer, _ = self.checkout("outer")
        nested = outer / "vendor" / "inner"
        fw = self.framework(nested)
        self.assertEqual(Path(self.git(nested, "rev-parse", "--show-toplevel").stdout.strip()).resolve(), outer)
        record, _ = self.build(fw)
        self.assertIsNone(record["source_commit"])
        self.assertIsNone(record["source_tree_clean"])

    def test_inherited_git_dir_cannot_supply_the_commit(self):
        outer, _ = self.checkout("outer")
        loose = self.base / "loose"
        fw = self.framework(loose)
        with patch.dict(os.environ, {"GIT_DIR": str(outer / ".git"), "GIT_WORK_TREE": str(loose)}):
            record, _ = self.build(fw)
        self.assertIsNone(record["source_commit"])

    def test_failed_build_leaves_no_generated_file(self):
        _repo, fw = self.checkout()
        generated = [fw / "MANIFEST", fw / build_pack.PROTOCOL_METADATA_FILENAME, fw / "BUILD-PROVENANCE.json"]

        def fail(*_args, **_kwargs):
            for path in generated:
                self.assertTrue(path.exists(), path)
            raise RuntimeError("forced zip failure")

        with patch.object(build_pack.zipfile, "ZipFile", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "forced zip failure"):
                build_pack.build_zip(self.out, "1.0.0", "2tm5", framework_dir=fw, write_version=False,
                                     update_manifest=False, inject_install_templates=False)
        for path in generated:
            self.assertFalse(path.exists(), path)


class ReleaseChecksumTests(unittest.TestCase):
    class _Recorder:
        def __init__(self, gh_returncode=0):
            self.calls = []
            self.sums = None
            self.sums_path = None
            self.notes_path = None
            self.gh_returncode = gh_returncode

        def __call__(self, argv, **kwargs):
            self.calls.append(list(argv))

            class _CP:
                def __init__(self, rc, out="", err=""):
                    self.returncode, self.stdout, self.stderr = rc, out, err

            if argv[:3] == ["gh", "release", "create"]:
                self.sums_path = Path(next(a for a in argv if a.endswith("SHA256SUMS")))
                self.sums = self.sums_path.read_bytes()
                self.notes_path = Path(argv[argv.index("--notes-file") + 1])
                return _CP(self.gh_returncode, err="upload failed" if self.gh_returncode else "")
            if argv[:3] == ["git", "diff", "--cached"]:
                return _CP(1)
            if argv[:2] == ["git", "log"]:
                return _CP(0, "Close wave x\n")
            return _CP(0, "ok")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.root = self.base / "repo"
        version = self.root / build_pack.FRAMEWORK_REL / "VERSION"
        version.parent.mkdir(parents=True)
        version.write_text("1.6.0+ptest\n", encoding="utf-8")
        self.feature = self.asset("wavefoundry-1.6.0.ptest.zip", b"feature")
        self.models = self.asset("wavefoundry-models-3.zip", b"models")
        self.combined = self.asset("wavefoundry-1.6.0.ptest.with-models.zip", b"combined")

    def asset(self, name, body):
        path = self.base / name
        path.write_bytes(body)
        return path

    def expected_lines(self):
        files = [self.feature, self.models, self.combined]
        return [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(files, key=lambda p: p.name)]

    def run_release(self, rec, **kwargs):
        with patch("build_pack.subprocess.run", rec):
            build_pack._run_release_orchestration(self.root, "1.6.0", self.feature, "notes body",
                                                  extra_assets=[self.models, self.combined], **kwargs)

    def test_sums_list_every_other_asset_sorted_with_lf_and_folder_is_removed(self):
        rec = self._Recorder()
        self.run_release(rec, dry_run=False)
        self.assertEqual(rec.sums_path.name, "SHA256SUMS")
        self.assertNotIn(b"\r", rec.sums)
        self.assertTrue(rec.sums.endswith(b"\n"))
        lines = rec.sums.decode("ascii").splitlines()
        self.assertEqual(lines, self.expected_lines())
        self.assertNotEqual(sorted([self.feature, self.models, self.combined], key=lambda p: p.name),
                            [self.feature, self.models, self.combined])
        self.assertFalse(any("SHA256SUMS" in line for line in lines))
        self.assertFalse(rec.sums_path.parent.exists())
        self.assertFalse(rec.sums_path.parent.is_relative_to(self.root))
        gh = next(c for c in rec.calls if c[:3] == ["gh", "release", "create"])
        self.assertEqual(gh[-4:], [str(self.feature), str(self.models), str(self.combined), str(rec.sums_path)])

    def test_failed_upload_keeps_notes_and_sums_and_names_them(self):
        rec = self._Recorder(gh_returncode=1)
        with self.assertRaises(RuntimeError) as raised:
            self.run_release(rec, dry_run=False)
        self.addCleanup(shutil.rmtree, rec.sums_path.parent, True)
        message = str(raised.exception)
        self.assertIn(str(rec.sums_path.parent), message)
        self.assertIn(f"--notes-file {rec.notes_path}", message)
        self.assertIn(str(rec.sums_path), message)
        self.assertEqual(rec.notes_path.read_text(encoding="utf-8"), "notes body")
        self.assertEqual(rec.sums_path.read_bytes(), rec.sums)

    def test_non_plain_asset_name_refuses_before_any_release_step(self):
        bad = self.asset("bad name.zip", b"x")
        rec = self._Recorder()
        with patch("build_pack.subprocess.run", rec), self.assertRaisesRegex(RuntimeError, "not a plain file name"):
            build_pack._run_release_orchestration(self.root, "1.6.0", bad, "notes", dry_run=False)
        self.assertFalse([c for c in rec.calls if c[:2] in (["git", "commit"], ["git", "tag"], ["git", "add"])
                          or c[:1] == ["gh"]])

    def test_reserved_or_duplicate_asset_names_refuse(self):
        reserved = self.asset("SHA256SUMS", b"x")
        other = self.base / "elsewhere"
        other.mkdir()
        duplicate = other / self.models.name
        duplicate.write_bytes(b"copy")
        for assets, pattern in (([self.feature, reserved], "not a plain file name"),
                                ([self.feature, self.models, duplicate], "share the name")):
            with self.subTest(pattern=pattern), self.assertRaisesRegex(RuntimeError, pattern):
                build_pack._release_checksum_lines(assets)

    def test_missing_gh_keeps_the_folder_and_prints_recovery(self):
        rec = self._Recorder()

        def run(argv, **kwargs):
            if argv[:1] == ["gh"]:
                rec.sums_path = Path(next(a for a in argv if a.endswith("SHA256SUMS")))
                raise FileNotFoundError("gh")
            return rec(argv, **kwargs)

        with patch("build_pack.subprocess.run", run), self.assertRaises(RuntimeError) as raised:
            build_pack._run_release_orchestration(self.root, "1.6.0", self.feature, "notes", dry_run=False)
        self.addCleanup(shutil.rmtree, rec.sums_path.parent, True)
        self.assertIn("could not run gh", str(raised.exception))
        self.assertIn(str(rec.sums_path), str(raised.exception))
        self.assertTrue(rec.sums_path.exists())

    def test_dry_run_prints_the_same_lines(self):
        import contextlib
        import io
        buf = io.StringIO()
        rec = self._Recorder()
        with contextlib.redirect_stderr(buf):
            self.run_release(rec, dry_run=True)
        for line in self.expected_lines():
            self.assertIn(line, buf.getvalue())
        self.assertFalse([c for c in rec.calls if c[:1] == ["gh"]])
