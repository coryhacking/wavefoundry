"""Fixture-fidelity guidance availability; these checks do not prove agent adherence."""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))
import render_agent_surfaces as renderer

SEEDS = SCRIPTS_ROOT.parent / "seeds"
REPO = SCRIPTS_ROOT.parents[2]
CORE = "209-agent-harness-core.prompt.md"
QA = "239-qa-reviewer.prompt.md"
CORE_REFERENCE = f".wavefoundry/framework/seeds/{CORE}"
CORE_PHRASES = (
    "build fixture state through canonical producers",
    "not an independent correctness oracle",
    "deliberately malformed inputs",
    "read the diagnostic message",
)
QA_PHRASES = (
    "build prerequisite state through canonical producers",
    "preserve deliberate inputs under test",
    "keep expected-value oracles independent",
    "an earlier gate refusal proves nothing",
)


class FixtureFidelityGuidanceTests(unittest.TestCase):
    def assert_phrases(self, text: str, phrases: tuple[str, ...]) -> None:
        for phrase in phrases:
            self.assertIn(phrase, text)

    def test_seed_rules_and_each_deleted_phrase_control(self) -> None:
        for filename, phrases in ((CORE, CORE_PHRASES), (QA, QA_PHRASES)):
            text = (SEEDS / filename).read_text(encoding="utf-8")
            self.assert_phrases(text, phrases)
            for phrase in phrases:
                with self.subTest(seed=filename, removed=phrase):
                    self.assertEqual(text.count(phrase), 1)
                    with self.assertRaises(AssertionError):
                        self.assert_phrases(text.replace(phrase, ""), phrases)

    def test_qa_preserves_five_conditions_and_self_hosted_guidance(self) -> None:
        seed = (SEEDS / QA).read_text(encoding="utf-8")
        gate = seed.split("## Evidence-integrity gate", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(re.findall(r"^(\d+)\. ", gate, re.MULTILINE), list("123456"))
        self.assertIn(QA_PHRASES[0], gate.split("\n3. ", 1)[0])
        self.assertIn("the sixth when claiming a measured delta", gate)
        self.assertIn("6. **A claimed delta has a controlled comparison.**", gate)
        local = (REPO / "docs/agents/qa-reviewer.md").read_text(encoding="utf-8")
        self.assert_phrases(local, QA_PHRASES)

    def test_public_renderer_pointer_fresh_role_and_preserved_existing_body(self) -> None:
        """Exercise the transport, including the old same-text-refresh counterexample."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seeds = root / ".wavefoundry/framework/seeds"
            seeds.mkdir(parents=True)
            for name in (CORE, QA):
                (seeds / name).write_bytes((SEEDS / name).read_bytes())
            renderer.render_agent_surfaces(root)
            qa_path = root / "docs/agents/qa-reviewer.md"
            fresh = qa_path.read_text(encoding="utf-8")
            self.assert_phrases(fresh, QA_PHRASES)
            common = [
                root / carrier.destination
                for carrier in renderer.review_protocol_carriers(root)
                if carrier.source_seed == CORE and (root / carrier.destination).is_file()
            ]
            self.assertTrue(common, "seed 209 must have actual consumer carriers")
            for path in common:
                with self.subTest(carrier=path.relative_to(root).as_posix()):
                    self.assertIn(CORE_REFERENCE, path.read_text(encoding="utf-8"))
                    # Canonical source is shipped separately, not inlined here.
                    self.assertNotIn(CORE_PHRASES[0], path.read_text(encoding="utf-8"))
            self.assert_phrases((root / CORE_REFERENCE).read_text(encoding="utf-8"), CORE_PHRASES)

            project_prose = "\nProject-owned QA acceptance rule.\n"
            qa_path.write_text(fresh + project_prose, encoding="utf-8")
            before = qa_path.read_bytes()
            changed_seed = (seeds / QA).read_text(encoding="utf-8") + "\nNEW-SEED-SENTINEL\n"
            (seeds / QA).write_text(changed_seed, encoding="utf-8")
            renderer.render_agent_surfaces(root)
            self.assertEqual(qa_path.read_bytes(), before)
            self.assertNotIn("NEW-SEED-SENTINEL", qa_path.read_text(encoding="utf-8"))
            # Explicit local guidance synchronization also survives regeneration.
            synced = fresh + project_prose + "\nExplicitly synchronized fixture-fidelity wording.\n"
            qa_path.write_text(synced, encoding="utf-8")
            renderer.render_agent_surfaces(root)
            self.assertEqual(qa_path.read_text(encoding="utf-8"), synced)


if __name__ == "__main__":
    unittest.main()
