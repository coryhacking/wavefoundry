import sys,json,stat,io,contextlib,importlib.util
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('own_probes','/tmp/wf-204mp-lexical-final-arch-docs-probes.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
T=p.T
cases={
 'image_literal_title':('[A](elsewhere "![icon][ref]")\n\n[ref]: OLD\n\n[LIVE](OLD)\n','[A](elsewhere "![icon][ref]")\n\n[ref]: NEW\n\n[LIVE](NEW)\n','09'),
 'image_literal_html':('Text <span note="![icon][ref]">\n\n[ref]: OLD\n\n[LIVE](OLD)\n','Text <span note="![icon][ref]">\n\n[ref]: NEW\n\n[LIVE](NEW)\n','09'),
 'real_shared_image':('![icon][ref]\n\n[ref]: OLD\n\n[LIVE](OLD)\n','![icon][ref]\n\n[ref]: OLD\n\n[LIVE](NEW)\n','06'),
 'multiline_tag':('Text <span\nnote="`"> [LIVE](OLD) <span note="`">\n','Text <span\nnote="`"> [LIVE](NEW) <span note="`">\n','09'),
 'attribute_link':('Text <span note="[C](OLD)"> [LIVE](OLD)\n','Text <span note="[C](OLD)"> [LIVE](NEW)\n','09'),
 'unmatched_title_tick':('[A](OLD "`") [LIVE](OLD) `\n','[A](NEW "`") [LIVE](NEW) `\n','11'),
 'reference_title_literal':('[ref]: OLD "[C](OLD) `"\n[LIVE](OLD)\n\n` unrelated\n','[ref]: NEW "[C](OLD) `"\n[LIVE](NEW)\n\n` unrelated\n','10'),
}
rows=[p.run_case(n,*v) for n,v in cases.items()]
for row in rows:print(row['case'],row['passed'],flush=True)
# Independent actual native-pair path expected substitutions, not production spans.
for style in ('raw','escaped','percent'):
 target=T('runTest');target.setUp();row={'case':'native-'+style,'group':'07'}
 try:
  old_rel,new_rel=next((a,b) for a,b in target.ras.COUNCIL_ROLE_RENAMES if a.endswith('/SKILL.md'))
  old_native=target.root/old_rel;old_native.parent.mkdir(parents=True,exist_ok=True)
  old_native.write_bytes(('# Native\n\nSee '+target.old_rel+'\n').encode());old_native.chmod(0o640)
  a,b='../../../'+old_rel,'../../../'+new_rel
  if style=='escaped':a,b=(x.replace('-','\\-') for x in (a,b))
  if style=='percent':a,b=(x.replace('-','%2d') for x in (a,b))
  original=(f'[N](<{a}?a=2#x> "retained")\r\n[L]({target.old.name})\r\n').encode()
  expected=(f'[N](<{b}?a=2#x> "retained")\r\n[L]({target.new.name})\r\n').encode()
  target.peer.write_bytes(original);target.peer.chmod(0o640);preview=target._preview_incoming_role_links();target._surface()
  row['installed']=not old_native.exists() and (target.root/new_rel).is_file() and target.peer.read_bytes()==expected
  actual=target.mod.subprocess_util.isolated_run;runs=[]
  def capture(*args,**kwargs):
   kwargs.update(capture_output=True,text=True);r=actual(*args,**kwargs);runs.append(r);return r
  with patch.object(target.mod.subprocess_util,'isolated_run',side_effect=capture):target._surface()
  row['retry']=target.peer.read_bytes()==expected and len(runs)==1 and 'unchanged unsupported' not in runs[0].stderr
  row['mode']=stat.S_IMODE(target.peer.stat().st_mode)==0o640 and stat.S_IMODE((target.root/new_rel).stat().st_mode)==0o640
  row['passed']=all(row[k] for k in ('installed','retry','mode'))
 finally:target.doCleanups()
 rows.append(row);print(row['case'],row['passed'],flush=True)
# Current doc/history ownership and guidance truth.
t=T('runTest');t.setUp()
try:
 roots=t.ras.record_paths.load_record_roots(t.root)
 excluded=['docs/agents/journals/past.md','docs/agents/snapshots/past.md','docs/reports/past.md','docs/architecture/decisions/past.md','docs/decisions/past.md','docs/adr/past.md',roots.waves_rel+'/past.md',roots.plans_rel+'/past.md']
 src=f'[old](docs/agents/specialists/{t.old.name})\r\n'.encode()
 for rel in excluded:
  path=t.root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(src)
 preview=t._preview_incoming_role_links();t._surface();t._surface()
 row={'case':'history-and-guidance','group':'08','passed':all((t.root/rel).read_bytes()==src for rel in excluded) and all(rel not in preview for rel in excluded),'paths':excluded}
 seed=(p.ROOT/'.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md').read_text()
 clause=next(x for x in seed.splitlines() if '**Council role rename.**' in x)
 required=['automatically repairs supported local inline and reference-link destinations','their links remain unchanged and are not reported','Dry-run preview','rerun repairs remaining eligible links']
 row['current_guidance']=all(x in clause for x in required)
 old=__import__('subprocess').check_output(['git','show','HEAD:.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md'],cwd=p.ROOT,text=True)
 row['known_bad_old_guidance_rejected']=not all(x in old for x in required)
 row['passed']=row['passed'] and row['current_guidance'] and row['known_bad_old_guidance_rejected'];rows.append(row);print(row['case'],row['passed'])
finally:t.doCleanups()
Path('/tmp/wf-204mp-autolink-final-arch-docs-extras.json').write_text(json.dumps({'cases':cases,'rows':rows},indent=2))
