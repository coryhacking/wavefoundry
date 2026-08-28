"""Versioned differential-fixture regeneration for change 1whup-enh (wave 1wik9).

Requirement 4: the doc-code kind change alters the markdown chunk-set shape
(kind code -> doc-code on extracted fences, file-pass ordinal ids), so the
markdown byte-identity differential fixture is regenerated as a deliberate
versioned step. Every changed row in the old-versus-new diff MUST classify
into the intended delta classes; any unclassified delta blocks (exits
nonzero, writes nothing). The specs-negatives differential is asserted
ZERO-DELTA: no negative is doc-family, so any delta there is a leak outside
the doc-family paths. Both regenerated snapshots are re-proven to
discriminate (fail on a mutated input) before they re-arm.

MUST run under the tool venv (system python lacks tree-sitter; the 1wfsl
environment-sensitive-oracle lesson):
    ~/.wavefoundry/venv/bin/python "docs/waves/1wik9 fenced-diagram-and-spec-retrieval/evidence/regen_differentials_1whup.py" [--write]

Prints the classified diff report to stdout; rewrites the committed fixture
files ONLY with --write (QA-DEL-1: bare re-runs never clobber committed
artifacts).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
FIXTURES = SCRIPTS / "tests" / "fixtures" / "retrieval_golden"
sys.path.insert(0, str(SCRIPTS))

import chunker  # noqa: E402

_ORDINAL_RE = re.compile(r":code-\d+$")


def _chunk_rows(sources: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for entry in sources:
        for c in chunker.chunk_file(entry["source"], entry["path"]):
            rows.append(c.to_dict())
    return rows


def classify_markdown_delta(old_rows: list[dict], new_rows: list[dict]) -> dict:
    """Pairwise-classify old vs new markdown rows. The kind change alters no
    chunk boundaries (same fences, same prose), so counts and order match;
    a count mismatch is itself an unclassified (blocking) delta."""
    report: dict = {"row_count_old": len(old_rows), "row_count_new": len(new_rows),
                    "changed": [], "unclassified": []}
    if len(old_rows) != len(new_rows):
        report["unclassified"].append(
            f"row count changed {len(old_rows)} -> {len(new_rows)}")
        return report
    for old, new in zip(old_rows, new_rows):
        if old == new:
            continue
        classes = []
        diff_keys = {k for k in set(old) | set(new) if old.get(k) != new.get(k)}
        if diff_keys <= {"id", "kind"}:
            if old.get("kind") == "code" and new.get("kind") == "doc-code":
                classes.append("kind code->doc-code (doc-family extracted block)")
            if old.get("id") != new.get("id"):
                base_old = _ORDINAL_RE.sub("", str(old.get("id")))
                stripped_old = base_old[:-len(":code")] if base_old.endswith(":code") else base_old
                base_new = _ORDINAL_RE.sub("", str(new.get("id")))
                stripped_new = base_new[:-len(":code")] if base_new.endswith(":code") else base_new
                if stripped_old == stripped_new and _ORDINAL_RE.search(str(new.get("id"))):
                    classes.append("file-pass ordinal id addition")
        if classes and len(classes) == len(diff_keys & {"id", "kind"}) and diff_keys <= {"id", "kind"}:
            report["changed"].append({
                "old_id": old.get("id"), "new_id": new.get("id"),
                "old_kind": old.get("kind"), "new_kind": new.get("kind"),
                "classes": classes,
            })
        else:
            report["unclassified"].append({
                "old_id": old.get("id"), "new_id": new.get("id"),
                "diff_keys": sorted(diff_keys),
            })
    return report


def regenerate_specs_negatives() -> tuple[list[dict], list[dict]]:
    old = json.loads(
        (FIXTURES / "specs_negatives_differential_expected.json").read_text(
            encoding="utf-8"))
    new: dict[str, list[dict]] = {}
    for rel in old:
        src = (FIXTURES / "specs" / rel).read_text(encoding="utf-8")
        new[rel] = [c.to_dict() for c in chunker.chunk_file(src, rel)]
    return old, new


def prove_discrimination(sources: list[dict], expected: list[dict]) -> bool:
    """The re-armed snapshot must FAIL on a mutated input: flip one fence's
    content in the first source that has one and confirm inequality."""
    mutated = [dict(entry) for entry in sources]
    for entry in mutated:
        if "```" in entry["source"]:
            entry["source"] = entry["source"].replace(
                "```", "```\nMUTATED_SENTINEL_LINE", 1)
            break
    else:
        return False
    return _chunk_rows(mutated) != expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    sources = json.loads(
        (FIXTURES / "markdown_differential_sources.json").read_text(
            encoding="utf-8"))
    old_expected = json.loads(
        (FIXTURES / "markdown_differential_expected.json").read_text(
            encoding="utf-8"))
    new_expected = _chunk_rows(sources)

    report = classify_markdown_delta(old_expected, new_expected)
    old_neg, new_neg = regenerate_specs_negatives()
    negatives_zero_delta = old_neg == new_neg
    discriminates = prove_discrimination(sources, new_expected)

    out = {
        "regeneration": "1whup Requirement 4 versioned differential regeneration",
        "chunker_version": chunker.CHUNKER_VERSION,
        "markdown_delta": report,
        "specs_negatives_zero_delta": negatives_zero_delta,
        "markdown_snapshot_discriminates_on_mutation": discriminates,
    }
    print(json.dumps(out, indent=2))

    blocked = bool(report["unclassified"]) or not negatives_zero_delta \
        or not discriminates
    if blocked:
        print("BLOCKED: unclassified delta, negatives delta, or "
              "non-discriminating snapshot; nothing written.", file=sys.stderr)
        return 1
    if args.write:
        (FIXTURES / "markdown_differential_expected.json").write_text(
            json.dumps(new_expected, indent=2) + "\n", encoding="utf-8")
        print(f"wrote markdown_differential_expected.json "
              f"({len(new_expected)} rows, chunker {chunker.CHUNKER_VERSION})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
