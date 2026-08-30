"""Per-line content-coverage differential for change 1wh1b-enh (wave 1wl7u).

Requirement 6 (standing ARCH-DEL-1 criterion): golden sets alone cannot see
coverage loss, so this differential proves, over notebook and
duplicate-titled fixtures, that

  1. no file loses per-line coverage relative to the pre-change chunker —
     every non-blank source line covered by ANY old chunk stays covered by
     a new chunk;
  2. previously-dropped notebook code-cell content appears in
     docs-table-eligible chunks (it was in NO table before: kind="code"
     from a never-code-eligible .ipynb);
  3. duplicate-titled prose content SURVIVES the id-keyed collapse: the
     coverage is computed over the chunks that survive a dict-by-id pass
     (the _plan_lance_delta_rows / registry-upsert last-writer-wins model),
     which is exactly where the old chunker silently lost rows;
  4. revert-simulation: re-running the post-change assertions against the
     pre-change chunker FAILS (reports the lost lines), proving the
     differential is non-vacuous.

The pre-change chunker loads from ``git show HEAD:...chunker.py`` (the
wave's edits are uncommitted; HEAD is the shipped v37).

MUST run under the tool venv from the repository root:
    ~/.wavefoundry/venv/bin/python "docs/waves/1wl7u retrieval-loose-ends/evidence/coverage_differential_1wh1b.py" [--out <file>]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
FIXTURES = SCRIPTS / "tests" / "fixtures" / "retrieval_golden"
sys.path.insert(0, str(SCRIPTS))

import chunker as new_chunker  # noqa: E402

DOCS_TABLE_KINDS = {"doc", "seed", "prompt", "doc-summary", "doc-code"}


def _load_old_chunker():
    blob = subprocess.run(
        ["git", "show", "HEAD:.wavefoundry/framework/scripts/chunker.py"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix="_old_chunker.py", delete=False, encoding="utf-8")
    tmp.write(blob)
    tmp.close()
    spec = importlib.util.spec_from_file_location("old_cov_chunker", tmp.name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["old_cov_chunker"] = mod
    spec.loader.exec_module(mod)
    return mod


def _surviving_texts(mod, source: str, path: str, kinds=None) -> list[str]:
    """Chunk and keep only the texts that survive the id-keyed collapse
    (dict last-writer-wins — the delta planner / registry model)."""
    by_id: dict[str, str] = {}
    for c in mod.chunk_file(source, path):
        if kinds is None or c.kind in kinds:
            by_id[c.id] = c.text
    return list(by_id.values())


def _content_lines(path: str, source: str) -> list[str]:
    """The per-line coverage universe for a fixture: lines that a correct
    chunker MUST carry into some chunk text. Notebook fixtures use the CELL
    source lines (raw .ipynb JSON lines are serialization, not content);
    prose fixtures use their marker-tagged body lines (heading and
    adornment lines are structural — they become ids/breadcrumbs, not
    body text)."""
    if path.endswith(".ipynb"):
        nb = json.loads(source)
        out: list[str] = []
        for cell in nb.get("cells", []):
            if cell.get("cell_type") not in ("markdown", "code"):
                continue
            text = cell.get("source", "")
            if isinstance(text, list):
                text = "".join(text)
            out.extend(ln.strip() for ln in text.splitlines()
                       if ln.strip() and len(ln.strip()) >= 4
                       and not ln.strip().startswith("#"))
        return out
    return [ln.strip() for ln in source.splitlines()
            if "-content-line" in ln]


def _covered(lines: list[str], texts: list[str]) -> set[str]:
    blob = "\n".join(texts)
    return {ln for ln in lines if ln in blob}


def _nb_code_cell_lines(source: str) -> list[str]:
    nb = json.loads(source)
    out: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        text = cell.get("source", "")
        if isinstance(text, list):
            text = "".join(text)
        out.extend(ln.strip() for ln in text.splitlines()
                   if ln.strip() and len(ln.strip()) >= 4)
    return out


def _fixtures() -> list[tuple[str, str]]:
    nb_fix = (FIXTURES / "prose" / "ipynb" / "churn_cohort_analysis.ipynb")
    dup_md = (
        "# Guide\n\n"
        "## Setup\n\nFirst body with a distinctive marker alpha-content-line.\n\n"
        "## Setup\n\nSecond body with a distinctive marker beta-content-line.\n\n"
        "## Setup 2\n\nLiteral title body gamma-content-line.\n"
    )
    dup_rst = (
        "Guide\n=====\n\n"
        "Usage\n-----\n\nFirst rst body delta-content-line.\n\n"
        "Usage\n-----\n\nSecond rst body epsilon-content-line.\n"
    )
    dup_adoc = (
        "= Guide\n\n"
        "== Usage\n\nFirst adoc body zeta-content-line.\n\n"
        "== Usage\n\nSecond adoc body eta-content-line.\n"
    )
    return [
        ("docs/churn_cohort_analysis.ipynb",
         nb_fix.read_text(encoding="utf-8")),
        ("docs/dup-guide.md", dup_md),
        ("docs/dup-guide.rst", dup_rst),
        ("docs/dup-guide.adoc", dup_adoc),
    ]


def run_differential(post_mod, pre_mod) -> dict:
    """Assert post_mod's coverage against pre_mod's baseline. Called once
    with (new, old) for the real differential and once with (old, old) for
    the revert-simulation, where the docs-eligibility assertion must fail."""
    report: dict = {"files": {}, "violations": []}
    for path, source in _fixtures():
        lines = _content_lines(path, source)
        old_any = _covered(lines, _surviving_texts(pre_mod, source, path))
        new_any = _covered(lines, _surviving_texts(post_mod, source, path))
        docs_texts = _surviving_texts(post_mod, source, path, DOCS_TABLE_KINDS)
        new_docs = _covered(lines, docs_texts)
        lost = sorted(old_any - new_any)
        entry = {
            "content_lines": len(lines),
            "covered_any_old": len(old_any),
            "covered_any_new": len(new_any),
            "covered_docs_eligible_new": len(new_docs),
            "lines_lost_vs_old": lost,
        }
        if lost:
            report["violations"].append(f"{path}: lost {len(lost)} lines")
        if path.endswith(".ipynb"):
            code_lines = _nb_code_cell_lines(source)
            missing = sorted(set(code_lines) - _covered(code_lines, docs_texts))
            entry["code_cell_lines"] = len(code_lines)
            entry["code_cell_lines_docs_eligible"] = (
                len(code_lines) - len(missing))
            entry["code_cell_lines_missing_from_docs"] = missing
            if missing:
                report["violations"].append(
                    f"{path}: {len(missing)} code-cell lines not docs-eligible")
        else:
            # Duplicate-titled prose: every content line must survive the
            # id-keyed collapse into a docs-eligible SECTION chunk. The
            # doc-summary chunk is excluded from this leg (QA delivery
            # advisory: the markdown summary happens to carry the first
            # section's opening lines, which masked md collapse loss in the
            # revert simulation).
            section_texts = _surviving_texts(
                post_mod, source, path, DOCS_TABLE_KINDS - {"doc-summary"})
            missing = sorted(set(lines) - _covered(lines, section_texts))
            entry["prose_lines_missing_after_id_collapse"] = missing
            if missing:
                report["violations"].append(
                    f"{path}: {len(missing)} prose lines lost to id collapse")
        report["files"][path] = entry
    report["pass"] = not report["violations"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    old_chunker = _load_old_chunker()
    forward = run_differential(new_chunker, old_chunker)
    revert_sim = run_differential(old_chunker, old_chunker)

    results = {
        "differential": "1wh1b per-line content coverage (id-collapse surviving rows)",
        "old_chunker_version": old_chunker.CHUNKER_VERSION,
        "new_chunker_version": new_chunker.CHUNKER_VERSION,
        "forward": forward,
        "revert_simulation": {
            "pass": revert_sim["pass"],
            "violations": revert_sim["violations"],
            "non_vacuous": not revert_sim["pass"],
        },
        "result": "PASS" if (forward["pass"] and not revert_sim["pass"])
                  else "FAIL",
    }
    payload = json.dumps(results, indent=2) + "\n"
    print(payload, end="")
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    return 0 if results["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
