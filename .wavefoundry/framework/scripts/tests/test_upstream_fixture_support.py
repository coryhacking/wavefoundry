"""Tests for the upstream-only fixture helper (change 21ile)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for entry in (str(TESTS_DIR), str(SCRIPTS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import upstream_fixture_support as ufs  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[4]
# The routed fixture the known-bad control uses. Where it is genuinely absent
# (a distribution), the source-repository pins below skip through the helper.
ROUTED_FIXTURE = REPO_ROOT / "docs/agents/history/operating-memory-2026-07-22.md"


class UnexpectedSkip(Exception):
    """Not an AssertionError, so ``assertRaises(AssertionError)`` cannot absorb it."""


class UpstreamFixtureHelperTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "docs").mkdir()
        self.absent = self.root / "docs" / "evals" / "absent.json"

    def _config(self, text: "str | None") -> None:
        path = self.root / ufs.CONFIG_REL
        if text is not None:
            path.write_text(text, encoding="utf-8")

    def _config_obj(self, obj) -> None:
        self._config(json.dumps(obj))

    def _call(self, path):
        """Call the helper; a skip where none is expected fails rather than skips."""
        try:
            return ufs.upstream_fixture(path, root=self.root)
        except unittest.SkipTest as exc:
            raise UnexpectedSkip(f"unexpected skip: {exc}") from None

    def test_a_present_path_is_returned(self):
        present = self.root / "docs" / "present.json"
        present.write_text("{}", encoding="utf-8")
        self._config(None)  # never consulted for a present fixture
        self.assertEqual(present, self._call(present))
        self.assertEqual(present, self._call(str(present)))

    def test_absent_with_the_key_true_fails(self):
        self._config_obj({"testing": {"upstream_fixtures_required": True}})
        with self.assertRaises(AssertionError) as ctx:
            self._call(self.absent)
        self.assertIn(str(self.absent), str(ctx.exception))
        self.assertIn("upstream_fixtures_required is true", str(ctx.exception))

    def test_absent_with_the_key_absent_or_false_skips(self):
        for config in ({}, {"testing": {}}, {"testing": {"upstream_fixtures_required": False}}):
            with self.subTest(config=config):
                self._config_obj(config)
                with self.assertRaises(unittest.SkipTest) as ctx:
                    ufs.upstream_fixture(self.absent, root=self.root)
                self.assertEqual(f"upstream-only fixture absent: {self.absent}",
                                 str(ctx.exception))

    def test_absent_with_a_bad_config_fails_naming_path_and_cause(self):
        cases = {
            "missing": (None, "is missing"),
            "malformed": ("{not json", "is not valid JSON"),
            "non_object_root": ("[]", "must be a JSON object"),
            "non_object_testing": (json.dumps({"testing": True}), "testing must be an object"),
            "non_boolean_key": (json.dumps({"testing": {"upstream_fixtures_required": "yes"}}),
                                "must be a boolean"),
            "null_key": (json.dumps({"testing": {"upstream_fixtures_required": None}}),
                         "must be a boolean"),
        }
        for name, (text, cause) in cases.items():
            with self.subTest(case=name):
                config = self.root / ufs.CONFIG_REL
                config.unlink(missing_ok=True)
                self._config(text)
                with self.assertRaises(AssertionError) as ctx:
                    self._call(self.absent)
                self.assertIn(str(self.absent), str(ctx.exception))
                self.assertIn(cause, str(ctx.exception))

    def test_a_missing_config_fails_closed_unlike_the_docs_lint_opt_in(self):
        # Deliberate opposite of docs-lint's _framework_internal_constants_enabled,
        # which reads a missing config as "off". Here "off" would mean a silent skip.
        import wave_lint_lib.docs_constants_validators as dcv
        enabled, failures = dcv._framework_internal_constants_enabled(self.root)
        self.assertEqual((False, []), (enabled, failures))
        self.assertEqual(None, ufs.fixtures_required(self.root)[0])
        with self.assertRaises(AssertionError):
            self._call(self.absent)

    def test_the_default_root_is_derived_from_the_helper_file_not_the_cwd(self):
        self.assertEqual(REPO_ROOT, ufs.REPO_ROOT)
        self.assertTrue((ufs.REPO_ROOT / ".wavefoundry" / "framework" / "scripts").is_dir())


class InstallDefaultsTests(unittest.TestCase):
    def test_install_defaults_never_carry_a_testing_key(self):
        # A defaults edit must not seed the source-repository opt-in into consumers.
        defaults = REPO_ROOT / ".wavefoundry" / "framework" / "install" / "workflow-config.defaults.json"
        data = json.loads(defaults.read_text(encoding="utf-8"))
        self.assertNotIn("testing", data)


class SourceRepositoryOptInTests(unittest.TestCase):
    """Pins that hold only where the upstream fixtures are hosted.

    ``setUp`` skips them only where the real fixture is absent and the opt-in
    is off (a distribution); this repository proceeds to the pins.
    """

    def setUp(self):
        # Decided independently of the helper under test, so a helper that
        # always skipped could not skip these pins too.
        if not ROUTED_FIXTURE.is_file():
            self.assertIs(False, ufs.fixtures_required()[0],
                          f"{ROUTED_FIXTURE} is absent where the opt-in is not off")
            self.skipTest(f"{ufs.SKIP_PREFIX}{ROUTED_FIXTURE}")

    def test_this_repository_sets_the_opt_in_true(self):
        # AC-3: without this pin a removed key would turn every routed read
        # here into a silent skip.
        data = json.loads((REPO_ROOT / ufs.CONFIG_REL).read_text(encoding="utf-8"))
        self.assertIs(True, data.get("testing", {}).get("upstream_fixtures_required"))
        self.assertEqual((True, ""), ufs.fixtures_required())

    def test_a_routed_test_fails_rather_than_skips_when_its_fixture_is_absent_here(self):
        # AC-2 known-bad: make one routed fixture absent to the helper's own
        # existence probe; with this repository's opt-in the routed test fails.
        # A helper that skipped unconditionally would fail this test.
        import test_events_only_residue_census as routed
        case = routed.LocalRoleHistoryCensusTests(
            "test_journal_payload_only_in_bounded_history")
        result = unittest.TestResult()
        with mock.patch.object(ufs, "_exists", return_value=False):
            case.run(result)
        self.assertEqual(1, result.testsRun)
        self.assertEqual([], result.skipped)
        self.assertEqual([], result.errors)
        self.assertEqual(1, len(result.failures))
        self.assertIn(f"upstream-only fixture absent: {ROUTED_FIXTURE}",
                      result.failures[0][1])


if __name__ == "__main__":
    unittest.main()
