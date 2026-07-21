"""Contention-safe performance-budget policy (wave 1seax / 1t3zv).

The framework suite runs up to six parallel workers; back-to-back runs
saturate the machine, and tight wall-clock budgets then flake on scheduler
contention even though the measured operation is healthy (recorded: a 120 ms
isolated result failing a 200 ms budget; a 240 ms isolated result failing a
3 s budget at 3.2 s contended).

Policy for any NEW wall-clock budget in the suite:

1. Record an ISOLATED reference measurement and, when available, a contended
   one (after sustained six-worker activity).
2. Set the budget with measured contention headroom — at least ~3x the worst
   observed contended time — while staying at least an order of magnitude
   under a genuine regression of the guarded operation.
3. Assert through :func:`assert_within_budget` so failures report the
   observed timing, the threshold, and the isolated reference (the triage
   signal separating contention from regression).
4. Prefer RELATIVE bounds (ratio of two timings measured in the same run)
   where the invariant allows — they are contention-immune by construction.

Do not globally serialize the suite and do not inflate budgets without the
measured basis.
"""
from __future__ import annotations


# Canonical per-operation budget table (operator-review repair): the SINGLE
# source both rebudgeted tests and the meaningful-slowdown guard consume, so
# the guard always exercises the REAL thresholds. Ratios are bounded by the
# permissiveness invariant below: an inflated budget fails the guard.
PERF_BUDGETS: dict[str, dict[str, float]] = {
    "100K-row drift detection": {
        "budget_s": 1.0,
        # isolated 0.120s / worst contended 0.276s (six-worker suite, 2026-07-20)
        "isolated_reference_s": 0.120,
    },
    "20000-def line scan": {
        "budget_s": 10.0,
        # isolated 0.240s / worst contended 3.215s (six-worker suite, 2026-07-20)
        "isolated_reference_s": 0.240,
    },
}

# Permissiveness invariant: every budget stays within [3x, 50x] of its
# isolated reference — below 3x it will flake under contention; above 50x it
# stops being a regression guard.
PERMISSIVENESS_MIN_RATIO = 3.0
PERMISSIVENESS_MAX_RATIO = 50.0


def assert_operation_within_budget(testcase, operation: str, elapsed_s: float) -> None:
    """Budget assertion for a REGISTERED operation — the table is the source."""
    entry = PERF_BUDGETS[operation]
    assert_within_budget(
        testcase, elapsed_s, entry["budget_s"],
        operation=operation,
        isolated_reference_s=entry["isolated_reference_s"],
    )


def assert_within_budget(
    testcase,
    elapsed_s: float,
    budget_s: float,
    *,
    operation: str,
    isolated_reference_s: float,
) -> None:
    """Budget assertion with contention-aware diagnostics."""
    testcase.assertLess(
        elapsed_s,
        budget_s,
        (
            f"{operation} took {elapsed_s:.3f}s (budget {budget_s:.3f}s; isolated "
            f"reference {isolated_reference_s:.3f}s). If the isolated rerun is near "
            "the reference, this failure was scheduler contention under parallel "
            "suite workers; if the isolated rerun also exceeds the budget, the "
            "operation regressed."
        ),
    )
