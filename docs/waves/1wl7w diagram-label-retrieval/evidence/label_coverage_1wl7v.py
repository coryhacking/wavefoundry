"""Label-coverage differential for change 1wl7v-enh (wave 1wl7w).

Requirement 6: proves every AUTHORED label in the committed drawio/excalidraw
fixtures appears in a docs-table-eligible chunk, and that the drawio result is
identical for the compressed and plain save forms. Non-vacuity by
revert-simulation: the same assertions against the PRE-CHANGE chunker (loaded
from ``git show HEAD``, which predates this wave's uncommitted edits) must
FAIL with every label missing (the files previously emitted only a zero-row
code-kind line window). The ghost sentinel must appear in NO chunk under the
new chunker (the isDeleted skip), asserted alongside coverage.

Also emits the CHUNK-LEVEL anchor-uniqueness proof for the golden queries:
raw-text scanning cannot see anchors inside compressed drawio bodies, so each
new golden anchor is proven to appear in exactly one chunk across the entire
chunked diagrams corpus.

MUST run under the tool venv from the repository root:
    ~/.wavefoundry/venv/bin/python "docs/waves/1wl7w diagram-label-retrieval/evidence/label_coverage_1wl7v.py" [--out <file>]
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
DIAGRAMS = SCRIPTS / "tests" / "fixtures" / "retrieval_golden" / "diagrams"
sys.path.insert(0, str(SCRIPTS))

import chunker as new_chunker  # noqa: E402

DOCS_TABLE_KINDS = {"doc", "seed", "prompt", "doc-summary", "doc-code"}
GHOST = "GHOST_DELETED_LABEL_SENTINEL"

AUTHORED_LABELS = {
    "drawio/platform-architecture.drawio": [
        "Ingress gateway terminates mutual TLS",
        "Edge proxy fleet",
        "Fraud scoring engine",
        "Ledger reconciliation worker",   # object-wrapper label
        "Columnar analytics store",
        "replicates snapshots to the cold region",
        "Cold region archive",
    ],
    "drawio/deploy-flow.drawio": [
        "Artifact signing service",
        "canary rollout gate checks error budget",
        "Production fleet",
    ],
    "excalidraw/incident-runbook.excalidraw": [
        "page the on-call resolver first",
        "escalate to the database owner after two failed probes",
        "rotate the incident commander every four hours",
        "Sev1 containment steps",
    ],
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
    spec = importlib.util.spec_from_file_location("old_lbl_chunker", tmp.name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["old_lbl_chunker"] = mod
    spec.loader.exec_module(mod)
    return mod


def coverage(mod) -> dict:
    report: dict = {"files": {}, "violations": []}
    for rel, labels in AUTHORED_LABELS.items():
        src = (DIAGRAMS / rel).read_text(encoding="utf-8")
        chunks = mod.chunk_file(src, rel)
        docs_blob = "\n".join(
            c.text for c in chunks if c.kind in DOCS_TABLE_KINDS)
        missing = [lb for lb in labels if lb not in docs_blob]
        ghost_leak = any(GHOST in c.text for c in chunks)
        report["files"][rel] = {
            "labels": len(labels), "covered": len(labels) - len(missing),
            "missing": missing, "ghost_leak": ghost_leak,
            "chunk_ids": [c.id for c in chunks],
        }
        if missing:
            report["violations"].append(f"{rel}: {len(missing)} labels missing")
        if ghost_leak:
            report["violations"].append(f"{rel}: ghost sentinel leaked")
    report["pass"] = not report["violations"]
    return report


def form_equivalence() -> dict:
    """Compressed vs plain drawio must extract identical label text."""
    import base64, urllib.parse, zlib, re
    src = (DIAGRAMS / "drawio" / "platform-architecture.drawio").read_text(
        encoding="utf-8")
    packed = [c.text for c in new_chunker.chunk_file(src, "d/x.drawio")]
    # Build the plain form by inflating each page body in place.
    def _inflate(m):
        body = m.group(2)
        raw = base64.b64decode(body)
        xml = urllib.parse.unquote(
            zlib.decompressobj(-15).decompress(raw).decode())
        return m.group(1) + xml + m.group(3)
    plain_src = re.sub(r"(<diagram[^>]*>)([A-Za-z0-9+/=]+)(</diagram>)",
                       _inflate, src)
    plain = [c.text for c in new_chunker.chunk_file(plain_src, "d/x.drawio")]
    return {"identical": packed == plain, "pages": len(packed)}


def anchor_uniqueness() -> dict:
    queries = json.loads(
        (SCRIPTS / "tests" / "fixtures" / "retrieval_golden"
         / "golden_queries_diagrams.json").read_text(encoding="utf-8"))
    new = [q for q in queries if "-" in q["id"]]
    all_chunks = []
    for f in sorted(p for p in DIAGRAMS.rglob("*") if p.is_file()):
        rel = str(f.relative_to(DIAGRAMS)).replace("\\", "/")
        for c in new_chunker.chunk_file(f.read_text(encoding="utf-8"), rel):
            all_chunks.append((rel, c.id, c.text))
    out = {}
    for q in new:
        hits = [cid for rel, cid, text in all_chunks
                if q["expected_anchor"] in text]
        out[q["id"]] = {"anchor": q["expected_anchor"], "chunks": hits,
                        "unique": len(hits) == 1}
    out["all_unique"] = all(v["unique"] for k, v in out.items()
                            if k != "all_unique")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    old_chunker = _load_old_chunker()
    forward = coverage(new_chunker)
    revert = coverage(old_chunker)
    equiv = form_equivalence()
    anchors = anchor_uniqueness()
    # Per-format non-vacuity (QA delivery advisory): one violation anywhere
    # is too coarse — the revert simulation must show BOTH formats losing
    # labels, or one format's differential could go blind unnoticed.
    revert_formats = {rel.split("/", 1)[0]
                      for rel, entry in revert["files"].items()
                      if entry["missing"] or entry["ghost_leak"]}
    results = {
        "differential": "1wl7v authored-label coverage over docs-eligible chunks",
        "old_chunker_version": old_chunker.CHUNKER_VERSION,
        "new_chunker_version": new_chunker.CHUNKER_VERSION,
        "forward": forward,
        "revert_simulation": {"pass": revert["pass"],
                              "violations": revert["violations"],
                              "formats_failing": sorted(revert_formats),
                              "non_vacuous": revert_formats >= {"drawio",
                                                               "excalidraw"}},
        "compressed_plain_equivalence": equiv,
        "anchor_uniqueness": anchors,
        "result": "PASS" if (forward["pass"]
                             and revert_formats >= {"drawio", "excalidraw"}
                             and equiv["identical"]
                             and anchors["all_unique"]) else "FAIL",
    }
    payload = json.dumps(results, indent=2) + "\n"
    print(payload, end="")
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    return 0 if results["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
