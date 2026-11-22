"""Sentence-set difference: prose blocks present now that were absent at the selected base revision (robust to renames)."""
import json,glob,os
src=open("measure.py").read().split("# ---------- corpora ----------")[0]
exec(src)
def base_blocks(paths):
    s=set()
    for p in paths:
        for n in git("ls-tree","-r","--name-only",BASE,"--",p).split("\n"):
            if n.endswith(".md"):
                for k,b in blocks(git("show",f"{BASE}:{n}")): s.add(b)
    return s
def now_blocks(paths):
    out=[]
    for p in paths:
        fs=[os.path.join(REPO,p)] if p.endswith(".md") else sorted(glob.glob(os.path.join(REPO,p,"**/*.md"),recursive=True))
        for f in fs: out+=blocks(open(f,encoding="utf-8").read())
    return out
res=[]
for name,paths in [(f"seeds NEW blocks since {BASE} (set difference)",[".wavefoundry/framework/seeds"]),
                   (f"docs/prompts NEW blocks since {BASE}",["docs/prompts"]),
                   (f"handoff NEW blocks since {BASE}",["docs/agents/session-handoff.md"])]:
    old=base_blocks(paths); new=[b for b in now_blocks(paths) if b[1] not in old]
    m=measure(name,new); res.append(m)
    print({k:v for k,v in m.items() if not isinstance(v,(list,dict))})
    if "seeds" in name:
        print("MULTI:"); [print("  -",s[:260]) for s in m.get("multi_examples", [])[:12]]
        print("HEDGES",m.get("hedges", {}))
        import random; random.seed(5)
        ss=[s for _,s in sentences(new)]
        sh=[s for s in ss if re.search(r"\bshould\b|as needed|where possible|as appropriate|where appropriate|if possible",s,re.I)]
        print("HEDGE SENTS:"); [print("  ?",s[:300]) for s in sh[:16]]
        long=[s for s in ss if is_imperative(s) and len(words(s))>30]
        print("LONG IMPERATIVES",len(long)); [print("  !",s[:420]) for s in sample_examples(long, 6)]
json.dump(res,open("newprose.json","w"),indent=1)
