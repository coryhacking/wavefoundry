"""Guidance delivery contracts; these checks do not establish agent effectiveness."""
from __future__ import annotations

from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import render_agent_surfaces as ras
import vocabulary_profile as vp
from upstream_fixture_support import source_repository_fixture

import test_rust_practices_baseline as baseline_tests

FRAMEWORK = SCRIPTS.parent
ROOT = FRAMEWORK.parent.parent
BASELINE = baseline_tests.BASELINE
RECORD = "docs/contributing/rust-best-practices.md"
RUST_PRECEDENCE = (
    r"record.*governs",
    r"where the record is silent, the project's existing configuration and dominant patterns govern",
    r"informs proposals only",
    r"relevant baseline entry through its index, not the whole document",
    r"Propose, never apply, a baseline practice",
)
# Rust-specific tokens that must not appear in the all-stacks blocks.
RUST_TOKENS = ("Rust", "Cargo", "Clippy", "rust-practices", "rust-best-practices", "crate")


def seed(number: str) -> str:
    path = next((FRAMEWORK / "seeds").glob(number + "-*.prompt.md"))
    return source_repository_fixture(path).read_text(encoding="utf-8")


def paragraphs(text: str) -> list[str]:
    return re.split(r"\n\s*\n", text)


class LanguageGuidanceTests(unittest.TestCase):
    def assert_performance_contract(self, text: str) -> None:
        # Renderer marker comments identify their producer, not review guidance.
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        body = "\n".join(line for line in text.splitlines() if "**Tool posture" not in line)
        modules = {p.name for p in SCRIPTS.rglob("*.py")}
        for name in modules:
            self.assertNotIn(name, body, name)
        for identifier in ("chunk_file", "search_*", "code_*", "code-summary", "top_n * 4", "20-symbol"):
            self.assertNotIn(identifier, body)
        self.assertNotRegex(body, r"(?i)(?:running|reviewing|review runs).*on Wavefoundry")
        self.assertNotIn("not measured numbers", body)
        for pattern in (
            r"(?i)complexity", r"(?i)repeated work", r"(?i)(?:patterns|pattern).*loop",
            r"(?i)filter.*(?:before|precede).*cap", r"(?i)bounded.*memory|memory.*bounded",
            r"(?i)accumulation.*calls", r"(?i)allocat", r"(?i)(?:buffer.*cop|cop.*buffer)",
            r"(?i)thread.*runtime|runtime.*thread", r"(?i)reshap", r"(?i)lock.*hold",
            r"(?i)briefing", r"(?i)architecture", r"(?i)coordinator",
            r"(?i)measurement", r"(?i)estimate.*method", r"Project Harness Extensions",
        ):
            self.assertRegex(body, pattern)

    def test_performance_seed_and_real_missing_role_delivery(self):
        text = seed("212")
        self.assert_performance_contract(text)
        carrier = next(c for c in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY if c.source_seed.startswith("212-"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seeds = root / ".wavefoundry/framework/seeds"
            seeds.mkdir(parents=True)
            (seeds / carrier.source_seed).write_text(text, encoding="utf-8")
            self.assertFalse((root / carrier.destination).exists())
            with mock.patch.object(ras, "REVIEW_PROTOCOL_CARRIER_REGISTRY", (carrier,)):
                written = ras.reconcile_review_protocol_surfaces(root)
            self.assertIn(carrier.destination, written)
            self.assert_performance_contract((root / carrier.destination).read_text(encoding="utf-8"))

    def test_performance_contract_detects_leaked_module_and_missing_cost(self):
        text = seed("212")
        for mutant in (text + "\nReview `indexer.py`.\n", re.sub(r"(?im)^.*lock.*hold.*$", "", text)):
            with self.subTest(mutant=mutant[-80:]), self.assertRaises(AssertionError):
                self.assert_performance_contract(mutant)

    def test_builder_detects_multiple_stacks_and_keeps_expertise(self):
        text = seed("222")
        self.assertIn("Cargo.toml", text)
        self.assertIn("*.rs", text)
        self.assertRegex(text, r"(?i)(?:each|every).*detected.*(?:language|stack)")
        self.assertNotRegex(text, r"(?i)primary (?:stack|language)\b|mixed or undetected")
        for expertise in ("Pydantic", "Spring bean", "Entity Framework", "Prisma", "asyncio"):
            self.assertIn(expertise, text)
        for example in ("unchecked cast", "type-ignore", "null-forgiving"):
            self.assertIn(example, text)
        for concept in ("ownership", "shared", "exclusive", "cohesive", "consumer", "suppression"):
            self.assertIn(concept, text.lower())
        self.assertRegex(text, r"(?i)(?:merely|only).*diagnostic|diagnostic.*(?:merely|only)")
        self.assertRegex(text, r"(?i)(?:necessary|justified).*tradeoff|tradeoff.*(?:necessary|justified)")

    def test_rust_block_is_conditional_specific_and_lints_opt_in(self):
        text = seed("222")
        block = re.search(r"(?ms)^\*\*Rust[^\n]*\n(.*?)(?=^---|^\*\*|^##|\Z)", text)
        self.assertIsNotNone(block)
        rust = block.group(0)
        self.assertRegex(rust, r"(?i)when.*Rust")
        for token in ("clone", "to_vec", "collect", "redundant_clone", "implicit_clone", "needless_collect", "large_types_passed_by_value", "too_many_lines"):
            self.assertIn(token, rust)
        for other in ("Python", "TypeScript", "C#", "JVM"):
            self.assertNotIn(other, rust)
        self.assertRegex(rust, r"(?i)pinned.*toolchain")
        self.assertRegex(rust, r"(?i)group")
        self.assertRegex(text, r"(?i)never enable.*(?:automatically|operator)|(?:without|requires?).*explicit operator")
        generic = re.search(r"(?ms)^\*\*Backend.*?^---", text).group(0)
        for line in generic.splitlines():
            if line.startswith("- "):
                self.assertNotIn(line, rust)

    def test_escalation_and_port_planning_preserve_authority(self):
        for number in ("222", "180"):
            with self.subTest(seed=number):
                text = seed(number)
                for pattern in (r"(?i)only local fix", r"(?i)structural workaround", r"(?i)coordinator", r"(?i)no (?:new )?approval", r"(?i)(?:outside|leaves|exceeds).*scope"):
                    self.assertRegex(text, pattern)
        text = seed("170")
        port = next(p for p in paragraphs(text) if re.search(r"(?i)ports.*rewrites|rewrites.*ports", p))
        for concept in ("ownership", "data model", "hot paths", "equivalent", "design quality"):
            self.assertIn(concept, port)
        self.assertNotRegex(port, r"(?m)^#{1,6} ")

    def test_reviewer_conditions_and_aggregate_justification(self):
        text = seed("221")
        check = next(p for p in paragraphs(text) if "workaround" in p.lower())
        for pattern in (r"(?i)statically", r"N/A", r"Suppressed failures", r"(?i)aggregate|together|combined", r"(?i)unsupported|unjustified"):
            self.assertRegex(check, pattern)
        perf = seed("212")
        rust = next(p for p in paragraphs(perf) if "Rust" in p and "Tool posture" not in p)
        self.assertRegex(rust, r"(?i)when.*Rust|Rust.*only")
        section = re.search(r"(?ms)^### Rust[^\n]*\n(.*?)(?=^#{2,3} |\Z)", perf).group(1)
        self.assertIn("clone", section)
        generic = re.search(r"(?ms)^## What to Check\n(.*?)(?=^## )", perf).group(1)
        checks = [line for line in generic.splitlines() if line.startswith("- ")]
        self.assertTrue(checks)
        for line in checks:
            self.assertNotIn(line, section)

    def assert_existing_merge(self, text: str, number: str, destination: str):
        # The owner is one bullet, not the whole adjacent migration list.
        candidates = [line for line in text.splitlines()
                      if line.lstrip().startswith("- ") and number in line and destination in line]
        self.assertTrue(candidates)
        self.assertTrue(any(re.search(r"(?i)changed", p) and re.search(r"(?i)merg", p)
                            and re.search(r"(?i)existing", p) and re.search(r"(?i)preserv", p)
                            for p in candidates), (number, destination))

    def test_upgrade_requires_existing_document_merge_not_names(self):
        text = seed("160")
        for number, path in (("212", "docs/agents/performance-reviewer.md"),
                             ("212", "docs/prompts/agents/performance-reviewer.prompt.md"),
                             ("222", "docs/agents/software-engineer.md"),
                             ("180", "docs/prompts/implement-spec.prompt.md")):
            with self.subTest(seed=number):
                self.assert_existing_merge(text, number, path)
                with self.assertRaises(AssertionError):
                    self.assert_existing_merge(f"Seed {number} generates `{path}` when absent.", number, path)
                owner = "Changed performance-reviewer guidance" if number == "212" else "Changed builder guidance"
                removed = "\n".join(line for line in text.splitlines() if owner not in line)
                with self.assertRaises(AssertionError):
                    self.assert_existing_merge(removed, number, path)
        perf_rule = next(p for p in paragraphs(text) if "212" in p and "docs/agents/performance-reviewer.md" in p)
        self.assertRegex(perf_rule, r"(?i)replace.*inherited")
        self.assertRegex(perf_rule, r"(?i)when present|if present")

    def assert_rust_precedence(self, text: str) -> None:
        block = re.search(r"(?ms)^\*\*Rust[^\n]*\n(.*?)(?=^---|^\*\*|^##|\Z)", text)
        self.assertIsNotNone(block)
        rust = block.group(0)
        for pattern in RUST_PRECEDENCE:
            self.assertRegex(rust, pattern)
        self.assertIn(f"`{BASELINE}`", rust)
        self.assertIn(f"`{RECORD}`", rust)
        for name in ("Backend", "SQL", "Testing"):
            shared = re.search(rf"(?ms)^\*\*{name}[^\n]*\(all stacks\)\*\*\n(.*?)(?=^---|^\*\*|^##|\Z)", text)
            self.assertIsNotNone(shared, name)
            for token in RUST_TOKENS:
                self.assertNotIn(token, shared.group(0), (name, token))

    def test_rust_block_carries_record_precedence(self):
        text = seed("222")
        self.assert_rust_precedence(text)
        self.assertIn("Candidate lints, as proposals only", text)
        self.assertRegex(text, r"(?i)never enable them automatically or without explicit operator direction")
        line = next(l for l in text.splitlines() if l.startswith("- Propose, never apply"))
        moved = text.replace(line + "\n", "", 1).replace(
            "**Backend and service development (all stacks)**\n",
            "**Backend and service development (all stacks)**\n" + line + "\n", 1)
        bolded = text.replace(line, "**Note:** " + line[2:], 1)
        for mutant in (moved, bolded):
            with self.assertRaises(AssertionError):
                self.assert_rust_precedence(mutant)

    def assert_reviewer_rust_sentence(self, paragraph: str) -> None:
        for pattern in (r"For Rust, review the change against the project's record", r"citing the row",
                        r"reasoned N/A when the project has no record", r"claimed verification"):
            self.assertRegex(paragraph, pattern)
        self.assertIn(f"`{RECORD}`", paragraph)

    def test_reviewer_workaround_check_cites_the_rust_record(self):
        check = next(p for p in paragraphs(seed("221")) if "workaround" in p.lower())
        self.assert_reviewer_rust_sentence(check)
        with self.assertRaises(AssertionError):
            self.assert_reviewer_rust_sentence(re.sub(r" For Rust, review.*", "", check))
        reviewer = source_repository_fixture(ROOT / "docs/agents/code-reviewer.md").read_text(encoding="utf-8")
        local = next(l for l in reviewer.splitlines() if "Compiler and type-checker workarounds" in l)
        self.assert_reviewer_rust_sentence(local)

    def test_upgrade_merge_rules_name_builder_and_review_carriers(self):
        text = seed("160")
        self.assert_existing_merge(text, "222", "docs/agents/software-engineer.md")
        self.assert_existing_merge(text, "221", "docs/agents/code-reviewer.md")
        removed = "\n".join(l for l in text.splitlines() if "Changed project-owned review carriers" not in l)
        with self.assertRaises(AssertionError):
            self.assert_existing_merge(removed, "221", "docs/agents/code-reviewer.md")

    def assert_record_offer(self, text: str, blocked: str) -> None:
        lines = [l for l in text.splitlines() if "Rust record offer" in l]
        self.assertEqual(len(lines), 1)
        offer = lines[0]
        self.assertRegex(offer, r"^\s+- ")
        for pattern in (r"one informational line", rf"does not block {blocked}", r"existing record is left unchanged",
                        r"Cargo\.toml", r"ordinary planned change", r"decision left for the operator"):
            self.assertRegex(offer, pattern)
        self.assertIn(f"`{RECORD}`", offer)
        self.assertIn(f"`{BASELINE}`", offer)

    def test_install_and_upgrade_summaries_offer_the_record(self):
        upgrade, install = seed("160"), seed("012")
        self.assert_record_offer(upgrade, "the upgrade")
        self.assert_record_offer(install, "installation")
        summary = re.search(r"(?ms)^### 2\.15 .*?(?=^### |\Z)", install).group(0)
        topics = re.findall(r"^\d+\. \*\*(.+?)\*\*", summary, re.MULTILINE)
        self.assertEqual(len(topics), 8)
        self.assertIn("This eight-topic list is the authoritative structure", summary)
        self.assertIn("Rust record offer", summary)
        for mutant in (install.replace("does not block installation", "must finish first", 1),
                       install.replace("   - Rust record offer", "- Rust record offer", 1),
                       install.replace(", and an existing record is left unchanged", "", 1)):
            with self.assertRaises(AssertionError):
                self.assert_record_offer(mutant, "installation")

    def changed_rust_sentences(self) -> list[str]:
        rust = re.search(r"(?ms)^\*\*Rust[^\n]*\n(.*?)(?=^---|^\*\*|^##|\Z)", seed("222")).group(0)
        review = next(p for p in paragraphs(seed("221")) if "workaround" in p.lower())
        offers = [l for number in ("160", "012") for l in seed(number).splitlines() if "Rust record offer" in l]
        return [rust, review.split("For Rust,", 1)[1], *offers]

    def test_changed_rust_seed_text_has_no_agent_imperative_or_identifier(self):
        for sentence in self.changed_rust_sentences():
            with self.subTest(sentence=sentence[:60]):
                self.assertEqual(baseline_tests.imperative_hits(sentence), [])
                self.assertEqual(baseline_tests.identifier_hits(sentence), [])
        self.assertTrue(baseline_tests.imperative_hits("Then add the lint to the manifest file."))
        self.assertTrue(baseline_tests.identifier_hits("As decided in 2abcd."))

    def test_local_carriers_keep_project_guidance_and_receive_additions(self):
        def local(path):
            return source_repository_fixture(ROOT / path).read_text(encoding="utf-8")
        performance = local("docs/prompts/agents/performance-reviewer.prompt.md")
        for name in ("chunker.py", "indexer.py", "chunk_file", "server.py"):
            self.assertIn(name, performance)
        software = local("docs/agents/software-engineer.md")
        self.assertIn("ownership", software.lower())
        self.assertNotRegex(software, r"(?m)^\*\*Rust|^#+ Rust")
        for slug in ("implement-change", "implement-wave"):
            self.assertIn("structural workaround", local(vp.prompt_doc(slug)))
        self.assertIn("design quality", local(vp.prompt_doc("plan-change")))


if __name__ == "__main__":
    unittest.main()
