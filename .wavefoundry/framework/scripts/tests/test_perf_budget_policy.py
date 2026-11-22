"""Wave 1seax (1t3zv): the contention-safe budget policy keeps its teeth."""
from __future__ import annotations

import ast
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from perf_budget_policy import (  # noqa: E402
    PERF_BUDGETS,
    PERMISSIVENESS_MAX_RATIO,
    PERMISSIVENESS_MIN_RATIO,
    check_operation_within_budget,
    timing_budget,
)
import perf_budget_policy  # noqa: E402


class MeaningfulSlowdownGuardTests(unittest.TestCase):
    """AC-3 (strengthened by operator review): the guard exercises each REAL
    registered budget, and the permissiveness invariant bounds every budget
    against its isolated reference."""

    def test_injected_slowdown_fails_each_real_budget(self):
        """An injected slowdown just past each ACTUAL threshold fails — the
        10-second line-scan budget included."""
        for operation, entry in PERF_BUDGETS.items():
            with self.subTest(operation=operation):
                with self.assertRaises(AssertionError) as ctx:
                    check_operation_within_budget(
                        self, operation, entry["budget_s"] * 1.1
                    )
                message = str(ctx.exception)
                self.assertIn(f"budget {entry['budget_s']:.3f}s", message)
                self.assertIn(
                    f"{entry['isolated_reference_s']:.3f}s", message
                )
                self.assertIn("regressed", message)

    def test_just_under_each_real_budget_passes(self):
        for operation, entry in PERF_BUDGETS.items():
            with self.subTest(operation=operation):
                check_operation_within_budget(
                    self, operation, entry["budget_s"] * 0.9
                )

    def test_permissiveness_invariant_bounds_every_budget(self):
        """A budget below 3x its isolated reference will flake under
        contention; above 50x it stops guarding regressions. An inflated
        table entry fails HERE."""
        for operation, entry in PERF_BUDGETS.items():
            ratio = entry["budget_s"] / entry["isolated_reference_s"]
            with self.subTest(operation=operation, ratio=round(ratio, 1)):
                self.assertGreaterEqual(ratio, PERMISSIVENESS_MIN_RATIO)
                self.assertLessEqual(ratio, PERMISSIVENESS_MAX_RATIO)

    def test_unregistered_operation_is_rejected(self):
        with self.assertRaises(KeyError):
            check_operation_within_budget(self, "not-a-registered-op", 0.1)

    def test_rebudgeted_tests_consume_the_registered_table(self):
        for name, marker in (
            ("test_indexer.py", '"100K-row drift detection"'),
            ("test_graph_indexer.py", '"20000-def line scan"'),
        ):
            source = (TESTS_DIR / name).read_text(encoding="utf-8")
            self.assertIn("assert_operation_within_budget", source)
            self.assertIn(marker, source)
            self.assertNotIn(
                "isolated_reference_s=", source,
                f"{name} must not carry its own budget numbers — the table is the source",
            )


# Change 242yq: the throughput census. Each row is (file stem, class, test,
# labels in call order); every label is one bypass skip.
CENSUS = (
    ("test_server_context_efficiency", "ContextEfficiencyServerIntegrationTests",
     "test_repeated_warm_estimator_and_projection_budgets",
     ("10-source warm", "50-source warm", "lifecycle flush/projection warm")),
    ("test_server_context_efficiency", "ContextEfficiencyServerIntegrationTests",
     "test_idle_projection_poll_is_bounded_and_does_not_scan_docs", ("1000 idle projection polls",)),
    ("test_memory_eval", "MemoryEvalTests",
     "test_lexical_evaluation_has_registered_contention_safe_budget",
     ("1000-record memory lexical evaluation",)),
    ("test_indexer", "SQLiteDriftDetectionScaleTests", "test_10k_rows_sub_second",
     ("100K-row drift detection",)),
    ("test_indexer", "SQLiteDriftDetectionScaleTests", "test_100k_rows_contention_safe_budget",
     ("100K-row drift detection",)),
    ("test_graph_indexer", "GraphIndexerTests", "test_line_scan_cost_bound_and_build_log",
     ("20000-def line scan",)),
    ("test_lexical_ranking_eval", "ShippedCorpusProbeTests",
     "test_the_whole_calibration_pass_stays_inside_the_runtime_budget", ("calibration pass runtime",)),
    ("test_memory_records", "HotPathBoundedIOTests", "test_warm_path_call_counts_and_latency_are_bounded",
     ("first advisory call", "warm advisory call")),
)

# Complexity, hang and denial-of-service guards: always on, never routed.
GUARDS = (
    ("test_navigation_glob", "test_many_double_star_segments_stay_fast"),
    ("test_extension_tool_modules", "test_call_parsing_is_bounded"),
    ("test_techdocs_audit_lib", "test_the_backtracking_ceiling_is_measured_at_its_own_boundary"),
    ("test_techdocs_audit_lib", "test_adjacent_floating_prefixes_collapse_without_reducing_source_budget"),
    ("test_techdocs_audit_lib", "test_a_subject_that_cannot_name_a_file_is_never_matched"),
    ("test_techdocs_audit_lib", "test_a_pathological_pattern_cannot_wedge_the_matcher"),
    ("test_techdocs_audit_lib", "test_a_symlink_cycle_terminates_in_bounded_time"),
    ("test_scanner_input_limits", "test_decoded_size_just_under_cap_scans_completely_with_full_ruleset"),
    ("test_upgrade_wavefoundry", "test_free_text_placeholders_use_bounded_quantifiers"),
)

HELPER_NAMES = {"timing_budget", "assert_operation_within_budget", "assert_within_budget"}
REASON = "timing-budget bypass: declared by tests/fixtures/profiles/control.json: census control"


def _bypassed(reason=REASON):
    return mock.patch.object(perf_budget_policy, "_timing_budget_bypass_reason", return_value=reason)


def _run_case(case: type) -> "tuple[unittest.TestResult, list[tuple[str, str]]]":
    skips: list[tuple[str, str]] = []

    class Result(unittest.TextTestResult):
        def addSkip(self, test, reason):  # noqa: N802
            super().addSkip(test, reason)
            skips.append((test.id(), reason))

    runner = unittest.TextTestRunner(stream=io.StringIO(), resultclass=Result)
    return runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(case)), skips


class TimingBudgetHelperTests(unittest.TestCase):
    """Change 242yq AC-1 to AC-3: the shared helper and its bypass."""

    def test_without_a_declaration_the_check_runs(self):
        calls = []
        with _bypassed(None):
            timing_budget(self, "ran", lambda: calls.append(1))
            with self.assertRaises(AssertionError):
                timing_budget(self, "fails", lambda: self.assertLess(2.0, 1.0))
        self.assertEqual(calls, [1])

    def test_a_declaration_skips_each_label_and_the_test_continues(self):
        class Mixed(unittest.TestCase):
            def test_mixed(self):
                timing_budget(self, "first", lambda: self.fail("first bound evaluated"))
                timing_budget(self, "second", lambda: self.fail("second bound evaluated"))
                self.assertEqual(1, 2, "non-budget assertion")

        with _bypassed():
            result, skips = _run_case(Mixed)
        prefix = f"{Mixed.__module__}.{Mixed.__qualname__}.test_mixed"
        self.assertEqual(skips, [(f"{prefix} (timing_budget='first')", REASON),
                                 (f"{prefix} (timing_budget='second')", REASON)])
        self.assertEqual(len(result.failures), 1, "the later non-budget assertion still fails")
        self.assertIn("non-budget assertion", result.failures[0][1])

    def test_a_repeated_label_is_refused_with_and_without_a_declaration(self):
        for reason in (None, REASON):
            with self.subTest(declared=reason is not None):
                class Repeat(unittest.TestCase):
                    def test_repeat(self):
                        timing_budget(self, "same", lambda: None)
                        timing_budget(self, "same", lambda: None)

                with _bypassed(reason):
                    result, _ = _run_case(Repeat)
                self.assertEqual(len(result.errors), 1)
                self.assertIn("already used in this test", result.errors[0][1])

    def test_labels_reset_per_test(self):
        class Two(unittest.TestCase):
            def test_a(self):
                timing_budget(self, "shared", lambda: None)

            def test_b(self):
                timing_budget(self, "shared", lambda: None)

        with _bypassed(None):
            result, _ = _run_case(Two)
        self.assertTrue(result.wasSuccessful(), result.errors)

    def test_threshold_core_is_never_bypassed(self):
        entry = PERF_BUDGETS["1000-record memory lexical evaluation"]
        with _bypassed():
            with self.assertRaises(AssertionError):
                check_operation_within_budget(
                    self, "1000-record memory lexical evaluation", entry["budget_s"] * 1.1)
            with self.assertRaises(KeyError):
                perf_budget_policy.assert_operation_within_budget(self, "not-a-registered-op", 0.1)

    def test_registered_operations_skip_under_their_own_name(self):
        class Registered(unittest.TestCase):
            def test_registered(self):
                perf_budget_policy.assert_operation_within_budget(
                    self, "20000-def line scan", 1e9)

        with _bypassed():
            result, skips = _run_case(Registered)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual([sid.split(" (", 1)[1] for sid, _ in skips],
                         ["timing_budget='20000-def line scan')"])


def _function(stem: str, name: str) -> "tuple[ast.Module, ast.FunctionDef]":
    tree = ast.parse((TESTS_DIR / f"{stem}.py").read_text(encoding="utf-8"))
    found = [node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(found) != 1:
        raise AssertionError(f"{stem}.py defines {name} {len(found)} times")
    return tree, found[0]


def _called_names(node: ast.AST) -> "set[str]":
    names = set()
    for call in ast.walk(node):
        if isinstance(call, ast.Call):
            func = call.func
            names.add(func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", ""))
    return names


def _routes(stem: str, name: str) -> bool:
    """Whether the test body, or a ``self._helper`` it calls in the same
    file, calls the shared helper."""
    tree, func = _function(stem, name)
    called = _called_names(func)
    if called & HELPER_NAMES:
        return True
    for helper in sorted(n for n in called if n.startswith("_")):
        defs = [node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == helper]
        if any(_called_names(d) & HELPER_NAMES for d in defs):
            return True
    return False


class TimingBudgetCensusPinTests(unittest.TestCase):
    """Change 242yq Requirement 8: the census tests route through the
    helper; the always-on guards do not."""

    def test_every_census_test_calls_the_helper(self):
        for stem, _cls, name, _labels in CENSUS:
            with self.subTest(test=f"{stem}::{name}"):
                self.assertTrue(_routes(stem, name), "census test no longer calls the helper")

    def test_no_guard_test_calls_the_helper(self):
        for stem, name in GUARDS:
            with self.subTest(test=f"{stem}::{name}"):
                self.assertFalse(_routes(stem, name), "a guard must stay always on")

    def test_the_pin_detects_unrouting_and_routing(self):
        unrouted = ast.parse("def test_x(self):\n    self.assertLess(1, 2)\n").body[0]
        routed = ast.parse("def test_y(self):\n    timing_budget(self, 'l', lambda: None)\n").body[0]
        self.assertFalse(_called_names(unrouted) & HELPER_NAMES)
        self.assertTrue(_called_names(routed) & HELPER_NAMES)


_CENSUS_RUNNER = r"""
import io, json, os, sys, unittest
tests_dir, mode, rows = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
sys.path[:0] = [tests_dir, os.path.dirname(tests_dir)]
import test_worker_guard
test_worker_guard.install()
import perf_budget_policy
modules = [perf_budget_policy]
try:
    import tests.perf_budget_policy as packaged
    modules.append(packaged)
except ImportError:
    pass
REASON = %r
skips = []
class Result(unittest.TextTestResult):
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        skips.append([test.id(), reason])
def run(test_id):
    suite = unittest.defaultTestLoader.loadTestsFromName(test_id)
    return unittest.TextTestRunner(stream=io.StringIO(), resultclass=Result).run(suite)
out = []
for test_id, count in rows:
    for forced in ([0] if mode == "bypass" else range(1, count + 1)):
        state = {"calls": 0}
        def reader(forced=forced, state=state):
            state["calls"] += 1
            if mode == "bypass":
                return REASON
            if state["calls"] == forced:
                raise AssertionError("forced timing budget call %%d" %% forced)
            return None
        for module in modules:
            module._timing_budget_bypass_reason = reader
        result = run(test_id)
        out.append({"id": test_id, "forced": forced, "calls": state["calls"],
                    "failures": [text[-400:] for _, text in result.failures],
                    "errors": [text[-400:] for _, text in result.errors]})
print("CENSUS-RESULT:" + json.dumps({"runs": out, "skips": skips}))
""" % (REASON,)


class TimingBudgetCensusRunTests(unittest.TestCase):
    """Change 242yq AC-1 and AC-2, run on the real census tests in a child."""

    def _run(self, mode: str) -> dict:
        rows = [[f"{stem}.{cls}.{name}", len(labels)] for stem, cls, name, labels in CENSUS]
        done = subprocess.run(
            [sys.executable, "-B", "-c", _CENSUS_RUNNER, str(TESTS_DIR), mode,
             json.dumps(rows)],
            cwd=str(TESTS_DIR.parent), capture_output=True, text=True, timeout=540)
        line = [x for x in done.stdout.splitlines() if x.startswith("CENSUS-RESULT:")]
        self.assertEqual(len(line), 1, done.stdout[-2000:] + done.stderr[-2000:])
        return json.loads(line[0][len("CENSUS-RESULT:"):])

    def test_default_run_executes_each_bound_through_the_helper(self):
        # AC-1: failing the helper at call n fails that test at call n.
        data = self._run("force")
        for run in data["runs"]:
            with self.subTest(test=run["id"], forced=run["forced"]):
                problems = run["failures"] + run["errors"]
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(f"forced timing budget call {run['forced']}", problems[0])
        self.assertEqual(data["skips"], [], "the default path reports no bypass skip")

    def test_declared_bypass_skips_exactly_the_census_labels(self):
        # AC-2: the exact 11 skips, with the reason, and no failure.
        data = self._run("bypass")
        expected = sorted([f"{stem}.{cls}.{name} (timing_budget={label!r})", REASON]
                          for stem, cls, name, labels in CENSUS for label in labels)
        self.assertEqual(sorted(data["skips"]), expected)
        self.assertEqual(len(expected), 11)
        for run in data["runs"]:
            with self.subTest(test=run["id"]):
                self.assertEqual(run["failures"] + run["errors"], [])


if __name__ == "__main__":
    unittest.main()
