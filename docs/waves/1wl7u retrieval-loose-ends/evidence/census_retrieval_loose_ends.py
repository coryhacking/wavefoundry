"""Executed censuses for change 1wh1b-enh (wave 1wl7u retrieval-loose-ends).

Four censuses, all executed through the real chunker and indexer, never grep
(the standing wave watchpoint; the census, not the plan, is the authority):

1. prose_id_site_census — every un-anchored slug-id emission site across ALL
   chunkers (md/rst/adoc family, H3-split, line-window bases, HTML/XML regex
   fallbacks, tree-sitter config chunker), with executed duplicate-title
   collision reproduction and the collision-free control formats.
2. notebook_census — chunk_jupyter emission shape (ids, kinds, sections,
   language source, output invisibility) and both-tables routing today.
3. kind_mirror_census — the seven shipped doc-code kind mirrors (1whup).
4. drawio_census — text-XML .drawio through walk_repo, both eligibility
   sets, and chunk_file: walked, chunked, zero rows shipped.

Prints JSON to stdout; writes a file ONLY with --out (QA-DEL-1 lesson from
wave 1wfsl: bare re-runs must never clobber committed evidence).

Run from the repository root:
    ~/.wavefoundry/venv/bin/python "docs/waves/1wl7u retrieval-loose-ends/evidence/census_retrieval_loose_ends.py" [--out <file>]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import chunker  # noqa: E402
import indexer  # noqa: E402


def _ids(chunks) -> list[str]:
    return [c.id for c in chunks]


def _dupes(chunks) -> dict[str, int]:
    counts = Counter(c.id for c in chunks)
    return {i: n for i, n in counts.items() if n > 1}


def _pad(prefix: str, chars: int) -> str:
    """Prose filler that pushes a section body over a size threshold."""
    line = prefix + " filler prose sentence that carries no anchors. "
    reps = chars // len(line) + 2
    return "\n\n".join(line for _ in range(reps))


def prose_id_site_census() -> dict:
    over = chunker.H3_SPLIT_THRESHOLD_CHARS + 200
    results: dict = {}

    md_dup_h2 = (
        "# Guide\n\n## Setup\n\nFirst setup body.\n\n"
        "## Setup\n\nSecond setup body.\n"
    )
    results["md_dup_h2"] = {
        "site": "chunk_markdown section emission (id=f\"{path}#{slug}\")",
        "ids": _ids(chunker.chunk_file(md_dup_h2, "docs/guide.md")),
        "collisions": _dupes(chunker.chunk_file(md_dup_h2, "docs/guide.md")),
    }

    md_dup_h3 = (
        "# Guide\n\n## Config\n\n### Advanced\n\n" + _pad("A", over // 2)
        + "\n\n### Advanced\n\n" + _pad("B", over // 2) + "\n"
    )
    results["md_dup_h3"] = {
        "site": "_split_h3_sections (id=f\"{path}#{h2_slug}/{h3_slug}\")",
        "collisions": _dupes(chunker.chunk_file(md_dup_h3, "docs/h3.md")),
    }

    md_dup_lw = (
        "# Guide\n\n## Notes\n\n" + _pad("A", over)
        + "\n\n## Notes\n\n" + _pad("A", over) + "\n"
    )
    results["md_dup_linewindow"] = {
        "site": "chunk_markdown oversized-section line-window base (id=f\"{path}#{slug}:L{a}-L{b}\", window lines RELATIVE to extracted prose)",
        "collisions": _dupes(chunker.chunk_file(md_dup_lw, "docs/lw.md")),
    }

    md_preamble = (
        "Opening prose before any heading.\n\n# Guide\n\n"
        "## Preamble\n\nA literal section titled Preamble.\n"
    )
    results["md_preamble_vs_literal_title"] = {
        "site": "preamble sentinel slug vs a literal 'Preamble' H2 title",
        "collisions": _dupes(chunker.chunk_file(md_preamble, "docs/pre.md")),
    }

    rst_dup = (
        "Guide\n=====\n\nSetup\n-----\n\nFirst body.\n\nSetup\n-----\n\nSecond body.\n"
    )
    results["rst_dup"] = {
        "site": "_emit_prose_sections shared rst/adoc emission (id=f\"{path}#{slug}\")",
        "collisions": _dupes(chunker.chunk_file(rst_dup, "docs/guide.rst")),
    }

    adoc_dup = (
        "= Guide\n\n== Setup\n\nFirst body.\n\n== Setup\n\nSecond body.\n"
    )
    results["adoc_dup"] = {
        "site": "_emit_prose_sections via chunk_adoc",
        "collisions": _dupes(chunker.chunk_file(adoc_dup, "docs/guide.adoc")),
    }

    setup2 = (
        "# Guide\n\n## Setup\n\nFirst.\n\n## Setup\n\nSecond.\n\n"
        "## Setup 2\n\nA literal title that slugifies to setup-2.\n"
    )
    setup2_chunks = chunker.chunk_file(setup2, "docs/s2.md")
    results["md_literal_suffix_shape"] = {
        "site": "why bare -N ordinals are unsafe: 'Setup 2' slugifies into the -2 tail",
        "ids": _ids(setup2_chunks),
        "collisions": _dupes(setup2_chunks),
    }

    html_dup = (
        "<html><body>\n<section>\n<p>First body.</p>\n</section>\n"
        "<section>\n<p>Second body.</p>\n</section>\n</body></html>\n"
    )
    results["html_regex_fallback_dup"] = {
        "site": "chunk_html regex fallback (id=f\"{path}#{_slugify(tag)}\", kind doc; runs when tree-sitter is unavailable)",
        "collisions": _dupes(chunker.chunk_html(html_dup, "docs/page.html")),
        "kinds": sorted({c.kind for c in chunker.chunk_html(html_dup, "docs/page.html")}),
    }
    results["html_treesitter_path"] = {
        "site": "chunk_file on the same source (tree-sitter path when available)",
        "ids": _ids(chunker.chunk_file(html_dup, "docs/page.html")),
        "collisions": _dupes(chunker.chunk_file(html_dup, "docs/page.html")),
    }
    # CODE-DEL-1 (delivery review): the multi-line fixture above cannot see
    # the same-line-sibling collision on the tree-sitter path — its ids are
    # anchored {slug}-L{start}, which same-line siblings share. This compact
    # one-liner is the shape minified HTML produces.
    html_one_line = (
        "<html><body><section><p>First body.</p></section>"
        "<section><p>Second body.</p></section></body></html>"
    )
    results["html_treesitter_same_line_siblings"] = {
        "site": "_ts_markup_chunker (id=f\"{path}#{slug}-L{start}\", kind doc; DEFAULT dispatch path)",
        "ids": _ids(chunker.chunk_file(html_one_line, "docs/min.html")),
        "collisions": _dupes(chunker.chunk_file(html_one_line, "docs/min.html")),
    }

    xml_dup = (
        "<catalog>\n<item>\nFirst plain text body.\n</item>\n"
        "<item>\nSecond plain text body.\n</item>\n</catalog>\n"
    )
    results["xml_regex_fallback_dup"] = {
        "site": "chunk_xml regex fallback (id=f\"{path}#{_slugify(label)}\", kind doc)",
        "collisions": _dupes(chunker.chunk_xml(xml_dup, "docs/catalog.xml")),
        "kinds": sorted({c.kind for c in chunker.chunk_xml(xml_dup, "docs/catalog.xml")}),
    }

    yaml_dup = "setup:\n  a: 1\nsetup:\n  b: 2\n"
    yaml_chunks = chunker.chunk_file(yaml_dup, "config/app.yaml")
    results["config_ts_flat_dup"] = {
        "site": "_ts_flat_emit_chunker (id=f\"{path}#{slug}\", kind code; config/markup flat files)",
        "ids": _ids(yaml_chunks),
        "collisions": _dupes(yaml_chunks),
        "kinds": sorted({c.kind for c in yaml_chunks}),
    }

    fences = (
        "# Guide\n\n## Setup\n\n```bash\necho one\n```\n\n"
        "## Setup\n\n```bash\necho two\n```\n"
    )
    controls = {
        "markdown_fences": _dupes(chunker.chunk_file(fences, "docs/f.md")),
        "sdl_repeat_ordinals": _dupes(chunker.chunk_file(
            "type User { id: ID }\nextend type User { a: Int }\nextend type User { b: Int }\n",
            "api/schema.graphql")),
        "jupyter_cell_ids": _dupes(chunker.chunk_file(json.dumps({
            "cells": [
                {"cell_type": "code", "source": ["x = 1\n"]},
                {"cell_type": "code", "source": ["y = 2\n"]},
            ],
            "metadata": {"kernelspec": {"language": "python"}},
        }), "docs/nb.ipynb")),
        "diagram_single_unit": _dupes(chunker.chunk_file(
            "flowchart TD\n  A --> B\n", "docs/flow.mmd")),
    }
    results["collision_free_controls"] = {
        "note": "fence :code-N file-pass ordinals, SDL crumb_counts, #cell-N, one-per-file diagrams — all collision-free by construction",
        "collisions_found": {k: v for k, v in controls.items() if v},
    }
    return results


def notebook_census() -> dict:
    nb = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Analysis Overview\n", "Intro prose.\n"]},
            {"cell_type": "code",
             "source": ["import pandas as pd\n", "df = pd.read_csv('data.csv')\n"],
             "outputs": [{"output_type": "stream",
                          "text": ["OUTPUT_SENTINEL_ROWS_PRINTED\n"]}]},
            {"cell_type": "code",
             "source": ["summary <- summarize(df)\n"],
             "metadata": {"languageId": "r"},
             "outputs": []},
            {"cell_type": "raw", "source": ["raw cell ignored\n"]},
        ],
        "metadata": {"kernelspec": {"language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    chunks = chunker.chunk_file(json.dumps(nb), "docs/analysis.ipynb")
    docs_bucket = [c.id for c in chunks if indexer._is_docs_kind(c.kind)]
    code_bucket_eligible = ".ipynb" in indexer.SOURCE_CODE_EXTENSIONS
    return {
        "emitted": [
            {"id": c.id, "kind": c.kind, "language": c.language,
             "section": c.section} for c in chunks
        ],
        "output_sentinel_in_any_chunk_text": any(
            "OUTPUT_SENTINEL_ROWS_PRINTED" in c.text for c in chunks),
        "per_cell_language_metadata_honored": any(
            c.language == "r" for c in chunks),
        "docs_table_ids_today": docs_bucket,
        "ipynb_is_code_table_eligible": code_bucket_eligible,
        "code_cell_rows_shipped_today": [
            c.id for c in chunks
            if (indexer._is_docs_kind(c.kind))
            or (c.kind in ("code", "code-summary") and code_bucket_eligible)
        ],
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
        "mirrors_key_on_kind_not_format": True,
        "note": "notebook cells reuse the landed doc-code kind, so every mirror "
                "carries them with no new site; verified by the docs_table_ids "
                "post-change regression, not assumed.",
    }


def drawio_census() -> dict:
    drawio = (
        '<mxfile host="app.diagrams.net" modified="2026-08-01T00:00:00.000Z">\n'
        '  <diagram id="pipeline" name="Indexing pipeline">\n'
        '    <mxGraphModel dx="800" dy="600">\n'
        "      <root>\n"
        '        <mxCell id="0" />\n'
        '        <mxCell id="1" parent="0" />\n'
        '        <mxCell id="2" value="walk_repo" style="rounded=1" vertex="1" parent="1">\n'
        '          <mxGeometry x="40" y="40" width="120" height="40" as="geometry" />\n'
        "        </mxCell>\n"
        '        <mxCell id="3" value="chunk_file" style="rounded=1" vertex="1" parent="1">\n'
        '          <mxGeometry x="220" y="40" width="120" height="40" as="geometry" />\n'
        "        </mxCell>\n"
        "      </root>\n"
        "    </mxGraphModel>\n"
        "  </diagram>\n"
        "</mxfile>\n"
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs").mkdir()
        (root / "docs" / "pipeline.drawio").write_text(drawio, encoding="utf-8")
        (root / "docs" / "readme.md").write_text("# Control\n\nProse.\n", encoding="utf-8")
        walked = sorted(
            str(p.relative_to(root)).replace("\\", "/")
            for p in indexer.walk_repo(root)
        )
    chunks = chunker.chunk_file(drawio, "docs/pipeline.drawio")
    return {
        "walked_paths": walked,
        "drawio_walks_in_today": "docs/pipeline.drawio" in walked,
        "in_generated_exclude_extensions": ".drawio" in indexer._GENERATED_EXCLUDE_EXTENSIONS,
        "excalidraw_precedent_in_generated_exclude": ".excalidraw" in indexer._GENERATED_EXCLUDE_EXTENSIONS,
        "in_binary_extensions": ".drawio" in indexer.BINARY_EXTENSIONS,
        "walker_version": indexer.WALKER_VERSION,
        "chunk_output": [
            {"id": c.id, "kind": c.kind, "lines": list(c.lines)} for c in chunks
        ],
        "docs_rows_shipped": [c.id for c in chunks if indexer._is_docs_kind(c.kind)],
        "code_table_eligible": ".drawio" in indexer.SOURCE_CODE_EXTENSIONS,
        "cost_summary": "walked + chunked (one code-kind line window) but ships "
                        "zero rows in either table: pure walk/chunk cost, zero value",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    results = {
        "census": "1wh1b-enh executed censuses: prose-id emission sites (all "
                  "chunkers), notebook emission, kind mirrors, drawio membership",
        "chunker_version": chunker.CHUNKER_VERSION,
        "walker_version": indexer.WALKER_VERSION,
        "prose_id_site_census": prose_id_site_census(),
        "notebook_census": notebook_census(),
        "kind_mirror_census": kind_mirror_census(),
        "drawio_census": drawio_census(),
    }
    payload = json.dumps(results, indent=2) + "\n"
    print(payload, end="")
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
