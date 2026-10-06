"""Wave 1zv8c (change 1zv89): a distribution declares its own skills.

``mcp_tool_extensions.EXTENSION_SKILLS`` is a renderer-only declaration:
``render_agent_surfaces`` reads it at call time, validates it in the
preflight before any write, and renders each entry as a thin-pointer
SKILL.md; the server only lists it and never fails on it.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parent
sys.path.insert(0, str(SCRIPTS_ROOT))
sys.path.insert(0, str(TESTS_ROOT))

import mcp_tool_extensions as ext  # noqa: E402
import mcp_tool_roster  # noqa: E402
import render_agent_surfaces as ras  # noqa: E402
from declaration_support import base_declaration  # noqa: E402

GURU_STUB = "# Guru\n\nRole: guru\n"
HOSTS = (".codex", ".claude", ".agents")
PROMPT_DOC = "docs/prompts/acme-deploy.prompt.md"
VALID_SPEC = {
    "title": "Deploy Acme",
    "description": "Deploy the Acme service with the distribution's checklist. The Acme deploy workflow.",
    "prompt_doc": PROMPT_DOC,
    # A list, as a JSON profile asset declares it.
    "summary": ["Read the prompt doc before the first step.", "Never deploy without operator approval."],
}
VALID = {"acme-deploy": VALID_SPEC}
EXPECTED_DOCUMENT = (
    "---\nname: acme-deploy\n"
    "description: Deploy the Acme service with the distribution's checklist. The Acme deploy workflow.\n"
    "---\n\n"
    "# Deploy Acme (skill)\n\n"
    "This skill is a thin pointer: the workflow lives in `docs/prompts/acme-deploy.prompt.md`. "
    "Read that document and follow it; do not improvise the steps from this summary.\n\n"
    "- Read the prompt doc before the first step.\n"
    "- Never deploy without operator approval.\n"
)


def _spec(**changes: object) -> dict:
    spec = copy.deepcopy(VALID_SPEC)
    for key, value in changes.items():
        if value is _DROP:
            spec.pop(key)
        else:
            spec[key] = value
    return spec


_DROP = object()


def _repo(root: Path, *, prompt: bool = True, hosts: "tuple[str, ...]" = HOSTS) -> None:
    (root / "docs" / "agents").mkdir(parents=True)
    (root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
    (root / "docs" / "prompts").mkdir(parents=True)
    if prompt:
        (root / PROMPT_DOC).write_text("# Acme deploy\n", encoding="utf-8")
    for host in hosts:
        (root / host).mkdir()


def _snapshot(root: Path) -> "dict[str, bytes | None]":
    """Every path under ``root`` with its bytes (None for a directory)."""
    out: "dict[str, bytes | None]" = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        out[rel] = None if path.is_dir() else path.read_bytes()
    return out


class DeclaredSkillRenderTests(unittest.TestCase):
    """AC-1 and AC-3: a valid declared skill renders; the stock declaration is unchanged."""

    def test_valid_declared_skill_renders_to_every_active_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=VALID):
            root = Path(temp_dir)
            _repo(root)
            written = ras.render_skills(root)
            for host in HOSTS:
                rel = f"{host}/skills/acme-deploy/SKILL.md"
                self.assertIn(rel, written)
                self.assertEqual((root / rel).read_bytes(), EXPECTED_DOCUMENT.encode("utf-8"))
            # Framework skills still render, byte for byte, beside it.
            for skill in ras.SKILL_REGISTRY:
                if skill.requires_doc and not (root / skill.requires_doc).is_file():
                    continue
                self.assertEqual((root / ".claude" / "skills" / skill.name / "SKILL.md").read_text(
                    encoding="utf-8"), ras.skill_document(skill))
            before = _snapshot(root)
            self.assertEqual(ras.render_skills(root), [])
            self.assertEqual(_snapshot(root), before)

    def test_frontmatter_parses_as_the_declared_strings(self) -> None:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError:
            self.skipTest("PyYAML is not installed")
        front = EXPECTED_DOCUMENT.split("---\n")[1]
        self.assertEqual(yaml.safe_load(front),
                         {"name": "acme-deploy", "description": VALID_SPEC["description"]})

    def test_tuple_summary_renders_the_same_bytes(self) -> None:
        declaration = {"acme-deploy": _spec(summary=tuple(VALID_SPEC["summary"]))}
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=declaration):
            root = Path(temp_dir)
            _repo(root, hosts=(".claude",))
            ras.render_skills(root)
            self.assertEqual((root / ".claude/skills/acme-deploy/SKILL.md").read_text(encoding="utf-8"),
                             EXPECTED_DOCUMENT)

    def test_absent_prompt_doc_writes_nothing_for_that_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=VALID):
            root = Path(temp_dir)
            _repo(root, prompt=False)
            written = ras.render_skills(root)
            self.assertFalse(any("acme-deploy" in rel for rel in written))
            for host in HOSTS:
                self.assertFalse((root / host / "skills" / "acme-deploy").exists())
            self.assertNotIn(".claude/skills/acme-deploy/SKILL.md", ras._skill_output_destinations(root))

    def test_full_render_includes_the_declared_skill_and_converges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=VALID):
            root = Path(temp_dir)
            _repo(root)
            written = ras.render_agent_surfaces(root)
            self.assertIn(".codex/skills/acme-deploy/SKILL.md", written)
            before = _snapshot(root)
            again = ras.render_agent_surfaces(root)
            self.assertFalse(any("acme-deploy" in rel for rel in again), again)
            self.assertEqual(_snapshot(root), before)

    def test_stock_declaration_renders_exactly_the_framework_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration():
            root = Path(temp_dir)
            _repo(root)
            self.assertEqual(ras.declared_skills(), ())
            self.assertEqual(ras.declared_skill_problems(), [])
            ras.render_skills(root)
            expected = {skill.name for skill in ras.SKILL_REGISTRY
                        if not skill.requires_doc or (root / skill.requires_doc).is_file()}
            for host in HOSTS:
                self.assertEqual({p.name for p in (root / host / "skills").iterdir()}, expected)

    def test_framework_thin_pointers_keep_the_wavefoundry_label(self) -> None:
        plan = next(skill for skill in ras.SKILL_REGISTRY if skill.name == "wf-plan-change")
        self.assertTrue(plan.body.startswith("# Plan a change (Wavefoundry skill)\n\n"))
        with base_declaration(EXTENSION_SKILLS=VALID):
            (declared,) = ras.declared_skills()
        self.assertTrue(declared.body.startswith("# Deploy Acme (skill)\n\n"))
        self.assertEqual(declared.requires_doc, PROMPT_DOC)

    def test_the_declaration_is_read_at_call_time(self) -> None:
        with base_declaration(EXTENSION_SKILLS=VALID):
            self.assertEqual([s.name for s in ras.declared_skills()], ["acme-deploy"])
        with base_declaration():
            self.assertEqual(ras.declared_skills(), ())


class SkillDeclarationProblemTests(unittest.TestCase):
    """AC-2: every rule in Requirement 2 reports a named problem."""

    def assert_refused(self, declaration: object, name: str, key: str) -> None:
        problems = ext.skill_declaration_problems(declaration)
        self.assertTrue(problems, f"accepted: {declaration!r}")
        self.assertTrue(any(f"skill {name!r}" in p and key in p for p in problems), problems)

    def test_valid_declarations_have_no_problems(self) -> None:
        self.assertEqual(ext.skill_declaration_problems(VALID), [])
        self.assertEqual(ext.skill_declaration_problems({"acme-deploy": _spec(summary=("one line",))}), [])
        self.assertEqual(ext.skill_declaration_problems({}), [])
        # Summary lines skip the YAML scalar rules.
        self.assertEqual(ext.skill_declaration_problems({"acme-deploy": _spec(summary=["true", "42"])}), [])
        self.assertEqual(ext.skill_declaration_problems({"a" * 64: VALID_SPEC}), [])
        self.assertEqual(ext.skill_declaration_problems({"acme": _spec(description="x" * 1024)}), [])

    def test_the_declaration_must_be_a_mapping(self) -> None:
        self.assertTrue(ext.skill_declaration_problems(["acme-deploy"]))

    def test_name_rules(self) -> None:
        for name in ("Acme", "acme_deploy", "acme--deploy", "-acme", "acme-", "acme deploy", "a" * 65,
                     "wf-acme", "claude-helper", "acme-anthropic"):
            with self.subTest(name=name):
                self.assert_refused({name: VALID_SPEC}, name, "name")
        self.assertTrue(ext.skill_declaration_problems({7: VALID_SPEC}))

    def test_entry_shape_rules(self) -> None:
        self.assert_refused({"acme": "not a mapping"}, "acme", "entry")
        for key in ext.SKILL_KEYS:
            with self.subTest(missing=key):
                self.assert_refused({"acme": _spec(**{key: _DROP})}, "acme", key)
        self.assert_refused({"acme": _spec(body="free form")}, "acme", "body")

    def _text_cases(self) -> "list[object]":
        cases: "list[object]" = ["", 5, None, "a\nb", "a\rb", "a\tb", "a\x00b", "a\x1fb", "a\x7fb", "a\x85b",
                                 "a\x9bb", "a\u2028b", "a\u2029b", " lead", "trail ", "key: value", "a #b",
                                 "ends:"]
        cases += [f"{ch}x" for ch in "-?:,[]{}#&*!|>'\"%@`"]
        return cases

    def test_title_and_description_rules(self) -> None:
        scalar_cases = ["true", "False", "YES", "no", "On", "OFF", "null", "Null", "~",
                        "42", "-1.5", "+3", "1e3", "0x1F", "0o17", "0b101", "017", "1_000", ".5", "1:20",
                        ".inf", ".NaN", "inf", "nan"]
        for key in ("title", "description"):
            for value in self._text_cases() + scalar_cases:
                with self.subTest(key=key, value=value):
                    self.assert_refused({"acme": _spec(**{key: value})}, "acme", key)
        self.assert_refused({"acme": _spec(description="x" * 1025)}, "acme", "description")

    def test_summary_rules(self) -> None:
        for value in ([], ["x"] * 9, "oneline", None, {"a": 1}):
            with self.subTest(summary=value):
                self.assert_refused({"acme": _spec(summary=value)}, "acme", "summary must be a list or tuple")
        for line in self._text_cases():
            with self.subTest(line=line):
                self.assert_refused({"acme": _spec(summary=["fine", line])}, "acme", "summary[1]")
        self.assertEqual(ext.skill_declaration_problems({"acme": _spec(summary=["x"] * 8)}), [])

    def test_prompt_doc_rules(self) -> None:
        for value in ("docs\\prompts\\acme.prompt.md", "docs/prompts\\acme.prompt.md", "C:/docs/prompts/a.prompt.md",
                      "c:docs/prompts/a.prompt.md", "/docs/prompts/a.prompt.md", "docs/prompts/../a.prompt.md",
                      "docs/prompts/sub/../../a.prompt.md", "docs/prompts/./a.prompt.md",
                      "docs/prompts//a.prompt.md", "docs/other/a.prompt.md", "docs/prompts/a.md",
                      "docs/prompts/.prompt.md", "prompts/a.prompt.md", "docs/prompts/a`b.prompt.md",
                      "docs/prompts/a\nb.prompt.md", "", None, 3):
            with self.subTest(prompt_doc=value):
                self.assert_refused({"acme": _spec(prompt_doc=value)}, "acme", "prompt_doc")
        self.assertEqual(ext.skill_declaration_problems(
            {"acme": _spec(prompt_doc="docs/prompts/acme/deploy.prompt.md")}), [])
        # Each form is named by its own rule, even inside an otherwise valid path.
        for value, rule in (("docs/prompts/a\\b.prompt.md", "backslash"), ("docs/prompts/a:b.prompt.md", "':'"),
                            ("/docs/prompts/a.prompt.md", "absolute"), ("docs/prompts/../prompts/a.prompt.md", "'..'")):
            with self.subTest(prompt_doc=value, rule=rule):
                self.assert_refused({"acme": _spec(prompt_doc=value)}, "acme", rule)

    def test_every_problem_is_reported_at_once(self) -> None:
        problems = ext.skill_declaration_problems(
            {"wf-one": _spec(title="true"), "two": _spec(prompt_doc="x.md", summary=[])})
        self.assertTrue(any("'wf-one'" in p and "wf-" in p for p in problems))
        self.assertTrue(any("'wf-one' title" in p for p in problems))
        self.assertTrue(any("'two' prompt_doc" in p for p in problems))
        self.assertTrue(any("'two' summary" in p for p in problems))

    def test_the_renderer_also_refuses_a_retired_skill_path(self) -> None:
        # ".codex/skills/auto-guru/SKILL.md" is a retired path every render removes.
        self.assertEqual(ext.skill_declaration_problems({"auto-guru": VALID_SPEC}), [])
        problems = ras.declared_skill_problems({"auto-guru": VALID_SPEC})
        self.assertTrue(any("'auto-guru'" in p and ".codex/skills/auto-guru" in p for p in problems), problems)
        self.assertEqual(ras.declared_skill_problems(VALID), [])

    def test_the_retired_planning_skill_name_is_refused(self) -> None:
        # Wave 1zyc5 retired the feature-named planning skill; its rendered
        # paths are in STALE_SKILL_PATHS, so a distribution cannot revive it.
        problems = ras.declared_skill_problems({"wf-plan-feature": VALID_SPEC})
        self.assertTrue(
            any("'wf-plan-feature'" in p and "skills/wf-plan-feature" in p for p in problems), problems
        )


INVALID = {"wf-acme": VALID_SPEC, "auto-guru": VALID_SPEC, "bad-title": _spec(title="null")}


class InvalidDeclarationRefusesRenderTests(unittest.TestCase):
    """AC-2: an invalid declaration refuses every render before its first write."""

    def assert_names_every_problem(self, message: str) -> None:
        for name in INVALID:
            self.assertIn(repr(name), message)

    def test_render_agent_surfaces_refuses_and_writes_nothing(self) -> None:
        for state in ("fresh", "rendered"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                _repo(root)
                if state == "rendered":
                    with base_declaration(EXTENSION_SKILLS=VALID):
                        ras.render_agent_surfaces(root)
                # A legacy prompt the first mutating step would migrate.
                (root / ras.REVIEW_PLAN_OLD_PROMPT).write_text("# legacy\n", encoding="utf-8")
                before = _snapshot(root)
                with base_declaration(EXTENSION_SKILLS=INVALID):
                    with self.assertRaises(RuntimeError) as caught:
                        ras.render_agent_surfaces(root)
                self.assert_names_every_problem(str(caught.exception))
                self.assertEqual(_snapshot(root), before)

    def test_render_skills_rechecks_before_its_own_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _repo(root)
            before = _snapshot(root)
            with base_declaration(EXTENSION_SKILLS=INVALID), self.assertRaises(RuntimeError) as caught:
                ras.render_skills(root)
            self.assert_names_every_problem(str(caught.exception))
            self.assertEqual(_snapshot(root), before)

    def test_preflight_refuses_each_rule_the_renderer_owns(self) -> None:
        for declaration in ({"wf-acme": VALID_SPEC}, {"auto-guru": VALID_SPEC}):
            with self.subTest(declaration=list(declaration)), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                _repo(root)
                with base_declaration(EXTENSION_SKILLS=declaration), self.assertRaises(RuntimeError) as caught:
                    ras.preflight_agent_surface_paths(root)
                self.assertIn(repr(next(iter(declaration))), str(caught.exception))

    def _run_main(self, module: str, root: Path, declaration: dict) -> subprocess.CompletedProcess:
        driver = (
            "import json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import mcp_tool_extensions\n"
            "mcp_tool_extensions.EXTENSION_SKILLS = json.loads(sys.argv[2])\n"
            f"import {module} as target\n"
            "argv = ['--repo-root', sys.argv[3]]\n"
            "sys.exit(target.main(argv) if target.main.__code__.co_argcount else "
            "(sys.argv.__setitem__(slice(1, None), argv) or target.main()))\n"
        )
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["WAVEFOUNDRY_SKIP_PYTHON_HEAL"] = "1"
        return subprocess.run(
            [sys.executable, "-B", "-c", driver, str(SCRIPTS_ROOT), json.dumps(declaration), str(root)],
            cwd=str(SCRIPTS_ROOT), env=env, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False, timeout=300,
        )

    def test_both_render_entry_points_refuse_and_write_nothing(self) -> None:
        for module in ("render_platform_surfaces", "render_agent_surfaces"):
            with self.subTest(module=module), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                _repo(root)
                (root / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
                (root / ras.REVIEW_PLAN_OLD_PROMPT).write_text("# legacy\n", encoding="utf-8")
                before = _snapshot(root)
                result = self._run_main(module, root, INVALID)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("EXTENSION_SKILLS", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assert_names_every_problem(result.stderr)
                self.assertEqual(_snapshot(root), before)

    def test_platform_entry_point_renders_a_valid_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _repo(root)
            result = self._run_main("render_platform_surfaces", root, VALID)
            self.assertEqual(result.returncode, 0, result.stderr)
            for host in HOSTS:
                self.assertEqual((root / host / "skills" / "acme-deploy" / "SKILL.md").read_text(encoding="utf-8"),
                                 EXPECTED_DOCUMENT)


class ServerToleratesSkillDeclarationTests(unittest.TestCase):
    """AC-3: the skill declaration is never fatal to the server."""

    def test_a_skills_only_declaration_is_not_a_tool_declaration(self) -> None:
        with base_declaration(EXTENSION_SKILLS=INVALID):
            self.assertFalse(ext.declared())
            self.assertEqual(mcp_tool_roster.all_tool_tiers(), dict(mcp_tool_roster.TOOL_TIERS))
            mcp_tool_roster.allow_rules(include_write=True)
            ext.validate_declaration(core_tools=set(mcp_tool_roster.TOOL_TIERS) - mcp_tool_roster.RUNNER_TOOLS,
                                     runner_tools=mcp_tool_roster.RUNNER_TOOLS)

    def test_server_info_lists_declared_skills_and_problems(self) -> None:
        from server_tools_support import load_server
        srv = load_server()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with base_declaration():
                stock = srv.wf_server_info_response(root)["data"]["extensions"]
            self.assertEqual(stock["skills"], [])
            self.assertNotIn("skill_problems", stock)
            with base_declaration(EXTENSION_SKILLS=VALID):
                valid = srv.wf_server_info_response(root)
            self.assertEqual(valid["data"]["extensions"]["skills"], ["acme-deploy"])
            self.assertNotIn("skill_problems", valid["data"]["extensions"])
            declaration = {**VALID, "wf-acme": _spec(title="true")}
            with base_declaration(EXTENSION_SKILLS=declaration):
                response = srv.wf_server_info_response(root)
            extensions = response["data"]["extensions"]
            self.assertEqual(extensions["skills"], ["acme-deploy", "wf-acme"])
            self.assertEqual(extensions["skill_problems"], ext.skill_declaration_problems(declaration))
            self.assertTrue(any("'wf-acme' title" in p for p in extensions["skill_problems"]))


if __name__ == "__main__":
    unittest.main()
