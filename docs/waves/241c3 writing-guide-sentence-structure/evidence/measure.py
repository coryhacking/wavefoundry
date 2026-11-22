#!/usr/bin/env python3
"""Prose measures for the STE review. Read-only on the repo."""
import json, re, subprocess, sys, glob, os, statistics, collections, random
from pathlib import Path
REPO = os.environ.get("WF_REPO") or subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
ADOPTION_COMMIT = "189a2502"
BASE = os.environ.get("WF_BASE", ADOPTION_COMMIT)  # diff base for "added since" corpora; set to the release commit on a re-run
_DEFAULT_POST_W = ["23z45", "23z46", "23zbf", "23zbg", "23xo7", "23ve6"]
POST_W = os.environ.get("WF_POST_WAVES", " ".join(_DEFAULT_POST_W)).split()  # wave id prefixes, space-separated
POST_VERSIONS = set(os.environ.get("WF_POST_VERSIONS", "Unreleased 1.43.0 1.44.0 1.44.1 1.45.0 1.46.0 1.47.0").split())
if not REPO:
    sys.exit("measure.py: repository root not found; set WF_REPO")
def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True).stdout

# ---------- prose extraction ----------
META = re.compile(r"^(Owner|Status|Last verified|Change Status|Wave|Kind|Priority|Type|Created|Updated|Change ID|Wave ID)\s*:", re.I)
def blocks(md):
    """Yield prose blocks (paragraphs / list items). Skips code fences, tables, headings, metadata."""
    out, fence = [], False
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = not fence; continue
        if fence or not s: continue
        if s.startswith("|") or s.startswith("#") or s.startswith("<!--") or META.match(s): continue
        if re.match(r"^[-=*_]{3,}$", s): continue
        kind = "para"
        m = re.match(r"^(?:[-*+]|\d+[.)])\s+(\[[ x~X]\]\s+)?", s)
        if m:
            kind = "item"; s = s[m.end():]
        s = s.lstrip("> ").strip()
        out.append((kind, s))
    return out
def clean(s):
    s = re.sub(r"`[^`]*`", " IDENT ", s)                 # inline code -> one token
    s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", s)     # links -> label
    s = re.sub(r"https?://\S+", " IDENT ", s)
    s = re.sub(r"\*\*|__|(?<!\w)[*_](?=\w)|(?<=\w)[*_](?!\w)", "", s)
    s = re.sub(r"\b[\w./-]+\.(md|py|json|jsonl|toml|js|css|cjs|sh|ps1|txt|yaml|yml)\b", " IDENT ", s)
    s = re.sub(r"\b\w+(_\w+)+\b", " IDENT ", s)           # snake_case identifiers
    s = re.sub(r"\b(e\.g|i\.e|etc|vs)\.", lambda m: m.group(1).replace(".", ""), s)
    s = re.sub(r"\bv?\d+(\.\d+)+\b", " NUM ", s)
    return re.sub(r"\s+", " ", s).strip()
SPLIT = re.compile(r"(?<=[.!?])[\"”')\]]*\s+(?=[\"“(\[]?[A-Z`])")
def sentences(text):
    res = []
    for kind, raw in blocks(text) if isinstance(text, str) else text:
        c = clean(raw)
        for s in SPLIT.split(c):
            s = s.strip()
            w = words(s)
            if len(w) >= 3: res.append((kind, s))
    return res
def words(s):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’/-]*", s)

# ---------- heuristics ----------
IRREG = "written known shown given taken made done run kept held built sent set put read left found lost seen drawn thrown chosen broken frozen driven hidden bound told sold paid met cut split spent caught brought bought taught thought understood begun gone".split()
PASSIVE = re.compile(r"\b(is|are|was|were|be|been|being|gets|get|got)\s+(?:(?:not|never|also|only|still|already|then|now|always|\w+ly)\s+){0,2}(\w+ed|%s)\b" % "|".join(IRREG), re.I)
NOT_PART = {"need","indeed","speed","feed","embed","seed","exceed","proceed","succeed","red","shed","hundred","unused","based","supposed","allowed","required" } - {"based","supposed","allowed","required"}
def passive(s):
    for m in PASSIVE.finditer(s):
        if m.group(2).lower() not in NOT_PART: return True
    return False
HEDGES = [r"\bshould\b", r"\bas needed\b", r"\bwhere possible\b", r"\bif feasible\b", r"\bas appropriate\b", r"\bwhere appropriate\b",
          r"\bwhen(?:ever)? possible\b", r"\bif possible\b", r"\bas necessary\b", r"\bwhere practical\b", r"\bwhen practical\b", r"\bideally\b", r"\bwhere feasible\b"]
FUNC = set("""a an the this that these those of in on at to for from by with without within into onto over under between through during before after
above below against about across per via as than and or nor but so yet if when while where whether because unless until though although since
is are was were be been being am do does did has have had having will would shall should may might can could must not no never only also still
it its they them their he she we our you your i who whom whose which what there here then now each every any all some both either neither none
more most less least very too just even such same other another own out up down off again once
uses use used using keeps keep kept adds add added runs run reads read writes write names name named records record recorded returns return returned
reports report reported checks check checked needs need needed makes make made gives give gave gets get got takes take took shows show showed
says say said states state stated stays stay remains remain becomes become requires require required fails fail failed passes pass passed
carries carry holds hold lets let means mean covers cover applies apply calls call called opens open closes close refuses refuse blocks block
includes include contains contain leaves leave left sets set changes change changed moves move creates create removes remove tells tell
no longer one two three four five first second third next last new old already how why not""".split())
def noun_clusters(s):
    """Runs of >=4 consecutive content tokens with no function word, punctuation, -ly adverb or -ing/-ed/-s verb-like end inside."""
    hits = []
    for seg in re.split(r"[,;:()\[\]\"“”—–]| - ", s):
        run = []
        for t in re.findall(r"[A-Za-z][A-Za-z'/-]*", seg) + ["the"]:
            tl = t.lower()
            ok = tl not in FUNC and not tl.endswith("ly") and t not in ("IDENT", "NUM")
            if ok: run.append(t)
            else:
                # count hyphen compounds as their parts
                n = sum(len(x.split("-")) for x in run)
                if n >= 4 and len(run) >= 3: hits.append(" ".join(run))
                run = []
    return hits
IMPER = set("""run read write call open close record add remove check verify use keep update mark set create delete edit fix confirm report ask stop
route load pass name state list review apply treat follow do stamp fetch build install copy move replace cite prefer return rerun re-run inspect
compare capture include exclude save start restart wait resolve identify choose select send hand note log search scan load skip surface escalate
render regenerate refresh admit prepare implement plan test trace re-read reread reopen show give put make start end ensure cut split merge map""".split())
def is_imperative(s):
    w = words(s)
    return bool(w) and w[0].lower() in IMPER and w[0][0].isupper()
MULTI = re.compile(r"(?:\band\b|\bthen\b|;|,)\s+(?:then\s+)?(%s)\b" % "|".join(sorted(IMPER, key=len, reverse=True)))
def multi_instr(s):
    return bool(MULTI.search(s[len(words(s)[0]):]))

def pct(xs, p):
    xs = sorted(xs)
    if not xs: return 0
    k = (len(xs) - 1) * p
    f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)

def sample_examples(population, limit):
    """Return at most the available examples, including an empty sample."""
    return random.sample(population, min(limit, len(population)))


def measure(name, text_or_blocks):
    sents = sentences(text_or_blocks)
    lens = [len(words(s)) for _, s in sents]
    n = len(lens); tw = sum(lens)
    if n == 0: return {"corpus": name, "sentences": 0}
    pas = sum(passive(s) for _, s in sents)
    ncs = [h for _, s in sents for h in noun_clusters(s)]
    hed = collections.Counter()
    for _, s in sents:
        for h in HEDGES:
            c = len(re.findall(h, s, re.I))
            if c: hed[h.replace(r"\b", "")] += c
    imp = [s for _, s in sents if is_imperative(s)]
    mi = [s for s in imp if multi_instr(s)]
    return {"corpus": name, "sentences": n, "words": tw, "median": statistics.median(lens), "mean": round(tw / n, 1),
            "p90": round(pct(lens, .9), 1), "max": max(lens),
            "over20_pct": round(100 * sum(l > 20 for l in lens) / n, 1), "over25_pct": round(100 * sum(l > 25 for l in lens) / n, 1),
            "over40_pct": round(100 * sum(l > 40 for l in lens) / n, 1),
            "passive_sent_pct": round(100 * pas / n, 1),
            "noun_clusters_per_1k": round(1000 * len(ncs) / tw, 1), "noun_cluster_examples": ncs[:400],
            "should_per_1k": round(1000 * hed.get("should", 0) / tw, 2),
            "open_hedges_per_1k": round(1000 * sum(v for k, v in hed.items() if k != "should") / tw, 2), "hedges": dict(hed),
            "imperative_sents": len(imp), "multi_instr_pct": round(100 * len(mi) / len(imp), 1) if imp else None,
            "imp_len_median": statistics.median([len(words(s)) for s in imp]) if imp else None,
            "imp_over20_pct": round(100 * sum(len(words(s)) > 20 for s in imp) / len(imp), 1) if imp else None,
            "multi_examples": mi[:40], "longest": sorted([s for _, s in sents], key=lambda s: -len(words(s)))[:12]}

def rd(p):
    try: return open(p, encoding="utf-8").read()
    except Exception: return ""
def wave_dirs(prefixes):
    return sorted({path for prefix in prefixes for path in glob.glob(f"{REPO}/docs/waves/{prefix}*")})


def admitted_spec_paths(waves):
    for directory in wave_dirs(waves):
        folder = Path(directory)
        record = rd(folder / "wave.md")
        section = re.search(r"^## Changes[ \t]*$([\s\S]*?)(?=^## |\Z)", record, re.MULTILINE)
        if not section:
            continue
        admitted = set(re.findall(r"^Change ID:[ \t]*`([^`\n]+)`[ \t]*$", section[1], re.MULTILINE))
        members = sorted(path for path in folder.glob("*.md") if path.name != "wave.md" and path.stem in admitted)
        missing = admitted - {path.stem for path in members}
        if missing:
            sys.exit(f"Missing admitted spec in {folder}: {', '.join(sorted(missing))}")
        yield from members


def specs(waves):
    return "\n\n".join(path.read_text(encoding="utf-8") for path in admitted_spec_paths(waves))


# ---------- corpora ----------
PRE_W = ["20k0e", "20lkx", "20np5", "20qvn", "20st7", "20e12", "20b39", "20oqx", "20ngc"]
def wavemd(ws): return "\n\n".join(rd(d + "/wave.md") for d in wave_dirs(ws))
def spec_sections(ws, heads):
    out = []
    for path in admitted_spec_paths(ws):
        cur = None; buf = []
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^##\s+(.*)", line)
            if m: cur = m.group(1).strip()
            elif cur and any(cur.lower().startswith(h) for h in heads): buf.append(line)
        out.append("\n".join(buf))
    return "\n\n".join(out)
def observed(ws, fields=("observed",)):
    out = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in fields and isinstance(v, str): out.append(("para", v))
                else: walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    for d in wave_dirs(ws):
        for l in rd(d + "/events.jsonl").splitlines():
            try: walk(json.loads(l))
            except Exception: pass
    return out
def changelog(text, versions):
    out = []; on = False
    for line in text.splitlines():
        m = re.match(r"^## \[([^\]]+)\]", line)
        if m: on = m.group(1) in versions; continue
        if on: out.append(line)
    return "\n".join(out)
def added_lines(paths):
    d = git("diff", "-U0", BASE, "--", *paths)
    return "\n".join(l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++"))
def tree_text(rev, path):
    names = git("ls-tree", "-r", "--name-only", rev, "--", path).split("\n")
    return "\n\n".join(git("show", f"{rev}:{n}") for n in names if n.endswith(".md"))

CL = rd(f"{REPO}/CHANGELOG.md")
corp = collections.OrderedDict()
corp["changelog PRE (1.32.0-1.38.0)"] = changelog(CL, {"1.32.0","1.33.0","1.34.0","1.35.0","1.36.0","1.37.0","1.38.0"})
corp["changelog EARLY-POST (1.39.0-1.42.0)"] = changelog(CL, {"1.39.0","1.40.0","1.41.0","1.42.0"})
corp["changelog POST (WF_POST_VERSIONS)"] = changelog(CL, POST_VERSIONS)
corp[f"seeds PRE (all seeds at {BASE}^)"] = tree_text(BASE + "^", ".wavefoundry/framework/seeds")
corp[f"seeds+prompts POST (lines added since {BASE}, incl. working tree)"] = added_lines([".wavefoundry/framework/seeds", "docs/prompts"])
corp["specs PRE (9 mid-Oct waves)"] = specs(PRE_W)
corp["specs POST (WF_POST_WAVES)"] = specs(POST_W)
corp["spec requirements+AC PRE"] = spec_sections(PRE_W, ["requirements", "acceptance criteria"])
corp["spec requirements+AC POST"] = spec_sections(POST_W, ["requirements", "acceptance criteria"])
corp["spec tasks PRE"] = spec_sections(PRE_W, ["tasks"])
corp["spec tasks POST"] = spec_sections(POST_W, ["tasks"])
corp["wave.md PRE"] = wavemd(PRE_W)
corp["wave.md POST"] = wavemd(POST_W)
corp[f"handoff PRE (at {BASE}^)"] = git("show", BASE + "^:docs/agents/session-handoff.md")
corp["handoff POST (working tree)"] = rd(f"{REPO}/docs/agents/session-handoff.md")
corp["review observed PRE"] = observed(PRE_W)
corp["review observed POST"] = observed(POST_W)
corp["writing guide itself"] = rd(f"{REPO}/.wavefoundry/framework/docs/writing-guide.md")

res = [measure(k, v) for k, v in corp.items()]
if not any(r.get("sentences") for r in res):
    sys.exit("measure.py: every corpus is empty; check WF_REPO, WF_BASE and WF_POST_WAVES")
json.dump(res, open("measures.json", "w"), indent=1)
cols = ["sentences","words","median","mean","p90","max","over20_pct","over25_pct","over40_pct","passive_sent_pct","noun_clusters_per_1k","should_per_1k","open_hedges_per_1k","imperative_sents","imp_len_median","imp_over20_pct","multi_instr_pct"]
with open("measures.md", "w") as f:
    f.write("| corpus | " + " | ".join(cols) + " |\n|" + "---|" * (len(cols) + 1) + "\n")
    for r in res:
        f.write("| " + r["corpus"] + " | " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n")
print(open("measures.md").read())

# ---------- term consistency ----------
TERMS = {
 "spec/change": [r"\bspecs?\b", r"\bchanges?\b(?! (?:to|in|the|that|a|an|it|its|how|what|when|from|is|are)\b)", r"\bchange docs?\b", r"\bplans?\b", r"\bchange records?\b", r"\bproposals?\b", r"\btickets?\b"],
 "wave/set": [r"\bwaves?\b", r"\bsets?\b(?= of (?:changes|specs))", r"\bbatch(?:es)?\b", r"\biterations?\b", r"\bsprints?\b", r"\bdelivery\b"],
 "readiness": [r"\breadiness\b", r"\breadied\b", r"\bready\b", r"\bprepared?\b", r"\bpreparation\b", r"\bcouncil-readiness\b"],
 "approval": [r"\bapprovals?\b", r"\bapproved?s?\b", r"\bsign-?offs?\b", r"\bsigned off\b", r"\battestations?\b", r"\bauthori[sz]ations?\b", r"\bconsent\b", r"\bconfirmation\b", r"\bgo-ahead\b", r"\bgreen ?light\b"],
}
with open("terms.md", "w") as f:
    for concept, pats in TERMS.items():
        f.write(f"\n### {concept}\n\n| corpus | " + " | ".join(p.replace("\\b","").replace("|","/") for p in pats) + " |\n|" + "---|" * (len(pats) + 1) + "\n")
        for k, v in corp.items():
            txt = " ".join(clean(b) for _, b in (blocks(v) if isinstance(v, str) else v))
            word_count = len(words(txt))
            cells = []
            for pattern in pats:
                count = len(re.findall(pattern, txt, re.I))
                rate = f"{1000 * count / word_count:.1f}" if word_count else "no observations"
                cells.append(f"{count} ({rate})")
            f.write(f"| {k} | " + " | ".join(cells) + " |\n")
print(open("terms.md").read())
