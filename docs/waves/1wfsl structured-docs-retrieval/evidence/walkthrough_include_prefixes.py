"""AC-1 walkthrough for 1wdvr-doc (wave 1wfsl): the shipped guidance, executed
end-to-end against a sample repository fixture.

This walkthrough also RECORDS an implementation-time falsification: the plan's
original recipe framing ("a directory outside its default code roots ... add it
to the list") assumed `indexing.project_include_prefixes.code` restricts the
corpus. Executing the real filters disproved that — the code corpus spans the
WHOLE repository by default (everything outside `.wavefoundry/`, the corpus
exclusions, and ignore files), and the prefixes list is the opt-back-in past
the `.wavefoundry/` blanket. The shipped guidance was corrected to say so, and
this walkthrough proves BOTH halves of the corrected guidance:

Part A (default coverage): an OpenAPI spec in an ordinary non-source directory
(`api-contracts/`) is in the code corpus with NO configuration, and a semantic
query hits its operation chunk after a real build.

Part B (the opt-in recipe): the same spec nested under `.wavefoundry/contracts/`
is blanket-excluded; adding `.wavefoundry/contracts` to
`indexing.project_include_prefixes.code` (the guidance's config step), then
rebuilding (the rebuild step), makes a semantic query hit it (the verify step —
the same embedder + Lance vector search `code_search` performs).

Run with the wavefoundry tool venv python (embedding models required):
    ~/.wavefoundry/venv/bin/python "docs/waves/1wfsl structured-docs-retrieval/evidence/walkthrough_include_prefixes.py"
Writes walkthrough_include_prefixes_result.json next to this script.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import numpy as np  # noqa: E402

import indexer  # noqa: E402

SPEC = """openapi: 3.0.3
info:
  title: Orders API
  description: Contract for the order fulfillment service.
paths:
  /orders/{orderId}/refund:
    post:
      summary: Refund a fulfilled order
      description: >-
        Issues a refund for a fulfilled order. Refunds are asynchronous and
        settle within two business days; partial refunds require the original
        line-item identifiers.
      responses:
        '202':
          description: Refund accepted for asynchronous settlement.
"""

APP = "def fulfill(order_id):\n    \"\"\"Fulfill an order by id.\"\"\"\n    return order_id\n"

QUERY = "how do I refund a fulfilled order"


def write_config(root: Path, code_prefixes: list[str]) -> None:
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "workflow-config.json").write_text(json.dumps({
        "indexing": {"project_include_prefixes": {"docs": [], "code": code_prefixes}},
    }), encoding="utf-8")


def code_corpus_rels(root: Path) -> set[str]:
    files = indexer.walk_repo(root, respect_ignore=True)
    files = indexer._filter_project_index_excludes(
        files, root, None,
        project_include_prefixes=indexer._effective_project_include_prefixes(
            root, root / ".wavefoundry" / "index", "code", None),
    )
    files = indexer._filter_code_files(files, root, include_tests=False,
                                       include_generated=False)
    return {str(p.relative_to(root)).replace("\\", "/") for p in files}


def semantic_hit_rank(root: Path, expected_path: str) -> tuple[int, list[dict]]:
    """The verification step: same embedder + Lance vector search as code_search."""
    import lancedb
    db = lancedb.connect(str(root / ".wavefoundry" / "index"))
    table = db.open_table("code")
    embedder = indexer._get_embedder(indexer.CODE_MODEL)
    prefix = indexer.query_embedding_prefix(indexer.CODE_MODEL)
    qvec = np.asarray(
        list(embedder.embed([prefix + QUERY], batch_size=1))[0], dtype=np.float32
    )
    hits = table.search(qvec).limit(5).to_list()
    tops = [
        {"path": h.get("path"), "chunk_id": h.get("id"), "section": h.get("section")}
        for h in hits
    ]
    paths = [h["path"] for h in tops]
    rank = 1 + paths.index(expected_path) if expected_path in paths else 0
    return rank, tops


def main() -> int:
    result: dict = {"walkthrough": "1wdvr-doc AC-1 corrected-guidance walkthrough"}

    # Part A: ordinary directory — searchable by DEFAULT (no configuration).
    with tempfile.TemporaryDirectory(prefix="wf-1wdvr-a-") as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text(APP, encoding="utf-8")
        (root / "api-contracts").mkdir()
        (root / "api-contracts" / "orders-api.yaml").write_text(SPEC, encoding="utf-8")
        corpus = code_corpus_rels(root)
        assert "api-contracts/orders-api.yaml" in corpus, corpus
        indexer.build_index(root, content="code", full=True, verbose=False)
        rank, tops = semantic_hit_rank(root, "api-contracts/orders-api.yaml")
        assert rank > 0, tops
        result["part_a_default_coverage"] = {
            "corpus_membership_no_config": True,
            "query": QUERY,
            "spec_hit_rank": rank,
            "top_hits": tops,
        }

    # Part B: .wavefoundry/-nested spec — blanket-excluded, then opted in.
    with tempfile.TemporaryDirectory(prefix="wf-1wdvr-b-") as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text(APP, encoding="utf-8")
        nested = root / ".wavefoundry" / "contracts"
        nested.mkdir(parents=True)
        (nested / "orders-api.yaml").write_text(SPEC, encoding="utf-8")

        before = code_corpus_rels(root)
        assert ".wavefoundry/contracts/orders-api.yaml" not in before, before

        # The guidance's config step.
        write_config(root, [".wavefoundry/contracts"])
        after = code_corpus_rels(root)
        assert ".wavefoundry/contracts/orders-api.yaml" in after, after

        # The rebuild step (real build), then the verify step.
        indexer.build_index(root, content="code", full=True, verbose=False)
        rank, tops = semantic_hit_rank(root, ".wavefoundry/contracts/orders-api.yaml")
        assert rank > 0, tops
        result["part_b_prefix_opt_in"] = {
            "excluded_before_prefix": True,
            "included_after_prefix": True,
            "query": QUERY,
            "spec_hit_rank": rank,
            "top_hits": tops,
        }

    result["verdict"] = (
        "GUIDANCE VERIFIED: default coverage hits the ordinary-directory spec; "
        "the prefix opt-in makes the blanket-excluded spec searchable"
    )
    out = Path(__file__).with_name("walkthrough_include_prefixes_result.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
