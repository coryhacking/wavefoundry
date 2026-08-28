"""Content-coverage differential for change 1whup-enh (wave 1wik9), AC-4.

Procedural oracle (Requirement 6): per-line coverage classification of
DOCS-TABLE-ELIGIBLE chunk content, new chunker versus the pre-change chunker,
over the markdown differential-source fixtures plus one fixture per
census-enumerated emission site (markdown doc, markdown prompt, rst, adoc,
notebook). A nonblank source line is COVERED when its stripped content appears
in at least one docs-table-eligible chunk's text. The pre-change surface is
reconstructed exactly as in baseline_prechange_driver.py: the classified
regeneration diff proved v35 prose rows are byte-identical to v34 and the only
delta rows are the fences themselves, which at v34 were kind="code" and
docs-table-INELIGIBLE — so v35 output minus doc-code IS the v34 docs surface.

Checks:
1. NO-LOSS: every line covered pre-change stays covered post-change, per
   fixture (the 1wfsl ARCH-DEL-1 invariant; golden sets cannot see this).
2. GAIN: each fixture with extractable code content has at least one
   previously-uncovered line covered post-change (fence lines reached the
   docs surface), except the prompt and notebook fixtures whose preserved
   behavior is pinned (prompt fences were ALREADY covered inline; notebook
   code cells stay uncovered by recorded disposition).
3. NON-VACUOUS (revert-simulation): recomputing with doc-code treated as
   ineligible again must make the differential DETECT the loss.

Run under the tool venv from the repository root:
    ~/.wavefoundry/venv/bin/python "docs/waves/1wik9 fenced-diagram-and-spec-retrieval/evidence/coverage_differential_1whup.py" [--out <file.json>]

Prints the report; writes ONLY with --out. Exits nonzero on any check failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
FIXTURES = SCRIPTS / "tests" / "fixtures" / "retrieval_golden"
sys.path.insert(0, str(SCRIPTS))

import chunker  # noqa: E402
import indexer  # noqa: E402

DOCS_KINDS_POST = tuple(
    k for k in ("doc", "seed", "prompt", "doc-summary", "doc-code")
    if indexer._is_docs_kind(k)
)
DOCS_KINDS_PRE = tuple(k for k in DOCS_KINDS_POST if k != "doc-code")

MD_DOC = (
    "Preamble prose.\n\n"
    "```ini\npreamble_setting = true\n```\n\n"
    "# Widget Guide\n\n"
    "## Install\n\nRun the installer.\n\n"
    "```bash\nwidgetctl install --profile default\n```\n\n"
    "## Install\n\nSecond duplicate-titled section.\n\n"
    "```python\nimport widget\n```\n"
)
MD_PROMPT = "# Prompt Doc\n\n## Step\n\nRun this:\n\n```bash\nrun --step one\n```\n"
RST_DOC = (
    "Guide\n=====\n\nUsage\n-----\n\nProse here.\n\n"
    ".. code-block:: python\n\n   configure(retries=3)\n"
)
ADOC_DOC = (
    "= Guide\n\n== Usage\n\nProse here.\n\n"
    "[source,python]\n----\nconfigure(retries=3)\n----\n"
)
IPYNB_DOC = json.dumps({
    "cells": [
        {"cell_type": "markdown", "source": ["# Notebook\n", "Prose cell.\n"]},
        {"cell_type": "code", "source": ["compute_answer(42)\n"], "outputs": []},
    ],
    "metadata": {}, "nbformat": 4, "nbformat_minor": 5,
})

# (path, source, expects_gain) — prompt keeps inline coverage (no gain
# expected), notebook keeps its recorded dropped state (no gain expected).
EMISSION_FIXTURES = [
    ("docs/guide.md", MD_DOC, True),
    ("docs/prompts/step.prompt.md", MD_PROMPT, False),
    ("docs/guide.rst", RST_DOC, True),
    ("docs/guide.adoc", ADOC_DOC, True),
    ("docs/analysis.ipynb", IPYNB_DOC, False),
]

STRUCTURAL = frozenset({"```", "----", "....", "|===", "====", "-----"})


def _content_lines(source: str, path: str) -> list[str]:
    """Nonblank, non-structural source lines (stripped). For notebooks the
    raw JSON lines are not prose; classify over the cell sources instead."""
    if path.endswith(".ipynb"):
        nb = json.loads(source)
        lines = []
        for cell in nb.get("cells", []):
            lines.extend("".join(cell.get("source", [])).splitlines())
    else:
        lines = source.splitlines()
    out = []
    for raw in lines:
        s = raw.strip()
        if not s or s in STRUCTURAL or s.startswith("```"):
            continue
        out.append(s)
    return out


def _covered(lines: list[str], corpus: str) -> set[str]:
    return {ln for ln in lines if ln in corpus}


def classify(path: str, source: str, kinds: tuple[str, ...]) -> set[str]:
    chunks = chunker.chunk_file(source, path)
    corpus = "\n".join(c.text for c in chunks if c.kind in kinds)
    return _covered(_content_lines(source, path), corpus)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    sources = json.loads(
        (FIXTURES / "markdown_differential_sources.json").read_text(
            encoding="utf-8"))
    cases = [(e["path"], e["source"], None) for e in sources]
    cases += EMISSION_FIXTURES

    report: dict = {
        "differential": "1whup AC-4 per-line docs-table content-coverage",
        "chunker_version": chunker.CHUNKER_VERSION,
        "docs_kinds_post": list(DOCS_KINDS_POST),
        "docs_kinds_pre": list(DOCS_KINDS_PRE),
        "fixtures": [], "failures": [],
    }
    for path, source, expects_gain in cases:
        lines = _content_lines(source, path)
        pre = classify(path, source, DOCS_KINDS_PRE)
        post = classify(path, source, DOCS_KINDS_POST)
        lost = sorted(pre - post)
        gained = sorted(post - pre)
        row = {
            "path": path, "content_lines": len(lines),
            "covered_pre": len(pre), "covered_post": len(post),
            "lost_lines": lost, "gained_lines": gained,
        }
        if lost:
            report["failures"].append(f"{path}: coverage LOST for {lost}")
        if expects_gain is True and not gained:
            report["failures"].append(
                f"{path}: expected previously-dropped code lines to gain "
                f"docs-table coverage; none did")
        if expects_gain is False and gained:
            report["failures"].append(
                f"{path}: preserved-behavior fixture unexpectedly gained "
                f"coverage: {gained}")
        report["fixtures"].append(row)

    # Revert-simulation: with doc-code ineligible again, the differential must
    # DETECT the loss on every gain-expected fixture.
    detected = 0
    for path, source, expects_gain in EMISSION_FIXTURES:
        if not expects_gain:
            continue
        post = classify(path, source, DOCS_KINDS_POST)
        reverted = classify(path, source, DOCS_KINDS_PRE)
        if post - reverted:
            detected += 1
    expected_detections = sum(1 for _, _, g in EMISSION_FIXTURES if g)
    report["revert_simulation"] = {
        "detected_loss_on": detected, "expected": expected_detections,
        "non_vacuous": detected == expected_detections and detected > 0,
    }
    if not report["revert_simulation"]["non_vacuous"]:
        report["failures"].append("revert-simulation failed to detect loss")

    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        Path(__file__).with_name(args.out).write_text(text + "\n",
                                                      encoding="utf-8")
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
