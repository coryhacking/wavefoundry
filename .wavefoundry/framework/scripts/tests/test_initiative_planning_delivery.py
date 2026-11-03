"""Mechanical Plan initiative delivery; prose reconciliation is exercised separately."""

from __future__ import annotations

import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import build_pack
import upgrade_wavefoundry
import vocabulary_profile as vp


FRAMEWORK = SCRIPTS.parent
PREFIX = ".wavefoundry/framework/"
SEED = "seeds/171-plan-initiative.prompt.md"
PROMPT = "docs/prompts/plan-arc.prompt.md"
ROUTES = (
    "seeds/050-agent-entry-surface-bootstrap.prompt.md",
    "seeds/100-project-prompt-surface-bootstrap.prompt.md",
    "seeds/160-upgrade-wavefoundry.prompt.md",
)


def collected_archive(framework: Path, members: set[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for source, name in build_pack.collect_files(framework):
            if name in members:
                archive.write(source, name)
    return buffer.getvalue()


def extract(payload: bytes, target: Path) -> None:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        upgrade_wavefoundry._extract_feature_members(archive, target)


class InitiativePlanningDeliveryTests(unittest.TestCase):
    def test_collection_and_extraction_deliver_sources_without_authoring_local_prose(self):
        members = {PREFIX + name for name in (SEED, *ROUTES,
                   "scripts/render_agent_surfaces.py", "scripts/vocabulary_profile.py")}
        names = {name for _, name in build_pack.collect_files(FRAMEWORK)}
        self.assertNotIn(PREFIX + "scripts/tests/test_initiative_planning_delivery.py", names)
        payload = collected_archive(FRAMEWORK, members)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(set(archive.namelist()), members)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            extract(payload, root)
            self.assertEqual((root / (PREFIX + SEED)).read_bytes(), (FRAMEWORK / SEED).read_bytes())
            for name in ROUTES:
                text = (root / (PREFIX + name)).read_text(encoding="utf-8")
                self.assertIn(PROMPT, text, name)
                self.assertIn("171-plan-initiative.prompt.md", text, name)
            self.assertFalse((root / PROMPT).exists())
            self.assertFalse((root / ".codex/skills/wf-plan-initiative").exists())
            retained = {
                PROMPT: b"# Plan initiative\r\nKeep our project-specific policy.\r\n",
                "VISION.md": b"# Adopted project direction\n",
            }
            for name, content in retained.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            extract(payload, root)
            for name, content in retained.items():
                self.assertEqual((root / name).read_bytes(), content)

    def test_later_seed_revision_is_extracted_without_overwriting_custom_prompt(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source, target = base / "source", base / "target"
            (source / "seeds").mkdir(parents=True)
            shutil.copyfile(FRAMEWORK / SEED, source / SEED)
            members = {PREFIX + SEED}
            extract(collected_archive(source, members), target)
            candidate = base / "candidate.zip"
            candidate.write_bytes(collected_archive(source, members))
            self.assertEqual(upgrade_wavefoundry._compute_seed_diffs(target, candidate), [])
            prompt = target / PROMPT
            prompt.parent.mkdir(parents=True, exist_ok=True)
            custom = b"# Existing initiative guidance\nLocal extension.\n"
            prompt.write_bytes(custom)
            revision = (source / SEED).read_bytes() + b"\nFixture-only canonical revision.\n"
            (source / SEED).write_bytes(revision)
            payload = collected_archive(source, members)
            candidate.write_bytes(payload)
            diffs = upgrade_wavefoundry._compute_seed_diffs(target, candidate)
            self.assertEqual([(name, status) for name, status, _ in diffs],
                             [("171-plan-initiative.prompt.md", "modified")])
            self.assertIn("+Fixture-only canonical revision.", diffs[0][2])
            extract(payload, target)
            self.assertEqual((target / (PREFIX + SEED)).read_bytes(), revision)
            self.assertEqual(prompt.read_bytes(), custom)
            self.assertEqual(upgrade_wavefoundry._compute_seed_diffs(target, candidate), [])
            # Extraction supplies the new canonical source; seed 160 directs
            # the separate agent merge and its explicit conflict handling.

    def test_initiative_names_reject_collisions_and_allow_adjacent_names(self):
        errors = vp.prompt_name_errors({"plan-change": {
            "slug": "plan-initiative", "shortcut": "Plan adjacent work"}})
        self.assertTrue(any("fixed framework prompt slug" in error for error in errors))
        self.assertTrue(any("fixed or retired framework skill" in error for error in errors))
        for field in ("shortcut", "aliases"):
            spec = {"slug": "plan-initiative-next", "shortcut": "Plan initiative next"}
            spec[field] = "pLaN InItIaTiVe" if field == "shortcut" else ["pLaN InItIaTiVe"]
            with self.subTest(field=field):
                self.assertTrue(any("shortcut or alias" in error
                                    for error in vp.prompt_name_errors({"plan-change": spec})))
        self.assertEqual(vp.prompt_name_errors({"plan-change": {
            "slug": "plan-initiative-next", "shortcut": "Plan initiative next"}}), [])


if __name__ == "__main__":
    unittest.main()
