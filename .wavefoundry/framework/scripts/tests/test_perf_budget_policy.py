"""Wave 1seax (1t3zv): the contention-safe budget policy keeps its teeth."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from perf_budget_policy import (  # noqa: E402
    PERF_BUDGETS,
    PERMISSIVENESS_MAX_RATIO,
    PERMISSIVENESS_MIN_RATIO,
    assert_operation_within_budget,
    assert_within_budget,
)


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
                    assert_operation_within_budget(
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
                assert_operation_within_budget(
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
            assert_operation_within_budget(self, "not-a-registered-op", 0.1)

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


if __name__ == "__main__":
    unittest.main()
