"""Verify writing-guide collection, extraction and readable invocation references."""

from __future__ import annotations

import io
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import build_pack
import record_paths
import upgrade_wavefoundry
import vocabulary_profile


FRAMEWORK = SCRIPTS.parent
REPO = FRAMEWORK.parent.parent
GUIDE = ".wavefoundry/framework/docs/writing-guide.md"
SEEDS = (
    "020-run-contract.prompt.md",
    "050-agent-entry-surface-bootstrap.prompt.md",
    "100-project-prompt-surface-bootstrap.prompt.md",
    "160-upgrade-wavefoundry.prompt.md",
    "209-agent-harness-core.prompt.md",
    "233-technical-writer.prompt.md",
)


def collected_archive(framework: Path, members: set[str] | None = None) -> bytes:
    """Use the production producer; selecting members bounds this component probe."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for source, name in build_pack.collect_files(framework):
            if members is None or name in members:
                archive.write(source, name)
    return buffer.getvalue()


def extract(payload: bytes, target: Path) -> None:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        upgrade_wavefoundry._extract_feature_members(archive, target)


class WritingGuideDeliveryTests(unittest.TestCase):
    """Mechanical evidence only; agent-assisted prose merges are observed separately."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.members = {GUIDE} | {
            f".wavefoundry/framework/seeds/{name}" for name in SEEDS
        }

    def assert_readable_guide_reference(self, root: Path, text: str):
        references = re.findall(r"`([^`\n]*writing-guide[^`\n]*)`", text)
        self.assertTrue(references, "no writing-guide reference")
        for reference in references:
            self.assertEqual(reference, GUIDE, "stale or noncanonical guide reference")
            content = (root / reference).read_text(encoding="utf-8")
            self.assertTrue(content.strip(), "guide is empty")
        return content

    def test_fresh_extraction_delivers_guide_and_all_seed_routes(self):
        payload = collected_archive(FRAMEWORK, self.members)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(set(archive.namelist()), self.members)
        extract(payload, self.root)
        self.assertEqual((self.root / GUIDE).read_bytes(), (REPO / GUIDE).read_bytes())
        for seed in SEEDS:
            with self.subTest(seed=seed):
                text = (self.root / ".wavefoundry/framework/seeds" / seed).read_text()
                self.assert_readable_guide_reference(self.root, text)
        # Extraction never pretends to perform the agent's local prose authoring.
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_existing_policy_and_history_survive_repeated_extraction(self):
        history = Path(record_paths.WAVES_ROOT) / "old"
        retained = {
            "AGENTS.md": b"# Local policy\nUse our established domain terminology.\n",
            "docs/prompts/index.md": b"# Commands\nOperator-owned additions.\n",
            "docs/agents/specialists/technical-writer.md": b"# Writer\nLocal role policy.\n",
            (history / vocabulary_profile.RECORD_FILENAME).as_posix(): b"# Historical record\nStatus: closed\n",
            (history / "events.jsonl").as_posix(): b'{"historical": true}\n',
            "VISION.md": b"# Adopted vision\nProject-owned meaning.\n",
        }
        for name, data in retained.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        payload = collected_archive(FRAMEWORK, self.members)
        for _ in range(2):
            extract(payload, self.root)
            for name, data in retained.items():
                with self.subTest(name=name):
                    self.assertEqual((self.root / name).read_bytes(), data)

    def test_guide_only_payload_update_needs_no_seed_change(self):
        source = self.root / "source"
        (source / "docs").mkdir(parents=True)
        (source / "seeds").mkdir()
        shutil.copyfile(REPO / GUIDE, source / "docs/writing-guide.md")
        seed = "020-run-contract.prompt.md"
        shutil.copyfile(FRAMEWORK / "seeds" / seed, source / "seeds" / seed)
        target = self.root / "target"
        extract(collected_archive(source), target)
        old_seed = (target / ".wavefoundry/framework/seeds" / seed).read_bytes()
        revision = (source / "docs/writing-guide.md").read_bytes() + b"\nFixture-only revision.\n"
        (source / "docs/writing-guide.md").write_bytes(revision)
        extract(collected_archive(source), target)
        self.assertEqual((target / GUIDE).read_bytes(), revision)
        self.assertEqual((target / ".wavefoundry/framework/seeds" / seed).read_bytes(), old_seed)

    def test_local_invocation_routes_load_the_guide(self):
        for name in ("AGENTS.md", "docs/prompts/index.md", "docs/agents/specialists/technical-writer.md"):
            with self.subTest(name=name):
                self.assert_readable_guide_reference(REPO, (REPO / name).read_text())
        upgrade = (REPO / "docs/prompts/upgrade-wavefoundry.prompt.md").read_text()
        seed_path = ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md"
        self.assertIn(seed_path, upgrade)
        self.assert_readable_guide_reference(REPO, (REPO / seed_path).read_text())

    def test_missing_guide_and_stale_reference_controls_are_rejected(self):
        payload = collected_archive(FRAMEWORK, self.members - {GUIDE})
        extract(payload, self.root)
        carrier = f"Read `{GUIDE}` when authoring."
        with self.assertRaises(FileNotFoundError):
            self.assert_readable_guide_reference(self.root, carrier)
        extract(collected_archive(FRAMEWORK, {GUIDE}), self.root)
        self.assert_readable_guide_reference(self.root, carrier)
        with self.assertRaisesRegex(AssertionError, "stale or noncanonical"):
            self.assert_readable_guide_reference(
                self.root, carrier.replace("docs/writing-guide.md", "docs/old-writing-guide.md")
            )


if __name__ == "__main__":
    unittest.main()
