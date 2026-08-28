"""Executed per-name exclusion census for change 1wfsn-enh (wave 1wfsl).

Requirement 1: classify every candidate machine-generated name by EXECUTING the
real walk (`indexer.walk_repo`) and the real corpus filter
(`indexer._filter_code_files`) against a constructed fixture tree, never by
grep. The wave watchpoint exists because two grep-based planning censuses in
this wave were falsified against the tree.

Classifications (mechanism-class granularity per Requirement 1 / AC-1):
  - walk_excluded_name          : dropped at the exact-filename check
  - walk_excluded_ext_or_sniff  : dropped by binary-extension, generated-
                                  extension, or content-sniff mechanisms
  - corpus_filtered             : walks, but `_filter_code_files` drops it from
                                  the code corpus
  - indexed                     : walks AND survives the code-corpus filter
                                  (reachable by a corpus configuration)

Also records the repository-level "before" statistics for Requirement 6 /
AC-4: walked-file count, code-corpus file count, and on-disk index size for
this repository, plus the real-tree classification of any candidate names that
exist here (notably docs/scan-findings.json, the qa re-verification advisory).

Run from the repository root:
    python3 "docs/waves/1wfsl structured-docs-retrieval/evidence/census_exclusions.py"
Prints results to stdout; writes a file ONLY when --out is given, so a bare
re-run can never clobber the committed census_results.json (before) /
census_results_after.json (after) artifacts (QA-DEL-1).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import indexer  # noqa: E402  (real walk + filters; the census MUST use these)

TEXT = "generated: true\ncontent: sample\n"
JSON_TEXT = '{"generated": true, "content": "sample"}\n'
MIN_JS = "!function(){var a=1;console.log(a)}();\n"
MIN_CSS = ".a{color:#fff}.b{margin:0}\n"
BINARY = b"\x00\x01\x02bun-lockb-binary\x00payload"

# (relative path, content) — every candidate name from the 1wfsn plan plus the
# qa re-verification addition (scan-findings.json) and legitimate siblings that
# MUST remain included.
FIXTURE_FILES: list[tuple[str, bytes | str]] = [
    # expected name-layer exclusions (HARDCODED_EXCLUDE_FILENAMES)
    ("package-lock.json", JSON_TEXT),
    ("yarn.lock", TEXT),
    ("pnpm-lock.yaml", TEXT),
    ("prompt-surface-manifest.json", JSON_TEXT),
    # expected extension exclusions (.lock in BINARY_EXTENSIONS)
    ("Cargo.lock", TEXT),
    ("poetry.lock", TEXT),
    ("uv.lock", TEXT),
    ("Pipfile.lock", TEXT),
    ("composer.lock", TEXT),
    ("Gemfile.lock", TEXT),
    ("flake.lock", TEXT),
    # expected content-sniff exclusion (binary payload, unknown extension)
    ("bun.lockb", BINARY),
    # expected generated-extension exclusions (_GENERATED_EXCLUDE_EXTENSIONS)
    ("ui-state.snap", TEXT),
    ("diagram.excalidraw", JSON_TEXT),
    # expected corpus-filter drops (walk, but not SOURCE_CODE_EXTENSIONS)
    ("go.sum", TEXT),
    ("gradle.lockfile", TEXT),
    ("app.js.map", JSON_TEXT),
    # candidate stragglers (the plan expects these INDEXED today)
    ("npm-shrinkwrap.json", JSON_TEXT),
    ("packages.lock.json", JSON_TEXT),
    ("app.min.js", MIN_JS),
    ("styles.min.css", MIN_CSS),
    # qa re-verification advisory candidate: machine-generated findings ledger
    ("docs/scan-findings.json", JSON_TEXT),
    # legitimate siblings that MUST remain included
    ("package.json", JSON_TEXT),
    ("app.js", "var a = 1;\nconsole.log(a);\n"),
    ("styles.css", ".a { color: #fff; }\n"),
]

CANDIDATE_NAMES = [rel for rel, _ in FIXTURE_FILES]


def classify(rel: str, walked: set[str], corpus: set[str]) -> dict:
    name = rel.rsplit("/", 1)[-1]
    suffix = ("." + name.rsplit(".", 1)[-1]).lower() if "." in name else ""
    entry: dict = {"path": rel}
    if rel in corpus:
        entry["classification"] = "indexed"
        entry["mechanism_class"] = None
    elif rel in walked:
        entry["classification"] = "corpus_filtered"
        entry["mechanism_class"] = "corpus-filter"
    else:
        # mechanism-class probe against the real constants, in the walk's own
        # check order (machine-authority path predicates precede the name layer;
        # the getattr fallbacks keep the probe runnable against the pre-1wfsn
        # module for the BEFORE run)
        is_scan_findings = getattr(indexer, "_is_secret_scan_findings_path", None)
        suffix_patterns = getattr(indexer, "HARDCODED_EXCLUDE_FILENAME_SUFFIXES", ())
        if is_scan_findings is not None and is_scan_findings(rel):
            entry["classification"] = "walk_excluded_machine_authority"
            entry["mechanism_class"] = "machine-authority path"
        elif name in indexer.HARDCODED_EXCLUDE_FILENAMES:
            entry["classification"] = "walk_excluded_name"
            entry["mechanism_class"] = "name"
        elif suffix_patterns and name.endswith(tuple(suffix_patterns)):
            entry["classification"] = "walk_excluded_name"
            entry["mechanism_class"] = "name (suffix pattern)"
        elif suffix in indexer.BINARY_EXTENSIONS:
            entry["classification"] = "walk_excluded_ext_or_sniff"
            entry["mechanism_class"] = "extension-or-sniff (binary extension)"
        elif suffix in indexer._GENERATED_EXCLUDE_EXTENSIONS:
            entry["classification"] = "walk_excluded_ext_or_sniff"
            entry["mechanism_class"] = "extension-or-sniff (generated extension)"
        else:
            entry["classification"] = "walk_excluded_ext_or_sniff"
            entry["mechanism_class"] = "extension-or-sniff (content sniff)"
    return entry


def run_fixture_census() -> list[dict]:
    with tempfile.TemporaryDirectory(prefix="wf-1wfsn-census-") as tmp:
        root = Path(tmp)
        for rel, content in FIXTURE_FILES:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")

        walked_paths = indexer.walk_repo(root, respect_ignore=True)
        walked = {
            str(p.relative_to(root)).replace("\\", "/") for p in walked_paths
        }
        corpus_paths = indexer._filter_code_files(
            walked_paths, root, include_tests=False, include_generated=False
        )
        corpus = {
            str(p.relative_to(root)).replace("\\", "/") for p in corpus_paths
        }
        return [classify(rel, walked, corpus) for rel in CANDIDATE_NAMES]


def dir_size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def run_repo_stats() -> dict:
    walked_paths = indexer.walk_repo(REPO_ROOT, respect_ignore=True)
    walked = {
        str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in walked_paths
    }
    corpus_paths = indexer._filter_code_files(
        walked_paths, REPO_ROOT, include_tests=False, include_generated=False
    )
    candidate_hits = {}
    for rel in sorted(walked):
        name = rel.rsplit("/", 1)[-1]
        if name in {
            "scan-findings.json", "npm-shrinkwrap.json", "packages.lock.json",
            "go.sum", "gradle.lockfile",
        } or name.endswith((".min.js", ".min.css", ".map")):
            candidate_hits[rel] = "walked"
    return {
        "walked_file_count": len(walked_paths),
        "code_corpus_file_count": len(corpus_paths),
        "index_dir_size_bytes": dir_size_bytes(REPO_ROOT / ".wavefoundry" / "index"),
        "candidate_names_walked_in_this_repo": candidate_hits,
        "scan_findings_json_walks": "docs/scan-findings.json" in walked,
    }


def main() -> int:
    # QA-DEL-1 (delivery review): re-runs must never clobber the committed
    # before/after artifacts — the default output is a non-committed name;
    # pass --out explicitly to write a committed artifact on purpose.
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", default=None,
        help="output filename (written next to this script); WITHOUT --out the "
             "results print to stdout only, so a bare re-run can never write "
             "into the committed evidence directory",
    )
    args = parser.parse_args()
    results = {
        "census": "1wfsn-enh Requirement 1 executed per-name census",
        "method": "indexer.walk_repo + indexer._filter_code_files on a constructed fixture tree; no grep",
        "walker_version": indexer.WALKER_VERSION,
        "fixture_census": run_fixture_census(),
        "repository_before_stats": run_repo_stats(),
    }
    if args.out:
        out = Path(__file__).with_name(args.out)
        out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
