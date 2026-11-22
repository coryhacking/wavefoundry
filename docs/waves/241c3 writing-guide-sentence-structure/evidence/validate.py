import json,random,re,sys
sys.argv=[sys.argv[0]]
import importlib.util
src=open("measure.py").read().split("# ---------- corpora ----------")[0]
exec(src)
R={r["corpus"]:r for r in json.load(open("measures.json"))}
random.seed(11)
post=[]; pre=[]
for k,r in R.items():
    if "POST" in k and "EARLY" not in k and "tasks" not in k and "requirements" not in k: post+=r.get("noun_cluster_examples", [])
    if "PRE" in k and "tasks" not in k and "requirements" not in k and "seeds" not in k: pre+=r.get("noun_cluster_examples", [])
print("POST sample:"); [print(" ",i,x) for i,x in enumerate(sample_examples(post,40))]
print("PRE sample:"); [print(" ",i,x) for i,x in enumerate(sample_examples(pre,40))]
# handoff added lines
d=git("diff","-U0",BASE,"--","docs/agents/session-handoff.md")
add="\n".join(l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++"))
m=measure(f"handoff POST (lines added since {BASE})",add)
print({k:v for k,v in m.items() if not isinstance(v,(list,dict))})
json.dump(m,open("handoff_added.json","w"),indent=1)
# passive precision sample
import glob
txt=R  # reuse: re-derive sentences from changelog post
CL=open(REPO+"/CHANGELOG.md").read()
ss=[s for _,s in sentences(CL) if passive(s)]
print("PASSIVE sample:"); [print("  ~",s[:200]) for s in sample_examples(ss,12)]
