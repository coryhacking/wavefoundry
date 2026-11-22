"""Condition order in instructions; article-free (telegraphic) sentences; long paragraphs."""
import json,glob,os,random
src=open("measure.py").read().split("# ---------- corpora ----------")[0]
exec(src)
random.seed(6)
N=json.load(open("newprose2.json"))
def load_new():
    # recompute new blocks the same way as newprose2 by reading its cached sentences is not possible; rerun import
    import runpy,io,contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        g=runpy.run_path("newprose2.py")
    return g["new"],g["touched"]
new,touched=load_new()
TRAIL=re.compile(r"\S\s+(if|unless|when|only when|only if|once|after|before|until)\s+\w+",re.I)
LEAD=re.compile(r"^(If|Unless|When|Once|After|Before|Until|On|For|With|In|During|Where)\b")
def cond(blocks_,lab):
    ss=[s for _,s in sentences(blocks_)]
    imp=[s for s in ss if is_imperative(s)]
    trail=[s for s in imp if re.search(r"\b(if|unless|only when|only if)\b",s)]
    lead=[s for s in ss if re.match(r"^(If|Unless|When|Once|Only when|Only if)\b",s) and re.search(r",\s+(%s)\b"%"|".join(IMPER),s)]
    print(lab,"imperative",len(imp),"action-first with trailing if/unless",len(trail),"condition-first instructions",len(lead))
    return trail
t=cond(new,"seeds+prompts NEW"); [print("  >",s[:220]) for s in sample_examples(t, 8)]
cond(touched,"seeds+prompts TOUCHED")
ART=re.compile(r"\b(a|an|the|this|that|these|those|its|their|each|every|no|all|both|any|one|two|three|four|five|six)\b",re.I)
def tele(lab,bl):
    ss=[s for _,s in sentences(bl)]
    long=[s for s in ss if len(words(s))>=8]
    t=[s for s in long if not ART.search(s)]
    rate = round(100 * len(t) / len(long), 1) if long else "(no observations)"
    print(lab,"sentences>=8w",len(long),"with no article/determiner",len(t),rate)
    return t
def waves(ws,fn):
    return [f for w in ws for d in glob.glob(f"{REPO}/docs/waves/{w}*") for f in glob.glob(d+"/"+fn)]
POST=POST_W; PRE=["20k0e","20lkx","20np5","20qvn","20st7","20e12","20b39","20oqx","20ngc"]
def obs(ws):
    out=[]
    def walk(o):
        if isinstance(o,dict):
            for k,v in o.items():
                if k=="observed" and isinstance(v,str): out.append(("para",v))
                else: walk(v)
        elif isinstance(o,list):
            for v in o: walk(v)
    for f in waves(ws,"events.jsonl"):
        for l in open(f):
            try: walk(json.loads(l))
            except Exception: pass
    return out
x=tele("review observed POST",obs(POST)); [print("  .",s[:180]) for s in sample_examples(x,6)]
tele("review observed PRE",obs(PRE))
tele("specs POST",specs(POST)); tele("specs PRE",specs(PRE))
d=git("diff","-U0",BASE,"--","docs/agents/session-handoff.md")
tele("handoff added","\n".join(l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")))
tele("handoff PRE",git("show",BASE+"^:docs/agents/session-handoff.md"))
CL=open(REPO+"/CHANGELOG.md").read()
# paragraph sentence counts
def paras(lab,text):
    n=[len(SPLIT.split(clean(b))) for k,b in (blocks(text) if isinstance(text,str) else text)]
    n=[x for x in n if x>=1]
    if not n:
        print(lab, "blocks", 0, "(no observations)")
        return
    print(lab,"blocks",len(n),"median sents",statistics.median(n),"over6 %",round(100*sum(x>6 for x in n)/len(n),1),"max",max(n))
paras("specs POST",specs(POST)); paras("specs PRE",specs(PRE)); paras("seeds NEW",new); paras("observed POST",obs(POST)); paras("observed PRE",obs(PRE))
