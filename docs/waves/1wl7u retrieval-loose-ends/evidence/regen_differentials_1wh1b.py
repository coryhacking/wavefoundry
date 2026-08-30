"""Versioned differential-fixture regeneration for change 1wh1b-enh (wave 1wl7u).

Requirement 5: the notebook doc-code routing and the repeat-only prose-id
ordinals change the chunk-set shape, so the markdown byte-identity
differential regenerates as a deliberate versioned step. The prepare council
proved the existing sources are BLIND to both declared delta classes (no
duplicate titles, no notebooks), so this regeneration ADDS one
duplicate-titled markdown source and one notebook source; without them the
classify-every-changed-row exercise is vacuous.

Contract:
  * the three pre-existing sources must chunk BYTE-IDENTICALLY old-vs-new
    (single-title dominant case; any delta there blocks);
  * every differing row on the added sources must classify into exactly the
    declared classes — ``notebook-cell-kind`` (kind code -> doc-code, plus
    the breadcrumb-injection text prefix that rides the kind) and
    ``repeat-title-ordinal-id`` (bare base -> ``~k`` base); any unclassified
    delta blocks (exit nonzero, writes nothing);
  * discrimination / revert-simulation: the regenerated expected snapshot
    must MISMATCH the pre-change chunker's output on the added sources
    (nonzero classified deltas), proving the re-armed differential fails if
    the chunker reverts;
  * the specs-negatives differential is asserted ZERO-DELTA old-vs-new (no
    negative is a notebook or duplicate-titled prose doc).

The pre-change chunker is loaded from ``git show HEAD:...chunker.py`` (the
wave's edits are uncommitted, so HEAD is the shipped 1.20.0 chunker v37).

MUST run under the tool venv from the repository root:
    ~/.wavefoundry/venv/bin/python "docs/waves/1wl7u retrieval-loose-ends/evidence/regen_differentials_1wh1b.py" [--write]

Prints the classified diff report to stdout; rewrites the committed fixture
files ONLY with --write (QA-DEL-1: bare re-runs never clobber committed
artifacts).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
FIXTURES = SCRIPTS / "tests" / "fixtures" / "retrieval_golden"
sys.path.insert(0, str(SCRIPTS))

import chunker as new_chunker  # noqa: E402

_TILDE_BASE_RE = re.compile(r"~\d+")

DUP_MD_SOURCE = {
    "path": "docs/team-guide.md",
    "source": (
        "# Team Guide\n\n"
        "## Setup\n\nFirst onboarding steps.\n\n"
        "```bash\nteamctl init --profile default\n```\n\n"
        "## Setup\n\nDuplicate-titled second setup section.\n\n"
        "```bash\nteamctl init --profile shared\n```\n\n"
        "## Setup 2\n\nA literal title that slugifies into the -2 tail.\n"
    ),
}

NB_SOURCE = {
    "path": "docs/metrics-notebook.ipynb",
    "source": json.dumps({
        "cells": [
            {"cell_type": "markdown",
             "source": ["# Metrics Walkthrough\n", "Weekly rollup notes.\n"]},
            {"cell_type": "code",
             "source": ["rollup = aggregate_weekly(events)\n"],
             "outputs": [{"output_type": "stream",
                          "text": ["UNINDEXED_OUTPUT_SENTINEL\n"]}]},
            {"cell_type": "code",
             "source": ["publish_dashboard(rollup)\n"],
             "outputs": []},
        ],
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }),
}


def _load_old_chunker():
    blob = subprocess.run(
        ["git", "show", "HEAD:.wavefoundry/framework/scripts/chunker.py"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix="_old_chunker.py", delete=False, encoding="utf-8")
    tmp.write(blob)
    tmp.close()
    spec = importlib.util.spec_from_file_location("old_chunker", tmp.name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["old_chunker"] = mod  # dataclass decorator resolves __module__
    spec.loader.exec_module(mod)
    return mod


def _rows(mod, sources: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for entry in sources:
        for c in mod.chunk_file(entry["source"], entry["path"]):
            rows.append(c.to_dict())
    return rows


def _classify(old: dict, new: dict) -> str | None:
    """Return the delta class for one changed row pair, or None."""
    if new["path"].endswith(".ipynb"):
        # notebook-cell-kind: code -> doc-code; text may gain the injected
        # section-breadcrumb prefix that rides the docs-kind membership.
        stripped = new["text"]
        section = (new.get("section") or "")
        if section and stripped.startswith(section + "\n"):
            stripped = stripped[len(section) + 1:]
        if (old["kind"] == "code" and new["kind"] == "doc-code"
                and old["id"] == new["id"]
                and stripped == old["text"]):
            return "notebook-cell-kind"
        return None
    # repeat-title-ordinal-id: identical row except the id base gains ~k.
    if (old["kind"] == new["kind"] and old["text"] == new["text"]
            and old["id"] != new["id"]
            and _TILDE_BASE_RE.sub("", new["id"]) == old["id"]):
        return "repeat-title-ordinal-id"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    old_chunker = _load_old_chunker()
    report: dict = {
        "old_chunker_version": old_chunker.CHUNKER_VERSION,
        "new_chunker_version": new_chunker.CHUNKER_VERSION,
    }

    base_sources = json.loads(
        (FIXTURES / "markdown_differential_sources.json").read_text(
            encoding="utf-8"))
    # Idempotent re-runs: strip any previously-added 1wh1b sources first.
    added_paths = {DUP_MD_SOURCE["path"], NB_SOURCE["path"]}
    base_sources = [e for e in base_sources if e["path"] not in added_paths]
    extended = base_sources + [DUP_MD_SOURCE, NB_SOURCE]

    # 1. Pre-existing sources: byte-identical old vs new.
    old_base = _rows(old_chunker, base_sources)
    new_base = _rows(new_chunker, base_sources)
    report["preexisting_sources_byte_identical"] = old_base == new_base
    if old_base != new_base:
        print(json.dumps(report, indent=2))
        print("BLOCKED: pre-existing single-title sources changed", file=sys.stderr)
        return 1

    # 2. Added sources: classify every changed row.
    old_added = _rows(old_chunker, [DUP_MD_SOURCE, NB_SOURCE])
    new_added = _rows(new_chunker, [DUP_MD_SOURCE, NB_SOURCE])
    classes: dict[str, int] = {}
    unclassified: list = []
    if len(old_added) != len(new_added):
        unclassified.append(
            f"row count changed {len(old_added)} -> {len(new_added)}")
    else:
        for o, n in zip(old_added, new_added):
            if o == n:
                continue
            cls = _classify(o, n)
            if cls is None:
                unclassified.append({"old": o["id"], "new": n["id"],
                                     "old_kind": o["kind"], "new_kind": n["kind"]})
            else:
                classes[cls] = classes.get(cls, 0) + 1
    report["classified_deltas"] = classes
    report["unclassified_deltas"] = unclassified

    # 3. Discrimination / revert-simulation: the re-armed snapshot must
    # mismatch the pre-change chunker on the added sources.
    both_classes_present = (
        classes.get("notebook-cell-kind", 0) > 0
        and classes.get("repeat-title-ordinal-id", 0) > 0
    )
    report["revert_simulation_detects_mismatch"] = (
        old_added != new_added and both_classes_present)

    # 4. Specs-negatives: zero delta old vs new over the committed corpus.
    negatives = json.loads(
        (FIXTURES / "specs_negatives_differential_expected.json").read_text(
            encoding="utf-8"))
    neg_delta = []
    for rel in negatives:
        src = (FIXTURES / "specs" / rel).read_text(encoding="utf-8")
        o = [c.to_dict() for c in old_chunker.chunk_file(src, rel)]
        n = [c.to_dict() for c in new_chunker.chunk_file(src, rel)]
        if o != n:
            neg_delta.append(rel)
    report["specs_negatives_zero_delta"] = not neg_delta
    report["specs_negatives_changed"] = neg_delta

    ok = (not unclassified and both_classes_present
          and report["revert_simulation_detects_mismatch"] and not neg_delta)
    report["result"] = "PASS" if ok else "BLOCKED"
    print(json.dumps(report, indent=2))
    if not ok:
        return 1

    if args.write:
        (FIXTURES / "markdown_differential_sources.json").write_text(
            json.dumps(extended, indent=2) + "\n", encoding="utf-8")
        expected = _rows(new_chunker, extended)
        (FIXTURES / "markdown_differential_expected.json").write_text(
            json.dumps(expected, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE {len(extended)} sources, {len(expected)} expected rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
