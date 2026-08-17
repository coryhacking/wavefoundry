import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import agent_surface_integrity as subject
import render_agent_surfaces as renderer
from wave_lint_lib.wave_validators import _check_agent_category_metadata, _check_agent_role_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _forked_role_root(tmp: Path) -> Path:
    """A repo root holding a top-level red-team doc plus the canonical carrier."""
    root = tmp
    header = "# {name}\n\nOwner: Engineering\nStatus: active\nRole: red-team\nCategory: specialist\n"
    (root / "docs" / "agents" / "specialists").mkdir(parents=True)
    (root / "docs" / "agents" / "red-team.md").write_text(header.format(name="Red Team"), encoding="utf-8")
    (root / "docs" / "agents" / "specialists" / "red-team.md").write_text(header.format(name="Red Team"), encoding="utf-8")
    return root


class AgentSurfaceIntegrityTests(unittest.TestCase):
    def test_registry_paths_are_the_only_canonical_authority(self):
        paths = subject.canonical_role_paths()
        self.assertEqual(paths["red-team"], "docs/agents/specialists/red-team.md")
        self.assertEqual(paths["wave-council"], "docs/agents/specialists/wave-council.md")

    def test_audit_follows_a_registry_destination_change(self):
        # AC-2: no parallel role-path list. Move one carrier's destination in the registry
        # and the audit's canonical path moves with it; a non-renderer or non-executable
        # carrier never becomes canonical.
        import dataclasses
        moved = []
        for carrier in subject.REVIEW_POLICY_CARRIER_REGISTRY:
            if carrier.destination == "docs/agents/specialists/red-team.md":
                moved.append(dataclasses.replace(carrier, destination="docs/agents/roles/red-team.md"))
            else:
                moved.append(carrier)
        moved.append(dataclasses.replace(moved[0], destination="docs/agents/not-a-carrier.md", owner="project"))
        with patch.object(subject, "REVIEW_POLICY_CARRIER_REGISTRY", tuple(moved)):
            paths = subject.canonical_role_paths()
        self.assertEqual(paths["red-team"], "docs/agents/roles/red-team.md")
        self.assertNotIn("not-a-carrier", paths)

    def test_duplicate_framework_role_is_advisory_and_lint_remains_per_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seeds = root / ".wavefoundry/framework/seeds"
            seeds.parent.mkdir(parents=True)
            shutil.copytree(PROJECT_ROOT / "seeds", seeds)
            top = root / "docs/agents/red-team.md"
            top.parent.mkdir(parents=True)
            top.write_text("# Red Team\n\nOwner: Engineering\nStatus: active\nRole: red-team\nCategory: specialist\n\n## Local memory\n", encoding="utf-8")
            renderer.reconcile_review_protocol_surfaces(root)
            self.assertEqual(_check_agent_role_metadata(root), [])
            self.assertEqual(_check_agent_category_metadata(root), [])
            # AC-9: byte-for-byte, the audit never touches a role doc or a renderer-owned
            # marker region (the canonical carrier holds the executable-review-evidence block)
            before = {p: p.read_bytes() for p in (root / "docs" / "agents").rglob("*.md")}
            self.assertTrue(any(b"wave:executable-review-evidence begin" in body for body in before.values()))
            result = subject.audit_agent_surfaces(root)
            after = {p: p.read_bytes() for p in (root / "docs" / "agents").rglob("*.md")}
            self.assertEqual(before, after)
            [duplicate] = result["duplicate_roles"]
            self.assertEqual(duplicate["role"], "red-team")
            self.assertEqual(duplicate["canonical_path"], "docs/agents/specialists/red-team.md")
            self.assertEqual(result["finding_count"], 1)
            self.assertTrue(result["advisory"])
            self.assertNotIn("orphaned_canonical_roles", result)
            self.assertNotIn("active_references", result)
            self.assertTrue((root / "docs/agents/red-team.md").is_file())


class UpgradeSurfacesTests(unittest.TestCase):
    """Wave 1vgep (1vflu) AC-7 plus delivery findings: the advisory reaches the operator
    from the runner-owned summary line, which the standalone --cleanup process runs from
    the freshly extracted runner, so it already covers the upgrade delivering the audit;
    no extension hook prints it (finding pre-cleanup-hook-duplicates-advisory)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _forked_role_root(Path(self.tmp.name))
        self.upgrade = _load_script("upgrade_wavefoundry")
        self.ext = _load_script("upgrade_extensions")

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_helper_reports_findings_and_degrades_to_none_root(self):
        self.assertEqual(self.upgrade._run_agent_surface_integrity_scan(None), {"available": False, "finding_count": 0})
        report = self.upgrade._run_agent_surface_integrity_scan(self.root)
        self.assertEqual(report["finding_count"], 1)
        self.assertEqual(report["duplicate_roles"][0]["role"], "red-team")

    def test_operator_summary_prints_the_advisory_with_paths(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.upgrade._print_operator_summary(
                from_version="1.17.1", to_version="1.17.2", zip_path=None, pruned_count=0,
                ran_index_rebuild=False, failed_phase=None, root=self.root,
            )
        out = buf.getvalue()
        self.assertIn("Agent-role integrity: 1 advisory finding(s)", out)
        self.assertIn("red-team: docs/agents/red-team.md, docs/agents/specialists/red-team.md -> docs/agents/specialists/red-team.md", out)

    def test_delivering_upgrade_cleanup_prints_the_advisory_exactly_once(self):
        # The operator summary is emitted only by phase_cleanup, which every documented
        # path runs in the standalone --cleanup process from the FRESHLY EXTRACTED runner,
        # so the upgrade that delivers the audit already reports it, once. A zip-loaded
        # extension hook that also printed it would double the block (delivery finding
        # pre-cleanup-hook-duplicates-advisory), and dropping the runner line would zero it.
        import zipfile
        import memory_backfill
        import upgrade_lib
        for from_version, label in (("1.17.0+pjdj", "delivering upgrade"), ("1.17.1+abcd", "later upgrade")):
            with tempfile.TemporaryDirectory() as tmp:
                root = _forked_role_root(Path(tmp))
                (root / ".wavefoundry" / "index").mkdir(parents=True)
                (root / "docs" / "waves").mkdir(parents=True, exist_ok=True)
                # the zip that delivered this upgrade carries the CURRENT extension module
                zp = root / "wavefoundry-1.17.1.zip"
                with zipfile.ZipFile(zp, "w") as zf:
                    zf.write(SCRIPTS / "upgrade_extensions.py", ".wavefoundry/framework/scripts/upgrade_extensions.py")
                run_id = memory_backfill.ensure_run(root, "upgrade")
                memory_backfill.sync_inventory(root, run_id)
                memory_backfill.mark_indexed(root, run_id)
                upgrade_lib.write_upgrade_lock(root, from_version, "1.17.1")
                upgrade_lib.update_upgrade_lock(root, memory_backfill_run_id=run_id,
                                                memory_backfill_state="indexed", zip_path=str(zp))
                buf = io.StringIO()
                with patch.object(self.upgrade, "_ensure_rendered_permissions_backstop"), contextlib.redirect_stdout(buf):
                    code = self.upgrade.main(["--root", str(root), "--yes", "--cleanup"])
                out = buf.getvalue()
                self.assertEqual(code, 0, out)
                self.assertIn("Extension module loaded from zip", out, label)
                self.assertEqual(out.count("Agent-role integrity: 1 advisory finding(s)"), 1, f"{label}: {out}")
                self.assertEqual(out.count("red-team: docs/agents/red-team.md, docs/agents/specialists/red-team.md -> docs/agents/specialists/red-team.md"), 1, label)
                # and no extension hook claims the advisory
                self.assertFalse(hasattr(self.ext, "pre_cleanup"), "the advisory has one owner: the runner summary")
