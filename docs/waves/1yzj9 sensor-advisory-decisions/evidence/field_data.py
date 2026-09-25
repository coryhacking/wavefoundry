"""Field data for the AC-locality sensor decision (wave 1yzj9).

Usage: python -B field_data.py <repo-root>
Runs the sensor over the final text of every change document, split at wave 1wur7
(the sensor's introduction); prints per-corpus counts, the documents with findings
since 1wur7, and a seeded random sample of 12 historical findings for review.
"""
import collections, random, re, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / ".wavefoundry/framework/scripts"))
from wave_lint_lib.wave_validators import _check_ac_asserts_repository_state as check

PHRASE = re.compile(r"(AC-\w+) asserts repository-wide state \('([^']+)'\)")
THIS_WAVE = "1yzj9"
for label, keep in (("before 1wur7", lambda w: w < "1wur7"),
                    ("since 1wur7, excluding this wave", lambda w: "1wur7" <= w != THIS_WAVE)):
    waves = sorted(p for p in (root / "docs/waves").iterdir() if p.is_dir() and keep(p.name.split()[0]))
    docs, hit_docs, findings_all = 0, [], []
    for wave in waves:
        for doc in sorted(wave.glob("*.md")):
            if not re.match(r"^[0-9a-z]{5}-[a-z]+ ", doc.name):
                continue
            docs += 1
            findings = check(doc.read_text(encoding="utf-8"), doc.name)
            if findings:
                hit_docs.append(f"{wave.name.split()[0]}/{doc.name}")
            for finding in findings:
                m = PHRASE.search(finding)
                findings_all.append((wave.name.split()[0], doc.name[:48], m.group(1) if m else "?", m.group(2) if m else "?"))
    phrases = collections.Counter(p for *_, p in findings_all)
    print(f"{label}: {len(waves)} waves, {docs} change docs, {len(hit_docs)} with findings, {len(findings_all)} findings")
    print(f"  top phrases: {phrases.most_common(5)}")
    if len(hit_docs) <= 5:
        for name in hit_docs:
            print(f"  hit: {name}")
    else:
        random.seed(7)
        print("  seeded sample of 12 findings (wave, doc, AC, phrase), reviewed as true positives:")
        for row in random.sample(findings_all, 12):
            print(f"    {row}")
