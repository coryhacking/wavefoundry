"""Public rendering and install-audit regression tests for partial prompt setup."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1]
FRAMEWORK = SCRIPTS.parent
BASE = SCRIPTS / "tests/fixtures/docs_lint/base"
sys.path.insert(0, str(SCRIPTS))

import docs_handlers  # noqa: E402
import review_policy  # noqa: E402
import server_impl  # noqa: E402


class PartialPromptInstallIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(BASE, self.root, dirs_exist_ok=True)
        target = self.root / ".wavefoundry/framework"
        shutil.copytree(
            SCRIPTS, target / "scripts",
            ignore=shutil.ignore_patterns("tests", "__pycache__"),
        )
        shutil.copytree(FRAMEWORK / "install", target / "install")
        shutil.copytree(FRAMEWORK / "seeds", target / "seeds")
        shutil.copy2(FRAMEWORK / "VERSION", target / "VERSION")
        self.server_file = target / "scripts/server_impl.py"

    def _sync(self):
        with patch.object(server_impl, "__file__", str(self.server_file)):
            return docs_handlers.wf_sync_surfaces_response(self.root, mode="run")

    def _audit(self):
        with patch.object(server_impl, "__file__", str(self.server_file)):
            return server_impl.wf_audit_install_response(self.root)

    def test_public_sync_repairs_empty_policy_region_without_permissions(self):
        path = self.root / "docs/prompts/upgrade-wavefoundry.prompt.md"
        original = path.read_text(encoding="utf-8")
        begin = review_policy.UPGRADE_POLICY_MARKER_BEGIN
        end = review_policy.UPGRADE_POLICY_MARKER_END
        left = original.index(begin)
        right = original.index(end) + len(end)
        prefix, suffix = original[:left], original[right:]
        path.write_text(prefix + begin + "\n\n" + end + suffix, encoding="utf-8")

        settings = self.root / ".claude/settings.json"
        settings.parent.mkdir(parents=True)
        permission_bytes = b'{"permissions":{"allow":["Bash(project:*)"]}}\n'
        settings.write_bytes(permission_bytes)
        original_permissions = json.loads(permission_bytes)["permissions"]

        first = self._sync()
        self.assertEqual(first["status"], "ok", first)
        self.assertIn("docs/prompts/upgrade-wavefoundry.prompt.md", first["data"]["written"])
        rendered = path.read_text(encoding="utf-8")
        self.assertTrue(rendered.startswith(prefix))
        self.assertTrue(rendered.endswith(suffix))
        self.assertIn(review_policy.UPGRADE_POLICY_BLOCK, rendered)
        self.assertEqual(rendered.count(begin), 1)
        self.assertEqual(rendered.count(end), 1)
        self.assertEqual(json.loads(settings.read_text())["permissions"], original_permissions)
        self.assertNotIn("wavefoundryAllowWriteTools", settings.read_text())

        snapshot = path.read_bytes()
        second = self._sync()
        self.assertEqual(second["status"], "ok", second)
        self.assertEqual(second["data"]["written"], [])
        self.assertEqual(path.read_bytes(), snapshot)
        self.assertEqual(json.loads(settings.read_text())["permissions"], original_permissions)

    def test_partial_seed_100_stays_pending_until_prompt_and_manifest_repair(self):
        self.assertEqual(self._sync()["status"], "ok")
        log = self.root / ".wavefoundry/install-log.md"
        pending_row = (
            "- [ ] 2.9 — Generate repo-local prompt surface (seed-100) "
            "— artifact: `docs/prompts/prompt-surface-manifest.json`"
        )
        log.write_text("# Install\n\n## Phase 2\n\n" + pending_row + "\n", encoding="utf-8")

        manifest = self.root / "docs/prompts/prompt-surface-manifest.json"
        manifest_bytes = manifest.read_bytes()
        data = json.loads(manifest_bytes)
        prompt_rel = "docs/prompts/plan-feature.prompt.md"
        self.assertIn(prompt_rel, {entry["doc"] for entry in data["public_prompt_surface"]})
        # This is a mandatory seed-100 catalog member, not an arbitrary fixture file.
        seed = (FRAMEWORK / "seeds/100-project-prompt-surface-bootstrap.prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(f"- `{prompt_rel}`", seed)
        prompt = self.root / prompt_rel
        authored_bytes = prompt.read_bytes()
        prompt.unlink()
        data.pop("schema_version")
        manifest.write_text(json.dumps(data), encoding="utf-8")

        blocked = self._audit()
        self.assertEqual(blocked["data"]["status"], "lint_errors", blocked)
        errors = "\n".join(blocked["data"]["errors"])
        self.assertIn("missing `schema_version`", errors)
        self.assertIn(f"registered prompt doc `{prompt_rel}` does not exist", errors)
        self.assertIn(pending_row, log.read_text(encoding="utf-8"))

        prompt.write_bytes(authored_bytes)
        manifest.write_bytes(manifest_bytes)
        ready = self._audit()
        self.assertEqual(ready["data"]["status"], "next_step", ready)
        self.assertEqual(ready["data"]["row"]["number"], "2.9")
        self.assertEqual(prompt.read_bytes(), authored_bytes)

        log.write_text(log.read_text(encoding="utf-8").replace("- [ ] 2.9", "- [x] 2.9"), encoding="utf-8")
        complete = self._audit()
        self.assertEqual(complete["data"]["status"], "complete", complete)
