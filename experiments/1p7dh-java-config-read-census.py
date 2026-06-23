#!/usr/bin/env python3
"""1p7dh Phase-0 Java config-read census (read-only recon).

Scopes whether/how to extend `reads_config` to Java BEFORE building it. Answers:

  1. How does this repo read config? — `@Value("${k}")`, `getProperty("k")`,
     `getenv("K")`, typed getters, `@ConfigurationProperties` — and is the KEY a
     string LITERAL or a CONSTANT reference (constant refs are already covered by
     the existing `reads`->constant relation, so they are NOT the gap).
  2. Target locality of the LITERAL keys — do they bind to a graph node
     (a JSON config-key node, or a constant node by value/name) or are they
     UNBOUND (e.g. a Spring application.yml/.properties key that isn't indexed as
     a config-key node — which would mean reads_config-for-Java also needs
     properties/yaml config-key NODE extraction, the bigger half).
  3. A sample of literal keys + classification, to seed the design.

Regex-based, pure stdlib, READ-ONLY. Reads <root>/.wavefoundry/index/graph/
project-graph.json (if present) to classify keys against real graph nodes.

Usage: python3 1p7dh-java-config-read-census.py --root /path/to/java-repo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Config-read shapes. Each captures the KEY token (group 1) — a quoted literal,
# a ${...} placeholder body, or a bare CONSTANT identifier.
SHAPES = {
    "@Value-literal":      re.compile(r'@Value\(\s*"\$\{([^:}"]+)[:}]'),
    "getProperty-literal": re.compile(r'\bgetProperty\(\s*"([^"]+)"'),
    "getenv-literal":      re.compile(r'\bgetenv\(\s*"([^"]+)"'),
    "typed-getter-literal": re.compile(r'\b(?:getString|getInteger|getBoolean|getLong|getRequiredProperty)\(\s*"([^"]+)"'),
    "get-literal":         re.compile(r'\.get\(\s*"([^"]+)"\s*\)'),
    "ConfigurationProperties-prefix": re.compile(r'@ConfigurationProperties\(\s*(?:prefix\s*=\s*)?"([^"]+)"'),
}
# Constant-reference reads (key is an UPPER_SNAKE identifier, not a literal) —
# already covered by the existing reads->constant relation.
CONST_REF = re.compile(r'\b(?:getProperty|getenv|getRequiredProperty)\(\s*([A-Z][A-Z0-9_]{2,})\s*[\),]')


def load_graph_keys(root: Path):
    """Return (json_config_keys, json_config_leaves, constant_values, constant_names)."""
    json_keys, json_leaves, const_values, const_names = set(), set(), set(), set()
    g = root / ".wavefoundry/index/graph/project-graph.json"
    if g.exists():
        try:
            data = json.loads(g.read_text(encoding="utf-8"))
            for n in data.get("nodes", []):
                nid = str(n.get("id") or "")
                if "::" not in nid:
                    continue
                f, key = nid.split("::", 1)
                if f.endswith((".json", ".jsonc")) and ("config" in f.lower() or "profile" in f.lower()):
                    json_keys.add(key); json_leaves.add(key.rsplit(".", 1)[-1])
                if n.get("kind") == "constant":
                    const_names.add(key.rsplit(".", 1)[-1])
                    v = n.get("value")
                    if isinstance(v, str) and v:
                        const_values.add(v.strip('"\''))
        except Exception:
            pass
    return json_keys, json_leaves, const_values, const_names


def classify(key: str, jk, jl, cv, cn) -> str:
    if key in jk or key.rsplit(".", 1)[-1] in jl:
        return "json_config_node"
    if key in cv:
        return "constant_value"
    if key in cn:
        return "constant_name"
    return "unbound"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--samples", type=int, default=20)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    jk, jl, cv, cn = load_graph_keys(root)
    print(f"root: {root}")
    print(f"graph keys known: {len(jk)} json-config / {len(cv)} constant-values / "
          f"{len(cn)} constant-names ({'graph' if (jk or cv or cn) else 'NO GRAPH — build it first'})\n")

    shape_counts = Counter()
    target_class = Counter()
    const_ref_reads = 0
    samples: list[tuple[str, str, str]] = []
    files = 0
    for p in root.rglob("*.java"):
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        files += 1
        rel = str(p.relative_to(root))
        for shape, rx in SHAPES.items():
            for m in rx.finditer(src):
                key = m.group(1).strip()
                if not key:
                    continue
                shape_counts[shape] += 1
                cls = classify(key, jk, jl, cv, cn)
                target_class[cls] += 1
                if len(samples) < args.samples:
                    samples.append((shape, key[:50], cls))
        const_ref_reads += len(CONST_REF.findall(src))

    print(f"scanned {files} .java files\n")
    print("=== Config-read shapes (literal-key) ===")
    for k, c in shape_counts.most_common():
        print(f"  {k:34s} {c:5d}")
    if not shape_counts:
        print("  (none)")
    print(f"\nConstant-reference reads (already covered by reads->constant): {const_ref_reads}")

    print("\n=== Literal-key TARGET locality (the make-or-break) ===")
    tot = sum(target_class.values()) or 1
    for k in ("json_config_node", "constant_value", "constant_name", "unbound"):
        v = target_class.get(k, 0)
        print(f"  {k:18s} {v:5d} ({v/tot:5.1%})")
    bindable = tot - target_class.get("unbound", 0)
    print(f"  -> literal keys that would bind an existing node: {bindable}/{tot} ({bindable/tot:.1%})")
    print(f"     unbound (need properties/yaml config-key NODE extraction): {target_class.get('unbound', 0)}/{tot}")

    print("\n=== Verdict ===")
    lit = sum(shape_counts.values())
    if lit == 0:
        print("  No literal-based config reads — config is constant-based; the existing")
        print("  reads->constant relation covers it. reads_config-for-Java would be a no-op here.")
    elif target_class.get("unbound", 0) > bindable:
        print("  Literal-based reads exist but mostly UNBOUND → reads_config-for-Java needs")
        print("  properties/yaml config-key NODE extraction first (the bigger half).")
    else:
        print("  Literal-based reads bind existing nodes → a Java literal-capture extension")
        print("  (mirroring the Python capture into the Java extractor) would add real edges.")

    print(f"\n=== Sample literal keys (up to {args.samples}) ===")
    for shape, key, cls in samples:
        print(f"  [{cls:16s}] {shape:24s} \"{key}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
