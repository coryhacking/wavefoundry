"""Report-only lifecycle drift, including incoming hooks and retained evidence."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import subprocess
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import render_agent_surfaces as renderer
import upgrade_extensions as extensions
import upgrade_lib
import upgrade_wavefoundry as upgrade

CREATE = renderer.vocabulary_profile.prompt_doc("create-wave")
IMPLEMENT = renderer.vocabulary_profile.prompt_doc("implement-wave")


class BaselineDriftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="215a9-baselines-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "target"
        self.root.mkdir()
        self.install = self.root / ".wavefoundry/framework/install"
        self.pack = Path(self.temp.name) / "incoming.zip"

    def put(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode())
        return path

    def fixture(self):
        # Independent literal states: A was shipped, B arrives, Z is an
        # earlier preserved copy. No expected result calls the producer.
        self.put(".wavefoundry/framework/install/lifecycle-prompts/create-wave.prompt.md", "# Create Wave\nA\nLast verified: {{generated_at}}\n")
        self.put(CREATE, "# " + renderer.vocabulary_profile.shortcut_title("create-wave") + "\r\nA\r\nLast verified: 2024-01-02\r\n")
        self.put(".wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md", "A\n")
        self.put(IMPLEMENT, "Z\n")
        self.put(".wavefoundry/framework/install/lifecycle-prompts/memory-review.prompt.md", "B\n")
        self.put("docs/prompts/memory-review.prompt.md", "Z\n")
        self.put(".wavefoundry/framework/install/lifecycle-prompts/review-plan.prompt.md", "A\n")
        self.put("docs/prompts/review-plan.prompt.md", "B\n")
        self.put("docs/plans/plan-template.md", "B\n")
        return {"lifecycle-prompts/create-wave.prompt.md": "# Create Wave\nB\nLast verified: {{generated_at}}\n",
                "lifecycle-prompts/implement-wave.prompt.md": "B\n",
                "lifecycle-prompts/memory-review.prompt.md": "B\n",
                "lifecycle-prompts/review-plan.prompt.md": "B\n", "plan-template.md": "B\n"}

    def make_pack(self, incoming):
        with zipfile.ZipFile(self.pack, "w") as archive:
            for source in SCRIPTS.rglob("*.py"):
                if "tests" in source.relative_to(SCRIPTS).parts or "__pycache__" in source.parts:
                    continue
                archive.write(source, ".wavefoundry/framework/scripts/" + source.relative_to(SCRIPTS).as_posix())
            for name, content in incoming.items():
                archive.writestr(".wavefoundry/framework/install/" + name, content)
        return self.pack

    def ctx(self, dry_run=False):
        # A supported old coordinator context has no new method/capability.
        return types.SimpleNamespace(root=self.root, from_version="1.33.0", to_version="1.34.0", zip_path=self.pack, yes=True, dry_run=dry_run)

    def states(self, findings):
        return {item["file"]: item["detail"].split(":", 1)[0] for item in findings}

    def test_literal_states_dates_crlf_and_preserved_older_copy(self):
        incoming = self.fixture()
        before = {p: p.read_bytes() for p in self.root.rglob("*.md")}
        findings = renderer.lifecycle_baseline_drift(self.root, incoming)
        self.assertEqual(self.states(findings), {
            CREATE: "upstream_changed_local_matches_previous",
            IMPLEMENT: "upstream_changed_local_differs_from_previous",
            "docs/prompts/memory-review.prompt.md": "upstream_unchanged_local_differs",
            "docs/prompts/review-plan.prompt.md": "already_current",
            "docs/plans/plan-template.md": "baseline_unknown"})
        self.assertIn("earlier template update that was never applied", findings[1]["detail"])
        self.assertEqual(findings[-1]["detail"], "baseline_unknown: previous template unavailable; local copy matches incoming template")
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_all_eight_registry_baselines_report_and_all_current_are_omitted(self):
        incoming = {}
        expected = {renderer.vocabulary_profile.prompt_doc(key) for key in (
            "create-wave", "implement-wave", "prepare-wave", "review-wave", "close-wave", "close-change")}
        expected.update({"docs/prompts/memory-review.prompt.md", "docs/prompts/review-plan.prompt.md"})
        self.assertEqual(len(expected), 8)
        for destination, template in renderer.LIFECYCLE_PROMPT_BASELINES:
            self.put(destination, "A\n")
            self.put(".wavefoundry/framework/install/lifecycle-prompts/" + template, "A\n")
            incoming["lifecycle-prompts/" + template] = "B\n"
        findings = renderer.lifecycle_baseline_drift(self.root, incoming)
        self.assertEqual(set(self.states(findings)), expected)
        self.assertEqual(set(self.states(findings).values()), {"upstream_changed_local_matches_previous"})
        for destination, template in renderer.LIFECYCLE_PROMPT_BASELINES:
            self.put(destination, "B\n")
            self.put(".wavefoundry/framework/install/lifecycle-prompts/" + template, "B\n")
        self.assertEqual(renderer.lifecycle_baseline_drift(self.root, incoming), [])

    def test_current_empty_dynamic_plans_root_and_real_materialization(self):
        with patch.object(renderer.record_paths, "PLANS_ROOT", "work/proposals"):
            self.put(".wavefoundry/framework/install/plan-template.md", "Last verified: {{generated_at}}\nB\n")
            renderer.reconcile_scaffold_baselines(self.root)
            self.assertTrue((self.root / "work/proposals/plan-template.md").exists())
            self.assertEqual(renderer.lifecycle_baseline_drift(self.root, {"plan-template.md": "Last verified: {{generated_at}}\nB\n"}), [])

    def test_contained_read_does_not_accept_outside_symlink_as_previous_match(self):
        outside = Path(self.temp.name) / "outside.md"
        outside.write_text("B\n")
        local = self.root / "docs/plans/plan-template.md"
        local.parent.mkdir(parents=True)
        local.symlink_to(outside)
        findings = renderer.lifecycle_baseline_drift(self.root, {"plan-template.md": "B\n"})
        self.assertEqual(findings, [{"channel": "lifecycle_baseline_drift", "file": "docs/plans/plan-template.md", "detail": "baseline_unknown: local copy unavailable through contained read; comparison unavailable"}])
        self.assertEqual(outside.read_text(), "B\n")

    def test_incoming_old_context_preview_apply_and_resume_replay(self):
        incoming = self.fixture()
        self.make_pack(incoming)
        extension = upgrade._load_extension_module(self.pack)
        before = {p: p.read_bytes() for p in self.root.rglob("*.md")}
        out = io.StringIO()
        # Public incoming post_extract dry-run dispatch used by older parents.
        with contextlib.redirect_stdout(out), patch.object(extension, "_preview_council_role_links"), patch.object(extension, "_post_extract"):
            upgrade._run_hook("post_extract", self.ctx(True), extension)
        self.assertIn('"detail": "upstream_changed_local_matches_previous:', out.getvalue())
        self.assertFalse(upgrade_lib.upgrade_lock_path(self.root).exists())
        upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0", zip_path=self.pack)
        with contextlib.redirect_stdout(io.StringIO()), \
             patch.object(extension, "_preview_council_role_links"), \
             patch.object(extension, "_capture_index_guard_handoff"), \
             patch.object(extension, "_protect_existing_root_bootstrap"), \
             patch.object(extension, "_preserve_original_manifest"), \
             patch.object(extension, "_snapshot_graph_builder_doc_claim"), \
             patch.object(extension, "_cut_over_runtime_locks"):
            upgrade._run_hook("pre_extract", self.ctx(), extension)
        captured = upgrade_lib.read_upgrade_lock(self.root)["lifecycle_baseline_drift"]
        self.assertEqual(self.states(captured)[CREATE], "upstream_changed_local_matches_previous")
        # Simulate the actual destructive framework-only extraction boundary.
        with zipfile.ZipFile(self.pack) as archive:
            for name in archive.namelist():
                if "/install/" in name:
                    target = self.root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
        recomputed = renderer.lifecycle_baseline_drift(self.root, incoming)
        self.assertNotEqual(recomputed, captured)
        with contextlib.redirect_stdout(io.StringIO()), patch.object(extension, "_incoming_renderer_query", side_effect=AssertionError("must not recompute")):
            self.assertEqual(extension.lifecycle_baseline_report(self.ctx(), persist=True), captured)
        self.assertEqual({p: p.read_bytes() for p in before if "/install/" not in str(p)}, {p: data for p, data in before.items() if "/install/" not in str(p)})
        # A full standard retry rewrites its checkpoint but preserves the
        # producer's original facts for the identical incoming artifact.
        upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0", zip_path=self.pack)
        self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)["lifecycle_baseline_drift"], captured)
        # Standalone summary producer consumes the lock, independently of hooks.
        report = upgrade._empty_reporting("complete", "")
        summary_out = io.StringIO()
        with patch.object(upgrade, "_collect_reconciliation_report", return_value=report), patch.object(upgrade, "_historical_memory_report", return_value=None), contextlib.redirect_stdout(summary_out):
            self.assertEqual(upgrade._emit_delegated_summary(self.root), 0)
        summary = json.loads(summary_out.getvalue().split(upgrade.WAVE_UPGRADE_SUMMARY_SENTINEL)[1])
        self.assertEqual(summary["lifecycle_baseline_drift"], captured)
        self.assertTrue(all(set(item) == {"channel", "file", "detail"} for item in captured))
        # Exercise the actual public MCP response parser/bounder with the
        # canonical producer's sentinel, rather than a hand-authored summary.
        from server_tools_support import load_server
        server = load_server()
        with patch.object(server, "_mcp_subprocess_run", return_value=subprocess.CompletedProcess([], 0, summary_out.getvalue(), "")):
            response = server.wf_upgrade_response(self.root)
        self.assertEqual(response["data"]["summary"]["lifecycle_baseline_drift"], captured)
        self.assertEqual(response["data"]["exit_code"], 0)


    def test_cleanup_preserves_bytes_exit_and_captured_machine_summary(self):
        incoming = self.fixture()
        self.make_pack(incoming)
        exit_results = []
        for drift in (True, False):
            upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0", zip_path=self.pack)
            with contextlib.redirect_stdout(io.StringIO()):
                captured = extensions.lifecycle_baseline_report(self.ctx(), persist=True)
            if not drift:
                upgrade_lib.update_upgrade_lock(self.root, lifecycle_baseline_drift=[])
                captured = []
            before = {p: p.read_bytes() for p in self.root.rglob("*.md")}
            out = io.StringIO()
            with patch.object(upgrade, "_collect_reconciliation_report", return_value=upgrade._empty_reporting("complete", "")), \
                 patch.object(upgrade, "_record_setup_baseline", return_value=None), \
                 patch.object(upgrade, "_regenerate_codebase_map_on_upgrade"), \
                 patch.object(upgrade, "materialize_lifecycle_policy"), \
                 contextlib.redirect_stdout(out):
                exit_results.append(upgrade.phase_cleanup(self.root, "1.33.0", "1.34.0", self.pack, 0, False))
            line = next(line for line in out.getvalue().splitlines() if line.startswith(upgrade.WAVE_UPGRADE_SUMMARY_SENTINEL))
            summary = json.loads(line[len(upgrade.WAVE_UPGRADE_SUMMARY_SENTINEL):])
            self.assertEqual(summary["lifecycle_baseline_drift"], captured)
            self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertEqual(exit_results, [None, None])

    def test_lock_preserves_empty_same_pack_but_discards_changed_pack_or_version(self):
        self.make_pack({})
        for captured in ([], [{"channel": "lifecycle_baseline_drift", "file": "x", "detail": "baseline_unknown"}]):
            upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0", zip_path=self.pack)
            with patch.object(extensions, "_incoming_renderer_query", return_value=json.dumps(captured)), contextlib.redirect_stdout(io.StringIO()):
                extensions.lifecycle_baseline_report(self.ctx(), persist=True)
            # Different path, identical bytes: authority is the pack digest.
            retry = self.pack.with_name("retry.zip")
            retry.write_bytes(self.pack.read_bytes())
            upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0", zip_path=retry)
            self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)["lifecycle_baseline_drift"], captured)
            upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.35.0", zip_path=retry)
            self.assertNotIn("lifecycle_baseline_drift", upgrade_lib.read_upgrade_lock(self.root))
            upgrade_lib.update_upgrade_lock(self.root, to_version="1.34.0", lifecycle_baseline_drift=captured, lifecycle_baseline_drift_pack_sha256=extensions._pack_sha256(self.pack))
            retry.write_bytes(b"another pack")
            upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0", zip_path=retry)
            self.assertNotIn("lifecycle_baseline_drift", upgrade_lib.read_upgrade_lock(self.root))

    def test_new_plan_preview_is_printed_and_computed_once_then_captured(self):
        self.make_pack(self.fixture())
        extension = upgrade._load_extension_module(self.pack)
        out = io.StringIO()
        with patch.object(upgrade, "_load_extension_module", return_value=extension), \
             patch.object(extension, "_incoming_renderer_query", wraps=extension._incoming_renderer_query) as query, \
             contextlib.redirect_stdout(out):
            upgrade._print_change_plan(self.root, "1.33.0", "1.34.0", self.pack, False, [])
            ctx = upgrade.UpgradeContext(self.root, "1.33.0", "1.34.0", self.pack, True)
            upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0", zip_path=self.pack)
            captured = extension.lifecycle_baseline_report(ctx, persist=True)
        self.assertEqual(query.call_count, 1)
        self.assertEqual(out.getvalue().splitlines().count("Lifecycle baseline drift (report only; project copies preserved):"), 1)
        self.assertEqual(self.states(captured)[CREATE], "upstream_changed_local_matches_previous")
        self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)["lifecycle_baseline_drift"], captured)
        upgrade._LIFECYCLE_BASELINE_PLAN_FINDINGS.clear()

    def test_local_stat_failure_is_unknown_and_does_not_abort(self):
        incoming = self.fixture()
        with patch.object(Path, "lstat", side_effect=PermissionError("denied")):
            findings = renderer.lifecycle_baseline_drift(self.root, incoming)
        self.assertEqual(self.states(findings)["docs/plans/plan-template.md"], "baseline_unknown")

    def test_current_tree_report_uses_current_install_without_archive(self):
        self.fixture()
        self.put(".wavefoundry/framework/install/plan-template.md", "B\n")
        ctx = self.ctx()
        ctx.zip_path = None
        with contextlib.redirect_stdout(io.StringIO()):
            findings = extensions.lifecycle_baseline_report(ctx)
        self.assertNotIn("docs/plans/plan-template.md", self.states(findings))
        self.assertEqual(self.states(findings)[IMPLEMENT], "upstream_unchanged_local_differs")
        self.assertTrue(all(item["file"] for item in findings))

    def test_different_pack_or_target_preview_does_not_replay_stale_snapshot(self):
        self.make_pack(self.fixture())
        upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0", zip_path=self.pack)
        with contextlib.redirect_stdout(io.StringIO()):
            captured = extensions.lifecycle_baseline_report(self.ctx(), persist=True)
        for changed in ("target", "pack"):
            ctx = self.ctx(True)
            if changed == "target":
                ctx.to_version = "1.35.0"
            else:
                ctx.zip_path = self.pack.with_name("different.zip")
                ctx.zip_path.write_bytes(b"different artifact")
            with patch.object(extensions, "_incoming_renderer_query", return_value="[]") as query, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(extensions.lifecycle_baseline_report(ctx), [])
            query.assert_called_once()
            self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)["lifecycle_baseline_drift"], captured)

    def test_public_dry_run_machine_summary_and_single_human_report(self):
        self.make_pack(self.fixture())
        extension = upgrade._load_extension_module(self.pack)
        out = io.StringIO()
        with patch.object(upgrade, "_load_extension_module", return_value=extension), \
             patch.object(extension, "_preview_council_role_links"), \
             patch.object(extension, "_post_extract"), \
             contextlib.redirect_stdout(out):
            code = upgrade.phase_dry_run(self.root, explicit_pack=self.pack)
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().splitlines().count("Lifecycle baseline drift (report only; project copies preserved):"), 1)
        line = next(line for line in out.getvalue().splitlines() if line.startswith(upgrade.WAVE_UPGRADE_SUMMARY_SENTINEL))
        summary = json.loads(line[len(upgrade.WAVE_UPGRADE_SUMMARY_SENTINEL):])
        self.assertEqual(self.states(summary["lifecycle_baseline_drift"])[CREATE], "upstream_changed_local_matches_previous")
        self.assertFalse(upgrade_lib.upgrade_lock_path(self.root).exists())
        upgrade._LIFECYCLE_BASELINE_PLAN_FINDINGS.clear()

    def test_retained_lock_missing_capture_is_unknown_while_empty_is_known(self):
        upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0")
        self.assertEqual(upgrade._lifecycle_baseline_findings(self.root), [{"channel": "lifecycle_baseline_drift", "file": "", "detail": "baseline_unknown: no pre-extraction comparison captured; previous-template evidence unavailable"}])
        upgrade_lib.update_upgrade_lock(self.root, lifecycle_baseline_drift=[])
        self.assertEqual(upgrade._lifecycle_baseline_findings(self.root), [])

    def test_unavailable_is_captured_and_empty_is_not_recomputed(self):
        self.make_pack({})
        upgrade_lib.write_upgrade_lock(self.root, from_version="1.33.0", to_version="1.34.0", zip_path=self.pack)
        for response in ("[]", "invalid-json"):
            upgrade_lib.update_upgrade_lock(self.root, lifecycle_baseline_drift=None)
            with patch.object(extensions, "_incoming_renderer_query", return_value=response), contextlib.redirect_stdout(io.StringIO()):
                captured = extensions.lifecycle_baseline_report(self.ctx(), persist=True)
            with patch.object(extensions, "_incoming_renderer_query", side_effect=AssertionError("recomputed")), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(extensions.lifecycle_baseline_report(self.ctx(), persist=True), captured)
            self.assertEqual(bool(captured), response != "[]")


if __name__ == "__main__":
    unittest.main()
