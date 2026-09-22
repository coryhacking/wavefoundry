from __future__ import annotations

import re
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "framework" / "scripts"
RENDER_SCRIPT = SCRIPTS_ROOT / "render_agent_surfaces.py"
PLATFORM_RENDER_SCRIPT = SCRIPTS_ROOT / "render_platform_surfaces.py"
GURU_STUB = "# Guru\n\nRole: guru\n"

sys.path.insert(0, str(SCRIPTS_ROOT))
import render_agent_surfaces as ras  # noqa: E402
import render_platform_surfaces as rps  # noqa: E402
import review_policy  # noqa: E402
import review_policy_reconcile  # noqa: E402
from wave_lint_lib.core_validators import check_review_policy_carriers  # noqa: E402


def assert_memory_review_contract(test: unittest.TestCase, text: str) -> None:
    for literal in (
        "Source event:",
        "Validation: pending",
        "action_delta=...",
        "rationale=...",
        "evidence_verified=...",
        "current_target_verified=...",
        "canonical_overlap=...",
        "Never send a hand-authored or already-finalized candidate",
        'memory_reconcile(memory_id=...,\n     status="active"|"rejected")',
        'memory_consolidate(mode="dry_run")',
        "<one exact groups[].memory_ids>",
        "does not\n   expose or accept a bulk retired-record cleanup list",
        "retain_for_history=true",
        "memory_purge(memory_id=..., reviewed=true",
        'index_build(content="docs", mode="update")',
        'index_build_status(layer="project")',
        "`lock.held=false`",
        '`state="finished"`',
        '`state="idle"`',
        '`epoch.status="complete"`',
        "`epoch.interrupted=false`",
        "`lock.ended_at`",
        "`up_to_date=true`",
        "stop and report it",
        "index_health()",
        "wf_memory_eval()",
        "Do not record model names.",
    ):
        test.assertIn(literal, text)

    ordered = [
        'index_build(content="docs", mode="update")',
        'index_build_status(layer="project")',
        "index_health()",
        "wf_memory_eval()",
    ]
    positions = [text.index(literal) for literal in ordered]
    test.assertEqual(positions, sorted(positions))

    read_only = text.split("## Read-only procedure", 1)[1].split("## Report", 1)[0]
    calls = set(re.findall(r"\b([a-z][a-z0-9_]*)\(", read_only))
    test.assertTrue(calls)
    test.assertTrue(
        calls.issubset(
            {"memory_brief", "memory_search", "memory_consolidate", "wf_memory_eval"}
        ),
        calls,
    )
    test.assertIn('memory_consolidate(mode="dry_run")', read_only)


class LegacyAutoGuruSectionTests(unittest.TestCase):
    def test_marker_boundary(self):
        for namespace in ("wave", "waveframework", "wavefoundry", "waveforge", "other"):
            with self.subTest(namespace=namespace):
                marker = f"<!-- {namespace}:x begin -->\nkept\n"
                text = "prefix\n## Code and documentation questions (auto-Guru)\nold\n" + marker
                result = ras.strip_legacy_auto_guru_section(text)
                self.assertNotIn("old", result)
                self.assertEqual(marker in result, namespace in ras.marker_namespaces.MARKER_NAMESPACES)


class BriefingLoopCarrierTests(unittest.TestCase):
    """Distribution/semantic pins, not a claim that agents always follow prose."""

    CARRIERS = {
        "brief": (
            ".wavefoundry/framework/seeds/170-plan-feature.prompt.md",
            "docs/prompts/plan-feature.prompt.md",
        ),
        "readback": (
            ".wavefoundry/framework/seeds/180-implement-feature.prompt.md",
            ".wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md",
            "docs/prompts/implement-feature.prompt.md",
            "docs/prompts/implement-wave.prompt.md",
        ),
        "gap": (
            ".wavefoundry/framework/seeds/175-review-plan.prompt.md",
            "docs/prompts/review-plan.prompt.md",
        ),
        "upgrade": (
            ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md",
            "docs/prompts/upgrade-wavefoundry.prompt.md",
        ),
    }
    HEADINGS = {
        "brief": "**Brief before drafting:**",
        "readback": "**Readback before editing:**",
        "gap": "**Compare the draft with its brief:**",
        "upgrade": "- **Changed briefing-loop carriers.**",
    }
    # Independent obligations: equality alone would accept two broken copies.
    CLAUSES = {
        "brief": (
            "Reuse the request, prior answers, and relevant project context",
            "before the Divergent Pre-Plan",
            "goal, consumer/audience, angle or approach, constraints, deliverable/format, exclusions, and observable success",
            "existing Rationale and summarize it to the operator before dependent drafting",
            "one concise sentence can suffice",
            "do not require a field-filling interview or confirmation",
            "at most three for small tasks and five for complex tasks",
            "ceilings rather than quotas",
            "Do not repeat known questions or restart a pass to evade the budget",
            "assumptions only for reversible implementation choices within established scope",
            "Keep unresolved goal, scope, acceptance, or authorization decisions open until answered",
            "pause dependent work and continue independent work",
            "Silence is neither an answer nor approval",
            "without creating another brief file",
        ),
        "readback": (
            "Before the first implementation edit of each change",
            "`Readback:` in its existing Progress Log and surface its substance to the operator",
            "intended behavior, relevant ACs, important scope boundary, and expected affected files",
            "one before/after example for nontrivial behavior changes",
            "Correct an agent-only misreading directly",
            "actual contract contradiction or missing consequential decision back to planning",
            "pausing only dependent work",
            "not automatically Level 3 and adds no second approval",
            "Refresh only materially changed understanding",
            "do not repeat an unchanged readback or create another artifact",
        ),
        "gap": (
            "At the start of this optional review",
            "Requirements, Acceptance Criteria, and Scope against the brief in Rationale",
            "operator's request, and relevant established context",
            "When no change is specified, use the corresponding current-wave planning content",
            "strong, vague, missing, removable, or less useful to the consumer",
            "report only meaningful observations",
            "feed unresolved discrepancies into the existing decision-branch walk",
            "Read Rationale as reference for the brief, without reopening the whole section or resolved Decision Log entries",
            "New ideas remain proposals, not authorized scope",
            "adds no document, gate, or signoff",
            "preserve the existing stop condition and one-question-at-a-time flow",
        ),
        "upgrade": (
            "Retain the read-only pre-apply change evidence for the seeds and install baseline",
            "After extraction",
            "during the same installing run",
            "`170-plan-feature.prompt.md` -> `docs/prompts/plan-feature.prompt.md`",
            "`175-review-plan.prompt.md` -> `docs/prompts/review-plan.prompt.md`",
            "`180-implement-feature.prompt.md` -> `docs/prompts/implement-feature.prompt.md`",
            "`.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md` -> `docs/prompts/implement-wave.prompt.md`",
            "Merge only changed authored clauses",
            "preserving project additions, metadata, and every renderer-owned marker region",
            "verify a unique insertion location and absence of conflicting local instructions",
            "If the old clause or insertion location is ambiguous, or local intent conflicts, stop and present the conflict",
            "Never replace a whole destination or silently omit a changed mapping",
            "Missing-only baseline rendering does not update existing authored prose",
            "run `wf render-surfaces` after reconciliation for the regions it owns",
        ),
    }

    def _block(self, kind: str, text: str) -> str:
        heading = self.HEADINGS[kind]
        self.assertEqual(text.count(heading), 1)
        tail = text.split(heading, 1)[1]
        # New blocks contain at most two paragraphs (upgrade has a mapping list).
        boundary = (r"\n ?- \*\*Changed Prepare" if kind == "upgrade"
                    else r"\n(?:## |[A-Z][^\n]*:\n)")
        body = re.split(boundary, tail, maxsplit=1)[0].strip()
        self.assertTrue(body)
        self.assertNotIn("\u2014", body)
        return body

    def _assert_contract(self, kind: str, text: str) -> str:
        body = self._block(kind, text)
        for clause in self.CLAUSES[kind]:
            self.assertIn(clause, body)
        if kind == "gap":
            self.assertNotIn("Do not review sections outside Requirements", text)
        return body

    def test_each_carrier_independently_satisfies_contract_and_matches(self) -> None:
        for kind, paths in self.CARRIERS.items():
            bodies = []
            for path in paths:
                with self.subTest(kind=kind, path=path):
                    bodies.append(self._assert_contract(kind, (PROJECT_ROOT.parent / path).read_text()))
            self.assertTrue(bodies)
            self.assertTrue(all(body == bodies[0] for body in bodies))

    def test_deleted_empty_and_reversed_clauses_are_detected_in_every_carrier(self) -> None:
        for kind, paths in self.CARRIERS.items():
            for path in paths:
                original = (PROJECT_ROOT.parent / path).read_text()
                body = self._assert_contract(kind, original)
                mutants = [original.replace(self.HEADINGS[kind], "", 1), original.replace(body, "", 1)]
                for clause in self.CLAUSES[kind]:
                    # Mutate only this block: a repeated phrase in unrelated
                    # upgrade guidance must not mask a missing instruction.
                    mutants.append(original.replace(body, body.replace(clause, "", 1), 1))
                reversals = {
                    "brief": (
                        ("Silence is neither an answer nor approval", "Silence is approval"),
                        ("Keep unresolved goal, scope, acceptance, or authorization decisions open until answered", "Assume unresolved goal, scope, acceptance, or authorization decisions are approved"),
                        ("ceilings rather than quotas", "mandatory question quotas"),
                    ),
                    "readback": (
                        ("Before the first implementation edit", "After the first implementation edit"),
                        ("Correct an agent-only misreading directly", "Escalate every agent-only misreading for operator approval"),
                        ("not automatically Level 3 and adds no second approval", "always Level 3 and requires a second approval"),
                    ),
                    "gap": (
                        ("Read Rationale as reference for the brief", "Never read Rationale"),
                        ("New ideas remain proposals, not authorized scope", "New ideas automatically become authorized scope"),
                    ),
                    "upgrade": (
                        ("during the same installing run", "during a future optional run"),
                        ("Merge only changed authored clauses", "Replace entire destination files"),
                        ("stop and present the conflict", "overwrite the conflicting local intent"),
                    ),
                }
                for before, after in reversals[kind]:
                    self.assertIn(before, body)
                    mutants.append(original.replace(body, body.replace(before, after, 1), 1))
                for index, mutant in enumerate(mutants):
                    with self.subTest(kind=kind, path=path, mutant=index):
                        self.assertNotEqual(mutant, original)
                        with self.assertRaises(AssertionError):
                            self._assert_contract(kind, mutant)

    def test_real_render_creates_baseline_and_preserves_customized_carriers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            written = ras.render_agent_surfaces(root)
            target = root / "docs/prompts/implement-wave.prompt.md"
            self.assertIn("docs/prompts/implement-wave.prompt.md", written)
            self._assert_contract("readback", target.read_text())
            self.assertNotIn("{{generated_at}}", target.read_text())
            # Review-plan baseline delegates to the seed; other authored prompts
            # are not claimed to be whole-file renderer outputs.
            review = root / "docs/prompts/review-plan.prompt.md"
            self.assertIn("175-review-plan.prompt.md", review.read_text())
            self.assertEqual(ras.render_agent_surfaces(root), [])
            snapshots = {}
            for name in ("plan-feature", "review-plan", "implement-feature", "implement-wave"):
                relative = f"docs/prompts/{name}.prompt.md"
                custom = ("# Project prompt\n\nOwner: Local team\nStatus: active\n"
                          "Last verified: 2026-01-01\n\nKeep project-specific output conventions.\n")
                (root / relative).write_text(custom)
            ras.render_agent_surfaces(root)  # Establish the renderer-owned regions.
            for name in ("plan-feature", "review-plan", "implement-feature", "implement-wave"):
                target = root / f"docs/prompts/{name}.prompt.md"
                self.assertTrue(target.read_text().startswith(custom))
                snapshots[target] = target.read_bytes()
            self.assertEqual(ras.render_agent_surfaces(root), [])
            for target, expected in snapshots.items():
                self.assertEqual(target.read_bytes(), expected)


class HostNeutralOrchestrationCarrierTests(unittest.TestCase):
    """Carrier and authored-merge fixtures, never native-host or agent-adherence proof."""

    ROOT = PROJECT_ROOT.parent
    OWNER = "180-implement-feature.prompt.md"
    PHASES = ("prepare-wave", "implement-wave", "review-wave", "close-wave")
    POLICY_HEADING = "## Host-neutral orchestration"
    # AC-derived obligations, independently asserted rather than copy equality.
    POLICY_CLAUSES = (
        "throughout Prepare, plan review, implementation, verification, delivery review and Close",
        "responsibilities, not fixed model tiers",
        "use a lighter model only when it meets the same quality bar for that task",
        "Optimize total verified effort, including retries, rework and integration",
        "If model selection is unavailable, use the current model and state the limitation",
        "relevant ACs, dependencies, owned and forbidden paths, interface constraints",
        "weigh briefing, waiting and integration overhead against the expected benefit",
        "keep small, tightly coupled work with the coordinator when delegation would cost more than it helps",
        "Set an early, task-sized checkpoint for a useful draft, finding or executed test",
        "without creating another artifact or approval gate",
        "promptly rebrief, change the model when available, or reclaim the task",
        "do not keep waiting merely because the worker is still running",
        "Serialize overlapping writes",
        "perform implementation tasks sequentially and state that choice",
        "Parent MCP access does not prove worker MCP access",
        "Worker completion is not wave completion",
        "a fresh independent context, on the same host or another",
        "required review remains pending",
        "reviewed revision or tree fingerprint",
        "a moved tree requires affected evidence to be refreshed",
        "Delegation-time selection is primary",
        "inheritance alone is not a task-fit decision",
        "Do not bake provider/model names or capability rankings into the policy",
        "Distinguish requested settings from observed runtime identity",
        "When the host does not expose the actual model or effort, record unknown",
    )
    UPGRADE_HEADING = "## Host-neutral orchestration reconciliation"
    UPGRADE_CLAUSES = (
        "during the same upgrade editing pass",
        "preserve project additions, metadata and renderer-owned regions",
        "merge only the changed authored clauses at a unique location",
        "present the conflict instead of overwriting it",
        "Missing-only rendering preserves existing prose and is not proof that this merge happened",
        "prepare-wave, implement-feature, implement-wave, review-wave, pause-wave, close-wave and agent-routing-concurrency",
        "AGENTS.md and docs/agents/wave-coordinator.md",
        "a repeat merge makes no further changes",
        "not an automatic prose migration claim",
    )

    def _assert_block(self, text: str, heading: str, clauses: tuple[str, ...]) -> str:
        self.assertEqual(text.count(heading), 1)
        block = text.split(heading, 1)[1].split("\n## ", 1)[0]
        if heading == self.POLICY_HEADING:
            block = block.split("\nWave orchestration contract:", 1)[0]
        for clause in clauses:
            self.assertIn(clause, block)
        return block

    def _assert_phase_pointer(self, text: str) -> None:
        paragraphs = [p for p in text.split("\n\n") if self.OWNER in p]
        self.assertEqual(len(paragraphs), 1)
        for clause in ("Host-neutral orchestration", "Use only available host capabilities",
                       "sequential implementation does not satisfy required independent review"):
            self.assertIn(clause, paragraphs[0])

    def test_canonical_contract_and_each_propagation_carrier(self) -> None:
        policy = (self.ROOT / ".wavefoundry/framework/seeds" / self.OWNER).read_text()
        self._assert_block(policy, self.POLICY_HEADING, self.POLICY_CLAUSES)
        for relative in (".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md",
                         "docs/prompts/upgrade-wavefoundry.prompt.md"):
            self._assert_block((self.ROOT / relative).read_text(), self.UPGRADE_HEADING, self.UPGRADE_CLAUSES)
        for phase in (*self.PHASES, "implement-feature", "pause-wave", "agent-routing-concurrency"):
            self._assert_phase_pointer((self.ROOT / f"docs/prompts/{phase}.prompt.md").read_text())
        bootstrap = (self.ROOT / ".wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md").read_text()
        self.assertIn("Seed 180 owns **Host-neutral orchestration** throughout Prepare-to-Close", bootstrap)
        for phase in self.PHASES:
            self.assertIn(phase, bootstrap.split("## Host-neutral orchestration carriers", 1)[1])
        for relative in ("AGENTS.md", ".wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md"):
            text = (self.ROOT / relative).read_text()
            self.assertIn("actual tools and allowlist rather than assuming inherited MCP access", text)
            self.assertNotIn("subagents without an explicit `tools:` allowlist inherit the parent's MCP tools", text)
        for relative in ("docs/agents/wave-coordinator.md", "docs/contributing/agent-team-workflow.md",
                         "docs/agents/platform-mapping.md"):
            text = (self.ROOT / relative).read_text()
            self.assertIn(self.OWNER, text)
            self.assertIn("Check actual worker capabilities rather than assuming inherited tools", text)

    def test_deleted_and_reversed_semantic_obligations_are_detected(self) -> None:
        for relative, heading, clauses, reversals in (
            (".wavefoundry/framework/seeds/" + self.OWNER, self.POLICY_HEADING, self.POLICY_CLAUSES, (
                ("not fixed model tiers", "fixed model tiers"),
                ("does not prove worker MCP access", "proves worker MCP access"),
                ("required review remains pending", "required review is satisfied by the implementer"),
            )),
            (".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md", self.UPGRADE_HEADING, self.UPGRADE_CLAUSES, (
                ("present the conflict instead of overwriting it", "overwrite the conflicting local policy"),
                ("not an automatic prose migration claim", "an automatic prose migration guarantee"),
            )),
        ):
            original = (self.ROOT / relative).read_text()
            block = self._assert_block(original, heading, clauses)
            mutants = [original.replace(heading, "", 1), original.replace(block, "", 1)]
            mutants.extend(original.replace(block, block.replace(clause, "", 1), 1) for clause in clauses)
            mutants.extend(original.replace(block, block.replace(old, new, 1), 1) for old, new in reversals)
            for index, mutant in enumerate(mutants):
                with self.subTest(path=relative, mutant=index):
                    self.assertNotEqual(mutant, original)
                    with self.assertRaises(AssertionError):
                        self._assert_block(mutant, heading, clauses)
        for phase in self.PHASES:
            text = (self.ROOT / f"docs/prompts/{phase}.prompt.md").read_text()
            self._assert_phase_pointer(text)
            for old, new in ((self.OWNER, "missing-owner.md"),
                             ("does not satisfy required independent review", "satisfies required independent review")):
                with self.subTest(phase=phase, mutation=old):
                    mutant = text.replace(old, new, 1)
                    self.assertNotEqual(mutant, text)
                    with self.assertRaises(AssertionError):
                        self._assert_phase_pointer(mutant)

    def test_public_fresh_render_delivers_every_lifecycle_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            written = ras.render_agent_surfaces(root)
            snapshots = {}
            for phase in self.PHASES:
                relative = f"docs/prompts/{phase}.prompt.md"
                self.assertIn(relative, written)
                target = root / relative
                self._assert_phase_pointer(target.read_text())
                self.assertNotIn("{{generated_at}}", target.read_text())
                snapshots[target] = target.read_bytes()
            ras.render_agent_surfaces(root)
            for target, expected in snapshots.items():
                self.assertEqual(target.read_bytes(), expected)

    def _assert_review_delivery_contract(self, text: str) -> None:
        # AC-derived obligations checked on producer output, not template equality.
        authored = text.split("<!-- wave:executable-review-evidence", 1)[0]
        flat = " ".join(authored.split())
        for clause in (
            "Review wave is the delivery phase; readiness review already ran at Prepare",
            "Every required-lane approval comes from a reviewer context started for delivery review",
            "non-delivery checkpoint pass or repair may return findings and evidence but records no approval",
            "Without the typed tool, return judgment facts to the coordinator and never hand-edit the ledger",
            "seed 209's **Briefing Packet**",
            "`code-reviewer` is not optional",
            "branch-complete and re-entrant checks",
            "QA verifies state across repeated calls or routine steps",
            "current receipt-derived `required_council_signoffs` lists `wave-council-delivery`",
            "AC scope gap check", "`qa-reviewer` attests every required row",
            "Verify every `[~]` AC", "## AC and Task Verification Truth Hierarchy",
            "## Project review specifics",
            "Review wave ends when every required lane and any receipt-required council approval is current in `wf_review_wave`",
            "It does not close the wave, mark completion or commit changes",
        ):
            self.assertIn(clause, flat)

    def test_fresh_review_template_contract_and_known_bad_controls(self) -> None:
        template_root = SCRIPTS_ROOT.parent / "install" / "lifecycle-prompts"
        baseline = (template_root / "review-wave.prompt.md").read_text()
        mutants = (
            ("delivery phase", "readiness phase"),
            ("but records no approval", "and records approval"),
            ("It does not close the wave", "It closes the wave"),
        )
        for mutation in (None, *mutants):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                local_templates = root / ".wavefoundry/framework/install/lifecycle-prompts"
                local_templates.mkdir(parents=True)
                for source in template_root.glob("*.md"):
                    (local_templates / source.name).write_bytes(source.read_bytes())
                if mutation:
                    old, new = mutation
                    self.assertEqual(baseline.count(old), 1)
                    (local_templates / "review-wave.prompt.md").write_text(baseline.replace(old, new, 1))
                written = ras.render_agent_surfaces(root)
                self.assertIn("docs/prompts/review-wave.prompt.md", written)
                target = root / "docs/prompts/review-wave.prompt.md"
                rendered = target.read_text()
                self._assert_phase_pointer(rendered)
                if mutation:
                    with self.assertRaises(AssertionError):
                        self._assert_review_delivery_contract(rendered)
                else:
                    self._assert_review_delivery_contract(rendered)
                    snapshot = target.read_bytes()
                    ras.render_agent_surfaces(root)
                    self.assertEqual(snapshot, target.read_bytes())

    def test_four_host_entry_paths_reach_shared_phase_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for host in (".codex", ".claude", ".agents", ".github"):
                (root / host).mkdir()
            (root / "docs/agents").mkdir(parents=True)
            (root / "docs/agents/guru.md").write_text(GURU_STUB)
            # Entry documents are agent-authored input, not renderer outputs.
            (root / "AGENTS.md").write_text(
                "# Project instructions\n\n" + "\n".join(
                    f"Read docs/prompts/{phase}.prompt.md." for phase in self.PHASES
                ) + "\n"
            )
            (root / "CLAUDE.md").write_text("# Claude\n\n## Startup Order\n\n1. AGENTS.md\n")
            (root / ".github/copilot-instructions.md").write_text(
                "# Copilot\n\nRead AGENTS.md.\n\n## Key Guardrails\n"
            )
            for platform in ("codex", "claude", "antigravity", "copilot"):
                rps.render_platform_entrypoints(root, platform)
            ras.render_agent_surfaces(root)
            for host in (".codex", ".claude", ".agents"):
                for phase in self.PHASES:
                    skill = root / host / "skills" / f"wf-{phase}" / "SKILL.md"
                    text = skill.read_text()
                    self.assertIn(f"docs/prompts/{phase}.prompt.md", text)
                    # The wrapper routes; the policy stays in the shared owner.
                    self.assertNotIn(self.POLICY_HEADING, text)
                    self.assertNotIn(self.POLICY_CLAUSES[3], text)
            self.assertIn("@AGENTS.md", (root / "CLAUDE.md").read_text())
            self.assertIn("AGENTS.md", (root / ".github/copilot-instructions.md").read_text())
            for phase in self.PHASES:
                self._assert_phase_pointer((root / f"docs/prompts/{phase}.prompt.md").read_text())

    def test_customized_prompts_require_authored_merge_then_converge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs/prompts").mkdir(parents=True)
            stale = "Every child agent always inherits the parent's MCP tools."
            prefix = "# Local workflow\n\nOwner: Local team\nStatus: active\nLast verified: 2026-01-01\n\n"
            suffix = "\n\nKeep project-specific output conventions and the local release checklist.\n"
            for phase in self.PHASES:
                (root / f"docs/prompts/{phase}.prompt.md").write_text(prefix + stale + suffix)
            ras.render_agent_surfaces(root)
            before = {}
            for phase in self.PHASES:
                target = root / f"docs/prompts/{phase}.prompt.md"
                text = target.read_text()
                self.assertTrue(text.startswith(prefix + stale + suffix))
                before[target] = text
            # Deliberate test-side agent editing step, NOT upgrader automation.
            # Only the known authored stale clause is replaced; all renderer-owned
            # regions and unrelated project text retain their exact bytes.
            for target, original in before.items():
                baseline = self.ROOT / ".wavefoundry/framework/install/lifecycle-prompts" / target.name
                paragraphs = [p for p in baseline.read_text().split("\n\n") if self.OWNER in p]
                self.assertEqual(len(paragraphs), 1, target.name)
                self.assertEqual(original.count(stale), 1)
                merged = original.replace(stale, paragraphs[0], 1)
                target.write_text(merged)
                self.assertEqual(merged.replace(paragraphs[0], stale, 1), original)
                self._assert_phase_pointer(merged)
                self.assertNotIn(stale, merged)
            snapshots = {target: target.read_bytes() for target in before}
            for _ in range(2):
                ras.render_agent_surfaces(root)
                for target, expected in snapshots.items():
                    self.assertEqual(target.read_bytes(), expected)


class MemoryReviewPromptTests(unittest.TestCase):
    def test_prompt_contract_and_known_bad_controls(self) -> None:
        prompt = (
            PROJECT_ROOT / "framework" / "install" / "lifecycle-prompts"
            / "memory-review.prompt.md"
        ).read_text(encoding="utf-8")
        assert_memory_review_contract(self, prompt)

        known_bad = (
            prompt.replace("canonical_overlap=...,", "", 1),
            prompt.replace(
                "Never send a hand-authored or already-finalized candidate",
                "Send a hand-authored or already-finalized candidate",
                1,
            ),
            prompt.replace('index_build_status(layer="project")', "", 1),
        )
        for broken in known_bad:
            with self.subTest():
                with self.assertRaises(AssertionError):
                    assert_memory_review_contract(self, broken)

    def test_missing_only_baseline_materializes_and_preserves_existing_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            written = ras.render_agent_surfaces(root)
            target = root / "docs" / "prompts" / "memory-review.prompt.md"
            self.assertIn("docs/prompts/memory-review.prompt.md", written)
            assert_memory_review_contract(self, target.read_text(encoding="utf-8"))
            snapshot = target.read_bytes()
            self.assertEqual(ras.render_agent_surfaces(root), [])
            self.assertEqual(target.read_bytes(), snapshot)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "docs" / "prompts" / "memory-review.prompt.md"
            target.parent.mkdir(parents=True)
            existing = b"# Project-owned memory review\n\nkeep exactly\n"
            target.write_bytes(existing)
            ras.render_agent_surfaces(root)
            self.assertEqual(target.read_bytes(), existing)

    def test_fresh_renderer_replays_only_upgrade_policy_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / review_policy_reconcile.UPGRADE_POLICY_DESTINATION
            target.parent.mkdir(parents=True)
            stale = review_policy.UPGRADE_POLICY_BLOCK.replace(
                "**Review memories**", "**Old memory command**"
            )
            prefix = "# Project upgrade\n\nproject-prefix\n\n"
            suffix = "\n\n## Project suffix\n\nkeep me\n"
            target.write_text(prefix + stale + suffix, encoding="utf-8")

            written = ras.render_agent_surfaces(root)
            self.assertIn(review_policy_reconcile.UPGRADE_POLICY_DESTINATION, written)
            rendered = target.read_text(encoding="utf-8")
            self.assertTrue(rendered.startswith(prefix))
            self.assertTrue(rendered.endswith(suffix))
            self.assertIn("**Review memories**", rendered)
            self.assertNotIn("**Old memory command**", rendered)
            first = target.read_bytes()
            self.assertEqual(ras.render_agent_surfaces(root), [])
            self.assertEqual(target.read_bytes(), first)

    def test_upgrade_policy_symlink_escape_refuses_before_sibling_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside:
            root = Path(temp_dir)
            outside_target = Path(outside) / "upgrade.md"
            outside_target.write_text("outside\n", encoding="utf-8")
            target = root / review_policy_reconcile.UPGRADE_POLICY_DESTINATION
            target.parent.mkdir(parents=True)
            target.symlink_to(outside_target)

            with self.assertRaisesRegex(RuntimeError, "escapes the repository root"):
                ras.render_agent_surfaces(root)
            self.assertFalse((root / "docs/prompts/create-wave.prompt.md").exists())
            self.assertEqual(outside_target.read_bytes(), b"outside\n")

    def test_ambiguous_upgrade_policy_marker_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / review_policy_reconcile.UPGRADE_POLICY_DESTINATION
            target.parent.mkdir(parents=True)
            target.write_text(
                review_policy.UPGRADE_POLICY_MARKER_BEGIN
                + "\n"
                + review_policy.UPGRADE_POLICY_MARKER_BEGIN
                + "\n"
                + review_policy.UPGRADE_POLICY_MARKER_END
                + "\n",
                encoding="utf-8",
            )
            before = target.read_bytes()
            with self.assertRaisesRegex(RuntimeError, "ambiguous review-policy upgrade markers"):
                ras.render_agent_surfaces(root)
            self.assertEqual(target.read_bytes(), before)


class ScaffoldBaselineTests(unittest.TestCase):
    def test_plan_template_materializes_missing_with_date_and_preserves_existing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            ras.time, "strftime", return_value="2026-08-17"
        ):
            root = Path(temp_dir)
            written = ras.reconcile_scaffold_baselines(root)
            target = root / "docs" / "plans" / "plan-template.md"
            self.assertEqual(written, ["docs/plans/plan-template.md"])
            text = target.read_text(encoding="utf-8")
            self.assertIn("Last verified: 2026-08-17", text)
            self.assertNotIn("{{generated_at}}", text)
            snapshot = target.read_bytes()
            self.assertEqual(ras.reconcile_scaffold_baselines(root), [])
            self.assertEqual(target.read_bytes(), snapshot)

    def test_plan_template_resolves_target_file_then_module_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target_asset = root / ".wavefoundry/framework/install/plan-template.md"
            target_asset.parent.mkdir(parents=True)
            target_asset.write_text("# Target\n\nLast verified: {{generated_at}}\n", encoding="utf-8")
            self.assertEqual(ras._resolve_install_asset(root, "plan-template.md"), target_asset)
            target_asset.unlink()
            resolved = ras._resolve_install_asset(root, "plan-template.md")
            self.assertEqual(resolved.name, "plan-template.md")
            self.assertTrue(resolved.is_file())


class ReviewProtocolCarrierRegistryTests(unittest.TestCase):
    def test_policy_lifecycle_baselines_are_derived_from_the_registry(self) -> None:
        derived = {
            (carrier.destination, carrier.source.removeprefix("lifecycle:"))
            for carrier in ras.REVIEW_POLICY_CARRIER_REGISTRY
            if carrier.owner == "renderer" and carrier.source.startswith("lifecycle:")
        }
        self.assertTrue(derived)
        self.assertTrue(derived.issubset(set(ras.LIFECYCLE_PROMPT_BASELINES)))

    def test_policy_renderer_materializes_all_registered_policy_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for destination, block in ras.REVIEW_POLICY_SURFACE_BLOCKS.items():
                path = root / destination
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("project prose\n", encoding="utf-8")
            written = ras.reconcile_review_policy_surfaces(root)
            self.assertEqual(set(written), set(ras.REVIEW_POLICY_SURFACE_BLOCKS))
            for destination in ras.REVIEW_POLICY_SURFACE_BLOCKS:
                text = (root / destination).read_text(encoding="utf-8")
                self.assertEqual(text.count(ras.REVIEW_POLICY_SURFACE_MARKER_BEGIN), 1)
                self.assertEqual(text.count(ras.REVIEW_POLICY_SURFACE_MARKER_END), 1)

    def test_pre_v115_existing_docs_receive_owned_policy_baselines_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            direct_docs = {
                carrier.destination
                for carrier in ras.REVIEW_POLICY_CARRIER_REGISTRY
                if carrier.owner == "direct_docs"
                and carrier.destination not in {
                    "docs/agents",
                    "docs/references/dashboard-adapter-model.md",
                }
            }
            original: dict[str, bytes] = {}
            for destination in direct_docs:
                path = root / destination
                path.parent.mkdir(parents=True, exist_ok=True)
                body = f"# Existing project document\n\nproject-owned:{destination}\n".encode()
                path.write_bytes(body)
                original[destination] = body

            written = ras.render_agent_surfaces(root)
            self.assertTrue(direct_docs.issubset(set(written)))
            self.assertEqual(check_review_policy_carriers(root), [])
            for destination, prefix in original.items():
                with self.subTest(destination=destination):
                    rendered = (root / destination).read_bytes()
                    self.assertTrue(rendered.startswith(prefix))
                    text = rendered.decode("utf-8")
                    self.assertEqual(
                        text.count(ras.REVIEW_POLICY_SURFACE_MARKER_BEGIN), 1
                    )
                    self.assertEqual(
                        text.count(ras.REVIEW_POLICY_SURFACE_MARKER_END), 1
                    )

            absent = root / "docs/references/dashboard-adapter-model.md"
            self.assertFalse(absent.exists())
            snapshot = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(ras.render_agent_surfaces(root), [])
            self.assertEqual(
                snapshot,
                {
                    path.relative_to(root).as_posix(): path.read_bytes()
                    for path in root.rglob("*")
                    if path.is_file()
                },
            )

    def test_independent_reference_contract_is_bounded_and_preserves_independence(self) -> None:
        seeds_root = PROJECT_ROOT / "framework" / "seeds"
        core = (seeds_root / "209-agent-harness-core.prompt.md").read_text(encoding="utf-8")
        code = (seeds_root / "221-code-reviewer.prompt.md").read_text(encoding="utf-8")
        qa = (seeds_root / "239-qa-reviewer.prompt.md").read_text(encoding="utf-8")

        for literal in (
            "one highest-risk differential or invariant probe",
            "normative specification",
            "materially independent implementation",
            "prior-version behavior contract",
            "authoritative schema/model",
            "metamorphic invariant",
            "fixed seed or durable fixture",
            "reject invalid generated inputs before comparison",
            "same hypothesis list is not an independent reference",
            "Implementer-authored evidence remains `independent: false`",
            "If no credible independent reference exists",
            "not reviewer adherence",
        ):
            self.assertIn(literal, core)
        self.assertIn("Name the reference, the exact promised property", code)
        self.assertIn("name the assertion that would falsify it", qa)
        self.assertIn("Executable review never broadens task authority", core)
        self.assertNotIn("oracle_id", core + code + qa)
        self.assertNotIn("oracle_property", core + code + qa)

    def test_carrier_blocks_carry_chain_aware_independence_contract(self) -> None:
        """1tmb2 AC-8: the shared carrier block and the QA extension name the
        enforced rejection codes and the honest declaration limit, so every
        rendered carrier propagates the enforced-versus-declared split."""
        block = ras.REVIEW_PROTOCOL_CARRIER_BLOCK
        self.assertIn("wf_review_wave(phase='implementation')", block)
        self.assertIn("`wf_review_event`", block)
        self.assertIn("never hand-edit", block)
        self.assertIn("role without lifecycle mutation authority", block)
        self.assertNotIn("four-way actionability gate", block)
        self.assertNotIn("`do_now`", block)
        self.assertIn("`reverification_context_not_fresh`", block)
        self.assertIn("`reverification_actor_not_distinct`", block)
        self.assertIn("`review_evidence_independence_invalid`", block)
        self.assertIn("not caller", block)
        qa_block = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "239-qa-reviewer.prompt.md", "docs/agents/qa-reviewer.md"
            )
        )
        self.assertIn("must not reverify its own", qa_block)
        # The codes pinned here are the validator's actual constants, so a
        # rename on either side breaks this test.
        import review_evidence

        self.assertIn(f"`{review_evidence.REVERIFICATION_CONTEXT_NOT_FRESH}`", block)
        self.assertIn(f"`{review_evidence.REVERIFICATION_ACTOR_NOT_DISTINCT}`", block)
        self.assertIn(
            f"`{review_evidence.REVIEW_EVIDENCE_INDEPENDENCE_INVALID}`", block
        )

    def test_independent_reference_carrier_is_role_scoped_and_carries_the_proof_ceiling(self) -> None:
        code = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "221-code-reviewer.prompt.md", "docs/agents/code-reviewer.md"
            )
        )
        qa = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "239-qa-reviewer.prompt.md", "docs/agents/qa-reviewer.md"
            )
        )
        security = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "229-security-reviewer.prompt.md", "docs/agents/security-reviewer.md"
            )
        )

        for role_block in (code, qa):
            self.assertIn("same-hypothesis helper", role_block)
            self.assertIn("`independent: false`", role_block)
            self.assertIn("Carrier-presence tests prove propagation", role_block)
        self.assertIn("assertion that would falsify", qa)
        self.assertNotIn("Independent-reference verification", security)

        repo_root = TESTS_ROOT.parents[3]
        for rel in ("docs/agents/code-reviewer.md", "docs/agents/qa-reviewer.md"):
            rendered = (repo_root / rel).read_text(encoding="utf-8")
            self.assertIn(ras.INDEPENDENT_REFERENCE_CARRIER_BLOCK, rendered)

    def test_dual_implementation_reference_scenario_carries_bounded_falsification_contract(self) -> None:
        # AC-3 scenario fixture: a deterministic fallback parser has a materially
        # independent grammar-backed implementation. The carrier must ask for the exact
        # compared property and common-mode limit, while keeping the probe finite.
        scenario = {
            "mechanism": "fallback parser",
            "reference": "materially independent grammar-backed parser",
            "promised_property": "stable public initializer identity",
            "highest_risk_input": "valid declaration-prefix boundary",
        }
        self.assertNotEqual(scenario["mechanism"], scenario["reference"])
        code = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "221-code-reviewer.prompt.md", "docs/agents/code-reviewer.md"
            )
        )
        qa = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "239-qa-reviewer.prompt.md", "docs/agents/qa-reviewer.md"
            )
        )
        code_flat = " ".join(code.split())
        self.assertIn("one highest-risk probe bounded, reproducible", code_flat)
        self.assertIn("exact promised property", code_flat)
        self.assertIn("common-mode", code_flat)
        self.assertIn("assertion that would falsify", qa)
        self.assertIn("limited to valid inputs", " ".join(qa.split()))

    def test_no_reference_or_unsafe_probe_scenario_narrows_claim_without_broadening_authority(self) -> None:
        # AC-3 scenario fixture: no credible reference exists and the tempting comparison
        # would require an unauthorized external mutation. The canonical rule must record
        # the limitation/narrow the claim, not invent a reference or broaden task authority.
        scenario = {
            "credible_reference": None,
            "candidate_probe": "unauthorized external mutation",
            "authorized": False,
            "expected_disposition": "record narrow limitation",
        }
        self.assertIsNone(scenario["credible_reference"])
        self.assertFalse(scenario["authorized"])
        core = (
            PROJECT_ROOT / "framework" / "seeds" / "209-agent-harness-core.prompt.md"
        ).read_text(encoding="utf-8")
        self.assertIn("If no credible independent reference exists", core)
        self.assertIn("record that narrow limitation", core)
        self.assertIn("Executable review never broadens task authority", core)
        self.assertIn("not proof of universal correctness", core)

    def test_manifest_is_derived_from_unique_registry_destinations(self) -> None:
        expected = tuple(row.destination for row in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY)
        self.assertEqual(ras.REVIEW_PROTOCOL_CARRIER_MANIFEST, expected)
        self.assertEqual(len(expected), len(set(expected)))
        self.assertIn("docs/agents/qa-reviewer.md", expected)
        self.assertIn("docs/prompts/agents/review-wave.prompt.md", expected)
        self.assertIn("docs/contributing/review-and-evals.md", expected)
        seeds_root = PROJECT_ROOT / "framework" / "seeds"
        missing_sources = [
            row.source_seed
            for row in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY
            if not (seeds_root / row.source_seed).is_file()
        ]
        self.assertEqual(missing_sources, [])

    def test_self_host_ownership_contracts_cover_every_registry_destination(self) -> None:
        repo_root = TESTS_ROOT.parents[3]
        ownership = (repo_root / "docs" / "contributing" / "review-and-evals.md").read_text(
            encoding="utf-8"
        )
        change = next((repo_root / "docs" / "waves").glob("1skt1*/1siu0*.md")).read_text(
            encoding="utf-8"
        )
        for carrier in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY:
            self.assertIn(carrier.destination, ownership, carrier.destination)
            self.assertIn(carrier.destination, change, carrier.destination)

    def test_reconciles_before_guru_guard_preserves_extensions_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target = repo_root / "docs" / "agents" / "code-reviewer.md"
            target.parent.mkdir(parents=True)
            operator_extension = "## Project extension\n\n- keep this byte-for-byte\n"
            target.write_text("# Code Reviewer\n\n" + operator_extension, encoding="utf-8")

            written = ras.render_agent_surfaces(repo_root)
            self.assertIn("docs/agents/code-reviewer.md", written)
            self.assertIn("docs/agents/qa-reviewer.md", written)
            self.assertIn("docs/prompts/review-wave.prompt.md", written)
            self.assertIn("docs/prompts/create-wave.prompt.md", written)
            first = target.read_bytes()
            text = first.decode("utf-8")
            self.assertIn(operator_extension, text)
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, text)
            self.assertIn("wf_review_wave(phase='implementation')", text)
            self.assertIn("Independent-reference verification", text)
            qa_text = (repo_root / "docs" / "agents" / "qa-reviewer.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("assertion that would falsify", qa_text)
            self.assertIn("`independent: false`", qa_text)
            self.assertFalse((repo_root / "docs" / "agents" / "guru.md").exists())
            create_wave = (repo_root / "docs" / "prompts" / "create-wave.prompt.md").read_text(encoding="utf-8")
            for literal in (
                # declaration-check: asserts the declaration contract; creates no lifecycle state
                "review-evidence-source: events.jsonl",
                "exactly empty file",
                "No review findings recorded.",
                "sole",
            ):
                self.assertIn(literal, create_wave)
            self.assertNotIn("review-evidence-adoptions.json", create_wave)
            self.assertEqual(
                create_wave.count(ras.CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN), 1
            )
            self.assertEqual(
                create_wave.count(ras.CONTEXT_EFFICIENCY_CARRIER_MARKER_END), 1
            )
            self.assertIn(ras._context_efficiency_carrier_block(), create_wave)
            self.assertNotIn("review-evidence-protocol: 1", create_wave)
            self.assertNotIn("wave:finding-synthesis", create_wave)
            self.assertNotIn("```jsonl", create_wave)

            self.assertEqual(ras.render_agent_surfaces(repo_root), [])
            self.assertEqual(target.read_bytes(), first)

    def test_context_efficiency_region_refreshes_exactly_once_and_preserves_project_prose(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target = repo_root / ras.CONTEXT_EFFICIENCY_DESTINATION
            target.parent.mkdir(parents=True)
            prefix = "# Project Create Wave\n\nproject-prefix  \n\n"
            suffix = "\n\n## Project extension\n\n- keep this byte-for-byte\n"
            target.write_text(
                prefix
                + "<!-- wavefoundry:context-efficiency-carrier begin -->"
                + "\nstale telemetry prose\n"
                + "<!-- wavefoundry:context-efficiency-carrier end -->"
                + suffix,
                encoding="utf-8",
            )

            ras.render_agent_surfaces(repo_root)
            first = target.read_bytes()
            text = first.decode("utf-8")
            self.assertTrue(text.startswith(prefix))
            self.assertIn(suffix, text)
            self.assertNotIn("stale telemetry prose", text)
            self.assertNotIn("wavefoundry:context-efficiency-carrier", text)
            self.assertEqual(
                text.count(ras.CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN), 1
            )
            self.assertEqual(
                text.count(ras.CONTEXT_EFFICIENCY_CARRIER_MARKER_END), 1
            )
            self.assertIn(ras._context_efficiency_carrier_block(), text)

            ras.render_agent_surfaces(repo_root)
            self.assertEqual(target.read_bytes(), first)

    def test_context_efficiency_carrier_has_no_renderer_fallback_copy(self) -> None:
        source = RENDER_SCRIPT.read_text(encoding="utf-8")
        self.assertIn(
            "CONTEXT_EFFICIENCY_CARRIER_BLOCK = None",
            source,
        )
        self.assertNotIn("Estimated retrieval context avoided", source)
        self.assertNotIn("workflow-instruction compression proxy", source)

    def test_context_efficiency_seed_obligations_cover_target_propagation(self) -> None:
        seeds_root = PROJECT_ROOT / "framework" / "seeds"
        prompt_bootstrap = seeds_root.joinpath(
            "100-project-prompt-surface-bootstrap.prompt.md"
        ).read_text(encoding="utf-8")
        wave_memory = seeds_root.joinpath(
            "110-wave-memory-bootstrap.prompt.md"
        ).read_text(encoding="utf-8")
        for literal in (
            "wave:context-efficiency-carrier",
            "`create-wave`",
            "`prepare-wave`",
            "`implement-wave`",
            "`review-wave`",
            "`close-wave`",
            "with no framework-seed fallback",
            "Keep `.wavefoundry/logs/` in the managed runtime ignore block",
            "never create `context-efficiency.sqlite`",
            "historical `wave.md` or `events.jsonl`",
        ):
            self.assertIn(literal, prompt_bootstrap)
        for literal in (
            "operational aggregate, not lifecycle or review authority",
            "single plain table",
            "Estimated context avoided",
            "canonical `wave:` markers",
            "successful create or mutating prepare",
            "accounting-gap poison",
            "creates no SQLite store eagerly",
        ):
            self.assertIn(literal, wave_memory)

    def test_stale_owned_region_refreshes_without_touching_surrounding_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target = repo_root / "docs" / "prompts" / "review-wave.prompt.md"
            target.parent.mkdir(parents=True)
            prefix = "# Review Wave\n\nproject-prefix\n\n"
            suffix = "\n\nproject-suffix\n"
            target.write_text(
                prefix
                + "<!-- waveframework:executable-review-evidence begin — generated by render_agent_surfaces.py; preserve project-authored content outside this region -->"
                + "\nstale\n"
                + "<!-- waveframework:executable-review-evidence end -->"
                + suffix,
                encoding="utf-8",
            )

            ras.reconcile_review_protocol_surfaces(repo_root)
            text = target.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(prefix))
            self.assertTrue(text.endswith(suffix))
            self.assertNotIn("\nstale\n", text)
            self.assertNotIn("waveframework:executable-review-evidence", text)
            self.assertIn("public or registered", text)

    def test_malformed_owned_markers_fail_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target = repo_root / "docs" / "agents" / "qa-reviewer.md"
            target.parent.mkdir(parents=True)
            original = "# QA\n\n" + ras.REVIEW_PROTOCOL_MARKER_BEGIN + "\ntruncated\n"
            target.write_text(original, encoding="utf-8")

            written = ras.reconcile_review_protocol_surfaces(repo_root)
            self.assertNotIn("docs/agents/qa-reviewer.md", written)
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_parent_symlink_escape_is_refused_without_touching_external_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            repo_root = outer / "repo"
            outside = outer / "outside"
            (repo_root / "docs").mkdir(parents=True)
            outside.mkdir()
            sentinel = outside / "qa-reviewer.md"
            sentinel.write_text("external sentinel\n", encoding="utf-8")
            (repo_root / "docs" / "agents").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(RuntimeError, "escapes the repository root"):
                ras.reconcile_review_protocol_surfaces(repo_root)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "external sentinel\n")

    def test_only_registered_enabled_native_role_wrappers_are_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            registered = repo_root / ".claude" / "agents" / "code-reviewer.md"
            unregistered = repo_root / ".claude" / "agents" / "project-custom.md"
            codex = repo_root / ".codex" / "skills" / "agent-role-code-reviewer" / "SKILL.md"
            for path in (registered, unregistered, codex):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {path.stem}\n\nproject extension\n", encoding="utf-8")

            manifest = ras.review_protocol_carrier_manifest(repo_root)
            self.assertIn(".claude/agents/code-reviewer.md", manifest)
            self.assertIn(".codex/skills/agent-role-code-reviewer/SKILL.md", manifest)
            self.assertNotIn(".claude/agents/project-custom.md", manifest)

            written = ras.reconcile_review_protocol_surfaces(repo_root)
            self.assertIn(".claude/agents/code-reviewer.md", written)
            self.assertIn(".codex/skills/agent-role-code-reviewer/SKILL.md", written)
            self.assertNotIn(".claude/agents/project-custom.md", written)
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, registered.read_text(encoding="utf-8"))
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, codex.read_text(encoding="utf-8"))
            self.assertIn("Independent-reference verification", registered.read_text(encoding="utf-8"))
            self.assertIn("Independent-reference verification", codex.read_text(encoding="utf-8"))
            self.assertNotIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, unregistered.read_text(encoding="utf-8"))

    def test_self_host_enabled_manifest_has_exactly_one_owned_region(self) -> None:
        repo_root = TESTS_ROOT.parents[3]
        manifest = ras.review_protocol_carrier_manifest(repo_root)
        self.assertIn(".claude/agents/guru.md", manifest)
        self.assertIn(".codex/skills/wf-guru/SKILL.md", manifest)
        for rel in manifest:
            path = repo_root / rel
            if not path.is_file():
                # Conditional repo-local/native carriers are enabled by presence.
                continue
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(ras.REVIEW_PROTOCOL_MARKER_BEGIN), 1, rel)
            self.assertEqual(text.count(ras.REVIEW_PROTOCOL_MARKER_END), 1, rel)


class RenderAgentSurfacesTests(unittest.TestCase):
    def test_public_agent_render_refuses_dangling_native_wrapper_symlink_escapes(self) -> None:
        for shape in ("final", "parent"):
            with self.subTest(shape=shape), tempfile.TemporaryDirectory() as temp_dir:
                outer = Path(temp_dir)
                repo_root = outer / "repo"
                outside = outer / "outside"
                (repo_root / "docs" / "agents").mkdir(parents=True)
                (repo_root / "docs" / "agents" / "guru.md").write_text(
                    GURU_STUB, encoding="utf-8"
                )
                skill = repo_root / ".codex" / "skills" / "wf-guru" / "SKILL.md"
                skill.parent.mkdir(parents=True)
                if shape == "final":
                    outside.mkdir()
                    skill.symlink_to(outside / "created.md")
                    escaped = outside / "created.md"
                else:
                    skill.parent.rmdir()
                    outside.mkdir()
                    skill.parent.symlink_to(outside, target_is_directory=True)
                    escaped = outside / "SKILL.md"

                result = subprocess.run(
                    ["python3", str(RENDER_SCRIPT), "--repo-root", str(repo_root)],
                    cwd=SCRIPTS_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("escapes the repository root", result.stderr)
                self.assertFalse(escaped.exists())

    def test_public_platform_render_refuses_final_carrier_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            repo_root = outer / "repo"
            outside = outer / "outside.md"
            target = repo_root / "docs" / "agents" / "qa-reviewer.md"
            target.parent.mkdir(parents=True)
            outside.write_text("external sentinel\n", encoding="utf-8")
            target.symlink_to(outside)

            result = subprocess.run(
                ["python3", str(PLATFORM_RENDER_SCRIPT), "--repo-root", str(repo_root)],
                cwd=SCRIPTS_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("escapes the repository root", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(outside.read_text(encoding="utf-8"), "external sentinel\n")

    def test_missing_guru_stays_disabled_while_required_review_carriers_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            result = subprocess.run(
                ["python3", str(RENDER_SCRIPT), "--repo-root", str(repo_root)],
                cwd=PROJECT_ROOT / "framework" / "scripts",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((repo_root / "docs" / "agents" / "qa-reviewer.md").is_file())
            self.assertTrue((repo_root / "docs" / "prompts" / "review-wave.prompt.md").is_file())
            self.assertFalse((repo_root / "docs" / "agents" / "guru.md").exists())
            self.assertFalse((repo_root / ".cursor" / "rules" / "auto-guru.mdc").exists())

    def test_renders_tier2_and_tier3_when_guru_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            (repo_root / ".cursor" / "rules").mkdir(parents=True)
            (repo_root / ".cursor" / "rules" / "project-context.mdc").write_text(
                "# Cursor\n\n## Key Guardrails\n\n- stage gate\n",
                encoding="utf-8",
            )
            (repo_root / ".claude" / "agents").mkdir(parents=True)
            # Wave 1p6lp: skill emission is host-dir gated; the full platform
            # render creates .codex via render_codex_mcp_config before this
            # pass, so the standalone agent render needs the dir pre-made.
            (repo_root / ".codex").mkdir()
            (repo_root / ".junie").mkdir()
            (repo_root / ".junie" / "guidelines.md").write_text(
                "# Junie\n\n## Key Rules\n\n- other\n",
                encoding="utf-8",
            )
            (repo_root / "CLAUDE.md").write_text(
                "# Claude\n\n## Startup Order\n\n1. AGENTS.md\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(RENDER_SCRIPT), "--repo-root", str(repo_root)],
                cwd=PROJECT_ROOT / "framework" / "scripts",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

            cursor_rule = repo_root / ".cursor" / "rules" / "auto-guru.mdc"
            self.assertTrue(cursor_rule.is_file())
            self.assertIn("alwaysApply: true", cursor_rule.read_text(encoding="utf-8"))

            claude_agent = repo_root / ".claude" / "agents" / "guru.md"
            self.assertTrue(claude_agent.is_file())
            self.assertIn("PROACTIVELY", claude_agent.read_text(encoding="utf-8"))
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, claude_agent.read_text(encoding="utf-8"))

            codex_skill = repo_root / ".codex" / "skills" / "wf-guru" / "SKILL.md"
            self.assertTrue(codex_skill.is_file())
            codex_skill_text = codex_skill.read_text(encoding="utf-8")
            self.assertIn("name: wf-guru", codex_skill_text)
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, codex_skill_text)

            # Registry skills land on every active skill host (wave 1p6lp).
            claude_guru_skill = repo_root / ".claude" / "skills" / "wf-guru" / "SKILL.md"
            self.assertTrue(claude_guru_skill.is_file())
            for host in (".codex", ".claude"):
                upgrade_skill = repo_root / host / "skills" / "wf-upgrade" / "SKILL.md"
                self.assertTrue(upgrade_skill.is_file(), upgrade_skill)
                self.assertIn("name: wf-upgrade", upgrade_skill.read_text(encoding="utf-8"))
            # .agents is absent in this repo fixture, so no Antigravity tree.
            self.assertFalse((repo_root / ".agents").exists())

            codex_mcp_config = repo_root / ".codex" / "config.toml"
            self.assertFalse(
                codex_mcp_config.exists(),
                "agent renderer must not own Codex MCP configuration",
            )

            junie = (repo_root / ".junie" / "guidelines.md").read_text(encoding="utf-8")
            self.assertIn("wave:auto-guru begin", junie)
            self.assertIn("code_ask", junie)

            claude = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("wave:auto-guru begin", claude)
            self.assertIn("guru", claude)


class ReviewPlanPromptMigrationTests(unittest.TestCase):
    _EXACT_CONTRACT = (
        ("Heading", "# Interrogate This Plan", "# Review Plan"),
        (
            "Shortcut",
            "Shortcut: **`Interrogate this plan`** | Alias: **`Stress-test this plan`**",
            "Shortcut: **`Review plan`** | Aliases: **`Interrogate this plan`**, **`Stress-test this plan`**",
        ),
        (
            "Purpose",
            "Optional stress-test of a consolidated change doc before wave admission. Walks every unresolved decision branch in Requirements, Acceptance Criteria, and Scope.",
            "Optional stress-test of a consolidated change doc, or the current wave record when no change is specified, before or after admission and before implementation. Walks every unresolved decision branch in Requirements, Acceptance Criteria, and Scope.",
        ),
        (
            "Input fallback",
            "Given a change doc as context:",
            "Given a change doc as context, or the current wave record when no change is specified:",
        ),
        (
            "When to use",
            "- Before admitting a complex or high-risk change",
            "- Before or after admitting a complex or high-risk change, but before implementation",
        ),
        (
            "No-gate timing",
            "**Interrogate this plan** is an optional stress-testing tool, not a required lifecycle step. Use it before or after authoring a change doc but before wave admission.",
            "**Review plan** is an optional stress-testing tool, not a required lifecycle step. Use it before or after plan admission, at the operator's discretion, before implementation begins.",
        ),
        (
            "Canonical source",
            "See `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md` for the full interrogation contract.",
            "See `.wavefoundry/framework/seeds/175-review-plan.prompt.md` for the full plan-review contract.",
        ),
    )
    _EARLY_CANONICAL_CONTRACT = (
        ("Heading", "# Interrogate This Plan Prompt", ("# Review Plan Prompt",)),
        (
            "Primary trigger",
            "- `Interrogate this plan`",
            ("- `Review plan`", "- `Interrogate this plan`"),
        ),
        (
            "Canonical source",
            "Use `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md` to:",
            ("Use `.wavefoundry/framework/seeds/175-review-plan.prompt.md` to:",),
        ),
        (
            "Input fallback",
            "- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md` or `docs/plans/<change-id>.md`) or wave record (`docs/waves/<wave-id>/wave.md`).",
            ("- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md` or `docs/plans/<change-id>.md`) or, when no change is specified, the current wave record (`docs/waves/<wave-id>/wave.md`).",),
        ),
        (
            "Scope wording",
            "- Do not re-plan or derive new scope during interrogation; record emergent scope items as follow-on candidates rather than introducing them inline.",
            ("- Do not re-plan or derive new scope during plan review; record emergent scope items as follow-on candidates rather than introducing them inline.",),
        ),
        (
            "No-gate identity",
            "- Do not treat this as a required lifecycle gate; it is entirely voluntary before or after plan admission.",
            ("- Do not treat **Review plan** as a required lifecycle gate; it is entirely voluntary before or after plan admission.",),
        ),
        (
            "Bounded wording",
            "- Keep interrogation bounded to Requirements, Acceptance Criteria, and Scope — do not re-examine explicitly resolved Decision Log entries.",
            ("- Keep plan review bounded to Requirements, Acceptance Criteria, and Scope — do not re-examine explicitly resolved Decision Log entries.",),
        ),
        (
            "Batch example",
            "- In `--batch` mode (e.g. `Interrogate this plan --batch`): dump all unresolved questions as a numbered list rather than asking one at a time. Each item includes the recommended answer and source citation.",
            ("- In `--batch` mode (e.g. `Review plan --batch`): dump all unresolved questions as a numbered list rather than asking one at a time. Each item includes the recommended answer and source citation.",),
        ),
    )

    def _legacy_text(self, newline: str = "\n") -> str:
        return newline.join(
            [old_line for _label, old_line, _new_line in self._EXACT_CONTRACT]
            + ["", "## Project extension", "Keep this authored paragraph byte-identical.", ""]
        )

    def test_exact_seven_line_contract_and_other_bytes_are_preserved(self) -> None:
        self.assertEqual(ras.REVIEW_PLAN_LEGACY_CONTRACT_LINES, self._EXACT_CONTRACT)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old = root / ras.REVIEW_PLAN_OLD_PROMPT
            old.parent.mkdir(parents=True)
            original = self._legacy_text("\r\n")
            with old.open("w", encoding="utf-8", newline="") as handle:
                handle.write(original)

            self.assertEqual(
                ras.migrate_review_plan_prompt(root),
                [ras.REVIEW_PLAN_OLD_PROMPT, ras.REVIEW_PLAN_NEW_PROMPT],
            )
            new = root / ras.REVIEW_PLAN_NEW_PROMPT
            self.assertFalse(old.exists())
            with new.open("r", encoding="utf-8", newline="") as handle:
                actual = handle.read()
            expected = original
            for _label, old_line, new_line in self._EXACT_CONTRACT:
                expected = expected.replace(old_line, new_line)
            self.assertEqual(actual.encode("utf-8"), expected.encode("utf-8"))
            self.assertIn("\r\n## Project extension\r\n", actual)

    def test_recovered_early_canonical_profile_migrates_exactly(self) -> None:
        self.assertEqual(
            ras.REVIEW_PLAN_EARLY_CANONICAL_CONTRACT_LINES,
            self._EARLY_CANONICAL_CONTRACT,
        )
        recovered_lines = [
            "# Interrogate This Plan Prompt",
            "",
            "Owner: Engineering",
            "Status: active",
            "Last verified: 2026-05-02",
            "",
            "## Purpose",
            "",
            "Optional shortcut for stress-testing a plan before or after admission by walking every unresolved decision branch one question at a time, providing recommendations sourced from project resources, and stopping when all branches are resolved.",
            "",
            "## Trigger Phrases",
            "",
            "- `Interrogate this plan`",
            "- `Stress-test this plan`",
            "",
            "## Task",
            "",
            "Use `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md` to:",
            "",
            "- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md` or `docs/plans/<change-id>.md`) or wave record (`docs/waves/<wave-id>/wave.md`).",
            "- Walk every unresolved decision branch in its **Requirements**, **Acceptance Criteria**, and **Scope** sections.",
            "- In default interactive mode, ask one question at a time. With each question, provide a recommended answer and cite the project resource (source code, `docs/specs/*.md`, `docs/architecture/`, `docs/references/`, `docs/agents/`, or other checked-in artifact) that supports it.",
            "- Self-answer without operator input when the answer is derivable from project resources; surface to the operator only questions that genuinely require human judgment (product intent, business priority, or architectural tradeoff not resolvable from evidence).",
            "- Log self-answered questions briefly so the operator can see what was resolved without their input.",
            '- Stop when all branches in Requirements, Acceptance Criteria, and Scope are resolved — or when the operator says "enough" or "stop".',
            "- In `--batch` mode (e.g. `Interrogate this plan --batch`): dump all unresolved questions as a numbered list rather than asking one at a time. Each item includes the recommended answer and source citation.",
            "",
            "## Required Behavior",
            "",
            "- Attempt to self-answer from project resources before surfacing any question to the operator.",
            "- Do not re-plan or derive new scope during interrogation; record emergent scope items as follow-on candidates rather than introducing them inline.",
            "- Do not treat this as a required lifecycle gate; it is entirely voluntary before or after plan admission.",
            "- Keep interrogation bounded to Requirements, Acceptance Criteria, and Scope — do not re-examine explicitly resolved Decision Log entries.",
            "- Do not repeat questions the operator has already answered.",
        ]
        original = "\r\n".join(recovered_lines) + "\r\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old = root / ras.REVIEW_PLAN_OLD_PROMPT
            old.parent.mkdir(parents=True)
            with old.open("w", encoding="utf-8", newline="") as handle:
                handle.write(original)

            self.assertEqual(
                ras.migrate_review_plan_prompt(root),
                [ras.REVIEW_PLAN_OLD_PROMPT, ras.REVIEW_PLAN_NEW_PROMPT],
            )
            with (root / ras.REVIEW_PLAN_NEW_PROMPT).open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                migrated = handle.read()

        self.assertIn(
            "- `Review plan`\r\n- `Interrogate this plan`\r\n- `Stress-test this plan`",
            migrated,
        )
        self.assertIn("Last verified: 2026-05-02\r\n", migrated)
        self.assertIn("before or after admission", migrated)
        self.assertNotIn("175-interrogate-plan.prompt.md", migrated)
        for label, old_line, new_lines in self._EARLY_CANONICAL_CONTRACT:
            if label != "Primary trigger":
                self.assertNotIn(old_line, migrated)
            for new_line in new_lines:
                self.assertIn(new_line, migrated)

    def test_early_profile_embedded_contract_lines_block_without_mutation(self) -> None:
        for changed_label, changed_old, _changed_new in self._EARLY_CANONICAL_CONTRACT:
            with self.subTest(field=changed_label), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                old = root / ras.REVIEW_PLAN_OLD_PROMPT
                new = root / ras.REVIEW_PLAN_NEW_PROMPT
                old.parent.mkdir(parents=True)
                original = "\n".join(
                    (
                        f"PROJECT-PREFIX {old_line} PROJECT-SUFFIX"
                        if old_line == changed_old
                        else old_line
                    )
                    for _label, old_line, _new_lines in self._EARLY_CANONICAL_CONTRACT
                ) + "\n"
                old.write_text(original, encoding="utf-8")

                with self.assertRaisesRegex(RuntimeError, changed_label):
                    ras.migrate_review_plan_prompt(root)

                self.assertEqual(old.read_text(encoding="utf-8"), original)
                self.assertFalse(new.exists())

    def test_contract_strings_embedded_in_customized_lines_block_without_mutation(self) -> None:
        for changed_label, changed_old, _changed_new in self._EXACT_CONTRACT:
            with self.subTest(field=changed_label), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                old = root / ras.REVIEW_PLAN_OLD_PROMPT
                new = root / ras.REVIEW_PLAN_NEW_PROMPT
                old.parent.mkdir(parents=True)
                original = "\n".join(
                    (
                        f"PROJECT-PREFIX {old_line} PROJECT-SUFFIX"
                        if old_line == changed_old
                        else old_line
                    )
                    for _label, old_line, _new_line in self._EXACT_CONTRACT
                ) + "\n"
                old.write_text(original, encoding="utf-8")

                with self.assertRaisesRegex(RuntimeError, changed_label):
                    ras.migrate_review_plan_prompt(root)

                self.assertEqual(old.read_text(encoding="utf-8"), original)
                self.assertFalse(new.exists())

    def test_five_prompt_states_fail_closed_or_converge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.assertEqual(ras.migrate_review_plan_prompt(root), [])  # neither

            new = root / ras.REVIEW_PLAN_NEW_PROMPT
            new.parent.mkdir(parents=True)
            new.write_bytes(b"project-owned new prompt\r\n")
            self.assertEqual(ras.migrate_review_plan_prompt(root), [])  # new-only
            self.assertEqual(new.read_bytes(), b"project-owned new prompt\r\n")

        for state in ("customized-old-only", "both"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                old = root / ras.REVIEW_PLAN_OLD_PROMPT
                new = root / ras.REVIEW_PLAN_NEW_PROMPT
                old.parent.mkdir(parents=True)
                old_bytes = self._legacy_text().replace(
                    "# Interrogate This Plan", "# Project-specific plan review"
                ).encode("utf-8")
                old.write_bytes(old_bytes)
                if state == "both":
                    new_bytes = b"independent new prompt\n"
                    new.write_bytes(new_bytes)
                with self.assertRaisesRegex(RuntimeError, "migration blocked"):
                    ras.migrate_review_plan_prompt(root)
                self.assertEqual(old.read_bytes(), old_bytes)
                if state == "customized-old-only":
                    self.assertFalse(new.exists())
                else:
                    self.assertEqual(new.read_bytes(), new_bytes)

    def test_seventh_baseline_is_metadata_stamped_and_missing_only(self) -> None:
        self.assertEqual(len(ras.LIFECYCLE_PROMPT_BASELINES), 7)
        self.assertEqual(
            ras.LIFECYCLE_PROMPT_BASELINES[-1],
            (ras.REVIEW_PLAN_NEW_PROMPT, "review-plan.prompt.md"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            written = ras.reconcile_lifecycle_prompt_baselines(root)
            self.assertIn(ras.REVIEW_PLAN_NEW_PROMPT, written)
            prompt = root / ras.REVIEW_PLAN_NEW_PROMPT
            first = prompt.read_bytes()
            text = first.decode("utf-8")
            self.assertIn("Owner: Engineering", text)
            self.assertIn("Status: active", text)
            self.assertRegex(text, r"Last verified: \d{4}-\d{2}-\d{2}")
            self.assertNotIn("{{generated_at}}", text)
            self.assertEqual(ras.reconcile_lifecycle_prompt_baselines(root), [])
            self.assertEqual(prompt.read_bytes(), first)

    def test_full_render_orders_migration_before_skill_and_baseline(self) -> None:
        order: list[str] = []
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            ras, "preflight_agent_surface_paths", return_value=None
        ), patch.object(
            ras, "migrate_review_plan_prompt", side_effect=lambda _root: order.append("migration") or []
        ), patch.object(
            ras, "render_skills", side_effect=lambda _root: order.append("skills") or []
        ), patch.object(
            ras,
            "reconcile_lifecycle_prompt_baselines",
            side_effect=lambda _root: order.append("baselines") or [],
        ), patch.object(ras, "reconcile_scaffold_baselines", return_value=[]), patch.object(
            ras, "reconcile_upgrade_policy_surface", return_value=[]
        ), patch.object(ras, "reconcile_review_protocol_surfaces", return_value=[]), patch.object(
            ras, "reconcile_review_policy_surfaces", return_value=[]
        ), patch.object(ras, "reconcile_context_efficiency_surface", return_value=[]), patch.object(
            ras, "guru_available", return_value=False
        ):
            ras.render_agent_surfaces(Path(temp_dir))
        self.assertEqual(order, ["migration", "skills", "baselines"])


class SkillRegistryTests(unittest.TestCase):
    """Wave 1p6lp (1p6lo) — unified skill registry + SKILL.md emitter."""

    # The doc-gated skills (wave 1ve3a) and their gate docs.
    _DOC_GATED = {
        "wf-package": "docs/prompts/package-wavefoundry.prompt.md",
        "wf-code-cleanup": "docs/prompts/codebase-cleanup-review.prompt.md",
        "wf-techdocs": "docs/prompts/refresh-techdocs.prompt.md",
    }

    def _repo(
        self,
        root: Path,
        *,
        guru: bool = True,
        gate_docs: bool = True,
        hosts=(".codex", ".claude", ".agents"),
    ) -> None:
        (root / "docs" / "agents").mkdir(parents=True)
        if guru:
            (root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
        if gate_docs:
            (root / "docs" / "prompts").mkdir(parents=True, exist_ok=True)
            for rel in self._DOC_GATED.values():
                (root / rel).write_text("# gate doc stub\n", encoding="utf-8")
        for host in hosts:
            (root / host).mkdir(parents=True, exist_ok=True)

    def test_registry_names_hold_the_wf_namespace_policy(self) -> None:
        self.assertTrue(ras.SKILL_REGISTRY)
        for skill in ras.SKILL_REGISTRY:
            self.assertRegex(skill.name, r"^wf-[a-z0-9]+(?:-[a-z0-9]+)*$")
            self.assertTrue(skill.description.strip())
            self.assertTrue(skill.body.strip())
            # Frontmatter descriptions render as single-line YAML plain
            # scalars: a newline or ": " would break strict parsers.
            self.assertNotIn("\n", skill.description)
            self.assertNotIn(": ", skill.description, skill.name)

    def test_registry_descriptions_are_pairwise_distinct(self) -> None:
        descriptions = [skill.description for skill in ras.SKILL_REGISTRY]
        self.assertEqual(len(descriptions), len(set(descriptions)))

    def test_review_plan_is_the_only_plan_review_skill_and_preserves_boundary(self) -> None:
        by_name = {skill.name: skill for skill in ras.SKILL_REGISTRY}
        self.assertIn("wf-review-plan", by_name)
        self.assertNotIn("wf-interrogate-plan", by_name)
        skill = by_name["wf-review-plan"]
        for literal in (
            "docs/prompts/review-plan.prompt.md",
            "current wave record",
            "before or after admission",
            "before implementation",
            "no typed signoff",
            "wf-review-wave",
        ):
            self.assertIn(literal, f"{skill.description}\n{skill.body}")

        council = by_name["wf-council"]
        council_contract = f"{council.description}\n{council.body}"
        for literal in (
            "Review plan",
            "wf-review-plan",
            "Interrogate this plan",
            "Stress-test this plan",
            "Review wave",
            "wf-review-wave",
        ):
            self.assertIn(literal, council_contract)

    def test_first_full_render_migrates_prompt_before_emitting_review_plan_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._repo(root)
            old = root / ras.REVIEW_PLAN_OLD_PROMPT
            old.parent.mkdir(parents=True, exist_ok=True)
            old.write_text(
                "\n".join(
                    old_line
                    for _label, old_line, _new_line in ras.REVIEW_PLAN_LEGACY_CONTRACT_LINES
                )
                + "\n\nProject extension survives.\n",
                encoding="utf-8",
            )

            written = ras.render_agent_surfaces(root)
            self.assertIn(ras.REVIEW_PLAN_OLD_PROMPT, written)
            self.assertIn(ras.REVIEW_PLAN_NEW_PROMPT, written)
            self.assertFalse(old.exists())
            migrated = (root / ras.REVIEW_PLAN_NEW_PROMPT).read_text(encoding="utf-8")
            self.assertIn("current wave record when no change is specified", migrated)
            self.assertIn("before or after plan admission", migrated)
            self.assertIn("Project extension survives.", migrated)
            for host in (".codex", ".claude", ".agents"):
                skill = root / host / "skills" / "wf-review-plan" / "SKILL.md"
                self.assertTrue(skill.is_file())
                skill_text = skill.read_text(encoding="utf-8")
                self.assertIn("docs/prompts/review-plan.prompt.md", skill_text)
                self.assertIn("current wave record", skill_text)
                self.assertIn("before or after admission", skill_text)

    def test_self_hosted_review_plan_skills_match_registry_bytes(self) -> None:
        root = TESTS_ROOT.parents[2].parent
        review_plan = next(
            skill for skill in ras.SKILL_REGISTRY if skill.name == "wf-review-plan"
        )
        expected = ras.skill_document(review_plan).encode("utf-8")
        for host in (".codex", ".claude", ".agents"):
            self.assertEqual(
                (root / host / "skills" / "wf-review-plan" / "SKILL.md").read_bytes(),
                expected,
            )
            self.assertFalse(
                (root / host / "skills" / "wf-interrogate-plan" / "SKILL.md").exists()
            )

    def test_render_skills_refuses_unprefixed_name(self) -> None:
        bad = ras.Skill(name="upgrade", description="d", body="b")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._repo(root)
            with patch.object(ras, "SKILL_REGISTRY", (bad,)):
                with self.assertRaises(RuntimeError):
                    ras.render_skills(root)

    def test_emits_every_skill_to_every_active_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._repo(root)
            written = ras.render_skills(root)
            for skill in ras.SKILL_REGISTRY:
                for host in (".codex", ".claude", ".agents"):
                    rel = f"{host}/skills/{skill.name}/SKILL.md"
                    self.assertIn(rel, written)
                    text = (root / rel).read_text(encoding="utf-8")
                    self.assertTrue(
                        text.startswith(f"---\nname: {skill.name}\ndescription: "),
                        rel,
                    )

    def test_guru_gate_and_host_dir_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._repo(root, guru=False, hosts=(".codex", ".claude"))
            ras.render_skills(root)
            self.assertFalse((root / ".codex" / "skills" / "wf-guru").exists())
            self.assertTrue((root / ".codex" / "skills" / "wf-upgrade" / "SKILL.md").is_file())
            self.assertTrue((root / ".claude" / "skills" / "wf-upgrade" / "SKILL.md").is_file())
            self.assertFalse((root / ".agents").exists(), "inactive host must gain no tree")

    def test_stale_pre_registry_paths_are_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._repo(root)
            old_flat = root / ".claude" / "skills" / "upgrade-wave.md"
            old_flat.parent.mkdir(parents=True)
            old_flat.write_text("old flat skill\n", encoding="utf-8")
            old_codex = root / ".codex" / "skills" / "auto-guru" / "SKILL.md"
            old_codex.parent.mkdir(parents=True)
            old_codex.write_text("old codex skill\n", encoding="utf-8")
            retired: list[Path] = []
            for host in (".codex", ".claude", ".agents"):
                path = root / host / "skills" / "wf-interrogate-plan" / "SKILL.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("retired plan-review skill\n", encoding="utf-8")
                retired.append(path)
            sibling = retired[0].parent / "operator-note.md"
            sibling.write_text("preserve me\n", encoding="utf-8")
            written = ras.render_skills(root)
            self.assertIn(".claude/skills/upgrade-wave.md", written)
            self.assertIn(".codex/skills/auto-guru/SKILL.md", written)
            self.assertFalse(old_flat.exists())
            self.assertFalse(old_codex.parent.exists(), "emptied per-skill dir removed")
            for path in retired:
                self.assertIn(path.relative_to(root).as_posix(), written)
                self.assertFalse(path.exists())
            self.assertTrue(retired[0].parent.is_dir(), "non-empty skill dir preserved")
            self.assertEqual(sibling.read_text(encoding="utf-8"), "preserve me\n")
            self.assertFalse(retired[1].parent.exists(), "empty Claude skill dir removed")
            self.assertFalse(retired[2].parent.exists(), "empty agents skill dir removed")
            for host in (".codex", ".claude", ".agents"):
                self.assertTrue(
                    (root / host / "skills" / "wf-review-plan" / "SKILL.md").is_file()
                )
            self.assertTrue((root / ".claude" / "skills" / "wf-upgrade" / "SKILL.md").is_file())
            self.assertTrue((root / ".codex" / "skills" / "wf-guru" / "SKILL.md").is_file())

    def test_doc_gate_polarity_both_directions(self) -> None:
        # Wave 1ve3a: the negative direction is the deliverable — a repo
        # without the backing prompt doc (every target repo today) must emit
        # neither doc-gated skill on any host.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._repo(root, gate_docs=True)
            ras.render_skills(root)
            for name in self._DOC_GATED:
                for host in (".codex", ".claude", ".agents"):
                    self.assertTrue(
                        (root / host / "skills" / name / "SKILL.md").is_file(),
                        f"{name} missing on {host} despite gate doc present",
                    )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._repo(root, gate_docs=False)
            ras.render_skills(root)
            for name in self._DOC_GATED:
                emitted = list(root.glob(f"*/skills/{name}"))
                self.assertEqual(
                    emitted, [], f"{name} emitted without its gate doc: {emitted}"
                )
            # Ungated lifecycle skills still emit in the same repo.
            self.assertTrue(
                (root / ".claude" / "skills" / "wf-upgrade" / "SKILL.md").is_file()
            )

    def test_doc_gated_entries_declare_their_backing_doc_as_gate(self) -> None:
        # The gate must point at the same doc the thin-pointer body names,
        # so the skill can never render where its pointer dangles.
        by_name = {skill.name: skill for skill in ras.SKILL_REGISTRY}
        for name, rel in self._DOC_GATED.items():
            skill = by_name[name]
            self.assertEqual(skill.requires_doc, rel)
            self.assertIn(rel, skill.body)
        self.assertEqual(by_name["wf-guru"].requires_doc, "docs/agents/guru.md")

    def test_stale_cleanup_refuses_symlink_escape(self) -> None:
        # Deletion containment: a legacy wrapper path symlinked outside the
        # repo must refuse loudly, never unlink through the escape.
        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            root = outer / "repo"
            outside = outer / "outside"
            self._repo(root)
            outside.mkdir()
            (outside / "SKILL.md").write_text("external sentinel\n", encoding="utf-8")
            legacy_dir = root / ".codex" / "skills" / "auto-guru"
            legacy_dir.parent.mkdir(parents=True, exist_ok=True)
            legacy_dir.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                ras.render_skills(root)
            self.assertEqual(
                (outside / "SKILL.md").read_text(encoding="utf-8"),
                "external sentinel\n",
            )

    def test_retired_plan_skill_cleanup_is_contained_to_each_declared_host_root(self) -> None:
        for polarity in (
            "declared-root",
            "same-root-parent",
            "in-repo-parent",
            "outside-parent",
            "final-file",
        ):
            with self.subTest(polarity=polarity), tempfile.TemporaryDirectory() as temp_dir:
                outer = Path(temp_dir)
                root = outer / "repo"
                self._repo(root)
                stale_dir = root / ".codex" / "skills" / "wf-interrogate-plan"
                stale_dir.parent.mkdir(parents=True, exist_ok=True)
                if polarity == "declared-root":
                    skills_root = root / ".codex" / "skills"
                    skills_root.rmdir()
                    target = root / "unrelated-host-tree"
                    target.mkdir()
                    sentinel = target / "wf-interrogate-plan" / "SKILL.md"
                    sentinel.parent.mkdir()
                    sentinel.write_text("declared-root sentinel\n", encoding="utf-8")
                    skills_root.symlink_to(target, target_is_directory=True)
                elif polarity == "same-root-parent":
                    target = stale_dir.parent / "operator-owned-skill"
                    target.mkdir()
                    sentinel = target / "SKILL.md"
                    sentinel.write_text("same-root sentinel\n", encoding="utf-8")
                    stale_dir.symlink_to(target, target_is_directory=True)
                elif polarity == "in-repo-parent":
                    target = root / "unrelated" / "borrowed-skill"
                    target.mkdir(parents=True)
                    sentinel = target / "SKILL.md"
                    sentinel.write_text("in-repo sentinel\n", encoding="utf-8")
                    stale_dir.symlink_to(target, target_is_directory=True)
                elif polarity == "outside-parent":
                    target = outer / "outside"
                    target.mkdir()
                    sentinel = target / "SKILL.md"
                    sentinel.write_text("outside sentinel\n", encoding="utf-8")
                    stale_dir.symlink_to(target, target_is_directory=True)
                else:
                    stale_dir.mkdir()
                    target = root / "unrelated" / "sentinel.md"
                    target.parent.mkdir(parents=True)
                    target.write_text("final sentinel\n", encoding="utf-8")
                    sentinel = target
                    (stale_dir / "SKILL.md").symlink_to(target)
                before = sentinel.read_bytes()
                with self.assertRaisesRegex(RuntimeError, "declared host skill root"):
                    ras.render_skills(root)
                self.assertEqual(sentinel.read_bytes(), before)
                self.assertFalse(
                    (
                        root
                        / ".codex"
                        / "skills"
                        / "wf-review-plan"
                        / "SKILL.md"
                    ).exists()
                )

    def test_thin_pointer_targets_exist_in_self_hosted_repo(self) -> None:
        # Wave 1p6lw AC-2/AC-6: every prompt doc a skill body points at must
        # resolve in the self-hosted tree (the thin-pointer contract's target).
        repo_root = TESTS_ROOT.parents[2].parent
        pattern = re.compile(r"docs/prompts/[a-z0-9-]+\.prompt\.md")
        for skill in ras.SKILL_REGISTRY:
            targets = set(pattern.findall(skill.body))
            if skill.name not in ("wf-guru",):
                self.assertTrue(targets, f"{skill.name} body names no prompt doc")
            for target in targets:
                self.assertTrue(
                    (repo_root / target).is_file(), f"{skill.name}: missing {target}"
                )

    def test_second_full_render_is_convergent(self) -> None:
        # The Codex wf-guru skill is also a review carrier: the reconcile pass
        # appends owned regions after the registry writes the template. The
        # registry grafts existing regions on re-render, so the second full
        # render must report zero written paths.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._repo(root)
            first = ras.render_agent_surfaces(root)
            self.assertTrue(first)
            self.assertEqual(ras.render_agent_surfaces(root), [])


class AutoGuruRoutingAnchorRegressionTests(unittest.TestCase):
    """Wave 1p3dk / 1p3hf (intent-based-auto-guru-routing) regression guard.

    The literal failure-mode example ``tell me about the way authentication works``
    is the load-bearing anchor for the auto-Guru routing examples table in
    `seed-050` and the rendered `AGENTS.md`. This test asserts the anchor's
    presence in both surfaces so a future seed edit, render, or refactor that
    accidentally drops the example fails loudly.

    The brittleness is intentional: this single phrase is the demonstrable
    failure case that motivated the table's existence. Any change that needs
    to rephrase the anchor should rephrase it in the same change as updating
    this test — the coupling enforces the documentation discipline.
    """

    # The phrase is the semantic anchor; casing is operator-driven (the original
    # user message was lowercase; rendered docs use sentence case). The test is
    # case-insensitive — the load-bearing element is the phrase, not the casing.
    FAILURE_MODE_ANCHOR = "tell me about the way authentication works"

    def _repo_root(self) -> Path:
        # TESTS_ROOT = .../.wavefoundry/framework/scripts/tests
        # parents[2] = .wavefoundry; .parent = repo root
        return TESTS_ROOT.parents[2].parent

    def _assertAnchorIn(self, text: str, surface_label: str, hint: str) -> None:
        """Case-insensitive contains check. Brittleness is intentional on the
        phrase itself; casing variation is acceptable."""
        self.assertIn(
            self.FAILURE_MODE_ANCHOR.lower(), text.lower(),
            f"{surface_label} must contain the failure-mode anchor "
            f"'{self.FAILURE_MODE_ANCHOR}' (case-insensitive) — {hint}",
        )

    def test_anchor_present_in_seed_050(self) -> None:
        seed_path = self._repo_root() / ".wavefoundry" / "framework" / "seeds" / "050-agent-entry-surface-bootstrap.prompt.md"
        self.assertTrue(seed_path.is_file(), f"missing {seed_path}")
        self._assertAnchorIn(
            seed_path.read_text(encoding="utf-8"),
            "seed-050",
            "see wave 1p3dk / 1p3hf rationale",
        )

    def test_anchor_present_in_seed_211(self) -> None:
        seed_path = self._repo_root() / ".wavefoundry" / "framework" / "seeds" / "211-guru.prompt.md"
        self.assertTrue(seed_path.is_file(), f"missing {seed_path}")
        self._assertAnchorIn(
            seed_path.read_text(encoding="utf-8"),
            "seed-211 (Guru role doc)",
            "mirror seed-050's failure-mode anchor per the AC-5 mirroring contract",
        )

    def test_anchor_present_in_rendered_agents_md(self) -> None:
        agents_md = self._repo_root() / "AGENTS.md"
        self.assertTrue(agents_md.is_file(), f"missing {agents_md}")
        self._assertAnchorIn(
            agents_md.read_text(encoding="utf-8"),
            "AGENTS.md",
            "the lead agent reads this surface before routing decisions",
        )

    def test_anchor_in_examples_table_context(self) -> None:
        """The anchor must appear inside an examples table marked as
        anchoring-not-rule. Guards against the table being dropped while the
        anchor survives in unrelated prose."""
        agents_md = self._repo_root() / "AGENTS.md"
        text = agents_md.read_text(encoding="utf-8")
        lines = text.splitlines()
        anchor_lower = self.FAILURE_MODE_ANCHOR.lower()
        anchor_line_idx = next(
            (i for i, line in enumerate(lines) if anchor_lower in line.lower()),
            -1,
        )
        self.assertGreaterEqual(anchor_line_idx, 0, "anchor missing entirely")
        window = "\n".join(lines[max(0, anchor_line_idx - 20):anchor_line_idx + 20])
        self.assertIn("Route to Guru?", window,
            "anchor must appear within the examples-table context (Route to Guru? column header expected nearby)")
        self.assertIn("anchoring", window.lower(),
            "table must be framed as 'anchoring examples for an intent rule, not the rule itself' — "
            "guards against the table becoming a keyword-match list")


class AgentSurfaceNewlineTests(unittest.TestCase):
    """Wave 1p9ix (F14) — render_agent_surfaces.write_text must write embedded
    line terminators VERBATIM (newline="") so the freshly generated agent surfaces
    are byte-identical LF on every host, matching render_platform_surfaces.write_text.
    """

    # The freshly generated agent surfaces this renderer owns.
    _GENERATED_SURFACES = (
        (".cursor", "rules", "auto-guru.mdc"),
        (".claude", "agents", "guru.md"),
        (".codex", "skills", "wf-guru", "SKILL.md"),
        (".codex", "skills", "wf-upgrade", "SKILL.md"),
    )

    def _make_repo(self, repo_root: Path) -> None:
        (repo_root / "docs" / "agents").mkdir(parents=True)
        (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
        (repo_root / ".cursor" / "rules").mkdir(parents=True)
        (repo_root / ".claude" / "agents").mkdir(parents=True)
        (repo_root / ".codex").mkdir()

    def test_write_text_uses_newline_empty_and_writes_verbatim(self) -> None:
        # Durable, host-independent guard: capture the newline kwarg passed to
        # Path.open. The old `path.write_text(content, encoding="utf-8")` never
        # passes newline="" (it uses the default newline=None, which translates
        # every "\n" -> os.linesep on native Windows), so this fails on a revert
        # on ANY host, not only on Windows.
        real_open = Path.open
        captured: dict[str, object] = {}

        def spy_open(self, *args, **kwargs):  # noqa: ANN001
            captured["newline"] = kwargs.get("newline", "<absent>")
            return real_open(self, *args, **kwargs)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "surface.txt"
            with patch.object(Path, "open", spy_open):
                ras.write_text(target, "line-1\nline-2\nline-3\n")
            self.assertEqual(
                captured.get("newline"), "",
                "write_text must open with newline='' so embedded \\n are written verbatim",
            )
            raw = target.read_bytes()
            self.assertNotIn(b"\r\n", raw, "written bytes must be LF-only")
            self.assertEqual(target.read_text(encoding="utf-8"), "line-1\nline-2\nline-3\n")

    def test_rendered_agent_surfaces_are_lf_only(self) -> None:
        # Render the four generated surfaces and assert their bytes contain no
        # \r\n (LF-only) regardless of os.linesep on the rendering host.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            written = ras.render_agent_surfaces(repo_root)
            self.assertTrue(written, "render should produce surfaces when guru.md is present")
            for parts in self._GENERATED_SURFACES:
                surface = repo_root.joinpath(*parts)
                self.assertTrue(surface.is_file(), f"missing generated surface {surface}")
                raw = surface.read_bytes()
                self.assertNotIn(
                    b"\r\n", raw,
                    f"{'/'.join(parts)} must be written LF-only (no CRLF)",
                )


class CodexConfigOverwriteSafetyTests(unittest.TestCase):
    """Wave 1p9pe (1p9p7-bug renderer-overwrite-safety): the `.codex/config.toml`
    write must upsert only the framework-managed marker region and preserve all
    operator-authored TOML byte-for-byte. Pre-fix, `write_text(codex_mcp_config,
    CODEX_MCP_CONFIG_TOML)` clobbered the file on every render — this deleted a
    committed operator `wf_close_wave` approval guardrail twice (waves 1p9j0/1p9qm).
    """

    OPERATOR_BLOCK = (
        "[mcp_servers.wavefoundry.tools.wf_close_wave]\n"
        'approval_mode = "approve"\n'
    )

    # This repo's exact pre-migration on-disk shape (AC-7): the unmarked
    # framework table at lines 1-3 plus the restored operator block at 5-6.
    THIS_REPO_PREMIGRATION_SHAPE = (
        "[mcp_servers.wavefoundry]\n"
        'command = "python3"\n'
        'args = [".wavefoundry/framework/scripts/server.py"]\n'
        "\n"
        "[mcp_servers.wavefoundry.tools.wf_close_wave]\n"
        'approval_mode = "approve"\n'
    )

    def _make_repo(self, repo_root: Path) -> None:
        (repo_root / "docs" / "agents").mkdir(parents=True)
        (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")

    def _config_path(self, repo_root: Path) -> Path:
        return repo_root / ".codex" / "config.toml"

    def _render(self, repo_root: Path) -> None:
        ras.render_agent_surfaces(repo_root)
        rps.render_codex_mcp_config(repo_root)

    def _parse(self, text: str) -> dict:
        import tomllib

        return tomllib.loads(text)

    def test_create_if_missing_renders_marked_framework_region(self) -> None:
        # AC-3: a fresh repo with no .codex/config.toml gets the file created
        # containing the framework-managed region, and it parses as TOML.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            self._render(repo_root)
            text = self._config_path(repo_root).read_text(encoding="utf-8")
            self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, text)
            self.assertIn(ras.CODEX_CONFIG_MARKER_END, text)
            parsed = self._parse(text)
            self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")
            self.assertEqual(
                parsed["mcp_servers"]["wavefoundry"]["args"],
                [".wavefoundry/framework/scripts/server.py"],
            )

    def test_rerender_preserves_operator_block_byte_for_byte(self) -> None:
        # AC-1: an operator-added block outside the marker region survives a
        # re-render byte-for-byte while the framework region stays current.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            self._render(repo_root)
            config = self._config_path(repo_root)
            seeded = config.read_text(encoding="utf-8") + "\n" + self.OPERATOR_BLOCK
            config.write_text(seeded, encoding="utf-8")

            self._render(repo_root)

            text = config.read_text(encoding="utf-8")
            self.assertIn(self.OPERATOR_BLOCK, text, "operator block must survive re-render")
            self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, text)
            parsed = self._parse(text)
            self.assertEqual(
                parsed["mcp_servers"]["wavefoundry"]["tools"]["wf_close_wave"]["approval_mode"],
                "approve",
            )
            self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")

    def test_double_render_is_idempotent(self) -> None:
        # AC-2: two consecutive renders produce identical bytes — with and
        # without operator content present.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            config = self._config_path(repo_root)

            self._render(repo_root)
            first = config.read_bytes()
            self._render(repo_root)
            self.assertEqual(first, config.read_bytes(), "fresh double-render must be byte-identical")

            config.write_text(
                config.read_text(encoding="utf-8") + "\n" + self.OPERATOR_BLOCK,
                encoding="utf-8",
            )
            self._render(repo_root)
            second = config.read_bytes()
            self._render(repo_root)
            self.assertEqual(second, config.read_bytes(), "double-render with operator content must be byte-identical")

    def test_stale_framework_region_is_refreshed(self) -> None:
        # Requirement 1: the framework-managed command/args are kept CURRENT —
        # a stale marked region is rewritten to the canonical template.
        stale = (
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python-old"\n'
            'args = ["old/server.py"]\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
            "\n" + self.OPERATOR_BLOCK
        )
        result = ras.upsert_codex_mcp_config(stale)
        self.assertNotIn("python-old", result)
        self.assertIn('command = "python3"', result)
        self.assertIn(self.OPERATOR_BLOCK, result)

    def test_legacy_marker_namespace_migrates_without_duplicate_table(self) -> None:
        existing = (
            ras.CODEX_CONFIG_MARKER_BEGIN.replace(
                "# wave:", "# waveframework:"
            )
            + "\n"
            + ras.CODEX_MCP_CONFIG_TOML.rstrip()
            + "\n"
            + ras.CODEX_CONFIG_MARKER_END.replace(
                "# wave:", "# waveframework:"
            )
            + "\n"
        )
        result = ras.upsert_codex_mcp_config(existing)
        self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, result)
        self.assertNotIn("waveframework:codex-mcp", result)
        self.assertEqual(result.count("[mcp_servers.wavefoundry]"), 1)

    def test_absorbs_unmarked_framework_table_this_repos_shape(self) -> None:
        # AC-7: migration absorption + TOML validity, seeded with this repo's
        # exact pre-migration on-disk shape. The first marked render must
        # absorb the unmarked framework table into the managed region (never
        # duplicate it) and the result must parse as valid TOML.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            config = self._config_path(repo_root)
            config.parent.mkdir(parents=True)
            config.write_text(self.THIS_REPO_PREMIGRATION_SHAPE, encoding="utf-8")

            self._render(repo_root)

            text = config.read_text(encoding="utf-8")
            header_lines = [
                line for line in text.splitlines() if line.strip() == "[mcp_servers.wavefoundry]"
            ]
            self.assertEqual(
                len(header_lines), 1,
                "the unmarked framework table must be ABSORBED, not duplicated",
            )
            self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, text)
            self.assertIn(self.OPERATOR_BLOCK, text, "operator block must survive migration byte-for-byte")
            parsed = self._parse(text)  # tomllib round-trip: raises on duplicate tables
            self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")
            self.assertEqual(
                parsed["mcp_servers"]["wavefoundry"]["tools"]["wf_close_wave"]["approval_mode"],
                "approve",
            )

            # The migration is one-time: the next render is byte-identical.
            migrated = config.read_bytes()
            ras.render_agent_surfaces(repo_root)
            self.assertEqual(migrated, config.read_bytes())

    def test_unrelated_operator_server_table_survives(self) -> None:
        # Requirement 1: unrelated [mcp_servers.*] tables are operator content.
        operator_table = '[mcp_servers.other]\ncommand = "deno"\n'
        result = ras.upsert_codex_mcp_config(
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
            "\n" + operator_table
        )
        self.assertIn(operator_table, result)
        parsed = self._parse(result)
        self.assertEqual(parsed["mcp_servers"]["other"]["command"], "deno")
        self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")

    def test_operator_key_inside_framework_table_survives_migration(self) -> None:
        # An operator-added key trailing the framework command/args stays in
        # the [mcp_servers.wavefoundry] table (markers are TOML comments).
        result = ras.upsert_codex_mcp_config(
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
            "startup_timeout_ms = 20000\n"
        )
        parsed = self._parse(result)
        self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["startup_timeout_ms"], 20000)
        self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")

    def test_unparseable_merge_leaves_existing_untouched(self) -> None:
        # Fail-safe: if absorption would produce invalid TOML (here: a shape
        # the absorber cannot merge without duplicating `command`), the
        # existing operator config is returned unchanged rather than corrupted.
        odd_shape = (
            "[mcp_servers.wavefoundry]\n"
            "# operator comment blocks absorption of the lines below\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
        )
        self.assertEqual(ras.upsert_codex_mcp_config(odd_shape), odd_shape)


class CodexConfigUpsertHardeningTests(unittest.TestCase):
    """Wave 1p9pe review-fix lane: `upsert_codex_mcp_config` hardening.

    Convergent findings from the red-team/code/architecture/security review
    streams: (a) single-exit tomllib validation — every mutating branch's
    candidate is parse-validated, and any failure returns the existing content
    unchanged; (b) the unmarked-table migration accepts TOML-equivalent header
    spellings (quoted keys, whitespace) so they migrate instead of duplicating;
    (c) a bracket-count desync from an unbalanced bracket inside a string
    fail-safes instead of silently absorbing operator content to EOF (the one
    corruption tomllib validation cannot catch, because the result parses);
    (d) fail-safe is loud — stderr warning naming the file — and the path is
    NOT reported in `written`.
    """

    OPERATOR_BLOCK = (
        "[mcp_servers.wavefoundry.tools.wf_close_wave]\n"
        'approval_mode = "approve"\n'
    )

    def _parse(self, text: str) -> dict:
        import tomllib

        return tomllib.loads(text)

    def _upsert(self, existing: str) -> tuple[str, list[str]]:
        reasons: list[str] = []
        result = ras.upsert_codex_mcp_config(existing, on_fail_safe=reasons.append)
        return result, reasons

    def test_quoted_header_spelling_migrates_not_duplicates(self) -> None:
        # Pre-fix the quoted spelling missed the exact-match header scan and
        # fell to the append branch, WRITING a duplicate-table file tomllib
        # rejects. It must migrate exactly like the plain spelling.
        existing = (
            '[mcp_servers."wavefoundry"]\n'
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
            "\n" + self.OPERATOR_BLOCK
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [], "quoted header must migrate, not fail-safe")
        headers = [
            line for line in result.splitlines()
            if line.strip().startswith("[") and "wavefoundry]" in line.replace('"', "").replace(" ", "")
        ]
        self.assertEqual(
            [h for h in headers if "tools" not in h],
            ["[mcp_servers.wavefoundry]"],
            "exactly one (canonical) framework table header after migration",
        )
        self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, result)
        self.assertIn(self.OPERATOR_BLOCK, result)
        parsed = self._parse(result)  # raises on a duplicate table
        self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")

    def test_whitespace_header_variant_migrates(self) -> None:
        existing = (
            "[ mcp_servers.wavefoundry ]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [])
        self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, result)
        self.assertNotIn("[ mcp_servers.wavefoundry ]", result)
        self._parse(result)

    def test_dotted_key_form_fails_safe_not_corrupt(self) -> None:
        # Dotted-key assignments define the table without a header line; the
        # append branch would re-declare it (invalid TOML). Must fail-safe.
        existing = (
            'mcp_servers.wavefoundry.command = "python3"\n'
            'mcp_servers.wavefoundry.args = ["x"]\n'
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "dotted-key config must be left untouched")
        self.assertEqual(len(reasons), 1)
        self._parse(result)  # still the operator's valid file

    def test_marker_text_inside_operator_string_fails_safe(self) -> None:
        # Marker text embedded in an operator string value must not select the
        # region-replace branch (pre-fix the substring check sliced through
        # the string). The valid file is left untouched.
        existing = (
            "[mcp_servers.other]\n"
            f'note = "{ras.CODEX_CONFIG_MARKER_BEGIN} and {ras.CODEX_CONFIG_MARKER_END}"\n'
            'command = "deno"\n'
        )
        self._parse(existing)  # precondition: the operator file is valid
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "file with marker text in a string must be untouched")
        self.assertEqual(len(reasons), 1)

    def test_unbalanced_bracket_in_string_operator_subtable_survives(self) -> None:
        # The one silent-loss shape: an unbalanced "[" inside a string desyncs
        # the bracket counter, and pre-fix the absorber ate everything to EOF
        # — dropping the operator subtable while producing VALID TOML (so the
        # tomllib guard alone cannot catch it). Must fail-safe instead.
        existing = (
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py", "--flag["]\n'
            "\n" + self.OPERATOR_BLOCK
        )
        self._parse(existing)  # precondition: valid operator file
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "desynced absorption must fail-safe, not eat to EOF")
        self.assertIn(self.OPERATOR_BLOCK, result, "operator subtable must survive")
        self.assertEqual(len(reasons), 1)
        self.assertIn("bracket", reasons[0])

    def test_oversized_value_continuation_fails_safe(self) -> None:
        # The continuation-line cap: a value run longer than the small
        # constant is treated as a desync even if brackets eventually balance.
        filler = "".join(f'"pad-{i}",\n' for i in range(ras._CODEX_ABSORB_MAX_VALUE_LINES + 2))
        existing = (
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            "args = [\n" + filler + "]\n"
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing)
        self.assertEqual(len(reasons), 1)
        self.assertIn("continuation", reasons[0])

    def test_marked_region_replace_ignores_marker_text_in_string(self) -> None:
        # A real marked region plus an operator string that ALSO contains
        # marker text: the line-anchored match must replace only the real
        # region and preserve the operator string byte-for-byte.
        fresh = ras.upsert_codex_mcp_config(None)
        operator_tail = (
            "\n[mcp_servers.other]\n"
            f'note = "{ras.CODEX_CONFIG_MARKER_END}"\n'
        )
        existing = fresh + operator_tail
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [])
        self.assertEqual(result, existing, "re-render must be idempotent and keep the string")
        self._parse(result)

    def test_fail_safe_render_warns_and_omits_written(self) -> None:
        # End-to-end (fix d): a fail-safe merge during render_agent_surfaces
        # emits a stderr warning naming the file and does NOT report the path
        # in the returned written list; the file bytes are untouched.
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            config = repo_root / ".codex" / "config.toml"
            config.parent.mkdir(parents=True)
            fail_safe_shape = (
                'mcp_servers.wavefoundry.command = "python3"\n'
                'mcp_servers.wavefoundry.args = ["x"]\n'
            )
            config.write_text(fail_safe_shape, encoding="utf-8")

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                ras.render_agent_surfaces(repo_root)
                rps._manifest_start()
                rps.render_codex_mcp_config(repo_root)
                written = list(rps._MANIFEST_WRITTEN or [])

            self.assertNotIn(
                ".codex/config.toml", written,
                "a fail-safe (unchanged) file must not be reported as written",
            )
            warning = stderr.getvalue()
            self.assertIn("config.toml", warning, "fail-safe must warn loudly on stderr")
            self.assertIn("fail-safe", warning)
            self.assertEqual(
                config.read_text(encoding="utf-8"), fail_safe_shape,
                "the operator file must be byte-for-byte untouched",
            )

    def test_successful_render_still_reports_config_written(self) -> None:
        # Guard the inverse: the normal path still reports the path.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            ras.render_agent_surfaces(repo_root)
            rps._manifest_start()
            rps.render_codex_mcp_config(repo_root)
            config = repo_root / ".codex" / "config.toml"
            self.assertIn(
                config.resolve(),
                [Path(path).resolve() for path in (rps._MANIFEST_WRITTEN or [])],
            )


class CodexConfigCouncilFixNowTests(unittest.TestCase):
    """Wave 1p9pe delivery-council fix-now lane: `upsert_codex_mcp_config`.

    (1) Security seat S-NEW-1: a triple-quoted (multiline) operator string
    whose body reproduces BOTH marker comment lines as whole physical lines
    matched the line-anchored region regex; the replace branch sliced the
    string, silently dropped operator content, and the sliced result still
    parsed — the tomllib guard was blind. Empirically proven pre-fix.
    (2) QA seat: the marker-replace branch's own tomllib exit was untested.
    (3) Rotating seat: semantic tomllib-equivalence exit guard — after
    normalizing framework-owned differences, existing and candidate parsed
    docs must be EQUAL, structurally closing valid-TOML content-loss shapes
    (e.g. a balanced-bracket absorption desync) the parse check cannot flag.
    (4) Rotating seat: CRLF-rewritten marker regions now match (region
    refresh) instead of perpetually fail-safing with a stale block.
    """

    OPERATOR_BLOCK = (
        "[mcp_servers.wavefoundry.tools.wf_close_wave]\n"
        'approval_mode = "approve"\n'
    )

    def _upsert(self, existing: str) -> tuple[str, list[str]]:
        reasons: list[str] = []
        result = ras.upsert_codex_mcp_config(existing, on_fail_safe=reasons.append)
        return result, reasons

    def _parse(self, text: str) -> dict:
        import tomllib

        return tomllib.loads(text)

    def test_multiline_string_reproducing_both_marker_lines_fails_safe(self) -> None:
        # S-NEW-1 probe B: triple-quoted operator string containing both
        # marker lines as whole physical lines + a real unmarked framework
        # table below. Pre-fix: the region replace sliced the string, dropped
        # the operator's blob content (including `command = "evil"`), and the
        # result STILL PARSED. Must fail-safe with the string-embedding reason.
        existing = (
            "[mcp_servers.other]\n"
            'blob = """\n'
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            'command = "evil"\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
            '"""\n'
            "\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
        )
        self._parse(existing)  # precondition: the operator file is valid TOML
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "string-embedded marker lines must fail-safe untouched")
        self.assertEqual(len(reasons), 1)
        self.assertIn("multiline operator string", reasons[0])

    def test_single_line_marker_string_with_real_region_still_upserts(self) -> None:
        # No-false-positive guard: this repo's on-disk shape (marked region +
        # operator tools subtable) plus an operator SINGLE-LINE string that
        # mentions one marker line. Single-line strings cannot line-anchor the
        # region regex, so the normal replace path must run: the stale region
        # is refreshed and every operator byte outside it survives.
        operator_tail = (
            "\n" + self.OPERATOR_BLOCK
            + "\n[mcp_servers.other]\n"
            f'note = "{ras.CODEX_CONFIG_MARKER_END}"\n'
        )
        existing = (
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python-old"\n'
            'args = ["old/server.py"]\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
            + operator_tail
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [], "single-line marker mention must not fail-safe")
        self.assertNotIn("python-old", result, "stale framework region must be refreshed")
        self.assertIn('command = "python3"', result)
        self.assertIn(operator_tail, result, "operator content incl. the marker string survives")
        self._parse(result)

    def test_region_replace_duplicate_operator_table_hits_tomllib_exit(self) -> None:
        # QA seat: the marker-REPLACE branch flowing into the tomllib single
        # exit was untested. A well-formed marked region plus an operator-owned
        # duplicate [mcp_servers.wavefoundry] table outside it: the existing
        # content already does not parse (duplicate table), so the parsed-
        # baseline guards are skipped and the region replace runs; the
        # candidate is still duplicate-table TOML, so the tomllib exit must
        # fail-safe with the existing content unchanged. No marker text in any
        # string value — this shape exercises the parse exit specifically.
        existing = (
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
            "\n"
            "[mcp_servers.wavefoundry]\n"
            "startup_timeout_ms = 20000\n"
        )
        with self.assertRaises(Exception):
            self._parse(existing)  # precondition: duplicate table, unparseable
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "unparseable replace result must leave existing untouched")
        self.assertEqual(len(reasons), 1)
        self.assertIn("parse", reasons[0])

    def test_balanced_bracket_desync_caught_by_semantic_equivalence_guard(self) -> None:
        # Rotating seat: brackets inside string values can desync the
        # absorption counter and RETURN TO ZERO, evading both the depth
        # fail-safe and the continuation cap — pre-fix the absorber ate the
        # operator table to EOF and the result parsed cleanly. Only the
        # semantic-equivalence exit guard catches this shape.
        existing = (
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = ["x", "--open[["]\n'
            "\n"
            "[mcp_servers.other]\n"
            'key = "]]close"\n'
        )
        self._parse(existing)  # precondition: valid operator file
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "balanced-bracket desync must fail-safe, not eat to EOF")
        self.assertIn("[mcp_servers.other]", result, "operator table must survive")
        self.assertEqual(len(reasons), 1)
        self.assertIn("operator-owned parsed content", reasons[0])

    def test_normalized_doc_equivalence_tolerances(self) -> None:
        # Unit coverage of the equivalence helper: framework-owned differences
        # (command/args refresh; wavefoundry-table creation) are tolerated;
        # any operator-owned difference is not.
        norm = ras._codex_normalized_doc
        base = {"mcp_servers": {"wavefoundry": {"command": "python-old", "args": ["old"]}}}
        refreshed = {"mcp_servers": {"wavefoundry": {"command": "python3", "args": ["new"]}}}
        self.assertEqual(norm(base), norm(refreshed), "command/args refresh must be equivalent")

        self.assertEqual(
            norm({}), norm(refreshed),
            "creating the wavefoundry table (and mcp_servers parent) must be equivalent",
        )
        with_other = {"mcp_servers": {"other": {"command": "deno"}}}
        with_other_and_fw = {
            "mcp_servers": {"other": {"command": "deno"}, "wavefoundry": {"command": "python3"}}
        }
        self.assertEqual(norm(with_other), norm(with_other_and_fw))

        operator_changed = {"mcp_servers": {"other": {"command": "node"}, "wavefoundry": {"command": "python3"}}}
        self.assertNotEqual(
            norm(with_other_and_fw), norm(operator_changed),
            "an operator key change must NOT be equivalent",
        )

        with_subtable = {
            "mcp_servers": {"wavefoundry": {"command": "python3", "tools": {"wf_close_wave": {"approval_mode": "approve"}}}}
        }
        dropped_subtable = {"mcp_servers": {"wavefoundry": {"command": "python3"}}}
        self.assertNotEqual(
            norm(with_subtable), norm(dropped_subtable),
            "dropping an operator subtable must NOT be equivalent",
        )

    def test_crlf_marker_region_is_replaced_not_fail_safed(self) -> None:
        # Rotating seat: a CRLF-rewritten config (editor/tooling re-encoded)
        # must still match its marker region — region refreshed, operator CRLF
        # content outside the region preserved byte-for-byte — instead of
        # perpetually fail-safing with a stale framework block.
        stale_region = (
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python-old"\n'
            'args = ["old/server.py"]\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
        )
        operator_tail = '\n[mcp_servers.other]\ncommand = "deno"\n'
        existing = (stale_region + operator_tail).replace("\n", "\r\n")
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [], "CRLF marker region must be matched, not fail-safed")
        self.assertNotIn("python-old", result, "stale framework region must be refreshed")
        self.assertIn(
            operator_tail.replace("\n", "\r\n"), result,
            "operator CRLF content outside the region survives byte-for-byte",
        )
        self._parse(result)


class GuruWrapperModelPolicyTests(unittest.TestCase):
    """Use the complete producer, including both carrier reconciliation passes."""

    def _root(self, directory: str, *, guru: bool = True) -> tuple[Path, Path]:
        root = Path(directory)
        if guru:
            role = root / "docs/agents/guru.md"
            role.parent.mkdir(parents=True)
            role.write_text(GURU_STUB, encoding="utf-8")
        wrapper = root / ".claude/agents/guru.md"
        wrapper.parent.mkdir(parents=True)
        return root, wrapper

    def _assert_neutral_fresh_render(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, wrapper = self._root(directory)
            first_written = ras.render_agent_surfaces(root)
            first = wrapper.read_bytes()
            header = first.decode().split("---", 2)[1]
            self.assertIn(".claude/agents/guru.md", first_written)
            self.assertNotRegex(header, r"(?m)^(?:model|effort):")
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN.encode(), first)
            self.assertNotIn(".claude/agents/guru.md", ras.render_agent_surfaces(root))
            self.assertEqual(first, wrapper.read_bytes())

    def test_fresh_wrapper_omits_preferences_and_is_stable(self) -> None:
        self._assert_neutral_fresh_render()

    def test_seed_050_claude_guru_example_omits_preferences(self) -> None:
        seed = (PROJECT_ROOT / "framework/seeds/050-agent-entry-surface-bootstrap.prompt.md").read_text(encoding="utf-8")
        blocks = re.findall(r"(?m)^---\nname: guru\n.*?^---", seed, re.DOTALL)
        self.assertTrue(blocks, "must inspect the actual seed's Guru header")
        for header in blocks:
            self.assertNotRegex(header, r"(?m)^(?:model|effort):")

    def _assert_preserved_render(self, model: str = "sonnet", effort: str = "high", newline: str = "\n", bom: str = "") -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, wrapper = self._root(directory)
            header = bom + (
                "---\nname: local-guru\ndescription: Local description\n"
                "tools: Read, mcp__wavefoundry__code_read\n"
                f"model: {model}\neffort: {effort}\n"
                "# Operator comment\npermissionMode: plan\ncustom:\n  nested: [one, two]\n---\n"
            ).replace("\n", newline)
            wrapper.write_bytes((header + newline + "Old generated body" + newline).encode())
            ras.render_agent_surfaces(root)
            first = wrapper.read_bytes()
            self.assertTrue(first.startswith(header.encode()), "all existing frontmatter bytes must survive")
            self.assertIn(b"## Your job", first, "the generated body must actually refresh")
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN.encode(), first)
            self.assertNotIn(b"Old generated body", first)
            self.assertNotIn(".claude/agents/guru.md", ras.render_agent_surfaces(root))
            self.assertEqual(first, wrapper.read_bytes())

    def test_existing_choices_and_unrelated_header_survive(self) -> None:
        for model, effort in (("sonnet", "high"), ("inherit", "medium"), ("future/provider-v7", "future-effort"), ('"future: model"', "'high' # chosen")):
            for newline in ("\n", "\r\n"):
                with self.subTest(model=model, effort=effort, newline=repr(newline)):
                    self._assert_preserved_render(model, effort, newline)
        self._assert_preserved_render(newline="\r\n", bom="\ufeff")

    def test_malformed_header_stays_byte_identical_across_entire_render(self) -> None:
        headers = (
            "\ufeff---\nmodel: sonnet\nmodel: inherit\n---\n",
            "---\nname: guru\nmodel: sonnet\n",  # no close
            "---\nmodel: sonnet\nmodel: inherit\n---\n",
            "---\neffort: high\neffort: low\n---\n",
            "---\nmodel: sonnet\n'model': inherit\n---\n",
            "---\nmodel: [sonnet]\n---\n",
            "---\neffort: {value: high}\n---\n",
            "---\nmodel:\n  - sonnet\n---\n",
            "---\nmodel: |\n  sonnet\n---\n",
            "---\nmodel: sonnet\n  continuation\n---\n",
            "---\nmodel: \"unclosed\n---\n",
            "---\n model: sonnet\n model: inherit\n---\n",
            "---\n effort: [high]\n---\n",
        )
        for header in headers:
            for guru in (True, False):
                for protocol in ("", f"\n{ras.REVIEW_PROTOCOL_MARKER_BEGIN}\nstale\n{ras.REVIEW_PROTOCOL_MARKER_END}\n"):
                    with self.subTest(header=header, guru=guru, protocol=bool(protocol)), tempfile.TemporaryDirectory() as directory:
                        root, wrapper = self._root(directory, guru=guru)
                        original = (header + "\n# Existing body\n" + protocol).replace("\n", "\r\n").encode()
                        wrapper.write_bytes(original)
                        for _ in range(2):
                            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                                written = ras.render_agent_surfaces(root)
                            self.assertIn("render_agent_surfaces: WARNING", stderr.getvalue())
                            self.assertNotIn(".claude/agents/guru.md", written)
                            self.assertEqual(original, wrapper.read_bytes())

    def test_controls_kill_reintroduced_default_and_unconditional_overwrite(self) -> None:
        self._assert_neutral_fresh_render()
        self._assert_preserved_render()
        token = "name: guru\n"
        self.assertEqual(ras.CLAUDE_GURU_AGENT.count(token), 1)
        mutant = ras.CLAUDE_GURU_AGENT.replace(token, token + "model: sonnet\n")
        with patch.object(ras, "CLAUDE_GURU_AGENT", mutant):
            with self.assertRaises(AssertionError):
                self._assert_neutral_fresh_render()
        # Restore the old unconditional template write at the real write
        # chokepoint, leaving both reconciliation passes running normally.
        original_write = ras.write_text

        def overwrite(path, content):
            if path.as_posix().endswith("/.claude/agents/guru.md"):
                content = ras.CLAUDE_GURU_AGENT
            return original_write(path, content)

        with patch.object(ras, "write_text", side_effect=overwrite):
            with self.assertRaises(AssertionError):
                self._assert_preserved_render()

    def test_control_kills_missing_whole_render_frontmatter_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, wrapper = self._root(directory, guru=False)
            original = b"---\nmodel: [sonnet]\n---\n\nExisting body\n"
            wrapper.write_bytes(original)
            with patch("sys.stderr", new_callable=io.StringIO):
                ras.render_agent_surfaces(root)
            self.assertEqual(original, wrapper.read_bytes(), "unmutated producer must preserve bytes")
            with patch.object(ras, "_claude_agent_frontmatter", return_value=""):
                written = ras.render_agent_surfaces(root)
            self.assertIn(".claude/agents/guru.md", written)
            with self.assertRaises(AssertionError):
                self.assertEqual(original, wrapper.read_bytes())


class GuruWrapperToolAllowlistTests(unittest.TestCase):
    """Subagent MCP tool access — the rendered guru wrapper's frontmatter
    `tools:` allowlist must grant the read-only Wavefoundry retrieval tools its
    own body instructs it to use. An explicit allowlist is not additive in
    Claude Code, so omitting the MCP tools makes the wrapper self-contradictory
    (body says "call code_ask", frontmatter forbids it). Guards:
      1. the enumerated read-only retrieval grant (incl. ToolSearch for hosts
         that defer MCP schemas),
      2. no write-capable / lifecycle-mutating wave_* tool ever granted,
      3. frontmatter grants cover every MCP tool the wrapper body names.
    """

    # The read-only retrieval set the wrapper must grant. Exact tool names are
    # the fail-safe frontmatter form: honored -> precise read-only grant;
    # ignored by a host -> status quo (never a mutator exposure).
    _REQUIRED_GRANTS = {
        "ToolSearch",
        "mcp__wavefoundry__code_ask",
        "mcp__wavefoundry__code_search",
        "mcp__wavefoundry__code_keyword",
        "mcp__wavefoundry__code_read",
        "mcp__wavefoundry__code_outline",
        "mcp__wavefoundry__code_definition",
        "mcp__wavefoundry__code_references",
        "mcp__wavefoundry__code_callhierarchy",
        "mcp__wavefoundry__code_dependencies",
        "mcp__wavefoundry__code_impact",
        "mcp__wavefoundry__code_list_files",
        "mcp__wavefoundry__code_constants",
        "mcp__wavefoundry__code_pattern",
        "mcp__wavefoundry__code_callgraph",
        "mcp__wavefoundry__code_graph_path",
        "mcp__wavefoundry__code_graph_community",
        "mcp__wavefoundry__docs_search",
        "mcp__wavefoundry__seed_get",
    }

    def _rendered_guru(self) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            (repo_root / ".claude" / "agents").mkdir(parents=True)
            ras.render_agent_surfaces(repo_root)
            return (repo_root / ".claude" / "agents" / "guru.md").read_text(encoding="utf-8")

    @staticmethod
    def _tools_entries(rendered: str) -> list[str]:
        for line in rendered.splitlines():
            if line.startswith("tools:"):
                return [entry.strip() for entry in line[len("tools:"):].split(",") if entry.strip()]
        return []

    def test_required_readonly_grants_present(self) -> None:
        entries = set(self._tools_entries(self._rendered_guru()))
        missing = self._REQUIRED_GRANTS - entries
        self.assertFalse(
            missing,
            f"guru wrapper tools: allowlist is missing required read-only grants: {sorted(missing)}",
        )
        # The pre-fix baseline tools stay granted.
        for base in ("Read", "Grep", "Glob", "Bash"):
            self.assertIn(base, entries)

    def test_no_mutating_wave_tool_granted(self) -> None:
        entries = self._tools_entries(self._rendered_guru())
        offenders = [e for e in entries if e.startswith("mcp__wavefoundry__wave_")]
        self.assertEqual(
            offenders, [],
            "guru wrapper must never grant wave_* lifecycle/mutating tools",
        )
        # And never a bare server-level grant, which would include the mutators.
        self.assertNotIn("mcp__wavefoundry", entries)
        self.assertNotIn("mcp__wavefoundry__*", entries)

    def test_body_instructions_covered_by_grants(self) -> None:
        rendered = self._rendered_guru()
        entries = set(self._tools_entries(rendered))
        body = rendered.split("---", 2)[2] if rendered.count("---") >= 2 else rendered
        body_named = set(re.findall(r"`((?:code|docs)_[a-z_]+|seed_get|wave_[a-z_]+)`", body))
        body_named |= set(re.findall(r"`mcp__wavefoundry__([a-z_]+)`", body))
        self.assertTrue(body_named, "wrapper body should name its MCP tools")
        uncovered = {
            name for name in body_named
            if f"mcp__wavefoundry__{name}" not in entries
        }
        self.assertFalse(
            uncovered,
            "wrapper body instructs tools its frontmatter does not grant "
            f"(the self-contradiction this change fixes): {sorted(uncovered)}",
        )


class FreshCarrierAgentFrontmatterTests(unittest.TestCase):
    """Regression: fresh docs/agents/** carriers must satisfy the pack's own docs-lint.

    A 1.13.0 upgrade halted at the docs gate because newly-rendered specialist
    carriers lacked the `Role:`/`Category:` frontmatter the agent-metadata validator
    requires. These tests render carriers into a temp root that EXPOSES the real
    seeds (so rendering takes the seed-verbatim path, not the frontmatter-less
    title-minimum branch that would make the test vacuous) and assert the agent
    validators pass over the whole rendered `docs/agents/**` set.
    """

    def _render_fresh_root(self, repo_root: Path) -> None:
        import shutil

        seeds_dst = repo_root / ".wavefoundry" / "framework" / "seeds"
        seeds_dst.parent.mkdir(parents=True)
        shutil.copytree(PROJECT_ROOT / "framework" / "seeds", seeds_dst)
        ras.reconcile_review_protocol_surfaces(repo_root)

    def test_fresh_carriers_pass_the_pack_agent_metadata_validators(self) -> None:
        from wave_lint_lib.wave_validators import (
            _check_agent_category_metadata,
            _check_agent_role_metadata,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._render_fresh_root(repo_root)

            # The exact checks that blocked the upgrade — over the whole rendered set.
            self.assertEqual(_check_agent_role_metadata(repo_root), [])
            self.assertEqual(_check_agent_category_metadata(repo_root), [])

            specialists = repo_root / "docs" / "agents" / "specialists"

            # Requirement 1 (seed frontmatter): a single-destination specialist renders
            # seed-verbatim (proving the seeds dir was actually consulted) with Role/Category.
            red_team = (specialists / "red-team.md").read_text(encoding="utf-8")
            self.assertIn("# Agent Body — Red Team", red_team)  # seed body, not title-minimum
            self.assertIn("Role: red-team", red_team)
            self.assertIn("Category: specialist", red_team)

            # Requirement 2 (renderer fallback): seed 236 carries NO seed frontmatter, so
            # its specialist render gets Role/Category from the fallback — and its exempt
            # docs/prompts render must NOT be polluted with them.
            archetype = (specialists / "archetype-council.md").read_text(encoding="utf-8")
            self.assertIn("Role: archetype-council", archetype)
            self.assertIn("Category: specialist", archetype)
            prompt = (repo_root / "docs" / "prompts" / "archetype-council.prompt.md").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("Role: archetype-council", prompt)
            self.assertNotIn("Category: specialist", prompt)

            # Non-specialist derivation: a review-category carrier must get Category: review,
            # not specialist — this is why the fallback reuses _expected_agent_category.
            qa = (repo_root / "docs" / "agents" / "qa-reviewer.md").read_text(encoding="utf-8")
            self.assertIn("Role: qa-reviewer", qa)
            self.assertIn("Category: review", qa)

    def test_fallback_is_fresh_only_and_does_not_clobber_existing_frontmatter(self) -> None:
        # An existing (update-path) specialist doc with project-authored frontmatter must
        # be preserved verbatim outside the owned region — the fallback runs fresh-only.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target = repo_root / "docs" / "agents" / "specialists" / "red-team.md"
            target.parent.mkdir(parents=True)
            existing = "# Red Team\n\nRole: red-team\nCategory: specialist\n\n## Project note\n\n- keep me\n"
            target.write_text(existing, encoding="utf-8")

            ras.reconcile_review_protocol_surfaces(repo_root)

            text = target.read_text(encoding="utf-8")
            self.assertIn("## Project note", text)
            self.assertIn("- keep me", text)
            # Exactly one Role:/Category: each — no duplicate injection on the update path.
            self.assertEqual(text.count("Role: red-team"), 1)
            self.assertEqual(text.count("Category: specialist"), 1)


# ---------------------------------------------------------------------------
# Wave 1vj4e (1vj4d): Backstage catalog + TechDocs baseline command
# ---------------------------------------------------------------------------

_TECHDOCS_GOLDEN_CATALOG = """\
# wavefoundry: generated missing-only Backstage/TechDocs baseline; project-owned, edit freely.
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: example-project-docs
  title: example-project-docs Documentation
  description: Technical documentation for the example-project-docs project.
  annotations:
    backstage.io/techdocs-ref: dir:.
spec:
  type: documentation
  lifecycle: experimental
  owner: engineering
"""

_TECHDOCS_GOLDEN_MKDOCS = """\
# wavefoundry: generated missing-only Backstage/TechDocs baseline; project-owned, edit freely.
site_name: example-project-docs Documentation
site_description: Technical documentation for the example-project-docs project.
docs_dir: docs
plugins:
  - techdocs-core
nav:
  - Home: index.md
  - Project overview: references/project-overview.md
  - Architecture: ARCHITECTURE.md
  - Workflow and agent commands: prompts/index.md
exclude_docs: |
  /*
  !/index.md
  !/ARCHITECTURE.md
  !/architecture/
  !/architecture/**
  !/references/
  !/references/**
  !/prompts/
  /prompts/*
  !/prompts/index.md
"""

_TECHDOCS_GOLDEN_INDEX = """\
# example-project-docs Documentation

Owner: Engineering
Status: active
Last verified: 2026-08-18

<!-- wavefoundry: generated missing-only Backstage/TechDocs baseline; project-owned, edit freely. -->

Technical documentation for the `example-project-docs` project.

- [Project overview](references/project-overview.md)
- [Architecture](ARCHITECTURE.md)
- [Workflow and agent commands](prompts/index.md)
"""

_TECHDOCS_GOLDEN = {
    "catalog-info.yaml": _TECHDOCS_GOLDEN_CATALOG,
    "mkdocs.yml": _TECHDOCS_GOLDEN_MKDOCS,
    "docs/index.md": _TECHDOCS_GOLDEN_INDEX,
}
_TECHDOCS_TRIO = tuple(destination for destination, _t, _m in ras.TECHDOCS_BASELINES)
_TECHDOCS_MARKER_LINE = {destination: marker for destination, _t, marker in ras.TECHDOCS_BASELINES}


def _techdocs_repo(temp_dir: str, *, name: str = "Example_Project", targets: bool = True) -> Path:
    """A target root whose navigation targets exist (the command's precondition)."""

    root = (Path(temp_dir) / name).resolve()
    (root / "docs" / "references").mkdir(parents=True)
    (root / "docs" / "prompts").mkdir(parents=True)
    if targets:
        for target in ras.TECHDOCS_PRECONDITION_TARGETS:
            (root / target).write_text(f"# {target}\n", encoding="utf-8")
    return root


def _techdocs_render(root: Path):
    with patch.object(ras.time, "strftime", return_value="2026-08-18"):
        return ras.render_techdocs_baseline(root)


def _techdocs_snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


class TechdocsBaselineGoldenTests(unittest.TestCase):
    """AC-1: literal UTF-8/LF golden bytes, marker lines, one terminal newline; normalization vectors."""

    def test_all_absent_generates_the_literal_golden_trio(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _techdocs_repo(temp_dir)
            result = _techdocs_render(root)
            self.assertEqual(result.written_paths, _TECHDOCS_TRIO)
            self.assertEqual(result.preserved_paths, ())
            self.assertEqual(result.generated_paths, _TECHDOCS_TRIO)
            self.assertEqual(result.missing_targets, ())
            self.assertIsNone(result.partial)
            for destination, golden in _TECHDOCS_GOLDEN.items():
                raw = (root / destination).read_bytes()
                self.assertEqual(raw, golden.encode("utf-8"), destination)
                self.assertNotIn(b"\r", raw, destination)
                self.assertTrue(raw.endswith(b"\n") and not raw.endswith(b"\n\n"), destination)
                marker = _TECHDOCS_MARKER_LINE[destination]
                self.assertEqual(raw.decode("utf-8").count(marker), 1, destination)
            # The landing page's marker sits immediately after the metadata block.
            index_lines = _TECHDOCS_GOLDEN_INDEX.splitlines()
            self.assertEqual(index_lines[4], "Last verified: 2026-08-18")
            self.assertEqual(index_lines[6], _TECHDOCS_MARKER_LINE["docs/index.md"])
            # Templates on disk still hold the placeholders (substitution is per render).
            for _destination, template_name, _marker in ras.TECHDOCS_BASELINES:
                template = ras._resolve_install_asset(root, template_name)
                self.assertIn("{{entity_name}}", template.read_text(encoding="utf-8"), template_name)

    def test_templates_ship_under_names_no_discovery_glob_matches(self) -> None:
        # A literal catalog-info.yaml shipped into every target would be found by
        # Backstage `**/catalog-info.yaml` location globs and ingest a placeholder.
        install_dir = SCRIPTS_ROOT.parent / "install"
        for _destination, template_name, _marker in ras.TECHDOCS_BASELINES:
            self.assertIn(".template.", template_name)
            self.assertTrue((install_dir / template_name).is_file(), template_name)
        self.assertFalse((install_dir / "catalog-info.yaml").exists())
        self.assertFalse((install_dir / "mkdocs.yml").exists())

    def test_name_normalization_vectors(self) -> None:
        vectors = [
            ("My...__Repo", "my-repo-docs"),
            ("project-docs", "project-docs"),
            ("sample", "sample-docs"),
            ("\U0001f525", "project-docs"),
            ("", "project-docs"),
            ("a" * 58, ("a" * 58) + "-docs"),
            ("a" * 59, ("a" * 58) + "-docs"),
            (("a" * 57) + "-b", ("a" * 57) + "-docs"),
            ("Example_Project", "example-project-docs"),
        ]
        for raw, expected in vectors:
            with self.subTest(raw=raw):
                name = ras.techdocs_entity_name(raw)
                self.assertEqual(name, expected)
                self.assertLessEqual(len(name), 63)
                self.assertRegex(name, r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?-docs$")

    def test_entity_name_derives_from_the_resolved_root_basename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _techdocs_repo(temp_dir, name="Sample.Repo")
            _techdocs_render(root)
            text = (root / "catalog-info.yaml").read_text(encoding="utf-8")
            self.assertIn("  name: sample-repo-docs\n", text)


class TechdocsBaselineStateMatrixTests(unittest.TestCase):
    """AC-2: all 27 absent / present-unmarked / present-marked states from the single rule."""

    _UNMARKED = {
        "catalog-info.yaml": "apiVersion: backstage.io/v1alpha1\nkind: Component\nmetadata:\n  name: mine\n",
        "mkdocs.yml": "site_name: Mine\n",
        "docs/index.md": "# Mine\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-01-01\n",
    }

    @staticmethod
    def _marked(destination: str) -> str:
        # A marked pre-existing member from ANOTHER project: foreign content, our marker.
        marker = _TECHDOCS_MARKER_LINE[destination]
        if destination == "docs/index.md":
            return f"# Foreign\n\nOwner: X\nStatus: active\nLast verified: 2026-01-01\n\n{marker}\n\nforeign\n"
        return f"{marker}\nforeign: true\n"

    def _seed(self, root: Path, state: tuple) -> dict:
        before = {}
        for destination, member_state in zip(_TECHDOCS_TRIO, state):
            if member_state == "absent":
                continue
            content = self._UNMARKED[destination] if member_state == "unmarked" else self._marked(destination)
            path = root / destination
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
            before[destination] = path.read_bytes()
        return before

    def test_every_state_writes_absent_members_only_and_warns_iff_mixed(self) -> None:
        import itertools

        states = list(itertools.product(("absent", "unmarked", "marked"), repeat=3))
        self.assertEqual(len(states), 27)
        for state in states:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp_dir:
                root = _techdocs_repo(temp_dir)
                before = self._seed(root, state)
                absent = tuple(d for d, s in zip(_TECHDOCS_TRIO, state) if s == "absent")
                unmarked = [d for d, s in zip(_TECHDOCS_TRIO, state) if s == "unmarked"]
                marked = [d for d, s in zip(_TECHDOCS_TRIO, state) if s == "marked"]
                present = tuple(d for d, s in zip(_TECHDOCS_TRIO, state) if s != "absent")

                result = _techdocs_render(root)

                self.assertEqual(result.written_paths, absent)
                self.assertEqual(result.preserved_paths, present)
                self.assertEqual(result.missing_targets, ())
                expected_generated = tuple(d for d in _TECHDOCS_TRIO if d in marked or d in absent)
                self.assertEqual(result.generated_paths, expected_generated)
                for destination, raw in before.items():
                    self.assertEqual((root / destination).read_bytes(), raw, destination)
                for destination in absent:
                    self.assertEqual(
                        (root / destination).read_bytes(),
                        _TECHDOCS_GOLDEN[destination].encode("utf-8"),
                        destination,
                    )
                if unmarked and expected_generated:
                    self.assertIsNotNone(result.partial, state)
                    record = result.partial
                    self.assertEqual(record["channel"], "backstage-techdocs")
                    self.assertEqual(record["code"], "backstage_techdocs_partial")
                    self.assertEqual(record["preserved_paths"], unmarked)
                    self.assertEqual(record["generated_paths"], list(expected_generated))
                    expected_detail = ras.TECHDOCS_PARTIAL_WARNING.format(paths=", ".join(unmarked))
                    self.assertEqual(record["detail"], expected_detail)
                    self.assertTrue(record["detail"].startswith("Backstage/TechDocs baseline is partial; preserved project-owned files: "))
                    for word in ("success", "validated", "valid TechDocs", "verified"):
                        self.assertNotIn(word, record["detail"].lower())
                else:
                    self.assertIsNone(result.partial, state)

                # Recomputation: the read-only classifier agrees, before and after a rerun,
                # and the rerun is byte-idempotent and writes nothing.
                classified = ras.classify_techdocs_baseline(root)
                self.assertEqual(classified, result.partial)
                snapshot = {d: (root / d).read_bytes() for d in _TECHDOCS_TRIO}
                rerun = _techdocs_render(root)
                self.assertEqual(rerun.written_paths, ())
                self.assertEqual(rerun.preserved_paths, _TECHDOCS_TRIO)
                self.assertEqual(rerun.generated_paths, expected_generated)
                self.assertEqual(rerun.partial, result.partial)
                self.assertEqual({d: (root / d).read_bytes() for d in _TECHDOCS_TRIO}, snapshot)
                self.assertEqual(ras.classify_techdocs_baseline(root), result.partial)

    def test_warning_names_unmarked_paths_in_canonical_order_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _techdocs_repo(temp_dir)
            self._seed(root, ("unmarked", "absent", "unmarked"))
            result = _techdocs_render(root)
            self.assertEqual(result.partial["preserved_paths"], ["catalog-info.yaml", "docs/index.md"])
            self.assertIn("preserved project-owned files: catalog-info.yaml, docs/index.md.", result.partial["detail"])
            self.assertEqual(result.partial["detail"].count("Backstage/TechDocs baseline is partial"), 1)


class TechdocsBaselineClassifierTests(unittest.TestCase):
    """AC-2 tolerance: BOM/CRLF/prepended header/edited-but-marked stay generated; unmarked,
    wrong-form, undecodable, non-regular, and escaping members are project-owned."""

    def _classify(self, root: Path, destination: str, raw: bytes) -> bool:
        path = root / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return ras.techdocs_member_is_generated(path, _TECHDOCS_MARKER_LINE[destination])

    def test_bom_on_a_yaml_member_with_the_marker_on_line_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = b"\xef\xbb\xbf" + _TECHDOCS_GOLDEN_CATALOG.encode("utf-8")
            self.assertTrue(self._classify(root, "catalog-info.yaml", raw))
            # Control: a first-line-only, non-sig reader would fail this fixture.
            first_line = raw.split(b"\n", 1)[0].decode("utf-8")
            self.assertNotEqual(first_line, _TECHDOCS_MARKER_LINE["catalog-info.yaml"])

    def test_crlf_marked_member_is_generated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raw = _TECHDOCS_GOLDEN_MKDOCS.replace("\n", "\r\n").encode("utf-8")
            self.assertTrue(self._classify(Path(temp_dir), "mkdocs.yml", raw))

    def test_prepended_header_and_user_edits_keep_the_landing_page_generated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prepended = ("<!-- editor header -->\n\n" + _TECHDOCS_GOLDEN_INDEX).encode("utf-8")
            self.assertTrue(self._classify(root, "docs/index.md", prepended))
            edited = (_TECHDOCS_GOLDEN_INDEX + "\n## Added by a user\n\nStill marked.\n").encode("utf-8")
            self.assertTrue(self._classify(root, "docs/index.md", edited))

    def test_unmarked_and_wrong_form_members_are_project_owned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            unmarked = _TECHDOCS_GOLDEN_INDEX.replace(_TECHDOCS_MARKER_LINE["docs/index.md"] + "\n\n", "")
            self.assertNotIn("wavefoundry:", unmarked)
            self.assertFalse(self._classify(root, "docs/index.md", unmarked.encode("utf-8")))
            # docs/index.md carrying only the YAML `#` form is project-owned...
            yaml_form = _TECHDOCS_GOLDEN_INDEX.replace(
                _TECHDOCS_MARKER_LINE["docs/index.md"], _TECHDOCS_MARKER_LINE["catalog-info.yaml"]
            )
            self.assertFalse(self._classify(root, "docs/index.md", yaml_form.encode("utf-8")))
            # ...and its mirror: a YAML member carrying only the HTML-comment form.
            html_form = _TECHDOCS_GOLDEN_CATALOG.replace(
                _TECHDOCS_MARKER_LINE["catalog-info.yaml"], _TECHDOCS_MARKER_LINE["docs/index.md"]
            )
            self.assertFalse(self._classify(root, "catalog-info.yaml", html_form.encode("utf-8")))

    def test_undecodable_non_regular_and_escaping_members_are_project_owned_and_never_raise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _techdocs_repo(temp_dir)
            # Undecodable bytes around the marker: project-owned, no exception.
            raw = b"\xff\xfe" + _TECHDOCS_GOLDEN_MKDOCS.encode("utf-8")
            self.assertFalse(self._classify(root, "mkdocs.yml", raw))
            (root / "mkdocs.yml").unlink()
            # A directory at a destination and an escaping symlink at another:
            # both project-owned in the read-only classifier, which never raises
            # and never reads outside the root.
            (root / "mkdocs.yml").mkdir()
            outside = Path(temp_dir) / "outside.yaml"
            outside.write_text(_TECHDOCS_GOLDEN_CATALOG, encoding="utf-8")
            (root / "catalog-info.yaml").symlink_to(outside)
            (root / "docs" / "index.md").write_text(_TECHDOCS_GOLDEN_INDEX, encoding="utf-8")
            record = ras.classify_techdocs_baseline(root)
            self.assertEqual(record["preserved_paths"], ["catalog-info.yaml", "mkdocs.yml"])
            self.assertEqual(record["generated_paths"], ["docs/index.md"])
            # Absent members are in neither list; a fully absent trio is None.
            (root / "docs" / "index.md").unlink()
            (root / "mkdocs.yml").rmdir()
            (root / "catalog-info.yaml").unlink()
            self.assertIsNone(ras.classify_techdocs_baseline(root))


class TechdocsBaselinePreconditionAndPathTests(unittest.TestCase):
    """AC-3 precondition and negative render/setup/upgrade paths; AC-4 containment."""

    def test_precondition_failure_writes_nothing_and_names_missing_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _techdocs_repo(temp_dir, targets=False)
            before = _techdocs_snapshot(root)
            result = _techdocs_render(root)
            self.assertEqual(result.missing_targets, ras.TECHDOCS_PRECONDITION_TARGETS)
            self.assertEqual(result.written_paths, ())
            self.assertIsNone(result.partial)
            self.assertEqual(_techdocs_snapshot(root), before)
            for destination in _TECHDOCS_TRIO:
                self.assertFalse((root / destination).exists(), destination)
            # One missing target names exactly that one.
            for target in ras.TECHDOCS_PRECONDITION_TARGETS[:-1]:
                (root / target).write_text("# t\n", encoding="utf-8")
            result = _techdocs_render(root)
            self.assertEqual(result.missing_targets, (ras.TECHDOCS_PRECONDITION_TARGETS[-1],))
            self.assertEqual(result.written_paths, ())

    def test_render_setup_and_upgrade_paths_never_write_the_trio(self) -> None:
        # Non-vacuous: the fixture satisfies the precondition, and the positive
        # control at the end proves the command itself writes all three here.
        import os
        import setup_wavefoundry
        import venv_bootstrap
        from test_upgrade_wavefoundry import load_upgrade_module

        with tempfile.TemporaryDirectory() as temp_dir:
            root = _techdocs_repo(temp_dir)
            (root / ".claude").mkdir()
            (root / "docs" / "agents").mkdir(parents=True)
            (root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")

            ras.render_agent_surfaces(root)
            for destination in _TECHDOCS_TRIO:
                self.assertFalse((root / destination).exists(), f"render pass wrote {destination}")

            env = {**os.environ, "WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}
            # The exact argv setup Step 1 and upgrade Phase 1 spawn.
            result = subprocess.run(
                [sys.executable, str(PLATFORM_RENDER_SCRIPT), "--repo-root", str(root), "--include-permissions"],
                cwd=str(PROJECT_ROOT), text=True, capture_output=True, check=False, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for destination in _TECHDOCS_TRIO:
                self.assertFalse((root / destination).exists(), f"render_platform_surfaces wrote {destination}")

            with patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False):
                self.assertEqual(setup_wavefoundry._run_render_platform_surfaces(root), 0)
            for destination in _TECHDOCS_TRIO:
                self.assertFalse((root / destination).exists(), f"setup Step 1 wrote {destination}")

            upgrade = load_upgrade_module()
            with patch.object(upgrade, "_preferred_python", return_value=sys.executable), \
                 patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False):
                upgrade.phase_surface_rendering(root)
            for destination in _TECHDOCS_TRIO:
                self.assertFalse((root / destination).exists(), f"upgrade Phase 1 wrote {destination}")

            # Positive control.
            control = _techdocs_render(root)
            self.assertEqual(control.written_paths, _TECHDOCS_TRIO)

    def test_only_the_two_declared_entries_call_the_command_function(self) -> None:
        # Static guard for the negative test: no other framework script (setup,
        # upgrade, render_platform_surfaces) calls render_techdocs_baseline. The
        # allowlist is exactly the two entry points that share the one function:
        # the CLI thin entry and the MCP tool in techdocs_handlers (1vj4d Requirement 10,
        # widened deliberately when the MCP tool was added).
        # rglob, not glob: a call site added under a subpackage (wave_lint_lib/,
        # for example) must not slip past this guard. Tests are excluded because
        # they exercise the function on purpose.
        callers = []
        for path in sorted(SCRIPTS_ROOT.rglob("*.py")):
            if path.name in {"render_agent_surfaces.py", "techdocs_baseline.py", "techdocs_handlers.py"}:
                continue
            if "tests" in path.relative_to(SCRIPTS_ROOT).parts:
                continue
            if "render_techdocs_baseline(" in path.read_text(encoding="utf-8"):
                callers.append(path.name)
        self.assertEqual(callers, [])
        self.assertIn("render_techdocs_baseline(", (SCRIPTS_ROOT / "techdocs_baseline.py").read_text(encoding="utf-8"))
        self.assertIn("render_techdocs_baseline(", (SCRIPTS_ROOT / "techdocs_handlers.py").read_text(encoding="utf-8"))
        # And the render pass itself has no call site.
        import inspect

        self.assertNotIn("render_techdocs_baseline", inspect.getsource(ras.render_agent_surfaces))
        self.assertNotIn("techdocs_baseline", inspect.getsource(ras.preflight_agent_surface_paths))

    def test_generated_landing_page_is_lint_clean_with_targets_present(self) -> None:
        from wave_lint_lib.link_validators import check_markdown_links
        from wave_lint_lib.metadata_validators import check_metadata

        with tempfile.TemporaryDirectory() as temp_dir:
            root = _techdocs_repo(temp_dir)
            _techdocs_render(root)
            page = root / "docs" / "index.md"
            self.assertEqual(check_metadata(root, page), [])
            self.assertEqual(check_markdown_links(root, page), [])
            # Control: without the targets the same page has exactly three broken links,
            # which is why the precondition exists.
            for target in ras.TECHDOCS_PRECONDITION_TARGETS:
                (root / target).unlink()
            self.assertEqual(len(check_markdown_links(root, page)), 3)

    def test_in_root_symlink_to_a_regular_file_is_present_and_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _techdocs_repo(temp_dir)
            real = root / "docs" / "site.yml"
            real.write_text("site_name: Mine\n", encoding="utf-8")
            (root / "mkdocs.yml").symlink_to(Path("docs") / "site.yml")
            result = _techdocs_render(root)
            self.assertEqual(result.written_paths, ("catalog-info.yaml", "docs/index.md"))
            self.assertEqual(result.preserved_paths, ("mkdocs.yml",))
            self.assertTrue((root / "mkdocs.yml").is_symlink())
            self.assertEqual(real.read_bytes(), b"site_name: Mine\n")
            self.assertEqual(result.partial["preserved_paths"], ["mkdocs.yml"])

    def test_non_regular_or_escaping_destinations_are_refused_before_any_write(self) -> None:
        import os
        import stat as stat_module

        cases = {
            "escaping symlink": ("catalog-info.yaml", "escape"),
            "directory": ("docs/index.md", "dir"),
            "dangling symlink": ("mkdocs.yml", "dangling"),
            "symlink to a directory": ("mkdocs.yml", "dirlink"),
        }
        if hasattr(os, "mkfifo"):
            cases["fifo"] = ("catalog-info.yaml", "fifo")
        for label, (destination, kind) in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as temp_dir:
                root = _techdocs_repo(temp_dir)
                outside = Path(temp_dir) / "outside.txt"
                outside.write_text("sentinel\n", encoding="utf-8")
                target = root / destination
                if kind == "escape":
                    target.symlink_to(outside)
                elif kind == "dir":
                    target.mkdir()
                elif kind == "dangling":
                    target.symlink_to(Path("docs") / "nowhere.yml")
                elif kind == "dirlink":
                    target.symlink_to(Path("docs"))
                else:
                    os.mkfifo(target)
                before = {d: (root / d).exists() or (root / d).is_symlink() for d in _TECHDOCS_TRIO}
                with self.assertRaises(RuntimeError):
                    _techdocs_render(root)
                # Nothing written: every trio path is exactly as before, the sentinel untouched.
                for d in _TECHDOCS_TRIO:
                    self.assertEqual((root / d).exists() or (root / d).is_symlink(), before[d], (label, d))
                    if not before[d]:
                        self.assertFalse((root / d).exists(), (label, d))
                self.assertEqual(outside.read_text(encoding="utf-8"), "sentinel\n")
                if kind == "dir":
                    self.assertTrue(stat_module.S_ISDIR(target.lstat().st_mode))

    def test_refusal_on_the_third_destination_blocks_the_first_two(self) -> None:
        # Classification runs for all three destinations before the first write.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _techdocs_repo(temp_dir)
            (root / "docs" / "index.md").mkdir()
            with self.assertRaises(RuntimeError):
                _techdocs_render(root)
            self.assertFalse((root / "catalog-info.yaml").exists())
            self.assertFalse((root / "mkdocs.yml").exists())

    def test_exclusive_write_refuses_to_truncate_an_existing_member(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "catalog-info.yaml"
            path.write_text("mine\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                ras._write_review_carrier_text(path, "generated\n", exclusive=True)
            self.assertEqual(path.read_text(encoding="utf-8"), "mine\n")
            # The default (sibling families) still truncates in place.
            ras._write_review_carrier_text(path, "generated\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "generated\n")


class TechdocsExcludeDocsOracleTests(unittest.TestCase):
    """AC-5: a stdlib ordered-pattern oracle over the golden `exclude_docs` block, pinned to
    the MkDocs/pathspec outcomes recorded in the 1vj4d Decision Log (2026-08-18)."""

    SURVIVORS = (
        "index.md",
        "ARCHITECTURE.md",
        "architecture/current-state.md",
        "architecture/deep/nested.md",
        "references/project-overview.md",
        "references/install-assets.md",
        "prompts/index.md",
    )
    REJECTS = (
        "README.md",
        "SECURITY.md",
        "agents/guru.md",
        "agents/session-handoff.md",
        "agents/memory/x.md",
        "prompts/plan-feature.prompt.md",
        "prompts/prompt-surface-manifest.json",
        "plans/1abc-x.md",
        "waves/1vj4e x/wave.md",
        "reports/foo.md",
        "workflow-config.json",
        "repo-profile.json",
        "scans/secrets.json",
        "unknown-root.md",
        "unknown/dir/file.md",
        "prompts/sub/index.md",
    )

    @staticmethod
    def _exclude_block(text: str) -> list[str]:
        lines = text.splitlines()
        start = lines.index("exclude_docs: |") + 1
        block = []
        for line in lines[start:]:
            if not line.startswith("  "):
                break
            block.append(line[2:])
        return block

    @staticmethod
    def _pattern_regex(pattern: str) -> "re.Pattern[str]":
        # gitignore subset used by the golden block, per-file semantics as MkDocs
        # applies them (`GitIgnoreSpec.match_file(src_uri)`): a leading `/` anchors
        # at the docs root; `*` never crosses `/`; `**` crosses; a trailing `/`
        # names a directory and everything under it; a plain path also matches
        # everything under it.
        anchored = pattern.startswith("/")
        body = pattern[1:] if anchored else pattern
        directory_only = body.endswith("/")
        body = body.rstrip("/")
        parts = []
        for segment in body.split("/"):
            if segment == "**":
                parts.append(".*")
            else:
                parts.append(re.escape(segment).replace(r"\*", "[^/]*"))
        core = "/".join(parts)
        core = core.replace("/.*/", "(?:/.*/|/)").replace("/.*", "(?:/.*)?")
        prefix = "^" if anchored else "^(?:.*/)?"
        suffix = "/.*$" if directory_only else "(?:/.*)?$"
        return re.compile(prefix + core + suffix)

    @classmethod
    def _excluded(cls, block: list[str], path: str) -> bool:
        excluded = False
        for line in block:
            negate = line.startswith("!")
            pattern = line[1:] if negate else line
            if cls._pattern_regex(pattern).match(path):
                excluded = not negate
        return excluded

    def _golden_block(self) -> list[str]:
        return self._exclude_block(_TECHDOCS_GOLDEN_MKDOCS)

    def test_golden_block_matches_the_change_doc_and_the_template(self) -> None:
        template = (SCRIPTS_ROOT.parent / "install" / "mkdocs.template.yml").read_text(encoding="utf-8")
        self.assertEqual(self._exclude_block(template), self._golden_block())
        self.assertEqual(
            self._golden_block(),
            ["/*", "!/index.md", "!/ARCHITECTURE.md", "!/architecture/", "!/architecture/**",
             "!/references/", "!/references/**", "!/prompts/", "/prompts/*", "!/prompts/index.md"],
        )
        for key in ("site_name: example-project-docs Documentation",
                    "site_description: Technical documentation for the example-project-docs project.",
                    "docs_dir: docs", "  - techdocs-core",
                    "  - Home: index.md", "  - Project overview: references/project-overview.md",
                    "  - Architecture: ARCHITECTURE.md", "  - Workflow and agent commands: prompts/index.md"):
            self.assertIn(key, _TECHDOCS_GOLDEN_MKDOCS)

    def test_survivors_and_rejects_pinned_to_the_recorded_outcomes(self) -> None:
        block = self._golden_block()
        for path in self.SURVIVORS:
            self.assertFalse(self._excluded(block, path), path)
        for path in self.REJECTS:
            self.assertTrue(self._excluded(block, path), path)

    def test_removed_pattern_mutants_fail_the_oracle(self) -> None:
        block = self._golden_block()
        without_index = [line for line in block if line != "!/prompts/index.md"]
        self.assertTrue(self._excluded(without_index, "prompts/index.md"), "survivor must be rejected by the mutant")
        without_prompt_deny = [line for line in block if line != "/prompts/*"]
        self.assertFalse(self._excluded(without_prompt_deny, "prompts/plan-feature.prompt.md"), "prompt body admitted by the mutant")
        # Both mutants still agree with the golden on the other side, so the failure is specific.
        self.assertFalse(self._excluded(without_index, "index.md"))
        self.assertTrue(self._excluded(without_prompt_deny, "README.md"))


class TechdocsCarrierLiteralPinTests(unittest.TestCase):
    """Wave 1vj4e: literal pins for the seed/doc carriers of 1vj4d AC-6 and 1vmpz AC-1/AC-4/AC-5."""

    SEEDS = SCRIPTS_ROOT.parent / "seeds"
    REVIEW_BRANCH_HEADING = "## Read-only procedure (review branch)"

    def _read(self, rel: str) -> str:
        return (PROJECT_ROOT.parent / rel).read_text(encoding="utf-8")

    def test_seed_178_carries_the_workflow_boundary_and_checklist(self) -> None:
        text = (self.SEEDS / "178-refresh-techdocs.prompt.md").read_text(encoding="utf-8")
        for literal in (
            "- `Refresh TechDocs`", "- `Author TechDocs`",
            "### Step 1: baseline (`wf_techdocs_baseline`, CLI `wf techdocs-baseline`)",
            # The citation-form rule and its Step 3 re-resolve are the whole mechanism
            # that keeps a published page's locators true (delivery finding DEL-4);
            # without these pins either clause could be deleted with the suite green.
            "Prefer the symbol form",
            "recompute every such range against the final tree at Step 3",
            "after all other edits in this session are complete",
            "still covers the fact it is cited for",
            "### Step 2: collaboration (the technical-writer coordinates)",
            "### Step 3: validation",
            "**Audience invariant.**", "**Link boundary.**", "**Ownership.**",
            "### Recording boundary", "never treat a `run` event as evidence",
            "## Operator follow-up checklist (canonical)",
            "Wavefoundry does not render or preview the downstream site.",
            "Rendering and publication are owned by the operator's chosen Backstage/CI environment",
            "`repo_url` / `edit_uri`",
            "Mark the row `[~]`",
            "removing the generated-by line from the trio's root members",
        ):
            self.assertIn(literal, text, literal)
        self.assertNotIn("techdocs_baseline.py", text)

    def test_techdocs_carriers_pin_boundary_remediation_semantics(self) -> None:
        surfaces = (
            ("seed-178", (self.SEEDS / "178-refresh-techdocs.prompt.md").read_text(encoding="utf-8")),
            ("docs/prompts/refresh-techdocs.prompt.md", self._read("docs/prompts/refresh-techdocs.prompt.md")),
        )
        replacements = {
            "Removing a page from `nav` changes discoverability only":
                "Removing a page from `nav` removes it from publication",
            "Adding `repo_url` does not rewrite Markdown links":
                "Adding `repo_url` rewrites Markdown links",
            "direct-file matches take precedence over ancestor-directory matches":
                "ancestor-directory matches take precedence over direct-file matches",
            "the last matching rule wins within each tier":
                "the first matching rule wins within each tier",
            "a directory negation does not necessarily override a direct-file exclusion":
                "a directory negation always overrides a direct-file exclusion",
        }

        def contract_holds(text: str) -> bool:
            return all(clause in text for clause in replacements)

        for label, text in surfaces:
            with self.subTest(surface=label, contract="literal-and-semantic"):
                self.assertTrue(contract_holds(text), label)
                self.assertNotIn("the `nav` entries plus the paths that survive", text, label)
                self.assertNotIn("through `repo_url` when the operator has configured it", text, label)
            for clause, known_bad in replacements.items():
                with self.subTest(surface=label, mutant=clause):
                    mutant = text.replace(clause, known_bad, 1)
                    self.assertNotEqual(mutant, text, f"vacuous mutant: {label}: {clause}")
                    self.assertFalse(contract_holds(mutant), f"surviving mutant: {label}: {clause}")

    def test_upgrade_carriers_pin_merge_safe_project_prompt_reconciliation(self) -> None:
        surfaces = (
            ("seed-160", (self.SEEDS / "160-upgrade-wavefoundry.prompt.md").read_text(encoding="utf-8")),
            ("docs/prompts/upgrade-wavefoundry.prompt.md", self._read("docs/prompts/upgrade-wavefoundry.prompt.md")),
        )
        replacements = {
            "Keep the read-only pre-apply seed diff through the installing run":
                "Discard the pre-apply seed diff after preview",
            "If it reports `178-refresh-techdocs.prompt.md` changed":
                "Ignore whether `178-refresh-techdocs.prompt.md` changed",
            "during the same installing run": "during a later upgrade",
            "Preserve project-only additions and metadata":
                "Discard project-only additions and metadata",
            "never replace the project-owned prompt as a whole":
                "replace the project-owned prompt as a whole",
            "cannot be identified uniquely": "can be selected by best effort",
            "local wording conflicts with the new invariant":
                "local wording conflicts may be overwritten",
            "After the merge, run `wf render-surfaces` again":
                "After the merge, skip the final `wf render-surfaces` pass",
        }
        mapping_contracts = {
            "**Storage recovery guidance in existing upgrade prompts (seed 160).**": {
                "On every upgrade, including same-version retries":
                    "Only when the release version changes",
                "even when the pre-apply diff reports no seed change":
                    "skip when the pre-apply diff reports no seed change",
                "freshly extracted `160-upgrade-wavefoundry.prompt.md`":
                    "previously installed `160-upgrade-wavefoundry.prompt.md`",
                "existing `docs/prompts/upgrade-wavefoundry.prompt.md`":
                    "existing `docs/prompts/install-wavefoundry.prompt.md`",
                "during the same installing run": "during a later upgrade",
                "restart checkpoint and retained CLI continuation": "restart as an upgrade failure",
                "`--rebuild-storage` and its MCP-before-pause/CLI-after-pause boundary":
                    "reconnect MCP to rebuild after the pause",
                "package identity and receipt prohibitions": "receipt editing escape hatches",
                "publication/verification gate before cleanup": "cleanup before verification",
                "Preserve project-only additions, metadata and all renderer-owned marker regions":
                    "Discard project-only additions, metadata and renderer-owned marker regions",
                "merge only missing or stale storage guidance outside those regions":
                    "replace prose inside managed regions",
                "never replace the project-owned prompt as a whole":
                    "replace the project-owned prompt as a whole",
                "If no prior storage section exists": "Ignore a missing storage section",
                "add a single section at an unambiguous location":
                    "append a duplicate section on every retry",
                "already-current guidance remains unchanged": "always rewrite current guidance",
                "old clause or insertion location cannot be identified uniquely":
                    "old clauses may be selected by best effort",
                "local wording conflicts with the new contract":
                    "local wording conflicts may be overwritten",
                "stop and present the conflict to the operator": "guess and continue",
                "Re-run `wf render-surfaces` and the docs gate after the merge":
                    "Skip rendering and docs validation after the merge",
            },
            "**Changed Prepare Serialization Points carrier.**": {
                "`170-plan-feature.prompt.md` changed":
                    "`170-plan-feature.prompt.md` was unchanged",
                "freshly extracted `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md`":
                    "pre-upgrade lifecycle baseline",
                "merge only that grammar": "replace the entire prompt",
                "project-authored prose of `docs/prompts/prepare-wave.prompt.md`":
                    "renderer-owned region of `docs/prompts/prepare-wave.prompt.md`",
                "Preserve its metadata, all other project prose, and every renderer-owned marker region":
                    "Discard its metadata, project prose, and renderer-owned marker regions",
                "final `wf render-surfaces` pass remains responsible for those managed regions":
                    "manual reconciliation remains responsible for managed regions",
                "Never replace the carrier as a whole":
                    "Replace the carrier as a whole",
                "prior project-authored clause cannot be identified uniquely":
                    "prior project-authored clause may be selected by best effort",
                "local wording conflicts with the new grammar":
                    "local wording conflicts may be overwritten",
            },
            "**Changed contribution-workflow carrier.**": {
                "seeds `170` or `190` changed": "seeds `170` and `190` were unchanged",
                "AC-locality and advisory-sensor clauses":
                    "unrelated workflow clauses",
                "`docs/contributing/change-workflow.md`":
                    "`docs/contributing/review-and-evals.md`",
                "Preserve project-only content and metadata":
                    "Discard project-only content and metadata",
                "never replace the carrier as a whole":
                    "replace the carrier as a whole",
                "prior canonical clause cannot be identified uniquely":
                    "prior canonical clause may be selected by best effort",
                "local wording conflicts with the new contract":
                    "local wording conflicts may be overwritten",
            },
        }

        def contract_holds(text: str) -> bool:
            return all(clause in text for clause in replacements)

        for label, text in surfaces:
            techdocs_line = next(
                (
                    line
                    for line in text.splitlines()
                    if line.lstrip().startswith(
                        "- **Changed Refresh TechDocs instructions (seed 178).**"
                    )
                ),
                None,
            )
            with self.subTest(surface=label, contract="literal-and-semantic"):
                self.assertIsNotNone(techdocs_line, label)
                assert techdocs_line is not None
                self.assertTrue(contract_holds(techdocs_line), label)
                for literal in (
                    "seeds `170`, `180`, `190`, `209`, `214`, `221`, or `239` changed",
                    "docs/prompts/implement-wave.prompt.md",
                    "docs/agents/wave-coordinator.md",
                    "Review Artifact Discipline",
                    "preserve historical review artifacts",
                ):
                    self.assertIn(literal, text, f"{label}: {literal}")
            for clause, known_bad in replacements.items():
                with self.subTest(surface=label, mutant=clause):
                    mutant = techdocs_line.replace(clause, known_bad, 1)
                    self.assertNotEqual(mutant, techdocs_line, f"vacuous mutant: {label}: {clause}")
                    self.assertFalse(contract_holds(mutant), f"surviving mutant: {label}: {clause}")
            for heading, clauses in mapping_contracts.items():
                with self.subTest(surface=label, mapping=heading):
                    mapping_line = next(
                        (
                            line
                            for line in text.splitlines()
                            if line.lstrip().startswith(f"- {heading}")
                        ),
                        None,
                    )
                    self.assertIsNotNone(mapping_line, f"{label}: {heading}")
                    assert mapping_line is not None
                    self.assertTrue(
                        all(clause in mapping_line for clause in clauses),
                        f"{label}: incomplete mapping {heading}",
                    )
                if mapping_line is None:
                    continue  # The missing-mapping assertion already failed.
                for clause, known_bad in clauses.items():
                    with self.subTest(surface=label, mapping=heading, mutant=clause):
                        mutant = mapping_line.replace(clause, known_bad, 1)
                        self.assertNotEqual(
                            mutant,
                            mapping_line,
                            f"vacuous mapping mutant: {label}: {heading}: {clause}",
                        )
                        self.assertFalse(
                            all(required in mutant for required in clauses),
                            f"surviving mapping mutant: {label}: {heading}: {clause}",
                        )

    def test_techdocs_carriers_keep_python_validation_and_no_render_boundary(self) -> None:
        refresh_surfaces = (
            ("seed-178", (self.SEEDS / "178-refresh-techdocs.prompt.md").read_text(encoding="utf-8")),
            ("docs/prompts/refresh-techdocs.prompt.md", self._read("docs/prompts/refresh-techdocs.prompt.md")),
        )
        install_surfaces = (
            ("seed-012", (self.SEEDS / "012-install-wavefoundry-phase-2.prompt.md").read_text(encoding="utf-8")),
            ("docs/prompts/install-wavefoundry.prompt.md", self._read("docs/prompts/install-wavefoundry.prompt.md")),
        )
        for label, text in refresh_surfaces:
            with self.subTest(surface=label, contract="required-validation"):
                for literal in (
                    "These required checks stay inside Wavefoundry's declared Python tool environment",
                    "Run full docs validation",
                    "Confirm every `nav` target in `mkdocs.yml` exists",
                    "Run the publication audit",
                    "Re-resolve every `path:start-end` citation",
                    "Report what was written, what each supplier verified",
                    "An unavailable external renderer is neither a finding nor a degraded lane",
                ):
                    self.assertIn(literal, text, f"{label}: {literal}")
        for label, text in (*refresh_surfaces, *install_surfaces):
            with self.subTest(surface=label, contract="no-render"):
                self.assertIn("does not render or preview the downstream site", text, label)
                self.assertIn(
                    "rendering and publication are owned by the operator's chosen backstage/ci environment",
                    text.lower(),
                    label,
                )
                lowered = text.lower()
                for forbidden in (
                    "npx ",
                    "@techdocs/cli",
                    "techdocs-cli",
                    "--no-docker",
                    "mkdocs-techdocs-core",
                    "run `mkdocs",
                    "install `mkdocs",
                    "preview with",
                ):
                    self.assertNotIn(forbidden, lowered, f"{label}: {forbidden}")

        def contract_holds(text: str) -> bool:
            lowered = text.lower()
            return (
                "does not render or preview the downstream site" in lowered
                and "an unavailable external renderer is neither a finding nor a degraded lane" in lowered
                and "npx @techdocs/cli" not in lowered
            )

        refresh_text = refresh_surfaces[0][1]
        self.assertTrue(contract_holds(refresh_text))
        for mutant in (
            refresh_text.replace(
                "does not render or preview the downstream site",
                "renders or previews the downstream site with npx @techdocs/cli",
                1,
            ),
            refresh_text.replace(
                "An unavailable external renderer is neither a finding nor a degraded lane",
                "An unavailable external renderer is a degraded lane",
                1,
            ),
        ):
            with self.subTest(contract="semantic-known-bad"):
                self.assertFalse(contract_holds(mutant))

    def _review_branch(self, text: str, label: str) -> str:
        # Slice the review branch out of the document so the write-tier assertion
        # below is scoped to it: the authoring branch names the same tool legally,
        # so a whole-file negative would be vacuous.
        self.assertIn(self.REVIEW_BRANCH_HEADING, text, label)
        return text.split(self.REVIEW_BRANCH_HEADING, 1)[1].split("\n## ", 1)[0]

    def test_seed_178_and_the_prompt_carry_the_review_only_branch(self) -> None:
        # Delivery reverification killed nothing with three mutants against this
        # prose: deleting the whole review section, deleting the router sentence,
        # and pointing the review branch at the write-tier baseline tool. The seed
        # is what ships and the self-hosted prompt is hand-authored, so both carry
        # the pins; only the seed reaches a target repository.
        surfaces = (
            ("seed-178", (self.SEEDS / "178-refresh-techdocs.prompt.md").read_text(encoding="utf-8")),
            ("docs/prompts/refresh-techdocs.prompt.md", self._read("docs/prompts/refresh-techdocs.prompt.md")),
        )
        for label, text in surfaces:
            with self.subTest(surface=label):
                # The router sentence is the only thing that sends a read-only
                # request down the review branch; without it the branch is
                # present but unreachable.
                self.assertIn("**Two branches.**", text, label)
                self.assertIn("run the **read-only procedure** at the end of this document instead", text, label)
                section = self._review_branch(text, label)
                for literal in (
                    "Selected by an explicit read-only request. The deliverable is a report, not an edit.",
                    "**The rule is the invariant, not a tool list: any read-only operation is fine; nothing may write.**",
                    "**Never, in this branch:**",
                    "write or edit any page",
                    "call `wf_techdocs_baseline` in either mode",
                    "remove a generated-by marker line, which the authoring branch alone may do",
                    "call `wf_garden_docs`, `wf_sync_surfaces`, any other docs mutation, or any index mutation",
                    "call an external renderer or site-preview command",
                    "Run the audit: `wf_techdocs_audit` over MCP",
                    "findings and proposed-edits table",
                    "Write nothing.",
                ):
                    self.assertIn(literal, section, f"{label}: {literal}")
                # The forbidden-write rule, stated as its own falsifiable fact: the
                # branch promises never to invoke the write-tier baseline, whose CLI
                # has no dry-run, so no mode-bearing call form belongs in this section.
                self.assertNotIn("wf_techdocs_baseline(mode=", section, label)

    def test_seed_100_and_seed_050_register_the_shortcut(self) -> None:
        seed_100 = (self.SEEDS / "100-project-prompt-surface-bootstrap.prompt.md").read_text(encoding="utf-8")
        self.assertIn("- `docs/prompts/refresh-techdocs.prompt.md`", seed_100)
        self.assertIn("- **refresh-techdocs** (public-only)", seed_100)
        self.assertIn("`wf-techdocs`", seed_100)
        seed_050 = (self.SEEDS / "050-agent-entry-surface-bootstrap.prompt.md").read_text(encoding="utf-8")
        self.assertIn("**Refresh TechDocs shortcut**", seed_050)
        self.assertIn("**`Author TechDocs`**", seed_050)
        self.assertIn("`wf-techdocs` on their prompt docs", seed_050)

    def test_install_seeds_state_the_no_generation_and_pointer_rules(self) -> None:
        seed_011 = (self.SEEDS / "011-install-wavefoundry-phase-1.prompt.md").read_text(encoding="utf-8")
        self.assertIn("Phase 1 never generates them", seed_011)
        seed_040 = (self.SEEDS / "040-docs-structure-bootstrap.prompt.md").read_text(encoding="utf-8")
        self.assertIn("Do **not** create `docs/index.md` here", seed_040)
        self.assertIn("preserved byte-for-byte by that command", seed_040)
        seed_160 = (self.SEEDS / "160-upgrade-wavefoundry.prompt.md").read_text(encoding="utf-8")
        self.assertIn("The upgrade does **not** generate `catalog-info.yaml`, `mkdocs.yml`, or `docs/index.md`", seed_160)
        self.assertIn("run `wf render-surfaces` **again**", seed_160)
        self.assertIn("**Refresh TechDocs**", seed_160)
        seed_012 = (self.SEEDS / "012-install-wavefoundry-phase-2.prompt.md").read_text(encoding="utf-8")
        self.assertIn("### 2.13.5 — Generate the Backstage catalog and TechDocs baseline via Refresh TechDocs (seed-178)", seed_012)
        self.assertIn("the **Refresh TechDocs** shortcut with its operator follow-up checklist", seed_012)
        for seed in (seed_011, seed_040, seed_160, seed_012):
            self.assertNotIn("techdocs_baseline.py", seed)

    def test_self_hosted_surfaces_name_the_command_and_the_skill(self) -> None:
        index = self._read("docs/prompts/index.md")
        self.assertIn("| **Refresh TechDocs** / **Author TechDocs** |", index)
        self.assertIn("`wf techdocs-baseline`", index)
        agents = self._read("AGENTS.md")
        self.assertIn("| **Refresh TechDocs** / **Author TechDocs** |", agents)
        self.assertIn("`wf-techdocs` (Refresh TechDocs", agents)
        manifest = self._read("docs/prompts/prompt-surface-manifest.json")
        self.assertIn('"doc": "docs/prompts/refresh-techdocs.prompt.md"', manifest)
        self.assertIn('"shortcut": "Refresh TechDocs"', manifest)
        self.assertNotIn("Author TechDocs", manifest)
        mapping = self._read("docs/agents/platform-mapping.md")
        self.assertIn("| `wf-techdocs` | `docs/prompts/refresh-techdocs.prompt.md` |", mapping)
        prompt = self._read("docs/prompts/refresh-techdocs.prompt.md")
        # The seed carries these pins; the self-hosted twin is hand-authored, so
        # without these two lines both citation clauses could be deleted here with
        # the suite green (delivery finding QA-RV2-1).
        self.assertIn("Prefer the symbol form", prompt)
        self.assertIn("still covers the fact it is cited for", prompt)
        workflow = self._read("docs/contributing/agent-team-workflow.md")
        self.assertIn("**Refresh TechDocs** engages it as coordinator", workflow)
        catalog = self._read("docs/agents/specialists/README.md")
        self.assertIn("Coordinates **Refresh TechDocs**", catalog)
        prompt = self._read("docs/prompts/refresh-techdocs.prompt.md")
        self.assertIn("**Shortcut phrases:** `Refresh TechDocs` · `Author TechDocs`", prompt)
        self.assertIn("## Operator follow-up checklist (canonical)", prompt)
        for rel in ("docs/prompts/install-wavefoundry.prompt.md", "docs/prompts/upgrade-wavefoundry.prompt.md", "docs/references/install-assets.md"):
            self.assertIn("techdocs-baseline", self._read(rel), rel)


if __name__ == "__main__":
    unittest.main()
