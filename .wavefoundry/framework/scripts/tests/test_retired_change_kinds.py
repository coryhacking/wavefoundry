"""Retired change kinds (wave 1zli8, change 1zlhx).

``vocabulary_profile.RETIRED_CHANGE_KINDS`` names the kinds no creation path
mints any more (``feat``). The kind stays in the grammar, so existing ids lint
unchanged; ``wf_new_feature``, ``change_doc_response`` and the lifecycle-id CLI
refuse it with one sentence, ``retired_kind_message``, naming the replacement.
The scratch-tree single-source case (AC-6) and the lint case (AC-3) live in
``test_change_kinds``, beside the scratch machinery they share.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

from server_tools_support import SCRIPTS_ROOT, load_server, load_thin_runner, _make_repo
import record_paths
import vocabulary_profile


def _plans_dir(root: Path) -> Path:
    return Path(root).joinpath(*record_paths.PLANS_ROOT.split("/"))


def _call_tool(mcp, name: str, args: dict) -> dict:
    """Call through FastMCP's real client path."""
    result = asyncio.run(mcp.call_tool(name, args))
    if isinstance(result, tuple):
        structured = result[1]
        if isinstance(structured, dict):
            return structured.get("result", structured)
        result = result[0]
    if isinstance(result, dict):
        return result
    return json.loads(result[0].text)


def _files_under(root: Path) -> list[str]:
    """Every project file under ``docs/`` (the server's own runtime state under
    ``.wavefoundry/``, such as producer locks, is not a change-doc write)."""
    docs = Path(root) / "docs"
    return sorted(p.relative_to(root).as_posix() for p in docs.rglob("*") if p.is_file())


class _MintSpy:
    """Stands in for the lifecycle module: records every ``build_id`` call and
    delegates to the real one."""

    def __init__(self, real):
        self._real = real
        self.calls: list[tuple] = []

    def build_id(self, kind, slug, **kwargs):
        self.calls.append((kind, slug))
        return self._real.build_id(kind, slug, **kwargs)


class RetiredKindDeclarationTests(unittest.TestCase):
    """Requirement 1: the retired set is declared once, beside the core kinds."""

    def test_feat_is_the_retired_kind_and_stays_in_the_grammar(self):
        self.assertEqual(vocabulary_profile.RETIRED_CHANGE_KINDS, ("feat",))
        self.assertIn("feat", vocabulary_profile.CORE_CHANGE_KINDS)
        self.assertIn("feat", vocabulary_profile.CHANGE_KINDS)

    def test_mintable_kinds_are_the_change_kinds_without_the_retired_ones_in_order(self):
        expected = tuple(k for k in vocabulary_profile.CHANGE_KINDS if k not in ("feat",))
        self.assertEqual(vocabulary_profile.MINTABLE_CHANGE_KINDS, expected)

    def test_the_message_names_the_kind_existing_ids_and_the_replacement(self):
        message = vocabulary_profile.retired_kind_message("feat")
        self.assertIn("'feat'", message)
        self.assertIn("retired", message)
        self.assertIn("existing", message)
        self.assertIn("enh", message)
        self.assertIn("wf_new_enhancement", message)


class McpRefusalTests(unittest.TestCase):
    """AC-1: ``wf_new_feature`` through ``call_tool`` refuses and writes nothing."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self._tmp.name))
        try:
            self.mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

    def tearDown(self):
        self._tmp.cleanup()

    def _call(self, name: str, slug: str) -> "tuple[dict, _MintSpy]":
        spy = _MintSpy(self.srv._lifecycle_module())
        with mock.patch.object(self.srv, "_lifecycle_module", return_value=spy):
            return _call_tool(self.mcp, name, {"slug": slug}), spy

    def test_wf_new_feature_returns_the_retired_refusal(self):
        before = _files_under(self.root)
        config = (self.root / "docs" / "workflow-config.json").read_bytes()
        result, spy = self._call("wf_new_feature", "some-feature")
        self.assertEqual(result["status"], "error", result)
        self.assertEqual(result["data"], {"kind": "feat", "slug": "some-feature", "mode": "create"})
        self.assertEqual(len(result["diagnostics"]), 1, result["diagnostics"])
        diagnostic = result["diagnostics"][0]
        self.assertEqual(diagnostic["code"], "change_kind_retired")
        self.assertEqual(diagnostic["message"], vocabulary_profile.retired_kind_message("feat"))
        self.assertEqual(diagnostic["recovery_tools"], ["wf_new_enhancement"])
        self.assertEqual(result["next_tools"], ["wf_new_enhancement"])
        self.assertEqual(result["usage"], "wf_new_enhancement(slug=...)")
        # No file, no lifecycle mint.
        self.assertFalse(_plans_dir(self.root).exists())
        self.assertEqual(_files_under(self.root), before)
        self.assertEqual((self.root / "docs" / "workflow-config.json").read_bytes(), config)
        self.assertEqual(spy.calls, [])

    def test_wf_new_enhancement_still_mints(self):
        result, spy = self._call("wf_new_enhancement", "some-change")
        self.assertEqual(result["status"], "ok", result)
        self.assertTrue(result["data"]["change_id"].endswith("-enh some-change"))
        self.assertTrue((self.root / result["data"]["path"]).is_file())
        self.assertEqual([kind for kind, _slug in spy.calls], ["enh"])


class ChangeDocResponseRefusalTests(unittest.TestCase):
    """AC-2: the extension helper refuses the retired kind; casing keeps today's error."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_feat_is_refused_and_nothing_is_written(self):
        before = _files_under(self.root)
        spy = _MintSpy(self.srv._lifecycle_module())
        with mock.patch.object(self.srv, "_lifecycle_module", return_value=spy):
            result = self.srv.change_doc_response(self.root, "feat", "made-here")
        self.assertEqual(result["status"], "error", result)
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["change_kind_retired"])
        self.assertEqual(result["diagnostics"][0]["message"], vocabulary_profile.retired_kind_message("feat"))
        self.assertEqual(result["next_tools"], ["wf_new_enhancement"])
        self.assertEqual(_files_under(self.root), before)
        self.assertEqual(spy.calls, [])

    def test_uppercase_feat_keeps_invalid_arguments(self):
        result = self.srv.change_doc_response(self.root, "FEAT", "made-here")
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["invalid_arguments"])
        # The refusal lists only the kinds that can be created.
        message = result["diagnostics"][0]["message"]
        self.assertIn(", ".join(vocabulary_profile.MINTABLE_CHANGE_KINDS), message)
        self.assertNotIn("feat", message.split(";", 1)[1])

    def test_the_shared_check_compares_the_normalized_kind_before_the_slug_check(self):
        for kind, slug in ((" Feat ", "x"), ("feat", ""), ("FEAT", "  ")):
            with self.subTest(kind=kind, slug=slug):
                result = self.srv._change_create_response(self.root, kind, slug, mode="create")
                self.assertEqual([d["code"] for d in result["diagnostics"]], ["change_kind_retired"])
                self.assertEqual(result["data"]["kind"], "feat")
        self.assertFalse(_plans_dir(self.root).exists())

    def test_dry_run_is_refused_too(self):
        result = self.srv._change_create_response(self.root, "feat", "x", mode="dry_run")
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["change_kind_retired"])
        self.assertEqual(result["data"]["mode"], "dry_run")


class CliRefusalTests(unittest.TestCase):
    """AC-2: ``lifecycle_id --kind feat`` exits 2 naming the replacement."""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            return subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_ROOT / "lifecycle_id.py"), *args],
                cwd=str(root), env=env, capture_output=True, text=True, timeout=120,
            )

    def test_feat_exits_2_with_the_message(self):
        done = self._run("--kind", "feat", "--slug", "x")
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertEqual(done.stdout, "")
        self.assertIn(f"lifecycle_id: error: {vocabulary_profile.retired_kind_message('feat')}", done.stderr)

    def test_the_refusal_comes_before_slug_validation(self):
        # An invalid slug with a retired kind reports the retirement, not the
        # slug: the refusal runs before build_id validates or mints anything.
        done = self._run("--kind", "feat", "--slug", "Bad Slug")
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn(vocabulary_profile.retired_kind_message("feat"), done.stderr)
        self.assertNotIn("slug", done.stderr.replace(vocabulary_profile.retired_kind_message("feat"), ""))

    def test_enh_still_mints(self):
        done = self._run("--kind", "enh", "--slug", "x")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertRegex(done.stdout.strip(), r"^[0-9a-z]{5,6}-enh x$")

    def test_feat_stays_a_parseable_choice(self):
        import lifecycle_id
        self.assertIn("feat", lifecycle_id.KIND_CHOICES)
        self.assertEqual(lifecycle_id.parse_args(["--kind", "feat", "--slug", "x"]).kind, "feat")


class GuidanceTests(unittest.TestCase):
    """AC-4: guidance recommends ``wf_new_enhancement``, not the retired tool."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def test_wf_help_plan_change_recommends_wf_new_enhancement(self):
        workflow = self.srv._help_catalog()["workflows"]["plan_change"]
        self.assertEqual(workflow["recommended_chain"], ["wf_new_enhancement", "wf_get_change", "wf_validate_docs"])
        self.assertEqual(workflow["fallback_tools"], ["wf_new_bug", "wf_new_maintenance", "wf_new_change"])
        self.assertIn("wf_new_enhancement", workflow["next_step"])
        self.assertTrue(workflow["usage"].startswith("wf_new_enhancement("), workflow["usage"])
        self.assertNotIn("wf_new_feature", json.dumps(workflow))

    def test_wf_help_goal_was_renamed_to_plan_change_without_alias(self):
        # Wave 1zyc5: the planning goal is plan_change; the old goal is unknown.
        result = self.srv.wf_help_response("plan_change")
        self.assertEqual(result["data"]["goal"], "plan_change")
        self.assertEqual(result["data"]["recommended_chain"][0], "wf_new_enhancement")
        retired = "plan_" + "feature"
        old = self.srv.wf_help_response(retired)
        self.assertEqual(old["diagnostics"][0]["code"], "unknown_goal")
        self.assertNotIn(retired, self.srv._help_catalog()["workflows"])
        self.assertEqual(self.srv.wf_help_response("")["usage"], "wf_help(goal='plan_change')")
        from framework_files import source_path

        source = source_path("server_impl.py").read_text(encoding="utf-8")
        self.assertNotIn(retired, source)

    def test_wf_list_plans_next_tools_name_wf_new_enhancement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            plans = _plans_dir(root)
            plans.mkdir(parents=True)
            (plans / "1abcd-enh a-plan.md").write_text(
                "# A Plan\n\nOwner: Engineering\nStatus: planned\nLast verified: 2026-10-01\n\n"
                f"{vocabulary_profile.MEMBER_ID_LABEL}: `1abcd-enh a-plan`\n",
                encoding="utf-8",
            )
            result = self.srv.wf_list_plans_response(root)
        self.assertTrue(result["data"]["plans"], result)
        self.assertIn("wf_new_enhancement", result["next_tools"])
        self.assertNotIn("wf_new_feature", result["next_tools"])

    def test_docstrings_name_the_retirement(self):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                mcp = load_thin_runner().build_server(_make_repo(Path(tmp)))
                tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
        except ImportError:
            self.skipTest("mcp package not installed")
        feature = tools["wf_new_feature"].description
        self.assertIn("retired", feature)
        self.assertIn("wf_new_enhancement", feature)
        change = tools["wf_new_change"].description
        prefer = next(line for line in change.splitlines() if "Prefer" in line)
        self.assertNotIn("feat", prefer)
        self.assertIn("enh", prefer)



class SkillGuidanceTests(unittest.TestCase):
    """The shipped wf-plan-change skill offers no retired kind's scaffold."""

    def test_the_plan_change_skill_lists_no_retired_scaffold(self):
        import render_agent_surfaces
        skill = next(s for s in render_agent_surfaces.SKILL_REGISTRY if s.name == "wf-plan-change")
        line = next(l for l in skill.body.splitlines() if "`wf_new_<kind>`" in l)
        scaffolds = [w.strip() for w in line.split("(", 1)[1].split(")", 1)[0].split(",")]
        self.assertIn("enhancement", scaffolds)
        # The retired kind's scaffold word (feat is offered as "feature").
        self.assertNotIn("feature", scaffolds)
        for kind in vocabulary_profile.RETIRED_CHANGE_KINDS:
            self.assertNotIn(kind, scaffolds)


if __name__ == "__main__":
    unittest.main()
