"""Genuinely new seed/prompt blocks: max word-set Jaccard against every block at the selected base revision below 0.5."""
import json,glob,os,random
src=open("measure.py").read().split("# ---------- corpora ----------")[0]
exec(src)
def base_blocks(paths):
    s=[]
    for p in paths:
        for n in git("ls-tree","-r","--name-only",BASE,"--",p).split("\n"):
            if n.endswith(".md"):
                s+=[b for k,b in blocks(git("show",f"{BASE}:{n}"))]
    return s
def now_blocks(paths):
    out=[]
    for p in paths:
        for f in sorted(glob.glob(os.path.join(REPO,p,"**/*.md"),recursive=True)): out+=blocks(open(f,encoding="utf-8").read())
    return out
paths=[".wavefoundry/framework/seeds","docs/prompts"]
old=base_blocks(paths); oldset=set(old)
ws=lambda b:frozenset(w.lower() for w in words(b))
oldw=[ws(b) for b in set(old) if len(words(b))>=4]
inv={}
for i,s in enumerate(oldw):
    for w in s: inv.setdefault(w,[]).append(i)
new=[];touched=[]
seen=set()
for k,b in now_blocks(paths):
    if b in oldset or b in seen: continue
    seen.add(b)
    s=ws(b)
    if len(s)<4: continue
    cand={}
    for w in s:
        l=inv.get(w,[])
        if len(l)<400:
            for i in l: cand[i]=cand.get(i,0)+1
    best=0
    for i,c in sorted(cand.items(),key=lambda x:-x[1])[:30]:
        j=len(s&oldw[i])/len(s|oldw[i]); best=max(best,j)
    (new if best<0.5 else touched).append((k,b))
out=[]
touched_label = "edited pre-adoption blocks" if BASE == ADOPTION_COMMIT else f"edited blocks from {BASE}"
for name,c in [(f"seeds+prompts NEW (no near match at {BASE})",new),(f"seeds+prompts TOUCHED ({touched_label})",touched)]:
    m=measure(name,c); out.append(m)
    print({k:v for k,v in m.items() if not isinstance(v,(list,dict))}); print("HEDGES",m.get("hedges", {}))
json.dump(out,open("newprose2.json","w"),indent=1)
random.seed(2)
ss=[s for _,s in sentences(new)]
print("NEW multi:"); [print("  -",s[:240]) for s in sample_examples([s for s in ss if is_imperative(s) and multi_instr(s)],10)]
print("NEW hedges:"); [print("  ?",s[:260]) for s in ss if re.search(r"\bshould\b|as needed|where possible|as appropriate|where appropriate|if possible",s,re.I)][:12]
print("NEW random paras:"); [print("  #",b[:700]) for k,b in sample_examples([x for x in new if len(words(x[1]))>40],5)]
