import json,glob,os,random
src=open("measure.py").read().split("# ---------- corpora ----------")[0]
exec(src)
random.seed(4)
d=git("diff","-U0",BASE,"--","docs/agents/session-handoff.md")
add="\n".join(l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++"))
ss=[s for _,s in sentences(add)]
p=[s for s in ss if passive(s)]
ag=[s for s in p if re.search(r"\bby (the|a|an|its|each|every|[A-Z])",s)]
print("handoff passive",len(p),"of",len(ss),"with by-agent",len(ag))
[print("  ~",s[:170]) for s in sample_examples(p,10)]
for lab,ws in [("POST",POST_W),("PRE",["20k0e","20lkx","20np5","20qvn","20st7","20e12","20b39","20oqx","20ngc"])]:
    ss=[s for _,s in sentences(specs(ws))]
    both=[s for s in ss if re.search(r"\bspecs?\b",s,re.I) and re.search(r"\b(the|this|each|every|a|admitted|one|sibling|its) changes?\b",s,re.I)]
    sp=sum(bool(re.search(r"\bspecs?\b",s,re.I)) for s in ss); ch=sum(bool(re.search(r"\b(the|this|each|every|a|admitted|one|sibling|its) changes?\b",s,re.I)) for s in ss)
    print(lab,"sentences",len(ss),"with spec",sp,"with change-as-noun",ch,"both",len(both))
    [print("  &",s[:230]) for s in sample_examples(both, 5)]
# -ing nominal starts and missing articles (telegraphic) in handoff/wave: sentences starting with a bare noun and no article within first 3 tokens - skip
# semicolons per 1000 words as a proxy for chained statements
R=json.load(open("measures.json"))
