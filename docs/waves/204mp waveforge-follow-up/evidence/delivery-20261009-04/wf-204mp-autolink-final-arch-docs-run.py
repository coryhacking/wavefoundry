import sys,importlib.util,json,time,stat
from pathlib import Path
ROOT=Path('/Users/coryhacking/Developer/wavefoundry');B='/tmp/wf-204mp-autolink-final-arch-docs-'
sys.path[:0]=[str(ROOT/'.wavefoundry/framework/scripts'),str(ROOT/'.wavefoundry/framework/scripts/tests')]
spec=importlib.util.spec_from_file_location('candidate','/tmp/wf-204mp-lexical-final-arch-docs-probes.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
T=p.T
A={
'uri_literal':('Text <https://host.invalid/[hidden](OLD)> [live](OLD)\n','Text <https://host.invalid/[hidden](OLD)> [live](NEW)\n'),
'uri_query':('Text <custom+protocol://host.invalid/?arg=[hidden](OLD)> [live](OLD)\n','Text <custom+protocol://host.invalid/?arg=[hidden](OLD)> [live](NEW)\n'),
'uri_tick':('Text <https://host.invalid/?arg=`> [live](OLD) tail `\n','Text <https://host.invalid/?arg=`> [live](NEW) tail `\n'),
'email_tick':('Text <a`@host.invalid> [live](OLD) tail `\n','Text <a`@host.invalid> [live](NEW) tail `\n'),
'prior_code_uri':('Text ` <https://host.invalid/[hidden](OLD)?arg=`> [live](OLD)\n','Text ` <https://host.invalid/[hidden](OLD)?arg=`> [live](NEW)\n'),
'prior_code_email':('Text ` <a`@host.invalid> [live](OLD)\n','Text ` <a`@host.invalid> [live](NEW)\n'),
'quote_uri':('> Text <https://host.invalid/[hidden](OLD)> [live](OLD)\n','> Text <https://host.invalid/[hidden](OLD)> [live](NEW)\n'),
'list_email':('- Text <a`@host.invalid> [live](OLD) tail `\n','- Text <a`@host.invalid> [live](NEW) tail `\n'),
'metadata_ref':('[first](elsewhere "![icon][r]")\n\n[r]: OLD\n\n[live](OLD)\n','[first](elsewhere "![icon][r]")\n\n[r]: NEW\n\n[live](NEW)\n'),
'escaped_angle':('Text \\<https://host.invalid/[hidden](OLD)> [live](OLD)\n','Text \\<https://host.invalid/[hidden](OLD)> [live](NEW)\n'),
}
# Escaped angle has an ordinary Markdown link inside literal text, resolving as external nested URI prefix? Independent parser below decides, do not silently count it.
A.pop('escaped_angle')
def actual(name,original,expected,old=False):
 t=T('runTest');t.setUp();r={'case':name,'old_renderer':old}
 try:
  if old:(t.scripts/'render_agent_surfaces.py').write_bytes(Path('/tmp/wf-204mp-pre-autolink-renderer.py').read_bytes())
  def b(s):return s.replace('OLD',t.old.name).replace('NEW',t.new.name).replace('\n','\r\n').encode()
  source,want=b(original),b(expected);t.peer.write_bytes(source);t.peer.chmod(0o640);snap=t._tree();preview=t._preview_incoming_role_links();r['preview_no_writes']=snap==t._tree();t._surface();first=t.peer.read_bytes();t._surface();repeat=t.peer.read_bytes()
  r.update(role_moved=not t.old.exists() and t.new.exists(),install_exact=first==want,reinstall_exact=repeat==want,mode_preserved=stat.S_IMODE(t.peer.stat().st_mode)==0o640,expected=want.decode(),observed=first.decode());r['passed']=all(r[k] for k in ['preview_no_writes','role_moved','install_exact','reinstall_exact','mode_preserved'])
 except Exception as e:r.update(passed=False,error=repr(e))
 finally:t.doCleanups()
 return r
started=time.monotonic();rows=[]
for n,v in p.cases.items():
 row=p.run_case(n,*v);rows.append(row);print('CURRENT',n,row['passed'],flush=True)
for n,v in A.items():
 row=actual(n,*v);rows.append(row);print('CURRENT',n,row['passed'],flush=True)
oldrows=[]
for n in list(A)[:6]:
 row=actual(n,*A[n],old=True);oldrows.append(row);print('PRE-FIX',n,row['passed'],flush=True)
mutants=[]
for m in p.mutants:
 values=('![A](wave%2Dcouncil.md)\n\n[L](OLD)\n','![A](wave%2Dcouncil.md)\n\n[L](NEW)\n','13') if m[1]=='encoded_image' else p.cases[m[1]]
 if m[0]=='omit-html':continue # prior survival not counted as own kill; valid block termination mutation below.
 row=p.run_case(m[1],*values,mutation=m,diag=m[1]=='encoded_image');row['detected']=not row['passed'] and row.get('role_moved',False) and 'error' not in row;mutants.append(row);print('MUTANT',m[0],row['detected'],flush=True)
extra=[
('omit-uri','uri_literal',r'+ r"|<[A-Za-z][A-Za-z0-9+.-]{1,31}:[^\x00-\x20<>]*>"',''),
('omit-email','email_tick',r'+ r"|<[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*>"',r'+ r"(?!)"'),
('omit-metadata-blank','metadata_ref','for pos in range(metadata_start, metadata_end - 1):','for pos in range(0):'),
('omit-HTML-terminator','html_comment','html = None\n                block_boundary = True','html = "unmatchable HTML terminator"\n                block_boundary = True'),
('odd-only-escape','escaped_link_2','if escaped(m.start()):','if m.start() > 0 and masked[m.start() - 1] == "\\\\":'),
]
# Exact email token mutation avoids quoting ambiguity via extracting single source line.
src=(ROOT/'.wavefoundry/framework/scripts/render_agent_surfaces.py').read_text();email=next(x.strip().rstrip(',') for x in src.splitlines() if '+ r"|<[A-Za-z0-9.!#$%' in x)
extra[1]=('omit-email','email_tick',email,'+ r"(?!)"')
for m in extra:
 val=(*A[m[1]],'14' if m[1] in ['uri_literal','email_tick'] else '09') if m[1] in A else p.cases[m[1]]
 row=p.run_case(m[1],*val,mutation=m);row['detected']=not row['passed'] and row.get('role_moved',False) and 'error' not in row;mutants.append(row);print('MUTANT',m[0],row['detected'],row.get('error',''),flush=True)
Path(B+'behavior.json').write_text(json.dumps({'rows':rows,'pre_fix':oldrows,'mutants':mutants,'elapsed':time.monotonic()-started},indent=2));print('DONE',len(rows),sum(not r['passed'] for r in rows),len(mutants),flush=True)
