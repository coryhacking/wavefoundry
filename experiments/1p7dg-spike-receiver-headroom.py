#!/usr/bin/env python3
"""1p7dg measurement spike (AC-1) — per-language receiver-resolution headroom.

Graph-only, language-agnostic, pure stdlib. Point it at any repo that has a
built wavefoundry graph and it triages each language's EXTRACTED call edges into:

  1. bound-to-project-node ......... PROMOTION headroom (v23-style; faithfulness-
                                     benign — the edge already binds a unique node,
                                     only the confidence label is under-tagged).
                                     Split same-file vs cross-file.
  2. external + unique project leaf  RESOLUTION headroom (the "extend the per-
                                     language receiver resolver" work — a project
                                     symbol with that name exists and is UNIQUE,
                                     so better receiver typing could bind it).
  3. external + ambiguous leaf ..... HARD resolution headroom (>1 project symbol
                                     with that name — needs a real receiver TYPE
                                     to disambiguate; the wrong-twin risk zone).
  4. external + no project leaf .... CEILING (third-party / dynamic — drop).

Per-language verdict heuristic:
  - bucket 1 dominant  -> PROMOTE (cheap, faithful) — what Python needed.
  - bucket 2 material  -> EXTEND RESOLVER (per-language, faithfulness-reviewed).
  - buckets 3/4 dominant -> near ceiling -> DROP, record the data.

Usage:
  python3 1p7dg-spike-receiver-headroom.py --root /path/to/repo
  python3 1p7dg-spike-receiver-headroom.py            # defaults to wavefoundry

The repo must have a graph at <root>/.wavefoundry/index/graph/project-graph.json.
Build one with:  index_build(content='graph', mode='rebuild')   (MCP)
              or  python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --include-code --root <root>

Side B (Python-only source-AST receiver census) runs only when --root has Python.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from pathlib import Path

EXT_LANG = {
    ".py": "python", ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".cs": "csharp", ".go": "go", ".rs": "rust", ".swift": "swift",
    ".rb": "ruby", ".php": "php", ".scala": "scala",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".cjs": "javascript", ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp",
    ".sql": "sql",
}


def node_lang(node):
    return EXT_LANG.get(Path(node.get("source_file") or "").suffix.lower(), "")


def _leaf(symbol: str) -> str:
    """Last simple-name segment of a node id or external target."""
    s = symbol.split("::", 1)[-1]          # drop file prefix
    s = s.split("external::", 1)[-1]       # drop external:: prefix if present
    return s.rsplit(".", 1)[-1].rsplit("/", 1)[-1]


def analyze(payload):
    nodes = [n for n in payload.get("nodes", []) if isinstance(n.get("id"), str)]
    node_ids = {n["id"] for n in nodes}
    by_id = {n["id"]: n for n in nodes}
    # project simple-name -> count (for resolution-headroom triage of external targets)
    leaf_count: Counter = Counter()
    for n in nodes:
        if n.get("kind") in ("function", "method", "class", "constant", "type"):
            leaf_count[_leaf(n["id"])] += 1

    tiers: dict = {}      # lang -> Counter(confidence tier)
    buckets: dict = {}    # lang -> Counter(triage bucket)
    for e in payload.get("edges", []):
        if e.get("relation") != "calls":
            continue
        conf = str(e.get("confidence") or "").upper()
        tgt = str(e.get("target") or "")
        src = str(e.get("source") or "")
        lang = ""
        for nid in (src, tgt):
            n = by_id.get(nid)
            if n:
                lang = node_lang(n)
                if lang:
                    break
        if not lang:
            # external target with no node — attribute by source file ext
            lang = EXT_LANG.get(Path(src.split("::", 1)[0]).suffix.lower(), "")
        if not lang:
            continue
        tiers.setdefault(lang, Counter())[conf] += 1
        if conf != "EXTRACTED":
            continue
        b = buckets.setdefault(lang, Counter())
        if tgt in node_ids and not tgt.startswith("external::"):
            same = src.split("::", 1)[0] == tgt.split("::", 1)[0]
            b["1_promote_same_file" if same else "1_promote_cross_file"] += 1
        else:
            c = leaf_count.get(_leaf(tgt), 0)
            if c == 1:
                b["2_resolve_unique"] += 1
            elif c > 1:
                b["3_resolve_ambiguous"] += 1
            else:
                b["4_ceiling_external"] += 1
    return tiers, buckets


def verdict(b: Counter) -> str:
    tot = sum(b.values()) or 1
    promote = b["1_promote_same_file"] + b["1_promote_cross_file"]
    resolve = b["2_resolve_unique"]
    if promote / tot >= 0.25:
        return f"PROMOTE (v23-style; {promote/tot:.0%} of EXTRACTED already bound)"
    if resolve / tot >= 0.15:
        return f"EXTEND RESOLVER ({resolve/tot:.0%} external w/ a unique project symbol)"
    return "near CEILING -> DROP (record data)"


# --- Side B: Python-only source-AST receiver census (optional) ---------------

class ReceiverCensus(ast.NodeVisitor):
    def __init__(self):
        self.cat = Counter(); self._typed = [{}]; self._ctor = [{}]
    def _f(self, node):
        self._typed.append(dict(self._typed[-1])); self._ctor.append(dict(self._ctor[-1]))
        for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            if a.annotation is not None:
                self._typed[-1][a.arg] = True
        self.generic_visit(node); self._typed.pop(); self._ctor.pop()
    visit_AsyncFunctionDef = visit_FunctionDef = _f
    def visit_AnnAssign(self, n):
        if isinstance(n.target, ast.Name):
            self._typed[-1][n.target.id] = True
        self.generic_visit(n)
    def visit_Assign(self, n):
        if (isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                and n.value.func.id[:1].isupper()):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    self._ctor[-1][t.id] = True
        self.generic_visit(n)
    def visit_Call(self, n):
        f = n.func
        if isinstance(f, ast.Attribute):
            r = f.value
            if isinstance(r, ast.Name):
                if r.id in ("self", "cls"): self.cat["self_cls"] += 1
                elif r.id in self._typed[-1]: self.cat["RECOVERABLE_annotated"] += 1
                elif r.id in self._ctor[-1]: self.cat["RECOVERABLE_constructed"] += 1
                else: self.cat["untyped_name_recv"] += 1
            else: self.cat["other_recv"] += 1
        elif isinstance(f, ast.Name): self.cat["bare_call"] += 1
        self.generic_visit(n)


def side_b(root: Path):
    cat = Counter(); files = 0
    for p in root.rglob("*.py"):
        rp = str(p.relative_to(root))
        if "__pycache__" in rp or "/tests/" in f"/{rp}" or rp.startswith("experiments/"):
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        files += 1; c = ReceiverCensus(); c.visit(tree); cat.update(c.cat)
    return files, cat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--side-b", action="store_true", help="run the Python-only source census")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    graph = root / ".wavefoundry/index/graph/project-graph.json"
    if not graph.exists():
        print(f"NO GRAPH at {graph}\nBuild one first: index_build(content='graph', mode='rebuild')\n"
              f"or: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --include-code --root {root}")
        return 1
    payload = json.loads(graph.read_text(encoding="utf-8"))
    print(f"root: {root}\nbuilder_version: {payload.get('builder_version')}\n")
    tiers, buckets = analyze(payload)

    print("=== Per-language calls-edge confidence ===")
    for lang in sorted(tiers):
        c = tiers[lang]; total = sum(c.values()); ext = c.get("EXTRACTED", 0)
        print(f"  {lang:12s} calls={total:6d}  EXTRACTED={ext:6d} ({ext/total:5.1%})  "
              + " ".join(f"{k}={v}" for k, v in sorted(c.items()) if k != "EXTRACTED"))

    print("\n=== EXTRACTED triage + per-language AC-1 verdict ===")
    for lang in sorted(buckets):
        b = buckets[lang]; tot = sum(b.values()) or 1
        print(f"  {lang}: EXTRACTED={tot}")
        for k in ("1_promote_same_file", "1_promote_cross_file",
                  "2_resolve_unique", "3_resolve_ambiguous", "4_ceiling_external"):
            v = b.get(k, 0)
            print(f"      {k:22s} {v:6d} ({v/tot:5.1%})")
        print(f"      -> {verdict(b)}\n")

    if args.side_b:
        files, cat = side_b(root)
        if files:
            print(f"=== Side B: Python source census ({files} files) ===")
            for k, v in cat.most_common():
                print(f"  {k:26s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
