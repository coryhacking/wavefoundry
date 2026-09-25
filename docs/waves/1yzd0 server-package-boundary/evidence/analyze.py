"""Derive per-module importer tables from scan.json.

prod = file directly in scripts/ or wave_lint_lib/ (not tests/, benchmarks/)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

d = json.load(open(Path(__file__).with_name("scan.json")))
SP = ".wavefoundry/framework/scripts/"


def cls(f):
    r = f[len(SP):] if f.startswith(SP) else f
    if r.startswith("tests/"):
        return "test"
    if r.startswith("benchmarks/"):
        return "bench"
    if r.startswith("wave_lint_lib/"):
        return "wll"
    if "/" not in r:
        return "prod"
    return "other"


def stem(f):
    r = f[len(SP):] if f.startswith(SP) else f
    if r.startswith("wave_lint_lib/"):
        return "wave_lint_lib"
    return Path(r).stem


by_mod = defaultdict(lambda: defaultdict(list))
for f, refs in d["py"].items():
    for r in refs:
        m = r["mod"]
        if stem(f) == m and cls(f) in ("prod", "wll"):
            continue  # self refs
        by_mod[m][f].append(r)

mode = sys.argv[1] if len(sys.argv) > 1 else "summary"
mods = sys.argv[2:] or d["universe"]
if mode == "summary":
    for m in mods:
        files = by_mod.get(m, {})
        prod = sorted(stem(f) for f in files if cls(f) in ("prod", "wll"))
        tests = [f for f in files if cls(f) == "test"]
        other = [f for f in files if cls(f) not in ("prod", "wll", "test")]
        print(f"{m}: prod_importers={len(prod)} tests={len(tests)} other={len(other)} :: {', '.join(prod)}")
elif mode == "detail":
    for m in mods:
        print(f"### {m}")
        for f, refs in sorted(by_mod.get(m, {}).items()):
            for r in refs:
                print(f"  {cls(f):5} {f[len(SP):] if f.startswith(SP) else f}:{r['line']} [{r['kind']}/{r['scope']}] {r['text']}")
        for f, hits in d["nonpy"].items():
            for h in hits:
                if h["mod"] == m:
                    print(f"  nonpy {f}:{h['line']} {h['text']}")
elif mode == "deps":
    # what each module in mods imports (prod files only)
    for m in mods:
        f = SP + m + ".py"
        refs = d["py"].get(f, [])
        seen = defaultdict(set)
        for r in refs:
            if r["mod"] != m:
                seen[r["mod"]].add(f"{r['kind'].split(':')[0]}/{r['scope']}")
        print(f"{m} -> " + "; ".join(f"{k}({','.join(sorted(v))})" for k, v in sorted(seen.items())))
