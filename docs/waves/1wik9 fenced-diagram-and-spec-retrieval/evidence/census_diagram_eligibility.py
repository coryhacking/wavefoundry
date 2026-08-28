"""Executed diagram-file eligibility census for change 1whuq-enh (wave 1wik9).

Requirement 3: record docs-table eligibility for diagram files in and out of
docs roots by EXECUTING the real walk (`indexer.walk_repo`) and the real
docs-eligibility filter (`indexer._filter_project_index_excludes`, the same
call `build_index` uses for `docs_eligible_rel`) against a constructed
fixture tree, never grep. Also pins the Requirement 2 binary-impostor case:
a `.dot` file with a null-byte OLE header (the legacy Word-template namesake)
must stay walk-excluded by the content sniff, which is why registration is
chunker-only and the six extensions never join `_KNOWN_TEXT_EXTENSIONS`.

Run under the tool venv from the repository root:
    ~/.wavefoundry/venv/bin/python "docs/waves/1wik9 fenced-diagram-and-spec-retrieval/evidence/census_diagram_eligibility.py" [--out <file.json>]

Prints JSON; writes ONLY with --out (QA-DEL-1).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import indexer  # noqa: E402

MERMAID = "---\ntitle: Flow\n---\nflowchart LR\n    A[Auth] --> B[Tokens]\n"
PUML = "@startuml\ntitle Topology\n[Relay] --> [Scheduler]\n@enduml\n"
DOT = 'digraph Deps {\n    a -> b [label="reads flags"];\n}\n'
BINARY_DOT = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64  # OLE header

FIXTURES: list[tuple[str, bytes | str]] = [
    ("docs/diagrams/auth-flow.mmd", MERMAID),
    ("docs/diagrams/pipeline.mermaid", MERMAID),
    ("src/architecture/topology.puml", PUML),
    ("design/lifecycle.plantuml", PUML),
    ("deps/services.dot", DOT),
    ("tooling/targets.gv", DOT),
    # Adjacent fact: a diagram inside an excluded-directory NAME (dist, build,
    # target, out, ...) never walks — directory exclusions precede extension
    # or content handling. Recorded, not changed.
    ("build/inside-excluded-dir.gv", DOT),
    (".wavefoundry/framework/notes/internal.mmd", MERMAID),
    ("templates/legacy-word-template.dot", BINARY_DOT),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="wf-1whuq-census-") as tmp:
        root = Path(tmp)
        for rel, content in FIXTURES:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                p.write_bytes(content)
            else:
                p.write_text(content, encoding="utf-8")
        (root / "docs" / "workflow-config.json").write_text(
            json.dumps({"indexing": {}}), encoding="utf-8")

        walked_paths = indexer.walk_repo(root, respect_ignore=True)
        walked = {str(p.relative_to(root)).replace("\\", "/")
                  for p in walked_paths}
        # The same docs-eligibility call build_index makes (default prefixes:
        # no include_prefixes restriction, no project include-prefix opt-ins).
        docs_eligible = {
            str(f.relative_to(root)).replace("\\", "/")
            for f in indexer._filter_project_index_excludes(
                walked_paths, root, (), project_include_prefixes=(),
            )
        }
        rows = []
        for rel, content in FIXTURES:
            rows.append({
                "path": rel,
                "walks": rel in walked,
                "docs_eligible": rel in docs_eligible,
                "binary_impostor": isinstance(content, bytes),
            })

    results = {
        "census": "1whuq Requirement 3 executed diagram eligibility census",
        "walker_version": indexer.WALKER_VERSION,
        "method": "indexer.walk_repo + indexer._filter_project_index_excludes "
                  "on a constructed fixture tree; no grep",
        "fixture_census": rows,
        "polarity": {
            "in_docs_root_eligible": all(
                r["docs_eligible"] for r in rows
                if r["path"].startswith("docs/") and not r["binary_impostor"]),
            "out_of_docs_root_eligible": all(
                r["docs_eligible"] for r in rows
                if not r["path"].startswith((".wavefoundry/", "docs/", "build/"))
                and not r["binary_impostor"]),
            "excluded_dir_name_never_walks": not any(
                r["walks"] for r in rows if r["path"].startswith("build/")),
            "wavefoundry_nested_excluded": not any(
                r["docs_eligible"] for r in rows
                if r["path"].startswith(".wavefoundry/")),
            "binary_impostor_walk_excluded": not any(
                r["walks"] for r in rows if r["binary_impostor"]),
        },
    }
    text = json.dumps(results, indent=2)
    print(text)
    if args.out:
        Path(__file__).with_name(args.out).write_text(text + "\n",
                                                      encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
