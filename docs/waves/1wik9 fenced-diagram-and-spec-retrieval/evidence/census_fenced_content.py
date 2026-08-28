"""Executed emission-site and kind-mirror census for change 1whup-enh (wave 1wik9).

Requirement 1: enumerate every doc-family chunker emission site producing
code-kind chunks, prove through `_chunks_for_file` plus the real eligibility
sets which chunks are dropped today, record the notebook state, and sweep every
shipped kind-enumeration mirror. Executed through the real chunker and indexer,
never grep (the standing wave watchpoint).

Prints JSON to stdout; writes a file ONLY with --out (QA-DEL-1 lesson from wave
1wfsl: bare re-runs must never clobber committed evidence).

Run from the repository root:
    python3 "docs/waves/1wik9 fenced-diagram-and-spec-retrieval/evidence/census_fenced_content.py" [--out census_fenced_content.json]
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

import chunker  # noqa: E402
import indexer  # noqa: E402

MD_DOC = """Preamble prose with a fence below.

```ini
preamble_setting = true
```

# Widget Guide

## Install

Run the installer.

```bash
widgetctl install --profile default
```

## Install

Second section with a duplicate title.

```python
import widget
```
"""

MD_PROMPT = """# Prompt Doc

## Step

Run this:

```bash
run --step one
```
"""

RST_DOC = """Guide
=====

Usage
-----

Prose here.

.. code-block:: python

   configure(retries=3)
"""

ADOC_DOC = """= Guide

== Usage

Prose here.

[source,python]
----
configure(retries=3)
----
"""

IPYNB_DOC = json.dumps({
    "cells": [
        {"cell_type": "markdown", "source": ["# Notebook\n", "Prose cell.\n"]},
        {"cell_type": "code", "source": ["compute_answer(42)\n"], "outputs": []},
    ],
    "metadata": {}, "nbformat": 4, "nbformat_minor": 5,
})

FIXTURES = [
    ("docs/guide.md", MD_DOC),
    ("docs/prompts/step.prompt.md", MD_PROMPT),
    ("docs/guide.rst", RST_DOC),
    ("docs/guide.adoc", ADOC_DOC),
    ("docs/analysis.ipynb", IPYNB_DOC),
]


def emission_census() -> list[dict]:
    rows = []
    for rel, source in FIXTURES:
        doc_chunks, code_chunks = indexer._chunks_for_file(rel, source)
        rows.append({
            "file": rel,
            "doc_kind_chunks": [
                {"id": c["id"], "kind": c["kind"]} for c in doc_chunks
            ],
            "code_kind_chunks": [
                {"id": c["id"], "kind": c["kind"], "language": c.get("language")}
                for c in code_chunks
            ],
            "code_chunk_id_collisions": sorted({
                cid for cid in [c["id"] for c in code_chunks]
                if [c["id"] for c in code_chunks].count(cid) > 1
            }),
        })
    return rows


def eligibility_census() -> dict:
    with tempfile.TemporaryDirectory(prefix="wf-1whup-census-") as tmp:
        root = Path(tmp)
        for rel, source in FIXTURES:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(source, encoding="utf-8")
        (root / "docs" / "workflow-config.json").write_text(
            json.dumps({"indexing": {}}), encoding="utf-8")
        walked = indexer.walk_repo(root, respect_ignore=True)
        index_dir = root / ".wavefoundry" / "index"
        code_files = indexer._filter_code_files(
            walked, root, include_tests=False, include_generated=False)
        code_rels = {str(p.relative_to(root)).replace("\\", "/") for p in code_files}
        return {
            "walked": sorted(
                str(p.relative_to(root)).replace("\\", "/") for p in walked
            ),
            "code_eligible": sorted(code_rels),
            "doc_family_files_code_eligible": sorted(
                r for r, _ in FIXTURES if r in code_rels
            ),
        }


def kind_mirror_census() -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_retrieval_eval",
        SCRIPTS / "tests" / "fixtures" / "retrieval_golden" / "run_retrieval_eval.py",
    )
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    import server_impl
    import inspect
    src = inspect.getsource(server_impl)
    return {
        "indexer._is_docs_kind_members": [
            k for k in ("doc", "seed", "prompt", "doc-summary", "doc-code", "code")
            if indexer._is_docs_kind(k)
        ],
        "harness._DOCS_KINDS": sorted(harness._DOCS_KINDS),
        "server_impl.DOCS_SEARCH_KINDS": sorted(server_impl.DOCS_SEARCH_KINDS),
        # _doc_matches_kind is a WaveIndex method that never touches self, so
        # the census calls it unbound; "" (no filter) trivially matches, so the
        # question is whether ANY explicit filter can match a doc-code chunk.
        "server_impl._doc_matches_kind_doc_code_matches_any_filter": any(
            server_impl.WaveIndex._doc_matches_kind(
                None, {"kind": "doc-code", "path": "docs/x.md"}, k
            ) for k in ["doc", "seed", "architecture", "prompt", "doc-summary", "doc-code"]
        ),
        "server_impl_code_ask_partition_tuples_count": src.count(
            '("doc", "doc-summary", "seed")'
        ),
        "server_impl_validation_required_tuple_present": (
            '("doc", "doc-summary")' in src
        ),
        "chunker._DOCS_BREADCRUMB_KINDS": list(chunker._DOCS_BREADCRUMB_KINDS),
        "chunker._max_chars_for_doc_code_chunk": chunker._max_chars_for_chunk(
            chunker.Chunk(id="x", path="p", kind="doc-code", language=None,
                          lines=(1, 1), section=None, text="t")
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    results = {
        "census": "1whup-enh Requirement 1 executed emission-site and kind-mirror census",
        "chunker_version": chunker.CHUNKER_VERSION,
        "walker_version": indexer.WALKER_VERSION,
        "emission_sites": emission_census(),
        "eligibility": eligibility_census(),
        "kind_mirrors": kind_mirror_census(),
    }
    text = json.dumps(results, indent=2)
    if args.out:
        Path(__file__).with_name(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
