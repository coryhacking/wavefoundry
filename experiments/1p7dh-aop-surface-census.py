#!/usr/bin/env python3
"""1p7dh Phase-0 AOP-surface census (read-only recon).

Characterizes the AOP / instrumentation surface of a Java repo so the upstream
Wavefoundry team can scope the advice-registration (`advises`) edge BEFORE
writing any extractor. Answers three questions:

  1. ByteBuddy-DSL vs AspectJ-annotation — which construct carries the
     instrumentation string (decides what to capture).
  2. Of the captured instrumentation TARGET strings, how many name a PROJECT
     type (the edge target would be a real graph node) vs a THIRD-PARTY type
     (not in the graph — the ceiling). This decides whether the edge model is
     even viable as project-node→project-node.
  3. Sample ground-truth rows (file, construct, string, classified target) to
     seed the external-oracle faithfulness check.

Regex-based, pure stdlib, any python3, READ-ONLY (no source or graph edits).

Usage:
  python3 1p7dh-aop-surface-census.py --root /path/to/java-repo

If <root>/.wavefoundry/index/graph/project-graph.json exists it is used to
classify captured type strings as project vs external (more accurate); otherwise
project types are harvested from `class/interface/enum` declarations in source.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# --- construct patterns -------------------------------------------------------
# AspectJ advice/aspect annotations, capturing an optional first string-literal arg.
ASPECTJ_ANN = re.compile(
    r'@(Around|Before|After|AfterReturning|AfterThrowing|Pointcut|Aspect|DeclareParents)\b'
    r'\s*(?:\(\s*"([^"]*)")?'
)
# ByteBuddy @Advice.* method markers (no string arg — the type binding is in the DSL).
BB_ADVICE_MARKER = re.compile(r'@Advice\.(On[A-Za-z]+)\b')
# ByteBuddy / ElementMatchers DSL matchers carrying a type/name string.
BB_MATCHER = re.compile(
    r'\b(named|namedIgnoreCase|nameStartsWith|nameStartsWithIgnoreCase|nameEndsWith|'
    r'nameContains|nameMatches|hasSuperType|isSubTypeOf|isAnnotatedWith|declaresMethod)'
    r'\s*\(\s*"([^"]+)"'
)
# ByteBuddy advice wiring: Advice.to(SomeAdvice.class)
ADVICE_TO = re.compile(r'\bAdvice\.to\(\s*([A-Za-z_][\w.]*)\.class')
# A fully-qualified type token (pkg.pkg.Type) inside any captured string/expression.
FQN_TYPE = re.compile(r'\b([a-z][\w]*(?:\.[a-z0-9_]+)*\.[A-Z]\w*)\b')
# Project type declarations (source fallback when no graph is present).
TYPE_DECL = re.compile(r'\b(?:class|interface|enum|@interface|record)\s+([A-Z]\w*)')


def load_project_types(root: Path) -> tuple[set[str], set[str]]:
    """Return (qualified_names, simple_names) of project Java types, from the
    graph if present, else from source declarations."""
    qual: set[str] = set()
    simple: set[str] = set()
    graph = root / ".wavefoundry/index/graph/project-graph.json"
    if graph.exists():
        try:
            g = json.loads(graph.read_text(encoding="utf-8"))
            for n in g.get("nodes", []):
                nid = str(n.get("id") or "")
                if "::" not in nid or not nid.split("::", 1)[0].endswith((".java", ".kt")):
                    continue
                if n.get("kind") not in ("class", "type", "interface", "enum"):
                    continue
                q = nid.split("::", 1)[1]
                qual.add(q)
                simple.add(q.rsplit(".", 1)[-1])
            if qual:
                return qual, simple
        except Exception:
            pass
    for p in root.rglob("*.java"):
        try:
            for m in TYPE_DECL.finditer(p.read_text(encoding="utf-8", errors="replace")):
                simple.add(m.group(1))
        except Exception:
            continue
    return qual, simple


def classify_target(s: str, qual: set[str], simple: set[str]) -> str:
    """Classify the type token(s) in a captured string: project / external / not-a-type."""
    cands = set(FQN_TYPE.findall(s))
    # bare TitleCase tokens (simple type names) as a weaker candidate
    bare = {t for t in re.findall(r'\b([A-Z]\w{2,})\b', s)}
    if any(c in qual for c in cands) or any(c.rsplit(".", 1)[-1] in simple for c in cands):
        return "project"
    if cands:
        return "external"            # looks like a FQN type, but not a project one (3rd-party)
    if bare & simple:
        return "project_simple"      # bare simple-name match (weaker; ambiguity risk)
    if bare:
        return "external_simple"
    return "non_type"                # a pointcut/expr with no resolvable type token


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--samples", type=int, default=20)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    qual, simple = load_project_types(root)
    print(f"root: {root}")
    print(f"project types known: {len(qual)} qualified / {len(simple)} simple "
          f"({'graph' if qual else 'source-decl fallback'})\n")

    ann = Counter(); ann_with_str = Counter(); markers = Counter()
    matchers = Counter(); advice_to = 0
    target_class = Counter()
    samples: list[tuple[str, str, str, str]] = []
    files = 0

    for p in root.rglob("*.java"):
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        files += 1
        rel = str(p.relative_to(root))
        for m in ASPECTJ_ANN.finditer(src):
            ann[m.group(1)] += 1
            if m.group(2) is not None:
                ann_with_str[m.group(1)] += 1
                cls = classify_target(m.group(2), qual, simple)
                target_class[cls] += 1
                if len(samples) < args.samples:
                    samples.append((rel, f"@{m.group(1)}", m.group(2)[:60], cls))
        for m in BB_ADVICE_MARKER.finditer(src):
            markers[m.group(1)] += 1
        for m in BB_MATCHER.finditer(src):
            matchers[m.group(1)] += 1
            cls = classify_target(m.group(2), qual, simple)
            target_class[cls] += 1
            if len(samples) < args.samples:
                samples.append((rel, m.group(1) + "()", m.group(2)[:60], cls))
        advice_to += len(ADVICE_TO.findall(src))

    print(f"scanned {files} .java files\n")
    print("=== AspectJ annotations (count / with-string-arg) ===")
    for k, c in ann.most_common():
        print(f"  @{k:18s} {c:5d}  (string-arg: {ann_with_str.get(k, 0)})")
    if not ann:
        print("  (none)")
    print("\n=== ByteBuddy @Advice.* method markers ===")
    for k, c in markers.most_common():
        print(f"  @Advice.{k:18s} {c:5d}")
    if not markers:
        print("  (none)")
    print(f"\n=== ByteBuddy / ElementMatchers DSL matchers (with string arg) ===")
    for k, c in matchers.most_common():
        print(f"  {k:24s} {c:5d}")
    if not matchers:
        print("  (none)")
    print(f"\nAdvice.to(X.class) wiring sites: {advice_to}")

    # framework verdict
    aspectj = sum(ann_with_str.values())
    bytebuddy = sum(matchers.values()) + sum(markers.values()) + advice_to
    print("\n=== Framework verdict ===")
    if bytebuddy and bytebuddy >= 2 * max(aspectj, 1):
        verdict = "BYTEBUDDY-DSL dominant — capture the DSL matcher call-site strings (named/nameStartsWith/...)"
    elif aspectj and aspectj >= 2 * max(bytebuddy, 1):
        verdict = "ASPECTJ-ANNOTATION dominant — capture the annotation pointcut strings"
    elif aspectj or bytebuddy:
        verdict = "MIXED — both ByteBuddy DSL and AspectJ annotations carry binding strings"
    else:
        verdict = "NO AOP binding strings found — advises edge likely N/A for this repo"
    print(f"  bytebuddy-signal={bytebuddy}  aspectj-signal={aspectj}  -> {verdict}")

    print("\n=== Instrumentation TARGET classification (the make-or-break) ===")
    tot = sum(target_class.values()) or 1
    for k in ("project", "project_simple", "external", "external_simple", "non_type"):
        v = target_class.get(k, 0)
        print(f"  {k:16s} {v:5d} ({v/tot:5.1%})")
    proj = target_class.get("project", 0) + target_class.get("project_simple", 0)
    print(f"  -> project-type targets (edge would bind a graph node): {proj}/{tot} ({proj/tot:.1%})")
    print(f"     external/third-party targets (NOT in the graph): "
          f"{tot - proj - target_class.get('non_type', 0)}/{tot}")

    print(f"\n=== Sample rows (oracle seed, up to {args.samples}) ===")
    for rel, construct, s, cls in samples:
        print(f"  [{cls:14s}] {construct:24s} \"{s}\"   ({rel})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
