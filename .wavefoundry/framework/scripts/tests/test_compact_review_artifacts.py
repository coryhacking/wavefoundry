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
import vocabulary_profile
from prompt_vocabulary_support import prime_profile_render, shipped_prompt_vocabulary

SEEDS = SCRIPTS_ROOT.parent / "seeds"
CORE = "209-agent-harness-core.prompt.md"
IMPLEMENT = "180-implement-spec.prompt.md"
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
            "`.wavefoundry/work/<wave-id>/` disposable area",
            "promote unique long-term proof out of disposable work",
            "New durable approvals must not rely solely on work-area paths",
            "final outcomes, review disagreements, source/profile identities",
            "memory disposition and the evidence index",
            "unique long-run proof that canonical tests, exact Git history",
            f"Explain each retained exception inline in `{CANONICAL_RECORD}`",
            "preserve historical conclusions, admitted specs and immutable `events.jsonl`",
            "wave-owned, verified redundant material with no live references",
            "check containment, file identity, uniqueness and references",
            "keep cited originals unless their consumers are explicitly migrated",
            "keep unreconstructable dirty-tree baselines",
            "Only the designated owned `.wavefoundry/work/<wave-id>/` is eligible for automatic best-effort cleanup after successful operator-authorized whole-wave closure",
            "ordinary wave-folder evidence keeps these manual protections",
            "Close reports citation state for the closing wave folder's extra files and never deletes them; no age expiry, blanket deletion, cleanup sidecar or automatic deletion gate",
            "consume its returned continuation actions and current receipt identity",
            "Finish source, test, configuration and edit-gate edits, and substantive edits to the wave under test, before the final canonical suite",
            "Validated routine bookkeeping may continue",
            "Reuse a successful test receipt only when its source input identity matches",
            "changed inputs, a red result, or missing/unreadable proof still stop qualification",
            "Required specialist/Council authority, exact test qualification and final full documentation validation remain unchanged",
            "dry-run to resolve uncertain checks, not as a compulsory extra gate",
            "no framework-source suite/profile qualification, extra evidence pass or broad memory maintenance",
            "memory curation is on demand",
            "render → docs gate → incremental index ordering",
            "Reuse a report only while its inputs are unchanged",
        ),
        IMPLEMENT: (
            "`.wavefoundry/work/<wave-id>/`, keyed by the resolved unique lifecycle prefix",
            "Before finalizing evidence, preserve unique long-term proof",
            "new durable approvals must not depend solely on disposable paths",
            "attempts contained cleanup after the close transition",
            "Dry-run, failed close and single-change close preserve work",
            "Unsupported safe deletion preserves files with a notice",
            "only to the owned work area, never historical wave artifacts",
            "Confirm current readiness and delivery authority",
            "consume successful typed-write continuation actions",
            "Re-Prepare when the receipt is missing or stale",
            "Reuse only a successful receipt matching current inputs",
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
            "the lifecycle-reported disposable work area",
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
        # This repository's rendered prompt sits at the profile's path and
        # carries every phrase; whole-section identity with the template is a
        # contract only under the shipped names, since a distribution words its
        # own prompts (change 2134q).
        authored = (repo / vocabulary_profile.prompt_doc("implement-wave")).read_text(encoding="utf-8")
        assert_completion(authored)
        if shipped_prompt_vocabulary():
            self.assertIn(completion, authored)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target_template = root / ".wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md"
            shutil.copytree(template_path.parent, target_template.parent)
            target_template.write_text(template, encoding="utf-8")
            prime_profile_render(root)
            renderer.render_agent_surfaces(root)
            carrier = root / vocabulary_profile.prompt_doc("implement-wave")
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

    # Change 23p9t: the Close disposition step for a record folder's extras.
    CLOSE_STEP = (
        "Give every extra file in the wave folder a disposition before the final docs validation and the close write",
        "read its advisory `record_extras_present`",
        "**Keep**: the file stays, and one line in `## Review Checkpoints` names it (or its group) and says why it is kept",
        "When a file is kept only because of a loose mention, that line cites it by path",
        "list the folder yourself and review every extra, including the files the report does not list",
        "When `complete` is false, likewise review the folder by hand",
        # Two pins around the record file's name, which this test must not spell
        # (the profile literal census refuses a default-layout literal here).
        "A file the report does not list has no citation state or flags from the tool, so judge it yourself: "
        "search `events.jsonl`,",
        "and the admitted specs for its path, its name and its containing "
        "directories, apply the same keep rules to what you find, and keep the file unless you establish that "
        "nothing refers to it",
        "Before removing a `not_cited` file whose four booleans are all false, search `events.jsonl` for the file's name stem",
        "search the folder's other extras for its name; a match means the file is referenced, so keep it",
        "`events.jsonl` is matched against the decoded string values of its lines",
        "**Summarize, then remove**",
        "**Remove**: remove the file with no summary",
        "Always keep a `cited_in_ledger` file, because the ledger is never rewritten",
        "When the citation sits in a spec section other than the Progress Log, keep the file",
        "Keep a `not_cited` file whose `name_in_ledger`, `name_in_record` or `directory_in_ledger` is true",
        "Write summaries and rewritten citations only into `## Review Checkpoints` or a spec's Progress Log",
        "A summary in a Progress Log contains no line that starts with `## `",
        "Before removing a file, check the kept extras for references to it",
        "Read `record_extras_present` again on the close write's response",
        "What is worth keeping in a wave folder",
        "Worth keeping: proof that cannot be reproduced from a recorded command, the tests and Git history",
        "Cite a kept file by its path, not only by its directory",
        "Paths are compared exactly as written, in forward-slash form, on every platform",
    )
    CLOSE_TEMPLATE_STEP = (
        "advisory `record_extras_present`",
        "Give every listed file one disposition",
        "Always keep a\n   `cited_in_ledger` file",
        "`name_in_ledger`, `name_in_record` or `directory_in_ledger` true",
        "search the ledger\n   for its name stem and the other extras for its name; a match keeps it",
        "list the\n   folder yourself and give every extra a disposition under the same rules,\n   including files the report does not list",
        "review the folder by hand\n   when `complete` is false",
        "An unlisted file has no citation state or flags,\n   so search the ledger, the record and the specs for its path, name and\n"
        "   directories, and keep it unless nothing refers to it",
        "the tool removes nothing and blocks nothing",
    )

    def test_close_disposition_step_in_seed_repository_copy_and_template(self) -> None:
        def section(text: str) -> str:
            return text.split("## Wave-folder cleanup\n", 1)[1].split("\nPromotion destinations", 1)[0]

        def assert_step(text: str, phrases) -> None:
            for phrase in phrases:
                self.assertIn(phrase, text)

        seed = section((SEEDS / "190-close-wave.prompt.md").read_text(encoding="utf-8"))
        assert_step(seed, self.CLOSE_STEP)
        self.assertNotIn("reference resolver", seed)
        template = (SCRIPTS_ROOT.parent / "install/lifecycle-prompts/close-wave.prompt.md").read_text(encoding="utf-8")
        assert_step(template, self.CLOSE_TEMPLATE_STEP)
        # The earlier guidance to keep unlisted files unreviewed is replaced.
        self.assertNotIn("are unreviewed: keep them", seed)
        self.assertNotIn("keep any file the report does not list", template)
        repo_copy = SCRIPTS_ROOT.parents[2] / vocabulary_profile.prompt_doc("close-wave")
        if repo_copy.is_file():
            authored = repo_copy.read_text(encoding="utf-8")
            assert_step(authored, self.CLOSE_STEP)
            if shipped_prompt_vocabulary():
                # This repository's copy is hand-edited to match the seed section.
                self.assertIn(seed, authored)
        for phrases, text in ((self.CLOSE_STEP, seed), (self.CLOSE_TEMPLATE_STEP, template)):
            for phrase in phrases:
                with self.subTest(removed=phrase), self.assertRaises(AssertionError):
                    assert_step(text.replace(phrase, "REVERSED OBLIGATION"), phrases)


if __name__ == "__main__":
    unittest.main()
