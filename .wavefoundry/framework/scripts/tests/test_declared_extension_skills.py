"""Wave 1zv8c (change 1zv89): a distribution declares its own skills.

``mcp_tool_extensions.EXTENSION_SKILLS`` is a renderer-only declaration:
``render_agent_surfaces`` reads it at call time, validates it in the
preflight before any write, and renders each entry as a thin-pointer
SKILL.md; the server only lists it and never fails on it.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import time
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
MARKER = "<!-- wavefoundry:declared-skill -->"
# The wave 1zv8c rendering, before the ownership marker (wave 1zyb3, change 1zxnu).
LEGACY_DOCUMENT = (
    "---\nname: acme-deploy\n"
    "description: Deploy the Acme service with the distribution's checklist. The Acme deploy workflow.\n"
    "---\n\n"
    "# Deploy Acme (skill)\n\n"
    "This skill is a thin pointer: the workflow lives in `docs/prompts/acme-deploy.prompt.md`. "
    "Read that document and follow it; do not improvise the steps from this summary.\n\n"
    "- Read the prompt doc before the first step.\n"
    "- Never deploy without operator approval.\n"
)
EXPECTED_DOCUMENT = (
    "---\nname: acme-deploy\n"
    "description: Deploy the Acme service with the distribution's checklist. The Acme deploy workflow.\n"
    "---\n\n"
    "<!-- wavefoundry:declared-skill -->\n\n"
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


# ---- Wave 1zyb3 (change 1zxnu): ownership marker, orphans, templates ----------

TEMPLATE = "lifecycle-prompts/review-plan.prompt.md"
PACKAGED_TEMPLATE = SCRIPTS_ROOT.parent / "install" / TEMPLATE
KEEP_SPEC = _spec(title="Keep Me", prompt_doc="docs/prompts/keep-me.prompt.md")


def _head_document(skill: "ras.Skill") -> str:
    """The SKILL.md bytes HEAD renders for a framework skill: frontmatter, blank line, body."""
    return f"---\nname: {skill.name}\ndescription: {skill.description}\n---\n\n{skill.body}"


def _render_capturing(func, root: Path) -> "tuple[list[str], str]":
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        written = func(root)
    return written, err.getvalue()


def _dir_link(link: Path, target: Path) -> str:
    """A directory symlink, or a junction on Windows when symlinks need a privilege."""
    try:
        link.symlink_to(target, target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError):
        if os.name == "nt":
            import _winapi  # noqa: PLC0415

            _winapi.CreateJunction(str(target), str(link))
            return "junction"
        raise unittest.SkipTest("directory links are unavailable here")


def _write(path: Path, content: "str | bytes") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_bytes(content.encode("utf-8"))


class DeclaredSkillMarkerTests(unittest.TestCase):
    """AC-1: declared skills carry the marker as the first body line; wf- skills do not move."""

    def test_rendered_declared_skill_has_two_frontmatter_keys_and_the_marker_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=VALID):
            root = Path(temp_dir)
            _repo(root)
            ras.render_skills(root)
            for host in HOSTS:
                lines = (root / host / "skills/acme-deploy/SKILL.md").read_text(encoding="utf-8").split("\n")
                self.assertEqual(lines[0], "---")
                close = lines.index("---", 1)
                self.assertEqual([line.split(":", 1)[0] for line in lines[1:close]], ["name", "description"])
                self.assertEqual(lines[close + 1], "")
                self.assertEqual(lines[close + 2], MARKER)

    def test_marker_detection_needs_the_first_body_line(self) -> None:
        self.assertTrue(ras.has_declared_skill_marker(EXPECTED_DOCUMENT))
        self.assertTrue(ras.has_declared_skill_marker(EXPECTED_DOCUMENT.replace("\n", "\r\n")))
        self.assertFalse(ras.has_declared_skill_marker(LEGACY_DOCUMENT))
        elsewhere = LEGACY_DOCUMENT.replace("# Deploy Acme (skill)\n", f"# Deploy Acme (skill)\n\n{MARKER}\n")
        self.assertIn(MARKER, elsewhere)
        self.assertFalse(ras.has_declared_skill_marker(elsewhere))
        self.assertFalse(ras.has_declared_skill_marker(f"{MARKER}\n# no frontmatter\n"))
        self.assertFalse(ras.has_declared_skill_marker(f"---\nname: x\n{MARKER}\n"))
        self.assertFalse(ras.has_declared_skill_marker(EXPECTED_DOCUMENT.replace(MARKER, MARKER + " ")))

    def test_framework_skills_keep_their_head_bytes(self) -> None:
        for skill in ras.SKILL_REGISTRY:
            with self.subTest(skill=skill.name):
                self.assertFalse(skill.declared)
                self.assertEqual(ras.skill_document(skill), _head_document(skill))
                self.assertNotIn(MARKER, ras.skill_document(skill))
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=VALID):
            root = Path(temp_dir)
            _repo(root)
            ras.render_skills(root)
            for skill in ras.SKILL_REGISTRY:
                if skill.requires_doc and not (root / skill.requires_doc).is_file():
                    continue
                for host in HOSTS:
                    self.assertEqual((root / host / "skills" / skill.name / "SKILL.md").read_bytes(),
                                     _head_document(skill).encode("utf-8"))


class DeclaredSkillOwnershipTests(unittest.TestCase):
    """AC-2 and AC-3: an unmarked SKILL.md is never overwritten unless it is the pre-marker rendering."""

    HAND = "---\nname: acme-deploy\ndescription: Mine.\n---\n\n# My own skill\n"

    def test_hand_written_skill_is_refused_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=VALID):
            root = Path(temp_dir)
            _repo(root)
            hand = root / ".claude/skills/acme-deploy/SKILL.md"
            _write(hand, self.HAND)
            written, err = _render_capturing(ras.render_agent_surfaces, root)
            self.assertEqual(hand.read_bytes(), self.HAND.encode("utf-8"))
            self.assertNotIn(".claude/skills/acme-deploy/SKILL.md", written)
            notices = [line for line in err.splitlines() if "NOTICE" in line]
            self.assertEqual(len(notices), 1, err)
            self.assertIn(".claude/skills/acme-deploy/SKILL.md", notices[0])
            self.assertIn("rename the declared skill", notices[0])
            self.assertIn("remove or rename the hand-written folder", notices[0])
            # Every other skill and surface still renders.
            for host in (".codex", ".agents"):
                self.assertIn(f"{host}/skills/acme-deploy/SKILL.md", written)
            self.assertIn(".claude/skills/wf-plan-change/SKILL.md", written)
            self.assertIn(".claude/agents/guru.md", written)

    def test_pre_marker_rendering_is_adopted_lf_and_crlf(self) -> None:
        for label, legacy in (("lf", LEGACY_DOCUMENT), ("crlf", LEGACY_DOCUMENT.replace("\n", "\r\n"))):
            with self.subTest(label), tempfile.TemporaryDirectory() as temp_dir, \
                    base_declaration(EXTENSION_SKILLS=VALID):
                root = Path(temp_dir)
                _repo(root)
                for host in HOSTS:
                    _write(root / host / "skills/acme-deploy/SKILL.md", legacy)
                written, err = _render_capturing(ras.render_skills, root)
                self.assertNotIn("NOTICE", err)
                for host in HOSTS:
                    rel = f"{host}/skills/acme-deploy/SKILL.md"
                    self.assertIn(rel, written)
                    self.assertEqual((root / rel).read_bytes(), EXPECTED_DOCUMENT.encode("utf-8"))

    def test_one_byte_off_the_pre_marker_rendering_is_refused(self) -> None:
        near = LEGACY_DOCUMENT.replace("Never deploy", "Never Deploy")
        self.assertEqual(len(near), len(LEGACY_DOCUMENT))
        for label, content in (("changed", near), ("appended", LEGACY_DOCUMENT + "x")):
            with self.subTest(label), tempfile.TemporaryDirectory() as temp_dir, \
                    base_declaration(EXTENSION_SKILLS=VALID):
                root = Path(temp_dir)
                _repo(root)
                target = root / ".codex/skills/acme-deploy/SKILL.md"
                _write(target, content)
                written, err = _render_capturing(ras.render_skills, root)
                self.assertEqual(target.read_bytes(), content.encode("utf-8"))
                self.assertNotIn(".codex/skills/acme-deploy/SKILL.md", written)
                self.assertIn(".codex/skills/acme-deploy/SKILL.md", err)

    def test_a_marked_file_is_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=VALID):
            root = Path(temp_dir)
            _repo(root)
            target = root / ".claude/skills/acme-deploy/SKILL.md"
            _write(target, EXPECTED_DOCUMENT.replace("Never deploy", "Old text"))
            written, err = _render_capturing(ras.render_skills, root)
            self.assertNotIn("NOTICE", err)
            self.assertIn(".claude/skills/acme-deploy/SKILL.md", written)
            self.assertEqual(target.read_bytes(), EXPECTED_DOCUMENT.encode("utf-8"))


class DeclaredSkillOrphanTests(unittest.TestCase):
    """AC-4 and AC-5: undeclared marked folders are removed; everything else is left alone."""

    def test_removed_declaration_removes_only_the_owned_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(temp_dir)
            outside = Path(outside_dir)
            _repo(root)
            with base_declaration(EXTENSION_SKILLS={**VALID, "keep-me": KEEP_SPEC}):
                ras.render_skills(root)  # keep-me is gated off: no prompt doc
            skills = root / ".claude/skills"
            kept = {
                # Marked, and its name casefolds to the still-declared keep-me.
                "Keep-Me/SKILL.md": EXPECTED_DOCUMENT,
                # Unmarked, hand-written.
                "hand-made/SKILL.md": LEGACY_DOCUMENT,
                # The framework's namespace, even when marked.
                "wf-custom/SKILL.md": EXPECTED_DOCUMENT,
                # Marked, with an extra entry.
                "extra-entry/SKILL.md": EXPECTED_DOCUMENT,
                "extra-entry/notes.txt": "operator notes\n",
            }
            for rel, content in kept.items():
                _write(skills / rel, content)
            _write(outside / "target/SKILL.md", EXPECTED_DOCUMENT)
            kind = _dir_link(skills / "linked", outside / "target")
            # A real folder whose SKILL.md is a link to a marked file elsewhere.
            (skills / "file-link").mkdir()
            try:
                (skills / "file-link" / "SKILL.md").symlink_to(outside / "target" / "SKILL.md")
                file_link = True
            except (OSError, NotImplementedError):
                file_link = False
            before_kept = {rel: (skills / rel).read_bytes() for rel in kept}
            before_outside = _snapshot(outside)
            with base_declaration(EXTENSION_SKILLS={"keep-me": KEEP_SPEC}):
                written, err = _render_capturing(ras.render_skills, root)
            for host in HOSTS:
                rel = f"{host}/skills/acme-deploy/SKILL.md"
                self.assertIn(rel, written)
                self.assertFalse((root / host / "skills" / "acme-deploy").exists(), host)
            self.assertEqual({rel: (skills / rel).read_bytes() for rel in kept}, before_kept)
            self.assertEqual(sorted(p.name for p in (skills / "extra-entry").iterdir()), ["SKILL.md", "notes.txt"])
            self.assertEqual(_snapshot(outside), before_outside, kind)
            self.assertTrue(os.path.lexists(skills / "linked"))
            if file_link:
                self.assertTrue((skills / "file-link" / "SKILL.md").is_symlink())
            notices = [line for line in err.splitlines() if "NOTICE" in line]
            self.assertEqual(len(notices), 1, err)
            self.assertIn(".claude/skills/extra-entry", notices[0])
            self.assertFalse(any("linked" in rel or "Keep-Me" in rel or "hand-made" in rel
                                 or "wf-custom" in rel or "extra-entry" in rel for rel in written), written)

    def test_gated_off_declared_skill_keeps_its_marked_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=VALID):
            root = Path(temp_dir)
            _repo(root)
            ras.render_skills(root)
            (root / PROMPT_DOC).unlink()
            before = _snapshot(root)
            self.assertEqual(ras.render_skills(root), [])
            self.assertEqual(_snapshot(root), before)
            self.assertTrue((root / ".claude/skills/acme-deploy/SKILL.md").is_file())

    def test_linked_host_skills_root_still_raises_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(temp_dir)
            outside = Path(outside_dir)
            _repo(root)
            _write(outside / "orphan/SKILL.md", EXPECTED_DOCUMENT)
            _dir_link(root / ".claude/skills", outside)
            before = _snapshot(root)
            before_outside = _snapshot(outside)
            with base_declaration(), self.assertRaises(RuntimeError):
                ras.render_skills(root)
            self.assertEqual(_snapshot(root), before)
            self.assertEqual(_snapshot(outside), before_outside)

    def test_orphan_folder_gaining_an_entry_after_the_decision_survives(self) -> None:
        """Wave 1zyb3 delivery repair (DEL-4b): removal is unlink + rmdir,
        never rmtree; an entry that appears between the orphan decision and
        the removal survives with its folder, reported in a NOTICE."""
        from unittest import mock

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _repo(root)
            with base_declaration(EXTENSION_SKILLS=VALID):
                ras.render_skills(root)
            real = ras._declared_skill_orphans

            def _decide_then_add(active_skill_roots):
                orphans = real(active_skill_roots)
                for _rel, _skill_file, folder in orphans:
                    (folder / ".DS_Store").write_bytes(b"late")
                return orphans

            with base_declaration(), mock.patch.object(ras, "_declared_skill_orphans", _decide_then_add):
                written, err = _render_capturing(ras.render_skills, root)
            for host in HOSTS:
                folder = root / host / "skills" / "acme-deploy"
                self.assertIn(f"{host}/skills/acme-deploy/SKILL.md", written)
                self.assertFalse((folder / "SKILL.md").exists(), host)
                self.assertEqual((folder / ".DS_Store").read_bytes(), b"late", host)
                self.assertIn(f"{host}/skills/acme-deploy could not be removed", err)
            notices = [line for line in err.splitlines() if "NOTICE" in line]
            self.assertEqual(len(notices), len(HOSTS), err)
            self.assertNotIn(str(root), err)
            # Wave 200xy (200v2): the NOTICE names the rmdir failure's class.
            for notice in notices:
                self.assertIn("(OSError)", notice)

    def test_failed_orphan_unlink_raises_path_free_before_any_write(self) -> None:
        """Wave 200xy (200v2): a failed orphan SKILL.md unlink raises
        RuntimeError naming the relative path and the exception class only,
        and stops the render before any skill write or prompt creation."""
        from unittest import mock

        other_prompt = "docs/prompts/other-skill.prompt.md"
        other = {"other-skill": _spec(title="Other Skill", prompt_doc=other_prompt,
                                      prompt_doc_template=TEMPLATE)}
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _repo(root)
            with base_declaration(EXTENSION_SKILLS=VALID):
                ras.render_skills(root)
            before = _snapshot(root)
            real_unlink = Path.unlink

            def _locked_unlink(path, *args, **kwargs):
                if path.name == "SKILL.md" and "acme-deploy" in path.parts:
                    raise PermissionError(13, "Permission denied", str(path))
                return real_unlink(path, *args, **kwargs)

            with base_declaration(EXTENSION_SKILLS=other), \
                    mock.patch.object(Path, "unlink", _locked_unlink), \
                    self.assertRaises(RuntimeError) as caught:
                ras.render_skills(root)
            message = str(caught.exception)
            self.assertRegex(message, r"(\.codex|\.claude|\.agents)/skills/acme-deploy/SKILL\.md")
            self.assertIn("(PermissionError)", message)
            self.assertNotIn(str(root), message)
            self.assertNotIn(str(root.resolve()), message)
            self.assertNotIn("Permission denied", message)
            # Nothing was written after the failure: no skill folder for the
            # newly declared skill, no materialized prompt creation, and the
            # tree is exactly as before the render.
            self.assertFalse((root / other_prompt).exists())
            for host in HOSTS:
                self.assertFalse((root / host / "skills" / "other-skill").exists(), host)
            self.assertEqual(_snapshot(root), before)


class PromptDocTemplateTests(unittest.TestCase):
    """AC-6 and AC-7: the optional prompt_doc_template key."""

    def assert_refused(self, value: object, rule: str) -> None:
        problems = ext.skill_declaration_problems({"acme": _spec(prompt_doc_template=value)})
        named = [p for p in problems if "prompt_doc_template" in p and rule in p]
        self.assertEqual(len(named), 1, problems)

    def test_valid_template_is_accepted(self) -> None:
        self.assertEqual(ext.SKILL_OPTIONAL_KEYS, ("prompt_doc_template",))
        for value in (TEMPLATE, "acme.prompt.md", "acme/sub/deploy.prompt.md"):
            with self.subTest(value=value):
                self.assertEqual(ext.skill_declaration_problems({"acme": _spec(prompt_doc_template=value)}), [])

    def test_each_rule_is_named(self) -> None:
        for value, rule in (("/install/a.prompt.md", "absolute"), ("a/../b.prompt.md", "'..'"),
                            ("a\\b.prompt.md", "backslash"), ("c:a.prompt.md", "':'"),
                            ("a/b.md", "must end in .prompt.md"), (7, "non-empty string"),
                            ("a/./b.prompt.md", "'..'"), ("a//b.prompt.md", "'..'"),
                            ("a`b.prompt.md", "backtick"), ("a\nb.prompt.md", "control")):
            with self.subTest(value=value):
                self.assert_refused(value, rule)
        problems = ext.skill_declaration_problems({"acme": _spec(prompt_doc_template=TEMPLATE, extra=1)})
        self.assertEqual([p for p in problems if "unknown key" in p], ["skill 'acme': unknown key(s) extra"])
        problems = ext.skill_declaration_problems({"acme": _spec(prompt_doc=_DROP, prompt_doc_template=TEMPLATE)})
        self.assertTrue(any("missing key(s) prompt_doc" in p for p in problems), problems)

    def test_absent_doc_is_created_from_the_template_and_the_skill_renders(self) -> None:
        declaration = {"acme-deploy": _spec(prompt_doc_template=TEMPLATE)}
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=declaration):
            root = Path(temp_dir)
            _repo(root, prompt=False)
            written = ras.render_skills(root)
            self.assertIn(PROMPT_DOC, written)
            expected = PACKAGED_TEMPLATE.read_text(encoding="utf-8").replace(
                "{{generated_at}}", time.strftime("%Y-%m-%d"))
            self.assertIn("{{generated_at}}", PACKAGED_TEMPLATE.read_text(encoding="utf-8"))
            self.assertEqual((root / PROMPT_DOC).read_text(encoding="utf-8"), expected)
            for host in HOSTS:
                self.assertIn(f"{host}/skills/acme-deploy/SKILL.md", written)
            # The doc now exists, so a second render creates nothing and is quiet.
            self.assertEqual(ras._declared_prompt_doc_creations(root), {})
            self.assertEqual(ras.render_skills(root), [])

    def test_a_skipped_prompt_doc_is_not_created_and_its_skill_waits(self) -> None:
        """Wave 200xy (200xx): a prompt doc in ``skip_paths`` (an unrecorded
        profile prompt path) is not created; its skill renders once it is."""
        declaration = {"acme-deploy": _spec(prompt_doc_template=TEMPLATE)}
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=declaration):
            root = Path(temp_dir)
            _repo(root, prompt=False)
            written = ras.render_skills(root, skip_paths=frozenset({PROMPT_DOC}))
            self.assertFalse(os.path.lexists(root / PROMPT_DOC))
            self.assertNotIn(PROMPT_DOC, written)
            for host in HOSTS:
                self.assertFalse((root / host / "skills" / "acme-deploy").exists(), host)
            written = ras.render_skills(root)
            self.assertIn(PROMPT_DOC, written)
            self.assertIn(".codex/skills/acme-deploy/SKILL.md", written)

    def test_target_template_wins_and_an_existing_doc_is_kept(self) -> None:
        declaration = {"acme-deploy": _spec(prompt_doc_template="acme/deploy.prompt.md")}
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=declaration):
            root = Path(temp_dir)
            _repo(root, prompt=False)
            _write(root / ".wavefoundry/framework/install/acme/deploy.prompt.md", "# Acme\n\nLast verified: {{generated_at}}\n")
            ras.render_skills(root)
            self.assertTrue((root / PROMPT_DOC).read_text(encoding="utf-8").startswith("# Acme\n\nLast verified: 2"))
            _write(root / PROMPT_DOC, "# operator copy\n")
            written = ras.render_agent_surfaces(root)
            self.assertNotIn(PROMPT_DOC, written)
            self.assertEqual((root / PROMPT_DOC).read_bytes(), b"# operator copy\n")

    def test_missing_template_raises_naming_it_before_any_write(self) -> None:
        declaration = {"acme-deploy": _spec(prompt_doc_template="acme/none.prompt.md")}
        for render in (ras.render_agent_surfaces, ras.render_skills, ras.preflight_agent_surface_paths):
            with self.subTest(render=render.__name__), tempfile.TemporaryDirectory() as temp_dir, \
                    base_declaration(EXTENSION_SKILLS=declaration):
                root = Path(temp_dir)
                _repo(root, prompt=False)
                (root / ras.REVIEW_PLAN_OLD_PROMPT).write_text("# legacy\n", encoding="utf-8")
                before = _snapshot(root)
                with self.assertRaises(RuntimeError) as caught:
                    render(root)
                self.assertIn("acme/none.prompt.md", str(caught.exception))
                self.assertEqual(_snapshot(root), before)
        # With the doc present the template is never needed.
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=declaration):
            root = Path(temp_dir)
            _repo(root)
            ras.render_skills(root)
            self.assertEqual((root / PROMPT_DOC).read_text(encoding="utf-8"), "# Acme deploy\n")

    def test_preflight_contains_the_template_destination(self) -> None:
        # The prompt doc sits in its own folder, linked outside the repository,
        # so only the template destination itself can trip the containment.
        nested = "docs/prompts/acme/deploy.prompt.md"
        declaration = {"acme-deploy": _spec(prompt_doc=nested, prompt_doc_template=TEMPLATE)}
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir, \
                base_declaration(EXTENSION_SKILLS=declaration):
            root = Path(temp_dir)
            _repo(root, prompt=False)
            _dir_link(root / "docs/prompts/acme", Path(outside_dir))
            for check in (ras.preflight_agent_surface_paths, ras.render_skills):
                with self.subTest(check=check.__name__), self.assertRaises(RuntimeError) as caught:
                    check(root)
                self.assertIn(nested, str(caught.exception))
            self.assertEqual(list(Path(outside_dir).iterdir()), [])

    def test_dangling_link_at_the_prompt_doc_is_present_and_never_written_through(self) -> None:
        """Wave 1zyb3 delivery repair (DEL-4a): ``lexists``, so a dangling
        link at the prompt doc is never followed by the template creation."""
        declaration = {"acme-deploy": _spec(prompt_doc_template=TEMPLATE)}
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=declaration):
            root = Path(temp_dir)
            _repo(root, prompt=False)
            try:
                (root / PROMPT_DOC).symlink_to("acme-elsewhere.prompt.md")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            self.assertEqual(ras._declared_prompt_doc_creations(root), {})
            written = ras.render_skills(root)
            self.assertNotIn(PROMPT_DOC, written)
            self.assertFalse((root / "docs/prompts/acme-elsewhere.prompt.md").exists())
            self.assertTrue((root / PROMPT_DOC).is_symlink())

    def test_template_creation_never_overwrites_a_doc_that_appears_after_the_check(self) -> None:
        """Wave 1zyb3 delivery repair (DEL-4c): the create is ``O_EXCL``, so
        a prompt doc written between the presence check and the create is
        neither truncated nor overwritten."""
        from unittest import mock

        declaration = {"acme-deploy": _spec(prompt_doc_template=TEMPLATE)}
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(EXTENSION_SKILLS=declaration):
            root = Path(temp_dir)
            _repo(root, prompt=False)
            real = ras._declared_prompt_doc_creations

            def _check_then_appear(repo_root):
                creations = real(repo_root)
                (root / PROMPT_DOC).write_bytes(b"# operator copy\n")
                return creations

            with mock.patch.object(ras, "_declared_prompt_doc_creations", _check_then_appear), \
                    self.assertRaises(RuntimeError):
                ras.render_skills(root)
            self.assertEqual((root / PROMPT_DOC).read_bytes(), b"# operator copy\n")


class StockDeclarationSkillBytesTests(unittest.TestCase):
    """AC-8: under the shipped empty declaration every skill path keeps its HEAD bytes."""

    def test_stock_render_matches_head_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration():
            root = Path(temp_dir)
            _repo(root)
            (root / "docs/prompts/package-wavefoundry.prompt.md").write_text("# p\n", encoding="utf-8")
            written = ras.render_agent_surfaces(root)
            skill_paths = sorted(rel for rel in written if "/skills/" in rel)
            expected = sorted(
                f"{host}/skills/{skill.name}/SKILL.md"
                for skill in ras.SKILL_REGISTRY for host in HOSTS
                if not skill.requires_doc or (root / skill.requires_doc).is_file()
            )
            self.assertEqual(skill_paths, expected)
            by_name = {skill.name: skill for skill in ras.SKILL_REGISTRY}
            for rel in skill_paths:
                text = (root / rel).read_text(encoding="utf-8")
                if rel.startswith(".codex/skills/wf-guru/"):
                    # The Codex guru skill is also a review carrier with reconciled regions.
                    self.assertTrue(text.startswith(_head_document(by_name["wf-guru"])[:200]))
                    continue
                self.assertEqual(text, _head_document(by_name[rel.split("/")[2]]), rel)
            self.assertFalse(any(MARKER in (root / rel).read_text(encoding="utf-8") for rel in skill_paths))


if __name__ == "__main__":
    unittest.main()
