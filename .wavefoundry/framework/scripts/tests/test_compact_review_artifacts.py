"""Compact evidence policy transport; prose pins do not prove agent adherence."""
from __future__ import annotations

import sys
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))
import render_agent_surfaces as renderer
from record_layout_support import SHIPPED_DEFAULTS

SEEDS = SCRIPTS_ROOT.parent / "seeds"
CORE = "209-agent-harness-core.prompt.md"
IMPLEMENT = "180-implement-change.prompt.md"
CHAIR = "215-council-chair.prompt.md"
# Raw canonical seeds retain shipped vocabulary; profile renderers consume or
# point to those sources. Derive the source expectation from the shared fixture
# vocabulary rather than hardcoding a default-layout filename in the contract.
CANONICAL_RECORD = SHIPPED_DEFAULTS["vocabulary_profile"]["RECORD_FILENAME"]


class CompactReviewArtifactContractTests(unittest.TestCase):
    # Each phrase names a distinct safety/efficiency obligation, not incidental
    # formatting. Deletion and reversal controls run against the actual seed.
    CONTRACTS = {
        CORE: (
            "temporary storage outside the repository",
            "final outcomes, review disagreements, source/profile identities",
            "memory disposition and the evidence index",
            "unique long-run proof that canonical tests, exact Git history",
            f"Explain each retained exception inline in `{CANONICAL_RECORD}`",
            "preserve historical conclusions, admitted change docs and immutable `events.jsonl`",
            "wave-owned, verified redundant material with no live references",
            "check containment, file identity, uniqueness and references",
            "keep cited originals unless their consumers are explicitly migrated",
            "keep unreconstructable dirty-tree baselines",
            "No age expiry, blanket deletion, reference resolver, cleanup sidecar or automatic deletion gate",
            "consume its returned continuation actions and current receipt identity",
            "Batch review bookkeeping and final documentation reconciliation",
            "current successful test receipt only when its input identity matches",
            "changed inputs, a red result, or missing/unreadable proof still stop qualification",
            "Required specialist/Council authority, exact test qualification and final full documentation validation remain unchanged",
            "dry-run to resolve uncertain checks, not as a compulsory extra gate",
            "no framework-source suite/profile qualification, extra evidence pass or broad memory maintenance",
            "existing bounded historical-memory checkpoint",
            "render → docs gate → incremental index ordering",
            "Reuse a report only while its inputs are unchanged",
        ),
        IMPLEMENT: (
            "Confirm current readiness and delivery authority",
            "consume successful typed-write continuation actions",
            "Re-Prepare when the receipt is missing or stale",
            "reuse only a successful receipt matching current inputs",
            "Required lanes, focused independent repair review and final full docs validation remain unchanged",
        ),
        CHAIR: (
            "existing risk-selected primer depth",
            "does not remove any required specialist or Council authority",
            "Readiness verifies plan feasibility against current code and bounded safe controls",
            "not future delivery execution that cannot exist before implementation",
            "temporary storage outside the repository",
            "Typed evidence in immutable `events.jsonl` remains machine authority",
            "Do not create per-seat repository reports",
        ),
    }

    def assert_contract(self, name: str, text: str) -> None:
        for phrase in self.CONTRACTS[name]:
            self.assertIn(phrase, text)

    def test_each_seed_and_deleted_or_reversed_obligation_controls(self) -> None:
        for name, phrases in self.CONTRACTS.items():
            text = (SEEDS / name).read_text(encoding="utf-8")
            self.assert_contract(name, text)
            for phrase in phrases:
                with self.subTest(seed=name, clause=phrase):
                    # This mutation actually removes the named seed obligation;
                    # it must fail this same contract, not an unrelated pin.
                    self.assertEqual(text.count(phrase), 1)
                    for replacement in ("", "REVERSED OBLIGATION"):
                        with self.assertRaises(AssertionError):
                            self.assert_contract(name, text.replace(phrase, replacement))

    def test_public_render_transports_core_pointer_and_chair_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seeds = root / ".wavefoundry/framework/seeds"
            seeds.mkdir(parents=True)
            for name in self.CONTRACTS:
                (seeds / name).write_bytes((SEEDS / name).read_bytes())
            renderer.render_agent_surfaces(root)
            chair = root / "docs/agents/specialists/council-chair.md"
            self.assert_contract(CHAIR, chair.read_text(encoding="utf-8"))
            core_carriers = [
                root / carrier.destination
                for carrier in renderer.review_protocol_carriers(root)
                if carrier.source_seed == CORE and (root / carrier.destination).is_file()
            ]
            self.assertTrue(core_carriers)
            for path in core_carriers:
                self.assertIn(f".wavefoundry/framework/seeds/{CORE}", path.read_text(encoding="utf-8"))
            self.assert_contract(CORE, (seeds / CORE).read_text(encoding="utf-8"))

            # Canonical pointer transport catches a deleted source obligation
            # instead of claiming that the consumer copied the source body.
            phrase = self.CONTRACTS[CORE][0]
            (seeds / CORE).write_text((seeds / CORE).read_text().replace(phrase, ""), encoding="utf-8")
            renderer.render_agent_surfaces(root)
            with self.assertRaises(AssertionError):
                self.assert_contract(CORE, (seeds / CORE).read_text(encoding="utf-8"))

    def test_render_preserves_project_chair_prose_and_converges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            renderer.render_agent_surfaces(root)
            chair = root / "docs/agents/specialists/council-chair.md"
            chair.write_text(chair.read_text() + "\nProject-owned review convention.\n", encoding="utf-8")
            renderer.render_agent_surfaces(root)
            before = chair.read_bytes()
            self.assertEqual(renderer.render_agent_surfaces(root), [])
            self.assertEqual(chair.read_bytes(), before)

    def test_implement_wave_template_and_authored_carrier_match_and_render(self) -> None:
        repo = SCRIPTS_ROOT.parents[2]
        template_path = SCRIPTS_ROOT.parent / "install/lifecycle-prompts/implement-wave.prompt.md"
        template = template_path.read_text(encoding="utf-8")
        completion = template.split("## Completion\n", 1)[1].split("\nImplementation is complete", 1)[0]
        phrases = (
            "temporary storage outside the repository",
            "preserve cited and unique proof",
            "Consume successful typed-write continuation actions",
            "successful receipt matching current inputs",
            "Required lanes, focused independent repair review and final full docs validation remain unchanged",
            "dry-run resolves uncertain checks and is not a compulsory extra gate",
        )

        def assert_completion(text: str) -> None:
            for phrase in phrases:
                self.assertIn(phrase, text)

        assert_completion(completion)
        self.assertIn(completion, (repo / "docs/prompts/implement-wave.prompt.md").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target_template = root / ".wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md"
            shutil.copytree(template_path.parent, target_template.parent)
            target_template.write_text(template, encoding="utf-8")
            renderer.render_agent_surfaces(root)
            carrier = root / "docs/prompts/implement-wave.prompt.md"
            assert_completion(carrier.read_text(encoding="utf-8"))
            self.assertIn(completion, carrier.read_text(encoding="utf-8"))
            # Mutate this consumer's actual template and force a fresh render,
            # rather than checking an unrelated seed while transport is broken.
            for phrase in phrases:
                target_template.write_text(template.replace(phrase, "REVERSED OBLIGATION"), encoding="utf-8")
                carrier.unlink()
                renderer.render_agent_surfaces(root)
                with self.subTest(removed=phrase), self.assertRaises(AssertionError):
                    assert_completion(carrier.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
