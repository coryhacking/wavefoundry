#!/usr/bin/env python3
"""``wf techdocs-audit`` — audit the TechDocs publication surface (wave 1vqqi).

A thin CLI entry (the ``gpu_doctor.py`` / ``techdocs_baseline.py`` pattern) over
``techdocs_audit_lib.run_techdocs_audit``: it parses ``--root`` / ``--json`` /
``--compare-to`` and formats the typed report. All behavior lives in the library
so the MCP tool and this entry observe one patch; the bounded runner's private
worker calls the raw ``audit_techdocs`` implementation. The entry never writes.

Exit codes follow the report's CONTENT, not its verdict: 1 whenever any finding
is present or the run degraded so that something could not be computed, 2 when
the audit could not run, and 0 otherwise. ``not_applicable`` (no ``mkdocs.yml``)
is a legitimate state rather than a failure, so on its own it exits 0 -- but it
is a forced verdict that wins over accumulated findings, so it does NOT suppress
an exit 1 when the trio checks still found something.

This deliberately differs from the sibling ``wf techdocs-baseline``, where 1
means precondition-unmet: there, 1 is a refusal; here, 1 is an informative
result. Text mode prints ``techdocs-audit: <severity> <code> <path>: <detail>``,
with `` -> <href>`` after the path whenever the finding carries one
per finding plus a one-line summary on stdout, with degrade reasons as
``techdocs-audit: NOTE ...`` on stderr; ``--json`` prints the report envelope on
stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

venv_bootstrap.activate_tool_venv()
cli_stdio.configure_utf8_stdio()

_PREFIX = "techdocs-audit"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="wf techdocs-audit",
        description=(
            "Audit the TechDocs publication surface: the mkdocs.yml boundary, nav targets, "
            "relative links that dangle or escape it, published-page metadata, the "
            "Backstage/TechDocs trio's ownership, and the agent startup-order audience invariant. "
            "Reads only; gates nothing."
        ),
    )
    parser.add_argument("--root", default="", help="Repository root (default: discovered from the cwd).")
    parser.add_argument(
        "--json", action="store_true",
        help="Print the report envelope on stdout instead of the text summary.",
    )
    parser.add_argument(
        "--compare-to", default="",
        help=(
            "Git ref for the audience baseline (default HEAD). The default is an identity check on a "
            "clean tree and is reported as such; pass an explicit ref for the historical question."
        ),
    )
    return parser.parse_args(argv)


def _emit_text(report) -> None:
    for finding in report.findings:
        href = f" -> {finding.href}" if finding.href else ""
        print(f"{_PREFIX}: {finding.severity} {finding.code} {finding.path}{href}: {finding.detail}")
    summary = report.summary
    publication = report.publication or {}
    print(
        f"{_PREFIX}: {summary['verdict']}; {summary['finding_count']} finding(s) over "
        f"{publication.get('survivor_count', 0)} published page(s)"
    )
    for reason in report.degraded:
        print(f"{_PREFIX}: NOTE degraded: {reason}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))

    from techdocs_audit_lib import (
        DEGRADE_MKDOCS_ABSENT,
        run_techdocs_audit,
    )

    # Root resolution sits INSIDE the try: `expanduser()` raises RuntimeError for
    # an unknown user (`~nosuchuser/x`), and it sat outside, so the entry that
    # promises an exit code emitted a traceback instead.
    try:
        if args.root:
            repo_root = Path(args.root).expanduser().resolve()
        else:
            from render_platform_surfaces import discover_repo_root

            repo_root = discover_repo_root()
        report = run_techdocs_audit(repo_root, compare_to=args.compare_to or None)
    except (RuntimeError, OSError, ValueError, re.error) as exc:
        print(f"{_PREFIX}: ERROR the audit could not run: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        for reason in report.degraded:
            print(f"{_PREFIX}: NOTE degraded: {reason}", file=sys.stderr)
    else:
        _emit_text(report)

    # Content, not verdict. `not_applicable` is a forced verdict that wins over
    # accumulated findings, so keying the exit code on the verdict made a repo
    # with a partial trio and an unauthored landing page exit 0 while both of
    # the documented exit-1 conditions held. A gate-shaped consumer chaining on
    # exit status would have read that as a pass.
    beyond_not_applicable = [d for d in report.degraded if d != DEGRADE_MKDOCS_ABSENT]
    return 1 if report.findings or beyond_not_applicable else 0


if __name__ == "__main__":  # pragma: no cover - thin entry
    raise SystemExit(main())
