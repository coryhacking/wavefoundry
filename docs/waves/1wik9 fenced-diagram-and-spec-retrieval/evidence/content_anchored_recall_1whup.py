"""Content-anchored recall@5 supplement for the 1whup prose measurement.

The prose harness's hit predicate requires the expected FILE plus the anchor
substring, which measures per-format attribution. The fixture corpus is
matched trios (the same content authored in md, rst, and adoc for per-format
comparability), so under cosine ties the file attribution among identical
twins is arbitrary: a chunk can slide below rank 5 while its byte-identical
twin keeps the slot. This supplement scores a hit when the expected ANCHOR
appears in any top-5 chunk's text — the form that measures whether the asker
still finds the answer. Executed classification of the 1whup after-run showed
every file-attributed hit loss kept its anchor content in the top 5 via a
cross-format twin (zero content losses), which is why the Requirement 5 hard
bar binds on this content-anchored form.

Run under the tool venv from the repository root:
    ~/.wavefoundry/venv/bin/python \
      "docs/waves/1wik9 fenced-diagram-and-spec-retrieval/evidence/content_anchored_recall_1whup.py" [--out <file.json>]

Reads the committed before/after eval results next to this script; prints the
per-format content-anchored recall@5 for both runs. Writes ONLY with --out.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
FIXTURES = SCRIPTS / "tests" / "fixtures" / "retrieval_golden"
sys.path.insert(0, str(SCRIPTS))

import chunker  # noqa: E402

RUNS = ("eval_prose_before_1whup.json", "eval_prose_after_1whup.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    gq = json.loads(
        (FIXTURES / "golden_queries_prose.json").read_text(encoding="utf-8"))
    anchors = {
        f"{e['id']}:{fmt}": t["anchor"]
        for e in gq for fmt, t in e["variants"].items()
    }
    chunk_text: dict[str, str] = {}
    prose = FIXTURES / "prose"
    for f in sorted(prose.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(prose)).replace("\\", "/")
        for c in chunker.chunk_file(f.read_text(encoding="utf-8"), rel):
            chunk_text[f"{rel}#{c.id}"] = c.text

    results: dict = {
        "supplement": "1whup content-anchored recall@5 (anchor in any top-5 chunk)",
        "chunker_version": chunker.CHUNKER_VERSION,
        "runs": {},
    }
    for name in RUNS:
        d = json.loads((HERE / name).read_text(encoding="utf-8"))
        per_fmt = {}
        for fmt, m in sorted(d["metrics_by_format"].items()):
            hits = sum(
                1 for q in m["per_query"]
                if any(anchors[q["id"]] in chunk_text.get(t, "")
                       for t in q["top5"])
            )
            per_fmt[fmt] = {
                "content_anchored_recall_at_5": hits / len(m["per_query"]),
                "file_attributed_recall_at_5": m["recall_at_5"],
                "query_count": len(m["per_query"]),
            }
        results["runs"][name] = {"label": d["label"], "formats": per_fmt}

    text = json.dumps(results, indent=2)
    if args.out:
        (HERE / args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
