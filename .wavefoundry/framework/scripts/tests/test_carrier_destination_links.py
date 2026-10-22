"""Change 21ayx: a carrier destination that is a dangling link, or that
resolves under ``.git``, is refused instead of followed."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))
import render_agent_surfaces as ras  # noqa: E402
import techdocs_audit_lib  # noqa: E402
from wave_lint_lib.core_validators import check_review_policy_carrier_parity  # noqa: E402

DEST = "docs/prompts/close-wave.prompt.md"


def _can_symlink() -> bool:
    probe = Path(tempfile.mkdtemp(prefix="symlink-probe-"))
    try:
        os.symlink(probe / "missing", probe / "link")
        return True
    except (OSError, NotImplementedError):
        return False
    finally:
        shutil.rmtree(probe, ignore_errors=True)


SYMLINK_SKIP = "this platform or account cannot create symlinks (Windows needs privilege or Developer Mode)"


@unittest.skipUnless(_can_symlink(), SYMLINK_SKIP)
class CarrierDestinationLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="carrier-links-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / ".git" / "hooks").mkdir(parents=True)
        (self.root / "docs" / "prompts").mkdir(parents=True)

    def _assert_refused(self, call, fragment: str) -> str:
        with self.assertRaises(RuntimeError) as caught:
            call()
        message = str(caught.exception)
        self.assertIn(fragment, message)
        return message

    def test_dangling_destination_link_into_git_hooks_is_refused(self) -> None:
        """AC-1: the reported write."""
        hook = self.root / ".git" / "hooks" / "pre-push"
        os.symlink(hook, self.root / DEST)
        message = self._assert_refused(
            lambda: ras.reconcile_lifecycle_prompt_baselines(self.root), DEST)
        self.assertIn("dangling link", message)
        self.assertFalse(os.path.lexists(hook))

    def test_dangling_ancestor_link_is_refused_and_creates_no_folder(self) -> None:
        """AC-2."""
        prompts = self.root / "docs" / "prompts"
        prompts.rmdir()
        missing = self.root / "elsewhere"
        os.symlink(missing, prompts, target_is_directory=True)
        self._assert_refused(
            lambda: ras._contained_review_carrier_path(self.root, DEST), "dangling link")
        self._assert_refused(
            lambda: ras.reconcile_lifecycle_prompt_baselines(self.root), "dangling link")
        self.assertFalse(os.path.lexists(missing))

    def test_ancestor_link_to_existing_git_hooks_is_refused(self) -> None:
        """AC-3: an existing .git target is refused and nothing lands there."""
        prompts = self.root / "docs" / "prompts"
        prompts.rmdir()
        os.symlink(self.root / ".git" / "hooks", prompts, target_is_directory=True)
        self._assert_refused(
            lambda: ras.reconcile_lifecycle_prompt_baselines(self.root), ".git directory")
        self.assertEqual(list((self.root / ".git" / "hooks").iterdir()), [])

    def test_case_variant_git_target_is_refused_on_case_insensitive_fs(self) -> None:
        """AC-3: the .git comparison ignores case where the file system does."""
        if not (self.root / ".GIT").exists():
            self.skipTest("case-sensitive file system: .GIT is a different folder")
        prompts = self.root / "docs" / "prompts"
        prompts.rmdir()
        os.symlink(self.root / ".GIT" / "hooks", prompts, target_is_directory=True)
        self._assert_refused(
            lambda: ras._contained_review_carrier_path(self.root, DEST), ".git directory")

    def test_case_variant_git_target_is_refused_whatever_the_platform(self) -> None:
        """A case-insensitive volume under sys.platform linux (WSL2 on a Windows drive)."""
        if not (self.root / ".GIT").exists():
            self.skipTest("case-sensitive file system: .GIT is a different folder")
        prompts = self.root / "docs" / "prompts"
        prompts.rmdir()
        os.symlink(self.root / ".GIT" / "hooks", prompts, target_is_directory=True)
        with mock.patch.object(sys, "platform", "linux"):
            self._assert_refused(
                lambda: ras._contained_review_carrier_path(self.root, DEST), ".git directory")

    def test_link_to_existing_in_repo_file_resolves_as_today(self) -> None:
        """AC-3: present, not materialized."""
        shared = self.root / "shared" / "close.md"
        shared.parent.mkdir()
        shared.write_text("project prose\n", encoding="utf-8")
        os.symlink(shared, self.root / DEST)
        self.assertEqual(ras._contained_review_carrier_path(self.root, DEST), shared.resolve())
        written = ras.reconcile_lifecycle_prompt_baselines(self.root)
        self.assertNotIn(DEST, written)
        self.assertEqual(shared.read_text(encoding="utf-8"), "project prose\n")

    def test_escaping_link_keeps_the_existing_refusal(self) -> None:
        """AC-3."""
        outside = Path(tempfile.mkdtemp(prefix="carrier-outside-"))
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        os.symlink(outside / "close.md", self.root / DEST)
        self._assert_refused(
            lambda: ras._contained_review_carrier_path(self.root, DEST),
            "escapes the repository root through a symlink")
        self.assertIsNone(techdocs_audit_lib._contained(self.root, DEST))

    def test_techdocs_maps_the_new_refusal_to_its_degrade_result(self) -> None:
        os.symlink(self.root / ".git" / "hooks" / "pre-push", self.root / DEST)
        self.assertIsNone(techdocs_audit_lib._contained(self.root, DEST))

    def test_docs_lint_reports_a_dangling_destination(self) -> None:
        """AC-4: the read-only gate completes and names the destination."""
        os.symlink(self.root / ".git" / "hooks" / "pre-push", self.root / DEST)
        failures = check_review_policy_carrier_parity(self.root)
        self.assertTrue(any(f.startswith(f"{DEST}:") and "dangling link" in f for f in failures),
                        failures)


class CarrierDestinationWithoutLinksTests(unittest.TestCase):
    def test_missing_destination_without_links_resolves_as_today(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="carrier-nolinks-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        resolved = ras._contained_review_carrier_path(root, DEST)
        self.assertEqual(resolved, (root / DEST).resolve())
        self.assertFalse(resolved.exists())


if __name__ == "__main__":
    unittest.main()
